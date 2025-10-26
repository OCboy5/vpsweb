# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**VPSWeb (Vox Poetica Studio Web)** is a professional AI-powered poetry translation platform that implements a collaborative Translator→Editor→Translator workflow to produce high-fidelity translations between English and Chinese (and other languages).

**Current Status**: v0.3.6 - Translation Display & SSE Enhancement

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
```

### Quality Checks
```bash
./dev-check.sh                         # Run all quality checks
poetry run pytest tests/               # Run tests
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

### Release Management
🚨 **CRITICAL**: All releases MUST follow the strict workflow in `VERSION_WORKFLOW.md`.

**Essential Steps**:
1. Create backup: `./save-version.sh X.Y.Z`
2. Update versions in 3 files + documentation
3. Commit and push to main
4. Create release: `./push-version.sh X.Y.Z "notes"`
5. Verify release on GitHub

### Emergency Procedures
```bash
# List local backup versions
git tag -l "*local*"

# Restore specific version
git checkout v0.2.0-local-2025-10-05
```

### Key Architectural Patterns

#### FastAPI Web Application (v0.3+)
- **SSE Streaming**: Real-time workflow progress via Server-Sent Events
- **Dependency Injection**: Service layer with async database sessions
- **Modular Routing**: Separate API routers for poems, translations, statistics
- **Task Tracking**: In-memory task management via FastAPI app.state

#### Async Database Patterns
- Service layer pattern with dependency injection
- Async session management with proper cleanup
- Cascade operations for related data integrity

### Specialized Documentation
- **WeChat Integration**: [docs/wechat-integration.md](docs/wechat-integration.md)
- **API Patterns**: [docs/api-patterns.md](docs/api-patterns.md)
- **Testing**: [docs/testing.md](docs/testing.md)
- **Future Development**: [docs/future-development.md](docs/future-development.md)

---
## Important Reminders
**NEVER**:
- Announce success before new written code passing all tests
**ALWAYS**:
- Commit working code incrementally
- Update plan documentation as you go
- Learn from existing implementations
- Stop after 3 failed attempts and reassess
- Always use context7 when I need code generation, setup or configuration steps, or library/API documentation. This means you should automatically use the Context7 MCP tools to resolve library id and get library docs without me having to explicitly ask.

**IMPORTANT**: This guide serves as the canonical reference for Claude Code development on VPSWeb. Focus on project-specific architectural patterns and conventions that aren't discoverable from the code structure itself.