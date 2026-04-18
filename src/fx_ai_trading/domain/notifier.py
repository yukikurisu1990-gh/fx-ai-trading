"""Notifier domain interfaces and DTOs (D3 §2.10.1 / 6.13).

Two-path dispatch:
  - dispatch_direct_sync: critical events (safe_stop etc.) — fsync to FileNotifier
    + synchronous send to all available notifiers, never via outbox.
  - dispatch_via_outbox: non-critical events — async via notification_outbox table.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NotifyEvent:
    """A notification event to be dispatched."""

    event_code: str
    severity: str  # critical | warning | info
    payload: dict
    occurred_at: datetime


@dataclass(frozen=True)
class NotifyResult:
    """Result of Notifier.send()."""

    success: bool
    notifier_name: str
    sent_at: datetime
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Interfaces (Protocol)
# ---------------------------------------------------------------------------


class Notifier(Protocol):
    """Single-channel notification sender (D3 §2.10.1 / 6.13).

    Implementations: FileNotifier (always required), SlackNotifier (MVP),
    EmailNotifier (Phase 7+).

    Invariant: FileNotifier.send() must always succeed (last-resort path,
    DB-independent). Its fsync guarantees durability.
    """

    def send(self, event: NotifyEvent, severity: str, payload: dict) -> NotifyResult:
        """Send *event* through this notifier channel."""
        ...


class NotifierDispatcher(Protocol):
    """Two-path dispatcher for Notifier channels (D3 §2.10.1 / 6.13).

    Critical path (dispatch_direct_sync): safe_stop / db.critical_write_failed /
    stream.gap_sustained / reconciler.mismatch_manual_required / ntp.skew_reject.
    Must NOT use notification_outbox.

    Non-critical path (dispatch_via_outbox): async via notification_outbox table.
    """

    def dispatch_direct_sync(
        self,
        event: NotifyEvent,
        severity: str,
        payload: dict,
    ) -> None:
        """Send *event* synchronously to FileNotifier (fsync) + all available
        external notifiers. Must not use outbox. Used for critical events only.
        """
        ...

    def dispatch_via_outbox(
        self,
        event: NotifyEvent,
        severity: str,
        payload: dict,
    ) -> None:
        """Write *event* to notification_outbox for async dispatch.
        Must not be called for critical events.
        """
        ...
