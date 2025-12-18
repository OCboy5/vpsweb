"""
Repository System Test Configuration and Fixtures

This module provides pytest configuration and shared fixtures specifically
for testing the VPSWeb repository system components.

Features:
- Async database session fixtures
- Repository test data factories
- Common test utilities
- Test environment setup
"""

import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, pool
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import Session, sessionmaker

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.vpsweb.repository.models import Base

# Configure pytest-asyncio
pytest_asyncio.default_mode = "auto"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Create a test database engine.

    Uses an in-memory SQLite database for fast testing.
    """
    # Use in-memory SQLite for testing
    test_url = "sqlite+aiosqlite:///:memory:"

    engine = create_async_engine(
        test_url,
        echo=False,
        poolclass=pool.StaticPool,
        connect_args={
            "check_same_thread": False,
        },
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    await engine.dispose()


@pytest.fixture(scope="session")
def sync_test_engine():
    """
    Create a synchronous test database engine with in-memory SQLite.

    This matches production setup and uses synchronous SQLAlchemy.
    """
    # Use regular SQLite for testing (like production)
    test_url = "sqlite:///:memory:"

    engine = create_engine(
        test_url,
        echo=False,
        poolclass=pool.StaticPool,
        connect_args={
            "check_same_thread": False,
        },
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Clean up
    engine.dispose()


@pytest.fixture
def db_session(sync_test_engine) -> Generator[Session, None, None]:
    """
    Create a synchronous database session for testing.

    Matches production setup and provides proper test isolation.

    Yields:
        Session: Synchronous database session matching production
    """
    from sqlalchemy.orm import sessionmaker

    session = sessionmaker(
        bind=sync_test_engine,
        autocommit=False,
        autoflush=False,
    )()

    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def sample_poem_data():
    """Sample poem data for testing."""
    return {
        "poet_name": "Test Poet",
        "poem_title": "Test Poem Title",
        "source_language": "en",
        "original_text": "This is a test poem with enough content to pass validation requirements. It contains meaningful verses and proper structure for testing purposes.",
        "selected": False,
        "metadata_json": '{"test": "sample_poem_data"}',
    }


@pytest.fixture
def sample_translation_data():
    """Sample translation data for testing."""
    return {
        "target_language": "zh-CN",
        "version": 1,
        "translated_text": "这是一首测试诗歌的中文翻译，包含足够的内容以通过验证要求。它包含有意义的诗节和用于测试目的的正确结构。",
        "translator_notes": "Test translation notes",
        "translator_type": "hybrid",
        "translator_info": "Test Translator",
        "quality_score": "0.85",
        "license": "CC-BY-4.0",
        "is_published": True,
    }


@pytest.fixture
def sample_ai_log_data():
    """Sample AI log data for testing."""
    return {
        "workflow_mode": "hybrid",
        "provider": "test_provider",
        "model_name": "test-model",
        "temperature": "0.7",
        "prompt_tokens": 100,
        "completion_tokens": 200,
        "total_tokens": 300,
        "cost": "0.001",
        "duration_seconds": "5.5",
        "status": "completed",
        "error_message": None,
        "raw_response": '{"result": "test"}',
    }


@pytest.fixture
def sample_human_note_data():
    """Sample human note data for testing."""
    return {
        "note_type": "editorial",
        "content": "This is a test note with sufficient content to pass validation. It provides meaningful feedback about the poem or translation.",
        "author_name": "Test Reviewer",
        "is_public": True,
    }


@pytest.fixture
def mock_ulid_generator():
    """Mock ULID generator for predictable test IDs."""

    def _generate_ulid():
        return "01HXRQ8YJ9P9N7Q4J8K2R4S4T3"

    return _generate_ulid


@pytest.fixture
def mock_language_validator():
    """Mock language validator for testing."""

    def _validate_language_code(code):
        valid_codes = ["en", "zh-CN", "es", "fr", "de", "ja"]
        if code.lower() in valid_codes:
            return True, None
        return False, f"Invalid language code: {code}"

    return _validate_language_code


@pytest.fixture
def sample_poem(db_session, sample_poem_data, mock_ulid_generator):
    """Create a sample poem in the database."""
    from src.vpsweb.repository.models import Poem

    poem_data = sample_poem_data.copy()
    poem_data["id"] = mock_ulid_generator()

    poem = Poem(**poem_data)
    db_session.add(poem)
    db_session.commit()
    db_session.refresh(poem)

    return poem


@pytest.fixture
def sample_translation(
    db_session, sample_poem, sample_translation_data, mock_ulid_generator
):
    """Create a sample translation in the database."""
    from src.vpsweb.repository.models import Translation

    translation_data = sample_translation_data.copy()
    translation_data["id"] = mock_ulid_generator()
    translation_data["poem_id"] = sample_poem.id

    translation = Translation(**translation_data)
    db_session.add(translation)
    db_session.commit()
    db_session.refresh(translation)

    return translation


# Custom pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (require database)"
    )
    config.addinivalue_line("markers", "slow: Slow tests (marked for CI)")
    config.addinivalue_line("markers", "repository: Repository layer tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "validation: Input validation tests")


@pytest.fixture(autouse=True)
def configure_logging():
    """Configure logging for tests."""
    import logging

    # Set higher log level for tests to reduce noise
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    # Use a simple console handler for tests
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


# Test utilities
class AsyncTestContext:
    """Helper class for async test context management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_poem(self, **kwargs):
        """Create a poem with default values."""
        from src.vpsweb.repository.models import Poem

        default_data = {
            "id": "01HXRQ8YJ9P9N7Q4J8K2R4S4T3",
            "poet_name": "Test Poet",
            "poem_title": "Test Poem",
            "source_language": "en",
            "original_text": "Test poem content for testing purposes.",
            "is_active": True,
        }
        default_data.update(kwargs)

        poem = Poem(**default_data)
        self.session.add(poem)
        await self.session.commit()
        await self.session.refresh(poem)
        return poem

    async def create_translation(self, poem_id: str, **kwargs):
        """Create a translation with default values."""
        from src.vpsweb.repository.models import Translation

        default_data = {
            "id": "01HXRQ8YJ9P9N7Q4J8K2R4S4T4",
            "poem_id": poem_id,
            "target_language": "zh-CN",
            "version": 1,
            "translated_text": "测试翻译内容",
            "translator_type": "hybrid",
            "license": "CC-BY-4.0",
            "is_published": True,
        }
        default_data.update(kwargs)

        translation = Translation(**default_data)
        self.session.add(translation)
        await self.session.commit()
        await self.session.refresh(translation)
        return translation


@pytest.fixture
def test_context(db_session):
    """Create a test context helper."""
    yield AsyncTestContext(db_session)


# Error testing utilities
@pytest.fixture
def raise_database_error():
    """Utility to raise database errors in tests."""

    def _raise_error(message="Test database error"):
        from src.vpsweb.repository.exceptions import DatabaseException

        raise DatabaseException(message)

    return _raise_error


@pytest.fixture
def raise_validation_error():
    """Utility to raise validation errors in tests."""

    def _raise_error(message="Test validation error"):
        from src.vpsweb.repository.exceptions import ValidationException

        raise ValidationException(message)

    return _raise_error


# Test data generators
@pytest.fixture
def generate_test_poems():
    """Generate multiple test poems."""

    def _generate_poems(count: int = 5):
        poems = []
        for i in range(count):
            poem = {
                "id": f"test_poem_{i:03d}",
                "poet_name": f"Poet {i}",
                "poem_title": f"Test Poem {i}",
                "source_language": "en" if i % 2 == 0 else "zh-CN",
                "original_text": f"This is test poem number {i} with sufficient content for validation.",
                "is_active": True,
            }
            poems.append(poem)
        return poems

    return _generate_poems


@pytest_asyncio.fixture
async def test_client(db_session):
    """
    Create a test client for FastAPI app testing.

    Args:
        db_session: Async database session

    Returns:
        AsyncClient: Test HTTP client
    """
    from httpx import AsyncClient

    from src.vpsweb.repository.database import get_db
    from src.vpsweb.webui.main import create_app

    # Create the FastAPI app
    app = create_app()

    # Override the database dependency
    def override_get_db():
        return db_session

    app.dependency_overrides[get_db] = override_get_db

    # Create test client
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()
