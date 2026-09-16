from __future__ import annotations

import asyncio
from celery import Celery
from app.core.config import settings
from app.core.cache import close_redis
from app.tasks.refresh_kpis import refresh_kpis
from app.tasks.demo_data import generate_demo_data, clean_demo_data
from app.tasks.cache_tasks import clean_stale_cache, warmup_cache
from app.tasks.metrics_tasks import record_system_metrics, update_meta_cache
from app.tasks.backup import backup_db_snapshot
from app.tasks.email import send_health_email
from typing import Any, Coroutine


# ----------------------------------------------------------------------
# Celery configuration
# ----------------------------------------------------------------------
celery_app = Celery(
    "smartenergy",
    broker=settings.celery_broker_url or settings.redis_url,
    backend=settings.celery_result_backend or settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


# Helper to run async functions inside Celery worker
def run_async(coro: Coroutine[Any, Any, dict[str, Any]]) -> dict[str, Any]:
    async def execute() -> dict[str, Any]:
        try:
            return await coro
        finally:
            await close_redis()

    return asyncio.run(execute())


# ----------------------------------------------------------------------
# Task wrappers
# ----------------------------------------------------------------------
@celery_app.task(name="kpis.refresh")
def t_refresh_kpis() -> dict[str, Any]:
    return run_async(refresh_kpis())


@celery_app.task(name="demo.generate")
def t_generate_demo() -> dict[str, Any]:
    return run_async(generate_demo_data())


@celery_app.task(name="demo.clean")
def t_clean_demo() -> dict[str, Any]:
    return run_async(clean_demo_data())


@celery_app.task(name="cache.clean")
def t_clean_cache() -> dict[str, Any]:
    return run_async(clean_stale_cache())


@celery_app.task(name="cache.warmup")
def t_warmup_cache() -> dict[str, Any]:
    return run_async(warmup_cache())


@celery_app.task(name="metrics.record")
def t_record_metrics() -> dict[str, Any]:
    return run_async(record_system_metrics())


@celery_app.task(name="meta.update")
def t_update_meta() -> dict[str, Any]:
    return run_async(update_meta_cache())


@celery_app.task(name="backup.db")
def t_backup_db() -> dict[str, Any]:
    return run_async(backup_db_snapshot())


@celery_app.task(name="email.health")
def t_health_email() -> dict[str, Any]:
    return run_async(send_health_email())


# ----------------------------------------------------------------------
# Celery Beat schedule (code-based)
# ----------------------------------------------------------------------
celery_app.conf.beat_schedule = {
    "kpis-refresh-daily": {
        "task": "kpis.refresh",
        "schedule": 60 * 60 * 24,  # every 24 h
        "options": {"expires": 60 * 60},
    },
    "demo-generate-weekly": {
        "task": "demo.generate",
        "schedule": 60 * 60 * 24 * 7,
    },
    "demo-clean-weekly": {
        "task": "demo.clean",
        "schedule": 60 * 60 * 24 * 7,
    },
    "cache-clean-daily": {
        "task": "cache.clean",
        "schedule": 60 * 60 * 24,
    },
    "cache-warmup-daily": {
        "task": "cache.warmup",
        "schedule": 60 * 60 * 24,
    },
    "metrics-every-10m": {
        "task": "metrics.record",
        "schedule": 600,
    },
    "meta-update-hourly": {
        "task": "meta.update",
        "schedule": 3600,
    },
    "backup-db-daily": {
        "task": "backup.db",
        "schedule": 60 * 60 * 24,
    },
    "health-email-daily": {
        "task": "email.health",
        "schedule": 60 * 60 * 24,
    },
}
