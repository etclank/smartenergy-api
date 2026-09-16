from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.meter import Meter


class EnergyReactive(Base):
    """
    Represents reactive energy measurements for a meter.
    Contains both imported and exported reactive values.
    """

    __tablename__ = "energy_reactive"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    imported_kvarh: Mapped[float] = mapped_column(Float, nullable=False)
    exported_kvarh: Mapped[float] = mapped_column(Float, nullable=False)
    meter_id: Mapped[int] = mapped_column(ForeignKey("meters.id"))

    meter: Mapped["Meter"] = relationship(back_populates="reactive_readings")
