"""No-overlap proof utilities (metadata-only) against the consumed dead window.

Implements PR #430 T-7 + R-2b at the code level: design artifacts must end on or
before ``DESIGN_END``; forward artifacts must begin on or after
``FORWARD_FLOOR``; the dead window (the consumed M1 holdout) must be absent from
every role. Fail-closed; fixture-tested; reads no data.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from scripts.m15_gate3a.pair_authority import PAIRS_20, PairAuthorityError, canonical_pair
from scripts.m15_gate3a.timeutil import TimestampError, to_utc

DESIGN_START: Final[datetime] = datetime(2025, 4, 25, 0, 0, 0, tzinfo=UTC)
DESIGN_END: Final[datetime] = datetime(2026, 2, 28, 23, 59, 59, tzinfo=UTC)
DEAD_START: Final[datetime] = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)
DEAD_END: Final[datetime] = datetime(2026, 4, 24, 23, 59, 59, tzinfo=UTC)
FORWARD_FLOOR: Final[datetime] = datetime(2026, 4, 25, 0, 0, 0, tzinfo=UTC)

# B-2 / O-3: the constants stay at second granularity (moving them would
# conflict with the committed no_overlap_proof.json, which is why O-3's
# half-open rewrite was declined). The dead window is nonetheless treated as
# covering the whole of its final second, so a sub-second timestamp inside
# 2026-04-24T23:59:59.x is dead — strictly more conservative, and it changes no
# published boundary constant.
_DEAD_END_EXCLUSIVE: Final[datetime] = DEAD_END + timedelta(seconds=1)

# Ordering invariants of the frozen spans (defence against a constant edit).
# Explicit raises, not `assert`: bare asserts are stripped under `python -O`.
if not (DESIGN_START < DESIGN_END < DEAD_START <= DEAD_END < FORWARD_FLOOR):
    raise RuntimeError("frozen span constants are out of order")
if _DEAD_END_EXCLUSIVE != FORWARD_FLOOR:
    raise RuntimeError("dead-window end and the forward floor must be contiguous")


class NoOverlapError(RuntimeError):
    """Raised when an artifact role overlaps the dead window or violates bounds."""


def _parse(ts: Any) -> datetime:
    """Parse a timestamp; naive inputs FAIL CLOSED (never assumed UTC).

    BL-2: awareness is decided by :mod:`scripts.m15_gate3a.timeutil`, not by
    ``tzinfo is None``. A ``tzinfo`` whose ``utcoffset()`` returns ``None``
    leaves the value naive while ``tzinfo is None`` is ``False``, and the old
    ``astimezone(UTC)`` then reinterpreted it in the **host's** zone — which
    made this dead-window verdict depend on where it was run.
    """
    try:
        return to_utc(ts)
    except TimestampError as exc:
        raise NoOverlapError(str(exc)) from exc


def _intersects_dead_window(ts_min: datetime, ts_max: datetime) -> bool:
    """True iff [ts_min, ts_max] touches the dead window, final second included."""
    return not (ts_max < DEAD_START or ts_min >= _DEAD_END_EXCLUSIVE)


def _assert_ordered(lo: datetime, hi: datetime, *, what: str) -> None:
    """B-2: a reversed span must never reach the dead-window predicate.

    ``_intersects_dead_window`` short-circuits on ``ts_min > DEAD_END``, so an
    inverted pair could be certified clean while its real span sat inside the
    dead window. Every bound-checker now rejects the inversion first.
    """
    if hi < lo:
        raise NoOverlapError(
            f"{what}: ts_max {hi.isoformat()} < ts_min {lo.isoformat()} (reversed span)"
        )


def assert_design_bounds(ts_min: Any, ts_max: Any) -> None:
    """Design artifact must sit within [DESIGN_START, DESIGN_END] and miss dead window."""
    lo, hi = _parse(ts_min), _parse(ts_max)
    _assert_ordered(lo, hi, what="design")
    if hi > DESIGN_END:
        raise NoOverlapError(
            f"design ts_max {hi.isoformat()} > DESIGN_END {DESIGN_END.isoformat()}"
        )
    if lo < DESIGN_START:
        raise NoOverlapError(
            f"design ts_min {lo.isoformat()} < DESIGN_START {DESIGN_START.isoformat()}"
        )
    if _intersects_dead_window(lo, hi):
        raise NoOverlapError("design artifact intersects the dead window")


def assert_forward_bounds(ts_min: Any, ts_max: Any) -> None:
    """Forward artifact must begin >= FORWARD_FLOOR and miss the dead window."""
    lo, hi = _parse(ts_min), _parse(ts_max)
    _assert_ordered(lo, hi, what="forward")
    if lo < FORWARD_FLOOR:
        raise NoOverlapError(
            f"forward ts_min {lo.isoformat()} < FORWARD_FLOOR {FORWARD_FLOOR.isoformat()}"
        )
    if _intersects_dead_window(lo, hi):
        raise NoOverlapError("forward artifact intersects the dead window")


def assert_no_dead_window(ts_min: Any, ts_max: Any, *, role: str) -> None:
    """Any role's span must not intersect the dead window (fail-closed)."""
    lo, hi = _parse(ts_min), _parse(ts_max)
    _assert_ordered(lo, hi, what=role)
    if _intersects_dead_window(lo, hi):
        raise NoOverlapError(
            f"{role}: span intersects dead window {DEAD_START.date()}..{DEAD_END.date()}"
        )


_SHA256_HEX_LENGTH: Final[int] = 64


def _materialise(files: Any, *, role: str) -> tuple[Any, ...]:
    """Return the evidence as a tuple, or refuse if it is not re-scannable.

    BL-1: ``Sequence`` is an ABC — nothing forces ``__len__`` to agree with
    iteration. The previous guard trusted ``len(files)`` for ``expected_count``
    and then counted the loop separately, so a container reporting ``20`` while
    yielding nothing produced ``files_checked=0`` **and** the T-7 proof token.
    Both passes and indexed access must now agree before anything is checked.
    """
    if isinstance(files, (str, bytes, bytearray)) or not isinstance(files, Sequence):
        raise NoOverlapError(
            f"{role}: files must be a concrete sequence of file records, got {type(files).__name__}"
        )
    try:
        declared = len(files)
        first = tuple(files)
        second = tuple(files)
    except (TypeError, ValueError) as exc:
        raise NoOverlapError(f"{role}: evidence could not be re-scanned: {exc}") from exc
    if len(first) != declared or len(second) != declared:
        raise NoOverlapError(
            f"{role}: __len__ reports {declared} but iteration yields "
            f"{len(first)}/{len(second)} records (evidence is not self-consistent)"
        )
    for index, (a, b) in enumerate(zip(first, second, strict=True)):
        if a is not b and a != b:
            raise NoOverlapError(f"{role}: iteration is not stable at index {index}")
        try:
            indexed = files[index]
        except (IndexError, KeyError, TypeError) as exc:
            raise NoOverlapError(f"{role}: indexed access failed at {index}: {exc}") from exc
        if indexed is not a and indexed != a:
            raise NoOverlapError(f"{role}: indexed access disagrees with iteration at {index}")
    return first


def _roster_report(records: tuple[Any, ...], *, role: str) -> dict:
    """Bind the evidence to the canonical PAIRS_20 roster; refuse anything short of it.

    BL-1: the proof used to say nothing about *which* files it saw, so twenty
    copies of one record satisfied a twenty-file inventory. Every record must
    name a pair in the frozen universe, alias spellings collapse to the same
    canonical name (so ``eur/usd`` duplicates ``EUR_USD``), and the canonical
    roster must equal PAIRS_20 exactly — no missing, duplicate or unknown pair.
    """
    seen: dict[str, int] = {}
    duplicate: list[str] = []
    unknown: list[Any] = []
    filenames: dict[str, int] = {}
    digests: dict[str, int] = {}

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise NoOverlapError(
                f"{role}: file record must be a mapping, got {type(record).__name__}"
            )
        try:
            pair = canonical_pair(record.get("pair"))
        except PairAuthorityError:
            unknown.append(record.get("pair"))
            continue
        if pair in seen:
            duplicate.append(pair)
        else:
            seen[pair] = index

        filename = record.get("filename")
        if filename is not None:
            if not isinstance(filename, str) or not filename.strip():
                raise NoOverlapError(f"{role}: file record {index} has a non-string filename")
            if filename in filenames:
                raise NoOverlapError(
                    f"{role}: filename {filename!r} appears at records "
                    f"{filenames[filename]} and {index} (duplicate evidence)"
                )
            filenames[filename] = index

        digest = record.get("sha256")
        if digest is not None:
            if (
                not isinstance(digest, str)
                or len(digest) != _SHA256_HEX_LENGTH
                or any(c not in "0123456789abcdefABCDEF" for c in digest)
            ):
                raise NoOverlapError(f"{role}: file record {index} has a malformed sha256")
            key = digest.lower()
            if key in digests:
                raise NoOverlapError(
                    f"{role}: sha256 {key} appears at records {digests[key]} and "
                    f"{index} (duplicate evidence)"
                )
            digests[key] = index

    missing = [p for p in PAIRS_20 if p not in seen]
    report = {
        "expected_pairs": list(PAIRS_20),
        "expected_pair_count": len(PAIRS_20),
        "actual_pairs": [p for p in PAIRS_20 if p in seen],
        "actual_record_count": len(records),
        "missing_pairs": missing,
        "duplicate_pairs": sorted(set(duplicate)),
        "unknown_pairs": [repr(u) for u in unknown],
    }
    if missing or duplicate or unknown:
        raise NoOverlapError(
            f"{role}: roster does not match PAIRS_20 — "
            f"expected {len(PAIRS_20)}, got {len(records)} records; "
            f"missing={report['missing_pairs']}, "
            f"duplicate={report['duplicate_pairs']}, "
            f"unknown={report['unknown_pairs']}"
        )
    return report


def assert_per_file_bounds(
    files: Sequence[Any], *, role: str, expected_count: int | None = None
) -> dict:
    """Per-file ts-bound assertions for a role's inventory (design|forward).

    The returned ``PROVEN_NO_DEAD_WINDOW_OVERLAP`` token is a claim about the
    whole 20-pair inventory, so it is only ever produced when the evidence is
    re-scannable, bound to the canonical roster, and every record's span clears
    the dead window. ``expected_count`` remains a caller-supplied cross-check —
    on its own it can no longer produce the token.
    """
    if role not in ("design", "forward"):
        raise NoOverlapError(f"unknown role {role!r}")
    records = _materialise(files, role=role)
    if not records:
        raise NoOverlapError(f"{role}: empty file list")
    if expected_count is not None and len(records) != expected_count:
        raise NoOverlapError(f"{role}: expected {expected_count} files, got {len(records)}")
    report = _roster_report(records, role=role)

    checked = 0
    for record in records:
        tmin = record.get("ts_min_utc")
        tmax = record.get("ts_max_utc")
        if not tmin or not tmax:
            raise NoOverlapError(f"{role}: file missing ts bounds")
        if role == "design":
            assert_design_bounds(tmin, tmax)
        else:
            assert_forward_bounds(tmin, tmax)
        checked += 1
    if checked != len(records):  # pragma: no cover - defensive
        raise NoOverlapError(f"{role}: checked {checked} of {len(records)} records")
    return {
        "role": role,
        "files_checked": checked,
        **report,
        "result": "PROVEN_NO_DEAD_WINDOW_OVERLAP",
    }
