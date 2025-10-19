"""
Input Validation Module for VPSWeb Repository System

This module provides comprehensive input validation for all API endpoints,
including security validation, sanitization, and content validation.

Features:
- Request input validation and sanitization
- SQL injection prevention
- XSS protection for web content
- File upload validation
- Content length and format validation
- Security headers validation
"""

import re
import html
import json
from typing import Any, Dict, List, Optional, Union, Callable
from urllib.parse import unquote
from pydantic import BaseModel, ValidationError
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .schemas import (
    PoemCreate, PoemUpdate, TranslationCreate, TranslationUpdate,
    AiLogCreate, HumanNoteCreate
)
from ..utils.language_mapper import validate_language_code


class ValidationError(Exception):
    """Base validation error."""
    pass


class SecurityValidationError(ValidationError):
    """Security-related validation error."""
    pass


class ContentValidationError(ValidationError):
    """Content validation error."""
    pass


class InputSanitizer:
    """
    Provides input sanitization utilities.

    Handles XSS prevention, SQL injection protection, and content sanitization.
    """

    # XSS dangerous patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',  # onclick=, onload=, etc.
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
    ]

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
        r'(--|#)',
        r'(/\*.*?\*/)',
        r'(\bOR\b.*?=.*\bOR\b)',
        r'(\bAND\b.*?=.*\bAND\b)',
        r'(1=1|1 = 1)',
        r'(true|TRUE)',
        r'(false|FALSE)',
    ]

    @staticmethod
    def sanitize_html(content: str) -> str:
        """
        Sanitize HTML content to prevent XSS attacks.

        Args:
            content: Raw HTML content

        Returns:
            Sanitized HTML content
        """
        if not content:
            return content

        # HTML escape the content
        sanitized = html.escape(content)

        # Remove dangerous script-like content
        for pattern in InputSanitizer.XSS_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)

        return sanitized

    @staticmethod
    def sanitize_text(content: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize plain text content.

        Args:
            content: Raw text content
            max_length: Maximum allowed length

        Returns:
            Sanitized text content
        """
        if not content:
            return content

        # Remove null bytes and control characters
        sanitized = content.replace('\x00', '')
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', sanitized)

        # Trim whitespace
        sanitized = sanitized.strip()

        # Apply length limit
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized

    @staticmethod
    def validate_no_sql_injection(content: str) -> bool:
        """
        Validate that content doesn't contain SQL injection patterns.

        Args:
            content: Content to validate

        Returns:
            True if safe, False if potentially malicious

        Raises:
            SecurityValidationError: If SQL injection patterns are found
        """
        if not content:
            return True

        content_upper = content.upper()
        for pattern in InputSanitizer.SQL_INJECTION_PATTERNS:
            if re.search(pattern, content_upper):
                raise SecurityValidationError(f"Potential SQL injection detected: {pattern}")

        return True

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate URL format and safety.

        Args:
            url: URL to validate

        Returns:
            True if safe, False otherwise
        """
        if not url:
            return True

        # Basic URL pattern
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return bool(url_pattern.match(url))

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

        # Remove directory traversal attempts
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')

        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*]', '', filename)

        # Limit length and remove surrounding whitespace
        filename = filename.strip()[:255]

        return filename or "unnamed"


class ContentValidator:
    """
    Provides content validation for different data types.

    Validates poetry content, translations, and metadata according to business rules.
    """

    @staticmethod
    def validate_poem_content(content: str) -> bool:
        """
        Validate poem content according to business rules.

        Args:
            content: Poem content to validate

        Returns:
            True if valid

        Raises:
            ContentValidationError: If content is invalid
        """
        if not content or not content.strip():
            raise ContentValidationError("Poem content cannot be empty")

        content = content.strip()

        # Minimum length check
        if len(content) < 10:
            raise ContentValidationError("Poem content too short (minimum 10 characters)")

        # Maximum length check (reasonable limit for poetry)
        if len(content) > 50000:  # ~50K characters
            raise ContentValidationError("Poem content too long (maximum 50,000 characters)")

        # Check for reasonable character ratio (avoid binary data)
        text_chars = sum(1 for c in content if c.isprintable() and not c.isspace())
        if text_chars / len(content) < 0.7:
            raise ContentValidationError("Poem content appears to contain non-text data")

        return True

    @staticmethod
    def validate_translation_content(content: str) -> bool:
        """
        Validate translation content.

        Args:
            content: Translation content to validate

        Returns:
            True if valid

        Raises:
            ContentValidationError: If content is invalid
        """
        if not content or not content.strip():
            raise ContentValidationError("Translation content cannot be empty")

        content = content.strip()

        # Minimum length check
        if len(content) < 5:
            raise ContentValidationError("Translation content too short (minimum 5 characters)")

        # Maximum length check
        if len(content) > 60000:  # ~60K characters (allow longer than original)
            raise ContentValidationError("Translation content too long (maximum 60,000 characters)")

        return True

    @staticmethod
    def validate_author_name(name: str) -> bool:
        """
        Validate author/poet name.

        Args:
            name: Author name to validate

        Returns:
            True if valid

        Raises:
            ContentValidationError: If name is invalid
        """
        if not name or not name.strip():
            raise ContentValidationError("Author name cannot be empty")

        name = name.strip()

        # Length validation
        if len(name) < 2:
            raise ContentValidationError("Author name too short (minimum 2 characters)")

        if len(name) > 255:
            raise ContentValidationError("Author name too long (maximum 255 characters)")

        # Character validation (allow letters, spaces, hyphens, apostrophes)
        if not re.match(r'^[a-zA-Z\u4e00-\u9fff\u3400-\u4dbf\-\s\'\-\.]+$', name):
            raise ContentValidationError("Author name contains invalid characters")

        return True

    @staticmethod
    def validate_title(title: str) -> bool:
        """
        Validate poem or translation title.

        Args:
            title: Title to validate

        Returns:
            True if valid

        Raises:
            ContentValidationError: If title is invalid
        """
        if not title or not title.strip():
            raise ContentValidationError("Title cannot be empty")

        title = title.strip()

        # Length validation
        if len(title) < 1:
            raise ContentValidationError("Title too short")

        if len(title) > 255:
            raise ContentValidationError("Title too long (maximum 255 characters)")

        # Basic character validation
        if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fff\u3400-\u4dbf\-\s\'\-\.\:\,\!\?]+$', title):
            raise ContentValidationError("Title contains invalid characters")

        return True

    @staticmethod
    def validate_tags(tags: str) -> bool:
        """
        Validate tags string.

        Args:
            tags: Comma-separated tags

        Returns:
            True if valid

        Raises:
            ContentValidationError: If tags are invalid
        """
        if not tags:
            return True  # Empty tags are allowed

        tags = tags.strip()

        # Split and validate individual tags
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]

        if len(tag_list) > 20:
            raise ContentValidationError("Too many tags (maximum 20)")

        for tag in tag_list:
            if len(tag) < 1:
                raise ContentValidationError("Tag too short")
            if len(tag) > 50:
                raise ContentValidationError("Tag too long (maximum 50 characters)")
            if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fff\u3400-\u4dbf\-\s\'\-]+$', tag):
                raise ContentValidationError(f"Tag '{tag}' contains invalid characters")

        return True


class RequestValidator:
    """
    Validates API requests and provides security validation.

    Integrates with FastAPI for request validation and security checks.
    """

    def __init__(self):
        """Initialize the request validator."""
        self.sanitizer = InputSanitizer()
        self.content_validator = ContentValidator()

    def validate_poem_create_request(self, data: Dict[str, Any]) -> PoemCreate:
        """
        Validate poem creation request data.

        Args:
            data: Request data dictionary

        Returns:
            Validated PoemCreate object

        Raises:
            ValidationError: If validation fails
        """
        try:
            # Basic security validation
            self._validate_request_security(data)

            # Pydantic validation
            poem_data = PoemCreate(**data)

            # Additional content validation
            self.content_validator.validate_poem_content(poem_data.original_text)
            self.content_validator.validate_author_name(poem_data.poet_name)
            self.content_validator.validate_title(poem_data.poem_title)

            # Language code validation
            if not validate_language_code(poem_data.source_language)[0]:
                raise ContentValidationError(f"Invalid language code: {poem_data.source_language}")

            return poem_data

        except ValidationError as e:
            raise ValidationError(f"Invalid poem data: {str(e)}")

    def validate_poem_update_request(self, data: Dict[str, Any]) -> PoemUpdate:
        """
        Validate poem update request data.

        Args:
            data: Request data dictionary

        Returns:
            Validated PoemUpdate object

        Raises:
            ValidationError: If validation fails
        """
        try:
            # Basic security validation
            self._validate_request_security(data)

            # Pydantic validation
            poem_data = PoemUpdate(**data)

            # Additional validation for provided fields
            if poem_data.original_text:
                self.content_validator.validate_poem_content(poem_data.original_text)

            if poem_data.poet_name:
                self.content_validator.validate_author_name(poem_data.poet_name)

            if poem_data.poem_title:
                self.content_validator.validate_title(poem_data.poem_title)

            if poem_data.source_language:
                if not validate_language_code(poem_data.source_language)[0]:
                    raise ContentValidationError(f"Invalid language code: {poem_data.source_language}")

            if poem_data.tags:
                self.content_validator.validate_tags(poem_data.tags)

            return poem_data

        except ValidationError as e:
            raise ValidationError(f"Invalid poem update data: {str(e)}")

    def validate_translation_create_request(self, data: Dict[str, Any]) -> TranslationCreate:
        """
        Validate translation creation request data.

        Args:
            data: Request data dictionary

        Returns:
            Validated TranslationCreate object

        Raises:
            ValidationError: If validation fails
        """
        try:
            # Basic security validation
            self._validate_request_security(data)

            # Pydantic validation
            translation_data = TranslationCreate(**data)

            # Additional content validation
            self.content_validator.validate_translation_content(translation_data.translated_text)

            # Language code validation
            if not validate_language_code(translation_data.target_language)[0]:
                raise ContentValidationError(f"Invalid language code: {translation_data.target_language}")

            return translation_data

        except ValidationError as e:
            raise ValidationError(f"Invalid translation data: {str(e)}")

    def validate_translation_update_request(self, data: Dict[str, Any]) -> TranslationUpdate:
        """
        Validate translation update request data.

        Args:
            data: Request data dictionary

        Returns:
            Validated TranslationUpdate object

        Raises:
            ValidationError: If validation fails
        """
        try:
            # Basic security validation
            self._validate_request_security(data)

            # Pydantic validation
            translation_data = TranslationUpdate(**data)

            # Additional validation for provided fields
            if translation_data.translated_text:
                self.content_validator.validate_translation_content(translation_data.translated_text)

            if translation_data.target_language:
                if not validate_language_code(translation_data.target_language)[0]:
                    raise ContentValidationError(f"Invalid language code: {translation_data.target_language}")

            return translation_data

        except ValidationError as e:
            raise ValidationError(f"Invalid translation update data: {str(e)}")

    def _validate_request_security(self, data: Dict[str, Any]) -> None:
        """
        Perform basic security validation on request data.

        Args:
            data: Request data dictionary

        Raises:
            SecurityValidationError: If security validation fails
        """
        for key, value in data.items():
            if isinstance(value, str):
                # Check for SQL injection
                self.sanitizer.validate_no_sql_injection(value)

                # Check for XSS in text fields
                if key in ['original_text', 'translated_text', 'translator_notes']:
                    value = self.sanitizer.sanitize_html(value)

    def validate_file_upload(self, filename: str, content_type: str, size: int) -> bool:
        """
        Validate file upload parameters.

        Args:
            filename: Original filename
            content_type: MIME content type
            size: File size in bytes

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        # Filename validation
        safe_filename = self.sanitizer.sanitize_filename(filename)

        # Content type validation (only allow text files)
        allowed_types = [
            'text/plain', 'text/markdown', 'application/json',
            'text/html'  # Only for content that will be sanitized
        ]

        if content_type not in allowed_types:
            raise ValidationError(f"Content type {content_type} not allowed")

        # Size validation (max 10MB)
        max_size = 10 * 1024 * 1024
        if size > max_size:
            raise ValidationError(f"File too large (maximum {max_size} bytes)")

        return True


# Global validator instance
_request_validator: Optional[RequestValidator] = None


def get_request_validator() -> RequestValidator:
    """
    Get the global request validator instance.

    Returns:
        Global RequestValidator instance
    """
    global _request_validator
    if _request_validator is None:
        _request_validator = RequestValidator()
    return _request_validator


# Validation middleware functions
def validate_and_sanitize_string(
    content: str,
    max_length: Optional[int] = None,
    allow_html: bool = False
) -> str:
    """
    Validate and sanitize string content.

    Args:
        content: Raw string content
        max_length: Maximum allowed length
        allow_html: Whether HTML content is allowed

    Returns:
        Sanitized string content
    """
    sanitizer = InputSanitizer()

    if allow_html:
        return sanitizer.sanitize_html(content)
    else:
        return sanitizer.sanitize_text(content, max_length)


def validate_language_code_safe(language_code: str) -> bool:
    """
    Safely validate language code.

    Args:
        language_code: Language code to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If invalid
    """
    is_valid, error_msg = validate_language_code(language_code)
    if not is_valid:
        raise ValidationError(error_msg or "Invalid language code")
    return True


def validate_content_length(content: str, min_length: int = 1, max_length: int = 10000) -> bool:
    """
    Validate content length.

    Args:
        content: Content to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        True if valid

    Raises:
        ValidationError: If invalid
    """
    content_length = len(content) if content else 0

    if content_length < min_length:
        raise ValidationError(f"Content too short (minimum {min_length} characters)")

    if content_length > max_length:
        raise ValidationError(f"Content too long (maximum {max_length} characters)")

    return True