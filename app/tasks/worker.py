from __future__ import annotations

import asyncio
import os
from typing import Any, Coroutine

from app.core.cache import close_redis
from app.core.logging import setup_logging
from app.tasks.cache_tasks import clean_stale_cache
from app.tasks.celery_app import celery_app
from app.tasks.demo_data import generate_demo_data, clean_demo_data
from app.tasks.email import send_health_email
from app.tasks.metrics_tasks import record_system_metrics, update_meta_cache
from app.tasks.refresh_kpis import refresh_kpis


setup_logging(os.getenv("ROLE", "worker"))


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
@celery_app.task(name="system.ping")
def t_ping(value: str = "pong") -> dict[str, str]:
    """Deterministic broker/worker/result-backend integration probe."""
    return {"status": "ok", "value": value}


@celery_app.task(name="kpis.refresh")
def t_refresh_kpis() -> dict[str, Any]:
    return run_async(refresh_kpis())


@celery_app.task(name="demo.generate")
def t_generate_demo(days: int = 7) -> dict[str, Any]:
    return run_async(generate_demo_data(days))


@celery_app.task(name="demo.clean")
def t_clean_demo(older_than_days: int = 30) -> dict[str, Any]:
    return run_async(clean_demo_data(older_than_days))


@celery_app.task(name="cache.clean")
def t_clean_cache() -> dict[str, Any]:
    return run_async(clean_stale_cache())


@celery_app.task(name="metrics.record")
def t_record_metrics() -> dict[str, Any]:
    return run_async(record_system_metrics())


@celery_app.task(name="meta.update")
def t_update_meta() -> dict[str, Any]:
    return run_async(update_meta_cache())


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
    "cache-clean-daily": {
        "task": "cache.clean",
        "schedule": 60 * 60 * 24,
        "options": {"expires": 60 * 60},
    },
    "metrics-every-10m": {
        "task": "metrics.record",
        "schedule": 600,
        "options": {"expires": 9 * 60},
    },
}
