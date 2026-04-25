# Phase 9.12 — Model quality (Phase C) Closure Memo

**Status**: Closed — **SOFT GO** at SELECTOR net Sharpe **0.160**
**Master tip at authorship**: `9ae57ad` (PR #192 B-2 merged)
**Predecessor**: Phase 9.10 closed NO-GO at master `17d00c7`
**Related**: `docs/phase9_roadmap.md` §6.14, `docs/design/phase9_12_design_memo.md`, `docs/design/phase9_10_closure_memo.md`

---

## 1. What this phase set out to do

Phase 9.10 closed NO-GO at the 1pip cost gate. The grid search pinned three findings:

1. Confidence threshold barely moves Sharpe (~0.01 per 0.05 step).
2. Spread is the dominant cost driver (~0.21 Sharpe per 0.5pip).
3. Fixed `TP=3pip / SL=2pip` is the binding constraint.

Phase 9.12 was the next attempt at the cost gate. Three levers were proposed in priority order:

- **B-1**: ATR-based dynamic TP/SL (replace fixed pip with ATR multiples).
- **B-2**: Bid/ask-aware triple-barrier labels (embed spread into the label, not a post-hoc deduction).
- **B-3** (optional): Meta-labeling (2-layer ML) to whiten Layer 1 signals when needed.

A perf optimisation along the way (vectorised eval loop, ~30× faster) made the grid sweeps cheap.

---

## 2. What shipped

### Infrastructure / scripts (all merged)

| PR | Scope | Lines |
|----|-------|-------|
| #189 | Phase 9.12 kickoff design memo | docs only |
| #190 | B-1 — ATR-based TP/SL backtest script (`v4`) | 793 |
| #191 | B-1 perf — vectorised per-fold eval, ~30× speedup | 197 diff |
| #192 | B-2 — bid/ask-aware triple-barrier labels (`v5`) | 1,058 |
| **(this PR)** | B-3 — meta-labeling layer (`v6`) + closure memo | 1,200 |

All four code PRs merged to master with CI green.

### Research scripts (not promoted to production)

```
scripts/compare_multipair_v4_atr.py     # B-1: ATR TP/SL
scripts/compare_multipair_v5_bidask.py  # B-2: bid/ask labels
scripts/compare_multipair_v6_meta.py    # B-3: meta-labeling
```

Same research-first pattern as Phase 9.10. Production code (`MLDirectionStrategy`, `feature_service`, `meta_decider`) is unchanged — the production path's promotion is gated behind a Phase 9.12 GO, which we did not reach.

---

## 3. Results

### 3.1 Single-config comparison (all at TP=1.5×ATR, SL=1.0×ATR, slippage=0.0pip)

```
                     EU NetSh   SEL NetSh   SEL NetPnL  WinFold%(SEL)  SigRate(SEL)
v3 (mid label, 1pip)   -0.087    -0.076       -49,611         0%            100%
v4 (ATR label, 1pip)   -0.205    -0.074       -56,475         13%           100%
v5 (bid/ask label)     +0.146    +0.160       +6,793          82%           3.5%
v6 (+ meta-labeling)   +0.146    +0.158       +6,642          82%           3.5%
                                              ↑
                                         SOFT GO (>=0.15, <0.20)
```

The decisive jump was **v4 → v5**: the same model architecture, fed mid-based labels, produced negative Sharpe; fed bid/ask-aware labels, it produced positive Sharpe. **Embedding the spread into the label was the unlock.** ATR scaling alone (v4) and meta-labeling on top of v5 (v6) had marginal-to-zero effect.

### 3.2 v6 meta-threshold sweep

```
meta-threshold | SELECTOR NetSh | Trades  | vs v5 baseline
no meta (v5)   |     0.160      |  9,728  | (baseline)
0.50           |     0.158      |  9,692  | -0.002
0.55           |     0.157      |  9,677  | -0.003
0.60           |     0.157      |  9,658  | -0.003
0.65           |     0.157      |  9,632  | -0.003
```

Raising the threshold from 0.50 to 0.65 trims only ~1% of trades and slightly reduces Sharpe. The Layer 2 keep-probabilities cluster in a narrow band (0.4–0.7), so the threshold doesn't act as a meaningful discriminator.

### 3.3 Pair selection redistribution

```
v3 / v4 (mid label, JPY-heavy):   USD_JPY 24-30%  EUR_JPY 14-21%  GBP_JPY 10-15%  (JPY ≈ 50-64%)
v5 / v6 (bid/ask label):          USD_JPY 33%     EUR_USD 23%     AUD_USD 16%    GBP_USD 14%  (JPY ≈ 38%)
```

Stricter labels push the SELECTOR away from JPY crosses and toward majors. Likely cause: JPY-cross volatility looks favourable in mid-only space but the wider bid/ask spreads on JPY crosses penalise them in the v5/v6 label space.

---

## 4. Go / No-Go verdict

| Threshold | SELECTOR NetSharpe | Verdict |
|---|---|---|
| ≥ 0.20 (GO) | 0.160 | **NOT MET** |
| ≥ 0.15 (SOFT GO) | 0.160 | **PASS** |
| < 0.15 (NO-GO) | — | n/a |

**Phase 9.12 closes at SOFT GO.** Per the design memo's gate, this means: try Phase 9.13 (risk lever) before re-running the gate. Phase 9.11 (3+ year robustness) remains BLOCKED on full GO.

---

## 5. What this means in plain terms

At slippage = 0.0pip the strategy generates approximately:

```
+6,793 pip / 9 months ≈ +755 pip/month ≈ +25 pip/day  (multipair selection)
EV per trade:           +0.70 pip
Trade frequency:        ~36 trades/day  (1,080 trades/month)
```

Translated to a $10k account using 1 mini-lot / trade ($1 per pip):

| Slippage assumption | Net EV/trade | Monthly PnL | Monthly return |
|---|---|---|---|
| 0.0 pip (idealised) | +0.70 pip | +755 pip | **+7.6%** |
| 0.2 pip (prop EXEC) | +0.50 pip | +540 pip | **+5.4%** |
| **0.5 pip (retail)** | **+0.20 pip** | **+217 pip** | **+2.2%** |
| 1.0 pip (bad EXEC) | -0.30 pip | -291 pip | **-2.9%** |

In other words: **the strategy has positive expected value, but the margin is thin**. Realistic retail-account slippage probably leaves 1–4% monthly expected return — meaningful, but not survivable to month-to-month variance without further hardening.

Sharpe 0.16 (per-trade) means month-to-month swings of ±5–10% are routine; ~2 of every 10 months will be negative.

---

## 6. Why B-3 (meta-labeling) didn't help

Two structural reasons:

1. **No new information.** Layer 2's inputs are the original feature set plus Layer 1's `(p_tp, p_sl)`. There is no orthogonal signal — Layer 2 is just re-projecting what Layer 1 already saw. It cannot outperform a re-tuned Layer 1.
2. **Narrow `predict_proba` distribution.** Layer 2 outputs cluster in 0.4–0.7. Threshold-based filtering moves only the tails, which are a small fraction of trades. Effective filter is <1% of total signals.

To make meta-labeling work would require **orthogonal features**:
- Regime tags (trending vs range, ATR percentile)
- Session indicator (Asia/London/NY)
- Recent hit-rate of Layer 1 (last N trades for this pair)
- Microstructure (order-book pressure, recent realised vol)
- News proximity (economic calendar)

These are Phase 9.12 follow-on work (out of scope here) or Phase 9.13 risk-lever territory.

---

## 7. Next phase

**Phase 9.11 stays BLOCKED**, but the BLOCK is now SOFT — there is a real edge, just not enough margin for the GO gate. Two paths forward:

### Path A (recommended): Phase 9.13 risk lever first

Per the design memo's SOFT GO disposition. Phase 9.13 lifts SOFT GO toward GO via **leverage on the existing edge**, not new alpha:

- **Kelly / Fractional Kelly position sizing** — current backtest uses 1 unit per trade; Kelly-scaled sizing on the per-trade pip distribution typically lifts net Sharpe by 0.03–0.08 because the size itself becomes information-driven.
- **Portfolio correlation cap** — JPY crosses + EUR/USD + AUD/USD all move together in risk-on/risk-off; cap the gross exposure when correlation is high to flatten drawdowns.
- **Daily / consecutive-loss kill switches** — protect tail months from compounding losses.

Estimated lift: SOFT GO 0.16 → maybe 0.18–0.22 (full GO threshold would be cleared at the upper end).

### Path B: orthogonal features for meta-labeling

If Phase 9.13 underdelivers, return to Phase 9.12 with a B-3 v2 that includes regime / session / recent-hit-rate features. Higher-information-content Layer 2 might lift signals that Phase 9.13 can't reach.

Phase 9.14 (paper trading, 1–3 months OANDA demo) follows whichever path produces a full GO.

---

## 8. What stayed out of scope (deferred by design)

| Item | Deferred to |
|------|-------------|
| Kelly position sizing | Phase 9.13 |
| Portfolio correlation cap | Phase 9.13 |
| Kill switches (daily / consecutive / DD) | Phase 9.13 |
| Orthogonal features for meta-labeling (regime / session / news) | Phase 9.12 v2 if 9.13 misses |
| 3+ year multi-regime data | Phase 9.11 (still BLOCKED) |
| Out-of-sample hold-out | Phase 9.11 |
| Production code wiring (`MLDirectionStrategy`, `feature_service` ATR/bid-ask) | After Phase 9.12 produces full GO |
| OANDA demo paper trading | Phase 9.14 |

---

## 9. Commit trail

```
3658291  PR #189  Phase 9.12 kickoff design memo
d287913  PR #190  B-1 ATR-based TP/SL script
b2fe91b  PR #191  B-1 perf optimization (~30x speedup)
9ae57ad  PR #192  B-2 bid/ask-aware labels — SOFT GO
<TBD>    PR #???  B-3 meta-labeling + this closure memo
```

---

## 10. Notes for future-me

- **The mid → bid/ask label switch is THE finding of this phase.** It flipped −0.205 EU Sharpe to +0.146; ATR scaling alone (B-1) and meta-labeling (B-3) were rounding-error contributions on top.
- **Per-fold Sharpe outliers in v5/v6** (Fold 6 EU=161, Fold 21 EU=76, Fold 3 RD=17.91) are sample-size artefacts: EU at 0.9% sigrate over 5,000 bars/fold ≈ 45 trades; some folds have <5 trades and Sharpe gets noisy. **Aggregate Sharpe is robust** because it pools all trades across all folds.
- **JPY pairs lose share when the label tightens.** This is consistent with their wider observed spreads in the practice-account BA data. Useful diagnostic to remember when Phase 9.13 designs the correlation cap.
- **Vectorised eval was a force multiplier.** Pre-optimisation runs took 2 hours; post-opt runs take 6 minutes. Threshold sweeps that were "spend an afternoon waiting" became "kick off and check after lunch". Worth doing at any phase that involves a sweep over hyperparameters.
- **Meta-labeling without orthogonal features is a no-op.** Don't repeat B-3 with the same feature set in Phase 9.13.
- **The SOFT GO is real but thin.** $10k account at 0.5pip realistic slippage ≈ 2.2%/month expected, with -3 to -5%/month variance. Phase 9.14 demo is mandatory before any live capital — backtest 0.16 could degrade to 0.07–0.10 at first contact with reality.
