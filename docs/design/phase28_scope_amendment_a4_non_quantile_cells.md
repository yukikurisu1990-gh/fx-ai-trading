# Phase 28 Scope Amendment — A4 Non-Quantile Cell Shapes

**Type**: doc-only scope amendment
**Status**: amends Phase 28 kickoff §15.2 cell-shape policy to admit non-quantile cells **under A4 sub-phase scope only**; does NOT initiate any sub-phase
**Branch**: `research/phase28-scope-amendment-a4-non-quantile-cells`
**Base**: master @ `5b6d1c4` (post-PR #339 / Phase 28 post-28.0a routing review)
**Pattern**: analogous to PR #324 (Phase 27 S-E scope amendment) / PR #330 (Phase 27 R7-C scope amendment) / PR #311 (Phase 26 R6-new-A allowlist amendment)
**Date**: 2026-05-17

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Phase 28 scope amendment** admitting **non-quantile cell shapes (R1 absolute-threshold, R4 top-K per bar) under A4 monetisation-aware selection sub-phase scope only**. It updates Clause 2 (cell-shape closure) for A4 sub-phases only; non-A4 sub-phases retain the existing quantile-based cell-shape contract. It does **NOT**:*
>
> - *initiate any A4 / A0 / A2 / A3 sub-phase,*
> - *create any Phase 28 sub-phase design memo,*
> - *elevate R-T1 / R-B / R-T3 (carry-forward routes remain in PR #334 status),*
> - *broaden the closed feature allowlists (R7-A / R7-C unchanged; R7-B / R7-D still NOT admissible),*
> - *change the target spec, architecture, or production v9,*
> - *modify the §10 baseline numeric or any prior verdict.*
>
> *Approval is the **scope-binding** prerequisite for the next 28.0b-α A4 design memo PR. The 28.0b-α design memo, the 28.0b-β implementation, and any sub-phase initiation each require a separate later user routing decision.*

Same approval-then-defer pattern as PR #324 / PR #330 / PR #311.

---

## 1. Why this amendment exists

Phase 28's post-28.0a routing review (PR #339) selected **A4 monetisation-aware selection** as the primary second-mover (prior 35-45 %). PR #339 §13 also records that **R-T1 full reframing under A4** is admissible. The A4 axis is defined (Phase 28 kickoff PR #335 §5.5) as:

> A4 — monetisation-aware selection: redesign the selection rule jointly with the score, instead of applying top-quantile-on-score after the fact. Examples: joint training of score + selection threshold, cost-aware ranking, position-conditional selection.

The Phase 28 first-mover routing review (PR #336 §15.2) declared that **A4 sub-phases that introduce non-quantile selection cell shapes trigger a Clause 2 scope amendment**. The post-28.0a routing review (PR #339 §11.1 / §13) confirms this: the two most direct attacks on H-B7 (val-selection rule misspecified; strengthened by 28.0a 6/6 val-selector pattern) are:

- **R1 absolute-threshold** — trade when `score > c` for a learned threshold `c`. This is a **non-quantile cell shape** because the cell is not defined by a per-row quantile rank.
- **R4 ranked-cutoff / top-K per bar** — at each M5 bar, take the K highest-scoring candidates. This is a **non-quantile cell shape** because the selection is per-bar rather than per-row independent.

Without this amendment, A4 sub-phases would be restricted to quantile-based rules only (R2 middle-bulk / R3 per-pair quantile), which substantially weakens the prior P(GO) for A4 (PR #339 §6 / §15.2) and would risk collapsing A4 into R-T2 quantile-trim inertia (PR #339 §11.1 NG#A4-1).

This amendment admits R1 and R4 cell shapes **under A4 sub-phase scope only**. All other constraints remain unchanged.

---

## 2. Clause 2 update: current vs new

### 2.1 Current Clause 2 (per Phase 28 kickoff PR #335 §15.2; inherited from Phase 27)

> Cell-shape closure: all formal sub-phase cells are defined by per-row quantile selection on a score (top-q% on score, bottom-q% on score, or quantile ranges). Non-quantile cell shapes are NOT admissible under any sub-phase scope. Introducing a non-quantile cell shape requires a separate Clause 2 scope amendment PR.

### 2.2 New Clause 2 (this amendment; effective post-merge)

> Cell-shape closure: all formal sub-phase cells are defined by per-row quantile selection on a score (top-q% on score, bottom-q% on score, or quantile ranges), **EXCEPT** under **A4 monetisation-aware selection sub-phase scope**, where the following non-quantile cell shapes are also admissible:
>
> - **Absolute-threshold cells**: `trade if score > c` where `c` is a deterministic val-fit value (per-pair median, per-pair quantile, or global percentile). The cell is defined by the inequality, not by a per-row quantile rank.
> - **Top-K per bar cells**: at each `M5` bar timestamp, select the K highest-scoring candidates. The cell is defined per-bar, not per-row independent.
>
> Non-quantile cells under A4 scope MUST:
>
> 1. Pre-state the deterministic fit / cell definition in the sub-phase α design memo (no open-ended grid sweep);
> 2. Co-exist with at least one quantile-based **C-top-q-control** cell (NG#A4-3 inheritance from A4 design memo) for within-eval ablation drift detection;
> 3. Preserve all binding constraints (§6 of this amendment).
>
> Non-quantile cell shapes are NOT admissible under any non-A4 sub-phase scope (A0 / A1 / A2 / A3) without a further separate Clause 2 scope amendment PR specific to that axis.

### 2.3 Scope of the amendment

This amendment:

- **Adds** two non-quantile cell shape categories (absolute-threshold; top-K per bar) to the admissibility set under A4.
- **Restricts** the new admissibility strictly to A4 sub-phase scope. A0 / A1 / A2 / A3 retain the original quantile-only cell-shape contract.
- **Preserves** all other contracts (R7-A / R7-C closed allowlists, target spec, architecture, production v9, etc.).
- **Inherits** the pre-stated-numerics-only requirement (NG#A1-1 from 28.0a-α §6.1; analogous NG#A4-1 in the upcoming 28.0b-α design memo) — no grid sweep within a non-quantile cell shape variant.

---

## 3. What this admits

### 3.1 Non-quantile cell shapes (A4 sub-phase scope only)

#### 3.1.1 R1 absolute-threshold

- **Cell definition**: `trade if score > c` where `c` is a val-fit constant or per-pair val-fit constant.
- **Pre-stated fit method** at α (28.0b-α §4.1): `c = per-pair val-median(score)`. Deterministic; no grid sweep.
- **Cell shape contract**: per-row inequality test. Not a quantile rank.
- **Inheritance**: D-1 bid/ask executable harness; validation-only selection; test touched once.

#### 3.1.2 R4 ranked-cutoff / top-K per bar

- **Cell definition**: at each unique `signal_ts` (M5 bar), take the K highest-scoring rows.
- **Pre-stated K** at α (28.0b-α §4.4): `K = 1` (deterministic; "best-of-bar" selection). No grid sweep.
- **Cell shape contract**: per-bar (signal_ts) selection. Not per-row independent.
- **Inheritance**: D-1 bid/ask executable harness; validation-only selection; test touched once.

### 3.2 No other admissions

This amendment admits **only** the two non-quantile cell shapes above, **only** under A4 sub-phase scope. It does **not** admit:

- Open-ended numeric grid sweeps within a non-quantile cell shape (NG#A4-1 inheritance forbids this; pre-stated numerics fixed at α).
- Non-quantile cell shapes under non-A4 sub-phase scope (A0 / A1 / A2 / A3).
- Other non-quantile patterns beyond the two above (e.g., regime-conditional selection cells, per-direction conditional cells) — these would require a further separate scope amendment.

---

## 4. What this does NOT admit

This amendment is **minimal-surface**. It does **NOT**:

1. **Broaden the closed feature allowlists.**
   - R7-A (4 features: `pair`, `direction`, `atr_at_signal_pip`, `spread_at_signal_pip`) — unchanged.
   - R7-C (3 features: `f5a_spread_z_50`, `f5b_volume_z_50`, `f5c_high_spread_low_vol_50`) — unchanged; remains closed allowlist; not admissible inside A4.
   - **R7-B and R7-D** remain **NOT admissible**; require their own scope amendment PR (analogous to PR #330 R7-C amendment) to be introduced.
2. **Change the target spec.** Triple-barrier realised PnL (K_FAV=1.5×ATR, K_ADV=1.0×ATR, H_M1=60, bid/ask executable per D-1) — unchanged. A2 target redesign remains a dissent; not affected by this amendment.
3. **Change the architecture.** LightGBM tabular regressor / classifier remains the default. A0 architecture redesign remains a dissent; not affected by this amendment.
4. **Admit non-A4 axes inside A4.** A4 sub-phase scope is strictly about selection-rule redesign on a fixed score and fixed feature surface. A0 / A1 / A2 / A3 require their own design memos (and where applicable, their own scope amendments).
5. **Change production v9.** Production v9 20-pair (Phase 9.12 closure tip `79ed1e8`) remains untouched.
6. **Modify §10 baseline.** §10 baseline (C-sb-baseline; q\*=5; val Sharpe -0.1863; test Sharpe -0.1732; n 34,626; ann_pnl -204,664.4; test Spearman -0.1535) — immutable. A4 sub-phase β-eval will continue to use C-sb-baseline as FAIL-FAST reproduction reference.
7. **Modify any prior verdict.** All Phase 25 / 26 / 27 verdicts, the Phase 28.0a-β verdict, and all closure-time hypothesis-status snapshots remain unchanged.
8. **Elevate R-T1 / R-B / R-T3.** The amendment makes R-T1 formal reframing under A4 *possible* (PR #339 §13), but does not elevate R-T1 itself. R-T1 absorption is declared in the upcoming 28.0b-α design memo (separate later PR).
9. **Initiate any sub-phase.** No 28.0b-α design memo / 28.0b-β eval / scripts / tests / artifacts touched. No auto-route after merge.
10. **Touch production / deployment.** No X-v2 OOS gating change; no Phase 22 frozen-OOS contract change; no production v9 change.

---

## 5. Inheritance preserved

The following contracts inherited from Phase 25 / 26 / 27 / 28 are **preserved unchanged**:

### 5.1 Cell-shape pattern inheritance

- 27.0f / 28.0a quantile-based cell-shape contracts remain the **default** for all non-A4 sub-phases.
- The {5, 10, 20, 30, 40} quantile family inherited at 27.0f (D-Z4) / 28.0a (PR #337 §7) continues to apply to quantile-based cells inside A4 (e.g., the C-a4-top-q-control cell).
- D10 multi-artifact form (27.0f 3-artifact / 28.0a 4-artifact + 1 multiclass) extends naturally to A4: 4 rule cells + 1 control + 1 baseline = 6-cell structure (or smaller depending on A4 design memo final scope).

### 5.2 Harness contracts

- **D-1 bid/ask executable harness** preserved. `_compute_realised_barrier_pnl` reads bid_h / ask_l / ask_h / bid_l. No mid-to-mid leakage. No spread_factor parameter on the cache.
- **Fix A row-set isolation contract** (27.0f-β PR #332) remains the canonical template for any additive row-drop surface. A4 sub-phases do not introduce row-drops (no feature additions); Fix A is not exercised inside A4 but the contract remains available.
- **5-fold OOF (DIAGNOSTIC-ONLY; seed=42)** sub-procedure inherited.
- **2-layer selection-overfit guard** (validation-only selection; test touched once) — preserved unchanged. A4 non-quantile cells inherit this guard:
  - **Layer 1**: val-selected (cell\*, q\* or cell\*-alone for non-quantile) only contributes to formal verdict.
  - **Layer 2**: cross-cell aggregation rule unchanged. Non-quantile cells aggregate alongside quantile cells.
- **C-sb-baseline reproduction FAIL-FAST** (27.0c-α §7.3 inheritance) — preserved verbatim. A4 sub-phase β-evals continue to embed this gate.

### 5.3 Verdict ladder inheritance

- **H1m** (Spearman score-vs-realised-PnL ≥ +0.30 on val-selected cell) — preserved.
- **H2** (val Sharpe lift ≥ +0.05 vs §10 baseline) — preserved.
- **H3** (trade count ≥ 20,000 on val-selected) — preserved. For non-quantile cells, the trade count is the number of rows that pass the cell definition (e.g., rows where `score > c` for R1, or K × n_bars for R4).
- **H4** (formal test Spearman; DIAGNOSTIC-ONLY) — preserved.
- **ADOPT_CANDIDATE wall**: H2 PASS = PROMISING_BUT_NEEDS_OOS only. **Preserved**. Non-quantile cells are subject to the same wall.

---

## 6. Binding constraints (verbatim)

The following constraints remain binding throughout 28.0b-α / 28.0b-β / any future A4 sub-phase:

- D-1 bid/ask executable harness preserved
- R7-A subset preserved
- R7-C closed allowlist preserved (no broader F5-c / F5-d / F5-e)
- no R7-B
- no R7-D
- no target redesign (A2 remains dissent; not exercised here)
- no architecture change (A0 remains dissent; not exercised here)
- no non-A4 axes admitted by this amendment
- validation-only selection
- test touched once
- ADOPT_CANDIDATE wall preserved
- H2 PASS = PROMISING_BUT_NEEDS_OOS only
- NG#10 / NG#11 not relaxed
- γ closure PR #279 preserved
- X-v2 OOS gating remains required for any future production deployment
- Phase 22 frozen-OOS contract preserved
- production v9 20-pair (Phase 9.12 closure tip `79ed1e8`) untouched
- §10 baseline immutable (no numeric change in this amendment or future A4 sub-phases)
- MEMORY.md unchanged inside this PR
- doc-only
- no implementation
- no eval
- no production change
- no auto-route after merge
- no sub-phase initiation
- no R-T1 / R-B / R-T3 elevation
- no prior verdict modification

### 6.1 What "no R-T1 elevation" means in this amendment

This amendment makes **R-T1 formal reframing under A4 admissible** in principle (per PR #339 §13). It does **not** elevate R-T1 as a standalone Phase 27 carry-forward route. R-T1 absorption is declared formally in the **upcoming 28.0b-α design memo PR** (separate later PR), where R-T1's carry-forward register status will be transitioned to "absorbed under A4 sub-phase scope."

The amendment also does **not** elevate R-B or R-T3. Both remain in PR #334 carry-forward status:

- R-B (different feature axis): deferred-not-foreclosed; requires its own scope amendment to broaden the closed feature allowlist; not affected by this amendment.
- R-T3 (concentration formalisation): below-threshold; deferred; not affected by this amendment.

---

## 7. References

**Phase 28**:
- PR #335 — Phase 28 kickoff (§15.2 amendment policy; A4 non-quantile cell trigger)
- PR #336 — Phase 28 first-mover routing review (§5.5 A4 definition; §15.2 amendment trigger declaration)
- PR #337 — Phase 28.0a-α A1 objective redesign design memo (NG#A1-1 / NG#A1-2 / NG#A1-3 anti-collapse guard template; pre-stated-numerics pattern)
- PR #338 — Phase 28.0a-β A1 objective redesign eval (FALSIFIED_OBJECTIVE_INSUFFICIENT result; H-B7 strengthening evidence)
- PR #339 — Phase 28 post-28.0a routing review (A4 primary; R-T1 reframing under A4 declared admissible; §11.1 R-T2 inertia risk)

**Phase 27 (template inheritance)**:
- PR #311 — Phase 26 R6-new-A allowlist amendment (minimal-surface scope-amendment template)
- PR #324 — Phase 27 S-E scope amendment (Phase 27 admission template)
- PR #330 — Phase 27 R7-C scope amendment (most-similar predecessor: amendment of closed allowlist for a single sub-phase scope only)
- PR #334 — Phase 27 closure memo (H-B7 / H-B8 / H-B9 carry-forward; R-T1 / R-B / R-T3 register)

**Binding contracts**:
- PR #279 — γ closure
- Phase 22 frozen-OOS contract
- X-v2 OOS gating
- Phase 9.12 production v9 closure tip `79ed1e8` (production v9 20-pair, untouched throughout Phase 27, Phase 28 kickoff, Phase 28.0a, and this amendment)

---

*End of `docs/design/phase28_scope_amendment_a4_non_quantile_cells.md`.*
