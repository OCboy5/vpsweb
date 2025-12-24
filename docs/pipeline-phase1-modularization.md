# Phase 1: Workflow Modularization

## Goal
Refactor the translation workflow from duplicated step methods to a modular Pipeline/Stage architecture, making it easy to add/remove workflow steps.

**This phase focuses on architecture and flexibility. Parallel execution is deferred to Phase 2.**

## Success Criteria
1. ✅ Can add a new workflow step by creating a Stage class and adding to pipeline
2. ✅ Manual and auto workflows share the same Stage implementations
3. ✅ Existing tests still pass (no regressions)
4. ✅ No performance degradation
5. ✅ Evaluation step integrated (runs as single-instance validation)

## What's Included
- Pipeline/Stage architecture
- ExecutionMode enum (AUTO/MANUAL)
- EvaluationStage (single instance, validates translation)
- Unified manual/auto workflow
- Resume capability for manual workflow
- Factory pattern with feature flag
- **NOT** parallel execution (always count=1)

## What's Deferred to Phase 2
- ParallelStageConfig class
- `Pipeline._execute_parallel_stage()` method
- Aggregated progress reporting for parallel stages
- Configurable parallel_count
- Multiple translation candidates

---

## Phase 1 Architecture

### Core Design Principles
1. **Stage-based pipeline**: Each workflow step is a Stage class
2. **Unified execution**: Single Pipeline for both AUTO and MANUAL modes
3. **Resume capability**: Pipeline can resume from any stage (for manual workflow)
4. **Stage registration**: Dynamic dispatch instead of hardcoded if/elif chains
5. **Typed state**: Type-safe state passing between stages

### New File: `src/vpsweb/core/pipeline.py`

(See `pipeline-refactor-plan.md` for full code)

---

## Implementation Steps

### Step 1: Create Core Pipeline Components
**Files to Create:**
1. `src/vpsweb/core/pipeline.py`
2. `src/vpsweb/core/stages.py`

**Tests to Create:**
1. `tests/unit/test_pipeline.py` - Pipeline unit tests
2. `tests/unit/test_stages.py` - Stage unit tests

### Step 2: Add StepExecutor Evaluation Support
**File to Modify:**
1. `src/vpsweb/core/executor.py` - Add `execute_evaluation()` method

**Tests to Create:**
1. `tests/unit/test_executor_evaluation.py`

### Step 3: Create Unified Workflow
**Files to Create:**
1. `src/vpsweb/core/pipeline_workflow.py` - Unified PipelineTranslationWorkflow
2. `src/vpsweb/core/workflow_factory.py` - Factory with feature flag

**Tests to Create:**
1. `tests/integration/test_workflow_phase1.py` - Phase 1 integration tests

### Step 4: Add Evaluation Configuration
**Files to Create:**
1. `config/prompts/evaluation.yaml`
2. `config/pipeline.yaml`

**Files to Modify:**
1. `config/task_templates.yaml` - Add `evaluation_reasoning` template

### Step 5: Update TranslationOutput Model
**File to Modify:**
1. `src/vpsweb/models/translation.py` - Add `evaluation_result` field (Optional)

### Step 6: Update Entry Points & Refactor WorkflowServiceV2
**Files to Modify:**
1. `src/vpsweb/__main__.py` - Use factory
2. `src/vpsweb/webui/utils/translation_runner.py` - Use factory
3. `src/vpsweb/cli/services.py` - Use factory
4. `src/vpsweb/webui/services/services.py` - **Major Refactor**:
   - Replace manual `WorkflowStep` construction loop with `create_translation_workflow` factory call.
   - Remove legacy config fallback logic that constructs steps manually.
   - Ensure `TranslationWorkflow` instantiation uses the factory.

### Step 7: Update Frontend Progress Handling
**File to Modify:**
1. `src/vpsweb/webui/services/services.py` - `_execute_workflow` method:
   - Update `step_states` initialization to include "Translation Evaluation".
   - Update `progress_map` to include "Translation Evaluation" (suggested map: Initial=25, Eval=50, Editor=75, Revision=100).

### Step 8: Integrate Manual Workflow (Phase 1 only)
**File to Modify:**
1. `src/vpsweb/webui/services/manual_workflow_service.py`:
   - Refactor `start_session` to initialize `PipelineTranslationWorkflow` in MANUAL mode.
   - Refactor `submit_step` to call `pipeline.execute(..., resume_from_stage=...)`.
   - Ensure session state tracks `current_stage_index` matching the pipeline's state.

### Step 9: Establish Performance Baseline
**Files to Create:**
1. `docs/performance-baseline.md`

**Tests to Create:**
1. `tests/integration/test_output_parity.py` - Compare old vs new outputs

### Step 10: Gradual Migration
1. Set `use_pipeline=True` in development
2. Run tests, monitor metrics
3. Compare outputs
4. Fix issues
5. Rollback if needed

### Step 11: Default to Pipeline
1. Default `use_pipeline=True`
2. Monitor production
3. Remove legacy code after 2 weeks

---

## Files Summary for Phase 1

### New Files (13)
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

### Modified Files (8)
| File | Changes |
|------|---------|
| `src/vpsweb/core/executor.py` | Add `execute_evaluation()` method |
| `src/vpsweb/models/translation.py` | Add `evaluation_result` field |
| `src/vpsweb/webui/services/services.py` | Use factory, update progress map, refactor initialization |
| `src/vpsweb/webui/services/manual_workflow_service.py` | Integrate with pipeline |
| `config/task_templates.yaml` | Add `evaluation_reasoning` |
| `src/vpsweb/__main__.py` | Use factory |
| `src/vpsweb/webui/utils/translation_runner.py` | Use factory |
| `src/vpsweb/cli/services.py` | Use factory |

---

## Rollback Plan

**Triggers:**
- Error rate increases >20%
- Duration increases >50%
- Any critical bug blocking workflow
- Tests failing

**Procedure:**
1. Set `use_pipeline=False`
2. Restart application
3. Monitor return to baseline
4. Fix issues, re-test, retry