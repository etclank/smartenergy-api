# tests/test_cache_utils_decorator.py
import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient

from app.api.utils.cache_utils import cache_response


@pytest.mark.asyncio
async def test_cache_decorator_hit_and_miss(monkeypatch):
    """Simulate cache miss then hit using fake cache_get/set."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "redis_url", "redis://test")
    store = {}

    async def fake_cache_get(key):
        return store.get(key)

    async def fake_cache_set(key, val, ttl):
        store[key] = val

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


@pytest.mark.asyncio
async def test_real_routes_cache_models_and_separate_paths_and_filters(
    client, db_session, monkeypatch
):
    from app.core.config import settings
    from app.models import Meter
    from app.api.utils import cache_utils

    monkeypatch.setattr(settings, "redis_url", "redis://test")
    store = {}
    writes = []

    async def get(key):
        return store.get(key)

    async def put(key, value, ttl):
        import json

        store[key] = json.loads(json.dumps(value))
        writes.append((key, ttl))

    monkeypatch.setattr(cache_utils, "cache_get", get)
    monkeypatch.setattr(cache_utils, "cache_set", put)
    meters = [
        Meter(
            name=f"cache-{i}",
            location="test",
            serial_number=f"cache-{i}",
            type="electric",
            site_id=1,
        )
        for i in (1, 2)
    ]
    db_session.add_all(meters)
    await db_session.commit()
    for meter in meters:
        result = await client.get(f"/api/meters/{meter.id}")
        assert result.status_code == 200
        assert result.json()["id"] == meter.id
    repeat = await client.get(f"/api/meters/{meters[0].id}")
    assert repeat.json()["id"] == meters[0].id
    assert len(writes) == 2
    for mid in (1, 2):
        assert (
            await client.get(f"/api/energy_imported/?meter_id={mid}")
        ).status_code == 200
    assert len(store) == 4
    assert all(ttl > 0 for _, ttl in writes)
