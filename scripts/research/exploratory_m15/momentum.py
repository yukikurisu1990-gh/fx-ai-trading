"""The momentum route: `2021-04-26 … 2023-04-25`, unread history, and nothing else.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `POST_HOC_EXPLORATORY_HYPOTHESIS`.

Operations: `track_a_momentum_historical_read` and
`track_a_momentum_m15_derivation`. Scope
`MOMENTUM_SUPPLEMENTAL_EXPLORATORY_HISTORY`, which becomes `EXPLORATORY_SEEN_DATA`
the moment it is read and is never formal evidence.

A third route, not a widened second one
---------------------------------------

`bars` reads `2025-04-25 … 2025-12-28` and `supplemental` reads
`2023-04-26 … 2025-04-24`. Both are untouched. This module has its own constants
and its own guard, and that guard's upper bound is
`supplemental.SUPPLEMENTAL_START_UTC` itself, so the three windows partition the
archive by construction rather than by three separate opinions about where the
boundaries are:

    [2021-04-26 … 2023-04-25]  momentum      <- this module, unread until now
    [2023-04-26 … 2025-04-24]  supplemental  <- seen
    [2025-04-25 … 2025-12-28]  development   <- seen
    [2025-12-29 …          ]  OOS / dead / forward  <- forbidden to all three

The three defences the previous round's audit established are all carried over
rather than re-derived: a bound that is not an exact `YYYY-MM-DD` is refused
outright (string comparisons are sound only at fixed width, and a truncated bound
was shown to walk past two guards), the scan compares equal-width date prefixes
with no sentinel, and `load`/`build_cache` validate the **rows** they serve
rather than only the request that asked for them.

The signal is a negation, not a copy
------------------------------------

`_signal` returns `-round2._signal(...)`. Every gate in the reversal signal is
sign-symmetric: negation commutes with `where`, `ffill` and `fillna(0.0)`, and
the rollover block tests `decided != decided.shift(1)`, which is invariant under
negation. So negating the finished series is exactly negating the raw position
and changing nothing else — which is what "the exact mirror" has to mean if it is
to mean anything. A sign-swapped copy of the function would be identical today
and free to drift tomorrow, and it would put a second copy of a frozen rule in
the tree; the previous round's audit found one of those and it had already
drifted.
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Final

import pandas as pd

from scripts.research.exploratory_m15 import PAIRS, pip_size, round2, utc_date
from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.exploratory_m15 import supplemental as supp

#: Resolved from the archive manifest before any content was read and recorded in
#: `docs/research/m15_track_a_momentum_hypothesis_plan.md` at `c0ba1cd`.
MOMENTUM_START_UTC: Final[str] = "2021-04-26"
MOMENTUM_END_UTC: Final[str] = "2023-04-25"
#: The first date this route may not touch: the already-seen supplemental span.
#: Taken from that module rather than restated, so the two stay adjacent.
FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC: Final[str] = supp.SUPPLEMENTAL_START_UTC

#: `raise`, not `assert`: `python -O` strips `assert`, and a scope property that
#: disappears under an interpreter flag is not a property.
if (
    utc_date(FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC, field="supplemental start")
    - utc_date(MOMENTUM_END_UTC, field="momentum end")
) != timedelta(days=1):
    raise RuntimeError(
        f"{MOMENTUM_END_UTC} and {FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC} are not adjacent, "
        "so the three routes no longer partition the archive: either a gap has opened "
        "between them or they overlap."
    )

SCOPE: Final[str] = "MOMENTUM_SUPPLEMENTAL_EXPLORATORY_HISTORY"
SPAN_LABEL: Final[str] = "MOMENTUM_SUPPLEMENTAL_REPLICATION_B"
OPERATION_READ: Final[str] = "track_a_momentum_historical_read"
OPERATION_DERIVATION: Final[str] = "track_a_momentum_m15_derivation"

SOURCE_TEMPLATE: Final[str] = supp.SOURCE_TEMPLATE
CACHE_DIR: Final[Path] = (
    bars_module.REPO_ROOT / "artifacts" / "track_a_scratch" / "momentum_replication_b"
)

#: The candidate, frozen at `c0ba1cd` before the span was read. `lookback` and
#: `hold` come from `round2.CENTRE` so there is one definition, not two.
FROZEN_LOOKBACK: Final[int] = round2.CENTRE[0]
FROZEN_HOLD: Final[int] = round2.CENTRE[1]
FROZEN_ENTRY_Z: Final[float] = 1.0
NEIGHBOURHOOD: Final[tuple[int, ...]] = (384, 480, 576)


class MomentumSpanError(RuntimeError):
    """Raised when a request reaches outside the momentum span."""


def assert_momentum_span(start: str, end: str) -> None:
    """The guard for this route only. It relaxes no other guard.

    Comparisons are on the **parsed dates**, never on the caller's objects. An
    audit built a `str` subclass overriding `__lt__`/`__ge__` and walked all
    three guards, after which the reader decoded the whole ten-year archive —
    the OOS slice, the dead window and the forward epoch included. `utc_date`
    returns a real `datetime.date`, which no caller can poison, so the check is
    on a value this module derived rather than on one it was handed. For genuine
    strings the behaviour is unchanged: at fixed width, string order and date
    order coincide.
    """
    lo = utc_date(start, field="start")
    hi = utc_date(end, field="end")
    if hi < lo:
        raise MomentumSpanError(f"{start}..{end} is empty")
    if lo < utc_date(MOMENTUM_START_UTC, field="momentum start"):
        raise MomentumSpanError(
            f"{start} is before the resolved momentum span ({MOMENTUM_START_UTC}); "
            "the span was fixed from the archive manifest before any content was read "
            "and is not an argument"
        )
    if hi >= utc_date(FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC, field="supplemental start"):
        raise MomentumSpanError(
            f"{end} reaches {FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC} or later. That is the "
            "already-seen supplemental span, and beyond it the development corpus, the "
            "EXPLORATORY_OOS_SLICE, the dead window and the forward epoch. This route "
            "reads only history no round has looked at."
        )


def source_path(pair: str) -> Path:
    if pair not in PAIRS:
        raise ValueError(f"{pair!r} is not one of the twenty registered pairs")
    return bars_module.DATA_DIR / SOURCE_TEMPLATE.format(pair=pair)


def read_m1(
    pair: str,
    *,
    start: str = MOMENTUM_START_UTC,
    end: str = MOMENTUM_END_UTC,
) -> pd.DataFrame:
    """The pair's M1 rows inside the momentum span, and nothing else.

    The timestamp is taken from the line prefix **before** the row is parsed, so
    a row outside the window is never decoded — and under
    `HISTORICAL_EXPLORATORY_OOS_PRISTINE_CLAIM_WITHDRAWN` a decode is a read.
    Both bounds compare equal-width date prefixes against bounds the guard has
    already proved are exactly ten characters; the `break` is an optimisation, so
    an unsorted file under-reads rather than over-reads.
    """
    assert_momentum_span(start, end)
    path = source_path(pair)
    if not path.is_file():
        raise FileNotFoundError(f"{path.name} is not present under data/")
    times: list[str] = []
    columns: dict[str, list[float]] = {key: [] for key in bars_module.PRICE_KEYS}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            head = line[:64]
            quote = head.index('"time"')
            colon = head.index(":", quote)
            first = head.index('"', colon) + 1
            stamp = head[first : head.index('"', first)]
            day = stamp[:10]
            if day < start:
                continue
            if day > end:
                break
            row = json.loads(line)
            times.append(stamp)
            for key in bars_module.PRICE_KEYS:
                columns[key].append(float(row[key]))
    frame = pd.DataFrame(columns)
    frame["ts"] = pd.to_datetime(pd.Series(times, dtype="string"), format="ISO8601", utc=True)
    return frame


def assert_rows_in_span(frame: pd.DataFrame, *, pair: str) -> pd.DataFrame:
    """Refuse **rows** outside the span, not just requests that ask for them."""
    if frame.empty:
        raise MomentumSpanError(f"{pair}: the cached frame is empty")
    first, last = frame["ts"].min(), frame["ts"].max()
    lo = pd.Timestamp(MOMENTUM_START_UTC, tz="UTC")
    hi = pd.Timestamp(FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC, tz="UTC")
    if first < lo or last >= hi:
        raise MomentumSpanError(
            f"{pair}: cached bars run {first} … {last}, which leaves the momentum span "
            f"[{lo}, {hi}). The cache is not authoritative for what may be read."
        )
    return frame


def build_cache(
    pairs=PAIRS,
    *,
    start: str = MOMENTUM_START_UTC,
    end: str = MOMENTUM_END_UTC,
) -> dict[str, dict[str, object]]:
    """Derive the momentum-span M15 bars once, with the committed bucketing."""
    assert_momentum_span(start, end)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    summary: dict[str, dict[str, object]] = {}
    for pair in pairs:
        target = CACHE_DIR / f"m15_{pair}.parquet"
        if target.is_file():
            frame = assert_rows_in_span(pd.read_parquet(target), pair=pair)
        else:
            frame = assert_rows_in_span(
                bars_module.to_m15(read_m1(pair, start=start, end=end), pip_size=pip_size(pair)),
                pair=pair,
            )
            frame.to_parquet(target, index=False)
        summary[pair] = {
            "bars": int(len(frame)),
            "complete": int(frame["complete_bucket"].sum()),
            "incomplete": int((~frame["complete_bucket"]).sum()),
            "rows_ingested": int(frame["n_source_bars"].sum()),
            "first_ts": frame["ts"].iloc[0].isoformat(),
            "last_ts": frame["ts"].iloc[-1].isoformat(),
            "median_spread_pips": round(float(frame["spread_close_pips"].median()), 3),
        }
    return summary


def load(pair: str) -> pd.DataFrame:
    target = CACHE_DIR / f"m15_{pair}.parquet"
    if not target.is_file():
        raise FileNotFoundError(f"{target.name} is not cached; run build_cache first")
    return assert_rows_in_span(pd.read_parquet(target), pair=pair)


def load_all() -> dict[str, pd.DataFrame]:
    return {pair: load(pair) for pair in PAIRS}


def signal(
    frame: pd.DataFrame,
    *,
    lookback: int,
    hold: int,
    entry_z: float,
    phase: int,
    atr_bucket: str = "all",
) -> pd.Series:
    """The reversal signal, negated — long what rose, short what fell.

    See the module docstring for why this is a negation rather than a copy with
    the two constants swapped.
    """
    return -round2._signal(
        frame,
        lookback=lookback,
        hold=hold,
        entry_z=entry_z,
        phase=phase,
        atr_bucket=atr_bucket,
    )


__all__ = [
    "CACHE_DIR",
    "FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC",
    "FROZEN_ENTRY_Z",
    "FROZEN_HOLD",
    "FROZEN_LOOKBACK",
    "MOMENTUM_END_UTC",
    "MOMENTUM_START_UTC",
    "NEIGHBOURHOOD",
    "OPERATION_DERIVATION",
    "OPERATION_READ",
    "SCOPE",
    "SPAN_LABEL",
    "MomentumSpanError",
    "assert_momentum_span",
    "assert_rows_in_span",
    "build_cache",
    "load",
    "load_all",
    "read_m1",
    "signal",
    "source_path",
]
