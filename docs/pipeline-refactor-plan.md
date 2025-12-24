# Plan: Modularize Translation Workflow with Pipeline/Stage Architecture

## Overview
This document is the **master plan** for a two-phase refactoring of the translation workflow. The refactoring is split into two phases to reduce risk and allow validation at each step.

**Phase 1: Modularization** → [pipeline-phase1-modularization.md](./pipeline-phase1-modularization.md)
**Phase 2: Parallel Execution** → [pipeline-phase2-parallel.md](./pipeline-phase2-parallel.md)

---

## Summary
Refactor the translation workflow from duplicated step methods to a modular Pipeline/Stage architecture in two phases:

1. **Phase 1 (Modularization)**: Eliminate code duplication, make it easy to add/remove workflow steps
2. **Phase 2 (Parallel Execution)**: Enable running multiple translations in parallel with automatic selection

## Success Criteria (Overall)
1. **Not break anything** - Zero regressions in existing functionality
2. **Easily insert Evaluation step** between initial translation and editor review (Phase 1)
3. **Run multiple initial translations in parallel** and feed results to evaluation step (Phase 2)
4. **Unified manual/auto workflow** sharing same Stage implementations (Phase 1)
5. **Evaluation uses reasoning model** (deepseek_reasoner by default) (Phase 1)

## Current Problems (from code exploration)

### 1. Duplicated StepConfigAdapter Class
**File**: `src/vpsweb/core/workflow.py`
- Lines 709-727, 799-814, ~887: Same `StepConfigAdapter` class repeated 3 times

### 2. Identical Step Execution Pattern
Each of `_initial_translation()`, `_editor_review()`, `_translator_revision()` follows the same pattern:
- Get config from `_config_facade.get_workflow_step_config()`
- Create StepConfigAdapter
- Call `step_executor.execute_*()`
- Extract output with fallback logic
- Create result model (InitialTranslation/EditorReview/RevisedTranslation)

### 3. Hardcoded Dispatch in StepExecutor Methods
**File**: `src/vpsweb/core/executor.py`
- `execute_initial_translation()`, `execute_editor_review()`, `execute_translator_revision()` are separate methods
- Adding a new step requires modifying both workflow.py AND executor.py
- No dynamic dispatch mechanism

### 4. Separate Manual and Auto Workflow Implementations
**Files**: `src/vpsweb/core/workflow.py`, `src/vpsweb/webui/services/manual_workflow_service.py`
- ManualWorkflowService has its own step sequence and state management
- Code duplication in prompt rendering, output parsing, result model creation
- Adding Evaluation step would require changes in both places

### 5. No Support for Parallel Stage Execution
- Current workflow executes stages sequentially
- No mechanism to run multiple instances of a stage and aggregate results
- Cannot support "generate 3 translations in parallel, then evaluate" pattern

## Proposed Architecture

### Core Design Principles

1. **Typed State**: Replace `Dict[str, Any]` with `TypedDict` for type-safe state passing
2. **Execution Modes**: Single Pipeline supports both AUTO and MANUAL execution
3. **Parallel-Ready**: Built-in support for parallel stage execution with configurable count
4. **Stage Registration**: Dynamic dispatch instead of hardcoded if/elif chains
5. **Evaluation First**: Evaluation step is always included in the workflow (not optional)

### Core Abstractions (New File: `src/vpsweb/core/pipeline.py`)

```python
"""
Unified Pipeline Architecture for Translation Workflow.

Supports both automatic and manual execution modes with shared Stage implementations.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypedDict, Type

from ..models.translation import (
    EditorReview,
    InitialTranslation,
    RevisedTranslation,
    TranslationInput,
)

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Pipeline execution mode."""
    AUTO = "auto"      # Fully automatic execution
    MANUAL = "manual"  # Stage-by-stage with user interaction


class PipelineState(TypedDict):
    """
    Type-safe state passed between pipeline stages.

    This replaces the untyped Dict[str, Any] with explicit schema.
    """
    # Core inputs
    translation_input: TranslationInput
    step_executor: "StepExecutor"
    bbr_content: Optional[str]

    # Stage outputs - support both single and multiple values
    initial_translation: Optional[InitialTranslation]
    initial_translations: Optional[List[InitialTranslation]]  # For parallel + evaluation
    evaluation_result: Optional[Dict[str, Any]]  # New: evaluation output
    editor_review: Optional[EditorReview]
    revised_translation: Optional[RevisedTranslation]

    # Execution metadata
    current_stage_index: int
    total_stages: int


@dataclass
class StageContext:
    """
    Context passed through pipeline stages.

    Attributes:
        input_data: Original input data for the pipeline
        workflow_mode: Current workflow mode (hybrid, reasoning, non_reasoning, manual)
        config_facade: ConfigFacade for accessing workflow/LLM configuration
        system_config: Main system config including translation_strategy dials
        state: Typed state passed between stages
        execution_mode: AUTO or MANUAL execution
    """
    input_data: Dict[str, Any]
    workflow_mode: str
    config_facade: "ConfigFacade"
    system_config: Dict[str, Any]
    state: PipelineState
    execution_mode: ExecutionMode = ExecutionMode.AUTO


@dataclass
class StageResult:
    """Result from a stage execution."""
    status: str  # "success", "failed", "skipped", "waiting_for_user"
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParallelStageConfig:
    """
    Configuration for running a stage multiple times in parallel.

    Attributes:
        stage_class: The Stage class to run in parallel
        count: Number of parallel instances to run (default=1 means sequential)
        config_generator: Optional function to generate different config per instance
        output_key: Key in state to store aggregated results
    """
    stage_class: Type["Stage"]
    count: int = 1  # Default to 1 (sequential execution)
    config_generator: Optional[Callable[[int], Dict[str, Any]]] = None
    output_key: str = "initial_translations"


class Stage(ABC):
    """
    Abstract base class for workflow stages.

    All stages inherit from this and implement execute() method.
    Stages are shared between AUTO and MANUAL execution modes.
    """
    name: str
    display_name: str

    @abstractmethod
    async def execute(self, context: StageContext) -> StageResult:
        """Execute the stage logic."""
        pass

    def build_input_data(self, context: StageContext) -> Dict[str, Any]:
        """Override in subclass for custom input building."""
        return context.input_data.copy()

    def get_rendered_prompt(self, context: StageContext) -> tuple[str, str]:
        """
        Get the rendered prompt for this stage (for MANUAL mode).
        Override in subclass to provide the prompt for user to copy.
        """
        raise NotImplementedError(f"{self.name} does not support manual prompt rendering")


ProgressCallback = Callable[[str, Dict[str, Any]], Awaitable[None]]


class Pipeline:
    """
    Unified pipeline orchestrator supporting both AUTO and MANUAL execution.

    Key features:
    - Sequential and parallel stage execution
    - Shared Stage implementations for auto and manual modes
    - Centralized error handling, progress tracking, metrics
    """

    def __init__(
        self,
        name: str,
        stages: List[Stage],
        step_executor: "StepExecutor",
        progress_callback: Optional[ProgressCallback] = None,
        parallel_configs: Optional[List[ParallelStageConfig]] = None,
    ):
        self.name = name
        self.stages = stages
        self.step_executor = step_executor
        self.progress_callback = progress_callback
        self.parallel_configs = parallel_configs or []
        self.metrics = {"stages_completed": 0, "stages_failed": 0, "total_duration": 0}

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: StageContext,
        resume_from_stage: int = None,
    ) -> Dict[str, Any]:
        """
        Execute all stages in sequence (AUTO mode) or prepare for manual interaction (MANUAL mode).

        Args:
            input_data: Original input data for the pipeline
            context: Stage context with state and execution mode
            resume_from_stage: Optional stage index to resume from (for MANUAL mode workflow resume)

        CRITICAL for MANUAL mode:
        - When resume_from_stage is provided, skip stages before this index
        - After each completed stage, update context.state["current_stage_index"]
        - Return context with current_stage_index so caller can resume later
        """
        results = {}
        start_time = asyncio.get_event_loop().time()

        # Determine starting stage (for resume capability in MANUAL mode)
        start_idx = resume_from_stage if resume_from_stage is not None else context.state.get("current_stage_index", 0)

        expanded_stages = self._expand_stages()

        for i, stage_or_config in enumerate(expanded_stages):
            # Skip completed stages (for MANUAL mode resume)
            if i < start_idx:
                continue

            context.state["current_stage_index"] = i

            if isinstance(stage_or_config, ParallelStageConfig):
                # Parallel execution
                result = await self._execute_parallel_stage(stage_or_config, context)
                results[f"{stage_or_config.output_key}_parallel"] = result
            else:
                # Sequential execution
                result = await self._execute_stage(stage_or_config, context)
                results[stage_or_config.name] = result

                # For manual mode, stop after each stage and wait for user
                if context.execution_mode == ExecutionMode.MANUAL:
                    if result.status == "success":
                        result.status = "waiting_for_user"
                        break  # Return control to user for input

            # Stop on failure
            if result.status == "failed":
                break

        self.metrics["total_duration"] = asyncio.get_event_loop().time() - start_time
        return {"pipeline_name": self.name, "results": results, "metrics": self.metrics}

    def _expand_stages(self) -> List:
        """Expand stages with parallel configurations."""
        result = []
        for stage in self.stages:
            # Check if this stage has a parallel config
            matching = [c for c in self.parallel_configs if c.stage_class == type(stage)]
            if matching and matching[0].count > 1:
                result.append(matching[0])
            else:
                result.append(stage)
        return result

    async def _execute_stage(self, stage: Stage, context: StageContext) -> StageResult:
        """Execute a single stage with progress tracking."""
        if self.progress_callback:
            await self.progress_callback(
                stage.display_name,
                {"status": "running", "message": f"Starting {stage.display_name}..."}
            )

        try:
            result = await stage.execute(context)

            if result.status == "success":
                self.metrics["stages_completed"] += 1
                if self.progress_callback:
                    await self.progress_callback(
                        stage.display_name,
                        {"status": "completed", **result.metadata}
                    )
            else:
                self.metrics["stages_failed"] += 1

            return result

        except Exception as e:
            self.metrics["stages_failed"] += 1
            logger.error(f"Stage {stage.name} failed: {e}")
            if self.progress_callback:
                await self.progress_callback(
                    stage.display_name,
                    {"status": "failed", "error": str(e)}
                )
            return StageResult(status="failed", error=str(e))

    async def _execute_parallel_stage(
        self, config: ParallelStageConfig, context: StageContext
    ) -> StageResult:
        """
        Execute multiple instances of a stage in parallel.

        Results are aggregated into a list and stored in context.state.

        Uses aggregated progress reporting to avoid UI jitter from rapid events.
        """
        if self.progress_callback:
            await self.progress_callback(
                f"{config.stage_class.__name__} (parallel x{config.count})",
                {"status": "running", "message": f"Starting {config.count} parallel instances..."}
            )

        # Create stage instances
        instances = [config.stage_class() for _ in range(config.count)]

        # Execute all in parallel
        tasks = [stage.execute(context) for stage in instances]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results with aggregated progress reporting
        successful_results = []
        failed_count = 0
        total_parallel = config.count

        for i, r in enumerate(raw_results):
            if isinstance(r, Exception):
                logger.error(f"Parallel instance {i} failed: {r}")
                failed_count += 1
            elif r.status == "success":
                successful_results.append(r)
            else:
                failed_count += 1

            # AGGREGATED PROGRESS: Report at milestones to avoid UI jitter
            # Report at 33%, 67%, 100% of completion
            completed = len(successful_results) + failed_count
            milestone = max(1, total_parallel // 3)

            if completed == total_parallel or (completed > 0 and completed % milestone == 0):
                if self.progress_callback:
                    await self.progress_callback(
                        f"{config.stage_class.__name__}",
                        {
                            "status": "running",
                            "parallel_progress": f"{completed}/{total_parallel} completed",
                            "progress_percent": int((completed / total_parallel) * 100),
                        }
                    )

        if not successful_results:
            return StageResult(status="failed", error="All parallel instances failed")

        # Store aggregated results in state
        if config.output_key == "initial_translations":
            context.state["initial_translations"] = [
                InitialTranslation(**r.output) for r in successful_results
            ]
            # Also set the first one as the canonical initial_translation for compatibility
            context.state["initial_translation"] = context.state["initial_translations"][0]

        self.metrics["stages_completed"] += 1

        # Final completion report
        if self.progress_callback:
            await self.progress_callback(
                f"{config.stage_class.__name__}",
                {
                    "status": "completed",
                    "parallel_count": config.count,
                    "successful": len(successful_results),
                    "failed": failed_count,
                }
            )

        return StageResult(
            status="success",
            output={config.output_key: [r.output for r in successful_results]},
            metadata={
                "parallel_count": config.count,
                "successful": len(successful_results),
                "failed": failed_count,
            },
        )
```

### Concrete Stage Implementations (New File: `src/vpsweb/core/stages.py`)

```python
"""
Concrete stage implementations for the translation pipeline.

All stages share the same BaseTranslationStage for common logic.
Each stage overrides build_input_data() for its specific input requirements.
"""
import logging
from typing import Dict, List, Optional, Callable, Any

from .pipeline import Stage, StageContext, StageResult
from ..models.translation import (
    EditorReview,
    InitialTranslation,
    RevisedTranslation,
    TranslationInput,
)

logger = logging.getLogger(__name__)


class BaseTranslationStage(Stage):
    """
    Base class eliminating StepConfigAdapter duplication and output extraction pattern.

    Uses stage registration pattern for dynamic dispatch to StepExecutor methods.
    """

    # Registry mapping step_name to executor method factory
    _executor_factories: Dict[str, Callable] = {}

    def __init__(self, name: str, display_name: str, step_name: str, result_model_class: type):
        self.name = name
        self.display_name = display_name
        self.step_name = step_name
        self.result_model_class = result_model_class

    async def execute(self, context: StageContext) -> StageResult:
        """Execute stage: get config, build input, execute step, extract output, create model."""
        # Get step config from ConfigFacade
        step_config_dict = context.config_facade.get_workflow_step_config(
            context.workflow_mode, self.step_name
        )
        step_config = self._create_step_config(step_config_dict)

        # Build input data (subclass override)
        input_data = self.build_input_data(context)

        # Execute step via registered executor factory
        result = await self._execute_step_via_factory(input_data, step_config, context)

        # Extract output with fallback (centralized)
        output_data = self._extract_output(result)

        # Create result model (centralized)
        model_instance = self._create_result_model(output_data, result, step_config)

        # Store in state
        if self.step_name == "initial_translation":
            context.state["initial_translation"] = model_instance
        elif self.step_name == "editor_review":
            context.state["editor_review"] = model_instance
        elif self.step_name == "translator_revision":
            context.state["revised_translation"] = model_instance

        return StageResult(status="success", output=model_instance.model_dump())

    def _create_step_config(self, config_dict: Dict) -> Any:
        """Create StepConfig from dict (eliminates StepConfigAdapter class duplication)."""
        class StepConfigDict:
            def __init__(self, d):
                self._d = d
            def __getattr__(self, name):
                return self._d.get(name)
        return StepConfigDict(config_dict)

    def _extract_output(self, result: Dict) -> Dict:
        """Centralized output extraction with fallback."""
        if "output" in result:
            return result["output"]
        from ..services.parser import OutputParser
        raw_content = result.get("metadata", {}).get("raw_response", {}).get("content_preview", "")
        return OutputParser.parse_xml(raw_content) or {"content": raw_content}

    def _execute_step_via_factory(
        self, input_data: Dict, step_config: Any, context: StageContext
    ) -> Dict:
        """Dynamic dispatch via registered executor factory."""
        factory = self._executor_factories.get(self.step_name)
        if factory is None:
            raise ValueError(f"No executor factory registered for step: {self.step_name}")

        return factory(
            context.state["step_executor"],
            input_data,
            step_config,
            context.state,
        )

    def _create_result_model(self, output_data: Dict, result: Dict, step_config: Any) -> Any:
        """Centralized result model creation."""
        usage = result.get("metadata", {}).get("usage", {})
        model_info = {
            "provider": step_config.provider,
            "model": step_config.model,
            "temperature": str(step_config.temperature),
        }

        if self.result_model_class == InitialTranslation:
            return InitialTranslation(
                initial_translation=output_data.get("initial_translation", ""),
                initial_translation_notes=output_data.get("initial_translation_notes", ""),
                translated_poem_title=output_data.get("translated_poem_title", ""),
                translated_poet_name=output_data.get("translated_poet_name", ""),
                model_info=model_info,
                tokens_used=usage.get("tokens_used", 0),
            )
        elif self.result_model_class == EditorReview:
            return EditorReview(
                editor_suggestions=output_data.get("editor_suggestions", ""),
                model_info=model_info,
                tokens_used=usage.get("tokens_used", 0),
            )
        elif self.result_model_class == RevisedTranslation:
            return RevisedTranslation(
                revised_translation=output_data.get("revised_translation", ""),
                revised_translation_notes=output_data.get("revised_translation_notes", ""),
                refined_translated_poem_title=output_data.get("refined_translated_poem_title", ""),
                refined_translated_poet_name=output_data.get("refined_translated_poet_name", ""),
                model_info=model_info,
                tokens_used=usage.get("tokens_used", 0),
            )

    @classmethod
    def register_executor_factory(cls, step_name: str, factory: Callable):
        """Register an executor factory for a step name."""
        cls._executor_factories[step_name] = factory


class InitialTranslationStage(BaseTranslationStage):
    def __init__(self):
        super().__init__("initial_translation", "Initial Translation", "initial_translation", InitialTranslation)

    def build_input_data(self, context: StageContext) -> Dict:
        translation_input: TranslationInput = context.state["translation_input"]
        return {
            "original_poem": translation_input.original_poem,
            # Language is str enum, use directly (NOT .value - already a string)
            "source_lang": translation_input.source_lang,  # Already "English", "Chinese", etc.
            "target_lang": translation_input.target_lang,
            "poem_title": translation_input.metadata.get("title", "Untitled"),
            "poet_name": translation_input.metadata.get("author", "Unknown"),
            "adaptation_level": context.system_config.get("translation_strategy", {}).get("adaptation_level", "balanced"),
            "repetition_policy": context.system_config.get("translation_strategy", {}).get("repetition_policy", "strict"),
            "additions_policy": context.system_config.get("translation_strategy", {}).get("additions_policy", "forbid"),
        }


class EvaluationStage(Stage):
    """
    NEW: Evaluation stage to select best translation from multiple candidates.

    Placed between initial_translation and editor_review.
    Uses reasoning model for evaluation.
    """

    name = "evaluation"
    display_name = "Translation Evaluation"

    async def execute(self, context: StageContext) -> StageResult:
        """Evaluate multiple translation candidates and select the best one."""
        # Get all candidate translations from parallel execution
        candidates: List[InitialTranslation] = context.state.get("initial_translations", [])

        if not candidates:
            # Fallback to single translation
            single = context.state.get("initial_translation")
            if single:
                candidates = [single]
            else:
                return StageResult(status="skipped", error="No translations to evaluate")

        # Build evaluation input with all candidates
        evaluation_input = self._build_evaluation_input(candidates, context)

        # Get evaluation step config (uses reasoning model)
        step_config = context.config_facade.get_workflow_step_config(
            context.workflow_mode, "evaluation"
        )

        # Execute evaluation via StepExecutor
        executor = context.state["step_executor"]
        result = await executor.execute_evaluation(candidates, evaluation_input, step_config)

        # Extract selected translation index and rationale
        output_data = result.get("output", {})
        selected_idx = output_data.get("selected_index", 0)
        rationale = output_data.get("rationale", "")

        # Store selected translation as canonical and evaluation result
        context.state["initial_translation"] = candidates[selected_idx]
        context.state["evaluation_result"] = {
            "selected_index": selected_idx,
            "rationale": rationale,
            "all_candidates": [c.model_dump() for c in candidates],
        }

        return StageResult(
            status="success",
            output={
                "selected_translation": candidates[selected_idx].model_dump(),
                "rationale": rationale,
            },
            metadata={"candidates_evaluated": len(candidates)}
        )

    def _build_evaluation_input(
        self, candidates: List[InitialTranslation], context: StageContext
    ) -> Dict[str, Any]:
        """Build input data for evaluation prompt."""
        translation_input: TranslationInput = context.state["translation_input"]

        return {
            "original_poem": translation_input.original_poem,
            # Language is str enum, use directly (NOT .value)
            "source_lang": translation_input.source_lang,
            "target_lang": translation_input.target_lang,
            "candidate_translations": [
                {
                    "index": i,
                    "translation": c.initial_translation,
                    "notes": c.initial_translation_notes,
                    "title": c.translated_poem_title,
                }
                for i, c in enumerate(candidates)
            ],
            "evaluation_criteria": context.system_config.get("evaluation_criteria", {
                "accuracy": "Faithfulness to original meaning",
                "fluency": "Natural flow in target language",
                "style": "Preservation of poetic style",
            }),
        }


class EditorReviewStage(BaseTranslationStage):
    def __init__(self):
        super().__init__("editor_review", "Editor Review", "editor_review", EditorReview)

    def build_input_data(self, context: StageContext) -> Dict:
        translation_input: TranslationInput = context.state["translation_input"]
        initial_translation: InitialTranslation = context.state["initial_translation"]

        from vpsweb.utils.text_processing import add_line_labels
        labeled_original_poem = add_line_labels(translation_input.original_poem)

        return {
            "original_poem": labeled_original_poem,
            # Language is str enum, use directly (NOT .value)
            "source_lang": translation_input.source_lang,
            "target_lang": translation_input.target_lang,
            "translated_poem_title": initial_translation.translated_poem_title,
            "translated_poet_name": initial_translation.translated_poet_name,
            "initial_translation": initial_translation.initial_translation,
            "initial_translation_notes": initial_translation.initial_translation_notes,
        }


class TranslatorRevisionStage(BaseTranslationStage):
    def __init__(self):
        super().__init__("translator_revision", "Translator Revision", "translator_revision", RevisedTranslation)

    def build_input_data(self, context: StageContext) -> Dict:
        translation_input: TranslationInput = context.state["translation_input"]
        initial_translation: InitialTranslation = context.state["initial_translation"]
        editor_review: EditorReview = context.state["editor_review"]

        return {
            "original_poem": translation_input.original_poem,
            # Language is str enum, use directly (NOT .value)
            "source_lang": translation_input.source_lang,
            "target_lang": translation_input.target_lang,
            "initial_translation": initial_translation.initial_translation,
            "editor_suggestions": editor_review.editor_suggestions,
        }


# Register executor factories for dynamic dispatch
def _register_executor_factories():
    """Register all executor factories with BaseTranslationStage."""

    def initial_translation_factory(executor, input_data, config, state):
        return executor.execute_initial_translation(
            state["translation_input"],
            config,
            state.get("bbr_content"),
        )

    def editor_review_factory(executor, input_data, config, state):
        return executor.execute_editor_review(
            state["initial_translation"],
            state["translation_input"],
            config,
        )

    def translator_revision_factory(executor, input_data, config, state):
        return executor.execute_translator_revision(
            state["editor_review"],
            state["translation_input"],
            state["initial_translation"],
            config,
        )

    BaseTranslationStage.register_executor_factory("initial_translation", initial_translation_factory)
    BaseTranslationStage.register_executor_factory("editor_review", editor_review_factory)
    BaseTranslationStage.register_executor_factory("translator_revision", translator_revision_factory)


# Auto-register on import
_register_executor_factories()
```

### Unified Workflow Wrapper (New File: `src/vpsweb/core/pipeline_workflow.py`)

```python
"""
Unified Pipeline Translation Workflow.

Supports both AUTO and MANUAL execution modes with shared Stage implementations.
"""
import logging
import time
import uuid
from typing import Any, Dict, Optional

from ..models.translation import TranslationInput, TranslationOutput
from ..services.config import ConfigFacade
from ..services.llm.factory import LLMFactory
from ..services.prompts import PromptService
from .executor import StepExecutor
from .pipeline import (
    ExecutionMode,
    ParallelStageConfig,
    Pipeline,
    PipelineState,
    StageContext,
)
from .stages import (
    EditorReviewStage,
    EvaluationStage,
    InitialTranslationStage,
    TranslatorRevisionStage,
)

logger = logging.getLogger(__name__)


class PipelineTranslationWorkflow:
    """
    Unified workflow using Pipeline/Stage architecture.

    Supports both AUTO and MANUAL execution modes.
    Maintains exact same interface as TranslationWorkflow for drop-in replacement.
    """

    def __init__(
        self,
        config_facade: ConfigFacade,
        workflow_mode: str,
        task_service=None,
        task_id=None,
        repository_service=None,
        execution_mode: ExecutionMode = ExecutionMode.AUTO,
        parallel_count: int = 1,  # Configurable, default=1 (sequential)
    ):
        self.config_facade = config_facade
        self.workflow_mode = workflow_mode
        self.task_service = task_service
        self.task_id = task_id
        self.repository_service = repository_service
        self.execution_mode = execution_mode
        self.parallel_count = parallel_count

        # Initialize components
        self._initialize_components()

        # Create pipeline with stages
        # NEW: Includes EvaluationStage between initial_translation and editor_review
        stages = [
            InitialTranslationStage(),
            EvaluationStage(),  # Always included (not optional)
            EditorReviewStage(),
            TranslatorRevisionStage(),
        ]

        # Configure parallel execution for initial_translation if count > 1
        parallel_configs = []
        if self.parallel_count > 1:
            parallel_configs.append(
                ParallelStageConfig(
                    stage_class=InitialTranslationStage,
                    count=self.parallel_count,
                    output_key="initial_translations",
                )
            )

        self.pipeline = Pipeline(
            name=f"translation-{workflow_mode}",
            stages=stages,
            step_executor=self.step_executor,
            progress_callback=self._progress_callback_wrapper,
            parallel_configs=parallel_configs,
        )

    def _initialize_components(self):
        """Initialize common components."""
        self.llm_factory = LLMFactory(config_facade=self.config_facade)
        self.prompt_service = PromptService()

        system_config = (
            self.config_facade.main.model_dump()
            if hasattr(self.config_facade, "main")
            else {}
        )

        self.step_executor = StepExecutor(
            self.llm_factory, self.prompt_service, system_config
        )

    async def execute(
        self, input_data: TranslationInput, show_progress: bool = True
    ) -> TranslationOutput:
        """Execute workflow (interface-compatible with TranslationWorkflow)."""
        workflow_id = str(uuid.uuid4())
        start_time = time.time()

        # Handle BBR
        bbr_content = await self._get_bbr_content(input_data)

        # Create typed context
        context = StageContext(
            input_data=input_data.model_dump(),
            workflow_mode=self.workflow_mode,
            config_facade=self.config_facade,
            system_config=self.config_facade.main.model_dump(),
            state=PipelineState(
                translation_input=input_data,
                step_executor=self.step_executor,
                bbr_content=bbr_content,
                initial_translation=None,
                initial_translations=None,
                evaluation_result=None,
                editor_review=None,
                revised_translation=None,
                current_stage_index=0,
                total_stages=4,
            ),
            execution_mode=self.execution_mode,
        )

        # Execute pipeline
        pipeline_result = await self.pipeline.execute(input_data.model_dump(), context)

        # Convert to TranslationOutput
        return self._create_translation_output(
            workflow_id, pipeline_result, input_data, start_time
        )

    async def _get_bbr_content(self, input_data: TranslationInput) -> Optional[str]:
        """Retrieve BBR content from repository if available."""
        # Implementation same as TranslationWorkflow
        ...

    async def _progress_callback(self, step_name: str, data: Dict[str, Any]):
        """Progress callback for SSE updates."""
        if self.task_service and self.task_id:
            await self.task_service.update_task_progress(
                self.task_id, step_name, data
            )

    def _create_translation_output(
        self, workflow_id: str, pipeline_result: Dict, input_data: TranslationInput, start_time: float
    ) -> TranslationOutput:
        """Convert pipeline result to TranslationOutput."""
        results = pipeline_result["results"]
        metrics = pipeline_result["metrics"]

        # Extract stage outputs from state (they were stored during execution)
        # The pipeline result contains the final state
        ...

    # MANUAL mode support methods
    async def get_current_stage_prompt(self, session_id: str) -> Dict[str, str]:
        """
        Get the rendered prompt for the current stage (MANUAL mode).

        Returns system_prompt and user_prompt for user to copy to external LLM.
        """
        # Implementation for manual workflow
        ...

    async def submit_manual_stage_result(
        self, session_id: str, stage_name: str, llm_response: str
    ) -> StageResult:
        """
        Submit LLM response for a manual stage and continue to next.

        Used in MANUAL mode where user interacts with external LLM.
        """
        # Implementation for manual workflow
        ...
```

### Factory with Feature Flag (New File: `src/vpsweb/core/workflow_factory.py`)

```python
"""
Factory for creating workflow instances with unified pipeline support.
"""
from typing import Optional

from ..models.config import WorkflowMode
from .pipeline import ExecutionMode
from .workflow import TranslationWorkflow


def create_translation_workflow(
    config_facade,
    workflow_mode: str,
    task_service=None,
    task_id=None,
    repository_service=None,
    use_pipeline=False,  # FEATURE FLAG
    execution_mode: ExecutionMode = ExecutionMode.AUTO,
    parallel_count: int = 1,  # Configurable, default=1 (sequential)
):
    """
    Factory function to create workflow instance.

    Args:
        config_facade: Configuration facade
        workflow_mode: Workflow mode (hybrid, reasoning, non_reasoning, manual)
        task_service: Optional task service for progress updates
        task_id: Optional task ID
        repository_service: Optional repository service for BBR retrieval
        use_pipeline: Feature flag to enable new pipeline implementation
        execution_mode: AUTO or MANUAL execution
        parallel_count: Number of parallel initial translations (1=sequential)
    """
    if use_pipeline:
        from .pipeline_workflow import PipelineTranslationWorkflow
        return PipelineTranslationWorkflow(
            config_facade=config_facade,
            workflow_mode=workflow_mode,
            task_service=task_service,
            task_id=task_id,
            repository_service=repository_service,
            execution_mode=execution_mode,
            parallel_count=parallel_count,
        )
    else:
        # Legacy workflow for backward compatibility
        return TranslationWorkflow(
            config_facade=config_facade,
            workflow_mode=workflow_mode,
            task_service=task_service,
            task_id=task_id,
            repository_service=repository_service,
        )
```

## Configuration Changes Required

### New File: `config/prompts/evaluation.yaml`

```yaml
# Evaluation step prompt template
# This prompt asks the reasoning model to select the best translation among candidates

system_prompt: |
  You are an expert literary critic and poetry translator specializing in cross-lingual poetic analysis.

  Your task is to evaluate {{candidate_count}} translation candidates of a poem from {{source_lang}} to {{target_lang}}.

  Evaluate each translation based on:
  1. Accuracy: Faithfulness to original meaning and imagery
  2. Fluency: Natural flow and readability in {{target_lang}}
  3. Style: Preservation of poetic style and tone
  4. Creativity: Appropriate creative adaptation where required

  After analyzing all candidates, select the best one and provide your rationale.

user_prompt: |
  Original Poem ({{source_lang}}):
  {{original_poem}}

  Translation Candidates:

  {% for candidate in candidate_translations %}
  Candidate #{{candidate.index}}:
  Translation:
  {{candidate.translation}}

  Notes:
  {{candidate.notes}}

  {% endfor %}

  Evaluation Criteria:
  {% for criterion, description in evaluation_criteria.items() %}
  - {{criterion}}: {{description}}
  {% endfor %}

  Please output your evaluation in the following XML format:

  <evaluation>
    <analysis>
      [Your analysis of each candidate]
    </analysis>
    <selected_index>[0, 1, 2, ...]</selected_index>
    <rationale>
      [Detailed rationale for your selection]
    </rationale>
  </evaluation>
```

### Modify: `config/task_templates.yaml`

Add evaluation step template:

```yaml
task_templates:
  # ... existing templates ...

  # NEW: Evaluation task (uses reasoning model)
  evaluation_reasoning:
    model_ref: "deepseek_reasoner"  # Uses reasoning model as specified
    prompt_template: "evaluation"
    temperature: 0.1
    max_tokens: 8192
    timeout: 180
    retry_attempts: 2
```

### New File: `config/pipeline.yaml`

```yaml
# Pipeline configuration for execution modes and parallelism

pipeline:
  # Default parallel execution count (configurable)
  default_parallel_count: 1

  # Per-workflow-mode overrides
  hybrid:
    parallel_count: 1  # Can be increased to 2-3 for experimentation

  reasoning:
    parallel_count: 1  # Usually 1, reasoning models are slower

  non_reasoning:
    parallel_count: 3  # Can use higher count for fast non-reasoning models

# Evaluation criteria (can be overridden per project)
evaluation_criteria:
  accuracy: "Faithfulness to original meaning and imagery"
  fluency: "Natural flow and readability in target language"
  style: "Preservation of poetic style, tone, and voice"
  creativity: "Appropriate creative adaptation where culturally required"
```

## Implementation Plan

This refactoring is split into **two separate phases** to reduce risk:

### Phase 1: Modularization (Foundation)
**Document**: [pipeline-phase1-modularization.md](./pipeline-phase1-modularization.md)

**Goal**: Make it easy to add/remove workflow steps without breaking existing functionality.

**Duration**: 2-3 weeks

**What's Included:**
- Pipeline/Stage architecture
- ExecutionMode enum (AUTO/MANUAL)
- EvaluationStage (single instance validation)
- Unified manual/auto workflow
- Resume capability for manual workflow
- Factory pattern with feature flag

**Success Criteria:**
- Can add a new step by creating Stage class
- Manual and auto workflows share same Stages
- Existing tests pass
- No performance regression

**Next**: Proceed to Phase 2 only after Phase 1 is validated in production for 2 weeks.

---

### Phase 2: Parallel Execution (Enhancement)
**Document**: [pipeline-phase2-parallel.md](./pipeline-phase2-parallel.md)

**Goal**: Enable running multiple translations in parallel with automatic best-selection.

**Duration**: 1-2 weeks

**Prerequisites**: Phase 1 complete and validated in production.

**What's Included:**
- ParallelStageConfig class
- `Pipeline._execute_parallel_stage()` method
- Aggregated progress reporting
- Configurable parallel_count
- Multi-candidate evaluation

**Success Criteria:**
- Can run N translations in parallel
- Results aggregate correctly
- Evaluation selects best translation
- Progress reporting smooth (no jitter)
- Performance scales with parallel_count

---

## Quick Reference

| Aspect | Phase 1 | Phase 2 |
|--------|---------|---------|
| **Focus** | Architecture & flexibility | Performance & scale |
| **Risk Level** | Medium | Low-Medium |
| **New Classes** | Pipeline, Stage, ExecutionMode | ParallelStageConfig |
| **New Methods** | `Pipeline.execute()`, `_execute_stage()` | `_execute_parallel_stage()` |
| **Evaluation** | Single validation | Multi-candidate selection |
| **Parallel** | No (always count=1) | Yes (configurable) |
| **Files** | 13 new, 8 modified | 3 new, 5 modified |
| **Tests** | Integration & unit | Parallel-specific |

## Detailed Implementation Plans

For detailed step-by-step implementation instructions, see:

- **Phase 1**: [pipeline-phase1-modularization.md](./pipeline-phase1-modularization.md)
  - 11 implementation steps
  - File-by-file breakdown
  - Rollback procedures

- **Phase 2**: [pipeline-phase2-parallel.md](./pipeline-phase2-parallel.md)
  - 10 implementation steps
  - Performance testing strategy
  - Configuration examples

---

## Critical Implementation Details

### StepExecutor.execute_evaluation() Method (NEW)

Add to `src/vpsweb/core/executor.py`:

```python
async def execute_evaluation(
    self,
    candidates: List[InitialTranslation],
    input_data: Dict[str, Any],
    config: StepConfig,
) -> Dict[str, Any]:
    """
    Execute evaluation step to select best translation among candidates.

    Args:
        candidates: List of translation candidates to evaluate
        input_data: Evaluation input with candidates and criteria
        config: Step configuration (evaluation_reasoning)

    Returns:
        Dictionary with selected_index and rationale
    """
    logger.info(f"Evaluating {len(candidates)} translation candidates")

    # Render evaluation prompt
    system_prompt, user_prompt = await self._render_prompt_template(
        "evaluation", input_data, config
    )

    # Get provider and execute
    provider = await self._get_llm_provider(config)
    llm_response = await self._execute_llm_with_retry(
        provider, system_prompt, user_prompt, config, "evaluation"
    )

    # Parse evaluation output
    parsed = await self._parse_and_validate_output(
        "evaluation", llm_response.content, config
    )

    # Build result
    return {
        "output": parsed,
        "metadata": {
            "raw_response": {"content_preview": llm_response.content[:500]},
            "usage": {"tokens_used": llm_response.tokens_used},
        },
    }
```

### Stage Registration Pattern (UPDATED)

Instead of hardcoded if/elif chains, stages register their executor factories:

```python
# In stages.py - at module level
def _register_executor_factories():
    BaseTranslationStage.register_executor_factory("initial_translation", initial_translation_factory)
    BaseTranslationStage.register_executor_factory("editor_review", editor_review_factory)
    BaseTranslationStage.register_executor_factory("translator_revision", translator_revision_factory)

_register_executor_factories()
```

**Benefits:**
- Adding new stages doesn't require modifying BaseTranslationStage
- Dynamic dispatch based on step_name
- Each stage controls its own executor interaction

### Typed State vs Dict (UPDATED)

Using `PipelineState` TypedDict instead of `Dict[str, Any]`:

**Before (problematic):**
```python
context.shared_state["initial_translation"]  # What type? Runtime errors possible
```

**After (type-safe):**
```python
context.state: PipelineState  # Type checked
context.state["initial_translation"]  # InitialTranslation type
```

**Implementation Note:** Use `TypedDict` for minimal change while gaining type safety. Full dataclass could be Phase 2.

### Parallel Execution Edge Cases

1. **All parallel instances fail**: Mark stage as failed, stop pipeline
2. **Some succeed, some fail**: Continue with successful results, log failures
3. **Single instance (count=1)**: Acts as normal sequential execution (default behavior)
4. **Config generator**: Optional function to create different configs per parallel instance:
   ```python
   def generate_config(index: int) -> Dict:
       return {"temperature": 0.5 + (index * 0.2)}  # 0.5, 0.7, 0.9
   ```

### Evaluation Step Fallback

If `initial_translations` is empty (parallel_count=1):
- Evaluation uses single `initial_translation` as the only candidate
- Effectively becomes a validation step with rationale
- No errors, graceful degradation

### BBR Handling
BBR (Background Briefing Report) is only used in initial_translation stage. Must be retrieved from repository_service and passed through `context.state["bbr_content"]`.

### Strategy Dials
Translation strategy values (adaptation_level, repetition_policy, etc.) are stored in `system_config.main.translation_strategy`. Must be injected into `input_data` for each stage.

### Progress Callbacks
SSE (Server-Sent Events) for real-time progress must work identically. Pipeline's `progress_callback` wraps existing callback mechanism. For parallel stages, report each instance separately.

### Output Model Compatibility
Final `TranslationOutput` must have identical structure: workflow_id, input, initial_translation, editor_review, revised_translation, background_briefing_report, total_tokens, duration_seconds, workflow_mode, total_cost.

**NEW**: Also include `evaluation_result` in output containing selected_index and rationale.

### Manual Workflow Integration
Manual workflow needs:
- `get_current_stage_prompt()` - Returns rendered prompt for user to copy
- `submit_manual_stage_result()` - Accepts user's LLM response and continues
- Session state tracking for current stage index

## Rollback Plan

**Triggers:**
- Error rate increases >20%
- Duration increases >50%
- Any critical bug blocking workflow
- Evaluation produces consistently poor selections

**Procedure:**
1. Set `use_pipeline=False` in configuration
2. Restart application
3. Monitor return to baseline
4. Fix issues, re-test, retry migration

**Rollback Testing:**
- Before Phase 5, actually test the rollback procedure
- Verify that switching back to legacy workflow works seamlessly

## Files Summary (Two-Phase Approach)

### Phase 1: Modularization

**New Files (13)**
| File | Purpose |
|------|---------|
| `src/vpsweb/core/pipeline.py` | Pipeline, Stage, StageContext, ExecutionMode |
| `src/vpsweb/core/stages.py` | All 4 stage implementations |
| `src/vpsweb/core/pipeline_workflow.py` | Unified PipelineTranslationWorkflow |
| `src/vpsweb/core/workflow_factory.py` | Factory with feature flag |
| `config/prompts/evaluation.yaml` | Evaluation prompt template |
| `config/pipeline.yaml` | Pipeline configuration |
| `docs/performance-baseline.md` | Performance metrics |
| `tests/unit/test_pipeline.py` | Pipeline unit tests |
| `tests/unit/test_stages.py` | Stage unit tests |
| `tests/unit/test_executor_evaluation.py` | StepExecutor evaluation tests |
| `tests/integration/test_workflow_phase1.py` | Phase 1 integration tests |
| `tests/integration/test_output_parity.py` | Output comparison tests |

**Modified Files (8)**
| File | Changes |
|------|---------|
| `src/vpsweb/core/executor.py` | Add `execute_evaluation()` method |
| `src/vpsweb/models/translation.py` | Add `evaluation_result` field |
| `src/vpsweb/webui/services/services.py` | Use factory, update progress map |
| `src/vpsweb/webui/services/manual_workflow_service.py` | Integrate with pipeline |
| `config/task_templates.yaml` | Add `evaluation_reasoning` |
| `src/vpsweb/__main__.py` | Use factory |
| `src/vpsweb/webui/utils/translation_runner.py` | Use factory |
| `src/vpsweb/cli/services.py` | Use factory |

### Phase 2: Parallel Execution

**New Files (3)**
| File | Purpose |
|------|---------|
| `tests/unit/test_parallel_pipeline.py` | Parallel execution unit tests |
| `tests/unit/test_evaluation_multi.py` | Multi-candidate evaluation tests |
| `tests/integration/test_parallel_evaluation.py` | End-to-end parallel + eval tests |

**Modified Files (5)**
| File | Changes |
|------|---------|
| `src/vpsweb/core/pipeline.py` | Add ParallelStageConfig, parallel execution methods |
| `src/vpsweb/core/stages.py` | Update EvaluationStage for multi-candidate |
| `src/vpsweb/core/pipeline_workflow.py` | Add parallel_count support |
| `src/vpsweb/core/workflow_factory.py` | Add parallel_count parameter |
| `config/pipeline.yaml` | Update with parallel settings |

### Total Across Both Phases

| Metric | Phase 1 | Phase 2 | Total |
|--------|---------|---------|-------|
| New Files | 13 | 3 | 16 |
| Modified Files | 8 | 5 | 13 |
| Total Changes | 21 | 8 | 29 |

---

## Benefits (Two-Phase Approach)

### Phase 1 Benefits
1. **Eliminated Duplication**: StepConfigAdapter (3x), output extraction (3x), result creation (3x) → 1 each
2. **Easy to Add Stages**: Create new Stage subclass, add to Pipeline
3. **Unified Architecture**: Auto and Manual workflows share same Stage implementations
4. **Type-Safe State**: TypedDict for compile-time safety on state passing
5. **Centralized Error/Retry/Metrics**: Single place to handle all stages
6. **Better Testability**: Each stage independently testable
7. **Zero Breaking Change**: Feature flag allows instant rollback

### Phase 2 Benefits (Additional)
1. **Parallel Execution**: Run multiple translations in parallel, configurable count
2. **Performance Improvement**: ~2-3x speedup with parallel_count=3
3. **Automatic Selection**: Evaluation picks best translation from candidates
4. **Flexible Scaling**: Can adjust parallel_count based on needs

---

## Success Criteria Verification (Two-Phase)

| Criterion | Phase |
|-----------|-------|
| 1. Not break anything | Phase 1 (feature flag, gradual migration, rollback plan) |
| 2. Insert Evaluation step | Phase 1 (EvaluationStage class, always included) |
| 3. Parallel initial translations | Phase 2 (ParallelStageConfig, configurable count) |
| 4. Unified manual/auto | Phase 1 (ExecutionMode enum, shared Stage classes) |
| 5. Evaluation uses reasoning | Phase 1 (evaluation_reasoning template with deepseek_reasoner) |

---

## CORRECTIONS & ADDITIONAL IMPLEMENTATION DETAILS

### Critical Fixes to Plan

#### 1. Language Enum Handling (FIXED)
**Issue**: Plan originally used `.value` on Language enums
**Fact**: `Language` is a `str` enum (inherits from `str`), values are already "English", "Chinese", "Polish"
**Fix**: Use Language enums directly in all stages, NOT with `.value`

```python
# CORRECT:
"source_lang": translation_input.source_lang,  # Already "English", "Chinese", etc.
"target_lang": translation_input.target_lang,

# WRONG (do NOT use):
"source_lang": translation_input.source_lang.value,  # Would return "English" which is redundant
```

#### 2. Progress Calculation for 4 Stages (NEEDS UPDATE)
**Issue**: Current code uses 33%, 67%, 100% for 3 stages
**Fix**: Update to 25%, 50%, 75%, 100% for 4 stages

In `src/vpsweb/webui/services/services.py`, update the progress map:

```python
# BEFORE (3 stages):
progress_map = {
    "Initial Translation": 33,
    "Editor Review": 67,
    "Translator Revision": 100,
}

# AFTER (4 stages with Evaluation):
progress_map = {
    "Initial Translation": 25,
    "Translation Evaluation": 50,  # NEW
    "Editor Review": 75,
    "Translator Revision": 100,
}
```

### Additional Implementation Details

#### 3. TranslationOutput Model Update (REQUIRED)

Add to `src/vpsweb/models/translation.py`:

```python
class TranslationOutput(BaseModel):
    # ... existing fields ...

    # NEW: Evaluation results (safe to add - Optional field)
    evaluation_result: Optional[Dict[str, Any]] = Field(
        None,
        description="Evaluation results containing selected_index and rationale",
    )
```

Also update `to_dict()` and `from_dict()` methods to include the new field.

#### 4. Entry Points That Need Updates

These files create TranslationWorkflow instances and need parameter updates:

| File | Lines | Current Call | Required Update |
|------|-------|--------------|-----------------|
| `src/vpsweb/__main__.py` | ~427 | `TranslationWorkflow(config_facade=config_facade)` | Add factory call |
| `src/vpsweb/webui/services/services.py` | 997-1013 | `TranslationWorkflow(config_facade=..., ...)` | Add factory call |
| `src/vpsweb/webui/utils/translation_runner.py` | ~47 | `TranslationWorkflow()` | Add factory call |
| `src/vpsweb/cli/services.py` | 496-498 | `TranslationWorkflow(workflow_config, providers_config, workflow_mode)` | Add factory call |

**Pattern for updates:**

```python
# BEFORE:
workflow = TranslationWorkflow(config_facade=config_facade, ...)

# AFTER (use factory):
workflow = create_translation_workflow(
    config_facade=config_facade,
    workflow_mode=workflow_mode,
    use_pipeline=True,  # Feature flag
    execution_mode=ExecutionMode.AUTO,
    parallel_count=1,
    ...
)
```

#### 5. Manual Workflow Step Names

**Discovery**: Manual workflow uses step names like `"initial_translation_nonreasoning"`
**Plan assumption**: Uses simple names like `"initial_translation"`

**Resolution**: The step name in the plan refers to the pipeline stage name, while the task template name remains qualified. The ConfigFacade's `get_workflow_step_config()` should handle this mapping correctly.

#### 6. PipelineState TypedDict Considerations

**Discovery**: Codebase uses Pydantic models extensively, not TypedDict
**Recommendation**: Consider using Pydantic model instead of TypedDict for PipelineState:

```python
# Alternative (may be better for this codebase):
from pydantic import BaseModel

class PipelineState(BaseModel):
    translation_input: TranslationInput
    step_executor: "StepExecutor"
    bbr_content: Optional[str] = None
    initial_translation: Optional[InitialTranslation] = None
    initial_translations: Optional[List[InitialTranslation]] = None
    evaluation_result: Optional[Dict[str, Any]] = None
    editor_review: Optional[EditorReview] = None
    revised_translation: Optional[RevisedTranslation] = None
    current_stage_index: int = 0
    total_stages: int = 4
```

This provides better validation and is more consistent with the codebase's patterns.

#### 7. Progress Callback Details for Parallel Stages

When running parallel stages, report each instance separately:

```python
# In Pipeline._execute_parallel_stage():
for i, result in enumerate(successful_results):
    await self.progress_callback(
        f"{stage.display_name} #{i+1}",
        {"status": "completed", "parallel_index": i, "total_parallel": config.count}
    )
```

#### 8. Stage Context Creation Pattern

The plan's `PipelineState` initialization needs proper handling:

```python
# In PipelineTranslationWorkflow.execute():
context = StageContext(
    input_data=input_data.model_dump(),
    workflow_mode=self.workflow_mode,
    config_facade=self.config_facade,
    system_config=self.config_facade.main.model_dump(),
    state=PipelineState(
        translation_input=input_data,
        step_executor=self.step_executor,
        bbr_content=bbr_content,
        initial_translation=None,  # Required by TypedDict/Pydantic
        initial_translations=None,
        evaluation_result=None,
        editor_review=None,
        revised_translation=None,
        current_stage_index=0,
        total_stages=4,
    ),
    execution_mode=self.execution_mode,
)
```

### Summary of Required Changes to Plan

1. ✅ Language enum handling - FIXED (use directly, no .value)
2. ✅ Pipeline resume capability - FIXED (added resume_from_stage parameter)
3. ⚠️ Progress calculation - Documented (needs 4-stage mapping)
4. ⚠️ TranslationOutput model - Documented (needs Pydantic update)
5. ⚠️ Entry points - Documented (5 files need updates)
6. ✅ Manual workflow names - Clarified (stage name vs template name)
7. ⚠️ PipelineState - Alternative Pydantic approach suggested
8. ⚠️ Parallel progress - Reporting pattern documented
9. ⚠️ deepseek_reasoner validation - NEEDS ADDITION (see below)

---

## CRITICAL ISSUES (User Feedback)

### 🚨 Issue #1: Pipeline Resume Capability (FIXED Above)

**Problem**: The original `Pipeline.execute()` method executed stages from index 0 every time. In MANUAL mode with stateless HTTP requests, this would restart from stage 0 on each user interaction.

**Solution Implemented**:
- Added `resume_from_stage` parameter to `Pipeline.execute()`
- Track and use `context.state["current_stage_index"]` to skip completed stages
- Updated loop to start from the correct index: `if i < start_idx: continue`

**Usage Pattern for Manual Workflow**:
```python
# First request - starts at stage 0
result = await pipeline.execute(input_data, context)

# User submits response for stage 0

# Second request - resume from stage 1
next_stage = context.state["current_stage_index"] + 1
result = await pipeline.execute(input_data, context, resume_from_stage=next_stage)
```

### ⚠️ Issue #2: TranslationOutput Schema Update (Already Addressed)

**Status**: Already documented in corrections section. Ensure:
```python
evaluation_result: Optional[Dict[str, Any]] = Field(
    None,
    description="Evaluation results containing selected_index and rationale",
)
```

### ⚠️ Issue #3: deepseek_reasoner Dependency Validation

**Problem**: Evaluation step hardcodes `model_ref: "deepseek_reasoner"`. If user hasn't defined this model, pipeline crashes.

**Required Fix**: Add validation in `Pipeline.__init__` or `EvaluationStage`:

```python
# In PipelineTranslationWorkflow.__init__() or EvaluationStage
def _validate_evaluation_model(self):
    """Check if evaluation model exists in registry."""
    from ..services.config import ConfigFacade

    config = self.config_facade
    evaluation_config = config.get_workflow_step_config(self.workflow_mode, "evaluation")

    if not evaluation_config:
        raise ValueError(
            f"Evaluation step not configured for workflow mode: {self.workflow_mode}. "
            "Add 'evaluation_reasoning' to config/task_templates.yaml"
        )

    model_ref = evaluation_config.get("model_ref", "deepseek_reasoner")

    # Check if model exists in models.yaml
    try:
        provider = config.get_provider_for_model(model_ref)
        if not provider:
            raise ValueError(f"Model '{model_ref}' not found in models.yaml")
    except Exception as e:
        raise ValueError(
            f"Evaluation model '{model_ref}' not available. "
            f"Please add it to config/models.yaml or use a different model_ref. Error: {e}"
        )
```

### ⚠️ Issue #4: Parallel Progress Reporting UI Jitter

**Problem**: Rapid-firing progress events for each parallel instance might cause UI jitter.

**Mitigation Strategies**:

1. **Aggregate Progress** (Recommended):
```python
# In Pipeline._execute_parallel_stage():
total_parallel = config.count
completed = 0

for i, result in enumerate(successful_results):
    completed += 1
    # Only report progress at milestones
    if completed == total_parallel or completed % max(1, total_parallel // 3) == 0:
        await self.progress_callback(
            stage.display_name,
            {
                "status": "running",
                "parallel_progress": f"{completed}/{total_parallel} completed",
                "progress_percent": int((completed / total_parallel) * 100),
            }
        )
```

2. **Batch Reporting**:
```python
# Report only when all parallel instances complete
await self.progress_callback(
    stage.display_name,
    {
        "status": "completed",
        "parallel_count": config.count,
        "successful": len(successful_results),
        "failed": failed_count,
    }
)
```

3. **Frontend Compatibility Check**:
   - Current task_service.update_task_progress() signature supports `details` dict
   - Add `parallel_substeps` key to details for frontend to handle specially
   - Frontend can choose to display as indeterminate progress or step counter

**Recommended Approach**: Use aggregation strategy #1 with milestones at 33%, 67%, 100% of parallel completion.

---

### Final Status of All Critical Issues

| Issue | Status | Action Taken |
|-------|--------|--------------|
| 1. Pipeline Resume Capability | ✅ FIXED | Added `resume_from_stage` parameter to `Pipeline.execute()` |
| 2. TranslationOutput Schema | ⚠️ DOCUMENTED | Ensure `Optional[Dict[str, Any]]` field in Pydantic model |
| 3. deepseek_reasoner Validation | ✅ DOCUMENTED | Added `_validate_evaluation_model()` code pattern |
| 4. Parallel Progress Jitter | ✅ FIXED | Added aggregated progress reporting in `_execute_parallel_stage()` |

---

## Implementation Ready

All critical issues have been addressed:
- ✅ Manual workflow can now resume from any stage
- ✅ Parallel progress reports at milestones (not rapid-fire)
- ✅ Model validation pattern documented
- ✅ Language enum handling corrected (no .value needed)
- ✅ Progress calculation documented (25/50/75/100 for 4 stages)
- ✅ Entry point integration documented
- ✅ TranslationOutput field addition pattern documented

**The plan is now ready for implementation.**
