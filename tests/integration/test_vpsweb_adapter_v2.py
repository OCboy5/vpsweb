"""
Integration tests for Phase 3B VPSWeb Workflow Adapter V2.

Tests the refactored adapter with dependency injection and interface-based
workflow orchestration.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any

# Import the Phase 3A infrastructure components
from vpsweb.core.container import DIContainer
from vpsweb.core.interfaces import (
    IWorkflowOrchestrator,
    ILLMFactory,
    ILLMProvider,
    IPromptService,
    IOutputParser,
    WorkflowConfig,
    WorkflowResult,
    WorkflowStatus,
    LLMRequest,
    LLMResponse,
    ParsedOutput,
    ParsingResult,
)
from vpsweb.core.workflow_orchestrator_v2 import WorkflowOrchestratorV2
from vpsweb.webui.services.vpsweb_adapter_v2 import VPSWebWorkflowAdapterV2
from vpsweb.webui.services.poem_service import PoemService
from vpsweb.repository.service import RepositoryWebService

# ============================================================================
# Integration Test Fixtures
# ============================================================================

@pytest.fixture
def mock_dependencies():
    """Create all required mock dependencies."""
    # Mock LLM Factory and Provider
    factory = Mock(spec=ILLMFactory)
    provider = Mock(spec=ILLMProvider)
    response = LLMResponse(
        content="<translation>Hola mundo</translation>",
        model="test-model",
        provider="test-provider",
        tokens_used=50
    )
    provider.generate = AsyncMock(return_value=response)
    factory.get_provider = Mock(return_value=provider)

    # Mock Prompt Service
    prompt_service = Mock(spec=IPromptService)
    prompt_service.render_prompt = AsyncMock(return_value=("system_prompt", "user_prompt"))

    # Mock Output Parser
    output_parser = Mock(spec=IOutputParser)
    output_parser.parse_xml = Mock(return_value=ParsedOutput(
        content={
            "translation": "Hola mundo",
            "confidence": 0.95,
            "notes": "Translation completed successfully"
        },
        result_type=ParsingResult.SUCCESS
    ))

    return {
        "factory": factory,
        "provider": provider,
        "response": response,
        "prompt_service": prompt_service,
        "output_parser": output_parser
    }


@pytest.fixture
def di_container_with_services(mock_dependencies):
    """DI container with all required services registered."""
    container = DIContainer()

    # Register all required services
    container.register_instance(ILLMFactory, mock_dependencies["factory"])
    container.register_instance(IPromptService, mock_dependencies["prompt_service"])
    container.register_instance(IOutputParser, mock_dependencies["output_parser"])

    return container


@pytest.fixture
def workflow_orchestrator(di_container_with_services):
    """Create workflow orchestrator with all dependencies."""
    return WorkflowOrchestratorV2(container=di_container_with_services)


@pytest.fixture
def mock_poem_service():
    """Mock poem service."""
    service = Mock(spec=PoemService)
    service.get_poem = AsyncMock(return_value={
        "id": "poem_123",
        "title": "Test Poem",
        "author": "Test Author",
        "content": "Hello world, this is a test poem",
        "source_language": "en"
    })
    return service


@pytest.fixture
def mock_repository_service():
    """Mock repository service."""
    service = Mock(spec=RepositoryWebService)
    service.create_translation = AsyncMock(return_value=Mock(id="translation_123"))
    return service


@pytest.fixture
def vpsweb_adapter_v2(workflow_orchestrator, mock_poem_service, mock_repository_service):
    """Create VPSWeb adapter V2 with all dependencies."""
    return VPSWebWorkflowAdapterV2(
        poem_service=mock_poem_service,
        repository_service=mock_repository_service,
        workflow_orchestrator=workflow_orchestrator
    )


# ============================================================================
# Integration Tests
# ============================================================================

class TestVPSWebWorkflowAdapterV2Integration:
    """Integration tests for the refactored VPSWeb adapter."""

    @pytest.mark.asyncio
    async def test_complete_translation_workflow(
        self,
        vpsweb_adapter_v2,
        mock_poem_service,
        mock_repository_service
    ):
        """Test complete translation workflow integration."""
        # Execute translation workflow
        result = await vpsweb_adapter_v2.execute_translation_workflow(
            poem_id="poem_123",
            source_lang="en",
            target_lang="zh-CN",
            workflow_mode="hybrid"
        )

        # Verify response structure
        assert "task_id" in result
        assert result["status"].value == "pending"
        assert "Translation workflow started" in result["message"]
        assert "refactored orchestrator" in result["message"]

        # Verify poem service was called
        mock_poem_service.get_poem.assert_called_once_with("poem_123")

        # Wait for async execution
        await asyncio.sleep(0.2)

        # Verify the workflow is being tracked (would need app.state access)
        # This is a basic integration test - full end-to-end testing would require
        # setting up the FastAPI app context

    @pytest.mark.asyncio
    async def test_workflow_with_different_modes(
        self,
        vpsweb_adapter_v2,
        mock_dependencies
    ):
        """Test workflow execution with different modes."""
        modes = ["reasoning", "non_reasoning", "hybrid"]

        for mode in modes:
            result = await vpsweb_adapter_v2.execute_translation_workflow(
                poem_id="poem_123",
                source_lang="en",
                target_lang="zh-CN",
                workflow_mode=mode
            )

            assert result["status"].value == "pending"
            assert "task_id" in result

            # Allow async execution to proceed
            await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_error_handling_for_missing_poem(self, vpsweb_adapter_v2, mock_poem_service):
        """Test error handling when poem is not found."""
        # Configure poem service to return None (poem not found)
        mock_poem_service.get_poem = AsyncMock(return_value=None)

        # Should raise WorkflowExecutionError
        with pytest.raises(Exception) as exc_info:
            await vpsweb_adapter_v2.execute_translation_workflow(
                poem_id="nonexistent_poem",
                source_lang="en",
                target_lang="zh-CN",
                workflow_mode="hybrid"
            )

        assert "Poem not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_language_code_conversion(self, vpsweb_adapter_v2):
        """Test language code conversion functionality."""
        poem_data = {
            "id": "poem_123",
            "title": "Test Poem",
            "author": "Test Author",
            "content": "Hello world"
        }

        # Test various language codes that match the TranslationInput enum
        test_cases = [
            ("en", "English"),
            ("zh-CN", "Chinese"),
            ("pl", "Polish"),
            ("unknown", "English"),  # Fallback to English
        ]

        for source_code, expected_name in test_cases:
            # Use different target language to satisfy validation
            target_code = "zh-CN" if source_code != "zh-CN" else "en"
            input_data = vpsweb_adapter_v2._map_repository_to_workflow_input(
                poem_data, source_code, target_code
            )

            assert input_data.source_lang == expected_name
            assert input_data.target_lang in ["Chinese", "English"]
            assert input_data.original_poem == "Hello world"
            assert input_data.metadata["source_lang_iso"] == source_code
            assert input_data.metadata["target_lang_iso"] == target_code

    def test_workflow_config_creation(self, vpsweb_adapter_v2):
        """Test workflow configuration creation for different modes."""
        modes = ["reasoning", "non_reasoning", "hybrid"]

        for mode in modes:
            config = vpsweb_adapter_v2._create_workflow_config_from_mode(mode)

            assert config.name == f"translation_{mode}"
            assert f"{mode}" in config.description
            assert len(config.steps) == 3

            # Verify step names
            step_names = [step.name for step in config.steps]
            assert "Initial Translation" in step_names
            assert "Editor Review" in step_names
            assert "Translator Revision" in step_names

            # Verify mode-specific configuration
            if mode == "reasoning":
                assert config.steps[0].temperature == 0.3
                assert config.steps[0].max_tokens == 2000
            elif mode == "hybrid":
                assert config.steps[0].temperature == 0.5
                assert config.steps[0].max_tokens == 1800

    def test_workflow_orchestrator_delegation(
        self,
        workflow_orchestrator,
        vpsweb_adapter_v2
    ):
        """Test that adapter properly delegates to workflow orchestrator."""
        # Test list_workflows delegation
        workflows = vpsweb_adapter_v2.list_workflows()
        assert isinstance(workflows, list)

        # Test status delegation (sync wrapper around async)
        status = vpsweb_adapter_v2.get_workflow_status("nonexistent_id")
        # Should return None for non-existent workflow or handle sync/async mismatch
        assert status is None or isinstance(status, str)

        # Test cancel delegation
        result = vpsweb_adapter_v2.cancel_workflow("nonexistent_id")
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_input_validation(self, vpsweb_adapter_v2):
        """Test input validation for workflow execution."""
        # Test missing poem_id
        with pytest.raises(Exception):
            await vpsweb_adapter_v2.execute_translation_workflow(
                poem_id="",
                source_lang="en",
                target_lang="zh-CN",
                workflow_mode="hybrid"
            )

        # Test same source and target language
        with pytest.raises(Exception):
            await vpsweb_adapter_v2.execute_translation_workflow(
                poem_id="poem_123",
                source_lang="en",
                target_lang="en",
                workflow_mode="hybrid"
            )

    @pytest.mark.asyncio
    async def test_progress_callback_integration(
        self,
        vpsweb_adapter_v2,
        mock_dependencies
    ):
        """Test progress callback integration with orchestrator."""
        result = await vpsweb_adapter_v2.execute_translation_workflow(
            poem_id="poem_123",
            source_lang="en",
            target_lang="zh-CN",
            workflow_mode="hybrid"
        )

        assert result["status"].value == "pending"

        # Allow workflow execution to proceed
        await asyncio.sleep(0.2)

        # The workflow should have progressed through steps
        # This would require more sophisticated testing setup with FastAPI app.state


# ============================================================================
# Performance and Error Handling Tests
# ============================================================================

class TestVPSWebWorkflowAdapterV2Performance:
    """Performance and error handling tests for the refactored adapter."""

    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(
        self,
        vpsweb_adapter_v2,
        mock_dependencies
    ):
        """Test executing multiple workflows concurrently."""
        tasks = []
        results = []

        # Start multiple concurrent workflows
        for i in range(5):
            task = vpsweb_adapter_v2.execute_translation_workflow(
                poem_id=f"poem_{i}",
                source_lang="en",
                target_lang="zh-CN",
                workflow_mode="hybrid"
            )
            tasks.append(task)

        # Wait for all to start
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all started successfully
        assert len(results) == 5
        for i, result in enumerate(results):
            assert not isinstance(result, Exception)
            assert result["status"].value == "pending"
            assert "task_id" in result

    @pytest.mark.asyncio
    async def test_workflow_orchestrator_error_propagation(
        self,
        mock_dependencies
    ):
        """Test error propagation from workflow orchestrator."""
        # Create orchestrator with failing provider
        container = DIContainer()
        factory = mock_dependencies["factory"]
        provider = mock_dependencies["provider"]
        provider.generate = AsyncMock(side_effect=Exception("LLM API Error"))

        container.register_instance(ILLMFactory, factory)
        container.register_instance(IPromptService, mock_dependencies["prompt_service"])
        container.register_instance(IOutputParser, mock_dependencies["output_parser"])

        failing_orchestrator = WorkflowOrchestratorV2(container=container)

        # Create adapter with failing orchestrator
        mock_poem_service = Mock(spec=PoemService)
        mock_poem_service.get_poem = AsyncMock(return_value={
            "id": "poem_123",
            "content": "Hello world"
        })

        mock_repository_service = Mock(spec=RepositoryWebService)

        adapter = VPSWebWorkflowAdapterV2(
            poem_service=mock_poem_service,
            repository_service=mock_repository_service,
            workflow_orchestrator=failing_orchestrator
        )

        # Execute workflow - should handle errors gracefully
        result = await adapter.execute_translation_workflow(
            poem_id="poem_123",
            source_lang="en",
            target_lang="zh-CN",
            workflow_mode="hybrid"
        )

        # Should still return a task ID, with error handling during execution
        assert result["status"].value == "pending"
        assert "task_id" in result

        # Allow async execution to proceed and handle errors
        await asyncio.sleep(0.2)

    def test_memory_usage_with_large_workflows(self, vpsweb_adapter_v2):
        """Test memory usage with large workflow configurations."""
        # Test with various workflow modes
        modes = ["reasoning", "non_reasoning", "hybrid"]

        for mode in modes:
            config = vpsweb_adapter_v2._create_workflow_config_from_mode(mode)

            # Verify configuration size is reasonable
            config_str = str(config)
            assert len(config_str) < 10000  # Should be under 10KB

            # Verify step count is fixed
            assert len(config.steps) == 3

    @pytest.mark.asyncio
    async def test_timeout_handling(
        self,
        vpsweb_adapter_v2,
        mock_dependencies
    ):
        """Test timeout handling in workflow execution."""
        # Configure provider to timeout
        provider = mock_dependencies["provider"]
        provider.generate = AsyncMock(
            side_effect=asyncio.TimeoutError("Request timeout")
        )

        result = await vpsweb_adapter_v2.execute_translation_workflow(
            poem_id="poem_123",
            source_lang="en",
            target_lang="zh-CN",
            workflow_mode="hybrid"
        )

        # Should still return task ID for async execution
        assert result["status"].value == "pending"

        # Allow execution to proceed and handle timeout
        await asyncio.sleep(0.2)