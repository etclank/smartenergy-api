from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas.auth import LoginIn, TokenOut
from app.core.security import create_access_token, verify_password
from app.core.deps import get_current_user, get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    user = await db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenOut(access_token=create_access_token(sub=user.username))


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict[str, str]:
    return {"username": user.username}
