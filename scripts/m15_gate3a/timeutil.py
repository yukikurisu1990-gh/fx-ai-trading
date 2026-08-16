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

It is also the single **emission** authority (contract §12.23):
:func:`format_utc_z` is the only renderer permitted to put a timestamp into an
artifact, and ``datetime.isoformat()`` — which yields ``+00:00`` — must not.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from scripts.m15_gate3a.numeric_authority import NumericAuthorityError, pin_float

# EVERY fractional group of an ISO timestamp, on EITHER ISO decimal separator.
#
# RF-1: this was ``\.(\d+)`` scanned with ``.search``, and both halves of that
# were wrong. ISO-8601 admits ``,`` as well as ``.`` as the decimal sign and
# ``datetime.fromisoformat`` accepts it, so ``"…23:59:59,0000005+00:00"`` was
# parsed and silently TRUNCATED while its ``.`` spelling was refused. A fraction
# may also sit in the **offset** (``"…+00:00:00.9999999"``), which ``.search``
# never reached because it stops at the first match. Scanned with ``finditer``.
_FRACTION_RE: Final[re.Pattern[str]] = re.compile(r"[.,](\d+)")

# Digits of an ISO fraction that `datetime` can represent. Anything past this is
# information `fromisoformat` throws away without saying so.
_MICROSECOND_DIGITS: Final[int] = 6


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

    **What the ``timestamp()`` cross-check actually does (RF-2).** It compares
    the subclass's own answer for its instant against the instant rebuilt from
    its components, so it catches a subclass whose components and whose
    ``timestamp()`` **disagree**. It does *not* catch a component lie as such:
    a subclass that lies **consistently** — reporting the same wrong instant
    from both its components and its ``timestamp()`` — agrees with itself and
    passes. The earlier wording asserted that component lies were caught
    outright, which is a guarantee this code does not have. What is guaranteed
    is only the consistency of the two views, plus the ``.nanosecond`` limb.

    Its resolution is limited in the other direction too: a float64 second count
    near 2026 resolves ~4e-7 s, so it cannot see a lone nanosecond — that is
    what the ``.nanosecond`` limb is for, and neither limb is claimed to be
    universal over subclasses that hide a sub-microsecond remainder somewhere
    with no attribute to read.

    **P-5 — both operands are pinned before the subtraction.** The check used to
    be ``abs(ts.timestamp() - utc.timestamp())``, which is arithmetic on an
    object the *caller* supplied: a subclass whose ``timestamp()`` returned a
    ``float`` subclass overriding ``__sub__``/``__abs__`` answered every
    subtraction with ``0.0`` and was ACCEPTED where the identical lie returned as
    a plain ``float`` was REFUSED (measured: an hour of drift, and
    :func:`format_utc_z` then emitted ``2025-06-02T00:00:00Z``). Both values now
    go through the single numeric authority first, so the difference is computed
    between two plain ``float``\\ s. A ``timestamp()`` returning something that
    is not a number at all — which used to leak a bare ``TypeError`` out of
    :func:`to_utc` — fails closed as a :class:`TimestampError` for the same
    reason.
    """
    if getattr(ts, "nanosecond", 0):
        raise TimestampError(
            f"timestamp {ts!s} carries sub-microsecond resolution "
            f"(nanosecond={ts.nanosecond}); refused rather than truncated"
        )
    if not isinstance(ts, datetime) or type(ts) is datetime:
        return
    try:
        declared = ts.timestamp()
        rebuilt = utc.timestamp()
    except (OverflowError, OSError, ValueError) as exc:
        raise TimestampError(f"timestamp() failed for {type(ts).__name__}: {exc}") from exc
    try:
        declared_seconds = pin_float(declared, what="timestamp()")
        rebuilt_seconds = pin_float(rebuilt, what="timestamp()")
    except NumericAuthorityError as exc:
        raise TimestampError(
            f"timestamp() did not return a number for {type(ts).__name__}: {exc}"
        ) from exc
    drift = abs(declared_seconds - rebuilt_seconds)
    if drift != 0.0:
        raise TimestampError(
            f"{type(ts).__name__} instant disagrees with its own components "
            f"(drift {drift!r}s); refused"
        )


def _assert_no_subsecond_information_loss(text: str, original: Any) -> None:
    """Refuse an ISO string whose fractions carry a non-zero sub-microsecond digit.

    ``datetime.fromisoformat`` keeps six fractional digits and discards the rest
    in silence, so the excess has to be judged here, where it is still visible.
    Contract §12.23 fixes the disposition:

    * excess digits that are **all zero** carry no information — the committed
      M1 predecessor inventory writes ``"2025-04-24T22:03:00.000000000Z"``, nine
      digits of nothing — and are accepted;
    * **any** non-zero digit past the microsecond is **refused, never
      truncated**, whichever ISO decimal separator spells it and whether it sits
      in the time or in the offset.

    Both separators and every fraction in the string are examined (RF-1): the
    previous single-``.``, first-match-only check refused ``".0000005"`` while
    accepting ``",0000005"`` and any fraction in the offset.
    """
    for match in _FRACTION_RE.finditer(text):
        digits = match.group(1)
        excess = digits[_MICROSECOND_DIGITS:]
        if any(digit != "0" for digit in excess):
            raise TimestampError(
                f"ISO timestamp {original!r} carries {len(digits)} fractional digits with a "
                f"non-zero sub-microsecond remainder {excess!r}; refused rather than truncated"
            )


def to_utc(ts: Any) -> datetime:
    """Return an exact plain UTC ``datetime``; fail closed on anything else.

    Accepts a tz-aware ``datetime`` (including subclasses) or an ISO string
    carrying an explicit offset. The result is always a plain ``datetime``, so
    a subclass cannot carry its own comparison semantics past this boundary.

    Sub-microsecond **information** is refused, never truncated. The internal
    audit found the truncating version fail-open at the T-7 boundary: a
    ``pandas.Timestamp`` 500 ns *past* ``DESIGN_END`` rebuilt to exactly
    ``DESIGN_END`` and was certified clean, where the code this replaced had
    refused it. Every caller of this function — including the dead-window and
    forward-floor predicates — gets that check, not only the minute path.
    Excess fractional digits that are **all zero** lose nothing and are accepted
    (§12.23); see :func:`_assert_no_subsecond_information_loss` for exactly what
    that admits and what it refuses.
    """
    if isinstance(ts, str):
        # `str(ts)` would re-enter a subclass's `__str__`, letting it show one
        # string to these checks and another to the parser. Pin the character
        # data once, as a plain `str` (RF-20 pins this against reversion).
        text = str.__str__(ts).strip()
        if not text:
            raise TimestampError("empty timestamp string")
        _assert_no_subsecond_information_loss(text, ts)
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


def format_utc_z(ts: Any) -> str:
    """Render an instant as ``YYYY-MM-DDTHH:MM:SSZ`` — the only artifact spelling.

    Contract §12.23: every timestamp reaching an artifact goes through this one
    formatter, and ``datetime.isoformat()`` — which renders the offset as
    ``+00:00`` — may not. The input is put through :func:`to_utc` first, so this
    inherits every refusal above and can never be handed a naive value, a lying
    subclass, or a truncated sub-microsecond remainder.

    A non-zero microsecond is **refused, not truncated**: the output format has
    no fractional field, so rendering one would silently move the instant, which
    is precisely the failure §12.23 exists to prevent. A caller legitimately
    holding a sub-second instant must say so in its own units, not through this.

    The components are formatted explicitly rather than through ``strftime``,
    whose zero-padding of years before 1000 is platform-dependent.
    """
    utc = to_utc(ts)
    if utc.microsecond:
        raise TimestampError(
            f"timestamp {utc!s} carries microsecond={utc.microsecond}; the canonical "
            "artifact format has no fractional field and will not truncate it"
        )
    return (
        f"{utc.year:04d}-{utc.month:02d}-{utc.day:02d}"
        f"T{utc.hour:02d}:{utc.minute:02d}:{utc.second:02d}Z"
    )
