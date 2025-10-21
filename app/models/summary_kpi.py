from __future__ import annotations

from datetime import datetime, date
from sqlalchemy import Integer, Float, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.site import Site

class SummaryKPI(Base):
    __tablename__ = "summary_kpi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Daily grain (one row per site per day)
    date: Mapped[date] = mapped_column(Date, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)

    imported_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    exported_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_max_power: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    site: Mapped["Site"] = relationship()

    __table_args__ = (
        UniqueConstraint("site_id", "date", name="uq_summary_kpi_site_id_date"),
    )
