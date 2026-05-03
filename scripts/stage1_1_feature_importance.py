"""stage1_1_feature_importance.py — Dump LGBM feature_importances_ from M15+CSI best.

Use the current-best config (M15 chained_best + CSI features, Stage 0.7 b) result)
to identify redundant / weak features before refining the feature set.

Train fold 1 only (full-fold training is overkill for importance ranking).
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "scripts")
import compare_prod_ablation as m
import stage0_5_meta_layer_eval as s05
import stage0_7_csi_regime_as_features as s07

sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

_DATA_DIR = Path("data")


def main() -> None:
    print("="*80)
    print("Stage 1.1 - Feature importances from M15 + CSI best config")
    print("="*80, flush=True)

    # M15 chained_best + CSI config
    base_tf, suffix, horizon = 15, "1825d", 3
    cw = {0: 1.2, 1: 1.0, 2: 1.2}

    m._BAR_MINUTES = base_tf
    m._HORIZON = horizon
    m._TRAINING_MODE = "multi"
    m._TP_MULT = 1.5
    m._SL_MULT = 1.0
    m._USE_CLASS_WEIGHT = True
    m._CUSTOM_CLASS_WEIGHT = cw

    # Load
    raw_dfs = {}
    for pair in m._ALL_PAIRS:
        p = _DATA_DIR / f"candles_{pair}_M{base_tf}_{suffix}_BA.jsonl"
        if not p.exists():
            continue
        raw_dfs[pair] = m._load_ba_candles(p)
    print(f"loaded {len(raw_dfs)} pairs", flush=True)

    # Features
    t0 = time.time()
    feat_dfs = {}
    for pair, df in raw_dfs.items():
        pip = m._PIP_SIZE.get(pair, 0.0001)
        df = m._add_base_features(df)
        df = m._add_upper_tf_features(df)
        df = m._add_mtf_features(df)
        df = m._add_spread_features(df, pip)
        feat_dfs[pair] = df
    pair_dfs = {pair: m._add_labels(df, pair) for pair, df in feat_dfs.items()}
    print(f"features+labels built ({time.time()-t0:.1f}s)", flush=True)

    # CSI features
    t0 = time.time()
    csi_feats = s07._compute_csi_signed_features(feat_dfs)
    print(f"CSI features built ({time.time()-t0:.1f}s)", flush=True)
    del feat_dfs, raw_dfs

    # Attach CSI
    s07._attach_features(pair_dfs, csi_feats, ["csi_base", "csi_quote", "csi_diff_signed"])

    base_feat_cols = m._get_base_feat_for_tf(base_tf) + list(m._SPREAD_FEAT)
    feat_cols = base_feat_cols + ["csi_base", "csi_quote", "csi_diff_signed"]
    print(f"\n{len(feat_cols)} features", flush=True)

    # Train fold 1 only
    t_min = min(df["timestamp"].min() for df in pair_dfs.values())
    t_max = max(df["timestamp"].max() for df in pair_dfs.values())
    folds = m._generate_folds(t_min, t_max, 365, 90)
    print(f"{len(folds)} folds, training fold 1 only for importance dump", flush=True)
    fold = folds[0]
    tr_s, tr_e = fold["train_start"], fold["train_end"]

    train_mask = {}
    for pair in pair_dfs:
        ts = pair_dfs[pair]["timestamp"]
        mfull = (ts >= tr_s) & (ts < tr_e)
        idx_true = mfull[mfull].index
        if len(idx_true) > m._HORIZON + 1:
            m_kept = pd.Series(False, index=mfull.index)
            m_kept.loc[idx_true[:-(m._HORIZON + 1)]] = True
            train_mask[pair] = m_kept
        else:
            train_mask[pair] = pd.Series(False, index=mfull.index)

    t0 = time.time()
    models = m._train_models(pair_dfs, feat_cols, train_mask,
                             regularize=True, multipair=True, fold_seed=1)
    print(f"trained ({time.time()-t0:.1f}s)", flush=True)

    # Dump importances
    mp_models = models[m._MULTIPAIR_KEY]
    multi_model = mp_models["multi"]
    # feat_cols + ["pair_id"] is the actual training input
    full_cols = feat_cols + ["pair_id"]

    # LightGBM exposes feature_importances_ (default = 'split' = number of times feature is used)
    # Also try 'gain' which is total gain across splits
    split_imp = multi_model.feature_importances_
    try:
        gain_imp = multi_model.booster_.feature_importance(importance_type="gain")
    except Exception:
        gain_imp = np.zeros_like(split_imp)

    print(f"\n{'#'*80}")
    print(f"# Feature importances ({len(full_cols)} features, sorted by GAIN)")
    print(f"{'#'*80}")
    print(f"  {'rank':>4}  {'feature':<28}  {'split':>10}  {'gain':>14}  {'gain%':>6}")
    print(f"  {'-'*70}")
    total_gain = gain_imp.sum() if gain_imp.sum() > 0 else 1.0
    sorted_idx = np.argsort(-gain_imp)
    for rank, i in enumerate(sorted_idx, 1):
        pct = 100.0 * gain_imp[i] / total_gain
        print(f"  {rank:>4}  {full_cols[i]:<28}  {split_imp[i]:>10}  {gain_imp[i]:>14.1f}  {pct:>5.1f}%")

    # Group analysis: identify likely redundant features (close-derived smoothing)
    print(f"\n{'#'*80}")
    print(f"# Group analysis")
    print(f"{'#'*80}")

    groups = {
        "close_smooth": ["ema_12", "ema_26", "sma_20", "sma_50", "bb_middle"],
        "bb_band":      ["bb_upper", "bb_lower", "bb_width"],
        "macd":         ["macd_line", "macd_signal", "macd_histogram"],
        "atr_base":     ["atr_14"],
        "rsi":          ["rsi_14"],
        "spread":       ["spread_now_pip", "spread_ma_ratio_20", "spread_zscore_50"],
        "csi":          ["csi_base", "csi_quote", "csi_diff_signed"],
        "pair_id":      ["pair_id"],
        "upper_m5":     [f"m5{s}" for s in ["_return_1","_return_3","_volatility","_rsi_14","_ma_slope","_bb_pct_b","_trend_slope","_trend_dir"]],
        "upper_m15":    [f"m15{s}" for s in ["_return_1","_return_3","_volatility","_rsi_14","_ma_slope","_bb_pct_b","_trend_slope","_trend_dir"]],
        "upper_h1":     [f"h1{s}" for s in ["_return_1","_return_3","_volatility","_rsi_14","_ma_slope","_bb_pct_b","_trend_slope","_trend_dir"]],
        "mtf_h4":       ["h4_atr_14"],
        "mtf_d1":       ["d1_return_3", "d1_range_pct", "d1_atr_14"],
        "mtf_w1":       ["w1_return_1", "w1_range_pct"],
    }
    print(f"\n  {'group':<14}  {'n_feat':>6}  {'sum_gain':>14}  {'gain%':>6}  {'avg/feat':>10}")
    print(f"  {'-'*60}")
    grouped: list[tuple[str, int, float, float]] = []
    name_to_idx = {f: i for i, f in enumerate(full_cols)}
    for gname, gfeats in groups.items():
        idx_list = [name_to_idx[f] for f in gfeats if f in name_to_idx]
        if not idx_list:
            continue
        s_gain = gain_imp[idx_list].sum()
        pct = 100.0 * s_gain / total_gain
        avg = s_gain / max(1, len(idx_list))
        grouped.append((gname, len(idx_list), s_gain, pct))
    for gname, n, s, pct in sorted(grouped, key=lambda x: -x[2]):
        print(f"  {gname:<14}  {n:>6d}  {s:>14.1f}  {pct:>5.1f}%  {s/max(1,n):>10.1f}")

    # Bottom features (candidates for removal)
    print(f"\n{'#'*80}")
    print(f"# Bottom 15 features by gain (candidates for removal)")
    print(f"{'#'*80}")
    bottom_idx = np.argsort(gain_imp)[:15]
    for i in bottom_idx:
        pct = 100.0 * gain_imp[i] / total_gain
        print(f"  {full_cols[i]:<28}  split={split_imp[i]:>4d}  gain={gain_imp[i]:>10.1f}  ({pct:.2f}%)")


if __name__ == "__main__":
    main()
