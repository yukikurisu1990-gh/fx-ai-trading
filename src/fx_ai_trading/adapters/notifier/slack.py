"""SlackNotifier — Webhook-based Slack notification (D3 §2.10.1 / 6.13).

Sends a JSON POST to a Slack Incoming Webhook URL.
On failure, returns NotifyResult(success=False) — caller must handle fallback.

Design constraints:
  - Webhook URL loaded from environment variable SLACK_WEBHOOK_URL (never hardcoded).
  - Must not use datetime.now() / time.time() (development_rules.md §13.1).
    Timestamp is taken from event.occurred_at.
  - No retry / backoff — M6 scope (retry is M8+).
  - Connection timeout: 5 seconds (prevents blocking the critical sync path).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from fx_ai_trading.adapters.notifier.base import NotifierBase
from fx_ai_trading.domain.notifier import NotifyEvent, NotifyResult

_WEBHOOK_ENV_VAR = "SLACK_WEBHOOK_URL"
_CONNECT_TIMEOUT_S = 5


class SlackNotifier(NotifierBase):
    """Slack Incoming Webhook notifier.

    Args:
        webhook_url: Slack webhook URL. If None, read from SLACK_WEBHOOK_URL env var.
                     Raises ValueError at init if neither source provides a URL.
    """

    NAME = "slack"

    def __init__(self, webhook_url: str | None = None) -> None:
        url = webhook_url or os.environ.get(_WEBHOOK_ENV_VAR, "").strip()
        if not url:
            raise ValueError(
                f"SlackNotifier requires a webhook URL — set {_WEBHOOK_ENV_VAR} env var"
                " or pass webhook_url explicitly."
            )
        self._webhook_url = url

    def send(self, event: NotifyEvent, severity: str, payload: dict) -> NotifyResult:
        """POST the event to the Slack Incoming Webhook.

        Returns NotifyResult(success=False) on any HTTP or network error.
        No retry — caller is responsible for fallback (FileNotifier).
        """
        body = {
            "text": f"[{severity.upper()}] {event.event_code}",
            "attachments": [
                {
                    "color": _severity_color(severity),
                    "fields": [
                        {"title": k, "value": str(v), "short": True} for k, v in payload.items()
                    ],
                    "footer": event.occurred_at.isoformat(),
                }
            ],
        }
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self._webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=_CONNECT_TIMEOUT_S):
                pass
        except (urllib.error.URLError, OSError, Exception) as exc:  # noqa: BLE001
            return NotifyResult(
                success=False,
                notifier_name=self.NAME,
                sent_at=event.occurred_at,
                error_message=str(exc),
            )
        return NotifyResult(success=True, notifier_name=self.NAME, sent_at=event.occurred_at)


def _severity_color(severity: str) -> str:
    return {"critical": "danger", "warning": "warning", "info": "good"}.get(severity, "#cccccc")
