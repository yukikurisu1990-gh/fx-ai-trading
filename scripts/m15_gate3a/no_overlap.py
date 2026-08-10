"""No-overlap **declaration** utilities (metadata-only) against the dead window.

Implements PR #430 T-7 + R-2b at the code level: design artifacts must end on or
before ``DESIGN_END``; forward artifacts must begin on or after
``FORWARD_FLOOR``; the dead window (the consumed M1 holdout) must be absent from
every role. Fail-closed; fixture-tested; reads no data.

**Scope boundary (audit B-2, contract §12.13 / D-11 token discipline).** Nothing
in this module opens a file, and nothing in it measures bytes. Every quantity it
checks was *declared by the caller*. Its maximal claim is therefore the
declaration-only token
:data:`DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL`, which asserts only that
the supplied inventory metadata is internally consistent with the frozen
boundary constants. It says nothing about any file's contents.

The byte-level vocabulary lives in :mod:`scripts.m15_gate3a.proof` and this
module deliberately has **no import edge to it**, so no byte-level token string
is reachable from here. Promotion — deriving a byte-level claim from
declaration-only evidence — is forbidden by D-11 and is prevented structurally,
not by comment: ``proof`` refuses a declaration record by type, and this module
cannot name a byte-level token at all.

The byte-reading producer/verifier packages that *can* discharge the byte-level
proof are a separate gate (contract §15.4); this module is the reader-free
contract enforcement, never a substitute for it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from scripts.m15_gate3a.pair_authority import PAIRS_20, PairAuthorityError, canonical_pair
from scripts.m15_gate3a.timeutil import TimestampError, format_utc_z, to_utc

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


# --- Token discipline (audit B-2; contract §11 "Token discipline", §12.13) ----
#
# The single token this module may emit. It names its own evidentiary basis in
# its own spelling, so a reader of an emitted artifact cannot mistake it for the
# byte-level proof playbook §5 requires. `proof.py` registers this string as
# declaration-only and asserts it is disjoint from the byte-level vocabulary.
DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL: Final[str] = (
    "DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL"
)

# Stated in the result itself, because B-2 found the old result honest about the
# five schema keys it skipped and silent about the far more important fact that
# its bounds were never measured.
DECLARATION_ONLY_EVIDENCE_BASIS: Final[str] = (
    "CALLER_DECLARED_METADATA_ONLY__NO_FILE_OPENED__NO_BYTE_MEASURED"
)


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


def is_dead_window_instant(ts: Any) -> bool:
    """True iff a single instant lies inside the dead window (final second included).

    Exposed so the coverage limb can reject an expected or certified M15 slot
    that sits inside the consumed M1 holdout without reaching into this module's
    private predicate or re-deriving the frozen constants.
    """
    instant = _parse(ts)
    return DEAD_START <= instant < _DEAD_END_EXCLUSIVE


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


def _assert_design_bounds_parsed(lo: datetime, hi: datetime) -> None:
    """Design bound checks over values that are **already** parsed (B-3).

    Split out so the certifying caller can bound-check and publish the *same*
    ``datetime`` objects. Each guard raises with a phrase unique to it, so a
    test can pin one epoch limb without regex alternation (audit B-7a).
    """
    _assert_ordered(lo, hi, what="design")
    if hi > DESIGN_END:
        raise NoOverlapError(
            f"design ts_max {hi.isoformat()} exceeds the frozen design-epoch ceiling "
            f"DESIGN_END {DESIGN_END.isoformat()}"
        )
    if lo < DESIGN_START:
        raise NoOverlapError(
            f"design ts_min {lo.isoformat()} precedes the frozen design-epoch floor "
            f"DESIGN_START {DESIGN_START.isoformat()}"
        )
    # DEFENCE IN DEPTH, and unreachable while the frozen constants hold.
    # `DEAD_START` is exactly one second after `DESIGN_END`, so any design span
    # touching the dead window has already tripped the ceiling limb above. The
    # internal audit proved this by mutation: nulling this limb *and* its
    # forward twin leaves the whole suite green, so **no test can name either
    # one**. It is retained deliberately — the import-time invariant is the only
    # thing making it unreachable, and a future constant edit that slipped past
    # that invariant would need this. It is documented rather than deleted, and
    # rather than left to look like coverage: the regex alternation the audit
    # removed (`"dead window|DESIGN_END"`) was passing *because* of the ceiling
    # limb while appearing to exercise this one.
    if _intersects_dead_window(lo, hi):  # pragma: no cover - unreachable while constants hold
        raise NoOverlapError("design artifact intersects the dead window")


def _assert_forward_bounds_parsed(lo: datetime, hi: datetime) -> None:
    """Forward bound checks over values that are **already** parsed (B-3, B-7a)."""
    _assert_ordered(lo, hi, what="forward")
    if lo < FORWARD_FLOOR:
        raise NoOverlapError(
            f"forward ts_min {lo.isoformat()} precedes the frozen forward-epoch floor "
            f"FORWARD_FLOOR {FORWARD_FLOOR.isoformat()}"
        )
    # Unreachable twin of the design limb above, for the mirror reason:
    # `_DEAD_END_EXCLUSIVE == FORWARD_FLOOR` (asserted at import), so a span with
    # `lo >= FORWARD_FLOOR` cannot intersect. Same rationale for retention.
    if _intersects_dead_window(lo, hi):  # pragma: no cover - unreachable while constants hold
        raise NoOverlapError("forward artifact intersects the dead window")


def assert_design_bounds(ts_min: Any, ts_max: Any) -> None:
    """Design artifact must sit within [DESIGN_START, DESIGN_END] and miss dead window."""
    _assert_design_bounds_parsed(_parse(ts_min), _parse(ts_max))


def assert_forward_bounds(ts_min: Any, ts_max: Any) -> None:
    """Forward artifact must begin >= FORWARD_FLOOR and miss the dead window."""
    _assert_forward_bounds_parsed(_parse(ts_min), _parse(ts_max))


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

    # Snapshot each record into a plain dict. A Mapping is free to answer
    # `.get()` differently on every call — the internal audit built one whose
    # `.get("pair")` cycled through PAIRS_20, so twenty references to a single
    # record satisfied the roster while `_materialise` saw `a is b` throughout.
    # Reading each record once, here, is what makes the roster pass and the
    # bounds pass see the same evidence.
    snapshot: list[dict] = []
    identities: dict[int, int] = {}
    for index, record in enumerate(first):
        if not isinstance(record, Mapping):
            raise NoOverlapError(
                f"{role}: file record must be a mapping, got {type(record).__name__}"
            )
        # Twenty files means twenty record OBJECTS. One object appearing at two
        # indices is a single file claiming to be two, however it answers: the
        # internal audit built a Mapping that advanced through PAIRS_20 on each
        # read, so twenty references to it presented as a complete roster with
        # matching filenames and digests. Identity is what that cannot forge.
        if id(record) in identities:
            raise NoOverlapError(
                f"{role}: the same record object appears at indices "
                f"{identities[id(record)]} and {index} (duplicate evidence)"
            )
        identities[id(record)] = index
        try:
            snapshot.append(dict(record))
        except Exception as exc:  # noqa: BLE001 - a record that cannot be read fails closed
            raise NoOverlapError(f"{role}: record {index} could not be read: {exc}") from exc
    return tuple(snapshot)


def _roster_report(
    records: tuple[Any, ...], *, role: str
) -> tuple[dict, tuple[dict[str, str], ...]]:
    """Bind the evidence to the canonical PAIRS_20 roster; refuse anything short of it.

    BL-1: the proof used to say nothing about *which* files it saw, so twenty
    copies of one record satisfied a twenty-file inventory. Every record must
    name a pair in the frozen universe, alias spellings collapse to the same
    canonical name (so ``eur/usd`` duplicates ``EUR_USD``), and the canonical
    roster must equal PAIRS_20 exactly — no missing, duplicate or unknown pair.

    B-3 generalised: the canonical pair, filename and digest **certified here**
    are returned so the publisher emits exactly these values. Re-deriving them
    from the record a second time is the defect B-3 named for timestamps, and a
    ``str`` subclass can drift across two reads the same way a ``tzinfo`` can.
    """
    identities: list[dict[str, str]] = []
    seen: dict[str, int] = {}
    duplicate: list[str] = []
    unknown: list[Any] = []
    non_canonical: list[str] = []
    filenames: dict[str, int] = {}
    digests: dict[str, int] = {}

    for index, record in enumerate(records):
        raw_pair = record.get("pair")
        try:
            pair = canonical_pair(raw_pair)
        except PairAuthorityError:
            unknown.append(raw_pair)
            continue
        if raw_pair != pair:
            # The committed inventory declares `"pair": "one of PAIRS_20"`, and
            # cost_schema already refuses a non-canonical spelling. Reported so
            # the two consumers of the same frozen contract cannot disagree —
            # but only after the duplicate classification above, so an alias of
            # an already-seen pair is still named as the duplicate it is.
            non_canonical.append(f"{raw_pair!r}->{pair}")
        if pair in seen:
            duplicate.append(pair)
        else:
            seen[pair] = index

        # BL-1 (second round): identity keys are MANDATORY, not opt-in. The
        # committed `required_schema_per_file` lists `filename` and `sha256` as
        # required, and while they were optional the duplicate-evidence guards
        # could simply be switched off by omitting them — twenty records naming
        # twenty pairs while describing one physical file earned the token.
        raw_filename = record.get("filename")
        if not isinstance(raw_filename, str):
            raise NoOverlapError(
                f"{role}: file record {index} ({pair}) has no usable 'filename' "
                "(required by the committed inventory schema)"
            )
        # Collapse to a plain `str` BEFORE checking, so a subclass cannot answer
        # the check with one value and the publication with another (B-3 class).
        filename = str.__str__(raw_filename)
        if not filename.strip():
            raise NoOverlapError(
                f"{role}: file record {index} ({pair}) has no usable 'filename' "
                "(required by the committed inventory schema)"
            )
        if filename in filenames:
            raise NoOverlapError(
                f"{role}: filename {filename!r} appears at records "
                f"{filenames[filename]} and {index} (duplicate evidence)"
            )
        filenames[filename] = index

        raw_digest = record.get("sha256")
        if not isinstance(raw_digest, str):
            raise NoOverlapError(
                f"{role}: file record {index} ({pair}) has a non-string 'sha256' "
                "(required by the committed inventory schema: 64-hex)"
            )
        digest = str.__str__(raw_digest)
        if len(digest) != _SHA256_HEX_LENGTH or any(
            c not in "0123456789abcdefABCDEF" for c in digest
        ):
            raise NoOverlapError(
                f"{role}: file record {index} ({pair}) has no well-formed 'sha256' "
                "(required by the committed inventory schema: 64-hex)"
            )
        key = digest.lower()
        if key in digests:
            raise NoOverlapError(
                f"{role}: sha256 {key} appears at records {digests[key]} and "
                f"{index} (duplicate evidence)"
            )
        digests[key] = index
        # Frozen at the moment of checking. These are the plain-`str` values the
        # duplicate guards above actually used, so the publication cannot differ.
        identities.append({"pair": pair, "filename": filename, "sha256": key})

    missing = [p for p in PAIRS_20 if p not in seen]
    report = {
        "expected_pairs": list(PAIRS_20),
        "expected_pair_count": len(PAIRS_20),
        "actual_pairs": [p for p in PAIRS_20 if p in seen],
        "actual_record_count": len(records),
        "missing_pairs": missing,
        "duplicate_pairs": sorted(set(duplicate)),
        "unknown_pairs": [repr(u) for u in unknown],
        "non_canonical_pair_spellings": sorted(set(non_canonical)),
    }
    if missing or duplicate or unknown or non_canonical:
        raise NoOverlapError(
            f"{role}: roster does not match PAIRS_20 — "
            f"expected {len(PAIRS_20)}, got {len(records)} records; "
            f"missing={report['missing_pairs']}, "
            f"duplicate={report['duplicate_pairs']}, "
            f"unknown={report['unknown_pairs']}, "
            f"non_canonical={report['non_canonical_pair_spellings']}"
        )
    if len(identities) != len(records):  # pragma: no cover - defensive
        raise NoOverlapError(
            f"{role}: certified {len(identities)} identities for {len(records)} records"
        )
    return report, tuple(identities)


def assert_per_file_bounds(
    files: Sequence[Any], *, role: str, expected_count: int | None = None
) -> dict:
    """Per-file ts-bound assertions for the **design** inventory.

    The returned :data:`DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL` token is
    a claim about the whole 20-pair inventory *as declared*, so it is only ever
    produced when the evidence is re-scannable, bound to the canonical roster,
    carries the identity keys the committed schema requires, and every record's
    declared span clears the dead window. ``expected_count`` remains a
    caller-supplied cross-check — on its own it can no longer produce the token.

    **What this token is not (audit B-2, §12.13).** No file is opened, no byte is
    read, and the declared ``sha256`` is checked for shape only — never against
    any file's contents. Playbook §5's byte-level no-overlap proof is therefore
    *not* discharged here and cannot be: the byte-level vocabulary lives in
    :mod:`scripts.m15_gate3a.proof` and this module has no import edge to it, so
    a byte-level token is not reachable from this function by any code path.
    The result states this in ``evidence_basis`` rather than leaving a reader of
    the emitted artifact to infer it.

    ``role="forward"`` is **refused**. The roster binding above is derived from
    ``design_m15_inventory.json``; the committed ``forward_epoch_inventory.json``
    declares a different shape — no ``pair`` key at all, and a per-file
    ``"role": "validation | holdout"`` split that may well mean two records per
    pair. Applying the design roster to it would pre-decide an open contract,
    which is exactly what BL-5 refused to do elsewhere in this change. The
    forward inventory is `EMPTY__NO_FORWARD_DATA_EXISTS` with `file_count: 0`,
    so nothing is blocked by refusing today.
    """
    if role == "forward":
        raise NoOverlapError(
            "forward: per-file proof refused — the committed forward inventory "
            "schema has no 'pair' key and splits each file by validation|holdout, "
            "so the PAIRS_20 roster binding cannot be applied without inventing "
            "the forward evidence shape. Requires separate contract Gate-decision."
        )
    if role != "design":
        raise NoOverlapError(f"unknown role {role!r}")
    records = _materialise(files, role=role)
    if not records:
        raise NoOverlapError(f"{role}: empty file list")
    if expected_count is not None and len(records) != expected_count:
        raise NoOverlapError(f"{role}: expected {expected_count} files, got {len(records)}")
    report, identities = _roster_report(records, role=role)

    checked = 0
    spans: list[dict[str, str]] = []
    for record, identity in zip(records, identities, strict=True):
        tmin = record.get("ts_min_utc")
        tmax = record.get("ts_max_utc")
        if not tmin or not tmax:
            raise NoOverlapError(f"{role}: file missing ts bounds")
        # B-3: parse ONCE, then check and publish the *same* objects. The
        # previous code bound-checked one parse at `:321` and re-parsed the same
        # inputs at `:328-329` to build `certified_spans`; the two parses were
        # independent, so a drifting `tzinfo` returned the proof token while
        # publishing a span inside the dead window — an artifact refuting itself.
        lo = _parse(tmin)
        hi = _parse(tmax)
        _assert_design_bounds_parsed(lo, hi)
        # Record what was actually certified, so the proof artifact can be
        # re-checked against the inventory it claims to prove. `identity` holds
        # the very pair/digest strings the roster guards used, for the same
        # reason.
        spans.append(
            {
                "pair": identity["pair"],
                "sha256": identity["sha256"],
                "filename": identity["filename"],
                # C-2 / contract §12.23: the canonical emission form is
                # `YYYY-MM-DDTHH:MM:SSZ` through the single formatter.
                # `isoformat()` yields `+00:00`, which no committed gate-3a
                # artifact uses and which the contract forbids in any
                # artifact. The formatter refuses a non-zero microsecond
                # rather than truncating it, so a sub-second bound fails
                # closed here instead of being published in a spelling the
                # committed artifacts never carry.
                "ts_min_utc": format_utc_z(lo),
                "ts_max_utc": format_utc_z(hi),
            }
        )
        checked += 1
    if checked != len(records):  # pragma: no cover - defensive
        raise NoOverlapError(f"{role}: checked {checked} of {len(records)} records")
    return {
        "role": role,
        "files_checked": checked,
        "certified_spans": spans,
        # The check covers declared identity + declared ts bounds only. These
        # committed `required_schema_per_file` keys are NOT verified here, and
        # saying so is what stops the token being read as inventory validation.
        #
        # These are quoted VERBATIM from the committed
        # `artifacts/m15_gate3a/design_m15_inventory.json`, so `eligible_event_count`
        # keeps the committed spelling even though §12.20 of the contract
        # Gate-decision pins the measured quantity as `complete_bucket_count`
        # (which is what `aggregation.py` now emits). Renaming the key here
        # would desynchronise this list from the artifact it names. The rename
        # lands with the inventory schema extension at the gate-3a
        # continuation; recorded as a residual item, not silently reconciled.
        "schema_keys_not_verified": [
            "size_bytes",
            "row_count",
            "eligible_event_count",
            "gap_report",
            "pip_size",
        ],
        # B-2: the bounds themselves are DECLARED, not measured. The old result
        # was honest about the five keys above and silent about this, which is
        # the more important omission.
        "evidence_basis": DECLARATION_ONLY_EVIDENCE_BASIS,
        "declared_not_measured": ["ts_min_utc", "ts_max_utc", "sha256", "filename"],
        "files_opened": 0,
        "bytes_measured": 0,
        **report,
        "result": DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL,
    }
