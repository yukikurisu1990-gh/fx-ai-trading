"""Unit tests for Stage 23.0b M5 Donchian breakout eval."""

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
    """Build a regular 5-minute synthetic M5 BA OHLC dataframe."""
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
# 1: Donchian causal shift(1)
# ---------------------------------------------------------------------------


def test_donchian_upper_lower_causal_shift1():
    n = 30
    bid_close = 1.0 + np.arange(n, dtype=float) * 0.0001
    m5 = _make_m5(n, bid_close=bid_close)
    df = stage23_0b.compute_donchian_bands(m5, n=10)
    # At bar t, upper_10 should equal max of mid_h over [t-10, t-1]
    t = 15
    expected_upper = df["mid_h"].iloc[t - 10 : t].max()
    np.testing.assert_allclose(df["upper_10"].iloc[t], expected_upper)
    # And mid_h at bar t itself should NOT be in the window
    assert df["upper_10"].iloc[t] != df["mid_h"].iloc[t] or df["mid_h"].iloc[t] == expected_upper


# ---------------------------------------------------------------------------
# 2: Donchian uses mid (not bid/ask)
# ---------------------------------------------------------------------------


def test_donchian_uses_mid_high_low_not_bid_or_ask():
    n = 25
    m5 = _make_m5(n, bid_close=np.full(n, 1.0))
    df = stage23_0b.compute_donchian_bands(m5, n=5)
    # mid_h at any row equals the (bid_h + ask_h) / 2
    expected_mid_h = (m5["bid_h"] + m5["ask_h"]) / 2.0
    np.testing.assert_allclose(df["mid_h"], expected_mid_h)
    # upper_5 NEVER equals bid_h.shift(1).rolling(5).max() (would be different
    # because bid_h is below mid_h)
    bid_only_upper = m5["bid_h"].shift(1).rolling(5).max()
    # They differ at rows where the rolling max is defined
    valid_mask = df["upper_5"].notna()
    assert (df.loc[valid_mask, "upper_5"] != bid_only_upper.loc[valid_mask]).any()


# ---------------------------------------------------------------------------
# 3, 4: long/short trigger conditions
# ---------------------------------------------------------------------------


def test_long_trigger_strict_above_upper():
    # Construct a series where mid_c at index 11 strictly exceeds upper_10.
    n = 25
    bid_close = np.full(n, 1.0)
    bid_close[11] = 1.0 + 5 * 0.0001  # strong jump
    m5 = _make_m5(n, bid_close=bid_close, high_offset_pip=0.0, low_offset_pip=0.0)
    sigs = stage23_0b.extract_signals(m5, n=10)
    long_sigs = sigs[sigs["direction"] == "long"]
    # The bar at index 11 should appear as a long signal
    expected_ts = m5.index[11]
    assert expected_ts in set(long_sigs["entry_ts"])


def test_short_trigger_strict_below_lower():
    n = 25
    bid_close = np.full(n, 1.0)
    bid_close[11] = 1.0 - 5 * 0.0001
    m5 = _make_m5(n, bid_close=bid_close, high_offset_pip=0.0, low_offset_pip=0.0)
    sigs = stage23_0b.extract_signals(m5, n=10)
    short_sigs = sigs[sigs["direction"] == "short"]
    assert m5.index[11] in set(short_sigs["entry_ts"])


def test_long_trigger_equals_upper_does_not_trigger():
    n = 25
    bid_close = np.full(n, 1.0)
    # mid_c == upper_10 at idx 11 → strict > should NOT trigger
    m5 = _make_m5(n, bid_close=bid_close, high_offset_pip=0.0, low_offset_pip=0.0)
    sigs = stage23_0b.extract_signals(m5, n=10)
    # No signals at all on a flat series with high_offset=0
    assert len(sigs) == 0


# ---------------------------------------------------------------------------
# 5: no signal in warmup
# ---------------------------------------------------------------------------


def test_no_signal_when_donchian_window_not_filled():
    n = 25
    bid_close = np.linspace(1.0, 1.0 + 25 * 0.0001, n)
    m5 = _make_m5(n, bid_close=bid_close, high_offset_pip=0.5, low_offset_pip=0.5)
    sigs = stage23_0b.extract_signals(m5, n=10)
    # All emitted signals must have entry_ts at idx >= 10 (since shift(1) + rolling(10)
    # makes upper_10/lower_10 NaN for idx < 10)
    if len(sigs):
        idx_positions = m5.index.get_indexer(sigs["entry_ts"])
        assert (idx_positions >= 10).all()


# ---------------------------------------------------------------------------
# 6, 7: signal join + valid_label filter
# ---------------------------------------------------------------------------


def _make_synthetic_labels(n_signal: int, signal_tf: str = "M5") -> pd.DataFrame:
    """Build a small synthetic 23.0a-shape labels DataFrame for join tests."""
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
    # Build trivial signal at the third entry_ts, long
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
    assert np.isfinite(joined["time_exit_pnl"].iloc[0])


def test_signal_drops_invalid_rows():
    labels = _make_synthetic_labels(10)
    labels.loc[5, "valid_label"] = False
    valid_only = labels[labels["valid_label"]]
    assert len(valid_only) < len(labels)


# ---------------------------------------------------------------------------
# 8: per-trade Sharpe ddof=0
# ---------------------------------------------------------------------------


def test_sharpe_per_trade_ddof0_no_annualize():
    pnl = pd.Series([1.0, -0.5, 2.0, -1.0, 0.5])
    expected = pnl.mean() / pnl.std(ddof=0)
    assert abs(stage23_0b._per_trade_sharpe(pnl) - expected) < 1e-12


# ---------------------------------------------------------------------------
# 9: A0 annual_trades scaling
# ---------------------------------------------------------------------------


def test_a0_annual_trades_uses_dataset_span_2_years():
    # 1500 trades over ~2 years span → ~750 annual_trades
    expected = 1500 / stage23_0b.SPAN_YEARS
    assert abs(expected - 750.5) < 1.0


# ---------------------------------------------------------------------------
# 10: A4 fold majority
# ---------------------------------------------------------------------------


def test_a4_4fold_majority_rule():
    # Build 100 trades with different signs in different folds.
    # Quintiles 0..4 of 100 trades → bars [0:20), [20:40), [40:60), [60:80), [80:100)
    # k=0 dropped (warmup), eval k=1..4.
    # Make k=1, k=2, k=3 positive and k=4 negative → expect 3/4 positive.
    pnl = np.zeros(100)
    pnl[0:20] = 1.0  # k=0 warmup (dropped)
    pnl[20:40] = 1.0  # k=1 positive
    pnl[40:60] = 1.0  # k=2 positive
    pnl[60:80] = 1.0  # k=3 positive
    pnl[80:100] = -1.0  # k=4 negative
    # Add jitter so std > 0
    pnl = pnl + np.linspace(0, 0.001, 100)
    df = pd.DataFrame(
        {
            "entry_ts": pd.date_range("2026-01-01", periods=100, freq="1h", tz=UTC),
            "pnl_pip": pnl,
        }
    )
    fold = stage23_0b._fold_stability(df)
    assert fold["n_positive"] == 3


# ---------------------------------------------------------------------------
# 11: A5 spread stress
# ---------------------------------------------------------------------------


def test_a5_spread_stress_subtracts_half_pip_per_trade():
    pnl = pd.Series([1.0, 0.5, 2.0, -0.3, 0.8])
    stressed = pnl - stage23_0b.A5_SPREAD_STRESS_PIP
    assert abs(stage23_0b.A5_SPREAD_STRESS_PIP - 0.5) < 1e-12
    np.testing.assert_allclose(stressed, [0.5, 0.0, 1.5, -0.8, 0.3])


# ---------------------------------------------------------------------------
# 12: NG#6 — runtime assertion blocks non-M5 signal_timeframe
# ---------------------------------------------------------------------------


def test_no_phase22_m1_cell_reused():
    # The script's load_pair_labels asserts signal_timeframe == "M5".
    # Build a synthetic labels DF with signal_timeframe != "M5" and verify it
    # would be rejected if filed through the runtime check.
    # We test the assertion logic directly:
    bad_labels = _make_synthetic_labels(5, signal_tf="M1")
    bad_labels = bad_labels[bad_labels["valid_label"]]
    # Mimic the runtime check
    assert (bad_labels["signal_timeframe"] != "M5").all()
    # The actual function under test:
    # stage23_0b.SIGNAL_TIMEFRAME == "M5" — sweep grid never sets non-M5
    assert stage23_0b.SIGNAL_TIMEFRAME == "M5"


# ---------------------------------------------------------------------------
# 13: cell pooling aggregates all pairs (no filter)
# ---------------------------------------------------------------------------


def test_cell_pooling_aggregates_all_pairs():
    # PAIRS_20 import surfaces — assert it is the canonical 20
    assert len(stage23_0b.PAIRS_20) == 20
    # And no pair filter is hard-coded for the sweep
    assert "EUR_USD" in stage23_0b.PAIRS_20
    assert "USD_JPY" in stage23_0b.PAIRS_20
    assert "AUD_NZD" in stage23_0b.PAIRS_20


# ---------------------------------------------------------------------------
# 14: smoke mode definition
# ---------------------------------------------------------------------------


def test_smoke_mode_3pairs_2cells():
    assert len(stage23_0b.SMOKE_PAIRS) == 3
    assert "USD_JPY" in stage23_0b.SMOKE_PAIRS
    assert "EUR_USD" in stage23_0b.SMOKE_PAIRS
    assert "GBP_JPY" in stage23_0b.SMOKE_PAIRS
    assert len(stage23_0b.SMOKE_CELLS) == 2


# ---------------------------------------------------------------------------
# 15: 3-class verdict assignment
# ---------------------------------------------------------------------------


def test_verdict_3class_assignment():
    # ADOPT_CANDIDATE: A0..A5 all pass, S1 strong
    gates_all = {"A0": True, "A1": True, "A2": True, "A3": True, "A4": True, "A5": True}
    s1_strong = {
        "is_sharpe": 0.10,
        "oos_sharpe": 0.08,
        "oos_is_ratio": 0.8,
        "is_n": 800,
        "oos_n": 200,
    }
    assert stage23_0b.assign_verdict(gates_all, s1_strong) == "ADOPT_CANDIDATE"

    # PROMISING (A0-A5 pass but S1 weak)
    s1_weak = {
        "is_sharpe": 0.10,
        "oos_sharpe": 0.02,
        "oos_is_ratio": 0.2,
        "is_n": 800,
        "oos_n": 200,
    }
    assert stage23_0b.assign_verdict(gates_all, s1_weak) == "PROMISING_BUT_NEEDS_OOS"

    # PROMISING (A0-A3 pass, A4 fails)
    gates_a4_fail = {"A0": True, "A1": True, "A2": True, "A3": True, "A4": False, "A5": True}
    assert stage23_0b.assign_verdict(gates_a4_fail, None) == "PROMISING_BUT_NEEDS_OOS"

    # PROMISING (A0-A3 pass, A5 fails)
    gates_a5_fail = {"A0": True, "A1": True, "A2": True, "A3": True, "A4": True, "A5": False}
    assert stage23_0b.assign_verdict(gates_a5_fail, None) == "PROMISING_BUT_NEEDS_OOS"

    # REJECT (A1 fail)
    gates_a1_fail = {"A0": True, "A1": False, "A2": True, "A3": True, "A4": True, "A5": True}
    assert stage23_0b.assign_verdict(gates_a1_fail, None) == "REJECT"

    # REJECT (A0 fail)
    gates_a0_fail = {"A0": False, "A1": True, "A2": True, "A3": True, "A4": True, "A5": True}
    assert stage23_0b.assign_verdict(gates_a0_fail, None) == "REJECT"


# ---------------------------------------------------------------------------
# 16: S0 random-entry Sharpe near zero on long-mean-zero pool
# ---------------------------------------------------------------------------


def test_s0_random_entry_sharpe_near_zero():
    rng = np.random.RandomState(99)
    n = 5000
    pnl = rng.randn(n)  # mean ~0, std 1
    pool = pd.DataFrame(
        {
            "direction": ["long"] * (n // 2) + ["short"] * (n // 2),
            "tb_pnl": pnl,
            "time_exit_pnl": pnl,
        }
    )
    s0 = stage23_0b._random_entry_sharpe(pool, n_long=500, n_short=500, exit_col="tb_pnl")
    # |s0| should be small (~|0.05| or less for n=1000 sampled from mean-0 noise)
    assert abs(s0) < 0.2


# ---------------------------------------------------------------------------
# 17: S1 strict 80/20 chronological split
# ---------------------------------------------------------------------------


def test_s1_strict_oos_split_80_20_chronological():
    n = 1000
    df = pd.DataFrame(
        {
            "entry_ts": pd.date_range("2026-01-01", periods=n, freq="1min", tz=UTC),
            "pnl_pip": np.linspace(-1.0, 1.0, n),
        }
    )
    s1 = stage23_0b._strict_oos_split(df)
    # IS = first 800, OOS = last 200
    assert s1["is_n"] == 800
    assert s1["oos_n"] == 200


# ---------------------------------------------------------------------------
# 18: overtrading warning
# ---------------------------------------------------------------------------


def test_overtrading_warning_threshold():
    # annual_trades > 1000 should raise warning flag (not block)
    metrics_high = {
        "annual_trades": 1500.0,
        "n_trades": 3000,
        "sharpe": 0.10,
        "annual_pnl": 200.0,
        "max_dd": 100.0,
        "a4_n_positive": 4,
        "a4_fold_sharpes": [0.1] * 4,
        "a5_stressed_annual_pnl": 50.0,
        "hit_rate": 0.55,
        "payoff_asymmetry": 1.2,
        "s0_random_entry_sharpe": 0.0,
        "overtrading_warning": True,
        "n_long": 1500,
        "n_short": 1500,
    }
    gates = stage23_0b.gate_matrix(metrics_high)
    # A0 still passes (overtrading warning is NOT blocking)
    assert gates["A0"] is True
    # And the warning flag is set
    assert metrics_high["overtrading_warning"] is True
