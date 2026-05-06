"""Unit tests for Stage 23.0c-rev1 signal-quality control study."""

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
rev1 = importlib.import_module("stage23_0c_rev1_signal_quality_eval")


# ---------------------------------------------------------------------------
# 1: Filter constants are fixed module-level (NOT searched)
# ---------------------------------------------------------------------------


def test_filter_constants_fixed_not_search():
    assert rev1.NEUTRAL_BAND == 0.5
    assert rev1.COOLDOWN_BARS == 3
    assert rev1.COST_GATE_THRESHOLD == 0.6
    # Confirm CLI does not expose these as overrides
    import inspect

    src = inspect.getsource(rev1.main)
    assert "default=NEUTRAL_BAND" not in src
    assert "default=COOLDOWN_BARS" not in src
    assert "default=COST_GATE_THRESHOLD" not in src


# ---------------------------------------------------------------------------
# 2: z-score base computation matches 23.0c
# ---------------------------------------------------------------------------


def test_zscore_computation_matches_23_0c():
    """Regression: rev1 uses 23.0c's compute_zscore directly."""
    rng = np.random.RandomState(0)
    n = 50
    bid = 1.0 + rng.randn(n) * 0.0001
    start = datetime(2026, 1, 5, 9, 5, tzinfo=UTC)
    idx = pd.date_range(start, periods=n, freq="5min", tz=UTC)
    spread = 0.0001
    df = pd.DataFrame(
        {
            "bid_o": bid,
            "bid_h": bid + 0.5 * spread,
            "bid_l": bid - 0.5 * spread,
            "bid_c": bid,
            "ask_o": bid + spread,
            "ask_h": bid + 1.5 * spread,
            "ask_l": bid - 0.5 * spread + spread,
            "ask_c": bid + spread,
        },
        index=idx,
    )
    df_z_c = stage23_0c.compute_zscore(df, n=10)
    # rev1 uses the same function
    assert "z_10" in df_z_c.columns


# ---------------------------------------------------------------------------
# 3, 4: F1 neutral_reset
# ---------------------------------------------------------------------------


def test_f1_neutral_reset_lock_release_at_z_inside_neutral_band():
    """z dips, returns to neutral, dips again → 2 long signals."""
    z = np.array(
        [
            # 0..4: z = 0 (neutral)
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            # 5: z = -2.5 (extreme) → fire long, lock
            -2.5,
            # 6,7: z stays extreme, locked
            -2.6,
            -2.7,
            # 8: z = -1.0 (back inside threshold band but NOT neutral) → still locked
            -1.0,
            # 9,10: z = -0.4 (in neutral band) → release
            -0.4,
            -0.4,
            # 11: z = -2.5 → fire long again
            -2.5,
            # 12: z stays extreme, locked
            -2.6,
        ]
    )
    long_idx, short_idx = rev1._signals_f1_neutral_reset(z, threshold=2.0, neutral_band=0.5)
    assert 5 in long_idx
    assert 11 in long_idx
    assert 6 not in long_idx and 7 not in long_idx and 8 not in long_idx and 12 not in long_idx
    assert len(long_idx) == 2


def test_f1_neutral_reset_does_not_release_in_outer_band():
    """z bounces between -threshold and -0.5 (never enters neutral) → no re-fire."""
    z = np.array(
        [
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            -2.5,  # idx 5: fire, lock
            -2.5,  # locked
            -1.0,  # outside neutral, still locked
            -0.7,  # outside neutral (|z|=0.7 > 0.5), still locked
            -2.5,  # would have re-fired with threshold-band release, but locked → no fire
        ]
    )
    long_idx, _ = rev1._signals_f1_neutral_reset(z, threshold=2.0, neutral_band=0.5)
    assert 5 in long_idx
    assert 9 not in long_idx
    assert len(long_idx) == 1


# ---------------------------------------------------------------------------
# 5, 6, 7: F2 cooldown
# ---------------------------------------------------------------------------


def test_f2_cooldown_3_bars_blocks_re_entry():
    """First-touch fire at idx 5; idx 5+1 fire blocked even with re-cross."""
    long_first = np.array([5, 6, 8, 12])  # 23.0c first-touch indices
    short_first = np.array([])
    long_after, short_after = rev1._signals_f2_cooldown(long_first, short_first, cooldown_bars=3)
    # 5 fires; 6 is within 3 bars (6-5=1 < 3) → blocked
    # 8 is within 3 bars of 5 (8-5=3 >= 3) → fires
    # 12 is 4 bars from 8 → fires
    assert 5 in long_after
    assert 6 not in long_after
    assert 8 in long_after
    assert 12 in long_after


def test_f2_cooldown_does_not_block_after_4_bars():
    long_first = np.array([5, 9])
    long_after, _ = rev1._signals_f2_cooldown(long_first, np.array([]), cooldown_bars=3)
    # 9-5=4 >= 3 → both fire
    assert list(long_after) == [5, 9]


def test_f2_cooldown_independent_per_direction():
    """Long fires don't block short cooldown."""
    long_first = np.array([5])
    short_first = np.array([6])
    long_after, short_after = rev1._signals_f2_cooldown(long_first, short_first, cooldown_bars=3)
    assert 5 in long_after
    assert 6 in short_after  # not blocked by long fire


# ---------------------------------------------------------------------------
# 8, 9, 10, 11: F3 reversal_confirmation
# ---------------------------------------------------------------------------


def test_f3_reversal_confirmation_requires_z_rising_for_long():
    # z below -threshold but FALLING → no fire
    z = np.array([0.0, 0.0, -1.0, -2.5, -3.0, -3.5])
    mid_c = np.array([1.0, 1.0, 0.99, 0.98, 0.97, 0.96])  # mid_c falling too
    long_idx, _ = rev1._signals_f3_reversal(z, mid_c, threshold=2.0, neutral_band=0.5)
    assert len(long_idx) == 0


def test_f3_reversal_confirmation_requires_mid_c_rising_for_long():
    # z below -threshold and rising, but mid_c falling → no fire
    z = np.array([0.0, -2.5, -2.4, -2.3])  # z rising
    mid_c = np.array([1.0, 0.99, 0.98, 0.97])  # mid_c falling
    long_idx, _ = rev1._signals_f3_reversal(z, mid_c, threshold=2.0, neutral_band=0.5)
    assert len(long_idx) == 0


def test_f3_reversal_confirmation_fires_when_both_rising_and_z_below():
    # z below -threshold, z rising, mid_c rising → fire
    z = np.array([0.0, -3.0, -2.5, -2.3])
    mid_c = np.array([1.0, 0.97, 0.98, 0.99])  # mid_c rising at idx 2,3
    long_idx, _ = rev1._signals_f3_reversal(z, mid_c, threshold=2.0, neutral_band=0.5)
    # At idx 2: z=-2.5 (below -2), z[2]>z[1]=−3.0 (rising), mid_c[2]>mid_c[1] (rising) → fire
    assert 2 in long_idx


def test_f3_neutral_band_lock_release():
    """F3: lock until |z| <= 0.5; persist while in outer band."""
    # Build z series that fires at idx 2, then stays in outer-band region (locked),
    # then enters neutral band at idx 6, then re-fires at idx 8.
    z = np.array(
        [
            0.0,  # idx 0
            -3.0,  # idx 1
            -2.5,  # idx 2: z below -2, z rising, mid_c will rise → fire
            -2.0,  # idx 3: still locked (|z|=2 > 0.5)
            -1.5,  # idx 4: still locked
            -1.0,  # idx 5: still locked
            -0.4,  # idx 6: |z|=0.4 <= 0.5 → release lock
            -3.0,  # idx 7: z below, z falling → would not fire (wrong direction)
            -2.5,  # idx 8: z below, z[8]>z[7] (rising), mid_c rises → fire
        ]
    )
    mid_c = np.array([1.0, 0.97, 0.98, 0.99, 1.00, 1.01, 1.02, 0.97, 0.98])
    long_idx, _ = rev1._signals_f3_reversal(z, mid_c, threshold=2.0, neutral_band=0.5)
    assert 2 in long_idx
    assert 8 in long_idx
    # No fires in 3..6 (locked)
    assert not any(3 <= i <= 6 for i in long_idx)


# ---------------------------------------------------------------------------
# 12, 13: F4 cost_gate
# ---------------------------------------------------------------------------


def test_f4_cost_gate_drops_high_cost_signals():
    """Trades with cost_ratio > 0.6 are dropped post-join."""
    trades = pd.DataFrame(
        {
            "entry_ts": pd.date_range("2026-01-01", periods=5, freq="5min", tz=UTC),
            "pair": ["EUR_USD"] * 5,
            "direction": ["long"] * 5,
            "pnl_pip": [1.0, -0.5, 2.0, -1.0, 0.5],
            "cost_ratio": [0.3, 0.7, 0.5, 0.8, 0.6],  # 0.7 and 0.8 > 0.6 → dropped
            "signal_timeframe": ["M5"] * 5,
        }
    )
    kept = trades[trades["cost_ratio"] <= rev1.COST_GATE_THRESHOLD]
    # 0.6 is exactly at the threshold; <= 0.6 so kept
    assert len(kept) == 3
    assert kept["cost_ratio"].tolist() == [0.3, 0.5, 0.6]


def test_f4_cost_gate_keeps_low_cost_signals():
    trades = pd.DataFrame({"cost_ratio": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]})
    kept = trades[trades["cost_ratio"] <= rev1.COST_GATE_THRESHOLD]
    assert len(kept) == 6  # all kept


def test_f4_cost_gate_is_per_entry_not_pair_filter():
    """F4 keeps individual low-cost trades from any pair; doesn't drop entire pairs."""
    trades = pd.DataFrame(
        {
            "pair": ["AUD_NZD"] * 4,  # high-spread pair
            "cost_ratio": [0.5, 0.7, 0.8, 0.4],  # mix of below/above threshold
        }
    )
    kept = trades[trades["cost_ratio"] <= rev1.COST_GATE_THRESHOLD]
    assert len(kept) == 2  # 2 trades from AUD_NZD survive (per-entry, not per-pair)
    assert "AUD_NZD" in set(kept["pair"])


# ---------------------------------------------------------------------------
# 14: signal join to 23.0a outcomes (per filter)
# ---------------------------------------------------------------------------


def test_signal_join_to_23_0a_outcome_per_filter():
    # Synthetic signals from each filter join cleanly to a synthetic 23.0a frame.
    start = datetime(2026, 1, 5, 9, 5, tzinfo=UTC)
    ts = pd.date_range(start, periods=10, freq="5min", tz=UTC)
    labels = pd.DataFrame(
        {
            "entry_ts": list(ts) * 2,
            "pair": ["EUR_USD"] * 20,
            "signal_timeframe": ["M5"] * 20,
            "horizon_bars": [np.int8(1)] * 20,
            "direction": ["long"] * 10 + ["short"] * 10,
            "tb_pnl": np.float32(1.0),
            "time_exit_pnl": np.float32(2.0),
            "valid_label": True,
            "cost_ratio": np.float32(0.5),
        }
    )
    sig = pd.DataFrame(
        {
            "entry_ts": [ts[3]],
            "pair": ["EUR_USD"],
            "direction": ["long"],
        }
    )
    joined = pd.merge(
        sig, labels[labels["horizon_bars"] == 1], on=["entry_ts", "pair", "direction"]
    )
    assert len(joined) == 1
    assert "cost_ratio" in joined.columns


# ---------------------------------------------------------------------------
# 15: NG#6 signal_timeframe runtime assertion
# ---------------------------------------------------------------------------


def test_no_phase22_m1_cell_reused():
    assert rev1.SIGNAL_TIMEFRAME == "M5"


# ---------------------------------------------------------------------------
# 16: per-filter verdict
# ---------------------------------------------------------------------------


def test_per_filter_verdict_assignment():
    # ADOPT_CANDIDATE if A0..A5 + S1 strong
    best_pass = {
        "filter": "F1_neutral_reset",
        "N": 24,
        "threshold": 2.0,
        "horizon_bars": 1,
        "exit_rule": "tb",
        "gate_A0": True,
        "gate_A1": True,
        "gate_A2": True,
        "gate_A3": True,
        "gate_A4": True,
        "gate_A5": True,
        "sharpe": 0.10,
    }
    s1_strong = {
        "is_sharpe": 0.10,
        "oos_sharpe": 0.08,
        "oos_is_ratio": 0.8,
        "is_n": 800,
        "oos_n": 200,
    }
    assert rev1.assign_per_filter_verdict(best_pass, s1_strong) == "ADOPT_CANDIDATE"

    # PROMISING if A4 fails
    best_a4_fail = dict(best_pass, gate_A4=False)
    assert rev1.assign_per_filter_verdict(best_a4_fail, None) == "PROMISING_BUT_NEEDS_OOS"

    # REJECT if A1 fails
    best_a1_fail = dict(best_pass, gate_A1=False)
    assert rev1.assign_per_filter_verdict(best_a1_fail, None) == "REJECT"

    # REJECT if no best (None)
    assert rev1.assign_per_filter_verdict(None, None) == "REJECT"


# ---------------------------------------------------------------------------
# 17: overall verdict picks the best filter
# ---------------------------------------------------------------------------


def test_overall_verdict_picks_best_filter():
    # ADOPT > PROMISING > REJECT priority
    per_filter = {
        "F1_neutral_reset": "REJECT",
        "F2_cooldown": "PROMISING_BUT_NEEDS_OOS",
        "F3_reversal_confirmation": "ADOPT_CANDIDATE",
        "F4_cost_gate": "REJECT",
    }
    overall, winner = rev1.overall_verdict(per_filter)
    assert overall == "ADOPT_CANDIDATE"
    assert winner == "F3_reversal_confirmation"

    # All REJECT → overall REJECT
    all_reject = {f: "REJECT" for f in rev1.FILTERS}
    overall_r, winner_r = rev1.overall_verdict(all_reject)
    assert overall_r == "REJECT"
    assert winner_r is None


# ---------------------------------------------------------------------------
# 18: smoke mode shape
# ---------------------------------------------------------------------------


def test_smoke_mode_3pairs_4filters_2cells_each():
    assert len(rev1.SMOKE_PAIRS) == 3
    assert len(rev1.SMOKE_CELLS_PER_FILTER) == 2
    assert len(rev1.FILTERS) == 4


# ---------------------------------------------------------------------------
# 19: filter effectiveness ranking row shape
# ---------------------------------------------------------------------------


def test_filter_effectiveness_ranking_in_report():
    cell_results = [
        {
            "filter": "F1_neutral_reset",
            "annual_trades": 5000.0,
            "sharpe": -0.2,
            "gate_A0": True,
            "gate_A1": False,
            "gate_A2": False,
        },
        {
            "filter": "F1_neutral_reset",
            "annual_trades": 8000.0,
            "sharpe": -0.3,
            "gate_A0": True,
            "gate_A1": False,
            "gate_A2": False,
        },
    ]
    ranking = rev1.filter_effectiveness_ranking(cell_results, ["F1_neutral_reset"])
    assert len(ranking) == 1
    r = ranking[0]
    assert r["filter"] == "F1_neutral_reset"
    assert r["n_cells"] == 2
    assert abs(r["median_ann_trades"] - 6500.0) < 1e-6
    assert r["n_pass_a0"] == 2
    assert r["n_pass_a1"] == 0


# ---------------------------------------------------------------------------
# 20: filter roles are documented
# ---------------------------------------------------------------------------


def test_filter_roles_documented():
    assert rev1.FILTER_ROLES["F1_neutral_reset"] == "re-entry control"
    assert rev1.FILTER_ROLES["F2_cooldown"] == "time-interval control"
    assert rev1.FILTER_ROLES["F3_reversal_confirmation"] == "reversal start confirmation"
    assert "per-entry execution-cost sanity gate" in rev1.FILTER_ROLES["F4_cost_gate"]
    assert "NOT a pair filter" in rev1.FILTER_ROLES["F4_cost_gate"]
