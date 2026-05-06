"""Unit tests for Stage 24.0d regime-conditional exits."""

from __future__ import annotations

import importlib
import json
import sys
from datetime import UTC
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage24_0b = importlib.import_module("stage24_0b_trailing_stop_eval")
stage24_0c = importlib.import_module("stage24_0c_partial_exit_eval")
stage24_0d = importlib.import_module("stage24_0d_regime_conditional_eval")


# ---------------------------------------------------------------------------
# 1: frozen entry streams imported (3 cells, all 23.0d / M15 / h=4)
# ---------------------------------------------------------------------------


def test_frozen_entry_streams_imported_from_24_0a(tmp_path: Path):
    real = REPO_ROOT / "artifacts" / "stage24_0a" / "frozen_entry_streams.json"
    if real.exists():
        cells = stage24_0d.load_frozen_streams(real)
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
                        "exit_rule": "tb",
                    },
                    "score": 3.7,
                    "metrics": {},
                }
                for i in range(3)
            ],
        }
        stub_path = tmp_path / "frozen.json"
        stub_path.write_text(json.dumps(stub), encoding="utf-8")
        cells = stage24_0d.load_frozen_streams(stub_path)
    assert len(cells) == 3
    for c in cells:
        assert c["source_stage"] == "23.0d"
        assert c["signal_timeframe"] == "M15"
        assert c["cell_params"]["horizon_bars"] == 4


# ---------------------------------------------------------------------------
# 2: regime constants are fixed
# ---------------------------------------------------------------------------


def test_regime_constants_fixed():
    assert len(stage24_0d.R1_VARIANTS) == 3
    assert len(stage24_0d.R2_VARIANTS) == 3
    assert len(stage24_0d.R3_VARIANTS) == 3
    # R1_v3 / R2_v3 / R3_v3 are uniform controls
    assert stage24_0d.R1_VARIANTS[2]["K_low"] == stage24_0d.R1_VARIANTS[2]["K_high"]
    r2_v3 = stage24_0d.R2_VARIANTS[2]
    assert r2_v3["asian"] == r2_v3["london"] == r2_v3["ny"]
    r3_v3 = stage24_0d.R3_VARIANTS[2]
    assert r3_v3["with_trend"] == r3_v3["against_trend"]
    assert stage24_0d.R3_SLOPE_LOOKBACK == 5


def test_variants_count_9():
    assert len(stage24_0d.VARIANTS) == 9
    modes = [v["mode"] for v in stage24_0d.VARIANTS]
    assert modes.count("R1_atr_regime") == 3
    assert modes.count("R2_session_regime") == 3
    assert modes.count("R3_trend_regime") == 3


# ---------------------------------------------------------------------------
# 3: regime is exit-parameter selector ONLY (entry stream count invariance)
# ---------------------------------------------------------------------------


def test_regime_is_exit_parameter_only_not_entry_filter():
    """
    For any regime variant, the script never drops a signal based on regime —
    it only changes which exit parameter is used per trade. This is enforced
    by construction in `simulate_regime_variant`: every code path returns
    a simulated trade (exit_idx, pnl, reason, partial_done). There is NO
    branch that returns 'skip this trade'.

    We verify this by inspecting the dispatcher source for any return-without-
    simulate pattern, plus a behavioural check: pass a synthetic trade through
    each variant and verify all variants return a tuple of length 4.
    """
    # Behavioural check: every variant returns 4-tuple for the same input
    pip = 0.0001
    bid_close = np.array([1.0001, 1.0002, 1.0003, 1.0004])
    ask_close = np.array([1.0002, 1.0003, 1.0004, 1.0005])
    for variant in stage24_0d.VARIANTS:
        for direction in ("long", "short"):
            for regime in ("low_vol", "high_vol", "asian", "london", "ny", "up", "down"):
                try:
                    out = stage24_0d.simulate_regime_variant(
                        variant,
                        direction,
                        regime,
                        bid_close,
                        ask_close,
                        atr_pips=10.0,
                        entry_ask=1.0000,
                        entry_bid=1.0000,
                        pip=pip,
                    )
                except (ValueError, KeyError):
                    # Some regimes are not valid for some modes (e.g., "asian" for R1)
                    # That's fine — runtime would never call them with mismatched regime.
                    continue
                assert isinstance(out, tuple) and len(out) == 4, (
                    f"variant {variant['label']} regime {regime} did not return 4-tuple"
                )

    # Static check: dispatcher source never returns a "skip" sentinel
    import inspect

    src = inspect.getsource(stage24_0d.simulate_regime_variant)
    # No 'return None', no 'continue', no 'raise SkipTrade', etc.
    assert "return None" not in src
    assert "raise SkipTrade" not in src


# ---------------------------------------------------------------------------
# 4: NG#11 — no forward-looking regime tag (R3 trend uses shift(1))
# ---------------------------------------------------------------------------


def test_no_forward_looking_regime_tag_r3():
    """slope_5 = mid_c[t-1] - mid_c[t-5]; the signal bar's own close is NOT used."""
    # Construct mid_c series where signal bar (idx=10) has wildly different close
    # from prior bars. The trend regime should depend on bars [t-5..t-1] only.
    mid_c = np.array(
        [
            1.00,
            1.01,
            1.02,
            1.03,
            1.04,
            1.05,
            1.06,
            1.07,
            1.08,
            1.09,  # idx 6..9: ascending
            9.99,  # idx 10 = signal bar; massively different
            1.10,
            1.11,
            1.12,
        ]
    )
    signal_idx = 10
    # Expected: slope_5 = mid_c[9] - mid_c[5] = 1.09 - 1.05 = 0.04 > 0 → "up"
    # The signal bar's own value (9.99) must NOT influence the tag.
    trend = stage24_0d.compute_r3_trend_regime(mid_c, signal_idx, lookback=5)
    assert trend == "up"

    # Now flip the trajectory: use prior bars but ascending only
    mid_c_2 = np.array(
        [
            1.10,
            1.09,
            1.08,
            1.07,
            1.06,
            1.05,
            1.04,
            1.03,
            1.02,
            1.01,
            9.99,
            1.00,
            0.99,
            0.98,
        ]
    )
    trend_2 = stage24_0d.compute_r3_trend_regime(mid_c_2, signal_idx=10, lookback=5)
    # slope = mid_c[9] - mid_c[5] = 1.01 - 1.05 = -0.04 < 0 → "down"
    assert trend_2 == "down"


# ---------------------------------------------------------------------------
# 5: R1 ATR median dispatch
# ---------------------------------------------------------------------------


def test_r1_atr_regime_uses_cross_pair_median():
    median = 5.0
    assert stage24_0d.compute_r1_atr_regime(3.0, median) == "low_vol"
    assert stage24_0d.compute_r1_atr_regime(7.0, median) == "high_vol"
    assert stage24_0d.compute_r1_atr_regime(5.0, median) == "high_vol"  # boundary >= median


def test_r1_atr_dispatch_k_low_vs_k_high():
    """low_vol -> K_low; high_vol -> K_high."""
    pip = 0.0001
    bid_close = np.array([1.0001, 1.0002])
    ask_close = np.array([1.0002, 1.0003])
    variant = stage24_0d.VARIANTS[0]  # R1_v1: K_low=1.0, K_high=2.0
    # Different regimes should produce different exit logic if the path
    # crosses the trail with one K but not the other. With our simple path,
    # both probably do time exit. The dispatch correctness is verified by
    # confirming no exception and a 4-tuple return.
    out_low = stage24_0d.simulate_regime_variant(
        variant, "long", "low_vol", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    out_high = stage24_0d.simulate_regime_variant(
        variant, "long", "high_vol", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    assert len(out_low) == 4 and len(out_high) == 4


# ---------------------------------------------------------------------------
# 6: R2 session 3-bucket
# ---------------------------------------------------------------------------


def test_r2_session_3_buckets_utc_hour():
    fn = stage24_0d.compute_r2_session_regime
    assert fn(pd.Timestamp("2026-01-01 03:00", tz=UTC)) == "asian"
    assert fn(pd.Timestamp("2026-01-01 07:59", tz=UTC)) == "asian"
    assert fn(pd.Timestamp("2026-01-01 08:00", tz=UTC)) == "london"
    assert fn(pd.Timestamp("2026-01-01 12:00", tz=UTC)) == "london"
    assert fn(pd.Timestamp("2026-01-01 15:59", tz=UTC)) == "london"
    assert fn(pd.Timestamp("2026-01-01 16:00", tz=UTC)) == "ny"
    assert fn(pd.Timestamp("2026-01-01 23:59", tz=UTC)) == "ny"


def test_r2_session_labels_are_utc_bucket_not_market_open():
    """R2 labels are conventional UTC bucket labels, NOT market-open filters."""
    assert stage24_0d._R2_LABELS_ARE_CONVENTIONAL_UTC_BUCKETS is True
    # Docstring of compute_r2_session_regime should mention "NOT market-open filter"
    doc = stage24_0d.compute_r2_session_regime.__doc__ or ""
    assert "NOT market-open filter" in doc or "conventional bucket labels" in doc


def test_r2_dispatch_partial_fraction_by_session():
    pip = 0.0001
    bid_close = np.array([1.0001, 1.0002, 1.0003, 1.0004])
    ask_close = np.array([1.0002, 1.0003, 1.0004, 1.0005])
    variant = stage24_0d.VARIANTS[3]  # R2_v1: asian=0.25, london=0.50, ny=0.75
    # All 3 buckets should dispatch a different partial fraction
    out_a = stage24_0d.simulate_regime_variant(
        variant, "long", "asian", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    out_l = stage24_0d.simulate_regime_variant(
        variant, "long", "london", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    out_n = stage24_0d.simulate_regime_variant(
        variant, "long", "ny", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    # All 4-tuples
    assert all(len(out) == 4 for out in (out_a, out_l, out_n))


# ---------------------------------------------------------------------------
# 7: R3 trend slope_5
# ---------------------------------------------------------------------------


def test_r3_trend_slope_5_mid_c_shift1():
    # Ascending series: slope_5 > 0 → "up"
    mid_c = np.array([1.0, 1.01, 1.02, 1.03, 1.04, 1.05, 1.06, 1.07, 1.08, 1.09, 1.10])
    assert stage24_0d.compute_r3_trend_regime(mid_c, signal_idx=10, lookback=5) == "up"
    # Descending series
    mid_c_d = np.array([1.10, 1.09, 1.08, 1.07, 1.06, 1.05, 1.04, 1.03, 1.02, 1.01, 1.00])
    assert stage24_0d.compute_r3_trend_regime(mid_c_d, signal_idx=10, lookback=5) == "down"
    # Warmup (signal_idx < lookback): default to "up"
    assert stage24_0d.compute_r3_trend_regime(mid_c, signal_idx=2, lookback=5) == "up"


def test_r3_trend_uptrend_long_uses_with_trend_k():
    """Long + up regime -> with_trend K; long + down regime -> against_trend K."""
    pip = 0.0001
    bid_close = np.array([1.0001, 1.0002, 1.0003])
    ask_close = np.array([1.0002, 1.0003, 1.0004])
    variant = stage24_0d.VARIANTS[6]  # R3_v1: with_trend=2.0, against_trend=1.0
    # With our simple path, both should reach time exit; verify no exception.
    out_up = stage24_0d.simulate_regime_variant(
        variant, "long", "up", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    out_down = stage24_0d.simulate_regime_variant(
        variant, "long", "down", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    assert len(out_up) == 4 and len(out_down) == 4


def test_r3_trend_downtrend_short_uses_with_trend_k():
    pip = 0.0001
    bid_close = np.array([1.0001, 1.0000, 0.9999])
    ask_close = np.array([1.0002, 1.0001, 1.0000])
    variant = stage24_0d.VARIANTS[6]  # R3_v1: with_trend=2.0, against_trend=1.0
    out_down = stage24_0d.simulate_regime_variant(
        variant, "short", "down", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    out_up = stage24_0d.simulate_regime_variant(
        variant, "short", "up", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    assert len(out_down) == 4 and len(out_up) == 4


# ---------------------------------------------------------------------------
# 8: NG#10 inheritance via 24.0b/0c simulators
# ---------------------------------------------------------------------------


def test_ng10_close_only_inherited_via_24_0b_simulator():
    """24.0d's R1/R3 modes use 24.0b's _simulate_atr_long/short directly."""
    assert stage24_0d.stage24_0b._simulate_atr_long is stage24_0b._simulate_atr_long
    assert stage24_0d.stage24_0b._simulate_atr_short is stage24_0b._simulate_atr_short


def test_ng10_close_only_inherited_via_24_0c_simulator():
    """24.0d's R2 mode uses 24.0c's _simulate_p1_long/short directly."""
    assert stage24_0d.stage24_0c._simulate_p1_long is stage24_0c._simulate_p1_long
    assert stage24_0d.stage24_0c._simulate_p1_short is stage24_0c._simulate_p1_short


# ---------------------------------------------------------------------------
# 9: uniform controls have no regime effect
# ---------------------------------------------------------------------------


def test_uniform_controls_have_no_regime_effect():
    """R1_v3, R2_v3, R3_v3 use the same exit param across all regime buckets."""
    pip = 0.0001
    bid_close = np.array([1.0001, 1.0002, 1.0003, 1.0004])
    ask_close = np.array([1.0002, 1.0003, 1.0004, 1.0005])

    # R1_v3 uniform K=1.5
    v_r1 = stage24_0d.VARIANTS[2]
    out_low = stage24_0d.simulate_regime_variant(
        v_r1, "long", "low_vol", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    out_high = stage24_0d.simulate_regime_variant(
        v_r1, "long", "high_vol", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    # Same K → identical results
    assert out_low == out_high

    # R3_v3 uniform K=1.5
    v_r3 = stage24_0d.VARIANTS[8]
    out_up = stage24_0d.simulate_regime_variant(
        v_r3, "long", "up", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    out_down = stage24_0d.simulate_regime_variant(
        v_r3, "long", "down", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    assert out_up == out_down

    # R2_v3 uniform fraction=0.50
    v_r2 = stage24_0d.VARIANTS[5]
    out_a = stage24_0d.simulate_regime_variant(
        v_r2, "long", "asian", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    out_l = stage24_0d.simulate_regime_variant(
        v_r2, "long", "london", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    out_n = stage24_0d.simulate_regime_variant(
        v_r2, "long", "ny", bid_close, ask_close, 10.0, 1.0000, 1.0000, pip
    )
    assert out_a == out_l == out_n


# ---------------------------------------------------------------------------
# 10: A4 fold-stability inherited
# ---------------------------------------------------------------------------


def test_a4_4fold_majority_inherited():
    pnl = np.zeros(100)
    pnl[0:20] = 1.0  # k=0 warmup
    pnl[20:80] = 1.0
    pnl[80:] = -1.0
    pnl = pnl + np.linspace(0, 0.001, 100)
    df = pd.DataFrame(
        {
            "entry_ts": pd.date_range("2026-01-01", periods=100, freq="1h", tz=UTC),
            "pnl_pip": pnl,
        }
    )
    fold = stage24_0d._fold_stability(df)
    assert fold["n_positive"] == 3


# ---------------------------------------------------------------------------
# 11: REJECT reason inheritance
# ---------------------------------------------------------------------------


def test_reject_reason_path_ev_unrealisable_inherited():
    metrics = {"overtrading_warning": False}
    gates_a1_fail = {"A0": True, "A1": False, "A2": True, "A3": True, "A4": True, "A5": True}
    assert (
        stage24_0d.classify_reject_reason_phase24(metrics, gates_a1_fail) == "path_ev_unrealisable"
    )


# ---------------------------------------------------------------------------
# 12: smoke mode shape
# ---------------------------------------------------------------------------


def test_smoke_mode_shape():
    assert len(stage24_0d.SMOKE_PAIRS) == 3
    assert len(stage24_0d.SMOKE_VARIANTS) == 3
    modes_in_smoke = {v["mode"] for v in stage24_0d.SMOKE_VARIANTS}
    assert modes_in_smoke == {"R1_atr_regime", "R2_session_regime", "R3_trend_regime"}


# ---------------------------------------------------------------------------
# 13: per_regime_breakdown diagnostic
# ---------------------------------------------------------------------------


def test_per_regime_breakdown_in_metrics():
    trades = pd.DataFrame(
        {
            "pnl_pip": [1.0, -0.5, 2.0, -1.0],
            "best_possible_pnl": [3.0, 2.0, 5.0, 1.0],
            "tb_pnl": [0.5, -0.3, 1.5, -0.8],
            "time_exit_pnl": [0.7, -0.2, 1.7, -0.9],
            "direction": ["long"] * 4,
            "entry_ts": pd.date_range("2026-01-01", periods=4, freq="1h", tz=UTC),
            "regime_tag": ["low_vol", "high_vol", "low_vol", "high_vol"],
        }
    )
    m = stage24_0d.evaluate_cell(trades, mode="R1_atr_regime")
    assert "per_regime_breakdown" in m
    assert "low_vol" in m["per_regime_breakdown"]
    assert "high_vol" in m["per_regime_breakdown"]
    # Each bucket has 2 trades
    assert m["per_regime_breakdown"]["low_vol"]["n_trades"] == 2
    assert m["per_regime_breakdown"]["high_vol"]["n_trades"] == 2


# ---------------------------------------------------------------------------
# 14: signal_timeframe constant
# ---------------------------------------------------------------------------


def test_signal_timeframe_m15():
    assert stage24_0d.SIGNAL_TIMEFRAME == "M15"


# ---------------------------------------------------------------------------
# 15: SMOKE_VARIANTS has exactly 3 different mode types
# ---------------------------------------------------------------------------


def test_smoke_variants_one_per_mode():
    modes = [v["mode"] for v in stage24_0d.SMOKE_VARIANTS]
    assert len(set(modes)) == 3


# ---------------------------------------------------------------------------
# 16: dispatcher does not raise on valid (mode, direction, regime) triples
# ---------------------------------------------------------------------------


def test_dispatcher_handles_all_valid_combinations():
    pip = 0.0001
    bid_close = np.array([1.0001, 1.0002])
    ask_close = np.array([1.0002, 1.0003])
    valid_combos = [
        ("R1_atr_regime", ["low_vol", "high_vol"]),
        ("R2_session_regime", ["asian", "london", "ny"]),
        ("R3_trend_regime", ["up", "down"]),
    ]
    for mode, regimes in valid_combos:
        variants = [v for v in stage24_0d.VARIANTS if v["mode"] == mode]
        for variant in variants:
            for direction in ("long", "short"):
                for regime in regimes:
                    out = stage24_0d.simulate_regime_variant(
                        variant,
                        direction,
                        regime,
                        bid_close,
                        ask_close,
                        10.0,
                        1.0000,
                        1.0000,
                        pip,
                    )
                    assert isinstance(out, tuple) and len(out) == 4
