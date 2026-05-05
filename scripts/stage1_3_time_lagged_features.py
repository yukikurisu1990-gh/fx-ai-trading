"""stage1_3_time_lagged_features.py — Add time + lagged-return features.

Stage 1.2 confirmed cleanup is harmful (negative result). Stage 1.3 tries the
additive direction: introduce orthogonal signals not present in current features.

Added features (8):
  hour_sin, hour_cos         (cyclic hour of UTC day)
  dow_sin, dow_cos           (cyclic day of week)
  session_london             (UTC 7-16)
  session_ny                 (UTC 13-22)
  ret_lag_1                  (close.pct_change(1) lagged 1 bar — LGBM can't infer sequence)
  ret_lag_5                  (close.pct_change(1) lagged 5 bars)

Bases (with their best Stage 0.7 feature additions):
  M1_V2_baseline   + Regime_full   (53 -> 61 features)
  M1_chained_best  + Regime_cont   (49 -> 57 features)
  M15_chained_best + CSI            (50 -> 58 features)
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

_TIME_LAGGED_COLS = [
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "session_london", "session_ny",
    "ret_lag_1", "ret_lag_5",
]

# (name, base_tf, suffix, horizon, cw, extra_feat_groups)
_CASES = [
    ("M1_V2_Regime_full",   1, "730d",  20, None,
        ["regime_cont", "regime_oh"]),
    ("M1_chained_Regime_cont", 1, "730d",  40, {0: 1.2, 1: 1.0, 2: 1.2},
        ["regime_cont"]),
    ("M15_chained_CSI",     15, "1825d",  3, {0: 1.2, 1: 1.0, 2: 1.2},
        ["csi"]),
]


def _add_time_lagged_features(pair_dfs: dict[str, pd.DataFrame]) -> None:
    """Attach time-cyclic + lagged-return features in-place."""
    for pair, df in pair_dfs.items():
        ts = pd.DatetimeIndex(df["timestamp"])
        hour = ts.hour.to_numpy(dtype=float)
        dow = ts.dayofweek.to_numpy(dtype=float)

        df["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
        df["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
        df["dow_sin"] = np.sin(2 * np.pi * dow / 7.0)
        df["dow_cos"] = np.cos(2 * np.pi * dow / 7.0)

        df["session_london"] = ((hour >= 7) & (hour < 16)).astype(float)
        df["session_ny"]     = ((hour >= 13) & (hour < 22)).astype(float)

        # lagged returns (use close, pct_change → shift to make it strictly past)
        ret1 = df["close"].pct_change(1)
        df["ret_lag_1"] = ret1.shift(1).values
        df["ret_lag_5"] = ret1.shift(5).values


def _build_feat_cols(base_tf: int, extra_groups: list[str], with_time: bool) -> list[str]:
    base_cols = m._get_base_feat_for_tf(base_tf) + list(m._SPREAD_FEAT)
    extra: list[str] = []
    if "csi" in extra_groups:
        extra += ["csi_base", "csi_quote", "csi_diff_signed"]
    if "regime_cont" in extra_groups:
        extra += ["atr_ratio", "trend_slope"]
    if "regime_oh" in extra_groups:
        extra += [f"regime_{c}" for c in s07._REGIME_CATS]
    if with_time:
        extra += _TIME_LAGGED_COLS
    return base_cols + extra


def _attach_extra(pair_dfs, extra_groups, csi_feats, regime_feats):
    if "csi" in extra_groups:
        s07._attach_features(pair_dfs, csi_feats, ["csi_base", "csi_quote", "csi_diff_signed"])
    if "regime_cont" in extra_groups:
        s07._attach_features(pair_dfs, regime_feats, ["atr_ratio", "trend_slope"])
    if "regime_oh" in extra_groups:
        s07._attach_features(pair_dfs, regime_feats,
                              [f"regime_{c}" for c in s07._REGIME_CATS])


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
    del feat_dfs

    results = []
    # a_ref: use Stage 0.7 best (no time/lagged)
    full_a = _build_feat_cols(base_tf, extra_groups, with_time=False)
    print(f"\n  >> a_ref ({len(full_a)} feat)", flush=True)
    pair_dfs = {pair: df.copy() for pair, df in pair_dfs_master.items()}
    _attach_extra(pair_dfs, extra_groups, csi_feats, regime_feats)
    t0 = time.time()
    res = _train_and_simulate(pair_dfs, full_a)
    results.append((name, "a_ref", len(full_a), res))
    print(f"  a_ref           feat={len(full_a)}  Sharpe={res['sharpe']:+.4f}  "
          f"hit={res['hit_pct']:5.1f}%  n={res['n']:6,d}  PnL={res['pnl']:+9.1f}  ({time.time()-t0:.0f}s)",
          flush=True)
    del pair_dfs

    # b_with_time_lagged: add 8 time/lagged features
    full_b = _build_feat_cols(base_tf, extra_groups, with_time=True)
    print(f"\n  >> b_with_time_lagged ({len(full_b)} feat, +{len(full_b)-len(full_a)})", flush=True)
    pair_dfs = {pair: df.copy() for pair, df in pair_dfs_master.items()}
    _attach_extra(pair_dfs, extra_groups, csi_feats, regime_feats)
    _add_time_lagged_features(pair_dfs)
    t0 = time.time()
    res = _train_and_simulate(pair_dfs, full_b)
    results.append((name, "b_with_time_lagged", len(full_b), res))
    print(f"  b_with_time_lagged  feat={len(full_b)}  Sharpe={res['sharpe']:+.4f}  "
          f"hit={res['hit_pct']:5.1f}%  n={res['n']:6,d}  PnL={res['pnl']:+9.1f}  ({time.time()-t0:.0f}s)",
          flush=True)
    del pair_dfs

    return results


def main() -> None:
    print("="*80)
    print("Stage 1.3 - Add time + lagged features")
    print(f"  Added: {_TIME_LAGGED_COLS}")
    print(f"  Bases: {[c[0] for c in _CASES]}")
    print("="*80, flush=True)

    all_results = []
    for case_args in _CASES:
        all_results.extend(_run_case(*case_args))

    print("\n\n" + "="*100)
    print("STAGE 1.3 SUMMARY")
    print("="*100)
    print(f"  {'Case':<28}  {'Variant':<22}  {'Feat':>4}  {'Sharpe':>8}  {'Hit%':>6}  {'N':>7}  {'PnL':>10}")
    print("  " + "-"*98)
    for name, v, n_feat, res in all_results:
        print(f"  {name:<28}  {v:<22}  {n_feat:>4d}  {res['sharpe']:+8.4f}  "
              f"{res['hit_pct']:6.1f}%  {res['n']:7,d}  {res['pnl']:+10.1f}")
    print("="*100)


if __name__ == "__main__":
    main()
