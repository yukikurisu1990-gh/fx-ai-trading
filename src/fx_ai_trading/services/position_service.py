"""PositionService — thin wrapper around PositionsRepository (D3 §2.9.1).

All writes go through PositionsRepository.insert_event() — never directly
to the engine. This ensures Common Keys context flows through the repo layer.
"""

from __future__ import annotations

from fx_ai_trading.config.common_keys_context import CommonKeysContext
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
        context: CommonKeysContext,
        *,
        order_id: str | None = None,
        avg_price: str | None = None,
        unrealized_pl: str | None = None,
        realized_pl: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Append a position snapshot event via PositionsRepository.insert_event()."""
        self._repo.insert_event(
            position_snapshot_id=position_snapshot_id,
            account_id=account_id,
            instrument=instrument,
            event_type=event_type,
            units=units,
            context=context,
            order_id=order_id,
            avg_price=avg_price,
            unrealized_pl=unrealized_pl,
            realized_pl=realized_pl,
            correlation_id=correlation_id,
        )
