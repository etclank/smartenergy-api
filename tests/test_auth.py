import pytest
from jose import jwt
from fastapi import status
from app.core.config import settings
from app.models import User
from app.core.security import hash_password


@pytest.mark.asyncio
async def test_login_and_me(client, db_session):
    """Ensure /api/auth/login issues a JWT and /api/auth/me validates it."""

    # Create a user in the test DB
    user = User(
        username="alice",
        email="alice@example.com",
        hashed_password=hash_password("secret"),
    )
    db_session.add(user)
    await db_session.commit()

    # Login
    login_data = {"username": "alice", "password": "secret"}
    resp = await client.post("/api/auth/login", json=login_data)
    assert resp.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)

    token = resp.json()["access_token"]

    # Verify token manually
    decoded = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    assert decoded["sub"] == "alice"

    # Call /me
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = await client.get("/api/auth/me", headers=headers)

    assert me_resp.status_code == status.HTTP_200_OK
    assert me_resp.json() == {"username": "alice"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"username": "alice", "password": "wrong"}, 401),
        ({"username": "unknown", "password": "wrong"}, 401),
        ({"username": "alice"}, 422),
        ({"username": "", "password": "x"}, 422),
        ([], 422),
    ],
)
async def test_login_rejects_invalid_credentials(client, payload, expected):
    response = await client.post("/api/auth/login", json=payload)
    assert response.status_code == expected
    assert "access_token" not in response.json()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/meters/",
        "/api/tasks/refresh-kpis",
        "/api/tasks/demo/generate",
        "/api/tasks/demo/clean",
        "/api/tasks/cache/clean",
        "/api/tasks/cache/warmup",
        "/api/tasks/metrics/record",
        "/api/tasks/meta/update",
        "/api/tasks/email/health",
    ],
)
async def test_writes_require_authentication(client, path):
    response = await client.post(path, json={})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_task_day_limits(authenticated_client):
    for path in [
        "demo/generate?days=0",
        "demo/generate?days=32",
        "demo/clean?older_than_days=-1",
    ]:
        response = await authenticated_client.post("/api/tasks/" + path)
        assert response.status_code == 422
