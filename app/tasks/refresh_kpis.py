from __future__ import annotations

from datetime import date, timedelta
from sqlalchemy import select, func
from app.core.db import get_async_engine, async_sessionmaker_dep
from app.models import (
    Site,
    Meter,
    EnergyImported,
    EnergyExported,
    MaxPower,
    SummaryKPI,
)


async def refresh_kpis(target: date | None = None) -> dict:
    """
    Aggregate imported/exported energy and average max power per site
    for the given date (defaults to yesterday).
    Upserts into summary_kpi (unique per site_id + date).
    """
    target = target or (date.today() - timedelta(days=1))
    engine = get_async_engine()
    SessionLocal = async_sessionmaker_dep(engine)

    async with SessionLocal() as session:
        # -----------------------------------------------------
        # 1️⃣ Aggregate totals per site for the target day
        # -----------------------------------------------------

        # Imported energy (sum)
        q_imp = (
            select(Meter.site_id, func.sum(EnergyImported.measure_value))
            .join(Meter, Meter.id == EnergyImported.meter_id)
            .where(func.date(EnergyImported.timestamp) == target)
            .group_by(Meter.site_id)
        )

        # Exported energy (sum)
        q_exp = (
            select(Meter.site_id, func.sum(EnergyExported.measure_value))
            .join(Meter, Meter.id == EnergyExported.meter_id)
            .where(func.date(EnergyExported.timestamp) == target)
            .group_by(Meter.site_id)
        )

        # Max power (average)
        q_power = (
            select(Meter.site_id, func.avg(MaxPower.measure_value))
            .join(Meter, Meter.id == MaxPower.meter_id)
            .where(func.date(MaxPower.timestamp) == target)
            .group_by(Meter.site_id)
        )

        imp = {sid: float(v or 0) for sid, v in (await session.execute(q_imp)).all()}
        exp = {sid: float(v or 0) for sid, v in (await session.execute(q_exp)).all()}
        pwr = {sid: float(v or 0) for sid, v in (await session.execute(q_power)).all()}

        # -----------------------------------------------------
        # 2️⃣ Upsert results into summary_kpi
        # -----------------------------------------------------
        site_ids = (await session.execute(select(Site.id))).scalars().all()
        upserts = 0

        for sid in site_ids:
            imported_kwh = imp.get(sid, 0.0)
            exported_kwh = exp.get(sid, 0.0)
            avg_max_power = pwr.get(sid, 0.0)

            existing = await session.scalar(
                select(SummaryKPI).where(
                    SummaryKPI.site_id == sid,
                    SummaryKPI.date == target,
                )
            )
            if existing:
                existing.imported_kwh = imported_kwh
                existing.exported_kwh = exported_kwh
                existing.avg_max_power = avg_max_power
            else:
                session.add(
                    SummaryKPI(
                        site_id=sid,
                        date=target,
                        imported_kwh=imported_kwh,
                        exported_kwh=exported_kwh,
                        avg_max_power=avg_max_power,
                    )
                )
            upserts += 1

        await session.commit()

        # -----------------------------------------------------
        # 3️⃣ Return summary
        # -----------------------------------------------------
        return {
            "date": str(target),
            "sites_processed": len(site_ids),
            "rows_upserted": upserts,
        }
