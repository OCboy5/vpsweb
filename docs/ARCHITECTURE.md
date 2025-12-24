# VPSWeb Architecture Documentation

**Version**: v0.7.0
**Date**: 2025-12-18
**Status**: Production-Ready Repository System with WebUI and BBR

---

## 📋 Overview

VPSWeb v0.7.0 implements a **modern web-centric architecture** with **real-time capabilities** and **AI-enhanced translation workflows**. The system features a sophisticated FastAPI-based WebUI as the primary interface, complemented by Background Briefing Reports (BBR) for contextual translation enhancement and Server-Sent Events (SSE) for live progress updates. This architecture represents the evolution from a CLI tool to a comprehensive web application with advanced AI-powered features.

---

## 🏗️ System Architecture

### **High-Level Architecture Pattern**

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                           VPSWeb v0.7.0 Architecture                              │
├────────────────────────────────────────────────────────────────────────────────┤
│  Web Interface Layer (FastAPI + Tailwind CSS + SSE)                               │
│  ├── Real-time Dashboard with Statistics                                         │
│  ├── Poem Management Interface                                                 │
│  ├── Translation Workflow with Live Progress                                    │
│  ├── BBR Modal System                                                          │
│  └── Responsive Design (Mobile + Desktop)                                      │
├────────────────────────────────────────────────────────────────────────────────┤
│  API Layer (FastAPI Routers + SSE Endpoints)                                   │
│  ├── Poems API (/api/v1/poems/)                                                 │
│  ├── Translations API (/api/v1/translations/)                                  │
│  ├── Poets API (/api/v1/poets/)                                                 │
│  ├── Statistics API (/api/v1/statistics/)                                       │
│  ├── Workflow API (/api/v1/workflow/)                                           │
│  ├── Manual Workflow API (/api/v1/manual/)                                      │
│  └── SSE Streaming (/api/v1/workflow/tasks/{id}/stream)                         │
├────────────────────────────────────────────────────────────────────────────────┤
│  Service Layer (Business Logic + Real-time)                                      │
│  ├── PoemService                                                               │
│  ├── TranslationService                                                        │
│  ├── ManualWorkflowService                                                      │
│  ├── SSEService (Server-Sent Events)                                           │
│  ├── BBRGenerator (Background Briefing Reports)                               │
│  └── VPSWebWorkflowAdapter                                                     │
├────────────────────────────────────────────────────────────────────────────────┤
│  Translation Engine Layer                                                       │
│  ├── 3-Step AI Workflow (Initial → Editor → Revision)                         │
│  ├── Multiple Workflow Modes (Hybrid, Manual, Reasoning, Non-Reasoning)       │
│  ├── BBR Generation Service                                                    │
│  ├── Multi-language Support (EN, CN, JA, KO)                                  │
│  └── LLM Provider Abstraction (Tongyi, DeepSeek, OpenAI)                      │
├────────────────────────────────────────────────────────────────────────────────┤
│  Repository Layer (Data Access + Models)                                        │
│  ├── CRUD Operations                                                          │
│  ├── Database Session Management                                              │
│  ├── Data Validation                                                          │
│  └── Background Briefing Reports Storage                                       │
├────────────────────────────────────────────────────────────────────────────────┤
│  Data Storage Layer                                                             │
│  ├── SQLite Database (Primary Data Store)                                      │
│  │   ├── poems (Original poems and metadata)                                   │
│  │   ├── translations (Translation results and BBR links)                      │
│  │   ├── background_briefing_reports (BBR content and metadata)               │
│  │   ├── ai_logs (AI execution logs and metrics)                              │
│  │   └── human_notes (Human feedback and ratings)                             │
│  └── File System Archive (Original AI Outputs)                                 │
├────────────────────────────────────────────────────────────────────────────────┤
│  Real-time Communication Layer                                                  │
│  ├── Server-Sent Events (SSE) for Live Updates                                │
│  ├── Task State Management                                                     │
│  ├── Progress Tracking                                                         │
│  └── Event Broadcasting                                                        │
└────────────────────────────────────────────────────────────────────────────────┘
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

### **5-Table Schema Architecture**

#### **1. poems** - Poem Metadata
```sql
CREATE TABLE poems (
    id TEXT PRIMARY KEY,                    -- ULID for time-sortable IDs
    title TEXT NOT NULL,                     -- Poem title
    author TEXT NOT NULL,                    -- Poet name
    source_lang TEXT NOT NULL,               -- Source language (ISO code)
    original_text TEXT NOT NULL,             -- Original poem content
    metadata TEXT,                           -- JSON metadata (optional)
    is_selected BOOLEAN DEFAULT FALSE,       -- Star/favorite flag
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
    workflow_mode TEXT NOT NULL,             -- hybrid|manual|reasoning|non_reasoning
    translation_type TEXT NOT NULL,          -- ai|human
    translated_text TEXT NOT NULL,           -- Final translation result
    raw_path TEXT,                           -- Path to original JSON output file
    quality_rating INTEGER DEFAULT 0,        -- 0-10 rating (0 = unrated)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### **3. background_briefing_reports** - BBR Storage (NEW)
```sql
CREATE TABLE background_briefing_reports (
    id TEXT PRIMARY KEY,                    -- ULID for time-sortable IDs
    poem_id TEXT NOT NULL REFERENCES poems(id) ON DELETE CASCADE,
    content TEXT NOT NULL,                   -- BBR content with contextual analysis
    model_provider TEXT,                      -- Model provider and version
    created_at TIMESTAMP NOT NULL,           -- BBR generation timestamp
    input_tokens INTEGER DEFAULT 0,          -- Input tokens used
    output_tokens INTEGER DEFAULT 0,         -- Output tokens generated
    total_tokens INTEGER DEFAULT 0           -- Total tokens used
);
```

#### **4. ai_logs** - AI Workflow Execution Logs
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

#### **5. human_notes** - Human Editorial Notes
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
- **One-to-Many**: `poems` → `background_briefing_reports` (one poem can have multiple BBRs)
- **One-to-Many**: `translations` → `ai_logs` (one translation can have multiple AI execution logs)
- **One-to-Many**: `translations` → `human_notes` (one translation can have multiple human notes)
- **Cascading Deletes**: Deleting a poem automatically removes all related translations, BBRs, and notes
- **BBR Integration**: Each BBR is linked to a poem for contextual translation enhancement

---

## 🔍 Background Briefing Report (BBR) Architecture

### **BBR System Design**

The Background Briefing Report system provides AI-generated contextual analysis to enhance translation quality:

```
┌─────────────────────────────────────────────────────────────────┐
│                    BBR Generation Architecture                 │
├─────────────────────────────────────────────────────────────────┤
│  BBR Trigger (WebUI)                                            │
│  ├── User clicks BBR button on poem detail page                 │
│  ├── AJAX request to /api/v1/bbr/generate                      │
│  └── Loading state displayed to user                           │
├─────────────────────────────────────────────────────────────────┤
│  BBR Generation Service                                         │
│  ├── Poem content analysis                                     │
│  ├── Cultural context detection                                │
│  ├── Linguistic feature extraction                             │
│  └── Historical research integration                           │
├─────────────────────────────────────────────────────────────────┤
│  LLM Provider Integration                                       │
│  ├── Context-enhanced prompt construction                      │
│  ├── Multi-prompt analysis strategy                           │
│  ├── Response parsing and validation                          │
│  └── Token usage tracking                                     │
├─────────────────────────────────────────────────────────────────┤
│  BBR Storage                                                    │
│  ├── Database storage (background_briefing_reports table)     │
│  ├── Metadata tracking (tokens, model, timing)               │
│  └── File archival for complete responses                     │
├─────────────────────────────────────────────────────────────────┤
│  BBR Presentation                                               │
│  ├── Interactive modal with drag/resize                        │
│  ├── Formatted display with sections                          │
│  ├── Close/persist state management                           │
│  └── Integration with translation workflow                    │
└─────────────────────────────────────────────────────────────────┘
```

### **BBR Content Structure**

Each BBR contains:
- **Cultural Context**: Historical period, cultural references, societal context
- **Linguistic Analysis**: Poetic devices, language peculiarities, translation challenges
- **Literary Significance**: Poem's place in literature, critical reception
- **Translation Considerations**: Specific challenges and recommendations

### **BBR Integration Points**

1. **Pre-Translation Enhancement**: BBR generated before translation provides context
2. **Translation Workflow**: BBR content included in translation prompts
3. **Quality Assessment**: BBR used for evaluating translation accuracy
4. **Human Review**: BBR displayed alongside translations for context

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

## 📡 Real-time Architecture (Server-Sent Events)

### **SSE System Design**

VPSWeb implements Server-Sent Events for real-time workflow updates:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Server-Sent Events Architecture              │
├─────────────────────────────────────────────────────────────────┤
│  Client Connection                                              │
│  ├── EventSource connection to /api/v1/workflow/tasks/{id}/stream │
│  ├── 200ms polling interval for responsiveness                 │
│  ├── Automatic reconnection on failures                        │
│  └── Browser-native EventSource API                            │
├─────────────────────────────────────────────────────────────────┤
│  SSE Event Stream                                               │
│  ├── connected: Initial connection established                  │
│  ├── status: General status updates                           │
│  ├── step_change: Workflow step transitions                   │
│  ├── step_start: Step execution begun                         │
│  ├── step_complete: Step finished successfully                │
│  ├── completed: Entire workflow finished                     │
│  ├── error: Error occurred                                   │
│  ├── heartbeat: Keep-alive signals                           │
│  └── timeout: Stream timeout                                  │
├─────────────────────────────────────────────────────────────────┤
│  Server-Side Implementation                                     │
│  ├── FastAPI StreamingResponse                               │
│  ├── Task state management in app.state.tasks                 │
│  ├── JSON-encoded event data                                 │
│  ├── Connection lifecycle management                          │
│  └── Error handling and cleanup                              │
├─────────────────────────────────────────────────────────────────┤
│  Frontend Event Handling                                       │
│  ├── EventSource event listeners                             │
│  ├── Progress bar updates                                    │
│  ├── Step indicator animations                               │
│  ├── Status message display                                 │
│  └── Error notification                                     │
└─────────────────────────────────────────────────────────────────┘
```

### **SSE Event Flow**

1. **Connection**: Client establishes EventSource connection
2. **Authentication**: Task ID validation and authorization
3. **Event Streaming**: Server pushes real-time updates
4. **UI Updates**: Frontend updates interface based on events
5. **Completion**: Stream closes when workflow finishes or errors

### **Technical Implementation**

- **Protocol**: HTTP/1.1 with text/event-stream content type
- **Format**: JSON-encoded data with event type prefixes
- **Reliability**: Automatic reconnection with exponential backoff
- **Performance**: Minimal overhead, efficient for one-way communication

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
src/vpsweb/webui/web/templates/
├── base.html                  # Base template with navigation and responsive design
├── index.html                 # Real-time dashboard with statistics and activity
├── poem_detail.html           # Poem detail with translation workflow and BBR
├── poem_new.html              # New poem creation form
├── poem_compare.html          # Side-by-side translation comparison
├── poets/                     # Poet management templates
├── translations/              # Translation management templates
├── selected/                  # Selected/favorites templates
└── components/                # Reusable UI components
    ├── translation_card.html  # Translation display component
    ├── progress_bar.html      # Real-time progress component
    └── bbr_modal.html         # BBR display modal
```

#### **Frontend Technologies**
- **Tailwind CSS**: Utility-first CSS framework for responsive design
- **Server-Sent Events**: Native browser EventSource API for real-time updates
- **Responsive Design**: Mobile-first approach with progressive enhancement
- **Accessibility**: Semantic HTML5 with ARIA labels and keyboard navigation

#### **Interactive Features**
- **Real-time Progress**: Live translation workflow updates via SSE
- **BBR Modal System**: Draggable, resizable modal for Background Briefing Reports
- **Dynamic Content Loading**: AJAX-based content updates without page refreshes
- **Toast Notifications**: Non-intrusive feedback for user actions
- **Progress Visualization**: Animated progress bars and step indicators

---

## 🔍 API Architecture

### **RESTful API Design**

#### **API Endpoint Organization**
- **Poems API**: `/api/v1/poems/` - Poem CRUD operations and search
- **Translations API**: `/api/v1/translations/` - Translation management
- **Poets API**: `/api/v1/poets/` - Poet management and statistics
- **Statistics API**: `/api/v1/statistics/` - Repository analytics
- **Workflow API**: `/api/v1/workflow/` - Automated translation workflow triggers
- **Manual Workflow API**: `/api/v1/manual/` - Manual translation session management
- **BBR API**: `/api/v1/bbr/` - Background Briefing Report generation
- **SSE API**: `/api/v1/workflow/tasks/{id}/stream` - Real-time event streaming

#### **OpenAPI Documentation**
- **Auto-Generated**: FastAPI automatically creates OpenAPI specifications
- **Interactive Docs**: Swagger UI available at `/docs`
- **ReDoc**: Alternative documentation at `/redoc`
- **Comprehensive Examples**: Request/response examples for all endpoints

#### **SSE Streaming Endpoints**
- **Task Progress**: Real-time workflow updates
- **Event Types**: Connected, status, step changes, completion, errors
- **Connection Management**: Automatic cleanup and timeout handling

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

The VPSWeb v0.7.0 architecture represents a **mature, feature-rich system** that has successfully evolved from a CLI tool into a comprehensive web application with advanced AI capabilities. The integration of Background Briefing Reports, real-time updates via Server-Sent Events, and a sophisticated WebUI demonstrates the system's commitment to user experience and translation quality.

### **Key Architectural Strengths**
1. **Modern Web-Centric Design**: FastAPI-based WebUI with responsive Tailwind CSS styling
2. **Real-time Capabilities**: SSE implementation for live workflow progress updates
3. **AI-Enhanced Translation**: BBR system providing contextual analysis for better translations
4. **Flexible Workflow Options**: Multiple translation modes (Hybrid, Manual, Reasoning, Non-Reasoning)
5. **Multi-language Support**: English, Chinese, Japanese, and Korean with extensible design
6. **Robust Data Architecture**: 5-table schema with proper relationships and cascading deletes
7. **Dual-Storage Strategy**: Optimal balance between database performance and file archival
8. **Modern Technology Stack**: FastAPI, SQLAlchemy 2.0, Pydantic V2, SSE integration

### **Technical Achievements**
- **Seamless Real-time Updates**: Event-driven architecture with minimal overhead
- **Interactive BBR System**: AI-powered contextual analysis with intuitive modal interface
- **3-Step Translation Workflow**: Sophisticated T-E-T process with quality tracking
- **Comprehensive API Design**: RESTful endpoints with SSE streaming capabilities
- **Scalable Architecture**: Ready for multi-user deployment and cloud migration

### **Future Evolution Path**
The architecture is designed for continued enhancement:
- **Advanced AI Features**: Integration of more sophisticated translation models
- **Collaborative Features**: Multi-user workflows and shared translation projects
- **Expanded Language Support**: Additional languages and specialized domains
- **Cloud Integration**: Scalable cloud deployment with managed services
- **Analytics Dashboard**: Advanced translation quality metrics and insights
- **Plugin Architecture**: Extensible system for custom translation workflows

This architecture provides a robust foundation for VPSWeb's position as a leading AI-powered poetry translation platform, combining cutting-edge technology with respect for poetic tradition and cultural nuances.

---

*Architecture documentation current as of v0.7.0 - 2025-12-18*