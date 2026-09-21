import asyncio

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import text

from app.core.cache import get_redis
from app.core.db import engine

router = APIRouter(prefix="/health", tags=["health"])
READINESS_TIMEOUT_SECONDS = 2.0


async def database_ping() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


@router.get("/z", status_code=status.HTTP_200_OK)
async def healthz() -> dict[str, str]:
    """Process/cache health endpoint used by containers and the dashboard."""
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


@router.get("/readyz", response_model=None)
async def readyz() -> dict[str, str] | JSONResponse:
    """Report readiness from a bounded PostgreSQL-compatible database query."""
    try:
        await asyncio.wait_for(
            database_ping(),
            timeout=READINESS_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.warning("Database readiness failed: {}", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "database": "unavailable"},
        )
    return {"status": "ready"}
