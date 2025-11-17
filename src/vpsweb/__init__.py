"""
Vox Poetica Studio Web - Professional AI-powered poetry translation system.

This package provides a modular Python application for professional poetry translation
using a Translator→Editor→Translator workflow that produces high-fidelity translations
preserving aesthetic beauty, musicality, emotional resonance, and cultural context.

Key Features:
- Multi-stage collaborative translation workflow
- Configurable via YAML configuration files
- Support for multiple LLM providers (Tongyi, DeepSeek, etc.)
- Structured JSON outputs with comprehensive metadata
- CLI and Python API interfaces

Example Usage:

    # CLI usage
    vpsweb translate --input poem.txt --source English --target Chinese

    # Python API usage
    from vpsweb.core.workflow import TranslationWorkflow
    from vpsweb.models.translation import TranslationInput

    workflow = TranslationWorkflow(config)
    input_data = TranslationInput(
        original_poem="The fog comes on little cat feet.",
        source_lang="English",
        target_lang="Chinese"
    )
    result = await workflow.execute(input_data)
"""

__version__ = "0.5.1"
__author__ = "Vox Poetica Studio"
__description__ = "Professional AI-powered poetry translation system"

# Core components
from .core.workflow import TranslationWorkflow
from .core.executor import StepExecutor

# Data models
from .models.translation import (
    TranslationInput,
    InitialTranslation,
    EditorReview,
    RevisedTranslation,
    TranslationOutput,
)
from .models.config import WorkflowConfig, StepConfig, CompleteConfig, LoggingConfig

# Services
from .services.llm.factory import LLMFactory
from .services.prompts import PromptService
from .services.parser import OutputParser

# Utilities
from .utils.logger import setup_logging, get_logger
from .utils.config_loader import load_config
from .utils.storage import StorageHandler

# CLI entry point
from .__main__ import cli

__all__ = [
    # Core components
    "TranslationWorkflow",
    "StepExecutor",
    # Data models
    "TranslationInput",
    "InitialTranslation",
    "EditorReview",
    "RevisedTranslation",
    "TranslationOutput",
    "WorkflowConfig",
    "StepConfig",
    "CompleteConfig",
    "LoggingConfig",
    # Services
    "LLMFactory",
    "PromptService",
    "OutputParser",
    # Utilities
    "setup_logging",
    "get_logger",
    "load_config",
    "StorageHandler",
    # CLI
    "cli",
]
