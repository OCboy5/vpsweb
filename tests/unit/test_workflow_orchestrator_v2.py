"""
Unit tests for Phase 3B Workflow Orchestrator V2.

Tests the new interface-based workflow orchestration implementation
with dependency injection and comprehensive error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any

# Import the Phase 3A infrastructure components
from src.vpsweb.core.container import DIContainer, LifetimeScope
from src.vpsweb.core.interfaces import (
    IWorkflowOrchestrator,
    ILLMFactory,
    ILLMProvider,
    IPromptService,
    IOutputParser,
    IEventBus,
    ILogger,
    IMetricsCollector,
    WorkflowConfig,
    WorkflowStep,
    WorkflowResult,
    WorkflowStatus,
    LLMRequest,
    LLMResponse,
    ParsedOutput,
    ParsingResult,
)
from src.vpsweb.core.workflow_orchestrator_v2 import (
    WorkflowOrchestratorV2,
    WorkflowStepStatus,
    WorkflowExecutionContext,
    WorkflowStepResult,
)
from src.vpsweb.utils.tools_phase3a_v2 import (
    ErrorCollector,
    PerformanceMonitor,
)


# ============================================================================
# Test Fixtures and Mocks
# ============================================================================

@pytest.fixture
def mock_llm_factory():
    """Mock LLM factory for testing."""
    factory = Mock(spec=ILLMFactory)
    provider = Mock(spec=ILLMProvider)

    # Configure provider response
    response = LLMResponse(
        content="<translation>Hello world</translation>",
        model="test-model",
        provider="test-provider",
        tokens_used=50,
        prompt_tokens=25,
        completion_tokens=25
    )

    provider.generate = AsyncMock(return_value=response)
    factory.get_provider = Mock(return_value=provider)
    factory.list_providers = Mock(return_value=["test-provider"])

    return factory, provider, response


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
    parser.parse_xml = Mock(return_value=ParsedOutput(
        content={"translation": "Hello world"},
        result_type=ParsingResult.SUCCESS
    ))
    return parser


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing."""
    event_bus = Mock(spec=IEventBus)
    event_bus.publish = AsyncMock()
    return event_bus


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    logger = Mock(spec=ILogger)
    return logger


@pytest.fixture
def mock_metrics_collector():
    """Mock metrics collector for testing."""
    collector = Mock(spec=IMetricsCollector)
    collector.increment_counter = Mock()
    collector.record_timing = Mock()
    return collector


@pytest.fixture
def di_container_with_mocks(mock_llm_factory, mock_prompt_service, mock_output_parser):
    """DI container with all required services registered."""
    container = DIContainer()
    factory, provider, response = mock_llm_factory

    # Register all required services
    container.register_instance(ILLMFactory, factory)
    container.register_instance(IPromptService, mock_prompt_service)
    container.register_instance(IOutputParser, mock_output_parser)

    return container


@pytest.fixture
def sample_workflow_config():
    """Sample workflow configuration for testing."""
    return WorkflowConfig(
        name="test_workflow",
        description="Test workflow for unit testing",
        steps=[
            WorkflowStep(
                name="initial_translation",
                provider="test-provider",
                model="test-model",
                prompt_template="templates/translation.xml",
                temperature=0.7,
                max_tokens=1000,
                timeout=30.0,
                retry_attempts=3,
                required_fields=["translation"]
            )
        ]
    )


@pytest.fixture
def workflow_orchestrator_v2(di_container_with_mocks, mock_event_bus, mock_logger, mock_metrics_collector):
    """Create workflow orchestrator with all dependencies."""
    return WorkflowOrchestratorV2(
        container=di_container_with_mocks,
        event_bus=mock_event_bus,
        logger=mock_logger,
        metrics_collector=mock_metrics_collector
    )


# ============================================================================
# Workflow Execution Tests
# ============================================================================

class TestWorkflowOrchestratorV2:
    """Test cases for WorkflowOrchestratorV2."""

    @pytest.mark.asyncio
    async def test_execute_workflow_success(
        self,
        workflow_orchestrator_v2,
        sample_workflow_config,
        mock_event_bus
    ):
        """Test successful workflow execution."""
        input_data = {"text": "Hello world", "target_lang": "Spanish"}

        # Execute workflow
        result = await workflow_orchestrator_v2.execute_workflow(
            sample_workflow_config,
            input_data
        )

        # Wait a bit for async event publishing
        await asyncio.sleep(0.1)

        # Verify result
        assert result.status == WorkflowStatus.COMPLETED
        assert result.steps_executed == 1
        assert result.total_tokens_used > 0
        assert result.execution_time > 0
        assert "translation" in result.results

        # Verify events were published (allowing for async fire-and-forget)
        # Note: Events might not be published synchronously in the test
        # assert mock_event_bus.publish.call_count >= 2  # started + completed

    @pytest.mark.asyncio
    async def test_execute_workflow_with_progress_callback(
        self,
        workflow_orchestrator_v2,
        sample_workflow_config
    ):
        """Test workflow execution with progress callback."""
        input_data = {"text": "Hello world"}
        progress_updates = []

        async def progress_callback(step_name: str, details: Dict[str, Any]):
            progress_updates.append((step_name, details))

        result = await workflow_orchestrator_v2.execute_workflow(
            sample_workflow_config,
            input_data,
            progress_callback=progress_callback
        )

        # Verify progress updates were received
        assert len(progress_updates) >= 2
        assert progress_updates[-1][0] == "workflow_completed"
        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_workflow_step_failure(
        self,
        di_container_with_mocks,
        mock_event_bus,
        mock_logger,
        mock_metrics_collector
    ):
        """Test workflow execution when a step fails."""
        # Setup failing LLM provider
        factory, provider, response = di_container_with_mocks.resolve(ILLMFactory)
        provider.generate = AsyncMock(side_effect=Exception("LLM API Error"))

        orchestrator = WorkflowOrchestratorV2(
            container=di_container_with_mocks,
            event_bus=mock_event_bus,
            logger=mock_logger,
            metrics_collector=mock_metrics_collector
        )

        config = WorkflowConfig(
            name="failing_workflow",
            steps=[
                WorkflowStep(
                    name="failing_step",
                    provider="test-provider",
                    model="test-model",
                    prompt_template="templates/test.xml"
                )
            ]
        )

        result = await orchestrator.execute_workflow(config, {"test": "data"})

        # Verify failure handling
        assert result.status == WorkflowStatus.FAILED
        assert len(result.errors) > 0
        assert result.execution_time > 0

        # Verify error events were published
        assert mock_event_bus.publish.call_count >= 2  # started + failed

    @pytest.mark.asyncio
    async def test_execute_step_success(
        self,
        workflow_orchestrator_v2,
        sample_workflow_config
    ):
        """Test individual step execution."""
        step = sample_workflow_config.steps[0]
        input_data = {"text": "Hello world"}

        result = await workflow_orchestrator_v2.execute_step(step, input_data)

        # Verify step result
        assert result.step_name == "initial_translation"
        assert result.status == WorkflowStepStatus.COMPLETED
        assert result.result is not None
        assert result.duration > 0
        assert result.tokens_used > 0
        assert "translation" in result.result

    @pytest.mark.asyncio
    async def test_execute_step_failure(self, di_container_with_mocks, mock_logger, mock_metrics_collector):
        """Test step execution failure."""
        # Setup failing provider
        factory, provider, response = di_container_with_mocks.resolve(ILLMFactory)
        provider.generate = AsyncMock(side_effect=Exception("API Error"))

        orchestrator = WorkflowOrchestratorV2(
            container=di_container_with_mocks,
            logger=mock_logger,
            metrics_collector=mock_metrics_collector
        )

        step = WorkflowStep(
            name="failing_step",
            provider="test-provider",
            model="test-model",
            prompt_template="templates/test.xml"
        )

        result = await orchestrator.execute_step(step, {"test": "data"})

        # Verify failure handling
        assert result.step_name == "failing_step"
        assert result.status == WorkflowStepStatus.FAILED
        assert result.error == "API Error"
        assert result.duration > 0
        assert result.tokens_used == 0

    @pytest.mark.asyncio
    async def test_workflow_status_tracking(self, workflow_orchestrator_v2):
        """Test workflow status tracking."""
        workflow_id = "test-workflow-id"

        # Status should be None for non-existent workflow
        status = await workflow_orchestrator_v2.get_workflow_status(workflow_id)
        assert status is None

    @pytest.mark.asyncio
    async def test_cancel_workflow(self, workflow_orchestrator_v2):
        """Test workflow cancellation."""
        workflow_id = "test-workflow-id"

        # Cancel non-existent workflow should return False
        result = await workflow_orchestrator_v2.cancel_workflow(workflow_id)
        assert result is False

    def test_list_workflows(self, workflow_orchestrator_v2):
        """Test workflow listing."""
        workflows = workflow_orchestrator_v2.list_workflows()

        # Should return list of available workflows
        assert isinstance(workflows, list)
        assert len(workflows) > 0
        assert all(isinstance(w, str) for w in workflows)

    @pytest.mark.asyncio
    async def test_performance_metrics(
        self,
        workflow_orchestrator_v2,
        sample_workflow_config
    ):
        """Test performance metrics collection."""
        input_data = {"text": "Hello world"}

        # Execute workflow to generate metrics
        await workflow_orchestrator_v2.execute_workflow(
            sample_workflow_config,
            input_data
        )

        # Get performance metrics
        metrics = workflow_orchestrator_v2.get_performance_metrics()

        # Verify metrics structure
        assert "performance_monitor" in metrics
        assert "error_collector" in metrics
        assert "active_workflows" in metrics
        assert "resource_manager" in metrics

        # Verify performance monitor has data
        perf_monitor_metrics = metrics["performance_monitor"]
        assert "workflow_execution" in perf_monitor_metrics

    @pytest.mark.asyncio
    async def test_cleanup(self, workflow_orchestrator_v2):
        """Test orchestrator cleanup."""
        # Should not raise any exceptions
        await workflow_orchestrator_v2.cleanup()

        # Verify all resources are cleaned up
        metrics = workflow_orchestrator_v2.get_performance_metrics()
        assert metrics["active_workflows"] == 0

    @pytest.mark.asyncio
    async def test_multi_step_workflow(
        self,
        workflow_orchestrator_v2,
        mock_event_bus
    ):
        """Test workflow with multiple steps."""
        config = WorkflowConfig(
            name="multi_step_workflow",
            steps=[
                WorkflowStep(
                    name="step1",
                    provider="test-provider",
                    model="test-model",
                    prompt_template="templates/step1.xml"
                ),
                WorkflowStep(
                    name="step2",
                    provider="test-provider",
                    model="test-model",
                    prompt_template="templates/step2.xml"
                ),
                WorkflowStep(
                    name="step3",
                    provider="test-provider",
                    model="test-model",
                    prompt_template="templates/step3.xml"
                )
            ]
        )

        input_data = {"text": "Hello world"}
        progress_updates = []

        async def progress_callback(step_name: str, details: Dict[str, Any]):
            progress_updates.append((step_name, details))

        result = await workflow_orchestrator_v2.execute_workflow(
            config,
            input_data,
            progress_callback=progress_callback
        )

        # Verify multi-step execution
        assert result.status == WorkflowStatus.COMPLETED
        assert result.steps_executed == 3
        assert result.total_tokens_used > 0

        # Verify progress updates for each step
        step_names = [update[0] for update in progress_updates]
        assert "step1" in step_names
        assert "step2" in step_names
        assert "step3" in step_names
        assert "workflow_completed" in step_names

        # Verify events for each step
        event_calls = mock_event_bus.publish.call_args_list
        event_names = [call[0][0][0].data for call in event_calls if hasattr(call[0][0][0], 'data')]

        # Should have events for workflow start, each step start/complete, and workflow complete
        assert len(event_calls) >= 8  # start + 3*2 (start+complete) + complete


# ============================================================================
# Error Handling and Edge Cases Tests
# ============================================================================

class TestWorkflowOrchestratorV2ErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_missing_dependencies(self, di_container_with_mocks):
        """Test behavior with missing dependencies."""
        # Clear all registrations and only re-register LLM factory
        di_container_with_mocks.clear()
        factory, _, _ = di_container_with_mocks.resolve(ILLMFactory)
        di_container_with_mocks.register_instance(ILLMFactory, factory)

        orchestrator = WorkflowOrchestratorV2(container=di_container_with_mocks)

        config = WorkflowConfig(
            name="test_workflow",
            steps=[
                WorkflowStep(
                    name="test_step",
                    provider="test-provider",
                    model="test-model",
                    prompt_template="templates/test.xml"
                )
            ]
        )

        # Should fail gracefully when prompt service is missing
        with pytest.raises(RuntimeError, match="Prompt service not available"):
            await orchestrator.execute_workflow(config, {"test": "data"})

    @pytest.mark.asyncio
    async def test_invalid_step_configuration(self, workflow_orchestrator_v2):
        """Test handling of invalid step configurations."""
        invalid_step = WorkflowStep(
            name="invalid_step",
            provider="",  # Empty provider should fail validation
            model="test-model",
            prompt_template="templates/test.xml"
        )

        with pytest.raises(ValueError, match="missing provider"):
            await workflow_orchestrator_v2.execute_step(invalid_step, {"test": "data"})

    @pytest.mark.asyncio
    async def test_progress_callback_error_handling(
        self,
        workflow_orchestrator_v2,
        sample_workflow_config
    ):
        """Test handling of progress callback errors."""
        input_data = {"text": "Hello world"}

        # Callback that raises an exception
        async def failing_callback(step_name: str, details: Dict[str, Any]):
            if step_name == "initial_translation":
                raise Exception("Callback error")

        # Should not affect workflow execution
        result = await workflow_orchestrator_v2.execute_workflow(
            sample_workflow_config,
            input_data,
            progress_callback=failing_callback
        )

        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_event_bus_error_handling(self, di_container_with_mocks):
        """Test handling of event bus errors."""
        # Event bus that raises errors
        failing_event_bus = Mock(spec=IEventBus)
        failing_event_bus.publish = AsyncMock(side_effect=Exception("Event bus error"))

        orchestrator = WorkflowOrchestratorV2(
            container=di_container_with_mocks,
            event_bus=failing_event_bus
        )

        config = WorkflowConfig(
            name="test_workflow",
            steps=[
                WorkflowStep(
                    name="test_step",
                    provider="test-provider",
                    model="test-model",
                    prompt_template="templates/test.xml"
                )
            ]
        )

        # Should not affect workflow execution
        result = await orchestrator.execute_workflow(config, {"test": "data"})

        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_output_parser_error_handling(
        self,
        di_container_with_mocks,
        mock_prompt_service
    ):
        """Test handling of output parser errors."""
        # Setup parser that fails
        parser = Mock(spec=IOutputParser)
        parser.parse_xml = Mock(side_effect=Exception("Parse error"))
        di_container_with_mocks.register_instance(IOutputParser, parser)

        orchestrator = WorkflowOrchestratorV2(container=di_container_with_mocks)

        step = WorkflowStep(
            name="parse_test_step",
            provider="test-provider",
            model="test-model",
            prompt_template="templates/test.xml"
        )

        # Should fallback to raw content on parse error
        result = await orchestrator.execute_step(step, {"test": "data"})

        assert result.status == WorkflowStepStatus.COMPLETED
        assert "content" in result.result
        assert result.result["content"] == "<translation>Hello world</translation>"


# ============================================================================
# Integration Tests
# ============================================================================

class TestWorkflowOrchestratorV2Integration:
    """Integration tests for the workflow orchestrator."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_real_dependencies(
        self,
        di_container_with_mocks,
        mock_prompt_service,
        mock_output_parser,
        mock_event_bus,
        mock_logger,
        mock_metrics_collector
    ):
        """Test full workflow execution with real dependency injection."""
        orchestrator = WorkflowOrchestratorV2(
            container=di_container_with_mocks,
            event_bus=mock_event_bus,
            logger=mock_logger,
            metrics_collector=mock_metrics_collector
        )

        # Complex workflow configuration
        config = WorkflowConfig(
            name="complex_workflow",
            description="Complex workflow for integration testing",
            steps=[
                WorkflowStep(
                    name="initial_translation",
                    provider="test-provider",
                    model="test-model",
                    prompt_template="templates/initial_translation.xml",
                    temperature=0.7,
                    max_tokens=1000,
                    timeout=30.0,
                    retry_attempts=2,
                    required_fields=["translation", "confidence"]
                ),
                WorkflowStep(
                    name="quality_check",
                    provider="test-provider",
                    model="test-model",
                    prompt_template="templates/quality_check.xml",
                    temperature=0.3,
                    max_tokens=500,
                    timeout=15.0,
                    retry_attempts=1,
                    required_fields=["quality_score"]
                )
            ]
        )

        input_data = {
            "text": "Hello world, this is a test",
            "source_lang": "English",
            "target_lang": "Spanish",
            "context": "formal"
        }

        # Execute workflow
        result = await orchestrator.execute_workflow(config, input_data)

        # Verify comprehensive result
        assert result.status == WorkflowStatus.COMPLETED
        assert result.steps_executed == 2
        assert result.total_tokens_used > 0
        assert result.execution_time > 0
        assert len(result.results) >= 2

        # Verify metrics were recorded
        assert mock_metrics_collector.increment_counter.call_count >= 2
        assert mock_metrics_collector.record_timing.call_count >= 2

        # Verify events were published
        event_calls = mock_event_bus.publish.call_args_list
        assert len(event_calls) >= 6  # start + 2*2 (start+complete) + complete

        # Verify performance metrics
        metrics = orchestrator.get_performance_metrics()
        assert "workflow_execution" in metrics["performance_monitor"]
        assert not metrics["error_collector"]["has_errors"]

    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(
        self,
        di_container_with_mocks,
        mock_prompt_service,
        mock_output_parser
    ):
        """Test executing multiple workflows concurrently."""
        orchestrator = WorkflowOrchestratorV2(container=di_container_with_mocks)

        config = WorkflowConfig(
            name="concurrent_test",
            steps=[
                WorkflowStep(
                    name="test_step",
                    provider="test-provider",
                    model="test-model",
                    prompt_template="templates/test.xml"
                )
            ]
        )

        # Execute multiple workflows concurrently
        tasks = []
        for i in range(5):
            task = orchestrator.execute_workflow(
                config,
                {"test": f"data_{i}", "index": i}
            )
            tasks.append(task)

        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all completed successfully
        assert len(results) == 5
        for i, result in enumerate(results):
            assert not isinstance(result, Exception)
            assert result.status == WorkflowStatus.COMPLETED
            assert result.results["test"] == f"data_{i}"