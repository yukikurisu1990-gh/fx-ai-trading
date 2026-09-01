"""The derivation's **second** scope layer: the rows it was actually handed.

Why this module exists
----------------------

`derive_m15` gated what a request *declared* and never looked at what it was
*given*. Two review roles measured the consequence at PR #456: rows dated inside
the `EXPLORATORY_OOS_SLICE`, the consumed dead window and the forward epoch
aggregated under a valid derivation grant, and a `ReadRequest` subclass honest at
the gates and widened afterwards produced a `DerivedM15` labelled over the slice
while the seen-data ledger recorded five development days. Neither was reachable
— no route in this repository can *produce* those rows — but the guarantee was
one layer thinner than the read's, and "unreachable today" is a property of the
callers, not of the route.

`read_historical` has carried the equivalent checks from the start, with its own
commentary saying why: `no_overlap` "checks metadata and cannot see bytes", and
relying on the file's contents would be "an accident of the data, not a property
of the route". Both sentences are about the derivation too.

**This does not trust the caller.** The derivation is a separately granted
operation, so it establishes for itself that its input is inside its own
authorisation rather than inheriting the belief that an authorised reader
produced it.

Two layers, one set of boundaries
---------------------------------

The **boundary definitions are shared** with the read route — the same
`is_dead_window_instant`, the same `FORWARD_FLOOR`, the same
`assert_clear_of_slice`, the same `canonical_pair`, the same `ROW_TIMESTAMP_KEY`
and `ROW_SIDE_KEYS`. Inventing a second set of dates for the same windows is the
two-implementation defect this programme has already paid for twice, and a
boundary that can drift between two modules is worse than one checked once.

What is **not** shared is the check. Declaration-level (`assert_span_admissible`,
`assert_development_only`, `grant_covers`) and row-level (here) stay separate
layers, because a single shared helper would make both layers wrong together —
which is the failure mode a second layer exists to catch.

The snapshot, and why the rows that are validated are the rows that are used
---------------------------------------------------------------------------

Every validated row is copied into a **fresh plain `dict`**, and that copy is
what the caller hands to the aggregator. A mapping that answers one way when it
is checked and another when it is read defeats any amount of checking, and this
package has been defeated that way before: `aggregate_m15._snapshot_row` exists
because an audit "built a row whose values changed between reads and got an
``eligible: True`` bar with ``bid_h`` below ``bid_l``", and a two-faced `list`
subclass has defeated the per-row provenance marker by being iterated twice.
Validating a snapshot and returning it collapses the two reads into one.

The real-provenance marker is carried onto the snapshot deliberately. Dropping it
would make every derivation look synthetic to
:mod:`scripts.m15_gate3a.derivation_containment` and disarm the bypass guard —
a "fix" that quietly removes a control is worse than the gap it closes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from scripts.m15_gate3a.derivation_containment import is_real_row, stamp_real_provenance
from scripts.m15_gate3a.no_overlap import FORWARD_FLOOR, is_dead_window_instant
from scripts.m15_gate3a.pair_authority import PairAuthorityError, canonical_pair
from scripts.m15_track_a.oos_slice import OosSliceError, assert_clear_of_slice
from scripts.m15_track_a.read_route import ROW_SIDE_KEYS, ROW_TIMESTAMP_KEY

#: Greppable, and the same shape as the read route's refusal tokens.
ROW_SCOPE_TOKEN: Final[str] = "M15_DERIVATION_INPUT_ROWS_OUTSIDE_THE_AUTHORISED_SCOPE_REFUSED"

#: What this layer establishes, and what it does not.
ROW_SCOPE_STATUS: Final[str] = (
    "DERIVATION_INPUT_VALIDATED_AGAINST_THE_GRANT_REQUEST_INTERSECTION_NOT_AGAINST_A_CALLER_CLAIM"
)


class RowScopeError(RuntimeError):
    """Raised when the rows handed to a derivation are outside its authorisation."""


@dataclass(frozen=True)
class RowScope:
    """The window and pair set one derivation is authorised over.

    Built from the **intersection** of grant and request, never from either
    alone: coverage is containment, so a grant may be wider than the request and
    a request may be wider than the grant. Narrowest wins, which is the rule the
    read route had to learn twice.
    """

    lo: datetime
    hi: datetime
    pairs: tuple[str, ...]

    def __post_init__(self) -> None:
        for field, value in (("lo", self.lo), ("hi", self.hi)):
            # Exact type, not ``isinstance``: ``pandas.Timestamp`` is a
            # ``datetime`` subclass, and this package has had a boundary check
            # broken by one before — nanoseconds survived a ``.replace()`` that
            # was meant to normalise the instant away.
            if type(value) is not datetime:  # noqa: E721
                raise RowScopeError(f"{field} must be a plain datetime, got {type(value).__name__}")
            if value.utcoffset() is None:
                # ``tzinfo is not None`` is not an awareness test: a tzinfo whose
                # ``utcoffset`` returns None is naive, and a naive instant is
                # re-interpreted in the host's zone.
                raise RowScopeError(f"{field} must be timezone-aware")
        if self.lo > self.hi:
            raise RowScopeError(f"empty window: {self.lo.isoformat()}..{self.hi.isoformat()}")
        if type(self.pairs) is not tuple or not self.pairs:  # noqa: E721
            raise RowScopeError("pairs must be a non-empty tuple")
        for pair in self.pairs:
            if type(pair) is not str:  # noqa: E721
                raise RowScopeError(f"malformed pair in scope: {pair!r}")


def assert_batch_pairs_in_scope(rows_by_pair: Any, scope: RowScope) -> None:
    """Refuse a batch carrying any pair the derivation is not authorised over.

    The loop that aggregates iterates the *intersection*, so an extra pair in the
    batch is never derived — but it is still real historical data sitting in the
    object a derivation was handed, and a batch whose contents exceed its
    authorisation is a mixed-scope batch whichever half gets used. Refused rather
    than ignored: silently working on the subset leaves the caller believing the
    whole batch was in scope.
    """
    if type(rows_by_pair) is not dict:  # noqa: E721
        raise RowScopeError(
            f"{ROW_SCOPE_TOKEN}: rows_by_pair must be a plain dict, got "
            f"{type(rows_by_pair).__name__}. A mapping subclass can answer one way when it is "
            "checked and another when it is read."
        )
    authorised = frozenset(scope.pairs)
    seen: set[str] = set()
    for pair in rows_by_pair:
        if type(pair) is not str:  # noqa: E721
            raise RowScopeError(f"{ROW_SCOPE_TOKEN}: malformed pair key {pair!r} in the batch.")
        try:
            canonical = canonical_pair(pair)
        except PairAuthorityError as exc:
            raise RowScopeError(f"{ROW_SCOPE_TOKEN}: {exc}") from exc
        if pair != canonical:
            # An **alias spelling**, and the first revision of this function let
            # it through: it canonicalised the key for the membership test while
            # the derivation loop reads only the canonical key, so ``EURUSD``
            # and ``eur/usd`` sat in the batch carrying rows that were never
            # validated. ``read_route._pairs_to_read`` refuses two spellings of
            # one pair for exactly this reason; an audit measured that this did
            # not.
            raise RowScopeError(
                f"{ROW_SCOPE_TOKEN}: the batch names {pair!r}, an alias of {canonical}. The "
                "derivation reads the canonical key, so an alias would carry rows nothing "
                "validates. Canonical spellings only."
            )
        if canonical in seen:
            raise RowScopeError(f"{ROW_SCOPE_TOKEN}: the batch names {canonical} more than once.")
        seen.add(canonical)
        if canonical not in authorised:
            raise RowScopeError(
                f"{ROW_SCOPE_TOKEN}: the batch carries rows for {canonical}, which is not in "
                f"the authorised pair set {', '.join(scope.pairs)}. A derivation does not "
                "quietly work on the subset of a batch that happens to be in scope."
            )
    missing = authorised - seen
    if missing:
        raise RowScopeError(
            f"{ROW_SCOPE_TOKEN}: the batch carries no rows for {', '.join(sorted(missing))}, "
            "which the authorisation names. A partial derivation reported as a whole one is "
            "how a coverage figure stops meaning anything."
        )


def rows_in_scope(rows: Any, *, pair: str, scope: RowScope) -> list[dict[str, Any]]:
    """Validate every row against `scope` and return a fresh, plain snapshot.

    Fail-closed on the first violation. Nothing is filtered: a row outside the
    authorisation means the batch is not what the authorisation describes, and
    dropping it would hand back a result that looks compliant and is not.
    """
    if type(rows) is not list:  # noqa: E721
        raise RowScopeError(
            f"{ROW_SCOPE_TOKEN}: {pair} rows must be a plain list, got {type(rows).__name__}. A "
            "sequence subclass can yield different rows on a second iteration, and this package "
            "has been defeated that way."
        )
    if not rows:
        raise RowScopeError(
            f"{ROW_SCOPE_TOKEN}: {pair} carries no rows. An empty derivation reported as a "
            "whole one is how a coverage figure stops meaning anything."
        )

    snapshot: list[dict[str, Any]] = []
    previous: datetime | None = None
    for index, row in enumerate(rows):
        if type(row) is not dict:  # noqa: E721
            raise RowScopeError(
                f"{ROW_SCOPE_TOKEN}: {pair} row {index} must be a plain dict, got "
                f"{type(row).__name__}."
            )
        # ``is_real_row`` before anything else is read off the row: it treats a
        # mapping that raises as **real**, and the marker has to reach the
        # snapshot or the derivation-bypass guard sees synthetic rows.
        real = is_real_row(row)

        if ROW_TIMESTAMP_KEY not in row:
            raise RowScopeError(
                f"{ROW_SCOPE_TOKEN}: {pair} row {index} has no {ROW_TIMESTAMP_KEY!r}."
            )
        timestamp = row[ROW_TIMESTAMP_KEY]
        if type(timestamp) is not datetime:  # noqa: E721
            raise RowScopeError(
                f"{ROW_SCOPE_TOKEN}: {pair} row {index} has a {type(timestamp).__name__} "
                f"timestamp; a plain tz-aware datetime is required. A datetime subclass can "
                "carry precision that survives normalisation."
            )
        # ``tzinfo is UTC`` rather than ``utcoffset() == 0``: an offset read
        # twice is an offset a two-faced tzinfo can answer differently, and the
        # first revision read it once to gate and once inside ``astimezone``.
        # The authorised read stamps ``datetime.UTC`` itself, so identity is the
        # exact test and it cannot be computed.
        if timestamp.tzinfo is not UTC:
            if timestamp.utcoffset() is None:
                raise RowScopeError(
                    f"{ROW_SCOPE_TOKEN}: {pair} row {index} is timezone-naive. A naive instant "
                    "is re-interpreted in the host's zone, which moves the boundary with the "
                    "host."
                )
            raise RowScopeError(
                f"{ROW_SCOPE_TOKEN}: {pair} row {index} does not carry datetime.UTC. The "
                "authorised read produces UTC instants; anything else was assembled elsewhere, "
                "and a tzinfo that computes its offset can compute a different one next time."
            )
        instant = timestamp

        if previous is not None and instant <= previous:
            raise RowScopeError(
                f"{ROW_SCOPE_TOKEN}: {pair} row {index} is at {instant.isoformat()}, not after "
                f"the previous row. The authorised read produces a strictly increasing series; "
                "this one was reordered or duplicated after it."
            )
        previous = instant

        # The three committed boundaries, checked with the same primitives the
        # read route uses, then the authorised window itself.
        if is_dead_window_instant(instant):
            raise RowScopeError(
                f"{ROW_SCOPE_TOKEN}: {pair} row {index} is at {instant.isoformat()}, inside the "
                "consumed dead window."
            )
        if instant >= FORWARD_FLOOR:
            raise RowScopeError(
                f"{ROW_SCOPE_TOKEN}: {pair} row {index} is at {instant.isoformat()}, at or after "
                f"the forward-epoch floor {FORWARD_FLOOR.date()}. That span is Track B's "
                "confirmation dataset and no Track A operation may touch it."
            )
        try:
            assert_clear_of_slice(instant, instant, what=f"{ROW_SCOPE_TOKEN}: {pair} row {index}")
        except OosSliceError as exc:
            raise RowScopeError(str(exc)) from exc
        if instant < scope.lo or instant > scope.hi:
            raise RowScopeError(
                f"{ROW_SCOPE_TOKEN}: {pair} row {index} is at {instant.isoformat()}, outside the "
                f"authorised window {scope.lo.isoformat()}..{scope.hi.isoformat()} — the "
                "intersection of the grant and the request, warm-up included."
            )

        built: dict[str, Any] = {ROW_TIMESTAMP_KEY: instant}
        for key in ROW_SIDE_KEYS:
            if key not in row:
                raise RowScopeError(
                    f"{ROW_SCOPE_TOKEN}: {pair} row {index} is missing side key {key!r}."
                )
            value = row[key]
            if type(value) is not float:  # noqa: E721
                # ``float(value)`` is not a pin: a ``float`` subclass decides
                # what ``__float__`` returns, and this package has had a
                # numeric guard walked past that way.
                raise RowScopeError(
                    f"{ROW_SCOPE_TOKEN}: {pair} row {index} key {key!r} is a "
                    f"{type(value).__name__}, not a plain float."
                )
            if value != value or value in (float("inf"), float("-inf")):
                raise RowScopeError(
                    f"{ROW_SCOPE_TOKEN}: {pair} row {index} key {key!r} is not finite."
                )
            built[key] = value
        if real:
            stamp_real_provenance(built)
        snapshot.append(built)

    return snapshot


__all__ = [
    "ROW_SCOPE_STATUS",
    "ROW_SCOPE_TOKEN",
    "RowScope",
    "RowScopeError",
    "assert_batch_pairs_in_scope",
    "rows_in_scope",
]
