"""ML uplift harness provenance / hashing tests."""

from __future__ import annotations

from scripts.ml_uplift_harness.contracts import contract_from_dict
from scripts.ml_uplift_harness.provenance import (
    UNCAPTURED_CODE_SHA,
    canonical_hash,
    capture_provenance,
    contract_hashes,
)


def test_canonical_hash_deterministic():
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}
    assert canonical_hash(a) == canonical_hash(b)  # key order independent
    assert canonical_hash(a) != canonical_hash({"a": 2, "b": 3})


def test_contract_hashes_deterministic(synthetic_contract):
    c1 = contract_from_dict(synthetic_contract)
    c2 = contract_from_dict(synthetic_contract)
    assert contract_hashes(c1) == contract_hashes(c2)
    keys = set(contract_hashes(c1))
    assert {
        "feature_contract_hash",
        "label_contract_hash",
        "cost_contract_hash",
        "validation_contract_hash",
        "model_config_hash",
        "experiment_contract_hash",
    } <= keys


def test_capture_provenance_uses_stub_when_no_sha(synthetic_contract):
    synthetic_contract["code_sha"] = None
    contract = contract_from_dict(synthetic_contract)
    prov = capture_provenance(contract, code_sha=None)
    assert prov["code_sha"] == UNCAPTURED_CODE_SHA
    assert "hashes" in prov and prov["contract_version"] == "ml-uplift-harness.v1"


def test_capture_provenance_prefers_explicit_sha(synthetic_contract):
    contract = contract_from_dict(synthetic_contract)
    prov = capture_provenance(contract, code_sha="explicit-sha")
    assert prov["code_sha"] == "explicit-sha"
