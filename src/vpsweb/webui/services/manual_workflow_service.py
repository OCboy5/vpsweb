"""
Manual Workflow Service for VPSWeb.

This module provides a service for managing manual translation workflows
where users interact with external LLM services through copy-paste operations.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from vpsweb.repository.service import RepositoryWebService
from vpsweb.services.parser import OutputParser
from vpsweb.services.prompts import PromptService
from vpsweb.utils.storage import StorageHandler
from vpsweb.webui.services.interfaces import IWorkflowServiceV2

logger = logging.getLogger(__name__)


class ManualWorkflowService:
    """
    Service for managing manual translation workflows.

    This service handles session-based workflow execution where users
    manually interact with external LLM services and paste responses back.
    """

    def __init__(
        self,
        prompt_service: PromptService,
        output_parser: OutputParser,
        workflow_service: IWorkflowServiceV2,
        repository_service: RepositoryWebService,
        storage_handler: StorageHandler,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the manual workflow service."""
        self.prompt_service = prompt_service
        self.output_parser = output_parser
        self.workflow_service = workflow_service
        self.repository_service = repository_service
        self.storage_handler = storage_handler
        self.logger = logger or logging.getLogger(__name__)
        self.sessions: Dict[str, Dict[str, Any]] = {}

    async def start_session(self, poem_id: str, target_lang: str) -> Dict[str, Any]:
        """
        Initialize a new manual workflow session.

        Args:
            poem_id: ID of the poem to translate
            target_lang: Target language for translation

        Returns:
            Session data with first step prompt
        """
        try:
            # Generate session ID
            session_id = str(uuid.uuid4())

            # Validate poem exists
            poem = self.repository_service.repo.poems.get_by_id(poem_id)
            if not poem:
                raise ValueError(f"Poem not found: {poem_id}")

            source_lang = poem.source_language

            # Get BBR if available
            bbr_content = ""
            try:
                bbr = self.repository_service.repo.background_briefing_reports.get_by_poem(
                    poem_id
                )
                if bbr:
                    bbr_content = bbr.content
                    self.logger.info(
                        f"Found existing BBR for poem {poem_id} (content length: {len(bbr_content)} chars)"
                    )
            except Exception as e:
                self.logger.warning(f"Failed to retrieve BBR for poem {poem_id}: {e}")

            # Define workflow steps (same as hybrid mode)
            step_sequence = [
                "initial_translation_nonreasoning",
                "editor_review_reasoning",
                "translator_revision_nonreasoning",
            ]

            # Create session
            session = {
                "session_id": session_id,
                "poem_id": poem_id,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "current_step_index": 0,
                "step_sequence": step_sequence,
                "completed_steps": {},
                "bbr_content": bbr_content,  # Store BBR in session
                "created_at": datetime.now(timezone.utc),
            }

            self.sessions[session_id] = session

            # Get first step prompt
            current_step = step_sequence[0]
            prompt = await self._get_step_prompt(
                step_name=current_step,
                poem=poem,
                source_lang=source_lang,
                target_lang=target_lang,
                previous_results=None,
                bbr_content=bbr_content,
            )

            self.logger.info(
                f"Started manual workflow session {session_id} for poem {poem_id}"
            )

            return {
                "session_id": session_id,
                "step_name": current_step,
                "step_index": 0,
                "total_steps": len(step_sequence),
                "prompt": prompt,
                "poem_title": poem.poem_title,
                "poet_name": poem.poet_name,
            }

        except Exception as e:
            self.logger.error(f"Error starting manual workflow session: {e}")
            raise

    async def submit_step(
        self,
        session_id: str,
        step_name: str,
        llm_response: str,
        model_name: str,
    ) -> Dict[str, Any]:
        """
        Process user-submitted step response.

        Args:
            session_id: Manual workflow session ID
            step_name: Name of the current step
            llm_response: Response from external LLM
            model_name: Name of the LLM model used

        Returns:
            Next step data or completion status
        """
        try:
            # Validate session exists
            if session_id not in self.sessions:
                raise ValueError(f"Session not found: {session_id}")

            session = self.sessions[session_id]
            current_step_index = session["current_step_index"]
            step_sequence = session["step_sequence"]

            # Validate step name matches current step
            expected_step = step_sequence[current_step_index]
            if step_name != expected_step:
                raise ValueError(
                    f"Step mismatch: expected {expected_step}, got {step_name}"
                )

            # Parse the LLM response
            try:
                parsed_data = self.output_parser.parse_xml(llm_response)
            except Exception as e:
                raise ValueError(f"Failed to parse LLM response: {str(e)}")

            # Store step result
            step_result = {
                "step_name": step_name,
                "llm_response": llm_response,
                "model_name": model_name,
                "parsed_data": parsed_data,
                "timestamp": datetime.now(timezone.utc),
            }
            session["completed_steps"][step_name] = step_result

            # Check if this was the last step
            if current_step_index == len(step_sequence) - 1:
                # Workflow completed - save to database
                await self._complete_workflow(session_id)
                return {
                    "status": "completed",
                    "message": "Manual workflow completed successfully",
                }
            else:
                # Move to next step
                session["current_step_index"] += 1
                next_step_index = session["current_step_index"]
                next_step = step_sequence[next_step_index]

                # Get poem for next step prompt
                poem = self.repository_service.repo.poems.get_by_id(session["poem_id"])

                # Get previous results for context
                previous_results = {
                    k: v["parsed_data"] for k, v in session["completed_steps"].items()
                }

                # Generate next step prompt
                next_prompt = await self._get_step_prompt(
                    step_name=next_step,
                    poem=poem,
                    source_lang=session["source_lang"],
                    target_lang=session["target_lang"],
                    previous_results=previous_results,
                    bbr_content=session.get("bbr_content", ""),
                )

                return {
                    "status": "continue",
                    "step_name": next_step,
                    "step_index": next_step_index,
                    "total_steps": len(step_sequence),
                    "prompt": next_prompt,
                }

        except Exception as e:
            self.logger.error(f"Error submitting manual workflow step: {e}")
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current session state."""
        return self.sessions.get(session_id)

    async def _get_step_prompt(
        self,
        step_name: str,
        poem: Any,
        source_lang: str,
        target_lang: str,
        previous_results: Optional[Dict[str, Any]] = None,
        bbr_content: Optional[str] = None,
    ) -> str:
        """Generate prompt for a specific step."""
        try:
            # Map step names to template names (filenames without .yaml)
            template_map = {
                "initial_translation_nonreasoning": "initial_translation_nonreasoning",
                "editor_review_reasoning": "editor_review_reasoning",
                "translator_revision_nonreasoning": "translator_revision_nonreasoning",
            }

            template_name = template_map.get(step_name)
            if not template_name:
                raise ValueError(f"Unknown step: {step_name}")

            # Prepare template variables
            template_vars = {
                "poem_title": poem.poem_title,
                "poet_name": poem.poet_name,
                "original_poem": poem.original_text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "source_language": source_lang,
                "target_language": target_lang,
                # Additional required variables with defaults
                "adaptation_level": "medium",
                "additions_policy": "minimal",
                "background_briefing_report": bbr_content or "",
                "prosody_target": "preserve_rhythm_and_meter",
                "repetition_policy": "preserve_meaningful_repetition",
                "current_step": step_name.replace("_", " ").title(),
            }

            # Add previous results for context
            if previous_results:
                if "initial_translation_nonreasoning" in previous_results:
                    data = previous_results["initial_translation_nonreasoning"]
                    template_vars["initial_translation"] = data.get(
                        "initial_translation", ""
                    )
                    template_vars["initial_translation_notes"] = data.get(
                        "initial_translation_notes", ""
                    )
                    template_vars["translated_poem_title"] = data.get(
                        "translated_poem_title", ""
                    )
                    template_vars["translated_poet_name"] = data.get(
                        "translated_poet_name", ""
                    )
                if "editor_review_reasoning" in previous_results:
                    data = previous_results["editor_review_reasoning"]
                    template_vars["editor_suggestions"] = data.get(
                        "editor_suggestions", ""
                    )

            # Render prompt (returns system_prompt, user_prompt)
            system_prompt, user_prompt = self.prompt_service.render_prompt(
                template_name, template_vars
            )

            # Combine system and user prompts for manual workflow
            prompt = f"=== SYSTEM PROMPT ===\n{system_prompt}\n\n=== USER PROMPT ===\n{user_prompt}"
            return prompt

        except Exception as e:
            self.logger.error(f"Error generating step prompt: {e}")
            raise

    async def _complete_workflow(self, session_id: str) -> str:
        """
        Save completed workflow to database using existing WorkflowServiceV2.

        Args:
            session_id: ID of the completed session

        Returns:
            Translation ID
        """
        try:
            session = self.sessions[session_id]
            poem_id = session["poem_id"]
            target_lang = session["target_lang"]
            completed_steps = session["completed_steps"]

            # Get poem
            poem = self.repository_service.repo.poems.get_by_id(poem_id)

            # Create a mock result object that matches the expected structure
            # This simulates the output from an automated workflow
            from ...models.translation import (
                EditorReview,
                InitialTranslation,
                Language,
                RevisedTranslation,
                TranslationInput,
                TranslationOutput,
            )

            # Extract data from completed steps
            initial_data = completed_steps["initial_translation_nonreasoning"][
                "parsed_data"
            ]
            editor_data = completed_steps["editor_review_reasoning"]["parsed_data"]
            revision_data = completed_steps["translator_revision_nonreasoning"][
                "parsed_data"
            ]

            # Create InitialTranslation from parsed XML data
            initial_translation = InitialTranslation(
                initial_translation=initial_data.get("initial_translation", ""),
                initial_translation_notes=initial_data.get(
                    "initial_translation_notes", ""
                ),
                translated_poem_title=initial_data.get("translated_poem_title", ""),
                translated_poet_name=initial_data.get("translated_poet_name", ""),
                model_info={
                    "provider": "manual",
                    "model": completed_steps["initial_translation_nonreasoning"][
                        "model_name"
                    ],
                    "temperature": "0.7",
                    "max_tokens": "4000",
                },
                tokens_used=0,  # Not tracked for manual
                cost=0.0,  # Not tracked for manual
            )

            editor_review = EditorReview(
                editor_suggestions=editor_data.get("editor_suggestions", ""),
                model_info={
                    "provider": "manual",
                    "model": completed_steps["editor_review_reasoning"]["model_name"],
                    "temperature": "0.5",
                    "max_tokens": "2000",
                },
                tokens_used=0,  # Not tracked for manual
                cost=0.0,  # Not tracked for manual
            )

            revised_translation = RevisedTranslation(
                revised_translation=revision_data.get("revised_translation", ""),
                revised_translation_notes=revision_data.get(
                    "revised_translation_notes", ""
                ),
                refined_translated_poem_title=revision_data.get(
                    "refined_translated_poem_title", ""
                ),
                refined_translated_poet_name=revision_data.get(
                    "refined_translated_poet_name", ""
                ),
                model_info={
                    "provider": "manual",
                    "model": completed_steps["translator_revision_nonreasoning"][
                        "model_name"
                    ],
                    "temperature": "0.7",
                    "max_tokens": "4000",
                },
                tokens_used=0,  # Not tracked for manual
                cost=0.0,  # Not tracked for manual
            )

            # Create translation input
            # Use standard language code mapping from automatic workflow
            from vpsweb.models.translation import LANGUAGE_CODE_MAP
            from vpsweb.utils.language_mapper import LanguageMapper

            # Get proper language codes using the same pattern as automatic workflow
            language_mapper = LanguageMapper()

            # Convert source language to proper code
            source_lang_code = (
                language_mapper.get_language_code(session["source_lang"])
                or session["source_lang"]
            )
            # Normalize the code
            source_lang_code = language_mapper.normalize_code(source_lang_code)

            # Convert target language to proper code and enum
            target_lang_code = (
                language_mapper.get_language_code(target_lang) or target_lang
            )
            # Normalize the code
            target_lang_code = language_mapper.normalize_code(target_lang_code)

            # Convert to Language enums using LANGUAGE_CODE_MAP
            source_lang_enum = LANGUAGE_CODE_MAP.get(source_lang_code, Language.ENGLISH)
            target_lang_enum = LANGUAGE_CODE_MAP.get(target_lang_code, Language.CHINESE)

            # Validate that source and target languages are different
            if source_lang_enum == target_lang_enum:
                raise ValueError(
                    f"Source and target languages must be different. "
                    f"Both cannot be '{source_lang_enum.value}'. Please select different languages."
                )

            translation_input = TranslationInput(
                original_poem=poem.original_text,
                source_lang=source_lang_enum,
                target_lang=target_lang_enum,
                metadata={
                    "title": poem.poem_title,
                    "author": poem.poet_name,
                    "poem_id": poem_id,
                },
            )

            # Create translation output
            translation_output = TranslationOutput(
                workflow_id=session_id,
                input=translation_input,
                initial_translation=initial_translation,
                editor_review=editor_review,
                revised_translation=revised_translation,
                total_tokens=0,  # Not tracked for manual
                duration_seconds=0,  # Not tracked for manual
                workflow_mode="manual",
                total_cost=0.0,  # Not tracked for manual
            )

            # Save using existing workflow service method
            await self.workflow_service._persist_workflow_result(
                poem_id=poem_id,
                result=translation_output,
                workflow_mode="manual",
                input_data=translation_input,
            )

            # Clean up session
            del self.sessions[session_id]

            self.logger.info(f"Completed manual workflow session {session_id}")

            return session_id

        except Exception as e:
            self.logger.error(f"Error completing manual workflow: {e}")
            raise

    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up expired sessions."""
        from datetime import timedelta

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        expired_sessions = []

        for session_id, session in self.sessions.items():
            if session["created_at"] < cutoff_time:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.sessions[session_id]

        if expired_sessions:
            self.logger.info(
                f"Cleaned up {len(expired_sessions)} expired manual workflow sessions"
            )

        return len(expired_sessions)
