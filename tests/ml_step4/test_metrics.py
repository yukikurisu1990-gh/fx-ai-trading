"""Portfolio metrics tests — daily Sharpe, drawdown, concentration, cost cells."""

from __future__ import annotations

import math

import pytest

from scripts.ml_step4 import metrics
from scripts.ml_step4.metrics import (
    MetricTrade,
    annualised_daily_sharpe,
    compute_all,
    concurrency_profile,
    cost_sensitivity,
    daily_portfolio_pnl,
    max_equity_drawdown,
    pair_concentration,
)


def test_daily_sharpe_from_daily_series_not_per_trade() -> None:
    # Two days: day1 has two trades summing to +1, day2 has one trade +3.
    trades = [
        MetricTrade("EUR_USD", "2025-01-01", 0.5),
        MetricTrade("USD_JPY", "2025-01-01", 0.5),
        MetricTrade("EUR_USD", "2025-01-02", 3.0),
    ]
    series = [v for _, v in daily_portfolio_pnl(trades, cell_pips=0.0)]
    assert series == [1.0, 3.0]
    # Daily Sharpe uses the [1,3] daily series, not the [0.5,0.5,3] per-trade series.
    expected = (2.0 / math.sqrt(2.0)) * math.sqrt(252)
    assert annualised_daily_sharpe(series) == pytest.approx(expected)


def test_daily_sharpe_degenerate_cases() -> None:
    assert annualised_daily_sharpe([]) == 0.0
    assert annualised_daily_sharpe([1.0]) == 0.0
    assert annualised_daily_sharpe([2.0, 2.0, 2.0]) == 0.0  # zero variance


def test_max_drawdown_on_daily_equity_curve() -> None:
    dd = max_equity_drawdown([-1.0, -1.0, 5.0], notional_equity_pips=100.0)
    assert dd["max_drawdown_pips"] == pytest.approx(2.0)
    assert dd["max_drawdown_frac"] == pytest.approx(0.02)


def test_max_drawdown_requires_positive_notional() -> None:
    with pytest.raises(ValueError):
        max_equity_drawdown([1.0], notional_equity_pips=0.0)


def test_pair_concentration_uses_trade_and_pnl_share() -> None:
    trades = [
        MetricTrade("EUR_USD", "2025-01-01", 4.0),
        MetricTrade("EUR_USD", "2025-01-01", 4.0),
        MetricTrade("EUR_USD", "2025-01-01", 4.0),
        MetricTrade("USD_JPY", "2025-01-02", 1.0),
    ]
    conc = pair_concentration(trades, cell_pips=0.0)
    assert conc["max_trade_share"] == pytest.approx(0.75)  # 3 of 4 trades
    assert conc["max_positive_pnl_share"] == pytest.approx(12.0 / 13.0)


def test_cost_sensitivity_recomputes_per_cell() -> None:
    trades = [
        MetricTrade("EUR_USD", "2025-01-01", 1.0),
        MetricTrade("EUR_USD", "2025-01-02", 1.0),
    ]
    cs = cost_sensitivity(trades, cells=(0.0, 0.5, 1.0))
    assert cs["0.0pip"]["expectancy_pips"] == pytest.approx(1.0)
    assert cs["0.5pip"]["expectancy_pips"] == pytest.approx(0.5)
    assert cs["1.0pip"]["expectancy_pips"] == pytest.approx(0.0)


def test_concurrency_profile() -> None:
    # A closes at 10, B opens at 5 (overlap => max 2), C opens at 10 (A freed).
    prof = concurrency_profile([(0, 10), (5, 15), (10, 20)])
    assert prof["max_concurrency"] == 2.0


def test_compute_all_bundle() -> None:
    trades = [MetricTrade(f"P{i % 3}", f"2025-01-{(i % 5) + 1:02d}", 1.0) for i in range(20)]
    bundle = compute_all(
        trades,
        cell_pips=0.5,
        notional_equity_pips=1000.0,
        holdout_trading_days=5,
    )
    assert bundle["trade_count"] == 20
    assert bundle["primary_metric"] == "daily_portfolio_sharpe_annualised"
    assert "1.0pip" in bundle["cost_sensitivity"]
    assert bundle["daily_coverage_frac"] == pytest.approx(1.0)


def test_trading_days_per_year_constant() -> None:
    assert metrics.contract.TRADING_DAYS_PER_YEAR == 252


# --- PR #411 R-5: auditable UTC trading-day definition ----------------------


def test_r5_trading_day_utc_grouping() -> None:
    from datetime import UTC, datetime

    from scripts.ml_step4.metrics import trading_day_utc

    assert trading_day_utc(datetime(2025, 4, 25, 0, 0, tzinfo=UTC)) == "2025-04-25"
    assert trading_day_utc(datetime(2025, 4, 25, 23, 59, tzinfo=UTC)) == "2025-04-25"


def test_r5_converts_other_tz_to_utc() -> None:
    from datetime import datetime, timedelta, timezone

    from scripts.ml_step4.metrics import trading_day_utc

    # 2025-04-26 00:30 at UTC+2 is 2025-04-25 22:30 UTC -> UTC day 25.
    tz = timezone(timedelta(hours=2))
    assert trading_day_utc(datetime(2025, 4, 26, 0, 30, tzinfo=tz)) == "2025-04-25"


def test_r5_naive_datetime_fails_closed() -> None:
    from datetime import datetime

    from scripts.ml_step4.metrics import trading_day_utc

    with pytest.raises(ValueError):
        trading_day_utc(datetime(2025, 4, 25, 0, 0))  # no tzinfo


def test_r5_definition_recorded_in_contract() -> None:
    from scripts.ml_step4 import contract

    assert contract.TRADING_DAY_DEFINITION == "utc_calendar_date"
    ev = contract.contract_dict()["evaluation"]
    assert ev["daily_coverage_denominator"] == "distinct_utc_calendar_dates_in_holdout"
