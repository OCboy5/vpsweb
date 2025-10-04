# Contributing to VPSWeb

Thank you for your interest in contributing to VPSWeb! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Release Process](#release-process)

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct:

- Be respectful and inclusive
- Exercise consideration and respect in your speech and actions
- Attempt collaboration before conflict
- Refrain from demeaning, discriminatory, or harassing behavior
- Be mindful of your surroundings and fellow participants

## Getting Started

### Prerequisites

- Python 3.9+
- Poetry (for dependency management)
- Git

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/vpsweb.git
   cd vpsweb
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/original-owner/vpsweb.git
   ```

## Development Setup

### 1. Install Dependencies

```bash
# Install with Poetry
poetry install

# Install development dependencies
poetry install --with dev

# Activate the virtual environment
poetry shell
```

### 2. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# TONGYI_API_KEY=your-key-here
# DEEPSEEK_API_KEY=your-key-here
```

### 3. Verify Installation

```bash
# Test CLI (PYTHONPATH is automatically loaded from .env)
vpsweb --help

# Test basic functionality
vpsweb translate --input examples/poems/short_english.txt --source English --target Chinese --dry-run

# Run tests (when available)
pytest tests/
```

## Code Style

We follow strict code style guidelines to maintain code quality and consistency.

### Python Style Guide

We use:
- **Black** for code formatting
- **Flake8** for linting
- **isort** for import sorting
- **mypy** for type checking

### Formatting Commands

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Pre-commit Hooks

We use pre-commit hooks to automatically format and lint code:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

### Docstring Style

Use Google/NumPy style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """Brief description of function.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When something goes wrong
        TypeError: When type is incorrect

    Example:
        >>> function_name("test", 42)
        True
    """
    pass
```

## Testing

### Test Structure

- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Fixtures: `tests/fixtures/`

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/

# Run with coverage
pytest --cov=vpsweb --cov-report=html

# Run specific test file
pytest tests/unit/test_workflow.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_translation"
```

### Writing Tests

Follow these guidelines for writing tests:

1. Use descriptive test names
2. Test both success and failure cases
3. Use fixtures for common setup
4. Mock external dependencies
5. Keep tests focused and fast

Example test structure:

```python
import pytest
from unittest.mock import patch

class TestTranslationWorkflow:
    """Test suite for translation workflow."""

    def test_workflow_initialization(self, sample_workflow_config):
        """Test workflow initialization with valid config."""
        workflow = TranslationWorkflow(sample_workflow_config)
        assert workflow.config == sample_workflow_config

    @pytest.mark.asyncio
    async def test_workflow_execution(self, sample_translation_input, mock_llm_factory):
        """Test complete workflow execution."""
        workflow = TranslationWorkflow(sample_workflow_config)
        result = await workflow.execute(sample_translation_input)

        assert result.workflow_id is not None
        assert result.total_tokens > 0
```

## Documentation

### Documentation Structure

- `README.md`: Project overview and quick start
- `docs/`: Detailed documentation
  - `configuration.md`: Configuration guide
  - `api_reference.md`: Python API reference
  - `PSD_CC.md`: Product specifications
- Inline docstrings: Code documentation

### Updating Documentation

1. Update inline docstrings when modifying code
2. Update relevant documentation files
3. Ensure all examples work
4. Test documentation examples

### Building Documentation

```bash
# Generate API documentation (if using Sphinx)
cd docs
make html
```

## Pull Request Process

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Your Changes

- Follow code style guidelines
- Write tests for new functionality
- Update documentation
- Ensure all tests pass

### 3. Commit Your Changes

Use conventional commit messages:

```bash
git add .
git commit -m "feat: add new translation provider"
git commit -m "fix: resolve parsing error in XML responses"
git commit -m "docs: update configuration examples"
git commit -m "test: add integration tests for CLI"
```

Commit types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `style`: Code style changes
- `perf`: Performance improvements
- `chore`: Maintenance tasks

### 4. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:

- Clear title and description
- Reference to related issues
- Summary of changes
- Test results

### 5. PR Review Process

- At least one maintainer must approve
- All tests must pass
- Code must follow style guidelines
- Documentation must be updated

## Issue Reporting

### Bug Reports

When reporting bugs, include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Step-by-step reproduction instructions
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**: Python version, OS, dependencies
6. **Logs**: Relevant error logs or stack traces

### Feature Requests

For feature requests, include:

1. **Problem**: The problem you're trying to solve
2. **Solution**: Your proposed solution
3. **Alternatives**: Any alternative solutions considered
4. **Use Case**: How this feature would be used

### Issue Templates

Use the provided issue templates on GitHub for consistent reporting.

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Steps

1. **Update Version**: Update version in `pyproject.toml`
2. **Update Changelog**: Add release notes to `CHANGELOG.md`
3. **Create Release Branch**: `git checkout -b release/vX.Y.Z`
4. **Run Tests**: Ensure all tests pass
5. **Create Tag**: `git tag vX.Y.Z`
6. **Push**: `git push origin vX.Y.Z`
7. **Create GitHub Release**: With release notes
8. **Publish to PyPI**: `poetry publish --build`

## Project Structure

```
vpsweb/
├── src/vpsweb/           # Main package source
│   ├── core/            # Workflow orchestration
│   ├── models/          # Data models (Pydantic)
│   ├── services/        # External service integrations
│   └── utils/           # Utility functions
├── tests/               # Test suite
│   ├── unit/           # Unit tests
│   ├── integration/     # Integration tests
│   └── fixtures/        # Test data
├── config/              # Configuration files
├── docs/               # Documentation
└── examples/           # Usage examples
```

## Development Workflow

### Typical Development Cycle

1. **Plan**: Discuss feature/bug in issue
2. **Branch**: Create feature branch from `main`
3. **Develop**: Implement changes with tests
4. **Test**: Run all tests and linting
5. **Document**: Update documentation
6. **Review**: Create PR and address feedback
7. **Merge**: Squash and merge to `main`
8. **Release**: Follow release process

### Code Review Guidelines

When reviewing code, check for:

- **Functionality**: Does it work as intended?
- **Testing**: Are there adequate tests?
- **Documentation**: Is documentation updated?
- **Style**: Does it follow code style?
- **Performance**: Any performance implications?
- **Security**: Any security concerns?

## Getting Help

- **Issues**: Use GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Documentation**: Check existing documentation first

## Recognition

Contributors will be recognized in:

- GitHub contributors list
- Release notes
- Project documentation

Thank you for contributing to VPSWeb! 🎉