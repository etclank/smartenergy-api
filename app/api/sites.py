# app/api/sites.py
from fastapi import APIRouter, Request, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db
from app.models.site import Site
from app.api.schemas.site import SiteOut
from app.api.utils.cache_utils import cache_response

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("/", response_model=list[SiteOut], status_code=status.HTTP_200_OK)
@cache_response(ttl=60)
async def list_sites(
    request: Request, db: AsyncSession = Depends(get_db)
) -> list[SiteOut]:
    """Return all available sites."""
    res = await db.execute(select(Site))
    items = res.scalars().all()
    return [SiteOut.model_validate(s) for s in items]
