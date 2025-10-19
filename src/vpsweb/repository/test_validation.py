#!/usr/bin/env python3
"""
Test script for enhanced Pydantic validation in VPSWeb Repository v0.3.1
"""

import sys
from pathlib import Path

# Add repository root to path
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

from pydantic import ValidationError
from schemas import (
    PoemCreate, TranslationCreate, AILogCreate, HumanNoteCreate,
    TranslatorType, WorkflowMode
)

def test_poem_validation():
    """Test poem schema validation"""
    print("=== Testing Poem Validation ===")

    # Valid poem
    try:
        poem = PoemCreate(
            poet_name="陶渊明",
            poem_title="歸園田居",
            source_language="zh",
            original_text="採菊東籬下，悠然見南山。山氣日夕佳，飛鳥相與還。"
        )
        print(f"✓ Valid poem created: {poem.poet_name} - {poem.poem_title}")
    except ValidationError as e:
        print(f"✗ Unexpected validation error: {e}")

    # Invalid poet name (empty)
    try:
        poem = PoemCreate(
            poet_name="",
            poem_title="Test Poem",
            source_language="en",
            original_text="This is a test poem with enough content."
        )
        print("✗ Should have failed with empty poet name")
    except ValidationError as e:
        print(f"✓ Correctly caught empty poet name: {e.errors()[0]['msg']}")

    # Invalid language code
    try:
        poem = PoemCreate(
            poet_name="Test Poet",
            poem_title="Test",
            source_language="x",  # Too short
            original_text="This is a test poem with enough content."
        )
        print("✗ Should have failed with invalid language code")
    except ValidationError as e:
        print(f"✓ Correctly caught invalid language code: {e.errors()[0]['msg']}")

    # Invalid original text (too short)
    try:
        poem = PoemCreate(
            poet_name="Test Poet",
            poem_title="Test",
            source_language="en",
            original_text="Short"  # Too short
        )
        print("✗ Should have failed with short original text")
    except ValidationError as e:
        print(f"✓ Correctly caught short original text: {e.errors()[0]['msg']}")

def test_translation_validation():
    """Test translation schema validation"""
    print("\n=== Testing Translation Validation ===")

    # Valid translation
    try:
        translation = TranslationCreate(
            poem_id="test_poem_id",
            translator_type=TranslatorType.AI,
            translator_info="gpt-4",
            target_language="en",
            translated_text="Picking chrysanthemums by the eastern fence, I calmly see the Southern Mountain."
        )
        print(f"✓ Valid translation created: {translation.translator_type} - {translation.target_language}")
    except ValidationError as e:
        print(f"✗ Unexpected validation error: {e}")

    # Invalid quality rating
    try:
        translation = TranslationCreate(
            poem_id="test_poem_id",
            translator_type=TranslatorType.HUMAN,
            translator_info="John Doe",
            target_language="en",
            translated_text="This is a valid translation with enough content to pass validation.",
            quality_rating=6  # Too high
        )
        print("✗ Should have failed with invalid quality rating")
    except ValidationError as e:
        print(f"✓ Correctly caught invalid quality rating: {e.errors()[0]['msg']}")

def test_ai_log_validation():
    """Test AI log schema validation"""
    print("\n=== Testing AI Log Validation ===")

    # Valid AI log
    try:
        ai_log = AILogCreate(
            translation_id="test_translation_id",
            model_name="gpt-4",
            workflow_mode=WorkflowMode.REASONING,
            runtime_seconds=45.5,
            token_usage_json='{"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}',
            notes="Translation completed successfully"
        )
        print(f"✓ Valid AI log created: {ai_log.model_name} - {ai_log.workflow_mode}")
    except ValidationError as e:
        print(f"✗ Unexpected validation error: {e}")

    # Invalid runtime (negative)
    try:
        ai_log = AILogCreate(
            translation_id="test_translation_id",
            model_name="gpt-4",
            workflow_mode=WorkflowMode.HYBRID,
            runtime_seconds=-10  # Negative
        )
        print("✗ Should have failed with negative runtime")
    except ValidationError as e:
        print(f"✓ Correctly caught negative runtime: {e.errors()[0]['msg']}")

    # Invalid JSON
    try:
        ai_log = AILogCreate(
            translation_id="test_translation_id",
            model_name="gpt-4",
            workflow_mode=WorkflowMode.NON_REASONING,
            token_usage_json='{"invalid": json}'  # Invalid JSON
        )
        print("✗ Should have failed with invalid JSON")
    except ValidationError as e:
        print(f"✓ Correctly caught invalid JSON: {e.errors()[0]['msg']}")

def test_human_note_validation():
    """Test human note schema validation"""
    print("\n=== Testing Human Note Validation ===")

    # Valid human note
    try:
        note = HumanNoteCreate(
            translation_id="test_translation_id",
            note_text="This translation captures the poetic essence well. Consider alternative wording for clarity."
        )
        print(f"✓ Valid human note created: {note.note_text[:50]}...")
    except ValidationError as e:
        print(f"✗ Unexpected validation error: {e}")

    # Invalid note text (too short)
    try:
        note = HumanNoteCreate(
            translation_id="test_translation_id",
            note_text="Hi"  # Too short
        )
        print("✗ Should have failed with short note text")
    except ValidationError as e:
        print(f"✓ Correctly caught short note text: {e.errors()[0]['msg']}")

def main():
    """Run all validation tests"""
    print("Testing Enhanced Pydantic Schemas for VPSWeb Repository v0.3.1")
    print("=" * 60)

    test_poem_validation()
    test_translation_validation()
    test_ai_log_validation()
    test_human_note_validation()

    print("\n" + "=" * 60)
    print("Validation testing completed!")

if __name__ == "__main__":
    main()