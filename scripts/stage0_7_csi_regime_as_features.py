"""stage0_7_csi_regime_as_features.py — CSI/Regime as INPUT FEATURES (not filter/weight).

Following Stage 0.5 finding that Meta layer as filter/weight is structurally limited,
this stage tests integrating CSI/Regime info INTO the LGBM model itself as input features.
The model decides how to use them; no post-hoc filter/weight applied.

Variants per base config:
  a) baseline (47 features, no CSI/regime added)
  b) +CSI       : add csi_diff_signed, csi_base, csi_quote          (50 features)
  c) +Regime    : add atr_ratio, trend_slope                         (49 features)
  d) +Regime+oh : add atr_ratio, trend_slope, regime_one_hot (4)     (53 features)
  e) +ALL       : c + b combined                                     (56 features)

Bases: M1_V2_baseline, M1_chained_best, M15_chained_best.

Note: This re-evaluates Phase 9.16 verdict ("CSI as features → REJECT") on
clean pipeline + tz-fixed CSI computation + multipair LGBM.
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "scripts")
import compare_prod_ablation as m
import stage0_5_meta_layer_eval as s05  # reuse _compute_csi & _compute_regime

sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

_DATA_DIR = Path("data")

_BASES = [
    ("M1_V2_baseline",   1, "730d",  20, None),
    ("M1_chained_best",  1, "730d",  40, {0: 1.2, 1: 1.0, 2: 1.2}),
    ("M15_chained_best",15, "1825d",  3, {0: 1.2, 1: 1.0, 2: 1.2}),
]

_REGIME_CATS = ["range", "trend_up", "trend_down", "high_vol"]


def _compute_csi_signed_features(pair_dfs: dict[str, pd.DataFrame],
                                  lookback: int = s05._CSI_LOOKBACK) -> dict[str, pd.DataFrame]:
    """Per-pair csi feature columns: csi_diff_signed, csi_base, csi_quote."""
    return_by_pair = {}
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

    out = {}
    for pair, df in pair_dfs.items():
        base, quote = pair.split("_")
        ts = pd.DatetimeIndex(df["timestamp"])  # tz-aware
        csi_base = csi_df[base].reindex(ts).values
        csi_quote = csi_df[quote].reindex(ts).values
        out[pair] = pd.DataFrame({
            "csi_base":         csi_base,
            "csi_quote":        csi_quote,
            "csi_diff_signed":  csi_base - csi_quote,
        }, index=df.index)
    return out


def _compute_regime_features(pair_dfs: dict[str, pd.DataFrame],
                             atr_period: int = 14, ema_period: int = 20,
                             atr_ma_period: int = 20, slope_lookback: int = 20) -> dict[str, pd.DataFrame]:
    """Per-pair regime feature columns: atr_ratio, trend_slope, regime_one_hot (4)."""
    out = {}
    for pair, df in pair_dfs.items():
        atr = df["atr_14"]
        atr_mean = atr.rolling(atr_ma_period, min_periods=atr_ma_period).mean()
        atr_ratio = (atr / atr_mean.replace(0.0, np.nan)).values

        close = df["close"]
        ema = close.ewm(span=ema_period, adjust=False, min_periods=ema_period).mean()
        slope_raw = ema - ema.shift(slope_lookback)
        trend_slope = (slope_raw / atr.replace(0.0, np.nan)).values

        # regime classification (priority: high_vol > trend_up > trend_down > range)
        regime = np.full(len(df), "range", dtype=object)
        with np.errstate(invalid="ignore"):
            high_vol_mask = (atr_ratio > 2.0)
            trend_up_mask = (~high_vol_mask) & (trend_slope > 0.3)
            trend_down_mask = (~high_vol_mask) & (trend_slope < -0.3)
        regime[high_vol_mask & ~np.isnan(atr_ratio)] = "high_vol"
        regime[trend_up_mask & ~np.isnan(trend_slope)] = "trend_up"
        regime[trend_down_mask & ~np.isnan(trend_slope)] = "trend_down"

        cols = {
            "atr_ratio":        atr_ratio,
            "trend_slope":      trend_slope,
        }
        for cat in _REGIME_CATS:
            cols[f"regime_{cat}"] = (regime == cat).astype(float)
        out[pair] = pd.DataFrame(cols, index=df.index)
    return out


def _attach_features(pair_dfs: dict[str, pd.DataFrame],
                     extra: dict[str, pd.DataFrame],
                     cols: list[str]) -> None:
    """In-place attach selected columns from `extra` into pair_dfs."""
    for pair, df in pair_dfs.items():
        ex = extra[pair]
        for c in cols:
            df[c] = ex[c].values


def _train_and_simulate(pair_dfs: dict[str, pd.DataFrame],
                        feat_cols: list[str]) -> dict:
    """Run WF training+sim and return stats."""
    t_min = min(df["timestamp"].min() for df in pair_dfs.values())
    t_max = max(df["timestamp"].max() for df in pair_dfs.values())
    folds = m._generate_folds(t_min, t_max, 365, 90)

    open_until_ts: dict = {}
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
    pair_dfs_master = {pair: m._add_labels(df, pair) for pair, df in feat_dfs.items()}
    print(f"  features+labels built ({time.time()-t0:.1f}s)", flush=True)
    del raw_dfs

    t0 = time.time()
    csi_feats = _compute_csi_signed_features(feat_dfs)
    print(f"  CSI features built ({time.time()-t0:.1f}s)", flush=True)
    t0 = time.time()
    regime_feats = _compute_regime_features(feat_dfs)
    print(f"  Regime features built ({time.time()-t0:.1f}s)", flush=True)
    del feat_dfs

    base_feat_cols = m._get_base_feat_for_tf(base_tf) + list(m._SPREAD_FEAT)
    csi_cols = ["csi_base", "csi_quote", "csi_diff_signed"]
    regime_cont_cols = ["atr_ratio", "trend_slope"]
    regime_oh_cols = [f"regime_{c}" for c in _REGIME_CATS]

    variants = [
        ("a_baseline",         []),
        ("b_plus_CSI",         csi_cols),
        ("c_plus_Regime_cont", regime_cont_cols),
        ("d_plus_Regime_full", regime_cont_cols + regime_oh_cols),
        ("e_ALL",              csi_cols + regime_cont_cols + regime_oh_cols),
    ]

    results = []
    for v_name, extra_cols in variants:
        print(f"\n  >> {v_name} (n_extra={len(extra_cols)})", flush=True)
        # Reset pair_dfs from master copy and attach extra cols if any
        pair_dfs = {pair: df.copy() for pair, df in pair_dfs_master.items()}
        if any(c.startswith("csi_") for c in extra_cols):
            _attach_features(pair_dfs, csi_feats,
                             [c for c in extra_cols if c.startswith("csi_")])
        non_csi = [c for c in extra_cols if not c.startswith("csi_")]
        if non_csi:
            _attach_features(pair_dfs, regime_feats, non_csi)
        feat_cols = base_feat_cols + extra_cols
        print(f"    {len(feat_cols)} features", flush=True)

        t0 = time.time()
        res = _train_and_simulate(pair_dfs, feat_cols)
        elapsed = time.time() - t0
        results.append((name, v_name, len(feat_cols), res, elapsed))
        print(f"  {v_name:25s}  feat={len(feat_cols)}  Sharpe={res['sharpe']:+.4f}  "
              f"hit={res['hit_pct']:5.1f}%  n={res['n']:6,d}  PnL={res['pnl']:+9.1f}  ({elapsed:.0f}s)",
              flush=True)
        del pair_dfs

    return results


def main() -> None:
    print("="*80)
    print("Stage 0.7 - CSI / Regime as INPUT FEATURES (re-eval Phase 9.16 verdict)")
    print(f"  Bases: {[b[0] for b in _BASES]}")
    print(f"  Variants: a_baseline, b_+CSI, c_+Regime_cont, d_+Regime_full, e_ALL")
    print("="*80, flush=True)

    all_results = []
    for base_args in _BASES:
        all_results.extend(_run_base(*base_args))

    print("\n\n" + "="*100)
    print("STAGE 0.7 SUMMARY")
    print("="*100)
    print(f"  {'Base':<22}  {'Variant':<22}  {'Feat':>4}  {'Sharpe':>8}  {'Hit%':>6}  {'N':>7}  {'PnL(pip)':>10}")
    print("  " + "-"*90)
    for base_name, v_name, n_feat, res, _ in all_results:
        print(f"  {base_name:<22}  {v_name:<22}  {n_feat:>4d}  {res['sharpe']:+8.4f}  "
              f"{res['hit_pct']:6.1f}%  {res['n']:7,d}  {res['pnl']:+10.1f}")
    print("="*100)

    print("\nTOP 5 by Sharpe (vs baselines: M1_V2=-0.189, M1_chained=-0.085, M15_chained=-0.039):")
    for base_name, v_name, n_feat, res, _ in sorted(all_results, key=lambda x: -x[3]['sharpe'])[:5]:
        print(f"  {base_name:<22}  {v_name:<22}  feat={n_feat}  Sharpe={res['sharpe']:+.4f}  n={res['n']:,d}")


if __name__ == "__main__":
    main()
