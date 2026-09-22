# ruff: noqa: E501 -- panel prose
"""5 本が共有する FX panel。**構成は 1 つ、data source は 2 つ。**

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

長 span（ECB 参照レート）と近 span（guarded M15 cache）で data source は違うが、
**currency excess return の作り方は同一**にする。そうしないと 2 つの span の結果を
同じ表に並べられない。採るのは本 repo が既に使っている構成である:

1. pair ごとに日次 close-to-close の log return を作る
2. 通貨 `c` について、`c` が base の pair は `+`、quote の pair は `-` で符号を揃え、
   その平均を `currency_return[c]` とする
3. **cross-section の平均を引く** — これが common factor（dollar 方向）の除去であり、
   panel を「相対価値の panel」にする

**どちらの span も、凍結した seen window の外の行は入らない。**
`sources.assert_no_protected_day` が最後に確認する。
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.top_five import UNIVERSE, sources

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
SCRATCH: Final[Path] = REPO_ROOT / "artifacts/track_a_scratch"

#: 近 span を連続被覆する 3 つの guarded cache。どれも既に seen 化された data で、
#: archive の新規読み取りは行わない。
RECENT_CACHES: Final[tuple[str, ...]] = (
    "momentum_replication_b",
    "supplemental_replication",
    "exploratory_round_1",
)

#: 長 span の ECB 参照レート（EUR 建て）。
LONG_CACHE: Final[str] = "valuation"

#: 1 日を成立させるのに要る M15 バー数。既存の corpus 構成と同じ閾値。
MIN_BARS_FOR_A_TRADING_DAY: Final[int] = 40


def _tradable_pairs(currencies: tuple[str, ...]) -> list[tuple[str, str]]:
    """universe 内で両脚が揃う通貨対。順序は決定的にする。"""
    ordered = list(currencies)
    return [(a, b) for i, a in enumerate(ordered) for b in ordered[i + 1 :]]


def _currency_excess(pair_returns: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """pair の log return から currency excess return を作る。**両 span 共通。**"""
    currency_return = pd.DataFrame(index=pair_returns.index, columns=list(UNIVERSE), dtype=float)
    coverage: dict[str, int] = {}
    for currency in UNIVERSE:
        signed = []
        for column in pair_returns.columns:
            base, quote = column.split("_")
            if currency == base:
                signed.append(pair_returns[column])
            elif currency == quote:
                signed.append(-pair_returns[column])
        coverage[currency] = len(signed)
        if signed:
            currency_return[currency] = pd.concat(signed, axis=1).mean(axis=1)
    common = currency_return.mean(axis=1)
    return {
        "currency_return": currency_return,
        "currency_excess_return": currency_return.sub(common, axis=0),
        "common_factor": common.to_frame("common_factor"),
        "coverage": pd.Series(coverage, name="legs_per_currency").to_frame(),
        "pair_returns": pair_returns,
    }


def long_span_panel() -> dict[str, pd.DataFrame]:
    """ECB 参照レートから。EUR が numeraire なので EUR 列は 1.0 である。"""
    data = SCRATCH / LONG_CACHE
    rates = {}
    for currency in UNIVERSE:
        if currency == "EUR":
            continue
        path = data / f"fx_{currency.lower()}.parquet"
        frame = pd.read_parquet(path).set_index("period")["value"].astype(float)
        rates[currency] = frame
    fx = pd.DataFrame(rates)
    fx.index = pd.to_datetime(fx.index)
    fx["EUR"] = 1.0
    fx = fx[list(UNIVERSE)].sort_index()

    #: `BASE_QUOTE` の価格は quote / base。EUR 建てレートからはこの比で出る。
    prices = {}
    for base, quote in _tradable_pairs(UNIVERSE):
        prices[f"{base}_{quote}"] = fx[quote] / fx[base]
    returns = np.log(pd.DataFrame(prices)).diff().dropna(how="all")
    returns = returns[[sources.is_seen(ts.date()) for ts in returns.index]]
    sources.assert_no_protected_day([ts.date() for ts in returns.index], label="long_span")
    return _currency_excess(returns)


def _daily_from_m15(path: Path) -> pd.Series:
    """M15 bar から UTC 日次の mid close。**その日の最後のバーだけを使う。**"""
    frame = pd.read_parquet(path, columns=["ts", "bid_c", "ask_c"])
    mid = (frame["bid_c"].astype(float) + frame["ask_c"].astype(float)) / 2.0
    day = pd.to_datetime(frame["ts"], utc=True).dt.date
    grouped = pd.DataFrame({"day": day, "mid": mid}).groupby("day", sort=True)
    daily = grouped["mid"].last()
    enough = grouped["mid"].size() >= MIN_BARS_FOR_A_TRADING_DAY
    return daily[enough]


def recent_span_panel() -> dict[str, pd.DataFrame]:
    """3 つの guarded cache を連結して日次にする。**archive は読まない。**"""
    per_pair: dict[str, pd.Series] = {}
    for cache in RECENT_CACHES:
        directory = SCRATCH / cache
        for path in sorted(directory.glob("m15_*.parquet")):
            pair = path.stem.removeprefix("m15_")
            series = _daily_from_m15(path)
            per_pair[pair] = series if pair not in per_pair else pd.concat([per_pair[pair], series])
    closes = pd.DataFrame(per_pair).sort_index()
    closes = closes[~closes.index.duplicated(keep="last")]
    closes.index = pd.to_datetime(closes.index)
    keep = [c for c in closes.columns if set(c.split("_")) <= set(UNIVERSE)]
    returns = np.log(closes[keep]).diff().dropna(how="all")
    returns = returns[[sources.is_seen(ts.date()) for ts in returns.index]]
    sources.assert_no_protected_day([ts.date() for ts in returns.index], label="recent_span")
    return _currency_excess(returns)


def build() -> dict[str, Any]:
    """両 span の panel と、その provenance。"""
    long_panel = long_span_panel()
    recent_panel = recent_span_panel()
    return {
        "long": long_panel,
        "recent": recent_panel,
        "provenance": {
            "construction": (
                "pair 日次 log return -> 符号を揃えた通貨平均 -> cross-section 平均を引く。"
                "**両 span で同一**"
            ),
            "long": {
                "source": "ECB euro reference rates (already acquired for T-V)",
                "days": int(len(long_panel["currency_excess_return"])),
                "first": str(long_panel["currency_excess_return"].index.min().date()),
                "last": str(long_panel["currency_excess_return"].index.max().date()),
                "pairs": int(long_panel["pair_returns"].shape[1]),
            },
            "recent": {
                "source": f"guarded M15 caches: {', '.join(RECENT_CACHES)}",
                "days": int(len(recent_panel["currency_excess_return"])),
                "first": str(recent_panel["currency_excess_return"].index.min().date()),
                "last": str(recent_panel["currency_excess_return"].index.max().date()),
                "pairs": int(recent_panel["pair_returns"].shape[1]),
                "no_archive_read": True,
            },
            "carry_leg": "CARRY_LEG_ABSENT_ON_BOTH_SPANS_SPOT_ONLY",
        },
    }


def business_day_lag(frame: pd.DataFrame, days: int) -> pd.DataFrame:
    """外部系列を `days` 営業日ずらす。**panel の calendar 上でずらす。**

    暦日でずらすと週末を挟んだときに lag が縮む。panel の行番号で送るのが正しい。
    """
    if days < 1:
        raise ValueError("lag は 1 営業日以上でなければならない")
    return frame.shift(days)


def align_to_panel(series: pd.Series, index: pd.DatetimeIndex, *, lag: int) -> pd.Series:
    """外部日次系列を panel の calendar に載せ、指定営業日だけ遅らせる。

    `reindex(...).ffill()` を先に行うのは、外部系列の休場日が FX の営業日と一致しない
    ためである。**ffill してから shift する**ので、ずらし幅は panel の営業日で数えられる。
    """
    aligned = series.reindex(series.index.union(index)).sort_index().ffill().reindex(index)
    return aligned.shift(lag)


def as_of(day: dt.date) -> str:
    return day.isoformat()


__all__ = [
    "LONG_CACHE",
    "MIN_BARS_FOR_A_TRADING_DAY",
    "RECENT_CACHES",
    "align_to_panel",
    "build",
    "business_day_lag",
    "long_span_panel",
    "recent_span_panel",
]
