# Phase 9.X-A — Alternative labels (return regression) Closure Memo

**Status**: Closed — **NO ADOPT** (label class is NOT the lever; pivot to Phase 9.X-B alt features)
**Master tip at authorship**: `e6d4905` (after Phase 9.19/J-1 merged) + this PR
**Predecessor**: Phase 9.19 closed PARTIAL GO 2026-04-26 (modest +25% PnL via Top-K)
**Related**: `docs/design/phase9_x_a_design_memo.md`, `docs/design/phase9_19_closure_memo.md`

---

## 1. What this phase set out to do

Phase 9.13–9.19 collectively proved every alpha-engineering lever feeding INTO the SELECTOR has been exhausted. Phase 9.19 closure §6 framed the structural conclusion: "the model class itself is the ceiling." Option B (model-class change) has three candidate axes, sequenced cheapest-first:

- **A — Alternative labels** (THIS PHASE)
- **B — Alternative features**
- **C — Alternative model class (LSTM/Transformer)**

Phase 9.X-A tested the **cheapest** axis: swap the LightGBM 3-class triple-barrier classifier for an LGBMRegressor on raw return at horizon. Same features, same TB PnL eval. The single question: **is the calibration ceiling label-dependent (training target) or model-dependent (LightGBM × 15 TA features)?**

---

## 2. What shipped

| PR | Scope | Result |
|----|-------|--------|
| (this PR) | K-0..K-2 bundled — kickoff design memo + `compare_multipair_v15_regression.py` + 20-pair eval at percentile thresholds {50, 90} + closure memo | NO ADOPT |

---

## 3. Results — 20-pair, 39-fold, two threshold percentiles

### 3.1 pct=50 (50th percentile of |y_hat| as no-trade floor)

```
Cell              K   Sharpe   PnL(pip)   MaxDD   DD%PnL   PnL ratio   Trades
lgbm_only         1   0.061    21,306     219     1.0%     2.61×       276,017
lgbm_only         2   0.077    41,158     392     1.0%     5.04×       276,017
lgbm_only         3   0.083    54,094     504     0.9%     6.63×       276,017
lgbm_only         5   0.092    79,102     816     1.0%     9.69×       276,017
lgbm+mr+bo        1   0.060    20,883     216     1.0%     2.56×       276,218
lgbm+mr+bo        2   0.075    39,312     392     1.0%     4.82×       276,218
lgbm+mr+bo        3   0.082    53,532     517     1.0%     6.56×       276,218
lgbm+mr+bo        5   0.091    79,021     771     1.0%     9.69×       276,218
```

### 3.2 pct=90 (90th percentile, more aggressive filter)

```
Cell              K   Sharpe   PnL(pip)   MaxDD   DD%PnL   PnL ratio   Trades
lgbm_only         1   0.050    13,182     381     2.9%     1.62×       171,475
lgbm_only         2   0.070    25,852     472     1.8%     3.17×       171,475
lgbm_only         3   0.078    33,677     435     1.3%     4.13×       171,475
lgbm_only         5   0.082    42,633     590     1.4%     5.23×       171,475
lgbm+mr+bo        1   0.038    11,902     332     2.8%     1.46×       254,613
lgbm+mr+bo        2   0.053    23,940     447     1.9%     2.94×       254,613
lgbm+mr+bo        3   0.060    33,422     515     1.5%     4.10×       254,613
lgbm+mr+bo        5   0.073    52,129     506     1.0%     6.39×       254,613
```

### 3.3 Best (cell, K, pct) by Sharpe vs baseline

| Variant | Best Sharpe | Best PnL ratio | Baseline gap |
|---------|-------------|---------------|---------------|
| Regression pct=50 K=5 lgbm_only | **0.092** | 9.69× | **−0.068 vs baseline 0.160** |
| Regression pct=90 K=5 lgbm_only | 0.082 | 5.23× | −0.078 |
| Phase 9.16 production baseline | 0.160 | 1.00× | 0 |
| Phase 9.19 K=2 naive lgbm_only (PARTIAL GO) | 0.165 | 1.25× | +0.005 |

**Regression NEVER reaches baseline Sharpe across all 16 sweep cells.**

---

## 4. Verdict — NO ADOPT

| Gate | Best regression cell | Result |
|------|---------------------|--------|
| GO (Sharpe ≥ 0.18 AND PnL ≥ 1.10× AND DD%PnL ≤ 5%) | pct=50 K=5: Sharpe 0.092 | ✗ Sharpe 0.092 << 0.18 |
| PARTIAL GO (Sharpe ≥ baseline 0.160) | best 0.092 | ✗ |
| STRETCH GO (any Sharpe ≥ 0.20) | best 0.092 | ✗ |
| **NO ADOPT** (Sharpe < baseline) | all cells | ✓ TRIGGERED |

**Production default unchanged: 20-pair v9 symmetric spread bundle (Sharpe 0.160, PnL 8,157, DD%PnL 2.5%).**

This is the **expected outcome (60% prior probability per design memo §9)**. The optimistic 25% scenario (Sharpe 0.18-0.22) did not materialize. Confirms the working hypothesis.

---

## 5. The structural finding — labels are NOT the lever

Phase 9.X-A produces a stronger conclusion than "regression doesn't help":

**Regression makes things STRICTLY WORSE as a single-pair signal.** At K=1:
- Classifier baseline lgbm_only: Sharpe 0.160, PnL 8,157, Trades 12,461
- Regression pct=50 lgbm_only: Sharpe 0.061 (−62%), PnL 21,306 (+161%), Trades 276,017 (+22×)
- Regression pct=90 lgbm_only: Sharpe 0.050 (−69%), PnL 13,183 (+62%), Trades 171,475 (+14×)

The regression generates **22× more trades than the classifier** but per-trade EV plummets:
- Classifier per-trade EV: 8,157 / 12,461 = **0.654 pip/trade**
- Regression pct=50 per-trade EV: 21,306 / 276,017 = **0.077 pip/trade** (−88%)

This pattern is **identical** to the Phase 9.17 / 9.17b / 9.19 trade-rate explosion problem: more trades, lower per-trade EV, Sharpe collapses. The label change didn't fix the calibration ceiling.

**Most importantly**: even at the most aggressive filter (pct=90 cuts trade rate by ~40%), Sharpe only lifts marginally (0.061 → 0.050 wait, that's WORSE; 0.092 → 0.082 also worse). Filtering by predicted-magnitude **does NOT improve per-trade quality** — same calibration problem found in Phase 9.18 / 9.17b for classifiers.

**The bottleneck is NOT in the label space.** The same 15 TA features carry the same predictive ceiling regardless of whether we train classifier or regressor on them.

---

## 6. What's next — Phase 9.X-B (alt features) is the natural pivot

Per Phase 9.19 closure §6 sequencing:

```
Phase 9.X-A (regression label)        ← THIS PHASE: NO ADOPT
        ↓
Phase 9.X-B (alt features)            ← NEXT (cheapest decisive test)
        ↓
   ├ GO: features were the bottleneck → ship
   └ NO ADOPT: model class is the bottleneck
        ↓
Phase 9.X-C (LSTM / TFT)              ← if 9.X-B fails
        ↓
   └ NO ADOPT: data source is the bottleneck (microstructure required)
```

### 6.1 Phase 9.X-B — Tier 1 candidates

Per the conversation thread of 2026-04-26 evening (user-recommended ordering):

| Candidate | Cost | Expected | Notes |
|-----------|------|----------|-------|
| **Volatility clustering** (GARCH cond. var, vol-of-vol, variance ratio) | 1-2 days | Medium | OHLC-only; complementary to existing ATR |
| **Cross-asset (DXY momentum minimum)** | 3 days | Medium-High | Different alpha source; well-documented FX driver |
| **Calendar / event** (FOMC/NFP distance, event-time × hour-of-day) | 2-3 days | Medium-High | FX is event-driven; needs OANDA labs API or self-built calendar |
| Microstructure / orderbook | 3-5 days + data | High | OANDA does NOT provide L2; needs separate data source |

**Recommended Tier 1 (Phase 9.X-B kickoff)**: **vol-clustering + DXY combined** — ~2.5 days, no new data dependency. The cheapest decisive test of "are features the bottleneck?".

### 6.2 If Phase 9.X-B also fails

Pivot to Phase 9.X-C (LSTM, ~5 days). If LSTM also fails, the answer is: data source is the bottleneck → microstructure data acquisition (Phase 9.X-D).

---

## 7. Cumulative path through Phase 9.10–9.X-A

```
v3 (mid label, 1pip):                 Sharpe -0.076  NO-GO
v5 (bid/ask label):                   Sharpe +0.160  SOFT GO  ★ DECISIVE
v9-20p (20 pairs):                    Sharpe +0.160  PnL +20.1%  ★ Phase 9.16 (production default)
v12 bucketed (H-1):                   Sharpe +0.127  PnL -19%    ✗ Phase 9.18 NO ADOPT
v13 lgbm+mr (t=0.0):                  Sharpe +0.053  PnL +52%    ✗ Phase 9.17 NO ADOPT
v13 lgbm+mr (t=0.5):                  Sharpe +0.058  PnL +40%    ✗ Phase 9.17b NO ADOPT
v14 lgbm_only K=2 naive:              Sharpe +0.165  PnL +25%    ★ Phase 9.19 PARTIAL GO
v14 lgbm_only K=5 naive:              Sharpe +0.161  PnL +36%    (sqrt(K) didn't materialise)
v15 regression pct=50 K=1:            Sharpe +0.061  PnL +161%   ✗ Phase 9.X-A NO ADOPT (this)
v15 regression pct=50 K=5:            Sharpe +0.092  PnL +869%   ✗ same fundamental ceiling
v15 regression pct=90 K=5:            Sharpe +0.082  PnL +423%   ✗ filter doesn't help calibration
```

---

## 8. Notes for future-me

1. **Label class is NOT the lever.** Confirmed across both classifier (TB) and regressor (return). Same 15 TA features carry the same ceiling regardless of model output. The next phase MUST attack either features or model architecture.

2. **The "trade-rate explosion + per-trade EV collapse" pattern repeats.** First seen in Phase 9.17 (rule strategies + LGBM ensemble), then 9.17b (threshold filter on rules), then 9.19 (multi-pick), now 9.X-A (regression). Whenever a new mechanism produces more trades from the same feature space, Sharpe collapses even if PnL grows. **Per-trade EV is the binding constraint, NOT trade count.**

3. **PnL grows linearly with trade count, Sharpe falls inversely** — across all four phases above. This is empirical evidence that the 15 TA features are *signal-saturated*: extracting more trades from them just dilutes per-trade quality.

4. **Pct-90 vs pct-50 filtering on regression**: cutting trade rate by ~40% (pct=50 276k → pct=90 171k) only changed Sharpe from 0.061 → 0.050 at K=1 (slightly *worse*). Filtering by predicted-magnitude doesn't lift per-trade EV — same finding as Phase 9.18 (LGBM confidence bucketing) and 9.17b (rule-strategy threshold). **All confidence-magnitude filters are weak levers in this feature space.**

5. **Regression at K=5 PnL is comically high** (79,103 pip = 9.7× baseline) but **Sharpe is half of baseline** (0.092 vs 0.160). Don't be tempted by raw PnL — variance grew faster than mean. If a future user wants raw pip count regardless of risk, they'd take this; if they want a stable strategy, they wouldn't. Production should NOT adopt this.

6. **Confidence in Phase 9.X-B+ ordering**: based on 4-phase repetition of the per-trade-EV pattern, I'd estimate Phase 9.X-B (alt features) ALSO has ~50% NO ADOPT probability. The signal is increasingly that the bottleneck is at the **data source** layer (microstructure required). Phase 9.X-C (LSTM) is unlikely to break the ceiling on the same feature stream — but worth one more cheap test before pivoting to data acquisition.

---

## 9. Commit trail

```
<TBD>    PR #???  K-0..K-2 bundled — design memo + v15 script + eval logs + this closure memo
```
