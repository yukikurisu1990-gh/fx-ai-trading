"""Notifier domain interfaces and DTOs (D3 §2.10.1 / 6.13).

Two-path dispatch:
  - dispatch_direct_sync: critical events (safe_stop etc.) — fsync to FileNotifier
    + synchronous send to all available notifiers, never via outbox.
  - dispatch_via_outbox: non-critical events — async via notification_outbox table.

DispatchResult (G-3 PR-3 / docs/design/g3_notifier_fix_plan.md §3.3.3):
  ``dispatch_direct_sync`` returns a ``DispatchResult`` exposing every
  channel's ``NotifyResult`` so callers (notably ``SafeStopHandler``)
  can bind their truth to ``file_success`` instead of "no exception
  raised".  This closes audit finding R-4: pre-PR-3 step-3 success
  was indistinguishable between "everything delivered" and "file
  silently failed but no exception leaked".
"""

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class DispatchResult:
    """Per-channel results of ``NotifierDispatcher.dispatch_direct_sync``.

    Introduced in G-3 PR-3 (memo §3.3.3) so SafeStop step 3 can bind its
    truth to file delivery (C-4) rather than "no exception raised".

    Fields mirror the fan-out order of ``dispatch_direct_sync``:
      - ``file``      — always present (FileNotifier is the last-resort path).
      - ``externals`` — same order as the dispatcher's ``external_notifiers``
                        constructor arg; empty list when none configured.
      - ``email``     — ``None`` when ``email_notifier`` is not configured
                        (the PR-1 hard guard keeps this ``None`` in production
                        until the notifier_factory is taught to wire Email).

    Convenience properties:
      - ``file_success``           — bound by C-4 / SafeStop step 3.
      - ``all_success``            — every configured leg succeeded.
      - ``any_external_success``   — at least one external leg succeeded
                                     (useful for operator-visible alerting).
    """

    file: NotifyResult
    externals: list[NotifyResult] = field(default_factory=list)
    email: NotifyResult | None = None

    @property
    def file_success(self) -> bool:
        return self.file.success

    @property
    def all_success(self) -> bool:
        if not self.file.success:
            return False
        if not all(r.success for r in self.externals):
            return False
        return not (self.email is not None and not self.email.success)

    @property
    def any_external_success(self) -> bool:
        return any(r.success for r in self.externals)


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
    ) -> DispatchResult:
        """Send *event* synchronously to FileNotifier (fsync) + all available
        external notifiers. Must not use outbox. Used for critical events only.

        Returns a ``DispatchResult`` with one ``NotifyResult`` per leg so
        callers (e.g. ``SafeStopHandler``) can bind their truth to
        ``DispatchResult.file_success`` (G-3 PR-3 / memo §3.3.3 / C-4).
        Failures of any leg are logged but never raised — fan-out continues
        to the next leg unconditionally (C-9 non-blocking guarantee).
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
