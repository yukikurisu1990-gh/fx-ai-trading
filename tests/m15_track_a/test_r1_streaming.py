"""The bounded-memory route, against the full-buffer route it replaces.

`TRACK_A_R1_STREAMING_SEMANTIC_EQUIVALENCE_PASSED` is what this file
establishes.

**No test here touches real market data.** Every case writes synthetic JSONL
into a temporary tree and repoints `source_path_for` at it; `data/` is never
opened, and the scratch and ledger roots are redirected so no real seen-data
entry is created.

The reference, and why it lives here
------------------------------------

"Full-buffer semantics" is one `read_historical` over the whole span followed by
one `derive_m15` over everything it returned — what `run_r1` did before this
change. That composition is **not** kept in production: §6 forbids a parallel
route and a fallback. It is reconstructed here, from the same two committed
callables, purely as the thing the streaming route must equal. `_reference`
below is that reconstruction and nothing else calls it.

A note on the fingerprint, and on what is not stubbed
-----------------------------------------------------

`require_authorization` measures `implementation_fingerprint()` on **every**
check — deliberately, so a mid-run source change is caught — and the streaming
route checks once per read and once per derivation, per window.

The figures, measured rather than estimated, because a human authorises a run on
them. One `implementation_fingerprint()` is **412 ms** over **32** files. The
two-day fixture below measures it **181** times (most windows are empty and read
without deriving) — about 75 s. A **full corpus**, where every 31-day window of
every pair carries rows, measures it **321** times: about **132 s**. An earlier
drafting said "181 times … about 48 seconds", which was the fixture's number
presented as the corpus's.

`fast_fingerprint` memoises **the real measured value** for the duration of a
case: same number, computed once. It does not stub the check, the comparison, or
any refusal — a grant bound to a different value is still refused, and the
negative cases prove it. `test_the_fingerprint_is_measured_at_every_check_not_cached`
runs unmemoised and asserts the per-check property the memoisation would
otherwise hide.
"""

from __future__ import annotations

import ast
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_track_a import (
    authorization,
    containment,
    derivation,
    identity,
    isolation,
    r1_survey,
    read_route,
    scratch,
    seen_ledger,
    streaming,
)

EPOCH = read_route.SOURCE_EPOCH
#: A short span and three pairs for the equivalence work: the property under
#: test is "chunked == whole", and it does not get truer with twenty pairs.
#: The orchestrator-level case below runs the full authorised corpus.
PAIRS = ("EUR_USD", "USD_JPY", "GBP_USD")
SPAN_START = "2025-05-05"  # a Monday
#: A Tuesday, so the weekend gap falls in the **middle** of the span and the
#: last date carries rows. It ended on the Sunday for a draft, and a role showed
#: what that hid: an enumerator that dropped the span's final date changed no bar,
#: because that date had none. One assertion caught it; no equivalence case did.
SPAN_END = "2025-05-13"
APPROVED_SHA = "a" * 40


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("track_a_scratch", "data"):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(scratch, "scratch_root", lambda: tmp_path / "track_a_scratch")
    monkeypatch.setattr(
        read_route,
        "source_path_for",
        lambda pair: (
            tmp_path / "data" / read_route.SOURCE_FILENAME_TEMPLATE.format(pair=pair, epoch=EPOCH)
        ),
    )
    return tmp_path


@pytest.fixture
def fast_fingerprint(monkeypatch: pytest.MonkeyPatch) -> str:
    """The real measured value, computed once. See the module docstring."""
    measured = containment.implementation_fingerprint()
    monkeypatch.setattr(containment, "implementation_fingerprint", lambda: measured)
    return measured


@pytest.fixture
def guards_installed() -> object:
    isolation.install_all()
    try:
        yield
    finally:
        isolation.uninstall_all()


def _write_minutes(
    sandbox: Path,
    pair: str,
    *,
    start: str,
    end: str,
    skip_weekends: bool = True,
    hole_every: int = 0,
) -> int:
    """One M1 row per minute, in the committed shape. Returns the row count.

    Weekends are omitted by default so the corpus has a real gap: a window that
    lands wholly inside one is the case the streaming route has to skip rather
    than refuse, and the reference has to agree about.

    `hole_every` drops one minute in every N, which leaves **incomplete buckets**.
    A role found that without it every bucket was complete, `total_missing` was 0
    in every window, and a mutant replacing the accumulator's `+=` with `=`
    survived the entire suite — the fixture could not see an accumulation bug
    because it never accumulated anything but zero.
    """
    path = sandbox / "data" / read_route.SOURCE_FILENAME_TEMPLATE.format(pair=pair, epoch=EPOCH)
    jpy = pair.endswith("_JPY")
    base = 150.0 if jpy else 1.1000
    tick = 0.01 if jpy else 0.0001
    moment = datetime.fromisoformat(start).replace(tzinfo=UTC)
    stop = datetime.fromisoformat(end).replace(tzinfo=UTC) + timedelta(days=1)
    written = 0
    index = 0
    with path.open("w", encoding="utf-8") as handle:
        while moment < stop:
            if skip_weekends and moment.weekday() >= 5:
                moment += timedelta(minutes=1)
                continue
            if hole_every and index % hole_every == hole_every - 1:
                moment += timedelta(minutes=1)
                index += 1
                continue
            mid = base + ((index % 40) - 20) * tick
            half = tick
            handle.write(
                json.dumps(
                    {
                        "time": moment.isoformat().replace("+00:00", "Z"),
                        "bid_o": mid - half,
                        "bid_h": mid - half + 3 * tick,
                        "bid_l": mid - half - 3 * tick,
                        "bid_c": mid - half + tick,
                        "ask_o": mid + half,
                        "ask_h": mid + half + 3 * tick,
                        "ask_l": mid + half - 3 * tick,
                        "ask_c": mid + half + tick,
                    }
                )
                + "\n"
            )
            moment += timedelta(minutes=1)
            index += 1
            written += 1
    return written


@pytest.fixture
def corpus(sandbox: Path) -> dict[str, int]:
    """Weekend gap in the middle, holes inside buckets, rows on the last date."""
    return {
        pair: _write_minutes(sandbox, pair, start=SPAN_START, end=SPAN_END, hole_every=23)
        for pair in PAIRS
    }


def _run(**overrides: Any) -> identity.RunIdentity:
    fields: dict[str, Any] = {
        "run_id": "r1-streaming-equivalence",
        "code_sha": APPROVED_SHA,
        "calendar_semantics": identity.CALENDAR_UTC_DATES_NO_MARKET_HOURS,
        "started_at_utc": "2026-09-03T00:00:00Z",
    }
    fields.update(overrides)
    return identity.RunIdentity(**fields)


def _grant_for(operation: str, request: read_route.ReadRequest) -> Any:
    """A grant whose scope is exactly the request's, so a widened test span
    cannot pass because the grant happened to be wider."""
    return _grant(
        operation,
        pairs=request.pairs,
        span_start_utc=request.touched_start_utc,
        span_end_utc=request.span_end_utc,
    )


def _grant(operation: str, *, pairs: tuple[str, ...] = PAIRS, **overrides: Any) -> Any:
    fields: dict[str, Any] = {
        "operation": operation,
        "span_start_utc": SPAN_START,
        "span_end_utc": SPAN_END,
        "pairs": pairs,
        "timeframe": "M1",
        "approved_head_sha": APPROVED_SHA,
        "approved_implementation_fingerprint": containment.implementation_fingerprint(),
        "approver_record": "synthetic equivalence probe, not a recorded approval",
    }
    fields.update(overrides)
    return authorization.ReadGrant(**fields)


def _request(**overrides: Any) -> read_route.ReadRequest:
    fields: dict[str, Any] = {
        "span_start_utc": SPAN_START,
        "span_end_utc": SPAN_END,
        "pairs": PAIRS,
        "timeframe": "M1",
        "warmup_extension_start_utc": SPAN_START,
    }
    fields.update(overrides)
    return read_route.ReadRequest(**fields)


def _declare(run: identity.RunIdentity, request: read_route.ReadRequest) -> None:
    seen_ledger.declare(
        seen_ledger.SeenDeclaration(
            run_id=run.run_id,
            span_start_utc=request.touched_start_utc,
            span_end_utc=request.span_end_utc,
            pairs=request.pairs,
            timeframe=request.timeframe,
            purpose="synthetic streaming-equivalence probe",
        ),
        run,
    )


def _reference(request: read_route.ReadRequest, run: identity.RunIdentity) -> derivation.DerivedM15:
    """Full-buffer semantics: one read, one derivation. Test-only, by design."""
    read = read_route.read_historical(
        request, run, grant=_grant_for(authorization.OPERATION_HISTORICAL_READ, request)
    )
    return derivation.derive_m15(
        derivation.DerivationRequest(read_request=request, read=read),
        run,
        grant=_grant_for(authorization.OPERATION_M15_DERIVATION, request),
    )


def _streamed(
    request: read_route.ReadRequest, run: identity.RunIdentity, *, window_days: int
) -> derivation.DerivedM15:
    return streaming.derive_streaming(
        request,
        run,
        read_grant=_grant_for(authorization.OPERATION_HISTORICAL_READ, request),
        derivation_grant=_grant_for(authorization.OPERATION_M15_DERIVATION, request),
        window_days=window_days,
    )


def _both(
    request: read_route.ReadRequest, *, window_days: int
) -> tuple[derivation.DerivedM15, derivation.DerivedM15]:
    run = _run()
    _declare(run, request)
    return _reference(request, run), _streamed(request, run, window_days=window_days)


# ---------------------------------------------------------------------------
# Equivalence
# ---------------------------------------------------------------------------


def _assert_derivations_identical(
    reference: derivation.DerivedM15, streamed: derivation.DerivedM15
) -> None:
    """Every decision-bearing field, compared exactly.

    No tolerance is introduced. The bars are built by the same
    `aggregate_m15` from the same rows, so identical inputs give identical
    floats; a tolerance here would be a new contract term invented to hide a
    difference that should not exist.
    """
    assert streamed.epoch == reference.epoch
    assert streamed.span_start_utc == reference.span_start_utc
    assert streamed.span_end_utc == reference.span_end_utc
    assert streamed.coverage_status == reference.coverage_status
    assert streamed.classification == reference.classification
    assert streamed.classification_secondary == reference.classification_secondary
    assert streamed.run_id == reference.run_id
    assert streamed.operation == reference.operation
    #: pair ordering, not just pair membership
    assert list(streamed.bars_by_pair) == list(reference.bars_by_pair)
    assert list(streamed.gap_reports) == list(reference.gap_reports)
    for pair in reference.bars_by_pair:
        assert streamed.bars_by_pair[pair] == reference.bars_by_pair[pair], pair
        assert streamed.gap_reports[pair] == reference.gap_reports[pair], pair
    assert streamed.bar_count == reference.bar_count
    assert streamed.as_record() == reference.as_record()


@pytest.mark.parametrize("window_days", [1, 2, 3, 4, 5, 6, 7, 8, 13, 100])
def test_the_streamed_derivation_equals_the_full_buffer_one(
    corpus: dict[str, int], guards_installed: object, fast_fingerprint: str, window_days: int
) -> None:
    """A. reference vs B. streaming, over many window sizes.

    `window_days=100` exceeds the span, so the whole thing is one window and the
    streaming route degenerates to per-pair full buffering — which must also
    agree. `window_days=1` is the other end: a window per UTC day, including two
    that are wholly weekend and carry no row at all.
    """
    reference, streamed = _both(_request(), window_days=window_days)
    _assert_derivations_identical(reference, streamed)


@pytest.mark.parametrize("window_days", [1, 3, 7])
def test_the_r1_survey_is_identical_on_both_routes(
    corpus: dict[str, int], guards_installed: object, fast_fingerprint: str, window_days: int
) -> None:
    """The whole survey record: schema, coverage, spreads, cost, eligibility, ratios."""
    reference, streamed = _both(_request(), window_days=window_days)
    left = r1_survey.survey(reference, containment_status=containment.STATUS_CONTAINED, breadth_k=0)
    right = r1_survey.survey(streamed, containment_status=containment.STATUS_CONTAINED, breadth_k=0)
    assert right.as_record() == left.as_record()
    assert right.pairs == left.pairs
    assert right.required_outputs == left.required_outputs


def test_the_equivalence_corpus_actually_exercises_the_accumulators(
    corpus: dict[str, int], guards_installed: object, fast_fingerprint: str
) -> None:
    """A fixture that never accumulates anything but zero proves nothing.

    A role replaced `total_missing +=` with `=` in the accumulator and it
    survived the whole suite, because every bucket in the old fixture was
    complete. This asserts the corpus has incomplete buckets, that
    `total_missing` is non-zero, and that it differs between a one-window and a
    many-window run only by being *equal* — i.e. the sum is really being taken.
    """
    reference, streamed = _both(_request(), window_days=2)
    for pair in reference.gap_reports:
        missing = reference.gap_reports[pair]["total_missing_source_minutes_within_emitted_buckets"]
        assert missing > 0, f"{pair}: the corpus has no incomplete bucket to accumulate"
        assert (
            streamed.gap_reports[pair]["total_missing_source_minutes_within_emitted_buckets"]
            == missing
        ), pair
        assert reference.gap_reports[pair]["incomplete_bucket_count"] > 0, pair
        assert reference.gap_reports[pair]["rows_ingested"] > 0, pair
        assert (
            streamed.gap_reports[pair]["rows_ingested"]
            == (reference.gap_reports[pair]["rows_ingested"])
        ), pair


def test_an_empty_window_still_checks_the_batch_it_was_handed(
    corpus: dict[str, int],
    guards_installed: object,
    fast_fingerprint: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The gate a first drafting skipped past when a window had no rows.

    `if not rows: continue` meant an empty window ran **no** derivation gate, so
    a read whose batch carried an unauthorised pair was accepted where the
    non-streaming reference refuses it. Unreachable through the committed read
    route — which is exactly what `row_scope`'s own commentary says is not a
    reason to leave it.
    """
    real = read_route.read_historical

    def smuggling(*a: Any, **kw: Any) -> Any:
        read = real(*a, **kw)
        if any(read.rows_by_pair.values()):
            return read
        return read_route.HistoricalRead(
            run_id=read.run_id,
            operation=read.operation,
            timeframe=read.timeframe,
            epoch=read.epoch,
            span_start_utc=read.span_start_utc,
            span_end_utc=read.span_end_utc,
            rows_by_pair={**read.rows_by_pair, "USD_CHF": []},
        )

    monkeypatch.setattr(read_route, "read_historical", smuggling)
    request = _request()
    run = _run()
    _declare(run, request)
    with pytest.raises(streaming.StreamingError, match="authorises"):
        _streamed(request, run, window_days=1)


def test_a_gap_in_the_window_enumeration_is_refused(
    corpus: dict[str, int],
    guards_installed: object,
    fast_fingerprint: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The accumulator refuses an overlap; a dropped window is the quieter failure.

    A role patched `iter_windows` to skip one day and got a silently shorter
    derivation with no refusal at all.
    """
    real = streaming.iter_windows

    def with_a_gap(*a: Any, **kw: Any) -> Any:
        windows = real(*a, **kw)
        return windows[:1] + windows[2:]

    monkeypatch.setattr(streaming, "iter_windows", with_a_gap)
    request = _request()
    run = _run()
    _declare(run, request)
    with pytest.raises(streaming.StreamingError, match="gap between"):
        _streamed(request, run, window_days=1)


def test_eligibility_and_partial_buckets_survive_chunking(
    corpus: dict[str, int], guards_installed: object, fast_fingerprint: str
) -> None:
    """`complete_bucket` is the flag a split bucket would corrupt first.

    A bucket split across two windows would emit twice, each time with fewer
    than fifteen source minutes, so both halves would be ineligible. Asserted on
    the counts as well as the bars, because two ineligible bars where one
    eligible bar belongs is exactly the shape of that failure.
    """
    reference, streamed = _both(_request(), window_days=1)
    for pair in reference.bars_by_pair:
        ref_bars = reference.bars_by_pair[pair]
        out_bars = streamed.bars_by_pair[pair]
        assert len(out_bars) == len(ref_bars)
        assert [b["ts"] for b in out_bars] == [b["ts"] for b in ref_bars]
        assert [b["complete_bucket"] for b in out_bars] == [b["complete_bucket"] for b in ref_bars]
        assert [b["n_source_bars"] for b in out_bars] == [b["n_source_bars"] for b in ref_bars]
        assert sum(b["complete_bucket"] for b in out_bars) > 0, (
            "the fixture produced no eligible bar"
        )
        #: no bucket start appears twice
        starts = [b["ts"] for b in out_bars]
        assert len(starts) == len(set(starts))


# ---------------------------------------------------------------------------
# Chunk boundaries
# ---------------------------------------------------------------------------


def test_every_window_boundary_is_a_bucket_boundary() -> None:
    """The property that makes a carry buffer unnecessary, checked directly.

    Whole UTC days only, and a day is a whole number of 15-minute buckets, so a
    boundary can never fall inside one.
    """
    from scripts.m15_gate3a.aggregation import BUCKET_MINUTES

    assert 24 * 60 % BUCKET_MINUTES == 0
    for window_days in (1, 2, 3, 7, 31, 400):
        windows = streaming.iter_windows(SPAN_START, SPAN_END, window_days=window_days)
        assert windows[0][0] == SPAN_START
        assert windows[-1][1] == SPAN_END
        for (_, end), (start, _) in zip(windows, windows[1:], strict=False):
            #: contiguous, no gap and no overlap
            assert (datetime.fromisoformat(end) + timedelta(days=1)).date().isoformat() == start
            #: and the boundary instant is midnight, i.e. a bucket start
            boundary = datetime.fromisoformat(start).replace(tzinfo=UTC)
            assert boundary.hour == 0 and boundary.minute == 0


@pytest.mark.parametrize("window_days", [0, -1, 1.5, "7", None])
def test_a_window_step_that_could_split_a_bucket_is_refused(window_days: Any) -> None:
    """Fractional or non-integral steps are refused, not rounded."""
    with pytest.raises(streaming.StreamingError):
        streaming.iter_windows(SPAN_START, SPAN_END, window_days=window_days)


def test_a_bucket_emitted_by_two_windows_is_refused() -> None:
    """The fail-closed backstop, exercised rather than trusted.

    `iter_windows` makes this unreachable. If a later change ever did split a
    bucket, the accumulator must refuse rather than emit the same bucket twice
    as two incomplete bars — which would silently halve an eligible bar into two
    ineligible ones.
    """
    from scripts.m15_gate3a.incremental_m15 import IncrementalM15, IncrementalM15Error

    accumulator = IncrementalM15(pair="EUR_USD")
    bucket = datetime(2025, 5, 5, 12, 0, tzinfo=UTC)
    report = {
        "pair": "EUR_USD",
        "total_missing_source_minutes_within_emitted_buckets": 0,
        "rows_ingested": 1,
    }
    rows = [{"ts": bucket}]
    accumulator.absorb([{"ts": bucket}], report, rows)
    with pytest.raises(IncrementalM15Error, match="more than one"):
        accumulator.absorb([{"ts": bucket}], report, rows)


def test_a_window_wholly_inside_a_gap_is_skipped_not_refused(
    sandbox: Path, guards_installed: object, fast_fingerprint: str
) -> None:
    """A weekend window carries no row. `row_scope` refuses an empty batch.

    Skipping it is what keeps the streaming route from rejecting a corpus the
    reference accepts, and the equivalence assertion is what proves the skip
    changed nothing.
    """
    for pair in PAIRS:
        _write_minutes(sandbox, pair, start=SPAN_START, end=SPAN_END)
    request = _request()
    run = _run()
    _declare(run, request)
    #: 2025-05-10 and 2025-05-11 are the Saturday and Sunday; with window_days=1
    #: each is a window of its own and neither carries a row.
    windows = streaming.iter_windows(SPAN_START, SPAN_END, window_days=1)
    assert ("2025-05-10", "2025-05-10") in windows
    reference = _reference(request, run)
    streamed = _streamed(request, run, window_days=1)
    _assert_derivations_identical(reference, streamed)


def test_a_corpus_with_no_row_at_all_is_refused(
    sandbox: Path, guards_installed: object, fast_fingerprint: str
) -> None:
    """Skipping empty windows must not turn an empty corpus into a success.

    The refusal comes from `IncrementalM15.result()`, one level down — the same
    place, and for the same reason, that `row_scope.rows_in_scope` refuses an
    empty batch in the non-streaming reference. Asserted where it actually
    fires rather than where a first drafting expected it.
    """
    from scripts.m15_gate3a.incremental_m15 import IncrementalM15Error

    for pair in PAIRS:
        _write_minutes(sandbox, pair, start="2025-05-10", end="2025-05-11")  # weekend only
    request = _request()
    run = _run()
    _declare(run, request)
    with pytest.raises(IncrementalM15Error, match="nothing to report"):
        _streamed(request, run, window_days=1)


def test_the_accumulator_sorts_and_pins_the_pair_it_was_built_for() -> None:
    """Two defence-in-depth guards, exercised directly.

    A mutation audit classified both as *equivalent* under the committed
    enumerator — windows arrive in order, and `derive_m15` canonicalises the pair
    before the report is built — so nothing reached them. Equivalent today is a
    property of the caller, and these are the guards that hold if that changes.
    """
    from scripts.m15_gate3a.incremental_m15 import IncrementalM15, IncrementalM15Error

    def report(**over: Any) -> dict[str, Any]:
        base = {
            "pair": "EUR_USD",
            "total_missing_source_minutes_within_emitted_buckets": 0,
            "rows_ingested": 1,
        }
        base.update(over)
        return base

    #: batches out of order still produce an ordered series
    accumulator = IncrementalM15(pair="EUR_USD")
    later = datetime(2025, 5, 5, 12, 0, tzinfo=UTC)
    earlier = datetime(2025, 5, 5, 11, 45, tzinfo=UTC)

    def bar(ts: datetime) -> dict[str, Any]:
        #: the two fields `_build_gap_report` reads off a bar
        return {"ts": ts, "complete_bucket": True, "n_source_bars": 15}

    accumulator.absorb([bar(later)], report(), [{"ts": later}])
    accumulator.absorb([bar(earlier)], report(), [{"ts": earlier}])
    bars, _ = accumulator.result()
    assert [bar["ts"] for bar in bars] == [earlier, later]

    #: and a report for another pair is refused rather than folded in
    other = IncrementalM15(pair="EUR_USD")
    with pytest.raises(IncrementalM15Error, match="is for"):
        other.absorb([bar(later)], report(pair="USD_JPY"), [{"ts": later}])


def test_an_accumulator_with_no_batch_refuses_to_report() -> None:
    """The same fail-closed rule one level down, where the report is built."""
    from scripts.m15_gate3a.incremental_m15 import IncrementalM15, IncrementalM15Error

    with pytest.raises(IncrementalM15Error, match="nothing to report"):
        IncrementalM15(pair="EUR_USD").result()


# ---------------------------------------------------------------------------
# The memory bound
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("days", [3, 7, 14])
def test_peak_retained_raw_rows_does_not_grow_with_the_corpus(
    sandbox: Path, guards_installed: object, fast_fingerprint: str, days: int
) -> None:
    """The bound, measured. Not argued from the shape of the code.

    The corpus grows with `days`; the window does not. If the route were still
    accumulating, the peak would track the corpus.
    """
    end = (datetime.fromisoformat(SPAN_START) + timedelta(days=days - 1)).date().isoformat()
    total = sum(
        _write_minutes(sandbox, pair, start=SPAN_START, end=end, skip_weekends=False)
        for pair in PAIRS
    )
    request = _request(span_end_utc=end)
    run = _run()
    _declare(run, request)
    streaming.reset_retention_instrument()
    _streamed(request, run, window_days=2)
    peak = streaming.peak_retained_raw_rows()
    assert peak <= 2 * 1440, (peak, days)
    assert peak < total, (peak, total)
    assert streaming.retained_raw_rows() == 0, "rows were still held after the run returned"


def test_the_peak_is_a_window_of_one_pair_not_the_whole_corpus(
    sandbox: Path, guards_installed: object, fast_fingerprint: str
) -> None:
    """Twenty pairs, and the peak is still one pair's window."""
    pairs = tuple(sorted(PAIRS_20))
    for pair in pairs:
        _write_minutes(sandbox, pair, start=SPAN_START, end="2025-05-09", skip_weekends=False)
    request = _request(pairs=pairs, span_end_utc="2025-05-09")
    run = _run()
    _declare(run, request)
    streaming.reset_retention_instrument()
    _streamed(request, run, window_days=2)
    peak = streaming.peak_retained_raw_rows()
    assert peak <= 2 * 1440, peak
    #: what the full-buffer route would have held, for the comparison
    whole_corpus = len(pairs) * 5 * 1440
    assert peak * 10 < whole_corpus, (peak, whole_corpus)


def test_the_instrument_is_released_when_a_window_refuses(
    corpus: dict[str, int], guards_installed: object, fast_fingerprint: str, monkeypatch: Any
) -> None:
    """A refused window must not leave the count — or the rows — inflated."""
    request = _request()
    run = _run()
    _declare(run, request)
    streaming.reset_retention_instrument()
    monkeypatch.setattr(
        derivation,
        "derive_m15",
        lambda *a, **kw: (_ for _ in ()).throw(derivation.DerivationRouteError("refused")),
    )
    with pytest.raises(derivation.DerivationRouteError):
        _streamed(request, run, window_days=3)
    assert streaming.retained_raw_rows() == 0


# ---------------------------------------------------------------------------
# The route, and what it does not become
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("run_id", "a-different-run", "records run"),
        ("timeframe", "M15", "not M1"),
        ("operation", "track_a_m15_research_derivation", "records operation"),
    ],
)
def test_a_window_read_that_disagrees_with_the_authorisation_is_refused(
    corpus: dict[str, int],
    guards_installed: object,
    fast_fingerprint: str,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
    match: str,
) -> None:
    """The post-read verifications, now per window rather than once per run.

    They lived in `run_r1` until the read moved down here. A mutation audit had
    found three of them unverified when they were upstream, so moving them must
    not drop them: this is the same property, checked more often.
    """
    real = read_route.read_historical

    def relabelled(*a: Any, **kw: Any) -> Any:
        read = real(*a, **kw)
        fields = {
            "run_id": read.run_id,
            "operation": read.operation,
            "timeframe": read.timeframe,
            "epoch": read.epoch,
            "span_start_utc": read.span_start_utc,
            "span_end_utc": read.span_end_utc,
            "rows_by_pair": read.rows_by_pair,
        }
        fields[field] = value
        return read_route.HistoricalRead(**fields)

    monkeypatch.setattr(read_route, "read_historical", relabelled)
    request = _request()
    run = _run()
    _declare(run, request)
    with pytest.raises(streaming.StreamingError, match=match):
        _streamed(request, run, window_days=3)


def test_a_window_read_that_returns_the_wrong_shape_is_refused(
    corpus: dict[str, int],
    guards_installed: object,
    fast_fingerprint: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A read that succeeded is not the same as a read that returned what was gated."""
    monkeypatch.setattr(read_route, "read_historical", lambda *a, **kw: {"rows": []})
    request = _request()
    run = _run()
    _declare(run, request)
    with pytest.raises(streaming.StreamingError, match="not a HistoricalRead"):
        _streamed(request, run, window_days=3)


def test_a_window_reporting_another_epoch_is_refused(
    corpus: dict[str, int],
    guards_installed: object,
    fast_fingerprint: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One run, one epoch. Windows that disagree are not one corpus."""
    real = read_route.read_historical
    seen: list[int] = []

    def drifting(*a: Any, **kw: Any) -> Any:
        read = real(*a, **kw)
        seen.append(1)
        if len(seen) < 3 or not any(read.rows_by_pair.values()):
            return read
        return read_route.HistoricalRead(
            run_id=read.run_id,
            operation=read.operation,
            timeframe=read.timeframe,
            epoch="some_other_epoch",
            span_start_utc=read.span_start_utc,
            span_end_utc=read.span_end_utc,
            rows_by_pair=read.rows_by_pair,
        )

    monkeypatch.setattr(read_route, "read_historical", drifting)
    request = _request()
    run = _run()
    _declare(run, request)
    with pytest.raises(streaming.StreamingError, match="epoch"):
        _streamed(request, run, window_days=1)


def test_a_window_derivation_returning_the_wrong_shape_is_refused(
    corpus: dict[str, int],
    guards_installed: object,
    fast_fingerprint: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(derivation, "derive_m15", lambda *a, **kw: {"bars": []})
    request = _request()
    run = _run()
    _declare(run, request)
    with pytest.raises(streaming.StreamingError, match="derivation route returned"):
        _streamed(request, run, window_days=3)


def test_live_raw_rows_are_bounded_by_the_window(
    sandbox: Path, guards_installed: object, fast_fingerprint: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bound, measured on the **heap** rather than on a counter.

    `peak_retained_raw_rows()` is bookkeeping, and a mutation audit walked three
    defects straight past it: a module-level list that retained every window's
    read still reported one window; a balanced no-op instrument reported nothing
    at all; and deleting `del read` doubled true retention without moving the
    number.

    So this attaches a weak-referenced sentinel to every row the read route
    builds and counts the ones still alive at the deepest point of the run —
    inside the aggregator, with the window's rows in hand. That is a fact about
    the heap; no amount of bookkeeping satisfies it.
    """
    import weakref

    class _Sentinel:
        __slots__ = ("__weakref__",)

    alive: list[weakref.ref[Any]] = []
    real_row = read_route._row_from_source

    def sentinelled(*a: Any, **kw: Any) -> Any:
        row = real_row(*a, **kw)
        marker = _Sentinel()
        #: an extra key the row-scope snapshot does not copy, so this tracks the
        #: read's own row objects and nothing downstream
        row["_audit_sentinel"] = marker
        alive.append(weakref.ref(marker))
        return row

    def live() -> int:
        return sum(1 for ref in alive if ref() is not None)

    deep: list[int] = []
    between: list[int] = []
    real_delegate = derivation.DELEGATE
    real_read = read_route.read_historical

    def measuring_delegate(rows: Any, **kw: Any) -> Any:
        #: the deepest point: this window's rows are in hand
        deep.append(live())
        return real_delegate(rows, **kw)

    def measuring_read(*a: Any, **kw: Any) -> Any:
        #: **between** windows, before the next read allocates anything. A
        #: previous window still held here is the `del read` mutant: the peak
        #: inside the delegate looks identical either way, so measuring only
        #: there let it survive.
        between.append(live())
        return real_read(*a, **kw)

    monkeypatch.setattr(read_route, "_row_from_source", sentinelled)
    monkeypatch.setattr(derivation, "DELEGATE", measuring_delegate)
    monkeypatch.setattr(read_route, "read_historical", measuring_read)

    window_days = 2
    peaks: dict[int, tuple[int, int]] = {}
    for days in (4, 8, 16):
        for pair in PAIRS:
            _write_minutes(
                sandbox,
                pair,
                start=SPAN_START,
                end=(datetime.fromisoformat(SPAN_START) + timedelta(days=days - 1))
                .date()
                .isoformat(),
                skip_weekends=False,
            )
        request = _request(
            span_end_utc=(datetime.fromisoformat(SPAN_START) + timedelta(days=days - 1))
            .date()
            .isoformat()
        )
        run = _run(run_id=f"live-rows-{days}")
        _declare(run, request)
        alive.clear()
        deep.clear()
        between.clear()
        streaming.reset_retention_instrument()
        _streamed(request, run, window_days=window_days)
        corpus = days * 1440 * len(PAIRS)
        peaks[days] = (max(deep), corpus)
        #: nothing from a finished window survives into the next one
        assert max(between) == 0, (
            f"{max(between)} raw rows from an earlier window were still alive when the next "
            "one started"
        )
        #: and the counter agrees with the heap, so a no-op instrument that
        #: reports nothing cannot pass while the heap measurement does
        assert streaming.peak_retained_raw_rows() == max(deep), (
            streaming.peak_retained_raw_rows(),
            max(deep),
        )
        assert live() == 0, f"{live()} raw rows still alive after the run"

    #: the corpus quadruples; the live peak does not move
    observed = {days: peak for days, (peak, _) in peaks.items()}
    assert len(set(observed.values())) == 1, observed
    peak = next(iter(observed.values()))
    #: and it is exactly one window of one pair — `<=` would also be satisfied
    #: by an instrument that counts nothing
    assert peak == window_days * 1440, (peak, window_days)
    for days, (_, corpus) in peaks.items():
        assert peak * 4 <= corpus, (days, peak, corpus)


def test_the_streaming_route_swallows_nothing(
    corpus: dict[str, int], guards_installed: object, fast_fingerprint: str
) -> None:
    """A `try` around a stage is how "it failed but we carried on" gets written.

    `test_r1_orchestrator.py` pins that for `run_r1` and `preflight`. The
    read → derive loop moved down here, and the pin did not move with it: a
    mutant wrapped `accumulator.absorb(...)` in `except Exception: pass` and
    survived the whole suite, returning a silently 25 %-short derivation reported
    as a complete one.

    Structural half: `derive_streaming` may hold a `try`/`finally` — it needs one
    to balance the retention instrument — and no `except` at all.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(streaming.derive_streaming))
    handlers = [node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)]
    assert not handlers, (
        f"derive_streaming catches something at line(s) {[h.lineno for h in handlers]}"
    )
    tries = [node for node in ast.walk(tree) if isinstance(node, ast.Try)]
    assert all(node.finalbody and not node.handlers for node in tries), tries


def test_an_accumulation_failure_aborts_the_run(
    corpus: dict[str, int],
    guards_installed: object,
    fast_fingerprint: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The behavioural half of the same property.

    A structural pin says the code has no `except`; this says a failure actually
    propagates, so a short derivation can never be returned as a whole one.
    """
    from scripts.m15_gate3a import incremental_m15

    real_absorb = incremental_m15.IncrementalM15.absorb
    calls = {"n": 0}

    def failing(self: Any, *a: Any, **kw: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 2:
            raise incremental_m15.IncrementalM15Error("injected accumulation failure")
        return real_absorb(self, *a, **kw)

    monkeypatch.setattr(incremental_m15.IncrementalM15, "absorb", failing)
    request = _request()
    run = _run()
    _declare(run, request)
    with pytest.raises(incremental_m15.IncrementalM15Error, match="injected"):
        _streamed(request, run, window_days=2)


def test_a_request_mutated_mid_run_cannot_fabricate_the_recorded_span(
    corpus: dict[str, int],
    guards_installed: object,
    fast_fingerprint: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The defect `derivation.py` was fixed for, reopened here and closed again.

    A role widened the caller's `ReadRequest` from a plain sibling thread and got
    a `DerivedM15` labelled `1970-01-01..2099-12-31`, which `r1_survey` copies
    verbatim into the R1 evidence record. Driven from inside the delegate here
    rather than from a racing thread: the property is "the span comes from a
    snapshot", and a race would test the scheduler.
    """
    request = _request()
    run = _run()
    _declare(run, request)
    real_delegate = derivation.DELEGATE

    def widen_then_delegate(rows: Any, **kw: Any) -> Any:
        object.__setattr__(request, "span_start_utc", "1970-01-01")
        object.__setattr__(request, "span_end_utc", "2099-12-31")
        object.__setattr__(request, "warmup_extension_start_utc", "1970-01-01")
        return real_delegate(rows, **kw)

    monkeypatch.setattr(derivation, "DELEGATE", widen_then_delegate)
    derived = _streamed(request, run, window_days=3)
    assert derived.span_start_utc == SPAN_START
    assert derived.span_end_utc == SPAN_END


def test_there_is_no_fallback_to_a_full_buffer_route() -> None:
    """`_reference` lives in this file, not in `scripts/`.

    §6 forbids a parallel research route and a fallback. The only production
    composition of read → derive is `derive_streaming`, and `run_r1` calls it.
    """

    orchestrator_source = Path(
        __import__("scripts.m15_track_a.r1_orchestrator", fromlist=["x"]).__file__
    ).read_text(encoding="utf-8")
    tree = ast.parse(orchestrator_source)
    called = {
        getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert "derive_streaming" in called
    assert "read_historical" not in called, "the orchestrator still reads the whole corpus"
    assert "derive_m15" not in called, "the orchestrator still derives in one shot"


def test_the_streaming_module_reuses_the_committed_callables() -> None:
    """No second reader, no second aggregator, no second survey."""

    source = Path(streaming.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    called = {
        getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert "read_historical" in called
    assert "derive_m15" in called
    #: the accumulation is the committed one, reached through its public class
    assert "IncrementalM15" in called
    #: and it opens nothing itself
    assert not ({"open", "read_text", "read_bytes"} & called), sorted(called)
    #: nor does it reach the aggregator, or that package's privates, directly
    assert "aggregate_m15" not in called
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported.add(f"{node.module}.{alias.name}")
    private = {name for name in imported if name.rsplit(".", 1)[-1].startswith("_")}
    assert not private, f"Track A reached a private of another package: {sorted(private)}"


def test_the_fingerprint_is_measured_at_every_check_not_cached(
    corpus: dict[str, int], guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unmemoised, on purpose: the property `fast_fingerprint` would hide.

    `require_authorization` measures the tree at check time so a mid-run source
    change is caught. The streaming route checks once per window, so the count
    must grow with the number of windows — if it did not, some window would be
    running against an implementation nobody re-verified.
    """
    real = containment.implementation_fingerprint
    counted: dict[str, int] = {"n": 0}

    def counting() -> str:
        counted["n"] += 1
        return real()

    monkeypatch.setattr(containment, "implementation_fingerprint", counting)
    request = _request()
    run = _run()
    _declare(run, request)
    _streamed(request, run, window_days=7)
    with_seven = counted["n"]

    counted["n"] = 0
    run_two = _run(run_id="r1-streaming-equivalence-two")
    _declare(run_two, request)
    _streamed(request, run_two, window_days=1)
    with_one = counted["n"]

    assert with_one > with_seven, (with_one, with_seven)
    assert with_seven > 1
