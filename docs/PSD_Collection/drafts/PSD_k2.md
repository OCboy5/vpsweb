📜 PSD – Vox Poetica Studio Web (vpsweb)

“Machine does the draft, human keeps the soul.”
1. Vision & Value

1.1 Enable poets, translators & researchers to co-create high-fidelity, multi-lingual poetry translations through an AI-augmented, human-in-the-loop pipeline.
1.2 Replicate the professional studio workflow “Translator → Editor → Translator” with fully open Python code, YAML configs, and future-proof web UI hooks.
1.3 Ship a GitHub-native project (issues, boards, CI/CD, releases, PyPI package) that any developer can git clone, pip install and extend.
2. High-Level Architecture


Copy
┌--------------┐      ┌--------------┐      ┌--------------┐
│   Step-1     │----▶ │   Step-2     │----▶ │   Step-3     │
│  Translator  │ JSON │   Editor     │ JSON │  Translator  │
│  (draft)     │      │ (critique)   │      │  (final)     │
└--------------┘      └--------------┘      └--------------┘
        ▲                                          ▼
        │            ┌--------------┐      ┌--------------┐
        └------------│  Config &    │      │   Outputs    │
                     │  Prompts     │      │  (artefacts) │
                     │  (YAML)      │      │  /out/*.json │
                     └--------------┘      └--------------┘
Each step = stateless Python function receiving a Pydantic model, returning a Pydantic model.
All prompts, model names, temperatures, etc. live in YAML – zero code change to switch from qwen-max to gpt-4o.
Every run produces timestamped artefacts (/out/<uuid>/) for full reproducibility and future UI rendering.
3. Functional Requirements (FR)

Table

Copy
ID	Requirement Statement	MoSCoW
FR-01	CLI entry-point vpsweb translate -c configs/ch2en.yml -i poem.txt	Must
FR-02	Load models & prompts from YAML; no hard-code strings	Must
FR-03	Produce identical results to the original Dify DSL when using same seeds & models	Must
FR-04	Structured JSON after every step; JSON-Schema validated via Pydantic	Must
FR-05	Support any OpenAI-compatible endpoint (OpenAI, DeepSeek, Tongyi, vLLM, etc.)	Must
FR-06	Async / await for concurrent API calls; rate-limit & retry with tenacity	Should
FR-07	Optional human-in-the-loop mode: pause after Editor, wait for user JSON edit	Should
FR-08	Extensible plugin loader for new steps (e.g. “Rhyme-Checker”, “MT-Evaluator”)	Could
FR-09	Provide Dockerfile + docker-compose.yml for one-liner local deployment	Could
FR-10	Embed FastAPI skeleton ready for web UI SPA (React/Vue) consumption	Won’t (phase-2)
4. Configuration Schema (v1)

yaml

Copy
# configs/ch2en.yml
project_name: "ch2en_li_bai_demo"
output_dir: "./out"

steps:
  - name: initial_translation
    model:
      provider: openai_compatible   # openai_compatible | azure | bedrock
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
      api_key: "${TONGYI_API_KEY}"
      model: "qwen-max-latest"
      temperature: 0.7
      max_tokens: 2000
    prompt_template_file: "prompts/initial_translation.jinja2"
    output_schema: "schemas/InitialTranslation.json"

  - name: editor_review
    model:
      provider: openai_compatible
      base_url: "https://api.deepseek.com/v1"
      api_key: "${DEEPSEEK_API_KEY}"
      model: "deepseek-reasoner"
      temperature: 0.3
      max_tokens: 4000
    prompt_template_file: "prompts/editor_review.jinja2"
    output_schema: "schemas/EditorReview.json"

  - name: final_translation
    model:
      provider: openai_compatible
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
      api_key: "${TONGYI_API_KEY}"
      model: "qwen-max-0919"
      temperature: 0.5
      max_tokens: 2000
    prompt_template_file: "prompts/final_translation.jinja2"
    output_schema: "schemas/FinalTranslation.json"
Secrets are injected via env-vars; never commit keys.
5. Data Models (Pydantic)

Python

Copy
# src/vpsweb/models.py
from pydantic import BaseModel, Field

class PoemRequest(BaseModel):
    original_poem: str
    source_lang: str
    target_lang: str

class InitialTranslation(BaseModel):
    poem_request: PoemRequest
    translation: str
    notes: str

class EditorReview(BaseModel):
    initial_translation: InitialTranslation
    suggestions: list[str]
    overall_assessment: str

class FinalTranslation(BaseModel):
    editor_review: EditorReview
    translation: str
    revision_notes: str
Each model → auto JSON-Schema → frontend forms / validation.
6. Prompt Management

Prompts live in prompts/*.jinja2 – leverage Jinja2 for logic & loops.
Version-controlled alongside code; diff-friendly.
Example (abridged):
jinja2

Copy
{# prompts/editor_review.jinja2 #}
You are a bilingual literary critic…
Source:
{{ poem_request.original_poem }}
Translation:
{{ initial_translation.translation }}
Provide numbered suggestions…
7. Project Layout (GitHub-ready)


Copy
vpsweb/
├── .github/
│   ├── workflows/ci.yml
│   ├── ISSUE_TEMPLATE/...
│   └── dependabot.yml
├── configs/
│   ├── ch2en.yml
│   └── en2fr.yml
├── prompts/
│   ├── initial_translation.jinja2
│   ├── editor_review.jinja2
│   └── final_translation.jinja2
├── schemas/               # JSON-Schema for each model (auto-generated)
├── src/vpsweb/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── models.py
│   ├── steps/
│   │   ├── __init__.py
│   │   ├── initial_translation.py
│   │   ├── editor_review.py
│   │   └── final_translation.py
│   ├── llm/
│   │   ├── __init__.py
│   │   └── openai_compatible.py
│   └── utils/
│       ├── io.py
│       └── validators.py
├── tests/
│   ├── unit/
│   └── fixtures/          # sample poems + expected JSON outputs
├── scripts/
│   └── sync_dify_output.py   # helper to validate parity
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml         # poetry or setuptools
├── README.md
├── LICENSE
└── docs/
    └── psd.md   ← this file
8. Development & Release Workflow

Local dev
bash

Copy
poetry install
poetry run pytest
poetry run vpsweb translate -c configs/ch2en.yml -i tests/fixtures/li_bai.txt
Pre-commit hooks – black, isort, flake8, mypy.
CI (GitHub Actions)
matrix py 3.9-3.12
unit tests + integration test against sandboxed LLM (optional)
build wheel & docker image on tag
Release
Tag v0.1.0 → CI pushes ghcr.io/<user>/vpsweb:0.1.0 and PyPI package.
9. Future Web-UI Integration (Phase-2)

FastAPI app mounted at /api serving:
POST /api/jobs → returns job-id
GET  /api/jobs/{id}/status
GET  /api/jobs/{id}/artefacts
Static SPA (React) in /frontend folder; GitHub Action builds → GitHub Pages.
WebSocket progress stream for human-in-the-loop pause/resume.
10. Risks & Mitigations

Table

Copy
Risk	Mitigation
Model output drift vs. Dify	Lock versions + snapshot integration tests
Prompt injection / unsafe content	Add input sanitiser + moderation filter step
API quota / cost explosion	Built-in token counter + budget limiter
Schema evolution breakage	Pydantic + semver + json-schema CI diff check
11. Success Metrics (alpha)

☑️ 100 % parity with Dify DSL on 5 test poems (BLEU ≥ 95 vs. Dify ref).
☑️ ≤ 10 % overhead in tokens vs. original Dify run.
☑️ CLI completes end-to-end in < 60 s (gpt-4o) on average laptop.
☑️ Zero hard-coded secrets; all configs pass yamllint + ansible-vault dry-run.
12. Next Actions (checklist)

[ ] Repo bootstrap: git init vpsweb + add LICENSE (MIT) + README badge skeleton
[ ] Poetry pyproject.toml + dev-dependencies
[ ] Pydantic models + JSON-Schema auto-export script
[ ] LLM connector interface + openai_compatible impl
[ ] Port three Dify prompts → Jinja2 templates
[ ] Implement StepDriver (async) + artefact writer
[ ] Unit tests (pytest + respx for LLM mock)
[ ] Integration test vs. Dify golden outputs
[ ] Dockerfile + CI workflow
[ ] Tag v0.1.0-alpha 🎉
End of PSD – version 0.1 – 2025-10-03