# ruff: noqa: E402 -- test environment must be set before application imports
import os
import tempfile

# Set safe configuration before any application import; never use deployment credentials.
_test_directory = tempfile.TemporaryDirectory(prefix="smartenergy-tests-")
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{_test_directory.name}/test.db"
os.environ.update(
    DATABASE_URL=TEST_DATABASE_URL,
    JWT_SECRET="test-secret",
    REDIS_URL=os.environ.get("TEST_REDIS_URL", ""),
    SENDGRID_API_KEY="",
    HEALTH_EMAIL_TO="",
    ENABLE_TELEMETRY="0",
    SEED_DEMO="0",
)

# tests/conftest.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.core import deps  # for dependency override

from app.core import config

# ---------------------------------------------------------------------
# Always use SQLite for testing
# ---------------------------------------------------------------------

# Override global settings so background tasks use SQLite too
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
config.settings.database_url = TEST_DATABASE_URL

engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
TestingSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


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
    await engine.dispose()


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


@pytest.fixture()
async def authenticated_client(client, db_session):
    import uuid
    from app.models import User
    from app.core.security import hash_password, create_access_token

    name = "operator_" + uuid.uuid4().hex[:12]
    user = User(
        username=name,
        email=f"{name}@example.com",
        hashed_password=hash_password("test-password"),
    )
    db_session.add(user)
    await db_session.commit()
    client.headers["Authorization"] = f"Bearer {create_access_token(name)}"
    yield client
    client.headers.pop("Authorization", None)
