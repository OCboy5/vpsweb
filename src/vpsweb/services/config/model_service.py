"""
Model Service - Domain-specific model and provider configuration access

This service provides high-level interfaces for accessing model and provider
configuration without directly manipulating the underlying YAML structure.
"""

import logging
from typing import Any, Dict, List, Optional

from ...models.config import ModelProviderConfig, ProvidersConfig

logger = logging.getLogger(__name__)


class ModelService:
    """
    Service for accessing model and provider configuration.

    Provides clean interfaces for:
    - Provider information and validation
    - Model availability and classification
    - Pricing information
    - Model selection and resolution
    """

    def __init__(self, providers_config: ProvidersConfig):
        """Initialize with providers configuration."""
        self._config = providers_config

    # Provider access and information
    def get_provider_names(self) -> List[str]:
        """Get list of available provider names."""
        return list(self._config.providers.keys())

    def get_provider_config(self, provider_name: str) -> ModelProviderConfig:
        """
        Get configuration for a specific provider.

        Args:
            provider_name: Name of the provider

        Returns:
            ModelProviderConfig object

        Raises:
            ValueError: If provider is not configured
        """
        if provider_name not in self._config.providers:
            available_providers = list(self._config.providers.keys())
            raise ValueError(
                f"Provider '{provider_name}' not found. "
                f"Available providers: {available_providers}"
            )
        return self._config.providers[provider_name]

    def get_provider_info(self, provider_name: str) -> Dict[str, Any]:
        """Get provider information in a dictionary format."""
        config = self.get_provider_config(provider_name)
        return {
            "name": provider_name,
            "api_key_env": config.api_key_env,
            "base_url": config.base_url,
            "type": config.type.value,
            "default_model": config.default_model,
            "available_models": config.models,
            "capabilities": {
                "reasoning": (
                    config.capabilities.reasoning if config.capabilities else False
                )
            },
        }

    # Model access and classification
    def get_available_models(self, provider_name: Optional[str] = None) -> List[str]:
        """
        Get list of available models.

        Args:
            provider_name: If specified, only return models from this provider

        Returns:
            List of model names
        """
        if provider_name:
            config = self.get_provider_config(provider_name)
            return config.models.copy()

        # Return all models from all providers
        all_models = []
        for provider_config in self._config.providers.values():
            all_models.extend(provider_config.models)
        return list(set(all_models))  # Remove duplicates

    def get_model_provider(self, model_name: str) -> str:
        """
        Find which provider has the specified model.

        Args:
            model_name: Name of the model to find

        Returns:
            Provider name

        Raises:
            ValueError: If model is not found in any provider
        """
        for provider_name, provider_config in self._config.providers.items():
            if model_name in provider_config.models:
                return provider_name

        raise ValueError(f"Model '{model_name}' not found in any provider")

    def get_default_model(self, provider_name: str) -> Optional[str]:
        """Get the default model for a provider."""
        config = self.get_provider_config(provider_name)
        return config.default_model

    def is_reasoning_model(self, model_name: str) -> bool:
        """
        Check if a model is classified as a reasoning model.

        Args:
            model_name: Name of the model

        Returns:
            True if the model is a reasoning model
        """
        # First check model_classification if available
        if self._config.model_classification:
            reasoning_models = self._config.model_classification.get(
                "reasoning_models", []
            )
            if model_name in reasoning_models:
                return True

        # Fall back to provider capabilities
        try:
            provider_name = self.get_model_provider(model_name)
            provider_config = self.get_provider_config(provider_name)
            return (
                provider_config.capabilities.reasoning
                if provider_config.capabilities
                else False
            )
        except ValueError:
            return False

    def get_model_classification(self) -> Dict[str, List[str]]:
        """Get model classification (reasoning vs non_reasoning)."""
        if not self._config.model_classification:
            # Build classification from provider capabilities
            reasoning_models = []
            non_reasoning_models = []

            for (
                provider_name,
                provider_config,
            ) in self._config.providers.items():
                if (
                    provider_config.capabilities
                    and provider_config.capabilities.reasoning
                ):
                    reasoning_models.extend(provider_config.models)
                else:
                    non_reasoning_models.extend(provider_config.models)

            return {
                "reasoning_models": list(set(reasoning_models)),
                "non_reasoning_models": list(set(non_reasoning_models)),
            }

        return self._config.model_classification

    # Pricing information
    def get_pricing_info(self, model_name: str) -> Dict[str, float]:
        """
        Get pricing information for a model.

        Args:
            model_name: Name of the model

        Returns:
            Dictionary with input and output pricing per 1K tokens
        """
        if not self._config.pricing:
            return {"input": 0.0, "output": 0.0}

        # Try to find exact model match
        for provider_name, pricing_info in self._config.pricing.items():
            if model_name in pricing_info:
                return pricing_info[model_name]

        # Try to find provider-level pricing
        try:
            provider_name = self.get_model_provider(model_name)
            if provider_name in self._config.pricing:
                return self._config.pricing[provider_name]
        except ValueError:
            pass

        return {"input": 0.0, "output": 0.0}

    def get_all_pricing_info(self) -> Dict[str, Dict[str, float]]:
        """Get all pricing information organized by model."""
        all_pricing = {}

        if self._config.pricing:
            for provider_name, pricing_info in self._config.pricing.items():
                if isinstance(pricing_info, dict):
                    # Check if this is model-specific pricing or provider-level
                    if any(isinstance(v, dict) for v in pricing_info.values()):
                        # Model-specific pricing
                        all_pricing.update(pricing_info)
                    else:
                        # Provider-level pricing - apply to all models in provider
                        if provider_name in self._config.providers:
                            for model in self._config.providers[provider_name].models:
                                all_pricing[model] = pricing_info

        return all_pricing

    # Global provider settings
    def get_global_settings(self) -> Dict[str, Any]:
        """Get global provider settings."""
        return self._config.provider_settings or {}

    def get_reasoning_settings(self) -> Dict[str, Any]:
        """Get reasoning-specific settings."""
        return self._config.reasoning_settings or {}

    # BBR and special task configurations
    def get_bbr_generation_config(self) -> Optional[Dict[str, Any]]:
        """Get BBR generation configuration."""
        return self._config.bbr_generation

    def get_wechat_translation_notes_config(self) -> Optional[Dict[str, Any]]:
        """Get WeChat translation notes configuration."""
        return getattr(self._config, "wechat_translation_notes", None)

    def get_wechat_article_generation_config(self) -> Optional[Dict[str, Any]]:
        """Get WeChat article generation configuration."""
        if hasattr(self._config, "wechat") and self._config.wechat:
            if hasattr(self._config.wechat, "article_generation"):
                return self._config.wechat.article_generation.model_dump()

        # Return default config if not found
        return {
            "include_translation_notes": True,
            "copyright_text": "【著作权声明】\n本译文与译注完全由知韵(VoxPoetica)AI工具生成制作，仅供学习交流使用。原作品版权归原作者所有，如有侵权请联系删除。翻译内容未经授权，不得转载、不得用于商业用途。若需引用，请注明出处。",
            "article_template": "codebuddy",
            "default_cover_image_path": "config/html_templates/cover_image_big.jpg",
            "default_local_cover_image_name": "cover_image_big.jpg",
            "model_type": "non_reasoning",
        }

    # Validation and utility methods
    def validate_providers(self) -> List[str]:
        """Validate provider configuration and return any errors."""
        errors = []

        if not self._config.providers:
            errors.append("No providers configured")
            return errors

        for provider_name, provider_config in self._config.providers.items():
            # Check required fields
            if not provider_config.api_key_env:
                errors.append(f"Provider {provider_name} missing api_key_env")

            if not provider_config.base_url:
                errors.append(f"Provider {provider_name} missing base_url")

            if not provider_config.models:
                errors.append(f"Provider {provider_name} has no models configured")
                continue

            # Validate default model
            if (
                provider_config.default_model
                and provider_config.default_model not in provider_config.models
            ):
                errors.append(
                    f"Provider {provider_name} default_model '{provider_config.default_model}' "
                    f"not in available models: {provider_config.models}"
                )

        return errors

    def get_provider_models_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get a summary of all providers and their models."""
        summary = {}
        for provider_name, provider_config in self._config.providers.items():
            summary[provider_name] = {
                "model_count": len(provider_config.models),
                "models": provider_config.models,
                "default_model": provider_config.default_model,
                "reasoning_capable": (
                    provider_config.capabilities.reasoning
                    if provider_config.capabilities
                    else False
                ),
            }
        return summary
