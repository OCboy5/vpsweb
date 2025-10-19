# VPSWeb Architecture Documentation

**Version**: v0.3.1
**Date**: 2025-10-19
**Status**: Production-Ready Repository System

---

## 📋 Overview

VPSWeb v0.3.1 implements a **modular FastAPI monolith** architecture with a **dual-storage strategy** that provides both robust data management and flexible file archival capabilities. This architecture was designed to transform VPSWeb from a CLI tool into a full-featured web application while maintaining complete backward compatibility.

---

## 🏗️ System Architecture

### **High-Level Architecture Pattern**

```
┌─────────────────────────────────────────────────────────────────┐
│                    VPSWeb v0.3.1 Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│  Web Interface Layer (FastAPI + Jinja2 + Tailwind CSS)           │
│  ├── Dashboard & Statistics                                     │
│  ├── Poem Management Interface                                 │
│  ├── Translation Management                                   │
│  └── API Documentation                                        │
├─────────────────────────────────────────────────────────────────┤
│  API Layer (FastAPI Routers)                                    │
│  ├── Poems API (/api/v1/poems/)                               │
│  ├── Translations API (/api/v1/translations/)                 │
│  ├── Statistics API (/api/v1/statistics/)                     │
│  └── Workflow API (/api/v1/workflow/)                         │
├─────────────────────────────────────────────────────────────────┤
│  Service Layer (Business Logic)                                 │
│  ├── PoemService                                               │
│  ├── TranslationService                                        │
│  └── VPSWebWorkflowAdapter                                     │
├─────────────────────────────────────────────────────────────────┤
│  Repository Layer (Data Access)                                 │
│  ├── CRUD Operations                                           │
│  ├── Database Session Management                               │
│  └── Data Validation                                           │
├─────────────────────────────────────────────────────────────────┤
│  Data Storage Layer                                             │
│  ├── SQLite Database (Primary Data Store)                      │
│  └── File System Archive (Original AI Outputs)                 │
├─────────────────────────────────────────────────────────────────┤
│  Integration Layer                                              │
│  ├── VPSWeb Translation Engine                                 │
│  ├── WeChat Article Generation                                │
│  └── Background Task Processing                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Dual-Storage Strategy

### **Storage Architecture Principle**

**SQLite Database = Single Source of Truth for Queryable Data**
**File System Archive = Immutable Raw Output Storage**

This dual-storage approach provides the best of both worlds:
- **Fast, indexed access** to structured data through the database
- **Complete audit trail** and **re-processing capability** through file archival

### **Data Storage Responsibilities**

#### **SQLite Database** (Primary Data Store)
- **Purpose**: Fast, indexed access to all queryable data and metadata
- **Content**: Structured data with relationships and constraints
- **Access Patterns**:
  - Dashboard statistics and reporting
  - Poem browsing and searching
  - Translation management and comparison
  - API responses and web interface data
- **Performance**: Optimized for read-heavy operations with proper indexing

#### **File System Archive** (`repository_root/data/`)
- **Purpose**: Immutable storage of original AI workflow outputs
- **Content**: Raw JSON files from translation and WeChat workflows
- **Access Patterns**:
  - Re-processing of original AI outputs
  - Historical analysis and audit trails
  - Backup and archival purposes
  - Data migration and format conversion
- **Linkage**: Connected to database via `translations.raw_path` column

### **Data Flow Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input    │───▶│  VPSWeb Workflow  │───▶│  JSON Output    │
│   (Web/CLI)     │    │     Engine        │    │   (Raw File)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Database Store  │◀───│   Parsed Data    │◀───│ File Path Link  │
│ (Structured)    │    │   Extraction     │    │   Reference     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

---

## 🗄️ Database Schema Design

### **4-Table Schema Architecture**

#### **1. poems** - Poem Metadata
```sql
CREATE TABLE poems (
    id TEXT PRIMARY KEY,                    -- ULID for time-sortable IDs
    title TEXT NOT NULL,                     -- Poem title
    author TEXT NOT NULL,                    -- Poet name
    source_lang TEXT NOT NULL,               -- Source language (ISO code)
    original_text TEXT NOT NULL,             -- Original poem content
    metadata TEXT,                           -- JSON metadata (optional)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### **2. translations** - Translation Records
```sql
CREATE TABLE translations (
    id TEXT PRIMARY KEY,                    -- ULID for time-sortable IDs
    poem_id TEXT NOT NULL REFERENCES poems(id) ON DELETE CASCADE,
    target_lang TEXT NOT NULL,               -- Target language (ISO code)
    workflow_mode TEXT NOT NULL,             -- reasoning|non_reasoning|hybrid
    translation_type TEXT NOT NULL,          -- ai|human
    translated_text TEXT NOT NULL,           -- Final translation result
    raw_path TEXT,                           -- Path to original JSON output file
    quality_rating INTEGER,                   -- 1-5 rating (optional)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### **3. ai_logs** - AI Workflow Execution Logs
```sql
CREATE TABLE ai_logs (
    id TEXT PRIMARY KEY,                    -- ULID for time-sortable IDs
    translation_id TEXT NOT NULL REFERENCES translations(id) ON DELETE CASCADE,
    model_name TEXT NOT NULL,                -- AI model used (e.g., qwen-max)
    step_name TEXT NOT NULL,                 -- Workflow step (initial_translation|editor_review|final_revision)
    runtime_seconds REAL NOT NULL,          -- Execution time
    token_usage TEXT NOT NULL,               -- JSON with prompt/completion counts
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### **4. human_notes** - Human Editorial Notes
```sql
CREATE TABLE human_notes (
    id TEXT PRIMARY KEY,                    -- ULID for time-sortable IDs
    translation_id TEXT NOT NULL REFERENCES translations(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,                 -- Human editorial feedback
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **Relationship Design**
- **One-to-Many**: `poems` → `translations` (one poem can have many translations)
- **One-to-Many**: `translations` → `ai_logs` (one translation can have multiple AI execution logs)
- **One-to-Many**: `translations` → `human_notes` (one translation can have multiple human notes)
- **Cascading Deletes**: Deleting a poem automatically removes all related translations and notes

---

## 🔧 Technical Stack Integration

### **Core Technologies**
- **FastAPI**: Modern Python web framework with automatic OpenAPI documentation
- **SQLAlchemy 2.0**: Modern ORM with async support and relationship management
- **Pydantic V2**: Data validation and serialization with field validators
- **SQLite**: Local database with WAL mode for optimal performance
- **Jinja2**: Template engine for server-rendered HTML
- **Tailwind CSS**: Modern utility-first CSS framework

### **Integration Patterns**

#### **FastAPI + SQLAlchemy Integration**
```python
# Dependency injection pattern
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API endpoint with database access
@app.get("/api/v1/poems/")
async def list_poems(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    poems = poem_service.get_poems(db, skip=skip, limit=limit)
    return poems
```

#### **Pydantic V2 Validation Integration**
```python
from pydantic import BaseModel, Field, field_validator, ConfigDict

class TranslationCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    poem_id: str = Field(..., description="Poem ID")
    target_lang: str = Field(..., description="Target language")
    translated_text: str = Field(..., min_length=1)

    @field_validator("target_lang")
    @classmethod
    def validate_target_language(cls, v):
        if v not in ["en", "zh-CN", "pl"]:
            raise ValueError("Invalid target language")
        return v
```

---

## 🔄 Background Task Architecture

### **Async Workflow Processing**

VPSWeb implements background task processing for long-running translation workflows:

```python
# Background task execution
@app.post("/api/v1/workflow/translate")
async def start_translation_workflow(
    request: WorkflowRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Create task record
    task = workflow_service.create_task(db, request)

    # Start background processing
    background_tasks.add_task(
        execute_translation_workflow,
        task.id,
        request
    )

    return {"task_id": task.id, "status": "pending"}
```

### **Task Tracking Architecture**
- **Database-First Tracking**: Task status stored in database for persistence
- **Status Management**: pending → running → completed/failed
- **Memory Management**: Automatic cleanup of old task records
- **Error Handling**: Comprehensive error capture and user feedback

---

## 🎨 Web Interface Architecture

### **Modern Web Application Design**

#### **Template Architecture**
```
templates/
├── base.html              # Base template with navigation and styling
├── index.html             # Dashboard with statistics and recent poems
├── poem_detail.html       # Poem detail and translation management
├── poem_new.html          # New poem creation form
├── poem_compare.html      # Translation comparison interface
└── api_docs.html         # User-friendly API documentation
```

#### **Responsive Design Strategy**
- **Mobile-First**: Progressive enhancement from mobile to desktop
- **Tailwind CSS**: Utility-first CSS framework for consistent styling
- **Interactive Components**: JavaScript for dynamic content loading
- **Accessibility**: Semantic HTML5 with proper ARIA labels

---

## 🔍 API Architecture

### **RESTful API Design**

#### **API Endpoint Organization**
- **Poems API**: `/api/v1/poems/` - Poem CRUD operations and search
- **Translations API**: `/api/v1/translations/` - Translation management
- **Statistics API**: `/api/v1/statistics/` - Repository analytics
- **Workflow API**: `/api/v1/workflow/` - Translation workflow triggers

#### **OpenAPI Documentation**
- **Auto-Generated**: FastAPI automatically creates OpenAPI specifications
- **Interactive Docs**: Swagger UI available at `/docs`
- **Comprehensive Examples**: Request/response examples for all endpoints

---

## 🚀 Performance Optimization

### **Database Performance**
- **Indexing Strategy**: Strategic indexes on foreign keys and search fields
- **Query Optimization**: Single LEFT JOIN queries to prevent N+1 problems
- **Connection Pooling**: Proper session management with SQLAlchemy
- **WAL Mode**: SQLite Write-Ahead Logging for better concurrency

### **Application Performance**
- **Async Processing**: Background tasks prevent API blocking
- **Response Times**: <200ms for all API endpoints
- **Caching Strategy**: Database query results cached where appropriate
- **Static File Serving**: Optimized static asset delivery

---

## 🔐 Security Architecture

### **Data Validation**
- **Input Sanitization**: Comprehensive validation with Pydantic schemas
- **SQL Injection Prevention**: SQLAlchemy ORM parameterized queries
- **XSS Protection**: Jinja2 auto-escaping for user content
- **File Upload Security**: Path validation and content type checking

### **Error Handling**
- **Structured Exceptions**: Comprehensive error hierarchy with meaningful messages
- **Transaction Rollback**: Automatic rollback on database errors
- **User Feedback**: Clear error messages without exposing system internals

---

## 📈 Scalability Considerations

### **Current Scope (Single-User Local Application)**
- **SQLite**: Excellent performance for local single-user scenarios
- **File Storage**: Local file system with adequate performance
- **Background Tasks**: FastAPI BackgroundTasks sufficient for current load

### **Future Scaling Path**
- **Database Migration**: SQLite → PostgreSQL for multi-user scenarios
- **File Storage**: Local → Cloud storage (S3, etc.) for distributed access
- **Background Tasks**: BackgroundTasks → Redis/Celery for distributed processing
- **Authentication**: Local → OAuth/JWT for multi-user support

---

## 🧪 Testing Architecture

### **Testing Strategy**
- **Unit Tests**: Model validation and CRUD operation testing
- **Integration Tests**: API endpoint testing with database fixtures
- **End-to-End Tests**: Complete workflow validation
- **Performance Tests**: Load testing for API endpoints

### **Test Infrastructure**
- **pytest**: Primary testing framework with fixtures
- **In-Memory SQLite**: Fast, isolated database testing
- **Coverage Goals**: 85%+ coverage for critical components
- **CI/CD Integration**: Automated testing on code changes

---

## 📚 Documentation Architecture

### **Documentation Hierarchy**
```
docs/
├── ARCHITECTURE.md              # This document - system architecture
├── User_Guide.md                 # End-user documentation
├── Development_Setup.md          # Developer onboarding guide
├── backup_restore_guide.md       # Backup and restoration procedures
├── reflections/                  # Post-implementation reflections
└── PSD_Collection/               # Project specification documents
```

### **Code Documentation**
- **Docstrings**: Comprehensive Google/NumPy style docstrings
- **Type Hints**: Full type annotation coverage
- **Inline Comments**: Strategic comments for complex logic
- **API Documentation**: Auto-generated OpenAPI specifications

---

## 🔄 Maintenance and Operations

### **Backup Strategy**
- **Automated Backups**: `scripts/backup.sh` for comprehensive system backup
- **Database Backups**: SQLite file backups with integrity validation
- **Configuration Backups**: YAML configuration and environment settings
- **Code Repository**: Git version control with proper tagging

### **Monitoring and Logging**
- **Structured Logging**: Comprehensive logging with log levels
- **Performance Monitoring**: API response time tracking
- **Error Tracking**: Comprehensive error capture and reporting
- **Health Checks**: Application health endpoints for monitoring

---

## 🎯 Conclusion

The VPSWeb v0.3.1 architecture represents a **well-designed, production-ready system** that successfully transforms a CLI tool into a comprehensive web application. The modular design, dual-storage strategy, and modern technology stack provide an excellent foundation for both current functionality and future scaling.

### **Key Architectural Strengths**
1. **Clean Separation of Concerns**: Modular architecture with clear layer boundaries
2. **Dual-Storage Strategy**: Optimal balance between performance and archival capabilities
3. **Modern Technology Stack**: FastAPI, SQLAlchemy 2.0, Pydantic V2 integration
4. **Comprehensive Testing**: Multi-layer testing strategy with good coverage
5. **Production-Ready Features**: Backup systems, monitoring, and documentation

### **Future Readiness**
The architecture is designed for gradual evolution:
- **Single-User → Multi-User**: Authentication and user management can be added
- **Local → Cloud**: Database and storage can be migrated to cloud services
- **CLI → Web → API**: Web interface can evolve to support external API consumers
- **Prototype → Production**: Architecture scales from prototype to production use

This architecture provides a solid foundation for VPSWeb's continued evolution while maintaining the simplicity and reliability that make it effective for its intended use case.

---

*Architecture documentation current as of v0.3.1 - 2025-10-19*