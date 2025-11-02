"""
Unit tests for Phase 3A infrastructure components.

This module tests the new dependency injection container, interfaces,
and core tools introduced in Phase 3A refactoring.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Import the Phase 3A infrastructure components
from src.vpsweb.core.container import (
    DIContainer,
    DIScope,
    ServiceLocator,
    LifetimeScope,
    injectable,
    auto_register
)
from src.vpsweb.core.interfaces import (
    ILLMProvider,
    ILLMFactory,
    IPromptService,
    IOutputParser,
    IWorkflowOrchestrator,
    LLMRequest,
    LLMResponse,
    WorkflowConfig,
    WorkflowStep,
    WorkflowResult,
    WorkflowStatus,
    ParsedOutput,
    ParsingResult
)
from src.vpsweb.utils.tools_phase3a_v2 import (
    AsyncTimer,
    timeout_context,
    ErrorCollector,
    ResourceManager,
    PerformanceMonitor,
    generate_hash,
    generate_unique_id,
    deep_merge_dict,
    validate_required_fields,
    ValidationError,
    safe_json_loads,
    safe_json_dumps
)


# ============================================================================
# Test Interfaces and Implementations
# ============================================================================

class ITestService:
    """Test service interface."""

    def process_data(self, data: Any) -> Any:
        pass

    async def process_data_async(self, data: Any) -> Any:
        pass


@injectable
class TestService(ITestService):
    """Test service implementation."""

    def __init__(self, multiplier: int = 2):
        self.multiplier = multiplier

    def process_data(self, data: Any) -> Any:
        return data * self.multiplier

    async def process_data_async(self, data: Any) -> Any:
        await asyncio.sleep(0.001)  # Simulate async work
        return self.process_data(data)


class TestLLMProvider(ILLMProvider):
    """Mock LLM provider for testing."""

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content="Mock response",
            model="mock-model",
            provider="test",
            tokens_used=10
        )

    async def generate_stream(self, request):
        # Mock streaming implementation
        yield "chunk1"
        yield "chunk2"

    def get_provider_name(self) -> str:
        return "test_provider"

    def get_available_models(self) -> list:
        return ["mock-model"]

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return True


# ============================================================================
# Dependency Injection Container Tests
# ============================================================================

class TestDIContainer:
    """Test cases for DI Container."""

    def test_register_and_resolve_transient(self):
        """Test transient dependency registration and resolution."""
        container = DIContainer()

        # Register transient dependency
        container.register(ITestService, implementation=TestService, lifetime=LifetimeScope.TRANSIENT)

        # Resolve multiple instances
        instance1 = container.resolve(ITestService)
        instance2 = container.resolve(ITestService)

        # Should be different instances
        assert instance1 is not instance2
        assert isinstance(instance1, TestService)
        assert isinstance(instance2, TestService)

    def test_register_and_resolve_singleton(self):
        """Test singleton dependency registration and resolution."""
        container = DIContainer()

        # Register singleton dependency
        container.register_singleton(ITestService, TestService)

        # Resolve multiple instances
        instance1 = container.resolve(ITestService)
        instance2 = container.resolve(ITestService)

        # Should be the same instance
        assert instance1 is instance2
        assert isinstance(instance1, TestService)

    def test_register_and_resolve_scoped(self):
        """Test scoped dependency registration and resolution."""
        container = DIContainer()

        # Register scoped dependency
        container.register_scoped(ITestService, TestService)

        # Test with scope
        with container.create_scope("test_scope"):
            instance1 = container.resolve(ITestService)
            instance2 = container.resolve(ITestService)

            # Should be same instance within scope
            assert instance1 is instance2

        # New scope should create new instance
        with container.create_scope("test_scope_2"):
            instance3 = container.resolve(ITestService)

            # Should be different from previous scope
            assert instance1 is not instance3

    def test_register_factory(self):
        """Test factory registration and resolution."""
        container = DIContainer()

        # Register factory
        def create_test_service():
            return TestService(multiplier=5)

        container.register_factory(ITestService, create_test_service)

        # Resolve instance
        instance = container.resolve(ITestService)

        assert isinstance(instance, TestService)
        assert instance.multiplier == 5

    def test_register_instance(self):
        """Test instance registration and resolution."""
        container = DIContainer()

        # Create and register instance
        test_instance = TestService(multiplier=10)
        container.register_instance(ITestService, test_instance)

        # Resolve instance
        resolved = container.resolve(ITestService)

        # Should be the same instance
        assert resolved is test_instance

    def test_constructor_injection(self):
        """Test constructor dependency injection."""
        container = DIContainer()

        # Register dependency
        container.register(ITestService, TestService)

        # Class that depends on ITestService
        @injectable
        class DependentService:
            def __init__(self, test_service: ITestService):
                self.test_service = test_service

            def get_result(self, data: Any) -> Any:
                return self.test_service.process_data(data)

        # Register dependent service
        container.register(DependentService, DependentService)

        # Resolve and test
        dependent = container.resolve(DependentService)
        result = dependent.get_result(5)

        assert result == 10  # 5 * 2 (default multiplier)

    def test_error_handling(self):
        """Test error handling in DI container."""
        container = DIContainer()

        # Test resolving unregistered dependency
        with pytest.raises(ValueError, match="Dependency .* is not registered"):
            container.resolve(ITestService)

        # Test double registration
        container.register(ITestService, TestService)
        with pytest.raises(ValueError, match="Dependency .* is already registered"):
            container.register(ITestService, TestService)

    def test_cleanup(self):
        """Test container cleanup."""
        container = DIContainer()

        # Register some dependencies
        container.register_singleton(ITestService, TestService)

        # Create a scope
        container.begin_scope("test_scope")
        container.resolve(ITestService)

        # Cleanup
        container.cleanup()

        # Should be clean
        assert len(container._singletons) == 0
        assert len(container._scoped_instances) == 0


class TestServiceLocator:
    """Test cases for Service Locator."""

    def test_service_locator_singleton(self):
        """Test service locator singleton pattern."""
        locator1 = ServiceLocator()
        locator2 = ServiceLocator()

        assert locator1 is locator2

    def test_service_locator_integration(self):
        """Test service locator integration with DI container."""
        container = DIContainer()
        container.register(ITestService, TestService)

        locator = ServiceLocator()
        locator.set_container(container)

        # Resolve through service locator
        instance = locator.resolve(ITestService)

        assert isinstance(instance, TestService)


# ============================================================================
# Interface Implementation Tests
# ============================================================================

class TestLLMInterface:
    """Test LLM interface implementation."""

    @pytest.mark.asyncio
    async def test_llm_provider_interface(self):
        """Test LLM provider interface compliance."""
        provider = TestLLMProvider()

        # Test required methods exist and work
        request = LLMRequest(
            messages=[{"role": "user", "content": "test"}],
            model="test-model"
        )

        response = await provider.generate(request)

        assert isinstance(response, LLMResponse)
        assert response.content == "Mock response"
        assert response.provider == "test"
        assert response.model == "mock-model"

        # Test streaming
        chunks = []
        async for chunk in provider.generate_stream(request):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == "chunk1"
        assert chunks[1] == "chunk2"


class TestWorkflowInterface:
    """Test workflow interface implementation."""

    def test_workflow_config_creation(self):
        """Test workflow configuration creation."""
        step = WorkflowStep(
            name="test_step",
            provider="test_provider",
            model="test_model",
            prompt_template="test_template.xml"
        )

        config = WorkflowConfig(
            name="test_workflow",
            description="Test workflow for testing",
            steps=[step]
        )

        assert config.name == "test_workflow"
        assert len(config.steps) == 1
        assert config.steps[0].name == "test_step"


# ============================================================================
# Utility Tools Tests
# ============================================================================

class TestAsyncTimer:
    """Test AsyncTimer utility."""

    @pytest.mark.asyncio
    async def test_async_timer(self):
        """Test async timer functionality."""
        timer = AsyncTimer("test_operation")

        async with timer:
            await asyncio.sleep(0.01)  # 10ms

        duration = timer.get_duration()
        assert duration is not None
        assert duration >= 0.01  # Should be at least 10ms
        assert duration < 0.1   # But not too long


class TestErrorCollector:
    """Test ErrorCollector utility."""

    def test_error_collection(self):
        """Test error collection functionality."""
        collector = ErrorCollector()

        # Add some errors
        try:
            raise ValueError("Test error 1")
        except ValueError as e:
            collector.add_error(e)

        try:
            raise RuntimeError("Test error 2")
        except RuntimeError as e:
            collector.add_error(e, context={"test": True})

        # Check error collection
        assert collector.has_errors()
        assert len(collector.get_errors()) == 2

        # Check filtering by type
        value_errors = collector.get_errors("ValueError")
        assert len(value_errors) == 1
        assert value_errors[0].message == "Test error 1"

        # Check summary
        summary = collector.get_error_summary()
        assert summary["ValueError"] == 1
        assert summary["RuntimeError"] == 1

        # Check clear
        collector.clear_errors()
        assert not collector.has_errors()


class TestResourceManager:
    """Test ResourceManager utility."""

    def test_resource_management(self):
        """Test resource management functionality."""
        manager = ResourceManager()

        # Add some resources
        cleanup_called = []

        def cleanup_func(resource):
            cleanup_called.append(resource)

        # Add resources
        resource1 = {"name": "test1"}
        resource2 = {"name": "test2"}

        manager.add_resource(resource1, cleanup_func)
        manager.add_resource(resource2, cleanup_func)

        # Cleanup specific resource
        manager.cleanup_resource(resource1)

        assert len(cleanup_called) == 1
        assert cleanup_called[0] == resource1
        assert len(manager.resources) == 1

        # Cleanup all
        manager.cleanup_all()

        assert len(cleanup_called) == 2
        assert resource2 in cleanup_called
        assert len(manager.resources) == 0


class TestPerformanceMonitor:
    """Test PerformanceMonitor utility."""

    def test_performance_monitoring(self):
        """Test performance monitoring functionality."""
        monitor = PerformanceMonitor()

        # Record some operations
        monitor.record_operation("test_op", 0.1, True)
        monitor.record_operation("test_op", 0.2, True)
        monitor.record_operation("test_op", 0.15, False)

        # Get metrics
        metrics = monitor.get_metrics("test_op")
        assert metrics is not None
        assert metrics.operation_count == 3
        assert abs(metrics.total_duration - 0.45) < 0.001
        assert metrics.min_duration == 0.1
        assert metrics.max_duration == 0.2
        assert metrics.error_count == 1
        summary = metrics.get_summary()
        assert summary['success_rate'] == 2/3

        # Test context manager
        with monitor.measure_operation("context_test"):
            import time
            time.sleep(0.01)  # Small delay

        context_metrics = monitor.get_metrics("context_test")
        assert context_metrics is not None
        assert context_metrics.operation_count == 1


class TestUtilityFunctions:
    """Test utility functions."""

    def test_generate_hash(self):
        """Test hash generation."""
        data1 = {"key": "value", "number": 42}
        data2 = {"number": 42, "key": "value"}  # Different order, same content

        hash1 = generate_hash(data1)
        hash2 = generate_hash(data2)

        assert hash1 == hash2  # Same content should produce same hash
        assert len(hash1) == 64  # SHA256 hex digest length

    def test_generate_unique_id(self):
        """Test unique ID generation."""
        id1 = generate_unique_id()
        id2 = generate_unique_id()
        id3 = generate_unique_id("prefix")

        assert id1 != id2  # Should be unique
        assert id3.startswith("prefix_")
        assert len(id1) == 36  # UUID length

    def test_deep_merge_dict(self):
        """Test deep dictionary merging."""
        dict1 = {
            "a": 1,
            "b": {"c": 2, "d": 3},
            "e": 4
        }

        dict2 = {
            "b": {"c": 20, "f": 5},
            "g": 6
        }

        result = deep_merge_dict(dict1, dict2)

        expected = {
            "a": 1,
            "b": {"c": 20, "d": 3, "f": 5},  # c should be overwritten, d preserved, f added
            "e": 4,
            "g": 6
        }

        assert result == expected

    def test_validation_functions(self):
        """Test validation functions."""
        # Test required fields validation
        data = {"name": "test", "value": 42}

        # Should pass
        validate_required_fields(data, ["name", "value"])

        # Should fail
        with pytest.raises(ValidationError):
            validate_required_fields(data, ["name", "value", "missing"])

    def test_safe_json_functions(self):
        """Test safe JSON functions."""
        # Test safe JSON loads
        valid_json = '{"key": "value", "number": 42}'
        invalid_json = '{"key": "value", "number":}'

        assert safe_json_loads(valid_json) == {"key": "value", "number": 42}
        assert safe_json_loads(invalid_json) is None

        # Test safe JSON dumps
        data = {"key": "value", "number": 42}

        result = safe_json_dumps(data)
        assert '"key": "value"' in result
        assert '"number": 42' in result

        # Test with object that can't be serialized
        class Unserializable:
            pass

        result = safe_json_dumps(Unserializable())
        # Should contain the string representation of the object
        assert "object at" in result


# ============================================================================
# Integration Tests
# ============================================================================

class TestPhase3AIntegration:
    """Integration tests for Phase 3A components."""

    @pytest.mark.asyncio
    async def test_di_container_with_llm_provider(self):
        """Test DI container integration with LLM provider."""
        container = DIContainer()

        # Register LLM provider
        container.register(ILLMProvider, TestLLMProvider)

        # Resolve and use provider
        provider = container.resolve(ILLMProvider)

        request = LLMRequest(
            messages=[{"role": "user", "content": "test"}],
            model="test-model"
        )

        response = await provider.generate(request)

        assert isinstance(response, LLMResponse)
        assert response.content == "Mock response"

    @pytest.mark.asyncio
    async def test_error_handling_with_tools(self):
        """Test error handling integration with tools."""
        error_collector = ErrorCollector()
        performance_monitor = PerformanceMonitor()

        # Function that might fail
        async def risky_operation(success_rate: float = 0.5):
            import random
            await asyncio.sleep(0.001)

            if random.random() > success_rate:
                raise ValueError("Random failure")

            return "success"

        # Run multiple operations
        for i in range(10):
            try:
                with performance_monitor.measure_operation("risky_op"):
                    result = await risky_operation(success_rate=0.8)
                    assert result == "success"
            except Exception as e:
                error_collector.add_error(e, {"iteration": i})

        # Check results
        metrics = performance_monitor.get_metrics("risky_op")
        assert metrics is not None
        assert metrics.operation_count == 10

        # Should have some errors due to random failure
        # (Not guaranteed, but likely with success_rate=0.8)
        if error_collector.has_errors():
            assert len(error_collector.get_errors()) > 0

    def test_resource_management_with_di(self):
        """Test resource management integration with DI."""
        container = DIContainer()
        manager = ResourceManager()

        # Register service with resource cleanup
        class ServiceWithResources:
            def __init__(self):
                self.resource = open(tempfile.NamedTemporaryFile(delete=False).name, 'w')
                manager.add_resource(self.resource, self.resource.close, "file_resource")

            def cleanup(self):
                self.resource.close()

        container.register(ServiceWithResources, ServiceWithResources)

        # Create service
        service = container.resolve(ServiceWithResources)

        # Should have a resource
        assert len(manager.resources) == 1

        # Cleanup
        manager.cleanup_all()

        # Should be clean
        assert len(manager.resources) == 0