"""
VPSWeb Repository System

This package provides the repository layer for the VPSWeb application,
including database models, API endpoints, validation, and security.

Modules:
- api: FastAPI application and endpoint definitions
- models: Database models and ORM configurations
- validation: Input validation and sanitization
- exceptions: Custom exception classes and error handling
- security: Security middleware and HTTP headers
- sanitization: Data cleaning and XSS protection
"""

from .validation import (
    ValidationError,
    SecurityValidationError,
    ContentValidationError,
    InputSanitizer,
    ContentValidator,
    RequestValidator,
    get_request_validator,
    validate_and_sanitize_string,
    validate_language_code_safe,
    validate_content_length,
)

from .exceptions import (
    ErrorCode,
    ErrorSeverity,
    VPSWebException,
    ValidationException,
    SecurityException,
    ResourceNotFoundException,
    ConflictException,
    ExternalServiceException,
    DatabaseException,
    HTTPStatusMapper,
    ErrorResponse,
    ErrorHandler,
    get_error_handler,
    raise_validation_error,
    raise_not_found_error,
    raise_conflict_error,
    raise_security_error,
    raise_external_service_error,
    raise_database_error,
)

from .sanitization import (
    TextSanitizer,
    HTMLSanitizer,
    MetadataSanitizer,
    FileContentSanitizer,
    get_text_sanitizer,
    get_html_sanitizer,
    get_metadata_sanitizer,
    get_file_sanitizer,
)

from .security import (
    SecurityHeadersMiddleware,
    XSSProtectionMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    setup_security_middleware,
)

__all__ = [
    # Input validation
    "ValidationError",
    "SecurityValidationError",
    "ContentValidationError",
    "InputSanitizer",
    "ContentValidator",
    "RequestValidator",
    "get_request_validator",
    "validate_and_sanitize_string",
    "validate_language_code_safe",
    "validate_content_length",

    # Exception handling
    "ErrorCode",
    "ErrorSeverity",
    "VPSWebException",
    "ValidationException",
    "SecurityException",
    "ResourceNotFoundException",
    "ConflictException",
    "ExternalServiceException",
    "DatabaseException",
    "HTTPStatusMapper",
    "ErrorResponse",
    "ErrorHandler",
    "get_error_handler",
    "raise_validation_error",
    "raise_not_found_error",
    "raise_conflict_error",
    "raise_security_error",
    "raise_external_service_error",
    "raise_database_error",

    # Data sanitization
    "TextSanitizer",
    "HTMLSanitizer",
    "MetadataSanitizer",
    "FileContentSanitizer",
    "get_text_sanitizer",
    "get_html_sanitizer",
    "get_metadata_sanitizer",
    "get_file_sanitizer",

    # Security middleware
    "SecurityHeadersMiddleware",
    "XSSProtectionMiddleware",
    "RateLimitMiddleware",
    "RequestLoggingMiddleware",
    "setup_security_middleware",
]