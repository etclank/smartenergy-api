# app/api/schemas/tariff.py
from pydantic import BaseModel, Field
from typing import Optional
from app.api.schemas.site import SiteOut  # reuse nested site info


class TariffBase(BaseModel):
    name: str = Field(default=..., examples=["Standard Tariff"])
    price_per_kwh: float = Field(default=..., examples=[0.175])


class TariffOut(TariffBase):
    id: int
    site_id: int
    site: Optional[SiteOut] = None

    model_config = {"from_attributes": True}
