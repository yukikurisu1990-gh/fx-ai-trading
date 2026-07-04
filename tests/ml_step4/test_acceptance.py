"""Acceptance / failure evaluator tests."""

from __future__ import annotations

import pytest

from scripts.ml_step4.acceptance import (
    DOES_NOT_MEET,
    MEETS,
    AcceptanceEvaluator,
    invalid_status,
)


def _passing_metrics() -> dict:
    return {
        "trade_count": 500,
        "daily_coverage_frac": 0.8,
        "expectancy_pips": 0.4,
        "daily_portfolio_sharpe_annualised": 1.2,
        "max_equity_drawdown": {"max_drawdown_frac": 0.05},
        "turnover_trades_per_day": 12.0,
        "pair_concentration": {"max_trade_share": 0.2, "max_positive_pnl_share": 0.3},
        "cost_sensitivity": {"1.0pip": {"expectancy_pips": 0.1}},
    }


def test_all_criteria_met() -> None:
    ev = AcceptanceEvaluator()
    result = ev.evaluate(_passing_metrics(), provenance_complete=True)
    assert result["status"] == MEETS
    assert result["meets"] is True
    assert all(c["passed"] for c in result["criteria"].values())


def test_below_threshold_is_does_not_meet_not_hidden() -> None:
    m = _passing_metrics()
    m["daily_portfolio_sharpe_annualised"] = 0.3  # below 0.8
    ev = AcceptanceEvaluator()
    result = ev.evaluate(m, provenance_complete=True)
    assert result["status"] == DOES_NOT_MEET
    assert result["meets"] is False
    # Honest negative is reported with a full criteria table (not hidden).
    assert result["criteria"]["daily_portfolio_sharpe"]["passed"] is False


def test_hard_trigger_checksum_mismatch() -> None:
    ev = AcceptanceEvaluator()
    result = ev.evaluate(
        _passing_metrics(), provenance_complete=True, hard_triggers={"CHECKSUM_MISMATCH"}
    )
    assert result["status"] == "ML_STEP4_RUN_INVALID_CHECKSUM_MISMATCH"


def test_insufficient_sample_is_hard_invalid() -> None:
    m = _passing_metrics()
    m["trade_count"] = 100  # below 300
    ev = AcceptanceEvaluator()
    result = ev.evaluate(m, provenance_complete=True)
    assert result["status"] == "ML_STEP4_RUN_INVALID_INSUFFICIENT_OOS_SAMPLE"


def test_low_coverage_is_hard_invalid() -> None:
    m = _passing_metrics()
    m["daily_coverage_frac"] = 0.2
    ev = AcceptanceEvaluator()
    result = ev.evaluate(m, provenance_complete=True)
    assert result["status"] == "ML_STEP4_RUN_INVALID_INSUFFICIENT_OOS_SAMPLE"


def test_missing_provenance_is_hard_invalid() -> None:
    ev = AcceptanceEvaluator()
    result = ev.evaluate(_passing_metrics(), provenance_complete=False)
    assert result["status"] == "ML_STEP4_RUN_INVALID_PROVENANCE_MISSING"


def test_trigger_precedence_is_deterministic() -> None:
    ev = AcceptanceEvaluator()
    result = ev.evaluate(
        _passing_metrics(),
        provenance_complete=False,  # PROVENANCE_MISSING
        hard_triggers={"CHECKSUM_MISMATCH", "SCOPE_EXPANSION"},
    )
    # CHECKSUM_MISMATCH has highest precedence.
    assert result["status"] == "ML_STEP4_RUN_INVALID_CHECKSUM_MISMATCH"


def test_cost_sensitivity_gate() -> None:
    m = _passing_metrics()
    m["cost_sensitivity"] = {"1.0pip": {"expectancy_pips": -0.2}}  # negative at 1 pip
    ev = AcceptanceEvaluator()
    result = ev.evaluate(m, provenance_complete=True)
    assert result["status"] == DOES_NOT_MEET
    assert result["criteria"]["cost_sensitivity_1pip"]["passed"] is False


def test_invalid_status_helper_rejects_typos() -> None:
    assert invalid_status("SCOPE_EXPANSION") == "ML_STEP4_RUN_INVALID_SCOPE_EXPANSION"
    with pytest.raises(ValueError):
        invalid_status("NOT_A_REAL_REASON")
