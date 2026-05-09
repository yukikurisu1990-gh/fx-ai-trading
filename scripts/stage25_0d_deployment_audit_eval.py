"""Stage 25.0d-β — Deployment-layer audit eval.

Implements the binding contract from PR #289 (25.0d-α
docs/design/phase25_0d_deployment_audit_design.md). Re-fits F1 + F2
best cells deterministically (random_state=42), computes calibration
analysis (decile + quintile), per-bucket realised barrier PnL,
extended threshold sweep, directional vs bidirectional comparison,
and closed-form AUC-EV theoretical bound. Tests H-A / H-B / H-D /
H-F from PR #288 §5.

MANDATORY CLAUSES (verbatim per 25.0d-α §12):

1. Phase 25 framing.
   Phase 25 is not a hyperparameter-tuning phase. It is a label-and-
   feature-class redesign phase.

2. Diagnostic-leakage prohibition.
   The 25.0a-β diagnostic columns MUST NOT appear in any model's
   feature matrix.

3. Causality and split discipline.
   All features use shift(1).rolling pattern. Train/val/test splits
   are strictly chronological (70/15/15). Threshold selection uses
   VALIDATION ONLY; test set is touched once.

4. γ closure preservation.
   Phase 25.0d does not modify the γ closure (PR #279).

5. Production-readiness preservation.
   Findings in 25.0d are hypothesis-generating only.

6. Deployment-layer scope clause.
   This PR investigates the structural AUC-PnL gap surfaced in
   PR #288 §4.2 by analysing F1+F2 best cells under varied
   deployment-layer settings. Tests H-A/H-B/H-D/H-F from #288 §5.
   Does NOT redesign features, labels, or model class. Verdict
   applies only to F1+F2 best cells; convergence with F3-F6 is a
   separate question. F1 and F2 verdicts (#284, #287) are NOT
   modified by this audit.

7. Production misunderstanding guard.
   This is a research deployment-layer audit, not a production
   deployment study.

8. Threshold sweep guard.
   The extended threshold sweep is diagnostic-only. It must not be
   interpreted as selecting a production threshold from the test
   set.

9. Directional comparison guard.
   Directional comparison is diagnostic-only. If directional
   candidate generation appears promising, it requires a separate
   predeclared design PR and frozen-OOS validation.
"""

from __future__ import annotations

import argparse
import importlib
import sys
import time
import warnings
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import brier_score_loss, roc_auc_score

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage25_0d"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Reuse heavily from stage25_0b and stage25_0c.
stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage25_0b = importlib.import_module("stage25_0b_f1_volatility_expansion_eval")
stage25_0c = importlib.import_module("stage25_0c_f2_volatility_regime_eval")

PAIRS_20 = stage23_0a.PAIRS_20
load_m1_ba = stage23_0a.load_m1_ba
pip_size_for = stage23_0a.pip_size_for

# Shared helpers (reused — NOT copy-paste)
load_path_quality_labels = stage25_0b.load_path_quality_labels
split_70_15_15 = stage25_0b.split_70_15_15
_compute_realised_barrier_pnl = stage25_0b._compute_realised_barrier_pnl
compute_8_gate_metrics = stage25_0b.compute_8_gate_metrics
gate_matrix = stage25_0b.gate_matrix
_select_threshold_on_val = stage25_0b._select_threshold_on_val
_proxy_pnl_per_row = stage25_0b._proxy_pnl_per_row

# F1 specifics
compute_f1_features_for_pair = stage25_0b.compute_f1_features_for_pair
build_logistic_pipeline_f1 = stage25_0b.build_logistic_pipeline
_admissible_mask_f1 = stage25_0b._admissible_mask_for_cell
F1_FEATURE_COLS_BASE = stage25_0b.FEATURE_COLS_BASE
F1_CATEGORICAL_COLS = stage25_0b.CATEGORICAL_COLS

# F2 specifics
compute_f2_features_for_pair = stage25_0c.compute_f2_features_for_pair
build_logistic_pipeline_f2 = stage25_0c.build_logistic_pipeline_f2
_apply_admissibility_filter_f2 = stage25_0c._apply_admissibility_filter
F2_PER_TF_COLS = stage25_0c.F2_PER_TF_COLS

PROHIBITED_DIAGNOSTIC_COLUMNS = stage25_0b.PROHIBITED_DIAGNOSTIC_COLUMNS

# ---------------------------------------------------------------------------
# Design constants (LOCKED from 25.0d-α)
# ---------------------------------------------------------------------------

K_FAV = stage25_0b.K_FAV  # 1.5
K_ADV = stage25_0b.K_ADV  # 1.0
H_M1_BARS = stage25_0b.H_M1_BARS  # 60
SPAN_DAYS = stage25_0b.SPAN_DAYS  # 730

# Cell specs (rank-1 from #284 / #287)
F1_RANK1_CELL = {"tf": "M5", "lookback": 50, "quantile": 0.20, "expansion": 1.25}
F2_RANK1_CELL = {"trailing_window": 200, "representation": "per_tf_only", "admissibility": "none"}

# Bucket / threshold parameters
N_DECILES = 10
N_QUINTILES = 5
LOW_BUCKET_N = 100
EXTENDED_THRESHOLDS = (0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80)

# Calibration verdict thresholds
CAL_DEVIATION_OK = 0.05
CAL_DEVIATION_MISCAL = 0.10

# Directional verdict thresholds
DIRECTIONAL_SHARPE_LIFT = 0.10
DIRECTIONAL_PNL_LIFT_PCT = 0.50
DIRECTIONAL_LOW_DATA_PER_DIR_TRAIN = 1000

# Theoretical AUC-EV quantiles
THEORETICAL_QUANTILES = (0.5, 0.6, 0.7, 0.8, 0.9)

# Base positive rate from 25.0a
BASE_POSITIVE_RATE = 0.187


# ---------------------------------------------------------------------------
# Decile / quintile bucketing
# ---------------------------------------------------------------------------


def decile_buckets(predicted_p: np.ndarray, n_buckets: int = N_DECILES) -> np.ndarray:
    """Equal-width buckets in [0, 1]. Returns int array of bucket indices [0, n_buckets)."""
    edges = np.linspace(0.0, 1.0, n_buckets + 1)
    edges[-1] += 1e-9  # ensure 1.0 falls in last bucket
    return np.clip(np.digitize(predicted_p, edges[1:-1], right=False), 0, n_buckets - 1)


def reliability_table(
    predicted_p: np.ndarray, labels: np.ndarray, n_buckets: int = N_DECILES
) -> pd.DataFrame:
    """Per-bucket reliability + Brier."""
    buckets = decile_buckets(predicted_p, n_buckets)
    rows: list[dict] = []
    for i in range(n_buckets):
        mask = buckets == i
        n = int(mask.sum())
        if n == 0:
            rows.append(
                {
                    "bucket": i,
                    "bucket_lo": i / n_buckets,
                    "bucket_hi": (i + 1) / n_buckets,
                    "n": 0,
                    "mean_predicted": float("nan"),
                    "actual_positive_rate": float("nan"),
                    "brier": float("nan"),
                    "low_bucket_n": True,
                }
            )
            continue
        p_bucket = predicted_p[mask]
        y_bucket = labels[mask]
        rows.append(
            {
                "bucket": i,
                "bucket_lo": i / n_buckets,
                "bucket_hi": (i + 1) / n_buckets,
                "n": n,
                "mean_predicted": float(p_bucket.mean()),
                "actual_positive_rate": float(y_bucket.mean()),
                "brier": float(brier_score_loss(y_bucket, p_bucket))
                if len(np.unique(y_bucket)) > 1 or n >= 2
                else float("nan"),
                "low_bucket_n": n < LOW_BUCKET_N,
            }
        )
    return pd.DataFrame(rows)


def calibration_verdict(rel_table: pd.DataFrame) -> tuple[str, float, str]:
    """Returns (verdict, max_systematic_deviation, note)."""
    valid = rel_table.dropna(subset=["mean_predicted", "actual_positive_rate"])
    if len(valid) < 3:
        return "INSUFFICIENT_BUCKETS", float("nan"), "fewer than 3 valid buckets"
    deviations = valid["actual_positive_rate"] - valid["mean_predicted"]
    max_abs = float(deviations.abs().max())
    # Systematic = same-sign across most buckets
    pos_count = (deviations > 0).sum()
    neg_count = (deviations < 0).sum()
    systematic = (pos_count >= len(valid) - 1) or (neg_count >= len(valid) - 1)
    if systematic and max_abs > CAL_DEVIATION_MISCAL:
        return "MISCALIBRATED", max_abs, "systematic over/under-estimation > 0.10"
    if max_abs <= CAL_DEVIATION_OK:
        return "CALIBRATION_OK", max_abs, "deviation within ±0.05"
    return "BOUNDARY", max_abs, "deviation in [0.05, 0.10] zone — user judgement"


def quintile_monotonicity(predicted_p: np.ndarray, labels: np.ndarray) -> bool:
    """True if quintile-bucketed actual positive rate is monotonically non-decreasing."""
    buckets = decile_buckets(predicted_p, N_QUINTILES)
    rates: list[float] = []
    for i in range(N_QUINTILES):
        mask = buckets == i
        if mask.sum() == 0:
            rates.append(float("nan"))
            continue
        rates.append(float(labels[mask].mean()))
    valid_rates = [r for r in rates if np.isfinite(r)]
    if len(valid_rates) < 2:
        return False
    return all(valid_rates[i] <= valid_rates[i + 1] for i in range(len(valid_rates) - 1))


# ---------------------------------------------------------------------------
# Per-bucket realised PnL
# ---------------------------------------------------------------------------


def per_bucket_realised_pnl(
    predicted_p: np.ndarray,
    test_df: pd.DataFrame,
    pair_runtime: dict,
    n_buckets: int = N_DECILES,
) -> pd.DataFrame:
    """Per-bucket: mean realised PnL, mean spread, net_EV."""
    buckets = decile_buckets(predicted_p, n_buckets)
    rows: list[dict] = []
    test_df = test_df.reset_index(drop=True)
    for i in range(n_buckets):
        mask = buckets == i
        idx = np.where(mask)[0]
        if len(idx) == 0:
            rows.append(
                {
                    "bucket": i,
                    "n": 0,
                    "mean_realised_pnl": float("nan"),
                    "mean_spread_pip": float("nan"),
                    "net_ev_pip": float("nan"),
                    "low_bucket_n": True,
                }
            )
            continue
        realised: list[float] = []
        spreads: list[float] = []
        for j in idx:
            row = test_df.iloc[j]
            pair = row["pair"]
            if pair not in pair_runtime:
                continue
            atr_pip = float(row["atr_at_signal_pip"])
            spread_pip = float(row["spread_at_signal_pip"])
            r = _compute_realised_barrier_pnl(
                pair, row["signal_ts"], row["direction"], atr_pip, pair_runtime[pair]
            )
            if r is not None:
                realised.append(r)
                spreads.append(spread_pip)
        if not realised:
            rows.append(
                {
                    "bucket": i,
                    "n": 0,
                    "mean_realised_pnl": float("nan"),
                    "mean_spread_pip": float("nan"),
                    "net_ev_pip": float("nan"),
                    "low_bucket_n": True,
                }
            )
            continue
        mean_realised = float(np.mean(realised))
        mean_spread = float(np.mean(spreads))
        rows.append(
            {
                "bucket": i,
                "n": len(realised),
                "mean_realised_pnl": mean_realised,
                "mean_spread_pip": mean_spread,
                "net_ev_pip": mean_realised - mean_spread,
                "low_bucket_n": len(realised) < LOW_BUCKET_N,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Extended threshold sweep (bidirectional argmax)
# ---------------------------------------------------------------------------


def threshold_sweep_bidirectional(
    test_df: pd.DataFrame,
    predicted_p: np.ndarray,
    pair_runtime: dict,
    thresholds: tuple[float, ...] = EXTENDED_THRESHOLDS,
) -> pd.DataFrame:
    """For each threshold, filter test rows by max(P_long, P_short) >= threshold;
    compute realised PnL via M1 path re-traverse; report Sharpe / ann_pnl /
    n_trades or EMPTY status."""
    test = test_df.reset_index(drop=True).copy()
    test["_p"] = predicted_p
    long_view = test[test["direction"] == "long"].set_index(["pair", "signal_ts"])
    short_view = test[test["direction"] == "short"].set_index(["pair", "signal_ts"])
    common_idx = long_view.index.intersection(short_view.index)
    if len(common_idx) == 0:
        return pd.DataFrame(
            [
                {
                    "threshold": t,
                    "status": "EMPTY",
                    "n_trades": 0,
                    "sharpe": float("nan"),
                    "annual_pnl": float("nan"),
                }
                for t in thresholds
            ]
        )
    p_long = long_view.loc[common_idx, "_p"]
    p_short = short_view.loc[common_idx, "_p"]
    atr_pip = long_view.loc[common_idx, "atr_at_signal_pip"]
    label_long = long_view.loc[common_idx, "label"]
    label_short = short_view.loc[common_idx, "label"]

    rows: list[dict] = []
    for thr in thresholds:
        long_traded = (p_long >= thr) & (p_long >= p_short)
        short_traded = (p_short >= thr) & (p_short > p_long)
        realised: list[float] = []
        for (pair, signal_ts), traded in long_traded.items():
            if not traded or pair not in pair_runtime:
                continue
            atr = float(atr_pip.loc[(pair, signal_ts)])
            r = _compute_realised_barrier_pnl(pair, signal_ts, "long", atr, pair_runtime[pair])
            if r is not None:
                realised.append(r)
        for (pair, signal_ts), traded in short_traded.items():
            if not traded or pair not in pair_runtime:
                continue
            atr = float(atr_pip.loc[(pair, signal_ts)])
            r = _compute_realised_barrier_pnl(pair, signal_ts, "short", atr, pair_runtime[pair])
            if r is not None:
                realised.append(r)
        n = len(realised)
        if n == 0:
            rows.append(
                {
                    "threshold": thr,
                    "status": "EMPTY",
                    "n_trades": 0,
                    "sharpe": float("nan"),
                    "annual_pnl": float("nan"),
                }
            )
            continue
        metrics = compute_8_gate_metrics(np.asarray(realised), n)
        rows.append(
            {
                "threshold": thr,
                "status": "OK",
                "n_trades": metrics["n_trades"],
                "sharpe": metrics["sharpe"],
                "annual_pnl": metrics["annual_pnl"],
            }
        )
    # Suppress unused-warning for label series; they could be reported later.
    _ = (label_long, label_short)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Directional comparison
# ---------------------------------------------------------------------------


def fit_directional_models(
    train_df: pd.DataFrame, val_df: pd.DataFrame, feature_cols: list[str], pipeline_builder
) -> dict:
    """Fit two pipelines (long-only / short-only) and select per-direction
    threshold on val. Returns dict with models + thresholds + flags."""
    out: dict = {"low_data_flag": False}
    for direction in ("long", "short"):
        train_d = train_df[train_df["direction"] == direction].copy()
        val_d = val_df[val_df["direction"] == direction].copy()
        n_train = len(train_d)
        if n_train < DIRECTIONAL_LOW_DATA_PER_DIR_TRAIN:
            out["low_data_flag"] = True
        if n_train < 50 or len(val_d) < 20:
            out[f"{direction}_model"] = None
            out[f"{direction}_threshold"] = float("nan")
            out[f"{direction}_n_train"] = n_train
            out[f"{direction}_n_val"] = len(val_d)
            continue
        if pipeline_builder is build_logistic_pipeline_f2:
            pipeline = pipeline_builder(feature_cols)
        else:
            pipeline = pipeline_builder()
        x_train = train_d[feature_cols + F1_CATEGORICAL_COLS]
        y_train = train_d["label"].astype(int)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pipeline.fit(x_train, y_train)
        x_val = val_d[feature_cols + F1_CATEGORICAL_COLS]
        val_p = pipeline.predict_proba(x_val)[:, 1]
        # Per-direction threshold: pick threshold maximising val proxy Sharpe
        atr_v = val_d["atr_at_signal_pip"].to_numpy()
        labels_v = val_d["label"].astype(int).to_numpy()
        best_thr = EXTENDED_THRESHOLDS[0]
        best_sharpe = -np.inf
        for thr in EXTENDED_THRESHOLDS:
            traded = val_p >= thr
            if traded.sum() < 2:
                continue
            pnls = np.array(
                [
                    _proxy_pnl_per_row(int(lbl), float(a), True)
                    for lbl, a in zip(labels_v[traded], atr_v[traded], strict=False)
                ]
            )
            std = pnls.std(ddof=0)
            sharpe = pnls.mean() / std if std > 0 else -np.inf
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_thr = thr
        out[f"{direction}_model"] = pipeline
        out[f"{direction}_threshold"] = best_thr
        out[f"{direction}_n_train"] = n_train
        out[f"{direction}_n_val"] = len(val_d)
    return out


def evaluate_directional(
    test_df: pd.DataFrame,
    directional: dict,
    feature_cols: list[str],
    pair_runtime: dict,
) -> dict:
    """Apply per-direction thresholds; same-bar both-fire conservative skip."""
    long_model = directional.get("long_model")
    short_model = directional.get("short_model")
    if long_model is None or short_model is None:
        return {
            "n_trades": 0,
            "n_skipped_both_fire": 0,
            "sharpe": float("nan"),
            "annual_pnl": float("nan"),
            "status": "MODEL_UNAVAILABLE",
        }
    long_thr = directional["long_threshold"]
    short_thr = directional["short_threshold"]
    test_long = test_df[test_df["direction"] == "long"].copy()
    test_short = test_df[test_df["direction"] == "short"].copy()
    if test_long.empty or test_short.empty:
        return {
            "n_trades": 0,
            "n_skipped_both_fire": 0,
            "sharpe": float("nan"),
            "annual_pnl": float("nan"),
            "status": "EMPTY_TEST_DIRECTION",
        }
    x_test_long = test_long[feature_cols + F1_CATEGORICAL_COLS]
    x_test_short = test_short[feature_cols + F1_CATEGORICAL_COLS]
    long_p = long_model.predict_proba(x_test_long)[:, 1]
    short_p = short_model.predict_proba(x_test_short)[:, 1]
    test_long["_p"] = long_p
    test_short["_p"] = short_p
    long_idx = test_long.set_index(["pair", "signal_ts"])
    short_idx = test_short.set_index(["pair", "signal_ts"])
    common = long_idx.index.intersection(short_idx.index)
    realised: list[float] = []
    n_skipped_both = 0
    for key in common:
        pair, signal_ts = key
        p_l = float(long_idx.loc[key, "_p"])
        p_s = float(short_idx.loc[key, "_p"])
        long_fire = p_l >= long_thr
        short_fire = p_s >= short_thr
        if long_fire and short_fire:
            n_skipped_both += 1
            continue
        if not (long_fire or short_fire):
            continue
        atr = float(long_idx.loc[key, "atr_at_signal_pip"])
        if pair not in pair_runtime:
            continue
        direction = "long" if long_fire else "short"
        r = _compute_realised_barrier_pnl(pair, signal_ts, direction, atr, pair_runtime[pair])
        if r is not None:
            realised.append(r)
    n = len(realised)
    if n == 0:
        return {
            "n_trades": 0,
            "n_skipped_both_fire": n_skipped_both,
            "sharpe": float("nan"),
            "annual_pnl": float("nan"),
            "status": "EMPTY",
            "long_threshold": long_thr,
            "short_threshold": short_thr,
        }
    metrics = compute_8_gate_metrics(np.asarray(realised), n)
    return {
        "n_trades": metrics["n_trades"],
        "n_skipped_both_fire": n_skipped_both,
        "sharpe": metrics["sharpe"],
        "annual_pnl": metrics["annual_pnl"],
        "status": "OK",
        "long_threshold": long_thr,
        "short_threshold": short_thr,
    }


# ---------------------------------------------------------------------------
# AUC-EV theoretical bound (closed-form binormal)
# ---------------------------------------------------------------------------


def conditional_p_positive_at_quantile(auc: float, base_rate: float, quantile: float) -> float:
    """Binormal model: AUC = Φ(d'/√2) with class-conditional unit-variance
    Gaussians. P(positive | predicted ≥ q-th quantile) derived via Bayes.
    """
    if not (0.0 < auc < 1.0) or not (0.0 < base_rate < 1.0) or not (0.0 < quantile < 1.0):
        return float("nan")
    d_prime = norm.ppf(auc) * np.sqrt(2.0)  # binormal d'
    # Score threshold at q-th quantile of mixture
    # Using normal-mixture inversion: P(predicted >= s) = base_rate * (1 - Φ(s - d'/2)) +
    #   (1 - base_rate) * (1 - Φ(s + d'/2)) ... Approximation: pick s such that
    # 1 - mixture_cdf(s) = 1 - quantile.
    # For simplicity we use numeric solver.
    from scipy.optimize import brentq

    def mix_cdf(s: float) -> float:
        return base_rate * norm.cdf(s - d_prime / 2.0) + (1 - base_rate) * norm.cdf(
            s + d_prime / 2.0
        )

    target = quantile
    try:
        s = brentq(lambda x: mix_cdf(x) - target, -10.0, 10.0)
    except ValueError:
        return float("nan")
    # P(positive | predicted >= s)
    p_geq_s_given_pos = 1 - norm.cdf(s - d_prime / 2.0)
    p_geq_s_given_neg = 1 - norm.cdf(s + d_prime / 2.0)
    p_geq_s = base_rate * p_geq_s_given_pos + (1 - base_rate) * p_geq_s_given_neg
    if p_geq_s <= 0:
        return float("nan")
    return float(base_rate * p_geq_s_given_pos / p_geq_s)


def theoretical_auc_ev_bound(
    auc: float,
    base_rate: float,
    k_fav: float,
    k_adv: float,
    mean_atr_pip: float,
    mean_spread_pip: float,
) -> pd.DataFrame:
    rows: list[dict] = []
    for q in THEORETICAL_QUANTILES:
        p_pos = conditional_p_positive_at_quantile(auc, base_rate, q)
        if not np.isfinite(p_pos):
            rows.append(
                {
                    "quantile": q,
                    "p_pos_given_predicted_geq_q": float("nan"),
                    "expected_pnl_pip": float("nan"),
                    "net_ev_pip": float("nan"),
                }
            )
            continue
        expected_pnl = p_pos * k_fav * mean_atr_pip - (1 - p_pos) * k_adv * mean_atr_pip
        net_ev = expected_pnl - mean_spread_pip
        rows.append(
            {
                "quantile": q,
                "p_pos_given_predicted_geq_q": p_pos,
                "expected_pnl_pip": expected_pnl,
                "net_ev_pip": net_ev,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Per-cell verdict logic
# ---------------------------------------------------------------------------


def derive_per_cell_verdict(
    cell_label: str,
    rel_table: pd.DataFrame,
    bucket_pnl: pd.DataFrame,
    threshold_sweep: pd.DataFrame,
    directional_eval: dict,
    bidirectional_metrics: dict,
    theoretical_table: pd.DataFrame,
) -> dict:
    """Returns dict with per-hypothesis verdict (H-A, H-B, H-D, H-F)."""
    cal_verdict, cal_dev, cal_note = calibration_verdict(rel_table)
    valid_buckets_pos = bucket_pnl.dropna(subset=["net_ev_pip"])
    h_f_empirical = "INDETERMINATE"
    if not valid_buckets_pos.empty:
        any_pos_bucket = (valid_buckets_pos["net_ev_pip"] > 0).any()
        h_f_empirical = "REFUTED" if any_pos_bucket else "CONFIRMED"
    valid_th = threshold_sweep[threshold_sweep["status"] == "OK"]
    extended_th = valid_th[valid_th["threshold"] >= 0.50]
    h_b = "REFUTED"
    if not extended_th.empty and (extended_th["sharpe"] > 0.082).any():
        h_b = "CONFIRMED"
    elif extended_th.empty:
        h_b = "INDETERMINATE_EMPTY"
    h_d = "INDETERMINATE"
    if directional_eval.get("status") == "OK":
        bd_sharpe = bidirectional_metrics.get("sharpe", float("nan"))
        dir_sharpe = directional_eval.get("sharpe", float("nan"))
        bd_pnl = bidirectional_metrics.get("annual_pnl", float("nan"))
        dir_pnl = directional_eval.get("annual_pnl", float("nan"))
        if np.isfinite(bd_sharpe) and np.isfinite(dir_sharpe):
            sharpe_lift = dir_sharpe - bd_sharpe
            pnl_pct_change = (dir_pnl - bd_pnl) / abs(bd_pnl) if bd_pnl != 0 else float("inf")
            if sharpe_lift >= DIRECTIONAL_SHARPE_LIFT or pnl_pct_change >= DIRECTIONAL_PNL_LIFT_PCT:
                # Caveat: 50%-from-negative is NOT monetisation
                h_d = "CONFIRMED" if dir_sharpe >= 0.082 else "PARTIAL_LIFT_BUT_STILL_NEG"
            else:
                h_d = "REFUTED"
    h_f_theoretical = "INDETERMINATE"
    if not theoretical_table.empty:
        max_th_ev = theoretical_table["net_ev_pip"].max()
        if np.isfinite(max_th_ev):
            h_f_theoretical = "REFUTED" if max_th_ev > 0 else "CONFIRMED"
    return {
        "cell_label": cell_label,
        "h_a": cal_verdict,
        "h_a_max_dev": cal_dev,
        "h_a_note": cal_note,
        "h_b": h_b,
        "h_d": h_d,
        "h_f_empirical": h_f_empirical,
        "h_f_theoretical": h_f_theoretical,
    }


# ---------------------------------------------------------------------------
# Re-fit harness for F1 / F2 rank-1
# ---------------------------------------------------------------------------


def refit_f1_rank1(labels: pd.DataFrame, args_pairs: list[str]) -> dict:
    """Re-fit F1 rank-1 cell deterministically. Returns trained pipeline +
    train/val/test splits + predictions + metadata."""
    print("--- F1 rank-1 re-fit ---")
    feats: list[pd.DataFrame] = []
    for pair in args_pairs:
        f = compute_f1_features_for_pair(pair, days=SPAN_DAYS)
        feats.append(f)
    feats_all = pd.concat(feats, ignore_index=True)
    feats_all["pair"] = feats_all["pair"].astype("object")
    labels_local = labels.copy()
    labels_local["pair"] = labels_local["pair"].astype("object")
    merged = pd.merge(labels_local, feats_all, on=["pair", "signal_ts"], how="inner")
    nan_mask = merged[F1_FEATURE_COLS_BASE[:-1]].isna().any(axis=1)
    merged_clean = merged[~nan_mask].copy()
    train_full, val_full, test_full, t70, t85 = split_70_15_15(merged_clean)
    # Apply F1 cell admissibility (q=0.20, e=1.25, primary_tf=M5)
    # _admissible_mask_f1 signature: (df, primary_tf, lookback, quantile, expansion)
    train = train_full[
        _admissible_mask_f1(
            train_full,
            F1_RANK1_CELL["tf"],
            F1_RANK1_CELL["lookback"],
            F1_RANK1_CELL["quantile"],
            F1_RANK1_CELL["expansion"],
        )
    ].copy()
    val = val_full[
        _admissible_mask_f1(
            val_full,
            F1_RANK1_CELL["tf"],
            F1_RANK1_CELL["lookback"],
            F1_RANK1_CELL["quantile"],
            F1_RANK1_CELL["expansion"],
        )
    ].copy()
    test = test_full[
        _admissible_mask_f1(
            test_full,
            F1_RANK1_CELL["tf"],
            F1_RANK1_CELL["lookback"],
            F1_RANK1_CELL["quantile"],
            F1_RANK1_CELL["expansion"],
        )
    ].copy()
    print(f"  F1 sizes: train={len(train)} val={len(val)} test={len(test)}")
    pipeline = build_logistic_pipeline_f1()
    x_train = train[F1_FEATURE_COLS_BASE + F1_CATEGORICAL_COLS]
    y_train = train["label"].astype(int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipeline.fit(x_train, y_train)
    x_test = test[F1_FEATURE_COLS_BASE + F1_CATEGORICAL_COLS]
    y_test = test["label"].astype(int).to_numpy()
    test_p = pipeline.predict_proba(x_test)[:, 1]
    test_auc = float(roc_auc_score(y_test, test_p)) if len(np.unique(y_test)) > 1 else float("nan")
    return {
        "cell_label": "F1 rank-1 (M5, q=0.20, e=1.25, lb=50)",
        "pipeline": pipeline,
        "train": train,
        "val": val,
        "test": test,
        "test_p": test_p,
        "y_test": y_test,
        "feature_cols": F1_FEATURE_COLS_BASE,
        "test_auc": test_auc,
        "split_dates": (merged_clean["signal_ts"].min(), t70, t85, merged_clean["signal_ts"].max()),
    }


def refit_f2_rank1(labels: pd.DataFrame, args_pairs: list[str]) -> dict:
    print("--- F2 rank-1 re-fit ---")
    feats: list[pd.DataFrame] = []
    for pair in args_pairs:
        f = compute_f2_features_for_pair(
            pair, days=SPAN_DAYS, trailing_window=F2_RANK1_CELL["trailing_window"]
        )
        feats.append(f)
    feats_all = pd.concat(feats, ignore_index=True)
    feats_all["pair"] = feats_all["pair"].astype("object")
    labels_local = labels.copy()
    labels_local["pair"] = labels_local["pair"].astype("object")
    merged = pd.merge(labels_local, feats_all, on=["pair", "signal_ts"], how="inner")
    nan_check_cols = [c for c in stage25_0c.F2_CATEGORICAL_COLS_BASE if c in merged.columns]
    nan_check_cols = [c for c in nan_check_cols if c != "f2_e_return_sign"]
    nan_check_cols += [c for c in stage25_0c.F2_NUMERIC_COLS_BASE if c in merged.columns]
    nan_mask = merged[nan_check_cols].isna().any(axis=1)
    merged_clean = merged[~nan_mask].copy()
    train_full, val_full, test_full, t70, t85 = split_70_15_15(merged_clean)
    # adm = "none"
    train = _apply_admissibility_filter_f2(train_full, F2_RANK1_CELL["admissibility"]).copy()
    val = _apply_admissibility_filter_f2(val_full, F2_RANK1_CELL["admissibility"]).copy()
    test = _apply_admissibility_filter_f2(test_full, F2_RANK1_CELL["admissibility"]).copy()
    print(f"  F2 sizes: train={len(train)} val={len(val)} test={len(test)}")
    pipeline = build_logistic_pipeline_f2(F2_PER_TF_COLS)
    x_train = train[F2_PER_TF_COLS + stage25_0c.CATEGORICAL_COVARIATES]
    y_train = train["label"].astype(int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipeline.fit(x_train, y_train)
    x_test = test[F2_PER_TF_COLS + stage25_0c.CATEGORICAL_COVARIATES]
    y_test = test["label"].astype(int).to_numpy()
    test_p = pipeline.predict_proba(x_test)[:, 1]
    test_auc = float(roc_auc_score(y_test, test_p)) if len(np.unique(y_test)) > 1 else float("nan")
    return {
        "cell_label": "F2 rank-1 (tw=200, rep=per_tf_only, adm=none)",
        "pipeline": pipeline,
        "train": train,
        "val": val,
        "test": test,
        "test_p": test_p,
        "y_test": y_test,
        "feature_cols": F2_PER_TF_COLS,
        "test_auc": test_auc,
        "split_dates": (merged_clean["signal_ts"].min(), t70, t85, merged_clean["signal_ts"].max()),
    }


# ---------------------------------------------------------------------------
# Cell audit (apply all hypothesis tests)
# ---------------------------------------------------------------------------


def audit_cell(cell_data: dict, pair_runtime: dict, pipeline_builder, *, is_f1: bool) -> dict:
    """Run calibration / per-bucket / threshold-sweep / directional / theoretical."""
    test_p = cell_data["test_p"]
    y_test = cell_data["y_test"]
    test_df = cell_data["test"]
    feature_cols = cell_data["feature_cols"]

    # H-A: calibration
    rel_table = reliability_table(test_p, y_test, n_buckets=N_DECILES)
    rel_table_quintile = reliability_table(test_p, y_test, n_buckets=N_QUINTILES)
    quintile_mono = quintile_monotonicity(test_p, y_test)

    # H-F empirical: per-bucket realised PnL
    bucket_pnl = per_bucket_realised_pnl(test_p, test_df, pair_runtime, n_buckets=N_DECILES)

    # H-B: extended threshold sweep
    threshold_sweep = threshold_sweep_bidirectional(
        test_df, test_p, pair_runtime, EXTENDED_THRESHOLDS
    )

    # Bidirectional baseline metrics: select threshold via val Sharpe proxy
    # (same logic as 25.0b/c).
    test_df_with_p = test_df.copy()
    test_df_with_p["_p"] = test_p
    val_df = cell_data["val"]
    if pipeline_builder is build_logistic_pipeline_f2:
        x_val = val_df[feature_cols + stage25_0c.CATEGORICAL_COVARIATES]
    else:
        x_val = val_df[feature_cols + F1_CATEGORICAL_COLS]
    val_p = cell_data["pipeline"].predict_proba(x_val)[:, 1]
    val_df = val_df.copy()
    val_df["_p"] = val_p
    val_long = val_df[val_df["direction"] == "long"].set_index(["pair", "signal_ts"])
    val_short = val_df[val_df["direction"] == "short"].set_index(["pair", "signal_ts"])
    common_v = val_long.index.intersection(val_short.index)
    bidir_metrics = {
        "sharpe": float("nan"),
        "annual_pnl": float("nan"),
        "n_trades": 0,
        "threshold": float("nan"),
    }
    if len(common_v) >= 10:
        try:
            sel_thr, _ = _select_threshold_on_val(
                val_long.loc[common_v, "_p"],
                val_short.loc[common_v, "_p"],
                val_long.loc[common_v, "label"],
                val_short.loc[common_v, "label"],
                val_long.loc[common_v, "atr_at_signal_pip"],
            )
            row_match = threshold_sweep[
                (threshold_sweep["threshold"] == sel_thr)
                | (threshold_sweep["threshold"] == round(sel_thr, 2))
            ]
            if not row_match.empty:
                bidir_metrics = {
                    "sharpe": float(row_match.iloc[0]["sharpe"]),
                    "annual_pnl": float(row_match.iloc[0]["annual_pnl"]),
                    "n_trades": int(row_match.iloc[0]["n_trades"]),
                    "threshold": sel_thr,
                }
            else:
                bidir_metrics["threshold"] = sel_thr
        except Exception:
            pass

    # H-D: directional comparison
    train_df = cell_data["train"]
    directional = fit_directional_models(train_df, val_df, feature_cols, pipeline_builder)
    directional_eval = evaluate_directional(test_df, directional, feature_cols, pair_runtime)

    # H-F theoretical: AUC-EV bound
    test_auc = cell_data["test_auc"]
    mean_atr = float(test_df["atr_at_signal_pip"].mean()) if len(test_df) > 0 else float("nan")
    mean_spread = (
        float(test_df["spread_at_signal_pip"].mean()) if len(test_df) > 0 else float("nan")
    )
    theoretical_table = theoretical_auc_ev_bound(
        test_auc if np.isfinite(test_auc) else 0.50,
        BASE_POSITIVE_RATE,
        K_FAV,
        K_ADV,
        mean_atr,
        mean_spread,
    )

    verdict = derive_per_cell_verdict(
        cell_data["cell_label"],
        rel_table,
        bucket_pnl,
        threshold_sweep,
        directional_eval,
        bidir_metrics,
        theoretical_table,
    )

    return {
        "cell_label": cell_data["cell_label"],
        "test_auc": test_auc,
        "n_train": len(train_df),
        "n_val": len(val_df),
        "n_test": len(test_df),
        "rel_table_decile": rel_table,
        "rel_table_quintile": rel_table_quintile,
        "quintile_monotonic": quintile_mono,
        "bucket_pnl": bucket_pnl,
        "threshold_sweep": threshold_sweep,
        "bidirectional_metrics": bidir_metrics,
        "directional_eval": directional_eval,
        "directional_low_data": directional.get("low_data_flag", False),
        "theoretical_table": theoretical_table,
        "verdict": verdict,
        "mean_atr_pip": mean_atr,
        "mean_spread_pip": mean_spread,
        "is_f1": is_f1,
    }


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


MANDATORY_CLAUSES = (
    "## Mandatory clauses\n\n"
    "**1. Phase 25 framing.** Phase 25 is not a hyperparameter-tuning phase. "
    "It is a label-and-feature-class redesign phase.\n\n"
    "**2. Diagnostic-leakage prohibition.** The 25.0a-β diagnostic columns "
    "MUST NOT appear in any model's feature matrix.\n\n"
    "**3. Causality and split discipline.** All features use shift(1).rolling "
    "pattern. Train/val/test splits are strictly chronological (70/15/15). "
    "Threshold selection uses VALIDATION ONLY; test set is touched once.\n\n"
    "**4. γ closure preservation.** Phase 25.0d does not modify the γ closure "
    "(PR #279).\n\n"
    "**5. Production-readiness preservation.** Findings in 25.0d are "
    "hypothesis-generating only. Production-readiness requires "
    "X-v2-equivalent frozen-OOS PR per Phase 22 contract.\n\n"
    "**6. Deployment-layer scope clause.** This PR investigates the "
    "structural AUC-PnL gap surfaced in PR #288 §4.2 by analysing F1+F2 "
    "best cells under varied deployment-layer settings. Tests H-A/H-B/H-D/H-F "
    "from #288 §5. Does NOT redesign features, labels, or model class. "
    "Verdict applies only to F1+F2 best cells; convergence with F3-F6 is a "
    "separate question. F1 and F2 verdicts (#284, #287) are NOT modified by "
    "this audit.\n\n"
    "**7. Production misunderstanding guard.** This is a research "
    "deployment-layer audit, not a production deployment study.\n\n"
    "**8. Threshold sweep guard.** The extended threshold sweep is "
    "diagnostic-only. It must not be interpreted as selecting a production "
    "threshold from the test set.\n\n"
    "**9. Directional comparison guard.** Directional comparison is "
    "diagnostic-only. If directional candidate generation appears promising, "
    "it requires a separate predeclared design PR and frozen-OOS validation.\n"
)


def write_eval_report(out_path: Path, audits: list[dict]) -> None:
    lines: list[str] = []
    lines.append("# Stage 25.0d-β — Deployment-Layer Audit Eval")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase25_0d_deployment_audit_design.md` (PR #289)")
    lines.append("")
    lines.append(MANDATORY_CLAUSES)
    lines.append("")
    lines.append("## Test-touched-once invariant")
    lines.append("")
    lines.append("**threshold selected on validation only; test set touched once.**")
    lines.append("")

    for audit in audits:
        lines.append(f"## Cell: {audit['cell_label']}")
        lines.append("")
        lines.append(
            f"- n_train: {audit['n_train']}, n_val: {audit['n_val']}, n_test: {audit['n_test']}"
        )
        lines.append(f"- test AUC: {audit['test_auc']:.4f}")
        lines.append(f"- mean ATR (pip): {audit['mean_atr_pip']:.4f}")
        lines.append(f"- mean spread (pip): {audit['mean_spread_pip']:.4f}")
        if audit["is_f1"] and audit["n_test"] < LOW_BUCKET_N * N_DECILES:
            lines.append("")
            lines.append(
                "> **F1 decile calibration is low-power due to small n_test. "
                "Interpret F1 bucket diagnostics as qualitative only.**"
            )
        lines.append("")

        # Calibration table
        lines.append("### H-A Calibration (decile reliability)")
        lines.append("")
        v = audit["verdict"]
        lines.append(
            f"- Verdict: **{v['h_a']}** (max abs deviation {v['h_a_max_dev']:.4f}; {v['h_a_note']})"
        )
        lines.append(f"- Quintile monotonic: {audit['quintile_monotonic']}")
        lines.append("")
        lines.append("| bucket | n | mean_predicted | actual_pos_rate | brier | LOW_BUCKET_N |")
        lines.append("|---|---|---|---|---|---|")
        for _, r in audit["rel_table_decile"].iterrows():
            mp = r.get("mean_predicted", float("nan"))
            ar = r.get("actual_positive_rate", float("nan"))
            br = r.get("brier", float("nan"))
            mp_s = f"{mp:.4f}" if np.isfinite(mp) else "n/a"
            ar_s = f"{ar:.4f}" if np.isfinite(ar) else "n/a"
            br_s = f"{br:.4f}" if np.isfinite(br) else "n/a"
            lines.append(
                f"| {int(r['bucket'])} | {int(r['n'])} | {mp_s} | {ar_s} | {br_s} | {'YES' if r['low_bucket_n'] else 'no'} |"  # noqa: E501
            )
        lines.append("")
        lines.append("**Quintile (5 buckets) supplementary:**")
        lines.append("")
        lines.append("| bucket | n | mean_predicted | actual_pos_rate | LOW_BUCKET_N |")
        lines.append("|---|---|---|---|---|")
        for _, r in audit["rel_table_quintile"].iterrows():
            mp = r.get("mean_predicted", float("nan"))
            ar = r.get("actual_positive_rate", float("nan"))
            mp_s = f"{mp:.4f}" if np.isfinite(mp) else "n/a"
            ar_s = f"{ar:.4f}" if np.isfinite(ar) else "n/a"
            lines.append(
                f"| {int(r['bucket'])} | {int(r['n'])} | {mp_s} | {ar_s} | {'YES' if r['low_bucket_n'] else 'no'} |"  # noqa: E501
            )
        lines.append("")

        # Per-bucket realised PnL
        lines.append("### H-F empirical: per-bucket realised PnL")
        lines.append("")
        lines.append(f"- Verdict: **{v['h_f_empirical']}**")
        lines.append("")
        lines.append(
            "| bucket | n | mean_realised_pip | mean_spread_pip | net_EV_pip | LOW_BUCKET_N |"
        )
        lines.append("|---|---|---|---|---|---|")
        for _, r in audit["bucket_pnl"].iterrows():
            mr = r.get("mean_realised_pnl", float("nan"))
            ms = r.get("mean_spread_pip", float("nan"))
            nev = r.get("net_ev_pip", float("nan"))
            mr_s = f"{mr:+.4f}" if np.isfinite(mr) else "n/a"
            ms_s = f"{ms:.4f}" if np.isfinite(ms) else "n/a"
            nev_s = f"{nev:+.4f}" if np.isfinite(nev) else "n/a"
            lines.append(
                f"| {int(r['bucket'])} | {int(r['n'])} | {mr_s} | {ms_s} | {nev_s} | {'YES' if r['low_bucket_n'] else 'no'} |"  # noqa: E501
            )
        lines.append("")

        # Threshold sweep
        lines.append("### H-B extended threshold sweep")
        lines.append("")
        lines.append(f"- Verdict: **{v['h_b']}**")
        lines.append("")
        lines.append(
            "> *Extended threshold sweep is diagnostic-only. It must not be interpreted as selecting a production threshold from the test set.*"  # noqa: E501
        )
        lines.append("")
        lines.append("| threshold | status | n_trades | sharpe | annual_pnl |")
        lines.append("|---|---|---|---|---|")
        for _, r in audit["threshold_sweep"].iterrows():
            sh = r.get("sharpe", float("nan"))
            ap = r.get("annual_pnl", float("nan"))
            sh_s = f"{sh:+.4f}" if np.isfinite(sh) else "n/a"
            ap_s = f"{ap:+.1f}" if np.isfinite(ap) else "n/a"
            lines.append(
                f"| {r['threshold']} | {r['status']} | {int(r['n_trades'])} | {sh_s} | {ap_s} |"
            )
        lines.append("")

        # Directional comparison
        lines.append("### H-D bidirectional vs directional")
        lines.append("")
        lines.append(f"- Verdict: **{v['h_d']}**")
        bd = audit["bidirectional_metrics"]
        de = audit["directional_eval"]
        lines.append(
            f"- Bidirectional baseline (val-selected threshold {bd.get('threshold')}): n_trades={bd.get('n_trades', 0)}, Sharpe={bd.get('sharpe', float('nan')):.4f}, ann_pnl={bd.get('annual_pnl', 0):+.1f}"  # noqa: E501
        )
        long_thr = de.get("long_threshold", "n/a")
        short_thr = de.get("short_threshold", "n/a")
        lines.append(
            f"- Directional (long_thr={long_thr}, short_thr={short_thr}): n_trades={de.get('n_trades', 0)}, n_skipped_both={de.get('n_skipped_both_fire', 0)}, Sharpe={de.get('sharpe', float('nan')):.4f}, ann_pnl={de.get('annual_pnl', 0):+.1f}, status={de.get('status')}"  # noqa: E501
        )
        if audit["directional_low_data"]:
            lines.append("- ⚠ DIRECTIONAL_LOW_DATA flag (per-direction n_train < 1000)")
        lines.append("")
        lines.append(
            "> *Directional comparison is diagnostic-only. If directional candidate generation appears promising, it requires a separate predeclared design PR and frozen-OOS validation.*"  # noqa: E501
        )
        lines.append("")
        lines.append(
            "> *Absolute profitability caveat: a 50% improvement from deeply-negative ann_pnl is NOT monetisation; check absolute level.*"  # noqa: E501
        )
        lines.append("")

        # Theoretical AUC-EV bound
        lines.append("### H-F theoretical: AUC-EV bound (closed-form binormal; diagnostic-only)")
        lines.append("")
        lines.append(f"- Verdict (theoretical): **{v['h_f_theoretical']}**")
        lines.append(
            f"- AUC: {audit['test_auc']:.4f}; base rate: {BASE_POSITIVE_RATE}; K_FAV={K_FAV}; K_ADV={K_ADV}; mean_atr_pip={audit['mean_atr_pip']:.4f}; mean_spread_pip={audit['mean_spread_pip']:.4f}"  # noqa: E501
        )
        lines.append("")
        lines.append("| quantile | P(pos | predicted ≥ q) | expected_pnl_pip | net_EV_pip |")
        lines.append("|---|---|---|---|")
        for _, r in audit["theoretical_table"].iterrows():
            pp = r["p_pos_given_predicted_geq_q"]
            ep = r["expected_pnl_pip"]
            nev = r["net_ev_pip"]
            pp_s = f"{pp:.4f}" if np.isfinite(pp) else "n/a"
            ep_s = f"{ep:+.4f}" if np.isfinite(ep) else "n/a"
            nev_s = f"{nev:+.4f}" if np.isfinite(nev) else "n/a"
            lines.append(f"| {r['quantile']} | {pp_s} | {ep_s} | {nev_s} |")
        lines.append("")
        lines.append(
            "> *Theoretical bound is diagnostic-only. Empirical realised barrier PnL takes priority.*"  # noqa: E501
        )
        lines.append("")
        lines.append("---")
        lines.append("")

    # Cross-cell convergence summary
    lines.append("## Cross-cell convergence summary")
    lines.append("")
    lines.append("| Hypothesis | F1 verdict | F2 verdict | Convergent? |")
    lines.append("|---|---|---|---|")
    f1_v = next((a["verdict"] for a in audits if a["is_f1"]), {})
    f2_v = next((a["verdict"] for a in audits if not a["is_f1"]), {})
    for h, label in [
        ("h_a", "H-A calibration"),
        ("h_b", "H-B threshold range"),
        ("h_d", "H-D bidirectional argmax"),
        ("h_f_empirical", "H-F empirical"),
        ("h_f_theoretical", "H-F theoretical"),
    ]:
        f1_val = f1_v.get(h, "n/a")
        f2_val = f2_v.get(h, "n/a")
        convergent = f1_val == f2_val
        lines.append(f"| {label} | {f1_val} | {f2_val} | {'YES' if convergent else 'no'} |")
    lines.append("")
    lines.append(
        "**Evidence weight reminder**: F1 bucket diagnostics are low-power (n_test=96; ~10/decile); F2 bucket diagnostics are high-sample (n_test ~600k; ~60k/decile). F2 is the primary evidence base for calibration and threshold-EV structure; F1 is qualitative only."  # noqa: E501
    )
    lines.append("")
    lines.append("## Routing options post-25.0d-β (no auto-routing; user picks)")
    lines.append("")
    lines.append("Per 25.0d-α §9 verdict criteria:")
    lines.append(
        "- Calibration mismatch + extended threshold rescues → H-A: calibration-before-threshold PR"
    )
    lines.append(
        "- Calibration OK + extended threshold rescues → H-B: expand threshold range design PR"
    )
    lines.append(
        "- Calibration OK + threshold doesn't rescue + directional rescues → H-D: directional pipeline design PR (separate predeclared design + frozen-OOS)"  # noqa: E501
    )
    lines.append(
        "- All deployment-layer hypotheses refuted → empirical structural gap; pivot to F3-F6 / label redesign"  # noqa: E501
    )
    lines.append("")
    lines.append("## Multiple-testing caveat")
    lines.append("")
    lines.append(
        "These are 2 evaluated cells × 4 hypotheses (H-A, H-B, H-D, H-F). Findings are research-level; production-readiness still requires X-v2-equivalent frozen-OOS PR."  # noqa: E501
    )
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_20)
    parser.add_argument("--out-dir", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    if args.smoke:
        args.pairs = ["USD_JPY", "EUR_USD", "GBP_JPY"]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Stage 25.0d-β deployment-layer audit ({len(args.pairs)} pairs) ===")
    print("Loading 25.0a path-quality labels...")
    labels = load_path_quality_labels()
    if args.pairs != PAIRS_20:
        labels = labels[labels["pair"].isin(args.pairs)]
    print(f"  labels rows: {len(labels)}")

    # Build pair_runtime once for both cells
    print("Building pair runtime (M1 OHLC)...")
    pair_runtime: dict[str, dict] = {}
    for pair in args.pairs:
        m1 = load_m1_ba(pair, days=SPAN_DAYS)
        pair_runtime[pair] = {
            "pip": pip_size_for(pair),
            "m1_pos": pd.Series(np.arange(len(m1), dtype=np.int64), index=m1.index),
            "n_m1": len(m1),
            "bid_h": m1["bid_h"].to_numpy(),
            "bid_l": m1["bid_l"].to_numpy(),
            "bid_c": m1["bid_c"].to_numpy(),
            "ask_h": m1["ask_h"].to_numpy(),
            "ask_l": m1["ask_l"].to_numpy(),
            "ask_c": m1["ask_c"].to_numpy(),
            "ask_o": m1["ask_o"].to_numpy(),
            "bid_o": m1["bid_o"].to_numpy(),
        }

    audits: list[dict] = []
    t0 = time.time()
    f1_data = refit_f1_rank1(labels, args.pairs)
    print(f"  F1 re-fit: {time.time() - t0:5.1f}s")
    audit_f1 = audit_cell(f1_data, pair_runtime, build_logistic_pipeline_f1, is_f1=True)
    audits.append(audit_f1)

    t0 = time.time()
    f2_data = refit_f2_rank1(labels, args.pairs)
    print(f"  F2 re-fit: {time.time() - t0:5.1f}s")
    audit_f2 = audit_cell(f2_data, pair_runtime, build_logistic_pipeline_f2, is_f1=False)
    audits.append(audit_f2)

    out_path = args.out_dir / "eval_report.md"
    write_eval_report(out_path, audits)
    print(f"\nReport: {out_path}")
    for a in audits:
        v = a["verdict"]
        print(
            f"  {a['cell_label']}: H-A={v['h_a']}, H-B={v['h_b']}, H-D={v['h_d']}, H-F_emp={v['h_f_empirical']}, H-F_theo={v['h_f_theoretical']}"  # noqa: E501
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
