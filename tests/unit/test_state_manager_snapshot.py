"""Unit tests: StateManager read-only surface (Cycle 6.7a/b).

Covers:
  open_instruments():
    - Reads from the positions timeline (6.7b source switch).
    - 'open'/'add' events make an instrument visible; 'close' hides it.
    - Filters by account_id; cross-account rows are invisible.
    - An instrument with both an open and a later close event is not open.
    - An instrument with only a close event is not open.
    - Empty positions table → frozenset().

  recent_execution_failures_within():
    - ORDER_REJECT + ORDER_TIMEOUT counted (L1 broker-origin only).
    - ORDER_EXPIRED / ORDER_CREATE / ORDER_FILL NOT counted.
    - Window boundary inclusive.
    - Cross-account isolation.
    - window_seconds=0 → 0.

  snapshot():
    - Returns StateSnapshot with consistent values.
    - concurrent_count == len(open_instruments) (M10 paper-mode invariant).
    - Cross-account isolation end-to-end.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.domain.state import StateSnapshot
from fx_ai_trading.services.state_manager import StateManager

_NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)

_DDL_POSITIONS = """
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
)
"""

_DDL_ORDER_TRANSACTIONS = """
CREATE TABLE order_transactions (
    broker_txn_id        TEXT NOT NULL,
    account_id           TEXT NOT NULL,
    order_id             TEXT,
    transaction_type     TEXT NOT NULL,
    transaction_time_utc TEXT NOT NULL,
    payload              TEXT,
    received_at_utc      TEXT NOT NULL,
    PRIMARY KEY (broker_txn_id, account_id)
)
"""


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL_POSITIONS))
        conn.execute(text(_DDL_ORDER_TRANSACTIONS))
    yield eng
    eng.dispose()


def _insert_position(
    engine,
    *,
    psid: str,
    account_id: str,
    instrument: str,
    event_type: str,
    order_id: str = "prev-o",
    event_time_utc: datetime = _NOW,
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO positions (
                    position_snapshot_id, order_id, account_id, instrument,
                    event_type, units, avg_price, unrealized_pl, realized_pl,
                    event_time_utc, correlation_id
                ) VALUES (
                    :psid, :oid, :aid, :inst,
                    :etype, 1000, 1.1, NULL, NULL,
                    :ts, NULL
                )
                """
            ),
            {
                "psid": psid,
                "oid": order_id,
                "aid": account_id,
                "inst": instrument,
                "etype": event_type,
                "ts": event_time_utc.isoformat(),
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


# --- open_instruments (positions-based, 6.7b) ---------------------------------


class TestOpenInstruments:
    def test_returns_empty_when_positions_table_is_empty(self, engine) -> None:
        sm = StateManager(engine, account_id="acc-1")
        assert sm.open_instruments() == frozenset()

    def test_open_event_makes_instrument_visible(self, engine) -> None:
        _insert_position(
            engine, psid="p1", account_id="acc-1", instrument="EURUSD", event_type="open"
        )
        sm = StateManager(engine, account_id="acc-1")
        assert sm.open_instruments() == frozenset({"EURUSD"})

    def test_add_event_also_makes_instrument_visible(self, engine) -> None:
        _insert_position(
            engine, psid="p1", account_id="acc-1", instrument="EURUSD", event_type="open"
        )
        _insert_position(
            engine,
            psid="p2",
            account_id="acc-1",
            instrument="EURUSD",
            event_type="add",
            event_time_utc=_NOW + timedelta(seconds=1),
        )
        sm = StateManager(engine, account_id="acc-1")
        assert sm.open_instruments() == frozenset({"EURUSD"})

    def test_close_event_hides_instrument(self, engine) -> None:
        _insert_position(
            engine, psid="p1", account_id="acc-1", instrument="EURUSD", event_type="open"
        )
        _insert_position(
            engine,
            psid="p2",
            account_id="acc-1",
            instrument="EURUSD",
            event_type="close",
            event_time_utc=_NOW + timedelta(seconds=1),
        )
        sm = StateManager(engine, account_id="acc-1")
        assert sm.open_instruments() == frozenset()

    def test_close_only_hides_that_instrument_not_others(self, engine) -> None:
        _insert_position(
            engine, psid="p1", account_id="acc-1", instrument="EURUSD", event_type="open"
        )
        _insert_position(
            engine,
            psid="p2",
            account_id="acc-1",
            instrument="EURUSD",
            event_type="close",
            event_time_utc=_NOW + timedelta(seconds=1),
        )
        _insert_position(
            engine, psid="p3", account_id="acc-1", instrument="USDJPY", event_type="open"
        )
        sm = StateManager(engine, account_id="acc-1")
        assert sm.open_instruments() == frozenset({"USDJPY"})

    def test_filters_by_account_id(self, engine) -> None:
        _insert_position(
            engine, psid="p1", account_id="acc-1", instrument="EURUSD", event_type="open"
        )
        _insert_position(
            engine, psid="p2", account_id="acc-2", instrument="USDJPY", event_type="open"
        )
        assert StateManager(engine, account_id="acc-1").open_instruments() == frozenset({"EURUSD"})
        assert StateManager(engine, account_id="acc-2").open_instruments() == frozenset({"USDJPY"})

    def test_dedupes_multiple_open_rows_same_instrument(self, engine) -> None:
        _insert_position(
            engine, psid="p1", account_id="acc-1", instrument="EURUSD", event_type="open"
        )
        _insert_position(
            engine,
            psid="p2",
            account_id="acc-1",
            instrument="EURUSD",
            event_type="add",
            event_time_utc=_NOW + timedelta(seconds=1),
        )
        sm = StateManager(engine, account_id="acc-1")
        assert sm.open_instruments() == frozenset({"EURUSD"})

    # --- 6.7c: re-open scenarios (fix for 6.7b NOT-IN bug) ---

    def test_reopen_after_close_is_visible(self, engine) -> None:
        """Instrument closed then re-opened must appear in open_instruments.

        The 6.7b query (NOT IN close events) hid all previously-closed
        instruments permanently.  The 6.7c fix (ROW_NUMBER on most recent
        event) correctly reflects the current timeline state.
        """
        _insert_position(
            engine, psid="p1", account_id="acc-1", instrument="EURUSD", event_type="open"
        )
        _insert_position(
            engine,
            psid="p2",
            account_id="acc-1",
            instrument="EURUSD",
            event_type="close",
            event_time_utc=_NOW + timedelta(seconds=1),
        )
        # Re-open after close
        _insert_position(
            engine,
            psid="p3",
            account_id="acc-1",
            instrument="EURUSD",
            event_type="open",
            event_time_utc=_NOW + timedelta(seconds=2),
        )
        sm = StateManager(engine, account_id="acc-1")
        assert sm.open_instruments() == frozenset({"EURUSD"})

    def test_reopen_close_reopen_tracks_correctly(self, engine) -> None:
        """Multiple open→close→open cycles all resolve to the correct state."""
        t = _NOW
        for cycle in range(3):
            _insert_position(
                engine,
                psid=f"open-{cycle}",
                account_id="acc-1",
                instrument="EURUSD",
                event_type="open",
                event_time_utc=t + timedelta(seconds=cycle * 10),
            )
            _insert_position(
                engine,
                psid=f"close-{cycle}",
                account_id="acc-1",
                instrument="EURUSD",
                event_type="close",
                event_time_utc=t + timedelta(seconds=cycle * 10 + 5),
            )
        sm = StateManager(engine, account_id="acc-1")
        # Most recent event is 'close' → not open
        assert sm.open_instruments() == frozenset()

        # One more open after the last close → open again
        _insert_position(
            engine,
            psid="open-final",
            account_id="acc-1",
            instrument="EURUSD",
            event_type="open",
            event_time_utc=t + timedelta(seconds=100),
        )
        assert sm.open_instruments() == frozenset({"EURUSD"})

    def test_reopen_does_not_leak_into_other_instruments(self, engine) -> None:
        """Re-open logic is per-instrument; other instruments unaffected."""
        _insert_position(
            engine, psid="p1", account_id="acc-1", instrument="EURUSD", event_type="open"
        )
        _insert_position(
            engine,
            psid="p2",
            account_id="acc-1",
            instrument="EURUSD",
            event_type="close",
            event_time_utc=_NOW + timedelta(seconds=1),
        )
        _insert_position(
            engine,
            psid="p3",
            account_id="acc-1",
            instrument="EURUSD",
            event_type="open",
            event_time_utc=_NOW + timedelta(seconds=2),
        )
        _insert_position(
            engine, psid="p4", account_id="acc-1", instrument="USDJPY", event_type="open"
        )
        sm = StateManager(engine, account_id="acc-1")
        assert sm.open_instruments() == frozenset({"EURUSD", "USDJPY"})


# --- recent_execution_failures_within (unchanged semantics) ------------------


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


# --- snapshot -----------------------------------------------------------------


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
        _insert_position(
            engine, psid="p1", account_id="acc-1", instrument="EURUSD", event_type="open"
        )
        _insert_position(
            engine, psid="p2", account_id="acc-1", instrument="USDJPY", event_type="open"
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
        for i, sym in enumerate(("EURUSD", "USDJPY", "GBPUSD")):
            _insert_position(
                engine, psid=f"p-{i}", account_id="acc-1", instrument=sym, event_type="open"
            )
        snap = StateManager(engine, account_id="acc-1").snapshot(
            now=_NOW, cooloff_window_seconds=900
        )
        assert snap.concurrent_count == len(snap.open_instruments) == 3

    def test_cross_account_isolation(self, engine) -> None:
        _insert_position(
            engine, psid="p1", account_id="acc-1", instrument="EURUSD", event_type="open"
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
