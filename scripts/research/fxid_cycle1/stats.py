# ruff: noqa: E501 -- stats prose
"""R-A2: seen の M15 cache の signal を使わない統計。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**出すのは spread・vol（標準偏差）・高値と安値の幅の割合・pair 間の相関構造だけ。**
return の平均・方向・side 別の統計・損益は計算しない（test で固定）。読み取りは
`patsd_stage0.data.load_pair`（R-A の 3 route と、span・fresh の guard）だけを通す。
"""

from __future__ import annotations

import math
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.fxid_cycle1 import clock

FIRST: Final[str] = "2021-04-26"
LAST: Final[str] = "2025-12-28"
HOLDS_HOURS: Final[tuple[int, ...]] = (2, 4, 6, 8)
SLIPPAGE_BP: Final[float] = 0.5
BAR: Final[pd.Timedelta] = pd.Timedelta(minutes=15)


def _r(x: float, d: int = 4) -> float | None:
    return round(float(x), d) if x is not None and np.isfinite(x) else None


def prepare(m15: pd.DataFrame) -> pd.DataFrame:
    """M15 → 必要な列だけ。return は連続する bar の間だけ（gap をまたがない）。"""
    out = (
        pd.DataFrame(
            {
                "ts": pd.to_datetime(m15["ts"], utc=True),
                "mid_c": m15["mid_c"].astype(float),
                "range_rel": ((m15["mid_h"] - m15["mid_l"]) / m15["mid_c"]).astype(float),
                "spread_rel": (m15["spread_close_pips"] * m15["pip_size"] / m15["mid_c"]).astype(
                    float
                ),
            }
        )
        .sort_values("ts")
        .reset_index(drop=True)
    )
    log_mid = np.log(out["mid_c"])
    consecutive = out["ts"].diff() == BAR
    out["ret_for_std"] = log_mid.diff().where(consecutive)
    out["ny_hour"] = clock.ny_time(out["ts"]).dt.hour
    return out


def hourly_profile(frame: pd.DataFrame) -> dict[int, dict[str, Any]]:
    """NY 現地時刻の時ごと（DST に正しい）の spread の分布と vol（標準偏差）。"""
    out = {}
    for hour, group in frame.groupby("ny_hour"):
        spread = group["spread_rel"]
        out[int(hour)] = {
            "spread_bp_median": _r(spread.median() * 1e4, 3),
            "spread_bp_mean": _r(spread.mean() * 1e4, 3),
            "spread_bp_p90": _r(spread.quantile(0.9) * 1e4, 3),
            "vol_bp_std": _r(group["ret_for_std"].std(ddof=1) * 1e4, 3),
            "bars": int(len(group)),
        }
    return out


def _bar_closing_at(frame: pd.DataFrame, moments: pd.DatetimeIndex) -> pd.Series:
    """各時刻に終わる M15 bar（start = 時刻 − 15 分）の index。無ければ NaN。"""
    position = pd.Series(frame.index, index=frame["ts"])
    return position.reindex(moments - BAR)


def window_spreads(frame: pd.DataFrame, overall_median: float) -> dict[str, Any]:
    """各 anchor の ±15 分（anchor に終わる bar と、anchor から始まる bar）の spread。"""
    out = {}
    by_ts = frame.set_index("ts")["spread_rel"]
    for name in clock.ANCHORS:
        moments = clock.anchor_series(FIRST, LAST, name)
        values = pd.concat([by_ts.reindex(moments - BAR), by_ts.reindex(moments)]).dropna()
        out[name] = {
            "spread_bp_median": _r(values.median() * 1e4, 3),
            "spread_bp_mean": _r(values.mean() * 1e4, 3),
            "spread_bp_p90": _r(values.quantile(0.9) * 1e4, 3),
            "ratio_mean_to_overall_median": _r(values.mean() / overall_median, 3),
            "n": int(len(values)),
        }
    return out


def anchor_moves(frame: pd.DataFrame, name: str, hours: int) -> pd.Series:
    """anchor から hours 時間の log mid の変化（日ごと）。**大きさ（標準偏差）にだけ使う。**

    当日決済の規則に合わせ、決済が NY 16:45 を越える保有は除く。
    """
    moments = clock.anchor_series(FIRST, LAST, name)
    exits = moments + pd.Timedelta(hours=hours)
    exit_ny = exits.tz_convert(clock.NEW_YORK)
    entry_ny = moments.tz_convert(clock.NEW_YORK)
    same_day = ~(
        (entry_ny.hour < 17)
        & ((exit_ny.hour * 60 + exit_ny.minute > 16 * 60 + 45) | (exit_ny.date != entry_ny.date))
    )
    moments, exits = moments[same_day], exits[same_day]
    start = _bar_closing_at(frame, moments)
    end = _bar_closing_at(frame, exits)
    ok = start.notna().to_numpy() & end.notna().to_numpy()
    log_mid = np.log(frame["mid_c"].to_numpy())
    moves = log_mid[end.to_numpy()[ok].astype(int)] - log_mid[start.to_numpy()[ok].astype(int)]
    return pd.Series(moves, index=moments[ok])


def anchor_economics(frame: pd.DataFrame, windows: dict[str, Any]) -> dict[str, Any]:
    """anchor ごとの h 時間の σ（標準偏差）と、窓の spread（平均 + slippage）との比。"""
    out = {}
    for name in clock.ANCHORS:
        cost_bp = (windows[name]["spread_bp_mean"] or float("nan")) + SLIPPAGE_BP
        rows = {}
        for hours in HOLDS_HOURS:
            moves = anchor_moves(frame, name, hours)
            if len(moves) < 30:
                rows[str(hours)] = {"n": int(len(moves)), "excluded": "same_day_rule_or_too_few"}
                continue
            sigma_bp = float(moves.std(ddof=1)) * 1e4
            rows[str(hours)] = {
                "n": int(len(moves)),
                "sigma_bp": _r(sigma_bp, 3),
                "cost_bp_mean_plus_slip": _r(cost_bp, 3),
                "cost_to_sigma": _r(cost_bp / sigma_bp, 4),
            }
        out[name] = rows
    return out


def ambiguity_upper_bound(frame: pd.DataFrame, sigma_4h: float) -> dict[str, Any]:
    """**経路を使わない上限**: 高値 − 安値 ≥ 2w の M15 bar の割合（w = k × σ_4h）。"""
    out: dict[str, Any] = {"sigma_4h_bp": _r(sigma_4h * 1e4, 3)}
    for k in (0.25, 0.5, 1.0):
        width = 2 * k * sigma_4h
        hit = frame["range_rel"] >= width
        out[f"w={k}sigma4h"] = {
            "share_all_bars": _r(hit.mean(), 5),
            "share_by_ny_hour_max": _r(hit.groupby(frame["ny_hour"]).mean().max(), 5),
        }
    return out


def breadth(moves_by_pair: dict[str, pd.Series]) -> dict[str, Any]:
    """同じ日の pair 間の相関行列の固有値から、実効の breadth（participation ratio と 80% の成分数）。"""
    table = pd.DataFrame(moves_by_pair).dropna()
    if len(table) < 30:
        return {"days": int(len(table)), "status": "too_few"}
    corr = np.corrcoef(table.to_numpy().T)
    eig = np.sort(np.linalg.eigvalsh(corr))[::-1]
    share = np.cumsum(eig) / eig.sum()
    off = corr[np.triu_indices_from(corr, 1)]
    return {
        "days": int(len(table)),
        "pairs": int(table.shape[1]),
        "participation_ratio": _r(eig.sum() ** 2 / (eig**2).sum(), 3),
        "components_for_80pct": int(np.searchsorted(share, 0.8) + 1),
        "top_eigen_share": _r(eig[0] / eig.sum(), 4),
        "mean_abs_pair_corr": _r(float(np.abs(off).mean()), 4),
    }


def block_moves(frame: pd.DataFrame, hours: int) -> pd.Series:
    """無条件の比較用: UTC の重ならない hours 時間の block の log mid の変化（大きさと相関にだけ使う）。"""
    by_ts = frame.set_index("ts")["mid_c"]
    close = by_ts.index + BAR
    starts = by_ts.index[(close.hour % hours == 0) & (close.minute == 0)]
    ends = starts + pd.Timedelta(hours=hours)
    a = by_ts.reindex(starts).to_numpy()
    b = by_ts.reindex(ends).to_numpy()
    ok = np.isfinite(a) & np.isfinite(b)
    return pd.Series(np.log(b[ok]) - np.log(a[ok]), index=starts[ok])


def sigma_from_vol(bar_vol: float, hours: int) -> float:
    return bar_vol * math.sqrt(4 * hours)


__all__ = [
    "ambiguity_upper_bound",
    "anchor_economics",
    "anchor_moves",
    "block_moves",
    "breadth",
    "hourly_profile",
    "prepare",
    "window_spreads",
]
