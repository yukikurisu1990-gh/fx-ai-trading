"""Integration: Execution Gate Risk-blocked path — Phase 6 Cycle 6.6.

Covers the new ``blocked`` outcome introduced by the RiskManager
integration.  Invariants asserted:

  - On size==0 or allow_trade()==False:
      * broker.place_order is NEVER called,
      * exactly one ``orders`` row is written with status=CANCELED,
      * exactly one ``no_trade_events`` row is written with
        reason_category=``risk`` and reason_code matching the specific
        guard,
      * zero ``order_transactions`` rows,
      * ``outcome`` == ``"blocked"`` and ``reject_reason`` carries the
        dotted ``risk.*`` code.
  - Both persisted rows are mirrored into secondary_sync_outbox (F-12).
  - Append-only: a second run after the first blocked call never
    mutates any earlier row.
  - Cycle 6.5 baseline path (no Risk injected) still works unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.domain.broker import Broker, OrderRequest, OrderResult
from fx_ai_trading.domain.risk import Instrument
from fx_ai_trading.services.execution_gate_runner import run_execution_gate
from fx_ai_trading.services.position_sizer import PositionSizerService
from fx_ai_trading.services.risk_manager import RiskManagerService
from fx_ai_trading.services.state_manager import StateManager

_FIXED_NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)

# --- DDL superset (trimmed copy of the Cycle 6.5 integration fixture) ----

_DDL_TRADING_SIGNALS = """
CREATE TABLE trading_signals (
    trading_signal_id TEXT PRIMARY KEY,
    meta_decision_id  TEXT NOT NULL,
    cycle_id          TEXT NOT NULL,
    instrument        TEXT NOT NULL,
    strategy_id       TEXT NOT NULL,
    signal_direction  TEXT NOT NULL,
    signal_time_utc   TEXT NOT NULL,
    correlation_id    TEXT,
    ttl_seconds       INTEGER
)
"""

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
    status            TEXT NOT NULL DEFAULT 'PENDING',
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

_DDL_NO_TRADE_EVENTS = """
CREATE TABLE no_trade_events (
    no_trade_event_id TEXT PRIMARY KEY,
    cycle_id          TEXT,
    meta_decision_id  TEXT,
    reason_category   TEXT NOT NULL,
    reason_code       TEXT NOT NULL,
    reason_detail     TEXT,
    source_component  TEXT NOT NULL,
    instrument        TEXT,
    strategy_id       TEXT,
    event_time_utc    TEXT NOT NULL
)
"""

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

_DDL_RISK_EVENTS = """
CREATE TABLE risk_events (
    risk_event_id       TEXT PRIMARY KEY,
    cycle_id            TEXT,
    instrument          TEXT,
    strategy_id         TEXT,
    verdict             TEXT NOT NULL,
    constraint_violated TEXT,
    detail              TEXT,
    event_time_utc      TEXT NOT NULL
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
        conn.execute(text(_DDL_TRADING_SIGNALS))
        conn.execute(text(_DDL_ORDERS))
        conn.execute(text(_DDL_ORDER_TRANSACTIONS))
        conn.execute(text(_DDL_NO_TRADE_EVENTS))
        conn.execute(text(_DDL_POSITIONS))
        conn.execute(text(_DDL_RISK_EVENTS))
        conn.execute(text(_DDL_OUTBOX))
    yield eng
    eng.dispose()


# --- Test doubles ----------------------------------------------------------


@dataclass
class _RecordingBroker:
    """Raises if called; proves the Risk path never reaches the broker."""

    account_type: str = "demo"
    call_count: int = 0

    def place_order(self, request: OrderRequest) -> OrderResult:
        self.call_count += 1
        raise AssertionError(
            "broker.place_order must not be called on Risk-blocked outcomes "
            f"(invoked {self.call_count}× with {request.client_order_id!r})"
        )


# Broker Protocol is structural — static assertion that _RecordingBroker matches.
_: Broker = _RecordingBroker()


def _seed_pending_signal(
    engine,
    *,
    trading_signal_id: str | None = None,
    instrument: str = "EURUSD",
    direction: str = "buy",
    correlation_id: str = "corr-risk-1",
    ttl_seconds: int = 3600,
) -> str:
    ts_id = trading_signal_id or generate_ulid()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO trading_signals (
                    trading_signal_id, meta_decision_id, cycle_id,
                    instrument, strategy_id, signal_direction,
                    signal_time_utc, correlation_id, ttl_seconds
                ) VALUES (
                    :trading_signal_id, :meta_decision_id, :cycle_id,
                    :instrument, :strategy_id, :signal_direction,
                    :signal_time_utc, :correlation_id, :ttl_seconds
                )
                """
            ),
            {
                "trading_signal_id": ts_id,
                "meta_decision_id": f"meta-{ts_id}",
                "cycle_id": f"cyc-{ts_id}",
                "instrument": instrument,
                "strategy_id": "strat-1",
                "signal_direction": direction,
                "signal_time_utc": _FIXED_NOW.isoformat(),
                "correlation_id": correlation_id,
                "ttl_seconds": ttl_seconds,
            },
        )
    return ts_id


def _instrument(symbol: str = "EURUSD", min_lot: int = 1000) -> Instrument:
    return Instrument(
        instrument=symbol,
        base_currency=symbol[:3],
        quote_currency=symbol[3:],
        pip_location=-4,
        min_trade_units=min_lot,
    )


def _risk_manager_default() -> RiskManagerService:
    return RiskManagerService(
        max_concurrent_positions=5,
        position_sizer=PositionSizerService(),
        max_open_positions=5,
        cooloff_max_failures=3,
    )


def _sm(engine) -> StateManager:
    return StateManager(engine, account_id="acc-1", clock=FixedClock(_FIXED_NOW))


def _seed_open_position(
    engine,
    *,
    instrument: str,
    account_id: str = "acc-1",
    order_id: str | None = None,
) -> str:
    """Insert a positions 'open' row.  Mirrors StateManager.on_fill semantics
    for tests that need the instrument to appear in ``open_instruments()``."""
    psid = generate_ulid()
    oid = order_id or generate_ulid()
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
                    'open', 1000, 1.1, NULL, NULL,
                    :ts, NULL
                )
                """
            ),
            {
                "psid": psid,
                "oid": oid,
                "aid": account_id,
                "inst": instrument,
                "ts": _FIXED_NOW.isoformat(),
            },
        )
    return psid


def _seed_broker_failure_txn(
    engine,
    *,
    transaction_type: str,
    suffix: str,
    account_id: str = "acc-1",
    offset_seconds: int = 60,
) -> None:
    """Insert one order_transactions row of a broker-failure type.

    ``transaction_type`` must be one of StateManager's failure set
    (ORDER_REJECT / ORDER_TIMEOUT) to be counted by recent_execution_failures_within.
    """
    txn_id = f"txn-{suffix}"
    event_time = _FIXED_NOW - timedelta(seconds=offset_seconds)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO order_transactions (
                    broker_txn_id, account_id, order_id, transaction_type,
                    transaction_time_utc, payload, received_at_utc
                ) VALUES (
                    :txn_id, :aid, NULL, :ttype,
                    :ts, '{}', :ts
                )
                """
            ),
            {
                "txn_id": txn_id,
                "aid": account_id,
                "ttype": transaction_type,
                "ts": event_time.isoformat(),
            },
        )


# --- size==0 blocked path --------------------------------------------------


class TestSizeUnderMinBlocks:
    def test_size_under_min_writes_orders_no_trade_events_no_txn(self, engine) -> None:
        _seed_pending_signal(engine)
        broker = _RecordingBroker(account_type="demo")

        # sl_pips=10 + risk_pct=1% + balance=100 → raw_units=0.1 < min_lot 1000.
        result = run_execution_gate(
            engine,
            broker=broker,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
            risk_manager=_risk_manager_default(),
            account_balance=100.0,
            risk_pct=1.0,
            sl_pips=10.0,
            instruments={"EURUSD": _instrument(min_lot=1000)},
            state_manager=_sm(engine),
        )

        assert result.outcome == "blocked"
        assert result.order_status == "CANCELED"
        assert result.reject_reason == "risk.size_under_min"
        assert result.order_transactions_written == 0
        assert result.no_trade_events_written == 1
        assert broker.call_count == 0

        with engine.connect() as conn:
            orders = conn.execute(
                text("SELECT status, canceled_at FROM orders WHERE trading_signal_id IS NOT NULL")
            ).fetchall()
            txns = conn.execute(text("SELECT count(*) FROM order_transactions")).scalar()
            events = conn.execute(
                text("SELECT reason_category, reason_code, instrument FROM no_trade_events")
            ).fetchall()

        assert len(orders) == 1
        assert orders[0].status == "CANCELED"
        assert orders[0].canceled_at is not None
        assert txns == 0
        assert len(events) == 1
        assert events[0].reason_category == "risk"
        assert events[0].reason_code == "size_under_min"
        assert events[0].instrument == "EURUSD"


class TestInvalidSLBlocks:
    def test_invalid_sl_is_reported_as_risk_invalid_sl(self, engine) -> None:
        _seed_pending_signal(engine)
        broker = _RecordingBroker(account_type="demo")
        result = run_execution_gate(
            engine,
            broker=broker,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
            risk_manager=_risk_manager_default(),
            account_balance=10_000.0,
            risk_pct=1.0,
            sl_pips=0.0,  # invalid
            instruments={"EURUSD": _instrument()},
            state_manager=_sm(engine),
        )
        assert result.outcome == "blocked"
        assert result.reject_reason == "risk.invalid_sl"
        assert broker.call_count == 0


# --- allow_trade G1/G2/G3 blocked paths ------------------------------------


class TestDuplicateInstrumentBlocks:
    def test_g1_fires_when_instrument_has_an_open_position(self, engine) -> None:
        # Seed an 'open' positions row for EURUSD so StateManager.snapshot()
        # reports it as currently held.  (Cycle 6.7d: authoritative source
        # is the positions table, not the orders table.)
        _seed_open_position(engine, instrument="EURUSD")
        _seed_pending_signal(engine, instrument="EURUSD")

        broker = _RecordingBroker(account_type="demo")
        result = run_execution_gate(
            engine,
            broker=broker,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
            risk_manager=_risk_manager_default(),
            account_balance=10_000.0,
            risk_pct=1.0,
            sl_pips=10.0,  # computes size > 0
            instruments={"EURUSD": _instrument(min_lot=1)},
            state_manager=_sm(engine),
        )

        assert result.outcome == "blocked"
        assert result.reject_reason == "risk.duplicate_instrument"
        assert broker.call_count == 0

        with engine.connect() as conn:
            codes = [
                r.reason_code
                for r in conn.execute(text("SELECT reason_code FROM no_trade_events")).fetchall()
            ]
        assert codes == ["duplicate_instrument"]


class TestMaxOpenPositionsBlocks:
    def test_g2_fires_when_concurrent_cap_is_reached(self, engine) -> None:
        # Seed 2 'open' positions rows on different instruments; max_open_positions=2.
        for sym in ("USDJPY", "GBPUSD"):
            _seed_open_position(engine, instrument=sym)
        _seed_pending_signal(engine, instrument="EURUSD")  # fresh instrument

        risk_mgr = RiskManagerService(
            max_concurrent_positions=5,
            position_sizer=PositionSizerService(),
            max_open_positions=2,  # tight cap
            cooloff_max_failures=99,
        )
        broker = _RecordingBroker(account_type="demo")
        result = run_execution_gate(
            engine,
            broker=broker,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
            risk_manager=risk_mgr,
            account_balance=10_000.0,
            risk_pct=1.0,
            sl_pips=10.0,
            instruments={"EURUSD": _instrument(min_lot=1)},
            state_manager=_sm(engine),
        )

        assert result.outcome == "blocked"
        assert result.reject_reason == "risk.max_open_positions"
        assert broker.call_count == 0


class TestCooloffBlocks:
    def test_g3_fires_when_recent_failures_reach_threshold(self, engine) -> None:
        # Seed 3 broker-failure order_transactions rows within the cool-off
        # window.  (Cycle 6.7d: authoritative failure signal is
        # order_transactions.ORDER_REJECT / ORDER_TIMEOUT, not orders.status.)
        for i in range(3):
            _seed_broker_failure_txn(engine, transaction_type="ORDER_REJECT", suffix=f"f-{i}")
        _seed_pending_signal(engine, instrument="EURUSD")

        risk_mgr = RiskManagerService(
            max_concurrent_positions=5,
            position_sizer=PositionSizerService(),
            max_open_positions=5,
            cooloff_max_failures=3,
        )
        broker = _RecordingBroker(account_type="demo")
        result = run_execution_gate(
            engine,
            broker=broker,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
            risk_manager=risk_mgr,
            account_balance=10_000.0,
            risk_pct=1.0,
            sl_pips=10.0,
            instruments={"EURUSD": _instrument(min_lot=1)},
            state_manager=_sm(engine),
        )

        assert result.outcome == "blocked"
        assert result.reject_reason == "risk.recent_execution_failure_cooloff"
        assert broker.call_count == 0


# --- Invariants ------------------------------------------------------------


class TestAppendOnlyAcrossTwoBlockedCycles:
    def test_second_blocked_run_does_not_mutate_first(self, engine) -> None:
        _seed_pending_signal(engine, trading_signal_id="ts-a", instrument="EURUSD")

        result_a = run_execution_gate(
            engine,
            broker=_RecordingBroker(account_type="demo"),
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
            risk_manager=_risk_manager_default(),
            account_balance=100.0,
            risk_pct=1.0,
            sl_pips=500.0,
            instruments={"EURUSD": _instrument(min_lot=1000)},
            state_manager=_sm(engine),
        )
        assert result_a.outcome == "blocked"

        with engine.connect() as conn:
            first_snapshot = conn.execute(text("SELECT order_id, status FROM orders")).fetchall()
            first_event_ids = {
                r[0]
                for r in conn.execute(
                    text("SELECT no_trade_event_id FROM no_trade_events")
                ).fetchall()
            }
        assert len(first_snapshot) == 1
        assert len(first_event_ids) == 1

        # Second signal → second block.  First rows must stay untouched.
        _seed_pending_signal(engine, trading_signal_id="ts-b", instrument="EURUSD")
        result_b = run_execution_gate(
            engine,
            broker=_RecordingBroker(account_type="demo"),
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
            risk_manager=_risk_manager_default(),
            account_balance=100.0,
            risk_pct=1.0,
            sl_pips=500.0,
            instruments={"EURUSD": _instrument(min_lot=1000)},
            state_manager=_sm(engine),
        )
        assert result_b.outcome == "blocked"

        with engine.connect() as conn:
            second_snapshot = conn.execute(
                text("SELECT order_id, status FROM orders ORDER BY order_id")
            ).fetchall()
            second_event_ids = {
                r[0]
                for r in conn.execute(
                    text("SELECT no_trade_event_id FROM no_trade_events")
                ).fetchall()
            }

        assert len(second_snapshot) == 2
        # Every row from the first run must still be there, unchanged.
        first_ids = {r[0] for r in first_snapshot}
        second_ids = {r[0] for r in second_snapshot}
        assert first_ids <= second_ids
        assert first_event_ids <= second_event_ids


class TestOutboxMirrorsBlockedRows:
    def test_orders_and_no_trade_events_land_in_outbox(self, engine) -> None:
        _seed_pending_signal(engine)
        run_execution_gate(
            engine,
            broker=_RecordingBroker(account_type="demo"),
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
            risk_manager=_risk_manager_default(),
            account_balance=100.0,
            risk_pct=1.0,
            sl_pips=500.0,
            instruments={"EURUSD": _instrument(min_lot=1000)},
            state_manager=_sm(engine),
        )
        with engine.connect() as conn:
            tables = sorted(
                r[0]
                for r in conn.execute(
                    text("SELECT DISTINCT table_name FROM secondary_sync_outbox")
                ).fetchall()
            )
        assert "orders" in tables
        assert "no_trade_events" in tables
        assert "order_transactions" not in tables  # invariant: never written


class TestCycle65PathStillWorksWhenRiskDisabled:
    def test_no_risk_injected_behaves_as_before(self, engine) -> None:
        # With risk_manager=None the runner must not call any Risk code
        # and must use the provided size_units unchanged.
        _seed_pending_signal(engine)

        class _AcceptBroker:
            account_type = "demo"

            def place_order(self, request: OrderRequest) -> OrderResult:
                return OrderResult(
                    client_order_id=request.client_order_id,
                    broker_order_id="bk-1",
                    status="filled",
                    filled_units=request.size_units,
                    fill_price=1.1,
                    message="ok",
                )

        result = run_execution_gate(
            engine,
            broker=_AcceptBroker(),
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
            size_units=1234,
            state_manager=_sm(engine),
        )
        assert result.outcome == "filled"
        assert result.order_status == "FILLED"


class TestRiskInputsValidation:
    def test_raises_when_risk_manager_given_without_sizing_inputs(self, engine) -> None:
        _seed_pending_signal(engine)
        with pytest.raises(ValueError, match="account_balance"):
            run_execution_gate(
                engine,
                broker=_RecordingBroker(account_type="demo"),
                account_id="acc-1",
                clock=FixedClock(_FIXED_NOW),
                risk_manager=_risk_manager_default(),
                # missing: account_balance / risk_pct / sl_pips / instruments
                state_manager=_sm(engine),
            )
