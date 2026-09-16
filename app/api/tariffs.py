# app/api/tariffs.py
from fastapi import APIRouter, Request, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.deps import get_db
from app.models.tariff import Tariff
from app.api.schemas.tariff import TariffOut
from app.api.utils.cache_utils import cache_response

router = APIRouter(prefix="/tariffs", tags=["tariffs"])


@router.get("/", response_model=list[TariffOut], status_code=status.HTTP_200_OK)
@cache_response(ttl=300)
async def list_tariffs(
    request: Request,
    site_id: int | None = Query(None, description="Filter tariffs by site_id"),
    db: AsyncSession = Depends(get_db),
) -> list[TariffOut]:
    """List all tariffs, optionally filtered by site_id, including related site info."""
    stmt = select(Tariff).options(selectinload(Tariff.site))
    if site_id:
        stmt = stmt.where(Tariff.site_id == site_id)

    res = await db.execute(stmt)
    items = res.scalars().all()
    return [TariffOut.model_validate(i) for i in items]
