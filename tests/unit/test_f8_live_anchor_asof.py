"""Unit tests: F8-C live barrier anchor + F8-D live feature as-of alignment.

Audit context: docs/design/project_wide_logic_audit_fable5_findings.md §4 F-8.

- F8-C (F8_LIVE_BARRIER_ANCHOR_ALIGNED): contract TP/SL barriers must anchor
  at the ACTUAL entry fill price recorded by on_fill, never silently at the
  decision-bar mid close; missing fill/ATR fails closed (no price barriers).
- F8-D (F8_FEATURE_ASOF_CONTRACT_ALIGNED): feature as-of must be the
  decision-bar CLOSE time so the just-completed decision bar survives
  FeatureService's strict ``timestamp < as_of_time`` filter, matching the
  training/backtest feature lag.

Synthetic values only. The runner script is importlib-loaded like the
existing arg tests.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest

_RUNNER_PATH = (
    __import__("pathlib").Path(__file__).resolve().parents[2]
    / "scripts"
    / "run_paper_decision_loop.py"
)
_spec = importlib.util.spec_from_file_location("paper_decision_runner_f8", _RUNNER_PATH)
runner = importlib.util.module_from_spec(_spec)
sys.modules["paper_decision_runner_f8"] = runner
assert _spec.loader is not None
_spec.loader.exec_module(runner)

_SRC = _RUNNER_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# F8-C: _barrier_prices — anchored at fill price
# ---------------------------------------------------------------------------


class TestBarrierPricesAnchor:
    def test_buy_anchored_at_fill_price(self) -> None:
        result = runner._barrier_prices(fill_price=1.1000, atr=0.0020, price_dp=5, direction="buy")
        assert result is not None
        tp, sl = result
        assert tp == pytest.approx(1.1030)  # fill + 1.5 * atr
        assert sl == pytest.approx(1.0980)  # fill - 1.0 * atr

    def test_sell_anchored_at_fill_price(self) -> None:
        result = runner._barrier_prices(fill_price=1.1000, atr=0.0020, price_dp=5, direction="sell")
        assert result is not None
        tp, sl = result
        assert tp == pytest.approx(1.0970)  # fill - 1.5 * atr
        assert sl == pytest.approx(1.1020)  # fill + 1.0 * atr

    def test_anchor_is_fill_not_decision_bar_mid(self) -> None:
        """A fill above the decision-bar mid must shift both barriers with it."""
        mid_close = 1.1000
        fill = 1.10012  # e.g. next-tick ask for a long
        atr = 0.0020
        result = runner._barrier_prices(fill_price=fill, atr=atr, price_dp=5, direction="buy")
        assert result is not None
        tp, sl = result
        assert tp == pytest.approx(round(fill + 1.5 * atr, 5))
        assert sl == pytest.approx(round(fill - 1.0 * atr, 5))
        # Explicitly NOT the mid-anchored levels.
        assert tp != pytest.approx(round(mid_close + 1.5 * atr, 5))
        assert sl != pytest.approx(round(mid_close - 1.0 * atr, 5))

    def test_jpy_precision_3dp(self) -> None:
        result = runner._barrier_prices(fill_price=155.123, atr=0.050, price_dp=3, direction="buy")
        assert result is not None
        tp, sl = result
        assert tp == pytest.approx(155.198)
        assert sl == pytest.approx(155.073)
        # Rounded to 3 decimal places exactly.
        assert tp == round(tp, 3)
        assert sl == round(sl, 3)

    def test_custom_multipliers(self) -> None:
        result = runner._barrier_prices(
            fill_price=1.2000, atr=0.0010, price_dp=5, direction="sell", tp_mult=2.0, sl_mult=0.5
        )
        assert result is not None
        tp, sl = result
        assert tp == pytest.approx(1.1980)
        assert sl == pytest.approx(1.2005)

    def test_default_multipliers_match_b2_constants(self) -> None:
        result = runner._barrier_prices(fill_price=1.0, atr=0.01, price_dp=5, direction="buy")
        assert result is not None
        tp, sl = result
        assert tp == pytest.approx(1.0 + runner._TP_MULT * 0.01)
        assert sl == pytest.approx(1.0 - runner._SL_MULT * 0.01)


class TestBarrierPricesFailClosed:
    @pytest.mark.parametrize(
        ("fill_price", "atr"),
        [
            (None, 0.0020),
            (1.1000, None),
            (None, None),
            (float("nan"), 0.0020),
            (1.1000, float("nan")),
            (float("inf"), 0.0020),
            (1.1000, float("inf")),
            (1.1000, 0.0),
            (1.1000, -0.0020),
            (0.0, 0.0020),
            (-1.1000, 0.0020),
        ],
    )
    def test_missing_or_nonfinite_inputs_return_none(self, fill_price, atr) -> None:
        assert (
            runner._barrier_prices(fill_price=fill_price, atr=atr, price_dp=5, direction="buy")
            is None
        )

    @pytest.mark.parametrize("direction", ["", "hold", "long", "BUY", "unknown"])
    def test_unknown_direction_returns_none(self, direction: str) -> None:
        assert (
            runner._barrier_prices(fill_price=1.1000, atr=0.0020, price_dp=5, direction=direction)
            is None
        )

    def test_docstring_cites_f8_contract(self) -> None:
        assert "F8_LIVE_BARRIER_ANCHOR_ALIGNED" in (runner._barrier_prices.__doc__ or "")


class TestRecordedFillPrice:
    def test_returns_avg_price_for_matching_order(self) -> None:
        sm = SimpleNamespace(
            open_position_details=lambda: [
                SimpleNamespace(order_id="other", avg_price=9.99),
                SimpleNamespace(order_id="ord1", avg_price=1.10012),
            ]
        )
        assert runner._recorded_fill_price(sm, "ord1") == pytest.approx(1.10012)

    def test_missing_order_returns_none(self) -> None:
        sm = SimpleNamespace(open_position_details=lambda: [])
        assert runner._recorded_fill_price(sm, "ord1") is None

    def test_read_failure_returns_none(self) -> None:
        def _boom():
            raise RuntimeError("db down")

        sm = SimpleNamespace(open_position_details=_boom)
        assert runner._recorded_fill_price(sm, "ord1") is None

    def test_nan_avg_price_fails_closed_via_barrier_prices(self) -> None:
        sm = SimpleNamespace(
            open_position_details=lambda: [SimpleNamespace(order_id="ord1", avg_price=float("nan"))]
        )
        fill = runner._recorded_fill_price(sm, "ord1")
        assert math.isnan(fill)  # lookup passes it through ...
        # ... and _barrier_prices rejects it (fail-closed chain).
        assert (
            runner._barrier_prices(fill_price=fill, atr=0.002, price_dp=5, direction="buy") is None
        )


class TestNoMidAnchorInLivePathStatic:
    """Static source assertions: the old decision-bar-mid anchor is gone."""

    @pytest.mark.parametrize(
        "old_expr",
        [
            "inst_close + _TP_MULT",
            "inst_close - _TP_MULT",
            "inst_close + _SL_MULT",
            "inst_close - _SL_MULT",
        ],
    )
    def test_old_mid_anchored_expression_removed(self, old_expr: str) -> None:
        assert old_expr not in _SRC

    def test_tpsl_map_anchor_reads_recorded_fill_price(self) -> None:
        # The contract barriers stored in _tpsl_map are computed from the
        # fill price read back from on_fill's persisted position row.
        assert "_recorded_fill_price(state_manager, opened_order_id)" in _SRC
        assert "fill_price=_fill_price" in _SRC

    def test_fail_closed_warning_present(self) -> None:
        # No silent fallback: missing fill/ATR must log an explicit warning
        # and leave the position governed by the time stop.
        assert "barrier_anchor_unavailable" in _SRC


# ---------------------------------------------------------------------------
# F8-D: _feature_as_of_time — decision-bar close, not open
# ---------------------------------------------------------------------------

_BAR_OPEN = datetime(2026, 1, 8, 12, 0, tzinfo=UTC)


class TestFeatureAsOfTime:
    def test_m1_open_1200_gives_asof_1201(self) -> None:
        assert runner._feature_as_of_time(_BAR_OPEN, "M1") == datetime(
            2026, 1, 8, 12, 1, tzinfo=UTC
        )

    def test_m5_open_1200_gives_asof_1205(self) -> None:
        assert runner._feature_as_of_time(_BAR_OPEN, "M5") == datetime(
            2026, 1, 8, 12, 5, tzinfo=UTC
        )

    def test_h1_open_1200_gives_asof_1300(self) -> None:
        assert runner._feature_as_of_time(_BAR_OPEN, "H1") == datetime(
            2026, 1, 8, 13, 0, tzinfo=UTC
        )

    def test_completed_decision_bar_passes_strict_lt_filter(self) -> None:
        """FeatureService filters strictly `timestamp < as_of_time`.

        With as-of = bar close (12:01 for an M1 bar opened 12:00), the
        completed decision bar stamped 12:00 is INCLUDED; the next /
        in-progress bar stamped 12:01 is still EXCLUDED.
        """
        as_of = runner._feature_as_of_time(_BAR_OPEN, "M1")
        decision_bar_ts = _BAR_OPEN  # completed decision bar (open stamp)
        next_bar_ts = _BAR_OPEN + timedelta(minutes=1)
        assert decision_bar_ts < as_of  # included
        assert not (next_bar_ts < as_of)  # excluded

    def test_old_open_stamped_asof_excluded_decision_bar(self) -> None:
        """Regression contrast: the pre-fix as-of (= bar OPEN) dropped the
        just-completed decision bar under the strict `<` filter."""
        old_as_of = _BAR_OPEN
        decision_bar_ts = _BAR_OPEN
        assert not (decision_bar_ts < old_as_of)

    def test_docstring_cites_f8_contract(self) -> None:
        doc = runner._feature_as_of_time.__doc__ or ""
        assert "F8_FEATURE_ASOF_CONTRACT_ALIGNED" in doc
        # The alignment intentionally applies to paper/replay and live equally.
        assert "equally" in doc

    def test_call_site_uses_helper_not_bar_open(self) -> None:
        assert "as_of_time=_feature_as_of_time(bar.time_utc, args.granularity)" in _SRC
        assert "as_of_time=bar.time_utc" not in _SRC


class TestRealFeatureServiceIncludesDecisionBar:
    """End-to-end through the real FeatureService strict `<` filter."""

    @staticmethod
    def _candle(ts: datetime, close: float) -> dict:
        return {
            "timestamp": ts,
            "open": close,
            "high": close + 0.0001,
            "low": close - 0.0001,
            "close": close,
            "volume": 100.0,
        }

    def _service(self):
        from fx_ai_trading.services.feature_service import FeatureService

        candles = [
            self._candle(_BAR_OPEN - timedelta(minutes=2), 1.1001),
            self._candle(_BAR_OPEN - timedelta(minutes=1), 1.1002),
            self._candle(_BAR_OPEN, 1.1003),  # completed decision bar
        ]
        return FeatureService(get_candles=lambda inst, as_of: candles)

    def test_asof_at_bar_close_includes_decision_bar(self) -> None:
        svc = self._service()
        fs = svc.build(
            instrument="EUR_USD",
            tier="M1",
            cycle_id=UUID(int=0),
            as_of_time=runner._feature_as_of_time(_BAR_OPEN, "M1"),
        )
        assert fs.sampled_features["last_close"] == pytest.approx(1.1003)

    def test_asof_at_bar_open_was_one_bar_stale(self) -> None:
        svc = self._service()
        fs = svc.build(
            instrument="EUR_USD",
            tier="M1",
            cycle_id=UUID(int=0),
            as_of_time=_BAR_OPEN,  # the pre-fix behaviour
        )
        assert fs.sampled_features["last_close"] == pytest.approx(1.1002)
