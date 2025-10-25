"""
VPSWeb Workflow Adapter for Web Interface Integration

This service layer bridges the existing VPSWeb translation workflow with the web interface,
providing async execution, background tasks, and repository integration.
"""

import asyncio
import logging
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
from .translation_service import TranslationService
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
        return {
            "poem_id": poem_id,
            "workflow_mode": workflow_mode,
            "source_lang": workflow_output.input.source_lang,
            "target_lang": workflow_output.input.target_lang,
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
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _execute_workflow_with_timeout(
        self,
        workflow: TranslationWorkflow,
        input_data: TranslationInput,
        timeout: int = DEFAULT_WORKFLOW_TIMEOUT,
    ) -> TranslationOutput:
        """
        Execute VPSWeb workflow with timeout protection.

        Args:
            workflow: VPSWeb workflow instance
            input_data: Translation input data
            timeout: Timeout in seconds

        Returns:
            TranslationOutput: Workflow execution result

        Raises:
            WorkflowTimeoutError: If workflow execution times out
            ConfigurationError: If workflow configuration is invalid
        """
        try:
            logger.info(f"Executing workflow with {timeout}s timeout")
            workflow_output = await asyncio.wait_for(
                workflow.execute(input_data, show_progress=False), timeout=timeout
            )
            logger.info("Workflow execution completed successfully")
            return workflow_output
        except asyncio.TimeoutError:
            logger.error(f"Workflow execution timed out after {timeout}s")
            raise WorkflowTimeoutError(
                f"Translation workflow timed out after {timeout} seconds."
            )
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            raise ConfigurationError(f"Workflow execution failed: {e}")

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

        # Create task ID and initialize in app.state (no database storage for personal use system)
        task_id = str(uuid.uuid4())

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

        # Synchronous execution temporarily removed - focus on background task execution
        # All translation workflows execute asynchronously for better user experience

        # Add to background tasks using FastAPI BackgroundTasks system
        if background_tasks:
            # Use FastAPI BackgroundTasks - this is the correct approach
            background_tasks.add_task(
                self._execute_workflow_task_standalone,
                task_id,
                poem_id,
                source_lang,
                target_lang,
                workflow_mode,
            )
            print(
                f"🚀 [DEBUG] Background task scheduled using STANDALONE approach for task_id: {task_id}"
            )
            logger.info(
                f"Background task scheduled using STANDALONE approach for task_id: {task_id}"
            )
        else:
            # Fallback: Execute as coroutine (this should not happen with proper FastAPI usage)
            logger.warning(
                "No background_tasks provided - falling back to direct coroutine execution"
            )
            asyncio.create_task(
                self._execute_workflow_task_standalone(
                    task_id, poem_id, source_lang, target_lang, workflow_mode
                )
            )

        return {
            "task_id": task_id,
            "status": TaskStatusEnum.PENDING,
            "message": "Translation workflow started",
        }

    def _execute_workflow_task_standalone(
        self,
        task_id: str,
        poem_id: str,
        source_lang: str,
        target_lang: str,
        workflow_mode_str: str,
    ) -> None:
        """
        Standalone background task execution that creates all its own resources.
        This fixes the FastAPI 0.106.0+ BackgroundTasks issue by being completely self-contained.
        Now uses FastAPI app.state for in-memory task tracking instead of database.

        Args:
            task_id: Workflow task ID
            poem_id: Poem ID to retrieve
            source_lang: Source language code
            target_lang: Target language code
            workflow_mode_str: Workflow mode as string
        """
        print(
            f"🚀 [STANDALONE] Starting standalone task execution for task_id: {task_id}"
        )

        # Import everything needed to be self-contained
        from src.vpsweb.repository.database import create_session
        from src.vpsweb.repository.service import RepositoryWebService
        from src.vpsweb.repository.schemas import TaskStatus
        from vpsweb.models.config import WorkflowMode
        from vpsweb.core.workflow import TranslationWorkflow
        from vpsweb.models.translation import TranslationInput, Language
        from ..task_models import TaskStatus as InMemoryTaskStatus, TaskStatusEnum

        # Get FastAPI app instance for app.state access
        # Import from main to avoid circular imports
        import sys
        import os

        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from ..main import app

        try:
            # Initialize task in app.state
            task_status = InMemoryTaskStatus(task_id=task_id)
            app.state.tasks[task_id] = task_status
            app.state.task_locks[task_id] = threading.Lock()

            print(
                f"✅ [STANDALONE] Task initialized in app.state for task_id: {task_id}"
            )

            # Update status to running
            with app.state.task_locks[task_id]:
                task_status.set_running("Translation workflow started")
                print(
                    f"🔄 [STANDALONE] Status updated to 'running' for task_id: {task_id}"
                )

            # Create database session for poem retrieval only
            db = create_session()
            try:
                repository_service = RepositoryWebService(db)
                print(
                    f"✅ [STANDALONE] DB session created for poem retrieval for task_id: {task_id}"
                )

                # Retrieve poem data
                poem = repository_service.get_poem(poem_id)
                if not poem:
                    raise ValueError(f"Poem not found: {poem_id}")

                # Create TranslationInput object for the workflow
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

                print(
                    f"📄 [STANDALONE] Poem retrieved: {poem.poem_title} for task_id: {task_id}"
                )

                # Parse workflow mode
                try:
                    workflow_mode = WorkflowMode(workflow_mode_str)
                except ValueError:
                    workflow_mode = WorkflowMode.HYBRID  # fallback
                    print(
                        f"⚠️ [STANDALONE] Invalid workflow mode '{workflow_mode_str}', using HYBRID"
                    )

                # Get workflow (recreate configuration)
                asyncio.run(self._load_configuration())
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
                print(f"✅ [STANDALONE] Workflow created for task_id: {task_id}")

                # Execute translation workflow with step progress tracking
                with app.state.task_locks[task_id]:
                    task_status.update_step(
                        step_name="Initial Translation",
                        step_details={"provider": "AI", "mode": workflow_mode_str},
                        step_percent=0,
                        message="Starting initial translation...",
                        step_state="running",
                    )
                    print(
                        f"📝 [STANDALONE] Step updated to 'Initial Translation' (running) for task_id: {task_id}"
                    )

                # Update progress during translation execution
                try:
                    # Step 1: Initial Translation in progress
                    with app.state.task_locks[task_id]:
                        task_status.set_progress(
                            10, "Initial Translation in progress..."
                        )
                        task_status.update_step(
                            step_name="Initial Translation",
                            step_details={"provider": "AI", "mode": workflow_mode_str},
                            step_percent=10,
                            message="AI is generating initial translation...",
                        )
                        print(
                            f"🔄 [STANDALONE] Step 1 progress updated (10%) for task_id: {task_id}"
                        )

                    translation_result = asyncio.run(
                        workflow.execute(translation_input)
                    )
                    print(
                        f"✅ [STANDALONE] Translation completed for task_id: {task_id}"
                    )

                    # Step 2: Editor Review completed
                    with app.state.task_locks[task_id]:
                        task_status.set_progress(66, "Editor review completed")
                        task_status.update_step(
                            step_name="Editor Review",
                            step_details={
                                "provider": "Deepseek",
                                "mode": "reasoning",
                                "status": "Completed",
                            },
                            step_percent=66,
                            message="Editor review completed successfully",
                            step_state="completed",
                        )
                        print(
                            f"✅ [STANDALONE] Step 2 progress updated (66%, completed) for task_id: {task_id}"
                        )

                    # Step 3: Translator Revision completed
                    with app.state.task_locks[task_id]:
                        task_status.set_progress(90, "Translator revision completed")
                        task_status.update_step(
                            step_name="Translator Revision",
                            step_details={
                                "provider": "AI",
                                "mode": "revision",
                                "status": "Completed",
                            },
                            step_percent=90,
                            message="Translator revision completed successfully",
                            step_state="completed",
                        )
                        print(
                            f"✅ [STANDALONE] Step 3 progress updated (90%, completed) for task_id: {task_id}"
                        )

                    # Update step progress for completed workflow
                    with app.state.task_locks[task_id]:
                        task_status.update_step(
                            step_name="Translation Complete",
                            step_details={
                                "total_tokens": translation_result.total_tokens,
                                "duration_seconds": translation_result.duration_seconds,
                                "workflow_id": translation_result.workflow_id,
                            },
                            step_percent=100,
                            message="Translation workflow completed successfully",
                        )
                        task_status.set_progress(100, "Translation completed!")
                        print(
                            f"✅ [STANDALONE] Final step update for task_id: {task_id}"
                        )

                except Exception as workflow_error:
                    print(
                        f"❌ [STANDALONE] Workflow execution error for task_id: {task_id}: {workflow_error}"
                    )
                    # Update error status in app.state
                    try:
                        if hasattr(app.state, "tasks") and task_id in app.state.tasks:
                            with app.state.task_locks[task_id]:
                                app.state.tasks[task_id].set_failed(
                                    error=str(workflow_error),
                                    message=f"Translation workflow failed: {str(workflow_error)}",
                                )
                                print(
                                    f"❌ [STANDALONE] Error status updated in app.state for task_id: {task_id}"
                                )
                    except Exception as app_state_error:
                        print(
                            f"❌ [STANDALONE] Failed to update app.state error status for task_id {task_id}: {str(app_state_error)}"
                        )
                    raise

                # Save result (convert TranslationOutput to JSON-serializable dict)
                def serialize_model(model):
                    """Convert Pydantic model to JSON-serializable dict"""
                    if hasattr(model, "dict"):
                        data = model.dict()
                    else:
                        data = model

                    # Convert datetime objects to ISO strings
                    def convert_datetimes(obj):
                        if isinstance(obj, dict):
                            return {k: convert_datetimes(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [convert_datetimes(item) for item in obj]
                        elif hasattr(obj, "isoformat"):
                            return obj.isoformat()
                        else:
                            return obj

                    return convert_datetimes(data)

                result_dict = {
                    "workflow_id": translation_result.workflow_id,
                    "input": serialize_model(translation_result.input),
                    "initial_translation": serialize_model(
                        translation_result.initial_translation
                    ),
                    "editor_review": serialize_model(translation_result.editor_review),
                    "revised_translation": serialize_model(
                        translation_result.revised_translation
                    ),
                    "full_log": translation_result.full_log,
                    "total_tokens": translation_result.total_tokens,
                    "duration_seconds": translation_result.duration_seconds,
                }
                # Update status to completed with 100% progress in app.state
                with app.state.task_locks[task_id]:
                    task_status.set_completed(
                        result=result_dict,
                        message="Translation workflow completed successfully",
                    )
                    print(
                        f"✅ [STANDALONE] Status updated to 'completed' (100%) in app.state for task_id: {task_id}"
                    )

                # Save translation result to database
                try:
                    from src.vpsweb.repository.schemas import (
                        TranslationCreate,
                        TranslatorType,
                    )

                    translation_service = db
                    from src.vpsweb.repository.service import RepositoryWebService

                    repository_service = RepositoryWebService(translation_service)

                    # Create TranslationCreate schema from result_dict
                    # Use the revised_translation as the final translated_text, fallback to initial_translation
                    revised = result_dict.get("revised_translation")
                    initial = result_dict.get("initial_translation", "")

                    # Handle case where translation fields might be dictionaries
                    if isinstance(revised, dict):
                        # Try different possible keys for translation text
                        # Based on analysis, the actual text is nested under 'revised_translation' key
                        final_translation = (
                            revised.get("revised_translation")  # Nested structure
                            or revised.get("translation")
                            or revised.get("text")
                            or revised.get("content")
                            or revised.get("result")
                            or str(revised)
                        )
                    elif isinstance(revised, str):
                        final_translation = revised
                    else:
                        final_translation = str(revised) if revised else initial

                    translation_create = TranslationCreate(
                        poem_id=poem_id,
                        translator_type=TranslatorType.AI,
                        translator_info="AI Workflow",
                        target_language=target_lang,
                        translated_text=final_translation,
                        metadata={
                            "workflow_mode": workflow_mode_str,
                            "workflow_id": result_dict.get("workflow_id"),
                            "total_tokens": result_dict.get("total_tokens", 0),
                            "duration_seconds": result_dict.get("duration_seconds", 0),
                            "full_log": result_dict.get("full_log", ""),
                            "source_content": result_dict.get("input", {}).get(
                                "content", ""
                            ),
                            "initial_translation": result_dict.get(
                                "initial_translation", ""
                            ),
                            "editor_review": result_dict.get("editor_review", ""),
                            "revised_translation": result_dict.get(
                                "revised_translation", ""
                            ),
                        },
                    )

                    # Save translation to database
                    repository_service.create_translation(translation_create)
                    print(
                        f"💾 [STANDALONE] Translation result saved to database for task_id: {task_id}"
                    )

                except Exception as db_save_error:
                    print(
                        f"⚠️ [STANDALONE] Failed to save translation to database for task_id {task_id}: {str(db_save_error)}"
                    )
                    # Don't fail the workflow, just log the error since app.state has the result

            finally:
                # Always close the database session
                db.close()
                print(f"🔒 [STANDALONE] Database session closed for task_id: {task_id}")

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

    def _execute_workflow_task_with_new_session(
        self, task_id: str, poem: Dict[str, Any], workflow_mode: WorkflowMode
    ) -> Dict[str, Any]:
        """
        Execute workflow task in background with separate database connection.

        This prevents SQLite transaction conflicts by creating a completely separate
        database connection for the background task execution.

        Note: This is a synchronous function for FastAPI BackgroundTasks compatibility.
        It uses asyncio.run() to execute async operations internally.
        """
        print(f"🌱 [BACKGROUND ENTRY] BACKGROUND TASK STARTING for task_id: {task_id}")
        logger.info(f"Starting background task execution for task_id: {task_id}")

        # Create async function to run the actual workflow
        async def _run_async_workflow():
            # Create a separate database engine for background task with WAL mode and NullPool
            from vpsweb.repository.settings import settings
            from sqlalchemy import create_engine, text
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy.pool import NullPool
            import time
            import random

            # Extract database file path and add WAL mode parameters
            db_url = settings.database_url
            if "sqlite:///" in db_url:
                # Remove existing parameters and add WAL mode for better concurrent access
                base_db_url = db_url.split("?")[0] if "?" in db_url else db_url
                wal_db_url = (
                    base_db_url + "?timeout=30&mode=rw&cache=shared&journal_mode=WAL"
                )
            else:
                wal_db_url = db_url

            # Use NullPool to prevent connection sharing issues in background tasks
            # Each database operation gets a fresh connection, avoiding locks
            background_engine = create_engine(
                wal_db_url,
                connect_args={"check_same_thread": False, "timeout": 30},
                poolclass=NullPool,  # Critical: No pooling for background tasks
                echo=False,
            )

            # Enable WAL mode and optimize for concurrent access
            with background_engine.connect() as conn:
                conn.execute(
                    text("PRAGMA journal_mode=WAL")
                )  # Enable Write-Ahead Logging
                conn.execute(
                    text("PRAGMA synchronous=NORMAL")
                )  # Balance safety/performance
                conn.execute(text("PRAGMA busy_timeout=30000"))  # 30 seconds timeout
                conn.execute(
                    text("PRAGMA foreign_keys=ON")
                )  # Enable foreign key constraints
                conn.execute(
                    text("PRAGMA temp_store=MEMORY")
                )  # Use memory for temp tables
                conn.execute(
                    text("PRAGMA mmap_size=268435456")
                )  # 256MB memory-mapped I/O
                conn.commit()

            BackgroundSessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=background_engine
            )
            db = BackgroundSessionLocal()
            logger.info(f"Created separate database connection for background task")

            # Add retry mechanism for database operations
            def retry_database_operation(max_retries=3, base_delay=0.1):
                def decorator(func):
                    def wrapper(*args, **kwargs):
                        for attempt in range(max_retries):
                            try:
                                return func(*args, **kwargs)
                            except Exception as e:
                                if (
                                    "database is locked" in str(e).lower()
                                    and attempt < max_retries - 1
                                ):
                                    # Exponential backoff with jitter
                                    delay = base_delay * (
                                        2**attempt
                                    ) + random.uniform(0, 0.1)
                                    logger.warning(
                                        f"Database locked on attempt {attempt + 1}, retrying in {delay:.2f}s"
                                    )
                                    time.sleep(delay)
                                else:
                                    raise

                    return wrapper

                return decorator

            # Apply retry to critical database operations
            original_commit = db.commit
            original_flush = db.flush

            @retry_database_operation(max_retries=3, base_delay=0.2)
            def safe_commit():
                original_commit()

            @retry_database_operation(max_retries=2, base_delay=0.1)
            def safe_flush():
                original_flush()

            # Replace methods with retry wrappers
            db.commit = safe_commit
            db.flush = safe_flush

            try:
                # Create new services with fresh database session
                poem_service = PoemService(db)
                translation_service = TranslationService(db)
                repository_service = RepositoryWebService(db)

                # Execute workflow with fresh services
                return await self._execute_workflow_task_with_services(
                    task_id,
                    poem,
                    workflow_mode,
                    poem_service,
                    translation_service,
                    repository_service,
                )

            except Exception as e:
                logger.error(f"Background workflow task {task_id} failed: {e}")
                # Update task status to failed
                try:
                    repository_service.update_workflow_task_status(
                        task_id, TaskStatus.FAILED, error_message=str(e)
                    )
                except:
                    logger.error(f"Failed to update task status to failed: {e}")
                raise
            finally:
                # Always close database session and engine
                try:
                    db.close()
                    background_engine.dispose()
                except:
                    pass

        # Execute the async workflow using asyncio.run()
        return asyncio.run(_run_async_workflow())

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
        logger.info(
            f"🚀 [STEP 1] Starting background workflow task execution for task_id: {task_id}"
        )

        # Get task from database
        logger.info(f"🔍 [STEP 2] Retrieving task from database for task_id: {task_id}")
        db_task = self.repository_service.get_workflow_task(task_id)
        if not db_task:
            logger.error(f"❌ [STEP 2 FAILED] Task not found in database: {task_id}")
            raise WorkflowExecutionError(f"Task not found: {task_id}")

        logger.info(
            f"✅ [STEP 2 SUCCESS] Task retrieved from database: poem_id={db_task.poem_id}, status={db_task.status}"
        )

        try:
            # Update task status in database
            logger.info(
                f"🔄 [STEP 3] Updating task status to RUNNING for task_id: {task_id}"
            )
            self.repository_service.update_workflow_task_status(
                task_id, TaskStatus.RUNNING, progress_percentage=0
            )
            logger.info(
                f"✅ [STEP 3 SUCCESS] Task status updated to RUNNING for task_id: {task_id}"
            )

            logger.info(
                f"📝 [STEP 4] Starting translation workflow task {task_id} for poem {db_task.poem_id}"
            )

            # Create workflow
            logger.info(
                f"⚙️ [STEP 5] Creating workflow instance for mode: {workflow_mode.value}"
            )
            workflow = await self._create_workflow(workflow_mode)
            logger.info(f"✅ [STEP 5 SUCCESS] Workflow instance created")

            # Prepare input
            logger.info(f"📋 [STEP 6] Preparing workflow input data")
            input_data = self._map_repository_to_workflow_input(
                poem, db_task.source_lang, db_task.target_lang
            )
            logger.info(
                f"✅ [STEP 6 SUCCESS] Workflow input prepared: {len(input_data)} fields"
            )

            # Execute workflow with timeout protection
            logger.info(
                f"🔄 [STEP 7] Executing VPSWeb translation workflow in {workflow_mode.value} mode (timeout: {DEFAULT_WORKFLOW_TIMEOUT}s)"
            )
            workflow_output = await self._execute_workflow_with_timeout(
                workflow, input_data, timeout=DEFAULT_WORKFLOW_TIMEOUT
            )
            logger.info(f"✅ [STEP 7 SUCCESS] Workflow execution completed")

            # Map output to repository format
            logger.info(f"📊 [STEP 8] Mapping workflow output to repository format")
            translation_data = self._map_workflow_output_to_repository(
                workflow_output, db_task.poem_id, db_task.workflow_mode
            )
            logger.info(f"✅ [STEP 8 SUCCESS] Output mapping completed")

            # Save to repository
            logger.info(f"💾 [STEP 9] Saving translation results to repository")
            saved_translation = await self.translation_service.create_translation(
                poem_id=db_task.poem_id,
                source_lang=db_task.source_lang,
                target_lang=db_task.target_lang,
                workflow_mode=db_task.workflow_mode,
                translation_data=translation_data,
            )
            logger.info(
                f"✅ [STEP 9 SUCCESS] Translation saved with ID: {saved_translation['id']}"
            )

            # Update task with result in database
            logger.info(f"🏁 [STEP 10] Updating task with final results")
            result_data = {
                "translation_id": saved_translation["id"],
                "total_tokens": workflow_output.total_tokens,
                "duration_seconds": workflow_output.duration_seconds,
                "total_cost": workflow_output.total_cost,
            }
            repository_service.set_workflow_task_result(task_id, result_data)
            repository_service.update_workflow_task_status(
                task_id, TaskStatus.COMPLETED, progress_percentage=100
            )
            logger.info(f"✅ [STEP 10 SUCCESS] Task marked as completed")

            logger.info(
                f"🎉 [WORKFLOW COMPLETE] Translation workflow task {task_id} completed successfully"
            )

            return {
                "task_id": task_id,
                "status": TaskStatus.COMPLETED,
                "translation_id": saved_translation["id"],
                "total_tokens": workflow_output.total_tokens,
                "duration_seconds": workflow_output.duration_seconds,
                "total_cost": workflow_output.total_cost,
                "message": "Translation completed successfully",
            }

        except WorkflowTimeoutError as e:
            logger.error(
                f"⏰ [TIMEOUT ERROR] VPSWeb workflow timed out for task {task_id}: {e}"
            )
            # Update task status in database
            logger.error(f"🔴 [FAILED] Updating task status to FAILED due to timeout")
            self.repository_service.update_workflow_task_status(
                task_id, TaskStatus.FAILED, progress_percentage=0, error_message=str(e)
            )

            raise WorkflowExecutionError(f"Workflow execution timed out: {e}")

        except WorkflowError as e:
            logger.error(
                f"❌ [WORKFLOW ERROR] VPSWeb workflow failed for task {task_id}: {e}"
            )
            # Update task status in database
            logger.error(
                f"🔴 [FAILED] Updating task status to FAILED due to workflow error"
            )
            self.repository_service.update_workflow_task_status(
                task_id, TaskStatus.FAILED, progress_percentage=0, error_message=str(e)
            )

            raise WorkflowExecutionError(f"Workflow execution failed: {e}")

        except Exception as e:
            logger.error(
                f"💥 [UNEXPECTED ERROR] Task {task_id} failed with unexpected error: {e}"
            )
            logger.error(
                f"🔴 [FAILED] Updating task status to FAILED due to unexpected error"
            )
            logger.error(f"Unexpected error in workflow task {task_id}: {e}")
            # Update task status in database
            self.repository_service.update_workflow_task_status(
                task_id, TaskStatus.FAILED, progress_percentage=0, error_message=str(e)
            )

            raise WorkflowExecutionError(f"Unexpected error: {e}")

    async def _execute_workflow_task_with_services(
        self,
        task_id: str,
        poem: Dict[str, Any],
        workflow_mode: WorkflowMode,
        poem_service: "PoemService",
        translation_service: "TranslationService",
        repository_service: "RepositoryWebService",
    ) -> Dict[str, Any]:
        """
        Execute the actual workflow task with provided services.

        Args:
            task_id: Unique task identifier
            poem: Poem data from repository
            workflow_mode: Workflow mode to use
            poem_service: Fresh poem service with isolated database session
            translation_service: Fresh translation service with isolated database session
            repository_service: Fresh repository service with isolated database session

        Returns:
            Task result with translation data

        Raises:
            WorkflowExecutionError: If execution fails
        """
        # Get task from database
        db_task = repository_service.get_workflow_task(task_id)
        if not db_task:
            raise WorkflowExecutionError(f"Task not found: {task_id}")

        try:
            # Update task status in database
            repository_service.update_workflow_task_status(
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

            # Execute workflow with timeout protection
            logger.info(
                f"Executing VPSWeb translation workflow in {workflow_mode.value} mode"
            )
            workflow_output = await self._execute_workflow_with_timeout(
                workflow, input_data, timeout=DEFAULT_WORKFLOW_TIMEOUT
            )

            # Map output to repository format
            translation_data = self._map_workflow_output_to_repository(
                workflow_output, db_task.poem_id, db_task.workflow_mode
            )

            # Save to repository using fresh translation service
            logger.info(f"Saving translation results to repository")
            # Filter translation_data to only include valid fields for create_translation
            filtered_translation_data = {
                k: v
                for k, v in translation_data.items()
                if k
                not in [
                    "workflow_id",
                    "poem_id",
                    "source_lang",
                    "target_lang",
                    "workflow_mode",
                ]
            }
            saved_translation = await translation_service.create_translation(
                poem_id=translation_data["poem_id"],
                source_lang=translation_data["source_lang"],
                target_lang=translation_data["target_lang"],
                workflow_mode=translation_data["workflow_mode"],
                translation_data=filtered_translation_data,
            )

            # Update task status in database using fresh repository service
            repository_service.update_workflow_task_status(
                task_id, TaskStatus.COMPLETED, progress_percentage=100
            )

            logger.info(f"Translation workflow task {task_id} completed successfully")

            return {
                "task_id": task_id,
                "status": TaskStatus.COMPLETED,
                "translation_id": saved_translation["id"],
                "total_tokens": workflow_output.total_tokens,
                "duration_seconds": workflow_output.duration_seconds,
                "total_cost": workflow_output.total_cost,
                "message": "Translation completed successfully",
            }

        except WorkflowTimeoutError as e:
            logger.error(f"VPSWeb workflow timed out for task {task_id}: {e}")
            # Update task status in database
            repository_service.update_workflow_task_status(
                task_id, TaskStatus.FAILED, progress_percentage=0, error_message=str(e)
            )
            raise WorkflowExecutionError(f"Workflow execution timed out: {e}")

        except WorkflowError as e:
            logger.error(f"VPSWeb workflow failed for task {task_id}: {e}")
            # Update task status in database
            repository_service.update_workflow_task_status(
                task_id, TaskStatus.FAILED, progress_percentage=0, error_message=str(e)
            )
            raise WorkflowExecutionError(f"Workflow execution failed: {e}")

        except Exception as e:
            logger.error(f"Unexpected error in workflow task {task_id}: {e}")
            # Update task status in database
            repository_service.update_workflow_task_status(
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
