"""NotifierDispatcherImpl — three-path dispatcher (D3 §2.10.1 / 6.13 / M17).

Critical path (dispatch_direct_sync):
  - Sends to FileNotifier synchronously with fsync (always first).
  - Then sends to each external notifier (SlackNotifier etc.) in order.
  - Then sends to EmailNotifier if configured (last in fan-out — M17).
  - Never uses the notification_outbox table.
  - Returns a ``DispatchResult`` exposing every leg's ``NotifyResult``
    (G-3 PR-3 / docs/design/g3_notifier_fix_plan.md §3.3.3 / C-4) so
    ``SafeStopHandler`` can bind step-3 success to file delivery rather
    than "no exception raised".  Pre-PR-3 the return was ``None`` and
    a silent FileNotifier failure was indistinguishable from a clean
    delivery (audit finding R-4).
  - Must be used for: safe_stop, db.critical_write_failed, stream.gap_sustained,
    reconciler.mismatch_manual_required, ntp.skew_reject.

Non-critical path (dispatch_via_outbox):
  - Writes to notification_outbox for async dispatch by OutboxProcessor (M8).
  - M6 implementation: logs to FileNotifier only (OutboxProcessor is M8 scope).
  - Must NOT be called for critical events.

Fan-out order (critical path): File → externals (Slack …) → Email.
Each leg is independent — failure of one never blocks the next (C-9
non-blocking guarantee preserved by PR-3: collecting per-leg
``NotifyResult`` does not change the no-raise / no-wait semantics).

Design constraint: does NOT call datetime.now() / time.time() (§13.1).
All timestamps come from NotifyEvent.occurred_at (injected by caller).
"""

from __future__ import annotations

import logging

from fx_ai_trading.adapters.notifier.base import NotifierBase
from fx_ai_trading.adapters.notifier.file import FileNotifier
from fx_ai_trading.domain.notifier import DispatchResult, NotifyEvent, NotifyResult

_log = logging.getLogger(__name__)


class NotifierDispatcherImpl:
    """Three-path Notifier dispatcher (File → externals → Email).

    Args:
        file_notifier: FileNotifier instance (required — last-resort path).
        external_notifiers: Additional notifiers (e.g. SlackNotifier) for
            the critical sync path. Optional.
        email_notifier: EmailNotifier for the critical path (M17). Optional;
            called last so SMTP failure never blocks File/Slack paths.

    Two-path contract (6.13):
        dispatch_direct_sync  → FileNotifier + externals + email (never outbox)
        dispatch_via_outbox   → outbox write (M6: FileNotifier fallback only)
    """

    def __init__(
        self,
        file_notifier: FileNotifier,
        external_notifiers: list[NotifierBase] | None = None,
        email_notifier: NotifierBase | None = None,
    ) -> None:
        self._file = file_notifier
        self._externals: list[NotifierBase] = external_notifiers or []
        self._email: NotifierBase | None = email_notifier

    # ------------------------------------------------------------------
    # Critical path — never uses outbox
    # ------------------------------------------------------------------

    def dispatch_direct_sync(
        self,
        event: NotifyEvent,
        severity: str,
        payload: dict,
    ) -> DispatchResult:
        """Send event synchronously to FileNotifier + all external notifiers.

        FileNotifier is always called first (last-resort durability).
        External / Email failures are logged but do NOT raise — fan-out
        continues to the next leg unconditionally (C-9 non-blocking).
        Never writes to notification_outbox (6.13 invariant).

        Returns:
            DispatchResult with each leg's ``NotifyResult`` in fan-out
            order: ``file`` (always), ``externals`` (same order as the
            constructor arg, possibly empty), ``email`` (``None`` when
            ``email_notifier`` is not configured — PR-1 hard guard keeps
            this ``None`` in production).  Callers should bind SafeStop
            step-3 truth to ``DispatchResult.file_success`` (memo
            §3.3.3 / C-4); external/email all-fail with file-OK MUST
            NOT make ``_safe_stop_completed`` flip to False (C-5).
        """
        file_result: NotifyResult = self._file.send(event, severity, payload)
        if not file_result.success:
            # File is the last-resort path — failure here is the only
            # signal that SafeStop step 3 should treat as "not completed"
            # (memo §3.3.3 / C-4).  Log at WARNING for parity with
            # external legs; the SafeStop layer logs the binding decision.
            _log.warning(
                "notifier %s failed for event %s: %s",
                file_result.notifier_name,
                event.event_code,
                file_result.error_message,
            )

        external_results: list[NotifyResult] = []
        for notifier in self._externals:
            result: NotifyResult = notifier.send(event, severity, payload)
            if not result.success:
                _log.warning(
                    "notifier %s failed for event %s: %s",
                    result.notifier_name,
                    event.event_code,
                    result.error_message,
                )
            external_results.append(result)

        email_result: NotifyResult | None = None
        if self._email is not None:
            email_result = self._email.send(event, severity, payload)
            if not email_result.success:
                _log.warning(
                    "notifier %s failed for event %s: %s",
                    email_result.notifier_name,
                    event.event_code,
                    email_result.error_message,
                )

        return DispatchResult(
            file=file_result,
            externals=external_results,
            email=email_result,
        )

    # ------------------------------------------------------------------
    # Non-critical path — via outbox (M8 OutboxProcessor)
    # ------------------------------------------------------------------

    def dispatch_via_outbox(
        self,
        event: NotifyEvent,
        severity: str,
        payload: dict,
    ) -> None:
        """Enqueue event for async dispatch via notification_outbox.

        M6 implementation: writes to FileNotifier only (OutboxProcessor = M8).
        The outbox table write will be added in M8 when OutboxProcessor is built.
        Critical events must NOT use this path (6.13 invariant).
        """
        self._file.send(event, severity, payload)
