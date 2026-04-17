"""Alembic runtime environment for fx-ai-trading (Cycle 14 skeleton).

This module is loaded by the ``alembic`` CLI. It is intentionally minimal
and forward-compatible with the future SQLAlchemy metadata hand-off
scheduled for Cycle 15+ (M2-2, first schema migration).

Scope at Cycle 14 (deliberate limitations):
- ``target_metadata`` is ``None`` because no SQLAlchemy ``Base`` exists
  in ``src/fx_ai_trading/`` yet. Autogenerate will report "No changes"
  for every revision attempted until the first model is introduced.
- The database URL is resolved from the ``DATABASE_URL`` environment
  variable, never from ``alembic.ini``. This follows the Phase 6.19
  config contract (secrets never enter the repository).
- The ``migrations/`` directory is excluded from ruff and custom lint
  (see pyproject.toml ``[tool.ruff] extend-exclude``), so this file is
  intentionally outside the app-layer lint scope.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# When the first SQLAlchemy ``Base`` class is declared (Cycle 15+),
# import it here and replace ``None`` with ``Base.metadata`` so that
# autogenerate can diff the model against the live schema. Example:
#
#     from fx_ai_trading.repositories.base import Base
#     target_metadata = Base.metadata
target_metadata = None


def _get_database_url() -> str:
    """Resolve the database URL from the environment.

    Priority: ``DATABASE_URL`` env var -> ``alembic.ini`` ``sqlalchemy.url``
    (intentionally blank by default). An empty result is tolerated at
    Cycle 14 because no revisions exist yet. Cycle 15+ must reject empty.
    """
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        url = config.get_main_option("sqlalchemy.url") or ""
    return url


def run_migrations_offline() -> None:
    """Run migrations in offline mode (emit SQL without connecting)."""
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode (connect to the DB and apply revisions)."""
    url = _get_database_url()
    configuration = config.get_section(config.config_ini_section, {})
    if url:
        configuration["sqlalchemy.url"] = url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
