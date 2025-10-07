from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.security import create_access_token
from app.core.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
async def login(request: Request) -> dict[str, str]:
    data = await request.json()
    username = data.get("username", "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="username required")

    token = create_access_token(sub=username)
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict[str, str]:
    return {"username": user.username}
