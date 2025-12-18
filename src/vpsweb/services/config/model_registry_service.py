"""
Model Registry Service for VPSWeb.

This service provides access to the pure model registry, allowing resolution
of model references to actual provider configurations and model information.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Model information from the model registry."""

    model_ref: str
    provider: str
    name: str
    reasoning: bool
    description: str


@dataclass
class ProviderInfo:
    """Provider information from the model registry."""

    name: str
    api_key_env: str
    base_url: str
    type: str
    models: List[str]


class ModelRegistryService:
    """
    Service for accessing model registry information.

    Provides model resolution, provider information, and pricing data
    based on the simplified model registry structure.
    """

    def __init__(self, models_config: Dict[str, Any]):
        """
        Initialize model registry service.

        Args:
            models_config: The models.yaml configuration dictionary
        """
        self._models_config = models_config
        self._providers = models_config.get("providers", {})
        self._models = models_config.get("models", {})
        self._pricing = models_config.get("pricing", {})
        self._provider_settings = models_config.get("provider_settings", {})
        self._reasoning_settings = models_config.get("reasoning_settings", {})

        logger.info(
            f"ModelRegistryService initialized with {len(self._models)} models"
        )

    def get_model_info(self, model_ref: str) -> ModelInfo:
        """
        Get complete model information by reference.

        Args:
            model_ref: The model reference (e.g., "qwen3_plus")

        Returns:
            ModelInfo object with model details

        Raises:
            ValueError: If model_ref is not found
        """
        if model_ref not in self._models:
            raise ValueError(
                f"Model reference '{model_ref}' not found in model registry"
            )

        model_data = self._models[model_ref]
        return ModelInfo(
            model_ref=model_ref,
            provider=model_data["provider"],
            name=model_data["name"],
            reasoning=model_data.get("reasoning", False),
            description=model_data.get("description", ""),
        )

    def list_providers(self) -> List[str]:
        """
        Get list of all available providers.

        Returns:
            List of provider names
        """
        return list(self._models_config.get("providers", {}).keys())

    def get_provider_info(self, provider_name: str) -> ProviderInfo:
        """
        Get provider configuration.

        Args:
            provider_name: Name of the provider (e.g., "tongyi")

        Returns:
            ProviderInfo object with provider details

        Raises:
            ValueError: If provider is not found
        """
        if provider_name not in self._providers:
            raise ValueError(
                f"Provider '{provider_name}' not found in model registry"
            )

        provider_data = self._providers[provider_name]

        # Get all models for this provider
        provider_models = [
            model_name
            for model_name, model_info in self._models.items()
            if model_info.get("provider") == provider_name
        ]

        return ProviderInfo(
            name=provider_name,
            api_key_env=provider_data["api_key_env"],
            base_url=provider_data["base_url"],
            type=provider_data["type"],
            models=provider_models,
        )

    def get_model_pricing(self, model_ref: str) -> Dict[str, float]:
        """
        Get pricing information for a model.

        Args:
            model_ref: The model reference (e.g., "qwen3_plus")

        Returns:
            Dictionary with 'input' and 'output' pricing per 1K tokens

        Raises:
            ValueError: If model_ref is not found or has no pricing
        """
        if model_ref not in self._pricing:
            raise ValueError(
                f"No pricing information found for model '{model_ref}'"
            )

        return self._pricing[model_ref].copy()

    def resolve_model_reference(self, model_ref: str) -> Tuple[str, str]:
        """
        Resolve model reference to (provider, actual_model_name).

        Args:
            model_ref: The model reference (e.g., "qwen3_plus")

        Returns:
            Tuple of (provider_name, model_name)

        Raises:
            ValueError: If model_ref is not found
        """
        model_info = self.get_model_info(model_ref)
        return model_info.provider, model_info.name

    def list_reasoning_models(self) -> List[str]:
        """
        Get all reasoning model references.

        Returns:
            List of model references that have reasoning capability
        """
        return [
            model_ref
            for model_ref, model_data in self._models.items()
            if model_data.get("reasoning", False)
        ]

    def list_non_reasoning_models(self) -> List[str]:
        """
        Get all non-reasoning model references.

        Returns:
            List of model references that do not have reasoning capability
        """
        return [
            model_ref
            for model_ref, model_data in self._models.items()
            if not model_data.get("reasoning", False)
        ]

    def get_all_models(self) -> List[str]:
        """
        Get all available model references.

        Returns:
            List of all model references in the registry
        """
        return list(self._models.keys())

    def get_provider_settings(
        self,
        provider_name: Optional[str] = None,
        reasoning: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Get provider settings, with optional reasoning-specific overrides.

        Args:
            provider_name: Specific provider name (optional)
            reasoning: Whether this is for a reasoning model (optional)

        Returns:
            Dictionary of provider settings
        """
        settings = self._provider_settings.copy()

        # Apply reasoning-specific settings if requested
        if reasoning and self._reasoning_settings:
            settings.update(self._reasoning_settings)

        return settings

    def is_reasoning_model(self, model_ref: str) -> bool:
        """
        Check if a model is a reasoning model.

        Args:
            model_ref: The model reference to check

        Returns:
            True if the model has reasoning capability
        """
        try:
            model_info = self.get_model_info(model_ref)
            return model_info.reasoning
        except ValueError:
            return False

    def get_model_description(self, model_ref: str) -> str:
        """
        Get model description.

        Args:
            model_ref: The model reference

        Returns:
            Model description string
        """
        try:
            model_info = self.get_model_info(model_ref)
            return model_info.description
        except ValueError:
            return f"Unknown model: {model_ref}"

    def calculate_cost(
        self, model_ref: str, input_tokens: int, output_tokens: int
    ) -> float:
        """
        Calculate cost for using a model.

        Args:
            model_ref: The model reference
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Total cost in RMB

        Raises:
            ValueError: If model has no pricing information
        """
        pricing = self.get_model_pricing(model_ref)
        input_cost = (input_tokens / 1000) * pricing.get("input", 0)
        output_cost = (output_tokens / 1000) * pricing.get("output", 0)
        return input_cost + output_cost

    def find_model_ref_by_name(self, model_name: str) -> Optional[str]:
        """
        Find model reference by actual model name.

        Args:
            model_name: The actual model name (e.g., "qwen-plus-latest")

        Returns:
            Model reference if found, None otherwise
        """
        for model_ref, model_info in self._models.items():
            if model_info.get("name") == model_name:
                return model_ref
        return None

    def build_name_to_reference_mapping(self) -> Dict[str, str]:
        """
        Build a mapping from model names to model references.

        This creates an efficient lookup dictionary that can be used
        to convert actual model names to their corresponding references.

        Returns:
            Dictionary mapping model names to model references
        """
        name_to_ref = {}
        for model_ref, model_info in self._models.items():
            model_name = model_info.get("name")
            if model_name:
                name_to_ref[model_name] = model_ref
        return name_to_ref

    def validate_model_ref(self, model_ref: str) -> bool:
        """
        Validate that a model reference exists in the registry.

        Args:
            model_ref: The model reference to validate

        Returns:
            True if the model reference exists
        """
        return model_ref in self._models

    def __repr__(self) -> str:
        """String representation of the model registry service."""
        return f"ModelRegistryService(models={len(self._models)}, providers={len(self._providers)})"
