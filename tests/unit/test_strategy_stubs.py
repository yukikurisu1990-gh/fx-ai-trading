"""Unit tests for Cycle 6.3 Strategy stubs.

Verifies:
  - Both stubs satisfy the StrategyEvaluator Protocol shape
    (duck-typed — no runtime_checkable decorator on the Protocol).
  - AlwaysNoTradeStrategy always returns 'no_trade'.
  - DeterministicTrendStrategy always returns 'long' or 'short' and
    never 'no_trade' — this is the Cycle 6.4 guarantee.
  - DeterministicTrendStrategy's direction is deterministic per
    (cycle_id, instrument).
  - All StrategySignal fields are populated (no None values for
    required numeric / str / int fields) — Cycle 6.3 explicit
    requirement ("StrategyOutput の値は必ず埋める").
"""

from __future__ import annotations

from datetime import UTC, datetime

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext, StrategySignal
from fx_ai_trading.strategies import (
    AlwaysNoTradeStrategy,
    DeterministicTrendStrategy,
)


def _dummy_features() -> FeatureSet:
    return FeatureSet(
        feature_version="stub.v1",
        feature_hash="deadbeef",
        feature_stats={"n": 0},
        sampled_features={},
        computed_at=datetime(2026, 4, 20, tzinfo=UTC),
    )


def _ctx(cycle_id: str = "cyc-0001") -> StrategyContext:
    return StrategyContext(
        cycle_id=cycle_id,
        account_id="acc-1",
        config_version="cv-1",
    )


class TestAlwaysNoTradeStrategy:
    def test_returns_no_trade(self) -> None:
        s = AlwaysNoTradeStrategy()
        r = s.evaluate("EURUSD", _dummy_features(), _ctx())
        assert r.signal == "no_trade"

    def test_all_fields_populated(self) -> None:
        s = AlwaysNoTradeStrategy()
        r = s.evaluate("EURUSD", _dummy_features(), _ctx())
        # Every StrategySignal field must be a concrete value, not None.
        assert r.strategy_id
        assert r.strategy_type
        assert r.strategy_version
        assert r.confidence == 0.0
        assert r.ev_before_cost == 0.0
        assert r.ev_after_cost == 0.0
        assert r.tp == 0.0
        assert r.sl == 0.0
        assert r.holding_time_seconds == 0
        assert r.enabled is True

    def test_deterministic_across_invocations(self) -> None:
        s = AlwaysNoTradeStrategy()
        a = s.evaluate("EURUSD", _dummy_features(), _ctx("cyc-A"))
        b = s.evaluate("EURUSD", _dummy_features(), _ctx("cyc-A"))
        assert a == b


class TestDeterministicTrendStrategy:
    def test_never_returns_no_trade(self) -> None:
        """Cycle 6.4 guarantee: this stub ALWAYS emits a trade direction."""
        s = DeterministicTrendStrategy()
        seen = set()
        for cyc in [f"cyc-{i}" for i in range(20)]:
            for inst in ["EURUSD", "USDJPY", "GBPUSD"]:
                r = s.evaluate(inst, _dummy_features(), _ctx(cyc))
                assert r.signal in {"long", "short"}
                seen.add(r.signal)
        # Sanity: across many inputs, both directions should occur.
        # If the hash happens to be badly skewed this still has
        # probability ~1 - 2^-60 to fail, so effectively impossible.
        assert seen == {"long", "short"}

    def test_direction_is_deterministic(self) -> None:
        s = DeterministicTrendStrategy()
        a = s.evaluate("EURUSD", _dummy_features(), _ctx("cyc-stable"))
        b = s.evaluate("EURUSD", _dummy_features(), _ctx("cyc-stable"))
        assert a.signal == b.signal

    def test_different_cycles_can_flip_direction(self) -> None:
        """If direction were fixed regardless of cycle_id, Cycle 6.4
        testability would suffer — this test ensures the stub varies."""
        s = DeterministicTrendStrategy()
        observed = {
            s.evaluate("EURUSD", _dummy_features(), _ctx(f"cyc-{i}")).signal for i in range(50)
        }
        assert observed == {"long", "short"}

    def test_all_numeric_fields_populated(self) -> None:
        s = DeterministicTrendStrategy()
        r = s.evaluate("EURUSD", _dummy_features(), _ctx())
        # Must all be concrete numbers usable by Meta.
        assert r.confidence == 0.70
        assert r.ev_before_cost == 15.0
        assert r.ev_after_cost == 12.0
        assert r.tp == 20.0
        assert r.sl == 10.0
        assert r.holding_time_seconds == 3600
        assert r.enabled is True

    def test_confidence_is_above_plausible_meta_threshold(self) -> None:
        """The 0.70 confidence is load-bearing for the Cycle 6.4 guarantee:
        Meta can set any threshold up to 0.70 and at least 1 trade
        still survives."""
        s = DeterministicTrendStrategy()
        r = s.evaluate("EURUSD", _dummy_features(), _ctx())
        assert r.confidence >= 0.70

    def test_returns_strategy_signal_instance(self) -> None:
        s = DeterministicTrendStrategy()
        r = s.evaluate("EURUSD", _dummy_features(), _ctx())
        assert isinstance(r, StrategySignal)

    def test_strategy_id_and_type_constants(self) -> None:
        s = DeterministicTrendStrategy()
        r = s.evaluate("EURUSD", _dummy_features(), _ctx())
        assert r.strategy_id == "stub.deterministic_trend.v1"
        assert r.strategy_type == "stub"
        assert r.strategy_version == "1.0.0"


class TestProtocolShape:
    """Lightweight duck-typing check — the Protocol is not
    ``@runtime_checkable`` in this repo so we rely on attribute
    presence."""

    def test_stubs_expose_evaluate(self) -> None:
        assert callable(AlwaysNoTradeStrategy().evaluate)
        assert callable(DeterministicTrendStrategy().evaluate)
