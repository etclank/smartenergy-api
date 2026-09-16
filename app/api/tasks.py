from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, status, Depends, Query
from app.core.deps import get_current_user
from app.tasks.refresh_kpis import refresh_kpis
from app.tasks.demo_data import generate_demo_data, clean_demo_data
from app.tasks.cache_tasks import clean_stale_cache, warmup_cache
from app.tasks.metrics_tasks import record_system_metrics, update_meta_cache
from app.tasks.backup import backup_db_snapshot
from app.tasks.email import send_health_email

router = APIRouter(
    prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)]
)


# -------------------------------------------------------------------------
# 1️⃣ KPI Tasks
# -------------------------------------------------------------------------
@router.post("/refresh-kpis", status_code=status.HTTP_202_ACCEPTED)
async def trigger_refresh_kpis(bg: BackgroundTasks) -> dict:
    """
    Aggregate daily KPIs and upsert into summary_kpi.
    """
    bg.add_task(refresh_kpis)
    return {"queued": "refresh_kpis"}


# -------------------------------------------------------------------------
# 2️⃣ Demo Data Lifecycle
# -------------------------------------------------------------------------
@router.post("/demo/generate", status_code=status.HTTP_202_ACCEPTED)
async def trigger_generate_demo(
    bg: BackgroundTasks, days: int = Query(7, ge=1, le=31)
) -> dict:
    """
    Generate new demo readings (extends existing demo dataset).
    """
    bg.add_task(generate_demo_data, days)
    return {"queued": "generate_demo_data", "days": days}


@router.post("/demo/clean", status_code=status.HTTP_202_ACCEPTED)
async def trigger_clean_demo(
    bg: BackgroundTasks, older_than_days: int = Query(30, ge=1)
) -> dict:
    """
    Delete demo data older than N days (rolling demo window).
    """
    bg.add_task(clean_demo_data, older_than_days)
    return {"queued": "clean_demo_data", "older_than_days": older_than_days}


# -------------------------------------------------------------------------
# 3️⃣ Cache Lifecycle
# -------------------------------------------------------------------------
@router.post("/cache/clean", status_code=status.HTTP_202_ACCEPTED)
async def trigger_cache_clean(bg: BackgroundTasks) -> dict:
    """
    Remove all cache:* entries from Redis.
    """
    bg.add_task(clean_stale_cache)
    return {"queued": "clean_stale_cache"}


@router.post("/cache/warmup", status_code=status.HTTP_202_ACCEPTED)
async def trigger_cache_warmup(bg: BackgroundTasks) -> dict:
    """
    Preload cache for common read endpoints.
    """
    bg.add_task(warmup_cache)
    return {"queued": "warmup_cache"}


# -------------------------------------------------------------------------
# 4️⃣ System Metrics + Meta Cache
# -------------------------------------------------------------------------
@router.post("/metrics/record", status_code=status.HTTP_202_ACCEPTED)
async def trigger_metrics(bg: BackgroundTasks) -> dict:
    """
    Record DB + Redis latency and table counts to system_metrics.
    """
    bg.add_task(record_system_metrics)
    return {"queued": "record_system_metrics"}


@router.post("/meta/update", status_code=status.HTTP_202_ACCEPTED)
async def trigger_meta(bg: BackgroundTasks) -> dict:
    """
    Update Redis meta:api cache with current API state.
    """
    bg.add_task(update_meta_cache)
    return {"queued": "update_meta_cache"}


# -------------------------------------------------------------------------
# 5 Operational tasks
# -------------------------------------------------------------------------
@router.post("/backup/db", status_code=status.HTTP_202_ACCEPTED)
async def trigger_backup(bg: BackgroundTasks) -> dict:
    bg.add_task(backup_db_snapshot)
    return {"queued": "backup_db_snapshot"}


@router.post("/email/health", status_code=status.HTTP_202_ACCEPTED)
async def trigger_health_email(bg: BackgroundTasks) -> dict:
    bg.add_task(send_health_email)
    return {"queued": "send_health_email"}
