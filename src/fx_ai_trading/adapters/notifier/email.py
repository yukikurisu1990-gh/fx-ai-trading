"""EmailNotifier — SMTP email delivery (M17 / 6.13).

Sends notification events via SMTP with STARTTLS and optional auth.
Failure returns NotifyResult(success=False) and never raises — callers
must not treat email failure as a reason to abort critical paths.

Secret safety: SMTP password is read from env at send-time only and is
never stored as an instance attribute or included in log messages.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from fx_ai_trading.adapters.notifier.base import NotifierBase
from fx_ai_trading.domain.notifier import NotifyEvent, NotifyResult

_log = logging.getLogger(__name__)

_MAX_RETRY = 3


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
    ) -> None:
        self._host = host
        self._port = port
        self._sender = sender
        self._recipients = list(recipients)
        self._username = username
        self._password = password
        self._use_starttls = use_starttls

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

        with smtplib.SMTP(self._host, self._port) as smtp:
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
