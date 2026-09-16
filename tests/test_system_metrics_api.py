# tests/test_system_metrics_api.py
import pytest
from fastapi import status
from app.models.system_metrics import SystemMetrics


@pytest.mark.asyncio
async def test_system_metrics_latest_and_list(client, db_session):
    """Verify /api/system_metrics/latest and /api/system_metrics/ endpoints."""
    # Insert a sample metric row directly
    m = SystemMetrics(
        db_latency_ms=4,
        redis_latency_ms=2,
        row_counts={"sites": 1},
        cpu_percent=12.3,
        mem_percent=45.6,
        uptime_seconds=321.9,
    )
    db_session.add(m)
    await db_session.commit()

    # Latest endpoint
    latest_resp = await client.get("/api/system_metrics/latest")
    assert latest_resp.status_code == status.HTTP_200_OK
    latest = latest_resp.json()
    assert latest["cpu_percent"] == pytest.approx(12.3, rel=1e-2)
    assert "timestamp" in latest
    assert "row_counts" in latest

    # List endpoint
    list_resp = await client.get("/api/system_metrics/")
    assert list_resp.status_code == status.HTTP_200_OK
    data = list_resp.json()
    assert isinstance(data, list)
    assert data[-1]["cpu_percent"] == pytest.approx(12.3, rel=1e-2)
