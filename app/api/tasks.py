from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from loguru import logger

from app.core.deps import get_current_user
from app.tasks.cache_tasks import warmup_cache
from app.tasks.celery_app import celery_app

router = APIRouter(
    prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)]
)

VISIBLE_TASK_STATES = {"PENDING", "STARTED", "SUCCESS", "FAILURE"}


def enqueue_task(
    task_name: str,
    operation: str,
    *,
    args: list[Any] | None = None,
) -> dict[str, str]:
    """Publish durable work without exposing broker failures to clients."""
    try:
        result = celery_app.send_task(task_name, args=args or [])
    except Exception as exc:
        logger.warning("Task enqueue failed for {}: {}", task_name, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task broker unavailable",
        ) from exc
    return {
        "status": "accepted",
        "task_id": result.id,
        "operation": operation,
    }


@router.post("/refresh-kpis", status_code=status.HTTP_202_ACCEPTED)
async def trigger_refresh_kpis() -> dict[str, str]:
    return enqueue_task("kpis.refresh", "refresh_kpis")


@router.post("/demo/generate", status_code=status.HTTP_202_ACCEPTED)
async def trigger_generate_demo(
    days: int = Query(7, ge=1, le=31),
) -> dict[str, str]:
    return enqueue_task("demo.generate", "generate_demo_data", args=[days])


@router.post("/demo/clean", status_code=status.HTTP_202_ACCEPTED)
async def trigger_clean_demo(
    older_than_days: int = Query(30, ge=1),
) -> dict[str, str]:
    return enqueue_task("demo.clean", "clean_demo_data", args=[older_than_days])


@router.post("/cache/clean", status_code=status.HTTP_202_ACCEPTED)
async def trigger_cache_clean() -> dict[str, str]:
    return enqueue_task("cache.clean", "clean_stale_cache")


@router.post("/cache/warmup", status_code=status.HTTP_202_ACCEPTED)
async def trigger_cache_warmup(bg: BackgroundTasks) -> dict[str, str]:
    """Run explicit cache warmup as best-effort API-local work."""
    bg.add_task(warmup_cache)
    return {
        "status": "accepted",
        "operation": "warmup_cache",
        "delivery": "best_effort",
    }


@router.post("/metrics/record", status_code=status.HTTP_202_ACCEPTED)
async def trigger_metrics() -> dict[str, str]:
    return enqueue_task("metrics.record", "record_system_metrics")


@router.post("/meta/update", status_code=status.HTTP_202_ACCEPTED)
async def trigger_meta() -> dict[str, str]:
    return enqueue_task("meta.update", "update_meta_cache")


@router.post("/email/health", status_code=status.HTTP_202_ACCEPTED)
async def trigger_health_email() -> dict[str, str]:
    return enqueue_task("email.health", "send_health_email")


@router.get("/{task_id}")
async def task_status(task_id: str) -> dict[str, str]:
    """Return a bounded Celery state without task results or tracebacks."""
    try:
        state = celery_app.AsyncResult(task_id).state
    except Exception as exc:
        logger.warning("Task status lookup failed: {}", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task backend unavailable",
        ) from exc
    if state not in VISIBLE_TASK_STATES:
        state = "PENDING"
    return {"task_id": task_id, "status": state}
