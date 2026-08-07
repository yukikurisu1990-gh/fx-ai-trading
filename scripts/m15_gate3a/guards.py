"""Refusal guards — fail closed on any real-data / train / evaluate / execute /
forward-adopt / model-binary / forbidden-status request.

This gate-5 machinery is synthetic-only. Every entry point that could be misused
to touch production data or claim an unauthorised status routes through these
guards.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Final

from scripts.m15_gate3a.path_authority import PathAuthorityError, assert_outside
from scripts.ml_step4.evidence import repo_root

# Real ML Step 4 archive / evidence root — off-limits for computation here.
_PROTECTED_PREFIXES: Final[tuple[str, ...]] = (
    "artifacts/ml_step4/365d_ba_v1",
    "artifacts/gate_p1_pr_b/firstrun_365d_ba",
)

# Statuses this gate is forbidden to assert (may appear only in prohibition lists).
# R-4: kept in step with the playbook §10 list, which additionally names
# READY_FOR_LIVE, ROBUST and DEPLOYABLE.
FORBIDDEN_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "PASS",
        "Tier 1",
        "FORMALLY_VERIFIED",
        "PRODUCTION_READY",
        "READY_FOR_LIVE",
        "M15_AUTHORISED",
        "H1_AUTHORISED",
        "H2_STARTED",
        "PHASE_C2_STARTED",
        "NEW_EPOCH_ADOPTED",
        "BYTE_ADMISSIBLE",
        "MEETS",
        "ROBUST",
        "DEPLOYABLE",
    }
)

_FORBIDDEN_OPERATIONS: Final[frozenset[str]] = frozenset(
    {
        "read_real_data",
        "derive_real_m15",
        "compute_real_checksums",
        "compute_real_spreads",
        "compute_labels_real",
        "train",
        "validate",
        "evaluate_validation",
        "evaluate_holdout",
        "execute",
        "write_model_binary",
        "adopt_forward_epoch",
    }
)


class RealDataRefusedError(RuntimeError):
    """Raised when a synthetic-only capability is asked to touch real data/ops."""


def assert_synthetic_only(mode: str) -> None:
    """Only 'synthetic' / 'fixture' modes are permitted."""
    if mode not in ("synthetic", "fixture"):
        raise RealDataRefusedError(
            f"mode {mode!r} refused: gate-5 machinery is synthetic/fixture only"
        )


def refuse_real_path(path: Any) -> None:
    """Fail closed if a path points at protected real archive / evidence trees.

    BL-3: containment is decided by :mod:`scripts.m15_gate3a.path_authority`,
    the single authority for Windows path aliasing. The previous inline check
    matched the extended-UNC prefix case-sensitively and gave up (allowing)
    after a fixed 64-level ancestor walk; both routes are closed there.
    """
    root = repo_root()
    roots = tuple((root / prefix) for prefix in _PROTECTED_PREFIXES)
    try:
        assert_outside(path, roots, _PROTECTED_PREFIXES)
    except PathAuthorityError as exc:
        raise RealDataRefusedError(str(exc)) from exc


def assert_no_forbidden_operation(**flags: bool) -> None:
    """Fail closed if any forbidden operation flag is truthy."""
    for op, requested in flags.items():
        if op in _FORBIDDEN_OPERATIONS and requested:
            raise RealDataRefusedError(f"operation {op!r} refused in synthetic-only gate 5")
        if op not in _FORBIDDEN_OPERATIONS and requested:
            raise RealDataRefusedError(f"unknown operation flag {op!r} refused (fail closed)")


def normalise_status(status: str) -> str:
    """Fold a status label to its comparison key.

    O-1 normalised case and surrounding whitespace. R-4 additionally folds the
    separator variants that slipped past it — ``"production ready"``,
    ``"PRODUCTION-READY"`` and ``"Tier  1"`` all reduce to the same key as the
    canonical spelling.
    """
    key = unicodedata.normalize("NFKC", status).strip().upper()
    key = re.sub(r"[\s\-./]+", "_", key)
    return re.sub(r"_+", "_", key).strip("_")


_FORBIDDEN_STATUSES_NORMALISED: Final[frozenset[str]] = frozenset(
    normalise_status(s) for s in FORBIDDEN_STATUSES
)


def is_forbidden_status(value: Any) -> bool:
    """True iff *value* is a string naming a forbidden status (any spelling)."""
    return isinstance(value, str) and normalise_status(value) in _FORBIDDEN_STATUSES_NORMALISED


def assert_status_allowed(status: Any) -> None:
    """Refuse to assert a forbidden status label (case/separator-insensitive)."""
    if is_forbidden_status(status):
        raise RealDataRefusedError(f"forbidden status {status!r} may not be asserted here")
