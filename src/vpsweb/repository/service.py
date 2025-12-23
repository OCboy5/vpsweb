"""
VPSWeb Repository Service Layer v0.3.1

Service layer that provides a clean interface between the webui and repository layers.
Handles database operations, error handling, and business logic.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from .crud import RepositoryService
from .models import AILog, HumanNote, Poem, Translation
from .schemas import (AILogCreate, AILogResponse, HumanNoteCreate,
                      HumanNoteResponse, PoemCreate, PoemResponse, PoemUpdate,
                      RepositoryStats, TranslationCreate, TranslationResponse,
                      TranslationUpdate)


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
            "recent_translations": [
                self._translation_to_response(t) for t in recent_translations
            ],
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
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated poems with optional filtering"""
        offset = (page - 1) * page_size

        if search:
            poems = self.repo.search_poems(search, limit=page_size)
            total = len(poems)  # Note: For large datasets, this should be optimized
        else:
            poems = self.repo.poems.get_multi(
                skip=offset, limit=page_size, poet_name=poet, language=language
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
                "has_previous": page > 1,
            },
        }

    def update_poem(
        self, poem_id: str, poem_data: PoemUpdate
    ) -> Optional[PoemResponse]:
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
            # First, delete all related translations manually (cascade delete)
            translations = self.repo.translations.get_by_poem(poem_id)
            for translation in translations:
                self.repo.translations.delete(translation.id)

            # Then delete the poem
            return self.repo.poems.delete(poem_id)
        except Exception as e:
            raise self._handle_error("Failed to delete poem", e)

    # Translation Methods
    def create_translation(
        self, translation_data: TranslationCreate
    ) -> TranslationResponse:
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
        result = []
        for translation in translations:
            # Manually load AI logs for workflow mode
            workflow_mode = None
            if translation.translator_type == "ai":
                ai_logs = self.repo.ai_logs.get_by_translation(translation.id)
                workflow_mode = ai_logs[0].workflow_mode if ai_logs else None

            translation_response = self._translation_to_response(
                translation, workflow_mode
            )
            result.append(translation_response)
        return result

    def get_translation_with_details(
        self, translation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get translation with all related details (AI logs, human notes)"""
        translation = self.repo.translations.get_by_id(translation_id)
        if not translation:
            return None

        ai_logs = self.repo.ai_logs.get_by_translation(translation_id)
        human_notes = self.repo.human_notes.get_by_translation(translation_id)

        return {
            "translation": self._translation_to_response(translation),
            "ai_logs": [self._ai_log_to_response(log) for log in ai_logs],
            "human_notes": [self._human_note_to_response(note) for note in human_notes],
        }

    def update_translation(
        self, translation_id: str, translation_data: TranslationUpdate
    ) -> Optional[TranslationResponse]:
        """Update a translation"""
        try:
            translation = self.repo.translations.update(
                translation_id, translation_data
            )
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
                raise ValueError(
                    f"Translation with ID {ai_log_data.translation_id} not found"
                )

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
                raise ValueError(
                    f"Translation with ID {note_data.translation_id} not found"
                )

            note = self.repo.human_notes.create(note_data)
            return self._human_note_to_response(note)
        except Exception as e:
            raise self._handle_error("Failed to create human note", e)

    def get_human_notes_by_translation(
        self, translation_id: str
    ) -> List[HumanNoteResponse]:
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
            translation_count=poem.translation_count,
        )

    def _translation_to_response(
        self, translation: Translation, workflow_mode: Optional[str] = None
    ) -> TranslationResponse:
        """Convert translation model to response schema"""
        return TranslationResponse(
            id=translation.id,
            poem_id=translation.poem_id,
            translator_type=translation.translator_type,
            translator_info=translation.translator_info,
            target_language=translation.target_language,
            translated_text=translation.translated_text,
            translated_poem_title=translation.translated_poem_title,
            translated_poet_name=translation.translated_poet_name,
            quality_rating=translation.quality_rating,
            raw_path=translation.raw_path,
            created_at=translation.created_at,
            workflow_mode=workflow_mode,
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
            created_at=ai_log.created_at,
        )

    def _human_note_to_response(self, note: HumanNote) -> HumanNoteResponse:
        """Convert human note model to response schema"""
        return HumanNoteResponse(
            id=note.id,
            translation_id=note.translation_id,
            note_text=note.note_text,
            created_at=note.created_at,
        )

    # Workflow Task Methods removed - task tracking now handled by FastAPI app.state
    # for real-time in-memory storage with enhanced step progress reporting

    # Poet-Specific Methods for Enhanced Browsing
    def get_all_poets(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        sort_by: str = "name",
        sort_order: str = "asc",
        min_poems: Optional[int] = None,
        min_translations: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get all poets with statistics and activity metrics"""
        # Ensure fresh transaction snapshot for SQLite WAL mode
        # This fixes the issue where poets added in other sessions are not visible
        self.db.rollback()

        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Getting poets: skip={skip}, limit={limit}, search={search}")

        from sqlalchemy import case, desc, func

        # Base query with poet statistics (separated by AI and Human)
        query = (
            self.db.query(
                Poem.poet_name,
                func.count(func.distinct(Poem.id)).label("poem_count"),
                func.count(Translation.id).label("translation_count"),
                func.sum(case((Translation.translator_type == "ai", 1), else_=0)).label(
                    "ai_translation_count"
                ),
                func.sum(
                    case((Translation.translator_type == "human", 1), else_=0)
                ).label("human_translation_count"),
                func.avg(Translation.quality_rating).label("avg_quality_rating"),
                func.max(Translation.created_at).label("last_translation_date"),
                func.max(Poem.created_at).label("last_poem_date"),
            )
            .outerjoin(
                Translation,
                Poem.id == Translation.poem_id,
            )
            .group_by(Poem.poet_name)
        )

        # Apply filters
        if search:
            query = query.filter(Poem.poet_name.ilike(f"%{search}%"))

        if min_poems is not None:
            query = query.having(func.count(func.distinct(Poem.id)) >= min_poems)

        if min_translations is not None:
            query = query.having(func.count(Translation.id) >= min_translations)

        # Apply sorting
        if sort_by == "name":
            order_column = Poem.poet_name
        elif sort_by == "poem_count":
            order_column = func.count(func.distinct(Poem.id))
        elif sort_by == "translation_count":
            order_column = func.count(Translation.id)
        elif sort_by == "recent_activity":
            # SQLite doesn't support greatest() function
            # Use a CASE statement to choose the latest date
            from sqlalchemy import case

            order_column = case(
                (
                    func.max(Translation.created_at) >= func.max(Poem.created_at),
                    func.max(Translation.created_at),
                ),
                else_=func.max(Poem.created_at),
            )
        else:
            order_column = Poem.poet_name

        if sort_order.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(order_column)

        # Get total count and apply pagination
        total_count = query.count()
        poets_data = query.offset(skip).limit(limit).all()

        return {
            "poets": [
                {
                    "poet_name": row.poet_name,
                    "poem_count": row.poem_count,
                    "translation_count": row.translation_count or 0,
                    "ai_translation_count": row.ai_translation_count or 0,
                    "human_translation_count": row.human_translation_count or 0,
                    "avg_quality_rating": (
                        float(row.avg_quality_rating)
                        if row.avg_quality_rating
                        else None
                    ),
                    "last_translation_date": row.last_translation_date,
                    "last_poem_date": row.last_poem_date,
                }
                for row in poets_data
            ],
            "total_count": total_count,
            "skip": skip,
            "limit": limit,
        }

    def get_poems_by_poet(
        self,
        poet_name: str,
        skip: int = 0,
        limit: int = 20,
        language: Optional[str] = None,
        has_translations: Optional[bool] = None,
        sort_by: str = "title",
        sort_order: str = "asc",
    ) -> Dict[str, Any]:
        """Get poems by a specific poet with translation information"""
        from sqlalchemy import desc, func

        # Base query for poems by poet with translation counts
        query = (
            self.db.query(
                Poem,
                func.count(Translation.id).label("translation_count"),
                func.max(Translation.created_at).label("last_translation_date"),
            )
            .outerjoin(
                Translation,
                Poem.id == Translation.poem_id,
            )
            .filter(Poem.poet_name == poet_name)
            .group_by(Poem.id)
        )

        # Apply filters
        if language:
            query = query.filter(Poem.source_language == language)

        if has_translations is not None:
            if has_translations:
                query = query.having(func.count(Translation.id) > 0)
            else:
                query = query.having(func.count(Translation.id) == 0)

        # Apply sorting
        if sort_by == "title":
            order_column = Poem.poem_title
        elif sort_by == "created_at":
            order_column = Poem.created_at
        elif sort_by == "translation_count":
            order_column = func.count(Translation.id)
        else:
            order_column = Poem.poem_title

        if sort_order.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(order_column)

        # Get total count and apply pagination
        total_count = query.count()
        poems_data = query.offset(skip).limit(limit).all()

        return {
            "poet_name": poet_name,
            "poems": [
                {
                    "id": poem.id,
                    "poet_name": poem.poet_name,
                    "poem_title": poem.poem_title,
                    "source_language": poem.source_language,
                    "original_text": poem.original_text,
                    "created_at": poem.created_at,
                    "updated_at": poem.updated_at,
                    "translation_count": translation_count or 0,
                    "last_translation_date": last_translation_date,
                }
                for poem, translation_count, last_translation_date in poems_data
            ],
            "total_count": total_count,
            "skip": skip,
            "limit": limit,
        }

    def get_translations_by_poet(
        self,
        poet_name: str,
        skip: int = 0,
        limit: int = 20,
        target_language: Optional[str] = None,
        translator_type: Optional[str] = None,
        min_quality: Optional[int] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """Get translations by a specific poet with detailed information"""
        from sqlalchemy import desc

        # Base query for translations by poet
        query = (
            self.db.query(
                Translation,
                Poem.poem_title,
                Poem.source_language,
            )
            .join(
                Poem,
                Translation.poem_id == Poem.id,
            )
            .filter(Poem.poet_name == poet_name)
        )

        # Apply filters
        if target_language:
            query = query.filter(Translation.target_language == target_language)

        if translator_type:
            query = query.filter(Translation.translator_type == translator_type)

        if min_quality is not None:
            query = query.filter(Translation.quality_rating >= min_quality)

        # Apply sorting
        if sort_by == "created_at":
            order_column = Translation.created_at
        elif sort_by == "quality_rating":
            order_column = Translation.quality_rating
        elif sort_by == "title":
            order_column = Poem.poem_title
        else:
            order_column = Translation.created_at

        if sort_order.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(order_column)

        # Get total count and apply pagination
        total_count = query.count()
        translations_data = query.offset(skip).limit(limit).all()

        return {
            "poet_name": poet_name,
            "translations": [
                {
                    "id": translation.id,
                    "poem_id": translation.poem_id,
                    "poem_title": poem_title,
                    "source_language": source_language,
                    "target_language": translation.target_language,
                    "translator_type": translation.translator_type,
                    "translator_info": translation.translator_info,
                    "translated_text": translation.translated_text,
                    "quality_rating": translation.quality_rating,
                    "created_at": translation.created_at,
                    "raw_path": translation.raw_path,
                }
                for translation, poem_title, source_language in translations_data
            ],
            "total_count": total_count,
            "skip": skip,
            "limit": limit,
        }

    def get_translation_history(self, poem_id: str) -> List[Dict[str, Any]]:
        """Get translation history for a specific poem"""
        translations = (
            self.db.query(Translation)
            .filter(Translation.poem_id == poem_id)
            .order_by(Translation.created_at.desc())
            .all()
        )

        return [
            {
                "id": translation.id,
                "translator_type": translation.translator_type,
                "translator_info": translation.translator_info,
                "target_language": translation.target_language,
                "quality_rating": translation.quality_rating,
                "created_at": translation.created_at,
                "has_ai_logs": len(translation.ai_logs) > 0,
                "has_human_notes": len(translation.human_notes) > 0,
            }
            for translation in translations
        ]

    def get_poet_statistics(self, poet_name: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a specific poet"""
        # Ensure fresh transaction snapshot
        self.db.rollback()
        
        from sqlalchemy import func

        # Check if poet exists
        poet_exists = self.db.query(Poem).filter(Poem.poet_name == poet_name).first()

        if not poet_exists:
            raise ValueError(f"Poet '{poet_name}' not found")

        # Get poem statistics
        poem_stats = (
            self.db.query(
                func.count(Poem.id).label("total_poems"),
                func.count(func.distinct(Poem.source_language)).label(
                    "source_languages_count"
                ),
                func.min(Poem.created_at).label("first_poem_date"),
                func.max(Poem.created_at).label("last_poem_date"),
            )
            .filter(Poem.poet_name == poet_name)
            .first()
        )

        # Get translation statistics
        translation_stats = (
            self.db.query(
                func.count(Translation.id).label("total_translations"),
                func.count(func.distinct(Translation.target_language)).label(
                    "target_languages_count"
                ),
                func.avg(Translation.quality_rating).label("avg_quality_rating"),
                func.count(func.distinct(Translation.translator_type)).label(
                    "translator_types_count"
                ),
                func.min(Translation.created_at).label("first_translation_date"),
                func.max(Translation.created_at).label("last_translation_date"),
            )
            .join(
                Poem,
                Translation.poem_id == Poem.id,
            )
            .filter(Poem.poet_name == poet_name)
            .first()
        )

        return {
            "poet_name": poet_name,
            "poem_statistics": {
                "total_poems": poem_stats.total_poems,
                "source_languages_count": poem_stats.source_languages_count,
                "first_poem_date": poem_stats.first_poem_date,
                "last_poem_date": poem_stats.last_poem_date,
            },
            "translation_statistics": {
                "total_translations": translation_stats.total_translations or 0,
                "target_languages_count": translation_stats.target_languages_count or 0,
                "avg_quality_rating": (
                    float(translation_stats.avg_quality_rating)
                    if translation_stats.avg_quality_rating
                    else None
                ),
                "translator_types_count": translation_stats.translator_types_count or 0,
                "first_translation_date": translation_stats.first_translation_date,
                "last_translation_date": translation_stats.last_translation_date,
            },
        }

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
