"""Q7's ``N = 1`` on the ``EXPLORATORY_OOS_SLICE``, made checkable at run time.

Q7's standing default, quoted from the gate document:

    the ``EXPLORATORY_OOS_SLICE`` is consumed at its **first decision-bearing
    observation** — the frozen contract's own definition of consumption (prereg
    §3.2: "consumed at its single authorised evaluation, **or upon any
    decision-bearing observation of it**").  Budget **N = 1**: every R2/R3
    iteration happens on the training portion, and the slice is read once, at
    R4.

    *What is asked:* whether to raise N above 1 … **Raising N is a loosening and
    needs the ruling.**

So ``N = 1`` is not a number this module chose; it is the fail-closed default in
force, and nothing here can raise it.  There is no ``set_budget``, no override
argument and no environment variable: raising ``N`` is a human + ChatGPT
loosening, and when it happens it changes this constant in a diff.

``N`` and ``K`` are different budgets
-------------------------------------

§8.12.13's correction, restated because conflating them is the likely mistake:
``K`` counts **configurations** whose result was observed; ``N`` counts
**observations of the slice**.  A single slice read that scores twenty
configurations spends ``N = 1`` and adds twenty to ``K``.  A configuration
re-scored on the training portion adds to ``K`` and spends no ``N``.

Consumption is terminal
-----------------------

Like `SEEN_IS_TERMINAL_AND_NO_RULING_CAN_RESTORE_UNSEEN_STATUS`, a consumed
slice does not become unconsumed because a run was discarded, a script failed,
or a result was unused.  The ledger here is append-only for the same reason the
seen-data ledger is.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from scripts.m15_track_a import scratch
from scripts.m15_track_a.identity import RunIdentity
from scripts.m15_track_a.scratch import ScratchRootError, assert_writable

OOS_BUDGET_FILENAME: Final[str] = "exploratory_oos_budget.jsonl"

#: One empty file per claimed observation.  See :func:`claim_path`.
OOS_CLAIM_TEMPLATE: Final[str] = "exploratory_oos_claim_{index:04d}.claim"

#: Q7's fail-closed default.  Raising it is a human + ChatGPT loosening and
#: shows up as a change to this line.
OOS_BUDGET_N: Final[int] = 1

OOS_BUDGET_CLASSIFICATION: Final[str] = "BINDING_GOVERNANCE_RECORD"

#: The token a caller sees when the budget is spent.
BUDGET_EXHAUSTED_TOKEN: Final[str] = "EXPLORATORY_OOS_SLICE_BUDGET_EXHAUSTED_N_EQUALS_1"


class OosBudgetError(RuntimeError):
    """Raised when the exploratory OOS slice would be observed beyond its budget."""


@dataclass(frozen=True)
class SliceObservation:
    """One decision-bearing observation of the exploratory OOS slice."""

    run_id: str
    slice_start_utc: str
    slice_end_utc: str
    purpose: str

    def __post_init__(self) -> None:
        for field, value in (
            ("run_id", self.run_id),
            ("slice_start_utc", self.slice_start_utc),
            ("slice_end_utc", self.slice_end_utc),
            ("purpose", self.purpose),
        ):
            if type(value) is not str or not value.strip():  # noqa: E721
                raise OosBudgetError(f"{field} must be a non-empty plain str")
        if self.slice_start_utc > self.slice_end_utc:
            raise OosBudgetError(
                f"slice_start_utc {self.slice_start_utc} is after slice_end_utc "
                f"{self.slice_end_utc}"
            )

    def as_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "slice_start_utc": self.slice_start_utc,
            "slice_end_utc": self.slice_end_utc,
            "purpose": self.purpose,
            "classification": OOS_BUDGET_CLASSIFICATION,
        }


def budget_path() -> Path:
    return scratch.ledger_root() / OOS_BUDGET_FILENAME


def claim_path(index: int) -> Path:
    """The claim file for observation ``index``.

    A separate, empty file per observation, created with ``O_CREAT | O_EXCL``.
    That flag pair is the only cross-process mutual exclusion available without
    a lock service: the OS guarantees exactly one creator, so exactly one caller
    can hold observation *i*. Reading a count and then appending is not
    equivalent — four concurrent processes measured four successful "consumes"
    of a budget of one, and three of the four appends were lost as well, so the
    record under-reported the very over-spend it failed to prevent.
    """
    return scratch.ledger_root() / OOS_CLAIM_TEMPLATE.format(index=index)


def observations_spent() -> int:
    """How many decision-bearing slice observations have been spent.

    The **greater** of two counts: the claim files the OS arbitrated, and the
    ledger lines already written. Counting claims alone was fail-open — a
    deleted claim file reset the budget while the ledger still carried the
    observation, so the evidence of the spend existed and was never consulted.

    **A limit stated rather than hidden.** Deleting *both* the claim file and
    the ledger — or the whole scratch directory — does reset this count, and
    nothing in-process can prevent that: the guards refuse a delete from inside
    a guarded run, and a shell does not go through them.
    `SEEN_IS_TERMINAL_AND_NO_RULING_CAN_RESTORE_UNSEEN_STATUS` is a governance
    fact about the data, not a property this file can enforce, and committing
    the ledger is the control that would make it durable — a
    governance-propagation item, not something this module decides.
    """
    root = scratch.scratch_root()
    if not root.exists():
        return 0
    claims = sum(1 for index in range(1, OOS_BUDGET_N + 1) if claim_path(index).exists())
    path = budget_path()
    recorded = 0
    if path.exists():
        recorded = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return max(claims, recorded)


def remaining() -> int:
    """``N`` minus what has been spent, floored at zero."""
    return max(0, OOS_BUDGET_N - observations_spent())


def assert_budget_available() -> None:
    """Refuse if the slice budget is already spent.

    Called **before** the observation, never after — an observation that has
    happened cannot be un-happened, so a check that runs afterwards records a
    violation instead of preventing one.
    """
    spent = observations_spent()
    if spent >= OOS_BUDGET_N:
        raise OosBudgetError(
            f"{BUDGET_EXHAUSTED_TOKEN}: the exploratory OOS slice has been observed "
            f"{spent} time(s) and Q7's budget is N = {OOS_BUDGET_N}. The slice is consumed "
            "at its first decision-bearing observation, and a consumed slice does not "
            "become unconsumed because a run was discarded. Raising N is a human + ChatGPT "
            "loosening, not a runtime option."
        )


def consume(observation: SliceObservation, identity: RunIdentity) -> Path:
    """Record one slice observation, refusing if the budget is spent.

    The check and the record are in one call deliberately: a caller that could
    check and then decide whether to record is a caller that can observe without
    recording.
    """
    if observation.run_id != identity.run_id:
        raise OosBudgetError(
            f"observation run_id {observation.run_id!r} does not match the identity's "
            f"{identity.run_id!r}"
        )
    assert_budget_available()
    path = budget_path()
    try:
        assert_writable(path)
    except ScratchRootError as exc:  # pragma: no cover - the path is a module constant
        raise OosBudgetError(f"budget path refused by the scratch authority: {exc}") from exc
    path.parent.mkdir(parents=True, exist_ok=True)

    # Claim the slot atomically before recording it.  ``assert_budget_available``
    # above gives the caller a readable error in the ordinary case; this is what
    # makes the budget hold when two runs race for the last observation.
    claimed = None
    for index in range(1, OOS_BUDGET_N + 1):
        candidate = claim_path(index)
        assert_writable(candidate)
        try:
            handle = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            continue
        os.close(handle)
        claimed = index
        break
    if claimed is None:
        raise OosBudgetError(
            f"{BUDGET_EXHAUSTED_TOKEN}: every one of Q7's N = {OOS_BUDGET_N} slot(s) is "
            "already claimed. Another run holds it; the slice is consumed."
        )

    payload = {
        "observation": observation.as_record(),
        "identity": identity.as_record(),
        "claim_index": claimed,
    }
    scratch.append_line(
        path, json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )
    return path


__all__ = [
    "BUDGET_EXHAUSTED_TOKEN",
    "OOS_BUDGET_CLASSIFICATION",
    "OOS_BUDGET_FILENAME",
    "OOS_BUDGET_N",
    "OosBudgetError",
    "SliceObservation",
    "assert_budget_available",
    "budget_path",
    "claim_path",
    "consume",
    "observations_spent",
    "remaining",
]
