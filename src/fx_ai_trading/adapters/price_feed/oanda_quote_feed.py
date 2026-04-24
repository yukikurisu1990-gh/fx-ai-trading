"""OandaQuoteFeed — QuoteFeed implementation backed by OANDA REST pricing (M-3d).

Polling-only producer.  Each ``get_quote()`` makes one synchronous
``PricingInfo`` call via ``OandaAPIClient`` and returns a ``Quote`` whose:

  - ``price``  — mid = (best bid + best ask) / 2
  - ``ts``     — parsed from OANDA's ``time`` field (the authoritative
                 observation timestamp).  **Not** ``clock.now()``: the
                 M-3c staleness gate must compare against the real
                 observation time, not the moment we polled.
  - ``source`` — ``SOURCE_OANDA_REST_SNAPSHOT`` by default (REST polling
                 returns a snapshot, not a stream).

Streaming (``subscribe_price_stream``) is intentionally out of scope for
M-3d; if/when streaming is needed it lands as a separate producer in a
later PR.

This producer makes no changes to ``run_exit_gate``, ``Supervisor``, or
the SafeStop wiring.  Wiring it into the supervisor's ``attach_exit_gate``
call is a separate concern and lives in a follow-up PR.

Account-type safety: the underlying ``OandaAPIClient`` is environment-
scoped (``practice`` or ``live``).  This producer does not enforce
demo / live matching — that responsibility stays in ``OandaBroker``
(Decision 2.6.1-1) and is unrelated to read-only pricing.

Retry policy: ``OandaAPIClient`` does not auto-retry; ``V20Error`` /
``OandaQuoteFeedError`` propagate to the caller.  The M-3c staleness
gate already provides the operational fallback when pricing is briefly
unavailable (the next tick re-attempts).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Final

from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
from fx_ai_trading.domain.price_feed import (
    SOURCE_OANDA_REST_SNAPSHOT,
    Quote,
)

_DEFAULT_SOURCE: Final[str] = SOURCE_OANDA_REST_SNAPSHOT


class OandaQuoteFeedError(RuntimeError):
    """Raised when an OANDA pricing response is missing required fields.

    Distinct from ``oandapyV20.exceptions.V20Error`` (transport / HTTP
    failures): this exception is for *parse* failures where OANDA
    returned a 200 OK whose body is not shaped as documented.  Treat
    both equivalently at the call site (skip / retry next tick) — they
    are split only for triage clarity.
    """


class OandaQuoteFeed:
    """``QuoteFeed`` implementation backed by OANDA REST pricing (M-3d).

    Implements the ``QuoteFeed`` Protocol from
    ``fx_ai_trading.domain.price_feed``.  No explicit base class
    inheritance — the Protocol is ``@runtime_checkable`` and
    ``isinstance(feed, QuoteFeed)`` succeeds for any object with a
    ``get_quote(instrument: str) -> Quote`` method.
    """

    def __init__(
        self,
        *,
        api_client: OandaAPIClient,
        account_id: str,
        source: str = _DEFAULT_SOURCE,
    ) -> None:
        self._api = api_client
        self._account_id = account_id
        self._source = source

    @property
    def source(self) -> str:
        return self._source

    def get_quote(self, instrument: str) -> Quote:
        prices = self._api.get_pricing(self._account_id, [instrument])
        if not prices:
            raise OandaQuoteFeedError(
                f"OANDA returned no pricing entry for instrument={instrument!r}"
            )
        entry = prices[0]
        bid = self._first_price(entry.get("bids"), side="bid", instrument=instrument)
        ask = self._first_price(entry.get("asks"), side="ask", instrument=instrument)
        ts = self._parse_time(entry.get("time"), instrument=instrument)
        # Phase 9.10: populate bid/ask so cost-aware consumers (PaperBroker)
        # can use side-specific prices. price stays as mid for backward compat.
        return Quote(
            price=(bid + ask) / 2.0,
            ts=ts,
            source=self._source,
            bid=bid,
            ask=ask,
        )

    @staticmethod
    def _first_price(
        entries: list[dict[str, Any]] | None,
        *,
        side: str,
        instrument: str,
    ) -> float:
        if not entries:
            raise OandaQuoteFeedError(
                f"OANDA pricing entry for instrument={instrument!r} missing {side!r} side"
            )
        raw = entries[0].get("price")
        if raw is None:
            raise OandaQuoteFeedError(
                f"OANDA pricing entry for instrument={instrument!r} {side!r}[0] missing 'price'"
            )
        return float(raw)

    @staticmethod
    def _parse_time(time_str: str | None, *, instrument: str) -> datetime:
        if not time_str:
            raise OandaQuoteFeedError(
                f"OANDA pricing entry for instrument={instrument!r} missing 'time'"
            )
        # OANDA timestamps are RFC3339 with up to 9 fractional digits and a
        # trailing 'Z'.  fromisoformat (3.11+) accepts the digit count and
        # +00:00 form; replace 'Z' before parsing to stay consistent with
        # the broker adapter's existing convention (oanda.py:_parse_transaction).
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
