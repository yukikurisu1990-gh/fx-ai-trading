# ruff: noqa: E501 -- contract prose
"""G4 の prior を system の Sharpe に直接課すための契約（裁定 `fx_system_architecture_ruling_2026_10.md` §5）。

component ごとに独立な N(0, τ_c²) の prior を置き、符号と重みを選んで最適に合成すると、system の達成しうる Sharpe の
大きさは √(Σ s_i²) で、その尺度は τ_c · √k_eff になる（k_eff は等相関 ρ の実効の数 k / (1 + (k − 1) ρ)）。
τ_c に system の τ をそのまま使うと、system の prior は τ√k_eff に緩む（G4 の抜け穴）。
component の prior は、含意する system の尺度が G4 の τ と一致するよう τ_c = τ_sys / √k_eff に縮める。
"""

from __future__ import annotations

import math


def effective_count(k: int, rho: float) -> float:
    if k < 1:
        raise ValueError("k ≥ 1")
    if not -1.0 / max(k - 1, 1) < rho < 1.0 and k > 1:
        raise ValueError("等相関 ρ が範囲外")
    return k / (1 + (k - 1) * rho)


def implied_system_prior_scale(component_tau: float, k: int, rho: float = 0.0) -> float:
    """component の prior の尺度 τ_c から、system の達成しうる Sharpe の prior の尺度。"""
    return component_tau * math.sqrt(effective_count(k, rho))


def calibrated_component_tau(system_tau: float, k: int, rho: float = 0.0) -> float:
    """含意する system の尺度が system_tau と一致する component の τ_c。"""
    return system_tau / math.sqrt(effective_count(k, rho))


def assert_not_loosened(component_tau: float, system_tau: float, k: int, rho: float = 0.0) -> None:
    """component の prior が system の prior を緩めていれば拒否する。"""
    implied = implied_system_prior_scale(component_tau, k, rho)
    if implied > system_tau * (1 + 1e-9):
        raise ValueError(
            f"component の prior（τ_c = {component_tau}）は system の prior を {implied:.3f} に緩める（G4 の τ = {system_tau}）"
        )
