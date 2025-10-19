"""
Poem Repository Tests

This module contains tests for the poem repository implementation,
covering CRUD operations, search functionality, and specialized queries.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from vpsweb.repository.poems import PoemRepository
from vpsweb.repository.schemas import PoemCreate, PoemUpdate
from vpsweb.repository.exceptions import (
    ResourceNotFoundException,
    ConflictException,
    ValidationError,
    DatabaseException,
)
from vpsweb.repository.models import Poem


class TestPoemRepository:
    """Test cases for PoemRepository."""

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_create_poem_success(
        self, db_session: AsyncSession, sample_poem_data
    ):
        """Test successful poem creation."""
        repo = PoemRepository(db_session)
        poem = await repo.create(PoemCreate(**sample_poem_data))

        assert poem is not None
        assert poem.poet_name == sample_poem_data["poet_name"]
        assert poem.poem_title == sample_poem_data["poem_title"]
        assert poem.source_language == sample_poem_data["source_language"]
        assert poem.original_text == sample_poem_data["original_text"]
        assert poem.is_active is True
        assert poem.id is not None

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_create_duplicate_poem_fails(
        self, db_session: AsyncSession, sample_poem: Poem, sample_poem_data
    ):
        """Test creating duplicate poem fails with conflict."""
        repo = PoemRepository(db_session)

        with pytest.raises(ConflictException) as exc_info:
            await repo.create(PoemCreate(**sample_poem_data))

        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_create_invalid_language_fails(
        self, db_session: AsyncSession, sample_poem_data, mock_language_validator
    ):
        """Test creating poem with invalid language fails."""
        repo = PoemRepository(db_session)
        invalid_data = sample_poem_data.copy()
        invalid_data["source_language"] = "invalid"

        # Mock language validator to return False
        with patch(
            "vpsweb.repository.poems.validate_language_code",
            return_value=(False, "Invalid language"),
        ):
            with pytest.raises(ValidationError) as exc_info:
                await repo.create(PoemCreate(**invalid_data))

            assert "Invalid language" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_success(self, db_session: AsyncSession, sample_poem: Poem):
        """Test successful poem retrieval by ID."""
        repo = PoemRepository(db_session)
        retrieved_poem = await repo.get(sample_poem.id)

        assert retrieved_poem is not None
        assert retrieved_poem.id == sample_poem.id
        assert retrieved_poem.poet_name == sample_poem.poet_name

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_not_found(self, db_session: AsyncSession):
        """Test poem retrieval by ID for non-existent poem."""
        repo = PoemRepository(db_session)
        retrieved_poem = await repo.get("non_existent_id")

        assert retrieved_poem is None

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_update_poem_success(
        self, db_session: AsyncSession, sample_poem: Poem
    ):
        """Test successful poem update."""
        repo = PoemRepository(db_session)

        update_data = PoemUpdate(poem_title="Updated Title", genre="updated_genre")

        updated_poem = await repo.update(sample_poem.id, update_data)

        assert updated_poem is not None
        assert updated_poem.poem_title == "Updated Title"
        assert updated_poem.genre == "updated_genre"
        assert updated_poem.poet_name == sample_poem.poet_name  # Unchanged

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_update_non_existent_poem_fails(self, db_session: AsyncSession):
        """Test updating non-existent poem fails."""
        repo = PoemRepository(db_session)

        update_data = PoemUpdate(poem_title="Updated Title")

        with pytest.raises(ResourceNotFoundException):
            await repo.update("non_existent_id", update_data)

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_delete_poem_success(
        self, db_session: AsyncSession, sample_poem: Poem
    ):
        """Test successful poem deletion."""
        repo = PoemRepository(db_session)

        result = await repo.delete(sample_poem.id)

        assert result is True

        # Verify poem is deleted
        deleted_poem = await repo.get(sample_poem.id)
        assert deleted_poem is None

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_delete_non_existent_poem_fails(self, db_session: AsyncSession):
        """Test deleting non-existent poem fails."""
        repo = PoemRepository(db_session)

        with pytest.raises(ResourceNotFoundException):
            await repo.delete("non_existent_id")

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_search_by_title(self, db_session: AsyncSession, sample_poem: Poem):
        """Test searching poems by title."""
        repo = PoemRepository(db_session)

        poems, total = await repo.search(query=sample_poem.poem_title)

        assert len(poems) >= 1
        assert total >= 1
        assert sample_poem.poem_title in poems[0].poem_title

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_search_by_poet(self, db_session: AsyncSession, sample_poem: Poem):
        """Test searching poems by poet name."""
        repo = PoemRepository(db_session)

        poems, total = await repo.search(poet=sample_poem.poet_name)

        assert len(poems) >= 1
        assert total >= 1
        assert sample_poem.poet_name in poems[0].poet_name

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_search_by_language(
        self, db_session: AsyncSession, sample_poem: Poem
    ):
        """Test searching poems by language."""
        repo = PoemRepository(db_session)

        poems, total = await repo.search(language=sample_poem.source_language)

        assert len(poems) >= 1
        assert total >= 1
        assert poems[0].source_language == sample_poem.source_language

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_search_no_results(self, db_session: AsyncSession):
        """Test searching with no matching results."""
        repo = PoemRepository(db_session)

        poems, total = await repo.search(query="NonExistentPoem")

        assert len(poems) == 0
        assert total == 0

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_by_language(self, db_session: AsyncSession, sample_poem: Poem):
        """Test getting poems by language."""
        repo = PoemRepository(db_session)

        poems, total = await repo.get_by_language(sample_poem.source_language)

        assert len(poems) >= 1
        assert total >= 1
        assert all(
            poem.source_language == sample_poem.source_language for poem in poems
        )

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_by_poet(self, db_session: AsyncSession, sample_poem: Poem):
        """Test getting poems by poet."""
        repo = PoemRepository(db_session)

        poems, total = await repo.get_by_poet(sample_poem.poet_name)

        assert len(poems) >= 1
        assert total >= 1
        assert all(
            sample_poem.poet_name.lower() in poem.poet_name.lower() for poem in poems
        )

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_popular_tags(self, db_session: AsyncSession, sample_poem: Poem):
        """Test getting popular tags."""
        repo = PoemRepository(db_session)

        tags = await repo.get_popular_tags()

        assert isinstance(tags, list)
        # The tag from sample_poem should be included
        if sample_poem.tags:
            assert len(tags) >= 1

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_language_distribution(
        self, db_session: AsyncSession, sample_poem: Poem
    ):
        """Test getting language distribution."""
        repo = PoemRepository(db_session)

        distribution = await repo.get_language_distribution()

        assert isinstance(distribution, list)
        assert len(distribution) >= 1

        # Should contain our sample poem's language
        languages = [item["language"] for item in distribution]
        assert sample_poem.source_language in languages

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_recent_poems(self, db_session: AsyncSession, sample_poem: Poem):
        """Test getting recent poems."""
        repo = PoemRepository(db_session)

        recent_poems = await repo.get_recent_poems(days=30)

        assert isinstance(recent_poems, list)
        # Should include our sample poem
        poem_ids = [poem.id for poem in recent_poems]
        assert sample_poem.id in poem_ids

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_statistics(self, db_session: AsyncSession, sample_poem: Poem):
        """Test getting poem statistics."""
        repo = PoemRepository(db_session)

        stats = await repo.get_statistics()

        assert isinstance(stats, dict)
        assert "total_poems" in stats
        assert "unique_languages" in stats
        assert "unique_poets" in stats
        assert "language_distribution" in stats
        assert "popular_tags" in stats

        assert stats["total_poems"] >= 1

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_bulk_update_status(
        self, db_session: AsyncSession, sample_poem: Poem
    ):
        """Test bulk updating poem status."""
        repo = PoemRepository(db_session)

        result = await repo.bulk_update_status(
            poem_ids=[sample_poem.id], is_active=False
        )

        assert result == 1

        # Verify the update
        updated_poem = await repo.get(sample_poem.id)
        assert updated_poem.is_active is False

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_count(self, db_session: AsyncSession, sample_poem: Poem):
        """Test counting poems."""
        repo = PoemRepository(db_session)

        count = await repo.count()

        assert isinstance(count, int)
        assert count >= 1

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_exists(self, db_session: AsyncSession, sample_poem: Poem):
        """Test checking if poem exists."""
        repo = PoemRepository(db_session)

        # Test existing poem
        assert await repo.exists(sample_poem.id) is True

        # Test non-existent poem
        assert await repo.exists("non_existent_id") is False

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_list_with_pagination(
        self, db_session: AsyncSession, sample_poem: Poem
    ):
        """Test listing poems with pagination."""
        repo = PoemRepository(db_session)

        # Test first page
        poems = await repo.get_multi(limit=1, skip=0)
        assert len(poems) >= 1

        # Test empty result with high skip
        empty_poems = await repo.get_multi(limit=10, skip=1000)
        assert len(empty_poems) == 0

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_get_by_title_and_poet(
        self, db_session: AsyncSession, sample_poem: Poem
    ):
        """Test getting poem by title and poet."""
        repo = PoemRepository(db_session)

        found_poem = await repo.get_by_title_and_poet(
            sample_poem.poem_title, sample_poem.poet_name
        )

        assert found_poem is not None
        assert found_poem.id == sample_poem.id

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_bulk_create(self, db_session: AsyncSession, sample_poem_data):
        """Test bulk creating poems."""
        repo = PoemRepository(db_session)

        # Create multiple poem data
        poems_data = []
        for i in range(3):
            poem_data = sample_poem_data.copy()
            poem_data["poem_title"] = f"Bulk Poem {i}"
            poem_data["poet_name"] = f"Bulk Poet {i}"
            poems_data.append(PoemCreate(**poem_data))

        created_poems = await repo.bulk_create(poems_data)

        assert len(created_poems) == 3
        assert all(poem.id is not None for poem in created_poems)
        assert all(poem.poem_title.startswith("Bulk Poem") for poem in created_poems)

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_database_error_handling(
        self, db_session: AsyncSession, raise_database_error
    ):
        """Test database error handling."""
        repo = PoemRepository(db_session)

        # Mock database session to raise an error
        with patch.object(db_session, "commit", side_effect=raise_database_error()):
            with pytest.raises(DatabaseException):
                await repo.create(
                    PoemCreate(
                        poet_name="Test",
                        poem_title="Test",
                        source_language="en",
                        original_text="Test content",
                    )
                )

    @pytest.mark.asyncio
    @pytest.mark.repository
    async def test_logger_called(self, db_session: AsyncSession, sample_poem_data):
        """Test that logger is called during operations."""
        repo = PoemRepository(db_session)

        with patch.object(repo.logger, "info") as mock_logger:
            await repo.create(PoemCreate(**sample_poem_data))

            # Verify logger was called
            mock_logger.assert_called_once()
            assert "Poem created" in str(mock_logger.call_args)
