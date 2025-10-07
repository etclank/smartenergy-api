# app/api/schemas/site.py
from pydantic import BaseModel, Field

class SiteBase(BaseModel):
    name: str = Field(default=..., examples=["Main Campus"])
    location: str | None = Field(default=None, examples=["Madrid, Spain"])

class SiteOut(SiteBase):
    id: int

    model_config = {"from_attributes": True}

