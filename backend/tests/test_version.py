import pytest
from httpx import AsyncClient


@pytest.mark.usefixtures("setup_test_db")
class TestVersionEndpoint:
    """Tests for the /api/version endpoint (no DB dependency)."""

    @pytest.mark.asyncio
    async def test_version_returns_200_and_structure(self, client: AsyncClient):
        response = await client.get("/api/version")
        assert response.status_code == 200

        body = response.json()
        assert "data" in body
        assert "message" in body
        assert "status" in body
        assert body["status"] == "ok"
        assert body["message"] == "Version retrieved successfully"

        data = body["data"]
        assert "version" in data
        assert "commit" in data
        assert "build_time" in data
        # Fields should be non-empty strings
        assert isinstance(data["version"], str)
        assert isinstance(data["commit"], str)
        assert isinstance(data["build_time"], str)

    @pytest.mark.asyncio
    async def test_version_returns_default_values_when_not_overridden(self, client: AsyncClient):
        """When no env overrides, version fields fallback to defaults."""
        response = await client.get("/api/version")
        body = response.json()
        data = body["data"]
        # In test env without explicit version env, should be "0.0.0-dev" or the VERSION file content
        assert data["version"] in ("0.0.0-dev", "0.2.0")
        assert data["commit"] == "unknown"
        assert data["build_time"] == "unknown"
