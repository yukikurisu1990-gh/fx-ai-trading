"""Unit tests for Stage 24.0b trailing-stop variants."""

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

stage24_0b = importlib.import_module("stage24_0b_trailing_stop_eval")


# ---------------------------------------------------------------------------
# 1: Frozen entry streams imported (3 cells, all 23.0d / M15 / h=4)
# ---------------------------------------------------------------------------


def test_frozen_entry_streams_imported_from_24_0a(tmp_path: Path):
    # If the real frozen JSON exists, use it; else write a stub
    real_json = REPO_ROOT / "artifacts" / "stage24_0a" / "frozen_entry_streams.json"
    if real_json.exists():
        cells = stage24_0b.load_frozen_streams(real_json)
    else:
        # Build synthetic stub with 3 cells
        stub = {
            "halt_triggered": False,
            "frozen_cells": [
                {
                    "rank": 1,
                    "source_stage": "23.0d",
                    "source_pr": 266,
                    "source_merge_commit": "d929867",
                    "source_verdict": "REJECT",
                    "reject_reason": "still_overtrading",
                    "signal_timeframe": "M15",
                    "filter": None,
                    "cell_params": {"N": 50, "horizon_bars": 4, "exit_rule": "tb"},
                    "score": 3.7,
                    "metrics": {},
                },
                {
                    "rank": 2,
                    "source_stage": "23.0d",
                    "source_pr": 266,
                    "source_merge_commit": "d929867",
                    "source_verdict": "REJECT",
                    "reject_reason": "still_overtrading",
                    "signal_timeframe": "M15",
                    "filter": None,
                    "cell_params": {"N": 50, "horizon_bars": 4, "exit_rule": "time"},
                    "score": 3.7,
                    "metrics": {},
                },
                {
                    "rank": 3,
                    "source_stage": "23.0d",
                    "source_pr": 266,
                    "source_merge_commit": "d929867",
                    "source_verdict": "REJECT",
                    "reject_reason": "still_overtrading",
                    "signal_timeframe": "M15",
                    "filter": None,
                    "cell_params": {"N": 20, "horizon_bars": 4, "exit_rule": "tb"},
                    "score": 3.1,
                    "metrics": {},
                },
            ],
        }
        stub_path = tmp_path / "frozen_entry_streams.json"
        stub_path.write_text(json.dumps(stub), encoding="utf-8")
        cells = stage24_0b.load_frozen_streams(stub_path)
    assert len(cells) == 3
    for c in cells:
        assert c["source_stage"] == "23.0d"
        assert c["signal_timeframe"] == "M15"
        assert c["cell_params"]["horizon_bars"] == 4


def test_load_frozen_streams_raises_on_halt(tmp_path: Path):
    stub = {"halt_triggered": True, "frozen_cells": []}
    stub_path = tmp_path / "halt.json"
    stub_path.write_text(json.dumps(stub), encoding="utf-8")
    try:
        stage24_0b.load_frozen_streams(stub_path)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "halted" in str(e)


# ---------------------------------------------------------------------------
# 2: trailing constants are fixed
# ---------------------------------------------------------------------------


def test_trailing_constants_fixed():
    assert stage24_0b.TRAILING_K_ATR == (1.0, 1.5, 2.0, 2.5)
    assert stage24_0b.TRAILING_FIXED_PIP == (5.0, 10.0, 20.0, 30.0)
    assert stage24_0b.TRAILING_BE_THRESHOLD_ATR == (1.0, 1.5, 2.0)
    assert stage24_0b.TP_ATR_MULT == 1.5
    assert stage24_0b.SL_ATR_MULT == 1.0
    assert stage24_0b.HORIZON_M1_BARS == 60


def test_variants_count_11():
    assert len(stage24_0b.VARIANTS) == 11
    modes = [v["mode"] for v in stage24_0b.VARIANTS]
    assert modes.count("T1_ATR") == 4
    assert modes.count("T2_fixed_pip") == 4
    assert modes.count("T3_breakeven") == 3


# ---------------------------------------------------------------------------
# 3, 4: ATR trailing — running max uses close, not high
# ---------------------------------------------------------------------------


def test_running_max_uses_close_not_high_long():
    # Synthetic bid_close: ascending then drops; trail at 5 pip (K=1, ATR=5)
    pip = 0.0001
    # bar 0: 1.0000, bar 1: 1.0010, bar 2: 1.0005 (drops 5 pip from prev close)
    bid_close = np.array([1.0000, 1.0010, 1.0005, 1.0003])
    # K=1, ATR=5 pip → distance = 5 pip = 0.0005
    # at bar 2: running_max=1.0010, trail=1.0005, bid_close[2]=1.0005 ≤ 1.0005 → exit
    exit_idx, pnl, reason = stage24_0b._simulate_atr_long(
        bid_close, k_atr=1.0, atr_pips=5.0, entry_ask=1.0001, pip=pip
    )
    assert exit_idx == 2
    # pnl = (1.0005 - 1.0001) / 0.0001 = 4 pip
    assert abs(pnl - 4.0) < 1e-6
    assert reason == "trail"


def test_running_min_uses_close_not_low_short():
    pip = 0.0001
    ask_close = np.array([1.0000, 0.9990, 0.9995, 0.9997])
    # K=1, ATR=5 pip → distance = 5 pip
    # at bar 2: running_min=0.9990, trail=0.9995, ask_close[2]=0.9995 >= 0.9995 → exit
    exit_idx, pnl, reason = stage24_0b._simulate_atr_short(
        ask_close, k_atr=1.0, atr_pips=5.0, entry_bid=0.9999, pip=pip
    )
    assert exit_idx == 2
    # pnl = (0.9999 - 0.9995) / 0.0001 = 4 pip
    assert abs(pnl - 4.0) < 1e-6
    assert reason == "trail"


# ---------------------------------------------------------------------------
# 5: NG#10 mandatory — no intra-bar lookahead
# ---------------------------------------------------------------------------


def test_no_intra_bar_lookahead_long():
    """Bar where intra-bar low would touch trail but close above trail → no exit.

    The simulator only sees close prices, so this is enforced by construction:
    we pass only bid_close array. The test verifies the implementation does
    NOT have any path-array peeking at high/low.
    """
    pip = 0.0001
    # bid_close = ascending then bar-2 close ABOVE trail
    bid_close = np.array([1.0000, 1.0010, 1.0006, 1.0003])
    # K=1, ATR=5 pip → distance = 5 pip = 0.0005
    # at bar 1: running_max=1.0010, trail=1.0005. close[1]=1.0010, no exit.
    # at bar 2: running_max=1.0010, trail=1.0005. close[2]=1.0006 > 1.0005, no exit.
    # at bar 3: running_max=1.0010, trail=1.0005. close[3]=1.0003 ≤ 1.0005 → exit
    exit_idx, pnl, reason = stage24_0b._simulate_atr_long(
        bid_close, k_atr=1.0, atr_pips=5.0, entry_ask=1.0001, pip=pip
    )
    assert exit_idx == 3, f"expected exit at bar 3 (close-only); got {exit_idx}"
    assert reason == "trail"


def test_no_intra_bar_lookahead_passes_to_time_when_close_never_drops():
    # Sustained uptrend: close always > running_max - distance → no exit, time exit at last
    pip = 0.0001
    bid_close = np.array([1.0000, 1.0001, 1.0002, 1.0003, 1.0004])
    exit_idx, pnl, reason = stage24_0b._simulate_atr_long(
        bid_close, k_atr=1.0, atr_pips=5.0, entry_ask=1.0001, pip=pip
    )
    assert exit_idx == 4  # last bar
    assert reason == "time"


# ---------------------------------------------------------------------------
# 6: long pnl uses entry_ask and exit_bid_close
# ---------------------------------------------------------------------------


def test_long_pnl_uses_entry_ask_and_exit_bid_close():
    pip = 0.0001
    bid_close = np.array([1.0000, 1.0010, 1.0005])
    # K=1, ATR=5 pip → trail at running_max - 5 pip
    # bar 2: running_max=1.0010, trail=1.0005, exit at 1.0005
    # entry_ask = 1.0002 → pnl = (1.0005 - 1.0002) / 0.0001 = 3.0 pip
    exit_idx, pnl, reason = stage24_0b._simulate_atr_long(
        bid_close, k_atr=1.0, atr_pips=5.0, entry_ask=1.0002, pip=pip
    )
    assert abs(pnl - 3.0) < 1e-6


# ---------------------------------------------------------------------------
# 7: short pnl uses entry_bid and exit_ask_close
# ---------------------------------------------------------------------------


def test_short_pnl_uses_entry_bid_and_exit_ask_close():
    pip = 0.0001
    ask_close = np.array([1.0000, 0.9990, 0.9995])
    exit_idx, pnl, reason = stage24_0b._simulate_atr_short(
        ask_close, k_atr=1.0, atr_pips=5.0, entry_bid=0.9998, pip=pip
    )
    # bar 2: running_min=0.9990, trail=0.9995, exit at ask_close=0.9995
    # entry_bid = 0.9998 → pnl = (0.9998 - 0.9995) / 0.0001 = 3.0 pip
    assert abs(pnl - 3.0) < 1e-6


# ---------------------------------------------------------------------------
# 8: fixed-pip trailing (similar to ATR but distance fixed)
# ---------------------------------------------------------------------------


def test_fixed_pip_trailing_long():
    pip = 0.0001
    # Use clear margin to avoid floating-point precision edge case
    bid_close = np.array([1.0000, 1.0010, 0.9998])
    # fp=10 → distance = 10 pip = 0.0010
    # bar 2: running_max=1.0010, trail=1.0000, bid_close[2]=0.9998 < 1.0000 → exit
    exit_idx, pnl, reason = stage24_0b._simulate_fixed_pip_long(
        bid_close, fp=10.0, entry_ask=1.0001, pip=pip
    )
    assert exit_idx == 2
    assert reason == "trail"


# ---------------------------------------------------------------------------
# 9: T3 breakeven — SL shifts to entry when threshold crossed
# ---------------------------------------------------------------------------


def test_breakeven_shifts_sl_to_entry_when_threshold_crossed():
    pip = 0.0001
    # entry_ask = 1.0000, ATR=10 pip
    # SL_initial = 1.0000 - 10 pip = 0.9990
    # TP = 1.0000 + 15 pip = 1.0015
    # BE_threshold=1.0 × ATR=10 pip → BE trigger when bid_close - 1.0000 >= 10 pip
    # bid_close = [1.0005, 1.0011, 0.9995]:
    #   bar 0: 1.0005 - 1.0000 = 5 pip < 10, no BE
    #   bar 1: 1.0011 - 1.0000 = 11 pip >= 10, BE triggered → SL := 1.0000
    #   bar 2: 0.9995 ≤ 1.0000 (post-BE SL) → exit at 0.9995, reason "sl_be"
    # pnl = (0.9995 - 1.0000) / 0.0001 = -5 pip (small loss; would have been -50 without BE)
    bid_close = np.array([1.0005, 1.0011, 0.9995])
    exit_idx, pnl, reason = stage24_0b._simulate_breakeven_long(
        bid_close, be_threshold=1.0, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    assert exit_idx == 2
    assert reason == "sl_be"
    assert abs(pnl - (-5.0)) < 1e-6


def test_breakeven_does_not_shift_below_threshold():
    pip = 0.0001
    # bid_close stays below threshold; BE never triggers; original SL hits
    # entry_ask=1.0000, ATR=10 pip → SL = 0.9990, TP = 1.0015
    # bid_close = [1.0003, 1.0005, 0.9989]:
    #   bar 0: 1.0003 - 1.0000 = 3 pip < 10, no BE
    #   bar 1: 1.0005 - 1.0000 = 5 pip < 10, no BE
    #   bar 2: 0.9989 ≤ 0.9990 (original SL) → exit, reason "sl"
    bid_close = np.array([1.0003, 1.0005, 0.9989])
    exit_idx, pnl, reason = stage24_0b._simulate_breakeven_long(
        bid_close, be_threshold=1.0, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    assert reason == "sl"  # original SL, not sl_be
    assert exit_idx == 2


# ---------------------------------------------------------------------------
# 10: TP evaluated at close only (not intra-bar high)
# ---------------------------------------------------------------------------


def test_tp_evaluated_at_close_only():
    pip = 0.0001
    # Close stays below TP → no TP exit even if high (not used) would have hit
    # entry_ask=1.0000, ATR=10 pip → TP=1.0015
    # bid_close = [1.0010, 1.0014, 1.0008] (close never reaches 1.0015)
    bid_close = np.array([1.0010, 1.0014, 1.0008])
    exit_idx, pnl, reason = stage24_0b._simulate_breakeven_long(
        bid_close, be_threshold=2.0, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    # No TP hit; check whether time exit or sl_be
    assert reason != "tp", "TP must NOT trigger on close < TP"


def test_tp_triggers_when_close_above_tp():
    pip = 0.0001
    bid_close = np.array([1.0010, 1.0016, 1.0014])
    exit_idx, pnl, reason = stage24_0b._simulate_breakeven_long(
        bid_close, be_threshold=2.0, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    assert exit_idx == 1
    assert reason == "tp"
    assert abs(pnl - 16.0) < 1e-6


# ---------------------------------------------------------------------------
# 11: SL evaluated at close only
# ---------------------------------------------------------------------------


def test_sl_evaluated_at_close_only():
    pip = 0.0001
    # entry_ask=1.0000, SL=0.9990. Close above SL throughout → no SL exit.
    bid_close = np.array([0.9995, 0.9991, 0.9994, 0.9999])
    exit_idx, pnl, reason = stage24_0b._simulate_breakeven_long(
        bid_close, be_threshold=2.0, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    assert reason != "sl"  # close never crossed SL


# ---------------------------------------------------------------------------
# 12: time exit when no other condition triggers
# ---------------------------------------------------------------------------


def test_horizon_time_exit_when_no_other():
    pip = 0.0001
    # Sideways close, no trail/TP/SL in a way that triggers
    bid_close = np.array([1.0001, 1.0001, 1.0001])
    exit_idx, pnl, reason = stage24_0b._simulate_atr_long(
        bid_close, k_atr=2.5, atr_pips=10.0, entry_ask=1.0000, pip=pip
    )
    # K=2.5, ATR=10 pip → distance = 25 pip; close never drops 25 pip → time exit
    assert exit_idx == 2
    assert reason == "time"


# ---------------------------------------------------------------------------
# 13: a4 fold-stability uses Phase 23 helper
# ---------------------------------------------------------------------------


def test_a4_4fold_majority_inherited():
    pnl = np.zeros(100)
    pnl[0:20] = 1.0  # k=0 warmup
    pnl[20:80] = 1.0  # k=1..3 positive
    pnl[80:] = -1.0  # k=4 negative
    pnl = pnl + np.linspace(0, 0.001, 100)
    df = pd.DataFrame(
        {
            "entry_ts": pd.date_range("2026-01-01", periods=100, freq="1h", tz="UTC"),
            "pnl_pip": pnl,
        }
    )
    fold = stage24_0b._fold_stability(df)
    assert fold["n_positive"] == 3


# ---------------------------------------------------------------------------
# 14: REJECT reason path_ev_unrealisable
# ---------------------------------------------------------------------------


def test_reject_reason_path_ev_unrealisable():
    metrics = {"overtrading_warning": False}
    gates_a1_fail = {"A0": True, "A1": False, "A2": True, "A3": True, "A4": True, "A5": True}
    assert (
        stage24_0b.classify_reject_reason_phase24(metrics, gates_a1_fail) == "path_ev_unrealisable"
    )

    # If overtrading + A1 fail → still_overtrading takes precedence
    metrics_over = {"overtrading_warning": True}
    assert (
        stage24_0b.classify_reject_reason_phase24(metrics_over, gates_a1_fail)
        == "still_overtrading"
    )


def test_reject_reason_under_firing():
    metrics = {"overtrading_warning": False}
    gates_a0_fail = {"A0": False, "A1": True, "A2": True, "A3": True, "A4": True, "A5": True}
    assert stage24_0b.classify_reject_reason_phase24(metrics, gates_a0_fail) == "under_firing"


# ---------------------------------------------------------------------------
# 15: smoke mode shape
# ---------------------------------------------------------------------------


def test_smoke_mode_shape():
    assert len(stage24_0b.SMOKE_PAIRS) == 3
    assert len(stage24_0b.SMOKE_VARIANTS) == 3
    modes_in_smoke = {v["mode"] for v in stage24_0b.SMOKE_VARIANTS}
    assert modes_in_smoke == {"T1_ATR", "T2_fixed_pip", "T3_breakeven"}


# ---------------------------------------------------------------------------
# 16: signal_timeframe == M15 enforced
# ---------------------------------------------------------------------------


def test_signal_timeframe_m15():
    assert stage24_0b.SIGNAL_TIMEFRAME == "M15"


# ---------------------------------------------------------------------------
# 17: Phase 23.0d module imported (entry signal generator)
# ---------------------------------------------------------------------------


def test_phase23_0d_module_imported_for_entry_replay():
    assert hasattr(stage24_0b, "stage23_0d")
    assert callable(stage24_0b.stage23_0d.extract_signals_first_touch_donchian)


# ---------------------------------------------------------------------------
# 18: simulate_variant dispatches by mode + direction
# ---------------------------------------------------------------------------


def test_simulate_variant_dispatch():
    pip = 0.0001
    bid_close = np.array([1.0000, 1.0010, 1.0005])
    ask_close = np.array([1.0001, 1.0011, 1.0006])
    v_atr = stage24_0b.VARIANTS[0]  # T1_ATR K=1.0
    out_long = stage24_0b.simulate_variant(
        v_atr,
        "long",
        bid_close,
        ask_close,
        atr_pips=5.0,
        entry_ask=1.0001,
        entry_bid=1.0000,
        pip=pip,
    )
    assert isinstance(out_long, tuple) and len(out_long) == 3
    out_short = stage24_0b.simulate_variant(
        v_atr,
        "short",
        bid_close,
        ask_close,
        atr_pips=5.0,
        entry_ask=1.0001,
        entry_bid=1.0000,
        pip=pip,
    )
    assert isinstance(out_short, tuple) and len(out_short) == 3
