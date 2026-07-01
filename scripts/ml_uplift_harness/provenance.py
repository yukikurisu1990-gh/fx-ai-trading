"""Provenance + deterministic hashing for the ML uplift harness.

Hashes are computed deterministically over canonical JSON of a config subset.
No subprocess / git / network is used here: the code SHA is provided by the
caller (or recorded as UNCAPTURED), keeping the harness side-effect-free.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .contracts import ExperimentContract

UNCAPTURED_CODE_SHA = "UNCAPTURED_IN_THIS_CONTEXT"


def canonical_hash(obj: Any) -> str:
    """Deterministic SHA-256 over canonical JSON of ``obj``."""
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def contract_hashes(contract: ExperimentContract) -> dict[str, str]:
    """Deterministic per-section contract hashes."""
    from dataclasses import asdict

    return {
        "feature_contract_hash": canonical_hash(asdict(contract.feature_set)),
        "label_contract_hash": canonical_hash(asdict(contract.label_contract)),
        "cost_contract_hash": canonical_hash(asdict(contract.cost_contract)),
        "validation_contract_hash": canonical_hash(asdict(contract.validation_split)),
        "model_config_hash": canonical_hash(asdict(contract.model_config)),
        "experiment_contract_hash": canonical_hash(contract.to_dict()),
    }


def capture_provenance(
    contract: ExperimentContract, *, code_sha: str | None = None
) -> dict[str, Any]:
    """Return a provenance block (hashes + code SHA + version), no side effects."""
    return {
        "code_sha": code_sha or contract.code_sha or UNCAPTURED_CODE_SHA,
        "contract_version": contract.contract_version,
        "generated_at": contract.generated_at,
        "hashes": contract_hashes(contract),
    }
