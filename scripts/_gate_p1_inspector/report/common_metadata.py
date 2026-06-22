"""Common metadata block stamped into PR-B.0 artifacts (plan §7).

PR-B.0 keeps the block minimal but honest: a schema version, the PR-B stage
marker, the deterministic ``pr_b_code_hash`` (so outer and inner can
cross-check that the same inspector bytes ran), and a best-effort
``pr_a_spec_version`` pointer to the protocol doc. No inspection data is
included.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..tolerances import PR_B_STAGE, SCHEMA_VERSION, STUB_MARKER

# Repo-relative path to the protocol PR-A doc (plan §7 pr_a_spec_version).
_PR_A_SPEC_RELPATH = "docs/design/gate_p1_feasibility_inspection_protocol.md"


def _inspector_package_dir() -> Path:
    # report/ -> _gate_p1_inspector/
    return Path(__file__).resolve().parent.parent


def _repo_root() -> Path:
    # _gate_p1_inspector/ -> scripts/ -> repo root
    return _inspector_package_dir().parent.parent


def compute_pr_b_code_hash() -> str:
    """Deterministic SHA-256 over all .py files under the inspector package.

    Recipe (shared by outer and inner so they can cross-check): for each .py
    file in sorted POSIX-relative-path order, hash ``relpath\\0bytes\\0``.
    """
    pkg_dir = _inspector_package_dir()
    digest = hashlib.sha256()
    for path in sorted(pkg_dir.rglob("*.py")):
        rel = path.relative_to(pkg_dir).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _pr_a_spec_version() -> dict[str, Any]:
    spec_path = _repo_root() / _PR_A_SPEC_RELPATH
    sha256: str | None = None
    if spec_path.exists():
        sha256 = hashlib.sha256(spec_path.read_bytes()).hexdigest()
    return {
        "path": _PR_A_SPEC_RELPATH,
        "sha256": sha256,
        "amendment": "amendment_1",
    }


def common_metadata_block() -> dict[str, Any]:
    """Return the common metadata block for every PR-B.0 JSON artifact."""
    return {
        "schema_version": SCHEMA_VERSION,
        "pr_b_stage": PR_B_STAGE,
        "stub_marker": STUB_MARKER,
        "pr_a_spec_version": _pr_a_spec_version(),
        "pr_b_code_hash": compute_pr_b_code_hash(),
    }
