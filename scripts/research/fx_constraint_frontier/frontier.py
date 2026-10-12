# ruff: noqa: E501 -- research prose
"""候補 × 制約の frontier の行列（事前登録 §1〜§4、§6、§9〜§12）。desk の計算だけで、価格の data を読まない。

入力は事前登録 §8 の凍結した表（`CANDIDATES`）と、公開の調査から lead が転記した値（`inputs.json`、出典は最終報告）。
統計の契約は、合成の較正の記録（`synthetic_contracts.json`）で選ばれたものを使う。
"""

from __future__ import annotations

import itertools
import json
import math
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, Final

import numpy as np
from scipy.stats import beta as beta_dist
from scipy.stats import norm

from scripts.research.fx_constraint_frontier import contracts as c

HERE: Final[Path] = Path(__file__).resolve().parent
TAU: Final[float] = c.TAU_SYS
E_SHARE: Final[float] = 0.58
S_SHARE: Final[float] = 0.42
Y_MAX: Final[int] = 60
FRESH_YEARS: Final[float] = 4.9
M_FLOOR: Final[float] = -5.0
HORIZONS: Final[dict[str, float | None]] = {"H0": None, "H1": 24.0, "H2": 36.0, "H3": 48.0}
DEVIATION: Final[dict[str, int]] = {
    "contract": 0,
    "E0": 0,
    "E1": 1,
    "E2": 2,
    "H0": 0,
    "H1": 2,
    "H2": 3,
    "H3": 4,
    "years_current": 0,
    "years_free_permitted": 0,
    "years_free_unknown_terms": 1,
    "years_paid": 2,
}


@dataclass(frozen=True)
class Window:
    """1 つの取引の窓（K3 は FOMC と日銀の 2 つ）。"""

    n: float
    k: float
    g: float
    sigma: float
    pair_cost_key: str  # inputs.json の cost の key


@dataclass(frozen=True)
class Candidate:
    cid: str
    windows: tuple[Window, ...]
    h0_hours: float
    d_kind: str  # "pub" / "desk"
    daily: bool  # 平日毎日の機会（延長で週末をまたぐ金曜を失う）
    years_key: str


#: 事前登録 §8.1 の凍結した値
CANDIDATES: Final[tuple[Candidate, ...]] = (
    Candidate("K1", (Window(250, 1, 2.8, 28.6, "K1"),), 6.25, "pub", True, "K1"),
    Candidate("K2", (Window(250, 1, 3.3, 27.3, "K2"),), 5.5, "pub", True, "K2"),
    Candidate(
        "K3",
        (Window(8, 1, 10.30, 60.0, "K3_FOMC"), Window(8, 1, 14.78, 98.0, "K3_BOJ")),
        22.75,
        "pub",
        False,
        "K3",
    ),
    Candidate("K4", (Window(15, 2.5, 6.0, 26.0, "K4"),), 2.0, "desk", False, "K4"),
)


def load_inputs(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or HERE / "inputs.json").read_text(encoding="utf-8"))


def d_quantiles(inp: dict[str, Any], kind: str) -> dict[str, float]:
    a, b = inp["d"][kind]["beta"]
    return {
        "p10": float(beta_dist.ppf(0.10, a, b)),
        "median": float(beta_dist.ppf(0.50, a, b)),
        "mean": float(a / (a + b)),
        "p90": float(beta_dist.ppf(0.90, a, b)),
    }


def nights(hours: float) -> int:
    return int(math.ceil(hours / 24.0))


def window_sharpe(
    w: Window,
    cost: float,
    d: float,
    horizon: float | None,
    h0: float,
    g_mode: str,
    f_night: float,
    daily: bool,
) -> float:
    """年率の net Sharpe（§1、§4）。"""
    n = w.n
    g, sigma, c_tot = w.g, w.sigma, cost
    if horizon is not None and horizon > h0:
        r = horizon / h0
        sigma = w.sigma * math.sqrt(r)
        if g_mode == "persist":
            g = w.g * math.sqrt(r)
        c_tot = cost + f_night * nights(horizon)
        if daily:
            n = w.n * 0.8  # 金曜の entry は週末をまたぐので行わない
    return math.sqrt(n * w.k) * (d * g - c_tot) / sigma


def candidate_sharpe(
    cand: Candidate, costs: dict[str, float], d: float, horizon: str, g_mode: str, f_night: float
) -> float:
    hz = HORIZONS[horizon]
    parts = [
        window_sharpe(w, costs[w.pair_cost_key], d, hz, cand.h0_hours, g_mode, f_night, cand.daily)
        for w in cand.windows
    ]
    if len(parts) == 1:
        return parts[0]
    pos = [max(p, 0.0) for p in parts]
    return math.sqrt(sum(p * p for p in pos)) if any(p > 0 for p in parts) else max(parts)


# ------------------------------------------------------------ 要る年数（§9）


def retained(contract: str, d: c.Draw, t_s: float, t_e: float) -> np.ndarray:
    """`contracts.run_contract` の retained と同じ規則（S0 / S3 / S4）。system の計算を省いた高速版。"""
    n = d.xs_h1.shape[0]
    xs = (d.xs_h1 + d.xs_h2) / 2
    if contract in ("S0", "S4"):
        m = float(c.F * c.W) if contract == "S0" else c.li_ji_meff(c.variant_corr_from_draw(d))
        zc = float(norm.ppf(1 - c.ALPHA_FW / m))
        ok = (xs * np.sqrt(t_s) >= zc) & (xs >= c.MIN_POINT) & (d.xs_h1 > 0) & (d.xs_h2 > 0)
        score = np.where(ok, xs, -np.inf).reshape(n, c.F, c.W)
        best = score.argmax(axis=2)
        has = np.isfinite(score.max(axis=2))
        y_best = d.ye[np.arange(n)[:, None], np.arange(c.F)[None, :] * c.W + best]
        return has & (y_best * np.sqrt(t_e) > c.E_T_CRIT)
    if contract == "S3":
        mf_s = c._fam(xs, d.cw)
        mf_e = c._fam(d.ye, d.cw)
        zc = float(norm.ppf(1 - c.ALPHA_FW / c.F))
        return (mf_s * np.sqrt(t_s) >= zc) & (mf_e * np.sqrt(t_e) > c.E_T_CRIT)
    raise ValueError(contract)


def _retained_power(contract: str, s: float, y: float, reps: int, seed: int) -> float:
    """1 family が真の s、他は 0。component の検出力。"""
    sc = c.Scenario("ONE", c._f(s))
    t_s, t_e = S_SHARE * y, E_SHARE * y
    d = c.draw(sc, t_s, t_e, reps, np.random.default_rng(seed))
    kept = retained(contract, d, t_s, t_e)
    return float(np.mean((d.theta_fam[:, 0] > 0) & kept[:, 0]))


@cache
def required_years(
    contract: str, s_rounded: float, reps: int = c.REPS, seed: int = c.SEED
) -> float:
    """検出力 ≥ 0.5 の最小の独立の年数（1 年刻み、1〜60）。s ≤ 0 は ∞。"""
    if s_rounded <= 0:
        return math.inf
    for y in range(1, Y_MAX + 1):
        if _retained_power(contract, s_rounded, float(y), reps, seed + y) >= 0.5:
            return float(y)
    return math.inf


def g4_required_years(s_sys: float) -> float:
    if s_sys <= 1.0:
        return math.inf
    return 1.0 / (E_SHARE * TAU**2 * (s_sys - 1.0))


def margin(avail: float, req: float) -> float:
    if not math.isfinite(req):
        return M_FLOOR
    return max(math.log(avail / req), M_FLOOR)


# ------------------------------------------------------------ frontier の点


@dataclass(frozen=True)
class Point:
    cost: str  # E0 / E1 / E2 / E3 / E4_075 / E4_050
    horizon: str
    g_mode: str
    d_level: str  # median / p10 / p90 / fixed50
    years: str  # current / free_permitted / free_unknown_terms / paid


def costs_at(inp: dict[str, Any], level: str) -> dict[str, float]:
    if level in ("E3", "E4_075", "E4_050"):
        v = {"E3": 1.0, "E4_075": 0.75, "E4_050": 0.5}[level]
        return dict.fromkeys(inp["cost"]["E0"], v)
    return dict(inp["cost"][level])


def d_at(inp: dict[str, Any], kind: str, level: str) -> float:
    if level == "fixed50":
        return 0.5
    return d_quantiles(inp, kind)[level]


def years_at(inp: dict[str, Any], key: str, level: str) -> float:
    return float(inp["years"][key][level])


def evaluate_point(inp: dict[str, Any], p: Point, contract: str) -> dict[str, Any]:
    costs = costs_at(inp, p.cost)
    f_night = float(inp["financing_bp_per_night"])
    rows: dict[str, Any] = {}
    feas_s: list[float] = []
    feas_years: list[float] = []
    for cand in CANDIDATES:
        d = d_at(inp, cand.d_kind, p.d_level)
        s = candidate_sharpe(cand, costs, d, p.horizon, p.g_mode, f_night)
        avail = years_at(inp, cand.years_key, p.years)
        req = required_years(contract, round(s, 2)) if s > 0 else math.inf
        ok = s > 0 and req <= avail
        rows[cand.cid] = {
            "d": round(d, 4),
            "s": round(s, 4),
            "years_available": avail,
            "years_required": req,
            "component_decision_grade": ok,
            "margin": round(margin(avail, req), 4),
        }
        if ok:
            feas_s.append(s)
            feas_years.append(avail)
    s_sys = math.sqrt(sum(x * x for x in feas_s)) if feas_s else 0.0
    y_sys = min(feas_years) if feas_years else 0.0
    g4_req = g4_required_years(s_sys)
    fresh_ok = s_sys * math.sqrt(FRESH_YEARS) >= 1.645
    system_ok = bool(feas_s) and g4_req <= y_sys and fresh_ok
    # 全ての net > 0 の候補で作る system（component の検出を問わない、参考）
    all_pos = [rows[k]["s"] for k in rows if rows[k]["s"] > 0]
    s_all = math.sqrt(sum(x * x for x in all_pos)) if all_pos else 0.0
    return {
        "candidates": rows,
        "system": {
            "s_sys_decision_grade_components": round(s_sys, 4),
            "years_available": y_sys,
            "g4_years_required": g4_req,
            "fresh_power_ok": fresh_ok,
            "feasible": system_ok,
            "margin": round(margin(y_sys, g4_req), 4) if feas_s else M_FLOOR,
            "s_sys_all_positive_reference": round(s_all, 4),
            "g4_years_required_all_positive_reference": g4_required_years(s_all),
        },
    }


def deviation(p: Point) -> int | None:
    if p.cost.startswith(("E3", "E4")):
        return None  # sensitivity だけ
    if p.d_level != "median" or p.g_mode != "flat":
        return None
    yk = {
        "current": "years_current",
        "free_permitted": "years_free_permitted",
        "free_unknown_terms": "years_free_unknown_terms",
        "paid": "years_paid",
    }[p.years]
    return DEVIATION[p.cost] + DEVIATION[p.horizon] + DEVIATION[yk]


def grid() -> list[Point]:
    pts = []
    for cost, hz, gm, dl, yr in itertools.product(
        ("E0", "E1", "E2", "E3", "E4_075", "E4_050"),
        ("H0", "H1", "H2", "H3"),
        ("flat", "persist"),
        ("median", "p10", "p90", "fixed50"),
        ("current", "free_permitted", "free_unknown_terms", "paid"),
    ):
        if hz == "H0" and gm == "persist":
            continue
        pts.append(Point(cost, hz, gm, dl, yr))
    return pts


def classify(points: list[tuple[Point, dict[str, Any]]]) -> dict[str, Any]:
    """§12 の規則。"""
    feasible = [(p, r) for p, r in points if r["system"]["feasible"] and deviation(p) is not None]
    if not feasible:
        return {"classification": "CONSTRAINT-A", "minimal_feasible": None}
    best = min(feasible, key=lambda pr: (deviation(pr[0]), -pr[1]["system"]["margin"]))
    dev = deviation(best[0])
    p = best[0]
    changed = [
        k
        for k, v in (
            ("cost", p.cost != "E0"),
            ("horizon", p.horizon != "H0"),
            ("years", p.years != "current"),
        )
        if v
    ]
    if dev is not None and dev <= 1:
        label = "CONSTRAINT-G"
    elif len(changed) == 1 and dev is not None and dev <= 2:
        label = {"cost": "CONSTRAINT-B", "horizon": "CONSTRAINT-C", "years": "CONSTRAINT-E"}[
            changed[0]
        ]
    elif dev is not None and dev <= 4:
        label = "CONSTRAINT-F"
    else:
        label = "CONSTRAINT-A"
    return {
        "classification": label,
        "minimal_feasible": {"point": p.__dict__, "deviation": dev, "result": best[1]},
    }


SWITCHES: Final[tuple[str, ...]] = ("cost", "horizon", "contract", "years", "d")


def shapley(
    inp: dict[str, Any], base_contract: str, chosen_contract: str, target: str
) -> dict[str, float]:
    """5 つの switch の Shapley 値（§11）。target は候補の ID か "system"。"""

    def value(on: frozenset[str]) -> float:
        p = Point(
            "E2" if "cost" in on else "E0",
            "H1" if "horizon" in on else "H0",
            "flat",
            "median" if "d" in on else "fixed50",
            "free_unknown_terms" if "years" in on else "current",
        )
        r = evaluate_point(inp, p, chosen_contract if "contract" in on else base_contract)
        return float(
            r["system"]["margin"] if target == "system" else r["candidates"][target]["margin"]
        )

    k = len(SWITCHES)
    out = {}
    for s in SWITCHES:
        others = [x for x in SWITCHES if x != s]
        tot = 0.0
        for r in range(k):
            for comb in itertools.combinations(others, r):
                wgt = math.factorial(r) * math.factorial(k - r - 1) / math.factorial(k)
                tot += wgt * (value(frozenset(comb) | {s}) - value(frozenset(comb)))
        out[s] = round(tot, 4)
    return out


def _smallest_s(contract: str, s_grid: np.ndarray, avail: float) -> float:
    """要る年数 ≤ avail となる最小の s（要る年数は s に単調に減ると仮定し、grid の上で二分探索）。"""
    lo, hi = 0, len(s_grid) - 1
    if required_years(contract, float(s_grid[hi])) > avail:
        return math.inf
    while lo < hi:
        mid = (lo + hi) // 2
        if required_years(contract, float(s_grid[mid])) <= avail:
            hi = mid
        else:
            lo = mid + 1
    return float(s_grid[lo])


def critical_thresholds(inp: dict[str, Any], contract: str) -> dict[str, Any]:
    """候補ごとの critical cost / decay / years（§38）。"""
    out = {}
    s_grid = np.round(np.arange(0.05, 3.001, 0.01), 2)
    for cand in CANDIDATES:
        avail = years_at(inp, cand.years_key, "current")
        s_need = _smallest_s(contract, s_grid, avail)
        w0 = cand.windows[0]
        d_med = d_at(inp, cand.d_kind, "median")
        c0 = costs_at(inp, "E0")[w0.pair_cost_key]
        scale = math.sqrt(w0.n * w0.k) / w0.sigma
        crit_cost = d_med * w0.g - s_need / scale if math.isfinite(s_need) else -math.inf
        crit_d = (c0 + s_need / scale) / w0.g if math.isfinite(s_need) else math.inf
        s_e0 = candidate_sharpe(
            cand, costs_at(inp, "E0"), d_med, "H0", "flat", float(inp["financing_bp_per_night"])
        )
        out[cand.cid] = {
            "years_available_current": avail,
            "s_needed_for_component_power_0_5": s_need,
            "critical_all_in_cost_bp_first_window": round(crit_cost, 3),
            "critical_d_first_window": round(crit_d, 3),
            "s_at_E0_H0_dmedian": round(s_e0, 4),
            "years_required_at_E0_H0_dmedian": required_years(contract, round(s_e0, 2))
            if s_e0 > 0
            else math.inf,
            "break_even_cost_bp_first_window": round(d_med * w0.g, 3),
        }
    return out
