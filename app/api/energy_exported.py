# app/api/energy_exported.py
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db
from app.models.energy_exported import EnergyExported
from app.api.schemas.energy import EnergyExportedOut

router = APIRouter(prefix="/energy_exported", tags=["energy"])

@router.get("/", response_model=list[EnergyExportedOut], status_code=status.HTTP_200_OK)
async def list_energy_exported(
    meter_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
)  -> list[EnergyExportedOut]:
    """List exported energy readings (optionally filtered by meter_id)."""
    stmt = select(EnergyExported)
    if meter_id:
        stmt = stmt.where(EnergyExported.meter_id == meter_id)
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [EnergyExportedOut.model_validate(i) for i in items]
