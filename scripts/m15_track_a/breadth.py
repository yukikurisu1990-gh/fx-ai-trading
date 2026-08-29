"""The exploration-breadth (``K``) record.

§8.11.10(2): the breadth "must be recorded **as it accrues**, because it cannot
be reconstructed afterwards".  §8.12.13 A-5 made it execution-gate item 9 after
finding it had no instrument.  This is the instrument, at the lightest weight
that still works.

``K``'s unit is R-7's, not a run counter
----------------------------------------

R-7: "``K`` is the number of evaluations **whose result was observed**, counted
**per configuration** — pair set × feature set × model × hyperparameters ×
threshold × split — **not per script invocation**.  Narrowing a sweep after
reading its output **adds** to ``K``; it never resets it."

§8.12.13 C-5 widened it once more: ``K`` also counts **the evaluable
configuration set** a frozen candidate can reach at confirmation, so a
multi-operating-point candidate cannot carry unbounded search into a "one
candidate, one run" record.  That limb is a Track B obligation and is recorded
here as a field the Track B packet reads, not as something this module computes.

Deliberately light
------------------

This is not an evidence artifact.  It records the configuration axes, a label,
and whether the result was observed — and nothing about what the result *was*,
because a Track A performance figure is `NON_DECISION_BEARING_EXPLORATORY_ONLY`
and putting one in a governance record is how it later gets cited.

Like the seen-data ledger it is a ``BINDING_GOVERNANCE_RECORD``: it constrains a
formal claim, so the non-decision-bearing label does not reach it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

from scripts.m15_track_a import scratch
from scripts.m15_track_a.identity import RunIdentity
from scripts.m15_track_a.scratch import ScratchRootError, assert_writable

BREADTH_FILENAME: Final[str] = "exploration_breadth.jsonl"

BREADTH_CLASSIFICATION: Final[str] = "BINDING_GOVERNANCE_RECORD"

#: R-7's configuration axes, in R-7's own order.  A configuration is the tuple
#: of these; two runs differing in any one of them are two configurations.
CONFIGURATION_AXES: Final[tuple[str, ...]] = (
    "pair_set",
    "feature_set",
    "model",
    "hyperparameters",
    "threshold",
    "split",
)


def _pin_bool(value: Any) -> bool:
    """Exactly a ``bool``.

    The writer pins ``result_observed`` with ``type(...) is not bool`` and the
    reader used ``bool(...)``, so a ledger line carrying ``0`` reconstructed as
    ``False`` with no error — silently undercounting ``K``. A reader that is
    laxer than its writer is the hole, whatever the writer checks.
    """
    if type(value) is not bool:  # noqa: E721
        raise BreadthRecordError(f"result_observed must be a bool in the record, got {value!r}")
    return value


class BreadthRecordError(RuntimeError):
    """Raised when a breadth entry is malformed."""


@dataclass(frozen=True)
class ConfigurationEntry:
    """One configuration Track A evaluated, and whether its result was observed."""

    run_id: str
    axes: Mapping[str, str]
    result_observed: bool
    note: str = ""

    def __post_init__(self) -> None:
        if type(self.run_id) is not str or not self.run_id.strip():  # noqa: E721
            raise BreadthRecordError("run_id must be a non-empty plain str")
        if not isinstance(self.axes, Mapping):
            raise BreadthRecordError("axes must be a mapping")
        missing = [axis for axis in CONFIGURATION_AXES if axis not in self.axes]
        if missing:
            raise BreadthRecordError(
                f"axes is missing {missing}; a configuration is the tuple of R-7's six axes, "
                "and an entry that omits one cannot be compared with another"
            )
        extra = sorted(set(self.axes) - set(CONFIGURATION_AXES))
        if extra:
            raise BreadthRecordError(
                f"axes carries unknown key(s) {extra}; R-7's unit is closed — a new axis is "
                "a contract question, not a field a run adds"
            )
        for axis, value in self.axes.items():
            if type(value) is not str or not value.strip():  # noqa: E721
                raise BreadthRecordError(f"axis {axis!r} must be a non-empty plain str")
        if type(self.result_observed) is not bool:  # noqa: E721
            raise BreadthRecordError("result_observed must be a bool")
        # ``frozen=True`` freezes the *binding*, not the dict behind it. Without
        # this, ``entry.axes["model"] = ...`` changes ``configuration_key`` after
        # validation and can inject an axis the closed-set check already refused.
        object.__setattr__(self, "axes", MappingProxyType(dict(self.axes)))
        if type(self.note) is not str:  # noqa: E721
            raise BreadthRecordError("note must be a str")

    def as_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "axes": dict(sorted(self.axes.items())),
            "result_observed": self.result_observed,
            "note": self.note,
            "classification": BREADTH_CLASSIFICATION,
        }

    @property
    def configuration_key(self) -> tuple[str, ...]:
        """The configuration this entry names, as R-7's ordered tuple."""
        return tuple(self.axes[axis] for axis in CONFIGURATION_AXES)


def breadth_path() -> Path:
    return scratch.scratch_root() / BREADTH_FILENAME


def record(entry: ConfigurationEntry, identity: RunIdentity) -> Path:
    """Append one configuration entry.  Append-only, like the seen ledger."""
    if entry.run_id != identity.run_id:
        raise BreadthRecordError(
            f"entry run_id {entry.run_id!r} does not match the identity's {identity.run_id!r}"
        )
    path = breadth_path()
    try:
        assert_writable(path)
    except ScratchRootError as exc:  # pragma: no cover - the path is a module constant
        raise BreadthRecordError(f"breadth path refused by the scratch authority: {exc}") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"entry": entry.as_record(), "identity": identity.as_record()}
    line = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")
    return path


def read_entries() -> tuple[ConfigurationEntry, ...]:
    path = breadth_path()
    if not path.exists():
        return ()
    out: list[ConfigurationEntry] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        payload = json.loads(raw)["entry"]
        out.append(
            ConfigurationEntry(
                run_id=payload["run_id"],
                axes=dict(payload["axes"]),
                result_observed=_pin_bool(payload["result_observed"]),
                note=payload.get("note", ""),
            )
        )
    return tuple(out)


def current_k() -> int:
    """``K`` so far: distinct configurations **whose result was observed**.

    Distinct, because R-7 counts per configuration and not per invocation — the
    same configuration evaluated twice is one evaluation of it.  Observed only,
    because R-7 says so; an entry recorded with ``result_observed=False`` is
    kept for the audit trail and does not add to ``K``.
    """
    observed = {entry.configuration_key for entry in read_entries() if entry.result_observed}
    return len(observed)


__all__ = [
    "BREADTH_CLASSIFICATION",
    "BREADTH_FILENAME",
    "CONFIGURATION_AXES",
    "BreadthRecordError",
    "ConfigurationEntry",
    "breadth_path",
    "current_k",
    "read_entries",
    "record",
]
