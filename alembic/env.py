"""Alembic environment.

Reads the database URL from the application's :class:`Settings` so that
``alembic.ini`` does not need to duplicate it.
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make `src` importable when running alembic from the project root.
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from src.core.config import settings  # noqa: E402
from src.core.database import Base  # noqa: E402

# Importing the model modules registers them on Base.metadata so that
# autogenerate sees every table.
from src.apps.rbac import models as _rbac_models  # noqa: E402,F401
from src.apps.users import models as _user_models  # noqa: E402,F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


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
            compare_type=True,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
