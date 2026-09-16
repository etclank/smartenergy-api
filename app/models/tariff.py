from sqlalchemy import Integer, String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.site import Site


class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    price_per_kwh: Mapped[float] = mapped_column(Float)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))

    site: Mapped["Site"] = relationship(back_populates="tariffs")
