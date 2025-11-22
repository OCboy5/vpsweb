"""
Background Briefing Report (BBR) Generator Service for VPSWeb.

This module provides a service for generating AI-powered Background Briefing Reports
for poems to enhance translation quality in the V2 workflow.
"""

import json
import time
import uuid
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

from .llm.factory import LLMFactory
from .prompts import PromptService
from ..repository.models import BackgroundBriefingReport
from ..services.config import get_config_facade, ConfigFacade
from ..models.config import ProvidersConfig
from ..utils.text_processing import count_effective_lines, add_line_labels, detect_stanza_structure

logger = logging.getLogger(__name__)

# Define UTC+8 timezone
UTC_PLUS_8 = timezone(timedelta(hours=8))


class BBRGeneratorError(Exception):
    """Base exception for BBR generation errors."""

    pass


class BBRLoadError(BBRGeneratorError):
    """Raised when BBR loading fails."""

    pass


class BBRGenerationError(BBRGeneratorError):
    """Raised when BBR generation fails."""

    pass


class BBRValidationError(BBRGeneratorError):
    """Raised when BBR validation fails."""

    pass


class BBRGenerator:
    """
    Service for generating and managing Background Briefing Reports.

    This service integrates with LLM providers and prompt templates to generate
    comprehensive background reports for poems, including proper cost tracking
    and time measurement.
    """

    def __init__(
        self,
        llm_factory: LLMFactory,
        prompt_service: PromptService,
        providers_config: Optional[ProvidersConfig] = None,
        config_facade: Optional[ConfigFacade] = None,
    ):
        """
        Initialize the BBR generator service.

        Args:
            llm_factory: LLM provider factory for model access
            prompt_service: Prompt service for template rendering
            providers_config: Legacy Provider configurations for cost calculation (deprecated)
            config_facade: New ConfigFacade instance for configuration access
        """
        self.llm_factory = llm_factory
        self.prompt_service = prompt_service

        # Support both legacy and ConfigFacade patterns
        if config_facade is not None:
            self._config_facade = config_facade
            self._using_facade = True
        else:
            # Try to get from global ConfigFacade
            try:
                self._config_facade = get_config_facade()
                self._using_facade = True
            except RuntimeError:
                # Fall back to legacy pattern
                if providers_config is None:
                    raise ValueError(
                        "Either providers_config or config_facade must be provided"
                    )
                self.providers_config = providers_config
                self._using_facade = False
                self._config_facade = None

        self.bbr_config = self._get_bbr_config()
        logger.info("Initialized BBR generator service")

    def _get_bbr_config(self) -> Dict[str, Any]:
        """
        Get BBR generation configuration.

        Returns:
            BBR configuration dictionary

        Raises:
            BBRGeneratorError: If BBR configuration is not found
        """
        if self._using_facade:
            # Use ConfigFacade to get BBR config from task templates
            try:
                return self._config_facade.get_bbr_config()
            except (RuntimeError, ValueError) as e:
                logger.warning(f"Could not get BBR config from task templates: {e}")
                # Fallback to hardcoded config
                pass
        else:
            # Legacy pattern
            if hasattr(self.providers_config, "bbr_generation"):
                return self.providers_config.bbr_generation

        # Fallback to hardcoded config if not found
        logger.warning("BBR config not found, using defaults")
        return {
            "provider": "tongyi",
            "model": "qwen-plus-latest",
            "temperature": 0.3,
            "max_tokens": 16384,
            "prompt_template": "background_briefing_report",
            "timeout": 180.0,
            "retry_attempts": 2,
        }

    async def generate_bbr(
        self,
        poem_id: str,
        poem_content: str,
        poet_name: str,
        poem_title: str,
        source_language: Optional[str] = None,
    ) -> BackgroundBriefingReport:
        """
        Generate a Background Briefing Report for a poem.

        Args:
            poem_id: Unique identifier for the poem
            poem_content: Full text of the poem
            poet_name: Name of the poet
            poem_title: Title of the poem
            source_language: Source language of the poem (optional)

        Returns:
            BackgroundBriefingReport with generated content and metadata

        Raises:
            BBRGenerationError: If generation fails
            BBRValidationError: If generated BBR is invalid
        """
        logger.info(f"Generating BBR for poem '{poem_title}' by {poet_name}")
        start_time = time.time()

        try:
            # Get provider and model configuration
            provider_name = self.bbr_config["provider"]
            model_name = self.bbr_config["model"]

            # Get provider instance
            provider = self.llm_factory.get_provider(provider_name)
            logger.debug(f"Using provider: {provider_name}, model: {model_name}")

            # Prepare prompt variables
            def get_friendly_language_name(lang_code):
                """Convert language code to friendly name."""
                if not lang_code:
                    return "Unknown"
                lang_code = lang_code.lower()
                if lang_code in ["en", "english"]:
                    return "English"
                elif lang_code in ["zh", "zh-cn", "zh-tw", "chinese"]:
                    return "Chinese"
                elif lang_code in ["fr", "french"]:
                    return "French"
                elif lang_code in ["de", "german"]:
                    return "German"
                elif lang_code in ["es", "spanish"]:
                    return "Spanish"
                else:
                    return lang_code.upper()

            friendly_source_lang = get_friendly_language_name(source_language)
            target_lang = "Chinese" if friendly_source_lang == "English" else "English"

            from vpsweb.utils.text_processing import (
                add_line_labels,
                count_effective_lines,
            )

            # Compute effective lines, stanza structure, and add line labels
            effective_lines = count_effective_lines(poem_content)
            stanza_structure = detect_stanza_structure(poem_content)
            labeled_source_text = add_line_labels(poem_content)

            variables = {
                "poet_name": poet_name,
                "poem_title": poem_title,
                "source_text": labeled_source_text,
                "source_lang": friendly_source_lang,
                "target_lang": target_lang,
                "effective_lines": effective_lines,
                "stanza_structure": stanza_structure,
            }

            # Render prompt template
            template_name = self.bbr_config["prompt_template"]
            system_prompt, user_prompt = self.prompt_service.render_prompt(
                template_name, variables
            )
            logger.debug(
                f"Rendered prompts: system({len(system_prompt)} chars), user({len(user_prompt)} chars)"
            )

            # Generate BBR content
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = await provider.generate(
                messages=messages,
                model=model_name,
                temperature=self.bbr_config["temperature"],
                max_tokens=self.bbr_config["max_tokens"],
            )

            # Calculate time spent
            time_spent = time.time() - start_time

            # Extract content and metadata
            bbr_content = response.content
            tokens_used = response.tokens_used
            input_tokens = response.prompt_tokens
            output_tokens = response.completion_tokens

            # Validate BBR content
            validated_content = self._validate_bbr_content(bbr_content)

            # Calculate cost
            cost = self.calculate_cost(
                input_tokens, output_tokens, provider_name, model_name
            )

            # Create BackgroundBriefingReport object
            bbr = BackgroundBriefingReport(
                id=str(uuid.uuid4()),
                poem_id=poem_id,
                content=json.dumps(validated_content, ensure_ascii=False, indent=2),
                model_info=json.dumps(
                    {
                        "provider": provider_name,
                        "model": model_name,
                        "temperature": self.bbr_config["temperature"],
                        "max_tokens": self.bbr_config["max_tokens"],
                        "prompt_template": template_name,
                    }
                ),
                tokens_used=tokens_used,
                cost=cost,
                time_spent=time_spent,
                created_at=datetime.now(UTC_PLUS_8),
                updated_at=datetime.now(UTC_PLUS_8),
            )

            logger.info(
                f"Successfully generated BBR in {time_spent:.2f}s, "
                f"tokens: {tokens_used}, cost: {cost:.4f}"
            )
            return bbr

        except Exception as e:
            time_spent = time.time() - start_time
            logger.error(f"BBR generation failed after {time_spent:.2f}s: {e}")
            raise BBRGenerationError(f"Failed to generate BBR: {e}")

    def get_bbr(self, poem_id: str) -> Optional[BackgroundBriefingReport]:
        """
        Retrieve an existing Background Briefing Report.

        Args:
            poem_id: ID of the poem to get BBR for

        Returns:
            BackgroundBriefingReport if found, None otherwise

        Raises:
            BBRLoadError: If loading fails
        """
        # This method would typically query the database
        # For now, returning None as placeholder
        # Implementation would be added in database service layer
        logger.debug(f"Looking for BBR for poem_id: {poem_id}")
        return None

    async def delete_bbr(self, poem_id: str) -> bool:
        """
        Delete a Background Briefing Report.

        Args:
            poem_id: ID of the poem to delete BBR for

        Returns:
            True if deleted successfully, False otherwise

        Raises:
            BBRLoadError: If deletion fails
        """
        try:
            logger.info(f"Deleting BBR for poem_id: {poem_id}")
            # This method would typically delete from database
            # For now, returning True as placeholder
            # Implementation would be added in database service layer
            return True
        except Exception as e:
            logger.error(f"Failed to delete BBR for poem_id {poem_id}: {e}")
            raise BBRLoadError(f"Failed to delete BBR: {e}")

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        provider_name: str,
        model_name: str,
    ) -> float:
        """
        Calculate cost for BBR generation.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            provider_name: Name of the provider used
            model_name: Name of the model used

        Returns:
            Calculated cost in RMB

        Raises:
            BBRGeneratorError: If pricing information is not available
        """
        try:
            # Try to find model reference from model name for pricing lookup
            if self._using_facade and hasattr(self._config_facade, "model_registry"):
                # New pattern: find model reference from actual model name
                model_ref = self._config_facade.model_registry.find_model_ref_by_name(
                    model_name
                )
                if model_ref:
                    # Use the model registry calculate_cost method
                    return self._config_facade.model_registry.calculate_cost(
                        model_ref, input_tokens, output_tokens
                    )
                else:
                    logger.warning(
                        f"Model reference not found for model name: {model_name}"
                    )
                    return 0.0
            else:
                # Legacy pattern - try to convert model name to model reference
                if (
                    hasattr(self.providers_config, "pricing")
                    and self.providers_config.pricing
                ):
                    pricing = self.providers_config.pricing
                else:
                    pricing = {}

                # Try to find model reference that corresponds to this model name
                model_ref = self._find_model_reference_dynamically(model_name)

                # First try model reference, then fall back to model name
                if model_ref and model_ref in pricing:
                    model_pricing = pricing[model_ref]
                    logger.debug(
                        f"Found pricing for model {model_name} using reference {model_ref}"
                    )
                elif model_name in pricing:
                    model_pricing = pricing[model_name]
                    logger.debug(f"Found pricing for model {model_name} directly")
                else:
                    logger.warning(
                        f"No pricing information found for model {model_name} (tried ref: {model_ref})"
                    )
                    return 0.0

                # Pricing is RMB per 1K tokens
                input_cost = (input_tokens / 1000) * model_pricing.get("input", 0)
                output_cost = (output_tokens / 1000) * model_pricing.get("output", 0)
                total_cost = input_cost + output_cost
                logger.debug(
                    f"Cost calculation: input={input_cost:.4f}, output={output_cost:.4f}, total={total_cost:.4f}"
                )
                return total_cost

        except Exception as e:
            logger.warning(
                f"Failed to calculate cost for {provider_name}/{model_name}: {e}"
            )
            return 0.0

    def _find_model_reference_dynamically(self, model_name: str) -> Optional[str]:
        """
        Find model reference dynamically using exact matching from model registry.

        This method tries to access the actual model registry configuration
        to perform exact matching from model name to model reference.

        Args:
            model_name: The actual model name (e.g., "qwen-plus-latest")

        Returns:
            Model reference if found, None otherwise
        """
        # Try to use ConfigFacade model registry if available (preferred approach)
        if self._using_facade and hasattr(self._config_facade, "model_registry"):
            model_ref = self._config_facade.model_registry.find_model_ref_by_name(
                model_name
            )
            if model_ref:
                logger.debug(
                    f"Found model reference {model_ref} for {model_name} via ConfigFacade"
                )
                return model_ref

        # Fallback: Try to load model registry directly
        try:
            from ..utils.config_loader import load_model_registry_config

            models_config = load_model_registry_config()

            # Build temporary mapping from the loaded models config
            for ref, info in models_config.get("models", {}).items():
                if info.get("name") == model_name:
                    logger.debug(
                        f"Found model reference {ref} for {model_name} via direct config load"
                    )
                    return ref

        except Exception as e:
            logger.warning(f"Failed to load model registry for reference lookup: {e}")

        # Final fallback: Return None if no exact match found
        logger.warning(f"No exact match found for model name: {model_name}")
        return None

    def _validate_bbr_content(self, content: str) -> Dict[str, Any]:
        """
        Validate and parse BBR content.

        Args:
            content: Raw BBR content from LLM

        Returns:
            Validated BBR content as dictionary

        Raises:
            BBRValidationError: If content is invalid
        """
        try:
            # Try to parse as JSON first
            if content.strip().startswith("{"):
                parsed_content = json.loads(content)
                self._validate_bbr_schema(parsed_content)
                return parsed_content

            # If not JSON, try to extract JSON from content
            import re

            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                parsed_content = json.loads(json_match.group())
                self._validate_bbr_schema(parsed_content)
                return parsed_content

            # If no valid JSON found, wrap in basic structure
            logger.warning(
                "No valid JSON found in BBR content, wrapping in basic structure"
            )
            return {
                "raw_content": content,
                "generation_timestamp": datetime.now(UTC_PLUS_8).isoformat(),
                "validation_warning": "Content could not be parsed as valid JSON schema",
            }

        except json.JSONDecodeError as e:
            raise BBRValidationError(f"Invalid JSON in BBR content: {e}")
        except Exception as e:
            raise BBRValidationError(f"BBR content validation failed: {e}")

    def _validate_bbr_schema(self, content: Dict[str, Any]) -> None:
        """
        Validate BBR content against expected schema.

        Args:
            content: BBR content dictionary

        Raises:
            BBRValidationError: If schema validation fails
        """
        # Check for required top-level fields
        required_fields = ["text_anchor", "poet_style", "thematic_analysis"]
        missing_fields = [field for field in required_fields if field not in content]

        if missing_fields:
            logger.warning(f"Missing recommended BBR fields: {missing_fields}")
            # Don't raise error for now, just warn
            # raise BBRValidationError(f"Missing required BBR fields: {missing_fields}")

        # Validate text_anchor
        if "text_anchor" in content:
            text_anchor = content["text_anchor"]
            if not isinstance(text_anchor, dict):
                raise BBRValidationError("text_anchor must be a dictionary")

            if "lines" in text_anchor and not isinstance(text_anchor["lines"], int):
                raise BBRValidationError("text_anchor.lines must be an integer")

        # Log validation success
        logger.debug("BBR content schema validation passed")

    def get_supported_languages(self) -> list[str]:
        """
        Get list of supported source languages for BBR generation.

        Returns:
            List of supported language codes
        """
        return [
            "English",
            "Chinese",
            "Japanese",
            "Korean",
            "French",
            "Spanish",
            "German",
        ]

    def estimate_generation_time(self, poem_length: int) -> float:
        """
        Estimate BBR generation time based on poem length.

        Args:
            poem_length: Length of poem in characters

        Returns:
            Estimated generation time in seconds
        """
        # Base time plus scaling factor for poem length
        base_time = 30.0  # 30 seconds base
        length_factor = poem_length / 1000.0  # Scale per 1000 characters
        estimated_time = base_time + (length_factor * 20.0)  # 20s per 1000 chars

        # Cap at reasonable maximum
        return min(estimated_time, 300.0)  # Max 5 minutes

    def __repr__(self) -> str:
        """String representation of the BBR generator."""
        return (
            f"BBRGenerator(provider='{self.bbr_config['provider']}', "
            f"model='{self.bbr_config['model']}')"
        )
