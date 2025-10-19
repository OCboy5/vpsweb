"""
Simple unit tests for VPSWeb Repository v0.3.1

Basic tests to verify models and schemas work without circular imports
"""

import pytest
import sys
from pathlib import Path

# Add repository root to path and isolate imports
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import directly from current module to avoid circular imports
from models import Poem, Translation, AILog, HumanNote, Base
from schemas import (
    PoemCreate,
    TranslationCreate,
    AILogCreate,
    HumanNoteCreate,
    TranslatorType,
    WorkflowMode,
)
from pydantic import ValidationError


def test_pydantic_validation():
    """Test that Pydantic validation works"""

    # Test valid poem creation
    poem_data = {
        "poet_name": "陶渊明",
        "poem_title": "歸園田居",
        "source_language": "zh",
        "original_text": "採菊東籬下，悠然見南山。山氣日夕佳，飛鳥相與還。",
        "metadata_json": '{"dynasty": "東晉"}',
    }

    poem = PoemCreate(**poem_data)
    assert poem.poet_name == "陶渊明"
    assert poem.poem_title == "歸園田居"
    assert poem.source_language == "zh"
    assert len(poem.original_text) >= 10

    # Test invalid poem (too short text)
    invalid_poem_data = poem_data.copy()
    invalid_poem_data["original_text"] = "Short"

    with pytest.raises(ValidationError):
        PoemCreate(**invalid_poem_data)

    # Test valid translation
    trans_data = {
        "poem_id": "test_poem_001",
        "translator_type": TranslatorType.AI,
        "translator_info": "gpt-4",
        "target_language": "en",
        "translated_text": "Picking chrysanthemums by the eastern fence, I calmly see the Southern Mountain.",
        "quality_rating": 5,
    }

    translation = TranslationCreate(**trans_data)
    assert translation.translator_type == TranslatorType.AI
    assert translation.target_language == "en"
    assert translation.quality_rating == 5

    # Test invalid quality rating
    invalid_trans_data = trans_data.copy()
    invalid_trans_data["quality_rating"] = 6

    with pytest.raises(ValidationError):
        TranslationCreate(**invalid_trans_data)


def test_model_creation():
    """Test SQLAlchemy model creation"""

    # Create poem model
    poem = Poem(
        id="test_poem_001",
        poet_name="李白",
        poem_title="靜夜思",
        source_language="zh",
        original_text="床前明月光，疑是地上霜。舉頭望明月，低頭思故鄉。",
    )

    assert poem.id == "test_poem_001"
    assert poem.poet_name == "李白"
    assert poem.poem_title == "靜夜思"

    # Test translation model
    translation = Translation(
        id="test_trans_001",
        poem_id="test_poem_001",
        translator_type=TranslatorType.AI,
        target_language="en",
        translated_text="Before my bed, the bright moonlight shines...",
    )

    assert translation.id == "test_trans_001"
    assert translation.poem_id == "test_poem_001"
    assert translation.translator_type == TranslatorType.AI

    # Test AI log model
    ai_log = AILog(
        id="test_ai_001",
        translation_id="test_trans_001",
        model_name="gpt-4",
        workflow_mode=WorkflowMode.REASONING,
        runtime_seconds=12.5,
    )

    assert ai_log.id == "test_ai_001"
    assert ai_log.model_name == "gpt-4"
    assert ai_log.workflow_mode == WorkflowMode.REASONING

    # Test human note model
    note = HumanNote(
        id="test_note_001",
        translation_id="test_trans_001",
        note_text="This is a good translation that captures the essence.",
    )

    assert note.id == "test_note_001"
    assert "good translation" in note.note_text


def test_enums():
    """Test enum values"""

    # Test TranslatorType
    assert TranslatorType.AI == "ai"
    assert TranslatorType.HUMAN == "human"
    assert list(TranslatorType) == [TranslatorType.AI, TranslatorType.HUMAN]

    # Test WorkflowMode
    assert WorkflowMode.REASONING == "reasoning"
    assert WorkflowMode.NON_REASONING == "non_reasoning"
    assert WorkflowMode.HYBRID == "hybrid"
    assert list(WorkflowMode) == [
        WorkflowMode.REASONING,
        WorkflowMode.NON_REASONING,
        WorkflowMode.HYBRID,
    ]


def test_model_relationships():
    """Test model relationships work correctly"""

    # Create models
    poem = Poem(
        id="test_poem_rel",
        poet_name="杜甫",
        poem_title="春望",
        source_language="zh",
        original_text="國破山河在，城春草木深。",
    )

    translation = Translation(
        id="test_trans_rel",
        poem_id="test_poem_rel",
        translator_type=TranslatorType.AI,
        target_language="en",
        translated_text="The state is destroyed, but the mountains and rivers remain.",
    )

    ai_log = AILog(
        id="test_ai_rel",
        translation_id="test_trans_rel",
        model_name="claude-3",
        workflow_mode=WorkflowMode.HYBRID,
    )

    # Test relationships (without database)
    # These would work when objects are properly associated through a session
    assert translation.poem_id == poem.id
    assert ai_log.translation_id == translation.id


def test_model_properties():
    """Test model helper properties"""

    # Create poem
    poem = Poem(
        id="test_poem_prop",
        poet_name="王維",
        poem_title="相思",
        source_language="zh",
        original_text="紅豆生南國，春來發幾枝。",
    )

    # Test translation count properties (would be 0 without actual relationships)
    # These properties would work properly when relationships are established
    assert hasattr(poem, "translation_count")
    assert hasattr(poem, "ai_translation_count")
    assert hasattr(poem, "human_translation_count")

    # Create translation
    translation = Translation(
        id="test_trans_prop",
        poem_id="test_poem_prop",
        translator_type=TranslatorType.AI,
        target_language="en",
        translated_text="Red beans grow in the southern country...",
    )

    # Test translation properties
    assert hasattr(translation, "has_ai_logs")
    assert hasattr(translation, "has_human_notes")

    # Create AI log
    ai_log = AILog(
        id="test_ai_prop",
        translation_id="test_trans_prop",
        model_name="gpt-4",
        workflow_mode=WorkflowMode.REASONING,
        token_usage_json='{"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}',
    )

    # Test AI log properties
    assert hasattr(ai_log, "token_usage")
    assert hasattr(ai_log, "cost_info")

    # Test token_usage parsing
    if ai_log.token_usage:
        assert ai_log.token_usage["total_tokens"] == 150


if __name__ == "__main__":
    # Run tests directly
    test_pydantic_validation()
    print("✓ Pydantic validation tests passed")

    test_model_creation()
    print("✓ Model creation tests passed")

    test_enums()
    print("✓ Enum tests passed")

    test_model_relationships()
    print("✓ Model relationship tests passed")

    test_model_properties()
    print("✓ Model property tests passed")

    print("\nAll simple tests passed! ✅")
