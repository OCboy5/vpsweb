"""
OpenAI-compatible API provider implementation.

This module implements support for OpenAI-compatible APIs including
Tongyi (Qwen), DeepSeek, and other providers that follow the OpenAI API format.
"""

import httpx
from typing import Dict, List, Any, Optional
import logging
import json

from .base import (
    BaseLLMProvider,
    LLMResponse,
    LLMProviderError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    ContentFilterError,
    ConfigurationError,
)

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    OpenAI-compatible API provider implementation.

    Supports providers like Tongyi (Qwen), DeepSeek, and others that follow
    the OpenAI API format.
    """

    def __init__(self, base_url: str, api_key: str, **kwargs):
        """
        Initialize the OpenAI-compatible provider.

        Args:
            base_url: Base URL for the provider's API
            api_key: API key for authentication
            **kwargs: Additional configuration options
        """
        super().__init__(base_url, api_key, **kwargs)
        self.timeout = kwargs.get("timeout", 120.0)
        self.max_retries = kwargs.get("max_retries", 3)
        self.retry_delay = kwargs.get("retry_delay", 1.0)
        self.connection_pool_size = kwargs.get("connection_pool_size", 10)

        # Validate API key on initialization
        if not self.api_key:
            raise AuthenticationError(
                f"API key not found for {self.get_provider_name()}. "
                f"Please set the appropriate environment variable (e.g., TONGYI_API_KEY, DEEPSEEK_API_KEY).",
                provider=self.get_provider_name(),
            )

        logger.info(f"Initialized OpenAICompatibleProvider for {base_url}")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[List[str]] = None,
        stream: bool = False,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a completion using the OpenAI-compatible API.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: Model name to use for generation
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            frequency_penalty: Frequency penalty parameter
            presence_penalty: Presence penalty parameter
            stop: Optional list of stop sequences
            stream: Whether to stream the response (currently not supported)
            timeout: Optional timeout for this specific request (overrides provider default)
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse containing the generated content and metadata

        Raises:
            LLMProviderError: If generation fails
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
            TimeoutError: If request times out
            ContentFilterError: If content is filtered
        """
        # Validate inputs
        self.validate_messages(messages)
        self.validate_generation_params(
            temperature, max_tokens, top_p, frequency_penalty, presence_penalty
        )

        if stream:
            raise NotImplementedError("Streaming is not currently supported")

        # Log request
        self.log_request(
            messages, model, temperature=temperature, max_tokens=max_tokens
        )

        # Prepare request payload
        payload = self._prepare_request_payload(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop,
            **kwargs,
        )

        # Prepare headers
        headers = self._prepare_headers()

        # Make request with retry logic
        response_data = await self._make_request_with_retry(
            payload=payload, headers=headers, timeout=timeout
        )

        # Parse response
        llm_response = self._parse_response(response_data, model)

        # Log response
        self.log_response(llm_response)

        return llm_response

    def _prepare_request_payload(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        frequency_penalty: float,
        presence_penalty: float,
        stop: Optional[List[str]],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Prepare the request payload for the API call.

        Args:
            messages: List of messages
            model: Model name
            temperature: Temperature parameter
            max_tokens: Maximum tokens
            top_p: Top-p parameter
            frequency_penalty: Frequency penalty
            presence_penalty: Presence penalty
            stop: Stop sequences
            **kwargs: Additional parameters

        Returns:
            Request payload dictionary
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
        }

        if stop:
            payload["stop"] = stop

        # Add any additional parameters
        payload.update(kwargs)

        return payload

    def _prepare_headers(self) -> Dict[str, str]:
        """
        Prepare headers for the API request.

        Returns:
            Headers dictionary
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "VoxPoeticaStudio/1.0.0",
        }

    async def _make_request_with_retry(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.

        Args:
            payload: Request payload
            headers: Request headers
            timeout: Optional timeout for this specific request (overrides provider default)

        Returns:
            Response data dictionary

        Raises:
            LLMProviderError: If request fails after retries
        """
        import asyncio
        from httpx import HTTPStatusError, ConnectError, TimeoutException

        for attempt in range(self.max_retries + 1):
            try:
                # Use step-specific timeout if provided, otherwise use provider default
                request_timeout = timeout if timeout is not None else self.timeout
                logger.info(
                    f"Using timeout: {request_timeout}s (step_specific: {timeout}, provider_default: {self.timeout})"
                )
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(request_timeout),
                    limits=httpx.Limits(max_connections=self.connection_pool_size),
                    http2=True,
                ) as client:

                    logger.info(
                        f"Making POST request to {self.base_url}/chat/completions"
                    )

                    # Explicitly disable streaming and add read timeout
                    modified_payload = payload.copy()
                    modified_payload["stream"] = False

                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=modified_payload,
                        headers=headers,
                    )
                    logger.info(
                        f"HTTP request completed, status: {response.status_code}, content length: {len(response.content)}"
                    )

                    # Handle HTTP errors
                    if response.status_code != 200:
                        await self._handle_http_error(response)

                    # DEBUG: Log response details
                    logger.info(
                        f"=== {self.get_provider_name().upper()} API RESPONSE DEBUG ==="
                    )
                    logger.info(f"Status Code: {response.status_code}")
                    logger.info(f"Response Length: {len(response.content)} bytes")
                    logger.info(
                        f"Response Content (first 500 chars): {response.content[:500]}"
                    )
                    logger.info(f"=== END API RESPONSE DEBUG ===")

                    # Parse successful response with timeout
                    try:
                        import json

                        logger.info(f"Starting JSON parsing...")

                        # Use asyncio.wait_for to add timeout to JSON parsing
                        response_data = await asyncio.wait_for(
                            asyncio.to_thread(response.json),
                            timeout=10.0,  # 10 second timeout for JSON parsing
                        )
                        logger.info(
                            f"JSON parsing successful, keys: {list(response_data.keys())}"
                        )
                        return response_data
                    except asyncio.TimeoutError:
                        logger.error(f"JSON parsing timed out after 10 seconds")
                        logger.error(
                            f"Response content length: {len(response.content)} bytes"
                        )
                        # Try to see what we got
                        content_preview = (
                            response.content[:500] if response.content else "No content"
                        )
                        logger.error(f"Response content preview: {content_preview}")
                        raise LLMProviderError(
                            f"JSON parsing timed out for {self.get_provider_name()}"
                        )
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON parsing failed: {e}")
                        logger.error(f"Response content: {response.content}")
                        raise LLMProviderError(
                            f"Invalid JSON response from {self.get_provider_name()}: {e}"
                        )
                    except Exception as e:
                        logger.error(f"Error parsing response: {e}")
                        raise LLMProviderError(
                            f"Error parsing response from {self.get_provider_name()}: {e}"
                        )

            except (ConnectError, TimeoutException) as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise TimeoutError(
                        f"Request to {self.get_provider_name()} timed out after {self.max_retries} retries: {e}",
                        provider=self.get_provider_name(),
                    )

            except HTTPStatusError as e:
                await self._handle_http_error(e.response)

            except Exception as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise LLMProviderError(
                        f"Request to {self.get_provider_name()} failed after {self.max_retries} retries: {e}",
                        provider=self.get_provider_name(),
                    )

        # This should never be reached, but just in case
        raise LLMProviderError(
            f"Request to {self.get_provider_name()} failed after all retries",
            provider=self.get_provider_name(),
        )

    async def _handle_http_error(self, response: httpx.Response) -> None:
        """
        Handle HTTP error responses.

        Args:
            response: HTTP response with error status

        Raises:
            Appropriate exception based on status code
        """
        status_code = response.status_code
        error_content = await response.aread()
        logger.error(
            f"Raw error content from {self.get_provider_name()}: {error_content}"
        )

        try:
            error_data = json.loads(error_content.decode("utf-8"))
            error_message = error_data.get("error", {}).get("message", str(error_data))
        except (json.JSONDecodeError, UnicodeDecodeError):
            error_message = error_content.decode("utf-8", errors="ignore")[:500]

        if status_code == 401:
            raise AuthenticationError(
                f"Authentication failed for {self.get_provider_name()}: {error_message}",
                provider=self.get_provider_name(),
                status_code=status_code,
            )
        elif status_code == 429:
            raise RateLimitError(
                f"Rate limit exceeded for {self.get_provider_name()}: {error_message}",
                provider=self.get_provider_name(),
                status_code=status_code,
            )
        elif status_code == 408 or status_code >= 500:
            raise TimeoutError(
                f"Server error from {self.get_provider_name()}: {error_message}",
                provider=self.get_provider_name(),
                status_code=status_code,
            )
        elif status_code == 400 and "content_filter" in error_message.lower():
            raise ContentFilterError(
                f"Content filtered by {self.get_provider_name()}: {error_message}",
                provider=self.get_provider_name(),
                status_code=status_code,
            )
        else:
            raise LLMProviderError(
                f"HTTP {status_code} error from {self.get_provider_name()}: {error_message}",
                provider=self.get_provider_name(),
                status_code=status_code,
            )

    def _parse_response(self, response_data: Dict[str, Any], model: str) -> LLMResponse:
        """
        Parse the API response into standardized format.

        Args:
            response_data: Raw response data from API
            model: Model name used for generation

        Returns:
            Standardized LLMResponse

        Raises:
            LLMProviderError: If response parsing fails
        """
        try:
            # Extract choices
            choices = response_data.get("choices", [])
            if not choices:
                raise LLMProviderError(
                    f"No choices in response from {self.get_provider_name()}",
                    provider=self.get_provider_name(),
                )

            choice = choices[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            if not content:
                content = message.get("reasoning_content", "")
            finish_reason = choice.get("finish_reason")

            if not content:
                raise LLMProviderError(
                    f"No content or reasoning_content in response from {self.get_provider_name()}",
                    provider=self.get_provider_name(),
                )

            # Extract usage information
            usage = response_data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

            # Extract additional metadata
            metadata = {
                "raw_response": response_data,
                "created": response_data.get("created"),
                "id": response_data.get("id"),
                "object": response_data.get("object"),
                "system_fingerprint": response_data.get("system_fingerprint"),
            }

            return LLMResponse(
                content=content,
                tokens_used=total_tokens,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model_name=model,
                finish_reason=finish_reason,
                metadata=metadata,
            )

        except (KeyError, IndexError, TypeError) as e:
            raise LLMProviderError(
                f"Failed to parse response from {self.get_provider_name()}: {e}",
                provider=self.get_provider_name(),
            )

    def validate_config(self, config) -> bool:
        """
        Validate provider configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if configuration is valid

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Handle both dict and Pydantic model (V1 and V2 compatibility)
        if hasattr(config, "model_dump"):
            # Pydantic V2
            config_dict = config.model_dump()
        elif hasattr(config, "dict"):
            # Pydantic V1
            config_dict = config.dict()
        else:
            # Already a dict
            config_dict = config

        required_keys = ["api_key_env", "base_url", "type"]
        missing_keys = [key for key in required_keys if key not in config_dict]

        if missing_keys:
            raise ConfigurationError(
                f"Missing required configuration keys: {missing_keys}",
                provider=self.get_provider_name(),
            )

        if config.get("type") != "openai_compatible":
            raise ConfigurationError(
                f"Invalid provider type: {config.get('type')}. Expected: openai_compatible",
                provider=self.get_provider_name(),
            )

        # Validate base URL
        base_url = config.get("base_url", "")
        if not base_url.startswith(("http://", "https://")):
            raise ConfigurationError(
                f"Invalid base URL: {base_url}. Must start with http:// or https://",
                provider=self.get_provider_name(),
            )

        # Validate models list
        models = config.get("models", [])
        if not models:
            raise ConfigurationError(
                "No models specified in configuration",
                provider=self.get_provider_name(),
            )

        logger.info(f"Configuration validated for {self.get_provider_name()}")
        return True

    def get_supported_models(self) -> List[str]:
        """
        Get list of supported models for this provider.

        Returns:
            List of model names supported by this provider
        """
        # This would typically come from configuration, but for now return common models
        # that are supported by OpenAI-compatible APIs
        return [
            "qwen-max-latest",
            "qwen-max-0919",
            "qwen-turbo",
            "deepseek-reasoner",
            "deepseek-chat",
            "gpt-4",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]

    def get_provider_name(self) -> str:
        """
        Get the provider name for identification.

        Returns:
            Provider name string
        """
        return "OpenAICompatible"

    def __repr__(self) -> str:
        """String representation of the provider."""
