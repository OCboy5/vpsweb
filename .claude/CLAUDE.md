# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Your context window will be automatically compacted as it approaches its limit, allowing you to continue working indefinitely from where you left off. Therefore, do not stop tasks early due to token budget concerns. As you approach your token budget limit, save your current progress and state to memory before the context window refreshes. Always be as persistent and autonomous as possible and complete tasks fully, even if the end of your budget is approaching. Never artificially stop any task early regardless of the context remaining.

## VPSWeb: AI-Powered Poetry Translation Platform

**Current Version**: v0.7.0
**Core Concept**: Professional poetry translation with AI-enhanced contextual analysis using Background Briefing Reports (BBR) and real-time collaborative workflows
**Primary Interface**: WebUI at http://127.0.0.1:8000

## Quick Start

### Prerequisites
- Python 3.13
- Poetry (package manager)

### 5-Minute Setup
```bash
git clone https://github.com/OCboy5/vpsweb.git
cd vpsweb
./scripts/setup.sh                # Environment setup
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"  # Required for src layout
./scripts/setup-database.sh init  # Initialize database
```

### Daily Commands
```bash
./scripts/start.sh                # Start FastAPI server (localhost:8000)
./scripts/stop.sh                 # Stop server
poetry run pytest tests/ -v       # Run tests
poetry run black src/ tests/      # Format code
```

## Project Architecture

### Core Components
```
src/vpsweb/
├── core/           # 3-Step T-E-T workflow orchestration
├── models/         # Pydantic data models
├── services/       # LLM provider abstractions & integrations
│   ├── bbr_generator.py  # Background Briefing Report generator
│   └── llm/               # LLM provider factory
├── repository/     # Database layer (5-table schema with BBR)
├── webui/          # FastAPI web application with SSE (PRIMARY INTERFACE)
│   ├── api/        # REST API endpoints
│   ├── services/   # WebUI business logic
│   └── web/        # Templates and static files
└── utils/          # Utilities and helpers
```

### Key Patterns
- **WebUI-First**: Modern web interface is primary user experience
- **3-Step Workflow**: Initial Translation → Editor Review → Translator Revision
- **BBR System**: AI-generated contextual analysis for enhanced translation
- **Provider Factory**: Pluggable LLM providers (Tongyi, DeepSeek, OpenAI-compatible)
- **Async-First**: Full async/await stack with SQLAlchemy 2.0
- **SSE Streaming**: Real-time workflow progress updates via Server-Sent Events
- **Dual Storage**: SQLite + file system for AI outputs
- **Script Management**: Setup and management scripts for easy deployment

## Development Commands

### Daily (Core Development)
```bash
./scripts/clean-start.sh          # Clean restart (stop + start)
poetry run black --check src/     # Check formatting
poetry run flake8 src/            # Lint code
poetry run mypy src/              # Type checking
```

### Weekly (Database & Updates)
```bash
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head             # Apply migrations
sqlite3 repository_root/repo.db ".tables"         # List tables
# Tables: poems, translations, background_briefing_reports, ai_logs, human_notes
```

### Occasional (Advanced)
```bash
./scripts/test.sh                 # Full test suite with coverage
poetry run pytest tests/slow      # Run slow tests
vpsweb translate -i poem.txt -s English -t Chinese -w hybrid  # CLI translation
# Test WebUI with different workflow modes
curl http://127.0.0.1:8000/api/v1/statistics/dashboard  # Check API endpoints
```

## Code Conventions

### Decision Classification
**Trivial** (implement directly):
- Simple bug fixes, documentation updates, single-file changes

**Non-Trivial** (use TodoWrite for planning):
- New features, API changes, architectural refactoring

### File Organization
- **Outputs**: `outputs/json/` and `outputs/markdown/` and `outputs/wechat_articles/`
- **Naming**: `{author}_{title}_{source_target}_{mode}_{date}_{hash}.{format}`
- **Example**: `陶渊明_歸園田居_chinese_english_hybrid_20251012_184234_81e865f8.json`
- **Database**: SQLite at `repository_root/repo.db`
- **Scripts**: All management scripts in `scripts/` directory

## Testing & Quality

### Pre-commit Validation
```bash
poetry run black --check src/ tests/ && poetry run pytest tests/
```

### Test Organization
- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests
- `tests/slow` - Slow tests (mark with `-m 'not slow'` to skip)

## Release Process

🚨 **CRITICAL**: All releases MUST follow `CLAUDE_RELEASE_PROCESS.md`

1. `./save-version.sh X.Y.Z` - Create local backup
2. Run quality checks
3. Update version files
4. Commit and push changes
5. `./push-version.sh X.Y.Z "release notes"` - Create release

**Emergency**: `git tag -l "*local*"` to list backups

## Important References

- **Architecture**: `docs/ARCHITECTURE.md`
- **API Patterns**: `docs/api-patterns.md`
- **Release Process**: `CLAUDE_RELEASE_PROCESS.md`
- **Development Setup**: `docs/Development_Setup.md`
- **User Guide**: `docs/User_Guide.md`

---

## Important Reminders

**NEVER**:
- Announce success before new code passes all tests

**ALWAYS**:
- Commit working code incrementally
- Learn from existing implementations
- Stop after 3 failed attempts and reassess
- Use Context7 MCP tools for library/API documentation without being asked

## v0.7.0 Specific Features

### Translation Workflow Modes
- **Hybrid** (Recommended): Balanced speed and quality
- **Manual**: Human-controlled with external LLM integration
- **Reasoning**: Detailed analysis with explanation generation
- **Non-Reasoning**: Fast, direct translation

### Supported Languages
- English (en)
- Chinese (zh-CN)
- Japanese (ja)
- Korean (ko)

### Key v0.7.0 Features
- **BBR (Background Briefing Reports)**: AI-generated contextual analysis
- **Real-time Updates**: Server-Sent Events for live progress tracking
- **WebUI Primary Interface**: http://127.0.0.1:8000
- **Interactive Modals**: Draggable BBR displays
- **Multi-language Support**: 4 languages with extensible design

**Focus**: Project-specific patterns not discoverable from code structure itself.