"""Single numeric authority for gate-3a — pin a caller's number before comparing it.

Why this module exists (audit N-1)
----------------------------------
This package had already hardened every other two-faced-object family:
``str`` through :func:`scripts.m15_gate3a.artifacts._pin` and
:func:`scripts.m15_gate3a.path_authority.resolve_candidate` (RF-6 / RF-20),
``Path`` through the path authority (RF-5), ``datetime`` through
:func:`scripts.m15_gate3a.timeutil._reject_subclass_divergence` (BL-2 / F-1),
and ``Sequence`` through the re-scan/identity guards (RF-4, BL-1). **Numbers were
the one family left unpinned**, and they are the family every quality
disposition in the package is decided with.

``isinstance(value, (int, float))`` admits a *subclass*, and a subclass may
override ``__lt__`` / ``__gt__`` / ``__le__`` / ``__ge__`` / ``__eq__`` /
``__float__`` / ``__index__``. Every ``<`` and ``>`` written against such an
object asks the object whether it should be refused. The internal audit and the
lead both reproduced the consequence:

* ``aggregation`` accepted a bucket whose ask was below its bid on every row —
  ``n_source_bars=15, eligible=True, complete_bucket=True`` — where the identical
  plain-``float`` crossings refused 12 times out of 12 (D-1 defeated);
* ``cost_schema`` validated a **negative** median spread, reporting
  ``min_observed_spread_pips = -50000.0``;
* ``effective_n`` accepted ``raw_event_count = -100``.

The remedy is the same one the other four families got: read the object's
**character data once**, as the plain built-in type, and make every later
decision against that plain value. ``float.__float__`` and ``int.__index__`` are
the unbound base-class slots, so they return the C-level double/integer the
object actually holds and cannot be intercepted by an override — exactly as
``str.__str__(text)`` returns the real character data of a ``str`` subclass.

Note that the ordinary constructors are **not** sufficient: ``float(value)``
calls ``type(value).__float__`` and therefore returns whatever a lying subclass
says (measured: ``float(F(-5.0)) == 0.0`` for a subclass overriding
``__float__``, while ``float.__float__(F(-5.0)) == -5.0``). The same holds for
``int(value)`` versus ``int.__index__(value)``.

**Scope.** This module reads nothing, decides no threshold and mints no
constant. It converts a type; the numeric *policy* stays with the caller, which
also owns the exception type its callers are documented to catch — so every
function here raises :class:`NumericAuthorityError` and each caller wraps it in
its own error class.

**Non-blocking item, closed with the P-1..P-7 round.** ``isinstance`` consults
``__class__``, which an arbitrary object may claim, so
``isinstance(value, int)`` could be satisfied by
something the unbound ``int.__index__`` slot then refuses with a bare
``TypeError``. That was still fail-closed, but it escaped the wrapping every
caller is documented to do, arriving as a ``TypeError`` where the caller's own
error class was promised. The slot calls are guarded so that spoofing lands on
:class:`NumericAuthorityError` like every other refusal here.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "NumericAuthorityError",
    "pin_float",
    "pin_int",
    "pin_number",
]


class NumericAuthorityError(ValueError):
    """Raised when a value cannot be pinned to plain numeric character data."""


def _index(value: Any, *, what: str) -> int:
    """``int.__index__`` with ``__class__``-spoofing folded into this module's error."""
    try:
        return int.__index__(value)
    except TypeError as exc:
        raise NumericAuthorityError(
            f"{what} claims to be an int but is a {type(value).__name__} that the int slot "
            f"refuses: {exc}"
        ) from exc


def pin_number(value: Any, *, what: str) -> int | float:
    """Return *value*'s plain ``int``/``float`` character data, or fail closed.

    ``bool`` is refused: it is an ``int`` subclass, and every caller in this
    package already treats a boolean where a count or a price belongs as a
    contract violation rather than as ``0``/``1``.
    """
    if isinstance(value, bool):
        raise NumericAuthorityError(f"{what} must be a number, not a bool")
    if isinstance(value, int):
        return _index(value, what=what)
    if isinstance(value, float):
        try:
            return float.__float__(value)
        except TypeError as exc:
            raise NumericAuthorityError(
                f"{what} claims to be a float but is a {type(value).__name__} that the float "
                f"slot refuses: {exc}"
            ) from exc
    raise NumericAuthorityError(f"{what} must be a number, got {type(value).__name__}")


def pin_int(value: Any, *, what: str) -> int:
    """Return *value*'s plain ``int`` character data, or fail closed.

    A ``float`` — including an integral one — is refused rather than rounded: a
    count is an ``int`` in every schema this package validates, and silently
    accepting ``15.0`` where ``15`` is required would widen a frozen schema.
    """
    if isinstance(value, bool):
        raise NumericAuthorityError(f"{what} must be an int, not a bool")
    if not isinstance(value, int):
        raise NumericAuthorityError(f"{what} must be an int, got {type(value).__name__}")
    return _index(value, what=what)


def pin_float(value: Any, *, what: str) -> float:
    """Return *value* as a plain ``float``, pinned through the base-class slots."""
    return float(pin_number(value, what=what))
