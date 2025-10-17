# Project Specification Document (PSD) v0.3 — VPSWeb Central Repository & Local Web UI

**Status**: Architectural Compromise Draft (v0.3 — Modern + Consistent)
**Date**: 2025-10-17
**Author**: VPSWeb Architecture Team
**Scope**: Local-first personal system with enterprise-grade security patterns

---

## 🎯 Executive Summary

This PSD represents a **hybrid architectural approach** that combines the best of modern simplicity with proven enterprise patterns. The system provides a **central repository** for AI and human poetry translations while maintaining **configuration consistency** with the existing vpsweb codebase and implementing **production-grade security**.

### Key Architectural Decisions

* **Frontend**: **HTMX + Tailwind CSS** for modern, lightweight server-rendered UI
* **Background Jobs**: **FastAPI BackgroundTasks** (appropriate for local use)
* **Configuration**: **YAML + Pydantic** (consistent with existing vpsweb system)
* **Security**: **Argon2 password hashing** + comprehensive constraints
* **Integration**: **Direct vpsweb API calls** with proper error handling
* **Database**: **SQLite with full constraints and optimization**

### Implementation Scope

* **MVP architecture** ready for **2-week implementation**
* **Local deployment** (single-user with secure authentication)
* **Configuration consistency** with existing translation workflows
* **Easily extensible** to multi-user or cloud deployment

---

## 🏗️ System Overview

### Primary Goals

1. Provide a **central repository** for AI and human poetry translations
2. Enable **side-by-side comparison** of translation versions
3. Integrate directly with **vpsweb translation workflows**
4. Support **local browsing, editing, and backups**
5. Maintain **configuration consistency** across the entire project

### Non-Goals (for this phase)

* Multi-user authentication (beyond single password)
* Real-time WebSocket updates
* Full-text search (planned for v0.4)
* Cloud deployment optimization

---

## ⚙️ Technical Architecture

### Stack Summary

| Layer       | Technology                     | Notes                               |
| ----------- | ------------------------------ | ----------------------------------- |
| Backend     | **FastAPI (async)**            | Core API + Web UI endpoints         |
| Database    | **SQLite (SQLAlchemy ORM)**    | Single unified DB, WAL mode, constraints |
| Frontend    | **HTMX + Tailwind CSS**        | Server-rendered reactive UI         |
| Integration | **Direct API**                 | Uses vpsweb.TranslationWorkflow API |
| Config      | **YAML + Pydantic**            | Consistent with existing vpsweb     |
| Security    | **Argon2 + HTTPBasic**         | Enterprise-grade password hashing   |
| Logging     | **structlog / JSON logs**      | For traceability and debugging      |

### System Components

```
FastAPI Web Server
├── Repository API (CRUD, compare, import/export)
├── Web UI (HTMX templates, Tailwind)
├── Integration Adapter (direct vpsweb calls)
├── Background Task Manager (FastAPI BackgroundTasks)
├── Security Manager (Argon2 + BasicAuth)
└── Configuration Manager (YAML + Pydantic)
```

### Directory Layout

```
src/vpsweb/repository/
├── main.py                # FastAPI entrypoint
├── database.py            # SQLAlchemy setup with constraints
├── models.py              # ORM models with CheckConstraints
├── schemas.py             # Pydantic API models
├── config.py              # Repository config loader (YAML + Pydantic)
├── security.py            # Argon2 + BasicAuth security
├── api/                   # REST endpoints
│   ├── poems.py
│   ├── translations.py
│   └── jobs.py
├── web/                   # HTMX templates + Tailwind
│   ├── routes.py
│   ├── templates/
│   └── static/
├── integration/
│   └── vpsweb_adapter.py  # Direct vpsweb calls
└── utils/
    ├── language_mapper.py # BCP-47 to natural language mapping
    ├── file_storage.py
    └── logger.py

# Existing configuration structure (REUSED)
config/
├── default.yaml          # Translation workflows
├── models.yaml           # LLM providers
├── wechat.yaml           # WeChat integration
├── repository.yaml       # Repository settings (NEW)
└── logging.yaml          # Logging configuration (NEW)
```

---

## 🧱 Data Model with Full Constraints

### Unified 4-table schema with comprehensive validation

### Tables

**poems**

```sql
CREATE TABLE poems (
    id TEXT PRIMARY KEY,                    -- ULID identifier
    poet_name TEXT NOT NULL,                -- Poet name
    poem_title TEXT NOT NULL,               -- Poem title
    source_language TEXT NOT NULL,          -- BCP-47 language code
    original_text TEXT NOT NULL,            -- Full poem text
    form TEXT,                             -- Poetic form (optional)
    period TEXT,                           -- Historical period (optional)
    created_at TEXT NOT NULL,              -- ISO timestamp
    updated_at TEXT NOT NULL,              -- ISO timestamp

    -- Data integrity constraints
    CONSTRAINT ck_poems_poet_name_not_empty
        CHECK (length(poet_name) > 0),
    CONSTRAINT ck_poems_poem_title_not_empty
        CHECK (length(poem_title) > 0),
    CONSTRAINT ck_poems_original_text_not_empty
        CHECK (length(original_text) > 0),
    CONSTRAINT ck_poems_source_language_valid
        CHECK (source_language IN ('en', 'zh-Hans', 'zh-Hant')),
    CONSTRAINT uq_poems_poem_title_lang
        UNIQUE (poet_name, poem_title, source_language)
);

-- Performance indexes
CREATE INDEX idx_poems_poet_name ON poems(poet_name);
CREATE INDEX idx_poems_source_language ON poems(source_language);
CREATE INDEX idx_poems_created_at ON poems(created_at);
CREATE INDEX idx_poems_poet_title ON poems(poem_title);
```

**translations**

```sql
CREATE TABLE translations (
    id TEXT PRIMARY KEY,                    -- ULID identifier
    poem_id TEXT NOT NULL,                  -- Foreign key to poems
    version INTEGER NOT NULL,               -- Translation version
    translator_type TEXT NOT NULL,          -- 'ai' or 'human'
    translator_info TEXT,                   -- Translator identifier
    target_language TEXT NOT NULL,          -- BCP-47 language code
    translated_text TEXT NOT NULL,          -- Translation result
    license TEXT DEFAULT 'CC-BY-4.0',      -- License type
    raw_path TEXT,                         -- Raw artifacts path
    created_at TEXT NOT NULL,              -- ISO timestamp

    -- Foreign key and constraints
    CONSTRAINT fk_translations_poem
        FOREIGN KEY (poem_id) REFERENCES poems(id) ON DELETE CASCADE,
    CONSTRAINT ck_translations_translator_type
        CHECK (translator_type IN ('ai', 'human')),
    CONSTRAINT ck_translations_text_not_empty
        CHECK (length(translated_text) > 0),
    CONSTRAINT ck_translations_target_language_valid
        CHECK (target_language IN ('en', 'zh-Hans', 'zh-Hant')),
    CONSTRAINT ck_translations_version_positive
        CHECK (version > 0),
    CONSTRAINT uq_translations_poem_version_type
        UNIQUE (poem_id, version, translator_type)
);

-- Performance indexes
CREATE INDEX idx_translations_poem_id ON translations(poem_id);
CREATE INDEX idx_translations_type ON translations(translator_type);
CREATE INDEX idx_translations_target ON translations(target_language);
CREATE INDEX idx_translations_created ON translations(created_at);
```

**ai_logs**

```sql
CREATE TABLE ai_logs (
    id TEXT PRIMARY KEY,                    -- ULID identifier
    translation_id TEXT NOT NULL,          -- Foreign key to translations
    model_name TEXT,                       -- LLM model name
    workflow_mode TEXT,                    -- vpsweb workflow mode
    token_usage_json TEXT,                 -- JSON token usage data
    cost_info_json TEXT,                   -- JSON cost information
    runtime_seconds REAL,                  -- Execution time in seconds
    notes TEXT,                            -- Additional notes
    created_at TEXT NOT NULL,              -- ISO timestamp

    -- Foreign key and constraints
    CONSTRAINT fk_ai_logs_translation
        FOREIGN KEY (translation_id) REFERENCES translations(id) ON DELETE CASCADE,
    CONSTRAINT ck_ai_logs_runtime_non_negative
        CHECK (runtime_seconds >= 0)
);

-- Performance indexes
CREATE INDEX idx_ai_logs_translation_id ON ai_logs(translation_id);
CREATE INDEX idx_ai_logs_model ON ai_logs(model_name);
```

**human_notes**

```sql
CREATE TABLE human_notes (
    id TEXT PRIMARY KEY,                    -- ULID identifier
    translation_id TEXT NOT NULL,          -- Foreign key to translations
    note_text TEXT NOT NULL,               -- Note content
    created_at TEXT NOT NULL,              -- ISO timestamp

    -- Foreign key and constraints
    CONSTRAINT fk_human_notes_translation
        FOREIGN KEY (translation_id) REFERENCES translations(id) ON DELETE CASCADE,
    CONSTRAINT ck_human_notes_text_not_empty
        CHECK (length(note_text) > 0)
);

-- Performance indexes
CREATE INDEX idx_human_notes_translation_id ON human_notes(translation_id);
```

---

## 🌐 API Specification

### REST Endpoints (Optimized)

```python
# Poem APIs
GET    /api/v1/poems              # List with filtering + translation counts
POST   /api/v1/poems              # Create new poem
GET    /api/v1/poems/{id}         # Get specific poem
PUT    /api/v1/poems/{id}         # Update poem
DELETE /api/v1/poems/{id}         # Delete poem (with cascade)

# Translation APIs
GET    /api/v1/translations?poem_id={id}  # List translations for poem
POST   /api/v1/translations              # Create new translation
GET    /api/v1/translations/{id}         # Get specific translation
PUT    /api/v1/translations/{id}         # Update translation
DELETE /api/v1/translations/{id}         # Delete translation

# Job APIs (BackgroundTasks)
POST   /api/v1/jobs/translate          # Queue AI translation
GET    /api/v1/jobs/{id}               # Check job status

# Import/Export APIs
POST   /api/v1/import/poems            # Import poem data
GET    /api/v1/export/poems            # Export poem data
POST   /api/v1/import/translations     # Import translation data
GET    /api/v1/export/translations     # Export translation data
```

### Optimized Poem Listing (Fixes N+1 Query)

```python
@router.get("/api/v1/poems", response_model=List[PoemResponse])
async def list_poems(
    poet: Optional[str] = Query(None),
    source_language: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session)
):
    """Get poems with translation counts (single query optimization)"""

    # Build subquery for translation counts
    count_subquery = (
        select(
            Translation.poem_id,
            func.count(Translation.id).label("translation_count")
        )
        .group_by(Translation.poem_id)
        .subquery()
    )

    # Main query with LEFT JOIN (single database roundtrip)
    query = (
        select(Poem, count_subquery.c.translation_count)
        .outerjoin(count_subquery, Poem.id == count_subquery.c.poem_id)
    )

    # Apply filters
    if poet:
        query = query.where(Poem.poet_name.ilike(f"%{poet}%"))
    if source_language:
        query = query.where(Poem.source_language == source_language)
    if search:
        query = query.where(
            Poem.poet_name.ilike(f"%{search}%") |
            Poem.poem_title.ilike(f"%{search}%") |
            Poem.original_text.ilike(f"%{search}%")
        )

    # Execute with pagination
    query = query.offset(skip).limit(limit).order_by(Poem.created_at.desc())
    result = await session.execute(query)

    # Build response
    poems_with_counts = []
    for poem, translation_count in result:
        poems_with_counts.append(
            PoemResponse(
                **poem.__dict__,
                translation_count=translation_count or 0
            )
        )

    return poems_with_counts
```

### Error Model

All errors return structured JSON:

```json
{
  "status": "error",
  "type": "ValidationError",
  "message": "Poem not found",
  "error_code": "POEM_NOT_FOUND",
  "timestamp": "2025-10-17T10:30:00Z"
}
```

---

## 🔒 Security Architecture (Enterprise-Grade)

### Password Security with Argon2

```python
# src/vpsweb/repository/security.py
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime, timedelta
import secrets

class SecurityManager:
    def __init__(self):
        # Industry-standard Argon2 configuration
        self.pwd_context = CryptContext(
            schemes=["argon2"],
            deprecated="auto",
            argon2__memory_cost=65536,    # 64MB memory
            argon2__time_cost=3,           # 3 iterations
            argon2__parallelism=4          # 4 parallel threads
        )
        self.active_sessions = {}

    def hash_password(self, password: str) -> str:
        """Hash password using Argon2"""
        return self.pwd_context.hash(password)

    def verify_password(self, password: str, hash: str) -> bool:
        """Verify password against Argon2 hash"""
        try:
            return self.pwd_context.verify(password, hash)
        except:
            return False

    def create_session(self) -> str:
        """Create secure session token"""
        session_id = secrets.token_urlsafe(32)
        self.active_sessions[session_id] = {
            "created_at": datetime.utcnow(),
            "last_accessed": datetime.utcnow()
        }
        return session_id

    async def authenticate_request(
        self,
        credentials: HTTPBasicCredentials = Depends(HTTPBasic())
    ):
        """HTTP Basic Auth with Argon2 verification"""
        config = config_manager.load_config()

        if not config.security.password_hash:
            return True  # No password set

        if not self.verify_password(credentials.password, config.security.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )

        return True

security_manager = SecurityManager()
```

### Configuration Security

```yaml
# config/repository.yaml (NEW - NO SECRETS STORED HERE)
repository:
  database_url: "sqlite+aiosqlite:///repository_root/repo.db"
  repo_root: "./repository_root"
  auto_create_dirs: true

security:
  session_timeout: 3600  # 1 hour
  api_key_required: false

server:
  host: "127.0.0.1"
  port: 8000
  reload: false
  debug: false

data:
  default_language: "en"
  supported_languages: ["en", "zh-Hans", "zh-Hant"]
  default_license: "CC-BY-4.0"
  max_poem_length: 10000
  max_translation_length: 20000
```

```bash
# .env.local (Git-ignored - SECRETS ONLY)
REPO_PASSWORD_HASH=$argon2id$v=19$m=65536,t=3,p=4$abc...xyz
```

---

## 🧩 Integration with vpsweb

### Direct API Integration (Path B)

```python
# src/vpsweb/repository/integration/vpsweb_adapter.py
from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.models.config import load_config
from src.vpsweb.repository.utils.language_mapper import LanguageMapper
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID
import json
from datetime import datetime

class VPSWebAdapter:
    """Direct vpsweb integration adapter"""

    def __init__(self):
        self.config = load_config("config/models.yaml")
        self.workflow = TranslationWorkflow(self.config)

    async def translate_poem(
        self,
        poem,
        target_language: str,
        workflow_mode: str = "hybrid",
        session: AsyncSession = None
    ) -> Dict[str, Any]:
        """Execute translation using vpsweb workflow"""
        try:
            # Convert BCP-47 to natural language for LLM
            language_pair = LanguageMapper.get_language_pair_for_llm(
                poem.source_language,
                target_language
            )

            # Execute vpsweb workflow
            result = await self.workflow.execute(
                text=poem.original_text,
                source_language=language_pair["source_language"],  # Natural language
                target_language=language_pair["target_language"],  # Natural language
                workflow_mode=workflow_mode
            )

            # Build translation record
            translation_data = {
                "id": str(ULID()),
                "poem_id": poem.id,
                "version": await self._get_next_translation_version(poem.id, session),
                "translator_type": "ai",
                "translator_info": f"vpsweb ({workflow_mode})",
                "target_language": target_language,  # Store BCP-47
                "translated_text": result.translated_text,
                "license": "CC-BY-4.0",
                "created_at": datetime.utcnow().isoformat()
            }

            # Build AI log record
            ai_log_data = {
                "id": str(ULID()),
                "translation_id": translation_data["id"],
                "model_name": getattr(result, 'model_name', None),
                "workflow_mode": workflow_mode,
                "token_usage_json": json.dumps({
                    "prompt_tokens": getattr(result, 'prompt_tokens', 0),
                    "completion_tokens": getattr(result, 'completion_tokens', 0),
                    "total_tokens": getattr(result, 'total_tokens', 0)
                }),
                "cost_info_json": json.dumps({
                    "prompt_cost": getattr(result, 'prompt_cost', 0.0),
                    "completion_cost": getattr(result, 'completion_cost', 0.0),
                    "total_cost": getattr(result, 'total_cost', 0.0)
                }),
                "runtime_seconds": getattr(result, 'runtime_seconds', 0),
                "notes": getattr(result, 'notes', ''),
                "created_at": datetime.utcnow().isoformat()
            }

            return {
                "success": True,
                "translation": translation_data,
                "ai_log": ai_log_data
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    async def _get_next_translation_version(
        self,
        poem_id: str,
        session: AsyncSession
    ) -> int:
        """Get next version number for poem's translations"""
        from src.vpsweb.repository.models import Translation
        from sqlalchemy import select, func

        stmt = select(func.max(Translation.version)).where(
            Translation.poem_id == poem_id
        )
        max_version = await session.scalar(stmt)
        return (max_version or 0) + 1
```

### Background Task Integration

```python
# src/vpsweb/repository/api/jobs.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from ..integration.vpsweb_adapter import VPSWebAdapter
from ..database import get_session
from ..models import Poem

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
vps_adapter = VPSWebAdapter()

@router.post("/translate")
async def submit_translation_job(
    poem_id: str,
    target_language: str,
    workflow_mode: str = "hybrid",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_session)
):
    """Submit AI translation job to background queue"""

    # Verify poem exists
    poem = await session.get(Poem, poem_id)
    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")

    # Queue background task
    background_tasks.add_task(
        vps_adapter.translate_poem,
        poem=poem,
        target_language=target_language,
        workflow_mode=workflow_mode,
        session=session
    )

    return {
        "status": "queued",
        "poem_id": poem_id,
        "target_language": target_language,
        "workflow_mode": workflow_mode
    }
```

---

## 🎨 Web UI Design (HTMX + Tailwind)

### Page Structure

* `/` → Dashboard: recent poems, statistics, activity
* `/poems` → Poem list with filters and search
* `/poems/{id}` → Poem detail with translations
* `/compare/{poem_id}` → Side-by-side translation comparison
* `/new/translation` → Start translation form
* `/settings` → Configuration and password management

### HTMX Features

* **Partial page updates** for real-time feedback
* **Inline editing** for poem and translation content
* **Dynamic filtering** without full page reloads
* **Progress indicators** for background jobs
* **Responsive design** with Tailwind utilities

### Template Example

```html
<!-- templates/poems/list.html -->
{% extends "base.html" %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <!-- Filters Section -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
        <form hx-get="/poems" hx-target="#poems-list" hx-indicator="#loading">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <input type="text" name="poet" placeholder="Filter by poet..."
                       class="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                <select name="source_language"
                        class="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="">All Languages</option>
                    <option value="en">English</option>
                    <option value="zh-Hans">Simplified Chinese</option>
                    <option value="zh-Hant">Traditional Chinese</option>
                </select>
                <input type="search" name="search" placeholder="Search content..."
                       class="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                <button type="submit"
                        class="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 transition">
                    Filter
                </button>
            </div>
        </form>
    </div>

    <!-- Loading Indicator -->
    <div id="loading" class="htmx-indicator hidden">
        <div class="text-center py-4">
            <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <p class="mt-2 text-gray-600">Loading poems...</p>
        </div>
    </div>

    <!-- Poems List -->
    <div id="poems-list" class="space-y-4">
        <!-- Content loaded via HTMX -->
    </div>
</div>
{% endblock %}
```

---

## 🧰 Configuration Management (Consistent)

### YAML + Pydantic Integration

```python
# src/vpsweb/repository/config.py
from pydantic import BaseModel, Field
from typing import Optional
import yaml
from pathlib import Path

class SecurityConfig(BaseModel):
    session_timeout: int = 3600
    api_key_required: bool = False

class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    debug: bool = False

class DataConfig(BaseModel):
    default_language: str = "en"
    supported_languages: list[str] = ["en", "zh-Hans", "zh-Hant"]
    default_license: str = "CC-BY-4.0"
    max_poem_length: int = 10000
    max_translation_length: int = 20000

class RepositoryConfig(BaseModel):
    database_url: str
    repo_root: str
    auto_create_dirs: bool = True
    security: SecurityConfig
    server: ServerConfig
    data: DataConfig

class ConfigManager:
    """Configuration manager using same patterns as existing vpsweb"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config/repository.yaml")
        self._config: Optional[RepositoryConfig] = None

    def load_config(self) -> RepositoryConfig:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            self._create_default_config()

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        self._config = RepositoryConfig(**config_data)
        return self._config

    def _create_default_config(self):
        """Create default configuration file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        default_config = {
            "repository": {
                "database_url": "sqlite+aiosqlite:///repository_root/repo.db",
                "repo_root": "./repository_root",
                "auto_create_dirs": True
            },
            "security": {
                "session_timeout": 3600,
                "api_key_required": False
            },
            "server": {
                "host": "127.0.0.1",
                "port": 8000,
                "reload": False,
                "debug": False
            },
            "data": {
                "default_language": "en",
                "supported_languages": ["en", "zh-Hans", "zh-Hant"],
                "default_license": "CC-BY-4.0",
                "max_poem_length": 10000,
                "max_translation_length": 20000
            }
        }

        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)

# Global instance (consistent with vpsweb patterns)
config_manager = ConfigManager()
```

### Language Mapper (Single Source of Truth)

```python
# src/vpsweb/repository/utils/language_mapper.py
from typing import Dict

class LanguageMapper:
    """Single source of truth for BCP-47 to natural language mapping"""

    _MAPPING = {
        # BCP-47 codes to natural language names (for LLM interaction)
        'en': 'English',
        'zh-Hans': 'Simplified Chinese',
        'zh-Hant': 'Traditional Chinese'
    }

    _REVERSE_MAPPING = {v: k for k, v in _MAPPING.items()}

    @classmethod
    def get_natural_language_name(cls, bcp47_code: str) -> str:
        """Convert BCP-47 code to natural language name"""
        return cls._MAPPING.get(bcp47_code, bcp47_code)

    @classmethod
    def get_bcp47_code(cls, natural_language: str) -> str:
        """Convert natural language name to BCP-47 code"""
        return cls._REVERSE_MAPPING.get(natural_language, natural_language)

    @classmethod
    def get_language_pair_for_llm(cls, source_code: str, target_code: str) -> Dict[str, str]:
        """Get language pair formatted for LLM interaction"""
        return {
            "source_language": cls.get_natural_language_name(source_code),
            "target_language": cls.get_natural_language_name(target_code)
        }

    @classmethod
    def get_supported_languages(cls) -> Dict[str, str]:
        """Get all supported language mappings"""
        return cls._MAPPING.copy()
```

---

## 🧪 Testing Strategy

### Test Structure

| Type        | Tools                     | Coverage Goal |
| ----------- | ------------------------- | ------------- |
| Unit        | pytest + httpx           | 85%           |
| Integration | pytest-asyncio           | CRUD + workflow |
| API         | pytest + TestClient      | All endpoints  |
| Security    | pytest + bandit          | Auth + input   |
| Database    | pytest + pytest-asyncio  | Schema + queries|

### Key Tests

```python
# tests/test_security.py
def test_argon2_password_hashing():
    """Test Argon2 password hashing and verification"""
    password = "test_password_123"
    security_manager = SecurityManager()

    # Hash password
    hash_result = security_manager.hash_password(password)
    assert hash_result.startswith("$argon2")

    # Verify correct password
    assert security_manager.verify_password(password, hash_result)

    # Verify incorrect password
    assert not security_manager.verify_password("wrong_password", hash_result)

# tests/test_optimized_queries.py
@pytest.mark.asyncio
async def test_poem_list_no_n_plus_one():
    """Test that poem listing doesn't cause N+1 queries"""
    # Create test data
    async with get_session() as session:
        # Create 10 poems with translations
        poems = []
        for i in range(10):
            poem = Poem(
                poet_name=f"Poet {i}",
                poem_title=f"Poem {i}",
                source_language="en",
                original_text=f"Original text {i}"
            )
            session.add(poem)
            poems.append(poem)

        await session.commit()

        # Add translations to each poem
        for poem in poems:
            for j in range(2):  # 2 translations per poem
                translation = Translation(
                    poem_id=poem.id,
                    version=j+1,
                    translator_type="ai",
                    target_language="zh-Hans",
                    translated_text=f"Translation {j} for poem {poem.id}"
                )
                session.add(translation)

        await session.commit()

    # Test API endpoint
    with TestClient(app) as client:
        response = client.get("/api/v1/poems?limit=20")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 10

        # Verify each poem has translation count
        for poem in data:
            assert "translation_count" in poem
            assert poem["translation_count"] == 2

# tests/test_vpsweb_integration.py
@pytest.mark.asyncio
async def test_vpsweb_adapter_integration():
    """Test direct vpsweb integration"""
    # Mock vpsweb workflow for testing
    class MockTranslationResult:
        def __init__(self):
            self.translated_text = "测试翻译"
            self.model_name = "test-model"
            self.workflow_mode = "hybrid"
            self.prompt_tokens = 50
            self.completion_tokens = 30
            self.total_tokens = 80
            self.runtime_seconds = 2.5

    adapter = VPSWebAdapter()

    # Mock the workflow execution
    original_execute = adapter.workflow.execute
    adapter.workflow.execute = lambda **kwargs: MockTranslationResult()

    try:
        # Create test poem
        poem = Poem(
            poet_name="Test Poet",
            poem_title="Test Poem",
            source_language="en",
            original_text="The mountains rise like ancient sentinels."
        )

        # Test translation
        result = await adapter.translate_poem(poem, "zh-Hans", "hybrid")

        assert result["success"] is True
        assert "translation" in result
        assert "ai_log" in result
        assert result["translation"]["translated_text"] == "测试翻译"
        assert result["translation"]["target_language"] == "zh-Hans"

    finally:
        # Restore original method
        adapter.workflow.execute = original_execute
```

---

## 💾 Backup & Data Lifecycle

### Backup Strategy

```python
# src/vpsweb/repository/cli.py (NEW)
import click
from pathlib import Path
import shutil
import json
from datetime import datetime

@click.group()
def cli():
    """VPSWeb Repository CLI commands"""
    pass

@cli.command()
@click.option('--output', '-o', help='Backup output directory')
def backup(output: str):
    """Create backup of repository data"""
    config = config_manager.load_config()
    repo_root = Path(config.repo_root)

    if output:
        backup_dir = Path(output)
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = Path(f"backups/backup_{timestamp}")

    backup_dir.mkdir(parents=True, exist_ok=True)

    # Backup database
    db_file = repo_root / "repo.db"
    if db_file.exists():
        shutil.copy2(db_file, backup_dir / "repo.db")

    # Backup data directory
    data_dir = repo_root / "data"
    if data_dir.exists():
        shutil.copytree(data_dir, backup_dir / "data", dirs_exist_ok=True)

    # Create backup metadata
    metadata = {
        "backup_time": datetime.utcnow().isoformat(),
        "version": "0.3.0",
        "files_copied": [
            str(p.relative_to(backup_dir))
            for p in backup_dir.rglob('*') if p.is_file()
        ]
    }

    with open(backup_dir / "backup_metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)

    click.echo(f"Backup created successfully: {backup_dir}")

@cli.command()
@click.argument('backup_path', type=click.Path(exists=True))
def restore(backup_path: str):
    """Restore repository from backup"""
    config = config_manager.load_config()
    repo_root = Path(config.repo_root)
    backup_dir = Path(backup_path)

    # Validate backup
    metadata_file = backup_dir / "backup_metadata.json"
    if not metadata_file.exists():
        raise click.ClickException("Invalid backup directory (missing metadata)")

    # Create backup of current data before restore
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    current_backup = repo_root.parent / f"pre_restore_backup_{timestamp}"
    shutil.copytree(repo_root, current_backup)

    try:
        # Clear current repository
        for item in repo_root.glob('*'):
            if item.is_file():
                item.unlink()
            elif item.is_dir() and item.name != 'data':  # Preserve data structure
                shutil.rmtree(item)

        # Restore from backup
        for item in backup_dir.glob('*'):
            if item.is_file() and item.name != 'backup_metadata.json':
                shutil.copy2(item, repo_root / item.name)
            elif item.is_dir():
                shutil.copytree(item, repo_root / item.name, dirs_exist_ok=True)

        click.echo(f"Repository restored from: {backup_path}")
        click.echo(f"Previous data backed up to: {current_backup}")

    except Exception as e:
        # Restore from backup if something went wrong
        shutil.rmtree(repo_root)
        shutil.copytree(current_backup, repo_root)
        raise click.ClickException(f"Restore failed: {e}. Previous data restored.")

if __name__ == '__main__':
    cli()
```

### Automated Backup

```bash
# Add to crontab for weekly backups
# 0 2 * * 0 cd /path/to/vpsweb && python -m src.vpsweb.repository.cli backup
```

---

## 🚀 Implementation Timeline (2 Weeks)

### Week 1: Foundation

| Day   | Tasks                                   | Deliverables                     |
| ----- | -------------------------------------- | -------------------------------- |
| 1     | Project scaffolding, DB setup, models | Working FastAPI app with SQLite   |
| 2     | Configuration system (YAML + Pydantic) | Config loading, validation       |
| 3     | Security system (Argon2 + BasicAuth)  | Secure authentication system     |
| 4     | Poem CRUD APIs with constraints        | Tested poem endpoints            |
| 5     | Translation CRUD APIs                  | Translation management working   |
| 6     | Database optimization (N+1 fix)        | Efficient queries, tests         |
| 7     | Basic HTMX templates + Tailwind        | Functional web UI                 |

### Week 2: Integration & Polish

| Day   | Tasks                                   | Deliverables                     |
| ----- | -------------------------------------- | -------------------------------- |
| 8     | vpsweb integration adapter             | AI translation jobs working      |
| 9     | BackgroundTasks integration            | Async job processing              |
| 10    | Advanced UI features (comparison view) | Complete user interface          |
| 11    | Import/Export functionality            | Data migration capabilities       |
| 12    | CLI backup/restore commands            | Data lifecycle management         |
| 13    | Comprehensive testing                  | 85%+ test coverage               |
| 14    | Documentation & final polish           | v0.3 release ready              |

---

## ✅ Success Metrics

### Functional Metrics
- [x] Complete CRUD operations for poems and translations
- [x] AI translation integration with vpsweb workflows
- [x] Secure authentication with Argon2
- [x] Side-by-side translation comparison
- [x] Import/export functionality
- [x] Backup and restore capabilities

### Performance Metrics
- **API Response Time**: < 300ms for 95% of requests
- **Page Load Time**: < 1s for web UI pages
- **Database Queries**: No N+1 query problems
- **Memory Usage**: < 512MB for typical usage

### Quality Metrics
- **Test Coverage**: 85%+ minimum
- **Security**: Argon2 password hashing, input validation
- **Code Quality**: Black formatting, mypy type checking
- **Documentation**: Complete API docs and user guide

### Usability Metrics
- **Learning Curve**: < 30 minutes for basic operations
- **Task Completion**: > 95% for common workflows
- **Error Recovery**: Graceful error handling and recovery

---

## 🧭 Future Extensions (v0.4+)

### v0.4 - Enhanced Features
* **WebSocket Updates**: Real-time job progress and notifications
* **Full-Text Search**: SQLite FTS5 integration for poems and translations
* **Advanced Filtering**: Date ranges, translation quality filters
* **Export Formats**: WeChat article format, PDF generation

### v0.5 - Multi-User & Cloud
* **User Accounts**: Role-based access control
* **Cloud Deployment**: PostgreSQL migration, Docker containerization
* **API Rate Limiting**: Throttling and usage monitoring
* **Advanced Analytics**: Translation statistics and usage patterns

### v0.6 - Enterprise Features
* **Workflow Orchestration**: Advanced job scheduling and dependencies
* **API Gateway**: External API access with OAuth2
* **Monitoring**: Comprehensive logging, metrics, and alerting
* **High Availability**: Load balancing, database replication

---

## 📋 System Requirements

### Minimum Requirements
* **Python**: 3.11+
* **Memory**: 512MB RAM
* **Storage**: 1GB (for data growth)
* **OS**: Linux, macOS, Windows (WSL2)

### Dependencies

```toml
# pyproject.toml (core dependencies)
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
sqlalchemy = "^2.0.0"
aiosqlite = "^0.19.0"
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
jinja2 = "^3.1.0"
python-multipart = "^0.0.6"
passlib = "^1.7.4"
argon2-cffi = "^23.1.0"
structlog = "^23.2.0"
click = "^8.1.0"
pyyaml = "^6.0.1"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
httpx = "^0.25.0"
black = "^23.10.0"
mypy = "^1.7.0"
bandit = "^1.7.5"
```

---

**End of PSD v0.3 — Modern, Secure, and Consistent Architecture for VPSWeb Repository System**

This document represents a balanced architectural approach that:
1. **Maintains consistency** with existing vpsweb configuration patterns
2. **Implements modern security** with Argon2 and comprehensive constraints
3. **Uses appropriate technology** (HTMX, BackgroundTasks) for the use case
4. **Provides realistic timeline** for 2-week implementation
5. **Ensures extensibility** for future multi-user and cloud deployment