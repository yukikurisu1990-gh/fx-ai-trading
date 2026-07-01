"""ML uplift harness validation tests (fail-closed on any real-run flag)."""

from __future__ import annotations

import pytest

from scripts.ml_uplift_harness.constants import STATUS_CONTRACT_VALIDATED
from scripts.ml_uplift_harness.contracts import HarnessContractError
from scripts.ml_uplift_harness.validators import assert_no_metric_values, validate_contract


def test_valid_synthetic_contract_passes(synthetic_contract):
    result = validate_contract(synthetic_contract)
    assert result.valid is True
    assert result.status == STATUS_CONTRACT_VALIDATED


def test_invalid_candidate_span_fails(synthetic_contract):
    synthetic_contract["data_span"]["candidate_span_id"] = "999d_BA"
    result = validate_contract(synthetic_contract)
    assert result.valid is False


def test_synthetic_span_allowed(synthetic_contract):
    synthetic_contract["data_span"]["candidate_span_id"] = "synthetic-tiny"
    assert validate_contract(synthetic_contract).valid is True


@pytest.mark.parametrize(
    "path",
    [
        ("data_span", "real_data_authorised"),
        ("non_authorisation", "model_training_performed"),
        ("non_authorisation", "model_inference_performed"),
        ("non_authorisation", "backtest_performed"),
        ("non_authorisation", "sweep_performed"),
        ("non_authorisation", "replay_performed"),
        ("non_authorisation", "trading_metrics_computed"),
        ("non_authorisation", "t2_execution_authorised"),
        ("non_authorisation", "byte_admissibility_approved"),
        ("non_authorisation", "new_epoch_adoption_authorised"),
        ("non_authorisation", "production_change_authorised"),
        ("non_authorisation", "llm_integration_authorised"),
        ("non_authorisation", "real_data_read"),
        ("non_authorisation", "feature_generation_performed"),
        ("non_authorisation", "label_generation_performed"),
    ],
)
def test_forbidden_flag_true_fails_closed(synthetic_contract, path):
    section, key = path
    synthetic_contract[section][key] = True
    result = validate_contract(synthetic_contract)
    assert result.valid is False
    assert any(key in e for e in result.errors)


def test_missing_required_field_fails(synthetic_contract):
    del synthetic_contract["label_contract"]
    result = validate_contract(synthetic_contract)
    assert result.valid is False


def test_assert_no_metric_values_rejects_value_bearing_keys():
    with pytest.raises(HarnessContractError):
        assert_no_metric_values({"results": {"sharpe": 1.23}})
    with pytest.raises(HarnessContractError):
        assert_no_metric_values({"pnl": 100.0})
    # metric NAMES as list items are allowed (schema placeholders, no values).
    assert_no_metric_values({"metrics_schema": ["sharpe", "pnl"]})
