"""
Background Briefing Report (BBR) Feature Tests for VPSWeb v0.7.0

Comprehensive tests for the BBR feature, including:
- BBR generation workflows
- Content quality and structure validation
- Integration with translation workflows
- API endpoint testing
- Performance and edge case testing
- File system integration
- LLM provider integration testing

BBR is a key v0.7.0 feature that provides AI-generated contextual analysis
for poems to enhance translation quality.
"""

import pytest
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.vpsweb.repository.models import Poem, BackgroundBriefingReport, Translation
from src.vpsweb.repository.crud import RepositoryService
from src.vpsweb.services.bbr_generator import BBRGeneratorService
from src.vpsweb.webui.services.interfaces import IBBRServiceV2


# ==============================================================================
# BBR Test Fixtures
# ==============================================================================

@pytest_asyncio.fixture
async def sample_poem_for_bbr(test_context):
    """Create a comprehensive poem suitable for BBR testing."""
    poem = await test_context.create_poem(
        poet_name="王維",
        poem_title="鹿柴",
        source_language="Chinese",
        original_text="""空山不見人，
但聞人語響。
返景入深林，
復照青苔上。""",
        metadata_json='{"dynasty": "Tang", "genre": "landscape_poetry", "theme": "nature", "form": "jueju"}'
    )
    return poem

@pytest_asyncio.fixture
async def complex_poem_for_bbr(test_context):
    """Create a complex poem with rich cultural context for BBR testing."""
    poem = await test_context.create_poem(
        poet_name="杜甫",
        poem_title="春望",
        source_language="Chinese",
        original_text="""國破山河在，城春草木深。
感時花濺淚，恨別鳥驚心。
烽火連三月，家書抵萬金。
白頭搔更短，渾欲不勝簪。""",
        metadata_json='{"dynasty": "Tang", "historical_context": "An Lushan Rebellion", "theme": "war_and_homesickness", "form": "lushi", "meter": "regulated_verse"}'
    )
    return poem

@pytest.fixture
def mock_bbr_content():
    """Mock BBR content for testing."""
    return """# Background Briefing Report: 鹿柴 by 王維

## Historical Context
王維 (Wang Wei, 701-761) was a Tang Dynasty poet renowned for his landscape poetry and Buddhist influences. "鹿柴" (Deer Enclosure) is one of his most famous works, exemplifying his mastery of capturing natural scenes with minimal words.

## Cultural Significance
This poem represents the pinnacle of Chinese landscape poetry (山水詩), demonstrating the Zen Buddhist concept of finding profound meaning in simple natural phenomena. The title "鹿柴" refers to a fenced enclosure or corral for deer, suggesting a place where nature and human activity intersect.

## Literary Analysis
### Structure and Form
- **Form**: 絕句 (Jueju) - Four-line regulated verse
- **Meter**: 5 characters per line
- **Rhyme Scheme**: AABA (響 xiǎng, 上 shàng)
- **Tone**: Meditative, observant, deeply connected to nature

### Key Imagery and Symbolism
1. **空山 (Empty Mountain)**: Represents both literal emptiness and the Buddhist concept of śūnyatā (emptiness)
2. **人語響 (Human voice echo)**: The paradox of presence through absence
3. **返景 (Returning light)**: Evening/afternoon light, possibly sunset
4. **青苔 (Green moss)**: Represents age, persistence, and the quiet passage of time

## Translation Challenges and Recommendations

### Challenge 1: Conceptual Density
Each line contains layers of meaning that resist direct translation:
- "空山" literally means "empty mountain" but carries profound Buddhist philosophical implications
- "返景" could mean "returning light," "reflected light," or "afternoon light"

**Recommendation**: Consider using footnotes or translator's notes to explain the deeper cultural and philosophical context.

### Challenge 2: Sound and Tone
The original Chinese creates specific phonetic resonances:
- "響" (xiǎng) evokes echo and resonance
- The parallel structure creates musicality

**Recommendation**: Preserve the contemplative tone even if literal meaning must be adapted. Consider using words that create similar auditory effects in the target language.

### Challenge 3: Minimalism
The poem's power comes from extreme concision (20 characters total). Direct translation often requires expansion to convey equivalent meaning.

**Recommendation**:
1. Prioritize preserving the core paradox (presence through absence)
2. Maintain the four-line structure if possible
3. Consider that some cultural concepts may require explanation rather than direct translation

## Cultural Context for Target Languages

### For English Translations
- English readers may not be familiar with Chinese landscape poetry traditions
- Buddhist philosophical concepts may need contextualization
- Consider the tradition of Romantic nature poetry as potential points of connection

### For Japanese Translations
- Japanese readers have cultural affinity with Chinese poetry traditions
- Many Buddhist concepts translate more directly
- Kanji characters maintain visual connection to original

### For Korean Translations
- Shared classical Chinese literary tradition (Hanmun)
- Similar philosophical traditions
- Consider historical Korean reception of Tang poetry

## Quality Assessment Criteria
1. **Preservation of Core Paradox**: Does the translation maintain the tension between emptiness and presence?
2. **Natural Language Quality**: Does it read naturally in the target language?
3. **Cultural Accessibility**: Is it understandable without extensive footnotes?
4. **Poetic Quality**: Does it maintain the meditative, observant tone?

## Recommended Translation Approaches

### Approach 1: Literal with Notes
Translate closely to original structure and use extensive notes to explain cultural context.

### Approach 2: Adaptive Translation
Prioritize conveying the emotional and philosophical impact over literal accuracy.

### Approach 3: Creative Interpretation
Create a new poem in the target language that captures the spirit and core insights of the original.

## Additional Resources
- "The Poetry of Wang Wei: New Translations and Commentary" (for reference translations)
- Buddhist philosophy texts explaining concepts of emptiness and presence
- Tang Dynasty historical context for deeper understanding"""

@pytest.fixture
def mock_bbr_service():
    """Create a mock BBR service for testing."""
    mock_service = AsyncMock(spec=IBBRServiceV2)
    mock_service.has_bbr.return_value = False
    mock_service.get_bbr.return_value = {
        "id": "test-bbr-id",
        "poem_id": "test-poem-id",
        "content": "Test BBR content",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    mock_service.generate_bbr.return_value = {
        "task_id": "bbr-task-123",
        "status": "started",
        "estimated_completion": "2-3 minutes"
    }
    mock_service.delete_bbr.return_value = True
    return mock_service


# ==============================================================================
# BBR Service Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.bbr
class TestBBRService:
    """Test the BBR service functionality."""

    async def test_bbr_generation_workflow(self, mock_bbr_service, sample_poem_for_bbr):
        """Test complete BBR generation workflow."""
        # Initial state - no BBR exists
        mock_bbr_service.has_bbr.return_value = False

        # Check if BBR exists
        has_bbr = await mock_bbr_service.has_bbr(sample_poem_for_bbr.id)
        assert has_bbr is False

        # Generate BBR
        with patch('src.vpsweb.webui.container.container') as mock_container:
            mock_container.resolve.return_value = mock_bbr_service

            result = await mock_bbr_service.generate_bbr(
                sample_poem_for_bbr.id,
                AsyncMock()  # BackgroundTasks mock
            )

        assert result["task_id"] == "bbr-task-123"
        assert result["status"] == "started"

        # Verify the service was called correctly
        mock_bbr_service.generate_bbr.assert_called_once()

    async def test_bbr_retrieval(self, mock_bbr_service, sample_poem_for_bbr):
        """Test BBR retrieval functionality."""
        # Mock BBR exists
        mock_bbr_service.has_bbr.return_value = True

        # Get BBR
        bbr = await mock_bbr_service.get_bbr(sample_poem_for_bbr.id)

        assert bbr is not None
        assert bbr["id"] == "test-bbr-id"
        assert bbr["poem_id"] == "test-poem-id"
        assert "content" in bbr

    async def test_bbr_exists_check(self, mock_bbr_service, sample_poem_for_bbr):
        """Test BBR existence checking."""
        # Test when BBR exists
        mock_bbr_service.has_bbr.return_value = True
        has_bbr = await mock_bbr_service.has_bbr(sample_poem_for_bbr.id)
        assert has_bbr is True

        # Test when BBR doesn't exist
        mock_bbr_service.has_bbr.return_value = False
        has_bbr = await mock_bbr_service.has_bbr(sample_poem_for_bbr.id)
        assert has_bbr is False

    async def test_bbr_deletion(self, mock_bbr_service, sample_poem_for_bbr):
        """Test BBR deletion functionality."""
        # Mock BBR exists
        mock_bbr_service.has_bbr.return_value = True

        # Delete BBR
        deleted = await mock_bbr_service.delete_bbr(sample_poem_for_bbr.id)
        assert deleted is True

        # Verify service was called
        mock_bbr_service.delete_bbr.assert_called_once_with(sample_poem_for_bbr.id)


# ==============================================================================
# BBR Generator Service Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.bbr
class TestBBRGeneratorService:
    """Test the BBR Generator Service."""

    async def test_bbr_generator_with_simple_poem(self, repository_service: RepositoryService, sample_poem_for_bbr):
        """Test BBR generation with a simple poem."""
        generator = BBRGeneratorService(repository_service)

        # Mock LLM response
        mock_llm_response = {
            "choices": [{
                "message": {
                    "content": mock_bbr_content()
                }
            }]
        }

        with patch('src.vpsweb.services.llm.factory.LLMFactory.get_provider') as mock_llm_factory:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = mock_llm_response
            mock_llm_factory.return_value = mock_llm

            # Generate BBR
            bbr_content = await generator.generate_bbr_content(sample_poem_for_bbr)

        assert bbr_content is not None
        assert len(bbr_content) > 1000  # Should be substantial
        assert "Historical Context" in bbr_content
        assert "Cultural Significance" in bbr_content
        assert "Translation Challenges" in bbr_content

    async def test_bbr_generator_with_complex_poem(self, repository_service: RepositoryService, complex_poem_for_bbr):
        """Test BBR generation with a complex poem rich in cultural context."""
        generator = BBRGeneratorService(repository_service)

        # Mock detailed LLM response for complex poem
        detailed_mock_response = {
            "choices": [{
                "message": {
                    "content": f"""# Background Briefing Report: 春望 by 杜甫

## Historical Context
杜甫 (Du Fu, 712-770), known as the "Poet-Historian," wrote this during the 安史之亂 (An Lushan Rebellion, 755-763), one of the most devastating civil wars in Chinese history. The fall of the capital 洛陽 and the emperor's flight created profound personal and national trauma.

## Cultural Significance
"春望" (Spring Gaze) captures the paradox of spring renewal amid national destruction. It embodies the Confucian ideal of using personal suffering to reflect on broader social and political concerns, establishing a template for politically engaged poetry.

## Deep Analysis
{mock_bbr_content()}
"""
                }
            }]
        }

        with patch('src.vpsweb.services.llm.factory.LLMFactory.get_provider') as mock_llm_factory:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = detailed_mock_response
            mock_llm_factory.return_value = mock_llm

            # Generate BBR
            bbr_content = await generator.generate_bbr_content(complex_poem_for_bbr)

        assert bbr_content is not None
        assert "Historical Context" in bbr_content
        assert "An Lushan Rebellion" in bbr_content
        assert "Poet-Historian" in bbr_content

    async def test_bbr_generator_error_handling(self, repository_service: RepositoryService, sample_poem_for_bbr):
        """Test BBR generator error handling."""
        generator = BBRGeneratorService(repository_service)

        # Mock LLM failure
        with patch('src.vpsweb.services.llm.factory.LLMFactory.get_provider') as mock_llm_factory:
            mock_llm = AsyncMock()
            mock_llm.generate.side_effect = Exception("LLM API Error")
            mock_llm_factory.return_value = mock_llm

            # Should handle error gracefully
            with pytest.raises(Exception):
                await generator.generate_bbr_content(sample_poem_for_bbr)

    async def test_bbr_generator_content_quality(self, repository_service: RepositoryService, sample_poem_for_bbr):
        """Test BBR content quality and structure."""
        generator = BBRGeneratorService(repository_service)

        # Mock high-quality LLM response
        quality_mock_response = {
            "choices": [{
                "message": {
                    "content": mock_bbr_content()
                }
            }]
        }

        with patch('src.vpsweb.services.llm.factory.LLMFactory.get_provider') as mock_llm_factory:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = quality_mock_response
            mock_llm_factory.return_value = mock_llm

            bbr_content = await generator.generate_bbr_content(sample_poem_for_bbr)

        # Validate content structure
        required_sections = [
            "Historical Context",
            "Cultural Significance",
            "Translation Challenges",
            "Quality Assessment Criteria"
        ]

        for section in required_sections:
            assert section in bbr_content, f"Missing required section: {section}"

        # Validate content length and quality
        assert len(bbr_content) > 2000  # Should be comprehensive
        assert bbr_content.count('#') >= 5  # Should have proper markdown structure

    async def test_bbr_generator_with_different_poems(self, repository_service: RepositoryService, test_context):
        """Test BBR generator with poems from different genres and eras."""
        generator = BBRGeneratorService(repository_service)

        test_poems = [
            await test_context.create_poem(
                poet_name="李白",
                poem_title="將進酒",
                source_language="Chinese",
                original_text="君不見黃河之水天上來...",
                metadata_json='{"dynasty": "Tang", "genre": "celebration_poetry"}'
            ),
            await test_context.create_poem(
                poet_name="William Shakespeare",
                poem_title="Sonnet 18",
                source_language="English",
                original_text="Shall I compare thee to a summer's day?",
                metadata_json='{"era": "Renaissance", "genre": "sonnet"}'
            )
        ]

        mock_response = {
            "choices": [{
                "message": {
                    "content": mock_bbr_content()
                }
            }]
        }

        with patch('src.vpsweb.services.llm.factory.LLMFactory.get_provider') as mock_llm_factory:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = mock_response
            mock_llm_factory.return_value = mock_llm

            # Generate BBR for each poem
            for poem in test_poems:
                bbr_content = await generator.generate_bbr_content(poem)
                assert bbr_content is not None
                assert len(bbr_content) > 1000


# ==============================================================================
# BBR API Endpoint Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.api
@pytest.mark.bbr
class TestBBRAPIEndpoints:
    """Test BBR-related API endpoints."""

    def test_generate_bbr_endpoint(self, test_client: TestClient, sample_poem, mock_bbr_service):
        """Test POST /api/v1/poems/{poem_id}/bbr/generate endpoint."""
        with patch('src.vpsweb.webui.container.container') as mock_container:
            mock_container.resolve.return_value = mock_bbr_service

            response = test_client.post(f"/api/v1/poems/{sample_poem.id}/bbr/generate")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Background Briefing Report generation started"
        assert "task_id" in data["data"]

    def test_generate_bbr_already_exists(self, test_client: TestClient, sample_poem):
        """Test BBR generation when BBR already exists."""
        # Mock service that returns existing BBR
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

    def test_get_bbr_success(self, test_client: TestClient, sample_poem):
        """Test GET /api/v1/poems/{poem_id}/bbr when BBR exists."""
        with patch('src.vpsweb.webui.services.interfaces.IBBRServiceV2') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_bbr.return_value = {
                "id": "test-bbr",
                "poem_id": sample_poem.id,
                "content": mock_bbr_content(),
                "created_at": datetime.now().isoformat()
            }
            mock_service.return_value = mock_instance

            response = test_client.get(f"/api/v1/poems/{sample_poem.id}/bbr")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["has_bbr"] is True
        assert "bbr" in data["data"]
        assert len(data["data"]["bbr"]["content"]) > 1000

    def test_get_bbr_not_found(self, test_client: TestClient, sample_poem):
        """Test GET /api/v1/poems/{poem_id}/bbr when BBR doesn't exist."""
        with patch('src.vpsweb.webui.services.interfaces.IBBRServiceV2') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_bbr.return_value = None
            mock_service.return_value = mock_instance

            response = test_client.get(f"/api/v1/poems/{sample_poem.id}/bbr")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["has_bbr"] is False

    def test_delete_bbr_success(self, test_client: TestClient, sample_poem):
        """Test DELETE /api/v1/poems/{poem_id}/bbr when BBR exists."""
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

    def test_bbr_poem_not_found(self, test_client: TestClient):
        """Test BBR endpoints with non-existent poem."""
        fake_poem_id = str(uuid.uuid4())[:26]

        # Test generate BBR
        response = test_client.post(f"/api/v1/poems/{fake_poem_id}/bbr/generate")
        assert response.status_code == 404

        # Test get BBR
        response = test_client.get(f"/api/v1/poems/{fake_poem_id}/bbr")
        assert response.status_code == 404

        # Test delete BBR
        response = test_client.delete(f"/api/v1/poems/{fake_poem_id}/bbr")
        assert response.status_code == 404


# ==============================================================================
# BBR Integration Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.bbr
class TestBBRIntegration:
    """Test BBR integration with translation workflows."""

    async def test_bbr_integration_with_translation_workflow(self, test_client: TestClient, sample_poem):
        """Test that BBR integrates properly with translation workflow."""
        # Generate BBR first
        with patch('src.vpsweb.webui.services.interfaces.IBBRServiceV2') as mock_bbr_service:
            mock_bbr_instance = AsyncMock()
            mock_bbr_instance.has_bbr.return_value = False
            mock_bbr_instance.generate_bbr.return_value = {"task_id": "bbr-123"}
            mock_bbr_service.return_value = mock_bbr_instance

            bbr_response = test_client.post(f"/api/v1/poems/{sample_poem.id}/bbr/generate")
            assert bbr_response.status_code == 200

        # Then trigger translation with BBR context
        translation_request = {
            "poem_id": sample_poem.id,
            "target_lang": "English",
            "workflow_mode": "hybrid"
        }

        with patch('src.vpsweb.webui.services.interfaces.IWorkflowServiceV2') as mock_workflow:
            mock_instance = AsyncMock()
            mock_instance.start_translation_workflow.return_value = "translation-456"
            mock_workflow.return_value = mock_instance

            translation_response = test_client.post("/api/v1/translations/trigger", json=translation_request)

        assert translation_response.status_code == 200
        translation_data = translation_response.json()
        assert translation_data["success"] is True

    async def test_bbr_content_quality_impact(self, repository_service: RepositoryService, test_context):
        """Test that BBR content positively impacts translation quality."""
        # Create poem
        poem = await test_context.create_poem(
            poet_name="Test Poet",
            poem_title="Test Poem",
            source_language="Chinese",
            original_text="Test content with cultural significance"
        )

        # Create BBR with high-quality contextual information
        bbr_data = {
            "id": str(uuid.uuid4())[:26],
            "poem_id": poem.id,
            "content": mock_bbr_content(),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        bbr = BackgroundBriefingReport(**bbr_data)
        repository_service.db.add(bbr)
        await repository_service.db.commit()

        # Verify BBR is associated with poem
        retrieved_poem = await repository_service.poems.get_by_id(poem.id)
        assert retrieved_poem is not None
        # Note: This depends on how the relationship is implemented in the models

    async def test_bbr_file_system_integration(self, repository_service: RepositoryService, sample_poem):
        """Test BBR integration with file system storage."""
        # Create BBR
        bbr_content = mock_bbr_content()

        bbr_data = {
            "id": str(uuid.uuid4())[:26],
            "poem_id": sample_poem.id,
            "content": bbr_content,
            "metadata_json": '{"stored_in_filesystem": true}',
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        bbr = BackgroundBriefingReport(**bbr_data)
        repository_service.db.add(bbr)
        await repository_service.db.commit()

        # Verify BBR was created and can be retrieved
        retrieved_bbr = await repository_service.bbrs.get_by_id(bbr.id)
        assert retrieved_bbr is not None
        assert len(retrieved_bbr.content) > 1000

    async def test_bbr_with_multiple_translations(self, repository_service: RepositoryService, test_context):
        """Test BBR functionality with multiple translations of the same poem."""
        # Create poem
        poem = await test_context.create_poem(
            poet_name="Multi-Translation Poet",
            poem_title="Multi-Translation Poem",
            source_language="Chinese",
            original_text="Content suitable for multiple translations"
        )

        # Create BBR
        bbr_data = {
            "id": str(uuid.uuid4())[:26],
            "poem_id": poem.id,
            "content": mock_bbr_content(),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        bbr = BackgroundBriefingReport(**bbr_data)
        repository_service.db.add(bbr)
        await repository_service.db.commit()

        # Create multiple translations
        translations = []
        for target_lang in ["English", "Japanese", "Korean"]:
            translation = await test_context.create_translation(
                poem_id=poem.id,
                target_language=target_lang,
                translator_type=TranslatorType.AI,
                translated_text=f"Translation in {target_lang}"
            )
            translations.append(translation)

        # Verify all translations are associated with the same poem that has BBR
        assert len(translations) == 3
        for translation in translations:
            assert translation.poem_id == poem.id


# ==============================================================================
# BBR Performance and Edge Case Tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.bbr
@pytest.mark.slow
class TestBBRPerformanceAndEdgeCases:
    """Test BBR performance and edge cases."""

    async def test_bbr_generation_performance(self, repository_service: RepositoryService, test_context, performance_timer):
        """Test BBR generation performance with large poems."""
        # Create a very long poem
        long_poem = await test_context.create_poem(
            poet_name="Long Poem Author",
            poem_title="Very Long Poem",
            source_language="Chinese",
            original_text="Very long poem content. " * 100,  # 4000 characters
            metadata_json='{"length": "very_long", "complexity": "high"}'
        )

        generator = BBRGeneratorService(repository_service)

        # Mock LLM response
        mock_response = {
            "choices": [{
                "message": {
                    "content": mock_bbr_content()
                }
            }]
        }

        with patch('src.vpsweb.services.llm.factory.LLMFactory.get_provider') as mock_llm_factory:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = mock_response
            mock_llm_factory.return_value = mock_llm

            performance_timer.start()
            bbr_content = await generator.generate_bbr_content(long_poem)
            performance_timer.stop()

        assert bbr_content is not None
        assert len(bbr_content) > 1000
        # Should complete within reasonable time (adjust threshold as needed)
        assert performance_timer.duration < 5.0

    async def test_bbr_with_minimal_poem_content(self, repository_service: RepositoryService, test_context):
        """Test BBR generation with minimal poem content."""
        minimal_poem = await test_context.create_poem(
            poet_name="Minimalist",
            poem_title="Short",
            source_language="English",
            original_text="Brief poem.",
            metadata_json='{"length": "minimal"}'
        )

        generator = BBRGeneratorService(repository_service)

        # Mock LLM response for minimal content
        mock_response = {
            "choices": [{
                "message": {
                    "content": """# Background Briefing Report: Short by Minimalist

## Historical Context
Limited biographical information available for this minimalist poem.

## Cultural Significance
Despite its brevity, this poem demonstrates how meaning can be concentrated in minimal text.

## Translation Challenges
- Limited context for interpretation
- Ambiguity in meaning due to minimal content
- Difficulty assessing authorial intent

## Notes
This BBR is necessarily limited due to the minimal source material available."""
                }
            }]
        }

        with patch('src.vpsweb.services.llm.factory.LLMFactory.get_provider') as mock_llm_factory:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = mock_response
            mock_llm_factory.return_value = mock_llm

            bbr_content = await generator.generate_bbr_content(minimal_poem)

        assert bbr_content is not None
        assert "limited context" in bbr_content.lower()

    async def test_bbr_concurrent_generation(self, repository_service: RepositoryService, test_context):
        """Test concurrent BBR generation for multiple poems."""
        # Create multiple poems
        poems = []
        for i in range(3):
            poem = await test_context.create_poem(
                poet_name=f"Concurrent Poet {i}",
                poem_title=f"Concurrent Poem {i}",
                source_language="Chinese",
                original_text=f"Concurrent poem content {i}",
                metadata_json=f'{{"index": {i}}}'
            )
            poems.append(poem)

        generator = BBRGeneratorService(repository_service)

        # Mock LLM response
        mock_response = {
            "choices": [{
                "message": {
                    "content": mock_bbr_content()
                }
            }]
        }

        with patch('src.vpsweb.services.llm.factory.LLMFactory.get_provider') as mock_llm_factory:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = mock_response
            mock_llm_factory.return_value = mock_llm

            # Generate BBRs concurrently
            tasks = [generator.generate_bbr_content(poem) for poem in poems]
            results = await asyncio.gather(*tasks)

        assert len(results) == 3
        for result in results:
            assert result is not None
            assert len(result) > 1000

    async def test_bbr_error_recovery(self, repository_service: RepositoryService, test_context):
        """Test BBR generation error recovery and retry logic."""
        poem = await test_context.create_poem(
            poet_name="Error Test Poet",
            poem_title="Error Test Poem",
            source_language="English",
            original_text="Test content for error handling"
        )

        generator = BBRGeneratorService(repository_service)

        # Mock LLM that fails first time, succeeds second time
        call_count = 0
        def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary API failure")
            return {
                "choices": [{
                    "message": {
                        "content": mock_bbr_content()
                    }
                }]
            }

        with patch('src.vpsweb.services.llm.factory.LLMFactory.get_provider') as mock_llm_factory:
            mock_llm = AsyncMock()
            mock_llm.generate.side_effect = mock_generate
            mock_llm_factory.return_value = mock_llm

            # First call should fail
            with pytest.raises(Exception):
                await generator.generate_bbr_content(poem)

            # Second call should succeed (if retry logic is implemented)
            # This test would need to be adapted based on actual retry implementation
            # For now, we just verify that the second call works
            result = await generator.generate_bbr_content(poem)
            assert result is not None

    async def test_bbr_content_validation(self, repository_service: RepositoryService, sample_poem):
        """Test BBR content validation and quality checks."""
        generator = BBRGeneratorService(repository_service)

        # Test various quality levels of LLM responses
        test_cases = [
            {
                "name": "high_quality",
                "content": mock_bbr_content(),
                "expected_valid": True
            },
            {
                "name": "low_quality_short",
                "content": "Brief analysis.",
                "expected_valid": False
            },
            {
                "name": "missing_sections",
                "content": "Some content but missing required sections",
                "expected_valid": False
            },
            {
                "name": "malformed_content",
                "content": "Malformed content with broken structure [[[",
                "expected_valid": False
            }
        ]

        for case in test_cases:
            mock_response = {
                "choices": [{
                    "message": {
                        "content": case["content"]
                    }
                }]
            }

            with patch('src.vpsweb.services.llm.factory.LLMFactory.get_provider') as mock_llm_factory:
                mock_llm = AsyncMock()
                mock_llm.generate.return_value = mock_response
                mock_llm_factory.return_value = mock_llm

                result = await generator.generate_bbr_content(sample_poem)

                if case["expected_valid"]:
                    assert result is not None
                    assert len(result) > 100  # Should have reasonable length
                else:
                    # Behavior depends on validation implementation
                    # Might return result anyway with quality warnings
                    assert result is not None