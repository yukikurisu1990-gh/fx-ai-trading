"""Retention feasibility inspection (plan §6.1 / §6.2).

Uses size metadata only (no read, no write, no transfer, no cloud config).
Under first-run mode the two PASS-enabling classifications are forced off and
the classification is restricted to either
``RETENTION_CAPABILITY_REQUIRES_SEPARATE_AUTHORISED_PROBE`` (a candidate
retained-bytes option exists but establishing/probing it needs separate T2
authorisation) or ``RETENTION_DESTINATION_UNRESOLVED`` (no candidate option
recorded).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..b1_constants import (
    ARTIFACT_SIZE_GUARD_BYTES,
    OANDA_ARCHIVE_MANIFEST_RELPATH,
    RETENTION_REQUIRES_PROBE,
    RETENTION_UNRESOLVED,
)

# Rough per-row storage estimate (bytes) for downstream label/split artifacts.
# Heuristic only; never read or generated here.
_LABELS_BYTES_PER_ROW = 64
_SPLIT_MANIFEST_BYTES_PER_ROW = 4


def assess_retention(
    span_label: str,
    files: list[dict[str, Any]],
    *,
    first_run_mode: bool,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Assess retention feasibility from size metadata under first-run rules."""
    repo_root = Path(repo_root)
    raw_bytes = sum(int(f["size_bytes"]) for f in files if f.get("present") and f.get("size_bytes"))
    total_rows = sum(int(f.get("row_count", 0)) for f in files)
    labels_estimate = total_rows * _LABELS_BYTES_PER_ROW
    split_estimate = total_rows * _SPLIT_MANIFEST_BYTES_PER_ROW

    candidate_options: list[dict[str, str]] = []
    if (repo_root / OANDA_ARCHIVE_MANIFEST_RELPATH).exists():
        candidate_options.append(
            {
                "option_id": "oanda_archive_2026_05_31",
                "description": (
                    "10y OANDA practice archive captured 2026-05-31, retained locally only"
                ),
                "manifest_path": OANDA_ARCHIVE_MANIFEST_RELPATH,
                "note": "Recorded as candidate input only. NOT a retention destination.",
            }
        )

    if first_run_mode:
        in_repo_within_guard = False
        existing_archive_visible = False
        classification = RETENTION_REQUIRES_PROBE if candidate_options else RETENTION_UNRESOLVED
    else:  # pragma: no cover - PR-B.1 hardcodes first_run_mode=True
        in_repo_within_guard = False
        existing_archive_visible = False
        classification = RETENTION_UNRESOLVED

    return {
        "span_label": span_label,
        "expected_total_raw_bytes": raw_bytes,
        "expected_labels_storage_estimate_bytes": labels_estimate,
        "expected_split_manifest_storage_estimate_bytes": split_estimate,
        "expected_total_retention_bytes": raw_bytes + labels_estimate + split_estimate,
        "in_repo_retention_size_guard_bytes": ARTIFACT_SIZE_GUARD_BYTES,
        "in_repo_retention_size_guard_semantics": "per-file ceiling, NOT aggregate budget",
        "in_repo_retention_within_guard": in_repo_within_guard,
        "existing_local_immutable_archive_visible_read_only": existing_archive_visible,
        "restoration_procedure_documented": False,
        "candidate_retention_options_requiring_later_authorisation": candidate_options,
        "retention_classification": classification,
    }
