"""The **one** historical read route for Track A, and it does not read today.

§8.13.5 item 1 and the execution gate's item 4 require a single route, so there
is exactly one function here that could open a market-data file, and it refuses
before it does.  There is no second reader, no fallback, no "if the BA file is
missing, use mid" branch — that fallback exists in `train_lgbm_models.py` and is
one of the reasons a single route was asked for.

Five gates, in order, all fail-closed
-------------------------------------

1. **Isolation installed** — network, DB and broker guards are in place before
   anything is opened.
2. **Authorization** — a :class:`~scripts.m15_track_a.authorization.ReadGrant`
   covering *this* operation, span, pairs and timeframe.
3. **Span** — inside the DESIGN span, and outside the dead window.  Checked with
   the committed, reader-free ``no_overlap`` helpers, not with a local
   comparison: ``DEAD_START`` is exactly one second after ``DESIGN_END``, and
   §3.6 records that a ``<=``/``<`` slip pulls consumed-holdout bars into
   exploratory training.
4. **Seen-data declaration** — a prior write-ahead declaration covering the
   whole interval, *including the warm-up extension*.
5. **The read itself** — which is `NotImplementedError` today, deliberately.

Why the read is unimplemented rather than implemented-and-disabled
------------------------------------------------------------------

Because "implemented but gated" and "not implemented" fail differently under a
mistake.  A gated implementation runs the moment a gate is bypassed; an absent
implementation cannot.  The gates above are what a future implementing PR will
have to satisfy, and they are written and tested now so that PR adds a body and
not a policy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from scripts.m15_gate3a.no_overlap import (
    DESIGN_END,
    DESIGN_START,
    assert_design_bounds,
    assert_no_dead_window,
)
from scripts.m15_track_a import authorization, isolation, seen_ledger
from scripts.m15_track_a.identity import RunIdentity

_DATE_RE: Final[re.Pattern[str]] = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")

#: The one route's own name, so a containment audit can assert there is one.
ROUTE_ID: Final[str] = "track_a_r1_local_historical_read_v1"

#: The status a caller gets instead of data, today.
NOT_IMPLEMENTED_TOKEN: Final[str] = "TRACK_A_HISTORICAL_READ_NOT_IMPLEMENTED_NO_DATA_IS_READ"

#: The single admissible source. Named so a second source is a diff, not a flag.
SOURCE_DESCRIPTION: Final[str] = (
    "the committed 365d_BA M1 bid/ask files named by the PR-B.1 inventory, restricted "
    "to the DESIGN span"
)


class ReadRouteError(RuntimeError):
    """Raised when a Track A historical read is refused."""


@dataclass(frozen=True)
class ReadRequest:
    """What a caller wants to read, including the warm-up it will touch."""

    span_start_utc: str
    span_end_utc: str
    pairs: tuple[str, ...]
    timeframe: str
    warmup_extension_start_utc: str

    def __post_init__(self) -> None:
        if type(self.timeframe) is not str or not self.timeframe.strip():  # noqa: E721
            raise ReadRouteError("timeframe must be a non-empty plain str")
        for field, value in (
            ("span_start_utc", self.span_start_utc),
            ("span_end_utc", self.span_end_utc),
            ("warmup_extension_start_utc", self.warmup_extension_start_utc),
        ):
            # A zero-padded ISO date, checked here rather than three gates later.
            # The ordering test below and the coverage test in ``authorization``
            # are both string comparisons, and a string comparison of dates is
            # chronological only once both operands are known to be padded:
            # "2025-1-05" sorts *after* "2025-02-01" at index five.
            if type(value) is not str:  # noqa: E721
                raise ReadRouteError(f"{field} must be a plain str, got {type(value).__name__}")
            if not _DATE_RE.match(value):
                raise ReadRouteError(f"{field} must be an ISO UTC date YYYY-MM-DD, got {value!r}")
        if type(self.pairs) is not tuple or not self.pairs:
            raise ReadRouteError("pairs must be a non-empty tuple")
        for pair in self.pairs:
            # Pinned with ``type(...) is not str`` like every other object here.
            # A ``str`` subclass may lie through ``__hash__``/``__eq__`` while
            # holding different content, and both the grant's pair check and the
            # ledger's are set membership — so an unpinned element defeats the
            # pair scope of the authorisation and of the seen-data record at once.
            if type(pair) is not str or not pair.strip():  # noqa: E721
                raise ReadRouteError(f"malformed pair in request: {pair!r}")
        if self.span_start_utc > self.span_end_utc:
            raise ReadRouteError(
                f"span_start_utc {self.span_start_utc} is after span_end_utc {self.span_end_utc}"
            )
        if self.warmup_extension_start_utc > self.span_start_utc:
            raise ReadRouteError(
                "warmup_extension_start_utc must be at or before span_start_utc — a warm-up "
                "widens the interval a run touches, it never narrows it"
            )

    @property
    def touched_start_utc(self) -> str:
        """The earliest date the run will actually touch, warm-up included.

        This is what the seen-data ledger and the span check see. §8.11.4 rule 2:
        a bar read only to initialise an indicator is seen.
        """
        return self.warmup_extension_start_utc


def _as_instant(date_text: str, *, end_of_day: bool) -> datetime:
    try:
        day = datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError as exc:
        raise ReadRouteError(f"not an ISO UTC date: {date_text!r}") from exc
    if end_of_day:
        return day.replace(hour=23, minute=59, second=59, tzinfo=UTC)
    return day.replace(tzinfo=UTC)


def assert_span_admissible(request: ReadRequest) -> None:
    """Refuse unless the whole touched interval is inside DESIGN and clear of the dead window.

    Both checks come from the committed ``no_overlap`` module, which is
    reader-free and fail-closed. Its own docstring records that it checks
    **declared** metadata and opens no file — so this establishes that the
    *declaration* is admissible, and §8.11.12 F-5's trailing purge is what keeps
    the *labels* inside it. The two are different obligations and this is only
    the first.
    """
    lo = _as_instant(request.touched_start_utc, end_of_day=False)
    hi = _as_instant(request.span_end_utc, end_of_day=True)
    try:
        assert_design_bounds(lo, hi)
        assert_no_dead_window(lo, hi, role="design")
    except Exception as exc:  # no_overlap raises its own typed errors
        raise ReadRouteError(
            f"Track A read refused: the touched interval {request.touched_start_utc}.."
            f"{request.span_end_utc} is not admissible. DESIGN is "
            f"{DESIGN_START.date()}..{DESIGN_END.date()} and the dead window is excluded "
            f"from every role at every timeframe. ({exc})"
        ) from exc


def read_historical(
    request: ReadRequest,
    identity: RunIdentity,
    *,
    grant: Any = None,
) -> object:
    """The single Track A historical read route.  Refuses, then raises NotImplementedError.

    Every gate is checked **before** the unimplemented body, so a future
    implementing PR cannot accidentally satisfy the signature while skipping
    one: by the time control reaches the body, isolation is installed, a
    covering grant exists, the span is admissible and the interval was declared
    ahead of the read.
    """
    if not isolation.is_installed():
        raise ReadRouteError(
            "Track A read refused: isolation guards are not installed. Call "
            "scripts.m15_track_a.isolation.install_all() first — a read must not be the "
            "operation that discovers the network is reachable."
        )

    checked = authorization.require_authorization(
        grant,
        operation=authorization.OPERATION_HISTORICAL_READ,
        span_start_utc=request.touched_start_utc,
        span_end_utc=request.span_end_utc,
        pairs=request.pairs,
        timeframe=request.timeframe,
        identity=identity,
    )

    assert_span_admissible(request)

    seen_ledger.assert_declared(
        span_start_utc=request.touched_start_utc,
        span_end_utc=request.span_end_utc,
        pairs=request.pairs,
    )

    # The scope the run claimed, on the record, before anything is opened. An
    # approval that leaves no trace of the scope it was exercised at cannot be
    # audited against the approval document afterwards.
    seen_ledger.record_grant(checked, identity, route=ROUTE_ID)

    with isolation.gated_read_window():
        raise NotImplementedError(
            f"{NOT_IMPLEMENTED_TOKEN}: every gate passed and no data was read. The read "
            f"body is deliberately absent — route {ROUTE_ID!r} over {SOURCE_DESCRIPTION}. "
            f"A future implementing PR supplies it, for run {identity.run_id!r}, and adds "
            "nothing to the policy above."
        )


__all__ = [
    "NOT_IMPLEMENTED_TOKEN",
    "ROUTE_ID",
    "SOURCE_DESCRIPTION",
    "ReadRequest",
    "ReadRouteError",
    "assert_span_admissible",
    "read_historical",
]
