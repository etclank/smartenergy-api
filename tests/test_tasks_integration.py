import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_refresh_kpis_endpoint(authenticated_client):
    resp = await authenticated_client.post("/api/tasks/refresh-kpis")
    assert resp.status_code == status.HTTP_202_ACCEPTED
    data = resp.json()
    assert data["queued"] == "refresh_kpis"


@pytest.mark.asyncio
async def test_generate_demo_data_endpoint(authenticated_client):
    resp = await authenticated_client.post("/api/tasks/demo/generate?days=2")
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert "generate_demo_data" in resp.text


@pytest.mark.asyncio
async def test_clean_demo_data_endpoint(authenticated_client):
    resp = await authenticated_client.post("/api/tasks/demo/clean?older_than_days=1")
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert "clean_demo_data" in resp.text


@pytest.mark.asyncio
async def test_cache_clean_and_warmup(authenticated_client):
    clean = await authenticated_client.post("/api/tasks/cache/clean")
    warm = await authenticated_client.post("/api/tasks/cache/warmup")
    assert clean.status_code == warm.status_code == status.HTTP_202_ACCEPTED


@pytest.mark.asyncio
async def test_metrics_and_meta_update(authenticated_client):
    m = await authenticated_client.post("/api/tasks/metrics/record")
    meta = await authenticated_client.post("/api/tasks/meta/update")
    assert m.status_code == meta.status_code == status.HTTP_202_ACCEPTED


@pytest.mark.asyncio
async def test_backup_and_email_tasks(authenticated_client):
    b = await authenticated_client.post("/api/tasks/backup/db")
    e = await authenticated_client.post("/api/tasks/email/health")
    assert b.status_code == e.status_code == status.HTTP_202_ACCEPTED


@pytest.mark.asyncio
async def test_trigger_record_metrics_endpoint(authenticated_client):
    resp = await authenticated_client.post("/api/tasks/metrics/record")
    assert resp.status_code in (202, 200)
    data = resp.json()
    assert "record" in str(data).lower()
