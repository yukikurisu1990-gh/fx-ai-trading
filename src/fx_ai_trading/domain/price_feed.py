"""PriceFeed domain interface and DTOs (D3 §2.1.1).

PriceFeed abstracts market data access for live (OANDA) and backtest
(HistoricalPriceFeed) implementations. Pure read — no side effects.

BarFeed (Phase 9.1) abstracts the bar-cadence data source used by the D3
decision loop (run_paper_decision_loop). Yields completed Candle objects at
1m/5m granularity — one Candle per tick of the decision loop.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Final, Protocol, runtime_checkable

from fx_ai_trading.common.clock import Clock
from fx_ai_trading.domain.risk import Instrument

# ---------------------------------------------------------------------------
# Source constants for Quote.source (M-3a)
# ---------------------------------------------------------------------------
# Minimal set — kept here to prevent typo drift across producers / tests.
# Add new sources only when an actual producer lands; do not pre-declare.

SOURCE_LEGACY_CALLABLE: Final[str] = "legacy_callable"
SOURCE_OANDA_CANDLE_REPLAY: Final[str] = "oanda_candle_replay"
SOURCE_OANDA_LIVE: Final[str] = "oanda_live"
SOURCE_OANDA_REST_SNAPSHOT: Final[str] = "oanda_rest_snapshot"
SOURCE_PAPER: Final[str] = "paper"
SOURCE_TEST_FIXTURE: Final[str] = "test_fixture"

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Candle:
    """A single OHLCV candle.

    ``open``/``high``/``low``/``close`` are mid-price OHLC (the legacy
    shape). Phase 9.10 adds optional ``bid_close`` / ``ask_close`` so
    cost-aware replay feeds can project side-specific prices into the
    downstream ``Quote`` without bloating Candle with full bid/ask OHLC
    — consumers that need bid/ask high/low (e.g. a grid-search backtest
    doing TP/SL barrier checks) should read the source JSONL directly.
    """

    instrument: str
    tier: str
    time_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    bid_close: float | None = None
    ask_close: float | None = None

    def __post_init__(self) -> None:
        # Mirror Quote: both-or-neither, and ask >= bid when populated.
        if (self.bid_close is None) != (self.ask_close is None):
            raise ValueError(
                "Candle.bid_close and Candle.ask_close must both be set or both be None "
                f"(got bid_close={self.bid_close!r}, ask_close={self.ask_close!r})."
            )
        if (
            self.bid_close is not None
            and self.ask_close is not None
            and self.ask_close < self.bid_close
        ):
            raise ValueError(
                f"Candle.ask_close ({self.ask_close!r}) must be >= bid_close ({self.bid_close!r})."
            )


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


@dataclass(frozen=True)
class Quote:
    """Single mid-price snapshot for the exit / execution path (M-3a).

    Distinct from ``PriceTick`` (bid/ask/spread oriented): consumers that
    only need a single price (run_exit_gate, ExitPolicyService) stay
    decoupled from the bid/ask split, and ``ts`` / ``source`` give the
    staleness layer (M-3c) something authoritative to inspect.

    Phase 9.10: optional ``bid`` / ``ask`` fields let cost-aware consumers
    (PaperBroker buy/sell fills, spread-adjusted backtests) use true
    side-specific prices. When both are supplied, ``price`` must equal
    ``(bid + ask) / 2`` within a small tolerance. When either is None,
    consumers should fall back to ``price`` (mid). Existing callers that
    only pass ``price`` continue to work unchanged.
    """

    price: float
    ts: datetime
    source: str
    bid: float | None = None
    ask: float | None = None

    def __post_init__(self) -> None:
        if self.ts.tzinfo is None:
            raise ValueError(
                f"Quote.ts must be timezone-aware (got naive datetime {self.ts!r}); use UTC."
            )
        # Mixed-populated state is disallowed — both or neither.
        if (self.bid is None) != (self.ask is None):
            raise ValueError(
                f"Quote.bid and Quote.ask must both be set or both be None "
                f"(got bid={self.bid!r}, ask={self.ask!r})."
            )
        # When both populated, price must equal mid within float tolerance.
        # Tolerance 1e-9 covers pip-level rounding (FX pips are 1e-4 or 1e-2).
        if self.bid is not None and self.ask is not None:
            expected_mid = (self.bid + self.ask) / 2.0
            if abs(expected_mid - self.price) > 1e-9:
                raise ValueError(
                    f"Quote.price ({self.price!r}) must equal (bid+ask)/2 "
                    f"({expected_mid!r}); bid={self.bid!r}, ask={self.ask!r}."
                )
            if self.ask < self.bid:
                raise ValueError(f"Quote.ask ({self.ask!r}) must be >= bid ({self.bid!r}).")


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


@runtime_checkable
class QuoteFeed(Protocol):
    """Single-price feed for run_exit_gate / execution_gate (M-3a).

    Migration target for the legacy ``Callable[[str], float]`` price_feed:
    ``Quote`` carries ``ts`` and ``source`` so the gate can apply
    staleness checks (M-3c) without a per-call wrapper.
    """

    def get_quote(self, instrument: str) -> Quote:
        """Return the latest single-price ``Quote`` for *instrument*."""
        ...


def callable_to_quote_feed(
    fn: Callable[[str], float],
    *,
    clock: Clock,
    source: str = SOURCE_LEGACY_CALLABLE,
) -> QuoteFeed:
    """Wrap a legacy ``Callable[[str], float]`` price_feed as a ``QuoteFeed`` (M-3a).

    ts is synthesized from ``clock.now()`` at call time, **not** the true
    observation time of the underlying price — staleness checks against
    this adapter therefore always pass.  This is intentional for the M-3
    migration: existing callers keep their plain-callable contract while
    the consumer side is rewritten against ``QuoteFeed``.
    """

    class _LegacyCallableAdapter:
        def get_quote(self, instrument: str) -> Quote:
            return Quote(price=fn(instrument), ts=clock.now(), source=source)

    return _LegacyCallableAdapter()


# ---------------------------------------------------------------------------
# BarFeed — decision-loop bar-cadence abstraction (Phase 9.1)
# ---------------------------------------------------------------------------


class BarFeed(Protocol):
    """Yields completed OHLCV bars at 1m/5m cadence for the D3 decision loop.

    Phase 1 I-1: sell/buy decisions are made at bar granularity, not tick.
    Concrete implementations:
      - OandaBarFeed: live polling via PriceFeed.get_candles()
      - CandleFileBarFeed: replay from fetch_oanda_candles JSONL

    Contract:
      - Each Candle yielded is *complete* (bar has closed).
      - Candles are yielded in ascending time order.
      - StopIteration when the source is exhausted (replay) or on shutdown.
    """

    def __iter__(self) -> Iterator[Candle]:
        """Yield completed Candles one at a time."""
        ...
