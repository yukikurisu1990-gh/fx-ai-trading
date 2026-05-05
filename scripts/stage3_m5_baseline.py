"""stage3_m5_baseline.py — M5 base TF, V2 + Stage 2 chained best.

M5 base means _BAR_MINUTES=5. HORIZON=8 ≈ M1 H=40 (clock-time equivalent).
Compare 3 cells: V2 baseline, +small_boost, +small_boost+H=8.
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, "scripts")
import compare_prod_ablation as m

sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

_DATA_DIR = Path("data")

# M5 base
m._BAR_MINUTES = 5
m._TRAINING_MODE = "multi"
m._EV_SL_FACTOR = 1.0
m._TP_MULT = 1.5
m._SL_MULT = 1.0
m._CONF_THR = 0.40
m._TOP_K = 3

# Cells: (name, horizon, class_weight)
_CELLS = [
    ("V2_baseline_M5",     20, None),                              # H=20 = 100 min, no cw
    ("small_boost_M5",     20, {0: 1.2, 1: 1.0, 2: 1.2}),          # H=20, small_boost
    ("small_boost_H8_M5",   8, {0: 1.2, 1: 1.0, 2: 1.2}),          # H=8 = 40 min, small_boost
    ("small_boost_H40_M5", 40, {0: 1.2, 1: 1.0, 2: 1.2}),          # H=40 = 200 min, small_boost
]


def main() -> None:
    print("="*80)
    print("Stage 3.1 - M5 base TF (1095d) chained-best comparison")
    print(f"  _BAR_MINUTES={m._BAR_MINUTES}  tp={m._TP_MULT}  sl={m._SL_MULT}  conf={m._CONF_THR}")
    print("="*80, flush=True)

    raw_dfs = {}
    for pair in m._ALL_PAIRS:
        p = _DATA_DIR / f"candles_{pair}_M5_1095d_BA.jsonl"
        if not p.exists():
            print(f"  SKIP {pair}: not found")
            continue
        raw_dfs[pair] = m._load_ba_candles(p)
    print(f"\n[1/3] loaded {len(raw_dfs)} pairs", flush=True)

    feat_only = {}
    for pair, df in raw_dfs.items():
        pip = m._PIP_SIZE.get(pair, 0.0001)
        df = m._add_base_features(df)
        df = m._add_upper_tf_features(df)
        df = m._add_mtf_features(df)
        df = m._add_spread_features(df, pip)
        feat_only[pair] = df
    print(f"[2/3] features built", flush=True)
    del raw_dfs

    feat_cols = m._get_base_feat_for_tf(5) + list(m._SPREAD_FEAT)
    print(f"  feat_cols n={len(feat_cols)}", flush=True)

    results = []
    for cell_name, horizon, cw in _CELLS:
        print(f"\n[3/3] >> {cell_name} (H={horizon}, cw={cw})", flush=True)
        m._HORIZON = horizon
        if cw is None:
            m._USE_CLASS_WEIGHT = False
            m._CUSTOM_CLASS_WEIGHT = None
        else:
            m._USE_CLASS_WEIGHT = True
            m._CUSTOM_CLASS_WEIGHT = cw

        # Re-label per cell (HORIZON varies)
        t1 = time.time()
        pair_dfs = {pair: m._add_labels(df, pair) for pair, df in feat_only.items()}
        print(f"  labels built {time.time()-t1:.1f}s", flush=True)

        t_min = min(df["timestamp"].min() for df in pair_dfs.values())
        t_max = max(df["timestamp"].max() for df in pair_dfs.values())
        # M5 1095d => use 365 train / 90 test (still in days; same as M1)
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
        res = m._stats(all_pnls)
        elapsed = time.time() - t0
        results.append((cell_name, horizon, cw, res, elapsed))
        print(f"  {cell_name}  Sharpe={res['sharpe']:+.4f}  hit={res['hit_pct']:5.1f}%  "
              f"n={res['n']:6,d}  PnL={res['pnl']:+9.1f}  ({elapsed:.0f}s)", flush=True)
        del pair_dfs

    print("\n" + "="*80)
    print("Stage 3.1 RESULTS (M5 1095d)")
    print("="*80)
    print(f"  {'Cell':<22}  {'H':>3}  {'Sharpe':>8}  {'Hit%':>6}  {'N':>7}  {'PnL(pip)':>10}  {'MaxDD':>10}")
    print("  " + "-"*88)
    for cell, horizon, _cw, res, _ in sorted(results, key=lambda x: -x[3]['sharpe']):
        print(f"  {cell:<22}  {horizon:3d}  {res['sharpe']:+8.4f}  {res['hit_pct']:6.1f}%  "
              f"{res['n']:7,d}  {res['pnl']:+10.1f}  {res['maxdd']:+10.1f}")
    print("="*80)


if __name__ == "__main__":
    main()
