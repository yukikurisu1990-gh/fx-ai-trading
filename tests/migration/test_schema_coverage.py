"""Schema coverage tests — verify all 42 D1 tables are declared in migrations.

These tests are DB-free: they parse migration files statically, so they run
in CI without a live PostgreSQL connection.

What is checked:
  - Every op.create_table() call across all revision files is collected.
  - The resulting set must exactly match the 42 D1 tables defined in
    docs/schema_catalog.md (Groups A–I).
  - alembic_version is NOT included (it is Alembic infrastructure, not D1).
"""

from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions"

# Canonical 42 D1 tables (Groups A–I, docs/schema_catalog.md).
EXPECTED_TABLES: frozenset[str] = frozenset(
    [
        # Group A — Reference (4)
        "brokers",
        "accounts",
        "instruments",
        "app_settings",
        # Group B — Market Data (3)
        "market_candles",
        "market_ticks_or_events",
        "economic_events",
        # Group C — Learning / Models (4)
        "model_registry",
        "training_runs",
        "model_evaluations",
        "predictions",
        # Group D — Decision Pipeline (7)
        "strategy_signals",
        "pair_selection_runs",
        "pair_selection_scores",
        "meta_decisions",
        "feature_snapshots",
        "ev_breakdowns",
        "correlation_snapshots",
        # Group E — Execution (4)
        "trading_signals",
        "orders",
        "order_transactions",
        "execution_metrics",
        # Group F — Outcome (2)
        "positions",
        "close_events",
        # Group G — Safety & Observability (9)
        "no_trade_events",
        "drift_events",
        "account_snapshots",
        "risk_events",
        "stream_status",
        "data_quality_events",
        "reconciliation_events",
        "retry_events",
        "anomalies",
        # Group H — Aggregates (4)
        "strategy_performance",
        "meta_strategy_evaluations",
        "daily_metrics",
        "dashboard_top_candidates",
        # Group I — Operations (6)
        "system_jobs",
        "app_runtime_state",
        "outbox_events",
        "notification_outbox",
        "supervisor_events",
        "app_settings_changes",
    ]
)


def _collect_created_tables() -> set[str]:
    """Return the set of table names passed to op.create_table() across all revisions."""
    tables: set[str] = set()
    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        src = path.read_text(encoding="utf-8")
        tables.update(re.findall(r'op\.create_table\(\s*"([^"]+)"', src))
    return tables


def test_total_table_count() -> None:
    """Exactly 43 D1 tables must be created across all migrations."""
    created = _collect_created_tables()
    assert len(created) == 43, (
        f"Expected 43 tables, found {len(created)}. "
        f"Extra: {created - EXPECTED_TABLES}, "
        f"Missing: {EXPECTED_TABLES - created}"
    )


def test_all_expected_tables_present() -> None:
    """Every table in EXPECTED_TABLES must appear in a migration's create_table call."""
    created = _collect_created_tables()
    missing = EXPECTED_TABLES - created
    assert not missing, f"Missing tables in migrations: {sorted(missing)}"


def test_no_unexpected_tables() -> None:
    """No table outside EXPECTED_TABLES should be created (guards against typos)."""
    created = _collect_created_tables()
    extra = created - EXPECTED_TABLES
    assert not extra, f"Unexpected tables in migrations: {sorted(extra)}"


def test_alembic_version_not_in_migrations() -> None:
    """alembic_version must NOT appear in op.create_table() — it is Alembic infrastructure."""
    created = _collect_created_tables()
    assert "alembic_version" not in created
