"""NotifierBase — abstract base for concrete Notifier implementations (D3 §2.10.1).

All concrete notifiers extend NotifierBase and must implement send().

Invariant: FileNotifier.send() must NEVER raise — it is the last-resort path.
           SlackNotifier.send() may fail; callers must handle NotifyResult.success=False.

send() must NOT call datetime.now() or time.time() — the timestamp is taken
from event.occurred_at (injected by caller) to satisfy development_rules.md §13.1.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from fx_ai_trading.domain.notifier import NotifyEvent, NotifyResult


class NotifierBase(ABC):
    """Abstract base for all Notifier implementations.

    Subclasses implement send() for their specific delivery channel.
    """

    @abstractmethod
    def send(self, event: NotifyEvent, severity: str, payload: dict) -> NotifyResult:
        """Deliver *event* through this channel and return a result record."""
