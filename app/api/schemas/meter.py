# app/api/schemas/meter.py
from pydantic import BaseModel, ConfigDict


# ----- Meters -----
class MeterCreate(BaseModel):
    serial_number: str
    type: str
    site_id: int


class MeterOut(MeterCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)
