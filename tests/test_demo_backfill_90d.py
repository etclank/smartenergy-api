from __future__ import annotations

from datetime import UTC, datetime, timedelta
import random

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import (
    Base,
    EnergyExported,
    EnergyImported,
    MaxPower,
    Meter,
    Site,
    SummaryKPI,
    Tariff,
    User,
)
from scripts import backfill_demo_90d as backfill


@pytest.fixture
async def backfill_engine() -> AsyncEngine:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


async def no_cache(_pattern: str) -> dict[str, str]:
    return {"status": "skip"}


@pytest.mark.asyncio
async def test_backfill_creates_complete_dataset_then_is_noop(
    backfill_engine: AsyncEngine,
) -> None:
    now = datetime(2026, 9, 23, 15, 37, tzinfo=UTC)
    result = await backfill.backfill_demo_90d(
        now=now, engine=backfill_engine, cache_cleaner=no_cache
    )

    assert result.status == "CREATED"
    assert result.sites == 3
    assert result.meters == 6
    assert result.tariffs == 3
    assert result.imported_readings == 90 * 24 * 6
    assert result.exported_readings == 90 * 24 * 6
    assert result.reactive_readings == 90 * 24 * 6
    assert result.oldest == datetime(2026, 6, 25, 15)
    assert result.newest == datetime(2026, 9, 23, 14)
    assert result.newest < now.replace(tzinfo=None)

    session_factory = backfill.async_sessionmaker_dep(backfill_engine)
    async with session_factory() as session:
        site_names = set((await session.scalars(select(Site.name))).all())
        meter_count = await session.scalar(select(func.count()).select_from(Meter))
        tariffs = (await session.scalars(select(Tariff))).all()
        imported_total = await session.scalar(
            select(func.sum(EnergyImported.measure_value))
        )
        solar_meter_id = await session.scalar(
            select(Meter.id).where(Meter.serial_number == "DEMO-SOL-PV")
        )
        solar_export = await session.scalar(
            select(func.sum(EnergyExported.measure_value)).where(
                EnergyExported.meter_id == solar_meter_id
            )
        )
        max_power_min = await session.scalar(select(func.min(MaxPower.measure_value)))
        kpi_import = await session.scalar(select(func.sum(SummaryKPI.imported_kwh)))

    assert site_names == {
        "Demo Residence",
        "Demo Office",
        "Demo Solar Facility",
    }
    assert meter_count == 6
    assert {(tariff.name, tariff.price_per_kwh) for tariff in tariffs} == {
        ("Demo Residential Standard", 0.28),
        ("Demo Business Standard", 0.24),
        ("Demo Solar Time-of-Use", 0.22),
    }
    assert imported_total is not None and imported_total > 0
    assert solar_export is not None and solar_export > 0
    assert max_power_min is not None and max_power_min > 0
    assert kpi_import is not None and kpi_import > 0

    rerun = await backfill.backfill_demo_90d(
        now=now + timedelta(days=30),
        engine=backfill_engine,
        cache_cleaner=no_cache,
    )
    assert rerun.status == "NOOP"
    assert rerun.oldest == result.oldest
    assert rerun.newest == result.newest


def test_generation_is_deterministic_and_profiles_have_expected_shape() -> None:
    timestamp = datetime(2026, 7, 6, 12)
    first = [
        backfill._reading_values(spec, timestamp, random.Random(backfill.SEED))
        for spec in backfill.METER_SPECS
    ]
    second = [
        backfill._reading_values(spec, timestamp, random.Random(backfill.SEED))
        for spec in backfill.METER_SPECS
    ]
    assert first == second
    assert all(imported >= 0 and exported >= 0 for imported, exported, _, _ in first)
    assert first[-1][1] > 0

    overnight = backfill._reading_values(
        backfill.METER_SPECS[-1], datetime(2026, 7, 6, 2), random.Random(2026)
    )
    assert overnight[1] == 0


@pytest.mark.asyncio
async def test_partial_known_dataset_is_blocked(backfill_engine: AsyncEngine) -> None:
    session_factory = backfill.async_sessionmaker_dep(backfill_engine)
    async with session_factory() as session:
        owner = User(
            username=backfill.OWNER_USERNAME,
            email=backfill.OWNER_EMAIL,
            hashed_password=backfill.DISABLED_PASSWORD_HASH,
        )
        session.add(owner)
        await session.flush()
        session.add(
            Site(
                name=backfill.SITE_SPECS[0].name,
                location=backfill.SITE_SPECS[0].location,
                user_id=owner.id,
            )
        )
        await session.commit()

    with pytest.raises(backfill.BackfillBlockedError, match="partial or mixed"):
        await backfill.backfill_demo_90d(engine=backfill_engine, cache_cleaner=no_cache)


@pytest.mark.asyncio
async def test_unrelated_existing_data_is_blocked(backfill_engine: AsyncEngine) -> None:
    session_factory = backfill.async_sessionmaker_dep(backfill_engine)
    async with session_factory() as session:
        session.add(
            User(
                username="existing-operator",
                email="operator@example.test",
                hashed_password="unusable",
            )
        )
        await session.commit()

    with pytest.raises(backfill.BackfillBlockedError, match="unrelated"):
        await backfill.backfill_demo_90d(engine=backfill_engine, cache_cleaner=no_cache)


@pytest.mark.asyncio
async def test_failure_rolls_back_all_writes(
    backfill_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail_insert(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("injected insert failure")

    monkeypatch.setattr(backfill, "_insert_in_batches", fail_insert)
    with pytest.raises(RuntimeError, match="injected insert failure"):
        await backfill.backfill_demo_90d(engine=backfill_engine, cache_cleaner=no_cache)

    session_factory = backfill.async_sessionmaker_dep(backfill_engine)
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 0
        assert await session.scalar(select(func.count()).select_from(Site)) == 0
        assert await session.scalar(select(func.count()).select_from(Meter)) == 0
