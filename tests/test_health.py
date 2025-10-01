import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status
from app.main import app

transport = ASGITransport(app=app)

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/healthz")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}
