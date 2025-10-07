# app/models/meter.py
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base  # ← import the shared Base

class Meter(Base):
    __tablename__ = "meters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
