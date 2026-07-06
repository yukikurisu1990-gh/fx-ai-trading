"""Effective-N estimator helper (PR #430 T-6) — pure, synthetic inputs only.

Adjusts a raw event count for overlapping-label autocorrelation (horizon 24 M15
bars) and cross-pair dependence, and applies the ``INSUFFICIENT_SAMPLE`` verdict
below the frozen floor. Computes NO strategy metrics and reads NO validation /
holdout data — the raw count, overlap fraction and correlation are supplied.
"""

from __future__ import annotations

from typing import Final

HORIZON_M15_BARS: Final[int] = 24
N_EFF_HOLDOUT_FLOOR: Final[int] = 400
RAW_HOLDOUT_TRADE_FLOOR: Final[int] = 1000
INSUFFICIENT_SAMPLE: Final[str] = "INSUFFICIENT_SAMPLE"
SUFFICIENT: Final[str] = "SAMPLE_SUFFICIENT"


class EffectiveNError(ValueError):
    """Raised when effective-N inputs violate the estimator contract."""


def effective_n(
    raw_event_count: int,
    *,
    overlap_fraction: float,
    cross_pair_corr: float,
    n_pairs: int,
    horizon_bars: int = HORIZON_M15_BARS,
    role: str = "holdout",
) -> dict:
    """Return raw + effective counts and the sufficiency verdict (fail-closed).

    ``rho_h = 1 + (H-1) * overlap_fraction`` thins overlapping labels;
    ``rho_x = 1 + (n_pairs-1) * cross_pair_corr`` discounts cross-pair
    dependence; ``N_eff = raw / rho_h / rho_x``. Non-overlapping, independent
    inputs recover ``N_eff -> raw``.
    """
    if not isinstance(raw_event_count, int) or raw_event_count < 0:
        raise EffectiveNError("raw_event_count must be a non-negative integer")
    if not (0.0 <= overlap_fraction <= 1.0):
        raise EffectiveNError("overlap_fraction must be in [0, 1]")
    if not (0.0 <= cross_pair_corr <= 1.0):
        raise EffectiveNError("cross_pair_corr must be in [0, 1]")
    if not isinstance(n_pairs, int) or n_pairs < 1:
        raise EffectiveNError("n_pairs must be a positive integer")
    if not isinstance(horizon_bars, int) or horizon_bars < 1:
        raise EffectiveNError("horizon_bars must be a positive integer")

    rho_h = 1.0 + (horizon_bars - 1) * overlap_fraction
    rho_x = 1.0 + (n_pairs - 1) * cross_pair_corr
    n_eff = raw_event_count / (rho_h * rho_x)

    verdict = SUFFICIENT
    if role == "holdout" and (
        raw_event_count < RAW_HOLDOUT_TRADE_FLOOR or n_eff < N_EFF_HOLDOUT_FLOOR
    ):
        verdict = INSUFFICIENT_SAMPLE

    return {
        "role": role,
        "raw_event_count": raw_event_count,
        "rho_h": rho_h,
        "rho_x": rho_x,
        "effective_n": n_eff,
        "n_eff_holdout_floor": N_EFF_HOLDOUT_FLOOR,
        "raw_holdout_trade_floor": RAW_HOLDOUT_TRADE_FLOOR,
        "verdict": verdict,
        "strategy_metrics_computed": False,
    }
