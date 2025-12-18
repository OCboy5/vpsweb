"""
Unit tests for ManualWorkflowService.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from vpsweb.services.parser import OutputParser
from vpsweb.webui.services.manual_workflow_service import ManualWorkflowService


class TestManualWorkflowService:
    """Test suite for ManualWorkflowService."""

    @pytest.fixture
    def mock_prompt_service(self):
        """Create a mock prompt service."""
        service = Mock()
        service.render_prompt = Mock(
            return_value=("system prompt", "user prompt with {poem_title}")
        )
        return service

    @pytest.fixture
    def mock_output_parser(self):
        """Create a mock output parser."""
        parser = Mock(spec=OutputParser)
        parser.parse_xml = Mock(
            return_value={
                "translated_poem_title": "Test Title",
                "translated_poem": "Test translation",
                "translation_notes": "Test notes",
            }
        )
        return parser

    @pytest.fixture
    def mock_workflow_service(self):
        """Create a mock workflow service."""
        service = Mock()
        service._persist_workflow_result = AsyncMock()
        return service

    @pytest.fixture
    def mock_repository_service(self):
        """Create a mock repository service."""
        service = Mock()
        service.repo.poems.get_by_id = Mock()
        return service

    @pytest.fixture
    def mock_storage_handler(self):
        """Create a mock storage handler."""
        return Mock()

    @pytest.fixture
    def manual_workflow_service(
        self,
        mock_prompt_service,
        mock_output_parser,
        mock_workflow_service,
        mock_repository_service,
        mock_storage_handler,
    ):
        """Create a ManualWorkflowService instance with mocked dependencies."""
        return ManualWorkflowService(
            prompt_service=mock_prompt_service,
            output_parser=mock_output_parser,
            workflow_service=mock_workflow_service,
            repository_service=mock_repository_service,
            storage_handler=mock_storage_handler,
        )

    @pytest.fixture
    def sample_poem(self):
        """Create a sample poem object."""
        poem = Mock()
        poem.id = "test-poem-id"
        poem.poem_title = "Test Poem"
        poem.poet_name = "Test Poet"
        poem.original_text = "Test poem content"
        poem.source_language = "English"
        return poem

    @pytest.mark.asyncio
    async def test_start_session_success(
        self, manual_workflow_service, mock_repository_service, sample_poem
    ):
        """Test successful session start."""
        # Setup mock
        mock_repository_service.repo.poems.get_by_id.return_value = sample_poem
        manual_workflow_service.prompt_service.render_prompt.return_value = (
            "System prompt",
            "Test prompt",
        )

        # Execute
        result = await manual_workflow_service.start_session(
            poem_id="test-poem-id", target_lang="Chinese"
        )

        # Verify
        assert result["session_id"] is not None
        assert result["step_name"] == "initial_translation_nonreasoning"
        assert result["step_index"] == 0
        assert result["total_steps"] == 3
        assert (
            "=== SYSTEM PROMPT ===\nSystem prompt\n\n=== USER PROMPT ===\n"
            "Test prompt" == result["prompt"]
        )
        assert result["poem_title"] == "Test Poem"
        assert result["poet_name"] == "Test Poet"

        # Verify session is stored
        session_id = result["session_id"]
        assert session_id in manual_workflow_service.sessions
        session = manual_workflow_service.sessions[session_id]
        assert session["poem_id"] == "test-poem-id"
        assert session["target_lang"] == "Chinese"
        assert session["current_step_index"] == 0

    @pytest.mark.asyncio
    async def test_start_session_poem_not_found(
        self, manual_workflow_service, mock_repository_service
    ):
        """Test session start with non-existent poem."""
        # Setup mock
        mock_repository_service.repo.poems.get_by_id.return_value = None

        # Execute and verify
        with pytest.raises(ValueError, match="Poem not found: test-poem-id"):
            await manual_workflow_service.start_session(
                poem_id="test-poem-id", target_lang="Chinese"
            )

    @pytest.mark.asyncio
    async def test_submit_step_success(self, manual_workflow_service, sample_poem):
        """Test successful step submission."""
        # Setup session
        manual_workflow_service.sessions["test-session"] = {
            "session_id": "test-session",
            "poem_id": "test-poem-id",
            "source_lang": "English",
            "target_lang": "Chinese",
            "current_step_index": 0,
            "step_sequence": [
                "initial_translation_nonreasoning",
                "editor_review_reasoning",
                "translator_revision_nonreasoning",
            ],
            "completed_steps": {},
            "created_at": datetime.now(timezone.utc),
        }

        # Setup mocks
        manual_workflow_service.repository_service.repo.poems.get_by_id.return_value = (
            sample_poem
        )
        manual_workflow_service.prompt_service.render_prompt.return_value = (
            "System prompt",
            "Next prompt",
        )

        # Execute
        result = await manual_workflow_service.submit_step(
            session_id="test-session",
            step_name="initial_translation_nonreasoning",
            llm_response="<response>Test translation</response>",
            model_name="GPT-4",
        )

        # Verify
        assert result["status"] == "continue"
        assert result["step_name"] == "editor_review_reasoning"
        assert result["step_index"] == 1
        assert (
            "=== SYSTEM PROMPT ===\nSystem prompt\n\n=== USER PROMPT ===\nNext prompt"
            == result["prompt"]
        )

        # Verify step was stored
        session = manual_workflow_service.sessions["test-session"]
        assert "initial_translation_nonreasoning" in session["completed_steps"]
        step = session["completed_steps"]["initial_translation_nonreasoning"]
        assert step["model_name"] == "GPT-4"
        assert step["llm_response"] == "<response>Test translation</response>"

    @pytest.mark.asyncio
    async def test_submit_step_last_step(self, manual_workflow_service, sample_poem):
        """Test successful submission of final step."""
        # Setup session with last step
        manual_workflow_service.sessions["test-session"] = {
            "session_id": "test-session",
            "poem_id": "test-poem-id",
            "source_lang": "English",
            "target_lang": "Chinese",
            "current_step_index": 2,  # Last step
            "step_sequence": [
                "initial_translation_nonreasoning",
                "editor_review_reasoning",
                "translator_revision_nonreasoning",
            ],
            "completed_steps": {
                "initial_translation_nonreasoning": {
                    "model_name": "GPT-4",
                    "parsed_data": {"translation": "Step 1"},
                },
                "editor_review_reasoning": {
                    "model_name": "GPT-4",
                    "parsed_data": {"review": "Step 2"},
                },
            },
            "created_at": datetime.now(timezone.utc),
        }

        # Setup mocks
        manual_workflow_service.repository_service.repo.poems.get_by_id.return_value = (
            sample_poem
        )

        # Execute
        result = await manual_workflow_service.submit_step(
            session_id="test-session",
            step_name="translator_revision_nonreasoning",
            llm_response="<response>Final translation</response>",
            model_name="GPT-4",
        )

        # Verify
        assert result["status"] == "completed"
        assert result["message"] == "Manual workflow completed successfully"

        # Verify session was cleaned up
        assert "test-session" not in manual_workflow_service.sessions

        # Verify _complete_workflow was called
        manual_workflow_service.workflow_service._persist_workflow_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_step_session_not_found(self, manual_workflow_service):
        """Test step submission with non-existent session."""
        # Execute and verify
        with pytest.raises(ValueError, match="Session not found: test-session"):
            await manual_workflow_service.submit_step(
                session_id="test-session",
                step_name="initial_translation_nonreasoning",
                llm_response="Test response",
                model_name="GPT-4",
            )

    @pytest.mark.asyncio
    async def test_submit_step_wrong_step(self, manual_workflow_service):
        """Test step submission with wrong step name."""
        # Setup session
        manual_workflow_service.sessions["test-session"] = {
            "session_id": "test-session",
            "current_step_index": 0,
            "step_sequence": ["initial_translation_nonreasoning"],
            "completed_steps": {},
        }

        # Execute and verify
        with pytest.raises(
            ValueError,
            match="Step mismatch: expected initial_translation_nonreasoning, got wrong_step",
        ):
            await manual_workflow_service.submit_step(
                session_id="test-session",
                step_name="wrong_step",
                llm_response="Test response",
                model_name="GPT-4",
            )

    @pytest.mark.asyncio
    async def test_submit_step_invalid_xml(self, manual_workflow_service):
        """Test step submission with invalid XML response."""
        # Setup session
        manual_workflow_service.sessions["test-session"] = {
            "session_id": "test-session",
            "current_step_index": 0,
            "step_sequence": ["initial_translation_nonreasoning"],
            "completed_steps": {},
        }

        # Setup mock to raise error
        manual_workflow_service.output_parser.parse_xml.side_effect = Exception(
            "Invalid XML"
        )

        # Execute and verify
        with pytest.raises(
            ValueError, match="Failed to parse LLM response: Invalid XML"
        ):
            await manual_workflow_service.submit_step(
                session_id="test-session",
                step_name="initial_translation_nonreasoning",
                llm_response="Invalid XML response",
                model_name="GPT-4",
            )

    @pytest.mark.asyncio
    async def test_get_session(self, manual_workflow_service):
        """Test getting session state."""
        # Setup session
        session_data = {"test": "session"}
        manual_workflow_service.sessions["test-session"] = session_data

        # Execute
        result = await manual_workflow_service.get_session("test-session")

        # Verify
        assert result == session_data

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, manual_workflow_service):
        """Test getting non-existent session."""
        # Execute
        result = await manual_workflow_service.get_session("test-session")

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_get_step_prompt(self, manual_workflow_service, sample_poem):
        """Test getting step prompt."""
        # Execute
        prompt = await manual_workflow_service._get_step_prompt(
            step_name="initial_translation_nonreasoning",
            poem=sample_poem,
            source_lang="English",
            target_lang="Chinese",
            previous_results=None,
        )

        # Verify
        assert prompt is not None
        manual_workflow_service.prompt_service.render_prompt.assert_called_once_with(
            "initial_translation_nonreasoning",
            {
                "poem_title": "Test Poem",
                "poet_name": "Test Poet",
                "original_poem": "Test poem content",
                "source_lang": "English",
                "target_lang": "Chinese",
                "source_language": "English",
                "target_language": "Chinese",
                "adaptation_level": "medium",
                "additions_policy": "minimal",
                "background_briefing_report": "",
                "prosody_target": "preserve_rhythm_and_meter",
                "repetition_policy": "preserve_meaningful_repetition",
                "current_step": "Initial Translation Nonreasoning",
            },
        )

    @pytest.mark.asyncio
    async def test_get_step_prompt_with_previous_results(
        self, manual_workflow_service, sample_poem
    ):
        """Test getting step prompt with previous results."""
        # Setup previous results
        previous_results = {
            "initial_translation_nonreasoning": {
                "initial_translation": "Test translation",
                "initial_translation_notes": "Test notes",
                "translated_poem_title": "Test Title",
                "translated_poet_name": "Test Poet",
            },
            "editor_review_reasoning": {
                "editor_suggestions": "Test review",
            },
        }

        # Execute
        prompt = await manual_workflow_service._get_step_prompt(
            step_name="translator_revision_nonreasoning",
            poem=sample_poem,
            source_lang="English",
            target_lang="Chinese",
            previous_results=previous_results,
        )

        # Verify
        assert prompt is not None
        manual_workflow_service.prompt_service.render_prompt.assert_called_once()
        call_args = manual_workflow_service.prompt_service.render_prompt.call_args
        assert call_args[0][0] == "translator_revision_nonreasoning"
        template_vars = call_args[0][1]
        assert "initial_translation" in template_vars
        assert "editor_suggestions" in template_vars

    def test_cleanup_expired_sessions(self, manual_workflow_service):
        """Test cleaning up expired sessions."""
        # Setup sessions - one recent, one old
        now = datetime.now(timezone.utc)
        old_time = now.replace(year=now.year - 1)  # 1 year ago

        manual_workflow_service.sessions["recent"] = {
            "created_at": now,
        }
        manual_workflow_service.sessions["old"] = {
            "created_at": old_time,
        }

        # Execute
        cleaned_count = manual_workflow_service.cleanup_expired_sessions(
            max_age_hours=1
        )

        # Verify
        assert cleaned_count == 1
        assert "recent" in manual_workflow_service.sessions
        assert "old" not in manual_workflow_service.sessions
