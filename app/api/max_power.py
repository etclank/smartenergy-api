# app/api/max_power.py
from fastapi import APIRouter, Request, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db
from app.models.max_power import MaxPower
from app.api.schemas.energy import MaxPowerOut
from app.api.utils.cache_utils import cache_response

router = APIRouter(prefix="/max_power", tags=["energy"])


@router.get("/", response_model=list[MaxPowerOut], status_code=status.HTTP_200_OK)
@cache_response(ttl=120)
async def list_max_power(
    request: Request,
    meter_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[MaxPowerOut]:
    """List max power readings (optionally filtered by meter_id)."""
    stmt = select(MaxPower)
    if meter_id:
        stmt = stmt.where(MaxPower.meter_id == meter_id)
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [MaxPowerOut.model_validate(i) for i in items]
