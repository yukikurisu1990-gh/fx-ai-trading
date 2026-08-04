"""Single timestamp authority for gate-3a (BL-2).

The diagnostic review of PR #440 found five independent awareness checks in the
package, all written as ``ts.tzinfo is None``. That is **not** Python's
awareness test: a ``tzinfo`` whose ``utcoffset()`` returns ``None`` leaves the
datetime naive while ``tzinfo is None`` is ``False``. ``astimezone(UTC)`` then
reinterprets the value in the **host's local zone** — aggregation accepted a
bucket nine hours wrong, and the dead-window verdict became host-dependent.

Every timestamp entering the package now goes through this module. It rejects:

* non-``datetime`` / non-``str`` inputs, and offset-less ISO strings;
* ``tzinfo is None``;
* ``utcoffset()`` returning ``None`` (Python's real awareness test);
* ``utcoffset()`` raising, or returning a non-``timedelta``;
* ``utcoffset()`` that is not stable across two calls (non-deterministic zones).

Conversion to UTC is then done from the offset itself rather than by
``astimezone``, so the host clock can never participate. No data is read here.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any


class TimestampError(ValueError):
    """Raised when a timestamp is not provably an exact UTC instant."""


def _require_deterministic_offset(ts: datetime) -> timedelta:
    """Return the UTC offset, or fail closed if it is absent/unstable/ill-typed."""
    if ts.tzinfo is None:
        raise TimestampError(f"naive datetime rejected (no tzinfo): {ts!s}")
    try:
        first = ts.utcoffset()
        second = ts.utcoffset()
    except Exception as exc:  # noqa: BLE001 - any tzinfo failure fails closed
        raise TimestampError(f"utcoffset() raised {type(exc).__name__}: {exc}") from exc
    if first is None:
        # The real awareness test. `tzinfo is not None` is not enough.
        raise TimestampError(f"datetime is naive: utcoffset() returned None for {ts!s}")
    if not isinstance(first, timedelta):
        raise TimestampError(f"utcoffset() must return a timedelta, got {type(first).__name__}")
    if first != second:
        raise TimestampError("utcoffset() is not deterministic across calls")
    return first


def to_utc(ts: Any) -> datetime:
    """Return an exact plain UTC ``datetime``; fail closed on anything else.

    Accepts a tz-aware ``datetime`` (including subclasses) or an ISO string
    carrying an explicit offset. The result is always a plain ``datetime`` —
    a subclass can never carry its own resolution or comparison semantics past
    this boundary.
    """
    if isinstance(ts, str):
        text = ts.strip()
        if not text:
            raise TimestampError("empty timestamp string")
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise TimestampError(f"unparseable ISO timestamp {ts!r}: {exc}") from exc
        if parsed.tzinfo is None:
            raise TimestampError(f"ISO string without explicit offset rejected: {ts!r}")
        ts = parsed
    if not isinstance(ts, datetime):
        raise TimestampError(f"timestamp must be a tz-aware datetime or ISO string, got {ts!r}")

    offset = _require_deterministic_offset(ts)
    # Rebuild from components and subtract the offset explicitly: no astimezone,
    # so the host zone cannot be consulted even for a pathological tzinfo.
    naive_local = datetime(ts.year, ts.month, ts.day, ts.hour, ts.minute, ts.second, ts.microsecond)
    return (naive_local - offset).replace(tzinfo=UTC)


def to_utc_minute(ts: Any) -> datetime:
    """Return an exact minute-aligned plain UTC ``datetime``; fail closed otherwise.

    Rejects any sub-minute remainder, including resolution a ``datetime``
    subclass keeps outside ``second``/``microsecond``: ``pandas.Timestamp``
    exposes ``.nanosecond``, and for a subclass that hides its remainder
    elsewhere the round-trip through ``timestamp()`` still disagrees with the
    rebuilt minute.
    """
    utc = to_utc(ts)
    if utc.second != 0 or utc.microsecond != 0:
        raise TimestampError(f"timestamp {utc.isoformat()} is not minute-aligned")
    if getattr(ts, "nanosecond", 0):
        raise TimestampError(
            f"timestamp {ts!s} carries sub-microsecond resolution "
            f"(nanosecond={ts.nanosecond}); not minute-aligned"
        )
    if isinstance(ts, datetime) and type(ts) is not datetime:
        # A subclass may hold resolution the component rebuild cannot see.
        # Compare instants numerically; a plain datetime round-trips exactly.
        try:
            drift = abs(ts.timestamp() - utc.timestamp())
        except (OverflowError, OSError, ValueError) as exc:
            raise TimestampError(f"timestamp() failed for {type(ts).__name__}: {exc}") from exc
        if drift != 0.0:
            raise TimestampError(
                f"{type(ts).__name__} carries resolution beyond microseconds "
                f"(drift {drift!r}s); not minute-aligned"
            )
    return utc
