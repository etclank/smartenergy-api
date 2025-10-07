# app/core/db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from typing import AsyncGenerator
# Base is imported in conftest.py where it's needed

# Configure engine
is_sqlite_memory = settings.database_url.startswith("sqlite") and ":memory:" in settings.database_url

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
poolclass = StaticPool if is_sqlite_memory else None

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    connect_args=connect_args,
    poolclass=poolclass,
)

# Async session factory
AsyncSessionLocal = sessionmaker(  # type: ignore
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# FastAPI dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
