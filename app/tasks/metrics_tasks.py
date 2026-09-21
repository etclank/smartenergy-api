# app/tasks/metrics_tasks.py
from __future__ import annotations

import time
import json
from datetime import datetime
from sqlalchemy import text, select, func
from app.core.db import get_async_engine, async_sessionmaker_dep
from app.core.cache import get_redis
from app.core.config import settings
import psutil
from app.models import (
    SystemMetrics,
    Site,
    Meter,
    EnergyImported,
    EnergyExported,
    EnergyReactive,
    MaxPower,
)


async def record_system_metrics() -> dict:
    """
    Measure database, Redis latency, row counts,
    and process stats (CPU %, memory %, uptime seconds).
    """
    engine = get_async_engine()
    SessionLocal = async_sessionmaker_dep(engine)
    try:
        db_ms = redis_ms = -1
        counts: dict[str, int] = {}

        # --------------------------------------------------
        # DB ping
        # --------------------------------------------------
        try:
            t0 = time.perf_counter()
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            db_ms = int(1000 * (time.perf_counter() - t0))
        except Exception:
            db_ms = -1

        # --------------------------------------------------
        # Redis ping
        # --------------------------------------------------
        try:
            r = await get_redis()
            if r:
                t1 = time.perf_counter()
                await r.ping()
                redis_ms = int(1000 * (time.perf_counter() - t1))
        except Exception:
            redis_ms = -1

        # --------------------------------------------------
        # Process stats via psutil
        # --------------------------------------------------
        try:
            proc = psutil.Process()
            with proc.oneshot():
                cpu_percent = psutil.cpu_percent(interval=0.1)
                mem_percent = proc.memory_percent()
                uptime_seconds = time.time() - proc.create_time()
        except Exception:
            cpu_percent = mem_percent = uptime_seconds = None

        # --------------------------------------------------
        # Row counts + insert metrics record
        # --------------------------------------------------
        try:
            async with SessionLocal() as db:
                counts = {
                    "sites": (await db.execute(select(func.count(Site.id)))).scalar()
                    or 0,
                    "meters": (await db.execute(select(func.count(Meter.id)))).scalar()
                    or 0,
                    "energy_imported": (
                        await db.execute(select(func.count(EnergyImported.id)))
                    ).scalar()
                    or 0,
                    "energy_exported": (
                        await db.execute(select(func.count(EnergyExported.id)))
                    ).scalar()
                    or 0,
                    "energy_reactive": (
                        await db.execute(select(func.count(EnergyReactive.id)))
                    ).scalar()
                    or 0,
                    "max_power": (
                        await db.execute(select(func.count(MaxPower.id)))
                    ).scalar()
                    or 0,
                }

                db.add(
                    SystemMetrics(
                        db_latency_ms=db_ms,
                        redis_latency_ms=redis_ms,
                        row_counts=counts,
                        cpu_percent=cpu_percent,
                        mem_percent=mem_percent,
                        uptime_seconds=uptime_seconds,
                    )
                )
                await db.commit()
        except Exception:
            pass  # Safe fail-open

        # --------------------------------------------------
        # Return summary
        # --------------------------------------------------
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "db_latency_ms": db_ms,
            "redis_latency_ms": redis_ms,
            "cpu_percent": cpu_percent,
            "mem_percent": mem_percent,
            "uptime_seconds": uptime_seconds,
            "row_counts": counts,
        }

    finally:
        await engine.dispose()


async def update_meta_cache() -> dict:
    """
    Update Redis 'meta:api' key with high-level API status metadata.
    Used by /api/meta and /site status page.
    """
    r = await get_redis()
    if not r:
        return {"status": "skip", "reason": "redis_unavailable"}

    payload = {
        "status": "up",
        "env": settings.env,
        "db": "up",
        "cache": "up",
        "version": "0.1.0",
        "last_seeded_at": datetime.utcnow().isoformat(),
    }

    try:
        await r.set("meta:api", json.dumps(payload), ex=3600)
        return {"status": "ok", "cached_key": "meta:api"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
