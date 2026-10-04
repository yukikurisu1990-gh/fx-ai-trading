# ruff: noqa: E501 -- research prose
"""R-A2b: NY の entry 時刻の signal-free の経済性（事前登録 `docs/research/fxid_ny_followup_preregistration_2026_10.md`）。

`POST_HOC_EXPLORATORY_FOLLOW_UP` · `NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

方向・side・return の平均・損益は計算しない。return（log mid の変化）は標準偏差と相関にだけ使う。
"""

from __future__ import annotations

import math
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.fxid_cycle1 import clock, stats

#: 事前登録 §2（固定）。name -> (hour, minute) in America/New_York
PRIMARY: Final[dict[str, tuple[int, int]]] = {
    "ny_0900": (9, 0),
    "ny_0930": (9, 30),
    "ny_1000": (10, 0),
}
BASELINE: Final[dict[str, tuple[int, int]]] = {"ny_0800": (8, 0)}
HOLD: Final[pd.Timedelta] = pd.Timedelta(hours=4)
BAR: Final[pd.Timedelta] = stats.BAR
EXIT_LAST_NY_MINUTE: Final[int] = 16 * 60 + 45

#: 事前登録 §3–§5
S_TARGET: Final[float] = 1.0
THRESHOLD: Final[float] = 0.15
BOUNDARY: Final[float] = 0.005
K_BASE: Final[int] = 3
N_BASE: Final[int] = 100
SLIP_BASE_BP: Final[float] = 0.5
K_GRID: Final[tuple[int, ...]] = (2, 3, 5)
N_GRID: Final[tuple[int, ...]] = (50, 100, 200)
SLIP_GRID_BP: Final[tuple[float, ...]] = (0.5, 1.0)
METHODS: Final[tuple[str, ...]] = ("entry_exit_half", "cycle1_entry_window")


def ny_moments(first: str, last: str, hour: int, minute: int) -> pd.DatetimeIndex:
    """first … last の NY 現地の平日の hour:minute を UTC で（夏時間は時刻帯の規則で）。"""
    days = pd.date_range(first, last, freq="D")
    out = [
        pd.Timestamp(
            year=d.year, month=d.month, day=d.day, hour=hour, minute=minute, tz=clock.NEW_YORK
        ).tz_convert("UTC")
        for d in days
        if d.dayofweek < 5
    ]
    return pd.DatetimeIndex(out)


def same_day_exit(moments: pd.DatetimeIndex) -> np.ndarray:
    """決済（+4 時間）が同じ NY の日付で 16:45 以前か。"""
    entry = moments.tz_convert(clock.NEW_YORK)
    exit_ = (moments + HOLD).tz_convert(clock.NEW_YORK)
    minute = exit_.hour * 60 + exit_.minute
    return np.asarray((minute <= EXIT_LAST_NY_MINUTE) & (exit_.date == entry.date))


def _closing_at(frame: pd.DataFrame, moments: pd.DatetimeIndex) -> np.ndarray:
    """時刻に終わる M15 bar の index（無ければ -1）。"""
    position = pd.Series(frame.index, index=frame["ts"]).reindex(moments - BAR)
    return position.fillna(-1).to_numpy().astype(int)


def anchor_table(frame: pd.DataFrame, hour: int, minute: int) -> dict[str, Any]:
    """1 pair × 1 評価時刻の spread・σ_4h（事前登録 §3）。"""
    moments = ny_moments(stats.FIRST, stats.LAST, hour, minute)
    moments = moments[same_day_exit(moments)]
    i0 = _closing_at(frame, moments)
    i1 = _closing_at(frame, moments + HOLD)
    i_post = _closing_at(frame, moments + BAR)
    ok = (i0 >= 0) & (i1 >= 0)
    spread = frame["spread_rel"].to_numpy()
    log_mid = np.log(frame["mid_c"].to_numpy())
    s_entry = spread[i0[ok]]
    s_exit = spread[i1[ok]]
    moves = log_mid[i1[ok]] - log_mid[i0[ok]]
    # Cycle 1 の方式: T と T + 15 分の snapshot の spread を（全日について）まとめた平均
    window = np.concatenate([spread[i0[i0 >= 0]], spread[i_post[i_post >= 0]]])
    post = spread[i_post[i_post >= 0]]
    return {
        "days": int(ok.sum()),
        "sigma_4h_bp": float(np.std(moves, ddof=1)) * 1e4,
        "entry_spread_bp": float(np.mean(s_entry)) * 1e4,
        "exit_spread_bp": float(np.mean(s_exit)) * 1e4,
        "post_entry_spread_bp": float(np.mean(post)) * 1e4,
        "rt_half_spread_bp": float(np.mean((s_entry + s_exit) / 2)) * 1e4,
        "cycle1_window_spread_bp": float(np.mean(window)) * 1e4,
        "_moves": pd.Series(moves, index=moments[ok]),
    }


def required_gross_to_sigma(
    cost_bp: float, sigma_bp: float, k: int, n: int, slip_bp: float
) -> float:
    """必要 gross / σ = (cost + slippage) / σ + S / √(k · n)（Cycle 1 と同じ式）。"""
    return (cost_bp + slip_bp) / sigma_bp + S_TARGET / math.sqrt(k * n)


def cost_bp(row: dict[str, Any], method: str) -> float:
    if method == "entry_exit_half":
        return float(row["rt_half_spread_bp"])
    if method == "cycle1_entry_window":
        return float(row["cycle1_window_spread_bp"])
    raise ValueError(method)


def classify(medians: dict[str, float]) -> str:
    within = sum(v <= THRESHOLD for v in medians.values())
    if within == len(PRIMARY):
        return "R_A2B_ECON_ALL_THREE"
    if within == 0:
        return "R_A2B_ECON_NONE"
    return "R_A2B_ECON_PARTIAL"


def evaluate(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    anchors = {**PRIMARY, **BASELINE}
    rows: dict[str, dict[str, dict[str, Any]]] = {a: {} for a in anchors}
    for pair, frame in frames.items():
        for name, (h, m) in anchors.items():
            rows[name][pair] = anchor_table(frame, h, m)

    out: dict[str, Any] = {"per_anchor": {}}
    primary_medians: dict[str, float] = {}
    for name, per_pair in rows.items():
        req = {
            p: required_gross_to_sigma(
                cost_bp(r, "entry_exit_half"), r["sigma_4h_bp"], K_BASE, N_BASE, SLIP_BASE_BP
            )
            for p, r in per_pair.items()
        }
        values = np.array(list(req.values()))
        median = float(np.median(values))
        if name in PRIMARY:
            primary_medians[name] = median
        sensitivity = {}
        for method in METHODS:
            for slip in SLIP_GRID_BP:
                for k in K_GRID:
                    for n in N_GRID:
                        v = np.array(
                            [
                                required_gross_to_sigma(
                                    cost_bp(r, method), r["sigma_4h_bp"], k, n, slip
                                )
                                for r in per_pair.values()
                            ]
                        )
                        sensitivity[f"{method}|slip={slip}|k={k}|n={n}"] = {
                            "median": round(float(np.median(v)), 4),
                            "pairs_within": int((v <= THRESHOLD).sum()),
                        }
        out["per_anchor"][name] = {
            "role": "primary" if name in PRIMARY else "baseline",
            "primary_median_required_gross_to_sigma": round(median, 4),
            "verdict": "ECON_WITHIN_15PCT" if median <= THRESHOLD else "ECON_EXCEEDS_15PCT",
            "distribution": {
                q: round(float(np.quantile(values, x)), 4)
                for q, x in (("min", 0), ("q25", 0.25), ("median", 0.5), ("q75", 0.75), ("max", 1))
            },
            "pairs_within": int((values <= THRESHOLD).sum()),
            "pairs_boundary": sorted(p for p, v in req.items() if abs(v - THRESHOLD) <= BOUNDARY),
            "median_cycle1_method_cost_to_sigma": round(
                float(
                    np.median(
                        [
                            (r["cycle1_window_spread_bp"] + SLIP_BASE_BP) / r["sigma_4h_bp"]
                            for r in per_pair.values()
                        ]
                    )
                ),
                4,
            ),
            "per_pair": {
                p: {
                    **{
                        k: (round(v, 4) if isinstance(v, float) else v)
                        for k, v in r.items()
                        if not k.startswith("_")
                    },
                    "cost_to_sigma_primary": round(
                        (r["rt_half_spread_bp"] + SLIP_BASE_BP) / r["sigma_4h_bp"], 4
                    ),
                    "required_gross_to_sigma_primary": round(req[p], 4),
                }
                for p, r in per_pair.items()
            },
            "sensitivity": sensitivity,
            "breadth": stats.breadth({p: r["_moves"] for p, r in per_pair.items()}),
        }
    out["overall"] = classify(primary_medians)
    return out


__all__ = [
    "BASELINE",
    "PRIMARY",
    "THRESHOLD",
    "anchor_table",
    "classify",
    "evaluate",
    "ny_moments",
    "required_gross_to_sigma",
    "same_day_exit",
]
