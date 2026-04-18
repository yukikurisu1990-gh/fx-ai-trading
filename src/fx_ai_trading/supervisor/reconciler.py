"""StartupReconciler — order state reconciliation at startup (M8).

Implements the Action Matrix (D4 §2.1 / M8) for reconciling DB order state
with broker state after a restart or crash.

Action Matrix (11 cases):
  DB_Status   | Broker_Status | Action
  ------------|---------------|----------
  PENDING     | not_found     | MARK_FAILED
  PENDING     | open/pending  | MARK_SUBMITTED
  PENDING     | filled        | MARK_FAILED  (edge: skipped SUBMITTED)
  PENDING     | canceled      | MARK_CANCELED
  SUBMITTED   | not_found     | MARK_FAILED  (orphaned)
  SUBMITTED   | open          | NO_OP        (normal in-flight)
  SUBMITTED   | filled        | MARK_FILLED
  SUBMITTED   | canceled      | MARK_CANCELED
  SUBMITTED   | failed        | MARK_FAILED
  FILLED      | any           | NO_OP        (terminal)
  CANCELED    | any           | NO_OP        (terminal)
  FAILED      | any           | NO_OP        (terminal)

Design constraints:
  - classify() is a pure function (testable in isolation).
  - reconcile() is single-shot (no while loop, no polling).
  - Broker is optional: if not provided, classify() treats all orders as NOT_FOUND.
  - In M8, broker status lookup is a skeleton (returns NOT_FOUND for all orders).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.orders import OrdersRepository

_log = logging.getLogger(__name__)

# Broker status constants (canonical strings used in classify())
_BROKER_NOT_FOUND = "not_found"
_BROKER_OPEN = "open"
_BROKER_PENDING = "pending"
_BROKER_FILLED = "filled"
_BROKER_CANCELED = "canceled"
_BROKER_FAILED = "failed"

# DB statuses considered "open" (not terminal)
_OPEN_DB_STATUSES = frozenset({"PENDING", "SUBMITTED"})
_TERMINAL_DB_STATUSES = frozenset({"FILLED", "CANCELED", "FAILED"})


class ReconcilerAction(Enum):
    """Action to take when DB and broker states diverge."""

    NO_OP = "no_op"
    MARK_SUBMITTED = "mark_submitted"
    MARK_FILLED = "mark_filled"
    MARK_CANCELED = "mark_canceled"
    MARK_FAILED = "mark_failed"


@dataclass
class ReconcileOutcome:
    """Summary of a reconcile() run."""

    examined: int = 0
    no_ops: int = 0
    submitted: int = 0
    filled: int = 0
    canceled: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


class StartupReconciler:
    """Reconciles open orders (PENDING/SUBMITTED) against broker state at startup.

    Args:
        orders_repo: OrdersRepository for reading open orders and writing transitions.
        context: CommonKeysContext for all repository write operations.
        broker: Optional broker adapter.  If None, all open orders are treated as
            NOT_FOUND at the broker and reconciled accordingly.
    """

    def __init__(
        self,
        orders_repo: OrdersRepository,
        context: CommonKeysContext,
        broker: object | None = None,
    ) -> None:
        self._orders_repo = orders_repo
        self._context = context
        self._broker = broker

    # ------------------------------------------------------------------
    # Pure classification function (testable)
    # ------------------------------------------------------------------

    @staticmethod
    def classify(db_status: str, broker_status: str | None) -> ReconcilerAction:
        """Return the reconciler action for a (db_status, broker_status) pair.

        Args:
            db_status: Current status in the orders table (e.g. 'PENDING').
            broker_status: Status reported by the broker, or None if not found.

        Returns:
            ReconcilerAction indicating what the reconciler should do.
        """
        if db_status in _TERMINAL_DB_STATUSES:
            return ReconcilerAction.NO_OP

        effective_broker = broker_status or _BROKER_NOT_FOUND

        if db_status == "PENDING":
            if effective_broker == _BROKER_NOT_FOUND:
                return ReconcilerAction.MARK_FAILED
            if effective_broker in (_BROKER_OPEN, _BROKER_PENDING):
                return ReconcilerAction.MARK_SUBMITTED
            if effective_broker == _BROKER_FILLED:
                # Skipped SUBMITTED state — cannot do a valid PENDING→SUBMITTED→FILLED
                # transition in one step.  Mark FAILED for manual review.
                return ReconcilerAction.MARK_FAILED
            if effective_broker == _BROKER_CANCELED:
                return ReconcilerAction.MARK_CANCELED
            if effective_broker == _BROKER_FAILED:
                return ReconcilerAction.MARK_FAILED
            # Unknown broker status — conservative: mark FAILED
            return ReconcilerAction.MARK_FAILED

        if db_status == "SUBMITTED":
            if effective_broker == _BROKER_NOT_FOUND:
                return ReconcilerAction.MARK_FAILED
            if effective_broker == _BROKER_OPEN:
                return ReconcilerAction.NO_OP
            if effective_broker == _BROKER_FILLED:
                return ReconcilerAction.MARK_FILLED
            if effective_broker == _BROKER_CANCELED:
                return ReconcilerAction.MARK_CANCELED
            if effective_broker == _BROKER_FAILED:
                return ReconcilerAction.MARK_FAILED
            # Unknown broker status — conservative: no-op (avoid data loss)
            return ReconcilerAction.NO_OP

        # Unknown DB status — do nothing
        return ReconcilerAction.NO_OP

    # ------------------------------------------------------------------
    # Single-shot reconciliation
    # ------------------------------------------------------------------

    def reconcile(self) -> ReconcileOutcome:
        """Query all open orders and apply the action matrix.

        Single-shot — does not loop or poll.  Called once at startup (Step 10).

        Returns:
            ReconcileOutcome with counts of actions taken and any errors.
        """
        _log.info("StartupReconciler.reconcile: starting")
        outcome = ReconcileOutcome()

        open_orders = self._get_open_orders()
        outcome.examined = len(open_orders)

        if not open_orders:
            _log.info("StartupReconciler.reconcile: no open orders — nothing to reconcile")
            return outcome

        _log.info("StartupReconciler.reconcile: examining %d open orders", len(open_orders))

        for order in open_orders:
            order_id = order["order_id"]
            db_status = order["status"]
            broker_status = self._get_broker_status(order_id)
            action = self.classify(db_status, broker_status)

            _log.debug(
                "StartupReconciler: order=%s db=%s broker=%s action=%s",
                order_id,
                db_status,
                broker_status,
                action.value,
            )

            self._apply_action(order_id, action, outcome)

        _log.info(
            "StartupReconciler.reconcile: done — examined=%d no_ops=%d submitted=%d"
            " filled=%d canceled=%d failed=%d errors=%d",
            outcome.examined,
            outcome.no_ops,
            outcome.submitted,
            outcome.filled,
            outcome.canceled,
            outcome.failed,
            len(outcome.errors),
        )
        return outcome

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_open_orders(self) -> list[dict]:
        """Return all orders with PENDING or SUBMITTED status."""
        from sqlalchemy import text

        with self._orders_repo._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT order_id, status FROM orders"
                    " WHERE status IN ('PENDING', 'SUBMITTED')"
                    " ORDER BY created_at ASC"
                )
            ).fetchall()
        return [{"order_id": row[0], "status": row[1]} for row in rows]

    def _get_broker_status(self, order_id: str) -> str | None:
        """Query broker for the status of *order_id*.

        In M8: skeleton — returns None (not_found) for all orders.
        In M9+: will call broker.get_order(order_id).
        """
        if self._broker is None:
            return None
        # M9+ implementation: return broker.get_order(order_id).status
        _log.debug("StartupReconciler._get_broker_status: broker stub — returning None")
        return None

    def _apply_action(
        self,
        order_id: str,
        action: ReconcilerAction,
        outcome: ReconcileOutcome,
    ) -> None:
        """Apply *action* to *order_id* and update *outcome* counters."""
        try:
            if action == ReconcilerAction.NO_OP:
                outcome.no_ops += 1
            elif action == ReconcilerAction.MARK_SUBMITTED:
                self._orders_repo.update_status(order_id, "SUBMITTED", self._context)
                outcome.submitted += 1
            elif action == ReconcilerAction.MARK_FILLED:
                self._orders_repo.update_status(order_id, "FILLED", self._context)
                outcome.filled += 1
            elif action == ReconcilerAction.MARK_CANCELED:
                self._orders_repo.update_status(order_id, "CANCELED", self._context)
                outcome.canceled += 1
            elif action == ReconcilerAction.MARK_FAILED:
                self._orders_repo.update_status(order_id, "FAILED", self._context)
                outcome.failed += 1
        except Exception as exc:  # noqa: BLE001
            msg = f"order={order_id} action={action.value} error={exc}"
            _log.error("StartupReconciler._apply_action: %s", msg)
            outcome.errors.append(msg)
