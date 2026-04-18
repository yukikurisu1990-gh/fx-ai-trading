"""NotifierDispatcherImpl — two-path dispatcher (D3 §2.10.1 / 6.13).

Critical path (dispatch_direct_sync):
  - Sends to FileNotifier synchronously with fsync (always first).
  - Then sends to each external notifier (SlackNotifier etc.) in order.
  - Never uses the notification_outbox table.
  - Must be used for: safe_stop, db.critical_write_failed, stream.gap_sustained,
    reconciler.mismatch_manual_required, ntp.skew_reject.

Non-critical path (dispatch_via_outbox):
  - Writes to notification_outbox for async dispatch by OutboxProcessor (M8).
  - M6 implementation: logs to FileNotifier only (OutboxProcessor is M8 scope).
  - Must NOT be called for critical events.

Design constraint: does NOT call datetime.now() / time.time() (§13.1).
All timestamps come from NotifyEvent.occurred_at (injected by caller).
"""

from __future__ import annotations

import logging

from fx_ai_trading.adapters.notifier.base import NotifierBase
from fx_ai_trading.adapters.notifier.file import FileNotifier
from fx_ai_trading.domain.notifier import NotifyEvent, NotifyResult

_log = logging.getLogger(__name__)


class NotifierDispatcherImpl:
    """Two-path Notifier dispatcher.

    Args:
        file_notifier: FileNotifier instance (required — last-resort path).
        external_notifiers: Additional notifiers (e.g. SlackNotifier) for
            the critical sync path. Optional.

    Two-path contract (6.13):
        dispatch_direct_sync  → FileNotifier + externals (never outbox)
        dispatch_via_outbox   → outbox write (M6: FileNotifier fallback only)
    """

    def __init__(
        self,
        file_notifier: FileNotifier,
        external_notifiers: list[NotifierBase] | None = None,
    ) -> None:
        self._file = file_notifier
        self._externals: list[NotifierBase] = external_notifiers or []

    # ------------------------------------------------------------------
    # Critical path — never uses outbox
    # ------------------------------------------------------------------

    def dispatch_direct_sync(
        self,
        event: NotifyEvent,
        severity: str,
        payload: dict,
    ) -> None:
        """Send event synchronously to FileNotifier + all external notifiers.

        FileNotifier is always called first (last-resort durability).
        External notifier failures are logged but do NOT raise.
        Never writes to notification_outbox (6.13 invariant).
        """
        self._file.send(event, severity, payload)
        for notifier in self._externals:
            result: NotifyResult = notifier.send(event, severity, payload)
            if not result.success:
                _log.warning(
                    "notifier %s failed for event %s: %s",
                    result.notifier_name,
                    event.event_code,
                    result.error_message,
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
