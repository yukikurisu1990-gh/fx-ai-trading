# ruff: noqa: E501 -- design-analysis prose
"""programme 設計のための signal-blind な算術（2026-09-28 裁定 §13 / §19–§22 / §27）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**alpha は計算しない。** ここにあるのは公式と、合成の乱数による simulation だけで、
FX の return・signal は一切使わない（drag の入力は呼び出し側が記録から渡す）。

- 検出力: 年率 Sharpe S を、年数 T の日次 return から検出するのに要る年数。
  Sharpe の標準誤差 ≈ √(1/T)（年率、日次 return がほぼ独立のとき）。
- 集約: N 本の signal（各 Sharpe s、互いの相関 ρ）を**等リスクで事前固定**して足すと
  S_p = s · √(N / (1 + (N − 1) ρ))。**相関が低いことは集約の理由にならない**（雑音同士も低相関）ので、
  s は「真の効果」を置く（観測値ではない）。
- 目標収益: 全 cost 後の Sharpe は R / v。**drag は Sharpe の単位で足す**（transaction cost も markup も
  gross notional に比例し、notional は vol target に比例するので、drag / vol は vol を変えても変わらない）。
- drawdown: 全 cost 後の Sharpe と vol を与えた日次 return を simulation し、10 年での最大 DD の分布を出す。
  iid 正規だけでなく、確率的 vol・gap・真の Sharpe の不確実性の変種を並べる。
"""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import Any, Final

import numpy as np

Z_ALPHA_TWO_SIDED_5: Final[float] = 1.959964
Z_POWER_80: Final[float] = 0.841621
TRADING_DAYS: Final[int] = 252


def years_needed(
    sharpe: float, *, z_alpha: float = Z_ALPHA_TWO_SIDED_5, z_power: float = Z_POWER_80
) -> float:
    """真の Sharpe を両側 5%・検出力 80% で検出するのに要る年数。"""
    return ((z_alpha + z_power) / sharpe) ** 2


def mde_sharpe(
    years: float, *, z_alpha: float = Z_ALPHA_TWO_SIDED_5, z_power: float = Z_POWER_80
) -> float:
    """年数 T で両側 5%・検出力 80% の最小検出 Sharpe。"""
    return (z_alpha + z_power) / math.sqrt(years)


def power_at(sharpe: float, years: float, *, z_alpha: float = Z_ALPHA_TWO_SIDED_5) -> float:
    """真の Sharpe S（> 0）、年数 T で、両側 5% 検定が正の側に棄却する確率 Φ(S√T − z₀.₉₇₅)。"""
    return float(NormalDist().cdf(sharpe * math.sqrt(years) - z_alpha))


def power_landscape() -> dict[str, Any]:
    """研究の型ごとの検出力。**年数の上限は既に使った seen span の長さ**（long 17.7 年、recent 4.7 年）。"""
    archetypes = {
        "daily_continuous_recent": {
            "years": 4.7,
            "note": "recent span の日次 book（例: U5・M10・Top-Five の recent）",
        },
        "daily_continuous_long": {"years": 17.7, "note": "long span（ECB 参照レート）の日次 book"},
        "monthly_macro_long": {
            "years": 17.7,
            "note": "月次 macro signal。return は日次でも、signal の独立な状態は有効標本数（5〜25）しか無い。下の検出力は上限",
        },
        "usd_factor_long": {
            "years": 17.7,
            "note": "1 factor（breadth 1）。符号 regime が少ない（M15 は 6、M16 は 28）。下の検出力は上限",
        },
        "cross_sectional_factor_long": {"years": 17.7, "note": "8 通貨の相対 book"},
        "combined_seen_all": {
            "years": 22.4,
            "note": "long + recent を合わせた seen の全長（#489 の pooled 22.5 年）",
        },
        "fresh_pool_if_released": {
            "years": 4.9,
            "note": "保護中の fresh pool 2016-06-02 … 2021-04-25 の**長さだけ**（中身は読まない）。単独で使ったときの検出力",
        },
        "event_driven": {
            "years": None,
            "note": "event 数が律速（例: 中銀会合 8 回/年 × 4 中銀 × 20 年 ≈ 640 件）。日次換算の年数では測れない",
        },
    }
    rows = {}
    for name, spec in archetypes.items():
        years = spec["years"]
        rows[name] = {
            **spec,
            "mde_sharpe_80pct_power": None if years is None else round(mde_sharpe(years), 3),
            "power_if_true_sharpe": None
            if years is None
            else {f"{s:.1f}": round(power_at(s, years), 3) for s in (0.2, 0.3, 0.5)},
        }
    return {
        "years_needed_80pct_power_two_sided_5pct": {
            f"{s:.1f}": round(years_needed(s), 1) for s in (0.1, 0.2, 0.3, 0.5, 0.7, 1.0)
        },
        "archetypes": rows,
        "family_vs_track": (
            "family 内の K 本を事前固定の等ウェイトで 1 つの統計量にすると、真の効果が family 共通なら Sharpe は "
            "√(K/(1+(K−1)ρ)) 倍になり、必要年数は (1+(K−1)ρ)/K 倍に縮む。**効果が family 共通でなければ、平均は薄まる**"
        ),
        "slow_signal_caveat": (
            "日次 return がほぼ独立なら Sharpe の SE は √(1/T) で決まるが、signal の状態がほとんど変わらない"
            "（有効標本 5〜25）なら、その推定は少数の regime の当たり外れに支配され、SE √(1/T) は過小評価になる"
        ),
    }


def aggregate_sharpe(signal_sharpe: float, n: int, rho: float) -> float:
    return signal_sharpe * math.sqrt(n / (1 + (n - 1) * rho))


def aggregation_scenarios() -> dict[str, Any]:
    """**N・ρ・s は観測から選ばない。** 固定の格子で並べる。s は 1 本あたりの **cost 後**の真の Sharpe。"""
    grid = {}
    for s in (0.05, 0.1, 0.2, 0.3):
        for rho in (0.0, 0.1, 0.3, 0.5):
            grid[f"s={s:.2f}|rho={rho:.1f}"] = {
                str(n): round(aggregate_sharpe(s, n, rho), 3) for n in (1, 3, 5, 10, 20)
            }
    #: 目標の Sharpe に届く最小の N（1,000 本でも届かなければ None）
    reach = {}
    for target in (0.5, 0.6, 0.75):
        for s in (0.1, 0.2, 0.3):
            for rho in (0.0, 0.1, 0.3):
                reach[f"target={target}|s={s:.1f}|rho={rho:.1f}"] = next(
                    (n for n in range(1, 1001) if aggregate_sharpe(s, n, rho) >= target), None
                )
    return {
        "formula": "S_p = s × √(N / (1 + (N − 1) ρ))（等リスク・事前固定）。s は cost 後の真の Sharpe",
        "grid": grid,
        "ceiling_as_n_grows": {
            f"s={s:.2f}|rho={rho:.1f}": round(s / math.sqrt(rho), 3)
            for s in (0.1, 0.2, 0.3)
            for rho in (0.1, 0.3, 0.5)
        },
        "min_n_to_reach_target": reach,
        "caveats": (
            "s は**真の**効果。観測された小さな Sharpe は selection と雑音を含むので s には使えない。",
            "ρ が低いのは『独立な情報』の証拠ではない — 情報を持たない signal 同士も低相関。",
            "cost は Sharpe の単位で 1 本ごとに引く: S_p,net = (s_gross − c) × √(N/(1+(N−1)ρ))。倍率は gross と同じだが、"
            "cost 後の s が 0 の source は何本足しても 0 のまま（逆向きの position が相殺されれば cost はそれより少し減る）。",
            "N を増やすには N 本の独立で真の source が要る。これまでの programme では null を超えた source は 0 本。",
        ),
    }


def required_sharpe(annual_return: float, vol: float, drag_sharpe: float = 0.0) -> float:
    """年 R を vol v で出すのに要る、drag を引く前の Sharpe = R / v + drag（drag は Sharpe の単位）。"""
    return annual_return / vol + drag_sharpe


def drawdown_distribution(
    sharpe: float,
    vol: float,
    *,
    years: int = 10,
    paths: int = 4000,
    seed: int = 20260928,
    variant: str = "iid_gaussian",
    prior_sd: float = 0.0,
) -> dict[str, float]:
    """合成の日次 return（全 cost 後の年率 Sharpe・vol）で、`years` 年の最大 DD（加算 equity）の分布。

    variant:
    - `iid_gaussian`: 真の Sharpe が要求値に等しく、iid 正規（最も楽観的）
    - `stochastic_vol`: 月次の log-vol が AR(1)（φ 0.9、innovation 0.25）で動く。平均分散は vol² に揃える
    - `gap`: iid 正規に、年 0.2 回の −5% ×（vol / 10%）の gap を足す（週末・中銀の不意打ち。margin の強制決済は入れていない）
    - `sharpe_uncertainty`: path ごとに真の Sharpe を N(sharpe, prior_sd²) から引く
    """
    rng = np.random.default_rng(seed)
    days = years * TRADING_DAYS
    sigma = vol / math.sqrt(TRADING_DAYS)
    true_sharpe = np.full((paths, 1), sharpe)
    if variant == "sharpe_uncertainty":
        true_sharpe = rng.normal(sharpe, prior_sd, size=(paths, 1))
    mu = true_sharpe * vol / TRADING_DAYS
    shocks = rng.normal(0.0, 1.0, size=(paths, days))
    scale = np.ones((paths, days))
    if variant == "stochastic_vol":
        months = years * 12
        log_vol = np.zeros((paths, months))
        for m in range(1, months):
            log_vol[:, m] = 0.9 * log_vol[:, m - 1] + rng.normal(0.0, 0.25, size=paths)
        monthly = np.exp(log_vol)
        monthly /= np.sqrt(np.mean(monthly**2))
        scale = np.repeat(monthly, TRADING_DAYS // 12 + 1, axis=1)[:, :days]
    returns = mu + sigma * scale * shocks
    if variant == "gap":
        gaps = rng.random(size=(paths, days)) < 0.2 / TRADING_DAYS
        returns = returns - gaps * 0.05 * (vol / 0.10)
    equity = np.cumsum(returns, axis=1)
    peak = np.maximum.accumulate(np.maximum(equity, 0.0), axis=1)
    drawdown = (equity - peak).min(axis=1)
    return {
        "median_max_dd": round(float(np.median(drawdown)), 3),
        "p10_max_dd": round(float(np.percentile(drawdown, 10)), 3),
        "prob_dd_worse_than_20pct": round(float((drawdown < -0.20).mean()), 3),
        "prob_dd_worse_than_30pct": round(float((drawdown < -0.30).mean()), 3),
        "prob_negative_after_years": round(float((equity[:, -1] < 0).mean()), 3),
    }


def objective_table(
    *,
    financing_drag_sharpe: dict[str, float],
    tc_drag_sharpe: dict[str, float],
    prior_mean: float,
    prior_sd: float,
) -> dict[str, Any]:
    """年 5% / 10% に要る Sharpe を、**transaction cost と financing を分けて**出す。

    - `net_all_in`: 全 cost 後の Sharpe（= R / v）。DD はこの値で決まる。
    - `tc_net_ex_financing_required`: financing を引く前の TC-net Sharpe（ledger の `sharpe_ex_financing` と比べる値）。
      financing の cell（APPROXIMATE_RESEARCH_FINANCING_RANGE、FULL_RETAIL_NET_UNKNOWN）ごと。
    - `gross_required_at_central_financing`: さらに transaction cost を引く前（book の速さの cell ごと）。
    - DD は 4 変種。`programme_prior` は、真の Sharpe が要求値ではなく programme の縮小推定から引かれた場合。
    """
    out: dict[str, Any] = {
        "drag_units": "Sharpe の単位（年率 drag ÷ book の vol）。notional が vol に比例するので vol を変えても変わらない",
        "financing_drag_sharpe": financing_drag_sharpe,
        "tc_drag_sharpe": tc_drag_sharpe,
        "label": "APPROXIMATE_RESEARCH_FINANCING_RANGE · FULL_RETAIL_NET_UNKNOWN · 実際の broker financing ではない",
        "dd_caveat": "DD は加算 equity。margin の強制決済・流動性の蒸発は入れていない。iid 正規の値が最も楽観的",
        "rows": {},
    }
    for target in (0.05, 0.10):
        for vol in (0.08, 0.10, 0.12, 0.15, 0.20):
            net = target / vol
            out["rows"][f"{target:.0%}@vol{vol:.0%}"] = {
                "net_all_in": round(net, 3),
                "tc_net_ex_financing_required": {
                    k: round(required_sharpe(target, vol, d), 3)
                    for k, d in financing_drag_sharpe.items()
                },
                "gross_required_at_central_financing": {
                    k: round(required_sharpe(target, vol, d + financing_drag_sharpe["central"]), 3)
                    for k, d in tc_drag_sharpe.items()
                },
                "stress_only": vol >= 0.20,
                "drawdown": {
                    "iid_gaussian_true_sharpe_equals_requirement": drawdown_distribution(net, vol),
                    "stochastic_vol": drawdown_distribution(net, vol, variant="stochastic_vol"),
                    "gap": drawdown_distribution(net, vol, variant="gap"),
                    "requirement_with_sharpe_uncertainty": drawdown_distribution(
                        net, vol, variant="sharpe_uncertainty", prior_sd=prior_sd
                    ),
                    "programme_prior": drawdown_distribution(
                        prior_mean, vol, variant="sharpe_uncertainty", prior_sd=prior_sd
                    ),
                },
            }
    return out


def forward_information(*, prior_mean: float, prior_sd: float) -> dict[str, Any]:
    """forward の長さごとに、候補の真の Sharpe についての情報がどれだけ増えるか。

    prior から、観測の SE = √(1/T) を加えた事後の SD と、forward 単独で z > 1.96
    （**片側 2.5%**、正の側）になる確率（事前予測）を出す。
    """
    rows = {}
    for months in (6, 12, 24, 36):
        years = months / 12
        se = math.sqrt(1 / years)
        posterior_sd = math.sqrt(1 / (1 / prior_sd**2 + 1 / se**2))
        predictive_sd = math.sqrt(prior_sd**2 + se**2)
        prob_significant = 1 - NormalDist(prior_mean / se, predictive_sd / se).cdf(
            Z_ALPHA_TWO_SIDED_5
        )
        rows[f"{months}m"] = {
            "se_of_sharpe": round(se, 3),
            "posterior_sd": round(posterior_sd, 3),
            "posterior_sd_reduction_vs_prior": round(1 - posterior_sd / prior_sd, 3),
            "prob_forward_alone_z_above_1_96_one_sided_2_5pct": round(prob_significant, 3),
        }
    return {"prior_mean": prior_mean, "prior_sd": prior_sd, "rows": rows}


__all__ = [
    "aggregate_sharpe",
    "aggregation_scenarios",
    "drawdown_distribution",
    "forward_information",
    "mde_sharpe",
    "objective_table",
    "power_at",
    "power_landscape",
    "required_sharpe",
    "years_needed",
]
