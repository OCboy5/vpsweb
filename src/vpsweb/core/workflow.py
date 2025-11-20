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
from ..models.config import WorkflowConfig, WorkflowMode, ProvidersConfig
from ..services.config import get_config_facade, ConfigFacade
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
        config_or_facade: Optional[WorkflowConfig] = None,
        providers_config: Optional[ProvidersConfig] = None,
        workflow_mode: Optional[WorkflowMode] = None,
        task_service: Optional[Any] = None,
        task_id: Optional[str] = None,
        system_config: Optional[Dict[str, Any]] = None,
        repository_service: Optional[Any] = None,
        # New ConfigFacade-based constructor parameters
        config_facade: Optional[ConfigFacade] = None,
        complete_config: Optional[Any] = None,
    ):
        """
        Initialize the translation workflow.

        Args:
            config_or_facade: Legacy WorkflowConfig (deprecated, use config_facade instead)
            providers_config: Legacy ProvidersConfig (deprecated, use config_facade instead)
            workflow_mode: Workflow mode to use (reasoning, non_reasoning, hybrid)
            task_service: Optional task service
            task_id: Optional task ID
            system_config: System configuration (deprecated)
            repository_service: Optional repository service for BBR retrieval
            config_facade: New ConfigFacade instance for configuration access
            complete_config: Legacy CompleteConfig for backward compatibility
        """
        # Support both legacy and new patterns
        if config_facade is not None:
            # New ConfigFacade-based initialization
            self._config_facade = config_facade
            self._using_facade = True
        else:
            # Try to auto-detect global ConfigFacade for backward compatibility
            try:
                from ..services.config import get_config_facade
                self._config_facade = get_config_facade()
                self._using_facade = True
                logger.info("TranslationWorkflow auto-detected global ConfigFacade")
            except RuntimeError:
                # No global ConfigFacade available, use legacy pattern
                if config_or_facade is None or providers_config is None or workflow_mode is None:
                    raise ValueError(
                        "Legacy initialization requires config, providers_config, and workflow_mode"
                    )
                self.config = config_or_facade  # Legacy WorkflowConfig
                self.providers_config = providers_config  # Legacy ProvidersConfig
                self.workflow_mode = workflow_mode
                self.system_config = system_config or {}
                self._using_facade = False
                self._config_facade = None
                logger.info("TranslationWorkflow using legacy configuration pattern")

        self.task_service = task_service
        self.task_id = task_id
        self.repository_service = repository_service

        # Initialize common components
        self._initialize_components()

        # Log initialization
        if self._using_facade:
            workflow_info = self._config_facade.get_workflow_info()
            logger.info(f"Initialized TranslationWorkflow: {workflow_info['name']} v{workflow_info['version']}")
        else:
            logger.info(f"Initialized TranslationWorkflow: {self.config.name} v{self.config.version}")

        logger.info(f"Workflow mode: {self._get_workflow_mode().value}")
        logger.info(f"Available steps: {list(self.workflow_steps.keys())}")

    def cancel(self):
        self._cancelled = True

    def _initialize_components(self):
        """Initialize common components based on initialization pattern."""
        if self._using_facade:
            # ConfigFacade-based initialization
            self.workflow_steps = self._config_facade.workflow.get_workflow_steps(self._get_workflow_mode())
            providers_config = self._config_facade.providers
        else:
            # Legacy initialization
            self.workflow_steps = self.config.get_workflow_steps(self.workflow_mode)
            providers_config = self.providers_config

        # Initialize services
        if self._using_facade:
            self.llm_factory = LLMFactory(config_facade=self._config_facade)
        else:
            self.llm_factory = LLMFactory(providers_config)
        self.prompt_service = PromptService()

        # Get system config for step executor
        if self._using_facade:
            # ConfigFacade stores main config in the 'main' attribute
            system_config = self._config_facade.main.model_dump() if hasattr(self._config_facade, 'main') else {}
        else:
            system_config = self.system_config

        self.step_executor = StepExecutor(
            self.llm_factory, self.prompt_service, system_config
        )

        # Initialize progress callback (optional)
        self.progress_callback: Optional[
            Callable[[str, Dict[str, Any]], Awaitable[None]]
        ] = None

        self._cancelled = False

    def _get_workflow_mode(self) -> WorkflowMode:
        """Get current workflow mode for both legacy and facade patterns."""
        if self._using_facade:
            # Extract from ConfigFacade main config
            from ..models.config import WorkflowMode
            return WorkflowMode(self._config_facade.get_workflow_info()['mode'])
        else:
            return self.workflow_mode

    def _get_step_config(self, step_name: str):
        """Get step configuration for both legacy and facade patterns."""
        if self._using_facade:
            return self._config_facade.workflow.get_step_config(self._get_workflow_mode(), step_name)
        else:
            return self.workflow_steps[step_name]

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

        logger.debug(f"Executing TranslationWorkflow with workflow_id: {workflow_id}")
        logger.info(f"Starting translation workflow {workflow_id}")
        logger.info(f"Translation: {input_data.source_lang} → {input_data.target_lang}")
        logger.info(f"Poem length: {len(input_data.original_poem)} characters")

        # Initialize progress tracker
        progress_tracker = None
        if show_progress:
            # Create progress tracker if it doesn't exist
            if not hasattr(self, 'progress_tracker') or self.progress_tracker is None:
                from ..utils.progress import create_progress_tracker
                workflow_steps = list(self.workflow_steps.keys()) if hasattr(self, 'workflow_steps') else []
                self.progress_tracker = create_progress_tracker(workflow_steps)
                logger.info(f"Created progress tracker with steps: {workflow_steps}")
            progress_tracker = self.progress_tracker

        if self._cancelled:
            return

        # Universal BBR Validation and Generation
        bbr_content = None
        bbr_record = None  # Store the full BBR record for final output
        if input_data.metadata and "poem_id" in input_data.metadata:
            poem_id = input_data.metadata["poem_id"]
            logger.info(f"Checking BBR for poem {poem_id}")

            try:
                # Check if BBR exists for this poem using repository service
                if self.repository_service:
                    bbr = self.repository_service.repo.background_briefing_reports.get_by_poem(
                        poem_id
                    )

                    if bbr:
                        # Store the full BBR record for final output
                        bbr_record = bbr
                        # Extract the content field for the prompt
                        bbr_content = bbr.content
                        logger.info(
                            f"Found existing BBR for poem {poem_id} (content length: {len(bbr_content)} chars)"
                        )
                        # DEBUG: Print BBR content preview
                        print(f"\n=== BBR CONTENT DEBUG ===")
                        print(f"Poem ID: {poem_id}")
                        print(f"BBR Content Length: {len(bbr_content)} chars")
                        print(f"BBR Content Preview (first 500 chars):")
                        print(bbr_content[:500])
                        print(f"=== END BBR CONTENT DEBUG ===\n")
                    else:
                        logger.info(
                            f"No BBR found for poem {poem_id}, proceeding without BBR"
                        )
                        # Note: BBR generation could be added here if needed for CLI usage
                else:
                    logger.debug("No repository service available for BBR retrieval")

            except Exception as e:
                logger.error(f"BBR retrieval failed for poem {poem_id}: {e}")
                # Continue without BBR if retrieval fails
                logger.info("Proceeding without BBR content")
        else:
            logger.debug("No poem_id available for BBR validation")

        try:
            log_entries.append(
                f"=== STEP 1: INITIAL TRANSLATION ({self._get_workflow_mode().value.upper()} MODE) ==="
            )
            # Get input preview length from config
            input_preview_length = (
                getattr(self._config_facade.main.system.preview_lengths, 'input_preview', 100)
                if hasattr(self._config_facade.main, 'system') and
                   hasattr(self._config_facade.main.system, 'preview_lengths') else 100
            )
            log_entries.append(
                f"Input: {input_data.original_poem[:input_preview_length]}..."
            )

            if progress_tracker:
                step_config = self._config_facade.get_workflow_step_config(
                    self._get_workflow_mode().value, "initial_translation"
                )
                model_info = {
                    "provider": step_config["provider"],
                    "model": step_config["model"],
                    "temperature": str(step_config["temperature"]),
                    "is_reasoning": self._config_facade.model_registry.is_reasoning_model(
                        step_config["model"]
                    ),
                }
                progress_tracker.start_step("initial_translation", model_info)

            # Call progress callback when Step 1 starts
            if self.progress_callback:
                await self.progress_callback(
                    "Initial Translation",
                    {"status": "running", "message": "Starting initial translation..."},
                )

            logger.debug("Calling _initial_translation")
            step_start_time = time.time()
            initial_translation = await self._initial_translation(
                input_data, bbr_content
            )
            step_duration = time.time() - step_start_time
            logger.debug(f"_initial_translation completed in {step_duration:.2f}s")
            initial_translation.duration = step_duration

            # Calculate cost for this step
            step_config = self._config_facade.get_workflow_step_config(
                self._get_workflow_mode().value, "initial_translation"
            )
            # Use actual token counts from API response
            input_tokens = getattr(initial_translation, "prompt_tokens", 0) or 0
            output_tokens = getattr(initial_translation, "completion_tokens", 0) or 0
            initial_translation.cost = self._calculate_step_cost(
                step_config["provider"], step_config["model"], input_tokens, output_tokens
            )
            log_entries.append(
                f"Initial translation completed: {initial_translation.tokens_used} tokens"
            )
            # Get response preview length from config
            response_preview_length = (
                getattr(self._config_facade.main.system.preview_lengths, 'response_preview', 100)
                if hasattr(self._config_facade.main, 'system') and
                   hasattr(self._config_facade.main.system, 'preview_lengths') else 100
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
                        "workflow_mode": self._get_workflow_mode().value,
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

            if self._cancelled:
                return

            # Step 2: Editor Review

            log_entries.append(
                f"\n=== STEP 2: EDITOR REVIEW ({self._get_workflow_mode().value.upper()} MODE) ==="
            )

            logger.info(
                f"Starting editor review with {initial_translation.tokens_used} tokens from initial translation"
            )

            if progress_tracker:
                step_config = self._config_facade.get_workflow_step_config(
                    self._get_workflow_mode().value, "editor_review"
                )
                model_info = {
                    "provider": step_config["provider"],
                    "model": step_config["model"],
                    "temperature": str(step_config["temperature"]),
                    "is_reasoning": self._config_facade.model_registry.is_reasoning_model(
                        step_config["model"]
                    ),
                }
                progress_tracker.start_step("editor_review", model_info)

            # Call progress callback when Step 2 starts
            if self.progress_callback:
                await self.progress_callback(
                    "Editor Review",
                    {"status": "running", "message": "Starting editor review..."},
                )

            logger.debug("Calling _editor_review")
            step_start_time = time.time()
            editor_review = await self._editor_review(input_data, initial_translation)
            step_duration = time.time() - step_start_time
            logger.debug(f"_editor_review completed in {step_duration:.2f}s")
            editor_review.duration = step_duration

            # Calculate cost for this step
            step_config = self._config_facade.get_workflow_step_config(
                self._get_workflow_mode().value, "editor_review"
            )
            # Use actual token counts from API response
            input_tokens = getattr(editor_review, "prompt_tokens", 0) or 0
            output_tokens = getattr(editor_review, "completion_tokens", 0) or 0
            editor_review.cost = self._calculate_step_cost(
                step_config["provider"], step_config["model"], input_tokens, output_tokens
            )
            logger.debug(
                f"Editor Review - Provider: {step_config['provider']}, Model: {step_config['model']}"
            )
            logger.debug(
                f"Editor Review - Input Tokens: {input_tokens}, Output Tokens: {output_tokens}"
            )
            logger.debug(f"Editor Review - Calculated Cost: {editor_review.cost}")
            logger.info(f"Editor review step completed successfully")
            log_entries.append(
                f"Editor review completed: {editor_review.tokens_used} tokens"
            )
            log_entries.append(
                f"Review length: {len(editor_review.editor_suggestions)} characters"
            )
            # Get editor preview length from config
            editor_preview_length = (
                getattr(self._config_facade.main.system.preview_lengths, 'editor_preview', 200)
                if hasattr(self._config_facade.main, 'system') and
                   hasattr(self._config_facade.main.system, 'preview_lengths') else 200
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
                        "workflow_mode": self._get_workflow_mode().value,
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

            if self._cancelled:
                return

            # Step 3: Translator Revision

            log_entries.append(
                f"\n=== STEP 3: TRANSLATOR REVISION ({self._get_workflow_mode().value.upper()} MODE) ==="
            )

            if progress_tracker:
                step_config = self._config_facade.get_workflow_step_config(
                    self._get_workflow_mode().value, "translator_revision"
                )
                model_info = {
                    "provider": step_config["provider"],
                    "model": step_config["model"],
                    "temperature": str(step_config["temperature"]),
                    "is_reasoning": self._config_facade.model_registry.is_reasoning_model(
                        step_config["model"]
                    ),
                }
                progress_tracker.start_step("translator_revision", model_info)

            # Call progress callback when Step 3 starts
            if self.progress_callback:
                await self.progress_callback(
                    "Translator Revision",
                    {"status": "running", "message": "Starting translator revision..."},
                )

            logger.debug("Calling _translator_revision")
            step_start_time = time.time()
            revised_translation = await self._translator_revision(
                input_data, initial_translation, editor_review
            )

            if self._cancelled:
                return
            step_duration = time.time() - step_start_time
            logger.debug(f"_translator_revision completed in {step_duration:.2f}s")
            revised_translation.duration = step_duration

            # Calculate cost for this step
            step_config = self._config_facade.get_workflow_step_config(
                self._get_workflow_mode().value, "translator_revision"
            )
            # Use actual token counts from API response
            input_tokens = getattr(revised_translation, "prompt_tokens", 0) or 0
            output_tokens = getattr(revised_translation, "completion_tokens", 0) or 0
            revised_translation.cost = self._calculate_step_cost(
                step_config["provider"], step_config["model"], input_tokens, output_tokens
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
                        "workflow_mode": self._get_workflow_mode().value,
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
                background_briefing_report=bbr_record,
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
        self, input_data: TranslationInput, bbr_content: Optional[str] = None
    ) -> InitialTranslation:
        """
        Execute initial translation step.

        Args:
            input_data: Translation input data
            bbr_content: Optional Background Briefing Report content for V2 templates

        Returns:
            Initial translation with notes

        Raises:
            StepExecutionError: If translation step fails
        """
        try:
            step_config_dict = self._config_facade.get_workflow_step_config(
                self._get_workflow_mode().value, "initial_translation"
            )

            # Create a simple object to hold step config for executor compatibility
            class StepConfigAdapter:
                def __init__(self, config_dict):
                    self.provider = config_dict.get("provider")
                    self.model = config_dict.get("model")
                    self.prompt_template = config_dict.get("prompt_template")
                    self.temperature = config_dict.get("temperature")
                    self.max_tokens = config_dict.get("max_tokens")
                    self.timeout = config_dict.get("timeout")
                    self.retry_attempts = config_dict.get("retry_attempts")
                    self.stop = config_dict.get("stop")
                    self.task_name = config_dict.get("task_name")
                    # Store original dict for any additional access
                    self._config_dict = config_dict

                def __getattr__(self, name):
                    # Fallback to dict for any other attributes
                    return self._config_dict.get(name)

            step_config = StepConfigAdapter(step_config_dict)

            # Execute step
            result = await self.step_executor.execute_initial_translation(
                input_data, step_config, bbr_content
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
            step_config_dict = self._config_facade.get_workflow_step_config(
                self._get_workflow_mode().value, "editor_review"
            )

            # Create adapter for executor compatibility
            class StepConfigAdapter:
                def __init__(self, config_dict):
                    self.provider = config_dict.get("provider")
                    self.model = config_dict.get("model")
                    self.prompt_template = config_dict.get("prompt_template")
                    self.temperature = config_dict.get("temperature")
                    self.max_tokens = config_dict.get("max_tokens")
                    self.timeout = config_dict.get("timeout")
                    self.retry_attempts = config_dict.get("retry_attempts")
                    self.stop = config_dict.get("stop")
                    self.task_name = config_dict.get("task_name")
                    self._config_dict = config_dict

                def __getattr__(self, name):
                    return self._config_dict.get(name)

            step_config = StepConfigAdapter(step_config_dict)

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
                    "is_reasoning": str(
                        self._config_facade.model_registry.is_reasoning_model(step_config.model)
                    ),
                },
                tokens_used=usage.get("tokens_used", 0),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                duration=result.get("duration"),
                cost=result.get("cost"),
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
            step_config_dict = self._config_facade.get_workflow_step_config(
                self._get_workflow_mode().value, "translator_revision"
            )

            # Create adapter for executor compatibility
            class StepConfigAdapter:
                def __init__(self, config_dict):
                    self.provider = config_dict.get("provider")
                    self.model = config_dict.get("model")
                    self.prompt_template = config_dict.get("prompt_template")
                    self.temperature = config_dict.get("temperature")
                    self.max_tokens = config_dict.get("max_tokens")
                    self.timeout = config_dict.get("timeout")
                    self.retry_attempts = config_dict.get("retry_attempts")
                    self.stop = config_dict.get("stop")
                    self.task_name = config_dict.get("task_name")
                    self._config_dict = config_dict

                def __getattr__(self, name):
                    return self._config_dict.get(name)

            step_config = StepConfigAdapter(step_config_dict)

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
        background_briefing_report: Optional[Any] = None,
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
            background_briefing_report: Optional BBR from database

        Returns:
            Complete translation output
        """
        # Combine all log entries
        full_log = "\n".join(log_entries)

        # Add summary to log
        full_log += f"\n\n=== WORKFLOW SUMMARY ==="
        full_log += f"\nWorkflow ID: {workflow_id}"
        full_log += f"\nWorkflow Mode: {self._get_workflow_mode().value}"
        full_log += f"\nTotal tokens: {total_tokens}"
        full_log += f"\nDuration: {duration:.2f}s"
        full_log += f"\nCompleted: {datetime.now().isoformat()}"

        # Create BBR model if available
        bbr_model = None
        if background_briefing_report:
            from ..models.translation import BackgroundBriefingReport
            import json

            # Parse model_info from JSON string if it exists and convert all values to strings
            model_info_dict = None
            if background_briefing_report.model_info:
                try:
                    parsed_info = json.loads(background_briefing_report.model_info)
                    # Convert all values to strings to match Dict[str, str] type
                    if isinstance(parsed_info, dict):
                        model_info_dict = {k: str(v) for k, v in parsed_info.items()}
                    else:
                        logger.warning(
                            f"BBR model_info is not a dictionary: {parsed_info}"
                        )
                        model_info_dict = None
                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        f"Failed to parse BBR model_info as JSON: {background_briefing_report.model_info}"
                    )
                    model_info_dict = None

            # Create the BackgroundBriefingReport model
            logger.debug(
                f"Creating BBR model - content length: {len(background_briefing_report.content)} chars, "
                f"model_info: {background_briefing_report.model_info}, "
                f"tokens_used: {background_briefing_report.tokens_used}, "
                f"time_spent: {background_briefing_report.time_spent}, "
                f"cost: {background_briefing_report.cost}, "
                f"poem_id: {background_briefing_report.poem_id}"
            )

            bbr_model = BackgroundBriefingReport(
                content=background_briefing_report.content,
                model_info=model_info_dict,
                tokens_used=background_briefing_report.tokens_used,
                cost=background_briefing_report.cost,
                duration=background_briefing_report.time_spent,  # Map time_spent to duration
                poem_id=background_briefing_report.poem_id,
            )

        return TranslationOutput(
            workflow_id=workflow_id,
            input=input_data,
            initial_translation=initial_translation,
            editor_review=editor_review,
            revised_translation=revised_translation,
            background_briefing_report=bbr_model,
            total_tokens=total_tokens,
            duration_seconds=duration,
            workflow_mode=self._get_workflow_mode().value,
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
            # Try to use ConfigFacade model registry if available
            if self._using_facade and hasattr(self._config_facade, 'model_registry'):
                # Use the same logic as BBR generator
                model_ref = self._config_facade.model_registry.find_model_ref_by_name(model)
                if model_ref:
                    return self._config_facade.model_registry.calculate_cost(model_ref, input_tokens, output_tokens)
                else:
                    logger.warning(f"Model reference not found for model name: {model}")
                    return 0.0
            else:
                # Legacy pattern - get pricing from providers_config
                providers_config = self.llm_factory.providers_config

                if hasattr(providers_config, "pricing") and providers_config.pricing:
                    pricing = providers_config.pricing

                # Try to find model reference that corresponds to this model name
                model_ref = self._find_model_reference_dynamically(model)

                # First try model reference, then fall back to model name
                if model_ref and model_ref in pricing:
                    model_pricing = pricing[model_ref]
                    logger.debug(f"Found pricing for model {model} using reference {model_ref}")
                elif model in pricing:
                    model_pricing = pricing[model]
                    logger.debug(f"Found pricing for model {model} directly")
                else:
                    logger.warning(f"No pricing information found for model {model} (tried ref: {model_ref})")
                    return 0.0

                # Pricing is RMB per 1K tokens
                input_cost = (input_tokens / 1000) * model_pricing.get("input", 0)
                output_cost = (output_tokens / 1000) * model_pricing.get("output", 0)
                logger.debug(f"Cost calculation for {model}: input={input_cost:.4f}, output={output_cost:.4f}")
                return input_cost + output_cost

                return 0.0
        except Exception as e:
            logger.warning(f"Failed to calculate cost for {provider}/{model}: {e}")
            return 0.0

    def _find_model_reference_dynamically(self, model_name: str) -> Optional[str]:
        """
        Find model reference dynamically using exact matching from model registry.

        This method tries to access the actual model registry configuration
        to perform exact matching from model name to model reference.

        Args:
            model_name: The actual model name (e.g., "qwen-plus-latest")

        Returns:
            Model reference if found, None otherwise
        """
        # Try to use ConfigFacade model registry if available (preferred approach)
        if self._using_facade and hasattr(self._config_facade, 'model_registry'):
            model_ref = self._config_facade.model_registry.find_model_ref_by_name(model_name)
            if model_ref:
                logger.debug(f"Found model reference {model_ref} for {model_name} via ConfigFacade")
                return model_ref

        # Fallback: Try to load model registry directly
        try:
            from ..utils.config_loader import load_model_registry_config
            models_config = load_model_registry_config()

            # Build temporary mapping from the loaded models config
            for ref, info in models_config.get('models', {}).items():
                if info.get('name') == model_name:
                    logger.debug(f"Found model reference {ref} for {model_name} via direct config load")
                    return ref

        except Exception as e:
            logger.warning(f"Failed to load model registry for reference lookup: {e}")

        # Final fallback: Return None if no exact match found
        logger.warning(f"No exact match found for model name: {model_name}")
        return None

    def __repr__(self) -> str:
        """String representation of the workflow."""
        return f"TranslationWorkflow(name='{self.config.name}', version='{self.config.version}')"
