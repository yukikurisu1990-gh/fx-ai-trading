"""Unit tests: CurrencyStrengthIndex classical CSI + z-score (Phase 9.3)."""

from __future__ import annotations

import math

import pytest

from fx_ai_trading.services.currency_strength import CurrencyStrengthIndex


@pytest.fixture()
def csi() -> CurrencyStrengthIndex:
    return CurrencyStrengthIndex()


class TestCurrencyStrengthIndexBasic:
    def test_empty_input_returns_empty(self, csi: CurrencyStrengthIndex) -> None:
        assert csi.compute({}) == {}

    def test_single_pair_all_zeros(self, csi: CurrencyStrengthIndex) -> None:
        # Only 1 pair → 2 currencies, but stdev of 2 mirrored values may be non-zero.
        # EUR gets +ret, USD gets -ret → raw differs → z-score ±1.
        result = csi.compute({"EUR_USD": 0.001})
        assert set(result) == {"EUR", "USD"}
        # Z-scores should sum to 0 and have equal magnitude.
        assert abs(sum(result.values())) < 1e-10
        assert result["EUR"] > 0  # EUR was base (positive return) → stronger
        assert result["USD"] < 0  # USD was quote (negative return) → weaker

    def test_skips_non_pair_keys(self, csi: CurrencyStrengthIndex) -> None:
        result = csi.compute({"BTCUSD": 0.01, "EUR_USD": 0.001})
        assert "BTCUSD" not in result

    def test_output_z_score_mean_zero(self, csi: CurrencyStrengthIndex) -> None:
        pair_returns = {
            "EUR_USD": 0.002,
            "GBP_USD": -0.001,
            "EUR_GBP": 0.003,
            "USD_JPY": 0.0015,
        }
        result = csi.compute(pair_returns)
        total = sum(result.values())
        assert abs(total) < 1e-9, f"mean should be ~0, got sum={total}"

    def test_output_z_score_unit_variance(self, csi: CurrencyStrengthIndex) -> None:
        pair_returns = {
            "EUR_USD": 0.002,
            "GBP_USD": -0.001,
            "EUR_GBP": 0.003,
            "USD_JPY": 0.0015,
        }
        result = csi.compute(pair_returns)
        vals = list(result.values())
        variance = sum((v - sum(vals) / len(vals)) ** 2 for v in vals) / (len(vals) - 1)
        assert abs(math.sqrt(variance) - 1.0) < 1e-9

    def test_zero_returns_all_zero(self, csi: CurrencyStrengthIndex) -> None:
        # All returns are 0 → raw CSI all 0 → z-scores all 0.
        pair_returns = {"EUR_USD": 0.0, "GBP_USD": 0.0, "EUR_GBP": 0.0}
        result = csi.compute(pair_returns)
        for v in result.values():
            assert v == pytest.approx(0.0)


class TestCurrencyStrengthIndexRanking:
    def test_strong_base_currency_ranks_highest(self, csi: CurrencyStrengthIndex) -> None:
        # EUR rising against both USD and GBP → EUR should be strongest.
        pair_returns = {
            "EUR_USD": 0.005,
            "EUR_GBP": 0.004,
            "GBP_USD": 0.001,
        }
        result = csi.compute(pair_returns)
        assert result["EUR"] == max(result.values())

    def test_weak_quote_currency_ranks_lowest(self, csi: CurrencyStrengthIndex) -> None:
        # USD falling against EUR and GBP → USD should be weakest.
        pair_returns = {
            "EUR_USD": 0.005,
            "GBP_USD": 0.003,
            "EUR_GBP": 0.002,
        }
        result = csi.compute(pair_returns)
        assert result["USD"] == min(result.values())

    def test_deterministic_output(self, csi: CurrencyStrengthIndex) -> None:
        pair_returns = {"EUR_USD": 0.002, "GBP_USD": -0.001, "EUR_GBP": 0.003}
        r1 = csi.compute(pair_returns)
        r2 = csi.compute(pair_returns)
        assert r1 == r2


class TestCurrencyStrengthIndexEdgeCases:
    def test_fewer_than_two_currencies_returns_zeros(self, csi: CurrencyStrengthIndex) -> None:
        # Single currency pair "AAA_AAA" → only AAA → 1 currency → z-score undefined.
        result = csi.compute({"AAA_AAA": 0.001})
        # Only 1 currency → _zscore returns 0.0 for it.
        assert result == {"AAA": 0.0}

    def test_currencies_with_no_base_pairs_get_zero_base_avg(
        self, csi: CurrencyStrengthIndex
    ) -> None:
        # JPY only appears as quote → base_avg = 0.
        pair_returns = {"EUR_JPY": 0.003, "USD_JPY": 0.002}
        result = csi.compute(pair_returns)
        assert "JPY" in result
        assert "EUR" in result
        assert "USD" in result
