# tests/test_meters.py
import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_create_meter(authenticated_client):
    """POST /api/meters/ should create a new meter."""
    payload = {
        "name": "Test Meter",
        "location": "Test Location",
        "serial_number": "TEST-001",
        "type": "single-phase",
        "site_id": 1,  # adjust if FK required
    }
    resp = await authenticated_client.post("/api/meters/", json=payload)
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["name"] == "Test Meter"
    assert data["location"] == "Test Location"
    assert data["serial_number"] == "TEST-001"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_meters(authenticated_client):
    """GET /api/meters/ should return a list of meters."""
    resp = await authenticated_client.get("/api/meters/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert "serial_number" in data[0]


@pytest.mark.asyncio
async def test_get_meter_by_id(authenticated_client):
    """GET /api/meters/{id} should retrieve a meter."""
    # Create first
    create_payload = {
        "name": "Test Meter 2",
        "location": "Test Location 2",
        "serial_number": "TEST-002",
        "type": "three-phase",
        "site_id": 1,
    }
    create_resp = await authenticated_client.post("/api/meters/", json=create_payload)
    assert create_resp.status_code == status.HTTP_201_CREATED
    created = create_resp.json()

    # Retrieve by ID
    meter_id = created["id"]
    resp = await authenticated_client.get(f"/api/meters/{meter_id}")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["id"] == meter_id
    assert data["name"] == "Test Meter 2"
    assert data["location"] == "Test Location 2"
    assert data["serial_number"] == "TEST-002"
