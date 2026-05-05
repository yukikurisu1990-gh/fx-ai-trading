"""Phase 22 research-integrity tests.

Synthetic-only assertions that reinforce the audit invariants identified in
``docs/design/phase22_research_integrity_audit.md``. Heavy parquet-dependent
spot-checks are kept in ``scripts/stage22_0x_research_audit.py`` and run
locally; this module contains only fast, CI-friendly checks.

Coverage:
- Annualisation formula constants
- per-trade Sharpe convention (no sqrt-of-N)
- best_possible_pnl forced REJECT in 22.0b and 22.0c verdict logic
- 22.0e feature allowlist excludes forbidden + leakage names
- 22.0e plan respects the user-modified policy
  (is_week_open_window / hour_utc / dow not in main features)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_22_0B = REPO_ROOT / "scripts" / "stage22_0b_mean_reversion_baseline.py"
SCRIPT_22_0C = REPO_ROOT / "scripts" / "stage22_0c_m5_breakout_m1_entry_hybrid.py"
SCRIPT_AUDIT = REPO_ROOT / "scripts" / "stage22_0x_research_audit.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mr = _load("stage22_0b_audit", SCRIPT_22_0B)
bo = _load("stage22_0c_audit", SCRIPT_22_0C)
audit = _load("stage22_0x_audit", SCRIPT_AUDIT)


# ---------------------------------------------------------------------------
# Annualisation
# ---------------------------------------------------------------------------


def test_eval_span_years_constant_matches_730_days() -> None:
    expected = 730.0 / 365.25
    assert abs(mr.EVAL_SPAN_YEARS_DEFAULT - expected) < 1e-9
    assert abs(bo.EVAL_SPAN_YEARS_DEFAULT - expected) < 1e-9
    assert abs(audit.EVAL_SPAN_YEARS - expected) < 1e-9


def test_22_0b_and_22_0c_use_same_annualisation() -> None:
    assert mr.EVAL_SPAN_YEARS_DEFAULT == bo.EVAL_SPAN_YEARS_DEFAULT


# ---------------------------------------------------------------------------
# Sharpe convention (per-trade, no sqrt-of-N)
# ---------------------------------------------------------------------------


def test_per_trade_sharpe_is_mean_over_std_no_annualisation() -> None:
    """Synthetic stream of constant +1 has std=0 (returns 0 by guard)."""
    pnl = np.array([1.0] * 100, dtype=np.float32)
    s = mr.per_trade_sharpe(pnl)
    assert s == 0.0  # std == 0 guard


def test_per_trade_sharpe_no_sqrt_of_n_in_22_0b() -> None:
    """For pnl ~ N(mean, std) with constant std, Sharpe should NOT scale
    with sample size — this is the no-annualisation convention.
    """
    rng = np.random.default_rng(0)
    small = rng.normal(loc=0.5, scale=1.0, size=200).astype(np.float32)
    large = rng.normal(loc=0.5, scale=1.0, size=2000).astype(np.float32)
    s_small = mr.per_trade_sharpe(small)
    s_large = mr.per_trade_sharpe(large)
    # Both should be near 0.5 (≈ mean/std), not 0.5×sqrt(N) which differs by 3.16x.
    assert abs(s_small - 0.5) < 0.2
    assert abs(s_large - 0.5) < 0.1
    # If sqrt(N) was applied, the ratio s_large/s_small would be √(2000/200)=3.16
    assert abs(s_large / s_small - 1.0) < 0.5


def test_per_trade_sharpe_22_0c_matches_22_0b() -> None:
    """Both research scripts must use the same Sharpe formula."""
    rng = np.random.default_rng(42)
    pnl = rng.normal(loc=-2.5, scale=8.0, size=10_000).astype(np.float32)
    s_mr = mr.per_trade_sharpe(pnl)
    s_bo = bo.per_trade_sharpe(pnl)
    assert abs(s_mr - s_bo) < 1e-9


# ---------------------------------------------------------------------------
# best_possible_pnl forced REJECT (verdict logic)
# ---------------------------------------------------------------------------


def _adopt_template(exit_rule: str = "tb_pnl") -> dict:
    """Cell metric template that would normally pass A0..A5."""
    return {
        "N": 20,
        "threshold": 2.0,
        "horizon_bars": 10,
        "exit_rule": exit_rule,
        "n_trades": 1000,
        "annual_trades": 500.0,
        "annual_pnl_pip": 250.0,
        "sharpe": 0.20,
        "max_dd_pip": 100.0,
        "dd_pct_pnl": 40.0,
        "mean_pnl": 0.5,
        "median_pnl": 0.4,
        "win_rate": 0.55,
        "annual_pnl_stress_+0.0": 250.0,
        "annual_pnl_stress_+0.2": 150.0,
        "annual_pnl_stress_+0.5": 50.0,
        "sharpe_stress_+0.0": 0.20,
        "sharpe_stress_+0.2": 0.15,
        "sharpe_stress_+0.5": 0.10,
        "fold_pos": 5,
        "fold_neg": 0,
        "fold_pnl_cv": 0.5,
        "fold_concentration_top": 0.30,
        **{f"fold_{i}_pnl": 50.0 for i in range(5)},
        **{f"fold_{i}_n": 200 for i in range(5)},
    }


def _adopt_template_22_0c(exit_rule: str = "tb_pnl") -> dict:
    base = _adopt_template(exit_rule)
    base["entry_timing"] = "immediate"
    base.pop("threshold", None)
    return base


def test_22_0b_classify_cell_forces_reject_for_best_possible_pnl() -> None:
    cell = _adopt_template(exit_rule="best_possible_pnl")
    cell["sharpe"] = 5.0  # unrealistically high
    cell["annual_pnl_pip"] = 1_000_000  # unrealistically high
    verdict, reasons = mr.classify_cell(cell)
    assert verdict == "REJECT"
    assert any("non-realistic" in r or "diagnostic" in r for r in reasons)


def test_22_0c_classify_cell_forces_reject_for_best_possible_pnl() -> None:
    cell = _adopt_template_22_0c(exit_rule="best_possible_pnl")
    cell["sharpe"] = 5.0
    cell["annual_pnl_pip"] = 1_000_000
    verdict, reasons = bo.classify_cell(cell)
    assert verdict == "REJECT"
    assert any("non-realistic" in r or "diagnostic" in r for r in reasons)


def test_22_0b_realistic_exit_rules_constant() -> None:
    assert mr.REALISTIC_EXIT_RULES == ("tb_pnl", "time_exit_pnl")
    assert "best_possible_pnl" not in mr.REALISTIC_EXIT_RULES


def test_22_0c_realistic_exit_rules_constant() -> None:
    assert bo.REALISTIC_EXIT_RULES == ("tb_pnl", "time_exit_pnl")
    assert "best_possible_pnl" not in bo.REALISTIC_EXIT_RULES


# ---------------------------------------------------------------------------
# 22.0e feature allowlist (audit static check)
# ---------------------------------------------------------------------------


def test_22_0e_allowlist_excludes_is_week_open_window() -> None:
    """Per user-modified policy in this audit conversation."""
    feat = audit.audit_22_0e_plan_features()
    assert feat["is_week_open_window_excluded_from_main"] is True


def test_22_0e_allowlist_excludes_hour_utc() -> None:
    feat = audit.audit_22_0e_plan_features()
    assert feat["hour_utc_excluded_from_main"] is True


def test_22_0e_allowlist_excludes_dow() -> None:
    feat = audit.audit_22_0e_plan_features()
    assert feat["dow_excluded_from_main"] is True


def test_22_0e_allowlist_excludes_all_forward_looking_columns() -> None:
    """No forward-looking outcome column may appear in main features."""
    feat = audit.audit_22_0e_plan_features()
    assert feat["overlap_violations"] == []
    forbidden_forward = {
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
    }
    main_set = set(feat["allowlist_main_features"])
    overlap = forbidden_forward & main_set
    assert overlap == set(), f"forward-looking leakage in allowlist: {overlap}"


def test_22_0e_allowlist_includes_expected_causal_features() -> None:
    feat = audit.audit_22_0e_plan_features()
    main_set = set(feat["allowlist_main_features"])
    must_have = {"cost_ratio", "atr_at_entry", "spread_entry", "pair", "direction"}
    assert must_have.issubset(main_set), f"missing causal features: {must_have - main_set}"


# ---------------------------------------------------------------------------
# Audit script API surface (sanity: the audit functions are callable)
# ---------------------------------------------------------------------------


def test_audit_module_exposes_top_cell_constants() -> None:
    assert audit.B_TOP_CELL["exit_rule"] == "time_exit_pnl"
    assert audit.B_TOP_CELL["N"] == 100
    assert audit.B_TOP_CELL["threshold"] == 3.0
    assert audit.B_TOP_CELL["horizon_bars"] == 40
    assert audit.C_TOP_CELL["exit_rule"] == "time_exit_pnl"
    assert audit.C_TOP_CELL["N"] == 100
    assert audit.C_TOP_CELL["entry_timing"] == "retest"
    assert audit.C_TOP_CELL["horizon_bars"] == 40


def test_audit_pip_size_consistency_with_research_scripts() -> None:
    for pair in ("USD_JPY", "EUR_USD", "AUD_NZD"):
        assert audit.pip_size_for(pair) == mr.pip_size_for(pair)
        assert audit.pip_size_for(pair) == bo.pip_size_for(pair)


def test_audit_canonical_pair_list_matches_research() -> None:
    assert audit.PAIRS_CANONICAL_20 == mr.PAIRS_CANONICAL_20
    assert audit.PAIRS_CANONICAL_20 == bo.PAIRS_CANONICAL_20
    assert len(audit.PAIRS_CANONICAL_20) == 20
    assert "CAD_JPY" not in audit.PAIRS_CANONICAL_20
    assert "GBP_CHF" in audit.PAIRS_CANONICAL_20
