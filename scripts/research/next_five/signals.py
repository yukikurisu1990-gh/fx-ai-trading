# ruff: noqa: E501 -- signal prose
"""凍結した 5 本の signal（2026-09-22 裁定 §J の `signal` / `direction` / `horizon`）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**Stage 1 は fixed / unfitted rule だけ。** 当てはめも学習もしない。

前 cycle の事故をここで構造的に塞ぐ:

- **外部 series を読む経路は `_load` 1 本に強制する。** parquet を直読みする関数を作らない。
  前 cycle は `_two_year` が取得層を迂回し、保護 pool の行が signal へ入った（C-1）。
- **staleness は暦日で数える。** 行数で数えると、union index に空白があると
  1 行で何年でも跨ぐ（前 cycle は 1 行で 1,792 日跨いでいた）。
- **nuisance 定数は override できるが、既定は必ず凍結値。** 感度報告のためだけに開ける。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.next_five import prereg

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
DATA_DIR: Final[Path] = REPO_ROOT / "artifacts/track_a_scratch/next_five"

#: 通貨 → その通貨の series に使う接頭辞。
CURRENCIES: Final[tuple[str, ...]] = prereg.UNIVERSE


class SignalUnavailableError(RuntimeError):
    """その track の signal を作るだけの data が揃っていない。

    **これは『機構が否定された』ではない。** 取得できなかっただけである。
    前 cycle で S07 を不達と不在の取り違えで退場させかけた記録があるので、
    例外の型で区別できるようにしてある。
    """


def _nuisance(name: str, overrides: dict[str, Any] | None) -> Any:
    """凍結値を既定とし、感度報告のときだけ override を許す。"""
    value = prereg.NUISANCE_CONSTANTS[name]["primary"]
    if overrides and name in overrides:
        allowed = prereg.NUISANCE_CONSTANTS[name]["sensitivity_set"]
        if overrides[name] not in allowed:
            raise ValueError(
                f"{name}={overrides[name]} は凍結した感度集合 {allowed} の外にある。"
                "集合の外の値を試すことは事前登録の外である"
            )
        value = overrides[name]
    return value


def _load(name: str) -> pd.Series:
    """**外部 series を読む唯一の経路。**

    取得層が既に seen window へ切り落としたものだけを置いてある。
    ここで直接 URL を叩いたり、切り落とし前の frame を読んだりはしない。
    """
    path = DATA_DIR / f"{name}.parquet"
    if not path.exists():
        raise SignalUnavailableError(f"{name} が取得されていない（{path.name} が無い）")
    frame = pd.read_parquet(path)
    if frame.empty:
        raise SignalUnavailableError(f"{name} は空である")
    column = frame.columns[-1]
    series = frame[column].astype(float)
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(frame.iloc[:, 0])
    return series.sort_index().dropna()


def _align(
    series: pd.Series,
    index: pd.DatetimeIndex,
    *,
    lag_business_days: int = 0,
    vintage_offset_months: int = 0,
    staleness_days: int = 75,
) -> pd.Series:
    """公表タイミングを守って日次 index へ載せる。**暦日で staleness を数える。**

    `vintage_offset_months` は「第 m 月の値は m+k 月末以降にのみ使う」という規約。
    `lag_business_days` は日次 series 用（公表の n 営業日後から使う）。
    """
    shifted = series.copy()
    if vintage_offset_months:
        shifted.index = shifted.index.to_period("M").to_timestamp("M") + pd.DateOffset(
            months=vintage_offset_months
        )
    if lag_business_days:
        shifted.index = shifted.index + pd.offsets.BDay(lag_business_days)
    shifted = shifted[~shifted.index.duplicated(keep="last")].sort_index()

    union = shifted.index.union(index)
    filled = shifted.reindex(union).sort_index().ffill()
    vintage = pd.Series(shifted.index, index=shifted.index).reindex(union).sort_index().ffill()
    age = (pd.Series(union, index=union) - vintage).dt.days
    filled[age > staleness_days] = np.nan
    return filled.reindex(index)


def _z(series: pd.Series, window: int) -> pd.Series:
    mean = series.rolling(window, min_periods=window // 2).mean()
    sd = series.rolling(window, min_periods=window // 2).std(ddof=0)
    return (series - mean) / sd.replace(0.0, np.nan)


def _cross_section(frame: pd.DataFrame) -> pd.DataFrame:
    """cross-section で相対化する。**水準ではなく相対が signal である。**"""
    return frame.sub(frame.mean(axis=1), axis=0)


def _panel_from_currency_series(getter, index: pd.DatetimeIndex, *, label: str) -> pd.DataFrame:
    """通貨ごとの series を集めて panel にする。**1 通貨も揃わなければ落とす。**"""
    columns: dict[str, pd.Series] = {}
    missing: list[str] = []
    for currency in CURRENCIES:
        try:
            columns[currency] = getter(currency)
        except SignalUnavailableError:
            missing.append(currency)
    if len(columns) < 3:
        raise SignalUnavailableError(
            f"{label}: cross-section が 3 通貨に満たない（欠け: {', '.join(missing)}）"
        )
    frame = pd.DataFrame(columns, index=index)
    return frame.reindex(columns=list(CURRENCIES))


def _change(series: pd.Series, months: int, *, log: bool = False) -> pd.Series:
    """低頻度 series の変化。月次 index 前提で `months` 期前との差を取る。"""
    base = np.log(series.where(series > 0)) if log else series
    return base - base.shift(months)


# ----------------------------------------------------------------------
# U1 / S29 — 実体貿易 flow
# ----------------------------------------------------------------------
def u1_scores(index: pd.DatetimeIndex, overrides: dict[str, Any] | None = None) -> pd.DataFrame:
    months = _nuisance("change_window_months", overrides)
    window = _nuisance("z_window", overrides)
    staleness = _nuisance("max_staleness_days", overrides)

    def getter(currency: str) -> pd.Series:
        raw = _load(f"trade_{currency.lower()}")
        changed = _change(raw, months)
        aligned = _align(changed, index, vintage_offset_months=2, staleness_days=staleness)
        return _z(aligned, window)

    #: 貿易収支が改善した通貨は上昇（凍結した向き）。
    return _cross_section(_panel_from_currency_series(getter, index, label="U1 貿易収支"))


# ----------------------------------------------------------------------
# U2 / S25 — 中銀 balance sheet
# ----------------------------------------------------------------------
def u2_scores(index: pd.DatetimeIndex, overrides: dict[str, Any] | None = None) -> pd.DataFrame:
    months = _nuisance("change_window_months", overrides)
    window = _nuisance("z_window", overrides)
    staleness = _nuisance("max_staleness_days", overrides)

    def getter(currency: str) -> pd.Series:
        raw = _load(f"balance_sheet_{currency.lower()}")
        changed = _change(raw, months, log=True)
        aligned = _align(changed, index, lag_business_days=2, staleness_days=staleness)
        return _z(aligned, window)

    #: 相対的に速く拡大した通貨は下落 → 符号を反転する（凍結した向き）。
    return -_cross_section(_panel_from_currency_series(getter, index, label="U2 balance sheet"))


# ----------------------------------------------------------------------
# U3 / S27 — 中銀 communication の tone
# ----------------------------------------------------------------------
def u3_scores(index: pd.DatetimeIndex, overrides: dict[str, Any] | None = None) -> pd.DataFrame:
    window = _nuisance("z_window", overrides)
    staleness = _nuisance("max_staleness_days", overrides)

    def getter(currency: str) -> pd.Series:
        raw = _load(f"tone_{currency.lower()}")
        changed = raw - raw.shift(1)
        aligned = _align(changed, index, lag_business_days=1, staleness_days=staleness)
        return _z(aligned, window)

    #: hawkish 側へ動いた通貨は上昇（凍結した向き）。
    return _cross_section(_panel_from_currency_series(getter, index, label="U3 tone"))


# ----------------------------------------------------------------------
# U4 / S31 — 公的外貨準備
# ----------------------------------------------------------------------
def u4_scores(index: pd.DatetimeIndex, overrides: dict[str, Any] | None = None) -> pd.DataFrame:
    window = _nuisance("z_window", overrides)
    staleness = _nuisance("max_staleness_days", overrides)

    def getter(currency: str) -> pd.Series:
        raw = _load(f"reserves_{currency.lower()}")
        #: 凍結どおり **3 か月変化**（`change_window_months` とは別の、機構側の定数）
        changed = _change(raw, 3, log=True)
        aligned = _align(changed, index, vintage_offset_months=1, staleness_days=staleness)
        return _z(aligned, window)

    #: 準備を積み増した通貨は下落（自国通貨を売っている）→ 符号を反転する。
    return -_cross_section(_panel_from_currency_series(getter, index, label="U4 外貨準備"))


# ----------------------------------------------------------------------
# U5 / S07 — 信用 spread
# ----------------------------------------------------------------------
def _broadcast(score: pd.Series, beta: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame({c: score * beta.get(c, 0.0) for c in CURRENCIES}, index=score.index)


def u5_scores(index: pd.DatetimeIndex, overrides: dict[str, Any] | None = None) -> pd.DataFrame:
    window = _nuisance("z_window", overrides)
    staleness = _nuisance("max_staleness_days", overrides)

    raw = _load("credit_hy_oas")
    #: 凍結どおり **5 日変化**（機構側の定数で、nuisance ではない）
    changed = raw - raw.shift(5)
    aligned = _align(changed, index, lag_business_days=2, staleness_days=staleness)
    score = _z(aligned, window)
    beta = prereg.TRACKS["U5"]["direction"]["beta"]
    return _cross_section(_broadcast(score.dropna(), beta).reindex(index))


SCORERS: Final[dict[str, Any]] = {
    "U1": u1_scores,
    "U2": u2_scores,
    "U3": u3_scores,
    "U4": u4_scores,
    "U5": u5_scores,
}


def scores_for(
    track: str,
    built: dict[str, Any],
    span: str,
    *,
    overrides: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """driver と感度測定が使う唯一の入口。**連続化規則もここで 1 つに固定する。**"""
    index = built[span]["currency_excess_return"].index
    raw = SCORERS[track](index, overrides)
    seeded = raw.dropna(how="any")
    if seeded.empty:
        return seeded
    first = index.get_loc(seeded.index[0])
    last = index.get_loc(seeded.index[-1])
    contiguous = index[first : last + 1]
    return raw.reindex(contiguous).ffill().dropna(how="any")


__all__ = [
    "CURRENCIES",
    "DATA_DIR",
    "SCORERS",
    "SignalUnavailableError",
    "scores_for",
    "u1_scores",
    "u2_scores",
    "u3_scores",
    "u4_scores",
    "u5_scores",
]
