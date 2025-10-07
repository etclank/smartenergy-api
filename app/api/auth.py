# app/api/auth.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.deps import get_current_user
from app.core.security import create_access_token

# No prefix — we mount absolute paths to match the tests (/auth/login, /auth/me)
router = APIRouter(tags=["auth"])


@router.post("/auth/login")
async def login(request: Request) -> dict[str, str]:
    """
    Accepts JSON: {"username": "...", "password": "..."} or form-encoded.
    Returns {"access_token": "...", "token_type": "bearer"}.
    """
    content_type = request.headers.get("content-type") or ""
    username = ""

    if content_type.startswith("application/json"):
        body = await request.json()
        if isinstance(body, dict):
            raw = body.get("username")
            if isinstance(raw, str):
                username = raw.strip()
    else:
        form = await request.form()
        raw = form.get("username")
        if isinstance(raw, str):
            username = raw.strip()

    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="username required"
        )

    token = create_access_token(sub=username)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/me")
async def me(user: str = Depends(get_current_user)) -> dict[str, str]:
    """Returns {"username": "<subject>"} for a valid Bearer token."""
    return {"username": user}
