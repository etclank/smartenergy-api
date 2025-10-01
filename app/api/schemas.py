from pydantic import BaseModel, ConfigDict

# ----- Meters -----
class MeterCreate(BaseModel):
    name: str
    location: str | None = None

class MeterOut(MeterCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ----- Auth -----
class LoginIn(BaseModel):
    username: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    username: str
