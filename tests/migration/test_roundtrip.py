"""Migration roundtrip test: upgrade head -> downgrade base -> upgrade head.

Requires an explicit opt-in (RUN_DB_INTEGRATION_TESTS=1) *and* a DATABASE_URL
exported by the caller. Tests never read .env; resource presence alone is not
authorization. Skipped otherwise, so CI without a DB is safe.

WARNING: downgrade base drops all 44 D1 tables. Any data in the DB is lost.
If the test fails mid-run, restore with: alembic upgrade head
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from tests.optin import database_url, requires_db

pytestmark = [pytest.mark.db, pytest.mark.destructive, requires_db]


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


@pytest.mark.destructive
def test_migration_roundtrip() -> None:
    """upgrade head -> downgrade base -> upgrade head must succeed with 44 tables."""
    engine = create_engine(database_url())

    # Step 1: ensure we start at head
    _run_alembic("upgrade_head")
    after_first_upgrade = _table_count(engine)
    assert after_first_upgrade == 44, (
        f"Expected 44 tables after initial upgrade, got {after_first_upgrade}"
    )

    # Step 2: downgrade to base (drops all D1 tables)
    _run_alembic("downgrade_base")
    after_downgrade = _table_count(engine)
    assert after_downgrade == 0, f"Expected 0 tables after downgrade base, got {after_downgrade}"

    # Step 3: upgrade back to head — must restore all 44 tables
    _run_alembic("upgrade_head")
    after_second_upgrade = _table_count(engine)
    assert after_second_upgrade == 44, (
        f"Expected 44 tables after re-upgrade, got {after_second_upgrade}"
    )

    engine.dispose()
