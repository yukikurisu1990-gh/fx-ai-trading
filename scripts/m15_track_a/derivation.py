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

Per pair, in the order the grant names them: hand the authorised M1 rows to the
committed aggregator together with the expected-slot set **Calendar A** declares
for that pair, and keep the ``(bars, gap_report)`` pair it returns.  Nothing
else — no labels, no features, no ATR, no cost model, no eligibility.  Those are
R1's survey, and the survey is a separate module so that this route stays the
one thing it is: the authorised way to turn M1 rows into M15 bars.

Three properties are worth naming because each is a refusal rather than a
convention:

* the expected-slot set is **required**, not optional.  ``aggregate_m15`` accepts
  ``expected_minutes=None`` and then reports its calendar-derived accounting as
  ``None``; a derivation that silently produced no coverage accounting is
  exactly the "measurement with no authority" R1 was blocked on, so this route
  refuses instead;
* the calendar is validated **through** ``validate_calendar`` and its epoch is
  checked, so a calendar for another epoch cannot be substituted;
* the window around the delegate call is opened **after** every gate has passed.
  Opening it is not an authorisation, and it is closed on the way out whether
  the aggregation raised or returned.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Final

from scripts.m15_gate3a.aggregation import (
    BUCKET_MINUTES,
    FULL_BUCKET_SOURCE_BARS,
    aggregate_m15,
)
from scripts.m15_gate3a.calendar_authority import (
    CalendarAuthorityError,
    ValidatedCalendar,
    validate_calendar,
)
from scripts.m15_gate3a.derivation_containment import authorised_derivation_window
from scripts.m15_track_a import authorization, isolation, seen_ledger
from scripts.m15_track_a.identity import RunIdentity
from scripts.m15_track_a.read_route import (
    HistoricalRead,
    ReadRequest,
    assert_development_only,
    assert_span_admissible,
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
    calendar_a: Any

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
    calendar_authority: str
    calendar_content_digest: str
    bars_by_pair: dict[str, list[dict[str, Any]]]
    gap_reports: dict[str, dict[str, Any]]

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
            "calendar_authority": self.calendar_authority,
            "calendar_content_digest": self.calendar_content_digest,
            "bars_by_pair": {pair: len(bars) for pair, bars in self.bars_by_pair.items()},
            "classification": self.classification,
            "classification_secondary": self.classification_secondary,
            "not_the_section_4_artifact": self.not_the_section_4_artifact,
        }


def expected_minutes_for(calendar: ValidatedCalendar, pair: str) -> frozenset[datetime]:
    """Calendar A's expected **M15 slots**, as the expected **M1 minutes** they contain.

    Two granularities meet here and they are not the same authority spelled
    differently. D-6's artifact declares ``expected_m15_slots`` — bucket starts —
    because slot membership is what a market calendar decides. ``aggregate_m15``
    wants ``expected_minutes``: the minute-level source authority its accounting
    identity is checked against (``expected == usable + absent + rejected``).

    The expansion is total and deterministic — each expected slot contributes
    exactly ``BUCKET_MINUTES`` consecutive minutes — so it introduces no
    judgement and no boundary. It is written here, in the authorised route,
    rather than in the calendar module, because it is a statement about what the
    *aggregator* consumes, not about what the market calendar declares.
    """
    minutes: set[datetime] = set()
    for slot in calendar.expected_slots(pair):
        for offset in range(BUCKET_MINUTES):
            minutes.add(slot + timedelta(minutes=offset))
    return frozenset(minutes)


def _validated_calendar(calendar_a: Any, *, epoch: str) -> ValidatedCalendar:
    """Calendar A, validated for this epoch, or refuse.

    An already-validated record is accepted so a caller that validated once does
    not validate twice; anything else goes through ``validate_calendar``, which
    is the only thing that mints one.
    """
    if calendar_a is None:
        raise DerivationRouteError(
            "Track A derivation refused: no Calendar A supplied. The expected-slot set is "
            "the coverage authority and is never inferred from the data (PR #444 D-6), so a "
            "derivation without it would produce coverage accounting with no authority."
        )
    if isinstance(calendar_a, ValidatedCalendar):
        validated = calendar_a
    else:
        try:
            validated = validate_calendar(calendar_a, expected_epoch=epoch)
        except CalendarAuthorityError as exc:
            raise DerivationRouteError(
                f"Track A derivation refused: Calendar A did not validate for epoch "
                f"{epoch!r}: {exc}"
            ) from exc
    if validated.target_epoch != epoch:
        raise DerivationRouteError(
            f"Track A derivation refused: Calendar A targets {validated.target_epoch!r} and "
            f"the read is {epoch!r}. The expected slot set of one epoch is not evidence "
            "about another."
        )
    return validated


def derive_m15(
    request: DerivationRequest,
    identity: RunIdentity,
    *,
    grant: Any = None,
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

    read_request = request.read_request
    checked = authorization.require_authorization(
        grant,
        operation=authorization.OPERATION_M15_DERIVATION,
        span_start_utc=read_request.touched_start_utc,
        span_end_utc=read_request.span_end_utc,
        pairs=read_request.pairs,
        timeframe=read_request.timeframe,
        identity=identity,
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

    if type(request.read) is not HistoricalRead:
        # Pinned exactly, and checked before anything is read off it. A missing
        # read used to reach ``request.read.operation`` and escape as a bare
        # AttributeError -- fail-closed by accident is not fail-closed, and an
        # AttributeError walks straight past ``except DerivationRouteError``.
        raise DerivationRouteError(
            "Track A derivation refused: `read` must be exactly a HistoricalRead from the "
            f"authorised read route, not a {type(request.read).__name__}. The derivation "
            "aggregates rows that came through the gates; it does not fetch its own."
        )
    if request.read.operation != authorization.OPERATION_HISTORICAL_READ:
        raise DerivationRouteError(
            "Track A derivation refused: the supplied rows did not come from "
            f"{authorization.OPERATION_HISTORICAL_READ}."
        )
    if request.read.timeframe != read_request.timeframe:
        raise DerivationRouteError(
            f"Track A derivation refused: the read is {request.read.timeframe} and the "
            f"request names {read_request.timeframe}."
        )

    calendar = _validated_calendar(request.calendar_a, epoch=request.read.epoch)

    bars_by_pair: dict[str, list[dict[str, Any]]] = {}
    gap_reports: dict[str, dict[str, Any]] = {}
    with authorised_derivation_window():
        for pair in checked.pairs:
            rows = request.read.rows_by_pair.get(pair)
            if rows is None:
                raise DerivationRouteError(
                    f"Track A derivation refused: the read carries no rows for {pair}, which "
                    "the grant names. A partial derivation reported as a whole one is how a "
                    "coverage figure stops meaning anything."
                )
            bars, report = DELEGATE(
                rows,
                pair=pair,
                expected_minutes=expected_minutes_for(calendar, pair),
            )
            bars_by_pair[pair] = bars
            gap_reports[pair] = report

    return DerivedM15(
        run_id=identity.run_id,
        operation=authorization.OPERATION_M15_DERIVATION,
        epoch=request.read.epoch,
        span_start_utc=request.read.span_start_utc,
        span_end_utc=request.read.span_end_utc,
        calendar_authority=calendar.authority,
        calendar_content_digest=calendar.content_digest,
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
    "expected_minutes_for",
]
