# ruff: noqa: E501 -- research prose
"""Architecture redesign の合成・解析の算術（**価格 data を一切読まない**。決定的）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` · design only.

計算するもの:

1. pair → currency の射影（20 pair × 8 通貨の incidence 行列の rank と、pair 固有の雑音の除去率）
2. 弱い component の portfolio の偽発見（帰無の N 本から in-sample の上位 k 本を選んだ portfolio の Sharpe）
3. interaction の検出力と多重性（交互作用の次数ごとの cell の標本の割合・MDE・候補の数）
4. 2 component の合成の Sharpe の上限（相関 ρ）
5. 基本法則 IR = IC · √BR · TC から必要な IC
6. system 単位の fresh の確認の検出力
"""

from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any, Final

import numpy as np
from scipy.stats import norm

from scripts.research.exploratory_m15.bars import PAIRS

REPO: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO / "artifacts/research/architecture_redesign/synthetic.json"
SEED: Final[int] = 20261007
CURRENCIES: Final[tuple[str, ...]] = ("AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD")
FRESH_YEARS: Final[float] = 4.895


def incidence() -> np.ndarray:
    """pair の long 1 単位 = base の +1、quote の −1（20 × 8）。"""
    a = np.zeros((len(PAIRS), len(CURRENCIES)))
    for i, pair in enumerate(PAIRS):
        base, quote = pair.split("_")
        a[i, CURRENCIES.index(base)] = 1.0
        a[i, CURRENCIES.index(quote)] = -1.0
    return a


def net_currency_exposure(positions: dict[str, float]) -> dict[str, float]:
    """pair の position（base 建ての単位、long +）を通貨の exposure に変換する。"""
    a = incidence()
    vec = np.array([positions.get(p, 0.0) for p in PAIRS])
    z = vec @ a
    return {c: round(float(v), 6) for c, v in zip(CURRENCIES, z, strict=True) if abs(v) > 1e-12}


def currency_projection() -> dict[str, Any]:
    a = incidence()
    rank = int(np.linalg.matrix_rank(a))
    proj = a @ np.linalg.pinv(a)  # pair 空間で、通貨の因子が張る部分空間への射影
    # 等分散・独立な pair 固有の雑音のうち、射影で残る割合 = rank / 20
    kept = float(np.trace(proj)) / len(PAIRS)
    example = net_currency_exposure({"EUR_USD": 1.0, "USD_JPY": -1.0, "EUR_JPY": 1.0})
    return {
        "pairs": len(PAIRS),
        "currencies": len(CURRENCIES),
        "rank": rank,
        "pair_noise_variance_kept_after_projection": round(kept, 4),
        "pair_noise_variance_removed": round(1 - kept, 4),
        "example_three_pair_signals_EURUSD_long_USDJPY_short_EURJPY_long": example,
    }


def portfolio_false_discovery(
    n: int = 100, k: int = 5, days: int = 1250, reps: int = 400, rho: float = 0.0
) -> dict[str, Any]:
    """真の Sharpe が全て 0 の N 本から、in-sample の Sharpe の上位 k 本を選ぶ。

    portfolio は等しい risk の配分。in-sample の portfolio の Sharpe と、独立な期間（同じ長さ）での Sharpe を比べる。
    rho は全ての strategy に共通の因子の相関。
    """
    rng = np.random.default_rng(SEED + int(rho * 100) + n + k)
    ann = math.sqrt(252)
    ins, oos, sel_mean = [], [], []
    for _ in range(reps):
        common = rng.standard_normal((days, 1))
        idio = rng.standard_normal((days, n))
        r_in = math.sqrt(rho) * common + math.sqrt(1 - rho) * idio
        common2 = rng.standard_normal((days, 1))
        idio2 = rng.standard_normal((days, n))
        r_out = math.sqrt(rho) * common2 + math.sqrt(1 - rho) * idio2
        sr_in = r_in.mean(0) / r_in.std(0, ddof=1) * ann
        top = np.argsort(sr_in)[-k:]
        sel_mean.append(float(sr_in[top].mean()))
        p_in = r_in[:, top].mean(1)
        p_out = r_out[:, top].mean(1)
        ins.append(p_in.mean() / p_in.std(ddof=1) * ann)
        oos.append(p_out.mean() / p_out.std(ddof=1) * ann)
    return {
        "n_candidates": n,
        "k_selected": k,
        "years": round(days / 252, 2),
        "common_factor_corr": rho,
        "true_sharpe_every_candidate": 0.0,
        "mean_selected_component_insample_sharpe": round(float(np.mean(sel_mean)), 3),
        "mean_portfolio_insample_sharpe": round(float(np.mean(ins)), 3),
        "mean_portfolio_independent_period_sharpe": round(float(np.mean(oos)), 3),
        "reps": reps,
    }


def interaction_power(
    trades_per_year: float = 250.0, years: float = 10.0, effect_per_trade_sd: float = 0.1
) -> list[dict[str, Any]]:
    """binary の状態変数の次数 m の交互作用は、標本の 2^-m の cell に効く。

    effect_per_trade_sd: cell の中での trade あたりの net の平均 / σ（例 0.1 = 年 250 回で Sharpe 1.58 相当）。
    """
    n = trades_per_year * years
    out = []
    for order in (0, 1, 2, 3):
        p = 2.0**-order
        se = 1 / math.sqrt(p * n)
        power = float(1 - norm.cdf(norm.ppf(0.95) - effect_per_trade_sd / se))
        mde = (norm.ppf(0.95) + norm.ppf(0.8)) * se
        out.append(
            {
                "interaction_order": order,
                "cell_share": p,
                "cell_trades": round(p * n),
                "mde_per_trade_mean_over_sd_80pct": round(mde, 4),
                "power_one_sided_5pct_at_effect": round(power, 3),
            }
        )
    return out


def interaction_multiplicity(state_vars: int = 10, levels: int = 2) -> list[dict[str, Any]]:
    """状態変数 M 個から、base mechanism × 状態変数 j 個の交互作用の cell の数。"""
    out = []
    for order in (1, 2, 3):
        combos = math.comb(state_vars, order)
        cells = combos * levels**order
        out.append({"order": order, "variable_combinations": combos, "cells": cells})
    return out


def max_combined_sharpe(s1: float, s2: float, rho: float) -> float:
    """2 本の最適な配分の Sharpe の上限: sqrt((s1² + s2² − 2ρ s1 s2) / (1 − ρ²))。"""
    return math.sqrt(max(s1 * s1 + s2 * s2 - 2 * rho * s1 * s2, 0.0) / (1 - rho * rho))


def combination_bounds() -> list[dict[str, Any]]:
    out = []
    for s1, s2, rho in itertools.product((0.2, 0.5, 0.75), (0.0, 0.4, 0.85), (0.0, 0.3, 0.5)):
        out.append(
            {
                "s1": s1,
                "s2": s2,
                "rho": rho,
                "max_combined": round(max_combined_sharpe(s1, s2, rho), 3),
            }
        )
    return out


def required_ic(ir: float = 1.0) -> list[dict[str, Any]]:
    out = []
    for decisions_per_year, eff_breadth in itertools.product((12, 52, 250), (1, 3, 5, 7)):
        br = decisions_per_year * eff_breadth
        out.append(
            {
                "decisions_per_year": decisions_per_year,
                "effective_breadth": eff_breadth,
                "required_ic_at_tc_1": round(ir / math.sqrt(br), 4),
                "required_ic_at_tc_0_5": round(ir / (0.5 * math.sqrt(br)), 4),
            }
        )
    return out


def fresh_power() -> list[dict[str, Any]]:
    return [
        {
            "true_sharpe": s,
            "fresh_years": FRESH_YEARS,
            "power_one_sided_5pct": round(
                float(1 - norm.cdf(norm.ppf(0.95) - s * math.sqrt(FRESH_YEARS))), 3
            ),
        }
        for s in (0.5, 0.7, 1.0, 1.3, 1.5)
    ]


def compute() -> dict[str, Any]:
    return {
        "currency_projection": currency_projection(),
        "portfolio_false_discovery": [
            portfolio_false_discovery(n=n, k=k, rho=rho)
            for n, k, rho in ((20, 5, 0.0), (100, 5, 0.0), (100, 10, 0.0), (100, 5, 0.3))
        ],
        "interaction_power": interaction_power(),
        "interaction_multiplicity_10_binary_states": interaction_multiplicity(),
        "two_component_max_sharpe": combination_bounds(),
        "required_ic_for_ir_1": required_ic(),
        "fresh_power_system_level": fresh_power(),
    }


def main() -> int:
    if RECORD.exists():
        raise SystemExit(f"{RECORD} は既にある。上書きしない")
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(
        json.dumps(compute(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    print(RECORD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
