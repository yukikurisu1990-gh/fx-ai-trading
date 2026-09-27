# ruff: noqa: E501 -- synthesis prose
"""programme 全体の evidence synthesis（2026-09-28 裁定 §5–§12）。**interpretation layer であって、過去の記録は書き換えない。**

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

入力は `artifacts/research/programme/ledger.json`（過去の記録から読み取った値だけ。推測しない）。
ここでは:

- 各行に evidence tier（A〜E）と net の用語（NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING / FULL_RETAIL_NET_UNKNOWN）を付け、
- 仮説の数を区別して数え（別 mechanism / 符号 / horizon / model / universe / 感度 / secondary / 事後診断）、
- programme 全体の null 比較（percentile の分布、p ≤ 0.05 の数と帰無での期待数）を出し、
- 縮小推定（empirical Bayes）で「試した mechanism の真の効果の分布」を推定する。

**Sharpe を pool するときは 1 つの定義だけを使う**: `sharpe_ex_financing`（transaction cost 後・financing 抜き）。
spot-only と judged（carry + markup 込み）を混ぜない。**新しい alpha は計算しない。**
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from statistics import NormalDist
from typing import Any, Final

import numpy as np

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
LEDGER: Final[Path] = REPO_ROOT / "artifacts/research/programme/ledger.json"

TIERS: Final[dict[str, str]] = {
    "A": "clean preregistered development evidence（凍結後に 1 回、1 つの仮説の primary、事後修正なし、多数の cell からの選択でない）",
    "B": "結果の前に凍結された grid の cell、多数から選ばれた cell、または事前登録の無い探索",
    "C": "post-result の実装修正を経た exploratory（POST_EXECUTION_SHARED_DEFECT_CORRECTED / POST_RESULT_IMPLEMENTATION_CORRECTED）",
    "D": "診断・secondary span・感度・benchmark・事後の分析、pre-R1 era 全体",
    "E": "無効・置き換え済み",
}

#: A に入れるのは「1 つの仮説の primary」だけ。grid の cell（horizon / model / 符号 / universe の変種）は
#: 事前凍結でも多数の中の 1 つなので B。
A_VARIANTS: Final[frozenset[str]] = frozenset({"DISTINCT_MECHANISM", "REPLICATION"})
NON_PRIMARY_VARIANTS: Final[frozenset[str]] = frozenset(
    {"SECONDARY_SPAN", "SENSITIVITY", "POST_HOC_DIAGNOSTIC", "BENCHMARK"}
)
SHARPE: Final[str] = "sharpe_ex_financing"


def tier_of(row: dict[str, Any]) -> str:
    if row.get("invalid"):
        return "E"
    if row.get("ledger_part") == "E":
        #: pre-R1 era は別 harness・Sharpe の定義が揃わず、Phase 27–29 は provenance 監査（#356）が未解消。
        #: 診断として読むだけで、A/B と同じ重みにしない。
        return "D"
    if row.get("post_result_correction"):
        return "C"
    if not row.get("is_primary") or row.get("variant_type") in NON_PRIMARY_VARIANTS:
        return "D"
    if row.get("selected_best_of_n"):
        #: 多数の cell から選んだ cell の値は selection を含む（family-wise の検定自体は有効）
        return "B"
    if row.get("preregistered") and row.get("variant_type") in A_VARIANTS:
        return "A"
    return "B"


def net_label(row: dict[str, Any]) -> dict[str, str]:
    financing = row.get("financing_included") or "NONE"
    if financing == "NONE":
        net = "NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING"
    elif financing == "APPROXIMATE_CARRY_AND_MARKUP":
        net = "NET_INCLUDING_APPROXIMATE_INTEREST_DIFFERENTIAL_AND_ASSUMED_MARKUP"
    elif financing == "RESEARCH_CARRY_POLICY_RATES":
        net = "NET_INCLUDING_RESEARCH_CARRY_POLICY_RATES_NO_BROKER_MARKUP"
    else:
        net = f"NET_WITH_{financing}"
    return {"net_definition": net, "full_retail_net": "FULL_RETAIL_NET_UNKNOWN"}


def load_ledger() -> list[dict[str, Any]]:
    rows = json.loads(LEDGER.read_text(encoding="utf-8"))["rows"]
    for row in rows:
        row["evidence_tier"] = tier_of(row)
        row.update(net_label(row))
    return rows


# ----------------------------------------------------------------------
# 仮説の数
# ----------------------------------------------------------------------
def hypothesis_counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    post = [r for r in rows if r.get("ledger_part") != "E" and not r.get("invalid")]
    distinct_post = {
        r["mechanism_id"] for r in post if r.get("variant_type") == "DISTINCT_MECHANISM"
    }
    primary_cells_post = [r for r in post if r.get("is_primary")]
    return {
        "post_r1": {
            "distinct_mechanisms": len(distinct_post),
            "primary_cells_including_horizon_model_sign_universe_variants": len(primary_cells_post),
            "preregistered_primary_cells": sum(
                1 for r in primary_cells_post if r.get("preregistered")
            ),
            "not_preregistered_primary_cells": sum(
                1 for r in primary_cells_post if not r.get("preregistered")
            ),
            "post_result_corrected_rows": sum(1 for r in post if r.get("post_result_correction")),
            "measured_rows_including_sensitivity_secondary_benchmark": len(post),
            "by_variant_type": dict(Counter(r.get("variant_type") for r in post)),
            "invalid_rows": sum(
                1 for r in rows if r.get("ledger_part") != "E" and r.get("invalid")
            ),
        },
        "pre_r1_legacy_rows": sum(1 for r in rows if r.get("ledger_part") == "E"),
        "rows_total": len(rows),
        "by_tier": dict(Counter(row["evidence_tier"] for row in rows)),
        "caveat": "数え方で 32〜212 の幅がある。span・panel・近い mechanism を共有するので、独立な検定の数はこれより少ない",
    }


# ----------------------------------------------------------------------
# mechanism 単位にまとめる（二重に数えない）
# ----------------------------------------------------------------------
def _root(row: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> str:
    """変種は基の mechanism にまとめる（例: T-R2 D は T-R C と同じ span の horizon 変種）。"""
    base = row.get("variant_of")
    seen: set[str] = set()
    while base and base in by_id and base not in seen:
        seen.add(base)
        row = by_id[base]
        base = row.get("variant_of")
    return row.get("mechanism_id") or row["track_id"]


def mechanism_groups(
    rows: list[dict[str, Any]], tiers: set[str], *, measure: str = SHARPE
) -> list[dict[str, Any]]:
    """tier に入る primary で、比較できる Sharpe を持つ行を mechanism 単位にまとめる。

    - 符号の鏡像（SIGN_VARIANT）は同じ測定の裏返しなので入れない。
    - 同じ mechanism の **同じ span** は 1 回しか数えない（変種より基の行を優先）。
    - 別の span は年数で重み付けて合成する。合成の SE² は 1/Σ年数（span が重ならないとき）。
    """
    by_id = {r["track_id"]: r for r in rows}
    groups: dict[str, dict[str, dict[str, Any]]] = {}
    for r in rows:
        if (
            r["evidence_tier"] in tiers
            and r.get("sharpe_comparable")
            and r.get("is_primary")
            and r.get("variant_type") != "SIGN_VARIANT"
            and r.get(measure) is not None
        ):
            spans = groups.setdefault(_root(r, by_id), {})
            span = str(r.get("span_dates") or r.get("span_label"))
            current = spans.get(span)
            if current is None or (current.get("variant_of") and not r.get("variant_of")):
                spans[span] = r
    out = []
    for key, spans in sorted(groups.items()):
        members = list(spans.values())
        years = [float(m["calendar_years"]) for m in members]
        total = sum(years)
        pooled = sum(float(m[measure]) * y for m, y in zip(members, years, strict=True)) / total
        out.append(
            {
                "mechanism_id": key,
                "sharpe": pooled,
                "years": total,
                "members": [m["track_id"] for m in members],
            }
        )
    return out


# ----------------------------------------------------------------------
# 多重検定と programme 全体の null 比較
# ----------------------------------------------------------------------
def _binomial_tail(k: int, n: int, p: float) -> float:
    """P(X ≥ k)、X ~ Binomial(n, p)。"""
    return float(sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1)))


def null_comparison(rows: list[dict[str, Any]], tiers: set[str]) -> dict[str, Any]:
    selected = [r for r in rows if r["evidence_tier"] in tiers]
    with_pct = [
        float(r["null_percentile"]) for r in selected if r.get("null_percentile") is not None
    ]
    with_p = [float(r["p_value"]) for r in selected if r.get("p_value") is not None]
    out: dict[str, Any] = {
        "tiers": sorted(tiers),
        "rows": len(selected),
        "rows_with_null_percentile": len(with_pct),
        "rows_with_p": len(with_p),
    }
    if with_pct:
        n = len(with_pct)
        out["percentile_counts"] = {}
        for threshold in (0.8, 0.9, 0.95):
            actual = sum(p >= threshold for p in with_pct)
            out["percentile_counts"][f">={threshold}"] = {
                "actual": actual,
                "expected_under_null": round(n * (1 - threshold), 2),
                "prob_at_least_actual_under_independent_null": round(
                    _binomial_tail(actual, n, 1 - threshold), 3
                ),
            }
        out["max_percentile"] = round(max(with_pct), 4)
        out["mean_percentile"] = round(float(np.mean(with_pct)), 3)
        #: 帰無なら percentile は一様 → 平均 0.5、標準誤差 √(1/12n)
        out["mean_percentile_z_vs_uniform"] = round(
            (float(np.mean(with_pct)) - 0.5) / math.sqrt(1 / (12 * n)), 2
        )
    if with_p:
        n = len(with_p)
        count = sum(p <= 0.05 for p in with_p)
        out["p_le_005"] = {
            "actual": count,
            "expected_false_positives_under_null": round(0.05 * n, 2),
            "prob_at_least_actual_under_independent_null": round(_binomial_tail(count, n, 0.05), 3),
            "min_p": round(min(with_p), 4),
        }
    #: 符号は mechanism 単位（鏡像を除き、同じ span を二重に数えず、financing 抜きの 1 つの定義）で数える
    net_groups = mechanism_groups(rows, tiers, measure=SHARPE)
    gross_groups = mechanism_groups(
        [r for r in rows if r.get("financing_included") in (None, "NONE")],
        tiers,
        measure="gross_sharpe",
    )
    if gross_groups:
        positive = sum(g["sharpe"] > 0 for g in gross_groups)
        out["gross_sign_by_mechanism"] = {
            "positive": positive,
            "negative": len(gross_groups) - positive,
            "prob_at_least_positive_if_null_half": round(
                _binomial_tail(positive, len(gross_groups), 0.5), 3
            ),
        }
    if net_groups:
        positive = sum(g["sharpe"] > 0 for g in net_groups)
        out["net_ex_financing_sign_by_mechanism"] = {
            "positive": positive,
            "negative": len(net_groups) - positive,
        }
    out["independence_caveat"] = (
        "tail 確率は検定が独立だと仮定している。同じ panel・同じ span・近い mechanism の検定は相関するので、"
        "実際の有効な検定数はこれより少なく、tail 確率は目安にとどまる。p の定義も cycle ごとに違う"
    )
    return out


# ----------------------------------------------------------------------
# 縮小推定（empirical Bayes）
# ----------------------------------------------------------------------
MU_GRID: Final[np.ndarray] = np.linspace(-2.0, 2.0, 801)
TAU_GRID: Final[np.ndarray] = np.linspace(0.0, 2.0, 401)
#: 95% の profile likelihood 区間（χ²₁ の 0.95 分位 / 2）
PROFILE_DROP_95: Final[float] = 3.841459 / 2


def fit_normal_normal(s: np.ndarray, se2: np.ndarray) -> dict[str, Any]:
    """Ŝᵢ ~ N(θᵢ, se²ᵢ)、θᵢ ~ N(μ, τ²) の周辺尤度を grid で最大化。τ の 95% 上限は profile likelihood。"""
    var = se2[None, None, :] + TAU_GRID[None, :, None] ** 2
    loglik = -0.5 * np.sum(
        np.log(var) + (s[None, None, :] - MU_GRID[:, None, None]) ** 2 / var, axis=2
    )
    i, j = np.unravel_index(int(np.argmax(loglik)), loglik.shape)
    profile_tau = loglik.max(axis=0)
    inside = TAU_GRID[profile_tau >= loglik[i, j] - PROFILE_DROP_95]
    return {
        "mu_hat": float(MU_GRID[i]),
        "tau_hat": float(TAU_GRID[j]),
        "tau_upper_95": float(inside.max()),
        "boundary_hit": bool(
            i in (0, len(MU_GRID) - 1) or j == len(TAU_GRID) - 1 or inside.max() >= TAU_GRID[-1]
        ),
    }


def shrinkage(
    rows: list[dict[str, Any]], tiers: set[str], *, measure: str = SHARPE
) -> dict[str, Any]:
    """**勝者探しではなく分布の推定。** Sharpe は 1 つの定義（既定: financing 抜きの TC-net）だけを使う。"""
    usable = mechanism_groups(rows, tiers, measure=measure)
    if len(usable) < 3:
        return {"tiers": sorted(tiers), "usable_mechanisms": len(usable), "status": "TOO_FEW_ROWS"}
    s = np.array([u["sharpe"] for u in usable])
    se2 = np.array([1.0 / u["years"] for u in usable])
    fit = fit_normal_normal(s, se2)
    mu_hat, tau_hat, tau_up = fit["mu_hat"], fit["tau_hat"], fit["tau_upper_95"]
    weights = tau_hat**2 / (tau_hat**2 + se2)
    posterior = mu_hat + weights * (s - mu_hat)
    #: τ̂ を固定したときの μ̂ の SE。mechanism 同士が同じ span を共有して相関するので、これは下限（過小）。
    mu_se = float(1 / math.sqrt(np.sum(1 / (se2 + tau_hat**2))))

    def share_above(threshold: float, tau: float) -> float:
        #: predictive: a new mechanism's true effect ~ N(mu_hat, tau^2 + SE(mu_hat)^2), so tau = 0 never gives 0 or 1
        return round(1 - NormalDist(mu_hat, math.sqrt(tau**2 + mu_se**2)).cdf(threshold), 3)

    return {
        "tiers": sorted(tiers),
        "sharpe_measure": measure,
        "usable_mechanisms": len(usable),
        "mechanisms": [
            {
                **u,
                "sharpe": round(u["sharpe"], 3),
                "years": round(u["years"], 2),
                "posterior_mean": round(float(p), 3),
            }
            for u, p in zip(usable, posterior, strict=True)
        ],
        "mu_hat": round(mu_hat, 3),
        "mu_se_lower_bound": round(mu_se, 3),
        "tau_hat": round(tau_hat, 3),
        "tau_upper_95_profile": round(tau_up, 3),
        "grid_boundary_hit": fit["boundary_hit"],
        "naive_mean_observed": round(float(s.mean()), 3),
        "max_observed": round(float(s.max()), 3),
        "max_posterior_mean": round(float(posterior.max()), 3),
        #: 真の効果の分布 N(μ̂, τ²) で、τ を点推定と 95% 上限の両方で出す（τ̂ = 0 で不確実性を隠さない）
        "share_true_above_predictive": {
            f"{t}": {
                "at_tau_hat": share_above(t, tau_hat),
                "at_tau_upper_95": share_above(t, tau_up),
            }
            for t in (0.0, 0.3, 0.5)
        },
        #: 新しい候補の事前予測分布（forward の情報量に使う）: N(μ̂, τ² + SE(μ̂)²)。τ は上限側を使う
        "new_candidate_prior": {
            "mean": round(mu_hat, 3),
            "sd": round(math.sqrt(tau_up**2 + mu_se**2), 3),
        },
        "reading": (
            "τ̂ が 0 に近いなら、観測のばらつきは標本誤差でほぼ説明でき、mechanism 間で真の効果が違う証拠は弱い。"
            "μ̂ は試した mechanism の平均的な真の TC-net（financing 抜き）Sharpe の推定。"
            "Sharpe の SE を √(1/年数) と置くので、遅い signal（有効標本 5〜25）では不確実性を過小評価する"
        ),
    }


__all__ = [
    "SHARPE",
    "TIERS",
    "fit_normal_normal",
    "hypothesis_counts",
    "load_ledger",
    "mechanism_groups",
    "net_label",
    "null_comparison",
    "shrinkage",
    "tier_of",
]
