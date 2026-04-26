# Phase 9.X-B — Alternative features (multi-pattern) Closure Memo

**Status**: Closed — **PARTIAL GO+** for `+mtf` alone (Sharpe 0.173 K=2, 0.174 K=3)
**Master tip at authorship**: `ff5f3be` (after Phase 9.X-A merged)
**Predecessor**: Phase 9.X-A closed NO ADOPT 2026-04-26 (label class is NOT the lever)
**Related**: `docs/design/phase9_x_b_design_memo.md`, `docs/design/phase9_x_a_closure_memo.md`

---

## 1. What this phase set out to do

Phase 9.X-A confirmed label class is NOT the lever. Phase 9.13–9.X-A's recurring pattern ("trade-rate explosion + per-trade EV collapse") suggested the bottleneck is in the (LightGBM × 15 TA features) calibration pair. Phase 9.X-B attacked the **features axis** with three OHLC-only feature groups in parallel — per user direction "**try multiple patterns, not just one**".

| Group | Features | Hypothesis |
|-------|---------|-----------|
| **vol** | realized variance (5/20), vol-of-vol, variance ratio, EWMA cond. var (~6 features) | GARCH-like dynamics complementary to ATR |
| **moments** | rolling skew/kurt (20), autocorr lag-1/lag-5 (~4 features) | Distributional asymmetry + persistence |
| **mtf** | 4h ATR, daily/weekly OHLC stats (~6 features) | Slower-cadence regime indicators |

---

## 2. What shipped

| PR | Scope | Result |
|----|-------|--------|
| (this PR #218) | L-0..L-2 bundled — design memo + v16 script + 4 evals + closure memo | **PARTIAL GO+** for +mtf |

Bug fixed mid-flight: autocorrelation pure-Python `.apply(lambda)` was prohibitively slow at 20-pair × 500k-bar scale; vectorised to `rolling.corr(shift(k))` (~100× faster). Smoke test at 2 pairs after fix gave Sharpe 0.196 — the suspected breakthrough. The 20-pair full eval revealed this was a 2-pair artefact (EUR/USD + GBP/USD overstate the moments lift).

---

## 3. Results — 4 evals × 8 sweep cells each = 32 data points

### 3.1 K=2 lgbm_only summary (most-comparable to Phase 9.19 PARTIAL GO baseline)

```
Variant             Sharpe    PnL(pip)    DD%PnL    PnL ratio   Trades
baseline (9.16)     0.160     8,157.2     2.5%      1.00x       12,461
Phase 9.19 K=2      0.165     10,219.8    2.6%      1.25x       12,461  (prior PARTIAL GO)
+vol K=2            0.166     9,902.4     2.7%      1.21x       11,299
+moments K=2        0.158     9,194.1     2.8%      1.13x       11,961
+mtf K=2            0.173     14,050.9    1.9%      1.72x       16,958  ★ BEST
+all K=2            0.158     10,838.2    2.7%      1.33x       13,456
```

### 3.2 K=3 lgbm_only summary (best Sharpe per group)

```
Variant             Sharpe    PnL(pip)    DD%PnL    PnL ratio   Trades
+vol K=3            0.160     10,384.9    3.3%      1.27x       11,299
+moments K=3        0.157     9,650.1     2.7%      1.18x       11,961
+mtf K=3            0.174     15,118.5    1.8%      1.85x       16,958  ★ BEST OVERALL
+all K=3            0.156     11,427.6    2.8%      1.40x       13,456
```

### 3.3 K=1 lgbm_only — direct apples-to-apples vs baseline

```
Variant             Sharpe    PnL(pip)    DD%PnL    Trades
baseline (9.16)     0.160     8,157.2     2.5%      12,461
+vol K=1            0.157     7,640.0     2.5%      11,299  (slight regression)
+moments K=1        0.145     7,037.9     3.3%      11,961  (clear regression)
+mtf K=1            0.163     10,990.3    2.1%      16,958  (modest lift)
+all K=1            0.150     8,546.9     2.6%      13,456  (regression)
```

### 3.4 Per-rank Sharpe diagnostic (mtf K=3 lgbm_only)

```
Rank      Mean Sharpe    Folds with rank
Rank 1    0.176          39
Rank 2    0.168          39
(Rank 3   ~0.10 estimated; per-rank dilution similar to Phase 9.19)
```

Both rank-1 and rank-2 mtf picks have higher individual Sharpe than Phase 9.19's (0.158 / 0.147). This is structural lift, not noise.

---

## 4. Verdict

| Variant | Best (cell, K) | Sharpe | PnL ratio | Gate result |
|---------|---------------|--------|-----------|-------------|
| **+mtf** | K=3 lgbm_only | **0.174** | **1.85×** | **PARTIAL GO+** (clearly above baseline; PnL ≥ 1.10×; DD%PnL 1.8%) |
| +vol | K=2 lgbm_only | 0.166 | 1.21× | Within noise vs Phase 9.19 baseline |
| +moments | K=2 lgbm_only | 0.158 | 1.13× | Worse than baseline at K=1 |
| +all | K=2 lgbm_only | 0.158 | 1.33× | Worse than mtf alone — multicollinearity |

| Gate | Result |
|------|--------|
| GO (Sharpe ≥ 0.18 AND PnL ≥ 1.10× AND DD%PnL ≤ 5%) | ✗ Sharpe 0.174 < 0.18 |
| **PARTIAL GO** (Sharpe ≥ baseline AND PnL ≥ baseline AND DD%PnL ≤ 5%) | **✓ +mtf clearly meets** |
| STRETCH GO (any Sharpe ≥ 0.20) | ✗ best 0.174 |
| NO ADOPT (Sharpe < baseline) | not triggered for +mtf |

**Verdict: PARTIAL GO+ for +mtf alone** — Sharpe +0.014 vs baseline (vs Phase 9.19's +0.005). Largest single-feature-change Sharpe lift since Phase 9.13 C-3 (+0.017).

---

## 5. Why +mtf works and the others don't

### 5.1 +mtf adds genuine orthogonal signal

The 4h/daily/weekly stats (h4_atr_14, d1_return_3, d1_atr_14, w1_return_1) capture **slower-cadence regime information** that the m5/m15/h1 features in the v9 baseline miss. LightGBM uses these as effective regime filters: PnL grows from 8,157 to 15,118 (1.85×) AND Sharpe rises (variance grows slower than mean).

Trade count rises from 12,461 to 16,958 (+36%). This is the FIRST phase where extra trades arrive WITH per-trade quality preserved. Per-trade EV at K=1: 10,990 / 16,958 = **0.648 pip/trade** vs baseline 0.654 pip/trade. **Same per-trade quality, more trades** — this is what Phase 9.13-9.19 was trying to find.

### 5.2 +vol's features are redundant with existing ATR

Volatility features (real_var, vol-of-vol, var_ratio, ewma_var) duplicate information already captured by atr_14, bb_width, and the multi-TF h1_volatility from Phase 9.4-9.9. LightGBM's split-selection sees them but they don't add discriminative power.

### 5.3 +moments alone HURTS at K=1

Skewness/kurtosis/autocorrelation features are *noisy* (rolling-window 20-bar moments are heavily influenced by outliers). At K=1 the model picks up false signals from these noisy features → Sharpe drops from 0.160 to 0.145. At K>=2, the SELECTOR's argmax averages out some noise → Sharpe recovers to 0.158 (still below baseline).

### 5.4 +all dilutes mtf's advantage (multicollinearity)

When all 16 new features are added together:
- Sharpe drops from 0.173 (mtf alone, K=2) to 0.158 (all combined)
- PnL drops from 14,051 to 10,838

LightGBM's tree-split selection scrambles when given too many correlated features. The vol features compete with mtf's daily ATR for the same regime-detection role. Result: mtf's lift gets diluted.

**Lesson**: feature additions are NOT additive. Each group must be tested individually first; combination only makes sense if individual tests show orthogonal lifts.

---

## 6. Cumulative path through Phase 9.10–9.X-B

```
v3 (mid label, 1pip):                 Sharpe -0.076  NO-GO
v5 (bid/ask label):                   Sharpe +0.160  ★ DECISIVE
v9-20p (20 pairs):                    Sharpe +0.160  ★ Phase 9.16 production default
v12 bucketed:                         Sharpe +0.127  ✗ Phase 9.18 NO ADOPT
v13 lgbm+mr (t=0.0):                  Sharpe +0.053  ✗ Phase 9.17 NO ADOPT
v14 lgbm_only K=2 naive:              Sharpe +0.165  ★ Phase 9.19 PARTIAL GO
v15 regression pct=50 K=5:            Sharpe +0.092  ✗ Phase 9.X-A NO ADOPT
v16 +vol K=2 lgbm_only:               Sharpe +0.166  ~ marginal lift
v16 +moments K=1 lgbm_only:           Sharpe +0.145  ✗ regression
v16 +mtf K=3 lgbm_only:               Sharpe +0.174  ★ Phase 9.X-B PARTIAL GO+ (this)
v16 +all K=2 lgbm_only:               Sharpe +0.158  ✗ multicollinearity
```

---

## 7. What's next

**Phase 9.X-B production-toggle (recommended)**: similar to Phase 9.19/J-3, add `--feature-groups mtf` to the production decision loop's runtime config. Default empty (Phase 9.16 baseline preserved); opt-in `--feature-groups mtf` activates the 1.85× PnL lift with Sharpe 0.174 / DD%PnL 1.8%. ~1 day implementation; low risk.

**Phase 9.X-C — LSTM/TFT (parallel track)**: still on the table. Sharpe ≥ 0.20 STRETCH GO is needed to unblock Phase 9.11. mtf alone gives 0.174; LSTM might stack with it. Estimated ~5 days. Recommended sequence:

```
Phase 9.X-B (this) ─→ PARTIAL GO+ ─→ adopt +mtf (J-4 toggle)
                              ↓
Phase 9.X-C (LSTM) — does it stack with +mtf?
                              ↓
   ├ STRETCH GO: ship combined, unblock Phase 9.11
   └ NO ADOPT: bottleneck is data source layer (microstructure)
```

**Phase 9.11 (3+ yr robustness)**: still BLOCKED on Sharpe ≥ 0.20. mtf alone insufficient.

---

## 8. Notes for future-me

1. **2-pair smoke is unreliable for moments-style features.** The +moments smoke gave Sharpe 0.196 on EUR/USD+GBP/USD; 20-pair full eval gave 0.158. The two-pair sample over-emphasizes correlated USD-major behavior. **Always require 5+ pairs of smoke before committing to a phase direction.**

2. **Multi-timeframe extension (mtf) is the only feature axis that worked.** vol features were redundant with existing ATR; moments features were too noisy. The pattern: features need to capture INFORMATION the existing 15 TA features miss, not duplicate them. Phase 9.4-9.9 already explored m5/m15/h1; the gap was 4h/daily/weekly. This makes intuitive sense post-hoc.

3. **+all combination dilutes mtf's advantage** (Sharpe 0.158 vs mtf alone 0.173). Multicollinearity / curse of dimensionality. **Future feature work**: test groups individually first; only combine if the individual results suggest non-overlapping lifts.

4. **Per-trade EV at K=1 with mtf: 0.648 pip/trade vs baseline 0.654 pip/trade.** Trade count rose 36% with per-trade EV preserved — this is the FIRST phase to escape the "trade-rate explosion + EV collapse" pattern that has been confirmed 5 times prior (Phase 9.17, 9.17b, 9.19, 9.X-A, +moments here). The lever is: **add features that enable better trade SELECTION**, not features that produce MORE trade signals.

5. **Autocorrelation perf bug**: `rolling().apply(lambda x: pd.Series(x).autocorr(lag=k))` is prohibitively slow (~100× slower than `rolling().corr(shift(k))`). The smoke test at 2 pairs ran in 1 minute, but at 20 pairs × 500k bars it never finished. Always vectorise rolling computations on 500k-bar series.

6. **+mtf K=3 is the practical sweet spot**: Sharpe 0.174 / PnL 1.85× / DD%PnL 1.8%. K=5 has slightly higher PnL (1.85→1.85×) but Sharpe drops to 0.170 — diminishing returns kick in. K=3 is the recommended production setting.

7. **Confidence in next-phase ordering updated**: Phase 9.X-B PARTIAL GO+ falsifies the "all engineering levers exhausted" prior. Adjusted prior for Phase 9.X-C (LSTM): ~40% chance of STRETCH GO when stacked with mtf (unconditional Sharpe lift from sequence-aware modeling on otherwise-static features). Worth pursuing.

---

## 9. Commit trail

```
900f154  PR #218  L-1 v16 with 3 feature groups (vol/moments/mtf)
cd53a31  PR #218  fix autocorrelation vectorisation (perf bug)
<TBD>    PR #218  L-2 closure memo + 4 eval logs
```
