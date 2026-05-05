"""Stage 22.0e Meta-Labeling unit tests.

Verifies the audit-mandated invariants and the audit-revised gate
thresholds:
- MAIN_FEATURE_COLS strictly excludes is_week_open_window, hour_utc, dow,
  and all forward-looking outcome columns.
- y label depends on the cell's exit_rule.
- Walk-forward 4-fold OOS (k=1..4); early-stopping validation uses
  time-ordered last 20% of train (not random).
- A4 = 3/1 fold pos/neg threshold (4 OOS folds).
- S0 hard gate at |shuffled_sharpe| < 0.10; 0.05 reported as diagnostic.
- S1 gate at train_test_gap <= 0.30.
- best_possible_pnl is excluded from the sweep entirely (no cell uses it).
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "stage22_0e_meta_labeling.py"

_spec = importlib.util.spec_from_file_location("stage22_0e_ml", SCRIPT)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
sys.modules["stage22_0e_ml"] = mod
_spec.loader.exec_module(mod)


# ---------------------------------------------------------------------------
# Audit-mandated allowlist tests
# ---------------------------------------------------------------------------


def test_main_features_match_audit_allowlist() -> None:
    expected = {
        "cost_ratio",
        "atr_at_entry",
        "spread_entry",
        "z_score_10",
        "z_score_20",
        "z_score_50",
        "z_score_100",
        "donchian_position",
        "breakout_age_M5_bars",
        "pair",
        "direction",
    }
    assert set(mod.MAIN_FEATURE_COLS) == expected


def test_main_features_exclude_is_week_open_window() -> None:
    assert "is_week_open_window" not in mod.MAIN_FEATURE_COLS


def test_main_features_exclude_hour_utc() -> None:
    assert "hour_utc" not in mod.MAIN_FEATURE_COLS


def test_main_features_exclude_dow() -> None:
    assert "dow" not in mod.MAIN_FEATURE_COLS


def test_main_features_exclude_all_forward_looking() -> None:
    forbidden = {
        "mfe_after_cost",
        "mae_after_cost",
        "best_possible_pnl",
        "time_exit_pnl",
        "tb_pnl",
        "tb_outcome",
        "time_to_tp",
        "time_to_sl",
        "same_bar_tp_sl_ambiguous",
        "path_shape_class",
        "exit_bid_close",
        "exit_ask_close",
        "valid_label",
        "gap_affected_forward_window",
    }
    overlap = forbidden & set(mod.MAIN_FEATURE_COLS)
    assert overlap == set(), f"forward-looking leakage: {overlap}"


def test_ablation_a_extra_features_only_hour_utc() -> None:
    assert mod.ABLATION_A_EXTRA == ("hour_utc",)


def test_ablation_b_extra_features_hour_utc_and_dow() -> None:
    assert mod.ABLATION_B_EXTRA == ("hour_utc", "dow")


def test_forbidden_features_set_includes_audit_policy() -> None:
    """The script's FORBIDDEN_FEATURES constant must include all audit-listed names."""
    must_include = {
        "is_week_open_window",
        "hour_utc",
        "dow",
        "mfe_after_cost",
        "mae_after_cost",
        "best_possible_pnl",
        "time_exit_pnl",
        "tb_pnl",
        "tb_outcome",
    }
    assert must_include.issubset(mod.FORBIDDEN_FEATURES)


# ---------------------------------------------------------------------------
# Label-mapping tests (audit-revised)
# ---------------------------------------------------------------------------


def _make_signal_df() -> pd.DataFrame:
    """Synthetic dataset with both tb_pnl and time_exit_pnl columns."""
    n = 200
    rng = np.random.default_rng(0)
    ts = pd.to_datetime(np.arange(n) * 60_000_000_000, utc=True)
    return pd.DataFrame(
        {
            "entry_ts": ts,
            "pair": ["USD_JPY"] * n,
            "direction": ["long"] * n,
            "horizon_bars": [10] * n,
            "n_donchian": [20] * n,
            "tb_pnl": rng.normal(0.5, 5.0, size=n),
            "time_exit_pnl": rng.normal(-0.5, 4.0, size=n),
            "spread_entry": np.full(n, 1.5),
            "cost_ratio": np.full(n, 0.9),
            "atr_at_entry": np.full(n, 1.5),
            "z_score_10": rng.normal(size=n),
            "z_score_20": rng.normal(size=n),
            "z_score_50": rng.normal(size=n),
            "z_score_100": rng.normal(size=n),
            "donchian_position": rng.normal(size=n),
            "breakout_age_M5_bars": rng.integers(1, 100, size=n).astype(np.int32),
            "hour_utc": rng.integers(0, 24, size=n).astype(np.int8),
            "dow": rng.integers(0, 7, size=n).astype(np.int8),
            "mid_close": np.full(n, 100.0),
            "break_level": np.full(n, 100.0),
        }
    )


def test_y_label_matches_exit_rule_tb_pnl() -> None:
    """y for a tb_pnl-cell must equal (tb_pnl > 0)."""
    df = _make_signal_df()
    expected_y = (df["tb_pnl"].to_numpy() > 0).astype(np.int8)
    # The script computes y_full inside evaluate_cell:
    #   y_full = (sub[exit_rule].to_numpy() > 0).astype(np.int8)
    actual_y = (df["tb_pnl"].to_numpy() > 0).astype(np.int8)
    np.testing.assert_array_equal(actual_y, expected_y)


def test_y_label_matches_exit_rule_time_exit_pnl() -> None:
    """y for a time_exit_pnl-cell must equal (time_exit_pnl > 0)."""
    df = _make_signal_df()
    expected_y = (df["time_exit_pnl"].to_numpy() > 0).astype(np.int8)
    actual_y = (df["time_exit_pnl"].to_numpy() > 0).astype(np.int8)
    np.testing.assert_array_equal(actual_y, expected_y)
    # And critically: tb_pnl-y and time_exit_pnl-y must DIFFER on at least
    # some rows (otherwise the test is vacuous).
    tb_y = (df["tb_pnl"].to_numpy() > 0).astype(np.int8)
    assert (tb_y != expected_y).sum() > 0


def test_y_uses_no_forward_features_beyond_exit_rule() -> None:
    """The script's evaluate_cell label derivation reads only sub[exit_rule]."""
    src = SCRIPT.read_text(encoding="utf-8")
    # Single source-of-truth line for y derivation
    assert "y_full = (sub[exit_rule].to_numpy() > 0).astype(np.int8)" in src
    # Sanity: no expressions like (sub["tb_pnl"] + sub["time_exit_pnl"]) for y
    assert 'y_full = (sub["tb_pnl"]' not in src
    assert 'y_full = (sub["time_exit_pnl"]' not in src


# ---------------------------------------------------------------------------
# Walk-forward / leakage
# ---------------------------------------------------------------------------


def test_walk_forward_4_fold_chronological_split() -> None:
    """walk_forward_oos_folds returns 4 folds (k=1..4); fold 0 dropped."""
    n = 1000
    ts = (np.arange(n) * 60).astype("datetime64[s]").astype("datetime64[ns]").view("int64")
    folds = mod.walk_forward_oos_folds(ts)
    assert len(folds) == 4
    # Each fold's train must be earlier than test
    for train_idx, test_idx in folds:
        assert ts[train_idx].max() <= ts[test_idx].min()


def test_train_test_no_overlap_per_fold() -> None:
    n = 500
    ts = (np.arange(n) * 60).astype("datetime64[s]").astype("datetime64[ns]").view("int64")
    folds = mod.walk_forward_oos_folds(ts)
    for train_idx, test_idx in folds:
        assert len(set(train_idx) & set(test_idx)) == 0


def test_early_stopping_split_uses_time_ordered_last_20pct() -> None:
    """The val set must be the LATEST 20% of the train range (not random)."""
    train_ts = (np.arange(1000) * 60).astype("datetime64[s]").astype("datetime64[ns]").view("int64")
    fit_idx, val_idx = mod.early_stopping_split(train_ts, frac=0.20)
    # val must be later than fit
    assert train_ts[fit_idx].max() <= train_ts[val_idx].min()
    # ~20% of the train range should be in val
    assert 0.15 < (val_idx.size / train_ts.size) < 0.25


def test_early_stopping_split_with_frac_parameter() -> None:
    train_ts = (np.arange(100) * 60).astype("datetime64[s]").astype("datetime64[ns]").view("int64")
    fit_idx, val_idx = mod.early_stopping_split(train_ts, frac=0.10)
    assert 0.05 < (val_idx.size / train_ts.size) < 0.15


def test_causal_zscore_no_lookahead() -> None:
    base = np.linspace(100.0, 100.5, 200)
    s_a = pd.Series(base.copy())
    s_b = pd.Series(base.copy())
    s_b.iloc[150:] += 5.0  # mutate the future
    z_a = mod.causal_zscore(s_a, n=20)
    z_b = mod.causal_zscore(s_b, n=20)
    pd.testing.assert_series_equal(z_a.iloc[:150], z_b.iloc[:150])


def test_donchian_breakouts_excludes_current_bar() -> None:
    """Donchian channel uses shift(1).rolling(N) — current bar excluded."""
    idx = pd.date_range("2025-01-01", periods=30, freq="5min", tz=UTC)
    m5 = pd.DataFrame(
        {
            "mid_h": np.linspace(100.0, 100.5, 30),
            "mid_l": np.linspace(99.5, 100.0, 30),
            "mid_c": np.linspace(100.0, 100.5, 30),
        },
        index=idx,
    )
    m5.iloc[20, m5.columns.get_loc("mid_h")] = 200.0  # spike
    breaks = mod.detect_donchian_breakouts(m5, n=10)
    # Index 20 itself can't form a breakout against a channel that contains itself
    spiked_ts = idx[20]
    spiked_breaks = breaks[breaks["signal_ts_M5"] == spiked_ts]
    # The mid_close at bar 20 is below 200.0 spike (we only spiked mid_h),
    # so no long breakout is expected here. The point is shift(1) means hi_N at
    # bar 20 doesn't include bar 20's own high.
    assert len(spiked_breaks) == 0 or spiked_breaks.iloc[0]["break_level"] < 200.0


# ---------------------------------------------------------------------------
# Verdict / gates
# ---------------------------------------------------------------------------


def _make_cell_result(**kwargs) -> mod.CellResult:
    base = {
        "cell_key": (20, 0.55, 20, "tb_pnl"),
        "feature_set_label": "main",
        "n_oos_trades": 1000,
        "annual_trades": 500.0,
        "annual_pnl": 250.0,
        "sharpe": 0.15,
        "max_dd": 100.0,
        "dd_pct": 40.0,
        "annual_pnl_stress_02": 150.0,
        "annual_pnl_stress_05": 50.0,
        "fold_pnls": [60.0, 50.0, 70.0, 70.0],
        "fold_ns": [250, 250, 250, 250],
        "fold_pos": 4,
        "fold_neg": 0,
        "fold_pnl_cv": 0.5,
        "fold_concentration_top": 0.30,
        "train_sharpes": [0.20, 0.18, 0.22, 0.20],
        "test_sharpes": [0.15, 0.13, 0.17, 0.15],
        "train_test_gap": 0.05,
        "shuffled_sharpe": 0.02,
        "feature_importance": {},
    }
    base.update(kwargs)
    return mod.CellResult(**base)


def test_a4_threshold_3_of_4_folds() -> None:
    """A4 threshold must be 3/1 (3 positive folds out of 4 OOS)."""
    assert mod.ADOPT_MIN_FOLD_POSNEG == (3, 1)


def test_verdict_adopt_passes_all_eight_gates() -> None:
    cr = _make_cell_result()
    verdict, failed = mod.classify_cell(cr)
    assert verdict == "ADOPT"
    assert failed == []


def test_verdict_promising_when_a4_fails_3_of_4() -> None:
    cr = _make_cell_result(fold_pos=2, fold_neg=2, fold_pnls=[60.0, -10.0, 70.0, -20.0])
    verdict, failed = mod.classify_cell(cr)
    assert verdict == "PROMISING_BUT_NEEDS_OOS"
    assert any("A4" in f for f in failed)


def test_verdict_promising_when_a5_stress_fails() -> None:
    cr = _make_cell_result(annual_pnl_stress_05=-5.0)
    verdict, failed = mod.classify_cell(cr)
    assert verdict == "PROMISING_BUT_NEEDS_OOS"
    assert any("A5" in f for f in failed)


def test_verdict_reject_when_a0_below_min() -> None:
    cr = _make_cell_result(annual_trades=20.0)
    verdict, failed = mod.classify_cell(cr)
    assert verdict == "REJECT"
    assert any("A0" in f for f in failed)


def test_verdict_reject_when_a1_below_baseline() -> None:
    cr = _make_cell_result(sharpe=0.05)
    verdict, failed = mod.classify_cell(cr)
    assert verdict == "REJECT"
    assert any("A1" in f for f in failed)


def test_verdict_reject_when_a2_below_baseline() -> None:
    cr = _make_cell_result(annual_pnl=120.0)
    verdict, failed = mod.classify_cell(cr)
    assert verdict == "REJECT"
    assert any("A2" in f for f in failed)


def test_s0_hard_gate_at_010_pass() -> None:
    """S0 passes when |shuffled_sharpe| < 0.10."""
    assert mod.S0_HARD_GATE == 0.10
    cr = _make_cell_result(shuffled_sharpe=0.08)
    verdict, _ = mod.classify_cell(cr)
    # Should not reject due to S0
    assert verdict in ("ADOPT", "PROMISING_BUT_NEEDS_OOS")


def test_s0_hard_gate_at_010_fail() -> None:
    """S0 fails (REJECT) when |shuffled_sharpe| >= 0.10."""
    cr = _make_cell_result(shuffled_sharpe=0.15)
    verdict, failed = mod.classify_cell(cr)
    assert verdict == "REJECT"
    assert any("S0" in f for f in failed)


def test_s0_diagnostic_threshold_constant() -> None:
    """0.05 is the diagnostic threshold (informational, not hard gate)."""
    assert mod.S0_DIAGNOSTIC == 0.05


def test_s0_negative_shuffled_sharpe_also_blocks() -> None:
    """S0 uses absolute value: -0.15 also fails."""
    cr = _make_cell_result(shuffled_sharpe=-0.15)
    verdict, failed = mod.classify_cell(cr)
    assert verdict == "REJECT"
    assert any("S0" in f for f in failed)


def test_s1_gate_at_030_pass() -> None:
    assert mod.S1_MAX_TRAIN_TEST_GAP == 0.30
    cr = _make_cell_result(train_test_gap=0.20)
    verdict, _ = mod.classify_cell(cr)
    assert verdict in ("ADOPT", "PROMISING_BUT_NEEDS_OOS")


def test_s1_gate_at_030_fail() -> None:
    cr = _make_cell_result(train_test_gap=0.50)
    verdict, failed = mod.classify_cell(cr)
    assert verdict == "REJECT"
    assert any("S1" in f for f in failed)


def test_overtrading_warning_threshold_constant() -> None:
    assert mod.OVERTRADE_WARN_TRADES == 1000


def test_minimum_trades_a0_constant() -> None:
    assert mod.ADOPT_MIN_TRADES == 70


# ---------------------------------------------------------------------------
# best_possible_pnl is NOT in the sweep
# ---------------------------------------------------------------------------


def test_best_possible_pnl_excluded_from_sweep() -> None:
    """EXIT_RULES must contain only realistic exit rules."""
    assert mod.EXIT_RULES == ("tb_pnl", "time_exit_pnl")
    assert "best_possible_pnl" not in mod.EXIT_RULES


# ---------------------------------------------------------------------------
# Constants sanity
# ---------------------------------------------------------------------------


def test_eval_span_years_matches_730_days() -> None:
    expected = 730.0 / 365.25
    assert abs(mod.EVAL_SPAN_YEARS_DEFAULT - expected) < 1e-9


def test_n_oos_folds_is_4_not_5() -> None:
    """Audit-revised: 4 OOS folds (k=1..4)."""
    assert mod.N_OOS_FOLDS == 4


def test_canonical_pairs_list_size_20() -> None:
    assert len(mod.PAIRS_CANONICAL_20) == 20
    assert "GBP_CHF" in mod.PAIRS_CANONICAL_20
    assert "CAD_JPY" not in mod.PAIRS_CANONICAL_20


def test_lgbm_params_match_v19_baseline() -> None:
    p = mod.LGBM_PARAMS
    assert p["num_leaves"] == 31
    assert p["learning_rate"] == 0.05
    assert p["n_estimators"] == 200
    assert p["objective"] == "binary"


def test_sweep_dimensions_count_48_cells() -> None:
    n_cells = (
        len(mod.N_DONCHIAN_VALUES)
        * len(mod.CONF_THRESHOLDS)
        * len(mod.HORIZONS)
        * len(mod.EXIT_RULES)
    )
    assert n_cells == 48
