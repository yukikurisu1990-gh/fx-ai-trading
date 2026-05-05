"""stage2_4_topk_sweep.py — Top-K sweep at HORIZON=40 + small_boost (Stage 2.3 best)."""
from __future__ import annotations
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, "scripts")
import compare_prod_ablation as m

sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

_DATA_DIR = Path("data")
_TOP_KS = [1, 2, 3, 5]

# V2 base + Stage 2.2 best + Stage 2.3 best
m._TRAINING_MODE         = "multi"
m._EV_SL_FACTOR          = 1.0
m._TP_MULT               = 1.5
m._SL_MULT               = 1.0
m._CONF_THR              = 0.40
m._HORIZON               = 40
m._USE_CLASS_WEIGHT      = True
m._CUSTOM_CLASS_WEIGHT   = {0: 1.2, 1: 1.0, 2: 1.2}  # small_boost


def main() -> None:
    print("="*80)
    print(f"Stage 2.4 Top-K sweep at HORIZON=40 + small_boost ({_TOP_KS})")
    print(f"  tp={m._TP_MULT}  sl={m._SL_MULT}  conf={m._CONF_THR}  H={m._HORIZON}  cw=small_boost")
    print("="*80, flush=True)

    raw_dfs = {}
    for pair in m._ALL_PAIRS:
        p = _DATA_DIR / f"candles_{pair}_M1_730d_BA.jsonl"
        if not p.exists():
            continue
        raw_dfs[pair] = m._load_ba_candles(p)
    print(f"\n[1/3] loaded {len(raw_dfs)} pairs", flush=True)

    feat_dfs = {}
    for pair, df in raw_dfs.items():
        pip = m._PIP_SIZE.get(pair, 0.0001)
        df = m._add_base_features(df)
        df = m._add_upper_tf_features(df)
        df = m._add_mtf_features(df)
        df = m._add_spread_features(df, pip)
        feat_dfs[pair] = df
    pair_dfs = {pair: m._add_labels(df, pair) for pair, df in feat_dfs.items()}
    print(f"[2/3] features+labels built", flush=True)
    del raw_dfs, feat_dfs

    feat_cols = m._get_base_feat_for_tf(1) + list(m._SPREAD_FEAT)

    # Train models once (Top-K only affects sim)
    t_min = min(df["timestamp"].min() for df in pair_dfs.values())
    t_max = max(df["timestamp"].max() for df in pair_dfs.values())
    folds = m._generate_folds(t_min, t_max, 365, 90)
    print(f"  {len(folds)} folds", flush=True)

    fold_cache = []
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
        t0 = time.time()
        models = m._train_models(pair_dfs, feat_cols, train_mask,
                                 regularize=True, multipair=True, fold_seed=fi)
        fold_cache.append((models, test_mask))
        print(f"  fold {fi}/{len(folds)} train ({time.time()-t0:.1f}s)", flush=True)

    print(f"\n[3/3] sim with K = {_TOP_KS}", flush=True)
    results = []
    for k in _TOP_KS:
        m._TOP_K = k
        t0 = time.time()
        all_pnls = []
        open_until_ts: dict = {}
        for models, test_mask in fold_cache:
            pnls, open_until_ts = m._simulate(
                pair_dfs, models, feat_cols, test_mask, multipair=True,
                open_until_ts=open_until_ts,
            )
            all_pnls.extend(pnls)
        res = m._stats(all_pnls)
        elapsed = time.time() - t0
        results.append((k, res, elapsed))
        print(f"  K={k}  Sharpe={res['sharpe']:+.4f}  hit={res['hit_pct']:5.1f}%  "
              f"n={res['n']:6,d}  PnL={res['pnl']:+9.1f}  ({elapsed:.0f}s)", flush=True)

    print("\n" + "="*80)
    print("Stage 2.4 RESULTS")
    print("="*80)
    print(f"  {'K':>4}  {'Sharpe':>8}  {'Hit%':>6}  {'N':>6}  {'PnL(pip)':>10}  {'MaxDD':>10}")
    print("  " + "-"*70)
    for k, res, _ in sorted(results, key=lambda x: -x[1]['sharpe']):
        print(f"  {k:4d}  {res['sharpe']:+8.4f}  {res['hit_pct']:6.1f}%  "
              f"{res['n']:6,d}  {res['pnl']:+10.1f}  {res['maxdd']:+10.1f}")
    print("="*80)


if __name__ == "__main__":
    main()
