# app/api/schemas/energy.py
from pydantic import BaseModel, Field
from datetime import datetime

# --- Shared Base ---
class EnergyBase(BaseModel):
    timestamp: datetime = Field(default=..., examples=["2025-10-01T00:00:00Z"])
    measure_value: float = Field(default=..., examples=[1.23])
    meter_id: int = Field(default=..., examples=[1])

class EnergyImportedOut(EnergyBase):
    id: int
    model_config = {"from_attributes": True}

class EnergyExportedOut(EnergyBase):
    id: int
    model_config = {"from_attributes": True}

class EnergyReactiveOut(BaseModel):
    id: int
    timestamp: datetime = Field(default=..., examples=["2025-10-01T00:00:00Z"])
    imported_kvarh: float = Field(default=..., examples=[0.45])
    exported_kvarh: float = Field(default=..., examples=[0.32])
    meter_id: int = Field(default=..., examples=[1])

    model_config = {"from_attributes": True}

class MaxPowerOut(BaseModel):
    id: int
    timestamp: datetime = Field(default=..., examples=["2025-10-01T00:00:00Z"])
    measure_value: float = Field(default=..., examples=[12.5])
    meter_id: int = Field(default=..., examples=[1])

    model_config = {"from_attributes": True}
