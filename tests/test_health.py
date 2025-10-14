# tests/test_health.py
import pytest
from fastapi import status

@pytest.mark.asyncio
async def test_healthz(client):
    """Check /api/health/z returns 200 and basic structure."""
    resp = await client.get("/api/health/z")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("ok", "up")
    assert "redis" in data  # "up" or "down"
    assert "docs" in data and "redoc" in data
