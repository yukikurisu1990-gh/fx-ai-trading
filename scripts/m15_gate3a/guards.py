"""Refusal guards — fail closed on any real-data / train / evaluate / execute /
forward-adopt / model-binary / forbidden-status request.

This gate-5 machinery is synthetic-only. Every entry point that could be misused
to touch production data or claim an unauthorised status routes through these
guards.
"""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Final

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


def _strip_extended_prefix(path: str | Path) -> str:
    r"""R-3: drop a Windows extended-length prefix before comparison.

    ``Path.resolve()`` *keeps* ``\\?\``, so ``\\?\C:\...`` compared unequal to
    ``C:\...`` while naming the same directory.
    """
    text = str(path)
    for prefix in ("\\\\?\\UNC\\", "\\\\?\\"):
        if text.startswith(prefix):
            rest = text[len(prefix) :]
            return f"\\\\{rest}" if prefix.endswith("UNC\\") else rest
    return text


_MAX_ANCESTOR_WALK: Final[int] = 64


def _names_protected(resolved: Path, protected: Path) -> bool:
    """True iff *resolved* is, or sits under, *protected* — by name **or identity**.

    String comparison alone is not enough: UNC aliases (``\\localhost\\C$\\...``),
    NTFS junctions and 8.3 short names all resolve to a different string while
    naming the same directory. Filesystem identity closes those; the name test
    still covers targets that do not exist yet (the usual case for a write).
    Any OS error while probing fails closed.
    """
    if resolved == protected or protected in resolved.parents:
        return True
    try:
        if not protected.exists():  # pragma: no cover - protected tree is committed
            return False
        probe = resolved
        for _ in range(_MAX_ANCESTOR_WALK):
            if probe.exists() and os.path.samefile(probe, protected):
                return True
            if probe.parent == probe:
                return False
            probe = probe.parent
    except OSError:
        return True  # unresolvable / inaccessible -> fail closed
    return False  # pragma: no cover - walk exhausted


def refuse_real_path(path: str | Path) -> None:
    """Fail closed if a path points at protected real archive / evidence trees."""
    try:
        resolved = Path(_strip_extended_prefix(path)).resolve()
    except OSError as exc:  # pragma: no cover - defensive
        raise RealDataRefusedError(f"unresolvable path: {exc}") from exc
    root = repo_root()
    for prefix in _PROTECTED_PREFIXES:
        protected = (root / prefix).resolve()
        if _names_protected(resolved, protected):
            raise RealDataRefusedError(f"refused real/protected path: {prefix}")


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
