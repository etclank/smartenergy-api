from __future__ import annotations

import os
import subprocess
import sys

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.models import Base
from scripts.adopt_legacy_schema import find_schema_issues


@pytest.mark.asyncio
async def test_compatible_legacy_schema_can_be_validated_and_stamped(tmp_path):
    database_url = f"sqlite+aiosqlite:///{tmp_path}/compatible.db"
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()

    assert await find_schema_issues(database_url) == []

    environment = os.environ | {
        "DATABASE_URL": database_url,
        "JWT_SECRET": "legacy-adoption-test-secret",
    }
    result = subprocess.run(
        [sys.executable, "-m", "scripts.adopt_legacy_schema", "--stamp"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        tables = await connection.run_sync(
            lambda sync: set(inspect(sync).get_table_names())
        )
    await engine.dispose()
    assert "alembic_version" in tables


@pytest.mark.asyncio
async def test_incompatible_legacy_schema_is_not_stamped(tmp_path):
    database_url = f"sqlite+aiosqlite:///{tmp_path}/incompatible.db"
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.tables["users"].create)
    await engine.dispose()

    issues = await find_schema_issues(database_url)
    assert any(issue.startswith("missing tables:") for issue in issues)

    environment = os.environ | {
        "DATABASE_URL": database_url,
        "JWT_SECRET": "legacy-adoption-test-secret",
    }
    result = subprocess.run(
        [sys.executable, "-m", "scripts.adopt_legacy_schema", "--stamp"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1

    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        tables = await connection.run_sync(
            lambda sync: set(inspect(sync).get_table_names())
        )
    await engine.dispose()
    assert "alembic_version" not in tables
