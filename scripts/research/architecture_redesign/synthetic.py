# ruff: noqa: E501 -- research prose
"""Architecture redesign の合成・解析の算術（**価格 data を一切読まない**。決定的）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` · design only.

承認: Human + ChatGPT の指示 `ARCHITECTURE_NEUTRAL_FX_SYSTEM_REDESIGN` §36（「synthetic / analytic calculation」を許可）。

計算するもの:

1. pair → currency の射影（20 pair × 8 通貨の incidence 行列の rank、iid の pair の予測の誤差の除去率、疎な view の射影の歪み）
2. 弱い component の portfolio の偽発見（帰無の N 本から in-sample の上位 k 本を選んだ portfolio の Sharpe）
3. 交互作用の項 β12 の検定に要る標本（効果は 2×2 の 1 cell だけ、多重性 M）
4. 2 component の合成の Sharpe の上限（相関 ρ）
5. system 単位の fresh の確認の検出力（SE = 1/√T と、Lo (2002) の SE）
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

REPO: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO / "artifacts/research/architecture_redesign/synthetic.json"
SEED: Final[int] = 20261007
#: PAIRS_20（`scripts/research/exploratory_m15/bars.PAIRS` と同じ。test で一致を確かめる。data の module を import しない）
PAIRS: Final[tuple[str, ...]] = (
    "AUD_CAD", "AUD_JPY", "AUD_NZD", "AUD_USD", "CHF_JPY", "EUR_AUD", "EUR_CAD", "EUR_CHF", "EUR_GBP", "EUR_JPY",
    "EUR_USD", "GBP_AUD", "GBP_CHF", "GBP_JPY", "GBP_USD", "NZD_JPY", "NZD_USD", "USD_CAD", "USD_CHF", "USD_JPY",
)  # fmt: skip
CURRENCIES: Final[tuple[str, ...]] = ("AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD")
FRESH_YEARS: Final[float] = (
    4.895  # fresh pool 2016-06-02 … 2021-04-25 の年数（Cycle 1 の design arithmetic と同じ）
)


def incidence() -> np.ndarray:
    """pair の long 1 単位（return の単位）= base の +1、quote の −1（20 × 8）。"""
    a = np.zeros((len(PAIRS), len(CURRENCIES)))
    for i, pair in enumerate(PAIRS):
        base, quote = pair.split("_")
        a[i, CURRENCIES.index(base)] = 1.0
        a[i, CURRENCIES.index(quote)] = -1.0
    return a


def net_currency_exposure(positions: dict[str, float]) -> dict[str, float]:
    """pair の risk の単位の position（long +）を、通貨の exposure（return の単位）に変換する。"""
    a = incidence()
    vec = np.array([positions.get(p, 0.0) for p in PAIRS])
    z = vec @ a
    return {c: round(float(v), 6) for c, v in zip(CURRENCIES, z, strict=True) if abs(v) > 1e-12}


def currency_projection() -> dict[str, Any]:
    a = incidence()
    rank = int(np.linalg.matrix_rank(a))
    pinv = np.linalg.pinv(a)
    proj = a @ pinv
    kept = float(np.trace(proj)) / len(PAIRS)
    usd_majors = [i for i, p in enumerate(PAIRS) if "USD" in p]
    # 疎な view（EUR_CHF だけの予測 1）を、全 pair の予測として A⁺ で射影した時の歪み
    f = np.zeros(len(PAIRS))
    f[PAIRS.index("EUR_CHF")] = 1.0
    z = pinv @ f
    kept_norm = float(np.linalg.norm(a @ z) ** 2 / np.linalg.norm(f) ** 2)
    return {
        "pairs": len(PAIRS),
        "currencies": len(CURRENCIES),
        "rank": rank,
        "iid_equal_variance_pair_forecast_error_kept_after_projection": round(kept, 4),
        "iid_equal_variance_pair_forecast_error_removed": round(1 - kept, 4),
        "usd_major_count": len(usd_majors),
        "usd_major_rank": int(np.linalg.matrix_rank(a[usd_majors])),
        "example_three_pair_signals_EURUSD_long_USDJPY_short_EURJPY_long": net_currency_exposure(
            {"EUR_USD": 1.0, "USD_JPY": -1.0, "EUR_JPY": 1.0}
        ),
        "sparse_view_EUR_CHF_only_projected_by_pinv": {
            c: round(float(v), 3) for c, v in zip(CURRENCIES, z, strict=True)
        },
        "sparse_view_share_of_squared_norm_kept": round(kept_norm, 3),
    }


def portfolio_false_discovery(
    n: int = 100, k: int = 5, days: int = 1250, reps: int = 400, rho: float = 0.0
) -> dict[str, Any]:
    """真の Sharpe が全て 0 の N 本から、in-sample の Sharpe の上位 k 本を選び、等 risk で組む。"""
    rng = np.random.default_rng(SEED + int(rho * 100) + n + k)
    ann = math.sqrt(252)
    ins, oos, sel_mean = [], [], []
    for _ in range(reps):
        r_in = math.sqrt(rho) * rng.standard_normal((days, 1)) + math.sqrt(
            1 - rho
        ) * rng.standard_normal((days, n))
        r_out = math.sqrt(rho) * rng.standard_normal((days, 1)) + math.sqrt(
            1 - rho
        ) * rng.standard_normal((days, n))
        sr_in = r_in.mean(0) / r_in.std(0, ddof=1) * ann
        top = np.argsort(sr_in)[-k:]
        sel_mean.append(float(sr_in[top].mean()))
        p_in = r_in[:, top].mean(1)
        p_out = r_out[:, top].mean(1)
        ins.append(p_in.mean() / p_in.std(ddof=1) * ann)
        oos.append(p_out.mean() / p_out.std(ddof=1) * ann)
    ins_arr = np.array(ins)
    return {
        "n_candidates": n,
        "k_selected": k,
        "years": round(days / 252, 2),
        "common_factor_corr": rho,
        "true_sharpe_every_candidate": 0.0,
        "mean_selected_component_insample_sharpe": round(float(np.mean(sel_mean)), 3),
        "mean_portfolio_insample_sharpe": round(float(ins_arr.mean()), 3),
        "portfolio_insample_sharpe_null_q90": round(float(np.quantile(ins_arr, 0.9)), 3),
        "mean_portfolio_independent_period_sharpe": round(float(np.mean(oos)), 3),
        "reps": reps,
    }


def interaction_term_requirement() -> list[dict[str, Any]]:
    """2×2 の均衡な設計で、効果 δ（trade あたり net の平均 / σ）が 1 cell だけにある時、β12 の検定に要る総 trade 数。

    SE(β12) = 4σ/√N。N = (4 (z_{α/M} + z_β) / δ)²。z_α は片側 5%、M は検定する交互作用の cell の数（Bonferroni 近似）。
    """
    out = []
    for delta, m in itertools.product((0.013, 0.03, 0.05, 0.1), (1, 45, 180)):
        z = norm.ppf(1 - 0.05 / m) + norm.ppf(0.8)
        n_total = (4 * z / delta) ** 2
        out.append(
            {
                "delta_per_trade": delta,
                "annual_sharpe_equivalent_at_250": round(delta * math.sqrt(250), 2),
                "tests_M": m,
                "total_trades_required": round(n_total),
                "years_at_250_trades_per_year": round(n_total / 250, 1),
            }
        )
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


def fresh_power() -> list[dict[str, Any]]:
    z = norm.ppf(0.95)
    out = []
    for s in (0.5, 0.7, 1.0, 1.3, 1.5):
        simple = 1 - norm.cdf(z - s * math.sqrt(FRESH_YEARS))
        lo = 1 - norm.cdf(z - s * math.sqrt(FRESH_YEARS) / math.sqrt(1 + s * s / 2))
        out.append(
            {
                "true_sharpe": s,
                "fresh_years": FRESH_YEARS,
                "power_se_1_over_sqrt_t": round(float(simple), 3),
                "power_lo_2002_se": round(float(lo), 3),
            }
        )
    return out


def compute() -> dict[str, Any]:
    return {
        "currency_projection": currency_projection(),
        "portfolio_false_discovery": [
            portfolio_false_discovery(n=n, k=k, rho=rho)
            for n, k, rho in ((20, 5, 0.0), (100, 5, 0.0), (100, 10, 0.0), (100, 5, 0.3))
        ],
        "interaction_term_requirement": interaction_term_requirement(),
        "two_component_max_sharpe": combination_bounds(),
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
