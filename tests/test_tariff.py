# tests/test_tariff.py
import pytest
from fastapi import status

@pytest.mark.asyncio
async def test_list_tariffs(client):
    """GET /api/tariffs/ should return a list of tariffs."""
    resp = await client.get("/api/tariffs/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert isinstance(data, list)
    if data:
        first = data[0]
        assert "name" in first
        assert "price_per_kwh" in first
        assert "site_id" in first


@pytest.mark.asyncio
async def test_tariffs_filtered_by_site(client):
    """GET /api/tariffs/?site_id={id} should filter tariffs by site."""
    # First, fetch all sites to get a valid site_id
    site_resp = await client.get("/api/sites/")
    assert site_resp.status_code == status.HTTP_200_OK
    sites = site_resp.json()
    if not sites:
        pytest.skip("No sites available to test tariffs filtering.")

    site_id = sites[0]["id"]
    resp = await client.get(f"/api/tariffs/?site_id={site_id}")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert isinstance(data, list)
    for tariff in data:
        assert tariff["site_id"] == site_id
