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
from pathlib import Path

from alembic import context
from alembic.ddl.impl import DefaultImpl
from dotenv import load_dotenv
from sqlalchemy import Column, MetaData, PrimaryKeyConstraint, Table, Text, engine_from_config, pool

from fx_ai_trading.db.base import Base

# Load .env from repository root before any URL resolution.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


# Alembic's default version_table_impl uses String(32) for version_num, which
# is too short for this project's revision IDs (e.g. 34-char group names).
# Patching at module load time ensures every new DB gets a TEXT column instead,
# so manual pre-creation is never required.  Existing DBs are unaffected because
# Alembic skips creation when alembic_version already exists.
def _version_table_impl_text(
    self,
    *,
    version_table: str,
    version_table_schema,
    version_table_pk: bool,
    **kw,
):
    vt = Table(
        version_table,
        MetaData(),
        Column("version_num", Text, nullable=False),
        schema=version_table_schema,
    )
    if version_table_pk:
        vt.append_constraint(
            PrimaryKeyConstraint("version_num", name=f"{version_table}_pkc")
        )
    return vt


DefaultImpl.version_table_impl = _version_table_impl_text

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Cycle 15+ target_metadata points at the single declarative ``Base`` in
# ``src/fx_ai_trading/db/base.py``. ORM model modules register with this
# metadata simply by being imported here; Cycle 15 itself declares no
# model subclasses because the initial Group A revision uses direct
# ``op.create_table``, so the metadata is empty at this stage.
target_metadata = Base.metadata


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
