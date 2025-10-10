# scripts/init_db.py
from __future__ import annotations

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.models.base import Base
from scripts.seed_demo import seed  # reuse your seeding logic


async def init_db() -> None:
    print(f"[init_db] Using database: {settings.database_url}")

    # Create async engine
    engine = create_async_engine(settings.database_url, echo=False, future=True)

    async with engine.begin() as conn:
        print("[init_db] Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)

    print("[init_db] Tables created successfully.")

    # Only seed if explicitly enabled
    if str(settings.seed_demo).lower() in {"1", "true", "yes"}:
        try:
            print("[init_db] Seeding demo data...")
            await seed()
            print("[init_db] ✅ Demo data seeded successfully.")
        except Exception as e:
            print(f"[init_db] ⚠️ Seeding failed: {e}")
    else:
        print("[init_db] Skipping demo data seeding (SEED_DEMO disabled).")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
