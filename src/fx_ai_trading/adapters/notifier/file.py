"""FileNotifier — last-resort JSONL notification log with fsync (D3 §2.10.1 / 6.13).

Writes every notification to logs/notifications.jsonl using append + flush + fsync.
This is the ONLY notifier guaranteed never to raise — it is the fallback path.

Design constraints:
  - Must not use datetime.now() / time.time() (development_rules.md §13.1).
    Timestamp is taken from event.occurred_at (injected by caller).
  - fsync ensures durability even on OS crash (required by 6.13 completion condition).
  - File is created if absent; parent directory must exist.
  - Thread-safe via threading.Lock (single-process safety).
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from fx_ai_trading.adapters.notifier.base import NotifierBase
from fx_ai_trading.domain.notifier import NotifyEvent, NotifyResult

_DEFAULT_LOG_PATH = Path("logs") / "notifications.jsonl"


class FileNotifier(NotifierBase):
    """Append-only JSONL notification log with fsync.

    Args:
        log_path: Path to the JSONL log file. Defaults to logs/notifications.jsonl.
                  Parent directory must exist before send() is called.
    """

    NAME = "file"

    def __init__(self, log_path: Path = _DEFAULT_LOG_PATH) -> None:
        self._log_path = log_path
        self._lock = threading.Lock()

    def send(self, event: NotifyEvent, severity: str, payload: dict) -> NotifyResult:
        """Append the event to the JSONL log with fsync.

        Never raises — on any I/O error returns NotifyResult(success=False, ...).
        Timestamp is taken from event.occurred_at (no datetime.now() call).
        """
        entry = {
            "event_code": event.event_code,
            "severity": severity,
            "payload": payload,
            "occurred_at": event.occurred_at.isoformat(),
        }
        try:
            with self._lock, self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        except Exception as exc:  # noqa: BLE001
            return NotifyResult(
                success=False,
                notifier_name=self.NAME,
                sent_at=event.occurred_at,
                error_message=str(exc),
            )
        return NotifyResult(success=True, notifier_name=self.NAME, sent_at=event.occurred_at)
