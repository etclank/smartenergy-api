# app/api/system_metrics.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db
from app.models.system_metrics import SystemMetrics
from typing import Any

router = APIRouter(prefix="/system_metrics", tags=["system_metrics"])

@router.get("/", summary="List all system metrics", response_model=list[dict])
async def list_system_metrics(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    res = await db.execute(select(SystemMetrics).order_by(SystemMetrics.id.desc()).limit(100))
    rows = res.scalars().all()
    return [
        {
            "timestamp": m.timestamp.isoformat(),
            "db_latency_ms": m.db_latency_ms,
            "redis_latency_ms": m.redis_latency_ms,
            "cpu_percent": m.cpu_percent,
            "mem_percent": m.mem_percent,
            "uptime_seconds": m.uptime_seconds,
            "row_counts": m.row_counts,
        }
        for m in reversed(rows)  # oldest first for chart order
    ]

@router.get("/latest", summary="Get latest system metric", response_model=dict)
async def latest_system_metric(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    res = await db.execute(select(SystemMetrics).order_by(SystemMetrics.id.desc()).limit(1))
    m = res.scalars().first()
    if not m:
        return {"status": "empty"}
    return {
        "timestamp": m.timestamp.isoformat(),
        "db_latency_ms": m.db_latency_ms,
        "redis_latency_ms": m.redis_latency_ms,
        "cpu_percent": m.cpu_percent,
        "mem_percent": m.mem_percent,
        "uptime_seconds": m.uptime_seconds,
        "row_counts": m.row_counts,
    }
