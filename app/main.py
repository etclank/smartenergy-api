from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from app.api.routers import api
from app.core.cache import get_redis, close_redis

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.core.config import settings


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

# Serve the static demo site
app.mount("/site", StaticFiles(directory="site", html=True), name="site")


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/site/")
