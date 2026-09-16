# tests/test_metrics_endpoints.py
import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_prometheus(client):
    """GET /api/metrics should return valid Prometheus exposition text."""
    resp = await client.get("/api/metrics")
    # FastAPI auto-redirects if missing slash
    if resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        resp = await client.get("/api/metrics/")

    assert resp.status_code == status.HTTP_200_OK, resp.text
    body = resp.text

    # Base Prometheus exposition markers
    assert "# HELP" in body
    assert "http_requests_total" in body

    # Allow variation across OS and envs (macOS may omit process metrics)
    assert any(
        key in body
        for key in [
            "process_resident_memory_bytes",
            "process_virtual_memory_bytes",
            "python_info",
        ]
    ), "Expected at least one standard Prometheus process metric"

    # Optional custom counters we define in app/api/metrics.py
    assert "cache_hits_total" in body
    assert "cache_misses_total" in body
