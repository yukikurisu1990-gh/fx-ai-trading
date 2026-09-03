"""The **one** M1→M15 research derivation route for Track A.

`RESEARCH_SCRATCH_M15_DERIVATION_ROUTE_NOT_SELECTED` named three ways to obtain
M15 bars for Track A, each with a cost:

  (i)   run the **committed** ``scripts.m15_gate3a.aggregation.aggregate_m15`` on
        real rows.  When this was written it added: "no code change and no
        refusal trips … **what has contained it is the absence of a reader**".
        **That sentence is now historical.** PR #453 supplied the reader, and a
        review role showed the bypass was live: real rows could be read under a
        valid *read* grant and aggregated without entering this route at all.
        :mod:`scripts.m15_gate3a.derivation_containment` closes it — the
        aggregator itself now refuses real rows outside the window this route
        opens — so what contains arm (i) is a mechanism rather than an absence;
  (ii)  write a **second**, fenced research aggregator — the two-implementation
        structure that produced one identical weekend-gap defect twice;
  (iii) complete the source audit first — the cost the split exists to avoid.

**Arm (i) is selected**, and this module is where that selection becomes visible
in a diff rather than being a decision someone reports having taken.

Why (i) and not (ii)
--------------------

(ii) is the only arm that creates a *new* way to be wrong.  The committed
aggregator's defects are known, enumerated and audited — four re-check rounds
have gone through it — whereas a second aggregator starts at zero and diverges
silently, which is exactly what INV-1 and the weekend-gap defect were.  One
implementation with a BLOCKED audit is a known quantity; two implementations are
two unknown ones.

What selecting (i) costs, stated rather than absorbed
-----------------------------------------------------

The committed aggregator's source audit stands **BLOCKED**
(`M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`),
so Track A would be giving an audit-blocked module its first real-data caller.
That is a real cost and it is **not** paid by this module: it is paid by the
authorisation, which names the operation and the head it is granted against, and
by the output being `NON_DECISION_BEARING_EXPLORATORY_ONLY` — a Track A
derivation is **not** the §4 artifact and may never be recorded as one.

What the body does
------------------

Per pair, in the intersection of grant and request: hand the authorised M1 rows
to the committed aggregator and keep the ``(bars, gap_report)`` pair it returns.
Nothing else — no labels, no features, no ATR, no cost model, no eligibility.
Those are R1's survey, and the survey is a separate module so that this route
stays the one thing it is: the authorised way to turn M1 rows into M15 bars.

**``expected_minutes`` is passed as ``None``, and that is a decision rather than
an omission.** An earlier revision of this module required a Calendar A and
refused without one. PR #444's D-6 forbids an implementer authoring market-hours
times, DST transitions or a holiday list; the execution gate §8 says requiring a
`ValidatedCalendar` of Track A "would block exploration on an artefact that does
not exist, for no leakage reason"; and
`PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` is open. So there is no
approved calendar to pass, the aggregator's calendar-derived accounting comes
back ``None``, and this route records
``COVERAGE_AUTHORITY_ABSENT_R1_REPORTS_A_DECLARED_LABEL_DIAGNOSTIC`` so that the
absence is reported rather than filled in.

Two properties are worth naming because each is a refusal rather than a
convention:

* the pair list is the **intersection** of grant and request — narrowest wins,
  as on the read route, which learned it twice;
* the window around the delegate call is opened **after** every gate has passed.
  Opening it is not an authorisation, and it is closed on the way out whether
  the aggregation raised or returned.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from scripts.m15_gate3a.aggregation import (
    BUCKET_MINUTES,
    FULL_BUCKET_SOURCE_BARS,
    aggregate_m15,
)
from scripts.m15_gate3a.derivation_containment import authorised_derivation_window
from scripts.m15_gate3a.pair_authority import PairAuthorityError, canonical_pair
from scripts.m15_gate3a.session_windows import COVERAGE_STATUS
from scripts.m15_track_a import authorization, isolation, seen_ledger
from scripts.m15_track_a.identity import RunIdentity
from scripts.m15_track_a.read_route import (
    HistoricalRead,
    ReadRequest,
    _as_instant,
    assert_development_only,
    assert_span_admissible,
)
from scripts.m15_track_a.row_scope import (
    ROW_SCOPE_STATUS,
    RowScope,
    RowScopeError,
    assert_batch_pairs_in_scope,
    rows_in_scope,
)

#: The selected arm, named so the choice is greppable.
SELECTED_ROUTE: Final[str] = "arm_i_committed_gate3a_aggregate_m15_on_research_scratch_output"

#: The committed callable this route delegates to — **bound**, not described.
#:
#: §8.12.10 condition 3 says the choice "counts as made only when it appears in a
#: diff — an explicit committed caller — never as a decision a session reports
#: having taken". A docstring naming the function is a report; this binding is
#: the diff. It is still not a *call*: the body is absent, so what the diff
#: commits is which implementation this route will use, not a use of it.
DELEGATE = aggregate_m15

#: The same name as a string, so a containment audit can assert the binding
#: without importing the delegate.
DELEGATE_QUALNAME: Final[str] = "scripts.m15_gate3a.aggregation.aggregate_m15"

#: What a Track A derivation is **not**.
NOT_THE_SECTION_4_ARTIFACT: Final[str] = (
    "A_TRACK_A_DERIVATION_IS_NOT_THE_SECTION_4_ARTIFACT_AND_MAY_NOT_BE_RECORDED_AS_ONE"
)

#: The audit status the selected arm inherits, restated so it is not forgotten.
DELEGATE_AUDIT_STATUS: Final[str] = (
    "M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES"
)

#: Both Track A classifications, carried on every derivation result.
OUTPUT_CLASSIFICATION: Final[str] = "NON_DECISION_BEARING_EXPLORATORY_ONLY"
OUTPUT_CLASSIFICATION_SECONDARY: Final[str] = "RESEARCH_SCRATCH_NON_AUTHORITATIVE"


class DerivationRouteError(RuntimeError):
    """Raised when a Track A derivation is refused."""


@dataclass(frozen=True)
class DerivationRequest:
    """One M1→M15 research derivation over a declared interval.

    Carries the :class:`HistoricalRead` rather than re-reading: a derivation
    that read for itself would be a second read of the same interval under a
    grant that authorises a derivation, which is the operation confusion this
    whole split exists to prevent. The rows come from the authorised read; this
    route only aggregates them.
    """

    read_request: ReadRequest
    read: HistoricalRead

    @property
    def bucket_minutes(self) -> int:
        """From the committed aggregator, never re-declared here."""
        return BUCKET_MINUTES

    @property
    def full_bucket_source_bars(self) -> int:
        """From the committed aggregator: an event needs ``n_source_bars == 15``."""
        return FULL_BUCKET_SOURCE_BARS


@dataclass(frozen=True)
class DerivedM15:
    """What one authorised Track A derivation returns, and its classification.

    Deliberately not a bare dict, for the reason :class:`HistoricalRead` is not:
    the classification travels with the bars, so a downstream stage cannot pick
    them up without it.
    """

    run_id: str
    operation: str
    epoch: str
    span_start_utc: str
    span_end_utc: str
    coverage_status: str
    bars_by_pair: dict[str, list[dict[str, Any]]]
    gap_reports: dict[str, dict[str, Any]]

    input_scope_status: str = ROW_SCOPE_STATUS
    classification: str = OUTPUT_CLASSIFICATION
    classification_secondary: str = OUTPUT_CLASSIFICATION_SECONDARY
    not_the_section_4_artifact: str = NOT_THE_SECTION_4_ARTIFACT

    @property
    def bar_count(self) -> int:
        return sum(len(bars) for bars in self.bars_by_pair.values())

    def as_record(self) -> dict[str, Any]:
        """Counts and identities only — never a bar, never a price."""
        return {
            "run_id": self.run_id,
            "operation": self.operation,
            "epoch": self.epoch,
            "span_start_utc": self.span_start_utc,
            "span_end_utc": self.span_end_utc,
            "coverage_status": self.coverage_status,
            "input_scope_status": self.input_scope_status,
            "bars_by_pair": {pair: len(bars) for pair, bars in self.bars_by_pair.items()},
            "classification": self.classification,
            "classification_secondary": self.classification_secondary,
            "not_the_section_4_artifact": self.not_the_section_4_artifact,
        }


def _pairs_to_derive(*, granted: tuple[str, ...], requested: tuple[str, ...]) -> tuple[str, ...]:
    """The intersection of grant and request. Narrowest wins.

    The read route learned this twice — coverage is *containment*, so a grant
    may be wider than the request, and looping the **grant**'s pair list derives
    pairs the declaration never covered. This route inherited the original
    defect rather than the fix: a review role passed a one-pair request with a
    two-pair grant and got two pairs back.
    """
    try:
        granted_canonical = frozenset(canonical_pair(pair) for pair in granted)
        requested_canonical = tuple(canonical_pair(pair) for pair in requested)
    except PairAuthorityError as exc:
        raise DerivationRouteError(f"Track A derivation refused: {exc}") from exc
    chosen: list[str] = []
    for pair in requested_canonical:
        if pair in chosen:
            raise DerivationRouteError(
                f"Track A derivation refused: {pair} is named twice in the request."
            )
        if pair not in granted_canonical:
            raise DerivationRouteError(
                f"Track A derivation refused: {pair} is not in the grant, although the "
                "coverage check passed. The request changed after it was checked."
            )
        chosen.append(pair)
    if not chosen:
        raise DerivationRouteError("Track A derivation refused: no pair to derive.")
    return tuple(chosen)


def derive_m15(
    request: DerivationRequest,
    identity: RunIdentity,
    *,
    grant: Any = None,
    context: Any = None,
) -> object:
    """The single Track A derivation route.

    The gates are the read route's, with the operation changed: a derivation is
    a distinct authorisation from a read, so a grant for one does not cover the
    other.  playbook §2.5 forbids chaining irreversible stages, and this is the
    same principle inside Track A.
    """
    if not isolation.is_installed():
        raise DerivationRouteError(
            "Track A derivation refused: isolation guards are not installed."
        )

    if type(request) is not DerivationRequest:
        # Pinned before a single field is read off it. ``DerivationRequest`` is
        # a public frozen dataclass, so a subclass could answer ``read_request``
        # honestly at the gate and differently at the delegate call — the exact
        # shape ``read_historical`` pins ``ReadRequest`` against, and which this
        # route did not pin at all.
        raise DerivationRouteError(
            "Track A derivation refused: `request` must be exactly a DerivationRequest, not a "
            f"{type(request).__name__}."
        )
    if type(request.read_request) is not ReadRequest:
        raise DerivationRouteError(
            "Track A derivation refused: `read_request` must be exactly a ReadRequest, not a "
            f"{type(request.read_request).__name__}. A subclass can answer a field differently "
            "each time it is read, so the gates and the delegate would see different scopes."
        )

    # **The normalised snapshot.** Every field is read exactly once, here, and
    # every later line uses this object rather than the caller's. ``frozen=True``
    # yields to ``object.__setattr__``, so a caller keeping a reference could
    # otherwise widen the request between the coverage check and the aggregation
    # — this route re-reads the span to build its record, which is where that
    # would land. Rebuilding through ``ReadRequest.__post_init__`` also re-runs
    # its validation on the values actually captured.
    read_request = ReadRequest(
        span_start_utc=request.read_request.span_start_utc,
        span_end_utc=request.read_request.span_end_utc,
        pairs=tuple(request.read_request.pairs),
        timeframe=request.read_request.timeframe,
        warmup_extension_start_utc=request.read_request.warmup_extension_start_utc,
    )

    checked = authorization.require_authorization(
        grant,
        operation=authorization.OPERATION_M15_DERIVATION,
        span_start_utc=read_request.touched_start_utc,
        span_end_utc=read_request.span_end_utc,
        pairs=read_request.pairs,
        timeframe=read_request.timeframe,
        identity=identity,
        context=context,
    )

    assert_span_admissible(read_request)
    # Added after a review role found it missing. Deriving M15 bars over the
    # slice is "computing a statistic over it", which R-2 forbids before R4 —
    # and this route's docstring claimed it applied the read route's gates,
    # which stopped being true the moment that route grew a slice gate. The body
    # is still absent, so nothing was derived; the gate composition was wrong.
    assert_development_only(read_request)

    seen_ledger.assert_declared(
        span_start_utc=read_request.touched_start_utc,
        span_end_utc=read_request.span_end_utc,
        pairs=read_request.pairs,
    )

    seen_ledger.record_grant(checked, identity, route=SELECTED_ROUTE)

    if type(request.read) is not HistoricalRead:  # noqa: E721
        # Pinned exactly, and checked before anything is read off it. A missing
        # read used to reach ``request.read.operation`` and escape as a bare
        # AttributeError -- fail-closed by accident is not fail-closed, and an
        # AttributeError walks straight past ``except DerivationRouteError``.
        raise DerivationRouteError(
            "Track A derivation refused: `read` must be exactly a HistoricalRead from the "
            f"authorised read route, not a {type(request.read).__name__}. The derivation "
            "aggregates rows that came through the gates; it does not fetch its own."
        )
    if type(request.read.rows_by_pair) is not dict:  # noqa: E721
        raise DerivationRouteError(
            "Track A derivation refused: `rows_by_pair` must be a plain dict, not a "
            f"{type(request.read.rows_by_pair).__name__}."
        )

    # **The read is snapshotted too, and this was a real defect.**
    #
    # The first revision of this fix snapshotted ``read_request`` and left
    # ``request.read`` live, then built the returned record from
    # ``request.read.epoch`` and its two span fields *after* every gate. An
    # audit widened those from a **plain sibling thread** — no monkeypatch, no
    # subclass — and got a `DerivedM15` labelled `1970-01-01..2099-12-31` that
    # `r1_survey` copied verbatim into the R1 evidence record. The rows were
    # never wrong; the derivation's account of them was. ``derivation_containment``
    # makes the same argument about per-pair parallelism: "an obvious
    # optimisation, so that is a bypass reachable by accident, not only by
    # intent".
    #
    # Every field is read exactly once, here, and nothing below touches
    # ``request.read`` again.
    read = HistoricalRead(
        run_id=request.read.run_id,
        operation=request.read.operation,
        timeframe=request.read.timeframe,
        epoch=request.read.epoch,
        span_start_utc=request.read.span_start_utc,
        span_end_utc=request.read.span_end_utc,
        rows_by_pair=dict(request.read.rows_by_pair),
    )

    if read.operation != authorization.OPERATION_HISTORICAL_READ:
        raise DerivationRouteError(
            "Track A derivation refused: the supplied rows did not come from "
            f"{authorization.OPERATION_HISTORICAL_READ}."
        )
    if read.timeframe != read_request.timeframe:
        raise DerivationRouteError(
            f"Track A derivation refused: the read is {read.timeframe} and the "
            f"request names {read_request.timeframe}."
        )
    # The read's own span is **checked**, not inherited. ``HistoricalRead`` is a
    # public frozen dataclass, so a hand-built one passed every gate and put its
    # own span straight into the record: a review role recorded
    # `1970-01-01 .. 2099-12-31` that way, and separately derived five days of
    # bars under a one-day grant. Nothing new was read either time -- the defect
    # is that the derivation's record disagreed with its own authorisation.
    if not (
        read_request.touched_start_utc <= read.span_start_utc
        and read.span_end_utc <= read_request.span_end_utc
    ):
        raise DerivationRouteError(
            f"Track A derivation refused: the read covers "
            f"{read.span_start_utc}..{read.span_end_utc}, which is not "
            f"inside the gated interval {read_request.touched_start_utc}.."
            f"{read_request.span_end_utc}."
        )

    derived_pairs = _pairs_to_derive(granted=checked.pairs, requested=read_request.pairs)

    # **The second layer: the rows, not the declaration.**
    #
    # Everything above this point establishes that what the caller *declared* is
    # inside the authorisation. None of it looks at what the caller actually
    # handed over, and two review roles at PR #456 measured the consequence:
    # slice, dead-window and forward rows aggregated under a valid derivation
    # grant, because ``no_overlap`` "checks metadata and cannot see bytes" — the
    # read route's own words about why it needs row-level guards too.
    #
    # The window is the **intersection** of grant and request, computed the same
    # way ``read_historical`` computes its own: narrowest wins on both ends. A
    # derivation validated against the request alone would accept everything a
    # wider request declared, and against the grant alone everything a wider
    # grant allowed.
    try:
        # Inside the translation: ``RowScopeError`` is not a
        # ``DerivationRouteError``, so an empty-window refusal raised while the
        # scope is being built would escape as a type this route's contract does
        # not name. Unreachable today — coverage forces request within grant —
        # and fail-closed either way, but "unreachable" is a property of the
        # callers.
        scope = RowScope(
            lo=max(
                _as_instant(checked.span_start_utc, end_of_day=False),
                _as_instant(read_request.touched_start_utc, end_of_day=False),
            ),
            hi=min(
                _as_instant(checked.span_end_utc, end_of_day=True),
                _as_instant(read_request.span_end_utc, end_of_day=True),
            ),
            pairs=derived_pairs,
        )
        assert_batch_pairs_in_scope(read.rows_by_pair, scope)
        in_scope_rows = {
            pair: rows_in_scope(read.rows_by_pair.get(pair), pair=pair, scope=scope)
            for pair in derived_pairs
        }
    except RowScopeError as exc:
        # Re-raised as this route's own error so an existing
        # ``except DerivationRouteError`` still fails closed, with the cause kept.
        raise DerivationRouteError(f"Track A derivation refused: {exc}") from exc

    bars_by_pair: dict[str, list[dict[str, Any]]] = {}
    gap_reports: dict[str, dict[str, Any]] = {}
    with authorised_derivation_window():
        for pair in derived_pairs:
            # The **validated snapshot**, never the caller's rows.
            # A mapping that answers one way when it is checked and another when
            # it is read defeats any amount of checking; the rows that were
            # validated are the rows that are aggregated.
            rows = in_scope_rows[pair]
            # ``expected_minutes=None`` **deliberately**, and the consequence
            # is recorded rather than hidden. D-6's coverage authority is an
            # approved calendar artifact;
            # `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` is open,
            # D-6 forbids an implementer authoring one, and omega-12 forbids
            # Track A authoring market hours. So the aggregator's
            # calendar-derived accounting comes back ``None`` -- which is what
            # it is -- and R1 reports observed structure as a declared-label
            # diagnostic rather than a coverage figure with no authority.
            bars, report = DELEGATE(rows, pair=pair, expected_minutes=None)
            bars_by_pair[pair] = bars
            gap_reports[pair] = report

    return DerivedM15(
        run_id=identity.run_id,
        operation=authorization.OPERATION_M15_DERIVATION,
        epoch=read.epoch,
        span_start_utc=read.span_start_utc,
        span_end_utc=read.span_end_utc,
        coverage_status=COVERAGE_STATUS,
        bars_by_pair=bars_by_pair,
        gap_reports=gap_reports,
    )


__all__ = [
    "DELEGATE",
    "DELEGATE_AUDIT_STATUS",
    "DELEGATE_QUALNAME",
    "NOT_THE_SECTION_4_ARTIFACT",
    "OUTPUT_CLASSIFICATION",
    "OUTPUT_CLASSIFICATION_SECONDARY",
    "SELECTED_ROUTE",
    "DerivationRequest",
    "DerivationRouteError",
    "DerivedM15",
    "derive_m15",
]
