"""
Integration tests for the VPSWeb CLI.

These tests use Click's CliRunner to test CLI commands with various input methods,
configuration loading, and output generation without making actual API calls.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from click.testing import CliRunner
from src.vpsweb.__main__ import cli


class TestCLIIntegration:
    """Integration tests for the CLI interface."""

    def test_cli_help_command(self, cli_runner):
        """Test that help command works."""
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Vox Poetica Studio Web" in result.output
        assert "translate" in result.output

    def test_cli_version_command(self, cli_runner):
        """Test that version command works."""
        result = cli_runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "vpsweb" in result.output
        assert "0.2.8" in result.output

    @patch("src.vpsweb.__main__.TranslationWorkflow")
    @patch("src.vpsweb.__main__.load_config")
    def test_cli_translate_from_file(
        self,
        mock_load_config,
        mock_workflow_class,
        cli_runner,
        sample_poem_file,
        sample_config,
    ):
        """Test translate command with file input."""
        # Mock the workflow execution
        mock_workflow = MagicMock()
        mock_workflow.execute.return_value = MagicMock(
            workflow_id="test-workflow-123",
            original_poem="The fog comes on little cat feet.",
            source_lang="English",
            target_lang="Chinese",
            initial_translation=MagicMock(
                initial_translation="雾来了，踏着猫的细步。",
                initial_translation_notes="Test notes",
            ),
            editor_review=MagicMock(text="1. Test suggestion\n2. Another suggestion"),
            revised_translation=MagicMock(
                revised_translation="雾来了，踏着猫儿轻盈的脚步。",
                revised_translation_notes="Revised notes",
            ),
            duration_seconds=10.5,
            total_tokens=1200,
        )
        mock_workflow_class.return_value = mock_workflow

        # Mock configuration loading
        mock_load_config.return_value = sample_config

        # Execute CLI command
        result = cli_runner.invoke(
            cli,
            [
                "translate",
                "--input",
                str(sample_poem_file),
                "--source",
                "English",
                "--target",
                "Chinese",
            ],
        )

        # Verify success
        assert result.exit_code == 0
        assert "Vox Poetica Studio Web" in result.output
        assert "TRANSLATION COMPLETE" in result.output
        assert "Workflow ID: test-workflow-123" in result.output

        # Verify workflow was called with correct input
        mock_workflow.execute.assert_called_once()
        input_data = mock_workflow.execute.call_args[0][0]
        assert input_data.original_poem == "The fog comes on little cat feet."
        assert input_data.source_lang == "English"
        assert input_data.target_lang == "Chinese"

    @patch("src.vpsweb.__main__.TranslationWorkflow")
    @patch("src.vpsweb.__main__.load_config")
    def test_cli_translate_from_stdin(
        self, mock_load_config, mock_workflow_class, cli_runner, sample_config
    ):
        """Test translate command with stdin input."""
        # Mock the workflow execution
        mock_workflow = MagicMock()
        mock_workflow.execute.return_value = MagicMock(
            workflow_id="test-workflow-456",
            original_poem="Test poem from stdin",
            source_lang="English",
            target_lang="Chinese",
            duration_seconds=8.5,
            total_tokens=900,
        )
        mock_workflow_class.return_value = mock_workflow

        # Mock configuration loading
        mock_load_config.return_value = sample_config

        # Execute CLI command with stdin input
        result = cli_runner.invoke(
            cli,
            ["translate", "--source", "English", "--target", "Chinese"],
            input="Test poem from stdin\n",
        )

        # Verify success
        assert result.exit_code == 0
        assert "Reading poem from stdin" in result.output
        assert "TRANSLATION COMPLETE" in result.output

        # Verify workflow was called with correct input
        mock_workflow.execute.assert_called_once()
        input_data = mock_workflow.execute.call_args[0][0]
        assert input_data.original_poem == "Test poem from stdin"

    @patch("src.vpsweb.__main__.TranslationWorkflow")
    @patch("src.vpsweb.__main__.load_config")
    def test_cli_translate_with_custom_config(
        self,
        mock_load_config,
        mock_workflow_class,
        cli_runner,
        sample_poem_file,
        sample_config,
    ):
        """Test translate command with custom configuration directory."""
        # Create temporary config directory
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Mock the workflow
            mock_workflow = MagicMock()
            mock_workflow.execute.return_value = MagicMock(
                workflow_id="test-workflow-custom",
                duration_seconds=12.0,
                total_tokens=1100,
            )
            mock_workflow_class.return_value = mock_workflow

            # Mock configuration loading
            mock_load_config.return_value = sample_config

            # Execute CLI command with custom config
            result = cli_runner.invoke(
                cli,
                [
                    "translate",
                    "--input",
                    str(sample_poem_file),
                    "--source",
                    "English",
                    "--target",
                    "Chinese",
                    "--config",
                    str(config_dir),
                ],
            )

            # Verify success
            assert result.exit_code == 0
            assert mock_load_config.called_with(config_dir)

    @patch("src.vpsweb.__main__.TranslationWorkflow")
    @patch("src.vpsweb.__main__.load_config")
    def test_cli_translate_with_custom_output_dir(
        self,
        mock_load_config,
        mock_workflow_class,
        cli_runner,
        sample_poem_file,
        sample_config,
        temp_output_dir,
    ):
        """Test translate command with custom output directory."""
        # Mock the workflow
        mock_workflow = MagicMock()
        mock_workflow.execute.return_value = MagicMock(
            workflow_id="test-workflow-output", duration_seconds=9.5, total_tokens=950
        )
        mock_workflow_class.return_value = mock_workflow

        # Mock configuration loading
        mock_load_config.return_value = sample_config

        # Execute CLI command with custom output
        result = cli_runner.invoke(
            cli,
            [
                "translate",
                "--input",
                str(sample_poem_file),
                "--source",
                "English",
                "--target",
                "Chinese",
                "--output",
                str(temp_output_dir),
            ],
        )

        # Verify success
        assert result.exit_code == 0
        assert "TRANSLATION COMPLETE" in result.output

    @patch("src.vpsweb.__main__.load_config")
    def test_cli_translate_dry_run(
        self, mock_load_config, cli_runner, sample_poem_file, sample_config
    ):
        """Test translate command with dry-run mode."""
        # Mock configuration loading
        mock_load_config.return_value = sample_config

        # Execute CLI command with dry-run
        result = cli_runner.invoke(
            cli,
            [
                "translate",
                "--input",
                str(sample_poem_file),
                "--source",
                "English",
                "--target",
                "Chinese",
                "--dry-run",
            ],
        )

        # Verify success (validation only, no execution)
        assert result.exit_code == 0
        assert "Validating configuration and input" in result.output
        assert "Dry run completed" in result.output
        assert "TRANSLATION COMPLETE" not in result.output  # No actual translation

    @patch("src.vpsweb.__main__.TranslationWorkflow")
    @patch("src.vpsweb.__main__.load_config")
    def test_cli_translate_verbose_mode(
        self,
        mock_load_config,
        mock_workflow_class,
        cli_runner,
        sample_poem_file,
        sample_config,
    ):
        """Test translate command with verbose logging."""
        # Mock the workflow
        mock_workflow = MagicMock()
        mock_workflow.execute.return_value = MagicMock(
            workflow_id="test-workflow-verbose",
            duration_seconds=11.0,
            total_tokens=1050,
        )
        mock_workflow_class.return_value = mock_workflow

        # Mock configuration loading
        mock_load_config.return_value = sample_config

        # Execute CLI command with verbose mode
        result = cli_runner.invoke(
            cli,
            [
                "translate",
                "--input",
                str(sample_poem_file),
                "--source",
                "English",
                "--target",
                "Chinese",
                "--verbose",
            ],
        )

        # Verify success
        assert result.exit_code == 0
        assert "TRANSLATION COMPLETE" in result.output

    def test_cli_translate_missing_required_options(self, cli_runner):
        """Test translate command with missing required options."""
        # Missing source language
        result = cli_runner.invoke(cli, ["translate", "--target", "Chinese"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "Error" in result.output

        # Missing target language
        result = cli_runner.invoke(cli, ["translate", "--source", "English"])
        assert result.exit_code != 0

    def test_cli_translate_invalid_language(self, cli_runner, sample_poem_file):
        """Test translate command with invalid language."""
        # Invalid source language
        result = cli_runner.invoke(
            cli,
            [
                "translate",
                "--input",
                str(sample_poem_file),
                "--source",
                "InvalidLang",
                "--target",
                "Chinese",
            ],
        )
        assert result.exit_code != 0

        # Invalid target language
        result = cli_runner.invoke(
            cli,
            [
                "translate",
                "--input",
                str(sample_poem_file),
                "--source",
                "English",
                "--target",
                "InvalidLang",
            ],
        )
        assert result.exit_code != 0

    def test_cli_translate_nonexistent_file(self, cli_runner):
        """Test translate command with nonexistent input file."""
        result = cli_runner.invoke(
            cli,
            [
                "translate",
                "--input",
                "/nonexistent/file.txt",
                "--source",
                "English",
                "--target",
                "Chinese",
            ],
        )
        assert result.exit_code != 0
        assert "Input file not found" in result.output or "Error" in result.output

    @patch("src.vpsweb.__main__.TranslationWorkflow")
    @patch("src.vpsweb.__main__.load_config")
    def test_cli_translate_workflow_error(
        self,
        mock_load_config,
        mock_workflow_class,
        cli_runner,
        sample_poem_file,
        sample_config,
    ):
        """Test CLI error handling when workflow fails."""
        # Mock workflow to raise an exception
        mock_workflow = MagicMock()
        mock_workflow.execute.side_effect = Exception("Workflow execution failed")
        mock_workflow_class.return_value = mock_workflow

        # Mock configuration loading
        mock_load_config.return_value = sample_config

        # Execute CLI command
        result = cli_runner.invoke(
            cli,
            [
                "translate",
                "--input",
                str(sample_poem_file),
                "--source",
                "English",
                "--target",
                "Chinese",
            ],
        )

        # Should fail with error message
        assert result.exit_code != 0
        assert (
            "Translation error" in result.output
            or "Workflow execution failed" in result.output
        )

    @patch("src.vpsweb.__main__.TranslationWorkflow")
    @patch("src.vpsweb.__main__.load_config")
    def test_cli_translate_output_file_creation(
        self,
        mock_load_config,
        mock_workflow_class,
        cli_runner,
        sample_poem_file,
        sample_config,
        temp_output_dir,
    ):
        """Test that CLI creates output files correctly."""
        # Mock the workflow with file-saving capability
        mock_output = MagicMock()
        mock_output.workflow_id = "test-workflow-file"
        mock_output.save_to_file = MagicMock()

        mock_workflow = MagicMock()
        mock_workflow.execute.return_value = mock_output
        mock_workflow_class.return_value = mock_workflow

        # Mock configuration loading
        mock_load_config.return_value = sample_config

        # Execute CLI command
        result = cli_runner.invoke(
            cli,
            [
                "translate",
                "--input",
                str(sample_poem_file),
                "--source",
                "English",
                "--target",
                "Chinese",
                "--output",
                str(temp_output_dir),
            ],
        )

        # Verify success and file saving
        assert result.exit_code == 0
        assert "Saving translation results" in result.output
        mock_output.save_to_file.assert_called_once()

    def test_cli_translate_empty_stdin(self, cli_runner):
        """Test translate command with empty stdin."""
        result = cli_runner.invoke(
            cli,
            ["translate", "--source", "English", "--target", "Chinese"],
            input="",  # Empty input
        )
        assert result.exit_code != 0
        assert "No poem text provided" in result.output or "Error" in result.output

    @patch("src.vpsweb.__main__.TranslationWorkflow")
    @patch("src.vpsweb.__main__.load_config")
    def test_cli_translate_different_language_pairs(
        self,
        mock_load_config,
        mock_workflow_class,
        cli_runner,
        sample_poem_file,
        sample_config,
    ):
        """Test translate command with different language pairs."""
        # Mock the workflow
        mock_workflow = MagicMock()
        mock_workflow.execute.return_value = MagicMock(
            workflow_id="test-workflow-lang", duration_seconds=10.0, total_tokens=1000
        )
        mock_workflow_class.return_value = mock_workflow

        # Mock configuration loading
        mock_load_config.return_value = sample_config

        # Test Chinese to English
        result = cli_runner.invoke(
            cli,
            [
                "translate",
                "--input",
                str(sample_poem_file),
                "--source",
                "Chinese",
                "--target",
                "English",
            ],
        )
        assert result.exit_code == 0

        # Test English to Polish (source only, since Polish can't be target)
        # This should fail validation
        result = cli_runner.invoke(
            cli,
            [
                "translate",
                "--input",
                str(sample_poem_file),
                "--source",
                "English",
                "--target",
                "Polish",
            ],
        )
        assert result.exit_code != 0


class TestCLIFunctionalEquivalence:
    """Tests to verify CLI functional equivalence with Dify workflow."""

    @patch("src.vpsweb.__main__.TranslationWorkflow")
    @patch("src.vpsweb.__main__.load_config")
    def test_cli_produces_complete_output(
        self,
        mock_load_config,
        mock_workflow_class,
        cli_runner,
        sample_poem_file,
        sample_config,
    ):
        """Verify CLI produces complete output matching Dify workflow."""
        # Create a realistic mock output
        mock_output = MagicMock()
        mock_output.workflow_id = "dify-equivalent-123"
        mock_output.original_poem = "The fog comes on little cat feet."
        mock_output.source_lang = "English"
        mock_output.target_lang = "Chinese"
        mock_output.initial_translation = MagicMock(
            initial_translation="雾来了，踏着猫的细步。",
            initial_translation_notes="Literal translation preserving imagery",
        )
        mock_output.editor_review = MagicMock(
            text="1. Improve poetic language\n2. Enhance rhythm"
        )
        mock_output.revised_translation = MagicMock(
            revised_translation="雾来了，踏着猫儿轻盈的脚步。",
            revised_translation_notes="Improved based on editor suggestions",
        )
        mock_output.duration_seconds = 15.5
        mock_output.total_tokens = 1250
        mock_output.get_congregated_output.return_value = {
            "original_poem": "The fog comes on little cat feet.",
            "initial_translation": "雾来了，踏着猫的细步。",
            "initial_translation_notes": "Literal translation preserving imagery",
            "editor_suggestions": "1. Improve poetic language\n2. Enhance rhythm",
            "revised_translation": "雾来了，踏着猫儿轻盈的脚步。",
            "revised_translation_notes": "Improved based on editor suggestions",
        }

        mock_workflow = MagicMock()
        mock_workflow.execute.return_value = mock_output
        mock_workflow_class.return_value = mock_workflow

        # Mock configuration loading
        mock_load_config.return_value = sample_config

        # Execute CLI command
        result = cli_runner.invoke(
            cli,
            [
                "translate",
                "--input",
                str(sample_poem_file),
                "--source",
                "English",
                "--target",
                "Chinese",
            ],
        )

        # Verify complete output structure
        assert result.exit_code == 0
        assert "TRANSLATION COMPLETE" in result.output
        assert "Workflow ID: dify-equivalent-123" in result.output
        assert "Total time: 15.50s" in result.output
        assert "Total tokens: 1250" in result.output

        # Verify translation preview
        assert "Initial Translation:" in result.output
        assert "Revised Translation:" in result.output
        assert "Editor suggestions:" in result.output

    @patch("src.vpsweb.__main__.TranslationWorkflow")
    @patch("src.vpsweb.__main__.load_config")
    def test_cli_progress_indication(
        self,
        mock_load_config,
        mock_workflow_class,
        cli_runner,
        sample_poem_file,
        sample_config,
    ):
        """Verify CLI shows proper progress indication."""
        # Mock the workflow
        mock_workflow = MagicMock()
        mock_workflow.execute.return_value = MagicMock(
            workflow_id="test-progress", duration_seconds=12.0, total_tokens=1100
        )
        mock_workflow_class.return_value = mock_workflow

        # Mock configuration loading
        mock_load_config.return_value = sample_config

        # Execute CLI command
        result = cli_runner.invoke(
            cli,
            [
                "translate",
                "--input",
                str(sample_poem_file),
                "--source",
                "English",
                "--target",
                "Chinese",
            ],
        )

        # Verify progress indicators
        assert result.exit_code == 0
        assert "Loading configuration" in result.output
        assert "Starting translation workflow" in result.output
        assert "Translating" in result.output
        assert "Saving translation results" in result.output

    @patch("src.vpsweb.__main__.load_config")
    def test_cli_configuration_validation(
        self, mock_load_config, cli_runner, sample_poem_file, sample_config
    ):
        """Verify CLI properly validates configuration."""
        # Mock configuration loading
        mock_load_config.return_value = sample_config

        # Test dry-run mode (configuration validation)
        result = cli_runner.invoke(
            cli,
            [
                "translate",
                "--input",
                str(sample_poem_file),
                "--source",
                "English",
                "--target",
                "Chinese",
                "--dry-run",
            ],
        )

        # Verify validation output
        assert result.exit_code == 0
        assert "Validating configuration and input" in result.output
        assert "Input validation passed" in result.output
        assert "Source: English" in result.output
        assert "Target: Chinese" in result.output
        assert "Poem length:" in result.output
        assert "Dry run completed" in result.output
