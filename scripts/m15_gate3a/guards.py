"""Refusal guards — fail closed on any real-data / train / evaluate / execute /
forward-adopt / model-binary / forbidden-status request.

This gate-5 machinery is synthetic-only.

**What this module actually guarantees (RF-15).** The previous docstring claimed
that every point of entry capable of touching production data or claiming an
unauthorised status routed through these guards. That was false and is not
restated: three of the four public guards
(:func:`assert_synthetic_only`, :func:`assert_no_forbidden_operation`,
:func:`assert_status_allowed`) have **no non-test caller anywhere in the
repository**, so they constrain nothing that is not explicitly handed to them.
Only these routings exist today, and they are the whole of the claim:

* :func:`refuse_real_path` is called by
  :func:`scripts.m15_gate3a.artifacts.write_metadata_artifact` on both the
  output directory and the joined target, before either is created;
* :func:`is_forbidden_status` is called by that module's scrubber on artifact
  keys, values and list items.

Each guard is individually fail-closed on the input it is given. Nothing here
asserts that a caller exists, that every write is routed, or that the package is
therefore contained: containment of an *unrouted* caller is not a property this
module has, and must not be cited as one.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Final

from scripts.m15_gate3a.path_authority import PathAuthorityError, assert_outside
from scripts.ml_step4.evidence import repo_root

# Trees this synthetic-only gate may never name as a computation or write target,
# relative to the repository root.
#
# B-5 / §12.18 / D-7: the set covered two directories, so `data/` (the real M1
# candle store and the default `data_root` of `Real365dBaProvider`), `models/`
# (20 model binaries), `docs/` (the governance tree itself — `refuse_real_path`
# was letting `write_metadata_artifact` target it) and the 730d/3650d PR-B.1
# evidence trees were all ALLOWED.
#
# `artifacts/m15_gate3a` is deliberately **absent**. D-7 rules that directory is
# populated through a human-reviewed PR diff and that the continuation's outputs
# go to a *separate output directory*; it also records the explicit trap of
# closing B-5 by adding the prefix here while §5 still names that directory as a
# write target. It becomes safe to add only once the separate output directory
# is adopted — which is not this change.
_PROTECTED_PREFIXES: Final[tuple[str, ...]] = (
    "artifacts/ml_step4/365d_ba_v1",
    "artifacts/gate_p1_pr_b/firstrun_365d_ba",
    "artifacts/gate_p1_pr_b/firstrun_730d_ba",
    "artifacts/gate_p1_pr_b/firstrun_3650d_ba",
    "data",
    "models",
    "docs",
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
        # RF-12: playbook §10's near-synonym guidance — "validated", "proven
        # profitable", "ready to deploy", "green-light", "cleared for
        # live/paper" — had no representation at all. Each spelling of the
        # slashed pair is listed, because the fold turns `/` into `_` and the
        # comparison is over the whole string.
        "VALIDATED",
        "PROVEN_PROFITABLE",
        "READY_TO_DEPLOY",
        "GREEN_LIGHT",
        "CLEARED_FOR_LIVE",
        "CLEARED_FOR_PAPER",
        "CLEARED_FOR_LIVE_PAPER",
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

    §12.18: the verdict is **cwd-independent**. It used to depend on the process
    working directory, because the protected roots are absolute while a relative
    candidate resolved against wherever the process happened to be — the same
    logical path was ALLOWED from one directory and REFUSED from another.
    ``resolve_candidate`` now refuses relative spellings outright (see its
    docstring for why refusal rather than repo-root anchoring), so the verdict
    for any path this accepts is a function of the path alone.
    """
    root = repo_root()
    roots = tuple((root / prefix) for prefix in _PROTECTED_PREFIXES)
    try:
        assert_outside(path, roots, _PROTECTED_PREFIXES)
    except PathAuthorityError as exc:
        raise RealDataRefusedError(str(exc)) from exc


def assert_no_forbidden_operation(**flags: bool) -> None:
    """Fail closed on an unknown flag name, a non-``bool`` value, or a set flag.

    RF-14 found three fail-open routes, all of them in the *disarmed* direction,
    which is the dangerous one for a guard that is supposed to prove a negative:

    * an **unknown flag name** was refused only when its value was truthy, so
      the likely caller typo ``training=False`` (for ``train``) passed silently
      and the operation it was meant to forbid went unguarded. The name is now
      checked before the value, so a misspelt flag can never look satisfied;
    * a **call with no flags at all** asserted nothing while reading exactly
      like an assertion that something had been checked. It is now an error —
      this guard exists to refuse a named operation, and a call naming none has
      no meaning to fail closed *on*;
    * a **non-``bool`` value** made truthiness the whole test, so ``train=0``
      and ``train=""`` disarmed a real flag as effectively as ``train=False``
      while ``train="no"`` refused. The value must now be an actual ``bool``.
    """
    if not flags:
        raise RealDataRefusedError(
            "assert_no_forbidden_operation() called with no flags refused: a call naming "
            "no operation asserts nothing"
        )
    for op, requested in flags.items():
        if op not in _FORBIDDEN_OPERATIONS:
            raise RealDataRefusedError(f"unknown operation flag {op!r} refused (fail closed)")
        if not isinstance(requested, bool):
            raise RealDataRefusedError(
                f"operation flag {op!r} must be a bool, got {type(requested).__name__}; "
                "truthiness is not a disposition"
            )
        if requested:
            raise RealDataRefusedError(f"operation {op!r} refused in synthetic-only gate 5")


def normalise_status(status: str) -> str:
    """Fold a status label to its separator-normalised comparison key.

    O-1 normalised case and surrounding whitespace. R-4 additionally folds the
    separator variants that slipped past it — ``"production ready"``,
    ``"PRODUCTION-READY"`` and ``"Tier  1"`` all reduce to the same key as the
    canonical spelling.
    """
    key = unicodedata.normalize("NFKC", status).strip().upper()
    key = re.sub(r"[\s\-./]+", "_", key)
    return re.sub(r"_+", "_", key).strip("_")


def _comparison_key(status: str) -> str:
    """Fold a status further, to its separators-removed comparison key.

    RF-12: playbook §10 declares that "casing/whitespace variants ... are
    treated identically", but :func:`normalise_status` maps a separator to
    ``_`` rather than removing it, so the *run-together* spellings ``tier1``,
    ``productionready`` and ``BYTEADMISSIBLE`` compared unequal to the
    canonical keys and passed. Removing separators entirely closes that class.

    The comparison stays **exact over the whole string** — this is not
    substring scanning, which is the scrubber's job, not this predicate's. So
    ``PASSED``, ``COMPASS``, ``BYPASS``, ``ROBUSTNESS``,
    ``MEETS_PREREGISTERED_CRITERIA`` and ``NOT_PRODUCTION_READY`` remain clean:
    each folds to a whole-string key that no forbidden label folds to.
    """
    return normalise_status(status).replace("_", "")


# Separators removed, so this is the weaker key of the two and subsumes the
# separator-normalised set: `k in NORMALISED` implies `_comparison_key(k)` is
# here. Only this one is tested, to avoid a second condition that can never
# fire independently.
_FORBIDDEN_STATUS_KEYS: Final[frozenset[str]] = frozenset(
    _comparison_key(s) for s in FORBIDDEN_STATUSES
)


def is_forbidden_status(value: Any) -> bool:
    """True iff *value* is a string naming a forbidden status (any spelling).

    Non-strings are **not** forbidden statuses and report ``False``; this is a
    predicate over labels, and the scrubber that calls it inspects arbitrary
    JSON values. Callers that must *refuse* rather than classify use
    :func:`assert_status_allowed`, which fails closed on the type (RF-13).
    """
    return isinstance(value, str) and _comparison_key(value) in _FORBIDDEN_STATUS_KEYS


def assert_status_allowed(status: Any) -> None:
    """Refuse to assert a forbidden status label (case/separator-insensitive).

    RF-13: this delegated straight to :func:`is_forbidden_status`, which reports
    ``False`` for anything that is not a ``str`` — so ``b"PASS"``, ``["PASS"]``
    and ``None`` were all silently *allowed*. A guard whose job is to refuse
    cannot treat "I cannot read this" as "this is fine": a non-``str`` status is
    now refused on its type, before any label comparison.
    """
    if not isinstance(status, str):
        raise RealDataRefusedError(
            f"status must be a str to be checked, got {type(status).__name__}; refused unread"
        )
    if is_forbidden_status(status):
        raise RealDataRefusedError(f"forbidden status {status!r} may not be asserted here")
