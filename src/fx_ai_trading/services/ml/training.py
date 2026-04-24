"""training — walk-forward CV training for LightGBM baseline (Phase 9.6).

Training protocol (roadmap §6.6):
  - Expanding window: train on [start .. T], validate on [T .. T+val_months].
  - Advance by val_months each fold.
  - MVP hyperparameters are fixed (no grid search) for reproducibility.
  - Label column: label_triple_barrier (+1 / -1 / 0).
  - Features: the 15 TA keys from FeatureService (FEATURE_COLUMNS).
  - Rows with null labels are dropped before training.

Returns list of (model, fold_metrics) for each fold.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import lightgbm as lgb
import pyarrow.parquet as pq

# Canonical feature column order (must match FeatureService._ZERO_FEATURES keys).
FEATURE_COLUMNS: list[str] = [
    "atr_14",
    "bb_lower",
    "bb_middle",
    "bb_pct_b",
    "bb_upper",
    "bb_width",
    "ema_12",
    "ema_26",
    "last_close",
    "macd_histogram",
    "macd_line",
    "macd_signal",
    "rsi_14",
    "sma_20",
    "sma_50",
]

LABEL_COLUMN = "label_triple_barrier"

# Label encoding: LightGBM multiclass requires 0-based integers.
# triple_barrier returns -1/0/+1 → encode to 0/1/2.
_LABEL_ENCODE = {-1: 0, 0: 1, 1: 2}
_LABEL_DECODE = {v: k for k, v in _LABEL_ENCODE.items()}

# Fixed MVP hyperparameters (reproducibility over tuning).
DEFAULT_PARAMS: dict[str, Any] = {
    "objective": "multiclass",
    "num_class": 3,
    "n_estimators": 100,
    "max_depth": 4,
    "learning_rate": 0.05,
    "num_leaves": 15,
    "min_child_samples": 20,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "verbose": -1,
    "random_state": 42,
}


@dataclass
class FoldResult:
    """Metrics and model for a single walk-forward fold."""

    fold_idx: int
    train_cutoff: datetime
    val_cutoff: datetime
    n_train: int
    n_val: int
    metrics: dict[str, float]
    model: lgb.LGBMClassifier


def _compute_metrics(y_true: list[int], y_pred: list[int]) -> dict[str, float]:
    n = len(y_true)
    if n == 0:
        return {}
    correct = sum(a == b for a, b in zip(y_true, y_pred, strict=True))
    hit_rate = correct / n

    # Per-class precision/recall (macro average).
    classes = (-1, 0, 1)
    precisions, recalls = [], []
    for cls in classes:
        tp = sum(1 for a, b in zip(y_true, y_pred, strict=True) if a == cls and b == cls)
        fp = sum(1 for a, b in zip(y_true, y_pred, strict=True) if a != cls and b == cls)
        fn = sum(1 for a, b in zip(y_true, y_pred, strict=True) if a == cls and b != cls)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        precisions.append(prec)
        recalls.append(rec)

    return {
        "hit_rate": round(hit_rate, 4),
        "macro_precision": round(sum(precisions) / len(precisions), 4),
        "macro_recall": round(sum(recalls) / len(recalls), 4),
    }


def train_walk_forward(
    parquet_path: str,
    train_months: int = 6,
    val_months: int = 1,
    feature_columns: list[str] | None = None,
    label_column: str = LABEL_COLUMN,
    params: dict[str, Any] | None = None,
) -> list[FoldResult]:
    """Run walk-forward cross-validation and return per-fold results.

    Args:
        parquet_path: Path to feature store parquet (from build_feature_store).
        train_months: Training window size in months (expanding from start).
        val_months: Validation window size in months.
        feature_columns: Feature column names (defaults to FEATURE_COLUMNS).
        label_column: Target column name.
        params: LightGBM hyperparameters (defaults to DEFAULT_PARAMS).

    Returns:
        List of FoldResult, one per fold.
    """
    feat_cols = feature_columns or FEATURE_COLUMNS
    lgb_params = {**DEFAULT_PARAMS, **(params or {})}

    table = pq.read_table(parquet_path, columns=["ts"] + feat_cols + [label_column])

    # Drop rows with null labels.
    mask = table.column(label_column).is_valid()
    table = table.filter(mask)

    ts_col = table.column("ts").to_pylist()
    y_raw = table.column(label_column).to_pylist()
    x_rows = [[table.column(c)[i].as_py() for c in feat_cols] for i in range(len(ts_col))]

    if not ts_col:
        return []

    min_ts = min(ts_col)
    max_ts = max(ts_col)

    results: list[FoldResult] = []
    fold_idx = 0

    # Walk-forward: first val window starts at min_ts + train_months.
    val_start = min_ts + timedelta(days=30 * train_months)

    while val_start + timedelta(days=30 * val_months) <= max_ts + timedelta(days=1):
        val_end = val_start + timedelta(days=30 * val_months)

        train_mask = [ts < val_start for ts in ts_col]
        val_mask = [val_start <= ts < val_end for ts in ts_col]

        x_train = [x for x, m in zip(x_rows, train_mask, strict=True) if m]
        y_train_raw = [y for y, m in zip(y_raw, train_mask, strict=True) if m]
        x_val = [x for x, m in zip(x_rows, val_mask, strict=True) if m]
        y_val_raw = [y for y, m in zip(y_raw, val_mask, strict=True) if m]

        if len(x_train) < 10 or len(x_val) < 5:
            val_start = val_end
            fold_idx += 1
            continue

        y_train = [_LABEL_ENCODE[v] for v in y_train_raw]

        model = lgb.LGBMClassifier(**lgb_params)
        model.fit(x_train, y_train)

        y_pred_encoded = model.predict(x_val)
        y_pred = [_LABEL_DECODE[int(p)] for p in y_pred_encoded]
        metrics = _compute_metrics(y_val_raw, y_pred)

        results.append(
            FoldResult(
                fold_idx=fold_idx,
                train_cutoff=val_start,
                val_cutoff=val_end,
                n_train=len(x_train),
                n_val=len(x_val),
                metrics=metrics,
                model=model,
            )
        )

        val_start = val_end
        fold_idx += 1

    return results


__all__ = [
    "DEFAULT_PARAMS",
    "FEATURE_COLUMNS",
    "LABEL_COLUMN",
    "FoldResult",
    "train_walk_forward",
]
