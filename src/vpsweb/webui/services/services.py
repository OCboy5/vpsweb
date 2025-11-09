"""
Phase 3C: Enhanced Service Layer Implementations.

This module provides concrete implementations of the service layer interfaces,
with dependency injection support and comprehensive error handling.
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from .interfaces import (
    IPoemServiceV2,
    ITranslationServiceV2,
    IPoetServiceV2,
    IWorkflowServiceV2,
    IStatisticsServiceV2,
    ITemplateServiceV2,
    IExceptionHandlerServiceV2,
    IPerformanceServiceV2,
    ITaskManagementServiceV2,
    ISSEServiceV2,
    IConfigServiceV2,
)
from ...utils.language_mapper import LanguageMapper
from vpsweb.repository.service import RepositoryWebService
from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.core.container import DIContainer
from vpsweb.utils.tools_phase3a import (
    ErrorCollector,
    PerformanceMonitor,
    generate_unique_id,
    deep_merge_dict,
)


class PoemServiceV2(IPoemServiceV2):
    """Enhanced poem service with dependency injection."""

    def __init__(
        self,
        repository_service: RepositoryWebService,
        performance_service: Optional[IPerformanceServiceV2] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.repository_service = repository_service
        self.performance_service = performance_service
        self.logger = logger or logging.getLogger(__name__)
        self.error_collector = ErrorCollector()

    async def get_poem_list(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get paginated list of poems with filtering options."""
        start_time = time.time()

        try:
            # Use repository service for data access
            poems = self.repository_service.repo.poems.get_multi(
                skip=skip,
                limit=limit,
                poet_name=None,
                language=language,
                title_search=search
            )

            # Get total count for pagination
            total_count = self.repository_service.repo.poems.count()

            result = {
                "poems": poems,
                "total_count": total_count,
                "pagination": {
                    "skip": skip,
                    "limit": limit,
                    "has_next": skip + limit < total_count,
                    "has_prev": skip > 0
                },
                "filters": {
                    "search": search,
                    "language": language
                }
            }

            # Log performance
            if self.performance_service:
                await self.performance_service.log_request_performance(
                    "get_poem_list",
                    "poems",
                    200,
                    (time.time() - start_time) * 1000,
                    {"total_count": total_count, "returned_count": len(poems)}
                )

            return result

        except Exception as e:
            self.error_collector.add_error(e, {
                "operation": "get_poem_list",
                "parameters": {"skip": skip, "limit": limit, "search": search, "language": language}
            })
            self.logger.error(f"Error getting poem list: {e}")
            raise

    async def get_poem_detail(self, poem_id: str) -> Dict[str, Any]:
        """Get detailed poem information including translations."""
        try:
            # Get poem
            poem = self.repository_service.repo.poems.get_by_id(poem_id)
            if not poem:
                raise ValueError(f"Poem not found: {poem_id}")

            # Get translations for this poem
            translations = self.repository_service.repo.translations.get_by_poem(poem_id)

            result = {
                "poem": poem,
                "translations": translations,
                "translation_count": len(translations),
                "last_updated": max([t.created_at for t in translations] + [poem.created_at]) if translations else poem.created_at
            }

            return result

        except Exception as e:
            self.error_collector.add_error(e, {"poem_id": poem_id})
            self.logger.error(f"Error getting poem detail: {e}")
            raise

    async def get_poem(self, poem_id: str) -> Dict[str, Any]:
        """Get basic poem information."""
        try:
            # Get poem
            poem = self.repository_service.repo.poems.get_by_id(poem_id)
            if not poem:
                raise ValueError(f"Poem not found: {poem_id}")

            # Convert to dictionary format expected by templates
            result = {
                "id": poem.id,
                "poet_name": poem.poet_name,
                "poem_title": poem.poem_title,
                "source_language": poem.source_language,
                "content": poem.original_text,
                "metadata_json": poem.metadata_json,
                "created_at": poem.created_at.isoformat() if poem.created_at else None,
                "updated_at": poem.updated_at.isoformat() if poem.updated_at else None,
                "translation_count": poem.translation_count,
                "ai_translation_count": poem.ai_translation_count,
                "human_translation_count": poem.human_translation_count,
            }

            return result

        except Exception as e:
            self.error_collector.add_error(e, {"poem_id": poem_id})
            self.logger.error(f"Error getting poem: {e}")
            raise

    async def create_poem(self, poem_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new poem with validation."""
        try:
            # Validate required fields
            if not poem_data.get("title"):
                raise ValueError("Poem title is required")
            if not poem_data.get("content"):
                raise ValueError("Poem content is required")
            if not poem_data.get("author"):
                raise ValueError("Poem author is required")

            # Additional validation
            if len(poem_data["content"]) < 10:
                raise ValueError("Poem content must be at least 10 characters")

            # Create poem using repository service
            poem = self.repository_service.repo.poems.create(poem_data)

            result = {
                "success": True,
                "poem": poem,
                "message": "Poem created successfully"
            }

            return result

        except Exception as e:
            self.error_collector.add_error(e, {"poem_data": poem_data})
            self.logger.error(f"Error creating poem: {e}")
            raise

    async def update_poem(self, poem_id: str, poem_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing poem."""
        try:
            # Check if poem exists
            existing_poem = self.repository_service.repo.poems.get_by_id(poem_id)
            if not existing_poem:
                raise ValueError(f"Poem not found: {poem_id}")

            # Update poem
            updated_poem = self.repository_service.repo.poems.update(poem_id, poem_data)

            result = {
                "success": True,
                "poem": updated_poem,
                "message": "Poem updated successfully"
            }

            return result

        except Exception as e:
            self.error_collector.add_error(e, {"poem_id": poem_id, "poem_data": poem_data})
            self.logger.error(f"Error updating poem: {e}")
            raise

    async def delete_poem(self, poem_id: str) -> bool:
        """Delete a poem and related data."""
        try:
            # Check if poem exists
            existing_poem = self.repository_service.repo.poems.get_by_id(poem_id)
            if not existing_poem:
                return False

            # Delete poem (cascade should handle related translations)
            success = self.repository_service.repo.poems.delete(poem_id)

            if success:
                self.logger.info(f"Successfully deleted poem: {poem_id}")
            else:
                self.logger.warning(f"Failed to delete poem: {poem_id}")

            return success

        except Exception as e:
            self.error_collector.add_error(e, {"poem_id": poem_id})
            self.logger.error(f"Error deleting poem: {e}")
            return False

    async def get_poem_statistics(self) -> Dict[str, Any]:
        """Get overall poem statistics."""
        try:
            total_poems = self.repository_service.repo.poems.count()
            recent_poems = self.repository_service.repo.poems.get_multi(skip=0, limit=10)

            # Calculate statistics
            stats = {
                "total_poems": total_poems,
                "recent_poems": len(recent_poems),
                "last_updated": recent_poems[0]["created_at"] if recent_poems else None,
                "average_content_length": 0,  # Would need additional calculation
                "language_distribution": {},  # Would need additional calculation
            }

            return stats

        except Exception as e:
            self.error_collector.add_error(e)
            self.logger.error(f"Error getting poem statistics: {e}")
            return {"total_poems": 0, "recent_poems": 0}


class TranslationServiceV2(ITranslationServiceV2):
    """Enhanced translation service with dependency injection."""

    def __init__(
        self,
        repository_service: RepositoryWebService,
        performance_service: Optional[IPerformanceServiceV2] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.repository_service = repository_service
        self.performance_service = performance_service
        self.logger = logger or logging.getLogger(__name__)
        self.error_collector = ErrorCollector()

    async def get_translation_list(
        self,
        skip: int = 0,
        limit: int = 100,
        poem_id: Optional[str] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get paginated list of translations with filtering."""
        try:
            translations = self.repository_service.repo.translations.get_multi(
                skip=skip,
                limit=limit,
                poem_id=poem_id,
                source_lang=source_lang,
                target_lang=target_lang
            )

            total_count = self.repository_service.repo.translations.count(
                poem_id=poem_id,
                source_lang=source_lang,
                target_lang=target_lang
            )

            result = {
                "translations": translations,
                "total_count": total_count,
                "pagination": {
                    "skip": skip,
                    "limit": limit,
                    "has_next": skip + limit < total_count,
                    "has_prev": skip > 0
                },
                "filters": {
                    "poem_id": poem_id,
                    "source_lang": source_lang,
                    "target_lang": target_lang
                }
            }

            return result

        except Exception as e:
            self.error_collector.add_error(e, {
                "operation": "get_translation_list",
                "filters": {"poem_id": poem_id, "source_lang": source_lang, "target_lang": target_lang}
            })
            self.logger.error(f"Error getting translation list: {e}")
            raise

    async def get_translation_detail(self, translation_id: str) -> Dict[str, Any]:
        """Get detailed translation information."""
        try:
            translation = self.repository_service.repo.translations.get_by_id(translation_id)
            if not translation:
                raise ValueError(f"Translation not found: {translation_id}")

            # Get related poem
            poem = self.repository_service.repo.poems.get_by_id(translation.poem_id)

            result = {
                "translation": translation,
                "poem": poem,
                "metadata": {
                    "has_workflow_steps": translation.has_workflow_steps,
                    "translation_type": translation.translator_type,
                    "quality_rating": translation.quality_rating
                }
            }

            return result

        except Exception as e:
            self.error_collector.add_error(e, {"translation_id": translation_id})
            self.logger.error(f"Error getting translation detail: {e}")
            raise

    async def get_translation_comparison(self, translation_id: str) -> Dict[str, Any]:
        """Get comparison data for a translation."""
        try:
            # This would implement comparison logic
            # For now, return basic data
            translation = self.repository_service.repo.translations.get_by_id(translation_id)
            if not translation:
                raise ValueError(f"Translation not found: {translation_id}")

            # Get other translations of the same poem for comparison
            other_translations = self.repository_service.repo.translations.get_by_poem(
                translation.poem_id,
                exclude_id=translation_id
            )

            result = {
                "translation": translation,
                "other_translations": other_translations,
                "comparison_count": len(other_translations)
            }

            return result

        except Exception as e:
            self.error_collector.add_error(e, {"translation_id": translation_id})
            self.logger.error(f"Error getting translation comparison: {e}")
            raise

    async def create_translation(self, translation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new translation with validation."""
        try:
            # Validate required fields
            if not translation_data.get("poem_id"):
                raise ValueError("Poem ID is required")
            if not translation_data.get("translated_content"):
                raise ValueError("Translated content is required")

            # Check if poem exists
            poem = self.repository_service.repo.poems.get_by_id(translation_data["poem_id"])
            if not poem:
                raise ValueError(f"Poem not found: {translation_data['poem_id']}")

            # Create translation
            translation = self.repository_service.repo.translations.create(translation_data)

            result = {
                "success": True,
                "translation": translation,
                "message": "Translation created successfully"
            }

            return result

        except Exception as e:
            self.error_collector.add_error(e, {"translation_data": translation_data})
            self.logger.error(f"Error creating translation: {e}")
            raise

    async def delete_translation(self, translation_id: str) -> bool:
        """Delete a translation."""
        try:
            success = self.repository_service.repo.translations.delete(translation_id)
            return success
        except Exception as e:
            self.error_collector.add_error(e, {"translation_id": translation_id})
            return False

    async def get_workflow_summary(self, translation_id: str) -> Dict[str, Any]:
        """Get workflow execution summary for a translation."""
        try:
            # This would integrate with the workflow orchestrator
            # For now, return placeholder data
            translation = self.repository_service.repo.translations.get_by_id(translation_id)
            if not translation:
                raise ValueError(f"Translation not found: {translation_id}")

            result = {
                "translation_id": translation_id,
                "has_workflow": translation.has_workflow_steps,
                "summary": "Workflow data not yet implemented"
            }

            return result

        except Exception as e:
            self.error_collector.add_error(e, {"translation_id": translation_id})
            self.logger.error(f"Error getting workflow summary: {e}")
            raise

    async def get_workflow_steps(self, translation_id: str) -> List[Dict[str, Any]]:
        """Get detailed workflow steps for a translation."""
        try:
            # Get workflow steps from repository service
            workflow_steps = self.repository_service.repo.workflow_steps.get_by_translation(translation_id)

            # Convert to dictionary format for template consumption
            steps_data = []
            for step in workflow_steps:
                step_data = {
                    "id": step.id,
                    "translation_id": step.translation_id,
                    "ai_log_id": step.ai_log_id,
                    "workflow_id": step.workflow_id,
                    "step_type": step.step_type,
                    "step_order": step.step_order,
                    "content": step.content,
                    "notes": step.notes,
                    "model_info": step.model_info,
                    "tokens_used": step.tokens_used,
                    "prompt_tokens": step.prompt_tokens,
                    "completion_tokens": step.completion_tokens,
                    "duration_seconds": step.duration_seconds,
                    "cost": step.cost,
                    "additional_metrics": step.additional_metrics,
                    "translated_title": step.translated_title,
                    "translated_poet_name": step.translated_poet_name,
                    "timestamp": step.timestamp.isoformat() if step.timestamp else None,
                    "created_at": step.created_at.isoformat() if step.created_at else None,
                }
                steps_data.append(step_data)

            return steps_data

        except Exception as e:
            self.error_collector.add_error(e, {"translation_id": translation_id})
            self.logger.error(f"Error getting workflow steps: {e}")
            return []


from fastapi import BackgroundTasks


class WorkflowServiceV2(IWorkflowServiceV2):
    """Enhanced workflow service with dependency injection."""

    def __init__(
        self,
        repository_service: RepositoryWebService,
        storage_handler: "StorageHandler",
        task_service: Optional[ITaskManagementServiceV2] = None,
        logger: Optional[logging.Logger] = None,
        config_path: Optional[str] = None,
    ):
        self.repository_service = repository_service
        self.storage_handler = storage_handler
        self.task_service = task_service
        self.logger = logger or logging.getLogger(__name__)
        self.error_collector = ErrorCollector()
        self.config_path = config_path
        self._config = None
        self._workflow_config = None
        self._providers_config = None

    async def _load_configuration(self):
        from vpsweb.utils.config_loader import load_config
        if self._config is None:
            try:
                self.logger.info("Loading VPSWeb configuration...")
                self._config = load_config(self.config_path)
                self._workflow_config = self._config.main.workflow
                self._providers_config = self._config.providers
            except Exception as e:
                self.logger.error(f"Failed to load VPSWeb configuration: {e}")
                raise

    async def start_translation_workflow(
        self,
        poem_id: str,
        target_lang: str,
        workflow_mode: str,
        background_tasks: BackgroundTasks,
        user_id: Optional[str] = None
    ) -> str:
        """Start a new translation workflow as a background task."""
        try:
            self.logger.info(f"🚀 [WORKFLOW] Starting translation workflow for poem {poem_id}")

            # Validate poem exists
            poem = self.repository_service.repo.poems.get_by_id(poem_id)
            if not poem:
                raise ValueError(f"Poem not found: {poem_id}")
            source_lang = poem.source_language
            self.logger.info(f"🌍 [WORKFLOW] Source lang: {source_lang}, Target lang: {target_lang}")

            # Create a task
            task_id = await self.task_service.create_task(
                "translation_workflow",
                {
                    "poem_id": poem_id,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "workflow_mode": workflow_mode,
                    "user_id": user_id
                },
                user_id
            )

            self.logger.info(f"📋 [WORKFLOW] Created task {task_id}, scheduling background task...")

            # Add the workflow execution to background tasks
            background_tasks.add_task(
                self._execute_workflow,
                task_id=task_id,
                poem_id=poem_id,
                target_lang=target_lang,
                workflow_mode=workflow_mode,
                source_lang=source_lang,
            )

            self.logger.info(f"✅ [WORKFLOW] Background task scheduled for task {task_id}")

            return task_id

        except Exception as e:
            self.error_collector.add_error(e, {
                "poem_id": poem_id,
                "workflow_mode": workflow_mode
            })
            self.logger.error(f"Error starting workflow: {e}")
            raise

    async def _execute_workflow(
        self,
        task_id: str,
        poem_id: str,
        target_lang: str,
        workflow_mode: str,
        source_lang: str,
    ):
        """Execute real workflow using the workflow orchestrator."""
        import asyncio
        from datetime import datetime
        from vpsweb.core.interfaces import WorkflowConfig

        self.logger.info(
            f"🎬 [WORKFLOW] _execute_workflow STARTED for task_id={task_id}"
        )
        self.logger.info(
            f"📝 [WORKFLOW] poem_id={poem_id}, target_lang={target_lang}"
        )
        self.logger.info(f"⚙️ [WORKFLOW] workflow_mode={workflow_mode}")

        task = await self.task_service.get_task(task_id)
        if not task:
            self.logger.error(f"Task {task_id} not found in _execute_workflow")
            return

        try:
            # Add initial delay to give SSE connection time to establish
            self.logger.info(f"⏳ [WORKFLOW] Waiting 1 second for SSE connection to establish...")
            await asyncio.sleep(1)

            await self.task_service.update_task_status(task_id, "running")

            # Initialize step states
            step_states = {
                "Initial Translation": "waiting",
                "Editor Review": "waiting",
                "Translator Revision": "waiting"
            }

            async def progress_callback(step_name: str, details: dict):
                progress_map = {
                    "Initial Translation": 33,
                    "Editor Review": 67,
                    "Translator Revision": 100,
                }
                progress = progress_map.get(step_name, 0)
                if details.get("status") == "running":
                    if step_name == "Initial Translation":
                        progress = 0
                    elif step_name == "Editor Review":
                        progress = 33
                    elif step_name == "Translator Revision":
                        progress = 67

                # Update step states
                if details.get("status") == "running":
                    step_states[step_name] = "running"
                elif details.get("status") == "completed":
                    step_states[step_name] = "completed"

                # Create enhanced step details for frontend compatibility
                enhanced_details = {
                    "step_status": details.get("status", "waiting"),
                    "provider": details.get("provider", "AI"),
                    "mode": workflow_mode,
                    "message": details.get("message", ""),
                    "output": details.get("output", "")
                }

                # Use the task service to update progress properly
                await self.task_service.update_task_progress(
                    task_id,
                    step=step_name,
                    progress=progress,
                    details={
                        **enhanced_details,
                        "step_states": step_states.copy(),
                        "message": details.get("message", ""),
                    },
                )

            # Load configuration
            await self._load_configuration()

            # Get poem data
            poem = self.repository_service.repo.poems.get_by_id(poem_id)
            if not poem:
                raise ValueError(f"Poem with ID {poem_id} not found")

            # Prepare workflow configuration with steps
            from vpsweb.models.config import WorkflowMode
            from vpsweb.core.interfaces import WorkflowStep

            # Convert string workflow_mode to enum
            if isinstance(workflow_mode, str):
                workflow_mode_enum = WorkflowMode(workflow_mode.lower())
            else:
                workflow_mode_enum = workflow_mode

            # Get step configurations from loaded config
            step_configs = self._workflow_config.get_workflow_steps(workflow_mode_enum)

            # Convert StepConfig to WorkflowStep objects
            workflow_steps = []
            for step_name, step_config in step_configs.items():
                workflow_step = WorkflowStep(
                    name=step_name,
                    provider=step_config.provider,
                    model=step_config.model,
                    prompt_template=step_config.prompt_template,
                    temperature=step_config.temperature,
                    max_tokens=step_config.max_tokens,
                    timeout=step_config.timeout,
                    retry_attempts=step_config.retry_attempts,
                    required_fields=step_config.required_fields
                )
                workflow_steps.append(workflow_step)

            workflow_config = WorkflowConfig(
                name=f"Translation-{workflow_mode}",
                description=f"Translation workflow using {workflow_mode} mode",
                steps=workflow_steps,
                metadata={
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "workflow_mode": workflow_mode,
                    "model_config": self._providers_config,
                    "workflow_config": self._workflow_config
                }
            )

            # Prepare input data for workflow
            from vpsweb.models.translation import TranslationInput, Language, LANGUAGE_CODE_MAP
            input_data = TranslationInput(
                original_poem=poem.original_text,
                source_lang=LANGUAGE_CODE_MAP.get(source_lang, source_lang),
                target_lang=LANGUAGE_CODE_MAP.get(target_lang, target_lang),
                metadata={
                    "title": poem.poem_title,
                    "author": poem.poet_name,
                    "poem_id": poem_id,
                }
            )

            workflow = TranslationWorkflow(
                config=self._workflow_config,
                providers_config=self._providers_config,
                workflow_mode=workflow_mode_enum,
                task_service=self.task_service,
                task_id=task_id,
            )
            await self.task_service.update_task(task_id, {"workflow": workflow})
            workflow.progress_callback = progress_callback

            # Execute real workflow using orchestrator
            self.logger.info(f"🚀 [WORKFLOW] Starting real workflow execution for task {task_id}")
            result = await workflow.execute(
                input_data=input_data,
                show_progress=True
            )

            self.logger.info(f"✅ [WORKFLOW] Real workflow completed for task {task_id}")

            # Save results to database and JSON
            self.logger.info(f"💾 [WORKFLOW] Saving results to database and JSON for task {task_id}")
            await self._persist_workflow_result(poem_id, result, workflow_mode, input_data)

            # Get workflow results from the result object
            final_result = result.revised_translation or result.initial_translation

            translated_text = ""
            if hasattr(final_result, 'revised_translation'):
                translated_text = final_result.revised_translation
            elif hasattr(final_result, 'initial_translation'):
                translated_text = final_result.initial_translation

            # Update final task state for completion
            final_task_data = {
                "task_id": task_id,
                "status": "completed",
                "progress": 100,
                "current_step": "Translator Revision",
                "step_details": {
                    "step_status": "completed",
                    "provider": result.initial_translation.model_info.get("model", "AI"),
                    "mode": workflow_mode,
                    "message": "All steps completed successfully",
                    "output": translated_text
                },
                "step_states": {
                    "Initial Translation": "completed",
                    "Editor Review": "completed",
                    "Translator Revision": "completed"
                },
                "message": "Translation workflow completed successfully",
                "error": None,
                "result": result.model_dump(),
                "created_at": datetime.now().isoformat(),
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            # Update the task with completion data
            if task_id in self.task_service.tasks:
                self.task_service.tasks[task_id].update(final_task_data)

            await self.task_service.update_task_status(task_id, "completed", result=result.__dict__)
            self.logger.info(f"Real workflow completed successfully for task {task_id}")

        except Exception as e:
            self.logger.error(f"Real workflow execution failed for task {task_id}: {e}", exc_info=True)
            await self.task_service.update_task_status(
                task_id, "failed", error=str(e)
            )

    async def _persist_workflow_result(self, poem_id: str, result: Any, workflow_mode: str, input_data: Dict[str, Any]):
        # Save to DB
        await self._save_translation_to_db(result, poem_id, workflow_mode, input_data)
        # Save to JSON
        await self._save_translation_to_json(result, poem_id, workflow_mode, input_data)

    async def _save_translation_to_db(self, result, poem_id, workflow_mode, input_data):
        from vpsweb.repository.schemas import AILogCreate, TranslationWorkflowStepCreate, TranslationCreate, TranslatorType, WorkflowStepType
        import json

        # Convert language names to proper codes for database storage
        language_mapper = LanguageMapper()

        # Get proper language codes
        source_lang_code = language_mapper.get_language_code(input_data.source_lang) or input_data.source_lang
        target_lang_code = language_mapper.get_language_code(input_data.target_lang) or input_data.target_lang

        # Normalize the codes
        source_lang_code = language_mapper.normalize_code(source_lang_code)
        target_lang_code = language_mapper.normalize_code(target_lang_code)

        # Create Translation first
        # Get results from the workflow result object
        final_result = result.revised_translation or result.initial_translation

        # Extract translation text
        translated_text = ""
        if hasattr(final_result, 'revised_translation'):
            translated_text = final_result.revised_translation
        elif hasattr(final_result, 'initial_translation'):
            translated_text = final_result.initial_translation

        # Debug: Log the extracted text
        self.logger.info(f"🔍 [DEBUG] Extracted translated_text: '{translated_text}' (length: {len(translated_text)})")

        # Skip database creation if no translation text was generated
        if not translated_text or len(translated_text.strip()) < 10:
            self.logger.warning(f"⚠️ [WARNING] No valid translation text generated for task {poem_id}. Skipping database persistence.")
            return

        translated_poem_title = ""
        if hasattr(final_result, 'refined_translated_poem_title'):
            translated_poem_title = final_result.refined_translated_poem_title
        elif hasattr(final_result, 'translated_poem_title'):
            translated_poem_title = final_result.translated_poem_title

        translated_poet_name = ""
        if hasattr(final_result, 'refined_translated_poet_name'):
            translated_poet_name = final_result.refined_translated_poet_name
        elif hasattr(final_result, 'translated_poet_name'):
            translated_poet_name = final_result.translated_poet_name

        translation_create = TranslationCreate(
            poem_id=poem_id,
            source_language=source_lang_code,
            target_language=target_lang_code,
            translated_text=translated_text,
            translated_poem_title=translated_poem_title,
            translated_poet_name=translated_poet_name,
            translator_type=TranslatorType.AI,
            translator_info=result.initial_translation.model_info.get("model", "unknown"),
            quality_rating=None,
            metadata={
                "status": "completed",
                "steps_executed": ["initial_translation", "editor_review", "translator_revision"],
                "total_tokens_used": result.total_tokens,
                "execution_time": result.duration_seconds,
                "results": {
                    "initial_translation": result.initial_translation.model_dump(),
                    "editor_review": result.editor_review.model_dump(),
                    "revised_translation": result.revised_translation.model_dump(),
                },
                "errors": [],
                "metadata": result.input.metadata
            },
        )
        translation = self.repository_service.repo.translations.create(translation_create)

        # Create AI Log with the translation_id
        ai_log_create = AILogCreate(
            translation_id=translation.id,
            model_name=result.initial_translation.model_info.get("model", "unknown"),
            workflow_mode=workflow_mode,
            token_usage_json=json.dumps({"total_tokens": result.total_tokens, "workflow_mode": workflow_mode}),
            cost_info_json=json.dumps({"total_cost": result.total_cost, "workflow_mode": workflow_mode}),
            runtime_seconds=result.duration_seconds,
            notes=f"Translation workflow completed using {workflow_mode} mode",
        )
        ai_log = self.repository_service.repo.ai_logs.create(ai_log_create)

        # Create Workflow Steps
        steps_data = [
            (WorkflowStepType.INITIAL_TRANSLATION, 1, result.initial_translation, "Initial Translation"),
            (WorkflowStepType.EDITOR_REVIEW, 2, result.editor_review, "Editor Review"),
            (WorkflowStepType.REVISED_TRANSLATION, 3, result.revised_translation, "Translator Revision"),
        ]

        for step_type, step_order, step_data, step_name in steps_data:
            # Extract translated metadata based on step type
            step_translated_title = None
            step_translated_poet_name = None

            # Handle different data structures for different step types
            if step_type == "editor_review":
                # Editor review step might store duration/cost differently
                self.logger.info(f"🔍 [DEBUG] Editor review step_data.type: {type(step_data)}")
                self.logger.info(f"🔍 [DEBUG] Editor review has 'duration' attr: {hasattr(step_data, 'duration')}")
                self.logger.info(f"🔍 [DEBUG] Editor review is dict: {isinstance(step_data, dict)}")

                if hasattr(step_data, 'duration'):
                    step_duration = getattr(step_data, 'duration', None)
                    self.logger.info(f"🔍 [DEBUG] Got duration from attr: {step_duration}")
                else:
                    step_duration = step_data.get('duration') if isinstance(step_data, dict) else None
                    self.logger.info(f"🔍 [DEBUG] Got duration from dict: {step_duration}")

                if hasattr(step_data, 'cost'):
                    step_cost = getattr(step_data, 'cost', None)
                    self.logger.info(f"🔍 [DEBUG] Got cost from attr: {step_cost}")
                else:
                    step_cost = step_data.get('cost') if isinstance(step_data, dict) else None
                    self.logger.info(f"🔍 [DEBUG] Got cost from dict: {step_cost}")
            else:
                # Other steps use object attributes
                step_duration = getattr(step_data, 'duration', None)
                step_cost = getattr(step_data, 'cost', None)

            if step_type == "initial_translation":
                step_translated_title = getattr(step_data, 'translated_poem_title', None)
                step_translated_poet_name = getattr(step_data, 'translated_poet_name', None)
            elif step_type == "revised_translation":
                step_translated_title = getattr(step_data, 'refined_translated_poem_title', None)
                step_translated_poet_name = getattr(step_data, 'refined_translated_poet_name', None)
            # For editor_review, translated metadata remain None but duration and cost should be preserved

            workflow_step_create = TranslationWorkflowStepCreate(
                translation_id=translation.id,
                ai_log_id=ai_log.id,
                workflow_id=result.workflow_id,
                step_type=step_type,
                step_order=step_order,
                content=getattr(step_data, 'initial_translation', '') or getattr(step_data, 'editor_suggestions', '') or getattr(step_data, 'revised_translation', ''),
                notes=getattr(step_data, 'initial_translation_notes', '') or getattr(step_data, 'revised_translation_notes', ''),
                model_info=json.dumps(step_data.model_info),
                tokens_used=step_data.tokens_used,
                prompt_tokens=step_data.prompt_tokens,
                completion_tokens=step_data.completion_tokens,
                duration_seconds=step_duration,
                cost=step_cost,
                translated_title=step_translated_title,
                translated_poet_name=step_translated_poet_name,
                timestamp=datetime.now(timezone(timedelta(hours=8))),  # UTC+8 timezone
            )
            self.repository_service.repo.workflow_steps.create(workflow_step_create)

    async def _save_translation_to_json(self, result, poem_id, workflow_mode, input_data):
        poem = self.repository_service.repo.poems.get_by_id(poem_id)
        if not poem:
            return

        # The result object is already a TranslationOutput object, which has a to_dict() method.
        # We can use it directly with the storage handler.

        # Log debug info about JSON save
        self.logger.info(f"💾 [JSON] Saving translation to JSON for task {poem_id}")

        self.storage_handler.save_translation_with_poet_dir(
            output=result,
            poet_name=poem.poet_name,
            workflow_mode=workflow_mode,
            include_mode_tag=True,
        )

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a workflow task."""
        try:
            if self.task_service:
                task = await self.task_service.get_task(task_id)
                if task:
                    return task

            return {"task_id": task_id, "status": "unknown"}

        except Exception as e:
            self.error_collector.add_error(e, {"task_id": task_id})
            self.logger.error(f"Error getting task status: {e}")
            return {"task_id": task_id, "status": "error", "error": str(e)}

    async def cancel_task(self, task_id: str, user_id: Optional[str] = None) -> bool:
        """Cancel a workflow task."""
        try:
            if self.task_service:
                await self.task_service.update_task_status(
                    task_id,
                    "cancelled",
                    {"cancelled_by": user_id or "system"}
                )
                return True
            return False

        except Exception as e:
            self.error_collector.add_error(e, {"task_id": task_id})
            self.logger.error(f"Error cancelling task: {e}")
            return False

    async def list_tasks(
        self,
        limit: int = 50,
        user_id: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """List workflow tasks with filtering."""
        try:
            if self.task_service:
                return await self.task_service.get_filtered_tasks(limit, user_id, status_filter)

            # Fallback - return empty list
            return {"tasks": [], "total_count": 0}

        except Exception as e:
            self.error_collector.add_error(e)
            self.logger.error(f"Error listing tasks: {e}")
            return {"tasks": [], "total_count": 0}

    async def get_workflow_modes(self) -> Dict[str, Any]:
        """Get available workflow modes."""
        return {
            "modes": [
                {
                    "name": "reasoning",
                    "description": "Step-by-step reasoning with detailed analysis",
                    "recommended_for": "complex or literary poems"
                },
                {
                    "name": "non_reasoning",
                    "description": "Direct translation without detailed reasoning",
                    "recommended_for": "simple or technical content"
                },
                {
                    "name": "hybrid",
                    "description": "Balanced approach with selective reasoning",
                    "recommended_for": "most content types"
                }
            ]
        }

    async def validate_workflow_input(
        self,
        poem_id: str,
        source_lang: str,
        target_lang: str,
        workflow_mode: str
    ) -> Dict[str, Any]:
        """Validate workflow input parameters."""
        try:
            # Check poem exists
            poem = self.repository_service.repo.poems.get_by_id(poem_id)
            if not poem:
                raise ValueError(f"Poem not found: {poem_id}")

            # Validate language difference
            if source_lang == target_lang:
                raise ValueError("Source and target languages must be different")

            # Validate workflow mode
            available_modes = ["reasoning", "non_reasoning", "hybrid"]
            if workflow_mode not in available_modes:
                raise ValueError(f"Invalid workflow mode: {workflow_mode}")

            return {
                "valid": True,
                "poem": {"id": poem.id, "title": poem.poem_title},
                "validation": {
                    "poem_exists": True,
                    "different_languages": True,
                    "valid_mode": True
                }
            }

        except Exception as e:
            self.error_collector.add_error(e, {
                "poem_id": poem_id,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "workflow_mode": workflow_mode
            })
            return {
                "valid": False,
                "error": str(e)
            }


class PoetServiceV2(IPoetServiceV2):
    """Enhanced poet service with dependency injection."""

    def __init__(
        self,
        repository_service: RepositoryWebService,
        performance_service: Optional[IPerformanceServiceV2] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.repository_service = repository_service
        self.performance_service = performance_service
        self.logger = logger or logging.getLogger(__name__)
        self.error_collector = ErrorCollector()

    async def get_poets_list(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        sort_by: str = "name",
        sort_order: str = "asc",
        min_poems: Optional[int] = None,
        min_translations: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get paginated list of poets with statistics."""
        try:
            # Get poets from repository
            poets = self.repository_service.repo.poems.get_distinct_poets(
                skip=skip,
                limit=limit,
                search=search,
                sort_by=sort_by,
                sort_order=sort_order
            )

            # Enrich with statistics
            enriched_poets = []
            for poet in poets:
                poet_stats = await self.get_poet_statistics(poet["name"])

                # Apply filters
                if min_poems and poet_stats["poem_count"] < min_poems:
                    continue
                if min_translations and poet_stats["translation_count"] < min_translations:
                    continue

                enriched_poet = {
                    **poet,
                    "poem_count": poet_stats["poem_count"],
                    "translation_count": poet_stats["translation_count"],
                    "last_activity": poet_stats["last_activity"]
                }
                enriched_poets.append(enriched_poet)

            result = {
                "poets": enriched_poets,
                "total_count": len(enriched_poets),
                "pagination": {
                    "skip": skip,
                    "limit": limit,
                    "has_next": len(enriched_poets) == limit,
                    "has_prev": skip > 0
                },
                "filters": {
                    "search": search,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "min_poems": min_poems,
                    "min_translations": min_translations
                }
            }

            return result

        except Exception as e:
            self.error_collector.add_error(e, {
                "operation": "get_poets_list",
                "filters": {"search": search, "sort_by": sort_by}
            })
            self.logger.error(f"Error getting poets list: {e}")
            raise

    async def get_poet_detail(
        self,
        poet_name: str,
        skip: int = 0,
        limit: int = 20,
        language: Optional[str] = None,
        has_translations: Optional[bool] = None,
        sort_by: str = "title",
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """Get detailed poet information with poems and statistics."""
        try:
            # Get poet's poems
            poems = self.repository_service.repo.poems.get_by_poet(
                poet_name=poet_name,
                skip=skip,
                limit=limit,
                language=language,
                has_translations=has_translations,
                sort_by=sort_by,
                sort_order=sort_order
            )

            # Get poet statistics
            stats = await self.get_poet_statistics(poet_name)

            result = {
                "poet": {
                    "name": poet_name,
                    "poem_count": stats["poem_count"],
                    "translation_count": stats["translation_count"],
                    "last_activity": stats["last_activity"]
                },
                "poems": poems,
                "statistics": stats,
                "pagination": {
                    "skip": skip,
                    "limit": limit,
                    "has_next": len(poems) == limit,
                    "has_prev": skip > 0
                }
            }

            return result

        except Exception as e:
            self.error_collector.add_error(e, {"poet_name": poet_name})
            self.logger.error(f"Error getting poet detail: {e}")
            raise

    async def get_poet_statistics(self, poet_name: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a specific poet."""
        try:
            # Get poem count
            poem_count = self.repository_service.repo.poems.count_by_poet(poet_name)

            # Get translation count
            translation_count = self.repository_service.repo.translations.count_by_poet(poet_name)

            # Get last activity
            last_poem = self.repository_service.repo.poems.get_latest_by_poet(poet_name)
            last_translation = self.repository_service.repo.translations.get_latest_by_poet(poet_name)

            last_activity = None
            if last_poem and last_translation:
                last_activity = max(last_poem.created_at, last_translation.updated_at)
            elif last_poem:
                last_activity = last_poem.created_at
            elif last_translation:
                last_activity = last_translation.updated_at

            return {
                "poet_name": poet_name,
                "poem_count": poem_count,
                "translation_count": translation_count,
                "last_activity": last_activity,
                "translation_ratio": translation_count / poem_count if poem_count > 0 else 0
            }

        except Exception as e:
            self.error_collector.add_error(e, {"poet_name": poet_name})
            self.logger.error(f"Error getting poet statistics: {e}")
            return {
                "poet_name": poet_name,
                "poem_count": 0,
                "translation_count": 0,
                "last_activity": None,
                "translation_ratio": 0
            }

    async def get_all_poets_statistics(self) -> Dict[str, Any]:
        """Get statistics for all poets."""
        try:
            # Get all poets
            poets = self.repository_service.repo.poems.get_distinct_poets(limit=1000)

            # Get statistics for each poet
            all_stats = []
            total_poems = 0
            total_translations = 0

            for poet in poets:
                stats = await self.get_poet_statistics(poet["name"])
                all_stats.append(stats)
                total_poems += stats["poem_count"]
                total_translations += stats["translation_count"]

            # Sort by translation count
            all_stats.sort(key=lambda x: x["translation_count"], reverse=True)

            return {
                "total_poets": len(all_stats),
                "total_poems": total_poems,
                "total_translations": total_translations,
                "overall_translation_ratio": total_translations / total_poems if total_poems > 0 else 0,
                "top_poets": all_stats[:10],  # Top 10 by translations
                "all_statistics": all_stats
            }

        except Exception as e:
            self.error_collector.add_error(e)
            self.logger.error(f"Error getting all poets statistics: {e}")
            return {
                "total_poets": 0,
                "total_poems": 0,
                "total_translations": 0,
                "overall_translation_ratio": 0,
                "top_poets": [],
                "all_statistics": []
            }


class StatisticsServiceV2(IStatisticsServiceV2):
    """Enhanced statistics service with dependency injection."""

    def __init__(
        self,
        repository_service: RepositoryWebService,
        performance_service: Optional[IPerformanceServiceV2] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.repository_service = repository_service
        self.performance_service = performance_service
        self.logger = logger or logging.getLogger(__name__)
        self.error_collector = ErrorCollector()

    async def get_repository_statistics(self) -> Dict[str, Any]:
        """Get comprehensive repository statistics."""
        try:
            # Basic counts
            total_poems = self.repository_service.repo.poems.count()
            total_translations = self.repository_service.repo.translations.count()

            # Recent activity (last 30 days)
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            recent_poems = self.repository_service.repo.poems.count_since(thirty_days_ago)
            recent_translations = self.repository_service.repo.translations.count_since(thirty_days_ago)

            # Language distribution
            languages = self.repository_service.repo.poems.get_language_distribution()

            # Poet statistics
            total_poets = len(self.repository_service.repo.poems.get_distinct_poets(limit=10000))

            result = {
                "overview": {
                    "total_poems": total_poems,
                    "total_translations": total_translations,
                    "total_poets": total_poets,
                    "total_translation_ratio": total_translations / total_poems if total_poems > 0 else 0
                },
                "recent_activity": {
                    "recent_poems": recent_poems,
                    "recent_translations": recent_translations,
                    "activity_period_days": 30
                },
                "language_distribution": languages,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

            return result

        except Exception as e:
            self.error_collector.add_error(e)
            self.logger.error(f"Error getting repository statistics: {e}")
            return {"error": str(e)}

    async def get_translation_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get translation trends over time."""
        try:
            # This would implement trend analysis
            # For now, return basic data
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)

            translations_in_period = self.repository_service.repo.translations.count_in_period(
                start_date, end_date
            )

            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "translations_created": translations_in_period,
                "daily_average": translations_in_period / days if days > 0 else 0
            }

        except Exception as e:
            self.error_collector.add_error(e, {"days": days})
            self.logger.error(f"Error getting translation trends: {e}")
            return {"error": str(e)}

    async def get_poet_activity_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get poet activity statistics."""
        try:
            # Get active poets in period
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)

            active_poets = self.repository_service.repo.poems.get_active_poets_in_period(
                start_date, end_date
            )

            return {
                "period": {"days": days},
                "active_poets_count": len(active_poets),
                "active_poets": active_poets[:20]  # Top 20
            }

        except Exception as e:
            self.error_collector.add_error(e, {"days": days})
            self.logger.error(f"Error getting poet activity stats: {e}")
            return {"error": str(e)}

    async def get_workflow_performance_stats(self) -> Dict[str, Any]:
        """Get workflow performance metrics."""
        try:
            # This would integrate with workflow orchestrator metrics
            # For now, return placeholder data
            return {
                "workflow_performance": {
                    "total_workflows": 0,
                    "successful_workflows": 0,
                    "failed_workflows": 0,
                    "average_execution_time": 0,
                    "success_rate": 0
                },
                "note": "Workflow performance tracking not yet implemented"
            }

        except Exception as e:
            self.error_collector.add_error(e)
            self.logger.error(f"Error getting workflow performance stats: {e}")
            return {"error": str(e)}


class PerformanceServiceV2(IPerformanceServiceV2):
    """Performance monitoring service implementation."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.performance_monitor = PerformanceMonitor()
        self.slow_request_threshold = 1000.0  # 1 second

    async def log_request_performance(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log request performance metrics."""
        try:
            await self.performance_monitor.record_request(
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration,
                additional_data=additional_data or {}
            )

            # Log slow requests
            if self.should_log_slow_request(duration):
                self.logger.warning(
                    f"Slow request: {method} {path} took {duration:.2f}ms"
                )

        except Exception as e:
            self.logger.error(f"Error logging performance: {e}")

    async def get_performance_summary(
        self,
        minutes: int = 60
    ) -> Dict[str, Any]:
        """Get performance summary for specified time period."""
        try:
            metrics = await self.performance_monitor.get_performance_metrics(minutes)
            return metrics

        except Exception as e:
            self.logger.error(f"Error getting performance summary: {e}")
            return {"error": str(e)}

    def should_log_slow_request(self, duration: float) -> bool:
        """Determine if request is slow enough to log."""
        return duration > self.slow_request_threshold


class TaskManagementServiceV2(ITaskManagementServiceV2):
    """In-memory task management service implementation."""

    def __init__(self, tasks_store: Optional[Dict[str, Any]] = None, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.tasks: Dict[str, Any] = tasks_store if tasks_store is not None else {}
        self.max_age_hours = 24

    async def create_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """Create a new background task."""
        task_id = generate_unique_id()

        task = {
            "id": task_id,
            "type": task_type,
            "data": task_data,
            "user_id": user_id,
            "status": "pending",
            "progress": 0,
            "current_step": None,
            "details": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "result": None,
            "error": None
        }

        self.tasks[task_id] = task
        self.logger.info(f"Created task {task_id} of type {task_type}")

        return task_id

    async def update_task(self, task_id: str, updates: Dict[str, Any]):
        """Update a task with new data."""
        if task_id in self.tasks:
            self.tasks[task_id].update(updates)

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by its ID."""
        return self.tasks.get(task_id)

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """Update task status."""
        if task_id in self.tasks:
            self.tasks[task_id].update({
                "status": status,
                "updated_at": datetime.now(timezone.utc),
                "result": result,
                "error": error
            })
            self.logger.info(f"Updated task {task_id} status to {status}")

    async def update_task_progress(
        self,
        task_id: str,
        step: str,
        progress: int,
        details: Dict[str, Any],
    ) -> None:
        """Update task progress while preserving step states and other important fields."""
        if task_id in self.tasks:
            # Preserve existing important fields
            existing_task = self.tasks[task_id]
            preserved_fields = {
                "step_states": existing_task.get("step_states", {}),
                "message": existing_task.get("message", ""),
                "error": existing_task.get("error"),
                "result": existing_task.get("result"),
                "created_at": existing_task.get("created_at"),
                "started_at": existing_task.get("started_at"),
                "completed_at": existing_task.get("completed_at"),
                "task_id": existing_task.get("task_id"),
                "type": existing_task.get("type"),
                "data": existing_task.get("data"),
                "user_id": existing_task.get("user_id"),
            }

            # Update with new progress data
            self.tasks[task_id].update({
                **preserved_fields,  # Preserve existing important fields
                "current_step": step,
                "progress": progress,
                "details": details,
                "step_states": details.get("step_states", preserved_fields["step_states"]),  # Update step_states from details
                "updated_at": datetime.now(timezone.utc),
            })

            # Debug logging for step_states
            updated_step_states = self.tasks[task_id].get("step_states", {})
            self.logger.info(f"Updated task {task_id} progress to {progress}% at step {step}, step_states: {updated_step_states}")

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task information."""
        return self.tasks.get(task_id)

    async def get_filtered_tasks(
        self,
        limit: int = 50,
        user_id: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get tasks with filtering."""
        tasks = list(self.tasks.values())

        # Apply filters
        if user_id:
            tasks = [t for t in tasks if t["user_id"] == user_id]

        if status_filter:
            tasks = [t for t in tasks if t["status"] == status_filter]

        # Sort by creation time (newest first)
        tasks.sort(key=lambda x: x["created_at"], reverse=True)

        # Apply limit
        tasks = tasks[:limit]

        return {
            "tasks": tasks,
            "total_count": len(tasks),
            "filters": {
                "user_id": user_id,
                "status_filter": status_filter,
                "limit": limit
            }
        }

    async def cleanup_expired_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up expired tasks."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        expired_tasks = [
            task_id for task_id, task in self.tasks.items()
            if task["created_at"] < cutoff_time
        ]

        for task_id in expired_tasks:
            del self.tasks[task_id]

        if expired_tasks:
            self.logger.info(f"Cleaned up {len(expired_tasks)} expired tasks")

        return len(expired_tasks)


class TemplateServiceV2(ITemplateServiceV2):
    """Template service implementation using Jinja2."""

    def __init__(self, template_dir: str = "src/vpsweb/webui/web/templates", logger: Optional[logging.Logger] = None):
        self.template_dir = template_dir
        self.logger = logger or logging.getLogger(__name__)
        self._templates = {}

        # Initialize Jinja2 environment
        from fastapi.templating import Jinja2Templates
        self.templates = Jinja2Templates(directory=template_dir)

    async def render_template(
        self,
        template_name: str,
        context: Dict[str, Any],
        request: Optional[Any] = None
    ) -> str:
        """Render a template with context."""
        try:
            from jinja2 import Environment, FileSystemLoader
            env = Environment(loader=FileSystemLoader(self.template_dir))

            # Add custom filters
            def strip_leading_spaces(text):
                """Strip leading spaces from each line in text."""
                if text is None:
                    return ""
                return '\n'.join(line.lstrip() for line in text.split('\n'))

            env.filters['strip_leading_spaces'] = strip_leading_spaces
            template = env.get_template(template_name)

            # Prepare template context with request-safe data
            template_context = context.copy()
            if request:
                # Extract request information safely
                template_context['current_path'] = str(request.url.path)
                template_context['query_params'] = dict(request.query_params)
            else:
                template_context['current_path'] = '/'
                template_context['query_params'] = {}

            return template.render(**template_context)

        except Exception as e:
            self.logger.error(f"Error rendering template {template_name}: {e}")
            # Fallback to simple debug output
            return f"<h1>Template Error: {template_name}</h1><p>Error: {str(e)}</p><p>Context keys: {list(context.keys())}</p>"

    async def get_template_list(self, category: Optional[str] = None) -> List[str]:
        """Get list of available templates."""
        # Return default templates
        templates = [
            "base.html",
            "dashboard.html",
            "poems/list.html",
            "poems/detail.html",
            "translations/list.html",
            "translations/detail.html"
        ]

        if category:
            templates = [t for t in templates if category in t]

        return templates

    async def validate_template_data(
        self,
        template_name: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate template data before rendering."""
        # Basic validation
        result = {
            "valid": True,
            "template_name": template_name,
            "provided_data_keys": list(data.keys()),
            "validation_errors": []
        }

        # Template-specific validation would go here
        if "poems" in template_name and not data.get("poems"):
            result["validation_errors"].append("poems data required for poems templates")
            result["valid"] = False

        return result


class ExceptionHandlerServiceV2(IExceptionHandlerServiceV2):
    """Error handling service implementation."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_collector = ErrorCollector()

    async def handle_http_error(
        self,
        error: Exception,
        request: Any,
        is_web_request: bool
    ) -> Any:
        """Handle HTTP errors with appropriate formatting."""
        error_id = self.generate_error_id()

        self.error_collector.add_error(error, {
            "error_id": error_id,
            "request_path": getattr(request, 'url', {}).path if hasattr(request, 'url') else str(request),
            "is_web_request": is_web_request
        })

        self.logger.error(f"HTTP Error [{error_id}]: {error}")

        # Return appropriate error response
        if is_web_request:
            from fastapi import HTTPException
            from fastapi.responses import JSONResponse

            if isinstance(error, HTTPException):
                return JSONResponse(
                    status_code=error.status_code,
                    content={
                        "error": error.detail,
                        "error_id": error_id,
                        "type": "HTTPException"
                    }
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Internal server error",
                        "error_id": error_id,
                        "type": "InternalServerError"
                    }
                )

        return {"error_id": error_id, "error": str(error)}

    async def handle_general_error(
        self,
        error: Exception,
        request: Any,
        error_id: str,
        is_web_request: bool
    ) -> Any:
        """Handle general exceptions with logging and formatting."""
        self.error_collector.add_error(error, {
            "error_id": error_id,
            "request_path": getattr(request, 'url', {}).path if hasattr(request, 'url') else str(request),
            "is_web_request": is_web_request
        })

        self.logger.error(f"General Error [{error_id}]: {error}", exc_info=True)

        if is_web_request:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={
                    "error": "An unexpected error occurred",
                    "error_id": error_id,
                    "type": "GeneralError"
                }
            )

        return {"error_id": error_id, "error": str(error)}

    def generate_error_id(self) -> str:
        """Generate unique error ID for tracking."""
        return generate_unique_id(prefix="err")


class SSEServiceV2(ISSEServiceV2):
    """Server-Sent Events service implementation."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.active_connections: Dict[str, Any] = {}

    async def create_sse_stream(
        self,
        task_id: str,
        request: Any
    ) -> Any:
        """Create SSE stream for real-time updates."""
        try:
            # This would create a proper SSE stream
            # For now, return a mock response
            stream_id = generate_unique_id(prefix="sse")

            self.active_connections[stream_id] = {
                "task_id": task_id,
                "request": request,
                "created_at": datetime.now(timezone.utc),
                "last_heartbeat": time.time()
            }

            self.logger.info(f"Created SSE stream {stream_id} for task {task_id}")

            # Return mock stream object
            return {"stream_id": stream_id, "task_id": task_id}

        except Exception as e:
            self.logger.error(f"Error creating SSE stream: {e}")
            raise

    async def send_sse_event(
        self,
        task_id: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Send SSE event to connected clients."""
        try:
            # Find active connections for this task
            connections = [
                (stream_id, conn) for stream_id, conn in self.active_connections.items()
                if conn["task_id"] == task_id
            ]

            for stream_id, conn in connections:
                # Send event to connection
                # This would use proper SSE protocol
                self.logger.debug(
                    f"Sending SSE event {event_type} to stream {stream_id} for task {task_id}"
                )

        except Exception as e:
            self.logger.error(f"Error sending SSE event: {e}")

    def should_send_heartbeat(self, last_update_time: float) -> bool:
        """Determine if heartbeat event should be sent."""
        # Send heartbeat every 30 seconds
        return (time.time() - last_update_time) > 30


class ConfigServiceV2(IConfigServiceV2):
    """Configuration service implementation."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._settings = {
            "app_name": "VPSWeb",
            "version": "0.3.12",
            "debug": False,
            "max_workflows_per_user": 10,
            "default_language": "en",
            "supported_languages": ["en", "zh-CN", "pl"]
        }

    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Get configuration setting."""
        return self._settings.get(key, default)

    async def get_all_settings(self) -> Dict[str, Any]:
        """Get all configuration settings."""
        return self._settings.copy()

    async def update_setting(self, key: str, value: Any) -> bool:
        """Update configuration setting."""
        try:
            if await self.validate_setting(key, value):
                self._settings[key] = value
                self.logger.info(f"Updated setting {key} = {value}")
                return True
            else:
                self.logger.warning(f"Invalid setting value: {key} = {value}")
                return False

        except Exception as e:
            self.logger.error(f"Error updating setting {key}: {e}")
            return False

    async def validate_setting(self, key: str, value: Any) -> bool:
        """Validate configuration setting value."""
        # Basic validation rules
        if key == "max_workflows_per_user":
            return isinstance(value, int) and value > 0
        elif key == "debug":
            return isinstance(value, bool)
        elif key == "default_language":
            return value in self._settings.get("supported_languages", [])
        else:
            return True  # No validation for other settings