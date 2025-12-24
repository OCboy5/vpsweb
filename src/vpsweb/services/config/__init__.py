"""
Configuration Services Module

This module provides the new configuration abstraction layer that centralizes
all configuration access patterns and provides a clean interface for the rest
of the application.

Phase 1 Implementation:
- No changes to existing YAML files or Pydantic models
- Pure abstraction layer over existing configuration structure
- Backward compatible with all current usage patterns
"""

from .facade import ConfigFacade, get_config_facade, initialize_config_facade
from .model_registry_service import ModelInfo, ModelRegistryService, ProviderInfo
from .model_service import ModelService
from .system_service import SystemService
from .task_template_service import ResolvedTaskConfig, TaskTemplate, TaskTemplateService
from .workflow_service import WorkflowService

__all__ = [
    "ConfigFacade",
    "get_config_facade",
    "initialize_config_facade",
    "WorkflowService",
    "ModelService",
    "SystemService",
    "ModelRegistryService",
    "ModelInfo",
    "ProviderInfo",
    "TaskTemplateService",
    "TaskTemplate",
    "ResolvedTaskConfig",
]
