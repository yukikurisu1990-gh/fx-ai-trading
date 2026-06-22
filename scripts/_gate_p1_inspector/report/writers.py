"""Report writers for PR-B.0 (plan §7).

Every write passes through these helpers, which enforce the extension
allowlist (``.json`` / ``.md``) and the per-artifact size ceiling. When the
filesystem guard is active (inner process), the actual write additionally
goes through the write-allowlist; these helpers add the size / extension /
forbidden-key validation on top.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..guards import GuardViolationError
from ..tolerances import (
    JSON_ARTIFACT_MAX_BYTES,
    MARKDOWN_ARTIFACT_MAX_BYTES,
)
from .schema import FORBIDDEN_STUB_KEYS


def _reject_forbidden_keys(payload: dict[str, Any]) -> None:
    present = FORBIDDEN_STUB_KEYS.intersection(payload.keys())
    if present:
        raise GuardViolationError(
            f"report writer: forbidden stub keys present {sorted(present)}; a "
            "PR-B.0 stub must carry no inspection result (plan §7)."
        )


def write_json_artifact(report_dir: Path, filename: str, payload: dict[str, Any]) -> Path:
    """Write a ``.json`` artifact under ``report_dir`` with size + key guards."""
    if not filename.endswith(".json"):
        raise GuardViolationError(f"report writer: '{filename}' is not a .json artifact.")
    _reject_forbidden_keys(payload)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    encoded = text.encode("utf-8")
    if len(encoded) > JSON_ARTIFACT_MAX_BYTES:
        raise GuardViolationError(
            f"report writer: '{filename}' is {len(encoded)} bytes, exceeding the "
            f"{JSON_ARTIFACT_MAX_BYTES}-byte JSON ceiling (plan §7)."
        )
    target = Path(report_dir) / filename
    target.write_text(text + "\n", encoding="utf-8")
    return target


def write_markdown_artifact(report_dir: Path, filename: str, text: str) -> Path:
    """Write a ``.md`` artifact under ``report_dir`` with a size guard."""
    if not filename.endswith(".md"):
        raise GuardViolationError(f"report writer: '{filename}' is not a .md artifact.")
    encoded = text.encode("utf-8")
    if len(encoded) > MARKDOWN_ARTIFACT_MAX_BYTES:
        raise GuardViolationError(
            f"report writer: '{filename}' is {len(encoded)} bytes, exceeding the "
            f"{MARKDOWN_ARTIFACT_MAX_BYTES}-byte markdown ceiling (plan §7)."
        )
    if "PASS" in text:
        raise GuardViolationError(
            "report writer: 'PASS' must never appear in a PR-B.0 report body "
            "(plan §7; first-run PASS is structurally unreachable)."
        )
    target = Path(report_dir) / filename
    target.write_text(text, encoding="utf-8")
    return target
