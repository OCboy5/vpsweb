# VPSWeb Repository v0.3.1 - Development Setup Guide

**Complete development environment setup for contributors and maintainers**

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Development Tools](#development-tools)
4. [Project Structure](#project-structure)
5. [Running Tests](#running-tests)
6. [Code Quality](#code-quality)
7. [Debugging](#debugging)
8. [Contributing Guidelines](#contributing-guidelines)
9. [Development Workflow](#development-workflow)

---

## Prerequisites

### System Requirements

- **Python**: 3.8 or higher (3.13 recommended)
- **Operating System**: macOS, Linux, or Windows (with WSL2)
- **Memory**: 8GB RAM minimum (16GB recommended)
- **Storage**: 2GB free space minimum
- **Git**: Version 2.0 or higher

### Required Software

#### Core Dependencies

```bash
# Python package manager
pip install poetry  # or: pip install --upgrade pip

# Database tools
sqlite3  # Usually comes with Python

# Git (if not already installed)
# macOS: xcode-select --install
# Ubuntu: sudo apt-get install git
# Windows: Download from git-scm.com
```

#### Optional Development Tools

```bash
# Development database tools
brew install sqlitebrowser  # macOS
# apt-get install sqlitebrowser  # Ubuntu

# API testing
brew install httpie          # macOS
# apt-get install httpie         # Ubuntu
# pip install httpie           # Cross-platform

# Code quality tools
pip install black isort flake8 mypy pytest pytest-cov

# Documentation
pip install mkdocs mkdocs-material
```

---

## Environment Setup

### 1. Clone the Repository

```bash
# Clone the repository
git clone <repository-url>
cd vpsweb/vpsweb

# Verify Python version
python --version  # Should be 3.8+

# Verify Poetry
poetry --version
```

### 2. Install Dependencies

#### Using Poetry (Recommended)

```bash
# Install project dependencies
poetry install

# Install development dependencies
poetry install --dev

# Activate virtual environment
poetry shell
```

#### Using pip (Alternative)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate   # Windows

# Install dependencies
pip install -e .
pip install -e ".[dev]"  # Development dependencies
```

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.local.template .env.local

# Edit environment file
nano .env.local
```

#### Development Environment Configuration

```bash
# .env.local
REPO_ROOT=./repository_root
REPO_DATABASE_URL=sqlite+aiosqlite:///./repository_root/repo.db
REPO_HOST=127.0.0.1
REPO_PORT=8000
REPO_DEBUG=true          # Enable debug mode
DEV_MODE=true             # Development mode
VERBOSE_LOGGING=true     # Verbose logging
LOG_FORMAT=text

# LLM Provider Configuration (use test keys for development)
TONGYI_API_KEY=your_development_api_key
DEEPSEEK_API_KEY=your_development_api_key

# Development Settings
TEST_MODE=true
MOCK_API_RESPONSES=true   # Enable mock responses for testing
```

### 4. Database Setup

```bash
# Set Python path
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Run database migrations
cd src/vpsweb/repository
alembic upgrade head
cd - > /dev/null

# Verify database
ls -la repository_root/
```

### 5. Verify Installation

```bash
# Test imports
python -c "
from vpsweb.webui.main import app
from vpsweb.repository.models import Poem
print('✅ Imports successful')
"

# Start development server
python -m vpsweb.webui.main
```

Visit: **http://127.0.0.1:8000**

---

## Development Tools

### IDE Configuration

#### VS Code (Recommended)

Install extensions:
- **Python** (Microsoft)
- **Pylance** (Microsoft)
- **Black Formatter** (Microsoft)
- **SQLite Viewer** (alexcv)
- **GitLens** (GitKraken)

VS Code settings (`.vscode/settings.json`):

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true,
        "*.egg-info": true
    }
}
```

#### PyCharm

1. Open project directory
2. Configure Python interpreter (use poetry venv)
3. Enable pytest integration
4. Configure code style: Black, isort

### Command Line Tools

#### Essential Commands

```bash
# Start development server
python -m vpsweb.webui.main

# Start with auto-reload
uvicorn vpsweb.webui.main:app --host 127.0.0.1 --port 8000 --reload

# Run tests
pytest tests/ -v

# Code formatting
black src/ tests/
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/

# Database operations
cd src/vpsweb/repository
alembic current
alembic revision --autogenerate -m "description"
alembic upgrade head
```

#### Helpful Aliases

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# VPSWeb development aliases
alias vpsweb="cd $(find ~ -name vpsweb -type d 2>/dev/null | head -1)"
alias vpsweb-start="python -m vpsweb.webui.main"
alias vpsweb-test="pytest tests/ -v"
alias vpsweb-format="black src/ tests/ && isort src/ tests/"
alias vpsweb-check="black --check src/ tests/ && flake8 src/ tests/ && mypy src/"
alias vpsweb-migrate="cd src/vpsweb/repository && alembic upgrade head"
```

---

## Project Structure

### Source Code Organization

```
src/vpsweb/
├── __init__.py
├── __main__.py                 # CLI entry point
├── models/                      # Pydantic data models
│   ├── __init__.py
│   ├── config.py               # Configuration models
│   ├── translation.py          # Translation workflow models
│   └── wechat.py               # WeChat integration models
├── core/                        # Core functionality
│   ├── __init__.py
│   ├── workflow.py              # Translation workflow engine
│   ├── executor.py              # Step execution engine
│   └── config_loader.py         # Configuration management
├── services/                    # External service integrations
│   ├── __init__.py
│   ├── llm/                     # LLM provider abstractions
│   │   ├── __init__.py
│   │   ├── base.py              # Base provider interface
│   │   ├── factory.py           # Provider factory
│   │   └── openai_compatible.py # OpenAI-compatible provider
│   ├── parser.py                # XML output parsing
│   └── prompts.py               # Prompt management
├── utils/                       # Utilities
│   ├── __init__.py
│   ├── config_loader.py         # Configuration loading
│   ├── storage.py               # File operations
│   ├── logger.py                # Logging configuration
│   ├── datetime_utils.py        # Date/time utilities
│   ├── file_storage.py          # File storage utilities
│   ├── language_mapper.py       # Language code mapping
│   └── ulid_utils.py            # ULID generation utilities
└── repository/                  # Repository system
    ├── __init__.py
    ├── models.py                # SQLAlchemy ORM models
    ├── schemas.py               # Pydantic schemas
    ├── database.py              # Database configuration
    ├── settings.py              # Repository settings
    ├── crud/                    # CRUD operations
    │   ├── __init__.py
    │   ├── poems.py              # Poem CRUD operations
    │   ├── translations.py       # Translation CRUD operations
    │   ├── ai_logs.py            # AI log CRUD operations
    │   └── human_notes.py        # Human note CRUD operations
    └── migrations/              # Alembic migrations
        ├── versions/
        └── env.py
```

### Web Interface Structure

```
src/vpsweb/webui/
├── __init__.py
├── main.py                      # FastAPI application
├── config.py                    # WebUI configuration
├── schemas.py                   # WebUI-specific schemas
├── api/                         # API endpoints
│   ├── __init__.py
│   ├── poems.py                 # Poem management endpoints
│   ├── translations.py          # Translation endpoints
│   ├── workflow.py              # Workflow management endpoints
│   └── statistics.py            # Statistics endpoints
├── services/                    # Business logic services
│   ├── __init__.py
│   ├── vpsweb_adapter.py        # VPSWeb integration adapter
│   ├── poem_service.py          # Poem management service
│   └── translation_service.py   # Translation service
└── web/                         # Web templates and static files
    ├── templates/               # Jinja2 templates
    │   ├── base.html            # Base template
    │   ├── index.html           # Dashboard
    │   ├── poem_detail.html     # Poem detail page
    │   ├── poem_new.html        # New poem form
    │   ├── poem_compare.html    # Comparison view
    │   └── api_docs.html        # API documentation
    └── static/                   # Static files (CSS, JS)
```

### Configuration Files

```
config/
├── default.yaml                 # Default workflow configuration
├── models.yaml                  # LLM provider configurations
└── wechat.yaml                  # WeChat integration configuration
```

---

## Running Tests

### Test Suite Overview

```bash
# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/test_models.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run with specific markers
pytest tests/ -m unit -v
pytest tests/ -m integration -v
pytest tests/ -m slow -v
```

### Test Categories

#### Unit Tests
- Model validation tests
- Service layer tests
- Utility function tests

#### Integration Tests
- API endpoint tests
- Database operation tests
- Workflow integration tests

#### End-to-End Tests
- Complete workflow tests
- Web interface tests
- Background task tests

### Writing Tests

#### Test Structure

```python
# tests/test_models.py
import pytest
from vpsweb.models.translation import TranslationRequest

class TestTranslationRequest:
    def test_valid_translation_request(self):
        """Test valid translation request creation"""
        request = TranslationRequest(
            source_text="Hello world",
            source_lang="en",
            target_lang="zh-CN"
        )
        assert request.source_text == "Hello world"
        assert request.source_lang == "en"
        assert request.target_lang == "zh-CN"

    def test_invalid_language_code(self):
        """Test invalid language code validation"""
        with pytest.raises(ValueError):
            TranslationRequest(
                source_text="Hello world",
                source_lang="invalid",
                target_lang="zh-CN"
            )
```

#### Fixtures

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from vpsweb.repository.models import Base
from vpsweb.repository.crud.poems import PoemCRUD

@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture
def poem_crud(test_db):
    """Create poem CRUD instance"""
    return PoemCRUD(test_db)
```

### Test Database

Tests use in-memory SQLite for isolation:

```python
# Test database setup
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
```

---

## Code Quality

### Code Formatting

#### Black (Code Formatter)

```bash
# Format all code
black src/ tests/

# Check formatting without changes
black --check src/ tests/

# Format specific files
black src/vpsweb/models/translation.py
```

#### isort (Import Sorting)

```bash
# Sort imports
isort src/ tests/

# Check imports
isort --check-only src/ tests/
```

### Code Linting

#### flake8

```bash
# Lint all code
flake8 src/ tests/

# Lint with configuration
flake8 --config=.flake8 src/ tests/
```

Configuration (`.flake8`):

```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude =
    .git,
    __pycache__,
    .venv,
    venv,
    build,
    dist
per-file-ignores =
    __init__.py: F401
```

#### mypy (Type Checking)

```bash
# Type check all code
mypy src/

# Type check specific module
mypy src/vpsweb/models/

# Type check with strict mode
mypy --strict src/
```

Configuration (`mypy.ini`):

```ini
[mypy]
python_version = 3.8
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True

[mypy-tests.*]
disallow_untyped_defs = False
```

### Pre-commit Hooks

Install pre-commit:

```bash
pip install pre-commit
pre-commit install
```

Configuration (`.pre-commit-config.yaml`):

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest tests/
        language: system
        pass_filenames: false
        always_run: true
```

---

## Debugging

### Development Server Debugging

#### Debug Mode

```bash
# Enable debug mode
export REPO_DEBUG=true
export VERBOSE_LOGGING=true

# Start with debugging
python -m vpsweb.webui.main
```

#### uvicorn Debug Mode

```bash
# Start with debug settings
uvicorn vpsweb.webui.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload \
  --log-level debug
```

### Python Debugger

#### Using pdb

```python
import pdb; pdb.set_trace()

# Or in FastAPI endpoint
@app.get("/debug")
async def debug_endpoint():
    import pdb; pdb.set_trace()
    return {"message": "Debug breakpoint"}
```

#### Using VS Code Debugger

Configuration (`.vscode/launch.json`):

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/vpsweb/webui/main.py",
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/src"
            }
        }
    ]
}
```

### Database Debugging

#### SQLite Browser

```bash
# Open database in SQLite CLI
sqlite3 repository_root/repo.db

# Common commands
.tables
.schema poems
SELECT * FROM poems LIMIT 5;
```

#### Alembic Debugging

```bash
# Check current migration
alembic current

# Check migration history
alembic history

# Generate migration
alembic revision --autogenerate -m "debug migration"

# Upgrade to specific revision
alembic upgrade +1
```

### API Debugging

#### HTTP Client Testing

```bash
# Using curl
curl -X GET "http://127.0.0.1:8000/health" -H "Accept: application/json"

# Using httpie
http GET 127.0.0.1:8000/health Accept:application/json

# POST request with data
http POST 127.0.0.1:8000/api/v1/poems/ \
  poet_name="Test Poet" \
  poem_title="Test Poem" \
  source_language="en" \
  original_text="Hello world" \
  target_language="zh-CN"
```

#### API Documentation

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **OpenAPI JSON**: http://127.0.0.1:8000/openapi.json

### Logging

#### Configure Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Use in code
logger = logging.getLogger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

#### Log Files

```bash
# View application logs
tail -f logs/vpsweb.log

# Filter logs by level
grep "ERROR" logs/vpsweb.log
grep "DEBUG" logs/vpsweb.log
```

---

## Contributing Guidelines

### Code Style

Follow these guidelines for consistent code style:

#### Python Code

```python
# Import order
import os
import sys
from typing import List, Optional

import fastapi
from pydantic import BaseModel

from vpsweb.models.config import Config

# Class definitions
class PoemModel(BaseModel):
    """Model representing a poem in the repository."""

    poet_name: str
    poem_title: str
    source_language: str
    original_text: str
    metadata_json: Optional[str] = None

    class Config:
        """Pydantic configuration."""
        validate_assignment = True

# Function definitions
def create_poem(data: dict) -> PoemModel:
    """Create a new poem from dictionary data.

    Args:
        data: Dictionary containing poem data

    Returns:
        PoemModel: Created poem model instance

    Raises:
        ValueError: If required fields are missing
    """
    if not data.get('poet_name'):
        raise ValueError("Poet name is required")

    return PoemModel(**data)
```

#### Documentation

```python
def complex_function(
    param1: str,
    param2: Optional[int] = None,
    *,
    keyword_param: bool = False
) -> dict:
    """Complex function with comprehensive documentation.

    This function demonstrates proper documentation format with
    detailed parameter descriptions and return value information.

    Args:
        param1: Description of the first parameter
        param2: Optional integer parameter for configuration
        keyword_param: Keyword-only parameter for special behavior

    Returns:
        Dictionary containing operation results

    Raises:
        ValueError: When param1 is empty or invalid
        TypeError: When param2 is not an integer (if provided)

    Example:
        >>> result = complex_function("test", 42, keyword_param=True)
        >>> print(result['status'])
        'success'
    """
    # Implementation here
    pass
```

### Git Workflow

#### Branch Naming

- `feature/description`: New features
- `fix/description`: Bug fixes
- `docs/description`: Documentation changes
- `refactor/description`: Code refactoring

#### Commit Messages

```
type(scope): description

[optional body]

[optional footer]
```

Examples:
```
feat(api): add poem search endpoint

Add comprehensive search functionality for poems including
full-text search and filtering options.

- Add POST /api/v1/poems/search endpoint
- Implement text-based search
- Add language and date filtering
- Update API documentation

Closes #123
```

```
fix(database): resolve migration issue

Fix foreign key constraint violation during database migration
by updating the migration order and adding proper constraints.

Fixes #124
```

### Pull Request Process

#### Before Submitting

1. **Code Quality**: Run all quality checks
   ```bash
   black --check src/ tests/
   flake8 src/ tests/
   mypy src/
   pytest tests/
   ```

2. **Documentation**: Update relevant documentation
   - API changes: Update OpenAPI docs
   - New features: Update user guide
   - Bug fixes: Update troubleshooting section

3. **Testing**: Ensure all tests pass
   ```bash
   pytest tests/ -v --cov=src
   ```

#### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally
```

---

## Development Workflow

### 1. Feature Development

```bash
# Create feature branch
git checkout -b feature/new-feature

# Implement feature
# (code implementation)

# Run quality checks
make check

# Run tests
make test

# Commit changes
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/new-feature
```

### 2. Bug Fixing

```bash
# Create bug fix branch
git checkout -b fix/bug-description

# Reproduce bug
# (write failing test)

# Fix bug
# (code implementation)

# Verify fix
make test

# Commit fix
git add .
git commit -m "fix: resolve bug description"

# Push and create PR
git push origin fix/bug-description
```

### 3. Testing Workflow

```bash
# Run all tests
pytest tests/ -v

# Run specific test category
pytest tests/ -m unit -v
pytest tests/ -m integration -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run performance tests
pytest tests/ -m performance -v
```

### 4. Release Process

```bash
# Update version
# (edit version in pyproject.toml)

# Update documentation
# (update docs/)

# Run final checks
make check
make test

# Tag release
git tag v0.3.1

# Push changes
git push origin main
git push origin v0.3.1
```

### Development Commands

Create a `Makefile` for common commands:

```makefile
.PHONY: help install check test format lint clean dev

help:
	@echo "Available commands:"
	@echo "  install     Install dependencies"
	@echo "  check       Run all quality checks"
	@echo "  test        Run tests"
	@echo "  format      Format code"
	@echo "  lint        Run linting"
	@echo "  clean       Clean cache files"
	@echo "  dev         Start development server"

install:
	poetry install --dev

check:
	black --check src/ tests/
	flake8 src/ tests/
	mypy src/

test:
	pytest tests/ -v --cov=src

format:
	black src/ tests/
	isort src/ tests/

lint:
	flake8 src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

dev:
	python -m vpsweb.webui.main
```

Use with:
```bash
make help    # Show available commands
make install # Install dependencies
make test    # Run tests
make dev     # Start development server
```

---

## Troubleshooting

### Common Development Issues

#### Import Errors

```bash
# Check Python path
echo $PYTHONPATH

# Set Python path
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Test imports
python -c "from vpsweb.webui.main import app"
```

#### Database Issues

```bash
# Reset database
rm repository_root/repo.db
cd src/vpsweb/repository
alembic upgrade head

# Check database integrity
sqlite3 repository_root/repo.db "PRAGMA integrity_check;"
```

#### Test Failures

```bash
# Run specific test
pytest tests/test_models.py::TestPoemModel::test_valid_poem -v

# Run with debugging
pytest tests/test_models.py::TestPoemModel::test_valid_poem -v -s

# Run with coverage
pytest tests/ --cov=src/vpsweb.models --cov-report=html
```

#### Performance Issues

```bash
# Profile application
python -m cProfile -o profile.stats -m vpsweb.webui.main

# Analyze profile
python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative')
p.print_stats(20)
"
```

### Getting Help

#### Internal Resources

- **Code Documentation**: Read docstrings and type hints
- **Test Files**: Check tests/ for usage examples
- **Configuration**: Review config/ files
- **Logs**: Check application logs for errors

#### External Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/
- **Pydantic Documentation**: https://pydantic-docs.helpmanual.io/
- **Alembic Documentation**: https://alembic.sqlalchemy.org/

---

**Happy coding! 🚀**

For questions or issues, please refer to the project documentation or create an issue in the repository.