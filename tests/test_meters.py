# tests/test_meters.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.db import Base
from app.core.deps import get_db

# Use a shared in-memory SQLite database.
# StaticPool ensures the same connection is reused across sessions.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
)
AsyncSessionTest = async_sessionmaker(engine_test, expire_on_commit=False)

# Override the app's dependency to use our test session factory
async def override_get_db():
    async with AsyncSessionTest() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db


# Make sure tables exist before any test runs, and dispose after.
@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_test_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine_test.dispose()

transport = ASGITransport(app=app)

@pytest.mark.asyncio
async def test_create_meter():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {"name": "Test Meter", "location": "Test Lab"}
        response = await ac.post("/meters/", json=payload)
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Test Meter"
        assert "id" in body


@pytest.mark.asyncio
async def test_list_meters():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/meters/")
        assert response.status_code == 200
        meters = response.json()
        assert isinstance(meters, list)
        assert any(m["name"] == "Test Meter" for m in meters)


@pytest.mark.asyncio
async def test_get_meter_by_id():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        list_response = await ac.get("/meters/")
        assert list_response.status_code == 200
        meters = list_response.json()
        meter_id = meters[0]["id"]

        response = await ac.get(f"/meters/{meter_id}")
        assert response.status_code == 200
        assert response.json()["id"] == meter_id
