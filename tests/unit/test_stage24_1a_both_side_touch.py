"""Unit tests for Stage 24.1a both-side touch envelope eval.

Implements the unit-test contract from `docs/design/ng10_envelope_confirmation.md`
§7. Tests are organised per envelope §7 categories with HARD invariants
explicitly marked.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage24_0b = importlib.import_module("stage24_0b_trailing_stop_eval")
stage24_1a = importlib.import_module("stage24_1a_both_side_touch_eval")


PIP = 0.0001
DATA_DIR = REPO_ROOT / "data"
_REPO_HAS_M1_DATA = (DATA_DIR / "candles_USD_JPY_M1_730d_BA.jsonl").exists()
_REPO_HAS_FROZEN = (REPO_ROOT / "artifacts" / "stage24_0a" / "frozen_entry_streams.json").exists()
_skip_no_data = pytest.mark.skipif(
    not _REPO_HAS_M1_DATA, reason="M1 BA data not present (CI env without data/ files)"
)
_skip_no_data_or_frozen = pytest.mark.skipif(
    not (_REPO_HAS_M1_DATA and _REPO_HAS_FROZEN),
    reason="M1 BA data or 24.0a frozen JSON not present (CI env without data/ files)",
)


def _arr(*v: float) -> np.ndarray:
    return np.asarray(v, dtype=float)


# ---------------------------------------------------------------------------
# §7.1 Trigger boundary tests (4)
# ---------------------------------------------------------------------------


def test_long_tp_touch_no_close_above_fills_at_tp():
    """T3_breakeven long: bid_h reaches TP, bid_c stays below TP -> fill at exact TP."""
    entry_ask = 1.0000
    atr_pips = 10.0
    atr_price = atr_pips * PIP
    tp_level = entry_ask + stage24_0b.TP_ATR_MULT * atr_price
    bid_h = _arr(tp_level + 1e-7)
    bid_l = _arr(entry_ask - 0.5 * PIP)
    bid_c = _arr(entry_ask - 0.1 * PIP)
    exit_idx, pnl, reason = stage24_1a._simulate_breakeven_long_envelope(
        bid_h,
        bid_l,
        bid_c,
        be_threshold=99.0,
        atr_pips=atr_pips,
        entry_ask=entry_ask,
        pip=PIP,
    )
    assert reason == "tp"
    expected_pnl = (tp_level - entry_ask) / PIP
    assert pnl == expected_pnl


def test_long_tp_no_touch_no_fill():
    entry_ask = 1.0000
    atr_pips = 10.0
    atr_price = atr_pips * PIP
    tp_level = entry_ask + stage24_0b.TP_ATR_MULT * atr_price
    bid_h = _arr(tp_level - PIP, tp_level - PIP)
    bid_l = _arr(entry_ask - PIP, entry_ask - PIP)
    bid_c = _arr(entry_ask, entry_ask)
    exit_idx, pnl, reason = stage24_1a._simulate_breakeven_long_envelope(
        bid_h,
        bid_l,
        bid_c,
        99.0,
        atr_pips,
        entry_ask,
        PIP,
    )
    assert reason == "time"


def test_short_tp_touch_no_close_below_fills_at_tp():
    entry_bid = 1.0000
    atr_pips = 10.0
    atr_price = atr_pips * PIP
    tp_level = entry_bid - stage24_0b.TP_ATR_MULT * atr_price
    ask_h = _arr(entry_bid + 0.5 * PIP)
    ask_l = _arr(tp_level - 1e-7)
    ask_c = _arr(entry_bid + 0.1 * PIP)
    exit_idx, pnl, reason = stage24_1a._simulate_breakeven_short_envelope(
        ask_h,
        ask_l,
        ask_c,
        99.0,
        atr_pips,
        entry_bid,
        PIP,
    )
    assert reason == "tp"
    expected_pnl = (entry_bid - tp_level) / PIP
    assert pnl == expected_pnl


def test_short_tp_no_touch_no_fill():
    entry_bid = 1.0000
    atr_pips = 10.0
    atr_price = atr_pips * PIP
    tp_level = entry_bid - stage24_0b.TP_ATR_MULT * atr_price
    ask_h = _arr(entry_bid + PIP, entry_bid + PIP)
    ask_l = _arr(tp_level + PIP, tp_level + PIP)
    ask_c = _arr(entry_bid, entry_bid)
    exit_idx, pnl, reason = stage24_1a._simulate_breakeven_short_envelope(
        ask_h,
        ask_l,
        ask_c,
        99.0,
        atr_pips,
        entry_bid,
        PIP,
    )
    assert reason == "time"


# ---------------------------------------------------------------------------
# §7.2 SL slippage proxy tests (4)
# ---------------------------------------------------------------------------


def test_long_sl_touch_close_above_fills_at_sl():
    """bid_l <= SL but bid_c > SL -> fill at exact SL (min(SL, bid_c) = SL)."""
    entry_ask = 1.0000
    atr_pips = 10.0
    atr_price = atr_pips * PIP
    sl_level = entry_ask - stage24_0b.SL_ATR_MULT * atr_price
    tp_level = entry_ask + stage24_0b.TP_ATR_MULT * atr_price
    bid_h = _arr(entry_ask + 0.1 * PIP)
    bid_l = _arr(sl_level - 1e-7)
    bid_c = _arr(sl_level + 0.2 * PIP)
    assert bid_c[0] > sl_level
    assert bid_h[0] < tp_level
    exit_idx, pnl, reason = stage24_1a._simulate_breakeven_long_envelope(
        bid_h,
        bid_l,
        bid_c,
        99.0,
        atr_pips,
        entry_ask,
        PIP,
    )
    assert reason == "sl"
    expected_pnl = (sl_level - entry_ask) / PIP
    assert pnl == expected_pnl


def test_long_sl_touch_close_below_fills_at_close():
    """bid_l <= SL AND bid_c < SL -> fill at bid_c (slippage; min(SL, bid_c) = bid_c)."""
    entry_ask = 1.0000
    atr_pips = 10.0
    atr_price = atr_pips * PIP
    sl_level = entry_ask - stage24_0b.SL_ATR_MULT * atr_price
    tp_level = entry_ask + stage24_0b.TP_ATR_MULT * atr_price
    bid_h = _arr(entry_ask - 0.1 * PIP)
    bid_l = _arr(sl_level - 5 * PIP)
    bid_c = _arr(sl_level - 3 * PIP)
    assert bid_c[0] < sl_level
    assert bid_h[0] < tp_level
    exit_idx, pnl, reason = stage24_1a._simulate_breakeven_long_envelope(
        bid_h,
        bid_l,
        bid_c,
        99.0,
        atr_pips,
        entry_ask,
        PIP,
    )
    assert reason == "sl"
    expected_pnl = (bid_c[0] - entry_ask) / PIP
    assert abs(pnl - expected_pnl) < 1e-9


def test_short_sl_touch_close_below_fills_at_sl():
    """ask_h >= SL but ask_c < SL -> fill at exact SL (max(SL, ask_c) = SL)."""
    entry_bid = 1.0000
    atr_pips = 10.0
    atr_price = atr_pips * PIP
    sl_level = entry_bid + stage24_0b.SL_ATR_MULT * atr_price
    ask_h = _arr(sl_level + 1e-7)
    ask_l = _arr(entry_bid - 0.5 * PIP)
    ask_c = _arr(sl_level - 0.2 * PIP)
    exit_idx, pnl, reason = stage24_1a._simulate_breakeven_short_envelope(
        ask_h,
        ask_l,
        ask_c,
        99.0,
        atr_pips,
        entry_bid,
        PIP,
    )
    assert reason == "sl"
    expected_pnl = (entry_bid - sl_level) / PIP
    assert pnl == expected_pnl


def test_short_sl_touch_close_above_fills_at_close():
    """ask_h >= SL AND ask_c > SL -> fill at ask_c (slippage; max(SL, ask_c) = ask_c)."""
    entry_bid = 1.0000
    atr_pips = 10.0
    atr_price = atr_pips * PIP
    sl_level = entry_bid + stage24_0b.SL_ATR_MULT * atr_price
    ask_h = _arr(sl_level + 5 * PIP)
    ask_l = _arr(entry_bid + 0.1 * PIP)
    ask_c = _arr(sl_level + 3 * PIP)
    exit_idx, pnl, reason = stage24_1a._simulate_breakeven_short_envelope(
        ask_h,
        ask_l,
        ask_c,
        99.0,
        atr_pips,
        entry_bid,
        PIP,
    )
    assert reason == "sl"
    expected_pnl = (entry_bid - ask_c[0]) / PIP
    assert abs(pnl - expected_pnl) < 1e-9


# ---------------------------------------------------------------------------
# §7.3 Same-bar SL-first invariant (2 HARD)
# ---------------------------------------------------------------------------


def test_same_bar_both_hit_long_fills_at_sl_formula_hard():
    """HARD invariant: bid_h>=TP AND bid_l<=SL in the same bar -> fill at SL,
    NEVER at TP."""
    entry_ask = 1.0000
    atr_pips = 10.0
    atr_price = atr_pips * PIP
    sl_level = entry_ask - stage24_0b.SL_ATR_MULT * atr_price
    tp_level = entry_ask + stage24_0b.TP_ATR_MULT * atr_price
    bid_h = _arr(tp_level + PIP)
    bid_l = _arr(sl_level - PIP)
    bid_c = _arr(entry_ask)
    assert bid_h[0] >= tp_level
    assert bid_l[0] <= sl_level
    exit_idx, pnl, reason = stage24_1a._simulate_breakeven_long_envelope(
        bid_h,
        bid_l,
        bid_c,
        99.0,
        atr_pips,
        entry_ask,
        PIP,
    )
    assert reason == "sl", f"HARD invariant violated: same-bar both-hit must fill SL, got {reason}"
    # Fill = min(sl_level, bid_c[0]) = min(sl_level, entry_ask) = sl_level (since sl < entry)
    expected_pnl = (sl_level - entry_ask) / PIP
    assert pnl == expected_pnl


def test_same_bar_both_hit_short_fills_at_sl_formula_hard():
    entry_bid = 1.0000
    atr_pips = 10.0
    atr_price = atr_pips * PIP
    sl_level = entry_bid + stage24_0b.SL_ATR_MULT * atr_price
    tp_level = entry_bid - stage24_0b.TP_ATR_MULT * atr_price
    ask_h = _arr(sl_level + PIP)
    ask_l = _arr(tp_level - PIP)
    ask_c = _arr(entry_bid)
    exit_idx, pnl, reason = stage24_1a._simulate_breakeven_short_envelope(
        ask_h,
        ask_l,
        ask_c,
        99.0,
        atr_pips,
        entry_bid,
        PIP,
    )
    assert reason == "sl", f"HARD invariant violated: same-bar both-hit must fill SL, got {reason}"
    expected_pnl = (entry_bid - sl_level) / PIP
    assert pnl == expected_pnl


# ---------------------------------------------------------------------------
# §7.4 No-lookahead invariants (2)
# ---------------------------------------------------------------------------


def test_no_lookahead_t_minus_1_unused():
    """If bid_h[t-1] >= TP but bid_h[t] < TP, no fill at t."""
    entry_ask = 1.0000
    atr_pips = 10.0
    atr_price = atr_pips * PIP
    tp_level = entry_ask + stage24_0b.TP_ATR_MULT * atr_price
    # bar 0: prior favorable touch (would be t-1 from bar 1's view)
    # bar 1: NO touch
    bid_h = _arr(tp_level + PIP, tp_level - PIP)
    bid_l = _arr(entry_ask - 0.1 * PIP, entry_ask - 0.1 * PIP)
    bid_c = _arr(entry_ask, entry_ask)
    # The simulator should fire on bar 0 (where bid_h crosses), not on bar 1.
    # If bar 1 fires due to lookahead at t-1, that's a bug. Bar 0 firing is correct.
    exit_idx, pnl, reason = stage24_1a._simulate_breakeven_long_envelope(
        bid_h,
        bid_l,
        bid_c,
        99.0,
        atr_pips,
        entry_ask,
        PIP,
    )
    assert reason == "tp"
    assert exit_idx == 0  # fired at bar 0, not bar 1


def test_no_lookahead_t_plus_1_unused():
    """If bid_h[t] < TP but bid_h[t+1] >= TP, no fill at t (must wait for bar t+1)."""
    entry_ask = 1.0000
    atr_pips = 10.0
    atr_price = atr_pips * PIP
    tp_level = entry_ask + stage24_0b.TP_ATR_MULT * atr_price
    bid_h = _arr(tp_level - PIP, tp_level + PIP)
    bid_l = _arr(entry_ask - 0.1 * PIP, entry_ask - 0.1 * PIP)
    bid_c = _arr(entry_ask, entry_ask)
    exit_idx, pnl, reason = stage24_1a._simulate_breakeven_long_envelope(
        bid_h,
        bid_l,
        bid_c,
        99.0,
        atr_pips,
        entry_ask,
        PIP,
    )
    assert reason == "tp"
    assert exit_idx == 1  # fired at bar 1, not bar 0


# ---------------------------------------------------------------------------
# §7.5 Data API backward compat (2)
# ---------------------------------------------------------------------------


@_skip_no_data
def test_load_m1_ba_returns_full_ohlc():
    """load_m1_ba already returns the 8 OHLC columns; no API change needed."""
    df = stage23_0a.load_m1_ba("USD_JPY", days=730)
    expected_cols = {"bid_o", "bid_h", "bid_l", "bid_c", "ask_o", "ask_h", "ask_l", "ask_c"}
    assert set(df.columns) >= expected_cols, (
        f"Missing OHLC columns: {expected_cols - set(df.columns)}"
    )


def test_load_m1_ba_default_signature_unchanged():
    """Backward compat: load_m1_ba accepts (pair, days=730) only — no new
    required args. 24.0b/0c/0d call sites must keep working."""
    import inspect

    sig = inspect.signature(stage23_0a.load_m1_ba)
    params = list(sig.parameters.values())
    # Must accept positional (pair, days=730) — exactly the signature 24.0b/0c/0d use.
    assert len(params) == 2
    assert params[0].name == "pair"
    assert params[1].name == "days"
    assert params[1].default == 730


# ---------------------------------------------------------------------------
# §7.6 Phase 24 reproducibility regression (3; smoke-mode in CI)
# ---------------------------------------------------------------------------


def _smoke_invoke(script_name: str) -> int:
    """Invoke a stage script in --smoke mode and return rc. Used for
    regression check that 24.0b/0c/0d still execute under the new code."""
    rc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script_name), "--smoke"],
        capture_output=True,
        timeout=180,
    )
    return rc.returncode


@_skip_no_data_or_frozen
def test_24_0b_close_only_smoke_regression():
    """Smoke regression: 24.0b still executes successfully under unchanged
    code path. Full byte-identical reproduction is checked locally if
    feasible (see eval_report.md reproducibility note)."""
    rc = _smoke_invoke("stage24_0b_trailing_stop_eval.py")
    assert rc == 0


@_skip_no_data_or_frozen
def test_24_0c_close_only_smoke_regression():
    rc = _smoke_invoke("stage24_0c_partial_exit_eval.py")
    assert rc == 0


@_skip_no_data_or_frozen
def test_24_0d_close_only_smoke_regression():
    rc = _smoke_invoke("stage24_0d_regime_conditional_eval.py")
    assert rc == 0


# ---------------------------------------------------------------------------
# Variant identity (per direction §8: exactly 24.0b's 11 variants)
# ---------------------------------------------------------------------------


def test_variants_are_exactly_24_0b_parity():
    assert stage24_1a.VARIANTS is stage24_0b.VARIANTS, (
        "24.1a must use exactly the same 11 variants as stage24_0b (per direction §8). "
        "Do not redefine — import the list verbatim."
    )
    assert len(stage24_1a.VARIANTS) == 11


def test_routing_thresholds_fixed():
    """Routing diagnostics H1/H2/H3 are FIXED constants per direction §5."""
    assert stage24_1a.H1_THRESHOLD_SHARPE == 0.082
    assert stage24_1a.H2_LIFT_THRESHOLD == 0.20
    assert stage24_1a.PHASE_24_0B_BEST_SHARPE == -0.177
    assert abs(stage24_1a.H2_NEW_SHARPE_THRESHOLD - 0.023) < 1e-9


# ---------------------------------------------------------------------------
# Routing classifier behaviour
# ---------------------------------------------------------------------------


def test_routing_h1_when_sharpe_clears_a1():
    best = {"sharpe": 0.10}
    label, _ = stage24_1a.classify_routing_hypothesis(best)
    assert label == "H1"


def test_routing_h2_when_sharpe_lifts_but_not_a1():
    best = {"sharpe": 0.05}  # +0.05 vs -0.177 = +0.227 lift
    label, _ = stage24_1a.classify_routing_hypothesis(best)
    assert label == "H2"


def test_routing_h3_when_no_lift():
    best = {"sharpe": -0.10}  # +0.077 lift < +0.20
    label, _ = stage24_1a.classify_routing_hypothesis(best)
    assert label == "H3"


def test_routing_h3_when_no_eligible_cell():
    label, _ = stage24_1a.classify_routing_hypothesis(None)
    assert label == "H3"


# ---------------------------------------------------------------------------
# Trail variant: bid_low touch trigger
# ---------------------------------------------------------------------------


def test_long_trail_bid_low_touch_fills_at_trail_when_close_above():
    """T1_ATR long: trail level = running_max - K*ATR. If bid_l touches
    trail but bid_c is above trail, fill at min(trail, bid_c) = trail."""
    entry_ask = 1.0000
    atr_pips = 10.0
    k = 1.0
    # bar 0: close at entry, no touch
    # bar 1: close at entry+5pip (trail = entry+5pip - 10pip = entry-5pip)
    #        bid_l dips below trail (touch); bid_c stays above trail
    bid_h = _arr(entry_ask + 0.1 * PIP, entry_ask + 5 * PIP)
    bid_l = _arr(entry_ask - 0.1 * PIP, entry_ask - 6 * PIP)
    bid_c = _arr(entry_ask, entry_ask + 5 * PIP)
    # On bar 1: running_max = entry + 5pip. Trail = entry - 5pip.
    # bid_l[1] = entry - 6pip <= trail; touch fires.
    # Fill = min(trail, bid_c[1]) = min(entry-5pip, entry+5pip) = entry-5pip
    exit_idx, pnl, reason = stage24_1a._simulate_atr_long_envelope(
        bid_h,
        bid_l,
        bid_c,
        k,
        atr_pips,
        entry_ask,
        PIP,
    )
    assert reason == "trail"
    assert exit_idx == 1
    expected_pnl = (entry_ask - 5 * PIP - entry_ask) / PIP  # -5 pip
    assert abs(pnl - expected_pnl) < 1e-9


def test_long_trail_no_touch_time_exit():
    entry_ask = 1.0000
    atr_pips = 10.0
    k = 1.0
    bid_h = _arr(entry_ask + 0.1 * PIP, entry_ask + 0.2 * PIP)
    bid_l = _arr(entry_ask - 0.1 * PIP, entry_ask - 0.05 * PIP)
    bid_c = _arr(entry_ask, entry_ask + 0.05 * PIP)
    exit_idx, pnl, reason = stage24_1a._simulate_atr_long_envelope(
        bid_h,
        bid_l,
        bid_c,
        k,
        atr_pips,
        entry_ask,
        PIP,
    )
    assert reason == "time"
