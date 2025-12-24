"""
LLM Provider Factory for creating and managing provider instances.

This module provides a factory pattern for creating LLM provider instances
based on configuration, with caching and error handling.
"""

import logging
import os
from typing import Any, Dict, Optional

from ...models.config import ModelProviderConfig
from ...services.config import ConfigFacade, get_config_facade
from .base import BaseLLMProvider, ConfigurationError, ProviderType
from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class LLMFactory:
    """
    Factory for creating and managing LLM provider instances.

    This factory reads provider configurations and creates appropriate
    provider instances with caching for performance.
    """

    def __init__(
        self,
        providers_config_or_facade: Optional[Any] = None,
        config_facade: Optional[ConfigFacade] = None,
    ):
        """
        Initialize the LLM factory with provider configurations.

        Args:
            providers_config_or_facade: Legacy ProvidersConfig (deprecated, use config_facade instead)
            config_facade: New ConfigFacade instance for configuration access
        """
        if config_facade is not None:
            # New ConfigFacade-based initialization
            self._config_facade = config_facade
            # Check if we're using the new model registry structure
            if hasattr(config_facade, "_using_new_structure") and config_facade._using_new_structure:
                # New model registry structure - don't use legacy providers_config
                self.providers_config = None
                self._using_new_structure = True
            else:
                # Legacy structure with ConfigFacade
                self.providers_config = config_facade.providers
                self._using_new_structure = False
            self._using_facade = True
        else:
            # Legacy initialization for backward compatibility
            if providers_config_or_facade is None:
                # Try to get from global ConfigFacade
                try:
                    config_facade = get_config_facade()
                    self._config_facade = config_facade
                    # Check if we're using the new model registry structure
                    if hasattr(config_facade, "_using_new_structure") and config_facade._using_new_structure:
                        # New model registry structure
                        self.providers_config = None
                        self._using_new_structure = True
                    else:
                        # Legacy structure
                        self.providers_config = config_facade.providers
                        self._using_new_structure = False
                    self._using_facade = True
                except RuntimeError:
                    raise ConfigurationError(
                        "No configuration provided. Either pass providers_config or config_facade, or initialize ConfigFacade first."
                    )
            else:
                self.providers_config = providers_config_or_facade
                self._using_facade = False
                self._using_new_structure = False
                self._config_facade = None

        self._provider_cache: Dict[str, BaseLLMProvider] = {}

        # Log initialization with proper provider count
        if self._using_new_structure:
            provider_count = len(self._config_facade.model_registry.list_providers())
            logger.info(f"Initialized LLMFactory with {provider_count} providers from model registry")
        else:
            provider_count = len(self.providers_config.providers) if self.providers_config else 0
            logger.info(f"Initialized LLMFactory with {provider_count} providers from legacy config")

    def get_provider(self, provider_name: str) -> BaseLLMProvider:
        """
        Get a provider instance by name.

        Args:
            provider_name: Name of the provider (e.g., 'tongyi', 'deepseek')

        Returns:
            Provider instance

        Raises:
            ConfigurationError: If provider is not configured
            AuthenticationError: If API key is not available
        """
        if provider_name in self._provider_cache:
            logger.debug(f"Returning cached provider: {provider_name}")
            return self._provider_cache[provider_name]

        # Get provider config (this will handle both new and legacy structures)
        provider_config = self.get_provider_config(provider_name)
        provider = self._create_provider(provider_name, provider_config)

        # Cache the provider instance
        self._provider_cache[provider_name] = provider
        logger.info(f"Created and cached provider: {provider_name}")

        return provider

    def get_provider_config(self, provider_name: str) -> ModelProviderConfig:
        """
        Get configuration for a specific provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Provider configuration

        Raises:
            ConfigurationError: If provider is not configured
        """
        # Handle new model registry structure
        if self._using_new_structure and self._config_facade:
            try:
                # Get provider info from model registry
                provider_info = self._config_facade.model_registry.get_provider_info(provider_name)
                # Create ModelProviderConfig from registry data
                return ModelProviderConfig(
                    api_key_env=provider_info.api_key_env,
                    base_url=provider_info.base_url,
                    type=provider_info.type,
                    models=provider_info.models,  # This will be a list of model names
                    default_model=(provider_info.models[0] if provider_info.models else None),
                )
            except ValueError as e:
                available_providers = self._config_facade.model_registry.list_providers()
                raise ConfigurationError(
                    f"Provider '{provider_name}' not found in configuration. "
                    f"Available providers: {available_providers}",
                    provider=provider_name,
                ) from e

        # Legacy structure
        if self.providers_config is None:
            raise ConfigurationError(
                f"No provider configuration available for provider '{provider_name}'",
                provider=provider_name,
            )

        if provider_name not in self.providers_config.providers:
            available_providers = list(self.providers_config.providers.keys())
            raise ConfigurationError(
                f"Provider '{provider_name}' not found in configuration. "
                f"Available providers: {available_providers}",
                provider=provider_name,
            )
        return self.providers_config.providers[provider_name]

    def _create_provider(self, provider_name: str, config: ModelProviderConfig) -> BaseLLMProvider:
        """
        Create a provider instance from configuration.

        Args:
            provider_name: Name of the provider
            config: Provider configuration

        Returns:
            Provider instance

        Raises:
            ConfigurationError: If provider type is not supported
            AuthenticationError: If API key is not available
        """
        logger.debug(f"Creating provider: {provider_name} with type: {config.type}")

        # Get API key from environment variable
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            from .base import AuthenticationError

            raise AuthenticationError(
                f"API key not found for provider '{provider_name}'. "
                f"Please set the environment variable: {config.api_key_env}",
                provider=provider_name,
            )

        # Get global provider settings
        if self._using_new_structure:
            # New model registry structure - no global provider settings available yet
            global_settings = {}
        else:
            # Legacy structure
            global_settings = self.providers_config.provider_settings or {}

        # Create provider based on type
        if config.type == ProviderType.OPENAI_COMPATIBLE:
            return self._create_openai_compatible_provider(
                provider_name=provider_name,
                base_url=config.base_url,
                api_key=api_key,
                global_settings=global_settings,
            )
        else:
            raise ConfigurationError(
                f"Unsupported provider type: {config.type}. " f"Supported types: {[t.value for t in ProviderType]}",
                provider=provider_name,
            )

    def _create_openai_compatible_provider(
        self,
        provider_name: str,
        base_url: str,
        api_key: str,
        global_settings: Dict[str, Any],
    ) -> OpenAICompatibleProvider:
        """
        Create an OpenAI-compatible provider instance.

        Args:
            provider_name: Name of the provider
            base_url: Base URL for the API
            api_key: API key
            global_settings: Global provider settings

        Returns:
            OpenAICompatibleProvider instance
        """
        provider_settings = {
            "timeout": global_settings.get("timeout", 120.0),
            "max_retries": global_settings.get("max_retries", 3),
            "retry_delay": global_settings.get("retry_delay", 1.0),
            "request_timeout": global_settings.get("request_timeout", 30.0),
            "connection_pool_size": global_settings.get("connection_pool_size", 10),
        }

        return OpenAICompatibleProvider(base_url=base_url, api_key=api_key, **provider_settings)

    def get_supported_models(self, provider_name: str) -> list[str]:
        """
        Get list of supported models for a specific provider.

        Args:
            provider_name: Name of the provider

        Returns:
            List of supported model names

        Raises:
            ConfigurationError: If provider is not configured
        """
        provider_config = self.get_provider_config(provider_name)
        return provider_config.models

    def get_default_model(self, provider_name: str) -> Optional[str]:
        """
        Get the default model for a specific provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Default model name, or None if not specified

        Raises:
            ConfigurationError: If provider is not configured
        """
        provider_config = self.get_provider_config(provider_name)
        return provider_config.default_model

    def validate_provider_config(self, provider_name: str) -> bool:
        """
        Validate configuration for a specific provider.

        Args:
            provider_name: Name of the provider

        Returns:
            True if configuration is valid

        Raises:
            ConfigurationError: If configuration is invalid
        """
        provider_config = self.get_provider_config(provider_name)
        provider = self.get_provider(provider_name)
        return provider.validate_config(provider_config)

    def get_all_providers(self) -> Dict[str, BaseLLMProvider]:
        """
        Get all configured providers.

        Returns:
            Dictionary mapping provider names to instances
        """
        providers = {}
        # Get list of providers based on structure
        if self._using_new_structure:
            provider_names = self._config_facade.model_registry.list_providers()
        else:
            provider_names = list(self.providers_config.providers.keys()) if self.providers_config else []

        for provider_name in provider_names:
            try:
                providers[provider_name] = self.get_provider(provider_name)
            except Exception as e:
                logger.warning(f"Failed to create provider '{provider_name}': {e}")
        return providers

    def clear_cache(self) -> None:
        """
        Clear the provider cache.
        """
        self._provider_cache.clear()
        logger.info("Cleared provider cache")

    def refresh_provider(self, provider_name: str) -> BaseLLMProvider:
        """
        Refresh a provider instance (clear cache and recreate).

        Args:
            provider_name: Name of the provider to refresh

        Returns:
            Fresh provider instance
        """
        if provider_name in self._provider_cache:
            del self._provider_cache[provider_name]
            logger.info(f"Cleared cached provider: {provider_name}")

        return self.get_provider(provider_name)

    @classmethod
    def from_config_file(cls, config_path: str) -> "LLMFactory":
        """
        Create an LLM factory from a configuration file.

        Args:
            config_path: Path to the models.yaml configuration file

        Returns:
            LLMFactory instance

        Raises:
            ConfigurationError: If configuration file is invalid
        """
        from ...utils.config_loader import load_providers_config

        logger.info(f"Creating LLMFactory from config file: {config_path}")
        providers_config = load_providers_config(config_path)
        return cls(providers_config)

    def __repr__(self) -> str:
        """String representation of the factory."""
        if self._using_new_structure:
            provider_names = self._config_facade.model_registry.list_providers()
        else:
            provider_names = list(self.providers_config.providers.keys()) if self.providers_config else []
        return f"LLMFactory(providers={provider_names}, cached={len(self._provider_cache)})"


# Convenience function for creating a factory from configuration
def create_llm_factory(providers_config: Any) -> LLMFactory:
    """
    Create an LLM factory from provider configurations.

    Args:
        providers_config: Provider configurations

    Returns:
        LLMFactory instance
    """
    return LLMFactory(providers_config)


# Convenience function for creating a factory from config file
def create_llm_factory_from_file(config_path: str) -> LLMFactory:
    """
    Create an LLM factory from a configuration file.

    Args:
        config_path: Path to the models.yaml configuration file

    Returns:
        LLMFactory instance
    """
    return LLMFactory.from_config_file(config_path)
