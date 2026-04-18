"""MidRunReconciler — mid-run order state reconciler skeleton (M8).

Responsibilities (full implementation: M9+):
  - Periodically check in-flight orders during the trading loop.
  - Detect orders that have been in SUBMITTED state beyond expected fill time.
  - Initiate FAILED transition for timed-out submitted orders.

M8 scope: skeleton class with stub check() method.
  - No while loop, no polling, no automatic retry.
  - Called by Supervisor (step 13) once per startup; full loop integration M9+.
"""

from __future__ import annotations

import logging

from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.orders import OrdersRepository

_log = logging.getLogger(__name__)


class MidRunReconciler:
    """Skeleton mid-run order state reconciler.

    Args:
        orders_repo: OrdersRepository for reading and updating order state.
        context: CommonKeysContext for repository writes.
    """

    def __init__(
        self,
        orders_repo: OrdersRepository,
        context: CommonKeysContext,
    ) -> None:
        self._orders_repo = orders_repo
        self._context = context

    def check(self, order_ids: list[str] | None = None) -> None:
        """Check in-flight orders for stale state.

        M8 skeleton — logs the call with the order count.
        Full implementation (M9+): detect timed-out SUBMITTED orders and fail them.

        Args:
            order_ids: Optional list of specific order IDs to check.
                       If None, checks all open orders (M9+).
        """
        count = len(order_ids) if order_ids is not None else "all"
        _log.info("MidRunReconciler.check: examining %s orders (M8 skeleton)", count)
