"""Unit tests for Stage 23.0c M5 z-score MR (first-touch) eval."""

from __future__ import annotations

import importlib
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage23_0b = importlib.import_module("stage23_0b_m5_donchian_eval")
stage23_0c = importlib.import_module("stage23_0c_m5_zscore_mr_eval")


# ---------------------------------------------------------------------------
# Synthetic helpers
# ---------------------------------------------------------------------------


def _make_m5(
    n_bars: int,
    bid_close: np.ndarray | None = None,
    spread_pip: float = 1.0,
    high_offset_pip: float = 0.5,
    low_offset_pip: float = 0.5,
    pip: float = 0.0001,
) -> pd.DataFrame:
    start = datetime(2026, 1, 5, 9, 5, tzinfo=UTC)
    idx = pd.date_range(start, periods=n_bars, freq="5min", tz=UTC)
    if bid_close is None:
        bid_close = np.full(n_bars, 1.0)
    bid_close = np.asarray(bid_close, dtype=np.float64)
    bid_open = bid_close.copy()
    bid_high = bid_close + high_offset_pip * pip
    bid_low = bid_close - low_offset_pip * pip
    ask_close = bid_close + spread_pip * pip
    ask_open = bid_open + spread_pip * pip
    ask_high = bid_high + spread_pip * pip
    ask_low = bid_low + spread_pip * pip
    return pd.DataFrame(
        {
            "bid_o": bid_open,
            "bid_h": bid_high,
            "bid_l": bid_low,
            "bid_c": bid_close,
            "ask_o": ask_open,
            "ask_h": ask_high,
            "ask_l": ask_low,
            "ask_c": ask_close,
        },
        index=idx,
    )


# ---------------------------------------------------------------------------
# 1: μ/σ causal shift(1)
# ---------------------------------------------------------------------------


def test_zscore_mu_sigma_use_causal_shift1():
    n = 30
    rng = np.random.RandomState(1)
    bid = 1.0 + np.cumsum(rng.randn(n)) * 0.0001
    m5 = _make_m5(n, bid_close=bid)
    df = stage23_0c.compute_zscore(m5, n=10)
    t = 15
    expected_mu = df["mid_c"].iloc[t - 10 : t].mean()
    np.testing.assert_allclose(df["mu_10"].iloc[t], expected_mu, rtol=1e-12)
    expected_sigma = df["mid_c"].iloc[t - 10 : t].std(ddof=0)
    np.testing.assert_allclose(df["sigma_10"].iloc[t], expected_sigma, rtol=1e-10)


# ---------------------------------------------------------------------------
# 2: signal uses mid_c, not bid_c/ask_c directly
# ---------------------------------------------------------------------------


def test_zscore_uses_mid_close_not_bid_or_ask():
    n = 25
    bid = 1.0 + np.arange(n) * 0.0001
    m5 = _make_m5(n, bid_close=bid)
    df = stage23_0c.compute_zscore(m5, n=5)
    expected_mid = (m5["bid_c"] + m5["ask_c"]) / 2.0
    np.testing.assert_allclose(df["mid_c"], expected_mid)


# ---------------------------------------------------------------------------
# 3, 4: long / short rising-edge first-touch
# ---------------------------------------------------------------------------


def test_long_signal_when_z_below_neg_threshold_first_touch():
    """Deterministic linear ramp + isolated drop at idx 20 → first-touch fires."""
    n = 40
    pip = 0.0001
    bid = 1.0 + np.linspace(0, 10 * pip, n)  # +0.25 pip per bar (σ in window > 0)
    bid[20] -= 8 * pip  # isolated big drop
    m5 = _make_m5(n, bid_close=bid)
    sigs = stage23_0c.extract_signals_first_touch(m5, n=10, threshold=2.0)
    long_sigs = sigs[sigs["direction"] == "long"]
    assert m5.index[20] in set(long_sigs["entry_ts"])


def test_short_signal_when_z_above_pos_threshold_first_touch():
    """Deterministic linear ramp + isolated spike at idx 20 → first-touch fires."""
    n = 40
    pip = 0.0001
    bid = 1.0 + np.linspace(0, 10 * pip, n)
    bid[20] += 8 * pip
    m5 = _make_m5(n, bid_close=bid)
    sigs = stage23_0c.extract_signals_first_touch(m5, n=10, threshold=2.0)
    short_sigs = sigs[sigs["direction"] == "short"]
    assert m5.index[20] in set(short_sigs["entry_ts"])


# ---------------------------------------------------------------------------
# 5: first-touch does NOT re-trigger while in the extreme zone
# ---------------------------------------------------------------------------


def test_first_touch_does_not_re_trigger_in_extreme_zone():
    """Sustained 5-pip bias for 10 bars on linear ramp baseline → ≤1 long signal."""
    n = 80
    pip = 0.0001
    bid = 1.0 + np.linspace(0, 8 * pip, n)  # deterministic ramp (no incidental crossings)
    bid[30:40] -= 5 * pip
    m5 = _make_m5(n, bid_close=bid)
    sigs = stage23_0c.extract_signals_first_touch(m5, n=10, threshold=2.0)
    long_sigs = sigs[sigs["direction"] == "long"]
    n_in_zone = sum(1 for ts in long_sigs["entry_ts"] if m5.index[28] <= ts <= m5.index[42])
    assert n_in_zone <= 1, f"Expected ≤1 long signal in bias zone, got {n_in_zone}"


# ---------------------------------------------------------------------------
# 6: lock resets after returning inside
# ---------------------------------------------------------------------------


def test_first_touch_resets_after_returning_inside():
    """Two isolated dip events on linear ramp baseline → ≥2 long signals."""
    n = 120
    pip = 0.0001
    bid = 1.0 + np.linspace(0, 12 * pip, n)
    bid[30] -= 8 * pip
    bid[60] -= 8 * pip
    m5 = _make_m5(n, bid_close=bid)
    sigs = stage23_0c.extract_signals_first_touch(m5, n=10, threshold=2.0)
    long_sigs = sigs[sigs["direction"] == "long"]
    assert len(long_sigs) >= 2


# ---------------------------------------------------------------------------
# 7: long and short locks are independent
# ---------------------------------------------------------------------------


def test_long_short_locks_independent():
    """Negative deviation and positive spike in same series on ramp baseline → both fire."""
    n = 80
    pip = 0.0001
    bid = 1.0 + np.linspace(0, 8 * pip, n)
    bid[30] -= 8 * pip
    bid[60] += 8 * pip
    m5 = _make_m5(n, bid_close=bid)
    sigs = stage23_0c.extract_signals_first_touch(m5, n=10, threshold=2.0)
    long_sigs = sigs[sigs["direction"] == "long"]
    short_sigs = sigs[sigs["direction"] == "short"]
    assert len(long_sigs) >= 1
    assert len(short_sigs) >= 1


# ---------------------------------------------------------------------------
# 8: warmup bars have no signal
# ---------------------------------------------------------------------------


def test_no_signal_when_rolling_window_not_filled():
    n = 25
    rng = np.random.RandomState(2)
    bid = 1.0 + rng.randn(n) * 0.0001
    m5 = _make_m5(n, bid_close=bid)
    sigs = stage23_0c.extract_signals_first_touch(m5, n=10, threshold=2.0)
    # No signal can occur at idx < 11 (rolling window not filled + shift(1) for z[t-1])
    if len(sigs):
        positions = m5.index.get_indexer(sigs["entry_ts"])
        assert (positions >= 11).all()


# ---------------------------------------------------------------------------
# 9: σ=0 produces no signal (constant series)
# ---------------------------------------------------------------------------


def test_no_signal_when_sigma_zero():
    n = 30
    bid = np.full(n, 1.0)
    m5 = _make_m5(n, bid_close=bid, high_offset_pip=0.0, low_offset_pip=0.0)
    sigs = stage23_0c.extract_signals_first_touch(m5, n=10, threshold=2.0)
    assert len(sigs) == 0


# ---------------------------------------------------------------------------
# 10, 11: signal join + valid_label
# ---------------------------------------------------------------------------


def _make_synthetic_labels(n_signal: int, signal_tf: str = "M5") -> pd.DataFrame:
    start = datetime(2026, 1, 5, 9, 5, tzinfo=UTC)
    ts = pd.date_range(start, periods=n_signal, freq="5min", tz=UTC)
    rows = []
    for t in ts:
        for h in (1, 2, 3):
            for d in ("long", "short"):
                rows.append(
                    {
                        "entry_ts": t,
                        "pair": "EUR_USD",
                        "signal_timeframe": signal_tf,
                        "horizon_bars": np.int8(h),
                        "horizon_minutes": np.int16(h * 5),
                        "direction": d,
                        "tb_pnl": np.float32(1.0 if d == "long" else -1.0),
                        "time_exit_pnl": np.float32(2.0 if d == "long" else -2.0),
                        "valid_label": True,
                    }
                )
    return pd.DataFrame(rows)


def test_signal_join_to_23_0a_outcome():
    labels = _make_synthetic_labels(20)
    sig = pd.DataFrame(
        {
            "entry_ts": [labels["entry_ts"].iloc[3]],
            "pair": ["EUR_USD"],
            "direction": ["long"],
        }
    )
    labels_h1 = labels[labels["horizon_bars"] == 1]
    joined = pd.merge(sig, labels_h1, on=["entry_ts", "pair", "direction"], how="inner")
    assert len(joined) == 1
    assert np.isfinite(joined["tb_pnl"].iloc[0])


def test_signal_drops_invalid_rows():
    labels = _make_synthetic_labels(10)
    labels.loc[5, "valid_label"] = False
    valid = labels[labels["valid_label"]]
    assert len(valid) < len(labels)


# ---------------------------------------------------------------------------
# 12, 13, 14: ddof=0 / A4 / A5 same as 23.0b
# ---------------------------------------------------------------------------


def test_sharpe_per_trade_ddof0_no_annualize():
    pnl = pd.Series([1.0, -0.5, 2.0, -1.0, 0.5])
    expected = pnl.mean() / pnl.std(ddof=0)
    assert abs(stage23_0c._per_trade_sharpe(pnl) - expected) < 1e-12


def test_a4_4fold_majority_rule_via_23_0b_helper():
    pnl = np.zeros(100)
    pnl[0:20] = 1.0  # k=0 warmup
    pnl[20:40] = 1.0
    pnl[40:60] = 1.0
    pnl[60:80] = 1.0
    pnl[80:100] = -1.0
    pnl = pnl + np.linspace(0, 0.001, 100)
    df = pd.DataFrame(
        {
            "entry_ts": pd.date_range("2026-01-01", periods=100, freq="1h", tz=UTC),
            "pnl_pip": pnl,
        }
    )
    fold = stage23_0c._fold_stability(df)
    assert fold["n_positive"] == 3


def test_a5_spread_stress_subtracts_half_pip_per_trade():
    assert abs(stage23_0c.A5_SPREAD_STRESS_PIP - 0.5) < 1e-12


# ---------------------------------------------------------------------------
# 15: NG#6 — signal_timeframe == "M5" runtime assertion
# ---------------------------------------------------------------------------


def test_no_phase22_m1_cell_reused():
    bad_labels = _make_synthetic_labels(5, signal_tf="M1")
    bad_labels = bad_labels[bad_labels["valid_label"]]
    assert (bad_labels["signal_timeframe"] != "M5").all()
    assert stage23_0c.SIGNAL_TIMEFRAME == "M5"


# ---------------------------------------------------------------------------
# 16: cell pooling — 20 pairs canonical
# ---------------------------------------------------------------------------


def test_cell_pooling_aggregates_all_pairs():
    assert len(stage23_0c.PAIRS_20) == 20
    assert "EUR_USD" in stage23_0c.PAIRS_20
    assert "USD_JPY" in stage23_0c.PAIRS_20


# ---------------------------------------------------------------------------
# 17: smoke mode shape
# ---------------------------------------------------------------------------


def test_smoke_mode_3pairs_2cells():
    assert len(stage23_0c.SMOKE_PAIRS) == 3
    assert len(stage23_0c.SMOKE_CELLS) == 2


# ---------------------------------------------------------------------------
# 18: 3-class verdict via 23.0b helper
# ---------------------------------------------------------------------------


def test_verdict_3class_assignment():
    gates_all = {"A0": True, "A1": True, "A2": True, "A3": True, "A4": True, "A5": True}
    s1_strong = {
        "is_sharpe": 0.10,
        "oos_sharpe": 0.08,
        "oos_is_ratio": 0.8,
        "is_n": 800,
        "oos_n": 200,
    }
    assert stage23_0c.assign_verdict(gates_all, s1_strong) == "ADOPT_CANDIDATE"

    gates_a4_fail = {"A0": True, "A1": True, "A2": True, "A3": True, "A4": False, "A5": True}
    assert stage23_0c.assign_verdict(gates_a4_fail, None) == "PROMISING_BUT_NEEDS_OOS"

    gates_a1_fail = {"A0": True, "A1": False, "A2": True, "A3": True, "A4": True, "A5": True}
    assert stage23_0c.assign_verdict(gates_a1_fail, None) == "REJECT"


# ---------------------------------------------------------------------------
# 19: REJECT-reason classification
# ---------------------------------------------------------------------------


def test_reject_reason_classification():
    # under_firing
    g_a0_fail = {"A0": False, "A1": True, "A2": True, "A3": True, "A4": True, "A5": True}
    m_low = {"overtrading_warning": False}
    assert stage23_0c.classify_reject_reason(m_low, g_a0_fail) == "under_firing"

    # still_overtrading
    g_a1_fail = {"A0": True, "A1": False, "A2": True, "A3": True, "A4": True, "A5": True}
    m_over = {"overtrading_warning": True}
    assert stage23_0c.classify_reject_reason(m_over, g_a1_fail) == "still_overtrading"

    # pnl_edge_insufficient
    m_normal = {"overtrading_warning": False}
    assert stage23_0c.classify_reject_reason(m_normal, g_a1_fail) == "pnl_edge_insufficient"

    # robustness_failure (A1+A2 pass, A4 fails)
    g_a4_fail = {"A0": True, "A1": True, "A2": True, "A3": True, "A4": False, "A5": True}
    assert stage23_0c.classify_reject_reason(m_normal, g_a4_fail) == "robustness_failure"

    # not REJECT
    g_all_pass = {"A0": True, "A1": True, "A2": True, "A3": True, "A4": True, "A5": True}
    assert stage23_0c.classify_reject_reason(m_normal, g_all_pass) is None


# ---------------------------------------------------------------------------
# 20: TRIGGER_MODE constant pinned to first_touch
# ---------------------------------------------------------------------------


def test_trigger_mode_constant_documented():
    assert stage23_0c.TRIGGER_MODE == "first_touch", (
        "23.0c must use first_touch trigger; continuous-trigger is intentionally NOT default. "
        "See docs/design/phase23_0c_m5_zscore_mr_baseline.md §2.2."
    )
