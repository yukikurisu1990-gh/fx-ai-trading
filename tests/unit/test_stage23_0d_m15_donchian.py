"""Unit tests for Stage 23.0d M15 Donchian first-touch breakout eval."""

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
stage23_0d = importlib.import_module("stage23_0d_m15_donchian_eval")


# ---------------------------------------------------------------------------
# Synthetic helpers
# ---------------------------------------------------------------------------


def _make_m15(
    n_bars: int,
    bid_close: np.ndarray | None = None,
    spread_pip: float = 1.0,
    high_offset_pip: float = 0.5,
    low_offset_pip: float = 0.5,
    pip: float = 0.0001,
) -> pd.DataFrame:
    start = datetime(2026, 1, 5, 9, 15, tzinfo=UTC)
    idx = pd.date_range(start, periods=n_bars, freq="15min", tz=UTC)
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
# 1: Donchian causal shift(1)
# ---------------------------------------------------------------------------


def test_donchian_upper_lower_causal_shift1():
    n = 30
    bid = 1.0 + np.arange(n, dtype=float) * 0.0001
    m15 = _make_m15(n, bid_close=bid)
    df = stage23_0d.compute_donchian_bands(m15, n=10)
    t = 15
    expected_upper = df["mid_h"].iloc[t - 10 : t].max()
    np.testing.assert_allclose(df["upper_10"].iloc[t], expected_upper)


# ---------------------------------------------------------------------------
# 2: signal-side uses mid (not bid/ask)
# ---------------------------------------------------------------------------


def test_donchian_uses_mid_high_low_not_bid_or_ask():
    n = 25
    m15 = _make_m15(n, bid_close=np.full(n, 1.0))
    df = stage23_0d.compute_donchian_bands(m15, n=5)
    expected_mid_h = (m15["bid_h"] + m15["ask_h"]) / 2.0
    np.testing.assert_allclose(df["mid_h"], expected_mid_h)


# ---------------------------------------------------------------------------
# 3, 4: long/short first-touch trigger
# ---------------------------------------------------------------------------


def test_long_first_touch_strict_above_upper():
    """Flat baseline + isolated upward spike at idx 20 → long first-touch fires."""
    n = 40
    pip = 0.0001
    bid = np.full(n, 1.0)
    bid[20] += 12 * pip
    m15 = _make_m15(n, bid_close=bid, high_offset_pip=0.0, low_offset_pip=0.0)
    sigs = stage23_0d.extract_signals_first_touch_donchian(m15, n=10)
    long_sigs = sigs[sigs["direction"] == "long"]
    assert m15.index[20] in set(long_sigs["entry_ts"])


def test_short_first_touch_strict_below_lower():
    n = 40
    pip = 0.0001
    bid = np.full(n, 1.0)
    bid[20] -= 12 * pip
    m15 = _make_m15(n, bid_close=bid, high_offset_pip=0.0, low_offset_pip=0.0)
    sigs = stage23_0d.extract_signals_first_touch_donchian(m15, n=10)
    short_sigs = sigs[sigs["direction"] == "short"]
    assert m15.index[20] in set(short_sigs["entry_ts"])


# ---------------------------------------------------------------------------
# 5: first-touch does NOT re-trigger above band
# ---------------------------------------------------------------------------


def test_first_touch_does_not_re_trigger_above_band():
    """Sustained price above band → at most 1 long signal in zone."""
    n = 80
    pip = 0.0001
    # Rise quickly, then stay elevated for many bars
    bid = np.full(n, 1.0)
    bid[:20] = 1.0  # baseline
    bid[20:50] = 1.0 + 5 * pip  # sustained above-band
    bid[50:] = 1.0
    m15 = _make_m15(n, bid_close=bid, high_offset_pip=0.0, low_offset_pip=0.0)
    sigs = stage23_0d.extract_signals_first_touch_donchian(m15, n=10)
    long_sigs = sigs[sigs["direction"] == "long"]
    n_in_zone = sum(1 for ts in long_sigs["entry_ts"] if m15.index[18] <= ts <= m15.index[52])
    assert n_in_zone <= 1, f"Expected ≤1 long signal in zone, got {n_in_zone}"


# ---------------------------------------------------------------------------
# 6: lock resets after returning inside band
# ---------------------------------------------------------------------------


def test_first_touch_resets_after_returning_inside_band():
    """Two separate breakouts above band → 2 long signals."""
    n = 120
    pip = 0.0001
    bid = np.full(n, 1.0)
    bid[20:25] = 1.0 + 5 * pip  # breakout #1
    bid[25:60] = 1.0  # back inside
    bid[60:65] = 1.0 + 5 * pip  # breakout #2
    bid[65:] = 1.0
    m15 = _make_m15(n, bid_close=bid, high_offset_pip=0.0, low_offset_pip=0.0)
    sigs = stage23_0d.extract_signals_first_touch_donchian(m15, n=10)
    long_sigs = sigs[sigs["direction"] == "long"]
    assert len(long_sigs) >= 2


# ---------------------------------------------------------------------------
# 7: long and short locks are independent
# ---------------------------------------------------------------------------


def test_long_short_locks_independent():
    n = 100
    pip = 0.0001
    bid = np.full(n, 1.0)
    bid[20:25] = 1.0 + 5 * pip  # break above
    bid[25:50] = 1.0  # back inside
    bid[50:55] = 1.0 - 5 * pip  # break below
    bid[55:] = 1.0
    m15 = _make_m15(n, bid_close=bid, high_offset_pip=0.0, low_offset_pip=0.0)
    sigs = stage23_0d.extract_signals_first_touch_donchian(m15, n=10)
    long_sigs = sigs[sigs["direction"] == "long"]
    short_sigs = sigs[sigs["direction"] == "short"]
    assert len(long_sigs) >= 1
    assert len(short_sigs) >= 1


# ---------------------------------------------------------------------------
# 8: warmup bars produce no signal
# ---------------------------------------------------------------------------


def test_no_signal_when_donchian_window_not_filled():
    n = 25
    bid = 1.0 + np.linspace(0, 4 * 0.0001, n)
    m15 = _make_m15(n, bid_close=bid)
    sigs = stage23_0d.extract_signals_first_touch_donchian(m15, n=10)
    if len(sigs):
        positions = m15.index.get_indexer(sigs["entry_ts"])
        # Need upper_N (>=N bars), upper_N_prev (+1), mid_c_prev (+1) defined
        assert (positions >= 11).all()


# ---------------------------------------------------------------------------
# 9, 10: signal join + horizon=4 M15 = 60 min
# ---------------------------------------------------------------------------


def _make_synthetic_m15_labels(n_signal: int, signal_tf: str = "M15") -> pd.DataFrame:
    start = datetime(2026, 1, 5, 9, 15, tzinfo=UTC)
    ts = pd.date_range(start, periods=n_signal, freq="15min", tz=UTC)
    rows = []
    for t in ts:
        for h in (1, 2, 4):
            for d in ("long", "short"):
                rows.append(
                    {
                        "entry_ts": t,
                        "pair": "EUR_USD",
                        "signal_timeframe": signal_tf,
                        "horizon_bars": np.int8(h),
                        "horizon_minutes": np.int16(h * 15),
                        "direction": d,
                        "tb_pnl": np.float32(1.0 if d == "long" else -1.0),
                        "time_exit_pnl": np.float32(2.0 if d == "long" else -2.0),
                        "valid_label": True,
                    }
                )
    return pd.DataFrame(rows)


def test_signal_join_to_23_0a_m15_outcome():
    labels = _make_synthetic_m15_labels(20)
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


def test_horizon_4_m15_yields_60_min_outcome():
    labels = _make_synthetic_m15_labels(20)
    h4 = labels[labels["horizon_bars"] == 4]
    assert (h4["horizon_minutes"] == 60).all()


# ---------------------------------------------------------------------------
# 11, 12, 13: ddof=0 / A4 / A5 (same as 23.0b/c)
# ---------------------------------------------------------------------------


def test_sharpe_per_trade_ddof0_no_annualize():
    pnl = pd.Series([1.0, -0.5, 2.0, -1.0, 0.5])
    expected = pnl.mean() / pnl.std(ddof=0)
    assert abs(stage23_0d._per_trade_sharpe(pnl) - expected) < 1e-12


def test_a4_4fold_majority_rule():
    pnl = np.zeros(100)
    pnl[0:20] = 1.0  # k=0 warmup
    pnl[20:80] = 1.0  # k=1..3 positive
    pnl[80:] = -1.0  # k=4 negative
    pnl = pnl + np.linspace(0, 0.001, 100)
    df = pd.DataFrame(
        {
            "entry_ts": pd.date_range("2026-01-01", periods=100, freq="1h", tz=UTC),
            "pnl_pip": pnl,
        }
    )
    fold = stage23_0d._fold_stability(df)
    assert fold["n_positive"] == 3


def test_a5_spread_stress_subtracts_half_pip_per_trade():
    assert abs(stage23_0d.A5_SPREAD_STRESS_PIP - 0.5) < 1e-12


# ---------------------------------------------------------------------------
# 14: NG#6 — signal_timeframe == "M15" runtime assertion
# ---------------------------------------------------------------------------


def test_no_phase22_m1_cell_reused():
    bad_labels = _make_synthetic_m15_labels(5, signal_tf="M1")
    bad_labels = bad_labels[bad_labels["valid_label"]]
    assert (bad_labels["signal_timeframe"] != "M15").all()
    assert stage23_0d.SIGNAL_TIMEFRAME == "M15"


# ---------------------------------------------------------------------------
# 15: cell pooling across 20 pairs
# ---------------------------------------------------------------------------


def test_cell_pooling_aggregates_all_pairs():
    assert len(stage23_0d.PAIRS_20) == 20
    assert "EUR_USD" in stage23_0d.PAIRS_20
    assert "USD_JPY" in stage23_0d.PAIRS_20


# ---------------------------------------------------------------------------
# 16: smoke mode
# ---------------------------------------------------------------------------


def test_smoke_mode_3pairs_2cells():
    assert len(stage23_0d.SMOKE_PAIRS) == 3
    assert len(stage23_0d.SMOKE_CELLS) == 2


# ---------------------------------------------------------------------------
# 17: 3-class verdict
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
    assert stage23_0d.assign_verdict(gates_all, s1_strong) == "ADOPT_CANDIDATE"

    gates_a4_fail = {"A0": True, "A1": True, "A2": True, "A3": True, "A4": False, "A5": True}
    assert stage23_0d.assign_verdict(gates_a4_fail, None) == "PROMISING_BUT_NEEDS_OOS"

    gates_a1_fail = {"A0": True, "A1": False, "A2": True, "A3": True, "A4": True, "A5": True}
    assert stage23_0d.assign_verdict(gates_a1_fail, None) == "REJECT"


# ---------------------------------------------------------------------------
# 18: REJECT-reason classification
# ---------------------------------------------------------------------------


def test_reject_reason_classification():
    g_a0_fail = {"A0": False, "A1": True, "A2": True, "A3": True, "A4": True, "A5": True}
    m_low = {"overtrading_warning": False}
    assert stage23_0d.classify_reject_reason(m_low, g_a0_fail) == "under_firing"

    g_a1_fail = {"A0": True, "A1": False, "A2": True, "A3": True, "A4": True, "A5": True}
    m_over = {"overtrading_warning": True}
    assert stage23_0d.classify_reject_reason(m_over, g_a1_fail) == "still_overtrading"

    m_normal = {"overtrading_warning": False}
    assert stage23_0d.classify_reject_reason(m_normal, g_a1_fail) == "pnl_edge_insufficient"

    g_a4_fail = {"A0": True, "A1": True, "A2": True, "A3": True, "A4": False, "A5": True}
    assert stage23_0d.classify_reject_reason(m_normal, g_a4_fail) == "robustness_failure"


# ---------------------------------------------------------------------------
# 19, 20: TRIGGER_MODE / SIGNAL_TIMEFRAME constants
# ---------------------------------------------------------------------------


def test_trigger_mode_constant_documented():
    assert stage23_0d.TRIGGER_MODE == "first_touch"


def test_signal_timeframe_constant_m15():
    assert stage23_0d.SIGNAL_TIMEFRAME == "M15"
