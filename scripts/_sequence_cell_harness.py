"""Sequence-cell evaluation harness for Phase 29.0b-β A0-broad eval.

Per PR #354 §10 + §11 (Phase 29.0b-α A0-broad design memo).

This harness provides per-row scoring + top-q quantile evaluation for:
  - Sequence cells (S1/S2/S3): per-row score via predict_sequence_score
  - Tabular control (C-d2-arch-control): per-row score via inherited
    LightGBM regressor; SAME quantile pipeline; **NOT a sequence model**.

The harness is the architectural change. Its role is to evaluate
both sequence models AND a tabular LightGBM control through the same
top-q + realised-PnL pipeline, so that:
  - C-d2-arch-control (tabular control in harness) ≈ 29.0a
    C-d1-target-control (6th anchor in tabular harness) within tolerance
  - C-d2-Sx (sequence model in harness) is comparable to C-d2-arch-control
    in the same harness — separates harness drift from sequence-model
    effect (PR #354 §10.2 load-bearing).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage26_0c = importlib.import_module("stage26_0c_l1_eval")
stage27_0e = importlib.import_module("stage27_0e_s_e_quantile_trim_eval")
stage27_0d = importlib.import_module("stage27_0d_s_e_regression_eval")

compute_8_gate_from_pnls = stage26_0c.compute_8_gate_from_pnls
fit_quantile_cutoff_on_val = stage26_0c.fit_quantile_cutoff_on_val
evaluate_quantile_family_custom = stage27_0e.evaluate_quantile_family_custom
compute_picker_score_s_e = stage27_0d.compute_picker_score_s_e


# ---------------------------------------------------------------------------
# Per-row scoring dispatcher
# ---------------------------------------------------------------------------


def score_rows_via_sequence_model(
    sequence_model, windowed_x: np.ndarray, batch_size: int, device, valid_mask: np.ndarray
) -> np.ndarray:
    """Compute per-row scalar scores via sequence model.

    Per PR #354 §8.3: per-row scoring (NOT per-step); identical to
    tabular pipeline downstream.

    Rows with valid_mask=False receive score=NaN.
    """
    from _sequence_training import predict_sequence_score

    scores = np.full(len(windowed_x), np.nan, dtype=np.float64)
    if int(valid_mask.sum()) == 0:
        return scores
    valid_idx = np.flatnonzero(valid_mask)
    x_valid = windowed_x[valid_idx]
    scores_valid = predict_sequence_score(sequence_model, x_valid, batch_size, device)
    scores[valid_idx] = scores_valid
    return scores


def score_rows_via_tabular(
    tabular_regressor, df_r7a: pd.DataFrame, valid_mask: np.ndarray
) -> np.ndarray:
    """Compute per-row scalar scores via tabular LightGBM regressor.

    Per PR #354 §10.1: C-d2-arch-control is a tabular LightGBM model
    evaluated INSIDE the sequence-cell evaluation harness; NOT a
    sequence model.

    Rows with valid_mask=False receive score=NaN to ensure the same
    row-set as the sequence cells (separates harness drift from sequence
    model effect).
    """
    scores = np.full(len(df_r7a), np.nan, dtype=np.float64)
    if int(valid_mask.sum()) == 0:
        return scores
    valid_idx = np.flatnonzero(valid_mask)
    x_valid = df_r7a.iloc[valid_idx]
    scores_valid = compute_picker_score_s_e(tabular_regressor, x_valid)
    scores[valid_idx] = scores_valid.astype(np.float64)
    return scores


def score_rows_via_tabular_full(
    tabular_regressor, df_r7a: pd.DataFrame
) -> np.ndarray:
    """Compute per-row scalar scores via tabular LightGBM regressor — full row-set.

    Used for C-sb-baseline FAIL-FAST (which uses the full R7-A row-set,
    not the windowed-valid subset; per PR #354 §11.1 inherited from
    Phase 28 §10).
    """
    return compute_picker_score_s_e(tabular_regressor, df_r7a).astype(np.float64)


# ---------------------------------------------------------------------------
# Per-cell quantile evaluation
# ---------------------------------------------------------------------------


def evaluate_cell_quantile_family(
    val_score: np.ndarray,
    val_pnl: np.ndarray,
    test_score: np.ndarray,
    test_pnl: np.ndarray,
    val_span_years: float,
    test_span_years: float,
    quantile_percents: tuple[float, ...] = (5.0, 10.0, 20.0, 30.0, 40.0),
) -> list[dict]:
    """Per-cell quantile family evaluation.

    Returns list of per-q records each with val/test metrics. Inherits
    the harness inhabited by stage27_0e.evaluate_quantile_family_custom.
    """
    return evaluate_quantile_family_custom(
        val_score,
        val_pnl,
        test_score,
        test_pnl,
        val_span_years,
        test_span_years,
        quantile_percents=quantile_percents,
    )


def evaluate_cell_q5_only(
    val_score: np.ndarray,
    val_pnl: np.ndarray,
    test_score: np.ndarray,
    test_pnl: np.ndarray,
    val_span_years: float,
    test_span_years: float,
) -> dict:
    """Single q=5 evaluation for C-sb-baseline FAIL-FAST cell."""
    return evaluate_quantile_family_custom(
        val_score,
        val_pnl,
        test_score,
        test_pnl,
        val_span_years,
        test_span_years,
        quantile_percents=(5.0,),
    )[0]


# ---------------------------------------------------------------------------
# Per-cell verdict extraction
# ---------------------------------------------------------------------------


def select_best_quantile_by_val_sharpe(quantile_results: list[dict]) -> dict:
    """Pick best (q, cutoff) by val Sharpe.

    Tie-breaker: annual_pnl → n_trades → smaller q. Same as inherited
    stage27_0e / stage28_0c pattern.
    """
    def _key(r: dict) -> tuple:
        v = r["val"]
        s = v["sharpe"] if np.isfinite(v["sharpe"]) else -np.inf
        return (s, v["annual_pnl"], v["n_trades"], -r["q_percent"])

    return max(quantile_results, key=_key)


# ---------------------------------------------------------------------------
# Determinism check helper
# ---------------------------------------------------------------------------


def compare_metric_level_determinism(
    record_a: dict, record_b: dict, sharpe_tol: float = 1e-4
) -> dict:
    """Compare two evaluation records at metric level (NOT bit-identical).

    Per user instruction + PR #354 §16.2 item 11:
      - val Sharpe ±1e-4
      - n_trades exact (±0)
      - selected q identical
    """
    sharpe_a = float(record_a.get("val_realised_sharpe", float("nan")))
    sharpe_b = float(record_b.get("val_realised_sharpe", float("nan")))
    sharpe_delta = sharpe_a - sharpe_b if np.isfinite(sharpe_a) and np.isfinite(sharpe_b) else float("nan")
    sharpe_within = np.isfinite(sharpe_delta) and abs(sharpe_delta) <= sharpe_tol

    n_a = int(record_a.get("val_n_trades", 0))
    n_b = int(record_b.get("val_n_trades", 0))
    n_match = n_a == n_b

    q_a = record_a.get("selected_q_percent", None)
    q_b = record_b.get("selected_q_percent", None)
    q_match = q_a == q_b

    return {
        "sharpe_a": sharpe_a,
        "sharpe_b": sharpe_b,
        "sharpe_delta": float(sharpe_delta) if np.isfinite(sharpe_delta) else float("nan"),
        "sharpe_within_tolerance": bool(sharpe_within),
        "n_trades_a": n_a,
        "n_trades_b": n_b,
        "n_trades_match": bool(n_match),
        "selected_q_a": q_a,
        "selected_q_b": q_b,
        "selected_q_match": bool(q_match),
        "all_within_tolerance": bool(sharpe_within and n_match and q_match),
    }
