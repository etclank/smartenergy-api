# tests/test_metrics_task.py
import pytest
from sqlalchemy import select

from app.tasks.metrics_tasks import record_system_metrics
from app.models.system_metrics import SystemMetrics


@pytest.mark.asyncio
async def test_record_system_metrics_task(db_session):
    """Directly run the metrics task and verify a DB row is created."""
    result = await record_system_metrics()
    assert result["status"] == "ok"
    assert "db_latency_ms" in result
    assert "cpu_percent" in result
    assert "mem_percent" in result
    assert isinstance(result["db_latency_ms"], (int, float))

    # Retrieve last recorded SystemMetrics ORM row
    rows = (
        (
            await db_session.execute(
                select(SystemMetrics).order_by(SystemMetrics.id.desc()).limit(1)
            )
        )
        .scalars()
        .all()
    )
    assert rows, "SystemMetrics table should have at least one entry"

    row = rows[0]
    assert isinstance(row.db_latency_ms, (int, float))
    assert isinstance(row.redis_latency_ms, (int, float))
    assert isinstance(row.cpu_percent, (int, float))
    assert isinstance(row.mem_percent, (int, float))
    assert isinstance(row.uptime_seconds, (int, float))
