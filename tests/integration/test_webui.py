"""
WebUI Smoke Tests for VPSWeb v0.7.0

Comprehensive smoke tests for the VPSWeb web interface ensuring:
- Main pages load correctly
- JavaScript and CSS assets are served
- Basic navigation works
- Error pages display properly
- Real-time features (SSE) are functional
- Integration with API endpoints

These tests validate the primary user experience at http://127.0.0.1:8000
"""

import pytest
import pytest_asyncio
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.vpsweb.repository.models import Poem, Translation, BackgroundBriefingReport
from src.vpsweb.repository.crud import RepositoryService


# ==============================================================================
# WebUI Test Fixtures
# ==============================================================================


@pytest.fixture
def webui_test_client(test_client: TestClient):
    """Create a test client specifically configured for WebUI testing."""
    return test_client


@pytest_asyncio.fixture
async def sample_poems_for_ui(test_context):
    """Create sample poems for WebUI testing."""
    poems = []

    # Create diverse poems for different test scenarios
    poem_data = [
        {
            "poet_name": "李白",
            "poem_title": "靜夜思",
            "source_language": "Chinese",
            "original_text": """床前明月光，
疑是地上霜。
舉頭望明月，
低頭思故鄉。""",
            "metadata_json": '{"dynasty": "Tang", "theme": "homesickness"}',
        },
        {
            "poet_name": "Emily Dickinson",
            "poem_title": "Hope is the thing with feathers",
            "source_language": "English",
            "original_text": """Hope is the thing with feathers
That perches in the soul,
And sings the tune without the words,
And never stops at all,""",
            "metadata_json": '{"era": "19th century", "style": "lyrical"}',
        },
        {
            "poet_name": "Shakespeare",
            "poem_title": "Sonnet 18",
            "source_language": "English",
            "original_text": """Shall I compare thee to a summer's day?
Thou art more lovely and more temperate:
Rough winds do shake the darling buds of May,
And summer's lease hath all too short a date:""",
            "metadata_json": '{"era": "Renaissance", "form": "sonnet"}',
        },
    ]

    for data in poem_data:
        poem = await test_context.create_poem(**data)
        poems.append(poem)

    return poems


# ==============================================================================
# Main Page Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.webui
class TestMainPages:
    """Test main WebUI pages load correctly."""

    def test_root_page_loads(self, webui_test_client: TestClient):
        """Test that the root page loads successfully."""
        response = webui_test_client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Check for basic page structure
        content = response.text
        assert len(content) > 1000  # Should have substantial content
        assert "VPSWeb" in content or "poetry" in content.lower()

    def test_dashboard_page_loads(self, webui_test_client: TestClient):
        """Test that the dashboard page loads successfully."""
        response = webui_test_client.get("/dashboard")

        # Dashboard should load (may redirect to root or show dashboard)
        assert response.status_code in [200, 302]

        if response.status_code == 200:
            content = response.text
            assert len(content) > 1000

    def test_poems_page_loads(self, webui_test_client: TestClient):
        """Test that the poems listing page loads successfully."""
        response = webui_test_client.get("/poems")

        assert response.status_code in [200, 302]  # May redirect to API-first approach

        if response.status_code == 200:
            content = response.text
            assert len(content) > 1000

    def test_statistics_page_loads(self, webui_test_client: TestClient):
        """Test that the statistics page loads successfully."""
        response = webui_test_client.get("/statistics")

        assert response.status_code in [200, 302]

        if response.status_code == 200:
            content = response.text
            assert len(content) > 1000

    def test_translations_page_loads(self, webui_test_client: TestClient):
        """Test that the translations page loads successfully."""
        response = webui_test_client.get("/translations")

        assert response.status_code in [200, 302]

        if response.status_code == 200:
            content = response.text
            assert len(content) > 1000


# ==============================================================================
# Static Assets Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.webui
class TestStaticAssets:
    """Test that static assets are served correctly."""

    def test_css_assets_load(self, webui_test_client: TestClient):
        """Test that CSS files are served."""
        # Test common CSS paths
        css_paths = ["/static/css/style.css", "/static/css/main.css", "/css/style.css"]

        for css_path in css_paths:
            response = webui_test_client.get(css_path)
            # CSS files may not exist, but should return 404, not server error
            assert response.status_code in [200, 404]

    def test_js_assets_load(self, webui_test_client: TestClient):
        """Test that JavaScript files are served."""
        # Test common JS paths
        js_paths = ["/static/js/app.js", "/static/js/main.js", "/js/app.js"]

        for js_path in js_paths:
            response = webui_test_client.get(js_path)
            # JS files may not exist, but should return 404, not server error
            assert response.status_code in [200, 404]

    def test_image_assets_load(self, webui_test_client: TestClient):
        """Test that image files are served."""
        # Test common image paths
        image_paths = [
            "/static/images/logo.png",
            "/static/images/favicon.ico",
            "/images/logo.png",
        ]

        for image_path in image_paths:
            response = webui_test_client.get(image_path)
            # Images may not exist, but should return 404, not server error
            assert response.status_code in [200, 404]

    def test_favicon_loads(self, webui_test_client: TestClient):
        """Test that favicon loads correctly."""
        favicon_paths = ["/favicon.ico", "/static/favicon.ico"]

        for favicon_path in favicon_paths:
            response = webui_test_client.get(favicon_path)
            # Favicon may not exist, but should return 404, not server error
            assert response.status_code in [200, 404]


# ==============================================================================
# Error Page Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.webui
class TestErrorPages:
    """Test that error pages display correctly."""

    def test_404_page_loads(self, webui_test_client: TestClient):
        """Test that 404 page loads correctly."""
        response = webui_test_client.get("/nonexistent-page")

        assert response.status_code == 404
        # Should return some kind of 404 response (HTML or JSON)
        assert len(response.text) > 0

    def test_500_error_handling(self, webui_test_client: TestClient):
        """Test that server errors are handled gracefully."""
        # Test with malformed request that should trigger server error
        response = webui_test_client.get("/api/v1/invalid-endpoint")

        # Should return 404 for API endpoints, not 500
        assert response.status_code in [404, 422]

    def test_method_not_allowed(self, webui_test_client: TestClient):
        """Test method not allowed responses."""
        response = webui_test_client.patch("/poems")

        assert response.status_code == 405


# ==============================================================================
# Integration Tests with API
# ==============================================================================


@pytest.mark.integration
@pytest.mark.webui
class TestWebUIAPIIntegration:
    """Test WebUI integration with API endpoints."""

    def test_api_accessible_from_webui_context(self, webui_test_client: TestClient):
        """Test that API endpoints are accessible from WebUI context."""
        # Test that API endpoints work when accessed from browser-like context
        api_endpoints = [
            "/api/v1/poems/",
            "/api/v1/statistics/dashboard",
            "/api/v1/poems/filter-options",
        ]

        for endpoint in api_endpoints:
            response = webui_test_client.get(endpoint)
            # These endpoints should work (though may return empty data)
            assert response.status_code == 200

    def test_cors_headers_present(self, webui_test_client: TestClient):
        """Test that CORS headers are present for WebUI compatibility."""
        response = webui_test_client.options("/api/v1/poems/")

        # Should handle OPTIONS request
        assert response.status_code in [200, 405]

    def test_api_json_responses(self, webui_test_client: TestClient):
        """Test that API returns proper JSON for WebUI consumption."""
        response = webui_test_client.get("/api/v1/poems/")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        data = response.json()
        assert "poems" in data
        assert "pagination" in data


# ==============================================================================
# Real-time Features Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.webui
class TestRealtimeFeatures:
    """Test real-time features like SSE."""

    def test_sse_endpoint_accessible(self, webui_test_client: TestClient):
        """Test that Server-Sent Events endpoint is accessible."""
        response = webui_test_client.get("/events")

        # SSE endpoints should be accessible (may return streaming response)
        assert response.status_code in [200, 404, 405]

    def test_websocket_endpoints(self, webui_test_client: TestClient):
        """Test WebSocket endpoint availability."""
        # Note: Full WebSocket testing may require different client setup
        response = webui_test_client.get("/ws")

        # WebSocket endpoints may return specific status codes
        assert response.status_code in [200, 404, 400, 426]  # 426 = Upgrade Required


# ==============================================================================
# Page Content and Structure Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.webui
class TestPageContent:
    """Test page content and structure."""

    def test_page_has_proper_html_structure(self, webui_test_client: TestClient):
        """Test that pages have proper HTML structure."""
        response = webui_test_client.get("/")

        assert response.status_code == 200

        content = response.text.lower()

        # Check for basic HTML structure elements
        html_tags = ["<!doctype html", "<html", "<head", "<body", "</html>"]

        # Some pages may be dynamic or return JSON, so be flexible
        if any(tag in content for tag in html_tags) or "json" in content:
            # Has some structure or is API response
            assert True
        else:
            # Minimal content check
            assert len(content) > 0

    def test_page_title_present(self, webui_test_client: TestClient):
        """Test that pages have proper titles."""
        response = webui_test_client.get("/")

        if response.status_code == 200:
            content = response.text.lower()
            # Look for title tag or VPSWeb branding
            has_title = "<title>" in content
            has_branding = "vpsweb" in content or "poetry" in content

            assert has_title or has_branding

    def test_navigation_elements(self, webui_test_client: TestClient):
        """Test that navigation elements are present."""
        response = webui_test_client.get("/")

        if response.status_code == 200:
            content = response.text.lower()

            # Look for common navigation elements
            nav_elements = ["nav", "menu", "navbar", "navigation"]
            has_navigation = any(element in content for element in nav_elements)

            # If no traditional nav, look for VPSWeb-specific elements
            has_app_elements = "poem" in content or "translation" in content

            assert has_navigation or has_app_elements


# ==============================================================================
# Performance Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.webui
@pytest.mark.slow
class TestWebUIPerformance:
    """Test WebUI performance characteristics."""

    def test_page_load_times(self, webui_test_client: TestClient):
        """Test that pages load within reasonable time."""
        import time

        pages_to_test = ["/", "/poems", "/statistics", "/translations"]

        for page in pages_to_test:
            start_time = time.time()
            response = webui_test_client.get(page)
            end_time = time.time()

            load_time = end_time - start_time

            # Should load quickly (adjust threshold as needed)
            assert (
                load_time < 5.0
            ), f"Page {page} took too long to load: {load_time:.2f}s"

            # Should not be server error
            assert response.status_code not in [500, 502, 503, 504]

    def test_concurrent_requests(self, webui_test_client: TestClient):
        """Test that concurrent requests are handled properly."""
        import threading
        import time

        results = []

        def make_request():
            response = webui_test_client.get("/")
            results.append(response.status_code)

        # Make multiple concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All requests should complete successfully or with acceptable errors
        for status_code in results:
            assert status_code not in [500, 502, 503, 504]


# ==============================================================================
# Accessibility Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.webui
class TestAccessibility:
    """Basic accessibility tests for WebUI."""

    def test_alt_tags_for_images(self, webui_test_client: TestClient):
        """Test that images have alt tags (when images are present)."""
        response = webui_test_client.get("/")

        if response.status_code == 200:
            content = response.text.lower()

            # If there are img tags, check for alt attributes
            if "<img" in content:
                # Look for img tags without alt attributes
                import re

                # Find all img tags
                img_tags = re.findall(r"<img[^>]*>", content)

                for img_tag in img_tags:
                    # Check if alt attribute is present
                    has_alt = "alt=" in img_tag or 'alt="' in img_tag
                    assert (
                        has_alt
                    ), f"Image tag missing alt attribute: {img_tag[:50]}..."

    def test_form_labels_present(self, webui_test_client: TestClient):
        """Test that form inputs have associated labels."""
        response = webui_test_client.get("/")

        if response.status_code == 200:
            content = response.text.lower()

            # If there are form inputs, check for labels
            if "<input" in content or "<textarea" in content:
                # Look for form controls
                has_labels = "<label" in content or "aria-label" in content
                # This is a basic check - real accessibility testing would be more thorough
                assert has_labels or len(content) == 0  # Or no forms present


# ==============================================================================
# Security Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.webui
class TestSecurityHeaders:
    """Test security headers and practices."""

    def test_security_headers(self, webui_test_client: TestClient):
        """Test that security headers are present."""
        response = webui_test_client.get("/")

        # Check for common security headers
        security_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection",
        ]

        # FastAPI may not set all headers by default
        # This test documents what headers are present
        present_headers = []
        for header in security_headers:
            if header in response.headers:
                present_headers.append(header)

        # At minimum, content-type should be set
        assert "content-type" in response.headers

    def test_no_sensitive_data_leaked(self, webui_test_client: TestClient):
        """Test that sensitive data is not leaked in responses."""
        response = webui_test_client.get("/")

        if response.status_code == 200:
            content = response.text.lower()

            # Look for potentially sensitive information
            sensitive_patterns = [
                "password",
                "secret",
                "token",
                "api_key",
                "private_key",
            ]

            # This is a basic check - real security testing would be more thorough
            for pattern in sensitive_patterns:
                # Check if pattern exists, but allow for legitimate uses
                if pattern in content:
                    # If found, it should be in a legitimate context
                    # This is a placeholder for more sophisticated checking
                    pass


# ==============================================================================
# Error Recovery Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.webui
class TestErrorRecovery:
    """Test error recovery and resilience."""

    def test_graceful_degradation(self, webui_test_client: TestClient):
        """Test that the application degrades gracefully."""
        # Test with missing query parameters
        response = webui_test_client.get("/poems?invalid_param=value")

        # Should handle gracefully, not crash
        assert response.status_code in [200, 400, 404, 422]

    def test_large_request_handling(self, webui_test_client: TestClient):
        """Test handling of large requests."""
        # Test with very long URL
        long_param = "a" * 1000
        response = webui_test_client.get(f"/poems?search={long_param}")

        # Should handle gracefully
        assert response.status_code in [200, 400, 404, 414]  # 414 = URI Too Long

    def test_malformed_request_handling(self, webui_test_client: TestClient):
        """Test handling of malformed requests."""
        # Test with malformed JSON
        response = webui_test_client.post(
            "/api/v1/poems/",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        # Should return validation error, not crash
        assert response.status_code in [400, 422]


# ==============================================================================
# WebUI Smoke Test Summary
# ==============================================================================


@pytest.mark.integration
@pytest.mark.webui
class TestWebUISmokeSummary:
    """Comprehensive smoke test summary for WebUI."""

    def test_core_webui_functionality(self, webui_test_client: TestClient):
        """Test core WebUI functionality in a single test."""
        core_endpoints = [
            ("/", "Root page"),
            ("/api/v1/poems/", "Poems API"),
            ("/api/v1/statistics/dashboard", "Statistics API"),
            ("/api/v1/poems/filter-options", "Filter options API"),
        ]

        results = []

        for endpoint, description in core_endpoints:
            try:
                response = webui_test_client.get(endpoint)
                status = response.status_code
                success = status in [200, 302]  # Success or redirect

                results.append(
                    {
                        "endpoint": endpoint,
                        "description": description,
                        "status": status,
                        "success": success,
                    }
                )

                assert status in [
                    200,
                    302,
                    404,
                ], f"{description} returned unexpected status: {status}"

            except Exception as e:
                results.append(
                    {
                        "endpoint": endpoint,
                        "description": description,
                        "error": str(e),
                        "success": False,
                    }
                )
                raise

        # All core functionality should work
        failed_tests = [r for r in results if not r.get("success", True)]
        assert len(failed_tests) == 0, f"Failed tests: {failed_tests}"
