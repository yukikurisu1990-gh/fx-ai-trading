# Phase 28.0c-α — A0-narrow Tabular Architecture-Topology Audit Design Memo

**Type**: doc-only sub-phase α design memo
**Status**: pre-states Phase 28.0c-β scope; does NOT initiate the β-eval
**Branch**: `research/phase28-0c-alpha-a0-architecture-redesign`
**Base**: master @ `831de0c` (post-PR #343 / Phase 28 post-28.0b routing review)
**Pattern**: analogous to PR #337 (28.0a-α A1) / PR #341 (28.0b-α A4) sub-phase α design memos
**Date**: 2026-05-18

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Phase 28.0c-α design memo**. It pre-states the **closed 4-architecture allowlist** under **A0-narrow** scope (AR1 hierarchical / AR2 pair-conditioned / AR3 stacked / AR4 deterministic regime split), the **fixed feature surface / target / selection rule**, the **6-cell structure**, the **D10 architecture-multi-artifact form**, the **formal H-C3 falsifiable hypothesis with 4-outcome ladder**, and the **3 anti-collapse guards (NG#A0-1 / NG#A0-2 / NG#A0-3)**. It also formally declares **A0-broad (sequence / NN model classes) deferred-not-foreclosed** — admissible via a separate scope amendment if Path A all-FALSIFIED triggers post-28.0c re-routing. It does **NOT**:*
>
> - *initiate the β-eval (no `scripts/stage28_0c_*.py`, no `tests/unit/test_stage28_0c_*.py`, no `artifacts/stage28_0c/`);*
> - *create any scope amendment (none required under Phase 28 kickoff §15 for A0-narrow; A0-broad scope amendment is a separate later PR if elevated);*
> - *elevate R-B / R-T3 (carry-forward register status preserved per PR #334 + updates by PR #339 / PR #343);*
> - *modify the §10 baseline numeric or any prior verdict.*
>
> *The β-eval implementation (PR `phase28-0c-beta-...`) is a **separate later PR**. The pre-stated parameters and the closed 4-architecture allowlist are fixed at α and cannot be changed at β; any change requires a memo amendment PR back to α. The Path A / Path B selection is **Path A (A0-narrow; no scope amendment)** by this design memo merge; Path B (A0-broad; sequence / NN) remains deferred-not-foreclosed.*

Same approval-then-defer pattern as PR #337 / PR #341.

---

## 1. A0-narrow mission statement

**Phase 28.0c is an A0-narrow tabular architecture-topology audit, not the full A0-broad sequence/NN redesign.**

The 7-eval evidence picture consolidated at PR #343 §3.1 shows the val-selector picked the inherited C-sb-baseline cell in 7/7 sub-phases. Channel B (score / objective; 6 variants), Channel C (selection rule; 5 variants), and Channel A (feature / regime-statistic; 1 variant) are exhausted at this tabular LightGBM architecture. H-B9 (seam exhausted at this architecture) is the strongest carry-forward hypothesis with 7 supporting data points.

A0 axis (Phase 28 kickoff PR #335 §5.1) attacks H-B9 by changing the model class itself. The **full A0** axis includes both:

- **A0-narrow**: tabular-LightGBM topology variants (hierarchical / pair-conditioned / stacked / deterministic regime split) — same model class with different topology
- **A0-broad**: structurally different model classes (sequence models — RNN / temporal CNN / Transformer — or neural networks with multi-head outputs) — requires new training pipeline, GPU dependency, and likely new windowed/path feature surface

**This sub-phase tests A0-narrow only.** A0-broad is **deferred-not-foreclosed** — admissible via a separate Phase 28 scope amendment PR if Path A (this sub-phase) all-FALSIFIED triggers a post-28.0c routing decision (§17 open question 1).

The mission is **NOT** to claim that A0 is exhausted if AR1-AR4 all fail. The mission is to test whether **tabular topology variation** can lift Sharpe above §10 baseline. A negative result falsifies **A0-narrow**, not all A0. The post-28.0c routing review will explicitly compare A0-broad scope-amendment elevation vs Phase 28 closure / Phase 29 rebase as the next routing question (§16 / §17).

This is A0 admissible per Phase 28 kickoff PR #335 §5.1, promoted to primary at post-28.0b routing review PR #343 §14.1 (prior 35-45 %; H-B9 most directly attacked). The β-eval will be implemented in a separate later PR (`phase28-0c-beta-...`).

---

## 2. Why A0-narrow is NOT Phase 27 / 28 inertia (6 distinctions)

Phase 28 kickoff PR #335 §3 listed five Phase 27 inertia routes that are NOT admissible. 28.0a-α §2 added A1 single-loss-variant micro-redesign; 28.0b-α §2 added R-T2 and selection-rule-only inertia routes. A0-narrow's design must be structurally distinct from each, and from sibling Phase 28 axes A2 / A3 / R-B.

### 2.1 A0-narrow ≠ score-axis micro-redesign (27.0b/c/d + 28.0a all 6 variants)

- **Phase 27 / 28.0a score / objective variants**: same model class (LightGBMRegressor / Classifier on R7-A) with different score formulations.
- **A0-narrow**: same R7-A feature surface, but **different model topology** (multi-stage / per-pair specialists / blended / regime-conditioned). The score arises from the topology, not from a loss-function change.

### 2.2 A0-narrow ≠ R-T2 quantile trim / 28.0b R1-R4 selection-rule redesign

- **27.0e R-T2 / 28.0b R1-R4**: same model class and same training pipeline, with different selection rules over the same score.
- **A0-narrow**: **selection rule fixed** at top-q on score (quantile family {5, 10, 20, 30, 40}; same as §10 baseline + C-a4-top-q-control). Only the **model that produces the score** changes.

**Caveat (AR1 inertia risk)**: AR1 hierarchical two-stage uses a stage-1 admission threshold (top 50% per-pair val-median) that **resembles** an absolute-threshold selection rule (28.0b R1). A0-narrow admits AR1 because the threshold's purpose is **architecture conditioning** (stage 2 trains only on stage-1-admitted rows; the regressor itself differs), **not** the final selection rule (the final selection still applies top-q on stage-2 score per the §10 baseline rule). NG#A0-1 (§6) enforces this distinction at β.

### 2.3 A0-narrow ≠ 27.0f R7-C feature widening / 28.0a L3 spread-cost weighting / 28.0b R3 per-pair quantile

- **Phase 27 R7-C + 28.0a L3 + 28.0b R3**: regime-axis attacks via feature widening / training-time loss weighting / per-pair selection quantile, respectively. All three FALSIFIED.
- **A0-narrow**: AR4 deterministic regime split is **structurally distinct** — regime conditioning enters as a per-row architectural routing rule (which model fits this row) at both training and inference time, **not** as a feature, a loss weight, or a selection threshold. AR4 is a **boundary case** to A3 (§3.2 below); admitted but flagged.

### 2.4 A0-narrow ≠ 28.0a A1 objective redesign

- **28.0a A1**: same model class (LightGBMRegressor on R7-A) with different loss functions (L1 / L2 / L3).
- **A0-narrow**: **loss fixed** (symmetric Huber α=0.9 inherited from 27.0d S-E across all AR variants; sample_weight=1; identical hyperparameters per AR2 D-BC6). Topology changes; loss does not.

### 2.5 A0-narrow ≠ C-sb-baseline-anchored sweep

- **C-sb-baseline-anchored sweep**: any sub-phase that only redefines q% / score on the inherited C-sb-baseline cell.
- **A0-narrow**: builds **new architecture cells** (C-a0-AR1 / AR2 / AR3 / AR4) by fitting structurally distinct artifacts. C-sb-baseline is preserved as the FAIL-FAST reproduction cell only.

### 2.6 A0-narrow ≠ A2 / A3 / R-B (sibling Phase 28 axes)

See §3 for axis-purity declaration.

---

## 3. A0-narrow vs A2 / A3 / R-B axis purity

A0-narrow attacks **model class topology only**. Sibling axes are preserved untouched:

### 3.1 A0-narrow ≠ A2

- A2 (target redesign) would change the realised-PnL target. A0-narrow **preserves the target** verbatim (triple-barrier realised PnL; K_FAV=1.5×ATR; K_ADV=1.0×ATR; H_M1=60; bid/ask executable per D-1).
- All 4 AR variants train against the same realised-PnL target.

### 3.2 A0-narrow ≠ A3 (boundary-sensitive at AR4)

- A3 (regime-conditioned modeling) would use **learned gating / mixture-of-experts / per-regime training with adaptive routing**. A0-narrow's AR4 uses **deterministic regime split** (per-pair val-median `atr_at_signal_pip`; fit on val once, applied at inference without adaptation). The split rule is pre-stated at α; not learned at β.
- **AR4 is boundary-sensitive but admissible under A0-narrow**: it tests whether a fixed regime-axis architectural decomposition (two LightGBMRegressors, one per regime) lifts Sharpe. A3 elevation (learned gating / MoE) requires a separate scope amendment and a separate sub-phase. **AR4 inertia risk: A3-adjacent** (see §12.4).
- The Phase 27 R7-C / 28.0a L3 / 28.0b R3 regime-axis falsifications add cumulative negative evidence; AR4 is structurally distinct but the prior is penalised.

### 3.3 A0-narrow ≠ R-B

- R-B (different feature axis) would add new closed-allowlist features beyond R7-A (e.g., path-shape, microstructure, multi-TF context). A0-narrow **preserves the R7-A feature surface** unchanged (4 features: pair / direction / atr_at_signal_pip / spread_at_signal_pip).
- AR4 uses `atr_at_signal_pip` only as a routing input (not as a learned feature inside the per-regime regressors; the per-regime regressors still see the full R7-A surface). No new feature class is introduced.

---

## 4. Closed 4-architecture allowlist (formal pre-statement)

**All AR1-AR4 variants remain within tabular LightGBM. Therefore, a negative result falsifies A0-narrow, not all possible A0.** A0-broad (sequence / NN) remains deferred-not-foreclosed (§7).

The four architecture variants are **fixed at α** and cannot be modified at β. Any change requires a memo amendment PR back to α.

### 4.1 AR1 — Hierarchical two-stage (candidate → confirm)

- **Stage 1**: LightGBMClassifier (S-B multiclass on R7-A) producing P(TP) − P(SL) score. Fit on full R7-A-clean train.
- **Stage-1 admission threshold**: rows with stage-1 score > **per-pair val-median of stage-1 score** (deterministic; α-fixed at the **top 50% per pair**; same fit method as 28.0b R1).
- **Stage 2**: LightGBMRegressor (S-E backbone; symmetric Huber α=0.9; sample_weight=1) **trained only on stage-1-admitted train rows**. The conditional training set is the architectural change.
- **Inference**: predict stage-1 score on val / test → apply per-pair threshold → admitted rows get stage-2 score predicted by the conditional regressor.
- **Selection**: top-q on stage-2 score with quantile family {5, 10, 20, 30, 40} (inherited).
- **A4 inertia caveat**: stage-1 admission threshold resembles 28.0b R1 absolute-threshold rule. AR1 admits this threshold because its purpose is **architectural conditioning of stage 2's training set**, not the final monetisation rule. NG#A0-1 (§6) enforces.

### 4.2 AR2 — Pair-conditioned specialist heads

- **Architecture**: 20 LightGBMRegressors, one per pair. Each specialist is trained **only on its pair's train rows** and uses the **27.0d S-E backbone verbatim** (symmetric Huber α=0.9; sample_weight=1; identical hyperparameters; D-BC6 per-pair hyperparameter tuning is **NOT admissible** per NG#A0-1).
- **Inference**: route each val / test row by its `pair` feature to the corresponding specialist. The pair-routing dictionary maps `pair_str → specialist_artifact`.
- **Selection**: top-q on the routed-specialist score with quantile family {5, 10, 20, 30, 40}.
- **Rationale**: tests whether **cross-pair training contamination** (current 27.0d C-se trains on all 20 pairs jointly) is the bottleneck. Per-pair specialists eliminate cross-pair information flow at training time.

### 4.3 AR3 — Stacked classifier+regressor blend

- **Architecture**: train S-B multiclass (P(TP) − P(SL)) and S-E regressor separately on R7-A train (same as 27.0d / 28.0a structure). Combine scores via fixed-weight blend at inference.
- **Blend formula**: `score_blend = 0.5 * rank_normalised(S-B raw) + 0.5 * rank_normalised(S-E)` where `rank_normalised(x) = pd.Series(x).rank(pct=True).to_numpy()` produces uniform[0, 1] transform per-cell.
- **Blend weight**: **0.5 / 0.5** (equal; α-fixed; no grid sweep; D-BC4 confirmed).
- **Inference**: predict S-B raw + S-E on val / test; rank-normalise per cell; blend → score_blend; top-q selection.
- **Rationale**: tests whether **classifier and regressor produce orthogonal information** that, when combined, lifts Sharpe. If a 50/50 blend produces strictly worse than the better of S-B and S-E, the two heads are redundant; if it produces strictly better, ensemble blending becomes a routing candidate.

### 4.4 AR4 — Deterministic regime split

- **Architecture**: 2 LightGBMRegressors (S-E backbone; same hyperparameters as 27.0d):
  - **High-vol specialist**: trained on rows where `atr_at_signal_pip > per-pair val-median atr_at_signal_pip`.
  - **Low-vol specialist**: trained on rows where `atr_at_signal_pip <= per-pair val-median atr_at_signal_pip`.
- **Regime split**: **per-pair val-median `atr_at_signal_pip`** (deterministic; α-fixed; D-BC7 confirmed). Per-pair granularity adapts to per-pair volatility scales.
- **Inference**: each val / test row is routed by its pair's val-median `atr_at_signal_pip` threshold to high-vol or low-vol specialist.
- **Selection**: top-q on routed-specialist score with quantile family {5, 10, 20, 30, 40}.
- **A3 boundary caveat (§3.2)**: AR4 is regime-axis-conditioned but uses **deterministic** routing (no learned gating, no MoE, no adaptive weights). A3 elevation requires separate scope amendment. NG#A0-1 (§6) enforces. Inertia risk: **high** (§12.4) — cumulative regime-axis negative evidence from 27.0f / 28.0a L3 / 28.0b R3.

### 4.5 Why 4 architectures exactly (closed allowlist)

The 4 variants jointly span four orthogonal hypotheses about tabular topology:

- **AR1**: "the issue is that score and selection are decoupled; conditional regression on top-half candidates helps"
- **AR2**: "the issue is cross-pair training contamination; per-pair specialists help"
- **AR3**: "the issue is information loss from picking only one head; classifier+regressor ensemble helps"
- **AR4**: "the issue is regime mixing; per-regime specialists help (architecturally, not as features)"

All 4 remain **within tabular LightGBM**. Therefore, **a negative result falsifies A0-narrow, not all possible A0**. A0-broad (sequence / NN) tests fundamentally different model classes and remains the natural next move if A0-narrow fails (§7).

### 4.6 No grid sweep within a variant

Within AR1, stage-1 admission percentile is fixed at 50% (no grid over [25%, 50%, 75%]). Within AR2, per-pair hyperparameters are identical (no per-pair tuning grid). Within AR3, blend weight is fixed at 0.5/0.5 (no grid over [0.3/0.7, 0.5/0.5, 0.7/0.3]). Within AR4, regime split feature is `atr_at_signal_pip` at per-pair val-median (no grid over alternate features or split percentiles). **NG#A0-1** enforces.

---

## 5. Fixed feature surface, target, and selection rule

A0-narrow commits to 3 invariants across all 4 AR variants:

- **Feature surface**: **R7-A only** (4 features: `pair`, `direction`, `atr_at_signal_pip`, `spread_at_signal_pip`). No R7-C / R7-D / R7-other. R-B reframing under A0 is NOT exercised here.
- **Target**: triple-barrier realised PnL (K_FAV=1.5×ATR; K_ADV=1.0×ATR; H_M1=60; D-1 bid/ask executable). Unchanged from Phase 27 / 28.0a / 28.0b.
- **Selection rule**: **top-q on candidate score** with quantile family {5, 10, 20, 30, 40} (inherited from 27.0f / 28.0a / 28.0b top-q-control). All 4 AR variants + C-a0-arch-control + C-sb-baseline use this rule for fair cross-comparison.

NG#A0-1 (§6) prevents drift to A1 / A2 / A3 / A4 / R-B inertia by enforcing these invariants.

---

## 6. Anti-collapse guards (NG#A0-1 / NG#A0-2 / NG#A0-3)

### 6.1 NG#A0-1 — closed 4-architecture allowlist, fixed feature / target / rule

The architecture MUST be one of {AR1, AR2, AR3, AR4} as defined in §4 with the α-fixed numerics (AR1 stage-1 50% per-pair val-median; AR2 27.0d S-E verbatim per-pair backbone; AR3 0.5/0.5 blend; AR4 per-pair val-median `atr_at_signal_pip` regime split).

- A 5th architecture variant at β is **NOT admissible** without a memo amendment PR back to α.
- A numeric grid sweep within a variant is **NOT admissible** (NG#A0-1 inheritance from NG#A1-1 / NG#A4-1).
- Sequence / NN model classes are **NOT admissible** without a separate scope amendment PR (Path B; deferred-not-foreclosed per §7).
- Feature surface broadening / target redesign / selection rule redesign / loss change are **NOT admissible** under A0-narrow.

### 6.2 NG#A0-2 — per-architecture verdict required

Each AR variant {AR1, AR2, AR3, AR4} must produce its own outcome per the 4-row ladder (§12). Aggregate-only verdicts (e.g., "average of four variants is PARTIAL_SUPPORT") are **NOT admissible**.

### 6.3 NG#A0-3 — C-a0-arch-control mandatory (rule-axis null + architecture-axis null)

The 6-cell structure (§9) MUST include **C-a0-arch-control** — a vanilla S-E LightGBMRegressor (R7-A; symmetric Huber α=0.9; sample_weight=1; top-q on score; bit-reproduces 27.0d C-se / 28.0a C-a1-se-r7a-replica / 28.0b C-a4-top-q-control).

- If any C-a0-ARx ≈ C-a0-arch-control within tolerance (n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5 %) at the val-selected (cell\*, q\*), the variant is flagged **PARTIAL_DRIFT_ARCH_REPLICA** (§12).
- Omitting C-a0-arch-control is **NOT admissible**.

---

## 7. Scope amendment requirement — Path A default; Path B deferred-not-foreclosed

### 7.1 Path A (default; this PR)

A0-narrow tabular topology variants AR1-AR4 are all admissible under Phase 28 kickoff §15:

- **Feature surface unchanged** (R7-A only) — no Clause 2 amendment for new closed allowlist
- **Target unchanged** (realised PnL) — no target-spec amendment
- **Selection rule unchanged** (top-q on score) — no Clause 2 amendment for non-quantile cells (cf. PR #340 for A4 only)
- **Loss unchanged** (symmetric Huber α=0.9) — no loss-class amendment
- **Model class within tabular LightGBM** — no new compute infrastructure or pipeline class

**No scope amendment required.** Single-PR sequence: 28.0c-α (this PR) → 28.0c-β eval.

### 7.2 Path B — A0-broad deferred-not-foreclosed

**Path B is not included in this PR.** Path B represents the **A0-broad** scope: sequence models (RNN / temporal CNN / Transformer) or neural networks with multi-head outputs that operate on a windowed / sequence input surface. Path B is **admissible in principle** but requires:

- **Separate scope amendment PR** (analogous to PR #340 R7-C / A4 non-quantile cells)
- **Likely a new windowed input feature surface** ("recent N M5 bars" as a sequence representation, or path-shape features as a structured input)
- **New training pipeline / GPU dependency** for non-LightGBM model classes
- **Updated Clause 2** if cell-shape changes (e.g., per-window selection cells instead of per-row)

**If Path A (this sub-phase) results in all AR1-AR4 FALSIFIED or PARTIAL_DRIFT, Path B vs Phase 28 closure must be the next routing review question** (§16 / §17 / PR #343 §16 row 6 trigger). The post-28.0c routing review will explicitly compare:

1. **Path B sequence/NN scope amendment + 28.0d-α A0-broad design memo** (continued architecture-axis attack via fundamentally different model class)
2. **Phase 28 closure / Phase 29 rebase** (architecture / target / data / feature surface jointly redesigned at a fresh phase)

Both options remain open at α. **This PR does not prejudge which is preferable** if Path A fails; the comparison is deferred to the routing review.

### 7.3 Status preserved

A0-broad's deferred-not-foreclosed status is preserved in this design memo. A0-broad revival requires explicit user routing decision + scope amendment PR.

---

## 8. In-scope vs out-of-scope

### 8.1 In-scope (β-eval will exercise these)

- **4 AR variants** R1 / R2 / R3 / R4 from §4 with α-fixed numerics (NG#A0-1)
- **Fixed feature surface, target, selection rule** (§5)
- **6-cell structure**: 4 AR variants + C-a0-arch-control + C-sb-baseline (§9)
- **D-1 bid/ask executable harness** unchanged
- **5-fold OOF (DIAGNOSTIC-ONLY; seed=42)** on control regressor (NG#A0-3 anchor); per-AR OOF is DIAGNOSTIC-approximate (D-BC7)
- **2-layer selection-overfit guard**
- **C-sb-baseline reproduction FAIL-FAST** (§10)
- **C-a0-arch-control drift check vs 27.0d / 28.0a / 28.0b control** (DIAGNOSTIC-ONLY WARN; 5-phase bit-reproduction; §11)
- **20-pair / 730-day / 70-15-15 split** inherited
- **25-section eval_report** inherited from 28.0b-α §14

### 8.2 Out-of-scope

- **Score axis variation** (A1 inertia — score is derived from architecture; loss is fixed)
- **Selection rule redesign** (A4 inertia — selection rule fixed at top-q on score)
- **AR1 stage-1 admission threshold as a selection rule** — stage-1 threshold is **architecture conditioning** for stage 2 (§2.2 caveat); the final selection is top-q on stage-2 score
- **Target redesign** (A2 territory; sibling axis)
- **Feature surface broadening** (R-B / R7-other; sibling axis)
- **Learned gating / MoE / per-regime adaptive routing** (A3 territory; AR4 deterministic regime split only)
- **Sequence / NN model classes** (A0-broad; Path B deferred-not-foreclosed; requires scope amendment)
- **5th AR variant at β** (NG#A0-1)
- **Numeric grid sweep within a variant** (NG#A0-1)
- **Per-pair hyperparameter tuning under AR2** (NG#A0-1; pair-conditioned backbone must be 27.0d S-E verbatim)
- **Path B scope amendment** within this PR (separate later PR if elevated)

---

## 9. Cell structure (6 cells × variable per architecture)

The β-eval evaluates **6 cells**. AR1 / AR2 / AR3 / AR4 are quantile-based variant cells (each with quantile family {5, 10, 20, 30, 40} on their respective scores). C-a0-arch-control and C-sb-baseline retain the inherited quantile family for cross-phase comparability.

| # | Cell ID | Picker / score | Cell shape | Configuration | Purpose |
|---|---|---|---|---|---|
| 1 | **C-a0-AR1** | S-E (stage-2 regressor; cond. on stage-1 ≥ pair-median) | quantile (top-q on stage-2 score) | stage-1: top 50% per-pair val-median admission | A0-narrow AR1 — hierarchical two-stage |
| 2 | **C-a0-AR2** | S-E (per-pair specialist; routed by pair) | quantile (top-q on routed score) | 20 per-pair models; 27.0d S-E verbatim | A0-narrow AR2 — pair-conditioned specialists |
| 3 | **C-a0-AR3** | 0.5·rank_norm(S-B raw) + 0.5·rank_norm(S-E) | quantile (top-q on blended score) | blend weight 0.5/0.5 fixed | A0-narrow AR3 — stacked classifier+regressor |
| 4 | **C-a0-AR4** | S-E (routed by per-pair val-median atr) | quantile (top-q on routed score) | high-vol/low-vol per pair; deterministic split | A0-narrow AR4 — deterministic regime split (A3-adjacent) |
| 5 | **C-a0-arch-control** | S-E (vanilla; sample_weight=1) | quantile (top-q on S-E score) | 27.0d C-se backbone verbatim | NG#A0-3 mandatory; rule-axis + architecture-axis null; reproduces 27.0d / 28.0a / 28.0b control |
| 6 | **C-sb-baseline** | S-B raw (P(TP) − P(SL)) | quantile (top-q on S-B raw) | multiclass S-B head | §10 baseline reproduction FAIL-FAST |

All 6 cells use the **quantile family {5, 10, 20, 30, 40}** (inherited from 27.0f / 28.0a / 28.0b). Total records: 6 cells × 5 quantiles = **30 (cell, q) pairs**.

### 9.1 D10 architecture-multi-artifact form

The β-eval fits the following artifacts:

- **AR1**: 1 stage-1 LightGBMClassifier (S-B multiclass) + 1 stage-2 LightGBMRegressor (S-E backbone, conditional training set) = 2 artifacts
- **AR2**: 20 per-pair LightGBMRegressors = 20 artifacts
- **AR3**: 1 LightGBMClassifier (S-B multiclass; shared with AR1 stage 1 if fits separately is wasteful, but fit-once for cleanliness) + 1 LightGBMRegressor (S-E) = 2 artifacts (or shared with control)
- **AR4**: 2 LightGBMRegressors (high-vol / low-vol per-regime specialists) = 2 artifacts
- **C-a0-arch-control**: 1 vanilla LightGBMRegressor (S-E backbone; sample_weight=1) = 1 artifact (note: may be shared with AR3's S-E if implementation reuses; β-eval design memo decision)
- **C-sb-baseline**: 1 multiclass head = 1 artifact

**Total ≈ 25-28 LightGBM artifacts** (depending on AR3 / control artifact sharing decision). All artifacts fit ONCE on full R7-A-clean train. β-eval implementation must declare the artifact-sharing topology explicitly.

### 9.2 Row-set policy (A0-specific; simpler than 27.0f)

All 6 cells share the **R7-A-clean parent row-set** (no R7-C row-drop; same as 28.0a / 28.0b). Fix A row-set isolation contract is not exercised under A0-narrow.

---

## 10. C-sb-baseline reproduction (FAIL-FAST; inherited)

The β-eval embeds the inherited **C-sb-baseline reproduction check** from 27.0c-α §7.3 / 27.0d / 27.0e / 27.0f / 28.0a / 28.0b. The check runs after all 6 cells have been evaluated and before any verdict is emitted.

| Metric | §10 baseline (immutable; PR #335 §10) | Tolerance |
|---|---|---|
| n_trades (test, val-selected q\*=5 on C-sb-baseline) | 34,626 | exact (±0) |
| Sharpe (test) | -0.1732 | ±1e-4 |
| ann_pnl (test, pip) | -204,664.4 | ±0.5 |

**Mismatch behaviour**: `BaselineMismatchError` HALT — FAIL-FAST. Inherited harness: `check_c_sb_baseline_match()`.

---

## 11. C-a0-arch-control drift check vs 27.0d C-se / 28.0a / 28.0b control (DIAGNOSTIC-ONLY WARN)

C-a0-arch-control reproduces 27.0d C-se with sample_weight=1 (5th bit-tight reproduction in the inheritance chain: 27.0d → 27.0f r7a-replica → 28.0a r7a-replica → 28.0b top-q-control → 28.0c arch-control).

- **Tolerance**: n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5 % of magnitude (inherited)
- **Mismatch behaviour**: `UserWarning`; eval_report records WARN flag; **NO HALT**

---

## 12. H-C3 formal pre-statement (4-outcome ladder per architecture)

PR #343 §7.3 placeholder → formal H-C3.

### 12.1 H-C3 hypothesis (formal)

> **H-C3 (A0-narrow scope)**: At least one of the four closed tabular architecture variants {AR1, AR2, AR3, AR4} will produce a val-selected configuration on the C-a0-ARx cell satisfying **all** of:
>
> 1. **H2 PASS**: val Sharpe ≥ §10 baseline + **+0.05 absolute** (val Sharpe ≥ -0.1363)
> 2. **H1m preserved**: val-selected cell Spearman ≥ **+0.30** (the score depends on the architecture; spearman threshold rolled forward)
> 3. **H3 PASS**: trade count ≥ **20,000**
> 4. **C-sb-baseline reproduction PASS** (FAIL-FAST gate)
>
> **OR** H-C3 is FALSIFIED at the variant.

### 12.2 H-C3 falsification interpretation — FALSIFIED_A0_NARROW vs FALSIFIED_ALL_A0

This is a load-bearing distinction. **H-C3 falsification under this sub-phase is bounded by the A0-narrow scope.**

- **If all 4 AR variants FALSIFIED** (any combination of row 2 PARTIAL_SUPPORT, row 3 FALSIFIED_ARCH_INSUFFICIENT, row 4 PARTIAL_DRIFT_ARCH_REPLICA) → the result is **FALSIFIED_A0_NARROW**, not FALSIFIED_ALL_A0.
- **A0-broad (sequence / NN model classes) remains deferred-not-foreclosed**. A negative A0-narrow result does NOT prove that no architecture change can lift Sharpe. It proves that **tabular LightGBM topology variations** within the closed 4-variant allowlist do not lift Sharpe.

**This PR explicitly does not claim FALSIFIED_ALL_A0 under any β outcome.** The post-28.0c routing review (separate PR) will compare:

1. A0-broad scope amendment (sequence / NN; Path B)
2. Phase 28 closure / Phase 29 rebase

as the two next-routing options if Path A all-FALSIFIED.

### 12.3 4-outcome ladder per architecture (precedence row 4 > 1 > 2 > 3)

The β-eval emits **one of four outcomes** for each AR variant. Precedence is enforced (PARTIAL_DRIFT_ARCH_REPLICA checked first per NG#A0-3).

| Row | Outcome | Per-architecture condition | Aggregate implication |
|---|---|---|---|
| **4** | **PARTIAL_DRIFT_ARCH_REPLICA** (checked first) | C-a0-ARx ≈ C-a0-arch-control (val-selected q\*) within tolerance (n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5 %) | Architecture had zero effect on monetization; analogous to 27.0f H-B6 / 28.0a H-C1 row 4 / 28.0b H-C2 row 4. Strong "model-class agnostic" result if all 4. |
| **1** | **PASS** | All 4 H-C3 conditions (§12.1) satisfied | If 1+ rule PASS → SPLIT_VERDICT_ROUTE_TO_REVIEW (PROMISING_BUT_NEEDS_OOS candidate; ADOPT_CANDIDATE wall preserved per Clause 1). |
| **2** | **PARTIAL_SUPPORT** | val Sharpe lift ∈ [+0.02, +0.05) AND other intact | If 1+ PARTIAL_SUPPORT and 0 PASS → REJECT_NON_DISCRIMINATIVE (sub-threshold). |
| **3** | **FALSIFIED_ARCH_INSUFFICIENT** (default) | val Sharpe lift < +0.02 OR other H-C3 conditions fail | If all 4 FALSIFIED → REJECT_NON_DISCRIMINATIVE; **FALSIFIED_A0_NARROW**; route to post-28.0c review for Path B vs Phase 28 closure. |

### 12.4 Aggregate decision rule

- If **any AR variant** records PASS → **SPLIT_VERDICT_ROUTE_TO_REVIEW**.
- If **0 AR variants** PASS but **1+ AR variant** PARTIAL_SUPPORT → **REJECT_NON_DISCRIMINATIVE** (sub-threshold).
- If **all 4 AR variants** FALSIFIED_ARCH_INSUFFICIENT OR PARTIAL_DRIFT_ARCH_REPLICA → **REJECT_NON_DISCRIMINATIVE** with **FALSIFIED_A0_NARROW** diagnostic note: "tabular topology variants insufficient; A0-broad remains deferred-not-foreclosed; route to post-28.0c routing review for Path B vs Phase 28 closure comparison."

---

## 13. D-BC decisions (12 items; user-confirmed defaults)

The following implementation-level decisions are pre-stated at α. All are default-approved per the design memo plan.

| ID | Decision | α-fixed value (default) |
|---|---|---|
| D-BC1 | Branch / script / test naming | `research/phase28-0c-alpha-a0-architecture-redesign` / `scripts/stage28_0c_a0_architecture_redesign_eval.py` / `tests/unit/test_stage28_0c_a0_architecture_redesign_eval.py` |
| D-BC2 | AR1 stage-1 admission threshold | top 50% per-pair val-median of stage-1 score (deterministic) |
| D-BC3 | AR2 per-pair backbone | 27.0d S-E verbatim inheritance (NO per-pair hyperparameter tuning per NG#A0-1) |
| D-BC4 | AR3 blend weight | 0.5 / 0.5 fixed; rank-normalised; no grid sweep |
| D-BC5 | AR4 regime split feature | `atr_at_signal_pip` |
| D-BC6 | AR4 regime split granularity | per-pair val-median (consistent with AR1) |
| D-BC7 | OOF coverage | control regressor only (S-E backbone; DIAGNOSTIC-ONLY; per-AR OOF approximate) |
| D-BC8 | H-C3 outcome ladder | 4 outcomes (PASS / PARTIAL_SUPPORT / FALSIFIED_ARCH_INSUFFICIENT / PARTIAL_DRIFT_ARCH_REPLICA); precedence row 4 > 1 > 2 > 3 |
| D-BC9 | PARTIAL_DRIFT_ARCH_REPLICA scope | val-selected (cell\*, q\*) only (single outcome per AR) |
| D-BC10 | eval_report structure | 25-section inherited from 28.0b-α §14 |
| D-BC11 | `--quick-mode` flag | retained; "formal verdict NOT valid in quick mode" warning preserved |
| D-BC12 | R-B / R-T1 / R-T3 language in eval_report | declare R-B / R-T3 not exercised in A0-narrow; R-T1 = FALSIFIED_under_A4 (resolved); A0-broad deferred-not-foreclosed |

---

## 14. Selection-overfit guard; validation-only selection; verdict ladder

Inheritance from 28.0b-α §11 §12 §13 verbatim:

### 14.1 Layer 1 — validation-only configuration selection

Val-selected per cell only contributes to formal H-C3 verdict. Other (cell, configuration) records labeled **DIAGNOSTIC-ONLY** in eval_report; excluded from H-C3 outcome row binding.

### 14.2 Layer 2 — cross-cell aggregation

Cross-cell aggregation rule unchanged from Phase 27 / 28. AR variants aggregate alongside control + baseline.

### 14.3 H1 / H2 / H3 / H4 preserved

H1m ≥ +0.30 / H2 lift ≥ +0.05 / H3 ≥ 20,000 / H4 DIAGNOSTIC. **ADOPT_CANDIDATE wall preserved (H2 PASS = PROMISING_BUT_NEEDS_OOS only). NG#10 / NG#11 not relaxed.**

---

## 15. eval_report.md (25-section pattern inherited from 28.0b-α §14)

A0-narrow specific adaptations:

| § | Section | Adaptation for A0-narrow |
|---|---|---|
| 1 | Executive summary | 4-row outcome ladder per AR variant; aggregate verdict; **FALSIFIED_A0_NARROW vs FALSIFIED_ALL_A0 distinction language** if all 4 falsify |
| 2 | Cells overview | 6 cells (AR1 / AR2 / AR3 / AR4 / arch-control / sb-baseline); architecture topology declared per cell |
| 3 | Row-set policy | A0-narrow row-set policy declaration (no R7-C drop) |
| 4 | Sanity probe results | inherited items 1-6 from 27.0f-α §10; NEW items 7-10 (AR1 stage-1 admission threshold distribution; AR2 per-pair training size distribution; AR3 blend rank distribution; AR4 regime split distribution) |
| 5 | OOF diagnostic | control regressor only (S-E backbone) |
| 6 | Regression diagnostic | per AR variant + control + baseline where applicable |
| 7 | Quantile-family per cell | 6 cells × 5 quantiles = 30 records |
| 8 | Val-selection per cell | per-cell val-selected record |
| 9 | Cross-cell aggregate verdict | per Layer 2 |
| 10 | §10 baseline reproduction | inherited FAIL-FAST |
| **11** | **Within-eval ablation drift (per AR variant vs C-a0-arch-control)** | PARTIAL_DRIFT_ARCH_REPLICA detection |
| **11b** | **C-a0-arch-control drift vs 27.0d / 28.0a / 28.0b control** | 5-phase bit-reproduction; WARN-only |
| 12 | Feature importance per AR variant | LightGBM `feature_importances_` per regressor / classifier |
| **13** | **H-C3 outcome row binding per AR variant** | per-AR 4-outcome; explicit FALSIFIED_A0_NARROW vs FALSIFIED_ALL_A0 distinction if all falsify |
| 14 | Trade-count budget audit | per AR variant on val |
| 15 | Pair concentration | per AR variant (AR2 expected lower concentration by construction; AR4 also) |
| 16 | Direction balance | per AR variant |
| 17 | Per-pair Sharpe contribution | per AR variant (DIAGNOSTIC-ONLY) |
| 18 | Top-tail regime audit | DIAGNOSTIC-ONLY; spread_at_signal_pip only; per AR variant on val |
| 19 | R7-A new-feature NaN check | inherited |
| 20 | Realised-PnL distribution by class | inherited |
| 21 | Timing breakdown | per-stage timer (label load, AR1 / AR2 / AR3 / AR4 fit, predict, evaluate per-cell) |
| 22 | References | PR #325 / #332 / #334 / #335 / #336 / #339 / #340 / #341 / #342 / #343 |
| 23 | Caveats | DIAGNOSTIC-ONLY labels; ADOPT_CANDIDATE wall; A0-narrow vs A0-broad distinction; FALSIFIED_A0_NARROW language; AR1 A4-inertia caveat (admitted as architecture-conditioning); AR4 A3-boundary caveat |
| 24 | Cross-validation re-fits diagnostic | 5-fold OOF on S-E (control) inherited |
| 25 | Sub-phase verdict snapshot | per-AR outcome + aggregate verdict + **A0-narrow scope declaration + A0-broad deferred-not-foreclosed reminder + routing implication** |

---

## 16. Decision rule — pre-stated thresholds + post-Path-A routing question

### 16.1 Standard decision rule (if any AR PASS or PARTIAL_SUPPORT)

| Condition | Routing |
|---|---|
| 1+ AR variant PASS at H-C3 | SPLIT_VERDICT_ROUTE_TO_REVIEW; PROMISING_BUT_NEEDS_OOS candidate; downstream architecture deployment review |
| 0 AR PASS, 1+ AR PARTIAL_SUPPORT | REJECT_NON_DISCRIMINATIVE (sub-threshold); post-28.0c review for A2 / A3 / R-B / Path B comparison |

### 16.2 Path A all-FALSIFIED → next routing question

**If all 4 AR variants FALSIFIED (any combination of PARTIAL_SUPPORT / FALSIFIED_ARCH_INSUFFICIENT / PARTIAL_DRIFT_ARCH_REPLICA without any PASS), the post-28.0c routing review MUST explicitly compare:**

1. **A0-broad sequence/NN scope amendment** (Path B; separate scope amendment PR analogous to PR #340 for windowed/sequence input + GPU pipeline + Clause 2 amendment for sequence cells)
2. **Phase 28 closure / Phase 29 rebase** (joint architecture / target / data / feature surface redesign at a fresh phase; analogous to PR #333 Phase 27 R-E primary)

Both options remain open at this α design memo merge. **This PR does not prejudge which is preferable.** The post-28.0c routing review will weigh the evidence (Path A failure mode — sub-threshold partial vs deep falsification; 8-eval picture if applicable; cumulative cost; remaining Phase 28 budget) and recommend a primary.

### 16.3 Constraints preserved across both Path B and Phase 28 closure paths

Both options preserve all binding constraints (§18): D-1 / ADOPT_CANDIDATE wall / NG#10 / NG#11 / γ closure PR #279 / Phase 22 frozen-OOS / production v9 untouched / §10 baseline immutable.

---

## 17. Open questions / unknowns (carried into post-28.0c routing review)

Five open questions pre-stated at α; the post-28.0c routing review (separate later PR) will address them after seeing the β-eval result.

### 17.1 If A0-narrow fails, should Phase 28 continue to A0-broad sequence/NN via scope amendment?

If Path A all-FALSIFIED, the natural Phase 28 next move is to test fundamentally different model classes (RNN / temporal CNN / Transformer / multi-head NN) under a Path B scope amendment. This continues the A0 axis attack via A0-broad, preserving cumulative Phase 28 investment. Cost: high (~3-5 sub-phases for full Path B sequence including amendment + design memo + β-eval; new GPU infrastructure). Information value: directly tests whether **model class** (vs **model topology**) is the binding constraint.

### 17.2 Or should Phase 28 close and Phase 29 rebase around new data / target / architecture jointly?

Alternatively, Path A all-FALSIFIED could be read as a stronger H-B9 confirmation (8 data points: 7-eval + 28.0c-narrow failure) suggesting that **the entire current architecture / target / data setup** is the binding constraint. Phase 29 would rebase jointly on architecture + target + (possibly) data + feature surface. Cost: high (Phase 29 kickoff + scope binding + first sub-phase). Information value: clean restart; may absorb deferred R-B / A2 routes alongside A0-broad as a unified Phase 29 scope.

### 17.3 Which intermediate outcomes inform the choice

The post-28.0c routing review will weigh:

- **Cumulative cost across Phase 28** (28.0a-β + 28.0b-β + 28.0c-β = 3 sub-phase evals at the time of post-28.0c)
- **Path A failure mode**: all-FALSIFIED_ARCH_INSUFFICIENT (subtle / sub-threshold) vs all-PARTIAL_DRIFT_ARCH_REPLICA (deep falsification; tabular architecture itself doesn't matter)
- **A2 / A3 prior updates** after A0-narrow failure
- **Remaining Phase 28 budget** and Phase 29 readiness

### 17.4 AR3 blend weight sensitivity (if PASS)

If AR3 PASSes at H-C3, the 0.5/0.5 fixed blend may be sub-optimal. Weight tuning becomes a separate sub-phase memo amendment (NG#A0-1 enforces no β-time tuning).

### 17.5 AR1 stage-2 training selection bias (if PASS or PARTIAL_SUPPORT)

AR1's stage-2 regressor trains on top-50% admitted rows. At inference, val / test rows must also pass the stage-1 admission filter before stage 2 scoring. This creates a selection bias in the stage-2 training distribution. The β-eval must report stage-2 training row counts per pair as a diagnostic.

---

## 18. Binding constraints (verbatim)

This memo preserves every constraint binding at the end of Phase 28.0b and at PR #343 routing review. They remain binding throughout 28.0c-α / 28.0c-β:

- D-1 bid/ask executable harness preserved
- R7-A subset preserved
- R7-C closed allowlist preserved (no R7-C addition in this sub-phase)
- no R7-B / R7-D feature widening
- no target redesign (A2 remains dissent; not exercised here)
- no selection rule redesign (A4 exhausted; rule fixed at top-q on score per §10 baseline rule)
- no loss redesign (A1 exhausted; symmetric Huber α=0.9 fixed)
- no learned gating / MoE / per-regime adaptive routing (A3 deferred; AR4 deterministic only)
- no sequence / NN model classes (A0-broad deferred-not-foreclosed via separate scope amendment if elevated)
- no 5th AR variant (closed 4-architecture allowlist; NG#A0-1)
- no grid sweep within an AR variant (α-fixed numerics; NG#A0-1)
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
- MEMORY.md unchanged inside this PR
- doc-only
- no implementation in this PR
- no eval in this PR
- no production change in this PR
- no auto-route after merge
- no R-B / R-T3 elevation (deferred per PR #334 / PR #343 §10 carry-forward)
- no A2 / A3 elevation (dissents per PR #343 §14; deferred-not-foreclosed)
- no scope amendment in this PR (Path A; A0-broad amendment is a separate later PR if elevated)
- R-T1 = FALSIFIED_under_A4 (resolved by PR #342; status preserved)
- A1 / A4 exhausted under tested closed allowlists (status preserved)
- A0-broad deferred-not-foreclosed (declared at §7.2; admissible via scope amendment)

The β-eval implementation PR will inherit all of these constraints unchanged.

---

## 19. References

**Phase 28 (this sub-phase chain)**:
- PR #335 — Phase 28 kickoff (A0 admissible at §5.1; amendment policy §15)
- PR #336 — Phase 28 first-mover routing review (A0 dissent 2)
- PR #337 / #338 — Phase 28.0a A1 objective redesign (NG#A1 / D10 4-artifact / H-C1 4-outcome ladder templates)
- PR #339 — Phase 28 post-28.0a routing review (A0 dissent 1)
- PR #340 — Phase 28 scope amendment A4 non-quantile cells (template for A0-broad amendment if elevated)
- PR #341 / #342 — Phase 28.0b A4 monetisation-aware selection (NG#A4 / H-C2 / R-T1 absorption templates)
- PR #343 — Phase 28 post-28.0b routing review (A0 primary; A2 / A3 dissents; R-B / R-T3 carry-forward; R-T1 resolved; A1 / A4 exhausted)

**Phase 27 (inheritance / template)**:
- PR #325 — Phase 27.0d-β S-E regression (S-E score backbone; symmetric Huber α=0.9; sample_weight=1)
- PR #332 — Phase 27.0f-β (within-eval ablation drift template; PARTIAL_DRIFT outcome pattern; 25-section eval_report origin)
- PR #334 — Phase 27 closure memo (R-T1 / R-B / R-T3 carry-forward register; H-B7 / H-B8 / H-B9 hypothesis source)

**Binding contracts**:
- PR #279 — γ closure
- Phase 22 frozen-OOS contract
- X-v2 OOS gating
- Phase 9.12 production v9 closure tip `79ed1e8` (production v9 20-pair, untouched throughout Phase 27 and Phase 28)

---

*End of `docs/design/phase28_0c_alpha_a0_architecture_redesign_design_memo.md`.*
