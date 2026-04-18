"""OutboxProcessor — single-shot Outbox event dispatcher (M8).

Picks pending outbox_events and dispatches them to the broker.

Design constraints (D1 §6.6 / CLAUDE.md §14):
  - Single-shot processing: dispatch_pending() processes up to `limit` events and returns.
  - No while loop, no polling, no automatic retry.
  - Called by Supervisor at startup (step 8 / step 14) and externally on demand.
  - pause() / resume() are skeleton methods (full implementation: M9+).

Dispatch flow per event:
  1. mark_dispatching()    — status: pending → dispatching
  2. broker dispatch       — skeleton in M8 (broker is optional)
  3. mark_acked() OR mark_failed()  — dispatching → acked/failed

Broker interaction is skeleton in M8: if no broker is provided, events are
marked as 'acked' immediately (simulating successful dispatch).
"""

from __future__ import annotations

import logging

from fx_ai_trading.common.clock import Clock, WallClock
from fx_ai_trading.common.exceptions import RepositoryError
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.outbox_events import OutboxEventsRepository

_log = logging.getLogger(__name__)


class OutboxProcessor:
    """Dispatches pending outbox events to the broker.

    Args:
        outbox_repo: OutboxEventsRepository for status management.
        context: CommonKeysContext propagated to repository writes.
        clock: Clock for dispatch timestamps.
        broker: Optional broker for dispatch; if None events are auto-acked (M8 skeleton).
    """

    def __init__(
        self,
        outbox_repo: OutboxEventsRepository,
        context: CommonKeysContext,
        clock: Clock | None = None,
        broker: object | None = None,
    ) -> None:
        self._outbox_repo = outbox_repo
        self._context = context
        self._clock: Clock = clock or WallClock()
        self._broker = broker
        self._paused = False

    def dispatch_pending(self, limit: int = 100) -> int:
        """Process up to *limit* pending outbox events.

        Returns:
            Number of events processed (acked + failed).

        Note:
            If paused, logs a warning and returns 0 immediately.
            No retry — failed events remain in 'failed' status for external handling.
        """
        if self._paused:
            _log.warning("OutboxProcessor.dispatch_pending: processor is paused — skipping")
            return 0

        pending = self._outbox_repo.get_pending(limit=limit)
        if not pending:
            _log.info("OutboxProcessor.dispatch_pending: no pending events")
            return 0

        _log.info("OutboxProcessor.dispatch_pending: processing %d events", len(pending))
        processed = 0

        for event in pending:
            event_id = event["outbox_event_id"]
            order_id = event.get("order_id")
            event_type = event["event_type"]

            try:
                attempted_at = self._clock.now()
                self._outbox_repo.mark_dispatching(
                    event_id,
                    attempted_at=attempted_at,
                    context=self._context,
                )
            except RepositoryError as exc:
                _log.warning(
                    "OutboxProcessor: cannot mark event %s as dispatching: %s — skipping",
                    event_id,
                    exc,
                )
                continue

            success = self._dispatch_event(event_id, order_id, event_type)

            if success:
                try:
                    self._outbox_repo.mark_acked(event_id, context=self._context)
                    _log.info("OutboxProcessor: event %s acked", event_id)
                except RepositoryError as exc:
                    _log.error("OutboxProcessor: failed to mark %s acked: %s", event_id, exc)
            else:
                try:
                    self._outbox_repo.mark_failed(event_id, context=self._context)
                    _log.warning("OutboxProcessor: event %s marked failed", event_id)
                except RepositoryError as exc:
                    _log.error("OutboxProcessor: failed to mark %s failed: %s", event_id, exc)

            processed += 1

        _log.info("OutboxProcessor.dispatch_pending: processed %d events", processed)
        return processed

    def pause(self) -> None:
        """Pause dispatch. Skeleton — full implementation M9+."""
        self._paused = True
        _log.info("OutboxProcessor: paused")

    def resume(self) -> None:
        """Resume dispatch. Skeleton — full implementation M9+."""
        self._paused = False
        _log.info("OutboxProcessor: resumed")

    # ------------------------------------------------------------------
    # Internal dispatch (skeleton in M8)
    # ------------------------------------------------------------------

    def _dispatch_event(
        self,
        event_id: str,
        order_id: str | None,
        event_type: str,
    ) -> bool:
        """Dispatch a single outbox event.  Returns True on success.

        In M8: if no broker is wired, returns True (auto-ack skeleton).
        In M9+: will call broker.place_order() or broker.cancel_order() etc.
        """
        if self._broker is None:
            _log.info(
                "OutboxProcessor._dispatch_event: no broker wired — auto-ack (M8 skeleton)"
                " event_id=%s event_type=%s",
                event_id,
                event_type,
            )
            return True

        # M9+ implementation: route by event_type to broker method
        _log.info(
            "OutboxProcessor._dispatch_event: broker dispatch stub"
            " event_id=%s event_type=%s order_id=%s",
            event_id,
            event_type,
            order_id,
        )
        return True
