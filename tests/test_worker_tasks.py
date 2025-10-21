import pytest
from app.tasks.refresh_kpis import refresh_kpis
from app.tasks.metrics_tasks import record_system_metrics

@pytest.mark.asyncio
async def test_refresh_kpis_executes():
    data = await refresh_kpis()
    assert "rows_upserted" in data

@pytest.mark.asyncio
async def test_record_system_metrics_executes():
    data = await record_system_metrics()
    assert "db_latency_ms" in data
