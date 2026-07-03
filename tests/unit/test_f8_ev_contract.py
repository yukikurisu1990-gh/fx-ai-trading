"""F8-F / F8-G tests — post-cost EV contract + force_fallback guard.

Covers (docs/design/project_wide_logic_audit_fable5_findings.md §4 F-8 / F-4):

  1. Contract helper math — ``ev_after_cost_pips`` subtracts cost exactly
     once, rejects negative cost; ``is_comparable`` accepts only the
     canonical unit.
  2. Every EV-emitting strategy declares an explicit ``ev_unit`` on its
     StrategySignal — canonical ``pips_post_cost`` for LGBM / MeanReversion /
     Breakout / stubs, honest non-comparable ``price_raw`` for the legacy
     price-unit strategies.
  3. MeanReversion / Breakout EV is in PIPS with an SL term:
     ev = confidence * tp_pips - (1 - confidence) * sl_pips, at the
     instrument pip size (0.01 JPY-quoted, else 0.0001).
  4. Meta fail-closed on incomparable units — candidates without ev_unit
     (legacy rows) or with a non-canonical unit are rejected with
     ``meta.ev_unit_incomparable`` and never ranked against comparable ones.
  5. F8_FORCE_FALLBACK_PRODUCTION_GUARDED — default MetaCycleConfig no
     longer force-adopts when every candidate fails the filters; the
     legacy Cycle 6.4 ≥1-trade guarantee requires force_fallback=True
     explicitly.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.ev_contract import (
    EV_UNIT_PIPS_POST_COST,
    EV_UNIT_PRICE_RAW,
    EV_UNIT_UNKNOWN,
    ev_after_cost_pips,
    is_comparable,
    pip_size,
)
from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.reason_codes import MetaFilterReason
from fx_ai_trading.domain.strategy import StrategyContext, StrategySignal
from fx_ai_trading.services.meta_cycle_runner import MetaCycleConfig, run_meta_cycle
from fx_ai_trading.services.strategies.atr import ATRStrategy
from fx_ai_trading.services.strategies.bollinger import BollingerStrategy
from fx_ai_trading.services.strategies.breakout import BreakoutStrategy
from fx_ai_trading.services.strategies.lgbm_strategy import LGBMStrategy
from fx_ai_trading.services.strategies.ma import MAStrategy
from fx_ai_trading.services.strategies.macd import MACDStrategy
from fx_ai_trading.services.strategies.mean_reversion import MeanReversionStrategy
from fx_ai_trading.services.strategies.rsi import RSIStrategy
from fx_ai_trading.strategies.stubs import (
    AlwaysNoTradeStrategy,
    DeterministicTrendStrategy,
)

_FIXED_NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)

_CTX = StrategyContext(cycle_id=str(uuid4()), account_id="acc001", config_version="v1")


def _make_features(**kwargs: float) -> FeatureSet:
    defaults = {
        "atr_14": 0.001,
        "bb_lower": 1.09,
        "bb_middle": 1.10,
        "bb_pct_b": 0.5,
        "bb_upper": 1.11,
        "bb_width": 0.018,
        "ema_12": 1.10,
        "ema_26": 1.10,
        "last_close": 1.10,
        "macd_histogram": 0.0,
        "macd_line": 0.0,
        "macd_signal": 0.0,
        "rsi_14": 50.0,
        "sma_20": 1.10,
        "sma_50": 1.10,
    }
    defaults.update(kwargs)
    return FeatureSet(
        feature_version="v2",
        feature_hash="test",
        feature_stats=defaults,
        sampled_features=defaults,
        computed_at=_FIXED_NOW,
    )


# ---------------------------------------------------------------------------
# 1. Contract helper math
# ---------------------------------------------------------------------------


class TestContractHelpers:
    def test_subtracts_cost_exactly_once(self) -> None:
        assert ev_after_cost_pips(10.0, 3.0) == pytest.approx(7.0)

    def test_zero_cost_is_identity(self) -> None:
        assert ev_after_cost_pips(12.5, 0.0) == pytest.approx(12.5)

    def test_negative_ev_passes_through(self) -> None:
        assert ev_after_cost_pips(-2.0, 1.0) == pytest.approx(-3.0)

    def test_negative_cost_raises(self) -> None:
        with pytest.raises(ValueError, match="cost_pips must be >= 0.0"):
            ev_after_cost_pips(10.0, -0.5)

    def test_double_subtraction_is_observable(self) -> None:
        # Guard characterisation: applying the helper twice subtracts twice —
        # the contract is that emitters route through it exactly once.
        once = ev_after_cost_pips(10.0, 3.0)
        twice = ev_after_cost_pips(once, 3.0)
        assert twice == pytest.approx(4.0)
        assert once != twice

    def test_is_comparable_only_for_canonical_unit(self) -> None:
        assert is_comparable(EV_UNIT_PIPS_POST_COST) is True
        assert is_comparable(EV_UNIT_PRICE_RAW) is False
        assert is_comparable(EV_UNIT_UNKNOWN) is False
        assert is_comparable("") is False

    def test_pip_size_convention(self) -> None:
        assert pip_size("USD_JPY") == pytest.approx(0.01)
        assert pip_size("EUR_USD") == pytest.approx(0.0001)


# ---------------------------------------------------------------------------
# 2./3. Strategy ev_unit declarations + pips math
# ---------------------------------------------------------------------------


class _FakeProbaModel:
    """Stand-in for LGBMClassifier: fixed [p_short, p_neutral, p_long]."""

    def __init__(self, proba: list[float]) -> None:
        self._proba = proba

    def predict_proba(self, x):  # noqa: ANN001, ANN201 - sklearn-shaped stub
        return np.array([self._proba])


def _make_lgbm(proba: list[float]) -> LGBMStrategy:
    strategy = object.__new__(LGBMStrategy)
    strategy._feature_cols = ["atr_14", "rsi_14"]
    strategy._tp_mult = 1.5
    strategy._sl_mult = 1.0
    strategy._threshold = 0.40
    strategy._strategy_id = "lgbm"
    strategy._models = {"USD_JPY": _FakeProbaModel(proba)}
    return strategy


class TestStrategyEvUnitDeclarations:
    def test_lgbm_trade_signal_is_pips_post_cost(self) -> None:
        strategy = _make_lgbm([0.1, 0.2, 0.7])  # p_long=0.7 → long
        sig = strategy.evaluate("USD_JPY", _make_features(atr_14=0.5), _CTX)
        assert sig.signal == "long"
        assert sig.ev_unit == EV_UNIT_PIPS_POST_COST
        # B-2 labels embed the spread → cost_pips=0.0 → after == before.
        assert sig.ev_after_cost == sig.ev_before_cost

    def test_lgbm_no_model_path_is_pips_post_cost(self) -> None:
        strategy = _make_lgbm([0.1, 0.2, 0.7])
        sig = strategy.evaluate("EUR_USD", _make_features(), _CTX)  # no model
        assert sig.signal == "no_trade"
        assert sig.ev_unit == EV_UNIT_PIPS_POST_COST

    def test_mean_reversion_ev_is_pips_with_sl_term(self) -> None:
        # rsi=15 → rsi_conf 0.5; bb_pct_b=0.05 → bb_conf 0.5 → confidence 0.5
        mr = MeanReversionStrategy("mr_1", tp_atr_multiplier=1.5, sl_atr_multiplier=1.0)
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=15.0, bb_pct_b=0.05, atr_14=0.001), _CTX)
        assert sig.signal == "long"
        assert sig.ev_unit == EV_UNIT_PIPS_POST_COST
        tp_pips = 0.001 * 1.5 / 0.0001  # 15 pips
        sl_pips = 0.001 * 1.0 / 0.0001  # 10 pips
        expected = 0.5 * tp_pips - 0.5 * sl_pips  # 2.5 pips
        assert sig.ev_before_cost == pytest.approx(expected, abs=1e-3)
        assert sig.ev_after_cost == pytest.approx(expected, abs=1e-3)  # cost_pips=0.0
        # tp/sl DTO fields stay in price units (unchanged contract).
        assert sig.tp == pytest.approx(0.0015)
        assert sig.sl == pytest.approx(0.001)

    def test_mean_reversion_uses_jpy_pip_size(self) -> None:
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("USD_JPY", _make_features(rsi_14=15.0, bb_pct_b=0.05, atr_14=0.1), _CTX)
        assert sig.signal == "long"
        tp_pips = 0.1 * 1.5 / 0.01  # 15 pips at JPY pip size
        sl_pips = 0.1 * 1.0 / 0.01  # 10 pips
        assert sig.ev_before_cost == pytest.approx(0.5 * tp_pips - 0.5 * sl_pips, abs=1e-3)

    def test_mean_reversion_no_trade_ev_zero(self) -> None:
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(), _CTX)
        assert sig.signal == "no_trade"
        assert sig.ev_before_cost == 0.0
        assert sig.ev_after_cost == 0.0
        assert sig.ev_unit == EV_UNIT_PIPS_POST_COST

    def test_breakout_ev_is_pips_with_sl_term(self) -> None:
        # close=1.116, bb_upper=1.110, atr=0.012 → strength 0.5 ATR →
        # confidence 1.0 at default breakout_strength_full_atr=0.5.
        bo = BreakoutStrategy("bo_1", tp_atr_multiplier=1.5, sl_atr_multiplier=1.0)
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(
                last_close=1.116,
                bb_upper=1.110,
                bb_lower=1.090,
                ema_12=1.11,
                ema_26=1.10,
                atr_14=0.012,
            ),
            _CTX,
        )
        assert sig.signal == "long"
        assert sig.ev_unit == EV_UNIT_PIPS_POST_COST
        tp_pips = 0.012 * 1.5 / 0.0001
        sl_pips = 0.012 * 1.0 / 0.0001
        expected = 1.0 * tp_pips - 0.0 * sl_pips
        assert sig.ev_before_cost == pytest.approx(expected, abs=1e-3)
        assert sig.ev_after_cost == pytest.approx(expected, abs=1e-3)

    def test_stub_strategies_declare_pips_post_cost(self) -> None:
        trend = DeterministicTrendStrategy().evaluate("EURUSD", _make_features(), _CTX)
        assert trend.ev_unit == EV_UNIT_PIPS_POST_COST
        no_trade = AlwaysNoTradeStrategy().evaluate("EURUSD", _make_features(), _CTX)
        assert no_trade.ev_unit == EV_UNIT_PIPS_POST_COST

    @pytest.mark.parametrize(
        "strategy",
        [
            RSIStrategy("rsi_1"),
            MACDStrategy("macd_1"),
            BollingerStrategy("bb_1"),
            MAStrategy("ma_1"),
            ATRStrategy("atr_1"),
        ],
        ids=["rsi", "macd", "bollinger", "ma", "atr"],
    )
    def test_legacy_price_unit_strategies_declare_non_comparable(self, strategy) -> None:
        sig = strategy.evaluate("EUR_USD", _make_features(), _CTX)
        assert sig.ev_unit == EV_UNIT_PRICE_RAW
        assert not is_comparable(sig.ev_unit)

    def test_strategy_signal_default_ev_unit_is_non_comparable(self) -> None:
        # An emitter that forgets to declare its unit can never be ranked.
        sig = StrategySignal(
            strategy_id="s",
            strategy_type="t",
            strategy_version="v",
            signal="long",
            confidence=0.9,
            ev_before_cost=10.0,
            ev_after_cost=10.0,
            tp=1.0,
            sl=1.0,
            holding_time_seconds=60,
            enabled=True,
        )
        assert sig.ev_unit == EV_UNIT_UNKNOWN
        assert not is_comparable(sig.ev_unit)


# ---------------------------------------------------------------------------
# 4./5. Meta fail-closed behaviour (sqlite fixture)
# ---------------------------------------------------------------------------

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


def _seed_candidate(
    engine,
    *,
    cycle_id: str,
    instrument: str,
    strategy_id: str,
    direction: str = "buy",
    confidence: float = 0.7,
    ev_after_cost: float = 12.0,
    ev_before_cost: float = 15.0,
    ev_unit: str | None = EV_UNIT_PIPS_POST_COST,
) -> None:
    """Seed one strategy_signals row.  ev_unit=None omits the key (legacy row)."""
    meta = {
        "decision_chain_id": "chain-test",
        "ev_before_cost": ev_before_cost,
        "ev_after_cost": ev_after_cost,
        "spread": 0.0,
        "tp": 20.0,
        "sl": 10.0,
        "holding_time_seconds": 3600,
        "enabled": True,
    }
    if ev_unit is not None:
        meta["ev_unit"] = ev_unit
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO strategy_signals (
                    cycle_id, instrument, strategy_id, strategy_type,
                    strategy_version, signal_direction, confidence,
                    signal_time_utc, meta
                ) VALUES (
                    :cycle_id, :instrument, :strategy_id, 'stub',
                    '1.0.0', :direction, :confidence,
                    :signal_time_utc, :meta
                )
                """
            ),
            {
                "cycle_id": cycle_id,
                "instrument": instrument,
                "strategy_id": strategy_id,
                "direction": direction,
                "confidence": confidence,
                "signal_time_utc": _FIXED_NOW.isoformat(),
                "meta": json.dumps(meta),
            },
        )


class TestMetaFailClosedOnIncomparableUnits:
    def test_missing_ev_unit_candidate_is_rejected(self, engine) -> None:
        """Legacy rows without an ev_unit key load as 'unknown' → rejected."""
        _seed_candidate(
            engine,
            cycle_id="cyc-legacy",
            instrument="EURUSD",
            strategy_id="s-legacy",
            ev_after_cost=50.0,
            ev_unit=None,
        )
        r = run_meta_cycle(engine, cycle_id="cyc-legacy", clock=FixedClock(_FIXED_NOW))
        assert r.adopted is False
        assert r.trading_signal_id is None
        assert r.filtered_count == 1
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT reason_code, strategy_id FROM no_trade_events"
                    " WHERE cycle_id='cyc-legacy'"
                )
            ).fetchone()
        assert row.reason_code == MetaFilterReason.EV_UNIT_INCOMPARABLE
        assert row.strategy_id == "s-legacy"

    def test_price_raw_candidate_is_rejected(self, engine) -> None:
        _seed_candidate(
            engine,
            cycle_id="cyc-praw",
            instrument="EURUSD",
            strategy_id="s-praw",
            ev_after_cost=100.0,
            ev_unit=EV_UNIT_PRICE_RAW,
        )
        r = run_meta_cycle(engine, cycle_id="cyc-praw", clock=FixedClock(_FIXED_NOW))
        assert r.adopted is False
        with engine.connect() as conn:
            reason = conn.execute(
                text("SELECT no_trade_reason FROM meta_decisions WHERE cycle_id='cyc-praw'")
            ).scalar()
        assert reason == MetaFilterReason.EV_UNIT_INCOMPARABLE

    def test_mixed_unit_cycle_comparable_wins_no_mixed_ranking(self, engine) -> None:
        """A numerically-huge price_raw EV must NOT outrank a modest
        pips_post_cost EV — the incomparable candidate is rejected before
        the F-16 sort ever sees it."""
        _seed_candidate(
            engine,
            cycle_id="cyc-mixed",
            instrument="EURUSD",
            strategy_id="s-price-raw-huge",
            ev_after_cost=99999.0,  # would win any naive mixed sort
            ev_unit=EV_UNIT_PRICE_RAW,
        )
        _seed_candidate(
            engine,
            cycle_id="cyc-mixed",
            instrument="USDJPY",
            strategy_id="s-pips-modest",
            ev_after_cost=2.0,
            ev_unit=EV_UNIT_PIPS_POST_COST,
        )
        r = run_meta_cycle(engine, cycle_id="cyc-mixed", clock=FixedClock(_FIXED_NOW))
        assert r.adopted is True
        assert r.adopted_strategy_id == "s-pips-modest"
        assert r.adopted_ev_after_cost == 2.0
        assert r.filtered_count == 1
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT reason_code, strategy_id FROM no_trade_events"
                    " WHERE cycle_id='cyc-mixed'"
                )
            ).fetchone()
        assert row.reason_code == MetaFilterReason.EV_UNIT_INCOMPARABLE
        assert row.strategy_id == "s-price-raw-huge"


class TestForceFallbackProductionGuarded:
    def test_default_config_is_fail_closed(self) -> None:
        # F8_FORCE_FALLBACK_PRODUCTION_GUARDED: production-like default.
        assert MetaCycleConfig().force_fallback is False

    def test_all_candidates_fail_default_config_adopts_nothing(self, engine) -> None:
        _seed_candidate(
            engine,
            cycle_id="cyc-guard",
            instrument="EURUSD",
            strategy_id="s-neg-ev",
            ev_after_cost=-1.0,
        )
        _seed_candidate(
            engine,
            cycle_id="cyc-guard",
            instrument="USDJPY",
            strategy_id="s-legacy-unit",
            ev_after_cost=8.0,
            ev_unit=None,
        )
        r = run_meta_cycle(engine, cycle_id="cyc-guard", clock=FixedClock(_FIXED_NOW))
        assert r.adopted is False
        assert r.fallback_used is False
        assert r.trading_signal_id is None
        assert r.adopted_ev_after_cost is None
        assert r.filtered_count == 2
        with engine.connect() as conn:
            ts = conn.execute(text("SELECT count(*) FROM trading_signals")).scalar()
            nte = conn.execute(
                text("SELECT count(*) FROM no_trade_events WHERE cycle_id='cyc-guard'")
            ).scalar()
        assert ts == 0
        assert nte == 2  # one rejection row per filtered candidate

    def test_explicit_force_fallback_true_still_adopts(self, engine) -> None:
        """The legacy smoke ≥1-trade guarantee remains available opt-in."""
        _seed_candidate(
            engine,
            cycle_id="cyc-optin",
            instrument="EURUSD",
            strategy_id="s-neg-ev",
            ev_after_cost=-1.0,
        )
        r = run_meta_cycle(
            engine,
            cycle_id="cyc-optin",
            clock=FixedClock(_FIXED_NOW),
            config=MetaCycleConfig(force_fallback=True),
        )
        assert r.adopted is True
        assert r.fallback_used is True
        assert r.adopted_strategy_id == "s-neg-ev"
