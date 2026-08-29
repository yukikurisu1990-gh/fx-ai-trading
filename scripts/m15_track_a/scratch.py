"""Q8 — the one research-scratch write root for Track A.

Every byte Track A writes goes beneath **one** root, named here as a module
constant with no caller-supplied directory component.  That constraint is not
tidiness: §9 of the gate document records that its own OUT ruling on
reserved-filename impersonation is honest *only* under "a **module constant
with no caller-supplied directory component**", because with a constant root
the researcher is not the adversary, and without one the Win32 trailing-dot
family becomes a correctness surface rather than merely an attack surface.

Containment is decided by :mod:`scripts.m15_gate3a.path_authority`, the
repository's single authority for path aliasing — the extended-UNC prefix, the
Win32 trailing-dot/space class, NTFS stream suffixes, ``..`` traversal and the
volume-GUID namespace are all closed there and are not re-implemented.

Two things this module adds that the gate-3a guards do not cover
----------------------------------------------------------------

1. ``artifacts/m15_gate3a/`` is **not** in ``guards._PROTECTED_PREFIXES`` — the
   open referral **NR-A** — so ``guards.refuse_real_path`` permits exactly the
   write §8.11.9 item 6 forbids.  This module protects it explicitly rather
   than relying on a guard that does not reach it.
2. Containment here is **positive**: a path is admissible only if it is *inside*
   the scratch root.  The gate-3a guard is negative — it refuses named
   protected roots and permits everything else — which is the right shape for a
   writer with many legitimate destinations and the wrong shape for one with
   exactly one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

from scripts.m15_gate3a.path_authority import PathAuthorityError, is_within, resolve_candidate

#: The single Track A scratch root, relative to the repository root.  A module
#: constant: no caller supplies it, no environment variable overrides it, and no
#: function takes it as an argument.
SCRATCH_ROOT_RELATIVE: Final[str] = "artifacts/track_a_scratch"

#: Roots Track A may never write into.  The first four are
#: ``guards._PROTECTED_PREFIXES``; ``artifacts/m15_gate3a`` is added here because
#: NR-A leaves it out of that tuple while §8.11.9 item 6 forbids the write.
FORBIDDEN_WRITE_PREFIXES: Final[tuple[str, ...]] = (
    "artifacts/ml_step4/365d_ba_v1",
    "artifacts/gate_p1_pr_b/firstrun_365d_ba",
    "artifacts/gate_p1_pr_b/firstrun_730d_ba",
    "artifacts/gate_p1_pr_b/firstrun_3650d_ba",
    "artifacts/m15_gate3a",
    "artifacts/oanda_archive_2026-05-31",
    "data",
    "models",
    "docs",
    "src",
    "scripts",
    "tests",
)

#: Canonical filenames of committed artifacts.  §8.12.13 G-9: no Track A file
#: may bear one, anywhere — the root constraint alone does not stop a Track A
#: file being mistaken for evidence by its name.
RESERVED_ARTIFACT_FILENAMES: Final[frozenset[str]] = frozenset(
    {
        "scrub_report.json",
        "no_overlap_proof.json",
        "design_m15_inventory.json",
        "design_m15_derivation_manifest.json",
        "forward_epoch_inventory.json",
        "forward_epoch_adoption_manifest.json",
        "effective_n_estimator_spec.json",
        "cost_table_plan_or_metadata.json",
        "candles_manifest.json",
        "raw_inventory_365d_BA.json",
    }
)


class ScratchRootError(RuntimeError):
    """Raised when a Track A write is outside the scratch root or is otherwise refused."""


def repo_root() -> Path:
    """The repository root, derived from this file's location."""
    return Path(__file__).resolve().parents[2]


def scratch_root() -> Path:
    """The absolute Track A scratch root.  Not created here."""
    return repo_root() / SCRATCH_ROOT_RELATIVE


def _forbidden_roots() -> tuple[tuple[Path, str], ...]:
    root = repo_root()
    return tuple((root / prefix, prefix) for prefix in FORBIDDEN_WRITE_PREFIXES)


def assert_writable(path: Any) -> Path:
    """Return the resolved path if Track A may write it; otherwise raise.

    Three independent checks, all fail-closed, in the order that makes the
    error most informative:

    1. the path resolves under the path authority (which refuses relative
       spellings, stream suffixes, the Win32 normalisable-component class and
       the non-drive namespace outright);
    2. it is **inside** the scratch root — a positive containment test;
    3. its filename is not a committed artifact's canonical name.

    Check 2 makes check 3 redundant for a well-behaved caller.  It is kept
    because §9's honesty condition for the reserved-filename OUT ruling depends
    on the root being constant, and a defence that rests on one condition is
    weaker than one that rests on two.
    """
    try:
        candidate = resolve_candidate(path)
    except PathAuthorityError as exc:
        raise ScratchRootError(f"Track A write refused: {exc}") from exc

    root = scratch_root()
    if not is_within(candidate, root):
        for forbidden, label in _forbidden_roots():
            if is_within(candidate, forbidden):
                raise ScratchRootError(
                    f"Track A write refused: {candidate} is inside the protected root "
                    f"{label!r}. Track A writes only beneath {SCRATCH_ROOT_RELATIVE}."
                )
        raise ScratchRootError(
            f"Track A write refused: {candidate} is outside the scratch root "
            f"{SCRATCH_ROOT_RELATIVE}. Every Track A output goes beneath it, and nothing "
            "goes anywhere else."
        )

    name = candidate.name
    if name in RESERVED_ARTIFACT_FILENAMES:
        raise ScratchRootError(
            f"Track A write refused: {name!r} is the canonical filename of a committed "
            "artifact. A Track A output may not bear one, anywhere — a file that looks "
            "like evidence can be cited as evidence (§8.12.13 G-9)."
        )
    return candidate


def is_writable(path: Any) -> bool:
    """Predicate form of :func:`assert_writable`, for reporting rather than enforcement."""
    try:
        assert_writable(path)
    except ScratchRootError:
        return False
    return True


__all__ = [
    "FORBIDDEN_WRITE_PREFIXES",
    "RESERVED_ARTIFACT_FILENAMES",
    "SCRATCH_ROOT_RELATIVE",
    "ScratchRootError",
    "assert_writable",
    "is_writable",
    "repo_root",
    "scratch_root",
]
