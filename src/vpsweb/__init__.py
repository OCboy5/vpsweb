"""
Vox Poetica Studio Web - Professional AI-powered poetry translation system.

This package provides a modular Python application for professional poetry
translation using a Translator→Editor→Translator workflow that produces
high-fidelity translations preserving aesthetic beauty, musicality, emotional
resonance, and cultural context.

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

__version__ = "0.7.3"
__author__ = "Vox Poetica Studio"
__description__ = "Professional AI-powered poetry translation system"

# CLI entry point
from .__main__ import cli
from .core.executor import StepExecutor

# Core components
from .core.workflow import TranslationWorkflow
from .models.config import (
    LoggingConfig,
    ModelProviderConfig,
    StepConfig,
    TaskTemplateStepConfig,
    WorkflowConfig,
)

# Data models
from .models.translation import (
    EditorReview,
    InitialTranslation,
    RevisedTranslation,
    TranslationInput,
    TranslationOutput,
)
from .services.config import ConfigFacade, get_config_facade, initialize_config_facade

# Services
from .services.llm.factory import LLMFactory
from .services.parser import OutputParser
from .services.prompts import PromptService
from .utils.config_loader import load_model_registry_config, load_task_templates_config

# Utilities
from .utils.logger import get_logger, setup_logging
from .utils.storage import StorageHandler

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
    "TaskTemplateStepConfig",
    "ModelProviderConfig",
    "LoggingConfig",
    "StepConfig",
    # Services
    "LLMFactory",
    "PromptService",
    "OutputParser",
    # Utilities
    "setup_logging",
    "get_logger",
    "load_model_registry_config",
    "load_task_templates_config",
    "StorageHandler",
    "ConfigFacade",
    "get_config_facade",
    "initialize_config_facade",
    # CLI
    "cli",
]
