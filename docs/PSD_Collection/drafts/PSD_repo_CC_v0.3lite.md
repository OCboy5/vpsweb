# Project Specification Document (PSD) v0.3-Lite — VPSWeb Central Repository & Local Web UI

**Status:** Minimal Prototype Revision (v0.3-Lite)
**Date:** 2025-10-19
**Scope:** Local single-user prototype for personal use

---

## 🎯 Objective

Design a **lightweight local repository and Web UI** for managing AI and human poetry translations produced by **vpsweb**, keeping core extensibility intact for future scaling.

The prototype focuses on simplicity, fast iteration, and seamless integration with the existing `vpsweb.TranslationWorkflow`.

---

## 🏗️ System Overview

### Goals

1. Run and store AI translations directly from vpsweb.
2. Store human translations for comparison.
3. View, compare, and browse translations locally via a simple Web UI.
4. Keep architecture modular enough for later expansion (auth, search, etc.).

### Non-Goals (Phase 1)

* Multi-user access or authentication.
* Background job system or async execution.
* Public web hosting or cloud deployment.
* HTMX interactivity or live updates.

---

## ⚙️ Technical Architecture

| Layer       | Technology                         | Notes                            |
| ----------- | ---------------------------------- | -------------------------------- |
| Backend     | **FastAPI (sync mode)**            | Single-process local web app     |
| Frontend    | **Jinja2 + Local Tailwind CSS**    | Simple HTML templates, no CDN    |
| Database    | **SQLite + SQLAlchemy ORM**        | Single file, WAL mode enabled    |
| Config      | **dotenv + Pydantic settings**     | Shared with vpsweb config system |
| Integration | **vpsweb.TranslationWorkflow API** | Direct import and execution      |
| Logging     | **Python logging**                 | Standard log output to console   |

### System Structure

```
repo_app/
├── main.py              # FastAPI entrypoint
├── database.py          # SQLite + SQLAlchemy setup
├── models.py            # ORM models (4-table schema)
├── schemas.py           # Pydantic models
├── api/                 # Route handlers
│   ├── poems.py
│   └── translations.py
├── web/                 # Templates + static assets
│   ├── templates/
│   │   ├── index.html
│   │   ├── poem.html
│   │   ├── compare.html
│   └── static/
│       ├── tailwind.css  # Local file (compiled or minified)
└── integration/
    └── vpsweb_adapter.py
```

---

## 🧱 Data Model

The 4-table schema from v0.2 is preserved for compatibility with vpsweb.

### Tables

**poems**

* id (ULID / UUIDv7)
* poet_name
* poem_title
* source_language (BCP-47)
* original_text
* created_at, updated_at

**translations**

* id
* poem_id (FK → poems)
* translator_type (enum: ai/human)
* translator_info
* target_language
* translated_text
* raw_path
* created_at

**ai_logs**

* id
* translation_id (FK)
* model_name, workflow_mode
* token_usage_json, cost_info_json
* runtime_seconds, notes, created_at

**human_notes**

* id
* translation_id (FK)
* note_text, created_at

---

## 🌐 API Endpoints

### REST Routes

```
GET    /api/v1/poems
POST   /api/v1/poems
GET    /api/v1/poems/{id}
GET    /api/v1/translations?poem_id={id}
POST   /api/v1/translations
POST   /api/v1/translate   → Run vpsweb translation and store result
```

All endpoints are open to localhost access (no authentication required).

### Example Workflow

1. User opens Web UI → selects a source poem.
2. Clicks “Run AI Translation” → triggers `/api/v1/translate`.
3. FastAPI route invokes `vpsweb.TranslationWorkflow`.
4. Result is stored in `translations` and `ai_logs`.
5. User views results in `/poems/{id}` or compares human/AI in `/compare/{poem_id}`.

---

## 🧩 Integration with vpsweb

Direct synchronous integration (no background queue):

```python
from vpsweb.core.workflow import TranslationWorkflow

class VPSWebAdapter:
    def run_translation(self, poem, target_lang, mode="hybrid"):
        wf = TranslationWorkflow()
        result = wf.execute(
            text=poem.original_text,
            source_language=poem.source_language,
            target_language=target_lang,
            workflow_mode=mode
        )
        return result.translated_text
```

---

## 🎨 Web UI Overview

**Pages:**

* `/` → Dashboard: lists poems
* `/poems/{id}` → Poem details + AI/Human translations
* `/compare/{poem_id}` → Side-by-side comparison view
* `/new` → Add new poem or upload translation

**Design:**

* Static Tailwind file in `/static/tailwind.css`
* Clean, text-focused layout for poetry display
* Responsive without external CDN

---

## 🧰 Configuration

**.env Example:**

```
DATABASE_URL=sqlite:///repository_root/repo.db
REPO_ROOT=./repository_root
LOG_LEVEL=INFO
ENV=development
```

**settings.py:**

```python
class RepoSettings(BaseSettings):
    database_url: str
    repo_root: str
    log_level: str = "INFO"
    class Config:
        env_file = ".env"
```

---

## 🔒 Security & Privacy

* Localhost access only.
* No password or auth by default.
* HTML autoescape enabled.
* Markdown content sanitized using `bleach`.

---

## 🧪 Testing

| Type        | Tool   | Scope                 |
| ----------- | ------ | --------------------- |
| Unit        | pytest | DB + model logic      |
| Integration | httpx  | vpsweb workflow calls |
| UI          | manual | local browser test    |

---

## 💾 Backup & Lifecycle

* Data stored under `repository_root/`
* Manual backup: copy `repo.db` + `/data/` folder
* Optional script: `vpsweb repo backup`

---

## 🚀 Implementation Timeline (1 Week Target)

| Day | Task                  | Deliverable             |
| --- | --------------------- | ----------------------- |
| 1–2 | Scaffold FastAPI + DB | app skeleton            |
| 3   | Implement CRUD        | working API             |
| 4   | Add templates         | basic UI pages          |
| 5   | Integrate vpsweb      | translation working     |
| 6   | Polish & test         | local workflow verified |
| 7   | Backup script + docs  | v0.3-Lite ready         |

---

## ✅ Success Criteria

* Can run vpsweb translations and save results locally.
* View AI & human translations in browser.
* Compare versions side-by-side.
* No external dependencies or auth required.
* Fully offline-capable.

---

**End of PSD v0.3-Lite — Minimal Viable Local Repository & Web UI for VPSWeb**
