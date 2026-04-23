"""Unit tests for the entry-side ``quote_feed`` wiring used by the
evaluation runner.

Background
----------
PR #153 wired ``PaperBroker`` to read fill prices from a ``QuoteFeed``
when one is injected, but the evaluation runner
(``scripts/run_paper_evaluation.py``) constructs the entry-side broker
via ``run_paper_entry_loop.build_components`` — which historically did
not forward a feed.  Result: entry fills always landed at the legacy
``nominal_price=1.0``, while exit fills used the real OANDA quote, so
``pnl_realized`` carried a constant ``(quote − 1.0) × units`` artefact
bias that wiped out any strategy-vs-strategy signal.

This test pins the **wiring contract** that fixes that artefact:

1. ``build_components(quote_feed=feed)`` must reach the broker — i.e.
   the open-leg fill price is what the feed returned, not the
   ``nominal_price=1.0`` fallback.
2. ``build_supervisor_with_paper_stack(quote_feed=feed)`` must accept
   an external feed and use it for the exit-side broker (so the same
   instance can be shared between entry and exit, eliminating the
   feed-source divergence the bias relied on).

We do not re-test the M-2 PnL formula here — that is covered by
``tests/unit/test_paper_broker_quote_feed.py`` from PR #153.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.broker import OrderRequest
from fx_ai_trading.domain.price_feed import Quote

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"

_FIXED_TS = datetime(2026, 4, 23, 13, 0, 0, tzinfo=UTC)
_ACCOUNT_ID = "acct-test"
_INSTRUMENT = "EUR_USD"


def _load_sibling(filename: str, alias: str) -> Any:
    if alias in sys.modules:
        return sys.modules[alias]
    spec = importlib.util.spec_from_file_location(alias, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


def _entry_lib() -> Any:
    return _load_sibling("run_paper_entry_loop.py", "_entry_lib_under_quote_wiring_test")


def _exit_lib() -> Any:
    return _load_sibling("run_paper_loop.py", "_exit_lib_under_quote_wiring_test")


class _ScriptedQuoteFeed:
    """Returns scripted prices in order; records every call."""

    def __init__(self, prices: list[float]) -> None:
        self._prices = list(prices)
        self.calls: list[str] = []

    def get_quote(self, instrument: str) -> Quote:
        self.calls.append(instrument)
        price = self._prices.pop(0)
        return Quote(price=price, ts=_FIXED_TS, source="test")


def _make_oanda_config() -> Any:
    entry = _entry_lib()
    return entry.OandaConfig(
        access_token="dummy-token",
        account_id="dummy-account",
        environment="practice",
    )


def test_build_components_passes_external_feed_to_paper_broker() -> None:
    """``build_components(quote_feed=feed)`` → broker reads from that feed.

    Verifies the entry-side fill price is no longer the
    ``nominal_price=1.0`` fallback when a feed is injected.  Without
    this wiring the evaluation runner would still emit
    ``open_px=1.00000000`` for every position even after PR #153.
    """
    entry = _entry_lib()

    feed = _ScriptedQuoteFeed(prices=[1.16500])
    engine = create_engine("sqlite:///:memory:")

    components = entry.build_components(
        oanda=_make_oanda_config(),
        engine=engine,
        account_id=_ACCOUNT_ID,
        clock=FixedClock(_FIXED_TS),
        quote_feed=feed,
    )

    assert components.quote_feed is feed

    request = OrderRequest(
        client_order_id="o-1",
        account_id=_ACCOUNT_ID,
        instrument=_INSTRUMENT,
        side="long",
        size_units=1000,
    )
    result = components.broker.place_order(request)

    assert result.fill_price == 1.16500
    assert result.fill_price != 1.0
    assert feed.calls == [_INSTRUMENT]


def test_build_supervisor_with_paper_stack_accepts_external_feed() -> None:
    """``build_supervisor_with_paper_stack(quote_feed=feed)`` shares the
    same feed instance across entry and exit sides when the eval runner
    constructs the supervisor with ``components.quote_feed``.

    A shared feed instance is the wiring guarantee that lets
    ``run_paper_evaluation`` produce comparable PnL across strategies —
    entry-leg ``avg_price`` and exit-leg ``fill_price`` come from the
    same source instead of two independent OANDA polls.
    """
    exit_lib = _exit_lib()

    feed = _ScriptedQuoteFeed(prices=[1.16500])  # not consumed in this test
    engine = create_engine("sqlite:///:memory:")

    supervisor, returned_feed = exit_lib.build_supervisor_with_paper_stack(
        oanda=_make_oanda_config(),
        instrument=_INSTRUMENT,
        engine=engine,
        account_id=_ACCOUNT_ID,
        clock=FixedClock(_FIXED_TS),
        quote_feed=feed,
    )

    assert returned_feed is feed
    # The exit-side broker stored on the gate must reference the same
    # feed object — sharing is the whole point of the param.
    exit_gate = supervisor._exit_gate  # type: ignore[attr-defined]
    assert exit_gate.broker._quote_feed is feed  # type: ignore[union-attr]
