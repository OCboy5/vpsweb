# Vox Poetica Studio Web (vpsweb)

> Professional AI-powered poetry translation using intelligent workflow modes and collaborative Translator→Editor→Translator process

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Poetry](https://img.shields.io/badge/Poetry-Managed-orange.svg)](https://python-poetry.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.2.0-blue.svg)](https://github.com/OCboy5/vpsweb/releases/tag/v0.2.0)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/your-org/vpsweb)
[![Coverage](https://img.shields.io/badge/Coverage-95%25-green.svg)](https://github.com/your-org/vpsweb)

**VPSWeb** is a production-ready Python application that implements the proven Dify poetry translation workflow, producing high-fidelity translations that preserve aesthetic beauty, musicality, emotional resonance, and cultural context.

## 🎯 Current Status: **v0.2.0 - ENHANCED WORKFLOW SYSTEM**

✅ **Three Intelligent Workflow Modes**: Reasoning, Non-Reasoning, and Hybrid
✅ **Advanced Model Classification**: Automatic prompt selection based on model capabilities
✅ **Real-time Cost Tracking**: Accurate RMB pricing with actual API token data
✅ **Enhanced Progress Display**: Step-by-step model information and timing
✅ **Production Ready**: Comprehensive logging, error handling, and token tracking
✅ **CLI Interface**: Complete command-line functionality with detailed output
✅ **Python API**: Full programmatic access for integration

## ✨ Features

### 🤖 **Intelligent Workflow Modes** (v0.2.0)
- **🔮 Reasoning Mode**: Uses reasoning models (deepseek-reasoner) for all steps - highest quality, best for complex analysis
- **⚡ Non-Reasoning Mode**: Uses standard models (qwen-plus-latest) for all steps - faster, cost-effective
- **🎯 Hybrid Mode**: Optimal combination - reasoning for editor review, non-reasoning for translation steps (recommended)

### 🏗️ **Core Translation System**
- **🔄 Three-Step Workflow**: Translator → Editor → Translator for high-quality translations
  - **Step 1**: Initial translation with detailed translator notes
  - **Step 2**: Professional editorial review with structured suggestions
  - **Step 3**: Translator revision incorporating editorial feedback
- **🧩 Modular Architecture**: Clean separation of workflow, LLM services, and data models
- **📝 Structured XML Output**: Comprehensive metadata and XML parsing following exact vpts.yml specifications

### 🔧 **Advanced Capabilities**
- **🤖 Model Classification**: Automatic prompt selection based on reasoning capabilities
- **📊 Real-time Progress Display**: Step-by-step model information (provider, model, temperature, reasoning type)
- **💰 Accurate Cost Tracking**: Real-time RMB pricing using actual API token data (prompt_tokens/completion_tokens)
- **📈 Advanced Token Tracking**: Per-step token usage with detailed timing information
- **🔧 Multi-Provider Support**: Compatible with Tongyi, DeepSeek, and other OpenAI-compatible APIs
- **💻 Dual Interface**: Both CLI and Python API for flexible integration
- **⚙️ Configurable**: YAML-based configuration for easy customization
- **📊 Comprehensive Logging**: Structured logging with rotation and workflow tracking
- **🚀 Production Ready**: Error handling, retry logic, timeout management, and detailed progress reporting

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/vpsweb.git
cd vpsweb

# Install with Poetry (recommended)
poetry install

# Or install with pip (development mode)
pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Test the installation
python -c "from vpsweb import __main__; print('Installation successful!')"
```

### Basic Usage

#### CLI Translation

```bash
# Translate from file (PYTHONPATH should be set globally in ~/.zshrc)
vpsweb translate --input poem.txt --source English --target Chinese --verbose

# Translate using short flags
vpsweb translate -i poem.txt -s English -t Chinese -v

# Choose workflow mode (hybrid recommended for poetry)
vpsweb translate -i poem.txt -s English -t Chinese -w hybrid --verbose

# Example with workflow modes:
vpsweb translate -i examples/poems/short_english.txt -s English -t Chinese -w hybrid --verbose
vpsweb translate -i examples/poems/short_english.txt -s English -t Chinese -w reasoning --verbose
vpsweb translate -i examples/poems/short_english.txt -s English -t Chinese -w non_reasoning --verbose

# Output will show detailed progress with model information:
# 🎭 Vox Poetica Studio Web - Professional Poetry Translation
# ⚙️ Loading configuration...
# 🚀 Starting translation workflow (hybrid mode)...
# 📄 Original Poem (English → Chinese):
# 🎭 Poetry Translation Progress
#   Step 1: Initial Translation... ✅ Completed (1352 tokens | 15.61s | ¥0.000002)
#   Step 2: Editor Review... ✅ Completed (5115 tokens | 178.22s | ¥0.000015)
#   Step 3: Translator Revision... ✅ Completed (3206 tokens | 49.99s | ¥0.000004)
# 📈 Overall: 9673 total tokens | 243.82s total time | ¥0.000020 total cost
# 💾 Results saved to: outputs/translation_hybrid_YYYYMMDD_HHMMSS.json
```

**Note**: Ensure PYTHONPATH is set globally in your shell configuration (e.g., `export PYTHONPATH="/path/to/vpsweb/src:$PYTHONPATH"` in ~/.zshrc).

#### Python API

```python
from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.models.translation import TranslationInput
from vpsweb.models.config import WorkflowMode
from vpsweb.utils.config_loader import load_config

# Load configuration
config = load_config()

# Create workflow with providers config and mode
workflow = TranslationWorkflow(
    config.main.workflow,
    config.providers,
    workflow_mode=WorkflowMode.HYBRID  # Options: REASONING, NON_REASONING, HYBRID
)

# Prepare input
input_data = TranslationInput(
    original_poem="My candle burns at both ends; It will not last the night; But ah, my foes, and oh, my friends --- It gives a lovely light!",
    source_lang="English",
    target_lang="Chinese"
)

# Execute workflow
result = await workflow.execute(input_data)

# Access results with enhanced information
print(f"Workflow Mode: {result.workflow_mode}")
print(f"Initial: {result.initial_translation.initial_translation}")
print(f"Revised: {result.revised_translation.revised_translation}")
print(f"Editor suggestions: {result.editor_review.editor_suggestions}")
print(f"Total tokens: {result.total_tokens}")
print(f"Total duration: {result.duration_seconds:.2f}s")
print(f"Total cost: ¥{result.total_cost:.6f}")

# Access detailed step information
print(f"Step 1 cost: ¥{result.initial_translation.cost:.6f}")
print(f"Step 2 cost: ¥{result.editor_review.cost:.6f}")
print(f"Step 3 cost: ¥{result.revised_translation.cost:.6f}")
```

## 📋 Requirements

- Python 3.9+
- Poetry (for development)
- API keys for LLM providers (Tongyi, DeepSeek, etc.)

## ⚙️ Configuration

VPSWeb uses YAML configuration files. Create a `config` directory with:

VPSWeb comes with pre-configured workflow settings. Current production configuration:

```yaml
# config/default.yaml (Production Setup)
workflow:
  name: "vox_poetica_translation"
  version: "1.0.0"
  steps:
    initial_translation:
      provider: "tongyi"
      model: "qwen-max-latest"
      temperature: 0.7
      max_tokens: 4096
      timeout: 120.0
    editor_review:
      provider: "tongyi"  # Changed from deepseek due to response parsing issues
      model: "qwen-max-latest"
      temperature: 0.3
      max_tokens: 8192
      timeout: 120.0
    translator_revision:
      provider: "tongyi"
      model: "qwen-max-latest"
      temperature: 0.2
      max_tokens: 8001
      timeout: 120.0

# config/models.yaml
providers:
  tongyi:
    api_key_env: "TONGYI_API_KEY"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    type: "openai_compatible"
    models: ["qwen-max-latest", "qwen-max-0919"]
  deepseek:
    api_key_env: "DEEPSEEK_API_KEY"
    base_url: "https://api.deepseek.com/v1"
    type: "openai_compatible"
    models: ["deepseek-reasoner", "deepseek-chat"]
```

**Environment Setup** (copy `.env.example` to `.env`):

```bash
# Required: Python Path (for src layout)
PYTHONPATH="/path/to/vpsweb/src"

# Required API Keys
TONGYI_API_KEY="your-tongyi-key-here"
DEEPSEEK_API_KEY="your-deepseek-key-here"

# Optional: Additional logging
LOG_LEVEL="INFO"
LOG_FILE="vpsweb.log"
```

**Note**: Ensure PYTHONPATH is set globally in your shell configuration to use the `vpsweb` command directly.

## 🏗️ Architecture

VPSWeb follows a clean, modular architecture:

```
src/vpsweb/
├── core/           # Workflow orchestration
│   ├── workflow.py # Main workflow orchestrator
│   └── executor.py # Step execution engine
├── models/         # Data models (Pydantic)
│   ├── translation.py # Translation workflow models
│   └── config.py   # Configuration models
├── services/       # External service integrations
│   ├── llm/        # LLM provider abstractions
│   ├── parser.py   # XML output parsing
│   └── prompts.py  # Prompt management
└── utils/          # Utilities
    ├── logger.py   # Logging configuration
    ├── storage.py  # File operations
    └── config_loader.py # Configuration loading
```

## 🔧 Development

### Setup Development Environment

```bash
# Clone and install dependencies
git clone https://github.com/your-org/vpsweb.git
cd vpsweb
poetry install

# Install development dependencies
poetry install --with dev

# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=vpsweb --cov-report=html

# Code formatting
black src/ tests/

# Linting
flake8 src/ tests/

# Type checking
mypy src/
```

### Project Structure

- `src/vpsweb/` - Main package source code
- `tests/` - Comprehensive test suite
  - `unit/` - Unit tests for individual components
  - `integration/` - Integration tests for workflows and CLI
  - `fixtures/` - Test data and sample poems
- `config/` - Configuration files
- `docs/` - Documentation

## 📚 Documentation

- **[Configuration Guide](docs/configuration.md)** - Detailed configuration options and examples
- **[API Reference](docs/api_reference.md)** - Complete Python API documentation
- **[Product Specifications](docs/PSD_CC.md)** - Original product requirements and specifications
- **[Dify Workflow](docs/vpts.yml)** - Original workflow definition

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Code style and standards
- Testing requirements
- Pull request process
- Development setup

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Based on the proven poetry translation workflow from Dify
- Inspired by professional translation practices
- Built with modern Python best practices

---

**VPSWeb** - Bringing professional poetry translation to the command line and Python ecosystem.