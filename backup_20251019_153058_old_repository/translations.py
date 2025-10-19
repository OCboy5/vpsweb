"""
Translation Repository Implementation

This module provides the translation repository with comprehensive CRUD operations,
version management, and specialized queries for the VPSWeb repository system.

Features:
- CRUD operations for translations
- Version management
- Translation quality tracking
- Translator-specific queries
- Language pair analysis
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository, NotFoundError, ValidationError
from .models import Translation, Poem
from .schemas import TranslationCreate, TranslationUpdate, TranslatorType
from .exceptions import (
    DatabaseException, ResourceNotFoundException,
    ConflictException, ErrorCode
)
from ..utils.logger import get_structured_logger
from ..utils.language_mapper import validate_language_code


class TranslationRepository(BaseRepository[Translation, TranslationCreate, TranslationUpdate]):
    """
    Repository for translation operations with specialized functionality.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize translation repository.

        Args:
            session: Async database session
        """
        super().__init__(Translation, session)
        self.logger = get_structured_logger()

    async def create(self, obj_in: TranslationCreate, created_by: Optional[str] = None) -> Translation:
        """
        Create a new translation with validation.

        Args:
            obj_in: Translation creation data
            created_by: User who created the translation

        Returns:
            Created translation

        Raises:
            ValidationError: If validation fails
            DatabaseException: If database operation fails
        """
        # Validate language codes
        is_valid, error_msg = validate_language_code(obj_in.target_language)
        if not is_valid:
            raise ValidationError(f"Invalid target language code: {error_msg}")

        # Verify poem exists
        poem_stmt = select(Poem).where(Poem.id == obj_in.poem_id)
        poem_result = await self.session.execute(poem_stmt)
        poem = poem_result.scalar_one_or_none()

        if not poem:
            raise ResourceNotFoundException(
                f"Poem not found: {obj_in.poem_id}",
                resource_id=obj_in.poem_id
            )

        # Check for duplicate translation (same poem, language, version)
        existing = await self.get_by_poem_language_version(
            obj_in.poem_id, obj_in.target_language, obj_in.version
        )
        if existing:
            raise ConflictException(
                f"Translation version {obj_in.version} for poem {obj_in.poem_id} in {obj_in.target_language} already exists",
                ErrorCode.DUPLICATE_RESOURCE
            )

        # Check if translation is not the same as source language
        if poem.source_language == obj_in.target_language:
            raise ValidationError(
                f"Target language {obj_in.target_language} is the same as source language {poem.source_language}"
            )

        try:
            # Create translation with additional validation
            translation_data = obj_in.dict()

            # Add system fields
            translation_data['created_by'] = created_by
            translation_data['updated_by'] = created_by

            db_translation = self.model(**translation_data)
            self.session.add(db_translation)
            await self.session.commit()
            await self.session.refresh(db_translation)

            self.logger.info(
                "Translation created",
                translation_id=db_translation.id,
                poem_id=obj_in.poem_id,
                target_language=obj_in.target_language,
                version=obj_in.version,
                translator_type=obj_in.translator_type,
                created_by=created_by
            )

            return db_translation

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to create translation",
                error=str(e),
                poem_id=obj_in.poem_id,
                target_language=obj_in.target_language
            )
            raise DatabaseException(f"Failed to create translation: {str(e)}")

    async def get_by_poem_language_version(
        self,
        poem_id: str,
        target_language: str,
        version: int
    ) -> Optional[Translation]:
        """
        Get a translation by poem, language, and version.

        Args:
            poem_id: Poem ID
            target_language: Target language code
            version: Translation version

        Returns:
            Found translation or None
        """
        try:
            stmt = select(self.model).where(
                and_(
                    self.model.poem_id == poem_id,
                    self.model.target_language == target_language,
                    self.model.version == version
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            self.logger.error(
                "Failed to get translation by poem/language/version",
                error=str(e),
                poem_id=poem_id,
                target_language=target_language,
                version=version
            )
            raise DatabaseException(f"Failed to get translation: {str(e)}")

    async def get_by_poem(
        self,
        poem_id: str,
        target_language: Optional[str] = None,
        only_published: bool = True
    ) -> List[Translation]:
        """
        Get translations for a specific poem.

        Args:
            poem_id: Poem ID
            target_language: Optional language filter
            only_published: Whether to return only published translations

        Returns:
            List of translations
        """
        try:
            conditions = [self.model.poem_id == poem_id]

            if target_language:
                conditions.append(self.model.target_language == target_language)

            if only_published:
                conditions.append(self.model.is_published == True)

            stmt = select(self.model).where(and_(*conditions)).order_by(
                self.model.target_language,
                desc(self.model.version)
            )

            result = await self.session.execute(stmt)
            translations = result.scalars().all()

            return list(translations)

        except Exception as e:
            self.logger.error(
                "Failed to get translations by poem",
                error=str(e),
                poem_id=poem_id,
                target_language=target_language
            )
            raise DatabaseException(f"Failed to get translations: {str(e)}")

    async def get_latest_version(
        self,
        poem_id: str,
        target_language: str,
        only_published: bool = True
    ) -> Optional[Translation]:
        """
        Get the latest version of a translation.

        Args:
            poem_id: Poem ID
            target_language: Target language code
            only_published: Whether to return only published translations

        Returns:
            Latest translation or None
        """
        try:
            conditions = [
                self.model.poem_id == poem_id,
                self.model.target_language == target_language
            ]

            if only_published:
                conditions.append(self.model.is_published == True)

            stmt = select(self.model).where(
                and_(*conditions)
            ).order_by(desc(self.model.version)).limit(1)

            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            self.logger.error(
                "Failed to get latest translation version",
                error=str(e),
                poem_id=poem_id,
                target_language=target_language
            )
            raise DatabaseException(f"Failed to get latest translation: {str(e)}")

    async def get_by_language_pair(
        self,
        source_language: str,
        target_language: str,
        only_published: bool = True,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Translation], int]:
        """
        Get translations by language pair.

        Args:
            source_language: Source language code
            target_language: Target language code
            only_published: Whether to return only published translations
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (translations, total count)
        """
        try:
            # Join with poems to filter by source language
            stmt = select(self.model).join(Poem).where(
                and_(
                    Poem.source_language == source_language,
                    self.model.target_language == target_language
                )
            )

            # Apply published filter
            if only_published:
                stmt = stmt.where(self.model.is_published == True)

            # Count query
            count_stmt = select(func.count()).select_from(self.model).join(Poem).where(
                and_(
                    Poem.source_language == source_language,
                    self.model.target_language == target_language
                )
            )

            if only_published:
                count_stmt = count_stmt.where(self.model.is_published == True)

            # Apply ordering and pagination
            stmt = stmt.order_by(desc(self.model.created_at)).offset(offset).limit(limit)

            # Execute queries
            result = await self.session.execute(stmt)
            translations = result.scalars().all()

            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar()

            return list(translations), total

        except Exception as e:
            self.logger.error(
                "Failed to get translations by language pair",
                error=str(e),
                source_language=source_language,
                target_language=target_language
            )
            raise DatabaseException(f"Failed to get translations by language pair: {str(e)}")

    async def get_by_translator_type(
        self,
        translator_type: TranslatorType,
        only_published: bool = True,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Translation], int]:
        """
        Get translations by translator type.

        Args:
            translator_type: Type of translator
            only_published: Whether to return only published translations
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (translations, total count)
        """
        try:
            conditions = [self.model.translator_type == translator_type]

            if only_published:
                conditions.append(self.model.is_published == True)

            # Query and count
            stmt = select(self.model).where(and_(*conditions)).order_by(
                desc(self.model.created_at)
            ).offset(offset).limit(limit)

            count_stmt = select(func.count()).select_from(self.model).where(and_(*conditions))

            # Execute queries
            result = await self.session.execute(stmt)
            translations = result.scalars().all()

            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar()

            return list(translations), total

        except Exception as e:
            self.logger.error(
                "Failed to get translations by translator type",
                error=str(e),
                translator_type=translator_type
            )
            raise DatabaseException(f"Failed to get translations by translator type: {str(e)}")

    async def search(
        self,
        query: Optional[str] = None,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None,
        translator_type: Optional[TranslatorType] = None,
        is_published: Optional[bool] = None,
        min_quality_score: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[Translation], int]:
        """
        Search translations with multiple filters.

        Args:
            query: Search query for translated text or notes
            source_language: Filter by source language (via poem join)
            target_language: Filter by target language
            translator_type: Filter by translator type
            is_published: Filter by published status
            min_quality_score: Filter by minimum quality score
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            order_desc: Whether to order descending

        Returns:
            Tuple of (translations, total count)
        """
        try:
            # Build base query with poem join
            stmt = select(self.model).join(Poem)
            count_stmt = select(func.count()).select_from(self.model).join(Poem)

            conditions = []

            # Apply filters
            if query:
                search_condition = or_(
                    self.model.translated_text.ilike(f"%{query}%"),
                    self.model.translator_notes.ilike(f"%{query}%")
                )
                conditions.append(search_condition)

            if source_language:
                conditions.append(Poem.source_language == source_language)

            if target_language:
                conditions.append(self.model.target_language == target_language)

            if translator_type:
                conditions.append(self.model.translator_type == translator_type)

            if is_published is not None:
                conditions.append(self.model.is_published == is_published)

            if min_quality_score is not None:
                conditions.append(
                    func.cast(self.model.quality_score, float) >= min_quality_score
                )

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
            translations = result.scalars().all()

            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar()

            return list(translations), total

        except Exception as e:
            self.logger.error(
                "Failed to search translations",
                error=str(e),
                query=query,
                filters={
                    "source_language": source_language,
                    "target_language": target_language,
                    "translator_type": translator_type,
                    "is_published": is_published
                }
            )
            raise DatabaseException(f"Failed to search translations: {str(e)}")

    async def get_language_pair_statistics(self) -> List[Dict[str, Any]]:
        """
        Get statistics for language pairs.

        Returns:
            List of language pair statistics
        """
        try:
            stmt = select(
                Poem.source_language.label('source_language'),
                self.model.target_language,
                func.count().label('translation_count'),
                func.count(func.distinct(self.model.poem_id)).label('unique_poems')
            ).join(Poem).where(
                self.model.is_published == True
            ).group_by(
                Poem.source_language,
                self.model.target_language
            ).order_by(desc('translation_count'))

            result = await self.session.execute(stmt)
            rows = result.all()

            return [
                {
                    "source_language": row.source_language,
                    "target_language": row.target_language,
                    "translation_count": row.translation_count,
                    "unique_poems": row.unique_poems
                }
                for row in rows
            ]

        except Exception as e:
            self.logger.error(
                "Failed to get language pair statistics",
                error=str(e)
            )
            raise DatabaseException(f"Failed to get language pair statistics: {str(e)}")

    async def get_translator_statistics(self) -> List[Dict[str, Any]]:
        """
        Get statistics by translator type.

        Returns:
            List of translator type statistics
        """
        try:
            stmt = select(
                self.model.translator_type,
                func.count().label('translation_count'),
                func.count(func.distinct(self.model.poem_id)).label('unique_poems'),
                func.avg(func.cast(self.model.quality_score, float)).label('avg_quality_score')
            ).where(
                self.model.is_published == True
            ).group_by(self.model.translator_type).order_by(desc('translation_count'))

            result = await self.session.execute(stmt)
            rows = result.all()

            return [
                {
                    "translator_type": row.translator_type,
                    "translation_count": row.translation_count,
                    "unique_poems": row.unique_poems,
                    "avg_quality_score": float(row.avg_quality_score) if row.avg_quality_score else None
                }
                for row in rows
            ]

        except Exception as e:
            self.logger.error(
                "Failed to get translator statistics",
                error=str(e)
            )
            raise DatabaseException(f"Failed to get translator statistics: {str(e)}")

    async def get_recent_translations(
        self,
        days: int = 7,
        only_published: bool = True,
        limit: int = 20
    ) -> List[Translation]:
        """
        Get recently created translations.

        Args:
            days: Number of days to look back
            only_published: Whether to return only published translations
            limit: Maximum number of results

        Returns:
            List of recent translations
        """
        try:
            # Calculate date threshold
            threshold_date = datetime.now(timezone.utc) - datetime.timedelta(days=days)

            # Build query
            conditions = [self.model.created_at >= threshold_date]

            if only_published:
                conditions.append(self.model.is_published == True)

            stmt = select(self.model).where(
                and_(*conditions)
            ).order_by(desc(self.model.created_at)).limit(limit)

            result = await self.session.execute(stmt)
            translations = result.scalars().all()

            return list(translations)

        except Exception as e:
            self.logger.error(
                "Failed to get recent translations",
                error=str(e),
                days=days
            )
            raise DatabaseException(f"Failed to get recent translations: {str(e)}")

    async def bulk_publish(
        self,
        translation_ids: List[str],
        is_published: bool = True,
        updated_by: Optional[str] = None
    ) -> int:
        """
        Bulk update the published status of multiple translations.

        Args:
            translation_ids: List of translation IDs
            is_published: New published status
            updated_by: User who made the update

        Returns:
            Number of updated translations
        """
        try:
            stmt = (
                update(self.model)
                .where(self.model.id.in_(translation_ids))
                .values(
                    is_published=is_published,
                    updated_by=updated_by,
                    updated_at=datetime.now(timezone.utc)
                )
            )

            result = await self.session.execute(stmt)
            await self.session.commit()

            self.logger.info(
                "Bulk updated translation publish status",
                translation_count=result.rowcount,
                is_published=is_published,
                updated_by=updated_by
            )

            return result.rowcount

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to bulk update translation publish status",
                error=str(e),
                translation_count=len(translation_ids)
            )
            raise DatabaseException(f"Failed to bulk update translation publish status: {str(e)}")

    def __repr__(self) -> str:
        return "<TranslationRepository>"