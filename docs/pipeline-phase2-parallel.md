# Phase 2: Parallel Execution Support

## Goal
Enable running multiple initial translations in parallel, with automatic aggregation and best-selection via the Evaluation step.

**This phase builds on Phase 1's modular architecture and adds parallel execution capabilities.**

## Prerequisites
✅ Phase 1 complete and validated in production
✅ Pipeline/Stage architecture stable
✅ Evaluation step working correctly

## Success Criteria
1. ✅ Can run N translations in parallel (configurable)
2. ✅ Results from parallel instances are aggregated correctly
3. ✅ Evaluation step selects best translation from candidates
4. ✅ Progress reporting doesn't cause UI jitter
5. ✅ Performance scales with parallel_count
6. ✅ No regressions in existing functionality

## What's Included
- ParallelStageConfig class
- `Pipeline._execute_parallel_stage()` method
- Aggregated progress reporting (milestones at 33%, 67%, 100%)
- Configurable parallel_count via config/pipeline.yaml
- Multi-candidate evaluation (selects best from N translations)

## What's NOT Changed
- Core Pipeline/Stage architecture (from Phase 1)
- ExecutionMode enum (from Phase 1)
- Individual stage implementations (from Phase 1)
- Manual workflow resume logic (from Phase 1)

---

## Architecture Changes

(See `pipeline-refactor-plan.md` for full code details)

### Key Updates for Phase 2:
1.  **Pipeline**: Adds `ParallelStageConfig` and `_execute_parallel_stage` logic.
2.  **EvaluationStage**: Updates `execute` method to handle `initial_translations` list (multiple candidates) vs single `initial_translation`.
3.  **Config**: Adds `pipeline.yaml` with `parallel_count` settings.

---

## Implementation Steps

### Step 1: Add Parallel Infrastructure
**File to Modify:**
1. `src/vpsweb/core/pipeline.py` - Add ParallelStageConfig, _expand_stages(), _execute_parallel_stage()

**Tests to Create:**
1. `tests/unit/test_parallel_pipeline.py` - Parallel execution unit tests

### Step 2: Update PipelineState
**File to Modify:**
1. `src/vpsweb/core/pipeline.py` - Add `initial_translations` field

### Step 3: Update EvaluationStage
**File to Modify:**
1. `src/vpsweb/core/stages.py` - Update to select from multiple candidates

**Tests to Create:**
1. `tests/unit/test_evaluation_multi.py` - Multi-candidate evaluation tests

### Step 4: Update PipelineTranslationWorkflow
**File to Modify:**
1. `src/vpsweb/core/pipeline_workflow.py` - Add parallel_count parameter and parallel_configs

### Step 5: Add Configuration
**File to Create:**
1. `config/pipeline.yaml` - Already created in Phase 1, update with parallel settings

### Step 6: Update Factory
**File to Modify:**
1. `src/vpsweb/core/workflow_factory.py` - Add parallel_count parameter

### Step 7: Update Frontend Progress Callback Logic
**File to Modify:**
1. `src/vpsweb/webui/services/services.py`:
   - In `_execute_workflow`'s internal `progress_callback` function:
   - **CRITICAL**: Modify the logic to respect `progress` passed in `details` (from the pipeline) if it exists.
   - Currently, it hardcodes `progress = progress_map.get(step_name, 0)`.
   - Change to: `progress = details.get("progress_percent") or progress_map.get(step_name, 0)`.
   - This ensures granular progress from parallel execution (e.g., "33/100 completed") is reflected in the UI, rather than being stuck at a fixed percentage.

### Step 8: Integration Testing
**Tests to Create:**
1. `tests/integration/test_parallel_evaluation.py` - End-to-end parallel + eval tests

### Step 9: Performance Testing
**Actions:**
1. Run with parallel_count=1 (baseline)
2. Run with parallel_count=2, measure speedup
3. Run with parallel_count=3, measure speedup
4. Document results in `docs/performance-baseline.md`

### Step 10: Gradual Rollout
1. Start with parallel_count=1 (no change)
2. Test parallel_count=2 in development
3. Test parallel_count=3 in development
4. Gradually increase in production based on performance

### Step 11: Monitor and Optimize
1. Monitor token usage with parallel_count > 1
2. Monitor error rates (should be isolated per instance)
3. Adjust progress milestones if UI jitter observed
4. Document optimal parallel_count per workflow mode

---

## Files Summary for Phase 2

### New Files (3)
| File | Purpose |
|------|---------|
| `tests/unit/test_parallel_pipeline.py` | Parallel execution unit tests |
| `tests/unit/test_evaluation_multi.py` | Multi-candidate evaluation tests |
| `tests/integration/test_parallel_evaluation.py` | End-to-end parallel + eval tests |

### Modified Files (5)
| File | Changes |
|------|---------|
| `src/vpsweb/core/pipeline.py` | Add ParallelStageConfig, _expand_stages(), _execute_parallel_stage() |
| `src/vpsweb/core/stages.py` | Update EvaluationStage for multi-candidate selection |
| `src/vpsweb/core/pipeline_workflow.py` | Add parallel_count parameter and parallel_configs |
| `src/vpsweb/core/workflow_factory.py` | Add parallel_count parameter |
| `src/vpsweb/webui/services/services.py` | Update `progress_callback` to support dynamic progress |
| `config/pipeline.yaml` | Update with parallel settings (if not set in Phase 1) |

---

## Rollback Plan

**Triggers:**
- Parallel execution causes errors
- Token usage too high
- No performance improvement
- UI jitter despite aggregation

**Procedure:**
1. Set `parallel_count=1` in config
2. Restart application
3. Monitor return to baseline
4. Fix issues, re-test