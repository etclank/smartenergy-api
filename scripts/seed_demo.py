# scripts/seed_demo.py
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import random
import math

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.models import (
    User,
    Site,
    Meter,
    Tariff,
    EnergyImported,
    EnergyExported,
    EnergyReactive,
    MaxPower,
)


async def seed() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # --- User ---
            user = (await session.scalar(select(User).where(User.username == "demo"))) or User(
                username="demo", email="demo@example.com"
            )
            session.add(user)
            await session.flush()

            # --- Sites ---
            site_names = ["Main Campus", "Research Lab"]
            sites: list[Site] = []

            for name in site_names:
                site = (await session.scalar(select(Site).where(Site.name == name))) or Site(
                    name=name,
                    location=f"{name} Building",
                    owner=user,
                )
                session.add(site)
                sites.append(site)
            await session.flush()

            # --- Tariffs ---
            for site in sites:
                # Standard tariff
                tariff_std = (await session.scalar(
                    select(Tariff).where(Tariff.name == f"{site.name} Standard")
                )) or Tariff(
                    name=f"{site.name} Standard",
                    price_per_kwh=round(0.15 + random.random() * 0.05, 3),
                    site=site,
                )
                session.add(tariff_std)

                # Peak tariff
                tariff_peak = (await session.scalar(
                    select(Tariff).where(Tariff.name == f"{site.name} Peak")
                )) or Tariff(
                    name=f"{site.name} Peak",
                    price_per_kwh=round(0.20 + random.random() * 0.05, 3),
                    site=site,
                )
                session.add(tariff_peak)

            # --- Meters + Measurements ---
            for site in sites:
                for i in range(3):
                    meter = (await session.scalar(
                        select(Meter).where(Meter.name == f"{site.name} Meter {i+1}")
                    )) or Meter(
                        name=f"{site.name} Meter {i+1}",
                        location=f"{site.location} - Floor {i+1}",
                        serial_number=f"{site.name[:3].upper()}-{i+1:03d}",
                        type=random.choice(["single-phase", "three-phase"]),
                        site=site,
                    )
                    session.add(meter)
                    await session.flush()

                    # 7 days of hourly data (168 samples)
                    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
                    for h in range(24 * 7):
                        ts = now - timedelta(hours=h)

                        # Add some smooth daily variation (optional: sinusoidal pattern)
                        base = 1.5 + 1.0 * (1 + math.sin(h / 12.0)) / 2  # gentle curve
                        imp = EnergyImported(timestamp=ts, measure_value=base + random.uniform(-0.3, 0.3), meter=meter)
                        exp = EnergyExported(timestamp=ts, measure_value=max(0, base / 2 + random.uniform(-0.2, 0.2)), meter=meter)
                        session.add_all([imp, exp])

                        reactive = EnergyReactive(
                            timestamp=ts,
                            imported_kvarh=0.2 + random.uniform(0.0, 0.2),
                            exported_kvarh=0.2 + random.uniform(0.0, 0.2),
                            meter=meter,
                        )
                        session.add(reactive)


                    # Max Power week data
                    for d in range(7):
                        ts_day = (now - timedelta(days=d)).date()
                        mp = MaxPower(timestamp=ts_day, measure_value=random.uniform(3.0, 5.5), meter=meter)
                        session.add(mp)


            await session.commit()
            print("[seed_demo] Demo data seeded successfully.")
            print(f"  Users: 1, Sites: {len(sites)}, Tariffs: {len(sites)*2}, Meters: {len(sites)*3}")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
