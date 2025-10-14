# tests/conftest.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.core import deps  # for dependency override

# ---------------------------------------------------------------------
# Always use SQLite for testing
# ---------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
TestingSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# ---------------------------------------------------------------------
# Dependency override
# ---------------------------------------------------------------------
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture(scope="session", autouse=True)
async def prepare_database():
    """Create all tables once per test session, then drop them at the end."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Apply FastAPI dependency override
    app.dependency_overrides[deps.get_db] = override_get_db

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.clear()


@pytest.fixture()
async def db_session():
    """Provide a clean async DB session per test."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture()
async def client():
    """Async HTTP client for FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
