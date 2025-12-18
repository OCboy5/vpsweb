"""
XML parsing utilities for Vox Poetica Studio Web.

This module provides specialized XML parsing functions for LLM outputs,
particularly for WeChat translation notes structure.
"""

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from ..models.wechat import TranslationNotes
from .logger import get_logger

logger = get_logger(__name__)


class XMLParseError(Exception):
    """Exception raised for XML parsing errors."""


class WeChatXMLParser:
    """
    Specialized XML parser for WeChat LLM outputs.

    Handles parsing of structured XML responses from LLM providers,
    particularly for translation notes and other WeChat-specific content.
    """

    @staticmethod
    def parse_translation_notes(xml_content: str) -> TranslationNotes:
        """
        Parse WeChat translation notes from XML content.

        Args:
            xml_content: XML string containing wechat_translation_notes structure

        Returns:
            TranslationNotes with digest and bullet points

        Raises:
            XMLParseError: If parsing fails
        """
        try:
            # Clean and prepare XML content
            cleaned_xml = WeChatXMLParser._clean_xml_content(xml_content)

            # Parse XML
            root = ET.fromstring(cleaned_xml)

            # Validate root element
            if root.tag != "wechat_translation_notes":
                raise XMLParseError(
                    f"Expected root element 'wechat_translation_notes', got '{root.tag}'"
                )

            # Extract digest
            digest = WeChatXMLParser._extract_text_content(root, "digest")
            if not digest:
                raise XMLParseError("Missing or empty digest element")

            # Extract notes
            notes_container = root.find("notes")
            if notes_container is None:
                raise XMLParseError("Missing notes element")

            notes_text = notes_container.text or ""
            bullet_points = WeChatXMLParser._parse_bullet_points(notes_text)

            if not bullet_points:
                raise XMLParseError("No bullet points found in notes")

            # Create and return TranslationNotes
            return TranslationNotes(digest=digest.strip(), notes=bullet_points)

        except ET.ParseError as e:
            raise XMLParseError(f"XML parsing failed: {e}")
        except Exception as e:
            raise XMLParseError(f"Error parsing translation notes XML: {e}")

    @staticmethod
    def _clean_xml_content(xml_content: str) -> str:
        """
        Clean XML content for reliable parsing.

        Args:
            xml_content: Raw XML content from LLM

        Returns:
            Cleaned XML string
        """
        # Remove common LLM artifacts
        xml_content = re.sub(r"```xml\s*", "", xml_content)
        xml_content = re.sub(r"```\s*$", "", xml_content)
        xml_content = xml_content.strip()

        # Find XML content boundaries
        start_tag = "<wechat_translation_notes>"
        end_tag = "</wechat_translation_notes>"

        start_idx = xml_content.find(start_tag)
        end_idx = xml_content.rfind(end_tag)

        if start_idx == -1 or end_idx == -1:
            raise XMLParseError("Could not find XML boundaries in content")

        return xml_content[start_idx : end_idx + len(end_tag)]

    @staticmethod
    def _extract_text_content(root: ET.Element, tag: str) -> Optional[str]:
        """
        Extract text content from a specific tag.

        Args:
            root: XML root element
            tag: Tag name to extract

        Returns:
            Text content or None if not found
        """
        element = root.find(tag)
        if element is not None and element.text:
            return element.text.strip()
        return None

    @staticmethod
    def _parse_bullet_points(notes_text: str) -> List[str]:
        """
        Parse bullet points from notes text.

        Args:
            notes_text: Raw notes text content

        Returns:
            List of bullet point strings
        """
        bullet_points = []

        # Split by lines and clean up
        for line in notes_text.split("\n"):
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Handle different bullet formats
            if line.startswith("•"):
                # Standard bullet
                bullet_point = line[1:].strip()
            elif line.startswith("- "):
                # Dash bullet
                bullet_point = line[2:].strip()
            elif line.startswith("* "):
                # Asterisk bullet
                bullet_point = line[2:].strip()
            elif re.match(r"^\d+\.\s", line):
                # Numbered bullet
                bullet_point = re.sub(r"^\d+\.\s*", "", line).strip()
            else:
                # Plain line, include as is
                bullet_point = line

            if bullet_point:
                bullet_points.append(bullet_point)

        return bullet_points

    @staticmethod
    def validate_translation_notes_xml(xml_content: str) -> Dict[str, Any]:
        """
        Validate translation notes XML structure without parsing.

        Args:
            xml_content: XML content to validate

        Returns:
            Dictionary with validation results
        """
        result = {
            "is_valid": False,
            "errors": [],
            "warnings": [],
            "structure": {},
        }

        try:
            # Clean and parse XML
            cleaned_xml = WeChatXMLParser._clean_xml_content(xml_content)
            root = ET.fromstring(cleaned_xml)

            # Check root element
            if root.tag != "wechat_translation_notes":
                result["errors"].append(
                    f"Wrong root element: '{root.tag}' (expected 'wechat_translation_notes')"
                )
                return result

            result["structure"]["root"] = root.tag

            # Check digest
            digest_elem = root.find("digest")
            if digest_elem is None:
                result["errors"].append("Missing digest element")
            else:
                digest_text = digest_elem.text or ""
                digest_chars = len(digest_text.strip())
                if digest_chars < 80:
                    result["warnings"].append(
                        "Digest too short (expected 80-120 characters)"
                    )
                elif digest_chars > 120:
                    result["warnings"].append(
                        "Digest too long (expected 80-120 characters)"
                    )

                result["structure"]["digest_length"] = digest_chars

            # Check notes
            notes_elem = root.find("notes")
            if notes_elem is None:
                result["errors"].append("Missing notes element")
            else:
                notes_text = notes_elem.text or ""
                bullet_points = WeChatXMLParser._parse_bullet_points(notes_text)

                if len(bullet_points) < 3:
                    result["warnings"].append("Too few bullet points (expected 3-6)")
                elif len(bullet_points) > 6:
                    result["warnings"].append("Too many bullet points (expected 3-6)")

                # Check bullet point lengths
                for i, bullet in enumerate(bullet_points):
                    if len(bullet) < 10:
                        result["warnings"].append(
                            f"Bullet point {i+1} too short (minimum 10 characters)"
                        )
                    elif len(bullet) > 40:
                        result["warnings"].append(
                            f"Bullet point {i+1} too long (maximum 40 characters)"
                        )

                result["structure"]["bullet_count"] = len(bullet_points)

            # If no errors, mark as valid
            if not result["errors"]:
                result["is_valid"] = True

            return result

        except Exception as e:
            result["errors"].append(f"Validation error: {e}")
            return result

    @staticmethod
    def extract_xml_from_text(text: str) -> Optional[str]:
        """
        Extract XML content from mixed text (LLM responses often have extra text).

        Args:
            text: Text containing XML

        Returns:
            Extracted XML content or None if not found
        """
        # Look for XML tags
        xml_pattern = r"<wechat_translation_notes>.*?</wechat_translation_notes>"
        match = re.search(xml_pattern, text, re.DOTALL | re.IGNORECASE)

        if match:
            return match.group(0)

        # Try alternative patterns
        alt_patterns = [
            r"<wechat_translation_notes>.*",
            r".*</wechat_translation_notes>",
            r"<wechat_translation_notes[^>]*>.*</wechat_translation_notes>",
        ]

        for pattern in alt_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(0)

        return None

    @staticmethod
    def sanitize_xml_for_parsing(xml_content: str) -> str:
        """
        Sanitize XML content to handle common LLM output issues.

        Args:
            xml_content: Raw XML content

        Returns:
            Sanitized XML content
        """
        # Remove common formatting artifacts
        xml_content = re.sub(r"```xml\s*", "", xml_content)
        xml_content = re.sub(r"```\s*$", "", xml_content)
        xml_content = re.sub(r"<\?xml[^>]*\?>", "", xml_content)

        # Fix common character encoding issues
        xml_content = xml_content.replace("&lt;", "<")
        xml_content = xml_content.replace("&gt;", ">")
        xml_content = xml_content.replace("&amp;", "&")
        xml_content = xml_content.replace("&quot;", '"')
        xml_content = xml_content.replace("&#39;", "'")

        # Remove excessive whitespace
        xml_content = re.sub(r"\s+", " ", xml_content)
        xml_content = xml_content.strip()

        return xml_content
