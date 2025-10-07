# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import api
from app.core.cache import get_redis, close_redis
from app.core.config import settings
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from typing import AsyncIterator


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
        allow_origins=settings.frontend_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

def print_router_tree(router: FastAPI, prefix: str = "") -> None:
    for r in router.routes:
        if hasattr(r, "path"):
            print(f"🔍 Router path: {prefix}{r.path}")
    for sub_router in getattr(router, "routes", []):
        if hasattr(sub_router, "router"):
            print_router_tree(sub_router.router, prefix=prefix + sub_router.path)

# ✅ include only unified /api router
app.include_router(api)
print_router_tree(app)

# Static site
app.mount("/site", StaticFiles(directory="site", html=True), name="site")

@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/site/")


for route in app.routes:
    if hasattr(route, "path"):
        print("✅ Registered route:", route.path)
