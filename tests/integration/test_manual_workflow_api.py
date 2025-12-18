"""
Integration tests for Manual Workflow API endpoints.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient


class TestManualWorkflowAPI:
    """Test suite for manual workflow API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        from vpsweb.webui.main import create_app

        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def sample_poem(self):
        """Create a sample poem for testing."""
        return {
            "id": "test-poem-id",
            "poem_title": "Test Poem",
            "poet_name": "Test Poet",
            "original_text": "Test poem content for translation",
            "source_language": "English",
            "created_at": "2024-01-01T00:00:00Z",
        }

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = Mock()
        session.query.return_value.filter.return_value.first.return_value = None
        return session

    def test_start_manual_workflow_success(self, client, sample_poem, mock_db_session):
        """Test successful manual workflow start."""
        with patch("vpsweb.webui.api.manual_workflow.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db_session

            with patch(
                "vpsweb.webui.api.manual_workflow.ManualWorkflowService"
            ) as mock_service_class:
                # Setup mock service
                mock_service = Mock()
                mock_service.start_session = Mock(
                    return_value=Mock(
                        session_id="test-session-id",
                        step_name="initial_translation_nonreasoning",
                        step_index=0,
                        total_steps=3,
                        prompt="Test prompt content",
                        poem_title="Test Poem",
                        poet_name="Test Poet",
                    )
                )
                mock_service_class.return_value = mock_service

                # Mock repository service to return poem
                mock_repo = Mock()
                mock_repo.poems.get_by_id.return_value = sample_poem

                # Execute request
                response = client.post(
                    "/api/v1/poems/test-poem-id/translate/manual/start",
                    json={"target_lang": "Chinese"},
                )

                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                assert data["data"]["session_id"] == "test-session-id"
                assert data["data"]["step_name"] == "initial_translation_nonreasoning"

    def test_start_manual_workflow_missing_target_lang(self, client, mock_db_session):
        """Test manual workflow start with missing target language."""
        with patch("vpsweb.webui.api.manual_workflow.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db_session

            # Execute request
            response = client.post(
                "/api/v1/poems/test-poem-id/translate/manual/start", json={}
            )

            # Verify response - should fail validation
            assert response.status_code == 422  # Validation error

    def test_start_manual_workflow_poem_not_found(self, client, mock_db_session):
        """Test manual workflow start with non-existent poem."""
        with patch("vpsweb.webui.api.manual_workflow.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db_session

            with patch(
                "vpsweb.webui.api.manual_workflow.ManualWorkflowService"
            ) as mock_service_class:
                # Setup mock service to raise error
                mock_service = Mock()
                mock_service.start_session = Mock(
                    side_effect=ValueError("Poem not found")
                )
                mock_service_class.return_value = mock_service

                # Execute request
                response = client.post(
                    "/api/v1/poems/non-existent-poem/translate/manual/start",
                    json={"target_lang": "Chinese"},
                )

                # Verify response
                assert response.status_code == 400
                data = response.json()
                assert "Poem not found" in data["detail"]

    def test_submit_manual_step_success(self, client, mock_db_session):
        """Test successful manual workflow step submission."""
        with patch("vpsweb.webui.api.manual_workflow.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db_session

            with patch(
                "vpsweb.webui.api.manual_workflow.ManualWorkflowService"
            ) as mock_service_class:
                # Setup mock service
                mock_service = Mock()
                mock_service.submit_step = Mock(
                    return_value={
                        "status": "continue",
                        "step_name": "editor_review_nonreasoning",
                        "step_index": 1,
                        "total_steps": 3,
                        "prompt": "Next step prompt",
                    }
                )
                mock_service_class.return_value = mock_service

                # Execute request
                response = client.post(
                    "/api/v1/poems/test-poem-id/translate/manual/step/initial_translation_nonreasoning",
                    json={
                        "session_id": "test-session-id",
                        "llm_response": "<translation>Test translation</translation>",
                        "llm_model_name": "GPT-4",
                    },
                )

                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["status"] == "continue"
                assert data["data"]["step_name"] == "editor_review_nonreasoning"

    def test_submit_manual_step_final_step(self, client, mock_db_session):
        """Test submission of final workflow step."""
        with patch("vpsweb.webui.api.manual_workflow.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db_session

            with patch(
                "vpsweb.webui.api.manual_workflow.ManualWorkflowService"
            ) as mock_service_class:
                # Setup mock service
                mock_service = Mock()
                mock_service.submit_step = Mock(
                    return_value={
                        "status": "completed",
                        "message": "Manual workflow completed successfully",
                    }
                )
                mock_service_class.return_value = mock_service

                # Execute request
                response = client.post(
                    "/api/v1/poems/test-poem-id/translate/manual/step/translator_revision_nonreasoning",
                    json={
                        "session_id": "test-session-id",
                        "llm_response": "<translation>Final translation</translation>",
                        "llm_model_name": "GPT-4",
                    },
                )

                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["status"] == "completed"

    def test_submit_manual_step_session_not_found(self, client, mock_db_session):
        """Test step submission with invalid session."""
        with patch("vpsweb.webui.api.manual_workflow.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db_session

            with patch(
                "vpsweb.webui.api.manual_workflow.ManualWorkflowService"
            ) as mock_service_class:
                # Setup mock service
                mock_service = Mock()
                mock_service.submit_step = Mock(
                    side_effect=ValueError("Session not found")
                )
                mock_service_class.return_value = mock_service

                # Execute request
                response = client.post(
                    "/api/v1/poems/test-poem-id/translate/manual/step/initial_translation_nonreasoning",
                    json={
                        "session_id": "invalid-session-id",
                        "llm_response": "Test response",
                        "llm_model_name": "GPT-4",
                    },
                )

                # Verify response
                assert response.status_code == 400
                data = response.json()
                assert "Session not found" in data["detail"]

    def test_get_manual_workflow_session(self, client, mock_db_session):
        """Test getting manual workflow session state."""
        with patch("vpsweb.webui.api.manual_workflow.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db_session

            with patch(
                "vpsweb.webui.api.manual_workflow.ManualWorkflowService"
            ) as mock_service_class:
                # Setup mock service
                mock_service = Mock()
                mock_service.get_session = Mock(
                    return_value={
                        "session_id": "test-session-id",
                        "poem_id": "test-poem-id",
                        "current_step_index": 1,
                        "completed_steps": {
                            "initial_translation_nonreasoning": {
                                "model_name": "GPT-4",
                                "timestamp": "2024-01-01T00:00:00Z",
                            }
                        },
                    }
                )
                mock_service_class.return_value = mock_service

                # Execute request
                response = client.get(
                    "/api/v1/poems/test-poem-id/translate/manual/session/test-session-id"
                )

                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["session_id"] == "test-session-id"
                assert data["data"]["poem_id"] == "test-poem-id"

    def test_get_manual_workflow_session_not_found(self, client, mock_db_session):
        """Test getting non-existent session."""
        with patch("vpsweb.webui.api.manual_workflow.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db_session

            with patch(
                "vpsweb.webui.api.manual_workflow.ManualWorkflowService"
            ) as mock_service_class:
                # Setup mock service
                mock_service = Mock()
                mock_service.get_session = Mock(return_value=None)
                mock_service_class.return_value = mock_service

                # Execute request
                response = client.get(
                    "/api/v1/poems/test-poem-id/translate/manual/session/non-existent-session"
                )

                # Verify response
                assert response.status_code == 404

    def test_get_manual_workflow_session_wrong_poem(self, client, mock_db_session):
        """Test getting session that belongs to different poem."""
        with patch("vpsweb.webui.api.manual_workflow.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db_session

            with patch(
                "vpsweb.webui.api.manual_workflow.ManualWorkflowService"
            ) as mock_service_class:
                # Setup mock service - session belongs to different poem
                mock_service = Mock()
                mock_service.get_session = Mock(
                    return_value={
                        "session_id": "test-session-id",
                        "poem_id": "different-poem-id",
                    }
                )
                mock_service_class.return_value = mock_service

                # Execute request
                response = client.get(
                    "/api/v1/poems/test-poem-id/translate/manual/session/test-session-id"
                )

                # Verify response
                assert response.status_code == 400
                data = response.json()
                assert "does not belong to this poem" in data["detail"]

    def test_cleanup_expired_sessions(self, client, mock_db_session):
        """Test cleaning up expired sessions."""
        with patch("vpsweb.webui.api.manual_workflow.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db_session

            with patch(
                "vpsweb.webui.api.manual_workflow.ManualWorkflowService"
            ) as mock_service_class:
                # Setup mock service
                mock_service = Mock()
                mock_service.cleanup_expired_sessions = Mock(return_value=5)
                mock_service_class.return_value = mock_service

                # Execute request
                response = client.post(
                    "/api/v1/translate/manual/cleanup?max_age_hours=24"
                )

                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["cleaned_count"] == 5

    def test_manual_workflow_step_validation_errors(self, client, mock_db_session):
        """Test validation errors for step submission."""
        with patch("vpsweb.webui.api.manual_workflow.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db_session

            # Test missing session_id
            response = client.post(
                "/api/v1/poems/test-poem-id/translate/manual/step/initial_translation_nonreasoning",
                json={
                    "llm_response": "Test response",
                    "llm_model_name": "GPT-4",
                },
            )
            assert response.status_code == 422  # Validation error

            # Test missing llm_response
            response = client.post(
                "/api/v1/poems/test-poem-id/translate/manual/step/initial_translation_nonreasoning",
                json={
                    "session_id": "test-session-id",
                    "llm_model_name": "GPT-4",
                },
            )
            assert response.status_code == 422  # Validation error

            # Test missing llm_model_name
            response = client.post(
                "/api/v1/poems/test-poem-id/translate/manual/step/initial_translation_nonreasoning",
                json={
                    "session_id": "test-session-id",
                    "llm_response": "Test response",
                },
            )
            assert response.status_code == 422  # Validation error
