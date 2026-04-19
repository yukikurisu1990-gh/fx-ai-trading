"""Unit tests: TSSCalculator (M20)."""

from __future__ import annotations

import pytest

from fx_ai_trading.services.tss_calculator import TSSCalculator, TSSResult

_CALC = TSSCalculator()


class TestTSSCalculatorBasic:
    def test_returns_none_for_unsupported_instrument(self) -> None:
        result = _CALC.compute("AUDUSD", [{"signal_direction": "buy", "confidence": 0.8}])
        assert result is None

    def test_returns_none_for_empty_signals(self) -> None:
        result = _CALC.compute("USDJPY", [])
        assert result is None

    def test_returns_none_when_all_confidence_zero(self) -> None:
        signals = [{"signal_direction": "buy", "confidence": 0.0}]
        result = _CALC.compute("EURUSD", signals)
        assert result is None

    def test_returns_tss_result_for_valid_signals(self) -> None:
        signals = [{"signal_direction": "buy", "confidence": 0.8}]
        result = _CALC.compute("USDJPY", signals)
        assert isinstance(result, TSSResult)

    def test_score_in_unit_interval(self) -> None:
        signals = [
            {"signal_direction": "buy", "confidence": 0.9},
            {"signal_direction": "buy", "confidence": 0.7},
        ]
        result = _CALC.compute("GBPUSD", signals)
        assert 0.0 <= result.score <= 1.0

    def test_direction_buy_when_buy_dominates(self) -> None:
        signals = [
            {"signal_direction": "buy", "confidence": 0.9},
            {"signal_direction": "sell", "confidence": 0.1},
        ]
        result = _CALC.compute("EURUSD", signals)
        assert result.direction == "buy"

    def test_direction_sell_when_sell_dominates(self) -> None:
        signals = [
            {"signal_direction": "sell", "confidence": 0.8},
            {"signal_direction": "buy", "confidence": 0.2},
        ]
        result = _CALC.compute("USDJPY", signals)
        assert result.direction == "sell"

    def test_horizon_min_is_60(self) -> None:
        signals = [{"signal_direction": "buy", "confidence": 0.5}]
        result = _CALC.compute("GBPUSD", signals)
        assert result.horizon_min == 60

    def test_components_has_two_entries(self) -> None:
        signals = [{"signal_direction": "buy", "confidence": 0.6}]
        result = _CALC.compute("EURUSD", signals)
        assert len(result.components) == 2

    def test_components_contain_confidence_and_direction_strength(self) -> None:
        signals = [{"signal_direction": "buy", "confidence": 0.6}]
        result = _CALC.compute("EURUSD", signals)
        names = {c["name"] for c in result.components}
        assert names == {"confidence", "direction_strength"}

    def test_none_confidence_treated_as_zero(self) -> None:
        signals = [
            {"signal_direction": "buy", "confidence": None},
            {"signal_direction": "buy", "confidence": 0.8},
        ]
        result = _CALC.compute("USDJPY", signals)
        assert result is not None
        assert result.direction == "buy"

    def test_deterministic_same_input(self) -> None:
        signals = [
            {"signal_direction": "buy", "confidence": 0.75},
            {"signal_direction": "sell", "confidence": 0.25},
        ]
        r1 = _CALC.compute("GBPUSD", signals)
        r2 = _CALC.compute("GBPUSD", signals)
        assert r1.score == r2.score
        assert r1.direction == r2.direction

    def test_instruments_set_contains_three(self) -> None:
        assert len(TSSCalculator.INSTRUMENTS) == 3
        assert "USDJPY" in TSSCalculator.INSTRUMENTS
        assert "EURUSD" in TSSCalculator.INSTRUMENTS
        assert "GBPUSD" in TSSCalculator.INSTRUMENTS

    def test_custom_weights_affect_score(self) -> None:
        signals = [{"signal_direction": "buy", "confidence": 0.8}]
        calc_conf = TSSCalculator(weight_confidence=1.0, weight_direction_strength=0.0)
        calc_dir = TSSCalculator(weight_confidence=0.0, weight_direction_strength=1.0)
        r_conf = calc_conf.compute("EURUSD", signals)
        r_dir = calc_dir.compute("EURUSD", signals)
        assert r_conf.score != r_dir.score


class TestTSSCalculatorAllInstruments:
    @pytest.mark.parametrize("instrument", ["USDJPY", "EURUSD", "GBPUSD"])
    def test_all_supported_instruments_return_result(self, instrument: str) -> None:
        signals = [{"signal_direction": "buy", "confidence": 0.7}]
        result = _CALC.compute(instrument, signals)
        assert result is not None
        assert result.score >= 0.0
