# tests/test_cache_utils_decorator.py
import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient

from app.api.utils.cache_utils import cache_response

@pytest.mark.asyncio
async def test_cache_decorator_hit_and_miss(monkeypatch):
    """Simulate cache miss then hit using fake cache_get/set."""
    store = {}

    async def fake_cache_get(key): return store.get(key)
    async def fake_cache_set(key, val, ttl): store[key] = val

    monkeypatch.setattr("app.api.utils.cache_utils.cache_get", fake_cache_get)
    monkeypatch.setattr("app.api.utils.cache_utils.cache_set", fake_cache_set)

    app = FastAPI()

    calls = {"count": 0}

    @app.get("/cached")
    @cache_response(ttl=10)
    async def cached_route(request: Request):
        calls["count"] += 1
        return {"ok": True, "count": calls["count"]}

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # First request → miss
        r1 = await ac.get("/cached")
        assert r1.json()["count"] == 1
        # Second request → hit (count unchanged)
        r2 = await ac.get("/cached")
        assert r2.json()["count"] == 1

        # Simulate bypass by deleting cache
        store.clear()
        r3 = await ac.get("/cached?new=true")
        assert r3.json()["count"] == 2


@pytest.mark.asyncio
async def test_cache_decorator_no_redis(monkeypatch):
    """If redis_url disabled, decorator calls underlying func directly."""
    from app.api.utils import cache_utils as cu
    monkeypatch.setattr(cu.settings, "redis_url", "")
    calls = {"count": 0}

    @cache_response(ttl=1)
    async def handler(request: Request):
        calls["count"] += 1
        return {"x": calls["count"]}

    # Direct call simulating FastAPI dependency
    result = await handler(request=Request(scope={"type": "http"}))
    assert result == {"x": 1}
