import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.core.security import verify_password
from app.models import User, Meter
from scripts.init_db import init_db
from scripts.seed_demo import seed


@pytest.mark.asyncio
async def test_disposable_initialization_and_explicit_seed(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path}/seed.db"
    monkeypatch.setattr(settings, "database_url", url)
    monkeypatch.setattr(settings, "seed_demo", 1)
    monkeypatch.setattr(settings, "demo_password", "unique-test-password")
    await init_db()
    engine = create_async_engine(url)
    try:
        async with async_sessionmaker(engine)() as session:
            assert await session.scalar(select(func.count(User.id))) == 0

        await seed()
        async with async_sessionmaker(engine)() as session:
            user = await session.scalar(select(User))
            assert verify_password("unique-test-password", user.hashed_password)
            user.email = "preserve@example.com"
            await session.commit()
        await init_db()
        async with async_sessionmaker(engine)() as session:
            assert await session.scalar(select(func.count(Meter.id))) == 6
            assert (await session.scalar(select(User))).email == "preserve@example.com"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_seed_requires_password(tmp_path, monkeypatch):
    monkeypatch.setattr(
        settings, "database_url", f"sqlite+aiosqlite:///{tmp_path}/empty.db"
    )
    monkeypatch.setattr(settings, "seed_demo", 1)
    monkeypatch.setattr(settings, "demo_password", "")
    with pytest.raises(ValueError, match="DEMO_PASSWORD"):
        await seed()


@pytest.mark.asyncio
async def test_disposable_initialization_rejects_postgres(monkeypatch):
    monkeypatch.setattr(
        settings,
        "database_url",
        "postgresql+asyncpg://example.invalid/smartenergy",
    )
    with pytest.raises(RuntimeError, match="use Alembic migrations"):
        await init_db()
