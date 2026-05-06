"""Unit tests for Stage 24.0c partial-exit variants."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage24_0c = importlib.import_module("stage24_0c_partial_exit_eval")


# ---------------------------------------------------------------------------
# 1: frozen entry streams imported (3 cells, all 23.0d / M15 / h=4)
# ---------------------------------------------------------------------------


def test_frozen_entry_streams_imported_from_24_0a(tmp_path: Path):
    real = REPO_ROOT / "artifacts" / "stage24_0a" / "frozen_entry_streams.json"
    if real.exists():
        cells = stage24_0c.load_frozen_streams(real)
    else:
        stub = {
            "halt_triggered": False,
            "frozen_cells": [
                {
                    "rank": i + 1,
                    "source_stage": "23.0d",
                    "source_pr": 266,
                    "source_merge_commit": "d929867",
                    "source_verdict": "REJECT",
                    "reject_reason": "still_overtrading",
                    "signal_timeframe": "M15",
                    "filter": None,
                    "cell_params": {
                        "N": 50 if i < 2 else 20,
                        "horizon_bars": 4,
                        "exit_rule": "tb" if i % 2 == 0 else "time",
                    },
                    "score": 3.7,
                    "metrics": {},
                }
                for i in range(3)
            ],
        }
        stub_path = tmp_path / "frozen.json"
        stub_path.write_text(json.dumps(stub), encoding="utf-8")
        cells = stage24_0c.load_frozen_streams(stub_path)
    assert len(cells) == 3
    for c in cells:
        assert c["source_stage"] == "23.0d"
        assert c["signal_timeframe"] == "M15"
        assert c["cell_params"]["horizon_bars"] == 4


# ---------------------------------------------------------------------------
# 2: partial-exit constants are fixed
# ---------------------------------------------------------------------------


def test_partial_exit_constants_fixed():
    assert stage24_0c.PARTIAL_FRACTIONS == (0.25, 0.50, 0.75)
    assert stage24_0c.K_MFE_VALUES == (1.0, 1.5, 2.0)
    assert stage24_0c.P3_FRACTION == 0.5
    assert stage24_0c.MIDPOINT_IDX == 30
    assert stage24_0c.HORIZON_M1_BARS == 60
    assert stage24_0c.TP_ATR_MULT == 1.5
    assert stage24_0c.SL_ATR_MULT == 1.0


def test_variants_count_9():
    assert len(stage24_0c.VARIANTS) == 9
    modes = [v["mode"] for v in stage24_0c.VARIANTS]
    assert modes.count("P1_tp_half") == 3
    assert modes.count("P2_time_midpoint") == 3
    assert modes.count("P3_mfe") == 3


# ---------------------------------------------------------------------------
# 3: P1 — partial fires at TP/2
# ---------------------------------------------------------------------------


def test_p1_partial_fires_at_tp_half_long():
    pip = 0.0001
    # entry_ask = 1.0000, ATR = 10 pip
    # partial_trigger = 1.0000 + 0.75 * 0.001 = 1.00075
    # TP = 1.00150, SL = 0.9990
    # bid_close = [1.0005, 1.0010] (idx 1 crosses partial_trigger; below TP)
    bid_close = np.array([1.0005, 1.0010])
    exit_idx, pnl, reason, partial_done = stage24_0c._simulate_p1_long(
        bid_close, fraction=0.5, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    # bar 1: bid_close=1.0010 >= partial_trigger 1.00075 → partial fires
    # No TP/SL hit; time exit at last bar.
    # partial leg: 0.5 * (1.0010 - 1.0000)/pip = 0.5 * 10 = 5 pip
    # remaining at last bar (1.0010 in this 2-bar series): 0.5 * 10 = 5 pip
    # total = 10 pip
    assert partial_done is True
    assert reason == "p1_time_after_partial"


def test_p1_partial_evaluated_at_close_only():
    """Synthetic series with close BELOW partial_trigger throughout → no fire."""
    pip = 0.0001
    bid_close = np.array([1.0005, 1.0006, 1.0007])  # all below 1.00075 trigger
    exit_idx, pnl, reason, partial_done = stage24_0c._simulate_p1_long(
        bid_close, fraction=0.5, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    assert partial_done is False
    assert reason == "time_full"


# ---------------------------------------------------------------------------
# 4, 5: P1 priority — full TP/SL takes priority over partial at same bar
# ---------------------------------------------------------------------------


def test_p1_full_tp_priority_over_partial_at_same_bar():
    """bid_close >= TP AND >= partial_trigger on same bar → full TP exit."""
    pip = 0.0001
    # entry_ask=1.0000, ATR=10 pip, TP=1.00150, partial_trigger=1.00075
    # bid_close[0]=1.0020 (>= TP and >= partial)
    bid_close = np.array([1.0020])
    exit_idx, pnl, reason, partial_done = stage24_0c._simulate_p1_long(
        bid_close, fraction=0.5, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    assert reason == "tp_full_no_partial"
    assert partial_done is False
    # full pnl: (1.0020 - 1.0000) / 0.0001 = 20.0
    assert abs(pnl - 20.0) < 1e-6


def test_p1_full_sl_priority_over_partial_at_same_bar():
    """First bar bid_close <= SL → full SL exit, no partial possible
    (partial requires ABOVE entry, but SL is BELOW)."""
    pip = 0.0001
    bid_close = np.array([0.9980])  # SL = 0.9990; 0.9980 < SL
    exit_idx, pnl, reason, partial_done = stage24_0c._simulate_p1_long(
        bid_close, fraction=0.5, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    assert reason == "sl_no_partial"
    assert partial_done is False


# ---------------------------------------------------------------------------
# 6: P2 — partial fires at midpoint only
# ---------------------------------------------------------------------------


def test_p2_partial_fires_at_midpoint_only():
    """Use small midpoint_idx for synthetic test."""
    pip = 0.0001
    # 5-bar series; midpoint=2; bid_close around entry, no TP/SL hit
    bid_close = np.array([1.0001, 1.0002, 1.0003, 1.0002, 1.0001])
    exit_idx, pnl, reason, partial_done = stage24_0c._simulate_p2_long(
        bid_close, fraction=0.5, midpoint_idx=2, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    # At t=2: bid_close=1.0003, no TP/SL hit → partial fires
    # Then bars 3, 4 don't hit TP/SL → time exit
    assert partial_done is True
    assert reason == "p2_time_after_partial"


def test_p2_full_tp_priority_at_midpoint_bar():
    """At midpoint bar, bid_close >= TP → full TP exit, NO midpoint partial fire."""
    pip = 0.0001
    # 3-bar series; midpoint=1
    # entry=1.0000, ATR=10pip, TP=1.00150
    # bid_close[1] = 1.0020 (>= TP and at midpoint)
    bid_close = np.array([1.0010, 1.0020, 1.0010])
    exit_idx, pnl, reason, partial_done = stage24_0c._simulate_p2_long(
        bid_close, fraction=0.5, midpoint_idx=1, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    # At t=1: TP hit (priority) → full TP exit, no partial
    assert reason == "tp_full_no_partial"
    assert partial_done is False
    assert exit_idx == 1


# ---------------------------------------------------------------------------
# 7: P3 — MFE running max uses close only
# ---------------------------------------------------------------------------


def test_p3_mfe_running_max_uses_close_only():
    """High above mfe_trigger but close below → MFE not yet triggered."""
    pip = 0.0001
    # entry=1.0000, ATR=10pip, K_MFE=1.0 → mfe_trigger = 1.0000 + 1.0 * 0.001 = 1.00100
    # bid_close = [1.0005, 1.0008, 1.0006] — all below mfe_trigger; partial does NOT fire
    bid_close = np.array([1.0005, 1.0008, 1.0006])
    exit_idx, pnl, reason, partial_done = stage24_0c._simulate_p3_long(
        bid_close, k_mfe=1.0, fraction=0.5, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    assert partial_done is False
    assert reason == "time_full"


def test_p3_mfe_partial_fires_when_running_max_close_crosses():
    """running_max_close crosses mfe_trigger → partial fires at THIS bar's close."""
    pip = 0.0001
    # entry=1.0000, ATR=10pip, K_MFE=1.0 → mfe_trigger = 1.00100
    # bid_close = [1.0005, 1.0011] — bar 1 bid_close=1.0011 > 1.00100 → partial fires
    bid_close = np.array([1.0005, 1.0011])
    exit_idx, pnl, reason, partial_done = stage24_0c._simulate_p3_long(
        bid_close, k_mfe=1.0, fraction=0.5, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    assert partial_done is True
    assert reason == "p3_time_after_partial"


# ---------------------------------------------------------------------------
# 8: P3 priority — full TP/SL over MFE partial
# ---------------------------------------------------------------------------


def test_p3_full_tp_priority_over_mfe_partial_at_same_bar():
    """bid_close >= TP AND running_max >= mfe_trigger on same bar → full TP exit."""
    pip = 0.0001
    # entry=1.0000, ATR=10pip, K_MFE=1.0 → mfe_trigger=1.00100; TP=1.00150
    # bid_close[0]=1.0020 (>= TP and running_max=1.0020 >= mfe_trigger)
    bid_close = np.array([1.0020])
    exit_idx, pnl, reason, partial_done = stage24_0c._simulate_p3_long(
        bid_close, k_mfe=1.0, fraction=0.5, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    assert reason == "tp_full_no_partial"
    assert partial_done is False


# ---------------------------------------------------------------------------
# 9: weighted PnL
# ---------------------------------------------------------------------------


def test_partial_pnl_weighted_sum():
    """total_pnl = fraction * partial_leg + (1-fraction) * remaining_leg."""
    pip = 0.0001
    # P1 long: partial_trigger=1.00075, TP=1.00150
    # bid_close = [1.0010, 1.0020] — bar 0: partial fires at 1.0010 (above 1.00075, below TP)
    # bar 1: TP hit at 1.0020 → remaining at 1.0020
    bid_close = np.array([1.0010, 1.0020])
    fraction = 0.5
    exit_idx, pnl, reason, partial_done = stage24_0c._simulate_p1_long(
        bid_close, fraction=fraction, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    # partial leg: 0.5 * (1.0010 - 1.0000)/pip = 0.5 * 10 = 5 pip
    # remaining leg at TP: 0.5 * (1.0020 - 1.0000)/pip = 0.5 * 20 = 10 pip
    # total = 15 pip
    assert partial_done is True
    assert reason == "p1_tp"
    assert abs(pnl - 15.0) < 1e-6


def test_partial_done_false_full_position_exit():
    """When partial never fires, exit pnl = full position pnl (NOT weighted)."""
    pip = 0.0001
    # entry=1.0000, ATR=10pip, TP=1.00150, partial_trigger=1.00075
    # bid_close stays below partial_trigger → partial never fires
    bid_close = np.array([1.0001, 1.0005, 1.0007])  # all below 1.00075
    fraction = 0.5
    exit_idx, pnl, reason, partial_done = stage24_0c._simulate_p1_long(
        bid_close, fraction=fraction, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    # No partial; time exit at last bar with full position
    # pnl = (1.0007 - 1.0000)/pip = 7 pip (full, not 0.5 * 7 = 3.5)
    assert partial_done is False
    assert reason == "time_full"
    assert abs(pnl - 7.0) < 1e-6


# ---------------------------------------------------------------------------
# 10: long uses bid_close, short uses ask_close
# ---------------------------------------------------------------------------


def test_long_uses_bid_close_partial():
    pip = 0.0001
    # _simulate_p1_long takes only bid_close — verify by signature inspection
    bid_close = np.array([1.0010, 1.0020])
    exit_idx, pnl, reason, _ = stage24_0c._simulate_p1_long(
        bid_close, fraction=0.5, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    # bar 0: bid_close=1.0010 > partial_trigger=1.00075 → partial; not TP yet
    # bar 1: bid_close=1.0020 > TP=1.00150 → TP exit; partial pnl + remaining
    # If bid were not used, this test would fail.
    assert reason == "p1_tp"


def test_short_uses_ask_close_partial():
    pip = 0.0001
    # Symmetric for short: triggers and exit at ask_close
    ask_close = np.array([0.9990, 0.9980])
    exit_idx, pnl, reason, partial_done = stage24_0c._simulate_p1_short(
        ask_close, fraction=0.5, atr_pips=10.0, entry_bid=1.0000, pip=pip
    )
    # entry_bid=1.0000, ATR=10pip → SL=1.0010, TP=0.9985, partial_trigger=0.99925
    # bar 0: ask_close=0.9990 < partial_trigger 0.99925 → partial fires
    # bar 1: ask_close=0.9980 → check TP: 0.9980 <= TP=0.9985 → TP hit, remaining at TP
    assert partial_done is True
    assert reason == "p1_tp"


# ---------------------------------------------------------------------------
# 11: remaining leg takes TP after partial
# ---------------------------------------------------------------------------


def test_remaining_leg_takes_tp_after_partial():
    pip = 0.0001
    bid_close = np.array([1.0010, 1.0020])
    exit_idx, pnl, reason, partial_done = stage24_0c._simulate_p1_long(
        bid_close, fraction=0.5, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    assert partial_done is True
    assert reason == "p1_tp"


# ---------------------------------------------------------------------------
# 12: time exit with partial done (path completes without TP/SL)
# ---------------------------------------------------------------------------


def test_time_exit_with_partial_done():
    pip = 0.0001
    # entry=1.0000, ATR=10pip, partial_trigger=1.00075
    # bid_close = [1.0010, 1.0009, 1.0008] — partial fires at bar 0; no TP/SL; time exit
    bid_close = np.array([1.0010, 1.0009, 1.0008])
    exit_idx, pnl, reason, partial_done = stage24_0c._simulate_p1_long(
        bid_close, fraction=0.5, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    assert partial_done is True
    assert reason == "p1_time_after_partial"
    # partial: 0.5 * 10 = 5 pip
    # remaining at last bar 1.0008: 0.5 * 8 = 4 pip
    # total = 9 pip
    assert abs(pnl - 9.0) < 1e-6


# ---------------------------------------------------------------------------
# 13: A4 fold-stability inherited
# ---------------------------------------------------------------------------


def test_a4_4fold_majority_inherited():
    pnl = np.zeros(100)
    pnl[0:20] = 1.0  # k=0 warmup
    pnl[20:80] = 1.0
    pnl[80:] = -1.0
    pnl = pnl + np.linspace(0, 0.001, 100)
    df = pd.DataFrame(
        {
            "entry_ts": pd.date_range("2026-01-01", periods=100, freq="1h", tz="UTC"),
            "pnl_pip": pnl,
        }
    )
    fold = stage24_0c._fold_stability(df)
    assert fold["n_positive"] == 3


# ---------------------------------------------------------------------------
# 14: REJECT reasons inherited (path_ev_unrealisable available)
# ---------------------------------------------------------------------------


def test_reject_reason_path_ev_unrealisable_inherited_from_24_0b():
    metrics = {"overtrading_warning": False}
    gates_a1_fail = {"A0": True, "A1": False, "A2": True, "A3": True, "A4": True, "A5": True}
    assert (
        stage24_0c.classify_reject_reason_phase24(metrics, gates_a1_fail) == "path_ev_unrealisable"
    )


# ---------------------------------------------------------------------------
# 15: smoke mode shape
# ---------------------------------------------------------------------------


def test_smoke_mode_shape():
    assert len(stage24_0c.SMOKE_PAIRS) == 3
    assert len(stage24_0c.SMOKE_VARIANTS) == 3
    modes_in_smoke = {v["mode"] for v in stage24_0c.SMOKE_VARIANTS}
    assert modes_in_smoke == {"P1_tp_half", "P2_time_midpoint", "P3_mfe"}


# ---------------------------------------------------------------------------
# 16: simulate_variant dispatch
# ---------------------------------------------------------------------------


def test_simulate_variant_dispatch_long_short():
    pip = 0.0001
    bid_close = np.array([1.0010, 1.0020])
    ask_close = np.array([1.0011, 1.0021])
    v_p1 = stage24_0c.VARIANTS[0]  # P1 fraction=0.25
    out_long = stage24_0c.simulate_variant(
        v_p1,
        "long",
        bid_close,
        ask_close,
        atr_pips=10.0,
        entry_ask=1.0000,
        entry_bid=1.0000,
        pip=pip,
    )
    assert isinstance(out_long, tuple) and len(out_long) == 4
    out_short = stage24_0c.simulate_variant(
        v_p1,
        "short",
        bid_close,
        ask_close,
        atr_pips=10.0,
        entry_ask=1.0000,
        entry_bid=1.0000,
        pip=pip,
    )
    assert isinstance(out_short, tuple) and len(out_short) == 4


# ---------------------------------------------------------------------------
# 17: partial_hit_rate diagnostic in metrics
# ---------------------------------------------------------------------------


def test_partial_hit_rate_diagnostic_in_metrics():
    trades = pd.DataFrame(
        {
            "pnl_pip": [1.0, -0.5, 2.0, -1.0],
            "best_possible_pnl": [3.0, 2.0, 5.0, 1.0],
            "tb_pnl": [0.5, -0.3, 1.5, -0.8],
            "time_exit_pnl": [0.7, -0.2, 1.7, -0.9],
            "direction": ["long"] * 4,
            "entry_ts": pd.date_range("2026-01-01", periods=4, freq="1h", tz="UTC"),
            "partial_done": [True, False, True, True],
        }
    )
    m = stage24_0c.evaluate_cell(trades)
    assert "partial_hit_rate" in m
    assert abs(m["partial_hit_rate"] - 0.75) < 1e-6  # 3/4 partial done


# ---------------------------------------------------------------------------
# 18: signal_timeframe constant
# ---------------------------------------------------------------------------


def test_signal_timeframe_m15():
    assert stage24_0c.SIGNAL_TIMEFRAME == "M15"
