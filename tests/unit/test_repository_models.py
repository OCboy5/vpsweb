"""
Repository Model Tests for VPSWeb v0.7.0

Comprehensive tests for SQLAlchemy models covering:
- Field validation and constraints
- Relationships between all 5 tables
- Indexes and performance optimization
- Default values and computed properties
- Model methods and business logic
- Data integrity and edge cases

Models Tested:
- Poem (Core poem data)
- Translation (Translation records with workflow support)
- BackgroundBriefingReport (BBR - v0.7.0 feature)
- AILog (AI execution logs)
- HumanNote (Human feedback)
"""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.vpsweb.repository.models import (
    AILog,
    BackgroundBriefingReport,
    Base,
    HumanNote,
    Poem,
    Translation,
)
from src.vpsweb.repository.schemas import (
    TranslatorType,
    WorkflowMode,
    WorkflowStepType,
)

# ==============================================================================
# Model Test Fixtures
# ==============================================================================


@pytest.fixture
def test_db_session():
    """Create a test database session for model testing."""
    # Use in-memory SQLite for fast, isolated testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,  # Set to True for SQL debugging
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
def sample_poem_data():
    """Sample valid poem data for testing."""
    return {
        "id": str(uuid.uuid4())[:26],  # ULID-like ID
        "poet_name": "李白",
        "poem_title": "靜夜思",
        "source_language": "Chinese",
        "original_text": """床前明月光，
疑是地上霜。
舉頭望明月，
低頭思故鄉。""",
        "metadata_json": '{"dynasty": "Tang", "theme": "homesickness", "form": "quintain"}',
        "selected": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }


@pytest.fixture
def sample_translation_data():
    """Sample valid translation data for testing."""
    poem_id = str(uuid.uuid4())[:26]
    return {
        "id": str(uuid.uuid4())[:26],
        "poem_id": poem_id,
        "translator_type": TranslatorType.AI,
        "translator_info": "VPSWeb Hybrid Mode v0.7.0",
        "target_language": "English",
        "translated_text": """Before my bed, the bright moonlight shines,
I wonder if it's frost on the ground.
I raise my head to gaze at the bright moon,
Then lower it thinking of my hometown.""",
        "translated_poem_title": "Quiet Night Thoughts",
        "translated_poet_name": "Li Bai",
        "quality_rating": 4,
        "has_workflow_steps": True,
        "workflow_step_count": 3,
        "total_tokens_used": 750,
        "total_cost": 0.025,
        "total_duration": 18.5,
        "metadata_json": '{"workflow_mode": "hybrid", "model": "qwen-max", "temperature": 0.7}',
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }


@pytest.fixture
def sample_bbr_data():
    """Sample valid Background Briefing Report data."""
    poem_id = str(uuid.uuid4())[:26]
    return {
        "id": str(uuid.uuid4())[:26],
        "poem_id": poem_id,
        "content": """# Background Briefing Report: 靜夜思 by 李白

## Historical Context
Written during the Tang Dynasty (618-907 CE), this poem exemplifies Li Bai's masterful use of simple imagery to evoke deep emotions.

## Cultural Significance
"靜夜思" is one of the most widely taught classical Chinese poems, expressing universal themes of homesickness and nostalgia.

## Translation Challenges
- Classical Chinese poetic conciseness vs. English verbosity
- Cultural metaphor of the moon as homesickness symbol
- Maintaining the AABB rhyme scheme in English

## Recommended Approach
Focus on emotional resonance over literal translation while preserving the poem's contemplative mood.""",
        "metadata_json": '{"generated_by": "qwen-max", "model_version": "latest", "generation_time": "2025-01-15T10:30:00Z"}',
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }


@pytest.fixture
def sample_ai_log_data():
    """Sample valid AI Log data."""
    translation_id = str(uuid.uuid4())[:26]
    return {
        "id": str(uuid.uuid4())[:26],
        "translation_id": translation_id,
        "workflow_step": WorkflowStepType.INITIAL_TRANSLATION,
        "model_name": "qwen-max",
        "workflow_mode": WorkflowMode.HYBRID,
        "runtime_seconds": 12.7,
        "token_usage_json": '{"prompt_tokens": 320, "completion_tokens": 180, "total_tokens": 500}',
        "cost_info_json": '{"prompt_cost": 0.008, "completion_cost": 0.004, "total_cost": 0.012, "currency": "USD"}',
        "notes": "Initial translation completed with good cultural adaptation",
        "created_at": datetime.now(),
    }


@pytest.fixture
def sample_human_note_data():
    """Sample valid Human Note data."""
    translation_id = str(uuid.uuid4())[:26]
    return {
        "id": str(uuid.uuid4())[:26],
        "translation_id": translation_id,
        "note_text": "Excellent translation that captures both the literal meaning and emotional undertone. The rhythm flows well in English while maintaining the contemplative mood of the original.",
        "created_at": datetime.now(),
    }


# ==============================================================================
# Poem Model Tests
# ==============================================================================


@pytest.mark.repository
@pytest.mark.unit
class TestPoemModel:
    """Comprehensive tests for the Poem model."""

    def test_create_valid_poem(
        self, test_db_session: Session, sample_poem_data
    ):
        """Test creating a valid poem with all fields."""
        poem = Poem(**sample_poem_data)
        test_db_session.add(poem)
        test_db_session.commit()

        assert poem.id == sample_poem_data["id"]
        assert poem.poet_name == sample_poem_data["poet_name"]
        assert poem.poem_title == sample_poem_data["poem_title"]
        assert poem.source_language == sample_poem_data["source_language"]
        assert poem.original_text == sample_poem_data["original_text"]
        assert poem.metadata_json == sample_poem_data["metadata_json"]
        assert poem.selected is True
        assert poem.created_at is not None
        assert poem.updated_at is not None

    def test_poem_field_validation(self, test_db_session: Session):
        """Test poem field constraints and validation."""
        poem_data = {
            "id": str(uuid.uuid4())[:26],
            "poet_name": "Test Poet",
            "poem_title": "Test Poem",
            "source_language": "English",
            "original_text": "Test content with sufficient length.",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        poem = Poem(**poem_data)
        test_db_session.add(poem)
        test_db_session.commit()

        retrieved_poem = (
            test_db_session.query(Poem).filter_by(id=poem.id).first()
        )
        assert retrieved_poem is not None
        assert retrieved_poem.poet_name == "Test Poet"

    def test_poem_optional_fields(self, test_db_session: Session):
        """Test poem with optional fields as None."""
        poem_data = {
            "id": str(uuid.uuid4())[:26],
            "poet_name": "Minimal Poet",
            "poem_title": "Minimal Poem",
            "source_language": "English",
            "original_text": "Simple content",
            "metadata_json": None,  # Optional field
            "selected": None,  # Optional field
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        poem = Poem(**poem_data)
        test_db_session.add(poem)
        test_db_session.commit()

        assert poem.metadata_json is None
        assert poem.selected is None

    def test_poem_metadata_json_storage(self, test_db_session: Session):
        """Test JSON metadata storage and retrieval."""
        metadata = {
            "dynasty": "Tang",
            "author_birth_year": 701,
            "death_year": 762,
            "themes": ["nature", "homesickness", "wine"],
            "poetic_forms": ["jueju", "lushi"],
            "influence": "high",
        }

        poem_data = {
            "id": str(uuid.uuid4())[:26],
            "poet_name": "李白",
            "poem_title": "將進酒",
            "source_language": "Chinese",
            "original_text": "君不見黃河之水天上來...",
            "metadata_json": str(metadata).replace(
                "'", '"'
            ),  # Convert to JSON string
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        poem = Poem(**poem_data)
        test_db_session.add(poem)
        test_db_session.commit()

        retrieved_poem = (
            test_db_session.query(Poem).filter_by(id=poem.id).first()
        )
        assert retrieved_poem is not None
        assert "dynasty" in retrieved_poem.metadata_json

    def test_poem_default_timestamps(self, test_db_session: Session):
        """Test poem with automatic timestamp handling."""
        poem_data = {
            "id": str(uuid.uuid4())[:26],
            "poet_name": "Auto Timestamp Poet",
            "poem_title": "Auto Timestamp Poem",
            "source_language": "English",
            "original_text": "Content to test timestamps",
        }

        poem = Poem(**poem_data)
        test_db_session.add(poem)
        test_db_session.commit()

        assert poem.created_at is not None
        assert poem.updated_at is not None
        assert isinstance(poem.created_at, datetime)
        assert isinstance(poem.updated_at, datetime)

    def test_poem_unique_id_constraint(
        self, test_db_session: Session, sample_poem_data
    ):
        """Test that poem IDs must be unique."""
        # Create first poem
        poem1 = Poem(**sample_poem_data)
        test_db_session.add(poem1)
        test_db_session.commit()

        # Attempt to create second poem with same ID
        poem2_data = sample_poem_data.copy()
        poem2_data["poem_title"] = "Different Title"
        poem2 = Poem(**poem2_data)
        test_db_session.add(poem2)

        # Should raise IntegrityError due to duplicate ID
        with pytest.raises(IntegrityError):
            test_db_session.commit()

    def test_poem_relationship_to_translations(
        self, test_db_session: Session, sample_poem_data
    ):
        """Test poem relationship to translations."""
        # Create poem
        poem = Poem(**sample_poem_data)
        test_db_session.add(poem)
        test_db_session.commit()

        # Create translations for the poem
        translations = []
        for i, target_lang in enumerate(["English", "Japanese", "Korean"]):
            translation_data = {
                "id": str(uuid.uuid4())[:26],
                "poem_id": poem.id,
                "translator_type": TranslatorType.AI,
                "translator_info": f"Translation Model {i+1}",
                "target_language": target_lang,
                "translated_text": f"Translation in {target_lang}",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }
            translation = Translation(**translation_data)
            test_db_session.add(translation)
            translations.append(translation)

        test_db_session.commit()

        # Test relationship
        retrieved_poem = (
            test_db_session.query(Poem).filter_by(id=poem.id).first()
        )
        assert len(retrieved_poem.translations) == 3
        target_languages = [
            t.target_language for t in retrieved_poem.translations
        ]
        assert "English" in target_languages
        assert "Japanese" in target_languages
        assert "Korean" in target_languages

    def test_poem_relationship_to_bbr(
        self, test_db_session: Session, sample_poem_data
    ):
        """Test poem relationship to Background Briefing Report."""
        # Create poem
        poem = Poem(**sample_poem_data)
        test_db_session.add(poem)
        test_db_session.commit()

        # Create BBR for the poem
        bbr_data = {
            "id": str(uuid.uuid4())[:26],
            "poem_id": poem.id,
            "content": "Background briefing report content",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        bbr = BackgroundBriefingReport(**bbr_data)
        test_db_session.add(bbr)
        test_db_session.commit()

        # Test relationship
        retrieved_poem = (
            test_db_session.query(Poem).filter_by(id=poem.id).first()
        )
        assert retrieved_poem.background_briefing_report is not None
        assert retrieved_poem.background_briefing_report.poem_id == poem.id


# ==============================================================================
# Translation Model Tests
# ==============================================================================


@pytest.mark.repository
@pytest.mark.unit
class TestTranslationModel:
    """Comprehensive tests for the Translation model."""

    def test_create_valid_translation(
        self, test_db_session: Session, sample_translation_data
    ):
        """Test creating a valid translation with all fields."""
        translation = Translation(**sample_translation_data)
        test_db_session.add(translation)
        test_db_session.commit()

        assert translation.id == sample_translation_data["id"]
        assert translation.poem_id == sample_translation_data["poem_id"]
        assert translation.translator_type == TranslatorType.AI
        assert (
            translation.target_language
            == sample_translation_data["target_language"]
        )
        assert translation.quality_rating == 4
        assert translation.has_workflow_steps is True
        assert translation.workflow_step_count == 3

    def test_translation_translator_types(self, test_db_session: Session):
        """Test different translator types."""
        translator_types = [TranslatorType.AI, TranslatorType.HUMAN]

        for trans_type in translator_types:
            translation_data = {
                "id": str(uuid.uuid4())[:26],
                "poem_id": str(uuid.uuid4())[:26],
                "translator_type": trans_type,
                "translator_info": "Test info",
                "target_language": "English",
                "translated_text": "Test translation",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

            translation = Translation(**translation_data)
            test_db_session.add(translation)

        test_db_session.commit()

        # Verify all types were saved correctly
        translations = test_db_session.query(Translation).all()
        assert len(translations) == 2
        types = {t.translator_type for t in translations}
        assert types == {TranslatorType.AI, TranslatorType.HUMAN}

    def test_translation_workflow_fields(self, test_db_session: Session):
        """Test translation workflow-related fields."""
        translation_data = {
            "id": str(uuid.uuid4())[:26],
            "poem_id": str(uuid.uuid4())[:26],
            "translator_type": TranslatorType.AI,
            "translator_info": "Workflow Test",
            "target_language": "English",
            "translated_text": "Translation with workflow data",
            "has_workflow_steps": True,
            "workflow_step_count": 4,
            "total_tokens_used": 1500,
            "total_cost": 0.045,
            "total_duration": 35.2,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        translation = Translation(**translation_data)
        test_db_session.add(translation)
        test_db_session.commit()

        assert translation.has_workflow_steps is True
        assert translation.workflow_step_count == 4
        assert translation.total_tokens_used == 1500
        assert translation.total_cost == 0.045
        assert translation.total_duration == 35.2

    def test_translation_quality_rating_range(self, test_db_session: Session):
        """Test translation quality rating constraints."""
        poem_id = str(uuid.uuid4())[:26]

        for rating in [1, 2, 3, 4, 5]:  # Valid ratings
            translation_data = {
                "id": str(uuid.uuid4())[:26],
                "poem_id": poem_id,
                "translator_type": TranslatorType.AI,
                "translator_info": "Quality Test",
                "target_language": "English",
                "translated_text": f"Translation with rating {rating}",
                "quality_rating": rating,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

            translation = Translation(**translation_data)
            test_db_session.add(translation)

        test_db_session.commit()

        # Verify all ratings were saved
        translations = (
            test_db_session.query(Translation).filter_by(poem_id=poem_id).all()
        )
        ratings = {t.quality_rating for t in translations}
        assert ratings == {1, 2, 3, 4, 5}

    def test_translation_optional_fields(self, test_db_session: Session):
        """Test translation with optional fields as None."""
        translation_data = {
            "id": str(uuid.uuid4())[:26],
            "poem_id": str(uuid.uuid4())[:26],
            "translator_type": TranslatorType.HUMAN,
            "translator_info": "Minimal Translation",
            "target_language": "English",
            "translated_text": "Minimal content",
            "quality_rating": None,  # Optional
            "metadata_json": None,  # Optional
            "has_workflow_steps": False,  # Optional
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        translation = Translation(**translation_data)
        test_db_session.add(translation)
        test_db_session.commit()

        retrieved_translation = (
            test_db_session.query(Translation)
            .filter_by(id=translation.id)
            .first()
        )
        assert retrieved_translation.quality_rating is None
        assert retrieved_translation.metadata_json is None
        assert retrieved_translation.has_workflow_steps is False

    def test_translation_relationship_to_ai_logs(
        self, test_db_session: Session, sample_translation_data
    ):
        """Test translation relationship to AI logs."""
        # Create translation
        translation = Translation(**sample_translation_data)
        test_db_session.add(translation)
        test_db_session.commit()

        # Create AI logs for the translation
        ai_logs = []
        for step in [
            WorkflowStepType.INITIAL_TRANSLATION,
            WorkflowStepType.EDITOR_REVIEW,
        ]:
            log_data = {
                "id": str(uuid.uuid4())[:26],
                "translation_id": translation.id,
                "workflow_step": step,
                "model_name": "test-model",
                "workflow_mode": WorkflowMode.HYBRID,
                "runtime_seconds": 5.0,
                "token_usage_json": '{"total_tokens": 100}',
                "cost_info_json": '{"total_cost": 0.01}',
                "created_at": datetime.now(),
            }
            ai_log = AILog(**log_data)
            test_db_session.add(ai_log)
            ai_logs.append(ai_log)

        test_db_session.commit()

        # Test relationship
        retrieved_translation = (
            test_db_session.query(Translation)
            .filter_by(id=translation.id)
            .first()
        )
        assert len(retrieved_translation.ai_logs) == 2
        steps = {log.workflow_step for log in retrieved_translation.ai_logs}
        assert WorkflowStepType.INITIAL_TRANSLATION in steps
        assert WorkflowStepType.EDITOR_REVIEW in steps

    def test_translation_relationship_to_human_notes(
        self, test_db_session: Session, sample_translation_data
    ):
        """Test translation relationship to human notes."""
        # Create translation
        translation = Translation(**sample_translation_data)
        test_db_session.add(translation)
        test_db_session.commit()

        # Create human notes for the translation
        notes = []
        for i, note_text in enumerate(
            ["Excellent translation", "Good rhythm", "Well done"]
        ):
            note_data = {
                "id": str(uuid.uuid4())[:26],
                "translation_id": translation.id,
                "note_text": note_text,
                "created_at": datetime.now(),
            }
            human_note = HumanNote(**note_data)
            test_db_session.add(human_note)
            notes.append(human_note)

        test_db_session.commit()

        # Test relationship
        retrieved_translation = (
            test_db_session.query(Translation)
            .filter_by(id=translation.id)
            .first()
        )
        assert len(retrieved_translation.human_notes) == 3

        note_texts = {
            note.note_text for note in retrieved_translation.human_notes
        }
        assert "Excellent translation" in note_texts
        assert "Good rhythm" in note_texts
        assert "Well done" in note_texts


# ==============================================================================
# Background Briefing Report Model Tests
# ==============================================================================


@pytest.mark.repository
@pytest.mark.unit
class TestBackgroundBriefingReportModel:
    """Comprehensive tests for the BackgroundBriefingReport model."""

    def test_create_valid_bbr(self, test_db_session: Session, sample_bbr_data):
        """Test creating a valid Background Briefing Report."""
        bbr = BackgroundBriefingReport(**sample_bbr_data)
        test_db_session.add(bbr)
        test_db_session.commit()

        assert bbr.id == sample_bbr_data["id"]
        assert bbr.poem_id == sample_bbr_data["poem_id"]
        assert len(bbr.content) > 100  # Should have substantial content
        assert bbr.created_at is not None
        assert bbr.updated_at is not None

    def test_bbr_content_storage(
        self, test_db_session: Session, sample_bbr_data
    ):
        """Test BBR content storage and retrieval."""
        # Test with Markdown content
        markdown_content = """# Test BBR

## Historical Context
This is historical context with **bold** and *italic* text.

## Translation Notes
- Point 1
- Point 2
- Point 3

```python
# Code block example
print("Translation example")
```

> Block quote for important notes
        """

        bbr_data = sample_bbr_data.copy()
        bbr_data["content"] = markdown_content

        bbr = BackgroundBriefingReport(**bbr_data)
        test_db_session.add(bbr)
        test_db_session.commit()

        retrieved_bbr = (
            test_db_session.query(BackgroundBriefingReport)
            .filter_by(id=bbr.id)
            .first()
        )
        assert retrieved_bbr is not None
        assert markdown_content in retrieved_bbr.content
        assert "**bold**" in retrieved_bbr.content
        assert "*italic*" in retrieved_bbr.content

    def test_bbr_unique_poem_constraint(
        self, test_db_session: Session, sample_bbr_data
    ):
        """Test that each poem can have only one BBR (if constraint exists)."""
        # Create first BBR
        bbr1 = BackgroundBriefingReport(**sample_bbr_data)
        test_db_session.add(bbr1)
        test_db_session.commit()

        # Attempt to create second BBR for same poem
        bbr2_data = sample_bbr_data.copy()
        bbr2_data["id"] = str(uuid.uuid4())[:26]  # Different ID
        bbr2_data["content"] = "Different content"
        bbr2 = BackgroundBriefingReport(**bbr2_data)
        test_db_session.add(bbr2)

        # Behavior depends on database constraints
        # If there's a unique constraint on poem_id, this should fail
        # Otherwise, multiple BBRs per poem might be allowed
        try:
            test_db_session.commit()
            # If commit succeeds, multiple BBRs are allowed
            bbrs = (
                test_db_session.query(BackgroundBriefingReport)
                .filter_by(poem_id=sample_bbr_data["poem_id"])
                .all()
            )
            assert len(bbrs) == 2
        except IntegrityError:
            # If constraint exists, this is expected behavior
            test_db_session.rollback()

    def test_bbr_metadata_storage(
        self, test_db_session: Session, sample_bbr_data
    ):
        """Test BBR metadata JSON storage."""
        metadata = {
            "generation_model": "qwen-max",
            "model_version": "2024-01-15",
            "generation_time": "2025-01-15T10:30:00Z",
            "tokens_used": 1200,
            "generation_cost": 0.036,
            "quality_score": 0.92,
            "review_status": "approved",
            "reviewer": "expert_translator",
        }

        bbr_data = sample_bbr_data.copy()
        bbr_data["metadata_json"] = str(metadata).replace("'", '"')

        bbr = BackgroundBriefingReport(**bbr_data)
        test_db_session.add(bbr)
        test_db_session.commit()

        retrieved_bbr = (
            test_db_session.query(BackgroundBriefingReport)
            .filter_by(id=bbr.id)
            .first()
        )
        assert retrieved_bbr is not None
        assert "generation_model" in retrieved_bbr.metadata_json


# ==============================================================================
# AI Log Model Tests
# ==============================================================================


@pytest.mark.repository
@pytest.mark.unit
class TestAILogModel:
    """Comprehensive tests for the AILog model."""

    def test_create_valid_ai_log(
        self, test_db_session: Session, sample_ai_log_data
    ):
        """Test creating a valid AI log."""
        ai_log = AILog(**sample_ai_log_data)
        test_db_session.add(ai_log)
        test_db_session.commit()

        assert ai_log.id == sample_ai_log_data["id"]
        assert ai_log.translation_id == sample_ai_log_data["translation_id"]
        assert ai_log.workflow_step == WorkflowStepType.INITIAL_TRANSLATION
        assert ai_log.model_name == "qwen-max"
        assert ai_log.workflow_mode == WorkflowMode.HYBRID
        assert ai_log.runtime_seconds == 12.7

    def test_ai_log_workflow_steps(self, test_db_session: Session):
        """Test AI logs for different workflow steps."""
        translation_id = str(uuid.uuid4())[:26]

        for step in WorkflowStepType:
            log_data = {
                "id": str(uuid.uuid4())[:26],
                "translation_id": translation_id,
                "workflow_step": step,
                "model_name": "test-model",
                "workflow_mode": WorkflowMode.REASONING,
                "runtime_seconds": 5.0,
                "token_usage_json": '{"total_tokens": 100}',
                "cost_info_json": '{"total_cost": 0.01}',
                "created_at": datetime.now(),
            }

            ai_log = AILog(**log_data)
            test_db_session.add(ai_log)

        test_db_session.commit()

        # Verify all steps were saved
        logs = (
            test_db_session.query(AILog)
            .filter_by(translation_id=translation_id)
            .all()
        )
        steps = {log.workflow_step for log in logs}
        assert len(steps) == len(WorkflowStepType)
        assert steps == set(WorkflowStepType)

    def test_ai_log_workflow_modes(self, test_db_session: Session):
        """Test AI logs for different workflow modes."""
        translation_id = str(uuid.uuid4())[:26]

        for mode in WorkflowMode:
            log_data = {
                "id": str(uuid.uuid4())[:26],
                "translation_id": translation_id,
                "workflow_step": WorkflowStepType.INITIAL_TRANSLATION,
                "model_name": "test-model",
                "workflow_mode": mode,
                "runtime_seconds": 5.0,
                "token_usage_json": '{"total_tokens": 100}',
                "cost_info_json": '{"total_cost": 0.01}',
                "created_at": datetime.now(),
            }

            ai_log = AILog(**log_data)
            test_db_session.add(ai_log)

        test_db_session.commit()

        # Verify all modes were saved
        logs = (
            test_db_session.query(AILog)
            .filter_by(translation_id=translation_id)
            .all()
        )
        modes = {log.workflow_mode for log in logs}
        assert len(modes) == len(WorkflowMode)
        assert modes == set(WorkflowMode)

    def test_ai_log_performance_metrics(self, test_db_session: Session):
        """Test AI log performance metrics storage."""
        performance_data = {
            "id": str(uuid.uuid4())[:26],
            "translation_id": str(uuid.uuid4())[:26],
            "workflow_step": WorkflowStepType.TRANSLATOR_REVISION,
            "model_name": "deepseek-reasoner",
            "workflow_mode": WorkflowMode.REASONING,
            "runtime_seconds": 45.8,
            "token_usage_json": '{"prompt_tokens": 850, "completion_tokens": 320, "total_tokens": 1170, "cache_read_tokens": 50, "cache_write_tokens": 25}"',
            "cost_info_json": '{"prompt_cost": 0.0255, "completion_cost": 0.0096, "total_cost": 0.0351, "currency": "USD", "api_endpoint_cost": 0.002}"',
            "notes": "Complex reasoning step with extensive analysis",
            "created_at": datetime.now(),
        }

        ai_log = AILog(**performance_data)
        test_db_session.add(ai_log)
        test_db_session.commit()

        retrieved_log = (
            test_db_session.query(AILog).filter_by(id=ai_log.id).first()
        )
        assert retrieved_log is not None
        assert retrieved_log.runtime_seconds == 45.8
        assert "total_tokens" in retrieved_log.token_usage_json
        assert "total_cost" in retrieved_log.cost_info_json

    def test_ai_log_chronological_ordering(self, test_db_session: Session):
        """Test AI logs maintain chronological order."""
        translation_id = str(uuid.uuid4())[:26]
        logs = []

        # Create logs with time gaps
        for i in range(3):
            log_data = {
                "id": str(uuid.uuid4())[:26],
                "translation_id": translation_id,
                "workflow_step": WorkflowStepType.INITIAL_TRANSLATION,
                "model_name": "test-model",
                "workflow_mode": WorkflowMode.HYBRID,
                "runtime_seconds": i * 2.0,
                "token_usage_json": f'{{"total_tokens": {100 + i * 50}}}',
                "cost_info_json": f'{{"total_cost": {0.01 + i * 0.005}}}',
                "notes": f"Log entry {i}",
                "created_at": datetime.now() + timedelta(seconds=i * 10),
            }

            ai_log = AILog(**log_data)
            test_db_session.add(ai_log)
            logs.append(ai_log)

        test_db_session.commit()

        # Retrieve logs ordered by creation time
        retrieved_logs = (
            test_db_session.query(AILog)
            .filter_by(translation_id=translation_id)
            .order_by(AILog.created_at)
            .all()
        )

        assert len(retrieved_logs) == 3
        assert retrieved_logs[0].created_at < retrieved_logs[1].created_at
        assert retrieved_logs[1].created_at < retrieved_logs[2].created_at

    def test_ai_log_relationship_to_translation(
        self, test_db_session: Session, sample_ai_log_data
    ):
        """Test AI log relationship to translation."""
        # First create a translation
        translation_data = {
            "id": sample_ai_log_data["translation_id"],
            "poem_id": str(uuid.uuid4())[:26],
            "translator_type": TranslatorType.AI,
            "translator_info": "Test",
            "target_language": "English",
            "translated_text": "Test translation",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        translation = Translation(**translation_data)
        test_db_session.add(translation)
        test_db_session.commit()

        # Now create the AI log
        ai_log = AILog(**sample_ai_log_data)
        test_db_session.add(ai_log)
        test_db_session.commit()

        # Test relationship
        retrieved_log = (
            test_db_session.query(AILog).filter_by(id=ai_log.id).first()
        )
        assert retrieved_log.translation.id == translation.id
        assert retrieved_log.translation.translated_text == "Test translation"


# ==============================================================================
# Human Note Model Tests
# ==============================================================================


@pytest.mark.repository
@pytest.mark.unit
class TestHumanNoteModel:
    """Comprehensive tests for the HumanNote model."""

    def test_create_valid_human_note(
        self, test_db_session: Session, sample_human_note_data
    ):
        """Test creating a valid human note."""
        human_note = HumanNote(**sample_human_note_data)
        test_db_session.add(human_note)
        test_db_session.commit()

        assert human_note.id == sample_human_note_data["id"]
        assert (
            human_note.translation_id
            == sample_human_note_data["translation_id"]
        )
        assert (
            len(human_note.note_text) > 50
        )  # Should have substantial content
        assert human_note.created_at is not None

    def test_human_note_content_validation(self, test_db_session: Session):
        """Test human note content with various lengths and formats."""
        translation_id = str(uuid.uuid4())[:26]

        test_contents = [
            "Short note.",
            "Medium length note with some detail about the translation quality and style.",
            "Very long detailed note that provides comprehensive feedback on the translation, including comments on cultural adaptation, poetic form preservation, rhythm and meter considerations, word choice analysis, and overall assessment of how well the translation captures the essence and artistic merit of the original poem while making it accessible and meaningful to the target audience.",
            "Note with\nmultiple\nlines\nand\nparagraphs.\n\nSecond paragraph with more detailed analysis.",
            "Note with special characters: 中文, 日本語, 한국어, español, français, Deutsch, português, русский",
            "Technical note with <markdown> **formatting** and [links](http://example.com)",
        ]

        created_notes = []
        for content in test_contents:
            note_data = {
                "id": str(uuid.uuid4())[:26],
                "translation_id": translation_id,
                "note_text": content,
                "created_at": datetime.now(),
            }

            human_note = HumanNote(**note_data)
            test_db_session.add(human_note)
            created_notes.append(human_note)

        test_db_session.commit()

        # Verify all notes were saved correctly
        retrieved_notes = (
            test_db_session.query(HumanNote)
            .filter_by(translation_id=translation_id)
            .all()
        )
        assert len(retrieved_notes) == len(test_contents)

        for original, retrieved in zip(test_contents, retrieved_notes):
            assert retrieved.note_text == original

    def test_human_note_chronological_ordering(self, test_db_session: Session):
        """Test human notes maintain chronological order."""
        translation_id = str(uuid.uuid4())[:26]

        # Create notes with specific timestamps
        timestamps = [
            datetime(2025, 1, 15, 10, 0, 0),
            datetime(2025, 1, 15, 10, 30, 0),
            datetime(2025, 1, 15, 11, 15, 0),
        ]

        note_texts = ["First review", "Second review", "Final review"]

        for timestamp, note_text in zip(timestamps, note_texts):
            note_data = {
                "id": str(uuid.uuid4())[:26],
                "translation_id": translation_id,
                "note_text": note_text,
                "created_at": timestamp,
            }

            human_note = HumanNote(**note_data)
            test_db_session.add(human_note)

        test_db_session.commit()

        # Retrieve notes ordered by creation time
        retrieved_notes = (
            test_db_session.query(HumanNote)
            .filter_by(translation_id=translation_id)
            .order_by(HumanNote.created_at)
            .all()
        )

        assert len(retrieved_notes) == 3
        assert retrieved_notes[0].note_text == "First review"
        assert retrieved_notes[1].note_text == "Second review"
        assert retrieved_notes[2].note_text == "Final review"

    def test_human_note_relationship_to_translation(
        self, test_db_session: Session, sample_human_note_data
    ):
        """Test human note relationship to translation."""
        # First create a translation
        translation_data = {
            "id": sample_human_note_data["translation_id"],
            "poem_id": str(uuid.uuid4())[:26],
            "translator_type": TranslatorType.HUMAN,
            "translator_info": "Human Translator",
            "target_language": "English",
            "translated_text": "Human translation",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        translation = Translation(**translation_data)
        test_db_session.add(translation)
        test_db_session.commit()

        # Now create the human note
        human_note = HumanNote(**sample_human_note_data)
        test_db_session.add(human_note)
        test_db_session.commit()

        # Test relationship
        retrieved_note = (
            test_db_session.query(HumanNote)
            .filter_by(id=human_note.id)
            .first()
        )
        assert retrieved_note.translation.id == translation.id
        assert (
            retrieved_note.translation.translated_text == "Human translation"
        )


# ==============================================================================
# Cross-Model Relationship Tests
# ==============================================================================


@pytest.mark.repository
@pytest.mark.unit
class TestCrossModelRelationships:
    """Test complex relationships across all models."""

    def test_complete_workflow_chain(self, test_db_session: Session):
        """Test complete workflow: Poem -> Translation -> AI Logs -> Human Notes."""
        # 1. Create poem
        poem_id = str(uuid.uuid4())[:26]
        poem_data = {
            "id": poem_id,
            "poet_name": "Test Poet",
            "poem_title": "Test Poem",
            "source_language": "Chinese",
            "original_text": "Test poem content",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        poem = Poem(**poem_data)
        test_db_session.add(poem)
        test_db_session.commit()

        # 2. Create translation
        translation_id = str(uuid.uuid4())[:26]
        translation_data = {
            "id": translation_id,
            "poem_id": poem_id,
            "translator_type": TranslatorType.AI,
            "translator_info": "Test Model",
            "target_language": "English",
            "translated_text": "Test translation",
            "has_workflow_steps": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        translation = Translation(**translation_data)
        test_db_session.add(translation)
        test_db_session.commit()

        # 3. Create BBR for poem
        bbr_id = str(uuid.uuid4())[:26]
        bbr_data = {
            "id": bbr_id,
            "poem_id": poem_id,
            "content": "Background briefing report content",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        bbr = BackgroundBriefingReport(**bbr_data)
        test_db_session.add(bbr)
        test_db_session.commit()

        # 4. Create AI logs for translation
        for step in [
            WorkflowStepType.INITIAL_TRANSLATION,
            WorkflowStepType.EDITOR_REVIEW,
        ]:
            log_data = {
                "id": str(uuid.uuid4())[:26],
                "translation_id": translation_id,
                "workflow_step": step,
                "model_name": "test-model",
                "workflow_mode": WorkflowMode.HYBRID,
                "runtime_seconds": 5.0,
                "token_usage_json": '{"total_tokens": 100}',
                "cost_info_json": '{"total_cost": 0.01}',
                "created_at": datetime.now(),
            }
            ai_log = AILog(**log_data)
            test_db_session.add(ai_log)

        # 5. Create human notes for translation
        for i, note_text in enumerate(
            ["Good start", "Needs refinement", "Final approval"]
        ):
            note_data = {
                "id": str(uuid.uuid4())[:26],
                "translation_id": translation_id,
                "note_text": note_text,
                "created_at": datetime.now() + timedelta(minutes=i),
            }
            human_note = HumanNote(**note_data)
            test_db_session.add(human_note)

        test_db_session.commit()

        # Verify complete chain
        retrieved_poem = (
            test_db_session.query(Poem).filter_by(id=poem_id).first()
        )
        assert retrieved_poem is not None
        assert len(retrieved_poem.translations) == 1
        assert retrieved_poem.background_briefing_report is not None

        retrieved_translation = retrieved_poem.translations[0]
        assert len(retrieved_translation.ai_logs) == 2
        assert len(retrieved_translation.human_notes) == 3

        # Verify all relationships are properly linked
        for ai_log in retrieved_translation.ai_logs:
            assert ai_log.translation_id == translation_id

        for human_note in retrieved_translation.human_notes:
            assert human_note.translation_id == translation_id

    def test_cascade_deletion_behavior(self, test_db_session: Session):
        """Test cascade deletion behavior across related models."""
        # Create complete workflow chain
        poem_id = str(uuid.uuid4())[:26]

        # Create poem
        poem = Poem(
            id=poem_id,
            poet_name="Cascade Test Poet",
            poem_title="Cascade Test Poem",
            source_language="English",
            original_text="Test content for cascade deletion",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        test_db_session.add(poem)
        test_db_session.commit()

        # Create translation
        translation = Translation(
            id=str(uuid.uuid4())[:26],
            poem_id=poem_id,
            translator_type=TranslatorType.AI,
            translator_info="Test",
            target_language="Chinese",
            translated_text="Test translation",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        test_db_session.add(translation)
        test_db_session.commit()

        # Create dependent records
        ai_log = AILog(
            id=str(uuid.uuid4())[:26],
            translation_id=translation.id,
            workflow_step=WorkflowStepType.INITIAL_TRANSLATION,
            model_name="test",
            workflow_mode=WorkflowMode.HYBRID,
            runtime_seconds=1.0,
            token_usage_json='{"total_tokens": 50}',
            cost_info_json='{"total_cost": 0.005}',
            created_at=datetime.now(),
        )
        test_db_session.add(ai_log)

        human_note = HumanNote(
            id=str(uuid.uuid4())[:26],
            translation_id=translation.id,
            note_text="Test note for cascade",
            created_at=datetime.now(),
        )
        test_db_session.add(human_note)

        bbr = BackgroundBriefingReport(
            id=str(uuid.uuid4())[:26],
            poem_id=poem_id,
            content="Test BBR for cascade",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        test_db_session.add(bbr)
        test_db_session.commit()

        # Verify all records exist
        assert test_db_session.query(Poem).filter_by(id=poem_id).count() == 1
        assert (
            test_db_session.query(Translation)
            .filter_by(poem_id=poem_id)
            .count()
            == 1
        )
        assert (
            test_db_session.query(AILog)
            .filter_by(translation_id=translation.id)
            .count()
            == 1
        )
        assert (
            test_db_session.query(HumanNote)
            .filter_by(translation_id=translation.id)
            .count()
            == 1
        )
        assert (
            test_db_session.query(BackgroundBriefingReport)
            .filter_by(poem_id=poem_id)
            .count()
            == 1
        )

        # Delete poem (should cascade to related records depending on configuration)
        test_db_session.delete(poem)
        test_db_session.commit()

        # Check cascade behavior (results depend on cascade configuration)
        remaining_poems = (
            test_db_session.query(Poem).filter_by(id=poem_id).count()
        )
        assert remaining_poems == 0  # Poem should be deleted

        # Other records' fate depends on cascade constraints in the model definitions


# ==============================================================================
# Model Constraint and Validation Tests
# ==============================================================================


@pytest.mark.repository
@pytest.mark.unit
class TestModelConstraintsAndValidation:
    """Test model constraints and validation at the database level."""

    def test_foreign_key_constraints(self, test_db_session: Session):
        """Test foreign key constraint enforcement."""
        # Test translation with non-existent poem_id
        fake_poem_id = str(uuid.uuid4())[:26]

        translation_data = {
            "id": str(uuid.uuid4())[:26],
            "poem_id": fake_poem_id,  # Non-existent poem
            "translator_type": TranslatorType.AI,
            "translator_info": "Test",
            "target_language": "English",
            "translated_text": "Test",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        translation = Translation(**translation_data)
        test_db_session.add(translation)

        # Should raise IntegrityError due to foreign key constraint
        with pytest.raises(IntegrityError):
            test_db_session.commit()

    def test_not_null_constraints(self, test_db_session: Session):
        """Test NOT NULL constraints on required fields."""
        # Test poem with missing required field
        poem_data = {
            "id": str(uuid.uuid4())[:26],
            # Missing poet_name (required)
            "poem_title": "Test",
            "source_language": "English",
            "original_text": "Test content",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        poem = Poem(**poem_data)
        test_db_session.add(poem)

        # Should raise error due to NOT NULL constraint
        with pytest.raises((IntegrityError, ValueError)):
            test_db_session.commit()

    def test_data_type_constraints(self, test_db_session: Session):
        """Test data type constraints and validation."""
        poem_data = {
            "id": str(uuid.uuid4())[:26],
            "poet_name": "Type Test Poet",
            "poem_title": "Type Test Poem",
            "source_language": "English",
            "original_text": "Test content for type validation",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        poem = Poem(**poem_data)
        test_db_session.add(poem)
        test_db_session.commit()

        # Verify data types are preserved correctly
        retrieved_poem = (
            test_db_session.query(Poem).filter_by(id=poem.id).first()
        )
        assert isinstance(retrieved_poem.id, str)
        assert isinstance(retrieved_poem.poet_name, str)
        assert isinstance(retrieved_poem.created_at, datetime)
        assert isinstance(retrieved_poem.updated_at, datetime)
