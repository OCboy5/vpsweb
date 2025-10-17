# Product Specifications Document (PSD)
## VPSWeb - Professional Poetry Translation System

### 1. Executive Summary

**Project Name**: vpsweb (Vox Poetica Studio Web)

**Purpose**: A professional poetry translation system that simulates collaborative translation workflows through a Translator→Editor→Translator iterative process, achieving high-quality poetry translations between English, Chinese, and other languages while preserving fidelity, poetic essence, aesthetic beauty, rhythm, musicality, and cultural appropriateness.

**Core Innovation**: Multi-agent collaborative approach mimicking real-world professional translation workflows with "initial translation → editorial review → final draft" iterations.

### 2. System Architecture

#### 2.1 High-Level Architecture
```
┌─────────────────────────────────────────────┐
│            User Interface Layer              │
│         (Future Web UI / CLI)                │
└─────────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────────┐
│           Orchestration Layer                │
│      (Workflow Engine & State Manager)       │
└─────────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────────┐
│             Agent Layer                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │Translator│ │  Editor  │ │Finalizer │    │
│  └──────────┘ └──────────┘ └──────────┘    │
└─────────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────────┐
│           Model Provider Layer               │
│     (OpenAI, Anthropic, Local Models)        │
└─────────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────────┐
│            Data Storage Layer                │
│    (Session Management, History, Outputs)    │
└─────────────────────────────────────────────┘
```

#### 2.2 Workflow Components (Based on DSL Analysis)

**Core Agents**:
1. **Translator Agent**: Performs initial translation and revision based on editorial feedback
2. **Editor Agent**: Reviews translations and provides structured editorial suggestions
3. **Finalizer Agent**: Produces the polished final translation

**Workflow Stages**:
1. **Initialization**: Input processing and context setup
2. **Initial Translation**: First translation attempt
3. **Editorial Review**: Critical analysis and suggestions
4. **Translation Revision**: Incorporating editorial feedback
5. **Final Polish**: Production of publication-ready translation

### 3. Technical Specifications

#### 3.1 Technology Stack
- **Language**: Python 3.9+
- **Framework**: Modular Python with async support
- **Configuration**: YAML/JSON for configs, TOML for project metadata
- **LLM Integration**: OpenAI API, Anthropic API, extensible to other providers
- **Data Format**: JSON for structured data exchange between components
- **Testing**: pytest, unittest
- **Documentation**: Sphinx-compatible docstrings
- **Packaging**: setuptools, pip-installable

#### 3.2 Project Structure
```
vpsweb/
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── setup.py
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml
├── config/
│   ├── models.yaml          # Model configurations
│   ├── prompts.yaml         # Agent prompts
│   ├── workflow.yaml        # Workflow definitions
│   └── settings.yaml        # General settings
├── vpsweb/
│   ├── __init__.py
│   ├── __main__.py         # CLI entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── workflow.py     # Workflow orchestration
│   │   ├── state.py        # State management
│   │   └── types.py        # Type definitions
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py         # Base agent class
│   │   ├── translator.py   # Translator agent
│   │   ├── editor.py       # Editor agent
│   │   └── finalizer.py    # Finalizer agent
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py         # Base model interface
│   │   ├── openai.py       # OpenAI integration
│   │   ├── anthropic.py    # Anthropic integration
│   │   └── factory.py      # Model factory
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py       # Configuration loader
│   │   ├── logger.py       # Logging utilities
│   │   └── validators.py   # Input validation
│   └── api/                # Future API layer
│       ├── __init__.py
│       └── server.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_agents/
│   ├── test_workflow/
│   └── test_models/
├── examples/
│   ├── basic_translation.py
│   └── sample_poems/
│       ├── english/
│       └── chinese/
└── docs/
    ├── conf.py
    ├── index.rst
    ├── api/
    └── guides/
```

### 4. Data Models

#### 4.1 Core Data Structures

```python
# Translation Request
{
    "id": "uuid",
    "source_text": "string",
    "source_language": "string",
    "target_language": "string",
    "context": {
        "author": "string",
        "title": "string",
        "genre": "string",
        "cultural_notes": "string"
    },
    "preferences": {
        "style": "formal|informal|poetic",
        "preserve_rhyme": "boolean",
        "preserve_meter": "boolean"
    }
}

# Translation State
{
    "request_id": "uuid",
    "current_stage": "enum",
    "iterations": [
        {
            "iteration_number": "integer",
            "translator_output": "object",
            "editor_feedback": "object",
            "timestamp": "datetime"
        }
    ],
    "final_translation": "object",
    "metadata": {
        "total_tokens": "integer",
        "processing_time": "float",
        "model_versions": "object"
    }
}

# Agent Output Structure
{
    "agent_id": "string",
    "stage": "string",
    "content": {
        "translation": "string",
        "annotations": ["string"],
        "confidence": "float",
        "reasoning": "string"
    },
    "metadata": {
        "model": "string",
        "tokens_used": "integer",
        "timestamp": "datetime"
    }
}
```

### 5. Configuration Specifications

#### 5.1 Model Configuration (models.yaml)
```yaml
models:
  default: "gpt-4"
  providers:
    openai:
      api_key: "${OPENAI_API_KEY}"
      models:
        gpt-4:
          temperature: 0.7
          max_tokens: 2000
        gpt-3.5-turbo:
          temperature: 0.7
          max_tokens: 1500
    anthropic:
      api_key: "${ANTHROPIC_API_KEY}"
      models:
        claude-3-sonnet:
          temperature: 0.7
          max_tokens: 2000
```

#### 5.2 Prompt Configuration (prompts.yaml)
```yaml
prompts:
  translator:
    initial:
      system: "You are a professional poetry translator..."
      user_template: "Translate the following {source_language} poem to {target_language}..."
    revision:
      system: "You are revising a translation based on editorial feedback..."
      user_template: "Original: {original}\nTranslation: {translation}\nFeedback: {feedback}"
  editor:
    system: "You are a professional poetry editor..."
    user_template: "Review this translation for accuracy, poetry, and cultural appropriateness..."
  finalizer:
    system: "You are producing the final version of a poetry translation..."
    user_template: "Based on all iterations, create the final translation..."
```

### 6. API Specifications

#### 6.1 CLI Interface
```bash
# Basic usage
vpsweb translate --input poem.txt --source en --target zh

# With configuration
vpsweb translate --config custom_config.yaml --input poem.txt

# Interactive mode
vpsweb interactive

# Batch processing
vpsweb batch --input-dir poems/ --output-dir translations/
```

#### 6.2 Python API
```python
from vpsweb import TranslationWorkflow, Config

# Initialize with custom config
config = Config.from_file("config.yaml")
workflow = TranslationWorkflow(config)

# Single translation
result = workflow.translate(
    text="Poetry text here",
    source_language="en",
    target_language="zh",
    context={"author": "Shakespeare", "title": "Sonnet 18"}
)

# Access results
print(result.final_translation)
print(result.iterations)
print(result.editor_feedback)
```

#### 6.3 Future Web API (REST)
```
POST /api/v1/translate
{
    "text": "string",
    "source_language": "string",
    "target_language": "string",
    "options": {}
}

GET /api/v1/translation/{id}
GET /api/v1/translation/{id}/iterations
GET /api/v1/models
GET /api/v1/languages
```

### 7. Quality Assurance

#### 7.1 Testing Strategy
- **Unit Tests**: Individual agent and component testing
- **Integration Tests**: Workflow and model integration testing
- **E2E Tests**: Complete translation workflow testing
- **Performance Tests**: Token usage and response time benchmarks
- **Quality Tests**: Translation quality metrics and evaluation

#### 7.2 Metrics and Monitoring
- Translation quality scores
- Token usage per translation
- Processing time per stage
- Success/failure rates
- Model performance comparison

### 8. Extensibility Considerations

#### 8.1 Plugin Architecture
- Custom agent implementations
- Additional language support
- Alternative model providers
- Custom evaluation metrics
- Export format plugins

#### 8.2 Web UI Integration Points
- WebSocket support for real-time updates
- Session management for multi-user support
- Progress tracking and visualization
- Result comparison and versioning
- User preference storage

### 9. Development Roadmap

#### Phase 1: Core Implementation (Weeks 1-2)
- [ ] Project setup and structure
- [ ] Base agent implementation
- [ ] Workflow orchestration
- [ ] Configuration system
- [ ] CLI interface

#### Phase 2: Model Integration (Week 3)
- [ ] OpenAI integration
- [ ] Anthropic integration
- [ ] Model factory and abstraction
- [ ] Error handling and retries

#### Phase 3: Advanced Features (Week 4)
- [ ] Batch processing
- [ ] Session management
- [ ] Performance optimization
- [ ] Comprehensive testing

#### Phase 4: Web Preparation (Week 5)
- [ ] API layer implementation
- [ ] WebSocket support
- [ ] Database integration
- [ ] Authentication framework

#### Phase 5: Documentation & Polish (Week 6)
- [ ] API documentation
- [ ] User guides
- [ ] Example collections
- [ ] Performance benchmarks

### 10. Security & Compliance

#### 10.1 Security Measures
- API key encryption and secure storage
- Input validation and sanitization
- Rate limiting and quota management
- Audit logging for all translations

#### 10.2 Data Privacy
- No permanent storage of translations by default
- Optional encrypted local caching
- GDPR-compliant data handling
- User consent for data usage

### 11. Success Criteria

1. **Functional**: Successfully translates poetry maintaining 90%+ semantic accuracy
2. **Performance**: Average translation time < 30 seconds
3. **Quality**: Editor approval rate > 80% in first iteration
4. **Scalability**: Handles 100+ concurrent translations
5. **Usability**: CLI completion in < 5 commands, API integration in < 10 lines of code

### 12. Appendices

#### A. Glossary
- **Agent**: Autonomous component performing specific translation tasks
- **Iteration**: One complete cycle of translation-review-revision
- **Workflow**: Complete orchestrated translation process
- **Stage**: Discrete step within the workflow

#### B. References
- Original Dify workflow DSL specification
- OpenAI API documentation
- Anthropic API documentation
- Poetry translation best practices

#### C. Version History
- v1.0.0: Initial PSD creation
- Future versions will be tracked in git

---

**Document Status**: Draft v1.0.0  
**Last Updated**: Current Date  
**Author**: VPSWeb Development Team  
**Review Status**: Pending Technical Review