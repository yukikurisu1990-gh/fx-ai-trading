"""OrdersRepository — read/write access to the orders table (D3 §2.9.1).

Status FSM (D1 §6.6): PENDING → SUBMITTED → FILLED | CANCELED | FAILED
Backward transitions raise RepositoryError (enforced by update_status).

Common Keys: orders table has no run_id/environment/code_version/config_version
columns in the current schema. Context is accepted on write methods for contract
compliance; keys are not written to DB until the schema is extended.
"""

from __future__ import annotations

from sqlalchemy import text

from fx_ai_trading.common.exceptions import RepositoryError
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.base import RepositoryBase

# FSM: allowed forward transitions only (D1 §6.6)
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"SUBMITTED", "CANCELED", "FAILED"},
    "SUBMITTED": {"FILLED", "CANCELED", "FAILED"},
    "FILLED": set(),
    "CANCELED": set(),
    "FAILED": set(),
}

_COLUMNS = (
    "order_id",
    "client_order_id",
    "trading_signal_id",
    "account_id",
    "instrument",
    "account_type",
    "order_type",
    "direction",
    "units",
    "status",
    "submitted_at",
    "filled_at",
    "canceled_at",
    "correlation_id",
    "created_at",
)


class OrdersRepository(RepositoryBase):
    """Read/write interface for the orders table."""

    def get_by_order_id(self, order_id: str) -> dict | None:
        """Return the order row for *order_id*, or None if not found."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT order_id, client_order_id, trading_signal_id,"
                    " account_id, instrument, account_type, order_type,"
                    " direction, units, status, submitted_at, filled_at,"
                    " canceled_at, correlation_id, created_at"
                    " FROM orders WHERE order_id = :order_id"
                ),
                {"order_id": order_id},
            ).fetchone()
        if row is None:
            return None
        return dict(zip(_COLUMNS, row, strict=True))

    def create_order(
        self,
        order_id: str,
        account_id: str,
        instrument: str,
        account_type: str,
        order_type: str,
        direction: str,
        units: str,
        context: CommonKeysContext,
        *,
        client_order_id: str | None = None,
        trading_signal_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Insert a new order row with status PENDING.

        context: Common Keys for contract compliance (not yet written to DB).
        """
        self._with_common_keys({}, context)
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO orders"
                    " (order_id, client_order_id, trading_signal_id,"
                    "  account_id, instrument, account_type, order_type,"
                    "  direction, units, correlation_id)"
                    " VALUES"
                    " (:order_id, :client_order_id, :trading_signal_id,"
                    "  :account_id, :instrument, :account_type, :order_type,"
                    "  :direction, :units, :correlation_id)"
                ),
                {
                    "order_id": order_id,
                    "client_order_id": client_order_id,
                    "trading_signal_id": trading_signal_id,
                    "account_id": account_id,
                    "instrument": instrument,
                    "account_type": account_type,
                    "order_type": order_type,
                    "direction": direction,
                    "units": units,
                    "correlation_id": correlation_id,
                },
            )

    def list_open_orders(self) -> list[dict]:
        """Return all orders with PENDING or SUBMITTED status, ordered by created_at.

        Used by StartupReconciler to find orders that need reconciliation.
        Returns dicts with keys: order_id, status.
        """
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT order_id, status FROM orders"
                    " WHERE status IN ('PENDING', 'SUBMITTED')"
                    " ORDER BY created_at ASC"
                )
            ).fetchall()
        return [{"order_id": row[0], "status": row[1]} for row in rows]

    def update_status(
        self,
        order_id: str,
        new_status: str,
        context: CommonKeysContext,
    ) -> None:
        """Transition order to *new_status*, enforcing FSM forward-only rule.

        Raises RepositoryError on backward or invalid transitions.
        context: Common Keys for contract compliance (not yet written to DB).
        """
        self._with_common_keys({}, context)
        with self._engine.begin() as conn:
            row = conn.execute(
                text("SELECT status FROM orders WHERE order_id = :oid"),
                {"oid": order_id},
            ).fetchone()
            if row is None:
                raise RepositoryError(f"Order {order_id!r} not found")
            current = row[0]
            allowed = _VALID_TRANSITIONS.get(current, set())
            if new_status not in allowed:
                raise RepositoryError(
                    f"Invalid order status transition: {current!r} → {new_status!r}"
                )
            conn.execute(
                text("UPDATE orders SET status = :status WHERE order_id = :oid"),
                {"status": new_status, "oid": order_id},
            )
