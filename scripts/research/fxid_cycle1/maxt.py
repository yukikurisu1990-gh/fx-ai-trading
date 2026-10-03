# ruff: noqa: E501 -- max-T prose
"""max-T の帰無較正の**技術検証**（Cycle 1）。実戦略の閾値は決めない。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

- **合成 data（主）**: seen の M15 mid の log return に、時点ごとに**全 pair 共通の ±1** を掛ける
  （vol の塊・pair 間の相関・大きさを保ち、方向を壊す）。実際の return の符号と position は対応しない。
- **合成 data（感度）**: 正規分布の return。pair × NY 時刻の vol と、pair 間の相関だけを seen から取る（実際の経路は使わない）。
- **候補は signal を持たない置き換えだけ**: ランダムな時刻（NY 03:00〜12:45 の M15 の終値）・ランダムな side・
  事前固定の保有（2 / 4 / 6 / 8 時間）・当日決済。S1 / S2 は実装しない。
- 帰無の分布 = 候補の**gross**（cost 前）の年率 Sharpe（日次）の最大値。帰無は「情報が無い」なので、閾値は gross の帰無から作る。
  **Cycle 2 での使い方の提案**（凍結しない）: 各候補の **net** の Sharpe をこの閾値と比べる（net の平均 ≤ 0 の最も不利な点での検定）。
  gross で選んでから net を見ると、cost に弱い候補を選ぶ bias が残る（報告 §9）。（run 1 は net を使い、候補の cost で帰無の中心が −2.5 前後にずれて、等価試行数と検出力が意味を失った）。各 replication の候補の最大値を記録し、
  閾値 = 帰無の最大値の 90 percentile（較正）、別の replication で family-wise 誤合格率を検証する。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Final

import numpy as np
import pandas as pd
from scipy.stats import beta, norm

from scripts.research.fxid_cycle1 import clock

TARGET_FWER: Final[float] = 0.10
SEED: Final[int] = 20261003
HOLDS_BARS: Final[tuple[int, ...]] = (8, 16, 24, 32)
ENTRY_NY_FIRST: Final[int] = 3 * 60
ENTRY_NY_LAST: Final[int] = 12 * 60 + 45
EXIT_NY_LAST: Final[int] = 16 * 60 + 45


@dataclass
class Grid:
    returns: np.ndarray  #: (T, P) 連続する bar の間だけの log return（gap は 0）。合成にだけ使う
    day: np.ndarray  #: (T,) 取引日の番号
    n_days: int
    ny_minute: np.ndarray  #: (T,) bar の終値の NY 現地時刻（分）
    sigma_bar: np.ndarray  #: (P,)
    cost: np.ndarray  #: (P,) round trip（return 単位）
    years: float


def build_grid(frames: dict[str, pd.DataFrame], cost: dict[str, float]) -> Grid:
    pairs = sorted(frames)
    index = pd.DatetimeIndex(sorted(set().union(*[set(f["ts"]) for f in frames.values()])))
    returns = np.zeros((len(index), len(pairs)))
    for j, pair in enumerate(pairs):
        series = frames[pair].set_index("ts")["ret_for_std"].reindex(index)
        returns[:, j] = series.fillna(0.0).to_numpy()
    close = index + pd.Timedelta(minutes=15)
    ny = close.tz_convert(clock.NEW_YORK)
    tday = clock.trading_day(pd.Series(index))
    codes, uniques = pd.factorize(tday)
    years = (index[-1] - index[0]).days / 365.25
    return Grid(
        returns=returns,
        day=codes,
        n_days=len(uniques),
        ny_minute=np.asarray(ny.hour * 60 + ny.minute),
        sigma_bar=returns.std(axis=0, ddof=1),
        cost=np.array([cost[p] for p in pairs]),
        years=years,
    )


@dataclass
class Candidate:
    t0: np.ndarray
    t1: np.ndarray
    pair: np.ndarray
    side: np.ndarray
    day: np.ndarray


def make_candidates(
    grid: Grid, n: int, *, seed: int, entries_per_day_per_pair: float = 0.5
) -> list[Candidate]:
    """signal を持たない置き換えの候補。**return を見ない**（時刻・side・保有は seed だけで決まる）。"""
    rng = np.random.default_rng([SEED, seed])
    eligible = (grid.ny_minute >= ENTRY_NY_FIRST) & (grid.ny_minute <= ENTRY_NY_LAST)
    bars_per_day = max(eligible.sum() / grid.n_days, 1.0)
    p = entries_per_day_per_pair / bars_per_day
    out = []
    n_bars, n_pairs = grid.returns.shape
    for k in range(n):
        hold = HOLDS_BARS[k % len(HOLDS_BARS)]
        mask = (rng.random((n_bars, n_pairs)) < p) & eligible[:, None]
        t0, pair = np.nonzero(mask)
        t1 = t0 + hold
        keep = t1 < n_bars
        t0, pair, t1 = t0[keep], pair[keep], t1[keep]
        same_day = (grid.day[t1] == grid.day[t0]) & (grid.ny_minute[t1] <= EXIT_NY_LAST)
        t0, pair, t1 = t0[same_day], pair[same_day], t1[same_day]
        side = rng.choice(np.array([-1.0, 1.0]), size=len(t0))
        out.append(Candidate(t0=t0, t1=t1, pair=pair, side=side, day=grid.day[t0]))
    return out


def synthetic_sign(grid: Grid, rng: np.random.Generator) -> np.ndarray:
    """主の合成: 時点ごとに全 pair 共通の ±1。"""
    signs = rng.choice(np.array([-1.0, 1.0]), size=grid.returns.shape[0])
    return grid.returns * signs[:, None]


def synthetic_gaussian(
    grid: Grid, rng: np.random.Generator, chol: np.ndarray, hour_scale: np.ndarray
) -> np.ndarray:
    """感度の合成: 相関（chol）と NY 時刻の vol の形（hour_scale: (T, P)）を持つ正規分布。"""
    z = rng.standard_normal(grid.returns.shape) @ chol.T
    return z * hour_scale


def candidate_sharpes(
    grid: Grid, returns: np.ndarray, candidates: list[Candidate], *, cost_multiple: float = 1.0
) -> np.ndarray:
    # 実価格の return（無作為化していないもの）に候補の向きを掛けることを拒否する（R-A2 / 裁定 §23）。
    if np.shares_memory(returns, grid.returns) or np.array_equal(returns, grid.returns):
        raise ValueError("candidate_sharpes は合成の return だけを受ける（実 return は拒否）")
    cum = np.vstack([np.zeros((1, returns.shape[1])), np.cumsum(returns, axis=0)])
    out = np.empty(len(candidates))
    days_per_year = grid.n_days / grid.years
    for k, c in enumerate(candidates):
        move = cum[c.t1 + 1, c.pair] - cum[c.t0 + 1, c.pair]
        pnl = (
            c.side * move / grid.sigma_bar[c.pair]
            - cost_multiple * grid.cost[c.pair] / grid.sigma_bar[c.pair]
        )
        daily = np.bincount(c.day, weights=pnl, minlength=grid.n_days)
        sd = daily.std(ddof=1)
        out[k] = daily.mean() / sd * math.sqrt(days_per_year) if sd > 0 else 0.0
    return out


def run_null(
    grid: Grid,
    candidates: list[Candidate],
    reps: int,
    *,
    stream: int,
    kind: str = "sign",
    chol=None,
    hour_scale=None,
) -> tuple[np.ndarray, np.ndarray]:
    """各 replication の候補の Sharpe の最大値と、候補 0 の Sharpe（単独の帰無の広がりの推定用）。"""
    rng = np.random.default_rng([SEED, 99, stream])
    maxima = np.empty(reps)
    first = np.empty(reps)
    for r in range(reps):
        synthetic = (
            synthetic_sign(grid, rng)
            if kind == "sign"
            else synthetic_gaussian(grid, rng, chol, hour_scale)
        )
        values = candidate_sharpes(grid, synthetic, candidates, cost_multiple=0.0)
        maxima[r] = values.max()
        first[r] = values[0]
    return maxima, first


def selection_power(
    grid: Grid,
    candidates: list[Candidate],
    reps: int,
    threshold: float,
    true_sharpe: float,
    *,
    stream: int,
) -> float:
    """**合成だけ**の検出力の確認: 候補 0 の trade に一定の drift を足して真の Sharpe を true_sharpe にし、
    max-T の閾値を超えて最大として選ばれる率。実戦略ではない（実装の確認用）。"""
    rng = np.random.default_rng([SEED, 55, stream])
    days_per_year = grid.n_days / grid.years
    c0 = candidates[0]
    n_trades = len(c0.t0)
    hits = 0
    for _ in range(reps):
        synthetic = synthetic_sign(grid, rng)
        values = candidate_sharpes(grid, synthetic, candidates, cost_multiple=0.0)
        cum = np.vstack([np.zeros((1, synthetic.shape[1])), np.cumsum(synthetic, axis=0)])
        move = cum[c0.t1 + 1, c0.pair] - cum[c0.t0 + 1, c0.pair]
        base = c0.side * move / grid.sigma_bar[c0.pair]
        daily = np.bincount(c0.day, weights=base, minlength=grid.n_days)
        target_mean = true_sharpe * daily.std(ddof=1) / math.sqrt(days_per_year)
        #: 帰無の**期待値**（gross は 0）からずらす。実現値に合わせると雑音が消えてしまう
        expected_null_mean = 0.0
        drift = (target_mean - expected_null_mean) * grid.n_days / n_trades
        boosted = np.bincount(c0.day, weights=base + drift, minlength=grid.n_days)
        values[0] = boosted.mean() / boosted.std(ddof=1) * math.sqrt(days_per_year)
        hits += int(values[0] > threshold and values[0] == values.max())
    return hits / reps


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def calibrate_and_verify(cal: np.ndarray, ver: np.ndarray, *, boot: int = 2000) -> dict[str, Any]:
    threshold = float(np.quantile(cal, 1 - TARGET_FWER))
    rng = np.random.default_rng([SEED, 7])
    boots = np.quantile(
        rng.choice(cal, size=(boot, len(cal)), replace=True), 1 - TARGET_FWER, axis=1
    )
    k = int((ver > threshold).sum())
    lo, hi = wilson(k, len(ver))
    exact_lo = float(beta.ppf(0.025, k, len(ver) - k + 1)) if k > 0 else 0.0
    exact_hi = float(beta.ppf(0.975, k + 1, len(ver) - k))
    return {
        "threshold_sharpe": round(threshold, 4),
        "threshold_bootstrap_95": [
            round(float(np.quantile(boots, 0.025)), 4),
            round(float(np.quantile(boots, 0.975)), 4),
        ],
        "verification_fwer": round(k / len(ver), 4),
        "verification_wilson_95": [round(lo, 4), round(hi, 4)],
        "verification_clopper_pearson_95": [round(exact_lo, 4), round(exact_hi, 4)],
        "mc_se": round(math.sqrt(0.1 * 0.9 / len(ver)), 4),
        "n_cal": len(cal),
        "n_ver": len(ver),
    }


def equivalent_trials(threshold: float, single_sd: float) -> float:
    """max-T の閾値と同じになる独立な試行の数（Φ(z)^N = 0.9 を解く）。"""
    z = threshold / single_sd
    phi = norm.cdf(z)
    return float(math.log(1 - TARGET_FWER) / math.log(phi)) if 0 < phi < 1 else float("nan")


__all__ = [
    "Grid",
    "build_grid",
    "calibrate_and_verify",
    "candidate_sharpes",
    "equivalent_trials",
    "make_candidates",
    "run_null",
    "selection_power",
    "synthetic_gaussian",
    "synthetic_sign",
]
