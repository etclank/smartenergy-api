# tests/test_energy_endpoints.py
import pytest
from fastapi import status

@pytest.mark.asyncio
async def test_list_sites(client):
    """GET /api/sites/ should return a list of sites."""
    resp = await client.get("/api/sites/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert "name" in data[0]
        assert "location" in data[0]


@pytest.mark.asyncio
async def test_list_energy_imported(client):
    """GET /api/energy_imported/ should return readings."""
    resp = await client.get("/api/energy_imported/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert "measure_value" in data[0]


@pytest.mark.asyncio
async def test_list_energy_exported(client):
    """GET /api/energy_exported/ should return readings."""
    resp = await client.get("/api/energy_exported/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert "measure_value" in data[0]


@pytest.mark.asyncio
async def test_list_energy_reactive(client):
    """GET /api/energy_reactive/ should return readings."""
    resp = await client.get("/api/energy_reactive/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert "measure_value" in data[0]


@pytest.mark.asyncio
async def test_list_max_power(client):
    """GET /api/max_power/ should return readings."""
    resp = await client.get("/api/max_power/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert "measure_value" in data[0]
