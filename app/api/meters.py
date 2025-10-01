from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models.meter import Meter
from app.api.schemas import MeterCreate, MeterOut

router = APIRouter(prefix="/meters")

@router.post("/", response_model=MeterOut, status_code=status.HTTP_201_CREATED)
async def create_meter(payload: MeterCreate, db: AsyncSession = Depends(get_db)):
    m = Meter(name=payload.name, location=payload.location)
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return m  # pydantic orm_mode will serialize

@router.get("/", response_model=list[MeterOut])
async def list_meters(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Meter))
    return list(res.scalars())

@router.get("/{meter_id}", response_model=MeterOut)
async def get_meter(meter_id: int, db: AsyncSession = Depends(get_db)):
    m = await db.get(Meter, meter_id)
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meter not found")
    return m
