"""Unit tests for run_meta_cycle — Phase 6 Cycle 6.4.

Covers in isolation:
  - Input validation (empty cycle_id; no strategy_signals rows).
  - F-16 sort order (ev_after_cost DESC, confidence DESC, spread ASC,
    strategy_id ASC).
  - Filter rejects (EV below threshold, confidence below threshold).
  - Forced fallback: every candidate filtered but one trade candidate
    exists → adopt top-EV, mark fallback.
  - Genuine no_trade: no trade candidates at all → NO_CANDIDATES row.
  - no_trade_events taxonomy: filter rejections carry source_component
    and meta_decision_id; whole-cycle NO_CANDIDATES has instrument/
    strategy_id = NULL.
  - Append-only invariant: rerun on a distinct cycle keeps prior rows.

These tests seed strategy_signals rows directly (bypassing
run_strategy_cycle) so the Meta service is tested against a controlled
candidate mix.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.services.meta_cycle_runner import (
    MetaCycleConfig,
    MetaCycleRunResult,
    run_meta_cycle,
)

_FIXED_NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)

# --- Test DDL (SQLite-safe subset of migrations 0005/0006/0007/0013) -------

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


# --- Helpers ---------------------------------------------------------------


def _seed_strategy_signal(
    engine,
    *,
    cycle_id: str,
    instrument: str,
    strategy_id: str,
    direction: str,
    confidence: float = 0.7,
    ev_after_cost: float = 12.0,
    ev_before_cost: float = 15.0,
    spread: float = 0.0,
    decision_chain_id: str | None = "chain-test",
    strategy_type: str = "stub",
    strategy_version: str = "1.0.0",
) -> None:
    meta = {
        "decision_chain_id": decision_chain_id,
        "ev_before_cost": ev_before_cost,
        "ev_after_cost": ev_after_cost,
        "spread": spread,
        "tp": 20.0,
        "sl": 10.0,
        "holding_time_seconds": 3600,
        "enabled": True,
    }
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO strategy_signals (
                    cycle_id, instrument, strategy_id, strategy_type,
                    strategy_version, signal_direction, confidence,
                    signal_time_utc, meta
                ) VALUES (
                    :cycle_id, :instrument, :strategy_id, :strategy_type,
                    :strategy_version, :direction, :confidence,
                    :signal_time_utc, :meta
                )
                """
            ),
            {
                "cycle_id": cycle_id,
                "instrument": instrument,
                "strategy_id": strategy_id,
                "strategy_type": strategy_type,
                "strategy_version": strategy_version,
                "direction": direction,
                "confidence": confidence,
                "signal_time_utc": _FIXED_NOW.isoformat(),
                "meta": json.dumps(meta),
            },
        )


def _count(engine, table: str, where: str = "1=1") -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT count(*) FROM {table} WHERE {where}")).scalar()


# --- Input validation ------------------------------------------------------


class TestInputValidation:
    def test_empty_cycle_id_raises(self, engine) -> None:
        with pytest.raises(ValueError, match="cycle_id must be non-empty"):
            run_meta_cycle(engine, cycle_id="", clock=FixedClock(_FIXED_NOW))

    def test_whitespace_cycle_id_raises(self, engine) -> None:
        with pytest.raises(ValueError, match="cycle_id must be non-empty"):
            run_meta_cycle(engine, cycle_id="   ", clock=FixedClock(_FIXED_NOW))

    def test_no_strategy_signals_raises(self, engine) -> None:
        with pytest.raises(ValueError, match="no strategy_signals rows found"):
            run_meta_cycle(engine, cycle_id="cyc-empty", clock=FixedClock(_FIXED_NOW))


# --- F-16 sort order -------------------------------------------------------


class TestF16SortOrder:
    def test_primary_sort_is_ev_after_cost_desc(self, engine) -> None:
        _seed_strategy_signal(
            engine, cycle_id="cyc-sort1", instrument="EURUSD",
            strategy_id="s-low", direction="buy", ev_after_cost=5.0, confidence=0.9,
        )
        _seed_strategy_signal(
            engine, cycle_id="cyc-sort1", instrument="USDJPY",
            strategy_id="s-high", direction="buy", ev_after_cost=20.0, confidence=0.6,
        )
        r = run_meta_cycle(engine, cycle_id="cyc-sort1", clock=FixedClock(_FIXED_NOW))
        assert r.adopted is True
        assert r.adopted_strategy_id == "s-high"  # higher ev_after_cost wins

    def test_secondary_sort_is_confidence_desc(self, engine) -> None:
        _seed_strategy_signal(
            engine, cycle_id="cyc-sort2", instrument="EURUSD",
            strategy_id="s-a", direction="buy", ev_after_cost=10.0, confidence=0.5,
        )
        _seed_strategy_signal(
            engine, cycle_id="cyc-sort2", instrument="USDJPY",
            strategy_id="s-b", direction="buy", ev_after_cost=10.0, confidence=0.9,
        )
        r = run_meta_cycle(engine, cycle_id="cyc-sort2", clock=FixedClock(_FIXED_NOW))
        assert r.adopted_strategy_id == "s-b"  # tie on EV, higher confidence wins

    def test_tertiary_sort_is_spread_asc(self, engine) -> None:
        _seed_strategy_signal(
            engine, cycle_id="cyc-sort3", instrument="EURUSD",
            strategy_id="s-wide", direction="buy", ev_after_cost=10.0,
            confidence=0.7, spread=3.0,
        )
        _seed_strategy_signal(
            engine, cycle_id="cyc-sort3", instrument="USDJPY",
            strategy_id="s-tight", direction="buy", ev_after_cost=10.0,
            confidence=0.7, spread=0.5,
        )
        r = run_meta_cycle(engine, cycle_id="cyc-sort3", clock=FixedClock(_FIXED_NOW))
        assert r.adopted_strategy_id == "s-tight"  # tighter spread wins

    def test_quaternary_sort_strategy_id_asc(self, engine) -> None:
        """All other keys tied — strategy_id alphabetical tiebreak."""
        _seed_strategy_signal(
            engine, cycle_id="cyc-sort4", instrument="EURUSD",
            strategy_id="s-zeta", direction="buy", ev_after_cost=10.0,
            confidence=0.7, spread=1.0,
        )
        _seed_strategy_signal(
            engine, cycle_id="cyc-sort4", instrument="USDJPY",
            strategy_id="s-alpha", direction="buy", ev_after_cost=10.0,
            confidence=0.7, spread=1.0,
        )
        r = run_meta_cycle(engine, cycle_id="cyc-sort4", clock=FixedClock(_FIXED_NOW))
        assert r.adopted_strategy_id == "s-alpha"


# --- Filter / threshold ---------------------------------------------------


class TestFilterThresholds:
    def test_ev_below_threshold_filters(self, engine) -> None:
        _seed_strategy_signal(
            engine, cycle_id="cyc-evf", instrument="EURUSD",
            strategy_id="s-low-ev", direction="buy", ev_after_cost=-2.0,
            confidence=0.8,
        )
        _seed_strategy_signal(
            engine, cycle_id="cyc-evf", instrument="USDJPY",
            strategy_id="s-ok-ev", direction="buy", ev_after_cost=5.0,
            confidence=0.8,
        )
        # min_ev_after_cost=0.0 → low_ev candidate rejected.
        r = run_meta_cycle(
            engine,
            cycle_id="cyc-evf",
            clock=FixedClock(_FIXED_NOW),
            config=MetaCycleConfig(min_ev_after_cost=0.0),
        )
        assert r.adopted_strategy_id == "s-ok-ev"
        assert r.filtered_count == 1
        # One rejection → one no_trade_events row.
        assert _count(engine, "no_trade_events", "cycle_id='cyc-evf'") == 1

    def test_confidence_below_threshold_filters(self, engine) -> None:
        _seed_strategy_signal(
            engine, cycle_id="cyc-cf", instrument="EURUSD",
            strategy_id="s-low-conf", direction="buy", ev_after_cost=20.0,
            confidence=0.3,
        )
        _seed_strategy_signal(
            engine, cycle_id="cyc-cf", instrument="USDJPY",
            strategy_id="s-ok-conf", direction="buy", ev_after_cost=5.0,
            confidence=0.6,
        )
        r = run_meta_cycle(
            engine,
            cycle_id="cyc-cf",
            clock=FixedClock(_FIXED_NOW),
            config=MetaCycleConfig(min_ev_after_cost=0.0, confidence_threshold=0.5),
        )
        assert r.adopted_strategy_id == "s-ok-conf"

    def test_stub_deterministic_trend_passes_default_thresholds(self, engine) -> None:
        """Cycle 6.4 guarantee: with stub numbers, default config must
        adopt.  Defaults are min_ev_after_cost=0.0, confidence_threshold=0.0."""
        _seed_strategy_signal(
            engine, cycle_id="cyc-stub", instrument="EURUSD",
            strategy_id="stub.deterministic_trend.v1", direction="buy",
            ev_after_cost=12.0, confidence=0.70,
        )
        r = run_meta_cycle(engine, cycle_id="cyc-stub", clock=FixedClock(_FIXED_NOW))
        assert r.adopted is True
        assert r.fallback_used is False


# --- Forced fallback ------------------------------------------------------


class TestForcedFallback:
    def test_fallback_adopts_when_all_filtered(self, engine) -> None:
        _seed_strategy_signal(
            engine, cycle_id="cyc-fb", instrument="EURUSD",
            strategy_id="s-1", direction="buy", ev_after_cost=-1.0,
            confidence=0.6,
        )
        _seed_strategy_signal(
            engine, cycle_id="cyc-fb", instrument="USDJPY",
            strategy_id="s-2", direction="sell", ev_after_cost=-5.0,
            confidence=0.9,
        )
        r = run_meta_cycle(
            engine,
            cycle_id="cyc-fb",
            clock=FixedClock(_FIXED_NOW),
            config=MetaCycleConfig(min_ev_after_cost=0.0, force_fallback=True),
        )
        # All candidates filtered but fallback adopts the top-EV one (s-1
        # with ev_after_cost=-1.0 beats s-2 at -5.0).
        assert r.adopted is True
        assert r.fallback_used is True
        assert r.adopted_strategy_id == "s-1"

    def test_fallback_disabled_emits_no_trade(self, engine) -> None:
        _seed_strategy_signal(
            engine, cycle_id="cyc-nofb", instrument="EURUSD",
            strategy_id="s-only", direction="buy", ev_after_cost=-1.0,
            confidence=0.6,
        )
        r = run_meta_cycle(
            engine,
            cycle_id="cyc-nofb",
            clock=FixedClock(_FIXED_NOW),
            config=MetaCycleConfig(min_ev_after_cost=0.0, force_fallback=False),
        )
        assert r.adopted is False
        assert r.trading_signal_id is None
        # meta_decisions.no_trade_reason is set.
        with engine.connect() as conn:
            reason = conn.execute(
                text("SELECT no_trade_reason FROM meta_decisions WHERE cycle_id='cyc-nofb'")
            ).scalar()
        assert reason == "EV_BELOW_THRESHOLD"


# --- Genuine no_trade -----------------------------------------------------


class TestGenuineNoTrade:
    def test_all_no_trade_input_produces_no_candidates_event(self, engine) -> None:
        _seed_strategy_signal(
            engine, cycle_id="cyc-nt", instrument="EURUSD",
            strategy_id="s-nt", direction="no_trade", ev_after_cost=0.0,
            confidence=0.0,
        )
        r = run_meta_cycle(engine, cycle_id="cyc-nt", clock=FixedClock(_FIXED_NOW))
        assert r.adopted is False
        assert r.trade_candidate_count == 0
        assert r.no_trade_event_count == 1  # single NO_CANDIDATES row

        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT reason_code, instrument, strategy_id, source_component"
                    " FROM no_trade_events WHERE cycle_id='cyc-nt'"
                )
            ).fetchone()
        assert row.reason_code == "NO_CANDIDATES"
        assert row.instrument is None
        assert row.strategy_id is None
        assert row.source_component == "meta_cycle_runner"


# --- Persistence shape ----------------------------------------------------


class TestPersistenceShape:
    def test_meta_decisions_row_written_every_cycle(self, engine) -> None:
        _seed_strategy_signal(
            engine, cycle_id="cyc-md", instrument="EURUSD",
            strategy_id="s-a", direction="buy",
        )
        run_meta_cycle(engine, cycle_id="cyc-md", clock=FixedClock(_FIXED_NOW))
        assert _count(engine, "meta_decisions", "cycle_id='cyc-md'") == 1

    def test_trading_signals_carries_correlation_id(self, engine) -> None:
        """decision_chain_id from strategy_signals.meta threads through to
        trading_signals.correlation_id — the stable identifier for the
        Strategy → Meta → Execution chain."""
        _seed_strategy_signal(
            engine, cycle_id="cyc-corr", instrument="EURUSD",
            strategy_id="s-a", direction="buy",
            decision_chain_id="chain-XYZ-123",
        )
        r = run_meta_cycle(engine, cycle_id="cyc-corr", clock=FixedClock(_FIXED_NOW))
        assert r.adopted is True
        with engine.connect() as conn:
            corr = conn.execute(
                text(
                    "SELECT correlation_id FROM trading_signals WHERE cycle_id='cyc-corr'"
                )
            ).scalar()
        assert corr == "chain-XYZ-123"

    def test_trading_signals_direction_is_buy_or_sell(self, engine) -> None:
        _seed_strategy_signal(
            engine, cycle_id="cyc-dir", instrument="EURUSD",
            strategy_id="s-a", direction="sell",
        )
        run_meta_cycle(engine, cycle_id="cyc-dir", clock=FixedClock(_FIXED_NOW))
        with engine.connect() as conn:
            d = conn.execute(
                text("SELECT signal_direction FROM trading_signals WHERE cycle_id='cyc-dir'")
            ).scalar()
        assert d == "sell"

    def test_outbox_rows_mirror_persisted_rows(self, engine) -> None:
        _seed_strategy_signal(
            engine, cycle_id="cyc-ob", instrument="EURUSD",
            strategy_id="s-a", direction="buy", ev_after_cost=-5.0,
        )
        _seed_strategy_signal(
            engine, cycle_id="cyc-ob", instrument="USDJPY",
            strategy_id="s-b", direction="buy", ev_after_cost=10.0,
        )
        # With default config, s-a is filtered (ev < 0), s-b adopted.
        r = run_meta_cycle(engine, cycle_id="cyc-ob", clock=FixedClock(_FIXED_NOW))
        assert r.adopted is True
        assert r.filtered_count == 1
        # Expected outbox rows: 1 meta_decisions + 1 trading_signals + 1 no_trade_events
        with engine.connect() as conn:
            tables = conn.execute(
                text(
                    "SELECT table_name, count(*) FROM secondary_sync_outbox"
                    " GROUP BY table_name ORDER BY table_name"
                )
            ).fetchall()
        by_table = {row[0]: row[1] for row in tables}
        assert by_table == {
            "meta_decisions": 1,
            "no_trade_events": 1,
            "trading_signals": 1,
        }


# --- Append-only -----------------------------------------------------------


class TestAppendOnly:
    def test_running_a_second_cycle_does_not_overwrite_prior(self, engine) -> None:
        _seed_strategy_signal(
            engine, cycle_id="cyc-A", instrument="EURUSD",
            strategy_id="s-a", direction="buy",
        )
        _seed_strategy_signal(
            engine, cycle_id="cyc-B", instrument="EURUSD",
            strategy_id="s-a", direction="buy",
        )
        run_meta_cycle(engine, cycle_id="cyc-A", clock=FixedClock(_FIXED_NOW))
        run_meta_cycle(engine, cycle_id="cyc-B", clock=FixedClock(_FIXED_NOW))
        with engine.connect() as conn:
            cycles = conn.execute(
                text(
                    "SELECT DISTINCT cycle_id FROM meta_decisions ORDER BY cycle_id"
                )
            ).fetchall()
        assert [c[0] for c in cycles] == ["cyc-A", "cyc-B"]


# --- Return shape ----------------------------------------------------------


class TestReturnShape:
    def test_result_is_meta_cycle_run_result(self, engine) -> None:
        _seed_strategy_signal(
            engine, cycle_id="cyc-r", instrument="EURUSD",
            strategy_id="s-a", direction="buy",
        )
        r = run_meta_cycle(engine, cycle_id="cyc-r", clock=FixedClock(_FIXED_NOW))
        assert isinstance(r, MetaCycleRunResult)
        assert r.cycle_id == "cyc-r"
        assert r.meta_decision_id  # non-empty
        assert r.adopted is True
        assert r.trading_signal_id is not None
        assert r.adopted_direction in {"buy", "sell"}
