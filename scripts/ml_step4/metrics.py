"""Metrics calculator for the ML Step 4 executor (pure, deterministic).

Key contract points enforced here:

* the **primary decision metric is daily portfolio Sharpe**, computed from the
  daily portfolio PnL series — NEVER per-trade Sharpe;
* **max equity drawdown** is peak-to-trough on the daily equity curve as a
  fraction of fixed notional equity (not DD%PnL);
* **pair concentration** uses both trade share and positive-PnL share;
* **cost sensitivity** recomputes metrics per cost cell (0.0 / 0.5 / 1.0 pip).

Per-trade records are ``MetricTrade(pair, day, gross_pnl_pips)`` where
``gross_pnl_pips`` already embeds spread exactly once (B-2 geometry) and ``day``
is the UTC calendar day. The flat slippage cost cell is subtracted a single
time per trade at metric time, which is what makes cost sensitivity well-defined.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from . import contract


@dataclass(frozen=True)
class MetricTrade:
    """One trade for portfolio metrics."""

    pair: str
    day: str  # UTC calendar day 'YYYY-MM-DD'
    gross_pnl_pips: float  # spread embedded once, before the flat slippage cell


def net_pnl(trade: MetricTrade, cell_pips: float) -> float:
    """Per-trade net PnL after applying the flat slippage cell once."""
    return trade.gross_pnl_pips - cell_pips


def daily_portfolio_pnl(trades: Iterable[MetricTrade], cell_pips: float) -> list[tuple[str, float]]:
    """Sum net per-trade PnL by UTC day; returns a day-sorted series."""
    by_day: dict[str, float] = {}
    for t in trades:
        by_day[t.day] = by_day.get(t.day, 0.0) + net_pnl(t, cell_pips)
    return sorted(by_day.items())


def expectancy(trades: Sequence[MetricTrade], cell_pips: float) -> float:
    """Mean per-trade net PnL in pips (0.0 if no trades)."""
    trades = list(trades)
    if not trades:
        return 0.0
    return sum(net_pnl(t, cell_pips) for t in trades) / len(trades)


def annualised_daily_sharpe(
    daily_pnl_values: Sequence[float],
    trading_days_per_year: int = contract.TRADING_DAYS_PER_YEAR,
) -> float:
    """Annualised Sharpe of the daily portfolio PnL series.

    ``mean / sample_stdev * sqrt(trading_days_per_year)``. Returns 0.0 for fewer
    than two days or zero variance (undefined Sharpe reported as 0.0, never NaN).
    """
    values = list(daily_pnl_values)
    if len(values) < 2:
        return 0.0
    sd = statistics.stdev(values)  # sample stdev (ddof=1)
    if sd == 0 or not math.isfinite(sd):
        return 0.0
    mean = statistics.fmean(values)
    return (mean / sd) * math.sqrt(trading_days_per_year)


def max_equity_drawdown(
    daily_pnl_values: Sequence[float], notional_equity_pips: float
) -> dict[str, float]:
    """Peak-to-trough drawdown on the daily equity curve.

    Equity curve = ``notional_equity_pips`` + cumulative daily PnL. Returns the
    absolute drawdown (pips) and its fraction of fixed notional equity.
    """
    if notional_equity_pips <= 0:
        raise ValueError("notional_equity_pips must be positive")
    equity = notional_equity_pips
    peak = equity
    max_dd_abs = 0.0
    for pnl in daily_pnl_values:
        equity += pnl
        peak = max(peak, equity)
        max_dd_abs = max(max_dd_abs, peak - equity)
    return {
        "max_drawdown_pips": max_dd_abs,
        "max_drawdown_frac": max_dd_abs / notional_equity_pips,
        "notional_equity_pips": notional_equity_pips,
    }


def win_rate(trades: Sequence[MetricTrade], cell_pips: float) -> float:
    trades = list(trades)
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if net_pnl(t, cell_pips) > 0)
    return wins / len(trades)


def avg_win_loss(trades: Sequence[MetricTrade], cell_pips: float) -> dict[str, float]:
    wins = [net_pnl(t, cell_pips) for t in trades if net_pnl(t, cell_pips) > 0]
    losses = [net_pnl(t, cell_pips) for t in trades if net_pnl(t, cell_pips) < 0]
    return {
        "avg_win_pips": statistics.fmean(wins) if wins else 0.0,
        "avg_loss_pips": statistics.fmean(losses) if losses else 0.0,
    }


def turnover(n_trades: int, n_trading_days: int) -> float:
    """Portfolio-average trades per day (0.0 if no trading days)."""
    if n_trading_days <= 0:
        return 0.0
    return n_trades / n_trading_days


def daily_coverage(trades: Iterable[MetricTrade], holdout_trading_days: int) -> float:
    """Fraction of holdout trading days that saw ≥ 1 trade."""
    if holdout_trading_days <= 0:
        return 0.0
    days = {t.day for t in trades}
    return len(days) / holdout_trading_days


def pair_contribution(
    trades: Sequence[MetricTrade], cell_pips: float
) -> dict[str, dict[str, float]]:
    """Per-pair trade share, PnL, and positive-PnL share."""
    trades = list(trades)
    n = len(trades)
    total_pos = sum(max(net_pnl(t, cell_pips), 0.0) for t in trades)
    out: dict[str, dict[str, float]] = {}
    for t in trades:
        rec = out.setdefault(t.pair, {"n_trades": 0.0, "pnl_pips": 0.0, "positive_pnl_pips": 0.0})
        rec["n_trades"] += 1
        rec["pnl_pips"] += net_pnl(t, cell_pips)
        rec["positive_pnl_pips"] += max(net_pnl(t, cell_pips), 0.0)
    for rec in out.values():
        rec["trade_share"] = rec["n_trades"] / n if n else 0.0
        rec["positive_pnl_share"] = rec["positive_pnl_pips"] / total_pos if total_pos > 0 else 0.0
    return out


def pair_concentration(trades: Sequence[MetricTrade], cell_pips: float) -> dict[str, float]:
    """Max single-pair trade share and max single-pair positive-PnL share."""
    contrib = pair_contribution(trades, cell_pips)
    if not contrib:
        return {"max_trade_share": 0.0, "max_positive_pnl_share": 0.0}
    return {
        "max_trade_share": max(r["trade_share"] for r in contrib.values()),
        "max_positive_pnl_share": max(r["positive_pnl_share"] for r in contrib.values()),
    }


def concurrency_profile(intervals: Sequence[tuple[Any, Any]]) -> dict[str, float]:
    """Max / mean simultaneous open positions from ``[entry, exit)`` intervals."""
    if not intervals:
        return {"max_concurrency": 0.0, "mean_concurrency": 0.0}
    events: list[tuple[Any, int]] = []
    for entry, exit_ in intervals:
        events.append((entry, 1))
        events.append((exit_, -1))
    # Sort by marker; at equal marker, process exits (-1) before entries (+1)
    # so a position closing at T frees the slot for one opening at T.
    events.sort(key=lambda e: (e[0], e[1]))
    cur = 0
    max_c = 0
    samples: list[int] = []
    for _, delta in events:
        cur += delta
        max_c = max(max_c, cur)
        if delta == 1:
            samples.append(cur)
    mean_c = statistics.fmean(samples) if samples else 0.0
    return {"max_concurrency": float(max_c), "mean_concurrency": mean_c}


def cost_sensitivity(
    trades: Sequence[MetricTrade],
    *,
    cells: Sequence[float] = contract.ALL_COST_CELLS_PIPS,
    trading_days_per_year: int = contract.TRADING_DAYS_PER_YEAR,
) -> dict[str, dict[str, float]]:
    """Recompute expectancy + daily Sharpe at each cost cell."""
    out: dict[str, dict[str, float]] = {}
    for cell in cells:
        series = [v for _, v in daily_portfolio_pnl(trades, cell)]
        out[f"{cell:.1f}pip"] = {
            "cell_pips": cell,
            "expectancy_pips": expectancy(trades, cell),
            "daily_portfolio_sharpe": annualised_daily_sharpe(series, trading_days_per_year),
        }
    return out


def compute_all(
    trades: Sequence[MetricTrade],
    *,
    cell_pips: float = contract.PRIMARY_COST_CELL_PIPS,
    notional_equity_pips: float,
    holdout_trading_days: int,
    trading_days_per_year: int = contract.TRADING_DAYS_PER_YEAR,
) -> dict[str, Any]:
    """Full metrics bundle at the given primary cost cell + cost sensitivity."""
    trades = list(trades)
    series = [v for _, v in daily_portfolio_pnl(trades, cell_pips)]
    n_days = len({t.day for t in trades})
    return {
        "cost_cell_pips": cell_pips,
        "trade_count": len(trades),
        "expectancy_pips": expectancy(trades, cell_pips),
        "daily_portfolio_sharpe_annualised": annualised_daily_sharpe(series, trading_days_per_year),
        "max_equity_drawdown": max_equity_drawdown(series, notional_equity_pips),
        "win_rate": win_rate(trades, cell_pips),
        **avg_win_loss(trades, cell_pips),
        "turnover_trades_per_day": turnover(len(trades), n_days),
        "daily_coverage_frac": daily_coverage(trades, holdout_trading_days),
        "pair_concentration": pair_concentration(trades, cell_pips),
        "cost_sensitivity": cost_sensitivity(trades, trading_days_per_year=trading_days_per_year),
        "primary_metric": "daily_portfolio_sharpe_annualised",
    }


# ---------------------------------------------------------------------------
# PR #411 R-5 — auditable UTC trading-day definition
# ---------------------------------------------------------------------------


def trading_day_utc(dt: datetime) -> str:
    """Canonical trading day = the UTC calendar date 'YYYY-MM-DD' (R-5).

    No local/broker timezone: the input is converted to UTC and truncated to the
    calendar date. This is the single sanctioned key for daily aggregation and
    the daily-coverage denominator.
    """
    if not isinstance(dt, datetime):
        raise ValueError("trading_day_utc requires a datetime")
    if dt.tzinfo is None:
        raise ValueError("trading_day_utc requires a timezone-aware datetime (UTC)")
    return dt.astimezone(UTC).strftime("%Y-%m-%d")
