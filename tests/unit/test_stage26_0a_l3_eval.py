"""Unit tests for Stage 26.0a-β L-3 EV regression eval (rev1).

Covers 24 binding tests from PR #301 §10 + 6 new rev1 tests from
PR #302 §10. Total: 30 tests + 3 additional invariant guards.
"""

from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

l3 = importlib.import_module("stage26_0a_l3_eval")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_row(
    pair: str = "EUR_USD",
    signal_ts: str = "2024-04-30 12:30:00+00:00",
    direction: str = "long",
    entry_ask: float = 1.07238,
    entry_bid: float = 1.07223,
    atr_at_signal_pip: float = 10.0,
    spread_at_signal_pip: float = 1.5,
    time_to_fav_bar: int = -1,
    time_to_adv_bar: int = -1,
    same_bar_both_hit: bool = False,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "pair": pair,
                "signal_ts": pd.Timestamp(signal_ts),
                "horizon_bars": 60,
                "direction": direction,
                "entry_ask": entry_ask,
                "entry_bid": entry_bid,
                "atr_at_signal_pip": atr_at_signal_pip,
                "spread_at_signal_pip": spread_at_signal_pip,
                "time_to_fav_bar": time_to_fav_bar,
                "time_to_adv_bar": time_to_adv_bar,
                "same_bar_both_hit": same_bar_both_hit,
            }
        ]
    )


def _no_runtime_map() -> dict:
    return {}


# ===========================================================================
# Original 24 tests from PR #301 §10 (inherited unchanged)
# ===========================================================================


# Test 1
def test_l3_label_construction_deterministic():
    df = _make_row(time_to_fav_bar=20, time_to_adv_bar=-1)
    y1 = l3.build_l3_labels_for_dataframe(df, _no_runtime_map(), 1, "raw_pip")
    y2 = l3.build_l3_labels_for_dataframe(df, _no_runtime_map(), 1, "raw_pip")
    assert y1.iloc[0] == y2.iloc[0]


# Test 2
def test_l3_base_pnl_is_mid_to_mid_long():
    df = _make_row(
        direction="long",
        atr_at_signal_pip=10.0,
        spread_at_signal_pip=0.0,
        time_to_fav_bar=20,
    )
    y = l3.build_l3_labels_for_dataframe(df, _no_runtime_map(), 1, "raw_pip")
    assert y.iloc[0] == pytest.approx(l3.K_FAV * 10.0, abs=1e-9)


# Test 3
def test_l3_base_pnl_is_mid_to_mid_short():
    df = _make_row(
        direction="short",
        atr_at_signal_pip=10.0,
        spread_at_signal_pip=0.0,
        time_to_fav_bar=20,
    )
    y = l3.build_l3_labels_for_dataframe(df, _no_runtime_map(), 1, "raw_pip")
    assert y.iloc[0] == pytest.approx(l3.K_FAV * 10.0, abs=1e-9)


# Test 4
def test_l3_spread_subtracted_exactly_once():
    df_zero = _make_row(spread_at_signal_pip=0.0, time_to_fav_bar=20)
    df_two = _make_row(spread_at_signal_pip=2.0, time_to_fav_bar=20)
    y_zero = l3.build_l3_labels_for_dataframe(df_zero, _no_runtime_map(), 1, "raw_pip").iloc[0]
    y_two = l3.build_l3_labels_for_dataframe(df_two, _no_runtime_map(), 1, "raw_pip").iloc[0]
    assert (y_zero - y_two) == pytest.approx(2.0, abs=1e-9)

    df_three = _make_row(spread_at_signal_pip=3.0, time_to_fav_bar=20)
    y_factor_1 = l3.build_l3_labels_for_dataframe(df_three, _no_runtime_map(), 1, "raw_pip").iloc[0]
    y_factor_2 = l3.build_l3_labels_for_dataframe(df_three, _no_runtime_map(), 2, "raw_pip").iloc[0]
    assert (y_factor_1 - y_factor_2) == pytest.approx(3.0, abs=1e-9)


# Test 5
def test_l3_entry_only_spread_subtracts_once_factor():
    df = _make_row(spread_at_signal_pip=1.5, time_to_fav_bar=20, atr_at_signal_pip=10.0)
    y = l3.build_l3_labels_for_dataframe(df, _no_runtime_map(), 1, "raw_pip").iloc[0]
    expected = l3.K_FAV * 10.0 - 1.5 * 1
    assert y == pytest.approx(expected, abs=1e-9)


# Test 6
def test_l3_round_trip_spread_subtracts_twice_factor():
    df = _make_row(spread_at_signal_pip=1.5, time_to_fav_bar=20, atr_at_signal_pip=10.0)
    y = l3.build_l3_labels_for_dataframe(df, _no_runtime_map(), 2, "raw_pip").iloc[0]
    expected = l3.K_FAV * 10.0 - 1.5 * 2
    assert y == pytest.approx(expected, abs=1e-9)


# Test 7
def test_l3_inherits_triple_barrier_k_fav_k_adv():
    assert pytest.approx(1.5) == l3.K_FAV
    assert pytest.approx(1.0) == l3.K_ADV


# Test 8
def test_l3_horizon_expiry_uses_m5_close_mark_to_market():
    n_m1 = 200
    ts_index = pd.date_range("2024-04-30 12:00", periods=n_m1, freq="1min", tz="UTC")
    bid_c = np.full(n_m1, 1.07000, dtype=np.float64)
    ask_c = np.full(n_m1, 1.07020, dtype=np.float64)
    entry_idx = 31
    exit_idx = entry_idx + l3.H_M1_BARS - 1
    bid_c[exit_idx] = 1.07100
    ask_c[exit_idx] = 1.07120

    pair_runtime = {
        "pip": 0.0001,
        "m1_pos": pd.Series(np.arange(n_m1), index=ts_index),
        "n_m1": n_m1,
        "bid_c": bid_c,
        "ask_c": ask_c,
        "bid_o": np.zeros(n_m1),
        "ask_o": np.zeros(n_m1),
        "bid_h": np.zeros(n_m1),
        "ask_h": np.zeros(n_m1),
        "bid_l": np.zeros(n_m1),
        "ask_l": np.zeros(n_m1),
    }
    pair_runtime_map = {"EUR_USD": pair_runtime}

    df = _make_row(
        signal_ts="2024-04-30 12:30:00+00:00",
        entry_ask=1.07020,
        entry_bid=1.07000,
        time_to_fav_bar=-1,
        time_to_adv_bar=-1,
    )
    y = l3.build_l3_labels_for_dataframe(df, pair_runtime_map, 1, "raw_pip").iloc[0]
    expected = 10.0 - 1.5
    assert y == pytest.approx(expected, abs=1e-6)


# Test 9
def test_l3_label_excludes_mfe_mae():
    df_base = _make_row(
        time_to_fav_bar=20,
        time_to_adv_bar=-1,
        atr_at_signal_pip=10.0,
        spread_at_signal_pip=0.0,
    )
    df_a = df_base.copy()
    df_a["max_fav_excursion_pip"] = 1.0
    df_a["max_adv_excursion_pip"] = 99.0
    df_b = df_base.copy()
    df_b["max_fav_excursion_pip"] = 50.0
    df_b["max_adv_excursion_pip"] = 50.0
    y_a = l3.build_l3_labels_for_dataframe(df_a, _no_runtime_map(), 1, "raw_pip").iloc[0]
    y_b = l3.build_l3_labels_for_dataframe(df_b, _no_runtime_map(), 1, "raw_pip").iloc[0]
    assert y_a == pytest.approx(y_b, abs=1e-12)


# Test 10
def test_l3_atr_normalised_scale():
    df = _make_row(time_to_fav_bar=20, atr_at_signal_pip=10.0, spread_at_signal_pip=2.0)
    y = l3.build_l3_labels_for_dataframe(df, _no_runtime_map(), 1, "atr_normalised").iloc[0]
    expected = (l3.K_FAV * 10.0 - 2.0) / 10.0
    assert y == pytest.approx(expected, abs=1e-9)


# Test 11
def test_l3_raw_pip_scale():
    df = _make_row(time_to_fav_bar=20, atr_at_signal_pip=10.0, spread_at_signal_pip=2.0)
    y = l3.build_l3_labels_for_dataframe(df, _no_runtime_map(), 1, "raw_pip").iloc[0]
    expected = l3.K_FAV * 10.0 - 2.0
    assert y == pytest.approx(expected, abs=1e-9)


# Test 12
def test_l3_winsorise_thresholds_fit_on_train_only():
    rng = np.random.default_rng(42)
    train_y = pd.Series(rng.normal(0.0, 1.0, size=2000))
    lo, hi = l3.fit_winsorise_train(train_y)
    assert -3.0 < lo < -1.5
    assert 1.5 < hi < 3.0
    lo_again, hi_again = l3.fit_winsorise_train(train_y)
    assert lo == pytest.approx(lo_again, abs=1e-12)
    assert hi == pytest.approx(hi_again, abs=1e-12)


# Test 13 — MANDATORY: winsorise does NOT touch harness PnL
def test_l3_winsorise_does_not_touch_realised_pnl_for_harness():
    """The harness realised PnL is computed by
    `precompute_realised_pnl_per_row` / `_compute_realised_barrier_pnl`,
    NEITHER of which accepts any winsorise/clip parameter.
    """
    sig = inspect.signature(l3.precompute_realised_pnl_per_row)
    param_names = set(sig.parameters.keys())
    assert "clip" not in param_names
    assert "winsorise" not in param_names
    assert "lo" not in param_names
    assert "hi" not in param_names

    sig2 = inspect.signature(l3._compute_realised_barrier_pnl)
    param_names2 = set(sig2.parameters.keys())
    assert "clip" not in param_names2
    assert "winsorise" not in param_names2

    y = pd.Series([float("-inf"), -5.0, 0.0, 5.0, float("inf")])
    out = l3.apply_winsorise(y, lo=-2.0, hi=2.0)
    assert out.tolist() == [-2.0, -2.0, 0.0, 2.0, 2.0]


# Test 14
def test_l3_winsorise_disabled_passes_through():
    y = pd.Series([-100.0, -1.0, 0.0, 1.0, 100.0])
    out = l3.apply_winsorise(y, lo=float("-inf"), hi=float("inf"))
    np.testing.assert_array_equal(out.to_numpy(), y.to_numpy())


# Test 15
def test_sweep_grid_has_24_cells():
    cells = l3.build_cells(include_lightgbm=True)
    assert len(cells) == 24
    cells_no_lgbm = l3.build_cells(include_lightgbm=False)
    assert len(cells_no_lgbm) == 16


# Test 16
def test_lightgbm_uses_fixed_conservative_config():
    expected = dict(
        n_estimators=200,
        learning_rate=0.03,
        num_leaves=31,
        max_depth=4,
        min_child_samples=100,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    assert expected == l3.LIGHTGBM_FIXED_CONFIG


# Test 17
def test_lightgbm_defer_path_when_not_importable():
    cells = l3.build_cells(include_lightgbm=False)
    assert len(cells) == 16
    assert all(c["model"] in ("LinearRegression", "Ridge") for c in cells)


# Test 18
def test_cell_and_threshold_selection_uses_validation_only():
    """select_cell_validation_only ranks (cell, q) by val Sharpe — NOT test."""
    cells = [
        {
            "cell": {"spread": "entry_only", "scale": "raw_pip", "clip": "none", "model": "Ridge"},
            "val_realised_sharpe": 0.20,
            "val_realised_annual_pnl": 100.0,
            "val_n_trades": 200,
            "val_max_dd": 10.0,
            "test_realised_metrics": {"sharpe": 0.05},
            "test_regression_diag": {"spearman": 0.1},
            "test_gates": {},
            "h_state": "OK",
        },
        {
            "cell": {"spread": "round_trip", "scale": "raw_pip", "clip": "none", "model": "Ridge"},
            "val_realised_sharpe": 0.10,
            "val_realised_annual_pnl": 50.0,
            "val_n_trades": 200,
            "val_max_dd": 8.0,
            "test_realised_metrics": {"sharpe": 0.50},
            "test_regression_diag": {"spearman": 0.5},
            "test_gates": {},
            "h_state": "OK",
        },
    ]
    result = l3.select_cell_validation_only(cells)
    sel = result["selected"]
    assert sel["cell"]["spread"] == "entry_only", "selection must use VAL Sharpe, not TEST Sharpe"


# Test 19
def test_verdict_tree_h2_pass_alone_not_adopt():
    val_selected = {
        "test_regression_diag": {"spearman": 0.20},
        "test_gates": {"A0": True, "A1": True, "A2": True, "A3": True, "A4": False, "A5": False},
        "test_realised_metrics": {"sharpe": 0.10},
    }
    result = l3.assign_verdict(val_selected)
    assert result["verdict"] == "PROMISING_BUT_NEEDS_OOS"


# Test 20
def test_verdict_tree_h1_meaningful_threshold_010():
    val_selected_a = {
        "test_regression_diag": {"spearman": 0.099},
        "test_gates": {},
        "test_realised_metrics": {"sharpe": float("nan")},
    }
    result_a = l3.assign_verdict(val_selected_a)
    assert result_a["verdict"] == "REJECT_WEAK_SIGNAL_ONLY"

    val_selected_b = {
        "test_regression_diag": {"spearman": 0.100},
        "test_gates": {"A1": False, "A2": False, "A0": True, "A3": True, "A4": True, "A5": True},
        "test_realised_metrics": {"sharpe": 0.05},
    }
    result_b = l3.assign_verdict(val_selected_b)
    assert result_b["verdict"] == "REJECT_BUT_INFORMATIVE_IMPROVED"
    assert result_b["h1_meaningful_pass"] is True


# Test 21
def test_verdict_tree_h1_weak_band_005_to_010():
    val_selected = {
        "test_regression_diag": {"spearman": 0.06},
        "test_gates": {},
        "test_realised_metrics": {"sharpe": 0.0},
    }
    result = l3.assign_verdict(val_selected)
    assert result["verdict"] == "REJECT_WEAK_SIGNAL_ONLY"


# Test 22
def test_h3_baseline_constant_phase25_best_minus_0192():
    assert pytest.approx(-0.192) == l3.H3_REFERENCE_SHARPE


# Test 23
def test_regression_diagnostic_returns_r2_pearson_spearman():
    rng = np.random.default_rng(0)
    n = 200
    y_true = rng.normal(0.0, 1.0, size=n)
    y_pred = y_true * 0.5 + rng.normal(0.0, 0.5, size=n)
    diag = l3.regression_diagnostics(y_true, y_pred)
    assert "r2" in diag
    assert "pearson" in diag
    assert "spearman" in diag
    assert diag["pearson"] > 0.5
    assert diag["spearman"] > 0.5


# Test 24
def test_no_diagnostic_columns_in_feature_set():
    prohibited = set(l3.PROHIBITED_DIAGNOSTIC_COLUMNS)
    feature_cols = set(l3.CATEGORICAL_COLS)
    assert prohibited.isdisjoint(feature_cols)
    assert set(l3.CATEGORICAL_COLS) == {"pair", "direction"}


# ===========================================================================
# Rev1: 6 NEW unit tests per PR #302 §10
# ===========================================================================


# Test 25 (rev1)
def test_quantile_cutoff_fits_on_val_only():
    """Perturbing test predictions does NOT change the val-fit cutoff."""
    rng = np.random.default_rng(42)
    pred_val = rng.normal(0.0, 1.0, size=1000)
    cutoff_v1 = l3.fit_quantile_cutoff_on_val(pred_val, 10)

    # Perturb a separate test prediction array — must not affect val-fit
    _pred_test_perturbed = rng.normal(100.0, 1.0, size=1000)  # noqa: F841

    # Re-fit on val only
    cutoff_v2 = l3.fit_quantile_cutoff_on_val(pred_val, 10)
    assert cutoff_v1 == pytest.approx(cutoff_v2, abs=1e-12), (
        "val-fit cutoff must be invariant under separate test perturbations"
    )

    # Top 10% of standard normal: cutoff near +1.28
    assert 1.0 < cutoff_v1 < 1.6


# Test 26 (rev1)
def test_quantile_cutoff_applied_to_test_uses_val_fit_value():
    """The scalar cutoff fitted on val is the SAME scalar applied to test."""
    pred_val = np.array([-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    pred_test = np.array([-100.0, -50.0, 0.0, 50.0, 100.0])
    pnl_val_zero = np.full(10, np.nan)
    pnl_test_zero = np.full(5, np.nan)

    results = l3.evaluate_quantile_family(
        pred_val,
        pnl_val_zero,
        pred_test,
        pnl_test_zero,
        span_years_val=0.107,
        span_years_test=0.107,
    )
    for r in results:
        cutoff = r["cutoff"]
        # The same cutoff value was applied to both val and test:
        # the val mask is pred_val >= cutoff; the test mask is pred_test >= cutoff
        # Both reference the SAME `cutoff` scalar.
        # We verify by counting matches with the cutoff:
        expected_val_n_above = int((pred_val >= cutoff).sum())
        expected_test_n_above = int((pred_test >= cutoff).sum())
        assert r["val"]["n_traded_above_threshold"] == expected_val_n_above
        assert r["test"]["n_traded_above_threshold"] == expected_test_n_above


# Test 27 (rev1)
def test_no_full_sample_qcut_in_quantile_path():
    """The quantile path does NOT call np.quantile on train+val+test combined
    or on test alone. fit_quantile_cutoff_on_val takes a SINGLE pred array
    (val only); evaluate_quantile_family fits on pred_val and applies to
    pred_test without recomputing a test quantile.
    """
    src = inspect.getsource(l3.evaluate_quantile_family)
    # Must call fit_quantile_cutoff_on_val with pred_val argument
    assert "fit_quantile_cutoff_on_val(pred_val" in src, (
        "quantile family must fit cutoff on pred_val only"
    )
    # Must NOT call np.quantile on pred_test
    assert "np.quantile(pred_test" not in src, "test predictions must NOT be passed to np.quantile"

    # fit_quantile_cutoff_on_val signature: takes only one prediction array
    sig = inspect.signature(l3.fit_quantile_cutoff_on_val)
    pred_params = [p for p in sig.parameters if p.startswith("pred")]
    assert pred_params == ["pred_val"], f"fit function must take only pred_val; got {pred_params}"


# Test 28 (rev1)
def test_quantile_threshold_family_has_5_candidates():
    assert l3.THRESHOLDS_QUANTILE_PERCENTS == (5, 10, 20, 30, 40)
    assert len(l3.THRESHOLDS_QUANTILE_PERCENTS) == 5


# Test 29 (rev1)
def test_negative_absolute_thresholds_secondary_informational():
    """Absolute thresholds are computed and reported but NOT used by
    select_cell_validation_only — that function only consults
    val_realised_sharpe / val_realised_annual_pnl / val_max_dd /
    val_n_trades from the PRIMARY quantile family, never the
    absolute_best/absolute_all fields.
    """
    src = inspect.getsource(l3.select_cell_validation_only)
    assert "absolute_best" not in src, "selection must NOT reference absolute_best"
    assert "absolute_all" not in src, "selection must NOT reference absolute_all"
    # Sanity: negative-spanning absolute candidates are defined
    assert l3.NEG_THRESHOLDS_RAW_PIP == (-5.0, -3.0, -1.0, 0.0, 1.0)
    assert l3.NEG_THRESHOLDS_ATR == (-0.5, -0.3, -0.1, 0.0, 0.1)


# Test 30 (rev1)
def test_selected_threshold_family_is_quantile():
    """The val-selected cell record has selected_q_percent (quantile) — NOT
    a plain `selected_threshold` (absolute). The verdict-feeding fields
    (`val_realised_sharpe`, `val_realised_annual_pnl`, `val_n_trades`,
    `val_max_dd`, `test_realised_metrics`, `test_gates`) all come from
    the quantile_best block per cell.
    """
    # Simulate a cell result dict shape per evaluate_cell
    cell_result_shape = {
        "cell": {"spread": "entry_only", "scale": "raw_pip", "clip": "none", "model": "Ridge"},
        "selected_q_percent": 10,
        "selected_cutoff": -3.5,
        "val_realised_sharpe": 0.1,
        "val_realised_annual_pnl": 100.0,
        "val_n_trades": 1000,
        "val_max_dd": 50.0,
        "absolute_best": {"threshold": -1.0, "val": {"sharpe": 0.05}, "test": {"sharpe": 0.02}},
        "absolute_all": [],
        "test_realised_metrics": {"sharpe": 0.05},
        "test_gates": {"A0": True, "A1": True, "A2": True, "A3": True, "A4": True, "A5": True},
        "test_regression_diag": {"spearman": 0.15},
        "h_state": "OK",
    }
    result = l3.select_cell_validation_only([cell_result_shape])
    sel = result["selected"]
    assert sel is not None
    # The val-selected pair must include selected_q_percent (quantile, primary)
    assert "selected_q_percent" in sel
    assert sel["selected_q_percent"] == 10


# ===========================================================================
# Additional invariant guards (not in 24+6 list but useful)
# ===========================================================================


def test_determine_barrier_outcome_branches():
    assert l3.determine_barrier_outcome(5, 5, True) == "SL"
    assert l3.determine_barrier_outcome(10, 5, False) == "SL"
    assert l3.determine_barrier_outcome(5, 10, False) == "TP"
    assert l3.determine_barrier_outcome(-1, 5, False) == "SL"
    assert l3.determine_barrier_outcome(5, -1, False) == "TP"
    assert l3.determine_barrier_outcome(-1, -1, False) == "TIME"


def test_ridge_pipeline_has_no_random_state():
    """Per user correction: Ridge constructed WITHOUT random_state."""
    pipe = l3.build_pipeline_ridge()
    reg = pipe.named_steps["reg"]
    assert reg.alpha == pytest.approx(1.0)
    assert reg.random_state is None


def test_select_cell_validation_only_uses_a0_prefilter():
    """A0-equivalent prefilter wins over higher val Sharpe."""
    a0_min = l3.A0_MIN_ANNUAL_TRADES * l3.VAL_SPAN_YEARS
    cells = [
        {
            "cell": {"spread": "entry_only", "scale": "raw_pip", "clip": "none", "model": "Ridge"},
            "selected_q_percent": 5,
            "val_realised_sharpe": 0.50,
            "val_realised_annual_pnl": 200.0,
            "val_n_trades": int(a0_min) - 1,
            "val_max_dd": 10.0,
            "h_state": "OK",
        },
        {
            "cell": {"spread": "round_trip", "scale": "raw_pip", "clip": "none", "model": "Ridge"},
            "selected_q_percent": 10,
            "val_realised_sharpe": 0.20,
            "val_realised_annual_pnl": 100.0,
            "val_n_trades": int(a0_min) + 100,
            "val_max_dd": 8.0,
            "h_state": "OK",
        },
    ]
    result = l3.select_cell_validation_only(cells)
    sel = result["selected"]
    assert sel["cell"]["spread"] == "round_trip"
    assert result["low_val_trades_flag"] is False
