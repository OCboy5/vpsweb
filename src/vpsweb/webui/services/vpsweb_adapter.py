"""
Phase 3B: Refactored VPSWeb Workflow Adapter V2.

This refactored adapter uses the new interface-based architecture with
dependency injection, providing better modularity and testability.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks

from vpsweb.core.interfaces import IConfigurationService, IWorkflowOrchestrator
from vpsweb.core.workflow_orchestrator import WorkflowConfig, WorkflowStep
from vpsweb.models.translation import TranslationInput
from vpsweb.repository.service import RepositoryWebService

from ..task_models import TaskStatusEnum
from .poem_service import PoemService


class VPSWebWorkflowAdapterV2:
    """
    Refactored VPSWeb workflow adapter using dependency injection and interfaces.

    This adapter provides:
    - Clean separation of concerns with interface-based design
    - Dependency injection for better testability
    - Simplified workflow execution delegation
    - Maintained backward compatibility with existing API
    """

    def __init__(
        self,
        poem_service: PoemService,
        repository_service: RepositoryWebService,
        workflow_orchestrator: IWorkflowOrchestrator,
        config_service: Optional[IConfigurationService] = None,
    ):
        """
        Initialize the refactored VPSWeb workflow adapter.

        Args:
            poem_service: Repository poem service
            repository_service: Repository service for database operations
            workflow_orchestrator: Interface-based workflow orchestrator
            config_service: Optional configuration service
        """
        self.poem_service = poem_service
        self.repository_service = repository_service
        self.workflow_orchestrator = workflow_orchestrator
        self.config_service = config_service

        self.logger = logging.getLogger(__name__)

        self.logger.info("VPSWebWorkflowAdapterV2 initialized with dependency injection")

    def _convert_language_code(self, lang_code: str) -> str:
        """
        Convert ISO language code to display name for VPSWeb workflow.

        Args:
            lang_code: ISO language code (e.g., 'en', 'zh-CN')

        Returns:
            Display name (e.g., 'English', 'Chinese')
        """
        # Language mapping for VPSWeb compatibility
        language_mapping = {
            "en": "English",
            "en-US": "English",
            "en-GB": "English",
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

        # Fallback to supported languages or default to English
        return language_mapping.get(lang_code, "English")

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
            metadata={
                "poem_id": poem_data.get("id"),
                "title": poem_data.get("title", "Unknown"),
                "author": poem_data.get("author", "Unknown"),
                "source_lang_iso": source_lang,
                "target_lang_iso": target_lang,
            },
        )

    def _create_workflow_config_from_mode(self, workflow_mode: str) -> WorkflowConfig:
        """
        Create workflow configuration from mode string.

        Args:
            workflow_mode: Workflow mode ('reasoning', 'non_reasoning', 'hybrid')

        Returns:
            WorkflowConfig for the orchestrator
        """
        # Map workflow modes to configurations
        step_configs = {
            "reasoning": {
                "provider": "deepseek",
                "model": "deepseek-reasoner",
                "temperature": 0.3,
                "max_tokens": 2000,
                "timeout": 60.0,
                "retry_attempts": 2,
            },
            "non_reasoning": {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "temperature": 0.7,
                "max_tokens": 1500,
                "timeout": 45.0,
                "retry_attempts": 3,
            },
            "hybrid": {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "temperature": 0.5,
                "max_tokens": 1800,
                "timeout": 50.0,
                "retry_attempts": 2,
            },
        }

        config = step_configs.get(workflow_mode, step_configs["hybrid"])

        return WorkflowConfig(
            name=f"translation_{workflow_mode}",
            description=f"Translation workflow in {workflow_mode} mode",
            steps=[
                # Initial Translation Step
                WorkflowStep(
                    name="Initial Translation",
                    provider=config["provider"],
                    model=config["model"],
                    prompt_template="templates/initial_translation.xml",
                    temperature=config["temperature"],
                    max_tokens=config["max_tokens"],
                    timeout=config["timeout"],
                    retry_attempts=config["retry_attempts"],
                    required_fields=["translation", "confidence"],
                ),
                # Editor Review Step
                WorkflowStep(
                    name="Editor Review",
                    provider=config["provider"],
                    model=config["model"],
                    prompt_template="templates/editor_review.xml",
                    temperature=0.3,
                    max_tokens=config["max_tokens"] // 2,
                    timeout=config["timeout"] / 2,
                    retry_attempts=1,
                    required_fields=["suggestions", "assessment"],
                ),
                # Translator Revision Step
                WorkflowStep(
                    name="Translator Revision",
                    provider=config["provider"],
                    model=config["model"],
                    prompt_template="templates/translator_revision.xml",
                    temperature=0.4,
                    max_tokens=config["max_tokens"],
                    timeout=config["timeout"],
                    retry_attempts=1,
                    required_fields=["final_translation", "quality_rating"],
                ),
            ],
            metadata={"mode": workflow_mode, "adapter_version": "v2"},
        )

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
        Execute VPSWeb translation workflow using the refactored orchestrator.

        Args:
            poem_id: ID of the poem to translate
            source_lang: Source language code
            target_lang: Target language code
            workflow_mode: Workflow mode (reasoning, non_reasoning, hybrid)
            background_tasks: FastAPI BackgroundTasks (kept for compatibility)
            synchronous: If True, execute synchronously and return result

        Returns:
            Dictionary with task info for SSE tracking

        Raises:
            WorkflowExecutionError: If workflow execution fails
        """
        self.logger.info(
            f"execute_translation_workflow called with poem_id={poem_id}, "
            f"source_lang={source_lang}, target_lang={target_lang}, workflow_mode={workflow_mode}"
        )

        # Validate inputs
        if not poem_id:
            raise WorkflowExecutionError("Poem ID is required")

        if source_lang == target_lang:
            raise WorkflowExecutionError("Source and target languages must be different")

        # Retrieve poem from repository
        poem = await self.poem_service.get_poem(poem_id)
        if not poem:
            raise WorkflowExecutionError(f"Poem not found: {poem_id}")

        # Create task ID and initialize tracking
        task_id = str(uuid.uuid4())
        self.logger.info(f"Created task ID: {task_id}")

        # Get FastAPI app instance for app.state access
        from vpsweb.webui.main import app

        # Initialize task in app.state for SSE compatibility
        from vpsweb.webui.task_models import TaskStatus as InMemoryTaskStatus

        task_status = InMemoryTaskStatus(task_id=task_id)
        app.state.tasks[task_id] = task_status
        app.state.task_locks[task_id] = __import__("threading").Lock()

        # Set initial workflow step states
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

        # Schedule asynchronous execution
        asyncio.create_task(
            self._execute_workflow_with_progress_callback(
                task_id,
                poem,
                source_lang,
                target_lang,
                workflow_mode,
            )
        )

        self.logger.info(f"Asynchronous workflow task {task_id} has been scheduled.")

        return {
            "task_id": task_id,
            "status": TaskStatusEnum.PENDING,
            "message": "Translation workflow started with refactored orchestrator",
        }

    async def _execute_workflow_with_progress_callback(
        self,
        task_id: str,
        poem: Dict[str, Any],
        source_lang: str,
        target_lang: str,
        workflow_mode_str: str,
    ) -> None:
        """
        Execute workflow using the refactored orchestrator with progress tracking.

        Args:
            task_id: Workflow task ID
            poem: Poem data dictionary
            source_lang: Source language code
            target_lang: Target language code
            workflow_mode_str: Workflow mode as string
        """
        self.logger.info(f"Starting refactored workflow execution for task_id: {task_id}")

        # Get FastAPI app instance
        from vpsweb.webui.main import app

        task_status = app.state.tasks.get(task_id)
        if not task_status:
            self.logger.error(f"Task {task_id} not found in app.state")
            return

        try:
            # Map poem data to workflow input
            workflow_input = self._map_repository_to_workflow_input(poem, source_lang, target_lang)

            # Create workflow configuration
            workflow_config = self._create_workflow_config_from_mode(workflow_mode_str)

            # Create progress callback for SSE compatibility
            async def progress_callback(step_name: str, details: Dict[str, Any]) -> None:
                # Skip updates if task is already completed or failed
                current_task_status = app.state.tasks.get(task_id)
                if not current_task_status or current_task_status.status in [
                    "completed",
                    "failed",
                ]:
                    return

                with app.state.task_locks[task_id]:
                    # Calculate progress percentage based on step
                    progress_map = {
                        "Initial Translation": 33,
                        "Editor Review": 67,
                        "Translator Revision": 100,
                    }

                    step_state = details.get("status", "running")

                    if step_state == "completed":
                        current_task_status.update_step(
                            step_name=step_name,
                            step_details={
                                "step_status": "completed",
                                **details,
                            },
                            step_state="completed",
                        )
                        current_task_status.progress = progress_map.get(step_name, 0)
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
                        # Set progress to previous step's completion
                        if step_name == "Initial Translation":
                            current_task_status.progress = 0
                        elif step_name == "Editor Review":
                            current_task_status.progress = 33
                        elif step_name == "Translator Revision":
                            current_task_status.progress = 67

                # Yield control to event loop for SSE updates
                await asyncio.sleep(0.01)

            # Set task as running
            with app.state.task_locks[task_id]:
                task_status.status = TaskStatusEnum.RUNNING
                task_status.started_at = datetime.now()
                task_status.current_step = "Initial Translation"
                task_status.step_details = {
                    "provider": "AI",
                    "step_status": "running",
                }
                task_status.message = "Executing translation workflow..."

            # Execute workflow using the refactored orchestrator
            result = await self.workflow_orchestrator.execute_workflow(
                workflow_config,
                workflow_input.to_dict(),
                progress_callback=progress_callback,
            )

            # Process result and save to database
            if result.status.value == "completed":
                # Debug: Log the workflow result structure
                self.logger.info(f"🔍 [DEBUG] Workflow result type: {type(result)}")
                self.logger.info(
                    f"🔍 [DEBUG] Workflow result dir: {[attr for attr in dir(result) if not attr.startswith('_')]}"
                )
                self.logger.info(f"🔍 [DEBUG] Results type: {type(result.results)}")
                self.logger.info(
                    f"🔍 [DEBUG] Results keys: {list(result.results.keys()) if hasattr(result.results, 'keys') else 'N/A'}"
                )

                # Debug each step result
                if hasattr(result.results, "items"):
                    for step_name, step_data in result.results.items():
                        self.logger.info(f"🔍 [DEBUG] Step '{step_name}' type: {type(step_data)}")
                        if hasattr(step_data, "__dict__"):
                            step_attrs = {k: v for k, v in step_data.__dict__.items() if not k.startswith("_")}
                            self.logger.info(f"🔍 [DEBUG] Step '{step_name}' attrs: {list(step_attrs.keys())}")
                            # Check for duration and cost specifically
                            if "duration" in step_attrs:
                                self.logger.info(f"🔍 [DEBUG] Step '{step_name}' duration: {step_attrs['duration']}")
                            if "cost" in step_attrs:
                                self.logger.info(f"🔍 [DEBUG] Step '{step_name}' cost: {step_attrs['cost']}")
                        elif isinstance(step_data, dict):
                            self.logger.info(f"🔍 [DEBUG] Step '{step_name}' dict keys: {list(step_data.keys())}")
                            if "duration" in step_data:
                                self.logger.info(f"🔍 [DEBUG] Step '{step_name}' duration: {step_data['duration']}")
                            if "cost" in step_data:
                                self.logger.info(f"🔍 [DEBUG] Step '{step_name}' cost: {step_data['cost']}")

                await self._save_workflow_result(
                    task_id,
                    result,
                    poem["id"],
                    source_lang,
                    target_lang,
                    workflow_mode_str,
                )

                # Mark task as completed
                with app.state.task_locks[task_id]:
                    task_status.set_completed(
                        result={
                            "workflow_result": result.__dict__,
                            "adapter_version": "v2",
                            "execution_time": result.execution_time,
                            "total_tokens": result.total_tokens_used,
                        },
                        message="Translation workflow completed successfully",
                    )
                    task_status.progress = 100

                self.logger.info(f"Workflow {task_id} completed successfully in {result.execution_time:.2f}s")
            else:
                # Workflow failed
                error_msg = "; ".join(result.errors) if result.errors else "Unknown error"
                with app.state.task_locks[task_id]:
                    task_status.set_failed(
                        error=error_msg,
                        message="Translation workflow failed",
                    )

                self.logger.error(f"Workflow {task_id} failed: {error_msg}")

        except Exception as e:
            self.logger.error(
                f"Error in refactored workflow task {task_id}: {e}",
                exc_info=True,
            )

            # Update task status to failed
            if task_status:
                with app.state.task_locks[task_id]:
                    task_status.set_failed(
                        error=str(e),
                        message="Translation workflow encountered an error",
                    )

    async def _save_workflow_result(
        self,
        task_id: str,
        workflow_result: Any,
        poem_id: str,
        source_lang: str,
        target_lang: str,
        workflow_mode: str,
    ) -> None:
        """
        Save workflow result to database and create AI logs.

        Args:
            task_id: Task identifier
            workflow_result: Result from workflow orchestrator
            poem_id: Source poem ID
            source_lang: Source language code
            target_lang: Target language code
            workflow_mode: Workflow mode used
        """
        self.logger.info(f"Saving workflow result for task {task_id}")

        try:
            # Convert workflow result to repository format
            # This would need to be adapted based on the actual workflow result structure
            translation_data = {
                "poem_id": poem_id,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "workflow_mode": workflow_mode,
                "execution_time": workflow_result.execution_time,
                "total_tokens": workflow_result.total_tokens_used,
                "adapter_version": "v2",
                "task_id": task_id,
                "results": workflow_result.results,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # Save translation using repository service
            # Note: This would need to be adapted to match actual schema
            self.logger.info(f"Translation data prepared for saving: {len(str(translation_data))} chars")

            # TODO: Implement actual database save with proper schema mapping
            # saved_translation = self.repository_service.create_translation(translation_data)
            # self.logger.info(f"Translation saved with ID: {saved_translation.id}")

        except Exception as e:
            self.logger.error(f"Failed to save workflow result: {e}", exc_info=True)
            # Don't fail the workflow, just log the error

    def get_workflow_status(self, workflow_id: str) -> Optional[str]:
        """
        Get the status of a workflow.

        Args:
            workflow_id: Workflow ID to check

        Returns:
            Current workflow status or None if not found
        """
        # This method delegates to the orchestrator
        # Note: This is async in the interface, but kept sync for backward compatibility
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, we can't use loop.run_until_complete
                # This is a limitation of the current design
                return None
            else:
                return asyncio.run(self.workflow_orchestrator.get_workflow_status(workflow_id))
        except Exception:
            return None

    def cancel_workflow(self, workflow_id: str) -> bool:
        """
        Cancel a running workflow.

        Args:
            workflow_id: Workflow ID to cancel

        Returns:
            True if cancelled successfully, False otherwise
        """
        # This method delegates to the orchestrator
        # Note: This is async in the interface, but kept sync for backward compatibility
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                return False
            else:
                return asyncio.run(self.workflow_orchestrator.cancel_workflow(workflow_id))
        except Exception:
            return False

    def list_workflows(self) -> list:
        """
        List all available workflow configurations.

        Returns:
            List of workflow configuration names
        """
        # This method delegates to the orchestrator
        # Note: This is async in the interface, but kept sync for backward compatibility
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                return []
            else:
                return asyncio.run(self.workflow_orchestrator.list_workflows())
        except Exception:
            return []


class WorkflowExecutionError(Exception):
    """Exception for workflow execution errors."""
