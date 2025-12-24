# Manual Translation Workflow Implementation Plan (v2)

## 1. Objective

This document outlines the plan to implement a "manual" translation workflow in the vpsWeb application. This new workflow will allow users to manually interact with Large Language Models (LLMs) through web chats, providing a cost-effective and flexible way to test different models and fine-tune translations.

The core idea is to leverage the existing prompt generation and response parsing capabilities of the application, but replace the direct API calls to LLMs with a user-mediated copy-paste process.

## 2. High-Level Workflow

The user experience for the manual workflow will be as follows:

1.  The user selects the "Manual" workflow mode on the poem detail page.
2.  The UI presents a populated prompt for the first step of the translation (e.g., Initial Translation).
3.  The user copies the prompt and pastes it into an external LLM web chat.
4.  The user copies the LLM's response from the web chat.
5.  The user pastes the response back into the vpsWeb application, provides the name of the LLM used, and submits.
6.  The application parses the response and presents the populated prompt for the next step (e.g., Editor Review).
7.  This process repeats until all workflow steps are complete.
8.  **Important:** Only upon successful completion of all steps will the final translation and all intermediate steps be saved to the database and a JSON file. If the workflow is abandoned or fails, no data will be persisted.

## 3. Implementation Details

This plan emphasizes reusing existing components to minimize development effort.

### 3.1. Backend Changes

#### 3.1.1. WorkflowMode Enum

The `WorkflowMode` enum will be updated to include the `MANUAL` option.

*   **File:** `src/vpsweb/models/config.py`
*   **Change:** Add `MANUAL = "manual"` to the `WorkflowMode` enum.

```python
class WorkflowMode(str, Enum):
    """Supported workflow modes."""

    REASONING = "reasoning"
    NON_REASONING = "non_reasoning"
    HYBRID = "hybrid"
    MANUAL = "manual"
```

#### 3.1.2. Database Schema

No changes are needed for the database schema. The existing `model_name` field in the `TranslationWorkflowStep` table will be used to store the user-provided LLM model name.

#### 3.1.3. API Endpoints

New API endpoints will be created to manage the manual workflow. A new file is recommended to keep the logic organized.

*   **New File:** `src/vpsweb/webui/api/manual_workflow.py`
*   **Endpoints:**
    *   `POST /api/v1/poems/{poem_id}/translate/manual/start`
        *   **Description:** Initializes the manual workflow for a given poem.
        *   **Request Body:**
            ```json
            {
                "target_lang": "string"
            }
            ```
        *   **Response Body:**
            ```json
            {
                "step": "initial_translation",
                "prompt": "string"
            }
            ```
    *   `POST /api/v1/poems/{poem_id}/translate/manual/step/{step_name}`
        *   **Description:** Submits the user's input for a workflow step. This endpoint will be stateful on the backend, holding the intermediate results in memory until the final step is complete.
        *   **Request Body:**
            ```json
            {
                "llm_response": "string",
                "llm_model_name": "string",
                "session_id": "string" // A unique ID to track the user's session
            }
            ```
        *   **Response Body (for intermediate steps):**
            ```json
            {
                "step": "next_step_name",
                "prompt": "string"
            }
            ```
        *   **Response Body (for final step):**
            ```json
            {
                "status": "completed",
                "message": "Manual workflow completed successfully."
            }
            ```
*   **Action:** The new router from `manual_workflow.py` will be included in `src/vpsweb/webui/main.py`.

#### 3.1.4. Workflow Service Logic

A new service will be created to encapsulate the logic for the manual workflow. This service will:

1.  On `start`, generate a unique session ID.
2.  Use the existing prompt services to generate the populated prompts for each step, reusing the prompt templates defined for the **hybrid workflow**.
3.  Store the results of each step in memory, associated with the session ID.
4.  On submission of the final step, use the existing `CRUDTranslationWorkflowStep` and other services to save the entire workflow's results to the database and generate the JSON output file.
5.  If a user abandons the workflow, the in-memory results will be discarded.

### 3.2. Frontend Changes

#### 3.2.1. Poem Detail Page

The main UI changes will be in the poem detail page.

*   **File:** `src/vpsweb/webui/web/templates/poem_detail.html`
*   **Changes:**
    1.  Add "Manual" to the "Workflow Mode" dropdown.
    2.  Add a new UI section that is hidden by default and becomes visible when "Manual" mode is selected.

*   **HTML Snippet for Manual Workflow UI:**

```html
<!-- Manual Workflow Section (initially hidden) -->
<div id="manual-workflow-section" class="hidden mt-4">
    <h3 class="text-lg font-medium text-gray-900" id="manual-workflow-step-title"></h3>
    
    <div>
        <label for="manual-workflow-prompt" class="block text-sm font-medium text-gray-700">Prompt to copy:</label>
        <textarea id="manual-workflow-prompt" rows="10" class="w-full px-3 py-2 border border-gray-300 rounded-md" readonly></textarea>
    </div>

    <div class="mt-4">
        <label for="manual-llm-model-name" class="block text-sm font-medium text-gray-700">LLM Model Name:</label>
        <input type="text" id="manual-llm-model-name" class="w-full px-3 py-2 border border-gray-300 rounded-md">
    </div>

    <div class="mt-4">
        <label for="manual-llm-response" class="block text-sm font-medium text-gray-700">Paste LLM response here:</label>
        <textarea id="manual-llm-response" rows="10" class="w-full px-3 py-2 border border-gray-300 rounded-md"></textarea>
    </div>

    <div class="mt-4">
        <button id="submit-manual-step-btn" class="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700">
            Submit Step
        </button>
    </div>
</div>
```

#### 3.2.2. JavaScript Logic

New JavaScript functions will be added to `poem_detail.html` to handle the manual workflow.

*   **State Management:** A JavaScript variable will hold the current manual workflow `session_id`.
*   **Functions:**
    *   A function to show/hide the `manual-workflow-section` based on the selected workflow mode.
    *   `startManualWorkflow()`: Called when the user starts the manual workflow. This will call the `.../manual/start` endpoint, store the `session_id` from the response, and populate the UI with the first prompt.
    *   `submitManualStep()`: Called when the user submits a step. This will gather the data from the form, include the `session_id` in the request, call the `.../manual/step/{step_name}` endpoint, and update the UI with the next prompt or a completion message.

### 3.3. Configuration

No changes are needed in `config/default.yaml` as the manual workflow will reuse the `hybrid_workflow` configuration for its prompt templates.

## 4. Testing Strategy

*   **Unit Tests:**
    *   New unit tests will be written for the new API endpoints in `src/vpsweb/webui/api/manual_workflow.py`.
    *   Tests will be added for the manual workflow service logic to ensure correct prompt generation, response parsing, and final database operations.
*   **End-to-End Testing:**
    *   Manually test the entire workflow from the web UI.
    *   Verify that abandoning the workflow mid-way does *not* save any data.
    *   Verify that upon successful completion, the data is correctly saved in the database.
    *   Verify that the final JSON output is generated and matches the format of the automated workflows.

## 5. Summary of New/Modified Files

*   `docs/manual_workflow_implementation_plan.md` (this file)
*   `src/vpsweb/models/config.py` (modified)
*   `src/vpsweb/webui/api/manual_workflow.py` (new)
*   `src/vpsweb/webui/main.py` (modified to include new router)
*   `src/vpsweb/webui/web/templates/poem_detail.html` (modified)
*   A new service file for manual workflow orchestration (e.g., `src/vpsweb/services/manual_workflow.py`)
