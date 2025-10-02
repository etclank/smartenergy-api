# scripts/seed_demo.py
from __future__ import annotations

import asyncio
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.meter import Meter


DEMO_METERS: Sequence[tuple[str, str]] = [
    ("Main Building", "Roof"),
    ("R&D Lab 1", "Basement"),
    ("Office East", "Floor 3"),
    ("Warehouse A", "Dock 2"),
]


async def seed() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async_session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    try:
        async with async_session() as session:
            for name, location in DEMO_METERS:
                exists = await session.execute(
                    select(Meter).where(Meter.name == name)
                )
                if exists.scalar_one_or_none() is None:
                    session.add(Meter(name=name, location=location))
            await session.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
