# tests/test_task_core_minimal.py
import pytest
import importlib
import types

# ---------------------------------------------------------------------
# cache_tasks
# ---------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cache_tasks_clean_and_warm(monkeypatch):
    """Ensure clean_stale_cache and warmup_cache run safely."""
    from app.tasks import cache_tasks

    class DummyRedis:
        def __init__(self):
            self.deleted = []
            self.keys = [b"cache:x", b"cache:y"]

        async def scan_iter(self, match=None):
            for k in self.keys:
                yield k

        async def delete(self, *keys):
            self.deleted.extend(keys)
            return len(keys)

    async def dummy_get_redis():
        return DummyRedis()

    # Patch get_redis and httpx.AsyncClient
    monkeypatch.setattr(cache_tasks, "get_redis", dummy_get_redis)

    # 1️⃣ clean_stale_cache
    res = await cache_tasks.clean_stale_cache("cache:*")
    assert res["status"] == "ok"
    assert res["deleted"] == 2

    # 2️⃣ warmup_cache
    class DummyResp:
        def __init__(self, status_code): self.status_code = status_code

    class DummyClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return None
        async def get(self, url): return DummyResp(200)

    monkeypatch.setattr(cache_tasks.httpx, "AsyncClient", lambda *a, **k: DummyClient())
    res2 = await cache_tasks.warmup_cache(base_url="http://test")
    assert res2["status"] in ("ok", "partial", "skip")
    assert res2["warmed"] == len(res2["errors"]) + res2["warmed"]


@pytest.mark.asyncio
async def test_cache_tasks_clean_fail(monkeypatch):
    """Ensure clean_stale_cache handles Redis unavailable or errors."""
    from app.tasks import cache_tasks

    async def bad_get_redis():
        return None  # simulate Redis unavailable instead of raising

    monkeypatch.setattr(cache_tasks, "get_redis", bad_get_redis)
    res = await cache_tasks.clean_stale_cache()
    assert res["status"] in ("skip", "error")


# ---------------------------------------------------------------------
# backup
# ---------------------------------------------------------------------
@pytest.mark.asyncio
async def test_backup_db_snapshot(monkeypatch, tmp_path):
    """Simulate DB snapshot creation and failure."""
    from app.tasks import backup
    dbfile = tmp_path / "test.db"
    dbfile.write_text("data")

    # Patch settings.database_url to point at tmp_path
    from app.core import config
    monkeypatch.setattr(config.settings, "database_url", f"sqlite+aiosqlite:///{dbfile}")

    res = await backup.backup_db_snapshot()
    assert res["status"] == "ok"
    assert "backup_file" in res


@pytest.mark.asyncio
async def test_backup_db_snapshot_error(monkeypatch):
    """Force a file creation failure to test error branch."""
    from app.tasks import backup
    from pathlib import Path
    monkeypatch.setattr(Path, "touch", lambda *a, **k: (_ for _ in ()).throw(OSError("fail")))
    from app.core import config
    monkeypatch.setattr(config.settings, "database_url", "sqlite+aiosqlite:///missing.db")
    res = await backup.backup_db_snapshot()
    assert res["status"] == "error"



# ---------------------------------------------------------------------
# email
# ---------------------------------------------------------------------
@pytest.mark.asyncio
async def test_email_send_health(monkeypatch):
    """Simulate email sending success/failure branches."""
    from app.tasks import email
    from app.core import config
    monkeypatch.setattr(config.settings, "sendgrid_api_key", "x")
    monkeypatch.setattr(config.settings, "health_email_to", "demo@example.com")

    class DummyResp:
        def __init__(self, code):
            self.status_code = code
            self.text = ""

    class DummyClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, *a, **k): return DummyResp(202)

    monkeypatch.setattr(email.httpx, "AsyncClient", lambda *a, **k: DummyClient())

    async def fake_metrics():
        return {"db_latency_ms": 1, "redis_latency_ms": 1, "row_counts": {}}

    monkeypatch.setattr(email, "record_system_metrics", fake_metrics)

    res = await email.send_health_email()
    assert res["status"] == "ok"

    # Simulate failure (exception during post)
    class FailingClient(DummyClient):
        async def post(self, *a, **k): raise RuntimeError("fail")

    monkeypatch.setattr(email.httpx, "AsyncClient", lambda *a, **k: FailingClient())
    res2 = await email.send_health_email()
    assert res2["status"] == "error"



# ---------------------------------------------------------------------
# worker
# ---------------------------------------------------------------------
def test_worker_registers_tasks(monkeypatch):
    """Ensure Celery worker loads correctly and tasks registered."""
    import app.tasks.worker as worker_mod

    class DummyCelery:
        def __init__(self, *a, **kw):
            self.conf = types.SimpleNamespace(beat_schedule={}, update=lambda **_: None)
            self.tasks = {}
            self.name = "smartenergy"

        def task(self, name=None, **_):
            def decorator(fn):
                self.tasks[name or fn.__name__] = fn
                return fn
            return decorator

        def conf_update(self, **_):
            pass

    monkeypatch.setattr(worker_mod, "Celery", DummyCelery)
    mod = importlib.reload(worker_mod)
    app = mod.celery_app
    assert hasattr(app, "tasks")
    assert "kpis.refresh" in app.tasks or "demo.generate" in app.tasks
