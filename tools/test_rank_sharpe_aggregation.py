"""Phase 9.X-I rank-3 Sharpe audit — synthetic minimum reproducible test.

Item 10 of the audit checklist. Tests whether the fold-mean Sharpe
aggregation can produce inflated rank-3 results purely from sample-size
asymmetry between ranks, without any real edge.

Three scenarios:
  A. All ranks have the same per-trade edge but rank-3 fires rarely
     (selection-effect proxy). Expected: pooled Sharpe ~ same across
     ranks. Fold-mean Sharpe may diverge if any artifact exists.
  B. Rank-3 fires sparsely with TRULY higher per-trade edge (selection
     bias). Fold-mean and pooled both reflect the higher edge.
  C. Rank-3 fires sparsely with same edge BUT fewer trades per fold
     causes some folds to fall below the n>=2 threshold (returning 0
     for that fold). Tests whether the n<2 fallback distorts mean.

Run:  python tools/test_rank_sharpe_aggregation.py
"""

from __future__ import annotations

import math
import statistics

import numpy as np


def _sharpe(values: list[float]) -> float:
    """Mirror of scripts/compare_multipair_v22_risk_sizing.py _sharpe."""
    if len(values) < 2:
        return 0.0
    mu = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)  # population
    return (mu / math.sqrt(var)) if var > 0 else 0.0


def fold_mean_vs_pooled(
    per_fold_pnls: list[list[float]],
    label: str,
) -> tuple[float, float, int]:
    fold_sharpes = [_sharpe(p) for p in per_fold_pnls]
    fold_mean = statistics.mean(fold_sharpes) if fold_sharpes else 0.0
    all_pnls = [v for f in per_fold_pnls for v in f]
    pooled = _sharpe(all_pnls)
    n_total = len(all_pnls)
    print(  # noqa: PRINT
        f"  {label:<32}  fold-mean Sharpe={fold_mean:>+.4f}  "
        f"pooled Sharpe={pooled:>+.4f}  "
        f"n_total={n_total}  "
        f"fold-trade-mean={n_total / max(1, len(per_fold_pnls)):.1f}"
    )
    return fold_mean, pooled, n_total


def scenario_a_uniform_edge(rng: np.random.Generator) -> None:
    print("\n=== Scenario A: uniform edge across ranks, rank-3 fires sparsely ===")  # noqa: PRINT
    n_folds = 39
    # All ranks: per-trade pip PnL ~ N(mu=0.5, sigma=15).
    rank1_per_fold: list[list[float]] = []
    rank2_per_fold: list[list[float]] = []
    rank3_per_fold: list[list[float]] = []
    for _ in range(n_folds):
        n1 = 350  # rank-1 fires ~every active bar
        n2 = 250
        n3 = 8  # rank-3 fires sparsely
        rank1_per_fold.append(rng.normal(0.5, 15, n1).tolist())
        rank2_per_fold.append(rng.normal(0.5, 15, n2).tolist())
        rank3_per_fold.append(rng.normal(0.5, 15, n3).tolist())
    fold_mean_vs_pooled(rank1_per_fold, "Rank 1 (n=350/fold)")
    fold_mean_vs_pooled(rank2_per_fold, "Rank 2 (n=250/fold)")
    fold_mean_vs_pooled(rank3_per_fold, "Rank 3 (n=8/fold)")


def scenario_b_real_selection_edge(rng: np.random.Generator) -> None:
    print("\n=== Scenario B: rank-3 has TRULY higher edge (genuine selection effect) ===")  # noqa: PRINT
    n_folds = 39
    rank1_per_fold: list[list[float]] = []
    rank2_per_fold: list[list[float]] = []
    rank3_per_fold: list[list[float]] = []
    for _ in range(n_folds):
        rank1_per_fold.append(rng.normal(0.5, 15, 350).tolist())
        rank2_per_fold.append(rng.normal(0.5, 15, 250).tolist())
        # Rank-3: stronger mean (selection effect from regime alignment)
        rank3_per_fold.append(rng.normal(2.5, 15, 8).tolist())
    fold_mean_vs_pooled(rank1_per_fold, "Rank 1 (mu=0.5)")
    fold_mean_vs_pooled(rank2_per_fold, "Rank 2 (mu=0.5)")
    fold_mean_vs_pooled(rank3_per_fold, "Rank 3 (mu=2.5)")


def scenario_c_n_lt_2_fallback(rng: np.random.Generator) -> None:
    print("\n=== Scenario C: rank-3 with very small n; n<2 fallback to 0 ===")  # noqa: PRINT
    n_folds = 39
    rank3_per_fold: list[list[float]] = []
    for _ in range(n_folds):
        # Some folds have 0 or 1 trades (-> Sharpe 0)
        n3 = max(0, int(rng.poisson(2)))
        rank3_per_fold.append(rng.normal(0.5, 15, n3).tolist())
    n_zero = sum(1 for f in rank3_per_fold if len(f) < 2)
    print(f"  Folds with n<2 (returns 0.0): {n_zero}/{n_folds}")  # noqa: PRINT
    fold_mean_vs_pooled(rank3_per_fold, "Rank 3 (poisson(2))")


def scenario_d_observed_pattern(rng: np.random.Generator) -> None:
    """Try to match the observed rank3 = 0.561 pattern.

    What input distributions make fold-mean Sharpe approach 0.561?
    """
    print("\n=== Scenario D: hunting for the configuration that produces 0.561 ===")  # noqa: PRINT
    # If we have moderate edge and small N, the mean of fold Sharpes can drift
    # high because individual folds with luck-of-the-draw 0-variance hit the
    # population-variance Sharpe ceiling.
    n_folds = 39

    # Try: rank-3 with concentrated wins (lots of bars where TP hits)
    # If TB says "TP hit 60% of time", the realized PnL distribution is
    # bimodal: +tp_pip if win, -sl_pip if loss, ~0 if timeout. Concentrated.
    rank3_per_fold = []
    for _ in range(n_folds):
        n3 = rng.poisson(10)  # ~10 trades per fold
        if n3 == 0:
            rank3_per_fold.append([])
            continue
        # 70% TP+ (selection-aligned regime), 30% SL-, very few timeouts
        outcomes = rng.choice([+30.0, -30.0, 0.0], size=n3, p=[0.7, 0.25, 0.05])
        rank3_per_fold.append(outcomes.tolist())
    fold_mean_vs_pooled(
        rank3_per_fold,
        "Rank 3 (TP+ 70% / SL- 25% / TO 5%)",
    )

    # Compare with rank-1 with same distribution but more trades
    rank1_per_fold = []
    for _ in range(n_folds):
        n1 = 350
        outcomes = rng.choice([+30.0, -30.0, 0.0], size=n1, p=[0.7, 0.25, 0.05])
        rank1_per_fold.append(outcomes.tolist())
    fold_mean_vs_pooled(
        rank1_per_fold,
        "Rank 1 (TP+ 70%, n=350)",
    )


def main() -> None:
    rng = np.random.default_rng(42)
    print("=" * 70)  # noqa: PRINT
    print("Synthetic test: fold-mean vs pooled Sharpe (item 10)")  # noqa: PRINT
    print("=" * 70)  # noqa: PRINT

    scenario_a_uniform_edge(rng)
    scenario_b_real_selection_edge(rng)
    scenario_c_n_lt_2_fallback(rng)
    scenario_d_observed_pattern(rng)

    print("\n" + "=" * 70)  # noqa: PRINT
    print("Interpretation:")  # noqa: PRINT
    print("  - If A shows fold-mean ~ pooled across all ranks: aggregation is fair")  # noqa: PRINT
    print("  - If C shows fold-mean << pooled: n<2 fallback artificially deflates")  # noqa: PRINT
    print("  - If D shows fold-mean ~ 0.5+ for rank3 with truly biased outcomes:")  # noqa: PRINT
    print("    real selection edge can produce the observed 0.561")  # noqa: PRINT
    print("=" * 70)  # noqa: PRINT


if __name__ == "__main__":
    main()
