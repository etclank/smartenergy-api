"""Create the current schema for a disposable local database."""

from __future__ import annotations

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.models import Base


async def init_db() -> None:
    if not settings.database_url.startswith("sqlite"):
        raise RuntimeError(
            "scripts.init_db supports disposable SQLite only; use Alembic migrations"
        )
    engine = create_async_engine(settings.database_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()
    print("[init_db] Disposable database schema created; no migrations or seed ran.")


if __name__ == "__main__":
    asyncio.run(init_db())
