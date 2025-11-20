"""
Task Template Service for VPSWeb.

This service provides access to task template definitions, allowing resolution
of task templates to actual LLM configurations using the model registry.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TaskTemplate:
    """Task template definition."""

    task_name: str
    model_ref: str
    prompt_template: str
    temperature: float
    max_tokens: int
    timeout: int
    retry_attempts: int
    stop: Optional[List[str]] = None


@dataclass
class ResolvedTaskConfig:
    """Resolved task configuration with actual model information."""

    task_name: str
    provider: str
    model: str
    prompt_template: str
    temperature: float
    max_tokens: int
    timeout: int
    retry_attempts: int
    stop: Optional[List[str]] = None


class TaskTemplateService:
    """
    Service for accessing task template definitions.

    Provides task template resolution, model preferences, and WeChat
    task mapping based on the task template structure.
    """

    def __init__(self, task_templates_config: Dict[str, Any]):
        """
        Initialize task template service.

        Args:
            task_templates_config: The task_templates.yaml configuration dictionary
        """
        self._task_templates_config = task_templates_config
        self._task_templates = task_templates_config.get("task_templates", {})

        logger.info(
            f"TaskTemplateService initialized with {len(self._task_templates)} task templates"
        )

    def get_task_template(self, task_name: str) -> TaskTemplate:
        """
        Get task template by name.

        Args:
            task_name: The task template name (e.g., "initial_translation_reasoning")

        Returns:
            TaskTemplate object with task details

        Raises:
            ValueError: If task_name is not found
        """
        if task_name not in self._task_templates:
            raise ValueError(f"Task template '{task_name}' not found")

        task_data = self._task_templates[task_name]
        return TaskTemplate(
            task_name=task_name,
            model_ref=task_data["model_ref"],
            prompt_template=task_data["prompt_template"],
            temperature=task_data["temperature"],
            max_tokens=task_data["max_tokens"],
            timeout=task_data["timeout"],
            retry_attempts=task_data.get("retry_attempts", 2),
            stop=task_data.get("stop"),
        )

    def resolve_task_config(
        self, task_name: str, model_registry_service
    ) -> ResolvedTaskConfig:
        """
        Resolve task template with actual model information.

        Args:
            task_name: The task template name
            model_registry_service: Service to resolve model references

        Returns:
            ResolvedTaskConfig with actual provider and model names

        Raises:
            ValueError: If task_name is not found or model_ref is invalid
        """
        task_template = self.get_task_template(task_name)

        # Resolve model reference to actual provider/model
        provider, model_name = model_registry_service.resolve_model_reference(
            task_template.model_ref
        )

        return ResolvedTaskConfig(
            task_name=task_name,
            provider=provider,
            model=model_name,
            prompt_template=task_template.prompt_template,
            temperature=task_template.temperature,
            max_tokens=task_template.max_tokens,
            timeout=task_template.timeout,
            retry_attempts=task_template.retry_attempts,
            stop=task_template.stop,
        )

    def get_wechat_task_template(self, model_type: str) -> str:
        """
        Get WeChat task template based on model type.

        Args:
            model_type: Either "reasoning" or "non_reasoning"

        Returns:
            Task template name for WeChat notes generation

        Raises:
            ValueError: If model_type is invalid
        """
        if model_type not in ["reasoning", "non_reasoning"]:
            raise ValueError(
                f"Invalid model_type '{model_type}'. Must be 'reasoning' or 'non_reasoning'"
            )

        # Try multiple variations to handle potential naming inconsistencies
        possible_names = [
            f"wechat_notes_{model_type}",
            f"wechat_notes_{model_type.strip()}",
            f"wechat_notes_{model_type.replace(' ', '_')}",
            f"wechat_notes_{model_type.replace('_', '')}",  # non_reasoning -> nonreasoning
        ]

        for task_name in possible_names:
            # Use explicit key matching to avoid encoding issues
            for existing_key in self._task_templates.keys():
                if (
                    existing_key.replace(" ", "").lower()
                    == task_name.replace(" ", "").lower()
                ):
                    return existing_key

        # List available WeChat tasks for debugging
        wechat_tasks = [k for k in self._task_templates.keys() if "wechat" in k.lower()]
        available_tasks = ", ".join(wechat_tasks)
        raise ValueError(
            f"WeChat task template for '{model_type}' not found. Available: {available_tasks}"
        )

    def list_wechat_tasks(self) -> List[str]:
        """
        List all WeChat-related task templates.

        Returns:
            List of task template names containing 'wechat'
        """
        return [k for k in self._task_templates.keys() if "wechat" in k.lower()]

    def list_all_tasks(self) -> List[str]:
        """
        Get all available task template names.

        Returns:
            List of all task template names
        """
        return list(self._task_templates.keys())

    def list_workflow_tasks(self) -> List[str]:
        """
        Get task templates used in translation workflows.

        Returns:
            List of task template names for translation workflows
        """
        workflow_patterns = [
            "initial_translation_",
            "editor_review_",
            "translator_revision_",
        ]

        workflow_tasks = []
        for task_name in self._task_templates.keys():
            if any(task_name.startswith(pattern) for pattern in workflow_patterns):
                workflow_tasks.append(task_name)

        return workflow_tasks

    def list_specialized_tasks(self) -> List[str]:
        """
        Get specialized task templates (BBR, WeChat, etc.).

        Returns:
            List of specialized task template names
        """
        workflow_patterns = [
            "initial_translation_",
            "editor_review_",
            "translator_revision_",
        ]

        specialized_tasks = []
        for task_name in self._task_templates.keys():
            if not any(task_name.startswith(pattern) for pattern in workflow_patterns):
                specialized_tasks.append(task_name)

        return specialized_tasks

    def get_task_model_ref(self, task_name: str) -> str:
        """
        Get the model reference for a task template.

        Args:
            task_name: The task template name

        Returns:
            Model reference used by the task template

        Raises:
            ValueError: If task_name is not found
        """
        task_template = self.get_task_template(task_name)
        return task_template.model_ref

    def get_tasks_by_model_ref(self, model_ref: str) -> List[str]:
        """
        Get all task templates that use a specific model reference.

        Args:
            model_ref: The model reference to search for

        Returns:
            List of task template names that use the model
        """
        matching_tasks = []
        for task_name, task_data in self._task_templates.items():
            if task_data.get("model_ref") == model_ref:
                matching_tasks.append(task_name)

        return matching_tasks

    def get_tasks_by_reasoning_type(self, reasoning: bool) -> List[str]:
        """
        Get task templates by reasoning type (from model references).

        Args:
            reasoning: True to get reasoning tasks, False for non-reasoning

        Returns:
            List of task template names that use reasoning/non-reasoning models
        """
        tasks_by_type = []

        # This would require access to model registry to check reasoning capability
        # For now, we'll infer from task names
        for task_name in self._task_templates.keys():
            if reasoning:
                if "reasoning" in task_name:
                    tasks_by_type.append(task_name)
            else:
                if "nonreasoning" in task_name:
                    tasks_by_type.append(task_name)

        return tasks_by_type

    def validate_task_template(self, task_name: str) -> bool:
        """
        Validate that a task template exists.

        Args:
            task_name: The task template name to validate

        Returns:
            True if the task template exists
        """
        return task_name in self._task_templates

    def get_task_summary(self, task_name: str) -> Dict[str, Any]:
        """
        Get a summary of task template information.

        Args:
            task_name: The task template name

        Returns:
            Dictionary with task summary information

        Raises:
            ValueError: If task_name is not found
        """
        task_template = self.get_task_template(task_name)

        return {
            "task_name": task_template.task_name,
            "model_ref": task_template.model_ref,
            "prompt_template": task_template.prompt_template,
            "temperature": task_template.temperature,
            "max_tokens": task_template.max_tokens,
            "timeout": task_template.timeout,
            "retry_attempts": task_template.retry_attempts,
            "has_stop_tokens": task_template.stop is not None,
            "stop_tokens": task_template.stop or [],
        }

    def __repr__(self) -> str:
        """String representation of the task template service."""
        return f"TaskTemplateService(tasks={len(self._task_templates)})"
