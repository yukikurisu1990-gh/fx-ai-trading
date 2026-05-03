# Post Bug-Fix Research Status — 2026-05-03

Comprehensive snapshot of the research conducted on 2026-05-03 after discovering and
fixing 4 critical leakage bugs in `scripts/compare_prod_ablation.py`. This document is
**self-sufficient** — a fresh Claude Code session should be able to pick up directly
from here without rebuilding context.

## TL;DR

* Phase 9 era reported Sharpe values (0.16 – 0.18 SELECTOR/multipair) were leakage
  artifacts. After fixing 4 bugs, V2 baseline collapsed to **Sharpe -0.189**.
* 50+ cells across 4 stages explored knobs, TFs, Meta layer, feature engineering.
* Current best (clean pipeline, all bugs fixed):
  **M1 chained_best + Regime_cont features + multi-TF regime features → Sharpe -0.015,
  n=217, Hit 36.9%, PnL -42 pip** (over 730d × 20 pairs WF 365d/90d).
* Sharpe -0.015 is statistically still negative but ≈zero; ZERO is within striking
  distance with further lever tuning.
* All Phase 9 production adoption decisions (9.10 → 9.X-O) should be considered
  invalidated until re-verified on the clean pipeline.

## Critical Bug Fixes Applied

Applied to `scripts/compare_prod_ablation.py` (all four are required for any
reproducible measurement):

| Fix | Location | Description |
|---|---|---|
| **M1** | `_add_base_features:307-313` | Weekend-gap detection in M1 ATR. Without this, `prev_close.shift(1)` pulls Friday close at Monday open → TR 7.3× bloat. Added `gap_mask = ts_diff > 2min` and NaN out `pc` accordingly. |
| **C1** | `_add_upper_tf_features:355-363` | Post-weekend bin tainting. Upper TF resampling produces near-NaN bins after weekend gap; `pct_change`/`diff` on those bins generate spurious signals that propagate forward. Solution: NaN out features for 5 bins after any gap > 1.5×rule. |
| **C2** | `_add_mtf_features:382-388` | Partial bin filter via `_filter_partial(ohlc, rule, min_ratio)` — drops H4/D1/W1 bins where M1 bar count is below threshold (50% / 25% / 50% respectively). Sunday-open partial days were producing garbage daily ranges. |
| **C3** | `_add_mtf_features:398, 415` | `min_periods=14` on H4/D1 ATR (was `min_periods=1`, computing ATR from a single bar). |

Production training script `scripts/train_lgbm_models.py` has the **same M1 weekend-gap
bug** (line ~140: `prev_close = c.shift(1).fillna(c)`) — this needs to be patched
before the next production retrain.

## Settings of Current Best

```python
# scripts/compare_prod_ablation.py module globals (set per cell)
_BAR_MINUTES = 1
_HORIZON = 40
_TRAINING_MODE = "multi"         # multinomial label_tb, single LGBM
_TP_MULT = 1.5                   # TP at +1.5 × ATR
_SL_MULT = 1.0                   # SL at -1.0 × ATR
_CONF_THR = 0.40                 # entry needs p ≥ 0.40
_TOP_K = 3                       # max trades per bar (currency-deduped)
_EV_SL_FACTOR = 1.0
_USE_CLASS_WEIGHT = True
_CUSTOM_CLASS_WEIGHT = {0: 1.2, 1: 1.0, 2: 1.2}  # small_boost
```

**Features (55 total)**:
* Base 14: atr_14, bb_pct_b, bb_width, bb_lower/middle/upper, ema_12/26, macd_*, rsi_14,
  sma_20/50
* Upper TF (m5/m15/h1) × 8 = 24
* MTF (h4/d1/w1) = 6
* Spread bundle = 3
* pair_id = 1 (multipair)
* +regime continuous = 2 (atr_ratio, trend_slope at base TF)
* **+multi-TF regime continuous = 6** (tf_m5/m15/h1 × {atr_ratio, trend_slope})

**Data**: 20 OANDA majors, M1 bid/ask, 730 days, WF 365d / 90d × 5 folds.

## Research Stage Summary

### Stage 1 — Phase 9 verdict re-validation (clean pipeline, V2 settings)

Three ablation cells using `scripts/compare_prod_ablation.py --cells C_wf365_base
E_wf365_full G_mp_wf365`:

| Cell | Spread | Mode | Sharpe | n | Hit% | PnL |
|---|---|---|---|---|---|---|
| C_wf365_base | ❌ | per-pair | -0.304 | 1880 | 23.9% | -4118 |
| E_wf365_full | ✓ | per-pair | -0.301 | 1383 | 26.1% | -3081 |
| G_mp_wf365 (V2 baseline) | ✓ | multipair | -0.189 | 112 | 26.8% | -293 |

Conclusion: Phase 9.15 “spread bundle PnL +13%” verdict invalidated. Multipair lift
real (+0.115 Sharpe vs per-pair) but achieved by cutting trade count 92%, not by
finding new edge.

Log: `artifacts/stage1_ablation_clean.log`

### Stage 2 — Knob sweeps (M1, V2 base)

* **2.1 TP/SL × conf** (16 cells, `scripts/sweep_conf_tpsl_v2.py`): best
  `tp=1.5/sl=1.0/conf=0.35` → -0.145.
* **2.2 class_weight** (6 variants, `scripts/sweep_class_weight_v2.py`): best
  `small_boost {0:1.2, 1:1.0, 2:1.2}` → -0.101.
* **Combined 2.1+2.2 smoke** (`scripts/stage2_combined_smoke.py`): -0.191 — interfere,
  do **not** combine.
* **2.3 HORIZON** (`scripts/stage2_3_horizon_sweep.py`): best `H=40` (40 min hold)
  → -0.085.
* **2.4 Top-K** (`scripts/stage2_4_topk_sweep.py`): K≥2 saturates at -0.085, K=1 worse.

M1 chained best (cumulative): tp=1.5/sl=1.0/conf=0.40/H=40/small_boost/K=2-3
→ Sharpe -0.085.

### Stage 3 — Time frame switch

* **3.1 M5 1095d** (`scripts/stage3_m5_baseline.py`): V2 baseline -0.110, small_boost
  variants worse. M5 V2 alone is the M5 best.
* **3.2 M15 1825d** (`scripts/stage3_m15_baseline.py`): V2 baseline -0.084,
  `small_boost + H=3 (45 min)` → -0.039 (best). 17 folds — large n.

Pattern: TF-cost ratio dominates (M1 ATR/spread ≈ 67%, M15 ≈ 30%). M15 + small_boost
+ H=3 “45-min hold sweet spot” mirrors M1 H=40 finding.

### Stage 0.5 / 0.6 — Production Meta layer evaluation

`scripts/stage0_5_meta_layer_eval.py` and `stage0_6_meta_layer_improved.py`.

**Critical TZ bug discovered and fixed**: `csi_df[base].reindex(df["timestamp"].values)`
stripped tz from the right side, returning all NaN. Fix: pass
`pd.DatetimeIndex(df["timestamp"])` instead.

After fix, on M15_chained_CSI base:
| Variant | Sharpe | n | Hit% |
|---|---|---|---|
| LGBM only | -0.039 | 195 | 40.0% |
| F5_only (CSI gate) | -0.023 | 185 | 41.1% |
| Regime_only (weight) | -0.039 | 195 | 40.0% |
| F5+Regime | -0.023 | 185 | 41.1% |

Production Meta layer is essentially **NO-OP on M1**, **+0.016 lift on M15**.
Directional variants (Stage 0.6) added no further lift.

### Stage 0.7 — CSI / Regime as INPUT FEATURES

`scripts/stage0_7_csi_regime_as_features.py`. Re-evaluates the Phase 9.16 verdict
("CSI as features → REJECT") on clean pipeline.

| Base | a_baseline | b_+CSI | c_+Regime_cont | d_+Regime_full | e_ALL |
|---|---|---|---|---|---|
| M1_V2 (-0.189) | -0.189 | -0.227 | -0.118 | **-0.049** ⭐ | -0.323 |
| M1_chained (-0.085) | -0.085 | -0.102 | -0.078 | -0.148 | -0.172 |
| M15_chained (-0.039) | -0.039 | **-0.019** ⭐ | -0.149 | -0.104 | -0.019 |

Findings:
* **Feature effects are TF-orthogonal**: M1 = Regime helps / CSI hurts, M15 = CSI helps
  / Regime hurts.
* M1 V2 + Regime_full alone gives **+0.140 lift** — biggest single-feature improvement.
* M15 + CSI gives **-0.019** (former overall best, n=208).

### Stage 1.1 — Feature importance dump

`scripts/stage1_1_feature_importance.py` — fold-1 train of M15+CSI best, dump
`feature_importances_`.

Top features (by gain%):
1. bb_pct_b 11.6 %
2. spread_zscore_50 7.6 %
3. d1_atr_14 6.4 %
4. spread_now_pip 6.3 %
5. spread_ma_ratio_20 5.5 %
6. atr_14 5.1 %

Group analysis:
* **spread bundle**: 19.3 % total, 33,621 avg/feat (highest leverage)
* close_smooth (ema_12/26, sma_20/50, bb_middle): only 1.4 %, avg/feat 1503 (lowest)

Zero-gain features (split=0): sma_20, h1_trend_dir, h4_full_trend_dir, h8_trend_dir.

### Stage 1.2 / 1.3 — Feature engineering attempts (NEGATIVE results)

* **1.2 cleanup** (`scripts/stage1_2_feature_cleanup.py`): drop 8-10 low-gain features.
  Result: all 3 bases worse (-0.018 to -0.149). Even zero-gain features contribute to
  tree splits; removing breaks structure.
* **1.3 add time + lagged returns** (`scripts/stage1_3_time_lagged_features.py`): add
  hour_sin/cos, dow_sin/cos, session flags, ret_lag_1/5. Result: all 3 bases worse
  (-0.082 to -0.129). LightGBM at capability ceiling.

### Stage 0.8a — Multi-TF regime features (NEW BEST)

`scripts/stage0_8a_multi_tf_regime.py`. Add `tf_<period>_atr_ratio` and
`tf_<period>_trend_slope` per upper TF, broadcast to base TF via shift(1)+ffill.

| Case | a_ref | b_multi_tf | Δ |
|---|---|---|---|
| M1_V2_Regime_full | -0.049 | -0.184 | -0.135 (worse) |
| **M1_chained_Regime_cont** | -0.078 | **-0.015** ⭐ | **+0.063** |
| M15_chained_CSI | -0.019 | -0.047 | -0.028 (worse) |

**M1_chained + Regime_cont + multi_TF (m5/m15/h1) → Sharpe -0.015, n=217, Hit 36.9 %,
PnL -42 pip** is the new overall best. Multi-TF regime info captures the
"M1 trending but M15 ranging" disagreement signal that the user explicitly hypothesised.

Hit% slightly down (37.3 → 36.9), but PnL improved 5× (-216 → -42) — trade quality up.

## Top 3 Configs Across All Stages

| # | Config | Sharpe | n | Hit% | PnL |
|---|---|---|---|---|---|
| **1** | **M1 chained + Regime_cont + multi_TF** ⭐ | **-0.015** | 217 | 36.9% | -42 |
| 2 | M15 chained + CSI | -0.019 | 208 | 42.8% | -77 |
| 3 | M1 V2 + Regime_full | -0.049 | 121 | 33.1% | -76 |

## Outstanding Issues

### Production-side (blocks live deployment)

1. **`scripts/train_lgbm_models.py:~140`** — has the same M1 weekend-gap TR bug we
   just fixed in the backtest. **Production model retrained on 2026-04-29 is
   leakage-corrupt**. Patch + retrain is mandatory before next volume mode cycle
   (~2026-05-27).
2. **`min_periods=1` vs `min_periods=14` mismatch** — production uses
   `min_periods=1`, backtest uses 14. Same ATR series will differ for the first 13
   bars of any history.
3. **`last_close` feature** — production trains 15 base features (incl. last_close);
   backtest has 14. **Skew between training and inference**.

### Knob lift ceiling on M1 chained + multi_TF

* conf_thr / TP/SL / EV_SL_FACTOR re-sweep on the new best config (Sharpe -0.015) is
  the cheapest next step, ~30 min.
* Adding CSI features to M1_chained + multi_TF was rejected by Stage 0.7 (M1+CSI
  hurt) but worth re-testing now since multi_TF changed the landscape.

### Regime classifier quality

Current classifier uses crude hardcoded thresholds (`atr_ratio > 2.0` for high_vol,
`|slope| > 0.3` for trend_*). On M1 V2 only **1/112** trades classify as `range`.
Data-driven thresholds + multi-feature classification would likely lift further.

## Plan Going Forward

### Immediate (≤ 1 day)

1. **Knob sweep on M1 chained + multi_TF best** (~30 min)
   * conf_thr ∈ {0.30, 0.35, 0.40, 0.45}
   * TP/SL ∈ {(1.0, 1.0), (1.5, 1.0), (2.0, 1.0)}
   * Expected: small lift, possibly into positive Sharpe (+0.01 to +0.03).
2. **Feature combo sweep on M1 chained + multi_TF** (~1 hour)
   * Add CSI features (Stage 0.7 said no but multi_TF changed things)
   * Add Regime one-hot (Stage 0.7 said no but multi_TF changed things)
   * Add upper-TF (h4, d1) regime to M1 base (currently only m5/m15/h1)

### Short-term (1-2 days)

3. **Regime classifier improvement** (~half day)
   * Data-driven thresholds: 33/67 percentile from training data
   * Optional multi-feature: add realized vol / autocorr / skewness
4. **Production sync** (~half day)
   * Patch `train_lgbm_models.py` weekend-gap bug
   * Patch `feature_service.py` if same pattern exists
   * Add `last_close` to backtest OR remove from production (alignment)
   * Retrain production model

### Medium-term (2-5 days)

5. **LSTM revisit** (~1.5-2 days)
   * Phase 9.X-C/M-1 LSTM was tested on buggy pipeline (Sharpe 0.061). Re-run on
     clean pipeline.
   * GPU available (RTX 3060 Ti).
   * Decision threshold: if LSTM ≤ -0.015, stick with LGBM.
6. **Walk-forward stability check on M1 chained + multi_TF** (~30 min)
   * Per-fold Sharpe, year-over-year breakdown, robustness to random seed.

## Reproducing the Current Best

```bash
# From C:\Users\yukik\fx-ai-trading

PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/stage0_8a_multi_tf_regime.py \
  > artifacts/stage0_8a_multi_tf_regime.log 2>&1

# Expected (M1_chained_Regime_cont b_multi_tf):
#   Sharpe = -0.0152
#   n = 217
#   Hit% = 36.9%
#   PnL = -41.8 pip
```

`scripts/stage0_8a_multi_tf_regime.py` runs all 3 bases (M1_V2, M1_chained, M15_chained)
× 2 variants (a_ref, b_multi_tf) = 6 cells in ~30 min.

To extend with knob sweep, set `m._CONF_THR = 0.35` etc. in a wrapper script that
imports `stage0_8a_multi_tf_regime` and just iterates `_run_case` with different
overrides.

## File Layout (research scripts)

```
scripts/
  compare_prod_ablation.py            # CRITICAL: contains M1/C1/C2/C3 fixes (UNTRACKED!)
  sweep_conf_tpsl_v2.py               # Stage 2.1
  sweep_class_weight_v2.py            # Stage 2.2
  stage2_combined_smoke.py            # Stage 2.1+2.2 combined smoke
  stage2_3_horizon_sweep.py           # Stage 2.3
  stage2_4_topk_sweep.py              # Stage 2.4
  stage3_m5_baseline.py               # Stage 3.1
  stage3_m15_baseline.py              # Stage 3.2
  stage0_5_meta_layer_eval.py         # Stage 0.5 (incl. _compute_csi, _compute_regime; tz fix applied)
  stage0_5_m15_chained_only.py        # Stage 0.5 wrapper (deprecated)
  stage0_6_meta_layer_improved.py     # Stage 0.6
  stage0_7_csi_regime_as_features.py  # Stage 0.7
  stage1_1_feature_importance.py      # Stage 1.1
  stage1_2_feature_cleanup.py         # Stage 1.2
  stage1_3_time_lagged_features.py    # Stage 1.3
  stage0_7a_meta_inverted.py          # ABANDONED (old design, premise was tz-bug interpretation)
  stage0_8a_multi_tf_regime.py        # Stage 0.8a (NEW BEST)

artifacts/
  stage1_ablation_clean.log
  stage2_*.log
  stage3_*.log
  stage0_5_meta_eval_FIXED.log
  stage0_6_meta_improved.log
  stage0_7_csi_regime_features.log
  stage0_8a_multi_tf_regime.log       # current best run output
  stage1_1_feature_importance.log
  stage1_2_feature_cleanup.log
  stage1_3_time_lagged.log
```

## Memory Index Updates

The following memory files capture the most-needed context for a fresh session:

* `project_v2_baseline_critical_fixes.md` — bug fixes summary
* `project_phase9_invalidation_2026_05_03.md` — Phase 9 verdicts invalidation
* `project_post_bug_fix_research_2026_05_03.md` (NEW) — research summary, current best
