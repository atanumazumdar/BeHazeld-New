"""
alembic/env.py — Migration environment.

Works with both SQLite (dev) and MS SQL Server (production).
DATABASE_URL env var always takes precedence over alembic.ini.

SQLite  batch mode  is ENABLED  for sqlite:// URLs (needed for ALTER TABLE).
SQL Server batch mode is DISABLED (SQL Server has full ALTER TABLE support).
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Import all models so Alembic can diff against current metadata
from app.models import Base  # noqa: F401

# ── Alembic config ────────────────────────────────────────────────────
config = context.config

# Allow DATABASE_URL env var to override alembic.ini (production override)
db_url: str = os.getenv(
    "DATABASE_URL",
    config.get_main_option("sqlalchemy.url", "sqlite:///./store.db"),
)
config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# batch mode required only for SQLite (which lacks full ALTER TABLE support)
_use_batch = db_url.startswith("sqlite")


# ── Offline mode (generate SQL script without connecting) ─────────────
def run_migrations_offline() -> None:
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_use_batch,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (apply migrations directly to DB) ─────────────────────
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=_use_batch,   # False for SQL Server
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
