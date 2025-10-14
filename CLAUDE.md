# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**VPSWeb (Vox Poetica Studio Web)** is a professional AI-powered poetry translation platform that implements a collaborative Translator→Editor→Translator workflow to produce high-fidelity translations between English and Chinese (and other languages).

**Current Status**: v0.2.5 - WeChat Article Publishing Optimization Release

## Core Development Principles

### 1. Strategy-Todo-Code Process

For any **non-trivial decision** (changes affecting multiple components, architectural decisions, or user-facing features), Claude Code MUST follow this three-step process with explicit approval required between phases:

#### **STRATEGY Phase** - Analysis and Planning
- Analyze the current codebase structure and existing implementation
- Research best practices and consider implications
- Evaluate multiple approaches and their trade-offs
- Review existing configuration and documentation
- Consider impact on version management, testing, and deployment
- **CRITICAL**: Present complete strategy for user approval before proceeding

#### **TODO Phase** - Structured Task Planning
- **REQUIREMENT**: Must get explicit consensus on strategy before creating TODO list
- Create a comprehensive, ordered task list using the TodoWrite tool
- Break complex changes into small, testable increments
- Include validation tasks (testing, formatting, documentation updates)
- Mark one task as `in_progress` at any time
- Update task status immediately upon completion
- **CRITICAL**: Present TODO list for user approval before proceeding to CODE phase

#### **CODE Phase** - Implementation and Validation
- **REQUIREMENT**: Must get explicit consensus on TODO list before starting implementation
- Execute tasks sequentially according to the TODO list
- Test each increment before proceeding
- Follow existing code patterns and conventions
- Update relevant documentation
- Ensure CI/CD compliance (Black formatting, tests passing)
- **CRITICAL**: Update task status and get confirmation on major milestones

### 2. Decision Classification

**Trivial Decisions** (Direct Implementation):
- Simple bug fixes with clear solutions
- Adding comments or improving documentation
- Single-file refactorings that don't affect interfaces
- Configuration value updates

**Non-Trivial Decisions** (Strategy-Todo-Code Required):
- Adding new workflow steps or modes
- Changing API interfaces or data models
- Modifying the core workflow orchestration
- Adding new LLM providers or integration patterns
- Changes affecting multiple configuration files
- Architectural refactoring
- New feature implementations

## Project Structure Knowledge

### Core Architecture
```
src/vpsweb/
├── core/                    # Workflow orchestration
│   ├── workflow.py          # Main workflow orchestrator (T-E-T flow)
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

### Workflow System
The system implements a **3-step Translator→Editor→Translator** workflow:
1. **Initial Translation**: Raw translation attempt
2. **Editor Review**: Critical assessment and suggestions
3. **Translator Revision**: Final polished translation

### Configuration System
- `config/default.yaml`: Main workflow configuration
- `config/models.yaml`: Provider configurations
- `config/wechat.yaml`: WeChat Official Account integration settings
- `config/html_templates/wechat_articles/`: WeChat article HTML templates
- Support for **reasoning**, **non-reasoning**, and **hybrid** workflow modes
- Model-specific parameters and prompt templates

## Common Development Commands

### Build and Development Environment
```bash
# Install dependencies with Poetry
poetry install

# Install development dependencies
poetry install --with dev

# Activate virtual environment
poetry shell

# Set PYTHONPATH for src layout (required globally)
export PYTHONPATH="/path/to/vpsweb/src:$PYTHONPATH"
# Add this to your ~/.zshrc for permanent setup
```

### Code Quality and Testing
```bash
# Run all quality checks (comprehensive validation)
./dev-check.sh

# Run specific checks
./dev-check.sh --lint-only      # Linting only
./dev-check.sh --test-only      # Tests only
./dev-check.sh --release-mode   # Release preparation checks
./dev-check.sh --fix            # Auto-fix formatting issues

# Individual tools
python -m black src/ tests/                    # Format code
python -m black --check src/ tests/            # Check formatting
python -m flake8 src/ --max-line-length=88     # Lint code
python -m mypy src/ --ignore-missing-imports   # Type checking
python -m pytest tests/ -v                     # Run tests
```

### Running the Application
```bash
# CLI translation (basic usage)
vpsweb translate -i poem.txt -s English -t Chinese

# CLI with different workflow modes
vpsweb translate -i poem.txt -s English -t Chinese -w hybrid --verbose
vpsweb translate -i poem.txt -s English -t Chinese -w reasoning --verbose
vpsweb translate -i poem.txt -s English -t Chinese -w non_reasoning --verbose

# Dry run (validation only)
vpsweb translate -i poem.txt -s English -t Chinese --dry-run

# WeChat article generation
vpsweb generate-article -j translation_output.json

# Python API usage
python -c "
from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.models.translation import TranslationInput
from vpsweb.models.config import WorkflowMode
from vpsweb.utils.config_loader import load_config

config = load_config()
workflow = TranslationWorkflow(config.main.workflow, config.providers, WorkflowMode.HYBRID)
input_data = TranslationInput(original_poem='My candle burns at both ends', source_lang='English', target_lang='Chinese')
result = await workflow.execute(input_data)
print(result.revised_translation.revised_translation)
"
```

### Version Management
```bash
# Create local backup before changes
./save-version.sh 0.2.2

# Push official release to GitHub
./push-version.sh 0.2.2 "Added new features and bug fixes"

# List local backup versions
git tag -l "*local*"

# Restore from backup
git checkout v0.2.0-local-2025-10-05
```

## Development Guidelines

### 1. Code Standards
- **Formatting**: Use Black code formatter (line-length: 88)
- **Type Checking**: Comprehensive type annotations with mypy
- **Error Handling**: Proper exception handling with custom exceptions
- **Documentation**: Google/NumPy style docstrings
- **Testing**: Test coverage for all components

### 2. Output File Organization
- **Directory Structure**:
  ```
  outputs/
  ├── json/           # All JSON translation outputs
  └── markdown/       # All markdown translation outputs
  ```
- **Naming Scheme**: `{author}_{title}_{source_target}_{mode}_{date}_{hash}.{format}`
  - Example: `陶渊明_歸園田居_chinese_english_hybrid_20251012_184234_81e865f8.json`
  - Example: `陶渊明_歸園田居_chinese_english_20251012_184234_81e865f8.md`
  - Example: `陶渊明_歸園田居_chinese_english_20251012_184234_81e865f8_log.md`
- **Key Features**:
  - Poet names lead filenames for easy identification
  - No "translation_" prefix - cleaner, poet-first naming
  - Log files have "log" suffix instead of prefix
  - Metadata extraction from poem text or provided metadata
  - Filename sanitization for cross-platform compatibility

### 3. Version Management
- Follow the workflow in `./VERSION_WORKFLOW.md` strictly
- Create local backups before major changes: `./save-version.sh`
- Push official releases with: `./push-version.sh`
- Ensure version consistency across ALL files before release

### 4. Quality Assurance
Before any release or major commit:
```bash
# Check code formatting
python -m black --check src/ tests/

# Run tests
python -m pytest tests/

# Verify imports work
python -c "from src.vpsweb.models.config import ModelProviderConfig"

# Check version consistency
grep -r "0\.2\.0" src/ pyproject.toml
```

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

## WeChat Official Account Integration

### Overview
VPSWeb includes comprehensive WeChat Official Account integration for automatic article publishing:
- **Article Generation**: Automatically formats translations as WeChat articles
- **Translation Notes Synthesis**: AI-powered synthesis of translation commentary
- **Draft Management**: Save as drafts for manual review or auto-publish
- **Media Management**: Handle images and formatting for WeChat platform

### Configuration Setup
```yaml
# config/wechat.yaml
appid: "${WECHAT_APPID}"
secret: "${WECHAT_SECRET}"
article_generation:
  include_translation_notes: true
  copyright_text: "本译文与导读由【知韵译诗】施知韵VoxPoetica原创制作"
publishing:
  save_as_draft: true  # Safe default
  auto_publish: false  # Manual control
```

### Environment Variables
```bash
# Required for WeChat integration
WECHAT_APPID="your-wechat-appid"
WECHAT_SECRET="your-wechat-secret"
```

### WeChat Usage
```bash
# Generate WeChat article from translation
vpsweb generate-article -j translation_output.json

# Generate with custom options
vpsweb generate-article -j translation.json -o my_articles/ --author "My Name"

# Publish to WeChat (if configured)
vpsweb publish-article -a article_metadata.json
```

### WeChat Article Templates
VPSWeb uses a flexible template system for WeChat articles:

- **HTML Templates**: `config/html_templates/wechat_articles/` - Control article layout and styling
- **Prompt Templates**: `config/prompts/wechat_article_notes_*.yaml` - Control LLM behavior for translation notes
- **Template Variables**: Uses Jinja2 templating with variables like `{{ poem_title }}`, `{{ poet_name }}`, etc.
- **Custom Templates**: Create new templates and update `config/wechat.yaml` to use them

#### Creating Custom Templates

**HTML Templates (Article Layout):**
1. Copy `config/html_templates/wechat_articles/default.html` to a new file
2. Modify the HTML structure and CSS styling as needed
3. Use supported template variables (see template file for examples)
4. Update `config/wechat.yaml`: `article_template: "your_template_name"`

**Prompt Templates (Translation Notes):**
1. Create a new prompt template in `config/prompts/` (e.g., `wechat_article_notes_custom.yaml`)
2. Customize the prompt for different LLM behaviors or output styles
3. Update `config/wechat.yaml`: `prompt_template: "wechat_article_notes_custom"`

#### Available Prompt Templates
- `wechat_article_notes_reasoning` - For reasoning models, detailed analysis
- `wechat_article_notes_nonreasoning` - For standard models, concise output

## Workflow Mode Management

### Reasoning Mode
- Use deepseek-reasoner or similar reasoning models
- Prompts should not interfere with Chain-of-Thought
- Higher token limits for reasoning traces
- Temperature settings optimized for analytical work

### Non-Reasoning Mode
- Use qwen-plus or similar standard models
- Direct, structured prompts for specific outputs
- Optimized for efficiency and consistency
- Lower temperature settings for reliability

### Hybrid Mode
- Combine reasoning and non-reasoning models strategically
- Example: Non-reasoning for initial translation, reasoning for editor review
- Leverage strengths of different model types

## Configuration Management

### YAML Configuration Structure
- All configurations in YAML format for readability
- Environment-specific overrides supported
- Validation using Pydantic models
- Hot reloading for development

### Prompt Template Management
- Separate templates for reasoning vs non-reasoning models
- Workflow-specific optimizations
- Easy A/B testing of different prompts
- Version control for prompt changes

## Testing Strategy

### Manual Testing (Current)
- End-to-end workflow verification
- Error handling validation
- Configuration testing
- CLI interface testing

### Automated Testing Framework
- Structure ready for implementation
- Pytest-based with asyncio support
- Mock providers for unit testing
- Integration tests for complete workflows

## API Integration Patterns

### Provider Factory Pattern
```python
# Standard provider instantiation
provider = LLMFactory.create_provider(
    provider_type="tongyi",
    config=provider_config
)

# Standard workflow execution
response = await provider.generate(
    messages=messages,
    temperature=0.7,
    max_tokens=4096
)
```

### Error Handling
- Custom exceptions for different error types
- Graceful degradation when providers fail
- Comprehensive logging for debugging
- User-friendly error messages

## Documentation Requirements

### Code Documentation
- All public APIs must have docstrings
- Complex algorithms need inline comments
- Configuration examples in docstrings
- Usage examples in docstrings

### Project Documentation
- README.md: Project overview and quick start
- DEVELOPMENT.md: Detailed development guide
- CHANGELOG.md: Version history and changes
- API documentation for all modules

## Future Development Guidelines

### Architectural Considerations
- Modularity for easy extension
- Configuration-driven flexibility
- Provider agnostic design
- Scalable workflow orchestration

### Performance Optimization
- Token usage optimization
- Response caching strategies
- Async processing opportunities
- Batch processing capabilities

### User Interface Development
- CLI interface currently implemented
- Web UI architecture ready for implementation
- API design for UI integration
- Progress tracking and display

## Release Management Workflow

### 🚨 CRITICAL: Release Process Requirements

When creating a new version release (vX.Y.Z), Claude Code **MUST** follow the strict workflow defined in `VERSION_WORKFLOW.md`. This is non-negotiable for maintaining release quality and consistency.

### 📋 Mandatory Release Checklist

For any version release, Claude must complete ALL of these steps in order:

#### **Phase 1: Preparation (Before Making Changes)**
1. **Create Local Backup** (MANDATORY - First Step!)
   ```bash
   ./save-version.sh X.Y.Z
   ```

2. **Version Bump** (Update 3 files exactly)
   - `pyproject.toml`: `version = "X.Y.Z"`
   - `src/vpsweb/__init__.py`: `__version__ = "X.Y.Z"`
   - `src/vpsweb/__main__.py`: `@click.version_option(version="X.Y.Z")`

3. **Update Documentation** (MANDATORY)
   - `CHANGELOG.md`: Add release notes section
   - `README.md`: Update version badge and status section
   - `STATUS.md`: Update version, executive summary, and features
   - Update other docs if needed

4. **Code Quality Check**
   - Format: `python -m black src/ tests/`
   - Check: `python -m black --check src/ tests/`
   - Tests: `pytest -q` (if possible)

#### **Phase 2: Commit & Release**
5. **Commit Changes**
   ```bash
   git add .
   git commit -m "Release vX.Y.Z - [Release Name]

   [Detailed release notes]

   🚀 Generated with Claude Code (https://claude.ai/claude-code)

   Co-Authored-By: Claude <noreply@anthropic.com>"
   git push origin main
   ```

6. **Create GitHub Release**
   ```bash
   ./push-version.sh X.Y.Z "Brief release notes"
   ```

#### **Phase 3: Verification**
7. **Verify Release**
   - Check GitHub release exists: `gh release view vX.Y.Z`
   - Verify tag on remote: `git ls-remote --tags origin | grep "refs/tags/vX.Y.Z$"`
   - Check GitHub Actions CI status

### ⚠️ Common Mistakes to Avoid
- **NEVER** skip local backup creation
- **NEVER** forget to update all 3 version files
- **NEVER** skip CHANGELOG.md updates
- **NEVER** skip README.md and STATUS.md updates
- **NEVER** commit without proper formatting check
- **ALWAYS** verify release exists after creation

### 📚 Reference Documents
- **Primary**: `VERSION_WORKFLOW.md` - Complete release workflow
- **Printable Checklist**: Section 9 of VERSION_WORKFLOW.md
- **Quick Reference**: Section 8 of VERSION_WORKFLOW.md

### 🔍 Quality Assurance
Before announcing any release, ensure:
- All checklist items are completed
- GitHub release page shows correct content
- CI/CD pipeline completed successfully
- Documentation reflects new version accurately

## Emergency Procedures

### Version Recovery
```bash
# List all local backup versions
git tag -l "*local*"

# Restore specific version
git checkout v0.1.0-local-2025-10-05
```

### Configuration Recovery
- Keep backup of working configurations
- Use version control for configuration changes
- Document configuration migration steps
- Test configuration changes in isolation

## Contact and Support

### Project Resources
- **GitHub Repository**: Primary development location
- **Documentation**: Comprehensive docs/ directory
- **Configuration Examples**: config/ directory
- **Test Examples**: tests/ directory

### Development Communication
- Use structured issue reports
- Include configuration details in bug reports
- Provide reproduction steps for issues
- Include log files for debugging

---

**IMPORTANT**: This guide serves as the canonical reference for Claude Code development on VPSWeb. All development activities must adhere to these guidelines, especially the Strategy-Todo-Code process for non-trivial decisions.
