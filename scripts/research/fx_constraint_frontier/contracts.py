# ruff: noqa: E501 -- research prose
"""統計の契約 S0〜S4 の合成の較正（事前登録 §5）。実の候補・価格の data を使わない。

model（§5.1）:
- F family × W variant。block の長さ T 年で、variant の年率の Sharpe の推定 = 真の値 + 誤差、誤差の分散 1 / T。
- 誤差の相関: 同じ family の中 ρ_w、family の間 ρ_f（共通の USD factor の scenario だけ 0.3）。
- variant の真の値 = family の値 + N(0, 0.1²)。
- family の portfolio（W variant の等しい重み）の Sharpe は、平均 / √c_w（c_w = (1 + (W − 1)ρ_w) / W）で、推定の誤差の分散は 1 / T。

全ての契約の最後は同じ G4: 採用した unit を S の推定で重み付け（w ∝ R⁻¹ x_S、E の data を見ない）、
E の推定 Ŝ_E = wᵀy / √(wᵀRw) に system の prior N(0, τ²) を課し、事後の平均 ≥ 1.0 なら GO。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
from scipy.stats import norm

F: Final[int] = 6
W: Final[int] = 4
TAU_SYS: Final[float] = 0.4
HETERO_SD: Final[float] = 0.1
SEED: Final[int] = 20261011
REPS: Final[int] = 20_000
ALPHA_FW: Final[float] = 0.10
MIN_POINT: Final[float] = 0.3
E_T_CRIT: Final[float] = float(norm.ppf(0.90))  # 1.2816
TAU_FLOOR: Final[float] = 0.1  # S1 / S2 の経験 Bayes の τ の下限
CONTRACTS: Final[tuple[str, ...]] = ("S0", "S1", "S2", "S3", "S4")


@dataclass(frozen=True)
class Scenario:
    name: str
    family_theta: tuple[float, ...]  # 長さ F
    rho_w: float = 0.7
    rho_f: float = 0.0
    prior_mean: float = 0.0
    cost_sd: float = 0.0  # 真の family の値を動かす（§5.2 の C、文面どおり）


def _f(*vals: float) -> tuple[float, ...]:
    return tuple(list(vals) + [0.0] * (F - len(vals)))


SCENARIOS: Final[tuple[Scenario, ...]] = (
    Scenario("Z0", _f()),
    Scenario("W1", _f(0.4)),
    Scenario("W2", _f(0.4, 0.4)),
    Scenario("M1", _f(0.8)),
    Scenario("M2", _f(0.8, 0.8)),
    Scenario("M3", _f(0.8, 0.8, 0.8)),
    Scenario("U", _f(0.8, 0.8), rho_f=0.3),
    Scenario("P", _f(), prior_mean=0.6),
    Scenario("C", _f(0.8, 0.8), cost_sd=0.15),
    Scenario("R", _f(0.8, 0.8), rho_w=0.9),
)
POWER_SCENARIOS: Final[tuple[str, ...]] = ("W1", "W2", "M1", "M2", "M3")
NULL_SCENARIOS: Final[tuple[str, ...]] = ("Z0", "P")


def variant_corr(rho_w: float, rho_f: float) -> np.ndarray:
    fam = np.repeat(np.arange(F), W)
    c = np.where(fam[:, None] == fam[None, :], rho_w, rho_f)
    np.fill_diagonal(c, 1.0)
    return c


def family_corr(rho_w: float, rho_f: float) -> np.ndarray:
    """family の portfolio の推定の誤差の相関（= 真の return の相関）。"""
    cw = (1 + (W - 1) * rho_w) / W
    r = np.full((F, F), rho_f / cw)
    np.fill_diagonal(r, 1.0)
    return r


def li_ji_meff(corr: np.ndarray) -> float:
    """Li & Ji（2005）の実効の試行数。"""
    lam = np.abs(np.linalg.eigvalsh(corr))
    return float(np.sum((lam >= 1).astype(float) + (lam - np.floor(lam))))


def _draw(rng: np.random.Generator, chol: np.ndarray, t: float, n: int) -> np.ndarray:
    z = rng.standard_normal((n, chol.shape[0]))
    return (z @ chol.T) / np.sqrt(t)


@dataclass(frozen=True)
class Draw:
    theta_v: np.ndarray  # (n, F·W) variant の真の値
    theta_fam: np.ndarray  # (n, F) family の portfolio の真の Sharpe
    xs_h1: np.ndarray  # S の前半の variant の推定
    xs_h2: np.ndarray
    ye: np.ndarray  # E の variant の推定
    cw: float
    rf: np.ndarray  # family の相関
    rho_f: float


def draw(sc: Scenario, t_s: float, t_e: float, n: int, rng: np.random.Generator) -> Draw:
    fam_theta = np.tile(np.asarray(sc.family_theta, float), (n, 1))
    if sc.cost_sd > 0:
        fam_theta = fam_theta + rng.normal(0.0, sc.cost_sd, size=(n, F))
    theta_v = np.repeat(fam_theta, W, axis=1) + rng.normal(0.0, HETERO_SD, size=(n, F * W))
    chol = np.linalg.cholesky(variant_corr(sc.rho_w, sc.rho_f))
    xs_h1 = theta_v + _draw(rng, chol, t_s / 2, n)
    xs_h2 = theta_v + _draw(rng, chol, t_s / 2, n)
    ye = theta_v + _draw(rng, chol, t_e, n)
    cw = (1 + (W - 1) * sc.rho_w) / W
    theta_fam = theta_v.reshape(n, F, W).mean(axis=2) / np.sqrt(cw)
    return Draw(theta_v, theta_fam, xs_h1, xs_h2, ye, cw, family_corr(sc.rho_w, sc.rho_f), sc.rho_f)


def _fam(x: np.ndarray, cw: float) -> np.ndarray:
    n = x.shape[0]
    return x.reshape(n, F, W).mean(axis=2) / np.sqrt(cw)


def _system(
    mask: np.ndarray, w_raw: np.ndarray, y: np.ndarray, theta: np.ndarray, r: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """採用した unit の system の E の推定と真の Sharpe（重みは S の推定から、E を見ない）。"""
    n = mask.shape[0]
    est = np.full(n, np.nan)
    tru = np.full(n, np.nan)
    for i in np.flatnonzero(mask.any(axis=1)):
        idx = np.flatnonzero(mask[i])
        sub = r[np.ix_(idx, idx)]
        w = np.linalg.solve(sub, np.maximum(w_raw[i, idx], 1e-6))
        den = float(np.sqrt(w @ sub @ w))
        est[i] = float(w @ y[i, idx]) / den
        tru[i] = float(w @ theta[i, idx]) / den
    return est, tru


def _go(est: np.ndarray, t_e: float) -> np.ndarray:
    k = TAU_SYS**2 * t_e
    post = est * k / (k + 1)
    return np.nan_to_num(post, nan=-np.inf) >= 1.0, post


def _eb_posterior_pos(m: np.ndarray, se2: float, prior_mean: float) -> np.ndarray:
    """family の間の経験 Bayes（平均は prior に固定、τ² はモーメント、下限 TAU_FLOOR²）。P(θ > 0)。"""
    tau2 = np.maximum(np.mean((m - prior_mean) ** 2, axis=1) - se2, TAU_FLOOR**2)[:, None]
    shrink = tau2 / (tau2 + se2)
    pm = prior_mean + shrink * (m - prior_mean)
    psd = np.sqrt(shrink * se2)
    return norm.cdf(pm / psd)


def run_contract(
    name: str, d: Draw, t_s: float, t_e: float, prior_mean: float, p1: float = 0.99
) -> dict[str, np.ndarray]:
    """返り値: retained（(n, F) の family の残存）、go、post、true_sys。"""
    n = d.xs_h1.shape[0]
    xs = (d.xs_h1 + d.xs_h2) / 2
    if name in ("S0", "S4"):
        m_trials = float(F * W) if name == "S0" else li_ji_meff(variant_corr_from_draw(d))
        zc = float(norm.ppf(1 - ALPHA_FW / m_trials))
        ok = (xs * np.sqrt(t_s) >= zc) & (xs >= MIN_POINT) & (d.xs_h1 > 0) & (d.xs_h2 > 0)
        # family ごとに S の最良の通過 variant を 1 つ選ぶ
        score = np.where(ok, xs, -np.inf).reshape(n, F, W)
        best = score.argmax(axis=2)
        has = np.isfinite(score.max(axis=2))
        rows = np.arange(n)[:, None]
        cols = np.arange(F)[None, :] * W + best
        y_best = d.ye[rows, cols]
        x_best = xs[rows, cols]
        th_best = d.theta_v[rows, cols]
        keep = has & (y_best * np.sqrt(t_e) > E_T_CRIT)
        r_unit = np.full((F, F), d.rho_f)
        np.fill_diagonal(r_unit, 1.0)
        est, tru = _system(keep, x_best, y_best, th_best, r_unit)
        go, post = _go(est, t_e)
        return {"retained": keep, "go": go, "post": post, "true_sys": tru}
    mf_s = _fam(xs, d.cw)
    mf_e = _fam(d.ye, d.cw)
    if name == "S3":
        zc = float(norm.ppf(1 - ALPHA_FW / F))
        adm = mf_s * np.sqrt(t_s) >= zc
        keep = adm & (mf_e * np.sqrt(t_e) > E_T_CRIT)
        est, tru = _system(keep, mf_s, mf_e, d.theta_fam, d.rf)
        go, post = _go(est, t_e)
        return {"retained": keep, "go": go, "post": post, "true_sys": tru}
    ppos = _eb_posterior_pos(mf_s, 1.0 / t_s, prior_mean)
    if name == "S1":
        keep = ppos >= p1
        est, tru = _system(keep, mf_s, mf_e, d.theta_fam, d.rf)
        go, post = _go(est, t_e)
        return {"retained": keep, "go": go, "post": post, "true_sys": tru}
    if name == "S2":
        adm = ppos >= 0.5
        est, tru = _system(adm, mf_s, mf_e, d.theta_fam, d.rf)
        passed = np.nan_to_num(est, nan=-np.inf) * np.sqrt(t_e) >= E_T_CRIT
        keep = adm & passed[:, None]
        go, post = _go(np.where(passed, est, np.nan), t_e)
        return {"retained": keep, "go": go, "post": post, "true_sys": tru}
    raise ValueError(name)


def variant_corr_from_draw(d: Draw) -> np.ndarray:
    rho_w = (d.cw * W - 1) / (W - 1)
    return variant_corr(rho_w, d.rho_f)


def metrics(sc: Scenario, d: Draw, res: dict[str, np.ndarray]) -> dict[str, float]:
    designed = np.asarray(sc.family_theta) > 0
    actual_pos = d.theta_fam > 0
    null = (~designed)[None, :] & ~actual_pos
    true = designed[None, :] & actual_pos
    kept = res["retained"]
    go = res["go"]
    tru = res["true_sys"]
    fwer = float(np.mean((kept & null).any(axis=1)))
    power = float(np.mean((kept & true).any(axis=1))) if designed.any() else float("nan")
    false_go = float(np.mean(go & (np.nan_to_num(tru, nan=-np.inf) < 1.0)))
    go_rate = float(np.mean(go))
    bias = float(np.mean((res["post"] - tru)[go])) if go.any() else float("nan")
    return {"fwer": fwer, "power": power, "false_go": false_go, "go": go_rate, "bias": bias}


def evaluate(
    t_s: float = 4.67, t_e: float = 6.4, reps: int = REPS, p1: float = 0.99, seed: int = SEED
) -> dict[str, dict[str, dict[str, float]]]:
    out: dict[str, dict[str, dict[str, float]]] = {}
    for j, sc in enumerate(SCENARIOS):
        d = draw(sc, t_s, t_e, reps, np.random.default_rng(seed + j))
        out[sc.name] = {
            c: metrics(sc, d, run_contract(c, d, t_s, t_e, sc.prior_mean, p1)) for c in CONTRACTS
        }
    return out


def calibrate_p1(
    t_s: float = 4.67, t_e: float = 6.4, reps: int = REPS, seed: int = SEED
) -> tuple[float, float]:
    """Z0 だけで、S1 の FWER が S0 の Z0 の FWER 以下になる最小の p₁（§5.3）。"""
    z0 = SCENARIOS[0]
    d = draw(z0, t_s, t_e, reps, np.random.default_rng(seed))
    target = metrics(z0, d, run_contract("S0", d, t_s, t_e, 0.0))["fwer"]
    grid = np.round(
        np.concatenate([np.arange(0.50, 0.99, 0.01), np.arange(0.990, 0.99991, 0.0005)]), 5
    )
    for p in grid:
        f = metrics(z0, d, run_contract("S1", d, t_s, t_e, 0.0, float(p)))["fwer"]
        if f <= target:
            return float(p), target
    return float(grid[-1]), target


def select(results: dict[str, dict[str, dict[str, float]]]) -> dict[str, object]:
    """§5.5 の採用の規則。"""
    base = results
    s0_z0 = base["Z0"]["S0"]["fwer"]
    n_const = {"S1": 2, "S2": 1, "S3": 0, "S4": 0}
    s0_power = float(np.mean([base[s]["S0"]["power"] for s in POWER_SCENARIOS]))
    s0_bias = float(np.nanmean([base[s]["S0"]["bias"] for s in base]))
    verdict: dict[str, dict[str, object]] = {}
    for c in ("S1", "S2", "S3", "S4"):
        c1 = all(base[s][c]["fwer"] <= min(s0_z0 + 0.01, 0.10) for s in NULL_SCENARIOS) and all(
            base[s][c]["false_go"] <= base[s]["S0"]["false_go"] + 0.01 for s in base
        )
        pw = float(np.mean([base[s][c]["power"] for s in POWER_SCENARIOS]))
        c2 = pw >= s0_power + 0.10
        b = float(np.nanmean([base[s][c]["bias"] for s in base]))
        c3 = not (b > s0_bias + 0.05) if np.isfinite(b) and np.isfinite(s0_bias) else True
        c4 = n_const[c] <= 3
        verdict[c] = {
            "c1_false_positive": c1,
            "c2_power": c2,
            "c3_bias": c3,
            "c4_constants": c4,
            "c5_auditable": True,
            "mean_power": round(pw, 4),
            "mean_bias": None if not np.isfinite(b) else round(b, 4),
            "passes": bool(c1 and c2 and c3 and c4),
        }
    passing = [c for c in verdict if verdict[c]["passes"]]
    if not passing:
        chosen = "S0"
    else:
        passing.sort(key=lambda c: (-float(verdict[c]["mean_power"]), n_const[c]))  # type: ignore[arg-type]
        chosen = passing[0]
        if len(passing) > 1:
            a, b2 = passing[0], passing[1]
            if (
                abs(float(verdict[a]["mean_power"]) - float(verdict[b2]["mean_power"])) <= 0.02
                and n_const[b2] < n_const[a]
            ):  # type: ignore[arg-type]
                chosen = b2
    return {
        "s0_z0_fwer": s0_z0,
        "s0_mean_power": round(s0_power, 4),
        "s0_mean_bias": None if not np.isfinite(s0_bias) else round(s0_bias, 4),
        "verdict": verdict,
        "chosen": chosen,
    }


def component_power_one_family(
    contract: str, s: float, y: float, reps: int = REPS, p1: float = 0.99, seed: int = SEED
) -> float:
    """§9: 1 family が真の s、他は 0。独立の年数 Y を 0.42 / 0.58 に分けた検出力。"""
    sc = Scenario("ONE", _f(s))
    t_s, t_e = 0.42 * y, 0.58 * y
    d = draw(sc, t_s, t_e, reps, np.random.default_rng(seed))
    return metrics(sc, d, run_contract(contract, d, t_s, t_e, 0.0, p1))["power"]
