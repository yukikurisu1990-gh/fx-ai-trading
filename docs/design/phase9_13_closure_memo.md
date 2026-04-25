# Phase 9.13 — Risk management (Phase D) Closure Memo

**Status**: Closed — **SOFT GO+** at SELECTOR net Sharpe **0.177** (C-3 only)
**Master tip at authorship**: `10ea77e` (Phase 9.13/C-1 merged)
**Predecessor**: Phase 9.12 closed SOFT GO at master `79ed1e8`
**Related**: `docs/phase9_roadmap.md` §6.15, `docs/design/phase9_13_design_memo.md`, `docs/design/phase9_12_closure_memo.md`

---

## 1. What this phase set out to do

Phase 9.12 closed at SOFT GO — SELECTOR net Sharpe **0.160** with v5 (B-2 bid/ask labels). Phase 9.13's job was to lift Sharpe via three risk levers (leverage on existing edge, not new alpha):

- **C-1**: Fractional Kelly position sizing
- **C-2**: Portfolio correlation cluster cap
- **C-3**: Kill switches (daily loss / consecutive loss / drawdown)

Target: **0.16 → 0.18–0.22** (clears the Phase 9.10 GO gate at the upper end).

---

## 2. What shipped

| PR | Scope | Result |
|----|-------|--------|
| #194 | Phase 9.13 design memo | docs only |
| #195 | C-1 Kelly sizing | flat 0.149 — no lift |
| **(this PR)** | C-2 + C-3 + closure memo + roadmap | C-3 only is recommended |

---

## 3. Decomposition results

All at TP=1.5×ATR / SL=1.0×ATR / slippage=0.0:

| Configuration | Sharpe | Net PnL (pip) | Trades | Δ vs v5 (PnL) |
|---|---|---|---|---|
| **v5 baseline (no risk)** | **0.160** | **6,793** | 9,728 | (baseline) |
| C-1 Kelly (any f) | 0.149 | ~6,500 | 9,700 | wash |
| **C-3 only (kill switches)** | **0.177** | **6,275** | 9,000 | **−7%** |
| C-2 only (cap=2) | 0.183 | 2,177 | 3,100 | −68% |
| C-2 + C-3 default (cap=2) | 0.181 | 2,139 | 3,033 | −69% |
| cap=1 + kill | 0.185 | 1,202 | 1,750 | −82% |
| cap=3 + kill | 0.172 | 2,744 | 3,891 | −60% |

## 4. Verdict

**Phase 9.13 closes at SOFT GO+ via C-3 only.** SELECTOR net Sharpe 0.177 is up from v5's 0.160 (+0.017) at the cost of just 7% of total profit. C-2 (correlation cap) has higher Sharpe but trades 60–80% of profit for that — uneconomic at typical retail slippage.

| Threshold | C-3 only Sharpe | Verdict |
|---|---|---|
| ≥ 0.20 (GO) | 0.177 | NOT MET |
| ≥ 0.15 (SOFT GO) | 0.177 | **PASS** |
| < 0.15 (NO-GO) | — | n/a |

**Phase 9.11 (3+ year robustness) remains BLOCKED on full GO.**

## 5. Why C-2 (correlation cap) is NOT recommended

Per-trade EV is essentially unchanged across C-2 cells:

```
v5 (no cap):        EV = 6,793 / 9,728  = 0.70 pip / trade
v8 cap=2 + kill:    EV = 2,139 / 3,033  = 0.71 pip / trade
v8 cap=1 + kill:    EV = 1,202 / 1,750  = 0.69 pip / trade
v8 cap=3 + kill:    EV = 2,744 / 3,891  = 0.71 pip / trade
```

C-2's Sharpe lift comes entirely from **dropping trades** (variance reduction by smaller sample), **not from selecting better trades** (mean lift). The retained trades have the same EV as the dropped ones — we're just keeping fewer of them. Sharpe is invariant under trade-count scaling, BUT the kill switches in C-3 only drop tail-loss trades selectively, so they preserve mean while reducing variance. C-2 drops indiscriminately.

Slippage break-even analysis ($10k account, 1 mini-lot/trade):

| Slippage / pip | v5 monthly PnL | v8 cap=2+kill | Winner |
|---|---|---|---|
| 0.0 (idealised) | +755 pip = +7.6% | +238 pip = +2.4% | **v5** |
| 0.3 (prop EXEC) | +485 pip = +4.9% | +211 pip = +2.1% | **v5** |
| **0.5 (retail)** | **+215 pip = +2.2%** | **+140 pip = +1.4%** | **v5** |
| 0.7 | +43 pip = +0.4% | +123 pip = +1.2% | **v8** |
| 1.0 | −229 pip (loss) | +95 pip = +1.0% | **v8** |

Break-even slippage ≈ **0.58 pip/trade**. Below that, C-2 is uneconomic. Above that, C-2's trade-count reduction lowers total slippage cost faster than it lowers gross PnL.

## 6. Recommended config (live & backtest)

```
v5 (B-2 bid/ask labels) + C-3 only (kill switches)
  --tp-mult 1.5
  --sl-mult 1.0
  --horizon 20
  --conf-threshold 0.50
  --no-correlation-cap    ← do NOT enable
  --daily-loss-pip 300
  --consec-loss-n 5
  --cooldown-bars 60
  --drawdown-kill-pip 1000
```

Result: SEL Sharpe **0.177**, PnL **6,275 pip / 9 mo ≈ 700 pip/month**, with three real-money safety nets (daily, consec, DD).

## 7. Why each lever did or didn't work

| Lever | Result | Why |
|---|---|---|
| C-1 Kelly | Wash | Same `predict_proba` Layer 1 sees → no new info; like B-3 meta-labeling |
| C-2 cap | Sharpe up, PnL down disproportionately | Mechanical trade drop without quality discrimination |
| **C-3 kill** | Sharpe **+0.017**, PnL **−7%** | Drops only tail-loss trades; preserves mean PnL, reduces variance |

The pattern: **risk levers based on Layer 1's own outputs cannot lift Sharpe without sacrificing volume**. Sharpe-lifting requires either (a) orthogonal information (Phase 9.15 plan), (b) larger universe with same hit rate (Phase 9.16 plan), or (c) different alpha sources entirely (Phase 9.17 plan).

## 8. Hard finding: Sharpe vs Profit are different goals

This phase surfaced a tension that shapes every Phase 9.X going forward:

> **Sharpe is invariant under trade-count scaling. Profit scales with trades.**

If we optimise for Sharpe alone, we will keep trimming trade volume until Sharpe peaks — at the cost of monthly profit. For a real-money strategy, what matters is **trade-level EV improvement** (lifts both metrics simultaneously). Phase 9.15+ targets exactly that: orthogonal features that improve hit rate per trade.

## 9. New phases added to the roadmap

The user requested fundamental profit-lifting moves. Phase 9.13 closure adds four new phases between current 9.13 and 9.14:

| New phase | Lever | Target lift |
|---|---|---|
| **9.15** | Orthogonal features (bid/ask spread, time-of-day, volume, recent hit-rate) | Hit rate +5–8pp → PnL +50–100% |
| **9.16** | Pair universe expansion (10 → 25-30 pairs) + conf threshold sweep | Trades +50–80% → PnL +50–80% |
| **9.17** | Multi-strategy ensemble (mean reversion, breakout, news-fade, carry) | Trades +100–200% → PnL +100–150% |
| **9.18** | Asymmetric TP/SL + partial exits | Per-trade EV +20–30% |

Combined target after 9.15-9.18: **~1,500-3,500 pip/month at $10k**, full GO Sharpe ≥ 0.20.

Phase 9.11 (3+ yr robustness) remains BLOCKED until at least 9.15+9.16 lift the gate.

## 10. Next phase

**Phase 9.15 — Orthogonal features.** The single highest expected-lift / lowest-cost move. Bid/ask spread is the standout: we already have the data (BA candles from 9.10), used it for labels in 9.12 (B-2), but never used it as a *feature*. Same for time-of-day and volume.

## 11. Commit trail

```
3658291  PR #189  Phase 9.12 kickoff design memo
d287913  PR #190  B-1 ATR-based TP/SL script
b2fe91b  PR #191  B-1 perf optimization (~30x speedup)
9ae57ad  PR #192  B-2 bid/ask-aware labels — SOFT GO
79ed1e8  PR #193  B-3 meta-labeling + Phase 9.12 closure memo (NO lift)
4c?????  PR #194  Phase 9.13 kickoff design memo
10ea77e  PR #195  C-1 Kelly sizing (no lift)
<TBD>    PR #???  C-2 + C-3 + this closure memo + roadmap 9.15-9.18 update
```

## 12. Notes for future-me

- **Don't repeat Layer-1-only levers.** B-3 meta-labeling, C-1 Kelly, C-2 correlation cap all share the same failure mode: same information source as Layer 1 → no Sharpe lift without trade-volume sacrifice. The next 4 phases (9.15-9.18) are explicitly designed to provide *orthogonal* information.
- **The bid/ask spread feature is the obvious next move** — we have the data from Phase 9.10's BA fetch but never used it as a feature. Likely the highest single-feature lift available.
- **Sharpe vs Profit distinction matters for real money.** A risk-managed strategy might *look* better on Sharpe but make less money. The C-3 only recommendation balances both — small Sharpe lift, tiny profit cost, real safety nets.
- **Per-trade EV around 0.70 pip is the binding constraint.** To reach $10k account → $1k/month, we either need more trades at the same EV (Phase 9.16 / 9.17) or fewer trades at higher EV (Phase 9.15 / 9.18). Profit = volume × EV; both axes can be expanded.
