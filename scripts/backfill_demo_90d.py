"""Create the bounded, deterministic portfolio demo dataset exactly once."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import math
import random
import time
from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.db import async_sessionmaker_dep, get_async_engine
from app.models import (
    EnergyExported,
    EnergyImported,
    EnergyReactive,
    MaxPower,
    Meter,
    Site,
    SummaryKPI,
    Tariff,
    User,
)
from app.tasks.cache_tasks import clean_stale_cache

SEED = 2026
HOURS = 90 * 24
PERIOD = "hourly"
OWNER_USERNAME = "demo-backfill-owner-disabled"
OWNER_EMAIL = "demo-backfill-owner@example.invalid"
DISABLED_PASSWORD_HASH = "!demo-backfill-login-disabled"


@dataclass(frozen=True)
class SiteSpec:
    name: str
    location: str
    tariff_name: str
    price_per_kwh: float


@dataclass(frozen=True)
class MeterSpec:
    site_name: str
    name: str
    location: str
    serial_number: str
    meter_type: str
    profile: str
    scale: float


SITE_SPECS = (
    SiteSpec(
        "Demo Residence",
        "Portfolio Residence",
        "Demo Residential Standard",
        0.28,
    ),
    SiteSpec("Demo Office", "Portfolio Office", "Demo Business Standard", 0.24),
    SiteSpec(
        "Demo Solar Facility",
        "Portfolio Solar Facility",
        "Demo Solar Time-of-Use",
        0.22,
    ),
)

METER_SPECS = (
    MeterSpec(
        "Demo Residence",
        "Residence Grid Meter",
        "Main incomer",
        "DEMO-RES-GRID",
        "single-phase",
        "residence",
        1.0,
    ),
    MeterSpec(
        "Demo Residence",
        "Residence Load Meter",
        "Household circuits",
        "DEMO-RES-LOAD",
        "single-phase",
        "residence",
        0.62,
    ),
    MeterSpec(
        "Demo Office",
        "Office Grid Meter",
        "Main incomer",
        "DEMO-OFF-GRID",
        "three-phase",
        "office",
        1.0,
    ),
    MeterSpec(
        "Demo Office",
        "Office Load Meter",
        "Office floor",
        "DEMO-OFF-LOAD",
        "three-phase",
        "office",
        0.68,
    ),
    MeterSpec(
        "Demo Solar Facility",
        "Solar Grid Meter",
        "Grid connection",
        "DEMO-SOL-GRID",
        "three-phase",
        "solar",
        0.72,
    ),
    MeterSpec(
        "Demo Solar Facility",
        "Solar Generation Meter",
        "PV array",
        "DEMO-SOL-PV",
        "three-phase",
        "solar",
        1.0,
    ),
)

DOMAIN_MODELS = (
    User,
    Site,
    Meter,
    Tariff,
    EnergyImported,
    EnergyExported,
    EnergyReactive,
    MaxPower,
    SummaryKPI,
)


class BackfillBlockedError(RuntimeError):
    """Raised before writes when existing domain data is not the complete demo."""


@dataclass(frozen=True)
class BackfillResult:
    status: str
    sites: int
    meters: int
    tariffs: int
    imported_readings: int
    exported_readings: int
    reactive_readings: int
    max_power_readings: int
    kpis: int
    oldest: datetime | None
    newest: datetime | None
    cache_status: str
    duration_seconds: float


def completed_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return 2,160 naive-UTC hourly slots ending at the last completed hour."""
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    current = current.astimezone(UTC)
    end = current.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    end = end.replace(tzinfo=None)
    return end - timedelta(hours=HOURS - 1), end


def _reading_values(
    spec: MeterSpec, timestamp: datetime, rng: random.Random
) -> tuple[float, float, float, float]:
    """Return import, export, imported reactive and exported reactive energy."""
    hour = timestamp.hour
    weekend = timestamp.weekday() >= 5
    day_factor = 1.0 + rng.uniform(-0.08, 0.08)

    if spec.profile == "residence":
        imported = 0.22
        if 6 <= hour <= 9:
            imported += 0.75 * math.sin(math.pi * (hour - 5) / 5)
        if 17 <= hour <= 22:
            imported += 1.35 * math.sin(math.pi * (hour - 16) / 7)
        if weekend and 10 <= hour <= 16:
            imported += 0.25
        exported = 0.0
    elif spec.profile == "office":
        imported = 0.18
        if not weekend and 7 <= hour <= 18:
            imported += 2.2 + 0.45 * math.sin(math.pi * (hour - 7) / 11)
        elif weekend and 9 <= hour <= 16:
            imported += 0.35
        exported = 0.0
    else:
        facility_load = 0.28 + (0.14 if 8 <= hour <= 18 else 0.0)
        daylight = math.sin(math.pi * (hour - 6) / 12) if 6 < hour < 18 else 0.0
        solar = 4.8 * daylight * day_factor * spec.scale
        imported = max(0.04, facility_load * spec.scale - solar)
        exported = max(0.0, solar - facility_load * spec.scale)

    if spec.profile != "solar":
        imported *= day_factor * spec.scale

    imported = round(max(0.0, imported), 4)
    exported = round(max(0.0, exported), 4)
    return (
        imported,
        exported,
        round(imported * 0.18, 4),
        round(exported * 0.08, 4),
    )


async def _counts(session: AsyncSession) -> dict[type[Any], int]:
    return {
        model: int(await session.scalar(select(func.count()).select_from(model)) or 0)
        for model in DOMAIN_MODELS
    }


async def _known_topology_is_exact(session: AsyncSession) -> bool:
    users = (await session.execute(select(User))).scalars().all()
    if len(users) != 1:
        return False
    owner = users[0]
    if (owner.username, owner.email) != (OWNER_USERNAME, OWNER_EMAIL):
        return False

    sites = (await session.execute(select(Site))).scalars().all()
    if len(sites) != len(SITE_SPECS):
        return False
    site_by_id = {site.id: site.name for site in sites}
    expected_sites = {(spec.name, spec.location) for spec in SITE_SPECS}
    if {(site.name, site.location) for site in sites} != expected_sites:
        return False
    if any(site.user_id != owner.id for site in sites):
        return False

    meters = (await session.execute(select(Meter))).scalars().all()
    if len(meters) != len(METER_SPECS):
        return False
    expected_meters = {
        (
            spec.site_name,
            spec.name,
            spec.location,
            spec.serial_number,
            spec.meter_type,
        )
        for spec in METER_SPECS
    }
    actual_meters = {
        (
            site_by_id.get(meter.site_id),
            meter.name,
            meter.location,
            meter.serial_number,
            meter.type,
        )
        for meter in meters
    }
    if actual_meters != expected_meters:
        return False

    tariffs = (await session.execute(select(Tariff))).scalars().all()
    if len(tariffs) != len(SITE_SPECS):
        return False
    expected_tariffs = {
        (spec.name, spec.tariff_name, spec.price_per_kwh) for spec in SITE_SPECS
    }
    actual_tariffs = {
        (site_by_id.get(tariff.site_id), tariff.name, tariff.price_per_kwh)
        for tariff in tariffs
    }
    return actual_tariffs == expected_tariffs


async def _reading_shape_is_complete(
    session: AsyncSession, last_completed_hour: datetime
) -> tuple[bool, datetime | None, datetime | None]:
    meters = (await session.execute(select(Meter.id))).scalars().all()
    if len(meters) != len(METER_SPECS):
        return False, None, None

    boundaries: tuple[datetime | None, datetime | None] = (None, None)
    for model in (EnergyImported, EnergyExported, EnergyReactive):
        rows = (
            await session.execute(
                select(
                    model.meter_id,
                    func.count(model.id),
                    func.count(func.distinct(model.timestamp)),
                    func.min(model.timestamp),
                    func.max(model.timestamp),
                ).group_by(model.meter_id)
            )
        ).all()
        if len(rows) != len(METER_SPECS):
            return False, None, None
        for meter_id, count, distinct_count, oldest, newest in rows:
            if meter_id not in meters or count != HOURS or distinct_count != HOURS:
                return False, None, None
            if oldest is None or newest is None:
                return False, None, None
            if newest - oldest != timedelta(hours=HOURS - 1):
                return False, None, None
            if newest > last_completed_hour:
                return False, None, None
            if model is EnergyImported:
                boundaries = oldest, newest
            elif boundaries != (oldest, newest):
                return False, None, None

    oldest, newest = boundaries
    if oldest is None or newest is None:
        return False, None, None
    dates = (newest.date() - oldest.date()).days + 1
    power_groups = (
        await session.execute(
            select(MaxPower.meter_id, func.count(MaxPower.id)).group_by(
                MaxPower.meter_id
            )
        )
    ).all()
    if len(power_groups) != len(METER_SPECS) or any(
        count != dates for _, count in power_groups
    ):
        return False, None, None
    kpi_groups = (
        await session.execute(
            select(SummaryKPI.site_id, func.count(SummaryKPI.id)).group_by(
                SummaryKPI.site_id
            )
        )
    ).all()
    if len(kpi_groups) != len(SITE_SPECS) or any(
        count != dates for _, count in kpi_groups
    ):
        return False, None, None
    if not await session.scalar(
        select(func.sum(EnergyImported.measure_value)).where(
            EnergyImported.measure_value > 0
        )
    ):
        return False, None, None
    solar_meter_id = await session.scalar(
        select(Meter.id).where(Meter.serial_number == "DEMO-SOL-PV")
    )
    if not await session.scalar(
        select(func.sum(EnergyExported.measure_value)).where(
            EnergyExported.meter_id == solar_meter_id,
            EnergyExported.measure_value > 0,
        )
    ):
        return False, None, None
    return True, oldest, newest


async def _classify(
    session: AsyncSession, last_completed_hour: datetime
) -> tuple[str, datetime | None, datetime | None]:
    counts = await _counts(session)
    if not any(counts.values()):
        return "empty", None, None

    known_identifiers = bool(
        await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.username == OWNER_USERNAME)
        )
        or await session.scalar(
            select(func.count())
            .select_from(Site)
            .where(Site.name.in_([spec.name for spec in SITE_SPECS]))
        )
        or await session.scalar(
            select(func.count())
            .select_from(Meter)
            .where(
                Meter.serial_number.in_([spec.serial_number for spec in METER_SPECS])
            )
        )
    )
    if await _known_topology_is_exact(session):
        complete, oldest, newest = await _reading_shape_is_complete(
            session, last_completed_hour
        )
        if complete:
            return "complete", oldest, newest
        raise BackfillBlockedError(
            "known demo topology is incomplete or its reading window is invalid"
        )
    if known_identifiers:
        raise BackfillBlockedError("partial or mixed known demo data already exists")
    raise BackfillBlockedError("unrelated application data already exists")


async def _insert_in_batches(
    session: AsyncSession,
    model: type[Any],
    rows: Iterable[dict[str, Any]],
    batch_size: int = 1000,
) -> None:
    batch: list[dict[str, Any]] = []
    for row in rows:
        batch.append(row)
        if len(batch) == batch_size:
            await session.execute(insert(model.__table__), batch)
            batch.clear()
    if batch:
        await session.execute(insert(model.__table__), batch)


async def _create_dataset(
    session: AsyncSession, oldest: datetime, newest: datetime
) -> dict[str, int]:
    owner = User(
        username=OWNER_USERNAME,
        email=OWNER_EMAIL,
        hashed_password=DISABLED_PASSWORD_HASH,
    )
    session.add(owner)
    await session.flush()

    sites = {
        spec.name: Site(
            name=spec.name,
            location=spec.location,
            user_id=owner.id,
        )
        for spec in SITE_SPECS
    }
    session.add_all(sites.values())
    await session.flush()
    session.add_all(
        Tariff(
            name=spec.tariff_name,
            price_per_kwh=spec.price_per_kwh,
            site_id=sites[spec.name].id,
        )
        for spec in SITE_SPECS
    )

    meters: list[tuple[MeterSpec, Meter]] = []
    for spec in METER_SPECS:
        meter = Meter(
            name=spec.name,
            location=spec.location,
            serial_number=spec.serial_number,
            type=spec.meter_type,
            site_id=sites[spec.site_name].id,
        )
        session.add(meter)
        meters.append((spec, meter))
    await session.flush()

    timestamps = [oldest + timedelta(hours=offset) for offset in range(HOURS)]
    rng = random.Random(SEED)
    site_daily_import: dict[tuple[int, date], float] = defaultdict(float)
    site_daily_export: dict[tuple[int, date], float] = defaultdict(float)
    site_daily_power: dict[tuple[int, date], list[float]] = defaultdict(list)

    imported_rows: list[dict[str, Any]] = []
    exported_rows: list[dict[str, Any]] = []
    reactive_rows: list[dict[str, Any]] = []
    daily_meter_peak: dict[tuple[int, date], float] = defaultdict(float)

    for spec, meter in meters:
        site_id = sites[spec.site_name].id
        for timestamp in timestamps:
            imported, exported, reactive_imported, reactive_exported = _reading_values(
                spec, timestamp, rng
            )
            imported_rows.append(
                {
                    "timestamp": timestamp,
                    "measure_value": imported,
                    "period": PERIOD,
                    "meter_id": meter.id,
                }
            )
            exported_rows.append(
                {
                    "timestamp": timestamp,
                    "measure_value": exported,
                    "period": PERIOD,
                    "meter_id": meter.id,
                }
            )
            reactive_rows.append(
                {
                    "timestamp": timestamp,
                    "imported_kvarh": reactive_imported,
                    "exported_kvarh": reactive_exported,
                    "meter_id": meter.id,
                }
            )
            key = (site_id, timestamp.date())
            site_daily_import[key] += imported
            site_daily_export[key] += exported
            meter_key = (meter.id, timestamp.date())
            daily_meter_peak[meter_key] = max(daily_meter_peak[meter_key], imported)

    await _insert_in_batches(session, EnergyImported, imported_rows)
    await _insert_in_batches(session, EnergyExported, exported_rows)
    await _insert_in_batches(session, EnergyReactive, reactive_rows)

    max_power_rows: list[dict[str, Any]] = []
    for (meter_id, reading_date), peak in daily_meter_peak.items():
        max_power_rows.append(
            {
                "timestamp": datetime.combine(reading_date, datetime.min.time()),
                "measure_value": round(max(peak, 0.01), 4),
                "meter_id": meter_id,
            }
        )
        meter_site_id = next(
            meter.site_id for _, meter in meters if meter.id == meter_id
        )
        site_daily_power[(meter_site_id, reading_date)].append(max(peak, 0.01))
    await _insert_in_batches(session, MaxPower, max_power_rows)

    kpi_rows = [
        {
            "date": reading_date,
            "site_id": site_id,
            "imported_kwh": round(imported, 4),
            "exported_kwh": round(site_daily_export[(site_id, reading_date)], 4),
            "avg_max_power": round(
                sum(site_daily_power[(site_id, reading_date)])
                / len(site_daily_power[(site_id, reading_date)]),
                4,
            ),
            "created_at": datetime.combine(reading_date, datetime.min.time()),
        }
        for (site_id, reading_date), imported in site_daily_import.items()
    ]
    await _insert_in_batches(session, SummaryKPI, kpi_rows)

    return {
        "imported": len(imported_rows),
        "exported": len(exported_rows),
        "reactive": len(reactive_rows),
        "max_power": len(max_power_rows),
        "kpis": len(kpi_rows),
    }


async def backfill_demo_90d(
    *,
    now: datetime | None = None,
    engine: AsyncEngine | None = None,
    cache_cleaner: Callable[[str], Awaitable[dict[str, Any]]] = clean_stale_cache,
) -> BackfillResult:
    """Create the dataset, return NOOP for an exact rerun, or block safely."""
    started = time.perf_counter()
    oldest, newest = completed_window(now)
    owned_engine = engine is None
    active_engine = engine or get_async_engine()
    session_factory = async_sessionmaker_dep(active_engine)
    try:
        async with session_factory() as session:
            async with session.begin():
                state, existing_oldest, existing_newest = await _classify(
                    session, newest
                )
                if state == "complete":
                    return BackfillResult(
                        status="NOOP",
                        sites=len(SITE_SPECS),
                        meters=len(METER_SPECS),
                        tariffs=len(SITE_SPECS),
                        imported_readings=HOURS * len(METER_SPECS),
                        exported_readings=HOURS * len(METER_SPECS),
                        reactive_readings=HOURS * len(METER_SPECS),
                        max_power_readings=int(
                            await session.scalar(
                                select(func.count()).select_from(MaxPower)
                            )
                            or 0
                        ),
                        kpis=int(
                            await session.scalar(
                                select(func.count()).select_from(SummaryKPI)
                            )
                            or 0
                        ),
                        oldest=existing_oldest,
                        newest=existing_newest,
                        cache_status="unchanged",
                        duration_seconds=time.perf_counter() - started,
                    )
                created = await _create_dataset(session, oldest, newest)

        cache_result = await cache_cleaner("cache:*")
        return BackfillResult(
            status="CREATED",
            sites=len(SITE_SPECS),
            meters=len(METER_SPECS),
            tariffs=len(SITE_SPECS),
            imported_readings=created["imported"],
            exported_readings=created["exported"],
            reactive_readings=created["reactive"],
            max_power_readings=created["max_power"],
            kpis=created["kpis"],
            oldest=oldest,
            newest=newest,
            cache_status=str(cache_result.get("status", "unknown")),
            duration_seconds=time.perf_counter() - started,
        )
    finally:
        if owned_engine:
            await active_engine.dispose()


def _print_result(result: BackfillResult) -> None:
    print(f"status={result.status}")
    print(
        f"sites={result.sites} meters={result.meters} tariffs={result.tariffs} "
        f"imported={result.imported_readings} exported={result.exported_readings} "
        f"reactive={result.reactive_readings} max_power={result.max_power_readings} "
        f"kpis={result.kpis}"
    )
    print(f"oldest={result.oldest.isoformat() if result.oldest else 'none'}")
    print(f"newest={result.newest.isoformat() if result.newest else 'none'}")
    print(f"cache={result.cache_status}")
    print(f"duration_seconds={result.duration_seconds:.2f}")


async def _main() -> int:
    try:
        _print_result(await backfill_demo_90d())
        return 0
    except BackfillBlockedError as exc:
        print("status=BLOCKED")
        print(f"reason={exc}")
        return 2
    except Exception as exc:
        print("status=FAILED")
        print(f"error_type={type(exc).__name__}")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
