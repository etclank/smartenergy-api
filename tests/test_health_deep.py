# tests/test_health_deep.py
import pytest

@pytest.mark.asyncio
async def test_healthz_up(monkeypatch, client):
    """Health endpoint returns status=up and redis=up when ping succeeds."""
    class DummyRedis:
        async def ping(self): return True
    # Patch get_redis to return DummyRedis
    from app.api import health as health_mod
    async def _get_redis(): return DummyRedis()
    monkeypatch.setattr(health_mod, "get_redis", _get_redis)

    resp = await client.get("/api/health/z")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "up"
    assert data["redis"] == "up"
    assert data["docs"] == "/docs"
    assert data["redoc"] == "/redoc"


@pytest.mark.asyncio
async def test_healthz_redis_down(monkeypatch, client):
    """If Redis ping fails, redis field = down."""
    from app.api import health as health_mod

    class FailingRedis:
        async def ping(self):
            raise RuntimeError("fail")

    async def _get_redis():
        return FailingRedis()

    monkeypatch.setattr(health_mod, "get_redis", _get_redis)

    resp = await client.get("/api/health/z")
    assert resp.status_code == 200
    assert resp.json()["redis"] == "down"


@pytest.mark.asyncio
async def test_cachez_up_and_down(monkeypatch, client):
    """Test cachez() returns up and down in both cases."""
    from app.api import health as health_mod

    class DummyRedis:
        async def ping(self):
            return True

    class FailingRedis:
        async def ping(self):
            raise RuntimeError("fail")

    async def _get_ok():
        return DummyRedis()

    async def _get_bad():
        return FailingRedis()

    # up
    monkeypatch.setattr(health_mod, "get_redis", _get_ok)
    res_up = await client.get("/api/health/cachez")
    assert res_up.json()["redis"] == "up"

    # down
    monkeypatch.setattr(health_mod, "get_redis", _get_bad)
    res_down = await client.get("/api/health/cachez")
    assert res_down.json()["redis"] == "down"