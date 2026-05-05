"""stage0_7a_meta_inverted.py — Inversion variants of Meta layer (empirical-fit).

Stage 0.5/0.6 demonstrated that LGBM edge lives in CSI-weak / range-regime zones.
Stage 0.7a tests inverted variants that explicitly target this zone:

  i) F5_inverted_tight       : require |csi_diff| < 0.3 (only trade in CSI-neutral)
  j) F5_inverted_loose       : require |csi_diff| < 0.5
  k) Range_only              : require regime == 'range' (skip trend/high_vol)
  l) F5_inv_tight + Range    : i + k combined

Bases: same 3 as Stage 0.6.
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "scripts")
import compare_prod_ablation as m
import stage0_5_meta_layer_eval as s05  # reuse helpers

sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

_DATA_DIR = Path("data")

_BASES = [
    ("M1_V2_baseline",   1, "730d",  20, None),
    ("M1_chained_best",  1, "730d",  40, {0: 1.2, 1: 1.0, 2: 1.2}),
    ("M15_chained_best",15, "1825d",  3, {0: 1.2, 1: 1.0, 2: 1.2}),
]


def _simulate_inverted(
    pair_dfs: dict[str, pd.DataFrame],
    fold_cache: list[tuple[dict, dict]],
    feat_cols: list[str],
    csi_data: dict[str, pd.DataFrame],
    regime_data: dict[str, pd.Series],
    *,
    variant: str,
) -> list[float]:
    horizon_td = pd.Timedelta(minutes=m._HORIZON * m._BAR_MINUTES)
    open_until_ts: dict = {}
    pnl_list: list[float] = []

    for models, test_mask in fold_cache:
        pair_signals: dict[str, dict] = {}
        for pair, df in pair_dfs.items():
            mask = test_mask.get(pair)
            if mask is None or not mask.any():
                continue
            labeled = df[mask].dropna(subset=[m._LABEL_COLUMN]).copy()
            if labeled.empty:
                continue

            orig_idx = labeled.index.to_numpy()
            te = labeled.reset_index(drop=True)
            te["pair_id"] = m._PAIR_IDX.get(pair, 0)
            mp_feat = feat_cols + ["pair_id"]
            feat = te[mp_feat].values

            pip = m._PIP_SIZE.get(pair, 0.0001)
            ask_full = df["ask_o"].to_numpy() if "ask_o" in df.columns else None
            bid_full = df["bid_o"].to_numpy() if "bid_o" in df.columns else None
            n_full = len(df)
            if ask_full is not None and bid_full is not None:
                spread_entry_arr = np.array([
                    (ask_full[oi+1] - bid_full[oi+1]) / pip if oi + 1 < n_full else np.nan
                    for oi in orig_idx
                ], dtype=float)
            else:
                spread_entry_arr = np.full(len(te), np.nan)

            csi_diff_abs_arr = csi_data[pair]["csi_diff_abs"].iloc[orig_idx].to_numpy()
            regime_arr = regime_data[pair].iloc[orig_idx].to_numpy()

            mp_models = models.get(m._MULTIPAIR_KEY)
            if mp_models is None:
                continue
            p_long, p_short, p_to = m._multi_proba(mp_models["multi"], feat)

            sig = {
                "timestamps":     te["timestamp"].values,
                "labels_long":    te[m._LABEL_LONG].values.astype(float),
                "labels_short":   te[m._LABEL_SHORT].values.astype(float),
                "atrs":           te["atr_14"].values.astype(float),
                "spread_entries": spread_entry_arr,
                "to_long":        te[m._TO_PNL_LONG].values.astype(float),
                "to_short":       te[m._TO_PNL_SHORT].values.astype(float),
                "pip":            pip,
                "p_long":         p_long,
                "p_short":        p_short,
                "p_to":           p_to,
                "csi_diff_abs":   csi_diff_abs_arr,
                "regime":         regime_arr,
            }
            pair_signals[pair] = sig

        bar_data: dict = {}
        for pair, sig in pair_signals.items():
            for i, ts in enumerate(sig["timestamps"]):
                bar_data.setdefault(ts, []).append((pair, i))

        for ts in sorted(bar_data.keys()):
            ts_now = pd.Timestamp(ts)
            candidates = []
            for pair, bar_idx in bar_data[ts]:
                if open_until_ts.get(pair, pd.Timestamp.min) > ts_now:
                    continue
                sig = pair_signals[pair]
                atr = float(sig["atrs"][bar_idx])
                spread_entry = float(sig["spread_entries"][bar_idx])
                l_long = sig["labels_long"][bar_idx]
                l_short = sig["labels_short"][bar_idx]
                if np.isnan(spread_entry) or np.isnan(atr) or atr <= 0.0:
                    continue
                if np.isnan(l_long) or np.isnan(l_short):
                    continue

                csi_diff = float(sig["csi_diff_abs"][bar_idx])
                rg = str(sig["regime"][bar_idx])

                # Apply inverted gates
                if variant == "i_F5_inv_tight":
                    if not np.isfinite(csi_diff) or csi_diff >= 0.3:
                        continue
                elif variant == "j_F5_inv_loose":
                    if not np.isfinite(csi_diff) or csi_diff >= 0.5:
                        continue
                elif variant == "k_Range_only":
                    if rg != "range":
                        continue
                elif variant == "l_F5_inv_tight_plus_Range":
                    if not np.isfinite(csi_diff) or csi_diff >= 0.3:
                        continue
                    if rg != "range":
                        continue

                pip = sig["pip"]
                tp_pip = m._TP_MULT * atr / pip
                sl_pip = m._SL_MULT * atr / pip
                p_long = float(sig["p_long"][bar_idx])
                p_short = float(sig["p_short"][bar_idx])
                p_to = float(sig["p_to"][bar_idx])
                ev_long = p_long * tp_pip - p_short * sl_pip - p_to * spread_entry
                ev_short = p_short * tp_pip - p_long * sl_pip - p_to * spread_entry

                if p_long >= p_short and p_long >= m._CONF_THR and ev_long > 0:
                    direction = "long"; conf = p_long; pnl_label = int(l_long)
                elif p_short > p_long and p_short >= m._CONF_THR and ev_short > 0:
                    direction = "short"; conf = p_short; pnl_label = int(l_short)
                else:
                    continue

                to_pnl = float(sig["to_long"][bar_idx]) if direction == "long" else float(sig["to_short"][bar_idx])
                candidates.append({
                    "pair": pair, "bar_idx": bar_idx, "direction": direction,
                    "conf": conf, "atr": atr, "pip": pip,
                    "pnl_label": pnl_label, "spread_entry": spread_entry,
                    "to_pnl": to_pnl,
                })

            if not candidates:
                continue
            candidates.sort(key=lambda x: -x["conf"])

            used_ccy: set[str] = set()
            picks: list[dict] = []
            for cand in candidates:
                pair = cand["pair"]
                base, quote = pair.split("_")
                if base in used_ccy or quote in used_ccy:
                    continue
                picks.append(cand)
                used_ccy.add(base); used_ccy.add(quote)
                open_until_ts[pair] = ts_now + horizon_td
                if len(picks) >= m._TOP_K:
                    break

            for pick in picks:
                tp_pip = m._TP_MULT * pick["atr"] / pick["pip"]
                sl_pip = m._SL_MULT * pick["atr"] / pick["pip"]
                pl = pick["pnl_label"]
                if pl == 1:
                    pnl_list.append(tp_pip)
                elif pl == -1:
                    pnl_list.append(-sl_pip)
                else:
                    to = pick["to_pnl"]
                    pnl_list.append(to if np.isfinite(to) else -pick["spread_entry"])

    return pnl_list


def _run_base(name: str, base_tf: int, suffix: str, horizon: int,
              cw: dict | None) -> list[tuple]:
    print(f"\n{'#'*80}")
    print(f"# {name}  (TF=M{base_tf}, suffix={suffix}, H={horizon}, cw={cw})")
    print(f"{'#'*80}", flush=True)

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
    pair_dfs = {pair: m._add_labels(df, pair) for pair, df in feat_dfs.items()}
    print(f"  features+labels built ({time.time()-t0:.1f}s)", flush=True)
    del raw_dfs

    t0 = time.time()
    csi_data = s05._compute_csi(feat_dfs)
    print(f"  CSI built ({time.time()-t0:.1f}s)", flush=True)
    t0 = time.time()
    regime_data = s05._compute_regime(feat_dfs)
    print(f"  Regime built ({time.time()-t0:.1f}s)", flush=True)
    del feat_dfs

    feat_cols = m._get_base_feat_for_tf(base_tf) + list(m._SPREAD_FEAT)

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

    variants = ["i_F5_inv_tight", "j_F5_inv_loose", "k_Range_only", "l_F5_inv_tight_plus_Range"]
    results = []
    for v in variants:
        t0 = time.time()
        pnls = _simulate_inverted(
            pair_dfs, fold_cache, feat_cols, csi_data, regime_data, variant=v,
        )
        res = m._stats(pnls)
        elapsed = time.time() - t0
        results.append((name, v, res, elapsed))
        print(f"  {v:30s}  Sharpe={res['sharpe']:+.4f}  hit={res['hit_pct']:5.1f}%  "
              f"n={res['n']:6,d}  PnL={res['pnl']:+9.1f}  ({elapsed:.0f}s)", flush=True)

    return results


def main() -> None:
    print("="*80)
    print("Stage 0.7a - Meta layer INVERSION variants")
    print(f"  Bases: {[b[0] for b in _BASES]}")
    print(f"  Variants: i_F5_inv_tight (csi<0.3), j_F5_inv_loose (csi<0.5),")
    print(f"            k_Range_only, l_F5_inv_tight + Range")
    print("="*80, flush=True)

    all_results = []
    for base_args in _BASES:
        all_results.extend(_run_base(*base_args))

    print("\n\n" + "="*100)
    print("STAGE 0.7a SUMMARY")
    print("="*100)
    print(f"  {'Base':<22}  {'Variant':<28}  {'Sharpe':>8}  {'Hit%':>6}  {'N':>7}  {'PnL(pip)':>10}  {'MaxDD':>10}")
    print("  " + "-"*104)
    for base_name, v_name, res, _ in all_results:
        print(f"  {base_name:<22}  {v_name:<28}  {res['sharpe']:+8.4f}  {res['hit_pct']:6.1f}%  "
              f"{res['n']:7,d}  {res['pnl']:+10.1f}  {res['maxdd']:+10.1f}")
    print("="*100)

    print("\nTOP 5 by Sharpe (vs Stage 0.5/0.6 LGBM-only baselines: M1_V2=-0.189, M1_chained=-0.085, M15_chained=-0.039):")
    for base_name, v_name, res, _ in sorted(all_results, key=lambda x: -x[2]['sharpe'])[:5]:
        print(f"  {base_name:<22}  {v_name:<28}  Sharpe={res['sharpe']:+.4f}  n={res['n']:,d}")


if __name__ == "__main__":
    main()
