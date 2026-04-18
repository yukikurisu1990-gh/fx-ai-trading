"""Integration smoke test: paper mode 1-cycle end-to-end pipeline (M12).

Verifies the service chain completes without exception:

  FeatureService → MAStrategy → MetaDeciderService
    → ExecutionGateService → PaperBroker.place_order → fill

No database required — PaperBroker is in-memory only.  This test confirms
that the wiring between services is intact; it does not validate business
correctness or profitability of the signal.

Fixture design:
  50 candles at close=1.0, then 20 candles at close=2.0.
  sma_20 ≈ 2.0, sma_50 ≈ 1.40 → strong uptrend → MAStrategy signal='long'.
  MetaDeciderService(min_ev=-1.0) accepts even negative-EV signals so the
  smoke pipeline always reaches PaperBroker regardless of confidence.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fx_ai_trading.adapters.broker.paper import PaperBroker
from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.broker import OrderRequest
from fx_ai_trading.domain.execution import RealtimeContext, TradingIntent
from fx_ai_trading.domain.meta import MetaContext
from fx_ai_trading.domain.strategy import StrategyContext
from fx_ai_trading.services.execution_gate import ExecutionGateService
from fx_ai_trading.services.feature_service import FeatureService
from fx_ai_trading.services.meta_decider import MetaDeciderService
from fx_ai_trading.services.strategies.ma import MAStrategy

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_INSTRUMENT = "EUR_USD"
_ACCOUNT_ID = "smoke-account-001"
_STRATEGY_ID = "smoke-ma-001"
_NOW = datetime(2025, 1, 10, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Fixture helper
# ---------------------------------------------------------------------------


def _make_candles() -> list[dict]:
    """Return 70 fixture candles: 50 at 1.0 then 20 at 2.0.

    All timestamps are strictly before _NOW so FeatureService includes all.
    sma_20 ≈ 2.0 >> sma_50 ≈ 1.40 → MAStrategy emits 'long' with positive divergence.
    """
    base = _NOW - timedelta(hours=71)
    candles: list[dict] = []
    for i in range(50):
        t = base + timedelta(hours=i)
        candles.append(
            {
                "timestamp": t,
                "open": 1.0,
                "high": 1.005,
                "low": 0.995,
                "close": 1.0,
                "volume": 1000.0,
            }
        )
    for i in range(20):
        t = base + timedelta(hours=50 + i)
        candles.append(
            {
                "timestamp": t,
                "open": 2.0,
                "high": 2.005,
                "low": 1.995,
                "close": 2.0,
                "volume": 1000.0,
            }
        )
    return candles


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------


def test_paper_smoke_one_cycle_end_to_end() -> None:
    """Full 1-cycle pipeline reaches PaperBroker fill without exception.

    Assertions:
      1. FeatureService produces a FeatureSet with sma_20 > sma_50.
      2. MAStrategy returns signal='long'.
      3. MetaDeciderService selects the signal (no_trade=False).
      4. ExecutionGateService approves the TradingIntent.
      5. PaperBroker records a filled position for EUR_USD.
    """
    clock = FixedClock(_NOW)
    cycle_id = uuid.uuid4()

    # --- Stage 1: Feature computation ---
    candles = _make_candles()
    feature_svc = FeatureService(get_candles=lambda _inst, _as_of: candles)
    features = feature_svc.build(_INSTRUMENT, "M1", cycle_id, _NOW)

    assert features.feature_stats["sma_20"] > features.feature_stats["sma_50"], (
        f"Fixture did not produce sma_20 > sma_50: {features.feature_stats}"
    )

    # --- Stage 2: Strategy signal ---
    strategy = MAStrategy(strategy_id=_STRATEGY_ID)
    ctx_strategy = StrategyContext(
        cycle_id=cycle_id,
        account_id=_ACCOUNT_ID,
        config_version="smoke-v1",
    )
    signal = strategy.evaluate(_INSTRUMENT, features, ctx_strategy)

    assert signal.signal == "long", f"Expected MAStrategy to emit 'long', got '{signal.signal}'"
    assert signal.sl > 0, "sl must be positive for gate to pass"

    # --- Stage 3: MetaDecider selection ---
    # min_ev=-1.0 ensures smoke reaches broker even when EV is slightly negative.
    meta_svc = MetaDeciderService(min_ev=-1.0)
    ctx_meta = MetaContext(
        cycle_id=cycle_id,
        account_id=_ACCOUNT_ID,
        config_version="smoke-v1",
    )
    decision = meta_svc.decide([signal], ctx_meta)

    assert not decision.no_trade, (
        f"MetaDecider returned no_trade unexpectedly: {decision.no_trade_reasons}"
    )

    # --- Stage 4: ExecutionGate ---
    # signal_created_at = 5 s before NOW → age (5 s) < default TTL (15 s).
    signal_created_at = _NOW - timedelta(seconds=5)
    intent = TradingIntent(
        trading_signal_id=str(uuid.uuid4()),
        order_id=str(uuid.uuid4()),
        account_id=_ACCOUNT_ID,
        instrument=_INSTRUMENT,
        side="buy",
        size_units=1000,
        tp=signal.tp,
        sl=signal.sl,
        signal_created_at=signal_created_at,
        correlation_id=str(cycle_id),
    )
    realtime_ctx = RealtimeContext(
        current_spread=0.00010,
        is_broker_reachable=True,
        checked_at=_NOW,
    )
    gate_svc = ExecutionGateService(clock=clock)
    gate_result = gate_svc.check(intent, realtime_ctx, defer_count=0)

    assert gate_result.decision == "approve", (
        f"ExecutionGate did not approve: decision={gate_result.decision!r},"
        f" reason={gate_result.reason_code!r}"
    )

    # --- Stage 5: PaperBroker fill ---
    broker = PaperBroker(account_type="demo", nominal_price=1.5)
    order_req = OrderRequest(
        client_order_id=intent.order_id,
        account_id=intent.account_id,
        instrument=_INSTRUMENT,
        side="buy",
        size_units=intent.size_units,
        tp=intent.tp,
        sl=intent.sl,
    )
    result = broker.place_order(order_req)

    assert result.status == "filled", f"PaperBroker.place_order returned status={result.status!r}"
    assert result.filled_units == 1000

    positions_after = broker.get_positions(_ACCOUNT_ID)
    assert any(p.instrument == _INSTRUMENT for p in positions_after), (
        f"PaperBroker has no position for {_INSTRUMENT} after fill"
    )
