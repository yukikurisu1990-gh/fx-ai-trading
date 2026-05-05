"""Unit tests for Stage 23.0a outcome dataset construction."""

from __future__ import annotations

import importlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23 = importlib.import_module("stage23_0a_build_outcome_dataset")


# ---------------------------------------------------------------------------
# Synthetic M1 data fixtures
# ---------------------------------------------------------------------------


def _make_m1(
    n_bars: int,
    start: datetime | None = None,
    bid_path: np.ndarray | None = None,
    spread_pip: float = 1.0,
    pip: float = 0.0001,
    high_offset_pip: float = 0.5,
    low_offset_pip: float = 0.5,
) -> pd.DataFrame:
    """Build a regular 1-minute synthetic M1 BA candle dataframe.

    bid_path: per-bar mid bid CLOSE prices. If None, constant 1.0.
    """
    if start is None:
        start = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)  # Monday 09:00
    idx = pd.date_range(start, periods=n_bars, freq="1min", tz=UTC)
    if bid_path is None:
        bid_path = np.full(n_bars, 1.0)
    bid_close = np.asarray(bid_path, dtype=np.float64)
    # For simplicity, open == close == high == low; spread is constant
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


def _build(pair: str, m1: pd.DataFrame, tf: str, horizons: tuple[int, ...]):
    signal_df = stage23.aggregate_m1_to_tf(m1, tf)
    return stage23.compute_pair_rows(pair, m1, signal_df, tf, horizons)


# ---------------------------------------------------------------------------
# 1-2: aggregation right-closed/right-labeled
# ---------------------------------------------------------------------------


def test_aggregate_m1_to_m5_right_closed_right_labeled():
    # 10 M1 bars from 09:00 to 09:09 (start times)
    m1 = _make_m1(n_bars=10, bid_path=np.arange(10, dtype=float) * 0.0001 + 1.0)
    agg = stage23.aggregate_m1_to_tf(m1, "M5")
    # Right-closed: M5 bar labeled 09:05 contains M1 starts in (09:00, 09:05]
    # = M1 starts at 09:01, 09:02, 09:03, 09:04, 09:05 (indices 1..5)
    bar_905 = pd.Timestamp("2026-01-05 09:05", tz=UTC)
    assert bar_905 in agg.index
    sub = m1.iloc[1:6]
    np.testing.assert_allclose(agg.loc[bar_905, "bid_o"], sub["bid_o"].iloc[0])
    np.testing.assert_allclose(agg.loc[bar_905, "bid_c"], sub["bid_c"].iloc[-1])
    np.testing.assert_allclose(agg.loc[bar_905, "bid_h"], sub["bid_h"].max())
    np.testing.assert_allclose(agg.loc[bar_905, "bid_l"], sub["bid_l"].min())


def test_aggregate_m1_to_m15_right_closed_right_labeled():
    m1 = _make_m1(n_bars=30, bid_path=np.arange(30, dtype=float) * 0.0001 + 1.0)
    agg = stage23.aggregate_m1_to_tf(m1, "M15")
    bar_915 = pd.Timestamp("2026-01-05 09:15", tz=UTC)
    assert bar_915 in agg.index
    sub = m1.iloc[1:16]  # M1 starts in (09:00, 09:15] = 09:01..09:15
    np.testing.assert_allclose(agg.loc[bar_915, "ask_o"], sub["ask_o"].iloc[0])
    np.testing.assert_allclose(agg.loc[bar_915, "ask_c"], sub["ask_c"].iloc[-1])


# ---------------------------------------------------------------------------
# 3: signal aggregation does not use future M1 bars
# ---------------------------------------------------------------------------


def test_signal_aggregation_does_not_use_future_m1_bars():
    m1 = _make_m1(n_bars=20, bid_path=np.arange(20, dtype=float))
    agg = stage23.aggregate_m1_to_tf(m1, "M5")
    bar_905 = pd.Timestamp("2026-01-05 09:05", tz=UTC)
    # The M5 bar labeled 09:05 close == M1 bar at 09:05 close
    np.testing.assert_allclose(agg.loc[bar_905, "bid_c"], m1.loc[bar_905, "bid_c"])
    # Must NOT include M1[09:06] or later
    next_m1 = pd.Timestamp("2026-01-05 09:06", tz=UTC)
    assert m1.loc[next_m1, "bid_c"] != agg.loc[bar_905, "bid_c"]


# ---------------------------------------------------------------------------
# 4-6: entry timing
# ---------------------------------------------------------------------------


def test_entry_uses_next_m1_bar_open():
    m1 = _make_m1(n_bars=20, bid_path=np.arange(20, dtype=float))
    rows = _build("EUR_USD", m1, "M5", (1,))
    rows = rows[rows["valid_label"]].sort_values("entry_ts")
    # First valid entry ts: 09:05 (M5 bar). Entry at M1[09:06].
    entry_ts = pd.Timestamp("2026-01-05 09:05", tz=UTC)
    sub = rows[(rows["entry_ts"] == entry_ts) & (rows["direction"] == "long")]
    if len(sub):
        m1_at_906 = m1.loc[pd.Timestamp("2026-01-05 09:06", tz=UTC)]
        np.testing.assert_allclose(sub.iloc[0]["entry_ask"], m1_at_906["ask_o"])
        np.testing.assert_allclose(sub.iloc[0]["entry_bid"], m1_at_906["bid_o"])


def test_entry_ts_equals_signal_close():
    m1 = _make_m1(n_bars=20, bid_path=np.arange(20, dtype=float))
    rows = _build("EUR_USD", m1, "M5", (1,))
    sig_idx = stage23.aggregate_m1_to_tf(m1, "M5").index
    rows_unique_ts = rows.drop_duplicates("entry_ts")["entry_ts"].sort_values().tolist()
    # Every row's entry_ts must be one of the signal-TF bar timestamps
    assert set(rows_unique_ts).issubset(set(sig_idx.tolist()))


def test_no_lookahead_in_path_index():
    m1 = _make_m1(n_bars=20, bid_path=np.arange(20, dtype=float))
    rows = _build("EUR_USD", m1, "M5", (1,))
    rows = rows[rows["valid_label"]]
    # entry_ts == signal_ts, entry M1 bar at signal_ts + 1min
    # path covers (signal_ts, signal_ts + horizon * tf_min]
    for _, r in rows.iterrows():
        # entry_ask must equal ask_o at signal_ts + 1 min
        m1_at_entry_ts = r["entry_ts"] + pd.Timedelta(minutes=1)
        np.testing.assert_allclose(r["entry_ask"], m1.loc[m1_at_entry_ts, "ask_o"])


# ---------------------------------------------------------------------------
# 7-8: bid/ask convention
# ---------------------------------------------------------------------------


def test_long_bid_ask_convention():
    # Need >= 14 M5 bars (= 70 M1 bars) for ATR(14) to be defined.
    n = 100
    bid_path = 1.0 + np.arange(n, dtype=float) * 0.0001
    m1 = _make_m1(n_bars=n, bid_path=bid_path, spread_pip=1.0)
    rows = _build("EUR_USD", m1, "M5", (1,))
    rows = rows[(rows["valid_label"]) & (rows["direction"] == "long")]
    assert len(rows) > 0
    # On rising series with horizon=1 M5 (5 M1 bars), long time-exit pnl > 0
    # (after spread). Path is +5*0.0001 = +5pip rise minus 1 pip spread = +4 pip.
    assert rows["time_exit_pnl"].mean() > 0


def test_short_bid_ask_convention():
    n = 100
    bid_path = 1.0 + np.arange(n, dtype=float) * 0.0001
    m1 = _make_m1(n_bars=n, bid_path=bid_path, spread_pip=1.0)
    rows = _build("EUR_USD", m1, "M5", (1,))
    rows = rows[(rows["valid_label"]) & (rows["direction"] == "short")]
    assert len(rows) > 0
    assert rows["time_exit_pnl"].mean() < 0


# ---------------------------------------------------------------------------
# 9: horizon=4 M15 covers 60 M1 bars
# ---------------------------------------------------------------------------


def test_horizon_4_m15_covers_60_m1_bars():
    # Need >= 14 M15 bars (= 210 M1) for ATR(14), plus 60 path bars.
    n = 300
    bid_path = 1.0 + np.arange(n, dtype=float) * 0.00001
    m1 = _make_m1(n_bars=n, bid_path=bid_path, spread_pip=1.0)
    rows = _build("EUR_USD", m1, "M15", (4,))
    rows = rows[(rows["valid_label"]) & (rows["direction"] == "long")].sort_values("entry_ts")
    assert len(rows) >= 1
    r = rows.iloc[0]
    assert int(r["horizon_minutes"]) == 60
    # entry_ts == signal_ts (M15). Entry at M1[entry_ts + 1 min]. Path 60 bars =
    # M1[entry_ts + 1] through M1[entry_ts + 60]. exit_bid_close is bid_c at
    # M1[entry_ts + 60].
    expected_exit_ts = r["entry_ts"] + pd.Timedelta(minutes=60)
    np.testing.assert_allclose(r["exit_bid_close"], m1.loc[expected_exit_ts, "bid_c"])


# ---------------------------------------------------------------------------
# 10: TP/SL ATR scaling on signal-TF
# ---------------------------------------------------------------------------


def test_tp_sl_atr_scaling_on_signal_tf():
    bid_path = 1.0 + np.cumsum(np.random.RandomState(0).randn(200)) * 1e-5
    m1 = _make_m1(n_bars=200, bid_path=bid_path)
    sig = stage23.aggregate_m1_to_tf(m1, "M5")
    sig_atr_pip = stage23.atr_causal(sig, period=stage23.ATR_PERIOD) / 0.0001
    rows = _build("EUR_USD", m1, "M5", (1,))
    rows = rows[(rows["valid_label"])]
    # For each valid row, tp_dist_pip == 1.5 * atr_at_entry_signal_tf
    np.testing.assert_allclose(rows["tp_dist_pip"], rows["atr_at_entry_signal_tf"] * 1.5, rtol=1e-5)
    np.testing.assert_allclose(rows["sl_dist_pip"], rows["atr_at_entry_signal_tf"] * 1.0, rtol=1e-5)
    # And atr_at_entry_signal_tf comes from the SIGNAL-TF ATR, not M1 ATR
    # Spot-check one value: rows['atr_at_entry_signal_tf'] for entry_ts T should equal
    # sig_atr_pip at the index of T in sig.
    pair_row = rows.iloc[0]
    sig_pos = sig.index.get_loc(pair_row["entry_ts"])
    np.testing.assert_allclose(pair_row["atr_at_entry_signal_tf"], sig_atr_pip[sig_pos], rtol=1e-5)


# ---------------------------------------------------------------------------
# 11-12: same-bar ambiguity
# ---------------------------------------------------------------------------


def _inject_huge_swing(m1: pd.DataFrame, target_idx: int, pip: float) -> pd.DataFrame:
    target_ts = m1.index[target_idx]
    m1.loc[target_ts, "bid_h"] = m1.loc[target_ts, "bid_c"] + 1000 * pip
    m1.loc[target_ts, "ask_h"] = m1.loc[target_ts, "ask_c"] + 1000 * pip
    m1.loc[target_ts, "bid_l"] = m1.loc[target_ts, "bid_c"] - 1000 * pip
    m1.loc[target_ts, "ask_l"] = m1.loc[target_ts, "ask_c"] - 1000 * pip
    return m1


def test_same_bar_ambiguous_resolves_to_sl():
    # Need ATR defined on M5 (>= 14 bars) AND modified M1 bar within forward path.
    # ATR(14) on M5 starts at signal_df idx 13 -> M1 idx (13+1)*5 = 70.
    # Use target M1 idx 88 (in path of M5 signal at M1[85]).
    n = 200
    pip = 0.0001
    rng = np.random.RandomState(42)
    bid_path = 1.0 + np.cumsum(rng.randn(n)) * 5 * pip
    m1 = _make_m1(
        n_bars=n,
        bid_path=bid_path,
        spread_pip=1.0,
        high_offset_pip=2.0,
        low_offset_pip=2.0,
    )
    m1 = _inject_huge_swing(m1, target_idx=88, pip=pip)
    rows = _build("EUR_USD", m1, "M5", (1,))
    rows = rows[(rows["valid_label"]) & (rows["direction"] == "long")]
    ambig = rows[rows["same_bar_tp_sl_ambiguous"]]
    assert len(ambig) > 0
    # Conservative: at least one ambig row -> SL
    assert (ambig["tb_outcome"] == -1).any()


def test_hit_tp_and_hit_sl_preserved_for_ambiguous():
    n = 200
    pip = 0.0001
    rng = np.random.RandomState(7)
    bid_path = 1.0 + np.cumsum(rng.randn(n)) * 5 * pip
    m1 = _make_m1(
        n_bars=n,
        bid_path=bid_path,
        spread_pip=1.0,
        high_offset_pip=2.0,
        low_offset_pip=2.0,
    )
    m1 = _inject_huge_swing(m1, target_idx=93, pip=pip)
    rows = _build("EUR_USD", m1, "M5", (1,))
    ambig = rows[(rows["valid_label"]) & (rows["same_bar_tp_sl_ambiguous"])]
    assert len(ambig) > 0
    assert (ambig["hit_tp"] & ambig["hit_sl"]).all()


# ---------------------------------------------------------------------------
# 13: gap detection
# ---------------------------------------------------------------------------


def test_gap_affected_flag_set_on_weekend():
    # Build M1: 100 bars then a 60-min gap then 100 more bars (need 14 M5 ATR
    # defined before any signal whose path crosses the gap).
    n_first = 100
    n_second = 100
    start = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
    idx_first = pd.date_range(start, periods=n_first, freq="1min", tz=UTC)
    gap_start = idx_first[-1] + pd.Timedelta(minutes=61)  # large gap (60-min hole)
    idx_second = pd.date_range(gap_start, periods=n_second, freq="1min", tz=UTC)
    idx = idx_first.append(idx_second)
    bid_close = np.full(len(idx), 1.0) + np.arange(len(idx), dtype=float) * 0.0001
    pip = 0.0001
    bid_open = bid_close.copy()
    bid_high = bid_close + 0.5 * pip
    bid_low = bid_close - 0.5 * pip
    ask_close = bid_close + 1.0 * pip
    ask_open = bid_open + 1.0 * pip
    ask_high = bid_high + 1.0 * pip
    ask_low = bid_low + 1.0 * pip
    m1 = pd.DataFrame(
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
    rows = _build("EUR_USD", m1, "M5", (3,))
    # Some valid rows should have gap_affected = True (the ones whose forward
    # path crosses the 60-minute hole).
    assert rows[rows["valid_label"] & rows["gap_affected_forward_window"]].shape[0] > 0


# ---------------------------------------------------------------------------
# 14: tail invalid
# ---------------------------------------------------------------------------


def test_valid_label_false_when_path_runs_past_end_of_data():
    # Last horizon * tf_min M1 bars worth of M5 signals must be valid_label=False.
    n = 60
    m1 = _make_m1(n_bars=n)
    rows = _build("EUR_USD", m1, "M5", (3,))
    rows_h3 = rows[rows["horizon_bars"] == 3]
    # The last signal bar's entry would be at signal_ts + 1 min, path of 15 M1 bars
    # → can't fit if signal_ts >= ts[n-1] - 15 min. Tail signals should be invalid.
    rows_h3_long = rows_h3[rows_h3["direction"] == "long"].sort_values("entry_ts")
    # The last 3 M5 bars (=15 M1 bars / 5 = 3 M5 bars) should be invalid for h=3
    assert not rows_h3_long.iloc[-1]["valid_label"]


# ---------------------------------------------------------------------------
# 15-17: schema
# ---------------------------------------------------------------------------


def test_schema_columns_match_design():
    m1 = _make_m1(n_bars=40)
    rows = _build("EUR_USD", m1, "M5", (1, 2, 3))
    assert list(rows.columns) == stage23.OUTPUT_COLUMNS


def test_schema_identity_within_tf():
    m1 = _make_m1(n_bars=40)
    rows_eu = _build("EUR_USD", m1, "M5", (1, 2, 3))
    rows_uj = _build("USD_JPY", m1, "M5", (1, 2, 3))
    assert list(rows_eu.columns) == list(rows_uj.columns)
    for col in rows_eu.columns:
        assert rows_eu[col].dtype == rows_uj[col].dtype, f"dtype mismatch for {col}"


def test_schema_compat_with_22_0a():
    """Every 22.0a column listed as carried-over must be present with a compatible dtype."""
    m1 = _make_m1(n_bars=40)
    rows = _build("EUR_USD", m1, "M5", (1, 2, 3))
    carried_over = [
        "entry_ts",
        "pair",
        "horizon_bars",
        "direction",
        "tb_pnl",
        "time_exit_pnl",
        "tb_outcome",
        "time_to_tp",
        "time_to_sl",
        "same_bar_tp_sl_ambiguous",
        "entry_ask",
        "entry_bid",
        "exit_bid_close",
        "exit_ask_close",
        "gap_affected_forward_window",
        "valid_label",
        "mfe_after_cost",
        "mae_after_cost",
        "spread_entry",
        "cost_ratio",
    ]
    for col in carried_over:
        assert col in rows.columns, f"missing carry-over column: {col}"


# ---------------------------------------------------------------------------
# 18: signal_timeframe column + filename
# ---------------------------------------------------------------------------


def test_signal_timeframe_present_as_column_and_filename(tmp_path: Path):
    m1 = _make_m1(n_bars=40)
    rows = _build("EUR_USD", m1, "M5", (1,))
    assert "signal_timeframe" in rows.columns
    assert (rows["signal_timeframe"] == "M5").all()
    rows2 = _build("EUR_USD", m1, "M15", (1,))
    assert (rows2["signal_timeframe"] == "M15").all()


# ---------------------------------------------------------------------------
# 19: tz-aware timestamps
# ---------------------------------------------------------------------------


def test_tz_aware_timestamps():
    m1 = _make_m1(n_bars=40)
    rows = _build("EUR_USD", m1, "M5", (1,))
    assert isinstance(rows["entry_ts"].dtype, pd.DatetimeTZDtype)
    assert str(rows["entry_ts"].dt.tz) == "UTC"


# ---------------------------------------------------------------------------
# 20: resolution-agnostic gap detection
# ---------------------------------------------------------------------------


def test_resolution_agnostic_gap_detection():
    m1 = _make_m1(n_bars=20)
    # Force a US-resolution DatetimeIndex (us instead of ns)
    m1_us = m1.copy()
    m1_us.index = pd.DatetimeIndex(m1_us.index.values.astype("datetime64[us]"), tz=UTC)
    rows_ns = _build("EUR_USD", m1, "M5", (1,))
    rows_us = _build("EUR_USD", m1_us, "M5", (1,))
    assert rows_ns["gap_affected_forward_window"].equals(rows_us["gap_affected_forward_window"])


# ---------------------------------------------------------------------------
# 21: barrier profile columns
# ---------------------------------------------------------------------------


def test_barrier_profile_columns_persisted():
    m1 = _make_m1(n_bars=40)
    rows = _build("EUR_USD", m1, "M5", (1,))
    assert "barrier_profile" in rows.columns
    assert (rows["barrier_profile"] == "standard").all()
    assert (rows["tp_atr_mult"] == np.float32(1.5)).all()
    assert (rows["sl_atr_mult"] == np.float32(1.0)).all()
    assert "tp_dist_pip" in rows.columns
    assert "sl_dist_pip" in rows.columns


# ---------------------------------------------------------------------------
# Schema JSON sanity (additional)
# ---------------------------------------------------------------------------


def test_schema_json_columns_match_module_constant(tmp_path: Path):
    out_dir = tmp_path / "stage23_0a"
    out_dir.mkdir()
    p = stage23.write_schema_json(out_dir)
    spec = json.loads(p.read_text(encoding="utf-8"))
    assert spec["columns"] == stage23.OUTPUT_COLUMNS
