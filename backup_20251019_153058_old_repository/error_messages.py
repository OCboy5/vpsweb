"""
User-Friendly Error Messages for VPSWeb Repository System

This module provides user-friendly error messages and templates
for different error scenarios in the web UI.

Features:
- Human-readable error messages
- Error message templates with parameters
- Localized error messages
- Actionable error guidance
- Error severity indicators
"""

from typing import Dict, Any, Optional, List
from enum import Enum

from .exceptions import ErrorCode, ErrorSeverity


class ErrorMessageCategory(str, Enum):
    """Categories of error messages for better organization."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    SYSTEM = "system"
    NETWORK = "network"
    SECURITY = "security"


class ErrorMessageTemplate:
    """
    Template for user-friendly error messages.
    """

    def __init__(
        self,
        title: str,
        message: str,
        description: Optional[str] = None,
        actions: Optional[List[str]] = None,
        category: ErrorMessageCategory = ErrorMessageCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ):
        """
        Initialize error message template.

        Args:
            title: Short, descriptive title
            message: Main error message
            description: Detailed explanation
            actions: List of suggested actions for the user
            category: Error category for organization
            severity: Error severity level
        """
        self.title = title
        self.message = message
        self.description = description
        self.actions = actions or []
        self.category = category
        self.severity = severity

    def format(self, **kwargs) -> Dict[str, Any]:
        """
        Format the error message with provided parameters.

        Args:
            **kwargs: Parameters to substitute in message templates

        Returns:
            Formatted error message dictionary
        """
        return {
            "title": self.title.format(**kwargs),
            "message": self.message.format(**kwargs),
            "description": self.description.format(**kwargs) if self.description else None,
            "actions": [action.format(**kwargs) for action in self.actions],
            "category": self.category.value,
            "severity": self.severity.value
        }


class ErrorMessageRegistry:
    """
    Registry of error message templates.
    """

    def __init__(self):
        """Initialize the error message registry."""
        self._templates: Dict[ErrorCode, ErrorMessageTemplate] = {}
        self._register_default_templates()

    def register_template(self, error_code: ErrorCode, template: ErrorMessageTemplate) -> None:
        """
        Register an error message template.

        Args:
            error_code: Error code to register template for
            template: Error message template
        """
        self._templates[error_code] = template

    def get_message(self, error_code: ErrorCode, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Get formatted error message for an error code.

        Args:
            error_code: Error code to get message for
            **kwargs: Parameters to substitute in templates

        Returns:
            Formatted error message or None if not found
        """
        template = self._templates.get(error_code)
        if template:
            return template.format(**kwargs)
        return None

    def get_all_messages(self) -> Dict[ErrorCode, ErrorMessageTemplate]:
        """
        Get all registered error message templates.

        Returns:
            Dictionary of all templates
        """
        return self._templates.copy()

    def _register_default_templates(self) -> None:
        """Register default error message templates."""

        # Validation errors
        self.register_template(
            ErrorCode.INVALID_INPUT,
            ErrorMessageTemplate(
                title="Invalid Input",
                message="The provided input is not valid.",
                description="Please check your input and try again. Make sure all required fields are filled out correctly.",
                actions=[
                    "Review the form for any missing or incorrect information",
                    "Check for special characters that might not be allowed",
                    "Try refreshing the page and submitting again"
                ],
                category=ErrorMessageCategory.VALIDATION,
                severity=ErrorSeverity.LOW
            )
        )

        self.register_template(
            ErrorCode.VALIDATION_ERROR,
            ErrorMessageTemplate(
                title="Validation Failed",
                message="Your input couldn't be validated: {field}",
                description="The {field} field contains invalid data. {details}",
                actions=[
                    "Check the {field} field for errors",
                    "Make sure the format matches the requirements",
                    "Refer to the field help text for guidance"
                ],
                category=ErrorMessageCategory.VALIDATION,
                severity=ErrorSeverity.LOW
            )
        )

        self.register_template(
            ErrorCode.MISSING_FIELD,
            ErrorMessageTemplate(
                title="Required Field Missing",
                message="The {field} field is required.",
                description="Please provide a value for the {field} field to continue.",
                actions=[
                    "Fill in the {field} field",
                    "Make sure you don't skip any required fields marked with *"
                ],
                category=ErrorMessageCategory.VALIDATION,
                severity=ErrorSeverity.LOW
            )
        )

        self.register_template(
            ErrorCode.CONTENT_TOO_LARGE,
            ErrorMessageTemplate(
                title="Content Too Large",
                message="The content you provided exceeds the maximum allowed size.",
                description="Please reduce the content size. Maximum allowed: {max_size} characters.",
                actions=[
                    "Shorten your text content",
                    "Split long content into multiple parts",
                    "Remove unnecessary formatting or images"
                ],
                category=ErrorMessageCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM
            )
        )

        # Authentication errors
        self.register_template(
            ErrorCode.UNAUTHORIZED,
            ErrorMessageTemplate(
                title="Authentication Required",
                message="You need to be logged in to access this resource.",
                description="Please sign in to your account to continue.",
                actions=[
                    "Sign in to your account",
                    "Create an account if you don't have one",
                    "Check if your session has expired"
                ],
                category=ErrorMessageCategory.AUTHENTICATION,
                severity=ErrorSeverity.MEDIUM
            )
        )

        self.register_template(
            ErrorCode.INVALID_TOKEN,
            ErrorMessageTemplate(
                title="Invalid Authentication",
                message="Your authentication token is invalid.",
                description="Please sign in again to get a new authentication token.",
                actions=[
                    "Sign out and sign back in",
                    "Clear your browser cache and cookies",
                    "Contact support if the problem persists"
                ],
                category=ErrorMessageCategory.AUTHENTICATION,
                severity=ErrorSeverity.MEDIUM
            )
        )

        self.register_template(
            ErrorCode.TOKEN_EXPIRED,
            ErrorMessageTemplate(
                title="Session Expired",
                message="Your session has expired due to inactivity.",
                description="Please sign in again to continue.",
                actions=[
                    "Sign in again to refresh your session",
                    "Consider enabling 'Stay signed in' if available"
                ],
                category=ErrorMessageCategory.AUTHENTICATION,
                severity=ErrorSeverity.MEDIUM
            )
        )

        # Authorization errors
        self.register_template(
            ErrorCode.FORBIDDEN,
            ErrorMessageTemplate(
                title="Access Denied",
                message="You don't have permission to access this resource.",
                description="This resource requires special permissions that you don't currently have.",
                actions=[
                    "Contact your administrator for access",
                    "Check if you're using the correct account",
                    "Verify that you have the necessary permissions"
                ],
                category=ErrorMessageCategory.AUTHORIZATION,
                severity=ErrorSeverity.MEDIUM
            )
        )

        # Not found errors
        self.register_template(
            ErrorCode.NOT_FOUND,
            ErrorMessageTemplate(
                title="Resource Not Found",
                message="The {resource_type} you're looking for doesn't exist.",
                description="We couldn't find the {resource_type} with ID: {resource_id}",
                actions=[
                    "Check the {resource_type} ID for typos",
                    "Browse the list of available {resource_type}s",
                    "Use the search function to find what you're looking for"
                ],
                category=ErrorMessageCategory.NOT_FOUND,
                severity=ErrorSeverity.LOW
            )
        )

        # Conflict errors
        self.register_template(
            ErrorCode.CONFLICT,
            ErrorMessageTemplate(
                title="Conflict Detected",
                message="There's a conflict with existing data.",
                description="Another user may have modified this resource, or there's duplicate information.",
                actions=[
                    "Refresh the page to see the latest information",
                    "Try your action again with updated data",
                    "Contact support if the conflict persists"
                ],
                category=ErrorMessageCategory.CONFLICT,
                severity=ErrorSeverity.MEDIUM
            )
        )

        self.register_template(
            ErrorCode.DUPLICATE_RESOURCE,
            ErrorMessageTemplate(
                title="Duplicate Resource",
                message="A {resource_type} with these details already exists.",
                description="Please check if this {resource_type} already exists and use a different name or identifier.",
                actions=[
                    "Search for existing {resource_type}s before creating new ones",
                    "Use a unique name or identifier",
                    "Edit the existing resource instead of creating a duplicate"
                ],
                category=ErrorMessageCategory.CONFLICT,
                severity=ErrorSeverity.MEDIUM
            )
        )

        # System errors
        self.register_template(
            ErrorCode.INTERNAL_SERVER_ERROR,
            ErrorMessageTemplate(
                title="System Error",
                message="Something went wrong on our end.",
                description="We're experiencing technical difficulties. Please try again in a few moments.",
                actions=[
                    "Try refreshing the page",
                    "Wait a few minutes and try again",
                    "Contact support if the problem continues"
                ],
                category=ErrorMessageCategory.SYSTEM,
                severity=ErrorSeverity.HIGH
            )
        )

        self.register_template(
            ErrorCode.DATABASE_ERROR,
            ErrorMessageTemplate(
                title="Database Error",
                message="We're having trouble accessing our database.",
                description="The system is experiencing database connectivity issues. Our team has been notified.",
                actions=[
                    "Try again in a few minutes",
                    "Save your work locally if possible",
                    "Contact support if the issue persists"
                ],
                category=ErrorMessageCategory.SYSTEM,
                severity=ErrorSeverity.HIGH
            )
        )

        self.register_template(
            ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="The {service_name} service is currently unavailable.",
                description="We're having trouble connecting to the {service_name} service. Please try again later.",
                actions=[
                    "Try again in a few minutes",
                    "Check if {service_name} is experiencing outages",
                    "Use an alternative service if available"
                ],
                category=ErrorMessageCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM
            )
        )

        # Service unavailable
        self.register_template(
            ErrorCode.SERVICE_UNAVAILABLE,
            ErrorMessageTemplate(
                title="Service Temporarily Unavailable",
                message="This service is temporarily down for maintenance.",
                description="We're currently performing maintenance. Please try again later.",
                actions=[
                    "Check back in a few minutes",
                    "Follow our status page for updates",
                    "Try again during off-peak hours"
                ],
                category=ErrorMessageCategory.SYSTEM,
                severity=ErrorSeverity.HIGH
            )
        )

        self.register_template(
            ErrorCode.MAINTENANCE_MODE,
            ErrorMessageTemplate(
                title="Under Maintenance",
                message="The system is currently under maintenance.",
                description="We're improving our service. We'll be back shortly!",
                actions=[
                    "Check our status page for updates",
                    "Try again in a few minutes",
                    "Follow us on social media for maintenance announcements"
                ],
                category=ErrorMessageCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM
            )
        )


# Global error message registry instance
_error_message_registry = ErrorMessageRegistry()


def get_error_message_registry() -> ErrorMessageRegistry:
    """
    Get the global error message registry instance.

    Returns:
        Global ErrorMessageRegistry instance
    """
    return _error_message_registry


def get_user_friendly_error(
    error_code: ErrorCode,
    **kwargs
) -> Dict[str, Any]:
    """
    Get a user-friendly error message for an error code.

    Args:
        error_code: Error code to get message for
        **kwargs: Parameters to substitute in templates

    Returns:
        User-friendly error message dictionary
    """
    registry = get_error_message_registry()
    message = registry.get_message(error_code, **kwargs)

    if message:
        return message

    # Fallback message if no template is found
    return {
        "title": "Error",
        "message": f"An error occurred: {error_code.value}",
        "description": "Please try again or contact support if the problem persists.",
        "actions": ["Try refreshing the page", "Contact support"],
        "category": ErrorMessageCategory.SYSTEM.value,
        "severity": ErrorSeverity.MEDIUM.value
    }


def format_validation_errors(validation_errors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Format FastAPI validation errors into user-friendly messages.

    Args:
        validation_errors: List of validation error dictionaries

    Returns:
        Formatted error message dictionary
    """
    if not validation_errors:
        return get_user_friendly_error(ErrorCode.VALIDATION_ERROR)

    # Get the first validation error for the main message
    first_error = validation_errors[0]
    field_path = " → ".join(str(loc) for loc in first_error.get("loc", []))
    error_message = first_error.get("msg", "Invalid input")
    error_type = first_error.get("type", "validation_error")

    # Create user-friendly message based on error type
    if "required" in error_type:
        title = "Required Field Missing"
        message = f"The field '{field_path}' is required."
        description = "Please fill in this field to continue."
        actions = ["Fill in the required field"]
    elif "too_long" in error_type:
        title = "Input Too Long"
        message = f"The field '{field_path}' is too long."
        description = "Please reduce the length of this field."
        actions = ["Shorten the content in this field"]
    elif "too_short" in error_type:
        title = "Input Too Short"
        message = f"The field '{field_path}' is too short."
        description = "Please provide more content for this field."
        actions = ["Add more content to this field"]
    elif "invalid_email" in error_type:
        title = "Invalid Email Address"
        message = "Please provide a valid email address."
        description = "The email format you entered is not correct."
        actions = ["Check the email format", "Enter a valid email address"]
    else:
        title = "Validation Error"
        message = f"The field '{field_path}' has an error: {error_message}"
        description = "Please correct the error in this field."
        actions = ["Fix the validation error"]

    return {
        "title": title,
        "message": message,
        "description": description,
        "actions": actions,
        "category": ErrorMessageCategory.VALIDATION.value,
        "severity": ErrorSeverity.LOW.value,
        "validation_errors": validation_errors
    }


# Export utility functions for common error scenarios
def get_field_required_message(field_name: str) -> Dict[str, Any]:
    """Get a message for a required field error."""
    return get_user_friendly_error(ErrorCode.MISSING_FIELD, field=field_name)


def get_not_found_message(resource_type: str, resource_id: str) -> Dict[str, Any]:
    """Get a message for a not found error."""
    return get_user_friendly_error(ErrorCode.NOT_FOUND, resource_type=resource_type, resource_id=resource_id)


def get_access_denied_message(resource_type: str = "resource") -> Dict[str, Any]:
    """Get a message for an access denied error."""
    return get_user_friendly_error(ErrorCode.FORBIDDEN)


def get_system_error_message(service_name: Optional[str] = None) -> Dict[str, Any]:
    """Get a message for a system error."""
    if service_name:
        return get_user_friendly_error(ErrorCode.EXTERNAL_SERVICE_ERROR, service_name=service_name)
    return get_user_friendly_error(ErrorCode.INTERNAL_SERVER_ERROR)