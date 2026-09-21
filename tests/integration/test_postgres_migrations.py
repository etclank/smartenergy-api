from __future__ import annotations

import os

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from httpx import AsyncClient
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

postgres_url = os.environ.get("TEST_POSTGRES_URL")
if not postgres_url:
    pytest.skip("TEST_POSTGRES_URL is required", allow_module_level=True)
POSTGRES_URL = os.environ["TEST_POSTGRES_URL"]

os.environ["DATABASE_URL"] = POSTGRES_URL
os.environ.setdefault("JWT_SECRET", "postgres-integration-test-secret")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("ENABLE_TELEMETRY", "0")

from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from scripts.adopt_legacy_schema import find_schema_issues  # noqa: E402


@pytest.mark.postgres
@pytest.mark.asyncio
async def test_migrated_postgres_schema_and_readiness() -> None:
    expected_revision = ScriptDirectory.from_config(
        Config("alembic.ini")
    ).get_current_head()
    engine = create_async_engine(POSTGRES_URL)
    try:
        async with engine.connect() as connection:
            table_names = await connection.run_sync(
                lambda sync: set(inspect(sync).get_table_names())
            )
            revision = await connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )
            assert await connection.scalar(text("SELECT 1")) == 1

        assert set(Base.metadata.tables).issubset(table_names)
        assert revision == expected_revision
        assert await find_schema_issues(POSTGRES_URL) == []

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/health/readyz")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
    finally:
        await engine.dispose()
