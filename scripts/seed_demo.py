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

# Optional: lightweight hashing for realism
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt", "sha256_crypt"],  # fallback if bcrypt fails
    default="bcrypt",
    deprecated="auto"
)



async def seed() -> None:
    """Seed demo data into the database."""
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    print(f"[seed_demo] Using database: {settings.database_url}")

    try:
        async with async_session() as session:
            # --- User ---
            user = await session.scalar(select(User).where(User.username == "demo"))
            if not user:
                hashed_pw = pwd_context.hash("demo")
                user = User(username="demo", email="demo@example.com", hashed_password=hashed_pw)
                session.add(user)
                await session.flush()
                print("[seed_demo] ✅ Demo user created with password 'demo'")
            else:
                print("[seed_demo] ⚠️ Demo user already exists — skipping creation.")

            # --- Sites ---
            site_names = ["Main Campus", "Research Lab"]
            sites: list[Site] = []

            for name in site_names:
                site = await session.scalar(select(Site).where(Site.name == name))
                if not site:
                    site = Site(
                        name=name,
                        location=f"{name} Building",
                        owner=user,
                    )
                    session.add(site)
                    sites.append(site)
                    print(f"[seed_demo] ✅ Created site: {site.name}")
                else:
                    sites.append(site)
                    print(f"[seed_demo] ⚠️ Site already exists: {site.name}")

            await session.flush()

            # --- Tariffs ---
            for site in sites:
                for tariff_name, base_price in [(f"{site.name} Standard", 0.15), (f"{site.name} Peak", 0.20)]:
                    tariff = await session.scalar(select(Tariff).where(Tariff.name == tariff_name))
                    if not tariff:
                        tariff = Tariff(
                            name=tariff_name,
                            price_per_kwh=round(base_price + random.random() * 0.05, 3),
                            site=site,
                        )
                        session.add(tariff)
                        print(f"[seed_demo] ✅ Created tariff: {tariff.name}")
                    else:
                        print(f"[seed_demo] ⚠️ Tariff exists: {tariff.name}")

            # --- Meters + Measurements ---
            for site in sites:
                for i in range(3):
                    meter_name = f"{site.name} Meter {i+1}"
                    meter = await session.scalar(select(Meter).where(Meter.name == meter_name))
                    if not meter:
                        meter = Meter(
                            name=meter_name,
                            location=f"{site.location} - Floor {i+1}",
                            serial_number=f"{site.name[:3].upper()}-{i+1:03d}",
                            type=random.choice(["single-phase", "three-phase"]),
                            site=site,
                        )
                        session.add(meter)
                        await session.flush()
                        print(f"[seed_demo] ✅ Created meter: {meter.name}")
                    else:
                        print(f"[seed_demo] ⚠️ Meter exists: {meter.name}")

                    # 7 days of hourly data (168 samples)
                    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
                    for h in range(24 * 7):
                        ts = now - timedelta(hours=h)

                        # Add some smooth daily variation (optional: sinusoidal pattern)
                        base = 1.5 + 1.0 * (1 + math.sin(h / 12.0)) / 2  # gentle curve
                        imp = EnergyImported(timestamp=ts, measure_value=base + random.uniform(-0.3, 0.3), meter=meter)
                        exp = EnergyExported(timestamp=ts, measure_value=max(0, base / 2 + random.uniform(-0.2, 0.2)), meter=meter)
                        reactive = EnergyReactive(
                            timestamp=ts,
                            imported_kvarh=0.2 + random.uniform(0.0, 0.2),
                            exported_kvarh=0.2 + random.uniform(0.0, 0.2),
                            meter=meter,
                        )
                        session.add_all([imp, exp, reactive])

                    # Max Power week data
                    for d in range(7):
                        ts_day = (now - timedelta(days=d)).date()
                        mp = MaxPower(timestamp=ts_day, measure_value=random.uniform(3.0, 5.5), meter=meter)
                        session.add(mp)

            await session.commit()
            print("[seed_demo] ✅ Demo data seeded successfully.")
            print(f"  Users: 1, Sites: {len(sites)}, Tariffs: {len(sites)*2}, Meters: {len(sites)*3}")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
