# Phase 9.X-M Design Memo — Dynamic SL/TP Optimization

**Status:** kickoff (design only). Implementation deferred until Phase 9.X-L verdict.
**Date:** 2026-04-27.
**Anchor:** Phase 9.X-E v19 causal +mtf K=3 SELECTOR — Sharpe 0.158.
**Goal:** replace fixed `tp_mult=4.0 / sl_mult=4.0 × ATR` with per-pair (and possibly per-regime) optimal values.

---

## Why this lever

External reviewer ranked this **Rank-5** in `sharpe_improvement_brief.md` §9. Reasoning:

> "fixed ATR×4 is rough. pair / session / regime ごとに最適値が違う可能性が高い."

We have always used `tp_mult=sl_mult=4.0` since Phase 9.10 without justification — it was inherited as a tunable. Different pairs have different vol structures (USD/JPY ≠ AUD/NZD), so a single value is unlikely globally optimal.

## Core hypothesis

For a given pair, there exists `(tp*, sl*)` ∈ R² such that:

- Triple-barrier label distribution is **less degenerate** (closer to balanced 3-way classes)
- Model can extract more signal from the same features
- Per-trade EV improves at the same trade rate

If `(tp*, sl*) = (4, 4)` for all pairs, this is a no-op. We expect divergence: e.g., USD/JPY might be best at (3, 5) (asymmetric, slow trend), AUD/NZD best at (5, 3) (mean-reverting bias). The hypothesis is that **per-pair tuning unlocks 5-15% per-trade Sharpe lift**.

## Approach (3 alternatives)

### Approach A: pre-computed best (tp, sl) per pair (cheapest)

Run the existing v24/v25 backtest with several (tp_mult, sl_mult) combinations as separate evals; record per-pair Sharpe contribution; pick the pair-wise winner; merge into a `_per_pair_sltp` mapping; rerun once.

**Cost:** 4 (combos) + 1 (merged) = 5 evals × 30-50 min ≈ 3-4 hours wall.
**Risk:** in-sample optimization — picking winner on the same data we evaluate.

### Approach B: walk-forward per-pair tuning (per-fold)

On each retrain fold, for each pair, evaluate label-only Sharpe under several (tp, sl); pick the per-pair best; train model under that label config; carry to next test fold.

**Cost:** 16-25× current eval (heavier per fold). ~15+ hours wall.
**Risk:** much heavier compute; per-fold tuning can flip-flop and add variance.

### Approach C: two-stage — global per-pair, then static (recommended for v26)

1. **Stage 1 (one-shot):** on the FIRST 90-day training window only, sweep (tp, sl) ∈ {2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0}² (49 combos) per pair. Pick best `(tp*, sl*)_pair` by training-set net Sharpe.
2. **Stage 2 (entire walk-forward):** use the chosen `(tp*, sl*)_pair` for all 39 test folds.

This avoids per-fold flip-flop while still tuning per pair. Stage 1 is **label-computation only** (no model training) — much cheaper than Approach B.

**Cost:** Stage 1 is small (~10 min on 90 days × 20 pairs × 49 combos = 980 lightweight computations). Stage 2 = 1 normal eval (~30-50 min).
**Total: ~45 min wall.**

This is the recommended MVP for v26.

## Stage-1 metric: what to optimize

For each pair × (tp, sl) combo, we have the bid/ask-aware label distribution. Sharpe estimate on this LABEL set:

```python
labels = compute_tb_labels(pair_data, tp_mult, sl_mult)
# labels[i] in {-1, 0, +1} (SL / timeout / TP)
# but realized PnL per label depends on tp/sl values
realized_pnl_per_trade = []
for sig, label in zip(simulated_signals, labels):
    if label == sig:           # correct direction
        realized_pnl_per_trade.append(+tp_pip)  # TP hit
    elif label == -sig:        # wrong direction
        realized_pnl_per_trade.append(-sl_pip)  # SL hit
    else:                       # timeout
        realized_pnl_per_trade.append(0.0)
sharpe_proxy = mean(realized_pnl_per_trade) / std(realized_pnl_per_trade)
```

But `simulated_signals` requires a model — circularity.

Alternative: assume model achieves a fixed directional accuracy (e.g. 51%, slightly better than chance) and compute expected Sharpe under each (tp, sl). The (tp, sl) that maximizes this is the one with the cleanest label structure.

```
EV = 0.51 * tp_pip - 0.49 * sl_pip - timeout_neutral
Sharpe ≈ EV / sqrt(tp_pip² × p_tp + sl_pip² × p_sl)
```

Pick (tp, sl) that maximises this expected Sharpe.

## Verdict gates

| Verdict | Per-trade Sharpe | PnL retention |
| --- | --- | --- |
| GO         | ≥ 0.18 | ≥ 0.95× anchor |
| PARTIAL GO | ≥ 0.165 | ≥ 0.95× anchor |
| NO ADOPT | < 0.165 OR PnL < 0.85× | (sweep didn't pay off) |

Also report **per-pair (tp*, sl*) chosen** vs default (4, 4) — diagnostic of how universal the original is.

## Calibration prior

This is one of the few levers where the EXISTING fixed values are **demonstrably arbitrary** (no Phase justified them). So there's natural slack to improve:

- 50% — PARTIAL GO (Sharpe lift +0.005 to +0.015)
- 25% — GO (Sharpe lift +0.015 to +0.025)
- 15% — STRETCH GO (alone clears 0.20 — possible if some pairs have very degenerate (4,4) labels)
- 10% — NO ADOPT (per-pair selection on 90d in-sample doesn't generalize to test)

## Implementation plan (v26, deferred)

`scripts/compare_multipair_v26_dynamic_sltp.py` — clone of v25 (post 9.X-L if GO, else v24):

1. Add `_optimize_per_pair_sltp(train_df, pair, grid)` helper → returns `{pair: (tp_best, sl_best)}`.
2. Call once on first-fold training window. Cache result.
3. In `_eval_fold`, replace single `tp_mult, sl_mult` with `per_pair_sltp[pair]`.
4. Print Stage-1 mapping in summary block ("PHASE 9.X-M - PER-PAIR (TP, SL) MAPPING").
5. CLI: `--enable-dynamic-sltp`, `--sltp-grid "2.0,2.5,3.0,3.5,4.0,4.5,5.0"`, `--sltp-objective {sharpe,pnl}`.

## Risks

- **In-sample bias:** Stage 1 optimizes on training, Stage 2 evaluates on test — but Stage 2 is the FULL walk-forward, so test data includes folds far from the original training window. Per-pair (tp, sl) chosen on 90-day sample may not generalize to ranges 8 months later.
- **Overfit risk:** 49 combinations × 20 pairs = 980 hypotheses on 90-day data. Multiple-comparisons correction or larger training window may be needed.
- **Compounding with v25 filters:** if 9.X-L removes 15% of trades, the per-pair sample for Stage 1 shrinks proportionally; less reliable.

## Defer reason

Phase 9.X-L (filter) is cheaper to test (~2 hours impl + 1 eval) and reviewer Rank-1. If 9.X-L delivers significant lift, it changes the baseline for 9.X-M. If 9.X-L is NO ADOPT, 9.X-M still independent but priorities shift.

**Implementation only after Phase 9.X-L verdict.** Memo recorded now to capture design and avoid re-thinking later.

## Files

- This memo: `docs/design/phase9_x_m_design_memo.md`
- Implementation: `scripts/compare_multipair_v26_dynamic_sltp.py` (deferred)
- Eval log: `artifacts/phase9_x_m_dynamic_sltp.log` (deferred)
- Closure: `docs/design/phase9_x_m_closure_memo.md` (after eval)

Master tip when authored: `fd1d2f1` + open PRs.
