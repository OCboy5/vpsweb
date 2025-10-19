"""
VPSWeb Workflow Adapter for Web Interface Integration

This service layer bridges the existing VPSWeb translation workflow with the web interface,
providing async execution, background tasks, and repository integration.
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks

from ...core.workflow import TranslationWorkflow, WorkflowError, StepExecutionError
from ...models.translation import TranslationInput, TranslationOutput
from ...models.config import WorkflowMode
from ...utils.config_loader import load_config
from ...utils.logger import get_logger
from ...utils.storage import StorageHandler

from .poem_service import PoemService
from .translation_service import TranslationService
from ...repository.service import RepositoryWebService
from ...repository.schemas import WorkflowTaskCreate, TaskStatus, WorkflowTaskResult

logger = get_logger(__name__)


class VPSWebIntegrationError(Exception):
    """Base exception for VPSWeb integration errors."""

    pass


class WorkflowExecutionError(VPSWebIntegrationError):
    """Raised when workflow execution fails."""

    pass


class ConfigurationError(VPSWebIntegrationError):
    """Raised when configuration loading fails."""

    pass


class TaskStatus:
    """Background task status tracking."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class VPSWebWorkflowAdapter:
    """
    Adapter service that integrates VPSWeb translation workflow with the web interface.

    This service provides:
    - Async workflow execution with background tasks
    - Repository integration for storing results
    - Error handling and logging
    - Status tracking for long-running tasks
    """

    def __init__(
        self,
        poem_service: PoemService,
        translation_service: TranslationService,
        repository_service: RepositoryWebService,
        config_path: Optional[str] = None,
    ):
        """
        Initialize the VPSWeb workflow adapter.

        Args:
            poem_service: Repository poem service
            translation_service: Repository translation service
            repository_service: Repository service for database operations
            config_path: Optional custom config directory path
        """
        self.poem_service = poem_service
        self.translation_service = translation_service
        self.repository_service = repository_service
        self.config_path = config_path

        # Note: No longer using in-memory _active_tasks
        # Task tracking is now handled by the database via repository_service.workflow_tasks

        # Lazy-loaded configuration and workflow
        self._config = None
        self._workflow_config = None
        self._providers_config = None

        logger.info("VPSWebWorkflowAdapter initialized")

    async def _load_configuration(self):
        """
        Load VPSWeb configuration lazily.

        Raises:
            ConfigurationError: If configuration loading fails
        """
        if self._config is None:
            try:
                logger.info("Loading VPSWeb configuration...")
                self._config = load_config(self.config_path)
                self._workflow_config = self._config.main.workflow
                self._providers_config = self._config.providers

                logger.info(
                    f"Loaded workflow: {self._workflow_config.name} v{self._workflow_config.version}"
                )
                logger.info(
                    f"Available providers: {list(self._providers_config.providers.keys())}"
                )

            except Exception as e:
                logger.error(f"Failed to load VPSWeb configuration: {e}")
                raise ConfigurationError(f"Configuration loading failed: {e}")

    async def _create_workflow(
        self, workflow_mode: WorkflowMode = WorkflowMode.HYBRID
    ) -> TranslationWorkflow:
        """
        Create a new workflow instance.

        Args:
            workflow_mode: Workflow mode to use

        Returns:
            Initialized workflow instance

        Raises:
            ConfigurationError: If workflow creation fails
        """
        await self._load_configuration()

        try:
            # Create a minimal system config for the adapter
            system_config = {
                "system": {
                    "preview_lengths": {
                        "input_preview": 100,
                        "response_preview": 100,
                        "editor_preview": 200,
                    }
                }
            }

            workflow = TranslationWorkflow(
                config=self._workflow_config,
                providers_config=self._providers_config,
                workflow_mode=workflow_mode,
                system_config=system_config,
            )
            return workflow

        except Exception as e:
            logger.error(f"Failed to create workflow: {e}")
            raise ConfigurationError(f"Workflow creation failed: {e}")

    def _map_iso_to_display_language(self, iso_code: str) -> str:
        """
        Map ISO language codes to display names expected by VPSWeb TranslationInput.

        Args:
            iso_code: ISO language code (e.g., 'en', 'zh-CN')

        Returns:
            Display language name (e.g., 'English', 'Chinese')
        """
        language_mapping = {
            "en": "English",
            "en-US": "English",
            "en-GB": "English",
            "zh": "Chinese",
            "zh-CN": "Chinese",
            "zh-TW": "Chinese",
            "zh-HK": "Chinese",
            "es": "Spanish",
            "es-ES": "Spanish",
            "es-MX": "Spanish",
            "fr": "French",
            "fr-FR": "French",
            "de": "German",
            "de-DE": "German",
            "ja": "Japanese",
            "ja-JP": "Japanese",
            "ru": "Russian",
            "ru-RU": "Russian",
            "pl": "Polish",
            "pl-PL": "Polish",
            "ar": "Arabic",
            "ar-SA": "Arabic",
        }

        # Return the mapped language or default to English if not found
        return language_mapping.get(iso_code, "English")

    def _map_repository_to_workflow_input(
        self, poem_data: Dict[str, Any], source_lang: str, target_lang: str
    ) -> TranslationInput:
        """
        Map repository poem data to VPSWeb TranslationInput.

        Args:
            poem_data: Poem data from repository
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            TranslationInput for VPSWeb workflow
        """
        return TranslationInput(
            original_poem=poem_data["content"],
            source_lang=self._map_iso_to_display_language(source_lang),
            target_lang=self._map_iso_to_display_language(target_lang),
        )

    def _map_workflow_output_to_repository(
        self, workflow_output: TranslationOutput, poem_id: str, workflow_mode: str
    ) -> Dict[str, Any]:
        """
        Map VPSWeb TranslationOutput to repository translation format.

        Args:
            workflow_output: Output from VPSWeb workflow
            poem_id: ID of the source poem
            workflow_mode: Workflow mode used

        Returns:
            Dictionary format for repository storage
        """
        return {
            "workflow_id": workflow_output.workflow_id,
            "poem_id": poem_id,
            "workflow_mode": workflow_mode,
            "source_lang": workflow_output.input.source_lang,
            "target_lang": workflow_output.input.target_lang,
            "original_poem": workflow_output.input.original_poem,
            # Workflow steps
            "initial_translation": workflow_output.initial_translation.initial_translation,
            "initial_translation_notes": workflow_output.initial_translation.initial_translation_notes,
            "editor_suggestions": workflow_output.editor_review.editor_suggestions,
            "revised_translation": workflow_output.revised_translation.revised_translation,
            "revised_translation_notes": workflow_output.revised_translation.revised_translation_notes,
            # Metadata
            "total_tokens": workflow_output.total_tokens,
            "duration_seconds": workflow_output.duration_seconds,
            "total_cost": workflow_output.total_cost,
            "full_log": workflow_output.full_log,
            # Step-specific metadata
            "initial_model_info": workflow_output.initial_translation.model_info,
            "editor_model_info": workflow_output.editor_review.model_info,
            "revision_model_info": workflow_output.revised_translation.model_info,
            # Step-specific metrics
            "initial_tokens": workflow_output.initial_translation.tokens_used,
            "editor_tokens": workflow_output.editor_review.tokens_used,
            "revision_tokens": workflow_output.revised_translation.tokens_used,
            "initial_cost": getattr(workflow_output.initial_translation, "cost", None),
            "editor_cost": getattr(workflow_output.editor_review, "cost", None),
            "revision_cost": getattr(workflow_output.revised_translation, "cost", None),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

    async def execute_translation_workflow(
        self,
        poem_id: str,
        source_lang: str,
        target_lang: str,
        workflow_mode: str = "hybrid",
        background_tasks: Optional[BackgroundTasks] = None,
        synchronous: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute VPSWeb translation workflow for a poem.

        Args:
            poem_id: ID of the poem to translate
            source_lang: Source language code
            target_lang: Target language code
            workflow_mode: Workflow mode (reasoning, non_reasoning, hybrid)
            background_tasks: FastAPI BackgroundTasks for async execution
            synchronous: If True, execute synchronously and return result

        Returns:
            Dictionary with task info or result

        Raises:
            WorkflowExecutionError: If workflow execution fails
            ConfigurationError: If configuration is invalid
        """
        # Validate inputs
        if not poem_id:
            raise WorkflowExecutionError("Poem ID is required")

        if source_lang == target_lang:
            raise WorkflowExecutionError(
                "Source and target languages must be different"
            )

        # Validate workflow mode
        try:
            workflow_mode_enum = WorkflowMode(workflow_mode)
        except ValueError:
            raise WorkflowExecutionError(f"Invalid workflow mode: {workflow_mode}")

        # Retrieve poem from repository
        poem = await self.poem_service.get_poem(poem_id)
        if not poem:
            raise WorkflowExecutionError(f"Poem not found: {poem_id}")

        # Create task record in database
        task_create = WorkflowTaskCreate(
            poem_id=poem_id,
            source_lang=source_lang,
            target_lang=target_lang,
            workflow_mode=workflow_mode_enum,
        )

        # Save task to database
        db_task = self.repository_service.create_workflow_task(task_create)
        task_id = db_task.id

        if synchronous:
            # Execute workflow synchronously
            return await self._execute_workflow_task(task_id, poem, workflow_mode_enum)
        else:
            # Add to background tasks
            if background_tasks:
                background_tasks.add_task(
                    self._execute_workflow_task, task_id, poem, workflow_mode_enum
                )
            else:
                # Execute as coroutine
                asyncio.create_task(
                    self._execute_workflow_task(task_id, poem, workflow_mode_enum)
                )

            return {
                "task_id": task_id,
                "status": TaskStatus.PENDING,
                "message": "Translation workflow started",
            }

    async def _execute_workflow_task(
        self, task_id: str, poem: Dict[str, Any], workflow_mode: WorkflowMode
    ) -> Dict[str, Any]:
        """
        Execute the actual workflow task.

        Args:
            task_id: Unique task identifier
            poem: Poem data from repository
            workflow_mode: Workflow mode to use

        Returns:
            Task result with translation data

        Raises:
            WorkflowExecutionError: If execution fails
        """
        # Get task from database
        db_task = self.repository_service.get_workflow_task(task_id)
        if not db_task:
            raise WorkflowExecutionError(f"Task not found: {task_id}")

        try:
            # Update task status in database
            self.repository_service.update_workflow_task_status(
                task_id, TaskStatus.RUNNING, progress_percentage=0
            )

            logger.info(
                f"Starting translation workflow task {task_id} for poem {db_task.poem_id}"
            )

            # Create workflow
            workflow = await self._create_workflow(workflow_mode)

            # Prepare input
            input_data = self._map_repository_to_workflow_input(
                poem, db_task.source_lang, db_task.target_lang
            )

            # Execute workflow
            logger.info(
                f"Executing VPSWeb translation workflow in {workflow_mode.value} mode"
            )
            workflow_output = await workflow.execute(input_data, show_progress=False)

            # Map output to repository format
            translation_data = self._map_workflow_output_to_repository(
                workflow_output, db_task.poem_id, db_task.workflow_mode
            )

            # Save to repository
            logger.info(f"Saving translation results to repository")
            saved_translation = await self.translation_service.create_translation(
                poem_id=db_task.poem_id,
                source_lang=db_task.source_lang,
                target_lang=db_task.target_lang,
                workflow_mode=db_task.workflow_mode,
                translation_data=translation_data,
            )

            # Update task with result in database
            result_data = {
                "translation_id": saved_translation["id"],
                "workflow_id": workflow_output.workflow_id,
                "total_tokens": workflow_output.total_tokens,
                "duration_seconds": workflow_output.duration_seconds,
                "total_cost": workflow_output.total_cost,
            }
            self.repository_service.set_workflow_task_result(task_id, result_data)
            self.repository_service.update_workflow_task_status(
                task_id, TaskStatus.COMPLETED, progress_percentage=100
            )

            logger.info(f"Translation workflow task {task_id} completed successfully")

            return {
                "task_id": task_id,
                "status": TaskStatus.COMPLETED,
                "translation_id": saved_translation["id"],
                "workflow_id": workflow_output.workflow_id,
                "total_tokens": workflow_output.total_tokens,
                "duration_seconds": workflow_output.duration_seconds,
                "total_cost": workflow_output.total_cost,
                "message": "Translation completed successfully",
            }

        except WorkflowError as e:
            logger.error(f"VPSWeb workflow failed for task {task_id}: {e}")
            # Update task status in database
            self.repository_service.update_workflow_task_status(
                task_id, TaskStatus.FAILED, progress_percentage=0, error_message=str(e)
            )

            raise WorkflowExecutionError(f"Workflow execution failed: {e}")

        except Exception as e:
            logger.error(f"Unexpected error in workflow task {task_id}: {e}")
            # Update task status in database
            self.repository_service.update_workflow_task_status(
                task_id, TaskStatus.FAILED, progress_percentage=0, error_message=str(e)
            )

            raise WorkflowExecutionError(f"Unexpected error: {e}")

        # Note: Task cleanup is now handled by database - no need for manual cleanup

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a background task.

        Args:
            task_id: Task identifier

        Returns:
            Task status information or None if not found
        """
        # Get task from database
        db_task = self.repository_service.get_workflow_task(task_id)
        if not db_task:
            return None

        return {
            "task_id": db_task.id,
            "status": db_task.status.value,
            "poem_id": db_task.poem_id,
            "source_lang": db_task.source_lang,
            "target_lang": db_task.target_lang,
            "workflow_mode": db_task.workflow_mode.value,
            "created_at": (
                db_task.created_at.isoformat() if db_task.created_at else None
            ),
            "started_at": (
                db_task.started_at.isoformat() if db_task.started_at else None
            ),
            "completed_at": (
                db_task.completed_at.isoformat() if db_task.completed_at else None
            ),
            "progress_percentage": db_task.progress_percentage,
            "error": db_task.error_message,
            "result": db_task.result_json,
        }

    async def list_active_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List active background tasks.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of task information
        """
        # Get tasks from database
        db_tasks = self.repository_service.get_workflow_tasks(limit=limit)

        return [
            {
                "task_id": task.id,
                "status": task.status.value,
                "poem_id": task.poem_id,
                "source_lang": task.source_lang,
                "target_lang": task.target_lang,
                "workflow_mode": task.workflow_mode.value,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": (
                    task.completed_at.isoformat() if task.completed_at else None
                ),
                "error": task.error_message,
            }
            for task in db_tasks
        ]

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a background task (mark as failed).

        Args:
            task_id: Task identifier

        Returns:
            True if task was cancelled, False if not found
        """
        # Get task from database
        db_task = self.repository_service.get_workflow_task(task_id)
        if not db_task:
            return False

        if db_task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            # Update task status in database
            self.repository_service.update_workflow_task_status(
                task_id,
                TaskStatus.FAILED,
                progress_percentage=0,
                error_message="Task cancelled by user",
            )

            logger.info(f"Task {task_id} cancelled by user")
            return True

        return False

    async def get_workflow_modes(self) -> List[Dict[str, str]]:
        """
        Get available workflow modes.

        Returns:
            List of available workflow modes with descriptions
        """
        return [
            {
                "value": "hybrid",
                "label": "Hybrid",
                "description": "Balanced approach with reasoning for review steps",
            },
            {
                "value": "reasoning",
                "label": "Reasoning",
                "description": "Highest quality with detailed reasoning for all steps",
            },
            {
                "value": "non_reasoning",
                "label": "Non-Reasoning",
                "description": "Fast and cost-effective for standard translations",
            },
        ]

    async def validate_workflow_input(
        self, poem_id: str, source_lang: str, target_lang: str, workflow_mode: str
    ) -> Dict[str, Any]:
        """
        Validate workflow input without executing.

        Args:
            poem_id: ID of the poem to translate
            source_lang: Source language code
            target_lang: Target language code
            workflow_mode: Workflow mode to validate

        Returns:
            Validation result
        """
        try:
            # Check if poem exists
            poem = await self.poem_service.get_poem(poem_id)
            if not poem:
                return {"valid": False, "errors": [f"Poem not found: {poem_id}"]}

            # Validate languages
            if source_lang == target_lang:
                return {
                    "valid": False,
                    "errors": ["Source and target languages must be different"],
                }

            # Validate workflow mode
            try:
                WorkflowMode(workflow_mode)
            except ValueError:
                return {
                    "valid": False,
                    "errors": [f"Invalid workflow mode: {workflow_mode}"],
                }

            # Validate poem content
            if not poem.get("content") or len(poem["content"].strip()) < 10:
                return {
                    "valid": False,
                    "errors": ["Poem content is too short or empty"],
                }

            # Try to load configuration
            await self._load_configuration()

            return {
                "valid": True,
                "message": "Validation passed",
                "poem_preview": (
                    poem["content"][:100] + "..."
                    if len(poem["content"]) > 100
                    else poem["content"]
                ),
                "workflow_info": {
                    "workflow": self._workflow_config.name,
                    "version": self._workflow_config.version,
                    "providers": list(self._providers_config.providers.keys()),
                },
            }

        except Exception as e:
            return {"valid": False, "errors": [f"Validation error: {e}"]}


@asynccontextmanager
async def get_vpsweb_adapter(
    poem_service: PoemService,
    translation_service: TranslationService,
    repository_service: RepositoryWebService,
    config_path: Optional[str] = None,
):
    """
    Context manager for VPSWeb adapter instance.

    Args:
        poem_service: Repository poem service
        translation_service: Repository translation service
        repository_service: Repository service for database operations
        config_path: Optional config directory path

    Yields:
        VPSWebWorkflowAdapter instance
    """
    adapter = VPSWebWorkflowAdapter(
        poem_service=poem_service,
        translation_service=translation_service,
        repository_service=repository_service,
        config_path=config_path,
    )

    try:
        yield adapter
    finally:
        # Cleanup if needed
        pass
