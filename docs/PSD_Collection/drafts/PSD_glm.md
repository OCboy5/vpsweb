Product Specifications Document (PSD): vpsweb (Vox Poetica Studio Web)
Version: 1.0
Date: 2025-10-04
Author: AI Assistant
1. Introduction & Vision
1.1. Project Purpose
The vpsweb project aims to create a professional, AI-powered poetry translation platform. Its core purpose is to replicate and enhance the “Translator -> Editor -> Translator” (T-E-T) collaborative workflow, producing high-fidelity translations that preserve the original poem’s aesthetic beauty, musicality, emotional resonance, and cultural context.
1.2. Vision
Our vision is to democratize access to high-quality literary translation. By leveraging state-of-the-art Large Language Models (LLMs) in a structured, multi-agent workflow, vpsweb will serve poets, scholars, translators, and language enthusiasts, enabling them to explore and appreciate global poetic works with unprecedented depth and accuracy.
1.3. Core Problem
Direct, single-pass LLM translation often fails to capture the nuance, form, and artistic intent of poetry. Human translation is a iterative, collaborative process of drafting, critiquing, and refining. vpsweb automates this sophisticated process to achieve a superior result.
2. Project Goals & Objectives
Goal ID	Objective	Success Criteria
G-1	Replicate Dify Workflow	The Python core workflow produces outputs (translation, notes, suggestions) that are functionally equivalent to the provided Dify workflow.
G-2	Ensure High Configurability	All models, API keys, prompts, and workflow parameters are managed via external configuration files (e.g., YAML) without code changes.
G-3	Enforce Structured Data Flow	The output of each workflow step is a well-defined, validated data structure (e.g., Pydantic model) that can be reliably passed to the next step.
G-4	Establish a Scalable Architecture	The project is modular, allowing for easy addition of new translation steps, models, or languages in the future.
G-5	Lay Groundwork for a Web UI	The core logic is decoupled from any interface, designed to be easily wrapped by a web framework (e.g., FastAPI, Flask).
G-6	Adhere to GitHub Best Practices	The repository includes a standard project structure, README, LICENSE, contribution guidelines, and a clear issue/PR template.
3. Core Workflow Analysis (T-E-T)
The project is built around a three-step process, directly derived from the Dify workflow.
Step 1: Initial Translation (The “Translator”)
Input: original_poem (str), source_lang (str), target_lang (str).
Process: An LLM, acting as a expert translator, performs a deep analysis of the source poem and generates a high-quality initial draft. It also produces detailed notes explaining its choices, especially for challenging lines.
Output: A structured object InitialTranslationResult containing:
translation (str): The first draft of the translated poem.
notes (str): The translator’s explanatory notes.
Step 2: Editorial Review (The “Editor”)
Input: original_poem, InitialTranslationResult.
Process: A different LLM, often a reasoning model, acts as a literary critic and editor. It compares the original and the initial translation, identifying areas for improvement in faithfulness, expressiveness, elegance, and cultural resonance. It provides a numbered list of specific, constructive suggestions.
Output: A structured object EditorReviewResult containing:
suggestions (List[str]): A list of actionable feedback points.
Step 3: Final Revision (The “Translator” again)
Input: original_poem, InitialTranslationResult, EditorReviewResult.
Process: The first LLM (or a similar high-performance model) revisits its initial translation. It critically evaluates the editor’s suggestions, implements the valuable ones, and performs a final polish to create the definitive version.
Output: A structured object FinalRevisionResult containing:
translation (str): The final, polished translation.
notes (str): Notes explaining the key changes made during revision.
Final Step: Aggregation
Input: All data from the previous steps.
Process: A utility function combines all pieces—the original poem, each translation version, all notes, and the editor’s suggestions—into a single, comprehensive, and human-readable report.
Output: A single formatted string (final_report).
4. System Architecture & Design
4.1. Project Structure (GitHub)
vpsweb/
├── .github/                  # GitHub workflows (CI/CD), issue templates
│   └── workflows/
├── config/                   # All configuration files
│   ├── models.yaml           # LLM model definitions (provider, name, params)
│   └── prompts.yaml          # Prompt templates for each workflow step
├── docs/                     # Project documentation
│   └── psd.md                # This document
├── src/
│   └── vpsweb/
│       ├── __init__.py
│       ├── core/             # Core workflow and business logic
│       │   ├── __init__.py
│       │   ├── workflow.py   # Main orchestrator for the T-E-T process
│       │   ├── models.py     # Pydantic data models for structured I/O
│       │   └── llm_client.py # Abstraction layer for LLM API calls
│       ├── steps/            # Logic for each individual step
│       │   ├── __init__.py
│       │   ├── initial_translation.py
│       │   ├── editor_review.py
│       │   └── final_revision.py
│       └── utils/            # Helper functions
│           ├── __init__.py
│           └── aggregator.py # Logic to create the final report
├── tests/                    # Unit and integration tests
│   ├── test_workflow.py
│   └── test_steps/
├── .gitignore
├── LICENSE
├── README.md
├── pyproject.toml            # For Poetry/pip-tools dependency management
└── main.py                   # Entry point for a CLI interface
4.2. Core Components
Configuration (config/):
models.yaml: Will define which LLM to use for each role (e.g., translator_model: "qwen-max", editor_model: "deepseek-reasoner"). It will also store model parameters like temperature and max_tokens.
prompts.yaml: Will store the system and user prompt templates for each step, using placeholders (e.g., {{original_poem}}) for easy substitution.
LLM Client (core/llm_client.py):
A unified interface (e.g., class LLMClient) to interact with different LLM providers (OpenAI, Qwen/Tongyi, DeepSeek, etc.).
This will handle API authentication, request formatting, and response parsing, making it simple to swap models in the configuration file.
Data Models (core/models.py):
Crucial for structured data flow. We will use Pydantic to define the input and output for each step.
Example:
        from pydantic import BaseModel

        class InitialTranslationResult(BaseModel):
            translation: str
            notes: str

        class EditorReviewResult(BaseModel):
            suggestions: list[str]
Workflow Steps (steps/):
Each step will be a Python class or function with a clear execute method.
Example: class InitialTranslationStep takes the poem and config, uses the LLMClient to call the model, parses the response into an InitialTranslationResult Pydantic model, and returns it.
Main Orchestrator (core/workflow.py):
The VoxPoeticaWorkflow class will manage the entire process.
It will load configurations, instantiate the steps, and pass the structured output of one step as the input to the next, ensuring a clean, stateless pipeline.
5. Configuration Strategy
All user-configurable aspects will be externalized.
API Keys: Will be loaded from environment variables (e.g., OPENAI_API_KEY, TONGYI_API_KEY). The code will not contain any hardcoded credentials.
Model Selection: The models.yaml file will allow users to specify which model to use for each role, enabling easy experimentation with reasoning models vs. high-performance models.
Prompt Engineering: The prompts.yaml file allows for non-developers to tweak and improve the prompts without touching the Python code, which is essential for refining translation quality.
6. Development & Deployment Plan
Phase 1: Core Logic (MVP)
Set up the project structure and dependencies.
Implement the LLMClient with support for Qwen and DeepSeek.
Define Pydantic models.
Implement the three core steps (initial_translation, editor_review, final_revision).
Build the main workflow.py orchestrator.
Goal: Successfully run the full T-E-T workflow from a Python script and replicate the Dify output.
Phase 2: CLI Interface
Create a main.py using a library like Click or Typer.
Allow users to run a translation from the command line, specifying a text file or pasting the poem directly.
Output the final report to a file or the console.
Phase 3: Web UI (Future)
Create a new web/ directory.
Use FastAPI to create REST API endpoints that wrap the core workflow logic.
Develop a simple frontend (e.g., with React/Vue) to submit poems and display results.
Phase 4: Extension
Add support for more LLM providers (Claude, Gemini).
Implement more complex workflows (e.g., adding a “cultural expert” step).
Integrate evaluation metrics (e.g., BLEU, COMET) to automatically score translations.