# app/tasks/demo_data.py
from __future__ import annotations

import random
import math
from datetime import datetime, timedelta
from sqlalchemy import select, delete, func
from app.core.db import get_async_engine, async_sessionmaker_dep
from app.models import Meter, EnergyImported, EnergyExported, EnergyReactive, MaxPower


async def generate_demo_data(days: int = 1) -> dict:
    """
    Append new synthetic demo readings for the next N days (default: 1).
    Does NOT recreate users, sites, or meters — assumes they already exist.
    Mimics scripts/seed_demo.py patterns but only for new time periods.
    """
    engine = get_async_engine()
    SessionLocal = async_sessionmaker_dep(engine)
    try:
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        rnd = random.Random(42)

        async with SessionLocal() as session:
            meters = (await session.execute(select(Meter.id, Meter.name))).all()
            if not meters:
                return {"inserted": 0, "reason": "no meters present"}

            inserted = 0
            for mid, name in meters:
                # find latest timestamp for this meter
                res = await session.execute(
                    select(func.max(EnergyImported.timestamp)).where(
                        EnergyImported.meter_id == mid
                    )
                )
                last_ts = res.scalar()
                start_ts = (last_ts or now) + timedelta(hours=1)

                for h in range(24 * days):
                    ts = start_ts + timedelta(hours=h)
                    base = 1.5 + 1.0 * (1 + math.sin(h / 12.0)) / 2
                    session.add_all(
                        [
                            EnergyImported(
                                timestamp=ts,
                                measure_value=base + rnd.uniform(-0.3, 0.3),
                                meter_id=mid,
                            ),
                            EnergyExported(
                                timestamp=ts,
                                measure_value=max(0, base / 2 + rnd.uniform(-0.2, 0.2)),
                                meter_id=mid,
                            ),
                            EnergyReactive(
                                timestamp=ts,
                                imported_kvarh=0.2 + rnd.uniform(0.0, 0.2),
                                exported_kvarh=0.2 + rnd.uniform(0.0, 0.2),
                                meter_id=mid,
                            ),
                        ]
                    )
                    inserted += 3

                # Daily max power values for new days
                for d in range(days):
                    day_date = start_ts + timedelta(days=d)
                    session.add(
                        MaxPower(
                            timestamp=day_date,
                            measure_value=rnd.uniform(3.0, 5.5),
                            meter_id=mid,
                        )
                    )
                    inserted += 1

            await session.commit()
            return {
                "inserted": inserted,
                "days_added": days,
                "meters": len(meters),
                "completed_at": datetime.utcnow().isoformat(),
            }

    finally:
        await engine.dispose()


async def clean_demo_data(older_than_days: int = 30) -> dict:
    """
    Delete all readings older than the given window (rolling demo).
    """
    engine = get_async_engine()
    SessionLocal = async_sessionmaker_dep(engine)
    try:
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)

        async with SessionLocal() as session:
            total = 0
            for model, column in [
                (EnergyImported, EnergyImported.timestamp),
                (EnergyExported, EnergyExported.timestamp),
                (EnergyReactive, EnergyReactive.timestamp),
                (MaxPower, MaxPower.timestamp),
            ]:
                result = await session.execute(delete(model).where(column < cutoff))
                count = getattr(result, "rowcount", 0) or 0
                total += count
            await session.commit()

            return {
                "deleted": total,
                "cutoff": cutoff.isoformat(),
                "completed_at": datetime.utcnow().isoformat(),
            }
    finally:
        await engine.dispose()
