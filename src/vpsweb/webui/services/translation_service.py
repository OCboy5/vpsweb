"""
Translation Service for Repository Integration

Service layer for managing translation data in the repository.
Provides business logic for translation operations and workflow integration.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ...repository.models import Translation, AILog, Poem
from ...repository.crud import RepositoryService
from ...utils.ulid_utils import generate_ulid

logger = logging.getLogger(__name__)


class TranslationService:
    """Service layer for translation management operations."""

    def __init__(self, db: Session):
        """
        Initialize translation service with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.repository_service = RepositoryService(db)
        logger.info("TranslationService initialized")

    async def get_translation(self, translation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a translation by ID with related data.

        Args:
            translation_id: Unique identifier for the translation

        Returns:
            Translation data dictionary or None if not found
        """
        try:
            translation = self.repository_service.translations.get_by_id(translation_id)
            if not translation:
                return None

            # Get AI logs if available
            ai_logs = []
            if translation.has_ai_logs:
                ai_logs = [
                    {
                        "id": log.id,
                        "model_name": log.model_name,
                        "workflow_mode": log.workflow_mode,
                        "token_usage": log.token_usage,
                        "cost_info": log.cost_info,
                        "runtime_seconds": log.runtime_seconds,
                        "notes": log.notes,
                        "created_at": log.created_at.isoformat() if log.created_at else None
                    }
                    for log in translation.ai_logs
                ]

            # Get human notes if available
            human_notes = []
            if translation.has_human_notes:
                human_notes = [
                    {
                        "id": note.id,
                        "note_text": note.note_text,
                        "created_at": note.created_at.isoformat() if note.created_at else None
                    }
                    for note in translation.human_notes
                ]

            return {
                "id": translation.id,
                "poem_id": translation.poem_id,
                "translator_type": translation.translator_type,
                "translator_info": translation.translator_info,
                "target_language": translation.target_language,
                "translated_text": translation.translated_text,
                "quality_rating": translation.quality_rating,
                "raw_path": translation.raw_path,
                "created_at": translation.created_at.isoformat() if translation.created_at else None,
                "ai_logs": ai_logs,
                "human_notes": human_notes,
                "poem": {
                    "id": translation.poem.id,
                    "poet_name": translation.poem.poet_name,
                    "poem_title": translation.poem.poem_title,
                    "source_language": translation.poem.source_language
                } if translation.poem else None
            }

        except Exception as e:
            logger.error(f"Failed to get translation {translation_id}: {e}")
            raise

    async def list_translations(
        self,
        skip: int = 0,
        limit: int = 100,
        poem_id: Optional[str] = None,
        target_language: Optional[str] = None,
        translator_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List translations with optional filtering.

        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            poem_id: Filter by poem ID
            target_language: Filter by target language
            translator_type: Filter by translator type (ai/human)

        Returns:
            List of translation data dictionaries
        """
        try:
            # Apply filters if provided
            query = self.db.query(Translation).join(Poem)

            if poem_id:
                query = query.filter(Translation.poem_id == poem_id)

            if target_language:
                query = query.filter(Translation.target_language == target_language)

            if translator_type:
                query = query.filter(Translation.translator_type == translator_type)

            # Order by creation date (newest first) and paginate
            translations = query.order_by(desc(Translation.created_at)).offset(skip).limit(limit).all()

            return [
                {
                    "id": translation.id,
                    "poem_id": translation.poem_id,
                    "poem_title": translation.poem.poem_title,
                    "poet_name": translation.poem.poet_name,
                    "translator_type": translation.translator_type,
                    "translator_info": translation.translator_info,
                    "target_language": translation.target_language,
                    "translated_preview": translation.translated_text[:200] + "..." if len(translation.translated_text) > 200 else translation.translated_text,
                    "quality_rating": translation.quality_rating,
                    "created_at": translation.created_at.isoformat() if translation.created_at else None,
                    "has_ai_logs": translation.has_ai_logs,
                    "has_human_notes": translation.has_human_notes
                }
                for translation in translations
            ]

        except Exception as e:
            logger.error(f"Failed to list translations: {e}")
            raise

    async def create_translation(
        self,
        poem_id: str,
        source_lang: str,
        target_lang: str,
        workflow_mode: str,
        translation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new translation from VPSWeb workflow output.

        Args:
            poem_id: ID of the source poem
            source_lang: Source language code
            target_lang: Target language code
            workflow_mode: Workflow mode used
            translation_data: Translation data from VPSWeb workflow

        Returns:
            Created translation data dictionary
        """
        try:
            # Validate poem exists
            poem = self.repository_service.poems.get_by_id(poem_id)
            if not poem:
                raise ValueError(f"Poem not found: {poem_id}")

            # Generate unique ID
            translation_id = generate_ulid()

            # Create translation record
            translation = Translation(
                id=translation_id,
                poem_id=poem_id,
                translator_type="ai",
                translator_info=f"VPSWeb {workflow_mode} workflow",
                target_language=target_lang.lower(),
                translated_text=translation_data.get("revised_translation", ""),
                quality_rating=None,  # Could be calculated later
                raw_path=None,  # Could store file path if needed
                created_at=datetime.utcnow()
            )

            # Save translation
            self.db.add(translation)
            self.db.flush()  # Get ID without committing

            # Create AI log with workflow details
            ai_log = AILog(
                id=generate_ulid(),
                translation_id=translation.id,
                model_name="VPSWeb Workflow",  # Could be more specific
                workflow_mode=workflow_mode,
                token_usage_json=json.dumps({
                    "total_tokens": translation_data.get("total_tokens", 0),
                    "initial_tokens": translation_data.get("initial_tokens", 0),
                    "editor_tokens": translation_data.get("editor_tokens", 0),
                    "revision_tokens": translation_data.get("revision_tokens", 0)
                }),
                cost_info_json=json.dumps({
                    "total_cost": translation_data.get("total_cost", 0.0),
                    "initial_cost": translation_data.get("initial_cost", 0.0),
                    "editor_cost": translation_data.get("editor_cost", 0.0),
                    "revision_cost": translation_data.get("revision_cost", 0.0)
                }),
                runtime_seconds=translation_data.get("duration_seconds"),
                notes=json.dumps({
                    "workflow_id": translation_data.get("workflow_id"),
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "full_log": translation_data.get("full_log", ""),
                    "step_details": {
                        "initial_translation": {
                            "text": translation_data.get("initial_translation", ""),
                            "notes": translation_data.get("initial_translation_notes", ""),
                            "model_info": translation_data.get("initial_model_info", {})
                        },
                        "editor_suggestions": {
                            "text": translation_data.get("editor_suggestions", ""),
                            "model_info": translation_data.get("editor_model_info", {})
                        },
                        "revision": {
                            "text": translation_data.get("revised_translation", ""),
                            "notes": translation_data.get("revised_translation_notes", ""),
                            "model_info": translation_data.get("revision_model_info", {})
                        }
                    }
                }),
                created_at=datetime.utcnow()
            )

            # Save AI log
            self.db.add(ai_log)

            # Commit everything
            self.db.commit()
            self.db.refresh(translation)

            logger.info(f"Created translation: {translation_id} for poem: {poem_id}")

            # Return full translation data
            return await self.get_translation(translation_id)

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to create translation: {e}")
            self.db.rollback()
            raise

    async def update_translation(
        self,
        translation_id: str,
        translated_text: Optional[str] = None,
        quality_rating: Optional[int] = None,
        translator_info: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing translation.

        Args:
            translation_id: Unique identifier for the translation
            translated_text: Updated translated text (optional)
            quality_rating: Updated quality rating 1-5 (optional)
            translator_info: Updated translator info (optional)

        Returns:
            Updated translation data dictionary or None if not found

        Raises:
            ValueError: If updated fields are invalid
        """
        try:
            translation = self.repository_service.translations.get_by_id(translation_id)
            if not translation:
                return None

            # Update fields if provided
            if translated_text is not None:
                if not translated_text or not translated_text.strip():
                    raise ValueError("Translated text cannot be empty")
                translation.translated_text = translated_text.strip()

            if quality_rating is not None:
                if not 1 <= quality_rating <= 5:
                    raise ValueError("Quality rating must be between 1 and 5")
                translation.quality_rating = quality_rating

            if translator_info is not None:
                translation.translator_info = translator_info

            # Save changes
            self.db.commit()
            self.db.refresh(translation)

            logger.info(f"Updated translation: {translation_id}")

            return await self.get_translation(translation_id)

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update translation {translation_id}: {e}")
            self.db.rollback()
            raise

    async def delete_translation(self, translation_id: str) -> bool:
        """
        Delete a translation and its related logs and notes.

        Args:
            translation_id: Unique identifier for the translation

        Returns:
            True if translation was deleted, False if not found
        """
        try:
            translation = self.repository_service.translations.get_by_id(translation_id)
            if not translation:
                return False

            # Delete translation (cascade will delete AI logs and human notes)
            self.db.delete(translation)
            self.db.commit()

            logger.info(f"Deleted translation: {translation_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete translation {translation_id}: {e}")
            self.db.rollback()
            raise

    async def add_human_note(
        self,
        translation_id: str,
        note_text: str
    ) -> Dict[str, Any]:
        """
        Add a human note to a translation.

        Args:
            translation_id: Unique identifier for the translation
            note_text: Text content of the note

        Returns:
            Created note data dictionary

        Raises:
            ValueError: If translation not found or note text invalid
        """
        try:
            # Validate translation exists
            translation = self.repository_service.translations.get_by_id(translation_id)
            if not translation:
                raise ValueError(f"Translation not found: {translation_id}")

            if not note_text or not note_text.strip():
                raise ValueError("Note text cannot be empty")

            # Create note
            note = HumanNote(
                id=generate_ulid(),
                translation_id=translation_id,
                note_text=note_text.strip(),
                created_at=datetime.utcnow()
            )

            # Save note
            self.db.add(note)
            self.db.commit()
            self.db.refresh(note)

            logger.info(f"Added human note to translation: {translation_id}")

            return {
                "id": note.id,
                "translation_id": note.translation_id,
                "note_text": note.note_text,
                "created_at": note.created_at.isoformat() if note.created_at else None
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to add human note: {e}")
            self.db.rollback()
            raise

    async def get_translation_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about translations in the repository.

        Returns:
            Dictionary with translation statistics
        """
        try:
            total_translations = self.db.query(Translation).count()

            # Count by type
            ai_count = self.db.query(Translation).filter_by(translator_type='ai').count()
            human_count = self.db.query(Translation).filter_by(translator_type='human').count()

            # Count by language
            target_languages = self.db.query(
                Translation.target_language,
                self.db.func.count(Translation.id).label('count')
            ).group_by(Translation.target_language).all()

            # Count by workflow mode (from AI logs)
            workflow_modes = self.db.query(
                AILog.workflow_mode,
                self.db.func.count(AILog.id).label('count')
            ).group_by(AILog.workflow_mode).all()

            # Calculate average quality rating
            avg_quality = self.db.query(
                self.db.func.avg(Translation.quality_rating)
            ).filter(Translation.quality_rating.isnot(None)).scalar()

            return {
                "total_translations": total_translations,
                "ai_translations": ai_count,
                "human_translations": human_count,
                "target_languages": [
                    {"language": lang.target_language, "count": lang.count}
                    for lang in target_languages
                ],
                "workflow_modes": [
                    {"mode": mode.workflow_mode, "count": mode.count}
                    for mode in workflow_modes
                ],
                "average_quality_rating": float(avg_quality) if avg_quality else None
            }

        except Exception as e:
            logger.error(f"Failed to get translation statistics: {e}")
            raise

    async def get_poem_translations(self, poem_id: str) -> List[Dict[str, Any]]:
        """
        Get all translations for a specific poem.

        Args:
            poem_id: Unique identifier for the poem

        Returns:
            List of translation data dictionaries
        """
        return await self.list_translations(poem_id=poem_id, limit=1000)

    async def search_translations(
        self,
        query: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search translations by translated text or poem info.

        Args:
            query: Search query string
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching translations
        """
        try:
            if not query or len(query.strip()) < 2:
                return []

            search_term = f"%{query.strip()}%"

            translations = self.db.query(Translation).join(Poem).filter(
                (Translation.translated_text.ilike(search_term)) |
                (Poem.poet_name.ilike(search_term)) |
                (Poem.poem_title.ilike(search_term))
            ).order_by(desc(Translation.created_at)).offset(skip).limit(limit).all()

            return [
                {
                    "id": translation.id,
                    "poem_id": translation.poem_id,
                    "poem_title": translation.poem.poem_title,
                    "poet_name": translation.poem.poet_name,
                    "translator_type": translation.translator_type,
                    "target_language": translation.target_language,
                    "translated_preview": translation.translated_text[:200] + "..." if len(translation.translated_text) > 200 else translation.translated_text,
                    "quality_rating": translation.quality_rating,
                    "created_at": translation.created_at.isoformat() if translation.created_at else None
                }
                for translation in translations
            ]

        except Exception as e:
            logger.error(f"Failed to search translations: {e}")
            raise