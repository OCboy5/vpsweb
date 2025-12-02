"""
XML output parser for Vox Poetica Studio Web.

This module provides utilities for parsing XML-formatted responses from LLM providers,
extracting structured data, and validating parsed outputs based on the exact parsing
logic from docs/vpts.yml.
"""

import re
from typing import Dict, Any, List, Optional, Union
import logging

logger = logging.getLogger(__name__)


class ParserError(Exception):
    """Base exception for parser errors."""

    pass


class XMLParsingError(ParserError):
    """Raised when XML parsing fails."""

    pass


class ValidationError(ParserError):
    """Raised when output validation fails."""

    pass


class EmptyNotesFieldError(ValidationError):
    """Raised when notes fields contain empty JSON objects."""

    def __init__(self, field_name: str, step_name: str):
        self.field_name = field_name
        self.step_name = step_name
        message = (
            f"Notes field '{field_name}' is empty ({{}}) after {step_name} step. "
            f"LLM response must provide meaningful notes content."
        )
        super().__init__(message)


class OutputParser:
    """
    Parser for extracting structured data from XML-formatted LLM responses.

    This parser implements the exact XML parsing logic from docs/vpts.yml,
    handling nested tags, whitespace normalization, and comprehensive error cases.
    """

    @staticmethod
    def parse_xml(xml_string: str) -> Dict[str, Any]:
        """
        Parse XML string and extract all tags with their content.

        This method implements the exact parsing logic from docs/vpts.yml:
        - Removes whitespace between tags
        - Uses regex to find all tags and their contents
        - Handles nested tags recursively
        - Strips whitespace from content

        Args:
            xml_string: XML-formatted string to parse

        Returns:
            Dictionary mapping tag names to their content

        Raises:
            XMLParsingError: If parsing fails or XML is malformed
        """
        if not xml_string or not isinstance(xml_string, str):
            raise XMLParsingError(
                f"Invalid XML input: expected non-empty string, got {type(xml_string)}"
            )

        try:
            # Remove whitespace between tags (exact logic from vpts.yml)
            xml_string = re.sub(r"\s+(<|>)", r"\1", xml_string.strip())

            # Find all tags and their contents (exact pattern from vpts.yml)
            pattern = r"<(\w+)>(.*?)</\1>"
            matches = re.findall(pattern, xml_string, re.DOTALL)

            if not matches:
                logger.warning(f"No XML tags found in string: {xml_string[:100]}...")
                return {}

            result = {}
            for tag, content in matches:
                # Recursively parse nested tags if present (exact logic from vpts.yml)
                if re.search(r"<\w+>", content):
                    result[tag] = OutputParser.parse_xml(
                        content
                    )  # Recursive call for nested tags
                else:
                    result[tag] = (
                        content  # Preserve internal whitespace, don't strip content
                    )

            logger.debug(
                f"Successfully parsed XML with {len(result)} tags: {list(result.keys())}"
            )
            return result

        except re.error as e:
            raise XMLParsingError(f"Regex error while parsing XML: {e}")
        except Exception as e:
            raise XMLParsingError(f"Unexpected error parsing XML: {e}")

    @staticmethod
    def extract_tags(xml_string: str, tags: List[str]) -> Dict[str, Any]:
        """
        Extract specific tags from XML string.

        Args:
            xml_string: XML-formatted string to parse
            tags: List of tag names to extract

        Returns:
            Dictionary with only the requested tags

        Raises:
            XMLParsingError: If parsing fails
        """
        if not tags:
            return {}

        parsed_data = OutputParser.parse_xml(xml_string)

        # Extract only requested tags
        result = {}
        missing_tags = []

        for tag in tags:
            if tag in parsed_data:
                result[tag] = parsed_data[tag]
            else:
                missing_tags.append(tag)

        if missing_tags:
            logger.warning(
                f"Missing expected tags: {missing_tags}. Available tags: {list(parsed_data.keys())}"
            )

        logger.debug(
            f"Extracted {len(result)} of {len(tags)} requested tags: {list(result.keys())}"
        )
        return result

    @staticmethod
    def validate_output(
        parsed_data: Dict[str, Any], required_fields: List[str]
    ) -> bool:
        """
        Validate that parsed output contains all required fields.

        Args:
            parsed_data: Dictionary from parse_xml()
            required_fields: List of field names that must be present

        Returns:
            True if all required fields are present

        Raises:
            ValidationError: If validation fails with details
        """
        if not required_fields:
            return True

        if not isinstance(parsed_data, dict):
            raise ValidationError(
                f"Expected dict for validation, got {type(parsed_data)}"
            )

        missing_fields = []
        empty_fields = []

        for field in required_fields:
            if field not in parsed_data:
                missing_fields.append(field)
            elif (
                isinstance(parsed_data[field], str) and not parsed_data[field].strip()
            ) or (parsed_data[field] is None):
                empty_fields.append(field)
            # Additional check for empty JSON objects
            elif (
                isinstance(parsed_data[field], str)
                and parsed_data[field].strip() == "{}"
            ):
                empty_fields.append(field)

        if missing_fields or empty_fields:
            error_messages = []
            if missing_fields:
                error_messages.append(f"Missing fields: {missing_fields}")
            if empty_fields:
                error_messages.append(f"Empty fields: {empty_fields}")
            available_fields = list(parsed_data.keys())

            raise ValidationError(
                f"Output validation failed: {'; '.join(error_messages)}. "
                f"Available fields: {available_fields}"
            )

        logger.debug(f"Output validation passed for fields: {required_fields}")
        return True

    @staticmethod
    def parse_initial_translation_xml(xml_string: str) -> Dict[str, str]:
        """
        Parse initial translation XML specifically with support for translated titles and poet names.

        Args:
            xml_string: XML string from initial translation step

        Returns:
            Dictionary with 'initial_translation', 'initial_translation_notes',
            'translated_poem_title', and 'translated_poet_name'

        Raises:
            XMLParsingError: If parsing fails or expected tags are missing
        """
        try:
            parsed_data = OutputParser.parse_xml(xml_string)

            # Handle nested structure - check if we have a 'translation' wrapper
            if "translation" in parsed_data:
                content = parsed_data["translation"]
                if isinstance(content, str):
                    content = OutputParser.parse_xml(content)
            else:
                content = parsed_data

            # Extract specific fields (updated to include translated title and poet name)
            initial_translation = str(content.get("initial_translation", ""))
            initial_translation_notes = str(
                content.get("initial_translation_notes", "")
            )
            translated_poem_title = str(
                content.get("translated_poem_title", "")
            ).strip()
            translated_poet_name = str(content.get("translated_poet_name", "")).strip()

            if not initial_translation:
                raise XMLParsingError(
                    "Missing required 'initial_translation' tag in XML"
                )

            result = {
                "initial_translation": initial_translation,
                "initial_translation_notes": initial_translation_notes,
                "translated_poem_title": translated_poem_title,
                "translated_poet_name": translated_poet_name,
            }

            logger.debug(
                f"Successfully parsed initial translation XML with {len([k for k, v in result.items() if v])} fields"
            )
            return result

        except KeyError as e:
            raise XMLParsingError(
                f"Missing expected tag in initial translation XML: {e}"
            )
        except Exception as e:
            raise XMLParsingError(f"Error parsing initial translation XML: {e}")

    @staticmethod
    def parse_revised_translation_xml(xml_string: str) -> Dict[str, str]:
        """
        Parse revised translation XML specifically with support for refined translated titles and poet names.

        Args:
            xml_string: XML string from translator revision step

        Returns:
            Dictionary with 'revised_translation', 'revised_translation_notes',
            'refined_translated_poem_title', and 'refined_translated_poet_name'

        Raises:
            XMLParsingError: If parsing fails or expected tags are missing
        """
        try:
            parsed_data = OutputParser.parse_xml(xml_string)
            if isinstance(parsed_data, str):
                parsed_data = OutputParser.parse_xml(parsed_data)

            # Extract specific fields (updated to include refined translated title and poet name)
            revised_translation = str(parsed_data.get("revised_translation", ""))
            revised_translation_notes = str(
                parsed_data.get("revised_translation_notes", "")
            )
            refined_translated_poem_title = str(
                parsed_data.get("refined_translated_poem_title", "")
            ).strip()
            refined_translated_poet_name = str(
                parsed_data.get("refined_translated_poet_name", "")
            ).strip()

            if not revised_translation:
                raise XMLParsingError(
                    "Missing required 'revised_translation' tag in XML"
                )

            result = {
                "revised_translation": revised_translation,
                "revised_translation_notes": revised_translation_notes,
                "refined_translated_poem_title": refined_translated_poem_title,
                "refined_translated_poet_name": refined_translated_poet_name,
            }

            logger.debug(
                f"Successfully parsed revised translation XML with {len([k for k, v in result.items() if v])} fields"
            )
            return result

        except KeyError as e:
            raise XMLParsingError(
                f"Missing expected tag in revised translation XML: {e}"
            )
        except Exception as e:
            raise XMLParsingError(f"Error parsing revised translation XML: {e}")

    @staticmethod
    def parse_editor_review_xml(xml_string: str) -> Dict[str, str]:
        """
        Parse editor review XML specifically, with robust handling of malformed XML.

        Args:
            xml_string: XML string from editor review step

        Returns:
            Dictionary with 'editor_suggestions'

        Raises:
            XMLParsingError: If parsing fails
        """
        try:
            # Find the start of the editor_suggestions tag
            start_tag = "<editor_suggestions>"
            start_index = xml_string.find(start_tag)

            if start_index == -1:
                # If start tag is not found, try to parse as a whole
                parsed_data = OutputParser.parse_xml(xml_string)
                if "editor_suggestions" in parsed_data:
                    return {"editor_suggestions": parsed_data["editor_suggestions"]}
                else:
                    # As a last resort, return the whole string if no tags are found
                    logger.warning(
                        "Could not find <editor_suggestions> tag, returning raw content."
                    )
                    return {"editor_suggestions": xml_string}

            # Find the end of the editor_suggestions tag
            end_tag = "</editor_suggestions>"
            end_index = xml_string.rfind(end_tag)

            if end_index == -1:
                # If end tag is not found, extract from start tag to the end of the string
                logger.warning(
                    "Missing </editor_suggestions> closing tag. Parsing to end of string."
                )
                content = xml_string[start_index + len(start_tag) :]
            else:
                # If both tags are found, extract the content between them
                content = xml_string[start_index + len(start_tag) : end_index]

            return {"editor_suggestions": content.strip()}

        except Exception as e:
            raise XMLParsingError(f"Error parsing editor review XML: {e}")

    @staticmethod
    def is_valid_xml(xml_string: str) -> bool:
        """
        Check if a string contains valid XML structure.

        Args:
            xml_string: String to validate

        Returns:
            True if string contains valid XML tags
        """
        if not xml_string or not isinstance(xml_string, str):
            return False

        try:
            result = OutputParser.parse_xml(xml_string)
            return len(result) > 0
        except XMLParsingError:
            return False

    @staticmethod
    def get_xml_structure(xml_string: str) -> Dict[str, Any]:
        """
        Analyze XML structure and return tag hierarchy.

        Args:
            xml_string: XML string to analyze

        Returns:
            Dictionary describing the XML structure
        """
        try:
            parsed_data = OutputParser.parse_xml(xml_string)

            # Check if parsing actually found any tags
            if not parsed_data:
                return {"error": "Invalid XML structure", "root_tags": []}

            def analyze_structure(data, prefix=""):
                structure = {}
                for key, value in data.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, dict):
                        structure[full_key] = {
                            "type": "nested",
                            "children": analyze_structure(value, full_key),
                        }
                    else:
                        structure[full_key] = {
                            "type": "string",
                            "length": len(str(value)),
                        }
                return structure

            return {
                "root_tags": list(parsed_data.keys()),
                "structure": analyze_structure(parsed_data),
                "total_tags": len(parsed_data),
            }

        except XMLParsingError:
            return {"error": "Invalid XML structure", "root_tags": []}

    @staticmethod
    def sanitize_xml_content(content: str) -> str:
        """
        Sanitize content for safe XML inclusion.

        Args:
            content: String content to sanitize

        Returns:
            Sanitized content safe for XML
        """
        if not content:
            return ""

        # Escape XML special characters
        content = content.replace("&", "&amp;")
        content = content.replace("<", "&lt;")
        content = content.replace(">", "&gt;")
        content = content.replace('"', "&quot;")
        content = content.replace("'", "&apos;")

        return content.strip()

    def __repr__(self) -> str:
        """String representation of the parser."""
        return "OutputParser()"


# Convenience functions for common parsing tasks
def parse_initial_translation(xml_string: str) -> Dict[str, str]:
    """Convenience function to parse initial translation XML."""
    return OutputParser.parse_initial_translation_xml(xml_string)


def parse_editor_review(xml_string: str) -> Dict[str, str]:
    """Convenience function to parse editor review XML."""
    return OutputParser.parse_editor_review_xml(xml_string)


def parse_revised_translation(xml_string: str) -> Dict[str, str]:
    """Convenience function to parse revised translation XML."""
    return OutputParser.parse_revised_translation_xml(xml_string)


def extract_translation_data(
    xml_string: str, translation_type: str = "initial"
) -> Dict[str, str]:
    """
    Extract translation data based on type.

    Args:
        xml_string: XML string to parse
        translation_type: 'initial' or 'revised'

    Returns:
        Dictionary with translation data
    """
    if translation_type == "initial":
        return parse_initial_translation(xml_string)
    elif translation_type == "revised":
        return parse_revised_translation(xml_string)
    else:
        raise ValueError(f"Unsupported translation type: {translation_type}")
