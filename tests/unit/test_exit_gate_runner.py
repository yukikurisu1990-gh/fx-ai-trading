"""Unit tests: run_exit_gate (Cycle 6.7c).

Covers:
  noop paths:
    - No open positions → empty result list.
    - ExitPolicy returns should_exit=False → noop outcome.
    - Multiple positions, none exit → all noop.

  close paths:
    - should_exit=True, broker filled → outcome='closed'.
    - positions(close) row written after successful close.
    - close_events row written after successful close.
    - Both outbox rows (positions + close_events) enqueued (F-12).
    - primary_reason propagated to on_close and ExitGateRunResult.

  broker_rejected path:
    - Broker returns non-filled → outcome='broker_rejected'.
    - No positions(close) row written on broker rejection.

  multi-position:
    - Mixed: one exits, one holds → correct outcomes per instrument.
    - Both exit → both 'closed' results.

  re-open scenario (6.7c fix):
    - Close via exit runner → open_instruments() returns empty.
    - Re-fill after exit runner close → instrument visible again.

  D1-format reasons:
    - reasons list uses {priority, reason_code, detail} format.
    - priority is 1-indexed in priority order.

  L2 constraint:
    - position_id passed to evaluate() equals order_id (order identity).

  E2 constraint:
    - close_request side is 'short' when open side is 'long'.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.common.exceptions import AccountTypeMismatchRuntime
from fx_ai_trading.domain.broker import Broker, OrderRequest, OrderResult
from fx_ai_trading.domain.exit import ExitDecision
from fx_ai_trading.services.exit_gate_runner import ExitGateRunResult, run_exit_gate
from fx_ai_trading.services.state_manager import StateManager

_NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)
_OPEN_TIME = _NOW - timedelta(seconds=300)

# --- DDL ----------------------------------------------------------------------

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

_DDL_CLOSE_EVENTS = """
CREATE TABLE close_events (
    close_event_id       TEXT PRIMARY KEY,
    order_id             TEXT NOT NULL,
    position_snapshot_id TEXT,
    reasons              TEXT NOT NULL,
    primary_reason_code  TEXT NOT NULL,
    closed_at            TEXT NOT NULL,
    pnl_realized         NUMERIC(18,8),
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

_DDL_OUTBOX = """
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
)
"""


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL_POSITIONS))
        conn.execute(text(_DDL_CLOSE_EVENTS))
        conn.execute(text(_DDL_ORDER_TRANSACTIONS))
        conn.execute(text(_DDL_OUTBOX))
    yield eng
    eng.dispose()


# --- Helpers ------------------------------------------------------------------


def _make_sm(engine, account_id: str = "acc-1") -> StateManager:
    return StateManager(engine, account_id=account_id, clock=FixedClock(_NOW))


def _seed_open_position(
    engine,
    *,
    psid: str,
    order_id: str,
    instrument: str,
    units: int = 1000,
    avg_price: float = 1.10,
    account_id: str = "acc-1",
    open_time: datetime = _OPEN_TIME,
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
                    'open', :units, :avg, NULL, NULL,
                    :ts, NULL
                )
                """
            ),
            {
                "psid": psid,
                "oid": order_id,
                "aid": account_id,
                "inst": instrument,
                "units": units,
                "avg": avg_price,
                "ts": open_time.isoformat(),
            },
        )


def _positions(engine, *, account_id: str = "acc-1") -> list:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM positions WHERE account_id = :aid"),
            {"aid": account_id},
        ).fetchall()


def _close_events(engine) -> list:
    with engine.connect() as conn:
        return conn.execute(text("SELECT * FROM close_events")).fetchall()


def _outbox(engine, *, table_name: str) -> list:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM secondary_sync_outbox WHERE table_name = :tn"),
            {"tn": table_name},
        ).fetchall()


# --- Test doubles -------------------------------------------------------------


class _AlwaysHoldPolicy:
    """ExitPolicy stub: never exits."""

    def evaluate(self, *_, **__) -> ExitDecision:
        return ExitDecision(position_id="", should_exit=False, reasons=())


class _AlwaysExitPolicy:
    """ExitPolicy stub: always exits with max_holding_time."""

    def evaluate(self, position_id: str, **__) -> ExitDecision:
        return ExitDecision(
            position_id=position_id,
            should_exit=True,
            reasons=("max_holding_time",),
            primary_reason="max_holding_time",
        )


class _MultiReasonExitPolicy:
    """ExitPolicy stub: exits with emergency_stop + sl."""

    def evaluate(self, position_id: str, **__) -> ExitDecision:
        return ExitDecision(
            position_id=position_id,
            should_exit=True,
            reasons=("emergency_stop", "sl"),
            primary_reason="emergency_stop",
        )


@dataclass
class _FillBroker:
    """Broker stub: always returns filled."""

    account_type: str = "demo"
    last_request: OrderRequest | None = None

    def place_order(self, request: OrderRequest) -> OrderResult:
        self.last_request = request
        return OrderResult(
            client_order_id=request.client_order_id,
            broker_order_id="bk-close-ok",
            status="filled",
            filled_units=request.size_units,
            fill_price=1.12,
        )


@dataclass
class _RejectBroker:
    """Broker stub: always returns rejected."""

    account_type: str = "demo"

    def place_order(self, request: OrderRequest) -> OrderResult:
        return OrderResult(
            client_order_id=request.client_order_id,
            broker_order_id="bk-close-fail",
            status="rejected",
            filled_units=0,
        )


_: Broker = _FillBroker()


def _fixed_price(price: float) -> object:
    """Returns a price_feed callable that always returns `price`."""
    return lambda _instrument: price


def _run(
    engine,
    *,
    policy=None,
    broker=None,
    account_id: str = "acc-1",
    price: float = 1.10,
    context: dict | None = None,
) -> list[ExitGateRunResult]:
    sm = _make_sm(engine, account_id=account_id)
    return run_exit_gate(
        broker=broker or _FillBroker(),
        account_id=account_id,
        clock=FixedClock(_NOW),
        state_manager=sm,
        exit_policy=policy or _AlwaysHoldPolicy(),
        price_feed=_fixed_price(price),
        context=context,
    )


# --- noop paths ---------------------------------------------------------------


class TestNoop:
    def test_no_open_positions_returns_empty_list(self, engine) -> None:
        results = _run(engine)
        assert results == []

    def test_hold_policy_returns_noop_outcome(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        results = _run(engine, policy=_AlwaysHoldPolicy())
        assert len(results) == 1
        assert results[0].outcome == "noop"
        assert results[0].instrument == "EURUSD"
        assert results[0].primary_reason is None

    def test_noop_writes_no_positions_row(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        _run(engine, policy=_AlwaysHoldPolicy())
        rows = _positions(engine)
        assert len(rows) == 1  # only the seeded open row
        assert rows[0].event_type == "open"

    def test_multiple_positions_all_hold(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        _seed_open_position(engine, psid="p2", order_id="o2", instrument="USDJPY")
        results = _run(engine, policy=_AlwaysHoldPolicy())
        assert len(results) == 2
        assert all(r.outcome == "noop" for r in results)


# --- close path ---------------------------------------------------------------


class TestClose:
    def test_exit_policy_true_produces_closed_outcome(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        results = _run(engine, policy=_AlwaysExitPolicy())
        assert len(results) == 1
        assert results[0].outcome == "closed"
        assert results[0].instrument == "EURUSD"
        assert results[0].primary_reason == "max_holding_time"

    def test_close_writes_positions_close_row(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        _run(engine, policy=_AlwaysExitPolicy())
        rows = _positions(engine)
        close_rows = [r for r in rows if r.event_type == "close"]
        assert len(close_rows) == 1
        assert close_rows[0].instrument == "EURUSD"
        assert float(close_rows[0].units) == 0.0

    def test_close_writes_close_events_row(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        _run(engine, policy=_AlwaysExitPolicy())
        ces = _close_events(engine)
        assert len(ces) == 1
        assert ces[0].primary_reason_code == "max_holding_time"
        assert ces[0].order_id == "o1"

    def test_close_enqueues_positions_to_outbox(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        _run(engine, policy=_AlwaysExitPolicy())
        rows = _outbox(engine, table_name="positions")
        # The seeded open row is NOT enqueued (inserted directly);
        # the close row IS enqueued via on_close.
        assert len(rows) == 1
        payload = json.loads(rows[0].payload_json)
        assert payload["event_type"] == "close"

    def test_close_enqueues_close_events_to_outbox(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        _run(engine, policy=_AlwaysExitPolicy())
        rows = _outbox(engine, table_name="close_events")
        assert len(rows) == 1
        payload = json.loads(rows[0].payload_json)
        assert payload["primary_reason_code"] == "max_holding_time"

    def test_reasons_stored_in_d1_format(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        _run(engine, policy=_MultiReasonExitPolicy())
        ces = _close_events(engine)
        stored = json.loads(ces[0].reasons)
        assert stored[0] == {"priority": 1, "reason_code": "emergency_stop", "detail": ""}
        assert stored[1] == {"priority": 2, "reason_code": "sl", "detail": ""}

    def test_close_side_is_opposite_of_open_side(self, engine) -> None:
        broker = _FillBroker()
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        sm = _make_sm(engine)
        run_exit_gate(
            broker=broker,
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            price_feed=_fixed_price(1.10),
            side="long",
        )
        assert broker.last_request is not None
        assert broker.last_request.side == "short"

    def test_close_request_uses_position_units(self, engine) -> None:
        broker = _FillBroker()
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD", units=2500)
        sm = _make_sm(engine)
        run_exit_gate(
            broker=broker,
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            price_feed=_fixed_price(1.10),
        )
        assert broker.last_request is not None
        assert broker.last_request.size_units == 2500

    def test_l2_position_id_is_order_id(self, engine) -> None:
        """L2: evaluate() receives order_id as position_id."""
        received: list[str] = []

        class _RecordPolicy:
            def evaluate(self, position_id: str, **__) -> ExitDecision:
                received.append(position_id)
                return ExitDecision(position_id=position_id, should_exit=False, reasons=())

        _seed_open_position(engine, psid="p1", order_id="ord-xyz", instrument="EURUSD")
        sm = _make_sm(engine)
        run_exit_gate(
            broker=_FillBroker(),
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_RecordPolicy(),
            price_feed=_fixed_price(1.10),
        )
        assert received == ["ord-xyz"]


# --- broker_rejected path -----------------------------------------------------


class TestBrokerRejected:
    def test_broker_rejected_outcome(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        results = _run(engine, policy=_AlwaysExitPolicy(), broker=_RejectBroker())
        assert len(results) == 1
        assert results[0].outcome == "broker_rejected"
        assert results[0].primary_reason == "max_holding_time"

    def test_broker_rejected_writes_no_positions_close_row(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        _run(engine, policy=_AlwaysExitPolicy(), broker=_RejectBroker())
        rows = _positions(engine)
        assert all(r.event_type != "close" for r in rows)

    def test_broker_rejected_writes_no_close_events_row(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        _run(engine, policy=_AlwaysExitPolicy(), broker=_RejectBroker())
        assert _close_events(engine) == []


# --- multi-position -----------------------------------------------------------


class TestMultiPosition:
    def test_one_exits_one_holds(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        _seed_open_position(engine, psid="p2", order_id="o2", instrument="USDJPY")

        # Only USDJPY exits (policy checks instrument name)
        class _SelectivePolicy:
            def evaluate(self, position_id: str, instrument: str, **__) -> ExitDecision:
                if instrument == "USDJPY":
                    return ExitDecision(
                        position_id=position_id,
                        should_exit=True,
                        reasons=("max_holding_time",),
                        primary_reason="max_holding_time",
                    )
                return ExitDecision(position_id=position_id, should_exit=False, reasons=())

        results = _run(engine, policy=_SelectivePolicy())
        outcomes = {r.instrument: r.outcome for r in results}
        assert outcomes["EURUSD"] == "noop"
        assert outcomes["USDJPY"] == "closed"

    def test_both_exit(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        _seed_open_position(engine, psid="p2", order_id="o2", instrument="USDJPY")
        results = _run(engine, policy=_AlwaysExitPolicy())
        assert len(results) == 2
        assert all(r.outcome == "closed" for r in results)
        close_rows = [r for r in _positions(engine) if r.event_type == "close"]
        assert len(close_rows) == 2


# --- re-open scenario (6.7c fix) ---------------------------------------------


class TestReOpenScenario:
    def test_position_invisible_after_exit_runner_close(self, engine) -> None:
        """After run_exit_gate closes a position, open_instruments must be empty."""
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        assert sm.open_instruments() == frozenset({"EURUSD"})

        run_exit_gate(
            broker=_FillBroker(),
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            price_feed=_fixed_price(1.10),
        )
        assert sm.open_instruments() == frozenset()

    def test_refill_after_close_makes_instrument_visible_again(self, engine) -> None:
        """Re-fill after exit gate close must re-appear in open_instruments.

        This is the core re-open bug that 6.7c fixes.  The 6.7b NOT-IN
        query would leave the instrument permanently hidden.
        """
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)

        run_exit_gate(
            broker=_FillBroker(),
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            price_feed=_fixed_price(1.10),
        )
        assert sm.open_instruments() == frozenset()

        # Re-entry: new fill for the same instrument
        sm2 = StateManager(
            engine, account_id="acc-1", clock=FixedClock(_NOW + timedelta(seconds=10))
        )
        sm2.on_fill(order_id="o2", instrument="EURUSD", units=1000, avg_price=1.11)
        assert sm2.open_instruments() == frozenset({"EURUSD"})

    def test_refill_event_type_is_open_not_add(self, engine) -> None:
        """After a full close, the next fill writes event_type='open' (not 'add')."""
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)

        run_exit_gate(
            broker=_FillBroker(),
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            price_feed=_fixed_price(1.10),
        )

        sm2 = StateManager(
            engine, account_id="acc-1", clock=FixedClock(_NOW + timedelta(seconds=10))
        )
        sm2.on_fill(order_id="o2", instrument="EURUSD", units=1000, avg_price=1.11)

        rows = _positions(engine)
        reopen_row = next(r for r in rows if r.order_id == "o2")
        assert reopen_row.event_type == "open"

    def test_g1_blocks_second_signal_after_reopen(self, engine) -> None:
        """After re-fill, open_instruments reflects the new position,
        so a second duplicate signal would be blocked by G1."""
        sm = _make_sm(engine)
        # Close existing and re-open
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        run_exit_gate(
            broker=_FillBroker(),
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            price_feed=_fixed_price(1.10),
        )
        sm2 = StateManager(
            engine, account_id="acc-1", clock=FixedClock(_NOW + timedelta(seconds=10))
        )
        sm2.on_fill(order_id="o2", instrument="EURUSD", units=1000, avg_price=1.11)

        # G1 check: EURUSD must be in open_instruments
        assert "EURUSD" in sm2.open_instruments()
        # A third fill would write 'add', not 'open' (pyramiding)
        sm2.on_fill(order_id="o3", instrument="EURUSD", units=500, avg_price=1.12)
        rows = _positions(engine)
        third = next(r for r in rows if r.order_id == "o3")
        assert third.event_type == "add"


# --- open_position_details ----------------------------------------------------


class TestOpenPositionDetails:
    def test_empty_when_no_positions(self, engine) -> None:
        sm = _make_sm(engine)
        assert sm.open_position_details() == []

    def test_returns_one_entry_for_one_open_position(self, engine) -> None:
        _seed_open_position(
            engine,
            psid="p1",
            order_id="o1",
            instrument="EURUSD",
            units=1000,
            avg_price=1.1234,
            open_time=_OPEN_TIME,
        )
        sm = _make_sm(engine)
        details = sm.open_position_details()
        assert len(details) == 1
        d = details[0]
        assert d.instrument == "EURUSD"
        assert d.order_id == "o1"
        assert d.units == 1000
        assert abs(d.avg_price - 1.1234) < 1e-6

    def test_closed_position_not_included(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        sm = _make_sm(engine)
        sm.on_close(
            order_id="o1",
            instrument="EURUSD",
            reasons=[{"priority": 1, "reason_code": "tp", "detail": ""}],
            primary_reason_code="tp",
        )
        assert sm.open_position_details() == []

    def test_two_instruments_returns_two_entries(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        _seed_open_position(engine, psid="p2", order_id="o2", instrument="USDJPY")
        sm = _make_sm(engine)
        details = sm.open_position_details()
        assert len(details) == 2
        instruments = {d.instrument for d in details}
        assert instruments == {"EURUSD", "USDJPY"}

    def test_reopen_after_close_returns_new_entry(self, engine) -> None:
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        sm.on_close(
            order_id="o1",
            instrument="EURUSD",
            reasons=[{"priority": 1, "reason_code": "tp", "detail": ""}],
            primary_reason_code="tp",
        )
        sm2 = StateManager(
            engine, account_id="acc-1", clock=FixedClock(_NOW + timedelta(seconds=10))
        )
        sm2.on_fill(order_id="o2", instrument="EURUSD", units=800, avg_price=1.11)
        details = sm2.open_position_details()
        assert len(details) == 1
        assert details[0].order_id == "o2"
        assert details[0].units == 800


# --- PR-5 (U-2): AccountTypeMismatchRuntime → safe_stop wiring ---------------


@dataclass
class _MismatchBroker:
    """Broker stub: every place_order raises AccountTypeMismatchRuntime."""

    account_type: str = "demo"
    actual_account_type: str = "live"
    received: list[OrderRequest] | None = None

    def __post_init__(self) -> None:
        if self.received is None:
            self.received = []

    def place_order(self, request: OrderRequest) -> OrderResult:
        assert self.received is not None
        self.received.append(request)
        raise AccountTypeMismatchRuntime(
            f"Broker account_type {self.actual_account_type!r} != expected {self.account_type!r}"
        )


class _SupervisorSpy:
    """Captures (kwargs) of every trigger_safe_stop call."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def trigger_safe_stop(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _SupervisorNoop:
    """Accepts trigger_safe_stop and does nothing."""

    def trigger_safe_stop(self, **_kwargs) -> None:
        return None


class _BrokenSupervisor:
    """trigger_safe_stop itself raises — must NOT swallow original exception."""

    def trigger_safe_stop(self, **_kwargs) -> None:
        raise RuntimeError("supervisor blew up")


class TestAccountTypeMismatchRuntimeWiring:
    def test_no_supervisor_propagates_exception_unchanged(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        sm = _make_sm(engine)
        with pytest.raises(AccountTypeMismatchRuntime):
            run_exit_gate(
                broker=_MismatchBroker(),
                account_id="acc-1",
                clock=FixedClock(_NOW),
                state_manager=sm,
                exit_policy=_AlwaysExitPolicy(),
                price_feed=_fixed_price(1.10),
                # supervisor=None (default)
            )
        # No close_event, no positions(close) row, no outbox entry.
        assert _close_events(engine) == []
        assert all(r.event_type != "close" for r in _positions(engine))
        assert _outbox(engine, table_name="close_events") == []

    def test_supervisor_triggers_safe_stop_with_canonical_reason(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        sm = _make_sm(engine)
        spy = _SupervisorSpy()
        broker = _MismatchBroker(account_type="demo", actual_account_type="live")
        with pytest.raises(AccountTypeMismatchRuntime):
            run_exit_gate(
                broker=broker,
                account_id="acc-1",
                clock=FixedClock(_NOW),
                state_manager=sm,
                exit_policy=_AlwaysExitPolicy(),
                price_feed=_fixed_price(1.10),
                supervisor=spy,  # type: ignore[arg-type]
            )
        assert len(spy.calls) == 1
        call = spy.calls[0]
        assert call["reason"] == "account_type_mismatch_runtime"
        assert call["occurred_at"] == _NOW
        payload = call["payload"]
        # payload key parity with PR-4 (execution_gate_runner).
        assert set(payload.keys()) == {
            "actual_account_type",
            "expected_account_type",
            "instrument",
            "client_order_id",
            "detail",
        }
        assert payload["actual_account_type"] == "demo"  # broker.account_type
        assert payload["expected_account_type"] is None
        assert payload["instrument"] == "EURUSD"
        assert payload["client_order_id"]  # ulid populated
        assert "live" in payload["detail"] and "demo" in payload["detail"]

    def test_supervisor_wired_does_not_write_close_event_or_on_close(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        sm = _make_sm(engine)
        with pytest.raises(AccountTypeMismatchRuntime):
            run_exit_gate(
                broker=_MismatchBroker(),
                account_id="acc-1",
                clock=FixedClock(_NOW),
                state_manager=sm,
                exit_policy=_AlwaysExitPolicy(),
                price_feed=_fixed_price(1.10),
                supervisor=_SupervisorNoop(),  # type: ignore[arg-type]
            )
        # No close_event written.
        assert _close_events(engine) == []
        # No positions(close) row appended via on_close.
        assert all(r.event_type != "close" for r in _positions(engine))
        # No outbox entry for close_events or positions(close).
        assert _outbox(engine, table_name="close_events") == []
        positions_outbox_close = [
            r
            for r in _outbox(engine, table_name="positions")
            if json.loads(r.payload_json).get("event_type") == "close"
        ]
        assert positions_outbox_close == []

    def test_supervisor_trigger_safe_stop_failure_does_not_swallow_original(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        sm = _make_sm(engine)
        with pytest.raises(AccountTypeMismatchRuntime):
            run_exit_gate(
                broker=_MismatchBroker(),
                account_id="acc-1",
                clock=FixedClock(_NOW),
                state_manager=sm,
                exit_policy=_AlwaysExitPolicy(),
                price_feed=_fixed_price(1.10),
                supervisor=_BrokenSupervisor(),  # type: ignore[arg-type]
            )
        assert _close_events(engine) == []

    def test_mismatch_on_first_position_aborts_remaining_positions(self, engine) -> None:
        """Account-type drift → broker can't be trusted → loop must abort."""
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        _seed_open_position(engine, psid="p2", order_id="o2", instrument="USDJPY")
        sm = _make_sm(engine)
        broker = _MismatchBroker()
        with pytest.raises(AccountTypeMismatchRuntime):
            run_exit_gate(
                broker=broker,
                account_id="acc-1",
                clock=FixedClock(_NOW),
                state_manager=sm,
                exit_policy=_AlwaysExitPolicy(),
                price_feed=_fixed_price(1.10),
                supervisor=_SupervisorNoop(),  # type: ignore[arg-type]
            )
        # Only the first position was attempted; loop aborted before second.
        assert broker.received is not None
        assert len(broker.received) == 1
        assert _close_events(engine) == []
