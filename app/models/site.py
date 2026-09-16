from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.meter import Meter
    from app.models.tariff import Tariff


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(200))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    owner: Mapped["User"] = relationship(back_populates="sites")
    meters: Mapped[list["Meter"]] = relationship(
        back_populates="site", cascade="all, delete"
    )
    tariffs: Mapped[list["Tariff"]] = relationship(
        back_populates="site", cascade="all, delete"
    )
