"""OandaInstrumentRegistry — dynamic instrument list with TTL cache (Phase 9.2).

Phase 1 invariant I-8: the tradeable instrument set MUST be fetched
dynamically from OANDA at runtime.  Hardcoded lists are prohibited
(enforced by CI lint in Phase 9.X-B).

Design:
  - ``list_active()`` returns OANDA's current instrument set filtered to
    tradeable FX pairs (type == "CURRENCY").
  - Results are cached for ``ttl_seconds`` (default 3600 s = 1 h) to
    avoid hammering the API on every cycle.
  - On cache miss (first call or TTL expired): calls
    ``OandaAPIClient.list_account_instruments(account_id)`` and refreshes.
  - Thread safety: single-threaded callers assumed (Tier-A is single-process).
    No lock needed; a racy refresh is benign (worst case: two API calls).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from fx_ai_trading.common.clock import Clock, WallClock

if TYPE_CHECKING:
    from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient

_log = logging.getLogger(__name__)

_DEFAULT_TTL_SECONDS = 3600
_TRADEABLE_TYPE = "CURRENCY"


class OandaInstrumentRegistry:
    """Dynamic instrument registry backed by OANDA account instruments API.

    Args:
        client: ``OandaAPIClient`` instance (handles auth + oandapyV20 calls).
        account_id: OANDA account ID to query.
        ttl_seconds: Cache lifetime in seconds (default 3600).
        instrument_types: Set of OANDA instrument types to include.
            Default: ``{"CURRENCY"}`` (FX pairs only).
    """

    def __init__(
        self,
        client: OandaAPIClient,
        account_id: str,
        *,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        instrument_types: frozenset[str] = frozenset({_TRADEABLE_TYPE}),
        clock: Clock | None = None,
    ) -> None:
        self._client = client
        self._account_id = account_id
        self._ttl_seconds = ttl_seconds
        self._instrument_types = instrument_types
        self._clock: Clock = clock if clock is not None else WallClock()
        self._cached: list[str] = []
        self._cached_at: datetime | None = None

    def list_active(self) -> list[str]:
        """Return current list of tradeable instrument names.

        Fetches from OANDA on first call or when cache has expired.
        Returns instrument names (e.g. ``["EUR_USD", "GBP_USD", ...]``).
        Never returns a hardcoded list (I-8).
        """
        now = self._clock.now()
        if self._cached_at is None or (now - self._cached_at).total_seconds() > self._ttl_seconds:
            self._refresh(now)
        return list(self._cached)

    def invalidate(self) -> None:
        """Force cache invalidation — next ``list_active()`` hits the API."""
        self._cached_at = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _refresh(self, now: datetime) -> None:
        raw = self._client.list_account_instruments(self._account_id)
        instruments = [
            entry["name"]
            for entry in raw
            if entry.get("type") in self._instrument_types and entry.get("tradeable", True)
        ]
        instruments.sort()
        _log.info("OandaInstrumentRegistry refreshed: %d instruments", len(instruments))
        self._cached = instruments
        self._cached_at = now


__all__ = ["OandaInstrumentRegistry"]
