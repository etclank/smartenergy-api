# tests/conftest.py
import pytest
from httpx import AsyncClient
from app.main import app
from app.core.db import engine
from app.models.base import Base
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# Async test session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@pytest.fixture(scope="session", autouse=True)
async def prepare_database():
    """Create all tables once per test session, then drop them."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture()
async def db_session():
    """Provides a clean async DB session for each test."""
    async with AsyncSessionLocal() as session:
        yield session

@pytest.fixture()
async def client():
    """Provides an Async HTTP client for FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
