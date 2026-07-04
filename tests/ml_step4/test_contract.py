"""Contract config immutability, hash stability/sensitivity, fail-closed guards."""

from __future__ import annotations

import pytest

from scripts.ml_step4 import contract


def test_hashes_are_stable_across_calls() -> None:
    assert contract.config_hash() == contract.config_hash()
    assert contract.feature_config_hash() == contract.feature_config_hash()
    assert contract.model_config_hash() == contract.model_config_hash()


def test_three_hashes_are_distinct() -> None:
    hashes = {
        contract.config_hash(),
        contract.feature_config_hash(),
        contract.model_config_hash(),
    }
    assert len(hashes) == 3


def test_frozen_contract_values() -> None:
    assert contract.EPOCH_ID == "RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1"
    assert contract.SPAN == "365d_BA"
    assert contract.EXPECTED_FILE_COUNT == 20
    assert contract.EXPECTED_TOTAL_BYTES == 1_481_715_517
    assert contract.HORIZON_M1_BARS == 20
    assert contract.PURGE_EMBARGO_BARS == 21
    assert contract.THRESHOLD_CANDIDATES == (0.35, 0.40, 0.45)
    assert contract.PRIMARY_COST_CELL_PIPS == 0.5


def test_feature_config_excludes_optin_groups_by_default() -> None:
    fc = contract.feature_config()
    assert fc["feature_version"] == "v4"
    assert fc["base_only"] is True
    assert fc["enabled_groups"] == []
    assert set(fc["excluded_groups"]) == {"mtf", "vol", "moments"}


def test_feature_config_hash_changes_if_feature_config_changes() -> None:
    base = contract._sha256_hex(contract.feature_config())
    mutated = contract._sha256_hex({**contract.feature_config(), "enabled_groups": ["mtf"]})
    assert base != mutated


def test_model_config_hash_changes_if_model_config_changes() -> None:
    base = contract._sha256_hex(contract.model_config())
    mutated = contract._sha256_hex({**contract.model_config(), "n_estimators": 999})
    assert base != mutated


def test_assert_model_family_rejects_non_lightgbm() -> None:
    contract.assert_model_family(contract.MODEL_FAMILY)  # no raise
    for bad in ("xgboost", "catboost", "sklearn_rf"):
        with pytest.raises(contract.ContractViolationError):
            contract.assert_model_family(bad)


def test_assert_no_deployed_model_reuse() -> None:
    contract.assert_no_deployed_model_reuse(None)
    contract.assert_no_deployed_model_reuse("scratch/new_model.txt")
    for bad in ("models/lgbm/EUR_USD.txt", "MODELS/LGBM/x", "a/models/lgbm/b.pkl"):
        with pytest.raises(contract.ContractViolationError):
            contract.assert_no_deployed_model_reuse(bad)


def test_assert_feature_groups_base_only() -> None:
    assert contract.assert_feature_groups(()) == ()
    assert contract.assert_feature_groups([]) == ()
    for bad in (["mtf"], ["vol"], ["moments"], ["unknown_group"]):
        with pytest.raises(contract.ContractViolationError):
            contract.assert_feature_groups(bad)


def test_forbidden_scope_lists_expansion_spans() -> None:
    for token in ("730d_BA", "3650d_BA", "phase_c2", "broad_hyperparameter_search"):
        assert token in contract.FORBIDDEN_SCOPE
