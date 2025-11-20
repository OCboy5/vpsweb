"""
Configuration Facade - Central Configuration Access Layer

This module provides the main ConfigFacade class that acts as the single
entry point for all configuration access in the application. It abstracts
away the underlying YAML structure and provides clean, typed interfaces.

Phase 1: Wraps existing CompleteConfig without changing underlying structure
"""

from typing import Optional, Dict, Any, List
from ...models.config import (
    WorkflowConfig,
    WorkflowMode,
    StepConfig,
    CompleteConfig,
    MainConfig,
    ProvidersConfig,
)
import logging

logger = logging.getLogger(__name__)

# Global instance for singleton pattern
_config_facade: Optional['ConfigFacade'] = None


class ConfigFacade:
    """
    Central facade for accessing configuration throughout the application.

    This class provides high-level interfaces to access configuration without
    directly touching the underlying YAML structure or Pydantic models.

    Phase 1 Implementation:
    - Wraps existing CompleteConfig structure
    - Provides domain-specific service interfaces
    - Maintains backward compatibility
    """

    def __init__(self, complete_config: CompleteConfig,
                 models_config: Optional[Dict[str, Any]] = None,
                 task_templates_config: Optional[Dict[str, Any]] = None):
        """
        Initialize with existing CompleteConfig structure and optional new configs.

        Args:
            complete_config: The main configuration
            models_config: Optional models.yaml config for new structure
            task_templates_config: Optional task_templates.yaml config for new structure
        """
        self._config = complete_config
        self._models_config = models_config
        self._task_templates_config = task_templates_config

        # Initialize domain services (legacy)
        from .workflow_service import WorkflowService
        from .model_service import ModelService
        from .system_service import SystemService

        self.workflow = WorkflowService(complete_config.main.workflow)
        self.models = ModelService(complete_config.providers)
        self.system = SystemService(
            complete_config.main.storage,
            complete_config.main.logging,
            complete_config.main.monitoring
        )

        # Initialize new registry services if available
        if models_config and task_templates_config:
            from .model_registry_service import ModelRegistryService
            from .task_template_service import TaskTemplateService

            self.model_registry = ModelRegistryService(models_config)
            self.task_templates = TaskTemplateService(task_templates_config)
            self._using_new_structure = True
            logger.info("ConfigFacade initialized with new model registry structure")
        else:
            self.model_registry = None
            self.task_templates = None
            self._using_new_structure = False
            logger.info("ConfigFacade initialized with legacy structure")

        logger.info("ConfigFacade initialization completed")

    # Legacy compatibility methods - preserve current interface
    @property
    def main(self) -> MainConfig:
        """Get main configuration (legacy compatibility)."""
        return self._config.main

    @property
    def providers(self) -> ProvidersConfig:
        """Get providers configuration (legacy compatibility)."""
        return self._config.providers

    def get_complete_config(self) -> CompleteConfig:
        """Get the underlying CompleteConfig (legacy compatibility)."""
        return self._config

    # New high-level interfaces
    def get_workflow_info(self) -> Dict[str, str]:
        """Get basic workflow information for display."""
        # Handle both enum and string workflow_mode values
        workflow_mode = self._config.main.workflow_mode
        if hasattr(workflow_mode, 'value'):
            # It's an enum
            mode_str = workflow_mode.value
        else:
            # It's already a string
            mode_str = str(workflow_mode)

        return {
            "name": self.workflow.get_name(),
            "version": self.workflow.get_version(),
            "mode": mode_str,
        }

    def get_provider_names(self) -> List[str]:
        """Get list of available provider names."""
        return list(self._config.providers.providers.keys())

    def validate_configuration(self) -> List[str]:
        """Validate configuration and return any errors."""
        errors = []

        # Validate workflow configuration
        try:
            self.workflow.validate_workflow_modes()
        except Exception as e:
            errors.append(f"Workflow validation failed: {e}")

        # Validate provider configuration
        try:
            self.models.validate_providers()
        except Exception as e:
            errors.append(f"Provider validation failed: {e}")

        return errors

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration for debugging."""
        return {
            "workflow": self.get_workflow_info(),
            "providers": self.get_provider_names(),
            "workflow_mode": self._config.main.workflow_mode.value,
            "storage_format": self._config.main.storage.format,
            "logging_level": self._config.main.logging.level.value,
            "using_new_structure": self._using_new_structure,
        }

    # New model registry and task template methods
    def is_using_new_structure(self) -> bool:
        """Check if using new model registry structure."""
        return self._using_new_structure

    def resolve_task_template(self, task_name: str) -> Dict[str, Any]:
        """
        Resolve task template to actual LLM configuration.

        Args:
            task_name: The task template name (e.g., "initial_translation_reasoning")

        Returns:
            Dictionary with resolved configuration including provider, model, parameters

        Raises:
            RuntimeError: If new model registry structure is not available
            ValueError: If task template is not found
        """
        if not self._using_new_structure:
            raise RuntimeError("Task template resolution requires new model registry structure")

        if not self.task_templates or not self.model_registry:
            raise RuntimeError("Model registry services not available")

        # Resolve the task template using the model registry
        resolved_config = self.task_templates.resolve_task_config(task_name, self.model_registry)

        return {
            "provider": resolved_config.provider,
            "model": resolved_config.model,
            "prompt_template": resolved_config.prompt_template,
            "temperature": resolved_config.temperature,
            "max_tokens": resolved_config.max_tokens,
            "timeout": resolved_config.timeout,
            "retry_attempts": resolved_config.retry_attempts,
            "stop": resolved_config.stop,
            "task_name": resolved_config.task_name,
        }

    def get_workflow_step_config(self, mode: str, step_name: str) -> Dict[str, Any]:
        """
        Get resolved configuration for a specific workflow step.

        Args:
            mode: Workflow mode (reasoning, non_reasoning, hybrid)
            step_name: Step name (initial_translation, editor_review, translator_revision)

        Returns:
            Dictionary with resolved step configuration

        Raises:
            RuntimeError: If new model registry structure is not available
            ValueError: If workflow mode or step is not found
        """
        if not self._using_new_structure:
            raise RuntimeError("Workflow step resolution requires new model registry structure")

        # Get workflow configuration for the mode
        workflow_data = self.workflow.get_workflow_data()
        if mode not in workflow_data:
            raise ValueError(f"Workflow mode '{mode}' not found")

        mode_config = workflow_data[mode]
        if step_name not in mode_config:
            raise ValueError(f"Step '{step_name}' not found in workflow mode '{mode}'")

        step_config = mode_config[step_name]

        # Handle both TaskTemplateStepConfig (new) and StepConfig (legacy) objects
        if hasattr(step_config, 'task_template'):
            task_template_name = step_config.task_template
        else:
            # Legacy StepConfig - this shouldn't happen with new structure but kept for compatibility
            raise ValueError(f"Step '{step_name}' in mode '{mode}' uses legacy configuration, expected task_template")

        if not task_template_name:
            raise ValueError(f"No task_template found for step '{step_name}' in mode '{mode}'")

        return self.resolve_task_template(task_template_name)

    def get_wechat_task_config(self, model_type: str) -> Dict[str, Any]:
        """
        Get WeChat task configuration based on model type.

        Args:
            model_type: Either "reasoning" or "non_reasoning"

        Returns:
            Dictionary with resolved WeChat task configuration

        Raises:
            RuntimeError: If new model registry structure is not available
            ValueError: If model_type is invalid
        """
        if not self._using_new_structure:
            raise RuntimeError("WeChat task resolution requires new model registry structure")

        task_template_name = self.task_templates.get_wechat_task_template(model_type)
        return self.resolve_task_template(task_template_name)

    def get_bbr_config(self) -> Dict[str, Any]:
        """
        Get BBR generation configuration.

        Returns:
            Dictionary with resolved BBR configuration

        Raises:
            RuntimeError: If new model registry structure is not available
            ValueError: If BBR task template is not found
        """
        if not self._using_new_structure:
            raise RuntimeError("BBR config resolution requires new model registry structure")

        return self.resolve_task_template("bbr_generation")

    def list_available_tasks(self) -> List[str]:
        """
        List all available task templates.

        Returns:
            List of task template names

        Raises:
            RuntimeError: If new model registry structure is not available
        """
        if not self._using_new_structure:
            raise RuntimeError("Task listing requires new model registry structure")

        return self.task_templates.list_all_tasks()

    def list_available_models(self) -> List[str]:
        """
        List all available model references.

        Returns:
            List of model references

        Raises:
            RuntimeError: If new model registry structure is not available
        """
        if not self._using_new_structure:
            raise RuntimeError("Model listing requires new model registry structure")

        return self.model_registry.get_all_models()


def initialize_config_facade(complete_config: CompleteConfig,
                           models_config: Optional[Dict[str, Any]] = None,
                           task_templates_config: Optional[Dict[str, Any]] = None) -> ConfigFacade:
    """
    Initialize the global ConfigFacade instance.

    Args:
        complete_config: The loaded CompleteConfig instance
        models_config: Optional models.yaml config for new structure
        task_templates_config: Optional task_templates.yaml config for new structure

    Returns:
        ConfigFacade instance
    """
    global _config_facade
    _config_facade = ConfigFacade(complete_config, models_config, task_templates_config)

    structure_type = "new model registry" if models_config and task_templates_config else "legacy"
    logger.info(f"Global ConfigFacade initialized with {structure_type} structure")
    return _config_facade


def get_config_facade() -> ConfigFacade:
    """
    Get the global ConfigFacade instance.

    Returns:
        The initialized ConfigFacade instance

    Raises:
        RuntimeError: If ConfigFacade has not been initialized
    """
    global _config_facade
    if _config_facade is None:
        raise RuntimeError(
            "ConfigFacade not initialized. Call initialize_config_facade() first."
        )
    return _config_facade


def is_config_facade_initialized() -> bool:
    """Check if ConfigFacade has been initialized."""
    global _config_facade
    return _config_facade is not None