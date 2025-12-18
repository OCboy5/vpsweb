"""
Basic API Endpoint Tests for VPSWeb v0.7.0

Simplified API tests that work with existing test infrastructure.
"""

import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.api
class TestBasicAPIEndpoints:
    """Basic API endpoint tests."""

    def test_health_check(self, test_client: TestClient):
        """Test that the API is responsive."""
        # Test root endpoint or health check
        response = test_client.get("/")
        assert response.status_code in [
            200,
            404,
        ]  # 404 is acceptable if no root endpoint

    def test_list_poems_empty(self, test_client: TestClient):
        """Test GET /api/v1/poems/ with empty database."""
        response = test_client.get("/api/v1/poems/")

        assert response.status_code == 200
        data = response.json()
        assert data["poems"] == []
        assert data["pagination"]["total_items"] == 0

    def test_create_poem_success(self, test_client: TestClient):
        """Test POST /api/v1/poems/ with valid data."""
        poem_data = {
            "poet_name": "Emily Dickinson",
            "poem_title": "Hope is the thing with feathers",
            "source_language": "English",
            "original_text": """Hope is the thing with feathers
That perches in the soul,
And sings the tune without the words,
And never stops at all,""",
            "metadata": '{"theme": "hope", "style": "lyrical"}',
        }

        response = test_client.post("/api/v1/poems/", json=poem_data)

        assert response.status_code == 200
        data = response.json()
        assert data["poet_name"] == poem_data["poet_name"]
        assert data["poem_title"] == poem_data["poem_title"]
        assert data["source_language"] == poem_data["source_language"]
        assert data["original_text"] == poem_data["original_text"]

    def test_create_poem_validation_errors(self, test_client: TestClient):
        """Test POST /api/v1/poems/ with invalid data."""
        # Test missing required fields
        invalid_data = {
            "poet_name": "Test Poet"
            # Missing poem_title, source_language, original_text
        }

        response = test_client.post("/api/v1/poems/", json=invalid_data)
        assert response.status_code == 422  # Validation error

        # Test empty content
        invalid_data = {
            "poet_name": "Test Poet",
            "poem_title": "Test Poem",
            "source_language": "English",
            "original_text": "",  # Empty content
        }

        response = test_client.post("/api/v1/poems/", json=invalid_data)
        assert response.status_code == 400  # Business logic error

    def test_get_filter_options(self, test_client: TestClient):
        """Test GET /api/v1/poems/filter-options."""
        response = test_client.get("/api/v1/poems/filter-options")

        assert response.status_code == 200
        data = response.json()
        assert "poets" in data
        assert "languages" in data

    def test_search_poems_by_title(self, test_client: TestClient):
        """Test POST /api/v1/poems/search by title."""
        search_data = {"query": "Test", "search_type": "title"}

        response = test_client.post("/api/v1/poems/search", json=search_data)

        assert response.status_code == 200

    def test_get_statistics_dashboard(self, test_client: TestClient):
        """Test GET /api/v1/statistics/dashboard."""
        response = test_client.get("/api/v1/statistics/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert "total_poems" in data
        assert "total_translations" in data

    def test_translation_trigger_validation(self, test_client: TestClient):
        """Test POST /api/v1/translations/trigger validation."""
        # Test missing required fields
        invalid_request = {
            "target_lang": "Chinese",
            "workflow_mode": "hybrid",
            # Missing poem_id
        }

        response = test_client.post(
            "/api/v1/translations/trigger", json=invalid_request
        )
        assert response.status_code == 422

        # Test invalid workflow mode
        invalid_request = {
            "poem_id": str(uuid.uuid4())[:26],
            "target_lang": "Chinese",
            "workflow_mode": "invalid_mode",
        }

        response = test_client.post(
            "/api/v1/translations/trigger", json=invalid_request
        )
        assert response.status_code == 422

    def test_list_translations_empty(self, test_client: TestClient):
        """Test GET /api/v1/translations/ with empty database."""
        response = test_client.get("/api/v1/translations/")

        assert response.status_code == 200
        data = response.json()
        assert data["translations"] == []
        assert data["pagination"]["total_items"] == 0

    def test_bbr_endpoints_with_fake_poem(self, test_client: TestClient):
        """Test BBR endpoints with non-existent poem."""
        fake_poem_id = str(uuid.uuid4())[:26]

        # Test generate BBR
        response = test_client.post(
            f"/api/v1/poems/{fake_poem_id}/bbr/generate"
        )
        assert response.status_code == 404

        # Test get BBR
        response = test_client.get(f"/api/v1/poems/{fake_poem_id}/bbr")
        assert response.status_code == 404

        # Test delete BBR
        response = test_client.delete(f"/api/v1/poems/{fake_poem_id}/bbr")
        assert response.status_code == 404

    def test_error_handling(self, test_client: TestClient):
        """Test API error handling."""
        # Test 404 for non-existent endpoint
        response = test_client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code == 404

        # Test 404 for non-existent poem
        fake_poem_id = str(uuid.uuid4())[:26]
        response = test_client.get(f"/api/v1/poems/{fake_poem_id}")
        assert response.status_code == 404

        # Test method not allowed
        response = test_client.patch("/api/v1/poems/")
        assert response.status_code == 405
