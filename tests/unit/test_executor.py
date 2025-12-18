"""
Unit tests for the StepExecutor class.

These tests verify the core execution engine that orchestrates the poetry translation
workflow by coordinating LLM providers, prompt templates, and output parsing.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.vpsweb.core.executor import (
    LLMCallError,
    OutputParsingError,
    PromptRenderingError,
    StepExecutor,
)
from src.vpsweb.models.config import StepConfig
from src.vpsweb.models.translation import (
    InitialTranslation,
    TranslationInput,
)
from src.vpsweb.services.prompts import PromptService


class TestStepExecutor:
    """Test cases for StepExecutor functionality."""

    @pytest.fixture
    def mock_llm_factory(self):
        """Create a mock LLM factory."""
        factory = Mock()
        # Add the get_provider_config method
        mock_provider_config = Mock()
        mock_provider_config.name = "openai"
        mock_provider_config.api_key_env = "OPENAI_API_KEY"
        mock_provider_config.base_url = "https://api.openai.com/v1"
        mock_provider_config.type = "openai_compatible"
        mock_provider_config.models = ["gpt-3.5-turbo", "gpt-4"]
        factory.get_provider_config.return_value = mock_provider_config
        return factory

    @pytest.fixture
    def mock_prompt_service(self):
        """Create a mock prompt service."""
        service = Mock(spec=PromptService)
        return service

    @pytest.fixture
    def step_executor(self, mock_llm_factory, mock_prompt_service):
        """Create a StepExecutor instance with mocked dependencies."""
        return StepExecutor(mock_llm_factory, mock_prompt_service)

    @pytest.fixture
    def sample_step_config(self):
        """Create a sample step configuration."""
        return StepConfig(
            name="initial_translation",
            provider="openai",
            model="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=1000,
            prompt_template="initial_translation.yaml",
            timeout=30,
            retry_attempts=2,
            required_fields=[
                "initial_translation",
                "initial_translation_notes",
            ],
        )

    @pytest.fixture
    def sample_llm_response(self):
        """Create a sample LLM response."""
        response = Mock()
        response.content = """
        <initial_translation>雾来了
踏着猫的小脚。</initial_translation>
        <initial_translation_notes>This translation captures the gentle imagery.</initial_translation_notes>
        """
        response.tokens_used = 150
        response.prompt_tokens = 50
        response.completion_tokens = 100
        return response

    @pytest.fixture
    def sample_translation_input(self):
        """Create sample translation input data."""
        return TranslationInput(
            original_poem="The fog comes on little cat feet.",
            source_lang="English",
            target_lang="Chinese",
        )

    @pytest.mark.asyncio
    async def test_execute_step_success(
        self,
        step_executor,
        mock_llm_factory,
        mock_prompt_service,
        sample_step_config,
        sample_llm_response,
    ):
        """Test successful step execution."""
        # Setup mocks
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = sample_llm_response
        mock_llm_factory.get_provider.return_value = mock_provider

        mock_prompt_service.render_prompt.return_value = (
            "System prompt content",
            "User prompt content",
        )

        input_data = {
            "original_poem": "The fog comes on little cat feet.",
            "source_lang": "English",
            "target_lang": "Chinese",
        }

        # Execute step
        result = await step_executor.execute_step(
            "initial_translation", input_data, sample_step_config
        )

        # Verify results
        assert result["step_name"] == "initial_translation"
        assert result["status"] == "success"
        assert "output" in result
        assert "metadata" in result
        assert (
            result["output"]["initial_translation"] == "雾来了\n踏着猫的小脚。"
        )
        assert (
            result["output"]["initial_translation_notes"]
            == "This translation captures the gentle imagery."
        )

        # Verify metadata
        metadata = result["metadata"]
        assert metadata["model_info"]["provider"] == "openai"
        assert metadata["model_info"]["model"] == "gpt-3.5-turbo"
        assert metadata["usage"]["tokens_used"] == 150
        assert metadata["execution_time_seconds"] > 0

        # Verify mocks were called
        mock_llm_factory.get_provider.assert_called_once()
        mock_prompt_service.render_prompt.assert_called_once_with(
            "initial_translation.yaml", input_data
        )
        mock_provider.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_step_with_retry_success(
        self,
        step_executor,
        mock_llm_factory,
        mock_prompt_service,
        sample_step_config,
        sample_llm_response,
    ):
        """Test successful step execution after retry."""
        # Setup mocks - first call fails, second succeeds
        mock_provider = AsyncMock()
        mock_provider.generate.side_effect = [
            Exception("API timeout"),
            sample_llm_response,
        ]
        mock_llm_factory.get_provider.return_value = mock_provider

        mock_prompt_service.render_prompt.return_value = (
            "System prompt content",
            "User prompt content",
        )

        input_data = {
            "original_poem": "Test poem",
            "source_lang": "English",
            "target_lang": "Chinese",
        }

        # Execute step
        result = await step_executor.execute_step(
            "initial_translation", input_data, sample_step_config
        )

        # Verify success after retry
        assert result["status"] == "success"
        assert mock_provider.generate.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_step_retry_exhausted(
        self,
        step_executor,
        mock_llm_factory,
        mock_prompt_service,
        sample_step_config,
    ):
        """Test step execution fails after exhausting retries."""
        # Setup mocks - all calls fail
        mock_provider = AsyncMock()
        mock_provider.generate.side_effect = Exception("API error")
        mock_llm_factory.get_provider.return_value = mock_provider

        mock_prompt_service.render_prompt.return_value = (
            "System prompt content",
            "User prompt content",
        )

        input_data = {
            "original_poem": "Test poem",
            "source_lang": "English",
            "target_lang": "Chinese",
        }

        # Execute step - should raise exception
        with pytest.raises(LLMCallError) as exc_info:
            await step_executor.execute_step(
                "initial_translation", input_data, sample_step_config
            )

        assert "LLM API call failed after 3 attempts" in str(exc_info.value)
        assert mock_provider.generate.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_execute_step_prompt_rendering_error(
        self, step_executor, mock_prompt_service, sample_step_config
    ):
        """Test handling of prompt rendering errors."""
        # Setup mock to raise template error
        from src.vpsweb.services.prompts import TemplateLoadError

        mock_prompt_service.render_prompt.side_effect = TemplateLoadError(
            "Template not found"
        )

        input_data = {
            "original_poem": "Test poem",
            "source_lang": "English",
            "target_lang": "Chinese",
        }

        # Execute step - should raise exception
        with pytest.raises(PromptRenderingError) as exc_info:
            await step_executor.execute_step(
                "initial_translation", input_data, sample_step_config
            )

        assert "Failed to render prompt template" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_step_output_parsing_error(
        self,
        step_executor,
        mock_llm_factory,
        mock_prompt_service,
        sample_step_config,
    ):
        """Test handling of output parsing errors."""
        # Setup mocks
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = Mock(
            content="Invalid XML content", tokens_used=50
        )
        mock_llm_factory.get_provider.return_value = mock_provider

        mock_prompt_service.render_prompt.return_value = (
            "System prompt content",
            "User prompt content",
        )

        input_data = {
            "original_poem": "Test poem",
            "source_lang": "English",
            "target_lang": "Chinese",
        }

        # Execute step - should raise exception due to missing required fields
        with pytest.raises(OutputParsingError) as exc_info:
            await step_executor.execute_step(
                "initial_translation", input_data, sample_step_config
            )

        assert "Failed to parse or validate LLM output" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_initial_translation(
        self,
        step_executor,
        mock_llm_factory,
        mock_prompt_service,
        sample_step_config,
        sample_llm_response,
        sample_translation_input,
    ):
        """Test the specific initial translation step."""
        # Setup mocks
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = sample_llm_response
        mock_llm_factory.get_provider.return_value = mock_provider

        mock_prompt_service.render_prompt.return_value = (
            "System prompt content",
            "User prompt content",
        )

        # Execute initial translation
        result = await step_executor.execute_initial_translation(
            sample_translation_input, sample_step_config
        )

        # Verify results
        assert result["step_name"] == "initial_translation"
        assert result["status"] == "success"
        assert "initial_translation" in result["output"]
        assert "initial_translation_notes" in result["output"]

        # Verify correct input data was passed
        call_args = mock_prompt_service.render_prompt.call_args[0]
        assert call_args[0] == "initial_translation.yaml"
        assert (
            call_args[1]["original_poem"]
            == "The fog comes on little cat feet."
        )
        assert call_args[1]["source_lang"] == "English"
        assert call_args[1]["target_lang"] == "Chinese"

    @pytest.mark.asyncio
    async def test_execute_editor_review(
        self,
        step_executor,
        mock_llm_factory,
        mock_prompt_service,
        sample_step_config,
        sample_translation_input,
    ):
        """Test the specific editor review step."""
        # Setup mocks
        mock_provider = AsyncMock()
        editor_response = Mock()
        editor_response.content = """
        <editor_suggestions>1. Consider using more poetic language\n2. Check rhythm consistency</editor_suggestions>
        """
        editor_response.tokens_used = 80
        mock_provider.generate.return_value = editor_response
        mock_llm_factory.get_provider.return_value = mock_provider

        mock_prompt_service.render_prompt.return_value = (
            "Editor review system prompt",
            "Editor review user prompt",
        )

        # Create initial translation
        initial_translation = InitialTranslation(
            original_poem="The fog comes on little cat feet.",
            source_lang="English",
            target_lang="Chinese",
            initial_translation="雾来了\n踏着猫的小脚。",
            initial_translation_notes="Translation notes with sufficient length to meet the word count requirement for validation. This needs to be longer to pass the 200-300 word validation check that is built into the model.",
            model_info={"provider": "openai", "model": "gpt-3.5-turbo"},
            tokens_used=150,
            translated_poem_title="",  # Add this required field
            translated_poet_name="",  # Add this required field
        )

        # Execute editor review
        result = await step_executor.execute_editor_review(
            initial_translation, sample_translation_input, sample_step_config
        )

        # Verify results
        assert result["step_name"] == "editor_review"
        assert result["status"] == "success"

        # Verify correct input data was passed
        call_args = mock_prompt_service.render_prompt.call_args[0]
        assert call_args[0] == "editor_review"
        assert call_args[1]["initial_translation"] == "雾来了\n踏着猫的小脚。"

    @pytest.mark.asyncio
    async def test_execute_translator_revision(
        self,
        step_executor,
        mock_llm_factory,
        mock_prompt_service,
        sample_step_config,
        sample_translation_input,
    ):
        """Test the specific translator revision step."""
        # Setup mocks
        mock_provider = AsyncMock()
        revision_response = Mock()
        revision_response.content = """
        <revised_translation>雾悄悄地来了\n像猫一样轻盈。</revised_translation>
        <revised_translation_notes>Based on editor suggestions, refined the translation.</revised_translation_notes>
        """
        revision_response.tokens_used = 120
        mock_provider.generate.return_value = revision_response
        mock_llm_factory.get_provider.return_value = mock_provider

        mock_prompt_service.render_prompt.return_value = (
            "Revision system prompt",
            "Revision user prompt",
        )

        # Create editor review
        editor_review = Mock()
        editor_review.original_poem = "The fog comes on little cat feet."
        editor_review.source_lang = "English"
        editor_review.target_lang = "Chinese"
        editor_review.initial_translation = "雾来了\n踏着猫的小脚。"
        editor_review.initial_translation_notes = "Translation notes with sufficient length to meet the word count requirement for validation. This needs to be longer to pass the 200-300 word validation check that is built into the model."
        editor_review.editor_suggestions = (
            "Consider using more poetic language"
        )
        editor_review.translated_poem_title = ""  # Add this
        editor_review.translated_poet_name = ""  # Add this

        # Execute translator revision
        result = await step_executor.execute_translator_revision(
            editor_review,
            sample_translation_input,
            sample_step_config,
        )

        # Verify results
        assert result["step_name"] == "translator_revision"
        assert result["status"] == "success"

        # Verify correct input data was passed
        call_args = mock_prompt_service.render_prompt.call_args[0]
        assert call_args[0] == "translator_revision"
        assert (
            call_args[1]["editor_suggestions"]
            == "Consider using more poetic language"
        )

    def test_validate_step_inputs(self, step_executor):
        """Test input validation for unknown step name."""
        config = Mock(spec=StepConfig)

        # Invalid step name
        with pytest.raises(
            ValueError, match="Unknown step name: invalid_step"
        ):
            step_executor._validate_step_inputs(
                "invalid_step", {"key": "value"}, config
            )

    @pytest.mark.asyncio
    async def test_get_llm_provider_error(
        self, step_executor, mock_llm_factory
    ):
        """Test LLM provider initialization error handling."""
        # Setup mock to raise exception
        mock_llm_factory.get_provider_config.side_effect = Exception(
            "Provider error"
        )

        config = Mock(spec=StepConfig)
        config.provider = "openai"

        # Should raise LLMCallError
        with pytest.raises(
            LLMCallError, match="Failed to initialize LLM provider"
        ):
            await step_executor._get_llm_provider(config)

    def test_build_step_result(
        self, step_executor, sample_llm_response, sample_step_config
    ):
        """Test result building with metadata."""
        parsed_output = {
            "initial_translation": "Test translation",
            "initial_translation_notes": "Test notes",
        }
        execution_time = 2.5

        result = step_executor._build_step_result(
            "initial_translation",
            parsed_output,
            sample_llm_response,
            execution_time,
            sample_step_config,
        )

        # Verify structure
        assert result["step_name"] == "initial_translation"
        assert result["status"] == "success"
        assert result["output"] == parsed_output

        # Verify metadata
        metadata = result["metadata"]
        assert metadata["execution_time_seconds"] == execution_time
        assert metadata["model_info"]["provider"] == "openai"
        assert metadata["model_info"]["model"] == "gpt-3.5-turbo"
        assert metadata["usage"]["tokens_used"] == 150
        assert metadata["raw_response"]["content_length"] == len(
            sample_llm_response.content
        )
        assert "content_preview" in metadata["raw_response"]
        assert "timestamp" in metadata

    def test_step_executor_repr(
        self, step_executor, mock_llm_factory, mock_prompt_service
    ):
        """Test string representation."""
        repr_str = repr(step_executor)
        assert "StepExecutor" in repr_str
        assert "llm_factory" in repr_str
        assert "prompt_service" in repr_str

    @pytest.mark.asyncio
    async def test_empty_llm_response_handling(
        self,
        step_executor,
        mock_llm_factory,
        mock_prompt_service,
        sample_step_config,
    ):
        """Test handling of empty LLM responses."""
        # Setup mocks with empty response
        mock_provider = AsyncMock()
        empty_response = Mock()
        empty_response.content = ""
        empty_response.tokens_used = 0
        mock_provider.generate.return_value = empty_response
        mock_llm_factory.get_provider.return_value = mock_provider

        mock_prompt_service.render_prompt.return_value = (
            "System prompt content",
            "User prompt content",
        )

        input_data = {
            "original_poem": "Test poem",
            "source_lang": "English",
            "target_lang": "Chinese",
        }

        # Execute step - should raise exception
        with pytest.raises(LLMCallError, match="LLM returned empty response"):
            await step_executor.execute_step(
                "initial_translation", input_data, sample_step_config
            )

    @pytest.mark.asyncio
    async def test_plain_text_response_fallback(
        self,
        step_executor,
        mock_llm_factory,
        mock_prompt_service,
        sample_step_config,
    ):
        """Test fallback handling when no XML tags are found."""
        # Setup mocks with plain text response (no XML tags)
        mock_provider = AsyncMock()
        plain_text_response = Mock()
        plain_text_response.content = "This is plain text without XML tags"
        plain_text_response.tokens_used = 75
        mock_provider.generate.return_value = plain_text_response
        mock_llm_factory.get_provider.return_value = mock_provider

        mock_prompt_service.render_prompt.return_value = (
            "System prompt content",
            "User prompt content",
        )

        # Modify config to not require specific fields
        config_no_required = StepConfig(
            name="initial_translation",
            provider=sample_step_config.provider,
            model="gpt-3.5-turbo",
            prompt_template="initial_translation.yaml",
            required_fields=[],  # No required fields
        )

        input_data = {
            "original_poem": "Test poem",
            "source_lang": "English",
            "target_lang": "Chinese",
        }

        # Execute step - should succeed with fallback
        result = await step_executor.execute_step(
            "initial_translation", input_data, config_no_required
        )

        assert result["status"] == "success"
        assert (
            result["output"]["content"]
            == "This is plain text without XML tags"
        )


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v"])
