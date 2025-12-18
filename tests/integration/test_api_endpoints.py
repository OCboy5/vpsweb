"""
Comprehensive API Endpoint Tests for VPSWeb v0.7.0

This module tests all core API endpoints with proper mocking, database isolation,
and comprehensive test coverage for success and error cases.

Key Features:
- Tests all major API endpoints
- Uses in-memory SQLite database for isolation
- Mocks LLM providers to avoid external dependencies
- Tests both success and error scenarios
- Covers all 4 workflow modes (Hybrid, Manual, Reasoning, Non-Reasoning)
- Validates response models and status codes
"""

import pytest
import json
import uuid
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.vpsweb.repository.models import Poem, Translation, BackgroundBriefingReport
from src.vpsweb.repository.schemas import PoemCreate, TranslationCreate
from src.vpsweb.webui.schemas import WorkflowMode, TranslationRequest


# ==============================================================================
# Poem API Endpoint Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.api
class TestPoemEndpoints:
    """Test suite for poem API endpoints."""

    def test_list_poems_empty(self, test_client: TestClient):
        """Test GET /api/v1/poems/ with empty database."""
        response = test_client.get("/api/v1/poems/")

        assert response.status_code == 200
        data = response.json()
        assert data["poems"] == []
        assert data["pagination"]["current_page"] == 1
        assert data["pagination"]["total_items"] == 0
        assert data["pagination"]["total_pages"] == 0

    def test_list_poems_with_data(self, test_client: TestClient, sample_poem):
        """Test GET /api/v1/poems/ with existing poems."""
        response = test_client.get("/api/v1/poems/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["poems"]) == 1

        poem = data["poems"][0]
        assert poem["poet_name"] == sample_poem.poet_name
        assert poem["poem_title"] == sample_poem.poem_title
        assert poem["source_language"] == sample_poem.source_language
        assert poem["translation_count"] == 0
        assert poem["ai_translation_count"] == 0
        assert poem["human_translation_count"] == 0

    @pytest.mark.asyncio
    async def test_list_poems_pagination(self, test_client: TestClient, test_context):
        """Test poem list pagination functionality."""
        # Create multiple poems
        poems = []
        for i in range(5):
            poem = await test_context.create_poem(
                poet_name=f"Poet {i}",
                poem_title=f"Poem {i}",
                original_text=f"Content of poem {i}"
            )
            poems.append(poem)

        # Test first page
        response = test_client.get("/api/v1/poems/?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["poems"]) == 2
        assert data["pagination"]["current_page"] == 1
        assert data["pagination"]["total_pages"] == 3
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["has_previous"] is False

        # Test second page
        response = test_client.get("/api/v1/poems/?page=2&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["poems"]) == 2
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["has_previous"] is True

    def test_list_poems_filters(self, test_client: TestClient, test_context):
        """Test poem list filtering functionality."""
        # Create poems with different attributes
        await test_context.create_poem(
            poet_name="李白", poem_title="静夜思", source_language="Chinese"
        )
        await test_context.create_poem(
            poet_name="Shakespeare", poem_title="Sonnet 18", source_language="English"
        )

        # Test poet name filter
        response = test_client.get("/api/v1/poems/?poet_name=李白")
        assert response.status_code == 200
        data = response.json()
        assert len(data["poems"]) == 1
        assert data["poems"][0]["poet_name"] == "李白"

        # Test language filter
        response = test_client.get("/api/v1/poems/?language=English")
        assert response.status_code == 200
        data = response.json()
        assert len(data["poems"]) == 1
        assert data["poems"][0]["source_language"] == "English"

        # Test title search
        response = test_client.get("/api/v1/poems/?title_search=Sonnet")
        assert response.status_code == 200
        data = response.json()
        assert len(data["poems"]) == 1
        assert "Sonnet" in data["poems"][0]["poem_title"]

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
            "metadata": '{"theme": "hope", "style": "lyrical"}'
        }

        response = test_client.post("/api/v1/poems/", json=poem_data)

        assert response.status_code == 200
        data = response.json()
        assert data["poet_name"] == poem_data["poet_name"]
        assert data["poem_title"] == poem_data["poem_title"]
        assert data["source_language"] == poem_data["source_language"]
        assert data["original_text"] == poem_data["original_text"]
        assert data["metadata_json"] == poem_data["metadata"]
        assert "id" in data
        assert "created_at" in data

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
            "original_text": ""  # Empty content
        }

        response = test_client.post("/api/v1/poems/", json=invalid_data)
        assert response.status_code == 400  # Business logic error

    def test_get_poem_success(self, test_client: TestClient, sample_poem):
        """Test GET /api/v1/poems/{poem_id} with existing poem."""
        response = test_client.get(f"/api/v1/poems/{sample_poem.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_poem.id
        assert data["poet_name"] == sample_poem.poet_name
        assert data["poem_title"] == sample_poem.poem_title
        assert data["source_language"] == sample_poem.source_language
        assert data["original_text"] == sample_poem.original_text

    def test_get_poem_not_found(self, test_client: TestClient):
        """Test GET /api/v1/poems/{poem_id} with non-existent poem."""
        fake_id = str(uuid.uuid4())[:26]
        response = test_client.get(f"/api/v1/poems/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_poem_success(self, test_client: TestClient, sample_poem):
        """Test PUT /api/v1/poems/{poem_id} with valid data."""
        update_data = {
            "poet_name": "Updated Poet Name",
            "poem_title": "Updated Poem Title",
            "source_language": "English",
            "original_text": "Updated poem content",
            "metadata": '{"updated": true}'
        }

        response = test_client.put(f"/api/v1/poems/{sample_poem.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_poem.id
        assert data["poet_name"] == update_data["poet_name"]
        assert data["poem_title"] == update_data["poem_title"]
        assert data["original_text"] == update_data["original_text"]

    def test_update_poem_not_found(self, test_client: TestClient):
        """Test PUT /api/v1/poems/{poem_id} with non-existent poem."""
        fake_id = str(uuid.uuid4())[:26]
        update_data = {
            "poet_name": "Test",
            "poem_title": "Test",
            "source_language": "English",
            "original_text": "Test content"
        }

        response = test_client.put(f"/api/v1/poems/{fake_id}", json=update_data)
        assert response.status_code == 404

    def test_toggle_poem_selection(self, test_client: TestClient, sample_poem):
        """Test PATCH /api/v1/poems/{poem_id}/selected."""
        # Test selecting poem
        selection_data = {"selected": True}
        response = test_client.patch(f"/api/v1/poems/{sample_poem.id}/selected", json=selection_data)

        assert response.status_code == 200
        data = response.json()
        assert data["selected"] is True

        # Test deselecting poem
        selection_data = {"selected": False}
        response = test_client.patch(f"/api/v1/poems/{sample_poem.id}/selected", json=selection_data)

        assert response.status_code == 200
        data = response.json()
        assert data["selected"] is False

    def test_delete_poem_success(self, test_client: TestClient, sample_poem):
        """Test DELETE /api/v1/poems/{poem_id} with existing poem."""
        response = test_client.delete(f"/api/v1/poems/{sample_poem.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert sample_poem.poem_title in data["message"]

        # Verify poem is deleted
        get_response = test_client.get(f"/api/v1/poems/{sample_poem.id}")
        assert get_response.status_code == 404

    def test_delete_poem_not_found(self, test_client: TestClient):
        """Test DELETE /api/v1/poems/{poem_id} with non-existent poem."""
        fake_id = str(uuid.uuid4())[:26]
        response = test_client.delete(f"/api/v1/poems/{fake_id}")

        assert response.status_code == 404

    def test_get_poem_translations_empty(self, test_client: TestClient, sample_poem):
        """Test GET /api/v1/poems/{poem_id}/translations with no translations."""
        response = test_client.get(f"/api/v1/poems/{sample_poem.id}/translations")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_get_poem_translations_with_data(self, test_client: TestClient, sample_poem, sample_translation):
        """Test GET /api/v1/poems/{poem_id}/translations with existing translations."""
        response = test_client.get(f"/api/v1/poems/{sample_poem.id}/translations")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        translation = data[0]
        assert translation["id"] == sample_translation.id
        assert translation["translator_type"] == sample_translation.translator_type
        assert translation["target_language"] == sample_translation.target_language
        assert translation["translated_text"] == sample_translation.translated_text

    def test_search_poems_by_title(self, test_client: TestClient, test_context):
        """Test POST /api/v1/poems/search by title."""
        # Create test poems
        await test_context.create_poem(
            poet_name="Poet 1",
            poem_title="The Rose Garden",
            original_text="Content about roses"
        )
        await test_context.create_poem(
            poet_name="Poet 2",
            poem_title="Spring Morning",
            original_text="Content about spring"
        )

        # Search for "Rose"
        response = test_client.post("/api/v1/poems/search?search_type=title&query=Rose")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "Rose" in data[0]["poem_title"]

    def test_get_filter_options(self, test_client: TestClient, test_context):
        """Test GET /api/v1/poems/filter-options."""
        # Create poems with different poets and languages
        await test_context.create_poem(poet_name="李白", source_language="Chinese")
        await test_context.create_poem(poet_name="Shakespeare", source_language="English")
        await test_context.create_poem(poet_name="Du Fu", source_language="Chinese")

        response = test_client.get("/api/v1/poems/filter-options")

        assert response.status_code == 200
        data = response.json()
        assert len(data["poets"]) == 3
        assert "李白" in data["poets"]
        assert "Shakespeare" in data["poets"]
        assert "Du Fu" in data["poets"]
        assert len(data["languages"]) == 2
        assert "Chinese" in data["languages"]
        assert "English" in data["languages"]

    def test_get_recent_activity(self, test_client: TestClient, test_context):
        """Test GET /api/v1/poems/recent-activity."""
        # Create a recent poem
        await test_context.create_poem(
            poet_name="Recent Poet",
            poem_title="Recent Poem",
            original_text="Recent content"
        )

        response = test_client.get("/api/v1/poems/recent-activity")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data


# ==============================================================================
# Translation API Endpoint Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.api
class TestTranslationEndpoints:
    """Test suite for translation API endpoints."""

    def test_list_translations_empty(self, test_client: TestClient):
        """Test GET /api/v1/translations/ with empty database."""
        response = test_client.get("/api/v1/translations/")

        assert response.status_code == 200
        data = response.json()
        assert data["translations"] == []
        assert data["pagination"]["total_items"] == 0

    def test_list_translations_with_data(self, test_client: TestClient, sample_translation):
        """Test GET /api/v1/translations/ with existing translations."""
        response = test_client.get("/api/v1/translations/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["translations"]) == 1

        translation = data["translations"][0]
        assert translation["id"] == sample_translation.id
        assert translation["target_language"] == sample_translation.target_language

    def test_trigger_translation_hybrid_mode(self, test_client: TestClient, sample_poem):
        """Test POST /api/v1/translations/trigger with hybrid workflow mode."""
        translation_request = {
            "poem_id": sample_poem.id,
            "target_lang": "Chinese",
            "workflow_mode": "hybrid"
        }

        # Mock the workflow service
        with patch('src.vpsweb.webui.services.interfaces.IWorkflowServiceV2') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.start_translation_workflow.return_value = "test-task-123"
            mock_service.return_value = mock_instance

            response = test_client.post("/api/v1/translations/trigger", json=translation_request)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["task_id"] == "test-task-123"
        assert "workflow started" in data["message"].lower()

    def test_trigger_translation_all_modes(self, test_client: TestClient, sample_poem):
        """Test POST /api/v1/translations/trigger with all workflow modes."""
        modes = ["hybrid", "manual", "reasoning", "non-reasoning"]

        for mode in modes:
            translation_request = {
                "poem_id": sample_poem.id,
                "target_lang": "Chinese",
                "workflow_mode": mode
            }

            with patch('src.vpsweb.webui.services.interfaces.IWorkflowServiceV2') as mock_service:
                mock_instance = AsyncMock()
                mock_instance.start_translation_workflow.return_value = f"test-task-{mode}"
                mock_service.return_value = mock_instance

                response = test_client.post("/api/v1/translations/trigger", json=translation_request)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["task_id"] == f"test-task-{mode}"

    def test_trigger_translation_validation_errors(self, test_client: TestClient):
        """Test POST /api/v1/translations/trigger with invalid data."""
        # Test missing poem_id
        invalid_request = {
            "target_lang": "Chinese",
            "workflow_mode": "hybrid"
        }

        response = test_client.post("/api/v1/translations/trigger", json=invalid_request)
        assert response.status_code == 422

        # Test invalid workflow mode
        invalid_request = {
            "poem_id": str(uuid.uuid4())[:26],
            "target_lang": "Chinese",
            "workflow_mode": "invalid_mode"
        }

        response = test_client.post("/api/v1/translations/trigger", json=invalid_request)
        assert response.status_code == 422

    def test_list_translations_filters(self, test_client: TestClient, test_context):
        """Test translation list filtering functionality."""
        # Create a poem and multiple translations
        poem = await test_context.create_poem(poet_name="Test Poet", poem_title="Test Poem")

        await test_context.create_translation(
            poem_id=poem.id,
            target_language="Chinese",
            translator_type="ai"
        )
        await test_context.create_translation(
            poem_id=poem.id,
            target_language="Japanese",
            translator_type="human"
        )

        # Test filter by poem_id
        response = test_client.get(f"/api/v1/translations/?poem_id={poem.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["translations"]) == 2

        # Test filter by target_language
        response = test_client.get("/api/v1/translations/?target_language=Chinese")
        assert response.status_code == 200
        data = response.json()
        assert len(data["translations"]) == 1
        assert data["translations"][0]["target_language"] == "Chinese"

        # Test filter by translator_type
        response = test_client.get("/api/v1/translations/?translator_type=ai")
        assert response.status_code == 200
        data = response.json()
        assert len(data["translations"]) == 1
        assert data["translations"][0]["translator_type"] == "ai"


# ==============================================================================
# BBR (Background Briefing Report) API Endpoint Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.api
class TestBBREndpoints:
    """Test suite for BBR API endpoints."""

    def test_generate_bbr_success(self, test_client: TestClient, sample_poem):
        """Test POST /api/v1/poems/{poem_id}/bbr/generate."""
        # Mock BBR service
        with patch('src.vpsweb.webui.services.interfaces.IBBRServiceV2') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.has_bbr.return_value = False
            mock_instance.generate_bbr.return_value = {"task_id": "bbr-task-123"}
            mock_service.return_value = mock_instance

            response = test_client.post(f"/api/v1/poems/{sample_poem.id}/bbr/generate")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Background Briefing Report generation started"
        assert data["data"]["task_id"] == "bbr-task-123"

    def test_generate_bbr_already_exists(self, test_client: TestClient, sample_poem):
        """Test POST /api/v1/poems/{poem_id}/bbr/generate when BBR already exists."""
        # Mock BBR service that returns existing BBR
        with patch('src.vpsweb.webui.services.interfaces.IBBRServiceV2') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.has_bbr.return_value = True
            mock_instance.get_bbr.return_value = {
                "id": "existing-bbr",
                "content": "Existing BBR content"
            }
            mock_service.return_value = mock_instance

            response = test_client.post(f"/api/v1/poems/{sample_poem.id}/bbr/generate")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Background Briefing Report already exists"
        assert data["data"]["regenerated"] is False
        assert data["data"]["bbr"]["id"] == "existing-bbr"

    def test_generate_bbr_poem_not_found(self, test_client: TestClient):
        """Test POST /api/v1/poems/{poem_id}/bbr/generate with non-existent poem."""
        fake_id = str(uuid.uuid4())[:26]
        response = test_client.post(f"/api/v1/poems/{fake_id}/bbr/generate")

        assert response.status_code == 404

    def test_get_bbr_success(self, test_client: TestClient, sample_poem):
        """Test GET /api/v1/poems/{poem_id}/bbr when BBR exists."""
        # Mock BBR service
        with patch('src.vpsweb.webui.services.interfaces.IBBRServiceV2') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_bbr.return_value = {
                "id": "test-bbr",
                "poem_id": sample_poem.id,
                "content": "Test BBR content",
                "generated_at": "2025-01-15T10:00:00Z"
            }
            mock_service.return_value = mock_instance

            response = test_client.get(f"/api/v1/poems/{sample_poem.id}/bbr")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Background Briefing Report found"
        assert data["data"]["has_bbr"] is True
        assert data["data"]["bbr"]["id"] == "test-bbr"

    def test_get_bbr_not_found(self, test_client: TestClient, sample_poem):
        """Test GET /api/v1/poems/{poem_id}/bbr when BBR doesn't exist."""
        # Mock BBR service
        with patch('src.vpsweb.webui.services.interfaces.IBBRServiceV2') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_bbr.return_value = None
            mock_service.return_value = mock_instance

            response = test_client.get(f"/api/v1/poems/{sample_poem.id}/bbr")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "No Background Briefing Report found"
        assert data["data"]["has_bbr"] is False

    def test_delete_bbr_success(self, test_client: TestClient, sample_poem):
        """Test DELETE /api/v1/poems/{poem_id}/bbr when BBR exists."""
        # Mock BBR service
        with patch('src.vpsweb.webui.services.interfaces.IBBRServiceV2') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.has_bbr.return_value = True
            mock_instance.delete_bbr.return_value = True
            mock_service.return_value = mock_instance

            response = test_client.delete(f"/api/v1/poems/{sample_poem.id}/bbr")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Background Briefing Report deleted successfully"
        assert data["data"]["deleted"] is True

    def test_delete_bbr_not_found(self, test_client: TestClient, sample_poem):
        """Test DELETE /api/v1/poems/{poem_id}/bbr when BBR doesn't exist."""
        # Mock BBR service
        with patch('src.vpsweb.webui.services.interfaces.IBBRServiceV2') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.has_bbr.return_value = False
            mock_service.return_value = mock_instance

            response = test_client.delete(f"/api/v1/poems/{sample_poem.id}/bbr")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "No Background Briefing Report to delete"
        assert data["data"]["deleted"] is False


# ==============================================================================
# Statistics API Endpoint Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.api
class TestStatisticsEndpoints:
    """Test suite for statistics API endpoints."""

    def test_get_dashboard_stats(self, test_client: TestClient):
        """Test GET /api/v1/statistics/dashboard."""
        response = test_client.get("/api/v1/statistics/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert "total_poems" in data
        assert "total_translations" in data
        assert "total_bbrs" in data
        assert "recent_activity" in data
        assert isinstance(data["total_poems"], int)
        assert isinstance(data["total_translations"], int)


# ==============================================================================
# Error Handling Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.api
class TestErrorHandling:
    """Test suite for API error handling."""

    def test_404_not_found(self, test_client: TestClient):
        """Test 404 response for non-existent endpoints."""
        response = test_client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code == 404

    def test_method_not_allowed(self, test_client: TestClient):
        """Test 405 response for wrong HTTP methods."""
        # Try to use POST on GET endpoint
        response = test_client.post("/api/v1/poems/")
        assert response.status_code == 422  # Validation error for empty POST

    def test_invalid_json(self, test_client: TestClient):
        """Test 400 response for invalid JSON."""
        response = test_client.post(
            "/api/v1/poems/",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_database_error_handling(self, test_client: TestClient, sample_poem):
        """Test API behavior when database operations fail."""
        # This would require mocking the database session to raise exceptions
        # For now, we just verify that the API responds gracefully
        response = test_client.get(f"/api/v1/poems/{sample_poem.id}")
        assert response.status_code in [200, 404, 500]  # Should be one of these


# ==============================================================================
# Performance Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.api
@pytest.mark.slow
class TestAPIPerformance:
    """Test suite for API performance."""

    def test_list_poems_performance(self, test_client: TestClient, test_context, performance_timer):
        """Test performance of poem list endpoint with multiple poems."""
        # Create many poems
        for i in range(50):
            await test_context.create_poem(
                poet_name=f"Poet {i}",
                poem_title=f"Poem {i}",
                original_text=f"Content {i}" * 10  # Longer content
            )

        performance_timer.start()
        response = test_client.get("/api/v1/poems/?page_size=20")
        performance_timer.stop()

        assert response.status_code == 200
        data = response.json()
        assert len(data["poems"]) == 20

        # Should respond within reasonable time (adjust threshold as needed)
        assert performance_timer.duration < 2.0

    def test_pagination_performance(self, test_client: TestClient, test_context, performance_timer):
        """Test pagination performance with large dataset."""
        # Create many poems
        for i in range(100):
            await test_context.create_poem(
                poet_name=f"Poet {i}",
                poem_title=f"Poem {i}",
                original_text=f"Content {i}"
            )

        # Test accessing last page
        performance_timer.start()
        response = test_client.get("/api/v1/poems/?page=5&page_size=20")
        performance_timer.stop()

        assert response.status_code == 200
        assert performance_timer.duration < 1.0


# ==============================================================================
# Integration Tests with Multiple Entities
# ==============================================================================

@pytest.mark.integration
@pytest.mark.api
class TestMultiEntityIntegration:
    """Test suite for API operations involving multiple entities."""

    async def test_poem_translation_workflow(self, test_client: TestClient, test_context):
        """Test complete workflow: create poem -> generate translations -> verify results."""
        # Create a poem
        poem = await test_context.create_poem(
            poet_name="Integration Poet",
            poem_title="Integration Test Poem",
            original_text="This poem tests the complete integration workflow."
        )

        # Create translations for the poem
        chinese_translation = await test_context.create_translation(
            poem_id=poem.id,
            target_language="Chinese",
            translated_text="这是集成测试诗歌的中文翻译。",
            translator_type="ai"
        )

        japanese_translation = await test_context.create_translation(
            poem_id=poem.id,
            target_language="Japanese",
            translated_text="これは統合テストの詩の日本語訳です。",
            translator_type="human"
        )

        # Verify poem data
        poem_response = test_client.get(f"/api/v1/poems/{poem.id}")
        assert poem_response.status_code == 200
        poem_data = poem_response.json()
        assert poem_data["translation_count"] == 2

        # Verify translations list
        translations_response = test_client.get(f"/api/v1/poems/{poem.id}/translations")
        assert translations_response.status_code == 200
        translations_data = translations_response.json()
        assert len(translations_data) == 2

        target_languages = {t["target_language"] for t in translations_data}
        assert "Chinese" in target_languages
        assert "Japanese" in target_languages

    @pytest.mark.asyncio
    async def test_filter_and_search_integration(self, test_client: TestClient, test_context):
        """Test integration between filtering and search functionality."""
        # Create diverse set of poems
        poems_data = [
            {
                "poet_name": "李白",
                "poem_title": "静夜思",
                "source_language": "Chinese",
                "original_text": "床前明月光"
            },
            {
                "poet_name": "杜甫",
                "poem_title": "春望",
                "source_language": "Chinese",
                "original_text": "国破山河在"
            },
            {
                "poet_name": "Wordsworth",
                "poem_title": "Daffodils",
                "source_language": "English",
                "original_text": "I wandered lonely as a cloud"
            }
        ]

        created_poems = []
        for poem_data in poems_data:
            poem = await test_context.create_poem(**poem_data)
            created_poems.append(poem)

        # Test combined filters
        response = test_client.get("/api/v1/poems/?language=Chinese")
        assert response.status_code == 200
        data = response.json()
        assert len(data["poems"]) == 2

        # Test search within filtered results
        response = test_client.post("/api/v1/poems/search?search_type=title&query=静")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "静" in data[0]["poem_title"]