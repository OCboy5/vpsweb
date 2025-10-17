# Project Specification Document: VPSWeb Poetry Repository & Web Interface

**Project Name**: VPSWeb Poetry Repository  
**Version**: 1.0.0  
**Date**: January 2025  
**Author**: VPSWeb Team  
**Status**: Development Ready

---

## Executive Summary

Extend the existing VPSWeb poetry translation system with a centralized repository and web interface to enable classification, storage, search, and access to hundreds/thousands of translated poems. The system will provide a web UI for the TET (Translator-Editor-Translator) workflow and comprehensive repository management.

### Key Objectives
1. Create a SQLite-based repository for storing poems and translations
2. Build a FastAPI-based REST API for repository access
3. Develop a web UI for browsing, searching, and translating poems
4. Implement quality evaluation and rating system
5. Deploy as a low-traffic niche website

### Technology Stack
- **Backend**: FastAPI (Python 3.9+)
- **Database**: SQLite with FTS5 (full-text search)
- **Frontend**: HTMX + Alpine.js + Tailwind CSS
- **Existing Core**: VPSWeb TET workflow (vpsweb.core.workflow)
- **Deployment**: Single server (Railway/Render recommended)

---

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                       Web Browser                            │
│  (HTMX + Alpine.js for interactivity)                       │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ HTTP/WebSocket
                 │
┌────────────────▼────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Routes     │  │   Business   │  │   Auth &     │     │
│  │   (REST)     │  │   Logic      │  │   Middleware │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────┬──────────────────┬──────────────────┬────────────┘
          │                  │                  │
          │                  │                  │
┌─────────▼──────────┐ ┌────▼────────────┐ ┌──▼──────────────┐
│  Repository Layer  │ │  VPSWeb Core    │ │  External APIs  │
│  (Database ops)    │ │  (TET workflow) │ │  (LLM services) │
└─────────┬──────────┘ └─────────────────┘ └─────────────────┘
          │
┌─────────▼──────────────────────────────────────────────────┐
│              SQLite Database + File System                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  repository  │  │    poems/    │  │ translations/│     │
│  │     .db      │  │  (originals) │  │  (outputs)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
vpsweb/
├── src/vpsweb/
│   ├── core/                      # Existing TET workflow
│   │   ├── workflow.py
│   │   └── executor.py
│   │
│   ├── repository/                # NEW: Repository layer
│   │   ├── __init__.py
│   │   ├── core.py               # PoemRepository class
│   │   ├── models.py             # Data models
│   │   ├── schema.sql            # Database schema
│   │   └── search.py             # Full-text search logic
│   │
│   ├── web/                       # NEW: Web application
│   │   ├── __init__.py
│   │   ├── app.py                # FastAPI application
│   │   ├── api/                  # API routes
│   │   │   ├── __init__.py
│   │   │   ├── poems.py          # Poem endpoints
│   │   │   ├── translations.py   # Translation endpoints
│   │   │   ├── search.py         # Search endpoints
│   │   │   └── workflow.py       # TET workflow endpoints
│   │   │
│   │   ├── templates/            # HTML templates (Jinja2)
│   │   │   ├── base.html
│   │   │   ├── home.html
│   │   │   ├── browse.html
│   │   │   ├── poem_detail.html
│   │   │   ├── translation_detail.html
│   │   │   ├── translate.html
│   │   │   └── search.html
│   │   │
│   │   └── static/               # Static assets
│   │       ├── css/
│   │       │   └── styles.css
│   │       ├── js/
│   │       │   └── app.js        # Alpine.js components
│   │       └── images/
│   │
│   ├── models/                    # Existing models
│   ├── services/                  # Existing services
│   └── utils/                     # Existing utilities
│
├── data/                          # NEW: Data directory
│   ├── repository.db             # SQLite database
│   ├── poems/                    # Original source files
│   │   ├── english/
│   │   │   ├── shakespeare/
│   │   │   └── frost/
│   │   ├── chinese/
│   │   │   ├── tang_dynasty/
│   │   │   └── modern/
│   │   └── metadata/             # Rich metadata files
│   │
│   └── translations/             # Translation outputs
│       ├── by_date/              # Organized by date
│       │   └── 2025/01/
│       └── by_poem/              # Organized by poem
│           └── sonnet_18/
│
├── scripts/                       # NEW: Utility scripts
│   ├── init_database.py          # Initialize database
│   ├── import_existing.py        # Import existing translations
│   └── backup.py                 # Backup script
│
├── tests/
│   ├── unit/
│   │   └── test_repository.py    # NEW: Repository tests
│   └── integration/
│       └── test_web_api.py       # NEW: API tests
│
├── config/
│   └── repository_config.yaml    # NEW: Repository configuration
│
├── pyproject.toml                # Updated dependencies
└── README.md                     # Updated documentation
```

---

## Phase 1: Repository Core (Priority: HIGH)

### 1.1 Database Schema

**File**: `src/vpsweb/repository/schema.sql`

**Requirements**:
- Create SQLite database with the following tables:
  - `poems`: Store original source poems
  - `translations`: Store TET workflow results
  - `translators`: Optional human translator tracking
  - `collections`: Curated poem groupings
  - `collection_poems`: Many-to-many relationship
  - `tags`: Flexible categorization
  - `poem_tags`: Many-to-many relationship
  
- Implement FTS5 (Full-Text Search) tables:
  - `poems_fts`: Search in original poems
  - `translations_fts`: Search in translations
  
- Create triggers to keep FTS tables synchronized
- Create indexes for common queries
- Create views for convenient data access

**Schema Details**:

```sql
-- Core tables
CREATE TABLE poems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT,
    source_language TEXT NOT NULL,
    original_text TEXT NOT NULL,
    era TEXT,
    style TEXT,
    themes TEXT,  -- JSON array
    cultural_context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_file_path TEXT,
    metadata_json TEXT,  -- JSON for flexible metadata
    UNIQUE(title, author, source_language)
);

CREATE TABLE translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poem_id INTEGER NOT NULL,
    target_language TEXT NOT NULL,
    workflow_mode TEXT NOT NULL,  -- 'reasoning', 'non_reasoning', 'hybrid'
    
    -- TET workflow results
    initial_translation TEXT NOT NULL,
    initial_translator_notes TEXT,
    editor_review TEXT NOT NULL,
    editor_suggestions TEXT,
    revised_translation TEXT NOT NULL,
    revision_explanation TEXT,
    
    -- Metrics
    total_tokens INTEGER,
    total_duration_seconds REAL,
    total_cost_rmb REAL,
    step_metrics TEXT,  -- JSON
    
    -- Quality tracking
    human_rating INTEGER,  -- 1-5
    quality_notes TEXT,
    flagged_for_review BOOLEAN DEFAULT 0,
    
    -- Technical
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    translator_id INTEGER,
    output_file_path TEXT,
    
    FOREIGN KEY (poem_id) REFERENCES poems(id) ON DELETE CASCADE,
    FOREIGN KEY (translator_id) REFERENCES translators(id)
);

-- Additional tables: translators, collections, tags (see full schema above)
```

**Indexes**:
```sql
CREATE INDEX idx_poems_language ON poems(source_language);
CREATE INDEX idx_poems_author ON poems(author);
CREATE INDEX idx_translations_poem ON translations(poem_id);
CREATE INDEX idx_translations_target_lang ON translations(target_language);
CREATE INDEX idx_translations_workflow ON translations(workflow_mode);
CREATE INDEX idx_translations_rating ON translations(human_rating);
```

**Views**:
```sql
CREATE VIEW poems_with_stats AS
SELECT 
    p.*,
    COUNT(DISTINCT t.id) as translation_count,
    COUNT(DISTINCT t.target_language) as target_language_count,
    AVG(t.human_rating) as avg_rating
FROM poems p
LEFT JOIN translations t ON p.id = t.poem_id
GROUP BY p.id;
```

### 1.2 Repository Core Class

**File**: `src/vpsweb/repository/core.py`

**Class**: `PoemRepository`

**Requirements**:
- Implement CRUD operations for poems and translations
- Handle SQLite connection management (context managers)
- Automatic FTS index updates
- Transaction support
- Error handling and logging

**Key Methods**:

```python
class PoemRepository:
    def __init__(self, db_path: str = "data/repository.db"):
        """Initialize repository with database path"""
        
    # Poem operations
    def add_poem(self, title: str, author: str, source_language: str, 
                 original_text: str, **kwargs) -> int:
        """Add a new poem, return poem_id"""
        
    def get_poem(self, poem_id: int) -> Optional[Poem]:
        """Get poem by ID"""
        
    def find_poem(self, title: str, author: str, 
                  source_language: str) -> Optional[Poem]:
        """Find existing poem by unique constraint"""
        
    def find_or_create_poem(self, title: str, author: str, 
                           source_language: str, original_text: str, 
                           **kwargs) -> int:
        """Find existing or create new poem, return poem_id"""
        
    def list_poems(self, filters: Dict[str, Any] = None, 
                   limit: int = 50, offset: int = 0) -> List[Poem]:
        """List poems with optional filters"""
        
    def update_poem(self, poem_id: int, **kwargs) -> bool:
        """Update poem metadata"""
        
    # Translation operations
    def add_translation(self, poem_id: int, target_language: str,
                       workflow_mode: str, initial_translation: str,
                       editor_review: str, revised_translation: str,
                       **kwargs) -> int:
        """Add translation result, return translation_id"""
        
    def get_translation(self, translation_id: int) -> Optional[Translation]:
        """Get translation by ID"""
        
    def list_translations(self, poem_id: int = None, 
                         filters: Dict[str, Any] = None) -> List[Translation]:
        """List translations with optional filters"""
        
    def update_translation_rating(self, translation_id: int, 
                                 rating: int, notes: str = None) -> bool:
        """Update quality rating"""
        
    # Search operations
    def search(self, query: str, search_type: str = "all",
               languages: List[str] = None, limit: int = 50) -> List[Dict]:
        """Full-text search across poems and translations"""
        
    def search_poems(self, query: str, languages: List[str] = None) -> List[Poem]:
        """Search in original poems"""
        
    def search_translations(self, query: str, 
                           target_languages: List[str] = None) -> List[Translation]:
        """Search in translations"""
        
    # Statistics
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        
    # Utility
    def backup(self, backup_path: str) -> bool:
        """Create database backup"""
```

### 1.3 Data Models

**File**: `src/vpsweb/repository/models.py`

**Requirements**:
- Define Pydantic models for API validation
- Define dataclasses for internal use
- Include serialization/deserialization methods
- Type hints for all fields

**Models**:

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class PoemBase(BaseModel):
    """Base poem model"""
    title: str = Field(..., min_length=1, max_length=500)
    author: Optional[str] = Field(None, max_length=200)
    source_language: str = Field(..., min_length=2, max_length=50)
    original_text: str = Field(..., min_length=1)
    era: Optional[str] = None
    style: Optional[str] = None
    themes: Optional[List[str]] = None
    cultural_context: Optional[str] = None

class PoemCreate(PoemBase):
    """Model for creating poems"""
    source_file_path: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

class PoemResponse(PoemBase):
    """Model for poem responses"""
    id: int
    created_at: datetime
    updated_at: datetime
    translation_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

class TranslationBase(BaseModel):
    """Base translation model"""
    target_language: str = Field(..., min_length=2, max_length=50)
    workflow_mode: str = Field(..., pattern="^(reasoning|non_reasoning|hybrid)$")
    
    initial_translation: str = Field(..., min_length=1)
    initial_translator_notes: Optional[str] = None
    editor_review: str = Field(..., min_length=1)
    editor_suggestions: Optional[str] = None
    revised_translation: str = Field(..., min_length=1)
    revision_explanation: Optional[str] = None
    
    total_tokens: Optional[int] = None
    total_duration_seconds: Optional[float] = None
    total_cost_rmb: Optional[float] = None
    step_metrics: Optional[Dict[str, Any]] = None

class TranslationCreate(TranslationBase):
    """Model for creating translations"""
    poem_id: int
    output_file_path: Optional[str] = None

class TranslationResponse(TranslationBase):
    """Model for translation responses"""
    id: int
    poem_id: int
    created_at: datetime
    human_rating: Optional[int] = Field(None, ge=1, le=5)
    quality_notes: Optional[str] = None
    flagged_for_review: bool = False
    
    class Config:
        from_attributes = True

class TranslationRating(BaseModel):
    """Model for rating translations"""
    rating: int = Field(..., ge=1, le=5)
    quality_notes: Optional[str] = None

class SearchQuery(BaseModel):
    """Model for search requests"""
    query: str = Field(..., min_length=1)
    search_type: str = Field("all", pattern="^(all|poems|translations)$")
    languages: Optional[List[str]] = None
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)

class SearchResult(BaseModel):
    """Model for search results"""
    type: str  # 'poem' or 'translation'
    id: int
    title: str
    snippet: str
    relevance_score: float
    poem_id: Optional[int] = None  # For translation results
```

### 1.4 Integration with Existing VPSWeb

**File**: `src/vpsweb/cli/__init__.py` (extend existing)

**Requirements**:
- Add `--store` flag to CLI translate command
- Automatically store results in repository when flag is set
- Extract poem metadata from input file
- Generate appropriate title if not provided

**Modified CLI**:

```python
@click.command()
@click.option('--input', '-i', required=True, help='Input poem file')
@click.option('--source', '-s', required=True, help='Source language')
@click.option('--target', '-t', required=True, help='Target language')
@click.option('--workflow', '-w', default='hybrid', help='Workflow mode')
@click.option('--store', is_flag=True, help='Store in repository')
@click.option('--title', help='Poem title (auto-detect if not provided)')
@click.option('--author', help='Poem author')
@click.option('--verbose', '-v', is_flag=True)
def translate(input, source, target, workflow, store, title, author, verbose):
    """Translate a poem using TET workflow"""
    
    # Existing translation logic
    result = workflow.execute(input_data)
    
    # NEW: Store in repository if --store flag
    if store:
        from vpsweb.repository import PoemRepository
        repo = PoemRepository()
        
        # Auto-detect title if not provided
        if not title:
            title = extract_title_from_text(input_data.original_poem)
        
        # Find or create poem
        poem_id = repo.find_or_create_poem(
            title=title,
            author=author,
            source_language=source,
            original_text=input_data.original_poem
        )
        
        # Store translation
        translation_id = repo.add_translation(
            poem_id=poem_id,
            target_language=target,
            workflow_mode=workflow,
            initial_translation=result.initial_translation.initial_translation,
            initial_translator_notes=result.initial_translation.translator_notes,
            editor_review=result.editor_review.editor_review,
            editor_suggestions=result.editor_review.editor_suggestions,
            revised_translation=result.revised_translation.revised_translation,
            revision_explanation=result.revised_translation.revision_explanation,
            total_tokens=result.total_tokens,
            total_duration_seconds=result.duration_seconds,
            total_cost_rmb=result.total_cost,
            step_metrics=result.get_step_metrics(),
            output_file_path=output_path
        )
        
        click.echo(f"✅ Stored in repository (poem_id={poem_id}, translation_id={translation_id})")
```

### 1.5 Import Script for Existing Translations

**File**: `scripts/import_existing.py`

**Requirements**:
- Scan `outputs/` directory for existing JSON files
- Extract poem and translation data
- Import into repository
- Handle duplicates gracefully
- Provide progress reporting

**Script Structure**:

```python
#!/usr/bin/env python3
"""
Import existing translation outputs into repository
Usage: python scripts/import_existing.py [--outputs-dir outputs/]
"""

import json
import click
from pathlib import Path
from vpsweb.repository import PoemRepository

def extract_poem_info(data: dict, filename: str) -> dict:
    """Extract poem metadata from translation JSON"""
    # Auto-detect title from original_poem (first line or filename)
    # Extract author from filename pattern if available
    # Determine era/style from filename or content
    pass

@click.command()
@click.option('--outputs-dir', default='outputs/', help='Directory with translation outputs')
@click.option('--dry-run', is_flag=True, help='Show what would be imported')
def import_translations(outputs_dir: str, dry_run: bool):
    """Import existing translations into repository"""
    
    repo = PoemRepository()
    output_dir = Path(outputs_dir)
    
    json_files = list(output_dir.glob("**/*.json"))
    click.echo(f"Found {len(json_files)} translation files")
    
    imported = 0
    skipped = 0
    errors = 0
    
    for json_file in json_files:
        try:
            with open(json_file) as f:
                data = json.load(f)
            
            # Extract poem info
            poem_info = extract_poem_info(data, json_file.name)
            
            if dry_run:
                click.echo(f"Would import: {poem_info['title']}")
                continue
            
            # Find or create poem
            poem_id = repo.find_or_create_poem(**poem_info)
            
            # Add translation
            translation_id = repo.add_translation(
                poem_id=poem_id,
                target_language=data['target_lang'],
                workflow_mode=data.get('workflow_mode', 'unknown'),
                initial_translation=data['initial_translation'],
                editor_review=data['editor_review'],
                revised_translation=data['revised_translation'],
                total_tokens=data.get('total_tokens'),
                total_duration_seconds=data.get('duration_seconds'),
                total_cost_rmb=data.get('total_cost'),
                output_file_path=str(json_file)
            )
            
            imported += 1
            click.echo(f"✅ Imported: {poem_info['title']} (translation_id={translation_id})")
            
        except Exception as e:
            errors += 1
            click.echo(f"❌ Error processing {json_file}: {e}")
    
    click.echo(f"\nSummary: {imported} imported, {skipped} skipped, {errors} errors")

if __name__ == '__main__':
    import_translations()
```

---

## Phase 2: Web API (Priority: HIGH)

### 2.1 FastAPI Application Setup

**File**: `src/vpsweb/web/app.py`

**Requirements**:
- Initialize FastAPI application
- Configure CORS for development
- Set up static files and templates
- Configure logging
- Add exception handlers
- Include API routers

**Application Structure**:

```python
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from vpsweb.web.api import poems, translations, search, workflow
from vpsweb.repository import PoemRepository

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="VPSWeb Poetry Repository",
    description="AI-powered poetry translation with TET workflow",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS configuration (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="src/vpsweb/web/static"), name="static")

# Templates
templates = Jinja2Templates(directory="src/vpsweb/web/templates")

# Initialize repository (singleton pattern)
repository = PoemRepository()

# Include API routers
app.include_router(poems.router, prefix="/api/poems", tags=["Poems"])
app.include_router(translations.router, prefix="/api/translations", tags=["Translations"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["Workflow"])

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Root route (home page)
@app.get("/")
async def home(request: Request):
    stats = repository.get_stats()
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "stats": stats}
    )
```

### 2.2 API Endpoints

#### 2.2.1 Poems API

**File**: `src/vpsweb/web/api/poems.py`

**Requirements**:
- List poems with filtering and pagination
- Get poem details with all translations
- Create new poem
- Update poem metadata
- Delete poem (soft delete preferred)

**Endpoints**:

```python
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from vpsweb.repository import PoemRepository
from vpsweb.repository.models import PoemCreate, PoemResponse

router = APIRouter()
repository = PoemRepository()

@router.get("/", response_model=List[PoemResponse])
async def list_poems(
    source_language: Optional[str] = None,
    author: Optional[str] = None,
    era: Optional[str] = None,
    style: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    List all poems with optional filters
    
    Filters:
    - source_language: Filter by source language
    - author: Filter by author name
    - era: Filter by era
    - style: Filter by poetry style
    """
    filters = {
        k: v for k, v in {
            "source_language": source_language,
            "author": author,
            "era": era,
            "style": style
        }.items() if v is not None
    }
    
    poems = repository.list_poems(filters=filters, limit=limit, offset=offset)
    return poems

@router.get("/{poem_id}", response_model=PoemResponse)
async def get_poem(poem_id: int):
    """Get poem by ID with all metadata"""
    poem = repository.get_poem(poem_id)
    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")
    return poem

@router.get("/{poem_id}/translations")
async def get_poem_translations(poem_id: int):
    """Get all translations for a poem"""
    poem = repository.get_poem(poem_id)
    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")
    
    translations = repository.list_translations(poem_id=poem_id)
    return {
        "poem": poem,
        "translations": translations,
        "translation_count": len(translations)
    }

@router.post("/", response_model=PoemResponse, status_code=201)
async def create_poem(poem: PoemCreate):
    """Create a new poem"""
    try:
        poem_id = repository.add_poem(**poem.dict())
        created_poem = repository.get_poem(poem_id)
        return created_poem
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{poem_id}", response_model=PoemResponse)
async def update_poem(poem_id: int, updates: dict):
    """Update poem metadata"""
    success = repository.update_poem(poem_id, **updates)
    if not success:
        raise HTTPException(status_code=404, detail="Poem not found")
    return repository.get_poem(poem_id)

@router.delete("/{poem_id}")
async def delete_poem(poem_id: int):
    """Delete a poem (and all its translations)"""
    # Implement soft delete or hard delete
    # Consider implications for translations
    pass
```

#### 2.2.2 Translations API

**File**: `src/vpsweb/web/api/translations.py`

**Endpoints**:

```python
from fastapi import APIRouter, HTTPException
from vpsweb.repository.models import TranslationResponse, TranslationRating

router = APIRouter()
repository = PoemRepository()

@router.get("/{translation_id}", response_model=TranslationResponse)
async def get_translation(translation_id: int):
    """Get translation by ID"""
    translation = repository.get_translation(translation_id)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    return translation

@router.get("/")
async def list_translations(
    target_language: Optional[str] = None,
    workflow_mode: Optional[str] = None,
    min_rating: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
):
    """List translations with filters"""
    filters = {
        k: v for k, v in {
            "target_language": target_language,
            "workflow_mode": workflow_mode,
            "min_rating": min_rating
        }.items() if v is not None
    }
    
    translations = repository.list_translations(filters=filters, limit=limit, offset=offset)
    return translations

@router.patch("/{translation_id}/rate")
async def rate_translation(translation_id: int, rating_data: TranslationRating):
    """Rate a translation (1-5 stars) with optional notes"""
    success = repository.update_translation_rating(
        translation_id,
        rating_data.rating,
        rating_data.quality_notes
    )
    if not success:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    return repository.get_translation(translation_id)

@router.post("/{translation_id}/flag")
async def flag_for_review(translation_id: int):
    """Flag translation for expert review"""
    # Implementation
    pass
```

#### 2.2.3 Search API

**File**: `src/vpsweb/web/api/search.py`

**Endpoints**:

```python
from fastapi import APIRouter, Query
from vpsweb.repository.models import SearchQuery, SearchResult

router = APIRouter()
repository = PoemRepository()

@router.get("/", response_model=List[SearchResult])
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    search_type: str = Query("all", pattern="^(all|poems|translations)$"),
    languages: Optional[List[str]] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    Full-text search across poems and translations
    
    Parameters:
    - q: Search query (required)
    - search_type: 'all', 'poems', or 'translations'
    - languages: Filter by languages (source or target)
    - limit: Maximum results to return
    - offset: Pagination offset
    """
    results = repository.search(
        query=q,
        search_type=search_type,
        languages=languages,
        limit=limit
    )
    return results

@router.get("/suggestions")
async def search_suggestions(q: str = Query(..., min_length=2)):
    """
    Get search suggestions/autocomplete
    Returns matching poem titles and authors
    """
    # Implementation: Query poems table for partial matches
    pass
```

#### 2.2.4 Workflow API (TET Translation)

**File**: `src/vpsweb/web/api/workflow.py`

**Requirements**:
- Trigger TET workflow from web interface
- Support async execution with progress tracking
- WebSocket for real-time updates
- Cost estimation before translation
- Automatic storage in repository

**Endpoints**:

```python
from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket
from pydantic import BaseModel
from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.models.translation import TranslationInput
from vpsweb.models.config import WorkflowMode
from vpsweb.utils.config_loader import load_config

router = APIRouter()
repository = PoemRepository()

class TranslationRequest(BaseModel):
    """Request model for translation"""
    poem_text: str
    source_language: str
    target_language: str
    workflow_mode: str = "hybrid"
    
    # Optional: If translating existing poem
    poem_id: Optional[int] = None
    
    # Optional metadata for new poems
    title: Optional[str] = None
    author: Optional[str] = None
    era: Optional[str] = None
    style: Optional[str] = None

class TranslationResponse(BaseModel):
    """Response model for translation"""
    translation_id: int
    poem_id: int
    status: str
    message: str
    websocket_url: Optional[str] = None

@router.post("/translate", response_model=TranslationResponse)
async def translate_poem(
    request: TranslationRequest,
    background_tasks: BackgroundTasks
):
    """
    Initiate TET translation workflow
    Returns immediately with translation_id and WebSocket URL for progress
    """
    
    # Load configuration
    config = load_config()
    
    # Create or find poem
    if request.poem_id:
        poem_id = request.poem_id
        poem = repository.get_poem(poem_id)
        if not poem:
            raise HTTPException(status_code=404, detail="Poem not found")
    else:
        # Create new poem
        title = request.title or extract_title_from_text(request.poem_text)
        poem_id = repository.add_poem(
            title=title,
            author=request.author,
            source_language=request.source_language,
            original_text=request.poem_text,
            era=request.era,
            style=request.style
        )
    
    # Prepare translation input
    input_data = TranslationInput(
        original_poem=request.poem_text,
        source_lang=request.source_language,
        target_lang=request.target_language
    )
    
    # Execute workflow in background
    workflow = TranslationWorkflow(
        config.main.workflow,
        config.providers,
        workflow_mode=WorkflowMode[request.workflow_mode.upper()]
    )
    
    # Create placeholder translation record
    translation_id = repository.add_translation(
        poem_id=poem_id,
        target_language=request.target_language,
        workflow_mode=request.workflow_mode,
        initial_translation="Processing...",
        editor_review="Processing...",
        revised_translation="Processing..."
    )
    
    # Execute translation in background
    background_tasks.add_task(
        execute_and_store_translation,
        workflow,
        input_data,
        translation_id,
        repository
    )
    
    return TranslationResponse(
        translation_id=translation_id,
        poem_id=poem_id,
        status="processing",
        message="Translation started",
        websocket_url=f"/api/workflow/progress/{translation_id}"
    )

async def execute_and_store_translation(
    workflow: TranslationWorkflow,
    input_data: TranslationInput,
    translation_id: int,
    repository: PoemRepository
):
    """Background task to execute translation and update repository"""
    try:
        # Execute workflow
        result = await workflow.execute(input_data)
        
        # Update translation record with results
        repository.update_translation(
            translation_id,
            initial_translation=result.initial_translation.initial_translation,
            initial_translator_notes=result.initial_translation.translator_notes,
            editor_review=result.editor_review.editor_review,
            editor_suggestions=result.editor_review.editor_suggestions,
            revised_translation=result.revised_translation.revised_translation,
            revision_explanation=result.revised_translation.revision_explanation,
            total_tokens=result.total_tokens,
            total_duration_seconds=result.duration_seconds,
            total_cost_rmb=result.total_cost,
            step_metrics=result.get_step_metrics()
        )
        
    except Exception as e:
        # Log error and update translation with error status
        logger.error(f"Translation failed: {e}", exc_info=True)
        repository.update_translation(
            translation_id,
            initial_translation=f"ERROR: {str(e)}",
            editor_review="N/A",
            revised_translation="N/A"
        )

@router.websocket("/progress/{translation_id}")
async def translation_progress(websocket: WebSocket, translation_id: int):
    """
    WebSocket endpoint for real-time translation progress
    Sends updates as workflow executes
    """
    await websocket.accept()
    
    try:
        # Poll translation status and send updates
        while True:
            translation = repository.get_translation(translation_id)
            
            # Send progress update
            await websocket.send_json({
                "translation_id": translation_id,
                "status": translation.status if hasattr(translation, 'status') else "processing",
                "current_step": translation.current_step if hasattr(translation, 'current_step') else None,
                "progress": translation.progress if hasattr(translation, 'progress') else 0
            })
            
            # Check if complete
            if translation.revised_translation and "Processing..." not in translation.revised_translation:
                await websocket.send_json({"status": "complete"})
                break
            
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

@router.post("/estimate")
async def estimate_cost(request: TranslationRequest):
    """
    Estimate cost and time for translation
    Returns approximate token count, duration, and RMB cost
    """
    # Rough estimation based on text length and workflow mode
    text_length = len(request.poem_text)
    
    # Simplified estimation logic
    estimated_tokens = text_length * 2  # Rough multiplier
    
    if request.workflow_mode == "reasoning":
        estimated_cost = estimated_tokens * 0.00001  # Higher cost
        estimated_duration = 180  # ~3 minutes
    elif request.workflow_mode == "hybrid":
        estimated_cost = estimated_tokens * 0.000005
        estimated_duration = 120  # ~2 minutes
    else:  # non_reasoning
        estimated_cost = estimated_tokens * 0.000002
        estimated_duration = 60  # ~1 minute
    
    return {
        "estimated_tokens": estimated_tokens,
        "estimated_duration_seconds": estimated_duration,
        "estimated_cost_rmb": estimated_cost,
        "workflow_mode": request.workflow_mode
    }
```

---

## Phase 3: Web UI (Priority: MEDIUM)

### 3.1 Base Template Structure

**File**: `src/vpsweb/web/templates/base.html`

**Requirements**:
- Responsive layout with Tailwind CSS
- Navigation header
- Footer with stats
- HTMX and Alpine.js setup
- Toast notifications for user feedback

**Base Template**:

```html
<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}VPSWeb Poetry Repository{% endblock %}</title>
    
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    
    <!-- Alpine.js -->
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    
    <!-- Custom CSS -->
    <link rel="stylesheet" href="{{ url_for('static', path='/css/styles.css') }}">
    
    {% block head %}{% endblock %}
</head>
<body class="h-full bg-gray-50">
    <!-- Navigation -->
    <nav class="bg-white shadow-sm border-b border-gray-200">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex">
                    <div class="flex-shrink-0 flex items-center">
                        <a href="/" class="text-2xl font-bold text-indigo-600">
                            🎭 VPSWeb
                        </a>
                    </div>
                    <div class="hidden sm:ml-6 sm:flex sm:space-x-8">
                        <a href="/" class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            Home
                        </a>
                        <a href="/browse" class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            Browse
                        </a>
                        <a href="/search" class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            Search
                        </a>
                        <a href="/translate" class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            Translate
                        </a>
                        <a href="/collections" class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            Collections
                        </a>
                    </div>
                </div>
                <div class="flex items-center">
                    <a href="/api/docs" target="_blank" class="text-sm text-gray-500 hover:text-gray-700">
                        API Docs
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {% block content %}{% endblock %}
    </main>

    <!-- Footer -->
    <footer class="bg-white border-t border-gray-200 mt-12">
        <div class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
            <div class="text-center text-sm text-gray-500">
                <p>VPSWeb Poetry Repository - Powered by AI-driven TET workflow</p>
                <p class="mt-2">
                    {% if stats %}
                        {{ stats.poem_count }} poems · {{ stats.translation_count }} translations · {{ stats.language_pair_count }} language pairs
                    {% endif %}
                </p>
            </div>
        </div>
    </footer>

    <!-- Toast Notification (Alpine.js component) -->
    <div x-data="{ show: false, message: '' }" 
         x-show="show" 
         x-transition
         @notify.window="message = $event.detail; show = true; setTimeout(() => show = false, 3000)"
         class="fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg"
         style="display: none;">
        <p x-text="message"></p>
    </div>

    {% block scripts %}{% endblock %}
</body>
</html>
```

### 3.2 Home Page

**File**: `src/vpsweb/web/templates/home.html`

**Features**:
- Repository statistics
- Recent translations
- Featured poems
- Quick search
- Quick translate button

```html
{% extends "base.html" %}

{% block content %}
<div class="px-4 py-8">
    <!-- Hero Section -->
    <div class="text-center mb-12">
        <h1 class="text-4xl font-bold text-gray-900 mb-4">
            Poetry Translation Repository
        </h1>
        <p class="text-xl text-gray-600 max-w-2xl mx-auto">
            Professional AI-powered poetry translation using the proven TET workflow.
            Preserving beauty, meaning, and cultural context across languages.
        </p>
        <div class="mt-8">
            <a href="/translate" class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">
                Start Translating
            </a>
            <a href="/browse" class="ml-4 inline-flex items-center px-6 py-3 border border-gray-300 text-base font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                Browse Repository
            </a>
        </div>
    </div>

    <!-- Statistics Grid -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
        <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <svg class="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                        </svg>
                    </div>
                    <div class="ml-5 w-0 flex-1">
                        <dl>
                            <dt class="text-sm font-medium text-gray-500 truncate">
                                Total Poems
                            </dt>
                            <dd class="text-lg font-semibold text-gray-900">
                                {{ stats.poem_count }}
                            </dd>
                        </dl>
                    </div>
                </div>
            </div>
        </div>

        <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <svg class="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                        </svg>
                    </div>
                    <div class="ml-5 w-0 flex-1">
                        <dl>
                            <dt class="text-sm font-medium text-gray-500 truncate">
                                Translations
                            </dt>
                            <dd class="text-lg font-semibold text-gray-900">
                                {{ stats.translation_count }}
                            </dd>
                        </dl>
                    </div>
                </div>
            </div>
        </div>

        <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <svg class="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                        </svg>
                    </div>
                    <div class="ml-5 w-0 flex-1">
                        <dl>
                            <dt class="text-sm font-medium text-gray-500 truncate">
                                Language Pairs
                            </dt>
                            <dd class="text-lg font-semibold text-gray-900">
                                {{ stats.language_pair_count }}
                            </dd>
                        </dl>
                    </div>
                </div>
            </div>
        </div>

        <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <svg class="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                        </svg>
                    </div>
                    <div class="ml-5 w-0 flex-1">
                        <dl>
                            <dt class="text-sm font-medium text-gray-500 truncate">
                                Avg Rating
                            </dt>
                            <dd class="text-lg font-semibold text-gray-900">
                                {{ stats.avg_rating|round(1) }}/5
                            </dd>
                        </dl>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Quick Search -->
    <div class="bg-white shadow rounded-lg p-6 mb-12">
        <h2 class="text-lg font-medium text-gray-900 mb-4">Quick Search</h2>
        <form hx-get="/api/search" hx-target="#search-results" hx-trigger="submit">
            <div class="flex gap-4">
                <input 
                    type="text" 
                    name="q" 
                    placeholder="Search poems, translations, authors..."
                    class="flex-1 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                    required
                />
                <button 
                    type="submit"
                    class="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                >
                    Search
                </button>
            </div>
        </form>
        <div id="search-results" class="mt-4"></div>
    </div>

    <!-- Recent Translations -->
    <div class="bg-white shadow rounded-lg p-6">
        <h2 class="text-lg font-medium text-gray-900 mb-4">Recent Translations</h2>
        <div class="space-y-4">
            {% for translation in recent_translations %}
            <div class="border-l-4 border-indigo-400 pl-4 py-2 hover:bg-gray-50">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <h3 class="text-sm font-medium text-gray-900">
                            <a href="/poems/{{ translation.poem_id }}" class="hover:underline">
                                {{ translation.poem_title }}
                            </a>
                        </h3>
                        <p class="text-sm text-gray-500">
                            {{ translation.source_language }} → {{ translation.target_language }}
                            · {{ translation.workflow_mode }} mode
                        </p>
                    </div>
                    <div class="flex items-center ml-4">
                        {% if translation.human_rating %}
                        <span class="flex items-center text-yellow-400">
                            {% for i in range(translation.human_rating) %}
                            <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                            </svg>
                            {% endfor %}
                        </span>
                        {% endif %}
                        <span class="ml-2 text-xs text-gray-400">
                            {{ translation.created_at|timeago }}
                        </span>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        <div class="mt-4 text-center">
            <a href="/browse" class="text-indigo-600 hover:text-indigo-500 text-sm font-medium">
                View all translations →
            </a>
        </div>
    </div>
</div>
{% endblock %}
```

### 3.3 Translation Workflow Page

**File**: `src/vpsweb/web/templates/translate.html`

**Features**:
- Input poem (paste or upload)
- Select source/target languages
- Choose workflow mode
- Cost/time estimation
- Real-time progress display
- Results display with rating

```html
{% extends "base.html" %}

{% block content %}
<div class="px-4 py-8" x-data="translationWorkflow()">
    <div class="max-w-4xl mx-auto">
        <h1 class="text-3xl font-bold text-gray-900 mb-8">Translate Poem</h1>

        <!-- Translation Form -->
        <div class="bg-white shadow rounded-lg p-6 mb-6" x-show="!translating && !result">
            <form @submit.prevent="submitTranslation()">
                <!-- Poem Input -->
                <div class="mb-6">
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        Poem Text
                    </label>
                    <textarea 
                        x-model="poemText"
                        rows="10"
                        class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                        placeholder="Paste your poem here..."
                        required
                    ></textarea>
                    <p class="mt-1 text-sm text-gray-500">
                        <span x-text="poemText.length"></span> characters
                    </p>
                </div>

                <!-- Language Selection -->
                <div class="grid grid-cols-2 gap-4 mb-6">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Source Language
                        </label>
                        <select 
                            x-model="sourceLanguage"
                            class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                        >
                            <option value="English">English</option>
                            <option value="Chinese">Chinese</option>
                            <option value="Spanish">Spanish</option>
                            <option value="French">French</option>
                            <option value="German">German</option>
                            <option value="Japanese">Japanese</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Target Language
                        </label>
                        <select 
                            x-model="targetLanguage"
                            class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                        >
                            <option value="Chinese">Chinese</option>
                            <option value="English">English</option>
                            <option value="Spanish">Spanish</option>
                            <option value="French">French</option>
                            <option value="German">German</option>
                            <option value="Japanese">Japanese</option>
                        </select>
                    </div>
                </div>

                <!-- Workflow Mode -->
                <div class="mb-6">
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                        Workflow Mode
                    </label>
                    <div class="space-y-2">
                        <label class="flex items-start p-4 border rounded-lg cursor-pointer" 
                               :class="workflowMode === 'hybrid' ? 'border-indigo-600 bg-indigo-50' : 'border-gray-300'">
                            <input type="radio" x-model="workflowMode" value="hybrid" class="mt-1">
                            <div class="ml-3">
                                <p class="font-medium text-gray-900">🎯 Hybrid (Recommended)</p>
                                <p class="text-sm text-gray-500">Optimal balance of quality and cost. Reasoning for editor review, standard models for translation.</p>
                            </div>
                        </label>
                        <label class="flex items-start p-4 border rounded-lg cursor-pointer"
                               :class="workflowMode === 'reasoning' ? 'border-indigo-600 bg-indigo-50' : 'border-gray-300'">
                            <input type="radio" x-model="workflowMode" value="reasoning" class="mt-1">
                            <div class="ml-3">
                                <p class="font-medium text-gray-900">🔮 Reasoning Mode</p>
                                <p class="text-sm text-gray-500">Highest quality. Uses reasoning models for all steps. Best for complex poetry.</p>
                            </div>
                        </label>
                        <label class="flex items-start p-4 border rounded-lg cursor-pointer"
                               :class="workflowMode === 'non_reasoning' ? 'border-indigo-600 bg-indigo-50' : 'border-gray-300'">
                            <input type="radio" x-model="workflowMode" value="non_reasoning" class="mt-1">
                            <div class="ml-3">
                                <p class="font-medium text-gray-900">⚡ Non-Reasoning Mode</p>
                                <p class="text-sm text-gray-500">Faster and more cost-effective. Standard models for all steps.</p>
                            </div>
                        </label>
                    </div>
                </div>

                <!-- Optional Metadata -->
                <div class="mb-6">
                    <button type="button" @click="showMetadata = !showMetadata" class="text-sm text-indigo-600 hover:text-indigo-500">
                        + Add optional metadata (title, author, era, style)
                    </button>
                    <div x-show="showMetadata" x-transition class="mt-4 space-y-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Title</label>
                            <input type="text" x-model="title" class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Author</label>
                            <input type="text" x-model="author" class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Era</label>
                                <input type="text" x-model="era" class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500" placeholder="e.g., Tang Dynasty, Romantic">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Style</label>
                                <input type="text" x-model="style" class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500" placeholder="e.g., Sonnet, 五言绝句">
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Cost Estimation -->
                <div class="mb-6 p-4 bg-gray-50 rounded-lg">
                    <button type="button" @click="estimateCost()" class="text-sm text-indigo-600 hover:text-indigo-500 mb-2">
                        Calculate estimated cost
                    </button>
                    <div x-show="estimate" x-transition class="text-sm text-gray-600 space-y-1">
                        <p>Estimated tokens: <span class="font-medium" x-text="estimate?.estimated_tokens"></span></p>
                        <p>Estimated duration: <span class="font-medium" x-text="estimate?.estimated_duration_seconds"></span>s</p>
                        <p>Estimated cost: <span class="font-medium text-indigo-600">¥<span x-text="estimate?.estimated_cost_rmb?.toFixed(6)"></span></span></p>
                    </div>
                </div>

                <!-- Submit -->
                <button 
                    type="submit"
                    class="w-full px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 font-medium"
                    :disabled="!poemText || !sourceLanguage || !targetLanguage"
                >
                    Start Translation
                </button>
            </form>
        </div>

        <!-- Progress Display -->
        <div x-show="translating" class="bg-white shadow rounded-lg p-6">
            <h2 class="text-xl font-semibold mb-4">Translation in Progress</h2>
            <div class="space-y-4">
                <!-- Step 1 -->
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <div class="h-10 w-10 rounded-full flex items-center justify-center"
                             :class="progress.step >= 1 ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'">
                            <span x-show="progress.step > 1">✓</span>
                            <span x-show="progress.step === 1">1</span>
                            <span x-show="progress.step < 1">1</span>
                        </div>
                    </div>
                    <div class="ml-4 flex-1">
                        <p class="text-sm font-medium text-gray-900">Initial Translation</p>
                        <p class="text-sm text-gray-500">Translator creates first draft with notes</p>
                    </div>
                </div>

                <!-- Step 2 -->
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <div class="h-10 w-10 rounded-full flex items-center justify-center"
                             :class="progress.step >= 2 ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'">
                            <span x-show="progress.step > 2">✓</span>
                            <span x-show="progress.step === 2">2</span>
                            <span x-show="progress.step < 2">2</span>
                        </div>
                    </div>
                    <div class="ml-4 flex-1">
                        <p class="text-sm font-medium text-gray-900">Editor Review</p>
                        <p class="text-sm text-gray-500">Professional editorial feedback</p>
                    </div>
                </div>

                <!-- Step 3 -->
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <div class="h-10 w-10 rounded-full flex items-center justify-center"
                             :class="progress.step >= 3 ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'">
                            <span x-show="progress.step > 3">✓</span>
                            <span x-show="progress.step === 3">3</span>
                            <span x-show="progress.step < 3">3</span>
                        </div>
                    </div>
                    <div class="ml-4 flex-1">
                        <p class="text-sm font-medium text-gray-900">Translator Revision</p>
                        <p class="text-sm text-gray-500">Final polished translation</p>
                    </div>
                </div>
            </div>

            <!-- Progress Bar -->
            <div class="mt-6">
                <div class="w-full bg-gray-200 rounded-full h-2">
                    <div class="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                         :style="`width: ${(progress.step / 3) * 100}%`"></div>
                </div>
            </div>

            <p class="mt-4 text-center text-sm text-gray-500">
                <span x-text="progress.message"></span>
            </p>
        </div>

        <!-- Results Display -->
        <div x-show="result" class="space-y-6">
            <!-- Translation Tabs -->
            <div class="bg-white shadow rounded-lg overflow-hidden">
                <div class="border-b border-gray-200">
                    <nav class="-mb-px flex">
                        <button @click="activeTab = 'final'" 
                                class="px-6 py-4 text-sm font-medium border-b-2"
                                :class="activeTab === 'final' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'">
                            Final Translation
                        </button>
                        <button @click="activeTab = 'workflow'" 
                                class="px-6 py-4 text-sm font-medium border-b-2"
                                :class="activeTab === 'workflow' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'">
                            TET Workflow
                        </button>
                        <button @click="activeTab = 'metrics'" 
                                class="px-6 py-4 text-sm font-medium border-b-2"
                                :class="activeTab === 'metrics' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'">
                            Metrics
                        </button>
                    </nav>
                </div>

                <!-- Tab Content -->
                <div class="p-6">
                    <!-- Final Translation Tab -->
                    <div x-show="activeTab === 'final'">
                        <div class="grid grid-cols-2 gap-6">
                            <div>
                                <h3 class="text-sm font-medium text-gray-700 mb-2">Original (<span x-text="sourceLanguage"></span>)</h3>
                                <div class="p-4 bg-gray-50 rounded-lg whitespace-pre-wrap" x-text="poemText"></div>
                            </div>
                            <div>
                                <h3 class="text-sm font-medium text-gray-700 mb-2">Translation (<span x-text="targetLanguage"></span>)</h3>
                                <div class="p-4 bg-indigo-50 rounded-lg whitespace-pre-wrap" x-text="result?.revised_translation"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Workflow Tab -->
                    <div x-show="activeTab === 'workflow'">
                        <div class="space-y-6">
                            <!-- Step 1 -->
                            <div>
                                <h3 class="text-sm font-medium text-gray-900 mb-2">Step 1: Initial Translation</h3>
                                <div class="p-4 bg-gray-50 rounded-lg whitespace-pre-wrap text-sm" x-text="result?.initial_translation"></div>
                                <div x-show="result?.initial_translator_notes" class="mt-2 p-3 bg-blue-50 rounded text-sm">
                                    <p class="font-medium text-blue-900 mb-1">Translator Notes:</p>
                                    <p class="text-blue-700" x-text="result?.initial_translator_notes"></p>
                                </div>
                            </div>

                            <!-- Step 2 -->
                            <div>
                                <h3 class="text-sm font-medium text-gray-900 mb-2">Step 2: Editor Review</h3>
                                <div class="p-4 bg-gray-50 rounded-lg whitespace-pre-wrap text-sm" x-text="result?.editor_review"></div>
                                <div x-show="result?.editor_suggestions" class="mt-2 p-3 bg-yellow-50 rounded text-sm">
                                    <p class="font-medium text-yellow-900 mb-1">Editor Suggestions:</p>
                                    <p class="text-yellow-700" x-text="result?.editor_suggestions"></p>
                                </div>
                            </div>

                            <!-- Step 3 -->
                            <div>
                                <h3 class="text-sm font-medium text-gray-900 mb-2">Step 3: Revised Translation</h3>
                                <div class="p-4 bg-green-50 rounded-lg whitespace-pre-wrap text-sm" x-text="result?.revised_translation"></div>
                                <div x-show="result?.revision_explanation" class="mt-2 p-3 bg-green-50 rounded text-sm">
                                    <p class="font-medium text-green-900 mb-1">Revision Explanation:</p>
                                    <p class="text-green-700" x-text="result?.revision_explanation"></p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Metrics Tab -->
                    <div x-show="activeTab === 'metrics'">
                        <div class="grid grid-cols-3 gap-4">
                            <div class="p-4 bg-gray-50 rounded-lg">
                                <p class="text-sm text-gray-500">Total Tokens</p>
                                <p class="text-2xl font-semibold text-gray-900" x-text="result?.total_tokens"></p>
                            </div>
                            <div class="p-4 bg-gray-50 rounded-lg">
                                <p class="text-sm text-gray-500">Duration</p>
                                <p class="text-2xl font-semibold text-gray-900"><span x-text="result?.total_duration_seconds?.toFixed(1)"></span>s</p>
                            </div>
                            <div class="p-4 bg-gray-50 rounded-lg">
                                <p class="text-sm text-gray-500">Cost</p>
                                <p class="text-2xl font-semibold text-indigo-600">¥<span x-text="result?.total_cost_rmb?.toFixed(6)"></span></p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Rating Section -->
            <div class="bg-white shadow rounded-lg p-6">
                <h3 class="text-lg font-medium text-gray-900 mb-4">Rate this Translation</h3>
                <div class="flex items-center space-x-2 mb-4">
                    <template x-for="star in [1,2,3,4,5]">
                        <button @click="rating = star" type="button">
                            <svg class="h-8 w-8" :class="star <= rating ? 'text-yellow-400' : 'text-gray-300'" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                            </svg>
                        </button>
                    </template>
                </div>
                <textarea 
                    x-model="qualityNotes"
                    rows="3"
                    placeholder="Optional: Add your thoughts about this translation..."
                    class="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 mb-4"
                ></textarea>
                <button @click="submitRating()" class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
                    Submit Rating
                </button>
            </div>

            <!-- Actions -->
            <div class="flex justify-between">
                <button @click="reset()" class="px-6 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">
                    Translate Another Poem
                </button>
                <a :href="`/poems/${result?.poem_id}`" class="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
                    View in Repository
                </a>
            </div>
        </div>
    </div>
</div>

<script>
function translationWorkflow() {
    return {
        // Form data
        poemText: '',
        sourceLanguage: 'English',
        targetLanguage: 'Chinese',
        workflowMode: 'hybrid',
        title: '',
        author: '',
        era: '',
        style: '',
        showMetadata: false,
        
        // UI state
        translating: false,
        result: null,
        activeTab: 'final',
        estimate: null,
        
        // Progress
        progress: {
            step: 0,
            message: 'Initializing...'
        },
        
        // Rating
        rating: 0,
        qualityNotes: '',
        
        async estimateCost() {
            const response = await fetch('/api/workflow/estimate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    poem_text: this.poemText,
                    source_language: this.sourceLanguage,
                    target_language: this.targetLanguage,
                    workflow_mode: this.workflowMode
                })
            });
            this.estimate = await response.json();
        },
        
        async submitTranslation() {
            this.translating = true;
            this.progress.step = 0;
            
            const response = await fetch('/api/workflow/translate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    poem_text: this.poemText,
                    source_language: this.sourceLanguage,
                    target_language: this.targetLanguage,
                    workflow_mode: this.workflowMode,
                    title: this.title,
                    author: this.author,
                    era: this.era,
                    style: this.style
                })
            });
            
            const data = await response.json();
            
            // Connect to WebSocket for progress
            this.connectWebSocket(data.translation_id);
        },
        
        connectWebSocket(translationId) {
            const ws = new WebSocket(`ws://${window.location.host}/api/workflow/progress/${translationId}`);
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.status === 'complete') {
                    this.loadTranslation(translationId);
                } else {
                    this.progress.step = data.current_step || 0;
                    this.progress.message = data.message || 'Processing...';
                }
            };
        },
        
        async loadTranslation(translationId) {
            const response = await fetch(`/api/translations/${translationId}`);
            this.result = await response.json();
            this.translating = false;
        },
        
        async submitRating() {
            if (!this.rating || !this.result) return;
            
            await fetch(`/api/translations/${this.result.id}/rate`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    rating: this.rating,
                    quality_notes: this.qualityNotes
                })
            });
            
            window.dispatchEvent(new CustomEvent('notify', { 
                detail: 'Rating submitted successfully!' 
            }));
        },
        
        reset() {
            this.poemText = '';
            this.result = null;
            this.translating = false;
            this.rating = 0;
            this.qualityNotes = '';
            this.activeTab = 'final';
        }
    }
}
</script>
{% endblock %}
```

### 3.4 Browse & Search Pages

**Files**: `src/vpsweb/web/templates/browse.html`, `search.html`, `poem_detail.html`

(Similar structure with HTMX for dynamic loading, filters, and pagination)

---

## Phase 4: Testing & Quality (Priority: MEDIUM)

### 4.1 Unit Tests

**File**: `tests/unit/test_repository.py`

**Requirements**:
- Test all PoemRepository methods
- Test database operations (CRUD)
- Test full-text search functionality
- Test data validation
- Mock external dependencies

**Example Tests**:

```python
import pytest
from vpsweb.repository import PoemRepository
from vpsweb.repository.models import Poem, Translation

@pytest.fixture
def repo(tmp_path):
    """Create temporary repository for testing"""
    db_path = tmp_path / "test.db"
    return PoemRepository(str(db_path))

def test_add_poem(repo):
    """Test adding a new poem"""
    poem_id = repo.add_poem(
        title="Test Poem",
        author="Test Author",
        source_language="English",
        original_text="Test text"
    )
    assert poem_id > 0
    
    poem = repo.get_poem(poem_id)
    assert poem.title == "Test Poem"
    assert poem.author == "Test Author"

def test_find_or_create_poem(repo):
    """Test find or create functionality"""
    # First call creates
    poem_id_1 = repo.find_or_create_poem(
        title="Unique Poem",
        author="Author",
        source_language="English",
        original_text="Text"
    )
    
    # Second call finds existing
    poem_id_2 = repo.find_or_create_poem(
        title="Unique Poem",
        author="Author",
        source_language="English",
        original_text="Text"
    )
    
    assert poem_id_1 == poem_id_2

def test_add_translation(repo):
    """Test adding translation"""
    poem_id = repo.add_poem(
        title="Test",
        author="Author",
        source_language="English",
        original_text="Text"
    )
    
    translation_id = repo.add_translation(
        poem_id=poem_id,
        target_language="Chinese",
        workflow_mode="hybrid",
        initial_translation="初译",
        editor_review="编辑审查",
        revised_translation="修订译文"
    )
    
    assert translation_id > 0
    translation = repo.get_translation(translation_id)
    assert translation.target_language == "Chinese"

def test_search_poems(repo):
    """Test full-text search"""
    repo.add_poem(
        title="Summer Day",
        author="Poet",
        source_language="English",
        original_text="The summer breeze flows"
    )
    
    results = repo.search_poems("summer")
    assert len(results) > 0
    assert "summer" in results[0].title.lower() or "summer" in results[0].original_text.lower()

def test_update_translation_rating(repo):
    """Test rating update"""
    poem_id = repo.add_poem(
        title="Test",
        author="Author",
        source_language="English",
        original_text="Text"
    )
    
    translation_id = repo.add_translation(
        poem_id=poem_id,
        target_language="Chinese",
        workflow_mode="hybrid",
        initial_translation="初译",
        editor_review="编辑审查",
        revised_translation="修订译文"
    )
    
    success = repo.update_translation_rating(translation_id, 5, "Excellent!")
    assert success
    
    translation = repo.get_translation(translation_id)
    assert translation.human_rating == 5
    assert translation.quality_notes == "Excellent!"
```

### 4.2 Integration Tests

**File**: `tests/integration/test_web_api.py`

**Requirements**:
- Test API endpoints end-to-end
- Test workflow execution
- Test search functionality
- Use TestClient from FastAPI

```python
from fastapi.testclient import TestClient
from vpsweb.web.app import app

client = TestClient(app)

def test_list_poems():
    """Test GET /api/poems"""
    response = client.get("/api/poems")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_poem():
    """Test POST /api/poems"""
    poem_data = {
        "title": "Test Poem",
        "author": "Test Author",
        "source_language": "English",
        "original_text": "This is a test poem"
    }
    response = client.post("/api/poems", json=poem_data)
    assert response.status_code == 201
    assert response.json()["title"] == "Test Poem"

def test_search():
    """Test GET /api/search"""
    response = client.get("/api/search?q=test")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
```

---

## Phase 5: Deployment (Priority: LOW initially)

### 5.1 Production Configuration

**File**: `config/production.yaml`

**Requirements**:
- Production database settings
- API rate limiting
- Logging configuration
- Security settings

```yaml
# Production configuration
environment: production

database:
  path: "/app/data/repository.db"
  backup_path: "/app/backups/"
  backup_interval_hours: 24

api:
  host: "0.0.0.0"
  port: 8000
  workers: 2
  rate_limit:
    enabled: true
    requests_per_minute: 60
  cors:
    allowed_origins:
      - "https://yoursite.com"

logging:
  level: "INFO"
  format: "json"
  file: "/app/logs/vpsweb.log"
  rotation: "100 MB"

security:
  api_key_required: false  # Enable when needed
  https_only: true
```

### 5.2 Dockerfile

**File**: `Dockerfile`

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

# Copy application
COPY src/ ./src/
COPY config/ ./config/

# Create data directories
RUN mkdir -p /app/data /app/logs /app/backups

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "vpsweb.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.3 Deployment Scripts

**File**: `scripts/deploy.sh`

```bash
#!/bin/bash
# Deployment script for Railway/Render

echo "Building application..."
docker build -t vpsweb:latest .

echo "Running database migrations..."
python scripts/init_database.py

echo "Starting application..."
exec uvicorn vpsweb.web.app:app --host 0.0.0.0 --port $PORT
```

---

## Dependencies & Configuration

### Updated pyproject.toml

```toml
[tool.poetry]
name = "vpsweb"
version = "1.0.0"
description = "AI-powered poetry translation with repository and web interface"

[tool.poetry.dependencies]
python = "^3.9"

# Existing dependencies
openai = "^1.0.0"
pydantic = "^2.0.0"
python-dotenv = "^1.0.0"
pyyaml = "^6.0"
click = "^8.0.0"

# NEW: Web and database dependencies
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
jinja2 = "^3.1.2"
python-multipart = "^0.0.6"
websockets = "^12.0"
aiofiles = "^23.2.1"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-cov = "^4.1.0"
pytest-asyncio = "^0.21.0"
black = "^23.0.0"
flake8 = "^6.1.0"
mypy = "^1.5.0"

[tool.poetry.scripts]
vpsweb = "vpsweb.__main__:main"
```

---

## Implementation Checklist

### Phase 1: Repository Core (Week 1-2)
- [ ] Create database schema SQL file
- [ ] Implement PoemRepository class
- [ ] Create data models (Pydantic)
- [ ] Add FTS5 search functionality
- [ ] Integrate with existing CLI (--store flag)
- [ ] Create import script for existing translations
- [ ] Write unit tests for repository
- [ ] Test with existing vpsweb outputs

### Phase 2: Web API (Week 3-4)
- [ ] Set up FastAPI application
- [ ] Implement Poems API endpoints
- [ ] Implement Translations API endpoints
- [ ] Implement Search API endpoints
- [ ] Implement Workflow API with WebSocket
- [ ] Add cost estimation endpoint
- [ ] Create API documentation
- [ ] Write integration tests

### Phase 3: Web UI (Week 5-7)