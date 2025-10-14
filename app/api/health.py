# app/api/health.py (final aligned)
from fastapi import APIRouter, status
from app.core.cache import get_redis

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/z", status_code=status.HTTP_200_OK)
async def healthz() -> dict[str, str]:
    """Global health endpoint (used by Render + frontend badges)."""
    redis_status = "down"
    try:
        client = await get_redis()
        if client:
            await client.ping()
            redis_status = "up"
    except Exception:
        redis_status = "down"

    return {
        "status": "up",
        "redis": redis_status,
        "docs": "/docs",
        "redoc": "/redoc",
    }


@router.get("/cachez", status_code=status.HTTP_200_OK)
async def cachez() -> dict[str, str]:
    """Dedicated Redis health endpoint."""
    try:
        client = await get_redis()
        if client:
            await client.ping()
            return {"redis": "up"}
    except Exception:
        pass
    return {"redis": "down"}
