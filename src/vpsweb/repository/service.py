"""
VPSWeb Repository Service Layer v0.3.1

Service layer that provides a clean interface between the webui and repository layers.
Handles database operations, error handling, and business logic.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from .crud import RepositoryService
from .schemas import (
    PoemCreate, PoemUpdate, PoemResponse,
    TranslationCreate, TranslationUpdate, TranslationResponse,
    AILogCreate, AILogResponse,
    HumanNoteCreate, HumanNoteResponse,
    RepositoryStats,
    WorkflowTaskCreate, WorkflowTaskResponse, TaskStatus, WorkflowMode
)
from .models import Poem, Translation, AILog, HumanNote, WorkflowTask


class RepositoryWebService:
    """
    Web service layer for repository operations.
    Provides high-level methods for the web UI to interact with the repository.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = RepositoryService(db)

    # Dashboard and Statistics Methods
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for the main dashboard"""
        stats = self.repo.get_repository_stats()
        recent_poems = self.repo.poems.get_multi(limit=5)
        recent_translations = self.repo.translations.get_multi(limit=5)

        return {
            "stats": stats,
            "recent_poems": [self._poem_to_response(p) for p in recent_poems],
            "recent_translations": [self._translation_to_response(t) for t in recent_translations]
        }

    # Poem Methods
    def create_poem(self, poem_data: PoemCreate) -> PoemResponse:
        """Create a new poem"""
        try:
            poem = self.repo.poems.create(poem_data)
            return self._poem_to_response(poem)
        except Exception as e:
            raise self._handle_error("Failed to create poem", e)

    def get_poem(self, poem_id: str) -> Optional[PoemResponse]:
        """Get a poem by ID"""
        poem = self.repo.poems.get_by_id(poem_id)
        if poem:
            return self._poem_to_response(poem)
        return None

    def get_poems_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        poet: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get paginated poems with optional filtering"""
        offset = (page - 1) * page_size

        if search:
            poems = self.repo.search_poems(search, limit=page_size)
            total = len(poems)  # Note: For large datasets, this should be optimized
        else:
            poems = self.repo.poems.get_multi(
                skip=offset,
                limit=page_size,
                poet_name=poet,
                language=language
            )
            total = self.repo.poems.count()

        return {
            "poems": [self._poem_to_response(p) for p in poems],
            "pagination": {
                "current_page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": (total + page_size - 1) // page_size,
                "has_next": offset + page_size < total,
                "has_previous": page > 1
            }
        }

    def update_poem(self, poem_id: str, poem_data: PoemUpdate) -> Optional[PoemResponse]:
        """Update a poem"""
        try:
            poem = self.repo.poems.update(poem_id, poem_data)
            if poem:
                return self._poem_to_response(poem)
            return None
        except Exception as e:
            raise self._handle_error("Failed to update poem", e)

    def delete_poem(self, poem_id: str) -> bool:
        """Delete a poem and all related data"""
        try:
            return self.repo.poems.delete(poem_id)
        except Exception as e:
            raise self._handle_error("Failed to delete poem", e)

    # Translation Methods
    def create_translation(self, translation_data: TranslationCreate) -> TranslationResponse:
        """Create a new translation"""
        try:
            # Verify poem exists
            poem = self.repo.poems.get_by_id(translation_data.poem_id)
            if not poem:
                raise ValueError(f"Poem with ID {translation_data.poem_id} not found")

            translation = self.repo.translations.create(translation_data)
            return self._translation_to_response(translation)
        except Exception as e:
            raise self._handle_error("Failed to create translation", e)

    def get_translation(self, translation_id: str) -> Optional[TranslationResponse]:
        """Get a translation by ID"""
        translation = self.repo.translations.get_by_id(translation_id)
        if translation:
            return self._translation_to_response(translation)
        return None

    def get_poem_translations(self, poem_id: str) -> List[TranslationResponse]:
        """Get all translations for a poem"""
        translations = self.repo.translations.get_by_poem(poem_id)
        return [self._translation_to_response(t) for t in translations]

    def get_translation_with_details(self, translation_id: str) -> Optional[Dict[str, Any]]:
        """Get translation with all related details (AI logs, human notes)"""
        translation = self.repo.translations.get_by_id(translation_id)
        if not translation:
            return None

        ai_logs = self.repo.ai_logs.get_by_translation(translation_id)
        human_notes = self.repo.human_notes.get_by_translation(translation_id)

        return {
            "translation": self._translation_to_response(translation),
            "ai_logs": [self._ai_log_to_response(log) for log in ai_logs],
            "human_notes": [self._human_note_to_response(note) for note in human_notes]
        }

    def update_translation(self, translation_id: str, translation_data: TranslationUpdate) -> Optional[TranslationResponse]:
        """Update a translation"""
        try:
            translation = self.repo.translations.update(translation_id, translation_data)
            if translation:
                return self._translation_to_response(translation)
            return None
        except Exception as e:
            raise self._handle_error("Failed to update translation", e)

    def delete_translation(self, translation_id: str) -> bool:
        """Delete a translation and all related data"""
        try:
            return self.repo.translations.delete(translation_id)
        except Exception as e:
            raise self._handle_error("Failed to delete translation", e)

    # AI Log Methods
    def create_ai_log(self, ai_log_data: AILogCreate) -> AILogResponse:
        """Create a new AI log entry"""
        try:
            # Verify translation exists
            translation = self.repo.translations.get_by_id(ai_log_data.translation_id)
            if not translation:
                raise ValueError(f"Translation with ID {ai_log_data.translation_id} not found")

            ai_log = self.repo.ai_logs.create(ai_log_data)
            return self._ai_log_to_response(ai_log)
        except Exception as e:
            raise self._handle_error("Failed to create AI log", e)

    def get_ai_logs_by_translation(self, translation_id: str) -> List[AILogResponse]:
        """Get all AI logs for a translation"""
        ai_logs = self.repo.ai_logs.get_by_translation(translation_id)
        return [self._ai_log_to_response(log) for log in ai_logs]

    def get_ai_logs_by_model(self, model_name: str) -> List[AILogResponse]:
        """Get all AI logs for a specific model"""
        ai_logs = self.repo.ai_logs.get_by_model(model_name)
        return [self._ai_log_to_response(log) for log in ai_logs]

    # Human Note Methods
    def create_human_note(self, note_data: HumanNoteCreate) -> HumanNoteResponse:
        """Create a new human note"""
        try:
            # Verify translation exists
            translation = self.repo.translations.get_by_id(note_data.translation_id)
            if not translation:
                raise ValueError(f"Translation with ID {note_data.translation_id} not found")

            note = self.repo.human_notes.create(note_data)
            return self._human_note_to_response(note)
        except Exception as e:
            raise self._handle_error("Failed to create human note", e)

    def get_human_notes_by_translation(self, translation_id: str) -> List[HumanNoteResponse]:
        """Get all human notes for a translation"""
        notes = self.repo.human_notes.get_by_translation(translation_id)
        return [self._human_note_to_response(note) for note in notes]

    def delete_human_note(self, note_id: str) -> bool:
        """Delete a human note"""
        try:
            return self.repo.human_notes.delete(note_id)
        except Exception as e:
            raise self._handle_error("Failed to delete human note", e)

    # Search and Comparison Methods
    def search_poems(self, query: str, limit: int = 20) -> List[PoemResponse]:
        """Search poems by content"""
        poems = self.repo.search_poems(query, limit=limit)
        return [self._poem_to_response(p) for p in poems]

    def get_comparison_view(self, poem_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive comparison view for a poem"""
        return self.repo.get_poem_with_translations(poem_id)

    def get_repository_stats(self) -> RepositoryStats:
        """Get comprehensive repository statistics"""
        stats = self.repo.get_repository_stats()
        return RepositoryStats(**stats)

    # Helper Methods
    def _poem_to_response(self, poem: Poem) -> PoemResponse:
        """Convert poem model to response schema"""
        return PoemResponse(
            id=poem.id,
            poet_name=poem.poet_name,
            poem_title=poem.poem_title,
            source_language=poem.source_language,
            original_text=poem.original_text,
            metadata_json=poem.metadata_json,
            created_at=poem.created_at,
            updated_at=poem.updated_at,
            translation_count=poem.translation_count
        )

    def _translation_to_response(self, translation: Translation) -> TranslationResponse:
        """Convert translation model to response schema"""
        return TranslationResponse(
            id=translation.id,
            poem_id=translation.poem_id,
            translator_type=translation.translator_type,
            translator_info=translation.translator_info,
            target_language=translation.target_language,
            translated_text=translation.translated_text,
            quality_rating=translation.quality_rating,
            raw_path=translation.raw_path,
            created_at=translation.created_at
        )

    def _ai_log_to_response(self, ai_log: AILog) -> AILogResponse:
        """Convert AI log model to response schema"""
        return AILogResponse(
            id=ai_log.id,
            translation_id=ai_log.translation_id,
            model_name=ai_log.model_name,
            workflow_mode=ai_log.workflow_mode,
            token_usage_json=ai_log.token_usage_json,
            cost_info_json=ai_log.cost_info_json,
            runtime_seconds=ai_log.runtime_seconds,
            notes=ai_log.notes,
            created_at=ai_log.created_at
        )

    def _human_note_to_response(self, note: HumanNote) -> HumanNoteResponse:
        """Convert human note model to response schema"""
        return HumanNoteResponse(
            id=note.id,
            translation_id=note.translation_id,
            note_text=note.note_text,
            created_at=note.created_at
        )

    # Workflow Task Methods
    def create_workflow_task(self, task_data: WorkflowTaskCreate) -> WorkflowTaskResponse:
        """Create a new workflow task"""
        try:
            task = self.repo.workflow_tasks.create(task_data)
            return self._workflow_task_to_response(task)
        except Exception as e:
            raise self._handle_error("Failed to create workflow task", e)

    def get_workflow_task(self, task_id: str) -> Optional[WorkflowTaskResponse]:
        """Get a workflow task by ID"""
        task = self.repo.workflow_tasks.get(task_id)
        if task:
            return self._workflow_task_to_response(task)
        return None

    def get_workflow_tasks(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        status: Optional[TaskStatus] = None,
        poem_id: Optional[str] = None
    ) -> List[WorkflowTaskResponse]:
        """Get workflow tasks with optional filtering"""
        tasks = self.repo.workflow_tasks.get_multi(
            skip=skip, limit=limit, status=status, poem_id=poem_id
        )
        return [self._workflow_task_to_response(task) for task in tasks]

    def update_workflow_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress_percentage: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> Optional[WorkflowTaskResponse]:
        """Update workflow task status"""
        try:
            task = self.repo.workflow_tasks.update_status(
                task_id, status, progress_percentage, error_message
            )
            if task:
                return self._workflow_task_to_response(task)
            return None
        except Exception as e:
            raise self._handle_error("Failed to update workflow task status", e)

    def set_workflow_task_result(self, task_id: str, result_data: Dict[str, Any]) -> Optional[WorkflowTaskResponse]:
        """Set workflow task result and mark as completed"""
        try:
            task = self.repo.workflow_tasks.set_result(task_id, result_data)
            if task:
                return self._workflow_task_to_response(task)
            return None
        except Exception as e:
            raise self._handle_error("Failed to set workflow task result", e)

    def _workflow_task_to_response(self, task: WorkflowTask) -> WorkflowTaskResponse:
        """Convert workflow task model to response schema"""
        return WorkflowTaskResponse(
            id=task.id,
            poem_id=task.poem_id,
            source_lang=task.source_lang,
            target_lang=task.target_lang,
            workflow_mode=WorkflowMode(task.workflow_mode),
            status=TaskStatus(task.status),
            progress_percentage=task.progress_percentage,
            result_json=task.result_json,
            error_message=task.error_message,
            started_at=task.started_at,
            completed_at=task.completed_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
            is_running=task.is_running,
            is_completed=task.is_completed,
            duration_seconds=task.duration_seconds
        )

    def _handle_error(self, message: str, error: Exception) -> Exception:
        """Handle and format errors consistently"""
        # Log the error here in a real application
        # For now, just wrap it with a descriptive message
        error_msg = f"{message}: {str(error)}"

        # You could create custom exception types here
        return Exception(error_msg)


# Factory function for dependency injection
def create_repository_service(db: Session) -> RepositoryWebService:
    """Create repository web service instance"""
    return RepositoryWebService(db)