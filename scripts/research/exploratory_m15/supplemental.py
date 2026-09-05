"""The supplemental history route: `2023-04-26 … 2025-04-24`, and nothing else.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Operations: `track_a_supplemental_historical_read` and
`track_a_supplemental_m15_derivation`. Scope:
`SUPPLEMENTAL_EXPLORATORY_HISTORY`, which becomes `EXPLORATORY_SEEN_DATA` the
moment it is read and is never formal evidence.

Why this is a separate module rather than a parameter
-----------------------------------------------------

`bars._assert_span` refuses anything before `2025-04-25` or at/after
`2025-12-29`. The obvious way to read earlier history is to make its bounds
arguments — and that turns a prohibition into a default, which is how a guard
stops guarding. The instruction was explicit: do not weaken the existing guard,
add an authorisation route limited to the new operation.

So `bars._assert_span` is untouched and still refuses exactly what it refused
before. This module has **its own** constants and **its own** guard, and that
guard is narrower than the one it sits beside: it refuses anything at or after
`2025-04-25` as well as anything before `2023-04-26`. Neither route can reach the
other's window, and neither can reach the `EXPLORATORY_OOS_SLICE`, the dead
window or the forward epoch.

That last point is not theoretical. The source here is the **ten-year** archive,
which physically contains the OOS slice, the dead window, the forward epoch and
data up to 2026-05-29. The development reader could rely on its file ending
shortly after its window; this one cannot rely on anything, so it clips at both
ends and stops scanning the moment it passes its own end date.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import pandas as pd

from scripts.research.exploratory_m15 import DEVELOPMENT_START_UTC, PAIRS, pip_size
from scripts.research.exploratory_m15 import bars as bars_module

#: The span, resolved from the archive manifest before any content was read and
#: recorded in `docs/research/m15_track_a_supplemental_replication_plan.md`.
SUPPLEMENTAL_START_UTC: Final[str] = "2023-04-26"
SUPPLEMENTAL_END_UTC: Final[str] = "2025-04-24"
#: The first date this route may **not** touch, taken from the development corpus
#: rather than restated. The package already exports a `FIRST_FORBIDDEN_UTC`
#: meaning `2025-12-29`, so a second constant of that name meaning `2025-04-25`
#: would be two different walls under one name. Tying the bound to
#: `DEVELOPMENT_START_UTC` also keeps the two routes exactly adjacent: no gap can
#: open between them, and no overlap.
FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC: Final[str] = DEVELOPMENT_START_UTC

#: The recorded span ends the day before the development corpus begins. Asserted
#: at import rather than left as a comment, because "adjacent" is the property
#: that makes the pair of guards a partition instead of two opinions.
assert SUPPLEMENTAL_END_UTC < FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC
assert (
    pd.Timestamp(FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC) - pd.Timestamp(SUPPLEMENTAL_END_UTC)
).days == 1

SCOPE: Final[str] = "SUPPLEMENTAL_EXPLORATORY_HISTORY"
OPERATION_READ: Final[str] = "track_a_supplemental_historical_read"
OPERATION_DERIVATION: Final[str] = "track_a_supplemental_m15_derivation"

SOURCE_TEMPLATE: Final[str] = "candles_{pair}_M1_3650d_BA.jsonl"
MANIFEST: Final[Path] = (
    bars_module.REPO_ROOT / "artifacts" / "oanda_archive_2026-05-31" / "candles_manifest.json"
)
CACHE_DIR: Final[Path] = (
    bars_module.REPO_ROOT / "artifacts" / "track_a_scratch" / "supplemental_replication"
)


class SupplementalSpanError(RuntimeError):
    """Raised when a request reaches outside the supplemental span."""


def assert_supplemental_span(start: str, end: str) -> None:
    """The guard for this route only. It does not relax any other guard."""
    if start < SUPPLEMENTAL_START_UTC:
        raise SupplementalSpanError(
            f"{start} is before the resolved supplemental span "
            f"({SUPPLEMENTAL_START_UTC}); the span was fixed from the archive manifest "
            "before any content was read and is not an argument"
        )
    if end >= FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC:
        raise SupplementalSpanError(
            f"{end} reaches {FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC} or later. That is the "
            "development corpus "
            "and beyond it the EXPLORATORY_OOS_SLICE, the dead window and the forward epoch. "
            "This route reads history strictly before the development window."
        )
    if end < start:
        raise SupplementalSpanError(f"{start}..{end} is empty")


def source_path(pair: str) -> Path:
    if pair not in PAIRS:
        raise ValueError(f"{pair!r} is not one of the twenty registered pairs")
    return bars_module.DATA_DIR / SOURCE_TEMPLATE.format(pair=pair)


def manifest_coverage() -> dict[str, tuple[str, str]]:
    """`(first, last)` UTC dates per pair, from the manifest — not from the data."""
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {
        entry["pair"]: (entry["first_time"][:10], entry["last_time"][:10])
        for entry in payload["files"]
        if entry["granularity"] == "M1" and entry["days"] == 3650
    }


def read_m1(
    pair: str,
    *,
    start: str = SUPPLEMENTAL_START_UTC,
    end: str = SUPPLEMENTAL_END_UTC,
) -> pd.DataFrame:
    """The pair's M1 rows inside the supplemental span, and nothing else.

    The timestamp is extracted from the line prefix **before** the row is parsed,
    so a row outside the window is never decoded — the defect R1's gated reader
    was found to have, and one that matters far more here because the file
    continues into the OOS slice and past it.
    """
    assert_supplemental_span(start, end)
    path = source_path(pair)
    if not path.is_file():
        raise FileNotFoundError(f"{path.name} is not present under data/")
    stop = end + "T99"
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
            if stamp[:10] < start:
                continue
            if stamp > stop:
                break
            row = json.loads(line)
            times.append(stamp)
            for key in bars_module.PRICE_KEYS:
                columns[key].append(float(row[key]))
    frame = pd.DataFrame(columns)
    frame["ts"] = pd.to_datetime(pd.Series(times, dtype="string"), format="ISO8601", utc=True)
    return frame


def build_cache(
    pairs=PAIRS,
    *,
    start: str = SUPPLEMENTAL_START_UTC,
    end: str = SUPPLEMENTAL_END_UTC,
) -> dict[str, dict[str, object]]:
    """Derive the supplemental M15 bars once, with the committed bucketing."""
    assert_supplemental_span(start, end)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    summary: dict[str, dict[str, object]] = {}
    for pair in pairs:
        target = CACHE_DIR / f"m15_{pair}.parquet"
        if target.is_file():
            frame = pd.read_parquet(target)
        else:
            frame = bars_module.to_m15(read_m1(pair, start=start, end=end), pip_size=pip_size(pair))
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
    return pd.read_parquet(target)


def load_all() -> dict[str, pd.DataFrame]:
    return {pair: load(pair) for pair in PAIRS}


__all__ = [
    "CACHE_DIR",
    "FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC",
    "OPERATION_DERIVATION",
    "OPERATION_READ",
    "SCOPE",
    "SUPPLEMENTAL_END_UTC",
    "SUPPLEMENTAL_START_UTC",
    "SupplementalSpanError",
    "assert_supplemental_span",
    "build_cache",
    "load",
    "load_all",
    "manifest_coverage",
    "read_m1",
]
