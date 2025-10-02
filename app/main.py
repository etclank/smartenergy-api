from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from app.api.routers import api
from app.cache import get_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        await get_redis()
    except Exception:
        pass
    yield
    try:
        await close_redis()
    except Exception:
        pass


app = FastAPI(title="SmartEnergy API", version="0.1.0", lifespan=lifespan)
app.include_router(api)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "docs": "/docs", "redoc": "/redoc"}
