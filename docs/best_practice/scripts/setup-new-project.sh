#!/bin/bash
# Automated New Project Setup Script
# Based on VPSWeb project success patterns

set -e

echo "🚀 Setting up new Claude Code project with VPSWeb best practices"
echo "================================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    local status=$1
    local message=$2

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}❌ $message${NC}"
    elif [ "$status" = "INFO" ]; then
        echo -e "${BLUE}ℹ️  $message${NC}"
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠️  $message${NC}"
    fi
}

# Verify we're in the right directory
if [ ! -d "docs" ] || [ ! -d "src" ]; then
    print_status "WARN" "This doesn't look like a project directory. Creating structure..."
fi

# 1. Create project structure
print_status "INFO" "Creating project structure..."
mkdir -p src/{project_name,tests}
mkdir -p tests/{unit,integration,performance,fixtures}
mkdir -p docs/{claudecode,api,user_guide}
mkdir -p scripts/{setup,testing,deployment}
mkdir -p config
mkdir -p outputs/{json,markdown,logs}

# 2. Create essential configuration files
print_status "INFO" "Creating configuration files..."

# pyproject.toml
cat > pyproject.toml << 'EOF'
[tool.poetry]
name = "your-project-name"
version = "0.1.0"
description = "Your project description"
authors = ["Your Name <your.email@example.com>"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.11"
pydantic = "^2.0"
asyncio = "^3.4"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
pytest-cov = "^4.0"
pytest-asyncio = "^0.21"
black = "^23.0"
flake8 = "^6.0"
mypy = "^1.0"
pre-commit = "^3.0"
safety = "^2.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'

[tool.isort]
profile = "black"
multi_line_output = 3

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=80"
asyncio_mode = "auto"
EOF

# pytest.ini
cat > pytest.ini << 'EOF'
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    --strict-markers
    --disable-warnings
    -v
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
    performance: Performance tests
EOF

# .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203,W503]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
EOF

# .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.coverage
htmlcov/
.pytest_cache/
.tox/

# Project specific
outputs/
repository_root/
*.log
.env
.envrc

# OS
.DS_Store
Thumbs.db
EOF

# 3. Create test infrastructure
print_status "INFO" "Creating test infrastructure..."

cat > tests/conftest.py << 'EOF'
import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_config():
    """Sample configuration for testing"""
    return {
        "provider": "test_provider",
        "model": "test-model",
        "max_tokens": 1000,
        "temperature": 0.7
    }

@pytest.fixture
def mock_llm_factory():
    """Mock LLM factory for testing"""
    factory = Mock()
    provider = AsyncMock()
    provider.generate.return_value = {"content": "test response"}
    factory.get_provider.return_value = provider
    return factory

@pytest.fixture
def sample_data():
    """Sample data for testing"""
    return {
        "id": "test_001",
        "name": "Test Item",
        "value": 42,
        "metadata": {"created_at": "2025-01-02"}
    }
EOF

# 4. Create core component template
print_status "INFO" "Creating core component template..."

mkdir -p src/project_name
cat > src/project_name/__init__.py << 'EOF'
"""Your project package following VPSWeb patterns"""

__version__ = "0.1.0"
EOF

cat > src/project_name/core.py << 'EOF'
"""Core component following VPSWeb patterns"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import asyncio
import logging

logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Configuration with type safety"""
    provider: str
    model: str
    max_tokens: int = 1000
    temperature: float = 0.7

class CoreComponent:
    """Core component with dependency injection and error handling"""

    def __init__(self, config: Config, validator=None, error_handler=None):
        self.config = config
        self.validator = validator or self._default_validator
        self.error_handler = error_handler or self._default_error_handler

    def _default_validator(self, data: Dict[str, Any]) -> bool:
        """Default validation logic"""
        return bool(data and isinstance(data, dict))

    def _default_error_handler(self, error: Exception, context: str) -> Dict[str, Any]:
        """Default error handling"""
        logger.error(f"Error in {context}: {error}")
        return {
            "status": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context
        }

    async def process_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data with validation and error handling"""
        try:
            if not self.validator(input_data):
                raise ValueError("Invalid input data")

            # Your core logic here
            result = {
                "status": "success",
                "processed_data": input_data,
                "config": {
                    "provider": self.config.provider,
                    "model": self.config.model
                }
            }

            logger.info(f"Successfully processed data: {len(input_data)} items")
            return result

        except Exception as e:
            return self.error_handler(e, "process_data")

    def get_status(self) -> Dict[str, Any]:
        """Get component status"""
        return {
            "status": "healthy",
            "config": {
                "provider": self.config.provider,
                "model": self.config.model
            },
            "version": "0.1.0"
        }
EOF

# 5. Create initial tests
print_status "INFO" "Creating initial tests..."

cat > tests/unit/test_core.py << 'EOF'
import pytest
from unittest.mock import Mock, AsyncMock
from project_name.core import CoreComponent, Config

class TestCoreComponent:
    """Test core component with VPSWeb patterns"""

    @pytest.fixture
    def sample_config(self):
        return Config(
            provider="test_provider",
            model="test-model",
            max_tokens=1500,
            temperature=0.8
        )

    @pytest.fixture
    def core_component(self, sample_config):
        return CoreComponent(sample_config)

    @pytest.mark.unit
    def test_component_initialization(self, core_component, sample_config):
        """Test component initialization with dependency injection"""
        assert core_component.config == sample_config
        assert core_component.validator is not None
        assert core_component.error_handler is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_data_success(self, core_component):
        """Test successful data processing"""
        input_data = {"test": "data", "value": 123}

        result = await core_component.process_data(input_data)

        assert result["status"] == "success"
        assert result["processed_data"] == input_data
        assert result["config"]["provider"] == "test_provider"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_data_validation_failure(self, core_component):
        """Test data validation failure"""
        invalid_data = None

        result = await core_component.process_data(invalid_data)

        assert result["status"] == "error"
        assert result["error_type"] == "ValueError"

    @pytest.mark.unit
    def test_get_status(self, core_component):
        """Test status reporting"""
        status = core_component.get_status()

        assert status["status"] == "healthy"
        assert status["config"]["provider"] == "test_provider"
        assert status["version"] == "0.1.0"
EOF

# 6. Create scripts directory with essential scripts
print_status "INFO" "Creating development scripts..."

cat > scripts/quality-gate.sh << 'EOF'
#!/bin/bash
# Quality gate validation script

set -e

echo "🔍 Running Quality Gate Validation"
echo "================================="

# Code formatting
if poetry run black --check src/ tests/; then
    echo "✅ Code formatting OK"
else
    echo "❌ Code formatting issues found"
    echo "Run 'poetry run black src/ tests/' to fix"
    exit 1
fi

# Linting
if poetry run flake8 src/ tests/; then
    echo "✅ Linting OK"
else
    echo "❌ Linting issues found"
    exit 1
fi

# Type checking
if poetry run mypy src/; then
    echo "✅ Type checking OK"
else
    echo "❌ Type checking issues found"
    exit 1
fi

# Tests
if poetry run pytest tests/ -v --cov=src --cov-fail-under=80; then
    echo "✅ All tests passing"
else
    echo "❌ Test failures or insufficient coverage"
    exit 1
fi

echo "🎉 All quality gates passed!"
EOF

chmod +x scripts/quality-gate.sh

cat > scripts/daily-setup.sh << 'EOF'
#!/bin/bash
# Daily development setup script

echo "🌅 Daily Development Setup"
echo "========================="

# Verify environment
poetry install

# Set environment
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Quick health check
python -c "from project_name.core import CoreComponent; print('✅ Import check passed')"

echo "✅ Daily setup complete!"
EOF

chmod +x scripts/daily-setup.sh

# 7. Create initial documentation
print_status "INFO" "Creating documentation..."

cat > README.md << 'EOF'
# Your Project Name

A Claude Code project following VPSWeb best practices.

## Quick Start

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Set environment:
   ```bash
   export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
   ```

3. Run tests:
   ```bash
   poetry run pytest tests/ -v
   ```

4. Run quality gates:
   ```bash
   ./scripts/quality-gate.sh
   ```

## Development

Follow the daily workflow:
```bash
./scripts/daily-setup.sh
```

## Documentation

See [docs/best_practice/](docs/best_practice/) for comprehensive development guidance.

## Project Structure

- `src/project_name/` - Main source code
- `tests/` - Test suite (unit, integration, performance)
- `docs/` - Documentation and project tracking
- `scripts/` - Development automation scripts
EOF

# 8. Initialize Poetry and install dependencies
print_status "INFO" "Initializing Poetry and installing dependencies..."
poetry install

# 9. Run initial quality check
print_status "INFO" "Running initial quality check..."
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Test basic functionality
python -c "from project_name.core import CoreComponent, Config; print('✅ Import check passed')"

# Run formatting
poetry run black src/ tests/

# Run tests
if poetry run pytest tests/ -v --cov=src; then
    print_status "PASS" "Initial tests passing"
else
    print_status "FAIL" "Initial tests failing"
    exit 1
fi

# 10. Create project tracking documents
print_status "INFO" "Setting up project tracking..."

if [ -d "docs/best_practice/templates" ]; then
    cp docs/best_practice/templates/phase_tracking.md docs/claudecode/current_phase.md 2>/dev/null || echo "Templates not found, creating basic tracking"

    # Create basic tracking if templates not available
    mkdir -p docs/claudecode
    cat > docs/claudecode/current_phase.md << 'EOF'
# Project Phase Tracking

**Project Name**: Your Project Name
**Project Start Date**: $(date +%Y-%m-%d)
**Current Phase**: Phase 0: Test Infrastructure
**Overall Status**: In Progress

## Phase Progress Overview

| Phase | Status | Start Date | Completion | Test Success | Code Quality |
|-------|--------|------------|------------|--------------|--------------|
| Phase 0: Test Infrastructure | 🟡 In Progress | $(date +%Y-%m-%d) | - | 1/1 (100%) | A+ |

## Today's Achievements
- [x] Project structure created
- [x] Test infrastructure initialized
- [x] First component and tests implemented
- [x] Quality gates established
- [x] Documentation structure created

## Next Steps
- [ ] Complete MCP tools setup and practice
- [ ] Implement additional features
- [ ] Set up CI/CD pipeline
- [ ] Add comprehensive documentation
EOF
fi

# 11. Final validation
print_status "INFO" "Running final validation..."

echo ""
print_status "PASS" "Project setup complete!"
echo ""
echo "📁 Project structure created:"
echo "   src/project_name/ - Core components"
echo "   tests/ - Test suite (unit, integration)"
echo "   docs/ - Documentation and tracking"
echo "   scripts/ - Development automation"
echo ""
echo "🚀 Quick start commands:"
echo "   poetry install                    # Install dependencies"
echo "   export PYTHONPATH=\"\$(pwd)/src:\$PYTHONPATH\"  # Set Python path"
echo "   poetry run pytest tests/ -v      # Run tests"
echo "   ./scripts/quality-gate.sh        # Run quality gates"
echo ""
print_status "INFO" "📚 Next steps:"
echo "   1. Read docs/best_practice/NEW_PROJECT_STARTUP_GUIDE.md"
echo "   2. Complete MCP tools practice exercises"
echo "   3. Follow the daily workflow from docs/best_practice/04-development-workflow.md"
echo ""
print_status "PASS" "🎉 Your project is ready for VPSWeb-level development!"