"""stage0_6_meta_layer_improved.py — Improved Meta layer variants (directional CSI/regime).

Stage 0.5 evaluated production-default Meta layer (binary F5 + non-directional regime).
Stage 0.6 tests improved variants that exploit directional information:

  e) F5_directional           : long only if csi_base > csi_quote + 0.5
                                short only if csi_quote > csi_base + 0.5
  f) Regime_directional       : trend_up → ev_long×1.2 / ev_short×0.8
                                trend_down → ev_long×0.8 / ev_short×1.2
                                high_vol → both×0.5
                                range → 1.0
  g) F5_dir + Regime_dir      : e + f combined
  h) CSI_continuous_signed    : ev_long *= (1 + clip(csi_diff_signed, -2, 2) * 0.3)
                                ev_short *= (1 - clip(csi_diff_signed, -2, 2) * 0.3)
                                CSI is connected to direction continuously, no gate

Bases: same 4 as Stage 0.5. 16 cells total.
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "scripts")
import compare_prod_ablation as m
import stage0_5_meta_layer_eval as s05  # reuse _compute_csi / _compute_regime

sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

_DATA_DIR = Path("data")
_CSI_MIN_DIFF = 0.5
_CSI_CONT_SCALE = 0.3
_CSI_CONT_CLIP = 2.0

_REGIME_DIR_WEIGHTS = {
    # regime -> (long_weight, short_weight)
    "trend_up":   (1.2, 0.8),
    "trend_down": (0.8, 1.2),
    "high_vol":   (0.5, 0.5),
    "range":      (1.0, 1.0),
}


_BASES = [
    ("M1_V2_baseline",   1, "730d",  20, None),
    ("M1_chained_best",  1, "730d",  40, {0: 1.2, 1: 1.0, 2: 1.2}),
    ("M15_chained_best",15, "1825d",  3, {0: 1.2, 1: 1.0, 2: 1.2}),
]


def _compute_csi_signed(pair_dfs: dict[str, pd.DataFrame],
                        lookback: int = s05._CSI_LOOKBACK) -> dict[str, pd.DataFrame]:
    """Return per-pair csi data INCLUDING signed csi_diff.

    csi_diff_signed = csi_base - csi_quote (positive favors long; negative favors short).
    """
    return_by_pair: dict[str, pd.Series] = {}
    for pair, df in pair_dfs.items():
        ret = df.set_index("timestamp")["close"].pct_change(lookback)
        return_by_pair[pair] = ret

    return_df = pd.DataFrame(return_by_pair).sort_index()

    strength_df = pd.DataFrame(index=return_df.index, columns=s05._ALL_CURRENCIES, dtype=float)
    for ccy in s05._ALL_CURRENCIES:
        base_cols = [p for p in return_df.columns if p.split("_")[0] == ccy]
        quote_cols = [p for p in return_df.columns if p.split("_")[1] == ccy]
        base_avg = return_df[base_cols].mean(axis=1) if base_cols else pd.Series(0.0, index=return_df.index)
        quote_avg = return_df[quote_cols].mean(axis=1) if quote_cols else pd.Series(0.0, index=return_df.index)
        strength_df[ccy] = base_avg - quote_avg

    mu = strength_df.mean(axis=1)
    sigma = strength_df.std(axis=1, ddof=0).replace(0.0, np.nan)
    csi_df = strength_df.sub(mu, axis=0).div(sigma, axis=0).fillna(0.0)

    out: dict[str, pd.DataFrame] = {}
    for pair, df in pair_dfs.items():
        base, quote = pair.split("_")
        # tz-aware reindex: must use Series/DatetimeIndex, not .values
        ts = pd.DatetimeIndex(df["timestamp"])
        csi_base = csi_df[base].reindex(ts).values
        csi_quote = csi_df[quote].reindex(ts).values
        out[pair] = pd.DataFrame({
            "csi_base":   csi_base,
            "csi_quote":  csi_quote,
            "csi_diff_signed": csi_base - csi_quote,  # positive favors long
        })
    return out


def _simulate_with_meta_improved(
    pair_dfs: dict[str, pd.DataFrame],
    fold_cache: list[tuple[dict, dict]],
    feat_cols: list[str],
    csi_data: dict[str, pd.DataFrame],
    regime_data: dict[str, pd.Series],
    *,
    variant: str,  # "e_F5_dir", "f_Regime_dir", "g_F5_dir_Regime_dir", "h_CSI_continuous"
) -> list[float]:
    is_mp = True
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

            csi_signed_arr = csi_data[pair]["csi_diff_signed"].iloc[orig_idx].to_numpy()
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
                "csi_signed":     csi_signed_arr,
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

                csi_signed = float(sig["csi_signed"][bar_idx])
                rg = str(sig["regime"][bar_idx])

                pip = sig["pip"]
                tp_pip = m._TP_MULT * atr / pip
                sl_pip = m._SL_MULT * atr / pip
                p_long = float(sig["p_long"][bar_idx])
                p_short = float(sig["p_short"][bar_idx])
                p_to = float(sig["p_to"][bar_idx])

                # Compute multipliers based on variant
                w_long = 1.0
                w_short = 1.0
                allow_long = True
                allow_short = True

                if variant in ("e_F5_dir", "g_F5_dir_Regime_dir"):
                    # Directional CSI gate
                    if not np.isfinite(csi_signed):
                        continue  # CSI unknown: skip
                    allow_long = csi_signed >= _CSI_MIN_DIFF
                    allow_short = csi_signed <= -_CSI_MIN_DIFF

                if variant in ("f_Regime_dir", "g_F5_dir_Regime_dir"):
                    # Directional regime weighting
                    wl, ws = _REGIME_DIR_WEIGHTS.get(rg, (1.0, 1.0))
                    w_long *= wl
                    w_short *= ws

                if variant == "h_CSI_continuous":
                    # Continuous signed CSI scaling
                    if not np.isfinite(csi_signed):
                        cs = 0.0
                    else:
                        cs = float(np.clip(csi_signed, -_CSI_CONT_CLIP, _CSI_CONT_CLIP))
                    w_long *= (1.0 + cs * _CSI_CONT_SCALE)
                    w_short *= (1.0 - cs * _CSI_CONT_SCALE)

                ev_long = w_long * (p_long * tp_pip - p_short * sl_pip - p_to * spread_entry)
                ev_short = w_short * (p_short * tp_pip - p_long * sl_pip - p_to * spread_entry)

                direction = None
                if allow_long and p_long >= p_short and p_long >= m._CONF_THR and ev_long > 0:
                    direction = "long"; conf = p_long; pnl_label = int(l_long)
                elif allow_short and p_short > p_long and p_short >= m._CONF_THR and ev_short > 0:
                    direction = "short"; conf = p_short; pnl_label = int(l_short)
                if direction is None:
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
    csi_data = _compute_csi_signed(feat_dfs)
    print(f"  CSI (signed) built ({time.time()-t0:.1f}s)", flush=True)
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

    variants = ["e_F5_dir", "f_Regime_dir", "g_F5_dir_Regime_dir", "h_CSI_continuous"]
    results = []
    for v in variants:
        t0 = time.time()
        pnls = _simulate_with_meta_improved(
            pair_dfs, fold_cache, feat_cols, csi_data, regime_data, variant=v,
        )
        res = m._stats(pnls)
        elapsed = time.time() - t0
        results.append((name, v, res, elapsed))
        print(f"  {v:25s}  Sharpe={res['sharpe']:+.4f}  hit={res['hit_pct']:5.1f}%  "
              f"n={res['n']:6,d}  PnL={res['pnl']:+9.1f}  ({elapsed:.0f}s)", flush=True)

    return results


def main() -> None:
    print("="*80)
    print("Stage 0.6 - Improved Meta layer (directional CSI / regime)")
    print(f"  Bases: {[b[0] for b in _BASES]}")
    print(f"  Variants: e_F5_dir, f_Regime_dir, g_F5_dir_Regime_dir, h_CSI_continuous")
    print("="*80, flush=True)

    all_results = []
    for base_args in _BASES:
        all_results.extend(_run_base(*base_args))

    print("\n\n" + "="*100)
    print("STAGE 0.6 SUMMARY (16 cells)")
    print("="*100)
    print(f"  {'Base':<22}  {'Variant':<22}  {'Sharpe':>8}  {'Hit%':>6}  {'N':>7}  {'PnL(pip)':>10}  {'MaxDD':>10}")
    print("  " + "-"*94)
    for base_name, v_name, res, _ in all_results:
        print(f"  {base_name:<22}  {v_name:<22}  {res['sharpe']:+8.4f}  {res['hit_pct']:6.1f}%  "
              f"{res['n']:7,d}  {res['pnl']:+10.1f}  {res['maxdd']:+10.1f}")
    print("="*100)

    print("\nTOP 5 cells by Sharpe:")
    for base_name, v_name, res, _ in sorted(all_results, key=lambda x: -x[2]['sharpe'])[:5]:
        print(f"  {base_name:<22}  {v_name:<22}  Sharpe={res['sharpe']:+.4f}  n={res['n']:,d}")


if __name__ == "__main__":
    main()
