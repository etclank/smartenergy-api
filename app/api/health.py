# app/api/health.py
from fastapi import APIRouter, status
from app.core.cache import get_redis

router = APIRouter()

@router.get("/healthz", status_code=status.HTTP_200_OK)
async def healthz() -> dict[str, str]:
    return {"status": "ok"}

async def ping_redis() -> bool:
    try:
        redis = await get_redis()
        return await redis.ping()
    except Exception:
        return False

@router.get("/cachez", status_code=status.HTTP_200_OK)
async def cachez() -> dict[str, str]:
    return {"redis": "up" if await ping_redis() else "down"}
