# scripts/init_db.py
from __future__ import annotations

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings
from app.models.base import Base
from scripts.seed_demo import seed  # reuse your seeding logic


async def init_db() -> None:
    print(f"[init_db] Using database: {settings.database_url}")

    engine = create_async_engine(settings.database_url, echo=False, future=True)

    async with engine.begin() as conn:
        print("[init_db] Creating all tables (if missing)...")
        await conn.run_sync(Base.metadata.create_all)

        # ✅ Ensure Stage 2.5 columns exist in system_metrics
        print("[init_db] Verifying system_metrics columns...")
        try:
            result = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='system_metrics';")
            )
            existing_cols = {row[0] for row in result.fetchall()}
            required_cols = {"cpu_percent", "mem_percent", "uptime_seconds"}

            missing = required_cols - existing_cols
            if missing:
                for col in missing:
                    print(f"[init_db] Adding missing column: {col}")
                    if col == "cpu_percent":
                        await conn.execute(text("ALTER TABLE system_metrics ADD COLUMN cpu_percent DOUBLE PRECISION DEFAULT 0;"))
                    elif col == "mem_percent":
                        await conn.execute(text("ALTER TABLE system_metrics ADD COLUMN mem_percent DOUBLE PRECISION DEFAULT 0;"))
                    elif col == "uptime_seconds":
                        await conn.execute(text("ALTER TABLE system_metrics ADD COLUMN uptime_seconds DOUBLE PRECISION DEFAULT 0;"))
                print("[init_db] ✅ Schema updated with missing telemetry columns.")
            else:
                print("[init_db] All telemetry columns already exist.")
        except Exception as e:
            print(f"[init_db] ⚠️ Column verification skipped or failed: {e}")

    print("[init_db] Tables verified successfully.")

    # Optional demo data seed
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
    print("[init_db] Database initialization complete.")


if __name__ == "__main__":
    asyncio.run(init_db())
