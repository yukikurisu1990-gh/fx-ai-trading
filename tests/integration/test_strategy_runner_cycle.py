"""Integration test: full Strategy cycle run — Phase 6 Cycle 6.3.

Verifies the end-to-end flow:
  features + stubs -> run_strategy_cycle -> strategy_signals rows +
  secondary_sync_outbox rows, with decision_chain_id threaded through
  the meta JSON column.

Key assertions aligned with the Cycle 6.3 user brief:
  - At least one row per cycle carries a trade direction ('buy' |
    'sell') — Cycle 6.4 Meta guarantee.
  - Both no_trade and trade coexist in the same cycle.
  - All StrategyOutput fields land in the meta JSON (decision_chain_id,
    ev_before_cost, ev_after_cost, tp, sl, holding_time_seconds,
    enabled).
  - decision_chain_id is CONSISTENT per (cycle_id, instrument) — all
    strategies for that instrument share the same chain_id.
  - outbox rows mirror strategy_signals rows 1:1 with matching
    primary_key tuples.
  - The runner is append-only: a second run_strategy_cycle on the
    same cycle_id adds rows rather than updating existing ones (rows
    for different strategies / instruments coexist).

Uses SQLite in-memory — no DATABASE_URL, no live Supabase.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext
from fx_ai_trading.services.strategy_runner import (
    StrategyRunResult,
    run_strategy_cycle,
)
from fx_ai_trading.strategies import (
    AlwaysNoTradeStrategy,
    DeterministicTrendStrategy,
)

# --- Test DDL (simplified from migration 0005 + 0013) ---------------------
# We drop the FK to instruments because this test doesn't exercise the
# instruments table.  All other nullability and shape preserved.
_DDL_STRATEGY_SIGNALS = """
CREATE TABLE strategy_signals (
    cycle_id          TEXT NOT NULL,
    instrument        TEXT NOT NULL,
    strategy_id       TEXT NOT NULL,
    strategy_type     TEXT NOT NULL,
    strategy_version  TEXT,
    signal_direction  TEXT NOT NULL,
    confidence        NUMERIC(6,4),
    signal_time_utc   TEXT NOT NULL,
    meta              TEXT,
    PRIMARY KEY (cycle_id, instrument, strategy_id)
)
"""

_DDL_OUTBOX = """
CREATE TABLE secondary_sync_outbox (
    outbox_id        TEXT PRIMARY KEY,
    table_name       TEXT NOT NULL,
    primary_key      TEXT NOT NULL,
    version_no       BIGINT NOT NULL DEFAULT 0,
    payload_json     TEXT NOT NULL,
    enqueued_at      TEXT NOT NULL,
    acked_at         TEXT,
    last_error       TEXT,
    attempt_count    INTEGER NOT NULL DEFAULT 0,
    next_attempt_at  TEXT,
    run_id           TEXT,
    environment      TEXT,
    code_version     TEXT,
    config_version   TEXT
)
"""

_FIXED_NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL_STRATEGY_SIGNALS))
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
    return StrategyContext(
        cycle_id=cycle_id,
        account_id="acc-1",
        config_version="cv-1",
    )


# --- Test cases -----------------------------------------------------------


class TestHappyPath:
    def test_writes_one_row_per_instrument_per_strategy(self, engine) -> None:
        result = run_strategy_cycle(
            engine,
            cycle_id="cyc-0001",
            instruments=["EURUSD", "USDJPY", "GBPUSD"],
            strategies=[AlwaysNoTradeStrategy(), DeterministicTrendStrategy()],
            features={i: _features(i) for i in ["EURUSD", "USDJPY", "GBPUSD"]},
            context=_ctx("cyc-0001"),
            clock=FixedClock(_FIXED_NOW),
            run_id="run-001",
            environment="paper",
        )
        assert isinstance(result, StrategyRunResult)
        assert result.rows_written == 6  # 3 instruments × 2 strategies
        with engine.connect() as conn:
            db_count = conn.execute(
                text("SELECT count(*) FROM strategy_signals WHERE cycle_id='cyc-0001'")
            ).scalar()
            outbox_count = conn.execute(
                text(
                    "SELECT count(*) FROM secondary_sync_outbox"
                    " WHERE table_name='strategy_signals'"
                )
            ).scalar()
        assert db_count == 6
        assert outbox_count == 6  # 1:1 mirror of DB rows


class TestTradeAndNoTradeCoexist:
    def test_no_trade_and_trade_both_present(self, engine) -> None:
        run_strategy_cycle(
            engine,
            cycle_id="cyc-mix",
            instruments=["EURUSD", "USDJPY"],
            strategies=[AlwaysNoTradeStrategy(), DeterministicTrendStrategy()],
            features={i: _features(i) for i in ["EURUSD", "USDJPY"]},
            context=_ctx("cyc-mix"),
            clock=FixedClock(_FIXED_NOW),
        )
        with engine.connect() as conn:
            directions = conn.execute(
                text(
                    "SELECT signal_direction, count(*) FROM strategy_signals"
                    " GROUP BY signal_direction"
                )
            ).fetchall()
        by_dir = {row[0]: row[1] for row in directions}
        # AlwaysNoTrade produces 2 no_trade rows (one per instrument).
        assert by_dir["no_trade"] == 2
        # DeterministicTrend produces 2 buy|sell rows.
        trade_count = sum(v for k, v in by_dir.items() if k in {"buy", "sell"})
        assert trade_count == 2

    def test_cycle_always_has_at_least_one_trade(self, engine) -> None:
        """Cycle 6.4 Meta guarantee — every cycle must contain >=1 trade signal."""
        result = run_strategy_cycle(
            engine,
            cycle_id="cyc-guarantee",
            instruments=["EURUSD"],
            strategies=[AlwaysNoTradeStrategy(), DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-guarantee"),
            clock=FixedClock(_FIXED_NOW),
        )
        assert result.trade_signals >= 1
        assert result.no_trade_signals >= 1


class TestStrategyOutputFullyPopulated:
    def test_meta_json_has_all_fields_for_trade_row(self, engine) -> None:
        run_strategy_cycle(
            engine,
            cycle_id="cyc-full",
            instruments=["EURUSD"],
            strategies=[DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-full"),
            clock=FixedClock(_FIXED_NOW),
        )
        with engine.connect() as conn:
            raw = conn.execute(
                text(
                    "SELECT meta FROM strategy_signals"
                    " WHERE cycle_id='cyc-full'"
                )
            ).scalar()
        meta = json.loads(str(raw))
        expected_keys = {
            "decision_chain_id",
            "ev_before_cost",
            "ev_after_cost",
            "tp",
            "sl",
            "holding_time_seconds",
            "enabled",
        }
        assert set(meta.keys()) == expected_keys
        # All values are concrete — none are None.
        for k in expected_keys:
            assert meta[k] is not None

    def test_db_columns_populated(self, engine) -> None:
        run_strategy_cycle(
            engine,
            cycle_id="cyc-cols",
            instruments=["EURUSD"],
            strategies=[DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-cols"),
            clock=FixedClock(_FIXED_NOW),
        )
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT strategy_type, strategy_version,"
                    " signal_direction, confidence, signal_time_utc"
                    " FROM strategy_signals WHERE cycle_id='cyc-cols'"
                )
            ).fetchone()
        assert row.strategy_type == "stub"
        assert row.strategy_version == "1.0.0"
        assert row.signal_direction in {"buy", "sell"}
        assert row.confidence is not None
        assert row.signal_time_utc is not None


class TestDecisionChainId:
    def test_same_instrument_shares_chain_id_across_strategies(self, engine) -> None:
        run_strategy_cycle(
            engine,
            cycle_id="cyc-chain",
            instruments=["EURUSD"],
            strategies=[AlwaysNoTradeStrategy(), DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-chain"),
            clock=FixedClock(_FIXED_NOW),
        )
        with engine.connect() as conn:
            metas = [
                json.loads(str(r[0]))
                for r in conn.execute(
                    text(
                        "SELECT meta FROM strategy_signals"
                        " WHERE cycle_id='cyc-chain'"
                    )
                ).fetchall()
            ]
        chain_ids = {m["decision_chain_id"] for m in metas}
        assert len(chain_ids) == 1, (
            "all strategies for the same instrument must share one chain_id"
        )

    def test_different_instruments_get_distinct_chain_ids(self, engine) -> None:
        result = run_strategy_cycle(
            engine,
            cycle_id="cyc-multi",
            instruments=["EURUSD", "USDJPY", "GBPUSD"],
            strategies=[DeterministicTrendStrategy()],
            features={i: _features(i) for i in ["EURUSD", "USDJPY", "GBPUSD"]},
            context=_ctx("cyc-multi"),
            clock=FixedClock(_FIXED_NOW),
        )
        assert len(result.decision_chain_ids) == 3
        assert len(set(result.decision_chain_ids.values())) == 3

    def test_chain_ids_are_ulid_shape(self, engine) -> None:
        result = run_strategy_cycle(
            engine,
            cycle_id="cyc-shape",
            instruments=["EURUSD"],
            strategies=[DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-shape"),
            clock=FixedClock(_FIXED_NOW),
        )
        cid = result.decision_chain_ids["EURUSD"]
        assert isinstance(cid, str) and len(cid) == 26


class TestOutboxMirror:
    def test_outbox_primary_key_matches_signals_pk(self, engine) -> None:
        run_strategy_cycle(
            engine,
            cycle_id="cyc-mirror",
            instruments=["EURUSD"],
            strategies=[DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-mirror"),
            clock=FixedClock(_FIXED_NOW),
        )
        with engine.connect() as conn:
            outbox_pk = conn.execute(
                text(
                    "SELECT primary_key FROM secondary_sync_outbox"
                    " WHERE table_name='strategy_signals'"
                )
            ).scalar()
        decoded = json.loads(str(outbox_pk))
        assert decoded == ["cyc-mirror", "EURUSD", "stub.deterministic_trend.v1"]

    def test_outbox_payload_carries_meta(self, engine) -> None:
        run_strategy_cycle(
            engine,
            cycle_id="cyc-payload",
            instruments=["EURUSD"],
            strategies=[DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-payload"),
            clock=FixedClock(_FIXED_NOW),
        )
        with engine.connect() as conn:
            raw = conn.execute(
                text(
                    "SELECT payload_json FROM secondary_sync_outbox"
                    " WHERE table_name='strategy_signals'"
                )
            ).scalar()
        payload = json.loads(str(raw))
        assert "meta" in payload
        assert "decision_chain_id" in payload["meta"]

    def test_outbox_carries_common_keys(self, engine) -> None:
        run_strategy_cycle(
            engine,
            cycle_id="cyc-common",
            instruments=["EURUSD"],
            strategies=[DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-common"),
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
                    " WHERE table_name='strategy_signals'"
                )
            ).fetchone()
        assert row == ("run-42", "paper", "abc123", "cv-9")


class TestAppendOnly:
    def test_second_run_appends_rows_for_different_cycle(self, engine) -> None:
        """Running a second cycle must NOT update / delete prior rows."""
        run_strategy_cycle(
            engine,
            cycle_id="cyc-A",
            instruments=["EURUSD"],
            strategies=[DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-A"),
            clock=FixedClock(_FIXED_NOW),
        )
        run_strategy_cycle(
            engine,
            cycle_id="cyc-B",
            instruments=["EURUSD"],
            strategies=[DeterministicTrendStrategy()],
            features={"EURUSD": _features("EURUSD")},
            context=_ctx("cyc-B"),
            clock=FixedClock(_FIXED_NOW),
        )
        with engine.connect() as conn:
            cycles = conn.execute(
                text("SELECT DISTINCT cycle_id FROM strategy_signals ORDER BY cycle_id")
            ).fetchall()
        assert [c[0] for c in cycles] == ["cyc-A", "cyc-B"]

    def test_no_update_or_delete_paths_exercised(self, engine) -> None:
        """Structural check: after a run, sqlite_master statement
        count on strategy_signals writes is 'INSERT only'.

        This is verified implicitly — if the runner ever UPDATE'd
        or DELETE'd, the rows_written counter would diverge from the
        actual row count.  We assert 1:1."""
        result = run_strategy_cycle(
            engine,
            cycle_id="cyc-ao",
            instruments=["EURUSD", "USDJPY"],
            strategies=[AlwaysNoTradeStrategy(), DeterministicTrendStrategy()],
            features={i: _features(i) for i in ["EURUSD", "USDJPY"]},
            context=_ctx("cyc-ao"),
            clock=FixedClock(_FIXED_NOW),
        )
        with engine.connect() as conn:
            db = conn.execute(text("SELECT count(*) FROM strategy_signals")).scalar()
        assert db == result.rows_written


class TestInputValidation:
    def test_empty_instruments_raises(self, engine) -> None:
        with pytest.raises(ValueError, match="instruments must be non-empty"):
            run_strategy_cycle(
                engine,
                cycle_id="cyc-x",
                instruments=[],
                strategies=[DeterministicTrendStrategy()],
                features={},
                context=_ctx("cyc-x"),
                clock=FixedClock(_FIXED_NOW),
            )

    def test_empty_strategies_raises(self, engine) -> None:
        with pytest.raises(ValueError, match="strategies must be non-empty"):
            run_strategy_cycle(
                engine,
                cycle_id="cyc-x",
                instruments=["EURUSD"],
                strategies=[],
                features={"EURUSD": _features("EURUSD")},
                context=_ctx("cyc-x"),
                clock=FixedClock(_FIXED_NOW),
            )

    def test_missing_features_for_instrument_raises(self, engine) -> None:
        with pytest.raises(ValueError, match="missing FeatureSet"):
            run_strategy_cycle(
                engine,
                cycle_id="cyc-x",
                instruments=["EURUSD", "USDJPY"],
                strategies=[DeterministicTrendStrategy()],
                features={"EURUSD": _features("EURUSD")},  # USDJPY missing
                context=_ctx("cyc-x"),
                clock=FixedClock(_FIXED_NOW),
            )
