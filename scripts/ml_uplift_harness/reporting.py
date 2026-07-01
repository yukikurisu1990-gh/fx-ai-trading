"""Synthetic report building + writing for the ML uplift harness.

Every report is clearly marked SYNTHETIC-ONLY, carries the non-authorisation
flags, and is validated to contain no forbidden success/promotion tokens and no
trading-metric values before it is written.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import (
    FORBIDDEN_REPORT_TOKENS,
    NON_AUTHORISATION_FLAGS,
    STATUS_BACKTEST_NOT_AUTHORISED,
    STATUS_BYTE_ADMISSIBILITY_NOT_APPROVED,
    STATUS_MODEL_TRAINING_NOT_AUTHORISED,
    STATUS_NEW_EPOCH_NOT_AUTHORISED,
    STATUS_PRODUCTION_CHANGE_NOT_AUTHORISED,
    STATUS_REAL_DATA_READ_NOT_AUTHORISED,
    STATUS_REAL_EXPERIMENT_NOT_AUTHORISED,
    STATUS_REPORT_SHAPE_VALIDATED,
    STATUS_T2_NOT_AUTHORISED,
    STATUS_TRADING_METRICS_NOT_COMPUTED,
    SYNTHETIC_MARKERS,
)
from .contracts import ExperimentContract, HarnessContractError
from .validators import assert_no_metric_values

_MAX_BYTES = 512 * 1024

_STATUS_SET = [
    STATUS_REPORT_SHAPE_VALIDATED,
    STATUS_REAL_EXPERIMENT_NOT_AUTHORISED,
    STATUS_REAL_DATA_READ_NOT_AUTHORISED,
    STATUS_MODEL_TRAINING_NOT_AUTHORISED,
    STATUS_BACKTEST_NOT_AUTHORISED,
    STATUS_TRADING_METRICS_NOT_COMPUTED,
    STATUS_T2_NOT_AUTHORISED,
    STATUS_BYTE_ADMISSIBILITY_NOT_APPROVED,
    STATUS_NEW_EPOCH_NOT_AUTHORISED,
    STATUS_PRODUCTION_CHANGE_NOT_AUTHORISED,
]


def build_synthetic_report(
    contract: ExperimentContract,
    provenance: dict[str, Any],
    artifact_manifest: dict[str, Any],
    contract_status: str,
) -> dict[str, Any]:
    """Assemble the synthetic-only report payload (no metric values)."""
    flags = {name: False for name in NON_AUTHORISATION_FLAGS}
    return {
        "experiment_id": contract.experiment_id,
        "purpose": contract.purpose,
        "markers": list(SYNTHETIC_MARKERS),
        "statuses": [contract_status, *_STATUS_SET],
        "non_authorisation_flags": flags,
        "provenance": provenance,
        "artifact_manifest": artifact_manifest,
        "contract_echo": contract.to_dict(),
        "metrics_schema_names_only": contract.output_report.metrics_schema,
        "notice": (
            "SYNTHETIC_ONLY harness report; NOT_REAL_EXPERIMENT_EVIDENCE. "
            "NO_MODEL_RUN, NO_BACKTEST, NO_TRADING_METRICS. No real data was "
            "read; no features / labels / model / inference / sweep / replay "
            "occurred; no PnL / Sharpe / IC / MI / oracle / calibration / "
            "expected-value computed. No T2 execution, byte-admissibility, "
            "new-epoch adoption, production routing, or LLM integration was "
            "authorised. This is harness scaffolding validation only."
        ),
    }


def _assert_clean(text: str) -> None:
    for token in FORBIDDEN_REPORT_TOKENS:
        if token in text:
            raise HarnessContractError(f"report contains forbidden token '{token}'")


def write_report(output_dir: Path, filename: str, payload: dict[str, Any]) -> Path:
    """Validate + write a JSON report to ``output_dir`` (metadata only)."""
    if not filename.endswith(".json"):
        raise HarnessContractError(f"'{filename}' is not a .json report")
    assert_no_metric_values(payload)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    _assert_clean(text)
    if len(text.encode("utf-8")) > _MAX_BYTES:
        raise HarnessContractError(f"report '{filename}' exceeds size ceiling")
    target = Path(output_dir) / filename
    target.write_text(text + "\n", encoding="utf-8")
    return target


def write_markdown(output_dir: Path, filename: str, text: str) -> Path:
    if not filename.endswith(".md"):
        raise HarnessContractError(f"'{filename}' is not a .md report")
    _assert_clean(text)
    if len(text.encode("utf-8")) > _MAX_BYTES:
        raise HarnessContractError(f"report '{filename}' exceeds size ceiling")
    target = Path(output_dir) / filename
    target.write_text(text, encoding="utf-8")
    return target
