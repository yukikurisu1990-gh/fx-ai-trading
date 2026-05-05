"""sweep_conf_tpsl_v2.py — V2 (multi + no_class_weight + 全 bug fix) で conf_thr × tp/sl の 2D sweep.

設計:
  - データロード + 特徴量構築は 1 回のみ
  - tp/sl 4 通り × 5 folds = 20 multipair モデル学習 (約 25-30 分)
  - 各 (tp, sl) の学習結果に conf_thr 4 通りを事後シミュレーションで適用 = 16 セル

セル: G_mp_wf365 (multipair, WF 365d/90d, 730d data, spread+reg)
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "scripts")
import compare_prod_ablation as m

# ----- スイープ -----
_CONF_THRS = [0.25, 0.30, 0.35, 0.40]
_TP_SLS    = [(1.0, 1.0), (1.5, 1.0), (2.0, 1.0), (1.5, 1.5)]
_DATA_DIR  = Path("data")

# V2 settings
m._TRAINING_MODE    = "multi"
m._USE_CLASS_WEIGHT = False
m._EV_SL_FACTOR     = 1.0

sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]


def main() -> None:
    print("="*80, flush=True)
    print(f"V2 Sweep: training_mode=multi  class_weight=None  ev_sl_factor=1.0", flush=True)
    print(f"  conf_thrs : {_CONF_THRS}", flush=True)
    print(f"  tp/sl     : {_TP_SLS}", flush=True)
    print(f"  total     : {len(_CONF_THRS) * len(_TP_SLS)} cells", flush=True)
    print("="*80, flush=True)

    # 1) Load BA candles
    print("\n[1/3] Loading candles ...", flush=True)
    t0 = time.time()
    raw_dfs: dict[str, pd.DataFrame] = {}
    for pair in m._ALL_PAIRS:
        p = _DATA_DIR / f"candles_{pair}_M1_730d_BA.jsonl"
        if not p.exists():
            print(f"  SKIP {pair}: not found")
            continue
        raw_dfs[pair] = m._load_ba_candles(p)
    print(f"  loaded {len(raw_dfs)} pairs in {time.time()-t0:.1f}s", flush=True)

    # 2) Build features (label-independent)
    print("\n[2/3] Building features ...", flush=True)
    t0 = time.time()
    feat_only: dict[str, pd.DataFrame] = {}
    for pair, df in raw_dfs.items():
        pip = m._PIP_SIZE.get(pair, 0.0001)
        df = m._add_base_features(df)
        df = m._add_upper_tf_features(df)
        df = m._add_mtf_features(df)
        df = m._add_spread_features(df, pip)
        feat_only[pair] = df
    print(f"  features built in {time.time()-t0:.1f}s", flush=True)
    del raw_dfs

    feat_cols = list(m._BASE_FEAT) + list(m._SPREAD_FEAT)

    # 3) Sweep loop
    results: list[tuple] = []
    for tp, sl in _TP_SLS:
        print(f"\n[3/3] >> tp={tp} sl={sl} ...", flush=True)
        # Rebuild labels for this tp/sl
        m._TP_MULT = tp
        m._SL_MULT = sl
        t1 = time.time()
        pair_dfs: dict[str, pd.DataFrame] = {}
        for pair, df in feat_only.items():
            pair_dfs[pair] = m._add_labels(df, pair)
        print(f"  labels built {time.time()-t1:.1f}s", flush=True)

        # WF folds
        t_min = min(df["timestamp"].min() for df in pair_dfs.values())
        t_max = max(df["timestamp"].max() for df in pair_dfs.values())
        folds = m._generate_folds(t_min, t_max, 365, 90)
        print(f"  {len(folds)} folds", flush=True)

        fold_cache: list[tuple[dict, dict]] = []  # (models, test_mask) per fold

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
            test_mask  = {p: (df["timestamp"]>=te_s)&(df["timestamp"]<te_e)
                          for p, df in pair_dfs.items()}
            t2 = time.time()
            models = m._train_models(pair_dfs, feat_cols, train_mask,
                                     regularize=True, multipair=True, fold_seed=fi)
            fold_cache.append((models, test_mask))
            print(f"    fold {fi}/{len(folds)}  train [{tr_s.date()}->{tr_e.date()}-21bars]  ({time.time()-t2:.1f}s)",
                  flush=True)

        # For each conf_thr: simulate using cached models
        for conf_thr in _CONF_THRS:
            m._CONF_THR = conf_thr
            t3 = time.time()
            all_pnls: list[float] = []
            open_until_ts: dict = {}  # NEW BUG #F: fold 間で持ち越し
            for models, test_mask in fold_cache:
                pnls, open_until_ts = m._simulate(
                    pair_dfs, models, feat_cols, test_mask, multipair=True,
                    open_until_ts=open_until_ts,
                )
                all_pnls.extend(pnls)
            res = m._stats(all_pnls)
            elapsed = time.time() - t3
            results.append((tp, sl, conf_thr, res, elapsed))
            print(f"  conf={conf_thr:.2f}  Sharpe={res['sharpe']:+.4f}  "
                  f"hit={res['hit_pct']:5.1f}%  n={res['n']:6,d}  PnL={res['pnl']:+10.1f}  "
                  f"MaxDD={res['maxdd']:+8.1f}  ({elapsed:.0f}s)", flush=True)

        del pair_dfs, fold_cache

    # ----- Final summary -----
    print("\n" + "="*88, flush=True)
    print("SWEEP RESULTS (Sharpe descending)", flush=True)
    print("="*88, flush=True)
    print(f"  {'tp':>4} {'sl':>4} {'conf':>5}  {'Sharpe':>8}  {'Hit%':>6}  {'N':>7}  {'PnL(pip)':>10}  {'MaxDD':>10}",
          flush=True)
    print("  " + "-"*78, flush=True)
    for tp, sl, conf, res, _ in sorted(results, key=lambda x: -x[3]["sharpe"]):
        print(f"  {tp:4.1f} {sl:4.1f} {conf:5.2f}  {res['sharpe']:+8.4f}  {res['hit_pct']:6.1f}%  "
              f"{res['n']:7,d}  {res['pnl']:+10.1f}  {res['maxdd']:+10.1f}", flush=True)

    # 2D table
    print("\nSharpe matrix (rows=tp/sl, cols=conf_thr):", flush=True)
    print(f"  {'tp/sl':>10}  " + "  ".join(f"{c:>7.2f}" for c in _CONF_THRS), flush=True)
    for tp, sl in _TP_SLS:
        cells = []
        for conf in _CONF_THRS:
            r = next((res for t,s,c,res,_ in results if t==tp and s==sl and c==conf), None)
            cells.append(f"{r['sharpe']:+7.4f}" if r else "    N/A")
        print(f"  {tp:4.1f}/{sl:4.1f}  " + "  ".join(cells), flush=True)


if __name__ == "__main__":
    main()
