# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**VPSWeb (Vox Poetica Studio Web)** is a professional AI-powered poetry translation platform that implements a collaborative Translator→Editor→Translator workflow to produce high-fidelity translations between English and Chinese (and other languages).

**Current Status**: v0.3.0 - Major Enhancement Milestone with Repository System Architecture

**Tech Stack**: Python, Poetry, Pydantic, AsyncIO, OpenAI-compatible APIs, YAML configuration

## Core Development Principles

### 1. Strategy-Todo-Code-Reflection Process

For any **non-trivial decision** (changes affecting multiple components, architectural decisions, or user-facing features), Claude Code MUST follow this four-step process with explicit approval required between phases:

#### **STRATEGY Phase** - Analysis and Planning
- Analyze current codebase and existing implementation
- Research best practices and evaluate trade-offs
- Review existing configuration and documentation
- Consider impact on version management, testing, and deployment
- **CRITICAL**: Present complete strategy for user approval before proceeding

#### **TODO Phase** - Structured Task Planning
- **REQUIREMENT**: Must get explicit consensus on strategy before creating TODO list
- Create comprehensive, ordered task list using TodoWrite tool
- Break complex changes into small, testable increments
- Mark one task as `in_progress` at any time, update status immediately upon completion
- **CRITICAL**: Present TODO list for user approval before proceeding to CODE phase

#### **CODE Phase** - Implementation and Validation
- **REQUIREMENT**: Must get explicit consensus on TODO list before starting implementation
- Execute tasks sequentially according to the TODO list
- Test each increment before proceeding
- Follow existing code patterns and conventions
- Ensure CI/CD compliance (Black formatting, tests passing)
- **CRITICAL**: Update task status and get confirmation on major milestones

#### **REFLECTION Phase** - Analysis and Continuous Improvement
- **REQUIREMENT**: Optional but recommended for significant non-trivial decisions
- **Purpose**: Systematic reflection on Strategy-Todo-Code effectiveness
- **Timing**: Conducted immediately after successful release
- **Scope**: Analyze decision quality, process effectiveness, and lessons learned
- **CRITICAL**: Reflections must create actionable insights for future decisions

**See [REFLECTION_SYSTEM.md](REFLECTION_SYSTEM.md) for complete guidance.**

### 2. Decision Classification

**Trivial Decisions** (Direct Implementation):
- Simple bug fixes with clear solutions
- Adding comments or improving documentation
- Single-file refactorings that don't affect interfaces
- Configuration value updates

**Non-Trivial Decisions** (Strategy-Todo-Code-Reflection Required):
- Adding new workflow steps or modes
- Changing API interfaces or data models
- Modifying core workflow orchestration
- Adding new LLM providers or integration patterns
- Changes affecting multiple configuration files
- Architectural refactoring
- New feature implementations

## Project Structure

### Core Architecture
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

### Key Architectural Patterns
- **3-Step Workflow**: Initial Translation → Editor Review → Translator Revision
- **Provider Abstraction**: Factory pattern for LLM provider flexibility
- **YAML Configuration**: Structured configuration with environment-specific overrides
- **Async Processing**: Full async/await support for concurrent operations

## Essential Development Commands

### Environment Setup
```bash
# Install dependencies
poetry install

# Set PYTHONPATH for src layout (required globally)
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
# Add this to your ~/.zshrc for permanent setup
```

### Quality and Testing
```bash
# Run all quality checks
./dev-check.sh

# Individual tools
python -m black src/ tests/                    # Format code
python -m pytest tests/ -v                     # Run tests
python -m mypy src/ --ignore-missing-imports   # Type checking
```

### Core Application Usage
```bash
# Basic translation
vpsweb translate -i poem.txt -s English -t Chinese

# With workflow mode
vpsweb translate -i poem.txt -s English -t Chinese -w hybrid

# Dry run validation
vpsweb translate -i poem.txt -s English -t Chinese --dry-run
```

### Version Management
```bash
# Create backup before changes
./save-version.sh X.Y.Z

# Create release
./push-version.sh X.Y.Z "Release notes"
```

**Pre-commit validation (MANDATORY)**: `python -m black --check src/ tests/ && python -m pytest tests/`

## Development Guidelines

### Code Standards
- **Formatting**: Black code formatter (line-length: 88)
- **Type Checking**: Comprehensive type annotations with mypy
- **Error Handling**: Proper exception handling with custom exceptions
- **Documentation**: Google/NumPy style docstrings for all public APIs
- **Testing**: Test coverage for all components

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

## Configuration Management

### Key Configuration Files
- `config/default.yaml`: Main workflow configuration
- `config/models.yaml`: Provider configurations
- `config/wechat.yaml`: WeChat Official Account integration

### Configuration Structure
- YAML format for readability
- Environment variable substitution using `${VAR_NAME}` syntax
- Pydantic model validation
- Support for workflow modes: reasoning, non_reasoning, hybrid

**See [docs/workflow-modes.md](docs/workflow-modes.md) for workflow mode details.**

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

### Specialized Documentation
- **WeChat Integration**: [docs/wechat-integration.md](docs/wechat-integration.md)
- **API Patterns**: [docs/api-patterns.md](docs/api-patterns.md)
- **Testing**: [docs/testing.md](docs/testing.md)
- **Future Development**: [docs/future-development.md](docs/future-development.md)
- **Documentation Standards**: [docs/documentation-standards.md](docs/documentation-standards.md)

---

**IMPORTANT**: This guide serves as the canonical reference for Claude Code development on VPSWeb. All development activities must adhere to these guidelines, especially the Strategy-Todo-Code-Reflection process for non-trivial decisions.