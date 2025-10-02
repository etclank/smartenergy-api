from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from app.api.routers import api
from app.cache import get_redis, close_redis

from fastapi.middleware.cors import CORSMiddleware
from app.config import settings


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

if settings.frontend_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins or ["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "docs": "/docs", "redoc": "/redoc"}
