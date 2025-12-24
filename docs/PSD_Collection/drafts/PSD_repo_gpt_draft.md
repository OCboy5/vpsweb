# Project Specification Document (PSD) v0.2 — VPSWeb Central Repository & Local Web UI

**Status**: Revised Draft (v0.2 — Simplified Prototype Architecture)
**Date**: 2025-10-17
**Author**: VPSWeb Architecture Team
**Scope**: Local-first personal system (Phase 1 prototype)

---

## 🎯 Executive Summary

This revision simplifies and modernizes the repository and web UI design for the **VPSWeb Poetry Translation System**, focusing on a robust, minimal, and maintainable **local-first prototype**. The system stores and manages both AI and human translations with seamless integration to `vpsweb.TranslationWorkflow`, while avoiding overengineering and deprecated components.

### Key Improvements Over v0.1

* Removed custom job queue → replaced with **FastAPI BackgroundTasks**
* Unified database access (no multiple SQLite DBs)
* Modernized frontend stack → **HTMX + Tailwind CSS** (no Jinja2 + Bootstrap)
* Added `.env`-based config for secrets and runtime paths
* Introduced structured logging, config validation, and environment profiles
* Reduced code complexity: fewer moving parts, faster to implement

### Implementation Scope

* MVP architecture ready for 2-week implementation
* Local deployment only (single-user)
* Easily expandable to multi-user, cloud-hosted system in later phases

---

## 🏗️ System Overview

### Primary Goals

1. Provide a **central repository** for AI and human poetry translations.
2. Enable **side-by-side comparison** of translation versions.
3. Integrate directly with **vpsweb translation workflows**.
4. Support **local browsing, editing, and backups**.

### Non-Goals (for this phase)

* Multi-user authentication (beyond single password)
* Real-time WebSocket updates
* Full-text search (planned for v0.3)

---

## ⚙️ Technical Architecture

### Stack Summary

| Layer       | Technology                     | Notes                               |
| ----------- | ------------------------------ | ----------------------------------- |
| Backend     | **FastAPI (async)**            | Core API + Web UI endpoints         |
| Database    | **SQLite (SQLAlchemy ORM)**    | Single unified DB, WAL mode         |
| Frontend    | **HTMX + Tailwind CSS**        | Server-rendered reactive UI         |
| Integration | **Direct API (Path B)**        | Uses vpsweb.TranslationWorkflow API |
| Config      | **dotenv + Pydantic settings** | Secure and environment-based        |
| Logging     | **structlog / JSON logs**      | For traceability and debugging      |

### System Components

```
FastAPI Web Server
├── Repository API (CRUD, compare, import/export)
├── Web UI (HTMX templates, Tailwind)
├── Integration Adapter (vpsweb direct calls)
└── Background Task Manager (FastAPI BackgroundTasks)
```

### Directory Layout

```
src/vpsweb/repository/
├── main.py                # FastAPI entrypoint
├── database.py            # SQLAlchemy setup
├── models.py              # ORM models
├── schemas.py             # Pydantic models
├── api/                   # REST endpoints
│   ├── poems.py
│   ├── translations.py
│   └── jobs.py
├── web/                   # HTMX templates + static assets
│   ├── routes.py
│   ├── templates/
│   └── static/
├── integration/
│   └── vpsweb_adapter.py
└── utils/
    ├── config.py          # Env + YAML config
    ├── file_storage.py
    └── logger.py
```

---

## 🧱 Data Model

Unified 4-table schema (same as v0.1, cleaned and constrainted)

### Tables

**poems**

* id (ULID / UUIDv7)
* poet_name
* poem_title
* source_language (BCP-47)
* original_text
* form, period
* created_at, updated_at

**translations**

* id
* poem_id (FK → poems)
* version (auto-increment per poem)
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

## 🌐 API Specification

### REST Endpoints (Simplified)

```
# Poem APIs
GET    /api/v1/poems
POST   /api/v1/poems
GET    /api/v1/poems/{id}
PUT    /api/v1/poems/{id}
DELETE /api/v1/poems/{id}

# Translation APIs
GET    /api/v1/translations?poem_id={id}
POST   /api/v1/translations
GET    /api/v1/translations/{id}
DELETE /api/v1/translations/{id}

# Job APIs
POST   /api/v1/jobs/translate   → run AI translation (background)
GET    /api/v1/jobs/{id}        → check job status
```

### Authentication

* **HTTP Basic Auth** for both API and Web UI
* Password hash stored in `.env` (`REPO_PASSWORD_HASH`)
* Token expiry: 12h session cookie

### Error Model

All errors return structured JSON:

```json
{
  "status": "error",
  "type": "ValidationError",
  "message": "Poem not found"
}
```

---

## 🧩 Integration with vpsweb

### Integration Mode: Path B (Direct API)

```python
from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.models.config import load_config

class VPSWebAdapter:
    async def run_translation(self, poem, target_lang, mode="hybrid"):
        config = load_config("config/models.yaml")
        wf = TranslationWorkflow(config)
        result = await wf.execute(
            text=poem.original_text,
            source_language=poem.source_language,
            target_language=target_lang,
            workflow_mode=mode
        )
        return result.translated_text
```

### Invocation via BackgroundTasks

```python
@router.post("/jobs/translate")
async def run_translation_job(poem_id: str, target_lang: str, background_tasks: BackgroundTasks):
    poem = await get_poem(poem_id)
    background_tasks.add_task(vps_adapter.run_translation, poem, target_lang)
    return {"status": "queued", "poem_id": poem_id}
```

---

## 🎨 Web UI Design (HTMX + Tailwind)

**Pages:**

* `/` → Dashboard: recent poems, stats
* `/poems` → Poem list & filters
* `/poems/{id}` → Poem detail + translations
* `/compare/{poem_id}/{translation_id}` → Side-by-side comparison
* `/new/ai` → Run AI translation form
* `/new/human` → Add human translation form

**Features:**

* Inline editing with HTMX partials
* Lightweight, responsive design
* Progressive enhancement: no JS build chain required

---

## 🧰 Configuration & Deployment

**.env example:**

```
DATABASE_URL=sqlite+aiosqlite:///repository_root/repo.db
REPO_ROOT=./repository_root
REPO_PASSWORD_HASH=$2b$12$abc...xyz
LOG_LEVEL=INFO
ENV=development
```

**Config Class (Pydantic):**

```python
class RepoSettings(BaseSettings):
    database_url: str
    repo_root: str
    repo_password_hash: str
    log_level: str = "INFO"
    class Config:
        env_file = ".env"
```

---

## 🔒 Security & Privacy

* Single-user password via BasicAuth
* All write endpoints require auth
* HTML autoescape enabled for user text
* Markdown rendering uses bleach sanitizer
* CSRF protection for form submissions (HTMX token header)

---

## 🧪 Testing & QA

| Type        | Tools               | Coverage              |
| ----------- | ------------------- | --------------------- |
| Unit        | pytest + httpx      | 80% minimum           |
| Integration | pytest-asyncio      | CRUD + workflow tests |
| Linting     | black, mypy, flake8 | Clean CI baseline     |
| Security    | bandit              | Basic static scan     |

---

## 💾 Backup & Data Lifecycle

* Unified repo root: `repository_root/`
* Manual backup via CLI `vpsweb repo backup`
* Automatic weekly snapshot (cron optional)
* Backup includes DB + `/data/` folder

---

## 🚀 Implementation Timeline (2 Weeks)

| Day   | Task                          | Deliverable               |
| ----- | ----------------------------- | ------------------------- |
| 1–2   | Project scaffolding, DB setup | working FastAPI app       |
| 3–4   | Poem + Translation CRUD       | tested APIs               |
| 5–6   | HTMX UI views                 | local UI functional       |
| 7–8   | vpsweb integration            | translation jobs running  |
| 9–10  | BackgroundTasks, auth         | secure local server       |
| 11–12 | Backup & config               | CLI + .env config working |
| 13–14 | Testing & polish              | v0.2 release              |

---

## ✅ Success Metrics

* **Functional**: Full CRUD, AI job execution, comparison view operational
* **Performance**: <300ms per API request, <1s page load
* **Security**: Password required for all writes
* **Reliability**: WAL-mode SQLite, recoverable backups
* **Usability**: <30-minute learning curve

---

## 🧭 Future Extensions (v0.3+)

* WebSocket job updates (real-time progress)
* FTS5 search for poems and translations
* Multi-user accounts with role-based access
* Export to WeChat / HTML article
* Postgres migration for public deployment

---

**End of PSD v0.2 — Simplified, Modern, Maintainable Architecture for Local Repository System**
