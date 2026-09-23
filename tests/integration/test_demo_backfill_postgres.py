from __future__ import annotations

from datetime import UTC, datetime
import os

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import create_async_engine

postgres_url = os.environ.get("TEST_POSTGRES_URL")
if not postgres_url:
    pytest.skip("TEST_POSTGRES_URL is required", allow_module_level=True)

os.environ["DATABASE_URL"] = postgres_url
os.environ.setdefault("JWT_SECRET", "postgres-integration-test-secret")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("ENABLE_TELEMETRY", "0")

from app.core.db import async_sessionmaker_dep  # noqa: E402
from app.models import EnergyImported, Meter, Site, SummaryKPI, Tariff  # noqa: E402
from scripts.backfill_demo_90d import backfill_demo_90d  # noqa: E402


async def no_cache(_pattern: str) -> dict[str, str]:
    return {"status": "skip"}


@pytest.mark.postgres
@pytest.mark.asyncio
async def test_real_backfill_path_on_postgres() -> None:
    engine = create_async_engine(postgres_url)
    try:
        result = await backfill_demo_90d(
            now=datetime(2026, 9, 23, 15, 37, tzinfo=UTC),
            engine=engine,
            cache_cleaner=no_cache,
        )
        assert result.status == "CREATED"

        session_factory = async_sessionmaker_dep(engine)
        async with session_factory() as session:
            assert await session.scalar(select(func.count()).select_from(Site)) == 3
            assert await session.scalar(select(func.count()).select_from(Meter)) == 6
            assert await session.scalar(select(func.count()).select_from(Tariff)) == 3
            assert (
                await session.scalar(select(func.count()).select_from(EnergyImported))
                == 90 * 24 * 6
            )
            assert (
                await session.scalar(select(func.sum(SummaryKPI.imported_kwh))) or 0
            ) > 0

        rerun = await backfill_demo_90d(
            now=datetime(2026, 9, 24, 15, 37, tzinfo=UTC),
            engine=engine,
            cache_cleaner=no_cache,
        )
        assert rerun.status == "NOOP"
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "TRUNCATE TABLE summary_kpi, max_power, energy_reactive, "
                    "energy_exported, energy_imported, tariffs, meters, sites, users "
                    "RESTART IDENTITY CASCADE"
                )
            )
        await engine.dispose()
