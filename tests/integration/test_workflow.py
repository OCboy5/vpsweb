"""
Integration tests for the complete translation workflow.

These tests verify the complete workflow execution with mocked LLM API calls,
ensuring functional equivalence with the Dify workflow without making actual API calls.
"""

from unittest.mock import AsyncMock

import pytest

from src.vpsweb.core.workflow import TranslationWorkflow
from src.vpsweb.models.config import WorkflowMode
from src.vpsweb.models.translation import TranslationInput, TranslationOutput
from src.vpsweb.services.llm.factory import LLMFactory


class TestTranslationWorkflowIntegration:
    """Integration tests for the complete translation workflow."""

    @pytest.mark.asyncio
    async def test_complete_workflow_execution(
        self,
        sample_translation_input,
        integration_workflow_config,
        integration_providers_config,
        mock_llm_factory_integration,
    ):
        """Test complete workflow execution with mocked LLM calls."""
        # Create workflow with legacy parameters and system config
        system_config = {"preview_lengths": {"input_preview": 100}}
        workflow = TranslationWorkflow(
            integration_workflow_config,
            integration_providers_config,
            WorkflowMode.HYBRID,
            system_config=system_config,
        )

        # Execute workflow
        result = await workflow.execute(sample_translation_input)

        # Verify result structure
        assert isinstance(result, TranslationOutput)
        assert result.workflow_id is not None
        assert result.original_poem == "The fog comes on little cat feet."
        assert result.source_lang == "English"
        assert result.target_lang == "Chinese"

        # Verify each step produced expected output
        assert (
            result.initial_translation.initial_translation == "雾来了，踏着猫的细步。"
        )
        assert "gentle imagery" in result.initial_translation.initial_translation_notes

        assert "poetic language" in result.editor_review.text
        assert "rhythm" in result.editor_review.text

        assert (
            result.revised_translation.revised_translation
            == "雾来了，踏着猫儿轻盈的脚步。"
        )
        assert (
            "editor's suggestions"
            in result.revised_translation.revised_translation_notes
        )

        # Verify metadata
        assert result.total_tokens > 0
        assert result.duration_seconds > 0.0

    @pytest.mark.asyncio
    async def test_workflow_with_different_poem(
        self,
        integration_workflow_config,
        integration_providers_config,
        mock_llm_factory_integration,
    ):
        """Test workflow with a different poem."""
        input_data = TranslationInput(
            original_poem="Two roads diverged in a yellow wood,",
            source_lang="English",
            target_lang="Chinese",
        )

        workflow = TranslationWorkflow(integration_workflow_config)
        result = await workflow.execute(input_data)

        assert result.original_poem == "Two roads diverged in a yellow wood,"
        assert result.initial_translation.initial_translation is not None
        assert result.revised_translation.revised_translation is not None

    @pytest.mark.asyncio
    async def test_workflow_error_handling(
        self, sample_translation_input, integration_workflow_config, mocker
    ):
        """Test workflow error handling when LLM API fails."""
        # Mock LLM to raise an exception
        mock_llm = AsyncMock()
        mock_llm.generate.side_effect = Exception("API Error")

        # Mock the factory to return our failing LLM
        mocker.patch.object(LLMFactory, "get_provider", return_value=mock_llm)

        workflow = TranslationWorkflow(integration_workflow_config)

        # Should raise an exception
        with pytest.raises(Exception) as exc_info:
            await workflow.execute(sample_translation_input)

        assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_workflow_with_malformed_xml_response(
        self, sample_translation_input, integration_workflow_config, mocker
    ):
        """Test workflow handling of malformed XML responses."""
        # Mock LLM to return malformed XML
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "<initial_translation>No closing tag"  # Malformed XML
                    }
                }
            ]
        }

        mocker.patch.object(LLMFactory, "get_provider", return_value=mock_llm)

        workflow = TranslationWorkflow(integration_workflow_config)

        # Should raise an exception due to parsing error
        with pytest.raises(Exception) as exc_info:
            await workflow.execute(sample_translation_input)

        assert "Failed to parse XML" in str(
            exc_info.value
        ) or "Missing required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_workflow_metadata_aggregation(
        self,
        sample_translation_input,
        integration_workflow_config,
        mock_llm_factory_integration,
    ):
        """Test that workflow properly aggregates metadata from all steps."""
        workflow = TranslationWorkflow(integration_workflow_config)
        result = await workflow.execute(sample_translation_input)

        # Verify all step metadata is present
        assert result.initial_translation.model_info is not None
        assert result.initial_translation.tokens_used > 0
        assert result.initial_translation.timestamp is not None

        assert result.editor_review.model_info is not None
        assert result.editor_review.tokens_used > 0
        assert result.editor_review.timestamp is not None

        assert result.revised_translation.model_info is not None
        assert result.revised_translation.tokens_used > 0
        assert result.revised_translation.timestamp is not None

        # Verify aggregated metadata
        assert result.total_tokens > 0
        assert result.duration_seconds > 0.0
        assert result.full_log is not None

    @pytest.mark.asyncio
    async def test_workflow_congregated_output(
        self,
        sample_translation_input,
        integration_workflow_config,
        mock_llm_factory_integration,
    ):
        """Test that workflow produces correct congregated output format."""
        workflow = TranslationWorkflow(integration_workflow_config)
        result = await workflow.execute(sample_translation_input)

        congregated = result.get_congregated_output()

        # Verify congregated output structure
        assert "original_poem" in congregated
        assert "initial_translation" in congregated
        assert "initial_translation_notes" in congregated
        assert "editor_suggestions" in congregated
        assert "revised_translation" in congregated
        assert "revised_translation_notes" in congregated

        # Verify content
        assert congregated["original_poem"] == "The fog comes on little cat feet."
        assert "雾来了" in congregated["initial_translation"]
        assert "猫" in congregated["revised_translation"]

    @pytest.mark.asyncio
    async def test_workflow_with_empty_poem(
        self, integration_workflow_config, mock_llm_factory_integration
    ):
        """Test workflow with very short poem."""
        input_data = TranslationInput(
            original_poem="Hello world",
            source_lang="English",
            target_lang="Chinese",
        )

        workflow = TranslationWorkflow(integration_workflow_config)
        result = await workflow.execute(input_data)

        # Should still complete successfully
        assert result.initial_translation.initial_translation is not None
        assert result.revised_translation.revised_translation is not None

    @pytest.mark.asyncio
    async def test_workflow_step_ordering(
        self,
        sample_translation_input,
        integration_workflow_config,
        mock_llm_factory_integration,
    ):
        """Test that workflow executes steps in correct order."""
        workflow = TranslationWorkflow(integration_workflow_config)
        result = await workflow.execute(sample_translation_input)

        # Verify step ordering by checking timestamps
        assert result.initial_translation.timestamp <= result.editor_review.timestamp
        assert result.editor_review.timestamp <= result.revised_translation.timestamp

        # Verify that editor review references initial translation
        assert (
            "initial" in result.editor_review.text.lower()
            or "translation" in result.editor_review.text.lower()
        )

        # Verify that revised translation references editor suggestions
        assert (
            "editor" in result.revised_translation.revised_translation_notes.lower()
            or "suggestion"
            in result.revised_translation.revised_translation_notes.lower()
        )

    @pytest.mark.asyncio
    async def test_workflow_with_custom_config(
        self, sample_translation_input, mock_llm_factory_integration
    ):
        """Test workflow with custom step configuration."""
        custom_config = WorkflowConfig(
            name="custom_workflow",
            version="1.0.0",
            steps=[
                StepConfig(
                    name="initial_translation",
                    provider="tongyi",
                    model="qwen-max",
                    temperature=0.8,  # Different temperature
                    max_tokens=500,  # Different token limit
                ),
                StepConfig(
                    name="editor_review",
                    provider="deepseek",
                    model="deepseek-chat",
                    temperature=0.3,  # Different temperature
                    max_tokens=400,  # Different token limit
                ),
                StepConfig(
                    name="translator_revision",
                    provider="tongyi",
                    model="qwen-max",
                    temperature=0.7,  # Different temperature
                    max_tokens=600,  # Different token limit
                ),
            ],
        )

        workflow = TranslationWorkflow(custom_config)
        result = await workflow.execute(sample_translation_input)

        # Should still complete successfully with custom config
        assert result.initial_translation.initial_translation is not None
        assert result.revised_translation.revised_translation is not None

    @pytest.mark.asyncio
    async def test_workflow_persistence(
        self,
        sample_translation_input,
        integration_workflow_config,
        mock_llm_factory_integration,
        temp_output_dir,
    ):
        """Test that workflow output can be saved and loaded."""
        workflow = TranslationWorkflow(integration_workflow_config)
        result = await workflow.execute(sample_translation_input)

        # Save to file
        output_file = temp_output_dir / "workflow_output.json"
        result.save_to_file(str(output_file))

        # Load from file
        from src.vpsweb.models.translation import TranslationOutput

        loaded_result = TranslationOutput.load_from_file(str(output_file))

        # Verify loaded result matches original
        assert loaded_result.workflow_id == result.workflow_id
        assert loaded_result.original_poem == result.original_poem
        assert (
            loaded_result.initial_translation.initial_translation
            == result.initial_translation.initial_translation
        )
        assert (
            loaded_result.revised_translation.revised_translation
            == result.revised_translation.revised_translation
        )
        assert loaded_result.total_tokens == result.total_tokens


class TestWorkflowFunctionalEquivalence:
    """Tests to verify functional equivalence with Dify workflow."""

    @pytest.mark.asyncio
    async def test_three_step_workflow_structure(
        self,
        sample_translation_input,
        integration_workflow_config,
        mock_llm_factory_integration,
    ):
        """Verify the workflow follows the Translator→Editor→Translator structure."""
        workflow = TranslationWorkflow(integration_workflow_config)
        result = await workflow.execute(sample_translation_input)

        # Verify three-step structure
        assert hasattr(result, "initial_translation")
        assert hasattr(result, "editor_review")
        assert hasattr(result, "revised_translation")

        # Verify step dependencies
        initial_text = result.initial_translation.initial_translation
        editor_text = result.editor_review.text
        revised_text = result.revised_translation.revised_translation

        # Editor should reference the initial translation
        assert initial_text is not None and len(initial_text) > 0
        assert editor_text is not None and len(editor_text) > 0
        assert revised_text is not None and len(revised_text) > 0

        # Revised translation should be different from initial (improved)
        assert initial_text != revised_text

    @pytest.mark.asyncio
    async def test_xml_parsing_consistency(
        self,
        sample_translation_input,
        integration_workflow_config,
        mock_llm_factory_integration,
    ):
        """Verify XML parsing follows the exact logic from vpts.yml."""
        workflow = TranslationWorkflow(integration_workflow_config)
        result = await workflow.execute(sample_translation_input)

        # Verify that XML tags are properly parsed and extracted
        initial = result.initial_translation
        revised = result.revised_translation

        # Both should have translations and notes
        assert initial.initial_translation is not None
        assert initial.initial_translation_notes is not None
        assert revised.revised_translation is not None
        assert revised.revised_translation_notes is not None

        # Translations should contain Chinese characters
        assert any("\u4e00" <= char <= "\u9fff" for char in initial.initial_translation)
        assert any("\u4e00" <= char <= "\u9fff" for char in revised.revised_translation)

    @pytest.mark.asyncio
    async def test_editor_suggestions_format(
        self,
        sample_translation_input,
        integration_workflow_config,
        mock_llm_factory_integration,
    ):
        """Verify editor suggestions follow the expected numbered format."""
        workflow = TranslationWorkflow(integration_workflow_config)
        result = await workflow.execute(sample_translation_input)

        editor_text = result.editor_review.text

        # Should contain numbered suggestions
        assert "1." in editor_text or "2." in editor_text or "3." in editor_text

        # Should contain improvement suggestions
        assert any(
            keyword in editor_text.lower()
            for keyword in [
                "improve",
                "suggest",
                "consider",
                "better",
                "enhance",
            ]
        )

    @pytest.mark.asyncio
    async def test_complete_metadata_generation(
        self,
        sample_translation_input,
        integration_workflow_config,
        mock_llm_factory_integration,
    ):
        """Verify complete metadata generation matches Dify workflow."""
        workflow = TranslationWorkflow(integration_workflow_config)
        result = await workflow.execute(sample_translation_input)

        # Verify all required metadata fields
        assert result.workflow_id is not None
        assert result.total_tokens > 0
        assert result.duration_seconds > 0.0
        assert result.full_log is not None

        # Verify step-level metadata
        assert result.initial_translation.tokens_used > 0
        assert result.editor_review.tokens_used > 0
        assert result.revised_translation.tokens_used > 0

        # Verify model information
        assert result.initial_translation.model_info is not None
        assert result.editor_review.model_info is not None
