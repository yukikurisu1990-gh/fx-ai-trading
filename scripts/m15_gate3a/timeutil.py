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

import re
from datetime import UTC, datetime, timedelta
from typing import Any, Final

# Fractional-seconds group of an ISO timestamp, used to catch resolution that
# `datetime.fromisoformat` would silently truncate.
_FRACTION_RE: Final[re.Pattern[str]] = re.compile(r"\.(\d+)")


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


def _reject_subclass_divergence(ts: Any, utc: datetime) -> None:
    """Refuse a ``datetime`` subclass whose true instant is not what it says.

    Two independent ways a subclass can lie to a component rebuild:

    * it carries resolution finer than a microsecond — ``pandas.Timestamp``
      exposes it as ``.nanosecond``;
    * it overrides ``.year`` / ``.month`` / … as properties, so the rebuild
      describes a *different instant* entirely. The internal audit reproduced
      a two-line subclass reporting ``month == 1`` for a March instant, which
      walked a dead-window timestamp straight past the dead-window predicate.

    The ``timestamp()`` cross-check catches the second class outright. Its
    resolution is limited: a float64 second count near 2026 resolves ~4e-7 s,
    so it cannot see a lone nanosecond — that is what the ``.nanosecond`` limb
    is for, and neither limb is claimed to be universal over subclasses that
    hide a sub-microsecond remainder somewhere with no attribute to read.
    """
    if getattr(ts, "nanosecond", 0):
        raise TimestampError(
            f"timestamp {ts!s} carries sub-microsecond resolution "
            f"(nanosecond={ts.nanosecond}); refused rather than truncated"
        )
    if not isinstance(ts, datetime) or type(ts) is datetime:
        return
    try:
        drift = abs(ts.timestamp() - utc.timestamp())
    except (OverflowError, OSError, ValueError) as exc:
        raise TimestampError(f"timestamp() failed for {type(ts).__name__}: {exc}") from exc
    if drift != 0.0:
        raise TimestampError(
            f"{type(ts).__name__} instant disagrees with its own components "
            f"(drift {drift!r}s); refused"
        )


def to_utc(ts: Any) -> datetime:
    """Return an exact plain UTC ``datetime``; fail closed on anything else.

    Accepts a tz-aware ``datetime`` (including subclasses) or an ISO string
    carrying an explicit offset. The result is always a plain ``datetime``, so
    a subclass cannot carry its own comparison semantics past this boundary.

    Sub-microsecond resolution is **refused, never truncated**. The internal
    audit found the truncating version fail-open at the T-7 boundary: a
    ``pandas.Timestamp`` 500 ns *past* ``DESIGN_END`` rebuilt to exactly
    ``DESIGN_END`` and was certified clean, where the code this replaced had
    refused it. Every caller of this function — including the dead-window and
    forward-floor predicates — gets that check, not only the minute path.
    """
    if isinstance(ts, str):
        text = str.__str__(ts).strip()
        if not text:
            raise TimestampError("empty timestamp string")
        # `datetime.fromisoformat` TRUNCATES beyond 6 fractional digits, so an
        # ISO string carrying nanoseconds parsed clean while the equivalent
        # `pandas.Timestamp` was refused — the same instant, two answers, with
        # the string path being the fail-open one. Refuse the excess digits
        # here, where they are still visible.
        fraction = _FRACTION_RE.search(text)
        if fraction and len(fraction.group(1)) > 6:
            raise TimestampError(
                f"ISO timestamp {ts!r} carries {len(fraction.group(1))} fractional digits; "
                "sub-microsecond resolution is refused rather than truncated"
            )
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
    try:
        naive_local = datetime(
            ts.year, ts.month, ts.day, ts.hour, ts.minute, ts.second, ts.microsecond
        )
        utc = (naive_local - offset).replace(tzinfo=UTC)
    except (OverflowError, ValueError, TypeError) as exc:
        # e.g. datetime.min with a positive offset. Fail closed with the
        # documented exception type rather than leaking OverflowError.
        raise TimestampError(f"timestamp out of representable range: {exc}") from exc
    _reject_subclass_divergence(ts, utc)
    return utc


def to_utc_minute(ts: Any) -> datetime:
    """Return an exact minute-aligned plain UTC ``datetime``; fail closed otherwise.

    :func:`to_utc` has already refused sub-microsecond resolution and any
    subclass whose instant disagrees with its components; this adds only the
    minute-alignment requirement on the seconds and microseconds themselves.
    """
    utc = to_utc(ts)
    if utc.second != 0 or utc.microsecond != 0:
        raise TimestampError(f"timestamp {utc.isoformat()} is not minute-aligned")
    return utc
