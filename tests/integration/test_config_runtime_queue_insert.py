"""Integration tests: Configuration Console Runtime queue insert (M26 Phase 2).

Uses in-memory SQLite seeded with the real app_settings + app_settings_changes
schema (subset). Verifies end-to-end that an enqueued change:
  1. lands in app_settings_changes with all 6 columns populated,
  2. does NOT modify app_settings (queue semantics — applied on restart),
  3. does NOT use any UPDATE statement on app_settings (source-level check).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.services import dashboard_query_service
from fx_ai_trading.services.dashboard_query_service import (
    enqueue_app_settings_change,
)

_DDL = [
    """CREATE TABLE app_settings (
        name        TEXT PRIMARY KEY,
        value       TEXT NOT NULL,
        type        TEXT NOT NULL,
        description TEXT,
        updated_at  TEXT
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

_SEED = [
    ("risk_per_trade_pct", "1.0", "float", "risk cap"),
    ("max_concurrent_positions", "5", "int", "open positions cap"),
    ("expected_account_type", "demo", "string", "broker account type"),
]


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        for ddl in _DDL:
            conn.execute(text(ddl))
        for name, value, type_, desc in _SEED:
            conn.execute(
                text(
                    "INSERT INTO app_settings"
                    " (name, value, type, description, updated_at)"
                    " VALUES (:n, :v, :t, :d, :u)"
                ),
                {
                    "n": name,
                    "v": value,
                    "t": type_,
                    "d": desc,
                    "u": "2026-04-20T00:00:00+00:00",
                },
            )
    yield eng
    eng.dispose()


def test_insert_lands_in_app_settings_changes(engine) -> None:
    enqueue_app_settings_change(
        engine,
        name="risk_per_trade_pct",
        old_value="1.0",
        new_value="1.5",
        changed_by="operator (UI)",
        reason="reduce risk per Iter3 review",
    )
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name, old_value, new_value, changed_by, reason FROM app_settings_changes")
        ).fetchall()
    assert len(rows) == 1
    name, old, new, by, reason = rows[0]
    assert name == "risk_per_trade_pct"
    assert old == "1.0"
    assert new == "1.5"
    assert by == "operator (UI)"
    assert reason == "reduce risk per Iter3 review"


def test_app_settings_is_not_modified(engine) -> None:
    """After enqueue, app_settings.value MUST be unchanged — applied on restart."""
    enqueue_app_settings_change(
        engine,
        name="risk_per_trade_pct",
        old_value="1.0",
        new_value="2.0",
        changed_by="op",
        reason="r",
    )
    with engine.connect() as conn:
        value = conn.execute(
            text("SELECT value FROM app_settings WHERE name = 'risk_per_trade_pct'")
        ).scalar()
    assert value == "1.0"


def test_multiple_inserts_each_get_unique_pk(engine) -> None:
    for new in ("1.1", "1.2", "1.3"):
        enqueue_app_settings_change(
            engine,
            name="risk_per_trade_pct",
            old_value="1.0",
            new_value=new,
            changed_by="op",
            reason="r",
        )
    with engine.connect() as conn:
        pks = [
            row[0]
            for row in conn.execute(
                text("SELECT app_settings_change_id FROM app_settings_changes")
            ).fetchall()
        ]
    assert len(pks) == 3
    assert len(set(pks)) == 3


def test_source_has_no_update_app_settings_statement() -> None:
    """The query service file must not contain UPDATE app_settings ... ."""
    src_path = Path(dashboard_query_service.__file__)
    src = src_path.read_text(encoding="utf-8")
    lower = src.lower()
    forbidden = (
        "update app_settings ",
        "update app_settings\n",
        "update app_settings(",
    )
    for needle in forbidden:
        assert needle not in lower, (
            f"forbidden write path found in dashboard_query_service: {needle!r}"
        )
