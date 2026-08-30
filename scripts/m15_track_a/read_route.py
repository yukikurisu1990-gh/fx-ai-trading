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
5. **The read itself** — the minimum that returns M1 rows and nothing else.

What the body does, and what it deliberately does not
-----------------------------------------------------

It resolves one committed 365d_BA M1 bid/ask file per requested pair, reads the
lines whose timestamp falls inside the **granted** span, and returns them in the
row shape ``scripts.m15_gate3a.aggregation.aggregate_m15`` consumes. That is
all. It does not aggregate, label, featurise, fit, score or write anything
except the ledger entries the gates above already require.

**Every bound it applies comes from the grant, not from its arguments.** The
request says what the caller wants; :func:`~scripts.m15_track_a.authorization.
require_authorization` has already refused anything the grant does not cover, and
the body then re-derives its per-pair file list and its timestamp window **from
the checked grant object**, so a request that somehow widened after the check
cannot widen the read.

**There is one source and no fallback.** ``train_lgbm_models.py`` has an "if the
BA file is missing, use mid" branch; that shape is why §8.13.5 asked for a single
route, and a missing file here is a **refusal**, never a substitution.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from scripts.m15_gate3a.no_overlap import (
    DESIGN_END,
    DESIGN_START,
    assert_design_bounds,
    assert_no_dead_window,
    is_dead_window_instant,
)
from scripts.m15_gate3a.pair_authority import canonical_pair
from scripts.m15_track_a import (
    OUTPUT_CLASSIFICATION,
    OUTPUT_CLASSIFICATION_SECONDARY,
    authorization,
    isolation,
    scratch,
    seen_ledger,
)
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

#: The committed epoch this route reads, and the only one it can name.
SOURCE_EPOCH: Final[str] = "365d_BA"

#: The one filename shape, as a template with no caller-supplied component.
SOURCE_FILENAME_TEMPLATE: Final[str] = "candles_{pair}_M1_{epoch}.jsonl"

#: Where those files live, relative to the repository root.
SOURCE_DIRECTORY_RELATIVE: Final[str] = "data"

#: The timeframe this route reads.  M15 does not exist until the derivation
#: runs, so a grant naming M15 does not describe anything this route can open.
SOURCE_TIMEFRAME: Final[str] = "M1"

#: The row keys ``aggregate_m15`` requires, in its own order: the bucket
#: timestamp plus per-side OHLC.  Named here so the read produces exactly the
#: shape the selected derivation route consumes and nothing more.
ROW_TIMESTAMP_KEY: Final[str] = "ts"
ROW_SIDE_KEYS: Final[tuple[str, ...]] = (
    "bid_o",
    "bid_h",
    "bid_l",
    "bid_c",
    "ask_o",
    "ask_h",
    "ask_l",
    "ask_c",
)

#: The source field each row key is read from.  ``time`` is OANDA's spelling.
_SOURCE_TIMESTAMP_FIELD: Final[str] = "time"


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


@dataclass(frozen=True)
class HistoricalRead:
    """What one Track A R1 read returns, and its classification.

    Deliberately not a bare dict: the classification travels with the data, so a
    downstream stage cannot pick up the rows without it.
    """

    run_id: str
    operation: str
    timeframe: str
    epoch: str
    span_start_utc: str
    span_end_utc: str
    rows_by_pair: dict[str, list[dict[str, Any]]]

    #: Every Track A output carries both labels (§8.11.2, §8.12.2).
    classification: str = OUTPUT_CLASSIFICATION
    classification_secondary: str = OUTPUT_CLASSIFICATION_SECONDARY

    @property
    def row_count(self) -> int:
        return sum(len(rows) for rows in self.rows_by_pair.values())

    def as_record(self) -> dict[str, Any]:
        """A summary safe to log.  Counts only — never a bar, never a price."""
        return {
            "run_id": self.run_id,
            "operation": self.operation,
            "timeframe": self.timeframe,
            "epoch": self.epoch,
            "span_start_utc": self.span_start_utc,
            "span_end_utc": self.span_end_utc,
            "rows_by_pair": {pair: len(rows) for pair, rows in self.rows_by_pair.items()},
            "row_count": self.row_count,
            "classification": self.classification,
            "classification_secondary": self.classification_secondary,
        }


def source_path_for(pair: str) -> Path:
    """The one committed file a pair's M1 bid/ask rows come from.

    A module constant template with no caller-supplied directory component, and
    the pair normalised through the committed authority first, so an unknown or
    non-canonical spelling fails closed before a path is built.
    """
    canonical = canonical_pair(pair)
    return (
        scratch.repo_root()
        / SOURCE_DIRECTORY_RELATIVE
        / SOURCE_FILENAME_TEMPLATE.format(pair=canonical, epoch=SOURCE_EPOCH)
    )


def _parse_source_timestamp(text: Any) -> datetime:
    """One OANDA timestamp, as a tz-aware UTC datetime, or refuse.

    ``fromisoformat`` handles the offset spellings; a naive value is refused
    rather than assumed UTC, because assuming it is how a host timezone
    reinterprets a bar.
    """
    if type(text) is not str:  # noqa: E721
        raise ReadRouteError(f"source timestamp must be a plain str, got {type(text).__name__}")
    candidate = text.replace("Z", "+00:00")
    # OANDA writes nanoseconds; ``fromisoformat`` accepts at most microseconds.
    if "." in candidate:
        head, _, tail = candidate.partition(".")
        digits = "".join(c for c in tail if c.isdigit())[:6]
        offset = tail[len(digits) :].lstrip("0123456789")
        candidate = f"{head}.{digits.ljust(6, '0')}{offset}"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ReadRouteError(f"source timestamp is not ISO-8601: {text!r}") from exc
    if parsed.utcoffset() is None:
        raise ReadRouteError(f"source timestamp is not timezone-aware: {text!r}")
    return parsed.astimezone(UTC)


def _row_from_source(raw: Any, *, pair: str, line_number: int) -> dict[str, Any]:
    """One source line as an ``aggregate_m15`` row, or refuse.

    Refuses rather than degrades, on the same footing as the aggregator it feeds:
    a missing key, a non-finite value or an unparseable timestamp is an error,
    never a dropped row and never a substituted default.
    """
    if not isinstance(raw, dict):
        raise ReadRouteError(f"{pair} line {line_number}: source row is not an object")
    row: dict[str, Any] = {
        ROW_TIMESTAMP_KEY: _parse_source_timestamp(raw.get(_SOURCE_TIMESTAMP_FIELD))
    }
    for key in ROW_SIDE_KEYS:
        if key not in raw:
            raise ReadRouteError(f"{pair} line {line_number}: source row missing {key!r}")
        try:
            value = float(raw[key])
        except (TypeError, ValueError) as exc:
            raise ReadRouteError(
                f"{pair} line {line_number}: {key!r} is not a finite number: {raw[key]!r}"
            ) from exc
        if value != value or value in (float("inf"), float("-inf")):
            raise ReadRouteError(f"{pair} line {line_number}: {key!r} is not finite")
        row[key] = value
    return row


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

    # Every bound below is taken from the **checked grant**, never from the
    # request. The request said what the caller wanted and the gate has already
    # refused anything wider; re-deriving from ``checked`` means a request object
    # mutated after the check cannot widen what is opened.
    if checked.timeframe != SOURCE_TIMEFRAME:
        raise ReadRouteError(
            f"Track A read refused: this route reads {SOURCE_TIMEFRAME} source bars, and the "
            f"grant names {checked.timeframe!r}. M15 does not exist until "
            "scripts.m15_track_a.derivation runs, which is a separate operation and a "
            "separate grant."
        )

    lo = _as_instant(checked.span_start_utc, end_of_day=False)
    hi = _as_instant(checked.span_end_utc, end_of_day=True)

    rows: dict[str, list[dict[str, Any]]] = {}
    with isolation.gated_read_window():
        for pair in checked.pairs:
            path = source_path_for(pair)
            if not path.is_file():
                # A refusal, not a substitution. The "if the BA file is missing,
                # use mid" fallback in train_lgbm_models.py is the shape §8.13.5
                # asked for a single route to remove.
                raise ReadRouteError(
                    f"Track A read refused: {path.name} is not present under "
                    f"{SOURCE_DIRECTORY_RELATIVE}/. This route has one source and no "
                    "fallback; a missing file is not a reason to read a different one."
                )
            collected: list[dict[str, Any]] = []
            with path.open(encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, 1):
                    if not line.strip():
                        continue
                    try:
                        raw = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ReadRouteError(
                            f"{pair} line {line_number}: source line is not JSON"
                        ) from exc
                    row = _row_from_source(raw, pair=pair, line_number=line_number)
                    timestamp = row[ROW_TIMESTAMP_KEY]
                    if timestamp < lo or timestamp > hi:
                        # Outside the granted span. Skipped rather than refused:
                        # the file spans more than the grant does, and reading
                        # past the grant is the thing this line prevents.
                        continue
                    if is_dead_window_instant(timestamp):
                        # Belt and braces. ``assert_span_admissible`` already
                        # refused a declared interval that touches the dead
                        # window; this refuses a *row* that does, whatever the
                        # declaration said, because no_overlap checks metadata
                        # and cannot see bytes.
                        raise ReadRouteError(
                            f"Track A read refused: {pair} carries a row at "
                            f"{timestamp.isoformat()}, inside the consumed dead window."
                        )
                    collected.append(row)
            rows[canonical_pair(pair)] = collected

    return HistoricalRead(
        run_id=identity.run_id,
        operation=authorization.OPERATION_HISTORICAL_READ,
        timeframe=SOURCE_TIMEFRAME,
        epoch=SOURCE_EPOCH,
        span_start_utc=checked.span_start_utc,
        span_end_utc=checked.span_end_utc,
        rows_by_pair=rows,
    )


__all__ = [
    "ROUTE_ID",
    "ROW_SIDE_KEYS",
    "ROW_TIMESTAMP_KEY",
    "SOURCE_DESCRIPTION",
    "SOURCE_DIRECTORY_RELATIVE",
    "SOURCE_EPOCH",
    "SOURCE_FILENAME_TEMPLATE",
    "SOURCE_TIMEFRAME",
    "HistoricalRead",
    "ReadRequest",
    "ReadRouteError",
    "assert_span_admissible",
    "read_historical",
    "source_path_for",
]
