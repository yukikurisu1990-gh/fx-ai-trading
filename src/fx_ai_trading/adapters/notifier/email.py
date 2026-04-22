"""EmailNotifier — SMTP email delivery (M17 / 6.13).

Sends notification events via SMTP with STARTTLS and optional auth.
Failure returns NotifyResult(success=False) and never raises — callers
must not treat email failure as a reason to abort critical paths.

Secret safety: SMTP password is read from env at send-time only and is
never stored as an instance attribute or included in log messages.

SafeStop block budget (G-3 PR-2 / docs/design/g3_notifier_fix_plan.md §3.2)
─────────────────────────────────────────────────────────────────────────
The Email channel is the slowest leg of ``NotifierDispatcherImpl``'s
``dispatch_direct_sync`` fan-out, so its worst-case wall-clock directly
caps how long ``SafeStopHandler`` step 3 can block (P-1 SafeStop priority).

  per-attempt timeout        = ``connect_timeout_s`` (default 10s)
  max attempts (retry budget) = ``_MAX_RETRY``       (= 2)
  worst-case wall-clock       = 10s × 2 = **≤ 20s**, well within the
                                ``safe_stop_step3_wall_budget_s = 30``
                                ceiling defined in memo §3.3.1.

The ``timeout`` kwarg passed to ``smtplib.SMTP`` covers both the initial
TCP connect and subsequent socket reads (per Python stdlib docs); it is
the only mechanism that prevents an unresponsive SMTP host from hanging
``safe_stop`` indefinitely (G-3 audit R-2).  Backoff between retries is
intentionally absent — ``time.sleep`` would conflict with the §13.1
clock constraint and the 30s budget already accounts for sequential
re-attempts.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from fx_ai_trading.adapters.notifier.base import NotifierBase
from fx_ai_trading.domain.notifier import NotifyEvent, NotifyResult

_log = logging.getLogger(__name__)

# Reduced from 3 → 2 in G-3 PR-2.  Combined with the new 10s per-attempt
# ``connect_timeout_s``, this caps the Email leg at ≤ 20s and keeps
# ``SafeStopHandler.fire`` step 3 inside the 30s budget (memo §3.2).
_MAX_RETRY = 2

# Default per-attempt SMTP timeout.  Picked at 10s in G-3 PR-2 so that
# 2 sequential attempts fit under the 30s ``safe_stop_step3_wall_budget_s``
# with headroom for File + Slack legs (memo §3.2 / §3.3.1).
_DEFAULT_CONNECT_TIMEOUT_S = 10


class EmailNotifier(NotifierBase):
    """SMTP-backed notifier (STARTTLS + optional auth).

    Args:
        host: SMTP server hostname.
        port: SMTP server port (default 587 for STARTTLS).
        sender: From address.
        recipients: List of To addresses.
        username: SMTP auth username (optional).
        password: SMTP auth password (optional — never logged).
        use_starttls: Whether to issue STARTTLS after EHLO (default True).
        connect_timeout_s: Per-attempt SMTP socket timeout in seconds
            (default 10).  Forwarded as the ``timeout`` kwarg of
            ``smtplib.SMTP`` so it bounds both the TCP connect and any
            subsequent socket reads.  Combined with ``_MAX_RETRY = 2``
            this caps the Email leg at ≤ 20s (G-3 PR-2 / memo §3.2).
            Must be > 0; see module docstring for the SafeStop budget
            rationale.
    """

    def __init__(
        self,
        host: str,
        port: int,
        sender: str,
        recipients: list[str],
        username: str | None = None,
        password: str | None = None,
        *,
        use_starttls: bool = True,
        connect_timeout_s: int = _DEFAULT_CONNECT_TIMEOUT_S,
    ) -> None:
        self._host = host
        self._port = port
        self._sender = sender
        self._recipients = list(recipients)
        self._username = username
        self._password = password
        self._use_starttls = use_starttls
        self._connect_timeout_s = connect_timeout_s

    # ------------------------------------------------------------------
    # NotifierBase implementation
    # ------------------------------------------------------------------

    def send(self, event: NotifyEvent, severity: str, payload: dict) -> NotifyResult:
        """Send *event* via SMTP.  Returns NotifyResult — never raises.

        Retries up to _MAX_RETRY times on transient SMTP errors.
        SMTP password is never included in log output.
        """
        subject = f"[{severity.upper()}] {event.event_code}"
        body = self._format_body(event, severity, payload)

        last_error: str | None = None
        for attempt in range(1, _MAX_RETRY + 1):
            try:
                self._send_one(subject, body)
                return NotifyResult(
                    success=True,
                    notifier_name="email",
                    sent_at=event.occurred_at,
                )
            except (smtplib.SMTPException, OSError) as exc:
                last_error = type(exc).__name__
                _log.warning(
                    "EmailNotifier attempt %d/%d failed for %s: %s",
                    attempt,
                    _MAX_RETRY,
                    event.event_code,
                    type(exc).__name__,
                )

        return NotifyResult(
            success=False,
            notifier_name="email",
            sent_at=event.occurred_at,
            error_message=last_error,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _send_one(self, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"] = self._sender
        msg["To"] = ", ".join(self._recipients)
        msg["Subject"] = subject
        msg.set_content(body)

        # ``timeout`` (PR-2) bounds both the initial TCP connect and any
        # subsequent socket reads — without this an unresponsive SMTP host
        # would hang ``safe_stop`` step 3 indefinitely (memo §3.2 / R-2).
        with smtplib.SMTP(self._host, self._port, timeout=self._connect_timeout_s) as smtp:
            if self._use_starttls:
                smtp.starttls()
            if self._username is not None and self._password is not None:
                smtp.login(self._username, self._password)
            smtp.send_message(msg)

    def _format_body(self, event: NotifyEvent, severity: str, payload: dict) -> str:
        lines = [
            f"Event   : {event.event_code}",
            f"Severity: {severity}",
            f"Time    : {event.occurred_at.isoformat()}",
            "",
            "Payload:",
        ]
        for k, v in payload.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)
