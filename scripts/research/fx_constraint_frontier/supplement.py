# ruff: noqa: E501 -- research prose
"""独立レビューの後の補足の計算（2026-10-11）。**事前登録の後・結果の後**に作ったもので、分類の規則を変えない。

中身:
- A. 事前登録 §8.1 が定めたが、主の実行で計算していなかった sensitivity（K1 g = 3.3、K3 日銀 σ = 51）
- B. 事前登録 §9.5 の文面どおりの system（同じ点の net > 0 の候補の全て）と、年数の規則（候補ごと / min / max）
- C. 事前登録 §6 の grid（候補 × 契約 × 独立の年数 5 / 10 / 15 / 20 / 30 年）
- D. review の訂正の感度（E2 の USD/JPY、K1 の有料の年数、週末の規則、公表 / 実測の比 2.2）

主の記録（`frontier.json`）の code と入力は変えない。この module は frontier.py の関数を読むだけ。
"""

from __future__ import annotations

import copy
import dataclasses
import math
from typing import Any, Final

from scripts.research.fx_constraint_frontier import frontier as fr

YEARS_GRID: Final[tuple[int, ...]] = (5, 10, 15, 20, 30)
SLIP: Final[dict[str, float]] = {"E1": 0.35, "E2": 0.2}


def candidates_with(k1_g: float = 2.8, k3_boj_sigma: float = 98.0) -> tuple[fr.Candidate, ...]:
    out = []
    for cand in fr.CANDIDATES:
        if cand.cid == "K1":
            w = dataclasses.replace(cand.windows[0], g=k1_g)
            cand = dataclasses.replace(cand, windows=(w,))
        if cand.cid == "K3":
            w0, w1 = cand.windows
            cand = dataclasses.replace(
                cand, windows=(w0, dataclasses.replace(w1, sigma=k3_boj_sigma))
            )
        out.append(cand)
    return tuple(out)


def window_sharpe_weekend(
    w: fr.Window,
    cost: float,
    d: float,
    horizon: float | None,
    h0: float,
    g_mode: str,
    f_night: float,
    daily: bool,
    weekend: str,
) -> float:
    """週末の規則の変種。"literal" = n 不変（事前登録 §4 の文面）、"main" = 主の実行（H > H0 で n × 0.8）、
    "weekday" = H1 で 0.8、H2 / H3 で 0.6（木曜の entry も 48h で週末をまたぐ、review の指摘）。"""
    n = w.n
    g, sigma, c_tot = w.g, w.sigma, cost
    if horizon is not None and horizon > h0:
        r = horizon / h0
        sigma = w.sigma * math.sqrt(r)
        if g_mode == "persist":
            g = w.g * math.sqrt(r)
        c_tot = cost + f_night * fr.nights(horizon)
        if daily:
            factor = {"literal": 1.0, "main": 0.8, "weekday": 0.8 if horizon <= 24 else 0.6}[
                weekend
            ]
            n = w.n * factor
    return math.sqrt(n * w.k) * (d * g - c_tot) / sigma


def cand_s(
    cand: fr.Candidate,
    costs: dict[str, float],
    d: float,
    horizon: str,
    g_mode: str,
    f_night: float,
    weekend: str,
) -> float:
    hz = fr.HORIZONS[horizon]
    parts = [
        window_sharpe_weekend(
            w, costs[w.pair_cost_key], d, hz, cand.h0_hours, g_mode, f_night, cand.daily, weekend
        )
        for w in cand.windows
    ]
    if len(parts) == 1:
        return parts[0]
    pos = [max(p, 0.0) for p in parts]
    return math.sqrt(sum(p * p for p in pos)) if any(p > 0 for p in parts) else max(parts)


def evaluate(
    inp: dict[str, Any],
    p: fr.Point,
    contract: str,
    cands: tuple[fr.Candidate, ...],
    weekend: str = "main",
) -> dict[str, Any]:
    """候補の s と、事前登録 §9.5 の文面どおりの system（net > 0 の全て）。年数の規則を 3 通り。"""
    costs = fr.costs_at(inp, p.cost)
    f = float(inp["financing_bp_per_night"])
    rows = {}
    for cand in cands:
        d = fr.d_at(inp, cand.d_kind, p.d_level)
        s = cand_s(cand, costs, d, p.horizon, p.g_mode, f, weekend)
        avail = fr.years_at(inp, cand.years_key, p.years)
        req = fr.required_years(contract, round(s, 2)) if s > 0 else math.inf
        rows[cand.cid] = {
            "s": round(s, 4),
            "avail": avail,
            "req": req,
            "dg": bool(s > 0 and req <= avail),
        }
    pos = {k: v for k, v in rows.items() if v["s"] > 0}
    s_sys = math.sqrt(sum(v["s"] ** 2 for v in pos.values())) if pos else 0.0
    g4 = fr.g4_required_years(s_sys)
    fresh = s_sys * math.sqrt(fr.FRESH_YEARS) >= 1.645
    # 文面どおり: 候補 c が feasible ⇔ c が decision-grade かつ、c を含む system の G4 の年数 ≤ c の使える年数、かつ fresh
    literal = {k: bool(v["dg"] and g4 <= v["avail"] and fresh) for k, v in rows.items()}
    dg = [v for v in rows.values() if v["dg"]]
    s_dg = math.sqrt(sum(v["s"] ** 2 for v in dg)) if dg else 0.0
    g4_dg = fr.g4_required_years(s_dg)
    fresh_dg = s_dg * math.sqrt(fr.FRESH_YEARS) >= 1.645
    return {
        "candidates": rows,
        "system_all_positive": {"s": round(s_sys, 4), "g4_years": g4, "fresh_ok": fresh},
        "feasible_literal_9_5": any(literal.values()),
        "feasible_literal_by_candidate": literal,
        "decision_grade_system": {
            "s": round(s_dg, 4),
            "g4_years": g4_dg,
            "feasible_min_years": bool(dg and g4_dg <= min(v["avail"] for v in dg) and fresh_dg),
            "feasible_max_years": bool(dg and g4_dg <= max(v["avail"] for v in dg) and fresh_dg),
        },
    }


def section_a_b(inp: dict[str, Any], contract: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    variants = {
        "main": candidates_with(),
        "k1_g_3_3": candidates_with(k1_g=3.3),
        "k3_boj_sigma_51": candidates_with(k3_boj_sigma=51.0),
        "both": candidates_with(k1_g=3.3, k3_boj_sigma=51.0),
    }
    for name, cands in variants.items():
        n_lit = n_min = n_max = 0
        n_lit_elig = n_min_elig = n_max_elig = 0
        best_elig = 0.0
        for p in fr.grid():
            r = evaluate(inp, p, contract, cands)
            elig = fr.deviation(p) is not None
            n_lit += r["feasible_literal_9_5"]
            n_min += r["decision_grade_system"]["feasible_min_years"]
            n_max += r["decision_grade_system"]["feasible_max_years"]
            if elig:
                n_lit_elig += r["feasible_literal_9_5"]
                n_min_elig += r["decision_grade_system"]["feasible_min_years"]
                n_max_elig += r["decision_grade_system"]["feasible_max_years"]
                best_elig = max(best_elig, r["system_all_positive"]["s"])
        out[name] = {
            "feasible_points_all_672": {
                "literal_9_5": n_lit,
                "decision_grade_min_years": n_min,
                "decision_grade_max_years": n_max,
            },
            "feasible_points_classification_eligible": {
                "literal_9_5": n_lit_elig,
                "decision_grade_min_years": n_min_elig,
                "decision_grade_max_years": n_max_elig,
            },
            "max_system_all_positive_at_eligible_points": round(best_elig, 4),
            "E2_H0_median_current": evaluate(
                inp, fr.Point("E2", "H0", "flat", "median", "current"), contract, cands
            ),
            "E2_H0_p90_current": evaluate(
                inp, fr.Point("E2", "H0", "flat", "p90", "current"), contract, cands
            ),
        }
    return out


def section_c(inp: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    cands = candidates_with()
    for cost in ("E0", "E1", "E2"):
        for dl in ("median", "fixed50", "p90"):
            p = fr.Point(cost, "H0", "flat", dl, "current")
            key = f"{cost}_H0_{dl}"
            row: dict[str, Any] = {}
            for contract in ("S0", "S3", "S4"):
                r = evaluate(inp, p, contract, cands)
                row[contract] = {
                    cid: {
                        "s": v["s"],
                        "years_required": v["req"],
                        "decision_grade_at": {
                            str(y): bool(v["s"] > 0 and v["req"] <= y) for y in YEARS_GRID
                        },
                    }
                    for cid, v in r["candidates"].items()
                }
                row["system_all_positive"] = {
                    "s": r["system_all_positive"]["s"],
                    "g4_years": r["system_all_positive"]["g4_years"],
                    "g4_ok_at": {
                        str(y): bool(r["system_all_positive"]["g4_years"] <= y) for y in YEARS_GRID
                    },
                }
            out[key] = row
    return out


def _with_cost(inp: dict[str, Any], level: str, key: str, value: float) -> dict[str, Any]:
    new = copy.deepcopy(inp)
    new["cost"][level][key] = value
    return new


def section_d(inp: dict[str, Any], contract: str) -> dict[str, Any]:
    cands = candidates_with()
    out: dict[str, Any] = {}
    pts = {
        "E2_H0_median": fr.Point("E2", "H0", "flat", "median", "current"),
        "E2_H0_p90_paid": fr.Point("E2", "H0", "flat", "p90", "paid"),
    }
    variants = {
        "main": inp,
        "e2_usdjpy_fxtf_0_458": _with_cost(inp, "E2", "K2", 0.258 + 0.2),
        "e2_usdjpy_saxo_with_commission_0_73": _with_cost(inp, "E2", "K2", 0.129 + 0.4 + 0.2),
    }
    k1paid = copy.deepcopy(inp)
    k1paid["years"]["K1"]["paid"] = 4.67
    variants["k1_paid_years_4_67"] = k1paid
    ratio = copy.deepcopy(inp)
    for lvl in ("E1", "E2"):
        for k in ("K1", "K2"):
            ratio["cost"][lvl][k] = round(2.2 * (inp["cost"][lvl][k] - SLIP[lvl]) + SLIP[lvl], 4)
    variants["advertised_to_measured_ratio_2_2"] = ratio
    for name, v in variants.items():
        out[name] = {k: evaluate(v, p, contract, cands) for k, p in pts.items()}
    out["weekend_rules_E2_median"] = {
        wk: {
            hz: evaluate(inp, fr.Point("E2", hz, gm, "median", "current"), contract, cands, wk)[
                "candidates"
            ]
            for hz, gm in (("H1", "flat"), ("H3", "flat"), ("H3", "persist"))
        }
        for wk in ("literal", "main", "weekday")
    }
    out["d_equal_1_E2_H0_current"] = {
        cid: round(cand_s(cand, fr.costs_at(inp, "E2"), 1.0, "H0", "flat", 0.2, "main"), 4)
        for cid, cand in zip(("K1", "K2", "K3", "K4"), cands, strict=True)
    }
    return out


def section_e_synthetic_prereg_null() -> dict[str, Any]:
    """事前登録 §5.4 の文面どおりの null（設計で 0 の family、実現の θ の符号を問わない）で FWER を測り直し、
    p₁ を細かい grid で較正し直して、§5.5 の選択が変わるかを確かめる。主の記録と同じ seed・反復。"""
    import numpy as np

    from scripts.research.fx_constraint_frontier import contracts as c

    def fwer_designed(sc: c.Scenario, d: c.Draw, res: dict[str, np.ndarray]) -> float:
        null = ~(np.asarray(sc.family_theta) > 0)
        return float(np.mean((res["retained"] & null[None, :]).any(axis=1)))

    z0 = c.SCENARIOS[0]
    dz = c.draw(z0, 4.67, 6.4, c.REPS, np.random.default_rng(c.SEED))
    target = fwer_designed(z0, dz, c.run_contract("S0", dz, 4.67, 6.4, 0.0))
    grid = np.round(np.arange(0.50, 0.99991, 0.0005), 5)
    p1 = float(grid[-1])
    for p in grid:
        if fwer_designed(z0, dz, c.run_contract("S1", dz, 4.67, 6.4, 0.0, float(p))) <= target:
            p1 = float(p)
            break
    results: dict[str, dict[str, dict[str, float]]] = {}
    for j, sc in enumerate(c.SCENARIOS):
        d = c.draw(sc, 4.67, 6.4, c.REPS, np.random.default_rng(c.SEED + j))
        results[sc.name] = {}
        for con in c.CONTRACTS:
            res = c.run_contract(con, d, 4.67, 6.4, sc.prior_mean, p1)
            m = c.metrics(sc, d, res)
            m["fwer"] = fwer_designed(sc, d, res)
            results[sc.name][con] = m
    return {
        "s0_z0_fwer_designed_null": target,
        "s1_p1_fine_grid": p1,
        "results": results,
        "selection": c.select(results),
    }


def single_test_years(s: float, alpha: float, power: float = 0.5) -> float:
    """事前に固定した 1 つの片側検定で、全ての Y を使う場合の要る年数（比較の参考）。"""
    from scipy.stats import norm

    return ((norm.ppf(1 - alpha) + norm.ppf(power)) / s) ** 2
