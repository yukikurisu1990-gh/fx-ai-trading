"""Contract validation for the ML uplift harness (fail-closed, synthetic-only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .constants import (
    ALLOWED_CANDIDATE_SPANS,
    FORBIDDEN_METRIC_KEYS,
    MUST_BE_FALSE_FLAGS,
    STATUS_CONTRACT_VALIDATED,
)
from .contracts import ExperimentContract, HarnessContractError, contract_from_dict


@dataclass
class ValidationResult:
    valid: bool
    status: str
    errors: list[str] = field(default_factory=list)


def _flag_value(contract: ExperimentContract, name: str) -> bool:
    if name == "real_data_authorised":
        return bool(contract.data_span.real_data_authorised)
    return bool(getattr(contract.non_authorisation, name))


def validate_contract(payload: dict[str, Any]) -> ValidationResult:
    """Validate a contract dict. Fails closed on any real-run / authorisation flag."""
    errors: list[str] = []
    try:
        contract = contract_from_dict(payload)
    except HarnessContractError as exc:
        return ValidationResult(valid=False, status="INVALID_CONTRACT", errors=[str(exc)])

    if not contract.experiment_id:
        errors.append("experiment_id must be non-empty")

    span = contract.data_span.candidate_span_id
    if span not in ALLOWED_CANDIDATE_SPANS and not span.startswith("synthetic"):
        errors.append(
            f"candidate_span_id '{span}' not in {sorted(ALLOWED_CANDIDATE_SPANS)} "
            "and not a synthetic span"
        )

    # This PR forbids real data + any real-run / downstream authorisation.
    for flag in MUST_BE_FALSE_FLAGS:
        if _flag_value(contract, flag):
            errors.append(f"{flag}=True is not authorised in this PR (must be False)")

    # metrics_schema may name metrics but must carry NO forbidden performance key
    # as an actual value-bearing field (names only are allowed).
    for name in contract.output_report.metrics_schema:
        if not isinstance(name, str):
            errors.append("metrics_schema entries must be metric NAMES (strings), not values")

    if errors:
        return ValidationResult(valid=False, status="INVALID_CONTRACT", errors=errors)
    return ValidationResult(valid=True, status=STATUS_CONTRACT_VALIDATED)


def assert_no_metric_values(payload: dict[str, Any]) -> None:
    """Raise if any forbidden trading-metric key appears anywhere in the payload."""

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(key, str) and key.lower() in FORBIDDEN_METRIC_KEYS:
                    raise HarnessContractError(f"forbidden trading-metric key present: {key}")
                _walk(value)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                _walk(item)

    _walk(payload)
