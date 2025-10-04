"""
Unit tests for the OutputParser class.

These tests verify the XML parsing functionality matches the exact logic
from docs/vpts.yml and handles various edge cases.
"""

import pytest
from src.vpsweb.services.parser import OutputParser, XMLParsingError, ValidationError


class TestOutputParser:
    """Test cases for OutputParser functionality."""

    def test_parse_xml_basic(self):
        """Test basic XML parsing."""
        xml_string = """
        <initial_translation>雾来了\n踏着猫的小脚。</initial_translation>
        <initial_translation_notes>This translation captures the gentle imagery.</initial_translation_notes>
        """

        result = OutputParser.parse_xml(xml_string)

        assert 'initial_translation' in result
        assert 'initial_translation_notes' in result
        assert result['initial_translation'] == '雾来了\n踏着猫的小脚。'
        assert result['initial_translation_notes'] == 'This translation captures the gentle imagery.'

    def test_parse_xml_with_whitespace_normalization(self):
        """Test that whitespace between tags is normalized (from vpts.yml logic)."""
        xml_string = """
        <initial_translation>
          雾来了
          踏着猫的小脚。
        </initial_translation>
        <initial_translation_notes>
          This translation captures the gentle imagery.
        </initial_translation_notes>
        """

        result = OutputParser.parse_xml(xml_string)

        # Whitespace should be preserved within content but normalized between tags
        assert 'initial_translation' in result
        assert 'initial_translation_notes' in result
        # Content should preserve internal whitespace but strip leading/trailing
        assert '雾来了\n          踏着猫的小脚。' in result['initial_translation']
        assert 'This translation captures the gentle imagery.' in result['initial_translation_notes']

    def test_parse_xml_nested_tags(self):
        """Test parsing XML with nested tags."""
        xml_string = """
        <outer>
          <inner1>Content 1</inner1>
          <inner2>Content 2</inner2>
        </outer>
        """

        result = OutputParser.parse_xml(xml_string)

        assert 'outer' in result
        assert isinstance(result['outer'], dict)
        assert 'inner1' in result['outer']
        assert 'inner2' in result['outer']
        assert result['outer']['inner1'] == 'Content 1'
        assert result['outer']['inner2'] == 'Content 2'

    def test_parse_xml_deeply_nested(self):
        """Test parsing deeply nested XML."""
        xml_string = """
        <level1>
          <level2>
            <level3>Deep content</level3>
          </level2>
        </level1>
        """

        result = OutputParser.parse_xml(xml_string)

        assert 'level1' in result
        assert isinstance(result['level1'], dict)
        assert 'level2' in result['level1']
        assert isinstance(result['level1']['level2'], dict)
        assert 'level3' in result['level1']['level2']
        assert result['level1']['level2']['level3'] == 'Deep content'

    def test_parse_xml_empty_content(self):
        """Test parsing XML with empty content."""
        xml_string = """
        <empty_tag></empty_tag>
        <whitespace_tag>   \n   </whitespace_tag>
        """

        result = OutputParser.parse_xml(xml_string)

        assert 'empty_tag' in result
        assert 'whitespace_tag' in result
        assert result['empty_tag'] == ''
        assert result['whitespace_tag'] == ''  # Whitespace stripped

    def test_parse_xml_single_line(self):
        """Test parsing single-line XML."""
        xml_string = '<tag>content</tag>'

        result = OutputParser.parse_xml(xml_string)

        assert 'tag' in result
        assert result['tag'] == 'content'

    def test_parse_xml_no_tags(self):
        """Test parsing string with no XML tags."""
        xml_string = "This is just plain text with no XML tags."

        result = OutputParser.parse_xml(xml_string)

        assert result == {}

    def test_parse_xml_malformed(self):
        """Test parsing malformed XML."""
        xml_string = "<open_tag>content"  # Missing closing tag

        result = OutputParser.parse_xml(xml_string)

        # Should return empty dict for malformed XML
        assert result == {}

    def test_parse_xml_unmatched_tags(self):
        """Test parsing XML with unmatched tags."""
        xml_string = "<tag1>content</tag2>"  # Mismatched tags

        result = OutputParser.parse_xml(xml_string)

        # Should not extract mismatched tags
        assert result == {}

    def test_parse_xml_special_characters(self):
        """Test parsing XML with special characters."""
        xml_string = """
        <special>Content with & symbols and "quotes"</special>
        """

        result = OutputParser.parse_xml(xml_string)

        assert 'special' in result
        assert 'Content with & symbols and "quotes"' in result['special']

    def test_parse_xml_with_attributes(self):
        """Test parsing XML with attributes (should ignore attributes)."""
        xml_string = """
        <tag attr="value">content</tag>
        """

        result = OutputParser.parse_xml(xml_string)

        # Should not extract tags with attributes (our regex is simple)
        assert result == {}

    def test_parse_xml_complex_initial_translation(self):
        """Test parsing complex initial translation XML."""
        xml_string = """
        <initial_translation>雾来了
        踏着猫的小脚。

        它坐下张望
        港口和城市
        在沉默的臀部
        然后继续前行。</initial_translation>
        <initial_translation_notes>This translation captures the gentle, quiet imagery of the original poem while maintaining the free verse structure. I chose to preserve the natural flow and avoid over-literal translation to maintain poetic beauty. The metaphor of "little cat feet" is translated to maintain its delicate, quiet connotation in Chinese culture.</initial_translation_notes>
        """

        result = OutputParser.parse_xml(xml_string)

        assert 'initial_translation' in result
        assert 'initial_translation_notes' in result
        assert isinstance(result['initial_translation'], str)
        assert isinstance(result['initial_translation_notes'], str)
        assert '雾来了' in result['initial_translation']
        assert 'This translation captures' in result['initial_translation_notes']

    def test_parse_xml_editor_suggestions_format(self):
        """Test parsing editor suggestions in the expected format."""
        xml_string = """
        Suggestions for Improving the Translation of "Fog" by Carl Sandburg:

        1. Line 1: Consider using a more poetic word for "雾来了"
        2. Line 2: The rhythm could be improved
        3. Lines 5-6: The translation of "on silent haunches" could be improved

        Overall assessment: This is a solid translation that captures the essence of the original poem.
        """

        result = OutputParser.parse_xml(xml_string)

        # Since this is plain text without XML tags, should return empty dict
        assert result == {}

    def test_extract_tags_basic(self):
        """Test extracting specific tags from XML."""
        xml_string = """
        <initial_translation>Translation content</initial_translation>
        <initial_translation_notes>Notes content</initial_translation_notes>
        <extra_tag>Extra content</extra_tag>
        """

        result = OutputParser.extract_tags(xml_string, ['initial_translation', 'initial_translation_notes'])

        assert 'initial_translation' in result
        assert 'initial_translation_notes' in result
        assert 'extra_tag' not in result  # Should not extract unrequested tags
        assert result['initial_translation'] == 'Translation content'
        assert result['initial_translation_notes'] == 'Notes content'

    def test_extract_tags_missing_tags(self):
        """Test extracting tags when some are missing."""
        xml_string = """
        <initial_translation>Translation content</initial_translation>
        """

        result = OutputParser.extract_tags(xml_string, ['initial_translation', 'missing_tag'])

        assert 'initial_translation' in result
        assert 'missing_tag' not in result  # Missing tag should not be in result
        assert result['initial_translation'] == 'Translation content'

    def test_extract_tags_empty_list(self):
        """Test extracting with empty tag list."""
        xml_string = "<tag>content</tag>"

        result = OutputParser.extract_tags(xml_string, [])

        assert result == {}

    def test_validate_output_basic(self):
        """Test basic output validation."""
        parsed_data = {
            'initial_translation': 'Translation content',
            'initial_translation_notes': 'Notes content'
        }

        is_valid = OutputParser.validate_output(parsed_data, ['initial_translation', 'initial_translation_notes'])

        assert is_valid is True

    def test_validate_output_missing_fields(self):
        """Test validation with missing required fields."""
        parsed_data = {
            'initial_translation': 'Translation content'
            # Missing initial_translation_notes
        }

        with pytest.raises(ValidationError) as exc_info:
            OutputParser.validate_output(parsed_data, ['initial_translation', 'initial_translation_notes'])

        assert 'Missing fields' in str(exc_info.value)
        assert 'initial_translation_notes' in str(exc_info.value)

    def test_validate_output_empty_fields(self):
        """Test validation with empty required fields."""
        parsed_data = {
            'initial_translation': 'Translation content',
            'initial_translation_notes': '   '  # Only whitespace
        }

        with pytest.raises(ValidationError) as exc_info:
            OutputParser.validate_output(parsed_data, ['initial_translation', 'initial_translation_notes'])

        assert 'Empty fields' in str(exc_info.value)
        assert 'initial_translation_notes' in str(exc_info.value)

    def test_validate_output_none_fields(self):
        """Test validation with None fields."""
        parsed_data = {
            'initial_translation': 'Translation content',
            'initial_translation_notes': None
        }

        with pytest.raises(ValidationError) as exc_info:
            OutputParser.validate_output(parsed_data, ['initial_translation', 'initial_translation_notes'])

        assert 'Empty fields' in str(exc_info.value)

    def test_validate_output_non_dict_input(self):
        """Test validation with non-dict input."""
        with pytest.raises(ValidationError) as exc_info:
            OutputParser.validate_output("not a dict", ['field1'])

        assert 'Expected dict for validation' in str(exc_info.value)

    def test_validate_output_empty_required_list(self):
        """Test validation with empty required fields list."""
        parsed_data = {'any': 'data'}

        is_valid = OutputParser.validate_output(parsed_data, [])

        assert is_valid is True

    def test_parse_initial_translation_xml(self):
        """Test parsing initial translation XML specifically."""
        xml_string = """
        <initial_translation>雾来了\n踏着猫的小脚。</initial_translation>
        <initial_translation_notes>This translation captures the gentle imagery.</initial_translation_notes>
        """

        result = OutputParser.parse_initial_translation_xml(xml_string)

        assert 'initial_translation' in result
        assert 'initial_translation_notes' in result
        assert result['initial_translation'] == '雾来了\n踏着猫的小脚。'
        assert result['initial_translation_notes'] == 'This translation captures the gentle imagery.'

    def test_parse_initial_translation_xml_missing_translation(self):
        """Test parsing initial translation XML when translation is missing."""
        xml_string = """
        <initial_translation_notes>Only notes, no translation</initial_translation_notes>
        """

        with pytest.raises(XMLParsingError) as exc_info:
            OutputParser.parse_initial_translation_xml(xml_string)

        assert "Missing required 'initial_translation' tag" in str(exc_info.value)

    def test_parse_revised_translation_xml(self):
        """Test parsing revised translation XML specifically."""
        xml_string = """
        <revised_translation>雾悄悄地来了\n像猫一样轻盈。</revised_translation>
        <revised_translation_notes>Based on editor suggestions, I refined the translation.</revised_translation_notes>
        """

        result = OutputParser.parse_revised_translation_xml(xml_string)

        assert 'revised_translation' in result
        assert 'revised_translation_notes' in result
        assert result['revised_translation'] == '雾悄悄地来了\n像猫一样轻盈。'
        assert result['revised_translation_notes'] == 'Based on editor suggestions, I refined the translation.'

    def test_is_valid_xml_valid(self):
        """Test XML validation with valid XML."""
        xml_string = "<tag>content</tag>"

        is_valid = OutputParser.is_valid_xml(xml_string)

        assert is_valid is True

    def test_is_valid_xml_invalid(self):
        """Test XML validation with invalid XML."""
        xml_string = "This is not XML"

        is_valid = OutputParser.is_valid_xml(xml_string)

        assert is_valid is False

    def test_is_valid_xml_malformed(self):
        """Test XML validation with malformed XML."""
        xml_string = "<unclosed_tag>content"

        is_valid = OutputParser.is_valid_xml(xml_string)

        assert is_valid is False

    def test_get_xml_structure(self):
        """Test XML structure analysis."""
        xml_string = """
        <level1>
          <level2>
            <level3>Deep content</level3>
          </level2>
        </level1>
        """

        structure = OutputParser.get_xml_structure(xml_string)

        assert 'root_tags' in structure
        assert 'structure' in structure
        assert 'total_tags' in structure
        assert 'level1' in structure['root_tags']
        assert structure['total_tags'] == 1

    def test_get_xml_structure_invalid(self):
        """Test XML structure analysis with invalid XML."""
        xml_string = "This is not XML"

        structure = OutputParser.get_xml_structure(xml_string)

        assert 'error' in structure
        assert structure['root_tags'] == []

    def test_sanitize_xml_content(self):
        """Test XML content sanitization."""
        content = 'Text with & symbols and <> brackets and "quotes"'

        sanitized = OutputParser.sanitize_xml_content(content)

        assert '&amp;' in sanitized
        assert '&lt;' in sanitized
        assert '&gt;' in sanitized
        assert '&quot;' in sanitized
        # Check that all special characters are properly escaped
        # The original &, <, >, " should be replaced with their escaped versions
        # The count should be 5: &amp; (2 &'s), &lt;, &gt;, &quot; (2 &'s)
        assert sanitized.count('&') == 5  # All special chars should be escaped with &

    def test_convenience_functions(self):
        """Test convenience functions for parsing."""
        xml_string = """
        <initial_translation>Test translation</initial_translation>
        <initial_translation_notes>Test notes</initial_translation_notes>
        """

        from src.vpsweb.services.parser import parse_initial_translation, parse_revised_translation, extract_translation_data

        # Test initial translation parsing
        result = parse_initial_translation(xml_string)
        assert result['initial_translation'] == 'Test translation'
        assert result['initial_translation_notes'] == 'Test notes'

        # Test extract translation data
        result = extract_translation_data(xml_string, "initial")
        assert result['initial_translation'] == 'Test translation'

        # Test revised translation parsing (should work with same structure)
        # (Just change the tag names in the XML)
        revised_xml = xml_string.replace('initial_', 'revised_')
        result = parse_revised_translation(revised_xml)
        assert result['revised_translation'] == 'Test translation'
        assert result['revised_translation_notes'] == 'Test notes'

    def test_real_world_initial_translation_example(self):
        """Test with a realistic initial translation example."""
        xml_string = """
        <initial_translation>雾来了
        踏着猫的小脚。

        它坐下张望
        港口和城市
        在沉默的臀部
        然后继续前行。</initial_translation>
        <initial_translation_notes>This translation captures the gentle, quiet imagery of the original poem while maintaining the free verse structure. I chose to preserve the natural flow and avoid over-literal translation to maintain poetic beauty. The metaphor of "little cat feet" is translated to maintain its delicate, quiet connotation in Chinese culture.</initial_translation_notes>
        """

        result = OutputParser.parse_xml(xml_string)

        assert 'initial_translation' in result
        assert 'initial_translation_notes' in result
        assert isinstance(result['initial_translation'], str)
        assert isinstance(result['initial_translation_notes'], str)
        assert '雾来了' in result['initial_translation']
        assert 'This translation captures' in result['initial_translation_notes']

        # Test the specific convenience function
        translation_data = OutputParser.parse_initial_translation_xml(xml_string)
        assert translation_data['initial_translation'] == result['initial_translation']
        assert translation_data['initial_translation_notes'] == result['initial_translation_notes']

    def test_real_world_editor_suggestions_format(self):
        """Test parsing editor suggestions in the expected format."""
        xml_string = """
        Suggestions for Improving the Translation of "Fog" by Carl Sandburg:

        1. Line 1: Consider using a more poetic word for "雾来了"
        2. Line 2: The rhythm could be improved
        3. Lines 5-6: The translation of "on silent haunches" could be improved

        Overall assessment: This is a solid translation that captures the essence of the original poem.
        """

        result = OutputParser.parse_xml(xml_string)

        # Since this is plain text without XML tags, should return empty dict
        assert result == {}

        # Test that it's considered invalid XML
        is_valid = OutputParser.is_valid_xml(xml_string)
        assert is_valid is False

    def test_edge_case_empty_string(self):
        """Test edge case with empty string."""
        with pytest.raises(XMLParsingError):
            OutputParser.parse_xml("")

    def test_edge_case_none_input(self):
        """Test edge case with None input."""
        with pytest.raises(XMLParsingError):
            OutputParser.parse_xml(None)

    def test_edge_case_non_string_input(self):
        """Test edge case with non-string input."""
        with pytest.raises(XMLParsingError):
            OutputParser.parse_xml(123)

    def test_complex_nested_structure(self):
        """Test complex nested XML structure."""
        xml_string = """
        <workflow>
          <step1>
            <result>Success</result>
            <data>
              <item>Item 1</item>
              <item>Item 2</item>
            </data>
          </step1>
          <step2>Simple result</step2>
        </workflow>
        """

        result = OutputParser.parse_xml(xml_string)

        assert 'workflow' in result
        assert isinstance(result['workflow'], dict)
        assert 'step1' in result['workflow']
        assert 'step2' in result['workflow']
        assert isinstance(result['workflow']['step1'], dict)
        assert 'result' in result['workflow']['step1']
        assert 'data' in result['workflow']['step1']
        assert isinstance(result['workflow']['step1']['data'], dict)
        assert 'item' in result['workflow']['step1']['data']  # Only one item key (last one wins)

    def test_mixed_content_with_text_and_tags(self):
        """Test XML with mixed content (text and tags)."""
        xml_string = """
        <mixed>
          Some text here
          <nested>Nested content</nested>
          More text
        </mixed>
        """

        result = OutputParser.parse_xml(xml_string)

        # Our simple regex parser will extract the nested tag but not the mixed text
        assert 'mixed' in result
        assert isinstance(result['mixed'], dict)
        assert 'nested' in result['mixed']
        assert result['mixed']['nested'] == 'Nested content'

    def test_parser_repr(self):
        """Test string representation of parser."""
        parser = OutputParser()
        repr_str = repr(parser)
        assert 'OutputParser()' in repr_str


class TestParserConvenienceFunctions:
    """Test convenience functions for common parsing tasks."""

    def test_parse_initial_translation_convenience(self):
        """Test the parse_initial_translation convenience function."""
        from src.vpsweb.services.parser import parse_initial_translation

        xml_string = """
        <initial_translation>Test translation</initial_translation>
        <initial_translation_notes>Test notes</initial_translation_notes>
        """

        result = parse_initial_translation(xml_string)

        assert result['initial_translation'] == 'Test translation'
        assert result['initial_translation_notes'] == 'Test notes'

    def test_parse_revised_translation_convenience(self):
        """Test the parse_revised_translation convenience function."""
        from src.vpsweb.services.parser import parse_revised_translation

        xml_string = """
        <revised_translation>Revised translation</revised_translation>
        <revised_translation_notes>Revised notes</revised_translation_notes>
        """

        result = parse_revised_translation(xml_string)

        assert result['revised_translation'] == 'Revised translation'
        assert result['revised_translation_notes'] == 'Revised notes'

    def test_extract_translation_data_convenience(self):
        """Test the extract_translation_data convenience function."""
        from src.vpsweb.services.parser import extract_translation_data

        # Test initial translation
        initial_xml = """
        <initial_translation>Initial translation</initial_translation>
        <initial_translation_notes>Initial notes</initial_translation_notes>
        """

        result = extract_translation_data(initial_xml, "initial")
        assert result['initial_translation'] == 'Initial translation'

        # Test revised translation
        revised_xml = """
        <revised_translation>Revised translation</revised_translation>
        <revised_translation_notes>Revised notes</revised_translation_notes>
        """

        result = extract_translation_data(revised_xml, "revised")
        assert result['revised_translation'] == 'Revised translation'

        # Test invalid translation type
        with pytest.raises(ValueError) as exc_info:
            extract_translation_data("any xml", "invalid_type")

        assert "Unsupported translation type: invalid_type" in str(exc_info.value)


class TestParserIntegration:
    """Integration tests for the complete parsing workflow."""

    def test_complete_initial_translation_workflow(self):
        """Test complete workflow for initial translation parsing."""
        xml_string = """
        <initial_translation>雾来了\n踏着猫的小脚。\n\n它坐下张望\n港口和城市\n在沉默的臀部\n然后继续前行。\u003c/initial_translation>
        <initial_translation_notes>This translation captures the gentle, quiet imagery of the original poem while maintaining the free verse structure. I chose to preserve the natural flow and avoid over-literal translation to maintain poetic beauty. The metaphor of "little cat feet" is translated to maintain its delicate, quiet connotation in Chinese culture.\u003c/initial_translation_notes>
        """

        # Parse the XML
        parsed_data = OutputParser.parse_xml(xml_string)

        # Extract specific tags
        extracted_data = OutputParser.extract_tags(xml_string, ['initial_translation', 'initial_translation_notes'])

        # Validate the output
        is_valid = OutputParser.validate_output(parsed_data, ['initial_translation', 'initial_translation_notes'])

        # Use convenience function
        from src.vpsweb.services.parser import parse_initial_translation
        translation_data = parse_initial_translation(xml_string)

        # Verify all methods work consistently
        assert is_valid is True
        assert 'initial_translation' in parsed_data
        assert 'initial_translation_notes' in parsed_data
        assert extracted_data['initial_translation'] == parsed_data['initial_translation']
        assert extracted_data['initial_translation_notes'] == parsed_data['initial_translation_notes']
        assert translation_data['initial_translation'] == parsed_data['initial_translation']
        assert translation_data['initial_translation_notes'] == parsed_data['initial_translation_notes']

    def test_complete_revised_translation_workflow(self):
        """Test complete workflow for revised translation parsing."""
        xml_string = """
        <revised_translation>雾悄悄地来了\n像猫一样轻盈的脚步。\n\n它静静地坐下\n俯瞰着港口和城市\n在无声的蹲伏中\n然后悄然离去。\u003c/revised_translation>
        <revised_translation_notes>Based on the editor's suggestions, I refined the translation to use more poetic and evocative language. I changed '雾来了' to '雾悄悄地来了' to better capture the gentle, stealthy nature of fog. The 'little cat feet' metaphor was enhanced to '像猫一样轻盈的脚步' (light footsteps like a cat). The 'silent haunches' was translated as '在无声的蹲伏中' which better conveys the quiet, watchful posture in Chinese poetic context.\u003c/revised_translation_notes>
        """

        # Use convenience function
        from src.vpsweb.services.parser import parse_revised_translation
        translation_data = parse_revised_translation(xml_string)

        # Verify structure
        assert 'revised_translation' in translation_data
        assert 'revised_translation_notes' in translation_data
        assert '雾悄悄地来了' in translation_data['revised_translation']
        assert 'Based on the editor\'s suggestions' in translation_data['revised_translation_notes']

        # Validate using the generic method
        parsed_data = OutputParser.parse_xml(xml_string)
        is_valid = OutputParser.validate_output(parsed_data, ['revised_translation', 'revised_translation_notes'])
        assert is_valid is True

    def test_error_recovery_workflow(self):
        """Test error recovery in parsing workflow."""
        # Test with malformed XML
        malformed_xml = "This is not valid XML"

        # Should handle gracefully and return empty dict
        result = OutputParser.parse_xml(malformed_xml)
        assert result == {}

        # Should be detected as invalid
        is_valid = OutputParser.is_valid_xml(malformed_xml)
        assert is_valid is False

        # Convenience functions should handle errors gracefully
        from src.vpsweb.services.parser import parse_initial_translation
        with pytest.raises(XMLParsingError):
            parse_initial_translation(malformed_xml)

    def test_complex_nested_workflow(self):
        """Test parsing complex nested structures."""
        xml_string = """
        <workflow_result>
          <translation>
            <initial>First translation</initial>
            <revised>Final translation</revised>
          </translation>
          <metadata>
            <tokens_used>1500</tokens_used>
            <duration>45.5</duration>
          </metadata>
        </workflow_result>
        """

        result = OutputParser.parse_xml(xml_string)

        assert 'workflow_result' in result
        assert isinstance(result['workflow_result'], dict)
        assert 'translation' in result['workflow_result']
        assert 'metadata' in result['workflow_result']
        assert isinstance(result['workflow_result']['translation'], dict)
        assert 'initial' in result['workflow_result']['translation']
        assert 'revised' in result['workflow_result']['translation']
        assert result['workflow_result']['translation']['initial'] == 'First translation'
        assert result['workflow_result']['translation']['revised'] == 'Final translation'

        # Test structure analysis
        structure = OutputParser.get_xml_structure(xml_string)
        assert 'workflow_result' in structure['root_tags']
        assert structure['total_tags'] == 1


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v"])  # noqa: E501