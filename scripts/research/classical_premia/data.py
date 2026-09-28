# ruff: noqa: E501 -- data prose
"""入力の組み立て。**新しい取得はしない**（既に seen の cache だけを読む）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

- FX: `top_five.panel.long_span_panel`（ECB 参照レート、seen window の外の行は入らず、最後に
  `assert_no_protected_day` で確認される）。
- 金利: `mechanism_redesign.signals._load_slot`（取得記録の content hash を照合し、参照期間が保護暦日に
  掛かる観測があれば読まずに止まる）。
- 最後にもう一度、span の全ての日が 2016-06-01 以前であることを parsed date で確認する。
"""

from __future__ import annotations

import datetime as dt
from typing import Final

import pandas as pd

from scripts.research.classical_premia import book, prereg
from scripts.research.mechanism_redesign import signals
from scripts.research.next_five.signals import _align
from scripts.research.top_five import panel, sources

LAST_RETURN_DAY: Final[dt.date] = dt.date.fromisoformat(prereg.SPAN["last_return_day"])
FRESH_POOL_START: Final[dt.date] = dt.date(2016, 6, 2)


def policy_rates(index: pd.DatetimeIndex, *, after_month_end_days: int = 0) -> pd.DataFrame:
    """BIS 政策金利の月末値を置く。

    - 会計（`after_month_end_days=0`）: 月末の当日から（#495 の policy_rates_contemporaneous と同じ置き方）。
    - signal（`after_month_end_days=1`）: 月末の**翌暦日**から。decision day（月初の営業日）には必ず前月末の値が
      届き、月末が週末・休日でも 1 か月古い値にならない（Role 1 N1）。当日の値は使わない。
    """
    columns: dict[str, pd.Series] = {}
    for currency in prereg.UNIVERSE:
        series, _ = signals._load_slot("policy_rate_bis", currency)
        placed = series.copy()
        placed.index = placed.index.to_period("M").to_timestamp(
            how="end"
        ).normalize() + pd.Timedelta(days=after_month_end_days)
        columns[currency] = _align(
            placed, index, staleness_days=int(prereg.CARRY["staleness_days"])
        )
    rates = pd.DataFrame(columns, index=index)
    for first, last in prereg.CARRY["jpy_zero_periods"]:
        window = (rates.index >= first) & (rates.index <= last)
        rates.loc[window, "JPY"] = rates.loc[window, "JPY"].fillna(0.0)
    return rates


def build() -> tuple[book.Inputs, dict[str, pd.DataFrame], dict[str, object]]:
    long_panel = panel.long_span_panel()
    returns = book.usd_numeraire_returns(long_panel["pair_returns"])
    index = returns.index
    last_day = max(ts.date() for ts in index)
    if last_day > LAST_RETURN_DAY or any(ts.date() >= FRESH_POOL_START for ts in index):
        raise AssertionError("panel に 2016-06-01 より後の行がある（fresh pool）")
    sources.assert_no_protected_day([ts.date() for ts in index], label="classical_premia")

    policy = policy_rates(index)
    account = {
        "policy_contemporaneous": policy,
        "three_month_lagged": signals.carry_rate_panel(index),
    }
    #: signal は月末の翌暦日から（decision day t には前月末までに確定した値だけ）
    signal_rates = policy_rates(index, after_month_end_days=1)

    decision_days = book.monthly_decision_days(
        index, prereg.SPAN["first_decision_on_or_after"], prereg.SPAN["last_return_day"]
    )
    first = decision_days[0]
    #: P&L は翌営業日なので、span は最後の営業日の 1 つ前まで
    span = index[(index >= first) & (index < index[-1])]
    inputs = book.Inputs(
        returns=returns,
        signal_rates=signal_rates,
        account_rates=account,
        decision_days=decision_days,
        span=span,
    )
    scores = {"carry": book.carry_scores(signal_rates), "momentum": book.momentum_scores(returns)}
    for name, frame in scores.items():
        within = frame.reindex(span)
        if within.isna().any().any():
            bad = within[within.isna().any(axis=1)].index[:3]
            raise ValueError(
                f"{name}: span 内に欠損した score がある {list(bad.date)}（fail-closed）"
            )
    provenance = {
        "source": prereg.SPAN["source"],
        "panel_first_day": str(index[0].date()),
        "panel_last_day": str(index[-1].date()),
        "first_decision_day": str(first.date()),
        "last_decision_day": str(decision_days[-1].date()),
        "decision_days": len(decision_days),
        "span_days": len(span),
        "last_pnl_day": str(index[index.get_loc(span[-1]) + 1].date()),
        "no_new_acquisition": True,
        "no_protected_day": True,
    }
    return inputs, scores, provenance


__all__ = ["build", "policy_rates"]
