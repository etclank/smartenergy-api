# app/main.py
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import api
from app.api.metrics import REQUEST_COUNT, REQUEST_LATENCY
import time
from app.core.logging import setup_logging
from app.core.cache import get_redis, close_redis
from app.core.config import settings
from app.core.db import engine
from app.core import telemetry
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable, Awaitable
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        await get_redis()
    except Exception:
        pass
    try:
        yield
    finally:
        await close_redis()
        await engine.dispose()


setup_logging()  # 🔹 initialize global logger

app = FastAPI(title="SmartEnergy API", version="0.1.0", lifespan=lifespan)


# ✅ Global metrics middleware
@app.middleware("http")
async def prometheus_metrics_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    latency = time.perf_counter() - start

    method = request.method
    route = request.scope.get("route")
    path = getattr(route, "path", "unmatched")
    status = response.status_code

    if "REQUEST_COUNT" in globals():
        REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
    if "REQUEST_LATENCY" in globals():
        REQUEST_LATENCY.labels(method=method, path=path).observe(latency)

    return response


# Initialize OpenTelemetry if enabled
telemetry.init_telemetry(app)

if settings.frontend_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api)

# Static site
app.mount("/site", StaticFiles(directory="site", html=True), name="site")

logger.info("SmartEnergy API startup complete")


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/site/")
