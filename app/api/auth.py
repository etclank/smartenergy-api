from fastapi import APIRouter, Depends
from app.api.schemas import LoginIn, TokenOut, UserOut
from app.security import create_access_token
from app.deps import get_current_user

router = APIRouter()

@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn):
    # Demo-only: accept any user/pass. Replace with real user lookup later.
    token = create_access_token(sub=payload.username)
    return TokenOut(access_token=token)

@router.get("/me", response_model=UserOut)
async def me(username: str = Depends(get_current_user)):
    return UserOut(username=username)
