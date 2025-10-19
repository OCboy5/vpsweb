"""
Poem Service for Repository Integration

Service layer for managing poem data in the repository.
Provides business logic for poem operations.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ...repository.models import Poem
from ...repository.crud import RepositoryService
from ...utils.ulid_utils import generate_ulid

logger = logging.getLogger(__name__)


class PoemService:
    """Service layer for poem management operations."""

    def __init__(self, db: Session):
        """
        Initialize poem service with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.repository_service = RepositoryService(db)
        logger.info("PoemService initialized")

    async def get_poem(self, poem_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a poem by ID.

        Args:
            poem_id: Unique identifier for the poem

        Returns:
            Poem data dictionary or None if not found
        """
        try:
            poem = self.repository_service.poems.get_by_id(poem_id)
            if not poem:
                return None

            return {
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

        except Exception as e:
            logger.error(f"Failed to get poem {poem_id}: {e}")
            raise

    async def list_poems(
        self,
        skip: int = 0,
        limit: int = 100,
        poet_name: Optional[str] = None,
        source_language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List poems with optional filtering.

        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            poet_name: Filter by poet name
            source_language: Filter by source language

        Returns:
            List of poem data dictionaries
        """
        try:
            # Apply filters if provided
            query = self.db.query(Poem)

            if poet_name:
                query = query.filter(Poem.poet_name.ilike(f"%{poet_name}%"))

            if source_language:
                query = query.filter(Poem.source_language == source_language)

            # Order by creation date (newest first) and paginate
            poems = (
                query.order_by(desc(Poem.created_at)).offset(skip).limit(limit).all()
            )

            return [
                {
                    "id": poem.id,
                    "poet_name": poem.poet_name,
                    "poem_title": poem.poem_title,
                    "source_language": poem.source_language,
                    "content_preview": (
                        poem.original_text[:200] + "..."
                        if len(poem.original_text) > 200
                        else poem.original_text
                    ),
                    "created_at": (
                        poem.created_at.isoformat() if poem.created_at else None
                    ),
                    "updated_at": (
                        poem.updated_at.isoformat() if poem.updated_at else None
                    ),
                    "translation_count": poem.translation_count,
                    "ai_translation_count": poem.ai_translation_count,
                    "human_translation_count": poem.human_translation_count,
                }
                for poem in poems
            ]

        except Exception as e:
            logger.error(f"Failed to list poems: {e}")
            raise

    async def create_poem(
        self,
        poet_name: str,
        poem_title: str,
        source_language: str,
        content: str,
        metadata_json: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new poem in the repository.

        Args:
            poet_name: Name of the poet
            poem_title: Title of the poem
            source_language: Source language code
            content: Full text content of the poem
            metadata_json: Optional metadata as JSON string

        Returns:
            Created poem data dictionary

        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            # Validate input
            if not poet_name or not poet_name.strip():
                raise ValueError("Poet name is required")

            if not poem_title or not poem_title.strip():
                raise ValueError("Poem title is required")

            if not source_language or not source_language.strip():
                raise ValueError("Source language is required")

            if not content or not content.strip():
                raise ValueError("Poem content is required")

            if len(content.strip()) < 10:
                raise ValueError("Poem content must be at least 10 characters")

            # Generate unique ID
            poem_id = generate_ulid()

            # Create poem record
            poem = Poem(
                id=poem_id,
                poet_name=poet_name.strip(),
                poem_title=poem_title.strip(),
                source_language=source_language.strip().lower(),
                original_text=content.strip(),
                metadata_json=metadata_json,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            # Save to database
            self.db.add(poem)
            self.db.commit()
            self.db.refresh(poem)

            logger.info(f"Created poem: {poem_id} - {poem_title} by {poet_name}")

            return {
                "id": poem.id,
                "poet_name": poem.poet_name,
                "poem_title": poem.poem_title,
                "source_language": poem.source_language,
                "content": poem.original_text,
                "metadata_json": poem.metadata_json,
                "created_at": poem.created_at.isoformat() if poem.created_at else None,
                "updated_at": poem.updated_at.isoformat() if poem.updated_at else None,
                "translation_count": 0,
                "ai_translation_count": 0,
                "human_translation_count": 0,
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to create poem: {e}")
            self.db.rollback()
            raise

    async def update_poem(
        self,
        poem_id: str,
        poet_name: Optional[str] = None,
        poem_title: Optional[str] = None,
        source_language: Optional[str] = None,
        content: Optional[str] = None,
        metadata_json: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing poem.

        Args:
            poem_id: Unique identifier for the poem
            poet_name: Updated poet name (optional)
            poem_title: Updated poem title (optional)
            source_language: Updated source language (optional)
            content: Updated poem content (optional)
            metadata_json: Updated metadata (optional)

        Returns:
            Updated poem data dictionary or None if not found

        Raises:
            ValueError: If updated fields are invalid
        """
        try:
            poem = self.repository_service.poems.get_by_id(poem_id)
            if not poem:
                return None

            # Update fields if provided
            if poet_name is not None:
                if not poet_name or not poet_name.strip():
                    raise ValueError("Poet name cannot be empty")
                poem.poet_name = poet_name.strip()

            if poem_title is not None:
                if not poem_title or not poem_title.strip():
                    raise ValueError("Poem title cannot be empty")
                poem.poem_title = poem_title.strip()

            if source_language is not None:
                if not source_language or not source_language.strip():
                    raise ValueError("Source language cannot be empty")
                poem.source_language = source_language.strip().lower()

            if content is not None:
                if not content or not content.strip():
                    raise ValueError("Poem content cannot be empty")
                if len(content.strip()) < 10:
                    raise ValueError("Poem content must be at least 10 characters")
                poem.original_text = content.strip()

            if metadata_json is not None:
                poem.metadata_json = metadata_json

            poem.updated_at = datetime.utcnow()

            # Save changes
            self.db.commit()
            self.db.refresh(poem)

            logger.info(f"Updated poem: {poem_id}")

            return {
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

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update poem {poem_id}: {e}")
            self.db.rollback()
            raise

    async def delete_poem(self, poem_id: str) -> bool:
        """
        Delete a poem and all its translations.

        Args:
            poem_id: Unique identifier for the poem

        Returns:
            True if poem was deleted, False if not found
        """
        try:
            poem = self.repository_service.poems.get_by_id(poem_id)
            if not poem:
                return False

            # Delete poem (cascade will delete translations, logs, and notes)
            self.db.delete(poem)
            self.db.commit()

            logger.info(f"Deleted poem: {poem_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete poem {poem_id}: {e}")
            self.db.rollback()
            raise

    async def get_poem_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about poems in the repository.

        Returns:
            Dictionary with poem statistics
        """
        try:
            total_poems = self.db.query(Poem).count()

            # Count by language
            languages = (
                self.db.query(
                    Poem.source_language, self.db.func.count(Poem.id).label("count")
                )
                .group_by(Poem.source_language)
                .all()
            )

            # Count by poet (top 10)
            poets = (
                self.db.query(
                    Poem.poet_name, self.db.func.count(Poem.id).label("count")
                )
                .group_by(Poem.poet_name)
                .order_by(desc(self.db.func.count(Poem.id)))
                .limit(10)
                .all()
            )

            return {
                "total_poems": total_poems,
                "languages": [
                    {"language": lang.source_language, "count": lang.count}
                    for lang in languages
                ],
                "top_poets": [
                    {"poet_name": poet.poet_name, "poem_count": poet.count}
                    for poet in poets
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get poem statistics: {e}")
            raise

    async def search_poems(
        self, query: str, skip: int = 0, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search poems by title, poet name, or content.

        Args:
            query: Search query string
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching poems
        """
        try:
            if not query or len(query.strip()) < 2:
                return []

            search_term = f"%{query.strip()}%"

            poems = (
                self.db.query(Poem)
                .filter(
                    (Poem.poet_name.ilike(search_term))
                    | (Poem.poem_title.ilike(search_term))
                    | (Poem.original_text.ilike(search_term))
                )
                .order_by(desc(Poem.created_at))
                .offset(skip)
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": poem.id,
                    "poet_name": poem.poet_name,
                    "poem_title": poem.poem_title,
                    "source_language": poem.source_language,
                    "content_preview": (
                        poem.original_text[:200] + "..."
                        if len(poem.original_text) > 200
                        else poem.original_text
                    ),
                    "created_at": (
                        poem.created_at.isoformat() if poem.created_at else None
                    ),
                    "translation_count": poem.translation_count,
                    "ai_translation_count": poem.ai_translation_count,
                    "human_translation_count": poem.human_translation_count,
                }
                for poem in poems
            ]

        except Exception as e:
            logger.error(f"Failed to search poems: {e}")
            raise
