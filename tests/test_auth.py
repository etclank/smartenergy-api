import pytest
from jose import jwt
from fastapi import status
from app.core.config import settings
from app.models import User


@pytest.mark.asyncio
async def test_login_and_me(client, db_session):
    """Ensure /api/auth/login issues a JWT and /api/auth/me validates it."""

    # Create a user in the test DB
    user = User(username="alice", email="alice@example.com")
    db_session.add(user)
    await db_session.commit()

    # Login
    login_data = {"username": "alice", "password": "secret"}
    resp = await client.post("/api/auth/login", json=login_data)
    assert resp.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)

    token = resp.json()["access_token"]

    # Verify token manually
    decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert decoded["sub"] == "alice"

    # Call /me
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = await client.get("/api/auth/me", headers=headers)

    assert me_resp.status_code == status.HTTP_200_OK
    assert me_resp.json() == {"username": "alice"}
