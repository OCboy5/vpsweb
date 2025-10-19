"""
Poem Repository Implementation

This module provides the poem repository with comprehensive CRUD operations,
search functionality, and specialized queries for the VPSWeb repository system.

Features:
- CRUD operations for poems
- Advanced search and filtering
- Tag management
- Language-specific queries
- Poetry-specific validation
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository, NotFoundError, ValidationError
from .models import Poem
from .schemas import PoemCreate, PoemUpdate
from .exceptions import (
    DatabaseException, ResourceNotFoundException,
    ConflictException, ErrorCode
)
from ..utils.logger import get_structured_logger
from ..utils.language_mapper import validate_language_code

try:
    import ulid
    def generate_ulid():
        return str(ulid.ULID())
except ImportError:
    # Fallback if ulid library not available
    import uuid
    def generate_ulid():
        return str(uuid.uuid4())


class PoemRepository(BaseRepository[Poem, PoemCreate, PoemUpdate]):
    """
    Repository for poem operations with specialized poetry functionality.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize poem repository.

        Args:
            session: Async database session
        """
        super().__init__(Poem, session)
        self.logger = get_structured_logger()

    async def create(self, obj_in: PoemCreate, created_by: Optional[str] = None) -> Poem:
        """
        Create a new poem with validation.

        Args:
            obj_in: Poem creation data
            created_by: User who created the poem

        Returns:
            Created poem

        Raises:
            ValidationError: If validation fails
            DatabaseException: If database operation fails
        """
        # Validate language code
        is_valid, error_msg = validate_language_code(obj_in.source_language)
        if not is_valid:
            raise ValidationError(f"Invalid language code: {error_msg}")

        # Check for duplicate poem (same title and poet)
        existing = await self.get_by_title_and_poet(obj_in.poem_title, obj_in.poet_name)
        if existing:
            raise ConflictException(
                f"Poem '{obj_in.poem_title}' by {obj_in.poet_name} already exists",
                ErrorCode.DUPLICATE_RESOURCE
            )

        try:
            # Create poem with additional validation
            poem_data = obj_in.model_dump()

            # Generate ULID for new poem
            poem_data['id'] = generate_ulid()

            # Note: created_by and updated_by are not currently in the model
            # These would need to be added to the model schema if needed
            # poem_data['created_by'] = created_by
            # poem_data['updated_by'] = created_by

            db_poem = self.model(**poem_data)
            self.session.add(db_poem)
            await self.session.commit()
            await self.session.refresh(db_poem)

            self.logger.info(
                "Poem created",
                poem_id=db_poem.id,
                title=db_poem.poem_title,
                poet=db_poem.poet_name,
                language=db_poem.source_language,
                created_by=created_by
            )

            return db_poem

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to create poem",
                error=str(e),
                title=obj_in.poem_title,
                poet=obj_in.poet_name
            )
            raise DatabaseException(f"Failed to create poem: {str(e)}")

    async def get_by_title_and_poet(self, title: str, poet: str) -> Optional[Poem]:
        """
        Get a poem by title and poet name.

        Args:
            title: Poem title
            poet: Poet name

        Returns:
            Found poem or None
        """
        try:
            stmt = select(self.model).where(
                and_(
                    self.model.poem_title == title,
                    self.model.poet_name == poet,
                    self.model.is_active == True
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            self.logger.error(
                "Failed to get poem by title and poet",
                error=str(e),
                title=title,
                poet=poet
            )
            raise DatabaseException(f"Failed to get poem: {str(e)}")

    async def search(
        self,
        query: Optional[str] = None,
        language: Optional[str] = None,
        poet: Optional[str] = None,
        genre: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_active: bool = True,
        limit: int = 20,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[Poem], int]:
        """
        Search poems with multiple filters.

        Args:
            query: Search query for title/poet/content
            language: Filter by source language
            poet: Filter by poet name
            genre: Filter by genre
            tags: Filter by tags (must contain all specified tags)
            is_active: Filter by active status
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            order_desc: Whether to order descending

        Returns:
            Tuple of (poems, total count)
        """
        try:
            # Build base query
            stmt = select(self.model).where(self.model.is_active == is_active)

            # Count query
            count_stmt = select(func.count()).select_from(self.model).where(
                self.model.is_active == is_active
            )

            # Apply filters
            conditions = []

            if query:
                search_condition = or_(
                    self.model.poem_title.ilike(f"%{query}%"),
                    self.model.poet_name.ilike(f"%{query}%"),
                    self.model.original_text.ilike(f"%{query}%")
                )
                conditions.append(search_condition)

            if language:
                conditions.append(self.model.source_language == language)

            if poet:
                conditions.append(self.model.poet_name.ilike(f"%{poet}%"))

            if genre:
                conditions.append(self.model.genre.ilike(f"%{genre}%"))

            if tags:
                for tag in tags:
                    conditions.append(self.model.tags.ilike(f"%{tag}%"))

            # Apply conditions to both queries
            if conditions:
                stmt = stmt.where(and_(*conditions))
                count_stmt = count_stmt.where(and_(*conditions))

            # Apply ordering
            order_field = getattr(self.model, order_by, None)
            if order_field:
                if order_desc:
                    stmt = stmt.order_by(desc(order_field))
                else:
                    stmt = stmt.order_by(asc(order_field))

            # Apply pagination
            stmt = stmt.offset(offset).limit(limit)

            # Execute queries
            result = await self.session.execute(stmt)
            poems = result.scalars().all()

            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar()

            self.logger.debug(
                "Poem search completed",
                query=query,
                language=language,
                poet=poet,
                results_count=len(poems),
                total_count=total
            )

            return list(poems), total

        except Exception as e:
            self.logger.error(
                "Failed to search poems",
                error=str(e),
                query=query,
                filters={
                    "language": language,
                    "poet": poet,
                    "genre": genre,
                    "tags": tags
                }
            )
            raise DatabaseException(f"Failed to search poems: {str(e)}")

    async def get_by_language(self, language: str, limit: int = 20, offset: int = 0) -> Tuple[List[Poem], int]:
        """
        Get poems by source language.

        Args:
            language: Language code
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (poems, total count)
        """
        # Validate language code
        is_valid, error_msg = validate_language_code(language)
        if not is_valid:
            raise ValidationError(f"Invalid language code: {error_msg}")

        try:
            # Build query
            stmt = select(self.model).where(
                and_(
                    self.model.source_language == language,
                    self.model.is_active == True
                )
            ).order_by(desc(self.model.created_at))

            # Count query
            count_stmt = select(func.count()).select_from(self.model).where(
                and_(
                    self.model.source_language == language,
                    self.model.is_active == True
                )
            )

            # Apply pagination
            stmt = stmt.offset(offset).limit(limit)

            # Execute queries
            result = await self.session.execute(stmt)
            poems = result.scalars().all()

            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar()

            return list(poems), total

        except Exception as e:
            self.logger.error(
                "Failed to get poems by language",
                error=str(e),
                language=language
            )
            raise DatabaseException(f"Failed to get poems by language: {str(e)}")

    async def get_by_poet(self, poet_name: str, limit: int = 20, offset: int = 0) -> Tuple[List[Poem], int]:
        """
        Get poems by poet name.

        Args:
            poet_name: Poet name
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (poems, total count)
        """
        try:
            # Build query
            stmt = select(self.model).where(
                and_(
                    self.model.poet_name.ilike(f"%{poet_name}%"),
                    self.model.is_active == True
                )
            ).order_by(desc(self.model.created_at))

            # Count query
            count_stmt = select(func.count()).select_from(self.model).where(
                and_(
                    self.model.poet_name.ilike(f"%{poet_name}%"),
                    self.model.is_active == True
                )
            )

            # Apply pagination
            stmt = stmt.offset(offset).limit(limit)

            # Execute queries
            result = await self.session.execute(stmt)
            poems = result.scalars().all()

            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar()

            return list(poems), total

        except Exception as e:
            self.logger.error(
                "Failed to get poems by poet",
                error=str(e),
                poet_name=poet_name
            )
            raise DatabaseException(f"Failed to get poems by poet: {str(e)}")

    async def get_popular_tags(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get popular tags with usage counts.

        Args:
            limit: Maximum number of tags to return

        Returns:
            List of tag dictionaries with name and count
        """
        try:
            # Query to extract and count tags
            stmt = select(
                func.unnest(func.string_to_array(self.model.tags, ',')).label('tag'),
                func.count().label('count')
            ).where(
                and_(
                    self.model.tags.isnot(None),
                    self.model.tags != '',
                    self.model.is_active == True
                )
            ).group_by('tag').order_by(desc('count')).limit(limit)

            result = await self.session.execute(stmt)
            rows = result.all()

            tags = [
                {"tag": row.tag.strip(), "count": row.count}
                for row in rows
                if row.tag and row.tag.strip()
            ]

            return tags

        except Exception as e:
            self.logger.error(
                "Failed to get popular tags",
                error=str(e)
            )
            raise DatabaseException(f"Failed to get popular tags: {str(e)}")

    async def get_language_distribution(self) -> List[Dict[str, Any]]:
        """
        Get distribution of poems by source language.

        Returns:
            List of language dictionaries with code and count
        """
        try:
            stmt = select(
                self.model.source_language,
                func.count().label('count')
            ).where(
                self.model.is_active == True
            ).group_by(self.model.source_language).order_by(desc('count'))

            result = await self.session.execute(stmt)
            rows = result.all()

            distribution = [
                {"language": row.source_language, "count": row.count}
                for row in rows
            ]

            return distribution

        except Exception as e:
            self.logger.error(
                "Failed to get language distribution",
                error=str(e)
            )
            raise DatabaseException(f"Failed to get language distribution: {str(e)}")

    async def update_translation_count(self, poem_id: str) -> None:
        """
        Update the translation count for a poem (denormalized field).

        Args:
            poem_id: Poem ID
        """
        try:
            # This would require joining with translations table
            # For now, this is a placeholder for future implementation
            pass

        except Exception as e:
            self.logger.error(
                "Failed to update translation count",
                error=str(e),
                poem_id=poem_id
            )
            raise DatabaseException(f"Failed to update translation count: {str(e)}")

    async def get_recent_poems(
        self,
        days: int = 7,
        language: Optional[str] = None,
        limit: int = 20
    ) -> List[Poem]:
        """
        Get recently created poems.

        Args:
            days: Number of days to look back
            language: Optional language filter
            limit: Maximum number of results

        Returns:
            List of recent poems
        """
        try:
            # Calculate date threshold
            threshold_date = datetime.now(timezone.utc) - datetime.timedelta(days=days)

            # Build query
            stmt = select(self.model).where(
                and_(
                    self.model.created_at >= threshold_date,
                    self.model.is_active == True
                )
            )

            # Apply language filter if specified
            if language:
                stmt = stmt.where(self.model.source_language == language)

            # Order by creation date and limit
            stmt = stmt.order_by(desc(self.model.created_at)).limit(limit)

            result = await self.session.execute(stmt)
            poems = result.scalars().all()

            return list(poems)

        except Exception as e:
            self.logger.error(
                "Failed to get recent poems",
                error=str(e),
                days=days,
                language=language
            )
            raise DatabaseException(f"Failed to get recent poems: {str(e)}")

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get poem statistics.

        Returns:
            Dictionary with various statistics
        """
        try:
            # Total poems
            total_stmt = select(func.count()).select_from(self.model).where(
                self.model.is_active == True
            )
            total_result = await self.session.execute(total_stmt)
            total_poems = total_result.scalar()

            # Poems this month
            this_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_stmt = select(func.count()).select_from(self.model).where(
                and_(
                    self.model.created_at >= this_month,
                    self.model.is_active == True
                )
            )
            month_result = await self.session.execute(month_stmt)
            month_poems = month_result.scalar()

            # Unique languages
            language_stmt = select(func.count(func.distinct(self.model.source_language))).select_from(self.model).where(
                self.model.is_active == True
            )
            language_result = await self.session.execute(language_stmt)
            unique_languages = language_result.scalar()

            # Unique poets
            poet_stmt = select(func.count(func.distinct(self.model.poet_name))).select_from(self.model).where(
                self.model.is_active == True
            )
            poet_result = await self.session.execute(poet_stmt)
            unique_poets = poet_result.scalar()

            return {
                "total_poems": total_poems,
                "poems_this_month": month_poems,
                "unique_languages": unique_languages,
                "unique_poets": unique_poets,
                "language_distribution": await self.get_language_distribution(),
                "popular_tags": await self.get_popular_tags(10)
            }

        except Exception as e:
            self.logger.error(
                "Failed to get poem statistics",
                error=str(e)
            )
            raise DatabaseException(f"Failed to get poem statistics: {str(e)}")

    async def bulk_update_status(
        self,
        poem_ids: List[str],
        is_active: bool,
        updated_by: Optional[str] = None
    ) -> int:
        """
        Bulk update the active status of multiple poems.

        Args:
            poem_ids: List of poem IDs
            is_active: New active status
            updated_by: User who made the update

        Returns:
            Number of updated poems
        """
        try:
            stmt = (
                update(self.model)
                .where(self.model.id.in_(poem_ids))
                .values(
                    is_active=is_active,
                    updated_by=updated_by,
                    updated_at=datetime.now(timezone.utc)
                )
            )

            result = await self.session.execute(stmt)
            await self.session.commit()

            self.logger.info(
                "Bulk updated poem status",
                poem_count=result.rowcount,
                is_active=is_active,
                updated_by=updated_by
            )

            return result.rowcount

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to bulk update poem status",
                error=str(e),
                poem_count=len(poem_ids)
            )
            raise DatabaseException(f"Failed to bulk update poem status: {str(e)}")

    def __repr__(self) -> str:
        return "<PoemRepository>"