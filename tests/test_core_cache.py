# tests/test_core_cache.py
import pytest
from types import SimpleNamespace


# ---------------------------------------------------------------------
# Dummy Redis client for mocking
# ---------------------------------------------------------------------
class DummyRedis:
    def __init__(self, *a, **kw):
        self.ping_called = False
        self.data = {}

    async def ping(self):
        self.ping_called = True
        return True

    async def close(self):
        pass

    async def get(self, key):
        return self.data.get(key)

    async def setex(self, key, ttl, value):
        self.data[key] = value


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_redis_success(monkeypatch):
    """Redis connects successfully and returns a client."""
    from app.core import cache

    cache._client = None  # reset global singleton
    monkeypatch.setattr(
        cache,
        "redis",
        SimpleNamespace(from_url=lambda *a, **k: DummyRedis()),
    )

    client = await cache.get_redis()
    assert isinstance(client, DummyRedis)
    assert client.ping_called
    assert cache._client is client  # singleton cached


@pytest.mark.asyncio
async def test_get_redis_failure(monkeypatch, capsys):
    """If Redis ping fails, get_redis() returns None gracefully."""
    from app.core import cache

    class FailingRedis(DummyRedis):
        async def ping(self):
            raise RuntimeError("boom")

    cache._client = None
    monkeypatch.setattr(
        cache,
        "redis",
        SimpleNamespace(from_url=lambda *a, **k: FailingRedis()),
    )

    client = await cache.get_redis()
    captured = capsys.readouterr().out
    assert "Redis unavailable" in captured
    assert client is None
    assert cache._client is None


@pytest.mark.asyncio
async def test_cache_set_and_get(monkeypatch):
    """Verify cache_set() and cache_get() serialize and deserialize correctly."""
    from app.core import cache

    dummy = DummyRedis()
    cache._client = dummy
    async def _get_redis(): return dummy
    monkeypatch.setattr(cache, "get_redis", _get_redis)

    payload = {"a": 1}
    await cache.cache_set("x", payload, ttl=1)
    val = await cache.cache_get("x")

    assert val == payload
    assert "x" in dummy.data


@pytest.mark.asyncio
async def test_cache_set_fail_open(monkeypatch):
    """If Redis operations raise, cache_set() fails open (no exception)."""
    from app.core import cache

    class BadRedis(DummyRedis):
        async def setex(self, *a, **k):
            raise RuntimeError("fail")

    bad = BadRedis()
    cache._client = bad

    async def _get_bad():
        return bad

    # IMPORTANT: get_redis is awaited in the code, so return an *async* function
    monkeypatch.setattr(cache, "get_redis", _get_bad)

    # Should not raise
    await cache.cache_set("key", {"b": 2}, ttl=1)


@pytest.mark.asyncio
async def test_ping_redis_true(monkeypatch):
    """ping_redis() returns True if Redis reachable."""
    from app.core import cache

    dummy = DummyRedis()
    cache._client = dummy
    async def _get_redis(): return dummy
    monkeypatch.setattr(cache, "get_redis", _get_redis)

    result = await cache.ping_redis()
    assert result is True


@pytest.mark.asyncio
async def test_ping_redis_false(monkeypatch):
    """ping_redis() returns False if Redis unavailable."""
    from app.core import cache

    cache._client = None

    async def _get_none():
        return None

    monkeypatch.setattr(cache, "get_redis", _get_none)
    result = await cache.ping_redis()
    assert result is False
