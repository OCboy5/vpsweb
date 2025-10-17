Product Specifications Document (PSD)
Vox Poetica Studio Web (vpsweb) v1.0

Document Information

Version: 1.0
Date: October 4, 2025
Status: Ready for Implementation
Target: GitHub Repository with Claude Code Implementation


1. Executive Summary
1.1 Project Overview
vpsweb (Vox Poetica Studio Web) is a professional poetry translation system that replicates a collaborative "Translator → Editor → Translator" workflow through AI agents. The system converts a proven Dify workflow into a modular, configurable Python application that produces high-fidelity translations preserving the original poem's aesthetic beauty, musicality, emotional resonance, and cultural context.
1.2 Core Value Proposition

Professional Quality: Multi-stage iterative translation mimicking real-world studio workflows
Configurability: All models, prompts, and parameters externalized via YAML
Structured Pipeline: Clean data flow with validated inputs/outputs at each stage
GitHub-Native: Full CI/CD, testing, documentation following best practices
Future-Ready: Designed for easy web UI integration (Phase 2)

1.3 Primary Use Cases

Translating poetry between English, Chinese, and Polish
Producing publication-quality translations with editorial oversight
Generating detailed translation rationales and editorial feedback
Batch processing multiple poems with consistent quality


2. System Architecture
2.1 High-Level Design
┌──────────────────────────────────────────────────────┐
│              Configuration Layer                     │
│  (config/*.yaml - models, prompts, workflow)         │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│           Workflow Orchestration Layer               │
│  ┌────────────┐  ┌──────────┐  ┌──────────────┐      │
│  │  Pipeline  │→ │ Executor │→ │ State Manager│      │
│  │  Builder   │  │  Engine  │  │              │      │
│  └────────────┘  └──────────┘  └──────────────┘      │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│              Translation Agents Layer                │
│  ┌─────────────┐ ┌──────────┐ ┌─────────────┐        │
│  │ Translator  │→│  Editor  │→│ Translator  │        │
│  │ (Initial)   │ │ (Review) │ │ (Revision)  │        │
│  └─────────────┘ └──────────┘ └─────────────┘        │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│              LLM Provider Layer                      │
│  ┌──────────────┐  ┌──────────────┐                  │
│  │ Tongyi/Qwen  │  │  DeepSeek    │                  │
│  │  (OpenAI     │  │  (OpenAI     │  [Extensible]    │
│  │ Compatible)  │  │ Compatible)  │                  │
│  └──────────────┘  └──────────────┘                  │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│              Data Persistence Layer                  │
│  (JSON outputs, structured artifacts)                │
└──────────────────────────────────────────────────────┘
2.2 Directory Structure
vpsweb/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # CI/CD pipeline
│   │   └── release.yml               # Release automation
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── config/
│   ├── default.yaml                  # Main configuration
│   ├── models.yaml                   # Model provider configs
│   └── prompts/                      # Prompt templates
│       ├── initial_translation.yaml
│       ├── editor_review.yaml
│       └── translator_revision.yaml
├── src/vpsweb/
│   ├── __init__.py
│   ├── __main__.py                   # CLI entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── workflow.py               # Main orchestrator
│   │   ├── pipeline.py               # Pipeline builder
│   │   └── executor.py               # Step executor
│   ├── models/
│   │   ├── __init__.py
│   │   ├── translation.py            # Pydantic data models
│   │   └── config.py                 # Configuration models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # Abstract base client
│   │   │   ├── openai_compatible.py  # OpenAI-compatible API
│   │   │   └── factory.py            # Provider factory
│   │   ├── prompts.py                # Prompt template manager
│   │   └── parser.py                 # XML/JSON response parser
│   └── utils/
│       ├── __init__.py
│       ├── config_loader.py          # YAML config loader
│       ├── logger.py                 # Structured logging
│       └── storage.py                # JSON file I/O
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Pytest fixtures
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│       └── sample_poems/
├── examples/
│   ├── basic_usage.py
│   └── poems/
├── outputs/                          # Gitignored output directory
│   └── .gitkeep
├── docs/
│   ├── README.md
│   ├── configuration.md
│   └── api_reference.md
├── .env.example                      # Template for API keys
├── .gitignore
├── LICENSE                           # MIT License
├── README.md
├── pyproject.toml                    # Poetry configuration
└── requirements.txt                  # Pip requirements

3. Core Components Specification
3.1 Data Models (Pydantic)
python# src/vpsweb/models/translation.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class TranslationInput(BaseModel):
    """Input for translation workflow"""
    original_poem: str = Field(..., min_length=1, max_length=5000)
    source_lang: str = Field(..., pattern="^(English|Chinese|Polish)$")
    target_lang: str = Field(..., pattern="^(English|Chinese|Polish)$")
    metadata: Optional[Dict] = None

class InitialTranslation(BaseModel):
    """Output from initial translation step"""
    translation: str
    notes: str
    timestamp: datetime
    model_info: Dict[str, str]
    tokens_used: int

class EditorReview(BaseModel):
    """Output from editor review step"""
    suggestions: List[str]
    overall_assessment: str
    timestamp: datetime
    model_info: Dict[str, str]
    tokens_used: int

class RevisedTranslation(BaseModel):
    """Output from translator revision step"""
    translation: str
    notes: str
    changes_made: List[str]
    timestamp: datetime
    model_info: Dict[str, str]
    tokens_used: int

class TranslationOutput(BaseModel):
    """Complete workflow output"""
    workflow_id: str
    input: TranslationInput
    initial_translation: InitialTranslation
    editor_review: EditorReview
    revised_translation: RevisedTranslation
    full_log: str
    total_tokens: int
    duration_seconds: float
3.2 Configuration Schema
yaml# config/default.yaml

workflow:
  name: "vox_poetica_translation"
  version: "1.0.0"
  
steps:
  initial_translation:
    provider: "tongyi"
    model: "qwen-max-latest"
    temperature: 0.7
    max_tokens: 4096
    prompt_template: "prompts/initial_translation.yaml"
    
  editor_review:
    provider: "deepseek"
    model: "deepseek-reasoner"
    temperature: 0.3
    max_tokens: 8192
    prompt_template: "prompts/editor_review.yaml"
    
  translator_revision:
    provider: "tongyi"
    model: "qwen-max-0919"
    temperature: 0.2
    max_tokens: 8001
    prompt_template: "prompts/translator_revision.yaml"

storage:
  output_dir: "outputs"
  format: "json"
  include_timestamp: true
  
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "vpsweb.log"
yaml# config/models.yaml

providers:
  tongyi:
    api_key_env: "TONGYI_API_KEY"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    type: "openai_compatible"
    models:
      - "qwen-max-latest"
      - "qwen-max-0919"
    
  deepseek:
    api_key_env: "DEEPSEEK_API_KEY"
    base_url: "https://api.deepseek.com/v1"
    type: "openai_compatible"
    models:
      - "deepseek-reasoner"
      - "deepseek-chat"
3.3 LLM Service Layer
python# src/vpsweb/services/llm/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate completion from messages"""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict) -> bool:
        """Validate provider configuration"""
        pass

# src/vpsweb/services/llm/openai_compatible.py

import os
import httpx
from .base import BaseLLMProvider

class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI-compatible API provider (Tongyi, DeepSeek, etc.)"""
    
    def __init__(self, base_url: str, api_key_env: str):
        self.base_url = base_url
        self.api_key = os.getenv(api_key_env)
        if not self.api_key:
            raise ValueError(f"Missing API key: {api_key_env}")
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **kwargs
                },
                timeout=120.0
            )
            response.raise_for_status()
            return response.json()
3.4 Workflow Orchestrator
python# src/vpsweb/core/workflow.py

from typing import Dict
from ..models.translation import (
    TranslationInput,
    TranslationOutput,
    InitialTranslation,
    EditorReview,
    RevisedTranslation
)
from ..services.llm.factory import LLMFactory
from ..services.prompts import PromptService
from ..services.parser import OutputParser
from ..utils.logger import get_logger

logger = get_logger(__name__)

class TranslationWorkflow:
    """Main orchestrator for the T-E-T translation workflow"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.llm_factory = LLMFactory(config['models'])
        self.prompt_service = PromptService(config['prompts'])
        self.parser = OutputParser()
    
    async def execute(self, input_data: TranslationInput) -> TranslationOutput:
        """Execute complete translation workflow"""
        logger.info(f"Starting translation: {input_data.source_lang} → {input_data.target_lang}")
        
        # Step 1: Initial Translation
        initial = await self._initial_translation(input_data)
        
        # Step 2: Editor Review
        review = await self._editor_review(input_data, initial)
        
        # Step 3: Translator Revision
        revised = await self._translator_revision(input_data, initial, review)
        
        # Aggregate results
        return self._aggregate_output(input_data, initial, review, revised)
    
    async def _initial_translation(self, input_data: TranslationInput) -> InitialTranslation:
        """Step 1: Initial translation"""
        # Implementation details...
        pass
    
    async def _editor_review(
        self,
        input_data: TranslationInput,
        initial: InitialTranslation
    ) -> EditorReview:
        """Step 2: Editorial review"""
        # Implementation details...
        pass
    
    async def _translator_revision(
        self,
        input_data: TranslationInput,
        initial: InitialTranslation,
        review: EditorReview
    ) -> RevisedTranslation:
        """Step 3: Translator revision"""
        # Implementation details...
        pass

4. CLI Interface
4.1 Command Structure
bash# Basic usage
vpsweb translate --input poem.txt --source English --target Chinese

# With custom config
vpsweb translate --input poem.txt --source English --target Chinese \
  --config custom_config.yaml

# From stdin
echo "Poem text..." | vpsweb translate --source English --target Chinese

# Output to specific directory
vpsweb translate --input poem.txt --source English --target Chinese \
  --output ./my_translations/

# Verbose logging
vpsweb translate --input poem.txt --source English --target Chinese -v

# Dry run (validation only)
vpsweb translate --input poem.txt --source English --target Chinese --dry-run
4.2 CLI Implementation
python# src/vpsweb/__main__.py

import click
import asyncio
from pathlib import Path
from .core.workflow import TranslationWorkflow
from .models.translation import TranslationInput
from .utils.config_loader import load_config
from .utils.logger import get_logger

@click.group()
def cli():
    """Vox Poetica Studio Web - Professional Poetry Translation"""
    pass

@cli.command()
@click.option('--input', '-i', type=click.Path(exists=True), help='Input poem file')
@click.option('--source', '-s', required=True, type=click.Choice(['English', 'Chinese', 'Polish']))
@click.option('--target', '-t', required=True, type=click.Choice(['English', 'Chinese']))
@click.option('--config', '-c', type=click.Path(exists=True), help='Custom config file')
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
@click.option('--dry-run', is_flag=True, help='Validate without execution')
def translate(input, source, target, config, output, verbose, dry_run):
    """Translate a poem using the T-E-T workflow"""
    asyncio.run(_translate(input, source, target, config, output, verbose, dry_run))

async def _translate(input_path, source, target, config_path, output_dir, verbose, dry_run):
    # Implementation...
    pass

if __name__ == '__main__':
    cli()

5. Testing Strategy
5.1 Test Coverage Requirements

Unit Tests: 80% minimum coverage
Integration Tests: All workflow paths
End-to-End Tests: Complete translation workflows with mocked LLMs

5.2 Test Structure
python# tests/conftest.py

import pytest
from vpsweb.models.translation import TranslationInput

@pytest.fixture
def sample_poem():
    return TranslationInput(
        original_poem="The fog comes\non little cat feet.",
        source_lang="English",
        target_lang="Chinese"
    )

@pytest.fixture
def mock_llm_response():
    return {
        "choices": [{
            "message": {
                "content": "<translation>雾来了\n踏着猫的小脚。</translation><notes>...</notes>"
            }
        }],
        "usage": {"total_tokens": 150}
    }

# tests/unit/test_parser.py

def test_xml_extraction():
    xml_string = "<translation>Text</translation><notes>Notes</notes>"
    result = OutputParser.parse_xml(xml_string)
    assert result['translation'] == 'Text'
    assert result['notes'] == 'Notes'

# tests/integration/test_workflow.py

@pytest.mark.asyncio
async def test_complete_workflow(sample_poem, mock_llm_responses):
    # Test complete T-E-T workflow with mocked LLM calls
    pass

6. GitHub Repository Setup
6.1 Essential Files
markdown# README.md

# Vox Poetica Studio Web (vpsweb)

Professional AI-powered poetry translation using a Translator→Editor→Translator workflow.

## Features
- ✨ Multi-stage collaborative translation
- 🔧 Fully configurable via YAML
- 🌍 Support for English, Chinese, Polish
- 📊 Structured JSON outputs
- 🚀 CLI and Python API

## Quick Start
\`\`\`bash
pip install vpsweb
vpsweb translate --input poem.txt --source English --target Chinese
\`\`\`

## Configuration
See [docs/configuration.md](docs/configuration.md)

## License
MIT
yaml# .github/workflows/ci.yml

name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        pip install -e .[dev]
    - name: Run tests
      run: |
        pytest --cov=vpsweb tests/
    - name: Lint
      run: |
        flake8 src/
        black --check src/

7. Implementation Phases
Phase 1: Foundation (Week 1)

 Repository setup
 Project structure
 Configuration system
 Data models (Pydantic)
 Basic CLI skeleton

Phase 2: Core Logic (Week 2)

 LLM provider abstraction
 Prompt template service
 XML/JSON parser
 Workflow orchestrator
 Step executors

Phase 3: Integration (Week 3)

 End-to-end workflow
 Storage handler
 Error handling
 Logging system
 CLI completion

Phase 4: Quality & Documentation (Week 4)

 Unit tests (80%+ coverage)
 Integration tests
 Documentation
 Examples
 GitHub CI/CD


8. Success Criteria
✅ Functional Requirements

Executes complete T-E-T workflow
Produces structured JSON output matching Dify workflow
Supports multiple LLM providers
CLI interface fully functional

✅ Quality Requirements

80%+ test coverage
Type hints throughout
PEP 8 compliant
Comprehensive documentation

✅ Performance Requirements

Completes workflow in < 3 minutes
Handles poems up to 2000 characters
Graceful error handling and retries