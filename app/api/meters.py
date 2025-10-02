from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models.meter import Meter
from .schemas import MeterCreate, MeterOut

router = APIRouter(prefix="/meters", tags=["meters"])

@router.post("/", response_model=MeterOut, status_code=status.HTTP_201_CREATED)
async def create_meter(payload: MeterCreate, db: AsyncSession = Depends(get_db)) -> MeterOut:
    meter = Meter(name=payload.name, location=payload.location)
    db.add(meter)
    await db.commit()
    await db.refresh(meter)
    return MeterOut.model_validate(meter)

@router.get("/", response_model=list[MeterOut])
async def list_meters(db: AsyncSession = Depends(get_db)) -> list[MeterOut]:
    res = await db.execute(select(Meter))
    meters = res.scalars().all()
    return [MeterOut.model_validate(m) for m in meters]

@router.get("/{meter_id}", response_model=MeterOut)
async def get_meter(meter_id: int, db: AsyncSession = Depends(get_db)) -> MeterOut:
    meter = await db.get(Meter, meter_id)
    if not meter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meter not found")
    return MeterOut.model_validate(meter)
