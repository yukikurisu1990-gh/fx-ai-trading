"""Artifact-path planning for the ML uplift harness (no real writes here).

Plans a deterministic report manifest under a safe output root. A safe root is
either external (outside the repo working tree, e.g. a test tmp dir) or an
explicitly synthetic/example location. Real experiment roots under the repo's
``artifacts/`` (that are not clearly synthetic) and any raw-data path are
rejected. Path traversal outside the chosen root is rejected.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .contracts import HarnessContractError

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SYNTHETIC_MARK_SEGMENTS = ("synthetic", "tests", "tmp", "example", "examples")

# Directory-name segments matched EXACTLY (so e.g. Windows "AppData" is not a
# false positive for "data"). Raw-data / archive locations.
_FORBIDDEN_NAME_SEGMENTS = (
    "data",
    "oanda_archive",
    "candles",
    "firstrun_365d_ba",
    "firstrun_730d_ba",
    "firstrun_3650d_ba",
)
# Raw dataset file suffixes matched by extension.
_FORBIDDEN_SUFFIXES = (".jsonl", ".parquet", ".csv")


def _has_forbidden_segment(path: Path) -> str | None:
    parts_lower = {p.lower() for p in path.parts}
    hit = parts_lower.intersection(_FORBIDDEN_NAME_SEGMENTS)
    if hit:
        return sorted(hit)[0]
    for part in path.parts:
        lowered = part.lower()
        for suffix in _FORBIDDEN_SUFFIXES:
            if lowered.endswith(suffix):
                return suffix
    return None


def validate_artifact_root(artifact_root: str | os.PathLike[str]) -> Path:
    """Return the resolved root if safe, else raise HarnessContractError."""
    root = Path(os.path.normpath(os.path.abspath(os.fspath(artifact_root))))

    forbidden = _has_forbidden_segment(root)
    if forbidden is not None:
        raise HarnessContractError(
            f"artifact_root '{root}' contains a forbidden path segment "
            f"('{forbidden}'): harness must not write near real data / archives."
        )

    try:
        rel = root.relative_to(_REPO_ROOT)
    except ValueError:
        return root  # external (temp/test) root is safe

    # In-repo: allow only clearly synthetic/example locations.
    parts_lower = {p.lower() for p in rel.parts}
    if parts_lower & set(_SYNTHETIC_MARK_SEGMENTS):
        return root
    raise HarnessContractError(
        f"in-repo artifact_root '{rel.as_posix()}' is not marked synthetic/test; "
        "real experiment artifacts are not authorised in this PR."
    )


def resolve_experiment_dir(artifact_root: str | os.PathLike[str], experiment_id: str) -> Path:
    """Return the absolute experiment output dir for writing (validated root)."""
    return validate_artifact_root(artifact_root) / experiment_id


def _machine_independent_dir(experiment_dir: Path) -> str:
    """Return a report-safe (no absolute / personal-machine) dir reference."""
    try:
        return experiment_dir.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        # External (temp/test) root: keep only the root basename + experiment id
        # so no personal-machine path prefix is recorded.
        return f"{experiment_dir.parent.name}/{experiment_dir.name}"


def plan_artifact_manifest(
    artifact_root: str | os.PathLike[str],
    experiment_id: str,
    report_files: list[str],
) -> dict[str, Any]:
    """Deterministic, machine-independent report manifest (no files written).

    The manifest records NO absolute / personal-machine path — only a repo-
    relative or basename-scoped reference — so it is safe to commit.
    """
    experiment_dir = resolve_experiment_dir(artifact_root, experiment_id)
    planned = []
    for name in sorted(report_files):
        target = (experiment_dir / name).resolve()
        if experiment_dir.resolve() not in target.parents and target != experiment_dir.resolve():
            raise HarnessContractError(f"planned report file '{name}' escapes the experiment dir")
        if target.suffix not in (".json", ".md"):
            raise HarnessContractError(f"planned report file '{name}' must be .json or .md")
        planned.append(target.name)
    return {
        "artifact_root_basename": experiment_dir.parent.name,
        "experiment_dir_reference": _machine_independent_dir(experiment_dir),
        "planned_report_files": planned,
        "write_performed": False,
    }
