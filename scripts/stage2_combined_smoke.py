"""stage2_combined_smoke.py — Stage 2.1 best (tp=1.5/sl=1.0/conf=0.35) × Stage 2.2 best (small_boost)."""
from __future__ import annotations
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, "scripts")
import compare_prod_ablation as m

sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

_DATA_DIR = Path("data")

# V2 base + 2.1 best + 2.2 best
m._TRAINING_MODE         = "multi"
m._EV_SL_FACTOR          = 1.0
m._TP_MULT               = 1.5
m._SL_MULT               = 1.0
m._CONF_THR              = 0.35     # ← Stage 2.1 best
m._USE_CLASS_WEIGHT      = True     # any True triggers custom weight branch
m._CUSTOM_CLASS_WEIGHT   = {0: 1.2, 1: 1.0, 2: 1.2}  # ← Stage 2.2 best (small_boost)


def main() -> None:
    print("="*80)
    print("Stage 2.1 + 2.2 combined smoke")
    print(f"  tp={m._TP_MULT}  sl={m._SL_MULT}  conf_thr={m._CONF_THR}")
    print(f"  class_weight=small_boost {m._CUSTOM_CLASS_WEIGHT}")
    print("="*80, flush=True)

    raw_dfs = {}
    for pair in m._ALL_PAIRS:
        p = _DATA_DIR / f"candles_{pair}_M1_730d_BA.jsonl"
        if not p.exists():
            continue
        raw_dfs[pair] = m._load_ba_candles(p)
    print(f"\n  loaded {len(raw_dfs)} pairs", flush=True)

    feat_dfs = {}
    for pair, df in raw_dfs.items():
        pip = m._PIP_SIZE.get(pair, 0.0001)
        df = m._add_base_features(df)
        df = m._add_upper_tf_features(df)
        df = m._add_mtf_features(df)
        df = m._add_spread_features(df, pip)
        feat_dfs[pair] = df
    pair_dfs = {pair: m._add_labels(df, pair) for pair, df in feat_dfs.items()}
    print(f"  features+labels built", flush=True)
    del raw_dfs, feat_dfs

    feat_cols = m._get_base_feat_for_tf(1) + list(m._SPREAD_FEAT)
    t_min = min(df["timestamp"].min() for df in pair_dfs.values())
    t_max = max(df["timestamp"].max() for df in pair_dfs.values())
    folds = m._generate_folds(t_min, t_max, 365, 90)
    print(f"  {len(folds)} folds", flush=True)

    t0 = time.time()
    all_pnls = []
    open_until_ts: dict = {}

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
        print(f"  fold {fi}/{len(folds)} done", flush=True)

    res = m._stats(all_pnls)
    elapsed = time.time() - t0

    print("\n" + "="*80)
    print(f"COMBINED RESULT")
    print("="*80)
    print(f"  Sharpe = {res['sharpe']:+.4f}")
    print(f"  Hit%   = {res['hit_pct']:5.1f}%")
    print(f"  N      = {res['n']:,d}")
    print(f"  PnL    = {res['pnl']:+10.1f} pip")
    print(f"  MaxDD  = {res['maxdd']:+10.1f} pip")
    print(f"  ({elapsed:.0f}s)")
    print()
    print(f"vs V2 baseline (none, conf=0.40):   Sharpe=-0.1894")
    print(f"vs Stage 2.1 best (conf=0.35):       Sharpe=-0.1454")
    print(f"vs Stage 2.2 best (small_boost):     Sharpe=-0.1006")


if __name__ == "__main__":
    main()
