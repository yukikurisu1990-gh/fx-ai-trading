"""Stage 1C — is tick volume a proxy for what we already have, or new information?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

No strategy is built here. The question is narrower and comes first: **once
realised volatility, the spread, the bar's own move and the session are
accounted for, is there anything left in tick volume?** If there is not, it is a
re-expression of variables the programme already has and it does not become a
feature.

Plan §14's gate, unchanged: redundant if the median per-pair `R²` of
`log(1 + volume)` on those four reaches 0.80 **and** the residual carries no
forward relation at `|z| ≥ 2` on both deciding panels.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from scripts.research.exploratory_m15 import volume as volume_reader
from scripts.research.monetizability import (
    NULL_DRAWS,
    SEED,
    VOLUME_FORWARD_TARGETS,
)
from scripts.research.round_b_prime import retrace


def attach(frame: pd.DataFrame, volume_frame: pd.DataFrame) -> pd.DataFrame:
    """Join the recovered volume onto a price panel on the M15 grid."""
    merged = frame.merge(volume_frame, on="ts", how="left", validate="one_to_one")
    return merged


def coverage(panel: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """What the recovered field actually contains, before anything is inferred."""
    rows: dict[str, Any] = {}
    for pair, frame in panel.items():
        volume = frame["volume"]
        rows[pair] = {
            "bars": int(len(frame)),
            "present": round(float(volume.notna().mean()), 5),
            "zero": round(float((volume.fillna(-1) == 0).mean()), 5),
            "median": round(float(volume.median()), 1) if volume.notna().any() else None,
            "p01": round(float(volume.quantile(0.01)), 1) if volume.notna().any() else None,
            "p99": round(float(volume.quantile(0.99)), 1) if volume.notna().any() else None,
            "m1_rows_missing_field": int(frame["volume_missing"].fillna(0).sum()),
        }
    present = [r["present"] for r in rows.values()]
    return {
        "per_pair": rows,
        "min_present": round(float(np.min(present)), 5),
        "median_present": round(float(np.median(present)), 5),
        "pairs": len(rows),
    }


def _design(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """`log(1 + volume)` and the four things it might merely re-express."""
    volume = frame["volume"].to_numpy(dtype=float)
    sigma = np.asarray(retrace.trailing_sigma(frame), dtype=float)
    pip = float(frame["pip_size"].iloc[0])
    spread = frame["spread_close_pips"].to_numpy(dtype=float)
    move = np.abs(frame["mid_c"].diff().to_numpy(dtype=float)) / pip
    hour = frame["ts"].dt.hour.to_numpy(dtype=float)

    target = np.log1p(volume)
    columns = [
        np.log(np.maximum(sigma / pip, 1e-6)),
        np.log(np.maximum(spread, 1e-6)),
        np.log1p(np.maximum(move, 0.0)),
        np.sin(2 * np.pi * hour / 24.0),
        np.cos(2 * np.pi * hour / 24.0),
        np.sin(4 * np.pi * hour / 24.0),
        np.cos(4 * np.pi * hour / 24.0),
    ]
    design = np.column_stack(columns)
    keep = np.isfinite(target) & np.isfinite(design).all(axis=1)
    if keep.sum() < 5_000:
        return None
    return target[keep], design[keep], np.flatnonzero(keep)


def redundancy(panel: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Per pair, how much of `log(1 + volume)` the existing variables explain."""
    rows: dict[str, Any] = {}
    for pair, frame in panel.items():
        built = _design(frame)
        if built is None:
            continue
        target, design, _ = built
        standard = np.column_stack([np.ones(len(design)), design])
        beta, *_ = np.linalg.lstsq(standard, target, rcond=None)
        fitted = standard @ beta
        residual = target - fitted
        total = float(((target - target.mean()) ** 2).sum())
        rows[pair] = {
            "n": int(len(target)),
            "r2": round(1.0 - float((residual**2).sum()) / total, 5) if total > 0 else None,
            "spearman_with_sigma": round(
                float(scipy_stats.spearmanr(target, design[:, 0]).statistic), 4
            ),
            "spearman_with_spread": round(
                float(scipy_stats.spearmanr(target, design[:, 1]).statistic), 4
            ),
            "spearman_with_abs_move": round(
                float(scipy_stats.spearmanr(target, design[:, 2]).statistic), 4
            ),
        }
    values = [r["r2"] for r in rows.values() if r["r2"] is not None]
    return {
        "per_pair": rows,
        "median_r2": round(float(np.median(values)), 5) if values else None,
        "min_r2": round(float(np.min(values)), 5) if values else None,
        "max_r2": round(float(np.max(values)), 5) if values else None,
        "pairs": len(rows),
    }


def _forward_targets(frame: pd.DataFrame, index: np.ndarray) -> dict[str, np.ndarray]:
    pip = float(frame["pip_size"].iloc[0])
    forward = (frame["mid_c"].shift(-1) - frame["mid_c"]).to_numpy(dtype=float) / pip
    return {
        "abs_next_return": np.abs(forward)[index],
        "signed_next_return": forward[index],
    }


def _residuals(panel: dict[str, pd.DataFrame]) -> dict[str, tuple[np.ndarray, dict]]:
    """Per pair, the part of `log(1 + volume)` the existing variables do not explain."""
    out: dict[str, tuple[np.ndarray, dict]] = {}
    for pair, frame in panel.items():
        built = _design(frame)
        if built is None:
            continue
        volume_log, design, index = built
        standard = np.column_stack([np.ones(len(design)), design])
        beta, *_ = np.linalg.lstsq(standard, volume_log, rcond=None)
        out[pair] = (volume_log - standard @ beta, _forward_targets(frame, index))
    return out


def incremental(
    panel: dict[str, pd.DataFrame], *, draws: int = NULL_DRAWS, seed: int = SEED
) -> dict[str, Any]:
    """Does what volume knows *beyond* those variables relate to the next bar?

    The residual is fitted once per pair and then permuted, because a shuffle
    destroys the pairing while keeping both marginals exactly — which is the
    right reference for a rank statistic, and cheap enough to run at the full
    draw count.
    """
    residuals = _residuals(panel)
    out: dict[str, Any] = {}
    rng = np.random.default_rng(seed)
    for target_name in VOLUME_FORWARD_TARGETS:
        usable: list[tuple[np.ndarray, np.ndarray]] = []
        observed: list[float] = []
        for residual, targets in residuals.values():
            forward = targets[target_name]
            keep = np.isfinite(forward) & np.isfinite(residual)
            if keep.sum() < 5_000:
                continue
            left, right = residual[keep], forward[keep]
            usable.append((left, right))
            observed.append(float(scipy_stats.spearmanr(left, right).statistic))
        if not observed:
            continue
        real = float(np.mean(observed))
        #: rank once, then permute the ranks: Spearman on permuted ranks is a
        #: Pearson correlation, so the null costs one dot product per draw
        ranked = [
            (scipy_stats.rankdata(left), scipy_stats.rankdata(right)) for left, right in usable
        ]
        samples: list[float] = []
        for _ in range(draws):
            drawn = []
            for left_rank, right_rank in ranked:
                shuffled = rng.permutation(left_rank)
                drawn.append(float(np.corrcoef(shuffled, right_rank)[0, 1]))
            samples.append(float(np.mean(drawn)))
        mean, sd = float(np.mean(samples)), float(np.std(samples))
        out[target_name] = {
            "real": round(real, 6),
            "per_pair": [round(v, 5) for v in observed],
            "pairs_same_sign": int(sum(1 for v in observed if (v > 0) == (real > 0))),
            "pairs": len(observed),
            "null_mean": round(mean, 6),
            "null_sd": round(sd, 6),
            "studentized": round((real - mean) / sd, 3) if sd > 0 else None,
            "draws": len(samples),
        }
    return out


def persistence(panel: dict[str, pd.DataFrame], *, lags: int = 8) -> dict[str, Any]:
    """How long a volume shock lasts, on the pair-local z-score."""
    rows: dict[str, list[float]] = {str(lag): [] for lag in range(1, lags + 1)}
    for frame in panel.values():
        volume = np.log1p(frame["volume"].to_numpy(dtype=float))
        clean = volume[np.isfinite(volume)]
        if len(clean) < 5_000:
            continue
        centred = clean - clean.mean()
        for lag in range(1, lags + 1):
            rows[str(lag)].append(
                float(np.corrcoef(centred[:-lag], centred[lag:])[0, 1])
                if lag < len(centred)
                else np.nan
            )
    return {lag: round(float(np.nanmean(v)), 4) for lag, v in rows.items() if v}


__all__ = ["attach", "coverage", "incremental", "persistence", "redundancy", "volume_reader"]
