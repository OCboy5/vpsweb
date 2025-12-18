"""
Enhanced conftest for Phase 3 with dependency injection support.

This module provides enhanced fixtures for Phase 3 testing, including
dependency injection container, test databases, and advanced mock management.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, Mock

import pytest

# Phase 3 DI framework imports (will be created)
try:
    from src.vpsweb.core.container import DIContainer
    from src.vpsweb.core.interfaces import (IOutputParser, IPromptService,
                                            IWorkflowOrchestrator)
except ImportError:
    # Fallback for before DI framework is implemented
    DIContainer = None
    ILLMProvider = None
    IPromptService = None
    IOutputParser = None
    IWorkflowOrchestrator = None

from src.vpsweb.models.config import StepConfig, WorkflowConfig
from src.vpsweb.models.translation import (EditorReview, InitialTranslation,
                                           RevisedTranslation,
                                           TranslationInput)


@pytest.fixture(scope="session")
def di_container() -> Generator[DIContainer, None, None]:
    """
    Dependency injection container fixture for Phase 3 testing.

    Provides a singleton DI container across all tests, ensuring consistent
    service creation and cleanup.
    """
    container = DIContainer()

    # Register test services
    if DIContainer is not None:
        # Register mock implementations for interfaces
        container.register(ITestService, MockTestService)
        container.register(IMockProviderService, MockProviderService)
        container.register(ITestConfigService, TestConfigService)

    try:
        yield container
    finally:
        # Cleanup container resources
        if hasattr(container, "cleanup"):
            container.cleanup()


@pytest.fixture
def mock_llm_factory():
    """Mock LLM factory for testing."""
    factory = Mock()
    factory.get_provider = Mock()
    factory.get_provider_config = Mock()

    # Configure mock provider config
    mock_config = Mock()
    mock_config.name = "test_provider"
    mock_config.type = "test"
    factory.get_provider_config.return_value = mock_config

    return factory


@pytest.fixture
def mock_prompt_service():
    """Mock prompt service for testing."""
    service = Mock(spec=IPromptService)
    service.render_prompt = AsyncMock(return_value=("system_prompt", "user_prompt"))
    return service


@pytest.fixture
def mock_output_parser():
    """Mock output parser for testing."""
    parser = Mock(spec=IOutputParser)
    parser.parse_xml = Mock(return_value={"content": "parsed"})
    parser.validate_output = Mock()
    return parser


@pytest.fixture
def sample_workflow_config():
    """Sample workflow configuration for testing."""
    return WorkflowConfig(
        name="test_workflow",
        steps=[
            StepConfig(
                name="initial_translation",
                provider="openai",
                model="gpt-4",
                prompt_template="templates/initial_translation.xml",
                temperature=0.7,
                max_tokens=1000,
                timeout=30,
                retry_attempts=3,
            )
        ],
    )


@pytest.fixture
def sample_step_config():
    """Sample step configuration for testing."""
    return StepConfig(
        name="test_step",
        provider="openai",
        model="gpt-4",
        prompt_template="templates/test.xml",
        temperature=0.7,
        max_tokens=1000,
        timeout=30,
        retry_attempts=3,
        required_fields=["content"],
    )


@pytest.fixture
def enhanced_translation_input():
    """Enhanced translation input with metadata for testing."""
    return TranslationInput(
        original_poem="The fog comes on little cat feet.",
        source_lang="English",
        target_lang="Chinese",
        metadata={
            "poem_title": "Fog",
            "poet_name": "Carl Sandburg",
            "publication_year": "1916",
            "theme": "nature",
            "form": "free verse",
            "mood": "contemplative",
        },
    )


@pytest.fixture
def mock_workflow_orchestrator():
    """Mock workflow orchestrator for testing."""
    orchestrator = Mock(spec=IWorkflowOrchestrator)
    orchestrator.execute_workflow = AsyncMock()
    orchestrator.get_workflow_status = AsyncMock()
    return orchestrator


@pytest.fixture
def async_test_db():
    """
    Async test database fixture for Phase 3 testing.

    Creates a temporary SQLite database for each test function,
    with proper async support and cleanup.
    """
    async with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"

        # Import here to avoid circular imports
        from src.vpsweb.repository.database import (create_database_engine,
                                                    create_tables)

        engine = create_database_engine(db_path)
        await create_tables(engine)

        yield engine

        # Cleanup
        await engine.dispose()
        # Remove temporary directory
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_data_factory():
    """
    Test data factory for creating consistent test data.

    Provides methods to create various test objects with consistent
    patterns and default values, reducing test code duplication.
    """
    return TestDataFactory()


class TestDataFactory:
    """Factory for creating test data objects with consistent patterns."""

    def create_translation_input(self, **overrides) -> TranslationInput:
        """Create a TranslationInput with optional overrides."""
        defaults = {
            "original_poem": "The fog comes on little cat feet.",
            "source_lang": "English",
            "target_lang": "Chinese",
            "metadata": {},
        }
        defaults.update(overrides)
        return TranslationInput(**defaults)

    def create_initial_translation(self, **overrides) -> InitialTranslation:
        """Create an InitialTranslation with optional overrides."""
        defaults = {
            "initial_translation": "雾来了，悄无声息",
            "initial_translation_notes": "保持了原诗的自由诗形式",
            "translated_poem_title": "雾",
            "translated_poet_name": "卡尔·桑德堡",
            "tokens_used": 150,
            "execution_time_seconds": 2.5,
            "quality_rating": 9.0,
        }
        defaults.update(overrides)
        return InitialTranslation(**defaults)

    def create_editor_review(self, **overrides) -> EditorReview:
        """Create an EditorReview with optional overrides."""
        defaults = {
            "editor_suggestions": [
                "Consider adding more descriptive imagery",
                "Review the rhyme scheme",
            ],
            "initial_translation_with_notes": "雾来了，悄无声息（翻译笔记）",
            "overall_assessment": "Good translation but needs refinement",
            "quality_rating": 7.5,
        }
        defaults.update(overrides)
        return EditorReview(**defaults)

    def create_revised_translation(self, **overrides) -> RevisedTranslation:
        """Create a RevisedTranslation with optional overrides."""
        defaults = {
            "revised_translation": "雾来时，猫脚轻悄走过",
            "revision_notes": "改进了意象表达和韵律感",
            "final_quality_rating": 9.5,
            "changes_made": [
                "Enhanced imagery with cat imagery",
                "Improved natural flow and rhythm",
                "Better preserved poetic form",
            ],
        }
        defaults.update(overrides)
        return RevisedTranslation(**defaults)

    def create_workflow_config(self, **overrides) -> WorkflowConfig:
        """Create a WorkflowConfig with optional overrides."""
        defaults = {
            "name": "test_workflow",
            "description": "Test workflow for testing",
            "steps": [
                StepConfig(
                    name="initial_translation",
                    provider="openai",
                    model="gpt-4",
                    prompt_template="templates/test.xml",
                )
            ],
        }
        defaults.update(overrides)
        return WorkflowConfig(**defaults)


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    response = Mock()
    response.content = "Test LLM response content"
    response.tokens_used = 100
    response.prompt_tokens = 50
    response.completion_tokens = 50
    response.model = "gpt-4"
    response.provider = "openai"
    response.temperature = 0.7
    response.max_tokens = 1000
    return response


@pytest.fixture
def mock_workflow_result():
    """Mock workflow result for testing."""
    result = Mock()
    result.status = "success"
    result.execution_time = 5.2
    result.steps_executed = 3
    result.total_tokens_used = 300
    result.error = None
    result.metadata = {"test": "data"}
    return result


# Test interfaces for Phase 3
class ITestService:
    """Test service interface for Phase 3 testing."""

    def process_data(self, data: Any) -> Any:
        pass


class IMockProviderService:
    """Mock provider service interface for Phase 3 testing."""

    async def generate_response(self, _messages, **kwargs) -> Any:
        pass


class ITestConfigService:
    """Test configuration service interface for Phase 3 testing."""

    def get_test_config(self, name: str) -> Any:
        pass


# Phase 3 enhanced configuration management
@pytest.fixture
def test_config_service():
    """Test configuration service for Phase 3."""
    return TestConfigService()


class TestConfigService:
    """Test configuration service implementation."""

    def __init__(self):
        self.configs = {
            "workflow": {
                "max_retries": 3,
                "timeout": 30,
                "temperature": 0.7,
                "max_tokens": 1000,
            },
            "testing": {
                "assertions_enabled": True,
                "mock_external_services": True,
                "performance_monitoring": False,
            },
        }

    def get_test_config(self, name: str) -> Dict[str, Any]:
        """Get configuration by name."""
        return self.configs.get(name, {})

    def update_config(self, name: str, **overrides):
        """Update configuration by name."""
        if name in self.configs:
            self.configs[name].update(overrides)

    def reset_config(self, name: str):
        """Reset configuration to defaults."""
        self.configs[name] = {
            "workflow": {
                "max_retries": 3,
                "timeout": 30,
                "temperature": 0.7,
                "max_tokens": 1000,
            },
            "testing": {
                "assertions_enabled": True,
                "mock_external_services": True,
                "performance_monitoring": False,
            },
        }


# Performance testing fixtures
@pytest.fixture
def performance_monitor():
    """Performance monitor fixture for Phase 3 testing."""
    return PerformanceMonitor()


class PerformanceMonitor:
    """Performance monitoring implementation."""

    def __init__(self):
        self.metrics = {}
        self.start_time = None

    def start_timer(self, name: str):
        """Start timing measurement."""
        import time

        self.start_time = time.time()
        self.metrics[name] = {"start_time": self.start_time}

    def end_timer(self, name: str):
        """End timing measurement."""
        import time

        if name in self.metrics and self.start_time:
            end_time = time.time()
            self.metrics[name].update(
                {"end_time": end_time, "duration": end_time - self.start_time}
            )
            del self.start_time

    def get_duration(self, name: str) -> float:
        """Get duration for a timing measurement."""
        if name in self.metrics and "duration" in self.metrics[name]:
            return self.metrics[name]["duration"]
        return 0.0

    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        return self.metrics.copy()


# Phase 3 data validation fixtures
@pytest.fixture
def data_validator():
    """Data validator fixture for Phase 3 testing."""
    return DataValidator()


class DataValidator:
    """Data validation implementation."""

    def validate_translation_input(self, data: Dict[str, Any]) -> bool:
        """Validate translation input data."""
        required_fields = ["original_poem", "source_lang", "target_lang"]
        return all(field in data for field in required_fields)

    def validate_step_config(self, data: Dict[str, Any]) -> bool:
        """Validate step configuration data."""
        required_fields = ["provider", "model", "prompt_template"]
        return all(field in data for field in required_fields)

    def validate_workflow_config(self, data: Dict[str, Any]) -> bool:
        """Validate workflow configuration data."""
        required_fields = ["name", "steps"]
        return all(field in data for field in required_fields)


# Error simulation fixtures
@pytest.fixture
def error_simulator():
    """Error simulator for testing error handling."""
    return ErrorSimulator()


class ErrorSimulator:
    """Error simulation implementation."""

    def __init__(self):
        self.error_scenarios = {}

    def add_scenario(self, name: str, error_type: type, message: str):
        """Add an error scenario for simulation."""
        self.error_scenarios[name] = {"type": error_type, "message": message}

    def simulate_error(self, scenario_name: str):
        """Simulate an error scenario."""
        if scenario_name in self.error_scenarios:
            scenario = self.error_scenarios[scenario_name]
            raise scenario["type"](scenario["message"])

    def clear_scenarios(self):
        """Clear all error scenarios."""
        self.error_scenarios.clear()


# Async testing utilities
@pytest.fixture
def async_test_helpers():
    """Async testing utilities for Phase 3."""
    return AsyncTestHelpers()


class AsyncTestHelpers:
    """Async testing utilities implementation."""

    @staticmethod
    async def wait_for_condition(
        condition_check: callable, timeout: float = 5.0, interval: float = 0.1
    ) -> bool:
        """Wait for a condition to become true."""
        import time

        start_time = time.time()

        while time.time() - start_time < timeout:
            if await condition_check():
                return True
            await asyncio.sleep(interval)

        return False

    @staticmethod
    async def assert_async_result(async_func, expected_result, timeout: float = 5.0):
        """Assert that an async function returns the expected result."""
        result = await asyncio.wait_for(async_func(), timeout=timeout)
        assert result == expected_result, f"Expected {expected_result}, got {result}"


# Memory and resource management
@pytest.fixture
def resource_manager():
    """Resource manager for test resource cleanup."""
    return ResourceManager()


class ResourceManager:
    """Resource manager implementation."""

    def __init__(self):
        self.resources = []

    def add_resource(self, resource, cleanup_func=None):
        """Add a resource to be managed."""
        self.resources.append({"resource": resource, "cleanup_func": cleanup_func})

    def cleanup_all(self):
        """Cleanup all managed resources."""
        for item in reversed(self.resources):
            resource = item["resource"]
            cleanup_func = item["cleanup_func"]

            if cleanup_func:
                try:
                    if asyncio.iscoroutinefunction(cleanup_func):
                        await cleanup_func(resource)
                    else:
                        cleanup_func(resource)
                except Exception:
                    # Log error but continue cleanup
                    print(f"Error cleaning up resource: {e}")

            # Generic cleanup
            if hasattr(resource, "close"):
                try:
                    if asyncio.iscoroutinefunction(resource.close):
                        await resource.close()
                    else:
                        resource.close()
                except Exception:
                    print(f"Error closing resource: {e}")

            self.resources.clear()


# Enhanced test context manager
@pytest.fixture
def test_context():
    """Enhanced test context manager."""
    return TestContext()


class TestContext:
    """Enhanced test context manager."""

    def __init__(self):
        self.resource_manager = ResourceManager()
        self.error_simulator = ErrorSimulator()
        self.data_validator = DataValidator()
        self.performance_monitor = PerformanceMonitor()

    def add_test_resource(self, resource, cleanup_func=None):
        """Add a test resource for management."""
        self.resource_manager.add_resource(resource, cleanup_func)

    def simulate_error(self, scenario_name: str):
        """Simulate an error scenario."""
        self.error_simulator.simulate_error(scenario_name)

    def validate_data(self, data_type: str, data: Dict[str, Any]) -> bool:
        """Validate test data."""
        if data_type == "translation_input":
            return self.data_validator.validate_translation_input(data)
        elif data_type == "step_config":
            return self.data_validator.validate_step_config(data)
        elif data_type == "workflow_config":
            return self.data_validator.validate_workflow_config(data)
        return True

    def start_timer(self, operation_name: str):
        """Start timing measurement for an operation."""
        self.performance_monitor.start_timer(operation_name)

    def end_timer(self, operation_name: str):
        """End timing measurement for an operation."""
        self.performance_monitor.end_timer(operation_name)

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected performance metrics."""
        return self.performance_monitor.get_metrics()

    def cleanup(self):
        """Cleanup all test resources."""
        self.resource_manager.cleanup_all()
        self.error_simulator.clear_scenarios()
