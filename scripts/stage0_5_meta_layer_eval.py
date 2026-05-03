"""stage0_5_meta_layer_eval.py — Independent evaluation of CSI (F5) and Regime layers.

Compares 4 base configs × 4 Meta variants = 16 cells.

Bases:
  M1_V2_baseline      : tp=1.5/sl=1.0/conf=0.40/H=20, no class_weight
  M1_chained_best     : + small_boost {1.2/1.0/1.2}, H=40
  M15_V2_baseline     : same as M1 V2 but base TF M15 1825d
  M15_chained_best    : + small_boost, H=3

Meta variants per base:
  a) LGBM only         : current baseline
  b) +F5 CSI filter    : reject if |csi[base] - csi[quote]| < 0.5
  c) +Regime weighting : ev_long/short *= regime_weight (trend 1.2 / range 1.0 / high_vol 0.5)
  d) +F5 +Regime       : production stack

CSI: 20-bar return × 20 pairs cross-section → per-currency strength → z-score
Regime: 14-bar EMA-ATR + 20-bar EMA slope, priority high_vol > trend_up > trend_down > range
"""
from __future__ import annotations
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "scripts")
import compare_prod_ablation as m

sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

_DATA_DIR = Path("data")
_ALL_CURRENCIES = ["AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD"]
_CSI_LOOKBACK = 20
_CSI_MIN_DIFF = 0.5
_REGIME_ATR_RATIO_THRESHOLD = 2.0
_REGIME_SLOPE_THRESHOLD = 0.3
_REGIME_WEIGHTS = {"trend_up": 1.2, "trend_down": 1.2, "range": 1.0, "high_vol": 0.5}


# Base configs to evaluate
_BASES = [
    # (name, base_tf, suffix, horizon, class_weight)
    ("M1_V2_baseline",   1, "730d",  20, None),
    ("M1_chained_best",  1, "730d",  40, {0: 1.2, 1: 1.0, 2: 1.2}),
    ("M15_chained_best",15, "1825d",  3, {0: 1.2, 1: 1.0, 2: 1.2}),
]


def _compute_csi(pair_dfs: dict[str, pd.DataFrame], lookback: int = _CSI_LOOKBACK) -> dict[str, pd.DataFrame]:
    """Compute per-bar CSI z-score for each currency.

    Returns: dict pair -> DataFrame with columns 'csi_base', 'csi_quote', 'csi_diff_abs'
             aligned to pair_dfs[pair]['timestamp'].
    """
    # Step A: build per-pair return at lookback bars (indexed by timestamp)
    return_by_pair: dict[str, pd.Series] = {}
    for pair, df in pair_dfs.items():
        ret = df.set_index("timestamp")["close"].pct_change(lookback)
        return_by_pair[pair] = ret

    # Step B: align all returns into a single DataFrame (rows=timestamps, cols=pairs)
    return_df = pd.DataFrame(return_by_pair).sort_index()

    # Step C: compute per-currency strength from cross-section
    strength_df = pd.DataFrame(index=return_df.index, columns=_ALL_CURRENCIES, dtype=float)
    for ccy in _ALL_CURRENCIES:
        base_cols = [p for p in return_df.columns if p.split("_")[0] == ccy]
        quote_cols = [p for p in return_df.columns if p.split("_")[1] == ccy]
        base_avg = return_df[base_cols].mean(axis=1) if base_cols else pd.Series(0.0, index=return_df.index)
        quote_avg = return_df[quote_cols].mean(axis=1) if quote_cols else pd.Series(0.0, index=return_df.index)
        strength_df[ccy] = base_avg - quote_avg

    # Step D: z-score normalize per row across currencies
    mu = strength_df.mean(axis=1)
    sigma = strength_df.std(axis=1, ddof=0).replace(0.0, np.nan)
    csi_df = strength_df.sub(mu, axis=0).div(sigma, axis=0).fillna(0.0)

    # Step E: per-pair csi_diff
    out: dict[str, pd.DataFrame] = {}
    for pair, df in pair_dfs.items():
        base, quote = pair.split("_")
        # NOTE: must use the Series itself (tz-aware) not .values (tz-stripped) for reindex
        ts = pd.DatetimeIndex(df["timestamp"])
        csi_base = csi_df[base].reindex(ts).values
        csi_quote = csi_df[quote].reindex(ts).values
        out[pair] = pd.DataFrame({
            "csi_base": csi_base,
            "csi_quote": csi_quote,
            "csi_diff_abs": np.abs(csi_base - csi_quote),
        })
    return out


def _compute_regime(pair_dfs: dict[str, pd.DataFrame],
                    atr_period: int = 14, ema_period: int = 20,
                    atr_ma_period: int = 20, slope_lookback: int = 20) -> dict[str, pd.Series]:
    """Compute per-bar regime label per pair.

    Returns: dict pair -> Series of strings ('high_vol', 'trend_up', 'trend_down', 'range')
             aligned to pair_dfs[pair].index.
    """
    out: dict[str, pd.Series] = {}
    for pair, df in pair_dfs.items():
        # atr_14 already exists in pair_dfs (built by _add_base_features)
        atr = df["atr_14"]
        atr_mean = atr.rolling(atr_ma_period, min_periods=atr_ma_period).mean()
        atr_ratio = atr / atr_mean.replace(0.0, np.nan)

        close = df["close"]
        ema = close.ewm(span=ema_period, adjust=False, min_periods=ema_period).mean()
        slope_raw = ema - ema.shift(slope_lookback)
        trend_slope = slope_raw / atr.replace(0.0, np.nan)

        regime = pd.Series("range", index=df.index, dtype=object)
        regime[(atr_ratio > _REGIME_ATR_RATIO_THRESHOLD).fillna(False)] = "high_vol"
        # Trend overrides only when not high_vol
        normal = (atr_ratio <= _REGIME_ATR_RATIO_THRESHOLD).fillna(False)
        regime[normal & (trend_slope > _REGIME_SLOPE_THRESHOLD).fillna(False)] = "trend_up"
        regime[normal & (trend_slope < -_REGIME_SLOPE_THRESHOLD).fillna(False)] = "trend_down"

        out[pair] = regime
    return out


def _simulate_with_meta(
    pair_dfs: dict[str, pd.DataFrame],
    fold_cache: list[tuple[dict, dict]],   # list of (models, test_mask) per fold
    feat_cols: list[str],
    csi_data: dict[str, pd.DataFrame],
    regime_data: dict[str, pd.Series],
    *,
    apply_csi: bool,
    apply_regime: bool,
) -> list[float]:
    """Simulation that respects current m._TP_MULT/_SL_MULT/_HORIZON/_CONF_THR/_TOP_K.

    apply_csi: if True, gate by F5 (|csi_diff| >= 0.5).
    apply_regime: if True, weight ev_long/ev_short by regime_weight.
    """
    is_mp = True  # all bases use multipair
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

            # Pull CSI/regime aligned to orig_idx
            csi_diff_arr = csi_data[pair]["csi_diff_abs"].iloc[orig_idx].to_numpy()
            regime_arr = regime_data[pair].iloc[orig_idx].to_numpy()

            # Predict
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
                "csi_diff":       csi_diff_arr,
                "regime":         regime_arr,
            }
            pair_signals[pair] = sig

        # Group by timestamp
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

                # Meta gate F5
                if apply_csi:
                    cd = float(sig["csi_diff"][bar_idx])
                    if not np.isfinite(cd) or cd < _CSI_MIN_DIFF:
                        continue

                # Regime weighting
                rw = 1.0
                if apply_regime:
                    rg = sig["regime"][bar_idx]
                    rw = _REGIME_WEIGHTS.get(str(rg), 1.0)

                pip = sig["pip"]
                tp_pip = m._TP_MULT * atr / pip
                sl_pip = m._SL_MULT * atr / pip

                p_long = float(sig["p_long"][bar_idx])
                p_short = float(sig["p_short"][bar_idx])
                p_to = float(sig["p_to"][bar_idx])
                ev_long = (p_long * tp_pip - p_short * sl_pip - p_to * spread_entry) * rw
                ev_short = (p_short * tp_pip - p_long * sl_pip - p_to * spread_entry) * rw

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
    """Train models once, then simulate 4 Meta variants. Returns list of (variant, stats)."""
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

    # Load
    raw_dfs = {}
    for pair in m._ALL_PAIRS:
        p = _DATA_DIR / f"candles_{pair}_M{base_tf}_{suffix}_BA.jsonl"
        if not p.exists():
            continue
        raw_dfs[pair] = m._load_ba_candles(p)
    print(f"  loaded {len(raw_dfs)} pairs", flush=True)

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
    print(f"  features+labels built ({time.time()-t0:.1f}s)", flush=True)
    del raw_dfs

    # CSI / Regime computation (once)
    t0 = time.time()
    csi_data = _compute_csi(feat_dfs)  # use feat_dfs (no labels yet) for CSI to avoid label_col impact
    print(f"  CSI built ({time.time()-t0:.1f}s)", flush=True)
    t0 = time.time()
    regime_data = _compute_regime(feat_dfs)
    print(f"  Regime built ({time.time()-t0:.1f}s)", flush=True)
    del feat_dfs

    feat_cols = m._get_base_feat_for_tf(base_tf) + list(m._SPREAD_FEAT)

    # Folds
    t_min = min(df["timestamp"].min() for df in pair_dfs.values())
    t_max = max(df["timestamp"].max() for df in pair_dfs.values())
    folds = m._generate_folds(t_min, t_max, 365, 90)
    print(f"  {len(folds)} folds", flush=True)

    # Train all folds
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

    # 4 Meta variants
    variants = [
        ("a_LGBM_only",          False, False),
        ("b_F5_only",            True,  False),
        ("c_Regime_only",        False, True),
        ("d_F5_plus_Regime",     True,  True),
    ]
    results = []
    for v_name, csi_on, reg_on in variants:
        t0 = time.time()
        pnls = _simulate_with_meta(
            pair_dfs, fold_cache, feat_cols, csi_data, regime_data,
            apply_csi=csi_on, apply_regime=reg_on,
        )
        res = m._stats(pnls)
        elapsed = time.time() - t0
        results.append((name, v_name, res, elapsed))
        print(f"  {v_name:25s}  Sharpe={res['sharpe']:+.4f}  hit={res['hit_pct']:5.1f}%  "
              f"n={res['n']:6,d}  PnL={res['pnl']:+9.1f}  ({elapsed:.0f}s)", flush=True)

    return results


def main() -> None:
    print("="*80)
    print("Stage 0.5 - Meta layer (CSI F5 + Regime weighting) independent eval")
    print(f"  Bases: {[b[0] for b in _BASES]}")
    print("="*80, flush=True)

    all_results = []
    for base_args in _BASES:
        base_results = _run_base(*base_args)
        all_results.extend(base_results)

    print("\n\n" + "="*100)
    print("STAGE 0.5 SUMMARY (16 cells)")
    print("="*100)
    print(f"  {'Base':<22}  {'Variant':<22}  {'Sharpe':>8}  {'Hit%':>6}  {'N':>7}  {'PnL(pip)':>10}  {'MaxDD':>10}")
    print("  " + "-"*94)
    # Sort by base, then variant
    for base_name, v_name, res, _ in all_results:
        print(f"  {base_name:<22}  {v_name:<22}  {res['sharpe']:+8.4f}  {res['hit_pct']:6.1f}%  "
              f"{res['n']:7,d}  {res['pnl']:+10.1f}  {res['maxdd']:+10.1f}")
    print("="*100)

    # Top 5 by Sharpe
    print("\nTOP 5 cells by Sharpe:")
    for base_name, v_name, res, _ in sorted(all_results, key=lambda x: -x[2]['sharpe'])[:5]:
        print(f"  {base_name:<22}  {v_name:<22}  Sharpe={res['sharpe']:+.4f}  n={res['n']:,d}")


if __name__ == "__main__":
    main()
