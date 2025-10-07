# alembic/env.py
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine.url import make_url

from app.core.config import settings
from app.models.meter import Base as MeterBase  # add other metadata here if needed

config = context.config

def _sync_url(url_str: str) -> str:
    """
    Alembic runs with a *sync* engine. Translate any async URL to a sync variant.
    - sqlite+aiosqlite://...  -> sqlite://...
    - postgresql+asyncpg://... -> postgresql+psycopg://...
    - postgresql+psycopg_async://... -> postgresql+psycopg://...
    """
    if not url_str:
        return url_str
    url = make_url(url_str)
    driver = url.drivername

    if driver.startswith("sqlite+aiosqlite"):
        url = url.set(drivername="sqlite")
    elif driver.startswith("postgresql+asyncpg"):
        url = url.set(drivername="postgresql+psycopg")
    elif driver.startswith("postgresql+psycopg_async"):
        url = url.set(drivername="postgresql+psycopg")

    return str(url)

# Inject runtime URL (sync) for Alembic
db_url = _sync_url(settings.database_url)
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Your target metadata
target_metadata = MeterBase.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
