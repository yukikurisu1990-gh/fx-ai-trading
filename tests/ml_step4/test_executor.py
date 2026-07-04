"""Guarded executor wiring tests (synthetic-only, no run)."""

from __future__ import annotations

import pytest

from scripts.ml_step4 import contract, evidence, executor, labels
from scripts.ml_step4.executor import (
    NON_DECISION_EXPLORATORY,
    PREFLIGHT_GATES,
    DiagnosticLabelingError,
    ExecutionRefusedError,
    PreflightError,
)

# --- Guarded entrypoint refuses real execution -------------------------------


def test_guarded_execute_refuses_real() -> None:
    with pytest.raises(ExecutionRefusedError):
        executor.guarded_execute(dry_run=False)


def test_guarded_execute_refuses_even_with_allow_flag() -> None:
    with pytest.raises(ExecutionRefusedError):
        executor.guarded_execute(dry_run=True, allow_real_execution=True)


def test_dry_run_returns_plan_with_no_execution_flags() -> None:
    plan = executor.guarded_execute(dry_run=True)
    assert plan["implementation_status"] == "ML_STEP4_GUARDED_EXECUTE_WIRING_IMPLEMENTED_NO_RUN"
    for flag in (
        "execution_performed",
        "raw_data_read",
        "model_trained",
        "holdout_evaluated",
        "evidence_written",
    ):
        assert plan[flag] is False


def test_plan_is_scrub_clean_and_carries_hashes() -> None:
    plan = executor.build_execution_plan()
    evidence.assert_clean(plan)  # metadata-only guarantee
    h = plan["hashes"]
    assert set(h) >= {
        "config_hash",
        "feature_config_hash",
        "model_config_hash",
        "threshold_config_hash",
    }
    assert all(len(v) == 64 for v in h.values())


# --- Preflight hard-gate orchestration ---------------------------------------


def test_preflight_all_gates_present_no_raw_read() -> None:
    r = executor.run_preflight()
    assert r["status"] == "PREFLIGHT_WIRING_COMPLETE_NO_RUN"
    assert r["missing_or_incomplete"] == []
    assert set(r["gates"]) == set(PREFLIGHT_GATES)
    assert r["raw_data_read"] is False
    assert r["checksums_computed"] is False
    assert r["inventory_metadata"]["checksums_computed"] is False
    assert r["inventory_metadata"]["file_count"] == contract.EXPECTED_FILE_COUNT
    assert r["inventory_metadata"]["total_bytes"] == contract.EXPECTED_TOTAL_BYTES


def test_preflight_refuses_when_inventory_unresolvable(tmp_path) -> None:
    r = executor.run_preflight(str(tmp_path / "nope.json"))
    assert r["status"] == "PREFLIGHT_REFUSED_INCOMPLETE"
    assert "inventory_resolver_available" in r["missing_or_incomplete"]


# --- R-4 label routing -------------------------------------------------------


def test_r4_label_contract_identity_in_plan() -> None:
    plan = executor.build_execution_plan()
    ident = plan["residual_bindings"]["R4_label_routing"]
    assert ident["label_contract_id"] == labels.LABEL_CONTRACT_ID
    assert ident["delegates_to"] == "scripts.traded_direction_pnl.traded_direction_pnl_price"


def test_r4_label_adapter_is_single_source() -> None:
    # The sanctioned scorer delegates to the committed F-2 helper (no fork).
    from scripts.traded_direction_pnl import traded_direction_pnl_price

    assert labels.traded_direction_pnl_price is traded_direction_pnl_price


# --- R-6 tie-rule provenance -------------------------------------------------


def test_r6_tie_rule_in_config_and_hash() -> None:
    tc = contract.threshold_config()
    assert tc["tie_rule"] == contract.THRESHOLD_TIE_RULE
    assert "tie_rule" in tc
    # config_hash covers the tie rule (present in contract_dict).
    assert "prefer_production_default" in contract.THRESHOLD_TIE_RULE


def test_r6_changing_tie_rule_changes_hash() -> None:
    base = contract.threshold_config_hash()
    mutated = contract._sha256_hex({**contract.threshold_config(), "tie_rule": "other"})
    assert base != mutated


# --- Seed / determinism policy -----------------------------------------------


def test_seed_policy_present_and_does_not_alter_model_hash() -> None:
    before = contract.model_config_hash()
    rp = executor.reproducibility_policy()
    assert rp["alters_model_config_hash"] is False
    assert rp["reproducibility_level"] == "bounded_not_bitwise_guaranteed"
    # model contract has no seed and is unchanged by the policy existing.
    assert "random_seed" not in contract.model_config()
    assert contract.model_config_hash() == before


def test_missing_seed_policy_fails_closed() -> None:
    with pytest.raises(PreflightError):
        executor.assert_reproducibility_recorded({"reproducibility_policy": {"foo": 1}})
    with pytest.raises(PreflightError):
        executor.assert_reproducibility_recorded({})


# --- maxDD fixed-notional constant -------------------------------------------


def test_maxdd_notional_in_provenance() -> None:
    ev = contract.contract_dict()["evaluation"]
    assert ev["fixed_notional_equity_pips"] == 10_000.0
    assert ev["fixed_notional_equity_pips"] == contract.FIXED_NOTIONAL_EQUITY_PIPS


def test_maxdd_notional_changes_config_hash() -> None:
    base = contract.config_hash()
    d = contract.contract_dict()
    d["evaluation"]["fixed_notional_equity_pips"] = 5000.0
    assert contract._sha256_hex(d) != base


def test_missing_maxdd_notional_fails_closed() -> None:
    with pytest.raises(PreflightError):
        executor.assert_maxdd_notional({"evaluation": {}})


# --- NON_DECISION_EXPLORATORY labeling ---------------------------------------


def test_diagnostics_get_labeled() -> None:
    labeled = executor.label_diagnostics({"feature_importance": [1, 2], "calibration": {"x": 1}})
    for entry in labeled.values():
        assert entry["classification"] == NON_DECISION_EXPLORATORY


def test_unlabeled_diagnostic_fails_closed() -> None:
    with pytest.raises(DiagnosticLabelingError):
        executor.assert_diagnostics_labeled({"feature_importance": [1, 2]})  # bare, no label


def test_decision_metric_mislabeled_as_exploratory_fails_closed() -> None:
    bad = {"expectancy_pips": {"classification": NON_DECISION_EXPLORATORY, "value": 0.4}}
    with pytest.raises(DiagnosticLabelingError):
        executor.assert_diagnostics_labeled(bad)


def test_exploratory_cannot_influence_acceptance() -> None:
    # An acceptance result whose criteria table only holds decision keys is clean;
    # a leaked exploratory key is rejected.
    executor.assert_diagnostics_excluded_from_decision(
        {"criteria": {"daily_portfolio_sharpe": {}, "turnover": {}}}
    )
    with pytest.raises(DiagnosticLabelingError):
        executor.assert_diagnostics_excluded_from_decision(
            {"criteria": {"feature_importance": {}, "turnover": {}}}
        )
