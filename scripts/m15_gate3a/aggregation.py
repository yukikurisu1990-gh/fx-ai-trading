"""Pure M1->M15 aggregation (synthetic rows only; no real files, no imputation).

Implements the frozen contract: UTC 15-minute bucket start; per-side bid/ask
OHLC (open=first, high=max, low=min, close=last); NO mid-price construction;
``n_source_bars`` recorded; event/label eligibility iff ``n_source_bars == 15``;
incomplete buckets are diagnostics-only; missing minutes stay missing (no
imputation); no synthetic weekend bars (a bucket is emitted only where at least
one source minute exists); per-pair pip-size authority via
``data_adapter.pip_size_for`` (fail-closed on unknown pair).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Final

from scripts.ml_step4.data_adapter import pip_size_for  # single pip authority

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
    return price_delta / pip_size_for(pair)


def _bucket_start(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        raise AggregationError("M1 row timestamp must be tz-aware UTC")
    ts = ts.astimezone(UTC)
    return ts.replace(
        minute=(ts.minute // BUCKET_MINUTES) * BUCKET_MINUTES, second=0, microsecond=0
    )


def _validate_row(row: dict[str, Any]) -> datetime:
    ts = row.get("ts")
    if not isinstance(ts, datetime):
        raise AggregationError("M1 row missing tz-aware 'ts' datetime")
    for k in _SIDE_KEYS:
        if k not in row:
            raise AggregationError(f"M1 row missing side key {k!r}")
        if not isinstance(row[k], (int, float)):
            raise AggregationError(f"M1 row key {k!r} must be numeric")
    return _bucket_start(ts)


def aggregate_m15(m1_rows: list[dict[str, Any]], *, pair: str) -> tuple[list[dict], dict]:
    """Aggregate synthetic M1 bid/ask OHLC rows into M15 bars + a gap report.

    Returns ``(m15_bars, gap_report)``. Each M15 bar carries per-side OHLC, the
    closing quoted spread, ``n_source_bars``, ``eligible`` (== 15), and the
    per-pair ``pip_size`` — NO mid price is constructed. ``pip_size_for(pair)``
    fails closed on an unknown/empty pair before any aggregation.
    """
    pip = pip_size_for(pair)  # fail-closed FIRST (unknown pair -> PipSizeError)
    if not isinstance(m1_rows, list):
        raise AggregationError("m1_rows must be a list of synthetic M1 dicts")

    buckets: dict[datetime, list[dict[str, Any]]] = {}
    order: list[datetime] = []
    for row in m1_rows:
        b = _validate_row(row)
        if b not in buckets:
            buckets[b] = []
            order.append(b)
        buckets[b].append(row)

    order.sort()
    bars: list[dict] = []
    total_missing = 0
    for b in order:
        rows = sorted(buckets[b], key=lambda r: r["ts"])
        n = len(rows)
        if n > FULL_BUCKET_SOURCE_BARS:
            raise AggregationError(
                f"bucket {b.isoformat()} has {n} > 15 source bars (duplicate minutes?)"
            )
        total_missing += FULL_BUCKET_SOURCE_BARS - n
        bid_c = rows[-1]["bid_c"]
        ask_c = rows[-1]["ask_c"]
        bars.append(
            {
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
        )

    # Gap report: contiguous 15-min windows between the first and last emitted
    # bucket that received NO source minutes (i.e. missing whole buckets). No
    # synthetic bars are created for them — they are only counted.
    missing_whole_buckets = 0
    max_gap_minutes = 0
    if order:
        cur = order[0]
        last = order[-1]
        present = set(order)
        run = 0
        while cur <= last:
            if cur not in present:
                missing_whole_buckets += 1
                run += BUCKET_MINUTES
                max_gap_minutes = max(max_gap_minutes, run)
            else:
                run = 0
            cur = cur + timedelta(minutes=BUCKET_MINUTES)

    gap_report = {
        "n_buckets_emitted": len(bars),
        "n_eligible": sum(1 for x in bars if x["eligible"]),
        "n_incomplete": sum(1 for x in bars if not x["eligible"]),
        "total_missing_source_minutes_within_emitted_buckets": total_missing,
        "missing_whole_buckets": missing_whole_buckets,
        "max_gap_minutes": max_gap_minutes,
        "imputation": False,
        "synthetic_weekend_bars": False,
        "mid_price_constructed": False,
        "pair": pair,
        "pip_size": pip,
    }
    return bars, gap_report
