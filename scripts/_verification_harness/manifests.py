"""Provenance manifest computation for V2-expanded.

Per amendment §A.0 / §A.4 / §A.5 (binding):

  * contract_hash — SHA-256 over the normalised contract dict (cells +
    comparators + row-set policy + thresholds + quantile family + loss
    + optimiser + seed + tolerances)
  * code_hash — SHA-256 over the sorted concatenation of the 20 formal
    harness source files
  * data_manifest_hash — SHA-256 over the source data manifest (per-pair
    M1 BA + signal source files with sizes + mtimes + content SHAs;
    pair universe; split boundaries)
  * environment_manifest — Python / lib versions + deterministic flags
    + CPU/GPU + seed
  * dependency_source_hashes — SHA-256 of every shared helper actually
    invoked by the formal path (transitive dependency provenance)
  * git_state_at_run_start — git status snapshot (HALT if uncommitted
    modifications detected)
  * size guard — HALT if any required committed file > 95 MB

Stage 1 provides the primitives; Stage 2/3 orchestration calls them.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


class ManifestError(RuntimeError):
    """Raised on manifest schema / hash mismatch / size-guard violation."""


# ---------------------------------------------------------------------------
# Formal 20-file harness topology (binding per amendment §A.4)
# ---------------------------------------------------------------------------

FORMAL_HARNESS_FILES: tuple[str, ...] = (
    "scripts/tabular_targeted_verification_v2_expanded.py",
    "scripts/_verification_harness/__init__.py",
    "scripts/_verification_harness/manifests.py",
    "scripts/_verification_harness/event_log.py",
    "scripts/_verification_harness/pnl_identity.py",
    "scripts/_verification_harness/row_set.py",
    "scripts/_verification_harness/sentinel_runner.py",
    "scripts/_verification_harness/reporting.py",
    "scripts/_verification_harness/contract_snapshots.py",
    "scripts/_verification_harness/forbidden_inputs.py",
    "scripts/_verification_harness/tolerances.py",
    "scripts/_verification_harness/sentinel_adapters/__init__.py",
    "scripts/_verification_harness/sentinel_adapters/_pinned_s_b_factory.py",
    "scripts/_verification_harness/sentinel_adapters/_pinned_s_e_factory.py",
    "scripts/_verification_harness/sentinel_adapters/s1_pr325.py",
    "scripts/_verification_harness/sentinel_adapters/s2_pr332.py",
    "scripts/_verification_harness/sentinel_adapters/s3_pr338.py",
    "scripts/_verification_harness/sentinel_adapters/s4_pr342.py",
    "scripts/_verification_harness/sentinel_adapters/s5_pr345.py",
    "scripts/_verification_harness/sentinel_adapters/s6_pr351.py",
)


# ---------------------------------------------------------------------------
# Hash primitives
# ---------------------------------------------------------------------------


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_of_dict(payload: dict[str, Any]) -> str:
    """Hash a normalised dict; uses sorted keys for determinism."""
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return _sha256_of_bytes(canonical.encode("utf-8"))


# ---------------------------------------------------------------------------
# contract_hash
# ---------------------------------------------------------------------------


def compute_contract_hash(contract_dict: dict[str, Any]) -> str:
    """SHA-256 over the normalised contract dict.

    The caller is responsible for assembling the contract dict per the
    schema specified in amendment §3.6 / §A.4 (cells / comparators /
    thresholds / tolerances / etc.).
    """
    return _sha256_of_dict(contract_dict)


# ---------------------------------------------------------------------------
# code_hash (over the 20 formal harness files; permits absent files at Stage 1)
# ---------------------------------------------------------------------------


@dataclass
class CodeHashResult:
    code_hash: str
    files_present: list[str]
    files_absent: list[str]
    per_file_sha256: dict[str, str]


def compute_code_hash(repo_root: Path = REPO_ROOT) -> CodeHashResult:
    """SHA-256 over sorted concatenation of the 20 formal harness source files.

    At Stage 1 some files do not yet exist (sentinel_runner / reporting /
    orchestrator / adapters); their absence is recorded so Stage 2/3 can
    detect drift.
    """
    per_file: dict[str, str] = {}
    present: list[str] = []
    absent: list[str] = []
    combined = hashlib.sha256()
    for rel in sorted(FORMAL_HARNESS_FILES):
        p = repo_root / rel
        if not p.is_file():
            absent.append(rel)
            per_file[rel] = ""
            combined.update(f"<ABSENT:{rel}>".encode())
            continue
        sha = _sha256_of_file(p)
        per_file[rel] = sha
        present.append(rel)
        combined.update(f"{rel}:{sha}".encode())
    return CodeHashResult(
        code_hash=combined.hexdigest(),
        files_present=present,
        files_absent=absent,
        per_file_sha256=per_file,
    )


# ---------------------------------------------------------------------------
# data_manifest_hash
# ---------------------------------------------------------------------------


@dataclass
class DataFileEntry:
    rel_path: str
    n_bytes: int
    mtime_ns: int
    content_sha256: str


def compute_data_manifest_hash(
    data_files: Iterable[Path],
    *,
    pair_universe: tuple[str, ...] | None = None,
    split_boundaries: dict[str, Any] | None = None,
    repo_root: Path = REPO_ROOT,
) -> tuple[str, dict[str, Any]]:
    """SHA-256 over the source-data manifest.

    Returns (data_manifest_hash, manifest_payload). The caller commits the
    manifest_payload to ``manifests/data_manifest_hash.json``.
    """
    entries: list[DataFileEntry] = []
    for p in sorted(data_files):
        if not p.is_file():
            continue
        rel = str(p.relative_to(repo_root)).replace("\\", "/")
        st = p.stat()
        entries.append(
            DataFileEntry(
                rel_path=rel,
                n_bytes=st.st_size,
                mtime_ns=st.st_mtime_ns,
                content_sha256=_sha256_of_file(p),
            )
        )
    payload = {
        "schema_version": "v2-expanded-1.0",
        "data_files": [
            {
                "rel_path": e.rel_path,
                "n_bytes": e.n_bytes,
                "mtime_ns": e.mtime_ns,
                "content_sha256": e.content_sha256,
            }
            for e in entries
        ],
        "pair_universe": list(pair_universe) if pair_universe else [],
        "split_boundaries": split_boundaries or {},
    }
    return _sha256_of_dict(payload), payload


# ---------------------------------------------------------------------------
# environment_manifest
# ---------------------------------------------------------------------------


def compute_environment_manifest(seed: int) -> dict[str, Any]:
    """Capture Python / lib versions + deterministic flags + CPU/GPU + seed."""
    versions: dict[str, str] = {}
    for mod_name in (
        "numpy",
        "pandas",
        "scipy",
        "lightgbm",
        "sklearn",
        "torch",
    ):
        try:
            mod = __import__(mod_name)
            versions[mod_name] = getattr(mod, "__version__", "unknown")
        except ImportError:
            versions[mod_name] = "not-installed"

    return {
        "schema_version": "v2-expanded-1.0",
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "lib_versions": versions,
        "deterministic_flags": {
            "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", "<unset>"),
            "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "<unset>"),
            "LIGHTGBM_NUM_THREADS": os.environ.get("LIGHTGBM_NUM_THREADS", "<unset>"),
            "CUBLAS_WORKSPACE_CONFIG": os.environ.get("CUBLAS_WORKSPACE_CONFIG", "<unset>"),
        },
        "seed": seed,
        "gpu_model": None,  # CPU-only verification by default
    }


def assert_environment_manifests_match(expected: dict[str, Any], observed: dict[str, Any]) -> None:
    """HALT on environment_manifest mismatch (default per §A.7 = HALT)."""
    keys_to_match = (
        "python_version",
        "python_implementation",
        "platform",
        "machine",
        "lib_versions",
        "deterministic_flags",
        "seed",
        "gpu_model",
    )
    for k in keys_to_match:
        if expected.get(k) != observed.get(k):
            raise ManifestError(
                f"environment_manifest mismatch on key {k!r}: "
                f"expected={expected.get(k)!r} observed={observed.get(k)!r}"
            )


# ---------------------------------------------------------------------------
# dependency_source_hashes (transitive dependency provenance per Stage 1 §4)
# ---------------------------------------------------------------------------


def compute_dependency_source_hashes(
    invoked_helpers: dict[str, Path],
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Hash every shared helper actually invoked by the formal path.

    ``invoked_helpers`` is a mapping ``helper_name -> path-to-source-file``
    that the harness records as it imports each helper. The result is
    committed to ``manifests/dependency_source_hashes.json``.

    Per Stage 1 binding: must include at minimum
      * _compute_realised_barrier_pnl
      * precompute_realised_pnl_per_row
      * split_70_15_15
      * _build_pair_runtime
    plus any additional shared helper invoked by foundation/sentinel paths.
    """
    entries: dict[str, dict[str, Any]] = {}
    for name, p in invoked_helpers.items():
        if not p.is_file():
            raise ManifestError(f"dependency source missing: {name!r} -> {p}")
        rel = str(p.relative_to(repo_root)).replace("\\", "/")
        entries[name] = {
            "source_path": rel,
            "content_sha256": _sha256_of_file(p),
            "n_bytes": p.stat().st_size,
        }
    return {
        "schema_version": "v2-expanded-1.0",
        "helpers": entries,
        "n_helpers": len(entries),
    }


MANDATORY_HELPER_NAMES: tuple[str, ...] = (
    "_compute_realised_barrier_pnl",
    "precompute_realised_pnl_per_row",
    "split_70_15_15",
    "_build_pair_runtime",
)


def assert_dependency_hashes_complete(
    dep_payload: dict[str, Any],
) -> None:
    """HALT if any mandatory shared helper is missing from the dependency hashes."""
    helpers = dep_payload.get("helpers", {})
    if not helpers:
        raise ManifestError("dependency_source_hashes is empty")
    missing = [n for n in MANDATORY_HELPER_NAMES if n not in helpers]
    if missing:
        raise ManifestError(f"dependency_source_hashes missing mandatory helpers: {missing!r}")


# ---------------------------------------------------------------------------
# git state at run start
# ---------------------------------------------------------------------------


def record_git_state_at_run_start(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Snapshot git HEAD + porcelain status; HALT if working tree dirty."""
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise ManifestError(f"git rev-parse HEAD failed: {e}") from e
    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=str(repo_root),
            stderr=subprocess.STDOUT,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise ManifestError(f"git status failed: {e}") from e

    # Modified-tracked-file detection: filter to lines that report tracked
    # changes (any non-empty first two columns where the first column isn't
    # '?' which would mean untracked).
    dirty_lines = []
    for line in status.splitlines():
        if not line:
            continue
        if line.startswith("??"):
            continue  # untracked file (environmental); does not count as dirty
        dirty_lines.append(line)

    return {
        "schema_version": "v2-expanded-1.0",
        "head_sha": head,
        "porcelain_full": status,
        "tracked_dirty_lines": dirty_lines,
        "tracked_clean": len(dirty_lines) == 0,
    }


def assert_git_state_clean(state: dict[str, Any]) -> None:
    if not state.get("tracked_clean"):
        raise ManifestError(
            f"working tree has uncommitted tracked changes; cannot start formal "
            f"run: {state.get('tracked_dirty_lines')!r}"
        )


# ---------------------------------------------------------------------------
# Size guard (per amendment §A.5; binding)
# ---------------------------------------------------------------------------


from .tolerances import ARTIFACT_SIZE_GUARD_BYTES  # noqa: E402


def assert_artifact_under_size_guard(path: Path) -> None:
    """HALT if any required committed artifact file > 95 MB."""
    if not path.is_file():
        return
    n = path.stat().st_size
    if n > ARTIFACT_SIZE_GUARD_BYTES:
        raise ManifestError(
            f"artifact size guard tripped: {path} is {n} bytes "
            f"(> {ARTIFACT_SIZE_GUARD_BYTES} bytes / 95 MB)"
        )


def check_artifact_tree_size(paths: Iterable[Path]) -> dict[str, Any]:
    """Run size guard over an iterable of artifact paths; collect violations.

    Returns a report; the orchestrator (Stage 3) consults the report and
    HALTs before PR creation if any violation is present.
    """
    violations: list[dict[str, Any]] = []
    sizes: list[dict[str, Any]] = []
    for p in paths:
        if not p.is_file():
            continue
        n = p.stat().st_size
        sizes.append({"path": str(p), "n_bytes": n})
        if n > ARTIFACT_SIZE_GUARD_BYTES:
            violations.append({"path": str(p), "n_bytes": n})
    return {
        "schema_version": "v2-expanded-1.0",
        "size_guard_bytes": ARTIFACT_SIZE_GUARD_BYTES,
        "n_files_inspected": len(sizes),
        "violations": violations,
        "all_under_guard": len(violations) == 0,
    }


# ---------------------------------------------------------------------------
# Persist manifests to JSON files
# ---------------------------------------------------------------------------


def write_manifest_json(payload: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
