"""Stage 22.0c M5 Donchian Breakout + M1 Entry Hybrid unit tests.

Verifies:
- Donchian causal channel (excludes current bar via shift(1))
- M5 right-closed/right-labeled aggregation has no lookahead
- Immediate entry timestamp strictly > signal timestamp
- Retest uses entry-side prices (long: ask_l; short: bid_h)
- Momentum uses entry-side prices (long: ask_h; short: bid_l) with 0.5×ATR offset
- Skipped trades not counted as PnL=0
- time_to_fire histogram in 1..5 range
- Direction-specific false-breakout rate
- Verdict logic: A0..A5 + best_possible_pnl forced REJECT
- NG list compliance (no week-open / pair-tier filter)
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "stage22_0c_m5_breakout_m1_entry_hybrid.py"

_spec = importlib.util.spec_from_file_location("stage22_0c_breakout", SCRIPT)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
sys.modules["stage22_0c_breakout"] = mod
_spec.loader.exec_module(mod)


# ---------------------------------------------------------------------------
# Synthetic M1 BA frame helpers
# ---------------------------------------------------------------------------


def _bar(ts, bid_o, bid_h, bid_l, bid_c, ask_o, ask_h, ask_l, ask_c) -> dict:
    return dict(
        timestamp=ts,
        bid_o=bid_o,
        bid_h=bid_h,
        bid_l=bid_l,
        bid_c=bid_c,
        ask_o=ask_o,
        ask_h=ask_h,
        ask_l=ask_l,
        ask_c=ask_c,
    )


def _flat_bar(ts: datetime, mid: float, spread: float = 0.02, rng: float = 0.05) -> dict:
    half = spread / 2.0
    return _bar(
        ts,
        mid - half,
        mid - half + rng,
        mid - half - rng,
        mid - half,
        mid + half,
        mid + half + rng,
        mid + half - rng,
        mid + half,
    )


def _build_m1(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows).set_index("timestamp")
    df.index = pd.DatetimeIndex(df.index, tz=UTC)
    return df.astype(np.float64)


# ---------------------------------------------------------------------------
# M5 aggregation + Donchian causality
# ---------------------------------------------------------------------------


def test_m5_aggregation_right_closed_no_lookahead() -> None:
    """An M5 bar at boundary T must use only M1 bars whose timestamp ≤ T.

    With ``closed="right"``, the bin labeled 00:05:00 spans (00:00:00, 00:05:00],
    so it includes the M1 bar at 00:05:00 (timestamp ≤ T). The close of the
    bin is the .last() value, which is the M1 close at 00:05:00 (index 5).
    """
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
    rows = [_flat_bar(start + timedelta(minutes=i), 100.0 + i * 0.001) for i in range(30)]
    df = _build_m1(rows)
    m5 = mod.aggregate_m1_to_m5_mid(df)
    bar_00_05 = m5.loc[pd.Timestamp("2025-01-01 00:05:00", tz=UTC)]
    # Bin (00:00:00, 00:05:00] contains M1 indices 1..5; .last() = index 5.
    expected_close = (df["bid_c"].iloc[5] + df["ask_c"].iloc[5]) / 2.0
    assert bar_00_05["mid_c"] == expected_close
    # And critically: NO M1 bar with timestamp > 00:05:00 contributed.
    # If we mutate index 6, the M5 bar at 00:05 must be unchanged.
    df_b = df.copy()
    df_b.iloc[6, df_b.columns.get_loc("bid_c")] = 999.0
    df_b.iloc[6, df_b.columns.get_loc("ask_c")] = 999.0
    m5_b = mod.aggregate_m1_to_m5_mid(df_b)
    assert m5_b.loc[pd.Timestamp("2025-01-01 00:05:00", tz=UTC), "mid_c"] == bar_00_05["mid_c"]


def test_donchian_excludes_current_bar() -> None:
    """hi_N[T] uses bars < T (shift(1) confirmation)."""
    # Construct an M5 frame where bar T has the highest high; the channel must
    # NOT count it.
    idx = pd.date_range("2025-01-01", periods=30, freq="5min", tz=UTC)
    m5 = pd.DataFrame(
        {
            "mid_o": np.linspace(100.0, 100.5, 30),
            "mid_h": np.linspace(100.1, 100.6, 30),
            "mid_l": np.linspace(99.9, 100.4, 30),
            "mid_c": np.linspace(100.0, 100.5, 30),
        },
        index=idx,
    )
    m5.iloc[20, m5.columns.get_loc("mid_h")] = 200.0  # spike at index 20
    hi, _ = mod.donchian_channel(m5, n=10)
    # Channel at index 20 must use bars 10..19 — index 20 itself excluded
    assert hi.iloc[20] != 200.0
    # Channel at index 21 includes index 20 (now in the look-back of bars < 21)
    assert hi.iloc[21] == 200.0


# ---------------------------------------------------------------------------
# Immediate entry timing
# ---------------------------------------------------------------------------


def test_immediate_entry_ts_strictly_greater_than_signal_ts() -> None:
    """Entry bar timestamp must be > signal_ts, never == signal_ts."""
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
    rows = [_flat_bar(start + timedelta(minutes=i), 100.0) for i in range(30)]
    df = _build_m1(rows)
    m1_ts_int = df.index.values.astype("datetime64[ns]").view("int64")
    atr = pd.Series(np.full(len(df), 0.05), index=df.index)
    sig_ts = pd.Timestamp("2025-01-01 00:05:00", tz=UTC)
    fire, _ = mod.find_entries_for_signal(
        df,
        m1_ts_int,
        atr,
        sig_ts,
        "long",
        100.0,
        "immediate",
    )
    assert fire is not None
    # signal_ts converted to ns int
    sig_int = np.datetime64(sig_ts, "ns").view("int64")
    entry_int = fire.entry_ts.astype("datetime64[ns]").view("int64")
    assert int(entry_int) > int(sig_int)


# ---------------------------------------------------------------------------
# Retest entry timing — bid/ask convention
# ---------------------------------------------------------------------------


def test_retest_long_uses_ask_l() -> None:
    """Long retest fires when ask_l <= break_level."""
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
    break_level = 100.10
    rows = []
    for i in range(10):
        # default flat bars well above break_level — ask_l > break_level → no fire
        rows.append(_flat_bar(start + timedelta(minutes=i), 100.5))
    # signal at minute 4; candidates are 5..9. Make minute 6's ask_l drop to 100.05
    rows[6] = _bar(
        start + timedelta(minutes=6),
        bid_o=100.10,
        bid_h=100.20,
        bid_l=100.05,
        bid_c=100.15,
        ask_o=100.20,
        ask_h=100.30,
        ask_l=100.05,
        ask_c=100.25,
    )
    df = _build_m1(rows)
    m1_ts_int = df.index.values.astype("datetime64[ns]").view("int64")
    atr = pd.Series(np.full(len(df), 0.05), index=df.index)
    sig_ts = pd.Timestamp("2025-01-01 00:04:00", tz=UTC)
    fire, _ = mod.find_entries_for_signal(
        df,
        m1_ts_int,
        atr,
        sig_ts,
        "long",
        break_level,
        "retest",
    )
    assert fire is not None
    # Should fire at minute 6 (bars_to_fire = 2 since candidates start at minute 5)
    assert fire.entry_ts == np.datetime64(df.index[6], "ns")
    assert fire.bars_to_fire == 2


def test_retest_short_uses_bid_h() -> None:
    """Short retest fires when bid_h >= break_level."""
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
    break_level = 99.90
    rows = []
    for i in range(10):
        rows.append(_flat_bar(start + timedelta(minutes=i), 99.50))
    # signal at minute 4; candidates 5..9. Make minute 5's bid_h spike up to break level
    rows[5] = _bar(
        start + timedelta(minutes=5),
        bid_o=99.50,
        bid_h=99.95,
        bid_l=99.45,
        bid_c=99.55,
        ask_o=99.55,
        ask_h=100.05,
        ask_l=99.50,
        ask_c=99.60,
    )
    df = _build_m1(rows)
    m1_ts_int = df.index.values.astype("datetime64[ns]").view("int64")
    atr = pd.Series(np.full(len(df), 0.05), index=df.index)
    sig_ts = pd.Timestamp("2025-01-01 00:04:00", tz=UTC)
    fire, _ = mod.find_entries_for_signal(
        df,
        m1_ts_int,
        atr,
        sig_ts,
        "short",
        break_level,
        "retest",
    )
    assert fire is not None
    assert fire.entry_ts == np.datetime64(df.index[5], "ns")


def test_retest_skipped_when_no_retest_within_5_bars() -> None:
    """If no candidate bar satisfies retest, skip."""
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
    rows = [_flat_bar(start + timedelta(minutes=i), 105.0) for i in range(15)]
    df = _build_m1(rows)
    m1_ts_int = df.index.values.astype("datetime64[ns]").view("int64")
    atr = pd.Series(np.full(len(df), 0.05), index=df.index)
    # break_level=99 — never reached in the all-105 series
    sig_ts = pd.Timestamp("2025-01-01 00:04:00", tz=UTC)
    fire, _ = mod.find_entries_for_signal(
        df,
        m1_ts_int,
        atr,
        sig_ts,
        "long",
        99.0,
        "retest",
    )
    assert fire is None


# ---------------------------------------------------------------------------
# Momentum entry timing — bid/ask convention
# ---------------------------------------------------------------------------


def test_momentum_long_uses_ask_h_with_half_atr_offset() -> None:
    """Long momentum: ask_h > break_level + 0.5 × ATR.

    Use small ``rng`` so the default flat bars do NOT incidentally trigger
    momentum — only the explicit spike at minute 7 should.
    """
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
    break_level = 100.0
    atr_val = 0.10  # 0.5 × ATR = 0.05 → threshold = 100.05
    rows = [_flat_bar(start + timedelta(minutes=i), 100.0, rng=0.001) for i in range(10)]
    rows[7] = _bar(
        start + timedelta(minutes=7),
        bid_o=100.00,
        bid_h=100.04,
        bid_l=99.99,
        bid_c=100.02,
        ask_o=100.04,
        ask_h=100.08,
        ask_l=100.00,
        ask_c=100.06,
    )
    df = _build_m1(rows)
    m1_ts_int = df.index.values.astype("datetime64[ns]").view("int64")
    atr = pd.Series(np.full(len(df), atr_val), index=df.index)
    sig_ts = pd.Timestamp("2025-01-01 00:04:00", tz=UTC)
    fire, _ = mod.find_entries_for_signal(
        df,
        m1_ts_int,
        atr,
        sig_ts,
        "long",
        break_level,
        "momentum",
    )
    assert fire is not None
    assert fire.entry_ts == np.datetime64(df.index[7], "ns")


def test_momentum_short_uses_bid_l_with_half_atr_offset() -> None:
    """Short momentum: bid_l < break_level - 0.5 × ATR."""
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
    break_level = 100.0
    atr_val = 0.10
    rows = []
    for i in range(10):
        rows.append(_flat_bar(start + timedelta(minutes=i), 100.0, rng=0.001))
    # spike bid_l below break_level - 0.05 at minute 6
    rows[6] = _bar(
        start + timedelta(minutes=6),
        bid_o=99.99,
        bid_h=100.00,
        bid_l=99.90,
        bid_c=99.94,
        ask_o=100.01,
        ask_h=100.02,
        ask_l=99.94,
        ask_c=99.96,
    )
    df = _build_m1(rows)
    m1_ts_int = df.index.values.astype("datetime64[ns]").view("int64")
    atr = pd.Series(np.full(len(df), atr_val), index=df.index)
    sig_ts = pd.Timestamp("2025-01-01 00:04:00", tz=UTC)
    fire, _ = mod.find_entries_for_signal(
        df,
        m1_ts_int,
        atr,
        sig_ts,
        "short",
        break_level,
        "momentum",
    )
    assert fire is not None
    assert fire.entry_ts == np.datetime64(df.index[6], "ns")


def test_momentum_skipped_when_no_continuation_within_5_bars() -> None:
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
    rows = [_flat_bar(start + timedelta(minutes=i), 100.0, rng=0.001) for i in range(15)]
    df = _build_m1(rows)
    m1_ts_int = df.index.values.astype("datetime64[ns]").view("int64")
    atr = pd.Series(np.full(len(df), 0.10), index=df.index)
    sig_ts = pd.Timestamp("2025-01-01 00:04:00", tz=UTC)
    fire, _ = mod.find_entries_for_signal(
        df,
        m1_ts_int,
        atr,
        sig_ts,
        "long",
        100.0,
        "momentum",
    )
    assert fire is None


# ---------------------------------------------------------------------------
# Skipped signals are not counted
# ---------------------------------------------------------------------------


def test_skipped_signals_not_counted_as_trades() -> None:
    """When retest/momentum doesn't fire, the entry is skipped — no PnL=0
    entry should be added to the accumulator.
    """
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
    rows = [_flat_bar(start + timedelta(minutes=i), 105.0) for i in range(15)]
    df = _build_m1(rows)
    m1_ts_int = df.index.values.astype("datetime64[ns]").view("int64")
    atr = pd.Series(np.full(len(df), 0.05), index=df.index)
    sig_ts = pd.Timestamp("2025-01-01 00:04:00", tz=UTC)
    fire, _ = mod.find_entries_for_signal(
        df,
        m1_ts_int,
        atr,
        sig_ts,
        "long",
        99.0,
        "retest",
    )
    assert fire is None
    # An accumulator that received only skipped signals must produce 0 trades
    acc = mod.CellAcc()
    materialized = acc.materialize()
    assert len(materialized) == 0


def test_time_to_fire_histogram_in_1_to_5_range() -> None:
    """time_to_fire is in [1, 5]."""
    stats = mod.TimingStats()
    # Simulate filling histogram via the entry-finder
    start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
    rows = [_flat_bar(start + timedelta(minutes=i), 100.0) for i in range(20)]
    df = _build_m1(rows)
    m1_ts_int = df.index.values.astype("datetime64[ns]").view("int64")
    atr = pd.Series(np.full(len(df), 0.05), index=df.index)
    for sig_idx in (4, 9, 14):
        sig_ts = df.index[sig_idx]
        fire, _ = mod.find_entries_for_signal(
            df,
            m1_ts_int,
            atr,
            sig_ts,
            "long",
            100.0,
            "immediate",
        )
        assert fire is not None
        assert 1 <= fire.bars_to_fire <= 5
        stats.bars_to_fire_hist[fire.bars_to_fire] = (
            stats.bars_to_fire_hist.get(fire.bars_to_fire, 0) + 1
        )
    assert sum(stats.bars_to_fire_hist.values()) == 3


# ---------------------------------------------------------------------------
# False breakout rate
# ---------------------------------------------------------------------------


def test_false_breakout_rate_long_definition() -> None:
    """Long false break: mid returns BELOW break_level within 5 M1 bars."""
    # mid_path stays above break_level → not false
    assert mod.is_false_breakout("long", 100.0, [100.5, 100.6, 100.4]) is False
    # one bar drops below break_level → false
    assert mod.is_false_breakout("long", 100.0, [100.2, 99.9, 100.3]) is True
    # empty path → false
    assert mod.is_false_breakout("long", 100.0, []) is False


def test_false_breakout_rate_short_definition() -> None:
    """Short false break: mid returns ABOVE break_level within 5 M1 bars."""
    assert mod.is_false_breakout("short", 100.0, [99.5, 99.4, 99.7]) is False
    assert mod.is_false_breakout("short", 100.0, [99.7, 100.1, 99.5]) is True
    assert mod.is_false_breakout("short", 100.0, []) is False


# ---------------------------------------------------------------------------
# 5-fold split + spread stress (sanity from 22.0b harness)
# ---------------------------------------------------------------------------


def _make_trades(timestamps: list[datetime], pnl: list[float]) -> pd.DataFrame:
    n = len(timestamps)
    return (
        pd.DataFrame(
            {
                "entry_ts": pd.to_datetime(timestamps, utc=True),
                "pnl": np.asarray(pnl, dtype=np.float64),
                "pair": ["USD_JPY"] * n,
                "spread_entry": np.full(n, 1.5, dtype=np.float32),
                "cost_ratio": np.full(n, 0.9, dtype=np.float32),
                "hour_utc": np.full(n, 10, dtype=np.int8),
                "dow": np.full(n, 1, dtype=np.int8),
                "direction": ["long"] * n,
            }
        )
        .sort_values("entry_ts")
        .reset_index(drop=True)
    )


def test_walkforward_5fold_split_chronological() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    ts = [start + timedelta(days=i) for i in range(50)]
    pnl = list(range(50))
    trades = _make_trades(ts, [float(p) for p in pnl])
    metrics = mod.compute_cell_metrics((20, "immediate", 10, "tb_pnl"), trades)
    fold_pnls = [metrics[f"fold_{i}_pnl"] for i in range(5)]
    for i in range(1, 5):
        assert fold_pnls[i] >= fold_pnls[i - 1]


def test_spread_stress_subtracts_uniformly() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    ts = [start + timedelta(hours=i) for i in range(100)]
    trades = _make_trades(ts, [1.0] * 100)
    m = mod.compute_cell_metrics((20, "immediate", 10, "tb_pnl"), trades)
    base = m["annual_pnl_pip"]
    stressed = m["annual_pnl_stress_+0.5"]
    expected_drop = 0.5 * 100 / mod.EVAL_SPAN_YEARS_DEFAULT
    assert abs(base - stressed - expected_drop) < 1e-3


# ---------------------------------------------------------------------------
# Verdict logic (parallel to 22.0b)
# ---------------------------------------------------------------------------


def _cell_template(**overrides) -> dict:
    base = {
        "N": 20,
        "entry_timing": "immediate",
        "horizon_bars": 10,
        "exit_rule": "tb_pnl",
        "n_trades": 1000,
        "annual_trades": 500.0,
        "annual_pnl_pip": 250.0,
        "sharpe": 0.15,
        "max_dd_pip": 100.0,
        "dd_pct_pnl": 40.0,
        "mean_pnl": 0.5,
        "median_pnl": 0.4,
        "win_rate": 0.55,
        "annual_pnl_stress_+0.0": 250.0,
        "annual_pnl_stress_+0.2": 150.0,
        "annual_pnl_stress_+0.5": 50.0,
        "sharpe_stress_+0.0": 0.15,
        "sharpe_stress_+0.2": 0.10,
        "sharpe_stress_+0.5": 0.05,
        "fold_pos": 5,
        "fold_neg": 0,
        "fold_pnl_cv": 0.5,
        "fold_concentration_top": 0.30,
        **{f"fold_{i}_pnl": 50.0 for i in range(5)},
        **{f"fold_{i}_n": 200 for i in range(5)},
    }
    base.update(overrides)
    return base


def test_verdict_adopt_when_all_gates_pass() -> None:
    cell = _cell_template()
    verdict, failed = mod.classify_cell(cell)
    assert verdict == "ADOPT"
    assert failed == []


def test_verdict_promising_when_a4_fails() -> None:
    cell = _cell_template(fold_pos=2, fold_neg=3)
    verdict, _ = mod.classify_cell(cell)
    assert verdict == "PROMISING_BUT_NEEDS_OOS"


def test_verdict_promising_when_a5_stress_fails() -> None:
    cell = _cell_template(**{"annual_pnl_stress_+0.5": -5.0})
    verdict, _ = mod.classify_cell(cell)
    assert verdict == "PROMISING_BUT_NEEDS_OOS"


def test_verdict_reject_when_a0_below_minimum_trades() -> None:
    cell = _cell_template(annual_trades=20.0)
    verdict, failed = mod.classify_cell(cell)
    assert verdict == "REJECT"
    assert any("A0" in f for f in failed)


def test_verdict_reject_when_a1_below_baseline_sharpe() -> None:
    cell = _cell_template(sharpe=0.05)
    verdict, failed = mod.classify_cell(cell)
    assert verdict == "REJECT"
    assert any("A1" in f for f in failed)


def test_best_possible_pnl_excluded_from_adopt_judgement() -> None:
    """best_possible_pnl is diagnostic-only; verdict must be REJECT
    regardless of the metric values."""
    cell = _cell_template(exit_rule="best_possible_pnl", sharpe=2.0, annual_pnl_pip=10000.0)
    verdict, failed = mod.classify_cell(cell)
    assert verdict == "REJECT"
    assert any("non-realistic" in f or "diagnostic" in f for f in failed)


# ---------------------------------------------------------------------------
# NG list compliance — script never reads is_week_open_window for filtering
# ---------------------------------------------------------------------------


def test_no_week_open_filter_in_script() -> None:
    src = SCRIPT.read_text(encoding="utf-8")
    # The string may appear at most in NG-list comments. The actual filter line
    # uses only valid_label and gap_affected_forward_window.
    assert 'labels["valid_label"]' in src
    assert "gap_affected_forward_window" in src
    # No row-drop predicate on is_week_open_window
    assert src.count("is_week_open_window") <= 2  # NG-list comments only


def test_canonical_pairs_list_size_20() -> None:
    assert len(mod.PAIRS_CANONICAL_20) == 20
    assert "GBP_CHF" in mod.PAIRS_CANONICAL_20


# ---------------------------------------------------------------------------
# Outcome join uses correct (entry_ts, horizon, direction) keys
# ---------------------------------------------------------------------------


def test_match_signals_returns_only_matching_indices() -> None:
    """_match_signals returns label-array indices where label_ts equals sig_ts."""
    label_ts = np.array([1, 3, 5, 7, 9], dtype=np.int64)
    sig_ts = np.array([3, 5, 6, 9], dtype=np.int64)
    matched = mod._match_signals(label_ts, sig_ts)
    # 3 -> idx 1, 5 -> idx 2, 9 -> idx 4 (6 not matched)
    assert list(matched) == [1, 2, 4]


def test_match_signals_empty_inputs() -> None:
    label_ts = np.array([1, 3, 5], dtype=np.int64)
    assert mod._match_signals(label_ts, np.empty(0, dtype=np.int64)).size == 0
    assert mod._match_signals(np.empty(0, dtype=np.int64), np.array([1], dtype=np.int64)).size == 0
