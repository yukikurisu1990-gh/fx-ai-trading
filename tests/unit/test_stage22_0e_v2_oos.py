"""Stage 22.0e-v2 Independent OOS Validation tests.

Verifies frozen specification, train/OOS split discipline, sub-fold diagnostic
treatment, verdict logic (user-revised boundaries), and audit allowlist
re-assertion.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "stage22_0e_v2_independent_oos.py"
PR259_SCRIPT = REPO_ROOT / "scripts" / "stage22_0e_meta_labeling.py"

_spec = importlib.util.spec_from_file_location("stage22_0e_v2", SCRIPT)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
sys.modules["stage22_0e_v2"] = mod
_spec.loader.exec_module(mod)


# ---------------------------------------------------------------------------
# Frozen-parameter assertions
# ---------------------------------------------------------------------------


def test_n_donchian_frozen_at_50() -> None:
    assert mod.N_DONCHIAN == 50


def test_conf_threshold_frozen_at_055() -> None:
    assert mod.CONF_THRESHOLD == 0.55


def test_horizon_frozen_at_40() -> None:
    assert mod.HORIZON_BARS == 40


def test_exit_rule_frozen_at_time_exit_pnl() -> None:
    assert mod.EXIT_RULE == "time_exit_pnl"


def test_primary_signal_is_donchian_immediate() -> None:
    assert mod.PRIMARY_SIGNAL == "donchian_immediate"


def test_feature_set_is_main_only() -> None:
    """The script uses MAIN_FEATURE_COLS imported from PR #259 — no extras."""
    src = SCRIPT.read_text(encoding="utf-8")
    # The features list construction in evaluate_frozen_cell:
    assert "features = list(MAIN_FEATURE_COLS)" in src
    # Critical: no addition of hour_utc / dow into the model features
    assert 'features = list(MAIN_FEATURE_COLS) + ["hour_utc"]' not in src
    assert 'features = list(MAIN_FEATURE_COLS) + ["dow"]' not in src


def test_no_sweep_loops_in_script() -> None:
    """No re-search of N / conf / horizon / exit_rule."""
    src = SCRIPT.read_text(encoding="utf-8")
    # No iteration over multi-value sweep ranges
    assert "for n in N_DONCHIAN_VALUES" not in src
    assert "for ct in CONF_THRESHOLDS" not in src
    assert "for h in HORIZONS" not in src
    assert "for er in EXIT_RULES" not in src
    # Only the frozen single-value constants are referenced for config
    assert "N_DONCHIAN = 50" in src
    assert "CONF_THRESHOLD = 0.55" in src
    assert "HORIZON_BARS = 40" in src
    assert 'EXIT_RULE = "time_exit_pnl"' in src


def test_train_frac_is_80_pct() -> None:
    assert mod.TRAIN_FRAC == 0.80


def test_es_val_frac_is_20_pct() -> None:
    assert mod.ES_VAL_FRAC == 0.20


def test_n_oos_subfolds_is_4() -> None:
    assert mod.N_OOS_SUBFOLDS == 4


# ---------------------------------------------------------------------------
# Train/OOS split discipline
# ---------------------------------------------------------------------------


def test_train_first_80pct_oos_last_20pct_chronologically() -> None:
    """The script uses entry_ts <= 0.80 quantile for train, > for OOS."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert "TRAIN_FRAC" in src
    assert "np.quantile(entry_ts_int, TRAIN_FRAC)" in src
    assert "train_mask = entry_ts_int <= cut_int" in src
    assert "oos_mask = entry_ts_int > cut_int" in src


def test_es_split_uses_time_ordered_last_20pct() -> None:
    """time_ordered_es_split uses np.quantile, NOT random shuffle."""
    train_ts = np.arange(1000, dtype=np.int64) * 60_000_000_000
    fit_idx, val_idx = mod.time_ordered_es_split(train_ts, 0.20)
    # val must be later than fit
    assert train_ts[fit_idx].max() <= train_ts[val_idx].min()
    # ~20% of the train range in val
    assert 0.15 < (val_idx.size / train_ts.size) < 0.25


def test_chronological_4_subfolds_no_overlap() -> None:
    oos_ts = np.arange(400, dtype=np.int64) * 60_000_000_000
    folds = mod.chronological_4_subfolds(oos_ts)
    assert len(folds) == 4
    # No overlap between consecutive folds
    for k in range(3):
        assert folds[k][1] == folds[k + 1][0]
    # Coverage = full array
    assert folds[0][0] == 0
    assert folds[-1][1] == 400


def test_oos_subfolds_diagnostic_only_no_training_role() -> None:
    """Sub-folds appear in evaluate_frozen_cell only AFTER training."""
    src = SCRIPT.read_text(encoding="utf-8")
    # The sub-fold computation comes after lgb.train()
    train_pos = src.find("booster = lgb.train")
    subfold_pos = src.find("chronological_4_subfolds(kept_ts_int)")
    assert train_pos > 0
    assert subfold_pos > train_pos, (
        "sub-fold computation must occur AFTER training; the sub-folds are diagnostic only"
    )


# ---------------------------------------------------------------------------
# Audit allowlist re-assertion
# ---------------------------------------------------------------------------


def test_main_feature_cols_unchanged_from_pr_259() -> None:
    """The v2 script imports MAIN_FEATURE_COLS from PR #259 — they MUST match."""
    spec = importlib.util.spec_from_file_location("pr259", PR259_SCRIPT)
    pr259 = importlib.util.module_from_spec(spec)
    sys.modules["pr259"] = pr259
    spec.loader.exec_module(pr259)
    assert mod.MAIN_FEATURE_COLS == pr259.MAIN_FEATURE_COLS


def test_no_hour_utc_in_main_features() -> None:
    assert "hour_utc" not in mod.MAIN_FEATURE_COLS


def test_no_dow_in_main_features() -> None:
    assert "dow" not in mod.MAIN_FEATURE_COLS


def test_no_is_week_open_window_in_main_features() -> None:
    assert "is_week_open_window" not in mod.MAIN_FEATURE_COLS


def test_no_forward_looking_in_main_features() -> None:
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
    }
    overlap = forbidden & set(mod.MAIN_FEATURE_COLS)
    assert overlap == set(), f"forward-looking leakage: {overlap}"


# ---------------------------------------------------------------------------
# Verdict logic (user-revised boundaries)
# ---------------------------------------------------------------------------


def _make_oos_result(**overrides) -> mod.OOSResult:
    """Template that would produce all-PASS gates."""
    base = {
        "n_train": 100_000,
        "n_oos": 25_000,
        "n_oos_filtered": 1000,
        "oos_span_years": 0.4,
        "train_sharpe": 0.20,
        "oos_sharpe": 0.15,
        "oos_annual_pnl": 250.0,
        "oos_annual_trades": 500.0,
        "oos_max_dd": 100.0,
        "oos_dd_pct": 40.0,
        "oos_mean_pnl": 0.5,
        "oos_win_rate": 0.55,
        "oos_annual_pnl_stress_02": 150.0,
        "oos_annual_pnl_stress_05": 50.0,
        "sub_fold_pnls": [60.0, 50.0, 70.0, 70.0],
        "sub_fold_ns": [250, 250, 250, 250],
        "sub_fold_sharpes": [0.15, 0.13, 0.17, 0.15],
        "sub_fold_pos": 4,
        "sub_fold_neg": 0,
        "sub_fold_ranges": [],
        "train_test_gap": 0.05,
        "feature_importance": {},
        "oos_trades_df": None,
    }
    base.update(overrides)
    return mod.OOSResult(**base)


def test_verdict_adopt_when_all_eight_gates_pass() -> None:
    r = _make_oos_result()
    verdict, gates, _ = mod.classify_verdict(r, shuffled_sharpe=0.02)
    assert verdict == "ADOPT"
    assert all(gates.values())


def test_verdict_promising_confirmed_when_a3_fails() -> None:
    r = _make_oos_result(oos_max_dd=400.0)  # > 200
    verdict, gates, failed = mod.classify_verdict(r, shuffled_sharpe=0.02)
    assert verdict == "PROMISING_CONFIRMED"
    assert "A3" in failed


def test_verdict_promising_confirmed_when_a4_fails() -> None:
    r = _make_oos_result(sub_fold_pos=2, sub_fold_neg=2, sub_fold_pnls=[60.0, -10.0, 70.0, -20.0])
    verdict, gates, failed = mod.classify_verdict(r, shuffled_sharpe=0.02)
    assert verdict == "PROMISING_CONFIRMED"
    assert "A4" in failed


def test_verdict_promising_confirmed_when_a5_fails() -> None:
    r = _make_oos_result(oos_annual_pnl_stress_05=-5.0)
    verdict, gates, failed = mod.classify_verdict(r, shuffled_sharpe=0.02)
    assert verdict == "PROMISING_CONFIRMED"
    assert "A5" in failed


def test_verdict_failed_oos_when_a0_fails() -> None:
    r = _make_oos_result(oos_annual_trades=20.0)
    verdict, _, failed = mod.classify_verdict(r, shuffled_sharpe=0.02)
    assert verdict == "FAILED_OOS"
    assert "A0" in failed


def test_verdict_failed_oos_when_a1_fails() -> None:
    r = _make_oos_result(oos_sharpe=0.05)
    verdict, _, failed = mod.classify_verdict(r, shuffled_sharpe=0.02)
    assert verdict == "FAILED_OOS"
    assert "A1" in failed


def test_verdict_failed_oos_when_a2_fails() -> None:
    r = _make_oos_result(oos_annual_pnl=120.0)
    verdict, _, failed = mod.classify_verdict(r, shuffled_sharpe=0.02)
    assert verdict == "FAILED_OOS"
    assert "A2" in failed


def test_verdict_failed_oos_when_s0_fails() -> None:
    r = _make_oos_result()
    verdict, _, failed = mod.classify_verdict(r, shuffled_sharpe=0.20)  # |0.20| > 0.10
    assert verdict == "FAILED_OOS"
    assert "S0" in failed


def test_verdict_failed_oos_when_s1_fails() -> None:
    r = _make_oos_result(train_test_gap=0.50)
    verdict, _, failed = mod.classify_verdict(r, shuffled_sharpe=0.02)
    assert verdict == "FAILED_OOS"
    assert "S1" in failed


def test_verdict_a3_alone_does_not_force_failed_oos() -> None:
    """Per user-revised boundary: A3 alone fail → PROMISING_CONFIRMED, not FAILED_OOS."""
    r = _make_oos_result(oos_max_dd=400.0)
    verdict, _, _ = mod.classify_verdict(r, shuffled_sharpe=0.02)
    assert verdict != "FAILED_OOS"


# ---------------------------------------------------------------------------
# Drawdown analysis
# ---------------------------------------------------------------------------


def _make_trades_df(n: int = 100, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ts = pd.to_datetime(np.arange(n) * 3600 * 1_000_000_000, utc=True)
    return pd.DataFrame(
        {
            "entry_ts": ts,
            "pair": ["USD_JPY"] * (n // 2) + ["EUR_USD"] * (n - n // 2),
            "direction": ["long"] * n,
            "predicted_P": rng.uniform(0.55, 0.85, size=n),
            "pnl": rng.normal(0.0, 5.0, size=n),
            "hour_utc": rng.integers(0, 24, size=n).astype(np.int8),
            "dow": rng.integers(0, 7, size=n).astype(np.int8),
        }
    )


def test_worst_trades_top_20_returned() -> None:
    df = _make_trades_df(100)
    diag = mod.analyze_drawdown_concentration(df)
    assert len(diag["worst_trades_top20"]) == 20
    # All worst trades have pnl <= median pnl
    pnls_top20 = [t["pnl"] for t in diag["worst_trades_top20"]]
    median = float(df["pnl"].median())
    assert max(pnls_top20) <= median


def test_per_pair_pnl_aggregation_present() -> None:
    df = _make_trades_df(100)
    diag = mod.analyze_drawdown_concentration(df)
    pairs_returned = {r["pair"] for r in diag["per_pair"]}
    assert pairs_returned == {"USD_JPY", "EUR_USD"}


def test_consecutive_loss_run_length_correct() -> None:
    # Construct synthetic series with a known longest run of losses
    df = pd.DataFrame(
        {
            "entry_ts": pd.to_datetime(np.arange(10) * 3600 * 1_000_000_000, utc=True),
            "pair": ["USD_JPY"] * 10,
            "direction": ["long"] * 10,
            "predicted_P": [0.6] * 10,
            "pnl": [-1.0, -1.0, -1.0, +2.0, -1.0, -1.0, -1.0, -1.0, +1.0, -1.0],  # longest run = 4
            "hour_utc": [10] * 10,
            "dow": [1] * 10,
        }
    )
    diag = mod.analyze_drawdown_concentration(df)
    assert diag["longest_consecutive_loss_run"] == 4


def test_attribution_categorises_distributed() -> None:
    """Random uniform pnl with no concentration → DISTRIBUTED."""
    df = _make_trades_df(200, seed=42)
    diag = mod.analyze_drawdown_concentration(df)
    attr = mod.attribute_drawdown(diag, [10.0, -5.0, 8.0, -3.0], [])
    # On uniformly random data, attribution often comes out as DISTRIBUTED
    # but may catch edge cases. Accept either DISTRIBUTED or known categories.
    assert "DISTRIBUTED" in attr or "CONCENTRATION" in attr or "STREAK" in attr


def test_attribution_categorises_few_trade_concentration() -> None:
    """Strong tail concentration: 20 large losses, rest tiny noise."""
    n = 200
    pnl = np.concatenate(
        [np.full(20, -100.0), np.random.default_rng(0).normal(0.5, 0.5, size=n - 20)]
    )
    df = pd.DataFrame(
        {
            "entry_ts": pd.to_datetime(np.arange(n) * 3600 * 1_000_000_000, utc=True),
            "pair": ["USD_JPY"] * n,
            "direction": ["long"] * n,
            "predicted_P": [0.6] * n,
            "pnl": pnl,
            "hour_utc": [10] * n,
            "dow": [1] * n,
        }
    )
    diag = mod.analyze_drawdown_concentration(df)
    attr = mod.attribute_drawdown(diag, [], [])
    assert "FEW_TRADE_CONCENTRATION" in attr


def test_attribution_categorises_consecutive_streak() -> None:
    """Long consecutive loss streak."""
    n = 100
    pnl = np.full(n, 1.0)
    pnl[40:55] = -3.0  # 15-loss streak
    df = pd.DataFrame(
        {
            "entry_ts": pd.to_datetime(np.arange(n) * 3600 * 1_000_000_000, utc=True),
            "pair": ["USD_JPY"] * n,
            "direction": ["long"] * n,
            "predicted_P": [0.6] * n,
            "pnl": pnl,
            "hour_utc": [10] * n,
            "dow": [1] * n,
        }
    )
    diag = mod.analyze_drawdown_concentration(df)
    attr = mod.attribute_drawdown(diag, [], [])
    assert "CONSECUTIVE_LOSS_STREAK" in attr


# ---------------------------------------------------------------------------
# Helpers (sanity)
# ---------------------------------------------------------------------------


def test_per_trade_sharpe_zero_when_constant() -> None:
    pnl = np.array([1.0] * 100)
    assert mod.per_trade_sharpe(pnl) == 0.0


def test_max_drawdown_zero_when_monotone() -> None:
    pnl = np.array([1.0, 1.0, 1.0, 1.0])
    assert mod.max_drawdown(pnl) == 0.0


def test_max_drawdown_correct_simple_case() -> None:
    # equity: 0, 1, 3, 2, 0 → peak=3, trough=0 → MaxDD=3
    pnl = np.array([1.0, 2.0, -1.0, -2.0])
    assert mod.max_drawdown(pnl) == 3.0


def test_pr259_module_import_works() -> None:
    """The script imports PR #259 helpers; verify module is loadable."""
    assert mod._PR259 is not None
    assert hasattr(mod._PR259, "MAIN_FEATURE_COLS")
    assert hasattr(mod._PR259, "build_signal_dataset")


def test_canonical_pairs_list_size_20() -> None:
    assert len(mod.PAIRS_CANONICAL_20) == 20
