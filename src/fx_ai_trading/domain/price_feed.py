"""PriceFeed domain interface and DTOs (D3 §2.1.1).

PriceFeed abstracts market data access for live (OANDA) and backtest
(HistoricalPriceFeed) implementations. Pure read — no side effects.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from fx_ai_trading.domain.risk import Instrument

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Candle:
    """A single OHLCV candle."""

    instrument: str
    tier: str
    time_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class PriceTick:
    """Latest bid/ask snapshot for an instrument."""

    instrument: str
    bid: float
    ask: float
    spread: float
    time_utc: datetime


@dataclass(frozen=True)
class PriceEvent:
    """Streaming price update (immutable, Common Keys fields populated by Repository)."""

    instrument: str
    bid: float
    ask: float
    spread: float
    event_time_utc: datetime
    received_at_utc: datetime


@dataclass(frozen=True)
class TransactionEvent:
    """Streaming transaction event from the broker account stream."""

    transaction_id: str
    transaction_type: str
    instrument: str | None
    event_time_utc: datetime
    received_at_utc: datetime
    payload: dict


# ---------------------------------------------------------------------------
# Interface (Protocol)
# ---------------------------------------------------------------------------


class PriceFeed(Protocol):
    """Market raw data abstraction (D3 §2.1.1).

    Invariant: returned data is in ascending time order.
    Side effects: none (pure read).
    Retry policy: caller applies RetryPolicy — PriceFeed itself does not retry.
    """

    def list_active_instruments(self) -> list[Instrument]:
        """Return all currently active instruments."""
        ...

    def get_candles(
        self,
        instrument: str,
        tier: str,
        from_utc: datetime,
        to_utc: datetime,
    ) -> list[Candle]:
        """Return candles for *instrument* in [from_utc, to_utc], ascending."""
        ...

    def get_latest_price(self, instrument: str) -> PriceTick:
        """Return the latest bid/ask snapshot for *instrument*."""
        ...

    def subscribe_price_stream(
        self,
        instruments: list[str],
    ) -> AsyncIterator[PriceEvent]:
        """Return an async iterator of PriceEvents for *instruments*."""
        ...

    def subscribe_transaction_stream(
        self,
        account_id: str,
    ) -> AsyncIterator[TransactionEvent]:
        """Return an async iterator of TransactionEvents for *account_id*."""
        ...
