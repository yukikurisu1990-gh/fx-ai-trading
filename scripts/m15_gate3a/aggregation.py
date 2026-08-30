"""Pure M1->M15 aggregation (synthetic rows only; no real files, no imputation).

Implements the frozen contract: UTC 15-minute bucket start; per-side bid/ask
OHLC (open=first, high=max, low=min, close=last); NO mid-price construction;
``n_source_bars`` recorded; event/label eligibility iff 15 DISTINCT
minute-aligned source minutes are usable; incomplete buckets are
diagnostics-only; missing minutes stay missing (no imputation); no synthetic
weekend bars (a bucket is emitted only where at least one source minute
exists); per-pair pip size via the gate-3a pair authority, which normalises the
spelling and fails closed outside the frozen PAIRS_20 universe.

This module reads nothing. It opens no file, imports no calendar artifact and
invents no market hours: the expected-slot authority is *injected* by the
caller (``expected_minutes``) or absent, and absence is reported as ``None``,
never inferred from the data (contract §12.10, D-6.1).

Contract Gate-decision (``docs/design/m15_contract_design_gate_decision.md``)
fixes the dispositions this module implements:

* **D-1 / §12.1-2 — a crossed quote (``ask < bid`` on any required field pair)
  is a HARD REFUSAL.** The bucket and the file are not certifiable; there is no
  correction, no drop-and-continue, no lenient mode and no counter that buys
  acceptance. ``ask == bid`` is *not* a crossed quote (D-1.7) — a zero spread is
  refused only by a separate cost/spread contract, never here.
* **D-2 / §12.4 — the semantic rejection tolerance is zero, structurally.** No
  tolerance parameter, no default, no inference and no ratio compared against a
  literal exists anywhere in this module.
* **D-3 / §12.5-7 — six-field minute accounting** (:func:`_build_minute_accounting`),
  with the identity ``expected = usable + absent + rejected`` asserted in code.
* **D-9 / §12.3 — a duplicate source minute aborts**, after canonicalisation,
  with no silent dedup; the minute is claimed *before* any quality disposition.

**§12.24 — correction of a false claim previously carried here.** The docstring
of the BL-4 change asserted that *"Aborting the whole pair was this package's
own invention."* That is false and is retracted: the merged PR #439 audit
prescribed ``ask_* >= bid_*`` per row verbatim, the third independent re-check
recorded the re-disposition as a blocker (B-4), and the contract Gate-decision
D-1 restored the refusal and recorded the re-disposition as procedurally void.
``scripts/stage25_0a_build_path_quality_dataset.py`` is *not* admissible
authority for a family-A design semantic and is no longer cited as one.

Earlier re-check fixes retained:

* **B-1** — minute alignment is decided on a *plain* UTC ``datetime`` rebuilt
  from the timestamp's components, and any sub-minute remainder is rejected,
  including the nanoseconds a ``pandas.Timestamp`` carries outside ``.second``
  and ``.microsecond``. Bucket keys and duplicate detection use that plain
  minute, so a nanosecond difference can no longer split one 15-minute window
  into two eligible bars.
* **B-4 / D-1** — crossed quotes refuse (see above).
* **BL-2** — awareness and minute alignment are decided by
  :mod:`scripts.m15_gate3a.timeutil`, the single timestamp authority. The old
  ``tzinfo is None`` test is not Python's awareness test and let a
  ``utcoffset()``-``None`` zone through ``astimezone(UTC)``, which then read the
  value in the *host's* zone and accepted a bucket hours wrong.
* **R-2 / RF-3** — per-row OHLC coherence is asserted, and re-asserted on the
  constructed bar together with the bid/ask relation.
* **RF-4** — a row object is read once, into a snapshot, and the same object may
  not appear twice: one record is one source minute, never fifteen.
* **RF-18** — ``spread_open`` is emitted alongside ``spread_close``.
* **R-6** — derived outputs are re-checked finite, not only the inputs.
* **N-1** — every caller-supplied number is pinned to its plain character data
  by :mod:`scripts.m15_gate3a.numeric_authority` *before* any comparison, so a
  ``float`` subclass with an overridden ``__lt__`` can no longer decide whether
  its own quote is crossed. See :func:`_assert_row_usable`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any, Final

from .derivation_containment import assert_derivation_authorised
from .numeric_authority import NumericAuthorityError, pin_number
from .pair_authority import canonical_pair, pip_size_for_pair
from .timeutil import TimestampError, to_utc_minute

BUCKET_MINUTES: Final[int] = 15
FULL_BUCKET_SOURCE_BARS: Final[int] = 15

# The four required quote fields of each side, in OHLC order.
_QUOTE_FIELDS: Final[tuple[str, ...]] = ("o", "h", "l", "c")

# Per-side OHLC source keys expected on each synthetic M1 row.
_SIDE_KEYS: Final[tuple[str, ...]] = tuple(
    f"{side}_{field}" for side in ("bid", "ask") for field in _QUOTE_FIELDS
)


class AggregationError(ValueError):
    """Raised when synthetic M1 input violates the aggregation contract."""


def to_pips(price_delta: float, pair: str) -> float:
    """Convert a price delta to pips using the per-pair authority (fail-closed)."""
    return price_delta / pip_size_for_pair(pair)


def _plain_utc_minute(ts: Any) -> datetime:
    """Return a plain minute-aligned UTC ``datetime``; fail closed on any remainder.

    BL-2: delegated to the single timestamp authority, which decides awareness
    by ``utcoffset()`` (not ``tzinfo is None``) and converts from the offset
    itself rather than via ``astimezone``, so the host's zone can never take
    part. Sub-minute remainder carried outside ``.second``/``.microsecond`` —
    ``pandas.Timestamp`` nanoseconds, or a subclass hiding it elsewhere — is
    still rejected there.
    """
    # M1 rows carry datetimes. Widening this to accept `str` was a loosening of
    # the input contract with nothing asking for it, so it is narrowed back.
    if not isinstance(ts, datetime):
        raise AggregationError("M1 row 'ts' is not a datetime (tz-aware datetime required)")
    try:
        return to_utc_minute(ts)
    except TimestampError as exc:
        raise AggregationError(f"M1 row timestamp rejected: {exc}") from exc


def _bucket_start(minute: datetime) -> datetime:
    """Floor a plain minute-aligned UTC datetime to its 15-minute bucket start."""
    start = minute.replace(minute=(minute.minute // BUCKET_MINUTES) * BUCKET_MINUTES)
    if start.minute % BUCKET_MINUTES or start.second or start.microsecond:  # pragma: no cover
        raise AggregationError(f"bucket start {start.isoformat()} is not 15-minute aligned")
    return start


def _snapshot_row(row: Any) -> dict[str, Any]:
    """Read every required key of one M1 row EXACTLY ONCE into a plain dict.

    RF-3/RF-4: the module claims to defend against a row that shows one face to
    validation and another to bar construction. It cannot do that while it reads
    the caller's object four times — the audit built a row whose values changed
    between reads and got an ``eligible: True`` bar with ``bid_h`` below
    ``bid_l``. One read per key, here, is what makes validation and bar
    construction see the same evidence. Every later stage reads this snapshot,
    never ``row``.
    """
    if not isinstance(row, Mapping):
        raise AggregationError(f"M1 row must be a mapping, got {type(row).__name__}")
    snapshot: dict[str, Any] = {}
    for key in ("ts", *_SIDE_KEYS):
        try:
            snapshot[key] = row[key]
        except KeyError as exc:
            # RF-29: fail closed with the documented exception type, never a
            # bare KeyError escaping to the caller.
            if key == "ts":
                raise AggregationError(
                    "M1 row has no 'ts' key (tz-aware datetime required)"
                ) from exc
            raise AggregationError(f"M1 row missing side key {key!r}") from exc
        except Exception as exc:
            raise AggregationError(f"M1 row key {key!r} could not be read: {exc}") from exc
    return snapshot


def _assert_row_usable(row: dict[str, Any], minute: datetime) -> None:
    """Assert one snapshotted M1 row is admissible to aggregation, or refuse.

    F-2: every side value must be a finite number (``math.isfinite``) — NaN /
    +inf / -inf fail closed before any aggregation output exists. R-2: the row's
    own OHLC must be internally coherent. D-1: the row must not be a crossed
    quote.

    D-2: there is no tolerance here. A row that violates the contract does not
    produce a smaller count — it refuses, and the bucket and file are not
    certifiable.

    **N-1 — the numbers are pinned before anything is compared.** The type test
    was ``isinstance(v, (int, float))``, which admits a *subclass*, and every
    crossed-quote and coherence decision below was then a ``<`` / ``>`` against
    the caller's own object. A two-faced ``float`` subclass overriding the
    ordering dunders therefore answered "not crossed" to D-1 on a bucket whose
    ask sat below its bid on all fifteen rows, and produced
    ``n_source_bars=15, eligible=True, complete_bucket=True`` where the identical
    plain-``float`` crossings refused 12 out of 12. The snapshot's values are
    replaced **in place** with their plain character data
    (:mod:`~scripts.m15_gate3a.numeric_authority`), so validation, bar
    construction and the re-assertion on the derived bar all read the same
    pinned numbers and no caller-controlled ``__lt__`` is ever consulted. This
    is the numeric member of the family already closed for ``str`` (RF-6/RF-20),
    ``Path`` (RF-5), ``datetime`` (BL-2) and ``Sequence`` (RF-4).
    """
    for k in _SIDE_KEYS:
        try:
            v = pin_number(row[k], what=f"M1 row key {k!r}")
        except NumericAuthorityError as exc:
            raise AggregationError(f"M1 row key {k!r} must be numeric ({exc})") from exc
        if not math.isfinite(v):
            raise AggregationError(f"M1 row key {k!r} is non-finite ({v!r})")
        row[k] = v
    _assert_row_coherent(row, minute)
    _assert_not_crossed(row, minute)


def _assert_row_coherent(row: dict[str, Any], minute: datetime) -> None:
    """R-2: reject rows whose per-side OHLC cannot describe any quote at all.

    Intra-side impossibilities: a high below its own low, or a high/low that
    fails to bracket the open and close. Those cannot be produced by a market,
    only by a broken writer. The bid/ask relation is a separate contract rule —
    see :func:`_assert_not_crossed`.
    """
    for side in ("bid", "ask"):
        o, h, low, c = (row[f"{side}_{k}"] for k in _QUOTE_FIELDS)
        if h < low:
            raise AggregationError(f"M1 row {minute.isoformat()} {side} high {h} < low {low}")
        if h < max(o, c) or low > min(o, c):
            raise AggregationError(
                f"M1 row {minute.isoformat()} {side} OHLC incoherent (o={o}, h={h}, l={low}, c={c})"
            )


def _assert_not_crossed(row: dict[str, Any], minute: datetime) -> None:
    """D-1 / §12.1-2: a crossed quote refuses. There is no drop-and-count.

    A crossed quote is any required bid/ask field pair where ``ask < bid``. It
    is never corrected, never dropped-and-continued, and eligibility is never
    preserved by discarding the offending observation: if a crossed quote exists
    anywhere in a bucket or file under certification, that bucket and that file
    are **not certifiable**, so this refuses the whole aggregation.

    ``ask == bid`` is **not** a crossed quote (D-1.7). A zero spread is refused
    only if it violates a separate cost/spread contract, and then by that
    contract — not by this rule.

    Each field pair reports its own name and values, so a test can identify
    which pair fired without a regex alternation.
    """
    for field in _QUOTE_FIELDS:
        bid = row[f"bid_{field}"]
        ask = row[f"ask_{field}"]
        if ask < bid:
            raise AggregationError(
                f"crossed quote at {minute.isoformat()}: "
                f"ask_{field} {ask} < bid_{field} {bid}; bucket and file are not certifiable"
            )


def _canonical_expected_minutes(expected_minutes: Any) -> frozenset[datetime] | None:
    """Canonicalise the INJECTED expected-minute authority, or return ``None``.

    D-6: the expected slot set is never inferred from the source and never
    invented here. This module authors no calendar: it accepts a set of
    ``datetime`` supplied by the caller, canonicalises each entry through the
    single timestamp authority, and refuses alias duplicates (two spellings of
    one minute) after canonicalisation, exactly as D-9 requires of source
    minutes. ``None`` means *no authority was supplied* — the calendar-derived
    fields are then reported as ``None``, never as zero.
    """
    if expected_minutes is None:
        return None
    if not isinstance(expected_minutes, (set, frozenset)):
        raise AggregationError(
            "expected_minutes must be a set or frozenset of tz-aware minute-aligned datetimes, "
            f"got {type(expected_minutes).__name__}"
        )
    canonical: set[datetime] = set()
    for item in expected_minutes:
        if not isinstance(item, datetime):
            raise AggregationError(
                f"expected_minutes entry must be a tz-aware datetime, got {type(item).__name__}"
            )
        try:
            minute = to_utc_minute(item)
        except TimestampError as exc:
            raise AggregationError(f"expected_minutes entry rejected: {exc}") from exc
        if minute in canonical:
            raise AggregationError(
                f"expected_minutes contains {minute.isoformat()} twice after canonicalisation"
            )
        canonical.add(minute)
    return frozenset(canonical)


def aggregate_m15(
    m1_rows: list[dict[str, Any]],
    *,
    pair: str,
    expected_minutes: set[datetime] | frozenset[datetime] | None = None,
) -> tuple[list[dict], dict]:
    """Aggregate synthetic M1 bid/ask OHLC rows into M15 bars + a gap report.

    Returns ``(m15_bars, gap_report)``. Each M15 bar carries the bucket start
    (``ts``), per-side OHLC, the opening and closing quoted spreads,
    ``n_source_bars``, the certifiability flag ``complete_bucket`` (and its
    retained alias ``eligible``), and the per-pair ``pip_size`` — NO mid price
    is constructed. The pair is normalised and universe-checked before any
    aggregation, so an unknown or non-canonical pair fails closed.

    ``expected_minutes`` is the OPTIONAL injected expected-slot authority (§9,
    D-6): a set of tz-aware minute-aligned datetimes. It is never defaulted,
    never inferred and never generated here. Without it the calendar-derived
    accounting fields are ``None``.

    **This function refuses rather than degrades.** Under D-1/D-2/D-9 a crossed
    quote, a non-finite or incoherent row, a duplicate minute, a repeated row
    object or a source minute outside the supplied expected authority raises
    :class:`AggregationError`; none of them yields a smaller count or a
    quietly-ineligible bar.
    """
    # Containment first, before the input is read at all. A guard placed after
    # the caller has already been trusted is caller discipline, and caller
    # discipline is what let real rows reach this function without passing
    # through the authorised Track A derivation route -- see
    # ``derivation_containment`` for the bypass this closes.
    assert_derivation_authorised(m1_rows)

    # fail-closed FIRST (unknown/off-universe pair raises), and D5: the emitted
    # artifact must carry the CANONICAL label, not the caller's spelling — the
    # committed design inventory requires "one of PAIRS_20" and cost_schema
    # already rejects non-canonical spellings.
    pair = canonical_pair(pair)
    pip = pip_size_for_pair(pair)
    # RF-26/BL-1: lazy evidence is refused. A generator or one-shot iterator can
    # answer differently on a second pass and cannot be re-read by an auditor.
    if not isinstance(m1_rows, list):
        raise AggregationError("m1_rows must be a list of synthetic M1 dicts")
    expected = _canonical_expected_minutes(expected_minutes)

    buckets: dict[datetime, list[tuple[datetime, dict[str, Any]]]] = {}
    observed_minutes: set[datetime] = set()
    identities: dict[int, int] = {}
    # BL-1's own lesson, applied here: `isinstance(m1_rows, list)` admits a list
    # SUBCLASS, and `len(m1_rows)` is whatever its `__len__` says. Count what is
    # actually iterated. R-2 term pinning: `rows_ingested` counts READS; the
    # minute counts in `minute_accounting` count MINUTES. They are not synonyms.
    rows_ingested = 0
    for index, row in enumerate(m1_rows):
        rows_ingested += 1
        # RF-4: fifteen source minutes means fifteen record OBJECTS. One object
        # presented at two indices is a single record claiming to be two, and it
        # walked a full `n_source_bars: 15, eligible: True` bucket past the
        # audit. `no_overlap._materialise` already carries this guard.
        if id(row) in identities:
            raise AggregationError(
                f"the same row object appears at indices {identities[id(row)]} and {index}; "
                "one M1 record cannot be two source minutes"
            )
        identities[id(row)] = index
        snapshot = _snapshot_row(row)
        minute = _plain_utc_minute(snapshot["ts"])
        bucket = _bucket_start(minute)
        # D-9 / §12.3: the minute is claimed BEFORE any quality disposition, so
        # a record that later fails the contract still consumes its minute and
        # cannot be substituted by a second record for the same minute. F-1/B-1:
        # the comparison is on the plain UTC minute, so an alias spelling or a
        # sub-minute remainder cannot open a second bucket. No silent dedup.
        if minute in observed_minutes:
            raise AggregationError(
                f"duplicate source minute {minute.isoformat()} in bucket {bucket.isoformat()}"
            )
        observed_minutes.add(minute)
        _assert_row_usable(snapshot, minute)
        buckets.setdefault(bucket, []).append((minute, snapshot))

    usable_minutes: set[datetime] = set()
    bars: list[dict] = []
    total_missing = 0
    for b in sorted(buckets):
        # Sort on the normalised minute, never on the caller's raw ``ts`` object.
        entries = sorted(buckets[b], key=lambda item: item[0])
        rows = [r for _, r in entries]
        usable_minutes.update(m for m, _ in entries)
        # R-2 term pinning: `n_source_bars` is the count of DISTINCT USABLE
        # source minutes contributing to this bucket. It is not a count of reads
        # (RF-4) and not "rows retained after rejection" — nothing is rejected
        # and retained here, because a contract violation refuses (D-1/D-2).
        n = len(rows)
        if n > FULL_BUCKET_SOURCE_BARS:  # pragma: no cover - distinct minutes bound this to 15
            raise AggregationError(f"bucket {b.isoformat()} has {n} > 15 source bars")
        total_missing += FULL_BUCKET_SOURCE_BARS - n
        bid_o = rows[0]["bid_o"]
        ask_o = rows[0]["ask_o"]
        bid_c = rows[-1]["bid_c"]
        ask_c = rows[-1]["ask_c"]
        # §12.7 / D-3.5: a certifiable bar requires EVERY contract-required
        # source minute to be usable — 15 distinct usable minutes, no fewer.
        complete = n == FULL_BUCKET_SOURCE_BARS
        bar = {
            "ts": b,
            "n_source_bars": n,
            "complete_bucket": complete,
            # Retained alias of `complete_bucket` for the frozen derivation
            # manifest's `event_label_eligibility` term. Same measured quantity,
            # never a second measurement.
            "eligible": complete,
            "bid_o": bid_o,
            "bid_h": max(r["bid_h"] for r in rows),
            "bid_l": min(r["bid_l"] for r in rows),
            "bid_c": bid_c,
            "ask_o": ask_o,
            "ask_h": max(r["ask_h"] for r in rows),
            "ask_l": min(r["ask_l"] for r in rows),
            "ask_c": ask_c,
            # RF-18: the open-side spread variant the pre-registration §4 and the
            # committed derivation manifest both require, taken from the
            # bucket's FIRST usable minute.
            "spread_open": ask_o - bid_o,
            "spread_close": ask_c - bid_c,
            "pip_size": pip,
        }
        _assert_bar_coherent(bar)
        bars.append(bar)

    accounting = _build_minute_accounting(
        observed=observed_minutes, usable=usable_minutes, expected=expected
    )
    gap_report = _build_gap_report(
        bucket_starts=sorted({_bucket_start(m) for m in observed_minutes}),
        source_minutes=sorted(observed_minutes),
        bars=bars,
        total_missing=total_missing,
        pair=pair,
        pip=pip,
        rows_ingested=rows_ingested,
        minute_accounting=accounting,
    )
    return bars, gap_report


def _assert_bar_coherent(bar: dict) -> None:
    """Re-assert on the CONSTRUCTED bar what the rows were required to satisfy.

    R-6: derived outputs must be finite too, not only the inputs — the quoted
    spreads can overflow to ``inf`` from finite inputs.

    RF-3: this guard documented itself as the last defence against a row that
    changes between validation and bar construction, then checked only
    finiteness and a negative ``spread_close``; the audit emitted an
    ``eligible: True`` bar with ``bid_h`` below ``bid_l`` and ``ask_h`` below
    ``bid_h`` straight through it. Bar-level OHLC coherence and the bid/ask
    relation are asserted here as well. With :func:`_snapshot_row` reading each
    row once these are defence in depth over the row-level guards rather than
    the only line of defence, and they are exercised directly by the tests.
    """
    for key in (*_SIDE_KEYS, "spread_open", "spread_close", "pip_size"):
        v = bar[key]
        if not math.isfinite(v):
            raise AggregationError(f"derived bar value {key!r} is non-finite ({v!r})")
    for key in ("spread_open", "spread_close"):
        if bar[key] < 0:
            raise AggregationError(f"negative quoted {key} {bar[key]!r}")
    for side in ("bid", "ask"):
        o, h, low, c = (bar[f"{side}_{k}"] for k in _QUOTE_FIELDS)
        if h < low:
            raise AggregationError(f"derived bar {side} high {h} < low {low}")
        if h < max(o, c) or low > min(o, c):
            raise AggregationError(
                f"derived bar {side} OHLC incoherent (o={o}, h={h}, l={low}, c={c})"
            )
    for field in _QUOTE_FIELDS:
        bid = bar[f"bid_{field}"]
        ask = bar[f"ask_{field}"]
        if ask < bid:
            raise AggregationError(f"derived bar crossed: ask_{field} {ask} < bid_{field} {bid}")


def _max_unavailable_run(expected: frozenset[datetime], usable: set[datetime]) -> int:
    """Longest run of consecutive EXPECTED minutes that are not usable (D-3.4).

    Measured against the expected calendar, never against the observed data:
    the run advances over the expected slots in order, so a stretch the calendar
    does not expect neither starts nor extends a run. The unit is expected
    minutes.
    """
    longest = 0
    run = 0
    for minute in sorted(expected):
        if minute in usable:
            run = 0
            continue
        run += 1
        longest = max(longest, run)
    return longest


def _build_minute_accounting(
    *,
    observed: set[datetime],
    usable: set[datetime],
    expected: frozenset[datetime] | None,
) -> dict:
    """D-3 / §12.5: the six separately-measured minute quantities.

    ``expected_source_minute_count`` — minutes the injected expected-slot
    authority says should exist. ``observed_source_minute_count`` — minutes for
    which a source record existed. ``absent_source_minute_count`` — expected but
    **not present**. ``rejected_source_minute_count`` — **present** but not
    usable because it violated a contract. ``usable_source_minute_count`` —
    canonical distinct minutes admissible to aggregation.
    ``max_unavailable_gap_minutes`` — longest run of consecutive
    expected-but-not-usable minutes (:func:`_max_unavailable_run`).

    **Coverage deficit spans BOTH ``absent`` and ``rejected``** (D-3.1); neither
    alone describes it, and a present-but-rejected minute is never reported
    merely as "missing" (D-3.2). ``expected``, ``absent`` and
    ``max_unavailable_gap_minutes`` are ``None`` — never ``0`` — when no
    expected-slot authority was supplied, because absence of data is a coverage
    question, not a calendar answer (D-6.1).

    The identity ``expected == usable + absent + rejected`` is asserted here and
    fails closed. It also fails closed on a source minute the authority does not
    expect, which is the only way the identity can break once ``usable`` is a
    subset of ``observed``.

    Honest note on ``rejected_source_minute_count``: it is *measured* (from the
    observed and usable minute sets), not asserted, so it is not a hard-coded
    self-attestation under R-1. Under D-1/D-2/D-9 every rejection route this
    module has refuses the whole aggregation, so a report that is *returned*
    carries ``0`` here; the field is emitted because §12.5 requires the term and
    the accounting identity is defined over it.
    """
    if not usable <= observed:
        raise AggregationError(
            "internal accounting error: usable minutes are not a subset of observed minutes"
        )
    observed_count = len(observed)
    usable_count = len(usable)
    rejected_count = observed_count - usable_count
    expected_count: int | None = None
    absent_count: int | None = None
    max_unavailable: int | None = None
    if expected is not None:
        expected_count = len(expected)
        absent_count = len(expected - observed)
        if expected_count != usable_count + absent_count + rejected_count:
            unexpected = sorted(observed - expected)
            detail = ""
            if unexpected:
                detail = (
                    f"; {len(unexpected)} source minute(s) lie outside the expected-slot "
                    f"authority, earliest {unexpected[0].isoformat()}"
                )
            raise AggregationError(
                "minute accounting identity violated: expected "
                f"{expected_count} != usable {usable_count} + absent {absent_count} "
                f"+ rejected {rejected_count}{detail}"
            )
        max_unavailable = _max_unavailable_run(expected, usable)
    return {
        "expected_source_minute_count": expected_count,
        "observed_source_minute_count": observed_count,
        "absent_source_minute_count": absent_count,
        "rejected_source_minute_count": rejected_count,
        "usable_source_minute_count": usable_count,
        "max_unavailable_gap_minutes": max_unavailable,
    }


def _build_gap_report(
    *,
    bucket_starts: list[datetime],
    source_minutes: list[datetime],
    bars: list[dict],
    total_missing: int,
    pair: str,
    pip: float,
    rows_ingested: int,
    minute_accounting: dict,
) -> dict:
    """Gap report with the schema keys the committed design inventory declares (R-7).

    ``minute_accounting`` carries the D-3 six-field coverage evidence and is the
    only coverage authority here. The remaining figures are observed-span
    diagnostics.

    **§12.6 / D-3.3 — the meaning of ``missing_minute_count``, stated where it
    appears, and it may NOT be used in any certification decision.** It counts
    absent minutes strictly BETWEEN the first and last minute that had a source
    record. It therefore counts market-closure minutes (weekends, holidays) like
    any other hole, and counts nothing before the first or after the last
    observed minute — a partial LEADING or TRAILING bucket contributes ``0``
    here while ``total_missing_source_minutes_within_emitted_buckets`` counts it.
    Coverage is decided by ``minute_accounting`` against the injected
    expected-slot authority, never by this figure. ``max_gap_minutes`` shares the
    same observed-span basis; ``max_unavailable_gap_minutes`` is the
    calendar-based quantity.

    ``rows_ingested`` counts READS, not minutes: it is incremented per iterated
    record so a list subclass with a lying ``__len__`` cannot falsify it. With
    duplicates and repeated row objects refused it equals
    ``observed_source_minute_count`` on every returned report, and the two names
    are kept distinct because R-2 records exactly that confusion.

    R-1: the hard-coded self-attestations ``imputation``,
    ``synthetic_weekend_bars`` and ``mid_price_constructed`` are **deleted**, not
    reported — none could ever take the other value, so none was evidence. The
    properties they claimed are observable instead: no bar carries a mid-price
    key, no bucket without a source minute is emitted, and no absent minute is
    back-filled. The drop counters ``dropped_crossed_quote_rows``,
    ``rows_retained``, ``buckets_fully_dropped`` and ``all_rows_dropped`` are
    deleted with the drop-and-count disposition that D-1 revoked: under the
    restored refusal each could only ever be zero/empty.
    """
    missing_whole_buckets = 0
    if bucket_starts:
        cur, last, present = bucket_starts[0], bucket_starts[-1], set(bucket_starts)
        while cur <= last:
            if cur not in present:
                missing_whole_buckets += 1
            cur += timedelta(minutes=BUCKET_MINUTES)

    missing_minute_count = 0
    max_gap_minutes = 0
    for prev, nxt in zip(source_minutes, source_minutes[1:], strict=False):
        hole = int((nxt - prev).total_seconds() // 60) - 1
        if hole > 0:
            missing_minute_count += hole
            max_gap_minutes = max(max_gap_minutes, hole)

    complete = sum(1 for x in bars if x["complete_bucket"])
    return {
        "pair": pair,
        "pip_size": pip,
        "n_buckets_emitted": len(bars),
        # R-2 / §12.20: `n_eligible` is renamed to the quantity it measures —
        # buckets with all 15 contract-required source minutes usable. It is NOT
        # `raw_traded_event_count` and must never be fed where that is meant.
        "complete_bucket_count": complete,
        "incomplete_bucket_count": len(bars) - complete,
        "missing_minute_count": missing_minute_count,
        "max_gap_minutes": max_gap_minutes,
        "total_missing_source_minutes_within_emitted_buckets": total_missing,
        "missing_whole_buckets": missing_whole_buckets,
        "rows_ingested": rows_ingested,
        "minute_accounting": minute_accounting,
    }
