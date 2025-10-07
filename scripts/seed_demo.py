# scripts/seed_demo.py
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import random

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
            sites = []
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
                tariff = (await session.scalar(select(Tariff).where(Tariff.site_id == site.id))) or Tariff(
                    name=f"{site.name} Standard",
                    price_per_kwh=0.15 + random.random() * 0.05,
                    site=site,
                )
                session.add(tariff)

            # --- Meters + Measurements ---
            for site in sites:
                for i in range(3):
                    meter = Meter(
                        name=f"{site.name} Meter {i+1}",
                        location=f"{site.location} - Floor {i+1}",
                        serial_number=f"{site.name[:3].upper()}-{i+1:03d}",
                        type=random.choice(["single-phase", "three-phase"]),
                        site=site,
                    )
                    session.add(meter)
                    await session.flush()

                    # 24h demo data (hourly)
                    now = datetime.utcnow()
                    for h in range(24):
                        ts = now - timedelta(hours=h)

                        # imported/exported
                        imp = EnergyImported(timestamp=ts, measure_value=random.uniform(0.5, 3.0), meter=meter)
                        exp = EnergyExported(timestamp=ts, measure_value=random.uniform(0.0, 1.0), meter=meter)
                        session.add_all([imp, exp])

                        # reactive energy (imported/exported kvarh values)
                        reactive = EnergyReactive(
                            timestamp=ts,
                            imported_kvarh=random.uniform(0.1, 0.5),
                            exported_kvarh=random.uniform(0.1, 0.4),
                            meter=meter,
                        )
                        session.add(reactive)

                    # max power daily
                    mp = MaxPower(timestamp=now.date(), measure_value=random.uniform(3.0, 5.5), meter=meter)
                    session.add(mp)

            await session.commit()
            print("[seed_demo] Demo data seeded successfully.")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
