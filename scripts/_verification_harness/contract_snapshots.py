"""Contract-snapshot loader for V2-expanded sentinels S-1..S-6.

Loads the 6 committed contract-snapshot docs under
``docs/design/v2_expanded_contract_snapshots/`` and computes their SHA-256.
The orchestrator (Stage 2/3) records the hashes in
``manifests/contract_snapshot_hashes.json`` and HALTs on mismatch at
runtime.

Per amendment Stage 1 binding: this module loads the docs as opaque text
+ SHA; it does NOT parse semantic content. Adapters (Stage 3) consume the
snapshot files directly for their own pinning.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOTS_DIR = REPO_ROOT / "docs" / "design" / "v2_expanded_contract_snapshots"


class ContractSnapshotError(RuntimeError):
    """Raised when a required snapshot is missing or its SHA changes mid-run."""


SENTINEL_SNAPSHOT_FILES: tuple[tuple[str, str], ...] = (
    ("S-1", "s1_pr325_snapshot.md"),
    ("S-2", "s2_pr332_snapshot.md"),
    ("S-3", "s3_pr338_snapshot.md"),
    ("S-4", "s4_pr342_snapshot.md"),
    ("S-5", "s5_pr345_snapshot.md"),
    ("S-6", "s6_pr351_snapshot.md"),
)


@dataclass
class ContractSnapshot:
    sentinel_id: str
    file_name: str
    abs_path: Path
    content_sha256: str
    n_bytes: int


def load_all_snapshots() -> list[ContractSnapshot]:
    """Load every required snapshot; HALT if any is missing."""
    out: list[ContractSnapshot] = []
    for sentinel_id, fname in SENTINEL_SNAPSHOT_FILES:
        p = SNAPSHOTS_DIR / fname
        if not p.is_file():
            raise ContractSnapshotError(f"required snapshot missing for {sentinel_id}: {p}")
        data = p.read_bytes()
        out.append(
            ContractSnapshot(
                sentinel_id=sentinel_id,
                file_name=fname,
                abs_path=p,
                content_sha256=hashlib.sha256(data).hexdigest(),
                n_bytes=len(data),
            )
        )
    return out


def write_snapshot_hashes_manifest(snapshots: list[ContractSnapshot], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema_version": "v2-expanded-1.0",
        "snapshots": [
            {
                "sentinel_id": s.sentinel_id,
                "file_name": s.file_name,
                "content_sha256": s.content_sha256,
                "n_bytes": s.n_bytes,
            }
            for s in snapshots
        ],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def assert_snapshots_stable(
    expected: list[ContractSnapshot], observed: list[ContractSnapshot]
) -> None:
    """HALT if any snapshot SHA changed between two checkpoints in the run."""
    exp_by_id = {s.sentinel_id: s.content_sha256 for s in expected}
    obs_by_id = {s.sentinel_id: s.content_sha256 for s in observed}
    if exp_by_id.keys() != obs_by_id.keys():
        raise ContractSnapshotError(
            f"snapshot set differs: expected={sorted(exp_by_id)} observed={sorted(obs_by_id)}"
        )
    for sid, exp_sha in exp_by_id.items():
        obs_sha = obs_by_id[sid]
        if exp_sha != obs_sha:
            raise ContractSnapshotError(
                f"snapshot {sid!r} SHA changed mid-run: expected={exp_sha[:12]} "
                f"observed={obs_sha[:12]}"
            )


# ---------------------------------------------------------------------------
# Companion review classification (loaded from PR #358 amendment companion doc)
# ---------------------------------------------------------------------------


COMPANION_REVIEW_PATH = (
    REPO_ROOT
    / "docs"
    / "design"
    / "tabular_targeted_verification_v2_expanded_historic_compatibility_review.md"
)


COMPATIBILITY_CLASSIFICATIONS: dict[str, dict[str, str]] = {
    "S-1": {
        "test_touched_once": "HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE",
        "data_identity": "HISTORIC_DATA_IDENTITY_NOT_PROVABLE",
        "permitted_wording": "CURRENT_MANIFEST_CLEAN_REEXECUTION_ONLY",
    },
    "S-2": {
        "test_touched_once": "HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE",
        "data_identity": "HISTORIC_DATA_IDENTITY_NOT_PROVABLE",
        "permitted_wording": "CURRENT_MANIFEST_CLEAN_REEXECUTION_ONLY",
    },
    "S-3": {
        "test_touched_once": "HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE",
        "data_identity": "HISTORIC_DATA_IDENTITY_NOT_PROVABLE",
        "permitted_wording": "CURRENT_MANIFEST_CLEAN_REEXECUTION_ONLY",
    },
    "S-4": {
        "test_touched_once": "HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE",
        "data_identity": "HISTORIC_DATA_IDENTITY_NOT_PROVABLE",
        "permitted_wording": "CURRENT_MANIFEST_CLEAN_REEXECUTION_ONLY",
    },
    "S-5": {
        "test_touched_once": "HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE",
        "data_identity": "HISTORIC_DATA_IDENTITY_NOT_PROVABLE",
        "permitted_wording": "CURRENT_MANIFEST_CLEAN_REEXECUTION_ONLY",
    },
    "S-6": {
        "test_touched_once": "HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE",
        "data_identity": "HISTORIC_DATA_IDENTITY_NOT_PROVABLE",
        "permitted_wording": "CURRENT_MANIFEST_CLEAN_REEXECUTION_ONLY",
    },
}


def write_compatibility_classification_artifact(out_path: Path) -> None:
    """Persist the per-sentinel classifications + companion-review-doc SHA."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    review_sha: str | None = None
    if COMPANION_REVIEW_PATH.is_file():
        review_sha = hashlib.sha256(COMPANION_REVIEW_PATH.read_bytes()).hexdigest()
    payload: dict[str, Any] = {
        "schema_version": "v2-expanded-1.0",
        "classifications": COMPATIBILITY_CLASSIFICATIONS,
        "companion_review_path": str(COMPANION_REVIEW_PATH).replace("\\", "/"),
        "companion_review_sha256": review_sha,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Forbidden wording registry (amendment §A.3)
# ---------------------------------------------------------------------------


PERMITTED_PER_SENTINEL_WORDING: str = "CURRENT_MANIFEST_CLEAN_REEXECUTION_ONLY"

# Permitted aggregate narrative (binding per §A.3)
PERMITTED_AGGREGATE_WORDING: str = (
    "clean re-execution of the V2-expanded contract under the current provenance-bound dataset"
)

# Forbidden wording (binding per §A.3 + design memo §10)
FORBIDDEN_WORDINGS: tuple[str, ...] = (
    "historical execution verified",
    "historic verdict reproduced",
    "historical negative verdict reproduction",
    "prior verdict revalidated",
    "prior verdict disproven",
    "historical verdict invalidated",
    "tabular evidence reconfirmed",
    "empirically clean",
    "PASS_TABULAR_EVIDENCE_RECONFIRMED",
    "FULL_TABULAR_EVIDENCE_REBUILT",
)


def assert_wording_not_forbidden(text: str) -> None:
    """HALT if ``text`` contains any forbidden wording string."""
    lo = text.lower()
    for forbidden in FORBIDDEN_WORDINGS:
        if forbidden.lower() in lo:
            raise ContractSnapshotError(f"forbidden wording detected: {forbidden!r}")
