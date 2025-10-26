"""
VPSWeb Workflow Adapter for Web Interface Integration

This service layer bridges the existing VPSWeb translation workflow with the web interface,
providing async execution, background tasks, and repository integration.
"""

import asyncio
import logging
import time
import uuid
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks
import os

from vpsweb.core.workflow import TranslationWorkflow, WorkflowError, StepExecutionError
from vpsweb.models.translation import TranslationInput, TranslationOutput
from vpsweb.models.config import WorkflowMode
from vpsweb.utils.config_loader import load_config
from vpsweb.utils.logger import get_logger
from vpsweb.utils.storage import StorageHandler
from vpsweb.utils.language_mapper import get_language_mapper

from .poem_service import PoemService

# TranslationService removed - dead code (not used in current codebase)
from ..task_models import TaskStatusEnum
from vpsweb.repository.service import RepositoryWebService
from vpsweb.repository.schemas import TaskStatus, WorkflowTaskResult
from vpsweb.repository.database import create_session
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

logger = get_logger(__name__)

# P0.1: Timeout configuration for workflow execution
DEFAULT_WORKFLOW_TIMEOUT = int(
    os.getenv("VPSWEB_WORKFLOW_TIMEOUT", "600")
)  # 10 minutes default
MAX_WORKFLOW_TIMEOUT = int(
    os.getenv("VPSWEB_MAX_WORKFLOW_TIMEOUT", "1800")
)  # 30 minutes maximum


class VPSWebIntegrationError(Exception):
    """Base exception for VPSWeb integration errors."""

    pass


class WorkflowExecutionError(VPSWebIntegrationError):
    """Raised when workflow execution fails."""

    pass


class ConfigurationError(VPSWebIntegrationError):
    """Raised when configuration loading fails."""

    pass


class WorkflowTimeoutError(VPSWebIntegrationError):
    """Raised when workflow execution times out."""

    pass


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
        repository_service: RepositoryWebService,
        config_path: Optional[str] = None,
    ):
        """
        Initialize the VPSWeb workflow adapter.

        Args:
            poem_service: Repository poem service
            repository_service: Repository service for database operations
            config_path: Optional custom config directory path
        """
        self.poem_service = poem_service
        self.repository_service = repository_service
        self.config_path = config_path
        # TranslationService removed - dead code (not used in current codebase)

        # Initialize StorageHandler for JSON file saving (CLI-compatible)
        self.storage_handler = StorageHandler()

        # Note: No longer using in-memory _active_tasks
        # Task tracking is now handled by the database via repository_service.workflow_tasks

        # Lazy-loaded configuration and workflow
        self._config = None
        self._workflow_config = None
        self._providers_config = None

        # Language mapper for ISO code conversion
        self.language_mapper = get_language_mapper()

        logger.info("VPSWebWorkflowAdapter initialized")

    def _convert_language_code(self, lang_code: str) -> str:
        """
        Convert ISO language code to display name for VPSWeb workflow.

        Args:
            lang_code: ISO language code (e.g., 'en', 'zh-CN')

        Returns:
            Display name (e.g., 'English', 'Chinese')
        """
        display_name = self.language_mapper.get_language_name(lang_code)
        if display_name:
            return display_name

        # Fallback mapping for common codes
        fallback_mapping = {
            "en": "English",
            "zh": "Chinese",
            "zh-CN": "Chinese",
            "zh-TW": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "fr": "French",
            "de": "German",
            "es": "Spanish",
            "ru": "Russian",
            "ar": "Arabic",
            "hi": "Hindi",
            "pl": "Polish",
        }

        return fallback_mapping.get(lang_code, lang_code.title())

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
            source_lang=self._convert_language_code(source_lang),
            target_lang=self._convert_language_code(target_lang),
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
        # Debug: Log the workflow output fields
        logger.info(f"🔍 [MAPPING DEBUG] Mapping workflow output to repository format")
        logger.info(
            f"🔍 [MAPPING DEBUG] workflow_output.initial_translation.translated_poem_title: '{workflow_output.initial_translation.translated_poem_title}'"
        )
        logger.info(
            f"🔍 [MAPPING DEBUG] workflow_output.initial_translation.translated_poet_name: '{workflow_output.initial_translation.translated_poet_name}'"
        )
        logger.info(
            f"🔍 [MAPPING DEBUG] workflow_output.revised_translation.refined_translated_poem_title: '{workflow_output.revised_translation.refined_translated_poem_title}'"
        )
        logger.info(
            f"🔍 [MAPPING DEBUG] workflow_output.revised_translation.refined_translated_poet_name: '{workflow_output.revised_translation.refined_translated_poet_name}'"
        )

        result = {
            "poem_id": poem_id,
            "workflow_mode": workflow_mode,
            "source_lang": workflow_output.input.source_lang,
            "target_lang": workflow_output.input.target_lang,
            # Workflow steps
            "initial_translation": workflow_output.initial_translation.initial_translation,
            "initial_translation_notes": workflow_output.initial_translation.initial_translation_notes,
            "translated_poem_title": workflow_output.initial_translation.translated_poem_title,
            "translated_poet_name": workflow_output.initial_translation.translated_poet_name,
            "editor_suggestions": workflow_output.editor_review.editor_suggestions,
            "revised_translation": workflow_output.revised_translation.revised_translation,
            "revised_translation_notes": workflow_output.revised_translation.revised_translation_notes,
            "refined_translated_poem_title": workflow_output.revised_translation.refined_translated_poem_title,
            "refined_translated_poet_name": workflow_output.revised_translation.refined_translated_poet_name,
            # Metadata
            "total_tokens": workflow_output.total_tokens,
            "duration_seconds": workflow_output.duration_seconds,
            "total_cost": workflow_output.total_cost,
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
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Debug: Log what we're putting in the result
        logger.info(
            f"🔍 [MAPPING DEBUG] Result['translated_poem_title']: '{result.get('translated_poem_title', 'MISSING')}'"
        )
        logger.info(
            f"🔍 [MAPPING DEBUG] Result['translated_poet_name']: '{result.get('translated_poet_name', 'MISSING')}'"
        )
        logger.info(
            f"🔍 [MAPPING DEBUG] Result['refined_translated_poem_title']: '{result.get('refined_translated_poem_title', 'MISSING')}'"
        )
        logger.info(
            f"🔍 [MAPPING DEBUG] Result['refined_translated_poet_name']: '{result.get('refined_translated_poet_name', 'MISSING')}'"
        )

        return result

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
        Execute VPSWeb translation workflow for a poem with real-time SSE progress updates.

        Args:
            poem_id: ID of the poem to translate
            source_lang: Source language code
            target_lang: Target language code
            workflow_mode: Workflow mode (reasoning, non_reasoning, hybrid)
            background_tasks: FastAPI BackgroundTasks (kept for compatibility)
            synchronous: If True, execute synchronously and return result (not implemented)

        Returns:
            Dictionary with task info for SSE tracking

        Raises:
            WorkflowExecutionError: If workflow execution fails
            ConfigurationError: If configuration is invalid
        """
        logger.info(
            f"execute_translation_workflow called with poem_id={poem_id}, source_lang={source_lang}, target_lang={target_lang}, workflow_mode={workflow_mode}, synchronous={synchronous}"
        )

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

        # Create task ID and initialize in app.state (no database storage for personal use system)
        task_id = str(uuid.uuid4())
        logger.info(f"Created task ID: {task_id}")

        # Import task models for app.state initialization
        from ..task_models import TaskStatus as InMemoryTaskStatus, TaskStatusEnum

        # Get FastAPI app instance for app.state access
        import sys
        import os

        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from ..main import app

        # Initialize task in app.state
        task_status = InMemoryTaskStatus(task_id=task_id)
        app.state.tasks[task_id] = task_status
        app.state.task_locks[task_id] = threading.Lock()

        # Set initial workflow step states to "waiting"
        task_status.update_step(
            step_name="Initial Translation",
            step_details={"step_status": "waiting"},
            step_state="waiting",
        )
        task_status.update_step(
            step_name="Editor Review",
            step_details={"step_status": "waiting"},
            step_state="waiting",
        )
        task_status.update_step(
            step_name="Translator Revision",
            step_details={"step_status": "waiting"},
            step_state="waiting",
        )
        print(
            f"[PROGRESS] Initial workflow states set: Initial Translation: 'waiting', Editor Review: 'waiting', Translator Revision: 'waiting'"
        )

        # Execute workflows asynchronously with real-time progress callbacks
        # This enables SSE streaming of step-by-step progress updates

        # Use asyncio.create_task to run the new callback-based async function
        # This runs the task concurrently on the main event loop, allowing real-time updates.
        asyncio.create_task(
            self._execute_workflow_task_with_callback(
                task_id,
                poem_id,
                source_lang,
                target_lang,
                workflow_mode,
            )
        )
        logger.info(
            f"Asynchronous workflow task {task_id} with callback has been scheduled."
        )

        return {
            "task_id": task_id,
            "status": TaskStatusEnum.PENDING,
            "message": "Translation workflow started",
        }

    async def _execute_workflow_task_with_callback(
        self,
        task_id: str,
        poem_id: str,
        source_lang: str,
        target_lang: str,
        workflow_mode_str: str,
    ) -> None:
        """
        Asynchronous background task that uses a progress callback to provide real-time updates.
        This method executes the translation workflow step-by-step and updates the task status
        through the callback mechanism for real-time SSE streaming.

        Args:
            task_id: Workflow task ID
            poem_id: Poem ID to retrieve
            source_lang: Source language code
            target_lang: Target language code
            workflow_mode_str: Workflow mode as string
        """
        logger.info(f"Starting callback-based workflow task for task_id: {task_id}")

        # Get FastAPI app instance for app.state access
        from ..main import app

        # Get task status from app.state (should already be initialized)
        task_status = app.state.tasks.get(task_id)
        if not task_status:
            logger.error(f"Task {task_id} not found in app.state for async execution.")
            return

        # Define helper function to check if task was cancelled
        def is_cancelled():
            if task_id not in app.state.tasks:
                return True
            current_status = app.state.tasks[task_id]
            return (
                current_status.status.value == "failed"
                and "cancelled" in str(current_status.message).lower()
            )

        # Check if task was cancelled before starting
        if is_cancelled():
            print(
                f"[WORKFLOW] ❌ Task {task_id} was CANCELLED before execution started"
            )
            logger.info(f"Task {task_id} was cancelled before execution started.")
            return

        logger.info(f"✅ [CALLBACK ENTRY] Task status found for task_id: {task_id}")

        try:
            # Define the async callback function that updates the task state
            async def progress_callback(step_name: str, details: dict):
                # Skip updates if task is already completed or failed (including cancelled)
                current_task_status = app.state.tasks.get(task_id)
                if not current_task_status or current_task_status.status in [
                    "completed",
                    "failed",
                ]:
                    return

                # Skip progress updates if task was cancelled
                if (
                    current_task_status.status.value == "failed"
                    and "cancelled" in str(current_task_status.message).lower()
                ):
                    print(
                        f"[PROGRESS] Task {task_id} was cancelled, skipping progress updates"
                    )
                    return

                with app.state.task_locks[task_id]:
                    # Calculate progress percentage based on step
                    progress_map = {
                        "Initial Translation": 33,  # 1/3
                        "Editor Review": 67,  # 2/3 (updated from 66% for mathematical accuracy)
                        "Translator Revision": 100,  # 3/3
                    }

                    # Update the current step and mark it appropriately
                    step_state = details.get("status", "running")

                    if step_state == "completed":
                        current_task_status.update_step(
                            step_name=step_name,
                            step_details={"step_status": "completed", **details},
                            step_state="completed",
                        )
                        # Set progress to the current step's completion level
                        current_task_status.progress = progress_map.get(step_name, 0)
                        print(
                            f"[PROGRESS] Step '{step_name}' completed - progress: {current_task_status.progress}%"
                        )
                    elif step_state == "failed":
                        current_task_status.update_step(
                            step_name=step_name,
                            step_details={"step_status": "failed", **details},
                            step_state="failed",
                        )
                    else:  # running
                        current_task_status.update_step(
                            step_name=step_name,
                            step_details={"step_status": "running", **details},
                            step_state="running",
                        )
                        # For running steps, show progress corresponding to the previous step's completion
                        # This ensures running steps show their task completion progress, not 100%
                        if step_name == "Initial Translation":
                            # Initial Translation just started, show 0%
                            current_task_status.progress = 0
                        elif step_name == "Editor Review":
                            # Editor Review is running, show Initial Translation completion (33%)
                            current_task_status.progress = 33
                        elif step_name == "Translator Revision":
                            # Translator Revision is running, show Editor Review completion (67%)
                            current_task_status.progress = 67
                        else:
                            # Fallback to step-specific progress
                            current_task_status.progress = progress_map.get(
                                step_name, 0
                            )
                        print(
                            f"[PROGRESS] Step '{step_name}' running - progress: {current_task_status.progress}%"
                        )

                # Yield control to the event loop so the SSE stream can send the update
                await asyncio.sleep(0.01)

            with app.state.task_locks[task_id]:
                # Set task as running with the first step already initialized
                task_status.status = TaskStatusEnum.RUNNING
                task_status.started_at = datetime.now()
                task_status.current_step = "Initial Translation"
                task_status.step_details = {"provider": "AI", "step_status": "running"}
                task_status.step_states = {"Initial Translation": "running"}
                task_status.message = "Initializing workflow..."
                task_status.updated_at = datetime.now()

            # Setup workflow (poem retrieval, input creation, etc.)
            from src.vpsweb.repository.database import create_session
            from src.vpsweb.repository.service import RepositoryWebService
            from vpsweb.models.config import WorkflowMode
            from vpsweb.models.translation import TranslationInput, Language

            db = create_session()
            poem = RepositoryWebService(db).get_poem(poem_id)
            db.close()

            if not poem:
                raise ValueError(f"Poem not found: {poem_id}")

            translation_input = TranslationInput(
                original_poem=poem.original_text,
                source_lang=(
                    Language.CHINESE
                    if poem.source_language.startswith("zh")
                    else Language.ENGLISH
                ),
                target_lang=(
                    Language.ENGLISH if target_lang == "en" else Language.CHINESE
                ),
                metadata={
                    "id": poem.id,
                    "title": poem.poem_title,
                    "author": poem.poet_name,
                },
            )

            # Parse workflow mode
            try:
                workflow_mode = WorkflowMode(workflow_mode_str)
            except ValueError:
                workflow_mode = WorkflowMode.HYBRID  # fallback
                logger.warning(
                    f"Invalid workflow mode '{workflow_mode_str}', using HYBRID"
                )

            # Get workflow (recreate configuration)
            await self._load_configuration()
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

            # CRITICAL: Assign our callback to the workflow instance
            workflow.progress_callback = progress_callback

            # Check if task was cancelled before executing workflow
            if is_cancelled():
                print(
                    f"[WORKFLOW] ❌ Task {task_id} was CANCELLED before workflow execution"
                )
                logger.info(f"Task {task_id} was cancelled before workflow execution.")
                return

            # Now, execute the workflow as a single, encapsulated unit
            # The progress callback will handle real-time SSE updates
            print(f"[WORKFLOW] Starting workflow execution for task {task_id}")

            try:
                final_result = await workflow.execute(
                    translation_input, show_progress=False
                )
            except Exception as e:
                # Check if the workflow was cancelled during execution
                if is_cancelled():
                    print(
                        f"[WORKFLOW] ❌ Task {task_id} was CANCELLED during workflow execution"
                    )
                    logger.info(
                        f"Task {task_id} was cancelled during workflow execution."
                    )
                    return
                else:
                    # Re-raise the exception if it's not due to cancellation
                    raise e

            # Final cancellation check after workflow execution
            if is_cancelled():
                print(
                    f"[WORKFLOW] ❌ Task {task_id} was CANCELLED after workflow execution"
                )
                logger.info(f"Task {task_id} was cancelled after workflow execution.")
                return

            print(f"[WORKFLOW] Workflow execution completed for task {task_id}")

            with app.state.task_locks[task_id]:
                task_status.set_completed(
                    result=final_result.to_dict(),
                    message="Workflow completed successfully.",
                )
                # Ensure final progress is 100%
                task_status.progress = 100
                print(
                    f"[TASK STATUS] Task marked as completed for task {task_id} - progress: 100%"
                )

                # Ensure all step states are properly set to completed for final UI update
                task_status.step_states = {
                    "Initial Translation": "completed",
                    "Editor Review": "completed",
                    "Translator Revision": "completed",
                }
                print(
                    f"[STEP STATES] Final step states updated: all steps marked as completed"
                )

            # Save the final result to the database
            print(f"[DB SAVE] Starting database save for task {task_id}")
            try:
                # We need to get the poem_id and other details from the original input data
                # since workflow tasks are stored in memory, not the database
                poem_id = translation_input.metadata.get("id")
                if not poem_id:
                    print(
                        f"[DB SAVE] ❌ No poem_id found in translation input metadata"
                    )
                    return

                print(f"[DB SAVE] Using poem_id from input: {poem_id}")

                # Map workflow output to repository format
                translation_data = self._map_workflow_output_to_repository(
                    final_result, poem_id, workflow_mode.value
                )
                print(f"[DB SAVE] Mapped workflow output to repository format")

                # Create database session and save translation
                db = create_session()
                repository_service = RepositoryWebService(db)

                # Get source and target languages from input and convert to proper format
                source_lang_raw = (
                    translation_input.source_lang.value
                    if hasattr(translation_input.source_lang, "value")
                    else str(translation_input.source_lang)
                )
                target_lang_raw = (
                    translation_input.target_lang.value
                    if hasattr(translation_input.target_lang, "value")
                    else str(translation_input.target_lang)
                )

                # Convert language names to ISO codes using the same mapping as the repository
                lang_map = {
                    "english": "en",
                    "chinese": "zh-CN",
                    "french": "fr",
                    "spanish": "es",
                    "german": "de",
                    "italian": "it",
                    "portuguese": "pt",
                    "korean": "ko",
                    "russian": "ru",
                    "japanese": "ja",
                }

                source_lang = lang_map.get(source_lang_raw.lower(), source_lang_raw)
                target_lang = lang_map.get(target_lang_raw.lower(), target_lang_raw)

                print(
                    f"[DB SAVE] Language codes converted: {source_lang_raw}->{source_lang}, {target_lang_raw}->{target_lang}"
                )

                print(
                    f"[DB SAVE] Creating translation with poem_id: {poem_id}, {source_lang}->{target_lang}"
                )

                # Save translation to database using RepositoryWebService
                print(f"[DB SAVE] About to create translation...")

                # Import the required schema classes
                from vpsweb.repository.schemas import TranslationCreate, TranslatorType

                # Create TranslationCreate object with proper schema
                # The final translation is stored as 'revised_translation' in the mapped data
                final_translation = translation_data.get("revised_translation", "")
                if not final_translation or len(final_translation.strip()) < 10:
                    # Fallback to initial translation if revised translation is empty
                    final_translation = translation_data.get("initial_translation", "")

                print(
                    f"[DB SAVE] Final translation length: {len(final_translation)} characters"
                )

                translation_create = TranslationCreate(
                    poem_id=poem_id,
                    source_language=source_lang,
                    target_language=target_lang,
                    translated_text=final_translation,
                    translated_poem_title=(
                        translation_data.get("refined_translated_poem_title")
                        or translation_data.get("translated_poem_title", "")
                    ).strip(),
                    translated_poet_name=(
                        translation_data.get("refined_translated_poet_name")
                        or translation_data.get("translated_poet_name", "")
                    ).strip(),
                    translator_type=TranslatorType.AI,  # Use proper enum value
                    translator_info="qwen-max",  # Use actual model name
                    quality_rating=translation_data.get(
                        "quality_rating", None
                    ),  # Fixed field name
                    metadata=translation_data,
                )

                print(
                    f"[DB SAVE] Created TranslationCreate object with {len(translation_create.translated_text)} characters"
                )
                saved_translation = repository_service.create_translation(
                    translation_create
                )
                print(
                    f"[DB SAVE] ✅ Translation created with ID: {saved_translation.id}"
                )

                # Save JSON file using poet-based storage (CLI-compatible)
                print(
                    f"[DB SAVE] 📁 [STEP 9.5] Saving JSON file with poet-based storage"
                )
                try:
                    # Use the same poet-based storage as CLI workflow
                    json_path = self.storage_handler.save_translation_with_poet_dir(
                        output=final_result,
                        poet_name=translation_input.metadata.get("author", "Unknown"),
                        workflow_mode=workflow_mode.value,
                        include_mode_tag=True,
                    )
                    print(
                        f"[DB SAVE] ✅ [STEP 9.5 SUCCESS] JSON file saved to poet directory: {json_path}"
                    )
                except Exception as json_error:
                    print(
                        f"[DB SAVE] ⚠️ [STEP 9.5 WARNING] Failed to save JSON file: {json_error}"
                    )
                    # Continue execution - database save was successful

                db.close()
                print(f"[DB SAVE] Database connection closed")

            except Exception as db_error:
                print(
                    f"[DB SAVE] ❌ Failed to save translation to database: {db_error}"
                )
                import traceback

                traceback.print_exc()
                # Don't fail the task, just log the error

        except Exception as e:
            logger.error(
                f"Error in callback-based workflow task {task_id}: {e}", exc_info=True
            )
            if task_status:
                with app.state.task_locks[task_id]:
                    task_status.set_failed(
                        error=str(e), message="The workflow encountered an error."
                    )

        except Exception as e:
            print(
                f"❌ [STANDALONE] Error in standalone task for task_id {task_id}: {str(e)}"
            )
            import traceback

            traceback.print_exc()

            # Update error status in app.state
            try:
                if hasattr(app.state, "tasks") and task_id in app.state.tasks:
                    with app.state.task_locks[task_id]:
                        app.state.tasks[task_id].set_failed(
                            error=str(e),
                            message=f"Translation workflow failed: {str(e)}",
                        )
                        print(
                            f"❌ [STANDALONE] Error status updated in app.state for task_id: {task_id}"
                        )
            except Exception as app_state_error:
                print(
                    f"❌ [STANDALONE] Failed to update app.state error status for task_id {task_id}: {str(app_state_error)}"
                )

            # Also try to update error status in database for logging
            try:
                error_db = create_session()
                try:
                    error_repository_service = RepositoryWebService(error_db)
                    error_repository_service.update_workflow_task_status(
                        task_id, TaskStatus.FAILED, error_message=str(e)
                    )
                    error_db.commit()
                    print(
                        f"❌ [STANDALONE] Error status updated in database for task_id: {task_id}"
                    )
                finally:
                    error_db.close()
            except Exception as update_error:
                print(
                    f"❌ [STANDALONE] Failed to update database error status for task_id {task_id}: {str(update_error)}"
                )


async def get_vpsweb_adapter(
    poem_service: PoemService,
    repository_service: RepositoryWebService,
    config_path: Optional[str] = None,
):
    """
    Context manager for VPSWeb adapter instance.

    Args:
        poem_service: Repository poem service
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
