"""EventBus domain interface and DTOs (D3 §2.14.1).

At-least-once delivery with idempotent consumers.
Three execution-mode implementations share this interface (InProcessEventBus /
LocalQueueEventBus / NetworkBusEventBus).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Event:
    """A domain event published to the EventBus."""

    topic: str
    event_id: str
    payload: dict
    occurred_at: datetime


@dataclass(frozen=True)
class SubscriptionId:
    """Opaque handle returned by EventBus.subscribe()."""

    value: str


# ---------------------------------------------------------------------------
# Interface (Protocol)
# ---------------------------------------------------------------------------


class EventBus(Protocol):
    """Inter-system communication bus (D3 §2.14.1).

    Delivery semantics: at-least-once + idempotent consumer (Phase 2).
    Same interface across all execution modes:
      - InProcessEventBus  (single_process_mode, MVP default)
      - LocalQueueEventBus (multi_service_mode, Phase 7+)
      - NetworkBusEventBus (container_ready_mode, Phase 8+)
    """

    def publish(self, topic: str, event: Event) -> None:
        """Publish *event* to *topic*."""
        ...

    def subscribe(self, topic: str, handler: Callable[[Event], None]) -> SubscriptionId:
        """Register *handler* for *topic*, return opaque subscription handle."""
        ...

    def unsubscribe(self, subscription_id: SubscriptionId) -> None:
        """Deregister the subscription identified by *subscription_id*."""
        ...
