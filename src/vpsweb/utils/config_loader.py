"""
Configuration loader for Vox Poetica Studio Web.

This module provides utilities for loading and validating YAML configuration files,
including environment variable substitution and comprehensive error handling.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from pydantic import ValidationError

from ..models.config import CompleteConfig
from ..models.wechat import ArticleGenerationConfig, WeChatConfig

logger = logging.getLogger(__name__)


class ConfigLoadError(Exception):
    """Custom exception for configuration loading errors."""


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
    pattern = r"\$\{([^}]+)\}"

    def replace_var(match):
        var_expr = match.group(1)

        # Check for default value syntax
        if ":-" in var_expr:
            var_name, default_value = var_expr.split(":-", 1)
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
        with open(file_path, "r", encoding="utf-8") as f:
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


def load_article_generation_config(config_data: Dict[str, Any]) -> ArticleGenerationConfig:
    """
    Load and validate article generation configuration.

    Args:
        config_data: Dictionary containing article generation settings

    Returns:
        Validated ArticleGenerationConfig instance

    Raises:
        ConfigLoadError: If configuration is invalid
    """
    try:
        # Use config_data directly since it's already the article_generation section
        article_gen_data = config_data

        # Validate with Pydantic
        article_gen_config = ArticleGenerationConfig(**article_gen_data)

        logger.info("Article generation configuration loaded and validated successfully")
        return article_gen_config

    except ValidationError as e:
        error_details = []
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            error_details.append(f"  {loc}: {error['msg']}")

        raise ConfigLoadError(f"Invalid article generation configuration:\n" + "\n".join(error_details))
    except Exception as e:
        raise ConfigLoadError(f"Error loading article generation configuration: {e}")


def load_wechat_complete_config(config_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Load complete WeChat-related configuration including API, article generation, and content settings.

    Args:
        config_dir: Directory containing configuration files

    Returns:
        Dictionary containing all WeChat-related configurations

    Raises:
        ConfigLoadError: If configuration cannot be loaded or validated
    """
    try:
        # Determine config path
        if config_dir:
            config_path = Path(config_dir) / "wechat.yaml"
        else:
            config_path = Path("config/wechat.yaml")

        # Load the full config
        full_config_data = load_yaml_file(config_path)

        # Extract WeChat API configuration
        wechat_config = {
            "appid": full_config_data.get("appid"),
            "secret": full_config_data.get("secret"),
            "base_url": full_config_data.get("base_url", "https://api.weixin.qq.com"),
            "token_cache_path": full_config_data.get("token_cache_path", "outputs/.cache/wechat_token.json"),
            "timeouts": full_config_data.get("timeouts", {"connect": 5.0, "read": 20.0}),
            "retry_config": full_config_data.get("retry", {"attempts": 3, "backoff": "exponential"}),
        }

        # Load article generation configuration
        article_gen_config = load_article_generation_config(full_config_data.get("article_generation", {}))

        # Combine all configurations
        complete_config = {
            "wechat": wechat_config,
            "article_generation": article_gen_config,
            "llm": full_config_data.get("llm", {}),
            "output": full_config_data.get("output", {}),
            "content": full_config_data.get("content", {}),
            "publishing": full_config_data.get("publishing", {}),
            "development": full_config_data.get("development", {}),
        }

        logger.info("Complete WeChat configuration loaded successfully")
        return complete_config

    except Exception as e:
        raise ConfigLoadError(f"Error loading complete WeChat configuration: {e}")


def validate_wechat_setup(config_dir: Optional[Union[str, Path]] = None) -> bool:
    """
    Validate WeChat configuration and setup without loading the complete system.

    Args:
        config_dir: Directory containing configuration files

    Returns:
        True if configuration is valid, False otherwise

    Raises:
        ConfigLoadError: If validation fails
    """
    try:
        logger.info("Validating WeChat configuration...")

        # Determine config path
        if config_dir:
            config_path = Path(config_dir) / "wechat.yaml"
        else:
            config_path = Path("config/wechat.yaml")

        # Load the full config
        full_config_data = load_yaml_file(config_path)

        # Extract WeChat API configuration
        wechat_config_dict = {
            "appid": full_config_data.get("appid"),
            "secret": full_config_data.get("secret"),
            "base_url": full_config_data.get("base_url", "https://api.weixin.qq.com"),
            "token_cache_path": full_config_data.get("token_cache_path", "outputs/.cache/wechat_token.json"),
            "timeouts": full_config_data.get("timeouts", {"connect": 5.0, "read": 20.0}),
            "retry_config": full_config_data.get("retry", {"attempts": 3, "backoff": "exponential"}),
        }

        # Convert to WeChatConfig object
        wechat_config = WeChatConfig(**wechat_config_dict)

        # Validate essential fields
        if not wechat_config.appid or wechat_config.appid == "YOUR_WECHAT_APPID":
            raise ConfigLoadError("WeChat AppID is not configured")

        if not wechat_config.secret or wechat_config.secret == "YOUR_WECHAT_SECRET":
            raise ConfigLoadError("WeChat Secret is not configured")

        # Validate article generation configuration
        article_gen_config = load_article_generation_config(full_config_data.get("article_generation", {}))

        # Check if essential directories can be created
        output_dir = Path(wechat_config.token_cache_path).parent
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created cache directory: {output_dir}")
            except Exception as e:
                raise ConfigLoadError(f"Cannot create cache directory {output_dir}: {e}")

        logger.info("WeChat configuration validation passed")
        return True

    except Exception as e:
        logger.error(f"WeChat configuration validation failed: {e}")
        raise


def load_model_registry_config() -> Dict[str, Any]:
    """
    Load the model registry configuration.

    Returns:
        Dictionary containing the models.yaml configuration

    Raises:
        ConfigLoadError: If the configuration file cannot be loaded
    """
    try:
        models_path = Path("config/models.yaml")
        if not models_path.exists():
            raise ConfigLoadError(f"Model registry file not found: {models_path}")

        with open(models_path, "r", encoding="utf-8") as f:
            models_config = yaml.safe_load(f)

        logger.info("Model registry configuration loaded successfully")
        return models_config

    except yaml.YAMLError as e:
        raise ConfigLoadError(f"Invalid YAML in model registry file: {e}")
    except Exception as e:
        raise ConfigLoadError(f"Failed to load model registry configuration: {e}")


def load_task_templates_config() -> Dict[str, Any]:
    """
    Load the task templates configuration.

    Returns:
        Dictionary containing the task_templates.yaml configuration

    Raises:
        ConfigLoadError: If the configuration file cannot be loaded
    """
    try:
        task_templates_path = Path("config/task_templates.yaml")
        if not task_templates_path.exists():
            raise ConfigLoadError(f"Task templates file not found: {task_templates_path}")

        with open(task_templates_path, "r", encoding="utf-8") as f:
            task_templates_config = yaml.safe_load(f)

        logger.info("Task templates configuration loaded successfully")
        return task_templates_config

    except yaml.YAMLError as e:
        raise ConfigLoadError(f"Invalid YAML in task templates file: {e}")
    except Exception as e:
        raise ConfigLoadError(f"Failed to load task templates configuration: {e}")


def validate_config_files(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Validate all configuration files.

    Args:
        config_path: Optional path to custom main configuration file

    Returns:
        Dictionary with validation results

    Raises:
        ConfigLoadError: If validation fails
    """
    try:
        errors = []
        warnings = []

        # Validate main configuration
        if config_path is None:
            main_config_path = Path("config/default.yaml")
        else:
            main_config_path = Path(config_path)

        if not main_config_path.exists():
            errors.append(f"Main configuration file not found: {main_config_path}")
        else:
            try:
                load_yaml_file(main_config_path)
                logger.info(f"Main configuration file is valid: {main_config_path}")
            except Exception as e:
                errors.append(f"Invalid main configuration: {e}")

        # Validate models configuration
        models_config_path = Path("config/models.yaml")
        if not models_config_path.exists():
            errors.append(f"Models configuration file not found: {models_config_path}")
        else:
            try:
                load_model_registry_config()
                logger.info("Models configuration file is valid")
            except Exception as e:
                errors.append(f"Invalid models configuration: {e}")

        # Validate task templates configuration
        try:
            load_task_templates_config()
            logger.info("Task templates configuration file is valid")
        except Exception as e:
            warnings.append(f"Task templates configuration issue: {e}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "config_files": {
                "main": str(main_config_path),
                "models": str(models_config_path),
                "task_templates": str(Path("config/task_templates.yaml")),
            },
        }

    except Exception as e:
        raise ConfigLoadError(f"Configuration validation failed: {e}")


def load_config(config_path: Optional[Union[str, Path]] = None) -> "CompleteConfig":
    """
    Load the complete configuration for backward compatibility.

    This function loads the main configuration (default.yaml or custom path)
    and models.yaml to create a CompleteConfig object for backward compatibility.
    It uses the new config pattern internally.

    Args:
        config_path: Optional path to custom configuration file. If None, uses default.yaml

    Returns:
        CompleteConfig object containing both main and providers configuration

    Raises:
        ConfigLoadError: If configuration cannot be loaded or is invalid
    """
    try:
        # Import here to avoid circular imports
        from ..models.config import CompleteConfig, MainConfig, ProvidersConfig

        # Load main configuration
        if config_path is None:
            main_config_path = Path("config/default.yaml")
        else:
            main_config_path = Path(config_path)

        if not main_config_path.exists():
            raise ConfigLoadError(f"Main configuration file not found: {main_config_path}")

        with open(main_config_path, "r", encoding="utf-8") as f:
            main_config_data = yaml.safe_load(f)

        # Apply environment variable substitution
        main_config_data = substitute_env_vars_in_data(main_config_data)

        # Load models configuration for providers
        models_config = load_model_registry_config()

        # Convert models.yaml format to providers config for CompleteConfig
        providers_data = {}

        if "providers" in models_config:
            # Extract models for each provider
            provider_models = {}
            if "models" in models_config:
                for model_name, model_info in models_config["models"].items():
                    provider_name = model_info.get("provider")
                    if provider_name:
                        if provider_name not in provider_models:
                            provider_models[provider_name] = []
                        provider_models[provider_name].append(model_info.get("name", model_name))

            for provider_name, provider_info in models_config["providers"].items():
                providers_data[provider_name] = {
                    "api_key_env": provider_info.get("api_key_env"),
                    "base_url": provider_info.get("base_url"),
                    "type": provider_info.get("type", "openai_compatible"),
                    "models": provider_models.get(provider_name, []),  # Add models list
                    "timeout": models_config.get("provider_settings", {}).get("timeout", 180.0),
                    "max_retries": models_config.get("provider_settings", {}).get("max_retries", 3),
                    "retry_delay": models_config.get("provider_settings", {}).get("retry_delay", 1.0),
                }

        # Create providers config
        providers_config = ProvidersConfig(providers=providers_data)

        # Create main config
        main_config = MainConfig(**main_config_data)

        # Create and return complete config
        complete_config = CompleteConfig(main=main_config, providers=providers_config)

        logger.info("Complete configuration loaded successfully")
        return complete_config

    except yaml.YAMLError as e:
        raise ConfigLoadError(f"Invalid YAML in configuration file: {e}")
    except ValidationError as e:
        raise ConfigLoadError(f"Configuration validation failed: {e}")
    except Exception as e:
        raise ConfigLoadError(f"Failed to load configuration: {e}")
