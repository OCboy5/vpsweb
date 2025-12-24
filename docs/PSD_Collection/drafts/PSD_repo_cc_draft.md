# Project Specification Document (PSD)
## VPSWeb Central Repository & Local Web UI

**Document Status**: Draft v0.1 (Work in Progress)
**Created**: 2025-10-17
**Target Version**: v0.2.9 (Repository Integration)
**Author**: VPSWeb Development Team

---

## 🎯 Executive Summary

**Project**: VPSWeb Central Repository & Local Web UI
**Status**: Ready for Implementation
**Timeline**: 2-week development cycle
**Target Release**: v0.2.9

### Project Overview
This document specifies the implementation of a centralized repository system for VPSWeb poetry translations, replacing scattered file-based outputs with an organized, web-accessible database. The system provides comprehensive translation management with both AI-generated and human-created content, featuring side-by-side comparison capabilities and seamless integration with existing VPSWeb translation workflows.

### Key Business Benefits
- **Centralized Management**: Replace disorganized file outputs with structured, searchable repository
- **Enhanced Productivity**: Web interface enables efficient browsing and comparison of translation iterations
- **Workflow Integration**: Seamless connection with existing VPSWeb translation processes
- **Data Preservation**: Structured storage with backup capabilities for translation provenance
- **User Accessibility**: Local web interface accessible via browser with password protection

### Technical Innovation
- **Dual-Language Architecture**: BCP 47 codes for internal storage, natural language names for LLM interactions
- **Asynchronous Processing**: Non-blocking background job management for AI translations
- **Modern Stack**: FastAPI + SQLAlchemy + SQLite with async/await patterns throughout
- **Extensible Design**: Clean separation of concerns enabling future feature expansion

### Implementation Timeline
- **Week 1**: Core database, API, and basic web interface
- **Week 2**: vpsweb integration, background jobs, security, and testing
- **Total Development**: 14 days with parallel task execution
- **Go-to-Market**: Immediate local deployment with single-user access

### Success Metrics
- **Functional**: Complete CRUD operations, AI translation integration, comparison views
- **Performance**: <200ms API response time, <1s page load time
- **Quality**: >90% test coverage, zero security vulnerabilities
- **Usability**: <30 minute learning curve, >95% task completion rate

### Stakeholder Value
- **Users**: Centralized, searchable translation repository with comparison tools
- **Developers**: Clean architecture enabling rapid feature development
- **Organization**: Preserved translation assets with provenance tracking
- **Future Growth**: Extensible foundation for advanced features like multi-user access and cloud deployment

---

## 📋 Project Context

### Current State
- VPSWeb has established poetry translation workflow with AI and human capabilities
- Current outputs are stored as JSON and Markdown files in output directories
- No central repository for managing and browsing translations
- No web interface for viewing and comparing translation iterations

### Problem Statement
Users need a centralized system to store, browse, and compare poetry translations with both AI-generated and human-created content. The current file-based output system lacks organization and accessibility.

### Solution Overview
Implement a local web-based repository system with FastAPI, SQLite, and a clean web interface to provide centralized storage, browsing, and comparison capabilities for poetry translations.

---

## 🎯 Project Goals

### Primary Goals
1. **Centralized Storage**: Replace scattered output files with organized database
2. **Web Interface**: Provide local web UI for browsing and managing translations
3. **Translation Comparison**: Enable side-by-side comparison of different translation versions
4. **vpsweb Integration**: Seamless integration with existing translation workflow

### Success Criteria
- [ ] FastAPI web server serves local repository interface
- [ ] SQLite database stores poems, translations, and metadata
- [ ] Web UI allows poem creation and browsing
- [ ] AI translation workflow integrated through vpsweb.TranslationWorkflow API
- [ ] Human translation input supported
- [ ] Side-by-side translation comparison view
- [ ] Import/export functionality for existing translation outputs
- [ ] Password protection for local web interface

---

## 🔧 Technical Requirements

### Functional Requirements

#### Web Interface Requirements
- **Dashboard**: Statistics and recent activity overview
- **Poem Management**: CRUD operations for poems with metadata
- **Translation Management**: Support for both AI and human translations
- **Comparison View**: Side-by-side comparison of original and translations
- **Job Management**: Background task processing for AI translations

#### Database Requirements
- **4-Table Schema**: poems, translations, ai_logs, human_notes
- **Translation Iteration Support**: Multiple versions per poem
- **Filesystem Provenance**: Raw artifacts stored alongside database records
- **BCP 47 Language Codes**: Standard language representation for internal storage (en, zh-Hans, zh-Hant)
- **Natural Language Names**: Convert BCP 47 codes to natural language names for LLM prompts (English, Simplified Chinese, Traditional Chinese)

#### Integration Requirements
- **Path B Integration**: Direct vpsweb.TranslationWorkflow API calls
- **No Subprocess Overhead**: Clean architecture with proper error handling
- **Background Tasks**: Non-blocking translation job processing
- **Import/Export**: Bulk operations for existing translation files

### Non-Functional Requirements

#### Performance
- **Response Time**: < 500ms for web UI operations
- **Database Operations**: < 100ms for standard queries
- **Background Jobs**: Non-blocking with status tracking

#### Reliability
- **Data Integrity**: SQLite WAL mode for concurrent access
- **Error Recovery**: Comprehensive error handling and job recovery
- **Backup Capabilities**: Manual and optional automated backup system

#### Usability
- **Responsive Design**: Bootstrap 5 for mobile-friendly interface
- **Intuitive Navigation**: Clear information architecture
- **Search and Filter**: Find poems by poet, title, language

---

## 🏗️ System Architecture

### Component Overview

```
FastAPI Web Server
├── Repository Module
│   ├── Database Layer (SQLAlchemy + SQLite)
│   ├── API Layer (RESTful endpoints)
│   ├── Web UI (Jinja2 + Bootstrap 5)
│   └── Background Task Manager
├── vpsweb Integration Module
│   ├── TranslationWorkflow Adapter
│   ├── Job Queue Management
│   └── Error Handler
├── File Storage System
│   ├── Poem Raw Files
│   ├── Translation Artifacts
│   └── Backup Archives
└── Configuration Management
    ├── YAML Configuration
    ├── Security (Password Protection)
    └── Logging System
```

### Detailed Architecture

#### 1. Repository Module Structure
```python
src/vpsweb/repository/
├── __init__.py
├── main.py              # FastAPI app configuration
├── database.py          # Database setup and connection
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── api/
│   ├── poems.py         # Poem CRUD operations
│   ├── translations.py  # Translation management
│   └── jobs.py         # Background job tracking
├── web/
│   ├── routes.py       # Web UI routes
│   └── templates/      # Jinja2 templates
├── integration/
│   └── vpsweb_adapter.py # vpsweb workflow integration
└── utils/
    ├── file_storage.py  # File system operations
    └── backup.py       # Backup utilities
```

#### 2. Database Schema Design (Optimized)
```sql
-- Poems Table with performance optimizations and constraints
CREATE TABLE poems (
  id TEXT PRIMARY KEY,                    -- ULID for distributed ID generation
  poet_name TEXT NOT NULL,
  poem_title TEXT NOT NULL,
  source_language TEXT NOT NULL CHECK (source_language IN ('en', 'zh-Hans', 'zh-Hant')),
  original_text TEXT NOT NULL,
  form TEXT CHECK (form IN ('sonnet', 'haiku', 'free verse', 'limerick', 'ode', 'ballad')),
  period TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes for poems
CREATE INDEX idx_poems_poet_name ON poems(poet_name);
CREATE INDEX idx_poems_source_language ON poems(source_language);
CREATE INDEX idx_poems_created_at ON poems(created_at);
CREATE INDEX idx_poems_poet_title ON poems(poem_title);
CREATE INDEX idx_poems_full_text ON poems USING FTS5(poet_name, poem_title, original_text);

-- Translations Table with constraints
CREATE TABLE translations (
  id TEXT PRIMARY KEY,                    -- ULID
  poem_id TEXT NOT NULL REFERENCES poems(id) ON DELETE CASCADE,
  version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
  translator_type TEXT NOT NULL CHECK (translator_type IN ('ai','human')),
  translator_info TEXT,
  target_language TEXT NOT NULL CHECK (target_language IN ('en', 'zh-Hans', 'zh-Hant')),
  translated_text TEXT NOT NULL,
  license TEXT DEFAULT 'CC-BY-4.0',
  raw_path TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

  -- Unique constraint to prevent duplicate translations
  UNIQUE(poem_id, target_language, version)
);

-- Performance indexes for translations
CREATE INDEX idx_translations_poem_id ON translations(poem_id);
CREATE INDEX idx_translations_target_language ON translations(target_language);
CREATE INDEX idx_translations_created_at ON translations(created_at);
CREATE INDEX idx_translations_translator_type ON translations(translator_type);
CREATE INDEX idx_translations_full_text ON translations USING FTS5(translated_text, translator_info);

-- AI Logs Table with constraints
CREATE TABLE ai_logs (
  id TEXT PRIMARY KEY,                    -- ULID
  translation_id TEXT NOT NULL REFERENCES translations(id) ON DELETE CASCADE,
  model_name TEXT NOT NULL CHECK (model_name IS NOT NULL),
  workflow_mode TEXT CHECK (workflow_mode IN ('reasoning', 'non_reasoning', 'hybrid')),
  token_usage_json TEXT CHECK (json_valid(token_usage_json)),
  cost_info_json TEXT CHECK (json_valid(cost_info_json)),
  runtime_seconds REAL CHECK (runtime_seconds >= 0),
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes for AI logs
CREATE INDEX idx_ai_logs_translation_id ON ai_logs(translation_id);
CREATE INDEX idx_ai_logs_model_name ON ai_logs(model_name);
CREATE INDEX idx_ai_logs_created_at ON ai_logs(created_at);

-- Human Notes Table with constraints
CREATE TABLE human_notes (
  id TEXT PRIMARY KEY,                    -- ULID
  translation_id TEXT NOT NULL REFERENCES translations(id) ON DELETE CASCADE,
  note_text TEXT NOT NULL CHECK (length(note_text) > 0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes for human notes
CREATE INDEX idx_human_notes_translation_id ON human_notes(translation_id);
CREATE INDEX idx_human_notes_created_at ON human_notes(created_at);
```
```

#### 3. API Layer Design
```python
# RESTful API Structure
/api/v1/poems/                    # Poem CRUD operations
/api/v1/translations/             # Translation management
/api/v1/jobs/                     # Background job tracking
/api/v1/import/                   # Bulk import operations
/api/v1/export/                   # Data export functionality
```

#### 4. Web UI Component Architecture
```python
# Page Structure
/                               # Dashboard with statistics
/poems                          # Poem listing and search
/poems/{id}                     # Poem detail view
/poems/{id}/compare/{tid}        # Side-by-side comparison
/translations/new/ai             # AI translation form
/translations/new/human           # Human translation form
/jobs/{job_id}                  # Job status tracking
/settings                       # Configuration management
```

### Data Flow Architecture

```
User Request → FastAPI Router → Dependency Injection → Business Logic
     ↓
Language Code Processing (BCP 47 ↔ Natural Language)
     ↓
Database Operations (SQLAlchemy ORM) → File Storage (Optional)
     ↓
Background Task Queue (if needed) → Response Generation
     ↓
Web UI Template Rendering → JSON API Response
```

### Language Handling Strategy

The system uses a dual-language approach to optimize both data storage and LLM interactions:

#### Internal Storage (Database & APIs)
- **Format**: BCP 47 language codes (`en`, `zh-Hans`, `zh-Hant`)
- **Benefits**: Standardized, machine-readable, internationally recognized
- **Usage**: Database schema, API parameters, configuration

#### LLM Interactions (Translation Workflows)
- **Format**: Natural language names (`English`, `Simplified Chinese`, `Traditional Chinese`)
- **Benefits**: Clear, unambiguous for AI models, no confusion
- **Usage**: vpsweb workflow prompts, AI model instructions

#### Conversion Process
```python
# Example conversion flow
source_code = "zh-Hans"  # Database storage
target_code = "en"      # Database storage

# Convert for LLM
language_pair = LanguageMapper.get_language_pair_for_llm(source_code, target_code)
# Result: {"source_language": "Simplified Chinese", "target_language": "English"}

# Use in vpsweb workflow
result = await workflow.execute(
    source_language=language_pair["source_language"],  # Natural language
    target_language=language_pair["target_language"]   # Natural language
)
```

This approach ensures data consistency while providing clear, unambiguous language specifications for AI translation processes.

---

## 📋 Implementation Plan

### Phase 1: Core Foundation (Days 1-3)

#### Task 1.1: Project Structure Setup
**File**: `src/vpsweb/repository/__init__.py`
**Priority**: High
**Dependencies**: None

```python
# Repository module initialization
__version__ = "0.1.0"
```

#### Task 1.2: Language Mapping Utility
**File**: `src/vpsweb/repository/utils/language_mapper.py`
**Priority**: High
**Dependencies**: None

```python
from typing import Dict, Optional
from enum import Enum

class LanguageCode(str, Enum):
    """BCP 47 language codes supported by the system"""
    ENGLISH = "en"
    SIMPLIFIED_CHINESE = "zh-Hans"
    TRADITIONAL_CHINESE = "zh-Hant"

class LanguageMapper:
    """Maps between BCP 47 codes and natural language names for LLM interactions"""

    BCP47_TO_NATURAL = {
        LanguageCode.ENGLISH: "English",
        LanguageCode.SIMPLIFIED_CHINESE: "Simplified Chinese",
        LanguageCode.TRADITIONAL_CHINESE: "Traditional Chinese"
    }

    NATURAL_TO_BCP47 = {
        "English": LanguageCode.ENGLISH,
        "Simplified Chinese": LanguageCode.SIMPLIFIED_CHINESE,
        "Traditional Chinese": LanguageCode.TRADITIONAL_CHINESE,
        # Alternative names for flexibility
        "中文": LanguageCode.SIMPLIFIED_CHINESE,
        "简体中文": LanguageCode.SIMPLIFIED_CHINESE,
        "繁體中文": LanguageCode.TRADITIONAL_CHINESE,
        "Chinese": LanguageCode.SIMPLIFIED_CHINESE  # Default to simplified
    }

    @classmethod
    def to_natural(cls, bcp47_code: str) -> str:
        """Convert BCP 47 code to natural language name"""
        return cls.BCP47_TO_NATURAL.get(LanguageCode(bcp47_code), bcp47_code)

    @classmethod
    def to_bcp47(cls, natural_name: str) -> str:
        """Convert natural language name to BCP 47 code"""
        return cls.NATURAL_TO_BCP47.get(natural_name, natural_name)

    @classmethod
    def get_language_pair_for_llm(cls, source_code: str, target_code: str) -> Dict[str, str]:
        """Get language names formatted for LLM prompts"""
        return {
            "source_language": cls.to_natural(source_code),
            "target_language": cls.to_natural(target_code)
        }

    @classmethod
    def validate_language_code(cls, code: str) -> bool:
        """Validate if language code is supported"""
        try:
            LanguageCode(code)
            return True
        except ValueError:
            return False

    @classmethod
    def get_supported_languages(cls) -> Dict[str, str]:
        """Get all supported languages with both codes and names"""
        return {
            code.value: name
            for code, name in cls.BCP47_TO_NATURAL.items()
        }
```

#### Task 1.3: Database Models Implementation
**File**: `src/vpsweb/repository/models.py`
**Priority**: High
**Dependencies**: SQLAlchemy, Pydantic

```python
from sqlalchemy import Column, String, Integer, Text, ForeignKey, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from ulid import ULID
from datetime import datetime

Base = declarative_base()

class Poem(Base):
    __tablename__ = "poems"

    id = Column(String, primary_key=True, default=lambda: str(ULID()))
    poet_name = Column(String, nullable=False)
    poem_title = Column(String, nullable=False)
    source_language = Column(String, nullable=False)  # BCP 47
    original_text = Column(Text, nullable=False)
    form = Column(String)  # Optional classification
    period = Column(String)  # Optional classification
    created_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat())

    translations = relationship("Translation", back_populates="poem", cascade="all, delete-orphan")

class Translation(Base):
    __tablename__ = "translations"

    id = Column(String, primary_key=True, default=lambda: str(ULID()))
    poem_id = Column(String, ForeignKey("poems.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    translator_type = Column(String, nullable=False, CheckConstraint("translator_type IN ('ai','human')"))
    translator_info = Column(String)
    target_language = Column(String, nullable=False)  # BCP 47
    translated_text = Column(Text, nullable=False)
    license = Column(String)  # Default: CC-BY-4.0 for AI
    raw_path = Column(String)  # Path to raw artifacts
    created_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat())

    poem = relationship("Poem", back_populates="translations")
    ai_log = relationship("AILog", uselist=False, back_populates="translation")
    human_notes = relationship("HumanNote", back_populates="translation")

class AILog(Base):
    __tablename__ = "ai_logs"

    id = Column(String, primary_key=True, default=lambda: str(ULID()))
    translation_id = Column(String, ForeignKey("translations.id"), nullable=False)
    model_name = Column(String)
    workflow_mode = Column(String)
    token_usage_json = Column(String)  # JSON string
    cost_info_json = Column(String)  # JSON string
    runtime_seconds = Column(Integer)
    notes = Column(String)
    created_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat())

    translation = relationship("Translation", back_populates="ai_log")

class HumanNote(Base):
    __tablename__ = "human_notes"

    id = Column(String, primary_key=True, default=lambda: str(ULID()))
    translation_id = Column(String, ForeignKey("translations.id"), nullable=False)
    note_text = Column(Text, nullable=False)
    created_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat())

    translation = relationship("Translation", back_populates="human_notes")
```

#### Task 1.3: Pydantic Schemas
**File**: `src/vpsweb/repository/schemas.py`
**Priority**: High
**Dependencies**: Pydantic

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class PoemCreate(BaseModel):
    poet_name: str = Field(..., min_length=1, max_length=200)
    poem_title: str = Field(..., min_length=1, max_length=200)
    source_language: str = Field(..., regex=r'^[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-[A-Z]{2})?$')  # BCP 47
    original_text: str = Field(..., min_length=1)
    form: Optional[str] = Field(None, max_length=50)
    period: Optional[str] = Field(None, max_length=50)

class PoemResponse(BaseModel):
    id: str
    poet_name: str
    poem_title: str
    source_language: str
    original_text: str
    form: Optional[str]
    period: Optional[str]
    created_at: datetime
    updated_at: datetime
    translation_count: int = 0

    class Config:
        orm_mode = True

class TranslationCreate(BaseModel):
    poem_id: str
    translator_type: str = Field(..., regex=r'^(ai|human)$')
    translator_info: Optional[str] = Field(None, max_length=100)
    target_language: str = Field(..., regex=r'^[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-[A-Z]{2})?$')
    translated_text: str = Field(..., min_length=1)
    license: Optional[str] = Field(None, max_length=50)

class TranslationResponse(BaseModel):
    id: str
    poem_id: str
    version: int
    translator_type: str
    translator_info: Optional[str]
    target_language: str
    translated_text: str
    license: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True

# Additional schemas for updates, filtering, etc.
```

### Phase 2: Database and API Layer (Days 4-6)

#### Task 2.1: Database Connection Setup
**File**: `src/vpsweb/repository/database.py`
**Priority**: High
**Dependencies**: SQLAlchemy, aiosqlite

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from .models import Base
import os

class DatabaseConfig:
    def __init__(self, database_url: str = "sqlite+aiosqlite:///repository_root/repo.db"):
        self.database_url = database_url
        self.engine = create_async_engine(
            database_url,
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 20
            },
            echo=os.getenv("DEBUG", "false").lower() == "true"
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

async def create_tables():
    """Create all database tables"""
    async with DatabaseConfig().engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncSession:
    """Dependency to get database session"""
    return DatabaseConfig().session_factory()
```

#### Task 2.3: FastAPI Application Setup
**File**: `src/vpsweb/repository/main.py`
**Priority**: High
**Dependencies**: FastAPI, DatabaseConfig

```python
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
import os

from .database import DatabaseConfig, get_session
from .api import poems, translations, jobs
from .web import routes as web_routes
from .integration.vpsweb_adapter import VPSWebAdapter

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create database tables
    await DatabaseConfig().create_tables()
    yield
    # Shutdown: cleanup if needed

app = FastAPI(
    title="VPSWeb Repository",
    description="Central repository for poetry translations",
    version="0.1.0",
    lifespan=lifespan
)

# Include API routers
app.include_router(poems.router, prefix="/api/v1/poems", tags=["poems"])
app.include_router(translations.router, prefix="/api/v1/translations", tags=["translations"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])

# Include web UI routes
app.include_router(web_routes.router, tags=["web"])

# Static files and templates
templates = Jinja2Templates(directory="src/vpsweb/repository/web/templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard page with statistics and recent activity"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
```

#### Task 2.4: Poem CRUD API Implementation
**File**: `src/vpsweb/repository/api/poems.py`
**Priority**: High
**Dependencies**: FastAPI, SQLAlchemy, Pydantic

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional

from ..database import get_session
from ..models import Poem, Translation
from ..schemas import PoemCreate, PoemResponse, PoemUpdate

router = APIRouter()

@router.post("/", response_model=PoemResponse)
async def create_poem(
    poem: PoemCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new poem"""
    db_poem = Poem(**poem.dict())
    session.add(db_poem)
    await session.commit()
    await session.refresh(db_poem)

    # Add translation count
    translation_count_stmt = select(func.count(Translation.id)).where(
        Translation.poem_id == db_poem.id
    )
    translation_count = await session.scalar(translation_count_stmt)

    return PoemResponse(
        **db_poem.__dict__,
        translation_count=translation_count or 0
    )

@router.get("/", response_model=List[PoemResponse])
async def list_poems(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    poet: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session)
):
    """List poems with filtering and pagination"""
    query = select(Poem)

    # Apply filters
    if poet:
        query = query.where(Poem.poet_name.ilike(f"%{poet}%"))
    if language:
        query = query.where(Poem.source_language == language)
    if search:
        query = query.where(
            or_(
                Poem.poet_name.ilike(f"%{search}%"),
                Poem.poem_title.ilike(f"%{search}%"),
                Poem.original_text.ilike(f"%{search}%")
            )
        )

    # Count total results
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await session.scalar(count_query)

    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    poems = result.scalars().all()

    # Add translation counts
    poems_with_counts = []
    for poem in poems:
        translation_count_stmt = select(func.count(Translation.id)).where(
            Translation.poem_id == poem.id
        )
        translation_count = await session.scalar(translation_count_stmt)
        poems_with_counts.append(
            PoemResponse(
                **poem.__dict__,
                translation_count=translation_count or 0
            )
        )

    return poems_with_counts

@router.get("/{poem_id}", response_model=PoemResponse)
async def get_poem(
    poem_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get a specific poem"""
    stmt = select(Poem).where(Poem.id == poem_id)
    result = await session.execute(stmt)
    poem = result.scalar_one_or_none()

    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")

    # Add translation count
    translation_count_stmt = select(func.count(Translation.id)).where(
        Translation.poem_id == poem.id
    )
    translation_count = await session.scalar(translation_count_stmt)

    return PoemResponse(
        **poem.__dict__,
        translation_count=translation_count or 0
    )

@router.put("/{poem_id}", response_model=PoemResponse)
async def update_poem(
    poem_id: str,
    poem_update: PoemUpdate,
    session: AsyncSession = Depends(get_session)
):
    """Update a poem"""
    stmt = select(Poem).where(Poem.id == poem_id)
    result = await session.execute(stmt)
    poem = result.scalar_one_or_none()

    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")

    # Update fields
    update_data = poem_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(poem, field, value)

    poem.updated_at = datetime.utcnow().isoformat()
    await session.commit()
    await session.refresh(poem)

    # Add translation count
    translation_count_stmt = select(func.count(Translation.id)).where(
        Translation.poem_id == poem.id
    )
    translation_count = await session.scalar(translation_count_stmt)

    return PoemResponse(
        **poem.__dict__,
        translation_count=translation_count or 0
    )

@router.delete("/{poem_id}")
async def delete_poem(
    poem_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Delete a poem"""
    stmt = select(Poem).where(Poem.id == poem_id)
    result = await session.execute(stmt)
    poem = result.scalar_one_or_none()

    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")

    await session.delete(poem)
    await session.commit()

    return {"message": "Poem deleted successfully"}
```

### Phase 3: vpsweb Integration (Days 7-9)

#### Task 3.1: vpsWeb Workflow Adapter
**File**: `src/vpsweb/repository/integration/vpsweb_adapter.py`
**Priority**: High
**Dependencies**: vpsweb.core.workflow, vpsweb.models.config

```python
from typing import Dict, Optional, Any
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path

from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.models.config import load_config
from vpsweb.models.translation import TranslationResult
from ..models import Translation, AILog, Poem
from ..database import get_session
from ..utils.language_mapper import LanguageMapper

class VPSWebAdapter:
    """Adapter for integrating vpsweb translation workflow"""

    def __init__(self, models_config_path: str = "config/models.yaml"):
        self.models_config_path = models_config_path
        self.config = load_config(models_config_path)
        self.workflow = TranslationWorkflow(self.config)

    async def translate_poem(
        self,
        poem: Poem,
        target_language: str,
        workflow_mode: str = "hybrid"
    ) -> Dict[str, Any]:
        """
        Translate a poem using vpsweb workflow

        Returns:
            Dict containing translation result and metadata
        """
        try:
            # Convert BCP 47 codes to natural language names for LLM
            language_pair = LanguageMapper.get_language_pair_for_llm(
                poem.source_language,
                target_language
            )

            # Execute translation workflow with natural language names
            result = await self.workflow.execute(
                text=poem.original_text,
                source_language=language_pair["source_language"],  # Natural language
                target_language=language_pair["target_language"],  # Natural language
                workflow_mode=workflow_mode
            )

            # Process result for database storage
            translation_data = {
                "id": str(ULID()),
                "poem_id": poem.id,
                "version": await self._get_next_translation_version(poem.id),
                "translator_type": "ai",
                "translator_info": f"vpsweb ({workflow_mode})",
                "target_language": target_language,
                "translated_text": result.translated_text,
                "license": "CC-BY-4.0",  # Default for AI translations
                "created_at": datetime.utcnow().isoformat()
            }

            # Prepare AI log data
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

            # Save raw artifacts to filesystem
            raw_path = await self._save_raw_artifacts(
                poem.id,
                translation_data["id"],
                result
            )
            translation_data["raw_path"] = raw_path

            return {
                "translation": translation_data,
                "ai_log": ai_log_data,
                "success": True
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    async def _get_next_translation_version(self, poem_id: str) -> int:
        """Get the next version number for a poem's translations"""
        async with get_session() as session:
            stmt = select(func.max(Translation.version)).where(
                Translation.poem_id == poem_id
            )
            max_version = await session.scalar(stmt)
            return (max_version or 0) + 1

    async def _save_raw_artifacts(
        self,
        poem_id: str,
        translation_id: str,
        result: TranslationResult
    ) -> str:
        """Save raw translation artifacts to filesystem"""
        # Create directory structure
        repo_root = Path("repository_root")
        translation_dir = repo_root / "data" / "translations" / translation_id
        translation_dir.mkdir(parents=True, exist_ok=True)

        # Save raw artifacts as JSON
        artifacts = {
            "translation_id": translation_id,
            "poem_id": poem_id,
            "result_data": {
                "translated_text": result.translated_text,
                "confidence_score": getattr(result, 'confidence_score', None),
                "reasoning_steps": getattr(result, 'reasoning_steps', []),
                "alternatives": getattr(result, 'alternatives', []),
                "metadata": getattr(result, 'metadata', {})
            },
            "workflow_info": {
                "model_name": getattr(result, 'model_name', None),
                "workflow_mode": getattr(result, 'workflow_mode', None),
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        raw_file = translation_dir / "raw.json"
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(artifacts, f, indent=2, ensure_ascii=False)

        return str(raw_file)
```

#### Task 3.2: Persistent Background Job Management
**File**: `src/vpsweb/repository/job_manager.py`
**Priority**: High
**Dependencies**: FastAPI BackgroundTasks, asyncio, SQLite

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import json
import uuid
import sqlite3
from pathlib import Path
from contextlib import asynccontextmanager

from ..models import Translation, AILog, Poem
from ..database import get_session
from ..integration.vpsweb_adapter import VPSWebAdapter
from ..exceptions import JobException

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    RETRYING = "retrying"

class JobPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Job:
    id: str
    job_type: str
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    progress: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: int = 5  # seconds
    metadata: Dict[str, Any] = field(default_factory=dict)

class JobStore(ABC):
    """Abstract interface for job persistence"""

    @abstractmethod
    async def create_job(self, job: Job) -> Job:
        """Create a new job"""
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID"""
        pass

    @abstractmethod
    async def update_job(self, job: Job) -> Job:
        """Update an existing job"""
        pass

    @abstractmethod
    async def list_jobs(self, status: Optional[JobStatus] = None, limit: int = 100) -> List[Job]:
        """List jobs with optional status filter"""
        pass

    @abstractmethod
    async def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        pass

    @abstractmethod
    async def cleanup_old_jobs(self, older_than: datetime) -> int:
        """Clean up old completed/failed jobs"""
        pass

class SQLiteJobStore(JobStore):
    """SQLite-based persistent job storage"""

    def __init__(self, db_path: str = "repository_root/jobs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize job database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    progress INTEGER DEFAULT 0,
                    result TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    timeout_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    retry_delay INTEGER DEFAULT 5,
                    metadata TEXT
                )
            """)

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs(priority)")

    async def create_job(self, job: Job) -> Job:
        """Create a new job"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO jobs (
                    id, job_type, status, priority, progress, result, error,
                    created_at, started_at, completed_at, timeout_at,
                    retry_count, max_retries, retry_delay, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id, job.job_type, job.status.value, job.priority.value,
                job.progress, json.dumps(job.result) if job.result else None,
                job.error, job.created_at.isoformat(), job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None,
                job.timeout_at.isoformat() if job.timeout_at else None,
                job.retry_count, job.max_retries, job.retry_delay,
                json.dumps(job.metadata)
            ))
        return job

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row:
                return self._row_to_job(row)
        return None

    async def update_job(self, job: Job) -> Job:
        """Update an existing job"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE jobs SET
                    status = ?, progress = ?, result = ?, error = ?,
                    started_at = ?, completed_at = ?, timeout_at = ?,
                    retry_count = ?, metadata = ?
                WHERE id = ?
            """, (
                job.status.value, job.progress,
                json.dumps(job.result) if job.result else None,
                job.error, job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None,
                job.timeout_at.isoformat() if job.timeout_at else None,
                job.retry_count, json.dumps(job.metadata),
                job.id
            ))
        return job

    async def list_jobs(self, status: Optional[JobStatus] = None, limit: int = 100) -> List[Job]:
        """List jobs with optional status filter"""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM jobs"
            params = []

            if status:
                query += " WHERE status = ?"
                params.append(status.value)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_job(row) for row in rows]

    async def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            return cursor.rowcount > 0

    async def cleanup_old_jobs(self, older_than: datetime) -> int:
        """Clean up old completed/failed jobs"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM jobs
                WHERE created_at < ?
                AND status IN ('completed', 'failed', 'cancelled')
            """, (older_than.isoformat(),))
            return cursor.rowcount

    def _row_to_job(self, row) -> Job:
        """Convert database row to Job object"""
        return Job(
            id=row[0],
            job_type=row[1],
            status=JobStatus(row[2]),
            priority=JobPriority(row[3]),
            progress=row[4],
            result=json.loads(row[5]) if row[5] else None,
            error=row[6],
            created_at=datetime.fromisoformat(row[7]),
            started_at=datetime.fromisoformat(row[8]) if row[8] else None,
            completed_at=datetime.fromisoformat(row[9]) if row[9] else None,
            timeout_at=datetime.fromisoformat(row[10]) if row[10] else None,
            retry_count=row[11],
            max_retries=row[12],
            retry_delay=row[13],
            metadata=json.loads(row[14]) if row[14] else {}
        )

class JobQueue:
    """Job queue with priority and retry logic"""

    def __init__(self, job_store: JobStore, max_concurrent_jobs: int = 3):
        self.job_store = job_store
        self.max_concurrent_jobs = max_concurrent_jobs
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self._shutdown = False

    async def submit_job(self, job: Job) -> str:
        """Submit a new job to the queue"""
        job = await self.job_store.create_job(job)
        await self._process_queue()
        return job.id

    async def get_job_status(self, job_id: str) -> Optional[Job]:
        """Get current job status"""
        return await self.job_store.get_job(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        job = await self.job_store.get_job(job_id)
        if not job:
            return False

        if job.status == JobStatus.RUNNING:
            # Cancel running task
            if job_id in self.running_jobs:
                self.running_jobs[job_id].cancel()
                del self.running_jobs[job_id]

        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        await self.job_store.update_job(job)
        return True

    async def _process_queue(self):
        """Process pending jobs"""
        if len(self.running_jobs) >= self.max_concurrent_jobs:
            return

        # Get next pending jobs ordered by priority
        pending_jobs = await self.job_store.list_jobs(JobStatus.PENDING)

        if not pending_jobs:
            return

        # Sort by priority (CRITICAL > HIGH > NORMAL > LOW)
        priority_order = {
            JobPriority.CRITICAL: 0,
            JobPriority.HIGH: 1,
            JobPriority.NORMAL: 2,
            JobPriority.LOW: 3
        }

        pending_jobs.sort(key=lambda job: priority_order[job.priority])

        for job in pending_jobs:
            if len(self.running_jobs) >= self.max_concurrent_jobs:
                break

            if job.timeout_at and datetime.utcnow() > job.timeout_at:
                job.status = JobStatus.TIMEOUT
                await self.job_store.update_job(job)
                continue

            # Start job execution
            task = asyncio.create_task(self._execute_job(job))
            self.running_jobs[job.id] = task

    async def _execute_job(self, job: Job):
        """Execute a single job"""
        try:
            # Update job status to running
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            await self.job_store.update_job(job)

            # Execute job based on type
            if job.job_type == "translation":
                result = await self._execute_translation_job(job)
            else:
                raise JobException(f"Unknown job type: {job.job_type}")

            # Update job with successful result
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.result = result
            job.completed_at = datetime.utcnow()

        except asyncio.CancelledError:
            job.status = JobStatus.CANCELLED
            job.error = "Job was cancelled"
            job.completed_at = datetime.utcnow()

        except Exception as e:
            job.error = str(e)

            # Handle retry logic
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = JobStatus.RETRYING
                job.progress = 0

                # Schedule retry
                await asyncio.sleep(job.retry_delay)
                await self.job_store.update_job(job)

                # Re-submit job for retry
                await self.submit_job(job)
                return
            else:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.utcnow()

        finally:
            # Remove from running jobs
            if job.id in self.running_jobs:
                del self.running_jobs[job.id]

            # Update job in store
            await self.job_store.update_job(job)

            # Process next jobs in queue
            await self._process_queue()

    async def _execute_translation_job(self, job: Job) -> Dict[str, Any]:
        """Execute a translation job"""
        poem_id = job.metadata.get("poem_id")
        target_language = job.metadata.get("target_language")
        workflow_mode = job.metadata.get("workflow_mode", "hybrid")

        if not poem_id or not target_language:
            raise JobException("Missing required job metadata")

        # Get poem from database
        async with get_session() as session:
            poem = await session.get(Poem, poem_id)
            if not poem:
                raise JobException(f"Poem not found: {poem_id}")

        # Update job progress
        job.progress = 10
        await self.job_store.update_job(job)

        # Execute translation
        adapter = VPSWebAdapter()

        job.progress = 30
        await self.job_store.update_job(job)

        result = await adapter.translate_poem(poem, target_language, workflow_mode)

        job.progress = 80
        await self.job_store.update_job(job)

        if not result["success"]:
            raise JobException(f"Translation failed: {result.get('error', 'Unknown error')}")

        # Save translation and AI log to database
        async with get_session() as session:
            # Create translation
            translation = Translation(**result["translation"])
            session.add(translation)
            await session.flush()

            # Create AI log if available
            if "ai_log" in result:
                ai_log = AILog(**result["ai_log"])
                session.add(ai_log)

            await session.commit()

        job.progress = 100
        return result

# Global job queue instance
_job_store: Optional[JobStore] = None
_job_queue: Optional[JobQueue] = None

def get_job_queue() -> JobQueue:
    """Get global job queue instance"""
    global _job_queue
    if _job_queue is None:
        _job_store = SQLiteJobStore()
        _job_queue = JobQueue(_job_store)
    return _job_queue
```

#### Task 3.3: Job Management API
**File**: `src/vpsweb/repository/api/jobs.py`
**Priority**: High
**Dependencies**: FastAPI BackgroundTasks, asyncio

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..database import get_session
from ..models import Poem
from ..job_manager import JobQueue, JobStatus, Job, JobPriority, get_job_queue
from ..schemas import JobCreate, JobResponse, JobUpdate

router = APIRouter()

@router.post("/translate", response_model=JobResponse)
async def start_translation_job(
    poem_id: str,
    target_language: str,
    workflow_mode: str = "hybrid",
    priority: JobPriority = JobPriority.NORMAL,
    timeout_seconds: int = 300,
    session: AsyncSession = Depends(get_session)
):
    """Start a background translation job"""

    # Verify poem exists
    poem = await session.get(Poem, poem_id)
    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")

    # Create job
    job = Job(
        id=str(uuid.uuid4()),
        job_type="translation",
        priority=priority,
        timeout_at=datetime.utcnow() + timedelta(seconds=timeout_seconds),
        metadata={
            "poem_id": poem_id,
            "target_language": target_language,
            "workflow_mode": workflow_mode
        }
    )

    job_queue = get_job_queue()
    job_id = await job_queue.submit_job(job)

    return JobResponse(
        id=job_id,
        job_type=job.job_type,
        status=JobStatus.PENDING,
        priority=job.priority,
        progress=0,
        created_at=job.created_at
    )

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get job status"""
    job_queue = get_job_queue()
    job = await job_queue.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        priority=job.priority,
        progress=job.progress,
        result=job.result,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        retry_count=job.retry_count
    )

@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[JobStatus] = None,
    limit: int = 50,
    offset: int = 0
):
    """List jobs with filtering and pagination"""
    job_queue = get_job_queue()
    jobs = await job_queue.job_store.list_jobs(status, limit + offset)

    return [
        JobResponse(
            id=job.id,
            job_type=job.job_type,
            status=job.status,
            priority=job.priority,
            progress=job.progress,
            result=job.result,
            error=job.error,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            retry_count=job.retry_count
        )
        for job in jobs[offset:offset + limit]
    ]

@router.delete("/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running job"""
    job_queue = get_job_queue()
    success = await job_queue.cancel_job(job_id)

    if not success:
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")

    return {"message": "Job cancelled successfully"}

@router.post("/cleanup")
async def cleanup_old_jobs(older_than_hours: int = 24):
    """Clean up old jobs"""
    job_queue = get_job_queue()
    cutoff_time = datetime.utcnow() - timedelta(hours=older_than)
    cleaned_count = await job_queue.job_store.cleanup_old_jobs(cutoff_time)

    return {"message": f"Cleaned up {cleaned_count} old jobs"}
```

### Pydantic Schemas for Jobs
**File**: `src/vpsweb/repository/schemas.py` (add to existing file)
```python
class JobCreate(BaseModel):
    job_type: str
    priority: JobPriority = JobPriority.NORMAL
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = {}

class JobResponse(BaseModel):
    id: str
    job_type: str
    status: JobStatus
    priority: JobPriority
    progress: int
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    retry_count: int

class JobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    progress: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
```

## 🔧 Complete API Specifications

### Translation CRUD Operations
**File**: `src/vpsweb/repository/api/translations.py`
**Priority**: High
**Dependencies**: FastAPI, SQLAlchemy, Pydantic

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from typing import List, Optional

from ..database import get_session
from ..models import Translation, Poem, AILog, HumanNote
from ..schemas import TranslationCreate, TranslationResponse, TranslationUpdate
from ..exceptions import ValidationError, DatabaseException

router = APIRouter()

@router.post("/", response_model=TranslationResponse)
async def create_translation(
    translation: TranslationCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new translation"""

    # Validate poem exists
    poem = await session.get(Poem, translation.poem_id)
    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")

    # Check for duplicate translation (same poem, language, version)
    existing = await session.execute(
        select(Translation).where(
            and_(
                Translation.poem_id == translation.poem_id,
                Translation.target_language == translation.target_language,
                Translation.version == translation.version
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Translation with this version already exists"
        )

    # Get next version if not specified
    if not hasattr(translation, 'version') or translation.version is None:
        max_version = await session.scalar(
            select(func.max(Translation.version)).where(
                Translation.poem_id == translation.poem_id
            )
        )
        translation.version = (max_version or 0) + 1

    db_translation = Translation(**translation.dict())
    session.add(db_translation)
    await session.commit()
    await session.refresh(db_translation)

    return TranslationResponse.from_orm(db_translation)

@router.get("/", response_model=List[TranslationResponse])
async def list_translations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    poem_id: Optional[str] = Query(None),
    target_language: Optional[str] = Query(None),
    translator_type: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session)
):
    """List translations with filtering and pagination"""
    query = select(Translation)

    # Apply filters
    if poem_id:
        query = query.where(Translation.poem_id == poem_id)
    if target_language:
        query = query.where(Translation.target_language == target_language)
    if translator_type:
        query = query.where(Translation.translator_type == translator_type)

    # Order by created_at desc
    query = query.order_by(desc(Translation.created_at))

    # Apply pagination
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    translations = result.scalars().all()

    return [TranslationResponse.from_orm(t) for t in translations]

@router.get("/{translation_id}", response_model=TranslationResponse)
async def get_translation(
    translation_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get a specific translation"""
    translation = await session.get(Translation, translation_id)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    return TranslationResponse.from_orm(translation)

@router.put("/{translation_id}", response_model=TranslationResponse)
async def update_translation(
    translation_id: str,
    translation_update: TranslationUpdate,
    session: AsyncSession = Depends(get_session)
):
    """Update a translation"""
    translation = await session.get(Translation, translation_id)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    # Update fields
    update_data = translation_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(translation, field, value)

    await session.commit()
    await session.refresh(translation)

    return TranslationResponse.from_orm(translation)

@router.delete("/{translation_id}")
async def delete_translation(
    translation_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Delete a translation"""
    translation = await session.get(Translation, translation_id)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    await session.delete(translation)
    await session.commit()

    return {"message": "Translation deleted successfully"}

@router.get("/{translation_id}/versions", response_model=List[TranslationResponse])
async def get_translation_versions(
    translation_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get all versions of a translation for a poem"""
    translation = await session.get(Translation, translation_id)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    versions = await session.execute(
        select(Translation).where(
            and_(
                Translation.poem_id == translation.poem_id,
                Translation.target_language == translation.target_language
            )
        ).order_by(desc(Translation.version))
    )

    return [TranslationResponse.from_orm(t) for t in versions.scalars().all()]

@router.post("/{translation_id}/notes")
async def add_human_note(
    translation_id: str,
    note_text: str,
    session: AsyncSession = Depends(get_session)
):
    """Add a human note to a translation"""
    translation = await session.get(Translation, translation_id)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    note = HumanNote(
        translation_id=translation_id,
        note_text=note_text
    )
    session.add(note)
    await session.commit()
    await session.refresh(note)

    return {"message": "Note added successfully", "note_id": note.id}

@router.get("/{translation_id}/notes")
async def get_translation_notes(
    translation_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get all notes for a translation"""
    translation = await session.get(Translation, translation_id)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    notes = await session.execute(
        select(HumanNote).where(
            HumanNote.translation_id == translation_id
        ).order_by(desc(HumanNote.created_at))
    )

    return [
        {
            "id": note.id,
            "note_text": note.note_text,
            "created_at": note.created_at
        }
        for note in notes.scalars().all()
    ]
```

### Import/Export API Operations
**File**: `src/vpsweb/repository/api/import_export.py`
**Priority**: Medium
**Dependencies**: FastAPI, file handling, validation

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import json
import csv
import io
from datetime import datetime

from ..database import get_session
from ..models import Poem, Translation
from ..schemas import PoemCreate, TranslationCreate
from ..exceptions import ValidationError, FileStorageException

router = APIRouter()

@router.post("/poems")
async def import_poems(
    file: UploadFile = File(...),
    format: str = "json",
    session: AsyncSession = Depends(get_session)
):
    """Import poems from JSON or CSV file"""

    if format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'json' or 'csv'")

    try:
        content = await file.read()

        if format == "json":
            poems_data = json.loads(content.decode('utf-8'))
            return await _import_poems_json(poems_data, session)
        else:
            return await _import_poems_csv(content.decode('utf-8'), session)

    except Exception as e:
        raise FileStorageException(f"Failed to import poems: {str(e)}")

@router.post("/translations")
async def import_translations(
    file: UploadFile = File(...),
    format: str = "json",
    session: AsyncSession = Depends(get_session)
):
    """Import translations from JSON file"""

    if format != "json":
        raise HTTPException(status_code=400, detail="Only JSON format supported for translations")

    try:
        content = await file.read()
        translations_data = json.loads(content.decode('utf-8'))
        return await _import_translations_json(translations_data, session)

    except Exception as e:
        raise FileStorageException(f"Failed to import translations: {str(e)}")

@router.get("/poems")
async def export_poems(
    format: str = "json",
    language: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Export poems in JSON or CSV format"""

    if format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Unsupported format")

    query = select(Poem)
    if language:
        query = query.where(Poem.source_language == language)

    poems = await session.execute(query)
    poems_list = poems.scalars().all()

    if format == "json":
        return await _export_poems_json(poems_list)
    else:
        return await _export_poems_csv(poems_list)

@router.get("/translations")
async def export_translations(
    format: str = "json",
    target_language: Optional[str] = None,
    translator_type: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Export translations with metadata"""

    if format != "json":
        raise HTTPException(status_code=400, detail="Only JSON format supported for translations")

    query = select(Translation)
    if target_language:
        query = query.where(Translation.target_language == target_language)
    if translator_type:
        query = query.where(Translation.translator_type == translator_type)

    translations = await session.execute(query)
    translations_list = translations.scalars().all()

    return await _export_translations_json(translations_list, session)

async def _import_poems_json(poems_data: List[Dict], session: AsyncSession) -> Dict[str, Any]:
    """Import poems from JSON data"""
    imported_count = 0
    errors = []

    for poem_data in poems_data:
        try:
            poem_create = PoemCreate(**poem_data)
            db_poem = Poem(**poem_create.dict())
            session.add(db_poem)
            await session.flush()
            imported_count += 1
        except Exception as e:
            errors.append(f"Failed to import poem {poem_data.get('poem_title', 'unknown')}: {str(e)}")

    await session.commit()

    return {
        "imported": imported_count,
        "errors": errors,
        "total": len(poems_data)
    }

async def _import_poems_csv(csv_content: str, session: AsyncSession) -> Dict[str, Any]:
    """Import poems from CSV data"""
    imported_count = 0
    errors = []

    reader = csv.DictReader(io.StringIO(csv_content))

    for row in reader:
        try:
            poem_data = {
                "poet_name": row["poet_name"],
                "poem_title": row["poem_title"],
                "source_language": row["source_language"],
                "original_text": row["original_text"],
                "form": row.get("form"),
                "period": row.get("period")
            }

            poem_create = PoemCreate(**poem_data)
            db_poem = Poem(**poem_create.dict())
            session.add(db_poem)
            await session.flush()
            imported_count += 1
        except Exception as e:
            errors.append(f"Failed to import CSV row {reader.line_num}: {str(e)}")

    await session.commit()

    return {
        "imported": imported_count,
        "errors": errors,
        "total": reader.line_num - 1
    }

async def _import_translations_json(translations_data: List[Dict], session: AsyncSession) -> Dict[str, Any]:
    """Import translations from JSON data"""
    imported_count = 0
    errors = []

    for translation_data in translations_data:
        try:
            # Validate poem exists
            poem = await session.get(Poem, translation_data["poem_id"])
            if not poem:
                errors.append(f"Poem not found: {translation_data['poem_id']}")
                continue

            translation_create = TranslationCreate(**translation_data)
            db_translation = Translation(**translation_create.dict())
            session.add(db_translation)
            await session.flush()
            imported_count += 1
        except Exception as e:
            errors.append(f"Failed to import translation: {str(e)}")

    await session.commit()

    return {
        "imported": imported_count,
        "errors": errors,
        "total": len(translations_data)
    }

async def _export_poems_json(poems: List[Poem]) -> StreamingResponse:
    """Export poems as JSON stream"""

    def generate():
        poems_data = []
        for poem in poems:
            poems_data.append({
                "id": poem.id,
                "poet_name": poem.poet_name,
                "poem_title": poem.poem_title,
                "source_language": poem.source_language,
                "original_text": poem.original_text,
                "form": poem.form,
                "period": poem.period,
                "created_at": poem.created_at,
                "updated_at": poem.updated_at
            })

        yield json.dumps(poems_data, indent=2, ensure_ascii=False)

    return StreamingResponse(
        io.StringIO(json.dumps([poem.__dict__ for poem in poems], indent=2, ensure_ascii=False)),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=poems_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"}
    )

async def _export_poems_csv(poems: List[Poem]) -> StreamingResponse:
    """Export poems as CSV stream"""

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["id", "poet_name", "poem_title", "source_language", "original_text", "form", "period", "created_at"])

    # Data rows
    for poem in poems:
        writer.writerow([
            poem.id, poem.poet_name, poem.poem_title, poem.source_language,
            poem.original_text, poem.form or "", poem.period or "", poem.created_at
        ])

    output.seek(0)

    return StreamingResponse(
        io.StringIO(output.getvalue()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=poems_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

async def _export_translations_json(translations: List[Translation], session: AsyncSession) -> StreamingResponse:
    """Export translations with full metadata"""

    translations_data = []
    for translation in translations:
        # Get associated poem
        poem = await session.get(Poem, translation.poem_id)

        translation_info = {
            "id": translation.id,
            "poem_id": translation.poem_id,
            "poem_title": poem.poem_title if poem else "Unknown",
            "poet_name": poem.poet_name if poem else "Unknown",
            "version": translation.version,
            "translator_type": translation.translator_type,
            "translator_info": translation.translator_info,
            "source_language": poem.source_language if poem else "Unknown",
            "target_language": translation.target_language,
            "translated_text": translation.translated_text,
            "license": translation.license,
            "created_at": translation.created_at
        }

        translations_data.append(translation_info)

    return StreamingResponse(
        io.StringIO(json.dumps(translations_data, indent=2, ensure_ascii=False)),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=translations_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"}
    )
```

### Updated API Layer Structure
```python
# Complete RESTful API Structure
/api/v1/poems/                    # Poem CRUD operations
/api/v1/poems/{id}               # Poem detail/update/delete
/api/v1/poems/{id}/translations   # Poem translations
/api/v1/translations/            # Translation CRUD operations
/api/v1/translations/{id}        # Translation detail/update/delete
/api/v1/translations/{id}/notes  # Translation notes
/api/v1/translations/{id}/versions # Translation versions
/api/v1/jobs/                    # Job management
/api/v1/jobs/{id}                # Job status
/api/v1/jobs/{id}/cancel         # Job cancellation
/api/v1/jobs/cleanup              # Job cleanup
/api/v1/import/poems              # Bulk poem import
/api/v1/import/translations       # Bulk translation import
/api/v1/export/poems              # Poem export
/api/v1/export/translations       # Translation export
```

## 🎨 Complete Web UI Architecture

### Web UI Component Structure
**Directory Structure**:
```
src/vpsweb/repository/web/
├── routes.py              # Web UI routes and controllers
├── templates/             # Jinja2 templates
│   ├── base.html         # Base template with common layout
│   ├── dashboard.html    # Dashboard with statistics
│   ├── poems/
│   │   ├── list.html     # Poem listing page
│   │   ├── new.html      # New poem form
│   │   ├── detail.html   # Poem detail view
│   │   └── compare.html  # Translation comparison
│   ├── translations/
│   │   ├── new.html      # New translation form
│   │   ├── detail.html   # Translation detail
│   │   └── edit.html     # Edit translation
│   ├── jobs/
│   │   ├── list.html     # Job listing
│   │   └── detail.html   # Job status detail
│   ├── import/
│   │   └── index.html    # Import interface
│   └── partials/
│       ├── navbar.html    # Navigation bar
│       ├── sidebar.html   # Sidebar navigation
│       ├── pagination.html # Pagination component
│       └── modals.html    # Modal dialogs
├── static/               # Static assets
│   ├── css/
│   │   ├── main.css      # Main styles
│   │   ├── responsive.css # Responsive design
│   │   └── components.css # Component styles
│   ├── js/
│   │   ├── main.js       # Main JavaScript
│   │   ├── job-status.js # Job status polling
│   │   └── comparison.js # Translation comparison
│   └── images/
└── utils/
    ├── template_helpers.py # Template helper functions
    └── form_helpers.py     # Form processing utilities
```

### Base Template with Responsive Design
**File**: `src/vpsweb/repository/web/templates/base.html`
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="VPSWeb Repository - Central Poetry Translation Management">
    <title>{% block title %}VPSWeb Repository{% endblock %}</title>

    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

    <!-- Custom CSS -->
    <link href="/static/css/main.css" rel="stylesheet">
    <link href="/static/css/responsive.css" rel="stylesheet">

    <!-- Accessibility improvements -->
    <meta name="theme-color" content="#0d6efd">
    <meta name="color-scheme" content="light dark">

    {% block extra_head %}{% endblock %}
</head>
<body>
    <!-- Skip to main content for accessibility -->
    <a href="#main-content" class="visually-hidden-focusable">Skip to main content</a>

    <!-- Navigation -->
    {% include "partials/navbar.html" %}

    <!-- Main content -->
    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar (desktop only) -->
            <aside class="col-md-3 col-lg-2 d-md-block bg-light sidebar collapse">
                {% include "partials/sidebar.html" %}
            </aside>

            <!-- Main content area -->
            <main class="col-md-9 ms-sm-auto col-lg-10 px-md-4" id="main-content">
                <!-- Breadcrumb navigation -->
                {% block breadcrumb %}{% endblock %}

                <!-- Page header -->
                {% block page_header %}{% endblock %}

                <!-- Flash messages -->
                {% include "partials/flash_messages.html" %}

                <!-- Page content -->
                {% block content %}{% endblock %}
            </main>
        </div>
    </div>

    <!-- Footer -->
    {% include "partials/footer.html" %}

    <!-- Modals container -->
    <div id="modal-container"></div>

    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/static/js/main.js"></script>

    {% block scripts %}{% endblock %}

    <!-- Accessibility enhancements -->
    <script>
        // Add ARIA labels dynamically for better screen reader support
        document.addEventListener('DOMContentLoaded', function() {
            // Add role="navigation" to main nav
            document.querySelector('nav').setAttribute('role', 'navigation');

            // Add live regions for dynamic content
            const jobStatusContainer = document.getElementById('job-status');
            if (jobStatusContainer) {
                jobStatusContainer.setAttribute('aria-live', 'polite');
                jobStatusContainer.setAttribute('aria-atomic', 'true');
            }
        });
    </script>
</body>
</html>
```

### Navigation Bar Component
**File**: `src/vpsweb/repository/web/templates/partials/navbar.html`
```html
<nav class="navbar navbar-expand-lg navbar-dark bg-primary sticky-top">
    <div class="container-fluid">
        <!-- Logo and title -->
        <a class="navbar-brand d-flex align-items-center" href="/">
            <i class="bi bi-journal-text me-2"></i>
            <span>VPSWeb Repository</span>
        </a>

        <!-- Mobile toggle -->
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav"
                aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
            <span class="navbar-toggler-icon"></span>
        </button>

        <!-- Navigation items -->
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav me-auto">
                <li class="nav-item">
                    <a class="nav-link" href="/" aria-current="{% if request.url.path == '/' %}page{% endif %}">
                        <i class="bi bi-speedometer2 me-1"></i>
                        Dashboard
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/poems" aria-current="{% if '/poems' in request.url.path %}page{% endif %}">
                        <i class="bi bi-book me-1"></i>
                        Poems
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="/jobs" aria-current="{% if '/jobs' in request.url.path %}page{% endif %}">
                        <i class="bi bi-clock-history me-1"></i>
                        Jobs
                        <span class="badge bg-danger ms-1" id="active-jobs-count" style="display: none;">0</span>
                    </a>
                </li>
                <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown"
                       aria-expanded="false">
                        <i class="bi bi-gear me-1"></i>
                        Tools
                    </a>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="/import">Import Data</a></li>
                        <li><a class="dropdown-item" href="/export">Export Data</a></li>
                        <li><hr class="dropdown-divider"></li>
                        <li><a class="dropdown-item" href="/settings">Settings</a></li>
                    </ul>
                </li>
            </ul>

            <!-- Search -->
            <form class="d-flex me-3" role="search" action="/poems" method="GET">
                <input class="form-control form-control-sm" type="search" name="search"
                       placeholder="Search poems..." aria-label="Search">
                <button class="btn btn-outline-light btn-sm ms-1" type="submit">
                    <i class="bi bi-search"></i>
                </button>
            </form>

            <!-- User menu -->
            <ul class="navbar-nav">
                <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown"
                       aria-expanded="false">
                        <i class="bi bi-person-circle me-1"></i>
                        Admin
                    </a>
                    <ul class="dropdown-menu dropdown-menu-end">
                        <li><a class="dropdown-item" href="/settings">
                            <i class="bi bi-gear me-2"></i>Settings
                        </a></li>
                        <li><a class="dropdown-item" href="/docs">
                            <i class="bi bi-book me-2"></i>Documentation
                        </a></li>
                        <li><hr class="dropdown-divider"></li>
                        <li><a class="dropdown-item" href="/logout">
                            <i class="bi bi-box-arrow-right me-2"></i>Logout
                        </a></li>
                    </ul>
                </li>
            </ul>
        </div>
    </div>
</nav>

<!-- Quick stats bar -->
<div class="bg-light border-bottom py-2">
    <div class="container-fluid">
        <div class="row align-items-center">
            <div class="col-md-8">
                <div class="d-flex gap-4">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-book text-primary me-1"></i>
                        <span class="small text-muted">Poems:</span>
                        <strong class="ms-1">{{ stats.poems if stats else 0 }}</strong>
                    </div>
                    <div class="d-flex align-items-center">
                        <i class="bi bi-translate text-success me-1"></i>
                        <span class="small text-muted">Translations:</span>
                        <strong class="ms-1">{{ stats.translations if stats else 0 }}</strong>
                    </div>
                    <div class="d-flex align-items-center">
                        <i class="bi bi-cpu text-info me-1"></i>
                        <span class="small text-muted">Active Jobs:</span>
                        <strong class="ms-1 text-warning" id="nav-active-jobs">0</strong>
                    </div>
                </div>
            </div>
            <div class="col-md-4 text-end">
                <span class="badge bg-secondary">
                    <i class="bi bi-database me-1"></i>
                    {{ config.repository.root_path | basename }}
                </span>
            </div>
        </div>
    </div>
</div>
```

### Dashboard Template
**File**: `src/vpsweb/repository/web/templates/dashboard.html`
```html
{% extends "base.html" %}

{% block title %}Dashboard - VPSWeb Repository{% endblock %}

{% block page_header %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
    <h1 class="h2">Dashboard</h1>
    <div class="btn-toolbar mb-2 mb-md-0">
        <div class="btn-group me-2">
            <a href="/poems/new" class="btn btn-primary">
                <i class="bi bi-plus-circle me-1"></i>New Poem
            </a>
            <a href="/import" class="btn btn-outline-secondary">
                <i class="bi bi-upload me-1"></i>Import
            </a>
        </div>
    </div>
</div>
{% endblock %}

{% block content %}
<!-- Statistics Cards -->
<div class="row mb-4">
    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card border-left-primary shadow h-100 py-2">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">
                            Total Poems
                        </div>
                        <div class="h5 mb-0 font-weight-bold text-gray-800">
                            {{ stats.poems if stats else 0 }}
                        </div>
                    </div>
                    <div class="col-auto">
                        <i class="bi bi-book fa-2x text-gray-300"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card border-left-success shadow h-100 py-2">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="text-xs font-weight-bold text-success text-uppercase mb-1">
                            AI Translations
                        </div>
                        <div class="h5 mb-0 font-weight-bold text-gray-800">
                            {{ stats.ai_translations if stats else 0 }}
                        </div>
                    </div>
                    <div class="col-auto">
                        <i class="bi bi-cpu fa-2x text-gray-300"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card border-left-info shadow h-100 py-2">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="text-xs font-weight-bold text-info text-uppercase mb-1">
                            Human Translations
                        </div>
                        <div class="h5 mb-0 font-weight-bold text-gray-800">
                            {{ stats.human_translations if stats else 0 }}
                        </div>
                    </div>
                    <div class="col-auto">
                        <i class="bi bi-person fa-2x text-gray-300"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card border-left-warning shadow h-100 py-2">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="text-xs font-weight-bold text-warning text-uppercase mb-1">
                            Active Jobs
                        </div>
                        <div class="h5 mb-0 font-weight-bold text-gray-800" id="dashboard-active-jobs">
                            0
                        </div>
                    </div>
                    <div class="col-auto">
                        <i class="bi bi-clock-history fa-2x text-gray-300"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Recent Activity -->
<div class="row">
    <div class="col-lg-8">
        <div class="card shadow mb-4">
            <div class="card-header py-3 d-flex flex-row align-items-center justify-content-between">
                <h6 class="m-0 font-weight-bold text-primary">Recent Poems</h6>
                <a href="/poems" class="btn btn-sm btn-outline-primary">View All</a>
            </div>
            <div class="card-body">
                {% if recent_poems %}
                    <div class="list-group list-group-flush">
                        {% for poem in recent_poems %}
                        <div class="list-group-item d-flex justify-content-between align-items-center">
                            <div class="flex-grow-1">
                                <h6 class="mb-1">{{ poem.poet_name }} - {{ poem.poem_title }}</h6>
                                <small class="text-muted">
                                    {{ poem.source_language }} •
                                    Created {{ poem.created_at.strftime('%Y-%m-%d %H:%M') }}
                                </small>
                            </div>
                            <div class="text-end">
                                <span class="badge bg-secondary rounded-pill">{{ poem.translation_count or 0 }} translations</span>
                                <a href="/poems/{{ poem.id }}" class="btn btn-sm btn-outline-primary ms-2">View</a>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                {% else %}
                    <div class="text-center py-4">
                        <i class="bi bi-journal-text display-4 text-muted"></i>
                        <p class="text-muted mt-2">No poems yet. <a href="/poems/new">Create your first poem</a> to get started.</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>

    <div class="col-lg-4">
        <!-- Quick Actions -->
        <div class="card shadow mb-4">
            <div class="card-header py-3">
                <h6 class="m-0 font-weight-bold text-primary">Quick Actions</h6>
            </div>
            <div class="card-body">
                <div class="d-grid gap-2">
                    <a href="/poems/new" class="btn btn-primary">
                        <i class="bi bi-plus-circle me-2"></i>Add New Poem
                    </a>
                    <a href="/translations/new" class="btn btn-success">
                        <i class="bi bi-translate me-2"></i>Add Translation
                    </a>
                    <a href="/import" class="btn btn-info">
                        <i class="bi bi-upload me-2"></i>Import Data
                    </a>
                    <a href="/export" class="btn btn-secondary">
                        <i class="bi bi-download me-2"></i>Export Data
                    </a>
                </div>
            </div>
        </div>

        <!-- Job Status -->
        <div class="card shadow mb-4">
            <div class="card-header py-3">
                <h6 class="m-0 font-weight-bold text-primary">Job Status</h6>
            </div>
            <div class="card-body" id="job-status-container">
                <div class="text-center py-3">
                    <p class="text-muted">No active jobs</p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="/static/js/dashboard.js"></script>
<script>
// Poll job status every 5 seconds
function updateJobStatus() {
    fetch('/api/v1/jobs/?status=running&limit=5')
        .then(response => response.json())
        .then(jobs => {
            const container = document.getElementById('job-status-container');
            const activeJobsCount = document.getElementById('dashboard-active-jobs');
            const navActiveJobs = document.getElementById('nav-active-jobs');

            activeJobsCount.textContent = jobs.length;
            navActiveJobs.textContent = jobs.length;

            if (jobs.length > 0) {
                navActiveJobs.style.display = 'inline';

                let html = '';
                jobs.forEach(job => {
                    html += `
                        <div class="mb-3 p-2 border rounded">
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="text-muted">Job #${job.id.substring(0, 8)}</small>
                                <span class="badge bg-warning">${job.status}</span>
                            </div>
                            <div class="progress mt-1" style="height: 4px;">
                                <div class="progress-bar bg-success" role="progressbar"
                                     style="width: ${job.progress}%"></div>
                            </div>
                        </div>
                    `;
                });
                container.innerHTML = html;
            } else {
                navActiveJobs.style.display = 'none';
                container.innerHTML = '<div class="text-center py-3"><p class="text-muted">No active jobs</p></div>';
            }
        })
        .catch(error => {
            console.error('Failed to fetch job status:', error);
        });
}

// Initial load and periodic updates
updateJobStatus();
setInterval(updateJobStatus, 5000);
</script>
{% endblock %}
```

### Poem Listing Template with Advanced Filtering
**File**: `src/vpsweb/repository/web/templates/poems/list.html`
```html
{% extends "base.html" %}

{% block title %}Poems - VPSWeb Repository{% endblock %}

{% block breadcrumb %}
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="/">Home</a></li>
        <li class="breadcrumb-item active">Poems</li>
    </ol>
</nav>
{% endblock %}

{% block page_header %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
    <h1 class="h2">Poems</h1>
    <div class="btn-toolbar mb-2 mb-md-0">
        <div class="btn-group me-2">
            <a href="/poems/new" class="btn btn-primary">
                <i class="bi bi-plus-circle me-1"></i>New Poem
            </a>
            <button type="button" class="btn btn-outline-secondary" data-bs-toggle="modal" data-bs-target="#filterModal">
                <i class="bi bi-funnel me-1"></i>Filter
            </button>
        </div>
        <div class="btn-group">
            <a href="/export/poems?format=json" class="btn btn-outline-success">
                <i class="bi bi-download me-1"></i>Export JSON
            </a>
            <a href="/export/poems?format=csv" class="btn btn-outline-success">
                <i class="bi bi-download me-1"></i>Export CSV
            </a>
        </div>
    </div>
</div>
{% endblock %}

{% block content %}
<!-- Search and Filter Bar -->
<div class="row mb-4">
    <div class="col-12">
        <form method="GET" class="row g-3">
            <div class="col-md-4">
                <input type="text" class="form-control" name="search" placeholder="Search poems..."
                       value="{{ filters.search }}">
            </div>
            <div class="col-md-2">
                <select class="form-select" name="language">
                    <option value="">All Languages</option>
                    <option value="en" {% if filters.language == 'en' %}selected{% endif %}>English</option>
                    <option value="zh-Hans" {% if filters.language == 'zh-Hans' %}selected{% endif %}>Simplified Chinese</option>
                    <option value="zh-Hant" {% if filters.language == 'zh-Hant' %}selected{% endif %}>Traditional Chinese</option>
                </select>
            </div>
            <div class="col-md-2">
                <input type="text" class="form-control" name="poet" placeholder="Poet name..."
                       value="{{ filters.poet }}">
            </div>
            <div class="col-md-2">
                <select class="form-select" name="sort">
                    <option value="recent">Most Recent</option>
                    <option value="title">Title A-Z</option>
                    <option value="poet">Poet A-Z</option>
                    <option value="translations">Most Translations</option>
                </select>
            </div>
            <div class="col-md-2">
                <button type="submit" class="btn btn-primary w-100">
                    <i class="bi bi-search me-1"></i>Search
                </button>
            </div>
        </form>
    </div>
</div>

<!-- Results Summary -->
<div class="row mb-3">
    <div class="col-12">
        <div class="d-flex justify-content-between align-items-center">
            <p class="mb-0">
                {% if poems %}
                    Found <strong>{{ poems|length }}</strong> poems
                    {% if filters.search or filters.poet or filters.language %}
                        matching your criteria
                    {% endif %}
                {% else %}
                    No poems found
                {% endif %}
            </p>
            <div class="btn-group btn-group-sm">
                <button type="button" class="btn btn-outline-secondary" id="grid-view">
                    <i class="bi bi-grid-3x3-gap"></i>
                </button>
                <button type="button" class="btn btn-outline-secondary active" id="list-view">
                    <i class="bi bi-list"></i>
                </button>
            </div>
        </div>
    </div>
</div>

<!-- Poems List -->
{% if poems %}
<div class="row" id="poems-container">
    {% for poem in poems %}
    <div class="col-12 poem-item">
        <div class="card mb-3 hover-shadow transition-shadow">
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-8">
                        <div class="d-flex align-items-start">
                            <div class="flex-grow-1">
                                <h5 class="card-title mb-1">
                                    <a href="/poems/{{ poem.id }}" class="text-decoration-none">
                                        {{ poem.poem_title }}
                                    </a>
                                    <small class="text-muted ms-2">{{ poem.source_language }}</small>
                                </h5>
                                <p class="card-text text-muted mb-2">
                                    <i class="bi bi-person me-1"></i>{{ poem.poet_name }}
                                    {% if poem.form %}<span class="badge bg-secondary ms-2">{{ poem.form }}</span>{% endif %}
                                    {% if poem.period %}<span class="badge bg-info ms-1">{{ poem.period }}</span>{% endif %}
                                </p>
                                <p class="card-text">{{ poem.original_text[:200] }}{% if poem.original_text|length > 200 %}...{% endif %}</p>
                                <div class="d-flex align-items-center">
                                    <small class="text-muted">
                                        <i class="bi bi-clock me-1"></i>
                                        Created {{ poem.created_at.strftime('%Y-%m-%d %H:%M') }}
                                    </small>
                                    {% if poem.updated_at != poem.created_at %}
                                    <small class="text-muted ms-3">
                                        <i class="bi bi-pencil me-1"></i>
                                        Updated {{ poem.updated_at.strftime('%Y-%m-%d %H:%M') }}
                                    </small>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4 text-end">
                        <div class="mb-2">
                            <span class="badge bg-primary rounded-pill">
                                {{ poem.translation_count or 0 }} translations
                            </span>
                        </div>
                        <div class="btn-group-vertical btn-group-sm d-grid gap-1">
                            <a href="/poems/{{ poem.id }}" class="btn btn-outline-primary">
                                <i class="bi bi-eye me-1"></i>View Details
                            </a>
                            <div class="btn-group">
                                <a href="/poems/{{ poem.id }}/translate" class="btn btn-outline-success">
                                    <i class="bi bi-translate me-1"></i>Translate
                                </a>
                                <button type="button" class="btn btn-outline-secondary dropdown-toggle"
                                        data-bs-toggle="dropdown" aria-expanded="false">
                                    <i class="bi bi-three-dots"></i>
                                </button>
                                <ul class="dropdown-menu">
                                    <li><a class="dropdown-item" href="/poems/{{ poem.id }}/edit">
                                        <i class="bi bi-pencil me-2"></i>Edit
                                    </a></li>
                                    <li><a class="dropdown-item" href="/poems/{{ poem.id }}/compare">
                                        <i class="bi bi-columns me-2"></i>Compare
                                    </a></li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li><a class="dropdown-item text-danger" href="/poems/{{ poem.id }}/delete">
                                        <i class="bi bi-trash me-2"></i>Delete
                                    </a></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    {% endfor %}
</div>

<!-- Pagination -->
{% include "partials/pagination.html" %}

{% else %}
<div class="text-center py-5">
    <i class="bi bi-journal-text display-1 text-muted"></i>
    <h3 class="mt-3">No poems found</h3>
    <p class="text-muted">
        {% if filters.search or filters.poet or filters.language %}
            Try adjusting your search criteria or
            <a href="/poems">clear all filters</a>.
        {% else %}
            Get started by <a href="/poems/new">creating your first poem</a>.
        {% endif %}
    </p>
    <a href="/poems/new" class="btn btn-primary mt-3">
        <i class="bi bi-plus-circle me-1"></i>Create New Poem
    </a>
</div>
{% endif %}
{% endblock %}

{% block scripts %}
<script>
// View toggle functionality
document.getElementById('grid-view').addEventListener('click', function() {
    document.getElementById('list-view').classList.remove('active');
    this.classList.add('active');
    // Implement grid view logic here
});

document.getElementById('list-view').addEventListener('click', function() {
    document.getElementById('grid-view').classList.remove('active');
    this.classList.add('active');
    // Ensure list view is maintained
});

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K for search focus
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.querySelector('input[name="search"]').focus();
    }
});
</script>
{% endblock %}
```

### Translation Comparison Template
**File**: `src/vpsweb/repository/web/templates/poems/compare.html`
```html
{% extends "base.html" %}

{% block title %}Translation Comparison - {{ poem.poet_name }} - {{ poem.poem_title }}{% endblock %}

{% block breadcrumb %}
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="/">Home</a></li>
        <li class="breadcrumb-item"><a href="/poems">Poems</a></li>
        <li class="breadcrumb-item"><a href="/poems/{{ poem.id }}">{{ poem.poem_title }}</a></li>
        <li class="breadcrumb-item active">Compare</li>
    </ol>
</nav>
{% endblock %}

{% block page_header %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
    <div>
        <h1 class="h2">{{ poem.poet_name }} - {{ poem.poem_title }}</h1>
        <p class="text-muted mb-0">Translation Comparison</p>
    </div>
    <div class="btn-toolbar mb-2 mb-md-0">
        <div class="btn-group me-2">
            <a href="/poems/{{ poem.id }}" class="btn btn-outline-secondary">
                <i class="bi bi-arrow-left me-1"></i>Back to Poem
            </a>
            <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#newTranslationModal">
                <i class="bi bi-plus-circle me-1"></i>Add Translation
            </button>
        </div>
    </div>
</div>
{% endblock %}

{% block content %}
<!-- Original Poem Section -->
<div class="card mb-4">
    <div class="card-header bg-light">
        <h5 class="mb-0">
            <i class="bi bi-book me-2"></i>Original Poem
            <small class="text-muted ms-2">({{ poem.source_language }})</small>
        </h5>
    </div>
    <div class="card-body">
        <div class="row">
            <div class="col-md-8">
                <pre class="poem-text">{{ poem.original_text }}</pre>
            </div>
            <div class="col-md-4">
                <dl class="row">
                    <dt class="col-sm-4">Poet:</dt>
                    <dd class="col-sm-8">{{ poem.poet_name }}</dd>

                    <dt class="col-sm-4">Language:</dt>
                    <dd class="col-sm-8">{{ poem.source_language }}</dd>

                    {% if poem.form %}
                    <dt class="col-sm-4">Form:</dt>
                    <dd class="col-sm-8">{{ poem.form }}</dd>
                    {% endif %}

                    {% if poem.period %}
                    <dt class="col-sm-4">Period:</dt>
                    <dd class="col-sm-8">{{ poem.period }}</dd>
                    {% endif %}
                </dl>
            </div>
        </div>
    </div>
</div>

<!-- Translations Comparison -->
{% if translations %}
<div class="row">
    {% for translation in translations %}
    <div class="col-lg-6 mb-4">
        <div class="card h-100 translation-card" data-translation-id="{{ translation.id }}">
            <div class="card-header d-flex justify-content-between align-items-center
                {% if translation.translator_type == 'ai' %}bg-success text-white{% else %}bg-info text-white{% endif %}">
                <div>
                    <h6 class="mb-0">
                        {{ translation.target_language }}
                        <small class="ms-2">Version {{ translation.version }}</small>
                    </h6>
                    <small>
                        {% if translation.translator_type == 'ai' %}
                            <i class="bi bi-cpu me-1"></i>{{ translation.translator_info }}
                        {% else %}
                            <i class="bi bi-person me-1"></i>{{ translation.translator_info }}
                        {% endif %}
                    </small>
                </div>
                <div class="btn-group btn-group-sm">
                    <button type="button" class="btn btn-light btn-sm"
                            onclick="toggleTranslation('{{ translation.id }}')"
                            title="Toggle visibility">
                        <i class="bi bi-eye"></i>
                    </button>
                    {% if translation.translator_type == 'ai' and translation.ai_log %}
                    <button type="button" class="btn btn-light btn-sm"
                            onclick="showTranslationDetails('{{ translation.id }}')"
                            title="Show AI details">
                        <i class="bi bi-info-circle"></i>
                    </button>
                    {% endif %}
                </div>
            </div>
            <div class="card-body">
                <div class="translation-content">
                    <pre class="poem-text">{{ translation.translated_text }}</pre>
                </div>

                <div class="translation-meta mt-3">
                    <div class="row">
                        <div class="col-6">
                            <small class="text-muted">
                                <i class="bi bi-clock me-1"></i>
                                {{ translation.created_at.strftime('%Y-%m-%d %H:%M') }}
                            </small>
                        </div>
                        <div class="col-6 text-end">
                            {% if translation.license %}
                            <small class="text-muted">{{ translation.license }}</small>
                            {% endif %}
                        </div>
                    </div>
                </div>

                {% if translation.human_notes %}
                <div class="translation-notes mt-3">
                    <h6 class="text-muted">Notes:</h6>
                    {% for note in translation.human_notes %}
                    <div class="alert alert-info small p-2">
                        {{ note.note_text }}
                        <small class="d-block text-muted mt-1">
                            {{ note.created_at.strftime('%Y-%m-%d %H:%M') }}
                        </small>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            <div class="card-footer">
                <div class="btn-group btn-group-sm w-100">
                    <a href="/translations/{{ translation.id }}/edit" class="btn btn-outline-secondary">
                        <i class="bi bi-pencil me-1"></i>Edit
                    </a>
                    <a href="/translations/{{ translation.id }}" class="btn btn-outline-primary">
                        <i class="bi bi-eye me-1"></i>Details
                    </a>
                    <button type="button" class="btn btn-outline-warning"
                            onclick="copyTranslation('{{ translation.id }}')">
                        <i class="bi bi-clipboard me-1"></i>Copy
                    </button>
                </div>
            </div>
        </div>
    </div>
    {% endfor %}
</div>

<!-- Comparison Controls -->
<div class="card mt-4">
    <div class="card-header">
        <h6 class="mb-0">Comparison Controls</h6>
    </div>
    <div class="card-body">
        <div class="row align-items-center">
            <div class="col-md-6">
                <div class="btn-group" role="group">
                    <button type="button" class="btn btn-outline-primary" onclick="toggleAllTranslations(true)">
                        <i class="bi bi-eye me-1"></i>Show All
                    </button>
                    <button type="button" class="btn btn-outline-primary" onclick="toggleAllTranslations(false)">
                        <i class="bi bi-eye-slash me-1"></i>Hide All
                    </button>
                    <button type="button" class="btn btn-outline-primary" onclick="toggleByType('ai')">
                        <i class="bi bi-cpu me-1"></i>AI Only
                    </button>
                    <button type="button" class="btn btn-outline-primary" onclick="toggleByType('human')">
                        <i class="bi bi-person me-1"></i>Human Only
                    </button>
                </div>
            </div>
            <div class="col-md-6 text-end">
                <div class="form-check form-switch d-inline-block">
                    <input class="form-check-input" type="checkbox" id="syncScroll">
                    <label class="form-check-label" for="syncScroll">
                        Sync scrolling
                    </label>
                </div>
                <div class="form-check form-switch d-inline-block ms-3">
                    <input class="form-check-input" type="checkbox" id="highlightDifferences">
                    <label class="form-check-label" for="highlightDifferences">
                        Highlight differences
                    </label>
                </div>
            </div>
        </div>
    </div>
</div>

{% else %}
<div class="text-center py-5">
    <i class="bi bi-translate display-1 text-muted"></i>
    <h3 class="mt-3">No translations yet</h3>
    <p class="text-muted">Create the first translation for this poem.</p>
    <a href="/translations/new?poem_id={{ poem.id }}" class="btn btn-primary mt-3">
        <i class="bi bi-plus-circle me-1"></i>Add Translation
    </a>
</div>
{% endif %}
{% endblock %}

<!-- AI Translation Details Modal -->
{% for translation in translations %}
    {% if translation.translator_type == 'ai' and translation.ai_log %}
<div class="modal fade" id="detailsModal{{ translation.id }}" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">AI Translation Details</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="row">
                    <div class="col-md-6">
                        <h6>Model Information</h6>
                        <table class="table table-sm">
                            <tr>
                                <td>Model:</td>
                                <td>{{ translation.ai_log.model_name }}</td>
                            </tr>
                            <tr>
                                <td>Workflow Mode:</td>
                                <td>{{ translation.ai_log.workflow_mode }}</td>
                            </tr>
                            <tr>
                                <td>Runtime:</td>
                                <td>{{ translation.ai_log.runtime_seconds }}s</td>
                            </tr>
                        </table>
                    </div>
                    <div class="col-md-6">
                        <h6>Token Usage</h6>
                        {% set tokens = translation.ai_log.token_usage_json | from_json %}
                        <table class="table table-sm">
                            <tr>
                                <td>Prompt:</td>
                                <td>{{ tokens.prompt_tokens }}</td>
                            </tr>
                            <tr>
                                <td>Completion:</td>
                                <td>{{ tokens.completion_tokens }}</td>
                            </tr>
                            <tr>
                                <td>Total:</td>
                                <td><strong>{{ tokens.total_tokens }}</strong></td>
                            </tr>
                        </table>
                    </div>
                </div>

                {% if translation.ai_log.notes %}
                <div class="mt-3">
                    <h6>Notes</h6>
                    <p class="text-muted">{{ translation.ai_log.notes }}</p>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
    {% endif %}
{% endfor %}

{% block scripts %}
<script>
function toggleTranslation(translationId) {
    const card = document.querySelector(`[data-translation-id="${translationId}"]`);
    card.style.display = card.style.display === 'none' ? 'block' : 'none';
}

function toggleAllTranslations(show) {
    document.querySelectorAll('.translation-card').forEach(card => {
        card.style.display = show ? 'block' : 'none';
    });
}

function toggleByType(type) {
    document.querySelectorAll('.translation-card').forEach(card => {
        const cardType = card.querySelector('.card-header').textContent.includes('cpu') ? 'ai' : 'human';
        card.style.display = cardType === type ? 'block' : 'none';
    });
}

function showTranslationDetails(translationId) {
    const modal = document.getElementById(`detailsModal${translationId}`);
    if (modal) {
        new bootstrap.Modal(modal).show();
    }
}

function copyTranslation(translationId) {
    const content = document.querySelector(`[data-translation-id="${translationId}"] .poem-text`).textContent;
    navigator.clipboard.writeText(content).then(() => {
        // Show success message
        const toast = document.createElement('div');
        toast.className = 'position-fixed bottom-0 end-0 p-3';
        toast.style.zIndex = '1050';
        toast.innerHTML = '<div class="toast show" role="alert"><div class="toast-body">Translation copied to clipboard!</div></div>';
        document.body.appendChild(toast);

        setTimeout(() => {
            document.body.removeChild(toast);
        }, 3000);
    });
}

// Sync scrolling functionality
document.getElementById('syncScroll')?.addEventListener('change', function(e) {
    if (e.target.checked) {
        // Implement sync scrolling logic here
        console.log('Sync scrolling enabled');
    }
});

// Highlight differences functionality
document.getElementById('highlightDifferences')?.addEventListener('change', function(e) {
    if (e.target.checked) {
        // Implement difference highlighting here
        console.log('Difference highlighting enabled');
    }
});
</script>

<style>
.poem-text {
    white-space: pre-wrap;
    font-family: 'Georgia', serif;
    font-size: 1.1em;
    line-height: 1.6;
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 0.375rem;
    border: 1px solid #dee2e6;
}

.translation-card {
    transition: all 0.3s ease;
}

.translation-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.hover-shadow:hover {
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    transition: box-shadow 0.3s ease;
}

@media (max-width: 768px) {
    .poem-text {
        font-size: 1em;
        padding: 0.5rem;
    }
}
</style>
{% endblock %}
```

### Job Status Management Interface
**File**: `src/vpsweb/repository/web/templates/jobs/detail.html`
```html
{% extends "base.html" %}

{% block title %}Job Status - {{ job.id[:8] }}{% endblock %}

{% block breadcrumb %}
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="/">Home</a></li>
        <li class="breadcrumb-item"><a href="/jobs">Jobs</a></li>
        <li class="breadcrumb-item active">Job {{ job.id[:8] }}</li>
    </ol>
</nav>
{% endblock %}

{% block page_header %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
    <div>
        <h1 class="h2">Job Status</h1>
        <p class="text-muted mb-0">ID: {{ job.id }}</p>
    </div>
    <div class="btn-toolbar mb-2 mb-md-0">
        {% if job.status in ['pending', 'running'] %}
        <button type="button" class="btn btn-warning" onclick="cancelJob('{{ job.id }}')">
            <i class="bi bi-x-circle me-1"></i>Cancel Job
        </button>
        {% endif %}
        <a href="/jobs" class="btn btn-outline-secondary ms-2">
            <i class="bi bi-arrow-left me-1"></i>Back to Jobs
        </a>
    </div>
</div>
{% endblock %}

{% block content %}
<!-- Job Status Card -->
<div class="card mb-4">
    <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">Job Information</h5>
        <span class="badge
            {% if job.status == 'completed' %}bg-success
            {% elif job.status == 'failed' %}bg-danger
            {% elif job.status == 'running' %}bg-warning
            {% elif job.status == 'cancelled' %}bg-secondary
            {% else %}bg-info{% endif %}">
            {{ job.status.title() }}
        </span>
    </div>
    <div class="card-body">
        <div class="row">
            <div class="col-md-6">
                <dl class="row">
                    <dt class="col-sm-4">Job Type:</dt>
                    <dd class="col-sm-8">{{ job.job_type.title() }}</dd>

                    <dt class="col-sm-4">Priority:</dt>
                    <dd class="col-sm-8">
                        <span class="badge bg-{{ 'danger' if job.priority == 'critical' else 'warning' if job.priority == 'high' else 'info' }}">
                            {{ job.priority.title() }}
                        </span>
                    </dd>

                    <dt class="col-sm-4">Created:</dt>
                    <dd class="col-sm-8">{{ job.created_at.strftime('%Y-%m-%d %H:%M:%S') }}</dd>

                    {% if job.started_at %}
                    <dt class="col-sm-4">Started:</dt>
                    <dd class="col-sm-8">{{ job.started_at.strftime('%Y-%m-%d %H:%M:%S') }}</dd>
                    {% endif %}

                    {% if job.completed_at %}
                    <dt class="col-sm-4">Completed:</dt>
                    <dd class="col-sm-8">{{ job.completed_at.strftime('%Y-%m-%d %H:%M:%S') }}</dd>
                    {% endif %}
                </dl>
            </div>
            <div class="col-md-6">
                <dt class="col-sm-4">Progress:</dt>
                <dd class="col-sm-8">
                    <div class="progress mb-2" style="height: 20px;">
                        <div class="progress-bar"
                             id="job-progress-bar"
                             role="progressbar"
                             style="width: {{ job.progress }}%"
                             aria-valuenow="{{ job.progress }}"
                             aria-valuemin="0"
                             aria-valuemax="100">
                            {{ job.progress }}%
                        </div>
                    </div>
                    <small class="text-muted">{{ job.progress }}% Complete</small>
                </dd>

                {% if job.retry_count > 0 %}
                <dt class="col-sm-4">Retries:</dt>
                <dd class="col-sm-8">
                    {{ job.retry_count }} / {{ job.max_retries }} attempts
                </dd>
                {% endif %}
            </div>
        </div>

        {% if job.error %}
        <div class="alert alert-danger mt-3">
            <h6 class="alert-heading">Error Information</h6>
            <p class="mb-0">{{ job.error }}</p>
        </div>
        {% endif %}
    </div>
</div>

<!-- Job Result -->
{% if job.result %}
<div class="card mb-4">
    <div class="card-header">
        <h6 class="mb-0">Job Result</h6>
    </div>
    <div class="card-body">
        <pre class="bg-light p-3 rounded"><code>{{ job.result | tojson(indent=2) }}</code></pre>
    </div>
</div>
{% endif %}
{% endblock %}

{% block scripts %}
<script>
let jobUpdateInterval;

function updateJobStatus() {
    fetch(`/api/v1/jobs/{{ job.id }}`)
        .then(response => response.json())
        .then(jobData => {
            // Update progress bar
            const progressBar = document.getElementById('job-progress-bar');
            if (progressBar) {
                progressBar.style.width = `${jobData.progress}%`;
                progressBar.setAttribute('aria-valuenow', jobData.progress);
                progressBar.textContent = `${jobData.progress}%`;
            }

            // Stop polling if job is complete
            if (['completed', 'failed', 'cancelled'].includes(jobData.status)) {
                clearInterval(jobUpdateInterval);
                location.reload(); // Reload to show final state
            }
        })
        .catch(error => {
            console.error('Failed to update job status:', error);
        });
}

function cancelJob(jobId) {
    if (confirm('Are you sure you want to cancel this job?')) {
        fetch(`/api/v1/jobs/${jobId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                alert(data.message);
                location.reload();
            }
        })
        .catch(error => {
            console.error('Failed to cancel job:', error);
            alert('Failed to cancel job. Please try again.');
        });
    }
}

// Start polling for job updates
jobUpdateInterval = setInterval(updateJobStatus, 2000);
updateJobStatus();
</script>
{% endblock %}
```

### Responsive CSS and Accessibility Features
**File**: `src/vpsweb/repository/web/static/css/responsive.css`
```css
/* Responsive Design for VPSWeb Repository */

/* Mobile-first approach */
@media (max-width: 576px) {
    /* Adjust navigation for mobile */
    .navbar-brand span {
        display: none;
    }

    .navbar-nav .nav-link {
        font-size: 0.9rem;
    }

    /* Stats bar mobile adjustments */
    .d-flex.gap-4 {
        flex-direction: column;
        gap: 0.5rem !important;
    }

    /* Card adjustments */
    .card-body {
        padding: 1rem;
    }

    .btn-group-vertical {
        display: flex;
        flex-direction: row;
        gap: 0.25rem;
    }

    .btn-group-vertical .btn {
        flex: 1;
    }

    /* Poem text adjustments */
    .poem-text {
        font-size: 0.9rem;
        padding: 0.75rem;
    }

    /* Comparison view mobile */
    .translation-card .card-body {
        padding: 0.75rem;
    }

    /* Job status mobile */
    .progress {
        height: 15px;
    }
}

@media (max-width: 768px) {
    /* Hide sidebar on mobile */
    .sidebar {
        display: none !important;
    }

    /* Adjust main content area */
    main {
        margin-left: 0 !important;
        padding: 1rem;
    }

    /* Dashboard cards mobile */
    .card.border-left-primary,
    .card.border-left-success,
    .card.border-left-info,
    .card.border-left-warning {
        border-left: none !important;
        border-top: 4px solid;
    }

    /* Table responsive */
    .table-responsive {
        font-size: 0.875rem;
    }

    /* Form adjustments */
    .row.g-3 {
        gap: 0.5rem;
    }

    .col-md-4,
    .col-md-2,
    .col-md-6 {
        margin-bottom: 0.5rem;
    }
}

@media (min-width: 768px) {
    /* Desktop improvements */
    .poem-text {
        font-size: 1.2em;
    }

    .translation-card {
        min-height: 400px;
    }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
    .card {
        border: 2px solid #000;
    }

    .btn {
        border: 2px solid currentColor;
    }

    .poem-text {
        border: 2px solid #000;
    }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
    .translation-card,
    .hover-shadow,
    .btn,
    .card {
        transition: none !important;
    }

    .spinner-border {
        animation: none;
        border: 4px solid #000;
        border-radius: 50%;
    }
}

/* Print styles */
@media print {
    .navbar,
    .sidebar,
    .btn,
    .modal,
    .toast,
    .breadcrumb {
        display: none !important;
    }

    main {
        margin: 0 !important;
        padding: 0 !important;
    }

    .card {
        border: 1px solid #000;
        page-break-inside: avoid;
        margin-bottom: 1rem;
    }

    .poem-text {
        background: #fff !important;
        border: 1px solid #000;
    }
}

/* Focus indicators for keyboard navigation */
.btn:focus,
.form-control:focus,
.form-select:focus,
.nav-link:focus {
    outline: 3px solid #0066cc;
    outline-offset: 2px;
}

/* Screen reader only content */
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}

/* Skip links for accessibility */
.visually-hidden-focusable:focus {
    position: static;
    width: auto;
    height: auto;
    padding: 0.5rem 1rem;
    margin: 1rem;
    background: #0066cc;
    color: #fff;
    z-index: 1000;
    clip: auto;
    white-space: normal;
}

/* Loading states */
.loading {
    position: relative;
    opacity: 0.6;
    pointer-events: none;
}

.loading::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 20px;
    height: 20px;
    margin: -10px 0 0 -10px;
    border: 2px solid #f3f3f3;
    border-top: 2px solid #0066cc;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Error states */
.error-message {
    background: #f8d7da;
    border: 1px solid #f5c6cb;
    color: #721c24;
    padding: 0.75rem;
    border-radius: 0.375rem;
    margin: 0.5rem 0;
}

.success-message {
    background: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
    padding: 0.75rem;
    border-radius: 0.375rem;
    margin: 0.5rem 0;
}
```

## 🔧 Configuration Management

### Configuration Structure

#### Configuration File: `repository_root/config.yaml`
```yaml
# VPSWeb Repository Configuration
repository:
  root_path: "./repository_root"
  database_url: "sqlite+aiosqlite:///repository_root/repo.db"
  auto_create_dirs: true

# Security Configuration
security:
  password_hash: null  # Set via CLI: vpsweb repo set-password
  session_timeout: 3600  # 1 hour
  api_key_required: false  # For local API access

# vpsweb Integration Settings
vpsweb:
  models_config: "config/models.yaml"
  default_workflow_mode: "hybrid"
  timeout_seconds: 300
  max_concurrent_jobs: 3
  retry_attempts: 2

# Server Configuration
server:
  host: "127.0.0.1"
  port: 8000
  reload: false  # Enable for development
  debug: false

# Logging Configuration
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  file: "logs/repository.log"
  max_size: "10MB"
  backup_count: 5
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Backup Configuration
backup:
  auto_enabled: false
  retention_days: 30
  backup_dir: "backups"
  compression: "gzip"
  include_raw_artifacts: true

# Import/Export Settings
data:
  default_language: "en"
  supported_languages: ["en", "zh-Hans", "zh-Hant"]
  default_license: "CC-BY-4.0"
  max_poem_length: 10000
  max_translation_length: 20000
  # Language mapping for LLM interactions
  language_mapping:
    "en": "English"
    "zh-Hans": "Simplified Chinese"
    "zh-Hant": "Traditional Chinese"
```

#### Configuration Management Implementation
**File**: `src/vpsweb/repository/config.py`
```python
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import hashlib
import getpass
from pydantic import BaseModel, Field

class SecurityConfig(BaseModel):
    password_hash: Optional[str] = None
    session_timeout: int = 3600
    api_key_required: bool = False

class VPSWebConfig(BaseModel):
    models_config: str = "config/models.yaml"
    default_workflow_mode: str = "hybrid"
    timeout_seconds: int = 300
    max_concurrent_jobs: int = 3
    retry_attempts: int = 2

class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    debug: bool = False

class RepositoryConfig(BaseModel):
    root_path: str = "./repository_root"
    database_url: str = "sqlite+aiosqlite:///repository_root/repo.db"
    auto_create_dirs: bool = True

class AppConfig(BaseModel):
    repository: RepositoryConfig
    security: SecurityConfig
    vpsweb: VPSWebConfig
    server: ServerConfig
    logging: Dict[str, Any]
    backup: Dict[str, Any]
    data: Dict[str, Any]

class ConfigManager:
    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path("repository_root/config.yaml")
        self._config: Optional[AppConfig] = None

    def load_config(self) -> AppConfig:
        """Load configuration from file"""
        if not self.config_path.exists():
            self._create_default_config()

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        self._config = AppConfig(**config_data)
        return self._config

    def _create_default_config(self):
        """Create default configuration file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        default_config = {
            "repository": {
                "root_path": "./repository_root",
                "database_url": "sqlite+aiosqlite:///repository_root/repo.db",
                "auto_create_dirs": True
            },
            "security": {
                "password_hash": None,
                "session_timeout": 3600,
                "api_key_required": False
            },
            "vpsweb": {
                "models_config": "config/models.yaml",
                "default_workflow_mode": "hybrid",
                "timeout_seconds": 300,
                "max_concurrent_jobs": 3,
                "retry_attempts": 2
            },
            "server": {
                "host": "127.0.0.1",
                "port": 8000,
                "reload": False,
                "debug": False
            },
            "logging": {
                "level": "INFO",
                "file": "logs/repository.log",
                "max_size": "10MB",
                "backup_count": 5,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "backup": {
                "auto_enabled": False,
                "retention_days": 30,
                "backup_dir": "backups",
                "compression": "gzip",
                "include_raw_artifacts": True
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

    def save_config(self, config: AppConfig):
        """Save configuration to file"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config.dict(), f, default_flow_style=False, allow_unicode=True)
        self._config = config

    def set_password(self, password: str) -> str:
        """Set and hash password using secure Argon2"""
        from passlib.context import CryptContext

        # Initialize password context with Argon2
        pwd_context = CryptContext(
            schemes=["argon2"],
            deprecated="auto",
            argon2__memory_cost=65536,
            argon2__time_cost=3,
            argon2__parallelism=4
        )

        # Hash password using Argon2 (industry standard)
        password_hash = pwd_context.hash(password)

        config = self.load_config()
        config.security.password_hash = password_hash
        self.save_config(config)

        return password_hash

    def verify_password(self, password: str) -> bool:
        """Verify password against secure hash"""
        from passlib.context import CryptContext

        if not hasattr(self, '_pwd_context'):
            self._pwd_context = CryptContext(
                schemes=["argon2"],
                deprecated="auto",
                argon2__memory_cost=65536,
                argon2__time_cost=3,
                argon2__parallelism=4
            )

        config = self.load_config()
        if not config.security.password_hash:
            return False

        try:
            return self._pwd_context.verify(password, config.security.password_hash)
        except:
            return False
```

### Security Implementation

#### Password Protection Middleware
**File**: `src/vpsweb/repository/security.py`
```python
from fastapi import HTTPException, Depends, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import secrets
import time

from .config import ConfigManager

security = HTTPBasic()
config_manager = ConfigManager()

class SecurityManager:
    def __init__(self):
        self.active_sessions = {}  # Simple session store

    async def authenticate_request(
        self,
        request: Request,
        credentials: Optional[HTTPBasicCredentials] = Depends(security)
    ):
        """Authenticate HTTP Basic Auth request"""
        config = config_manager.load_config()

        # Skip auth if no password set
        if not config.security.password_hash:
            return True

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Basic"},
            )

        if not config_manager.verify_password(credentials.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )

        return True

    def create_session(self) -> str:
        """Create a new session"""
        session_id = secrets.token_urlsafe(32)
        self.active_sessions[session_id] = {
            "created_at": time.time(),
            "last_accessed": time.time()
        }
        return session_id

    def validate_session(self, session_id: str) -> bool:
        """Validate session"""
        if session_id not in self.active_sessions:
            return False

        config = config_manager.load_config()
        session = self.active_sessions[session_id]

        # Check timeout
        if time.time() - session["last_accessed"] > config.security.session_timeout:
            del self.active_sessions[session_id]
            return False

        # Update last accessed
        session["last_accessed"] = time.time()
        return True

    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        config = config_manager.load_config()
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, session in self.active_sessions.items()
            if current_time - session["last_accessed"] > config.security.session_timeout
        ]

        for session_id in expired_sessions:
            del self.active_sessions[session_id]

security_manager = SecurityManager()
```

## 🔧 Error Handling Architecture

### Custom Exception Hierarchy
**File**: `src/vpsweb/repository/exceptions.py`
```python
from fastapi import HTTPException
from typing import Optional, Any, Dict
from datetime import datetime

class VPSWebRepositoryException(Exception):
    """Base exception for repository system"""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()
        super().__init__(message)

class DatabaseException(VPSWebRepositoryException):
    """Database-related exceptions"""
    pass

class ValidationError(VPSWebRepositoryException):
    """Data validation exceptions"""
    pass

class TranslationException(VPSWebRepositoryException):
    """Translation workflow exceptions"""
    pass

class JobException(VPSWebRepositoryException):
    """Background job exceptions"""
    pass

class ConfigurationException(VPSWebRepositoryException):
    """Configuration-related exceptions"""
    pass

class FileStorageException(VPSWebRepositoryException):
    """File system storage exceptions"""
    pass

# HTTP Exception Factory
def create_http_exception(
    status_code: int,
    detail: str,
    error_code: str = None,
    headers: Optional[Dict[str, str]] = None
) -> HTTPException:
    """Create standardized HTTP exception"""
    return HTTPException(
        status_code=status_code,
        detail={
            "error": detail,
            "error_code": error_code,
            "timestamp": datetime.utcnow().isoformat()
        },
        headers=headers
    )
```

### Global Exception Handler
**File**: `src/vpsweb/repository/error_handlers.py`
```python
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError
import logging
from datetime import datetime
from typing import Union

from .exceptions import VPSWebRepositoryException, DatabaseException, ValidationError

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Centralized error handling and response formatting"""

    @staticmethod
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all unhandled exceptions"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True, extra={
            "url": str(request.url),
            "method": request.method
        })

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": getattr(request.state, "request_id", None)
            }
        )

    @staticmethod
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle request validation errors"""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation failed",
                "error_code": "VALIDATION_ERROR",
                "message": "Invalid request data",
                "details": exc.errors(),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Handle database errors"""
        logger.error(f"Database error: {exc}", exc_info=True)

        if isinstance(exc, IntegrityError):
            error_code = "INTEGRITY_ERROR"
            message = "Database integrity constraint violated"
            status_code = status.HTTP_409_CONFLICT
        else:
            error_code = "DATABASE_ERROR"
            message = "Database operation failed"
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        return JSONResponse(
            status_code=status_code,
            content={
                "error": message,
                "error_code": error_code,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    async def custom_exception_handler(request: Request, exc: VPSWebRepositoryException) -> JSONResponse:
        """Handle custom repository exceptions"""
        logger.warning(f"Repository exception: {exc.message}", exc_info=True, extra={
            "error_code": exc.error_code,
            "details": exc.details
        })

        # Map exception types to HTTP status codes
        status_mapping = {
            DatabaseException: status.HTTP_500_INTERNAL_SERVER_ERROR,
            ValidationError: status.HTTP_400_BAD_REQUEST,
            TranslationException: status.HTTP_503_SERVICE_UNAVAILABLE,
            JobException: status.HTTP_503_SERVICE_UNAVAILABLE,
            ConfigurationException: status.HTTP_500_INTERNAL_SERVER_ERROR,
            FileStorageException: status.HTTP_500_INTERNAL_SERVER_ERROR
        }

        status_code = next(
            (code for exc_type, code in status_mapping.items() if isinstance(exc, exc_type)),
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        return JSONResponse(
            status_code=status_code,
            content={
                "error": exc.message,
                "error_code": exc.error_code or "REPOSITORY_ERROR",
                "details": exc.details,
                "timestamp": exc.timestamp
            }
        )

# Request ID Middleware
async def request_id_middleware(request: Request, call_next):
    """Add unique request ID to all requests"""
    import uuid
    request.state.request_id = str(uuid.uuid4())

    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response
```

### Error Handling Integration
**File**: `src/vpsweb/repository/main.py` (updated)
```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from .error_handlers import ErrorHandler, request_id_middleware
from .exceptions import VPSWebRepositoryException

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await DatabaseConfig().create_tables()
    yield
    # Shutdown

app = FastAPI(
    title="VPSWeb Repository",
    description="Central repository for poetry translations",
    version="0.1.0",
    lifespan=lifespan
)

# Add middleware
app.middleware("http")(request_id_middleware)

# Add exception handlers
app.add_exception_handler(Exception, ErrorHandler.global_exception_handler)
app.add_exception_handler(RequestValidationError, ErrorHandler.validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, ErrorHandler.sqlalchemy_exception_handler)
app.add_exception_handler(VPSWebRepositoryException, ErrorHandler.custom_exception_handler)

# Existing router includes...
```

### Error Response Standards
**Standard Error Response Format**:
```json
{
  "error": "Human-readable error message",
  "error_code": "SYSTEMATIC_ERROR_CODE",
  "message": "More detailed explanation",
  "details": {
    "field": "specific error details"
  },
  "timestamp": "2025-10-17T10:30:00Z",
  "request_id": "uuid-for-tracking"
}
```

**HTTP Status Code Mappings**:
- `400`: Validation errors, bad input
- `401`: Authentication required
- `403`: Permission denied
- `404`: Resource not found
- `409`: Integrity constraint violation
- `422`: Request validation failed
- `500`: Internal server error
- `503`: Service temporarily unavailable (translation/job failures)

### Logging and Monitoring Integration
**File**: `src/vpsweb/repository/monitoring.py`
```python
import logging
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Structured logging configuration
def setup_logging(config):
    """Configure structured logging with correlation IDs"""
    logging.basicConfig(
        level=getattr(logging, config.logging["level"]),
        format=config.logging["format"],
        handlers=[
            logging.FileHandler(config.logging["file"]),
            logging.StreamHandler()
        ]
    )

# Request logging middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "unknown")

        logger.info(f"Request started", extra={
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "user_agent": request.headers.get("user-agent")
        })

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            logger.info(f"Request completed", extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2)
            })

            return response

        except Exception as exc:
            duration = time.time() - start_time

            logger.error(f"Request failed", extra={
                "request_id": request_id,
                "error": str(exc),
                "duration_ms": round(duration * 1000, 2)
            }, exc_info=True)

            raise

# Error alerting (for production)
class ErrorAlertManager:
    """Handle error alerting and notifications"""

    @staticmethod
    async def alert_critical_error(error: Exception, context: Dict[str, Any]):
        """Send alerts for critical errors"""
        if isinstance(error, DatabaseException):
            await ErrorAlertManager._send_database_alert(error, context)
        elif isinstance(error, TranslationException):
            await ErrorAlertManager._send_translation_alert(error, context)

    @staticmethod
    async def _send_database_alert(error: Exception, context: Dict[str, Any]):
        """Send database-related alerts"""
        logger.critical(f"Database error alert: {error}", extra={
            "error_type": type(error).__name__,
            "context": context,
            "alert_level": "critical"
        })

    @staticmethod
    async def _send_translation_alert(error: Exception, context: Dict[str, Any]):
        """Send translation-related alerts"""
        logger.error(f"Translation error alert: {error}", extra={
            "error_type": type(error).__name__,
            "context": context,
            "alert_level": "warning"
        })
```

## 📋 Testing Strategy

### Unit Tests

#### Database Model Tests
**File**: `tests/test_models.py`
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.vpsweb.repository.models import Poem, Translation, AILog
from src.vpsweb.repository.database import get_session

@pytest.mark.asyncio
async def test_create_poem():
    """Test poem creation"""
    async with get_session() as session:
        poem = Poem(
            poet_name="陶渊明",
            poem_title="歸園田居·其一",
            source_language="zh-Hans",
            original_text="少無適俗韻，性本愛丘山。",
            form="五言古詩",
            period="東晉"
        )
        session.add(poem)
        await session.commit()
        await session.refresh(poem)

        assert poem.id is not None
        assert poem.poet_name == "陶渊明"
        assert poem.source_language == "zh-Hans"

@pytest.mark.asyncio
async def test_create_translation():
    """Test translation creation with relationships"""
    async with get_session() as session:
        # Create poem first
        poem = Poem(
            poet_name="陶渊明",
            poem_title="歸園田居·其一",
            source_language="zh-Hans",
            original_text="少無適俗韻，性本愛丘山。"
        )
        session.add(poem)
        await session.commit()

        # Create translation
        translation = Translation(
            poem_id=poem.id,
            translator_type="ai",
            translator_info="vpsweb (hybrid)",
            target_language="en",
            translated_text="Young, I never fit the common mold, My heart loved hills and mountains since birth.",
            license="CC-BY-4.0"
        )
        session.add(translation)
        await session.commit()
        await session.refresh(translation)

        assert translation.id is not None
        assert translation.poem_id == poem.id
        assert translation.translator_type == "ai"

@pytest.mark.asyncio
async def test_cascade_delete():
    """Test cascade delete behavior"""
    async with get_session() as session:
        # Create poem with translation
        poem = Poem(
            poet_name="Test Poet",
            poem_title="Test Poem",
            source_language="en",
            original_text="Test content"
        )
        session.add(poem)
        await session.commit()

        translation = Translation(
            poem_id=poem.id,
            translator_type="human",
            target_language="zh-Hans",
            translated_text="测试内容"
        )
        session.add(translation)
        await session.commit()

        poem_id = poem.id
        translation_id = translation.id

        # Delete poem (should cascade delete translation)
        await session.delete(poem)
        await session.commit()

        # Verify translation is also deleted
        deleted_translation = await session.get(Translation, translation_id)
        assert deleted_translation is None
```

#### API Endpoint Tests
**File**: `tests/test_api.py`
```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.vpsweb.repository.main import app
from src.vpsweb.repository.database import get_session
from src.vpsweb.repository.models import Poem

client = TestClient(app)

@pytest.mark.asyncio
async def test_create_poem_api():
    """Test poem creation API"""
    poem_data = {
        "poet_name": "陶渊明",
        "poem_title": "歸園田居·其一",
        "source_language": "zh-Hans",
        "original_text": "少無適俗韻，性本愛丘山。誤落塵網中，一去三十年。",
        "form": "五言古詩",
        "period": "東晉"
    }

    response = client.post("/api/v1/poems/", json=poem_data)
    assert response.status_code == 200

    data = response.json()
    assert data["poet_name"] == "陶渊明"
    assert data["poem_title"] == "歸園田居·其一"
    assert "id" in data
    assert data["translation_count"] == 0

@pytest.mark.asyncio
async def test_list_poems_api():
    """Test poems listing API"""
    # Create test poems
    async with get_session() as session:
        poems = [
            Poem(poet_name="陶渊明", poem_title="歸園田居", source_language="zh-Hans", original_text="Text 1"),
            Poem(poet_name="李白", poem_title="靜夜思", source_language="zh-Hans", original_text="Text 2")
        ]
        for poem in poems:
            session.add(poem)
        await session.commit()

    # Test listing
    response = client.get("/api/v1/poems/")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2

@pytest.mark.asyncio
async def test_search_poems_api():
    """Test poem search API"""
    # Create test poem
    async with get_session() as session:
        poem = Poem(
            poet_name="陶渊明",
            poem_title="歸園田居·其一",
            source_language="zh-Hans",
            original_text="少無適俗韻，性本愛丘山。"
        )
        session.add(poem)
        await session.commit()

    # Test search by poet
    response = client.get("/api/v1/poems/?poet=陶渊明")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["poet_name"] == "陶渊明"

    # Test search by text
    response = client.get("/api/v1/poems/?search=丘山")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
```

#### Integration Tests
**File**: `tests/test_integration.py`
```python
import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from src.vpsweb.repository.database import get_session
from src.vpsweb.repository.models import Poem
from src.vpsweb.repository.integration.vpsweb_adapter import VPSWebAdapter

@pytest.mark.asyncio
async def test_vpsweb_integration():
    """Test vpsweb workflow integration"""
    # Create test poem
    async with get_session() as session:
        poem = Poem(
            poet_name="Test Poet",
            poem_title="Test Poem",
            source_language="en",
            original_text="The mountains rise like ancient sentinels."
        )
        session.add(poem)
        await session.commit()

    # Test adapter (mock implementation for testing)
    adapter = VPSWebAdapter()

    # Mock the workflow execution for testing
    class MockTranslationResult:
        def __init__(self):
            self.translated_text = "群山如古代哨兵般矗立。"
            self.model_name = "test-model"
            self.workflow_mode = "hybrid"
            self.prompt_tokens = 50
            self.completion_tokens = 30
            self.total_tokens = 80
            self.runtime_seconds = 2.5

    # Mock the workflow.execute method
    original_execute = adapter.workflow.execute
    adapter.workflow.execute = lambda **kwargs: MockTranslationResult()

    try:
        result = await adapter.translate_poem(poem, "zh-Hans", "hybrid")

        assert result["success"] is True
        assert "translation" in result
        assert "ai_log" in result
        assert result["translation"]["translated_text"] == "群山如古代哨兵般矗立。"
        assert result["translation"]["target_language"] == "zh-Hans"

    finally:
        # Restore original method
        adapter.workflow.execute = original_execute

@pytest.mark.asyncio
async def test_background_job_workflow():
    """Test background job processing"""
    from src.vpsweb.repository.api.jobs import run_translation_job, job_store
    from src.vpsweb.repository.models import Poem

    # Create test poem
    async with get_session() as session:
        poem = Poem(
            poet_name="Test Poet",
            poem_title="Test Poem",
            source_language="en",
            original_text="Test content for background processing."
        )
        session.add(poem)
        await session.commit()

    # Create job
    job_id = "test-job-123"
    job_store[job_id] = {
        "id": job_id,
        "status": "pending",
        "progress": 0,
        "error": None
    }

    # Mock the adapter
    class MockAdapter:
        async def translate_poem(self, poem, target_lang, mode):
            return {
                "success": True,
                "translation": {
                    "id": "test-translation-id",
                    "poem_id": poem.id,
                    "translator_type": "ai",
                    "target_language": target_lang,
                    "translated_text": "模拟翻译内容",
                    "created_at": "2025-10-17T10:00:00"
                },
                "ai_log": {
                    "id": "test-ai-log-id",
                    "translation_id": "test-translation-id",
                    "model_name": "test-model",
                    "workflow_mode": mode,
                    "created_at": "2025-10-17T10:00:00"
                }
            }

    # Replace adapter temporarily
    from src.vpsweb.repository.api.jobs import VPSWebAdapter
    original_adapter = VPSWebAdapter
    VPSWebAdapter = MockAdapter

    try:
        # Run job
        await run_translation_job(job_id, poem, "zh-Hans", "hybrid")

        # Verify job completed
        assert job_store[job_id]["status"] == "completed"
        assert job_store[job_id]["progress"] == 100
        assert "translation_id" in job_store[job_id]

    finally:
        # Restore original adapter
        VPSWebAdapter = original_adapter
        # Clean up job
        if job_id in job_store:
            del job_store[job_id]
```

### End-to-End Tests

#### Web UI Tests
**File**: `tests/test_e2e.py`
```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.vpsweb.repository.main import app
from src.vpsweb.repository.database import get_session
from src.vpsweb.repository.models import Poem

client = TestClient(app)

@pytest.mark.asyncio
async def test_web_ui_poem_workflow():
    """Test complete poem creation and viewing workflow in web UI"""

    # Test dashboard loads
    response = client.get("/")
    assert response.status_code == 200
    assert "Dashboard" in response.text

    # Test poem list page
    response = client.get("/poems")
    assert response.status_code == 200

    # Test new poem form page
    response = client.get("/poems/new")
    assert response.status_code == 200
    assert "New Poem" in response.text

    # Submit poem form
    poem_data = {
        "poet_name": "陶渊明",
        "poem_title": "歸園田居·其一",
        "source_language": "zh-Hans",
        "original_text": "少無適俗韻，性本愛丘山。誤落塵網中，一去三十年。",
        "form": "五言古詩",
        "period": "東晉"
    }

    response = client.post("/poems/new", data=poem_data, follow_redirects=False)
    assert response.status_code == 303  # Redirect after creation

    # Extract poem ID from redirect location
    redirect_location = response.headers["location"]
    poem_id = redirect_location.split("/")[-1]

    # Test poem detail page
    response = client.get(f"/poems/{poem_id}")
    assert response.status_code == 200
    assert "陶渊明" in response.text
    assert "歸園田居·其一" in response.text

@pytest.mark.asyncio
async def test_api_json_workflow():
    """Test complete API workflow"""

    # Create poem via API
    poem_data = {
        "poet_name": "李白",
        "poem_title": "靜夜思",
        "source_language": "zh-Hans",
        "original_text": "床前明月光，疑是地上霜。舉頭望明月，低頭思故鄉。"
    }

    response = client.post("/api/v1/poems/", json=poem_data)
    assert response.status_code == 200
    poem = response.json()
    poem_id = poem["id"]

    # Get poem via API
    response = client.get(f"/api/v1/poems/{poem_id}")
    assert response.status_code == 200
    retrieved_poem = response.json()
    assert retrieved_poem["poet_name"] == "李白"

    # Update poem via API
    update_data = {
        "period": "唐代"
    }
    response = client.put(f"/api/v1/poems/{poem_id}", json=update_data)
    assert response.status_code == 200

    # Verify update
    response = client.get(f"/api/v1/poems/{poem_id}")
    assert response.status_code == 200
    updated_poem = response.json()
    assert updated_poem["period"] == "唐代"

    # Delete poem via API
    response = client.delete(f"/api/v1/poems/{poem_id}")
    assert response.status_code == 200

    # Verify deletion
    response = client.get(f"/api/v1/poems/{poem_id}")
    assert response.status_code == 404
```

## 🚨 Risk Assessment

### High Risk Items

#### 1. Database Corruption Risk
**Risk**: SQLite database corruption during concurrent access
**Impact**: Data loss, system unavailable
**Mitigation**:
- Use WAL mode for SQLite
- Implement proper connection pooling
- Regular backup automation
- Database integrity checks

#### 2. vpsweb Integration Failures
**Risk**: vpsweb workflow execution failures or API changes
**Impact**: Translation functionality unavailable
**Mitigation**:
- Comprehensive error handling in adapter
- Fallback mechanisms for failed translations
- Version compatibility checks
- Mock implementation for testing

#### 3. Background Job Management
**Risk**: Job queue overflow or orphaned jobs
**Impact**: Resource exhaustion, incomplete translations
**Mitigation**:
- Job timeout mechanisms
- Job cleanup processes
- Resource usage monitoring
- Max concurrent job limits

### Medium Risk Items

#### 1. Security Vulnerabilities
**Risk**: Weak authentication or session management
**Impact**: Unauthorized access to data
**Mitigation**:
- Strong password hashing
- Session timeout enforcement
- Input validation and sanitization
- HTTPS for remote access

#### 2. Performance Bottlenecks
**Risk**: Slow database queries or file I/O operations
**Impact**: Poor user experience
**Mitigation**:
- Database query optimization
- Async/await patterns throughout
- Connection pooling
- Response time monitoring

#### 3. File System Permissions
**Risk**: Inadequate permissions for repository directories
**Impact**: System startup failures or data loss
**Mitigation**:
- Directory creation verification
- Permission checks on startup
- Graceful error handling
- Clear user documentation

### Low Risk Items

#### 1. Configuration Management
**Risk**: Invalid configuration values
**Impact**: System behavior issues
**Mitigation**:
- Configuration validation
- Default value fallbacks
- Clear error messages
- Configuration documentation

#### 2. Template Rendering Issues
**Risk**: Jinja2 template errors
**Impact**: Web UI failures
**Mitigation**:
- Template syntax validation
- Error handling in views
- Fallback error pages
- Template testing

## 📅 Implementation Timeline

### Week 1: Foundation (Days 1-7)

#### Day 1-2: Project Setup and Database Models
- **Priority**: High
- **Tasks**:
  - Create repository module structure
  - Implement SQLAlchemy models
  - Set up database configuration
  - Create Pydantic schemas
- **Deliverables**: Working database layer with basic models

#### Day 3-4: Core API Implementation
- **Priority**: High
- **Tasks**:
  - Implement FastAPI application setup
  - Create poem CRUD endpoints
  - Add database dependency injection
  - Basic error handling
- **Deliverables**: Functional REST API for poems

#### Day 5-6: Translation Management
- **Priority**: High
- **Tasks**:
  - Implement translation CRUD endpoints
  - Add translation relationships
  - Create human translation forms
  - Basic validation logic
- **Deliverables**: Complete translation management API

#### Day 7: Basic Web UI
- **Priority**: Medium
- **Tasks**:
  - Set up Jinja2 templates
  - Create basic HTML templates
  - Implement poem listing and detail views
  - Add basic CSS styling
- **Deliverables**: Functional web interface

### Week 2: Integration and Advanced Features (Days 8-14)

#### Day 8-9: vpsweb Integration
- **Priority**: High
- **Tasks**:
  - Implement VPSWebAdapter class
  - Create workflow integration logic
  - Add error handling and logging
  - Test with actual vpsweb workflows
- **Deliverables**: Working AI translation integration

#### Day 10-11: Background Job System
- **Priority**: High
- **Tasks**:
  - Implement job management API
  - Add background task processing
  - Create job status tracking
  - Add job cancellation support
- **Deliverables**: Asynchronous translation processing

#### Day 12: Security and Configuration
- **Priority**: Medium
- **Tasks**:
  - Implement password protection
  - Add configuration management
  - Create session management
  - Add security middleware
- **Deliverables**: Secure system with configuration

#### Day 13: Import/Export Functionality
- **Priority**: Medium
- **Tasks**:
  - Implement bulk import from vpsweb outputs
  - Add export functionality
  - Create data validation logic
  - Add progress tracking
- **Deliverables**: Data migration capabilities

#### Day 14: Testing and Polish
- **Priority**: High
- **Tasks**:
  - Run comprehensive tests
  - Fix bugs and performance issues
  - Add documentation
  - Prepare for release
- **Deliverables**: Production-ready system

### Post-Implementation: Enhancement Phase

#### Version 0.3.0: Advanced Features
- Real-time job updates with WebSockets
- Full-text search with SQLite FTS5
- Advanced comparison tools
- Multi-language UI support

#### Version 0.4.0: Production Features
- Backup automation
- Performance monitoring
- Advanced user management
- API rate limiting

## 📊 Success Metrics

### Functional Metrics
- [x] Database schema creation and migration
- [x] Poem CRUD operations via API and UI
- [x] Translation management with versioning
- [x] AI translation integration
- [x] Background job processing
- [x] Web interface responsiveness
- [x] Security implementation
- [x] Configuration management
- [x] Import/export functionality
- [x] Comprehensive test coverage

### Performance Metrics
- **API Response Time**: < 200ms for 95% of requests
- **Database Query Time**: < 50ms for standard operations
- **Page Load Time**: < 1s for web UI pages
- **Background Job Throughput**: 3+ concurrent jobs
- **Memory Usage**: < 512MB for typical usage

### User Experience Metrics
- **Task Completion Rate**: > 95% for common workflows
- **Error Rate**: < 1% for normal operations
- **Learning Curve**: < 30 minutes for basic operations
- **Documentation Coverage**: 100% for public APIs

### Technical Metrics
- **Code Coverage**: > 90% for critical components
- **Type Coverage**: > 95% for Python code
- **Security Score**: No critical vulnerabilities
- **Performance Score**: Grade A+ on web performance tests

---

## 📚 References

### Technical Documentation
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **SQLAlchemy Async Documentation**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **ULID Specification**: https://github.com/ulid/spec
- **BCP 47 Language Tags**: https://tools.ietf.org/html/bcp47

### VPSWeb Integration
- **VPSWeb Core Workflow**: `src/vpsweb/core/workflow.py`
- **VPSWeb Configuration**: `config/models.yaml`
- **Translation Models**: `src/vpsweb/models/translation.py`

### Related Projects
- **SQLAdmin**: FastAPI admin interface for SQLAlchemy models
- **Pydantic**: Data validation using Python type annotations
- **Jinja2**: Modern and designer-friendly templating language

---

**Document Status**: Draft v0.1 - Ready for Implementation Review
## 🔧 Database Schema with Optimized Models and Constraints

### SQLAlchemy Models with Complete Constraints

```python
# src/vpsweb/repository/models.py
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON
from ulid import ULID
import json
from datetime import datetime
from typing import Optional

Base = declarative_base()

class Poem(Base):
    __tablename__ = 'poems'

    # Primary and unique constraints
    id = Column(String, primary_key=True, default=lambda: str(ULID()))
    poet_name = Column(String, nullable=False)
    poem_title = Column(String, nullable=False)
    source_language = Column(String, nullable=False)
    original_text = Column(Text, nullable=False)

    # Optional classification fields
    form = Column(String)
    period = Column(String)

    # Timestamp fields
    created_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat())

    # Constraints
    __table_args__ = (
        CheckConstraint("length(poet_name) > 0", name="ck_poems_poet_name_not_empty"),
        CheckConstraint("length(poem_title) > 0", name="ck_poems_poem_title_not_empty"),
        CheckConstraint("length(original_text) > 0", name="ck_poems_original_text_not_empty"),
        CheckConstraint("source_language IN ('en', 'zh-Hans', 'zh-Hant')", name="ck_poems_source_language_valid"),
        UniqueConstraint('poet_name', 'poem_title', 'source_language', name='uq_poems_poem_title_lang'),
        # Performance indexes
        Index('idx_poems_poet_name', 'poet_name'),
        Index('idx_poems_source_language', 'source_language'),
        Index('idx_poems_created_at', 'created_at'),
        Index('idx_poems_poet_title', 'poem_title'),
    )

    # Relationships
    translations = relationship("Translation", back_populates="poem", cascade="all, delete-orphan")

class Translation(Base):
    __tablename__ = 'translations'

    # Primary and foreign key constraints
    id = Column(String, primary_key=True, default=lambda: str(ULID()))
    poem_id = Column(String, ForeignKey('poems.id', ondelete='CASCADE'), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)

    # Translator information
    translator_type = Column(String, nullable=False)  # 'ai' or 'human'
    translator_info = Column(String)
    target_language = Column(String, nullable=False)
    translated_text = Column(Text, nullable=False)

    # License and provenance
    license = Column(String, default='CC-BY-4.0')
    raw_path = Column(String)

    # Timestamp
    created_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat())

    # Constraints
    __table_args__ = (
        CheckConstraint("translator_type IN ('ai', 'human')", name="ck_translations_translator_type"),
        CheckConstraint("length(translated_text) > 0", name="ck_translations_text_not_empty"),
        CheckConstraint("target_language IN ('en', 'zh-Hans', 'zh-Hant')", name="ck_translations_target_language_valid"),
        CheckConstraint("version > 0", name="ck_translations_version_positive"),
        UniqueConstraint('poem_id', 'version', 'translator_type', name='uq_translations_poem_version_type'),
        # Performance indexes
        Index('idx_translations_poem_id', 'poem_id'),
        Index('idx_translations_type', 'translator_type'),
        Index('idx_translations_target', 'target_language'),
        Index('idx_translations_created', 'created_at'),
    )

    # Relationships
    poem = relationship("Poem", back_populates="translations")
    ai_logs = relationship("AILog", back_populates="translation", cascade="all, delete-orphan")
    human_notes = relationship("HumanNote", back_populates="translation", cascade="all, delete-orphan")

class AILog(Base):
    __tablename__ = 'ai_logs'

    # Primary and foreign key constraints
    id = Column(String, primary_key=True, default=lambda: str(ULID()))
    translation_id = Column(String, ForeignKey('translations.id', ondelete='CASCADE'), nullable=False, index=True)

    # AI execution details
    model_name = Column(String)
    workflow_mode = Column(String)
    token_usage_json = Column(JSON)  # SQLite JSON support
    cost_info_json = Column(JSON)    # SQLite JSON support
    runtime_seconds = Column(Float)
    notes = Column(Text)

    # Timestamp
    created_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat())

    # Constraints
    __table_args__ = (
        CheckConstraint("runtime_seconds >= 0", name="ck_ai_logs_runtime_non_negative"),
        Index('idx_ai_logs_translation_id', 'translation_id'),
        Index('idx_ai_logs_model', 'model_name'),
    )

    # Relationships
    translation = relationship("Translation", back_populates="ai_logs")

class HumanNote(Base):
    __tablename__ = 'human_notes'

    # Primary and foreign key constraints
    id = Column(String, primary_key=True, default=lambda: str(ULID()))
    translation_id = Column(String, ForeignKey('translations.id', ondelete='CASCADE'), nullable=False, index=True)
    note_text = Column(Text, nullable=False)
    created_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat())

    # Constraints
    __table_args__ = (
        CheckConstraint("length(note_text) > 0", name="ck_human_notes_text_not_empty"),
        Index('idx_human_notes_translation_id', 'translation_id'),
    )

    # Relationships
    translation = relationship("Translation", back_populates="human_notes")

class Job(Base):
    __tablename__ = 'jobs'

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(ULID()))
    job_type = Column(String, nullable=False)  # 'ai_translation', 'import', 'export'

    # Job status and progress
    status = Column(String, nullable=False, default='pending')  # pending, running, completed, failed
    progress = Column(Integer, default=0)
    current_step = Column(String)
    total_steps = Column(Integer)

    # Job parameters and results
    parameters_json = Column(JSON)
    result_json = Column(JSON)
    error_message = Column(Text)

    # Timing information
    created_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat())
    started_at = Column(String)
    completed_at = Column(String)

    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'running', 'completed', 'failed', 'cancelled')", name="ck_jobs_status_valid"),
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_jobs_progress_range"),
        CheckConstraint("job_type IN ('ai_translation', 'import', 'export')", name="ck_jobs_type_valid"),
        CheckConstraint("total_steps > 0", name="ck_jobs_total_steps_positive"),
        Index('idx_jobs_status', 'status'),
        Index('idx_jobs_type', 'job_type'),
        Index('idx_jobs_created', 'created_at'),
    )
```

### Template Helper Fix: Custom Jinja2 Filters

```python
# src/vpsweb/repository/web/template_helpers.py
import os
from jinja2 import Environment
from datetime import datetime

def setup_template_filters(env: Environment):
    """Register custom Jinja2 filters"""

    @env.filter('basename')
    def basename_filter(path):
        """Extract basename from file path - fixes missing template helper"""
        if not path:
            return ""
        return os.path.basename(path)

    @env.filter('strftime')
    def strftime_filter(date_str, format_str='%Y-%m-%d %H:%M'):
        """Format datetime string for display"""
        if not date_str:
            return ""
        try:
            if isinstance(date_str, str):
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                dt = date_str
            return dt.strftime(format_str)
        except (ValueError, AttributeError):
            return str(date_str)

    @env.filter('truncate_words')
    def truncate_words_filter(text, length=50, suffix='...'):
        """Truncate text to specified word count"""
        if not text:
            return ""
        words = text.split()
        if len(words) <= length:
            return text
        return ' '.join(words[:length]) + suffix

    @env.filter('language_name')
    def language_name_filter(code):
        """Convert BCP 47 language code to display name"""
        language_map = {
            'en': 'English',
            'zh-Hans': 'Simplified Chinese',
            'zh-Hant': 'Traditional Chinese'
        }
        return language_map.get(code, code)

    @env.filter('file_size')
    def file_size_filter(size_bytes):
        """Format file size in human readable format"""
        if not size_bytes:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

# src/vpsweb/repository/web/routes.py
from fastapi import Request
from fastapi.templating import Jinja2Templates
from .template_helpers import setup_template_filters

def create_templates():
    """Create Jinja2Templates with custom filters"""
    templates = Jinja2Templates(directory="src/vpsweb/repository/web/templates")

    # Register custom filters
    setup_template_filters(templates.env)

    return templates

templates = create_templates()

@router.get("/")
async def dashboard(request: Request):
    """Dashboard page with proper template helper support"""
    # ... dashboard logic ...
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "stats": stats, "recent_activity": recent_activity}
    )
```

### Database Migration Strategy with Alembic

```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from src.vpsweb.repository.models import Base
from src.vpsweb.repository.config import settings

# this is the Alembic Config object
config = context.config

# Set the database URL
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """Run migrations in 'online' mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

# alembic/versions/001_initial_schema.py
"""Initial schema with constraints and indexes

Revision ID: 001
Revises:
Create Date: 2025-10-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create poems table
    op.create_table('poems',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('poet_name', sa.String(), nullable=False),
        sa.Column('poem_title', sa.String(), nullable=False),
        sa.Column('source_language', sa.String(), nullable=False),
        sa.Column('original_text', sa.Text(), nullable=False),
        sa.Column('form', sa.String(), nullable=True),
        sa.Column('period', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('updated_at', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('length(poet_name) > 0', name='ck_poems_poet_name_not_empty'),
        sa.CheckConstraint('length(poem_title) > 0', name='ck_poems_poem_title_not_empty'),
        sa.CheckConstraint('length(original_text) > 0', name='ck_poems_original_text_not_empty'),
        sa.CheckConstraint("source_language IN ('en', 'zh-Hans', 'zh-Hant')", name='ck_poems_source_language_valid'),
        sa.UniqueConstraint('poet_name', 'poem_title', 'source_language', name='uq_poems_poem_title_lang')
    )

    # Create indexes for poems
    op.create_index('idx_poems_poet_name', 'poems', ['poet_name'])
    op.create_index('idx_poems_source_language', 'poems', ['source_language'])
    op.create_index('idx_poems_created_at', 'poems', ['created_at'])
    op.create_index('idx_poems_poet_title', 'poems', ['poem_title'])

    # Create translations table
    op.create_table('translations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('poem_id', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('translator_type', sa.String(), nullable=False),
        sa.Column('translator_info', sa.String(), nullable=True),
        sa.Column('target_language', sa.String(), nullable=False),
        sa.Column('translated_text', sa.Text(), nullable=False),
        sa.Column('license', sa.String(), nullable=True),
        sa.Column('raw_path', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['poem_id'], ['poems.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("translator_type IN ('ai', 'human')", name='ck_translations_translator_type'),
        sa.CheckConstraint('length(translated_text) > 0', name='ck_translations_text_not_empty'),
        sa.CheckConstraint("target_language IN ('en', 'zh-Hans', 'zh-Hant')", name='ck_translations_target_language_valid'),
        sa.CheckConstraint('version > 0', name='ck_translations_version_positive'),
        sa.UniqueConstraint('poem_id', 'version', 'translator_type', name='uq_translations_poem_version_type')
    )

    # Create indexes for translations
    op.create_index('idx_translations_poem_id', 'translations', ['poem_id'])
    op.create_index('idx_translations_type', 'translations', ['translator_type'])
    op.create_index('idx_translations_target', 'translations', ['target_language'])
    op.create_index('idx_translations_created', 'translations', ['created_at'])

    # Create ai_logs table
    op.create_table('ai_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('translation_id', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=True),
        sa.Column('workflow_mode', sa.String(), nullable=True),
        sa.Column('token_usage_json', sa.JSON(), nullable=True),
        sa.Column('cost_info_json', sa.JSON(), nullable=True),
        sa.Column('runtime_seconds', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['translation_id'], ['translations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('runtime_seconds >= 0', name='ck_ai_logs_runtime_non_negative')
    )

    # Create indexes for ai_logs
    op.create_index('idx_ai_logs_translation_id', 'ai_logs', ['translation_id'])
    op.create_index('idx_ai_logs_model', 'ai_logs', ['model_name'])

    # Create human_notes table
    op.create_table('human_notes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('translation_id', sa.String(), nullable=False),
        sa.Column('note_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['translation_id'], ['translations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('length(note_text) > 0', name='ck_human_notes_text_not_empty')
    )

    # Create indexes for human_notes
    op.create_index('idx_human_notes_translation_id', 'human_notes', ['translation_id'])

    # Create jobs table
    op.create_table('jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('job_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('current_step', sa.String(), nullable=True),
        sa.Column('total_steps', sa.Integer(), nullable=True),
        sa.Column('parameters_json', sa.JSON(), nullable=True),
        sa.Column('result_json', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('started_at', sa.String(), nullable=True),
        sa.Column('completed_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('pending', 'running', 'completed', 'failed', 'cancelled')", name='ck_jobs_status_valid'),
        sa.CheckConstraint('progress >= 0 AND progress <= 100', name='ck_jobs_progress_range'),
        sa.CheckConstraint("job_type IN ('ai_translation', 'import', 'export')", name='ck_jobs_type_valid'),
        sa.CheckConstraint('total_steps > 0', name='ck_jobs_total_steps_positive')
    )

    # Create indexes for jobs
    op.create_index('idx_jobs_status', 'jobs', ['status'])
    op.create_index('idx_jobs_type', 'jobs', ['job_type'])
    op.create_index('idx_jobs_created', 'jobs', ['created_at'])

def downgrade() -> None:
    op.drop_table('jobs')
    op.drop_table('human_notes')
    op.drop_table('ai_logs')
    op.drop_table('translations')
    op.drop_table('poems')
```

## 🔄 Background Job Management with ARQ

### Replacing Custom Job System with Industry Standard Solution

**Architectural Decision**: The custom SQLite-based job system has been replaced with **ARQ (Asynchronous Redis Queue)** to eliminate hundreds of lines of high-maintenance code and leverage a proven, battle-tested background task system.

### ARQ Configuration and Setup

```python
# src/vpsweb/repository/jobs/arq_config.py
from arq import create_pool, cron
from arq.connections import RedisSettings
from arq import Worker
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class JobResult:
    """Standard job execution result"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = None

class VPSWebJobManager:
    """ARQ-based job management system"""

    def __init__(self, redis_settings: Optional[RedisSettings] = None):
        self.redis_settings = redis_settings or RedisSettings(
            host=localhost,
            port=6379,
            database=0,
            password=None
        )
        self.pool = None

    async def start(self):
        """Initialize Redis connection pool"""
        self.pool = await create_pool(self.redis_settings)
        logger.info("ARQ job manager started")

    async def stop(self):
        """Cleanup resources"""
        if self.pool:
            await self.pool.close()
        logger.info("ARQ job manager stopped")

    async def submit_translation_job(
        self,
        poem_id: str,
        target_language: str,
        workflow_mode: str = "hybrid",
        priority: int = 0
    ) -> str:
        """Submit translation job with priority support"""
        job_data = {
            "poem_id": poem_id,
            "target_language": target_language,
            "workflow_mode": workflow_mode,
            "submitted_at": datetime.utcnow().isoformat()
        }

        job_id = await self.pool.enqueue_job(
            "execute_translation",
            job_data,
            priority=priority
        )

        logger.info(f"Translation job {job_id} submitted for poem {poem_id}")
        return job_id

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get real-time job status"""
        try:
            job_info = await self.pool.get(f"arq:job:{job_id}")
            return json.loads(job_info) if job_info else None
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return None

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel pending job"""
        try:
            success = await self.pool.delete(f"arq:job:{job_id}")
            return success > 0
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

# ARQ Worker Functions
async def execute_translation(ctx, job_data: Dict[str, Any]) -> JobResult:
    """ARQ worker function for translation jobs"""
    start_time = datetime.utcnow()

    try:
        poem_id = job_data["poem_id"]
        target_language = job_data["target_language"]
        workflow_mode = job_data["workflow_mode"]

        from ..integration.vpsweb_adapter import VPSWebAdapter
        from ..database import get_session
        from ..models import Poem

        adapter = VPSWebAdapter()

        async with get_session() as session:
            poem = await session.get(Poem, poem_id)
            if not poem:
                raise ValueError(f"Poem {poem_id} not found")

            result = await adapter.translate_poem(poem, target_language, workflow_mode)

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return JobResult(
                success=True,
                result=result,
                execution_time=execution_time,
                metadata={"poem_id": poem_id, "target_language": target_language}
            )

    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        logger.error(f"Translation job failed: {e}")

        return JobResult(
            success=False,
            error=str(e),
            execution_time=execution_time,
            metadata=job_data
        )

# ARQ Worker Configuration
class WorkerSettings:
    """Production-ready ARQ worker settings"""

    redis_settings = RedisSettings()
    functions = [execute_translation]

    # Performance and reliability settings
    max_jobs = 3  # Configurable concurrency
    job_timeout = 300  # 5 minutes
    queue_read_limit = 100

    # Retry logic
    retry_jobs = True
    max_retries = 2
    retry_delay = 30

# Global job manager instance
job_manager = VPSWebJobManager()
```

### FastAPI Integration

```python
# src/vpsweb/repository/api/jobs.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from ..database import get_session
from ..jobs.arq_config import job_manager

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

@router.post("/submit-translation")
async def submit_translation_job(
    poem_id: str,
    target_language: str,
    workflow_mode: str = "hybrid",
    priority: int = 0,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, str]:
    """Submit translation job to ARQ queue"""

    # Verify poem exists
    from ..models import Poem
    poem = await session.get(Poem, poem_id)
    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")

    # Submit to ARQ
    job_id = await job_manager.submit_translation_job(
        poem_id, target_language, workflow_mode, priority
    )

    return {"job_id": job_id, "status": "submitted"}

@router.get("/{job_id}/status")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get real-time job status"""
    status = await job_manager.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")

    return status

@router.delete("/{job_id}")
async def cancel_job(job_id: str) -> Dict[str, str]:
    """Cancel pending job"""
    success = await job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")

    return {"job_id": job_id, "status": "cancelled"}
```

### Application Startup Integration

```python
# src/vpsweb/repository/main.py
from fastapi import FastAPI
from .jobs.arq_config import job_manager, start_job_manager, stop_job_manager

app = FastAPI(title="VPSWeb Repository")

@app.on_event("startup")
async def startup_event():
    """Initialize ARQ job manager on startup"""
    await start_job_manager()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup ARQ job manager on shutdown"""
    await stop_job_manager()

# Include job API routes
from .api.jobs import router as jobs_router
app.include_router(jobs_router)
```

### Deployment Configuration

```yaml
# docker-compose.yml
version: '3.8'
services:
  vpsweb-repository:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  vpsweb-worker:
    build: .
    command: python -m arq src.vpsweb.repository.jobs.arq_config.WorkerSettings
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0
    scale: 2  # Multiple worker processes

volumes:
  redis_data:
```

### Benefits of ARQ Approach

1. **Reliability**: Proven, battle-tested job queue system
2. **Performance**: Redis-based with built-in connection pooling
3. **Scalability**: Easy horizontal scaling with multiple workers
4. **Monitoring**: Built-in job tracking and retry mechanisms
5. **Maintenance**: Eliminates hundreds of lines of custom code
6. **Extensibility**: Easy to add new job types and functions

### Installation Requirements

```bash
# Add to pyproject.toml or requirements.txt
arq = "^0.25.0"
redis = "^4.5.0"
passlib = "^1.7.4"  # For Argon2 password hashing
argon2-cffi = "^21.3.0"  # Argon2 backend
```

## 🔧 Configuration Management: Eliminating Redundancy

### Single Source of Truth for Language Mapping

**Architectural Fix**: Removed redundant `language_mapping` from configuration and established `LanguageMapper` as the authoritative source.

```python
# src/vpsweb/repository/utils/language_mapper.py
from typing import Dict

class LanguageMapper:
    """Single source of truth for BCP 47 to natural language mapping"""

    _MAPPING = {
        # BCP 47 codes to natural language names (for LLM interaction)
        'en': 'English',
        'zh-Hans': 'Simplified Chinese',
        'zh-Hant': 'Traditional Chinese'
    }

    _REVERSE_MAPPING = {v: k for k, v in _MAPPING.items()}

    @classmethod
    def get_natural_language_name(cls, bcp47_code: str) -> str:
        """Convert BCP 47 code to natural language name"""
        return cls._MAPPING.get(bcp47_code, bcp47_code)

    @classmethod
    def get_bcp47_code(cls, natural_language: str) -> str:
        """Convert natural language name to BCP 47 code"""
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

### Updated Configuration (Removed Redundancy)

```yaml
# repository_root/config.yaml (Updated - No language_mapping)
repository:
  root_path: "./repository_root"
  database_url: "sqlite+aiosqlite:///repository_root/repo.db"
  auto_create_dirs: true

security:
  password_hash: null  # Set via API
  session_timeout: 3600
  api_key_required: false

vpsweb:
  models_config: "config/models.yaml"
  default_workflow_mode: "hybrid"
  timeout_seconds: 300
  max_concurrent_jobs: 3
  retry_attempts: 2

server:
  host: "127.0.0.1"
  port: 8000
  reload: false
  debug: false

# Note: language_mapping removed - use LanguageMapper class instead
data:
  default_language: "en"
  supported_languages: ["en", "zh-Hans", "zh-Hant"]  # BCP 47 codes only
  default_license: "CC-BY-4.0"
  max_poem_length: 10000
  max_translation_length: 20000
```

### Database Model Constraints Verification

**Fix**: Added comprehensive `CheckConstraint` definitions to SQLAlchemy models to match database schema:

```python
# src/vpsweb/repository/models.py (Constraint Updates)
from sqlalchemy import Column, String, Text, Integer, Float, ForeignKey, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base

class Poem(Base):
    __tablename__ = 'poems'

    # ... columns ...

    # Complete constraint definitions
    __table_args__ = (
        CheckConstraint("length(poet_name) > 0", name="ck_poems_poet_name_not_empty"),
        CheckConstraint("length(poem_title) > 0", name="ck_poems_poem_title_not_empty"),
        CheckConstraint("length(original_text) > 0", name="ck_poems_original_text_not_empty"),
        CheckConstraint("source_language IN ('en', 'zh-Hans', 'zh-Hant')", name="ck_poems_source_language_valid"),
        UniqueConstraint('poet_name', 'poem_title', 'source_language', name='uq_poems_poem_title_lang'),
        # Performance indexes
        Index('idx_poems_poet_name', 'poet_name'),
        Index('idx_poems_source_language', 'source_language'),
        Index('idx_poems_created_at', 'created_at'),
        Index('idx_poems_poet_title', 'poem_title'),
    )

class Translation(Base):
    __tablename__ = 'translations'

    # ... columns ...

    # Complete constraint definitions
    __table_args__ = (
        CheckConstraint("translator_type IN ('ai', 'human')", name="ck_translations_translator_type"),
        CheckConstraint("length(translated_text) > 0", name="ck_translations_text_not_empty"),
        CheckConstraint("target_language IN ('en', 'zh-Hans', 'zh-Hant')", name="ck_translations_target_language_valid"),
        CheckConstraint("version > 0", name="ck_translations_version_positive"),
        UniqueConstraint('poem_id', 'version', 'translator_type', name='uq_translations_poem_version_type'),
        # Performance indexes
        Index('idx_translations_poem_id', 'poem_id'),
        Index('idx_translations_type', 'translator_type'),
        Index('idx_translations_target', 'target_language'),
        Index('idx_translations_created', 'created_at'),
    )
```

### FastAPI Dependency Injection for Job Manager

**Fix**: Replaced global instances with proper FastAPI dependency injection:

```python
# src/vpsweb/repository/dependencies.py
from fastapi import Depends
from .jobs.arq_config import VPSWebJobManager

# Dependency injection instead of global instances
async def get_job_manager() -> VPSWebJobManager:
    """FastAPI dependency for job manager"""
    # Initialize if not already done
    if not hasattr(get_job_manager, "_instance"):
        get_job_manager._instance = VPSWebJobManager()
        await get_job_manager._instance.start()
    return get_job_manager._instance

# Updated API routes use dependencies
@router.post("/submit-translation")
async def submit_translation_job(
    poem_id: str,
    target_language: str,
    job_manager: VPSWebJobManager = Depends(get_job_manager),  # Proper DI
    session: AsyncSession = Depends(get_session)
):
    # Use injected dependency instead of global
    job_id = await job_manager.submit_translation_job(poem_id, target_language)
    return {"job_id": job_id}
```

## 🔧 API Optimization: Fixing N+1 Query Problem

### Optimized Poem Listing with Single Query

```python
# src/vpsweb/repository/api/poems.py (Optimized Version)
from sqlalchemy import select, func, outerjoin
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

@router.get("/", response_model=List[PoemResponse])
async def list_poems(
    poet: Optional[str] = Query(None, description="Filter by poet name"),
    source_language: Optional[str] = Query(None, description="Filter by source language"),
    search: Optional[str] = Query(None, description="Search in poet name, title, or text"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    session: AsyncSession = Depends(get_session)
):
    """Get list of poems with translation counts (optimized single query)"""

    # Build base query with translation count subquery
    count_subquery = (
        select(
            Translation.poem_id,
            func.count(Translation.id).label("translation_count")
        )
        .group_by(Translation.poem_id)
        .subquery()
    )

    # Main query with LEFT JOIN to get counts in single roundtrip
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

    # Count total results (optimized)
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await session.scalar(count_query)

    # Apply pagination and execute
    query = query.offset(skip).limit(limit).order_by(Poem.created_at.desc())
    result = await session.execute(query)

    # Build response with translation counts
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

### Query Performance Analysis

**Before (N+1 Problem)**:
- 1 query for poems list
- N queries for translation counts (N = number of poems)
- **Total**: 51 queries for 50 poems

**After (Optimized)**:
- 1 query with LEFT JOIN subquery
- **Total**: 1 query for any number of poems

**Performance Improvement**: 50x reduction in database roundtrips

## 📋 Architectural Specification Summary

### PSD Structure and Implementation Guidance

**Architectural Clarification**: This PSD serves as both a technical specification and implementation guide. For production development, the following specification format should be used as the primary contract, with detailed implementations moved to separate documentation.

### API Contracts Specification

#### Core REST API Endpoints

```yaml
# OpenAPI 3.0 Specification Summary
openapi: 3.0.0
info:
  title: VPSWeb Repository API
  version: 1.0.0

paths:
  /api/v1/poems:
    get:
      summary: List poems with filtering and pagination
      parameters:
        - name: poet
          in: query
          schema:
            type: string
        - name: source_language
          in: query
          schema:
            type: string
            enum: [en, zh-Hans, zh-Hant]
        - name: search
          in: query
          schema:
            type: string
        - name: skip
          in: query
          schema:
            type: integer
            minimum: 0
        - name: limit
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
      responses:
        200:
          description: List of poems with translation counts
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/PoemResponse'

    post:
      summary: Create new poem
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PoemCreate'
      responses:
        200:
          description: Poem created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PoemResponse'

  /api/v1/poems/{poem_id}:
    get:
      summary: Get specific poem
      parameters:
        - name: poem_id
          in: path
          required: true
          schema:
            type: string
      responses:
        200:
          description: Poem details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PoemResponse'
        404:
          description: Poem not found

  /api/v1/jobs/submit-translation:
    post:
      summary: Submit translation job
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                poem_id:
                  type: string
                target_language:
                  type: string
                  enum: [en, zh-Hans, zh-Hant]
                workflow_mode:
                  type: string
                  enum: [reasoning, non_reasoning, hybrid]
                  default: hybrid
                priority:
                  type: integer
                  minimum: 0
                  maximum: 10
                  default: 0
              required: [poem_id, target_language]
      responses:
        200:
          description: Job submitted successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id:
                    type: string
                  status:
                    type: string
                    enum: [submitted]

components:
  schemas:
    PoemResponse:
      type: object
      properties:
        id:
          type: string
        poet_name:
          type: string
        poem_title:
          type: string
        source_language:
          type: string
          enum: [en, zh-Hans, zh-Hant]
        original_text:
          type: string
        form:
          type: string
        period:
          type: string
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
        translation_count:
          type: integer
          minimum: 0

    PoemCreate:
      type: object
      properties:
        poet_name:
          type: string
          minLength: 1
        poem_title:
          type: string
          minLength: 1
        source_language:
          type: string
          enum: [en, zh-Hans, zh-Hant]
        original_text:
          type: string
          minLength: 1
        form:
          type: string
        period:
          type: string
      required: [poet_name, poem_title, source_language, original_text]
```

### Database Schema Contract

#### Core Tables Structure

```sql
-- Primary Tables Specification
CREATE TABLE poems (
    id TEXT PRIMARY KEY,                    -- ULID identifier
    poet_name TEXT NOT NULL,                -- Poet name (non-empty)
    poem_title TEXT NOT NULL,               -- Poem title (non-empty)
    source_language TEXT NOT NULL,          -- BCP 47 language code
    original_text TEXT NOT NULL,            -- Full poem text (non-empty)
    form TEXT,                             -- Poetic form (optional)
    period TEXT,                           -- Historical period (optional)
    created_at TEXT NOT NULL,              -- ISO timestamp
    updated_at TEXT NOT NULL,              -- ISO timestamp

    -- Constraints
    CONSTRAINT ck_poems_source_language_valid
        CHECK (source_language IN ('en', 'zh-Hans', 'zh-Hant')),
    CONSTRAINT uq_poems_poem_title_lang
        UNIQUE (poet_name, poem_title, source_language)
);

CREATE TABLE translations (
    id TEXT PRIMARY KEY,                    -- ULID identifier
    poem_id TEXT NOT NULL,                  -- Foreign key to poems
    version INTEGER NOT NULL,               -- Translation version
    translator_type TEXT NOT NULL,          -- 'ai' or 'human'
    translator_info TEXT,                   -- Translator identifier
    target_language TEXT NOT NULL,          -- BCP 47 language code
    translated_text TEXT NOT NULL,          -- Translation result
    license TEXT DEFAULT 'CC-BY-4.0',      -- License type
    raw_path TEXT,                         -- Raw artifacts path
    created_at TEXT NOT NULL,              -- ISO timestamp

    -- Constraints
    CONSTRAINT fk_translations_poem
        FOREIGN KEY (poem_id) REFERENCES poems(id) ON DELETE CASCADE,
    CONSTRAINT ck_translations_translator_type
        CHECK (translator_type IN ('ai', 'human')),
    CONSTRAINT ck_translations_target_language_valid
        CHECK (target_language IN ('en', 'zh-Hans', 'zh-Hant')),
    CONSTRAINT ck_translations_version_positive
        CHECK (version > 0),
    CONSTRAINT uq_translations_poem_version_type
        UNIQUE (poem_id, version, translator_type)
);
```

### System Architecture Contracts

#### Component Integration Points

```yaml
# System Integration Specification
components:
  web_api:
    type: FastAPI application
    interfaces:
      - HTTP REST API (port 8000)
      - Static file serving
      - WebSocket (future enhancement)
    dependencies:
      - database (SQLite/PostgreSQL)
      - job_queue (ARQ + Redis)
      - vpsweb_core (translation engine)

  job_queue:
    type: ARQ + Redis
    configuration:
      max_concurrent_jobs: 3
      job_timeout: 300s
      retry_attempts: 2
    job_types:
      - translation: Execute vpsweb translation workflow
      - import: Bulk data import
      - export: Data export operations

  database:
    type: SQLAlchemy ORM
    engines:
      - SQLite (development/local)
      - PostgreSQL (production option)
    migrations: Alembic
    constraints: Full data integrity with indexes

  vpsweb_integration:
    type: Python library integration
    interface: TranslationWorkflow class
    configuration:
      models_config: config/models.yaml
      workflow_modes: [reasoning, non_reasoning, hybrid]
```

### Implementation Guidance vs. Specification

**Recommended Development Approach**:

1. **Use this PSD as**: Complete implementation guide with detailed code examples
2. **Extract from this PSD**: API contracts, database schema, and architectural decisions
3. **Create separate documentation**:
   - `API_CONTRACT.md` - OpenAPI specifications
   - `DATABASE_SCHEMA.md` - Complete database design
   - `DEPLOYMENT_GUIDE.md` - Production deployment instructions
4. **Reference implementation**: Keep detailed code in appendix or separate repository

**Benefits of This Approach**:
- ✅ **Clear Contracts**: API and database specifications remain stable
- ✅ **Implementation Flexibility**: Developers can optimize implementation patterns
- ✅ **Maintainable Documentation**: Specifications don't become outdated
- ✅ **Complete Guidance**: Full implementation details available when needed

---

**Next Steps**: Technical implementation review and development kickoff
**Approvals Required**: Development Team Lead, Technical Architect

---

*This PSD provides comprehensive technical implementation details for the VPSWeb Central Repository and Web UI system, with specific focus on FastAPI, SQLAlchemy, vpsweb integration, web interface development, complete database constraints, proper template helper implementation, industry-standard background job management, optimized database queries, and proper architectural specification format.*