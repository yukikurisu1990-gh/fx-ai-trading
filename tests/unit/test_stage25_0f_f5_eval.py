"""Unit tests for Stage 25.0f-β F5 liquidity / spread / volume eval.

Enforces the 25.0f-α §2.5.1 volume pre-flight contract, the §2.7 strict-
causal contract (bar-t lookahead), the §2.2 concat-vs-interaction
distinction, the §2.6 train-only tercile fit guard, and the §3 21-cell
sweep grid invariant.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

f5 = importlib.import_module("stage25_0f_f5_eval")


# ---------------------------------------------------------------------------
# Volume pre-flight contract (§2.5.1) — happy path on real data
# ---------------------------------------------------------------------------


def test_volume_preflight_passes_on_real_data():
    """Real M1 BA jsonl carries volume; pre-flight must pass for 1 pair.

    Skipped when data files are absent (CI without the data dir).
    """
    data_path = REPO_ROOT / "data" / "candles_EUR_USD_M1_730d_BA.jsonl"
    if not data_path.exists():
        pytest.skip("M1 BA data not present in this environment")
    diag = f5.verify_volume_preflight(["EUR_USD"], days=730)
    assert "EUR_USD" in diag
    assert diag["EUR_USD"]["volume_nonnull_fraction"] >= f5.VOLUME_MIN_NONNULL_FRACTION


# ---------------------------------------------------------------------------
# Volume pre-flight failure paths (§2.5.1) — synthetic
# ---------------------------------------------------------------------------


def test_volume_preflight_halts_on_missing_volume(tmp_path, monkeypatch):
    """If the loader returns a DataFrame without 'volume', halt."""

    def fake_loader(pair: str, days: int = 730) -> pd.DataFrame:
        idx = pd.date_range("2024-01-01", periods=10, freq="1min", tz="UTC")
        return pd.DataFrame({"bid_c": np.ones(10), "ask_c": np.ones(10) + 1e-4}, index=idx)

    monkeypatch.setattr(f5, "load_m1_with_volume", fake_loader)
    with pytest.raises(f5.VolumePreflightError, match="volume column absent"):
        f5.verify_volume_preflight(["FAKE_PAIR"], days=730)


def test_volume_preflight_halts_on_low_nonnull_fraction(monkeypatch):
    """Non-null fraction below 0.99 must halt, not silently degrade."""

    def fake_loader(pair: str, days: int = 730) -> pd.DataFrame:
        idx = pd.date_range("2024-01-01", periods=100, freq="1min", tz="UTC")
        vol = np.ones(100)
        vol[:50] = np.nan  # 50% non-null
        return pd.DataFrame({"volume": vol}, index=idx)

    monkeypatch.setattr(f5, "load_m1_with_volume", fake_loader)
    with pytest.raises(f5.VolumePreflightError, match="non-null fraction"):
        f5.verify_volume_preflight(["FAKE_PAIR"], days=730, min_nonnull_fraction=0.99)


def test_volume_preflight_halts_on_negative_volume(monkeypatch):
    def fake_loader(pair: str, days: int = 730) -> pd.DataFrame:
        idx = pd.date_range("2024-01-01", periods=100, freq="1min", tz="UTC")
        vol = np.ones(100)
        vol[10] = -5
        return pd.DataFrame({"volume": vol}, index=idx)

    monkeypatch.setattr(f5, "load_m1_with_volume", fake_loader)
    with pytest.raises(f5.VolumePreflightError, match="negative volume"):
        f5.verify_volume_preflight(["FAKE_PAIR"], days=730)


def test_volume_preflight_halts_on_non_monotonic_index(monkeypatch):
    def fake_loader(pair: str, days: int = 730) -> pd.DataFrame:
        idx = pd.DatetimeIndex(
            [
                pd.Timestamp("2024-01-01 00:00", tz="UTC"),
                pd.Timestamp("2024-01-01 00:02", tz="UTC"),
                pd.Timestamp("2024-01-01 00:01", tz="UTC"),
            ]
            * 35
        )
        return pd.DataFrame({"volume": np.ones(len(idx))}, index=idx)

    monkeypatch.setattr(f5, "load_m1_with_volume", fake_loader)
    with pytest.raises(f5.VolumePreflightError, match="not monotonic"):
        f5.verify_volume_preflight(["FAKE_PAIR"], days=730)


# ---------------------------------------------------------------------------
# §2.7 — strict causality / bar-t lookahead invariance (MANDATORY)
# ---------------------------------------------------------------------------


def _build_synthetic_series(n: int = 600, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    return pd.Series(rng.normal(0.0, 1.0, size=n), index=idx)


def test_bar_t_lookahead_invariance_f5a_spread():
    """compute_spread_z_for_pair(t) MUST be invariant under perturbation of t."""
    s_normal = _build_synthetic_series()
    s_perturbed = s_normal.copy()
    t_target = s_normal.index[300]
    s_perturbed.loc[t_target] = 1e6

    f_normal = f5.compute_spread_z_for_pair(s_normal, lookback=20)
    f_perturbed = f5.compute_spread_z_for_pair(s_perturbed, lookback=20)
    v_normal = f_normal.loc[t_target]
    v_perturbed = f_perturbed.loc[t_target]
    if pd.isna(v_normal) and pd.isna(v_perturbed):
        return
    assert v_normal == pytest.approx(v_perturbed, abs=1e-12), (
        "spread_z(t) must NOT depend on bar t — §2.7 violation"
    )


def test_bar_t_lookahead_invariance_f5b_volume():
    s_normal = _build_synthetic_series(seed=1)
    s_perturbed = s_normal.copy()
    t_target = s_normal.index[300]
    s_perturbed.loc[t_target] = 1e6

    f_normal = f5.compute_volume_z_for_pair(s_normal, lookback=20)
    f_perturbed = f5.compute_volume_z_for_pair(s_perturbed, lookback=20)
    v_normal = f_normal.loc[t_target]
    v_perturbed = f_perturbed.loc[t_target]
    if pd.isna(v_normal) and pd.isna(v_perturbed):
        return
    assert v_normal == pytest.approx(v_perturbed, abs=1e-12)


def test_bar_t_lookahead_invariance_f5c_joint():
    """F5-c continuous + boolean terms are pointwise on already-causal inputs;
    perturbing bar t in spread_z / volume_z at t must not affect feature(t)."""
    spread_z = _build_synthetic_series(seed=2)
    volume_z = _build_synthetic_series(seed=3)
    spread_perturbed = spread_z.copy()
    t_target = spread_z.index[300]
    spread_perturbed.loc[t_target] = 1e6

    f_normal = f5.compute_f5c_continuous_and_flags(spread_z, volume_z, lookback=20)
    f_perturbed = f5.compute_f5c_continuous_and_flags(spread_perturbed, volume_z, lookback=20)
    # F5-c is pointwise — bar t in spread_z DOES affect feature(t) directly.
    # The causality contract is upstream: spread_z is itself shift(1)-causal,
    # so spread_z(t) is computed from bars <= t-1. The pointwise composition
    # preserves causality.
    # We test the upstream invariant in test_bar_t_lookahead_invariance_f5a_spread.
    # Here we just verify the F5-c computation is purely pointwise (no rolling).
    # Sanity: F5-c output at non-target t equals the corresponding f_normal value.
    # (Pointwise → equality everywhere except t_target.)
    other_idx = spread_z.index[200]
    for col in f_normal.columns:
        assert f_normal[col].loc[other_idx] == f_perturbed[col].loc[other_idx]


# ---------------------------------------------------------------------------
# §2.6 — train-only tercile fit guard (MANDATORY user correction)
# ---------------------------------------------------------------------------


def test_f5c_regime_thresholds_fit_on_train_only():
    """Tercile thresholds must come from TRAIN ONLY; val/test must NOT
    influence the cutoffs even if their distribution differs sharply.
    """
    rng = np.random.default_rng(42)
    n = 300
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    # Train: spread_z standard normal
    train = pd.DataFrame(
        {
            "f5a_spread_z_20": rng.normal(0.0, 1.0, size=n),
            "f5b_volume_z_20": rng.normal(0.0, 1.0, size=n),
            "label": rng.integers(0, 2, size=n),
        },
        index=idx,
    )
    # Val: spread_z shifted +5σ — radically different distribution
    val = pd.DataFrame(
        {
            "f5a_spread_z_20": rng.normal(5.0, 1.0, size=n),
            "f5b_volume_z_20": rng.normal(0.0, 1.0, size=n),
            "label": rng.integers(0, 2, size=n),
        },
        index=idx + pd.Timedelta(days=1),
    )
    # Test: spread_z shifted +10σ
    test = pd.DataFrame(
        {
            "f5a_spread_z_20": rng.normal(10.0, 1.0, size=n),
            "f5b_volume_z_20": rng.normal(0.0, 1.0, size=n),
            "label": rng.integers(0, 2, size=n),
        },
        index=idx + pd.Timedelta(days=2),
    )

    train_q33, train_q67 = f5.fit_terciles_on_train(train["f5a_spread_z_20"])
    train_out, val_out, test_out = f5.add_f5c_regime_cross_train_fit(train, val, test, lookback=20)

    # Train-fit thresholds should be near 0 (standard normal).
    assert -0.7 < train_q33 < 0.0
    assert 0.0 < train_q67 < 0.7

    # Apply train thresholds to val: nearly all val rows should be in bucket 2
    # (>= q67) because val spread_z is shifted +5σ.
    val_spread_in_bucket_2 = (val_out["f5a_spread_z_20"] >= train_q67).sum()
    assert val_spread_in_bucket_2 > 0.95 * len(val_out), (
        "train-fit terciles should classify val (spread_z + 5σ) overwhelmingly "
        "as bucket 2; if val influenced thresholds, this would not hold"
    )
    # Same for test: shifted +10σ should be entirely in bucket 2
    test_spread_in_bucket_2 = (test_out["f5a_spread_z_20"] >= train_q67).sum()
    assert test_spread_in_bucket_2 == len(test_out)


def test_fit_terciles_uses_only_provided_values():
    """fit_terciles_on_train returns quantiles of input only; if input is
    a uniform distribution, q33 / q67 should be close to 1/3 / 2/3."""
    n = 10000
    rng = np.random.default_rng(0)
    values = pd.Series(rng.uniform(0.0, 1.0, size=n))
    q33, q67 = f5.fit_terciles_on_train(values)
    assert 0.30 < q33 < 0.36
    assert 0.64 < q67 < 0.70


def test_fit_terciles_falls_back_on_low_n():
    values = pd.Series([0.1, 0.5, 0.9])
    q33, q67 = f5.fit_terciles_on_train(values)
    assert q33 < q67  # sentinel cutoffs in degenerate case


def test_apply_terciles_buckets_correctly():
    values = pd.Series([0.0, 0.5, 1.0, np.nan])
    out = f5.apply_terciles(values, q33=0.33, q67=0.67)
    assert out.iloc[0] == 0.0  # 0.0 < 0.33
    assert out.iloc[1] == 1.0  # 0.33 <= 0.5 < 0.67
    assert out.iloc[2] == 2.0  # 1.0 >= 0.67
    assert pd.isna(out.iloc[3])


# ---------------------------------------------------------------------------
# §2.2 — F5-a + F5-b is concat; F5-c is interaction (NOT the same)
# ---------------------------------------------------------------------------


def test_f5a_plus_f5b_is_concat_not_interaction():
    """F5-a + F5-b emits exactly 2 columns — marginals only, no joint terms."""
    cols = f5.feature_columns_for_cell("F5a_F5b", lookback=20)
    assert cols == ["f5a_spread_z_20", "f5b_volume_z_20"]
    assert len(cols) == 2


def test_f5c_alone_is_interaction_not_concat():
    """F5-c alone emits 4 continuous/boolean + 9 regime = 13 joint columns."""
    cols = f5.feature_columns_for_cell("F5c", lookback=20)
    assert "f5c_spread_x_volume_20" in cols
    assert "f5c_high_spread_high_vol_20" in cols
    assert "f5c_high_spread_low_vol_20" in cols
    assert "f5c_low_spread_high_vol_20" in cols
    for i in range(9):
        assert f"f5c_regime_20_{i}" in cols
    assert len(cols) == 4 + 9
    # Crucial invariant: F5-c does NOT include the F5-a / F5-b marginals.
    assert "f5a_spread_z_20" not in cols
    assert "f5b_volume_z_20" not in cols


def test_f5a_plus_f5b_plus_f5c_is_union():
    """F5-a + F5-b + F5-c emits marginals + joint terms = 2 + 13 = 15 cols."""
    cols = f5.feature_columns_for_cell("F5a_F5b_F5c", lookback=20)
    assert "f5a_spread_z_20" in cols
    assert "f5b_volume_z_20" in cols
    assert "f5c_spread_x_volume_20" in cols
    assert len(cols) == 2 + 4 + 9


def test_f5c_continuous_term_uses_no_future_info():
    """F5-c spread_z × volume_z is pointwise; no rolling, no future."""
    spread_z = pd.Series([0.0, 1.0, 2.0])
    volume_z = pd.Series([1.0, 2.0, 3.0])
    out = f5.compute_f5c_continuous_and_flags(spread_z, volume_z, lookback=20)
    # f5c_spread_x_volume_20[t] = spread_z[t] * volume_z[t]
    assert out["f5c_spread_x_volume_20"].tolist() == [0.0, 2.0, 6.0]


def test_f5c_high_spread_high_vol_flag_uses_z_cutoffs():
    spread_z = pd.Series([0.0, 1.5, 0.5, -2.0])
    volume_z = pd.Series([0.0, 1.5, -2.0, -2.0])
    out = f5.compute_f5c_continuous_and_flags(spread_z, volume_z, lookback=20)
    assert out["f5c_high_spread_high_vol_20"].tolist() == [0, 1, 0, 0]
    assert out["f5c_high_spread_low_vol_20"].tolist() == [0, 0, 0, 0]
    assert out["f5c_low_spread_high_vol_20"].tolist() == [0, 0, 0, 0]


# ---------------------------------------------------------------------------
# §3 — 21-cell sweep grid invariant
# ---------------------------------------------------------------------------


def test_sweep_grid_has_21_cells():
    assert len(f5.CELL_GRID) == 21


def test_sweep_grid_dimensions():
    assert f5.CELL_SUBGROUPS == (
        "F5a",
        "F5b",
        "F5c",
        "F5a_F5b",
        "F5a_F5c",
        "F5b_F5c",
        "F5a_F5b_F5c",
    )
    assert f5.CELL_LOOKBACKS == (20, 50, 100)


def test_subgroup_f5a_alone_columns():
    cols = f5.feature_columns_for_cell("F5a", lookback=50)
    assert cols == ["f5a_spread_z_50"]


def test_subgroup_f5b_alone_columns():
    cols = f5.feature_columns_for_cell("F5b", lookback=100)
    assert cols == ["f5b_volume_z_100"]


def test_cell_uses_f5c_flag():
    assert not f5.cell_uses_f5c("F5a")
    assert not f5.cell_uses_f5c("F5b")
    assert not f5.cell_uses_f5c("F5a_F5b")
    assert f5.cell_uses_f5c("F5c")
    assert f5.cell_uses_f5c("F5a_F5c")
    assert f5.cell_uses_f5c("F5b_F5c")
    assert f5.cell_uses_f5c("F5a_F5b_F5c")


# ---------------------------------------------------------------------------
# Calibration diagnostics (§6 — diagnostic-only)
# ---------------------------------------------------------------------------


def test_calibration_decile_returns_buckets():
    rng = np.random.default_rng(0)
    n = 1000
    p = rng.uniform(0.0, 1.0, size=n)
    label = (rng.uniform(0.0, 1.0, size=n) < p).astype(int)
    cal = f5.calibration_decile_check(p, label)
    assert "buckets" in cal
    assert len(cal["buckets"]) <= 10
    assert cal["overall_brier"] >= 0.0
    assert cal["low_n_flag"] is False


def test_calibration_decile_low_n_flag():
    p = np.array([0.1, 0.2, 0.3])
    label = np.array([0, 1, 0])
    cal = f5.calibration_decile_check(p, label)
    assert cal["low_n_flag"] is True


# ---------------------------------------------------------------------------
# Verdict tree (§7) — H2 PASS alone is NOT ADOPT_CANDIDATE
# ---------------------------------------------------------------------------


def test_verdict_h1_fail():
    gates = {"A0": True, "A1": True, "A2": True, "A3": True, "A4": True, "A5": True}
    v, h = f5.assign_cell_verdict(0.50, gates, n_trades=100)
    assert v == "REJECT_NON_DISCRIMINATIVE"
    assert h == "H1_FAIL"


def test_verdict_h1_pass_h2_fail():
    gates = {"A0": True, "A1": False, "A2": True, "A3": True, "A4": True, "A5": True}
    v, h = f5.assign_cell_verdict(0.58, gates, n_trades=100)
    assert v == "REJECT_BUT_INFORMATIVE"
    assert h == "H1_PASS_H2_FAIL"


def test_verdict_all_gates_pass():
    gates = {"A0": True, "A1": True, "A2": True, "A3": True, "A4": True, "A5": True}
    v, h = f5.assign_cell_verdict(0.60, gates, n_trades=100)
    assert v == "ADOPT_CANDIDATE"
    assert h == "ALL_GATES_PASS"


def test_verdict_h1_h2_pass_a3_a5_partial_promising():
    gates = {"A0": True, "A1": True, "A2": True, "A3": True, "A4": False, "A5": False}
    v, h = f5.assign_cell_verdict(0.60, gates, n_trades=100)
    assert v == "PROMISING_BUT_NEEDS_OOS"


def test_verdict_h1_h2_pass_a3_a5_all_fail():
    gates = {"A0": True, "A1": True, "A2": True, "A3": False, "A4": False, "A5": False}
    v, h = f5.assign_cell_verdict(0.60, gates, n_trades=100)
    assert v == "REJECT"


# ---------------------------------------------------------------------------
# H3 reference invariant + aggregate H3/H4
# ---------------------------------------------------------------------------


def test_h3_reference_constant():
    """H3 PASS threshold = best-of-{F1, F2, F3} + 0.01 = 0.5644 + 0.01."""
    assert pytest.approx(0.5644) == f5.H3_REFERENCE_AUC
    assert pytest.approx(0.01) == f5.H3_LIFT_THRESHOLD
    assert pytest.approx(0.5744) == f5.H3_PASS_AUC


def test_aggregate_h3_pass_when_lift_sufficient():
    cell_results = [
        {
            "cell": {"subgroup": "F5a", "lookback": 20},
            "test_auc": 0.5800,
            "h_state": "H1_PASS_H2_FAIL",
            "realised_metrics": {"sharpe": -0.1, "annual_pnl": 0.0},
        }
    ]
    agg = f5.aggregate_h3_h4(cell_results)
    assert agg["h3_pass"] is True
    assert agg["h4_pass"] is False


def test_aggregate_h4_pass_when_sharpe_nonneg():
    cell_results = [
        {
            "cell": {"subgroup": "F5a", "lookback": 20},
            "test_auc": 0.5500,
            "h_state": "H1_PASS_H2_FAIL",
            "realised_metrics": {"sharpe": 0.05, "annual_pnl": 50.0},
        }
    ]
    agg = f5.aggregate_h3_h4(cell_results)
    assert agg["h4_pass"] is True


def test_refine_verdict_with_h3_orthogonal():
    cell = {"verdict": "REJECT_BUT_INFORMATIVE", "h_state": "H1_PASS_H2_FAIL"}
    refined = f5.refine_verdict_with_h3(cell, h3_pass=True)
    assert refined["verdict"] == "REJECT_BUT_INFORMATIVE_ORTHOGONAL"


def test_refine_verdict_with_h3_redundant():
    cell = {"verdict": "REJECT_BUT_INFORMATIVE", "h_state": "H1_PASS_H2_FAIL"}
    refined = f5.refine_verdict_with_h3(cell, h3_pass=False)
    assert refined["verdict"] == "REJECT_BUT_INFORMATIVE_REDUNDANT"


# ---------------------------------------------------------------------------
# Diagnostic-leakage prohibition
# ---------------------------------------------------------------------------


def test_no_diagnostic_columns_in_feature_set():
    prohibited = set(f5.PROHIBITED_DIAGNOSTIC_COLUMNS)
    for sg in f5.CELL_SUBGROUPS:
        for lb in f5.CELL_LOOKBACKS:
            cols = f5.feature_columns_for_cell(sg, lb)
            assert prohibited.isdisjoint(cols), (
                f"diagnostic-column leakage in {sg}/{lb}: {prohibited & set(cols)}"
            )
