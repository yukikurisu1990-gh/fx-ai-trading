"""MidRunReconciler — mid-run order drift checker (M15 / Ob-MIDRUN-1).

Responsibilities:
  - Called by the Supervisor (Step 13) on a 15-min timer or on stream gap recovery.
  - Queries PENDING/SUBMITTED orders, classifies each against broker state, and
    applies corrective transitions using the same Action Matrix as StartupReconciler.
  - Rate-limited to avoid blocking the trading critical path:
      normal priority → reconcile bucket (2 rps, §6.2)
      high priority   → trading bucket   (10 rps, gap-recovery mode)

Design constraints:
  - Single-shot: no while loop, no polling.
  - Broker is optional; if absent, all orders are treated as NOT_FOUND.
  - The 15-min timer is owned by the Supervisor (Step 13), not by this class.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import Engine, text

from fx_ai_trading.common.clock import Clock, WallClock
from fx_ai_trading.common.rate_limiter import RateLimiter
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.orders import OrdersRepository
from fx_ai_trading.repositories.reconciliation_events import (
    ReconciliationEventsRepository,
)
from fx_ai_trading.supervisor.reconciler import ReconcilerAction, StartupReconciler

_log = logging.getLogger(__name__)

_PRIORITY_BUCKET = {"normal": "reconcile", "high": "trading"}

# Map ReconcilerAction → action_taken string written to reconciliation_events.
_ACTION_TAKEN_LABEL = {
    ReconcilerAction.MARK_SUBMITTED: "MARK_SUBMITTED",
    ReconcilerAction.MARK_FILLED: "MARK_FILLED",
    ReconcilerAction.MARK_CANCELED: "MARK_CANCELED",
    ReconcilerAction.MARK_FAILED: "MARK_FAILED",
}

# Allowed trigger_reason values for MidRunReconciler audit rows.  Restricted
# so a typo at the call site does not silently land an unrecognised value.
_VALID_TRIGGER_REASONS = frozenset({"midrun_heartbeat_gap", "periodic_drift_check"})

# trigger_reason / action_taken used when an outbox_stale signal is detected.
_OUTBOX_STALE_TRIGGER_REASON = "outbox_stale"
_OUTBOX_STALE_ACTION = "outbox_stale_detected"


@dataclass
class MidRunOutcome:
    """Summary of a MidRunReconciler.check() run."""

    examined: int = 0
    applied: int = 0
    skipped_by_rate_limit: int = 0
    errors: list[str] = field(default_factory=list)


class MidRunReconciler:
    """Mid-run order state drift checker with RateLimiter bucket switching.

    Args:
        orders_repo: OrdersRepository for reading and updating order state.
        context: CommonKeysContext for repository writes.
        rate_limiter: RateLimiter instance (injected for testability).
        broker: Optional broker adapter; if None, all orders classified as NOT_FOUND.
        reconciliation_repo: Optional ReconciliationEventsRepository.  When
            provided, every non-NO_OP action emits one audit row using the
            configured ``trigger_reason``.  When None (default), no audit
            rows are written — preserves the original M15 behaviour.
        trigger_reason: trigger_reason value written to reconciliation_events
            for action audit rows.  Must be ``'midrun_heartbeat_gap'`` or
            ``'periodic_drift_check'``.  Default ``'midrun_heartbeat_gap'``.
        engine: Optional SQLAlchemy Engine.  Required for the outbox_stale
            check; ignored when ``outbox_stale_seconds`` is None.
        outbox_stale_seconds: Threshold for the secondary_sync_outbox
            staleness query at the end of ``check()``.  When None (default),
            the outbox_stale check is skipped entirely.
        clock: Optional Clock for stamping event_time_utc on audit rows
            and for computing the outbox_stale threshold.  Defaults to
            WallClock().
    """

    def __init__(
        self,
        orders_repo: OrdersRepository,
        context: CommonKeysContext,
        rate_limiter: RateLimiter | None = None,
        broker: object | None = None,
        reconciliation_repo: ReconciliationEventsRepository | None = None,
        trigger_reason: str = "midrun_heartbeat_gap",
        engine: Engine | None = None,
        outbox_stale_seconds: int | None = None,
        clock: Clock | None = None,
    ) -> None:
        if trigger_reason not in _VALID_TRIGGER_REASONS:
            raise ValueError(
                f"trigger_reason must be one of {sorted(_VALID_TRIGGER_REASONS)}, "
                f"got {trigger_reason!r}"
            )
        self._orders_repo = orders_repo
        self._context = context
        self._rate_limiter = rate_limiter or RateLimiter()
        self._broker = broker
        self._reconciliation_repo = reconciliation_repo
        self._trigger_reason = trigger_reason
        self._engine = engine
        self._outbox_stale_seconds = outbox_stale_seconds
        self._clock = clock or WallClock()

    def check(
        self,
        order_ids: list[str] | None = None,
        priority: str = "normal",
    ) -> MidRunOutcome:
        """Check in-flight orders for state drift and apply corrective actions.

        Single-shot — does not loop.  Called by Supervisor Step 13.

        Args:
            order_ids: Optional explicit list of order IDs to examine.
                       If None, all PENDING/SUBMITTED orders are checked.
            priority: "normal" → reconcile bucket (low priority, 2 rps).
                      "high"   → trading bucket (high priority, gap recovery).

        Returns:
            MidRunOutcome with counters for examined, applied, skipped, and errors.
        """
        bucket = _PRIORITY_BUCKET.get(priority, "reconcile")
        outcome = MidRunOutcome()

        open_orders = self._orders_repo.list_open_orders()
        if order_ids is not None:
            id_set = set(order_ids)
            open_orders = [o for o in open_orders if o["order_id"] in id_set]

        outcome.examined = len(open_orders)
        _log.info(
            "MidRunReconciler.check: priority=%s bucket=%s examining=%d",
            priority,
            bucket,
            outcome.examined,
        )

        for order in open_orders:
            if not self._rate_limiter.acquire(bucket):
                outcome.skipped_by_rate_limit += 1
                _log.warning("MidRunReconciler: rate-limited, skipping order=%s", order["order_id"])
                continue

            self._process_order(order, outcome, priority)

        self._check_outbox_stale()

        _log.info(
            "MidRunReconciler.check: done examined=%d applied=%d skipped=%d errors=%d",
            outcome.examined,
            outcome.applied,
            outcome.skipped_by_rate_limit,
            len(outcome.errors),
        )
        return outcome

    def _process_order(self, order: dict, outcome: MidRunOutcome, priority: str) -> None:
        order_id = order["order_id"]
        db_status = order["status"]
        broker_status = self._get_broker_status(order_id)
        action = StartupReconciler.classify(db_status, broker_status)

        _log.debug(
            "MidRunReconciler: order=%s db=%s broker=%s action=%s",
            order_id,
            db_status,
            broker_status,
            action.value,
        )

        if action == ReconcilerAction.NO_OP:
            return

        try:
            if action == ReconcilerAction.MARK_SUBMITTED:
                self._orders_repo.update_status(order_id, "SUBMITTED", self._context)
            elif action == ReconcilerAction.MARK_FILLED:
                self._orders_repo.update_status(order_id, "FILLED", self._context)
            elif action == ReconcilerAction.MARK_CANCELED:
                self._orders_repo.update_status(order_id, "CANCELED", self._context)
            elif action == ReconcilerAction.MARK_FAILED:
                self._orders_repo.update_status(order_id, "FAILED", self._context)
            outcome.applied += 1
            self._record_audit(order_id, action, db_status, broker_status, priority)
        except Exception as exc:  # noqa: BLE001
            msg = f"order={order_id} action={action.value} error={exc}"
            _log.error("MidRunReconciler._process_order: %s", msg)
            outcome.errors.append(msg)

    def _get_broker_status(self, order_id: str) -> str | None:
        if self._broker is None:
            return None
        _log.debug("MidRunReconciler._get_broker_status: broker stub — returning None")
        return None

    def _record_audit(
        self,
        order_id: str,
        action: ReconcilerAction,
        db_status: str,
        broker_status: str | None,
        priority: str,
    ) -> None:
        """Write one reconciliation_events row for a non-NO_OP action."""
        if self._reconciliation_repo is None:
            return
        try:
            self._reconciliation_repo.insert(
                trigger_reason=self._trigger_reason,
                action_taken=_ACTION_TAKEN_LABEL[action],
                event_time_utc=self._clock.now(),
                order_id=order_id,
                detail={
                    "db_status": db_status,
                    "broker_status": broker_status,
                    "priority": priority,
                },
            )
        except Exception as exc:  # noqa: BLE001
            _log.error(
                "MidRunReconciler._record_audit failed: order=%s action=%s error=%s",
                order_id,
                action.value,
                exc,
            )

    def _check_outbox_stale(self) -> None:
        """Detect stale rows in secondary_sync_outbox and emit one audit row.

        Stale criterion (mirror of migration 0013 worker poll):
            ``acked_at IS NULL AND enqueued_at < now() - interval``

        Emits at most one ``trigger_reason='outbox_stale'`` row per
        ``check()``, with detail aggregating count / oldest_enqueued_at /
        table_names.  Skipped entirely when ``engine`` or
        ``outbox_stale_seconds`` is None, or when no stale rows exist.
        """
        if (
            self._reconciliation_repo is None
            or self._engine is None
            or self._outbox_stale_seconds is None
        ):
            return

        try:
            with self._engine.connect() as conn:
                rows = conn.execute(
                    text(
                        "SELECT table_name, enqueued_at FROM secondary_sync_outbox"
                        " WHERE acked_at IS NULL"
                        " AND enqueued_at < :threshold"
                    ),
                    {
                        "threshold": self._clock.now()
                        - timedelta(seconds=self._outbox_stale_seconds),
                    },
                ).fetchall()
        except Exception as exc:  # noqa: BLE001
            _log.error("MidRunReconciler._check_outbox_stale query failed: %s", exc)
            return

        if not rows:
            return

        oldest = min(r[1] for r in rows)
        table_names = sorted({r[0] for r in rows})
        try:
            self._reconciliation_repo.insert(
                trigger_reason=_OUTBOX_STALE_TRIGGER_REASON,
                action_taken=_OUTBOX_STALE_ACTION,
                event_time_utc=self._clock.now(),
                detail={
                    "count": len(rows),
                    "oldest_enqueued_at": oldest.isoformat() if oldest else None,
                    "table_names": table_names,
                },
            )
        except Exception as exc:  # noqa: BLE001
            _log.error("MidRunReconciler._check_outbox_stale audit insert failed: %s", exc)
