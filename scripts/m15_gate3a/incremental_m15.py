"""One pair's M15 result, assembled from bounded batches instead of one list.

Why this lives in `m15_gate3a` and not in Track A
-------------------------------------------------

`aggregate_m15` computes its bars per bucket but its **gap report over the whole
call**: `bucket_starts`, `source_minutes`, `total_missing`, `rows_ingested` and
the minute accounting are all functions of everything it was handed. Aggregating
a pair in N batches therefore produces N partial reports, and a run that wants
one report for the pair has to combine the *inputs* — which means reaching
`_bucket_start`, `_plain_utc_minute`, `_build_gap_report` and
`_build_minute_accounting`.

Those are this package's private helpers, and `tests/m15_gate3a/test_wp5_reader_freedom.py`
pins what Track A may import from here as a list of **named symbols** — from
`aggregation`, exactly `BUCKET_MINUTES`, `FULL_BUCKET_SOURCE_BARS`,
`aggregate_m15` and `to_pips`. Widening that to admit four private accumulation
helpers into Track A would loosen a committed prohibition to make a memory
optimisation possible, which is not a trade this programme makes.

So the accumulation lives here, beside the function whose intermediate
quantities it is accumulating, and Track A imports one public class. The report
this produces is built by **the same** `_build_gap_report` and
`_build_minute_accounting` that `aggregate_m15` uses, on the union of the same
inputs — not by a second implementation of either.

What this does not do
---------------------

**It does not call the aggregator.** `aggregate_m15` refuses real rows outside
the window `scripts.m15_track_a.derivation.derive_m15` opens, and that is the
containment this package spent a round building. This class is handed the bars
and report a *completed, authorised* derivation returned, plus the rows that
produced them so it can normalise their minutes with the same helper the
aggregator used. It holds no raw row of its own after `absorb` returns.

Equivalence, and where it is proved
-----------------------------------

`tests/m15_track_a/test_r1_streaming.py` runs the same synthetic corpus through
one full-buffer `aggregate_m15` and through this accumulator at ten different
batch sizes and requires the bars, the gap reports and the whole R1 survey
record to be **identical** — no tolerance, because identical inputs to the same
function give identical floats and a tolerance here would be a contract term
invented to hide a difference that should not exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from scripts.m15_gate3a.aggregation import (
    _bucket_start,
    _build_gap_report,
    _build_minute_accounting,
    _plain_utc_minute,
)
from scripts.m15_gate3a.pair_authority import canonical_pair, pip_size_for_pair

#: The key an M1 row carries its timestamp under, matching the read route's
#: `ROW_TIMESTAMP_KEY` and the aggregator's own `_snapshot_row`.
ROW_TIMESTAMP_KEY = "ts"


class IncrementalM15Error(RuntimeError):
    """Raised when batches cannot be combined into one pair's result."""


@dataclass
class IncrementalM15:
    """Accumulate one pair's bars and gap-report inputs, batch by batch.

    Holds bars and minutes. Never raw rows: `absorb` reads each row's timestamp
    and keeps nothing else, so the caller is free to release the batch as soon
    as it returns.
    """

    pair: str
    _bars: list[dict[str, Any]] = field(default_factory=list)
    _observed_minutes: set[datetime] = field(default_factory=set)
    _bucket_starts: set[datetime] = field(default_factory=set)
    _total_missing: int = 0
    _rows_ingested: int = 0

    def __post_init__(self) -> None:
        # Canonical, and fail-closed on an unknown pair, exactly as
        # ``aggregate_m15`` does before it aggregates anything.
        self.pair = canonical_pair(self.pair)

    def absorb(
        self,
        bars: list[dict[str, Any]],
        gap_report: dict[str, Any],
        m1_rows: list[dict[str, Any]],
    ) -> None:
        """Take one batch's authorised output and the rows that produced it."""
        if type(bars) is not list:  # noqa: E721
            raise IncrementalM15Error(f"bars must be a list, got {type(bars).__name__}")
        if type(gap_report) is not dict:  # noqa: E721
            raise IncrementalM15Error(f"gap_report must be a dict, got {type(gap_report).__name__}")
        if type(m1_rows) is not list:  # noqa: E721
            raise IncrementalM15Error(f"m1_rows must be a list, got {type(m1_rows).__name__}")
        if gap_report.get("pair") != self.pair:
            raise IncrementalM15Error(
                f"gap report is for {gap_report.get('pair')!r} and this accumulator is for "
                f"{self.pair!r}"
            )

        for bar in bars:
            start = bar["ts"]
            if start in self._bucket_starts:
                # A bucket emitted by two batches means a batch boundary split
                # it, and two incomplete bars for one bucket is not the same
                # M15 series: an eligible bar becomes two ineligible ones. The
                # caller is expected to cut only on bucket boundaries; this
                # refuses rather than relying on that.
                raise IncrementalM15Error(
                    f"{self.pair}: bucket {start.isoformat()} was emitted by more than one "
                    "batch, so a batch boundary split it"
                )
            self._bucket_starts.add(start)
        self._bars.extend(bars)

        for row in m1_rows:
            # The aggregator's own normaliser, so a batch's minutes are the
            # minutes it counted — not this module's idea of them.
            self._observed_minutes.add(_plain_utc_minute(row[ROW_TIMESTAMP_KEY]))

        self._total_missing += int(
            gap_report["total_missing_source_minutes_within_emitted_buckets"]
        )
        self._rows_ingested += int(gap_report["rows_ingested"])

    def result(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """The pair's bars and its gap report, built by the committed builders.

        `observed == usable`: `aggregate_m15` records a minute *before*
        `_assert_row_usable` runs, and that function raises rather than
        rejecting, so every observed minute of a batch that aggregated
        successfully is a usable one. The same set is passed for both, which is
        what `aggregate_m15` effectively passes too.

        `expected=None` because R1 passes `expected_minutes=None`: there is no
        approved calendar artifact and Track A may not author one, so the
        calendar-derived accounting is absent rather than invented.
        """
        if not self._bars and not self._observed_minutes:
            raise IncrementalM15Error(
                f"{self.pair}: no batch carried a source minute, so there is nothing to report"
            )
        bars = sorted(self._bars, key=lambda bar: bar["ts"])
        report = _build_gap_report(
            bucket_starts=sorted({_bucket_start(m) for m in self._observed_minutes}),
            source_minutes=sorted(self._observed_minutes),
            bars=bars,
            total_missing=self._total_missing,
            pair=self.pair,
            pip=pip_size_for_pair(self.pair),
            rows_ingested=self._rows_ingested,
            minute_accounting=_build_minute_accounting(
                observed=self._observed_minutes,
                usable=self._observed_minutes,
                expected=None,
            ),
        )
        return bars, report


__all__ = ["IncrementalM15", "IncrementalM15Error", "ROW_TIMESTAMP_KEY"]
