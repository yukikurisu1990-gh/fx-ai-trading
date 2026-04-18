"""PositionsRepository — append-only read/write for the positions table (D3 §2.9.1).

positions is an append-only event timeline (one row per change event).
No UPDATE/DELETE — only INSERT via insert_event().

Common Keys: positions table has no run_id/environment/code_version/config_version
columns in the current schema. Context is accepted on insert_event() for contract
compliance; keys are not written to DB until the schema is extended.
"""

from __future__ import annotations

from sqlalchemy import text

from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.base import RepositoryBase

_COLUMNS = (
    "position_snapshot_id",
    "order_id",
    "account_id",
    "instrument",
    "event_type",
    "units",
    "avg_price",
    "unrealized_pl",
    "realized_pl",
    "event_time_utc",
    "correlation_id",
)

_OPEN_EVENT_TYPES = ("open", "add", "swap_applied")


class PositionsRepository(RepositoryBase):
    """Read interface for the positions table."""

    def get_by_position_id(self, position_snapshot_id: str) -> dict | None:
        """Return the position snapshot row, or None if not found."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT position_snapshot_id, order_id, account_id, instrument,"
                    " event_type, units, avg_price, unrealized_pl, realized_pl,"
                    " event_time_utc, correlation_id"
                    " FROM positions WHERE position_snapshot_id = :position_snapshot_id"
                ),
                {"position_snapshot_id": position_snapshot_id},
            ).fetchone()
        if row is None:
            return None
        return dict(zip(_COLUMNS, row, strict=True))

    def get_open_positions(self, account_id: str) -> list[dict]:
        """Return non-close position snapshots for *account_id*, newest first.

        Returns rows with event_type in ('open', 'add', 'swap_applied').
        Callers needing the latest-state-per-instrument should group by instrument.
        """
        with self._engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT position_snapshot_id, order_id, account_id, instrument,"
                    " event_type, units, avg_price, unrealized_pl, realized_pl,"
                    " event_time_utc, correlation_id"
                    " FROM positions"
                    " WHERE account_id = :account_id"
                    "   AND event_type IN ('open', 'add', 'swap_applied')"
                    " ORDER BY event_time_utc DESC"
                ),
                {"account_id": account_id},
            )
            return [dict(zip(_COLUMNS, row, strict=True)) for row in result]

    def insert_event(
        self,
        position_snapshot_id: str,
        account_id: str,
        instrument: str,
        event_type: str,
        units: str,
        context: CommonKeysContext,
        *,
        order_id: str | None = None,
        avg_price: str | None = None,
        unrealized_pl: str | None = None,
        realized_pl: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Append a position snapshot event row (append-only, no UPDATE/DELETE).

        event_time_utc is set to DB NOW() to avoid datetime.now() in app code.
        context: Common Keys for contract compliance (not yet written to DB).
        """
        self._with_common_keys({}, context)
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO positions"
                    " (position_snapshot_id, order_id, account_id, instrument,"
                    "  event_type, units, avg_price, unrealized_pl, realized_pl,"
                    "  event_time_utc, correlation_id)"
                    " VALUES"
                    " (:sid, :order_id, :account_id, :instrument,"
                    "  :event_type, :units, :avg_price, :unrealized_pl, :realized_pl,"
                    "  CURRENT_TIMESTAMP, :correlation_id)"
                ),
                {
                    "sid": position_snapshot_id,
                    "order_id": order_id,
                    "account_id": account_id,
                    "instrument": instrument,
                    "event_type": event_type,
                    "units": units,
                    "avg_price": avg_price,
                    "unrealized_pl": unrealized_pl,
                    "realized_pl": realized_pl,
                    "correlation_id": correlation_id,
                },
            )
