# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Your context window will be automatically compacted as it approaches its limit, allowing you to continue working indefinitely from where you left off. Therefore, do not stop tasks early due to token budget concerns. As you approach your token budget limit, save your current progress and state to memory before the context window refreshes. Always be as persistent and autonomous as possible and complete tasks fully, even if the end of your budget is approaching. Never artificially stop any task early regardless of the context remaining.

## Project Overview

**VPSWeb (Vox Poetica Studio Web)** is a professional AI-powered poetry translation platform that implements a collaborative Translator→Editor→Translator workflow to produce high-fidelity translations between English and Chinese (and other languages).

**Current Status**: v0.3.11 - Language Code Standardization & UI Polish

**Tech Stack**: Python, Poetry, FastAPI, SQLAlchemy, Pydantic, AsyncIO, OpenAI-compatible APIs, YAML configuration, Tailwind CSS

## Development Decision Making

### Decision Classification

**Trivial Decisions** (Direct Implementation):
- Simple bug fixes with clear solutions
- Adding comments or improving documentation
- Single-file refactorings that don't affect interfaces
- Configuration value updates

**Non-Trivial Decisions** (Require Planning):
- Adding new workflow steps or modes
- Changing API interfaces or data models
- Modifying core workflow orchestration
- Adding new LLM providers or integration patterns
- Changes affecting multiple configuration files
- Architectural refactoring
- New feature implementations

For non-trivial decisions, use TodoWrite to create structured task plans and get approval before implementation.

## Project Structure

### Core Architecture

#### CLI and Core Translation System
```
src/vpsweb/
├── core/                    # Workflow orchestration
│   ├── workflow.py          # Main 3-step T-E-T workflow
│   └── executor.py          # Step execution engine
├── models/                  # Pydantic data models
│   ├── translation.py       # Translation workflow models
│   └── config.py           # Configuration models
├── services/                # External service integrations
│   ├── llm/               # LLM provider abstractions
│   │   ├── base.py        # Base provider interface
│   │   ├── factory.py     # Provider factory
│   │   └── openai_compatible.py  # OpenAI-compatible provider
│   ├── parser.py          # XML output parsing
│   └── prompts.py         # Prompt management
├── utils/                   # Utilities
│   ├── config_loader.py   # Configuration loading
│   ├── storage.py         # File operations
│   └── logger.py          # Logging configuration
└── __main__.py             # CLI entry point
```

#### Web Application and Repository System (v0.3+)
```
src/vpsweb/
├── webui/                   # FastAPI web application
│   ├── main.py             # FastAPI app entry point with SSE streaming
│   ├── api/                # REST API routers
│   │   ├── poems.py        # Poem management endpoints
│   │   ├── translations.py # Translation management endpoints
│   │   └── statistics.py   # Statistics and analytics endpoints
│   ├── templates/          # Jinja2 HTML templates
│   │   ├── base.html       # Base template with Tailwind CSS
│   │   ├── dashboard.html  # Main dashboard
│   │   └── poems/          # Poem management pages
│   └── static/             # Static assets (CSS, JS)
├── repository/              # Database layer and services
│   ├── database.py         # SQLAlchemy async database setup
│   ├── models.py           # Database ORM models (4-table schema)
│   │   ├── poems.py        # Poem data model
│   │   ├── translations.py # Translation data model
│   │   ├── ai_logs.py      # AI execution logs
│   │   └── human_notes.py  # Human annotations
│   ├── service.py          # Repository business logic
│   └── migrations/         # Alembic database migrations
└── utils/
    └── article_generator.py # WeChat article generation
```

### Key Architectural Patterns
- **3-Step Workflow**: Initial Translation → Editor Review → Translator Revision
- **Provider Abstraction**: Factory pattern for LLM provider flexibility
- **YAML Configuration**: Structured configuration with environment-specific overrides
- **Async Processing**: Full async/await support throughout the stack
- **FastAPI + SQLAlchemy 2.0**: Modern async web framework with async ORM
- **Dual Storage Strategy**: SQLite database for structured data + file system for AI outputs
- **SSE Streaming**: Real-time workflow progress updates via Server-Sent Events
- **Modular Routing**: Separate API routers for different domain areas

## Essential Development Commands

### Environment Setup
```bash
./scripts/setup.sh                     # Automated environment setup
poetry install                          # Install dependencies
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"  # Required for src layout
```

### Database and Server
```bash
./scripts/setup-database.sh init       # Initialize database
./scripts/start.sh                     # Start FastAPI server (localhost:8000)
./scripts/stop.sh                      # Stop server
./scripts/clean-start.sh               # Clean restart (stop + start)
```

### Testing and Quality
```bash
./scripts/test.sh                      # Run test suite with coverage
poetry run pytest tests/ -v            # Run tests with verbose output
poetry run pytest tests/unit/          # Run unit tests only
poetry run pytest tests/integration/   # Run integration tests only
poetry run pytest tests/slow           # Run slow tests (add -m 'not slow' to skip)
poetry run black --check src/ tests/   # Check code formatting
poetry run black src/ tests/           # Format code
poetry run flake8 src/ tests/          # Run linting
poetry run mypy src/                   # Type checking
```

### Database Operations
```bash
# Database migrations (Alembic)
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head                                # Apply migrations
alembic downgrade -1                               # Rollback one migration
alembic current                                    # Show current revision
alembic history                                    # Show migration history

# Direct database operations
sqlite3 repository_root/repo.db ".tables"          # List tables
sqlite3 repository_root/repo.db ".schema poems"    # Show table schema
```

### Core Usage
```bash
vpsweb translate -i poem.txt -s English -t Chinese -w hybrid  # Translation
vpsweb generate-article -j translation.json                   # WeChat articles
```

**Pre-commit validation**: `poetry run black --check src/ tests/ && poetry run pytest tests/`


## Project-Specific Conventions

### Output File Organization
- **Directory**: `outputs/json/` and `outputs/markdown/`
- **Naming**: `{author}_{title}_{source_target}_{mode}_{date}_{hash}.{format}`
- **Examples**: `陶渊明_歸園田居_chinese_english_hybrid_20251012_184234_81e865f8.json`
- **Key Features**: Poet-first naming, no prefixes, log files with "log" suffix

## LLM Provider Integration

### Supported Providers
- **Tongyi (Alibaba Cloud)**: Production ready, qwen-max models
- **DeepSeek**: Advanced reasoning, deepseek-reasoner models
- **OpenAI-Compatible**: Extensible framework for additional providers

### Adding New Providers
1. Create new provider class inheriting from `BaseLLMProvider`
2. Implement required methods: `generate()`, `get_provider_name()`
3. Update `factory.py` to include new provider
4. Add configuration in `models.yaml`
5. Test integration with existing workflow

**See [docs/api-patterns.md](docs/api-patterns.md) for detailed integration guidance.**

## Repository System Architecture (v0.3+)

### Database Design
- **4-Table Schema**: poems → translations → ai_logs → human_notes
- **Async SQLAlchemy 2.0**: Full async/await ORM with cascade operations
- **Dual Storage**: SQLite for structured data + file system for AI outputs
- **File Organization**: Poet-based subdirectory structure

### Configuration Structure
- YAML configuration files with environment variable substitution
- Three workflow modes: reasoning, non_reasoning, hybrid
- Automatic model classification (reasoning vs non-reasoning)
- Key files: `config/default.yaml`, `config/models.yaml`, `config/repository.yaml`

## Quick References

### 🚀 Release Management

🚨 **CRITICAL**: All releases MUST follow the standardized process in `CLAUDE_RELEASE_PROCESS.md`.

**User Instructions**: When user requests a release (e.g., "Create release v0.4.4"), Claude will:

1. **Create local backup**: `./save-version.sh X.Y.Z`
2. **Run quality checks**: Tests, formatting, file verification
3. **Update all version files**: pyproject.toml, __init__.py, __main__.py
4. **Update documentation**: CHANGELOG.md + README.md
5. **Commit and push**: All changes to main branch
6. **Create release**: `./push-version.sh X.Y.Z "release notes"`
7. **Verify success**: Confirm release appears on GitHub

**Key Requirements**:
- ✅ ALWAYS read `CLAUDE_RELEASE_PROCESS.md` first
- ✅ ALWAYS create local backup before changes
- ✅ ALWAYS update README.md with version info
- ✅ NEVER use GitHub Actions workflow (unreliable)
- ✅ ALWAYS use manual `push-version.sh` script
- ✅ ALWAYS verify release before reporting success

### Emergency Procedures
```bash
# List local backup versions
git tag -l "*local*"

# Restore specific version
git checkout v0.2.0-local-2025-10-05
```

### Key Architectural Patterns

##### FastAPI Web Application (v0.3+)
- **SSE Streaming**: Real-time workflow progress via Server-Sent Events
- **Dependency Injection**: Service layer with async database sessions
- **Modular Routing**: Separate API routers for poems, translations, statistics
- **Task Tracking**: In-memory task management via FastAPI app.state
- **Template System**: Jinja2 templates with Tailwind CSS for responsive UI
- **Static Assets**: CSS, JS, and image serving via FastAPI static mounts

#### Async Database Patterns
- Service layer pattern with dependency injection
- Async session management with proper cleanup
- Cascade operations for related data integrity
- Alembic migrations for schema versioning
- Connection pooling with aiosqlite for performance

### Specialized Documentation
- **WeChat Integration**: [docs/wechat-integration.md](docs/wechat-integration.md)
- **API Patterns**: [docs/api-patterns.md](docs/api-patterns.md)
- **Testing**: [docs/testing.md](docs/testing.md)
- **Future Development**: [docs/future-development.md](docs/future-development.md)
- **Development Setup**: [docs/Development_Setup.md](docs/Development_Setup.md)
- **User Guide**: [docs/User_Guide.md](docs/User_Guide.md)
- **Backup & Restore**: [docs/backup_restore_guide.md](docs/backup_restore_guide.md)

## Development Workflow Patterns

### Test-Driven Development
```bash
# Typical development cycle
poetry run pytest tests/unit/test_new_feature.py -v  # Test new feature
poetry run black src/ tests/                         # Format code
poetry run flake8 src/ tests/                        # Lint code
poetry run mypy src/                                 # Type check
git add . && git commit -m "feat: add new feature"   # Commit changes
```

### Debugging Common Issues
```bash
# Database issues
sqlite3 repository_root/repo.db "SELECT COUNT(*) FROM poems;"  # Check data
alembic current                                              # Check migration status

# Import issues
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"                  # Set path
python -c "from vpsweb import __main__; print('OK')"         # Test imports

# Server issues
./scripts/stop.sh                                            # Stop server
pkill -f uvicorn                                             # Kill stray processes
./scripts/clean-start.sh                                     # Clean restart
```
  
---
## Important Reminders
**NEVER**:
- Announce success before new written code passed all tests
**ALWAYS**:
- Commit working code incrementally
- Update plan documentation as you go
- Learn from existing implementations
- Stop after 3 failed attempts and reassess
- Always use context7 when I need code generation, setup or configuration steps, or library/API documentation. This means you should automatically use the Context7 MCP tools to resolve library id and get library docs without me having to explicitly ask.

**IMPORTANT**: This guide serves as the canonical reference for Claude Code development on VPSWeb. Focus on project-specific architectural patterns and conventions that aren't discoverable from the code structure itself.