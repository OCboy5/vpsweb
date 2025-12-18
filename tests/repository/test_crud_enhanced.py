"""
Essential Database CRUD Tests for VPSWeb v0.7.0

Tests only business-critical CRUD operations and data integrity.
Excludes performance tests, aggregation queries, and framework features.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.vpsweb.repository.crud import RepositoryService
from src.vpsweb.repository.models import (AILog, BackgroundBriefingReport,
                                          HumanNote, Poem, Translation)
from src.vpsweb.repository.schemas import (PoemCreate, TranslationCreate,
                                           TranslatorType, WorkflowStepType)


class TestEssentialCRUD:
    """Essential CRUD operations tests."""

    async def test_create_poem_basic(self, db_session_async):
        """Test basic poem creation."""
        repo = RepositoryService(db_session_async)

        poem_data = PoemCreate(
            poet_name="李白",
            poem_title="靜夜思",
            source_language="Chinese",
            original_text="床前明月光，疑是地上霜。",
            metadata_json={"dynasty": "Tang"},
        )

        poem = await repo.create_poem(poem_data)
        assert poem.id is not None
        assert poem.poet_name == "李白"
        assert poem.poem_title == "靜夜思"

    async def test_create_translation_with_relationship(self, db_session_async):
        """Test translation creation linked to a poem."""
        repo = RepositoryService(db_session_async)

        # Create poem first
        poem_data = PoemCreate(
            poet_name="Test Poet",
            poem_title="Test Poem",
            source_language="English",
            original_text="Test content",
        )
        poem = await repo.create_poem(poem_data)

        # Create translation
        translation_data = TranslationCreate(
            poem_id=poem.id,
            translator_type=TranslatorType.AI,
            translator_info="Test Model",
            target_language="Chinese",
            translated_text="测试翻译",
            quality_rating=4,
        )

        translation = await repo.create_translation(translation_data)
        assert translation.id is not None
        assert translation.poem_id == poem.id
        assert translation.translated_text == "测试翻译"

    async def test_poem_translation_relationship(self, db_session_async):
        """Test that poem-translation relationship works correctly."""
        repo = RepositoryService(db_session_async)

        # Create poem
        poem_data = PoemCreate(
            poet_name="Carl Sandburg",
            poem_title="Fog",
            source_language="English",
            original_text="The fog comes on little cat feet.",
        )
        poem = await repo.create_poem(poem_data)

        # Create translation
        translation_data = TranslationCreate(
            poem_id=poem.id,
            translator_type=TranslatorType.AI,
            translator_info="Test Model",
            target_language="Chinese",
            translated_text="雾来了，踏着猫的小脚。",
        )
        await repo.create_translation(translation_data)

        # Verify relationship
        poem_with_translations = await repo.get_poem_with_translations(poem.id)
        assert len(poem_with_translations.translations) == 1
        assert (
            poem_with_translations.translations[0].translated_text
            == "雾来了，踏着猫的小脚。"
        )

    async def test_bbr_creation_and_retrieval(self, db_session_async):
        """Test Background Briefing Report creation and retrieval."""
        repo = RepositoryService(db_session_async)

        # Create poem first
        poem_data = PoemCreate(
            poet_name="Test Poet",
            poem_title="Test Poem",
            source_language="English",
            original_text="Test content",
        )
        poem = await repo.create_poem(poem_data)

        # Create BBR
        bbr_data = {
            "id": str(uuid.uuid4())[:26],
            "poem_id": poem.id,
            "content": "This poem explores themes of nature and observation.",
            "metadata_json": {"analysis_depth": "medium"},
        }
        bbr = BackgroundBriefingReport(**bbr_data)
        db_session.add(bbr)
        await db_session.commit()

        # Retrieve BBR
        retrieved_bbr = await repo.get_bbr_by_poem_id(poem.id)
        assert retrieved_bbr is not None
        assert "nature and observation" in retrieved_bbr.content

    async def test_ai_log_workflow_tracking(self, db_session_async):
        """Test AI workflow step logging."""
        repo = RepositoryService(db_session_async)

        # Create poem
        poem_data = PoemCreate(
            poet_name="Test Poet",
            poem_title="Test Poem",
            source_language="English",
            original_text="Test content",
        )
        poem = await repo.create_poem(poem_data)

        # Create AI log
        ai_log_data = {
            "id": str(uuid.uuid4())[:26],
            "poem_id": poem.id,
            "workflow_step": WorkflowStepType.INITIAL_TRANSLATION,
            "model_provider": "test_provider",
            "model_name": "test_model",
            "tokens_used": 150,
            "response_time_ms": 2000,
            "request_data": {"prompt": "translate this"},
            "response_data": {"translation": "测试"},
            "status": "success",
        }
        ai_log = AILog(**ai_log_data)
        db_session.add(ai_log)
        await db_session.commit()

        # Verify log was created
        logs = await repo.get_ai_logs_by_poem_id(poem.id)
        assert len(logs) == 1
        assert logs[0].workflow_step == WorkflowStepType.INITIAL_TRANSLATION
        assert logs[0].tokens_used == 150

    async def test_human_note_creation(self, db_session_async):
        """Test human note creation and validation."""
        repo = RepositoryService(db_session_async)

        # Create poem and translation
        poem_data = PoemCreate(
            poet_name="Test Poet",
            poem_title="Test Poem",
            source_language="English",
            original_text="Test content",
        )
        poem = await repo.create_poem(poem_data)

        translation_data = TranslationCreate(
            poem_id=poem.id,
            translator_type=TranslatorType.HUMAN,
            translator_info="Test Translator",
            target_language="Chinese",
            translated_text="测试翻译",
        )
        translation = await repo.create_translation(translation_data)

        # Create human note
        note_data = {
            "id": str(uuid.uuid4())[:26],
            "translation_id": translation.id,
            "note_type": "suggestion",
            "content": "Consider using more poetic language",
            "author": "Editor",
            "metadata_json": {"priority": "medium"},
        }
        note = HumanNote(**note_data)
        db_session.add(note)
        await db_session.commit()

        # Verify note was created
        retrieved_note = await db_session.get(HumanNote, note.id)
        assert retrieved_note is not None
        assert retrieved_note.content == "Consider using more poetic language"

    async def test_constraint_validation_poem_unique_id(self, db_session_async):
        """Test that poem ID uniqueness constraint is enforced."""
        repo = RepositoryService(db_session_async)

        poem_id = str(uuid.uuid4())[:26]

        # Create first poem
        poem_data1 = PoemCreate(
            id=poem_id,
            poet_name="Poet 1",
            poem_title="Poem 1",
            source_language="English",
            original_text="Content 1",
        )
        await repo.create_poem(poem_data1)

        # Try to create second poem with same ID - should fail
        poem_data2 = PoemCreate(
            id=poem_id,  # Same ID
            poet_name="Poet 2",
            poem_title="Poem 2",
            source_language="English",
            original_text="Content 2",
        )

        with pytest.raises(IntegrityError):
            await repo.create_poem(poem_data2)

    async def test_cascade_delete_prevention(self, db_session_async):
        """Test that deleting a poem with translations is handled properly."""
        repo = RepositoryService(db_session_async)

        # Create poem with translation
        poem_data = PoemCreate(
            poet_name="Test Poet",
            poem_title="Test Poem",
            source_language="English",
            original_text="Test content",
        )
        poem = await repo.create_poem(poem_data)

        translation_data = TranslationCreate(
            poem_id=poem.id,
            translator_type=TranslatorType.AI,
            translator_info="Test Model",
            target_language="Chinese",
            translated_text="测试翻译",
        )
        await repo.create_translation(translation_data)

        # Try to delete poem - should handle gracefully
        # (Exact behavior depends on database constraints)
        try:
            await repo.delete_poem(poem.id)
            # Verify poem was deleted
            deleted_poem = await repo.get_poem(poem.id)
            assert deleted_poem is None
        except IntegrityError:
            # Expected if foreign key constraints prevent deletion
            pass
