"""
Unit tests for Pydantic models in VPSWeb.

Tests model validation, serialization, deserialization, and field validators
for all translation workflow models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.vpsweb.models.translation import (
    TranslationInput,
    InitialTranslation,
    EditorReview,
    RevisedTranslation,
    TranslationOutput,
    Language,
)
from src.vpsweb.services.parser import OutputParser
from src.vpsweb.models.config import (
    WorkflowConfig,
    StepConfig,
    CompleteConfig,
    LoggingConfig,
    MainConfig,
    ModelProviderConfig,
    ProvidersConfig,
)


class TestTranslationInput:
    """Test cases for TranslationInput model."""

    def test_create_valid_translation_input(self):
        """Test creating a valid TranslationInput."""
        input_data = TranslationInput(
            original_poem="The fog comes on little cat feet.",
            source_lang=Language.ENGLISH,
            target_lang=Language.CHINESE,
        )

        assert input_data.original_poem == "The fog comes on little cat feet."
        assert input_data.source_lang == Language.ENGLISH
        assert input_data.target_lang == Language.CHINESE
        assert input_data.metadata is None

    def test_create_with_metadata(self):
        """Test creating TranslationInput with metadata."""
        metadata = {"author": "Carl Sandburg", "title": "Fog", "year": 1916}

        input_data = TranslationInput(
            original_poem="The fog comes on little cat feet.",
            source_lang=Language.ENGLISH,
            target_lang=Language.CHINESE,
            metadata=metadata,
        )

        assert input_data.metadata == metadata

    def test_validation_empty_poem(self):
        """Test validation with empty poem."""
        with pytest.raises(ValidationError) as exc_info:
            TranslationInput(
                original_poem="",
                source_lang=Language.ENGLISH,
                target_lang=Language.CHINESE,
            )

        assert "original_poem" in str(exc_info.value)

    def test_validation_poem_too_long(self):
        """Test validation with poem exceeding max length."""
        long_poem = "x" * 2001  # Exceeds max_length: 2000

        with pytest.raises(ValidationError) as exc_info:
            TranslationInput(
                original_poem=long_poem,
                source_lang=Language.ENGLISH,
                target_lang=Language.CHINESE,
            )

        assert "original_poem" in str(exc_info.value)

    def test_validation_same_source_target_language(self):
        """Test validation when source and target languages are the same."""
        with pytest.raises(ValidationError) as exc_info:
            TranslationInput(
                original_poem="Test poem",
                source_lang=Language.ENGLISH,
                target_lang=Language.ENGLISH,
            )

        assert "Source and target languages must be different" in str(exc_info.value)

    def test_validation_invalid_target_language(self):
        """Test validation with invalid target language."""
        with pytest.raises(ValidationError) as exc_info:
            TranslationInput(
                original_poem="Test poem",
                source_lang=Language.ENGLISH,
                target_lang=Language.POLISH,  # Polish not allowed as target
            )

        assert "Target language must be either English or Chinese" in str(
            exc_info.value
        )

    def test_to_dict_method(self):
        """Test conversion to dictionary."""
        input_data = TranslationInput(
            original_poem="Test poem",
            source_lang=Language.ENGLISH,
            target_lang=Language.CHINESE,
        )

        result = input_data.to_dict()

        assert result["original_poem"] == "Test poem"
        assert result["source_lang"] == "English"
        assert result["target_lang"] == "Chinese"

    def test_from_dict_method(self):
        """Test creation from dictionary."""
        data = {
            "original_poem": "Test poem",
            "source_lang": "English",
            "target_lang": "Chinese",
        }

        input_data = TranslationInput.from_dict(data)

        assert input_data.original_poem == "Test poem"
        assert input_data.source_lang == Language.ENGLISH
        assert input_data.target_lang == Language.CHINESE


class TestInitialTranslation:
    """Test cases for InitialTranslation model."""

    def test_create_valid_initial_translation(self):
        """Test creating a valid InitialTranslation."""
        translation = InitialTranslation(
            initial_translation="雾来了，踏着猫的细步。",
            initial_translation_notes="This translation captures the gentle imagery.",
            model_info={"provider": "tongyi", "model": "qwen-max"},
            tokens_used=250,
        )

        assert translation.initial_translation == "雾来了，踏着猫的细步。"
        assert "gentle imagery" in translation.initial_translation_notes
        assert translation.model_info["provider"] == "tongyi"
        assert translation.tokens_used == 250
        assert isinstance(translation.timestamp, datetime)

    def test_validation_missing_required_fields(self):
        """Test validation with missing required fields."""
        with pytest.raises(ValidationError):
            InitialTranslation(
                initial_translation="",  # Empty required field
                initial_translation_notes="Notes",
                model_info={"provider": "test"},
                tokens_used=100,
            )

    def test_validation_negative_tokens(self):
        """Test validation with negative token count."""
        with pytest.raises(ValidationError) as exc_info:
            InitialTranslation(
                initial_translation="Translation",
                initial_translation_notes="Notes",
                model_info={"provider": "test"},
                tokens_used=-10,  # Negative tokens
            )

        assert "tokens_used" in str(exc_info.value)

    def test_to_dict_method(self):
        """Test conversion to dictionary with ISO timestamp."""
        translation = InitialTranslation(
            initial_translation="Test translation",
            initial_translation_notes="Test notes",
            model_info={"provider": "test"},
            tokens_used=100,
        )

        result = translation.to_dict()

        assert result["initial_translation"] == "Test translation"
        assert result["initial_translation_notes"] == "Test notes"
        assert result["tokens_used"] == 100
        assert "timestamp" in result
        # Timestamp should be in ISO format
        assert "T" in result["timestamp"]  # ISO format indicator

    def test_from_dict_method(self):
        """Test creation from dictionary with ISO timestamp."""
        data = {
            "initial_translation": "Test translation",
            "initial_translation_notes": "Test notes",
            "model_info": {"provider": "test"},
            "tokens_used": 100,
            "timestamp": "2024-01-01T12:00:00",
        }

        translation = InitialTranslation.from_dict(data)

        assert translation.initial_translation == "Test translation"
        assert translation.tokens_used == 100
        assert translation.timestamp == datetime.fromisoformat("2024-01-01T12:00:00")


class TestEditorReview:
    """Test cases for EditorReview model."""

    def test_create_valid_editor_review(self):
        """Test creating a valid EditorReview."""
        review = EditorReview(
            editor_suggestions="1. Improve rhythm\n2. Use more poetic language",
            model_info={"provider": "deepseek", "model": "deepseek-chat"},
            tokens_used=150,
        )

        assert "Improve rhythm" in review.editor_suggestions
        assert review.model_info["provider"] == "deepseek"
        assert review.tokens_used == 150
        assert isinstance(review.timestamp, datetime)

    def test_get_suggestions_list(self):
        """Test extracting numbered suggestions from editor text."""
        review = EditorReview(
            editor_suggestions="1. Improve rhythm\n2. Use more poetic language\n3. Add cultural context",
            model_info={"provider": "test"},
            tokens_used=100,
        )

        suggestions = review.get_suggestions_list()

        assert len(suggestions) == 3
        assert suggestions[0] == "Improve rhythm"
        assert suggestions[1] == "Use more poetic language"
        assert suggestions[2] == "Add cultural context"

    def test_get_overall_assessment(self):
        """Test extracting overall assessment from editor text."""
        review = EditorReview(
            editor_suggestions="1. Improve rhythm\n2. Use poetic language\nOverall assessment: Good translation needs refinement",
            model_info={"provider": "test"},
            tokens_used=100,
        )

        assessment = review.get_overall_assessment()

        assert assessment == "Good translation needs refinement"

    def test_to_dict_method(self):
        """Test conversion to dictionary with computed fields."""
        review = EditorReview(
            editor_suggestions="1. Improve rhythm\n2. Use poetic language",
            model_info={"provider": "test"},
            tokens_used=100,
        )

        result = review.to_dict()

        assert (
            result["editor_suggestions"] == "1. Improve rhythm\n2. Use poetic language"
        )
        assert result["tokens_used"] == 100
        # suggestions array and overall_assessment are no longer generated
        assert "suggestions" not in result
        assert "overall_assessment" not in result

    def test_from_dict_method(self):
        """Test creation from dictionary with computed fields."""
        data = {
            "editor_suggestions": "1. Improve rhythm\n2. Use poetic language",
            "model_info": {"provider": "test"},
            "tokens_used": 100,
            "timestamp": "2024-01-01T12:00:00",
        }

        review = EditorReview.from_dict(data)

        assert review.editor_suggestions == "1. Improve rhythm\n2. Use poetic language"
        assert review.tokens_used == 100
        # Computed fields should not be stored in the model
        assert not hasattr(review, "suggestions")


class TestRevisedTranslation:
    """Test cases for RevisedTranslation model."""

    def test_create_valid_revised_translation(self):
        """Test creating a valid RevisedTranslation."""
        translation = RevisedTranslation(
            revised_translation="雾来了，踏着猫儿轻盈的脚步。",
            revised_translation_notes="Improved rhythm and poetic language based on editor suggestions.",
            model_info={"provider": "tongyi", "model": "qwen-max"},
            tokens_used=300,
        )

        assert translation.revised_translation == "雾来了，踏着猫儿轻盈的脚步。"
        assert "Improved rhythm" in translation.revised_translation_notes
        assert translation.model_info["provider"] == "tongyi"
        assert translation.tokens_used == 300

    def test_to_dict_method(self):
        """Test conversion to dictionary."""
        translation = RevisedTranslation(
            revised_translation="Test translation",
            revised_translation_notes="Test notes",
            model_info={"provider": "test"},
            tokens_used=200,
        )

        result = translation.to_dict()

        assert result["revised_translation"] == "Test translation"
        assert result["revised_translation_notes"] == "Test notes"
        assert result["tokens_used"] == 200
        assert "timestamp" in result


class TestTranslationOutput:
    """Test cases for TranslationOutput model."""

    def test_create_valid_translation_output(self, sample_translation_output):
        """Test creating a valid TranslationOutput."""
        output = sample_translation_output

        assert output.workflow_id == "test-workflow-123"
        assert output.original_poem == "The fog comes on little cat feet."
        assert output.source_lang == "English"
        assert output.target_lang == "Chinese"
        assert output.total_tokens == 1250
        assert output.duration_seconds == 15.5

    def test_get_congregated_output(self, sample_translation_output):
        """Test generating congregated output format."""
        output = sample_translation_output
        congregated = output.get_congregated_output()

        assert congregated["original_poem"] == "The fog comes on little cat feet."
        assert congregated["initial_translation"] == "雾来了，踏着猫的细步。"
        assert congregated["revised_translation"] == "雾来了，踏着猫儿轻盈的脚步。"
        assert "editor_suggestions" in congregated
        assert "initial_translation_notes" in congregated
        assert "revised_translation_notes" in congregated

    def test_to_dict_method(self, sample_translation_output):
        """Test conversion to dictionary."""
        output = sample_translation_output
        result = output.to_dict()

        assert result["workflow_id"] == "test-workflow-123"
        assert result["total_tokens"] == 1250
        assert result["duration_seconds"] == 15.5
        assert "congregated_output" in result
        assert "input" in result
        assert "initial_translation" in result
        assert "editor_review" in result
        assert "revised_translation" in result

    def test_from_dict_method(self, sample_translation_output):
        """Test creation from dictionary."""
        data = sample_translation_output.to_dict()
        output = TranslationOutput.from_dict(data)

        assert output.workflow_id == "test-workflow-123"
        assert output.total_tokens == 1250
        assert output.duration_seconds == 15.5

    def test_save_and_load_from_file(self, sample_translation_output, temp_output_dir):
        """Test saving and loading from file."""
        file_path = temp_output_dir / "test_output.json"

        # Save to file
        sample_translation_output.save_to_file(str(file_path))

        # Load from file
        loaded_output = TranslationOutput.load_from_file(str(file_path))

        assert loaded_output.workflow_id == sample_translation_output.workflow_id
        assert loaded_output.total_tokens == sample_translation_output.total_tokens
        assert (
            loaded_output.duration_seconds == sample_translation_output.duration_seconds
        )


class TestConfigModels:
    """Test cases for configuration models."""

    def test_step_config_creation(self):
        """Test creating StepConfig."""
        step = StepConfig(
            name="initial_translation",
            provider="tongyi",
            model="qwen-max",
            temperature=0.7,
            max_tokens=1000,
            prompt_template="test_template.yaml",
        )

        assert step.name == "initial_translation"
        assert step.provider == "tongyi"
        assert step.model == "qwen-max"
        assert step.temperature == 0.7
        assert step.max_tokens == 1000

    def test_workflow_config_creation(self):
        """Test creating WorkflowConfig."""
        workflow = WorkflowConfig(
            name="test_workflow",
            version="1.0.0",
            steps=[
                StepConfig(
                    name="step1",
                    provider="tongyi",
                    model="qwen-max",
                    temperature=0.7,
                    max_tokens=1000,
                )
            ],
        )

        assert workflow.name == "test_workflow"
        assert workflow.version == "1.0.0"
        assert len(workflow.steps) == 1
        assert workflow.steps[0].name == "step1"

    def test_logging_config_creation(self):
        """Test creating LoggingConfig."""
        logging_config = LoggingConfig(
            level="INFO",
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            file="logs/test.log",
            max_file_size=10485760,
            backup_count=5,
        )

        assert logging_config.level == "INFO"
        assert logging_config.file == "logs/test.log"
        assert logging_config.max_file_size == 10485760
        assert logging_config.backup_count == 5

    def test_provider_config_creation(self):
        """Test creating ModelProviderConfig."""
        provider = ModelProviderConfig(
            api_key_env="TEST_API_KEY",
            base_url="https://api.example.com",
            type="openai_compatible",
            models=["gpt-3.5-turbo", "gpt-4"],
            default_model="gpt-3.5-turbo",
        )

        assert provider.api_key_env == "TEST_API_KEY"
        assert provider.base_url == "https://api.example.com"
        assert provider.type == "openai_compatible"
        assert provider.models == ["gpt-3.5-turbo", "gpt-4"]
        assert provider.default_model == "gpt-3.5-turbo"

    def test_complete_config_creation(self, sample_config):
        """Test creating CompleteConfig."""
        config = sample_config

        assert config.main.workflow.name == "test_workflow"
        assert config.main.workflow.version == "1.0.0"
        assert len(config.main.workflow.steps) == 3
        assert "tongyi" in config.providers.providers
        assert "deepseek" in config.providers.providers


class TestHelperFunctions:
    """Test cases for helper functions."""

    def test_extract_initial_translation_from_xml(self, mock_llm_response_valid_xml):
        """Test XML extraction helper function."""
        result = OutputParser.parse_initial_translation_xml(mock_llm_response_valid_xml)

        assert "initial_translation" in result
        assert "initial_translation_notes" in result
        assert "translated_poem_title" in result
        assert "translated_poet_name" in result
        assert result["initial_translation"] == "雾来了，踏着猫的细步。"
        assert result["translated_poem_title"] == "雾"
        assert result["translated_poet_name"] == "卡尔·桑德堡"

    def test_extract_revised_translation_from_xml(
        self, mock_llm_response_revised_translation
    ):
        """Test revised translation XML extraction helper function."""
        result = OutputParser.parse_revised_translation_xml(
            mock_llm_response_revised_translation
        )

        assert "revised_translation" in result
        assert "revised_translation_notes" in result
        assert "refined_translated_poem_title" in result
        assert "refined_translated_poet_name" in result
        assert result["revised_translation"] == "雾来了，踏着猫儿轻盈的脚步。"
        assert result["refined_translated_poem_title"] == "雾"
        assert result["refined_translated_poet_name"] == "卡尔·桑德堡"

    def test_extract_functions_with_invalid_xml(self):
        """Test extraction functions with invalid XML."""
        from src.vpsweb.services.parser import XMLParsingError

        invalid_xml = "This is not valid XML"

        # Should raise XMLParsingError for invalid XML
        with pytest.raises(XMLParsingError):
            OutputParser.parse_initial_translation_xml(invalid_xml)
        with pytest.raises(XMLParsingError):
            OutputParser.parse_revised_translation_xml(invalid_xml)


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_round_trip_serialization(self):
        """Test round-trip serialization of TranslationInput."""
        original = TranslationInput(
            original_poem="Test poem",
            source_lang=Language.ENGLISH,
            target_lang=Language.CHINESE,
            metadata={"author": "Test Author"},
        )

        # Convert to dict
        data = original.to_dict()

        # Convert back to model
        restored = TranslationInput.from_dict(data)

        assert restored.original_poem == original.original_poem
        assert restored.source_lang == original.source_lang
        assert restored.target_lang == original.target_lang
        assert restored.metadata == original.metadata

    def test_json_compatibility(self):
        """Test that models can be serialized to JSON."""
        import json

        input_data = TranslationInput(
            original_poem="Test poem",
            source_lang=Language.ENGLISH,
            target_lang=Language.CHINESE,
        )

        # Should serialize without errors
        json_str = json.dumps(input_data.to_dict())
        assert "Test poem" in json_str
        assert "English" in json_str
        assert "Chinese" in json_str

    def test_complete_workflow_serialization(self, sample_translation_output):
        """Test serialization of complete workflow output."""
        import json

        # Convert to dict
        data = sample_translation_output.to_dict()

        # Should serialize to JSON
        json_str = json.dumps(data, ensure_ascii=False)

        # Should contain all expected fields
        assert "workflow_id" in json_str
        assert "initial_translation" in json_str
        assert "revised_translation" in json_str
        assert "editor_review" in json_str
        assert "congregated_output" in json_str

        # Should be able to deserialize
        loaded_data = json.loads(json_str)
        restored_output = TranslationOutput.from_dict(loaded_data)

        assert restored_output.workflow_id == sample_translation_output.workflow_id
        assert restored_output.total_tokens == sample_translation_output.total_tokens
