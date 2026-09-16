# tests/test_metrics_tasks_retry.py
import pytest
import types
from app.tasks import metrics_tasks as mt


@pytest.mark.asyncio
async def test_record_system_metrics_success(monkeypatch):
    """Happy path: DB + Redis work and psutil returns valid stats."""

    # Dummy engine with async context
    class DummyConn:
        async def execute(self, *a, **k):
            return None

    class DummyEngine:
        def begin(self):
            return self

        async def __aenter__(self):
            return DummyConn()

        async def __aexit__(self, *a):
            pass

        async def dispose(self):
            pass

    async def _get_engine():
        return DummyEngine()

    monkeypatch.setattr(mt, "get_async_engine", lambda: DummyEngine())

    # Dummy Redis client
    class DummyRedis:
        async def ping(self):
            return True

    async def _get_redis():
        return DummyRedis()

    monkeypatch.setattr(mt, "get_redis", _get_redis)

    # Dummy psutil readings
    monkeypatch.setattr(
        mt.psutil,
        "Process",
        lambda: types.SimpleNamespace(
            oneshot=lambda self=None: self,
            memory_percent=lambda: 10.0,
            create_time=lambda: 0.0,
        ),
    )
    monkeypatch.setattr(mt.psutil, "cpu_percent", lambda interval=0.1: 5.0)

    res = await mt.record_system_metrics()
    assert res["status"] == "ok"
    assert isinstance(res["row_counts"], dict)
    assert "db_latency_ms" in res


@pytest.mark.asyncio
async def test_record_system_metrics_handles_exceptions(monkeypatch):
    """Ensure record_system_metrics() tolerates raised exceptions gracefully."""

    async def raise_runtime(*a, **k):
        raise RuntimeError("fail")

    class BrokenEngine:
        def begin(self):
            raise RuntimeError("fail")

        async def dispose(self):
            pass

    monkeypatch.setattr(mt, "get_async_engine", BrokenEngine)
    monkeypatch.setattr(mt, "get_redis", raise_runtime)
    monkeypatch.setattr(
        mt.psutil,
        "Process",
        lambda: (_ for _ in ()).throw(RuntimeError("psutil fail")),
    )

    res = await mt.record_system_metrics()
    assert res["status"] == "ok"
    assert res["db_latency_ms"] == -1 or res["redis_latency_ms"] == -1


@pytest.mark.asyncio
async def test_update_meta_cache_ok(monkeypatch):
    """update_meta_cache() writes meta:api successfully."""
    calls = {}

    class DummyRedis:
        async def set(self, key, val, ex=None):
            calls["key"] = key
            calls["val"] = val
            return True

    async def _get_redis():
        return DummyRedis()

    monkeypatch.setattr(mt, "get_redis", _get_redis)
    res = await mt.update_meta_cache()
    assert res["status"] == "ok"
    assert calls["key"] == "meta:api"


@pytest.mark.asyncio
async def test_update_meta_cache_fail(monkeypatch):
    """Handles Redis unavailable and set() failure."""

    async def _none():
        return None

    monkeypatch.setattr(mt, "get_redis", _none)
    res = await mt.update_meta_cache()
    assert res["status"] == "skip"

    class BadRedis:
        async def set(self, *a, **k):
            raise RuntimeError("boom")

    async def _bad():
        return BadRedis()

    monkeypatch.setattr(mt, "get_redis", _bad)
    res2 = await mt.update_meta_cache()
    assert res2["status"] == "error"
