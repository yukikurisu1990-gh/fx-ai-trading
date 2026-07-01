"""PR-B.2 report writers (plan §7).

Emit derived-metadata-only artifacts under the controlled report dir. Writers
enforce: extension allowlist, size ceilings, allowed top-level outcome set,
absence of any forbidden success/verification/authorisation token, and that
report.md never contains ``PASS``. They never write raw rows, credentials, or
trading metrics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..b2_constants import (
    ALLOWED_B2_OUTCOMES,
    B2_SCHEMA_VERSION,
    FORBIDDEN_REPORT_TOKENS,
    PR_B_STAGE_B2,
)
from ..guards import GuardViolationError
from ..tolerances import JSON_ARTIFACT_MAX_BYTES, MARKDOWN_ARTIFACT_MAX_BYTES
from .common_metadata import compute_pr_b_code_hash

_FORBIDDEN_RAW_KEYS = frozenset({"rows", "raw_rows", "candles", "payload", "raw_payload"})


def b2_metadata_block() -> dict[str, Any]:
    return {
        "schema_version": B2_SCHEMA_VERSION,
        "pr_b_stage": PR_B_STAGE_B2,
        "pr_b2_implemented": True,
        "dependency_inventory_performed": True,
        "pipeline_feasibility_performed": True,
        "raw_data_read": False,
        "pipeline_executed": False,
        "model_executed": False,
        "backtest_executed": False,
        "feature_generation_performed": False,
        "label_generation_performed": False,
        "trading_metrics_computed": False,
        "t2_execution_authorised": False,
        "byte_admissibility_approved": False,
        "new_epoch_adoption_authorised": False,
        "production_change_authorised": False,
        "pr_b_code_hash": compute_pr_b_code_hash(),
    }


def _assert_clean(text: str) -> None:
    if "PASS" in text:
        raise GuardViolationError("b2 writer: 'PASS' must never appear in a PR-B.2 report.")
    for token in FORBIDDEN_REPORT_TOKENS:
        if token in text:
            raise GuardViolationError(f"b2 writer: forbidden token '{token}' present.")


def _assert_no_raw_keys(payload: dict[str, Any]) -> None:
    present = _FORBIDDEN_RAW_KEYS.intersection(payload.keys())
    if present:
        raise GuardViolationError(f"b2 writer: forbidden raw-payload key(s) {sorted(present)}.")


def write_b2_json(report_dir: Path, filename: str, payload: dict[str, Any]) -> Path:
    if not filename.endswith(".json"):
        raise GuardViolationError(f"b2 writer: '{filename}' is not a .json artifact.")
    _assert_no_raw_keys(payload)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    _assert_clean(text)
    encoded = text.encode("utf-8")
    if len(encoded) > JSON_ARTIFACT_MAX_BYTES:
        raise GuardViolationError(f"b2 writer: '{filename}' exceeds the JSON ceiling.")
    target = Path(report_dir) / filename
    target.write_text(text + "\n", encoding="utf-8")
    return target


def write_b2_markdown(report_dir: Path, filename: str, text: str) -> Path:
    if not filename.endswith(".md"):
        raise GuardViolationError(f"b2 writer: '{filename}' is not a .md artifact.")
    _assert_clean(text)
    encoded = text.encode("utf-8")
    if len(encoded) > MARKDOWN_ARTIFACT_MAX_BYTES:
        raise GuardViolationError(f"b2 writer: '{filename}' exceeds the markdown ceiling.")
    target = Path(report_dir) / filename
    target.write_text(text, encoding="utf-8")
    return target


def validate_b2_outcome(outcome: str) -> None:
    if outcome not in ALLOWED_B2_OUTCOMES:
        raise GuardViolationError(
            f"b2 writer: outcome '{outcome}' is not an allowed PR-B.2 outcome "
            f"{sorted(ALLOWED_B2_OUTCOMES)} (PASS / Tier-1 / byte-admissibility unreachable)."
        )
