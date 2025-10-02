from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_db
from app.models.meter import Meter
from .schemas import MeterCreate, MeterOut

# NEW
import json
from app.cache import get_redis

router = APIRouter(prefix="/meters", tags=["meters"])

@router.post("/", response_model=MeterOut, status_code=status.HTTP_201_CREATED)
async def create_meter(payload: MeterCreate, db: AsyncSession = Depends(get_db)) -> MeterOut:
    meter = Meter(name=payload.name, location=payload.location)
    db.add(meter)
    await db.commit()
    await db.refresh(meter)

    # cache-bust list cache (ignore errors if Redis down)
    try:
        r = await get_redis()
        if r:
            await r.delete("meters:all")
    except Exception:
        pass

    return MeterOut.model_validate(meter)

@router.get("/", response_model=list[MeterOut])
async def list_meters(db: AsyncSession = Depends(get_db)) -> list[MeterOut]:
    cache_key = "meters:all"

    # try cache first (ignore if Redis not present)
    try:
        r = await get_redis()
        if r:
            cached = await r.get(cache_key)
            if cached:
                return [MeterOut.model_validate(m) for m in json.loads(cached)]
    except Exception:
        pass

    # DB query
    res = await db.execute(select(Meter))
    meters = res.scalars().all()
    data = [MeterOut.model_validate(m).model_dump() for m in meters]

    # store in cache for 60s (best-effort)
    try:
        r = await get_redis()
        if r:
            await r.set(cache_key, json.dumps(data), ex=60)
    except Exception:
        pass

    return [MeterOut.model_validate(m) for m in meters]

@router.get("/{meter_id}", response_model=MeterOut)
async def get_meter(meter_id: int, db: AsyncSession = Depends(get_db)) -> MeterOut:
    meter = await db.get(Meter, meter_id)
    if not meter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meter not found")
    return MeterOut.model_validate(meter)