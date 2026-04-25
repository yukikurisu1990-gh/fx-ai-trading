"""Unit tests for vectorised strategy helpers in compare_multipair_v13_ensemble.py (Phase 9.17 G-3).

These cover the script-level helpers that drive the v13 ensemble eval:
  - _compute_pnl_vec: per-bar gross PnL from signal x label x TP/SL
  - _mr_signal_vec:   vectorised MeanReversionStrategy
  - _bo_signal_vec:   vectorised BreakoutStrategy
  - _compute_correlation_matrix: inter-strategy Pearson rho

Each vectorised helper is also cross-checked against the corresponding
class-based strategy implementation in src/.../services/strategies/.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext
from fx_ai_trading.services.strategies.breakout import BreakoutStrategy
from fx_ai_trading.services.strategies.mean_reversion import MeanReversionStrategy

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "compare_multipair_v13_ensemble.py"
_spec = importlib.util.spec_from_file_location("v13_ensemble", _SCRIPT_PATH)
v13 = importlib.util.module_from_spec(_spec)
sys.modules["v13_ensemble"] = v13
assert _spec.loader is not None
_spec.loader.exec_module(v13)


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
        computed_at=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
    )


# ---------------------------------------------------------------------------
# _compute_pnl_vec
# ---------------------------------------------------------------------------


class TestComputePnlVec:
    def test_long_tp_returns_tp_pip(self) -> None:
        sig = np.array([1], dtype=np.int8)
        label = np.array([1], dtype=np.int64)
        tp_pip = np.array([15.0])
        sl_pip = np.array([10.0])
        traded = np.array([True])
        out = v13._compute_pnl_vec(sig, label, tp_pip, sl_pip, traded)
        assert out[0] == pytest.approx(15.0)

    def test_long_sl_returns_neg_sl_pip(self) -> None:
        sig = np.array([1], dtype=np.int8)
        label = np.array([-1], dtype=np.int64)
        tp_pip = np.array([15.0])
        sl_pip = np.array([10.0])
        traded = np.array([True])
        out = v13._compute_pnl_vec(sig, label, tp_pip, sl_pip, traded)
        assert out[0] == pytest.approx(-10.0)

    def test_short_tp_returns_tp_pip(self) -> None:
        sig = np.array([-1], dtype=np.int8)
        label = np.array([-1], dtype=np.int64)
        tp_pip = np.array([15.0])
        sl_pip = np.array([10.0])
        traded = np.array([True])
        out = v13._compute_pnl_vec(sig, label, tp_pip, sl_pip, traded)
        assert out[0] == pytest.approx(15.0)

    def test_short_sl_returns_neg_sl_pip(self) -> None:
        sig = np.array([-1], dtype=np.int8)
        label = np.array([1], dtype=np.int64)
        tp_pip = np.array([15.0])
        sl_pip = np.array([10.0])
        traded = np.array([True])
        out = v13._compute_pnl_vec(sig, label, tp_pip, sl_pip, traded)
        assert out[0] == pytest.approx(-10.0)

    def test_timeout_returns_zero(self) -> None:
        sig = np.array([1, -1], dtype=np.int8)
        label = np.array([0, 0], dtype=np.int64)
        tp_pip = np.array([15.0, 15.0])
        sl_pip = np.array([10.0, 10.0])
        traded = np.array([True, True])
        out = v13._compute_pnl_vec(sig, label, tp_pip, sl_pip, traded)
        assert out[0] == 0.0
        assert out[1] == 0.0

    def test_not_traded_returns_zero(self) -> None:
        sig = np.array([1], dtype=np.int8)
        label = np.array([1], dtype=np.int64)
        tp_pip = np.array([15.0])
        sl_pip = np.array([10.0])
        traded = np.array([False])
        out = v13._compute_pnl_vec(sig, label, tp_pip, sl_pip, traded)
        assert out[0] == 0.0


# ---------------------------------------------------------------------------
# _mr_signal_vec — cross-checked against MeanReversionStrategy
# ---------------------------------------------------------------------------


class TestMrSignalVec:
    def test_both_oversold_emits_long_matching_class(self) -> None:
        rsi = np.array([20.0])
        bb_pct_b = np.array([0.05])
        sig, conf = v13._mr_signal_vec(rsi, bb_pct_b)
        assert sig[0] == 1

        mr = MeanReversionStrategy("ref")
        ref = mr.evaluate("EUR_USD", _make_features(rsi_14=20.0, bb_pct_b=0.05), _CTX)
        assert ref.signal == "long"
        assert conf[0] == pytest.approx(ref.confidence, abs=1e-4)

    def test_both_overbought_emits_short_matching_class(self) -> None:
        rsi = np.array([80.0])
        bb_pct_b = np.array([0.95])
        sig, conf = v13._mr_signal_vec(rsi, bb_pct_b)
        assert sig[0] == -1

        mr = MeanReversionStrategy("ref")
        ref = mr.evaluate("EUR_USD", _make_features(rsi_14=80.0, bb_pct_b=0.95), _CTX)
        assert ref.signal == "short"
        assert conf[0] == pytest.approx(ref.confidence, abs=1e-4)

    def test_rsi_oversold_only_no_trade(self) -> None:
        rsi = np.array([20.0])
        bb_pct_b = np.array([0.5])
        sig, conf = v13._mr_signal_vec(rsi, bb_pct_b)
        assert sig[0] == 0
        assert conf[0] == 0.0

    def test_bb_overbought_only_no_trade(self) -> None:
        rsi = np.array([50.0])
        bb_pct_b = np.array([0.95])
        sig, conf = v13._mr_signal_vec(rsi, bb_pct_b)
        assert sig[0] == 0
        assert conf[0] == 0.0

    def test_neutral_no_trade(self) -> None:
        rsi = np.array([50.0])
        bb_pct_b = np.array([0.5])
        sig, conf = v13._mr_signal_vec(rsi, bb_pct_b)
        assert sig[0] == 0
        assert conf[0] == 0.0

    def test_batch_consistency(self) -> None:
        rsi = np.array([20.0, 50.0, 80.0, 25.0])
        bb_pct_b = np.array([0.05, 0.5, 0.95, 0.5])
        sig, conf = v13._mr_signal_vec(rsi, bb_pct_b)
        assert (sig == np.array([1, 0, -1, 0], dtype=np.int8)).all()
        assert conf[1] == 0.0  # neutral
        assert conf[3] == 0.0  # bb mismatched


# ---------------------------------------------------------------------------
# _bo_signal_vec — cross-checked against BreakoutStrategy
# ---------------------------------------------------------------------------


class TestBoSignalVec:
    def test_upper_break_with_uptrend_long_matching_class(self) -> None:
        last_close = np.array([1.115])
        bb_upper = np.array([1.11])
        bb_lower = np.array([1.09])
        ema_12 = np.array([1.105])
        ema_26 = np.array([1.100])
        atr = np.array([0.012])
        sig, conf = v13._bo_signal_vec(last_close, bb_upper, bb_lower, ema_12, ema_26, atr)
        assert sig[0] == 1

        bo = BreakoutStrategy("ref")
        ref = bo.evaluate(
            "EUR_USD",
            _make_features(
                last_close=1.115,
                bb_upper=1.11,
                bb_lower=1.09,
                ema_12=1.105,
                ema_26=1.100,
                atr_14=0.012,
            ),
            _CTX,
        )
        assert ref.signal == "long"
        assert conf[0] == pytest.approx(ref.confidence, abs=1e-4)

    def test_lower_break_with_downtrend_short_matching_class(self) -> None:
        last_close = np.array([1.085])
        bb_upper = np.array([1.11])
        bb_lower = np.array([1.09])
        ema_12 = np.array([1.095])
        ema_26 = np.array([1.100])
        atr = np.array([0.012])
        sig, conf = v13._bo_signal_vec(last_close, bb_upper, bb_lower, ema_12, ema_26, atr)
        assert sig[0] == -1

        bo = BreakoutStrategy("ref")
        ref = bo.evaluate(
            "EUR_USD",
            _make_features(
                last_close=1.085,
                bb_upper=1.11,
                bb_lower=1.09,
                ema_12=1.095,
                ema_26=1.100,
                atr_14=0.012,
            ),
            _CTX,
        )
        assert ref.signal == "short"
        assert conf[0] == pytest.approx(ref.confidence, abs=1e-4)

    def test_break_without_trend_no_trade(self) -> None:
        last_close = np.array([1.115])
        bb_upper = np.array([1.11])
        bb_lower = np.array([1.09])
        ema_12 = np.array([1.095])  # downtrend
        ema_26 = np.array([1.100])
        atr = np.array([0.012])
        sig, _ = v13._bo_signal_vec(last_close, bb_upper, bb_lower, ema_12, ema_26, atr)
        assert sig[0] == 0

    def test_zero_atr_no_trade(self) -> None:
        last_close = np.array([1.115])
        bb_upper = np.array([1.11])
        bb_lower = np.array([1.09])
        ema_12 = np.array([1.105])
        ema_26 = np.array([1.100])
        atr = np.array([0.0])
        sig, conf = v13._bo_signal_vec(last_close, bb_upper, bb_lower, ema_12, ema_26, atr)
        assert sig[0] == 0
        assert conf[0] == 0.0

    def test_batch_consistency(self) -> None:
        last_close = np.array([1.115, 1.100, 1.085])
        bb_upper = np.array([1.11, 1.11, 1.11])
        bb_lower = np.array([1.09, 1.09, 1.09])
        ema_12 = np.array([1.105, 1.105, 1.095])
        ema_26 = np.array([1.100, 1.100, 1.100])
        atr = np.array([0.012, 0.012, 0.012])
        sig, _ = v13._bo_signal_vec(last_close, bb_upper, bb_lower, ema_12, ema_26, atr)
        assert sig.tolist() == [1, 0, -1]


# ---------------------------------------------------------------------------
# _compute_correlation_matrix
# ---------------------------------------------------------------------------


class TestCorrelationMatrix:
    def test_perfect_positive_correlation(self) -> None:
        series = {
            "a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "b": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        }
        rho = v13._compute_correlation_matrix(series)
        assert rho[("a", "b")] == pytest.approx(1.0)

    def test_perfect_negative_correlation(self) -> None:
        series = {
            "a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "b": [6.0, 5.0, 4.0, 3.0, 2.0, 1.0],
        }
        rho = v13._compute_correlation_matrix(series)
        assert rho[("a", "b")] == pytest.approx(-1.0)

    def test_self_correlation_one(self) -> None:
        series = {"a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]}
        rho = v13._compute_correlation_matrix(series)
        assert rho[("a", "a")] == pytest.approx(1.0)

    def test_nan_excluded_from_overlap(self) -> None:
        # Bars where both series traded: [3.0, 4.0, 5.0, 6.0, 7.0]
        # Highly correlated; rho close to 1.0
        series = {
            "a": [1.0, np.nan, 3.0, 4.0, 5.0, 6.0, 7.0],
            "b": [np.nan, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
        }
        rho = v13._compute_correlation_matrix(series)
        assert rho[("a", "b")] == pytest.approx(1.0)

    def test_insufficient_overlap_returns_zero(self) -> None:
        # < 5 overlapping bars
        series = {
            "a": [1.0, np.nan, np.nan, np.nan, 5.0, np.nan],
            "b": [np.nan, 2.0, np.nan, 4.0, np.nan, 6.0],
        }
        rho = v13._compute_correlation_matrix(series)
        assert rho[("a", "b")] == 0.0

    def test_constant_series_returns_zero(self) -> None:
        series = {
            "a": [3.0, 3.0, 3.0, 3.0, 3.0, 3.0],
            "b": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        }
        rho = v13._compute_correlation_matrix(series)
        assert rho[("a", "b")] == 0.0
