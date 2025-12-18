"""
Prompt template service for Vox Poetica Studio Web.

This module provides a service for loading, validating, and rendering
prompt templates using Jinja2 templating engine.
"""

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

import yaml
from jinja2 import (
    Environment,
    FileSystemLoader,
    TemplateError,
    UndefinedError,
)

logger = logging.getLogger(__name__)


class PromptServiceError(Exception):
    """Base exception for prompt service errors."""


class TemplateLoadError(PromptServiceError):
    """Raised when template loading fails."""


class TemplateVariableError(PromptServiceError):
    """Raised when template variables are invalid or missing."""


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
            prompts_dir = (
                current_dir.parent.parent.parent / "config" / "prompts"
            )

        self.prompts_dir = Path(prompts_dir)
        self.templates_dir = self.prompts_dir

        # Initialize fallback directory for V1 templates
        self.fallback_dir = self.prompts_dir.parent / "prompts_V1"

        # Validate prompts directory exists
        if not self.prompts_dir.exists():
            raise TemplateLoadError(
                f"Prompts directory not found: {self.prompts_dir}"
            )

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
        if self.fallback_dir.exists():
            logger.info(
                f"V1 fallback directory available: {self.fallback_dir}"
            )

    def _setup_custom_filters(self) -> None:
        """Setup custom Jinja2 filters."""
        # Add strip filter to remove extra whitespace
        self.jinja_env.filters["strip"] = lambda x: x.strip() if x else x

        # Add word count filter
        self.jinja_env.filters["wordcount"] = lambda x: (
            len(x.split()) if x else 0
        )

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
            # Try fallback to V1 templates directory
            if self.fallback_dir.exists():
                fallback_file = self.fallback_dir / f"{template_name}.yaml"
                if fallback_file.exists():
                    logger.debug(
                        f"Loading V1 template from fallback: {template_name}"
                    )
                    template_file = fallback_file
                else:
                    available_templates = list(self.prompts_dir.glob("*.yaml"))
                    fallback_templates = (
                        list(self.fallback_dir.glob("*.yaml"))
                        if self.fallback_dir.exists()
                        else []
                    )
                    available_names = [f.stem for f in available_templates]
                    fallback_names = [f.stem for f in fallback_templates]
                    raise TemplateLoadError(
                        f"Template file '{template_name}.yaml' not found in {self.prompts_dir} "
                        f"or {self.fallback_dir}. Available: {available_names}, V1 fallbacks: {fallback_names}"
                    )
            else:
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

            # Log which version was loaded
            if str(self.fallback_dir) in str(template_file):
                logger.debug(f"Loaded V1 template: {template_name}")
            else:
                logger.debug(f"Loaded V2 template: {template_name}")

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
        template_names = sorted([f.stem for f in yaml_files])

        # Include V1 fallback templates if available
        if self.fallback_dir.exists():
            fallback_files = self.fallback_dir.glob("*.yaml")
            fallback_names = sorted([f.stem for f in fallback_files])
            # Combine and deduplicate
            all_names = list(set(template_names + fallback_names))
            return sorted(all_names)

        return template_names

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
            system_vars = self._extract_jinja_variables(
                template_data["system"]
            )
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
                system_template = self.jinja_env.from_string(
                    template_data["system"]
                )
                system_prompt = system_template.render(**variables)
                logger.debug(
                    f"Rendered system prompt ({len(system_prompt)} chars)"
                )
            except (TemplateError, UndefinedError) as e:
                raise TemplateVariableError(
                    f"Error rendering system prompt: {e}"
                )

        # Render user prompt if present
        user_prompt = ""
        if "user" in template_data:
            try:
                user_template = self.jinja_env.from_string(
                    template_data["user"]
                )
                user_prompt = user_template.render(**variables)
                logger.debug(
                    f"Rendered user prompt ({len(user_prompt)} chars)"
                )
            except (TemplateError, UndefinedError) as e:
                raise TemplateVariableError(
                    f"Error rendering user prompt: {e}"
                )

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
                system_template = permissive_env.from_string(
                    template_data["system"]
                )
                system_prompt = system_template.render(**variables)

            user_prompt = ""
            if "user" in template_data:
                user_template = permissive_env.from_string(
                    template_data["user"]
                )
                user_prompt = user_template.render(**variables)

            return system_prompt, user_prompt

    def load_bbr_prompt(self) -> Dict[str, Any]:
        """
        Load the Background Briefing Report prompt template.

        Returns:
            BBR template data dictionary

        Raises:
            TemplateLoadError: If BBR template cannot be loaded
        """
        try:
            return self.get_template("background_briefing_report")
        except TemplateLoadError as e:
            raise TemplateLoadError(f"BBR template not available: {e}")

    def render_bbr_prompt(
        self,
        poet_name: str,
        poem_title: str,
        original_poem: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Render the Background Briefing Report prompt with poem information.

        Args:
            poet_name: Name of the poet
            poem_title: Title of the poem
            original_poem: Full text of the original poem
            source_lang: Source language (optional)
            target_lang: Target language (optional)

        Returns:
            Tuple of (system_prompt, user_prompt)

        Raises:
            TemplateLoadError: If BBR template cannot be loaded
            TemplateVariableError: If required variables are missing
            TemplateError: If template rendering fails
        """
        variables = {
            "poet_name": poet_name,
            "poem_title": poem_title,
            "original_poem": original_poem,
            "source_lang": source_lang or "Unknown",
            "target_lang": target_lang or "Chinese",
        }

        return self.render_prompt("background_briefing_report", variables)

    def get_prompt_template(
        self, template_name: str, version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a prompt template with optional version specification.

        Args:
            template_name: Name of the template
            version: Optional version ("v1" or "v2", defaults to v2)

        Returns:
            Template data dictionary

        Raises:
            TemplateLoadError: If template cannot be loaded
        """
        if version == "v1" and self.fallback_dir.exists():
            # Force loading from V1 directory
            template_file = self.fallback_dir / f"{template_name}.yaml"
            if template_file.exists():
                try:
                    with open(template_file, "r", encoding="utf-8") as f:
                        template_data = yaml.safe_load(f)
                    if template_data:
                        logger.debug(f"Loaded V1 template: {template_name}")
                        return template_data
                except Exception as e:
                    logger.warning(
                        f"Failed to load V1 template {template_name}: {e}"
                    )

        # Default to regular loading (V2 priority with V1 fallback)
        return self.get_template(template_name)

    def validate_v2_template(self, template_name: str) -> bool:
        """
        Validate that a V2 template follows the expected structure.

        Args:
            template_name: Name of the V2 template to validate

        Returns:
            True if template is valid V2 format, False otherwise
        """
        try:
            template_data = self.get_template(template_name)

            # Check for V2-specific structure
            if "system" in template_data and "user" in template_data:
                # Check for V2-specific variables in BBR templates
                if template_name == "background_briefing_report":
                    user_content = template_data.get("user", "")
                    required_sections = ["<SOURCE_TEXT>", "{{ source_text }}"]
                    for section in required_sections:
                        if section not in user_content:
                            logger.warning(
                                f"V2 BBR template missing required section: {section}"
                            )
                            return False

                logger.debug(f"V2 template validation passed: {template_name}")
                return True
            else:
                logger.warning(
                    f"Template {template_name} does not follow V2 structure"
                )
                return False

        except Exception as e:
            logger.error(
                f"V2 template validation failed for {template_name}: {e}"
            )
            return False

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
            logger.error(
                f"Template validation failed for {template_name}: {e}"
            )
            return False

    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """
        Get information about a template including its version and metadata.

        Args:
            template_name: Name of the template

        Returns:
            Dictionary with template information
        """
        try:
            template_data = self.get_template(template_name)
            template_file = self.prompts_dir / f"{template_name}.yaml"

            # Determine if V1 or V2
            is_v1 = str(self.fallback_dir) in str(
                self._load_template_file.__wrapped__(self, template_name)
            )
            version = "v1" if is_v1 else "v2"

            info = {
                "name": template_name,
                "version": version,
                "has_system": "system" in template_data,
                "has_user": "user" in template_data,
                "file_path": str(template_file),
                "file_size": (
                    template_file.stat().st_size
                    if template_file.exists()
                    else 0
                ),
                "validation_status": self.validate_template(template_name),
            }

            # Add V2-specific validation
            if version == "v2":
                info["v2_validation"] = self.validate_v2_template(
                    template_name
                )

            return info

        except Exception as e:
            logger.error(
                f"Failed to get template info for {template_name}: {e}"
            )
            return {
                "name": template_name,
                "error": str(e),
                "validation_status": False,
            }

    def __repr__(self) -> str:
        """String representation of the service."""
        v2_count = len(list(self.prompts_dir.glob("*.yaml")))
        v1_count = (
            len(list(self.fallback_dir.glob("*.yaml")))
            if self.fallback_dir.exists()
            else 0
        )
        return (
            f"PromptService(prompts_dir='{self.prompts_dir}', "
            f"v2_templates={v2_count}, v1_templates={v1_count})"
        )
