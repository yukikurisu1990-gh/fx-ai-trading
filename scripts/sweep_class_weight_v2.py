"""sweep_class_weight_v2.py — M1 V2 baseline で class_weight variants を比較.

各 variant は同一 fold/data/feat で sim 速度を最大化 (LGBM 訓練のみ class_weight が変わる)。

Variants:
  none           : V2 現状 (自然分布、較正最適と推定)
  balanced       : sklearn 既定の 1/(n_classes×freq)
  mild_balanced  : sqrt(balanced) — 中庸
  small_boost    : 1.2/1.0/1.2 — 微小ブースト
  cost_sensitive : 1.5/0.5/1.5 — TP/SL の絶対値で重み付け
  moderate       : 2.0/0.5/2.0 — 中間ブースト
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "scripts")
import compare_prod_ablation as m

sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

_DATA_DIR = Path("data")

# V2 base settings
m._TRAINING_MODE    = "multi"
m._EV_SL_FACTOR     = 1.0
m._TP_MULT          = 1.5
m._SL_MULT          = 1.0
m._CONF_THR         = 0.40

# class_weight variants for M1 multinomial (~13/74/13 distribution)
# encoded: 0=short(-1), 1=timeout(0), 2=long(+1)
_VARIANTS: list[tuple[str, str | dict | None]] = [
    ("none",           None),
    ("balanced",       "balanced"),
    ("mild_balanced",  {0: 1.6, 1: 0.67, 2: 1.6}),     # sqrt(balanced)
    ("small_boost",    {0: 1.2, 1: 1.0, 2: 1.2}),
    ("cost_sensitive", {0: 1.5, 1: 0.5, 2: 1.5}),
    ("moderate",       {0: 2.0, 1: 0.5, 2: 2.0}),
]


def main() -> None:
    print("="*80)
    print("M1 V2 class_weight sweep")
    print(f"  variants: {[v[0] for v in _VARIANTS]}")
    print("="*80, flush=True)

    # Load + features (1 回のみ)
    print("\n[1/3] Loading candles ...", flush=True)
    raw_dfs = {}
    for pair in m._ALL_PAIRS:
        p = _DATA_DIR / f"candles_{pair}_M1_730d_BA.jsonl"
        if not p.exists(): continue
        raw_dfs[pair] = m._load_ba_candles(p)
    print(f"  loaded {len(raw_dfs)} pairs", flush=True)

    print("\n[2/3] Building features + labels ...", flush=True)
    feat_dfs = {}
    for pair, df in raw_dfs.items():
        pip = m._PIP_SIZE.get(pair, 0.0001)
        df = m._add_base_features(df)
        df = m._add_upper_tf_features(df)
        df = m._add_mtf_features(df)
        df = m._add_spread_features(df, pip)
        feat_dfs[pair] = df
    pair_dfs = {pair: m._add_labels(df, pair) for pair, df in feat_dfs.items()}
    print(f"  features built", flush=True)
    del raw_dfs, feat_dfs

    feat_cols = m._get_base_feat_for_tf(1) + list(m._SPREAD_FEAT)  # M1 + spread (V2 baseline)
    t_min = min(df["timestamp"].min() for df in pair_dfs.values())
    t_max = max(df["timestamp"].max() for df in pair_dfs.values())
    folds = m._generate_folds(t_min, t_max, 365, 90)
    print(f"  {len(folds)} folds", flush=True)

    # Run each variant
    print(f"\n[3/3] Running {len(_VARIANTS)} variants ...", flush=True)
    results = []
    for v_name, cw in _VARIANTS:
        # Set up class_weight
        if cw is None:
            m._USE_CLASS_WEIGHT = False
            m._CUSTOM_CLASS_WEIGHT = None
        elif cw == "balanced":
            m._USE_CLASS_WEIGHT = True
            m._CUSTOM_CLASS_WEIGHT = None
        else:
            m._USE_CLASS_WEIGHT = True  # ignored
            m._CUSTOM_CLASS_WEIGHT = cw

        t0 = time.time()
        all_pnls = []
        open_until_ts: dict = {}
        purge_td = pd.Timedelta(minutes=m._HORIZON)

        for fi, fold in enumerate(folds, 1):
            tr_s, tr_e = fold["train_start"], fold["train_end"]
            te_s, te_e = fold["test_start"],  fold["test_end"]
            # 正しい purge: bar 数ベース (週末跨ぎでも leak 無し)
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
            test_mask = {p: (df["timestamp"]>=te_s)&(df["timestamp"]<te_e) for p, df in pair_dfs.items()}
            models = m._train_models(pair_dfs, feat_cols, train_mask,
                                     regularize=True, multipair=True, fold_seed=fi)
            pnls, open_until_ts = m._simulate(
                pair_dfs, models, feat_cols, test_mask, multipair=True,
                open_until_ts=open_until_ts,
            )
            all_pnls.extend(pnls)
        res = m._stats(all_pnls)
        elapsed = time.time() - t0
        results.append((v_name, cw, res, elapsed))
        print(f"  {v_name:15s}  Sharpe={res['sharpe']:+.4f}  hit={res['hit_pct']:5.1f}%  "
              f"n={res['n']:6,d}  PnL={res['pnl']:+9.1f}  ({elapsed:.0f}s)", flush=True)

    # Summary
    print("\n" + "="*80)
    print("SWEEP RESULTS (Sharpe descending)")
    print("="*80)
    print(f"  {'variant':<16}  {'Sharpe':>8}  {'Hit%':>6}  {'N':>6}  {'PnL(pip)':>10}  {'MaxDD':>10}")
    print("  " + "-"*70)
    for name, cw, res, _ in sorted(results, key=lambda x: -x[2]['sharpe']):
        print(f"  {name:<16}  {res['sharpe']:+8.4f}  {res['hit_pct']:6.1f}%  "
              f"{res['n']:6,d}  {res['pnl']:+10.1f}  {res['maxdd']:+10.1f}")
    print("="*80)


if __name__ == "__main__":
    main()
