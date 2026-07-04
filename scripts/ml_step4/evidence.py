"""Metadata-only evidence writer + dedicated ML Step 4 scrubber (fail-closed).

Unlike the Foundation T2 scrubber (which forbids trading-metric keys), ML Step 4
evidence legitimately carries metrics (sharpe / pnl / expectancy / drawdown), so
this scrubber ALLOWS metric keys while still rejecting: raw candle/quote rows,
personal / runtime absolute paths, credentials, environment dumps, Google Drive
links, and R2 object keys / endpoints. Output JSON is deterministically ordered.

Safety guard: this writer refuses to create real first-run execution evidence
under ``artifacts/ml_step4/365d_ba_v1/`` unless a future, separately-authorised
execution explicitly opts in — nothing in this no-run PR does.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Final

from scripts.foundation_t2.constants import (
    CREDENTIAL_KEY_NAMES,
    LOCAL_PATH_PATTERNS,
    RAW_ROW_KEYS,
    SECRET_VALUE_PATTERNS,
)

SCRUBBER_VERSION: Final[str] = "ml-step4-evidence-scrubber.v1"

# Real first-run execution evidence directory (guarded in this no-run PR).
EXECUTION_EVIDENCE_DIR: Final[str] = "artifacts/ml_step4/365d_ba_v1"

EXPECTED_EVIDENCE_FILES: Final[tuple[str, ...]] = (
    "ml_step4_run_manifest.json",
    "ml_step4_pre_consumption_checksum_report.json",
    "ml_step4_split_report.json",
    "ml_step4_model_config_report.json",
    "ml_step4_metrics_report.json",
    "ml_step4_cost_sensitivity_report.json",
    "ml_step4_leakage_provenance_report.json",
    "ml_step4_acceptance_failure_decision_report.md",
)

# Google Drive / R2 endpoint indicators (object keys / share links).
_GDRIVE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"drive\.google\.com", re.IGNORECASE),
    re.compile(r"docs\.google\.com", re.IGNORECASE),
    re.compile(r"googleusercontent\.com", re.IGNORECASE),
)
_R2_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"[a-z0-9]+\.r2\.cloudflarestorage\.com", re.IGNORECASE),
    re.compile(r"\br2://", re.IGNORECASE),
)
# Environment-dump heuristic: 3+ SHELL-style VAR=value assignments in one string.
_ENV_DUMP_PATTERN: Final[re.Pattern[str]] = re.compile(r"(?:[A-Z][A-Z0-9_]{2,}=[^\s;]+[;\n\s]){3,}")
_ENV_DUMP_KEYS: Final[frozenset[str]] = frozenset({"env", "environ", "environment"})


class EvidenceScrubError(RuntimeError):
    """Raised when evidence would leak forbidden content or write is unsafe."""


def _scan_text(text: str, findings: list[str]) -> None:
    for pattern in LOCAL_PATH_PATTERNS:
        if pattern.search(text):
            findings.append(f"local_path:{pattern.pattern}")
    for pattern in SECRET_VALUE_PATTERNS:
        if pattern.search(text):
            findings.append(f"secret_value:{pattern.pattern}")
    for pattern in _GDRIVE_PATTERNS:
        if pattern.search(text):
            findings.append(f"google_drive:{pattern.pattern}")
    for pattern in _R2_PATTERNS:
        if pattern.search(text):
            findings.append(f"r2_object_key:{pattern.pattern}")
    if _ENV_DUMP_PATTERN.search(text):
        findings.append("env_dump:var_assignments")


def _scan_keys(obj: Any, findings: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str):
                low = key.lower()
                if low in RAW_ROW_KEYS:
                    findings.append(f"raw_row_key:{key}")
                if low in CREDENTIAL_KEY_NAMES and isinstance(value, str) and value.strip():
                    findings.append(f"credential_key:{key}")
                if low in _ENV_DUMP_KEYS and isinstance(value, (dict, list)) and value:
                    findings.append(f"env_dump_key:{key}")
            _scan_keys(value, findings)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _scan_keys(item, findings)


def scan_payload(payload: Any) -> list[str]:
    """Return cleanliness findings (empty == clean); allows metric keys."""
    findings: list[str] = []
    _scan_keys(payload, findings)
    _scan_text(json.dumps(payload, ensure_ascii=False, default=str), findings)
    return sorted(set(findings))


def assert_clean(payload: Any) -> None:
    findings = scan_payload(payload)
    if findings:
        raise EvidenceScrubError(f"evidence not clean: {findings}")


def serialise(report: Any) -> str:
    """Deterministically-ordered JSON (sorted keys, no BOM, trailing newline)."""
    return json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


# PR #411 R-2 fix: the guard is anchored to the REPO ROOT derived from this
# module's own location (scripts/ml_step4/evidence.py -> parents[2]), NOT the
# process working directory — changing cwd cannot bypass it, and `..`
# traversal is neutralised by resolve() before comparison.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    """Deterministic repository root (module-anchored, cwd-independent)."""
    return _REPO_ROOT


def _is_under_execution_dir(target: Path) -> bool:
    exec_dir = (_REPO_ROOT / EXECUTION_EVIDENCE_DIR).resolve()
    try:
        resolved = target.resolve()
    except OSError:  # pragma: no cover - defensive
        return False
    return resolved == exec_dir or exec_dir in resolved.parents


def write_report(
    directory: str | Path,
    filename: str,
    report: Any,
    *,
    allow_execution_evidence: bool = False,
) -> Path:
    """Scrub then write one metadata-only report deterministically; fail closed.

    Refuses to write into the real execution-evidence directory unless
    ``allow_execution_evidence`` (nothing in this no-run PR sets it).
    """
    target_dir = Path(directory)
    if not allow_execution_evidence and _is_under_execution_dir(target_dir):
        raise EvidenceScrubError(
            "refusing to write real first-run execution evidence under "
            f"{EXECUTION_EVIDENCE_DIR}/ in a no-run context"
        )
    assert_clean(report)
    target_dir.mkdir(parents=True, exist_ok=True)
    out = target_dir / filename
    if filename.endswith(".json"):
        out.write_text(serialise(report), encoding="utf-8")
    else:
        if not isinstance(report, str):
            raise EvidenceScrubError(f"non-JSON report {filename} must be a string")
        assert_clean(report)
        out.write_text(report if report.endswith("\n") else report + "\n", encoding="utf-8")
    return out
