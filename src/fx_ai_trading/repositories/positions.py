"""PositionsRepository — read access to the positions table.

Scope (M3 Cycle 10):
  - get_by_position_id(position_snapshot_id) -> dict | None
  - get_open_positions(account_id) -> list[dict]

positions is an append-only timeline (one row per change event).
get_open_positions returns snapshots with event_type in ('open','add','swap_applied').
Common Keys physical columns are M5 scope.
"""

from __future__ import annotations

from sqlalchemy import text

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
