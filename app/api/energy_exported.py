# app/api/energy_imported.py
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db
from app.models.energy_imported import EnergyImported
from app.api.schemas.energy import EnergyImportedOut
from app.api.utils.cache_utils import cache_response

router = APIRouter(prefix="/energy_imported", tags=["energy"])

@router.get("/", response_model=list[EnergyImportedOut], status_code=status.HTTP_200_OK)
@cache_response(ttl=60)
async def list_energy_imported(
    meter_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[EnergyImportedOut]:
    """List imported energy readings (optionally filtered by meter_id)."""
    stmt = select(EnergyImported)
    if meter_id:
        stmt = stmt.where(EnergyImported.meter_id == meter_id)
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [EnergyImportedOut.model_validate(i) for i in items]
