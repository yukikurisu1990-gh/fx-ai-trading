"""Integration smoke test: paper mode 1-cycle end-to-end pipeline (M12 / M25).

Verifies the full 7-stage service chain:

  Stage 1: FeatureService → features
  Stage 2: MAStrategy → signal='long'
  Stage 3: MetaDeciderService → decision (no_trade=False)
  Stage 4: ExecutionGateService → approve
  Stage 5: PaperBroker.place_order → filled
  Stage 6: ExitPolicyService.evaluate → should_exit=True (SL breach)  [M25]
  Stage 7: run_exit_gate → outcome='closed' + StateManager.on_close    [M25 / H-3c]

Stage 7 was migrated from the deprecated ``ExitExecutor`` path to
``run_exit_gate`` in M9/H-3c so the smoke pipeline exercises the
post-Cycle-6.7d (I-09) write path that delegates DB writes to
``StateManager.on_close``.  ``ExitExecutor`` itself was subsequently
removed in M9/H-3c (final PR); this file no longer imports it.

StateManager is mocked in Stage 7: the append-only write-path contract
is covered separately by ``tests/integration/test_state_manager*``.
What the smoke test pins here is that the 7-stage pipeline reaches the
close path and invokes the on_close write exactly once with the SL
primary_reason — the ``run_exit_gate`` analogue of the previous
"close_events row recorded" check.

Fixture design:
  50 candles at close=1.0, then 20 candles at close=2.0.
  sma_20 ≈ 2.0, sma_50 ≈ 1.40 → strong uptrend → MAStrategy signal='long'.
  MetaDeciderService(min_ev=-1.0) accepts even negative-EV signals so the
  smoke pipeline always reaches PaperBroker regardless of confidence.

  SL breach in Stage 6/7: set sl=3.0 (above fill price=1.5 for a 'long')
  so that current_price=1.0 < sl=3.0 triggers the SL rule.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from fx_ai_trading.adapters.broker.paper import PaperBroker
from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.broker import OrderRequest
from fx_ai_trading.domain.execution import RealtimeContext, TradingIntent
from fx_ai_trading.domain.meta import MetaContext
from fx_ai_trading.domain.state import OpenPositionInfo
from fx_ai_trading.domain.strategy import StrategyContext
from fx_ai_trading.services.execution_gate import ExecutionGateService
from fx_ai_trading.services.exit_gate_runner import run_exit_gate
from fx_ai_trading.services.exit_policy import ExitPolicyService
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
    """Full 1-cycle pipeline reaches PaperBroker fill and run_exit_gate close
    without exception.

    Assertions:
      1. FeatureService produces a FeatureSet with sma_20 > sma_50.
      2. MAStrategy returns signal='long'.
      3. MetaDeciderService selects the signal (no_trade=False).
      4. ExecutionGateService approves the TradingIntent.
      5. PaperBroker records a filled position for EUR_USD.
      6. ExitPolicyService fires on SL breach (primary_reason='sl').
      7. run_exit_gate returns one ExitGateRunResult(outcome='closed',
         primary_reason='sl') and invokes StateManager.on_close exactly
         once for the just-filled position.
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

    # --- Stage 6: ExitPolicy evaluation — SL breach ---
    # SL = 3.0 (above fill price 1.5 for 'long'), current_price = 1.0 → breach.
    # Kept as an explicit sanity check so a break in policy-rule logic is
    # distinguishable from a break in the gate/state-manager wiring below.
    exit_svc = ExitPolicyService()
    exit_decision = exit_svc.evaluate(
        position_id="smoke-pos-001",
        instrument=_INSTRUMENT,
        side="long",
        current_price=1.0,
        tp=5.0,
        sl=3.0,
        holding_seconds=60,
        context={},
    )

    assert exit_decision.should_exit, (
        f"ExitPolicyService did not trigger on SL breach: {exit_decision}"
    )
    assert exit_decision.primary_reason == "sl", (
        f"Expected primary_reason='sl', got {exit_decision.primary_reason!r}"
    )

    # --- Stage 7: run_exit_gate — close routed through StateManager.on_close ---
    # ``run_exit_gate`` reads the position from StateManager.open_position_details
    # (unlike the deprecated ExitExecutor which took position metadata as call
    # arguments), so we seed a mock StateManager with the just-filled position.
    # The append-only write-path contract itself lives in
    # tests/integration/test_state_manager*; here we only pin the smoke
    # property "the pipeline reaches the close write exactly once".
    state_manager = MagicMock(name="state_manager")
    state_manager.open_position_details.return_value = [
        OpenPositionInfo(
            instrument=_INSTRUMENT,
            order_id=intent.order_id,
            units=1000,
            avg_price=1.5,  # PaperBroker fill price
            open_time_utc=_NOW - timedelta(seconds=60),  # holding_seconds=60
            side="long",  # M-1a: derived from orders.direction='buy' in production
        )
    ]
    state_manager.on_close.return_value = ("smoke-snapshot-id", "smoke-close-event-id")

    results = run_exit_gate(
        broker=broker,
        account_id=_ACCOUNT_ID,
        clock=clock,
        state_manager=state_manager,
        exit_policy=exit_svc,
        quote_feed=lambda _instrument: 1.0,  # SL breach: 1.0 < sl=3.0
        tp=5.0,
        sl=3.0,
    )

    assert len(results) == 1, f"run_exit_gate returned {len(results)} results, expected 1"
    assert results[0].outcome == "closed", f"Expected outcome='closed', got {results[0].outcome!r}"
    assert results[0].primary_reason == "sl", (
        f"Expected primary_reason='sl', got {results[0].primary_reason!r}"
    )

    # StateManager.on_close MUST have been invoked exactly once — the
    # run_exit_gate analogue of the deprecated path's "close_events row
    # recorded" assertion.
    state_manager.on_close.assert_called_once()
    on_close_kwargs = state_manager.on_close.call_args.kwargs
    assert on_close_kwargs["order_id"] == intent.order_id
    assert on_close_kwargs["instrument"] == _INSTRUMENT
    assert on_close_kwargs["primary_reason_code"] == "sl"
    reason_codes = {r["reason_code"] for r in on_close_kwargs["reasons"]}
    assert "sl" in reason_codes
