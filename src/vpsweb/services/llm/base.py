"""
Abstract base class for LLM providers.

This module defines the interface that all LLM providers must implement,
ensuring consistent behavior across different AI service providers.
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    OPENAI_COMPATIBLE = "openai_compatible"


class LLMResponse(BaseModel):
    """Standardized response format from LLM providers."""

    content: str = Field(..., description="The generated text content")
    tokens_used: int = Field(
        ..., ge=0, description="Total number of tokens used in the request"
    )
    prompt_tokens: int = Field(..., ge=0, description="Number of tokens in the prompt")
    completion_tokens: int = Field(
        ..., ge=0, description="Number of tokens in the completion"
    )
    model_name: str = Field(
        ..., description="Name of the model that generated the response"
    )
    finish_reason: Optional[str] = Field(
        None,
        description="Reason why generation finished (e.g., 'stop', 'length')",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from the provider",
    )


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers.

    This class defines the interface that must be implemented by all LLM providers,
    ensuring consistent behavior across different AI service providers like Tongyi,
    DeepSeek, OpenAI, etc.
    """

    def __init__(self, base_url: str, api_key: str, **kwargs):
        """
        Initialize the LLM provider.

        Args:
            base_url: Base URL for the provider's API
            api_key: API key for authentication
            **kwargs: Additional provider-specific configuration
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.config = kwargs
        logger.info(f"Initialized {self.__class__.__name__} with base URL: {base_url}")

    @abstractmethod
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
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: Model name to use for generation
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            frequency_penalty: Frequency penalty parameter
            presence_penalty: Presence penalty parameter
            stop: Optional list of stop sequences
            stream: Whether to stream the response (not currently supported)
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse containing the generated content and metadata

        Raises:
            LLMProviderError: If generation fails
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
        """

    @abstractmethod
    def validate_config(self, config) -> bool:
        """
        Validate provider configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if configuration is valid, False otherwise

        Raises:
            ConfigurationError: If configuration is invalid with details
        """

    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """
        Get list of supported models for this provider.

        Returns:
            List of model names supported by this provider
        """

    def validate_messages(self, messages: List[Dict[str, str]]) -> None:
        """
        Validate message format before sending to provider.

        Args:
            messages: List of message dictionaries to validate

        Raises:
            ValueError: If messages are invalid
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")

        for i, message in enumerate(messages):
            if not isinstance(message, dict):
                raise ValueError(f"Message {i} must be a dictionary")

            if "role" not in message or "content" not in message:
                raise ValueError(f"Message {i} must have 'role' and 'content' keys")

            if message["role"] not in ["system", "user", "assistant"]:
                raise ValueError(f"Message {i} has invalid role: {message['role']}")

            if not message["content"] or not isinstance(message["content"], str):
                raise ValueError(f"Message {i} must have non-empty string content")

    def validate_generation_params(
        self,
        temperature: float,
        max_tokens: int,
        top_p: float,
        frequency_penalty: float,
        presence_penalty: float,
    ) -> None:
        """
        Validate generation parameters.

        Args:
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            frequency_penalty: Frequency penalty
            presence_penalty: Presence penalty

        Raises:
            ValueError: If any parameter is invalid
        """
        if not (0.0 <= temperature <= 2.0):
            raise ValueError(
                f"Temperature must be between 0.0 and 2.0, got {temperature}"
            )

        if max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {max_tokens}")

        if not (0.0 <= top_p <= 1.0):
            raise ValueError(f"top_p must be between 0.0 and 1.0, got {top_p}")

        if not (-2.0 <= frequency_penalty <= 2.0):
            raise ValueError(
                f"frequency_penalty must be between -2.0 and 2.0, got {frequency_penalty}"
            )

        if not (-2.0 <= presence_penalty <= 2.0):
            raise ValueError(
                f"presence_penalty must be between -2.0 and 2.0, got {presence_penalty}"
            )

    def log_request(self, messages: List[Dict[str, str]], model: str, **params) -> None:
        """
        Log the request for debugging and monitoring.

        Args:
            messages: Messages being sent
            model: Model being used
            **params: Generation parameters
        """
        logger.debug(f"Request to {self.__class__.__name__} - Model: {model}")
        logger.debug(f"Messages count: {len(messages)}")
        logger.debug(
            f"First message role: {messages[0]['role'] if messages else 'None'}"
        )
        logger.debug(f"Parameters: {params}")

    def log_response(self, response: LLMResponse) -> None:
        """
        Log the response for debugging and monitoring.

        Args:
            response: Response from the provider
        """
        logger.debug(f"Response from {self.__class__.__name__}")
        logger.debug(f"Tokens used: {response.tokens_used}")
        logger.debug(f"Model: {response.model_name}")
        logger.debug(f"Content length: {len(response.content)} characters")

    def get_provider_name(self) -> str:
        """
        Get the provider name for identification.

        Returns:
            Provider name string
        """
        return self.__class__.__name__.replace("Provider", "").replace("LLM", "")


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""

    def __init__(self, message: str, provider: str = None, status_code: int = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(LLMProviderError):
    """Raised when authentication fails."""


class RateLimitError(LLMProviderError):
    """Raised when rate limit is exceeded."""


class ConfigurationError(LLMProviderError):
    """Raised when configuration is invalid."""


class TimeoutError(LLMProviderError):
    """Raised when request times out."""


class ContentFilterError(LLMProviderError):
    """Raised when content is filtered by the provider."""
