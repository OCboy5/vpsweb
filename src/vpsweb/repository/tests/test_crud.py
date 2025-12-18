"""
Unit tests for VPSWeb Repository CRUD Operations v0.3.1

Tests for the CRUD operations: CRUDPoem, CRUDTranslation, CRUDAILog, CRUDHumanNote
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ..crud import (
    RepositoryService,
)
from ..models import Base
from ..schemas import (
    AILogCreate,
    HumanNoteCreate,
    PoemCreate,
    PoemUpdate,
    TranslationCreate,
    TranslationUpdate,
    TranslatorType,
    WorkflowMode,
)


# Test database setup
@pytest.fixture
def db_session():
    """Create a test database session"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    session = TestingSessionLocal()

    yield session

    session.close()


@pytest.fixture
def repository_service(db_session):
    """Create repository service instance"""
    return RepositoryService(db_session)


@pytest.fixture
def poem_create_data():
    """Sample poem creation data"""
    return PoemCreate(
        poet_name="李白",
        poem_title="靜夜思",
        source_language="zh-CN",
        original_text="床前明月光，疑是地上霜。舉頭望明月，低頭思故鄉。",
        metadata_json='{"dynasty": "唐", "theme": "思鄉"}',
    )


@pytest.fixture
def translation_create_data():
    """Sample translation creation data"""
    return TranslationCreate(
        poem_id="test_poem_id",
        translator_type=TranslatorType.AI,
        translator_info="gpt-4",
        target_language="en",
        translated_text="Before my bed, the bright moonlight shines. I wonder if it's frost on the ground. I raise my head to gaze at the bright moon, then lower it thinking of my hometown.",
        quality_rating=4,
    )


@pytest.fixture
def ai_log_create_data():
    """Sample AI log creation data"""
    return AILogCreate(
        translation_id="test_translation_id",
        model_name="gpt-4",
        workflow_mode=WorkflowMode.REASONING,
        runtime_seconds=8.7,
        token_usage_json='{"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200}',
        cost_info_json='{"total_cost": 0.004, "currency": "USD"}',
        notes="Translation completed with good quality",
    )


class TestCRUDPoem:
    """Test cases for CRUDPoem operations"""

    def test_create_poem(self, repository_service, poem_create_data):
        """Test creating a poem"""
        poem = repository_service.poems.create(poem_create_data)

        assert poem.id is not None
        assert poem.poet_name == poem_create_data.poet_name
        assert poem.poem_title == poem_create_data.poem_title
        assert poem.source_language == poem_create_data.source_language
        assert poem.original_text == poem_create_data.original_text
        assert poem.metadata_json == poem_create_data.metadata_json
        assert poem.created_at is not None
        assert poem.updated_at is not None

    def test_get_poem_by_id(self, repository_service, poem_create_data):
        """Test getting poem by ID"""
        # Create poem
        created_poem = repository_service.poems.create(poem_create_data)

        # Get poem by ID
        retrieved_poem = repository_service.poems.get_by_id(created_poem.id)

        assert retrieved_poem is not None
        assert retrieved_poem.id == created_poem.id
        assert retrieved_poem.poet_name == created_poem.poet_name
        assert retrieved_poem.poem_title == created_poem.poem_title

    def test_get_nonexistent_poem(self, repository_service):
        """Test getting non-existent poem"""
        poem = repository_service.poems.get_by_id("non_existent_id")
        assert poem is None

    def test_get_multiple_poems(self, repository_service, poem_create_data):
        """Test getting multiple poems"""
        # Create multiple poems
        poem1_data = poem_create_data.model_copy()
        poem1_data.poet_name = "李白"
        poem1_data.poem_title = "靜夜思"

        poem2_data = poem_create_data.model_copy()
        poem2_data.poet_name = "杜甫"
        poem2_data.poem_title = "春望"

        repository_service.poems.create(poem1_data)
        repository_service.poems.create(poem2_data)

        # Get all poems
        poems = repository_service.poems.get_multi()

        assert len(poems) == 2
        poem_titles = [p.poem_title for p in poems]
        assert "靜夜思" in poem_titles
        assert "春望" in poem_titles

    def test_filter_poems_by_poet(self, repository_service, poem_create_data):
        """Test filtering poems by poet name"""
        # Create poems by different poets
        poem1_data = poem_create_data.model_copy()
        poem1_data.poet_name = "李白"
        poem1_data.poem_title = "靜夜思"

        poem2_data = poem_create_data.model_copy()
        poem2_data.poet_name = "杜甫"
        poem2_data.poem_title = "春望"

        repository_service.poems.create(poem1_data)
        repository_service.poems.create(poem2_data)

        # Filter by poet
        li_bai_poems = repository_service.poems.get_multi(poet_name="李白")
        du_fu_poems = repository_service.poems.get_multi(poet_name="杜甫")

        assert len(li_bai_poems) == 1
        assert len(du_fu_poems) == 1
        assert li_bai_poems[0].poet_name == "李白"
        assert du_fu_poems[0].poet_name == "杜甫"

    def test_update_poem(self, repository_service, poem_create_data):
        """Test updating a poem"""
        # Create poem
        poem = repository_service.poems.create(poem_create_data)

        # Update poem
        update_data = PoemUpdate(
            poet_name="李白 (修改)",
            poem_title="靜夜思 (修改版)",
            original_text=poem.original_text + " (Additional text)",
        )

        updated_poem = repository_service.poems.update(poem.id, update_data)

        assert updated_poem is not None
        assert updated_poem.poet_name == "李白 (修改)"
        assert updated_poem.poem_title == "靜夜思 (修改版)"
        assert "Additional text" in updated_poem.original_text

    def test_update_nonexistent_poem(self, repository_service):
        """Test updating non-existent poem"""
        update_data = PoemUpdate(poet_name="Updated")
        result = repository_service.poems.update("non_existent", update_data)
        assert result is None

    def test_delete_poem(self, repository_service, poem_create_data):
        """Test deleting a poem"""
        # Create poem
        poem = repository_service.poems.create(poem_create_data)

        # Delete poem
        deleted = repository_service.poems.delete(poem.id)

        assert deleted is True

        # Verify deletion
        retrieved_poem = repository_service.poems.get_by_id(poem.id)
        assert retrieved_poem is None

    def test_delete_nonexistent_poem(self, repository_service):
        """Test deleting non-existent poem"""
        deleted = repository_service.poems.delete("non_existent")
        assert deleted is False

    def test_count_poems(self, repository_service, poem_create_data):
        """Test counting poems"""
        # Initially should be 0
        assert repository_service.poems.count() == 0

        # Create poems
        repository_service.poems.create(poem_create_data)
        assert repository_service.poems.count() == 1

        # Create another poem
        poem2_data = poem_create_data.model_copy()
        poem2_data.poem_title = "Another Poem"
        repository_service.poems.create(poem2_data)
        assert repository_service.poems.count() == 2


class TestCRUDTranslation:
    """Test cases for CRUDTranslation operations"""

    def test_create_translation(
        self, repository_service, poem_create_data, translation_create_data
    ):
        """Test creating a translation"""
        # Create poem first
        poem = repository_service.poems.create(poem_create_data)

        # Update translation data with correct poem_id
        translation_create_data.poem_id = poem.id

        # Create translation
        translation = repository_service.translations.create(
            translation_create_data
        )

        assert translation.id is not None
        assert translation.poem_id == poem.id
        assert (
            translation.translator_type
            == translation_create_data.translator_type
        )
        assert (
            translation.target_language
            == translation_create_data.target_language
        )
        assert (
            translation.translated_text
            == translation_create_data.translated_text
        )
        assert translation.created_at is not None

    def test_get_translations_by_poem(
        self, repository_service, poem_create_data, translation_create_data
    ):
        """Test getting translations by poem"""
        # Create poem
        poem = repository_service.poems.create(poem_create_data)

        # Create multiple translations for the poem
        translation_create_data.poem_id = poem.id
        translation_create_data.translator_type = TranslatorType.AI
        translation_create_data.translator_info = "gpt-4"
        ai_translation = repository_service.translations.create(
            translation_create_data
        )

        translation_create_data.translator_type = TranslatorType.HUMAN
        translation_create_data.translator_info = "John Translator"
        human_translation = repository_service.translations.create(
            translation_create_data
        )

        # Get translations by poem
        translations = repository_service.translations.get_by_poem(poem.id)

        assert len(translations) == 2
        assert ai_translation in translations
        assert human_translation in translations

    def test_filter_translations_by_type(
        self, repository_service, poem_create_data, translation_create_data
    ):
        """Test filtering translations by type"""
        # Create poem
        poem = repository_service.poems.create(poem_create_data)

        # Create AI translation
        translation_create_data.poem_id = poem.id
        translation_create_data.translator_type = TranslatorType.AI
        repository_service.translations.create(translation_create_data)

        # Filter by translator type
        ai_translations = repository_service.translations.get_multi(
            translator_type=TranslatorType.AI
        )
        human_translations = repository_service.translations.get_multi(
            translator_type=TranslatorType.HUMAN
        )

        assert len(ai_translations) == 1
        assert len(human_translations) == 0
        assert ai_translations[0].translator_type == TranslatorType.AI

    def test_update_translation(
        self, repository_service, poem_create_data, translation_create_data
    ):
        """Test updating a translation"""
        # Create poem and translation
        poem = repository_service.poems.create(poem_create_data)
        translation_create_data.poem_id = poem.id
        translation = repository_service.translations.create(
            translation_create_data
        )

        # Update translation
        update_data = TranslationUpdate(
            quality_rating=5,
            translated_text=translation.translated_text
            + " (Improved version)",
        )

        updated_translation = repository_service.translations.update(
            translation.id, update_data
        )

        assert updated_translation is not None
        assert updated_translation.quality_rating == 5
        assert "Improved version" in updated_translation.translated_text


class TestCRUDAILog:
    """Test cases for CRUDAILog operations"""

    def test_create_ai_log(
        self,
        repository_service,
        poem_create_data,
        translation_create_data,
        ai_log_create_data,
    ):
        """Test creating an AI log"""
        # Create poem and translation first
        poem = repository_service.poems.create(poem_create_data)
        translation_create_data.poem_id = poem.id
        translation = repository_service.translations.create(
            translation_create_data
        )

        # Update AI log data with correct translation_id
        ai_log_create_data.translation_id = translation.id

        # Create AI log
        ai_log = repository_service.ai_logs.create(ai_log_create_data)

        assert ai_log.id is not None
        assert ai_log.translation_id == translation.id
        assert ai_log.model_name == ai_log_create_data.model_name
        assert ai_log.workflow_mode == ai_log_create_data.workflow_mode
        assert ai_log.runtime_seconds == ai_log_create_data.runtime_seconds

    def test_get_ai_logs_by_translation(
        self,
        repository_service,
        poem_create_data,
        translation_create_data,
        ai_log_create_data,
    ):
        """Test getting AI logs by translation"""
        # Create poem and translation
        poem = repository_service.poems.create(poem_create_data)
        translation_create_data.poem_id = poem.id
        translation = repository_service.translations.create(
            translation_create_data
        )

        # Create multiple AI logs
        ai_log_create_data.translation_id = translation.id
        ai_log_create_data.model_name = "gpt-4"
        log1 = repository_service.ai_logs.create(ai_log_create_data)

        ai_log_create_data.model_name = "claude-3"
        log2 = repository_service.ai_logs.create(ai_log_create_data)

        # Get AI logs by translation
        logs = repository_service.ai_logs.get_by_translation(translation.id)

        assert len(logs) == 2
        assert log1 in logs
        assert log2 in logs

    def test_filter_ai_logs_by_model(
        self,
        repository_service,
        poem_create_data,
        translation_create_data,
        ai_log_create_data,
    ):
        """Test filtering AI logs by model"""
        # Create poem and translation
        poem = repository_service.poems.create(poem_create_data)
        translation_create_data.poem_id = poem.id
        translation = repository_service.translations.create(
            translation_create_data
        )

        # Create AI logs for different models
        ai_log_create_data.translation_id = translation.id
        ai_log_create_data.model_name = "gpt-4"
        repository_service.ai_logs.create(ai_log_create_data)

        ai_log_create_data.model_name = "claude-3"
        repository_service.ai_logs.create(ai_log_create_data)

        # Filter by model
        gpt_logs = repository_service.ai_logs.get_by_model("gpt-4")
        claude_logs = repository_service.ai_logs.get_by_model("claude-3")

        assert len(gpt_logs) == 1
        assert len(claude_logs) == 1
        assert gpt_logs[0].model_name == "gpt-4"
        assert claude_logs[0].model_name == "claude-3"


class TestCRUDHumanNote:
    """Test cases for CRUDHumanNote operations"""

    def test_create_human_note(
        self, repository_service, poem_create_data, translation_create_data
    ):
        """Test creating a human note"""
        # Create poem and translation first
        poem = repository_service.poems.create(poem_create_data)
        translation_create_data.poem_id = poem.id
        translation = repository_service.translations.create(
            translation_create_data
        )

        # Create human note
        note_data = HumanNoteCreate(
            translation_id=translation.id,
            note_text="This is an excellent translation that captures the poetic essence.",
        )

        note = repository_service.human_notes.create(note_data)

        assert note.id is not None
        assert note.translation_id == translation.id
        assert note.note_text == note_data.note_text
        assert note.created_at is not None

    def test_get_human_notes_by_translation(
        self, repository_service, poem_create_data, translation_create_data
    ):
        """Test getting human notes by translation"""
        # Create poem and translation
        poem = repository_service.poems.create(poem_create_data)
        translation_create_data.poem_id = poem.id
        translation = repository_service.translations.create(
            translation_create_data
        )

        # Create multiple human notes
        note1_data = HumanNoteCreate(
            translation_id=translation.id,
            note_text="First note: Good translation.",
        )
        note2_data = HumanNoteCreate(
            translation_id=translation.id,
            note_text="Second note: Could improve word choice.",
        )

        note1 = repository_service.human_notes.create(note1_data)
        note2 = repository_service.human_notes.create(note2_data)

        # Get notes by translation
        notes = repository_service.human_notes.get_by_translation(
            translation.id
        )

        assert len(notes) == 2
        assert note1 in notes
        assert note2 in notes

    def test_delete_human_note(
        self, repository_service, poem_create_data, translation_create_data
    ):
        """Test deleting a human note"""
        # Create poem and translation
        poem = repository_service.poems.create(poem_create_data)
        translation_create_data.poem_id = poem.id
        translation = repository_service.translations.create(
            translation_create_data
        )

        # Create note
        note_data = HumanNoteCreate(
            translation_id=translation.id, note_text="Test note for deletion."
        )
        note = repository_service.human_notes.create(note_data)

        # Delete note
        deleted = repository_service.human_notes.delete(note.id)

        assert deleted is True

        # Verify deletion
        retrieved_note = repository_service.human_notes.get_by_id(note.id)
        assert retrieved_note is None


class TestRepositoryService:
    """Test cases for RepositoryService"""

    def test_get_repository_stats(
        self, repository_service, poem_create_data, translation_create_data
    ):
        """Test getting repository statistics"""
        # Initially should be empty
        stats = repository_service.get_repository_stats()
        assert stats["total_poems"] == 0
        assert stats["total_translations"] == 0

        # Create poem
        poem = repository_service.poems.create(poem_create_data)

        # Create AI translation
        translation_create_data.poem_id = poem.id
        translation_create_data.translator_type = TranslatorType.AI
        repository_service.translations.create(translation_create_data)

        # Create human translation
        translation_create_data.translator_type = TranslatorType.HUMAN
        translation_create_data.translator_info = "Human Translator"
        repository_service.translations.create(translation_create_data)

        # Get updated stats
        stats = repository_service.get_repository_stats()

        assert stats["total_poems"] == 1
        assert stats["total_translations"] == 2
        assert stats["ai_translations"] == 1
        assert stats["human_translations"] == 1
        assert "zh-CN" in stats["languages"]
        assert stats["latest_translation"] is not None

    def test_search_poems(self, repository_service, poem_create_data):
        """Test searching poems"""
        # Create poems with different content
        poem1 = repository_service.poems.create(poem_create_data)

        poem2_data = poem_create_data.model_copy()
        poem2_data.poet_name = "杜甫"
        poem2_data.poem_title = "春望"
        poem2_data.original_text = "國破山河在，城春草木深。"
        poem2 = repository_service.poems.create(poem2_data)

        # Search by poet name
        results = repository_service.search_poems("李白")
        assert len(results) == 1
        assert results[0].id == poem1.id

        # Search by title
        results = repository_service.search_poems("春望")
        assert len(results) == 1
        assert results[0].id == poem2.id

        # Search by content
        results = repository_service.search_poems("山河")
        assert len(results) == 1
        assert results[0].id == poem2.id

    def test_get_poem_with_translations(
        self,
        repository_service,
        poem_create_data,
        translation_create_data,
        ai_log_create_data,
    ):
        """Test getting poem with all related data"""
        # Create poem
        poem = repository_service.poems.create(poem_create_data)

        # Create translation
        translation_create_data.poem_id = poem.id
        translation = repository_service.translations.create(
            translation_create_data
        )

        # Create AI log
        ai_log_create_data.translation_id = translation.id
        ai_log = repository_service.ai_logs.create(ai_log_create_data)

        # Create human note
        note_data = HumanNoteCreate(
            translation_id=translation.id,
            note_text="Excellent translation quality.",
        )
        note = repository_service.human_notes.create(note_data)

        # Get poem with all relations
        result = repository_service.get_poem_with_translations(poem.id)

        assert result is not None
        assert result["poem"].id == poem.id
        assert len(result["translations"]) == 1

        translation_data = result["translations"][0]
        assert translation_data["translation"].id == translation.id
        assert len(translation_data["ai_logs"]) == 1
        assert len(translation_data["human_notes"]) == 1
        assert translation_data["ai_logs"][0].id == ai_log.id
        assert translation_data["human_notes"][0].id == note.id

    def test_get_poem_with_translations_not_found(self, repository_service):
        """Test getting non-existent poem with translations"""
        result = repository_service.get_poem_with_translations("non_existent")
        assert result is None
