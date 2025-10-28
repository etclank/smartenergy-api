# tests/test_deps_missing_user.py
import uuid
import pytest
from jose import jwt
from fastapi import HTTPException, status

from app.core import deps
from app.core.config import settings
from app.models import User


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(monkeypatch):
    """Invalid token → raises 401."""
    async def dummy_get_db():
        yield None
    token = "invalid.token"
    with pytest.raises(HTTPException) as exc:
        await deps.get_current_user(token=token, db=None)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_current_user_missing_user(monkeypatch, db_session):
    """Valid token but user not found → raises 404."""
    payload = {"sub": "ghost"}
    token = jwt.encode(payload, deps.settings.jwt_secret, algorithm=deps.settings.jwt_algorithm)
    with pytest.raises(HTTPException) as exc:
        await deps.get_current_user(token=token, db=db_session)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_current_user_success(monkeypatch, db_session):
    """Existing user returned correctly."""
    username = f"alice_{uuid.uuid4().hex[:8]}"
    user = User(username=username, email="a@a.com")
    db_session.add(user)
    await db_session.commit()

    # Build a valid token for that user
    payload = {"sub": username}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    async def _override_get_db():
        async with db_session.bind.begin() as _:
            yield db_session

    monkeypatch.setattr(deps, "get_db", _override_get_db)

    current = await deps.get_current_user(token=token, db=db_session)
    assert current.username == username
