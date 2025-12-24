"""
Pytest fixtures for VPSWeb testing.

This module provides common fixtures for unit and integration tests,
including sample data, mock responses, and temporary directories.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from src.vpsweb.models.config import (
    CompleteConfig,
    LoggingConfig,
    MainConfig,
    ModelProviderConfig,
    ProvidersConfig,
    StepConfig,
    StorageConfig,
    WorkflowConfig,
)
from src.vpsweb.models.translation import (
    EditorReview,
    InitialTranslation,
    RevisedTranslation,
    TranslationInput,
    TranslationOutput,
)


@pytest.fixture
def sample_translation_input():
    """Fixture providing a sample TranslationInput for testing."""
    return TranslationInput(
        original_poem="The fog comes on little cat feet.",
        source_lang="English",
        target_lang="Chinese",
    )


@pytest.fixture
def sample_english_poem():
    """Fixture providing a sample English poem."""
    return """The fog comes
on little cat feet.
It sits looking
over harbor and city
on silent haunches
and then moves on."""


@pytest.fixture
def sample_chinese_poem():
    """Fixture providing a sample Chinese poem."""
    return """雾来了
踏着猫的细步
它静静地蹲伏着
俯视海港和城市
再向前走去"""


@pytest.fixture
def mock_llm_response_valid_xml():
    """Fixture providing a valid XML response from LLM."""
    return """<translation>
<initial_translation>雾来了，踏着猫的细步。</initial_translation>
<initial_translation_notes>This translation captures the imagery of the fog moving quietly like a cat.</initial_translation_notes>
<translated_poem_title>雾</translated_poem_title>
<translated_poet_name>卡尔·桑德堡</translated_poet_name>
</translation>"""


@pytest.fixture
def mock_llm_response_malformed_xml():
    """Fixture providing a malformed XML response from LLM."""
    return """<translation>
<initial_translation>雾来了，踏着猫的细步。</initial_translation>
<explanation>This is missing closing tags"""


@pytest.fixture
def mock_llm_response_missing_tags():
    """Fixture providing XML response with missing required tags."""
    return """<translation>
<explanation>This is missing the initial_translation tag</explanation>
</translation>"""


@pytest.fixture
def mock_llm_response_editor_review():
    """Fixture providing a valid editor review response."""
    return """<editor_review>
<text>1. Consider using more poetic language for "little cat feet"
2. The rhythm could be improved in the second line
3. Add more cultural context for Chinese readers</text>
<summary>Good literal translation but needs poetic refinement</summary>
</editor_review>"""


@pytest.fixture
def mock_llm_response_revised_translation():
    """Fixture providing a valid revised translation response."""
    return """<revised_translation>雾来了，踏着猫儿轻盈的脚步。</revised_translation>
<revised_translation_notes>Added poetic language and improved rhythm while maintaining original meaning.</revised_translation_notes>
<refined_translated_poem_title>雾</refined_translated_poem_title>
<refined_translated_poet_name>卡尔·桑德堡</refined_translated_poet_name>"""


@pytest.fixture
def temp_output_dir():
    """Fixture providing a temporary directory for output files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_config():
    """Fixture providing a sample CompleteConfig for testing."""
    return CompleteConfig(
        main=MainConfig(
            workflow=WorkflowConfig(
                name="test_workflow",
                version="1.0.0",
                hybrid_workflow={
                    "initial_translation": StepConfig(
                        provider="tongyi",
                        model="qwen-max",
                        temperature=0.7,
                        max_tokens=1000,
                        prompt_template="test_template.yaml",
                    ),
                    "editor_review": StepConfig(
                        provider="deepseek",
                        model="deepseek-chat",
                        temperature=0.5,
                        max_tokens=800,
                        prompt_template="test_template.yaml",
                    ),
                    "translator_revision": StepConfig(
                        provider="tongyi",
                        model="qwen-max",
                        temperature=0.6,
                        max_tokens=1000,
                        prompt_template="test_template.yaml",
                    ),
                },
            ),
            storage=StorageConfig(output_dir="./output"),
            logging=LoggingConfig(
                level="INFO",
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                file="logs/vpsweb.log",
                max_file_size=10485760,
                backup_count=5,
            ),
        ),
        providers=ProvidersConfig(
            providers={
                "tongyi": ModelProviderConfig(
                    api_key_env="TONGYI_API_KEY",
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    type="openai_compatible",
                    models=["qwen-max", "qwen-plus"],
                    default_model="qwen-max",
                ),
                "deepseek": ModelProviderConfig(
                    api_key_env="DEEPSEEK_API_KEY",
                    base_url="https://api.deepseek.com",
                    type="openai_compatible",
                    models=["deepseek-reasoner", "deepseek-chat"],
                    default_model="deepseek-reasoner",
                ),
            }
        ),
    )


@pytest.fixture
def sample_workflow_config():
    """Fixture providing a sample WorkflowConfig for testing."""
    return WorkflowConfig(
        name="test_workflow",
        version="1.0.0",
        steps=[
            StepConfig(
                name="initial_translation",
                provider="tongyi",
                model="qwen-max",
                temperature=0.7,
                max_tokens=1000,
            ),
            StepConfig(
                name="editor_review",
                provider="deepseek",
                model="deepseek-chat",
                temperature=0.5,
                max_tokens=800,
                prompt_template="test_template.yaml",
            ),
            StepConfig(
                name="translator_revision",
                provider="tongyi",
                model="qwen-max",
                temperature=0.6,
                max_tokens=1000,
                prompt_template="test_template.yaml",
            ),
        ],
    )


@pytest.fixture
def sample_translation_output():
    """Fixture providing a sample TranslationOutput for testing."""
    from datetime import datetime

    return TranslationOutput(
        workflow_id="test-workflow-123",
        input=TranslationInput(
            original_poem="The fog comes on little cat feet.",
            source_lang="English",
            target_lang="Chinese",
            metadata={"poet_name": "Carl Sandburg", "poem_title": "Fog"},
        ),
        initial_translation=InitialTranslation(
            initial_translation="雾来了，踏着猫的细步。",
            initial_translation_notes="Literal translation capturing the imagery",
            translated_poem_title="雾",
            translated_poet_name="卡尔·桑德堡",
            model_info={"provider": "test", "model": "test-model"},
            tokens_used=500,
            timestamp=datetime.now(),
        ),
        editor_review=EditorReview(
            editor_suggestions="1. Consider using more poetic language\n2. Improve rhythm\n\nOverall assessment: Good literal translation but needs refinement",
            model_info={"provider": "test", "model": "test-model"},
            tokens_used=300,
            timestamp=datetime.now(),
        ),
        revised_translation=RevisedTranslation(
            revised_translation="雾来了，踏着猫儿轻盈的脚步。",
            revised_translation_notes="Added poetic language and improved rhythm",
            refined_translated_poem_title="雾",
            refined_translated_poet_name="卡尔·桑德堡",
            model_info={"provider": "test", "model": "test-model"},
            tokens_used=450,
            timestamp=datetime.now(),
        ),
        full_log="Test workflow log",
        total_tokens=1250,
        duration_seconds=15.5,
    )


@pytest.fixture
def mock_async_function():
    """Fixture providing a mock async function for testing."""

    async def mock_async_func(*_args, **kwargs):
        return {"result": "mock_response"}

    return mock_async_func


@pytest.fixture
def mock_llm_factory():
    """Fixture providing a mock LLM factory for testing."""

    class MockLLM:
        async def generate(self, _prompt: str, **kwargs):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "<translation><initial_translation>Mock translation</initial_translation></translation>"
                        }
                    }
                ]
            }

    class MockLLMFactory:
        def create_llm(self, provider: str, model: str, **kwargs):
            return MockLLM()

    return MockLLMFactory()


# Fixture for async event loop
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Integration test fixtures
@pytest.fixture
def mock_llm_response_initial_translation():
    """Mock LLM response for initial translation step."""
    return {
        "choices": [
            {
                "message": {
                    "content": """<initial_translation>雾来了，踏着猫的细步。</initial_translation>
<initial_translation_notes>This translation captures the gentle imagery of the fog moving quietly like a cat. The phrase "little cat feet" is translated to convey the delicate, stealthy movement in Chinese poetic context.</initial_translation_notes>"""
                }
            }
        ]
    }


@pytest.fixture
def mock_llm_response_editor_review():
    """Mock LLM response for editor review step."""
    return {
        "choices": [
            {
                "message": {
                    "content": """1. Consider using more poetic language for "little cat feet" - perhaps "猫儿轻盈的脚步"
2. The rhythm could be improved in the second line
3. Add more cultural context for Chinese readers

Overall assessment: Good literal translation but needs poetic refinement to capture the original's musical quality."""
                }
            }
        ]
    }


@pytest.fixture
def mock_llm_response_revised_translation_api():
    """Mock LLM API response for translator revision step."""
    return {
        "choices": [
            {
                "message": {
                    "content": """<revised_translation>雾来了，踏着猫儿轻盈的脚步。</revised_translation>
<revised_translation_notes>Based on the editor's suggestions, I refined the translation to use more poetic language. Changed "猫的细步" to "猫儿轻盈的脚步" to better capture the gentle, graceful movement. The revised version maintains the original meaning while enhancing the poetic quality and rhythm.</revised_translation_notes>
<refined_translated_poem_title>雾</refined_translated_poem_title>
<refined_translated_poet_name>卡尔·桑德堡</refined_translated_poet_name>"""
                }
            }
        ]
    }


@pytest.fixture
def mock_llm_factory_integration(mocker):
    """Mock LLM factory for integration tests."""
    from src.vpsweb.services.llm.factory import LLMFactory

    class MockLLM:
        def __init__(self, responses):
            self.responses = responses
            self.call_count = 0

        async def generate(self, _prompt: str, **kwargs):
            response = self.responses[self.call_count % len(self.responses)]
            self.call_count += 1
            return response

    # Create mock that returns our mock LLM
    def mock_create_llm(self, provider: str, model: str, **kwargs):
        responses = [
            mock_llm_response_initial_translation(),
            mock_llm_response_editor_review(),
            mock_llm_response_revised_translation_api(),
        ]
        return MockLLM(responses)

    # Mock the get_provider method
    mock_factory = mocker.MagicMock()
    mock_factory.get_provider = mock_create_llm

    mocker.patch.object(LLMFactory, "get_provider", mock_create_llm)

    # Return a mock factory instance that has the patched method
    mock_factory_instance = mocker.MagicMock()
    mock_factory_instance.get_provider = mock_create_llm
    return mock_factory_instance


@pytest.fixture
def sample_poem_file(temp_output_dir):
    """Create a temporary poem file for CLI testing."""
    poem_file = temp_output_dir / "test_poem.txt"
    poem_file.write_text("The fog comes on little cat feet.")
    return poem_file


@pytest.fixture
def cli_runner():
    """Provide Click CLI runner for testing."""
    from click.testing import CliRunner

    return CliRunner()


@pytest.fixture
def integration_providers_config():
    """Providers configuration for integration tests."""
    from src.vpsweb.models.config import (
        ModelProviderConfig,
        ProvidersConfig,
        ProviderType,
    )

    return ProvidersConfig(
        providers={
            "tongyi": ModelProviderConfig(
                api_key_env="TEST_TONGYI_API_KEY",
                base_url="https://test-tongyi.com",
                type=ProviderType.OPENAI_COMPATIBLE,
                models=["qwen-max", "qwen-plus"],
            ),
            "deepseek": ModelProviderConfig(
                api_key_env="TEST_DEEPSEEK_API_KEY",
                base_url="https://test-deepseek.com",
                type=ProviderType.OPENAI_COMPATIBLE,
                models=["deepseek-chat", "deepseek-coder"],
            ),
        }
    )


@pytest.fixture
def integration_workflow_config():
    """Workflow configuration for integration tests."""
    return WorkflowConfig(
        name="integration_test_workflow",
        version="1.0.0",
        hybrid_workflow={
            "initial_translation": StepConfig(
                name="initial_translation",
                provider="tongyi",
                model="qwen-max",
                temperature=0.7,
                max_tokens=1000,
                prompt_template="test_template.yaml",
            ),
            "editor_review": StepConfig(
                name="editor_review",
                provider="deepseek",
                model="deepseek-chat",
                temperature=0.5,
                max_tokens=800,
                prompt_template="test_template.yaml",
            ),
            "translator_revision": StepConfig(
                name="translator_revision",
                provider="tongyi",
                model="qwen-max",
                temperature=0.6,
                max_tokens=1000,
                prompt_template="test_template.yaml",
            ),
        },
    )


# ==============================================================================
# Enhanced Database Fixtures for P2.1
# ==============================================================================

import sys
from typing import AsyncGenerator, Generator

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vpsweb.repository.crud import RepositoryService
from vpsweb.repository.models import Base
from vpsweb.repository.service import RepositoryWebService
from vpsweb.utils.logger import get_logger
from vpsweb.webui.main import app
from vpsweb.webui.services.poem_service import PoemService

# Configure pytest-asyncio
pytest_asyncio.default_mode = "auto"

logger = get_logger(__name__)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Create a test database engine with in-memory SQLite.

    This fixture creates a fresh database for each test session,
    providing fast, isolated testing without external dependencies.
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
    from sqlalchemy import create_engine

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
    """
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


@pytest_asyncio.fixture
async def db_session_async(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for testing.

    Provides an async database session with automatic rollback
    to ensure test isolation.

    Yields:
        AsyncSession: Database session with automatic rollback
    """
    async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        # Session automatically rolls back after context exit


@pytest_asyncio.fixture
async def test_client(db_session):
    """
    Create a FastAPI test client with database override.

    This fixture provides a TestClient for the FastAPI application
    with the database dependency overridden to use the test session.

    Args:
        db_session: Async database session fixture

    Yields:
        TestClient: FastAPI test client
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

    # Use aggressive mocking with unittest.mock to override container resolution
    from unittest.mock import AsyncMock, MagicMock, patch

    from vpsweb.webui.container import container

    # Create comprehensive mock BBR service
    mock_bbr_service = MagicMock()
    mock_bbr_service.has_bbr.return_value = False
    mock_bbr_service.generate_bbr = AsyncMock(
        return_value={"task_id": "mock-task", "status": "started"}
    )
    mock_bbr_service.get_bbr = AsyncMock(
        return_value={"id": "mock-bbr", "content": "Mock BBR content"}
    )
    mock_bbr_service.delete_bbr = AsyncMock(return_value={"success": True})

    # Create mock Poem service
    mock_poem_service = MagicMock()
    mock_poem_service.get_recent_activity = AsyncMock(return_value={"poems": []})

    # Create mock Workflow service
    mock_workflow_service = MagicMock()
    mock_workflow_service.start_workflow = AsyncMock(
        return_value={"task_id": "mock-workflow", "status": "started"}
    )
    mock_workflow_service.start_translation_workflow = AsyncMock(
        return_value="mock-task-id"
    )

    # Create test Repository service that uses test database session
    from src.vpsweb.repository.service import RepositoryWebService

    test_repository_service = RepositoryWebService(db_session)

    # Patch the container's resolve method for multiple services
    from vpsweb.webui.services.interfaces import (
        IBBRServiceV2,
        IPoemServiceV2,
        IWorkflowServiceV2,
    )

    # Store original resolve method before patching
    original_container_resolve = container.resolve

    def mock_resolve(self, dependency_type):
        if dependency_type == IBBRServiceV2:
            return mock_bbr_service
        elif dependency_type == IPoemServiceV2:
            return mock_poem_service
        elif dependency_type == IWorkflowServiceV2:
            return mock_workflow_service
        # CRITICAL: Ensure container services use test database, not production!
        # This prevents tests from writing to production database
        try:
            original_service = original_container_resolve(dependency_type)
            # Override repository service with test database
            if hasattr(original_service, "repository_service"):
                original_service.repository_service = test_repository_service
            # Override any direct repository access
            if hasattr(original_service, "repo"):
                original_service.repo = test_repository_service.repo
            if hasattr(original_service, "poems"):
                original_service.poems = test_repository_service.poems
            if hasattr(original_service, "translations"):
                original_service.translations = test_repository_service.translations
            return original_service
        except:
            # Fall back to test repository service for direct RepositoryService requests
            if dependency_type == RepositoryService:
                return test_repository_service
            # Fall back to original resolve for unknown dependencies
            return original_container_resolve(dependency_type)

    # Apply the patch to the container
    container.resolve = mock_resolve.__get__(container, type(container))

    # Create test client
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def repository_service(db_session) -> RepositoryService:
    """
    Create a repository service for testing.

    Args:
        db_session: Synchronous database session (matching production)

    Returns:
        RepositoryService: Repository service instance
    """
    return RepositoryService(db_session)


@pytest.fixture
def repository_web_service(db_session) -> RepositoryWebService:
    """
    Create a repository web service for testing.

    Args:
        db_session: Synchronous database session (matching production)

    Returns:
        RepositoryWebService: Repository web service instance
    """
    return RepositoryWebService(db_session)


@pytest.fixture
def poem_service(repository_service: RepositoryService) -> PoemService:
    """
    Create a poem service for testing.

    Args:
        repository_service: Repository service instance

    Returns:
        PoemService: Poem service instance
    """
    return PoemService(repository_service.db)


# Sample data fixtures for database testing
@pytest.fixture
def sample_poem_data():
    """Sample poem data for database testing."""
    return {
        "poet_name": "Test Poet",
        "poem_title": "Test Poem Title",
        "source_language": "en",
        "original_text": """The fog comes
on little cat feet.
It sits looking
over harbor and city
on silent haunches
and then moves on.""",
        "metadata_json": '{"author_birth_year": 1990, "genre": "modern"}',
    }


@pytest.fixture
def sample_chinese_poem_data():
    """Sample Chinese poem data for database testing."""
    return {
        "poet_name": "李白",
        "poem_title": "静夜思",
        "source_language": "zh-CN",
        "original_text": """床前明月光，
疑是地上霜。
举头望明月，
低头思故乡。""",
        "metadata_json": '{"dynasty": "Tang", "genre": "classical"}',
    }


@pytest.fixture
def sample_translation_data():
    """Sample translation data for database testing."""
    return {
        "target_language": "Chinese",
        "translated_text": """雾来了，
踏着猫的细步。
它静静地蹲伏着，
俯视海港和城市，
再向前走去。""",
        "translator_type": "ai",
        "translator_info": "VPSWeb AI Translator",
    }


@pytest.fixture
def sample_workflow_task_data():
    """Sample workflow task data for testing."""
    return {
        "source_lang": "English",
        "target_lang": "Chinese",
        "workflow_mode": "hybrid",
        "status": "pending",
        "progress_percentage": 0,
    }


# Database entity fixtures
@pytest.fixture
def sample_poem(db_session, sample_poem_data):
    """Create a sample poem in the database."""
    import uuid

    from vpsweb.repository.models import Poem

    poem_data = sample_poem_data.copy()
    poem_data["id"] = str(uuid.uuid4())[:26]  # Generate ULID-like ID

    poem = Poem(**poem_data)
    db_session.add(poem)
    db_session.commit()
    db_session.refresh(poem)

    return poem


@pytest.fixture
def sample_chinese_poem(db_session, sample_chinese_poem_data):
    """Create a sample Chinese poem in the database."""
    import uuid

    from vpsweb.repository.models import Poem

    poem_data = sample_chinese_poem_data.copy()
    poem_data["id"] = str(uuid.uuid4())[:26]  # Generate ULID-like ID

    poem = Poem(**poem_data)
    db_session.add(poem)
    db_session.commit()
    db_session.refresh(poem)

    return poem


@pytest.fixture
def sample_translation(db_session, sample_poem, sample_translation_data):
    """Create a sample translation in the database."""
    import uuid

    from vpsweb.repository.models import Translation

    translation_data = sample_translation_data.copy()
    translation_data["id"] = str(uuid.uuid4())[:26]  # Generate ULID-like ID
    translation_data["poem_id"] = sample_poem.id

    translation = Translation(**translation_data)
    db_session.add(translation)
    db_session.commit()
    db_session.refresh(translation)

    return translation


# Test data generators
@pytest.fixture
def poem_generator():
    """Generate multiple test poems."""

    def _generate_poems(count: int = 5):
        poems = []
        for i in range(count):
            poem = {
                "poet_name": f"Poet {i+1}",
                "poem_title": f"Test Poem {i+1}",
                "source_language": "English" if i % 2 == 0 else "Chinese",
                "original_text": f"This is test poem number {i+1} with sufficient content for validation. "
                * 3,
                "metadata_json": f'{{"test_index": {i+1}}}',
            }
            poems.append(poem)
        return poems

    return _generate_poems


@pytest.fixture
def translation_generator():
    """Generate multiple test translations."""

    def _generate_translations(poem_ids: list, target_lang: str = "Chinese"):
        translations = []
        for i, poem_id in enumerate(poem_ids):
            translation = {
                "poem_id": poem_id,
                "target_language": target_lang,
                "translated_text": f"This is translation {i+1} for poem {poem_id}. "
                * 2,
                "translator_type": "ai",
                "translator_info": f"Test Translator {i+1}",
            }
            translations.append(translation)
        return translations

    return _generate_translations


# Testing utilities
class TestDataFactory:
    """Factory for creating test data."""

    @staticmethod
    def create_poem(**overrides):
        """Create a poem with default values."""
        default_data = {
            "poet_name": "Test Poet",
            "poem_title": "Test Poem",
            "source_language": "en",
            "original_text": "Test poem content for testing purposes.",
            "metadata_json": "{}",
        }
        default_data.update(overrides)
        return default_data

    @staticmethod
    def create_translation(poem_id: str, **overrides):
        """Create a translation with default values."""
        default_data = {
            "poem_id": poem_id,
            "target_language": "Chinese",
            "translated_text": "测试翻译内容",
            "translator_type": "ai",
            "translator_info": "Test Translator",
        }
        default_data.update(overrides)
        return default_data


@pytest.fixture
def test_data_factory():
    """Create a test data factory."""
    return TestDataFactory()


# Async test context helper
class AsyncTestContext:
    """Helper class for test context management."""

    def __init__(self, session):
        self.session = session

    def create_poem(self, **kwargs):
        """Create a poem with default values."""
        import uuid

        from vpsweb.repository.models import Poem

        default_data = TestDataFactory.create_poem()
        # Use time + random for better uniqueness across test runs
        import random
        import time

        unique_id = f"test_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"[:26]
        default_data["id"] = unique_id
        default_data.update(kwargs)

        poem = Poem(**default_data)
        self.session.add(poem)
        self.session.flush()  # Don't commit - use flush to make object available in current transaction
        self.session.refresh(poem)
        return poem

    def create_translation(self, poem_id: str, **kwargs):
        """Create a translation with default values."""
        import uuid

        from vpsweb.repository.models import Translation

        default_data = TestDataFactory.create_translation(poem_id)
        # Use time + random for better uniqueness across test runs
        import random
        import time

        unique_id = f"tr_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"[:26]
        default_data["id"] = unique_id
        default_data.update(kwargs)

        translation = Translation(**default_data)
        self.session.add(translation)
        self.session.flush()  # Don't commit - use flush to make object available in current transaction
        self.session.refresh(translation)
        return translation


@pytest.fixture
def test_context(db_session):
    """Create a test context helper."""
    yield AsyncTestContext(db_session)


@pytest.fixture
async def async_test_context(db_session_async):
    """Create an async test context helper with async session."""
    yield AsyncTestContext(db_session_async)


# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Utility for timing test execution."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return Timer()


# Session-scoped fixture to ensure repository_root directory exists
@pytest.fixture(scope="session", autouse=True)
def ensure_repository_root_exists():
    """
    Ensure the repository_root directory exists before any tests run.

    This is needed because the global database engine in database.py
    is initialized with a file-based database URL. Even though tests
    override get_db to use an in-memory database, if any code touches
    the global engine, it will fail if the directory doesn't exist.

    This fixture runs automatically before all tests.
    """
    from pathlib import Path

    repo_root = Path("repository_root")
    repo_root.mkdir(exist_ok=True)

    # Also create the data subdirectory if needed
    data_path = repo_root / "data"
    data_path.mkdir(exist_ok=True)

    yield

    # Cleanup after all tests complete
    # Note: We don't remove the directory as it might be used by other processes


# Enhanced pytest markers
def pytest_configure(config):
    """Configure enhanced custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (require database)"
    )
    config.addinivalue_line("markers", "slow: Slow tests (marked for CI)")
    config.addinivalue_line("markers", "repository: Repository layer tests")
    config.addinivalue_line("markers", "webui: Web UI tests")
    config.addinivalue_line("markers", "workflow: Workflow tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line(
        "markers", "database: Database tests (requires in-memory DB)"
    )
