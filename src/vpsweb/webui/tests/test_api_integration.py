"""
API Integration Tests for VPSWeb Repository Web UI

Integration tests for all API endpoints to ensure they work correctly
with the database and business logic.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.vpsweb.repository.database import Base
from src.vpsweb.repository.schemas import PoemCreate
from src.vpsweb.webui.main import app

# Test client setup
client = TestClient(app)


@pytest.fixture
def db_session():
    """Create a test database session"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Use in-memory SQLite for testing
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_poem(db_session: Session):
    """Create a sample poem for testing"""
    poem_data = PoemCreate(
        poet_name="Test Poet",
        poem_title="Test Poem",
        source_language="English",
        original_text="This is a test poem for integration testing.",
        metadata_json={"test": True},
    )

    # Use the repository service to create the poem
    from src.vpsweb.repository.crud import RepositoryService

    service = RepositoryService(db_session)
    poem = service.poems.create(poem_data)
    return poem


class TestPoemAPI:
    """Test poem API endpoints"""

    def test_list_poems_empty(self, db_session: Session):
        """Test listing poems when database is empty"""
        response = client.get("/api/v1/poems/")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_poem(self, db_session: Session):
        """Test creating a new poem"""
        poem_data = {
            "poet_name": "William Shakespeare",
            "poem_title": "Sonnet 18",
            "source_language": "English",
            "original_text": "Shall I compare thee to a summer's day?",
            "metadata": '{"test": true}',
        }

        response = client.post("/api/v1/poems/", json=poem_data)
        assert response.status_code == 200

        data = response.json()
        assert data["poet_name"] == "William Shakespeare"
        assert data["poem_title"] == "Sonnet 18"
        assert data["source_language"] == "English"
        assert "id" in data
        assert "created_at" in data

    def test_get_poem_by_id(self, db_session: Session, sample_poem):
        """Test getting a poem by ID"""
        response = client.get(f"/api/v1/poems/{sample_poem.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == sample_poem.id
        assert data["poet_name"] == "Test Poet"

    def test_get_poem_not_found(self, db_session: Session):
        """Test getting a non-existent poem"""
        fake_id = "01H1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        response = client.get(f"/api/v1/poems/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_poem(self, db_session: Session, sample_poem):
        """Test updating a poem"""
        update_data = {
            "poet_name": "Updated Poet",
            "poem_title": "Updated Title",
            "source_language": "English",
            "original_text": "Updated poem text",
            "metadata": "Updated metadata",
        }

        response = client.put(
            f"/api/v1/poems/{sample_poem.id}", json=update_data
        )
        assert response.status_code == 200

        data = response.json()
        assert data["poet_name"] == "Updated Poet"
        assert data["poem_title"] == "Updated Title"

    def test_delete_poem(self, db_session: Session, sample_poem):
        """Test deleting a poem"""
        response = client.delete(f"/api/v1/poems/{sample_poem.id}")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_search_poems(self, db_session: Session, sample_poem):
        """Test searching poems"""
        response = client.post(
            "/api/v1/poems/search",
            params={"query": "Test", "search_type": "title"},
        )
        assert response.status_code == 200
        # Should return the sample poem
        data = response.json()
        assert len(data) >= 1

    def test_filter_poems_by_poet(self, db_session: Session, sample_poem):
        """Test filtering poems by poet name"""
        response = client.get(
            "/api/v1/poems/", params={"poet_name": "Test Poet"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["poet_name"] == "Test Poet"

    def test_poem_translations_endpoint(
        self, db_session: Session, sample_poem
    ):
        """Test getting translations for a poem"""
        response = client.get(f"/api/v1/poems/{sample_poem.id}/translations")
        assert response.status_code == 200
        # Should return empty list for new poem
        assert response.json() == []


class TestTranslationAPI:
    """Test translation API endpoints"""

    def test_create_translation(self, db_session: Session, sample_poem):
        """Test creating a new translation"""
        translation_data = {
            "poem_id": sample_poem.id,
            "target_language": "Chinese",
            "translator_name": "Test Translator",
            "translated_text": "这是一个测试翻译。",
            "quality_rating": 4,
        }

        response = client.post("/api/v1/translations/", json=translation_data)
        assert response.status_code == 200

        data = response.json()
        assert data["poem_id"] == sample_poem.id
        assert data["target_language"] == "Chinese"
        assert data["translator_type"] == "Human"

    def test_create_translation_invalid_poem(self, db_session: Session):
        """Test creating translation for non-existent poem"""
        translation_data = {
            "poem_id": "01H1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "target_language": "Chinese",
            "translator_name": "Test Translator",
            "translated_text": "这是一个测试翻译。",
            "quality_rating": 4,
        }

        response = client.post("/api/v1/translations/", json=translation_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_list_translations(self, db_session: Session, sample_poem):
        """Test listing translations"""
        # First create a translation
        translation_data = {
            "poem_id": sample_poem.id,
            "target_language": "Chinese",
            "translator_name": "Test Translator",
            "translated_text": "这是一个测试翻译。",
            "quality_rating": 4,
        }
        client.post("/api/v1/translations/", json=translation_data)

        # Then list translations
        response = client.get("/api/v1/translations/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_trigger_translation_workflow(
        self, db_session: Session, sample_poem
    ):
        """Test triggering translation workflow"""
        workflow_data = {
            "poem_id": sample_poem.id,
            "target_lang": "Spanish",
            "workflow_mode": "hybrid",
        }

        response = client.post(
            "/api/v1/translations/trigger", json=workflow_data
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "translation_id" in data

    def test_add_human_note(self, db_session: Session, sample_poem):
        """Test adding a human note to translation"""
        # First create a translation
        translation_data = {
            "poem_id": sample_poem.id,
            "target_language": "Chinese",
            "translator_name": "Test Translator",
            "translated_text": "这是一个测试翻译。",
            "quality_rating": 4,
        }
        translation_response = client.post(
            "/api/v1/translations/", json=translation_data
        )
        translation_id = translation_response.json()["id"]

        # Then add a note
        note_data = {"note_text": "This is a test note for the translation."}

        response = client.post(
            f"/api/v1/translations/{translation_id}/notes", json=note_data
        )
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestStatisticsAPI:
    """Test statistics API endpoints"""

    def test_get_repository_overview(self, db_session: Session):
        """Test getting repository overview statistics"""
        response = client.get("/api/v1/statistics/overview")
        assert response.status_code == 200

        data = response.json()
        assert "total_poems" in data
        assert "total_translations" in data
        assert "total_ai_translations" in data
        assert "total_human_translations" in data

    def test_get_language_distribution(self, db_session: Session, sample_poem):
        """Test getting language distribution statistics"""
        response = client.get("/api/v1/statistics/poems/language-distribution")
        assert response.status_code == 200

        data = response.json()
        assert "source_languages" in data
        assert "target_languages" in data
        assert "language_pairs" in data

    def test_get_search_metrics(self, db_session: Session, sample_poem):
        """Test getting search metrics"""
        response = client.get("/api/v1/statistics/search/metrics")
        assert response.status_code == 200

        data = response.json()
        assert "available_filters" in data
        assert "collection_stats" in data

        filters = data["available_filters"]
        assert "poets" in filters
        assert "source_languages" in filters
        assert "target_languages" in filters

    def test_get_translator_productivity(
        self, db_session: Session, sample_poem
    ):
        """Test getting translator productivity metrics"""
        response = client.get("/api/v1/statistics/translators/productivity")
        assert response.status_code == 200

        data = response.json()
        assert "total_translators" in data
        assert "translator_stats" in data

    def test_get_activity_timeline(self, db_session: Session, sample_poem):
        """Test getting activity timeline"""
        response = client.get(
            "/api/v1/statistics/timeline/activity", params={"days": 30}
        )
        assert response.status_code == 200

        data = response.json()
        assert "period" in data
        assert "summary" in data
        assert "daily_activity" in data


class TestAPIErrorHandling:
    """Test API error handling and validation"""

    def test_invalid_poem_data(self, db_session: Session):
        """Test validation of invalid poem data"""
        invalid_data = {
            "poet_name": "",  # Empty poet name
            "poem_title": "Test",
            "source_language": "EN",
            "original_text": "Test",
        }

        response = client.post("/api/v1/poems/", json=invalid_data)
        # Should return validation error
        assert response.status_code == 422

    def test_invalid_translation_data(self, db_session: Session, sample_poem):
        """Test validation of invalid translation data"""
        invalid_data = {
            "poem_id": sample_poem.id,
            "target_language": "",  # Empty target language
            "translator_name": "Test",
            "translated_text": "Test",
            "quality_rating": 10,  # Invalid rating (should be 1-5)
        }

        response = client.post("/api/v1/translations/", json=invalid_data)
        # Should return validation error
        assert response.status_code == 422

    def test_invalid_query_parameters(self, db_session: Session):
        """Test validation of invalid query parameters"""
        response = client.get(
            "/api/v1/poems/", params={"limit": 200}  # Exceeds maximum limit
        )
        # Should return validation error
        assert response.status_code == 422

    def test_pagination_parameters(self, db_session: Session, sample_poem):
        """Test pagination parameters work correctly"""
        response = client.get(
            "/api/v1/poems/", params={"skip": 0, "limit": 10}
        )
        assert response.status_code == 200
        # Should return results or empty list


class TestAPIHealth:
    """Test API health and basic functionality"""

    def test_health_check(self):
        """Test API health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_api_docs_accessible(self):
        """Test that API documentation is accessible"""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_spec(self):
        """Test OpenAPI specification is accessible"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
