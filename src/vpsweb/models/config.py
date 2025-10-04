"""
Configuration models for Vox Poetica Studio Web.

This module contains Pydantic models for validating and structuring
all configuration aspects of the translation workflow system.
"""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum


class ProviderType(str, Enum):
    """Supported LLM provider types."""
    OPENAI_COMPATIBLE = "openai_compatible"


class LogLevel(str, Enum):
    """Supported logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ModelProviderConfig(BaseModel):
    """Configuration for an LLM provider."""

    api_key_env: str = Field(
        ...,
        description="Environment variable name containing the API key"
    )
    base_url: str = Field(
        ...,
        description="Base URL for the provider's API"
    )
    type: ProviderType = Field(
        ...,
        description="Type of provider (e.g., openai_compatible)"
    )
    models: List[str] = Field(
        ...,
        description="List of available models from this provider"
    )
    default_model: Optional[str] = Field(
        None,
        description="Default model to use when not specified"
    )

    @validator('default_model')
    def validate_default_model(cls, v, values):
        """Validate that default_model is in the models list."""
        if v and 'models' in values:
            if v not in values['models']:
                raise ValueError(f"default_model '{v}' must be in models list")
        return v

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class StepConfig(BaseModel):
    """Configuration for a workflow step."""

    provider: str = Field(
        ...,
        description="Provider name (must match a provider in models.yaml)"
    )
    model: str = Field(
        ...,
        description="Model name to use for this step"
    )
    temperature: float = Field(
        0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for generation (0.0-2.0)"
    )
    max_tokens: int = Field(
        4096,
        ge=1,
        description="Maximum tokens to generate"
    )
    prompt_template: str = Field(
        ...,
        description="Path to prompt template file"
    )
    timeout: Optional[float] = Field(
        120.0,
        description="Request timeout in seconds"
    )
    retry_attempts: Optional[int] = Field(
        3,
        description="Number of retry attempts for failed requests"
    )
    required_fields: Optional[List[str]] = Field(
        None,
        description="Required fields in the step output for validation"
    )

    @validator('provider')
    def validate_provider(cls, v):
        """Validate provider name format."""
        if not v or not v.strip():
            raise ValueError("Provider name cannot be empty")
        return v.strip()

    @validator('prompt_template')
    def validate_prompt_template(cls, v):
        """Validate prompt template path."""
        if not v or not v.strip():
            raise ValueError("Prompt template path cannot be empty")
        if not v.endswith('.yaml') and not v.endswith('.yml'):
            raise ValueError("Prompt template must be a YAML file")
        return v.strip()


class WorkflowConfig(BaseModel):
    """Configuration for the translation workflow."""

    name: str = Field(
        ...,
        description="Workflow name"
    )
    version: str = Field(
        ...,
        description="Workflow version"
    )
    steps: Dict[str, StepConfig] = Field(
        ...,
        description="Configuration for each workflow step"
    )

    @validator('name')
    def validate_name(cls, v):
        """Validate workflow name."""
        if not v or not v.strip():
            raise ValueError("Workflow name cannot be empty")
        return v.strip()

    @validator('version')
    def validate_version(cls, v):
        """Validate version format."""
        if not v or not v.strip():
            raise ValueError("Version cannot be empty")
        # Basic semantic versioning validation
        parts = v.split('.')
        if len(parts) != 3:
            raise ValueError("Version must follow semantic versioning (x.y.z)")
        for part in parts:
            if not part.isdigit():
                raise ValueError("Version parts must be numeric")
        return v.strip()

    @validator('steps')
    def validate_steps(cls, v):
        """Validate that required steps are present."""
        required_steps = ['initial_translation', 'editor_review', 'translator_revision']
        for step in required_steps:
            if step not in v:
                raise ValueError(f"Missing required step: {step}")
        return v


class StorageConfig(BaseModel):
    """Configuration for data storage."""

    output_dir: str = Field(
        "outputs",
        description="Directory for output files"
    )
    format: Literal["json", "yaml"] = Field(
        "json",
        description="Output format (json or yaml)"
    )
    include_timestamp: bool = Field(
        True,
        description="Whether to include timestamp in output filenames"
    )
    pretty_print: bool = Field(
        True,
        description="Whether to pretty-print JSON output"
    )

    @validator('output_dir')
    def validate_output_dir(cls, v):
        """Validate output directory."""
        if not v or not v.strip():
            raise ValueError("Output directory cannot be empty")
        return v.strip()


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: LogLevel = Field(
        LogLevel.INFO,
        description="Logging level"
    )
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    file: Optional[str] = Field(
        "vpsweb.log",
        description="Log file path (None for console only)"
    )
    max_file_size: int = Field(
        10485760,  # 10MB
        description="Maximum log file size in bytes"
    )
    backup_count: int = Field(
        5,
        description="Number of backup log files to keep"
    )


class MainConfig(BaseModel):
    """Main configuration combining all components."""

    workflow: WorkflowConfig = Field(
        ...,
        description="Workflow configuration"
    )
    storage: StorageConfig = Field(
        default_factory=StorageConfig,
        description="Storage configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )


class ProvidersConfig(BaseModel):
    """Configuration for LLM providers."""

    providers: Dict[str, ModelProviderConfig] = Field(
        ...,
        description="Provider configurations keyed by provider name"
    )
    provider_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Global provider settings"
    )

    @validator('providers')
    def validate_providers(cls, v):
        """Validate that at least one provider is configured."""
        if not v:
            raise ValueError("At least one provider must be configured")

        # Validate that required providers are present if referenced
        required_providers = ['tongyi', 'deepseek']  # From PSD_CC.md
        for provider in required_providers:
            if provider not in v:
                # This is a warning, not an error, for flexibility
                import warnings
                warnings.warn(f"Recommended provider '{provider}' not found in configuration")

        return v


class CompleteConfig(BaseModel):
    """Complete configuration combining main config and providers."""

    main: MainConfig
    providers: ProvidersConfig

    def get_provider_config(self, provider_name: str) -> ModelProviderConfig:
        """Get configuration for a specific provider."""
        if provider_name not in self.providers.providers:
            raise ValueError(f"Provider '{provider_name}' not found in configuration")
        return self.providers.providers[provider_name]

    def get_step_config(self, step_name: str) -> StepConfig:
        """Get configuration for a specific workflow step."""
        if step_name not in self.main.workflow.steps:
            raise ValueError(f"Step '{step_name}' not found in workflow configuration")
        return self.main.workflow.steps[step_name]

    class Config:
        """Pydantic configuration."""
        use_enum_values = True