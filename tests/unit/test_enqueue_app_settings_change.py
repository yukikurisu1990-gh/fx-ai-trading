"""Unit tests for enqueue_app_settings_change (M26 Phase 2).

Verifies argument validation, SQL shape, and that the function never
touches app_settings (only inserts into app_settings_changes).

Uses an in-memory SQLite engine — no DATABASE_URL required.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import WallClock
from fx_ai_trading.services.dashboard_query_service import (
    enqueue_app_settings_change,
)

_DDL = [
    """CREATE TABLE app_settings (
        name        TEXT PRIMARY KEY,
        value       TEXT NOT NULL,
        type        TEXT NOT NULL,
        description TEXT
    )""",
    """CREATE TABLE app_settings_changes (
        app_settings_change_id TEXT PRIMARY KEY,
        name                   TEXT NOT NULL,
        old_value              TEXT,
        new_value              TEXT NOT NULL,
        changed_by             TEXT,
        reason                 TEXT,
        changed_at             TEXT NOT NULL
    )""",
]


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        for ddl in _DDL:
            conn.execute(text(ddl))
        conn.execute(
            text(
                "INSERT INTO app_settings (name, value, type, description)"
                " VALUES ('risk_per_trade_pct', '1.0', 'float', 'risk cap')"
            )
        )
    yield eng
    eng.dispose()


class TestArgumentValidation:
    def test_none_engine_raises(self) -> None:
        with pytest.raises(ValueError, match="engine is required"):
            enqueue_app_settings_change(
                None,
                name="risk_per_trade_pct",
                old_value="1.0",
                new_value="1.5",
                changed_by="op",
                reason="test",
            )

    def test_empty_name_raises(self, engine) -> None:
        with pytest.raises(ValueError, match="name must be non-empty"):
            enqueue_app_settings_change(
                engine,
                name="",
                old_value="1.0",
                new_value="1.5",
                changed_by="op",
                reason="test",
            )

    def test_whitespace_name_raises(self, engine) -> None:
        with pytest.raises(ValueError, match="name must be non-empty"):
            enqueue_app_settings_change(
                engine,
                name="   ",
                old_value="1.0",
                new_value="1.5",
                changed_by="op",
                reason="test",
            )

    def test_empty_new_value_raises(self, engine) -> None:
        with pytest.raises(ValueError, match="new_value must be non-empty"):
            enqueue_app_settings_change(
                engine,
                name="risk_per_trade_pct",
                old_value="1.0",
                new_value="",
                changed_by="op",
                reason="test",
            )

    def test_whitespace_new_value_raises(self, engine) -> None:
        with pytest.raises(ValueError, match="new_value must be non-empty"):
            enqueue_app_settings_change(
                engine,
                name="risk_per_trade_pct",
                old_value="1.0",
                new_value="   ",
                changed_by="op",
                reason="test",
            )


class TestInsertShape:
    def test_returns_one_on_success(self, engine) -> None:
        count = enqueue_app_settings_change(
            engine,
            name="risk_per_trade_pct",
            old_value="1.0",
            new_value="1.5",
            changed_by="operator (UI)",
            reason="risk reduction",
        )
        assert count == 1

    def test_inserts_all_six_columns(self, engine) -> None:
        enqueue_app_settings_change(
            engine,
            name="risk_per_trade_pct",
            old_value="1.0",
            new_value="1.5",
            changed_by="operator (UI)",
            reason="risk reduction",
        )
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT name, old_value, new_value, changed_by,"
                    " changed_at, reason"
                    " FROM app_settings_changes"
                )
            ).fetchone()
        assert row is not None
        assert row[0] == "risk_per_trade_pct"
        assert row[1] == "1.0"
        assert row[2] == "1.5"
        assert row[3] == "operator (UI)"
        assert row[4] is not None  # changed_at populated
        assert row[5] == "risk reduction"

    def test_pk_is_generated_ulid(self, engine) -> None:
        enqueue_app_settings_change(
            engine,
            name="risk_per_trade_pct",
            old_value="1.0",
            new_value="1.5",
            changed_by="op",
            reason="r",
        )
        with engine.connect() as conn:
            pk = conn.execute(
                text("SELECT app_settings_change_id FROM app_settings_changes")
            ).scalar()
        assert pk is not None
        assert isinstance(pk, str)
        assert len(pk) == 26  # ULID length

    def test_changed_at_is_recent_utc(self, engine) -> None:
        clock = WallClock()
        before = clock.now()
        enqueue_app_settings_change(
            engine,
            name="risk_per_trade_pct",
            old_value="1.0",
            new_value="1.5",
            changed_by="op",
            reason="r",
        )
        after = clock.now()
        with engine.connect() as conn:
            ts_str = conn.execute(text("SELECT changed_at FROM app_settings_changes")).scalar()
        # SQLite CURRENT_TIMESTAMP returns naive UTC ISO-8601 (no tzinfo).
        # Round-trip and treat as UTC, then bound-check against wall clock.
        ts = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        # Allow 1s slack on each side: SQLite CURRENT_TIMESTAMP is second-precision.
        assert (before - timedelta(seconds=1)) <= ts <= (after + timedelta(seconds=1))

    def test_old_value_can_be_none(self, engine) -> None:
        count = enqueue_app_settings_change(
            engine,
            name="new_key",
            old_value=None,
            new_value="42",
            changed_by="op",
            reason="initial set",
        )
        assert count == 1
        with engine.connect() as conn:
            old = conn.execute(text("SELECT old_value FROM app_settings_changes")).scalar()
        assert old is None


class TestNeverUpdatesAppSettings:
    def test_app_settings_value_unchanged_after_enqueue(self, engine) -> None:
        with engine.connect() as conn:
            before = conn.execute(
                text("SELECT value FROM app_settings WHERE name = 'risk_per_trade_pct'")
            ).scalar()
        enqueue_app_settings_change(
            engine,
            name="risk_per_trade_pct",
            old_value=before,
            new_value="2.5",
            changed_by="op",
            reason="r",
        )
        with engine.connect() as conn:
            after = conn.execute(
                text("SELECT value FROM app_settings WHERE name = 'risk_per_trade_pct'")
            ).scalar()
        assert before == after, (
            "enqueue_app_settings_change must NOT modify app_settings; "
            "queue is consumed by Supervisor on restart."
        )
