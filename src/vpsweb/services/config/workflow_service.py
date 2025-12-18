"""
Workflow Service - Domain-specific workflow configuration access

This service provides high-level interfaces for accessing workflow-related
configuration without directly manipulating the underlying YAML structure.
"""

import logging
from typing import Any, Dict, List, Union

from ...models.config import (StepConfig, TaskTemplateStepConfig,
                              WorkflowConfig, WorkflowMode)

logger = logging.getLogger(__name__)


class WorkflowService:
    """
    Service for accessing workflow-related configuration.

    Provides clean interfaces for:
    - Getting workflow steps by mode
    - Accessing step configurations
    - Workflow metadata and validation
    """

    def __init__(self, workflow_config: WorkflowConfig):
        """Initialize with workflow configuration."""
        self._config = workflow_config

    # High-level workflow information
    def get_name(self) -> str:
        """Get workflow name."""
        return self._config.name

    def get_version(self) -> str:
        """Get workflow version."""
        return self._config.version

    def get_workflow_info(self) -> Dict[str, str]:
        """Get complete workflow information."""
        return {
            "name": self._config.name,
            "version": self._config.version,
        }

    # Workflow mode and step access
    def get_available_modes(self) -> List[str]:
        """Get list of available workflow modes."""
        modes = []
        if self._config.reasoning_workflow:
            modes.append(WorkflowMode.REASONING.value)
        if self._config.non_reasoning_workflow:
            modes.append(WorkflowMode.NON_REASONING.value)
        if self._config.hybrid_workflow:
            modes.append(WorkflowMode.HYBRID.value)
        return modes

    def get_workflow_steps(
        self, mode: WorkflowMode
    ) -> Dict[str, Union[StepConfig, TaskTemplateStepConfig]]:
        """
        Get workflow steps for the specified mode.

        Args:
            mode: Workflow mode (reasoning, non_reasoning, hybrid)

        Returns:
            Dictionary mapping step names to StepConfig objects
        """
        if mode == WorkflowMode.REASONING and self._config.reasoning_workflow:
            return self._config.reasoning_workflow
        elif mode == WorkflowMode.NON_REASONING and self._config.non_reasoning_workflow:
            return self._config.non_reasoning_workflow
        elif mode == WorkflowMode.HYBRID and self._config.hybrid_workflow:
            return self._config.hybrid_workflow
        elif mode == WorkflowMode.MANUAL:
            # Manual workflow doesn't use YAML configuration
            # It uses a separate session-based workflow service
            return {}
        else:
            raise ValueError(f"Workflow mode '{mode.value}' is not configured")

    def get_workflow_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Get raw workflow data for all modes.

        Returns:
            Dictionary mapping mode names to step configurations
        """
        workflow_data = {}

        if self._config.reasoning_workflow:
            workflow_data["reasoning"] = self._config.reasoning_workflow
        if self._config.non_reasoning_workflow:
            workflow_data["non_reasoning"] = self._config.non_reasoning_workflow
        if self._config.hybrid_workflow:
            workflow_data["hybrid"] = self._config.hybrid_workflow

        return workflow_data

    def get_step_config(
        self, mode: WorkflowMode, step_name: str
    ) -> Union[StepConfig, TaskTemplateStepConfig]:
        """
        Get configuration for a specific workflow step.

        Args:
            mode: Workflow mode
            step_name: Name of the step (e.g., 'initial_translation')

        Returns:
            StepConfig object for the requested step
        """
        steps = self.get_workflow_steps(mode)
        if step_name not in steps:
            available_steps = list(steps.keys())
            raise ValueError(
                f"Step '{step_name}' not found in {mode.value} workflow. "
                f"Available steps: {available_steps}"
            )
        return steps[step_name]

    # Step-specific convenience methods
    def get_initial_translation_config(
        self, mode: WorkflowMode
    ) -> Union[StepConfig, TaskTemplateStepConfig]:
        """Get initial translation step configuration."""
        return self.get_step_config(mode, "initial_translation")

    def get_editor_review_config(
        self, mode: WorkflowMode
    ) -> Union[StepConfig, TaskTemplateStepConfig]:
        """Get editor review step configuration."""
        return self.get_step_config(mode, "editor_review")

    def get_translator_revision_config(
        self, mode: WorkflowMode
    ) -> Union[StepConfig, TaskTemplateStepConfig]:
        """Get translator revision step configuration."""
        return self.get_step_config(mode, "translator_revision")

    # Model and provider resolution for steps
    def get_step_model_info(self, mode: WorkflowMode, step_name: str) -> Dict[str, Any]:
        """
        Get model information for a specific step.

        Returns a dictionary with provider, model, and other model-related info.
        """
        step_config = self.get_step_config(mode, step_name)
        return {
            "provider": step_config.provider,
            "model": step_config.model,
            "temperature": step_config.temperature,
            "max_tokens": step_config.max_tokens,
            "prompt_template": step_config.prompt_template,
            "timeout": step_config.timeout,
            "retry_attempts": step_config.retry_attempts,
            "stop_sequences": step_config.stop,
        }

    def get_all_step_configs(self, mode: WorkflowMode) -> Dict[str, Dict[str, Any]]:
        """Get all step configurations with their model info."""
        steps = self.get_workflow_steps(mode)
        result = {}
        for step_name in steps:
            result[step_name] = self.get_step_model_info(mode, step_name)
        return result

    # Validation and utility methods
    def validate_workflow_modes(self) -> List[str]:
        """Validate workflow configuration and return any errors."""
        errors = []

        # Check that at least one workflow mode is configured
        available_modes = self.get_available_modes()
        if not available_modes:
            errors.append("No workflow modes configured")

        # Validate each configured mode
        for mode_str in available_modes:
            mode = WorkflowMode(mode_str)
            try:
                steps = self.get_workflow_steps(mode)
                if not steps:
                    errors.append(f"Workflow mode {mode_str} has no configured steps")

                # Validate required steps exist
                required_steps = [
                    "initial_translation",
                    "editor_review",
                    "translator_revision",
                ]
                for required_step in required_steps:
                    if required_step not in steps:
                        errors.append(
                            f"Workflow mode {mode_str} missing required step: {required_step}"
                        )

            except Exception as e:
                errors.append(f"Error validating workflow mode {mode_str}: {e}")

        return errors

    def get_step_names(self, mode: WorkflowMode) -> List[str]:
        """Get list of step names for a workflow mode."""
        steps = self.get_workflow_steps(mode)
        return list(steps.keys())

    def has_step(self, mode: WorkflowMode, step_name: str) -> bool:
        """Check if a workflow mode has a specific step."""
        try:
            steps = self.get_workflow_steps(mode)
            return step_name in steps
        except ValueError:
            return False
