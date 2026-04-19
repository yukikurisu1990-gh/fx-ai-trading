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

from fx_ai_trading.common.rate_limiter import RateLimiter
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.orders import OrdersRepository
from fx_ai_trading.supervisor.reconciler import ReconcilerAction, StartupReconciler

_log = logging.getLogger(__name__)

_PRIORITY_BUCKET = {"normal": "reconcile", "high": "trading"}


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
    """

    def __init__(
        self,
        orders_repo: OrdersRepository,
        context: CommonKeysContext,
        rate_limiter: RateLimiter | None = None,
        broker: object | None = None,
    ) -> None:
        self._orders_repo = orders_repo
        self._context = context
        self._rate_limiter = rate_limiter or RateLimiter()
        self._broker = broker

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

            self._process_order(order, outcome)

        _log.info(
            "MidRunReconciler.check: done examined=%d applied=%d skipped=%d errors=%d",
            outcome.examined,
            outcome.applied,
            outcome.skipped_by_rate_limit,
            len(outcome.errors),
        )
        return outcome

    def _process_order(self, order: dict, outcome: MidRunOutcome) -> None:
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
        except Exception as exc:  # noqa: BLE001
            msg = f"order={order_id} action={action.value} error={exc}"
            _log.error("MidRunReconciler._process_order: %s", msg)
            outcome.errors.append(msg)

    def _get_broker_status(self, order_id: str) -> str | None:
        if self._broker is None:
            return None
        _log.debug("MidRunReconciler._get_broker_status: broker stub — returning None")
        return None
