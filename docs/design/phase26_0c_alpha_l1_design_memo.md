# Phase 26.0c-α — L-1 Ternary Classification Design Memo

**Type**: doc-only design memo (binding contract for the eventual 26.0c-β implementation)
**Branch**: `research/phase26-0c-alpha-l1-design`
**Base**: master @ 40f98c2 (post-PR #307 merge)
**Pattern**: analogous to 26.0a-α (PR #301) / 26.0a-α-rev1 (PR #302) / 26.0b-α (PR #305)
**Status**: design memo only — does NOT initiate 26.0c-β eval
**Stop condition**: design memo merged → 26.0c-β implementation in a separate later instruction

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this design memo as the binding contract for the eventual Phase 26.0c-β L-1 ternary classification eval. It does NOT by itself authorise 26.0c-β implementation. The user explicitly authorises the 26.0c-β implementation PR in a separate later instruction.*

Same pattern as #301 / #302 / #305 approval semantics: accept design memo as contract, defer next implementation.

---

## 1. Phase 26.0c framing

- **L-1** = ternary classification: **TP-hit / SL-hit / TIME-exit**.
- Same triple-barrier event-time horizon as L-2 / L-3 (K_FAV=1.5×ATR, K_ADV=1.0×ATR, time cap equal to the 26.0a-β / 26.0b-β horizon).
- Same minimum feature set: `pair + direction` only (Phase 26 §5.1 binding **preserved unchanged**).
- Same canonical 20-pair universe + same 70/15/15 train/val/test split as 26.0a / 26.0b.
- Same fixed conservative LightGBM config; objective swapped to **multiclass** (`num_class=3`); `n_estimators=200, learning_rate=0.03, num_leaves=31, max_depth=4, min_child_samples=100, subsample=0.8, colsample_bytree=0.8, random_state=42`; `class_weight=balanced`.
- Phase 26 is NOT a continuation of Phase 25's feature-axis sweep (mandatory clause 6 preserved).
- This memo authorises one formal eval cell-grid only; nothing else.

---

## 2. L-1 label construction

### 2.1 Inputs (same as L-2 / L-3)

Per signal row from the 25.0a-β path-quality dataset:
- `pair`, `direction` (LONG/SHORT)
- `signal_t` (entry timestamp)
- `atr_at_signal_pip`
- `path_after_signal` (mid-price-based forward path)

### 2.2 Barrier construction

For each row:
- Long: TP = `mid_at_signal + K_FAV * atr_at_signal_pip * pip_size(pair)`, SL = `mid_at_signal - K_ADV * atr_at_signal_pip * pip_size(pair)`
- Short: TP = `mid_at_signal - K_FAV * atr_at_signal_pip * pip_size(pair)`, SL = `mid_at_signal + K_ADV * atr_at_signal_pip * pip_size(pair)`

K_FAV=1.5, K_ADV=1.0 (same as L-2 / L-3, unchanged).

### 2.3 Class label assignment (3 disjoint classes)

| Class | Code | Trigger |
|---|---|---|
| **TP** | 0 | TP barrier hit first within horizon |
| **SL** | 1 | SL barrier hit first within horizon |
| **TIME** | 2 | neither barrier hit; horizon reached |

**Disjoint by construction** (Decision A1). No abstain / no-trade class (that is L-4, deferred).

If both barriers are crossed in the same bar, tie-break: SL precedes TP (conservative — same convention as 24.0a / L-2 / L-3).

### 2.4 What is NOT in the label

- ❌ No spread subtraction at label construction (matches L-2; the L-2 / L-3 identity finding in PR #307 §3 makes this load-bearing).
- ❌ No continuous magnitude (L-1 is class label only; magnitude lives in the realised-PnL conversion step §5, not in the label).
- ❌ No abstain class (deferred to L-4).
- ❌ No pair-normalisation step (multiclass classification has no scale knob).

### 2.5 Mid-to-mid base PnL (for realised-PnL conversion only)

Same as L-2 / L-3 (cell-independent precomputation cache).

---

## 3. Picker / score function (Decision B1 + B2)

After multiclass LightGBM yields `P(TP), P(SL), P(TIME)` per row, two scores are computed:

| Picker | Score |
|---|---|
| **B1** | `P(TP)` |
| **B2** | `P(TP) - P(SL)` |

Both scores are **raw probabilities** (Decision F). **No isotonic calibration in the formal grid** (Decision E). Both scores are larger-is-better.

### 3.1 Explicitly excluded picker variants

- ❌ **B3 argmax voting** — collapses to majority class; not a continuous score; rejected at design.
- ❌ **B4 calibrated EV via class probs × class-realised-PnL** — partially overlaps L-3 (spread-aware EV); rejected at design.

---

## 4. Threshold family (Decision C + F)

### 4.1 Formal verdict basis: quantile-of-val on the picker score

Quantile-of-val candidates: **{5, 10, 20, 30, 40}%**. Top-q% of the val score distribution is traded; the corresponding val score cutoff is then applied to test **as a scalar** (test set touched once).

### 4.2 Diagnostic-only families (NOT formal cell dimensions)

These are computed and reported but **not eligible for cell selection or formal verdict routing**:

- Absolute probability thresholds: `{0.30, 0.40, 0.45, 0.50}` on `P(TP)`, or `{0.0, 0.05, 0.10, 0.15}` on `P(TP) - P(SL)`.
- Isotonic-calibrated probabilities (deferred; see §4.3).
- Per-class accuracy, AUC, Cohen's κ, multiclass logloss, confusion matrix (see §6 H1 binding).

### 4.3 Why isotonic calibration is removed from the formal grid (binding rationale)

> *Fitting isotonic calibration on the val set AND using the same val set to select the quantile cutoff introduces selection-overfit risk. The first L-1 eval should test the L-1 ternary label structure itself cleanly, not the calibration + selection interaction. Isotonic calibration is therefore deferred to either a diagnostic appendix in 26.0c-β or a later sub-phase. If isotonic results are reported in 26.0c-β at all, they must be flagged "diagnostic-only / not used in formal verdict."*

---

## 5. Realised-PnL conversion (cell-independent cache)

Same as L-2 / L-3:
- For each row in val and test, precompute the mid-to-mid realised PnL given the triple-barrier outcome (TP / SL / TIME) using `_compute_realised_barrier_pnl`.
- After quantile cutoff selection, sum across the top-q% rows and divide by trade count to get mean per-trade PnL (pip); compute Sharpe via daily aggregation.

This precomputation is cell-independent (does not depend on picker / cutoff / calibration choice) and is shared across all cells.

---

## 6. Hypothesis ladder (formal H1 binding)

| Hypothesis | Pass threshold (FORMAL) | Notes |
|---|---|---|
| **H1-weak** | val-selected cell **test Spearman(score, realised_pnl) > 0.05** | Score = the picker's raw probability output, NOT the class label |
| **H1-meaningful** | val-selected cell **test Spearman(score, realised_pnl) ≥ 0.10** | |
| **H2** | test realised Sharpe ≥ +0.082 AND ann_pnl ≥ +180 | Phase 26 binding |
| **H3** | test realised Sharpe > -0.192 | Phase 26 binding (G1; baseline unchanged) |
| **H4** | test realised Sharpe ≥ 0 | |

### 6.1 Why Spearman on raw score (NOT AUC / κ / logloss) is the formal H1

> *Phase 26's goal is NOT classification accuracy in itself. The goal is whether the score ranking converts to realised PnL on test. Spearman(score, realised_pnl) directly measures rank-correlation between picker output and the cell-independent realised-PnL cache. AUC / κ / logloss / confusion matrix / per-class accuracy measure classification quality, not score→PnL ranking, and so are diagnostic-only. ADOPT routing cannot depend on any single diagnostic column (clause 2 binding).*

### 6.2 Verdict-tree binding (preserved from 26.0b-α)

- **H2 PASS alone is NOT ADOPT_CANDIDATE.** ADOPT_CANDIDATE requires the full 8-gate A0-A5 harness via M1 path re-traverse.
- **H1_WEAK_FAIL** if both pickers fail H1-weak on the val-selected cell on test.
- **REJECT_NON_DISCRIMINATIVE** if H1_WEAK_FAIL AND test Sharpe ≤ H3 baseline.
- **NEEDS_REPLICATION** if H3 PASS but H2 FAIL.
- **ADOPT_CANDIDATE** only if H2 PASS AND all 8 A0-A5 gates pass on M1 re-traverse.

---

## 7. Formal cell grid (Decision E — 2 cells only)

> *Formal grid is intentionally minimal: 2 cells = 2 pickers × raw probability only. This isolates the L-1 ternary label structure as the single axis of test. Isotonic calibration is deferred (§4.3). Absolute probability thresholds are diagnostic-only (§4.2). Each formal cell sweeps quantile-of-val {5, 10, 20, 30, 40}% on val and applies the selected cutoff to test once.*

| Cell ID | Picker | Calibration | Cutoff family (formal) |
|---|---|---|---|
| **C01** | P(TP) | raw | quantile-of-val 5/10/20/30/40% |
| **C02** | P(TP) − P(SL) | raw | quantile-of-val 5/10/20/30/40% |

### 7.1 Val-selection rule (preserved from 26.0b-α §7)

Within each formal cell:
1. Apply **A0-prefilter**: drop quantiles whose val trade count is `< 200` (same threshold as 26.0a-β / 26.0b-β).
2. Among survivors, pick the quantile maximising **val realised Sharpe**.
3. **Tie-breakers** (in order): val realised ann_pnl → val Spearman(score, realised_pnl) → smaller quantile (more selective).

### 7.2 Cross-cell verdict aggregation

Two formal cells = two val-selected (cell\*, q\*) records. The Phase 26.0c-β verdict is formed by:
- If both cells' val-selected outcomes agree on the verdict tree branch → report that branch as the formal verdict.
- If they disagree → report each cell's branch separately and route to the routing-review pattern (no auto-resolution).

---

## 8. Posterior expectations (subjective / heuristic / not statistically estimated)

| Outcome | Probability tag |
|---|---|
| H1 PASS on C01 (P(TP) only) | low-to-medium |
| H1 PASS on C02 (P(TP) − P(SL)) | medium |
| H2 PASS (ADOPT_CANDIDATE-track) on either cell | low |
| H3 PASS (NEEDS_REPLICATION-track) | low-to-medium |
| Overall verdict resembles L-2 / L-3 (REJECT_NON_DISCRIMINATIVE) | medium-to-high |

**Posterior tags are subjective / heuristic / not statistically estimated.** They are discussion anchors only. The L-2 / L-3 identity finding does NOT directly imply L-1 will fail — L-1 is a structurally different label class (3-way classification, not regression) and the score→PnL ranking mechanism applies differently.

---

## 9. Diagnostic columns (binding: all of §9 are diagnostic-only)

All items in this section are diagnostic-only. **ADOPT routing must not depend on any single one** (mandatory clause 2).

### 9.1 Class-prior table

Train / val / test counts and shares for TP / SL / TIME per pair.

### 9.2 Pair-direction split

Trade-count share per pair on val-selected (cell\*, q\*); preserves the `CONCENTRATION_HIGH=True` flag if ≥80% single-pair share (threshold inherited from 26.0b-β, diagnostic-only, **not used in formal verdict / cell selection**).

### 9.3 Classification-quality diagnostics

- AUC of `P(TP)` (one-vs-rest) on val and test.
- Cohen's κ on val and test (multiclass).
- Multiclass logloss on val and test.
- Confusion matrix on val and test.
- Per-class accuracy on val and test.

All five are diagnostic-only. **None can be used as a formal verdict criterion** (§6.1 binding).

### 9.4 Absolute probability-threshold diagnostic

Run a parallel report for `P(TP) ≥ {0.30, 0.40, 0.45, 0.50}` and `P(TP) - P(SL) ≥ {0.0, 0.05, 0.10, 0.15}`. Report n_trades, val realised Sharpe, test realised Sharpe per absolute threshold. **None of these enter formal verdict routing.**

### 9.5 Optional isotonic-calibration diagnostic appendix

If included in 26.0c-β at all, must be flagged "diagnostic-only / not used in formal verdict" and must NOT be used to mint a verdict. Default recommendation: **omit from 26.0c-β; defer to a later sub-phase**.

### 9.6 L-1 vs L-2 vs L-3 comparison (mandatory section in 26.0c-β eval_report.md)

Same pattern as the L-2 vs L-3 section in 26.0b-β eval_report.md. Compare val-selected cell, n_trades, val/test realised Sharpe, val/test ann_pnl, val/test Spearman, pair concentration.

---

## 10. Sanity probe (mandatory before full sweep)

Same pattern as 26.0b-β sanity probe:
1. Build L-1 labels for train/val/test on the full 20-pair dataset.
2. Print class-prior counts and shares (TP / SL / TIME) overall and per pair.
3. Print mid-to-mid base PnL distributions (mean, p5, p50, p95) per class.
4. Confirm class counts are non-degenerate (each class > 1% of total rows).
5. **Halt if any sanity check fails.** The full sweep does not run unless the probe passes.

---

## 11. Implementation outline for 26.0c-β (NOT this PR)

| Item | Detail |
|---|---|
| Script | `scripts/stage26_0c_l1_eval.py` (~1700-1900 lines; closely modelled on `stage26_0b_l2_eval.py`) |
| Tests | `tests/unit/test_stage26_0c_l1_eval.py` (~30-35 tests; 3 NEW L-1-specific: class-set disjointness, P(TP)−P(SL) signal monotonicity, multiclass-probability sum-to-1 invariance) |
| Sanity probe | per §10 above |
| Eval report | `artifacts/stage26_0c/eval_report.md` with the mandatory **L-1 vs L-2 vs L-3 comparison** section (§9.6) |
| Runtime estimate | ~15-30 min (2 formal cells × 5 quantiles × multiclass LightGBM) |
| .gitignore entries | `artifacts/stage26_0c/{run.log, sweep_results.parquet, sweep_results.json, aggregate_summary.json, val_selected_cell.json}` |
| Master tip at impl start | TBD (post this PR merge) |

---

## 12. Mandatory clauses (verbatim, 6 total — inherited unchanged from #299 §7 / 26.0a-α §9 / rev1 §11 / 26.0b-α §9 / 26.0b post-routing-review §12)

1. **Phase 26 framing** — Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.
2. **Diagnostic columns prohibition** — Calibration / threshold-sweep / directional-comparison / classification-quality columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.
3. **γ closure preservation** — Phase 24 γ hard-close (PR #279) is unmodified.
4. **Production-readiness preservation** — X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure) remains untouched.
5. **NG#10 / NG#11 not relaxed**.
6. **Phase 26 scope** — Phase 26 is NOT a continuation of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed. (R6-new in post-26.0b routing review §6 still requires explicit scope amendment.)

---

## 13. PR chain reference

```
Phase 26:
  #299 (kickoff) → #300 (first-scope review)
  → #301 (26.0a-α L-3 design) → #302 (26.0a-α-rev1)
  → #303 (26.0a-β rev1 L-3 eval)
  → #304 (post-26.0a routing review)
  → #305 (26.0b-α L-2 design) → #306 (26.0b-β L-2 eval)
  → #307 (post-26.0b routing review)
  → THIS PR (26.0c-α L-1 design)
  → 26.0c-β L-1 eval (separate later instruction)
  → 26.0c post-routing-review (after 26.0c-β closure)
```

---

## 14. What this PR will NOT do

- ❌ Implement `scripts/stage26_0c_l1_eval.py`.
- ❌ Implement `tests/unit/test_stage26_0c_l1_eval.py`.
- ❌ Run any sweep or produce any `artifacts/stage26_0c/*` content.
- ❌ Modify `src/`, `scripts/` outside the design memo path, `tests/`, `artifacts/`.
- ❌ Touch `.gitignore` for `artifacts/stage26_0c/*` (deferred to 26.0c-β PR).
- ❌ Modify any prior verdict (Phase 25, Phase 26 #284..#307).
- ❌ Retroactively change L-2 or L-3 verdict.
- ❌ Modify γ closure (PR #279).
- ❌ Pre-approve production deployment.
- ❌ Update MEMORY.md.
- ❌ Foreclose L-4 / R6-new / R5 as later routing options.
- ❌ Foreclose F4 / F6 / F5-d / F5-e (Phase 25 deferred extensions).
- ❌ Authorise the 26.0c-β implementation PR.

---

## 15. Sign-off

After this design memo merges:

- **26.0c-β implementation** is authorised only by a separate later user instruction.
- The 26.0c-β PR will implement `scripts/stage26_0c_l1_eval.py` + `tests/unit/test_stage26_0c_l1_eval.py` + `artifacts/stage26_0c/eval_report.md` (with mandatory L-1 vs L-2 vs L-3 comparison section).
- After 26.0c-β closure, a 26.0c post-routing review will follow the #304 / #307 pattern.

**This PR stops here.**
