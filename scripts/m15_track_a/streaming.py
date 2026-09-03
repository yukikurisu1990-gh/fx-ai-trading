"""Bounded-memory execution for stage R1: the same route, a smaller footprint.

The blocker this closes
-----------------------

`read_historical` materialises every M1 row of every pair before the derivation
starts, and `run_r1` holds that read alive while `derive_m15` builds its own
validated copy. A review role measured ~880 bytes per retained row and
extrapolated the authorised corpus — 248 dates × 20 pairs — at roughly
**4.5–6 GB**. The number is not the whole problem. The seen-data declaration is
written **before** the read, is irreversible, and cannot be un-declared, so an
`OutOfMemoryError` would land *after* the corpus had already been spent.

Removing that risk before a first read is the point. Making R1 fast is not.

What changes, and what does not
-------------------------------

**Only the memory strategy.** Every semantic surface is the committed one,
reached through the committed callable:

* the read is `read_route.read_historical`, unmodified, called once per
  (pair, window) instead of once for everything;
* the derivation is `derivation.derive_m15`, unmodified, so `row_scope`,
  the grant∩request window, the exact-type pins, the ordering rule, the
  duplicate rule and the OOS / dead-window / forward refusals all apply per
  chunk exactly as they applied to the whole;
* the M15 bars are `aggregation.aggregate_m15`'s, reached only through
  `derive_m15`;
* the gap report is `aggregation._build_gap_report`'s, **called once per pair**
  on unioned inputs — not a second implementation of it, and not a merge of its
  outputs;
* the survey is `r1_survey.survey`, which still receives one whole `DerivedM15`.

There is no parallel research route and no fallback to a full-buffer path. The
formal R1 orchestrator calls this and nothing else calls it.

Why the boundaries cannot split a bucket
----------------------------------------

`ReadRequest` spans are **UTC dates**, so a window boundary is always midnight,
and midnight is always a multiple of `BUCKET_MINUTES` (15). A 15-minute bucket
therefore never straddles two chunks, and per-chunk aggregation is exactly
per-bucket aggregation of the same rows.

That is a property of the enumerator, so the enumerator is where it is enforced
(`iter_windows` refuses a non-integral day step) and the accumulator refuses a
bucket start it has already seen. A carry buffer would be the alternative; it is
not needed, and an unused carry is a second code path nobody exercises. If a
later change ever did split a bucket, `_PairAccumulator.absorb` raises rather
than emitting the same bucket twice as two incomplete bars.

What is bounded, and what is not — measured, not asserted
--------------------------------------------------------

Bounded, and independent of the corpus:

* **retained raw M1 rows** — one window of one pair, `window_days × 1440`
  rows at most. That is the ~880-bytes-per-row term, and the whole 4.5–6 GB.

Still proportional to the corpus, and deliberately so:

* the **M15 bars**, because `r1_survey.survey` takes one `DerivedM15` and its
  metric definitions are frozen. Bars are one-fifteenth of the rows;
* one pair's **observed minutes**, held only while that pair is in flight and
  released when its gap report is built.

`retained_raw_rows()` reports the running figure and
`peak_retained_raw_rows()` the high-water mark, so a test can bound it rather
than reason about it from the shape of the code.

The cost this pays
------------------

`read_historical` scans a source file from its first line and stops at the
window's end, so window *k* re-decodes the timestamps of the windows before it.
For the default 31-day window that is about 4.5× the single-pass decode work,
and it buys the memory bound without touching the audited read body or adding a
second reader. Production-grade performance is explicitly out of scope here.

Each window also appends its own grant-ledger row, so that ledger records the
authorisation once per window rather than once per run. The **seen-data**
declaration is untouched: it is still written once, write-ahead, by the
orchestrator, before anything is read.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Final

from scripts.m15_gate3a.aggregation import BUCKET_MINUTES
from scripts.m15_gate3a.incremental_m15 import IncrementalM15
from scripts.m15_track_a import derivation, read_route
from scripts.m15_track_a.identity import RunIdentity

#: The default window, in whole UTC days. Chosen for the memory/rescan
#: trade-off rather than derived from a contract: 31 days of one pair is about
#: 44 640 rows, and the re-decode cost over a 248-date corpus is about 4.5× a
#: single pass. It is a parameter, and the equivalence tests vary it.
DEFAULT_WINDOW_DAYS: Final[int] = 31

#: What this module establishes, and what it does not.
BOUNDED_MEMORY_STATUS: Final[str] = (
    "RAW_M1_RETENTION_BOUNDED_BY_ONE_WINDOW_OF_ONE_PAIR_M15_BARS_STILL_ACCUMULATE_FOR_THE_SURVEY"
)


class StreamingError(RuntimeError):
    """Raised when the bounded-memory route refuses."""


#: The high-water mark, process-wide, so a test can bound what the shape of the
#: code cannot prove. Reset by :func:`reset_retention_instrument`.
_retained_raw_rows: int = 0
_peak_retained_raw_rows: int = 0


def retained_raw_rows() -> int:
    """Raw M1 rows this module is holding right now."""
    return _retained_raw_rows


def peak_retained_raw_rows() -> int:
    """The most raw M1 rows held simultaneously since the last reset."""
    return _peak_retained_raw_rows


def reset_retention_instrument() -> None:
    """Zero the instrument. Test-facing; the route never calls it."""
    global _retained_raw_rows, _peak_retained_raw_rows
    _retained_raw_rows = 0
    _peak_retained_raw_rows = 0


def _hold(count: int) -> None:
    global _retained_raw_rows, _peak_retained_raw_rows
    _retained_raw_rows += count
    _peak_retained_raw_rows = max(_peak_retained_raw_rows, _retained_raw_rows)


def _release(count: int) -> None:
    global _retained_raw_rows
    _retained_raw_rows -= count


def iter_windows(
    span_start_utc: str, span_end_utc: str, *, window_days: int
) -> tuple[tuple[str, str], ...]:
    """Contiguous, non-overlapping UTC-date windows covering the span exactly.

    Whole days only, which is what keeps a 15-minute bucket inside one window:
    midnight is a multiple of `BUCKET_MINUTES`, so no bucket can straddle a
    boundary. A fractional step would break that, so it is refused rather than
    rounded.
    """
    if type(window_days) is not int or window_days < 1:  # noqa: E721
        raise StreamingError(f"window_days must be a positive int, got {window_days!r}")
    if 24 * 60 % BUCKET_MINUTES:  # pragma: no cover - 1440 % 15 == 0
        raise StreamingError(
            f"a day is not a whole number of {BUCKET_MINUTES}-minute buckets, so a day-aligned "
            "window boundary would split one"
        )
    try:
        start = date.fromisoformat(span_start_utc)
        end = date.fromisoformat(span_end_utc)
    except ValueError as exc:
        raise StreamingError(f"not an ISO UTC date: {exc}") from exc
    if start > end:
        raise StreamingError(f"empty span {span_start_utc}..{span_end_utc}")

    windows: list[tuple[str, str]] = []
    cursor = start
    while cursor <= end:
        stop = min(cursor + timedelta(days=window_days - 1), end)
        windows.append((cursor.isoformat(), stop.isoformat()))
        cursor = stop + timedelta(days=1)
    return tuple(windows)


def derive_streaming(
    request: read_route.ReadRequest,
    identity: RunIdentity,
    *,
    read_grant: Any,
    derivation_grant: Any,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> derivation.DerivedM15:
    """Read and derive the authorised span with bounded raw-row retention.

    Pair by pair, window by window: read one window of one pair, hand it to the
    committed derivation, keep the M15 bars, release the raw rows. The result is
    the `DerivedM15` a single full-buffer derivation would have produced.

    Every gate the non-streaming path runs still runs, per window, because it is
    the same `read_historical` and the same `derive_m15`. Nothing here relaxes a
    check, and there is no branch back to a full-buffer read.
    """
    if type(request) is not read_route.ReadRequest:  # noqa: E721
        raise StreamingError(
            f"request must be exactly a ReadRequest, not a {type(request).__name__}"
        )
    if type(identity) is not RunIdentity:  # noqa: E721
        raise StreamingError(
            f"identity must be exactly a RunIdentity, not a {type(identity).__name__}"
        )
    # **The request is snapshotted, and leaving it live was a reopened defect.**
    # `derive_m15` rebuilds its own inputs because an audit widened them "from a
    # plain sibling thread — no monkeypatch, no subclass" and got a `DerivedM15`
    # labelled `1970-01-01..2099-12-31` that `r1_survey` copied verbatim into the
    # R1 evidence record. This function read the span at `iter_windows` and again
    # at the `return`, so a role reproduced exactly that here. Every field is read
    # once, now, and nothing below touches the caller's object.
    request = read_route.ReadRequest(
        span_start_utc=request.span_start_utc,
        span_end_utc=request.span_end_utc,
        pairs=tuple(request.pairs),
        timeframe=request.timeframe,
        warmup_extension_start_utc=request.warmup_extension_start_utc,
    )
    windows = iter_windows(request.touched_start_utc, request.span_end_utc, window_days=window_days)
    # `iter_windows` is proven exact by test, and this checks it anyway. The
    # accumulator refuses an *overlap*; a role pointed out that a **gap** — a
    # window silently dropped — would just derive less and say nothing, which is
    # the quieter of the two failures and the one worth a backstop.
    if not windows or windows[0][0] != request.touched_start_utc:
        raise StreamingError(f"the windows do not start at {request.touched_start_utc}")
    if windows[-1][1] != request.span_end_utc:
        raise StreamingError(f"the windows do not reach {request.span_end_utc}")
    for (_, end), (start, _) in zip(windows, windows[1:], strict=False):
        if (date.fromisoformat(end) + timedelta(days=1)).isoformat() != start:
            raise StreamingError(
                f"the windows leave a gap between {end} and {start}: every authorised date must "
                "be covered exactly once"
            )

    bars_by_pair: dict[str, list[dict[str, Any]]] = {}
    gap_reports: dict[str, dict[str, Any]] = {}
    epoch: str | None = None

    for pair in request.pairs:
        accumulator = IncrementalM15(pair=pair)
        for lo, hi in windows:
            window_request = read_route.ReadRequest(
                span_start_utc=lo,
                span_end_utc=hi,
                pairs=(pair,),
                timeframe=request.timeframe,
                # No warm-up beyond the window: the run's warm-up is folded into
                # the first window by ``touched_start_utc`` above, and a window
                # may not reach outside the interval the grant covers.
                warmup_extension_start_utc=lo,
            )
            read = read_route.read_historical(window_request, identity, grant=read_grant)
            # The post-read verifications the orchestrator used to run on one
            # whole read, now run on **every window**. A mutation audit found
            # three of them unverified when they lived upstream; moving them
            # must not quietly drop them, and per window is strictly more often
            # than once.
            if type(read) is not read_route.HistoricalRead:  # noqa: E721
                raise StreamingError(
                    f"the read route returned a {type(read).__name__}, not a HistoricalRead"
                )
            if read.run_id != identity.run_id:
                raise StreamingError(
                    f"{pair} window {lo}..{hi}: the read records run {read.run_id!r} and this "
                    f"run is {identity.run_id!r}"
                )
            if read.timeframe != request.timeframe:
                raise StreamingError(
                    f"{pair} window {lo}..{hi}: the read returned {read.timeframe} bars, not "
                    f"{request.timeframe}"
                )
            if read.operation != derivation.authorization.OPERATION_HISTORICAL_READ:
                raise StreamingError(
                    f"{pair} window {lo}..{hi}: the read records operation {read.operation!r}"
                )
            # The window request names exactly one pair, so the read must carry
            # exactly that one. Checked **before** the empty-window skip below,
            # because a first drafting skipped straight past every derivation
            # gate when a window had no rows — and a role measured a read whose
            # batch carried an unauthorised pair being accepted there, where the
            # non-streaming reference refuses it. `row_scope`'s own commentary
            # is the rule: "unreachable today is a property of the callers, not
            # of the route."
            if set(read.rows_by_pair) != {pair}:
                raise StreamingError(
                    f"{pair} window {lo}..{hi}: the read carries "
                    f"{sorted(read.rows_by_pair)}, and this window authorises {pair} alone"
                )
            rows = read.rows_by_pair.get(pair, [])
            _hold(len(rows))
            try:
                if not rows:
                    # A window with no source minutes — a weekend, or a gap in
                    # the epoch. It contributes no bucket and no minute, so it is
                    # skipped rather than derived: ``row_scope`` refuses an empty
                    # batch, and refusing a legitimately empty window would make
                    # the streaming route reject corpora the reference accepts.
                    continue
                epoch = read.epoch if epoch is None else epoch
                if read.epoch != epoch:
                    raise StreamingError(
                        f"{pair}: window {lo}..{hi} reports epoch {read.epoch!r} and an earlier "
                        f"window reported {epoch!r}"
                    )
                derived = derivation.derive_m15(
                    derivation.DerivationRequest(read_request=window_request, read=read),
                    identity,
                    grant=derivation_grant,
                )
                if type(derived) is not derivation.DerivedM15:  # noqa: E721
                    raise StreamingError(
                        f"the derivation route returned a {type(derived).__name__}"
                    )
                # The accumulation lives in ``scripts/m15_gate3a`` beside the
                # aggregator whose intermediate quantities it combines: doing it
                # here would need four of that module's private helpers, and the
                # WP5 reader-freedom pin lists what Track A may import from that
                # package by name. Widening a committed prohibition to make a
                # memory optimisation possible is not a trade this makes.
                accumulator.absorb(derived.bars_by_pair[pair], derived.gap_reports[pair], rows)
            finally:
                # The raw rows go out of scope here whether the window derived or
                # raised. `finally`, not a happy-path release: a refused window
                # must not leave the instrument — or the memory — inflated.
                _release(len(rows))
                del rows
                del read
        bars, report = accumulator.result()
        bars_by_pair[pair] = bars
        gap_reports[pair] = report
        del accumulator

    # No `epoch is None` guard here, and that is deliberate rather than an
    # omission: a pair the authorisation names that carried no minute at all is
    # refused one level down, by `IncrementalM15.result()` — and by
    # `row_scope.rows_in_scope` in the non-streaming reference, which refuses an
    # empty batch for the same reason. A guard here would be unreachable, and
    # unreachable guards are how a route acquires a branch nobody exercises.
    assert epoch is not None  # noqa: S101 - every pair produced a result above

    return derivation.DerivedM15(
        run_id=identity.run_id,
        operation=derivation.authorization.OPERATION_M15_DERIVATION,
        epoch=epoch,
        span_start_utc=request.touched_start_utc,
        span_end_utc=request.span_end_utc,
        coverage_status=derivation.COVERAGE_STATUS,
        bars_by_pair=bars_by_pair,
        gap_reports=gap_reports,
    )


__all__ = [
    "BOUNDED_MEMORY_STATUS",
    "DEFAULT_WINDOW_DAYS",
    "StreamingError",
    "derive_streaming",
    "iter_windows",
    "peak_retained_raw_rows",
    "reset_retention_instrument",
    "retained_raw_rows",
]
