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
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt", "sha256_crypt"],
    default="bcrypt",
    deprecated="auto",
)


async def seed() -> None:
    """Seed an empty database; never overwrite existing users or data."""
    if not settings.demo_password or settings.demo_password in {"demo", "change-me"}:
        raise ValueError("Set DEMO_PASSWORD to a unique password before seeding")
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    print("[seed_demo] 🚀 Starting fresh demo database seed.")

    try:
        async with async_session() as session:
            if await session.scalar(select(User.id).limit(1)) is not None:
                print("[seed_demo] Existing users found; leaving data unchanged.")
                return

            # --- Create demo user ---
            hashed_pw = pwd_context.hash(settings.demo_password)
            user = User(
                username="demo", email="demo@example.com", hashed_password=hashed_pw
            )
            session.add(user)
            await session.flush()
            print("[seed_demo] Created demo user")

            # --- Sites ---
            site_names = ["Main Campus", "Research Lab"]
            sites: list[Site] = []
            for name in site_names:
                site = Site(name=name, location=f"{name} Building", owner=user)
                session.add(site)
                sites.append(site)
                print(f"[seed_demo] 🏢 Created site: {site.name}")

            await session.flush()

            # --- Tariffs ---
            for site in sites:
                for tariff_name, base_price in [
                    (f"{site.name} Standard", 0.15),
                    (f"{site.name} Peak", 0.20),
                ]:
                    tariff = Tariff(
                        name=tariff_name,
                        price_per_kwh=round(base_price + random.random() * 0.05, 3),
                        site=site,
                    )
                    session.add(tariff)
                    print(f"[seed_demo] 💡 Created tariff: {tariff.name}")

            # --- Meters + Measurements ---
            now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
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
                    print(f"[seed_demo] ⚙️ Created meter: {meter.name}")

                    # Hourly data (7 days)
                    hourly_records = []
                    for h in range(24 * 7):
                        ts = now - timedelta(hours=h)
                        base = 1.5 + 1.0 * (1 + math.sin(h / 12.0)) / 2
                        hourly_records.extend(
                            [
                                EnergyImported(
                                    timestamp=ts,
                                    measure_value=base + random.uniform(-0.3, 0.3),
                                    meter=meter,
                                ),
                                EnergyExported(
                                    timestamp=ts,
                                    measure_value=max(
                                        0, base / 2 + random.uniform(-0.2, 0.2)
                                    ),
                                    meter=meter,
                                ),
                                EnergyReactive(
                                    timestamp=ts,
                                    imported_kvarh=0.2 + random.uniform(0.0, 0.2),
                                    exported_kvarh=0.2 + random.uniform(0.0, 0.2),
                                    meter=meter,
                                ),
                            ]
                        )
                    session.add_all(hourly_records)

                    # Daily max power data (7 days)
                    power_records = [
                        MaxPower(
                            timestamp=(now - timedelta(days=d)),
                            measure_value=random.uniform(3.0, 5.5),
                            meter=meter,
                        )
                        for d in range(7)
                    ]
                    session.add_all(power_records)

            await session.commit()
            print("[seed_demo] ✅ Demo data seeded successfully.")
            print(
                f"[seed_demo] Summary → Users: 1 | Sites: {len(sites)} | Meters: {len(sites)*3} | Tariffs: {len(sites)*2}"
            )

    finally:
        await engine.dispose()
        print("[seed_demo] 🧹 Engine disposed — seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
