"""Verification event log + test-access guard primitives.

Per amendment §A.0 + Stage 1 binding: implements the test-touched-once event
ordering log (verification_log.jsonl) and the test-access guard that locks
all formal test feature / target / realised-PnL / metric access until
``val_selection_frozen`` is emitted for the relevant (scope, cell_id, q).

Stage 1 provides the primitives; Stage 2/3 orchestration uses them.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Allowed event types per scope
# ---------------------------------------------------------------------------

ALLOWED_EVENTS: tuple[str, ...] = (
    "val_split_loaded",
    "cell_fit_complete",
    "val_quantile_scored",
    "val_selection_frozen",
    "test_split_loaded",
    "test_metrics_computed",
)

PRE_FREEZE_EVENTS: frozenset[str] = frozenset(
    {"val_split_loaded", "cell_fit_complete", "val_quantile_scored", "val_selection_frozen"}
)

POST_FREEZE_EVENTS: frozenset[str] = frozenset({"test_split_loaded", "test_metrics_computed"})


class TestIsolationError(RuntimeError):
    """Raised on any test-isolation violation.

    Per amendment §A.0 / Stage 1 binding: raised when test data is accessed
    before val_selection_frozen for the relevant (scope, cell_id, q); when
    val_selection_frozen does not strictly precede test_split_loaded; or
    when a (scope, cell_id, q) is evaluated on test more than once.
    """


class EventLogError(RuntimeError):
    """Raised on event-log schema violations (unknown event type, bad order)."""


# ---------------------------------------------------------------------------
# Event log (append-only; persisted to verification_log.jsonl)
# ---------------------------------------------------------------------------


@dataclass
class EventLog:
    """Append-only event log keyed by scope + (cell_id, q).

    Each scope (foundation, S-1, ..., S-6) has its own ordering invariant:

      val_split_loaded -> cell_fit_complete* -> val_quantile_scored* ->
      val_selection_frozen -> test_split_loaded -> test_metrics_computed*

    Per amendment Stage 1 binding: multi-variant sentinels (S-3 L1/L2/L3,
    S-4 R1/R2/R3/R4, S-5 AR1..AR4, S-6 T1..T4) have ONE val_selection_frozen
    event per (scope, cell_id) and ONE test_metrics_computed event per
    (scope, cell_id, selected_q).
    """

    out_path: Path | None = None
    events: list[dict[str, Any]] = field(default_factory=list)

    def append(
        self,
        event: str,
        scope: str,
        cell_id: str | None = None,
        selected_q: float | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if event not in ALLOWED_EVENTS:
            raise EventLogError(f"unknown event type: {event!r}; allowed: {ALLOWED_EVENTS}")
        record = {
            "ts": time.time(),
            "event": event,
            "scope": scope,
            "cell_id": cell_id,
            "selected_q": selected_q,
            "payload": payload or {},
        }
        self.events.append(record)
        if self.out_path is not None:
            self.out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.out_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, default=str) + "\n")

    # ----- ordering helpers ------------------------------------------------

    def has_event(
        self,
        event: str,
        scope: str,
        cell_id: str | None = None,
    ) -> bool:
        for r in self.events:
            if r["event"] != event:
                continue
            if r["scope"] != scope:
                continue
            if cell_id is not None and r["cell_id"] != cell_id:
                continue
            return True
        return False

    def first_ts(
        self,
        event: str,
        scope: str,
        cell_id: str | None = None,
    ) -> float | None:
        for r in self.events:
            if r["event"] != event:
                continue
            if r["scope"] != scope:
                continue
            if cell_id is not None and r["cell_id"] != cell_id:
                continue
            return r["ts"]
        return None

    def count(
        self,
        event: str,
        scope: str,
        cell_id: str | None = None,
        selected_q: float | None = None,
    ) -> int:
        n = 0
        for r in self.events:
            if r["event"] != event:
                continue
            if r["scope"] != scope:
                continue
            if cell_id is not None and r["cell_id"] != cell_id:
                continue
            if selected_q is not None and r["selected_q"] != selected_q:
                continue
            n += 1
        return n

    # ----- HALT semantics --------------------------------------------------

    def assert_val_freeze_precedes_test(self, scope: str, cell_id: str | None = None) -> None:
        """HALT if val_selection_frozen does NOT strictly precede test_split_loaded."""
        ts_freeze = self.first_ts("val_selection_frozen", scope, cell_id)
        ts_test = self.first_ts("test_split_loaded", scope, cell_id)
        if ts_freeze is None and ts_test is None:
            return  # neither emitted; nothing to check yet
        if ts_freeze is None and ts_test is not None:
            raise TestIsolationError(
                f"scope={scope!r} cell_id={cell_id!r}: test_split_loaded emitted "
                f"without prior val_selection_frozen"
            )
        if ts_freeze is not None and ts_test is not None and ts_freeze >= ts_test:
            raise TestIsolationError(
                f"scope={scope!r} cell_id={cell_id!r}: val_selection_frozen ts="
                f"{ts_freeze!r} does NOT strictly precede test_split_loaded ts="
                f"{ts_test!r}"
            )

    def assert_no_repeat_test_metrics(self, scope: str, cell_id: str, selected_q: float) -> None:
        """HALT if more than one test_metrics_computed for (scope, cell_id, q)."""
        n = self.count("test_metrics_computed", scope, cell_id, selected_q)
        if n > 1:
            raise TestIsolationError(
                f"scope={scope!r} cell_id={cell_id!r} q={selected_q!r}: "
                f"test_metrics_computed emitted {n} times (must be ≤ 1)"
            )


# ---------------------------------------------------------------------------
# Test-access guard primitive
# ---------------------------------------------------------------------------


@dataclass
class TestAccessGuard:
    """Locks test data access until val_selection_frozen.

    Per amendment Stage 1 binding "Runtime test-access guard":

      * all formal test feature / target / realised-PnL / metric access must
        pass through the guard
      * guard remains locked until val_selection_frozen is emitted for the
        relevant (scope, cell_id, q)
      * any access before unlock = TestIsolationError / HALT

    Usage:

        guard = TestAccessGuard(log=event_log)
        # ... train + val ...
        event_log.append("val_selection_frozen", scope="foundation", ...)
        guard.unlock(scope="foundation")
        guard.read_test(scope="foundation", payload={"split": "test"})  # OK
    """

    log: EventLog
    _unlocked_scopes: set[str] = field(default_factory=set)

    def unlock(self, scope: str) -> None:
        """Unlock test access for ``scope``; requires val_selection_frozen emitted."""
        if not self.log.has_event("val_selection_frozen", scope=scope):
            raise TestIsolationError(
                f"cannot unlock test access for scope={scope!r}: "
                f"val_selection_frozen not yet emitted"
            )
        self._unlocked_scopes.add(scope)

    def is_unlocked(self, scope: str) -> bool:
        return scope in self._unlocked_scopes

    def read_test(self, scope: str, payload: dict[str, Any] | None = None) -> None:
        """Single test-access checkpoint. HALT if scope is still locked."""
        if scope not in self._unlocked_scopes:
            raise TestIsolationError(
                f"test access BEFORE freeze for scope={scope!r}: "
                f"val_selection_frozen has not unlocked this scope (payload={payload!r})"
            )
        # Permitted: record nothing additional; calling code records its own
        # test_split_loaded / test_metrics_computed event via EventLog.append.
