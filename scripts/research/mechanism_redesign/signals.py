# ruff: noqa: E501 -- signal prose
"""凍結する 4 本の signal（mechanism redesign cycle）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**Stage 1 は fixed / unfitted rule だけ。** 係数の推定も閾値の探索もしない。

next-five の共通基盤修正（C-1〜C-6）を引き継ぐ:

- 整列（`_align`）・n か月変化（`_change`）は next-five の**修正済み**実装をそのまま使う
  （基準値にも staleness、欠損行は観測扱いしない、m+k 月末着地）。
- `scores_for` は ffill しない。3 通貨未満の日が span の途中にあれば fail-closed。
- 外部 series を読む経路は `_load` 1 本。**参照期間が保護暦日に掛かる観測があれば読まずに止める**
  （request 側で既に外してあるので、ここは二重の確認）。

2 種類の book がある:

- **XS**（M11 / M10）: 既存の相対価値 book。第 1 主成分を中立化する。
- **DOLLAR**（M15 / M16）: ドル対 7 通貨 basket。**第 1 主成分を中立化しない**（それがドル factor
  そのものなので）。mu は USD に −s、他 7 通貨に +s/7。book は `linear` mapping で等ウェイト basket に
  なり、capped_weights が各側を 0.5 に揃えるので、**実際に効くのは s の符号だけ**（大きさは効かない）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.data_access import request_policy
from scripts.research.next_five.signals import (
    NonContiguousScoresError,
    SignalUnavailableError,
    _align,
    _change,
)
from scripts.research.top_five import UNIVERSE, sources

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
DATA_DIR: Final[Path] = REPO_ROOT / "artifacts/track_a_scratch/mechanism_redesign"
M15_CACHES: Final[tuple[str, ...]] = (
    "momentum_replication_b",
    "supplemental_replication",
    "exploratory_round_1",
)

CURRENCIES: Final[tuple[str, ...]] = UNIVERSE
FOREIGN: Final[tuple[str, ...]] = tuple(c for c in UNIVERSE if c != "USD")
MIN_CURRENCIES: Final[int] = 3

#: nuisance 定数（primary と感度集合）。**結果の後に best point を選ばない。**
NUISANCE: Final[dict[str, dict[str, Any]]] = {
    "max_staleness_days_monthly": {"primary": 75, "sensitivity_set": (45, 60, 75, 90, 120)},
    "change_window_months": {"primary": 12, "sensitivity_set": (6, 12, 24)},
    "liquidity_short_window": {"primary": 20, "sensitivity_set": (10, 20, 40)},
    "liquidity_long_window": {"primary": 250, "sensitivity_set": (126, 250, 500)},
    "implementation_tolerance_band": {"primary": 0.10, "sensitivity_set": (0.05, 0.10, 0.20)},
}

#: **機構側の定数**（nuisance ではない）。
#: 四半期 series は 1 期が約 92 日なので、月次の 75 日では次の公表までに必ず切れる。
#: 四半期の staleness は「1 期 + 1 か月」で固定する（感度は月次側だけで取る）。
QUARTERLY_STALENESS_DAYS: Final[int] = 125
#: 公表 lag（参照期間の最後の月からの月数で、m+k 月末以降に使う）。
LAG_MONTHS: Final[dict[str, int]] = {
    "short_rate_3m": 1,  # 市場金利の月平均。翌月初に確定、翌月末から使う
    "cpi": 2,  # 翌月中旬公表 → m+2 月末
    "unemployment": 2,
}
#: 四半期の stamp は四半期の初月。参照期間の最後の月は stamp + 2 か月。
QUARTER_EXTRA_MONTHS: Final[int] = 2
#: 流動性（M15 の quote）は当日の bar から作るので、**翌営業日から**使う。
LIQUIDITY_LAG_BUSINESS_DAYS: Final[int] = 1
MIN_BARS_FOR_A_DAY: Final[int] = 40


def _nuisance(name: str, overrides: dict[str, Any] | None) -> Any:
    value = NUISANCE[name]["primary"]
    if overrides and name in overrides:
        if overrides[name] not in NUISANCE[name]["sensitivity_set"]:
            raise ValueError(f"{name}={overrides[name]} は凍結した感度集合の外")
        value = overrides[name]
    return value


def _load(name: str) -> tuple[pd.Series, str]:
    """外部 series を読む唯一の経路。戻り値は (series, 参照期間の種類)。"""
    path = DATA_DIR / f"{name}.parquet"
    if not path.exists():
        raise SignalUnavailableError(f"{name} が取得されていない")
    frame = pd.read_parquet(path)
    series = frame.iloc[:, -1].astype(float).sort_index().dropna()
    if series.empty:
        raise SignalUnavailableError(f"{name} は空")
    spacing = float(pd.Series(series.index).diff().dt.days.median())
    kind = request_policy.QUARTER if spacing > 45 else request_policy.MONTH
    for stamp in series.index:
        lo, hi = request_policy.reference_period(stamp.date(), kind)
        if request_policy.touches_protected(lo, hi):
            raise AssertionError(f"{name}: 参照期間が保護暦日に掛かる観測がある（{stamp.date()}）")
    return series, kind


def _monthly_panel(
    slot: str, index: pd.DatetimeIndex, *, change_months: int | None, staleness: int
) -> pd.DataFrame:
    """通貨ごとの月次 / 四半期 series を、公表 lag を守って日次 index に載せる。"""
    columns: dict[str, pd.Series] = {}
    for currency in CURRENCIES:
        try:
            series, kind = _load_slot(slot, currency)
        except SignalUnavailableError:
            continue
        quarterly = kind == request_policy.QUARTER
        stale = QUARTERLY_STALENESS_DAYS if quarterly else staleness
        if change_months is not None:
            series = _change(series, change_months, staleness_days=stale)
        offset = LAG_MONTHS[slot] + (QUARTER_EXTRA_MONTHS if quarterly else 0)
        columns[currency] = _align(
            series, index, vintage_offset_months=offset, staleness_days=stale
        )
    return pd.DataFrame(columns, index=index).reindex(columns=list(CURRENCIES))


def _load_slot(slot: str, currency: str) -> tuple[pd.Series, str]:
    """CPI は前年比（%）で揃える。前年比 series が無い通貨だけ、指数水準から前年比を作る。"""
    if slot == "cpi":
        try:
            return _load(f"cpi_yoy_{currency.lower()}")
        except SignalUnavailableError:
            index_series, kind = _load(f"cpi_index_{currency.lower()}")
            log_change = _change(
                index_series, 12, log=True, staleness_days=QUARTERLY_STALENESS_DAYS
            )
            return (np.exp(log_change) - 1.0) * 100.0, kind
    return _load(f"{slot}_{currency.lower()}")


def _xs_z(frame: pd.DataFrame) -> pd.DataFrame:
    """日ごとの cross-section 標準化（3 通貨以上ある日だけ）。"""
    count = frame.notna().sum(axis=1)
    mean = frame.mean(axis=1)
    sd = frame.std(axis=1, ddof=0).replace(0.0, np.nan)
    out = frame.sub(mean, axis=0).div(sd, axis=0)
    out[count < MIN_CURRENCIES] = np.nan
    return out


# ----------------------------------------------------------------------
# M11 — macro data momentum（XS）
# ----------------------------------------------------------------------
def macro_momentum(
    index: pd.DatetimeIndex, overrides: dict[str, Any] | None = None
) -> pd.DataFrame:
    """s_c = xs_z(Δ インフレ) − xs_z(Δ 失業率)。**両方ある通貨だけ**が score を持つ。

    インフレの加速と失業率の低下が相対的に大きい通貨ほど高い（凍結した向き: 上昇）。
    """
    months = _nuisance("change_window_months", overrides)
    staleness = _nuisance("max_staleness_days_monthly", overrides)
    inflation = _monthly_panel("cpi", index, change_months=months, staleness=staleness)
    unemployment = _monthly_panel("unemployment", index, change_months=months, staleness=staleness)
    both = inflation.notna() & unemployment.notna()
    score = _xs_z(inflation.where(both)) - _xs_z(unemployment.where(both))
    return score


# ----------------------------------------------------------------------
# M16 — 米国と他国の macro momentum の差（DOLLAR）
# ----------------------------------------------------------------------
def _dollar_mu(sign: pd.Series, index: pd.DatetimeIndex) -> pd.DataFrame:
    """ドル factor の mu。USD に sign、他 7 通貨に −sign/7。sign が欠損の日は全通貨欠損。"""
    frame = pd.DataFrame(np.nan, index=index, columns=list(CURRENCIES))
    usable = sign.reindex(index)
    frame["USD"] = usable
    for currency in FOREIGN:
        frame[currency] = -usable / len(FOREIGN)
    return frame


def us_macro_momentum(
    index: pd.DatetimeIndex, overrides: dict[str, Any] | None = None
) -> pd.DataFrame:
    """M11 の score の **USD 成分の符号**でドルを持つ（米国の macro が相対的に強ければドル買い）。

    M11 の book は第 1 主成分を中立化するので、この成分を捨てている。M16 はその捨てた部分だけを測る。
    """
    score = macro_momentum(index, overrides)
    usd = score["USD"].where(score.notna().sum(axis=1) >= MIN_CURRENCIES + 1)
    return _dollar_mu(np.sign(usd), index)


# ----------------------------------------------------------------------
# M15 — dollar carry（DOLLAR）
# ----------------------------------------------------------------------
MIN_FOREIGN_RATES: Final[int] = 4


def dollar_carry(index: pd.DatetimeIndex, overrides: dict[str, Any] | None = None) -> pd.DataFrame:
    """d = 外国 3 か月金利の平均 − 米 3 か月金利。**d > 0 ならドル売り**（Lustig–Roussanov–Verdelhan）。"""
    staleness = _nuisance("max_staleness_days_monthly", overrides)
    rates = _monthly_panel("short_rate_3m", index, change_months=None, staleness=staleness)
    foreign = rates[list(FOREIGN)]
    enough = foreign.notna().sum(axis=1) >= MIN_FOREIGN_RATES
    differential = (foreign.mean(axis=1) - rates["USD"]).where(enough)
    return _dollar_mu(-np.sign(differential), index)


# ----------------------------------------------------------------------
# M10 — FX 流動性 premium（XS、recent span だけ）
# ----------------------------------------------------------------------
def _daily_relative_spread(path: Path) -> pd.Series:
    frame = pd.read_parquet(path, columns=["ts", "bid_c", "ask_c"])
    bid = frame["bid_c"].astype(float)
    ask = frame["ask_c"].astype(float)
    relative = (ask - bid) / ((ask + bid) / 2.0)
    stamp = pd.to_datetime(frame["ts"], utc=True)
    day = stamp.dt.tz_localize(None).dt.normalize()
    grouped = pd.DataFrame({"day": day, "rel": relative}).groupby("day")["rel"]
    daily = grouped.median()
    daily = daily[grouped.size() >= MIN_BARS_FOR_A_DAY]
    return daily[daily > 0]


def pair_spreads() -> pd.DataFrame:
    """3 つの guarded M15 cache から、pair ごとの日次の相対 spread（中央値）。"""
    per_pair: dict[str, list[pd.Series]] = {}
    for cache in M15_CACHES:
        directory = REPO_ROOT / "artifacts/track_a_scratch" / cache
        for path in sorted(directory.glob("m15_*.parquet")):
            pair = path.stem.removeprefix("m15_")
            if not set(pair.split("_")) <= set(CURRENCIES):
                continue
            per_pair.setdefault(pair, []).append(_daily_relative_spread(path))
    frame = pd.DataFrame(
        {pair: pd.concat(parts).groupby(level=0).last() for pair, parts in per_pair.items()}
    ).sort_index()
    frame = frame[[sources.is_seen(ts.date()) for ts in frame.index]]
    sources.assert_no_protected_day([ts.date() for ts in frame.index], label="m15_spreads")
    return frame


def liquidity(index: pd.DatetimeIndex, overrides: dict[str, Any] | None = None) -> pd.DataFrame:
    """L_c = 直近 short 日の平均 log 相対 spread − 直近 long 日の平均。**悪化した通貨を買う**（premium）。"""
    short = _nuisance("liquidity_short_window", overrides)
    long = _nuisance("liquidity_long_window", overrides)
    spreads = np.log(pair_spreads())
    currency = pd.DataFrame(index=spreads.index, columns=list(CURRENCIES), dtype=float)
    for c in CURRENCIES:
        legs = [col for col in spreads.columns if c in col.split("_")]
        if legs:
            currency[c] = spreads[legs].mean(axis=1)
    state = (
        currency.rolling(short, min_periods=short).mean()
        - currency.rolling(long, min_periods=long).mean()
    )
    state = state.shift(LIQUIDITY_LAG_BUSINESS_DAYS)
    out = state.sub(state.mean(axis=1), axis=0)
    return out.reindex(index)


SCORERS: Final[dict[str, Any]] = {
    "M15": dollar_carry,
    "M11": macro_momentum,
    "M16": us_macro_momentum,
    "M10": liquidity,
}
DOLLAR_TRACKS: Final[frozenset[str]] = frozenset({"M15", "M16"})


def scores_for(
    track: str,
    built: dict[str, Any],
    span: str,
    *,
    overrides: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """driver・感度・Stage 0 の唯一の入口（next-five の C-1 / C-6 と同じ規則）。"""
    index = built[span]["currency_excess_return"].index
    if track == "M10" and span == "long":
        raise SignalUnavailableError(
            "M10: 長 span には bid / ask の quote が無い（ECB 参照レートのみ）"
        )
    raw = SCORERS[track](index, overrides)
    raw = raw.loc[:, raw.notna().any()]
    if raw.empty:
        return raw.iloc[0:0]
    enough = raw.notna().sum(axis=1) >= MIN_CURRENCIES
    if not enough.any():
        return raw.iloc[0:0]
    first = index.get_loc(enough[enough].index[0])
    last = index.get_loc(enough[enough].index[-1])
    window = raw.reindex(index[first : last + 1])
    kept = window.notna().sum(axis=1) >= MIN_CURRENCIES
    if not kept.all():
        raise NonContiguousScoresError(
            f"{track}/{span}: 3 通貨未満の日が span の途中に {int((~kept).sum())} 日ある"
        )
    return window.fillna(0.0).reindex(columns=list(CURRENCIES), fill_value=0.0)


__all__ = [
    "CURRENCIES",
    "DOLLAR_TRACKS",
    "NUISANCE",
    "SCORERS",
    "NonContiguousScoresError",
    "SignalUnavailableError",
    "scores_for",
]
