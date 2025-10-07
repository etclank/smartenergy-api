# app/api/schemas/meter.py
from pydantic import BaseModel, ConfigDict


class MeterCreate(BaseModel):
    name: str
    location: str | None = None


class MeterOut(MeterCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)
