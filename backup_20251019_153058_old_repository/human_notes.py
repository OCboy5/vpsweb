"""
Human Note Repository Implementation

This module provides the human note repository with comprehensive CRUD operations,
annotation management, and specialized queries for human-generated notes.

Features:
- CRUD operations for human notes
- Note type management
- Public/private note handling
- Author tracking
- Content analysis
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository, NotFoundError, ValidationError
from .models import HumanNote, Poem, Translation
from .schemas import HumanNoteCreate, HumanNoteUpdate
from .exceptions import (
    DatabaseException, ResourceNotFoundException,
    ErrorCode
)
from ..utils.logger import get_structured_logger


class HumanNoteRepository(BaseRepository[HumanNote, HumanNoteCreate, HumanNoteUpdate]):
    """
    Repository for human note operations with specialized annotation functionality.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize human note repository.

        Args:
            session: Async database session
        """
        super().__init__(HumanNote, session)
        self.logger = get_structured_logger()
        self.valid_note_types = [
            'editorial', 'cultural', 'technical', 'historical', 'linguistic', 'general'
        ]

    async def create(self, obj_in: HumanNoteCreate, created_by: Optional[str] = None) -> HumanNote:
        """
        Create a new human note.

        Args:
            obj_in: Human note creation data
            created_by: User who created the note

        Returns:
            Created human note

        Raises:
            ValidationError: If validation fails
            DatabaseException: If database operation fails
        """
        # Validate note type
        if obj_in.note_type.lower() not in self.valid_note_types:
            raise ValidationError(
                f"Invalid note type: {obj_in.note_type}. "
                f"Valid types are: {', '.join(self.valid_note_types)}"
            )

        # Verify poem exists
        poem_stmt = select(Poem).where(Poem.id == obj_in.poem_id)
        poem_result = await self.session.execute(poem_stmt)
        poem = poem_result.scalar_one_or_none()

        if not poem:
            raise ResourceNotFoundException(
                f"Poem not found: {obj_in.poem_id}",
                resource_id=obj_in.poem_id
            )

        # Verify translation exists if provided
        if obj_in.translation_id:
            translation_stmt = select(Translation).where(Translation.id == obj_in.translation_id)
            translation_result = await self.session.execute(translation_stmt)
            translation = translation_result.scalar_one_or_none()

            if not translation:
                raise ResourceNotFoundException(
                    f"Translation not found: {obj_in.translation_id}",
                    resource_id=obj_in.translation_id
                )

            # Verify translation belongs to the specified poem
            if translation.poem_id != obj_in.poem_id:
                raise ValidationError(
                    f"Translation {obj_in.translation_id} does not belong to poem {obj_in.poem_id}"
                )

        try:
            # Create human note with additional validation
            note_data = obj_in.dict()

            # Add system fields
            note_data['created_by'] = created_by
            note_data['updated_by'] = created_by

            db_note = self.model(**note_data)
            self.session.add(db_note)
            await self.session.commit()
            await self.session.refresh(db_note)

            self.logger.info(
                "Human note created",
                note_id=db_note.id,
                poem_id=obj_in.poem_id,
                translation_id=obj_in.translation_id,
                note_type=obj_in.note_type,
                author_name=obj_in.author_name,
                is_public=obj_in.is_public,
                created_by=created_by
            )

            return db_note

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to create human note",
                error=str(e),
                poem_id=obj_in.poem_id,
                note_type=obj_in.note_type
            )
            raise DatabaseException(f"Failed to create human note: {str(e)}")

    async def get_by_poem(
        self,
        poem_id: str,
        note_type: Optional[str] = None,
        is_public: Optional[bool] = None,
        author_name: Optional[str] = None
    ) -> List[HumanNote]:
        """
        Get human notes for a specific poem.

        Args:
            poem_id: Poem ID
            note_type: Optional note type filter
            is_public: Optional public status filter
            author_name: Optional author name filter

        Returns:
            List of human notes
        """
        try:
            conditions = [self.model.poem_id == poem_id]

            if note_type:
                conditions.append(self.model.note_type == note_type.lower())

            if is_public is not None:
                conditions.append(self.model.is_public == is_public)

            if author_name:
                conditions.append(self.model.author_name.ilike(f"%{author_name}%"))

            stmt = select(self.model).where(and_(*conditions)).order_by(
                desc(self.model.created_at)
            )

            result = await self.session.execute(stmt)
            notes = result.scalars().all()

            return list(notes)

        except Exception as e:
            self.logger.error(
                "Failed to get human notes by poem",
                error=str(e),
                poem_id=poem_id
            )
            raise DatabaseException(f"Failed to get human notes: {str(e)}")

    async def get_by_translation(
        self,
        translation_id: str,
        note_type: Optional[str] = None,
        is_public: Optional[bool] = None
    ) -> List[HumanNote]:
        """
        Get human notes for a specific translation.

        Args:
            translation_id: Translation ID
            note_type: Optional note type filter
            is_public: Optional public status filter

        Returns:
            List of human notes
        """
        try:
            conditions = [self.model.translation_id == translation_id]

            if note_type:
                conditions.append(self.model.note_type == note_type.lower())

            if is_public is not None:
                conditions.append(self.model.is_public == is_public)

            stmt = select(self.model).where(and_(*conditions)).order_by(
                desc(self.model.created_at)
            )

            result = await self.session.execute(stmt)
            notes = result.scalars().all()

            return list(notes)

        except Exception as e:
            self.logger.error(
                "Failed to get human notes by translation",
                error=str(e),
                translation_id=translation_id
            )
            raise DatabaseException(f"Failed to get human notes: {str(e)}")

    async def get_by_author(
        self,
        author_name: str,
        is_public: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[HumanNote], int]:
        """
        Get human notes by author.

        Args:
            author_name: Author name
            is_public: Optional public status filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (notes, total count)
        """
        try:
            conditions = [self.model.author_name.ilike(f"%{author_name}%")]

            if is_public is not None:
                conditions.append(self.model.is_public == is_public)

            # Query and count
            stmt = select(self.model).where(and_(*conditions)).order_by(
                desc(self.model.created_at)
            ).offset(offset).limit(limit)

            count_stmt = select(func.count()).select_from(self.model).where(and_(*conditions))

            # Execute queries
            result = await self.session.execute(stmt)
            notes = result.scalars().all()

            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar()

            return list(notes), total

        except Exception as e:
            self.logger.error(
                "Failed to get human notes by author",
                error=str(e),
                author_name=author_name
            )
            raise DatabaseException(f"Failed to get human notes: {str(e)}")

    async def get_by_note_type(
        self,
        note_type: str,
        is_public: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[HumanNote], int]:
        """
        Get human notes by note type.

        Args:
            note_type: Note type
            is_public: Optional public status filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (notes, total count)
        """
        try:
            if note_type.lower() not in self.valid_note_types:
                raise ValidationError(
                    f"Invalid note type: {note_type}. "
                    f"Valid types are: {', '.join(self.valid_note_types)}"
                )

            conditions = [self.model.note_type == note_type.lower()]

            if is_public is not None:
                conditions.append(self.model.is_public == is_public)

            # Query and count
            stmt = select(self.model).where(and_(*conditions)).order_by(
                desc(self.model.created_at)
            ).offset(offset).limit(limit)

            count_stmt = select(func.count()).select_from(self.model).where(and_(*conditions))

            # Execute queries
            result = await self.session.execute(stmt)
            notes = result.scalars().all()

            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar()

            return list(notes), total

        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(
                "Failed to get human notes by type",
                error=str(e),
                note_type=note_type
            )
            raise DatabaseException(f"Failed to get human notes: {str(e)}")

    async def get_public_notes(
        self,
        limit: int = 20,
        offset: int = 0,
        note_type: Optional[str] = None
    ) -> Tuple[List[HumanNote], int]:
        """
        Get public human notes.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            note_type: Optional note type filter

        Returns:
            Tuple of (notes, total count)
        """
        try:
            conditions = [self.model.is_public == True]

            if note_type:
                if note_type.lower() not in self.valid_note_types:
                    raise ValidationError(
                        f"Invalid note type: {note_type}. "
                        f"Valid types are: {', '.join(self.valid_note_types)}"
                    )
                conditions.append(self.model.note_type == note_type.lower())

            # Query and count
            stmt = select(self.model).where(and_(*conditions)).order_by(
                desc(self.model.created_at)
            ).offset(offset).limit(limit)

            count_stmt = select(func.count()).select_from(self.model).where(and_(*conditions))

            # Execute queries
            result = await self.session.execute(stmt)
            notes = result.scalars().all()

            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar()

            return list(notes), total

        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(
                "Failed to get public notes",
                error=str(e),
                note_type=note_type
            )
            raise DatabaseException(f"Failed to get public notes: {str(e)}")

    async def search(
        self,
        query: Optional[str] = None,
        note_type: Optional[str] = None,
        author_name: Optional[str] = None,
        is_public: Optional[bool] = None,
        poem_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[HumanNote], int]:
        """
        Search human notes with multiple filters.

        Args:
            query: Search query for title and content
            note_type: Filter by note type
            author_name: Filter by author name
            is_public: Filter by public status
            poem_id: Filter by poem ID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (notes, total count)
        """
        try:
            conditions = []

            # Apply filters
            if query:
                search_condition = or_(
                    self.model.title.ilike(f"%{query}%"),
                    self.model.content.ilike(f"%{query}%")
                )
                conditions.append(search_condition)

            if note_type:
                if note_type.lower() not in self.valid_note_types:
                    raise ValidationError(
                        f"Invalid note type: {note_type}. "
                        f"Valid types are: {', '.join(self.valid_note_types)}"
                    )
                conditions.append(self.model.note_type == note_type.lower())

            if author_name:
                conditions.append(self.model.author_name.ilike(f"%{author_name}%"))

            if is_public is not None:
                conditions.append(self.model.is_public == is_public)

            if poem_id:
                conditions.append(self.model.poem_id == poem_id)

            # Query and count
            stmt = select(self.model).where(and_(*conditions) if conditions else True).order_by(
                desc(self.model.created_at)
            ).offset(offset).limit(limit)

            count_stmt = select(func.count()).select_from(self.model).where(
                and_(*conditions) if conditions else True
            )

            # Execute queries
            result = await self.session.execute(stmt)
            notes = result.scalars().all()

            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar()

            return list(notes), total

        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(
                "Failed to search human notes",
                error=str(e),
                query=query,
                filters={
                    "note_type": note_type,
                    "author_name": author_name,
                    "is_public": is_public,
                    "poem_id": poem_id
                }
            )
            raise DatabaseException(f"Failed to search human notes: {str(e)}")

    async def get_note_type_statistics(self) -> List[Dict[str, Any]]:
        """
        Get statistics by note type.

        Returns:
            List of note type statistics
        """
        try:
            stmt = select(
                self.model.note_type,
                func.count().label('total_notes'),
                func.count(func.nullif(self.model.is_public == False, True)).label('public_notes'),
                func.count(func.distinct(self.model.author_name)).label('unique_authors')
            ).group_by(self.model.note_type).order_by(desc('total_notes'))

            result = await self.session.execute(stmt)
            rows = result.all()

            return [
                {
                    'note_type': row.note_type,
                    'total_notes': row.total_notes,
                    'public_notes': row.public_notes or 0,
                    'private_notes': row.total_notes - (row.public_notes or 0),
                    'unique_authors': row.unique_authors
                }
                for row in rows
            ]

        except Exception as e:
            self.logger.error(
                "Failed to get note type statistics",
                error=str(e)
            )
            raise DatabaseException(f"Failed to get note type statistics: {str(e)}")

    async def get_author_statistics(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get statistics by author.

        Args:
            limit: Maximum number of authors to return

        Returns:
            List of author statistics
        """
        try:
            stmt = select(
                self.model.author_name,
                func.count().label('total_notes'),
                func.count(func.nullif(self.model.is_public == False, True)).label('public_notes'),
                func.count(func.distinct(self.model.note_type)).label('note_types_used')
            ).group_by(self.model.author_name).order_by(desc('total_notes')).limit(limit)

            result = await self.session.execute(stmt)
            rows = result.all()

            return [
                {
                    'author_name': row.author_name,
                    'total_notes': row.total_notes,
                    'public_notes': row.public_notes or 0,
                    'private_notes': row.total_notes - (row.public_notes or 0),
                    'note_types_used': row.note_types_used
                }
                for row in rows
            ]

        except Exception as e:
            self.logger.error(
                "Failed to get author statistics",
                error=str(e)
            )
            raise DatabaseException(f"Failed to get author statistics: {str(e)}")

    async def get_recent_notes(
        self,
        days: int = 7,
        is_public: Optional[bool] = None,
        limit: int = 20
    ) -> List[HumanNote]:
        """
        Get recently created human notes.

        Args:
            days: Number of days to look back
            is_public: Optional public status filter
            limit: Maximum number of results

        Returns:
            List of recent notes
        """
        try:
            # Calculate date threshold
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Build query
            conditions = [self.model.created_at >= threshold_date]

            if is_public is not None:
                conditions.append(self.model.is_public == is_public)

            stmt = select(self.model).where(
                and_(*conditions)
            ).order_by(desc(self.model.created_at)).limit(limit)

            result = await self.session.execute(stmt)
            notes = result.scalars().all()

            return list(notes)

        except Exception as e:
            self.logger.error(
                "Failed to get recent notes",
                error=str(e),
                days=days
            )
            raise DatabaseException(f"Failed to get recent notes: {str(e)}")

    async def bulk_update_visibility(
        self,
        note_ids: List[str],
        is_public: bool,
        updated_by: Optional[str] = None
    ) -> int:
        """
        Bulk update the public visibility of multiple notes.

        Args:
            note_ids: List of note IDs
            is_public: New public visibility status
            updated_by: User who made the update

        Returns:
            Number of updated notes
        """
        try:
            stmt = (
                update(self.model)
                .where(self.model.id.in_(note_ids))
                .values(
                    is_public=is_public,
                    updated_by=updated_by,
                    updated_at=datetime.now(timezone.utc)
                )
            )

            result = await self.session.execute(stmt)
            await self.session.commit()

            self.logger.info(
                "Bulk updated note visibility",
                note_count=result.rowcount,
                is_public=is_public,
                updated_by=updated_by
            )

            return result.rowcount

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to bulk update note visibility",
                error=str(e),
                note_count=len(note_ids)
            )
            raise DatabaseException(f"Failed to bulk update note visibility: {str(e)}")

    def __repr__(self) -> str:
        return "<HumanNoteRepository>"