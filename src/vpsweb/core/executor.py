"""
Step Executor for Vox Poetica Studio Web.

This module provides the core execution engine that orchestrates the poetry translation
workflow by coordinating LLM providers, prompt templates, and output parsing.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from ..services.llm.factory import LLMFactory
from ..services.prompts import PromptService, TemplateLoadError, TemplateVariableError
from ..services.parser import OutputParser, XMLParsingError, ValidationError
from ..models.config import StepConfig, ModelProviderConfig
from ..models.translation import (
    TranslationInput,
    InitialTranslation,
    EditorReview,
    RevisedTranslation,
    TranslationOutput
)

logger = logging.getLogger(__name__)


class StepExecutorError(Exception):
    """Base exception for step execution errors."""
    pass


class PromptRenderingError(StepExecutorError):
    """Raised when prompt template rendering fails."""
    pass


class LLMCallError(StepExecutorError):
    """Raised when LLM API calls fail."""
    pass


class OutputParsingError(StepExecutorError):
    """Raised when output parsing or validation fails."""
    pass


class StepExecutor:
    """
    Generic step executor that coordinates LLM providers, prompts, and parsing
    to execute workflow steps with proper error handling and retry logic.
    """

    def __init__(self, llm_factory: LLMFactory, prompt_service: PromptService):
        """
        Initialize the step executor.

        Args:
            llm_factory: Factory for creating LLM providers
            prompt_service: Service for loading and rendering prompt templates
        """
        self.llm_factory = llm_factory
        self.prompt_service = prompt_service
        self._step_templates = {
            "initial_translation": "initial_translation",
            "editor_review": "editor_review",
            "translator_revision": "translator_revision"
        }
        logger.info("Initialized StepExecutor with LLM factory and prompt service")

    async def execute_step(
        self,
        step_name: str,
        input_data: Dict[str, Any],
        config: StepConfig
    ) -> Dict[str, Any]:
        """
        Execute a single workflow step with full error handling and retry logic.

        Args:
            step_name: Name of the step to execute
            input_data: Input data for the step
            config: Step configuration with provider and parameters

        Returns:
            Dictionary containing execution results and metadata

        Raises:
            StepExecutorError: If execution fails after all retries
        """
        logger.info(f"Starting step execution: {step_name}")
        start_time = time.time()

        try:
            # Step 1: Validate inputs
            self._validate_step_inputs(step_name, input_data, config)

            # Step 2: Get LLM provider
            provider = await self._get_llm_provider(config)
            logger.debug(f"Using provider: {config.provider} with model: {config.model}")

            # Step 3: Render prompt template
            system_prompt, user_prompt = await self._render_prompt_template(
                step_name, input_data
            )
            logger.debug(f"Rendered system prompt: {len(system_prompt)} chars")
            logger.debug(f"Rendered user prompt: {len(user_prompt)} chars")

            # Step 4: Execute LLM call with retry logic
            llm_response = await self._execute_llm_with_retry(
                provider, system_prompt, user_prompt, config, step_name
            )
            logger.info(f"LLM call successful, response length: {len(llm_response.content)} chars")
            logger.debug(f"Tokens used: {llm_response.tokens_used}")

            # Step 5: Parse and validate output
            parsed_output = await self._parse_and_validate_output(
                step_name, llm_response.content, config
            )
            logger.debug(f"Output parsing successful, fields: {list(parsed_output.keys())}")

            # Step 6: Build result with metadata
            execution_time = time.time() - start_time
            result = self._build_step_result(
                step_name, parsed_output, llm_response, execution_time, config
            )

            logger.info(f"Step {step_name} completed successfully in {execution_time:.2f}s")
            return result

        except StepExecutorError as e:
            logger.error(f"Step execution failed for {step_name}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in step {step_name}: {e}")
            raise StepExecutorError(f"Unexpected error in step {step_name}: {e}")

    def _validate_step_inputs(
        self,
        step_name: str,
        input_data: Dict[str, Any],
        config: StepConfig
    ) -> None:
        """Validate step inputs and configuration."""
        if not step_name:
            raise ValueError("Step name cannot be empty")

        if step_name not in self._step_templates:
            raise ValueError(f"Unknown step name: {step_name}. Available: {list(self._step_templates.keys())}")

        if not isinstance(input_data, dict):
            raise ValueError("Input data must be a dictionary")

        if not config:
            raise ValueError("Step configuration is required")

        logger.debug(f"Step inputs validated for {step_name}")

    async def _get_llm_provider(self, config: StepConfig) -> Any:
        """Get LLM provider instance from factory."""
        try:
            # Get provider configuration from factory's models.yaml
            provider_config = self.llm_factory.get_provider_config(config.provider)
            if not provider_config:
                raise LLMCallError(f"Provider '{config.provider}' not found in configuration")

            return self.llm_factory.get_provider(config.provider)

        except Exception as e:
            logger.error(f"Failed to get LLM provider: {e}")
            raise LLMCallError(f"Failed to initialize LLM provider: {e}")

    async def _render_prompt_template(
        self,
        step_name: str,
        input_data: Dict[str, Any]
    ) -> tuple[str, str]:
        """Render the appropriate prompt template for the step."""
        template_name = self._step_templates[step_name]

        try:
            logger.debug(f"Rendering template: {template_name} with variables: {list(input_data.keys())}")
            system_prompt, user_prompt = self.prompt_service.render_prompt(
                template_name, input_data
            )

            # DEBUG: Log the rendered prompts for troubleshooting
            logger.info(f"=== {step_name.upper()} PROMPT DEBUG ===")
            logger.info(f"Step: {step_name}")
            logger.info(f"Template: {template_name}")
            logger.info(f"Input Variables: {list(input_data.keys())}")
            logger.info(f"System Prompt:\n{system_prompt}")
            logger.info(f"User Prompt Length: {len(user_prompt)} characters")
            logger.info(f"User Prompt:\n{user_prompt}")
            logger.info(f"=== END {step_name.upper()} PROMPT DEBUG ===")

            return system_prompt, user_prompt

        except (TemplateLoadError, TemplateVariableError) as e:
            logger.error(f"Prompt template rendering failed: {e}")
            raise PromptRenderingError(f"Failed to render prompt template: {e}")

    async def _execute_llm_with_retry(
        self,
        provider: Any,
        system_prompt: str,
        user_prompt: str,
        config: StepConfig,
        step_name: str
    ) -> Any:
        """Execute LLM call with exponential backoff retry logic."""
        max_retries = config.retry_attempts or 3
        base_delay = 1.0  # Base delay in seconds

        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"LLM call attempt {attempt + 1}/{max_retries + 1}")

                # Format messages for OpenAI-compatible API
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]

                response = await provider.generate(
                    messages=messages,
                    model=config.model,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    timeout=config.timeout
                )

                if not response or not response.content:
                    raise LLMCallError("LLM returned empty response")

                logger.debug(f"LLM call successful on attempt {attempt + 1}")

                # DEBUG: Log LLM response for troubleshooting
                logger.info(f"=== {step_name.upper()} RESPONSE DEBUG ===")
                logger.info(f"Step: {step_name}")
                logger.info(f"Provider: {config.provider}")
                logger.info(f"Model: {config.model}")
                logger.info(f"Response Length: {len(response.content)} characters")
                logger.info(f"Full Response:\n{response.content}")
                logger.info(f"=== END {step_name.upper()} RESPONSE DEBUG ===")

                return response

            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"LLM call failed after {max_retries + 1} attempts: {e}")
                    raise LLMCallError(f"LLM API call failed after {max_retries + 1} attempts: {e}")

                delay = base_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"LLM call attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s")
                await asyncio.sleep(delay)

    async def _parse_and_validate_output(
        self,
        step_name: str,
        llm_content: str,
        config: StepConfig
    ) -> Dict[str, Any]:
        """Parse LLM output and validate required fields."""
        try:
            # Parse XML content
            parsed_data = OutputParser.parse_xml(llm_content)

            if not parsed_data:
                logger.warning(f"No XML tags found in LLM response, treating as plain text")
                parsed_data = {"content": llm_content.strip()}

            # Validate required fields if specified
            if config.required_fields:
                logger.debug(f"Validating required fields: {config.required_fields}")
                OutputParser.validate_output(parsed_data, config.required_fields)

            # DEBUG: Log parsed output for troubleshooting
            logger.info(f"=== {step_name.upper()} PARSED OUTPUT DEBUG ===")
            logger.info(f"Step: {step_name}")
            logger.info(f"Parsed Data Keys: {list(parsed_data.keys())}")
            logger.info(f"Full Parsed Data:\n{parsed_data}")
            logger.info(f"=== END {step_name.upper()} PARSED OUTPUT DEBUG ===")

            return parsed_data

        except (XMLParsingError, ValidationError) as e:
            logger.error(f"Output parsing or validation failed: {e}")
            raise OutputParsingError(f"Failed to parse or validate LLM output: {e}")

    def _build_step_result(
        self,
        step_name: str,
        parsed_output: Dict[str, Any],
        llm_response: Any,
        execution_time: float,
        config: StepConfig
    ) -> Dict[str, Any]:
        """Build the final step result with all metadata."""
        return {
            "step_name": step_name,
            "status": "success",
            "output": parsed_output,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "execution_time_seconds": execution_time,
                "model_info": {
                    "provider": config.provider,
                    "model": config.model,
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens
                },
                "usage": {
                    "tokens_used": llm_response.tokens_used,
                    "prompt_tokens": getattr(llm_response, 'prompt_tokens', None),
                    "completion_tokens": getattr(llm_response, 'completion_tokens', None)
                },
                "raw_response": {
                    "content_length": len(llm_response.content),
                    "content_preview": llm_response.content[:200] + "..." if len(llm_response.content) > 200 else llm_response.content
                }
            }
        }

    async def execute_initial_translation(
        self,
        translation_input: TranslationInput,
        config: StepConfig
    ) -> Dict[str, Any]:
        """
        Execute the initial translation step.

        Args:
            translation_input: Translation input data
            config: Step configuration

        Returns:
            Execution result with initial translation
        """
        input_data = {
            "original_poem": translation_input.original_poem,
            "source_lang": translation_input.source_lang,
            "target_lang": translation_input.target_lang
        }

        return await self.execute_step("initial_translation", input_data, config)

    async def execute_editor_review(
        self,
        initial_translation: InitialTranslation,
        translation_input: TranslationInput,
        config: StepConfig
    ) -> Dict[str, Any]:
        """
        Execute the editor review step.

        Args:
            initial_translation: Initial translation to review
            translation_input: Original translation input data
            config: Step configuration

        Returns:
            Execution result with editor suggestions
        """
        input_data = {
            "original_poem": translation_input.original_poem,
            "source_lang": translation_input.source_lang,
            "target_lang": translation_input.target_lang,
            "initial_translation": initial_translation.initial_translation,
            "initial_translation_notes": initial_translation.initial_translation_notes
        }

        return await self.execute_step("editor_review", input_data, config)

    async def execute_translator_revision(
        self,
        editor_review: EditorReview,
        translation_input: TranslationInput,
        initial_translation: InitialTranslation,
        config: StepConfig
    ) -> Dict[str, Any]:
        """
        Execute the translator revision step.

        Args:
            editor_review: Editor review with suggestions
            translation_input: Original translation input data
            initial_translation: Initial translation object
            config: Step configuration

        Returns:
            Execution result with revised translation
        """
        input_data = {
            "original_poem": translation_input.original_poem,
            "source_lang": translation_input.source_lang,
            "target_lang": translation_input.target_lang,
            "initial_translation": initial_translation.initial_translation,
            "initial_translation_notes": initial_translation.initial_translation_notes,
            "editor_suggestions": editor_review.editor_suggestions
        }

        return await self.execute_step("translator_revision", input_data, config)

    def __repr__(self) -> str:
        """String representation of the executor."""
        return f"StepExecutor(llm_factory={self.llm_factory}, prompt_service={self.prompt_service})"