"""
Data Sanitization Utilities for VPSWeb Repository System

This module provides comprehensive data sanitization utilities for
cleaning and validating user input data.

Features:
- Text sanitization and cleaning
- HTML content sanitization
- File content sanitization
- Metadata sanitization
- Security-focused data cleaning
"""

import re
import html
import json
import unicodedata
from typing import Any, Dict, List, Optional, Union
from urllib.parse import unquote
import bleach
from bs4 import BeautifulSoup

from .validation import SecurityValidationError


class TextSanitizer:
    """
    Provides text sanitization utilities.

    Handles cleaning of plain text content while preserving readability.
    """

    # Control characters and potentially dangerous Unicode characters
    DANGEROUS_CHARS = [
        '\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07',
        '\x08', '\x0b', '\x0c', '\x0e', '\x0f', '\x10', '\x11', '\x12',
        '\x13', '\x14', '\x15', '\x16', '\x17', '\x18', '\x19', '\x1a',
        '\x1b', '\x1c', '\x1d', '\x1e', '\x1f', '\x7f'
    ]

    @staticmethod
    def sanitize_text(
        content: str,
        max_length: Optional[int] = None,
        preserve_line_breaks: bool = True,
        normalize_unicode: bool = True
    ) -> str:
        """
        Sanitize text content.

        Args:
            content: Raw text content
            max_length: Maximum allowed length
            preserve_line_breaks: Whether to preserve line breaks
            normalize_unicode: Whether to normalize Unicode characters

        Returns:
            Sanitized text content
        """
        if not content:
            return ""

        # Remove dangerous control characters
        for char in TextSanitizer.DANGEROUS_CHARS:
            content = content.replace(char, '')

        # Normalize Unicode if requested
        if normalize_unicode:
            content = unicodedata.normalize('NFKC', content)

        # Handle line breaks
        if preserve_line_breaks:
            # Convert various line break types to \n
            content = re.sub(r'\r\n|\r', '\n', content)
        else:
            # Remove all line breaks
            content = re.sub(r'\r\n|\r|\n', ' ', content)

        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)

        # Strip leading/trailing whitespace
        content = content.strip()

        # Apply length limit
        if max_length and len(content) > max_length:
            content = content[:max_length].rstrip()

        return content

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename for secure file storage.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        if not filename:
            return "unnamed"

        # URL decode if needed
        filename = unquote(filename)

        # Remove directory traversal attempts
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')

        # Remove dangerous characters
        dangerous_chars = '<>:"|?*\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f'
        for char in dangerous_chars:
            filename = filename.replace(char, '')

        # Replace problematic characters with underscores
        filename = re.sub(r'[^\w\-.]', '_', filename)

        # Remove consecutive underscores
        filename = re.sub(r'_+', '_', filename)

        # Remove leading/trailing underscores and dots
        filename = filename.strip('._')

        # Ensure it's not empty and not just dots/underscores
        if not filename or re.match(r'^[._]+$', filename):
            filename = "unnamed"

        # Limit length
        filename = filename[:255]

        return filename

    @staticmethod
    def sanitize_email(email: str) -> str:
        """
        Sanitize email address.

        Args:
            email: Email address to sanitize

        Returns:
            Sanitized email address

        Raises:
            SecurityValidationError: If email format is invalid
        """
        if not email:
            return ""

        email = email.strip().lower()

        # Basic email format validation
        email_pattern = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
        if not re.match(email_pattern, email):
            raise SecurityValidationError(f"Invalid email format: {email}")

        return email

    @staticmethod
    def sanitize_tags(tags: Union[str, List[str]]) -> List[str]:
        """
        Sanitize tags list.

        Args:
            tags: Tags as string (comma-separated) or list

        Returns:
            List of sanitized tags
        """
        if isinstance(tags, str):
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        else:
            tag_list = tags

        sanitized_tags = []
        for tag in tag_list:
            if tag:
                # Sanitize individual tag
                sanitized = TextSanitizer.sanitize_text(tag, max_length=50)
                if sanitized:
                    sanitized_tags.append(sanitized)

        return sanitized_tags

    @staticmethod
    def extract_keywords(content: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from text content.

        Args:
            content: Text content to analyze
            max_keywords: Maximum number of keywords to extract

        Returns:
            List of keywords
        """
        if not content:
            return []

        # Simple keyword extraction - split on whitespace and punctuation
        words = re.findall(r'\b[a-zA-Z\u4e00-\u9fff]{3,}\b', content.lower())

        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'this', 'that',
            'these', 'those', 'it', 'its', 'they', 'them', 'their', 'you', 'your',
            'yours', 'our', 'ours', 'we', 'us', 'was', 'were', 'been', 'be', 'am',
            'is', 'are', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'shall'
        }

        filtered_words = [word for word in words if word not in stop_words and len(word) >= 3]

        # Count word frequency
        word_counts = {}
        for word in filtered_words:
            word_counts[word] = word_counts.get(word, 0) + 1

        # Sort by frequency and return top keywords
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:max_keywords]]


class HTMLSanitizer:
    """
    Provides HTML content sanitization utilities.

    Uses bleach and BeautifulSoup for secure HTML sanitization.
    """

    # Allowed HTML tags for content
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'i', 'b', 'u',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li',
        'blockquote', 'code', 'pre',
        'a', 'span', 'div'
    ]

    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title'],
        '*': ['class', 'id'],
        'blockquote': ['cite'],
        'code': ['class'],
        'pre': ['class'],
        'span': ['class', 'style']
    }

    @staticmethod
    def sanitize_html(
        content: str,
        allow_links: bool = True,
        allow_formatting: bool = True,
        strip_comments: bool = True
    ) -> str:
        """
        Sanitize HTML content.

        Args:
            content: Raw HTML content
            allow_links: Whether to allow links
            allow_formatting: Whether to allow text formatting
            strip_comments: Whether to strip HTML comments

        Returns:
            Sanitized HTML content
        """
        if not content:
            return ""

        # Configure allowed tags based on options
        allowed_tags = HTMLSanitizer.ALLOWED_TAGS.copy()

        if not allow_links:
            allowed_tags.remove('a')

        if not allow_formatting:
            allowed_tags = [tag for tag in allowed_tags if tag not in ['strong', 'em', 'i', 'b', 'u']]

        try:
            # Use bleach for basic sanitization
            sanitized = bleach.clean(
                content,
                tags=allowed_tags,
                attributes=HTMLSanitizer.ALLOWED_ATTRIBUTES,
                strip=strip_comments,
                strip_comments=strip_comments
            )

            # Additional cleanup with BeautifulSoup
            soup = BeautifulSoup(sanitized, 'html.parser')

            # Remove any remaining dangerous attributes
            for tag in soup.find_all():
                # Remove style attributes with potentially dangerous content
                if tag.has_attr('style'):
                    style = tag['style']
                    # Basic CSS validation
                    if re.search(r'javascript:|expression\(|@import', style, re.IGNORECASE):
                        del tag['style']

                # Remove event handlers
                for attr in list(tag.attrs):
                    if attr.lower().startswith('on'):
                        del tag[attr]

            return str(soup)

        except Exception as e:
            # Fallback to basic HTML escaping if sanitization fails
            return html.escape(content)

    @staticmethod
    def strip_html(content: str) -> str:
        """
        Strip all HTML tags, leaving only text content.

        Args:
            content: HTML content

        Returns:
            Plain text content
        """
        if not content:
            return ""

        try:
            soup = BeautifulSoup(content, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        except Exception:
            # Fallback to regex-based HTML stripping
            content = re.sub(r'<[^>]+>', ' ', content)
            return ' '.join(content.split())

    @staticmethod
    def extract_text_summary(html_content: str, max_length: int = 500) -> str:
        """
        Extract readable text summary from HTML content.

        Args:
            html_content: HTML content
            max_length: Maximum summary length

        Returns:
            Text summary
        """
        text = HTMLSanitizer.strip_html(html_content)
        text = TextSanitizer.sanitize_text(text, max_length=max_length)
        return text


class MetadataSanitizer:
    """
    Provides metadata sanitization utilities.

    Handles cleaning of JSON metadata and structured data.
    """

    @staticmethod
    def sanitize_json_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize JSON metadata.

        Args:
            metadata: Raw metadata dictionary

        Returns:
            Sanitized metadata dictionary
        """
        sanitized = {}

        for key, value in metadata.items():
            if isinstance(value, str):
                # Sanitize string values
                sanitized[key] = TextSanitizer.sanitize_text(value, max_length=1000)
            elif isinstance(value, list):
                # Sanitize list values
                sanitized[key] = [
                    TextSanitizer.sanitize_text(str(item), max_length=500)
                    for item in value
                ]
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized[key] = MetadataSanitizer.sanitize_json_metadata(value)
            else:
                # Keep other types as-is
                sanitized[key] = value

        return sanitized

    @staticmethod
    def sanitize_translator_info(info: str) -> str:
        """
        Sanitize translator information.

        Args:
            info: Translator information

        Returns:
            Sanitized translator information
        """
        return TextSanitizer.sanitize_text(info, max_length=500)

    @staticmethod
    def sanitize_quality_score(score: str) -> str:
        """
        Sanitize quality score.

        Args:
            score: Quality score string

        Returns:
            Sanitized quality score
        """
        if not score:
            return ""

        # Allow numeric scores and descriptive values
        score = score.strip().lower()

        if score in ['high', 'medium', 'low', 'excellent', 'good', 'fair', 'poor']:
            return score

        # Validate numeric score
        if re.match(r'^\d+(\.\d+)?$', score):
            try:
                score_value = float(score)
                if 0 <= score_value <= 10:
                    return score
            except ValueError:
                pass

        # If invalid, return default
        return "medium"

    @staticmethod
    def sanitize_license(license_text: str) -> str:
        """
        Sanitize license information.

        Args:
            license_text: License text

        Returns:
            Sanitized license text
        """
        return TextSanitizer.sanitize_text(license_text, max_length=100)


class FileContentSanitizer:
    """
    Provides file content sanitization utilities.

    Handles validation and cleaning of uploaded file content.
    """

    # Dangerous file signatures
    DANGEROUS_SIGNATURES = [
        b'\x4D\x5A',  # ZIP
        b'\x50\x4B',  # ZIP
        b'\x1F\x8B',  # GZIP
        b'\x42\x5A',  # BZIP2
        b'\x7FELF',  # ELF executable
        b'\x4D\x5A\x90\x00',  # EXE
        b'\x49\x49\x2A\x00',  # TIFF (can be used for exploits)
        b'\xFF\xD8\xFF',  # JPEG
        b'\xFF\xD8\xFF\xE0\x00\x10JFIF',  # JPEG
        b'\x89PNG\x0D\x0A\x1A\x0A',  # PNG
        b'GIF8',  # GIF
        b'%PDF',  # PDF
    ]

    @staticmethod
    def validate_file_signature(content: bytes, allowed_types: List[str]) -> bool:
        """
        Validate file signature against allowed types.

        Args:
            content: File content bytes
            allowed_types: List of allowed MIME types

        Returns:
            True if file type is allowed

        Raises:
            SecurityValidationError: If file type is not allowed
        """
        if not content:
            return True

        # Check for dangerous signatures
        for signature in FileContentSanitizer.DANGEROUS_SIGNATURES:
            if content.startswith(signature):
                # Check if this type is explicitly allowed
                if signature == b'%PDF' and 'application/pdf' in allowed_types:
                    continue
                elif signature in [b'\xFF\xD8\xFF', b'\x89PNG'] and 'image/' in ''.join(allowed_types):
                    continue
                else:
                    raise SecurityValidationError(f"Dangerous file signature detected: {signature.hex()}")

        return True

    @staticmethod
    def sanitize_text_file_content(content: bytes, max_size: int = 1024 * 1024) -> str:
        """
        Sanitize text file content.

        Args:
            content: File content bytes
            max_size: Maximum allowed size in bytes

        Returns:
            Sanitized text content

        Raises:
            ValidationError: If content is too large
        """
        if len(content) > max_size:
            raise SecurityValidationError(f"File too large: {len(content)} bytes (max: {max_size})")

        try:
            # Try to decode as UTF-8
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                # Fallback to latin-1
                text_content = content.decode('latin-1')
            except UnicodeDecodeError:
                raise SecurityValidationError("Unable to decode file content as text")

        return TextSanitizer.sanitize_text(text_content)

    @staticmethod
    def extract_metadata_from_text(content: str) -> Dict[str, Any]:
        """
        Extract metadata from text content.

        Args:
            content: Text content

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            'length': len(content),
            'line_count': len(content.splitlines()),
            'word_count': len(content.split()),
            'language': 'unknown'
        }

        # Simple language detection based on character patterns
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        total_chars = len(content)

        if chinese_chars / max(total_chars, 1) > 0.3:
            metadata['language'] = 'chinese'
        elif re.search(r'[àáâäãååæçèéêëìíîïïññòóôöõøùúûüüýýÿÿ]', content):
            metadata['language'] = 'european'

        # Extract potential title (first line if short enough)
        lines = content.splitlines()
        if lines and len(lines[0]) < 100:
            metadata['potential_title'] = lines[0].strip()

        return metadata


# Global sanitizer instances
_text_sanitizer = TextSanitizer()
_html_sanitizer = HTMLSanitizer()
_metadata_sanitizer = MetadataSanitizer()
_file_sanitizer = FileContentSanitizer()


def get_text_sanitizer() -> TextSanitizer:
    """Get the global text sanitizer instance."""
    return _text_sanitizer


def get_html_sanitizer() -> HTMLSanitizer:
    """Get the global HTML sanitizer instance."""
    return _html_sanitizer


def get_metadata_sanitizer() -> MetadataSanitizer:
    """Get the global metadata sanitizer instance."""
    return _metadata_sanitizer


def get_file_sanitizer() -> FileContentSanitizer:
    """Get the global file content sanitizer instance."""
    return _file_sanitizer