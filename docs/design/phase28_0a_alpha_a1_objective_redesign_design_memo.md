# Phase 28.0a-α — A1 Objective Redesign Design Memo

**Type**: doc-only sub-phase α design memo
**Status**: pre-states Phase 28.0a-β scope; does **NOT** initiate the β-eval
**Branch**: `research/phase28-0a-alpha-a1-objective-redesign`
**Base**: master @ `d01e795` (post-PR #336 / Phase 28 first-mover routing review)
**Pattern**: analogous to PR #320 / #325 / #327 / #331 sub-phase α design memos under Phase 27
**Date**: 2026-05-16

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Phase 28.0a-α design memo**. It pre-states the **closed 3-loss allowlist** (L1 / L2 / L3), the **5-cell structure**, the **formal H-C1 falsifiable hypothesis with 4-row outcome ladder**, the **3 anti-collapse guards (NG#A1-1 / NG#A1-2 / NG#A1-3)**, and the **D10 4-artifact form** (3 loss-variant regressors + 1 symmetric-Huber control regressor + 1 multiclass head for §10 baseline reproduction). It does **NOT**:*
>
> - *initiate the β-eval (no `scripts/stage28_0a_*.py`, no `tests/unit/test_stage28_0a_*.py`, no `artifacts/stage28_0a/`);*
> - *create any scope amendment (none required under Phase 28 kickoff §15 for A1 objective redesign);*
> - *elevate R-T1 / R-B / R-T3 (all carry-forward routes remain in PR #334 status);*
> - *modify the §10 baseline numeric or any prior verdict;*
> - *touch `src/` / `scripts/` / `tests/` / `artifacts/` / `.gitignore` / `MEMORY.md`.*
>
> *The β-eval implementation (PR `phase28-0a-beta-...`) is a **separate later PR**. The pre-stated parameters (`w_clip`, `δ_pos`, `δ_neg`, `γ`) and the closed loss allowlist are fixed at α and cannot be changed at β; any change requires a memo amendment PR back to α.*

Same approval-then-defer pattern as PR #320 / #325 (27.0d-α) / #327 (27.0e-α) / #331 (27.0f-α).

---

## 1. A1 mission statement

Phase 27.0d-β unlocked the first real H1m-PASS ranking signal in the Phase 27 / 26 / 25 inheritance chain: the S-E LightGBM regressor on realised PnL produced **Spearman = +0.4381** on the test set at the C-se cell. The same C-se cell produced **Sharpe = -0.483** at q\*=40 (n=184,703). 27.0e-β (R-T2 quantile-family trim) preserved Spearman but worsened Sharpe monotonically; 27.0f-β (R7-C regime/context features) preserved Spearman but failed to lift Sharpe (C-se-rcw ≈ C-se-r7a-replica, max |Δ Sharpe| = 0.0039). The Phase 27 closure memo (PR #334 §6) consolidated this as the **load-bearing observation**: ranking signal is real, monetisation conversion is broken.

**Phase 28.0a-α exists** to pre-state the design of the **A1 sub-phase**: a **train-time objective / loss redesign** that **preserves the S-E ranking signal** (same R7-A features, same realised-PnL target, same LightGBM regressor architecture) while **attacking the Sharpe gap at training time** via three closed loss variants:

- **L1 — magnitude-weighted Huber loss** (per-row `sample_weight` based on |realised_pnl_pip|)
- **L2 — asymmetric Huber loss** (different δ for positive vs negative residuals; custom objective)
- **L3 — spread-cost-weighted Huber loss** (per-row `sample_weight` based on spread cost)

This is A1 from the Phase 28 kickoff (PR #335 §5.2) and the **primary first-mover** of Phase 28 per the routing review (PR #336 §14.1). The β-eval will be implemented in a separate later PR (`phase28-0a-beta-...`).

---

## 2. Why A1 is NOT Phase 27 inertia

Phase 28 kickoff §3 listed five Phase 27 inertia routes that are NOT admissible at Phase 28 kickoff. A1's design must be *distinct* from each. Per axis:

### 2.1 A1 ≠ S-C TIME penalty α grid (27.0b-β)

- **S-C**: single scalar α applied as a uniform TIME-class downweight, swept over a grid {0.0, 0.3, 0.5, 1.0}.
- **A1**: changes the **loss class** itself (magnitude-weighted / asymmetric / spread-cost-weighted). Each variant has **one pre-stated numeric parameter** fixed at α (see §4). No grid sweep on those parameters.
- **Anti-collapse guard NG#A1-1** (§6) makes this distinction enforceable: an α scalar grid sweep over a single Huber objective is NOT admissible under A1.

### 2.2 A1 ≠ S-D calibrated EV (27.0c-β)

- **S-D**: Platt-style probability calibration applied to the S-B classifier's P(TP) / P(SL) probabilities; the *score* is recomputed from calibrated probabilities.
- **A1**: keeps S-E's *regressor* architecture; modifies the **training-time loss** rather than post-fit score transformation.

### 2.3 A1 ≠ S-E symmetric Huber regression (27.0d-β)

- **S-E (27.0d)**: symmetric Huber loss on raw realised PnL (α=0.9 inherited from 27.0d-α); no per-row weighting; no asymmetry.
- **A1**: three variants, each structurally distinct from symmetric Huber. **C-a1-se-r7a-replica** (the within-eval ablation control; §7) reproduces 27.0d's S-E for direct comparison, so the "objective change has zero effect" outcome can be formally diagnosed (PARTIAL_DRIFT_R7A_REPLICA; §3.2).

### 2.4 A1 ≠ R-T2 quantile-family trim (27.0e-β)

- **R-T2**: selection-time intervention; trims the quantile family {5, 7.5, 10}.
- **A1**: train-time intervention; the **quantile family {5, 10, 20, 30, 40} is held fixed** at the 27.0f shape (§5 in-scope). A1 changes how the model learns, not how the selector picks.

### 2.5 A1 ≠ R7-C regime/context features (27.0f-β)

- **R7-C**: added 3 closed-allowlist regime-statistic features on top of R7-A. Feature surface widened.
- **A1**: **R7-A feature surface unchanged**. No R7-C addition. The information that R7-C tried to add (regime / spread / volume) enters via L3's `sample_weight = 1 + γ × spread_at_signal_pip` at training time, not as a feature.

A1's distinction from each Phase 27 inertia route is enforced by **NG#A1-1**, **NG#A1-2**, **NG#A1-3** in §6.

---

## 3. Formal H-C1 hypothesis (4-row outcome ladder)

The Phase 28 first-mover routing review (PR #336 §5.3) pre-stated a placeholder H-C1. This memo formalises it as a 4-row falsifiable outcome ladder.

### 3.1 H-C1 (formal pre-statement)

> **H-C1**: At least one of the three closed loss variants {L1 magnitude-weighted Huber, L2 asymmetric Huber, L3 spread-cost-weighted Huber} will produce a val-selected (cell\*, q\*) record on the C-a1-Lx cell satisfying **all** of:
>
> 1. **H2 PASS**: val Sharpe ≥ §10 baseline val Sharpe + **+0.05 absolute** (i.e., val Sharpe ≥ -0.136).
> 2. **H1m preserved**: val-selected cell Spearman ≥ **+0.30** (rolled forward from 27.0d S-E's +0.438; tolerates modest discrimination loss).
> 3. **C-sb-baseline reproduction PASS**: n_trades = 34,626 exact; Sharpe Δ ≤ ±1e-4; ann_pnl Δ ≤ ±0.5 pip (inherited from 27.0c-α §7.3 / 27.0d / 27.0e / 27.0f).
> 4. **H3 PASS**: trade count ≥ 20,000 (avoid degenerate low-trade-count Sharpe lifts).
>
> **OR** H-C1 is FALSIFIED at the variant.

### 3.2 4-row outcome ladder (per variant; aggregated across L1 / L2 / L3)

The β-eval will emit **one of four outcomes** for each loss variant {L1, L2, L3}. The aggregate verdict over the sub-phase is decided by which outcome appears across the three variants.

| Outcome | Per-variant condition | Aggregate implication |
|---|---|---|
| **PASS** | All four H-C1 conditions (3.1) satisfied on val-selected (cell\*, q\*) for this variant. | If 1+ variant PASSes and the C-sb-baseline reproduction is intact, sub-phase verdict = SPLIT_VERDICT_ROUTE_TO_REVIEW (per Phase 27 sub-phase aggregation; ADOPT_CANDIDATE wall preserved → PROMISING_BUT_NEEDS_OOS only). |
| **PARTIAL_SUPPORT** | Spearman preserved (≥ +0.30) AND val Sharpe lift ∈ [+0.02, +0.05) absolute AND trade count ≥ 20,000 AND C-sb-baseline reproduction intact. | If 1+ variant is PARTIAL_SUPPORT and 0 variants are PASS, sub-phase verdict = REJECT (sub-threshold). |
| **FALSIFIED_OBJECTIVE_INSUFFICIENT** | All three of {H2, H1m, H3} fail or val Sharpe lift < +0.02 absolute. | If all 3 variants are FALSIFIED_OBJECTIVE_INSUFFICIENT, sub-phase verdict = REJECT; strengthens the prior that the objective-axis is **not** the binding lever (H-B7 / H-B9 elevation candidates). |
| **PARTIAL_DRIFT_R7A_REPLICA** | C-a1-Lx ≈ C-a1-se-r7a-replica within tolerance (n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5 % magnitude) **at the val-selected q\***. | The loss change had zero effect on the score; analogous to 27.0f H-B6 FALSIFIED_R7C_INSUFFICIENT. If all 3 variants hit this outcome, sub-phase verdict = REJECT and the diagnosis is "LightGBM extracts the same signal regardless of the three loss variants tested." |

### 3.3 Aggregate decision rule

- If **any single variant** records PASS, sub-phase verdict = **SPLIT_VERDICT_ROUTE_TO_REVIEW** (val-selector may still pick C-sb-baseline; cross-cell aggregation per §9 decides).
- If **0 variants** PASS but **1+ variant** is PARTIAL_SUPPORT, sub-phase verdict = **REJECT_NON_DISCRIMINATIVE** (sub-threshold).
- If **0 variants** PASS and **0 variants** PARTIAL_SUPPORT, sub-phase verdict = **REJECT_NON_DISCRIMINATIVE** (deeper falsification).
- If **all 3 variants** hit PARTIAL_DRIFT_R7A_REPLICA, the diagnostic note records "objective change does not move the score regardless of variant" (load-bearing for §15 dissent elevation).

The aggregate verdict ladder mirrors Phase 27 sub-phase 群 (PR #325 §X / #328 §X / #332 §X) — H2 PASS still equals **PROMISING_BUT_NEEDS_OOS only** under the ADOPT_CANDIDATE wall (§12).

---

## 4. Closed 3-loss allowlist (pre-stated numeric parameters)

The three loss variants and their numeric parameters are **fixed at α** and cannot be modified at β. Any change requires a memo amendment PR back to α.

### 4.1 L1 — magnitude-weighted Huber loss

- **Definition**: per-row `sample_weight = min(|realised_pnl_pip|, w_clip)` where `w_clip` is fixed at α.
- **Pre-stated numeric**: **w_clip = 30.0 pip**.
- **Rationale**: 30.0 pip is above the p95 of |realised_pnl_pip| on TRAIN (per 27.0f-β SANITY PROBE: TP p95 = +21.03, SL p95 = -12.02 absolute, TIME p95 = +12.45), so the clip affects only the upper 1-2 % tail. It prevents single extreme-PnL rows from dominating the loss gradient while still up-weighting the genuinely high-magnitude regime that S-E currently treats uniformly.
- **Backbone**: LightGBM regressor with `objective='huber'`, `alpha=0.9` (inherited from 27.0d-α S-E; symmetric Huber). The weighting enters via `sample_weight=`, not via custom objective.

### 4.2 L2 — asymmetric Huber loss

- **Definition**: Huber loss with **two δ values**:
  - δ_pos applied when `residual = y - ŷ > 0` (under-prediction; model predicted lower than realised)
  - δ_neg applied when `residual < 0` (over-prediction; model predicted higher than realised)
- **Pre-stated numeric**: **δ_pos = 0.5** / **δ_neg = 1.5**.
- **Rationale**: The 27.0e-β monotonic top-tail-adversarial pattern (Sharpe worsens as q decreases from 40 → 10 → 5) suggests the regressor's top-tail confidence is *over-predicting* realised PnL. Penalising over-prediction (δ_neg = 1.5) three times as heavily as under-prediction (δ_pos = 0.5) at training time should compress the top-tail confidence toward the true distribution. The 3× ratio is chosen to be **structurally distinct** from a symmetric Huber (1.0 / 1.0) without being so extreme as to flip the model's predictions sign-wise.
- **Backbone**: LightGBM `lightgbm.Booster` API with a **custom objective function** (computes `grad` and `hess` for asymmetric Huber per the formula).

### 4.3 L3 — spread-cost-weighted Huber loss

- **Definition**: per-row `sample_weight = 1 + γ × spread_at_signal_pip`.
- **Pre-stated numeric**: **γ = 0.5**.
- **Rationale**: At γ = 0.5 and typical spread = 2 pip (per 27.0f-β SANITY PROBE: spread_at_signal_pip p50 = 1.9, mean = 2.169), the weight is 1 + 1.0 = 2.0x — expensive-spread rows are learned roughly twice as heavily. At spread = 3.7 pip (p95), the weight is 1 + 1.85 = 2.85x. This **directly tests** whether the regime-information that R7-C tried to add as a **feature** (and failed) helps when added as a **training-time weight** instead.
- **Backbone**: LightGBM regressor with `objective='huber'`, `alpha=0.9` (same backbone as L1). Weighting enters via `sample_weight=`.

### 4.4 Why 3 variants exactly (closed allowlist)

L1 / L2 / L3 jointly span three orthogonal hypotheses about what is missing from S-E:

- **L1**: "the loss undervalues high-magnitude rows in general"
- **L2**: "the loss is symmetric but the failure mode is asymmetric (over-prediction at the top tail)"
- **L3**: "the loss is regime-blind; expensive-spread rows need different weight"

The 3 variants do **not** include a 4th non-Huber backbone (e.g., MSE) by design — this would expand the cost-prior surface beyond what is justifiable as a first-mover. If A1's β-eval falsifies all three, that itself is information: it strengthens the prior that the objective axis is not the binding lever, raising A4 / A0 dissent priors.

### 4.5 No grid sweep within a variant

Within L1, `w_clip` is fixed at 30.0 pip; no `w_clip ∈ {15, 30, 60}` grid. Within L2, δ_pos = 0.5 / δ_neg = 1.5 is fixed; no asymmetry-ratio grid. Within L3, γ = 0.5 is fixed; no γ grid. **This is enforced by NG#A1-1** (§6.1).

---

## 5. In-scope vs out-of-scope

### 5.1 In-scope (β-eval will exercise these)

- **Model class**: LightGBM regressor on R7-A features (4 features: `pair`, `direction`, `atr_at_signal_pip`, `spread_at_signal_pip`). **Same as 27.0d / 27.0e / 27.0f.**
- **Target**: triple-barrier realised PnL (D-1 bid/ask executable; K_FAV = 1.5×ATR; K_ADV = 1.0×ATR; H_M1 = 60). **Unchanged from Phase 27.**
- **3 loss variants L1 / L2 / L3** as defined in §4 (closed allowlist; numeric parameters fixed at α).
- **Quantile family {5, 10, 20, 30, 40}** (same as 27.0f-β; preserves direct comparability to 5-eval evidence picture).
- **5-cell structure** as defined in §7 (3 loss variants + 1 within-eval ablation control + 1 §10-baseline reproduction).
- **D-1 bid/ask executable harness** unchanged.
- **5-fold OOF (DIAGNOSTIC-ONLY; seed = 42)** inherited from 27.0d / 27.0f.
- **2-layer selection-overfit guard** (validation-only selection; test touched once).
- **C-sb-baseline reproduction FAIL-FAST** (§8).
- **20-pair / 730-day / 70-15-15 chronological split** inherited.
- **OOF correlation diagnostic** computed for all 3 variants (per §7-5 confirmation).
- **Top-tail regime audit** computed for all 3 variants on val (per §7-6 confirmation; H-B6 mechanism diagnostic carried forward as a DIAGNOSTIC-ONLY check on whether the loss change moved the top-tail regime mix).
- **25-section eval_report.md** inherited from 27.0f-α §11 (§11 below).

### 5.2 Out-of-scope (NOT exercised by this sub-phase)

- **R7-C features** (regime/context). Frozen at PR #334 closure status; not added in this sub-phase. The information R7-C carried (spread / volume / regime) enters as L3's per-row weight instead.
- **Architecture change (A0)**. LightGBM regressor unchanged.
- **Target redesign (A2)**. Realised-PnL target unchanged.
- **Selection-rule redesign (A4)**. Top-quantile-on-score unchanged. R-T1 reframing NOT done in this sub-phase.
- **Feature surface broadening (R-B)**. R7-A closed allowlist preserved. No path / microstructure / multi-TF features added.
- **Concentration formalisation (R-T3)**. No per-pair budget caps / direction-balanced selection.
- **Universe / span / split changes**. 20-pair / 730-day / 70-15-15 split inherited.
- **Hyperparameter sweep beyond pre-stated `w_clip` / `δ_pos·δ_neg` / `γ`**. The 3 numerics are fixed at α; no grid sweep at β.
- **Non-Huber backbone**. The 3 variants are all Huber-based (with `sample_weight` or custom objective). MSE / quantile-regression / log-cosh are out of scope for this sub-phase.

---

## 6. Anti-collapse guards (NG#A1-1 / NG#A1-2 / NG#A1-3)

To enforce the §2 distinction (A1 ≠ Phase 27 inertia) at the implementation level, the β-eval and any sub-phase reasoning must respect three anti-collapse guards. These are pre-stated as binding gates at α.

### 6.1 NG#A1-1 — closed 3-loss allowlist, no scalar grid sweep

The loss change MUST be one of {L1 magnitude-weighted, L2 asymmetric, L3 spread-cost-weighted} as defined in §4 with the pre-stated numeric parameters (`w_clip = 30.0` / `δ_pos = 0.5, δ_neg = 1.5` / `γ = 0.5`).

- A scalar grid sweep over a single Huber `α` parameter is **NOT admissible**. (This would collapse to S-C-style TIME-α inertia.)
- A grid sweep over `w_clip` / `δ_pos·δ_neg` / `γ` within a variant is **NOT admissible**. (Each variant has exactly one numeric.)
- Adding a 4th variant at β is **NOT admissible** without a memo amendment PR back to α.

### 6.2 NG#A1-2 — per-variant verdict required

Each variant {L1, L2, L3} must produce its own verdict outcome per the 4-row ladder (§3.2). Aggregate-only verdicts (e.g., "average of three variants is PARTIAL_SUPPORT") are **NOT admissible**.

- The eval_report must list one outcome per variant: L1 → {PASS / PARTIAL_SUPPORT / FALSIFIED_OBJECTIVE_INSUFFICIENT / PARTIAL_DRIFT_R7A_REPLICA}; same for L2 and L3.
- The sub-phase aggregate verdict (§3.3) is derived from the three per-variant outcomes; it is NOT a substitute for the per-variant outcome.

### 6.3 NG#A1-3 — within-eval ablation control (C-a1-se-r7a-replica) MUST be present

The 5-cell structure (§7) MUST include **C-a1-se-r7a-replica** — a control regressor on R7-A only with symmetric Huber α=0.9 and `sample_weight = 1` (reproduces 27.0d's S-E exactly within tolerance).

- If any C-a1-Lx ≈ C-a1-se-r7a-replica within tolerance (n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5 % magnitude) at the val-selected q\*, that variant is recorded as **PARTIAL_DRIFT_R7A_REPLICA** (§3.2 row 4).
- The control's purpose is to **detect zero-effect outcomes** analogous to 27.0f-β's H-B6 FALSIFIED_R7C_INSUFFICIENT (C-se-rcw ≈ C-se-r7a-replica).
- Omitting the control cell is **NOT admissible** under NG#A1-3.

---

## 7. Cell structure (5 cells × 5 quantiles = 25 cell × q pairs)

The β-eval evaluates **5 cells**, each over a 5-quantile family {5, 10, 20, 30, 40}, producing 25 (cell, q) pairs.

| # | Cell ID | Picker / score | Feature set | Loss / objective | Sample weight | Purpose |
|---|---|---|---|---|---|---|
| 1 | **C-a1-L1** | S-E (regressor_pred) | R7-A only | Huber, α=0.9, **magnitude-weighted** | `min(\|realised_pnl_pip\|, 30.0)` | A1 variant 1 — magnitude-weighting test |
| 2 | **C-a1-L2** | S-E (regressor_pred) | R7-A only | **Asymmetric Huber**, δ_pos=0.5, δ_neg=1.5 | 1 (built into custom objective) | A1 variant 2 — asymmetry test |
| 3 | **C-a1-L3** | S-E (regressor_pred) | R7-A only | Huber, α=0.9, **spread-cost-weighted** | `1 + 0.5 × spread_at_signal_pip` | A1 variant 3 — spread-regime training-time test |
| 4 | **C-a1-se-r7a-replica** | S-E (regressor_pred) | R7-A only | Huber, α=0.9, **symmetric** (27.0d S-E) | 1 (control) | Within-eval ablation control (NG#A1-3); detects PARTIAL_DRIFT outcomes |
| 5 | **C-sb-baseline** | S-B raw (P(TP) − P(SL)) | R7-A only | Multiclass CE (S-B classifier) | 1 | §10 baseline reproduction FAIL-FAST (NG#A1-3 / §8) |

### 7.1 D10 4-artifact form (extension of 27.0f 3-artifact)

The β-eval will fit:

- **3 regressor artifacts** (L1 / L2 / L3) on R7-A train (R7-A-clean parent row-set; NO R7-C row-drop in this sub-phase)
- **1 control regressor artifact** (C-a1-se-r7a-replica; symmetric Huber, `sample_weight=1`)
- **1 multiclass head artifact** (C-sb-baseline; LightGBMClassifier multiclass)

Each artifact is fit **once**; predictions are computed on val / test once. The 5 cells × 5 quantiles share these 5 artifacts (no per-cell re-fit).

### 7.2 Row-set policy (A1-specific; no R7-C drop)

Since R7-C is out-of-scope for this sub-phase (§5.2), the Fix A row-set isolation contract (developed at 27.0f-β; PR #332) does **not** apply here. All 5 cells share the **R7-A-clean parent row-set**. This is simpler than 27.0f-β's mixed row-set design and preserves the §10 baseline reproduction by construction.

---

## 8. C-sb-baseline reproduction FAIL-FAST gate

The β-eval embeds the **C-sb-baseline reproduction check** inherited from 27.0c-α §7.3 / 27.0d / 27.0e / 27.0f. The check runs after all 5 cells have been evaluated and before any verdict is emitted.

| Metric | §10 baseline (immutable; PR #335 §10) | Tolerance |
|---|---|---|
| n_trades (test, val-selected q\*=5 on C-sb-baseline) | 34,626 | exact (±0) |
| Sharpe (test) | -0.1732 | ±1e-4 |
| ann_pnl (test, pip) | -204,664.4 | ±0.5 |

**Mismatch behaviour**: `BaselineMismatchError` HALT — the sub-phase β-eval terminates without emitting a verdict. This is **FAIL-FAST**. Inherited harness: `check_c_sb_baseline_match()` (analogous to 27.0c / 27.0d / 27.0e / 27.0f). The check guards against any unintended side-effect of the 3 loss variants on the baseline reproduction (e.g., if the sample_weight pipeline accidentally affects the multiclass head).

---

## 9. Selection-overfit guard (2-layer; verbatim from Phase 27 sub-phase 群)

The β-eval respects the 2-layer selection-overfit guard inherited from PR #325 / #328 / #332:

### 9.1 Layer 1 — validation-only (cell\*, q\*) selection

The val-selected (cell\*, q\*) record is the **only** record used for formal H-C1 verdict scoring. Other (cell, q) records are computed for diagnostic purposes (per-variant comparison, OOF diagnostic, top-tail audit), labelled DIAGNOSTIC-ONLY in the eval_report, and **not** used in the formal verdict ladder.

### 9.2 Layer 2 — cross-cell aggregation

After the val-selected (cell\*, q\*) is fixed for each cell, the aggregate verdict over all 5 cells follows the Phase 27 aggregation rule:

- All cells REJECT → **REJECT_NON_DISCRIMINATIVE**.
- 1+ cell PASS, other cells REJECT → **SPLIT_VERDICT_ROUTE_TO_REVIEW**.
- All cells PASS → would be **ADOPT_CANDIDATE_PENDING_OOS**, but **capped at PROMISING_BUT_NEEDS_OOS** by the ADOPT_CANDIDATE wall (§12; NG#10 / NG#11 not relaxed).

The cross-cell aggregation is computed on the 4 candidate cells (C-a1-L1 / L2 / L3 / se-r7a-replica). C-sb-baseline is the **control** for §10 reproduction, not a candidate cell.

---

## 10. Validation-only selection; test touched once

Binding contract from Phase 27 sub-phase 群 carried verbatim into 28.0a:

- The β-eval computes test-set metrics for **all 25 (cell, q) pairs** but **only the val-selected (cell, q) per cell** contributes to the formal H-C1 verdict.
- All other test-set metrics in the eval_report are labelled **DIAGNOSTIC-ONLY** and are excluded from H-C1 outcome row binding.
- The 5-fold OOF correlation diagnostic is computed on train only (using `seed = 42` fold assignment inherited from 27.0d / 27.0f). It is **DIAGNOSTIC-ONLY** and does not contribute to the formal verdict.

This is enforced by the inherited `evaluate_cell_*` and `select_cell_validation_only` harness functions (analogous to the 27.0f-β implementation in `scripts/stage27_0f_s_e_r7_c_regime_eval.py`).

---

## 11. eval_report.md — 25-section pattern inherited

The β-eval emits `artifacts/stage28_0a/eval_report.md` with the same 25-section pattern as 27.0f-α §11 / D-AA14. Per-section content adapted for A1:

| § | Section | Adaptation for A1 |
|---|---|---|
| 1 | Executive summary | 4-row outcome ladder per variant; aggregate verdict; baseline reproduction status |
| 2 | Cells overview | 5 cells (L1 / L2 / L3 / se-r7a-replica / sb-baseline) |
| 3 | Row-set / drop stats | R7-A-clean parent row-set (no R7-C drop in this sub-phase); §3 will be near-empty |
| 4 | Sanity probe results | Class priors / per-pair TIME-share / D-1 binding check / R7-A NaN check / R7-A positivity check (carried from 27.0f-α §10 items 1–13) |
| 5 | OOF correlation diagnostic (DIAGNOSTIC-ONLY) | Pearson / Spearman per variant on train (3 variants × 1 OOF = 3 diagnostics) |
| 6 | Regression diagnostic per cell | per-cell train / val / test R² / MAE / MSE for the 4 regressor cells |
| 7 | Quantile-family summary per cell | 25 (cell × q) pairs with val Sharpe / val n / test Sharpe / test n / test ann_pnl / test Spearman |
| 8 | Val-selection (cell\*, q\*) | per-cell val-selected record |
| 9 | Cross-cell aggregate verdict | per Layer 2 (§9.2) |
| 10 | §10 baseline reproduction | n_trades / Sharpe / ann_pnl deltas |
| 11 | Within-eval ablation drift (per variant vs C-a1-se-r7a-replica) | per-variant Δ test_sharpe / Δ test_n / Δ ann_pnl vs control; PARTIAL_DRIFT_R7A_REPLICA outcome flag |
| 12 | Feature importance per loss variant | LightGBM `feature_importances_` for each of L1 / L2 / L3 / control regressors |
| 13 | H-C1 outcome row binding | per-variant outcome (1 of 4 rows in §3.2) |
| 14 | Trade-count budget audit | per quantile q ∈ {5, 10, 20, 30, 40} on each cell |
| 15 | Pair concentration | per cell per q top-3 pairs and Herfindahl |
| 16 | Direction balance | long / short counts per cell per val-selected q |
| 17 | Per-pair Sharpe contribution | per cell per val-selected q |
| 18 | Top-tail regime audit (DIAGNOSTIC-ONLY) | per variant on val at q ∈ {10, 20}; spread / volume / high-spread-low-vol summary |
| 19 | R7-A new-feature NaN check | inherited from 27.0f-α §10 item 6 |
| 20 | Realised-PnL distribution by class | TP / SL / TIME mean / p5 / p50 / p95 on train (sanity probe item 4) |
| 21 | Timing breakdown | per-stage timer (R7-A label load, regressor fits, predict, evaluate) |
| 22 | References | PR #316 / #325 / #328 / #332 / #334 / #335 / #336 |
| 23 | Caveats | DIAGNOSTIC-ONLY labels; ADOPT_CANDIDATE wall; H2 PASS = PROMISING_BUT_NEEDS_OOS only |
| 24 | Cross-validation re-fits diagnostic | inherited from 27.0f-α §10 |
| 25 | Sub-phase verdict snapshot | per-variant outcome + aggregate verdict + routing implication |

---

## 12. H1 / H2 / H3 / H4 verdict ladder preservation

The verdict ladder is inherited verbatim from Phase 27 sub-phase 群 (PR #325 §X / #328 / #332):

| Layer | Meaning | Pass condition for C-a1-Lx cell |
|---|---|---|
| **H1m** | Spearman(score, realised_pnl) on val-selected (cell\*, q\*) | ≥ +0.30 (rolled forward from 27.0d S-E's +0.438) |
| **H2** | Val Sharpe lift vs §10 baseline | ≥ +0.05 absolute (i.e., val Sharpe ≥ -0.1363) |
| **H3** | Trade count on val-selected q\* | ≥ 20,000 (avoids degenerate low-trade Sharpe lifts) |
| **H4** | Formal test Spearman (DIAGNOSTIC-ONLY) | logged for test-touched-once consistency check |

### 12.1 ADOPT_CANDIDATE wall (binding constraint)

H2 PASS combined with H1m / H3 / H4 PASS produces verdict **PROMISING_BUT_NEEDS_OOS only** — **never** ADOPT_CANDIDATE. The ADOPT_CANDIDATE wall is preserved; NG#10 / NG#11 are not relaxed. Any future production deployment of a PROMISING_BUT_NEEDS_OOS result requires:

- X-v2 OOS gating (binding constraint §13)
- Phase 22 frozen-OOS contract preservation
- γ closure PR #279 not violated

### 12.2 What 28.0a-β can and cannot conclude

- **Can conclude**: H-C1 PASS / PARTIAL_SUPPORT / FALSIFIED_OBJECTIVE_INSUFFICIENT / PARTIAL_DRIFT_R7A_REPLICA per variant; aggregate sub-phase verdict; routing implication for Phase 28 second-mover.
- **Cannot conclude**: ADOPT_CANDIDATE (capped at PROMISING_BUT_NEEDS_OOS); production deployment authorisation; modification of §10 baseline numeric; modification of any prior Phase 25 / 26 / 27 verdict.

---

## 13. Binding constraints (verbatim)

This memo preserves every constraint binding at the end of Phase 27 and at Phase 28 kickoff (PR #335 §13). They remain binding throughout 28.0a-α / 28.0a-β:

- D-1 bid/ask executable harness preserved
- validation-only selection
- test touched once
- ADOPT_CANDIDATE wall preserved
- H2 PASS = PROMISING_BUT_NEEDS_OOS only
- NG#10 / NG#11 not relaxed
- γ closure PR #279 preserved
- X-v2 OOS gating remains required for any future production deployment
- Phase 22 frozen-OOS contract preserved
- production v9 20-pair (Phase 9.12 closure tip `79ed1e8`) untouched
- §10 baseline immutable (no numeric change in this PR or in the future β-eval)
- R7-A subset preserved; no R7-C addition in this sub-phase
- no scope amendment required (per Phase 28 kickoff §15)
- MEMORY.md unchanged inside this PR
- doc-only
- no implementation in this PR
- no eval in this PR
- no production change in this PR
- no auto-route after merge

The β-eval implementation PR will inherit all of these constraints unchanged.

---

## 14. What this PR is NOT

This PR is **NOT**:

1. The β-eval implementation (`scripts/stage28_0a_a1_objective_redesign_eval.py`). That is a **separate later PR**.
2. The β-eval results (`artifacts/stage28_0a/eval_report.md`, `aggregate_summary.json`, `sweep_results.parquet`, etc.). That is the **β-eval PR's output**.
3. The β-eval unit tests (`tests/unit/test_stage28_0a_a1_objective_redesign_eval.py`). Also β-eval PR.
4. A scope amendment (none required under Phase 28 kickoff §15 for A1 objective redesign).
5. An R-T1 / R-B / R-T3 elevation.
6. An A4 / A0 / A2 / A3 dissent elevation.
7. A modification to the §10 baseline numeric.
8. A modification to any prior Phase 25 / 26 / 27 verdict.
9. A modification of any Phase 28 kickoff (PR #335) admissibility decision.
10. An authorisation to touch `src/` / `scripts/` / `tests/` / `artifacts/` / `.gitignore` / `MEMORY.md`.
11. A production change. Production v9 20-pair untouched.
12. An auto-route trigger for any future action.

The next Phase 28 step (28.0a-β implementation PR) requires a **separate later user routing decision**.

---

## 15. Pre-stated open items (carried into 28.0a-β β-eval PR)

The following items are pre-stated at α and will be resolved at β-eval implementation time. The β-eval PR must address each one without modifying the closed allowlist (§4) or the anti-collapse guards (§6).

### 15.1 Implementation notes declared at α (not implemented here)

- **L1 magnitude-weighted Huber**: implementable via sklearn `lightgbm.LGBMRegressor.fit(X, y, sample_weight=w_L1)` where `w_L1 = np.minimum(np.abs(realised_pnl_pip_train), 30.0)`. **No custom objective needed.** The existing 27.0d S-E pipeline can be extended with one `sample_weight=` argument.
- **L2 asymmetric Huber**: will likely require **LightGBM custom objective** via `lightgbm.Booster.train(..., obj=asymmetric_huber_obj)` where `asymmetric_huber_obj(preds, dtrain)` returns `(grad, hess)` computed per the formula. The sklearn API does not natively support custom asymmetric objectives. The β-eval PR must implement the custom objective callable with closed-form `grad` and `hess`.
- **L3 spread-cost-weighted Huber**: implementable via sklearn API `sample_weight=w_L3` where `w_L3 = 1.0 + 0.5 * spread_at_signal_pip_train`. **No custom objective needed.**
- **All per-row weights computed on R7-A-clean parent row-set** (no R7-C row-drop applied; the train row-set is the full R7-A-clean train of ~2.94M rows).
- **C-a1-se-r7a-replica uses `sample_weight = 1`** (or `sample_weight=None`, equivalent in sklearn API). The control reproduces 27.0d-β's S-E within tolerance.
- **OOF fold assignment uses `seed = 42`** (inherited from 27.0d / 27.0f). The same fold assignment is used across all 3 variants for direct per-variant OOF comparability.
- **Implementation details are deferred to 28.0a-β**. The α memo declares the contract; the β PR writes the code.

### 15.2 Items the β-eval PR must pre-state at β-time

- **β-eval branch name**: `research/phase28-0a-beta-a1-objective-redesign` (suggested; β-eval PR confirms)
- **β-eval script name**: `scripts/stage28_0a_a1_objective_redesign_eval.py` (suggested)
- **β-eval test file**: `tests/unit/test_stage28_0a_a1_objective_redesign_eval.py` (suggested)
- **β-eval artifact directory**: `artifacts/stage28_0a/` (gitignore entries added in β-eval PR)
- **L2 custom objective unit tests**: at least 4 (gradient sign for under-prediction; gradient sign for over-prediction; hess positivity; sample-weight pass-through)
- **Per-variant FAIL-FAST guards**: per-variant R-row positivity, per-variant SanityProbe items, per-variant 25-section eval_report content
- **NG#A1-1 / NG#A1-2 / NG#A1-3 enforcement at β**: the β-eval PR must include unit tests verifying that the 3 variants are exactly the closed allowlist, with the pre-stated numerics, and that the control cell is present

### 15.3 Items NOT to be decided at β (require memo amendment back to α)

- Changes to `w_clip` / `δ_pos` / `δ_neg` / `γ` values
- Addition of a 4th loss variant
- Removal of any of L1 / L2 / L3
- Removal of the C-a1-se-r7a-replica control
- Changes to the quantile family {5, 10, 20, 30, 40}
- Changes to the OOF seed (42)
- Changes to the 5-cell structure (§7)

Any of these requires an **amendment PR** back to 28.0a-α before the β-eval implementation can proceed.

---

## 16. References

**Phase 28**:
- PR #335 — Phase 28 kickoff (`docs/design/phase28_kickoff.md`; A1 admissible at §5.2; amendment policy §15)
- PR #336 — Phase 28 first-mover routing review (`docs/design/phase28_first_mover_routing_review.md`; A1 primary §14.1; H-C1 placeholder §5.3)

**Phase 27 (inheritance / template)**:
- PR #316 — Phase 27 kickoff (template for sub-phase α design memos)
- PR #325 — Phase 27.0d-β S-E regression on realised PnL (A1's direct predecessor; symmetric Huber α=0.9; ranking signal +0.438)
- PR #327 — Phase 27.0e-α S-E quantile-trim design memo (D-Z4 quantile family decision; carried forward to {5, 10, 20, 30, 40})
- PR #328 — Phase 27.0e-β S-E quantile-trim eval (top-tail adversarial pattern; H-B5 PARTIAL_SUPPORT)
- PR #331 — Phase 27.0f-α S-E + R7-C design memo (3-cell structure template; D10 3-artifact form template; 25-section eval_report template)
- PR #332 — Phase 27.0f-β S-E + R7-C eval (Fix A row-set isolation contract; PARTIAL_DRIFT_R7A_REPLICA outcome template; H-B6 FALSIFIED_R7C_INSUFFICIENT)
- PR #334 — Phase 27 closure memo (5-eval evidence picture; H-B3 partial; H-B7 / H-B8 / H-B9 carry-forward; §10 baseline source)

**Binding contracts**:
- PR #279 — γ closure
- Phase 22 frozen-OOS contract
- X-v2 OOS gating
- Phase 9.12 production v9 closure tip `79ed1e8` (production v9 20-pair, untouched throughout Phase 27 and Phase 28 kickoff)

---

*End of `docs/design/phase28_0a_alpha_a1_objective_redesign_design_memo.md`.*
