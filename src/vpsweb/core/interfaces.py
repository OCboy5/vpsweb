"""
Core Interfaces for Phase 3 Refactoring.

This module defines the core interfaces that will be used throughout
the Phase 3 refactoring to enable better modularity and testability.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
from dataclasses import dataclass
from enum import Enum
import asyncio


# ============================================================================
# LLM Provider Interfaces
# ============================================================================

@dataclass
class LLMRequest:
    """Request object for LLM generation."""
    messages: List[Dict[str, str]]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    model: Optional[str] = None
    timeout: float = 30.0
    stream: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMResponse:
    """Response object from LLM generation."""
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    execution_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMStreamChunk:
    """Single chunk from streaming LLM response."""
    content: str
    is_final: bool = False
    metadata: Optional[Dict[str, Any]] = None


class ILLMProvider(ABC):
    """Interface for LLM providers."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            request: The generation request

        Returns:
            LLM response
        """
        pass

    @abstractmethod
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Generate a streaming response from the LLM.

        Args:
            request: The generation request

        Yields:
            Stream chunks
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name."""
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate provider configuration."""
        pass


class ILLMFactory(ABC):
    """Interface for LLM provider factory."""

    @abstractmethod
    def get_provider(self, provider_name: str) -> ILLMProvider:
        """Get a provider instance by name."""
        pass

    @abstractmethod
    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """Get provider configuration."""
        pass

    @abstractmethod
    def list_providers(self) -> List[str]:
        """List all available providers."""
        pass

    @abstractmethod
    def register_provider(self, name: str, provider_class: type, config: Dict[str, Any]) -> None:
        """Register a new provider."""
        pass


# ============================================================================
# Prompt Service Interfaces
# ============================================================================

@dataclass
class PromptTemplate:
    """Prompt template definition."""
    name: str
    template_content: str
    variables: List[str]
    metadata: Optional[Dict[str, Any]] = None


class IPromptService(ABC):
    """Interface for prompt management services."""

    @abstractmethod
    async def render_prompt(
        self,
        template_name: str,
        variables: Dict[str, Any],
        template_path: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Render a prompt template with variables.

        Args:
            template_name: Name of the template
            variables: Variables to substitute
            template_path: Optional custom template path

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        pass

    @abstractmethod
    def list_templates(self) -> List[str]:
        """List all available template names."""
        pass

    @abstractmethod
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a template by name."""
        pass

    @abstractmethod
    def validate_template(self, template_content: str) -> List[str]:
        """
        Validate template content and return list of variables.

        Args:
            template_content: The template content to validate

        Returns:
            List of variable names found in template
        """
        pass

    @abstractmethod
    async def register_template(self, template: PromptTemplate) -> None:
        """Register a new template."""
        pass


# ============================================================================
# Output Parser Interfaces
# ============================================================================

class ParsingResult(Enum):
    """Result of output parsing."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class ParsedOutput:
    """Result of parsing LLM output."""
    content: Dict[str, Any]
    result_type: ParsingResult
    errors: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class IOutputParser(ABC):
    """Interface for output parsing services."""

    @abstractmethod
    def parse_xml(self, output: str, expected_fields: Optional[List[str]] = None) -> ParsedOutput:
        """
        Parse XML output from LLM.

        Args:
            output: Raw LLM output
            expected_fields: Optional list of expected fields

        Returns:
            Parsed output result
        """
        pass

    @abstractmethod
    def parse_json(self, output: str, expected_fields: Optional[List[str]] = None) -> ParsedOutput:
        """
        Parse JSON output from LLM.

        Args:
            output: Raw LLM output
            expected_fields: Optional list of expected fields

        Returns:
            Parsed output result
        """
        pass

    @abstractmethod
    def extract_code_blocks(self, output: str, language: Optional[str] = None) -> List[str]:
        """
        Extract code blocks from output.

        Args:
            output: Raw LLM output
            language: Optional language filter

        Returns:
            List of code block contents
        """
        pass

    @abstractmethod
    def validate_output(self, parsed_output: ParsedOutput, schema: Dict[str, Any]) -> bool:
        """
        Validate parsed output against a schema.

        Args:
            parsed_output: The parsed output to validate
            schema: Validation schema

        Returns:
            True if valid, False otherwise
        """
        pass


# ============================================================================
# Workflow Orchestration Interfaces
# ============================================================================

class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """Single workflow step definition."""
    name: str
    provider: str
    model: str
    prompt_template: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: float = 30.0
    retry_attempts: int = 3
    required_fields: Optional[List[str]] = None


@dataclass
class WorkflowConfig:
    """Workflow configuration."""
    name: str
    description: Optional[str] = None
    steps: List[WorkflowStep] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.steps is None:
            self.steps = []


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    status: WorkflowStatus
    steps_executed: int
    total_tokens_used: int
    execution_time: float
    results: Dict[str, Any]
    errors: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class IWorkflowOrchestrator(ABC):
    """Interface for workflow orchestration."""

    @abstractmethod
    async def execute_workflow(
        self,
        config: WorkflowConfig,
        input_data: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> WorkflowResult:
        """
        Execute a complete workflow.

        Args:
            config: Workflow configuration
            input_data: Input data for the workflow
            progress_callback: Optional progress callback

        Returns:
            Workflow execution result
        """
        pass

    @abstractmethod
    async def execute_step(
        self,
        step: WorkflowStep,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single workflow step.

        Args:
            step: Workflow step to execute
            input_data: Input data for the step

        Returns:
            Step execution result
        """
        pass

    @abstractmethod
    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowStatus]:
        """Get the status of a running workflow."""
        pass

    @abstractmethod
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        pass

    @abstractmethod
    def list_workflows(self) -> List[str]:
        """List all available workflow configurations."""
        pass


# ============================================================================
# Configuration Management Interfaces
# ============================================================================

class IConfigurationService(ABC):
    """Interface for configuration management."""

    @abstractmethod
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        pass

    @abstractmethod
    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        pass

    @abstractmethod
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section."""
        pass

    @abstractmethod
    def reload_config(self) -> None:
        """Reload configuration from source."""
        pass

    @abstractmethod
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of errors."""
        pass


# ============================================================================
# Storage and Repository Interfaces
# ============================================================================

@dataclass
class StorageResult:
    """Result of storage operations."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IStorageService(ABC):
    """Interface for storage operations."""

    @abstractmethod
    async def save(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> StorageResult:
        """Save data with a key."""
        pass

    @abstractmethod
    async def load(self, key: str) -> StorageResult:
        """Load data by key."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> StorageResult:
        """Delete data by key."""
        pass

    @abstractmethod
    async def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List keys with optional prefix filter."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass


# ============================================================================
# Logging and Monitoring Interfaces
# ============================================================================

@dataclass
class LogEntry:
    """Log entry structure."""
    level: str
    message: str
    component: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ILogger(ABC):
    """Interface for logging services."""

    @abstractmethod
    def log(self, level: str, message: str, component: str, **kwargs) -> None:
        """Log a message."""
        pass

    @abstractmethod
    def debug(self, message: str, component: str, **kwargs) -> None:
        """Log debug message."""
        pass

    @abstractmethod
    def info(self, message: str, component: str, **kwargs) -> None:
        """Log info message."""
        pass

    @abstractmethod
    def warning(self, message: str, component: str, **kwargs) -> None:
        """Log warning message."""
        pass

    @abstractmethod
    def error(self, message: str, component: str, **kwargs) -> None:
        """Log error message."""
        pass

    @abstractmethod
    async def log_async(self, level: str, message: str, component: str, **kwargs) -> None:
        """Log a message asynchronously."""
        pass


class IMetricsCollector(ABC):
    """Interface for metrics collection."""

    @abstractmethod
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        pass

    @abstractmethod
    def record_timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timing metric."""
        pass

    @abstractmethod
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric."""
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        pass


# ============================================================================
# Retry and Resilience Interfaces
# ============================================================================

class RetryPolicy:
    """Retry policy configuration."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter


class IRetryService(ABC):
    """Interface for retry operations."""

    @abstractmethod
    async def execute_with_retry(
        self,
        operation: callable,
        policy: RetryPolicy,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an operation with retry logic.

        Args:
            operation: The operation to execute
            policy: Retry policy to apply
            *args: Operation arguments
            **kwargs: Operation keyword arguments

        Returns:
            Operation result
        """
        pass

    @abstractmethod
    async def should_retry(self, exception: Exception, attempt: int, policy: RetryPolicy) -> bool:
        """Determine if operation should be retried."""
        pass


# ============================================================================
# Event System Interfaces
# ============================================================================

@dataclass
class Event:
    """Event structure."""
    name: str
    data: Dict[str, Any]
    source: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IEventBus(ABC):
    """Interface for event bus."""

    @abstractmethod
    async def publish(self, event: Event) -> None:
        """Publish an event."""
        pass

    @abstractmethod
    def subscribe(self, event_name: str, handler: callable) -> str:
        """Subscribe to an event. Returns subscription ID."""
        pass

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from an event."""
        pass

    @abstractmethod
    async def get_events(self, filter_func: Optional[callable] = None) -> List[Event]:
        """Get events with optional filter."""
        pass