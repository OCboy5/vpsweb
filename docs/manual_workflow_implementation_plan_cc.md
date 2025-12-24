# Manual Translation Workflow Implementation Plan (v3)

## Executive Summary

This document provides a comprehensive implementation plan for adding a "manual" workflow mode to the VPSWeb poetry translation system. The manual workflow allows users to interact with external LLM services through copy-paste operations, providing a cost-effective way to test various models without requiring API integrations.

## Design Philosophy

1. **Maximum Reuse**: Leverage existing prompt templates, parsers, database schema, and UI patterns
2. **Session-Based Execution**: Maintain workflow state in memory, only persisting successful completions
3. **Seamless Integration**: Follow existing architectural patterns for consistency
4. **Minimal Code Changes**: Implement with the fewest possible modifications to the codebase

## Implementation Architecture

### High-Level Flow

```
User selects Manual mode → Initialize session → Display Step 1 prompt
       ↓
User copies prompt to external LLM → Gets response → Pastes back with model name
       ↓
System validates response → Stores in session → Displays Step 2 prompt
       ↓
... (repeat for all 3 steps) ...
       ↓
Final step complete → Save to database → Generate JSON file
```

## Detailed Implementation Plan

### Phase 1: Backend Model Updates

#### 1.1 Add Manual Workflow Mode
**File**: `src/vpsweb/models/config.py`
- Add `MANUAL = "manual"` to the `WorkflowMode` enum (line 101)

#### 1.2 Database Saving Strategy
For manual workflows:
- **AILog entry**: Create with `workflow_mode="manual"` and `model_name="user-specified"` (required field, placeholder value)
- **TranslationWorkflowStep entries**: Store the actual model names entered by the user in the `model_info` field for each step

### Phase 2: Core Service Implementation

#### 2.1 Create Manual Workflow Service
**New File**: `src/vpsweb/webui/services/manual_workflow_service.py`

```python
class ManualWorkflowService:
    """Service for managing manual translation workflows"""

    def __init__(self, prompt_service, output_parser, workflow_service):
        self.prompt_service = prompt_service
        self.output_parser = output_parser
        self.workflow_service = workflow_service
        self.sessions = {}  # In-memory session storage (no expiration needed)

    async def start_session(self, poem_id: str, target_lang: str) -> dict:
        """Initialize a new manual workflow session"""
        # ... implementation

    async def submit_step(self, session_id: str, step_name: str,
                         llm_response: str, model_name: str) -> dict:
        """Process user-submitted step response"""
        # ... implementation

    async def complete_workflow(self, session_id: str) -> dict:
        """Save completed workflow to database using existing WorkflowServiceV2"""
        session = self.sessions[session_id]

        # Transform session data to match expected format
        # Create AILog with model_name="user-specified"
        # Create TranslationWorkflowStep entries with user-provided model names

        # Call existing save method
        await self.workflow_service._save_translation_to_db(...)

        # Delete session after successful save
        del self.sessions[session_id]
```

#### 2.2 Reuse Hybrid Task Template Sequence
The manual workflow will use the same 3-step sequence as hybrid mode:
1. Step 1: `initial_translation_nonreasoning` template
2. Step 2: `editor_review_nonreasoning` template
3. Step 3: `translator_revision_nonreasoning` template

### Phase 3: API Endpoints

#### 3.1 Create Manual Workflow API Router
**New File**: `src/vpsweb/webui/api/manual_workflow.py`

```python
# Endpoints to implement:
POST /api/v1/poems/{poem_id}/translate/manual/start
    - Initialize manual workflow session
    - Response: { session_id, step_name, populated_prompt }

POST /api/v1/poems/{poem_id}/translate/manual/step/{step_name}
    - Submit user response for current step
    - Response: { next_step_name, populated_prompt } or { status: "completed" }

GET /api/v1/poems/{poem_id}/translate/manual/session/{session_id}
    - Get current session state
    - Response: { current_step, session_data }
```

#### 3.2 Register New Router
**File**: `src/vpsweb/webui/main.py`
- Add: `app.include_router(manual_workflow_router, prefix="/api/v1", tags=["manual"])`

### Phase 4: Frontend Implementation

#### 4.1 Update Workflow Mode Dropdown
**File**: `src/vpsweb/webui/web/templates/poem_detail.html`
- Add `<option value="manual">Manual Mode</option>` to workflow mode select (line 120)

#### 4.2 Add Manual Workflow UI Section
Add after line 221 (workflow progress section):

```html
<!-- Manual Workflow Section (initially hidden) -->
<div id="manual-workflow-section" class="hidden mt-6 p-4 bg-gray-50 rounded-lg">
    <h3 class="text-lg font-medium text-gray-900 mb-4">
        Manual Translation Workflow
    </h3>

    <!-- Step Indicator -->
    <div class="mb-4">
        <span class="text-sm font-medium text-gray-700">Current Step: </span>
        <span id="manual-current-step" class="text-sm font-bold text-blue-600"></span>
    </div>

    <!-- Prompt Display -->
    <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-2">
            Prompt to Copy:
        </label>
        <textarea id="manual-prompt-display"
                  rows="15"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm bg-white"
                  readonly></textarea>
        <button onclick="copyPromptToClipboard()"
                class="mt-2 px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300">
            Copy to Clipboard
        </button>
    </div>

    <!-- Response Input -->
    <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-2">
            LLM Model Used:
        </label>
        <input type="text"
               id="manual-model-name"
               class="w-full px-3 py-2 border border-gray-300 rounded-md"
               placeholder="e.g., GPT-4, Claude-3, etc.">
    </div>

    <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-2">
            Paste LLM Response:
        </label>
        <textarea id="manual-response-input"
                  rows="15"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
                  placeholder="Paste the complete response from the LLM here..."></textarea>
    </div>

    <!-- Submit Button -->
    <button id="manual-submit-step-btn"
            onclick="submitManualStep()"
            class="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
        Submit Step
    </button>
</div>
```

#### 4.3 Add JavaScript Functions
Add to the existing script section in `poem_detail.html`:

```javascript
// Manual workflow state
let manualSessionId = null;
let manualCurrentStep = null;

function showManualWorkflowSection() {
    document.getElementById('workflow-progress').classList.add('hidden');
    document.getElementById('manual-workflow-section').classList.remove('hidden');
}

function hideManualWorkflowSection() {
    document.getElementById('manual-workflow-section').classList.add('hidden');
}

async function startManualWorkflow() {
    const poemId = window.location.pathname.split('/').pop();
    const targetLang = document.getElementById('target-language').value;

    try {
        const response = await fetch(`/api/v1/poems/${poemId}/translate/manual/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_lang: targetLang })
        });

        const data = await response.json();
        manualSessionId = data.session_id;
        manualCurrentStep = data.step_name;

        updateManualWorkflowUI(data);
        showManualWorkflowSection();
    } catch (error) {
        console.error('Error starting manual workflow:', error);
        alert('Failed to start manual workflow');
    }
}

function updateManualWorkflowUI(data) {
    document.getElementById('manual-current-step').textContent =
        data.step_name.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
    document.getElementById('manual-prompt-display').value = data.prompt;
    document.getElementById('manual-response-input').value = '';
    document.getElementById('manual-model-name').value = '';
}

async function submitManualStep() {
    const poemId = window.location.pathname.split('/').pop();
    const response = document.getElementById('manual-response-input').value;
    const modelName = document.getElementById('manual-model-name').value;

    if (!response.trim()) {
        alert('Please paste the LLM response');
        return;
    }

    if (!modelName.trim()) {
        alert('Please enter the LLM model name');
        return;
    }

    try {
        const submitBtn = document.getElementById('manual-submit-step-btn');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Processing...';

        const apiResponse = await fetch(
            `/api/v1/poems/${poemId}/translate/manual/step/${manualCurrentStep}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: manualSessionId,
                    llm_response: response,
                    llm_model_name: modelName
                })
            }
        );

        const data = await apiResponse.json();

        if (data.status === 'completed') {
            alert('Manual workflow completed successfully! Translation has been saved.');
            location.reload();
        } else {
            manualCurrentStep = data.step_name;
            updateManualWorkflowUI(data);
        }
    } catch (error) {
        console.error('Error submitting step:', error);
        alert('Failed to submit step. Please try again.');
    } finally {
        const submitBtn = document.getElementById('manual-submit-step-btn');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Step';
    }
}

function copyPromptToClipboard() {
    const promptTextarea = document.getElementById('manual-prompt-display');
    promptTextarea.select();
    document.execCommand('copy');

    // Show brief confirmation
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = originalText, 2000);
}
```

### Phase 5: Integration Points

#### 5.1 Update startWorkflow() Function
Modify the existing `startWorkflow()` function in `poem_detail.html`:

```javascript
// Add at the beginning of startWorkflow()
const workflowMode = document.getElementById('workflow-mode').value;

if (workflowMode === 'manual') {
    startManualWorkflow();
    return;
}

// Rest of existing function for auto workflows...
```

#### 5.2 Leverage Existing Components

1. **Prompt Generation**: Use existing `PromptService` from `src/vpsweb/services/prompts.py`
2. **Response Parsing**: Reuse `OutputParser` classes from `src/vpsweb/services/parser.py`
3. **Database Operations**: Use existing `WorkflowServiceV2` for final save
4. **File Output**: Use existing `save_translation_with_poet_dir` function from `src/vpsweb/utils/storage.py`

### Phase 6: Session Management

#### 6.1 Session Data Structure
```python
{
    "session_id": "uuid",
    "poem_id": "poem_id",
    "target_lang": "string",
    "current_step": "step_name",
    "completed_steps": {
        "step_name": {
            "prompt": "string",
            "response": "string",
            "model_name": "string",
            "parsed_data": {},
            "timestamp": "datetime"
        }
    },
    "created_at": "datetime"
}
```

#### 6.2 Session Lifecycle
- **Creation**: When user starts manual workflow
- **Update**: After each successful step submission
- **Completion**: After final step, save to database and delete session
- **Note**: No expiration mechanism needed - sessions are in-memory only and cleared on server restart

### Phase 7: Error Handling & Validation

#### 7.1 Response Validation
- Validate XML structure using existing parsers
- Check for required fields in each step
- Provide clear error messages for invalid responses

#### 7.2 Edge Cases
- Handle user closing browser mid-workflow (session cleanup)
- Manage duplicate session submissions
- Handle very large responses

### Phase 8: Testing Strategy

#### 8.1 Unit Tests
- Test `ManualWorkflowService` methods
- Test prompt generation accuracy
- Test response parsing with various LLM outputs

#### 8.2 Integration Tests
- Test complete workflow with sample data
- Test session persistence and cleanup
- Test database saving on completion

#### 8.3 Manual Testing Checklist
- [ ] Manual mode appears in dropdown
- [ ] Session initializes correctly
- [ ] Prompts display correctly with populated variables
- [ ] Copy to clipboard works
- [ ] Response submission works
- [ ] Progress through all 3 steps
- [ ] Successful completion saves to database
- [ ] JSON file generation matches format
- [ ] Abandoned workflows don't save

### Phase 9: Deployment Considerations

#### 9.1 Configuration
- No config file changes needed (reuses hybrid templates)
- Consider adding session timeout configuration

#### 9.2 Monitoring
- Add logging for manual workflow operations
- Track session creation/completion metrics

### Phase 10: Future Enhancements

1. **Response Templates**: Save common responses for quick reuse
2. **Model History**: Track which models work best for different poem types
3. **Batch Processing**: Allow multiple poems in one manual session
4. **Export/Import**: Allow saving and loading manual workflow progress

## Implementation Timeline

1. **Day 1**: Backend model and service implementation
2. **Day 2**: API endpoints and session management
3. **Day 3**: Frontend UI implementation
4. **Day 4**: Integration testing and bug fixes
5. **Day 5**: Documentation and deployment

## Summary of Files to Modify/Create

### New Files:
- `src/vpsweb/webui/api/manual_workflow.py`
- `src/vpsweb/webui/services/manual_workflow_service.py`
- `tests/unit/test_manual_workflow_service.py`
- `tests/integration/test_manual_workflow_api.py`

### Modified Files:
- `src/vpsweb/models/config.py` (add MANUAL enum)
- `src/vpsweb/webui/main.py` (register new router)
- `src/vpsweb/webui/web/templates/poem_detail.html` (UI updates)

## Comparison with Existing Plan

### Pros of This Approach:
1. **Minimal Code Changes**: Reuses existing components to the maximum extent
2. **Session-Based**: Only saves successful completions, as required
3. **Consistent UX**: Follows existing UI patterns and styling
4. **Simple Architecture**: No complex state machines or workflow modifications

### Cons/Trade-offs:
1. **In-Memory Sessions**: Sessions are lost on server restart (acceptable for manual workflows)
2. **Single Session per Poem**: Users can't have multiple manual workflows for the same poem simultaneously

### Key Differences from Original Plan:
1. **No New Config Files**: Reuses hybrid configuration instead of creating new manual config
2. **Simplified API**: Uses RESTful endpoints instead of complex state management
3. **Better UI Integration**: Seamlessly integrates with existing poem detail page
4. **Leverages Existing Parsers**: Uses the same XML parsers as auto workflows

## Conclusion

This implementation plan provides a minimal-effort approach to adding manual workflow capabilities while maintaining consistency with the existing VPSWeb architecture. The solution reuses maximum existing components and provides a clean, user-friendly interface for manual LLM interactions.