"""No-overlap proof utilities (metadata-only) against the consumed dead window.

Implements PR #430 T-7 + R-2b at the code level: design artifacts must end on or
before ``DESIGN_END``; forward artifacts must begin on or after
``FORWARD_FLOOR``; the dead window (the consumed M1 holdout) must be absent from
every role. Fail-closed; fixture-tested; reads no data.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Final

DESIGN_START: Final[datetime] = datetime(2025, 4, 25, 0, 0, 0, tzinfo=UTC)
DESIGN_END: Final[datetime] = datetime(2026, 2, 28, 23, 59, 59, tzinfo=UTC)
DEAD_START: Final[datetime] = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)
DEAD_END: Final[datetime] = datetime(2026, 4, 24, 23, 59, 59, tzinfo=UTC)
FORWARD_FLOOR: Final[datetime] = datetime(2026, 4, 25, 0, 0, 0, tzinfo=UTC)


class NoOverlapError(RuntimeError):
    """Raised when an artifact role overlaps the dead window or violates bounds."""


def _parse(ts: Any) -> datetime:
    """Parse a timestamp; F-5 fix: naive inputs FAIL CLOSED (never assumed UTC).

    Accepts tz-aware ``datetime`` objects and ISO strings with an explicit
    ``Z`` / ``+00:00`` / other offset (converted to UTC deterministically).
    Timezone-naive datetimes and offset-less ISO strings are rejected.
    """
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            raise NoOverlapError(f"naive datetime rejected (no tzinfo): {ts.isoformat()}")
        return ts.astimezone(UTC)
    if isinstance(ts, str) and ts.strip():
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise NoOverlapError(f"ISO string without explicit offset rejected: {ts!r}")
        return parsed.astimezone(UTC)
    raise NoOverlapError(f"unparseable timestamp: {ts!r}")


def _intersects_dead_window(ts_min: datetime, ts_max: datetime) -> bool:
    return not (ts_max < DEAD_START or ts_min > DEAD_END)


def assert_design_bounds(ts_min: Any, ts_max: Any) -> None:
    """Design artifact must sit within [DESIGN_START, DESIGN_END] and miss dead window."""
    lo, hi = _parse(ts_min), _parse(ts_max)
    if hi > DESIGN_END:
        raise NoOverlapError(
            f"design ts_max {hi.isoformat()} > DESIGN_END {DESIGN_END.isoformat()}"
        )
    if lo < DESIGN_START:
        raise NoOverlapError(
            f"design ts_min {lo.isoformat()} < DESIGN_START {DESIGN_START.isoformat()}"
        )
    if _intersects_dead_window(lo, hi):
        raise NoOverlapError("design artifact intersects the dead window")


def assert_forward_bounds(ts_min: Any, ts_max: Any) -> None:
    """Forward artifact must begin >= FORWARD_FLOOR and miss the dead window."""
    lo, hi = _parse(ts_min), _parse(ts_max)
    if lo < FORWARD_FLOOR:
        raise NoOverlapError(
            f"forward ts_min {lo.isoformat()} < FORWARD_FLOOR {FORWARD_FLOOR.isoformat()}"
        )
    if _intersects_dead_window(lo, hi):
        raise NoOverlapError("forward artifact intersects the dead window")


def assert_no_dead_window(ts_min: Any, ts_max: Any, *, role: str) -> None:
    """Any role's span must not intersect the dead window (fail-closed)."""
    lo, hi = _parse(ts_min), _parse(ts_max)
    if hi < lo:
        raise NoOverlapError(f"{role}: ts_max < ts_min")
    if _intersects_dead_window(lo, hi):
        raise NoOverlapError(
            f"{role}: span intersects dead window {DEAD_START.date()}..{DEAD_END.date()}"
        )


def assert_per_file_bounds(files: list[dict[str, Any]], *, role: str) -> dict:
    """Per-file ts-bound assertions for a role's inventory (design|forward)."""
    if role not in ("design", "forward"):
        raise NoOverlapError(f"unknown role {role!r}")
    if not files:
        raise NoOverlapError(f"{role}: empty file list")
    checked = 0
    for f in files:
        tmin = f.get("ts_min_utc")
        tmax = f.get("ts_max_utc")
        if not tmin or not tmax:
            raise NoOverlapError(f"{role}: file missing ts bounds")
        if role == "design":
            assert_design_bounds(tmin, tmax)
        else:
            assert_forward_bounds(tmin, tmax)
        checked += 1
    return {"role": role, "files_checked": checked, "result": "PROVEN_NO_DEAD_WINDOW_OVERLAP"}
