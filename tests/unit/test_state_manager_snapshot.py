"""Unit tests: StateManager (Cycle 6.7a read-only snapshot source).

Covers:
  - snapshot() returns a StateSnapshot with consistent values.
  - open_instruments() filters to status='FILLED' for the configured
    account and ignores other accounts.
  - recent_execution_failures_within() counts exactly the broker-
    origin failure transaction_types (ORDER_REJECT, ORDER_TIMEOUT)
    within the window.  ORDER_EXPIRED / ORDER_CREATE / ORDER_FILL are
    NOT counted (L1 semantics).
  - cooloff window boundary behaves correctly (inclusive of cutoff).
  - Cross-account isolation.
  - Empty DB yields zero values.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.domain.state import StateSnapshot
from fx_ai_trading.services.state_manager import StateManager

_NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)

_DDL_ORDERS = """
CREATE TABLE orders (
    order_id          TEXT PRIMARY KEY,
    client_order_id   TEXT,
    trading_signal_id TEXT,
    account_id        TEXT NOT NULL,
    instrument        TEXT NOT NULL,
    account_type      TEXT NOT NULL,
    order_type        TEXT NOT NULL,
    direction         TEXT NOT NULL,
    units             NUMERIC(18,4) NOT NULL,
    status            TEXT NOT NULL,
    submitted_at      TEXT,
    filled_at         TEXT,
    canceled_at       TEXT,
    correlation_id    TEXT,
    created_at        TEXT NOT NULL
)
"""

_DDL_ORDER_TRANSACTIONS = """
CREATE TABLE order_transactions (
    broker_txn_id       TEXT NOT NULL,
    account_id          TEXT NOT NULL,
    order_id            TEXT,
    transaction_type    TEXT NOT NULL,
    transaction_time_utc TEXT NOT NULL,
    payload             TEXT,
    received_at_utc     TEXT NOT NULL,
    PRIMARY KEY (broker_txn_id, account_id)
)
"""


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL_ORDERS))
        conn.execute(text(_DDL_ORDER_TRANSACTIONS))
    yield eng
    eng.dispose()


def _insert_order(
    engine,
    *,
    order_id: str,
    account_id: str,
    instrument: str,
    status: str,
    created_at: datetime = _NOW,
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO orders (
                    order_id, client_order_id, trading_signal_id, account_id,
                    instrument, account_type, order_type, direction, units,
                    status, submitted_at, filled_at, canceled_at,
                    correlation_id, created_at
                ) VALUES (
                    :oid, :coid, :tsid, :aid,
                    :inst, 'demo', 'market', 'buy', 1000,
                    :status, :ts, :ts, NULL,
                    :corr, :ts
                )
                """
            ),
            {
                "oid": order_id,
                "coid": f"{order_id}:{instrument}:s1",
                "tsid": f"ts-{order_id}",
                "aid": account_id,
                "inst": instrument,
                "status": status,
                "ts": created_at.isoformat(),
                "corr": f"corr-{order_id}",
            },
        )


def _insert_txn(
    engine,
    *,
    broker_txn_id: str,
    account_id: str,
    order_id: str,
    transaction_type: str,
    transaction_time_utc: datetime,
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO order_transactions (
                    broker_txn_id, account_id, order_id, transaction_type,
                    transaction_time_utc, payload, received_at_utc
                ) VALUES (
                    :btxid, :aid, :oid, :ttype,
                    :ttu, '{}', :ttu
                )
                """
            ),
            {
                "btxid": broker_txn_id,
                "aid": account_id,
                "oid": order_id,
                "ttype": transaction_type,
                "ttu": transaction_time_utc.isoformat(),
            },
        )


# --- open_instruments ------------------------------------------------------


class TestOpenInstruments:
    def test_returns_empty_set_when_no_orders(self, engine) -> None:
        sm = StateManager(engine, account_id="acc-1")
        assert sm.open_instruments() == frozenset()

    def test_returns_only_filled_status(self, engine) -> None:
        _insert_order(
            engine, order_id="o1", account_id="acc-1", instrument="EURUSD", status="FILLED"
        )
        _insert_order(
            engine, order_id="o2", account_id="acc-1", instrument="USDJPY", status="CANCELED"
        )
        _insert_order(
            engine, order_id="o3", account_id="acc-1", instrument="GBPUSD", status="FAILED"
        )
        _insert_order(
            engine, order_id="o4", account_id="acc-1", instrument="AUDUSD", status="PENDING"
        )
        sm = StateManager(engine, account_id="acc-1")
        assert sm.open_instruments() == frozenset({"EURUSD"})

    def test_filters_by_account_id(self, engine) -> None:
        _insert_order(
            engine, order_id="o1", account_id="acc-1", instrument="EURUSD", status="FILLED"
        )
        _insert_order(
            engine, order_id="o2", account_id="acc-2", instrument="USDJPY", status="FILLED"
        )
        sm_a = StateManager(engine, account_id="acc-1")
        sm_b = StateManager(engine, account_id="acc-2")
        assert sm_a.open_instruments() == frozenset({"EURUSD"})
        assert sm_b.open_instruments() == frozenset({"USDJPY"})

    def test_dedupes_duplicate_instruments(self, engine) -> None:
        _insert_order(
            engine, order_id="o1", account_id="acc-1", instrument="EURUSD", status="FILLED"
        )
        _insert_order(
            engine, order_id="o2", account_id="acc-1", instrument="EURUSD", status="FILLED"
        )
        sm = StateManager(engine, account_id="acc-1")
        assert sm.open_instruments() == frozenset({"EURUSD"})


# --- recent_execution_failures_within --------------------------------------


class TestRecentExecutionFailures:
    def test_zero_when_no_transactions(self, engine) -> None:
        sm = StateManager(engine, account_id="acc-1")
        assert sm.recent_execution_failures_within(now=_NOW, window_seconds=900) == 0

    def test_counts_order_reject_and_order_timeout(self, engine) -> None:
        _insert_txn(
            engine,
            broker_txn_id="t1",
            account_id="acc-1",
            order_id="o1",
            transaction_type="ORDER_REJECT",
            transaction_time_utc=_NOW - timedelta(seconds=60),
        )
        _insert_txn(
            engine,
            broker_txn_id="t2",
            account_id="acc-1",
            order_id="o2",
            transaction_type="ORDER_TIMEOUT",
            transaction_time_utc=_NOW - timedelta(seconds=120),
        )
        sm = StateManager(engine, account_id="acc-1")
        assert sm.recent_execution_failures_within(now=_NOW, window_seconds=900) == 2

    def test_excludes_order_expired_ttl_path(self, engine) -> None:
        # L1: ORDER_EXPIRED is NOT broker-origin; do not count it.
        _insert_txn(
            engine,
            broker_txn_id="t1",
            account_id="acc-1",
            order_id="o1",
            transaction_type="ORDER_EXPIRED",
            transaction_time_utc=_NOW - timedelta(seconds=10),
        )
        sm = StateManager(engine, account_id="acc-1")
        assert sm.recent_execution_failures_within(now=_NOW, window_seconds=900) == 0

    def test_excludes_success_transactions(self, engine) -> None:
        _insert_txn(
            engine,
            broker_txn_id="t1",
            account_id="acc-1",
            order_id="o1",
            transaction_type="ORDER_CREATE",
            transaction_time_utc=_NOW - timedelta(seconds=10),
        )
        _insert_txn(
            engine,
            broker_txn_id="t2",
            account_id="acc-1",
            order_id="o1",
            transaction_type="ORDER_FILL",
            transaction_time_utc=_NOW - timedelta(seconds=9),
        )
        sm = StateManager(engine, account_id="acc-1")
        assert sm.recent_execution_failures_within(now=_NOW, window_seconds=900) == 0

    def test_excludes_failures_outside_window(self, engine) -> None:
        # Inside window: 1; outside window: 1.
        _insert_txn(
            engine,
            broker_txn_id="t1",
            account_id="acc-1",
            order_id="o1",
            transaction_type="ORDER_REJECT",
            transaction_time_utc=_NOW - timedelta(seconds=100),
        )
        _insert_txn(
            engine,
            broker_txn_id="t2",
            account_id="acc-1",
            order_id="o2",
            transaction_type="ORDER_TIMEOUT",
            transaction_time_utc=_NOW - timedelta(seconds=2000),
        )
        sm = StateManager(engine, account_id="acc-1")
        assert sm.recent_execution_failures_within(now=_NOW, window_seconds=900) == 1

    def test_cutoff_is_inclusive(self, engine) -> None:
        # Exact boundary — ts == cutoff should count.
        _insert_txn(
            engine,
            broker_txn_id="t1",
            account_id="acc-1",
            order_id="o1",
            transaction_type="ORDER_REJECT",
            transaction_time_utc=_NOW - timedelta(seconds=900),
        )
        sm = StateManager(engine, account_id="acc-1")
        assert sm.recent_execution_failures_within(now=_NOW, window_seconds=900) == 1

    def test_filters_by_account_id(self, engine) -> None:
        _insert_txn(
            engine,
            broker_txn_id="t1",
            account_id="acc-1",
            order_id="o1",
            transaction_type="ORDER_REJECT",
            transaction_time_utc=_NOW - timedelta(seconds=10),
        )
        _insert_txn(
            engine,
            broker_txn_id="t2",
            account_id="acc-2",
            order_id="o2",
            transaction_type="ORDER_TIMEOUT",
            transaction_time_utc=_NOW - timedelta(seconds=10),
        )
        assert (
            StateManager(engine, account_id="acc-1").recent_execution_failures_within(
                now=_NOW, window_seconds=900
            )
            == 1
        )
        assert (
            StateManager(engine, account_id="acc-2").recent_execution_failures_within(
                now=_NOW, window_seconds=900
            )
            == 1
        )

    def test_zero_when_window_is_zero(self, engine) -> None:
        _insert_txn(
            engine,
            broker_txn_id="t1",
            account_id="acc-1",
            order_id="o1",
            transaction_type="ORDER_REJECT",
            transaction_time_utc=_NOW,
        )
        sm = StateManager(engine, account_id="acc-1")
        assert sm.recent_execution_failures_within(now=_NOW, window_seconds=0) == 0


# --- snapshot --------------------------------------------------------------


class TestSnapshot:
    def test_empty_state(self, engine) -> None:
        sm = StateManager(engine, account_id="acc-1")
        snap = sm.snapshot(now=_NOW, cooloff_window_seconds=900)
        assert isinstance(snap, StateSnapshot)
        assert snap.open_instruments == frozenset()
        assert snap.concurrent_count == 0
        assert snap.recent_failure_count == 0
        assert snap.snapshot_time_utc == _NOW

    def test_groups_all_three_views(self, engine) -> None:
        _insert_order(
            engine, order_id="o1", account_id="acc-1", instrument="EURUSD", status="FILLED"
        )
        _insert_order(
            engine, order_id="o2", account_id="acc-1", instrument="USDJPY", status="FILLED"
        )
        _insert_txn(
            engine,
            broker_txn_id="t1",
            account_id="acc-1",
            order_id="ox",
            transaction_type="ORDER_REJECT",
            transaction_time_utc=_NOW - timedelta(seconds=5),
        )
        _insert_txn(
            engine,
            broker_txn_id="t2",
            account_id="acc-1",
            order_id="oy",
            transaction_type="ORDER_TIMEOUT",
            transaction_time_utc=_NOW - timedelta(seconds=200),
        )

        snap = StateManager(engine, account_id="acc-1").snapshot(
            now=_NOW, cooloff_window_seconds=900
        )
        assert snap.open_instruments == frozenset({"EURUSD", "USDJPY"})
        assert snap.concurrent_count == 2
        assert snap.recent_failure_count == 2

    def test_concurrent_count_equals_len_open_instruments(self, engine) -> None:
        # 6.7a invariant: paper-mode one-instrument ⇔ one-position.
        for i, sym in enumerate(("EURUSD", "USDJPY", "GBPUSD")):
            _insert_order(
                engine, order_id=f"o-{i}", account_id="acc-1", instrument=sym, status="FILLED"
            )
        snap = StateManager(engine, account_id="acc-1").snapshot(
            now=_NOW, cooloff_window_seconds=900
        )
        assert snap.concurrent_count == len(snap.open_instruments) == 3

    def test_cross_account_isolation(self, engine) -> None:
        _insert_order(
            engine, order_id="o1", account_id="acc-1", instrument="EURUSD", status="FILLED"
        )
        _insert_txn(
            engine,
            broker_txn_id="t1",
            account_id="acc-2",
            order_id="o2",
            transaction_type="ORDER_REJECT",
            transaction_time_utc=_NOW - timedelta(seconds=10),
        )

        snap_a = StateManager(engine, account_id="acc-1").snapshot(
            now=_NOW, cooloff_window_seconds=900
        )
        snap_b = StateManager(engine, account_id="acc-2").snapshot(
            now=_NOW, cooloff_window_seconds=900
        )
        assert snap_a.open_instruments == frozenset({"EURUSD"})
        assert snap_a.recent_failure_count == 0
        assert snap_b.open_instruments == frozenset()
        assert snap_b.recent_failure_count == 1
