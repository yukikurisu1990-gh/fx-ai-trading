# ruff: noqa: E501 -- signal prose
"""凍結した 5 本の signal を、凍結した定義のまま作る。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**この module は判断をしない。** 閾値も lookback も beta も `prereg` にあり、ここは
それを実行するだけである。値を選ぶ余地を持たせないのが目的で、そのために
定数はすべて `prereg` から読む。

**lag はすべて `panel.align_to_panel` を通す。** 外部値が同じ日の return 窓に
入る経路をこの module は持たない。
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd

from scripts.research.top_five import UNIVERSE, panel, prereg

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
DATA_DIR: Final[Path] = REPO_ROOT / "artifacts/track_a_scratch/top_five"

#: 標準化の窓。凍結文の「252 日で標準化」。
Z_WINDOW: Final[int] = 252

#: T1 / T2 の変化幅。凍結文の「5 日」。
SHOCK_LOOKBACK: Final[int] = 5

#: T3 の slope 変化幅。凍結文の「20 日」。
SLOPE_LOOKBACK: Final[int] = 20

#: T4 の窓。凍結文の「trailing 120 日 factor」「trailing 252 日 相関」。
FACTOR_WINDOW: Final[int] = 120
PARTNER_WINDOW: Final[int] = 252

#: T5 の z 窓。凍結文の「12 か月」。
TIC_WINDOW_MONTHS: Final[int] = 12


def _load(key: str) -> pd.Series:
    path = DATA_DIR / f"{key}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{key} は未取得である: {path}")
    frame = pd.read_parquet(path)
    return frame.iloc[:, 0]


def _trailing_z(series: pd.Series, window: int) -> pd.Series:
    """day t までの行だけで標準化する。**中心化窓は使わない。**"""
    mean = series.rolling(window, min_periods=window // 2).mean()
    sd = series.rolling(window, min_periods=window // 2).std(ddof=0)
    return (series - mean) / sd.replace(0.0, np.nan)


def _lag_for(source_key: str, span: str) -> int:
    row = prereg.PUBLICATION_TIMES[source_key]
    value = row[f"{span}_span_lag_business_days"]
    if not isinstance(value, int):
        raise TypeError(f"{source_key}/{span}: lag が営業日数でない（{value!r}）")
    return value


def _broadcast(score: pd.Series, beta: dict[str, float]) -> pd.DataFrame:
    """1 本の z を、凍結した beta で通貨へ配る。"""
    return pd.DataFrame({c: score * beta.get(c, 0.0) for c in UNIVERSE})


# ---------------------------------------------------------------------------
# T1 — cross-asset risk repricing
# ---------------------------------------------------------------------------


def t1_scores(index: pd.DatetimeIndex, span: str) -> pd.DataFrame:
    """`z` = 5 日 log(VIX) 変化の 252 日標準化。`mu = z * beta`。"""
    vix = _load("vix")
    shock = np.log(vix).diff(SHOCK_LOOKBACK)
    z = _trailing_z(shock, Z_WINDOW)
    aligned = panel.align_to_panel(z, index, lag=_lag_for("cboe_vix_close", span))
    return _broadcast(aligned, prereg.TRACKS["T1"]["direction"]["beta"])


# ---------------------------------------------------------------------------
# T2 — commodity terms of trade
# ---------------------------------------------------------------------------


def t2_scores(index: pd.DatetimeIndex, span: str) -> pd.DataFrame:
    """`z` = 5 日 log(WTI) return の 252 日標準化。T1 と同形、beta だけが違う。"""
    wti = _load("wti")
    shock = np.log(wti).diff(SHOCK_LOOKBACK)
    z = _trailing_z(shock, Z_WINDOW)
    aligned = panel.align_to_panel(z, index, lag=_lag_for("eia_wti_daily", span))
    return _broadcast(aligned, prereg.TRACKS["T2"]["direction"]["beta"])


# ---------------------------------------------------------------------------
# T3 — sovereign curve shape（符号は 2 本とも作る）
# ---------------------------------------------------------------------------

#: 凍結した 5 通貨と、その 10y / 2y の出どころ。
CURVE_LEGS: Final[dict[str, tuple[str, str]]] = {
    "USD": ("ust_10y", "usd_2y"),
    "EUR": ("bund_10y", "eur_2y"),
    "CAD": ("boc_10y", "cad_2y"),
    "CHF": ("snb_10y", "chf_2y"),
    "GBP": ("boe_10y", "gbp_2y"),
}

MARKET_YIELDS_DIR: Final[Path] = REPO_ROOT / "artifacts/track_a_scratch/market_yields"


def _two_year(currency: str) -> pd.Series:
    path = MARKET_YIELDS_DIR / f"{currency.lower()}_2y.parquet"
    frame = pd.read_parquet(path)
    column = frame.columns[-1]
    series = frame[column].astype(float)
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(frame.iloc[:, 0])
    return series.sort_index()


def t3_scores(index: pd.DatetimeIndex, span: str, *, hypothesis: str) -> pd.DataFrame:
    """`slope = 10y - 2y` の 20 日変化を 5 通貨 cross-section で rank して中心化。

    `hypothesis` は `"T3-H1"`（steepening -> 通貨高）か `"T3-H2"`（-> 通貨安）。
    **両方が事前登録されており、良かった方を後から選ぶことはしない。**
    """
    subs = prereg.TRACKS["T3"]["direction"]["sub_hypotheses"]
    if hypothesis not in subs:
        raise ValueError(f"未登録の sub-hypothesis: {hypothesis}")
    sign = 1.0 if hypothesis == "T3-H1" else -1.0

    lag = _lag_for("sovereign_curves", span)
    slopes = {}
    for currency, (long_key, _) in CURVE_LEGS.items():
        ten = _load(long_key)
        two = _two_year(currency)
        both = pd.concat([ten.rename("ten"), two.rename("two")], axis=1).sort_index().ffill()
        slope = (both["ten"] - both["two"]).dropna()
        change = slope.diff(SLOPE_LOOKBACK)
        slopes[currency] = panel.align_to_panel(change, index, lag=lag)

    frame = pd.DataFrame(slopes)
    ranked = frame.rank(axis=1, pct=True)
    centred = ranked.sub(ranked.mean(axis=1), axis=0)
    scores = pd.DataFrame(0.0, index=index, columns=list(UNIVERSE))
    for currency in CURVE_LEGS:
        scores[currency] = sign * centred[currency]
    #: cross-section を組めなかった日は建てない
    scores[frame.isna().all(axis=1)] = np.nan
    return scores


def t3_universe_width(index: pd.DatetimeIndex, span: str) -> pd.Series:
    """毎日、何通貨で cross-section を組んだか。凍結文が記録を求めている。"""
    lag = _lag_for("sovereign_curves", span)
    counts = {}
    for currency, (long_key, _) in CURVE_LEGS.items():
        ten = _load(long_key)
        two = _two_year(currency)
        both = pd.concat([ten.rename("ten"), two.rename("two")], axis=1).sort_index().ffill()
        slope = (both["ten"] - both["two"]).dropna().diff(SLOPE_LOOKBACK)
        counts[currency] = panel.align_to_panel(slope, index, lag=lag).notna()
    return pd.DataFrame(counts).sum(axis=1)


# ---------------------------------------------------------------------------
# T4 — currency-network propagation
# ---------------------------------------------------------------------------


def _residuals(excess: pd.DataFrame) -> pd.DataFrame:
    """trailing 120 日窓の leading factor を除いた残差。**centered 窓は使わない。**"""
    values = excess.to_numpy(dtype=float)
    out = np.full_like(values, np.nan)
    for row in range(FACTOR_WINDOW, len(values)):
        window = values[row - FACTOR_WINDOW : row]
        window = window[~np.isnan(window).any(axis=1)]
        if len(window) < FACTOR_WINDOW // 2:
            continue
        centred = window - window.mean(axis=0)
        _, _, vt = np.linalg.svd(centred, full_matrices=False)
        factor = vt[0]
        today = values[row]
        if np.isnan(today).any():
            continue
        out[row] = today - factor * float(today @ factor)
    return pd.DataFrame(out, index=excess.index, columns=excess.columns)


def t4_scores(excess: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`mu_i(t) = 残差_j(t)`。`j` は trailing 252 日で残差相関が最大の相手。

    返り値は (scores, residuals)。residuals は rename gate が使う。
    """
    residuals = _residuals(excess)
    scores = pd.DataFrame(np.nan, index=excess.index, columns=excess.columns)
    values = residuals.to_numpy(dtype=float)
    for row in range(FACTOR_WINDOW + PARTNER_WINDOW, len(values)):
        window = values[row - PARTNER_WINDOW : row]
        window = window[~np.isnan(window).any(axis=1)]
        if len(window) < PARTNER_WINDOW // 2:
            continue
        corr = np.corrcoef(window, rowvar=False)
        np.fill_diagonal(corr, -np.inf)
        partner = np.nanargmax(corr, axis=1)
        today = values[row]
        if np.isnan(today).any():
            continue
        scores.iloc[row] = today[partner]
    return scores, residuals


# ---------------------------------------------------------------------------
# T5 — international capital flow
# ---------------------------------------------------------------------------


def t5_scores(index: pd.DatetimeIndex) -> pd.DataFrame:
    """月次 TIC ネット買い越しの 12 か月 z。`mu_USD = +z`、他 7 通貨は `-z/7`。

    vintage: 第 `m` 月の値は `m+2` 月末以降にしか使わない。**月末で送る**ので、
    公表前の値が panel に載る経路が無い。
    """
    flow = _load("tic_s1")
    z = _trailing_z(flow, TIC_WINDOW_MONTHS)
    #: 観測月の月末 + 2 か月 = 使用開始日
    usable_from = (z.index + pd.offsets.MonthEnd(0) + pd.DateOffset(months=2)).normalize()
    shifted = pd.Series(z.to_numpy(), index=usable_from).sort_index()
    shifted = shifted[~shifted.index.duplicated(keep="last")]
    aligned = shifted.reindex(shifted.index.union(index)).sort_index().ffill().reindex(index)
    scores = pd.DataFrame(index=index, columns=list(UNIVERSE), dtype=float)
    others = [c for c in UNIVERSE if c != "USD"]
    scores["USD"] = aligned
    for currency in others:
        scores[currency] = -aligned / len(others)
    return scores


__all__ = [
    "CURVE_LEGS",
    "FACTOR_WINDOW",
    "PARTNER_WINDOW",
    "SHOCK_LOOKBACK",
    "SLOPE_LOOKBACK",
    "TIC_WINDOW_MONTHS",
    "Z_WINDOW",
    "t1_scores",
    "t2_scores",
    "t3_scores",
    "t3_universe_width",
    "t4_scores",
    "t5_scores",
]
