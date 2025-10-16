"""
Pytest fixtures for VPSWeb testing.

This module provides common fixtures for unit and integration tests,
including sample data, mock responses, and temporary directories.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

from src.vpsweb.models.translation import (
    TranslationInput,
    InitialTranslation,
    EditorReview,
    RevisedTranslation,
    TranslationOutput,
)
from src.vpsweb.models.config import (
    WorkflowConfig,
    StepConfig,
    CompleteConfig,
    LoggingConfig,
    MainConfig,
    ModelProviderConfig,
    ProvidersConfig,
)


@pytest.fixture
def sample_translation_input():
    """Fixture providing a sample TranslationInput for testing."""
    return TranslationInput(
        original_poem="The fog comes on little cat feet.",
        source_lang="English",
        target_lang="Chinese",
    )


@pytest.fixture
def sample_english_poem():
    """Fixture providing a sample English poem."""
    return """The fog comes
on little cat feet.
It sits looking
over harbor and city
on silent haunches
and then moves on."""


@pytest.fixture
def sample_chinese_poem():
    """Fixture providing a sample Chinese poem."""
    return """雾来了
踏着猫的细步
它静静地蹲伏着
俯视海港和城市
再向前走去"""


@pytest.fixture
def mock_llm_response_valid_xml():
    """Fixture providing a valid XML response from LLM."""
    return """<translation>
<initial_translation>雾来了，踏着猫的细步。</initial_translation>
<explanation>This translation captures the imagery of the fog moving quietly like a cat.</explanation>
</translation>"""


@pytest.fixture
def mock_llm_response_malformed_xml():
    """Fixture providing a malformed XML response from LLM."""
    return """<translation>
<initial_translation>雾来了，踏着猫的细步。</initial_translation>
<explanation>This is missing closing tags"""


@pytest.fixture
def mock_llm_response_missing_tags():
    """Fixture providing XML response with missing required tags."""
    return """<translation>
<explanation>This is missing the initial_translation tag</explanation>
</translation>"""


@pytest.fixture
def mock_llm_response_editor_review():
    """Fixture providing a valid editor review response."""
    return """<editor_review>
<text>1. Consider using more poetic language for "little cat feet"
2. The rhythm could be improved in the second line
3. Add more cultural context for Chinese readers</text>
<summary>Good literal translation but needs poetic refinement</summary>
</editor_review>"""


@pytest.fixture
def mock_llm_response_revised_translation():
    """Fixture providing a valid revised translation response."""
    return """<revised_translation>
<revised_translation>雾来了，踏着猫儿轻盈的脚步。</revised_translation>
<explanation>Added poetic language and improved rhythm while maintaining original meaning.</explanation>
</revised_translation>"""


@pytest.fixture
def temp_output_dir():
    """Fixture providing a temporary directory for output files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_config():
    """Fixture providing a sample CompleteConfig for testing."""
    return CompleteConfig(
        main=MainConfig(
            workflow=WorkflowConfig(
                name="test_workflow",
                version="1.0.0",
                steps=[
                    StepConfig(
                        name="initial_translation",
                        provider="tongyi",
                        model="qwen-max",
                        temperature=0.7,
                        max_tokens=1000,
                        prompt_template="test_template.yaml",
                    ),
                    StepConfig(
                        name="editor_review",
                        provider="deepseek",
                        model="deepseek-chat",
                        temperature=0.5,
                        max_tokens=800,
                        prompt_template="test_template.yaml",
                    ),
                    StepConfig(
                        name="translator_revision",
                        provider="tongyi",
                        model="qwen-max",
                        temperature=0.6,
                        max_tokens=1000,
                        prompt_template="test_template.yaml",
                    ),
                ],
            ),
            storage=MainConfig.StorageConfig(output_dir="./output"),
            logging=LoggingConfig(
                level="INFO",
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                file="logs/vpsweb.log",
                max_file_size=10485760,
                backup_count=5,
            ),
        ),
        providers=ProvidersConfig(
            providers={
                "tongyi": ModelProviderConfig(
                    api_key_env="TONGYI_API_KEY",
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    type="openai_compatible",
                    models=["qwen-max", "qwen-plus"],
                    default_model="qwen-max",
                ),
                "deepseek": ModelProviderConfig(
                    api_key_env="DEEPSEEK_API_KEY",
                    base_url="https://api.deepseek.com",
                    type="openai_compatible",
                    models=["deepseek-reasoner", "deepseek-chat"],
                    default_model="deepseek-reasoner",
                ),
            }
        ),
    )


@pytest.fixture
def sample_workflow_config():
    """Fixture providing a sample WorkflowConfig for testing."""
    return WorkflowConfig(
        name="test_workflow",
        version="1.0.0",
        steps=[
            StepConfig(
                name="initial_translation",
                provider="tongyi",
                model="qwen-max",
                temperature=0.7,
                max_tokens=1000,
            ),
            StepConfig(
                name="editor_review",
                provider="deepseek",
                model="deepseek-chat",
                temperature=0.5,
                max_tokens=800,
            ),
            StepConfig(
                name="translator_revision",
                provider="tongyi",
                model="qwen-max",
                temperature=0.6,
                max_tokens=1000,
            ),
        ],
    )


@pytest.fixture
def sample_translation_output():
    """Fixture providing a sample TranslationOutput for testing."""
    return TranslationOutput(
        workflow_id="test-workflow-123",
        original_poem="The fog comes on little cat feet.",
        source_lang="English",
        target_lang="Chinese",
        initial_translation=InitialTranslation(
            initial_translation="雾来了，踏着猫的细步。",
            explanation="Literal translation capturing the imagery",
        ),
        editor_review=EditorReview(
            text="1. Consider using more poetic language\n2. Improve rhythm",
            summary="Good literal translation but needs refinement",
        ),
        revised_translation=RevisedTranslation(
            revised_translation="雾来了，踏着猫儿轻盈的脚步。",
            explanation="Added poetic language and improved rhythm",
        ),
        duration_seconds=15.5,
        total_tokens=1250,
    )


@pytest.fixture
def mock_async_function():
    """Fixture providing a mock async function for testing."""

    async def mock_async_func(*args, **kwargs):
        return {"result": "mock_response"}

    return mock_async_func


@pytest.fixture
def mock_llm_factory():
    """Fixture providing a mock LLM factory for testing."""

    class MockLLM:
        async def generate(self, prompt: str, **kwargs):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "<translation><initial_translation>Mock translation</initial_translation></translation>"
                        }
                    }
                ]
            }

    class MockLLMFactory:
        def create_llm(self, provider: str, model: str, **kwargs):
            return MockLLM()

    return MockLLMFactory()


# Fixture for async event loop
@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Integration test fixtures
@pytest.fixture
def mock_llm_response_initial_translation():
    """Mock LLM response for initial translation step."""
    return {
        "choices": [
            {
                "message": {
                    "content": """<initial_translation>雾来了，踏着猫的细步。</initial_translation>
<initial_translation_notes>This translation captures the gentle imagery of the fog moving quietly like a cat. The phrase "little cat feet" is translated to convey the delicate, stealthy movement in Chinese poetic context.</initial_translation_notes>"""
                }
            }
        ]
    }


@pytest.fixture
def mock_llm_response_editor_review():
    """Mock LLM response for editor review step."""
    return {
        "choices": [
            {
                "message": {
                    "content": """1. Consider using more poetic language for "little cat feet" - perhaps "猫儿轻盈的脚步"
2. The rhythm could be improved in the second line
3. Add more cultural context for Chinese readers

Overall assessment: Good literal translation but needs poetic refinement to capture the original's musical quality."""
                }
            }
        ]
    }


@pytest.fixture
def mock_llm_response_revised_translation():
    """Mock LLM response for translator revision step."""
    return {
        "choices": [
            {
                "message": {
                    "content": """<revised_translation>雾来了，踏着猫儿轻盈的脚步。</revised_translation>
<revised_translation_notes>Based on the editor's suggestions, I refined the translation to use more poetic language. Changed "猫的细步" to "猫儿轻盈的脚步" to better capture the gentle, graceful movement. The revised version maintains the original meaning while enhancing the poetic quality and rhythm.</revised_translation_notes>"""
                }
            }
        ]
    }


@pytest.fixture
def mock_llm_factory_integration(mocker):
    """Mock LLM factory for integration tests."""
    from src.vpsweb.services.llm.factory import LLMFactory

    class MockLLM:
        def __init__(self, responses):
            self.responses = responses
            self.call_count = 0

        async def generate(self, prompt: str, **kwargs):
            response = self.responses[self.call_count % len(self.responses)]
            self.call_count += 1
            return response

    # Create mock that returns our mock LLM
    original_create = LLMFactory.create_llm

    def mock_create_llm(self, provider: str, model: str, **kwargs):
        responses = [
            mock_llm_response_initial_translation(),
            mock_llm_response_editor_review(),
            mock_llm_response_revised_translation(),
        ]
        return MockLLM(responses)

    mocker.patch.object(LLMFactory, "create_llm", mock_create_llm)
    return LLMFactory()


@pytest.fixture
def sample_poem_file(temp_output_dir):
    """Create a temporary poem file for CLI testing."""
    poem_file = temp_output_dir / "test_poem.txt"
    poem_file.write_text("The fog comes on little cat feet.")
    return poem_file


@pytest.fixture
def cli_runner():
    """Provide Click CLI runner for testing."""
    from click.testing import CliRunner

    return CliRunner()


@pytest.fixture
def integration_workflow_config():
    """Workflow configuration for integration tests."""
    return WorkflowConfig(
        name="integration_test_workflow",
        version="1.0.0",
        steps=[
            StepConfig(
                name="initial_translation",
                provider="tongyi",
                model="qwen-max",
                temperature=0.7,
                max_tokens=1000,
            ),
            StepConfig(
                name="editor_review",
                provider="deepseek",
                model="deepseek-chat",
                temperature=0.5,
                max_tokens=800,
            ),
            StepConfig(
                name="translator_revision",
                provider="tongyi",
                model="qwen-max",
                temperature=0.6,
                max_tokens=1000,
            ),
        ],
    )
