"""
Workflow Orchestrator for Vox Poetica Studio Web.

This module implements the main Translation→Editor→Translation workflow orchestrator
that coordinates the complete poetry translation process following the vpts.yml specification.
"""

import time
import logging
import uuid
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime

from ..services.llm.factory import LLMFactory
from ..services.prompts import PromptService
from ..core.executor import StepExecutor
from ..models.config import WorkflowConfig, WorkflowMode
from ..models.translation import (
    TranslationInput,
    InitialTranslation,
    EditorReview,
    RevisedTranslation,
    TranslationOutput,
)
from ..services.parser import OutputParser
from ..utils.progress import ProgressTracker, StepStatus

logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """Base exception for workflow execution errors."""

    pass


class StepExecutionError(WorkflowError):
    """Raised when a specific workflow step fails."""

    pass


class ConfigurationError(WorkflowError):
    """Raised when workflow configuration is invalid."""

    pass


class TranslationWorkflow:
    """
    Main orchestrator for the T-E-T translation workflow.

    This class coordinates the complete translation workflow:
    1. Initial Translation
    2. Editor Review
    3. Translator Revision
    """

    def __init__(
        self,
        config: WorkflowConfig,
        providers_config,
        workflow_mode: WorkflowMode = WorkflowMode.HYBRID,
        system_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the translation workflow.

        Args:
            config: Workflow configuration with step configurations
            providers_config: Provider configurations for LLM factory
            workflow_mode: Workflow mode to use (reasoning, non_reasoning, hybrid)
            system_config: System configuration with preview lengths and other settings
        """
        self.config = config
        self.workflow_mode = workflow_mode
        self.system_config = system_config or {}

        # Initialize services
        self.llm_factory = LLMFactory(providers_config)
        self.prompt_service = PromptService()
        self.step_executor = StepExecutor(self.llm_factory, self.prompt_service)

        # Initialize progress callback (optional)
        self.progress_callback: Optional[
            Callable[[str, Dict[str, Any]], Awaitable[None]]
        ] = None

        # Get the appropriate workflow steps for the mode
        self.workflow_steps = config.get_workflow_steps(workflow_mode)

        logger.info(f"Initialized TranslationWorkflow: {config.name} v{config.version}")
        logger.info(f"Workflow mode: {workflow_mode.value}")
        logger.info(f"Available steps: {list(self.workflow_steps.keys())}")

    async def execute(
        self, input_data: TranslationInput, show_progress: bool = True
    ) -> TranslationOutput:
        """
        Execute complete translation workflow.

        Args:
            input_data: Translation input with poem and language information
            show_progress: Whether to display progress updates

        Returns:
            Complete translation output with all intermediate results

        Raises:
            WorkflowError: If workflow execution fails
        """
        workflow_id = str(uuid.uuid4())
        start_time = time.time()
        log_entries = []

        logger.info(f"Starting translation workflow {workflow_id}")
        logger.info(f"Translation: {input_data.source_lang} → {input_data.target_lang}")
        logger.info(f"Poem length: {len(input_data.original_poem)} characters")

        # Initialize progress tracker
        progress_tracker: Optional[ProgressTracker] = None
        if show_progress:
            progress_tracker = ProgressTracker(
                ["initial_translation", "editor_review", "translator_revision"]
            )

        try:
            # Step 1: Initial Translation
            log_entries.append(
                f"=== STEP 1: INITIAL TRANSLATION ({self.workflow_mode.value.upper()} MODE) ==="
            )
            # Get input preview length from config
            input_preview_length = (
                self.system_config.get("system", {})
                .get("preview_lengths", {})
                .get("input_preview", 100)
            )
            log_entries.append(
                f"Input: {input_data.original_poem[:input_preview_length]}..."
            )

            if progress_tracker:
                step_config = self.workflow_steps["initial_translation"]
                model_info = {
                    "provider": step_config.provider,
                    "model": step_config.model,
                    "temperature": str(step_config.temperature),
                }
                progress_tracker.start_step("initial_translation", model_info)

            # Call progress callback when Step 1 starts
            if self.progress_callback:
                await self.progress_callback(
                    "Initial Translation",
                    {"status": "started", "message": "Starting initial translation..."},
                )

            step_start_time = time.time()
            initial_translation = await self._initial_translation(input_data)
            step_duration = time.time() - step_start_time
            initial_translation.duration = step_duration

            # Calculate cost for this step
            step_config = self.workflow_steps["initial_translation"]
            # Use actual token counts from API response
            input_tokens = getattr(initial_translation, "prompt_tokens", 0) or 0
            output_tokens = getattr(initial_translation, "completion_tokens", 0) or 0
            initial_translation.cost = self._calculate_step_cost(
                step_config.provider, step_config.model, input_tokens, output_tokens
            )
            log_entries.append(
                f"Initial translation completed: {initial_translation.tokens_used} tokens"
            )
            # Get response preview length from config
            response_preview_length = (
                self.system_config.get("system", {})
                .get("preview_lengths", {})
                .get("response_preview", 100)
            )
            log_entries.append(
                f"Translation: {initial_translation.initial_translation[:response_preview_length]}..."
            )

            if progress_tracker:
                progress_tracker.complete_step(
                    "initial_translation",
                    {
                        "original_poem": input_data.original_poem,
                        "initial_translation": initial_translation.initial_translation,
                        "initial_translation_notes": initial_translation.initial_translation_notes,
                        "tokens_used": initial_translation.tokens_used,
                        "prompt_tokens": getattr(
                            initial_translation, "prompt_tokens", None
                        ),
                        "completion_tokens": getattr(
                            initial_translation, "completion_tokens", None
                        ),
                        "duration": getattr(initial_translation, "duration", None),
                        "cost": getattr(initial_translation, "cost", None),
                        "workflow_mode": self.workflow_mode.value,
                        "model_info": initial_translation.model_info,
                    },
                )

            # Call progress callback after Step 1 completion
            if self.progress_callback:
                await self.progress_callback(
                    "Initial Translation",
                    {
                        "status": "completed",
                        "tokens_used": initial_translation.tokens_used,
                        "duration": getattr(initial_translation, "duration", None),
                        "cost": getattr(initial_translation, "cost", None),
                        "model_info": getattr(initial_translation, "model_info", None),
                    },
                )

            # Step 2: Editor Review
            log_entries.append(
                f"\n=== STEP 2: EDITOR REVIEW ({self.workflow_mode.value.upper()} MODE) ==="
            )

            logger.info(
                f"Starting editor review with {initial_translation.tokens_used} tokens from initial translation"
            )

            if progress_tracker:
                step_config = self.workflow_steps["editor_review"]
                model_info = {
                    "provider": step_config.provider,
                    "model": step_config.model,
                    "temperature": str(step_config.temperature),
                }
                progress_tracker.start_step("editor_review", model_info)

            # Call progress callback when Step 2 starts
            if self.progress_callback:
                await self.progress_callback(
                    "Editor Review",
                    {"status": "started", "message": "Starting editor review..."},
                )

            step_start_time = time.time()
            editor_review = await self._editor_review(input_data, initial_translation)
            step_duration = time.time() - step_start_time
            editor_review.duration = step_duration

            # Calculate cost for this step
            step_config = self.workflow_steps["editor_review"]
            # Use actual token counts from API response
            input_tokens = getattr(editor_review, "prompt_tokens", 0) or 0
            output_tokens = getattr(editor_review, "completion_tokens", 0) or 0
            editor_review.cost = self._calculate_step_cost(
                step_config.provider, step_config.model, input_tokens, output_tokens
            )
            logger.info(f"Editor review step completed successfully")
            log_entries.append(
                f"Editor review completed: {editor_review.tokens_used} tokens"
            )
            log_entries.append(
                f"Review length: {len(editor_review.editor_suggestions)} characters"
            )
            # Get editor preview length from config
            editor_preview_length = (
                self.system_config.get("system", {})
                .get("preview_lengths", {})
                .get("editor_preview", 200)
            )
            log_entries.append(
                f"Review preview: {editor_review.editor_suggestions[:editor_preview_length]}..."
            )

            if progress_tracker:
                progress_tracker.complete_step(
                    "editor_review",
                    {
                        "editor_suggestions": editor_review.editor_suggestions,
                        "tokens_used": editor_review.tokens_used,
                        "prompt_tokens": getattr(editor_review, "prompt_tokens", None),
                        "completion_tokens": getattr(
                            editor_review, "completion_tokens", None
                        ),
                        "duration": getattr(editor_review, "duration", None),
                        "cost": getattr(editor_review, "cost", None),
                        "workflow_mode": self.workflow_mode.value,
                        "model_info": editor_review.model_info,
                    },
                )

            # Call progress callback after Step 2 completion
            if self.progress_callback:
                await self.progress_callback(
                    "Editor Review",
                    {
                        "status": "completed",
                        "tokens_used": editor_review.tokens_used,
                        "duration": getattr(editor_review, "duration", None),
                        "cost": getattr(editor_review, "cost", None),
                        "model_info": getattr(editor_review, "model_info", None),
                    },
                )

            # Step 3: Translator Revision
            log_entries.append(
                f"\n=== STEP 3: TRANSLATOR REVISION ({self.workflow_mode.value.upper()} MODE) ==="
            )

            if progress_tracker:
                step_config = self.workflow_steps["translator_revision"]
                model_info = {
                    "provider": step_config.provider,
                    "model": step_config.model,
                    "temperature": str(step_config.temperature),
                }
                progress_tracker.start_step("translator_revision", model_info)

            # Call progress callback when Step 3 starts
            if self.progress_callback:
                await self.progress_callback(
                    "Translator Revision",
                    {"status": "started", "message": "Starting translator revision..."},
                )

            step_start_time = time.time()
            revised_translation = await self._translator_revision(
                input_data, initial_translation, editor_review
            )
            step_duration = time.time() - step_start_time
            revised_translation.duration = step_duration

            # Calculate cost for this step
            step_config = self.workflow_steps["translator_revision"]
            # Use actual token counts from API response
            input_tokens = getattr(revised_translation, "prompt_tokens", 0) or 0
            output_tokens = getattr(revised_translation, "completion_tokens", 0) or 0
            revised_translation.cost = self._calculate_step_cost(
                step_config.provider, step_config.model, input_tokens, output_tokens
            )
            log_entries.append(
                f"Translator revision completed: {revised_translation.tokens_used} tokens"
            )
            log_entries.append(
                f"Revised translation length: {len(revised_translation.revised_translation)} characters"
            )

            if progress_tracker:
                progress_tracker.complete_step(
                    "translator_revision",
                    {
                        "revised_translation": revised_translation.revised_translation,
                        "revised_translation_notes": revised_translation.revised_translation_notes,
                        "tokens_used": revised_translation.tokens_used,
                        "prompt_tokens": getattr(
                            revised_translation, "prompt_tokens", None
                        ),
                        "completion_tokens": getattr(
                            revised_translation, "completion_tokens", None
                        ),
                        "duration": getattr(revised_translation, "duration", None),
                        "cost": getattr(revised_translation, "cost", None),
                        "workflow_mode": self.workflow_mode.value,
                        "model_info": revised_translation.model_info,
                    },
                )

            # Call progress callback after Step 3 completion
            if self.progress_callback:
                await self.progress_callback(
                    "Translator Revision",
                    {
                        "status": "completed",
                        "tokens_used": revised_translation.tokens_used,
                        "duration": getattr(revised_translation, "duration", None),
                        "cost": getattr(revised_translation, "cost", None),
                        "model_info": getattr(revised_translation, "model_info", None),
                    },
                )

            # Calculate total cost
            total_cost = self._calculate_total_cost(
                initial_translation, editor_review, revised_translation
            )

            # Aggregate results
            duration = time.time() - start_time
            total_tokens = (
                initial_translation.tokens_used
                + editor_review.tokens_used
                + revised_translation.tokens_used
            )

            logger.info(
                f"Workflow {workflow_id} completed successfully in {duration:.2f}s"
            )
            logger.info(f"Total tokens used: {total_tokens}")

            # Calculate total cost
            total_cost = self._calculate_total_cost(
                initial_translation, editor_review, revised_translation
            )

            return self._aggregate_output(
                workflow_id=workflow_id,
                input_data=input_data,
                initial_translation=initial_translation,
                editor_review=editor_review,
                revised_translation=revised_translation,
                log_entries=log_entries,
                total_tokens=total_tokens,
                duration=duration,
                total_cost=total_cost,
            )

        except Exception as e:
            # Call progress callback on workflow failure
            if self.progress_callback:
                # Try to determine which step failed
                failed_step = "Unknown"
                if progress_tracker:
                    for step_name in reversed(progress_tracker.step_order):
                        step = progress_tracker.steps[step_name]
                        if step.status == StepStatus.IN_PROGRESS:
                            failed_step = step_name.replace("_", " ").title()
                            break

                await self.progress_callback(
                    failed_step, {"status": "failed", "error": str(e)}
                )

            if progress_tracker:
                # Determine which step failed based on current progress
                for step_name in reversed(progress_tracker.step_order):
                    step = progress_tracker.steps[step_name]
                    if step.status == StepStatus.IN_PROGRESS:
                        progress_tracker.fail_step(step_name, str(e))
                        break

            logger.error(f"Workflow {workflow_id} failed: {e}")
            raise WorkflowError(f"Translation workflow failed: {e}")

    async def _initial_translation(
        self, input_data: TranslationInput
    ) -> InitialTranslation:
        """
        Execute initial translation step.

        Args:
            input_data: Translation input data

        Returns:
            Initial translation with notes

        Raises:
            StepExecutionError: If translation step fails
        """
        try:
            step_config = self.workflow_steps["initial_translation"]

            # Prepare input context
            input_context = {
                "original_poem": input_data.original_poem,
                "source_lang": input_data.source_lang,
                "target_lang": input_data.target_lang,
            }

            # Execute step
            result = await self.step_executor.execute_initial_translation(
                input_data, step_config
            )

            # Extract translation and notes from XML
            if "output" in result:
                output_data = result["output"]
                translation = output_data.get("initial_translation", "")
                notes = output_data.get("initial_translation_notes", "")
                translated_poem_title = output_data.get("translated_poem_title", "")
                translated_poet_name = output_data.get("translated_poet_name", "")
            else:
                # Fallback: try to extract from raw response
                raw_content = (
                    result.get("metadata", {})
                    .get("raw_response", {})
                    .get("content_preview", "")
                )
                extracted = OutputParser.parse_initial_translation_xml(raw_content)
                translation = extracted.get("initial_translation", "")
                notes = extracted.get("initial_translation_notes", "")
                translated_poem_title = extracted.get("translated_poem_title", "")
                translated_poet_name = extracted.get("translated_poet_name", "")

            # Create InitialTranslation model
            usage = result.get("metadata", {}).get("usage", {})
            return InitialTranslation(
                initial_translation=translation,
                initial_translation_notes=notes,
                translated_poem_title=translated_poem_title,
                translated_poet_name=translated_poet_name,
                model_info={
                    "provider": step_config.provider,
                    "model": step_config.model,
                    "temperature": str(step_config.temperature),
                },
                tokens_used=usage.get("tokens_used", 0),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
            )

        except Exception as e:
            logger.error(f"Initial translation step failed: {e}")
            raise StepExecutionError(f"Initial translation failed: {e}")

    async def _editor_review(
        self, input_data: TranslationInput, initial_translation: InitialTranslation
    ) -> EditorReview:
        """
        Execute editor review step.

        Args:
            input_data: Original translation input
            initial_translation: Initial translation to review

        Returns:
            Editor review with suggestions

        Raises:
            StepExecutionError: If review step fails
        """
        try:
            step_config = self.workflow_steps["editor_review"]

            # Execute step
            result = await self.step_executor.execute_editor_review(
                initial_translation, input_data, step_config
            )

            # Extract editor text from result
            editor_suggestions = ""
            if "output" in result:
                output_data = result["output"]
                # Try different possible field names
                editor_suggestions = output_data.get("editor_suggestions", "")

            if not editor_suggestions:
                # Fallback: use content directly
                editor_suggestions = (
                    result.get("metadata", {})
                    .get("raw_response", {})
                    .get("content_preview", "")
                )

            # Create EditorReview model
            usage = result.get("metadata", {}).get("usage", {})
            return EditorReview(
                editor_suggestions=editor_suggestions,
                model_info={
                    "provider": step_config.provider,
                    "model": step_config.model,
                    "temperature": str(step_config.temperature),
                },
                tokens_used=usage.get("tokens_used", 0),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
            )

        except Exception as e:
            logger.error(f"Editor review step failed: {e}")
            raise StepExecutionError(f"Editor review failed: {e}")

    async def _translator_revision(
        self,
        input_data: TranslationInput,
        initial_translation: InitialTranslation,
        editor_review: EditorReview,
    ) -> RevisedTranslation:
        """
        Execute translator revision step.

        Args:
            input_data: Original translation input
            initial_translation: Initial translation
            editor_review: Editor review with suggestions

        Returns:
            Revised translation with notes

        Raises:
            StepExecutionError: If revision step fails
        """
        try:
            step_config = self.workflow_steps["translator_revision"]

            # Execute step
            result = await self.step_executor.execute_translator_revision(
                editor_review, input_data, initial_translation, step_config
            )

            # Extract revised translation and notes from XML
            if "output" in result:
                output_data = result["output"]
                translation = output_data.get("revised_translation", "")
                notes = output_data.get("revised_translation_notes", "")
                refined_translated_poem_title = output_data.get(
                    "refined_translated_poem_title", ""
                )
                refined_translated_poet_name = output_data.get(
                    "refined_translated_poet_name", ""
                )
            else:
                # Fallback: try to extract from raw response
                raw_content = (
                    result.get("metadata", {})
                    .get("raw_response", {})
                    .get("content_preview", "")
                )
                extracted = OutputParser.parse_revised_translation_xml(raw_content)
                translation = extracted.get("revised_translation", "")
                notes = extracted.get("revised_translation_notes", "")
                refined_translated_poem_title = extracted.get(
                    "refined_translated_poem_title", ""
                )
                refined_translated_poet_name = extracted.get(
                    "refined_translated_poet_name", ""
                )

            # Create RevisedTranslation model
            usage = result.get("metadata", {}).get("usage", {})
            return RevisedTranslation(
                revised_translation=translation,
                revised_translation_notes=notes,
                refined_translated_poem_title=refined_translated_poem_title,
                refined_translated_poet_name=refined_translated_poet_name,
                model_info={
                    "provider": step_config.provider,
                    "model": step_config.model,
                    "temperature": str(step_config.temperature),
                },
                tokens_used=usage.get("tokens_used", 0),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
            )

        except Exception as e:
            logger.error(f"Translator revision step failed: {e}")
            raise StepExecutionError(f"Translator revision failed: {e}")

    def _aggregate_output(
        self,
        workflow_id: str,
        input_data: TranslationInput,
        initial_translation: InitialTranslation,
        editor_review: EditorReview,
        revised_translation: RevisedTranslation,
        log_entries: list,
        total_tokens: int,
        duration: float,
        total_cost: float,
    ) -> TranslationOutput:
        """
        Aggregate all workflow results into final output.

        Args:
            workflow_id: Unique workflow identifier
            input_data: Original input data
            initial_translation: Initial translation result
            editor_review: Editor review result
            revised_translation: Revised translation result
            log_entries: List of log entries
            total_tokens: Total tokens used
            duration: Total execution time

        Returns:
            Complete translation output
        """
        # Combine all log entries
        full_log = "\n".join(log_entries)

        # Add summary to log
        full_log += f"\n\n=== WORKFLOW SUMMARY ==="
        full_log += f"\nWorkflow ID: {workflow_id}"
        full_log += f"\nWorkflow Mode: {self.workflow_mode.value}"
        full_log += f"\nTotal tokens: {total_tokens}"
        full_log += f"\nDuration: {duration:.2f}s"
        full_log += f"\nCompleted: {datetime.now().isoformat()}"

        return TranslationOutput(
            workflow_id=workflow_id,
            input=input_data,
            initial_translation=initial_translation,
            editor_review=editor_review,
            revised_translation=revised_translation,
            total_tokens=total_tokens,
            duration_seconds=duration,
            workflow_mode=self.workflow_mode.value,
            total_cost=total_cost,
        )

    def _calculate_total_cost(
        self, initial_translation, editor_review, revised_translation
    ):
        """Calculate total cost of the workflow."""
        total_cost = 0.0

        # Calculate cost for each step if we have the pricing info
        for step_result in [initial_translation, editor_review, revised_translation]:
            if hasattr(step_result, "cost") and step_result.cost is not None:
                total_cost += step_result.cost

        return total_cost

    def _calculate_step_cost(
        self, provider: str, model: str, input_tokens: int, output_tokens: int
    ):
        """Calculate cost for a single step."""
        try:
            # Get pricing from configuration
            providers_config = self.llm_factory.providers_config

            if hasattr(providers_config, "pricing") and providers_config.pricing:
                pricing = providers_config.pricing

                # Get pricing for this provider and model
                if provider in pricing and model in pricing[provider]:
                    model_pricing = pricing[provider][model]
                    # Pricing is RMB per 1K tokens
                    input_cost = (input_tokens / 1000) * model_pricing.get("input", 0)
                    output_cost = (output_tokens / 1000) * model_pricing.get(
                        "output", 0
                    )
                    return input_cost + output_cost

            return 0.0
        except Exception as e:
            logger.warning(f"Failed to calculate cost for {provider}/{model}: {e}")
            return 0.0

    def __repr__(self) -> str:
        """String representation of the workflow."""
        return f"TranslationWorkflow(name='{self.config.name}', version='{self.config.version}')"
