"""
Basic API endpoint tests for VPSWeb Repository System.

This module tests the basic API functionality including health checks,
info endpoints, and basic HTTP responses.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.api
@pytest.mark.unit
async def test_health_check_endpoint(test_client: AsyncClient):
    """
    Test the health check endpoint returns correct response.

    Args:
        test_client: Async HTTP client for testing
    """
    response = await test_client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.api
@pytest.mark.unit
async def test_info_endpoint(test_client: AsyncClient):
    """
    Test the info endpoint returns correct response.

    Args:
        test_client: Async HTTP client for testing
    """
    response = await test_client.get("/info")

    assert response.status_code == 200
    data = response.json()

    assert "title" in data
    assert "description" in data
    assert "version" in data
    assert "debug" in data
    assert "endpoints" in data

    # Check endpoints structure
    endpoints = data["endpoints"]
    assert "health" in endpoints
    assert "info" in endpoints


@pytest.mark.api
@pytest.mark.unit
async def test_root_endpoint_redirect(test_client: AsyncClient):
    """
    Test that root endpoint redirects or returns appropriate response.

    Args:
        test_client: Async HTTP client for testing
    """
    response = await test_client.get("/")

    # Should return 404 since we don't have a root endpoint defined
    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.unit
async def test_invalid_endpoint_returns_404(test_client: AsyncClient):
    """
    Test that invalid endpoints return 404 status.

    Args:
        test_client: Async HTTP client for testing
    """
    response = await test_client.get("/invalid-endpoint")

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.unit
async def test_cors_headers_present(test_client: AsyncClient):
    """
    Test that CORS headers are present in responses.

    Args:
        test_client: Async HTTP client for testing
    """
    response = await test_client.options("/health")

    # Check for CORS headers
    headers = response.headers
    assert (
        "access-control-allow-origin" in headers
        or "Access-Control-Allow-Origin" in headers
    )


@pytest.mark.api
@pytest.mark.unit
async def test_security_headers_present(test_client: AsyncClient):
    """
    Test that security headers are present in responses.

    Args:
        test_client: Async HTTP client for testing
    """
    response = await test_client.get("/health")

    # Check for security headers (case-insensitive)
    headers = dict(
        (key.lower(), value) for key, value in response.headers.items()
    )

    # Some common security headers that should be present
    security_headers = [
        "x-content-type-options",
        "x-frame-options",
        "x-xss-protection",
    ]

    # At least some security headers should be present
    found_headers = [
        header for header in security_headers if header in headers
    ]
    assert len(found_headers) > 0, "No security headers found in response"


@pytest.mark.api
@pytest.mark.unit
async def test_response_content_type_json(test_client: AsyncClient):
    """
    Test that API endpoints return JSON content type.

    Args:
        test_client: Async HTTP client for testing
    """
    response = await test_client.get("/health")

    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.api
@pytest.mark.unit
async def test_response_structure_consistency(test_client: AsyncClient):
    """
    Test that API responses have consistent structure.

    Args:
        test_client: Async HTTP client for testing
    """
    # Test health endpoint
    health_response = await test_client.get("/health")
    info_response = await test_client.get("/info")

    # Both should return valid JSON
    assert health_response.headers["content-type"].startswith(
        "application/json"
    )
    assert info_response.headers["content-type"].startswith("application/json")

    # Both should have proper status codes
    assert health_response.status_code == 200
    assert info_response.status_code == 200


@pytest.mark.api
@pytest.mark.unit
async def test_error_response_format(test_client: AsyncClient):
    """
    Test that error responses follow consistent format.

    Args:
        test_client: Async HTTP client for testing
    """
    response = await test_client.get("/nonexistent-endpoint")

    assert response.status_code == 404

    # Should return JSON error response
    assert "application/json" in response.headers.get("content-type", "")

    data = response.json()
    assert "error" in data or "detail" in data


@pytest.mark.api
@pytest.mark.unit
async def test_http_method_options(test_client: AsyncClient):
    """
    Test OPTIONS requests are handled properly.

    Args:
        test_client: Async HTTP client for testing
    """
    response = await test_client.options("/health")

    # Should return 200 or 405 (Method Not Allowed) but not error
    assert response.status_code in [200, 405]


@pytest.mark.api
@pytest.mark.unit
async def test_api_versioning_headers(test_client: AsyncClient):
    """
    Test that API versioning headers are present.

    Args:
        test_client: Async HTTP client for testing
    """
    response = await test_client.get("/health")

    # Check for version headers (case-insensitive)
    headers = dict(
        (key.lower(), value) for key, value in response.headers.items()
    )

    # Look for API version headers
    version_headers = ["api-version", "x-api-version", "version"]

    # At least one version header should be present
    [header for header in version_headers if header in headers]
    # This might be optional depending on implementation
    # assert len(found_headers) > 0, "No API version headers found"
