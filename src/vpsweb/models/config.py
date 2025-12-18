"""
Configuration models for Vox Poetica Studio Web.

This module contains Pydantic models for validating and structuring
all configuration aspects of the translation workflow system.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class ModelCapabilities(BaseModel):
    """Model capabilities classification."""

    reasoning: bool = Field(False, description="Whether this is a reasoning model")


class ModelProviderConfig(BaseModel):
    """Configuration for an LLM provider."""

    api_key_env: str = Field(
        ..., description="Environment variable name containing the API key"
    )
    base_url: str = Field(..., description="Base URL for the provider's API")
    type: ProviderType = Field(
        ..., description="Type of provider (e.g., openai_compatible)"
    )
    models: List[str] = Field(
        ..., description="List of available models from this provider"
    )
    default_model: Optional[str] = Field(
        None, description="Default model to use when not specified"
    )
    capabilities: Optional[ModelCapabilities] = Field(
        default_factory=ModelCapabilities, description="Model capabilities"
    )

    @field_validator("default_model")
    @classmethod
    def validate_default_model(cls, v, info):
        """Validate that default_model is in the models list."""
        if v and "models" in info.data:
            if v not in info.data["models"]:
                raise ValueError(f"default_model '{v}' must be in models list")
        return v

    model_config = ConfigDict(use_enum_values=True)


# Compatibility class for backward compatibility with existing code
class StepConfig(BaseModel):
    """
    Compatibility configuration for a workflow step.

    This class provides backward compatibility for code that still expects
    the old StepConfig interface. New code should use TaskTemplateStepConfig
    or access configuration through the ConfigFacade.
    """

    provider: str = Field(..., description="Provider name")
    model: str = Field(..., description="Model name to use for this step")
    temperature: float = Field(
        0.7, ge=0.0, le=2.0, description="Temperature for generation"
    )
    max_tokens: int = Field(4096, ge=1, description="Maximum tokens to generate")
    prompt_template: str = Field(..., description="Path to prompt template file")
    timeout: Optional[float] = Field(120.0, description="Request timeout in seconds")
    retry_attempts: Optional[int] = Field(
        3, description="Number of retry attempts for failed requests"
    )
    required_fields: Optional[List[str]] = Field(
        None, description="Required fields in the step output for validation"
    )
    stop: Optional[List[str]] = Field(None, description="Stop sequences for generation")

    model_config = ConfigDict(use_enum_values=True)


class WorkflowMode(str, Enum):
    """Supported workflow modes."""

    REASONING = "reasoning"
    NON_REASONING = "non_reasoning"
    HYBRID = "hybrid"
    MANUAL = "manual"


class TaskTemplateStepConfig(BaseModel):
    """Configuration for a workflow step using task templates (new structure)."""

    task_template: str = Field(
        ...,
        description="Task template name to resolve from task_templates.yaml",
    )

    @field_validator("task_template")
    @classmethod
    def validate_task_template(cls, v):
        """Validate task template name format."""
        if not v or not v.strip():
            raise ValueError("Task template name cannot be empty")
        return v.strip()


class WorkflowConfig(BaseModel):
    """Configuration for the translation workflow."""

    name: str = Field(..., description="Workflow name")
    version: str = Field(..., description="Workflow version")

    # Support both old and new structures
    reasoning_workflow: Optional[
        Dict[str, Union[StepConfig, TaskTemplateStepConfig]]
    ] = Field(None, description="Configuration for reasoning mode workflow steps")
    non_reasoning_workflow: Optional[
        Dict[str, Union[StepConfig, TaskTemplateStepConfig]]
    ] = Field(None, description="Configuration for non-reasoning mode workflow steps")
    hybrid_workflow: Optional[Dict[str, Union[StepConfig, TaskTemplateStepConfig]]] = (
        Field(None, description="Configuration for hybrid mode workflow steps")
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate workflow name."""
        if not v or not v.strip():
            raise ValueError("Workflow name cannot be empty")
        return v.strip()

    @field_validator("version")
    @classmethod
    def validate_version(cls, v):
        """Validate version format."""
        if not v or not v.strip():
            raise ValueError("Version cannot be empty")
        # Basic semantic versioning validation
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Version must follow semantic versioning (x.y.z)")
        for part in parts:
            if not part.isdigit():
                raise ValueError("Version parts must be numeric")
        return v.strip()

    @field_validator("hybrid_workflow")
    @classmethod
    def validate_workflows(cls, v, info):
        """Validate that at least one workflow mode is configured."""
        if (
            not v
            and not info.data.get("reasoning_workflow")
            and not info.data.get("non_reasoning_workflow")
        ):
            raise ValueError("At least one workflow mode must be configured")
        return v

    def get_workflow_steps(
        self, mode: WorkflowMode
    ) -> Dict[str, Union[StepConfig, TaskTemplateStepConfig]]:
        """Get workflow steps for the specified mode."""
        if mode == WorkflowMode.REASONING and self.reasoning_workflow:
            return self.reasoning_workflow
        elif mode == WorkflowMode.NON_REASONING and self.non_reasoning_workflow:
            return self.non_reasoning_workflow
        elif mode == WorkflowMode.HYBRID and self.hybrid_workflow:
            return self.hybrid_workflow
        else:
            raise ValueError(f"Workflow mode '{mode.value}' is not configured")


class StorageConfig(BaseModel):
    """Configuration for data storage."""

    output_dir: str = Field("outputs", description="Directory for output files")
    format: Literal["json", "yaml"] = Field(
        "json", description="Output format (json or yaml)"
    )
    include_timestamp: bool = Field(
        True, description="Whether to include timestamp in output filenames"
    )
    pretty_print: bool = Field(True, description="Whether to pretty-print JSON output")
    workflow_mode_tag: bool = Field(
        False,
        description="Whether to include workflow mode in output filenames",
    )

    @field_validator("output_dir")
    @classmethod
    def validate_output_dir(cls, v):
        """Validate output directory."""
        if not v or not v.strip():
            raise ValueError("Output directory cannot be empty")
        return v.strip()


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: LogLevel = Field(LogLevel.INFO, description="Logging level")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    file: Optional[str] = Field(
        "vpsweb.log", description="Log file path (None for console only)"
    )
    max_file_size: int = Field(
        10485760, description="Maximum log file size in bytes"  # 10MB
    )
    backup_count: int = Field(5, description="Number of backup log files to keep")
    log_reasoning_tokens: bool = Field(
        False,
        description="Whether to track reasoning model token usage separately",
    )


class MonitoringConfig(BaseModel):
    """Configuration for performance monitoring."""

    track_latency: bool = Field(True, description="Whether to track request latency")
    track_token_usage: bool = Field(True, description="Whether to track token usage")
    track_cost: bool = Field(False, description="Whether to estimate API costs")
    compare_workflows: bool = Field(
        False, description="Whether to enable A/B workflow comparison"
    )


# Compatibility classes for backward compatibility with ConfigFacade
class MainConfig(BaseModel):
    """Compatibility main configuration for backward compatibility."""

    workflow_mode: WorkflowMode = Field(
        WorkflowMode.HYBRID, description="Default workflow mode to use"
    )
    workflow: WorkflowConfig = Field(..., description="Workflow configuration")
    storage: StorageConfig = Field(
        default_factory=StorageConfig, description="Storage configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )
    monitoring: MonitoringConfig = Field(
        default_factory=MonitoringConfig,
        description="Monitoring configuration",
    )

    model_config = ConfigDict(use_enum_values=True)


class ProvidersConfig(BaseModel):
    """Compatibility providers configuration for backward compatibility."""

    providers: Dict[str, ModelProviderConfig] = Field(
        default_factory=dict, description="Provider configurations"
    )
    provider_settings: Dict[str, Any] = Field(
        default_factory=dict, description="Global provider settings"
    )
    model_classification: Optional[Dict[str, List[str]]] = Field(
        None, description="Model classification"
    )
    reasoning_settings: Optional[Dict[str, Any]] = Field(
        None, description="Reasoning model settings"
    )
    pricing: Optional[Dict[str, Any]] = Field(None, description="Pricing information")
    bbr_generation: Optional[Dict[str, Any]] = Field(
        None, description="BBR generation configuration"
    )

    def is_reasoning_model(self, model_name: str) -> bool:
        """Check if a model is classified as a reasoning model."""
        if not self.model_classification:
            return False
        reasoning_models = self.model_classification.get("reasoning_models", [])
        return model_name in reasoning_models


class CompleteConfig(BaseModel):
    """Compatibility complete configuration for backward compatibility."""

    main: MainConfig
    providers: ProvidersConfig

    def get_provider_config(self, provider_name: str) -> ModelProviderConfig:
        """Get configuration for a specific provider."""
        if provider_name not in self.providers.providers:
            raise ValueError(f"Provider '{provider_name}' not found in configuration")
        return self.providers.providers[provider_name]

    model_config = ConfigDict(use_enum_values=True)
