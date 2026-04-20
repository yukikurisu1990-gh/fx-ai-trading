"""Integration: Execution Gate + StateManager (Cycle 6.7a/b).

Asserts:
  - When ``state_manager`` is injected, G1/G2/G3 guards derive their
    inputs from ``StateManager.snapshot()`` (positions timeline in 6.7b).
  - G1/G2 respond to positions rows (not orders rows) — the 6.7b
    authoritative source switch.
  - ORDER_EXPIRED rows do NOT increment the G3 failure counter (L1).
  - Cross-account isolation via positions.
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

# --- DDL (superset: all tables needed by 6.7b write path) ---------------------

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


# --- Test doubles --------------------------------------------------------------


@dataclass
class _NeverBroker:
    account_type: str = "demo"
    call_count: int = 0

    def place_order(self, request: OrderRequest) -> OrderResult:
        self.call_count += 1
        raise AssertionError(
            f"broker must not be called on blocked path (called {self.call_count}×)"
        )


_: Broker = _NeverBroker()


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


# --- Helpers ------------------------------------------------------------------


def _seed_signal(
    engine,
    *,
    ts_id: str | None = None,
    instrument: str = "EURUSD",
    ttl_seconds: int = 3600,
) -> str:
    ts_id = ts_id or generate_ulid()
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
                    :now, 'corr-sm-1', :ttl
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


def _seed_open_position(
    engine,
    *,
    instrument: str,
    account_id: str = "acc-1",
    order_id: str | None = None,
) -> str:
    """Directly insert a positions 'open' row to simulate a prior fill."""
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


def _seed_txn(
    engine,
    *,
    transaction_type: str,
    account_id: str = "acc-1",
    offset_seconds: int = 60,
) -> None:
    txn_id = generate_ulid()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO order_transactions (
                    broker_txn_id, account_id, order_id, transaction_type,
                    transaction_time_utc, payload, received_at_utc
                ) VALUES (
                    :txid, :aid, 'prev-oid', :ttype,
                    :ttu, '{}', :ttu
                )
                """
            ),
            {
                "txid": txn_id,
                "aid": account_id,
                "ttype": transaction_type,
                "ttu": (_FIXED_NOW - timedelta(seconds=offset_seconds)).isoformat(),
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


def _run_with_state_manager(
    engine,
    *,
    broker=None,
    account_id: str = "acc-1",
    risk_manager: RiskManagerService | None = None,
    state_manager: StateManager,
) -> object:
    return run_execution_gate(
        engine,
        broker=broker or _NeverBroker(),
        account_id=account_id,
        clock=FixedClock(_FIXED_NOW),
        risk_manager=risk_manager,
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


def _make_sm(engine, account_id: str = "acc-1") -> StateManager:
    return StateManager(engine, account_id=account_id, clock=FixedClock(_FIXED_NOW))


# --- G1 duplicate instrument (positions-based) --------------------------------


class TestG1DuplicateViaStateManager:
    def test_blocks_when_positions_has_open_row(self, engine) -> None:
        # Seed a positions 'open' row — StateManager reads from positions now.
        _seed_open_position(engine, instrument="EURUSD", account_id="acc-1")
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        risk_mgr = RiskManagerService(
            max_concurrent_positions=5,
            position_sizer=PositionSizerService(),
            max_open_positions=5,
            cooloff_max_failures=99,
        )
        result = _run_with_state_manager(engine, risk_manager=risk_mgr, state_manager=sm)
        assert result.outcome == "blocked"
        assert result.reject_reason == "risk.duplicate_instrument"


# --- G2 max open positions (positions-based) ----------------------------------


class TestG2MaxOpenViaStateManager:
    def test_blocks_when_positions_count_reaches_cap(self, engine) -> None:
        for sym in ("USDJPY", "GBPUSD"):
            _seed_open_position(engine, instrument=sym, account_id="acc-1")
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        risk_mgr = RiskManagerService(
            max_concurrent_positions=5,
            position_sizer=PositionSizerService(),
            max_open_positions=2,
            cooloff_max_failures=99,
        )
        result = _run_with_state_manager(engine, risk_manager=risk_mgr, state_manager=sm)
        assert result.outcome == "blocked"
        assert result.reject_reason == "risk.max_open_positions"


# --- G3 cooloff via StateManager (L1 semantics) --------------------------------


class TestG3CooloffViaStateManager:
    def test_counts_order_reject_as_failure(self, engine) -> None:
        for _ in range(3):
            _seed_txn(engine, transaction_type="ORDER_REJECT", offset_seconds=30)
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        risk_mgr = RiskManagerService(
            max_concurrent_positions=5,
            position_sizer=PositionSizerService(),
            max_open_positions=5,
            cooloff_max_failures=3,
        )
        result = _run_with_state_manager(engine, risk_manager=risk_mgr, state_manager=sm)
        assert result.outcome == "blocked"
        assert result.reject_reason == "risk.recent_execution_failure_cooloff"

    def test_counts_order_timeout_as_failure(self, engine) -> None:
        for _ in range(3):
            _seed_txn(engine, transaction_type="ORDER_TIMEOUT", offset_seconds=30)
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        risk_mgr = RiskManagerService(
            max_concurrent_positions=5,
            position_sizer=PositionSizerService(),
            max_open_positions=5,
            cooloff_max_failures=3,
        )
        result = _run_with_state_manager(engine, risk_manager=risk_mgr, state_manager=sm)
        assert result.outcome == "blocked"
        assert result.reject_reason == "risk.recent_execution_failure_cooloff"

    def test_order_expired_does_not_trigger_cooloff(self, engine) -> None:
        for _ in range(10):
            _seed_txn(engine, transaction_type="ORDER_EXPIRED", offset_seconds=30)
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        risk_mgr = RiskManagerService(
            max_concurrent_positions=5,
            position_sizer=PositionSizerService(),
            max_open_positions=5,
            cooloff_max_failures=3,
        )
        result = _run_with_state_manager(
            engine, broker=_AcceptBroker(), risk_manager=risk_mgr, state_manager=sm
        )
        assert result.outcome == "filled"

    def test_mixed_expired_and_reject_counts_only_reject(self, engine) -> None:
        for _ in range(2):
            _seed_txn(engine, transaction_type="ORDER_EXPIRED", offset_seconds=30)
        for _ in range(2):
            _seed_txn(engine, transaction_type="ORDER_REJECT", offset_seconds=30)
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine)
        risk_mgr = RiskManagerService(
            max_concurrent_positions=5,
            position_sizer=PositionSizerService(),
            max_open_positions=5,
            cooloff_max_failures=3,
        )
        result = _run_with_state_manager(
            engine, broker=_AcceptBroker(), risk_manager=risk_mgr, state_manager=sm
        )
        assert result.outcome == "filled"


# --- Cross-account isolation (positions-based) --------------------------------


class TestAccountIsolation:
    def test_other_account_positions_not_visible(self, engine) -> None:
        for sym in ("USDJPY", "GBPUSD"):
            _seed_open_position(engine, instrument=sym, account_id="acc-OTHER")
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine, account_id="acc-1")
        risk_mgr = RiskManagerService(
            max_concurrent_positions=5,
            position_sizer=PositionSizerService(),
            max_open_positions=2,
            cooloff_max_failures=99,
        )
        result = _run_with_state_manager(
            engine, broker=_AcceptBroker(), risk_manager=risk_mgr, state_manager=sm
        )
        assert result.outcome == "filled"

    def test_other_account_failures_not_visible(self, engine) -> None:
        for _ in range(5):
            _seed_txn(
                engine, transaction_type="ORDER_REJECT", account_id="acc-OTHER", offset_seconds=30
            )
        _seed_signal(engine, instrument="EURUSD")
        sm = _make_sm(engine, account_id="acc-1")
        risk_mgr = RiskManagerService(
            max_concurrent_positions=5,
            position_sizer=PositionSizerService(),
            max_open_positions=5,
            cooloff_max_failures=3,
        )
        result = _run_with_state_manager(
            engine, broker=_AcceptBroker(), risk_manager=risk_mgr, state_manager=sm
        )
        assert result.outcome == "filled"
