"""End-to-end integration: Strategy cycle → Meta cycle — Phase 6 Cycle 6.4.

Chains run_strategy_cycle and run_meta_cycle in one SQLite in-memory
process, then asserts the Cycle 6.4 guarantee end to end: with the
supplied stubs, exactly one trading_signals row lands per cycle.

Covered flows:
  1. Golden path — 2 stubs × 2 instruments, ≥1 trading_signal.
  2. Only AlwaysNoTradeStrategy present → meta emits NO_CANDIDATES
     no_trade_events row, no trading_signal.
  3. decision_chain_id round-trip: strategy_signals.meta → meta_decisions
     active_strategies JSON → trading_signals.correlation_id (for the
     adopted candidate).
  4. Outbox mirror: every persisted row has a 1:1 secondary_sync_outbox
     counterpart.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext
from fx_ai_trading.services.meta_cycle_runner import run_meta_cycle
from fx_ai_trading.services.strategy_runner import run_strategy_cycle
from fx_ai_trading.strategies import (
    AlwaysNoTradeStrategy,
    DeterministicTrendStrategy,
)

_FIXED_NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)


# --- DDL ------------------------------------------------------------------

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


# --- Golden path: stubs → strategy → meta produces >=1 trading_signal ----


class TestGoldenPath:
    def test_one_trading_signal_per_cycle_with_stubs(self, engine) -> None:
        strat_result = run_strategy_cycle(
            engine,
            cycle_id="cyc-gold",
            instruments=["EURUSD", "USDJPY"],
            strategies=[AlwaysNoTradeStrategy(), DeterministicTrendStrategy()],
            features={i: _features(i) for i in ["EURUSD", "USDJPY"]},
            context=_ctx("cyc-gold"),
            clock=FixedClock(_FIXED_NOW),
        )
        assert strat_result.trade_signals >= 1

        meta_result = run_meta_cycle(engine, cycle_id="cyc-gold", clock=FixedClock(_FIXED_NOW))

        # Cycle 6.4 guarantee — exactly one trading_signal row per cycle.
        assert meta_result.adopted is True
        assert meta_result.trading_signal_id is not None
        assert meta_result.fallback_used is False  # stub passes default thresholds

        with engine.connect() as conn:
            trading_row_count = conn.execute(
                text("SELECT count(*) FROM trading_signals WHERE cycle_id='cyc-gold'")
            ).scalar()
            meta_row_count = conn.execute(
                text("SELECT count(*) FROM meta_decisions WHERE cycle_id='cyc-gold'")
            ).scalar()
        assert trading_row_count == 1
        assert meta_row_count == 1

    def test_adopted_strategy_is_from_non_no_trade_stub(self, engine) -> None:
        run_strategy_cycle(
            engine,
            cycle_id="cyc-from",
            instruments=["EURUSD"],
            strategies=[AlwaysNoTradeStrategy(), DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-from"),
            clock=FixedClock(_FIXED_NOW),
        )
        r = run_meta_cycle(engine, cycle_id="cyc-from", clock=FixedClock(_FIXED_NOW))
        assert r.adopted_strategy_id == "stub.deterministic_trend.v1"

    def test_trading_signal_fk_resolves_to_meta_decision(self, engine) -> None:
        """trading_signals.meta_decision_id must point at the single
        meta_decisions row for the cycle — the FK in the real PG schema."""
        run_strategy_cycle(
            engine,
            cycle_id="cyc-fk",
            instruments=["EURUSD"],
            strategies=[DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-fk"),
            clock=FixedClock(_FIXED_NOW),
        )
        run_meta_cycle(engine, cycle_id="cyc-fk", clock=FixedClock(_FIXED_NOW))
        with engine.connect() as conn:
            ts_md_id = conn.execute(
                text("SELECT meta_decision_id FROM trading_signals WHERE cycle_id='cyc-fk'")
            ).scalar()
            md_id = conn.execute(
                text("SELECT meta_decision_id FROM meta_decisions WHERE cycle_id='cyc-fk'")
            ).scalar()
        assert ts_md_id == md_id


# --- Only AlwaysNoTradeStrategy → NO_CANDIDATES --------------------------


class TestOnlyNoTradeStubs:
    def test_only_no_trade_stub_produces_no_candidates_event(self, engine) -> None:
        run_strategy_cycle(
            engine,
            cycle_id="cyc-all-nt",
            instruments=["EURUSD", "USDJPY"],
            strategies=[AlwaysNoTradeStrategy()],
            features={i: _features(i) for i in ["EURUSD", "USDJPY"]},
            context=_ctx("cyc-all-nt"),
            clock=FixedClock(_FIXED_NOW),
        )
        r = run_meta_cycle(engine, cycle_id="cyc-all-nt", clock=FixedClock(_FIXED_NOW))
        assert r.adopted is False
        assert r.trading_signal_id is None
        assert r.candidate_count == 2  # both no_trade rows loaded
        assert r.trade_candidate_count == 0

        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT reason_code FROM no_trade_events WHERE cycle_id='cyc-all-nt'")
            ).fetchone()
        assert row is not None and row.reason_code == "NO_CANDIDATES"

        with engine.connect() as conn:
            ts = conn.execute(
                text("SELECT count(*) FROM trading_signals WHERE cycle_id='cyc-all-nt'")
            ).scalar()
        assert ts == 0


# --- decision_chain_id round-trip ----------------------------------------


class TestDecisionChainIdRoundTrip:
    def test_trading_signal_correlation_id_matches_strategy_chain(self, engine) -> None:
        run_strategy_cycle(
            engine,
            cycle_id="cyc-chain",
            instruments=["EURUSD"],
            strategies=[DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-chain"),
            clock=FixedClock(_FIXED_NOW),
        )
        with engine.connect() as conn:
            raw_meta = conn.execute(
                text("SELECT meta FROM strategy_signals WHERE cycle_id='cyc-chain'")
            ).scalar()
        strategy_chain_id = json.loads(str(raw_meta))["decision_chain_id"]

        run_meta_cycle(engine, cycle_id="cyc-chain", clock=FixedClock(_FIXED_NOW))
        with engine.connect() as conn:
            trading_corr = conn.execute(
                text("SELECT correlation_id FROM trading_signals WHERE cycle_id='cyc-chain'")
            ).scalar()
        assert trading_corr == strategy_chain_id


# --- Outbox mirror across 3 domains --------------------------------------


class TestOutboxMirror:
    def test_each_persisted_row_mirrored_to_outbox(self, engine) -> None:
        run_strategy_cycle(
            engine,
            cycle_id="cyc-ob",
            instruments=["EURUSD"],
            strategies=[AlwaysNoTradeStrategy(), DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-ob"),
            clock=FixedClock(_FIXED_NOW),
        )
        run_meta_cycle(engine, cycle_id="cyc-ob", clock=FixedClock(_FIXED_NOW))

        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT table_name, count(*) FROM secondary_sync_outbox"
                    " GROUP BY table_name ORDER BY table_name"
                )
            ).fetchall()
        by_table = {r[0]: r[1] for r in rows}
        # 2 strategy_signals rows + 1 meta_decisions + 1 trading_signals
        # (no no_trade_events because default thresholds are permissive
        #  and DeterministicTrend passes cleanly).
        assert by_table["strategy_signals"] == 2
        assert by_table["meta_decisions"] == 1
        assert by_table["trading_signals"] == 1
        assert "no_trade_events" not in by_table

    def test_common_keys_propagate_on_meta_outbox_rows(self, engine) -> None:
        run_strategy_cycle(
            engine,
            cycle_id="cyc-common",
            instruments=["EURUSD"],
            strategies=[DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-common"),
            clock=FixedClock(_FIXED_NOW),
        )
        run_meta_cycle(
            engine,
            cycle_id="cyc-common",
            clock=FixedClock(_FIXED_NOW),
            run_id="run-42",
            environment="paper",
            code_version="abc123",
            config_version="cv-9",
        )
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT run_id, environment, code_version, config_version"
                    " FROM secondary_sync_outbox"
                    " WHERE table_name='trading_signals'"
                )
            ).fetchone()
        assert row == ("run-42", "paper", "abc123", "cv-9")


# --- Append-only across two chained cycles -------------------------------


class TestAppendOnlyAcrossCycles:
    def test_two_cycles_produce_two_trading_signals(self, engine) -> None:
        for c in ["cyc-1", "cyc-2"]:
            run_strategy_cycle(
                engine,
                cycle_id=c,
                instruments=["EURUSD"],
                strategies=[DeterministicTrendStrategy()],
                features={"EURUSD": _features("EURUSD")},
                context=_ctx(c),
                clock=FixedClock(_FIXED_NOW),
            )
            run_meta_cycle(engine, cycle_id=c, clock=FixedClock(_FIXED_NOW))
        with engine.connect() as conn:
            count = conn.execute(text("SELECT count(*) FROM trading_signals")).scalar()
        assert count == 2
