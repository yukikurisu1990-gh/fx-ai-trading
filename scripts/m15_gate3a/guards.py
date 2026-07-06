"""Refusal guards — fail closed on any real-data / train / evaluate / execute /
forward-adopt / model-binary / forbidden-status request.

This gate-5 machinery is synthetic-only. Every entry point that could be misused
to touch production data or claim an unauthorised status routes through these
guards.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

from scripts.ml_step4.evidence import repo_root

# Real ML Step 4 archive / evidence root — off-limits for computation here.
_PROTECTED_PREFIXES: Final[tuple[str, ...]] = (
    "artifacts/ml_step4/365d_ba_v1",
    "artifacts/gate_p1_pr_b/firstrun_365d_ba",
)

# Statuses this gate is forbidden to assert (may appear only in prohibition lists).
FORBIDDEN_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "PASS",
        "Tier 1",
        "FORMALLY_VERIFIED",
        "PRODUCTION_READY",
        "M15_AUTHORISED",
        "H1_AUTHORISED",
        "H2_STARTED",
        "PHASE_C2_STARTED",
        "NEW_EPOCH_ADOPTED",
        "BYTE_ADMISSIBLE",
        "MEETS",
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


def refuse_real_path(path: str | Path) -> None:
    """Fail closed if a path points at protected real archive / evidence trees."""
    try:
        resolved = Path(path).resolve()
    except OSError as exc:  # pragma: no cover - defensive
        raise RealDataRefusedError(f"unresolvable path: {exc}") from exc
    root = repo_root()
    for prefix in _PROTECTED_PREFIXES:
        protected = (root / prefix).resolve()
        if resolved == protected or protected in resolved.parents:
            raise RealDataRefusedError(f"refused real/protected path: {prefix}")


def assert_no_forbidden_operation(**flags: bool) -> None:
    """Fail closed if any forbidden operation flag is truthy."""
    for op, requested in flags.items():
        if op in _FORBIDDEN_OPERATIONS and requested:
            raise RealDataRefusedError(f"operation {op!r} refused in synthetic-only gate 5")
        if op not in _FORBIDDEN_OPERATIONS and requested:
            raise RealDataRefusedError(f"unknown operation flag {op!r} refused (fail closed)")


def assert_status_allowed(status: Any) -> None:
    """Refuse to assert a forbidden status label."""
    if isinstance(status, str) and status in FORBIDDEN_STATUSES:
        raise RealDataRefusedError(f"forbidden status {status!r} may not be asserted here")
