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

Exception isolation (G-2 / I-G2-06):
  Every step is wrapped in try/except so that a failure in one step never
  prevents subsequent steps from executing.  Each step returns a bool
  (True = no exception raised, False = exception logged) so callers can
  later observe partial completion.  The strict order from 6.1 is
  preserved — wrapping is purely additive.

Step-3 file binding (G-3 PR-3 / docs/design/g3_notifier_fix_plan.md §3.3.3):
  ``_fire_step3_notifier`` now also returns False when the dispatcher
  reports ``DispatchResult.file_success == False`` (no exception, but
  FileNotifier swallowed an I/O error).  This closes audit finding R-4
  and pins contract C-4 (``_safe_stop_completed`` ⇔ file delivery).
  External / Email leg failures are intentionally NOT propagated into
  the bool — C-5 mandates that file-OK keeps the stop "completed" so
  Supervisor.trigger_safe_stop is not retried needlessly.

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
    ) -> bool:
        """Execute the safe_stop sequence in strict order.

        Args:
            reason: Machine-readable stop reason
                (e.g. 'account_type_mismatch', 'drawdown_daily_exceeded').
            occurred_at: UTC datetime of the triggering event.
                Callers must provide this — no datetime.now() here.
            payload: Additional context merged into the Notifier payload.
            context: CommonKeysContext override (falls back to constructor arg).

        Returns:
            True iff every step (1–4) returned True (no exception, including
            the configured-skip path).  False if any step caught an
            exception.  Callers (e.g., Supervisor.trigger_safe_stop) use
            this to decide whether the safe_stop sequence completed and
            should not be retried, or whether a re-fire is warranted.

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
        s1 = self._fire_step1_journal(reason, occurred_at, effective_payload)

        # ── Step 2: loop stop (in-memory flag) ───────────────────────────
        s2 = self._fire_step2_loop_stop()

        # ── Step 3: notifier (critical, direct sync) ─────────────────────
        s3 = self._fire_step3_notifier(occurred_at, effective_payload)

        # ── Step 4: DB record (supervisor_events) ────────────────────────
        s4 = self._fire_step4_db(occurred_at, effective_payload, ctx)

        return s1 and s2 and s3 and s4

    # ------------------------------------------------------------------
    # Individual step implementations
    #
    # Each step returns True when no exception was raised (including the
    # configured-skip path), False when an exception was caught and
    # logged.  The bool is intentionally never raised to fire(): the
    # contract is that subsequent steps must always run.  Callers (e.g.,
    # Supervisor.trigger_safe_stop) may inspect these returns in a future
    # change to track partial completion.
    # ------------------------------------------------------------------

    def _fire_step1_journal(self, reason: str, occurred_at: datetime, payload: dict) -> bool:
        if self._journal is None:
            _log.error("SafeStopHandler: journal not set — step 1 skipped!")
            return True
        try:
            entry = {
                "event_code": self._EVENT_CODE,
                "reason": reason,
                "occurred_at": occurred_at.isoformat(),
                **{k: v for k, v in payload.items() if k != "reason"},
            }
            self._journal.append(entry)
            _log.info("SafeStopHandler step 1: journal written")
            return True
        except Exception as exc:  # noqa: BLE001
            _log.error("SafeStopHandler step 1: journal append failed: %s", exc)
            return False

    def _fire_step2_loop_stop(self) -> bool:
        if self._stop_callback is None:
            _log.warning("SafeStopHandler: stop_callback not set — step 2 skipped")
            return True
        try:
            self._stop_callback()
            _log.info("SafeStopHandler step 2: loop stopped")
            return True
        except Exception as exc:  # noqa: BLE001
            _log.error("SafeStopHandler step 2: stop_callback failed: %s", exc)
            return False

    def _fire_step3_notifier(self, occurred_at: datetime, payload: dict) -> bool:
        if self._notifier is None:
            _log.warning("SafeStopHandler: notifier not set — step 3 skipped")
            return True
        try:
            event = NotifyEvent(
                event_code=self._EVENT_CODE,
                severity="critical",
                payload=payload,
                occurred_at=occurred_at,
            )
            result = self._notifier.dispatch_direct_sync(event, "critical", payload)
            # PR-3 (memo §3.3.3 / C-4): step-3 truth is bound to file
            # delivery, not to "no exception raised".  External / Email
            # legs are deliberately ignored here so an unreachable Slack
            # / SMTP host does NOT flip ``_safe_stop_completed`` to False
            # (C-5: file durably written = stop is recoverable).
            #
            # ``getattr`` fallback keeps this back-compatible with mocks
            # and any future caller that returns a plain truthy value:
            # production ``NotifierDispatcherImpl`` always returns a
            # ``DispatchResult`` so ``file_success`` is always present.
            file_success = bool(getattr(result, "file_success", True))
            if not file_success:
                _log.error(
                    "SafeStopHandler step 3: file delivery reported failure "
                    "(NotifyResult.success=False) — _safe_stop_completed will remain False"
                )
                return False
            _log.info("SafeStopHandler step 3: notifier dispatched (file delivery OK)")
            return True
        except Exception as exc:  # noqa: BLE001
            _log.error("SafeStopHandler step 3: notifier dispatch failed: %s", exc)
            return False

    def _fire_step4_db(self, occurred_at: datetime, payload: dict, ctx: object | None) -> bool:
        repo = self._supervisor_events_repo
        if repo is None or ctx is None:
            _log.info("SafeStopHandler step 4: DB write skipped (repo or ctx not set)")
            return True
        try:
            repo.insert_event(
                event_type=self._EVENT_CODE,
                event_time_utc=occurred_at,
                context=ctx,
                detail=payload,
            )
            _log.info("SafeStopHandler step 4: supervisor_events written")
            return True
        except Exception as exc:  # noqa: BLE001
            _log.error("SafeStopHandler step 4: supervisor_events insert failed: %s", exc)
            return False
