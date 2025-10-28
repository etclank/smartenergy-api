# tests/test_security_bad_token.py
import pytest
from jose import jwt
from fastapi import HTTPException, status
from importlib import reload
from app.core import security


def test_hash_and_verify_password():
    """hash_password and verify_password are consistent."""
    pw = "abc123"
    hashed = security.hash_password(pw)
    assert security.verify_password(pw, hashed)


def test_create_access_token():
    """create_access_token produces valid JWT."""
    token = security.create_access_token("user1")
    decoded = jwt.decode(
        token,
        security.settings.jwt_secret,
        algorithms=[security.settings.jwt_algorithm],
    )
    assert decoded["sub"] == "user1"
    assert "exp" in decoded


def test_security_module_raises_without_secret(monkeypatch):
    """If JWT_SECRET is empty, importing security raises HTTPException."""
    import app.core.security as sec
    sec.settings.jwt_secret = ""  # force empty secret

    with pytest.raises(HTTPException) as exc:
        reload(sec)

    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
