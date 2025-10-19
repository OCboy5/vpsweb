"""
Comprehensive Form Validation for VPSWeb Repository System

This module provides comprehensive form validation utilities that can be used
both server-side and to generate frontend validation rules.

Features:
- Form field validation rules
- Real-time validation support
- Custom validation functions
- Error message formatting
- Frontend rule generation
"""

import re
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from dataclasses import dataclass
from enum import Enum

from .validation import ContentValidationError
from .error_messages import get_user_friendly_error, format_validation_errors


class ValidationRuleType(str, Enum):
    """Types of validation rules."""
    REQUIRED = "required"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    PATTERN = "pattern"
    EMAIL = "email"
    URL = "url"
    NUMBER = "number"
    INTEGER = "integer"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    IN_CHOICES = "in_choices"
    NOT_IN_CHOICES = "not_in_choices"
    CUSTOM = "custom"
    FILE_TYPE = "file_type"
    FILE_SIZE = "file_size"
    LANGUAGE_CODE = "language_code"
    TAGS = "tags"
    POEM_CONTENT = "poem_content"
    TRANSLATION_CONTENT = "translation_content"


@dataclass
class ValidationRule:
    """
    A single validation rule for a form field.
    """
    rule_type: ValidationRuleType
    value: Optional[Any] = None
    message: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Post-initialization processing."""
        if self.params is None:
            self.params = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation rule to dictionary."""
        return {
            "type": self.rule_type.value,
            "value": self.value,
            "message": self.message,
            "params": self.params
        }


@dataclass
class FieldValidation:
    """
    Validation configuration for a single form field.
    """
    name: str
    label: str
    rules: List[ValidationRule]
    required: bool = False
    default_value: Optional[Any] = None
    field_type: str = "text"

    def add_rule(self, rule_type: ValidationRuleType, value: Any = None, message: str = None, **params) -> 'FieldValidation':
        """
        Add a validation rule to this field.

        Args:
            rule_type: Type of validation rule
            value: Value for the rule (if applicable)
            message: Custom error message
            **params: Additional parameters for the rule

        Returns:
            Self for chaining
        """
        rule = ValidationRule(rule_type, value, message, params)
        self.rules.append(rule)
        if rule_type == ValidationRuleType.REQUIRED:
            self.required = True
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert field validation to dictionary."""
        return {
            "name": self.name,
            "label": self.label,
            "field_type": self.field_type,
            "required": self.required,
            "default_value": self.default_value,
            "rules": [rule.to_dict() for rule in self.rules]
        }


@dataclass
class ValidationResult:
    """
    Result of form validation.
    """
    is_valid: bool
    errors: Dict[str, List[str]]
    cleaned_data: Dict[str, Any]
    field_errors: Dict[str, Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "cleaned_data": self.cleaned_data,
            "field_errors": self.field_errors
        }


class FormValidator:
    """
    Comprehensive form validator with support for various field types and rules.
    """

    def __init__(self):
        """Initialize the form validator."""
        self.custom_validators: Dict[str, Callable] = {}
        self._register_default_validators()

    def add_field(self, name: str, label: str = None, field_type: str = "text") -> FieldValidation:
        """
        Add a new field to the form.

        Args:
            name: Field name
            label: Human-readable label
            field_type: Type of field (text, email, number, etc.)

        Returns:
            FieldValidation object for further configuration
        """
        if label is None:
            label = name.replace('_', ' ').title()

        field = FieldValidation(name=name, label=label, field_type=field_type, rules=[])
        return field

    def validate_form(self, form_data: Dict[str, Any], fields: List[FieldValidation]) -> ValidationResult:
        """
        Validate form data against field configurations.

        Args:
            form_data: Form data to validate
            fields: List of field validations

        Returns:
            ValidationResult with errors and cleaned data
        """
        errors = {}
        field_errors = {}
        cleaned_data = {}

        for field in fields:
            field_name = field.name
            field_value = form_data.get(field_name, field.default_value)
            field_errors_list = []

            # Clean the value
            cleaned_value = self._clean_field_value(field_value, field)
            cleaned_data[field_name] = cleaned_value

            # Validate each rule
            for rule in field.rules:
                error_message = self._validate_rule(cleaned_value, rule, field)
                if error_message:
                    field_errors_list.append(error_message)

            # Store field errors
            if field_errors_list:
                field_errors[field_name] = {
                    "field": field_name,
                    "label": field.label,
                    "errors": field_errors_list
                }
                errors[field_name] = field_errors_list

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            cleaned_data=cleaned_data,
            field_errors=field_errors
        )

    def generate_frontend_rules(self, fields: List[FieldValidation]) -> Dict[str, Any]:
        """
        Generate frontend validation rules for JavaScript validation.

        Args:
            fields: List of field validations

        Returns:
            Dictionary with frontend validation rules
        """
        frontend_rules = {}

        for field in fields:
            field_rules = []
            html5_attrs = {}

            for rule in field.rules:
                rule_config = self._rule_to_frontend(rule)
                if rule_config:
                    field_rules.append(rule_config)

                # Generate HTML5 validation attributes
                html5_attr = self._rule_to_html5_attr(rule)
                if html5_attr:
                    html5_attrs.update(html5_attr)

            frontend_rules[field.name] = {
                "label": field.label,
                "field_type": field.field_type,
                "required": field.required,
                "rules": field_rules,
                "html5_attrs": html5_attrs
            }

        return {
            "fields": frontend_rules,
            "error_messages": self._get_frontend_error_messages()
        }

    def _clean_field_value(self, value: Any, field: FieldValidation) -> Any:
        """Clean a field value based on field type."""
        if value is None:
            return None

        if field.field_type in ["text", "email", "password", "textarea"]:
            return str(value).strip() if value else ""
        elif field.field_type in ["number", "integer"]:
            try:
                if field.field_type == "integer":
                    return int(float(str(value)))
                else:
                    return float(str(value))
            except (ValueError, TypeError):
                return None
        elif field.field_type == "checkbox":
            return bool(value)
        elif field.field_type == "tags":
            if isinstance(value, str):
                # Split comma-separated tags
                return [tag.strip() for tag in value.split(",") if tag.strip()]
            elif isinstance(value, list):
                return [str(tag).strip() for tag in value if str(tag).strip()]
            return []
        else:
            return value

    def _validate_rule(self, value: Any, rule: ValidationRule, field: FieldValidation) -> Optional[str]:
        """Validate a single rule against a value."""
        try:
            if rule.rule_type == ValidationRuleType.REQUIRED:
                if not value or (isinstance(value, str) and not value.strip()):
                    return rule.message or f"{field.label} is required."

            elif rule.rule_type == ValidationRuleType.MIN_LENGTH:
                if value and len(str(value)) < rule.value:
                    return rule.message or f"{field.label} must be at least {rule.value} characters long."

            elif rule.rule_type == ValidationRuleType.MAX_LENGTH:
                if value and len(str(value)) > rule.value:
                    return rule.message or f"{field.label} must not exceed {rule.value} characters."

            elif rule.rule_type == ValidationRuleType.PATTERN:
                if value and not re.match(rule.value, str(value)):
                    return rule.message or f"{field.label} format is invalid."

            elif rule.rule_type == ValidationRuleType.EMAIL:
                if value and not self._validate_email(str(value)):
                    return rule.message or f"{field.label} must be a valid email address."

            elif rule.rule_type == ValidationRuleType.URL:
                if value and not self._validate_url(str(value)):
                    return rule.message or f"{field.label} must be a valid URL."

            elif rule.rule_type == ValidationRuleType.NUMBER:
                if value is not None:
                    try:
                        float(str(value))
                    except (ValueError, TypeError):
                        return rule.message or f"{field.label} must be a number."

            elif rule.rule_type == ValidationRuleType.INTEGER:
                if value is not None:
                    try:
                        int(float(str(value)))
                    except (ValueError, TypeError):
                        return rule.message or f"{field.label} must be an integer."

            elif rule.rule_type == ValidationRuleType.MIN_VALUE:
                if value is not None:
                    try:
                        numeric_value = float(str(value))
                        if numeric_value < rule.value:
                            return rule.message or f"{field.label} must be at least {rule.value}."
                    except (ValueError, TypeError):
                        pass

            elif rule.rule_type == ValidationRuleType.MAX_VALUE:
                if value is not None:
                    try:
                        numeric_value = float(str(value))
                        if numeric_value > rule.value:
                            return rule.message or f"{field.label} must not exceed {rule.value}."
                    except (ValueError, TypeError):
                        pass

            elif rule.rule_type == ValidationRuleType.IN_CHOICES:
                if value and value not in rule.value:
                    return rule.message or f"{field.label} must be one of: {', '.join(map(str, rule.value))}."

            elif rule.rule_type == ValidationRuleType.NOT_IN_CHOICES:
                if value and value in rule.value:
                    return rule.message or f"{field.label} cannot be any of: {', '.join(map(str, rule.value))}."

            elif rule.rule_type == ValidationRuleType.LANGUAGE_CODE:
                if value:
                    from ..utils.language_mapper import validate_language_code
                    is_valid, error_msg = validate_language_code(str(value))
                    if not is_valid:
                        return rule.message or f"{field.label}: {error_msg or 'Invalid language code'}."

            elif rule.rule_type == ValidationRuleType.TAGS:
                if value:
                    if isinstance(value, list) and len(value) > 20:
                        return rule.message or f"{field.label} cannot have more than 20 tags."
                    if isinstance(value, str) and len(value.split(',')) > 20:
                        return rule.message or f"{field.label} cannot have more than 20 tags."

            elif rule.rule_type == ValidationRuleType.POEM_CONTENT:
                if value:
                    content = str(value)
                    if len(content) < 10:
                        return rule.message or f"{field.label} must be at least 10 characters long."
                    if len(content) > 50000:
                        return rule.message or f"{field.label} must not exceed 50,000 characters."

            elif rule.rule_type == ValidationRuleType.TRANSLATION_CONTENT:
                if value:
                    content = str(value)
                    if len(content) < 5:
                        return rule.message or f"{field.label} must be at least 5 characters long."
                    if len(content) > 60000:
                        return rule.message or f"{field.label} must not exceed 60,000 characters."

            elif rule.rule_type == ValidationRuleType.CUSTOM:
                validator_name = rule.value
                if validator_name in self.custom_validators:
                    validator = self.custom_validators[validator_name]
                    error_message = validator(value, field, rule.params)
                    if error_message:
                        return rule.message or error_message

        except Exception as e:
            # If validation fails due to an exception, return a generic error
            return rule.message or f"Validation error for {field.label}."

        return None

    def _validate_email(self, email: str) -> bool:
        """Validate email address format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def _validate_url(self, url: str) -> bool:
        """Validate URL format."""
        pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)*[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return pattern.match(url) is not None

    def _rule_to_frontend(self, rule: ValidationRule) -> Optional[Dict[str, Any]]:
        """Convert a validation rule to frontend configuration."""
        if rule.rule_type == ValidationRuleType.REQUIRED:
            return {"type": "required", "message": rule.message}
        elif rule.rule_type == ValidationRuleType.MIN_LENGTH:
            return {"type": "minLength", "value": rule.value, "message": rule.message}
        elif rule.rule_type == ValidationRuleType.MAX_LENGTH:
            return {"type": "maxLength", "value": rule.value, "message": rule.message}
        elif rule.rule_type == ValidationRuleType.PATTERN:
            return {"type": "pattern", "value": rule.value, "message": rule.message}
        elif rule.rule_type == ValidationRuleType.EMAIL:
            return {"type": "email", "message": rule.message}
        elif rule.rule_type == ValidationRuleType.URL:
            return {"type": "url", "message": rule.message}
        elif rule.rule_type == ValidationRuleType.MIN_VALUE:
            return {"type": "min", "value": rule.value, "message": rule.message}
        elif rule.rule_type == ValidationRuleType.MAX_VALUE:
            return {"type": "max", "value": rule.value, "message": rule.message}
        elif rule.rule_type == ValidationRuleType.IN_CHOICES:
            return {"type": "in", "choices": rule.value, "message": rule.message}
        elif rule.rule_type == ValidationRuleType.TAGS:
            return {"type": "tags", "maxTags": rule.params.get("max_tags", 20), "message": rule.message}
        return None

    def _rule_to_html5_attr(self, rule: ValidationRule) -> Optional[Dict[str, str]]:
        """Convert a validation rule to HTML5 validation attributes."""
        if rule.rule_type == ValidationRuleType.REQUIRED:
            return {"required": "required"}
        elif rule.rule_type == ValidationRuleType.MIN_LENGTH:
            return {"minlength": str(rule.value)}
        elif rule.rule_type == ValidationRuleType.MAX_LENGTH:
            return {"maxlength": str(rule.value)}
        elif rule.rule_type == ValidationRuleType.PATTERN:
            return {"pattern": rule.value}
        elif rule.rule_type == ValidationRuleType.MIN_VALUE:
            return {"min": str(rule.value)}
        elif rule.rule_type == ValidationRuleType.MAX_VALUE:
            return {"max": str(rule.value)}
        return None

    def _get_frontend_error_messages(self) -> Dict[str, str]:
        """Get default frontend error messages."""
        return {
            "required": "This field is required.",
            "minLength": "This field must be at least {value} characters long.",
            "maxLength": "This field must not exceed {value} characters.",
            "pattern": "This field format is invalid.",
            "email": "Please enter a valid email address.",
            "url": "Please enter a valid URL.",
            "min": "This field must be at least {value}.",
            "max": "This field must not exceed {value}.",
            "in": "Please select a valid option.",
            "tags": "Please enter valid tags (maximum {maxTags})."
        }

    def _register_default_validators(self):
        """Register default custom validators."""
        # Add any custom validators here
        pass

    def register_custom_validator(self, name: str, validator: Callable):
        """
        Register a custom validation function.

        Args:
            name: Name of the validator
            validator: Validation function that takes (value, field, params) and returns error message or None
        """
        self.custom_validators[name] = validator


# Predefined field configurations for common use cases
class CommonFieldConfigs:
    """Predefined field configurations for common form fields."""

    @staticmethod
    def poem_title_field() -> FieldValidation:
        """Create a poem title field configuration."""
        return FormValidator().add_field("poem_title", "Poem Title")\
            .add_rule(ValidationRuleType.REQUIRED)\
            .add_rule(ValidationRuleType.MIN_LENGTH, 1)\
            .add_rule(ValidationRuleType.MAX_LENGTH, 255)\
            .add_rule(ValidationRuleType.PATTERN, r'^[a-zA-Z0-9\u4e00-\u9fff\u3400-\u4dbf\-\s\'\-\.\:\,\!\?]+$',
                     "Title contains invalid characters")

    @staticmethod
    def poet_name_field() -> FieldValidation:
        """Create a poet name field configuration."""
        return FormValidator().add_field("poet_name", "Poet Name")\
            .add_rule(ValidationRuleType.REQUIRED)\
            .add_rule(ValidationRuleType.MIN_LENGTH, 2)\
            .add_rule(ValidationRuleType.MAX_LENGTH, 255)\
            .add_rule(ValidationRuleType.PATTERN, r'^[a-zA-Z\u4e00-\u9fff\u3400-\u4dbf\-\s\'\-\.]+$',
                     "Name contains invalid characters")

    @staticmethod
    def poem_content_field() -> FieldValidation:
        """Create a poem content field configuration."""
        return FormValidator().add_field("original_text", "Poem Content", "textarea")\
            .add_rule(ValidationRuleType.REQUIRED)\
            .add_rule(ValidationRuleType.POEM_CONTENT)

    @staticmethod
    def translation_content_field() -> FieldValidation:
        """Create a translation content field configuration."""
        return FormValidator().add_field("translated_text", "Translation", "textarea")\
            .add_rule(ValidationRuleType.REQUIRED)\
            .add_rule(ValidationRuleType.TRANSLATION_CONTENT)

    @staticmethod
    def language_code_field() -> FieldValidation:
        """Create a language code field configuration."""
        return FormValidator().add_field("source_language", "Source Language")\
            .add_rule(ValidationRuleType.REQUIRED)\
            .add_rule(ValidationRuleType.LANGUAGE_CODE)

    @staticmethod
    def tags_field() -> FieldValidation:
        """Create a tags field configuration."""
        return FormValidator().add_field("tags", "Tags", "tags")\
            .add_rule(ValidationRuleType.TAGS)

    @staticmethod
    def email_field() -> FieldValidation:
        """Create an email field configuration."""
        return FormValidator().add_field("email", "Email Address", "email")\
            .add_rule(ValidationRuleType.EMAIL)\
            .add_rule(ValidationRuleType.MAX_LENGTH, 255)

    @staticmethod
    def translator_notes_field() -> FieldValidation:
        """Create a translator notes field configuration."""
        return FormValidator().add_field("translator_notes", "Translator Notes", "textarea")\
            .add_rule(ValidationRuleType.MAX_LENGTH, 5000)


# Global form validator instance
_form_validator = FormValidator()


def get_form_validator() -> FormValidator:
    """Get the global form validator instance."""
    return _form_validator


def validate_poem_form(data: Dict[str, Any]) -> ValidationResult:
    """
    Validate poem creation/update form data.

    Args:
        data: Form data to validate

    Returns:
        ValidationResult with errors and cleaned data
    """
    validator = get_form_validator()
    fields = [
        CommonFieldConfigs.poem_title_field(),
        CommonFieldConfigs.poet_name_field(),
        CommonFieldConfigs.poem_content_field(),
        CommonFieldConfigs.language_code_field(),
        CommonFieldConfigs.tags_field(),
    ]

    return validator.validate_form(data, fields)


def validate_translation_form(data: Dict[str, Any]) -> ValidationResult:
    """
    Validate translation creation/update form data.

    Args:
        data: Form data to validate

    Returns:
        ValidationResult with errors and cleaned data
    """
    validator = get_form_validator()
    fields = [
        CommonFieldConfigs.translation_content_field(),
        CommonFieldConfigs.language_code_field(),
        CommonFieldConfigs.translator_notes_field(),
    ]

    return validator.validate_form(data, fields)