"""SafeStopHandler — fires the safe_stop sequence in strict order (6.1 / M7).

Invariant (6.1 / D4 §2.1 Decision 2.1-1):

    1. SafeStopJournal.append()          ← file-based, DB-independent
    2. stop_callback()                    ← sets _trading_allowed=False
    3. dispatcher.dispatch_direct_sync()  ← Notifier (File + Slack, critical)
    4. supervisor_events INSERT           ← DB record (last; failure is safe)

This ordering guarantees that:
  - Evidence of the stop is durably written (fsync) before the loop halts.
  - The loop halts before external notification (notification ≠ prerequisite
    for stopping).
  - DB write is last so that a DB failure cannot prevent steps 1-3.

Verified by: tests/contract/test_safe_stop_fire_sequence.py
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from fx_ai_trading.domain.notifier import NotifyEvent
from fx_ai_trading.supervisor.safe_stop_journal import SafeStopJournal

_log = logging.getLogger(__name__)


class SafeStopHandler:
    """Executes the four-step safe_stop fire sequence.

    Args:
        journal: SafeStopJournal — step 1 (file write, always first).
        notifier: NotifierDispatcherImpl — step 3 (critical notification).
        stop_callback: Zero-arg callable executed as step 2 (loop stop).
            Must be idempotent (may be called from Supervisor._on_loop_stop).
        supervisor_events_repo: Optional SupervisorEventsRepository — step 4.
        common_keys_ctx: Optional CommonKeysContext for the DB write.

    All parameters default to None for contract-test flexibility.  In
    production, journal, notifier, and stop_callback are required.
    """

    _EVENT_CODE = "safe_stop.triggered"

    def __init__(
        self,
        journal: SafeStopJournal | None = None,
        notifier: object | None = None,  # NotifierDispatcherImpl
        stop_callback: Callable[[], None] | None = None,
        supervisor_events_repo: object | None = None,
        common_keys_ctx: object | None = None,
    ) -> None:
        self._journal = journal
        self._notifier = notifier
        self._stop_callback = stop_callback
        self._supervisor_events_repo = supervisor_events_repo
        self._common_keys_ctx = common_keys_ctx

    def fire(
        self,
        reason: str,
        occurred_at: datetime,
        payload: dict | None = None,
        context: object | None = None,
    ) -> None:
        """Execute the safe_stop sequence in strict order.

        Args:
            reason: Machine-readable stop reason
                (e.g. 'account_type_mismatch', 'drawdown_daily_exceeded').
            occurred_at: UTC datetime of the triggering event.
                Callers must provide this — no datetime.now() here.
            payload: Additional context merged into the Notifier payload.
            context: CommonKeysContext override (falls back to constructor arg).

        Sequence (order is mandatory per 6.1):
            1. journal.append()
            2. stop_callback()
            3. notifier.dispatch_direct_sync()
            4. supervisor_events INSERT
        """
        _log.critical("SafeStopHandler.fire(): reason=%s occurred_at=%s", reason, occurred_at)

        effective_payload = {"reason": reason, **(payload or {})}
        ctx = context or self._common_keys_ctx

        # ── Step 1: journal (file, fsync, DB-independent) ────────────────
        self._fire_step1_journal(reason, occurred_at, effective_payload)

        # ── Step 2: loop stop (in-memory flag) ───────────────────────────
        self._fire_step2_loop_stop()

        # ── Step 3: notifier (critical, direct sync) ─────────────────────
        self._fire_step3_notifier(occurred_at, effective_payload)

        # ── Step 4: DB record (supervisor_events) ────────────────────────
        self._fire_step4_db(occurred_at, effective_payload, ctx)

    # ------------------------------------------------------------------
    # Individual step implementations
    # ------------------------------------------------------------------

    def _fire_step1_journal(
        self, reason: str, occurred_at: datetime, payload: dict
    ) -> None:
        if self._journal is None:
            _log.error("SafeStopHandler: journal not set — step 1 skipped!")
            return
        entry = {
            "event_code": self._EVENT_CODE,
            "reason": reason,
            "occurred_at": occurred_at.isoformat(),
            **{k: v for k, v in payload.items() if k != "reason"},
        }
        self._journal.append(entry)
        _log.info("SafeStopHandler step 1: journal written")

    def _fire_step2_loop_stop(self) -> None:
        if self._stop_callback is None:
            _log.warning("SafeStopHandler: stop_callback not set — step 2 skipped")
            return
        self._stop_callback()
        _log.info("SafeStopHandler step 2: loop stopped")

    def _fire_step3_notifier(self, occurred_at: datetime, payload: dict) -> None:
        if self._notifier is None:
            _log.warning("SafeStopHandler: notifier not set — step 3 skipped")
            return
        event = NotifyEvent(
            event_code=self._EVENT_CODE,
            severity="critical",
            payload=payload,
            occurred_at=occurred_at,
        )
        self._notifier.dispatch_direct_sync(event, "critical", payload)
        _log.info("SafeStopHandler step 3: notifier dispatched")

    def _fire_step4_db(
        self, occurred_at: datetime, payload: dict, ctx: object | None
    ) -> None:
        repo = self._supervisor_events_repo
        if repo is None or ctx is None:
            _log.info("SafeStopHandler step 4: DB write skipped (repo or ctx not set)")
            return
        try:
            repo.insert_event(
                event_type=self._EVENT_CODE,
                event_time_utc=occurred_at,
                context=ctx,
                detail=payload,
            )
            _log.info("SafeStopHandler step 4: supervisor_events written")
        except Exception as exc:  # noqa: BLE001
            _log.error("SafeStopHandler step 4: supervisor_events insert failed: %s", exc)
