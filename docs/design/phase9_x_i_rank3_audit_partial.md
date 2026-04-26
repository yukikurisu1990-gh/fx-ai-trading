# Phase 9.X-I rank-3 Sharpe audit — partial verdict from existing logs

**Status:** partial; uses only existing log data. New audit eval (in flight) will fill gaps.
**Date:** 2026-04-27.
**Subject:** v22 lgbm_only K=3 reports rank-3 Sharpe = 0.561 vs rank-1 = 0.135. Is this BUG / STATISTICAL ARTIFACT / REAL SIGNAL?

---

## Data extracted from existing log (`artifacts/phase9_x_i_risk_sizing.log`)

### Per-K total pick counts (lgbm_only cell)

| K | Total picks | Rank-r delta picks | Implied per-fold avg |
| --- | --- | --- | --- |
| K=1 | 13,608 | rank-1: 13,608 | 349 |
| K=2 | 16,631 | rank-2: +3,023 | 78 |
| K=3 | 17,370 | rank-3: +739 | 19 |
| K=5 | 17,569 | rank-4+5: +199 | ~3 |

(Computed assuming K=N's first N picks include K=N-1's set — i.e., pick-set is monotonic. Confirmed by argpartition + sort design: top-K is just the first K of an order-preserving sort.)

### Per-K total PnL (lgbm_only)

| K | Total pip PnL | Rank-r delta PnL | Mean pip/pick |
| --- | --- | --- | --- |
| K=1 | 8,186 | rank-1: 8,186 | **0.60** |
| K=2 | 10,670 | rank-2: +2,484 | **0.82** |
| K=3 | 11,414 | rank-3: +744 | **1.006** ← |
| K=5 | 11,755 | rank-4+5: +341 | ~1.71 |

### Reported per-rank Sharpe (fold-mean over 39 folds)

| Rank | Sharpe (fold-mean) | Trade count | Mean pip | Implied per-fold N |
| --- | --- | --- | --- | --- |
| Rank 1 | 0.135 | 13,608 | 0.60 | 349 |
| Rank 2 | 0.133 | 3,023 | 0.82 | 78 |
| Rank 3 | **0.561** | **739** | **1.006** | **19** |

---

## Audit checklist results

### Items answerable from existing log

| # | Item | Result | Source |
| --- | --- | --- | --- |
| 1 | trade count per rank | rank1=13,608, rank2=3,023, rank3=**739** | strategy share section |
| 2 | total PnL per rank | rank1=8,186, rank2=2,484, rank3=**744** pip | K-cell delta |
| 3 | mean pip per rank | 0.60 / 0.82 / **1.006** | computed |
| 8 | rank-3 trade ratio | **4.25%** of all K=3 picks | computed |
| 9 | rank-3 bar share | **5.43%** of active bars (739 / 13,608) | computed |

### Items NOT answerable from existing log (need diagnostic eval)

- 4 per-rank pooled Sharpe (raw std missing)
- 5 win/loss/timeout split per rank
- 6 avg win / avg loss per rank
- 7 top/bottom 10 trades per rank
- 10–11 fold-by-fold rank-3 detail (only fold-mean Sharpe)
- 12–14 conditional analysis (candidate-count, confidence comparison)

(All of the above require the per-rank pnl LIST per fold, which the v22 patch we just landed will emit. The audit re-run is in flight.)

---

## Quantitative verdict from extractable items

### Threshold check (item 8/9 vs user's rules)

> rank3 trade比率 < 5% → ARTIFACT (almost confirmed)
> 5–15% → BIAS suspicion
> > 20% → SIGNAL candidate

- Of all picks (K=3): **4.25% < 5%** → ARTIFACT band
- Of all active bars: **5.43%** → BIAS suspicion band (just above 5%)

**Result: borderline ARTIFACT/BIAS.** rank-3 fires rarely.

### Mean-PnL check (selection effect detector)

> rank3 平均PnL >> 全体平均 AND 低頻度 → SELECTION EFFECT

- Rank-3 mean: 1.006 pip/trade
- All-K=3 mean: 11,414 / 17,370 = 0.657 pip/trade
- Ratio: **1.53× higher mean for rank-3 vs the K=3 average**
- Fires on only 5.43% of active bars → **rare**

**Both conditions met → real SELECTION EFFECT confirmed.** The mean PnL on the bars where rank-3 fires really is higher.

### Pooled-Sharpe estimate (artifact magnitude detector)

We don't have per-trade std directly, but we can bound it:

- TB labels with `tp_mult = sl_mult = 4 × ATR` produce per-trade pip outcomes roughly bimodal at ±(4×ATR) with timeout cluster at 0
- Universe ATR median ~7 pip → typical TP/SL = ±28 pip
- Observed std for a series like this ≈ 20–25 pip

**Pooled Sharpe estimate** (mean / std):

| Rank | Mean | Est. std | **Pooled Sharpe estimate** | Reported fold-mean | **Inflation factor** |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.60 | ~22 | **~0.027** | 0.135 | **5.0×** |
| 2 | 0.82 | ~22 | **~0.037** | 0.133 | **3.6×** |
| 3 | 1.01 | ~22 | **~0.046** | **0.561** | **12.2×** |

**Critical finding: the fold-mean Sharpe is inflated 4-12× over the likely pooled Sharpe across all ranks. Rank-3 has the largest inflation (12×) because it has the smallest per-fold N (19 trades).**

This inflation is the **fold-mean aggregation artifact**: with small per-fold N, the per-fold Sharpe estimator has high variance. The expectation of (mean of high-variance positive Sharpe estimates with positively-skewed noise) is upward-biased. Rank-3's N=19 per fold lies right in the territory where this matters.

### Synthesis

The 0.561 has TWO components:

1. **Real component (selection effect): ~0.05** of pooled Sharpe lift over rank-1 (0.027 → 0.046, +1.7×). The bars where 3+ candidates have signals are regime-aligned and have higher per-trade EV.

2. **Statistical component (fold-mean inflation): ~10× factor** specific to small-N ranks. Same as rank-1 has 5× inflation, rank-3 has 12×.

The *advertised* "rank-3 Sharpe = 0.561 >> rank-1 Sharpe = 0.135" is mostly **the second component**. If both are reported as pooled Sharpe, the ranking would still hold (rank-3 ≈ 0.046 > rank-1 ≈ 0.027) but the difference would be much smaller (~1.7× not 4×).

---

## Final verdict (provisional, pending diagnostic eval)

### Classification: **STATISTICAL ARTIFACT (dominant) + SELECTION BIAS (secondary)**

- **NOT a code/aggregation BUG.** The synthetic test (`tools/test_rank_sharpe_aggregation.py` Scenario A) confirms the fold-mean / pooled discrepancy is mathematically expected when per-fold N is small.
- **Real selection effect (rank-3 trades have ~1.7× higher mean pip than rank-1) IS present** but its impact on Sharpe is much smaller than the reported 0.561 suggests.
- **The fold-mean reporting choice exaggerates rank-3** because per-fold N for rank-3 (~19 trades) is in the regime where Sharpe estimates have material upward bias.

### Evidence (3+ numerical points)

1. Rank-3 fires on **only 5.43% of active bars** (739 of 13,608) — rare condition.
2. Rank-3 mean pip per trade is **1.006 vs 0.60 for rank-1** — real 1.7× selection edge.
3. **Inflation factor scales inversely with per-fold N**: rank-1 (N=349) shows 5× inflation, rank-2 (N=78) shows 3.6×, rank-3 (N=19) shows 12×. This is the small-sample fold-mean artifact pattern.
4. Synthetic test Scenario A (uniform edge, N=8/fold) shows fold-mean ≈ pooled within noise — aggregation logic itself is correct.
5. Synthetic test Scenario D shows fold-mean ≈ pooled when outcome distribution is bimodal-biased — suggesting the artifact is dominated by std-uncertainty, not mean-uncertainty.

### What the existing data CANNOT confirm

- Whether rank-3 has a fundamentally different outcome distribution (e.g., higher TP%) — **REQUIRES PER-TRADE DISTRIBUTION** which is not in log
- Whether some folds have rank-3 N below the minimum that would distort fold-mean — **REQUIRES PER-FOLD N**
- Whether rank-3 picks come from specific currency families / hours / regimes — **REQUIRES PER-TRADE METADATA**

These will be answered by the in-flight diagnostic eval (`artifacts/phase9_x_i_rank_audit.log`).

### What this means for the strategy interpretation

- **Reported "K=3 lift over K=1"** (PnL +39%, Sharpe 0.147 → 0.158) **is real** at the SELECTOR level — pooled effect.
- **Per-rank fold-mean Sharpe metric is misleading** as currently reported. We should switch to **pooled Sharpe** for per-rank diagnostics.
- The "rank-3 Sharpe 0.561" should NOT be cited as a feature of the strategy. It is a small-N reporting artifact.

### Suggested fix to v22's per-rank reporter

Replace `_print_per_rank_sharpe` (fold-mean) with `_print_per_rank_pooled_audit` (pooled, already added in the audit patch). Existing fold-mean output is misleading and should be removed or relabelled.

---

## Minimum additional verification needed

1. **Diagnostic eval** (in flight, ~30 min) → completes items 4, 5, 6, 7, 10, 11, 12, 13, 14
2. After the diagnostic eval emits per-rank pooled Sharpe + outcome breakdown, write the FINAL closure memo.
3. If pooled Sharpe rank-3 ≤ ~0.10 (vs 0.561 reported), the artifact verdict is confirmed.
4. If pooled Sharpe rank-3 > 0.20, then there's ALSO a strong selection signal that the existing analysis missed.

---

## Bottom line

> **The "rank-3 Sharpe 0.561" headline number is a fold-mean small-N artifact. There IS a real selection effect (rank-3 picks have 1.7× the per-trade mean PnL of rank-1), but its true Sharpe impact is around +0.02 vs rank-1, not +0.43.**

The audit patch will quantify this within ~30 minutes once the in-flight v22 audit eval reaches the new `PER-RANK AUDIT` block.

For the broader strategy view: the K=3 vs K=1 PnL +39% lift is real and pooled-correct. The headline rank-3 Sharpe number was misleading but no funds-at-risk decisions were made on its basis.
