"""
Configuration loader for Vox Poetica Studio Web.

This module provides utilities for loading and validating YAML configuration files,
including environment variable substitution and comprehensive error handling.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union
import logging
from pydantic import ValidationError

from ..models.config import (
    MainConfig,
    ProvidersConfig,
    CompleteConfig,
    ModelProviderConfig
)

logger = logging.getLogger(__name__)


class ConfigLoadError(Exception):
    """Custom exception for configuration loading errors."""
    pass


def substitute_env_vars(value: str) -> str:
    """
    Substitute environment variables in a string.

    Supports ${VAR_NAME} and ${VAR_NAME:-default_value} syntax.

    Args:
        value: String potentially containing environment variable references

    Returns:
        String with environment variables substituted

    Raises:
        ConfigLoadError: If required environment variable is not set
    """
    if not isinstance(value, str):
        return value

    # Pattern to match ${VAR_NAME} or ${VAR_NAME:-default_value}
    pattern = r'\$\{([^}]+)\}'

    def replace_var(match):
        var_expr = match.group(1)

        # Check for default value syntax
        if ':-' in var_expr:
            var_name, default_value = var_expr.split(':-', 1)
            var_name = var_name.strip()
            default_value = default_value.strip()

            env_value = os.getenv(var_name)
            if env_value is None:
                logger.info(f"Environment variable '{var_name}' not set, using default value")
                return default_value
            return env_value
        else:
            # No default value, variable is required
            var_name = var_expr.strip()
            env_value = os.getenv(var_name)

            if env_value is None:
                raise ConfigLoadError(
                    f"Required environment variable '{var_name}' is not set. "
                    f"Please set it in your .env file or environment."
                )
            return env_value

    try:
        result = re.sub(pattern, replace_var, value)
        return result
    except Exception as e:
        raise ConfigLoadError(f"Error substituting environment variables in '{value}': {e}")


def substitute_env_vars_in_data(data: Any) -> Any:
    """
    Recursively substitute environment variables in YAML data.

    Args:
        data: YAML data (dict, list, string, etc.)

    Returns:
        Data with environment variables substituted
    """
    if isinstance(data, dict):
        return {key: substitute_env_vars_in_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [substitute_env_vars_in_data(item) for item in data]
    elif isinstance(data, str):
        return substitute_env_vars(data)
    else:
        return data


def load_yaml_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load a YAML file and substitute environment variables.

    Args:
        file_path: Path to the YAML file

    Returns:
        Dictionary containing the YAML data

    Raises:
        ConfigLoadError: If file cannot be read or parsed
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise ConfigLoadError(f"Configuration file not found: {file_path}")

    if not file_path.is_file():
        raise ConfigLoadError(f"Configuration path is not a file: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)

        if yaml_data is None:
            raise ConfigLoadError(f"Configuration file is empty: {file_path}")

        # Substitute environment variables
        processed_data = substitute_env_vars_in_data(yaml_data)

        logger.info(f"Successfully loaded configuration file: {file_path}")
        return processed_data

    except yaml.YAMLError as e:
        raise ConfigLoadError(f"Invalid YAML in configuration file {file_path}: {e}")
    except Exception as e:
        raise ConfigLoadError(f"Error reading configuration file {file_path}: {e}")


def load_main_config(config_path: Union[str, Path]) -> MainConfig:
    """
    Load and validate the main configuration file.

    Args:
        config_path: Path to the main configuration file

    Returns:
        Validated MainConfig instance

    Raises:
        ConfigLoadError: If configuration is invalid
    """
    logger.info(f"Loading main configuration from: {config_path}")

    try:
        config_data = load_yaml_file(config_path)

        # Validate with Pydantic
        main_config = MainConfig(**config_data)

        logger.info("Main configuration loaded and validated successfully")
        return main_config

    except ValidationError as e:
        error_details = []
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error['loc'])
            error_details.append(f"  {loc}: {error['msg']}")

        raise ConfigLoadError(
            f"Invalid main configuration in {config_path}:\n" + "\n".join(error_details)
        )
    except Exception as e:
        raise ConfigLoadError(f"Error loading main configuration: {e}")


def load_providers_config(config_path: Union[str, Path]) -> ProvidersConfig:
    """
    Load and validate the providers configuration file.

    Args:
        config_path: Path to the providers configuration file

    Returns:
        Validated ProvidersConfig instance

    Raises:
        ConfigLoadError: If configuration is invalid
    """
    logger.info(f"Loading providers configuration from: {config_path}")

    try:
        config_data = load_yaml_file(config_path)

        # Validate with Pydantic
        providers_config = ProvidersConfig(**config_data)

        logger.info("Providers configuration loaded and validated successfully")
        return providers_config

    except ValidationError as e:
        error_details = []
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error['loc'])
            error_details.append(f"  {loc}: {error['msg']}")

        raise ConfigLoadError(
            f"Invalid providers configuration in {config_path}:\n" + "\n".join(error_details)
        )
    except Exception as e:
        raise ConfigLoadError(f"Error loading providers configuration: {e}")


def load_config(config_dir: Optional[Union[str, Path]] = None) -> CompleteConfig:
    """
    Load and validate the complete configuration from a directory.

    By default, looks for configuration files in the following order:
    1. Specified config directory
    2. ./config/ directory (relative to current working directory)
    3. ../config/ directory (relative to script location)

    Args:
        config_dir: Optional directory containing configuration files

    Returns:
        Complete validated configuration

    Raises:
        ConfigLoadError: If configuration cannot be loaded or validated
    """
    if config_dir is None:
        # Try to find config directory
        possible_paths = [
            Path("config"),
            Path(__file__).parent.parent.parent.parent / "config",
        ]

        for path in possible_paths:
            if path.exists() and path.is_dir():
                config_dir = path
                break

        if config_dir is None:
            raise ConfigLoadError(
                "Could not find configuration directory. "
                "Please specify config_dir or ensure config/ exists in the project root."
            )

    config_dir = Path(config_dir)

    if not config_dir.exists():
        raise ConfigLoadError(f"Configuration directory not found: {config_dir}")

    # Load main configuration
    main_config_path = config_dir / "default.yaml"
    if not main_config_path.exists():
        raise ConfigLoadError(f"Main configuration file not found: {main_config_path}")

    main_config = load_main_config(main_config_path)

    # Load providers configuration
    providers_config_path = config_dir / "models.yaml"
    if not providers_config_path.exists():
        raise ConfigLoadError(f"Providers configuration file not found: {providers_config_path}")

    providers_config = load_providers_config(providers_config_path)

    # Combine into complete configuration
    complete_config = CompleteConfig(
        main=main_config,
        providers=providers_config
    )

    logger.info("Complete configuration loaded successfully")
    return complete_config


def validate_config_files(config_dir: Optional[Union[str, Path]] = None) -> bool:
    """
    Validate configuration files without loading the complete system.

    Args:
        config_dir: Optional directory containing configuration files

    Returns:
        True if configuration is valid, False otherwise

    Raises:
        ConfigLoadError: If configuration files are invalid
    """
    try:
        config = load_config(config_dir)

        # Additional validation
        for step_name, step_config in config.main.workflow.steps.items():
            provider_name = step_config.provider
            if provider_name not in config.providers.providers:
                raise ConfigLoadError(
                    f"Step '{step_name}' references unknown provider '{provider_name}'"
                )

        logger.info("Configuration validation passed")
        return True

    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise