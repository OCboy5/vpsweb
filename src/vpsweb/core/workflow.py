"""
Workflow Orchestrator for Vox Poetica Studio Web.

This module implements the main Translation→Editor→Translation workflow orchestrator
that coordinates the complete poetry translation process following the vpts.yml specification.
"""

import asyncio
import time
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from ..services.llm.factory import LLMFactory
from ..services.prompts import PromptService
from ..services.parser import OutputParser
from ..core.executor import StepExecutor
from ..models.config import WorkflowConfig, StepConfig
from ..models.translation import (
    TranslationInput,
    InitialTranslation,
    EditorReview,
    RevisedTranslation,
    TranslationOutput,
    extract_initial_translation_from_xml,
    extract_revised_translation_from_xml
)
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

    def __init__(self, config: WorkflowConfig, providers_config):
        """
        Initialize the translation workflow.

        Args:
            config: Workflow configuration with step configurations
            providers_config: Provider configurations for LLM factory
        """
        self.config = config

        # Initialize services
        self.llm_factory = LLMFactory(providers_config)
        self.prompt_service = PromptService()
        self.step_executor = StepExecutor(self.llm_factory, self.prompt_service)

        logger.info(f"Initialized TranslationWorkflow: {config.name} v{config.version}")
        logger.info(f"Available steps: {list(config.steps.keys())}")

    async def execute(self, input_data: TranslationInput, show_progress: bool = True) -> TranslationOutput:
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
            progress_tracker = ProgressTracker([
                "initial_translation",
                "editor_review",
                "translator_revision"
            ])

        try:
            # Step 1: Initial Translation
            log_entries.append(f"=== STEP 1: INITIAL TRANSLATION ===")
            log_entries.append(f"Input: {input_data.original_poem[:100]}...")

            if progress_tracker:
                progress_tracker.start_step("initial_translation")

            initial_translation = await self._initial_translation(input_data)
            log_entries.append(f"Initial translation completed: {initial_translation.tokens_used} tokens")
            log_entries.append(f"Translation: {initial_translation.initial_translation[:100]}...")

            if progress_tracker:
                progress_tracker.complete_step("initial_translation", {
                    'original_poem': input_data.original_poem,
                    'initial_translation': initial_translation.initial_translation,
                    'initial_translation_notes': initial_translation.initial_translation_notes,
                    'tokens_used': initial_translation.tokens_used
                })

            # Step 2: Editor Review
            log_entries.append(f"\n=== STEP 2: EDITOR REVIEW ===")

            logger.info(f"Starting editor review with {initial_translation.tokens_used} tokens from initial translation")

            if progress_tracker:
                progress_tracker.start_step("editor_review")

            editor_review = await self._editor_review(input_data, initial_translation)
            logger.info(f"Editor review step completed successfully")
            log_entries.append(f"Editor review completed: {editor_review.tokens_used} tokens")
            log_entries.append(f"Review length: {len(editor_review.editor_suggestions)} characters")
            log_entries.append(f"Review preview: {editor_review.editor_suggestions[:200]}...")

            if progress_tracker:
                progress_tracker.complete_step("editor_review", {
                    'editor_suggestions': editor_review.editor_suggestions,
                    'tokens_used': editor_review.tokens_used
                })

            # Step 3: Translator Revision
            log_entries.append(f"\n=== STEP 3: TRANSLATOR REVISION ===")

            if progress_tracker:
                progress_tracker.start_step("translator_revision")

            revised_translation = await self._translator_revision(
                input_data, initial_translation, editor_review
            )
            log_entries.append(f"Translator revision completed: {revised_translation.tokens_used} tokens")
            log_entries.append(f"Revised translation length: {len(revised_translation.revised_translation)} characters")

            if progress_tracker:
                progress_tracker.complete_step("translator_revision", {
                    'revised_translation': revised_translation.revised_translation,
                    'revised_translation_notes': revised_translation.revised_translation_notes,
                    'tokens_used': revised_translation.tokens_used
                })

            # Show final summary if progress tracking
            if progress_tracker:
                summary = progress_tracker.get_summary()
                print(f"\n🎉 Translation Complete!")
                print(f"   Total Steps: {summary['completed_steps']}/{summary['total_steps']}")
                print(f"   Total Tokens: {summary['total_tokens']}")
                print(f"   Total Duration: {summary['total_duration']:.2f}s")

            # Aggregate results
            duration = time.time() - start_time
            total_tokens = (
                initial_translation.tokens_used +
                editor_review.tokens_used +
                revised_translation.tokens_used
            )

            logger.info(f"Workflow {workflow_id} completed successfully in {duration:.2f}s")
            logger.info(f"Total tokens used: {total_tokens}")

            return self._aggregate_output(
                workflow_id=workflow_id,
                input_data=input_data,
                initial_translation=initial_translation,
                editor_review=editor_review,
                revised_translation=revised_translation,
                log_entries=log_entries,
                total_tokens=total_tokens,
                duration=duration
            )

        except Exception as e:
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
        self,
        input_data: TranslationInput
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
            step_config = self.config.steps['initial_translation']

            # Prepare input context
            input_context = {
                'original_poem': input_data.original_poem,
                'source_lang': input_data.source_lang,
                'target_lang': input_data.target_lang
            }

            # Execute step
            result = await self.step_executor.execute_initial_translation(
                input_data, step_config
            )

            # Extract translation and notes from XML
            if 'output' in result:
                output_data = result['output']
                translation = output_data.get('initial_translation', '')
                notes = output_data.get('initial_translation_notes', '')
            else:
                # Fallback: try to extract from raw response
                raw_content = result.get('metadata', {}).get('raw_response', {}).get('content_preview', '')
                extracted = extract_initial_translation_from_xml(raw_content)
                translation = extracted.get('initial_translation', '')
                notes = extracted.get('initial_translation_notes', '')

            # Create InitialTranslation model
            return InitialTranslation(
                initial_translation=translation,
                initial_translation_notes=notes,
                model_info={
                    'provider': step_config.provider,
                    'model': step_config.model,
                    'temperature': str(step_config.temperature)
                },
                tokens_used=result.get('metadata', {}).get('usage', {}).get('tokens_used', 0)
            )

        except Exception as e:
            logger.error(f"Initial translation step failed: {e}")
            raise StepExecutionError(f"Initial translation failed: {e}")

    async def _editor_review(
        self,
        input_data: TranslationInput,
        initial_translation: InitialTranslation
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
            step_config = self.config.steps['editor_review']

            # Execute step
            result = await self.step_executor.execute_editor_review(
                initial_translation, input_data, step_config
            )

            # Extract editor text from result
            editor_suggestions = ''
            if 'output' in result:
                output_data = result['output']
                # Try different possible field names
                editor_suggestions = output_data.get('editor_suggestions', '')

            if not editor_suggestions:
                # Fallback: use content directly
                editor_suggestions = result.get('metadata', {}).get('raw_response', {}).get('content_preview', '')

            # Create EditorReview model
            return EditorReview(
                editor_suggestions=editor_suggestions,
                model_info={
                    'provider': step_config.provider,
                    'model': step_config.model,
                    'temperature': str(step_config.temperature)
                },
                tokens_used=result.get('metadata', {}).get('usage', {}).get('tokens_used', 0)
            )

        except Exception as e:
            logger.error(f"Editor review step failed: {e}")
            raise StepExecutionError(f"Editor review failed: {e}")

    async def _translator_revision(
        self,
        input_data: TranslationInput,
        initial_translation: InitialTranslation,
        editor_review: EditorReview
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
            step_config = self.config.steps['translator_revision']

            # Execute step
            result = await self.step_executor.execute_translator_revision(
                editor_review, input_data, initial_translation, step_config
            )

            # Extract revised translation and notes from XML
            if 'output' in result:
                output_data = result['output']
                translation = output_data.get('revised_translation', '')
                notes = output_data.get('revised_translation_notes', '')
            else:
                # Fallback: try to extract from raw response
                raw_content = result.get('metadata', {}).get('raw_response', {}).get('content_preview', '')
                extracted = extract_revised_translation_from_xml(raw_content)
                translation = extracted.get('revised_translation', '')
                notes = extracted.get('revised_translation_notes', '')

            # Create RevisedTranslation model
            return RevisedTranslation(
                revised_translation=translation,
                revised_translation_notes=notes,
                model_info={
                    'provider': step_config.provider,
                    'model': step_config.model,
                    'temperature': str(step_config.temperature)
                },
                tokens_used=result.get('metadata', {}).get('usage', {}).get('tokens_used', 0)
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
        duration: float
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
        full_log += f"\nTotal tokens: {total_tokens}"
        full_log += f"\nDuration: {duration:.2f}s"
        full_log += f"\nCompleted: {datetime.now().isoformat()}"

        return TranslationOutput(
            workflow_id=workflow_id,
            input=input_data,
            initial_translation=initial_translation,
            editor_review=editor_review,
            revised_translation=revised_translation,
            full_log=full_log,
            total_tokens=total_tokens,
            duration_seconds=duration
        )

    def __repr__(self) -> str:
        """String representation of the workflow."""
        return f"TranslationWorkflow(name='{self.config.name}', version='{self.config.version}')"