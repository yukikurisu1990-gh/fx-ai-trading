"""Real M1 rows are aggregated only through the authorised Track A route.

`scripts/m15_track_a/derivation.py` selected arm (i) — Track A derives M15 by
calling the committed :func:`~scripts.m15_gate3a.aggregation.aggregate_m15` —
and named, in the same docstring, what was holding the bypass shut:

    "no code change and no refusal trips, because it is a pure function over row
    dicts and ``assert_synthetic_only`` has no caller outside its own test.
    **What has contained it is the absence of a reader** and its BLOCKED source
    audit"

**PR #453 added the reader.** `read_historical` returns rows in exactly the
shape `aggregate_m15` consumes, so under a valid **read** grant a caller could
obtain real M1 rows and aggregate them without ever entering `derive_m15` — no
authorisation check, no fingerprint change, and nothing in any diff. A review
role found it by reading that sentence against the new head, and it is the
reason the R1 execution command was refused rather than worked around.

Where this lives, and why
-------------------------

The check has to sit **inside the aggregator**. A guard the caller may skip is
caller discipline, and caller discipline is precisely what failed.

It cannot live in :mod:`scripts.m15_gate3a.guards`, which would have been the
obvious home: that module imports ``scripts.ml_step4.evidence``, a **writer**,
and `aggregation` is reader-free and stays that way. It cannot live in
`m15_track_a` either — that is the wrong dependency direction and WP5 pins Track
A's import surface into this package. So it is its own module, and it imports
nothing but the standard library.

Two mechanisms, because each covers what the other cannot
---------------------------------------------------------

1. a **process latch**, set by the read route when it hands out rows drawn from
   the committed data root. It is not attached to the rows, so copying them into
   fresh dicts, re-keying them or passing them through a dataframe does not
   shake it off;
2. a **per-row marker**, which survives into a subprocess, a pickle or a file
   where the latch does not, and which names the offending row.

Synthetic and fixture use is untouched: rows from a temporary tree carry no
marker and set no latch, so every existing aggregation test behaves exactly as
before.

What this does **not** do
-------------------------

It does not stop code in this process from calling
:func:`authorised_derivation_window` itself, or from reaching into this module
and clearing the latch. Nothing in-process can — that limit is
`containment.AUDIT_BOUNDS`'s, unchanged. What it does is make the bypass
**impossible by accident** and **visible in a diff** when deliberate, which is
the standard the rest of this apparatus is held to.
"""

from __future__ import annotations

import contextvars
import threading
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Final

#: Key the read route stamps on rows drawn from the committed data root.
REAL_PROVENANCE_KEY: Final[str] = "_track_a_provenance"

#: Its only permitted value.
REAL_PROVENANCE: Final[str] = "TRACK_A_REAL_HISTORICAL_M1"

#: The refusal, greppable.
DERIVATION_BYPASS_TOKEN: Final[str] = (
    "M15_DERIVATION_FROM_REAL_ROWS_OUTSIDE_THE_AUTHORISED_ROUTE_REFUSED"
)

_real_rows_handed_out: bool = False


@dataclass(frozen=True)
class _WindowOwner:
    """Who opened the derivation window, and how deep they are inside it."""

    thread_id: int
    task: int | None
    depth: int


#: The authorised derivation window, pinned to the **thread and task that opened
#: it**, mirroring ``isolation._window``.
#:
#: The first drafting was a plain module global and its docstring claimed it was
#: "on the model of ``isolation.gated_read_window``" — which is precisely the
#: model that module records having rejected three times: "a process-wide flag
#: opened ``data/`` to every other thread; a ``threading.local`` opened it to
#: every other coroutine on the same thread; and a bare ``ContextVar`` is
#: *copied into* a child task". A review role measured all of it here: while the
#: authorised route held the window, an arbitrary aggregation of real rows
#: succeeded from another thread **and** from a child asyncio task. Per-pair
#: parallelism is an obvious optimisation, so that is a bypass reachable by
#: accident, not only by intent.
_window: contextvars.ContextVar[_WindowOwner | None] = contextvars.ContextVar(
    "track_a_derivation_window", default=None
)


def _current_task_id() -> int | None:
    try:
        import asyncio

        task = asyncio.current_task()
    except (ImportError, RuntimeError):
        return None
    return None if task is None else id(task)


class DerivationContainmentError(RuntimeError):
    """Real M1 rows were aggregated outside the authorised derivation route."""


def mark_real_rows_handed_out() -> None:
    """Latch that this process has been given real historical rows.

    One-way on purpose: a reset **is** the bypass. A test that needs a clean
    latch runs in a subprocess, and the ones that need it do.
    """
    global _real_rows_handed_out
    _real_rows_handed_out = True


def real_rows_handed_out() -> bool:
    """Whether this process has been handed rows from the committed data root."""
    return _real_rows_handed_out


def stamp_real_provenance(row: dict[str, Any]) -> dict[str, Any]:
    """Mark one row as real historical data, in place, and return it.

    ``aggregate_m15`` reads only ``ts`` and the eight side keys through
    ``_snapshot_row``, so the extra key changes no aggregation result. That is
    checked by a test rather than assumed.
    """
    row[REAL_PROVENANCE_KEY] = REAL_PROVENANCE
    return row


def is_real_row(row: Any) -> bool:
    """Whether one row carries the real-provenance marker.

    A mapping that raises on lookup is treated as **real**. The alternative —
    treating an unreadable row as synthetic — makes "raise from ``get``" the
    bypass, and this package has had a lying-mapping defeat before.
    """
    if not isinstance(row, Mapping):
        return False
    try:
        return row.get(REAL_PROVENANCE_KEY) == REAL_PROVENANCE
    except Exception:  # noqa: BLE001
        return True


@contextmanager
def authorised_derivation_window() -> Iterator[None]:
    """Open while the authorised derivation route is calling the aggregator.

    Re-entrant, exception-safe, and **scoped to the opening thread and task**.
    A sibling thread or a child task sees the window as closed, because the
    owner is compared rather than merely present — a ``ContextVar`` alone is
    copied into a child ``Task`` at creation and would be inherited.

    **Opening it is not an authorisation**: the route opens it only after its
    own gates have passed, so what it marks is "the gates ran", not "the caller
    would like them to have".
    """
    owner = _window.get()
    here = (threading.get_ident(), _current_task_id())
    depth = owner.depth + 1 if owner is not None and (owner.thread_id, owner.task) == here else 1
    token = _window.set(_WindowOwner(thread_id=here[0], task=here[1], depth=depth))
    try:
        yield
    finally:
        _window.reset(token)


def derivation_window_open() -> bool:
    """Whether an authorised derivation is in progress **on this thread and task**."""
    owner = _window.get()
    if owner is None:
        return False
    return (owner.thread_id, owner.task) == (threading.get_ident(), _current_task_id())


def assert_derivation_authorised(rows: Any) -> None:
    """Refuse an aggregation of real rows outside the authorised route.

    Called by :func:`~scripts.m15_gate3a.aggregation.aggregate_m15` before it
    touches its input. The window is tested first, so the authorised route pays
    nothing for the row scan.
    """
    if derivation_window_open():
        return
    if _real_rows_handed_out:
        raise DerivationContainmentError(
            f"{DERIVATION_BYPASS_TOKEN}: this process has been handed real historical M1 "
            "rows, so aggregate_m15 is reachable only through "
            "scripts.m15_track_a.derivation.derive_m15, which requires a "
            "track_a_m15_research_derivation grant. A read grant does not authorise a "
            "derivation (playbook §2.5)."
        )
    if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes, bytearray)):
        for index, row in enumerate(rows):
            if is_real_row(row):
                raise DerivationContainmentError(
                    f"{DERIVATION_BYPASS_TOKEN}: row {index} carries "
                    f"{REAL_PROVENANCE_KEY}={REAL_PROVENANCE!r}. Real historical rows are "
                    "aggregated only through scripts.m15_track_a.derivation.derive_m15."
                )


__all__ = [
    "DERIVATION_BYPASS_TOKEN",
    "REAL_PROVENANCE",
    "REAL_PROVENANCE_KEY",
    "DerivationContainmentError",
    "assert_derivation_authorised",
    "authorised_derivation_window",
    "derivation_window_open",
    "is_real_row",
    "mark_real_rows_handed_out",
    "real_rows_handed_out",
    "stamp_real_provenance",
]
