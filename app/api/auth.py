# app/api/auth.py
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.deps import get_current_user
from app.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(request: Request) -> dict[str, str]:
    """Accept JSON or form-encoded login; return a demo JWT."""
    content_type = (request.headers.get("content-type") or "").lower()
    username: str = ""

    if content_type.startswith("application/json"):
        body: Any = await request.json()
        if isinstance(body, dict):
            raw = body.get("username")
            username = raw.strip() if isinstance(raw, str) else ""
    else:
        form = await request.form()
        raw = form.get("username")
        username = raw.strip() if isinstance(raw, str) else ""

    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username required",
        )

    token = create_access_token(sub=username)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
async def me(user: str = Depends(get_current_user)) -> dict[str, str]:
    """Protected endpoint used by tests; must return username."""
    return {"username": user}
