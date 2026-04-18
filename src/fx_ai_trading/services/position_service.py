"""PositionService — thin wrapper around PositionsRepository.

Scope (M3 Cycle 12):
  - get_position(position_snapshot_id) -> dict | None
  - get_open_positions(account_id) -> list[dict]
  - record_position_event(...)
"""

from __future__ import annotations

from sqlalchemy import text

from fx_ai_trading.repositories.positions import PositionsRepository


class PositionService:
    """Provides position-level operations via PositionsRepository."""

    def __init__(self, repo: PositionsRepository) -> None:
        self._repo = repo

    def get_position(self, position_snapshot_id: str) -> dict | None:
        """Return the position snapshot dict, or None."""
        return self._repo.get_by_position_id(position_snapshot_id)

    def get_open_positions(self, account_id: str) -> list[dict]:
        """Return non-close position snapshots for *account_id*."""
        return self._repo.get_open_positions(account_id)

    def record_position_event(
        self,
        position_snapshot_id: str,
        account_id: str,
        instrument: str,
        event_type: str,
        units: str,
        *,
        order_id: str | None = None,
        avg_price: str | None = None,
        unrealized_pl: str | None = None,
        realized_pl: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Insert a position snapshot row via the repository engine."""
        with self._repo._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO positions"
                    " (position_snapshot_id, order_id, account_id, instrument,"
                    "  event_type, units, avg_price, unrealized_pl, realized_pl,"
                    "  event_time_utc, correlation_id)"
                    " VALUES"
                    " (:sid, :order_id, :account_id, :instrument,"
                    "  :event_type, :units, :avg_price, :unrealized_pl, :realized_pl,"
                    "  NOW(), :correlation_id)"
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
