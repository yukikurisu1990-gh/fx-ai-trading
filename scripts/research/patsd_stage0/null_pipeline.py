# ruff: noqa: E501 -- pipeline prose
"""S0-2（選択 pipeline 全体の帰無での誤合格率）と S0-3（G4 の到達可能性）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**損益は合成 data の上でだけ計算する。** 合成 data = seen の H4 mid の log return × 時点ごとに全 pair 共通の
ランダムな ±1（vol の塊・相関・大きさを保ち、方向の情報を壊す）。candidate は signal を持たない置き換えの規則
（ランダムな entry 時刻・ランダムな方向・事前固定の保有）で、B′ の family は実装しない。

実際の return の符号と candidate の position を対応付ける経路は、この module には無い
（`synthetic_cumret` だけが return を使い、必ずランダムな符号を掛ける。test で固定）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.stats import norm

from scripts.research.patsd_stage0 import prereg

EULER: float = 0.5772156649015329


# ----------------------------------------------------------------------
# 入力（実 data から取るのは |r| の構造・spread・日付だけ）
# ----------------------------------------------------------------------
@dataclass
class Panel:
    returns: np.ndarray  #: (T, P) H4 mid の log return（実値。合成にだけ使う）
    sigma_bar: np.ndarray  #: (P,) H4 bar の vol
    cost: np.ndarray  #: (P,) round trip cost（return 単位）
    bar_day: np.ndarray  #: (T,) bar の日の番号
    n_days: int
    oof_day: np.ndarray  #: (n_days,) bool
    fold_of_day: np.ndarray  #: (n_days,) int（OOF 外は -1）
    last_entry_bar: int
    oof_years: float


def build_panel(h4: dict[str, pd.DataFrame], cost: dict[str, float]) -> Panel:
    pairs = sorted(h4)
    index = sorted(set().union(*[set(frame["ts"]) for frame in h4.values()]))
    index = pd.DatetimeIndex(index)
    returns = np.zeros((len(index), len(pairs)))
    for j, pair in enumerate(pairs):
        close = h4[pair].set_index("ts")["mid_c"].reindex(index).ffill()
        r = np.log(close).diff().fillna(0.0).to_numpy()
        returns[:, j] = r
    sigma = returns[1:].std(axis=0, ddof=1)
    days = pd.DatetimeIndex(index.tz_convert("UTC").normalize().tz_localize(None))
    unique_days = pd.DatetimeIndex(sorted(set(days)))
    day_number = unique_days.get_indexer(days)
    oof_start = (
        pd.Timestamp(prereg.FIRST_DAY)
        + pd.offsets.BDay(prereg.WARMUP_BUSINESS_DAYS)
        + pd.DateOffset(years=1)
    )
    oof = np.asarray(unique_days >= oof_start)
    if not oof.any():
        raise ValueError("fold 外の日が無い（span が warm-up と最初の学習 block より短い）")
    quarters = unique_days.to_period("Q")
    fold = np.full(len(unique_days), -1)
    oof_quarters = sorted(set(quarters[oof]))
    for k, q in enumerate(oof_quarters):
        fold[(quarters == q) & oof] = k
    last_entry_day = pd.Timestamp(prereg.LAST_DAY) - pd.offsets.BDay(prereg.MAX_HOLD_BUSINESS_DAYS)
    last_entry_bar = int(
        np.searchsorted(np.asarray(days), np.datetime64(last_entry_day), side="right") - 1
    )
    oof_years = float((unique_days[oof][-1] - unique_days[oof][0]).days + 1) / 365.25
    return Panel(
        returns=returns,
        sigma_bar=sigma,
        cost=np.array([cost[p] for p in pairs]),
        bar_day=day_number,
        n_days=len(unique_days),
        oof_day=oof,
        fold_of_day=fold,
        last_entry_bar=last_entry_bar,
        oof_years=oof_years,
    )


def synthetic_cumret(panel: Panel, rng: np.random.Generator) -> np.ndarray:
    """**ベクトルの符号ランダム化**。時点ごとに全 pair 共通の ±1 を掛けてから累積する。"""
    signs = rng.choice(np.array([-1.0, 1.0]), size=panel.returns.shape[0])
    synthetic = panel.returns * signs[:, None]
    return np.vstack([np.zeros((1, synthetic.shape[1])), np.cumsum(synthetic, axis=0)])


# ----------------------------------------------------------------------
# signal を持たない置き換えの candidate（trade の一覧）
# ----------------------------------------------------------------------
@dataclass
class Trades:
    pair: np.ndarray
    t0: np.ndarray
    t1: np.ndarray
    direction: np.ndarray
    exit_day: np.ndarray


def base_configs() -> list[tuple[int, int, int, int, int]]:
    b = prereg.BUDGET
    return [
        (f, a, i, j, e)
        for f in range(b["families"])
        for a in range(b["architectures_per_family"])
        for i in range(len(b["grid"]["entry_prob_per_h4_bar"]))
        for j in range(len(b["grid"]["hold_h4_bars"]))
        for e in range(len(b["exits"]))
    ]


def make_trades(panel: Panel, config: tuple[int, int, int, int, int]) -> Trades:
    """entry 時刻・方向・保有は arch の seed だけで決まる（return を見ない）。格子の近傍は同じ乱数を共有する。"""
    f, a, i, j, e = config
    b = prereg.BUDGET
    rng = np.random.default_rng([prereg.SEED, f, a])
    n_bars, n_pairs = panel.returns.shape
    u = rng.random((n_bars, n_pairs))
    direction = rng.choice(np.array([-1, 1]), size=(n_bars, n_pairs))
    fraction = rng.uniform(0.5, 1.0, size=(n_bars, n_pairs))
    p = b["grid"]["entry_prob_per_h4_bar"][i]
    hold = b["grid"]["hold_h4_bars"][j]
    entry = u < p
    entry[panel.last_entry_bar + 1 :] = False
    t0, pair = np.nonzero(entry)
    duration = np.full(len(t0), hold) if e == 0 else np.ceil(hold * fraction[t0, pair]).astype(int)
    t1 = np.minimum(t0 + duration, n_bars - 1)
    return Trades(
        pair=pair, t0=t0, t1=t1, direction=direction[t0, pair], exit_day=panel.bar_day[t1]
    )


def trade_pnl(panel: Panel, cum: np.ndarray, trades: Trades) -> tuple[np.ndarray, np.ndarray]:
    """合成の累積 return の上での trade の損益（risk 単位 = 1 / H4 bar の vol）と cost。"""
    move = cum[trades.t1 + 1, trades.pair] - cum[trades.t0 + 1, trades.pair]
    gross = trades.direction * move / panel.sigma_bar[trades.pair]
    cost = panel.cost[trades.pair] / panel.sigma_bar[trades.pair]
    return gross, cost


def daily(
    panel: Panel, trades: Trades, values: np.ndarray, mask: np.ndarray | None = None
) -> np.ndarray:
    n_pairs = panel.returns.shape[1]
    if mask is not None:
        return (
            np.bincount(trades.exit_day[mask], weights=values[mask], minlength=panel.n_days)
            / n_pairs
        )
    return np.bincount(trades.exit_day, weights=values, minlength=panel.n_days) / n_pairs


# ----------------------------------------------------------------------
# 統計
# ----------------------------------------------------------------------
def ann_sharpe(x: np.ndarray, days_per_year: float) -> float:
    sd = x.std(ddof=1)
    return float(x.mean() / sd * math.sqrt(days_per_year)) if sd > 0 else 0.0


def shrink(s: float, se: float) -> float:
    mu, tau = prereg.PRIOR["mu"], prereg.PRIOR["tau"]
    w = tau**2 / (tau**2 + se**2)
    return mu + w * (s - mu)


def expected_max_z(n: int) -> float:
    if n <= 1:
        return 0.0
    return (1 - EULER) * norm.ppf(1 - 1 / n) + EULER * norm.ppf(1 - 1 / (n * math.e))


def deflated_p(x: np.ndarray, sr0: float) -> float:
    """Bailey–López de Prado の deflated Sharpe の p（日次の SR、歪度・尖度込み）。"""
    sd = x.std(ddof=1)
    if sd <= 0:
        return 1.0
    sr = x.mean() / sd
    z = (x - x.mean()) / sd
    skew = float((z**3).mean())
    kurt = float((z**4).mean())
    denom = math.sqrt(max(1 - skew * sr + (kurt - 1) / 4 * sr**2, 1e-12))
    stat = (sr - sr0) * math.sqrt(len(x) - 1) / denom
    return float(1 - norm.cdf(stat))


def effective_trials(matrix: np.ndarray) -> int:
    if matrix.shape[0] < 2:
        return matrix.shape[0]
    corr = np.corrcoef(matrix)
    corr = np.nan_to_num(corr, nan=0.0)
    dist = 1 - corr[np.triu_indices(len(corr), 1)]
    labels = fcluster(linkage(np.clip(dist, 0, 2), method="average"), t=0.2, criterion="distance")
    return int(len(set(labels)))


# ----------------------------------------------------------------------
# 1 replication
# ----------------------------------------------------------------------
@dataclass
class Trial:
    key: tuple
    kind: str
    base: tuple
    neighbours: list
    oof_net: np.ndarray
    oof_net15: np.ndarray


def _neighbours(config):
    f, a, i, j, e = config
    out = []
    for di, dj in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        ii, jj = i + di, j + dj
        if 0 <= ii < 3 and 0 <= jj < 3:
            out.append((f, a, ii, jj, e))
    return out


def run_replication(
    panel: Panel, trade_book: dict, rep_seed: int, injection: tuple | None = None
) -> dict[str, Any]:
    """injection = (真の Sharpe, 注入する base config)。None なら純粋な帰無。"""
    rng = np.random.default_rng([prereg.SEED, 7, rep_seed])
    cum = synthetic_cumret(panel, rng)
    oof = panel.oof_day
    days_per_year = oof.sum() / panel.oof_years
    se = 1 / math.sqrt(panel.oof_years)
    b = prereg.BUDGET

    pnl: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}
    for config, trades in trade_book.items():
        pnl[config] = trade_pnl(panel, cum, trades)

    drift: dict[tuple, float] = {}
    if injection is not None:
        true_sharpe, target = injection
        trades = trade_book[target]
        gross, cost = pnl[target]
        net_daily = daily(panel, trades, gross - cost)[oof]
        sd = net_daily.std(ddof=1)
        n_oof_trades = int(oof[trades.exit_day].sum())
        want_daily_mean = true_sharpe * sd / math.sqrt(days_per_year)
        have_daily_mean = -daily(panel, trades, cost)[oof].mean()
        per_trade = (
            (want_daily_mean - have_daily_mean)
            * oof.sum()
            * panel.returns.shape[1]
            / max(n_oof_trades, 1)
        )
        for neighbour in _neighbours(target):
            drift[neighbour] = per_trade * (
                1.0 if neighbour == target else prereg.NEIGHBOUR_SIGNAL_SHARE
            )

    def series(config, mask=None):
        trades = trade_book[config]
        gross, cost = pnl[config]
        gross = gross + drift.get(config, 0.0)
        net = daily(panel, trades, gross - cost, mask)[oof]
        net15 = daily(panel, trades, gross - 1.5 * cost, mask)[oof]
        return net, net15

    trials: list[Trial] = []
    for config in trade_book:
        net, net15 = series(config)
        trials.append(Trial(config, "rule", config, _neighbours(config), net, net15))

    def fold_stats(x):
        folds = panel.fold_of_day[oof]
        values = [
            ann_sharpe(x[folds == k], days_per_year)
            for k in range(folds.max() + 1)
            if (folds == k).sum() > 5
        ]
        return np.array(values)

    def u_score(trial):
        s = ann_sharpe(trial.oof_net, days_per_year)
        s15 = ann_sharpe(trial.oof_net15, days_per_year)
        folds = fold_stats(trial.oof_net)
        shrunk_folds = [shrink(v, 1 / math.sqrt(0.25)) for v in folds]
        return float(np.median(shrunk_folds) - 1.0 * folds.std(ddof=1) - 0.5 * max(s - s15, 0.0))

    base_scores = {t.key: u_score(t) for t in trials}
    base_sharpe = {t.key: ann_sharpe(t.oof_net, days_per_year) for t in trials}

    # L2 filter（family・exit ごとに U の上位 3 設定 × 2 filter）
    for f in range(b["families"]):
        for e in range(len(b["exits"])):
            candidates = sorted(
                [k for k in trade_book if k[0] == f and k[4] == e], key=lambda k: -base_scores[k]
            )[: b["l2_top_configs"]]
            for config in candidates:
                n = len(trade_book[config].t0)
                for k in range(b["l2_filters_per_family"]):
                    mask = np.random.default_rng([prereg.SEED, 11, *config, k]).random(n) < 0.5
                    net, net15 = series(config, mask)
                    trials.append(Trial((config, "L2", k), "L2", config, [], net, net15))

    # ML（base の fold 外 net Sharpe が正の family のうち上位 2、その最良設定に take / skip）
    best_by_family = {
        f: max((k for k in trade_book if k[0] == f), key=lambda k: base_scores[k])
        for f in range(b["families"])
    }
    eligible = [f for f, k in best_by_family.items() if base_sharpe[k] > 0]
    eligible = sorted(eligible, key=lambda f: -base_scores[best_by_family[f]])[: b["ml_families"]]
    for f in eligible:
        config = best_by_family[f]
        n = len(trade_book[config].t0)
        for model in range(b["ml_models"]):
            for hp in range(b["ml_hp"]):
                for target in range(b["ml_targets"]):
                    score = np.random.default_rng(
                        [prereg.SEED, 13, *config, model, hp, target]
                    ).random(n)
                    for q, keep in enumerate(b["ml_top_k"]):
                        mask = score >= np.quantile(score, 1 - keep)
                        net, net15 = series(config, mask)
                        key = (config, "ML", model, hp, target, q)
                        neigh = [
                            (config, "ML", model, h2, target, q2)
                            for h2, q2 in (
                                (hp, q),
                                (hp - 1, q),
                                (hp + 1, q),
                                (hp, q - 1),
                                (hp, q + 1),
                            )
                            if 0 <= h2 < b["ml_hp"] and 0 <= q2 < len(b["ml_top_k"])
                        ]
                        trials.append(Trial(key, "ML", config, neigh, net, net15))

    # baseline（合成 data の上の単純な trend / mean reversion、と no-trade = 0）
    lag = 20
    hold = 30
    bars = np.arange(lag, min(panel.last_entry_bar, cum.shape[0] - hold - 2), hold)
    past = cum[bars] - cum[bars - lag]
    move = cum[bars + hold] - cum[bars]
    trend_gross = np.sign(past) * move / panel.sigma_bar
    trend_cost = panel.cost / panel.sigma_bar
    baseline_days = panel.bar_day[bars + hold - 1]
    trend = np.bincount(
        baseline_days, weights=(trend_gross - trend_cost).mean(axis=1), minlength=panel.n_days
    )[oof]
    revert = np.bincount(
        baseline_days, weights=(-trend_gross - trend_cost).mean(axis=1), minlength=panel.n_days
    )[oof]
    best_baseline = max(0.0, ann_sharpe(trend, days_per_year), ann_sharpe(revert, days_per_year))

    # 指標と hard filter（DSR の閾値以外）
    matrix = np.vstack([t.oof_net for t in trials])
    n_eff = effective_trials(matrix)
    daily_sr = np.array(
        [
            t.oof_net.mean() / t.oof_net.std(ddof=1) if t.oof_net.std(ddof=1) > 0 else 0.0
            for t in trials
        ]
    )
    sr0 = float(np.sqrt(daily_sr.var(ddof=1)) * expected_max_z(n_eff))
    sharpe = {t.key: ann_sharpe(t.oof_net, days_per_year) for t in trials}
    rows = []
    for t in trials:
        s = sharpe[t.key]
        s15 = ann_sharpe(t.oof_net15, days_per_year)
        folds = fold_stats(t.oof_net)
        fold_ok = bool((folds > 0).mean() >= 0.6 and folds.min() >= -1 / math.sqrt(0.25))
        if t.kind == "rule":
            neigh = [sharpe[n] for n in t.neighbours]
        elif t.kind == "L2":
            neigh = [sharpe[n] for n in _neighbours(t.base)]
        else:
            neigh = [sharpe[n] for n in t.neighbours if n in sharpe]
        neigh = np.array(neigh)
        plateau = bool(
            len(neigh) and (np.sign(neigh) == np.sign(s)).mean() >= 0.7 and np.median(neigh) > 0
        )
        rows.append(
            {
                "key": t.key,
                "base": t.base,
                "sharpe": s,
                "u": u_score(t),
                "pass_wo_dsr": bool(s15 > 0 and plateau and fold_ok and s >= best_baseline + 0.3),
                "dsr_p": deflated_p(t.oof_net, sr0),
                "series": t.oof_net,
            }
        )

    injected_family = set(drift) if injection is not None else set()
    out: dict[str, Any] = {"n_trials": len(trials), "n_eff": n_eff, "best_baseline": best_baseline}
    for threshold in prereg.SELECTION["dsr_ladder"]:
        passers = sorted(
            [r for r in rows if r["pass_wo_dsr"] and r["dsr_p"] <= threshold], key=lambda r: -r["u"]
        )
        finalists = passers[: prereg.SELECTION["finalists"]]
        g4 = False
        g4_point = False
        includes_injected = any(r["base"] in injected_family for r in finalists)
        if finalists:
            stacked = np.vstack([r["series"] / r["series"].std(ddof=1) for r in finalists])
            portfolio = stacked.mean(axis=0)
            s_port = ann_sharpe(portfolio, days_per_year)
            g4 = shrink(s_port, se) >= prereg.G4_THRESHOLD
            g4_point = shrink(s_port - se * expected_max_z(n_eff), se) >= prereg.G4_THRESHOLD
        out[str(threshold)] = {
            "any_pass": bool(passers),
            "n_pass": len(passers),
            "g4": bool(g4),
            "g4_point_deflated": bool(g4_point),
            "g4_with_injected": bool(g4 and includes_injected),
            "g4_point_with_injected": bool(g4_point and includes_injected),
        }
    return out


def build_trade_book(panel: Panel) -> dict:
    return {config: make_trades(panel, config) for config in base_configs()}


def g4_arithmetic(oof_years: float) -> dict[str, Any]:
    """#498 §13 の算術（deflation 前）を、実際の fold 外の長さで再計算する。"""
    mu, tau = prereg.PRIOR["mu"], prereg.PRIOR["tau"]
    se = 1 / math.sqrt(oof_years)
    w = tau**2 / (tau**2 + se**2)
    needed = mu + (prereg.G4_THRESHOLD - mu) / w
    marginal = 1 - norm.cdf((needed - mu) / math.sqrt(tau**2 + se**2))
    return {
        "oof_years": round(oof_years, 3),
        "se": round(se, 4),
        "shrink_weight": round(w, 4),
        "observed_needed": round(needed, 4),
        "pass_prob_by_true_sharpe": {
            str(s): round(float(1 - norm.cdf((needed - s) / se)), 4)
            for s in prereg.INJECTED_TRUE_SHARPES
        },
        "marginal_pass_prob_under_prior": round(float(marginal), 5),
        "times_fresh_power_0_72": round(float(marginal * 0.72), 5),
    }


__all__ = [
    "Panel",
    "build_panel",
    "build_trade_book",
    "deflated_p",
    "effective_trials",
    "g4_arithmetic",
    "run_replication",
    "shrink",
    "synthetic_cumret",
]
