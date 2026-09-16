from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.site import Site
    from app.models.energy_imported import EnergyImported
    from app.models.energy_exported import EnergyExported
    from app.models.energy_reactive import EnergyReactive
    from app.models.max_power import MaxPower


class Meter(Base):
    __tablename__ = "meters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(200))
    serial_number: Mapped[str] = mapped_column(String(50), unique=True)
    type: Mapped[str] = mapped_column(String(50))
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))

    site: Mapped["Site"] = relationship(back_populates="meters")

    imported_readings: Mapped[list["EnergyImported"]] = relationship(
        back_populates="meter", cascade="all, delete"
    )
    exported_readings: Mapped[list["EnergyExported"]] = relationship(
        back_populates="meter", cascade="all, delete"
    )
    reactive_readings: Mapped[list["EnergyReactive"]] = relationship(
        back_populates="meter", cascade="all, delete"
    )
    max_power_readings: Mapped[list["MaxPower"]] = relationship(
        back_populates="meter", cascade="all, delete"
    )
