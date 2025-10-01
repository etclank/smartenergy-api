import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status
from app.main import app

transport = ASGITransport(app=app)

@pytest.mark.asyncio
async def test_login_and_me():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # login
        resp = await ac.post("/auth/login", json={"username": "alice", "password": "secret"})
        assert resp.status_code == status.HTTP_200_OK
        token = resp.json()["access_token"]

        # me (protected)
        headers = {"Authorization": f"Bearer {token}"}
        me_resp = await ac.get("/auth/me", headers=headers)
        assert me_resp.status_code == status.HTTP_200_OK
        assert me_resp.json()["username"] == "alice"
