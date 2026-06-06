"""
Alembic migration environment.

This wires Alembic into our application so that:
  - the database URL comes from our `settings` (the .env file), and
  - `target_metadata` points at `Base.metadata`, letting
    `alembic revision --autogenerate` detect model changes automatically.
"""

import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make the backend package importable (env.py runs from inside alembic/).
sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import settings          # noqa: E402
from db.base import Base             # noqa: E402
import models                        # noqa: E402,F401  (registers all tables)

# Alembic Config object, providing access to alembic.ini values.
config = context.config

# Inject our runtime DATABASE_URL so we never duplicate it in alembic.ini.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Set up Python logging per alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata autogenerate compares the database against.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (emits SQL to stdout).

    Useful for generating a SQL script to run elsewhere. Triggered by
    `alembic upgrade head --sql`.
    """
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
    """Run migrations against a live database connection (the usual path)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # detect column type changes on autogenerate
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
