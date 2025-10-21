from __future__ import annotations

import time
import json
from datetime import datetime
from sqlalchemy import text, select, func
from app.core.db import get_async_engine, async_sessionmaker_dep
from app.core.cache import get_redis
from app.core.config import settings
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
    Measure database and Redis latency and row counts,
    then insert a new SystemMetrics record.
    """
    engine = get_async_engine()
    SessionLocal = async_sessionmaker_dep(engine)

    db_ms = redis_ms = -1
    counts: dict[str, int] = {}

    try:
        # --------------------------------------------------
        # DB ping
        # --------------------------------------------------
        t0 = time.perf_counter()
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        db_ms = int(1000 * (time.perf_counter() - t0))
    except Exception:
        db_ms = -1

    # ------------------------------------------------------
    # Redis ping
    # ------------------------------------------------------
    try:
        r = await get_redis()
        if r:
            t1 = time.perf_counter()
            await r.ping()
            redis_ms = int(1000 * (time.perf_counter() - t1))
    except Exception:
        redis_ms = -1

    # ------------------------------------------------------
    # Row counts
    # ------------------------------------------------------
    try:
        async with SessionLocal() as db:
            counts = {
                "sites": (await db.execute(select(func.count(Site.id)))).scalar() or 0,
                "meters": (await db.execute(select(func.count(Meter.id)))).scalar() or 0,
                "energy_imported": (await db.execute(select(func.count(EnergyImported.id)))).scalar() or 0,
                "energy_exported": (await db.execute(select(func.count(EnergyExported.id)))).scalar() or 0,
                "energy_reactive": (await db.execute(select(func.count(EnergyReactive.id)))).scalar() or 0,
                "max_power": (await db.execute(select(func.count(MaxPower.id)))).scalar() or 0,
            }
            db.add(
                SystemMetrics(
                    db_latency_ms=db_ms,
                    redis_latency_ms=redis_ms,
                    row_counts=counts,
                )
            )
            await db.commit()
    except Exception:
        # Safe fail-open: do not crash background task
        pass

    # ------------------------------------------------------
    # Return summary
    # ------------------------------------------------------
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "db_latency_ms": db_ms,
        "redis_latency_ms": redis_ms,
        "row_counts": counts,
    }


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
        "version": "stage-2.4",
        "last_seeded_at": datetime.utcnow().isoformat(),
    }

    try:
        await r.set("meta:api", json.dumps(payload), ex=3600)
        return {"status": "ok", "cached_key": "meta:api"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
