# ruff: noqa: E501 -- synthesis prose
"""programme synthesis を 1 つの artifact に書く（`artifacts/research/programme/synthesis.json`）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**alpha は計算しない。** 入力は ledger（記録済みの値）、#495 の financing cell（記録済み）、
signal-blind な算術だけ。
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any, Final

from scripts.research.acquisition_safety import write_provenance
from scripts.research.programme import feasibility_math as fm
from scripts.research.programme import rules
from scripts.research.programme import synthesis as syn

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
OUT: Final[Path] = REPO_ROOT / "artifacts/research/programme/synthesis.json"
USD_FACTOR_RESULTS: Final[Path] = (
    REPO_ROOT / "artifacts/research/usd_factor_financing/development.json"
)

#: 統計的な構造の検定で、経済的な return の検定ではないもの。null 比較の「経済的な検定」から外す。
NON_ECONOMIC_TESTS: Final[frozenset[str]] = frozenset({"ROUNDBP_B1_variance_ratio"})

HISTORICAL_POSITIVES: Final[tuple[str, ...]] = (
    "TOP5_T5_recent",
    "NF_U2_recent",
    "NF_U4_recent",
    "TR2_D",
    "TV_C",
    "MR_M11_long",
    "MR_M01_long",
    "USDF_M16_long_total",
)

TIER_SETS: Final[dict[str, set[str]]] = {
    "A": {"A"},
    "A+B": {"A", "B"},
    "A+B+C": {"A", "B", "C"},
    "C": {"C"},
    "D": {"D"},
}
#: 主たる推定は A と A+B。C を含む推定は感度（C は結果を見た後に修正された行で、A と同じ重みにしない）。
SHRINKAGE_PRIMARY: Final[tuple[str, ...]] = ("A",)
#: A+B は計算するが、B の比較可能な行（T-R2 D）は同じ span の変種として T-R C にまとめられるので、A と同一になる。
#: 独立な頑健性確認ではない。
SHRINKAGE_SAME_AS_A: Final[tuple[str, ...]] = ("A+B",)
SHRINKAGE_SENSITIVITY: Final[tuple[str, ...]] = ("A+B+C",)


def _financing_cells() -> dict[str, Any]:
    """#495 の 8 cell（金利基準 × markup）から、financing の drag（Sharpe の単位）と符号の変化を読む。"""
    results = json.loads(USD_FACTOR_RESULTS.read_text(encoding="utf-8"))["results"]
    out: dict[str, Any] = {}
    for track in ("M15", "M16"):
        cells = results[f"{track}_long"]["pnl_decomposition"]["total_economic"]
        sharpe = {k: float(v["sharpe"]) for k, v in cells.items()}
        signs = {s > 0 for s in sharpe.values()}
        out[track] = {"cells": sharpe, "sign_changes_across_cells": len(signs) > 1}
    m16 = out["M16"]["cells"]
    base = m16["policy_contemporaneous|0.0000"]
    out["drag_sharpe"] = {
        "optimistic_markup_0": 0.0,
        "central_markup_0_5pct": round(base - m16["policy_contemporaneous|0.0050"], 3),
        "markup_1pct": round(base - m16["policy_contemporaneous|0.0100"], 3),
        "conservative_markup_2pct": round(base - m16["policy_contemporaneous|0.0200"], 3),
    }
    out["drag_source"] = (
        "artifacts/research/usd_factor_financing/development.json results.M16_long.pnl_decomposition.total_economic（policy_contemporaneous の markup 0 からの Sharpe の低下）。USD-factor book の参照値"
    )
    return out


def _tc_drag_cells(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """記録された gross − TC-net（financing 抜き）の Sharpe 差を、primary の比較可能な行で要約する。"""
    drags = sorted(
        float(r["gross_sharpe"]) - float(r["sharpe_ex_financing"])
        for r in rows
        if r.get("sharpe_comparable")
        and r.get("is_primary")
        and not r.get("invalid")
        and r.get("gross_sharpe") is not None
        and r.get("financing_included") in (None, "NONE")
    )
    q = statistics.quantiles(drags, n=4)
    return {
        "cells": {
            "slowest_recorded": round(drags[0], 3),
            "p25": round(q[0], 3),
            "median": round(q[1], 3),
            "p75": round(q[2], 3),
        },
        "rows": len(drags),
        "reading": "遅い月次 book（M01・M11・T-V）は 0.01〜0.04、日次・週次の book は 0.4〜2.5",
    }


def _siblings(rows: list[dict[str, Any]], row: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        r
        for r in rows
        if r is not row
        and r.get("mechanism_id") == row.get("mechanism_id")
        and r.get("is_primary")
        and not r.get("invalid")
        and r.get("span_dates") != row.get("span_dates")
    ]


def _positive_audit(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {r["track_id"]: r for r in rows}
    out = []
    for track in HISTORICAL_POSITIVES:
        r = by_id[track]
        out.append(
            {
                "track_id": track,
                "evidence_tier": r["evidence_tier"],
                "result_status": r["result_status"],
                "span": r["span_label"],
                "calendar_years": r["calendar_years"],
                "gross_sharpe": r["gross_sharpe"],
                "sharpe_ex_financing": r["sharpe_ex_financing"],
                "judged_net_sharpe_incl_approx_financing": r[
                    "judged_net_sharpe_incl_approx_financing"
                ],
                "full_retail_net": r["full_retail_net"],
                "null_percentile": r["null_percentile"],
                "p_value": r["p_value"],
                "null_stats_basis": r["null_stats_basis"],
                "effective_n": r["effective_n"],
                "effective_n_kind": r["effective_n_kind"],
                "loo_worst": r["loo_worst"],
                "concentration_top10": r["concentration_top10"],
                "max_dd": r["max_dd"],
                "post_result_correction": r["post_result_correction"],
                "mde_sharpe_at_span": None
                if not r["calendar_years"]
                else round(fm.mde_sharpe(float(r["calendar_years"])), 3),
                "forward_eligibility": rules.forward_eligibility(r, _siblings(rows, r)),
            }
        )
    return out


def build() -> dict[str, Any]:
    rows = syn.load_ledger()
    economic = [r for r in rows if r["track_id"] not in NON_ECONOMIC_TESTS]
    by_id = {r["track_id"]: r for r in rows}
    financing = _financing_cells()
    tc = _tc_drag_cells(rows)

    #: gross は financing を含まない行だけ（#495 の total 行の gross は carry を含む）
    gross_rows = [r for r in rows if r.get("financing_included") in (None, "NONE")]
    shrink = {
        f"{name}|{measure}": syn.shrinkage(
            gross_rows if measure == "gross_sharpe" else rows, TIER_SETS[name], measure=measure
        )
        for name in (*SHRINKAGE_PRIMARY, *SHRINKAGE_SAME_AS_A, *SHRINKAGE_SENSITIVITY)
        for measure in (syn.SHARPE, "gross_sharpe")
    }
    prior = shrink[f"A|{syn.SHARPE}"]["new_candidate_prior"]

    eligibility = [
        rules.forward_eligibility(r, _siblings(rows, r))
        for r in rows
        if r["evidence_tier"] in {"A", "B", "C"} and r.get("is_primary")
    ]

    return {
        "status": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
        "no_alpha_computed": True,
        "tiers": syn.TIERS,
        "hypothesis_counts": syn.hypothesis_counts(rows),
        "null_comparison": {
            "all_tests": {
                name: syn.null_comparison(rows, tiers) for name, tiers in TIER_SETS.items()
            },
            "economic_tests_only": {
                name: syn.null_comparison(economic, tiers) for name, tiers in TIER_SETS.items()
            },
            "non_economic_excluded": sorted(NON_ECONOMIC_TESTS),
            "p_value_caveat": "p は cycle ごとに定義が違う（片側の permutation / circular shift、両側の bootstrap、family-max）。数えるのは目安",
        },
        "shrinkage": {
            "primary": list(SHRINKAGE_PRIMARY),
            "same_as_A_not_an_independent_check": list(SHRINKAGE_SAME_AS_A),
            "sensitivity_only": list(SHRINKAGE_SENSITIVITY),
            "note": (
                "Sharpe は全て sharpe_ex_financing（TC-net、financing 抜き）。C を含む推定の τ̂ は主に cost の違い"
                "（TOP5_T4・T3 の −1.6 前後）で生じ、signal の質のばらつきではない。gross の推定では τ̂ = 0"
            ),
            "fits": shrink,
        },
        "historical_positive_audit": _positive_audit(rows),
        "forward_eligibility_all_primary_ABC": {
            "rows_checked": len(eligibility),
            "eligible_to_raise": [
                e["track_id"] for e in eligibility if e["eligible_to_raise_to_human"]
            ],
            "most_checks_passed": sorted(
                eligibility, key=lambda e: (-len(e["passed"]), e["track_id"])
            )[:8],
        },
        "broker_auth_trigger": {
            "M15": rules.broker_auth_trigger(
                by_id["USDF_M15_long_exfin"],
                sign_changes_across_financing_cells=financing["M15"]["sign_changes_across_cells"],
            ),
            "M16": rules.broker_auth_trigger(
                by_id["USDF_M16_long_exfin"],
                sign_changes_across_financing_cells=financing["M16"]["sign_changes_across_cells"],
            ),
            "financing_cells": {k: financing[k] for k in ("M15", "M16")},
        },
        "paid_data_trigger_evaluation": rules.PAID_DATA_TRIGGER_EVALUATION,
        "power_landscape": fm.power_landscape(),
        "aggregation_scenarios": fm.aggregation_scenarios(),
        "objective_table": fm.objective_table(
            financing_drag_sharpe={
                "optimistic": financing["drag_sharpe"]["optimistic_markup_0"],
                "central": financing["drag_sharpe"]["central_markup_0_5pct"],
                "conservative": financing["drag_sharpe"]["conservative_markup_2pct"],
            },
            tc_drag_sharpe=tc["cells"],
            #: prior は financing 抜きの TC-net。全 cost 後の DD には central の financing drag を引いた値を使う
            prior_mean=round(prior["mean"] - financing["drag_sharpe"]["central_markup_0_5pct"], 3),
            prior_sd=prior["sd"],
        ),
        "drag_inputs": {
            "financing": financing["drag_sharpe"],
            "financing_source": financing["drag_source"],
            "transaction_cost": tc,
        },
        "forward_information": {
            "tier_A_new_candidate_prior": fm.forward_information(
                prior_mean=prior["mean"], prior_sd=prior["sd"]
            ),
            "generic_prior_N(0.1,0.15)": fm.forward_information(prior_mean=0.1, prior_sd=0.15),
        },
        "rules": {
            "closure_principle": rules.CLOSURE_PRINCIPLE,
            "closed": rules.CLOSED,
            "open": rules.OPEN,
            "protected_information_ledger": rules.PROTECTED_INFORMATION_LEDGER,
            "d_m3": rules.D_M3_TOKEN,
            "forward_eligibility_conditions": rules.FORWARD_ELIGIBILITY_CONDITIONS,
            "broker_auth_trigger": rules.BROKER_AUTH_TRIGGER,
            "paid_data_trigger": rules.PAID_DATA_TRIGGER,
            "stop": rules.STOP_CONDITIONS,
            "continue": rules.CONTINUE_CONDITIONS,
            "pause_policy": rules.PAUSE_POLICY,
            "path_comparison": rules.PATH_COMPARISON,
        },
    }


def main() -> None:
    digest = write_provenance(OUT, build(), overwrite=True)
    print(f"wrote {OUT} sha256={digest}")


if __name__ == "__main__":
    main()
