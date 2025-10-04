### **Product Specifications Document (PSD): Vox Poetica Translation Studio (`vpsweb`)**

**Version:** 1.0
**Date:** 2025-10-03

#### 1. Overview

**1.1. Project Name:** Vox Poetica Translation Studio (`vpsweb`)

**1.2. Project Goal:** To create a configurable, script-based Python application that replicates the multi-step poetry translation workflow defined in the Dify "Vox Poetica Translation Studio" application. The project aims to produce high-quality, professional translations of poetry between various languages (initially English and Chinese) by simulating a collaborative process involving an initial translator, an editor, and a final revision by the translator.

**1.3. Scope:**
*   **In Scope:**
    *   A set of Python scripts to orchestrate the three-step translation workflow (Translate -> Review -> Revise).
    *   External configuration for all operational parameters, including LLM models, API endpoints, and prompts.
    *   Structured JSON-based input and output for each step of the workflow.
    *   A clear, well-documented project structure suitable for a GitHub repository.
    *   Initial support for the LLM providers and models specified in the Dify workflow (Tongyi Qwen, DeepSeek).
*   **Out of Scope (for Version 1.0):**
    *   A web-based user interface (UI) or API. The project will be executed via command-line scripts.
    *   A database for storing translation history. Storage will be file-based (JSON).
    *   Real-time collaboration features. The workflow is sequential and automated.

#### 2. System Architecture

The application will be designed with a modular architecture to ensure maintainability and extensibility.

**2.1. Proposed Directory Structure:** A standard Python project structure will be used, suitable for a GitHub repository.

```
vpsweb/
├── .github/              # GitHub-specific files (e.g., issue templates)
├── configs/
│   ├── config.yaml       # Main configuration file for models, API keys, etc.
│   └── prompts/
│       ├── 01_initial_translation.txt
│       ├── 02_editor_review.txt
│       └── 03_translator_revision.txt
├── data/
│   ├── input/            # Folder for input poems
│   └── output/           # Folder for all generated outputs
├── src/
│   ├── __init__.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── llm_handler.py    # Module to interact with LLM APIs
│   │   └── parser.py         # Module for parsing XML/JSON responses
│   ├── steps/
│   │   ├── __init__.py
│   │   ├── step_1_translate.py
│   │   ├── step_2_review.py
│   │   └── step_3_revise.py
│   └── workflow.py         # Main orchestrator for the translation process
├── tests/                  # Unit and integration tests
├── .gitignore
├── main.py                 # Entry point to run the application
└── README.md               # Project documentation
```

**2.2. Core Components:**

*   **`main.py`:** The command-line entry point. It will handle parsing arguments (e.g., path to the input poem file) and initiating the translation workflow.
*   **`workflow.py`:** The main orchestrator. It calls the three steps in sequence, passing the output of one step as the input to the next.
*   **`steps/` modules:** Each module (`step_1_translate.py`, etc.) is responsible for a single stage of the workflow. Its duties include:
    1.  Loading the relevant prompt from `configs/prompts/`.
    2.  Formatting the prompt with the required input data.
    3.  Calling the `llm_handler` to get a response from the appropriate LLM.
    4.  Parsing the response and saving the structured output.
*   **`components/llm_handler.py`:** An abstraction layer for communicating with different LLM APIs. It will read the model details and API keys from `configs/config.yaml` and handle the request/response logic. This makes it easy to switch models or add new providers.
*   **`components/parser.py`:** A utility module containing functions to reliably parse the XML-formatted responses from the LLMs into clean Python dictionaries, as seen in the Dify workflow's code nodes.

#### 3. Configuration Management

The system will be highly configurable to avoid hardcoding and allow for easy experimentation.

**3.1. `configs/config.yaml`:** This file will manage all external parameters.

```yaml
# API Keys and Endpoints (placeholders, to be loaded from environment variables for security)
api_keys:
  tongyi: ${TONGYI_API_KEY}
  deepseek: ${DEEPSEEK_API_KEY}

# Workflow Step Configurations
steps:
  initial_translation:
    provider: "tongyi"
    model: "qwen-max-latest"
    prompt_template: "configs/prompts/01_initial_translation.txt"
    completion_params:
      temperature: 0.5
  
  editor_review:
    provider: "deepseek"
    model: "deepseek-reasoner"
    prompt_template: "configs/prompts/02_editor_review.txt"
    completion_params:
      max_tokens: 8192
      temperature: 0.7

  translator_revision:
    provider: "tongyi"
    model: "qwen-max-0919"
    prompt_template: "configs/prompts/03_translator_revision.txt"
    completion_params:
      max_tokens: 8001
      temperature: 0.2
```

**3.2. `configs/prompts/`:** The detailed prompts from the Dify workflow will be stored as separate `.txt` files. This keeps the Python code clean and allows for easy modification of prompts without changing the code. Placeholders (e.g., `{{original_poem}}`) will be used for dynamic content insertion.

#### 4. Data Flow and Storage

The workflow will be data-driven, with each step producing a structured JSON file that serves as an input for subsequent steps and as a record of the process.

**4.1. Input:** The process will start with a simple JSON file in the `data/input/` directory.
*   **Example: `input_poem_1.json`**
    ```json
    {
      "original_poem": "The fog comes\non little cat feet.",
      "source_lang": "English",
      "target_lang": "Chinese",
      "metadata": {
        "title": "Fog",
        "poet": "Carl Sandburg"
      }
    }
    ```

**4.2. Workflow & Output:** For each input file, a unique output directory will be created in `data/output/` (e.g., using a timestamp or poem title) to store the results of each step.

1.  **Input:** `input_poem_1.json`
2.  **Step 1: Initial Translation**
    *   **Output:** `01_initial_translation.json`
        ```json
        {
          "initial_translation": "...",
          "initial_translation_notes": "..."
        }
        ```
3.  **Step 2: Editor Review**
    *   **Output:** `02_editor_review.json`
        ```json
        {
          "editor_suggestions": "Suggestions for Improving the Translation of..."
        }
        ```
4.  **Step 3: Translator Revision**
    *   **Output:** `03_revised_translation.json`
        ```json
        {
          "revised_translation": "...",
          "revised_translation_notes": "..."
        }
        ```
5.  **Final Aggregation:** The `workflow.py` orchestrator will create a final consolidated report.
    *   **Output:** `_final_result.json`
        ```json
        {
          "input_data": { ... },
          "step_1_output": { ... },
          "step_2_output": { ... },
          "step_3_output": { ... }
        }
        ```

This structured, file-based approach ensures that the entire translation process for a given poem is auditable and its artifacts are easily accessible.

#### 5. Dependencies

The project will rely on the following standard Python libraries:
*   `requests`: For making HTTP requests to LLM APIs.
*   `PyYAML`: For parsing the `config.yaml` file.
*   `python-dotenv`: To securely manage API keys from a `.env` file.
*   Standard libraries: `os`, `json`, `re`.