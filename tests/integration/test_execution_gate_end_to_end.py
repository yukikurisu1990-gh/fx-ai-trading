"""End-to-end integration: Strategy → Meta → Execution Gate — Phase 6 Cycle 6.5.

Chains run_strategy_cycle, run_meta_cycle, and run_execution_gate in a
single SQLite in-memory process against a real PaperBroker.  Asserts
the Cycle 6.5 completion criterion verbatim:

    1 trading_signal → 1 order → ≥1 order_transaction.

Also verifies:
  - correlation_id threads strategy_signals.meta.decision_chain_id →
    meta_decisions → trading_signals.correlation_id → orders.correlation_id →
    order_transactions.payload.
  - Paper-mode guard survives the full chain (account_type='demo' on
    orders).
  - Second full cycle appends — orders/order_transactions never mutate
    prior rows (append-only invariant).
  - no_trade_events row ends the chain cleanly (execution sees noop).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.adapters.broker.paper import PaperBroker
from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext
from fx_ai_trading.services.execution_gate_runner import run_execution_gate
from fx_ai_trading.services.meta_cycle_runner import run_meta_cycle
from fx_ai_trading.services.strategy_runner import run_strategy_cycle
from fx_ai_trading.strategies import (
    AlwaysNoTradeStrategy,
    DeterministicTrendStrategy,
)

_FIXED_NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)


# --- DDL (superset spanning 0004 → 0006) ---------------------------------

_DDL_STRATEGY_SIGNALS = """
CREATE TABLE strategy_signals (
    cycle_id         TEXT NOT NULL,
    instrument       TEXT NOT NULL,
    strategy_id      TEXT NOT NULL,
    strategy_type    TEXT NOT NULL,
    strategy_version TEXT,
    signal_direction TEXT NOT NULL,
    confidence       NUMERIC(6,4),
    signal_time_utc  TEXT NOT NULL,
    meta             TEXT,
    PRIMARY KEY (cycle_id, instrument, strategy_id)
)
"""

_DDL_META_DECISIONS = """
CREATE TABLE meta_decisions (
    meta_decision_id    TEXT PRIMARY KEY,
    cycle_id            TEXT NOT NULL,
    filter_result       TEXT,
    score_contributions TEXT,
    active_strategies   TEXT,
    regime_detected     TEXT,
    decision_time_utc   TEXT NOT NULL,
    no_trade_reason     TEXT
)
"""

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
        conn.execute(text(_DDL_STRATEGY_SIGNALS))
        conn.execute(text(_DDL_META_DECISIONS))
        conn.execute(text(_DDL_TRADING_SIGNALS))
        conn.execute(text(_DDL_ORDERS))
        conn.execute(text(_DDL_ORDER_TRANSACTIONS))
        conn.execute(text(_DDL_NO_TRADE_EVENTS))
        conn.execute(text(_DDL_OUTBOX))
    yield eng
    eng.dispose()


def _features(inst: str) -> FeatureSet:
    return FeatureSet(
        feature_version="stub.v1",
        feature_hash=f"hash-{inst}",
        feature_stats={"instrument": inst},
        sampled_features={},
        computed_at=_FIXED_NOW,
    )


def _ctx(cycle_id: str) -> StrategyContext:
    return StrategyContext(cycle_id=cycle_id, account_id="acc-1", config_version="cv-1")


def _run_full_chain(
    engine,
    *,
    cycle_id: str,
    instruments: list[str],
    strategies: list,
    broker: PaperBroker,
    clock: FixedClock,
):
    """Helper: strategy → meta → execution, single call each."""
    run_strategy_cycle(
        engine,
        cycle_id=cycle_id,
        instruments=instruments,
        strategies=strategies,
        features={i: _features(i) for i in instruments},
        context=_ctx(cycle_id),
        clock=clock,
    )
    meta = run_meta_cycle(engine, cycle_id=cycle_id, clock=clock)
    exec_result = run_execution_gate(
        engine, broker=broker, account_id="acc-1", clock=clock,
    )
    return meta, exec_result


# --- Cycle 6.5 completion criterion --------------------------------------


class TestCompletionCriterion:
    """`1件の trading_signal から 1件の order と 1件以上の order_transaction`."""

    def test_one_signal_yields_one_order_and_two_transactions(self, engine) -> None:
        broker = PaperBroker(account_type="demo")
        meta, exec_result = _run_full_chain(
            engine,
            cycle_id="cyc-complete",
            instruments=["EURUSD"],
            strategies=[DeterministicTrendStrategy()],
            broker=broker,
            clock=FixedClock(_FIXED_NOW),
        )
        # Meta produced exactly 1 trading_signal.
        assert meta.adopted is True
        assert meta.trading_signal_id is not None
        with engine.connect() as conn:
            ts_count = conn.execute(text("SELECT count(*) FROM trading_signals")).scalar()
        assert ts_count == 1

        # Execution consumed it and produced the minimum round-trip.
        assert exec_result.processed is True
        assert exec_result.outcome == "filled"
        assert exec_result.order_status == "FILLED"
        assert exec_result.order_transactions_written >= 1

        with engine.connect() as conn:
            orders_count = conn.execute(text("SELECT count(*) FROM orders")).scalar()
            txn_count = conn.execute(
                text("SELECT count(*) FROM order_transactions")
            ).scalar()
        assert orders_count == 1
        assert txn_count >= 1


# --- correlation_id end-to-end round-trip --------------------------------


class TestCorrelationRoundTrip:
    def test_chain_id_threads_through_to_order_transactions(self, engine) -> None:
        clock = FixedClock(_FIXED_NOW)
        broker = PaperBroker(account_type="demo")
        run_strategy_cycle(
            engine,
            cycle_id="cyc-corr",
            instruments=["EURUSD"],
            strategies=[DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-corr"),
            clock=clock,
        )

        # chain_id emitted by the strategy.
        with engine.connect() as conn:
            raw_meta = conn.execute(
                text("SELECT meta FROM strategy_signals WHERE cycle_id='cyc-corr'")
            ).scalar()
        strategy_chain_id = json.loads(str(raw_meta))["decision_chain_id"]

        run_meta_cycle(engine, cycle_id="cyc-corr", clock=clock)
        r = run_execution_gate(
            engine, broker=broker, account_id="acc-1", clock=clock,
        )

        # orders.correlation_id matches.
        with engine.connect() as conn:
            order_corr = conn.execute(
                text(
                    "SELECT correlation_id FROM orders WHERE order_id=:oid"
                ),
                {"oid": r.order_id},
            ).scalar()
        assert order_corr == strategy_chain_id

        # order_transactions payload includes the same correlation_id.
        with engine.connect() as conn:
            payloads = [
                json.loads(str(row[0]))
                for row in conn.execute(
                    text(
                        "SELECT payload FROM order_transactions WHERE order_id=:oid"
                    ),
                    {"oid": r.order_id},
                ).fetchall()
            ]
        assert payloads  # at least one
        for p in payloads:
            assert p.get("correlation_id") == strategy_chain_id


# --- Paper-mode guard on the full chain ----------------------------------


class TestPaperModePreserved:
    def test_order_account_type_is_demo_after_full_chain(self, engine) -> None:
        broker = PaperBroker(account_type="demo")
        _run_full_chain(
            engine,
            cycle_id="cyc-demo",
            instruments=["EURUSD"],
            strategies=[DeterministicTrendStrategy()],
            broker=broker,
            clock=FixedClock(_FIXED_NOW),
        )
        with engine.connect() as conn:
            account_types = [
                row[0]
                for row in conn.execute(
                    text("SELECT account_type FROM orders")
                ).fetchall()
            ]
        assert account_types == ["demo"]


# --- Genuine no-trade: chain ends cleanly --------------------------------


class TestAllNoTradeEndsAtExecution:
    def test_only_no_trade_stub_means_execution_noops(self, engine) -> None:
        broker = PaperBroker(account_type="demo")
        meta, exec_result = _run_full_chain(
            engine,
            cycle_id="cyc-allnt",
            instruments=["EURUSD"],
            strategies=[AlwaysNoTradeStrategy()],
            broker=broker,
            clock=FixedClock(_FIXED_NOW),
        )
        # Meta adopted nothing.
        assert meta.adopted is False
        # Execution saw nothing to pick up.
        assert exec_result.processed is False
        assert exec_result.outcome == "noop"

        with engine.connect() as conn:
            orders = conn.execute(text("SELECT count(*) FROM orders")).scalar()
            txns = conn.execute(
                text("SELECT count(*) FROM order_transactions")
            ).scalar()
            nt = conn.execute(
                text(
                    "SELECT reason_code FROM no_trade_events"
                    " WHERE cycle_id='cyc-allnt'"
                )
            ).fetchone()
        assert orders == 0
        assert txns == 0
        assert nt is not None and nt.reason_code == "NO_CANDIDATES"


# --- Append-only across two full cycles ----------------------------------


class TestAppendOnlyAcrossTwoCycles:
    def test_two_full_cycles_accumulate_two_orders(self, engine) -> None:
        broker = PaperBroker(account_type="demo")
        clock = FixedClock(_FIXED_NOW)
        for cid in ["cyc-a", "cyc-b"]:
            _run_full_chain(
                engine,
                cycle_id=cid,
                instruments=["EURUSD"],
                strategies=[DeterministicTrendStrategy()],
                broker=broker,
                clock=clock,
            )

        with engine.connect() as conn:
            orders = conn.execute(text("SELECT count(*) FROM orders")).scalar()
            filled = conn.execute(
                text("SELECT count(*) FROM orders WHERE status='FILLED'")
            ).scalar()
            txn_create = conn.execute(
                text(
                    "SELECT count(*) FROM order_transactions"
                    " WHERE transaction_type='ORDER_CREATE'"
                )
            ).scalar()
            txn_fill = conn.execute(
                text(
                    "SELECT count(*) FROM order_transactions"
                    " WHERE transaction_type='ORDER_FILL'"
                )
            ).scalar()
        assert orders == 2
        assert filled == 2
        assert txn_create == 2
        assert txn_fill == 2


# --- Outbox mirror across the full chain ---------------------------------


class TestOutboxFullChainMirror:
    def test_outbox_rows_cover_every_persisted_table(self, engine) -> None:
        broker = PaperBroker(account_type="demo")
        _run_full_chain(
            engine,
            cycle_id="cyc-ob",
            instruments=["EURUSD"],
            strategies=[DeterministicTrendStrategy()],
            broker=broker,
            clock=FixedClock(_FIXED_NOW),
        )
        with engine.connect() as conn:
            by_table = {
                r[0]: r[1]
                for r in conn.execute(
                    text(
                        "SELECT table_name, count(*) FROM secondary_sync_outbox"
                        " GROUP BY table_name"
                    )
                ).fetchall()
            }
        # Cycle 6.5 adds orders (1) + order_transactions (2) to the
        # pre-existing strategy/meta/trading_signals mirrors from 6.3/6.4.
        assert by_table.get("strategy_signals") == 1
        assert by_table.get("meta_decisions") == 1
        assert by_table.get("trading_signals") == 1
        assert by_table.get("orders") == 1
        assert by_table.get("order_transactions") == 2
