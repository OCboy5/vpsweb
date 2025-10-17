# VPSWeb Central Repository & Local Web UI — Finalized Strategy

**Version**: 1.0 (Final Strategy for PSD Generation)
**Date**: 2025-10-17
**Scope**: vpsweb package module for local personal-use system
**Timeline**: 2-week prototype plan

## Executive Summary

This strategy establishes a lightweight central repository and web interface for vpsweb translations, built as part of the vpsweb package. The system provides local storage, browsing, and comparison of poetry translations with both AI-generated and human-created content.

## Strategic Decisions Made

### Core Technology Stack
- **FastAPI + async** (modern Python stack)
- **SQLite + SQLAlchemy** (local database)
- **Jinja2 + Bootstrap 5** (simple UI)
- **Background async tasks** (non-blocking translations)

### Integration Approach
- **Path B integration** - direct vpsweb.TranslationWorkflow API calls
- No subprocess overhead, cleaner architecture
- Comprehensive error handling

### Data Model
- **4-table schema**: poems, translations, ai_logs, human_notes
- **Translation iteration support** - multiple versions per poem
- **Filesystem provenance** - raw artifacts stored alongside database

### User Experience
- Simple job status with manual refresh
- Password-protected local interface
- Basic CRUD operations through web UI
- CLI access for content creation
- Bulk import and export capabilities

## Detailed Architecture

### 1. Technology Decisions

#### **Framework Choice: FastAPI + Async**
```python
# Modern async approach for non-blocking operations
# Background tasks for translation jobs
# Automatic API documentation
# Type hints throughout
```

#### **Database: SQLite with SQLAlchemy**
```python
# Single file database: repo.db
# WAL mode for concurrent reads
# Manual schema migrations initially
# Alembic integration later if needed
```

#### **Frontend: Server-Rendered HTML**
```python
# Jinja2 templates with Bootstrap 5
# Minimal JavaScript for enhanced UX
# Responsive design for local use
# No complex SPA framework initially
```

### 2. Project Structure

#### **As vpsweb Package Module**
```
src/vpsweb/
├── core/                    # Existing workflow
├── models/                  # Existing data models
├── services/                # Existing services
├── repository/              # NEW: Repository module
│   ├── __init__.py
│   ├── main.py             # FastAPI app
│   ├── database.py         # Database setup
│   ├── models.py           # SQLAlchemy models
│   ├── schemas.py          # Pydantic schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── poems.py        # Poem CRUD
│   │   ├── translations.py # Translation CRUD
│   │   └── jobs.py         # Job management
│   ├── web/
│   │   ├── __init__.py
│   │   ├── routes.py       # Web UI routes
│   │   └── templates/      # Jinja2 templates
│   ├── integration/
│   │   ├── __init__.py
│   │   └── vpsweb_adapter.py # vpsweb integration
│   └── utils/
│       ├── __init__.py
│       ├── file_storage.py
│       └── backup.py
└── __main__.py              # CLI entry point
```

#### **Repository Filesystem Layout**
```
repository_root/
├── repo.db                  # SQLite database
├── config.yaml              # Configuration file
├── data/
│   ├── poems/{poem_id}/
│   │   ├── original.md
│   │   └── meta.json
│   └── translations/{translation_id}/
│       ├── final.md
│       ├── notes.md
│       └── raw.json
├── backups/                 # Backup archives
└── logs/                    # Application logs
```

### 3. Data Model Schema

#### **Poems Table**
```sql
CREATE TABLE poems (
  id TEXT PRIMARY KEY,                    -- ULID
  poet_name TEXT NOT NULL,
  poem_title TEXT NOT NULL,
  source_language TEXT NOT NULL,          -- BCP 47: en, zh-Hans, zh-Hant
  original_text TEXT NOT NULL,
  form TEXT,                              -- Optional classification
  period TEXT,                            -- Optional classification
  created_at TEXT NOT NULL,               -- ISO timestamp
  updated_at TEXT NOT NULL                -- ISO timestamp
);
```

#### **Translations Table**
```sql
CREATE TABLE translations (
  id TEXT PRIMARY KEY,                    -- ULID
  poem_id TEXT NOT NULL REFERENCES poems(id) ON DELETE CASCADE,
  version INTEGER NOT NULL DEFAULT 1,     -- Translation iteration support
  translator_type TEXT NOT NULL CHECK (translator_type IN ('ai','human')),
  translator_info TEXT,                   -- "vpsweb (hybrid)" or "Jane Doe"
  target_language TEXT NOT NULL,
  translated_text TEXT NOT NULL,
  license TEXT,                           -- Default: CC-BY-4.0 for AI
  raw_path TEXT,                          -- Path to raw artifacts
  created_at TEXT NOT NULL
);
```

#### **AI Logs Table**
```sql
CREATE TABLE ai_logs (
  id TEXT PRIMARY KEY,
  translation_id TEXT NOT NULL REFERENCES translations(id) ON DELETE CASCADE,
  model_name TEXT,
  workflow_mode TEXT,
  token_usage_json TEXT,
  cost_info_json TEXT,
  runtime_seconds REAL,
  notes TEXT,
  created_at TEXT NOT NULL
);
```

#### **Human Notes Table**
```sql
CREATE TABLE human_notes (
  id TEXT PRIMARY KEY,
  translation_id TEXT NOT NULL REFERENCES translations(id) ON DELETE CASCADE,
  note_text TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

### 4. Configuration Management

#### **config.yaml Structure**
```yaml
# vpsweb Repository Configuration
repository:
  root_path: "./repository_root"
  database_url: "sqlite:///repository_root/repo.db"

# Security
security:
  password_hash: null  # Set via CLI: vpsweb repo set-password

# vpsweb Integration
vpsweb:
  models_config: "config/models.yaml"
  default_workflow_mode: "hybrid"
  timeout_seconds: 300

# Logging
logging:
  level: "INFO"
  file: "logs/repository.log"

# Backup
backup:
  auto_enabled: false
  retention_days: 30
```

### 5. Integration with vpsweb

#### **Path B Integration: Direct API Calls**
```python
# repository/integration/vpsweb_adapter.py
from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.models.config import load_config

class VPSWebAdapter:
    async def run_translation(self, poem_text, source_lang, target_lang, mode="hybrid"):
        config = load_config("config/models.yaml")
        workflow = TranslationWorkflow(config)

        result = await workflow.execute(
            text=poem_text,
            source_language=source_lang,
            target_language=target_lang,
            workflow_mode=mode
        )

        return self._process_result(result)
```

### 6. Web Interface Design

#### **Core Pages & Functionality**

**Dashboard (`/`)**
- Statistics: poems count, translations count (AI vs human)
- Recent activity: latest translations, latest poems
- Quick actions: "New AI Translation", "Add Human Translation"

**Poems Management**
- **List View** (`/poems`): Filterable table (poet, title, language)
- **Detail View** (`/poems/{poem_id}`): Original text + translations list
- **Compare View** (`/poems/{poem_id}/compare/{translation_id}`): Side-by-side comparison

**Translation Management**
- **New AI Translation** (`/translations/new/ai`): Form + background job submission
- **Add Human Translation** (`/translations/new/human`): Manual input form
- **Translation Detail** (`/translations/{translation_id}`): Full details + provenance

**Job Management**
- **Job Status** (`/jobs/{job_id}`): Simple status page with manual refresh
- **Job Cancellation**: Cancel running translations through UI

### 7. API Design

#### **RESTful Endpoints**
```python
# Poem APIs
GET    /api/v1/poems                    # List poems with filters
POST   /api/v1/poems                    # Create new poem
GET    /api/v1/poems/{poem_id}          # Get poem details
PUT    /api/v1/poems/{poem_id}          # Update poem
DELETE /api/v1/poems/{poem_id}          # Delete poem

# Translation APIs
GET    /api/v1/translations             # List translations
POST   /api/v1/translations             # Create translation
GET    /api/v1/translations/{id}        # Get translation details
PUT    /api/v1/translations/{id}        # Update translation
DELETE /api/v1/translations/{id}        # Delete translation

# Job APIs
POST   /api/v1/jobs/translate           # Start translation job
GET    /api/v1/jobs/{job_id}            # Get job status
DELETE /api/v1/jobs/{job_id}            # Cancel job

# Import/Export APIs
POST   /api/v1/import/vpsweb            # Bulk import vpsweb outputs
GET    /api/v1/export/poem/{poem_id}    # Export poem with translations
GET    /api/v1/export/translation/{id}  # Export single translation
```

### 8. CLI Integration

#### **Extended vpsweb CLI Commands**
```bash
# Repository management
vpsweb repo init                         # Initialize new repository
vpsweb repo serve                        # Start web server
vpsweb repo set-password                 # Set access password
vpsweb repo backup                       # Create backup

# Content management
vpsweb poem add --file "poem.md"         # Add poem via CLI
vpsweb translation add --poem-id {id}    # Add translation via CLI
vpsweb import --dir "outputs/"           # Bulk import vpsweb outputs
vpsweb export --poem-id {id} --format json
```

### 9. Security & Authentication

#### **Simple Password Protection**
```python
# Single password stored as hash in config.yaml
# HTTP Basic Auth for web interface
# API key optional for local API access
# No user roles or RBAC (single-user local system)
```

#### **Data Validation**
```python
# Strict BCP 47 language codes (en, zh-Hans, zh-Hant)
# Required fields validation (poet_name, poem_title)
# Text content sanitization
# Input length limits and format validation
```

### 10. Error Handling & Logging

#### **Comprehensive Error Management**
```python
# Structured logging with correlation IDs
# User-friendly error messages in UI
# Detailed error context in logs
# Translation job failure recovery
# Database transaction rollback on errors
```

#### **Log Levels & Structure**
```python
# INFO: Normal operations, job completion
# WARNING: Non-fatal issues, retry scenarios
# ERROR: Failed operations, exceptions
# DEBUG: Detailed execution tracing
```

### 11. Backup & Recovery

#### **Separate Backup Script**
```python
# scripts/backup_repository.py
# Zip repo.db + data/ directory
# Configurable retention policy
# Incremental backup option
# Restore functionality
```

#### **Backup Strategy**
- **Manual backups** via CLI command
- **Optional auto-backup** (configurable)
- **Full and incremental** backup options
- **Retention management** with age-based cleanup

### 12. Data Import/Export

#### **Bulk Import Capabilities**
```python
# Import existing vpsweb JSON outputs
# Batch poem creation from text files
# Translation import with metadata preservation
# Duplicate detection and handling
```

#### **Export Functionality**
```python
# Export single poem with all translations
# Export translation with full provenance
# JSON and Markdown format options
# Bulk export by filters (poet, language, etc.)
```

### 13. Development & Deployment

#### **Local Development Setup**
```bash
# Install dependencies
poetry install

# Set PYTHONPATH
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Initialize repository
vpsweb repo init

# Start development server
vpsweb repo serve --dev --reload
```

#### **Quality Assurance**
```python
# Black code formatting
# pytest for testing
# mypy for type checking
# Pre-commit hooks
# Integration tests for vpsweb workflow
```

## Implementation Timeline

### Week 1: Core Foundation
- **Days 1-2**: Project setup, database models, basic FastAPI structure
- **Days 3-4**: Poem CRUD operations, web UI templates
- **Days 5-7**: Human translation workflow, basic comparison view

### Week 2: Integration & Polish
- **Days 8-9**: vpsweb integration (Path B), AI translation workflow
- **Days 10-11**: Job management, error handling, CLI commands
- **Days 12-14**: Backup functionality, import/export, testing & polish

## Success Criteria

### Functional Requirements
- [x] Create and browse poems via web interface
- [x] Run AI translations with vpsweb integration
- [x] Add and manage human translations
- [x] Compare original vs translations side-by-side
- [x] Import existing vpsweb outputs
- [x] Backup and restore repository data

### Non-Functional Requirements
- [x] Responsive UI for local use
- [x] Secure password protection
- [x] Comprehensive error handling
- [x] Clean separation of concerns
- [x] Extensible architecture for future features

## Future Growth Path

### Potential Enhancements (Out of Scope for Initial Version)
- Full-text search with SQLite FTS5
- Real-time job updates with WebSockets
- Multi-user support with RBAC
- Advanced translation comparison tools
- Semantic search capabilities
- Public deployment features

### Migration Paths
- SQLite → PostgreSQL for multi-user scenarios
- FastAPI → Distributed architecture
- Local-only → Cloud deployment
- Single-user → Multi-tenant system

---

**This finalized strategy provides a clear roadmap for implementing the vpsweb repository and web interface as a cohesive part of the vpsweb package, with specific technical decisions and implementation details ready for PSD generation.**