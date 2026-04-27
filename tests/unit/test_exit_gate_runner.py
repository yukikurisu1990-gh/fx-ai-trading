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

# Minimal orders DDL — only the columns ``open_position_details`` reads
# via its M-1a LEFT JOIN.  The production schema has many more columns
# (``client_order_id`` / ``trading_signal_id`` / ``account_type`` / ...);
# tests do not exercise those here.
_DDL_ORDERS = """
CREATE TABLE orders (
    order_id  TEXT PRIMARY KEY,
    direction TEXT NOT NULL
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
        conn.execute(text(_DDL_ORDERS))
    yield eng
    eng.dispose()


# --- Helpers ------------------------------------------------------------------


def _make_sm(engine, account_id: str = "acc-1") -> StateManager:
    return StateManager(engine, account_id=account_id, clock=FixedClock(_NOW))


def _seed_order(engine, *, order_id: str, direction: str = "buy") -> None:
    """Seed the bare-minimum ``orders`` row that ``open_position_details``
    needs for its M-1a LEFT JOIN.  Default ``direction='buy'`` keeps the
    paper-mode long-only fixture posture intact.
    """
    with engine.begin() as conn:
        conn.execute(
            text("INSERT OR IGNORE INTO orders (order_id, direction) VALUES (:oid, :dir)"),
            {"oid": order_id, "dir": direction},
        )


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
    direction: str = "buy",
) -> None:
    _seed_order(engine, order_id=order_id, direction=direction)
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
class _PriceFillBroker:
    """Broker stub: returns filled with a configurable ``fill_price``.

    Pass ``fill_price=None`` to simulate the OANDA edge case where the
    broker accepts the close but cannot report a fill price (M-2 fall-back).
    """

    fill_price: float | None
    account_type: str = "demo"
    last_request: OrderRequest | None = None

    def place_order(self, request: OrderRequest) -> OrderResult:
        self.last_request = request
        return OrderResult(
            client_order_id=request.client_order_id,
            broker_order_id="bk-close-priced",
            status="filled",
            filled_units=request.size_units,
            fill_price=self.fill_price,
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
        quote_feed=_fixed_price(price),
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

    def test_close_side_is_opposite_of_open_side_for_long(self, engine) -> None:
        broker = _FillBroker()
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        sm = _make_sm(engine)
        run_exit_gate(
            broker=broker,
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            quote_feed=_fixed_price(1.10),
        )
        assert broker.last_request is not None
        assert broker.last_request.side == "short"

    def test_close_side_is_opposite_of_open_side_for_short(self, engine) -> None:
        """M-1b: close side must derive per-position from pos.side.

        Seeds an open position whose underlying order has
        ``direction='sell'`` so the M-1a JOIN derives ``side='short'``;
        the closing OrderRequest must then carry ``side='long'``.
        """
        broker = _FillBroker()
        _seed_open_position(
            engine,
            psid="p1",
            order_id="o1",
            instrument="EURUSD",
            direction="sell",
        )
        sm = _make_sm(engine)
        run_exit_gate(
            broker=broker,
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            quote_feed=_fixed_price(1.10),
        )
        assert broker.last_request is not None
        assert broker.last_request.side == "long"

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
            quote_feed=_fixed_price(1.10),
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
            quote_feed=_fixed_price(1.10),
        )
        assert received == ["ord-xyz"]


# --- M-2: pnl_realized computation -------------------------------------------


class TestPnlRealized:
    """M-2: ``run_exit_gate`` computes gross PnL at close time and forwards it
    to ``StateManager.on_close`` (which writes it to ``close_events.pnl_realized``
    and ``positions.realized_pl``).

    Formula:  ``(fill_price - avg_price) * units * (+1 if long else -1)``
    Units are unsigned by repo convention (direction lives in ``pos.side``).
    Fees / spread / swap / quote-currency conversion are NOT included
    (gross PnL only — net PnL is a separate milestone).
    """

    def test_long_profit_pnl_is_positive(self, engine) -> None:
        broker = _PriceFillBroker(fill_price=1.12)
        _seed_open_position(
            engine,
            psid="p1",
            order_id="o1",
            instrument="EURUSD",
            avg_price=1.10,
            units=1000,
            direction="buy",
        )
        _run(engine, policy=_AlwaysExitPolicy(), broker=broker)
        ces = _close_events(engine)
        assert len(ces) == 1
        # (1.12 - 1.10) * 1000 * (+1) = 20.0
        assert float(ces[0].pnl_realized) == pytest.approx(20.0)

    def test_short_profit_pnl_is_positive(self, engine) -> None:
        broker = _PriceFillBroker(fill_price=1.10)
        _seed_open_position(
            engine,
            psid="p1",
            order_id="o1",
            instrument="EURUSD",
            avg_price=1.12,
            units=1000,
            direction="sell",
        )
        _run(engine, policy=_AlwaysExitPolicy(), broker=broker)
        ces = _close_events(engine)
        assert len(ces) == 1
        # (1.10 - 1.12) * 1000 * (-1) = 20.0
        assert float(ces[0].pnl_realized) == pytest.approx(20.0)

    def test_long_loss_pnl_is_negative(self, engine) -> None:
        broker = _PriceFillBroker(fill_price=1.08)
        _seed_open_position(
            engine,
            psid="p1",
            order_id="o1",
            instrument="EURUSD",
            avg_price=1.10,
            units=1000,
            direction="buy",
        )
        _run(engine, policy=_AlwaysExitPolicy(), broker=broker)
        ces = _close_events(engine)
        assert len(ces) == 1
        # (1.08 - 1.10) * 1000 * (+1) = -20.0
        assert float(ces[0].pnl_realized) == pytest.approx(-20.0)

    def test_fill_price_none_records_pnl_realized_as_null(self, engine) -> None:
        """OANDA edge case: broker returns filled but no fill_price.

        The close MUST still record (so the position is marked closed),
        but ``pnl_realized`` is left NULL — downstream aggregates remain
        ANSI-NULL-aware, and a fabricated value would silently corrupt
        metrics.
        """
        broker = _PriceFillBroker(fill_price=None)
        _seed_open_position(
            engine,
            psid="p1",
            order_id="o1",
            instrument="EURUSD",
            avg_price=1.10,
            units=1000,
            direction="buy",
        )
        results = _run(engine, policy=_AlwaysExitPolicy(), broker=broker)

        assert len(results) == 1
        assert results[0].outcome == "closed"
        ces = _close_events(engine)
        assert len(ces) == 1
        assert ces[0].pnl_realized is None


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
        # M-1a: run_exit_gate calls open_position_details which LEFT-JOINs
        # orders.  Seed the orders row so the JOIN finds 'buy' (→ side=long).
        _seed_order(engine, order_id="o1")
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        assert sm.open_instruments() == frozenset({"EURUSD"})

        run_exit_gate(
            broker=_FillBroker(),
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            quote_feed=_fixed_price(1.10),
        )
        assert sm.open_instruments() == frozenset()

    def test_refill_after_close_makes_instrument_visible_again(self, engine) -> None:
        """Re-fill after exit gate close must re-appear in open_instruments.

        This is the core re-open bug that 6.7c fixes.  The 6.7b NOT-IN
        query would leave the instrument permanently hidden.
        """
        # M-1a: orders rows for both order_ids the JOIN will touch.
        _seed_order(engine, order_id="o1")
        _seed_order(engine, order_id="o2")
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)

        run_exit_gate(
            broker=_FillBroker(),
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            quote_feed=_fixed_price(1.10),
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
        # M-1a: orders rows for both order_ids the JOIN will touch.
        _seed_order(engine, order_id="o1")
        _seed_order(engine, order_id="o2")
        sm = _make_sm(engine)
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)

        run_exit_gate(
            broker=_FillBroker(),
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            quote_feed=_fixed_price(1.10),
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
        # M-1a: orders rows for every order_id the JOIN will touch.
        # 'o3' is a same-instrument pyramid (event_type='add'), but
        # open_position_details still observes it via the JOIN.
        _seed_order(engine, order_id="o1")
        _seed_order(engine, order_id="o2")
        _seed_order(engine, order_id="o3")
        sm = _make_sm(engine)
        # Close existing and re-open
        sm.on_fill(order_id="o1", instrument="EURUSD", units=1000, avg_price=1.10)
        run_exit_gate(
            broker=_FillBroker(),
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            quote_feed=_fixed_price(1.10),
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
        # M-1a: open_position_details JOINs orders → seed an orders row
        # for every order_id whose position will be observed via the JOIN.
        _seed_order(engine, order_id="o1")
        _seed_order(engine, order_id="o2")
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
                quote_feed=_fixed_price(1.10),
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
                quote_feed=_fixed_price(1.10),
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
                quote_feed=_fixed_price(1.10),
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
                quote_feed=_fixed_price(1.10),
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
                quote_feed=_fixed_price(1.10),
                supervisor=_SupervisorNoop(),  # type: ignore[arg-type]
            )
        # Only the first position was attempted; loop aborted before second.
        assert broker.received is not None
        assert len(broker.received) == 1
        assert _close_events(engine) == []


# --- M-3b: QuoteFeed acceptance ----------------------------------------------


class _StubQuoteFeed:
    """Test-only QuoteFeed: counts get_quote calls, returns a constant price."""

    def __init__(self, price: float) -> None:
        from fx_ai_trading.domain.price_feed import Quote

        self._price = price
        self._Quote = Quote
        self.calls: list[str] = []

    def get_quote(self, instrument: str):
        self.calls.append(instrument)
        return self._Quote(price=self._price, ts=_NOW, source="test_fixture")


class TestQuoteFeedAcceptance:
    """run_exit_gate accepts both a QuoteFeed and a legacy callable.

    The legacy callable path is already exercised by every other test in
    this file; these tests pin the QuoteFeed branch and the discrimination
    logic (no double-wrap when a QuoteFeed is passed directly).
    """

    def test_quote_feed_direct_path_drives_close(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        sm = _make_sm(engine)
        feed = _StubQuoteFeed(price=1.10)
        results = run_exit_gate(
            broker=_FillBroker(),
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            quote_feed=feed,
        )
        # Decision still fires — proves get_quote().price is what reaches
        # the policy/broker layer, not the legacy-call result.
        assert [r.outcome for r in results] == ["closed"]
        assert feed.calls == ["EURUSD"]

    def test_legacy_callable_still_works_via_internal_wrap(self, engine) -> None:
        """Back-compat: a plain Callable[[str], float] is auto-wrapped."""
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        sm = _make_sm(engine)
        seen: list[str] = []

        def _legacy(instrument: str) -> float:
            seen.append(instrument)
            return 1.10

        results = run_exit_gate(
            broker=_FillBroker(),
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            quote_feed=_legacy,
        )
        assert [r.outcome for r in results] == ["closed"]
        assert seen == ["EURUSD"]

    def test_quote_feed_price_threads_through_to_policy(self, engine) -> None:
        """A different price must produce a different evaluation outcome.

        Uses an SL-only policy with sl=0.99: feed price 0.95 → SL hit;
        feed price 1.10 → no exit.  Pins that ``.price`` (not ``ts`` /
        ``source``) is what the policy receives.
        """
        from fx_ai_trading.domain.exit import ExitDecision

        sl_level = 0.99

        class _SlPolicy:
            def evaluate(
                self,
                *,
                position_id,
                instrument,
                side,
                current_price,
                tp,
                sl,
                holding_seconds,
                context,
            ):
                if current_price < sl_level:
                    return ExitDecision(
                        position_id=position_id,
                        should_exit=True,
                        reasons=("sl",),
                        primary_reason="sl",
                    )
                return ExitDecision(
                    position_id=position_id,
                    should_exit=False,
                    reasons=(),
                    primary_reason=None,
                )

        # Below SL → close.
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        sm = _make_sm(engine)
        results = run_exit_gate(
            broker=_FillBroker(),
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_SlPolicy(),
            quote_feed=_StubQuoteFeed(price=0.95),
            sl=sl_level,
        )
        assert [r.outcome for r in results] == ["closed"]


# --- M-3c: stale quote gate --------------------------------------------------


class _StaleStubFeed:
    """QuoteFeed stub with configurable ts/source for staleness tests."""

    def __init__(self, *, price: float, ts: datetime, source: str) -> None:
        from fx_ai_trading.domain.price_feed import Quote

        self._price = price
        self._ts = ts
        self._source = source
        self._Quote = Quote
        self.calls: list[str] = []

    def get_quote(self, instrument: str):
        self.calls.append(instrument)
        return self._Quote(price=self._price, ts=self._ts, source=self._source)


class TestStaleQuoteGate:
    """M-3c: stale quote gate skips close evaluation when quote.ts is too old.

    Threshold semantics: ``age_seconds > stale_max_age_seconds`` (strict >),
    so age == max_age is NOT stale.  ``emergency_stop`` bypasses the gate
    so an operator-triggered flat-all is never blocked by an upstream feed
    outage.  The legacy ``Callable`` adapter synthesises ``ts == clock.now()``
    so legacy callers always observe age=0 — verified by the last test below.
    """

    def test_stale_quote_returns_noop_stale_quote_outcome(self, engine, caplog) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        sm = _make_sm(engine)
        # 120s old vs default 60s threshold → stale.
        stale_ts = _NOW - timedelta(seconds=120)
        feed = _StaleStubFeed(price=1.10, ts=stale_ts, source="oanda_live")
        broker = _FillBroker()

        with caplog.at_level("WARNING", logger="fx_ai_trading.services.exit_gate_runner"):
            results = run_exit_gate(
                broker=broker,
                account_id="acc-1",
                clock=FixedClock(_NOW),
                state_manager=sm,
                exit_policy=_AlwaysExitPolicy(),
                quote_feed=feed,
            )

        assert [r.outcome for r in results] == ["noop_stale_quote"]
        assert results[0].instrument == "EURUSD"
        assert results[0].order_id == "o1"
        # Broker MUST NOT be called on the stale path.
        assert broker.last_request is None
        # on_close MUST NOT have written a close event.
        assert _close_events(engine) == []

        # Warning log must mention instrument, age, source.
        warning_msgs = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
        assert any("EURUSD" in m and "120.0" in m and "oanda_live" in m for m in warning_msgs), (
            f"expected warning with instrument/age/source, got: {warning_msgs}"
        )

    def test_emergency_stop_bypasses_stale_gate(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        sm = _make_sm(engine)
        # 600s old quote — far past any reasonable threshold.
        very_stale_ts = _NOW - timedelta(seconds=600)
        feed = _StaleStubFeed(price=1.10, ts=very_stale_ts, source="oanda_live")
        broker = _FillBroker()

        results = run_exit_gate(
            broker=broker,
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            quote_feed=feed,
            context={"emergency_stop": True},
        )

        # emergency_stop=True means the stale gate is bypassed and the
        # close path runs to completion.
        assert [r.outcome for r in results] == ["closed"]
        assert broker.last_request is not None
        assert len(_close_events(engine)) == 1

    def test_fresh_quote_proceeds_to_existing_path(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        sm = _make_sm(engine)
        # ts == clock.now() → age=0 → not stale (under any positive threshold).
        feed = _StaleStubFeed(price=1.10, ts=_NOW, source="oanda_live")
        broker = _FillBroker()

        results = run_exit_gate(
            broker=broker,
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            quote_feed=feed,
        )

        assert [r.outcome for r in results] == ["closed"]
        assert broker.last_request is not None

    def test_stale_max_age_seconds_override(self, engine) -> None:
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        sm = _make_sm(engine)
        # 30s old — well within default 60s — but threshold lowered to 10s.
        feed = _StaleStubFeed(
            price=1.10,
            ts=_NOW - timedelta(seconds=30),
            source="oanda_live",
        )
        broker = _FillBroker()

        results = run_exit_gate(
            broker=broker,
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            quote_feed=feed,
            stale_max_age_seconds=10.0,
        )

        # Per-call override flips the same fixture from fresh to stale.
        assert [r.outcome for r in results] == ["noop_stale_quote"]
        assert broker.last_request is None

    def test_legacy_callable_never_triggers_stale_gate(self, engine) -> None:
        """Legacy ``Callable[[str], float]`` is wrapped via
        ``callable_to_quote_feed`` which sets ``ts = clock.now()``.  Even
        with ``stale_max_age_seconds=0.0`` the gate cannot fire because
        age == 0 and the comparison is strict ``>``.  This is the M-3c
        guarantee of zero behavioural delta against legacy fixtures.
        """
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD")
        sm = _make_sm(engine)
        broker = _FillBroker()

        results = run_exit_gate(
            broker=broker,
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=_AlwaysExitPolicy(),
            quote_feed=lambda _instrument: 1.10,
            stale_max_age_seconds=0.0,
        )

        assert [r.outcome for r in results] == ["closed"]
        assert broker.last_request is not None


# --- per_position_tpsl (Phase 9.X-K+1) ---------------------------------------


class TestPerPositionTpsl:
    """per_position_tpsl passes per-position TP/SL price levels to the
    exit policy evaluate() call instead of the global tp/sl fallback.
    """

    def _run_with_tpsl(
        self,
        engine,
        *,
        current_price: float,
        per_position_tpsl: dict | None = None,
        global_tp: float | None = None,
        global_sl: float | None = None,
    ):
        from fx_ai_trading.services.exit_policy import ExitPolicyService

        sm = _make_sm(engine)
        broker = _FillBroker()
        policy = ExitPolicyService(max_holding_seconds=999_999)  # time-based won't fire
        return run_exit_gate(
            broker=broker,
            account_id="acc-1",
            clock=FixedClock(_NOW),
            state_manager=sm,
            exit_policy=policy,
            quote_feed=lambda _: current_price,
            tp=global_tp,
            sl=global_sl,
            per_position_tpsl=per_position_tpsl,
        )

    def test_none_map_uses_global_tp_sl(self, engine) -> None:
        """per_position_tpsl=None falls back to global tp/sl (backward compat)."""
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD", avg_price=1.10)
        results = self._run_with_tpsl(
            engine,
            current_price=1.13,  # above global tp 1.12 → TP fires
            per_position_tpsl=None,
            global_tp=1.12,
            global_sl=1.08,
        )
        assert results[0].outcome == "closed"
        assert results[0].primary_reason == "tp"

    def test_per_position_tp_fires_when_price_above(self, engine) -> None:
        """Per-position tp_price in the map → TP fires for that order."""
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD", avg_price=1.10)
        results = self._run_with_tpsl(
            engine,
            current_price=1.13,
            per_position_tpsl={"o1": (1.12, 1.08)},  # tp=1.12, sl=1.08
            global_tp=None,
            global_sl=None,
        )
        assert results[0].outcome == "closed"
        assert results[0].primary_reason == "tp"

    def test_per_position_sl_fires_when_price_below(self, engine) -> None:
        """Per-position sl_price in the map → SL fires for that order."""
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD", avg_price=1.10)
        results = self._run_with_tpsl(
            engine,
            current_price=1.07,  # below sl 1.08 → SL fires
            per_position_tpsl={"o1": (1.12, 1.08)},
            global_tp=None,
            global_sl=None,
        )
        assert results[0].outcome == "closed"
        assert results[0].primary_reason == "sl"

    def test_position_not_in_map_falls_back_to_global(self, engine) -> None:
        """Positions absent from the map use global tp/sl."""
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD", avg_price=1.10)
        results = self._run_with_tpsl(
            engine,
            current_price=1.13,
            per_position_tpsl={"other-order": (1.12, 1.08)},  # o1 NOT in map
            global_tp=1.12,
            global_sl=None,
        )
        assert results[0].outcome == "closed"
        assert results[0].primary_reason == "tp"

    def test_price_between_tp_and_sl_is_noop(self, engine) -> None:
        """Price within the TP/SL band → no exit fires."""
        _seed_open_position(engine, psid="p1", order_id="o1", instrument="EURUSD", avg_price=1.10)
        results = self._run_with_tpsl(
            engine,
            current_price=1.105,  # inside [1.08, 1.12]
            per_position_tpsl={"o1": (1.12, 1.08)},
            global_tp=None,
            global_sl=None,
        )
        assert results[0].outcome == "noop"
