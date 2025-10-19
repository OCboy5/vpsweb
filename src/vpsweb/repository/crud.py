"""
VPSWeb Repository CRUD Operations v0.3.1

Comprehensive CRUD operations for the 4-table database schema.
Provides create, read, update, and delete operations for poems, translations,
AI logs, and human notes with proper error handling and type safety.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

# Import ULID generation utility from v0.3.0 utils
from vpsweb.utils.ulid_utils import generate_ulid

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .models import Poem, Translation, AILog, HumanNote, WorkflowTask
from .schemas import (
    PoemCreate,
    PoemUpdate,
    PoemResponse,
    TranslationCreate,
    TranslationUpdate,
    TranslationResponse,
    AILogCreate,
    AILogResponse,
    HumanNoteCreate,
    HumanNoteResponse,
    WorkflowTaskCreate,
    WorkflowTaskUpdate,
    WorkflowTaskResponse,
    TranslatorType,
    WorkflowMode,
    TaskStatus,
)


class CRUDPoem:
    """CRUD operations for Poem model"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, poem_data: PoemCreate) -> Poem:
        """
        Create a new poem

        Args:
            poem_data: Poem creation data

        Returns:
            Created poem object

        Raises:
            IntegrityError: If poem with same ID already exists
        """
        # Generate ULID for time-sortable unique ID
        poem_id = generate_ulid()

        db_poem = Poem(
            id=poem_id,
            poet_name=poem_data.poet_name,
            poem_title=poem_data.poem_title,
            source_language=poem_data.source_language,
            original_text=poem_data.original_text,
            metadata_json=poem_data.metadata_json,
        )

        try:
            self.db.add(db_poem)
            self.db.commit()
            self.db.refresh(db_poem)
            return db_poem
        except IntegrityError:
            self.db.rollback()
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    def get_by_id(self, poem_id: str) -> Optional[Poem]:
        """
        Get poem by ID

        Args:
            poem_id: Poem ID

        Returns:
            Poem object if found, None otherwise
        """
        stmt = select(Poem).where(Poem.id == poem_id)
        result = self.db.execute(stmt).scalar_one_or_none()
        return result

    def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        poet_name: Optional[str] = None,
        language: Optional[str] = None,
        title_search: Optional[str] = None,
    ) -> List[Poem]:
        """
        Get multiple poems with optional filtering

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            poet_name: Filter by poet name
            language: Filter by source language
            title_search: Search in poem title

        Returns:
            List of poem objects
        """
        stmt = select(Poem)

        # Apply filters
        if poet_name:
            stmt = stmt.where(Poem.poet_name.ilike(f"%{poet_name}%"))
        if language:
            stmt = stmt.where(Poem.source_language == language)
        if title_search:
            stmt = stmt.where(Poem.poem_title.ilike(f"%{title_search}%"))

        # Apply ordering and pagination
        stmt = stmt.order_by(Poem.created_at.desc()).offset(skip).limit(limit)

        result = self.db.execute(stmt).scalars().all()
        return result

    def update(self, poem_id: str, poem_data: PoemUpdate) -> Optional[Poem]:
        """
        Update existing poem

        Args:
            poem_id: Poem ID
            poem_data: Poem update data

        Returns:
            Updated poem object if found, None otherwise
        """
        stmt = (
            update(Poem)
            .where(Poem.id == poem_id)
            .values(
                poet_name=poem_data.poet_name,
                poem_title=poem_data.poem_title,
                source_language=poem_data.source_language,
                original_text=poem_data.original_text,
                metadata_json=poem_data.metadata_json,
                updated_at=datetime.utcnow(),
            )
        )

        result = self.db.execute(stmt)
        if result.rowcount == 0:
            return None

        self.db.commit()
        return self.get_by_id(poem_id)

    def delete(self, poem_id: str) -> bool:
        """
        Delete poem by ID

        Args:
            poem_id: Poem ID

        Returns:
            True if deleted, False if not found
        """
        stmt = delete(Poem).where(Poem.id == poem_id)
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount > 0

    def count(self) -> int:
        """Get total number of poems"""
        stmt = select(func.count(Poem.id))
        result = self.db.execute(stmt).scalar()
        return result

    def get_by_poet(self, poet_name: str) -> List[Poem]:
        """Get all poems by a specific poet"""
        stmt = (
            select(Poem)
            .where(Poem.poet_name == poet_name)
            .order_by(Poem.created_at.desc())
        )
        result = self.db.execute(stmt).scalars().all()
        return result


class CRUDTranslation:
    """CRUD operations for Translation model"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, translation_data: TranslationCreate) -> Translation:
        """
        Create a new translation

        Args:
            translation_data: Translation creation data

        Returns:
            Created translation object
        """
        # Generate ULID for time-sortable unique ID
        translation_id = generate_ulid()

        db_translation = Translation(
            id=translation_id,
            poem_id=translation_data.poem_id,
            translator_type=translation_data.translator_type,
            translator_info=translation_data.translator_info,
            target_language=translation_data.target_language,
            translated_text=translation_data.translated_text,
            quality_rating=translation_data.quality_rating,
            raw_path=translation_data.raw_path,
        )

        try:
            self.db.add(db_translation)
            self.db.commit()
            self.db.refresh(db_translation)
            return db_translation
        except IntegrityError:
            self.db.rollback()
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    def get_by_id(self, translation_id: str) -> Optional[Translation]:
        """Get translation by ID"""
        stmt = select(Translation).where(Translation.id == translation_id)
        result = self.db.execute(stmt).scalar_one_or_none()
        return result

    def get_by_poem(self, poem_id: str) -> List[Translation]:
        """Get all translations for a poem"""
        stmt = (
            select(Translation)
            .where(Translation.poem_id == poem_id)
            .order_by(Translation.created_at.desc())
        )
        result = self.db.execute(stmt).scalars().all()
        return result

    def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        translator_type: Optional[TranslatorType] = None,
        target_language: Optional[str] = None,
    ) -> List[Translation]:
        """Get multiple translations with optional filtering"""
        stmt = select(Translation)

        if translator_type:
            stmt = stmt.where(Translation.translator_type == translator_type)
        if target_language:
            stmt = stmt.where(Translation.target_language == target_language)

        stmt = stmt.order_by(Translation.created_at.desc()).offset(skip).limit(limit)
        result = self.db.execute(stmt).scalars().all()
        return result

    def update(
        self, translation_id: str, translation_data: TranslationUpdate
    ) -> Optional[Translation]:
        """Update existing translation"""
        stmt = (
            update(Translation)
            .where(Translation.id == translation_id)
            .values(
                translator_type=translation_data.translator_type,
                translator_info=translation_data.translator_info,
                target_language=translation_data.target_language,
                translated_text=translation_data.translated_text,
                quality_rating=translation_data.quality_rating,
                raw_path=translation_data.raw_path,
            )
        )

        result = self.db.execute(stmt)
        if result.rowcount == 0:
            return None

        self.db.commit()
        return self.get_by_id(translation_id)

    def delete(self, translation_id: str) -> bool:
        """Delete translation by ID"""
        stmt = delete(Translation).where(Translation.id == translation_id)
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount > 0

    def count(self) -> int:
        """Get total number of translations"""
        stmt = select(func.count(Translation.id))
        result = self.db.execute(stmt).scalar()
        return result

    def get_by_language_pair(
        self, source_lang: str, target_lang: str
    ) -> List[Translation]:
        """Get translations by language pair"""
        stmt = (
            select(Translation)
            .join(Poem)
            .where(
                and_(
                    Poem.source_language == source_lang,
                    Translation.target_language == target_lang,
                )
            )
            .order_by(Translation.created_at.desc())
        )
        result = self.db.execute(stmt).scalars().all()
        return result


class CRUDAILog:
    """CRUD operations for AILog model"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, ai_log_data: AILogCreate) -> AILog:
        """Create a new AI log entry"""
        # Generate ULID for time-sortable unique ID
        ai_log_id = generate_ulid()

        db_ai_log = AILog(
            id=ai_log_id,
            translation_id=ai_log_data.translation_id,
            model_name=ai_log_data.model_name,
            workflow_mode=ai_log_data.workflow_mode,
            token_usage_json=ai_log_data.token_usage_json,
            cost_info_json=ai_log_data.cost_info_json,
            runtime_seconds=ai_log_data.runtime_seconds,
            notes=ai_log_data.notes,
        )

        try:
            self.db.add(db_ai_log)
            self.db.commit()
            self.db.refresh(db_ai_log)
            return db_ai_log
        except IntegrityError:
            self.db.rollback()
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    def get_by_id(self, ai_log_id: str) -> Optional[AILog]:
        """Get AI log by ID"""
        stmt = select(AILog).where(AILog.id == ai_log_id)
        result = self.db.execute(stmt).scalar_one_or_none()
        return result

    def get_by_translation(self, translation_id: str) -> List[AILog]:
        """Get all AI logs for a translation"""
        stmt = (
            select(AILog)
            .where(AILog.translation_id == translation_id)
            .order_by(AILog.created_at.desc())
        )
        result = self.db.execute(stmt).scalars().all()
        return result

    def get_by_model(self, model_name: str) -> List[AILog]:
        """Get AI logs by model name"""
        stmt = (
            select(AILog)
            .where(AILog.model_name == model_name)
            .order_by(AILog.created_at.desc())
        )
        result = self.db.execute(stmt).scalars().all()
        return result

    def get_by_workflow_mode(self, workflow_mode: WorkflowMode) -> List[AILog]:
        """Get AI logs by workflow mode"""
        stmt = (
            select(AILog)
            .where(AILog.workflow_mode == workflow_mode)
            .order_by(AILog.created_at.desc())
        )
        result = self.db.execute(stmt).scalars().all()
        return result


class CRUDHumanNote:
    """CRUD operations for HumanNote model"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, note_data: HumanNoteCreate) -> HumanNote:
        """Create a new human note"""
        # Generate ULID for time-sortable unique ID
        note_id = generate_ulid()

        db_note = HumanNote(
            id=note_id,
            translation_id=note_data.translation_id,
            note_text=note_data.note_text,
        )

        try:
            self.db.add(db_note)
            self.db.commit()
            self.db.refresh(db_note)
            return db_note
        except IntegrityError:
            self.db.rollback()
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    def get_by_id(self, note_id: str) -> Optional[HumanNote]:
        """Get human note by ID"""
        stmt = select(HumanNote).where(HumanNote.id == note_id)
        result = self.db.execute(stmt).scalar_one_or_none()
        return result

    def get_by_translation(self, translation_id: str) -> List[HumanNote]:
        """Get all human notes for a translation"""
        stmt = (
            select(HumanNote)
            .where(HumanNote.translation_id == translation_id)
            .order_by(HumanNote.created_at.desc())
        )
        result = self.db.execute(stmt).scalars().all()
        return result

    def delete(self, note_id: str) -> bool:
        """Delete human note by ID"""
        stmt = delete(HumanNote).where(HumanNote.id == note_id)
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount > 0


class CRUDWorkflowTask:
    """CRUD operations for WorkflowTask model"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, task_data: WorkflowTaskCreate) -> WorkflowTask:
        """
        Create a new workflow task

        Args:
            task_data: Task creation data

        Returns:
            Created task object

        Raises:
            IntegrityError: If task with same ID already exists
        """
        # Generate UUID for task ID
        task_id = str(uuid.uuid4())

        db_task = WorkflowTask(
            id=task_id,
            poem_id=task_data.poem_id,
            source_lang=task_data.source_lang,
            target_lang=task_data.target_lang,
            workflow_mode=task_data.workflow_mode.value,
            status=TaskStatus.PENDING.value,
            progress_percentage=0,
        )

        try:
            self.db.add(db_task)
            self.db.commit()
            self.db.refresh(db_task)
            return db_task
        except IntegrityError:
            self.db.rollback()
            raise

    def get(self, task_id: str) -> Optional[WorkflowTask]:
        """
        Get a workflow task by ID

        Args:
            task_id: Task ID

        Returns:
            Task object if found, None otherwise
        """
        stmt = select(WorkflowTask).where(WorkflowTask.id == task_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        status: Optional[TaskStatus] = None,
        poem_id: Optional[str] = None,
    ) -> List[WorkflowTask]:
        """
        Get multiple workflow tasks with optional filtering

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by task status
            poem_id: Filter by poem ID

        Returns:
            List of task objects
        """
        stmt = select(WorkflowTask).offset(skip).limit(limit)

        if status:
            stmt = stmt.where(WorkflowTask.status == status.value)
        if poem_id:
            stmt = stmt.where(WorkflowTask.poem_id == poem_id)

        stmt = stmt.order_by(WorkflowTask.created_at.desc())

        return self.db.execute(stmt).scalars().all()

    def update(
        self, task_id: str, task_data: WorkflowTaskUpdate
    ) -> Optional[WorkflowTask]:
        """
        Update a workflow task

        Args:
            task_id: Task ID
            task_data: Update data

        Returns:
            Updated task object if found, None otherwise
        """
        stmt = (
            update(WorkflowTask)
            .where(WorkflowTask.id == task_id)
            .values(**task_data.model_dump(exclude_unset=True))
            .returning(WorkflowTask)
        )

        try:
            result = self.db.execute(stmt)
            self.db.commit()
            return result.scalar_one_or_none()
        except SQLAlchemyError:
            self.db.rollback()
            return None

    def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress_percentage: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> Optional[WorkflowTask]:
        """
        Update task status with optional progress and error message

        Args:
            task_id: Task ID
            status: New status
            progress_percentage: Progress percentage (0-100)
            error_message: Error message if status is failed

        Returns:
            Updated task object if found, None otherwise
        """
        update_data = {"status": status.value}

        if progress_percentage is not None:
            update_data["progress_percentage"] = progress_percentage
        if error_message is not None:
            update_data["error_message"] = error_message

        # Set timestamps
        if status == TaskStatus.RUNNING:
            update_data["started_at"] = datetime.utcnow()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            update_data["completed_at"] = datetime.utcnow()

        return self.update(task_id, WorkflowTaskUpdate(**update_data))

    def set_result(
        self, task_id: str, result_data: Dict[str, Any]
    ) -> Optional[WorkflowTask]:
        """
        Set task result and mark as completed

        Args:
            task_id: Task ID
            result_data: Result data as dictionary

        Returns:
            Updated task object if found, None otherwise
        """
        import json

        result_json = json.dumps(result_data)

        update_data = WorkflowTaskUpdate(
            status=TaskStatus.COMPLETED,
            progress_percentage=100,
            result_json=result_json,
            completed_at=datetime.utcnow(),
        )

        return self.update(task_id, update_data)

    def delete(self, task_id: str) -> bool:
        """
        Delete a workflow task

        Args:
            task_id: Task ID

        Returns:
            True if deleted, False otherwise
        """
        stmt = delete(WorkflowTask).where(WorkflowTask.id == task_id)
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount > 0

    def count(self, *, status: Optional[TaskStatus] = None) -> int:
        """
        Count workflow tasks with optional filtering

        Args:
            status: Filter by task status

        Returns:
            Number of tasks
        """
        stmt = select(func.count(WorkflowTask.id))

        if status:
            stmt = stmt.where(WorkflowTask.status == status.value)

        return self.db.execute(stmt).scalar()


# Repository service that combines all CRUD operations
class RepositoryService:
    """Main repository service combining all CRUD operations"""

    def __init__(self, db: Session):
        self.db = db
        self.poems = CRUDPoem(db)
        self.translations = CRUDTranslation(db)
        self.ai_logs = CRUDAILog(db)
        self.human_notes = CRUDHumanNote(db)
        self.workflow_tasks = CRUDWorkflowTask(db)

    def get_repository_stats(self) -> Dict[str, Any]:
        """Get comprehensive repository statistics"""
        return {
            "total_poems": self.poems.count(),
            "total_translations": self.translations.count(),
            "ai_translations": self.db.execute(
                select(func.count(Translation.id)).where(
                    Translation.translator_type == TranslatorType.AI
                )
            ).scalar(),
            "human_translations": self.db.execute(
                select(func.count(Translation.id)).where(
                    Translation.translator_type == TranslatorType.HUMAN
                )
            ).scalar(),
            "languages": list(
                self.db.execute(select(Poem.source_language).distinct()).scalars()
            ),
            "latest_translation": self.db.execute(
                select(func.max(Translation.created_at))
            ).scalar(),
        }

    def search_poems(self, query: str, limit: int = 50) -> List[Poem]:
        """Search poems by text content"""
        stmt = (
            select(Poem)
            .where(
                or_(
                    Poem.poem_title.ilike(f"%{query}%"),
                    Poem.original_text.ilike(f"%{query}%"),
                    Poem.poet_name.ilike(f"%{query}%"),
                )
            )
            .limit(limit)
            .order_by(Poem.created_at.desc())
        )
        return self.db.execute(stmt).scalars().all()

    def get_poem_with_translations(self, poem_id: str) -> Optional[Dict[str, Any]]:
        """Get poem with all its translations and related data"""
        poem = self.poems.get_by_id(poem_id)
        if not poem:
            return None

        translations = self.translations.get_by_poem(poem_id)

        result = {"poem": poem, "translations": []}

        for translation in translations:
            ai_logs = self.ai_logs.get_by_translation(translation.id)
            human_notes = self.human_notes.get_by_translation(translation.id)

            result["translations"].append(
                {
                    "translation": translation,
                    "ai_logs": ai_logs,
                    "human_notes": human_notes,
                }
            )

        return result


# Dependency function for FastAPI
def get_repository_service(db: Session) -> RepositoryService:
    """Get repository service instance"""
    return RepositoryService(db)
