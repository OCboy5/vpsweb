"""
Prompt template service for Vox Poetica Studio Web.

This module provides a service for loading, validating, and rendering
prompt templates using Jinja2 templating engine.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Set
from jinja2 import (
    Environment,
    FileSystemLoader,
    Template,
    TemplateError,
    UndefinedError,
)
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


class PromptServiceError(Exception):
    """Base exception for prompt service errors."""

    pass


class TemplateLoadError(PromptServiceError):
    """Raised when template loading fails."""

    pass


class TemplateVariableError(PromptServiceError):
    """Raised when template variables are invalid or missing."""

    pass


class PromptService:
    """
    Service for managing and rendering prompt templates.

    This service loads YAML prompt templates from the config/prompts directory,
    validates required variables, and renders them using Jinja2 templating.
    """

    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Initialize the prompt service.

        Args:
            prompts_dir: Directory containing prompt templates.
                        Defaults to config/prompts relative to project root.
        """
        if prompts_dir is None:
            # Default to config/prompts relative to this file's location
            current_dir = Path(__file__).parent
            prompts_dir = current_dir.parent.parent.parent / "config" / "prompts"

        self.prompts_dir = Path(prompts_dir)
        self.templates_dir = self.prompts_dir

        # Validate prompts directory exists
        if not self.prompts_dir.exists():
            raise TemplateLoadError(f"Prompts directory not found: {self.prompts_dir}")

        if not self.prompts_dir.is_dir():
            raise TemplateLoadError(
                f"Prompts path is not a directory: {self.prompts_dir}"
            )

        # Initialize Jinja2 environment
        from jinja2 import StrictUndefined

        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            undefined=StrictUndefined,  # Raise errors for undefined variables
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        # Add custom filters if needed
        self._setup_custom_filters()

        logger.info(
            f"Initialized PromptService with prompts directory: {self.prompts_dir}"
        )

    def _setup_custom_filters(self) -> None:
        """Setup custom Jinja2 filters."""
        # Add strip filter to remove extra whitespace
        self.jinja_env.filters["strip"] = lambda x: x.strip() if x else x

        # Add word count filter
        self.jinja_env.filters["wordcount"] = lambda x: len(x.split()) if x else 0

    @lru_cache(maxsize=32)
    def _load_template_file(self, template_name: str) -> Dict[str, Any]:
        """
        Load a template file from disk with caching.

        Args:
            template_name: Name of the template file (without .yaml extension)

        Returns:
            Template data dictionary

        Raises:
            TemplateLoadError: If template file cannot be loaded
        """
        template_file = self.prompts_dir / f"{template_name}.yaml"

        if not template_file.exists():
            available_templates = list(self.prompts_dir.glob("*.yaml"))
            available_names = [f.stem for f in available_templates]
            raise TemplateLoadError(
                f"Template file '{template_name}.yaml' not found in {self.prompts_dir}. "
                f"Available templates: {available_names}"
            )

        try:
            with open(template_file, "r", encoding="utf-8") as f:
                template_data = yaml.safe_load(f)

            if template_data is None:
                raise TemplateLoadError(
                    f"Template file '{template_name}.yaml' is empty"
                )

            logger.debug(f"Loaded template: {template_name}")
            return template_data

        except yaml.YAMLError as e:
            raise TemplateLoadError(
                f"Invalid YAML in template file '{template_name}.yaml': {e}"
            )
        except Exception as e:
            raise TemplateLoadError(
                f"Error loading template file '{template_name}.yaml': {e}"
            )

    def get_template(self, template_name: str) -> Dict[str, Any]:
        """
        Get a template by name.

        Args:
            template_name: Name of the template (without .yaml extension)

        Returns:
            Template data dictionary

        Raises:
            TemplateLoadError: If template cannot be loaded
        """
        return self._load_template_file(template_name)

    def list_templates(self) -> list[str]:
        """
        List all available template names.

        Returns:
            List of template names (without extensions)
        """
        yaml_files = self.prompts_dir.glob("*.yaml")
        return sorted([f.stem for f in yaml_files])

    def _extract_jinja_variables(self, template_str: str) -> Set[str]:
        """
        Extract Jinja2 variable names from a template string.

        Args:
            template_str: Template string to analyze

        Returns:
            Set of variable names
        """
        # Simple regex to find Jinja2 variables {{ variable_name }}
        # This handles nested variables and filters
        variable_pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*(?:\|[\w\(\)\s,\.]*)?\s*\}\}"
        matches = re.findall(variable_pattern, template_str)

        # Extract base variable names (before any dots for attribute access)
        variables = set()
        for match in matches:
            # Handle nested attributes like {{ original_poem.title }}
            base_var = match.split(".")[0]
            variables.add(base_var)

        return variables

    def _validate_template_variables(
        self, template_data: Dict[str, Any], variables: Dict[str, Any]
    ) -> None:
        """
        Validate that all required template variables are provided.

        Args:
            template_data: Template data with system and user prompts
            variables: Variables to render the template with

        Raises:
            TemplateVariableError: If required variables are missing
        """
        required_vars = set()

        # Extract variables from system prompt
        if "system" in template_data:
            system_vars = self._extract_jinja_variables(template_data["system"])
            required_vars.update(system_vars)

        # Extract variables from user prompt
        if "user" in template_data:
            user_vars = self._extract_jinja_variables(template_data["user"])
            required_vars.update(user_vars)

        # Check if all required variables are provided
        missing_vars = required_vars - set(variables.keys())
        if missing_vars:
            available_vars = list(variables.keys())
            raise TemplateVariableError(
                f"Missing required template variables: {sorted(missing_vars)}. "
                f"Available variables: {available_vars}"
            )

    def render_prompt(
        self, template_name: str, variables: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Render a prompt template with the given variables.

        Args:
            template_name: Name of the template to render
            variables: Dictionary of variables to substitute in the template

        Returns:
            Tuple of (system_prompt, user_prompt)

        Raises:
            TemplateLoadError: If template cannot be loaded
            TemplateVariableError: If required variables are missing
            TemplateError: If template rendering fails
        """
        logger.debug(
            f"Rendering template: {template_name} with variables: {list(variables.keys())}"
        )

        # Load template data
        template_data = self.get_template(template_name)

        # Validate required variables
        self._validate_template_variables(template_data, variables)

        # Render system prompt if present
        system_prompt = ""
        if "system" in template_data:
            try:
                system_template = self.jinja_env.from_string(template_data["system"])
                system_prompt = system_template.render(**variables)
                logger.debug(f"Rendered system prompt ({len(system_prompt)} chars)")
            except (TemplateError, UndefinedError) as e:
                raise TemplateVariableError(f"Error rendering system prompt: {e}")

        # Render user prompt if present
        user_prompt = ""
        if "user" in template_data:
            try:
                user_template = self.jinja_env.from_string(template_data["user"])
                user_prompt = user_template.render(**variables)
                logger.debug(f"Rendered user prompt ({len(user_prompt)} chars)")
            except (TemplateError, UndefinedError) as e:
                raise TemplateVariableError(f"Error rendering user prompt: {e}")

        logger.info(f"Successfully rendered template: {template_name}")
        return system_prompt, user_prompt

    def render_prompt_safe(
        self,
        template_name: str,
        variables: Dict[str, Any],
        default_values: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """
        Render a prompt template with fallback to default values for missing variables.

        Args:
            template_name: Name of the template to render
            variables: Dictionary of variables to substitute
            default_values: Optional default values for missing variables

        Returns:
            Tuple of (system_prompt, user_prompt)

        Raises:
            TemplateLoadError: If template cannot be loaded
            TemplateError: If template rendering fails
        """
        if default_values:
            # Merge variables with defaults
            merged_vars = default_values.copy()
            merged_vars.update(variables)
            variables = merged_vars

        try:
            return self.render_prompt(template_name, variables)
        except TemplateVariableError as e:
            # If validation fails with defaults, try without strict validation
            logger.warning(
                f"Template validation failed with defaults, attempting safe render: {e}"
            )

            # Load template and render with available variables
            template_data = self.get_template(template_name)

            # Create a more permissive Jinja2 environment
            from jinja2 import ChainableUndefined

            permissive_env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                undefined=ChainableUndefined,  # Don't raise errors for undefined vars
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True,
            )

            system_prompt = ""
            if "system" in template_data:
                system_template = permissive_env.from_string(template_data["system"])
                system_prompt = system_template.render(**variables)

            user_prompt = ""
            if "user" in template_data:
                user_template = permissive_env.from_string(template_data["user"])
                user_prompt = user_template.render(**variables)

            return system_prompt, user_prompt

    def clear_cache(self) -> None:
        """
        Clear the template cache.
        """
        self._load_template_file.cache_clear()
        logger.info("Cleared template cache")

    def validate_template(self, template_name: str) -> bool:
        """
        Validate that a template can be loaded and parsed correctly.

        Args:
            template_name: Name of the template to validate

        Returns:
            True if template is valid, False otherwise
        """
        try:
            template_data = self.get_template(template_name)

            # Try to parse system prompt if present
            if "system" in template_data:
                self.jinja_env.from_string(template_data["system"])

            # Try to parse user prompt if present
            if "user" in template_data:
                self.jinja_env.from_string(template_data["user"])

            logger.debug(f"Template validation passed: {template_name}")
            return True

        except Exception as e:
            logger.error(f"Template validation failed for {template_name}: {e}")
            return False

    def __repr__(self) -> str:
        """String representation of the service."""
        return f"PromptService(prompts_dir='{self.prompts_dir}', templates_loaded={len(self.list_templates())})"
