# Phase 9.17b — Confidence-threshold post-filter (Option A) Closure Memo

**Status**: Closed — **NO ADOPT** (Option A failed; pivot to Option C — SELECTOR multi-pick — recommended)
**Master tip at authorship**: `c971b4f` (Phase 9.17b/I-1 merged) + this PR
**Predecessor**: Phase 9.17 closed NO ADOPT 2026-04-26 at master `22a2a24`
**Related**: `docs/design/phase9_17_closure_memo.md`, `docs/phase9_roadmap.md` §6.19

---

## 1. What this phase set out to do

Phase 9.17 closure memo §5 identified the root cause of the ensemble's NO ADOPT verdict: **trade-rate explosion**. MR/BO had no LightGBM-style confidence-threshold filter, producing 192k+ trades vs LGBM's 12,461. SELECTOR was dominated by MR/BO (~95% of bars); LightGBM picked < 5% of bars; per-trade EV diluted; Sharpe collapsed (0.160 → 0.053) despite +52% PnL.

**Hypothesis (Option A)**: adding a confidence_threshold post-filter to MR/BO would:
1. Cut trade rate to LGBM-comparable levels
2. Restore SELECTOR balance (LGBM picks proportional to its EV-quality)
3. Lift Sharpe back toward the 0.160 baseline

**Cost**: cheap experiment (~1 day). If it works, Phase 9.17 NO ADOPT becomes ADOPT with the threshold flag.

---

## 2. What shipped

| PR | Scope | Result |
|----|-------|--------|
| #211 | I-1 — `confidence_threshold` post-filter on MR/BO + v13 helpers + CLI flag (89 tests) | implementation; merged |
| **(this PR)** | I-2 — 20-pair eval at thresholds {0.0, 0.3, 0.5} + closure memo | NO ADOPT |

---

## 3. Results — threshold sweep at 20 pairs, 39 folds

### 3.1 SELECTOR Sharpe across thresholds

```
Cell                t=0.0    t=0.3    t=0.5    Baseline (lgbm_only)
lgbm+mr             0.053    0.055    0.058    0.160
lgbm+bo             0.035    0.039    0.042    0.160
lgbm+mr+bo          0.036    0.038    0.039    0.160
```

**Sharpe lift across the entire sweep is +0.005 (lgbm+mr).** Far from the +0.107 needed to clear baseline.

### 3.2 SELECTOR PnL across thresholds (lgbm+mr cell)

```
                    t=0.0           t=0.3           t=0.5
Trades              192,832         172,477         148,320
PnL (pip)           12,360          11,909          11,463
MR share            95.7%           95.1%           94.3%
LGBM share          4.3%            4.9%            5.7%
ρ (lgbm vs mr)      0.317           0.306           0.275
```

### 3.3 Why the threshold filter did not work

**Hypothesis 1 (intended)**: cut MR trade rate → LGBM gets proportional SELECTOR share → Sharpe rises.
**Reality**: at threshold 0.5, MR's trade count dropped only 23% (192k → 148k), and MR's SELECTOR share dropped only from 95.7% to 94.3%. LGBM share rose only 4.3% → 5.7%. The filter is non-aggressive even at threshold 0.5 because MR's confidence distribution is heavy in the 0.5-1.0 range (when both RSI and Bollinger are simultaneously at extremes, the indicators co-move and confidence saturates fast).

**To force LGBM share ≥ 50%, threshold would need to be > 0.7**, which would starve MR to < 5,000 trades and likely below statistical significance.

---

## 4. Verdict — NO ADOPT

| Gate | t=0.5 result |
|------|-------------|
| GO (PnL ≥ 1.10× baseline AND ρ ≤ 0.4 AND Sharpe ≥ baseline) | ✗ Sharpe 0.058 << 0.160 |
| PARTIAL GO (PnL ≥ 1.05× AND Sharpe ≥ baseline) | ✗ Sharpe 0.058 << 0.160 |
| STRETCH GO (any cell Sharpe ≥ 0.18) | ✗ best 0.160 (baseline) |

**Production default unchanged: 20-pair v9 symmetric spread bundle (Sharpe 0.160, PnL 8,157, DD%PnL 2.5%).**

---

## 5. Why Option A failed — the deeper finding

The Phase 9.17 closure §5 framed the failure as **"trade-rate explosion drowns out LGBM"**. This memo refines that interpretation:

**The real problem is per-trade EV, not trade rate.**

Even after filtering 23% of MR trades (those with confidence < 0.5), the remaining 148k MR trades still have low per-trade EV compared to LGBM. Filtering low-confidence MR trades didn't help because **MR confidence is not a hit-rate predictor**:
- At threshold 0.0, MR's PnL was 12,360 over 192,832 trades = **0.064 pip/trade EV**
- At threshold 0.5, MR's PnL was 11,463 over 148,320 trades = **0.077 pip/trade EV**

The high-confidence MR trades have only marginally better EV than the low-confidence ones. This is the **same calibration problem** Phase 9.18 closure §8 found for LightGBM ("model confidence ≥ 0.65 hits at 54.1% vs 54.5% overall"), now confirmed for rule-based strategies as well.

**Conclusion**: the limit isn't filtering granularity. It's that **rule-based MR/BO strategies on the same TA features inherit LightGBM's calibration ceiling**. Their confidence scores don't reliably rank trades by quality.

---

## 6. What's next — recommend Option C over Option B

Phase 9.17 closure proposed two options for next phase:
- **Option B**: pivot to alternative model class (LSTM, alt labels). Structural fix; ~3-5 days; bigger scope.
- **Option C** (added per user proposal 2026-04-26): SELECTOR multi-pick / Top-K. Bypass the MR/BO problem entirely by taking multiple LGBM picks per bar across pairs. ~1 day; bigger expected lift.

### 6.1 Option C: SELECTOR multi-pick

**Hypothesis**: the current SELECTOR's "1 (pair × strategy) per bar" is the binding constraint on trade rate. Taking the top-K LGBM picks per bar (sorted by confidence) trivially multiplies trade rate by K. If picks are uncorrelated, Sharpe scales by sqrt(K).

**Theoretical lift table (baseline Sharpe 0.160, K=3)**:

| ρ between picks | Sharpe |
|----------------|--------|
| 0.0 (independent) | 0.277 (clears 0.20 gate) |
| 0.3 | 0.224 (clears) |
| 0.5 | 0.196 (borderline) |
| 0.7 | 0.179 (misses 0.18) |

**Risks**:
1. FX pair correlations are typically 0.5-0.7 within currency families (EUR/USD long ⊥ GBP/USD long is usually NOT independent; both are USD short).
2. Diversification-aware multi-pick (limit one pick per currency family) would likely outperform naive top-K.
3. Real trading position-size budget: K simultaneous picks share the risk budget; naive top-K backtest assumes K-fold capital.

**Implementation cost**: ~1 day:
- Modify `_eval_fold` SELECTOR loop to argpartition top-K instead of argmax
- Aggregate PnL across K picks per bar (sum, with optional position-size scaling)
- Add `--top-k` CLI flag (default 1 = current behavior)
- Add `--diversify-by-currency` flag for the diversification-aware variant
- Run 20-pair eval sweep over K ∈ {1, 2, 3, 5}, with and without diversification

### 6.2 Option B: LSTM / alternative model class

If Option C also fails, the calibration ceiling is structural to the problem (TA features + triple-barrier label + LightGBM). A model-class change is then justified:
- **LSTM / Transformer**: time-series-aware models may catch sequential patterns LGBM misses
- **Alternative labels**: return-based (regression) instead of TB classification
- **Alternative features**: orderbook-derived, volatility-clustering, fractal dimension

Option B is bigger scope (3-5 days for an MVP, longer for proper validation). Defer until Option C verdict.

### 6.3 Recommended sequencing

1. **Phase 9.X — Option C kickoff design memo** (next, 0.5 days)
2. **Phase 9.X — Option C implementation + 20-pair eval** (1 day)
3. **Phase 9.X — Option C closure**:
   - GO: production toggle wiring + Phase 9.14 paper trading
   - PARTIAL GO with high ρ: try diversify-by-currency variant
   - NO ADOPT: pivot to Option B
4. **Phase 9.X — Option B kickoff** (only if Option C fails)

Phase 9.11 (3+ yr robustness) remains BLOCKED on Sharpe ≥ 0.20.

---

## 7. Cumulative path through Phase 9.10–9.17b

```
v3 (mid label, 1pip):            Sharpe -0.076  NO-GO
v5 (bid/ask label):              Sharpe +0.160  SOFT GO  ★ DECISIVE
v8 (C-3 kill switches):          Sharpe +0.177  SOFT GO+
v9-20p (20 pairs):               Sharpe +0.160  PnL +20.1% vs v5  ★ Phase 9.16 (production default)
v11 (+CSI):                      Sharpe +0.143  PnL -15% vs 20p   ✗ rejected
v12 bucketed (H-1):              Sharpe +0.127  PnL -19%          ✗ Phase 9.18 NO ADOPT
v12 bucketed+partial (H-2):      Sharpe -0.025  PnL -116%         ✗ Phase 9.18 NO ADOPT
v13 lgbm+mr (t=0.0):             Sharpe +0.053  PnL +52%, ρ=0.317 ✗ Phase 9.17 NO ADOPT
v13 lgbm+mr (t=0.3):             Sharpe +0.055  PnL +46%          ✗ Phase 9.17b sweep (this)
v13 lgbm+mr (t=0.5):             Sharpe +0.058  PnL +40%          ✗ Phase 9.17b sweep (this)
```

---

## 8. Notes for future-me

1. **Threshold filtering on rule-based strategies is a weak lever.** The confidence distribution of combined-AND strategies (MR=RSI∧BB) saturates fast — when both indicators are at extremes, both confidences hit 0.5+. So a threshold of 0.5 only filters bars where neither indicator is strong, and those are already a small fraction. To get meaningful trade-rate cuts, you need threshold > 0.7, which causes trade-volume collapse.

2. **The "confidence ≠ hit-rate" finding generalizes.** Phase 9.18 found this for LightGBM (predicting via predict_proba). Phase 9.17b confirms it for rule-based strategies (RSI/BB combined-AND). It's likely a property of any signal that's a function of TA features on the same OHLC stream — the features carry the same predictive ceiling regardless of the modeling approach.

3. **The next promising lever is the SELECTOR rule, not the strategy generator.** All Phase 9.13–9.17b changes modified what feeds INTO the SELECTOR (features, exit policies, more strategies, threshold filters). They all hit the same Sharpe ceiling because the SELECTOR's "1 pick per bar" rule caps the trade rate. Top-K SELECTOR is the first lever we haven't tried that touches the RULE itself.

4. **Don't add more strategies before fixing the SELECTOR.** Adding a third or fourth strategy (e.g., Phase 9.17 Tier 2: news fade, carry overlay) won't help if SELECTOR can only pick one per bar — they'll just compete for the same slot.

5. **MR vs BO anti-correlation is still real and exploitable.** ρ(mr, bo) = -0.669 at t=0.5 (-0.582 at t=0.0). If multi-pick allows simultaneous MR + BO trades on different pairs/regimes, the diversification benefit could materialize.

6. **Per-trade EV gap is the binding constraint, not trade volume.** This memo's Section 5 finding is the most important: filtering low-conf MR trades didn't lift per-trade EV materially (0.064 → 0.077 pip/trade across the threshold sweep). The remaining MR trades have only marginally better EV than the filtered ones. **The strategy class itself produces low-EV trades regardless of confidence value.**

---

## 9. Commit trail

```
c971b4f  PR #211  I-1 confidence_threshold post-filter (MR/BO + v13 helpers + CLI)
<TBD>    PR #???  I-2 this closure memo
```
