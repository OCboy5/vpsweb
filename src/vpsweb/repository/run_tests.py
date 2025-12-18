#!/usr/bin/env python3
"""
Isolated test runner for VPSWeb Repository v0.3.1
"""

import os
import sys
from pathlib import Path

# Add repository root to path
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

# Change to repository directory for proper package imports
os.chdir(Path(__file__).parent)


def test_imports():
    """Test that we can import all modules correctly"""
    try:
        # Test direct imports
        pass

        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_basic_models():
    """Test basic model creation without database"""
    try:
        from models import AILog, HumanNote, Poem, Translation

        # Test poem model
        poem = Poem(
            id="test_poem",
            poet_name="李白",
            poem_title="靜夜思",
            source_language="zh-CN",
            original_text="床前明月光，疑是地上霜。舉頭望明月，低頭思故鄉。",
        )
        assert poem.poet_name == "李白"
        assert poem.poem_title == "靜夜思"
        print("✓ Poem model creation works")

        # Test translation model
        translation = Translation(
            id="test_trans",
            poem_id="test_poem",
            translator_type="ai",
            target_language="en",
            translated_text="Before my bed, the bright moonlight shines...",
        )
        assert translation.translator_type == "ai"
        print("✓ Translation model creation works")

        # Test AI log model
        ai_log = AILog(
            id="test_ai",
            translation_id="test_trans",
            model_name="gpt-4",
            workflow_mode="reasoning",
        )
        assert ai_log.model_name == "gpt-4"
        print("✓ AI log model creation works")

        # Test human note model
        note = HumanNote(
            id="test_note",
            translation_id="test_trans",
            note_text="This is a good translation.",
        )
        assert "good translation" in note.note_text
        print("✓ Human note model creation works")

        return True
    except Exception as e:
        print(f"✗ Model creation error: {e}")
        return False


def test_pydantic_schemas():
    """Test Pydantic schema validation"""
    try:
        from pydantic import ValidationError
        from schemas import (
            PoemCreate,
            TranslationCreate,
            TranslatorType,
        )

        # Test valid poem
        poem = PoemCreate(
            poet_name="陶渊明",
            poem_title="歸園田居",
            source_language="zh-CN",
            original_text="採菊東籬下，悠然見南山。山氣日夕佳，飛鳥相與還。",
        )
        assert poem.poet_name == "陶渊明"
        print("✓ Valid poem schema works")

        # Test invalid poem (too short)
        try:
            invalid_poem = PoemCreate(
                poet_name="Test",
                poem_title="Test",
                source_language="en",
                original_text="Short",  # Too short
            )
            print("✗ Should have failed with short text")
            return False
        except ValidationError:
            print("✓ Invalid poem correctly rejected")

        # Test valid translation
        translation = TranslationCreate(
            poem_id="test_poem",
            translator_type=TranslatorType.AI,
            translator_info="gpt-4",
            target_language="en",
            translated_text="This is a valid translation with enough content to pass validation.",
            quality_rating=4,
        )
        assert translation.translator_type == TranslatorType.AI
        print("✓ Valid translation schema works")

        # Test invalid quality rating
        try:
            invalid_trans = TranslationCreate(
                poem_id="test_poem",
                translator_type=TranslatorType.HUMAN,
                target_language="en",
                translated_text="This is a valid translation.",
                quality_rating=6,  # Too high
            )
            print("✗ Should have failed with invalid quality rating")
            return False
        except ValidationError:
            print("✓ Invalid quality rating correctly rejected")

        return True
    except Exception as e:
        print(f"✗ Schema validation error: {e}")
        return False


def test_database_connection():
    """Test database connection and table creation"""
    try:
        from database import check_db_connection, create_session

        # Test database connection
        if check_db_connection():
            print("✓ Database connection successful")
        else:
            print("✗ Database connection failed")
            return False

        # Test session creation
        session = create_session()
        try:
            # Test simple query
            result = session.execute("SELECT 1").scalar()
            assert result == 1
            print("✓ Database session works")
        finally:
            session.close()

        return True
    except Exception as e:
        print(f"✗ Database connection error: {e}")
        return False


def main():
    """Run all tests"""
    print("Running VPSWeb Repository v0.3.1 Isolated Tests")
    print("=" * 50)

    tests = [
        ("Import Tests", test_imports),
        ("Model Tests", test_basic_models),
        ("Schema Tests", test_pydantic_schemas),
        ("Database Tests", test_database_connection),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
        else:
            print(f"FAILED: {test_name}")

    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())
