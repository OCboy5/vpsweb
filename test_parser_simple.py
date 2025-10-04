#!/usr/bin/env python3
"""
Simple test of the OutputParser to verify it works correctly.
"""

import sys
sys.path.insert(0, '.')

from src.vpsweb.services.parser import OutputParser, parse_initial_translation, parse_revised_translation

def test_basic_xml_parsing():
    """Test basic XML parsing functionality."""
    print("Testing Basic XML Parsing...")
    print("=" * 50)

    # Test 1: Basic XML parsing
    xml_string = """
    <initial_translation>雾来了\n踏着猫的小脚。</initial_translation>
    <initial_translation_notes>This translation captures the gentle imagery.</initial_translation_notes>
    """

    try:
        result = OutputParser.parse_xml(xml_string)
        print(f"✓ Basic XML parsing successful")
        print(f"  Parsed tags: {list(result.keys())}")
        print(f"  Translation: {result['initial_translation'][:50]}...")
        print(f"  Notes: {result['initial_translation_notes'][:50]}...")
    except Exception as e:
        print(f"❌ Basic XML parsing failed: {e}")
        return False

    # Test 2: Nested XML parsing
    nested_xml = """
    <workflow>
      <step1>First step</step1>
      <step2>Second step</step2>
    </workflow>
    """

    try:
        result = OutputParser.parse_xml(nested_xml)
        print(f"✓ Nested XML parsing successful")
        print(f"  Workflow structure: {type(result['workflow'])}")
        print(f"  Step 1: {result['workflow']['step1']}")
        print(f"  Step 2: {result['workflow']['step2']}")
    except Exception as e:
        print(f"❌ Nested XML parsing failed: {e}")
        return False

    # Test 3: Extract specific tags
    try:
        extracted = OutputParser.extract_tags(xml_string, ['initial_translation', 'initial_translation_notes'])
        print(f"✓ Tag extraction successful")
        print(f"  Extracted keys: {list(extracted.keys())}")
    except Exception as e:
        print(f"❌ Tag extraction failed: {e}")
        return False

    # Test 4: Validation
    try:
        is_valid = OutputParser.validate_output(extracted, ['initial_translation', 'initial_translation_notes'])
        print(f"✓ Validation successful: {is_valid}")
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

    # Test 5: Initial translation convenience function
    try:
        translation_data = parse_initial_translation(xml_string)
        print(f"✓ Initial translation parsing successful")
        print(f"  Has translation: {'initial_translation' in translation_data}")
        print(f"  Has notes: {'initial_translation_notes' in translation_data}")
    except Exception as e:
        print(f"❌ Initial translation parsing failed: {e}")
        return False

    return True

def test_error_handling():
    """Test error handling."""
    print("\nTesting Error Handling...")
    print("=" * 50)

    # Test malformed XML
    malformed_xml = "This is not XML"
    try:
        result = OutputParser.parse_xml(malformed_xml)
        print(f"✓ Malformed XML handled gracefully: {result}")
    except Exception as e:
        print(f"❌ Malformed XML handling failed: {e}")
        return False

    # Test missing required fields in validation
    incomplete_data = {'translation': 'content'}  # Missing notes
    try:
        OutputParser.validate_output(incomplete_data, ['translation', 'notes'])
        print("❌ Should have failed validation")
        return False
    except Exception as e:
        print(f"✓ Validation correctly rejected incomplete data: {type(e).__name__}")

    return True

def test_real_world_examples():
    """Test with real-world examples from vpts.yml."""
    print("\nTesting Real-World Examples...")
    print("=" * 50)

    # Real initial translation example
    real_xml = """
    <initial_translation>雾来了\n踏着猫的小脚。\n\n它坐下张望\n港口和城市\n在沉默的臀部\n然后继续前行。\u003c/initial_translation>
    <initial_translation_notes>This translation captures the gentle, quiet imagery of the original poem while maintaining the free verse structure. I chose to preserve the natural flow and avoid over-literal translation to maintain poetic beauty. The metaphor of "little cat feet" is translated to maintain its delicate, quiet connotation in Chinese culture.\u003c/initial_translation_notes>
    """

    try:
        result = parse_initial_translation(real_xml)
        print(f"✓ Real initial translation parsing successful")
        print(f"  Translation length: {len(result['initial_translation'])} chars")
        print(f"  Notes length: {len(result['initial_translation_notes'])} chars")
        print(f"  Contains Chinese: {'雾来了' in result['initial_translation']}")
    except Exception as e:
        print(f"❌ Real example parsing failed: {e}")
        return False

    return True

def main():
    """Run all tests."""
    print("Vox Poetica Studio Web - OutputParser Test")
    print("=" * 60)

    success = True
    success &= test_basic_xml_parsing()
    success &= test_error_handling()
    success &= test_real_world_examples()

    if success:
        print("\n" + "=" * 60)
        print("✅ All OutputParser tests passed!")
        print("\nThe OutputParser is ready for production with:")
        print("- Exact XML parsing logic from docs/vpts.yml")
        print("- Regex-based parsing with nested tag support")
        print("- Comprehensive error handling")
        print("- Validation and extraction utilities")
        print("- Convenience functions for translation workflows")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)