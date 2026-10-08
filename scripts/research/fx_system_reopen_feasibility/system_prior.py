# ruff: noqa: E501 -- contract prose
"""G4 の prior を system の Sharpe に直接課すための契約（裁定 `fx_system_architecture_ruling_2026_10.md` §5）。

component の真の Sharpe の vector s に prior s ~ N(0, τ_c² · C)（C は component の prior の相関、既定は単位行列）を置き、
component の return の相関 R の下で符号と重みを最適に選ぶと、system の達成しうる Sharpe は S = √(sᵀ R⁻¹ s)。

- **2 次の moment**: E[S²] = τ_c² · tr(R⁻¹ C)。C = I なら tr(R⁻¹) で、等相関 ρ > 0 では k より大きい（hedge が達成しうる Sharpe を上げる）。
  τ_c に system の τ をそのまま使うと、system の prior は緩む（G4 の抜け穴）。
- **tail**: G4 の prior N(0, τ_sys²) の下の P(system の Sharpe > 1) = 1 − Φ(1/τ_sys) と、component の prior が含意する P(S > 1) を比べる。
  2 次の moment を合わせても tail は合わない（S は χ 型の分布）ので、tail の検査を別に行う。

最初の版（2026-10-08、`96796d5`）は、k / (1 + (k − 1)ρ) を実効の数に使っていた。これは等しい重み・同じ符号の合成の量で、
最適な合成の量ではなく、ρ > 0 で抜け穴を残していた（独立レビュー Statistician の指摘で修正。P1 の計算はこの module を使っていない）。
"""

from __future__ import annotations

import math

import numpy as np


def _corr(k: int, rho: float) -> np.ndarray:
    r = np.full((k, k), float(rho))
    np.fill_diagonal(r, 1.0)
    if np.min(np.linalg.eigvalsh(r)) <= 0:
        raise ValueError("相関行列が正定値でない")
    return r


def second_moment_factor(r: np.ndarray, c: np.ndarray | None = None) -> float:
    """E[S²] / τ_c² = tr(R⁻¹ C)。"""
    c = np.eye(len(r)) if c is None else c
    return float(np.trace(np.linalg.solve(r, c)))


def implied_system_prior_scale(component_tau: float, k: int, rho: float = 0.0) -> float:
    """component の prior N(0, τ_c² I) が含意する、system の達成しうる Sharpe の RMS。"""
    return component_tau * math.sqrt(second_moment_factor(_corr(k, rho)))


def calibrated_component_tau(system_tau: float, k: int, rho: float = 0.0) -> float:
    """含意する system の RMS が system_tau と一致する τ_c（2 次の moment だけを合わせる）。"""
    return system_tau / math.sqrt(second_moment_factor(_corr(k, rho)))


def g4_tail(system_tau: float, threshold: float = 1.0) -> float:
    """G4 の prior N(0, τ_sys²) の下の P(system の Sharpe > threshold)。"""
    return 0.5 * math.erfc(threshold / (system_tau * math.sqrt(2)))


def implied_tail(
    component_tau: float,
    k: int,
    rho: float = 0.0,
    threshold: float = 1.0,
    n: int = 200_000,
    seed: int = 20261008,
) -> float:
    """component の prior が含意する P(√(sᵀR⁻¹s) > threshold)（Monte Carlo、決定的）。"""
    r = _corr(k, rho)
    rng = np.random.default_rng(seed)
    s = rng.normal(0.0, component_tau, size=(n, k))
    q = np.einsum("ij,ij->i", s, np.linalg.solve(r, s.T).T)
    return float(np.mean(np.sqrt(q) > threshold))


def calibrated_component_tau_tail(
    system_tau: float, k: int, rho: float = 0.0, threshold: float = 1.0
) -> float:
    """含意する tail が G4 の tail 以下になる最大の τ_c（二分法）。"""
    target = g4_tail(system_tau, threshold)
    lo, hi = 1e-4, system_tau
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if implied_tail(mid, k, rho, threshold) <= target:
            lo = mid
        else:
            hi = mid
    return lo


def assert_not_loosened(component_tau: float, system_tau: float, k: int, rho: float = 0.0) -> None:
    """component の prior が、system の prior を 2 次の moment か tail のどちらかで緩めていれば拒否する。"""
    implied = implied_system_prior_scale(component_tau, k, rho)
    if implied > system_tau * (1 + 1e-9):
        raise ValueError(
            f"component の prior（τ_c = {component_tau}）は system の RMS を {implied:.3f} に緩める（G4 の τ = {system_tau}）"
        )
    tail = implied_tail(component_tau, k, rho)
    allowed = g4_tail(system_tau)
    if tail > allowed + 3 * math.sqrt(max(allowed, 1e-6) / 200_000):
        raise ValueError(
            f"component の prior の tail P(S > 1) = {tail:.4f} は G4 の {allowed:.4f} を超える"
        )
