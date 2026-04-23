"""Unit tests: replay account isolation (replay PR5).

Pins the contract that:
  - A StateManager scoped to a fresh account_id (no rows) returns an empty
    open_position_details(), preventing exit gate from consuming any quote.
  - Exit gate makes zero get_quote() calls when open_position_details() is
    empty — quote exhaustion cannot occur on a clean replay account.
  - Positions accumulated under account A are invisible to a StateManager
    scoped to account B — account isolation is enforced at the query level.
  - seed_account() is idempotent: inserting the same account_id twice does
    not raise and returns False on the second call.
  - seed_account() returns True on first insert and False on subsequent ones.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.price_feed import Quote
from fx_ai_trading.services.exit_gate_runner import run_exit_gate
from fx_ai_trading.services.state_manager import StateManager

_NOW = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)
_OPEN_TIME = _NOW - timedelta(seconds=120)

# ---------------------------------------------------------------------------
# Minimal in-memory schema (no FK to accounts — matches unit test convention)
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE positions (
    position_snapshot_id TEXT PRIMARY KEY,
    order_id             TEXT,
    account_id           TEXT NOT NULL,
    instrument           TEXT NOT NULL,
    event_type           TEXT NOT NULL,
    units                NUMERIC(18,4) NOT NULL,
    avg_price            NUMERIC(18,8),
    unrealized_pl        NUMERIC(18,8),
    realized_pl          NUMERIC(18,8),
    event_time_utc       TEXT NOT NULL,
    correlation_id       TEXT
);
CREATE TABLE orders (
    order_id  TEXT PRIMARY KEY,
    direction TEXT NOT NULL
);
CREATE TABLE close_events (
    close_event_id       TEXT PRIMARY KEY,
    order_id             TEXT NOT NULL,
    position_snapshot_id TEXT,
    reasons              TEXT NOT NULL,
    primary_reason_code  TEXT NOT NULL,
    closed_at            TEXT NOT NULL,
    pnl_realized         NUMERIC(18,8),
    correlation_id       TEXT
);
CREATE TABLE order_transactions (
    broker_txn_id        TEXT NOT NULL,
    account_id           TEXT NOT NULL,
    order_id             TEXT,
    transaction_type     TEXT NOT NULL,
    transaction_time_utc TEXT NOT NULL,
    payload              TEXT,
    received_at_utc      TEXT NOT NULL,
    PRIMARY KEY (broker_txn_id, account_id)
);
CREATE TABLE secondary_sync_outbox (
    outbox_id       TEXT PRIMARY KEY,
    table_name      TEXT NOT NULL,
    primary_key     TEXT NOT NULL,
    version_no      BIGINT NOT NULL DEFAULT 0,
    payload_json    TEXT NOT NULL,
    enqueued_at     TEXT NOT NULL,
    acked_at        TEXT,
    last_error      TEXT,
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT,
    run_id          TEXT,
    environment     TEXT,
    code_version    TEXT,
    config_version  TEXT
);
"""

_DDL_ACCOUNTS = """
CREATE TABLE accounts (
    account_id    TEXT PRIMARY KEY,
    broker_id     TEXT NOT NULL,
    account_type  TEXT NOT NULL,
    base_currency TEXT NOT NULL
);
"""


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        for stmt in _DDL.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
    yield eng
    eng.dispose()


@pytest.fixture
def engine_with_accounts(engine):
    with engine.begin() as conn:
        conn.execute(text(_DDL_ACCOUNTS.strip()))
    return engine


def _seed_position(engine, *, account_id: str, instrument: str = "EUR_USD") -> None:
    order_id = f"ord-{account_id}-{instrument}"
    with engine.begin() as conn:
        conn.execute(
            text("INSERT OR IGNORE INTO orders (order_id, direction) VALUES (:oid, 'buy')"),
            {"oid": order_id},
        )
        conn.execute(
            text(
                "INSERT INTO positions"
                " (position_snapshot_id, order_id, account_id, instrument,"
                "  event_type, units, avg_price, event_time_utc)"
                " VALUES (:psid, :oid, :acct, :instr, 'open', 1000, 1.10, :ts)"
            ),
            {
                "psid": f"ps-{account_id}-{instrument}",
                "oid": order_id,
                "acct": account_id,
                "instr": instrument,
                "ts": _OPEN_TIME.isoformat(),
            },
        )


# ---------------------------------------------------------------------------
# StateManager account isolation
# ---------------------------------------------------------------------------


class TestStateManagerAccountIsolation:
    def test_fresh_account_returns_no_open_positions(self, engine) -> None:
        sm = StateManager(engine, account_id="acct-replay-eval", clock=FixedClock(_NOW))
        assert sm.open_position_details() == []

    def test_fresh_account_returns_no_open_instruments(self, engine) -> None:
        sm = StateManager(engine, account_id="acct-replay-eval", clock=FixedClock(_NOW))
        assert sm.open_instruments() == frozenset()

    def test_positions_for_other_account_not_visible(self, engine) -> None:
        _seed_position(engine, account_id="acct-paper-eval", instrument="EUR_USD")

        replay_sm = StateManager(engine, account_id="acct-replay-eval", clock=FixedClock(_NOW))
        assert replay_sm.open_position_details() == []

    def test_paper_account_positions_remain_visible_to_itself(self, engine) -> None:
        _seed_position(engine, account_id="acct-paper-eval", instrument="EUR_USD")

        paper_sm = StateManager(engine, account_id="acct-paper-eval", clock=FixedClock(_NOW))
        positions = paper_sm.open_position_details()
        assert len(positions) == 1
        assert positions[0].instrument == "EUR_USD"


# ---------------------------------------------------------------------------
# Exit gate makes zero get_quote() calls when account has no positions
# ---------------------------------------------------------------------------


class _CountingQuoteFeed:
    """Records every get_quote() call."""

    def __init__(self) -> None:
        self.call_count = 0

    def get_quote(self, instrument: str) -> Quote:  # noqa: ARG002
        self.call_count += 1
        return Quote(
            price=1.10,
            ts=_NOW,
            source="oanda_rest_snapshot",
        )


class TestExitGateQuoteConsumptionWithCleanAccount:
    def test_zero_positions_means_zero_get_quote_calls(self, engine) -> None:
        sm = StateManager(engine, account_id="acct-replay-eval", clock=FixedClock(_NOW))
        feed = _CountingQuoteFeed()
        broker = MagicMock()
        exit_policy = MagicMock()

        results = run_exit_gate(
            broker=broker,
            account_id="acct-replay-eval",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=exit_policy,
            quote_feed=feed,
            stale_max_age_seconds=99999.0,
        )

        assert results == []
        assert feed.call_count == 0

    def test_dirty_account_consumes_quote_per_position(self, engine) -> None:
        _seed_position(engine, account_id="acct-paper-eval", instrument="EUR_USD")
        sm = StateManager(engine, account_id="acct-paper-eval", clock=FixedClock(_NOW))
        feed = _CountingQuoteFeed()
        exit_policy = MagicMock()
        exit_policy.evaluate.return_value = MagicMock(
            should_exit=False,
            reasons=[],
            primary_reason=None,
        )
        broker = MagicMock()

        run_exit_gate(
            broker=broker,
            account_id="acct-paper-eval",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=exit_policy,
            quote_feed=feed,
            stale_max_age_seconds=99999.0,
        )

        assert feed.call_count >= 1


# ---------------------------------------------------------------------------
# seed_account() idempotency
# ---------------------------------------------------------------------------


class TestSeedAccountIdempotency:
    def test_first_insert_returns_true(self, engine_with_accounts) -> None:
        import importlib.util
        import sys
        from pathlib import Path

        _repo_root = Path(__file__).resolve().parents[2]
        alias = "_seed_replay_account_test"
        if alias not in sys.modules:
            spec = importlib.util.spec_from_file_location(
                alias, _repo_root / "scripts" / "seed_replay_account.py"
            )
            assert spec and spec.loader
            mod = importlib.util.module_from_spec(spec)
            sys.modules[alias] = mod
            spec.loader.exec_module(mod)
        mod = sys.modules[alias]

        inserted = mod.seed_account(
            engine=engine_with_accounts,
            account_id="acct-replay-eval",
            broker_id="paper",
            account_type="demo",
            base_currency="USD",
        )
        assert inserted is True

    def test_second_insert_returns_false_and_does_not_raise(self, engine_with_accounts) -> None:
        import sys

        mod = sys.modules["_seed_replay_account_test"]

        mod.seed_account(
            engine=engine_with_accounts,
            account_id="acct-replay-eval",
            broker_id="paper",
            account_type="demo",
            base_currency="USD",
        )
        inserted = mod.seed_account(
            engine=engine_with_accounts,
            account_id="acct-replay-eval",
            broker_id="paper",
            account_type="demo",
            base_currency="USD",
        )
        assert inserted is False

    def test_account_row_is_present_after_seed(self, engine_with_accounts) -> None:
        import sys

        mod = sys.modules["_seed_replay_account_test"]

        mod.seed_account(
            engine=engine_with_accounts,
            account_id="acct-replay-eval",
            broker_id="paper",
            account_type="demo",
            base_currency="USD",
        )
        with engine_with_accounts.connect() as conn:
            row = conn.execute(
                text("SELECT account_id FROM accounts WHERE account_id = 'acct-replay-eval'")
            ).fetchone()
        assert row is not None
