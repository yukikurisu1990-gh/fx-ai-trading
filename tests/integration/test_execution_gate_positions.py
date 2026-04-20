"""Integration: Execution Gate E2E — positions and risk_events write path (Cycle 6.7b).

Asserts the full round-trip when StateManager is injected:
  - A successful broker fill writes a positions 'open' row via on_fill.
  - A second signal for the same instrument is blocked (G1) and does NOT
    write a second positions row.
  - A risk reject (G1/G2/G3) writes a risk_events row with verdict='reject'
    and the dotted constraint_violated code (L6).
  - A risk accept writes a risk_events row with verdict='accept',
    constraint_violated=NULL.
  - A blocked path (G1 reject) writes risk_events but no new positions row.
  - size_units==0 (compute_size fail) writes a reject risk_events row.
  - The positions row is also present in secondary_sync_outbox (F-12).
  - The risk_events row is also present in secondary_sync_outbox.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

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

# --- DDL ----------------------------------------------------------------------

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
        conn.execute(text(_DDL_CLOSE_EVENTS))
        conn.execute(text(_DDL_RISK_EVENTS))
        conn.execute(text(_DDL_OUTBOX))
    yield eng
    eng.dispose()


# --- Test doubles -------------------------------------------------------------


class _AcceptBroker:
    account_type = "demo"

    def place_order(self, request: OrderRequest) -> OrderResult:
        return OrderResult(
            client_order_id=request.client_order_id,
            broker_order_id="bk-ok",
            status="filled",
            filled_units=request.size_units,
            fill_price=1.1,
            message="ok",
        )


@dataclass
class _NeverBroker:
    account_type: str = "demo"

    def place_order(self, request: OrderRequest) -> OrderResult:
        raise AssertionError("broker must not be called on blocked path")


_: Broker = _NeverBroker()


# --- Helpers ------------------------------------------------------------------


def _seed_signal(
    engine,
    *,
    instrument: str = "EURUSD",
    ttl_seconds: int = 3600,
) -> str:
    ts_id = generate_ulid()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO trading_signals (
                    trading_signal_id, meta_decision_id, cycle_id,
                    instrument, strategy_id, signal_direction,
                    signal_time_utc, correlation_id, ttl_seconds
                ) VALUES (
                    :tsid, :mid, :cid,
                    :inst, 'strat-1', 'buy',
                    :now, 'corr-1', :ttl
                )
                """
            ),
            {
                "tsid": ts_id,
                "mid": f"meta-{ts_id}",
                "cid": f"cyc-{ts_id}",
                "inst": instrument,
                "now": _FIXED_NOW.isoformat(),
                "ttl": ttl_seconds,
            },
        )
    return ts_id


def _seed_open_position(engine, *, instrument: str, account_id: str = "acc-1") -> None:
    psid = generate_ulid()
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
                "oid": generate_ulid(),
                "aid": account_id,
                "inst": instrument,
                "ts": _FIXED_NOW.isoformat(),
            },
        )


def _instrument(symbol: str = "EURUSD") -> Instrument:
    return Instrument(
        instrument=symbol,
        base_currency=symbol[:3],
        quote_currency=symbol[3:],
        pip_location=-4,
        min_trade_units=1,
    )


def _make_sm(engine, account_id: str = "acc-1") -> StateManager:
    return StateManager(engine, account_id=account_id, clock=FixedClock(_FIXED_NOW))


def _run(
    engine,
    *,
    broker=None,
    account_id: str = "acc-1",
    risk_manager: RiskManagerService | None = None,
    state_manager: StateManager,
    max_open: int = 5,
) -> object:
    rm = risk_manager or RiskManagerService(
        max_concurrent_positions=5,
        position_sizer=PositionSizerService(),
        max_open_positions=max_open,
        cooloff_max_failures=99,
    )
    return run_execution_gate(
        engine,
        broker=broker or _AcceptBroker(),
        account_id=account_id,
        clock=FixedClock(_FIXED_NOW),
        risk_manager=rm,
        account_balance=10_000.0,
        risk_pct=1.0,
        sl_pips=10.0,
        instruments={
            "EURUSD": _instrument(),
            "USDJPY": _instrument("USDJPY"),
            "GBPUSD": _instrument("GBPUSD"),
        },
        state_manager=state_manager,
    )


def _positions(engine, *, account_id: str = "acc-1") -> list:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM positions WHERE account_id = :aid"),
            {"aid": account_id},
        ).fetchall()


def _risk_events(engine) -> list:
    with engine.connect() as conn:
        return conn.execute(text("SELECT * FROM risk_events")).fetchall()


def _outbox(engine, *, table_name: str) -> list:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM secondary_sync_outbox WHERE table_name = :tn"),
            {"tn": table_name},
        ).fetchall()


# --- E2E: fill path -----------------------------------------------------------


class TestFillWritesPositions:
    def test_successful_fill_creates_positions_open_row(self, engine) -> None:
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        result = _run(engine, state_manager=sm)
        assert result.outcome == "filled"
        rows = _positions(engine)
        assert len(rows) == 1
        assert rows[0].event_type == "open"
        assert rows[0].instrument == "EURUSD"

    def test_positions_row_in_outbox(self, engine) -> None:
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        _run(engine, state_manager=sm)
        rows = _outbox(engine, table_name="positions")
        assert len(rows) == 1
        payload = json.loads(rows[0].payload_json)
        assert payload["event_type"] == "open"

    def test_fill_accept_verdict_written_to_risk_events(self, engine) -> None:
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        result = _run(engine, state_manager=sm)
        assert result.outcome == "filled"
        events = _risk_events(engine)
        accept_events = [e for e in events if e.verdict == "accept"]
        assert len(accept_events) == 1
        assert accept_events[0].constraint_violated is None

    def test_accept_risk_event_in_outbox(self, engine) -> None:
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        _run(engine, state_manager=sm)
        rows = _outbox(engine, table_name="risk_events")
        assert len(rows) == 1
        payload = json.loads(rows[0].payload_json)
        assert payload["verdict"] == "accept"


# --- E2E: G1 duplicate instrument reject --------------------------------------


class TestG1RejectWritesRiskEvents:
    def test_g1_reject_writes_risk_event_with_constraint(self, engine) -> None:
        _seed_open_position(engine, instrument="EURUSD")
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        result = _run(engine, broker=_NeverBroker(), state_manager=sm)
        assert result.outcome == "blocked"
        events = _risk_events(engine)
        assert len(events) == 1
        assert events[0].verdict == "reject"
        assert events[0].constraint_violated == "risk.duplicate_instrument"

    def test_g1_reject_does_not_write_positions_row(self, engine) -> None:
        _seed_open_position(engine, instrument="EURUSD")
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        _run(engine, broker=_NeverBroker(), state_manager=sm)
        rows = _positions(engine)
        # Only the seeded row exists; no new row from on_fill
        assert len(rows) == 1
        assert rows[0].event_type == "open"

    def test_g1_reject_risk_event_in_outbox(self, engine) -> None:
        _seed_open_position(engine, instrument="EURUSD")
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        _run(engine, broker=_NeverBroker(), state_manager=sm)
        rows = _outbox(engine, table_name="risk_events")
        assert len(rows) == 1
        payload = json.loads(rows[0].payload_json)
        assert payload["verdict"] == "reject"
        assert payload["constraint_violated"] == "risk.duplicate_instrument"


# --- E2E: G2 max open positions reject ----------------------------------------


class TestG2RejectWritesRiskEvents:
    def test_g2_reject_constraint_is_max_open_positions(self, engine) -> None:
        for sym in ("USDJPY", "GBPUSD"):
            _seed_open_position(engine, instrument=sym)
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        result = _run(engine, broker=_NeverBroker(), state_manager=sm, max_open=2)
        assert result.outcome == "blocked"
        events = _risk_events(engine)
        assert len(events) == 1
        assert events[0].constraint_violated == "risk.max_open_positions"


# --- E2E: second signal after fill -------------------------------------------


class TestSecondSignalAfterFill:
    def test_second_signal_for_same_instrument_blocked_by_g1(self, engine) -> None:
        # First signal fills successfully → positions row written
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        first = _run(engine, state_manager=sm)
        assert first.outcome == "filled"

        # Second signal for EURUSD → G1 should block (positions row exists)
        _seed_signal(engine, instrument="EURUSD")
        second = _run(engine, broker=_NeverBroker(), state_manager=sm)
        assert second.outcome == "blocked"
        assert second.reject_reason == "risk.duplicate_instrument"

    def test_after_fill_positions_count_increments(self, engine) -> None:
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        _run(engine, state_manager=sm)
        assert sm.open_instruments() == frozenset({"EURUSD"})


# --- E2E: compute_size=0 → reject risk_event ----------------------------------


class TestComputeSizeZeroPath:
    def test_size_zero_writes_reject_risk_event(self, engine) -> None:
        """When compute_size returns 0 (e.g. SizeUnderMin), on_risk_verdict
        must be called with verdict='reject' and a dotted constraint code."""
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        # sl_pips=0 → PositionSizer returns size=0 (division by zero guard)
        result = run_execution_gate(
            engine,
            broker=_NeverBroker(),
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
            risk_manager=RiskManagerService(
                max_concurrent_positions=5,
                position_sizer=PositionSizerService(),
                max_open_positions=5,
                cooloff_max_failures=99,
            ),
            account_balance=10_000.0,
            risk_pct=1.0,
            sl_pips=0.0,  # triggers size=0
            instruments={"EURUSD": _instrument()},
            state_manager=sm,
        )
        assert result.outcome == "blocked"
        events = _risk_events(engine)
        assert len(events) == 1
        assert events[0].verdict == "reject"
        assert events[0].constraint_violated is not None
        assert events[0].constraint_violated.startswith("risk.")

    def test_size_zero_does_not_write_positions_row(self, engine) -> None:
        """Blocked by compute_size=0 → broker not called → no positions row."""
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        run_execution_gate(
            engine,
            broker=_NeverBroker(),
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
            risk_manager=RiskManagerService(
                max_concurrent_positions=5,
                position_sizer=PositionSizerService(),
                max_open_positions=5,
                cooloff_max_failures=99,
            ),
            account_balance=10_000.0,
            risk_pct=1.0,
            sl_pips=0.0,
            instruments={"EURUSD": _instrument()},
            state_manager=sm,
        )
        assert _positions(engine) == []

    def test_size_zero_risk_event_in_outbox(self, engine) -> None:
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        run_execution_gate(
            engine,
            broker=_NeverBroker(),
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
            risk_manager=RiskManagerService(
                max_concurrent_positions=5,
                position_sizer=PositionSizerService(),
                max_open_positions=5,
                cooloff_max_failures=99,
            ),
            account_balance=10_000.0,
            risk_pct=1.0,
            sl_pips=0.0,
            instruments={"EURUSD": _instrument()},
            state_manager=sm,
        )
        rows = _outbox(engine, table_name="risk_events")
        assert len(rows) == 1
        import json

        payload = json.loads(rows[0].payload_json)
        assert payload["verdict"] == "reject"
