"""Unit tests: forward_return and triple_barrier labeling (Phase 9.5)."""

from __future__ import annotations

import pytest

from fx_ai_trading.services.labeling.forward_return import forward_return
from fx_ai_trading.services.labeling.triple_barrier import triple_barrier


class TestForwardReturn:
    def test_basic_positive_return(self) -> None:
        closes = [1.0, 1.0, 1.0, 1.1]
        result = forward_return(closes, horizon=1)
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(0.0)
        assert result[2] == pytest.approx(0.1)
        assert result[3] is None

    def test_last_horizon_entries_are_none(self) -> None:
        closes = [1.0] * 10
        result = forward_return(closes, horizon=3)
        assert all(r is None for r in result[-3:])
        assert all(r is not None for r in result[:-3])

    def test_horizon_equals_length_all_none(self) -> None:
        closes = [1.0, 1.1, 1.2]
        result = forward_return(closes, horizon=3)
        assert result == [None, None, None]

    def test_negative_return(self) -> None:
        closes = [1.1, 1.0]
        result = forward_return(closes, horizon=1)
        assert result[0] == pytest.approx(-1.0 / 11.0)
        assert result[1] is None

    def test_zero_close_returns_none(self) -> None:
        closes = [0.0, 1.0, 1.0]
        result = forward_return(closes, horizon=1)
        assert result[0] is None

    def test_invalid_horizon_raises(self) -> None:
        with pytest.raises(ValueError, match="horizon must be positive"):
            forward_return([1.0, 2.0], horizon=0)

    def test_empty_list(self) -> None:
        assert forward_return([], horizon=5) == []

    def test_single_element_all_none(self) -> None:
        assert forward_return([1.0], horizon=1) == [None]

    def test_horizon_12_length_invariant(self) -> None:
        # 20 elements, horizon=12 → None from index 8 (= 20-12) onward.
        closes = [float(i) for i in range(1, 21)]
        result = forward_return(closes, horizon=12)
        assert len(result) == len(closes)
        assert result[-13] is not None  # index 7: 7+12=19 < 20
        assert result[-12] is None  # index 8: 8+12=20 == n
        assert result[-1] is None


class TestTripleBarrier:
    def test_tp_hit_first(self) -> None:
        # Entry=1.0, TP at 1.001 (+10 pips), SL at 0.999 (-10 pips)
        closes = [1.0, 1.0, 1.001, 0.999]
        result = triple_barrier(closes, horizon=3, tp_pips=10, sl_pips=10)
        assert result[0] == 1

    def test_sl_hit_first(self) -> None:
        closes = [1.0, 1.0, 0.999, 1.001]
        result = triple_barrier(closes, horizon=3, tp_pips=10, sl_pips=10)
        assert result[0] == -1

    def test_timeout_label_zero(self) -> None:
        # Price stays flat — neither barrier touched
        closes = [1.0, 1.0, 1.0, 1.0, 1.0]
        result = triple_barrier(closes, horizon=3, tp_pips=10, sl_pips=10)
        assert result[0] == 0
        assert result[1] == 0

    def test_last_horizon_entries_are_none(self) -> None:
        closes = [1.0] * 10
        result = triple_barrier(closes, horizon=3, tp_pips=10, sl_pips=10)
        assert all(r is None for r in result[-3:])
        assert all(r is not None for r in result[:-3])

    def test_tp_boundary_exact(self) -> None:
        # TP is exactly at entry + 10 * 0.0001 = 1.0 + 0.001
        closes = [1.0, 1.001]
        result = triple_barrier(closes, horizon=1, tp_pips=10, sl_pips=10)
        assert result[0] == 1

    def test_sl_boundary_exact(self) -> None:
        closes = [1.0, 0.999]
        result = triple_barrier(closes, horizon=1, tp_pips=10, sl_pips=10)
        assert result[0] == -1

    def test_custom_pip_size(self) -> None:
        # JPY pairs: pip_size=0.01, TP=50 pips = 0.50
        closes = [150.0, 150.50]
        result = triple_barrier(closes, horizon=1, tp_pips=50, sl_pips=50, pip_size=0.01)
        assert result[0] == 1

    def test_invalid_horizon_raises(self) -> None:
        with pytest.raises(ValueError, match="horizon must be positive"):
            triple_barrier([1.0, 2.0], horizon=0, tp_pips=10, sl_pips=10)

    def test_invalid_tp_raises(self) -> None:
        with pytest.raises(ValueError, match="tp_pips and sl_pips must be positive"):
            triple_barrier([1.0, 2.0], horizon=1, tp_pips=0, sl_pips=10)

    def test_empty_list(self) -> None:
        assert triple_barrier([], horizon=1, tp_pips=10, sl_pips=10) == []

    def test_length_invariant(self) -> None:
        closes = [float(i) / 100 + 1.0 for i in range(20)]
        result = triple_barrier(closes, horizon=5, tp_pips=10, sl_pips=10)
        assert len(result) == len(closes)

    def test_tp_wins_over_timeout_with_sufficient_bars(self) -> None:
        # Bar 0 entry=1.0; bars 1–3 flat; bar 4 hits TP
        closes = [1.0, 1.0, 1.0, 1.0, 1.001, 1.0]
        result = triple_barrier(closes, horizon=5, tp_pips=10, sl_pips=10)
        assert result[0] == 1

    def test_sl_wins_over_timeout_with_sufficient_bars(self) -> None:
        closes = [1.0, 1.0, 1.0, 1.0, 0.999, 1.0]
        result = triple_barrier(closes, horizon=5, tp_pips=10, sl_pips=10)
        assert result[0] == -1
