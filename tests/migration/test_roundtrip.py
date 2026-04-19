"""Migration roundtrip test: upgrade head -> downgrade base -> upgrade head.

Requires a live PostgreSQL connection via DATABASE_URL (from .env or env var).
Skipped automatically when DATABASE_URL is not set, so CI without a DB is safe.

WARNING: downgrade base drops all 43 D1 tables. Any data in the DB is lost.
If the test fails mid-run, restore with: alembic upgrade head
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()


def _table_count(engine) -> int:
    """Return count of user tables in public schema (alembic_version excluded)."""
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT count(*) FROM pg_tables"
                " WHERE schemaname = 'public'"
                " AND tablename != 'alembic_version'"
            )
        )
        return result.scalar()


def _run_alembic(command: str) -> None:
    """Run an alembic command via Python API."""
    from alembic import command as alembic_cmd
    from alembic.config import Config

    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    cfg.set_main_option("script_location", "migrations")
    if command == "upgrade_head":
        alembic_cmd.upgrade(cfg, "head")
    elif command == "downgrade_base":
        alembic_cmd.downgrade(cfg, "base")


@pytest.mark.skipif(not _DATABASE_URL, reason="DATABASE_URL not set — skipping DB tests")
def test_migration_roundtrip() -> None:
    """upgrade head -> downgrade base -> upgrade head must succeed with 43 tables."""
    engine = create_engine(_DATABASE_URL)

    # Step 1: ensure we start at head
    _run_alembic("upgrade_head")
    after_first_upgrade = _table_count(engine)
    assert after_first_upgrade == 43, (
        f"Expected 43 tables after initial upgrade, got {after_first_upgrade}"
    )

    # Step 2: downgrade to base (drops all D1 tables)
    _run_alembic("downgrade_base")
    after_downgrade = _table_count(engine)
    assert after_downgrade == 0, f"Expected 0 tables after downgrade base, got {after_downgrade}"

    # Step 3: upgrade back to head — must restore all 43 tables
    _run_alembic("upgrade_head")
    after_second_upgrade = _table_count(engine)
    assert after_second_upgrade == 43, (
        f"Expected 43 tables after re-upgrade, got {after_second_upgrade}"
    )

    engine.dispose()
