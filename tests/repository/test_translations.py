"""
Translation Repository Tests

This module contains tests for the translation repository implementation,
covering CRUD operations, version management, and specialized queries.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from vpsweb.repository.translations import TranslationRepository
from vpsweb.repository.schemas import TranslationCreate, TranslationUpdate, TranslatorType, AiLogStatus
from vpsweb.repository.exceptions import (
    ResourceNotFoundException,
    ConflictException,
    ValidationError,
    DatabaseException
)
from vpsweb.repository.models import Translation, Poem


class TestTranslationRepository:
    """Test cases for TranslationRepository."""

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_create_translation_success(self, db_session: AsyncSession, sample_poem: Poem, sample_translation_data):
        """Test successful translation creation."""
        repo = TranslationRepository(db_session)

        translation_data = sample_translation_data.copy()
        translation_data["poem_id"] = sample_poem.id

        translation = await repo.create(TranslationCreate(**translation_data))

        assert translation is not None
        assert translation.poem_id == sample_poem.id
        assert translation.target_language == sample_translation_data["target_language"]
        assert translation.version == sample_translation_data["version"]
        assert translation.translated_text == sample_translation_data["translated_text"]
        assert translation.translator_type == sample_translation_data["translator_type"]
        assert translation.is_published == sample_translation_data["is_published"]

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_create_non_existent_poem_fails(self, db_session: AsyncSession, sample_translation_data):
        """Test creating translation for non-existent poem fails."""
        repo = TranslationRepository(db_session)

        translation_data = sample_translation_data.copy()
        translation_data["poem_id"] = "non_existent_poem_id"

        with pytest.raises(ResourceNotFoundException) as exc_info:
            await repo.create(TranslationCreate(**translation_data))

        assert "Poem not found" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_create_duplicate_translation_fails(self, db_session: AsyncSession, sample_poem: Poem, sample_translation_data):
        """Test creating duplicate translation fails with conflict."""
        repo = TranslationRepository(db_session)

        # Create first translation
        translation_data = sample_translation_data.copy()
        translation_data["poem_id"] = sample_poem.id
        await repo.create(TranslationCreate(**translation_data))

        # Try to create duplicate
        with pytest.raises(ConflictException) as exc_info:
            await repo.create(TranslationCreate(**translation_data))

        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_create_same_language_as_source_fails(self, db_session: AsyncSession, sample_poem: Poem, sample_translation_data):
        """Test creating translation with same language as source fails."""
        repo = TranslationRepository(db_session)

        translation_data = sample_translation_data.copy()
        translation_data["poem_id"] = sample_poem.id
        translation_data["target_language"] = sample_poem.source_language  # Same as source

        with pytest.raises(ValidationError) as exc_info:
            await repo.create(TranslationCreate(**translation_data))

        assert "same as source language" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_by_poem(self, db_session: AsyncSession, sample_poem: Poem, sample_translation: Translation):
        """Test getting translations by poem."""
        repo = TranslationRepository(db_session)

        translations = await repo.get_by_poem(sample_poem.id)

        assert len(translations) >= 1
        assert sample_translation.id in [t.id for t in translations]
        assert all(t.poem_id == sample_poem.id for t in translations)

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_by_poem_with_language_filter(self, db_session: AsyncSession, sample_poem: Poem, sample_translation: Translation):
        """Test getting translations by poem with language filter."""
        repo = TranslationRepository(db_session)

        translations = await repo.get_by_poem(
            sample_poem.id,
            target_language=sample_translation.target_language
        )

        assert len(translations) >= 1
        assert all(t.target_language == sample_translation.target_language for t in translations)
        assert all(t.poem_id == sample_poem.id for t in translations)

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_latest_version(self, db_session: AsyncSession, sample_poem: Poem, sample_translation: Translation):
        """Test getting latest version of translation."""
        repo = TranslationRepository(db_session)

        latest = await repo.get_latest_version(
            sample_poem.id,
            sample_translation.target_language
        )

        assert latest is not None
        assert latest.poem_id == sample_poem.id
        assert latest.target_language == sample_translation.target_language

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_by_language_pair(self, db_session: AsyncSession, sample_poem: Poem, sample_translation: Translation):
        """Test getting translations by language pair."""
        repo = TranslationRepository(db_session)

        translations, total = await repo.get_by_language_pair(
            sample_poem.source_language,
            sample_translation.target_language
        )

        assert len(translations) >= 1
        assert total >= 1
        assert sample_translation.id in [t.id for t in translations]

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_by_translator_type(self, db_session: AsyncSession, sample_translation: Translation):
        """Test getting translations by translator type."""
        repo = TranslationRepository(db_session)

        translations, total = await repo.get_by_translator_type(
            sample_translation.translator_type
        )

        assert isinstance(translations, list)
        assert isinstance(total, int)
        assert all(t.translator_type == sample_translation.translator_type for t in translations)

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_search_translations(self, db_session: AsyncSession, sample_translation: Translation):
        """Test searching translations."""
        repo = TranslationRepository(db_session)

        # Search by translated text
        translations, total = await repo.search(
            query=sample_translation.translated_text[:10]
        )

        assert len(translations) >= 1
        assert total >= 1

        # Search by translator type
        translations, total = await repo.search(
            translator_type=sample_translation.translator_type
        )

        assert len(translations) >= 1
        assert total >= 1

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_search_no_results(self, db_session: AsyncSession):
        """Test searching with no matching results."""
        repo = TranslationRepository(db_session)

        translations, total = await repo.search(query="NonExistentTranslation")

        assert len(translations) == 0
        assert total == 0

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_update_status(self, db_session: AsyncSession, sample_translation: Translation):
        """Test updating translation status."""
        repo = TranslationRepository(db_session)

        updated_translation = await repo.update_status(
            sample_translation.id,
            AiLogStatus.FAILED,
            error_message="Test error message"
        )

        assert updated_translation is not None
        assert updated_translation.status == AiLogStatus.FAILED
        assert updated_translation.error_message == "Test error message"

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_update_status_non_existent_fails(self, db_session: AsyncSession):
        """Test updating status of non-existent translation fails."""
        repo = TranslationRepository(db_session)

        with pytest.raises(ResourceNotFoundException):
            await repo.update_status(
                "non_existent_id",
                AiLogStatus.COMPLETED
            )

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_language_pair_statistics(self, db_session: AsyncSession, sample_poem: Poem, sample_translation: Translation):
        """Test getting language pair statistics."""
        repo = TranslationRepository(db_session)

        stats = await repo.get_language_pair_statistics()

        assert isinstance(stats, list)
        assert len(stats) >= 1

        # Should contain our sample translation's language pair
        source_targets = [(s["source_language"], s["target_language"]) for s in stats]
        pair = (sample_poem.source_language, sample_translation.target_language)
        assert pair in source_targets

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_translator_statistics(self, db_session: AsyncSession, sample_translation: Translation):
        """Test getting translator statistics."""
        repo = TranslationRepository(db_session)

        stats = await repo.get_translator_statistics()

        assert isinstance(stats, list)
        assert len(stats) >= 1

        # Should contain our sample translation's translator type
        translator_types = [s["translator_type"] for s in stats]
        assert sample_translation.translator_type in translator_types

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_recent_translations(self, db_session: AsyncSession, sample_translation: Translation):
        """Test getting recent translations."""
        repo = TranslationRepository(db_session)

        recent_translations = await repo.get_recent_translations(days=30)

        assert isinstance(recent_translations, list)
        # Should include our sample translation
        translation_ids = [t.id for t in recent_translations]
        assert sample_translation.id in translation_ids

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_bulk_publish(self, db_session: AsyncSession, sample_translation: Translation):
        """Test bulk updating translation publish status."""
        repo = TranslationRepository(db_session)

        result = await repo.bulk_publish(
            translation_ids=[sample_translation.id],
            is_published=False
        )

        assert result == 1

        # Verify the update
        updated_translation = await repo.get(sample_translation.id)
        assert updated_translation.is_published is False

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_count(self, db_session: AsyncSession, sample_translation: Translation):
        """Test counting translations."""
        repo = TranslationRepository(db_session)

        count = await repo.count()

        assert isinstance(count, int)
        assert count >= 1

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_exists(self, db_session: AsyncSession, sample_translation: Translation):
        """Test checking if translation exists."""
        repo = TranslationRepository(db_session)

        # Test existing translation
        assert await repo.exists(sample_translation.id) is True

        # Test non-existent translation
        assert await repo.exists("non_existent_id") is False

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_multi_with_pagination(self, db_session: AsyncSession, sample_translation: Translation):
        """Test listing translations with pagination."""
        repo = TranslationRepository(db_session)

        # Test first page
        translations = await repo.get_multi(limit=1, skip=0)
        assert len(translations) >= 1

        # Test empty result with high skip
        empty_translations = await repo.get_multi(limit=10, skip=1000)
        assert len(empty_translations) == 0

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_by_poem_language_version(self, db_session: AsyncSession, sample_poem: Poem, sample_translation: Translation):
        """Test getting translation by poem, language, and version."""
        repo = TranslationRepository(db_session)

        found_translation = await repo.get_by_poem_language_version(
            sample_poem.id,
            sample_translation.target_language,
            sample_translation.version
        )

        assert found_translation is not None
        assert found_translation.id == sample_translation.id

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_create_with_translation_reference(self, db_session: AsyncSession, sample_poem: Poem, sample_translation: Translation):
        """Test creating translation with translation reference."""
        repo = TranslationRepository(db_session)

        translation_data = sample_translation_data.copy()
        translation_data["poem_id"] = sample_poem.id
        translation_data["translation_id"] = sample_translation.id  # Reference to existing translation

        # This should work since the translation exists and belongs to the poem
        new_translation = await repo.create(TranslationCreate(**translation_data))

        assert new_translation is not None
        assert new_translation.poem_id == sample_poem.id
        assert new_translation.translation_id == sample_translation.id

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_create_with_invalid_translation_reference_fails(self, db_session: AsyncSession, sample_poem: Poem):
        """Test creating translation with invalid translation reference fails."""
        repo = TranslationRepository(db_session)

        translation_data = sample_translation_data.copy()
        translation_data["poem_id"] = sample_poem.id
        translation_data["translation_id"] = "non_existent_translation_id"

        with pytest.raises(ResourceNotFoundException):
            await repo.create(TranslationCreate(**translation_data))

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_database_error_handling(self, db_session: AsyncSession, sample_poem: Poem, sample_translation_data, raise_database_error):
        """Test database error handling."""
        repo = TranslationRepository(db_session)

        translation_data = sample_translation_data.copy()
        translation_data["poem_id"] = sample_poem.id

        # Mock database session to raise an error
        with patch.object(db_session, 'commit', side_effect=raise_database_error()):
            with pytest.raises(DatabaseException):
                await repo.create(TranslationCreate(**translation_data))

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_logger_called(self, db_session: AsyncSession, sample_poem: Poem, sample_translation_data):
        """Test that logger is called during operations."""
        repo = TranslationRepository(db_session)

        translation_data = sample_translation_data.copy()
        translation_data["poem_id"] = sample_poem.id

        with patch.object(repo.logger, 'info') as mock_logger:
            await repo.create(TranslationCreate(**translation_data))

            # Verify logger was called
            mock_logger.assert_called_once()
            assert "Translation created" in str(mock_logger.call_args)