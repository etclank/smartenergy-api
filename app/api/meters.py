# app/api/meters.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.meter import Meter
from app.api.schemas import MeterCreate, MeterOut
from app.api.utils.cache_utils import cache_response

router = APIRouter(prefix="/meters", tags=["meters"])


@router.post("/", response_model=MeterOut, status_code=status.HTTP_201_CREATED)
async def create_meter(payload: MeterCreate, db: AsyncSession = Depends(get_db)) -> MeterOut:
    """Create a new meter (no caching for writes)."""
    meter = Meter(
        name=payload.name,
        location=payload.location,
        serial_number=payload.serial_number,
        type=payload.type,
        site_id=payload.site_id,
    )
    db.add(meter)
    await db.commit()
    await db.refresh(meter)
    return MeterOut.model_validate(meter)


@router.get("/", response_model=list[MeterOut])
@cache_response(ttl=60)
async def list_meters(db: AsyncSession = Depends(get_db)) -> list[MeterOut]:
    """Return all meters."""
    res = await db.execute(select(Meter))
    items = res.scalars().all()
    return [MeterOut.model_validate(m) for m in items]


@router.get("/{meter_id}", response_model=MeterOut)
@cache_response(ttl=60)
async def get_meter(meter_id: int, db: AsyncSession = Depends(get_db)) -> MeterOut:
    """Retrieve a single meter by ID."""
    res = await db.execute(select(Meter).where(Meter.id == meter_id))
    meter = res.scalar_one_or_none()
    if meter is None:
        raise HTTPException(status_code=404, detail="Meter not found")
    return MeterOut.model_validate(meter)
