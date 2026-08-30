"""The **one** historical read route for Track A.

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

It resolves one committed 365d_BA M1 bid/ask file per pair, reads the lines whose
timestamp falls inside the window, and returns them in the row shape
``scripts.m15_gate3a.aggregation.aggregate_m15`` consumes. That is all. It does
not aggregate, label, featurise, fit, score or write anything except the ledger
entries the gates above already require.

**Every bound it applies is the narrowest of the three that constrain it.** An
earlier drafting took the window and the pair list from the **grant** alone,
reasoning that a request mutated after the gate could not then widen the read.
True, and it inverted the safety: coverage is *containment*, so a grant may be
**wider** than the request, and the wider part passed neither
``assert_span_admissible`` nor the seen-data declaration. Two review roles
reproduced it independently -- a one-month declaration with a full-design-span
grant returned ten months, and a one-pair declaration with a two-pair grant
opened two files. So the window and the pair list are now the **intersection**
of grant and request: no wider than the grant, so no unauthorised byte; no wider
than the request, so a mutated request cannot widen it; and therefore no wider
than what was declared.

**What it reads is bounded, and the bound is stated exactly.** The source is one
JSONL file per pair covering the whole epoch, and there is no index, so finding
the window means scanning. Two properties keep that scan honest, and neither is
an assumption about the data:

* price fields are materialised **only** for rows inside the window -- every
  other line is decoded for its timestamp and discarded;
* the scan **stops** at the first row past the window, and the source is
  required to be strictly increasing in time for that stop to be sound. A source
  that is not refuses the read; it never returns a silently truncated one.

Together those mean the consumed dead window and the forward epoch -- which sit
at the *end* of the file, after every admissible window -- are never reached.
What the scan does touch is stated without softening:
`SCAN_DECODES_TIMESTAMPS_OF_EARLIER_ROWS_IN_THE_SAME_FILE`.

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

from scripts.m15_gate3a.derivation_containment import (
    mark_real_rows_handed_out,
    stamp_real_provenance,
)
from scripts.m15_gate3a.no_overlap import (
    DESIGN_END,
    DESIGN_START,
    FORWARD_FLOOR,
    assert_design_bounds,
    assert_no_dead_window,
    is_dead_window_instant,
)
from scripts.m15_gate3a.pair_authority import PairAuthorityError, canonical_pair
from scripts.m15_gate3a.path_authority import PathAuthorityError, is_within
from scripts.m15_track_a import (
    OUTPUT_CLASSIFICATION,
    OUTPUT_CLASSIFICATION_SECONDARY,
    authorization,
    isolation,
    scratch,
    seen_ledger,
)
from scripts.m15_track_a.identity import RunIdentity
from scripts.m15_track_a.oos_slice import OosSliceError, assert_clear_of_slice

_DATE_RE: Final[re.Pattern[str]] = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")

#: The one route's own name, so a containment audit can assert there is one.
ROUTE_ID: Final[str] = "track_a_r1_local_historical_read_v1"

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
#: What the scan touches beyond the window, stated rather than softened.  See
#: the module docstring: reaching row *n* in a JSONL file means decoding rows
#: 1..n-1, so the timestamps of earlier rows in the same file are decoded. Their
#: prices are not materialised, and nothing after the window is reached at all.
SCAN_DISCLOSURE: Final[str] = "SCAN_DECODES_TIMESTAMPS_OF_EARLIER_ROWS_IN_THE_SAME_FILE"

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


def assert_development_only(request: ReadRequest) -> None:
    """Refuse a development read that reaches into the `EXPLORATORY_OOS_SLICE`.

    ``assert_span_admissible`` bounds the interval at the design span and clears
    it of the dead window. Neither of those sees the slice, because the slice is
    *inside* the design span — which is exactly why R-2 needed its boundary
    recorded before R1, and why this route stayed blocked until it was.

    The refusal is on the **touched** interval, warm-up included. A warm-up
    extension that reaches forward into the slice reads the slice; that it was
    only meant to prime an indicator changes nothing about which bars were
    opened. Refused rather than trimmed: silently shortening a read leaves the
    caller believing it got what it asked for.
    """
    try:
        assert_clear_of_slice(
            _as_instant(request.touched_start_utc, end_of_day=False),
            _as_instant(request.span_end_utc, end_of_day=True),
            what="Track A development read refused",
        )
    except OosSliceError as exc:
        raise ReadRouteError(str(exc)) from exc


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


def is_committed_source(path: Path) -> bool:
    """Whether a resolved source path sits under the committed data root.

    The one place "is this real historical data?" is decided. It is a **path**
    question rather than a caller-supplied flag, because a flag is something the
    caller sets and the whole point of the containment is not to depend on the
    caller. ``path_authority.is_within`` is the committed answer to Windows path
    aliasing — UNC spellings, junctions and 8.3 short names — so a source
    reached by an alias of ``data/`` is still real.
    """
    try:
        return is_within(path, scratch.repo_root() / SOURCE_DIRECTORY_RELATIVE)
    except PathAuthorityError:
        # Unresolvable is treated as **real**. Fail-closed: the consequence of
        # guessing "synthetic" is an unlatched process holding real rows.
        return True


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


def _source_timestamp(raw: Any, *, pair: str, line_number: int) -> datetime:
    """The timestamp of one source line, and nothing else from it.

    Split out from :func:`_row_from_source` so the span filter can run **before**
    the prices are materialised. A review role measured the earlier ordering: a
    malformed row outside the granted span still failed the read, which proved
    that every line in the file was being parsed in full. Prices outside the
    window are now never turned into floats.
    """
    if not isinstance(raw, dict):
        raise ReadRouteError(f"{pair} line {line_number}: source row is not an object")
    return _parse_source_timestamp(raw.get(_SOURCE_TIMESTAMP_FIELD))


def _pairs_to_read(*, granted: tuple[str, ...], requested: tuple[str, ...]) -> tuple[str, ...]:
    """The canonical pairs this read may open: the intersection, narrowest wins.

    Refuses rather than narrows. A requested pair the grant does not name is a
    contradiction -- ``grant_covers`` passed, so the request changed since -- and
    silently dropping it would hide that. Two spellings of one pair are refused
    for the same reason: folding them into one key loses the caller's meaning.
    """
    try:
        granted_canonical = frozenset(canonical_pair(pair) for pair in granted)
        requested_canonical = tuple(canonical_pair(pair) for pair in requested)
    except PairAuthorityError as exc:
        raise ReadRouteError(f"Track A read refused: {exc}") from exc
    seen: list[str] = []
    for pair in requested_canonical:
        if pair in seen:
            raise ReadRouteError(
                f"Track A read refused: {pair} is named twice in the request. Two spellings "
                "of one pair would fold into one result key, so the request is ambiguous."
            )
        if pair not in granted_canonical:
            raise ReadRouteError(
                f"Track A read refused: {pair} is not in the grant, although the coverage "
                "check passed. The request changed after it was checked."
            )
        seen.append(pair)
    if not seen:
        raise ReadRouteError("Track A read refused: the request names no pair to read.")
    return tuple(seen)


def _row_from_source(
    raw: Any, timestamp: datetime, *, pair: str, line_number: int
) -> dict[str, Any]:
    """One source line as an ``aggregate_m15`` row, or refuse.

    Refuses rather than degrades, on the same footing as the aggregator it feeds:
    a missing key or a non-finite value is an error, never a dropped row and
    never a substituted default. The timestamp is passed in because
    :func:`_source_timestamp` has already parsed it to decide this row is inside
    the window.
    """
    row: dict[str, Any] = {ROW_TIMESTAMP_KEY: timestamp}
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
    """The single Track A historical read route.

    Every gate is checked **before** the body, so by the time a byte is opened
    isolation is installed, a covering grant exists, the span is admissible, the
    interval was declared ahead of the read, and the grant's exercised scope is
    on the record.

    Returns a :class:`HistoricalRead`. Refuses — never degrades, never
    substitutes a second source — on any of: no grant, a grant that does not
    cover the request, an approved head that is not this run's, a timeframe this
    route does not read, an inadmissible span, an undeclared interval, a missing
    source file, a malformed row, or a row inside the dead window or at the
    forward-epoch floor.
    """
    if type(request) is not ReadRequest:
        # Pinned exactly, like the grant. A subclass can answer any field with a
        # property, and this route reads ``span_end_utc`` more than once — at
        # the admissibility gate, at the slice gate, and again when the window
        # is computed. A review role built exactly that: a subclass answering
        # honestly six times and then widening, which passed every gate and
        # returned the whole quarantined slice.
        raise ReadRouteError(
            f"Track A read refused: request must be exactly a ReadRequest, not a "
            f"{type(request).__name__}. A subclass can answer a field differently each "
            "time it is read, and the gates would then be checking a different request "
            "from the one that is executed."
        )
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
    assert_development_only(request)

    seen_ledger.assert_declared(
        span_start_utc=request.touched_start_utc,
        span_end_utc=request.span_end_utc,
        pairs=request.pairs,
    )

    # The scope the run claimed, on the record, before anything is opened. An
    # approval that leaves no trace of the scope it was exercised at cannot be
    # audited against the approval document afterwards.
    seen_ledger.record_grant(checked, identity, route=ROUTE_ID)

    # Every bound below is the **narrowest** of the three that constrain this
    # read, on both axes, and that is a correction of an earlier drafting.
    #
    # That drafting took the window and the pair list from the **grant** alone,
    # reasoning that a request mutated after the gate could not then widen the
    # read. True, and it inverted the safety: coverage is *containment*, so a
    # grant may be **wider** than the request, and the wider part was never
    # declared to the seen-data ledger and never passed
    # ``assert_span_admissible``. Two review roles reproduced it independently:
    # a May declaration with a full-design-span grant returned September and
    # February rows, and a one-pair declaration with a two-pair grant opened two
    # files. Ten months and a second pair would have become
    # `EXPLORATORY_SEEN_DATA` with one month and one pair on the record —
    # and seen-data is irreversible, so an under-record cannot be repaired.
    #
    # The intersection is no wider than the grant (so no unauthorised byte), no
    # wider than the request (so a mutated request cannot widen it), and
    # therefore no wider than the declaration (which was checked against the
    # request). Narrowest wins.
    if checked.timeframe != SOURCE_TIMEFRAME:
        raise ReadRouteError(
            f"Track A read refused: this route reads {SOURCE_TIMEFRAME} source bars, and the "
            f"grant names {checked.timeframe!r}. M15 does not exist until "
            "scripts.m15_track_a.derivation runs, which is a separate operation and a "
            "separate grant."
        )

    lo = max(
        _as_instant(checked.span_start_utc, end_of_day=False),
        _as_instant(request.touched_start_utc, end_of_day=False),
    )
    hi = min(
        _as_instant(checked.span_end_utc, end_of_day=True),
        _as_instant(request.span_end_utc, end_of_day=True),
    )
    if hi < lo:
        raise ReadRouteError(
            "Track A read refused: the grant and the request do not overlap in time, so "
            "there is no interval that is both authorised and declared."
        )
    # The gates above checked *the request's* strings. This checks the interval
    # that will actually be opened, after the intersection and after every field
    # has stopped being consulted. Belt and braces against the same shape twice
    # over: a request whose fields change between reads, and a grant whose span
    # runs past the ruled development corpus.
    try:
        assert_clear_of_slice(lo, hi, what="Track A development read refused (window)")
    except OosSliceError as exc:
        raise ReadRouteError(str(exc)) from exc
    pairs_to_read = _pairs_to_read(granted=checked.pairs, requested=request.pairs)

    rows: dict[str, list[dict[str, Any]]] = {}
    with isolation.gated_read_window():
        for pair in pairs_to_read:
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
            # Provenance is decided from **where the file is**, not from a
            # caller's word for it: a source under the committed data root is
            # real historical data, a source in a temporary tree is not. That is
            # why every existing synthetic test keeps working unchanged while a
            # genuine read latches the process.
            real = is_committed_source(path)
            collected: list[dict[str, Any]] = []
            previous = None
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
                    # The timestamp only. The prices of a row outside the window
                    # are never materialised — a review role measured the earlier
                    # ordering by putting a malformed row outside the span and
                    # watching an inside-the-span read fail on it.
                    timestamp = _source_timestamp(raw, pair=pair, line_number=line_number)
                    if previous is not None and timestamp <= previous:
                        # The stop below is only sound on an ordered source, so
                        # the order is **enforced**, not assumed. Refusing here
                        # is the difference between "this source is not what the
                        # route expects" and a silently truncated read.
                        raise ReadRouteError(
                            f"Track A read refused: {pair} line {line_number} is at "
                            f"{timestamp.isoformat()}, not after the previous row. This route "
                            "reads a strictly increasing source; it will not guess the order."
                        )
                    previous = timestamp
                    if timestamp > hi:
                        # Stop, rather than skip to the end of the file. The
                        # consumed dead window and the forward epoch sit after
                        # every admissible window, so stopping here is what keeps
                        # them unread — relying on the file not containing them
                        # would be a property of the data, not of the route.
                        break
                    if timestamp < lo:
                        # Before the window. Its prices are not decoded; its
                        # timestamp is, and SCAN_DISCLOSURE says so.
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
                    if timestamp >= FORWARD_FLOOR:
                        # The forward epoch is Track B's confirmation dataset.
                        # The committed 365d_BA files end before it, so today
                        # this can only fire on a file that is not the declared
                        # epoch — which is exactly when it should. A review role
                        # noted that relying on the file's contents is an
                        # accident of the data, not a property of the route.
                        raise ReadRouteError(
                            f"Track A read refused: {pair} carries a row at "
                            f"{timestamp.isoformat()}, at or after the forward-epoch floor "
                            f"{FORWARD_FLOOR.date()}. That span is Track B's confirmation "
                            "dataset and no Track A operation may touch it."
                        )
                    built = _row_from_source(raw, timestamp, pair=pair, line_number=line_number)
                    if real:
                        stamp_real_provenance(built)
                    collected.append(built)
            rows[pair] = collected
            if real:
                # Latched **after** the rows exist and before they are returned,
                # so a caller cannot receive real rows without the latch being
                # set. It is one-way; there is no reset, because a reset is the
                # bypass this closes.
                mark_real_rows_handed_out()

    return HistoricalRead(
        run_id=identity.run_id,
        operation=authorization.OPERATION_HISTORICAL_READ,
        timeframe=SOURCE_TIMEFRAME,
        epoch=SOURCE_EPOCH,
        span_start_utc=lo.date().isoformat(),
        span_end_utc=hi.date().isoformat(),
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
    "assert_development_only",
    "assert_span_admissible",
    "read_historical",
    "source_path_for",
]
