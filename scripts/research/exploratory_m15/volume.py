"""Tick-count volume, recovered over the three already-seen spans. Nothing else.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The archive writer emits a `volume` field per M1 row — the tick count OANDA
reports for that minute — and every research reader in this package copies only
`bars.PRICE_KEYS` out of each decoded row, so the field has never reached an M15
cache. Round B′ established that recovering it needs a content read of spans that
are **already seen**, not a new span, and referred it. That read is authorised for
this package over those three spans and no others.

Why this is a separate module
-----------------------------

`PRICE_KEYS` and the three readers are **not touched**. Widening them would
rewrite what every committed M15 cache contains and put a data-boundary change
inside a research task; this module reads the same files for one extra field and
writes its own cache beside them.

The span guards are **called, not re-implemented**
--------------------------------------------------

Each route already owns the only bound it may be read under, and those bounds are
the thing three audits have hardened — against a truncated `"2025"`, against a
`str` subclass overriding `__lt__`, and against an `end + "T99"` sentinel. This
module dispatches to `bars._assert_span`, `supplemental.assert_supplemental_span`
and `momentum.assert_momentum_span`, so there is no second copy of a bound to
drift, and weakening one would fail those routes' own tests rather than silently
widening this one.

The scan is the routes' own shape too: the timestamp is read out of the line
prefix and compared **before** `json.loads`, so a row outside the window is never
decoded. That is the defect R1's reader was found to have.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final, NamedTuple

import pandas as pd

from scripts.research.exploratory_m15 import PAIRS, pip_size, utc_date
from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.exploratory_m15 import momentum as momentum_module
from scripts.research.exploratory_m15 import supplemental as supplemental_module

#: the one field this module is authorised to recover
VOLUME_KEY: Final[str] = "volume"

CACHE_DIR: Final[Path] = (
    bars_module.REPO_ROOT / "artifacts" / "track_a_scratch" / "monetizability" / "volume_cache"
)


class Route(NamedTuple):
    """One authorised span, with the guard and the file that belong to it."""

    name: str
    start: str
    end: str
    guard: Callable[[str, str], None]
    source: Callable[[str], Path]


ROUTES: Final[dict[str, Route]] = {
    "momentum_2021_2023": Route(
        "momentum_2021_2023",
        momentum_module.MOMENTUM_START_UTC,
        momentum_module.MOMENTUM_END_UTC,
        momentum_module.assert_momentum_span,
        momentum_module.source_path,
    ),
    "supplemental_2023_2025": Route(
        "supplemental_2023_2025",
        supplemental_module.SUPPLEMENTAL_START_UTC,
        supplemental_module.SUPPLEMENTAL_END_UTC,
        supplemental_module.assert_supplemental_span,
        supplemental_module.source_path,
    ),
    "development_2025": Route(
        "development_2025",
        bars_module.DEVELOPMENT_START_UTC,
        bars_module.DEVELOPMENT_END_UTC,
        bars_module._assert_span,
        bars_module.source_path,
    ),
}


class VolumeSpanError(RuntimeError):
    """Raised when a volume read is asked for a span its route will not admit."""


def read_m1_volume(panel: str, pair: str, *, start: str | None = None, end: str | None = None):
    """The pair's M1 `(ts, volume)` rows inside the panel's own span.

    `start` and `end` default to the route's own constants and are passed through
    that route's guard whatever they are, so a caller cannot widen the window by
    supplying one.
    """
    if panel not in ROUTES:
        raise VolumeSpanError(f"{panel!r} is not one of the three authorised panels")
    route = ROUTES[panel]
    if pair not in PAIRS:
        raise VolumeSpanError(f"{pair!r} is not one of the twenty registered pairs")
    #: called for its own validation, and to keep the pair authority in the loop
    pip_size(pair)
    lo = route.start if start is None else start
    hi = route.end if end is None else end
    #: the route's own guard, not a copy of its bounds
    route.guard(lo, hi)
    #: and the parsed dates, so the scan below compares equal-width prefixes
    utc_date(lo, field="volume read start")
    utc_date(hi, field="volume read end")

    path = route.source(pair)
    if not path.is_file():
        raise FileNotFoundError(f"{path.name} is not present under data/")

    times: list[str] = []
    volumes: list[int] = []
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
            if day < lo:
                continue
            if day > hi:
                break
            row = json.loads(line)
            times.append(stamp)
            #: absent rather than zero would be a data fact worth seeing, so a
            #: missing key becomes NaN here and is counted, not silently zeroed
            volumes.append(row.get(VOLUME_KEY))

    frame = pd.DataFrame({"volume": pd.Series(volumes, dtype="Float64")})
    frame["ts"] = pd.to_datetime(pd.Series(times, dtype="string"), format="ISO8601", utc=True)
    return frame


def to_m15_volume(m1: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to the committed UTC 15-minute grid. Volume is a **sum**."""
    if m1.empty:
        return pd.DataFrame(columns=["ts", "volume", "volume_bars", "volume_missing"])
    bucket = m1["ts"].dt.floor(f"{bars_module.BUCKET_MINUTES}min")
    grouped = m1.groupby(bucket, sort=True)
    bars = pd.DataFrame(
        {
            "volume": grouped["volume"].sum(min_count=1),
            "volume_bars": grouped["volume"].size(),
            "volume_missing": grouped["volume"].apply(lambda s: int(s.isna().sum())),
        }
    )
    bars.index.name = "ts"
    return bars.reset_index()


def assert_rows_in_span(frame: pd.DataFrame, panel: str) -> pd.DataFrame:
    """Every retained row is inside the panel's declared span, or nothing is.

    The scan's `break` is an optimisation that trusts the file's ordering; this
    checks the rows that actually came back, which does not.
    """
    route = ROUTES[panel]
    if frame.empty:
        return frame
    day = frame["ts"].dt.strftime("%Y-%m-%d")
    outside = frame[(day < route.start) | (day > route.end)]
    if len(outside):
        raise VolumeSpanError(
            f"{len(outside)} {panel} rows fall outside {route.start}..{route.end}; "
            f"first is {outside['ts'].iloc[0]}"
        )
    return frame


def build_cache(panel: str, pairs: tuple[str, ...] = bars_module.PAIRS) -> dict[str, Any]:
    """Recover the panel's volume once and cache it. Returns what was read."""
    route = ROUTES[panel]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "panel": panel,
        "declared_span": [route.start, route.end],
        "guard": route.guard.__module__ + "." + route.guard.__name__,
        "source_template": route.source(pairs[0]).name.replace(pairs[0], "{pair}"),
        "pairs": {},
    }
    for pair in pairs:
        target = CACHE_DIR / f"volume_{panel}_{pair}.parquet"
        if target.is_file():
            frame = pd.read_parquet(target)
        else:
            m1 = read_m1_volume(panel, pair)
            assert_rows_in_span(m1, panel)
            frame = to_m15_volume(m1)
            assert_rows_in_span(frame, panel)
            frame.to_parquet(target, index=False)
        record["pairs"][pair] = {
            "m15_bars": int(len(frame)),
            "measured_span": [
                str(frame["ts"].min().date()),
                str(frame["ts"].max().date()),
            ]
            if len(frame)
            else None,
        }
    return record


def load(panel: str, pair: str) -> pd.DataFrame:
    target = CACHE_DIR / f"volume_{panel}_{pair}.parquet"
    if not target.is_file():
        raise FileNotFoundError(f"{target.name} is not built; call build_cache({panel!r}) first")
    return assert_rows_in_span(pd.read_parquet(target), panel)


def load_panel(panel: str, pairs: tuple[str, ...] = bars_module.PAIRS) -> dict[str, pd.DataFrame]:
    return {pair: load(panel, pair) for pair in pairs}


__all__ = [
    "CACHE_DIR",
    "ROUTES",
    "VOLUME_KEY",
    "Route",
    "VolumeSpanError",
    "assert_rows_in_span",
    "build_cache",
    "load",
    "load_panel",
    "read_m1_volume",
    "to_m15_volume",
]
