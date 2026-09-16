from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.core.config import settings

if not settings.jwt_secret:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="JWT_SECRET is not configured",
    )

if settings.env == "prod" and len(settings.jwt_secret) < 32:
    raise RuntimeError("JWT_SECRET must contain at least 32 characters in production")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(p: str) -> str:
    return pwd_context.hash(p)


def verify_password(p: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(p, hashed)
    except (ValueError, TypeError):
        return False


def create_access_token(sub: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": sub, "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
