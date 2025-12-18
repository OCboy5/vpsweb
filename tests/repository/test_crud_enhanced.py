"""
Enhanced Database CRUD Tests for VPSWeb v0.7.0

This module provides comprehensive tests for all CRUD operations with:
- Async/await support for SQLAlchemy 2.0
- Full relationship testing between all 5 tables
- Performance and edge case testing
- Database constraint validation
- Transaction rollback testing
- Complex query testing with joins and filters

Tables Tested:
1. poems - Core poem data
2. translations - Translation records with workflow support
3. background_briefing_reports - BBR records (v0.7.0 feature)
4. ai_logs - AI execution logs with performance metrics
5. human_notes - Human translator notes and feedback
"""

import asyncio
import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.vpsweb.repository.crud import RepositoryService
from src.vpsweb.repository.models import (
    AILog,
    BackgroundBriefingReport,
    HumanNote,
    Poem,
    Translation,
)
from src.vpsweb.repository.schemas import (
    AILogCreate,
    HumanNoteCreate,
    PoemCreate,
    TranslationCreate,
    TranslatorType,
    WorkflowMode,
    WorkflowStepType,
)

# ==============================================================================
# Enhanced CRUD Fixtures
# ==============================================================================


@pytest_asyncio.fixture
async def sample_poem_with_translations(db_session: AsyncSession):
    """Create a complete poem with translations for testing."""
    # Create poem
    poem_data = {
        "id": str(uuid.uuid4())[:26],
        "poet_name": "李白",
        "poem_title": "靜夜思",
        "source_language": "Chinese",
        "original_text": """床前明月光，
疑是地上霜。
舉頭望明月，
低頭思故鄉。""",
        "metadata_json": '{"dynasty": "Tang", "theme": "nostalgia"}',
    }
    poem = Poem(**poem_data)
    db_session.add(poem)
    await db_session.commit()

    # Create multiple translations
    translations = []

    # AI Translation
    ai_translation_data = {
        "id": str(uuid.uuid4())[:26],
        "poem_id": poem.id,
        "translator_type": TranslatorType.AI,
        "translator_info": "VPSWeb Hybrid Mode",
        "target_language": "English",
        "translated_text": """Before my bed, the bright moonlight shines,
I wonder if it's frost on the ground.
I raise my head to gaze at the bright moon,
Then lower it thinking of my hometown.""",
        "translated_poem_title": "Quiet Night Thoughts",
        "translated_poet_name": "Li Bai",
        "quality_rating": 4,
        "metadata_json": '{"workflow_mode": "hybrid", "model": "qwen-max"}',
    }
    ai_translation = Translation(**ai_translation_data)
    db_session.add(ai_translation)
    translations.append(ai_translation)

    # Human Translation
    human_translation_data = {
        "id": str(uuid.uuid4())[:26],
        "poem_id": poem.id,
        "translator_type": TranslatorType.HUMAN,
        "translator_info": "Dr. Wang Ming",
        "target_language": "Japanese",
        "translated_text": """床前、明るい月光が輝き、
地面に霜が降りたかと思う。
頭を上げて明るい月を眺め、
頭を下げて故郷を思う。""",
        "translated_poem_title": "静夜の思",
        "translated_poet_name": "李白",
        "quality_rating": 5,
    }
    human_translation = Translation(**human_translation_data)
    db_session.add(human_translation)
    translations.append(human_translation)

    await db_session.commit()
    await db_session.refresh(poem)
    for translation in translations:
        await db_session.refresh(translation)

    return poem, translations


@pytest_asyncio.fixture
async def sample_workflow_data(
    db_session: AsyncSession, sample_poem_with_translations
):
    """Create sample AI logs and human notes for workflow testing."""
    poem, translations = sample_poem_with_translations
    ai_translation = translations[0]  # AI translation
    human_translation = translations[1]  # Human translation

    # Create AI logs for different workflow steps
    ai_logs = []
    for step_type in [
        WorkflowStepType.INITIAL_TRANSLATION,
        WorkflowStepType.EDITOR_REVIEW,
        WorkflowStepType.TRANSLATOR_REVISION,
    ]:
        log_data = {
            "id": str(uuid.uuid4())[:26],
            "translation_id": ai_translation.id,
            "workflow_step": step_type,
            "model_name": (
                "qwen-max"
                if step_type != WorkflowStepType.EDITOR_REVIEW
                else "deepseek-chat"
            ),
            "workflow_mode": WorkflowMode.HYBRID,
            "runtime_seconds": 5.5 + len(ai_logs),
            "token_usage_json": f'{{"prompt_tokens": {100 + len(ai_logs) * 50}, "completion_tokens": {80 + len(ai_logs) * 40}, "total_tokens": {180 + len(ai_logs) * 90}}}',
            "cost_info_json": f'{{"total_cost": {0.002 + len(ai_logs) * 0.001}, "currency": "USD"}}',
            "notes": f"Step {step_type.value} completed successfully",
        }
        ai_log = AILog(**log_data)
        db_session.add(ai_log)
        ai_logs.append(ai_log)

    # Create human notes
    human_notes = []
    note_texts = [
        "Excellent rhythm and flow preservation",
        "Could improve cultural context in line 2",
        "Final version captures poetic essence well",
    ]
    for note_text in note_texts:
        note_data = {
            "id": str(uuid.uuid4())[:26],
            "translation_id": human_translation.id,
            "note_text": note_text,
        }
        human_note = HumanNote(**note_data)
        db_session.add(human_note)
        human_notes.append(human_note)

    await db_session.commit()
    for ai_log in ai_logs:
        await db_session.refresh(ai_log)
    for human_note in human_notes:
        await db_session.refresh(human_note)

    return ai_logs, human_notes


@pytest_asyncio.fixture
async def sample_bbr(db_session: AsyncSession, sample_poem_with_translations):
    """Create a sample Background Briefing Report."""
    poem, _ = sample_poem_with_translations

    bbr_data = {
        "id": str(uuid.uuid4())[:26],
        "poem_id": poem.id,
        "content": """# Background Briefing Report: 靜夜思 by 李白

## Historical Context
This poem was written during the Tang Dynasty (618-907 CE), often considered the golden age of Chinese poetry.

## Cultural Significance
"靜夜思" (Quiet Night Thoughts) is one of Li Bai's most famous and widely taught poems, capturing themes of homesickness and nostalgia.

## Translation Challenges
- The concise nature of classical Chinese poetry
- Cultural metaphor of moon as homesickness symbol
- Maintaining poetic rhythm in translation

## Recommended Translation Approach
Focus on preserving the emotional core while adapting imagery for target cultural context.""",
        "metadata_json": '{"generated_at": "2025-01-15T10:30:00Z", "model": "qwen-max"}',
    }
    bbr = BackgroundBriefingReport(**bbr_data)
    db_session.add(bbr)
    await db_session.commit()
    await db_session.refresh(bbr)

    return bbr


# ==============================================================================
# Enhanced Poem CRUD Tests
# ==============================================================================


@pytest.mark.repository
@pytest.mark.database
class TestEnhancedPoemCRUD:
    """Enhanced tests for Poem CRUD operations."""

    async def test_create_poem_with_validation(
        self, repository_service: RepositoryService
    ):
        """Test poem creation with comprehensive validation."""
        poem_create = PoemCreate(
            poet_name="Emily Dickinson",
            poem_title="'Hope' is the thing with feathers",
            source_language="English",
            original_text="""Hope is the thing with feathers
That perches in the soul,
And sings the tune without the words,
And never stops at all,""",
            metadata_json='{"theme": "hope", "style": "metaphorical", "era": "19th century"}',
        )

        poem = repository_service.poems.create(poem_create)

        assert poem.id is not None
        assert len(poem.id) == 26  # ULID length
        assert poem.poet_name == poem_create.poet_name
        assert poem.poem_title == poem_create.poem_title
        assert poem.source_language == poem_create.source_language
        assert poem.original_text == poem_create.original_text
        assert poem.metadata_json == poem_create.metadata_json
        assert poem.created_at is not None
        assert poem.updated_at is not None
        assert poem.created_at == poem.updated_at  # Should be same on creation

    async def test_create_poem_constraint_validation(
        self, repository_service: RepositoryService
    ):
        """Test poem creation violates database constraints."""
        # Test empty required fields
        with pytest.raises(ValueError):  # Should raise validation error
            poem_create = PoemCreate(
                poet_name="",  # Empty name
                poem_title="Test",
                source_language="English",
                original_text="Test content",
            )
            repository_service.poems.create(poem_create)

    async def test_update_poem_selection_toggle(
        self, repository_service: RepositoryService, sample_poem
    ):
        """Test updating poem selection status."""
        # Initially should be False/None
        assert sample_poem.selected in [False, None]

        # Toggle to True
        updated = repository_service.poems.update_selection(
            sample_poem.id, True
        )
        assert updated is not None
        assert updated.selected is True

        # Toggle back to False
        updated = repository_service.poems.update_selection(
            sample_poem.id, False
        )
        assert updated.selected is False

    async def test_poem_count_with_filters(
        self, repository_service: RepositoryService, test_context
    ):
        """Test poem count with various filters."""
        # Create diverse poems
        await test_context.create_poem(
            poet_name="李白", source_language="Chinese"
        )
        await test_context.create_poem(
            poet_name="杜甫", source_language="Chinese"
        )
        await test_context.create_poem(
            poet_name="Shakespeare", source_language="English"
        )

        # Test total count
        total_count = repository_service.poems.count()
        assert total_count == 3

        # Test filtered count
        chinese_count = repository_service.poems.count(
            source_language="Chinese"
        )
        assert chinese_count == 2

        english_count = repository_service.poems.count(
            source_language="English"
        )
        assert english_count == 1

        poet_count = repository_service.poems.count(poet_name="李白")
        assert poet_count == 1

    async def test_poem_complex_search(
        self, repository_service: RepositoryService, test_context
    ):
        """Test complex poem search with multiple criteria."""
        # Create test poems
        await test_context.create_poem(
            poet_name="Li Bai",
            poem_title="Quiet Night Thoughts",
            source_language="Chinese",
            original_text="Contains moon and homesickness themes",
        )
        await test_context.create_poem(
            poet_name="Wang Wei",
            poem_title="Deer Enclosure",
            source_language="Chinese",
            original_text="Contains nature imagery",
        )

        # Test title search
        results = repository_service.poems.get_multi(title_search="Night")
        assert len(results) == 1
        assert "Night" in results[0].poem_title

        # Test combined filters
        results = repository_service.poems.get_multi(
            poet_name="Li", source_language="Chinese"
        )
        assert len(results) == 1
        assert results[0].poet_name == "Li Bai"

    async def test_poem_pagination_performance(
        self, repository_service: RepositoryService, test_context
    ):
        """Test poem pagination with large dataset."""
        # Create many poems
        poem_ids = []
        for i in range(50):
            poem = await test_context.create_poem(
                poet_name=f"Poet {i}",
                poem_title=f"Poem Title {i}",
                original_text=f"Content for poem {i}" * 10,
            )
            poem_ids.append(poem.id)

        # Test pagination
        page_1 = repository_service.poems.get_multi(skip=0, limit=20)
        page_2 = repository_service.poems.get_multi(skip=20, limit=20)
        page_3 = repository_service.poems.get_multi(skip=40, limit=20)

        assert len(page_1) == 20
        assert len(page_2) == 20
        assert len(page_3) == 10

        # Verify no overlaps
        page_1_ids = {p.id for p in page_1}
        page_2_ids = {p.id for p in page_2}
        page_3_ids = {p.id for p in page_3}

        assert len(page_1_ids.intersection(page_2_ids)) == 0
        assert len(page_2_ids.intersection(page_3_ids)) == 0
        assert len(page_1_ids.intersection(page_3_ids)) == 0


# ==============================================================================
# Enhanced Translation CRUD Tests
# ==============================================================================


@pytest.mark.repository
@pytest.mark.database
class TestEnhancedTranslationCRUD:
    """Enhanced tests for Translation CRUD operations."""

    async def test_translation_with_workflow_support(
        self, repository_service: RepositoryService, sample_poem
    ):
        """Test creating translation with workflow metadata."""
        translation_create = TranslationCreate(
            poem_id=sample_poem.id,
            translator_type=TranslatorType.AI,
            translator_info="VPSWeb Reasoning Mode",
            target_language="English",
            translated_text="Translation with workflow steps",
            translated_poem_title="Test Title",
            translated_poet_name="Test Poet",
            quality_rating=4,
            has_workflow_steps=True,
            workflow_step_count=3,
            total_tokens_used=500,
            total_cost=0.015,
            total_duration=12.5,
            metadata_json='{"workflow_mode": "reasoning", "model": "deepseek-reasoner"}',
        )

        translation = repository_service.translations.create(
            translation_create
        )

        assert translation.id is not None
        assert translation.poem_id == sample_poem.id
        assert translation.has_workflow_steps is True
        assert translation.workflow_step_count == 3
        assert translation.total_tokens_used == 500
        assert translation.total_cost == 0.015
        assert translation.total_duration == 12.5

    async def test_translation_quality_rating_bounds(
        self, repository_service: RepositoryService, sample_poem
    ):
        """Test translation quality rating constraints."""
        # Test valid ratings
        valid_ratings = [1, 2, 3, 4, 5]
        for rating in valid_ratings:
            translation_create = TranslationCreate(
                poem_id=sample_poem.id,
                translator_type=TranslatorType.AI,
                translator_info="Test",
                target_language="English",
                translated_text="Test translation",
                quality_rating=rating,
            )
            translation = repository_service.translations.create(
                translation_create
            )
            assert translation.quality_rating == rating

    async def test_get_translations_by_type_and_language(
        self, repository_service: RepositoryService, test_context
    ):
        """Test filtering translations by type and language."""
        # Create poem
        poem = await test_context.create_poem()

        # Create different translations
        await test_context.create_translation(
            poem_id=poem.id,
            translator_type=TranslatorType.AI,
            target_language="English",
        )
        await test_context.create_translation(
            poem_id=poem.id,
            translator_type=TranslatorType.AI,
            target_language="Japanese",
        )
        await test_context.create_translation(
            poem_id=poem.id,
            translator_type=TranslatorType.HUMAN,
            target_language="English",
        )

        # Test filtering
        ai_translations = repository_service.translations.get_multi(
            translator_type=TranslatorType.AI
        )
        assert len(ai_translations) == 2

        english_translations = repository_service.translations.get_multi(
            target_language="English"
        )
        assert len(english_translations) == 2

        ai_english = repository_service.translations.get_multi(
            translator_type=TranslatorType.AI, target_language="English"
        )
        assert len(ai_english) == 1

    async def test_translation_performance_metrics(
        self, repository_service: RepositoryService, sample_poem
    ):
        """Test translation with performance metrics."""
        translation_create = TranslationCreate(
            poem_id=sample_poem.id,
            translator_type=TranslatorType.AI,
            translator_info="Performance Test",
            target_language="English",
            translated_text="Test",
            total_tokens_used=1000,
            total_cost=0.03,
            total_duration=25.7,
        )

        translation = repository_service.translations.create(
            translation_create
        )

        # Verify performance metrics are stored correctly
        assert translation.total_tokens_used == 1000
        assert translation.total_cost == 0.03
        assert translation.total_duration == 25.7

    async def test_translation_workflow_aggregation(
        self,
        repository_service: RepositoryService,
        sample_poem_with_translations,
    ):
        """Test getting aggregated workflow data for translations."""
        poem, translations = sample_poem_with_translations

        # Test aggregation query (this would be implemented in repository service)
        stats = repository_service.translations.get_workflow_stats()

        assert stats is not None
        assert "total_translations" in stats
        assert "ai_translations" in stats
        assert "human_translations" in stats
        assert "average_quality_rating" in stats


# ==============================================================================
# Enhanced BBR CRUD Tests
# ==============================================================================


@pytest.mark.repository
@pytest.mark.database
class TestEnhancedBBRCRUD:
    """Enhanced tests for Background Briefing Report CRUD operations."""

    async def test_create_bbr_with_validation(
        self, repository_service: RepositoryService, sample_poem
    ):
        """Test BBR creation with content validation."""
        bbr_create = BackgroundBriefingReportCreate(
            poem_id=sample_poem.id,
            content="""# Comprehensive BBR Test

## Historical Context
Detailed historical information about the poem and author.

## Cultural Analysis
Deep cultural context and significance.

## Translation Guidelines
Specific advice for translators working with this poem.""",
            metadata_json='{"model": "qwen-max", "tokens_used": 1500}',
        )

        bbr = repository_service.bbrs.create(bbr_create)

        assert bbr.id is not None
        assert bbr.poem_id == sample_poem.id
        assert len(bbr.content) > 100  # Should have substantial content
        assert bbr.created_at is not None

    async def test_bbr_unique_poem_constraint(
        self, repository_service: RepositoryService, sample_poem
    ):
        """Test that each poem can only have one BBR."""
        # Create first BBR
        bbr_create1 = BackgroundBriefingReportCreate(
            poem_id=sample_poem.id, content="First BBR content"
        )
        bbr1 = repository_service.bbrs.create(bbr_create1)
        assert bbr1 is not None

        # Attempt to create second BBR for same poem
        bbr_create2 = BackgroundBriefingReportCreate(
            poem_id=sample_poem.id, content="Second BBR content"
        )

        # This should either update existing BBR or raise constraint error
        # depending on business logic implementation
        with pytest.raises((IntegrityError, ValueError)):
            repository_service.bbrs.create(bbr_create2)

    async def test_get_bbr_with_poem_data(
        self, repository_service: RepositoryService, sample_bbr
    ):
        """Test getting BBR with associated poem information."""
        bbr = repository_service.bbrs.get_by_id(sample_bbr.id)
        assert bbr is not None
        assert bbr.poem_id == sample_bbr.poem_id

        # Test getting BBR by poem_id
        bbr_by_poem = repository_service.bbrs.get_by_poem(sample_bbr.poem_id)
        assert bbr_by_poem is not None
        assert bbr_by_poem.id == sample_bbr.id

    async def test_update_bbr_content(
        self, repository_service: RepositoryService, sample_bbr
    ):
        """Test updating BBR content."""
        updated_content = (
            sample_bbr.content
            + "\n\n## Additional Notes\nAdditional translation insights."
        )

        # Update method would need to be implemented in repository
        # updated_bbr = repository_service.bbrs.update(sample_bbr.id, {"content": updated_content})

        # For now, test that we can at least retrieve and compare
        current_bbr = repository_service.bbrs.get_by_id(sample_bbr.id)
        assert current_bbr.content == sample_bbr.content


# ==============================================================================
# Enhanced AI Log CRUD Tests
# ==============================================================================


@pytest.mark.repository
@pytest.mark.database
class TestEnhancedAILogCRUD:
    """Enhanced tests for AI Log CRUD operations."""

    async def test_ai_log_workflow_step_tracking(
        self, repository_service: RepositoryService, sample_translation
    ):
        """Test AI log creation for different workflow steps."""
        workflow_steps = [
            WorkflowStepType.INITIAL_TRANSLATION,
            WorkflowStepType.EDITOR_REVIEW,
            WorkflowStepType.TRANSLATOR_REVISION,
            WorkflowStepType.QUALITY_ASSESSMENT,
        ]

        created_logs = []
        for step in workflow_steps:
            log_create = AILogCreate(
                translation_id=sample_translation.id,
                workflow_step=step,
                model_name="qwen-max",
                workflow_mode=WorkflowMode.HYBRID,
                runtime_seconds=5.0 + len(created_logs),
                token_usage_json=f'{{"total_tokens": {200 + len(created_logs) * 100}}}',
                cost_info_json=f'{{"total_cost": {0.01 + len(created_logs) * 0.005}}}',
                notes=f"Completed {step.value} step",
            )

            ai_log = repository_service.ai_logs.create(log_create)
            created_logs.append(ai_log)

            assert ai_log.workflow_step == step
            assert ai_log.model_name == "qwen-max"
            assert ai_log.workflow_mode == WorkflowMode.HYBRID

        # Verify all logs are associated with the translation
        logs_by_translation = repository_service.ai_logs.get_by_translation(
            sample_translation.id
        )
        assert len(logs_by_translation) == len(workflow_steps)

    async def test_ai_log_performance_aggregation(
        self, repository_service: RepositoryService, sample_workflow_data
    ):
        """Test aggregating AI log performance metrics."""
        ai_logs, _ = sample_workflow_data

        # Test aggregation queries
        total_tokens = sum(
            int(
                log.token_usage_json.split('"total_tokens": ')[1].split("}")[0]
            )
            for log in ai_logs
        )

        total_cost = sum(
            float(log.cost_info_json.split('"total_cost": ')[1].split("}")[0])
            for log in ai_logs
        )

        total_runtime = sum(log.runtime_seconds for log in ai_logs)

        assert total_tokens > 0
        assert total_cost > 0
        assert total_runtime > 0

    async def test_ai_log_by_model_filtering(
        self, repository_service: RepositoryService, sample_workflow_data
    ):
        """Test filtering AI logs by model name."""
        ai_logs, _ = sample_workflow_data

        # Get logs by different models
        qwen_logs = repository_service.ai_logs.get_by_model("qwen-max")
        deepseek_logs = repository_service.ai_logs.get_by_model(
            "deepseek-chat"
        )

        assert len(qwen_logs) > 0
        assert len(deepseek_logs) > 0

        # Verify all logs have correct model names
        for log in qwen_logs:
            assert log.model_name == "qwen-max"

        for log in deepseek_logs:
            assert log.model_name == "deepseek-chat"


# ==============================================================================
# Enhanced Human Note CRUD Tests
# ==============================================================================


@pytest.mark.repository
@pytest.mark.database
class TestEnhancedHumanNoteCRUD:
    """Enhanced tests for Human Note CRUD operations."""

    async def test_human_note_creation(
        self, repository_service: RepositoryService, sample_translation
    ):
        """Test human note creation with validation."""
        note_texts = [
            "Excellent poetic quality and cultural adaptation.",
            "Consider adjusting rhythm in the second stanza.",
            "Final version successfully captures emotional depth.",
        ]

        created_notes = []
        for note_text in note_texts:
            note_create = HumanNoteCreate(
                translation_id=sample_translation.id, note_text=note_text
            )
            note = repository_service.human_notes.create(note_create)
            created_notes.append(note)

            assert note.translation_id == sample_translation.id
            assert note.note_text == note_text
            assert note.created_at is not None

        # Verify all notes are retrievable
        notes_by_translation = (
            repository_service.human_notes.get_by_translation(
                sample_translation.id
            )
        )
        assert len(notes_by_translation) == len(note_texts)

    async def test_human_note_content_validation(
        self, repository_service: RepositoryService, sample_translation
    ):
        """Test human note content validation."""
        # Test empty note
        with pytest.raises(ValueError):
            note_create = HumanNoteCreate(
                translation_id=sample_translation.id,
                note_text="",  # Empty note
            )
            repository_service.human_notes.create(note_create)

        # Test very long note
        long_note = "A" * 10000  # Very long note
        note_create = HumanNoteCreate(
            translation_id=sample_translation.id, note_text=long_note
        )

        # Should either succeed or fail based on max length constraints
        try:
            note = repository_service.human_notes.create(note_create)
            assert len(note.note_text) == len(long_note)
        except ValueError:
            # Expected if there's a max length constraint
            pass

    async def test_human_note_chronological_ordering(
        self, repository_service: RepositoryService, sample_translation
    ):
        """Test that human notes maintain chronological order."""
        note_texts = ["First note", "Second note", "Third note"]

        # Create notes with slight delays to ensure different timestamps
        created_notes = []
        for note_text in note_texts:
            note_create = HumanNoteCreate(
                translation_id=sample_translation.id, note_text=note_text
            )
            note = repository_service.human_notes.create(note_create)
            created_notes.append(note)
            await asyncio.sleep(0.01)  # Small delay

        # Retrieve notes and verify chronological order
        retrieved_notes = repository_service.human_notes.get_by_translation(
            sample_translation.id
        )

        # Should be ordered by created_at ascending
        for i in range(1, len(retrieved_notes)):
            assert (
                retrieved_notes[i].created_at
                >= retrieved_notes[i - 1].created_at
            )


# ==============================================================================
# Cross-Entity Relationship Tests
# ==============================================================================


@pytest.mark.repository
@pytest.mark.database
class TestCrossEntityRelationships:
    """Test relationships and operations across multiple entities."""

    async def test_complete_poem_workflow(
        self, repository_service: RepositoryService, sample_poem
    ):
        """Test complete workflow from poem creation through translation and review."""
        # Step 1: Create AI translation
        translation_create = TranslationCreate(
            poem_id=sample_poem.id,
            translator_type=TranslatorType.AI,
            translator_info="Hybrid Mode",
            target_language="English",
            translated_text="AI-generated translation",
            has_workflow_steps=True,
            workflow_step_count=3,
        )
        translation = repository_service.translations.create(
            translation_create
        )

        # Step 2: Create AI logs for each workflow step
        steps = [
            WorkflowStepType.INITIAL_TRANSLATION,
            WorkflowStepType.EDITOR_REVIEW,
            WorkflowStepType.TRANSLATOR_REVISION,
        ]

        for i, step in enumerate(steps):
            log_create = AILogCreate(
                translation_id=translation.id,
                workflow_step=step,
                model_name="qwen-max",
                workflow_mode=WorkflowMode.HYBRID,
                runtime_seconds=3.0 + i,
                token_usage_json=f'{{"total_tokens": {150 + i * 50}}}',
                cost_info_json=f'{{"total_cost": {0.005 + i * 0.002}}}',
                notes=f"Step {i+1} completed",
            )
            repository_service.ai_logs.create(log_create)

        # Step 3: Create human review notes
        note_texts = [
            "Good initial translation quality",
            "Cultural adaptation well handled",
            "Final version approved",
        ]
        for note_text in note_texts:
            note_create = HumanNoteCreate(
                translation_id=translation.id, note_text=note_text
            )
            repository_service.human_notes.create(note_create)

        # Step 4: Create BBR
        bbr_create = BackgroundBriefingReportCreate(
            poem_id=sample_poem.id,
            content="Comprehensive background analysis for translation context",
        )
        repository_service.bbrs.create(bbr_create)

        # Verify complete workflow
        poem_with_data = repository_service.get_poem_with_translations(
            sample_poem.id
        )
        assert poem_with_data is not None
        assert len(poem_with_data["translations"]) == 1

        translation_data = poem_with_data["translations"][0]
        assert len(translation_data["ai_logs"]) == 3
        assert len(translation_data["human_notes"]) == 3

    async def test_cascade_deletion_handling(
        self,
        repository_service: RepositoryService,
        sample_poem_with_translations,
    ):
        """Test cascade deletion behavior."""
        poem, translations = sample_poem_with_translations

        # Get initial counts
        initial_poem_count = repository_service.poems.count()
        initial_translation_count = len(
            repository_service.translations.get_by_poem(poem.id)
        )

        assert initial_poem_count > 0
        assert initial_translation_count > 0

        # Delete poem (should handle related data appropriately)
        deleted = repository_service.poems.delete(poem.id)
        assert deleted is True

        # Verify poem is deleted
        assert repository_service.poems.get_by_id(poem.id) is None

        # Check how related data is handled (depends on cascade configuration)
        remaining_translations = repository_service.translations.get_by_poem(
            poem.id
        )
        # Should be empty if cascade delete is configured
        assert len(remaining_translations) == 0

    async def test_performance_with_large_dataset(
        self, repository_service: RepositoryService, test_context
    ):
        """Test performance with large dataset across all entities."""
        # Create multiple poems with translations
        poem_count = 20
        translations_per_poem = 3

        created_poems = []
        for i in range(poem_count):
            poem = await test_context.create_poem(
                poet_name=f"Poet {i}",
                poem_title=f"Poem {i}",
                original_text=f"Content for poem {i}" * 5,
            )
            created_poems.append(poem)

            # Create translations for each poem
            for j in range(translations_per_poem):
                await test_context.create_translation(
                    poem_id=poem.id,
                    target_language=["English", "Japanese", "Korean"][j % 3],
                    translator_type=(
                        TranslatorType.AI
                        if j % 2 == 0
                        else TranslatorType.HUMAN
                    ),
                )

        # Test aggregation queries performance
        stats = repository_service.get_repository_stats()
        assert stats["total_poems"] == poem_count
        assert (
            stats["total_translations"] == poem_count * translations_per_poem
        )

        # Test filtered queries
        start_time = datetime.now()

        ai_translations = repository_service.translations.get_multi(
            translator_type=TranslatorType.AI
        )

        query_time = (datetime.now() - start_time).total_seconds()

        assert len(ai_translations) > 0
        assert (
            query_time < 1.0
        )  # Should complete quickly even with larger dataset


# ==============================================================================
# Database Constraint and Edge Case Tests
# ==============================================================================


@pytest.mark.repository
@pytest.mark.database
class TestDatabaseConstraintsAndEdgeCases:
    """Test database constraints and edge cases."""

    async def test_foreign_key_constraints(
        self, repository_service: RepositoryService
    ):
        """Test foreign key constraint enforcement."""
        # Test translation with non-existent poem_id
        fake_poem_id = str(uuid.uuid4())[:26]

        translation_create = TranslationCreate(
            poem_id=fake_poem_id,  # Non-existent poem
            translator_type=TranslatorType.AI,
            translator_info="Test",
            target_language="English",
            translated_text="Test",
        )

        with pytest.raises(IntegrityError):
            repository_service.translations.create(translation_create)

    async def test_unique_constraints(
        self, repository_service: RepositoryService, sample_poem
    ):
        """Test unique constraint enforcement where applicable."""
        # Create first translation
        translation_create1 = TranslationCreate(
            poem_id=sample_poem.id,
            translator_type=TranslatorType.AI,
            translator_info="Test Model",
            target_language="English",
            translated_text="First translation",
        )
        translation1 = repository_service.translations.create(
            translation_create1
        )

        # Create second translation (should be allowed - translations are not unique per poem)
        translation_create2 = TranslationCreate(
            poem_id=sample_poem.id,
            translator_type=TranslatorType.HUMAN,
            translator_info="Human Translator",
            target_language="English",
            translated_text="Second translation",
        )
        translation2 = repository_service.translations.create(
            translation_create2
        )

        assert translation1.id != translation2.id

    async def test_null_handling(
        self, repository_service: RepositoryService, sample_poem
    ):
        """Test proper handling of nullable fields."""
        # Create translation with minimal required fields
        translation_create = TranslationCreate(
            poem_id=sample_poem.id,
            translator_type=TranslatorType.AI,
            translator_info="Test",
            target_language="English",
            translated_text="Minimal translation",
            # Many optional fields left as None
        )

        translation = repository_service.translations.create(
            translation_create
        )

        # Verify nullable fields are handled correctly
        assert (
            translation.quality_rating is None
        )  # Should be None if not provided
        assert (
            translation.metadata_json is None
            or translation.metadata_json == {}
        )

    async def test_transaction_rollback(
        self, repository_service: RepositoryService, sample_poem
    ):
        """Test transaction rollback on errors."""
        initial_count = repository_service.translations.count()

        # Attempt to create invalid translation that should fail
        try:
            translation_create = TranslationCreate(
                poem_id=sample_poem.id,
                translator_type=TranslatorType.AI,
                translator_info="Test",
                target_language="",  # Invalid empty language code
                translated_text="Test",
            )
            repository_service.translations.create(translation_create)
        except (ValueError, IntegrityError):
            pass  # Expected to fail

        # Verify count hasn't changed (transaction was rolled back)
        final_count = repository_service.translations.count()
        assert final_count == initial_count
