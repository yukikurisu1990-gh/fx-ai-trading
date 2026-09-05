"""M1 → M15 for exploration, and a cache so a research loop is not I/O bound.

`NON_DECISION_BEARING_EXPLORATORY_ONLY`.

The bucketing follows the committed rules — UTC 15-minute grid, per-side OHLC,
`complete_bucket` when all fifteen source minutes are present — because the
object being explored should be the object R1 measured. It is checked against
R1's published per-pair counts rather than assumed equal to them.

The one thing this file guards hard is the **span**. Every read is clipped to
`2025-04-25 … 2025-12-28` before a row is kept, and a request that names a date
at or after `2025-12-29` is refused outright. The `EXPLORATORY_OOS_SLICE`, the
dead window and the forward epoch all sit after that date in the same archive.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import (
    DEVELOPMENT_END_UTC,
    DEVELOPMENT_START_UTC,
    FIRST_FORBIDDEN_UTC,
    PAIRS,
    pip_size,
    utc_date,
)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
DATA_DIR: Final[Path] = REPO_ROOT / "data"
CACHE_DIR: Final[Path] = REPO_ROOT / "artifacts" / "track_a_scratch" / "exploratory_round_1"
SOURCE_TEMPLATE: Final[str] = "candles_{pair}_M1_365d_BA.jsonl"

BUCKET_MINUTES: Final[int] = 15
#: `SESSIONS_UTC` spells these as strings; the boundaries are what matter here.
SESSION_BOUNDS: Final[dict[str, tuple[int, int]]] = {
    "asia": (0, 8),
    "europe": (8, 16),
    "us": (16, 24),
}
ROLLOVER_START_MINUTE: Final[int] = 21 * 60 + 55
ROLLOVER_END_MINUTE: Final[int] = 22 * 60 + 15

PRICE_KEYS: Final[tuple[str, ...]] = (
    "bid_o",
    "bid_h",
    "bid_l",
    "bid_c",
    "ask_o",
    "ask_h",
    "ask_l",
    "ask_c",
)


class ExploratorySpanError(RuntimeError):
    """Raised when a request reaches outside the authorised development span."""


def _assert_span(start: str, end: str) -> None:
    #: Refuse a malformed bound before comparing it. This guard's comparisons are
    #: string comparisons, which are sound only for fixed-width dates: an
    #: independent audit showed `end="2025-12-2"` passes `end >=
    #: FIRST_FORBIDDEN_UTC` and then, through the `end + "T99"` sentinel below,
    #: lets OOS rows reach `json.loads`. The check strictly *narrows* what this
    #: guard accepts -- every well-formed span it admitted before, it still
    #: admits, and every span it refused, it still refuses.
    if utc_date(end, field="end") < utc_date(start, field="start"):
        raise ExploratorySpanError(f"{start}..{end} is empty")
    if start < DEVELOPMENT_START_UTC:
        raise ExploratorySpanError(
            f"{start} is before the development corpus starts ({DEVELOPMENT_START_UTC})"
        )
    if end >= FIRST_FORBIDDEN_UTC:
        raise ExploratorySpanError(
            f"{end} reaches {FIRST_FORBIDDEN_UTC} or later. That is the "
            "EXPLORATORY_OOS_SLICE, and neither it nor the dead window nor the forward "
            "epoch is authorised for exploration."
        )


def source_path(pair: str) -> Path:
    return DATA_DIR / SOURCE_TEMPLATE.format(pair=pair)


def read_m1(pair: str, *, start: str = DEVELOPMENT_START_UTC, end: str = DEVELOPMENT_END_UTC):
    """The pair's M1 rows inside the span, as a DataFrame. Nothing outside it.

    The scan stops at the first timestamp past the window: the archive continues
    into the slice, and there is no reason for a research loop to walk into it.
    """
    _assert_span(start, end)
    path = source_path(pair)
    if not path.is_file():
        raise FileNotFoundError(f"{path.name} is not present under data/")
    times: list[str] = []
    columns: dict[str, list[float]] = {key: [] for key in PRICE_KEYS}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            #: the timestamp before the row, so a row past the window is never
            #: parsed -- the defect R1's read route was found to have
            head = line[:64]
            quote = head.index('"time"')
            colon = head.index(":", quote)
            first = head.index('"', colon) + 1
            stamp = head[first : head.index('"', first)]
            #: Both bounds compare the row's **date prefix** against a bound
            #: already known to be exactly ten characters, so the two strings are
            #: the same width and string order is date order. The previous upper
            #: bound compared the full stamp against an `end + "T99"` sentinel,
            #: which is only correct when `end` is well formed -- and the guard
            #: did not require that.
            day = stamp[:10]
            if day < start:
                continue
            if day > end:
                break
            row = json.loads(line)
            times.append(stamp)
            for key in PRICE_KEYS:
                columns[key].append(float(row[key]))
    frame = pd.DataFrame(columns)
    frame["ts"] = pd.to_datetime(pd.Series(times, dtype="string"), format="ISO8601", utc=True)
    return frame


def to_m15(m1: pd.DataFrame, *, pip_size: float) -> pd.DataFrame:
    """Aggregate M1 to the committed UTC 15-minute grid, per side."""
    if m1.empty:
        return pd.DataFrame()
    bucket = m1["ts"].dt.floor(f"{BUCKET_MINUTES}min")
    grouped = m1.groupby(bucket, sort=True)
    bars = pd.DataFrame(
        {
            "bid_o": grouped["bid_o"].first(),
            "bid_h": grouped["bid_h"].max(),
            "bid_l": grouped["bid_l"].min(),
            "bid_c": grouped["bid_c"].last(),
            "ask_o": grouped["ask_o"].first(),
            "ask_h": grouped["ask_h"].max(),
            "ask_l": grouped["ask_l"].min(),
            "ask_c": grouped["ask_c"].last(),
            "n_source_bars": grouped.size(),
        }
    )
    bars.index.name = "ts"
    bars = bars.reset_index()
    bars["complete_bucket"] = bars["n_source_bars"] == BUCKET_MINUTES
    bars["mid_o"] = (bars["bid_o"] + bars["ask_o"]) / 2.0
    bars["mid_h"] = (bars["bid_h"] + bars["ask_h"]) / 2.0
    bars["mid_l"] = (bars["bid_l"] + bars["ask_l"]) / 2.0
    bars["mid_c"] = (bars["bid_c"] + bars["ask_c"]) / 2.0
    bars["spread_close_pips"] = (bars["ask_c"] - bars["bid_c"]) / pip_size
    minute_of_day = bars["ts"].dt.hour * 60 + bars["ts"].dt.minute
    bars["rollover"] = (minute_of_day < ROLLOVER_END_MINUTE) & (
        minute_of_day + BUCKET_MINUTES > ROLLOVER_START_MINUTE
    )
    hour = bars["ts"].dt.hour
    session = np.full(len(bars), "us", dtype=object)
    for name, (lo, hi) in SESSION_BOUNDS.items():
        session[(hour >= lo) & (hour < hi)] = name
    bars["session"] = session
    bars["pip_size"] = pip_size
    return bars


def build_cache(pairs=PAIRS, *, start: str = DEVELOPMENT_START_UTC, end: str = DEVELOPMENT_END_UTC):
    """Derive every pair's M15 bars once and park them under the scratch root."""
    _assert_span(start, end)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    summary = {}
    for pair in pairs:
        target = CACHE_DIR / f"m15_{pair}.parquet"
        if target.is_file():
            bars = pd.read_parquet(target)
        else:
            bars = to_m15(read_m1(pair, start=start, end=end), pip_size=pip_size(pair))
            bars.to_parquet(target, index=False)
        summary[pair] = {
            "bars": int(len(bars)),
            "complete": int(bars["complete_bucket"].sum()),
            "incomplete": int((~bars["complete_bucket"]).sum()),
            "first_ts": bars["ts"].iloc[0].isoformat(),
            "last_ts": bars["ts"].iloc[-1].isoformat(),
            "rows_ingested": int(bars["n_source_bars"].sum()),
        }
    return summary


def load(pair: str) -> pd.DataFrame:
    target = CACHE_DIR / f"m15_{pair}.parquet"
    if not target.is_file():
        raise FileNotFoundError(f"{target.name} is not cached; run build_cache first")
    return pd.read_parquet(target)


__all__ = [
    "BUCKET_MINUTES",
    "CACHE_DIR",
    "ExploratorySpanError",
    "build_cache",
    "load",
    "read_m1",
    "to_m15",
]
