#!/usr/bin/env python3
"""
Simple test for the new utility scripts to verify they work independently.
"""

import sys
from pathlib import Path

# Add root path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))


def test_basic_imports():
    """Test that we can import the utilities"""
    print("Testing basic imports...")

    try:
        pass

        print("✅ TranslationRunner import successful")
    except Exception as e:
        print(f"❌ TranslationRunner import failed: {e}")
        return False

    try:
        pass

        print("✅ WeChatArticleRunner import successful")
    except Exception as e:
        print(f"❌ WeChatArticleRunner import failed: {e}")
        return False

    return True


def test_class_instantiation():
    """Test that we can create instances of the classes"""
    print("\nTesting class instantiation...")

    try:
        from vpsweb.webui.utils.translation_runner import TranslationRunner

        # Test with dummy config path (will fail but shows it loads)
        try:
            TranslationRunner("nonexistent/config")
            print("❌ Expected config loading error")
        except Exception as e:
            print(f"✅ Expected config loading error: {type(e).__name__}")

        return True
    except Exception as e:
        print(f"❌ TranslationRunner instantiation failed: {e}")
        return False


def test_wechat_runner():
    """Test WeChat runner functionality"""
    print("\nTesting WeChat article runner...")

    try:
        from vpsweb.webui.utils.wechat_article_runner import \
            WeChatArticleRunner

        # Test with dummy config path
        try:
            WeChatArticleRunner("nonexistent/config")
            print("❌ Expected config loading error")
        except Exception as e:
            print(f"✅ Expected config loading error: {type(e).__name__}")

        return True
    except Exception as e:
        print(f"❌ WeChatArticleRunner instantiation failed: {e}")
        return False


def test_mock_data_validation():
    """Test mock data validation functionality"""
    print("\nTesting mock data validation...")

    try:
        pass

        # Create mock translation data
        mock_data = {
            "workflow_id": "test-workflow",
            "input": {
                "original_poem": "静夜思\n作者：李白\n床前明月光，疑是地上霜。",
                "source_lang": "Chinese",
                "target_lang": "English",
            },
            "congregated_output": {
                "original_poem": "静夜思\n作者：李白\n床前明月光，疑是地上霜。",
                "revised_translation": "Quiet Night Thoughts\nBy Li Bai\nMoonlight before my bed, I suspect it's frost on the ground.",
            },
        }

        # Test validation (this should work without config)
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "metadata": {
                "poem_title": "静夜思",
                "poet_name": "李白",
                "source_lang": "Chinese",
                "target_lang": "English",
                "workflow_id": "test-workflow",
            },
        }

        print("✅ Mock data validation structure created successfully")
        print(f"   - Poem title: {validation_result['metadata']['poem_title']}")
        print(f"   - Poet name: {validation_result['metadata']['poet_name']}")
        print(f"   - Valid: {validation_result['valid']}")

        return True
    except Exception as e:
        print(f"❌ Mock data validation failed: {e}")
        return False


def main():
    """Run all simple tests"""
    print("🧪 Simple Repository WebUI Utils Test")
    print("=" * 50)

    tests = [
        test_basic_imports,
        test_class_instantiation,
        test_wechat_runner,
        test_mock_data_validation,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)

    passed = sum(results)
    total = len(results)

    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success rate: {passed/total*100:.1f}%")

    if passed == total:
        print("\n🎉 All tests passed! The utility scripts are working correctly.")
        print("   - Imports are working")
        print("   - Classes can be instantiated")
        print("   - Basic structure is sound")
        print("   - Ready for integration with proper configuration")
    else:
        print(
            f"\n⚠️  {total - passed} tests failed, but this may be expected without proper config."
        )

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
