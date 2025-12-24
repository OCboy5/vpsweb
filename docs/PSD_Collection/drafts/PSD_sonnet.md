# Vox Poetica Studio Web (vpsweb) - Product Specifications Document

## 1. Executive Summary

### 1.1 Project Overview
**Project Name:** Vox Poetica Studio Web (vpsweb)  
**Purpose:** A professional poetry translation system that simulates a collaborative workflow between translator and editor, converting poems between languages (primarily English and Chinese) while preserving fidelity, poetic quality, aesthetics, rhythm, musicality, and cultural resonance.

### 1.2 Core Workflow
The system implements a three-stage translation pipeline:
1. **Initial Translation** - Professional translator creates first draft
2. **Editor Review** - Bilingual critic provides detailed feedback
3. **Translator Revision** - Translator refines based on editor suggestions

### 1.3 Technology Stack
- **Language:** Python 3.9+
- **LLM Integration:** Support for multiple providers (Tongyi/Qwen, DeepSeek)
- **Configuration:** YAML/JSON-based config files
- **Storage:** JSON-based structured output
- **Version Control:** Git/GitHub

---

## 2. System Architecture

### 2.1 High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     Configuration Layer                      │
│  (config.yaml, prompts/, models.yaml)                       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Workflow   │  │   Pipeline   │  │   Executor   │      │
│  │   Manager    │→ │   Builder    │→ │   Engine     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                        Service Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     LLM      │  │    Prompt    │  │   Output     │      │
│  │   Provider   │  │   Template   │  │   Handler    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                         Data Layer                           │
│  (JSON Storage, Input/Output Management)                    │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Directory Structure
```
vpsweb/
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── setup.py
├── pyproject.toml
│
├── config/
│   ├── default.yaml           # Default configuration
│   ├── models.yaml            # Model provider configurations
│   └── prompts/               # Prompt templates
│       ├── initial_translation.yaml
│       ├── editor_review.yaml
│       └── translator_revision.yaml
│
├── src/
│   └── vpsweb/
│       ├── __init__.py
│       ├── __main__.py        # CLI entry point
│       │
│       ├── core/              # Core workflow logic
│       │   ├── __init__.py
│       │   ├── workflow.py    # Workflow orchestration
│       │   ├── pipeline.py    # Pipeline execution
│       │   └── executor.py    # Step execution
│       │
│       ├── models/            # Data models
│       │   ├── __init__.py
│       │   ├── translation.py # Translation data models
│       │   └── workflow.py    # Workflow configuration models
│       │
│       ├── services/          # External services
│       │   ├── __init__.py
│       │   ├── llm/          # LLM providers
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   ├── tongyi.py
│       │   │   └── deepseek.py
│       │   ├── prompts.py    # Prompt template manager
│       │   └── parser.py     # XML/JSON parser
│       │
│       └── utils/            # Utilities
│           ├── __init__.py
│           ├── config.py     # Configuration loader
│           ├── logger.py     # Logging setup
│           └── storage.py    # JSON storage handler
│
├── tests/                    # Unit and integration tests
│   ├── __init__.py
│   ├── test_workflow.py
│   ├── test_llm.py
│   └── fixtures/
│
├── examples/                 # Example usage
│   ├── sample_poems/
│   └── run_translation.py
│
└── outputs/                  # Generated outputs (gitignored)
    └── .gitkeep
```

---

## 3. Detailed Component Specifications

### 3.1 Configuration System

#### 3.1.1 Main Configuration (config/default.yaml)
```yaml
workflow:
  name: "vox_poetica_translation"
  version: "1.0.0"
  
models:
  initial_translation:
    provider: "tongyi"
    model: "qwen-max-latest"
    temperature: 1.0
    max_tokens: 4096
    
  editor_review:
    provider: "deepseek"
    model: "deepseek-reasoner"
    temperature: 1.0
    max_tokens: 8192
    
  translator_revision:
    provider: "tongyi"
    model: "qwen-max-0919"
    temperature: 0.2
    max_tokens: 8001

storage:
  output_dir: "outputs"
  format: "json"
  include_timestamp: true
  
logging:
  level: "INFO"
  format: "detailed"
  file: "vpsweb.log"
```

#### 3.1.2 Model Provider Configuration (config/models.yaml)
```yaml
providers:
  tongyi:
    api_key_env: "TONGYI_API_KEY"
    base_url: "https://dashscope.aliyuncs.com/api/v1"
    available_models:
      - "qwen-max-latest"
      - "qwen-max-0919"
      - "qwen-plus"
    
  deepseek:
    api_key_env: "DEEPSEEK_API_KEY"
    base_url: "https://api.deepseek.com/v1"
    available_models:
      - "deepseek-reasoner"
      - "deepseek-chat"
```

#### 3.1.3 Prompt Templates (config/prompts/*.yaml)
Each prompt stored as structured YAML with variables:
```yaml
name: "initial_translation"
version: "1.0"
system_prompt: |
  You are a renowned poet and professional {{source_lang}}-to-{{target_lang}} poetry translator...
  
user_prompt: |
  Your task is to provide a high-quality translation...
  
output_format:
  - type: "xml"
    tags:
      - "initial_translation"
      - "initial_translation_notes"
```

### 3.2 Core Workflow Components

#### 3.2.1 Workflow Manager (src/vpsweb/core/workflow.py)
**Responsibilities:**
- Load and validate workflow configuration
- Initialize pipeline stages
- Coordinate execution flow
- Handle errors and retries

**Key Classes:**
```python
class WorkflowManager:
    def __init__(self, config_path: str)
    def load_config(self) -> WorkflowConfig
    def execute(self, input_data: TranslationInput) -> TranslationOutput
    def validate_input(self, input_data: TranslationInput) -> bool
```

#### 3.2.2 Pipeline Builder (src/vpsweb/core/pipeline.py)
**Responsibilities:**
- Define pipeline stages
- Manage stage dependencies
- Pass data between stages

**Key Classes:**
```python
class Pipeline:
    def __init__(self, stages: List[PipelineStage])
    def add_stage(self, stage: PipelineStage)
    def run(self, input_data: dict) -> PipelineResult
    
class PipelineStage:
    def __init__(self, name: str, executor: Callable)
    def execute(self, input_data: dict) -> StageResult
    def validate_output(self, output: dict) -> bool
```

#### 3.2.3 Executor Engine (src/vpsweb/core/executor.py)
**Responsibilities:**
- Execute individual workflow steps
- Call LLM providers
- Parse and validate outputs

**Key Classes:**
```python
class StepExecutor:
    def __init__(self, llm_service: LLMService, prompt_service: PromptService)
    def execute_step(self, step_config: StepConfig, input_data: dict) -> StepResult
    def parse_output(self, raw_output: str, format: str) -> dict
```

### 3.3 Data Models

#### 3.3.1 Translation Models (src/vpsweb/models/translation.py)
```python
@dataclass
class TranslationInput:
    original_poem: str
    source_lang: str
    target_lang: str
    metadata: Optional[dict] = None

@dataclass
class InitialTranslation:
    translation: str
    notes: str
    timestamp: datetime
    model_info: dict

@dataclass
class EditorReview:
    suggestions: List[str]
    overall_assessment: str
    timestamp: datetime
    model_info: dict

@dataclass
class RevisedTranslation:
    translation: str
    notes: str
    changes_made: List[str]
    timestamp: datetime
    model_info: dict

@dataclass
class TranslationOutput:
    input: TranslationInput
    initial_translation: InitialTranslation
    editor_review: EditorReview
    revised_translation: RevisedTranslation
    full_log: str
    metadata: dict
```

### 3.4 LLM Service Layer

#### 3.4.1 Base LLM Provider (src/vpsweb/services/llm/base.py)
```python
class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(self, messages: List[dict], **kwargs) -> str
    
    @abstractmethod
    def validate_config(self, config: dict) -> bool
    
    def format_messages(self, system: str, user: str) -> List[dict]
    def handle_error(self, error: Exception) -> None
```

#### 3.4.2 Provider Implementations
- **TongyiProvider** (src/vpsweb/services/llm/tongyi.py)
- **DeepSeekProvider** (src/vpsweb/services/llm/deepseek.py)

Each implements the base interface with provider-specific API calls.

### 3.5 Prompt Template Service (src/vpsweb/services/prompts.py)
```python
class PromptService:
    def __init__(self, prompts_dir: str)
    def load_template(self, template_name: str) -> PromptTemplate
    def render(self, template_name: str, variables: dict) -> tuple[str, str]
    def validate_variables(self, template: PromptTemplate, variables: dict) -> bool
```

### 3.6 XML/JSON Parser (src/vpsweb/services/parser.py)
```python
class OutputParser:
    @staticmethod
    def parse_xml(xml_string: str) -> dict
    
    @staticmethod
    def extract_tags(xml_string: str, tags: List[str]) -> dict
    
    @staticmethod
    def validate_output(parsed_data: dict, required_fields: List[str]) -> bool
```

### 3.7 Storage Handler (src/vpsweb/utils/storage.py)
```python
class StorageHandler:
    def __init__(self, output_dir: str)
    def save_translation(self, output: TranslationOutput) -> str
    def load_translation(self, file_path: str) -> TranslationOutput
    def generate_filename(self, input: TranslationInput) -> str
```

---

## 4. Workflow Execution Flow

### 4.1 Step-by-Step Process

```
1. INPUT VALIDATION
   ├─→ Validate source/target languages
   ├─→ Check poem text validity
   └─→ Load configuration

2. INITIAL TRANSLATION
   ├─→ Load prompt template
   ├─→ Render with variables (source_lang, target_lang, original_poem)
   ├─→ Call Tongyi LLM (qwen-max-latest)
   ├─→ Parse XML output (<initial_translation>, <initial_translation_notes>)
   ├─→ Validate parsed output
   └─→ Store in TranslationOutput object

3. EDITOR REVIEW
   ├─→ Load prompt template
   ├─→ Render with variables (including initial translation)
   ├─→ Call DeepSeek LLM (deepseek-reasoner)
   ├─→ Extract numbered suggestions
   ├─→ Store in TranslationOutput object

4. TRANSLATOR REVISION
   ├─→ Load prompt template
   ├─→ Render with variables (including editor suggestions)
   ├─→ Call Tongyi LLM (qwen-max-0919)
   ├─→ Parse XML output (<revised_translation>, <revised_translation_notes>)
   ├─→ Validate parsed output
   └─→ Store in TranslationOutput object

5. FINAL OUTPUT
   ├─→ Compile full translation log
   ├─→ Generate JSON output file
   ├─→ Save to outputs directory
   └─→ Return TranslationOutput object
```

### 4.2 Data Flow Diagram
```
[Original Poem] 
    │
    ├─→ [Initial Translation LLM]
    │       │
    │       ├─→ translation text
    │       └─→ translation notes
    │
    ├─→ [Editor Review LLM]
    │       │
    │       └─→ suggestions list
    │
    └─→ [Translator Revision LLM]
            │
            ├─→ revised translation
            └─→ revision notes
                    │
                    └─→ [Final JSON Output]
```

---

## 5. CLI Interface Design

### 5.1 Command Structure
```bash
# Basic usage
vpsweb translate --input poem.txt --source English --target Chinese

# With custom config
vpsweb translate --input poem.txt --source English --target Chinese --config custom.yaml

# From stdin
echo "Poem text..." | vpsweb translate --source English --target Chinese

# Batch processing
vpsweb batch --input-dir poems/ --source English --target Chinese

# Show configuration
vpsweb config show

# Validate configuration
vpsweb config validate
```

### 5.2 CLI Arguments
```python
vpsweb translate
  --input, -i         Input poem file path
  --source, -s        Source language (English, Chinese, Polish)
  --target, -t        Target language (English, Chinese)
  --config, -c        Custom configuration file
  --output, -o        Output directory
  --verbose, -v       Verbose logging
  --dry-run          Validate without execution
```

---

## 6. Output Format Specification

### 6.1 JSON Output Structure
```json
{
  "metadata": {
    "workflow_version": "1.0.0",
    "execution_id": "uuid",
    "timestamp": "2025-10-03T12:00:00Z",
    "duration_seconds": 45.3
  },
  "input": {
    "original_poem": "...",
    "source_lang": "English",
    "target_lang": "Chinese"
  },
  "stages": {
    "initial_translation": {
      "translation": "...",
      "notes": "...",
      "model": "qwen-max-latest",
      "timestamp": "2025-10-03T12:00:15Z",
      "tokens_used": 1234
    },
    "editor_review": {
      "suggestions": ["1. ...", "2. ...", "..."],
      "overall_assessment": "...",
      "model": "deepseek-reasoner",
      "timestamp": "2025-10-03T12:00:30Z",
      "tokens_used": 2345
    },
    "revised_translation": {
      "translation": "...",
      "notes": "...",
      "model": "qwen-max-0919",
      "timestamp": "2025-10-03T12:00:45Z",
      "tokens_used": 1567
    }
  },
  "full_log": "Complete workflow log...",
  "status": "completed"
}
```

---

## 7. Error Handling Strategy

### 7.1 Error Categories
1. **Configuration Errors**
   - Missing API keys
   - Invalid model names
   - Malformed YAML/JSON

2. **Input Validation Errors**
   - Empty poem text
   - Unsupported languages
   - Invalid file formats

3. **LLM Provider Errors**
   - API connection failures
   - Rate limiting
   - Invalid responses

4. **Parsing Errors**
   - Malformed XML output
   - Missing required tags
   - Invalid JSON

### 7.2 Error Handling Approach
```python
class VPSWebError(Exception):
    """Base exception for vpsweb"""

class ConfigurationError(VPSWebError):
    """Configuration-related errors"""

class ValidationError(VPSWebError):
    """Input validation errors"""

class LLMProviderError(VPSWebError):
    """LLM provider errors"""

class ParsingError(VPSWebError):
    """Output parsing errors"""
```

### 7.3 Retry Strategy
- **LLM API Calls:** 3 retries with exponential backoff
- **Configuration Loading:** Fail fast
- **Output Parsing:** 2 retries with different parsing strategies

---

## 8. Testing Strategy

### 8.1 Unit Tests
- Configuration loading and validation
- Prompt template rendering
- XML/JSON parsing
- Data model validation
- Individual LLM provider mocking

### 8.2 Integration Tests
- Full workflow execution with mocked LLMs
- Pipeline stage coordination
- Error handling flows
- Storage operations

### 8.3 End-to-End Tests
- Complete translation workflow (requires API keys)
- Multiple language combinations
- Error scenarios
- Output validation

### 8.4 Test Coverage Target
- Minimum 80% code coverage
- 100% coverage for critical paths (workflow execution, parsing)

---

## 9. Documentation Requirements

### 9.1 README.md
- Project overview and purpose
- Installation instructions
- Quick start guide
- Configuration guide
- CLI usage examples
- Troubleshooting

### 9.2 API Documentation
- Auto-generated from docstrings
- Service interfaces
- Data model schemas
- Configuration options

### 9.3 Developer Guide
- Architecture overview
- Adding new LLM providers
- Customizing prompts
- Extending workflows

---

## 10. Development Roadmap

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Project structure setup
- [ ] Configuration system
- [ ] Base LLM provider interface
- [ ] Data models
- [ ] Basic CLI

### Phase 2: Workflow Implementation (Week 3-4)
- [ ] Workflow manager
- [ ] Pipeline builder
- [ ] Step executor
- [ ] LLM provider implementations (Tongyi, DeepSeek)
- [ ] Prompt template service

### Phase 3: Parsing & Storage (Week 5)
- [ ] XML/JSON parser
- [ ] Storage handler
- [ ] Output formatter
- [ ] Logging system

### Phase 4: Testing & Polish (Week 6)
- [ ] Unit tests
- [ ] Integration tests
- [ ] End-to-end tests
- [ ] Documentation
- [ ] Examples

### Phase 5: Advanced Features (Future)
- [ ] Web interface
- [ ] Batch processing optimization
- [ ] Additional LLM providers
- [ ] Translation quality metrics
- [ ] Parallel execution

---

## 11. Dependencies

### 11.1 Core Dependencies
```
pyyaml>=6.0
pydantic>=2.0
click>=8.0
python-dotenv>=1.0
requests>=2.31
httpx>=0.24
```

### 11.2 Development Dependencies
```
pytest>=7.4
pytest-cov>=4.1
black>=23.0
flake8>=6.1
mypy>=1.5
```

---

## 12. Security Considerations

### 12.1 API Key Management
- Store API keys in environment variables only
- Never commit API keys to repository
- Support `.env` file loading
- Validate API key presence at runtime

### 12.2 Input Validation
- Sanitize all user inputs
- Validate file paths to prevent directory traversal
- Limit poem text length to prevent abuse

### 12.3 Output Security
- Sanitize output filenames
- Prevent overwriting system files
- Validate JSON before writing

---

## 13. Performance Considerations

### 13.1 Optimization Targets
- LLM API call latency: Primary bottleneck (30-60s per call)
- Configuration loading: < 100ms
- Output generation: < 1s
- Total workflow: 2-3 minutes for typical poem

### 13.2 Caching Strategy
- Cache parsed prompts in memory
- Optional caching of LLM responses (for development/testing)
- Configuration hot-reload support

---

## 14. Monitoring & Logging

### 14.1 Logging Levels
- **DEBUG:** Detailed execution flow, variable values
- **INFO:** Stage completion, timing information
- **WARNING:** Retry attempts, fallback strategies
- **ERROR:** Failures, exceptions
- **CRITICAL:** System-level failures

### 14.2 Metrics to Track
- Execution time per stage
- Token usage per LLM call
- Success/failure rates
- Error types and frequencies

---

## 15. Deployment Considerations

### 15.1 Environment Variables
```bash
TONGYI_API_KEY=<your-api-key>
DEEPSEEK_API_KEY=<your-api-key>
VPSWEB_CONFIG_PATH=<custom-config-path>
VPSWEB_OUTPUT_DIR=<output-directory>
VPSWEB_LOG_LEVEL=INFO
```

### 15.2 Docker Support (Future)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["vpsweb"]
```

---

## 16. Success Criteria

### 16.1 Functional Requirements ✓
- [ ] Executes complete translation workflow
- [ ] Produces structured JSON output
- [ ] Supports multiple LLM providers
- [ ] Configurable via YAML files
- [ ] CLI interface working
- [ ] Error handling implemented

### 16.2 Quality Requirements ✓
- [ ] 80%+ test coverage
- [ ] Type hints throughout
- [ ] Comprehensive documentation
- [ ] Follows PEP 8 style guide
- [ ] No security vulnerabilities

### 16.3 Performance Requirements ✓
- [ ] Completes workflow in < 3 minutes
- [ ] Configuration loads in < 100ms
- [ ] Handles poems up to 2000 characters

---

## 17. Future Enhancements

1. **Web Interface:** Flask/FastAPI web service
2. **Batch Processing:** Parallel execution of multiple translations
3. **Quality Metrics:** Automated translation quality assessment
4. **Additional Providers:** OpenAI, Anthropic, local models
5. **Workflow Customization:** User-defined pipeline stages
6. **Translation Memory:** Reuse previous translations
7. **Collaborative Features:** Multi-user workflow support

---

## Appendix A: Dify DSL Mapping

| Dify Component | Python Equivalent |
|----------------|-------------------|
| Start Node | `TranslationInput` dataclass |
| LLM Nodes | `LLMService` + provider implementations |
| Code Nodes (XML parsing) | `OutputParser.parse_xml()` |
| Template Transform | `PromptService.render()` |
| End Node | `TranslationOutput` + `StorageHandler` |
| Variables | Configuration system + data models |

---

## Appendix B: Prompt Template Examples

See `config/prompts/` directory for full templates with variable substitution markers.

---

**Document Version:** 1.0  
**Last Updated:** 2025-10-03  
**Author:** Product Specification Team  
**Status:** Ready for Implementation