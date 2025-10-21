# app/core/db.py
from __future__ import annotations

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from typing import AsyncGenerator

# ---------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------
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

# ---------------------------------------------------------------------
# Async session factory for FastAPI dependencies
# ---------------------------------------------------------------------
AsyncSessionLocal = sessionmaker(  # type: ignore
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session

# ---------------------------------------------------------------------
# Helpers for background tasks
# ---------------------------------------------------------------------
def get_async_engine() -> AsyncEngine:
    """Return a new async engine (used by Celery/BackgroundTasks)."""
    return create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
        connect_args=connect_args,
        poolclass=poolclass,
    )

def async_sessionmaker_dep(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return an async_sessionmaker bound to the given engine."""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
