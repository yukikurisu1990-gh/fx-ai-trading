"""stage1_2_feature_cleanup.py — Drop low-gain features and re-evaluate.

Per Stage 1.1 importance analysis, drop 10 features with gain% < 0.6 from each base's
best feature config and re-run the WF backtest.

Drop list (10 features, identified from M15+CSI fold-1 importance):
  sma_20, h1_trend_dir, h4_full_trend_dir, h8_trend_dir,
  ema_26, bb_middle, ema_12, sma_50, macd_line, bb_lower

Bases (with their best Stage 0.7 feature additions):
  M1_V2_baseline   + Regime_full   (53 -> 43 features)
  M1_chained_best  + Regime_cont   (49 -> 39 features)
  M15_chained_best + CSI            (50 -> 40 features)
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, "scripts")
import compare_prod_ablation as m
import stage0_7_csi_regime_as_features as s07

sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

_DATA_DIR = Path("data")

_DROP_LIST = [
    "sma_20", "h1_trend_dir", "h4_full_trend_dir", "h8_trend_dir",
    "ema_26", "bb_middle", "ema_12", "sma_50", "macd_line", "bb_lower",
]

# (name, base_tf, suffix, horizon, cw, extra_feat_groups)
_CASES = [
    ("M1_V2_Regime_full",   1, "730d",  20, None,
        ["regime_cont", "regime_oh"]),
    ("M1_chained_Regime_cont", 1, "730d",  40, {0: 1.2, 1: 1.0, 2: 1.2},
        ["regime_cont"]),
    ("M15_chained_CSI",     15, "1825d",  3, {0: 1.2, 1: 1.0, 2: 1.2},
        ["csi"]),
]


def _build_feat_cols(base_tf: int, extra_groups: list[str]) -> list[str]:
    base_cols = m._get_base_feat_for_tf(base_tf) + list(m._SPREAD_FEAT)
    extra: list[str] = []
    if "csi" in extra_groups:
        extra += ["csi_base", "csi_quote", "csi_diff_signed"]
    if "regime_cont" in extra_groups:
        extra += ["atr_ratio", "trend_slope"]
    if "regime_oh" in extra_groups:
        extra += [f"regime_{c}" for c in s07._REGIME_CATS]
    return base_cols + extra


def _attach_extra(pair_dfs, extra_groups, csi_feats, regime_feats):
    if "csi" in extra_groups:
        s07._attach_features(pair_dfs, csi_feats, ["csi_base", "csi_quote", "csi_diff_signed"])
    if "regime_cont" in extra_groups:
        s07._attach_features(pair_dfs, regime_feats, ["atr_ratio", "trend_slope"])
    if "regime_oh" in extra_groups:
        s07._attach_features(pair_dfs, regime_feats,
                              [f"regime_{c}" for c in s07._REGIME_CATS])


def _train_and_simulate(pair_dfs, feat_cols):
    t_min = min(df["timestamp"].min() for df in pair_dfs.values())
    t_max = max(df["timestamp"].max() for df in pair_dfs.values())
    folds = m._generate_folds(t_min, t_max, 365, 90)
    open_until_ts = {}
    all_pnls = []
    for fi, fold in enumerate(folds, 1):
        tr_s, tr_e = fold["train_start"], fold["train_end"]
        te_s, te_e = fold["test_start"],  fold["test_end"]
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
        test_mask = {p: (df["timestamp"] >= te_s) & (df["timestamp"] < te_e)
                     for p, df in pair_dfs.items()}
        models = m._train_models(pair_dfs, feat_cols, train_mask,
                                 regularize=True, multipair=True, fold_seed=fi)
        pnls, open_until_ts = m._simulate(
            pair_dfs, models, feat_cols, test_mask, multipair=True,
            open_until_ts=open_until_ts,
        )
        all_pnls.extend(pnls)
        print(f"    fold {fi}/{len(folds)} done", flush=True)
    return m._stats(all_pnls)


def _run_case(name: str, base_tf: int, suffix: str, horizon: int,
              cw: dict | None, extra_groups: list[str]) -> list[tuple]:
    print(f"\n{'#'*80}\n# {name}\n{'#'*80}", flush=True)

    m._BAR_MINUTES = base_tf
    m._HORIZON = horizon
    m._TRAINING_MODE = "multi"
    m._TP_MULT = 1.5
    m._SL_MULT = 1.0
    m._CONF_THR = 0.40
    m._TOP_K = 3
    m._EV_SL_FACTOR = 1.0
    if cw is None:
        m._USE_CLASS_WEIGHT = False
        m._CUSTOM_CLASS_WEIGHT = None
    else:
        m._USE_CLASS_WEIGHT = True
        m._CUSTOM_CLASS_WEIGHT = cw

    raw_dfs = {}
    for pair in m._ALL_PAIRS:
        p = _DATA_DIR / f"candles_{pair}_M{base_tf}_{suffix}_BA.jsonl"
        if not p.exists():
            continue
        raw_dfs[pair] = m._load_ba_candles(p)
    print(f"  loaded {len(raw_dfs)} pairs", flush=True)

    t0 = time.time()
    feat_dfs = {}
    for pair, df in raw_dfs.items():
        pip = m._PIP_SIZE.get(pair, 0.0001)
        df = m._add_base_features(df)
        df = m._add_upper_tf_features(df)
        df = m._add_mtf_features(df)
        df = m._add_spread_features(df, pip)
        feat_dfs[pair] = df
    pair_dfs_master = {pair: m._add_labels(df, pair) for pair, df in feat_dfs.items()}
    print(f"  features+labels built ({time.time()-t0:.1f}s)", flush=True)
    del raw_dfs

    csi_feats = s07._compute_csi_signed_features(feat_dfs)
    regime_feats = s07._compute_regime_features(feat_dfs)
    del feat_dfs

    full_feat_cols = _build_feat_cols(base_tf, extra_groups)

    results = []
    # Variant a: keep all (reference)
    print(f"\n  >> a_ref ({len(full_feat_cols)} feat, no drop)", flush=True)
    pair_dfs = {pair: df.copy() for pair, df in pair_dfs_master.items()}
    _attach_extra(pair_dfs, extra_groups, csi_feats, regime_feats)
    t0 = time.time()
    res = _train_and_simulate(pair_dfs, full_feat_cols)
    results.append((name, "a_ref", len(full_feat_cols), res))
    print(f"  a_ref       feat={len(full_feat_cols)}  Sharpe={res['sharpe']:+.4f}  "
          f"hit={res['hit_pct']:5.1f}%  n={res['n']:6,d}  PnL={res['pnl']:+9.1f}  ({time.time()-t0:.0f}s)",
          flush=True)
    del pair_dfs

    # Variant b: drop low-gain features
    cleaned_feat_cols = [f for f in full_feat_cols if f not in _DROP_LIST]
    print(f"\n  >> b_cleaned ({len(cleaned_feat_cols)} feat, dropped {len(full_feat_cols)-len(cleaned_feat_cols)})", flush=True)
    pair_dfs = {pair: df.copy() for pair, df in pair_dfs_master.items()}
    _attach_extra(pair_dfs, extra_groups, csi_feats, regime_feats)
    t0 = time.time()
    res = _train_and_simulate(pair_dfs, cleaned_feat_cols)
    results.append((name, "b_cleaned", len(cleaned_feat_cols), res))
    print(f"  b_cleaned   feat={len(cleaned_feat_cols)}  Sharpe={res['sharpe']:+.4f}  "
          f"hit={res['hit_pct']:5.1f}%  n={res['n']:6,d}  PnL={res['pnl']:+9.1f}  ({time.time()-t0:.0f}s)",
          flush=True)
    del pair_dfs

    return results


def main() -> None:
    print("="*80)
    print("Stage 1.2 - Feature cleanup (drop 10 low-gain features)")
    print(f"  Drop list: {_DROP_LIST}")
    print(f"  Bases: {[c[0] for c in _CASES]}")
    print("="*80, flush=True)

    all_results = []
    for case_args in _CASES:
        all_results.extend(_run_case(*case_args))

    print("\n\n" + "="*100)
    print("STAGE 1.2 SUMMARY")
    print("="*100)
    print(f"  {'Case':<28}  {'Variant':<12}  {'Feat':>4}  {'Sharpe':>8}  {'Hit%':>6}  {'N':>7}  {'PnL':>10}")
    print("  " + "-"*90)
    for name, v, n_feat, res in all_results:
        print(f"  {name:<28}  {v:<12}  {n_feat:>4d}  {res['sharpe']:+8.4f}  "
              f"{res['hit_pct']:6.1f}%  {res['n']:7,d}  {res['pnl']:+10.1f}")
    print("="*100)


if __name__ == "__main__":
    main()
