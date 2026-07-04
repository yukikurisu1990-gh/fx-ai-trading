"""Deterministic chronological split builder (fail-closed).

Derives the common cross-pair window from per-pair timestamp metadata, then
produces chronological 70/15/15 train/validation/holdout boundaries with a
purge/embargo of ``horizon + 1`` M1 bars at every earlier-segment boundary.

The builder is pure and deterministic (no wall-clock): identical inputs →
identical boundaries. It fails closed on missing, inconsistent, or unparseable
timestamps, or a non-overlapping common window.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from . import contract

_BAR_SECONDS = 60  # M1


class SplitError(RuntimeError):
    """Raised when a deterministic split cannot be built."""


@dataclass(frozen=True)
class PairWindow:
    """Per-pair inclusive timestamp bounds (UTC)."""

    filename: str
    ts_min_utc: str
    ts_max_utc: str


def _parse(ts: str) -> datetime:
    if not isinstance(ts, str) or not ts:
        raise SplitError(f"timestamp missing/blank: {ts!r}")
    text = ts.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SplitError(f"unparseable timestamp {ts!r}: {exc}") from exc
    if dt.tzinfo is None:
        raise SplitError(f"timestamp {ts!r} is not timezone-aware (UTC required)")
    return dt.astimezone(UTC)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def common_window(pair_windows: Iterable[PairWindow]) -> tuple[datetime, datetime]:
    """Common cross-pair window: ``max(ts_min)`` .. ``min(ts_max)``; fail closed."""
    windows = list(pair_windows)
    if not windows:
        raise SplitError("no pair windows provided")
    mins: list[datetime] = []
    maxs: list[datetime] = []
    for w in windows:
        lo = _parse(w.ts_min_utc)
        hi = _parse(w.ts_max_utc)
        if lo >= hi:
            raise SplitError(f"pair {w.filename} has ts_min >= ts_max")
        mins.append(lo)
        maxs.append(hi)
    start = max(mins)
    end = min(maxs)
    if start >= end:
        raise SplitError("common cross-pair window is empty (no overlap)")
    return start, end


def build_split(
    pair_windows: Iterable[PairWindow],
    *,
    fractions: tuple[float, float, float] = contract.SPLIT_FRACTIONS,
    purge_bars: int = contract.PURGE_EMBARGO_BARS,
    bar_seconds: int = _BAR_SECONDS,
) -> dict[str, Any]:
    """Build deterministic 70/15/15 boundaries with purge/embargo.

    Fractions apply to the *time span* of the common window. Purge drops the
    last ``purge_bars`` bars of each earlier segment from label-eligible rows.
    """
    if len(fractions) != 3 or abs(sum(fractions) - 1.0) > 1e-9:
        raise SplitError(f"fractions must be three values summing to 1.0: {fractions}")
    if any(f <= 0 for f in fractions):
        raise SplitError(f"fractions must be positive: {fractions}")
    if purge_bars < 0:
        raise SplitError(f"purge_bars must be >= 0: {purge_bars}")

    start, end = common_window(pair_windows)
    total_seconds = (end - start).total_seconds()
    purge_seconds = purge_bars * bar_seconds
    if total_seconds <= 2 * purge_seconds:
        raise SplitError("common window too short for the requested purge/embargo")

    train_frac, val_frac, _ = fractions
    train_end = start.timestamp() + train_frac * total_seconds
    val_end = start.timestamp() + (train_frac + val_frac) * total_seconds

    def _dt(epoch: float) -> datetime:
        return datetime.fromtimestamp(epoch, tz=UTC)

    train_end_dt = _dt(train_end)
    val_end_dt = _dt(val_end)
    train_label_end_dt = _dt(train_end - purge_seconds)
    val_label_end_dt = _dt(val_end - purge_seconds)

    if not (start < train_label_end_dt < train_end_dt < val_label_end_dt < val_end_dt < end):
        raise SplitError("degenerate boundaries after purge/embargo")

    return {
        "common_window": {"start_utc": _iso(start), "end_utc": _iso(end)},
        "fractions": {"train": train_frac, "validation": val_frac, "holdout": fractions[2]},
        "purge_embargo_bars": purge_bars,
        "bar_seconds": bar_seconds,
        "segments": {
            "train": {
                "start_utc": _iso(start),
                "end_utc": _iso(train_end_dt),
                "label_eligible_end_utc": _iso(train_label_end_dt),
            },
            "validation": {
                "start_utc": _iso(train_end_dt),
                "end_utc": _iso(val_end_dt),
                "label_eligible_end_utc": _iso(val_label_end_dt),
            },
            "holdout": {
                "start_utc": _iso(val_end_dt),
                "end_utc": _iso(end),
                "evaluated_once": True,
            },
        },
        "deterministic": True,
    }
