"""
Unit tests for VPSWeb Repository ORM Models v0.3.1

Tests for the SQLAlchemy ORM models: Poem, Translation, AILog, HumanNote
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ..models import AILog, Base, HumanNote, Poem, Translation
from ..schemas import TranslatorType, WorkflowMode


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
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    yield session

    session.close()


@pytest.fixture
def sample_poem():
    """Create a sample poem for testing"""
    return Poem(
        id="test_poem_001",
        poet_name="陶渊明",
        poem_title="歸園田居",
        source_language="zh-CN",
        original_text="採菊東籬下，悠然見南山。",
        metadata_json='{"dynasty": "東晉", "theme": "田園"}',
    )


@pytest.fixture
def sample_translation(sample_poem):
    """Create a sample translation for testing"""
    return Translation(
        id="test_trans_001",
        poem_id=sample_poem.id,
        translator_type=TranslatorType.AI,
        translator_info="gpt-4",
        target_language="en",
        translated_text="Picking chrysanthemums by the eastern fence, I calmly see the Southern Mountain.",
        quality_rating=5,
    )


@pytest.fixture
def sample_ai_log(sample_translation):
    """Create a sample AI log for testing"""
    return AILog(
        id="test_ai_log_001",
        translation_id=sample_translation.id,
        model_name="gpt-4",
        workflow_mode=WorkflowMode.REASONING,
        token_usage_json='{"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}',
        cost_info_json='{"total_cost": 0.003, "currency": "USD"}',
        runtime_seconds=12.5,
        notes="Translation completed successfully",
    )


@pytest.fixture
def sample_human_note(sample_translation):
    """Create a sample human note for testing"""
    return HumanNote(
        id="test_note_001",
        translation_id=sample_translation.id,
        note_text="This translation captures the poetic essence well. The imagery is preserved effectively.",
    )


class TestPoemModel:
    """Test cases for Poem model"""

    def test_create_poem(self, db_session, sample_poem):
        """Test creating a poem"""
        db_session.add(sample_poem)
        db_session.commit()
        db_session.refresh(sample_poem)

        assert sample_poem.id == "test_poem_001"
        assert sample_poem.poet_name == "陶渊明"
        assert sample_poem.poem_title == "歸園田居"
        assert sample_poem.source_language == "zh-CN"
        assert sample_poem.original_text == "採菊東籬下，悠然見南山。"
        assert sample_poem.metadata_json is not None
        assert sample_poem.created_at is not None
        assert sample_poem.updated_at is not None

    def test_poem_string_representation(self, sample_poem):
        """Test poem __repr__ method"""
        repr_str = repr(sample_poem)
        assert "Poem" in repr_str
        assert sample_poem.id in repr_str
        assert sample_poem.poem_title in repr_str
        assert sample_poem.poet_name in repr_str

    def test_poem_translation_count(self, db_session, sample_poem, sample_translation):
        """Test poem translation count property"""
        # Add poem and translation to database
        db_session.add(sample_poem)
        db_session.add(sample_translation)
        db_session.commit()

        # Test the relationship
        assert sample_poem.translation_count == 1
        assert sample_poem.ai_translation_count == 1
        assert sample_poem.human_translation_count == 0

    def test_poem_with_multiple_translations(self, db_session, sample_poem):
        """Test poem with multiple translations"""
        # Add poem
        db_session.add(sample_poem)
        db_session.commit()

        # Add AI translation
        ai_translation = Translation(
            id="test_ai_trans",
            poem_id=sample_poem.id,
            translator_type=TranslatorType.AI,
            translator_info="claude-3",
            target_language="en",
            translated_text="AI translation of the poem.",
        )
        db_session.add(ai_translation)

        # Add human translation
        human_translation = Translation(
            id="test_human_trans",
            poem_id=sample_poem.id,
            translator_type=TranslatorType.HUMAN,
            translator_info="John Translator",
            target_language="en",
            translated_text="Human translation of the poem.",
        )
        db_session.add(human_translation)
        db_session.commit()

        # Test counts
        assert sample_poem.translation_count == 2
        assert sample_poem.ai_translation_count == 1
        assert sample_poem.human_translation_count == 1


class TestTranslationModel:
    """Test cases for Translation model"""

    def test_create_translation(self, db_session, sample_poem, sample_translation):
        """Test creating a translation"""
        # Add poem first
        db_session.add(sample_poem)
        db_session.commit()

        # Add translation
        db_session.add(sample_translation)
        db_session.commit()
        db_session.refresh(sample_translation)

        assert sample_translation.id == "test_trans_001"
        assert sample_translation.poem_id == sample_poem.id
        assert sample_translation.translator_type == TranslatorType.AI
        assert sample_translation.translator_info == "gpt-4"
        assert sample_translation.target_language == "en"
        assert sample_translation.quality_rating == 5
        assert sample_translation.created_at is not None

    def test_translation_relationships(
        self,
        db_session,
        sample_poem,
        sample_translation,
        sample_ai_log,
        sample_human_note,
    ):
        """Test translation relationships with AI logs and human notes"""
        # Add all to database
        db_session.add(sample_poem)
        db_session.add(sample_translation)
        db_session.add(sample_ai_log)
        db_session.add(sample_human_note)
        db_session.commit()

        # Test relationships
        assert sample_translation.poem == sample_poem
        assert len(sample_translation.ai_logs) == 1
        assert len(sample_translation.human_notes) == 1
        assert sample_translation.ai_logs[0] == sample_ai_log
        assert sample_translation.human_notes[0] == sample_human_note

    def test_translation_properties(
        self, sample_translation, sample_ai_log, sample_human_note
    ):
        """Test translation helper properties"""
        # Set up relationships manually for testing
        sample_translation.ai_logs = [sample_ai_log]
        sample_translation.human_notes = [sample_human_note]

        assert sample_translation.has_ai_logs is True
        assert sample_translation.has_human_notes is True

    def test_translation_string_representation(self, sample_translation):
        """Test translation __repr__ method"""
        repr_str = repr(sample_translation)
        assert "Translation" in repr_str
        assert sample_translation.id in repr_str
        assert str(sample_translation.translator_type) in repr_str
        assert sample_translation.target_language in repr_str


class TestAILogModel:
    """Test cases for AILog model"""

    def test_create_ai_log(
        self, db_session, sample_poem, sample_translation, sample_ai_log
    ):
        """Test creating an AI log"""
        # Add poem and translation first
        db_session.add(sample_poem)
        db_session.add(sample_translation)
        db_session.commit()

        # Add AI log
        db_session.add(sample_ai_log)
        db_session.commit()
        db_session.refresh(sample_ai_log)

        assert sample_ai_log.id == "test_ai_log_001"
        assert sample_ai_log.translation_id == sample_translation.id
        assert sample_ai_log.model_name == "gpt-4"
        assert sample_ai_log.workflow_mode == WorkflowMode.REASONING
        assert sample_ai_log.runtime_seconds == 12.5
        assert sample_ai_log.created_at is not None

    def test_ai_log_relationship(
        self, db_session, sample_poem, sample_translation, sample_ai_log
    ):
        """Test AI log relationship with translation"""
        # Add all to database
        db_session.add(sample_poem)
        db_session.add(sample_translation)
        db_session.add(sample_ai_log)
        db_session.commit()

        # Test relationship
        assert sample_ai_log.translation == sample_translation

    def test_ai_log_properties(self, sample_ai_log):
        """Test AI log helper properties"""
        # Test token usage parsing
        assert sample_ai_log.token_usage is not None
        assert sample_ai_log.token_usage["total_tokens"] == 150

        # Test cost info parsing
        assert sample_ai_log.cost_info is not None
        assert sample_ai_log.cost_info["total_cost"] == 0.003

    def test_ai_log_empty_properties(self):
        """Test AI log with empty JSON properties"""
        ai_log = AILog(
            id="test_empty",
            translation_id="test_trans",
            model_name="test-model",
            workflow_mode=WorkflowMode.NON_REASONING,
        )

        assert ai_log.token_usage is None
        assert ai_log.cost_info is None

    def test_ai_log_string_representation(self, sample_ai_log):
        """Test AI log __repr__ method"""
        repr_str = repr(sample_ai_log)
        assert "AILog" in repr_str
        assert sample_ai_log.id in repr_str
        assert sample_ai_log.model_name in repr_str
        assert str(sample_ai_log.workflow_mode) in repr_str


class TestHumanNoteModel:
    """Test cases for HumanNote model"""

    def test_create_human_note(
        self, db_session, sample_poem, sample_translation, sample_human_note
    ):
        """Test creating a human note"""
        # Add poem and translation first
        db_session.add(sample_poem)
        db_session.add(sample_translation)
        db_session.commit()

        # Add human note
        db_session.add(sample_human_note)
        db_session.commit()
        db_session.refresh(sample_human_note)

        assert sample_human_note.id == "test_note_001"
        assert sample_human_note.translation_id == sample_translation.id
        assert (
            sample_human_note.note_text
            == "This translation captures the poetic essence well. The imagery is preserved effectively."
        )
        assert sample_human_note.created_at is not None

    def test_human_note_relationship(
        self, db_session, sample_poem, sample_translation, sample_human_note
    ):
        """Test human note relationship with translation"""
        # Add all to database
        db_session.add(sample_poem)
        db_session.add(sample_translation)
        db_session.add(sample_human_note)
        db_session.commit()

        # Test relationship
        assert sample_human_note.translation == sample_translation

    def test_human_note_string_representation(self, sample_human_note):
        """Test human note __repr__ method"""
        repr_str = repr(sample_human_note)
        assert "HumanNote" in repr_str
        assert sample_human_note.id in repr_str
        assert sample_human_note.translation_id in repr_str


class TestModelConstraints:
    """Test model constraints and validations"""

    def test_poem_required_fields(self):
        """Test poem required field constraints"""
        # Missing required fields should raise errors
        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            poem = Poem()  # Missing all required fields
            # This would be caught at database level

    def test_translation_foreign_key_constraint(self, db_session):
        """Test translation foreign key constraint"""
        # Try to create translation with non-existent poem ID
        translation = Translation(
            id="test_invalid_fk",
            poem_id="non_existent_poem",
            translator_type=TranslatorType.AI,
            target_language="en",
            translated_text="Test translation",
        )

        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            db_session.add(translation)
            db_session.commit()

    def test_quality_rating_range(self):
        """Test quality rating field constraints"""
        # This would be enforced at application level via Pydantic
        # Database level, we're using CheckConstraint in the model
        pass  # Tested in validation tests

    def test_workflow_mode_enum(self):
        """Test workflow mode enum constraints"""
        # Test valid workflow modes
        for mode in [
            WorkflowMode.REASONING,
            WorkflowMode.NON_REASONING,
            WorkflowMode.HYBRID,
        ]:
            ai_log = AILog(
                id=f"test_{mode.value}",
                translation_id="test_trans",
                model_name="test-model",
                workflow_mode=mode,
            )
            assert ai_log.workflow_mode == mode

    def test_translator_type_enum(self):
        """Test translator type enum constraints"""
        # Test valid translator types
        for trans_type in [TranslatorType.AI, TranslatorType.HUMAN]:
            translation = Translation(
                id=f"test_{trans_type.value}",
                poem_id="test_poem",
                translator_type=trans_type,
                target_language="en",
                translated_text="Test translation",
            )
            assert translation.translator_type == trans_type
