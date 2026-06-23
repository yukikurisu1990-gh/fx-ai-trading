"""PR-B.1 inspection report writers (plan §7).

Emits derived-metadata-only artifacts under the controlled report dir. Writers
enforce: extension allowlist (.json/.md), per-artifact size ceilings, absence
of any forbidden success/verification label, the allowed first-run
top_level_outcome set, and that report.md never contains ``PASS``. They never
write raw candle rows, credentials, or model outputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..b1_constants import (
    ALLOWED_FIRST_RUN_OUTCOMES,
    B1_SCHEMA_VERSION,
    FORBIDDEN_SUCCESS_LABELS,
    PR_B_STAGE_B1,
)
from ..guards import GuardViolationError
from ..tolerances import JSON_ARTIFACT_MAX_BYTES, MARKDOWN_ARTIFACT_MAX_BYTES
from .common_metadata import compute_pr_b_code_hash

# Keys that must never appear anywhere in a PR-B.1 artifact (raw payloads).
_FORBIDDEN_RAW_KEYS = frozenset({"rows", "raw_rows", "candles", "payload", "raw_payload"})


def b1_metadata_block() -> dict[str, Any]:
    return {
        "schema_version": B1_SCHEMA_VERSION,
        "pr_b_stage": PR_B_STAGE_B1,
        "pr_b1_inspection": True,
        "pr_b2_implemented": False,
        "dependency_inventory_performed": False,
        "pipeline_feasibility_performed": False,
        "t2_execution_authorised": False,
        "pr_b_code_hash": compute_pr_b_code_hash(),
    }


def _assert_no_forbidden_content(text: str) -> None:
    for label in FORBIDDEN_SUCCESS_LABELS:
        if label in text:
            raise GuardViolationError(
                f"b1 writer: forbidden success/verification label '{label}' present."
            )


def _assert_no_raw_keys(payload: dict[str, Any]) -> None:
    present = _FORBIDDEN_RAW_KEYS.intersection(payload.keys())
    if present:
        raise GuardViolationError(f"b1 writer: forbidden raw-payload key(s) {sorted(present)}.")


def write_b1_json(report_dir: Path, filename: str, payload: dict[str, Any]) -> Path:
    if not filename.endswith(".json"):
        raise GuardViolationError(f"b1 writer: '{filename}' is not a .json artifact.")
    _assert_no_raw_keys(payload)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    _assert_no_forbidden_content(text)
    encoded = text.encode("utf-8")
    if len(encoded) > JSON_ARTIFACT_MAX_BYTES:
        raise GuardViolationError(
            f"b1 writer: '{filename}' is {len(encoded)} bytes (> JSON ceiling)."
        )
    target = Path(report_dir) / filename
    target.write_text(text + "\n", encoding="utf-8")
    return target


def write_b1_markdown(report_dir: Path, filename: str, text: str) -> Path:
    if not filename.endswith(".md"):
        raise GuardViolationError(f"b1 writer: '{filename}' is not a .md artifact.")
    if "PASS" in text:
        raise GuardViolationError("b1 writer: 'PASS' must never appear in a PR-B.1 report body.")
    _assert_no_forbidden_content(text)
    encoded = text.encode("utf-8")
    if len(encoded) > MARKDOWN_ARTIFACT_MAX_BYTES:
        raise GuardViolationError(
            f"b1 writer: '{filename}' is {len(encoded)} bytes (> markdown ceiling)."
        )
    target = Path(report_dir) / filename
    target.write_text(text, encoding="utf-8")
    return target


def validate_top_level_outcome(outcome: str) -> None:
    if outcome not in ALLOWED_FIRST_RUN_OUTCOMES:
        raise GuardViolationError(
            f"b1 writer: top_level_outcome '{outcome}' is not an allowed first-run "
            f"outcome {sorted(ALLOWED_FIRST_RUN_OUTCOMES)} (PASS is unreachable)."
        )
