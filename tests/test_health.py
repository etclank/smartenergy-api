# tests/test_health.py
import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_healthz(client):
    """Check /api/health/z returns status ok."""
    resp = await client.get("/api/health/z")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_cachez(client):
    """Check /api/health/cachez returns redis status."""
    resp = await client.get("/api/health/cachez")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "redis" in data
    assert data["redis"] in ("up", "down")
