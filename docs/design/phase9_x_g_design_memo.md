# Phase 9.X-G Design Memo — Portfolio-Optimized Top-K SELECTOR

**Status:** kickoff. Implementation pending.
**Date:** 2026-04-26.
**Anchor:** Phase 9.X-E v19 causal +mtf K=3 SELECTOR — Sharpe 0.158 / PnL 11,414 / DD%PnL 2.1%.
**Goal:** crack the Sharpe 0.20 ceiling that Phases 9.17/9.17b/9.19/9.X-A/9.X-C/9.X-D all bounced off.

---

## Hypothesis

Phase 9.19 (Top-K) showed K=2 lifted PnL +25% but **did not deliver the sqrt(K) Sharpe lift** that orthogonal sources should produce. Closure verdict: "pairs are systemically correlated."

That verdict assumed the SELECTOR's K picks are correlated **because pairs are correlated**. But naive Top-K just sorts by confidence and takes the top K — it has no awareness of pairwise correlation between the picks themselves. Two USD-cluster pairs (e.g. EUR/USD long + GBP/USD long) end up co-selected exactly when USD weakens.

If we **explicitly de-correlate the picks** (e.g. require pairwise correlation < ρ_max between selected trades), the surviving signals should be more independent, and Sharpe should scale closer to sqrt(K).

The Phase 9.X-B amendment finding (causal +vol K=3 Sharpe 0.160 ≈ +mtf 0.158) reinforces that we're at a structural ceiling under uncorrelated picks. Lever F (portfolio optimization) is the unexplored axis.

---

## Approach — three options

| Option | Description | Pros | Cons |
| ---    | ---         | ---  | ---  |
| **A. Greedy de-correlation** | Sort by conf; iteratively pick next-best with corr < ρ_max vs already-picked | Simple, robust to noisy correlation | Doesn't optimize globally |
| B. Mean-Variance (Markowitz) | Solve weight allocation under risk budget | Theoretically optimal | Notoriously unstable on noisy covariance, requires regularization |
| C. Hierarchical Risk Parity | Cluster candidates by corr, allocate within & between | More robust than B in low-data regimes | More complex, less interpretable |

**Decision: start with Option A.** If A delivers material lift, layer in B/C as second iteration. If A fails, revisit assumptions before adding complexity.

---

## Implementation plan — `scripts/compare_multipair_v20_portfolio.py`

### Inputs
Clone of `scripts/compare_multipair_v19_causal.py` (lookahead-fixed). Same load/feature/train pipeline; only the SELECTOR rule differs.

### Correlation computation
- Per-bar rolling pairwise Pearson of last-N bar returns (default N=100 m5 bars = ~8 hours).
- Computed across the full 20-pair universe before each SELECTOR call.
- Causal: rolls only over past returns up to (but not including) the current bar.

### Greedy de-correlation algorithm

```
candidates = sorted_by_confidence(all_pair_signals, descending)
selected = []
for c in candidates:
    if len(selected) == K:
        break
    if all(abs(corr(c.pair, s.pair)) < rho_max for s in selected):
        selected.append(c)
```

Fallback: if fewer than K survive the correlation filter, the bar takes whatever count fits (no padding with correlated picks).

### CLI surface
```
--top-ks 2,3,5
--rho-max-list 0.3,0.4,0.5,0.6
--corr-window 100
--ensemble-cells lgbm_only            # focus only on lgbm baseline this phase
```

### Metrics extension
- Existing: Sharpe, PnL, DD%PnL, MaxRho, Trades
- New: `avg_realized_rho` — mean pairwise correlation of trades that actually fired in each bar (validates that the filter worked)
- New: `picks_per_bar_avg` — confirms that fewer than K survive when ρ_max is tight

---

## Verdict gates

| Verdict | Condition |
| ---     | ---       |
| GO         | Sharpe ≥ 0.18 AND PnL ≥ 1.10× anchor AND DD%PnL ≤ 5% |
| PARTIAL GO | Sharpe ≥ 0.158 (anchor) — at least matches |
| **STRETCH GO** | Sharpe ≥ 0.20 — cracks Phase 9.11 robustness gate |
| NO ADOPT | Sharpe < 0.158 |

---

## Calibration prior

Drawing on the 5 prior phases that hit the Sharpe ceiling:

- 50% — NO ADOPT or PARTIAL GO (greedy too naive; Markowitz needed)
- 30% — PARTIAL GO at K=2 with ρ_max=0.4 (modest lift)
- **15% — STRETCH GO at K=3 with ρ_max=0.4 (cracks 9.11 gate)** ★ best case
- 5% — full STRETCH GO at K=5 (Sharpe ≥ 0.22, decisively)

If STRETCH GO hits, this is the **first phase to break the 0.158-0.174 ceiling structurally**, not via lookahead inflation. Phase 9.11 unblocked. Production wiring would target a leverage of 1.5-2x to capture the lift as monthly return.

---

## Why this might *not* work

- Pairs may be correlated **conditionally on the model's confidence**. If the model fires high-confidence signals on pair A and B precisely when A and B are about to move together (USD-cluster macro event), then de-correlation filter strips out the very signals that have the highest EV.
- 100-bar rolling correlation is noisy. ρ_max=0.3 may be unattainable in practice.
- If the filter is too aggressive, picks_per_bar collapses to 1 → effectively K=1 → no lift.

These are testable in eval; the multi-cell sweep is designed to find a sweet spot if one exists.

---

## Sequencing

1. **Now**: this design memo merged. Implementation kicks off in parallel.
2. v20 script (~3 hours dev).
3. 20-pair eval ×4 cells (K × ρ_max combinations) — runtime ~1 hour each, total ~30-60 min wall on this hardware in serial. Run all 4 cells in single eval.
4. Closure verdict + memo (~1 hour).
5. If GO/STRETCH GO: PR with v20 script + closure memo + production-wiring plan in `docs/design/phase9_x_g_live_deploy_addendum.md`.
6. If NO ADOPT: closure-only PR; revisit Markowitz / HRP in Phase 9.X-G2 if lever budget permits.

---

## Files

- This memo: `docs/design/phase9_x_g_design_memo.md`
- Implementation: `scripts/compare_multipair_v20_portfolio.py` (new)
- Eval logs: `artifacts/phase9_x_g_portfolio.log` (new)
- Closure: `docs/design/phase9_x_g_closure_memo.md` (after eval)

Master tip when authored: fd1d2f1 (after PR #224, #225, #226 merged).
