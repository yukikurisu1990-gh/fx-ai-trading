"""Unit tests for Stage 25.0e-β F3 cross-pair eval.

Enforces the 25.0e-α §2.5 strict-causal contract (bar-t lookahead),
the §2.3 canonical-pair-only orientation rule, and the §3 18-cell
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

f3 = importlib.import_module("stage25_0e_f3_eval")


# ---------------------------------------------------------------------------
# §2.3 — canonical-pair-only orientation
# ---------------------------------------------------------------------------


def test_pairs_containing_returns_only_canonical():
    """No synthetic / out-of-universe pair must ever appear."""
    canonical = set(f3.PAIRS_20)
    for c in f3.CURRENCIES:
        out = f3.pairs_containing(c)
        assert out, f"currency {c} should have at least one canonical pair"
        for p in out:
            assert p in canonical, f"non-canonical pair leaked: {p}"


def test_signed_return_orientation_base_currency():
    """If C is base in BASE_QUOTE, return sign is +1."""
    assert f3.signed_return_orientation("EUR_USD", "EUR") == +1
    assert f3.signed_return_orientation("USD_JPY", "USD") == +1
    assert f3.signed_return_orientation("AUD_NZD", "AUD") == +1


def test_signed_return_orientation_quote_currency():
    """If C is quote in BASE_QUOTE, return sign is -1."""
    assert f3.signed_return_orientation("EUR_USD", "USD") == -1
    assert f3.signed_return_orientation("USD_JPY", "JPY") == -1
    assert f3.signed_return_orientation("AUD_NZD", "NZD") == -1


def test_signed_return_orientation_raises_on_unrelated():
    with pytest.raises(ValueError):
        f3.signed_return_orientation("EUR_USD", "JPY")


def test_currency_strength_nzd_uses_3_canonical_pairs():
    """NZD coverage example from 25.0e-α §2.3: AUD_NZD, NZD_JPY, NZD_USD."""
    nzd_pairs = f3.pairs_containing("NZD")
    assert sorted(nzd_pairs) == sorted(["AUD_NZD", "NZD_JPY", "NZD_USD"])


def test_currency_strength_usd_uses_canonical_usd_pairs():
    usd_pairs = f3.pairs_containing("USD")
    expected = {
        "EUR_USD",
        "GBP_USD",
        "AUD_USD",
        "NZD_USD",
        "USD_CHF",
        "USD_CAD",
        "USD_JPY",
    }
    assert set(usd_pairs) == expected


# ---------------------------------------------------------------------------
# §2.5 — strict causality / bar-t lookahead invariance (MANDATORY)
# ---------------------------------------------------------------------------


def _build_synthetic_returns(n: int = 600, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    cols = list(f3.PAIRS_20)
    data = rng.normal(0.0, 1e-4, size=(n, len(cols)))
    return pd.DataFrame(data, index=idx, columns=cols)


def test_bar_t_lookahead_invariance_strength():
    """compute_currency_strength(t) MUST be invariant under perturbation
    of bar t. This enforces §2.5 strict-causal: feature(t) uses bars ≤ t-1.
    """
    df_normal = _build_synthetic_returns()
    df_perturbed = df_normal.copy()
    t_target = df_normal.index[300]
    df_perturbed.loc[t_target, "EUR_USD"] = 100.0  # huge perturbation at bar t

    f_normal = f3.compute_currency_strength(df_normal, "USD", lookback=20, zscore_window=20)
    f_perturbed = f3.compute_currency_strength(df_perturbed, "USD", lookback=20, zscore_window=20)
    v_normal = f_normal.loc[t_target]
    v_perturbed = f_perturbed.loc[t_target]
    if pd.isna(v_normal) and pd.isna(v_perturbed):
        return
    assert v_normal == pytest.approx(v_perturbed, abs=1e-12), (
        "currency_strength(t) must NOT depend on bar t — §2.5 violation"
    )


def test_bar_t_lookahead_invariance_correlation():
    """compute_pair_correlation(t) MUST be invariant under perturbation
    of bar t.
    """
    df_normal = _build_synthetic_returns()
    df_perturbed = df_normal.copy()
    t_target = df_normal.index[300]
    df_perturbed.loc[t_target, "EUR_USD"] = 50.0
    df_perturbed.loc[t_target, "GBP_USD"] = -50.0

    f_normal = f3.compute_pair_correlation(df_normal, "EUR_USD", "GBP_USD", lookback=50)
    f_perturbed = f3.compute_pair_correlation(df_perturbed, "EUR_USD", "GBP_USD", lookback=50)
    v_normal = f_normal.loc[t_target]
    v_perturbed = f_perturbed.loc[t_target]
    if pd.isna(v_normal) and pd.isna(v_perturbed):
        return
    assert v_normal == pytest.approx(v_perturbed, abs=1e-12), (
        "correlation(t) must NOT depend on bar t — §2.5 violation"
    )


def test_currency_strength_uses_only_past_window():
    """Last value should depend on bars[0..n-2], not bar n-1."""
    df_normal = _build_synthetic_returns(n=100)
    df_perturbed = df_normal.copy()
    last_ts = df_normal.index[-1]
    df_perturbed.loc[last_ts, :] = 1.0  # massive perturbation at t=last

    f_normal = f3.compute_currency_strength(df_normal, "EUR", lookback=20, zscore_window=20)
    f_perturbed = f3.compute_currency_strength(df_perturbed, "EUR", lookback=20, zscore_window=20)
    v_n = f_normal.iloc[-1]
    v_p = f_perturbed.iloc[-1]
    if pd.isna(v_n) and pd.isna(v_p):
        return
    assert v_n == pytest.approx(v_p, abs=1e-12)


# ---------------------------------------------------------------------------
# §2.4 — F3-b correlation pair-set is PREDECLARED (no target-aware)
# ---------------------------------------------------------------------------


def test_f3b_corr_pairs_is_predeclared_constant():
    """F3_B_CORR_PAIRS is a frozen tuple of 6 pair-pairs."""
    assert isinstance(f3.F3_B_CORR_PAIRS, tuple)
    assert len(f3.F3_B_CORR_PAIRS) == 6
    expected = {
        ("EUR_USD", "GBP_USD"),
        ("AUD_USD", "NZD_USD"),
        ("USD_JPY", "USD_CHF"),
        ("EUR_JPY", "GBP_JPY"),
        ("EUR_GBP", "EUR_USD"),
        ("AUD_JPY", "NZD_JPY"),
    }
    assert set(f3.F3_B_CORR_PAIRS) == expected


def test_f3b_corr_pairs_only_canonical():
    canonical = set(f3.PAIRS_20)
    for a, b in f3.F3_B_CORR_PAIRS:
        assert a in canonical
        assert b in canonical


# ---------------------------------------------------------------------------
# §3 — 18-cell sweep grid invariant
# ---------------------------------------------------------------------------


def test_sweep_grid_has_18_cells():
    assert len(f3.CELL_GRID) == 18


def test_sweep_grid_dimensions():
    assert f3.CELL_SUBGROUPS == ("F3a", "F3b", "F3a_F3b")
    assert f3.CELL_LOOKBACKS == (20, 50, 100)
    assert f3.CELL_ZSCORE_WINDOWS == (20, 50)


def test_subgroup_f3a_alone_columns():
    cols = f3.feature_columns_for_cell("F3a")
    assert all(c.startswith("f3a_") for c in cols)
    assert len(cols) == len(f3.CURRENCIES)


def test_subgroup_f3b_alone_columns():
    cols = f3.feature_columns_for_cell("F3b")
    assert all(c.startswith("f3b_") for c in cols)
    assert len(cols) == len(f3.F3_B_CORR_PAIRS)


def test_subgroup_f3a_plus_f3b_columns():
    cols = f3.feature_columns_for_cell("F3a_F3b")
    n_a = len(f3.CURRENCIES)
    n_b = len(f3.F3_B_CORR_PAIRS)
    assert len(cols) == n_a + n_b


# ---------------------------------------------------------------------------
# Calibration diagnostics (§6 — diagnostic-only)
# ---------------------------------------------------------------------------


def test_calibration_decile_returns_buckets():
    rng = np.random.default_rng(0)
    n = 1000
    p = rng.uniform(0.0, 1.0, size=n)
    # Make labels weakly correlated with p so AUC > 0.5
    label = (rng.uniform(0.0, 1.0, size=n) < p).astype(int)
    cal = f3.calibration_decile_check(p, label)
    assert "buckets" in cal
    assert len(cal["buckets"]) <= 10  # qcut may collapse on ties
    assert cal["overall_brier"] >= 0.0
    assert cal["low_n_flag"] is False


def test_calibration_decile_low_n_flag():
    p = np.array([0.1, 0.2, 0.3])
    label = np.array([0, 1, 0])
    cal = f3.calibration_decile_check(p, label)
    assert cal["low_n_flag"] is True


# ---------------------------------------------------------------------------
# Verdict tree (§7) — H2 PASS alone is NOT ADOPT_CANDIDATE
# ---------------------------------------------------------------------------


def test_verdict_h1_fail():
    gates = {"A0": True, "A1": True, "A2": True, "A3": True, "A4": True, "A5": True}
    v, h = f3.assign_cell_verdict(0.50, gates, n_trades=100)
    assert v == "REJECT_NON_DISCRIMINATIVE"
    assert h == "H1_FAIL"


def test_verdict_h1_pass_h2_fail():
    gates = {"A0": True, "A1": False, "A2": True, "A3": True, "A4": True, "A5": True}
    v, h = f3.assign_cell_verdict(0.58, gates, n_trades=100)
    assert v == "REJECT_BUT_INFORMATIVE"
    assert h == "H1_PASS_H2_FAIL"


def test_verdict_all_gates_pass():
    gates = {"A0": True, "A1": True, "A2": True, "A3": True, "A4": True, "A5": True}
    v, h = f3.assign_cell_verdict(0.60, gates, n_trades=100)
    assert v == "ADOPT_CANDIDATE"
    assert h == "ALL_GATES_PASS"


def test_verdict_h1_h2_pass_a3_a5_partial_promising():
    gates = {"A0": True, "A1": True, "A2": True, "A3": True, "A4": False, "A5": False}
    v, h = f3.assign_cell_verdict(0.60, gates, n_trades=100)
    assert v == "PROMISING_BUT_NEEDS_OOS"
    assert h == "H1_H2_PASS_A3_A5_PARTIAL"


def test_verdict_h1_h2_pass_a3_a5_all_fail():
    gates = {"A0": True, "A1": True, "A2": True, "A3": False, "A4": False, "A5": False}
    v, h = f3.assign_cell_verdict(0.60, gates, n_trades=100)
    assert v == "REJECT"
    assert h == "H1_H2_PASS_A3_A5_FAIL"


# ---------------------------------------------------------------------------
# H3 reference invariant (single-set comparison; not combined)
# ---------------------------------------------------------------------------


def test_h3_reference_constant():
    """H3 PASS threshold must equal best-of-{F1, F2} + 0.01 = 0.5644 + 0.01."""
    assert pytest.approx(0.5644) == f3.H3_REFERENCE_AUC
    assert pytest.approx(0.01) == f3.H3_LIFT_THRESHOLD
    assert pytest.approx(0.5744) == f3.H3_PASS_AUC


def test_aggregate_h3_pass_when_lift_sufficient():
    cell_results = [
        {
            "cell": {"subgroup": "F3a", "lookback": 20, "zscore_window": 20},
            "test_auc": 0.5800,
            "h_state": "H1_PASS_H2_FAIL",
            "realised_metrics": {"sharpe": -0.1, "annual_pnl": 0.0},
        },
        {
            "cell": {"subgroup": "F3b", "lookback": 50, "zscore_window": 50},
            "test_auc": 0.5700,
            "h_state": "H1_FAIL",
            "realised_metrics": {"sharpe": float("nan"), "annual_pnl": 0.0},
        },
    ]
    agg = f3.aggregate_h3_h4(cell_results)
    assert agg["best_auc"] == pytest.approx(0.5800)
    assert agg["h3_pass"] is True
    assert agg["h4_pass"] is False  # sharpe -0.1


def test_aggregate_h3_fail_when_lift_insufficient():
    cell_results = [
        {
            "cell": {"subgroup": "F3a", "lookback": 20, "zscore_window": 20},
            "test_auc": 0.5650,  # lift = 0.0006; below 0.01
            "h_state": "H1_PASS_H2_FAIL",
            "realised_metrics": {"sharpe": -0.05, "annual_pnl": 0.0},
        },
    ]
    agg = f3.aggregate_h3_h4(cell_results)
    assert agg["h3_pass"] is False


def test_aggregate_h4_pass_when_sharpe_nonneg():
    cell_results = [
        {
            "cell": {"subgroup": "F3a", "lookback": 20, "zscore_window": 20},
            "test_auc": 0.5600,
            "h_state": "H1_PASS_H2_FAIL",
            "realised_metrics": {"sharpe": 0.05, "annual_pnl": 50.0},
        },
    ]
    agg = f3.aggregate_h3_h4(cell_results)
    assert agg["h4_pass"] is True


def test_refine_verdict_with_h3_orthogonal():
    cell = {"verdict": "REJECT_BUT_INFORMATIVE", "h_state": "H1_PASS_H2_FAIL"}
    refined = f3.refine_verdict_with_h3(cell, h3_pass=True)
    assert refined["verdict"] == "REJECT_BUT_INFORMATIVE_ORTHOGONAL"


def test_refine_verdict_with_h3_redundant():
    cell = {"verdict": "REJECT_BUT_INFORMATIVE", "h_state": "H1_PASS_H2_FAIL"}
    refined = f3.refine_verdict_with_h3(cell, h3_pass=False)
    assert refined["verdict"] == "REJECT_BUT_INFORMATIVE_REDUNDANT"


# ---------------------------------------------------------------------------
# Diagnostic-leakage prohibition (clause 2)
# ---------------------------------------------------------------------------


def test_no_diagnostic_columns_in_feature_set():
    """The 5 diagnostic columns from 25.0a-β must NEVER appear in the
    feature column lists for any cell.
    """
    prohibited = set(f3.PROHIBITED_DIAGNOSTIC_COLUMNS)
    for sg in f3.CELL_SUBGROUPS:
        cols = f3.feature_columns_for_cell(sg)
        assert prohibited.isdisjoint(cols), (
            f"diagnostic-column leakage in subgroup {sg}: {prohibited & set(cols)}"
        )
