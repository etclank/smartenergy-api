from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import status

from app.api import tasks


@pytest.fixture()
def dispatched(monkeypatch):
    calls: list[tuple[str, list[object]]] = []

    def send_task(name: str, args: list[object]):
        calls.append((name, args))
        return SimpleNamespace(id=f"task-{len(calls)}")

    monkeypatch.setattr(tasks.celery_app, "send_task", send_task)
    return calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "task_name", "args", "operation"),
    [
        ("refresh-kpis", "kpis.refresh", [], "refresh_kpis"),
        ("demo/generate?days=2", "demo.generate", [2], "generate_demo_data"),
        ("demo/clean?older_than_days=3", "demo.clean", [3], "clean_demo_data"),
        ("cache/clean", "cache.clean", [], "clean_stale_cache"),
        ("metrics/record", "metrics.record", [], "record_system_metrics"),
        ("meta/update", "meta.update", [], "update_meta_cache"),
        ("email/health", "email.health", [], "send_health_email"),
    ],
)
async def test_durable_task_endpoints_enqueue_celery(
    authenticated_client, dispatched, path, task_name, args, operation
):
    response = await authenticated_client.post(f"/api/tasks/{path}")

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {
        "status": "accepted",
        "task_id": "task-1",
        "operation": operation,
    }
    assert dispatched == [(task_name, args)]


@pytest.mark.asyncio
async def test_enqueue_failure_is_controlled(authenticated_client, monkeypatch):
    def fail(*_args, **_kwargs):
        raise RuntimeError("redis://user:secret@private.example/1")

    monkeypatch.setattr(tasks.celery_app, "send_task", fail)
    response = await authenticated_client.post("/api/tasks/refresh-kpis")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"detail": "Task broker unavailable"}
    assert "secret" not in response.text


@pytest.mark.asyncio
async def test_cache_warmup_remains_explicit_best_effort(
    authenticated_client, monkeypatch
):
    calls = 0

    async def warmup() -> dict[str, str]:
        nonlocal calls
        calls += 1
        return {"status": "ok"}

    monkeypatch.setattr(tasks, "warmup_cache", warmup)
    response = await authenticated_client.post("/api/tasks/cache/warmup")

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {
        "status": "accepted",
        "operation": "warmup_cache",
        "delivery": "best_effort",
    }
    assert calls == 1


@pytest.mark.asyncio
async def test_task_status_is_bounded(authenticated_client, monkeypatch):
    monkeypatch.setattr(
        tasks.celery_app,
        "AsyncResult",
        lambda _task_id: SimpleNamespace(state="RETRY", result="do not expose"),
    )
    response = await authenticated_client.get("/api/tasks/task-123")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"task_id": "task-123", "status": "PENDING"}


@pytest.mark.asyncio
async def test_task_status_backend_failure_is_controlled(
    authenticated_client, monkeypatch
):
    def fail(_task_id):
        raise RuntimeError("sensitive backend failure")

    monkeypatch.setattr(tasks.celery_app, "AsyncResult", fail)
    response = await authenticated_client.get("/api/tasks/task-123")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"detail": "Task backend unavailable"}
    assert "sensitive" not in response.text
