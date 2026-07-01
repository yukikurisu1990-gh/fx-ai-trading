"""ML uplift harness contract-object tests."""

from __future__ import annotations

import pytest

from scripts.ml_uplift_harness.contracts import (
    ExperimentContract,
    HarnessContractError,
    contract_from_dict,
)


def test_valid_contract_roundtrip(synthetic_contract):
    contract = contract_from_dict(synthetic_contract)
    assert isinstance(contract, ExperimentContract)
    assert contract.experiment_id == "synthetic-exp-001"
    assert contract.data_span.real_data_authorised is False
    # to_dict roundtrips the nested structure.
    d = contract.to_dict()
    assert d["label_contract"]["horizon"] == 30
    assert d["model_config"]["random_seed"] == 7


def test_missing_section_fails_closed(synthetic_contract):
    del synthetic_contract["model_config"]
    with pytest.raises(HarnessContractError):
        contract_from_dict(synthetic_contract)


def test_missing_top_level_field_fails_closed(synthetic_contract):
    del synthetic_contract["experiment_id"]
    with pytest.raises(HarnessContractError):
        contract_from_dict(synthetic_contract)


def test_malformed_subspec_fails_closed(synthetic_contract):
    synthetic_contract["data_span"] = {"unexpected": True}
    with pytest.raises(HarnessContractError):
        contract_from_dict(synthetic_contract)


def test_non_dict_payload_fails_closed():
    with pytest.raises(HarnessContractError):
        contract_from_dict(["not", "a", "dict"])
