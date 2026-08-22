"""Record sealing for gate-3a authority-bearing types (audit FB-1, FR-3).

Why this module exists
----------------------
Four rounds of this audit have chased one family through four disguises. Each
round closed the route it was shown and left the family open:

* round 1 — a record could simply be **hand-built** by its public constructor;
* round 2 — ``dataclasses.replace`` re-minted one from a real instance's token;
* round 3 — ``copy.copy`` / ``copy.deepcopy`` / ``pickle`` rebuilt a frozen
  ``slots`` dataclass through ``__reduce_ex__`` **without** running
  ``__post_init__``, so each minted a record having spent no token;
* round 4 (**FB-1**) — an ordinary **subclass** with a no-op ``__post_init__``
  mints any token-bearing record for free, and **FR-3** — ``object.__new__``
  bypasses ``__post_init__`` outright, so twenty forged ``MeasurementRecord``\\ s
  carrying ``subject='RAW_M1_SOURCE_BYTES'``, a negative size and a reversed
  span were accepted by the roster.

The merged audit reproduced the subclass route end to end: a two-line subclass
of ``ValidatedCalendar`` and one of ``PairSlotMeasurement`` drove
``assert_full_coverage`` to a **genuine** ``CoverageResult`` bearing
``calendar_digest='NO_CALENDAR_EVER_EXISTED'`` and
``calendar_epoch='NO_EPOCH_WAS_EVER_APPROVED'`` — through public API only,
touching no underscore-prefixed name, never calling ``validate_calendar``, and
presenting no approval marker.

So this module does not add a fifth per-route guard. It closes the family:

1. **Subclassing is refused at class-creation time** (``__init_subclass__``), so
   there is no subclass to override anything on. This is the FB-1 route.
2. **Minting is registered, and consumers verify the registration.** A record
   built by any route that did not go through the module's own minting call is
   simply absent from the registry, so ``object.__new__`` — which no
   ``__new__`` override can intercept — produces an object every consumer
   refuses. This is the FR-3 route, and it is the only defence that works
   against it, because ``object.__setattr__`` can forge any *field*.
3. The copy protocols stay refused (round 3), here rather than repeated in
   three modules.

What this module deliberately does **not** claim
------------------------------------------------
Python has no enforced privacy. A caller that reaches into this module's
private names can mint a registration, and ``object.__setattr__`` still rewrites
a field of a real record after the fact. **Those two routes remain open and are
disclosed rather than claimed away** — which is why every consumer still
re-checks the invariants it depends on (``coverage.assert_full_coverage``
re-scans the expected slot set for dead-window and design-epoch membership;
``proof._limb_cv`` re-derives the roster) instead of trusting the type. Sealing
raises the floor from "public API mints a forgery" to "you must reach into
module privates", and says so.

The registry holds **weak** references, so sealing a record costs no lifetime
extension and a garbage-collected record cannot have its identity reused to
authenticate a later forgery (``id()`` reuse is exactly why an ``id``-keyed set
would have been wrong).
"""

from __future__ import annotations

from typing import Any
from weakref import WeakValueDictionary

__all__ = [
    "SealedRecordError",
    "assert_minted",
    "is_minted",
    "refuse_reconstruction",
    "register_minted",
    "seal",
]


class SealedRecordError(RuntimeError):
    """Raised when an authority-bearing record is subclassed, forged or copied."""


#: Every record minted through the sanctioned path, weakly referenced.
#:
#: Keyed by ``id()`` with the **object itself as the weak value**, and every
#: lookup re-checks identity (``entry is record``). Two hazards are closed at
#: once, and both were live:
#:
#: * ``id()`` reuse — CPython reuses an address after collection, so an
#:   ``id``-keyed *set* would eventually authenticate a forgery that merely
#:   landed on a freed slot. Here the entry dies with its referent, and the
#:   identity re-check refuses a stale hit anyway.
#: * **hashability** — a ``WeakSet`` hashes its members, and a frozen dataclass
#:   derives ``__hash__`` from its fields, so any record carrying a ``Mapping``
#:   or ``list`` field is unhashable and could not be registered at all. That is
#:   not hypothetical: ``ValidatedCalendar``, ``PairSlotMeasurement`` and
#:   ``ProofResult`` all carry one. Keying on ``id()`` removes the requirement,
#:   so sealing imposes no equality semantics on the records it protects.
_MINTED: WeakValueDictionary[int, Any] = WeakValueDictionary()


def seal[T: type](cls: T | None = None, *, error: type[Exception] = SealedRecordError):
    """Class decorator: refuse subclassing, copying, deep-copying and pickling.

    Applied to every authority-bearing record in this package. It must be
    applied **below** ``@dataclass`` (i.e. listed above it in source order), so
    that the dataclass machinery has finished generating ``__init__`` before the
    subclass guard is installed.

    ``error`` lets each module keep **its own documented exception class**, which
    is this package's standing rule (RF-29: "fails closed with the documented
    exception type"). A caller that catches ``CoverageConstructionError`` must
    not start seeing a foreign error because the refusal moved into a shared
    helper. Every such class derives from :class:`SealedRecordError` where the
    module declares it, so a caller may also catch the family.

    The dataclass it seals must be declared ``weakref_slot=True``; otherwise a
    ``slots=True`` dataclass cannot be weakly referenced and
    :func:`register_minted` would fail at the first mint. That is checked here,
    at import, rather than at the first call.
    """

    if cls is None:
        # Called as `@seal(error=...)`; return the decorator itself.
        def _decorate[U: type](inner: U) -> U:
            return seal(inner, error=error)

        return _decorate

    def _refuse_subclass(subcls: type, /, **_kwargs: object) -> None:
        raise error(
            f"{cls.__name__} may not be subclassed (attempted by {subcls.__name__!r}); "
            "a subclass can override __post_init__ and mint an authority-bearing record "
            "that no validation ever produced"
        )

    # `__init_subclass__` is implicitly a classmethod; bind it as one so the
    # subclass being created is what arrives, not this class.
    def _refuse_reconstruction(self: Any, *_args: Any) -> None:
        raise error(
            f"a {type(self).__name__} may not be copied, deep-copied or pickled; those "
            "protocols rebuild it without spending a construction token and without running "
            "its construction checks, so the copy would assert an authority that was never "
            "granted"
        )

    cls.__init_subclass__ = classmethod(_refuse_subclass)  # type: ignore[assignment]
    cls.__copy__ = _refuse_reconstruction  # type: ignore[attr-defined]
    cls.__deepcopy__ = _refuse_reconstruction  # type: ignore[attr-defined]
    cls.__reduce__ = _refuse_reconstruction  # type: ignore[attr-defined]

    slots = getattr(cls, "__slots__", None)
    if slots is not None and "__weakref__" not in slots:
        raise SealedRecordError(  # pragma: no cover - import-time contract check
            f"{cls.__name__} is a slots dataclass without weakref_slot=True, so it cannot "
            "be registered as minted; sealing it would silently fail closed on every mint"
        )
    return cls


def refuse_reconstruction(self: Any, *_args: Any) -> None:
    """Refuse ``copy.copy`` / ``copy.deepcopy`` / ``pickle`` with the default error.

    All three rebuild the instance through ``__reduce_ex__`` without running
    ``__post_init__``, so all three re-mint a record for free. A record only the
    package may mint is not a value that may be duplicated: a second copy
    asserts an authority that was never granted. :func:`seal` installs a variant
    of this that raises the sealed class's own documented error type.
    """
    raise SealedRecordError(
        f"a {type(self).__name__} may not be copied, deep-copied or pickled; those protocols "
        "rebuild the record without running its construction checks, so the copy would assert "
        "an authority that was never granted"
    )


def register_minted(record: Any) -> None:
    """Record that *record* was produced by the sanctioned minting path.

    Called from inside the record's own ``__post_init__``, **after** every
    construction check has passed — so a record that fails validation is never
    registered, and a record built by a route that skips ``__post_init__``
    (notably ``object.__new__``) is never registered either.
    """
    _MINTED[id(record)] = record


def is_minted(record: Any) -> bool:
    """True iff *record* went through the sanctioned minting path.

    The identity re-check is what makes an ``id()`` key sound: a hit whose
    referent is not this very object is a stale or reused address, and is no
    evidence at all.
    """
    return _MINTED.get(id(record)) is record


def assert_minted(record: Any, *, what: str, error: type[Exception] = SealedRecordError) -> None:
    """Fail closed unless *record* was minted through the sanctioned path.

    This is the check that closes **FR-3**. ``object.__new__(Cls)`` bypasses
    ``__new__`` and ``__post_init__`` alike — no override on the class can
    intercept it — so the only way to tell a forged record from a real one is
    that the real one is registered and the forgery is not.
    """
    if not is_minted(record):
        raise error(
            f"{what} was not produced by this package's minting path; a record built by "
            "object.__new__, or otherwise constructed without its validation running, "
            "carries no authority and is refused"
        )
