"""Pure M1->M15 aggregation (synthetic rows only; no real files, no imputation).

Implements the frozen contract: UTC 15-minute bucket start; per-side bid/ask
OHLC (open=first, high=max, low=min, close=last); NO mid-price construction;
``n_source_bars`` recorded; event/label eligibility iff 15 DISTINCT
minute-aligned source minutes are present; incomplete buckets are
diagnostics-only; missing minutes stay missing (no imputation); no synthetic
weekend bars (a bucket is emitted only where at least one source minute
exists); per-pair pip size via the gate-3a pair authority, which normalises the
spelling and fails closed outside the frozen PAIRS_20 universe.

Re-check fixes (PR #439):

* **B-1** — minute alignment is decided on a *plain* UTC ``datetime`` rebuilt
  from the timestamp's components, and any sub-minute remainder is rejected,
  including the nanoseconds a ``pandas.Timestamp`` carries outside ``.second``
  and ``.microsecond``. Bucket keys and duplicate detection use that plain
  minute, so a nanosecond difference can no longer split one 15-minute window
  into two eligible bars.
* **B-4** — pip size comes from ``pair_authority.pip_size_for_pair``.
* **R-2** — per-row OHLC coherence is asserted, so a finite-but-impossible row
  can no longer be swallowed by ``max()``/``min()`` into a plausible bar.
* **R-6** — derived outputs are re-checked finite, not only the inputs.
* **R-7** — the gap report counts missing source minutes and reports a
  minute-granular maximum gap under the schema key the committed inventory
  declares.

Second re-check fixes:

* **BL-2** — awareness and minute alignment are decided by
  :mod:`scripts.m15_gate3a.timeutil`, the single timestamp authority. The old
  ``tzinfo is None`` test is not Python's awareness test and let a
  ``utcoffset()``-``None`` zone through ``astimezone(UTC)``, which then read the
  value in the *host's* zone and accepted a bucket hours wrong.
* **BL-4** — a crossed quote (``ask < bid``) is a data anomaly, not a contract
  violation: the row is dropped and counted per pair, exactly as this repo's
  committed ``scripts/stage25_0a_build_path_quality_dataset.py`` already treats
  negative spread. Aborting the whole pair was this package's own invention.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, Final

from .pair_authority import canonical_pair, pip_size_for_pair
from .timeutil import TimestampError, to_utc_minute

BUCKET_MINUTES: Final[int] = 15
FULL_BUCKET_SOURCE_BARS: Final[int] = 15

# Per-side OHLC source keys expected on each synthetic M1 row.
_SIDE_KEYS: Final[tuple[str, ...]] = (
    "bid_o",
    "bid_h",
    "bid_l",
    "bid_c",
    "ask_o",
    "ask_h",
    "ask_l",
    "ask_c",
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
        raise AggregationError("M1 row missing tz-aware 'ts' datetime")
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


def _validate_row(row: dict[str, Any]) -> tuple[datetime, datetime]:
    """Validate one synthetic M1 row; return ``(bucket_start, minute_ts)``.

    F-1/B-1: the timestamp must reduce to an exact UTC minute (see
    :func:`_plain_utc_minute`). F-2: every side value must be a finite number
    (``math.isfinite``) — NaN / +inf / -inf fail closed before any aggregation
    output exists. R-2: the row's own OHLC must be internally coherent, so a
    finite-but-impossible row cannot be absorbed silently.

    A crossed quote is *not* checked here: BL-4 makes it a counted drop, which
    is a decision for the caller loop, not a validation error.
    """
    minute = _plain_utc_minute(row.get("ts"))
    for k in _SIDE_KEYS:
        if k not in row:
            raise AggregationError(f"M1 row missing side key {k!r}")
        v = row[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise AggregationError(f"M1 row key {k!r} must be numeric")
        if not math.isfinite(v):
            raise AggregationError(f"M1 row key {k!r} is non-finite ({v!r})")
    _assert_row_coherent(row, minute)
    return _bucket_start(minute), minute


def _assert_row_coherent(row: dict[str, Any], minute: datetime) -> None:
    """R-2: reject rows whose per-side OHLC cannot describe any quote at all.

    Only *intra-side* impossibilities are contract violations: a high below its
    own low, or a high/low that fails to bracket the open and close. Those
    cannot be produced by a market, only by a broken writer. The bid/ask
    relation is handled separately — see :func:`_is_crossed_quote`.
    """
    for side in ("bid", "ask"):
        o, h, low, c = (row[f"{side}_{k}"] for k in ("o", "h", "l", "c"))
        if h < low:
            raise AggregationError(f"M1 row {minute.isoformat()} {side} high {h} < low {low}")
        if h < max(o, c) or low > min(o, c):
            raise AggregationError(
                f"M1 row {minute.isoformat()} {side} OHLC incoherent (o={o}, h={h}, l={low}, c={c})"
            )


def _is_crossed_quote(row: dict[str, Any]) -> bool:
    """True iff any of the row's four ask values sits below its bid counterpart.

    BL-4: a crossed quote is an *observed data anomaly*, and this repository has
    already ruled on how to handle one. ``scripts/stage25_0a_build_path_quality_dataset.py``
    documents "rows with negative spread (data anomaly)" and drops the row while
    incrementing ``dropped_invalid_spread`` (``:191``, ``:242-245``, reported at
    ``:417``/``:424``). Gate-3a raising and abandoning the whole pair was this
    package's own stricter invention, incompatible with that precedent; the
    counted drop is adopted instead so one anomalous minute costs one minute.
    """
    return any(row[f"ask_{k}"] < row[f"bid_{k}"] for k in ("o", "h", "l", "c"))


def aggregate_m15(m1_rows: list[dict[str, Any]], *, pair: str) -> tuple[list[dict], dict]:
    """Aggregate synthetic M1 bid/ask OHLC rows into M15 bars + a gap report.

    Returns ``(m15_bars, gap_report)``. Each M15 bar carries per-side OHLC, the
    closing quoted spread, ``n_source_bars``, ``eligible`` (== 15 distinct
    minute-aligned source minutes), and the per-pair ``pip_size`` — NO mid price
    is constructed. The pair is normalised and universe-checked before any
    aggregation, so an unknown or non-canonical pair fails closed.
    """
    # fail-closed FIRST (unknown/off-universe pair raises), and D5: the emitted
    # artifact must carry the CANONICAL label, not the caller's spelling — the
    # committed design inventory requires "one of PAIRS_20" and cost_schema
    # already rejects non-canonical spellings.
    pair = canonical_pair(pair)
    pip = pip_size_for_pair(pair)
    if not isinstance(m1_rows, list):
        raise AggregationError("m1_rows must be a list of synthetic M1 dicts")

    buckets: dict[datetime, list[tuple[datetime, dict[str, Any]]]] = {}
    seen_minutes: dict[datetime, set[datetime]] = {}
    dropped_crossed = 0
    # BL-1's own lesson, applied here: `isinstance(m1_rows, list)` admits a list
    # SUBCLASS, and `len(m1_rows)` is whatever its `__len__` says. Reporting
    # `rows_ingested` from `len()` while counting retained/dropped in the loop
    # let a lying `__len__` falsify the report's own accounting identity. Count
    # what is actually iterated.
    rows_ingested = 0
    for row in m1_rows:
        rows_ingested += 1
        b, minute_ts = _validate_row(row)
        # F-1/B-1: completeness means 15 DISTINCT source minutes, compared on the
        # plain UTC minute — a duplicate differing only in a sub-minute remainder
        # is rejected here rather than silently opening a second bucket. The
        # minute is claimed BEFORE the crossed-quote drop, so a dropped anomaly
        # cannot be quietly substituted by a second record for the same minute.
        if minute_ts in seen_minutes.setdefault(b, set()):
            raise AggregationError(
                f"duplicate source minute {minute_ts.isoformat()} in bucket {b.isoformat()}"
            )
        seen_minutes[b].add(minute_ts)
        # BL-4: drop-and-count, per the stage25_0a precedent. The row leaves no
        # bar behind, so the bucket becomes incomplete and loses eligibility —
        # a dropped minute is never replaced, imputed or back-filled.
        if _is_crossed_quote(row):
            dropped_crossed += 1
            continue
        buckets.setdefault(b, []).append((minute_ts, row))

    order = sorted(buckets)
    bars: list[dict] = []
    total_missing = 0
    all_minutes: list[datetime] = []
    for b in order:
        # Sort on the normalised minute, never on the caller's raw ``ts`` object.
        entries = sorted(buckets[b], key=lambda item: item[0])
        rows = [r for _, r in entries]
        all_minutes.extend(m for m, _ in entries)
        n = len(rows)
        if n > FULL_BUCKET_SOURCE_BARS:  # pragma: no cover - unreachable after F-1/B-1
            raise AggregationError(f"bucket {b.isoformat()} has {n} > 15 source bars")
        total_missing += FULL_BUCKET_SOURCE_BARS - n
        bid_c = rows[-1]["bid_c"]
        ask_c = rows[-1]["ask_c"]
        bar = {
            "ts": b,
            "n_source_bars": n,
            "eligible": n == FULL_BUCKET_SOURCE_BARS,
            "bid_o": rows[0]["bid_o"],
            "bid_h": max(r["bid_h"] for r in rows),
            "bid_l": min(r["bid_l"] for r in rows),
            "bid_c": bid_c,
            "ask_o": rows[0]["ask_o"],
            "ask_h": max(r["ask_h"] for r in rows),
            "ask_l": min(r["ask_l"] for r in rows),
            "ask_c": ask_c,
            "spread_close": ask_c - bid_c,
            "pip_size": pip,
        }
        _assert_bar_finite(bar)
        bars.append(bar)

    # BL-4 (second round): gap metrics are computed over every minute that HAD a
    # source record — retained or dropped — so they describe *source coverage*,
    # while the drop counters describe *quality rejection*. Computing them over
    # retained minutes only made a fully-dropped bucket vanish from `order`
    # entirely, so a file whose first bucket was 100% crossed reported
    # missing_whole_buckets=0, missing_minute_count=0, max_gap_minutes=0 — a
    # gapless, fully-eligible-looking file that had lost half its input.
    source_minutes = sorted(m for minutes in seen_minutes.values() for m in minutes)
    fully_dropped = sorted(b for b in seen_minutes if b not in buckets)
    gap_report = _build_gap_report(
        sorted(seen_minutes),
        source_minutes,
        bars,
        total_missing,
        pair,
        pip,
        dropped_crossed,
        rows_ingested,
        len(all_minutes),
        fully_dropped,
    )
    return bars, gap_report


def _assert_bar_finite(bar: dict) -> None:
    """R-6: derived outputs must be finite too, not only the inputs."""
    for key in (*_SIDE_KEYS, "spread_close", "pip_size"):
        v = bar[key]
        if not math.isfinite(v):
            raise AggregationError(f"derived bar value {key!r} is non-finite ({v!r})")
    # Reachable since BL-4 moved the bid/ask cross out of `_assert_row_coherent`:
    # a row object that changes between validation and bar construction can put
    # a negative spread here, and this is the last guard before it reaches the
    # cost model. (Previously marked `# pragma: no cover` on the premise that
    # row coherence forbade it — that premise no longer holds.)
    if bar["spread_close"] < 0:
        raise AggregationError(f"negative quoted spread_close {bar['spread_close']!r}")


def _build_gap_report(
    order: list[datetime],
    all_minutes: list[datetime],
    bars: list[dict],
    total_missing: int,
    pair: str,
    pip: float,
    dropped_crossed_quote_rows: int,
    rows_ingested: int,
    rows_retained: int,
    fully_dropped_buckets: list[datetime],
) -> dict:
    """Gap report with the schema keys the committed design inventory declares (R-7).

    ``max_gap_minutes`` is the largest run of consecutive missing source minutes
    between the first and last observed minute — minute-granular, so a 28-minute
    hole inside two adjacent buckets is no longer reported as ``0``. Whole
    missing buckets are still counted separately. No bars are synthesised.

    BL-4: ``dropped_crossed_quote_rows`` is the second half of drop-and-count —
    the drop is never silent. ``rows_ingested`` / ``rows_retained`` make the
    loss ratio explicit, and ``buckets_fully_dropped`` names the buckets that
    had source rows but emitted no bar, so a file that lost whole windows to
    anomalies cannot read as a gapless file.

    **The gap metrics describe SOURCE coverage, the drop counters describe
    quality rejection.** ``order`` and ``all_minutes`` are therefore built from
    every minute that HAD a source record, retained or dropped. Computing them
    from retained minutes only made a fully-dropped bucket disappear from the
    span entirely and reported the file as gapless.

    ``all_rows_dropped`` is reported rather than raised on: an acceptance
    threshold for the drop ratio would be an invented number, and this module
    does not mint contract constants. That threshold is referred alongside the
    BL-5 magnitude bound.

    RF-2 — ``missing_minute_count`` semantics, stated exactly so a reader cannot
    infer the wrong one. It counts absent minutes strictly BETWEEN the first and
    last minute that had a source record. It therefore:

    * counts market-closure minutes (weekends, holidays) like any other hole —
      on a real design-span file closure will dominate the figure;
    * counts nothing before the first or after the last observed minute, so a
      partial LEADING or TRAILING bucket contributes ``0`` here while
      ``total_missing_source_minutes_within_emitted_buckets`` counts it.

    Which of those the committed inventory's ``gap_report.missing_minute_count``
    is meant to record — all absent minutes, or only in-session ones — is a
    contract question this module may not settle on its own. It is referred as
    ``Requires separate contract Gate-decision``; both figures are emitted
    meanwhile so neither reading is silently assumed. The committed per-file
    ``gap_report`` object carries only ``missing_minute_count`` and
    ``max_gap_minutes``, so the drop counters would NOT survive into the
    inventory unless that schema is extended — which is itself part of the
    referral, not something this module may decide.
    """
    missing_whole_buckets = 0
    if order:
        cur, last, present = order[0], order[-1], set(order)
        while cur <= last:
            if cur not in present:
                missing_whole_buckets += 1
            cur += timedelta(minutes=BUCKET_MINUTES)

    missing_minute_count = 0
    max_gap_minutes = 0
    if all_minutes:
        minutes = sorted(all_minutes)
        for prev, nxt in zip(minutes, minutes[1:], strict=False):
            hole = int((nxt - prev).total_seconds() // 60) - 1
            if hole > 0:
                missing_minute_count += hole
                max_gap_minutes = max(max_gap_minutes, hole)

    return {
        "n_buckets_emitted": len(bars),
        "n_eligible": sum(1 for x in bars if x["eligible"]),
        "n_incomplete": sum(1 for x in bars if not x["eligible"]),
        "missing_minute_count": missing_minute_count,
        "max_gap_minutes": max_gap_minutes,
        "total_missing_source_minutes_within_emitted_buckets": total_missing,
        "missing_whole_buckets": missing_whole_buckets,
        "rows_ingested": rows_ingested,
        "rows_retained": rows_retained,
        "dropped_crossed_quote_rows": dropped_crossed_quote_rows,
        "buckets_fully_dropped": [b.isoformat() for b in fully_dropped_buckets],
        "all_rows_dropped": bool(rows_ingested) and rows_retained == 0,
        "imputation": False,
        "synthetic_weekend_bars": False,
        "mid_price_constructed": False,
        "pair": pair,
        "pip_size": pip,
    }
