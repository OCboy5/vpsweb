"""
Test Enhanced Database Fixtures for P2.1

This test module verifies that the new pytest fixtures with in-memory
database work correctly and can be used for comprehensive testing.
"""

import pytest

# Mark these tests as database tests
pytestmark = pytest.mark.database


@pytest.mark.asyncio
async def test_database_session_fixture(db_session):
    """Test that the db_session fixture works correctly."""
    # Verify we have a database session
    assert db_session is not None
    assert hasattr(db_session, "execute")

    # Test basic database operations
    from sqlalchemy import text

    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_sample_poem_fixture(sample_poem):
    """Test that the sample_poem fixture creates a poem in the database."""
    # Verify the poem was created
    assert sample_poem is not None
    assert sample_poem.id is not None
    assert sample_poem.poet_name == "Test Poet"
    assert sample_poem.poem_title == "Test Poem Title"
    assert sample_poem.source_language == "English"


@pytest.mark.asyncio
async def test_sample_chinese_poem_fixture(sample_chinese_poem):
    """Test that the sample_chinese_poem fixture creates a Chinese poem."""
    # Verify the Chinese poem was created
    assert sample_chinese_poem is not None
    assert sample_chinese_poem.id is not None
    assert sample_chinese_poem.poet_name == "李白"
    assert sample_chinese_poem.poem_title == "静夜思"
    assert sample_chinese_poem.source_language == "Chinese"


@pytest.mark.asyncio
async def test_sample_translation_fixture(sample_translation):
    """Test that the sample_translation fixture creates a translation."""
    # Verify the translation was created
    assert sample_translation is not None
    assert sample_translation.id is not None
    assert sample_translation.target_language == "Chinese"
    assert sample_translation.translator_type == "ai"


@pytest.mark.asyncio
async def test_repository_service_fixture(repository_service, db_session):
    """Test that the repository service fixture works."""
    # Verify the repository service was created
    assert repository_service is not None
    assert repository_service.db_session == db_session

    # Test basic repository operations
    poems = await repository_service.list_poems()
    assert len(poems) >= 0


@pytest.mark.asyncio
async def test_poem_service_fixture(poem_service, sample_poem):
    """Test that the poem service fixture works with sample poem."""
    # Verify the poem service was created
    assert poem_service is not None

    # Test poem service operations
    poems = await poem_service.list_poems()
    assert len(poems) >= 1


@pytest.mark.asyncio
async def test_translation_service_fixture(
    translation_service, sample_poem, sample_translation
):
    """Test that the translation service fixture works."""
    # Verify the translation service was created
    assert translation_service is not None

    # Test translation service operations
    translations = await translation_service.list_translations(sample_poem.id)
    assert len(translations) >= 1


def test_test_client_fixture(test_client):
    """Test that the FastAPI test client fixture works."""
    # Verify the test client was created
    assert test_client is not None

    # Test basic API access
    response = test_client.get("/health")
    assert response.status_code == 200

    # Test API endpoint
    response = test_client.get("/api/v1/poems/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_test_context_fixture(test_context):
    """Test that the test context helper works."""
    # Verify the test context was created
    assert test_context is not None
    assert test_context.session is not None

    # Test creating a poem through the context helper
    poem = await test_context.create_poem(
        poet_name="Context Test Poet",
        poem_title="Context Test Poem",
        source_language="English",
        original_text="This is a test poem created via context helper.",
    )

    assert poem is not None
    assert poem.id is not None
    assert poem.poet_name == "Context Test Poet"


@pytest.mark.asyncio
async def test_poem_generator_fixture(poem_generator):
    """Test that the poem generator works."""
    # Test generating poems
    poems = poem_generator.generate_poems(3)
    assert len(poems) == 3

    for i, poem in enumerate(poems):
        assert poem["poet_name"] == f"Poet {i+1}"
        assert poem["poem_title"] == f"Test Poem {i+1}"


@pytest.mark.asyncio
async def test_translation_generator_fixture(translation_generator):
    """Test that the translation generator works."""
    # Test generating translations
    poem_ids = ["test-poem-1", "test-poem-2"]
    translations = translation_generator.generate_translations(poem_ids)
    assert len(translations) == 2

    for i, translation in enumerate(translations):
        assert translation["poem_id"] == poem_ids[i]
        assert translation["target_language"] == "Chinese"


def test_test_data_factory_fixture(test_data_factory):
    """Test that the test data factory works."""
    # Test creating poem data
    poem_data = test_data_factory.create_poem()
    assert poem_data["poet_name"] == "Test Poet"
    assert poem_data["poem_title"] == "Test Poem"

    # Test creating translation data
    translation_data = test_data_factory.create_translation("test-poem-id")
    assert translation_data["poem_id"] == "test-poem-id"
    assert translation_data["target_language"] == "Chinese"


def test_performance_timer_fixture(performance_timer):
    """Test that the performance timer works."""
    # Test timer functionality
    assert performance_timer.start_time is None
    assert performance_timer.end_time is None
    assert performance_timer.duration is None

    # Test timing
    performance_timer.start()
    import time

    time.sleep(0.01)  # 10ms
    performance_timer.stop()

    assert performance_timer.start_time is not None
    assert performance_timer.end_time is not None
    assert performance_timer.duration is not None
    assert performance_timer.duration >= 0.01


@pytest.mark.asyncio
async def test_database_isolation(db_session):
    """Test that database sessions are properly isolated."""
    # Create a poem in one session
    import uuid

    from vpsweb.repository.models import Poem

    poem_id = str(uuid.uuid4())[:26]
    poem = Poem(
        id=poem_id,
        poet_name="Isolation Test Poet",
        poem_title="Isolation Test Poem",
        source_language="English",
        original_text="Test poem for isolation verification.",
    )
    db_session.add(poem)
    await db_session.commit()

    # Verify the poem exists in this session
    result = await db_session.execute(
        "SELECT COUNT(*) FROM poems WHERE id = :poem_id", {"poem_id": poem_id}
    )
    assert result.scalar() == 1

    # Create a new session (simulating test isolation)
    from sqlalchemy.ext.asyncio import async_sessionmaker

    new_session = async_sessionmaker(
        bind=db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with new_session() as isolated_session:
        # The poem should not be visible in a rolled back session
        result = await isolated_session.execute(
            "SELECT COUNT(*) FROM poems WHERE id = :poem_id",
            {"poem_id": poem_id},
        )
        # The count should be 0 because changes are rolled back when session exits
        assert result.scalar() == 0


@pytest.mark.integration
async def test_full_workflow_integration(
    test_client, sample_poem, sample_translation
):
    """Test full workflow integration with all fixtures."""
    # Test getting poems via API
    response = test_client.get("/api/v1/poems/")
    assert response.status_code == 200
    poems_data = response.json()
    assert isinstance(poems_data, list)
    assert len(poems_data) >= 1

    # Test getting specific poem via API
    response = test_client.get(f"/api/v1/poems/{sample_poem.id}")
    assert response.status_code == 200
    poem_data = response.json()
    assert poem_data["id"] == sample_poem.id
    assert poem_data["poet_name"] == sample_poem.poet_name

    # Test getting translations for the poem
    response = test_client.get(f"/api/v1/poems/{sample_poem.id}/translations")
    assert response.status_code == 200
    translations_data = response.json()
    assert isinstance(translations_data, list)
    assert len(translations_data) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
