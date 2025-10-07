from sqlalchemy import Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.models.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.meter import Meter


class EnergyExported(Base):
    __tablename__ = "energy_exported"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    measure_value: Mapped[float] = mapped_column(Float, nullable=False)
    period: Mapped[str | None] = mapped_column(String(10))
    meter_id: Mapped[int] = mapped_column(ForeignKey("meters.id"))

    meter: Mapped["Meter"] = relationship(back_populates="exported_readings")
