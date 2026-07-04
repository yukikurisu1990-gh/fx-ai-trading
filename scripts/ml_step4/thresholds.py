"""Validation-only threshold selector (fail-closed).

Selects exactly one confidence threshold from the pre-declared set
``{0.35, 0.40, 0.45}`` using validation-window metrics only. The frozen holdout
is never inspected here (the function takes no holdout input). All rejected
threshold variants are recorded with their validation metrics.

Selection metric: the contract's primary decision metric, daily portfolio
Sharpe on the validation window. Ties resolve deterministically: prefer the
production-default threshold (0.40) if tied, else the smallest threshold.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from . import contract


class ThresholdSelectionError(ValueError):
    """Raised when threshold selection cannot proceed under the contract."""


@dataclass(frozen=True)
class ThresholdSelection:
    """Result of a validation-only threshold selection."""

    selected_threshold: float
    selection_metric: str
    selected_metrics: dict[str, Any]
    rejected: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "selected_threshold": self.selected_threshold,
            "selection_metric": self.selection_metric,
            "selected_validation_metrics": self.selected_metrics,
            "rejected_variants": self.rejected,
            "candidates": list(contract.THRESHOLD_CANDIDATES),
            "holdout_inspected": False,
        }


def select_threshold(
    validation_metrics_by_threshold: dict[float, dict[str, Any]],
    *,
    selection_metric: str = "daily_portfolio_sharpe",
    candidates: tuple[float, ...] = contract.THRESHOLD_CANDIDATES,
    production_default: float = contract.PRODUCTION_DEFAULT_THRESHOLD,
) -> ThresholdSelection:
    """Return exactly one threshold selected on validation metrics only."""
    if not validation_metrics_by_threshold:
        raise ThresholdSelectionError("no validation metrics provided")

    allowed = set(candidates)
    scored: list[tuple[float, float, dict[str, Any]]] = []
    for thr, metrics in validation_metrics_by_threshold.items():
        thr_f = float(thr)
        if thr_f not in allowed:
            raise ThresholdSelectionError(
                f"threshold {thr_f} is not a registered candidate {sorted(allowed)}"
            )
        if not isinstance(metrics, dict) or selection_metric not in metrics:
            raise ThresholdSelectionError(
                f"threshold {thr_f} missing selection metric {selection_metric!r}"
            )
        value = metrics[selection_metric]
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ThresholdSelectionError(f"threshold {thr_f} has non-finite {selection_metric!r}")
        scored.append((thr_f, float(value), dict(metrics)))

    # Deterministic pick: max selection metric; tie -> prefer production default,
    # else the smallest threshold value.
    best_value = max(v for _, v, _ in scored)
    tied = [thr for thr, v, _ in scored if v == best_value]
    selected = production_default if production_default in tied else min(tied)

    selected_metrics: dict[str, Any] = {}
    rejected: list[dict[str, Any]] = []
    for thr, _, metrics in sorted(scored, key=lambda t: t[0]):
        if thr == selected:
            selected_metrics = metrics
        else:
            rejected.append({"threshold": thr, "validation_metrics": metrics, "selected": False})

    return ThresholdSelection(
        selected_threshold=selected,
        selection_metric=selection_metric,
        selected_metrics=selected_metrics,
        rejected=rejected,
    )
