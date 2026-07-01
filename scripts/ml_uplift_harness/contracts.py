"""Experiment contract objects for the ML uplift harness (synthetic-only).

Strongly-typed spec dataclasses. These describe an intended future experiment;
they materialise NOTHING (no real data, features, labels, model, or metrics).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .constants import CONTRACT_VERSION


class HarnessContractError(ValueError):
    """Raised when an experiment contract is malformed or fails closed."""


@dataclass
class DataSpanSpec:
    candidate_span_id: str
    synthetic_fixture: bool = True
    real_data_authorised: bool = False


@dataclass
class FeatureSetSpec:
    feature_set_id: str
    feature_family: list[str] = field(default_factory=list)


@dataclass
class LabelContractSpec:
    label_contract_id: str
    horizon: int
    barrier_type: str
    cost_inclusion: bool


@dataclass
class CostContractSpec:
    spread_assumption: float
    slippage_stress: str
    commission_hurdle: float


@dataclass
class ValidationSplitSpec:
    split_type: str
    walk_forward_folds: int
    purged: bool
    embargo_bars: int


@dataclass
class ModelConfigSpec:
    model_family: str
    hyperparameters: dict[str, Any]
    random_seed: int


@dataclass
class OutputReportSpec:
    artifact_root: str
    report_files: list[str]
    metrics_schema: list[str]  # metric NAMES only; never values


@dataclass
class NonAuthorisationFlags:
    real_data_read: bool = False
    feature_generation_performed: bool = False
    label_generation_performed: bool = False
    model_training_performed: bool = False
    model_inference_performed: bool = False
    backtest_performed: bool = False
    sweep_performed: bool = False
    replay_performed: bool = False
    trading_metrics_computed: bool = False
    t2_execution_authorised: bool = False
    byte_admissibility_approved: bool = False
    new_epoch_adoption_authorised: bool = False
    production_change_authorised: bool = False
    llm_integration_authorised: bool = False


@dataclass
class ExperimentContract:
    experiment_id: str
    purpose: str
    generated_at: str | None
    code_sha: str | None
    data_span: DataSpanSpec
    feature_set: FeatureSetSpec
    label_contract: LabelContractSpec
    cost_contract: CostContractSpec
    validation_split: ValidationSplitSpec
    model_config: ModelConfigSpec
    output_report: OutputReportSpec
    non_authorisation: NonAuthorisationFlags
    contract_version: str = CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict

        return asdict(self)


_REQUIRED_SECTIONS = (
    "data_span",
    "feature_set",
    "label_contract",
    "cost_contract",
    "validation_split",
    "model_config",
    "output_report",
)


def _require(payload: dict[str, Any], key: str) -> Any:
    if key not in payload:
        raise HarnessContractError(f"contract missing required field: {key}")
    return payload[key]


def contract_from_dict(payload: dict[str, Any]) -> ExperimentContract:
    """Build an ExperimentContract from a plain dict, failing closed."""
    if not isinstance(payload, dict):
        raise HarnessContractError("contract must be a JSON object")
    for section in _REQUIRED_SECTIONS:
        if section not in payload:
            raise HarnessContractError(f"contract missing required section: {section}")
    try:
        return ExperimentContract(
            experiment_id=_require(payload, "experiment_id"),
            purpose=_require(payload, "purpose"),
            generated_at=payload.get("generated_at"),
            code_sha=payload.get("code_sha"),
            contract_version=payload.get("contract_version", CONTRACT_VERSION),
            data_span=DataSpanSpec(**payload["data_span"]),
            feature_set=FeatureSetSpec(**payload["feature_set"]),
            label_contract=LabelContractSpec(**payload["label_contract"]),
            cost_contract=CostContractSpec(**payload["cost_contract"]),
            validation_split=ValidationSplitSpec(**payload["validation_split"]),
            model_config=ModelConfigSpec(**payload["model_config"]),
            output_report=OutputReportSpec(**payload["output_report"]),
            non_authorisation=NonAuthorisationFlags(**payload.get("non_authorisation", {})),
        )
    except TypeError as exc:  # missing/extra sub-fields
        raise HarnessContractError(f"contract sub-spec malformed: {exc}") from exc
