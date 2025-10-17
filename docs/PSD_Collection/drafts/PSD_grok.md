Product Specification Document (PSD) for Vox Poetica Studio Web (vpsweb)
1. Document Information

Document Title: Product Specification Document for vpsweb
Version: 1.0
Date: October 03, 2025
Author: Grok 4 (xAI Assistant)
Project Name: vpsweb (Vox Poetica Studio Web)
Repository URL: (To be created on GitHub as https://github.com/[username]/vpsweb)
Status: Draft (Pending Implementation)

2. Introduction
2.1 Project Overview
The vpsweb project aims to create a modular, configurable Python-based implementation of a poetry translation workflow originally defined in a Dify DSL (YAML) file. The workflow simulates a collaborative process involving a translator, editor, and reviser to translate poems between languages (primarily English and Chinese, with extensibility to others like Polish), preserving fidelity, poetic beauty, rhythm, musicality, and cultural nuances.
The core workflow follows a "Translator -> Editor -> Translator" sequence:

Initial translation of the poem.
Editorial review and suggestions.
Revision based on feedback.
Aggregation of results into a structured output.

This Python project will replicate the Dify workflow's functionality using scripts, while adhering to GitHub best practices for structure, documentation, and version control. It is designed to be highly configurable (e.g., via YAML/JSON config files for models, prompts, and parameters) and structured for easy data flow between steps. The design considers future extensibility to add a web UI (e.g., using Flask or Streamlit), separating core logic from presentation layers.
2.2 Purpose

Convert the Dify DSL workflow into executable Python scripts to enable offline/local execution, customization, and integration.
Ensure the project follows GitHub guidelines: clean structure, README, licensing, issue tracking, and CI/CD potential.
Facilitate high-fidelity poetry translation with structured, reusable components.
Prepare for future web UI integration to make the tool accessible via a browser (e.g., input forms for poems and languages, output display).

2.3 Scope

In Scope:

Replication of the Dify workflow nodes (Start, LLMs, Code extractors, Template Transform, End) as Python functions/classes.
Configurable elements: LLM providers/models, prompts, input variables (e.g., original_poem, source_lang, target_lang).
Structured data handling: Use dictionaries or Pydantic models for inputs/outputs between steps.
GitHub repository setup: Directory structure, README, .gitignore, license (e.g., MIT).
Basic CLI execution for testing the workflow.
Logging and error handling for each step.


Out of Scope:

Actual web UI implementation (but design hooks for it, e.g., API-like functions).
Support for non-LLM providers beyond what's in the Dify file (e.g., Tongyi, Deepseek); extensibility via config.
Advanced features like multi-language support beyond English/Chinese/Polish, or file uploads (unless configured).
Production deployment (e.g., Docker, cloud hosting); focus on local development.



2.4 Assumptions and Dependencies

Python 3.10+ environment.
External libraries: requests or LLM SDKs (e.g., for Tongyi/Deepseek APIs), re and json (built-in for extraction), Pydantic for data validation.
API keys for LLM providers must be provided via environment variables or config.
Users have GitHub access to clone/fork the repo.
No internet access required beyond LLM API calls (configurable to use local models if possible).

3. Requirements
3.1 Functional Requirements

FR1: Workflow Execution

Replicate the Dify sequence: Input -> Initial Translation (LLM) -> Extract (Code) -> Editor Review (LLM) -> Revision (LLM) -> Extract (Code) -> Congregate (Template) -> Output.
Accept inputs: original_poem (str), source_lang (enum: English, Chinese, Polish), target_lang (enum: Chinese, English).
Produce structured output: A dictionary with keys like 'original_poem', 'initial_translation', 'initial_translation_notes', 'editor_suggestions', 'revised_translation', 'revised_translation_notes', and a formatted 'logs' string.


FR2: Configurability

Use config files (e.g., config.yaml) for:

LLM settings: provider (e.g., 'tongyi', 'deepseek'), model names (e.g., 'qwen-max-latest'), API endpoints, parameters (e.g., max_tokens, temperature).
Prompts: Full system/user prompts for each LLM step, with placeholders for variables (e.g., {{original_poem}}).
Extraction logic: Regex patterns or parsing functions.
Template for congregation: Jinja2-style string with placeholders.


Allow overriding configs via CLI arguments.


FR3: Structured Data Flow

Each step outputs a dict (e.g., {'text': '...'} for LLMs, {'initial_translation': '...', 'initial_translation_notes': '...'} for extractors).
Use Pydantic models for validation (e.g., TranslationOutput(BaseModel): initial_translation: str, ...).
Chain steps: Output of one becomes input to next (e.g., pass extracted dict to next LLM prompt).


FR4: Logging and Debugging

Log inputs/outputs of each step to console/file.
Handle errors gracefully (e.g., LLM API failures retry or fallback).


FR5: Extensibility for Web UI

Core logic in a module (e.g., vpsweb/core.py) with functions like run_workflow(inputs: dict, config: dict) -> dict.
Separate concerns: LLM calls in a utils/llm.py, parsers in utils/parser.py.
Design run_workflow as an API endpoint candidate (e.g., accept JSON, return JSON).



3.2 Non-Functional Requirements

NFR1: Performance: Workflow should complete in <30s for typical poems (assuming LLM latency); no optimization beyond config.
NFR2: Security: Store API keys in .env (not committed to Git); validate inputs to prevent injection.
NFR3: Maintainability: Modular code, type hints, docstrings, PEP8 compliance.
NFR4: Documentation: README with setup, usage, config examples; inline comments.
NFR5: Testing: Basic unit tests for parsers and template; integration test for full workflow.
NFR6: Licensing: MIT License for open-source.

4. Architecture and Design
4.1 High-Level Architecture

Modular Structure:

Entry point: main.py (CLI script to run workflow).
Core: core.py (orchestrates steps).
Utils: llm.py (handles LLM calls), parser.py (XML extraction), template.py (congregation).
Config: config.yaml (default), loader in config.py.


Data Flow:

Inputs -> LLM1 (Initial) -> Parser1 -> LLM2 (Editor) -> LLM3 (Revision) -> Parser2 -> Template -> Output.
All data passed as dicts, with placeholders resolved using string formatting or Jinja2.


Conversion Strategy from Dify DSL:

Parse YAML nodes/edges to map to functions: Start (input dict), LLMs (call_llm(prompt_template, variables)), Code (exec custom Python), Template (str.format or Jinja), End (return dict).
Prompts: Extract from YAML and store in config.yaml with placeholders (e.g., {{#1718674431213.original_poem#}} -> {original_poem}).
Variables: Use dict substitution for placeholders.
Edges: Represent as function calls in sequence.
Future: Could add a DSL parser to load arbitrary Dify YAMLs, but for v1, hardcode the sequence based on this specific YAML.



4.2 GitHub Repository Structure
textvpsweb/
├── .github/                # Workflows for CI/CD
│   └── workflows/
│       └── ci.yml          # Basic lint/test workflow
├── src/                    # Source code
│   ├── vpsweb/
│   │   ├── __init__.py
│   │   ├── core.py         # Workflow orchestration
│   │   ├── config.py       # Config loader
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── llm.py      # LLM API wrappers
│   │   │   ├── parser.py   # XML parsers
│   │   │   └── template.py # Template rendering
│   └── main.py             # CLI entry point
├── configs/                # Config files
│   └── config.yaml         # Default config (prompts, models)
├── tests/                  # Unit/integration tests
│   ├── test_parser.py
│   └── test_workflow.py
├── .env.example            # Sample env for API keys
├── .gitignore              # Ignore .env, __pycache__, etc.
├── LICENSE                 # MIT License
├── README.md               # Setup, usage, examples
├── requirements.txt        # Dependencies (pydantic, requests, jinja2, pytest)
└── setup.py                # For pip install -e .
4.3 Key Components

config.py: Load YAML/JSON, validate with Pydantic.
llm.py: Function call_llm(provider, model, prompt_parts: list[dict], variables: dict) -> dict{'text': str}.
parser.py: xml_to_dict(xml_str) -> dict, mirroring the YAML code nodes.
template.py: render_template(template_str, variables: dict) -> str.
core.py: def run_workflow(inputs: dict, config: dict) -> dict: Chain calls, return aggregated output.
main.py: Parse CLI args, load config, run workflow, print JSON/yaml output.

5. Implementation Plan

Phase 1: Setup repo structure, add README/LICENSE.
Phase 2: Implement config loader and utils (llm, parser, template).
Phase 3: Implement core workflow orchestration based on Dify sequence.
Phase 4: Add tests and CLI.
Phase 5: Document and prepare for web UI hooks (e.g., expose run_workflow as callable).

6. Risks and Mitigations

Risk: LLM API changes – Mitigation: Configurable providers.
Risk: Prompt placeholders mismatch – Mitigation: Use consistent naming, tests.
Risk: Parsing failures – Mitigation: Robust regex, error handling.
Risk: Future UI integration – Mitigation: Keep core stateless and input/output dict-based.

7. Approval

Pending user review/feedback before code generation.