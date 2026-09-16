from __future__ import annotations

from datetime import datetime
from sqlalchemy import Integer, String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SummaryEvent(Base):
    __tablename__ = "summary_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True, default=datetime.utcnow
    )

    event_type: Mapped[str] = mapped_column(
        String(100), index=True
    )  # e.g., "kpis.refresh", "cache.clean"
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
