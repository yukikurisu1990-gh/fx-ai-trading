"""stage0_8a_multi_tf_regime.py — Add multi-TF regime features (atr_ratio + trend_slope per upper TF).

Captures the case where M1 says trend_up but M15 says range, etc. — TF disagreement
as additional signal for the LGBM model.

For each base TF, compute regime indicators at multiple upper TFs and broadcast to base bars
using shift(1) + reindex(ffill) (causal alignment, same pattern as _add_upper_tf_features).

Per-TF regime features (continuous):
  tf_<period>_atr_ratio   : ATR / ATR.rolling(20).mean()  (vol regime indicator)
  tf_<period>_trend_slope : (EMA[-1] - EMA[-20]) / ATR    (trend strength)

Bases:
  M1 base: upper TFs = [m5, m15, h1]   →  6 features added
  M15 base: upper TFs = [h1, h4, d1]   →  6 features added

Compared to Stage 0.7 best per base.
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "scripts")
import compare_prod_ablation as m
import stage0_7_csi_regime_as_features as s07

sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

_DATA_DIR = Path("data")

# (rule, prefix) per base TF
_MULTI_TF_RULES = {
    1:  [("5min", "tf_m5"),  ("15min", "tf_m15"), ("1h", "tf_h1")],
    15: [("1h", "tf_h1"),    ("4h", "tf_h4"),     ("1D", "tf_d1")],
}

# (name, base_tf, suffix, horizon, cw, extra_feat_groups)
_CASES = [
    ("M1_V2_Regime_full",   1, "730d",  20, None,
        ["regime_cont", "regime_oh"]),
    ("M1_chained_Regime_cont", 1, "730d",  40, {0: 1.2, 1: 1.0, 2: 1.2},
        ["regime_cont"]),
    ("M15_chained_CSI",     15, "1825d",  3, {0: 1.2, 1: 1.0, 2: 1.2},
        ["csi"]),
]


def _compute_multi_tf_regime(pair_dfs: dict[str, pd.DataFrame],
                              upper_tfs: list[tuple[str, str]],
                              ema_period: int = 20, atr_period: int = 14,
                              atr_ma_period: int = 20, slope_lookback: int = 20) -> dict[str, pd.DataFrame]:
    """Per-pair multi-TF regime features (atr_ratio_<tf>, trend_slope_<tf>) aligned to base TF."""
    out: dict[str, pd.DataFrame] = {}
    for pair, df in pair_dfs.items():
        ts_idx = pd.DatetimeIndex(df["timestamp"])
        df_ts = df.set_index(ts_idx)
        cols: dict[str, np.ndarray] = {}

        for rule, prefix in upper_tfs:
            ohlc = (
                df_ts[["open", "high", "low", "close"]]
                .resample(rule)
                .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
                .dropna(how="all")
            )
            h, lo, c = ohlc["high"], ohlc["low"], ohlc["close"]
            pc = c.shift(1)
            tr = pd.concat([h - lo, (h - pc).abs(), (lo - pc).abs()], axis=1).max(axis=1)
            atr = tr.rolling(atr_period, min_periods=atr_period).mean()
            atr_mean = atr.rolling(atr_ma_period, min_periods=atr_ma_period).mean()
            atr_ratio = (atr / atr_mean.replace(0.0, np.nan))
            ema = c.ewm(span=ema_period, adjust=False, min_periods=ema_period).mean()
            slope_raw = ema - ema.shift(slope_lookback)
            trend_slope = (slope_raw / atr.replace(0.0, np.nan))

            # Causal alignment: shift(1) + reindex(ffill) (same pattern as _add_upper_tf_features)
            atr_ratio_aligned = atr_ratio.shift(1).reindex(ts_idx, method="ffill")
            slope_aligned = trend_slope.shift(1).reindex(ts_idx, method="ffill")
            cols[f"{prefix}_atr_ratio"] = atr_ratio_aligned.values
            cols[f"{prefix}_trend_slope"] = slope_aligned.values
        out[pair] = pd.DataFrame(cols, index=df.index)
    return out


def _multi_tf_feat_cols(base_tf: int) -> list[str]:
    rules = _MULTI_TF_RULES[base_tf]
    cols = []
    for _rule, prefix in rules:
        cols += [f"{prefix}_atr_ratio", f"{prefix}_trend_slope"]
    return cols


def _build_feat_cols(base_tf: int, extra_groups: list[str], with_multi_tf: bool) -> list[str]:
    base_cols = m._get_base_feat_for_tf(base_tf) + list(m._SPREAD_FEAT)
    extra: list[str] = []
    if "csi" in extra_groups:
        extra += ["csi_base", "csi_quote", "csi_diff_signed"]
    if "regime_cont" in extra_groups:
        extra += ["atr_ratio", "trend_slope"]
    if "regime_oh" in extra_groups:
        extra += [f"regime_{c}" for c in s07._REGIME_CATS]
    if with_multi_tf:
        extra += _multi_tf_feat_cols(base_tf)
    return base_cols + extra


def _attach_extra(pair_dfs, extra_groups, csi_feats, regime_feats, multi_tf_feats=None):
    if "csi" in extra_groups:
        s07._attach_features(pair_dfs, csi_feats, ["csi_base", "csi_quote", "csi_diff_signed"])
    if "regime_cont" in extra_groups:
        s07._attach_features(pair_dfs, regime_feats, ["atr_ratio", "trend_slope"])
    if "regime_oh" in extra_groups:
        s07._attach_features(pair_dfs, regime_feats,
                              [f"regime_{c}" for c in s07._REGIME_CATS])
    if multi_tf_feats is not None:
        # multi_tf_feats DataFrames have all the columns we need
        sample_cols = list(next(iter(multi_tf_feats.values())).columns)
        s07._attach_features(pair_dfs, multi_tf_feats, sample_cols)


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
    print(f"  CSI + regime base features built", flush=True)

    t0 = time.time()
    multi_tf_feats = _compute_multi_tf_regime(feat_dfs, _MULTI_TF_RULES[base_tf])
    print(f"  Multi-TF regime features built ({time.time()-t0:.1f}s, {2*len(_MULTI_TF_RULES[base_tf])} cols)",
          flush=True)
    del feat_dfs

    results = []
    # a_ref: Stage 0.7 best (no multi-TF regime)
    full_a = _build_feat_cols(base_tf, extra_groups, with_multi_tf=False)
    print(f"\n  >> a_ref ({len(full_a)} feat)", flush=True)
    pair_dfs = {pair: df.copy() for pair, df in pair_dfs_master.items()}
    _attach_extra(pair_dfs, extra_groups, csi_feats, regime_feats)
    t0 = time.time()
    res = _train_and_simulate(pair_dfs, full_a)
    results.append((name, "a_ref", len(full_a), res))
    print(f"  a_ref               feat={len(full_a)}  Sharpe={res['sharpe']:+.4f}  "
          f"hit={res['hit_pct']:5.1f}%  n={res['n']:6,d}  PnL={res['pnl']:+9.1f}  ({time.time()-t0:.0f}s)",
          flush=True)
    del pair_dfs

    # b_with_multi_tf: add multi-TF regime features
    full_b = _build_feat_cols(base_tf, extra_groups, with_multi_tf=True)
    print(f"\n  >> b_multi_tf ({len(full_b)} feat, +{len(full_b)-len(full_a)})", flush=True)
    pair_dfs = {pair: df.copy() for pair, df in pair_dfs_master.items()}
    _attach_extra(pair_dfs, extra_groups, csi_feats, regime_feats, multi_tf_feats)
    t0 = time.time()
    res = _train_and_simulate(pair_dfs, full_b)
    results.append((name, "b_multi_tf", len(full_b), res))
    print(f"  b_multi_tf          feat={len(full_b)}  Sharpe={res['sharpe']:+.4f}  "
          f"hit={res['hit_pct']:5.1f}%  n={res['n']:6,d}  PnL={res['pnl']:+9.1f}  ({time.time()-t0:.0f}s)",
          flush=True)
    del pair_dfs

    return results


def main() -> None:
    print("="*80)
    print("Stage 0.8a - Multi-TF regime features")
    print(f"  M1 base upper TFs:  m5, m15, h1   (6 features)")
    print(f"  M15 base upper TFs: h1, h4, d1     (6 features)")
    print(f"  Bases: {[c[0] for c in _CASES]}")
    print("="*80, flush=True)

    all_results = []
    for case_args in _CASES:
        all_results.extend(_run_case(*case_args))

    print("\n\n" + "="*100)
    print("STAGE 0.8a SUMMARY")
    print("="*100)
    print(f"  {'Case':<28}  {'Variant':<14}  {'Feat':>4}  {'Sharpe':>8}  {'Hit%':>6}  {'N':>7}  {'PnL':>10}")
    print("  " + "-"*92)
    for name, v, n_feat, res in all_results:
        print(f"  {name:<28}  {v:<14}  {n_feat:>4d}  {res['sharpe']:+8.4f}  "
              f"{res['hit_pct']:6.1f}%  {res['n']:7,d}  {res['pnl']:+10.1f}")
    print("="*100)


if __name__ == "__main__":
    main()
