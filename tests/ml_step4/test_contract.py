"""Contract config immutability, hash stability/sensitivity, fail-closed guards."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scripts.ml_step4 import contract

_TRAINER_PATH = Path(__file__).resolve().parents[2] / "scripts" / "train_lgbm_models.py"


def _trainer_literal(name: str):
    """AST-extract a module-level literal from the committed trainer (no import)."""
    tree = ast.parse(_TRAINER_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in {_TRAINER_PATH}")


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


# --- PR #411 B-1 fix: hyperparameters pinned to the trainer's committed literals


def test_b1_lgbm_params_equal_trainer_literals() -> None:
    """Frozen params MUST equal scripts/train_lgbm_models.py _LGBM_PARAMS (AST-pinned)."""
    assert _trainer_literal("_LGBM_PARAMS") == contract.LGBM_PARAMS
    assert contract.LGBM_PARAMS == {"learning_rate": 0.05, "num_leaves": 31, "verbose": -1}


def test_b1_n_estimators_equals_trainer_literal() -> None:
    assert _trainer_literal("_N_ESTIMATORS") == contract.LGBM_N_ESTIMATORS
    assert contract.LGBM_N_ESTIMATORS == 200


def test_b1_no_research_hyperparameters() -> None:
    """The v14 research extras from the PR #411 B-1 drift must be absent."""
    for extra in ("min_child_samples", "reg_alpha", "reg_lambda", "random_state", "n_jobs"):
        assert extra not in contract.LGBM_PARAMS
    mc = contract.model_config()
    assert "random_seed" not in mc  # trainer defines no seed; wiring PR decides
    assert mc["seed_policy"] == "wiring_pr_responsibility_trainer_defines_none"


def test_b1_extra_hyperparameter_changes_model_hash() -> None:
    base = contract.model_config_hash()
    mutated = dict(contract.model_config())
    mutated["params"] = {**mutated["params"], "reg_alpha": 0.1}
    assert contract._sha256_hex(mutated) != base
