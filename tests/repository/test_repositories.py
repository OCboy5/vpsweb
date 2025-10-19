"""
Repository layer tests for VPSWeb Repository System.

This module tests the repository pattern implementation including
CRUD operations, search functionality, and data validation.
"""

import pytest
from sqlalchemy.exc import SQLAlchemyError

from vpsweb.repository.poems import PoemRepository
from vpsweb.repository.translations import TranslationRepository
from vpsweb.repository.ai_logs import AiLogRepository
from vpsweb.repository.human_notes import HumanNoteRepository
from vpsweb.repository.exceptions import (
    DatabaseException,
    ValidationException,
    ResourceNotFoundException,
)
from vpsweb.repository.schemas import (
    PoemCreate,
    TranslationCreate,
    AiLogCreate,
    HumanNoteCreate,
    AiLogStatus,
    WorkflowMode,
)


@pytest.mark.repository
@pytest.mark.unit
async def test_poem_repository_create(db_session):
    """
    Test poem repository create operation.

    Args:
        db_session: Async database session
    """
    repo = PoemRepository(db_session)

    poem_data = PoemCreate(
        poet_name="Test Poet",
        poem_title="Test Poem",
        source_language="en",
        original_text="This is a test poem\nFor testing purposes\nWritten in English",
        tags=["test", "sample"],
    )

    poem = await repo.create(poem_data)

    assert poem is not None
    assert poem.poet_name == "Test Poet"
    assert poem.poem_title == "Test Poem"
    assert poem.source_language == "en"
    assert poem.is_active is True
    assert poem.id is not None


@pytest.mark.repository
@pytest.mark.unit
async def test_poem_repository_get_by_id(db_session, sample_poem):
    """
    Test poem repository get by ID operation.

    Args:
        db_session: Async database session
        sample_poem: Sample poem fixture
    """
    repo = PoemRepository(db_session)

    retrieved_poem = await repo.get(sample_poem.id)

    assert retrieved_poem is not None
    assert retrieved_poem.id == sample_poem.id
    assert retrieved_poem.poet_name == sample_poem.poet_name


@pytest.mark.repository
@pytest.mark.unit
async def test_poem_repository_get_not_found(db_session):
    """
    Test poem repository get operation with non-existent ID.

    Args:
        db_session: Async database session
    """
    repo = PoemRepository(db_session)

    retrieved_poem = await repo.get("non-existent-id")

    assert retrieved_poem is None


@pytest.mark.repository
@pytest.mark.unit
async def test_poem_repository_update(db_session, sample_poem):
    """
    Test poem repository update operation.

    Args:
        db_session: Async database session
        sample_poem: Sample poem fixture
    """
    repo = PoemRepository(db_session)

    update_data = {"poem_title": "Updated Test Poem", "tags": ["updated", "test"]}

    updated_poem = await repo.update(sample_poem, update_data)

    assert updated_poem.poem_title == "Updated Test Poem"
    assert "updated" in updated_poem.tags


@pytest.mark.repository
@pytest.mark.unit
async def test_poem_repository_delete(db_session, sample_poem):
    """
    Test poem repository delete operation.

    Args:
        db_session: Async database session
        sample_poem: Sample poem fixture
    """
    repo = PoemRepository(db_session)

    deleted_poem = await repo.remove(sample_poem)

    assert deleted_poem.id == sample_poem.id

    # Verify poem is deleted
    retrieved_poem = await repo.get(sample_poem.id)
    assert retrieved_poem is None


@pytest.mark.repository
@pytest.mark.unit
async def test_poem_repository_search(db_session, sample_poem):
    """
    Test poem repository search functionality.

    Args:
        db_session: Async database session
        sample_poem: Sample poem fixture
    """
    repo = PoemRepository(db_session)

    # Search by title
    poems, total = await repo.search(query="Test")

    assert total >= 1
    assert len(poems) >= 1
    assert any(poem.id == sample_poem.id for poem in poems)


@pytest.mark.repository
@pytest.mark.unit
async def test_translation_repository_create(db_session, sample_poem):
    """
    Test translation repository create operation.

    Args:
        db_session: Async database session
        sample_poem: Sample poem fixture
    """
    repo = TranslationRepository(db_session)

    translation_data = TranslationCreate(
        poem_id=sample_poem.id,
        translated_text="这是一首测试诗\n用于测试目的\n用中文写成",
        target_language="zh",
        version=1,
        translator_type="ai",
    )

    translation = await repo.create(translation_data)

    assert translation is not None
    assert translation.poem_id == sample_poem.id
    assert translation.target_language == "zh"
    assert translation.version == 1


@pytest.mark.repository
@pytest.mark.unit
async def test_translation_repository_get_by_poem(db_session, sample_translation):
    """
    Test translation repository get by poem operation.

    Args:
        db_session: Async database session
        sample_translation: Sample translation fixture
    """
    repo = TranslationRepository(db_session)

    translations = await repo.get_by_poem(sample_translation.poem_id)

    assert len(translations) >= 1
    assert any(t.id == sample_translation.id for t in translations)


@pytest.mark.repository
@pytest.mark.unit
async def test_ai_log_repository_create(db_session, sample_poem, sample_translation):
    """
    Test AI log repository create operation.

    Args:
        db_session: Async database session
        sample_poem: Sample poem fixture
        sample_translation: Sample translation fixture
    """
    repo = AiLogRepository(db_session)

    ai_log_data = AiLogCreate(
        poem_id=sample_poem.id,
        translation_id=sample_translation.id,
        provider="test_provider",
        model_name="test-model",
        workflow_mode=WorkflowMode.HYBRID,
        status=AiLogStatus.COMPLETED,
        duration_seconds=5.2,
        total_tokens=150,
        cost=0.005,
    )

    ai_log = await repo.create(ai_log_data)

    assert ai_log is not None
    assert ai_log.poem_id == sample_poem.id
    assert ai_log.translation_id == sample_translation.id
    assert ai_log.provider == "test_provider"


@pytest.mark.repository
@pytest.mark.unit
async def test_human_note_repository_create(
    db_session, sample_poem, sample_translation
):
    """
    Test human note repository create operation.

    Args:
        db_session: Async database session
        sample_poem: Sample poem fixture
        sample_translation: Sample translation fixture
    """
    repo = HumanNoteRepository(db_session)

    note_data = HumanNoteCreate(
        poem_id=sample_poem.id,
        translation_id=sample_translation.id,
        title="Test Note",
        content="This is a test note for the translation",
        note_type="editorial",
        author_name="Test Editor",
        is_public=True,
    )

    note = await repo.create(note_data)

    assert note is not None
    assert note.poem_id == sample_poem.id
    assert note.translation_id == sample_translation.id
    assert note.note_type == "editorial"


@pytest.mark.repository
@pytest.mark.unit
async def test_poem_repository_validation_error(db_session):
    """
    Test poem repository validation error handling.

    Args:
        db_session: Async database session
    """
    repo = PoemRepository(db_session)

    # Invalid language code
    invalid_poem_data = PoemCreate(
        poet_name="Test Poet",
        poem_title="Test Poem",
        source_language="invalid_lang",
        original_text="Test content",
    )

    with pytest.raises(ValidationException):
        await repo.create(invalid_poem_data)


@pytest.mark.repository
@pytest.mark.unit
async def test_translation_repository_not_found_error(db_session):
    """
    Test translation repository not found error handling.

    Args:
        db_session: Async database session
    """
    repo = TranslationRepository(db_session)

    # Try to create translation for non-existent poem
    invalid_translation_data = TranslationCreate(
        poem_id="non-existent-poem-id",
        translated_text="Test translation",
        target_language="zh",
        version=1,
    )

    with pytest.raises(ResourceNotFoundException):
        await repo.create(invalid_translation_data)


@pytest.mark.repository
@pytest.mark.unit
async def test_repository_count_operation(db_session, sample_poem):
    """
    Test repository count operation.

    Args:
        db_session: Async database session
        sample_poem: Sample poem fixture
    """
    repo = PoemRepository(db_session)

    count = await repo.count()

    assert count >= 1
    assert isinstance(count, int)


@pytest.mark.repository
@pytest.mark.unit
async def test_repository_exists_operation(db_session, sample_poem):
    """
    Test repository exists operation.

    Args:
        db_session: Async database session
        sample_poem: Sample poem fixture
    """
    repo = PoemRepository(db_session)

    exists = await repo.exists(sample_poem.id)
    assert exists is True

    not_exists = await repo.exists("non-existent-id")
    assert not_exists is False


@pytest.mark.repository
@pytest.mark.unit
async def test_repository_get_multi_operation(db_session, sample_poem):
    """
    Test repository get multiple operation.

    Args:
        db_session: Async database session
        sample_poem: Sample poem fixture
    """
    repo = PoemRepository(db_session)

    poems = await repo.get_multi(limit=10)

    assert len(poems) >= 1
    assert isinstance(poems, list)


@pytest.mark.repository
@pytest.mark.unit
async def test_database_error_handling(db_session, mock_ulid_generator):
    """
    Test database error handling in repositories.

    Args:
        db_session: Async database session
        mock_ulid_generator: Mock ULID generator
    """
    repo = PoemRepository(db_session)

    # Create a poem that will cause an error (missing required field)
    invalid_data = {
        "id": mock_ulid_generator(),
        "poet_name": "Test Poet",
        # Missing required fields
    }

    with pytest.raises((DatabaseException, SQLAlchemyError)):
        # This should raise an exception due to missing required fields
        poem = repo.model(**invalid_data)
        db_session.add(poem)
        await db_session.commit()
