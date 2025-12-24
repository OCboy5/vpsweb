"""
Essential tests for the OutputParser class.

Only tests critical functionality - XML parsing and error handling.
"""

import pytest
from src.vpsweb.services.parser import OutputParser


class TestOutputParser:
    """Essential OutputParser tests."""

    def test_parse_xml_basic_content(self):
        """Test XML parser correctly extracts basic content."""
        xml_string = """
        <initial_translation>雾来了
        踏着猫的小脚。</initial_translation>
        <initial_translation_notes>This translation captures gentle imagery.
        </initial_translation_notes>
        """

        result = OutputParser.parse_xml(xml_string)

        assert "initial_translation" in result
        assert "initial_translation_notes" in result
        assert "雾来了" in result["initial_translation"]
        assert "gentle imagery" in result["initial_translation_notes"]

    def test_parse_xml_error_handling(self):
        """Test that XML parser handles malformed input gracefully."""
        malformed_xml = """
        <initial_translation>Unclosed tag
        <another_tag>content</another_tag>
        """

        result = OutputParser.parse_xml(malformed_xml)

        # Should return empty dict or partial results for malformed XML
        assert isinstance(result, dict)

    def test_parse_xml_empty_input(self):
        """Test parser behavior with empty input."""
        # Current parser implementation raises XMLParsingError for empty input
        from src.vpsweb.services.parser import XMLParsingError

        with pytest.raises(XMLParsingError):
            OutputParser.parse_xml("")
