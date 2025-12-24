"""
Translation notes synthesizer for Vox Poetica Studio Web.

This module handles LLM-based synthesis of translation notes from workflow outputs,
using deepseek-reasoner with Chinese prompts for WeChat article generation.
"""

import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional

from ..models.wechat import TranslationNotes
from ..services.llm.base import BaseLLMProvider
from ..services.llm.factory import LLMFactory
from ..services.prompts import PromptService
from .logger import get_logger

logger = get_logger(__name__)


class TranslationNotesSynthesizerError(Exception):
    """Exception raised for translation notes synthesis errors."""


class TranslationNotesSynthesizer:
    """
    Synthesizes translation notes using LLM from workflow outputs.

    Uses deepseek-reasoner with Chinese prompts to generate reader-friendly
    translation notes for WeChat articles.
    """

    def __init__(
        self,
        provider_config: Dict[str, Any],
        system_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize translation notes synthesizer.

        Args:
            provider_config: LLM provider configuration
            system_config: System configuration with translation notes parameters
        """
        self.provider_config = provider_config
        self.system_config = system_config or {}
        self.prompt_service = PromptService()
        self._llm_provider: Optional[BaseLLMProvider] = None

    async def initialize(self) -> None:
        """Initialize LLM provider."""
        try:
            # Create LLM provider using factory
            self._llm_provider = LLMFactory.create_provider(
                provider_type=self.provider_config.get("type", "deepseek"),
                config=self.provider_config,
            )
            logger.info(f"Translation notes synthesizer initialized with {self.provider_config.get('type')} provider")
        except Exception as e:
            raise TranslationNotesSynthesizerError(f"Failed to initialize LLM provider: {e}")

    async def synthesize_notes(
        self, translation_data: Dict[str, Any], workflow_mode: str = "hybrid"
    ) -> TranslationNotes:
        """
        Synthesize translation notes from translation workflow data.

        Args:
            translation_data: Translation workflow JSON data
            workflow_mode: Workflow mode (reasoning, non_reasoning, hybrid)

        Returns:
            TranslationNotes with digest and bullet points

        Raises:
            TranslationNotesSynthesizerError: If synthesis fails
        """
        if not self._llm_provider:
            await self.initialize()

        try:
            # Extract translation notes sources
            notes_sources = self._extract_notes_sources(translation_data)

            # Determine prompt file based on workflow mode
            prompt_file = self._get_prompt_file(workflow_mode)

            # Format prompt with translation data using the service
            try:
                _, formatted_prompt = self.prompt_service.render_prompt(
                    template_name=prompt_file, variables=notes_sources
                )
            except Exception as e:
                # Fallback to manual formatting if render fails
                logger.warning(f"Template rendering failed, using fallback: {e}")
                prompt_template = self.prompt_service.get_template(prompt_file)
                formatted_prompt = self._format_prompt_fallback(prompt_template, notes_sources)

            # Generate notes using LLM
            response = await self._generate_with_llm(formatted_prompt, workflow_mode)

            # Parse XML response
            translation_notes = self._parse_xml_response(response)

            logger.info(f"Successfully synthesized {len(translation_notes.notes)} translation notes")
            return translation_notes

        except Exception as e:
            logger.error(f"Translation notes synthesis failed: {e}")
            raise TranslationNotesSynthesizerError(f"Failed to synthesize translation notes: {e}")

    def _extract_notes_sources(self, translation_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract translation notes sources from workflow data."""
        congregated = translation_data.get("congregated_output", {})

        sources = {
            "original_poem": "",
            "revised_translation": "",
            "revised_translation_notes": congregated.get("revised_translation_notes", ""),
            "editor_suggestions": congregated.get("editor_suggestions", ""),
            "initial_translation_notes": congregated.get("initial_translation_notes", ""),
        }

        # Extract original poem from input data
        input_data = translation_data.get("input", {})
        sources["original_poem"] = input_data.get("original_poem", "")

        # Extract revised translation from revised translation data
        revised = translation_data.get("revised_translation", {})
        sources["revised_translation"] = revised.get("revised_translation", "")

        # Fallback to top-level fields if congregated_output is not available
        if not sources["revised_translation_notes"]:
            sources["revised_translation_notes"] = revised.get("revised_translation_notes", "")

        if not sources["editor_suggestions"]:
            editor = translation_data.get("editor_review", {})
            sources["editor_suggestions"] = editor.get("editor_suggestions", "")

        if not sources["initial_translation_notes"]:
            initial = translation_data.get("initial_translation", {})
            sources["initial_translation_notes"] = initial.get("initial_translation_notes", "")

        return sources

    def _get_prompt_file(self, workflow_mode: str) -> str:
        """Get appropriate prompt file based on workflow mode."""
        if workflow_mode in ["reasoning", "hybrid"]:
            return "wechat_article_notes_reasoning.yaml"
        else:
            return "wechat_article_notes_nonreasoning.yaml"

    def _format_prompt_fallback(self, prompt_template: Dict[str, str], sources: Dict[str, str]) -> str:
        """Fallback method to format prompt template using Python string formatting."""
        try:
            # Extract user prompt
            user_prompt = prompt_template.get("user", "")

            # Format user prompt with sources using Python string formatting
            formatted_user_prompt = user_prompt.format(**sources)

            return formatted_user_prompt

        except KeyError as e:
            raise TranslationNotesSynthesizerError(f"Missing required template variable: {e}")
        except Exception as e:
            raise TranslationNotesSynthesizerError(f"Error formatting prompt: {e}")

    async def _generate_with_llm(self, prompt: str, workflow_mode: str) -> str:
        """Generate translation notes using LLM."""
        try:
            # Get parameters from system config or use defaults
            translation_notes_config = self.system_config.get("system", {}).get("translation_notes", {})

            if workflow_mode in ["reasoning", "hybrid"]:
                config = translation_notes_config.get("reasoning", {})
                temperature = config.get("temperature", 0.1)
                max_tokens = config.get("max_tokens", 2000)
                timeout = config.get("timeout", 60)
            else:
                config = translation_notes_config.get("non_reasoning", {})
                temperature = config.get("temperature", 0.3)
                max_tokens = config.get("max_tokens", 1500)
                timeout = config.get("timeout", 45)

            # Generate response
            messages = [{"role": "user", "content": prompt}]
            response = await self._llm_provider.generate(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )

            return response

        except Exception as e:
            raise TranslationNotesSynthesizerError(f"LLM generation failed: {e}")

    def _parse_xml_response(self, response: str) -> TranslationNotes:
        """
        Parse XML response from LLM to extract translation notes.

        Args:
            response: LLM response containing XML

        Returns:
            TranslationNotes with digest and bullet points

        Raises:
            TranslationNotesSynthesizerError: If parsing fails
        """
        try:
            # Clean response text
            cleaned_response = response.strip()

            # Find XML content
            xml_start = cleaned_response.find("<wechat_translation_notes>")
            xml_end = cleaned_response.find("</wechat_translation_notes>")

            if xml_start == -1 or xml_end == -1:
                raise TranslationNotesSynthesizerError("No valid XML found in LLM response")

            xml_content = cleaned_response[xml_start : xml_end + len("</wechat_translation_notes>")]

            # Parse XML
            root = ET.fromstring(xml_content)

            # Extract digest
            digest_elem = root.find("digest")
            if digest_elem is None or digest_elem.text is None:
                raise TranslationNotesSynthesizerError("Missing digest in XML response")

            digest = digest_elem.text.strip()

            # Extract notes
            notes_elem = root.find("notes")
            if notes_elem is None:
                raise TranslationNotesSynthesizerError("Missing notes in XML response")

            # Parse bullet points
            notes_text = notes_elem.text or ""
            bullet_points = []

            for line in notes_text.split("\n"):
                line = line.strip()
                if line.startswith("•"):
                    bullet_point = line[1:].strip()  # Remove bullet and trim
                    if bullet_point:
                        bullet_points.append(bullet_point)

            if not bullet_points:
                raise TranslationNotesSynthesizerError("No bullet points found in XML response")

            # Validate and create TranslationNotes
            translation_notes = TranslationNotes(digest=digest, notes=bullet_points)

            logger.info(f"Parsed {len(bullet_points)} translation notes from XML response")
            return translation_notes

        except ET.ParseError as e:
            raise TranslationNotesSynthesizerError(f"XML parsing failed: {e}")
        except Exception as e:
            raise TranslationNotesSynthesizerError(f"Error parsing XML response: {e}")

    async def synthesize_with_fallback(
        self,
        translation_data: Dict[str, Any],
        workflow_mode: str = "hybrid",
        fallback_config: Optional[Dict[str, Any]] = None,
    ) -> TranslationNotes:
        """
        Synthesize translation notes with fallback provider if primary fails.

        Args:
            translation_data: Translation workflow JSON data
            workflow_mode: Workflow mode (reasoning, non_reasoning, hybrid)
            fallback_config: Fallback LLM provider configuration

        Returns:
            TranslationNotes with digest and bullet points

        Raises:
            TranslationNotesSynthesizerError: If all attempts fail
        """
        try:
            # Try primary provider first
            return await self.synthesize_notes(translation_data, workflow_mode)

        except Exception as primary_error:
            logger.warning(f"Primary LLM provider failed: {primary_error}")

            if fallback_config:
                try:
                    logger.info("Attempting synthesis with fallback provider")

                    # Create fallback provider
                    fallback_provider = LLMFactory.create_provider(
                        provider_type=fallback_config.get("type", "tongyi"),
                        config=fallback_config,
                    )

                    # Use fallback to generate notes
                    notes_sources = self._extract_notes_sources(translation_data)
                    prompt_file = self._get_prompt_file(workflow_mode)
                    prompt_template = self.prompt_service.get_template(prompt_file)
                    formatted_prompt = self._format_prompt_fallback(prompt_template, notes_sources)

                    # Configure fallback parameters
                    temperature = 0.3
                    max_tokens = 1500
                    timeout = 45

                    messages = [{"role": "user", "content": formatted_prompt}]
                    response = await fallback_provider.generate(
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=timeout,
                    )

                    # Parse response
                    translation_notes = self._parse_xml_response(response)
                    logger.info("Successfully synthesized notes with fallback provider")
                    return translation_notes

                except Exception as fallback_error:
                    logger.error(f"Fallback provider also failed: {fallback_error}")
                    raise TranslationNotesSynthesizerError(
                        f"Both primary and fallback providers failed. "
                        f"Primary: {primary_error}. Fallback: {fallback_error}"
                    )
            else:
                # No fallback available
                raise primary_error

    async def close(self) -> None:
        """Close LLM provider if available."""
        if self._llm_provider and hasattr(self._llm_provider, "close"):
            try:
                await self._llm_provider.close()
                logger.info("Translation notes synthesizer closed")
            except Exception as e:
                logger.warning(f"Error closing synthesizer: {e}")
