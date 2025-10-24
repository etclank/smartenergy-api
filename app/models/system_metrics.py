# app/models/system_metrics.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Integer, DateTime, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class SystemMetrics(Base):
    __tablename__ = "system_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True, default=datetime.utcnow
    )

    db_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    redis_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    row_counts: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    cpu_percent: Mapped[float] = mapped_column(Float, nullable=True, default=None)
    mem_percent: Mapped[float] = mapped_column(Float, nullable=True, default=None)
    uptime_seconds: Mapped[float] = mapped_column(Float, nullable=True, default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
