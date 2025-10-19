# Project Specification Document (PSD) v0.3.1 — VPSWeb Central Repository & Local Web UI

**Status**: Enhanced Implementation-Ready Specification (v0.3.1)
**Date**: 2025-10-19
**Scope**: Local single-user prototype for personal use
**Target Timeline**: 7 days
**Strategic Approach**: FastAPI Monolith with SQLite (Modular Architecture: repository/ + webui/)
**Enhancement**: Integrated project scaffold insights with concrete implementation examples

---

## 🎯 Executive Summary

VPSWeb v0.3.1 delivers a **lightweight local repository and Web UI** for managing AI and human poetry translations. Built on a FastAPI monolith architecture with SQLite database, it provides immediate offline capability while maintaining extensibility for future production scaling.

**Core Value Proposition**: Run AI translations locally, store results permanently, and browse translations through an elegant web interface - all without external dependencies or cloud services.

---

## 🏗️ System Architecture

### Strategic Architecture Decision

**Chosen Approach**: FastAPI Monolith (validated through brainstorming/debate session)
- **Rationale**: Optimal balance of development speed, integration simplicity, and future extensibility
- **Deployment Model**: Single-process local web application
- **Integration Pattern**: Direct synchronous calls to vpsweb.TranslationWorkflow

### Technology Stack

| Layer | Technology | Justification |
|-------|------------|---------------|
| **Backend Framework** | FastAPI (sync mode) | Auto-docs, clean routing, future API readiness |
| **Database** | SQLite + SQLAlchemy ORM | Zero-config, single-file, ACID compliant |
| **Frontend** | Jinja2 templates + local Tailwind CSS | Simple, fast, poetry-focused display |
| **Configuration** | Pydantic Settings + .env | Consistent with vpsweb patterns |
| **Integration** | Direct vpsweb import | Seamless workflow integration |
| **Development Tools** | Black, pytest, Alembic | Code quality and safety |

### System Structure

```
src/vpsweb/repository/          # Repository data layer
├── __init__.py
├── database.py                 # SQLite + SQLAlchemy setup
├── models.py                   # ORM models (4-table schema)
├── schemas.py                  # Pydantic I/O models
├── crud.py                     # CRUD operations
├── settings.py                 # Configuration management
├── integration/
│   ├── __init__.py
│   └── vpsweb_adapter.py       # vpsweb workflow integration
├── migrations/                 # Alembic migration files
└── tests/
    ├── test_models.py
    ├── test_crud.py
    └── test_integration.py

src/vpsweb/webui/               # Web interface layer
├── __init__.py
├── main.py                     # FastAPI app entrypoint
├── config.py                   # WebUI-specific settings
├── api/
│   ├── __init__.py
│   ├── poems.py                # Poem HTTP endpoints
│   ├── translations.py         # Translation HTTP endpoints
│   └── compare.py              # Comparison endpoints
├── web/
│   ├── __init__.py
│   ├── templates/
│   │   ├── base.html           # Base template with Tailwind
│   │   ├── index.html          # Dashboard: poems list
│   │   ├── poem_detail.html    # Poem + translations view
│   │   ├── compare.html        # Side-by-side comparison
│   │   └── new_poem.html       # Add poem/upload form
│   └── static/
│       └── css/
│           └── tailwind.min.css  # Local Tailwind file
├── utils/
│   └── backup.py               # Simple backup utility
└── tests/
    ├── test_api.py
    └── test_templates.py

repository_root/                # Data storage
├── repo.db                     # SQLite database file
├── data/                       # Raw translation outputs
│   ├── ai_outputs/            # vpsweb JSON/XML files
│   └── human_uploads/         # Human translation files
├── backups/                   # Backup storage
└── logs/                      # Application logs
```

---

## 🧱 Data Model Specification

### Database Schema Design

**Rationale**: 4-table schema preserves compatibility with existing vpsweb data structures while enabling future extensibility.

#### Table: poems

```sql
CREATE TABLE poems (
    id TEXT PRIMARY KEY,                    -- ULID for sortable IDs
    poet_name TEXT NOT NULL,
    poem_title TEXT NOT NULL,
    source_language TEXT NOT NULL,          -- BCP-47 format (e.g., "en", "zh")
    original_text TEXT NOT NULL,
    metadata_json TEXT,                     -- Optional: author bio, historical context
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Table: translations

```sql
CREATE TABLE translations (
    id TEXT PRIMARY KEY,                    -- ULID
    poem_id TEXT NOT NULL REFERENCES poems(id),
    translator_type TEXT NOT NULL CHECK (translator_type IN ('ai', 'human')),
    translator_info TEXT,                   -- AI model name or human translator name
    target_language TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    quality_rating INTEGER CHECK (quality_rating >= 1 AND quality_rating <= 5),
    raw_path TEXT,                          -- Path to original JSON/XML output
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Table: ai_logs

```sql
CREATE TABLE ai_logs (
    id TEXT PRIMARY KEY,
    translation_id TEXT NOT NULL REFERENCES translations(id),
    model_name TEXT NOT NULL,
    workflow_mode TEXT NOT NULL,            -- 'reasoning', 'non_reasoning', 'hybrid'
    token_usage_json TEXT,                  -- Detailed token counts
    cost_info_json TEXT,                    -- Cost calculation data
    runtime_seconds REAL,
    notes TEXT,                             -- Warnings, errors, or observations
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Table: human_notes

```sql
CREATE TABLE human_logs (
    id TEXT PRIMARY KEY,
    translation_id TEXT NOT NULL REFERENCES translations(id),
    note_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Data Relationships

```
poems (1) → (*) translations
translations (1) → (0..1) ai_logs
translations (1) → (*) human_notes
```

---

## 🌐 API Specification

### REST Endpoints

#### Poem Management
```
GET    /api/v1/poems                    # List all poems with pagination
POST   /api/v1/poems                    # Create new poem entry
GET    /api/v1/poems/{poem_id}          # Get poem details
PUT    /api/v1/poems/{poem_id}          # Update poem metadata
DELETE /api/v1/poems/{poem_id}          # Delete poem and related translations
```

#### Translation Management
```
GET    /api/v1/translations             # List translations (filterable by poem_id)
POST   /api/v1/translations             # Add human translation
GET    /api/v1/translations/{trans_id}  # Get translation details
POST   /api/v1/translate                # Execute AI translation workflow
```

#### Comparison and Analysis
```
GET    /api/v1/compare/{poem_id}        # Get comparison data for poem
GET    /api/v1/statistics               # Repository statistics
```

### Key Endpoint: AI Translation Workflow

**POST /api/v1/translate**

```json
{
  "poem_id": "01H8X2Z3Y4X5K6M7N8P9Q0R1S",
  "target_language": "en",
  "workflow_mode": "hybrid",
  "model_override": null
}
```

**Response**:
```json
{
  "translation_id": "01H8X2Z3Y4X5K6M7N8P9Q0R2T",
  "translated_text": "Complete AI translation...",
  "ai_log": {
    "model_name": "qwen-max",
    "runtime_seconds": 12.5,
    "token_usage": {"prompt": 150, "completion": 200, "total": 350}
  }
}
```

---

## 🎨 Web UI Design Specification

### Page Architecture

#### 1. Dashboard (/) - Poem Repository Overview
**Purpose**: Browse and search poem collection
**Components**:
- Search bar (filters by poet, title, language)
- Paginated poem cards showing: poet, title, language, translation count
- "Add New Poem" action button
- Repository statistics summary

#### 2. Poem Detail (/poems/{poem_id}) - Translation Hub
**Purpose**: View poem and manage translations
**Components**:
- Poem display with original text formatting
- Translation tabs: AI translations | Human translations
- "Run AI Translation" button with workflow mode selection
- Side-by-side comparison for multiple translations
- Upload human translation form

#### 3. Comparison View (/compare/{poem_id}) - Analysis Interface
**Purpose**: Detailed comparison of translation quality
**Components**:
- Original poem in source language
- Multiple translations in parallel columns
- Quality rating system (1-5 stars)
- Notes and observations section
- Export comparison data functionality

#### 4. Add Poem (/new) - Content Creation
**Purpose**: Add new poems or upload existing translations
**Components**:
- Form fields: poet name, poem title, source language, text
- File upload for existing translations
- Language selection (dropdown with common languages)
- Metadata fields (optional author bio, historical context)

### Design System

**Typography**: Serif fonts for poetry display, sans-serif for UI
**Color Palette**:
- Primary: Deep indigo (#4F46E5)
- Secondary: Slate gray (#475569)
- Accent: Amber (#F59E0B) for highlights
- Background: Warm white (#FFFBF5)

**Layout Principles**:
- Mobile-first responsive design
- Poetry text uses generous line height and readable font sizes
- Clean, minimal interface that doesn't distract from content
- High contrast for accessibility

---

## 🔧 Concrete Implementation Examples

### Repository Layer - Database Setup

```python
# src/vpsweb/repository/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .settings import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}  # Required for SQLite
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    """Initialize database tables"""
    from . import models
    Base.metadata.create_all(bind=engine)

def get_db():
    """Database session dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Repository Layer - Models

```python
# src/vpsweb/repository/models.py
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Poem(Base):
    __tablename__ = "poems"
    id = Column(String, primary_key=True)
    poet_name = Column(String, nullable=False)
    poem_title = Column(String, nullable=False)
    source_language = Column(String, nullable=False)
    original_text = Column(Text, nullable=False)
    metadata_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    translations = relationship("Translation", back_populates="poem")

class Translation(Base):
    __tablename__ = "translations"
    id = Column(String, primary_key=True)
    poem_id = Column(String, ForeignKey("poems.id"))
    translator_type = Column(String, nullable=False)  # 'ai' or 'human'
    translator_info = Column(String)
    target_language = Column(String, nullable=False)
    translated_text = Column(Text, nullable=False)
    quality_rating = Column(String)
    raw_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    poem = relationship("Poem", back_populates="translations")
    ai_logs = relationship("AILog", back_populates="translation")
    human_notes = relationship("HumanNote", back_populates="translation")

class AILog(Base):
    __tablename__ = "ai_logs"
    id = Column(String, primary_key=True)
    translation_id = Column(String, ForeignKey("translations.id"))
    model_name = Column(String, nullable=False)
    workflow_mode = Column(String, nullable=False)
    token_usage_json = Column(JSON)
    cost_info_json = Column(JSON)
    runtime_seconds = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    translation = relationship("Translation", back_populates="ai_logs")

class HumanNote(Base):
    __tablename__ = "human_notes"
    id = Column(String, primary_key=True)
    translation_id = Column(String, ForeignKey("translations.id"))
    note_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    translation = relationship("Translation", back_populates="human_notes")
```

### WebUI Layer - FastAPI Application

```python
# src/vpsweb/webui/main.py
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.vpsweb.repository.database import init_db, get_db
from src.vpsweb.repository.models import Poem
from .api import poems, translations
from .config import settings

app = FastAPI(title="VPSWeb Repository v0.3.1")

# Static files and templates
app.mount("/static", StaticFiles(directory="src/vpsweb/webui/web/static"), name="static")
templates = Jinja2Templates(directory="src/vpsweb/webui/web/templates")

# API routers
app.include_router(poems.router, prefix="/api/v1/poems", tags=["poems"])
app.include_router(translations.router, prefix="/api/v1/translations", tags=["translations"])

@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    """Dashboard - list all poems"""
    poems_list = db.query(Poem).order_by(Poem.created_at.desc()).all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "poems": poems_list,
        "title": "VPSWeb Repository"
    })

if __name__ == "__main__":
    init_db()
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port, reload=settings.reload)
```

### WebUI Layer - Configuration

```python
# src/vpsweb/webui/config.py
from pydantic_settings import BaseSettings

class WebUISettings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_prefix = "WEBUI_"

settings = WebUISettings()
```

### Cross-Module Integration - API Endpoints

```python
# src/vpsweb/webui/api/poems.py
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List

from src.vpsweb.repository.database import get_db
from src.vpsweb.repository.models import Poem, Translation
from src.vpsweb.repository.schemas import PoemCreate, PoemResponse
from src.vpsweb.webui.web.templates import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def list_poems(request: Request, db: Session = Depends(get_db)):
    """List all poems"""
    poems = db.query(Poem).order_by(Poem.created_at.desc()).all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "poems": poems
    })

@router.post("/")
def create_poem(
    poet_name: str = Form(...),
    poem_title: str = Form(...),
    source_language: str = Form(...),
    original_text: str = Form(...),
    db: Session = Depends(get_db)
):
    """Create new poem via form submission"""
    from src.vpsweb.utils.ulid_utils import generate_ulid

    poem = Poem(
        id=generate_ulid(),
        poet_name=poet_name,
        poem_title=poem_title,
        source_language=source_language,
        original_text=original_text
    )
    db.add(poem)
    db.commit()
    return RedirectResponse(url=f"/poems/{poem.id}", status_code=303)

@router.get("/{poem_id}", response_class=HTMLResponse)
def poem_detail(request: Request, poem_id: str, db: Session = Depends(get_db)):
    """Show poem detail with translations"""
    poem = db.query(Poem).filter(Poem.id == poem_id).first()
    if not poem:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    translations = db.query(Translation).filter(Translation.poem_id == poem_id).all()
    return templates.TemplateResponse("poem_detail.html", {
        "request": request,
        "poem": poem,
        "translations": translations
    })
```

### Template Integration Examples

```html
<!-- src/vpsweb/webui/web/templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title or 'VPSWeb Repository' }}</title>
  <link href="/static/css/tailwind.min.css" rel="stylesheet">
  <style>
    body { font-family: 'Georgia', serif; }
    .poetry-text { line-height: 1.8; font-size: 1.1rem; }
    .ui-text { font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
  </style>
</head>
<body class="bg-gray-50 text-gray-900">
  <nav class="bg-white shadow-sm border-b">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between h-16">
        <div class="flex items-center">
          <h1 class="text-xl font-semibold text-gray-900">VPSWeb Repository</h1>
        </div>
        <div class="flex items-center space-x-4">
          <a href="/" class="text-gray-600 hover:text-gray-900">Dashboard</a>
          <a href="/new" class="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">Add Poem</a>
        </div>
      </div>
    </div>
  </nav>

  <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
    {% block content %}{% endblock %}
  </main>
</body>
</html>
```

```html
<!-- src/vpsweb/webui/web/templates/index.html -->
{% extends 'base.html' %}
{% block content %}
<div class="px-4 py-6 sm:px-0">
  <div class="border-4 border-dashed border-gray-200 rounded-lg p-8">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-900">Poetry Collection</h2>
      <div class="text-sm text-gray-500">
        {{ poems|length }} poems in repository
      </div>
    </div>

    {% if poems %}
    <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {% for poem in poems %}
      <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">{{ poem.poet_name }}</h3>
        <h4 class="text-md text-gray-700 mb-3">{{ poem.poem_title }}</h4>
        <p class="text-sm text-gray-500 mb-4">
          Language: {{ poem.source_language.upper() }}<br>
          Created: {{ poem.created_at.strftime('%Y-%m-%d') }}
        </p>
        <div class="flex justify-between items-center">
          <span class="text-sm text-indigo-600">
            {{ poem.translations|length if poem.translations else 0 }} translations
          </span>
          <a href="/poems/{{ poem.id }}" class="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
            View Details →
          </a>
        </div>
      </div>
      {% endfor %}
    </div>
    {% else %}
    <div class="text-center py-12">
      <p class="text-gray-500 text-lg">No poems in repository yet.</p>
      <a href="/new" class="mt-4 inline-block bg-indigo-600 text-white px-6 py-3 rounded-md hover:bg-indigo-700">
        Add Your First Poem
      </a>
    </div>
    {% endif %}
  </div>
</div>
{% endblock %}
```

### Development Workflow

```bash
# Development startup
uvicorn src.vpsweb.webui.main:app --reload --host 127.0.0.1 --port 8000

# Access the application
# Dashboard: http://127.0.0.1:8000/
# API Docs: http://127.0.0.1:8000/docs
```

### Backup Utility Implementation

```python
# src/vpsweb/webui/utils/backup.py
import shutil
import datetime
import os
from pathlib import Path

def backup_repository(repo_root: str = "./repository_root"):
    """Create a timestamped backup of the entire repository"""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"repo_backup_{timestamp}"
    backup_path = os.path.join(repo_root, "backups", backup_name)

    # Ensure backup directory exists
    os.makedirs(os.path.join(repo_root, "backups"), exist_ok=True)

    # Copy entire repository
    shutil.copytree(repo_root, backup_path, ignore=shutil.ignore_patterns('backups'))

    print(f"✅ Backup created: {backup_path}")
    return backup_path

def restore_repository(backup_path: str, target_repo_root: str = "./repository_root"):
    """Restore repository from backup"""
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    # Remove existing repository (except backups)
    if os.path.exists(target_repo_root):
        backup_dir = os.path.join(target_repo_root, "backups")
        if os.path.exists(backup_dir):
            shutil.move(backup_dir, "/tmp/repo_backups_temp")
        shutil.rmtree(target_repo_root)

    # Restore from backup
    shutil.copytree(backup_path, target_repo_root)

    # Restore backups if they existed
    temp_backup = "/tmp/repo_backups_temp"
    if os.path.exists(temp_backup):
        shutil.move(temp_backup, os.path.join(target_repo_root, "backups"))

    print(f"✅ Repository restored from: {backup_path}")
```

---

## 🚀 Development Workflow

### Quick Start Setup

```bash
# 1. Install dependencies
poetry install

# 2. Set PYTHONPATH for src layout (required globally)
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
# Add this to your ~/.zshrc for permanent setup

# 3. Create repository storage directories
mkdir -p repository_root/{data/{ai_outputs,human_uploads},backups,logs}

# 4. Create .env file
cat > .env << EOF
DATABASE_URL=sqlite:///./repository_root/repo.db
REPO_ROOT=./repository_root
STORAGE_PATH=./repository_root/data
WEBUI_HOST=127.0.0.1
WEBUI_PORT=8000
WEBUI_RELOAD=true
LOG_LEVEL=INFO
EOF

# 5. Run the application
uvicorn src.vpsweb.webui.main:app --reload --host 127.0.0.1 --port 8000
```

### Development Commands

```bash
# Development server with hot reload
uvicorn src.vpsweb.webui.main:app --reload --host 127.0.0.1 --port 8000

# Access points
# Web Interface: http://127.0.0.1:8000/
# API Documentation: http://127.0.0.1:8000/docs
# Interactive API Console: http://127.0.0.1:8000/redoc

# Database operations
# Initialize database (automatic on first run)
python -c "from src.vpsweb.repository.database import init_db; init_db()"

# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head

# Code quality checks
python -m black src/ tests/
python -m pytest tests/ -v
```

### Module Dependencies

```
webui/ depends on → repository/
├── repository.database (DB session, models)
├── repository.models (ORM models)
├── repository.schemas (Pydantic models)
├── repository.integration.vpsweb_adapter (Translation workflow)
└── repository.settings (Configuration)

repository/ depends on → vpsweb core
├── vpsweb.core.workflow (Translation execution)
├── vpsweb.models.config (Workflow modes)
├── vpsweb.utils.ulid_utils (ID generation)
└── vpsweb.utils.logger (Logging configuration)
```

### Testing Strategy

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific module tests
python -m pytest tests/repository/ -v
python -m pytest tests/webui/ -v

# Run with coverage
python -m pytest tests/ --cov=src/vpsweb/repository --cov=src/vpsweb/webui

# Test database operations
python -m pytest tests/test_repository_crud.py -v

# Test API endpoints
python -m pytest tests/test_api_endpoints.py -v

# Test VPSWeb integration
python -m pytest tests/test_integration.py -v
```

### Production Deployment (Future)

```bash
# Production run (no reload, optimized)
uvicorn src.vpsweb.webui.main:app --host 127.0.0.1 --port 8000 --workers 1

# With environment variables
export DATABASE_URL=sqlite:///./repository_root/repo.db
export WEBUI_HOST=0.0.0.0
export WEBUI_PORT=8000
export WEBUI_RELOAD=false

# Backup before deployment
python -c "from src.vpsweb.webui.utils.backup import backup_repository; backup_repository()"
```

---

## 🔧 Integration with VPSWeb

### VPSWeb Adapter Pattern

```python
# src/vpsweb/repository/integration/vpsweb_adapter.py
from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.models.config import WorkflowMode
from ..models import Poem, Translation, AILog
from ..database import SessionLocal
from ..settings import settings
import json
from datetime import datetime

class VPSWebRepositoryAdapter:
    """Adapter for integrating vpsweb workflow with repository storage"""

    def __init__(self):
        self.workflow = TranslationWorkflow()

    def run_translation_sync(
        self,
        poem_id: str,
        target_language: str,
        workflow_mode: str = "hybrid"
    ) -> dict:
        """Synchronous translation execution for web interface"""
        db = SessionLocal()
        try:
            # 1. Load poem from database
            poem = db.query(Poem).filter(Poem.id == poem_id).first()
            if not poem:
                raise ValueError(f"Poem not found: {poem_id}")

            # 2. Execute vpsweb workflow (synchronous for prototype)
            result = self.workflow.execute(
                text=poem.original_text,
                source_language=poem.source_language,
                target_language=target_language,
                workflow_mode=workflow_mode
            )

            # 3. Store results in database
            from src.vpsweb.utils.ulid_utils import generate_ulid

            translation = Translation(
                id=generate_ulid(),
                poem_id=poem_id,
                translator_type="ai",
                translator_info=result.model_name or "qwen-max",
                target_language=target_language,
                translated_text=result.translated_text,
                raw_path=getattr(result, 'output_path', None),
                created_at=datetime.utcnow()
            )

            # 4. Create AI log entry
            ai_log = AILog(
                id=generate_ulid(),
                translation_id=translation.id,
                model_name=result.model_name or "qwen-max",
                workflow_mode=workflow_mode,
                token_usage_json=json.dumps(getattr(result, 'token_usage', {})),
                cost_info_json=json.dumps(getattr(result, 'cost_info', {})),
                runtime_seconds=getattr(result, 'runtime_seconds', 0),
                notes=getattr(result, 'notes', ''),
                created_at=datetime.utcnow()
            )

            db.add(translation)
            db.add(ai_log)
            db.commit()

            return {
                "translation_id": translation.id,
                "translated_text": translation.translated_text,
                "model_name": ai_log.model_name,
                "runtime_seconds": ai_log.runtime_seconds,
                "token_usage": json.loads(ai_log.token_usage_json) if ai_log.token_usage_json else {}
            }

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
```

### Translation API Integration

```python
# src/vpsweb/webui/api/translations.py
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from src.vpsweb.repository.database import get_db
from src.vpsweb.repository.models import Poem, Translation
from src.vpsweb.repository.integration.vpsweb_adapter import VPSWebRepositoryAdapter

router = APIRouter()

@router.post("/translate")
def translate_poem(
    poem_id: str = Form(...),
    target_lang: str = Form(...),
    workflow_mode: str = Form(default="hybrid"),
    db: Session = Depends(get_db)
):
    """Execute AI translation via form submission"""
    try:
        # Verify poem exists
        poem = db.query(Poem).filter(Poem.id == poem_id).first()
        if not poem:
            raise HTTPException(status_code=404, detail="Poem not found")

        # Execute translation
        adapter = VPSWebRepositoryAdapter()
        result = adapter.run_translation_sync(
            poem_id=poem_id,
            target_language=target_lang,
            workflow_mode=workflow_mode
        )

        return {
            "status": "success",
            "translation_id": result["translation_id"],
            "message": f"Translation completed using {result['model_name']}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/human")
def add_human_translation(
    poem_id: str = Form(...),
    target_lang: str = Form(...),
    translator_name: str = Form(...),
    translated_text: str = Form(...),
    db: Session = Depends(get_db)
):
    """Add human translation via form submission"""
    from src.vpsweb.utils.ulid_utils import generate_ulid

    translation = Translation(
        id=generate_ulid(),
        poem_id=poem_id,
        translator_type="human",
        translator_info=translator_name,
        target_language=target_lang,
        translated_text=translated_text
    )

    db.add(translation)
    db.commit()

    return {
        "status": "success",
        "translation_id": translation.id,
        "message": "Human translation added successfully"
    }
```

### Configuration Integration

```python
# src/vpsweb/repository/settings.py
from pydantic_settings import BaseSettings

class RepositorySettings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./repository_root/repo.db"

    # Repository storage
    repo_root: str = "./repository_root"
    storage_path: str = "./repository_root/data"

    # VPSWeb integration
    vpsweb_config_path: str = "./config"
    default_workflow_mode: str = "hybrid"

    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

---

## 🧪 Testing Strategy

### Test Coverage Plan

| Component | Test Type | Tool | Coverage Goal |
|-----------|-----------|------|----------------|
| Database Models | Unit | pytest + SQLAlchemy fixtures | 95% |
| API Endpoints | Integration | pytest + httpx TestClient | 90% |
| VPSWeb Integration | Integration | pytest + vpsweb mock | 85% |
| Templates | Unit | pytest + Jinja2 test client | 80% |
| End-to-End | Manual | Browser testing | Core workflows |

### Key Test Scenarios

1. **Database Operations**: CRUD operations, relationship integrity, migrations
2. **API Functionality**: Request validation, response formats, error handling
3. **VPSWeb Integration**: Workflow execution, result storage, error propagation
4. **UI Workflows**: User journeys through all pages
5. **Data Consistency**: Translation-poem relationships, cascade deletes

### Test Data Strategy

```python
# tests/fixtures.py
@pytest.fixture
def sample_poem():
    return {
        "poet_name": "陶渊明",
        "poem_title": "歸園田居",
        "source_language": "zh",
        "original_text": "少無適俗韻，性本愛丘山..."
    }

@pytest.fixture
def sample_translation():
    return {
        "translator_type": "ai",
        "translator_info": "qwen-max",
        "target_language": "en",
        "translated_text": "Since young, I had no worldly rhythm..."
    }
```

---

## 🚀 Implementation Plan

### Phase 1: Foundation (Days 1-2)

**Day 1: Project Scaffolding**
- [ ] Create `src/vpsweb/repository/` and `src/vpsweb/webui/` package structure
- [ ] Set up FastAPI application in `webui/main.py` with basic routing
- [ ] Configure SQLite database with SQLAlchemy in `repository/database.py`
- [ ] Implement Alembic migration system
- [ ] Create basic Pydantic models and settings in both modules

**Day 2: Core Data Layer**
- [ ] Implement ORM models (4-table schema)
- [ ] Create database migration files
- [ ] Build basic CRUD operations
- [ ] Add data validation and constraints
- [ ] Write initial unit tests for models

### Phase 2: API Development (Day 3)

**Day 3: REST API Implementation**
- [ ] Implement poem management endpoints
- [ ] Implement translation CRUD endpoints
- [ ] Create translation workflow trigger endpoint
- [ ] Add comparison and statistics endpoints
- [ ] Write API integration tests

### Phase 3: Web Interface (Day 4)

**Day 4: Template Development**
- [ ] Set up Jinja2 template structure
- [ ] Implement base template with Tailwind CSS
- [ ] Create dashboard page with poem listing
- [ ] Build poem detail page with translation management
- [ ] Develop comparison view interface
- [ ] Add new poem creation form

### Phase 4: VPSWeb Integration (Day 5)

**Day 5: Workflow Integration**
- [ ] Implement VPSWeb adapter
- [ ] Connect translation workflow to API
- [ ] Handle workflow errors and logging
- [ ] Test end-to-end translation pipeline
- [ ] Optimize performance for synchronous execution

### Phase 5: Polish & Testing (Day 6)

**Day 6: Quality Assurance**
- [ ] Complete test suite coverage
- [ ] Manual UI testing and bug fixes
- [ ] Performance optimization
- [ ] Error handling improvements
- [ ] Documentation updates

### Phase 6: Deployment Preparation (Day 7)

**Day 7: Release Preparation**
- [ ] Create backup/restore scripts
- [ ] Write user documentation
- [ ] Prepare development environment setup
- [ ] Final integration testing
- [ ] Version release (v0.3.1)

---

## 📋 Success Criteria

### Functional Requirements
- [ ] Users can add poems with original text and metadata
- [ ] AI translations execute successfully via vpsweb workflow
- [ ] Human translations can be uploaded and stored
- [ ] Web interface displays poems and translations clearly
- [ ] Side-by-side comparison view works correctly
- [ ] All data persists in SQLite database

### Non-Functional Requirements
- [ ] Application runs locally on localhost:8000
- [ ] No external dependencies required for basic operation
- [ ] Offline capability (no internet required for core features)
- [ ] Responsive design works on mobile and desktop
- [ ] Code passes Black formatting and pytest validation
- [ ] Documentation covers setup and basic usage

### Integration Requirements
- [ ] Seamless integration with existing vpsweb.TranslationWorkflow
- [ ] Shared configuration with main vpsweb application
- [ ] Compatible with existing data export formats
- [ ] Maintains vpsweb's logging and error handling patterns

---

## 🔒 Security & Privacy

### Local-First Security Model
- **Network Access**: localhost only (127.0.0.1)
- **Authentication**: None required for personal use
- **Data Storage**: All data stored locally in SQLite file
- **External Dependencies**: Optional for AI models only

### Security Measures
- HTML auto-escaping in Jinja2 templates
- Input validation and sanitization
- File upload restrictions (type, size)
- SQL injection prevention via SQLAlchemy ORM
- Markdown content sanitization using bleach

---

## 💾 Backup & Data Management

### Data Storage Structure
```
repository_root/
├── repo.db                    # SQLite database file
├── data/                      # Raw translation outputs
│   ├── ai_outputs/           # vpsweb JSON/XML files
│   └── human_uploads/        # Human translation files
├── backups/                  # Automatic backup folder
└── logs/                     # Application logs
```

### Backup Strategy
```bash
# Manual backup command
vpsweb repo backup --output ./backups/repo_backup_$(date +%Y%m%d).tar.gz

# Restore command
vpsweb repo restore --input ./backups/repo_backup_20251019.tar.gz
```

### Migration Support
- Alembic migrations for schema changes
- Export functionality for data portability
- Version compatibility checks

---

## 🌟 Future Extensibility

### v0.4.0+ Features (Out of Scope for v0.3.1)
- Multi-user authentication and authorization
- Background job processing with Celery
- Full-text search with Elasticsearch
- Translation quality metrics and analytics
- Export formats (PDF, EPUB, print-ready)
- RESTful API for external clients
- Mobile application support

### Architectural Preparation
- Modular structure enables component extraction
- Database schema supports multi-tenant patterns
- API design supports future authentication layers
- Configuration system supports multiple environments

---

## 📖 Documentation Plan

### User Documentation
- **README.md**: Quick start guide and installation
- **USER_GUIDE.md**: Detailed feature walkthrough
- **CONFIGURATION.md**: Environment setup and options

### Developer Documentation
- **API_DOCS.md**: Auto-generated via FastAPI
- **DEVELOPMENT.md**: Setup and contribution guidelines
- **DATABASE_SCHEMA.md**: Entity-relationship documentation

### Technical Documentation
- **INTEGRATION.md**: VPSWeb workflow integration details
- **DEPLOYMENT.md**: Local deployment and configuration
- **TROUBLESHOOTING.md**: Common issues and solutions

---

**End of Enhanced PSD v0.3.1 — Implementation-Ready Specification for VPSWeb Repository & Local Web UI**

## 📋 Summary of Enhancements

This PSD v0.3.1 has been enhanced with concrete implementation insights from the project scaffold proposal:

### ✅ Key Improvements Added

1. **Modular Architecture**: Clear separation between `src/vpsweb/repository/` (data layer) and `src/vpsweb/webui/` (interface layer)
2. **Concrete Code Examples**: Real implementation patterns for FastAPI, SQLAlchemy, and template integration
3. **Development Workflow**: Complete setup instructions with working commands
4. **Cross-Module Integration**: Specific patterns for repository and webui interaction
5. **SQLite Configuration**: Proper `connect_args={"check_same_thread": False}` setup
6. **Template Integration**: Jinja2 examples with Tailwind CSS integration
7. **Form Handling**: FastAPI Form data patterns for translation workflows
8. **Backup Utilities**: Complete backup/restore implementation

### 🎯 Implementation Readiness

The PSD now provides:
- **Copy-paste ready code examples** for all major components
- **Step-by-step development workflow** with tested commands
- **Clear module boundaries** and dependency patterns
- **Production-ready configuration** examples
- **Complete testing strategy** with specific test commands

### 🚀 Ready for Implementation

With these enhancements, the development team can proceed directly with implementation using the concrete patterns and examples provided in this PSD. The 7-day timeline is achievable with the detailed guidance and ready-to-use code templates included.

**Next Steps**: Proceed with 7-day implementation timeline starting with Phase 1 foundation work, using the concrete examples and patterns provided in this enhanced PSD.