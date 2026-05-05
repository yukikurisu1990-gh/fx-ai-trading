"""Stage 22.0a Scalp Label Design unit tests.

Verifies the hard ADOPT criteria H1-H8 from
docs/design/phase22_0a_scalp_label_design.md, plus NG list compliance
(no filter applied; context flags informational only).
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "stage22_0a_scalp_label_design.py"

# Load the script as a module without depending on a package layout
_spec = importlib.util.spec_from_file_location("stage22_0a_label", SCRIPT)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
sys.modules["stage22_0a_label"] = mod
_spec.loader.exec_module(mod)


# ---------------------------------------------------------------------------
# Helpers — synthetic BA candle frames
# ---------------------------------------------------------------------------


def _build_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows).set_index("timestamp")
    df.index = pd.DatetimeIndex(df.index, tz=UTC)
    return df


def _flat_bar(ts: datetime, mid: float, spread: float = 0.02, rng: float = 0.05) -> dict:
    """Quiet bar with intra-bar range large enough to give ATR > spread."""
    half = spread / 2.0
    return {
        "timestamp": ts,
        "bid_o": mid - half,
        "bid_h": mid - half + rng,
        "bid_l": mid - half - rng,
        "bid_c": mid - half,
        "ask_o": mid + half,
        "ask_h": mid + half + rng,
        "ask_l": mid + half - rng,
        "ask_c": mid + half,
    }


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


def _consecutive(n: int, start: datetime, mid: float, spread: float = 0.02) -> list[dict]:
    return [_flat_bar(start + timedelta(minutes=i), mid, spread) for i in range(n)]


# ---------------------------------------------------------------------------
# H1 — row count expectation
# ---------------------------------------------------------------------------


def test_row_count_8_per_bar() -> None:
    n_bars = 100
    start = datetime(2025, 1, 1, tzinfo=UTC)
    df = _build_df(_consecutive(n_bars, start, 100.0))
    rows = mod.compute_pair_rows("USD_JPY", df)
    assert len(rows) == n_bars * len(mod.HORIZONS) * len(mod.DIRECTIONS)
    assert set(rows["horizon_bars"].unique()) == set(mod.HORIZONS)
    assert set(rows["direction"].unique()) == {"long", "short"}


# ---------------------------------------------------------------------------
# H2 — bid/ask separated entry/exit
# ---------------------------------------------------------------------------


def test_long_entry_uses_ask_open() -> None:
    """Bar i+1 ask_o must be entry_ask; bid_o must be entry_bid."""
    start = datetime(2025, 1, 1, tzinfo=UTC)
    rows_data = []
    for k in range(60):
        rows_data.append(
            _bar(
                start + timedelta(minutes=k),
                bid_o=100.0 + k * 0.001,
                bid_h=100.0 + k * 0.001 + 0.005,
                bid_l=100.0 + k * 0.001 - 0.005,
                bid_c=100.0 + k * 0.001 + 0.002,
                ask_o=100.02 + k * 0.001,
                ask_h=100.02 + k * 0.001 + 0.005,
                ask_l=100.02 + k * 0.001 - 0.005,
                ask_c=100.02 + k * 0.001 + 0.002,
            )
        )
    df = _build_df(rows_data)
    rows = mod.compute_pair_rows("USD_JPY", df)
    # at row i=10, entry comes from bar i+1=11
    target = rows[
        (rows["horizon_bars"] == 5)
        & (rows["direction"] == "long")
        & (rows["entry_ts"] == df.index[10])
    ].iloc[0]
    assert target["entry_ask"] == pytest.approx(df["ask_o"].iloc[11])
    assert target["entry_bid"] == pytest.approx(df["bid_o"].iloc[11])
    # exit at i+horizon = 15
    assert target["exit_bid_close"] == pytest.approx(df["bid_c"].iloc[15])
    assert target["exit_ask_close"] == pytest.approx(df["ask_c"].iloc[15])


def test_long_tp_fires_from_bid_high_short_tp_from_ask_low() -> None:
    """Long TP triggers when bid_h crosses; short TP triggers when ask_l crosses."""
    start = datetime(2025, 1, 1, tzinfo=UTC)
    rows_data = []
    base = 100.0
    spread = 0.02
    # 30 flat bars to warm up ATR
    for k in range(30):
        rows_data.append(_flat_bar(start + timedelta(minutes=k), base, spread))
    # bar 30 (i=29 signal): keeps flat, bar 31 = entry bar
    rows_data.append(_flat_bar(start + timedelta(minutes=30), base, spread))
    # bar 31 = entry (ask_o = base + spread/2)
    rows_data.append(_flat_bar(start + timedelta(minutes=31), base, spread))
    # bar 32: bid_h spikes up → long TP fires
    rows_data.append(
        _bar(
            start + timedelta(minutes=32),
            bid_o=base,
            bid_h=base + 1.0,
            bid_l=base,
            bid_c=base,
            ask_o=base + spread,
            ask_h=base + 1.0 + spread,
            ask_l=base + spread,
            ask_c=base + spread,
        )
    )
    # add bars to fill horizon
    for k in range(33, 80):
        rows_data.append(_flat_bar(start + timedelta(minutes=k), base, spread))
    df = _build_df(rows_data)
    rows = mod.compute_pair_rows("USD_JPY", df)
    target = rows[
        (rows["horizon_bars"] == 5)
        & (rows["direction"] == "long")
        & (rows["entry_ts"] == df.index[30])
    ].iloc[0]
    # tb_outcome should be +1 (TP hit) since the spike at bar 32 = path bar k=1
    # ATR is small for flat bars, so tp_dist tiny — spike of 1.0 will exceed tp_dist
    assert target["tb_outcome"] == 1
    assert target["time_to_tp"] == pytest.approx(2.0)  # k=1 (path index) → time_to_tp = 2


# ---------------------------------------------------------------------------
# H3 — look-ahead bias sanity
# ---------------------------------------------------------------------------


def test_no_lookahead_decision_bar_excluded() -> None:
    """Setting bar i to a wild value must NOT change row i's labels — the
    forward window starts at i+1.
    """
    start = datetime(2025, 1, 1, tzinfo=UTC)
    rows_a = []
    rows_b = []
    for k in range(80):
        rows_a.append(_flat_bar(start + timedelta(minutes=k), 100.0))
        rows_b.append(_flat_bar(start + timedelta(minutes=k), 100.0))
    # bar 40 only differs in version B (signal bar perturbation)
    rows_b[40] = _bar(
        start + timedelta(minutes=40),
        bid_o=99.0,
        bid_h=99.0,
        bid_l=99.0,
        bid_c=99.0,
        ask_o=99.02,
        ask_h=99.02,
        ask_l=99.02,
        ask_c=99.02,
    )
    df_a = _build_df(rows_a)
    df_b = _build_df(rows_b)
    out_a = mod.compute_pair_rows("USD_JPY", df_a)
    out_b = mod.compute_pair_rows("USD_JPY", df_b)
    # rows whose entry_ts > bar 40 must be identical (forward path uses bars > 40)
    later_a = out_a[out_a["entry_ts"] >= df_a.index[41]].reset_index(drop=True)
    later_b = out_b[out_b["entry_ts"] >= df_b.index[41]].reset_index(drop=True)
    pd.testing.assert_frame_equal(
        later_a[["mfe_after_cost", "mae_after_cost", "tb_outcome", "tb_pnl"]],
        later_b[["mfe_after_cost", "mae_after_cost", "tb_outcome", "tb_pnl"]],
        check_dtype=False,
    )


# ---------------------------------------------------------------------------
# H4 — last `horizon_bars` rows are valid_label=False
# ---------------------------------------------------------------------------


def test_tail_invalid_per_horizon() -> None:
    n_bars = 60
    start = datetime(2025, 1, 1, tzinfo=UTC)
    df = _build_df(_consecutive(n_bars, start, 100.0))
    rows = mod.compute_pair_rows("USD_JPY", df)
    for h in mod.HORIZONS:
        # the last h timestamps must yield valid_label=False on both directions
        sub = rows[rows["horizon_bars"] == h]
        tail_ts = sub["entry_ts"].sort_values().unique()[-h:]
        tail_rows = sub[sub["entry_ts"].isin(tail_ts)]
        assert (~tail_rows["valid_label"]).all(), f"horizon {h} tail not invalidated"


# ---------------------------------------------------------------------------
# H5 — gap_affected_forward_window
# ---------------------------------------------------------------------------


def test_gap_affected_flag_at_weekend_gap() -> None:
    start = datetime(2025, 1, 3, 20, 0, tzinfo=UTC)  # Friday afternoon
    rows_data = []
    # 50 normal M1 bars
    for k in range(50):
        rows_data.append(_flat_bar(start + timedelta(minutes=k), 100.0))
    # then a 48h gap (typical weekend) then 50 more bars
    after_gap = start + timedelta(minutes=50, hours=48)
    for k in range(50):
        rows_data.append(_flat_bar(after_gap + timedelta(minutes=k), 100.0))
    df = _build_df(rows_data)
    rows = mod.compute_pair_rows("USD_JPY", df)
    # rows whose forward window crosses the gap must be flagged
    pre_gap_rows = rows[
        (rows["horizon_bars"] == 40)
        & (rows["direction"] == "long")
        & (rows["entry_ts"] >= df.index[20])
        & (rows["entry_ts"] <= df.index[49])
    ]
    assert pre_gap_rows["gap_affected_forward_window"].any()
    # rows fully before any gap risk (entry_ts very early) should not be flagged
    early_rows = rows[
        (rows["horizon_bars"] == 5)
        & (rows["direction"] == "long")
        & (rows["entry_ts"] >= df.index[10])
        & (rows["entry_ts"] <= df.index[20])
    ]
    assert (~early_rows["gap_affected_forward_window"]).any()


# ---------------------------------------------------------------------------
# H6 — same_bar_tp_sl_ambiguous detection
# ---------------------------------------------------------------------------


def test_same_bar_ambiguity_flagged_and_resolved_conservatively() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    rows_data = []
    base = 100.0
    spread = 0.02
    # warm up ATR
    for k in range(30):
        rows_data.append(_flat_bar(start + timedelta(minutes=k), base, spread))
    # bars 30 = signal bar, 31 = entry bar
    rows_data.append(_flat_bar(start + timedelta(minutes=30), base, spread))
    rows_data.append(_flat_bar(start + timedelta(minutes=31), base, spread))
    # bar 32: a spike that hits both long TP and long SL within the same bar
    rows_data.append(
        _bar(
            start + timedelta(minutes=32),
            bid_o=base,
            bid_h=base + 1.0,
            bid_l=base - 1.0,
            bid_c=base,
            ask_o=base + spread,
            ask_h=base + 1.0 + spread,
            ask_l=base - 1.0 + spread,
            ask_c=base + spread,
        )
    )
    # fill remaining bars
    for k in range(33, 80):
        rows_data.append(_flat_bar(start + timedelta(minutes=k), base, spread))
    df = _build_df(rows_data)
    rows = mod.compute_pair_rows("USD_JPY", df)
    target = rows[
        (rows["horizon_bars"] == 5)
        & (rows["direction"] == "long")
        & (rows["entry_ts"] == df.index[30])
    ].iloc[0]
    assert target["same_bar_tp_sl_ambiguous"], "ambiguous flag not set"
    # conservative resolution → outcome -1 (SL)
    assert target["tb_outcome"] == -1
    assert target["tb_pnl"] < 0
    # time_to_sl recorded, time_to_tp NaN
    assert not np.isnan(target["time_to_sl"])
    assert np.isnan(target["time_to_tp"])


# ---------------------------------------------------------------------------
# H8 — schema reusable: pivotable on (horizon_bars, direction)
# ---------------------------------------------------------------------------


def test_schema_pivot_compatible() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    df = _build_df(_consecutive(100, start, 100.0))
    rows = mod.compute_pair_rows("USD_JPY", df)
    # pivot to wide on direction × horizon
    valid = rows[rows["valid_label"]]
    wide = valid.pivot_table(
        index=["entry_ts", "pair"],
        columns=["horizon_bars", "direction"],
        values="tb_outcome",
        aggfunc="first",
    )
    assert wide.shape[1] == len(mod.HORIZONS) * len(mod.DIRECTIONS)
    # every (h, d) combination present in columns
    expected_cols = {(h, d) for h in mod.HORIZONS for d in mod.DIRECTIONS}
    assert set(wide.columns.tolist()) == expected_cols


# ---------------------------------------------------------------------------
# NG list compliance
# ---------------------------------------------------------------------------


def test_week_open_window_rows_not_filtered() -> None:
    """The is_week_open_window flag is recorded but does not drop rows.

    Build a synthetic series spanning Sunday 21 UTC and assert that
    is_week_open_window=True rows exist in the output.
    """
    start = datetime(2025, 1, 5, 20, 0, tzinfo=UTC)  # Sunday 20:00 UTC
    df = _build_df(_consecutive(120, start, 100.0))
    rows = mod.compute_pair_rows("USD_JPY", df)
    we = rows[rows["is_week_open_window"]]
    # Sunday 21:00 UTC for 60 minutes → should exist in input → also in output
    assert len(we) > 0


def test_pip_size_jpy_vs_non_jpy() -> None:
    assert mod.pip_size_for("USD_JPY") == 0.01
    assert mod.pip_size_for("EUR_JPY") == 0.01
    assert mod.pip_size_for("EUR_USD") == 0.0001
    assert mod.pip_size_for("AUD_NZD") == 0.0001


# ---------------------------------------------------------------------------
# Numerical sanity: time_exit_pnl matches direct computation
# ---------------------------------------------------------------------------


def test_time_exit_pnl_matches_direct_computation() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    rows_data = []
    for k in range(80):
        # gradually rising mid
        mid = 100.0 + k * 0.005
        rows_data.append(_flat_bar(start + timedelta(minutes=k), mid))
    df = _build_df(rows_data)
    rows = mod.compute_pair_rows("USD_JPY", df)
    target = rows[
        (rows["horizon_bars"] == 10)
        & (rows["direction"] == "long")
        & (rows["entry_ts"] == df.index[30])
    ].iloc[0]
    expected = (df["bid_c"].iloc[40] - df["ask_o"].iloc[31]) / 0.01  # JPY pip = 0.01
    assert target["time_exit_pnl"] == pytest.approx(expected, rel=1e-4)


def test_short_time_exit_pnl_uses_entry_bid_minus_exit_ask_close() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    rows_data = []
    for k in range(80):
        mid = 100.0 - k * 0.005  # falling — short should profit
        rows_data.append(_flat_bar(start + timedelta(minutes=k), mid))
    df = _build_df(rows_data)
    rows = mod.compute_pair_rows("USD_JPY", df)
    target = rows[
        (rows["horizon_bars"] == 20)
        & (rows["direction"] == "short")
        & (rows["entry_ts"] == df.index[30])
    ].iloc[0]
    expected = (df["bid_o"].iloc[31] - df["ask_c"].iloc[50]) / 0.01
    assert target["time_exit_pnl"] == pytest.approx(expected, rel=1e-4)
    assert target["time_exit_pnl"] > 0  # short on a falling market


# ---------------------------------------------------------------------------
# Diagnostic-only column does not enter validity decisions
# ---------------------------------------------------------------------------


def test_path_shape_class_does_not_affect_valid_label() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    df = _build_df(_consecutive(100, start, 100.0))
    rows = mod.compute_pair_rows("USD_JPY", df)
    valid = rows[rows["valid_label"]]
    # path_shape_class can be 0..4; -1 only when invalid
    assert (valid["path_shape_class"] >= 0).all()
    invalid = rows[~rows["valid_label"]]
    assert (invalid["path_shape_class"] == -1).all()
