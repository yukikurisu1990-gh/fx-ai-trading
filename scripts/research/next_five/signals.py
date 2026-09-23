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

from scripts.research.next_five import corrections, prereg, series_map

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
DATA_DIR: Final[Path] = REPO_ROOT / "artifacts/track_a_scratch/next_five"

#: 通貨 → その通貨の series に使う接頭辞。
CURRENCIES: Final[tuple[str, ...]] = prereg.UNIVERSE

#: 1 日に必要な通貨数（凍結済みの breadth 規則）。**data 不足を理由に緩めない。**
MIN_CURRENCIES: Final[int] = 3


class NonContiguousScoresError(RuntimeError):
    """3 通貨以上の日が span の途中で途切れた（C-6）。

    `construction.run_book` は連続した decision day しか受け付けない。途切れた日を
    flat として残すか区間を分けるかは凍結文に無い判断なので、**どちらも選ばず fail-closed**
    で止め、その点を『計算不能』として記録する。
    """


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


#: 参照期間がここへ掛かる観測は使わない（POST_ALPHA_CORRECTION C-4）。
PROTECTED_REFERENCE_SPANS: Final[tuple[tuple[pd.Timestamp, pd.Timestamp], ...]] = (
    #: fresh pool
    (pd.Timestamp("2016-06-02"), pd.Timestamp("2021-04-26")),
    #: 最後の seen 日の翌日以降（development 末尾 2 日・historical OOS slice・forward epoch を含む。
    #: 保守側に広く取っている）
    (pd.Timestamp("2025-12-27"), pd.Timestamp.max.normalize()),
)


def _reference_period_is_protected(start: pd.Timestamp, end: pd.Timestamp) -> bool:
    return any(start <= hi and end >= lo for lo, hi in PROTECTED_REFERENCE_SPANS)


def _load(name: str, *, monthly: bool = False) -> pd.Series:
    """**外部 series を読む唯一の経路。**

    取得層が既に seen window へ切り落としたものだけを置いてある。
    ここで直接 URL を叩いたり、切り落とし前の frame を読んだりはしない。

    `monthly=True` の series は月初の日付で記録されている。取得層は **stamp の日付**で
    seen を判定したので、2016-06-01 stamp（2016 年 6 月の集計、参照期間は fresh pool）と
    2025-12-01 stamp（参照期間が forward epoch に掛かる）が残っている。
    **参照期間が保護期間に 1 日でも掛かる観測はここで落とす**（C-4）。
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
    series = series.sort_index().dropna()
    if monthly:
        periods = series.index.to_period("M")
        keep = [
            not _reference_period_is_protected(p.start_time.normalize(), p.end_time.normalize())
            for p in periods
        ]
        series = series[np.array(keep, dtype=bool)]
        if series.empty:
            raise SignalUnavailableError(f"{name} は保護期間を除くと空である")
    return series


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
    #: 欠損の行を観測として扱わない（C-2 の追補）。残すと `vintage` は欠損行の日付を
    #: 観測日として拾い、`filled` は欠損を飛ばして古い値を運ぶので、staleness 検査が
    #: 何年も前の値を通してしまう
    shifted = series.dropna().copy()
    if vintage_offset_months:
        #: 第 m 月の値を **m+k 月の月末**に置く（C-3）。初版は月末に `DateOffset(months=k)` を
        #: 足しており、2 月末 + 2 か月が 4 月 28 日になるなど 1〜3 日早く着地していた
        shifted.index = (
            (shifted.index.to_period("M") + vintage_offset_months)
            .to_timestamp(how="end")
            .normalize()
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


def _change(
    series: pd.Series, months: int, *, log: bool = False, staleness_days: int = 75
) -> pd.Series:
    """**n か月前の時点で観測されていた値**との差（FREEZE_AMENDMENT_PLUMBING の P-3）。

    初版は `shift(months)`、つまり「n 期前」を取っていた。週次 series では 12 期前が
    12 週前になり、凍結文の「12 か月変化」と一致しなかった。

    **基準値も staleness 規則に従う**（C-2）。n か月前の時点で最後に観測されていた値が
    `staleness_days` 暦日より古ければ欠損にする。これが無いと、保護 pool の空白を跨いで
    2016 年の値を基準に取り、「12 か月変化」が約 5 年変化になっていた。
    """
    base = np.log(series.where(series > 0)) if log else series.astype(float)
    base = base.dropna().sort_index()
    if base.empty:
        return base
    targets = base.index - pd.DateOffset(months=months)
    union = base.index.union(targets)
    past = base.reindex(union).sort_index().ffill().reindex(targets)
    observed_at = (
        pd.Series(base.index, index=base.index).reindex(union).sort_index().ffill().reindex(targets)
    )
    age = (pd.Series(targets, index=targets) - observed_at).dt.days
    past[(age > staleness_days).to_numpy()] = np.nan
    #: 最初の観測より前を指したら欠損（外挿しない）
    past[targets < base.index[0]] = np.nan
    return pd.Series(base.to_numpy() - past.to_numpy(), index=base.index)


def _mapping(track: str, currency: str) -> dict[str, Any]:
    """対応表に無い通貨は **取得できなかった** のであって、機構の否定ではない。"""
    row = series_map.SERIES_MAP.get(track, {}).get(currency)
    if row is None:
        raise SignalUnavailableError(f"{track} の {currency} は対応表に無い（NOT_MAPPED）")
    return row


def _is_monthly(track: str, currency: str) -> bool:
    return _mapping(track, currency)["lag"]["kind"] == "month_end_offset"


def _lag_kwargs(track: str, currency: str) -> dict[str, int]:
    """series ごとの公表 lag（series_map に凍結）。**月次は m+k 月末、週次・日次は n 営業日。**

    `corrections.LAG_CORRECTIONS` にある series は、凍結文（「公表日の 2 営業日後」）どおりの
    lag へ直したものを使う（C-5）。凍結済みの series_map 自体は書き換えない。
    """
    lag = corrections.LAG_CORRECTIONS.get((track, currency), _mapping(track, currency)["lag"])
    if lag["kind"] == "month_end_offset":
        return {"vintage_offset_months": int(lag["months"])}
    return {"lag_business_days": int(lag["n"])}


# ----------------------------------------------------------------------
# U1 / S29 — 実体貿易 flow
# ----------------------------------------------------------------------
def u1_scores(index: pd.DatetimeIndex, overrides: dict[str, Any] | None = None) -> pd.DataFrame:
    months = _nuisance("change_window_months", overrides)
    window = _nuisance("z_window", overrides)
    staleness = _nuisance("max_staleness_days", overrides)

    def getter(currency: str) -> pd.Series:
        raw = _load(f"trade_{currency.lower()}", monthly=_is_monthly("U1", currency))
        changed = _change(raw, months, staleness_days=staleness)
        aligned = _align(changed, index, staleness_days=staleness, **_lag_kwargs("U1", currency))
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
        raw = _load(f"balance_sheet_{currency.lower()}", monthly=_is_monthly("U2", currency))
        changed = _change(raw, months, log=True, staleness_days=staleness)
        aligned = _align(changed, index, staleness_days=staleness, **_lag_kwargs("U2", currency))
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
        raw = _load(f"reserves_{currency.lower()}", monthly=_is_monthly("U4", currency))
        #: 凍結どおり **3 か月変化**（`change_window_months` とは別の、機構側の定数）
        changed = _change(raw, 3, log=True, staleness_days=staleness)
        aligned = _align(changed, index, staleness_days=staleness, **_lag_kwargs("U4", currency))
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
    """driver と感度測定が使う唯一の入口。**連続化規則もここで 1 つに固定する。**

    FREEZE_AMENDMENT_PLUMBING の P-6: 初版は `dropna(how="any")` で、**1 通貨でも欠けた日を
    落としていた**。mapping できない通貨（例: U2 の GBP）の列は全期間が欠けるので、
    全日が消えていた。ここでは

    1. その span で観測が 1 つも無い通貨の列を外し、
    2. **1 日に 3 通貨以上**の score がある日だけを残し（凍結済みの breadth 規則）、
    3. その日に欠けている通貨は **0（建玉を持たない）** とする。
    """
    index = built[span]["currency_excess_return"].index
    raw = SCORERS[track](index, overrides)
    raw = raw.loc[:, raw.notna().any()]
    if raw.empty:
        #: 0 列 x 全日の frame を返すと、呼び出し側の len() が「使える日」を数え違える（O-3）
        return raw.iloc[0:0]
    enough = raw.notna().sum(axis=1) >= MIN_CURRENCIES
    if not enough.any():
        return raw.iloc[0:0]
    first = index.get_loc(enough[enough].index[0])
    last = index.get_loc(enough[enough].index[-1])
    contiguous = index[first : last + 1]
    #: **ffill しない**（C-1）。初版はここで上限なく前方補完し、`_align` の staleness 規則と
    #: P-6（欠けた通貨は 0）を無効にしていた — U1 の EUR は系列終了後 685 日持ち越されていた
    window = raw.reindex(contiguous)
    kept = window.notna().sum(axis=1) >= MIN_CURRENCIES
    if not kept.all():
        gaps = int((~kept).sum())
        raise NonContiguousScoresError(
            f"{track}/{span}: 3 通貨未満の日が span の途中に {gaps} 日ある（C-6）"
        )
    return window.fillna(0.0).reindex(columns=list(CURRENCIES), fill_value=0.0)


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
