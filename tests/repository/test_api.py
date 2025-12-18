"""
Essential health check test for VPSWeb Repository System.

Tests only the critical health endpoint functionality.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.api
@pytest.mark.unit
@pytest.mark.asyncio
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
    assert "services" in data
    assert "version" in data
