"""
Exception Handling Classes for VPSWeb Repository System

This module provides comprehensive exception handling classes and utilities
for standardized error responses and proper error management.

Features:
- Custom exception classes for different error types
- Standardized JSON error response format
- HTTP status code mapping
- Error logging and monitoring
- User-friendly error messages
"""

import traceback
from typing import Any, Dict, Optional, Union
from datetime import datetime, timezone
from enum import Enum

from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError

from ..utils.logger import get_structured_logger


class ErrorCode(str, Enum):
    """Standardized error codes."""

    # Validation errors (400)
    INVALID_INPUT = "INVALID_INPUT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    CONTENT_TOO_LARGE = "CONTENT_TOO_LARGE"
    INVALID_LANGUAGE_CODE = "INVALID_LANGUAGE_CODE"

    # Authentication errors (401)
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"

    # Authorization errors (403)
    FORBIDDEN = "FORBIDDEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

    # Not found errors (404)
    NOT_FOUND = "NOT_FOUND"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"

    # Conflict errors (409)
    CONFLICT = "CONFLICT"
    DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"

    # Server errors (500)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"

    # Service unavailable errors (503)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    MAINTENANCE_MODE = "MAINTENANCE_MODE"


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VPSWebException(Exception):
    """Base exception class for VPSWeb repository system."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize VPSWeb exception.

        Args:
            message: Human-readable error message
            error_code: Standardized error code
            details: Additional error details
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.now(timezone.utc)
        self.severity = self._determine_severity()

    def _determine_severity(self) -> ErrorSeverity:
        """Determine error severity based on error code."""
        critical_codes = [
            ErrorCode.DATABASE_ERROR,
            ErrorCode.INTERNAL_SERVER_ERROR,
            ErrorCode.SERVICE_UNAVAILABLE
        ]

        high_codes = [
            ErrorCode.EXTERNAL_SERVICE_ERROR,
            ErrorCode.FORBIDDEN,
            ErrorCode.UNAUTHORIZED
        ]

        if self.error_code in critical_codes:
            return ErrorSeverity.CRITICAL
        elif self.error_code in high_codes:
            return ErrorSeverity.HIGH
        elif self.error_code in [ErrorCode.CONFLICT, ErrorCode.CONTENT_TOO_LARGE]:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            "error": True,
            "error_code": self.error_code.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value
        }


class ValidationException(VPSWebException):
    """Exception raised for input validation errors."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize validation exception.

        Args:
            message: Error message
            field: Field name that failed validation
            value: Invalid value
            details: Additional error details
        """
        error_details = details or {}
        if field:
            error_details["field"] = field
        if value is not None:
            error_details["invalid_value"] = str(value)

        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            details=error_details
        )


class SecurityException(VPSWebException):
    """Exception raised for security-related errors."""

    def __init__(
        self,
        message: str,
        security_violation: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize security exception.

        Args:
            message: Error message
            security_violation: Type of security violation
            details: Additional error details
        """
        error_details = details or {}
        error_details["security_violation"] = security_violation

        super().__init__(
            message=message,
            error_code=ErrorCode.FORBIDDEN,
            details=error_details
        )


class ResourceNotFoundException(VPSWebException):
    """Exception raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize resource not found exception.

        Args:
            resource_type: Type of resource (e.g., "poem", "translation")
            resource_id: Resource identifier
            details: Additional error details
        """
        message = f"{resource_type.title()} with ID '{resource_id}' not found"
        error_details = details or {}
        error_details.update({
            "resource_type": resource_type,
            "resource_id": resource_id
        })

        super().__init__(
            message=message,
            error_code=ErrorCode.NOT_FOUND,
            details=error_details
        )


class ConflictException(VPSWebException):
    """Exception raised for resource conflicts."""

    def __init__(
        self,
        message: str,
        conflict_type: str,
        existing_resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize conflict exception.

        Args:
            message: Error message
            conflict_type: Type of conflict
            existing_resource_id: ID of existing conflicting resource
            details: Additional error details
        """
        error_details = details or {}
        error_details["conflict_type"] = conflict_type
        if existing_resource_id:
            error_details["existing_resource_id"] = existing_resource_id

        super().__init__(
            message=message,
            error_code=ErrorCode.CONFLICT,
            details=error_details
        )


class ExternalServiceException(VPSWebException):
    """Exception raised for external service integration errors."""

    def __init__(
        self,
        message: str,
        service_name: str,
        service_error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize external service exception.

        Args:
            message: Error message
            service_name: Name of external service
            service_error_code: Error code from external service
            details: Additional error details
        """
        error_details = details or {}
        error_details.update({
            "service_name": service_name,
            "service_error_code": service_error_code
        })

        super().__init__(
            message=message,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details=error_details
        )


class DatabaseException(VPSWebException):
    """Exception raised for database operation errors."""

    def __init__(
        self,
        message: str,
        operation: str,
        table: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize database exception.

        Args:
            message: Error message
            operation: Database operation that failed
            table: Database table name
            details: Additional error details
        """
        error_details = details or {}
        error_details.update({
            "operation": operation
        })
        if table:
            error_details["table"] = table

        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_ERROR,
            details=error_details
        )


class HTTPStatusMapper:
    """Maps error codes to HTTP status codes."""

    STATUS_MAPPING = {
        # Validation errors (400)
        ErrorCode.INVALID_INPUT: status.HTTP_400_BAD_REQUEST,
        ErrorCode.VALIDATION_ERROR: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ErrorCode.MISSING_FIELD: status.HTTP_400_BAD_REQUEST,
        ErrorCode.INVALID_FORMAT: status.HTTP_400_BAD_REQUEST,
        ErrorCode.CONTENT_TOO_LARGE: status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        ErrorCode.INVALID_LANGUAGE_CODE: status.HTTP_400_BAD_REQUEST,

        # Authentication errors (401)
        ErrorCode.UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
        ErrorCode.INVALID_TOKEN: status.HTTP_401_UNAUTHORIZED,
        ErrorCode.TOKEN_EXPIRED: status.HTTP_401_UNAUTHORIZED,

        # Authorization errors (403)
        ErrorCode.FORBIDDEN: status.HTTP_403_FORBIDDEN,
        ErrorCode.INSUFFICIENT_PERMISSIONS: status.HTTP_403_FORBIDDEN,

        # Not found errors (404)
        ErrorCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCode.RESOURCE_NOT_FOUND: status.HTTP_404_NOT_FOUND,

        # Conflict errors (409)
        ErrorCode.CONFLICT: status.HTTP_409_CONFLICT,
        ErrorCode.DUPLICATE_RESOURCE: status.HTTP_409_CONFLICT,

        # Server errors (500)
        ErrorCode.INTERNAL_SERVER_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCode.DATABASE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCode.EXTERNAL_SERVICE_ERROR: status.HTTP_502_BAD_GATEWAY,

        # Service unavailable errors (503)
        ErrorCode.SERVICE_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
        ErrorCode.MAINTENANCE_MODE: status.HTTP_503_SERVICE_UNAVAILABLE,
    }

    @classmethod
    def get_status_code(cls, error_code: ErrorCode) -> int:
        """
        Get HTTP status code for error code.

        Args:
            error_code: Error code to map

        Returns:
            HTTP status code
        """
        return cls.STATUS_MAPPING.get(error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    error: bool = True
    error_code: str
    message: str
    details: Dict[str, Any] = {}
    timestamp: str
    severity: str
    request_id: Optional[str] = None


class ErrorHandler:
    """
    Handles error processing and logging.

    Provides standardized error responses and logging functionality.
    """

    def __init__(self):
        """Initialize the error handler."""
        self.logger = get_structured_logger()

    def handle_exception(
        self,
        exception: Exception,
        request_id: Optional[str] = None,
        include_traceback: bool = False
    ) -> ErrorResponse:
        """
        Handle an exception and create standardized error response.

        Args:
            exception: Exception to handle
            request_id: Request ID for tracking
            include_traceback: Whether to include traceback in response

        Returns:
            Standardized error response
        """
        # Convert to VPSWeb exception if needed
        if isinstance(exception, VPSWebException):
            vpsweb_exception = exception
        else:
            vpsweb_exception = VPSWebException(
                message=str(exception),
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                cause=exception
            )

        # Log the error
        self._log_error(vpsweb_exception, request_id, include_traceback)

        # Create error response
        error_dict = vpsweb_exception.to_dict()
        if request_id:
            error_dict["request_id"] = request_id

        if include_traceback and vpsweb_exception.cause:
            error_dict["traceback"] = traceback.format_exc()

        return ErrorResponse(**error_dict)

    def _log_error(
        self,
        exception: VPSWebException,
        request_id: Optional[str] = None,
        include_traceback: bool = False
    ) -> None:
        """Log the error with appropriate level."""
        log_data = {
            "error_code": exception.error_code.value,
            "severity": exception.severity.value,
            "timestamp": exception.timestamp.isoformat()
        }

        if request_id:
            log_data["request_id"] = request_id

        if exception.details:
            log_data["details"] = exception.details

        if include_traceback and exception.cause:
            log_data["traceback"] = traceback.format_exc()

        # Log based on severity
        if exception.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(
                f"Critical error: {exception.message}",
                **log_data
            )
        elif exception.severity == ErrorSeverity.HIGH:
            self.logger.error(
                f"High severity error: {exception.message}",
                **log_data
            )
        elif exception.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(
                f"Medium severity error: {exception.message}",
                **log_data
            )
        else:
            self.logger.info(
                f"Low severity error: {exception.message}",
                **log_data
            )

    def create_http_exception(
        self,
        exception: Exception,
        request_id: Optional[str] = None
    ) -> HTTPException:
        """
        Create FastAPI HTTPException from exception.

        Args:
            exception: Exception to convert
            request_id: Request ID for tracking

        Returns:
            FastAPI HTTPException
        """
        error_response = self.handle_exception(exception, request_id)
        status_code = HTTPStatusMapper.get_status_code(error_response.error_code)

        return HTTPException(
            status_code=status_code,
            detail=error_response.dict()
        )


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """
    Get the global error handler instance.

    Returns:
        Global ErrorHandler instance
    """
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


# Convenience functions for common error scenarios
def raise_validation_error(
    message: str,
    field: Optional[str] = None,
    value: Optional[Any] = None
) -> None:
    """Raise a validation error."""
    raise ValidationException(message=message, field=field, value=value)


def raise_not_found_error(
    resource_type: str,
    resource_id: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Raise a not found error."""
    raise ResourceNotFoundException(
        resource_type=resource_type,
        resource_id=resource_id,
        details=details
    )


def raise_conflict_error(
    message: str,
    conflict_type: str,
    existing_resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Raise a conflict error."""
    raise ConflictException(
        message=message,
        conflict_type=conflict_type,
        existing_resource_id=existing_resource_id,
        details=details
    )


def raise_security_error(
    message: str,
    security_violation: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Raise a security error."""
    raise SecurityException(
        message=message,
        security_violation=security_violation,
        details=details
    )


def raise_external_service_error(
    message: str,
    service_name: str,
    service_error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Raise an external service error."""
    raise ExternalServiceException(
        message=message,
        service_name=service_name,
        service_error_code=service_error_code,
        details=details
    )


def raise_database_error(
    message: str,
    operation: str,
    table: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Raise a database error."""
    raise DatabaseException(
        message=message,
        operation=operation,
        table=table,
        details=details
    )