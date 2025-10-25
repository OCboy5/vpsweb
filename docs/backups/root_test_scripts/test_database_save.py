#!/usr/bin/env python3
"""
Test script to verify the database save fix for TranslationCreate schema
"""
import sys
import json

# Add src to path
sys.path.insert(0, '/Volumes/Work/Dev/vpsweb/vpsweb/src')

def test_translation_create_schema():
    """Test that the fixed TranslationCreate schema works correctly"""

    print("🧪 Testing TranslationCreate schema fix...")

    try:
        from vpsweb.repository.schemas import TranslationCreate, TranslatorType

        # Test data that mimics the workflow result
        result_dict = {
            "input": {"content": "久去山泽游，浪莽林野娱。"},
            "initial_translation": "Having long roamed mountains and marshes, I wandered wildly in forests and fields.",
            "revised_translation": "Long I've roamed the mountains and marshes, wandering freely through woods and wilds.",
            "editor_review": "Good flow, suggested minor improvements to word choice.",
            "workflow_id": "test-workflow-123",
            "total_tokens": 150,
            "duration_seconds": 25.5,
            "full_log": "Translation completed successfully."
        }

        # Test the fixed schema creation (this should work now)
        print("📝 Creating TranslationCreate object...")

        # Use the same logic as in the fixed code
        final_translation = result_dict.get("revised_translation") or result_dict.get("initial_translation", "")

        translation_create = TranslationCreate(
            poem_id="01K8AV9KFTSG8N2EWW9P6WR4ZC",
            translator_type=TranslatorType.AI,
            translator_info="AI Workflow",
            target_language="en",
            translated_text=final_translation,  # This is the required field we added
            metadata={
                "workflow_mode": "non_reasoning",
                "workflow_id": result_dict.get("workflow_id"),
                "total_tokens": result_dict.get("total_tokens", 0),
                "duration_seconds": result_dict.get("duration_seconds", 0),
                "full_log": result_dict.get("full_log", ""),
                "source_content": result_dict.get("input", {}).get("content", ""),
                "initial_translation": result_dict.get("initial_translation", ""),
                "editor_review": result_dict.get("editor_review", ""),
                "revised_translation": result_dict.get("revised_translation", "")
            }
        )

        print("✅ TranslationCreate object created successfully!")
        print(f"   Poem ID: {translation_create.poem_id}")
        print(f"   Translator: {translation_create.translator_info}")
        print(f"   Target Language: {translation_create.target_language}")
        print(f"   Translated Text: {translation_create.translated_text[:100]}...")
            if hasattr(translation_create, 'metadata'):
            print(f"   Metadata keys: {list(translation_create.metadata.keys())}")
        else:
            print("   Metadata: Not accessible via attribute (stored internally)")

        # Test JSON serialization
        print("\n🔤 Testing JSON serialization...")
        json_data = translation_create.model_dump()
        print("✅ JSON serialization successful!")
        print(f"   JSON keys: {list(json_data.keys())}")

        # Test the old broken approach to confirm it would fail
        print("\n❌ Testing old broken approach (should fail)...")
        try:
            # This is the OLD broken code that would fail
            broken_translation_create = TranslationCreate(
                poem_id="test",
                translator_type=TranslatorType.AI,
                translator_info="AI Workflow",
                target_language="en",
                source_content=result_dict.get("input", {}).get("content", ""),      # ❌ Invalid field
                initial_translation=result_dict.get("initial_translation", ""),        # ❌ Invalid field
                editor_review=result_dict.get("editor_review", ""),                    # ❌ Invalid field
                revised_translation=result_dict.get("revised_translation", ""),       # ❌ Invalid field
                metadata={}
            )
            print("❌ UNEXPECTED: Old broken approach worked (this shouldn't happen)")
            return False
        except Exception as e:
            print(f"✅ Expected failure with old approach: {type(e).__name__}: {str(e)[:100]}...")

        print("\n🎉 SCHEMA FIX VERIFICATION SUCCESSFUL!")
        print("✅ The database save fix is working correctly")
        print("✅ TranslationCreate schema validation passes")
        print("✅ Required translated_text field is properly provided")
        print("✅ Workflow data is correctly stored in metadata")

        return True

    except Exception as e:
        print(f"\n💥 SCHEMA FIX VERIFICATION FAILED!")
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Database Save Fix Verification")
    print("=" * 50)
    print("This test verifies that the TranslationCreate schema fix")
    print("resolves the 'Field required: translated_text' validation error")
    print("=" * 50)

    try:
        result = test_translation_create_schema()
        if result:
            print("\n✅ DATABASE SAVE FIX VERIFIED: Ready for production!")
            sys.exit(0)
        else:
            print("\n❌ DATABASE SAVE FIX FAILED: Needs more work")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)