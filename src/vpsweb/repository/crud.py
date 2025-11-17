"""
VPSWeb Repository CRUD Operations v0.3.1

Comprehensive CRUD operations for the 4-table database schema.
Provides create, read, update, and delete operations for poems, translations,
AI logs, and human notes with proper error handling and type safety.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid

# Define UTC+8 timezone
UTC_PLUS_8 = timezone(timedelta(hours=8))

# Import ULID generation utility from v0.3.0 utils
from vpsweb.utils.ulid_utils import generate_ulid

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .models import (
    Poem,
    Translation,
    AILog,
    HumanNote,
    TranslationWorkflowStep,
    BackgroundBriefingReport,
)
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
    TranslationWorkflowStepCreate,
    TranslationWorkflowStepResponse,
    TranslatorType,
    WorkflowMode,
    TaskStatus,
    WorkflowStepType,
)


class CRUDPoem:
    """CRUD operations for Poem model"""

    def __init__(self, db: Session):
        self.db = db

    def _safe_rollback(self):
        """Gracefully handle rollback errors that occur when no transaction is active"""
        try:
            self.db.rollback()
        except Exception:
            # Ignore rollback errors - they occur when no transaction is active
            pass

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
            self._safe_rollback()
            raise
        except SQLAlchemyError as e:
            self._safe_rollback()
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

    def count(
        self,
        poet_name: Optional[str] = None,
        language: Optional[str] = None,
        title_search: Optional[str] = None,
    ) -> int:
        """
        Get total number of poems with optional filtering

        Args:
            poet_name: Filter by poet name
            language: Filter by source language
            title_search: Search in poem title

        Returns:
            Total count of poems matching criteria
        """
        stmt = select(func.count(Poem.id))

        # Apply filters
        if poet_name:
            stmt = stmt.where(Poem.poet_name.ilike(f"%{poet_name}%"))
        if language:
            stmt = stmt.where(Poem.source_language == language)
        if title_search:
            stmt = stmt.where(Poem.poem_title.ilike(f"%{title_search}%"))

        result = self.db.execute(stmt).scalar()
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
                updated_at=datetime.now(timezone.utc),
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

    def _safe_rollback(self):
        """Gracefully handle rollback errors that occur when no transaction is active"""
        try:
            self.db.rollback()
        except Exception:
            # Ignore rollback errors - they occur when no transaction is active
            pass

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
            translated_poem_title=translation_data.translated_poem_title,  # 🎯 CRITICAL FIX: Add translated poem title
            translated_poet_name=translation_data.translated_poet_name,  # 🎯 CRITICAL FIX: Add translated poet name
            quality_rating=translation_data.quality_rating,
            raw_path=translation_data.raw_path,
        )

        try:
            self.db.add(db_translation)
            self.db.commit()
            self.db.refresh(db_translation)
            return db_translation
        except IntegrityError:
            self._safe_rollback()
            raise
        except SQLAlchemyError as e:
            self._safe_rollback()
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
        poem_id: Optional[str] = None,
    ) -> List[Translation]:
        """Get multiple translations with optional filtering"""
        stmt = select(Translation)

        if translator_type:
            stmt = stmt.where(Translation.translator_type == translator_type)
        if target_language:
            stmt = stmt.where(Translation.target_language == target_language)
        if poem_id:
            stmt = stmt.where(Translation.poem_id == poem_id)

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

    def _safe_rollback(self):
        """Gracefully handle rollback errors that occur when no transaction is active"""
        try:
            self.db.rollback()
        except Exception:
            # Ignore rollback errors - they occur when no transaction is active
            pass

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
            self._safe_rollback()
            raise
        except SQLAlchemyError as e:
            self._safe_rollback()
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

    def _safe_rollback(self):
        """Gracefully handle rollback errors that occur when no transaction is active"""
        try:
            self.db.rollback()
        except Exception:
            # Ignore rollback errors - they occur when no transaction is active
            pass

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
            self._safe_rollback()
            raise
        except SQLAlchemyError as e:
            self._safe_rollback()
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


class CRUDTranslationWorkflowStep:
    """CRUD operations for TranslationWorkflowStep model"""

    def __init__(self, db: Session):
        self.db = db

    def _safe_rollback(self):
        """Gracefully handle rollback errors that occur when no transaction is active"""
        try:
            self.db.rollback()
        except Exception:
            # Ignore rollback errors - they occur when no transaction is active
            pass

    def create(
        self, step_data: TranslationWorkflowStepCreate
    ) -> TranslationWorkflowStep:
        """
        Create a new translation workflow step

        Args:
            step_data: Workflow step creation data

        Returns:
            Created workflow step object

        Raises:
            IntegrityError: If step with same ID already exists
        """
        # Generate ULID for time-sortable unique ID
        step_id = generate_ulid()

        db_step = TranslationWorkflowStep(
            id=step_id,
            translation_id=step_data.translation_id,
            ai_log_id=step_data.ai_log_id,
            workflow_id=step_data.workflow_id,
            step_type=step_data.step_type,
            step_order=step_data.step_order,
            content=step_data.content,
            notes=step_data.notes,
            model_info=step_data.model_info,
            tokens_used=step_data.tokens_used,
            prompt_tokens=step_data.prompt_tokens,
            completion_tokens=step_data.completion_tokens,
            duration_seconds=step_data.duration_seconds,
            cost=step_data.cost,
            additional_metrics=step_data.additional_metrics,
            translated_title=step_data.translated_title,
            translated_poet_name=step_data.translated_poet_name,
            timestamp=step_data.timestamp,
        )

        try:
            self.db.add(db_step)
            self.db.commit()
            self.db.refresh(db_step)
            return db_step
        except IntegrityError:
            self._safe_rollback()
            raise
        except SQLAlchemyError as e:
            self._safe_rollback()
            raise e

    def get_by_id(self, step_id: str) -> Optional[TranslationWorkflowStep]:
        """Get workflow step by ID"""
        stmt = select(TranslationWorkflowStep).where(
            TranslationWorkflowStep.id == step_id
        )
        result = self.db.execute(stmt).scalar_one_or_none()
        return result

    def get_by_translation(self, translation_id: str) -> List[TranslationWorkflowStep]:
        """Get all workflow steps for a translation"""
        stmt = (
            select(TranslationWorkflowStep)
            .where(TranslationWorkflowStep.translation_id == translation_id)
            .order_by(
                TranslationWorkflowStep.step_order.asc(),
                TranslationWorkflowStep.timestamp.asc(),
            )
        )
        result = self.db.execute(stmt).scalars().all()
        return result

    def get_by_ai_log(self, ai_log_id: str) -> List[TranslationWorkflowStep]:
        """Get all workflow steps for an AI log"""
        stmt = (
            select(TranslationWorkflowStep)
            .where(TranslationWorkflowStep.ai_log_id == ai_log_id)
            .order_by(
                TranslationWorkflowStep.step_order.asc(),
                TranslationWorkflowStep.timestamp.asc(),
            )
        )
        result = self.db.execute(stmt).scalars().all()
        return result

    def get_by_workflow(self, workflow_id: str) -> List[TranslationWorkflowStep]:
        """Get all workflow steps for a workflow execution"""
        stmt = (
            select(TranslationWorkflowStep)
            .where(TranslationWorkflowStep.workflow_id == workflow_id)
            .order_by(
                TranslationWorkflowStep.step_order.asc(),
                TranslationWorkflowStep.timestamp.asc(),
            )
        )
        result = self.db.execute(stmt).scalars().all()
        return result

    def get_by_step_type(
        self, translation_id: str, step_type: WorkflowStepType
    ) -> Optional[TranslationWorkflowStep]:
        """Get a specific step type for a translation"""
        stmt = (
            select(TranslationWorkflowStep)
            .where(
                and_(
                    TranslationWorkflowStep.translation_id == translation_id,
                    TranslationWorkflowStep.step_type == step_type,
                )
            )
            .order_by(TranslationWorkflowStep.step_order.asc())
            .limit(1)
        )
        result = self.db.execute(stmt).scalar_one_or_none()
        return result

    def get_workflow_metrics(self, workflow_id: str) -> Dict[str, Any]:
        """Get aggregated metrics for a workflow execution"""
        stmt = select(
            func.sum(TranslationWorkflowStep.tokens_used).label("total_tokens"),
            func.sum(TranslationWorkflowStep.cost).label("total_cost"),
            func.sum(TranslationWorkflowStep.duration_seconds).label("total_duration"),
            func.count(TranslationWorkflowStep.id).label("step_count"),
        ).where(TranslationWorkflowStep.workflow_id == workflow_id)

        result = self.db.execute(stmt).first()
        return {
            "total_tokens": result.total_tokens or 0,
            "total_cost": result.total_cost or 0.0,
            "total_duration": result.total_duration or 0.0,
            "step_count": result.step_count or 0,
        }

    def update(
        self, step_id: str, update_data: Dict[str, Any]
    ) -> Optional[TranslationWorkflowStep]:
        """Update workflow step by ID"""
        stmt = (
            update(TranslationWorkflowStep)
            .where(TranslationWorkflowStep.id == step_id)
            .values(**update_data)
            .returning(TranslationWorkflowStep)
        )
        result = self.db.execute(stmt).scalar_one_or_none()

        if result:
            self.db.commit()
            self.db.refresh(result)

        return result

    def delete(self, step_id: str) -> bool:
        """Delete workflow step by ID"""
        stmt = delete(TranslationWorkflowStep).where(
            TranslationWorkflowStep.id == step_id
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount > 0

    def delete_by_workflow(self, workflow_id: str) -> int:
        """Delete all workflow steps for a workflow execution"""
        stmt = delete(TranslationWorkflowStep).where(
            TranslationWorkflowStep.workflow_id == workflow_id
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount

    def count(self) -> int:
        """Get total number of workflow steps"""
        stmt = select(func.count(TranslationWorkflowStep.id))
        result = self.db.execute(stmt).scalar()
        return result or 0

    def count_by_translation(self, translation_id: str) -> int:
        """Get number of workflow steps for a translation"""
        stmt = select(func.count(TranslationWorkflowStep.id)).where(
            TranslationWorkflowStep.translation_id == translation_id
        )
        result = self.db.execute(stmt).scalar()
        return result or 0


# CRUDWorkflowTask class removed - task tracking now handled by FastAPI app.state
# for real-time in-memory storage with enhanced step progress reporting


class CRUDBackgroundBriefingReport:
    """CRUD operations for BackgroundBriefingReport model"""

    def __init__(self, db: Session):
        self.db = db

    def _safe_rollback(self):
        """Gracefully handle rollback errors that occur when no transaction is active"""
        try:
            self.db.rollback()
        except Exception:
            # Ignore rollback errors - they occur when no transaction is active
            pass

    def create(self, bbr_data: dict) -> BackgroundBriefingReport:
        """
        Create a new Background Briefing Report

        Args:
            bbr_data: Dictionary containing BBR data

        Returns:
            Created BBR object
        """
        db_bbr = BackgroundBriefingReport(
            id=bbr_data["id"],
            poem_id=bbr_data["poem_id"],
            content=bbr_data["content"],
            model_info=bbr_data.get("model_info"),
            tokens_used=bbr_data.get("tokens_used"),
            cost=bbr_data.get("cost"),
            time_spent=bbr_data.get("time_spent"),
        )

        try:
            self.db.add(db_bbr)
            self.db.commit()
            self.db.refresh(db_bbr)
            return db_bbr
        except IntegrityError:
            self._safe_rollback()
            raise
        except SQLAlchemyError as e:
            self._safe_rollback()
            raise e

    def get_by_id(self, bbr_id: str) -> Optional[BackgroundBriefingReport]:
        """
        Get BBR by ID

        Args:
            bbr_id: BBR ID

        Returns:
            BBR object if found, None otherwise
        """
        stmt = select(BackgroundBriefingReport).where(
            BackgroundBriefingReport.id == bbr_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_poem(self, poem_id: str) -> Optional[BackgroundBriefingReport]:
        """
        Get BBR by poem ID

        Args:
            poem_id: Poem ID

        Returns:
            BBR object if found, None otherwise
        """
        stmt = select(BackgroundBriefingReport).where(
            BackgroundBriefingReport.poem_id == poem_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def update(
        self, bbr_id: str, update_data: dict
    ) -> Optional[BackgroundBriefingReport]:
        """
        Update BBR by ID

        Args:
            bbr_id: BBR ID
            update_data: Dictionary containing fields to update

        Returns:
            Updated BBR object if found, None otherwise
        """
        stmt = (
            update(BackgroundBriefingReport)
            .where(BackgroundBriefingReport.id == bbr_id)
            .values(**update_data)
            .returning(BackgroundBriefingReport)
        )
        result = self.db.execute(stmt).scalar_one_or_none()

        if result:
            self.db.commit()
            self.db.refresh(result)

        return result

    def delete(self, bbr_id: str) -> bool:
        """
        Delete BBR by ID

        Args:
            bbr_id: BBR ID

        Returns:
            True if deleted, False if not found
        """
        stmt = delete(BackgroundBriefingReport).where(
            BackgroundBriefingReport.id == bbr_id
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount > 0

    def delete_by_poem(self, poem_id: str) -> bool:
        """
        Delete BBR by poem ID

        Args:
            poem_id: Poem ID

        Returns:
            True if deleted, False if not found
        """
        stmt = delete(BackgroundBriefingReport).where(
            BackgroundBriefingReport.poem_id == poem_id
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount > 0

    def count(self) -> int:
        """Get total number of BBRs"""
        stmt = select(func.count(BackgroundBriefingReport.id))
        result = self.db.execute(stmt).scalar()
        return result or 0


# Repository service that combines all CRUD operations
class RepositoryService:
    """Main repository service combining all CRUD operations"""

    def __init__(self, db: Session):
        self.db = db
        self.poems = CRUDPoem(db)
        self.translations = CRUDTranslation(db)
        self.ai_logs = CRUDAILog(db)
        self.human_notes = CRUDHumanNote(db)
        self.workflow_steps = CRUDTranslationWorkflowStep(db)
        self.background_briefing_reports = CRUDBackgroundBriefingReport(db)
        # workflow_tasks removed - now using FastAPI app.state for task tracking

    def get_repository_stats(self) -> Dict[str, Any]:
        """Get comprehensive repository statistics"""
        return {
            "total_poets": self.db.execute(
                select(func.count(func.distinct(Poem.poet_name)))
            ).scalar(),
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
            workflow_steps = self.workflow_steps.get_by_translation(translation.id)

            result["translations"].append(
                {
                    "translation": translation,
                    "ai_logs": ai_logs,
                    "human_notes": human_notes,
                    "workflow_steps": workflow_steps,
                }
            )

        return result


# Dependency function for FastAPI
def get_repository_service(db: Session) -> RepositoryService:
    """Get repository service instance"""
    return RepositoryService(db)
