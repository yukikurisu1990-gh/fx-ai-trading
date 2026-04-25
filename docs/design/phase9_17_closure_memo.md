# Phase 9.17 — Multi-strategy ensemble (Phase I) Closure Memo

**Status**: Closed — **NO ADOPT** (symmetric v9 20-pair bundle remains production default)
**Master tip at authorship**: `32d2e7f` (Phase 9.17 G-3 merged) + this PR
**Predecessor**: Phase 9.18 closed NO ADOPT 2026-04-26 at master `ed71dd9`
**Related**: `docs/design/phase9_17_design_memo.md`, `docs/design/phase9_18_closure_memo.md`, `docs/phase9_roadmap.md` §6.19

---

## 1. What this phase set out to do

Phase 9.13–9.18 confirmed that the single-strategy LightGBM stack has a Sharpe ceiling of 0.143–0.177 that cannot be broken by:

- Layer 1 features (Phase 9.4–9.9): SELECTOR plateau
- Risk multipliers / kill switches (Phase 9.13 C-3): +0.017 lift, then flat
- Pair-universe expansion (Phase 9.16): +20% PnL, Sharpe flat at 0.160
- Per-trade exit engineering (Phase 9.18): regression on both bucketed TP/SL and partial exits

Phase 9.17 attacked the **orthogonal-alpha axis** — adding signal sources from a *different family* whose correlation with the LightGBM strategy is low enough that the ensemble Sharpe rises by the textbook formula `Sharpe(A+B) = (S_A+S_B) / sqrt(2(1+ρ))`.

**Tier 1 candidates implemented:**
- **MeanReversionStrategy (G-1)**: combined-AND of RSI ≤ 30 + bb_pct_b ≤ 0.10 (long; mirror for short)
- **BreakoutStrategy (G-2)**: bb-band break + EMA-trend confirmation

The kickoff design memo predicted **PnL +10–20%, Sharpe +0.02–0.04** at ρ ≤ 0.4 — but with an explicit honesty disclosure (§9.3) that Phase 9.4 TA strategies were authored without orthogonality target and may share too much with LightGBM's MACD/EMA/RSI features.

---

## 2. What shipped

| PR | Scope | Result |
|----|-------|--------|
| #206 | G-0 kickoff design memo | docs only |
| #207 | G-1 MeanReversionStrategy + 25 tests | implementation |
| #208 | G-2 BreakoutStrategy + 22 tests | implementation |
| #209 | G-3 `compare_multipair_v13_ensemble.py` + 23 tests | 4-cell internal sweep + correlation matrix |
| **(this PR)** | G-4 20-pair eval + closure memo | NO ADOPT |

---

## 3. Results

### 3.1 20-pair 4-cell sweep (full Phase 9.16 universe, 39-fold walk-forward)

```
                 Sharpe   PnL(pip)    MaxDD    DD%PnL   WinFold%   SigRate   Trades       MaxRho
lgbm_only        0.160     8,157.2    203.4     2.5%      90%       4.5%    12,461        —
lgbm+mr          0.053    12,360.4    177.9     1.4%      95%      69.8%   192,832     0.317
lgbm+bo          0.035     7,843.4    197.0     2.5%      95%      65.9%   181,927     0.206
lgbm+mr+bo       0.036     9,023.3    247.9     2.7%      97%      80.0%   220,839     0.582
```

**lgbm_only exactly reproduces Phase 9.16 v9 baseline** (Sharpe 0.160, PnL 8,157.2, DD%PnL 2.5%) — validates the v13 script.

### 3.2 SELECTOR strategy share (per cell)

```
Cell           lgbm     mr       bo
lgbm+mr         4.3%   95.7%      —
lgbm+bo         4.3%      —     95.7%
lgbm+mr+bo      3.0%   37.9%   59.1%
```

In every multi-strategy cell, **LightGBM is picked < 5% of the time**. MR / BO dominate the SELECTOR because their confidence outputs are not threshold-filtered the way LightGBM signals are.

### 3.3 Inter-strategy correlation (Pearson on per-bar mean gross PnL)

```
                lgbm        mr        bo
lgbm           +1.000    +0.317   -0.206
mr             +0.317    +1.000   -0.582
bo             -0.206    -0.582   +1.000
```

**Strategies ARE orthogonal at scale** — all cross-correlations |ρ| ≤ 0.582. The MR/BO pair is naturally anti-correlated (band-touch fade vs band-break follow). The 2-pair smoke run had inflated correlations (0.726 / 0.548 / 0.870) because of pair-similarity (EUR_USD + GBP_USD); the 20-pair universe properly diluted them.

---

## 4. Verdict — NO ADOPT

| Cell | PnL ratio | DD%PnL | Sharpe | Max ρ | Gate result |
|------|-----------|--------|--------|-------|-------------|
| lgbm+mr | 1.52× ✓ | 1.4% ✓ | 0.053 ✗ (< 0.160) | 0.317 ✓ | **NO ADOPT** (Sharpe < baseline) |
| lgbm+bo | 0.96× ✗ | 2.5% ✓ | 0.035 ✗ | 0.206 ✓ | **NO ADOPT** (PnL < baseline) |
| lgbm+mr+bo | 1.11× ✓ | 2.7% ✓ | 0.036 ✗ | 0.582 ✗ | **NO ADOPT** (Sharpe < baseline, ρ in 0.4–0.6 band) |

**No cell clears any gate.** The PARTIAL GO gate requires Sharpe ≥ baseline; all ensemble cells fail this. STRETCH GO requires Sharpe ≥ 0.18; none reach it. Production default unchanged: **20-pair v9 symmetric spread bundle (Sharpe 0.160, PnL 8,157, DD%PnL 2.5%)**.

---

## 5. Why orthogonal strategies failed differently than predicted

The design memo's failure mode prediction was: **"strategies will be highly correlated with LightGBM (ρ ≈ 0.7+) because LGBM uses the same features."** The 2-pair smoke run apparently confirmed this (ρ = 0.726 / 0.548 / 0.870).

**The 20-pair full eval revealed a different failure mode:**

1. **Strategies ARE adequately orthogonal** at scale (ρ ≤ 0.6 across all cell pairs).
2. **But the trade-rate explodes 15×** (12,461 → 192,832 in lgbm+mr) because MR/BO have no confidence-threshold filter analogous to LightGBM's `--conf-threshold 0.50`.
3. **SELECTOR dominated by MR/BO** — they get picked ~95% of the time; LightGBM falls to < 5%.
4. **Per-trade EV dilutes** — MR/BO take *every* setup matching their rule, including weak ones. Each individual trade has lower EV than a typical LGBM trade.
5. **Net result**: PnL grows (more trades × small EV), variance grows faster, **Sharpe collapses** (0.160 → 0.05).

This is **not the failure mode the design memo anticipated.** The orthogonality thesis is supported; the SELECTOR-budget thesis is not.

### 5.1 Strategy share-of-picks vs feature dominance

In a properly-balanced ensemble, each strategy should pick proportionally to its EV-quality. In Phase 9.17 v13:

| Cell | LGBM share | Reason |
|------|-----------|--------|
| lgbm+mr | 4.3% | MR confidence saturates at 1.0 on extreme bands; no threshold filter |
| lgbm+bo | 4.3% | BO confidence ≥ LGBM whenever 0.5×ATR break occurs |
| lgbm+mr+bo | 3.0% | Both MR and BO above LGBM most of the time |

The SELECTOR's `argmax(confidence)` rule is broken by MR/BO's unfiltered confidence values. LightGBM's `--conf-threshold 0.50` filter applies only to LGBM, leaving it at a structural disadvantage.

---

## 6. Cumulative path through Phase 9.10–9.18

```
v3 (mid label, 1pip):            Sharpe -0.076  NO-GO
v5 (bid/ask label):              Sharpe +0.160  SOFT GO  ★ DECISIVE
v8 (C-3 kill switches):          Sharpe +0.177  SOFT GO+
v9 (10p, +spread):               Sharpe +0.152  PnL +13%, DD -17%        ★ Phase 9.15
v10 (10p, +spread+RH):           Sharpe +0.143  PnL +15.5%               ★ Phase 9.15 opt-in
v9-20p (20 pairs):               Sharpe +0.160  PnL +20.1% vs v5         ★ Phase 9.16 (production default)
v11 (+CSI):                      Sharpe +0.143  PnL -15% vs 20p          ✗ rejected
v12 symmetric (sanity):          Sharpe +0.160  matches v9-20p exactly   ★ Phase 9.18 baseline confirmed
v12 bucketed (H-1):              Sharpe +0.127  PnL -19% vs symmetric    ✗ NO ADOPT
v12 bucketed+partial (H-2):      Sharpe -0.025  PnL -116% vs symmetric   ✗ NO ADOPT
v13 lgbm_only:                   Sharpe +0.160  matches v9-20p exactly   ★ Phase 9.17 baseline confirmed
v13 lgbm+mr:                     Sharpe +0.053  PnL +52%, ρ=0.317        ✗ NO ADOPT (Sharpe collapse)
v13 lgbm+bo:                     Sharpe +0.035  PnL -4%,  ρ=0.206        ✗ NO ADOPT
v13 lgbm+mr+bo:                  Sharpe +0.036  PnL +11%, ρ=0.582        ✗ NO ADOPT
```

---

## 7. What's next

Phase 9.17 closes the **orthogonal-alpha thread via rule-based strategies**. Despite achieving the orthogonality target (ρ ≤ 0.4 for lgbm+mr / lgbm+bo), the trade-rate explosion negates the Sharpe lift.

Two natural extensions exist before pivoting to model-class change:

**Option A (Phase 9.17b — narrower scope)**: add a confidence threshold to MR/BO (e.g. require conf ≥ 0.5 just like LightGBM). This would cut the trade rate dramatically. The risk: at conf ≥ 0.5, MR fires only at *both* RSI ≤ 15 AND bb_pct_b ≤ 0.05 simultaneously — a very rare setup that may not have enough trade volume to matter.

**Option B (model-class change)**: pivot to alternative model class (LSTM, transformer, alternative labels). The Sharpe ceiling is structurally tied to LightGBM's calibration — confirmed by both 9.18 (confidence ≠ hit-rate) and 9.17 (orthogonality alone insufficient).

**Recommendation**: Option A is a fast (~1 day) experiment with documented downside (low trade volume). Option B is the structural fix but requires significant scope. Try A first; if Sharpe still collapses, pivot to B.

Phase 9.11 (3+ year robustness) remains **BLOCKED** on Sharpe ≥ 0.20 gate.

G-5 (production runtime wiring) is **not triggered** — there's nothing to wire.

---

## 8. Notes for future-me

1. **The 2-pair smoke was misleading on correlation.** With only EUR_USD + GBP_USD (highly co-moving), all strategy pairs showed ρ ≥ 0.5. The 20-pair universe (which includes JPY pairs, CHF crosses, AUD crosses) properly diluted correlations. Lesson: smoke-run correlations on 2 pairs are a lower-bound estimate of orthogonality, not an upper bound. Always run the full universe before declaring "ρ too high."

2. **SELECTOR's confidence-based picker is a structural weakness.** The picker assumes confidence is calibrated across strategies. LightGBM's confidence is *post-threshold-filtered* (conf ≥ 0.50); MR/BO's is not. This is an apples-to-oranges comparison in the picker. Future ensemble work should either (a) impose a uniform threshold on all strategies, (b) use Sharpe-weighted picking instead of confidence-weighted, or (c) use *probability-of-improvement* (Bayesian).

3. **Trade-rate is the binding constraint, not orthogonality.** If you achieve ρ < 0.4 but trade rate goes 15× higher, Sharpe will fall by sqrt(15) ≈ 3.9× from variance growth alone. The ensemble math `Sharpe(A+B) = (S_A+S_B)/sqrt(2(1+ρ))` assumes each strategy's individual Sharpe is the same; if MR/BO's per-trade Sharpe is 1/15th of LGBM's, the formula doesn't help.

4. **PnL vs Sharpe trade-off is real.** Phase 9.17 cells produce **higher PnL** than the baseline (lgbm+mr: 1.52× = +4,200 pip extra) while collapsing Sharpe. If the user's actual objective were absolute pip count regardless of variance, lgbm+mr would be a GO. Phase 9.17's gate explicitly requires Sharpe ≥ baseline, so the PnL lift doesn't save it.

5. **MR/BO are anti-correlated** (ρ = -0.582). This is real and useful: band-touch fade vs band-break follow are structurally opposite. A future Phase that combines them with confidence thresholds (Option A above) might get a clean lift if the trade rate is contained.

6. **Per-strategy verdict: which one is the better candidate?**
   - **MR > BO**: lgbm+mr has PnL 1.52× and ρ 0.317 (clears 0.4 gate). lgbm+bo has PnL 0.96× and ρ 0.206. MR has more upside potential if the trade-rate problem is fixed.

---

## 9. Commit trail

```
111a755  PR #206  G-0 Phase 9.17 kickoff design memo
1d9433c  PR #207  G-1 MeanReversionStrategy + 25 tests
131b772  PR #208  G-2 BreakoutStrategy + 22 tests
32d2e7f  PR #209  G-3 compare_multipair_v13_ensemble.py + 23 tests
<TBD>    PR #???  G-4 this closure memo
```
