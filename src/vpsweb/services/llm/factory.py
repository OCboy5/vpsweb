"""
LLM Provider Factory for creating and managing provider instances.

This module provides a factory pattern for creating LLM provider instances
based on configuration, with caching and error handling.
"""

from typing import Dict, Any, Optional
import logging
import os
from functools import lru_cache

from .base import BaseLLMProvider, ConfigurationError, ProviderType
from .openai_compatible import OpenAICompatibleProvider
from ...models.config import ProvidersConfig, ModelProviderConfig

logger = logging.getLogger(__name__)


class LLMFactory:
    """
    Factory for creating and managing LLM provider instances.

    This factory reads provider configurations and creates appropriate
    provider instances with caching for performance.
    """

    def __init__(self, providers_config: ProvidersConfig):
        """
        Initialize the LLM factory with provider configurations.

        Args:
            providers_config: Provider configurations from models.yaml
        """
        self.providers_config = providers_config
        self._provider_cache: Dict[str, BaseLLMProvider] = {}
        logger.info(
            f"Initialized LLMFactory with {len(providers_config.providers)} providers"
        )

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

        if provider_name not in self.providers_config.providers:
            available_providers = list(self.providers_config.providers.keys())
            raise ConfigurationError(
                f"Provider '{provider_name}' not found in configuration. "
                f"Available providers: {available_providers}",
                provider=provider_name,
            )

        provider_config = self.providers_config.providers[provider_name]
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
        if provider_name not in self.providers_config.providers:
            available_providers = list(self.providers_config.providers.keys())
            raise ConfigurationError(
                f"Provider '{provider_name}' not found in configuration. "
                f"Available providers: {available_providers}",
                provider=provider_name,
            )
        return self.providers_config.providers[provider_name]

    def _create_provider(
        self, provider_name: str, config: ModelProviderConfig
    ) -> BaseLLMProvider:
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
                f"Unsupported provider type: {config.type}. "
                f"Supported types: {[t.value for t in ProviderType]}",
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

        return OpenAICompatibleProvider(
            base_url=base_url, api_key=api_key, **provider_settings
        )

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
        if provider_name not in self.providers_config.providers:
            raise ConfigurationError(
                f"Provider '{provider_name}' not found in configuration",
                provider=provider_name,
            )

        provider_config = self.providers_config.providers[provider_name]
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
        if provider_name not in self.providers_config.providers:
            raise ConfigurationError(
                f"Provider '{provider_name}' not found in configuration",
                provider=provider_name,
            )

        provider_config = self.providers_config.providers[provider_name]
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
        if provider_name not in self.providers_config.providers:
            raise ConfigurationError(
                f"Provider '{provider_name}' not found in configuration",
                provider=provider_name,
            )

        provider_config = self.providers_config.providers[provider_name]
        provider = self.get_provider(provider_name)
        return provider.validate_config(provider_config)

    def get_all_providers(self) -> Dict[str, BaseLLMProvider]:
        """
        Get all configured providers.

        Returns:
            Dictionary mapping provider names to instances
        """
        providers = {}
        for provider_name in self.providers_config.providers:
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
        return f"LLMFactory(providers={list(self.providers_config.providers.keys())}, cached={len(self._provider_cache)})"


# Convenience function for creating a factory from configuration
def create_llm_factory(providers_config: ProvidersConfig) -> LLMFactory:
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
