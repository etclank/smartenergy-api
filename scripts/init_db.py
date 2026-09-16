"""Create missing tables and apply the legacy telemetry-column compatibility step."""

from __future__ import annotations

import asyncio
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.models.base import Base
from scripts.seed_demo import seed


async def init_db() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            columns = await conn.run_sync(
                lambda sync: {
                    c["name"] for c in inspect(sync).get_columns("system_metrics")
                }
            )
            for column in ("cpu_percent", "mem_percent", "uptime_seconds"):
                if column not in columns:
                    await conn.execute(
                        text(
                            f"ALTER TABLE system_metrics ADD COLUMN {column} DOUBLE PRECISION DEFAULT 0"
                        )
                    )
    finally:
        await engine.dispose()
    if str(settings.seed_demo).lower() in {"1", "true", "yes"}:
        await seed()
    print("[init_db] Database initialization complete.")


if __name__ == "__main__":
    asyncio.run(init_db())
