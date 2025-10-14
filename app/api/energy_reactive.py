# app/api/energy_reactive.py
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db
from app.models.energy_reactive import EnergyReactive
from app.api.schemas.energy import EnergyReactiveOut
from app.api.utils.cache_utils import cache_response

router = APIRouter(prefix="/energy_reactive", tags=["energy"])

@router.get("/", response_model=list[EnergyReactiveOut], status_code=status.HTTP_200_OK)
@cache_response(ttl=60)
async def list_energy_reactive(
    meter_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[EnergyReactiveOut]:
    """List reactive energy readings (optionally filtered by meter_id)."""
    stmt = select(EnergyReactive)
    if meter_id:
        stmt = stmt.where(EnergyReactive.meter_id == meter_id)
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [EnergyReactiveOut.model_validate(i) for i in items]
