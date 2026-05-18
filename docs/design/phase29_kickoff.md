# Phase 29 Kickoff — Structural Rebase after Phase 28 Closure; Scope III Admissibility (A0-broad / A2 / R-B / A3); Policy C Hybrid Joint-Axis; Option 9c Dual Baseline Reference; First-mover Deferred

**Type**: formal Phase opening memo. **Doc-only**.
**Branch**: `research/phase29-kickoff`
**Base**: master @ `6aceb88` (post-PR #347; Phase 28 formally closed)
**Pattern**: analogous to PR #335 (Phase 28 kickoff memo)
**Date**: 2026-05-19

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Phase 29 opening**. It locks **Scope III admissibility** (A0-broad / A2 / R-B / A3 all admissible at kickoff), **Policy C hybrid joint-axis policy** (single-axis default; joint admission requires explicit sub-phase α motivation), **Option 9c dual baseline reference policy** (Phase 28 §10 archived; Phase 29 may define a new baseline reference per sub-phase α), and the **mandatory clauses** updated for Phase 29. This PR does **NOT**:*
>
> - *select the Phase 29 first sub-phase (first-mover decision is **explicitly deferred** to a separate first-mover routing review PR; analogous to PR #336 for Phase 28);*
> - *create any Phase 29 first sub-phase α design memo (separate later PR, after first-mover routing review);*
> - *create any A0-broad / A2 / R-B / A3 scope amendment (separate later PR if needed);*
> - *imply implementation approval for any of the four admissible axes — **Scope III is an admissibility declaration only**, not first-mover selection and not implementation approval;*
> - *implement a β-eval, modify production, or touch any prior verdict;*
> - *modify the Phase 28 §10 baseline numeric (immutable; archived);*
> - *modify the production v9 wiring (Phase 9.12 tip `79ed1e8`; untouched);*
> - *relax ADOPT_CANDIDATE wall, NG#10, NG#11, γ closure PR #279, X-v2 OOS gating, or the Phase 22 frozen-OOS contract;*
> - *auto-route to any Phase 29 sub-phase after merge.*
>
> *After this PR merges, the recommended next PR is `docs/design/phase29_first_mover_routing_review.md` (separate later PR; user-instructed). The first-mover ranking, first sub-phase α design memo, and β-eval are all sequenced **after** the first-mover routing review PR.*

Same approval-then-defer pattern as PR #335 (Phase 28 kickoff) and PR #334 (Phase 27 closure).

---

## 1. Phase 29 mission statement

**Phase 29 is a structural rebase after Phase 28 closure. It is allowed to jointly reconsider data, target, architecture, and feature surface under controlled admissibility, while preserving all production and OOS safety constraints.**

The rebase rationale was accepted at PR #346 (post-28.0c routing review primary recommendation) and formally recorded at PR #347 (Phase 28 closure memo). The 8-eval evidence picture — val-selector picked C-sb-baseline 8/8 across four orthogonal channels (B/C/A/D) — established that continuing single-axis extension within Phase 28's frame has diminishing information return relative to a multi-axis rebase. Phase 29 is the frame in which the four deferred-not-foreclosed axes (A0-broad / A2 / R-B / A3) can be jointly reconsidered.

Phase 29 is **not** a relaxation of production / OOS / falsifiability constraints. It is **not** a free-form research phase. It admits a controlled scope (§6), a controlled joint-axis policy (§7), and inherits the full Phase 28 falsifiability scaffolding (§8).

---

## 2. Phase 29 motivation: 8-eval picture inheritance

Phase 29 inherits Phase 28's 8-eval evidence picture as the primary motivation. Cross-reference to PR #347 (Phase 28 closure memo) §4 / §5 / §6:

| Channel | Sub-phases | Status at Phase 29 opening |
|---|---|---|
| B (score / objective / loss) | 27.0b/c/d + 28.0a | exhausted (4 sub-phases × closed allowlists) |
| C (selection rule) | 27.0e + 28.0b | exhausted (2 sub-phases × closed allowlists) |
| A (regime feature) | 27.0f + 28.0a-L3 + 28.0b-R3 | exhausted under tested closed allowlists |
| D (model class topology, tabular LightGBM) | 28.0c | exhausted (FALSIFIED_A0_NARROW) |

**Active hypotheses at Phase 29 opening**:
- **H-B9** (seam exhausted at this architecture stack): strongly strengthened; 8 supporting data points
- **H-A0-broad** (tabular model class insufficient; sequence/NN required): newly elevated by 28.0c-β; never tested
- **H-A2** (target misspecified): not yet tested; long-standing dissent
- **H-R-B** (R7-A feature surface insufficient; new feature class required): not yet tested; carry-forward since 27.0d
- **H-A3** (learned regime gating / MoE required, beyond deterministic split): mildly penalised by 28.0c AR4 deep failure; never tested as separate axis

Phase 29 is designed to test these hypotheses — individually under single-axis sub-phases, or jointly under explicit Policy C admission.

---

## 3. What Phase 29 INHERITS from Phase 28

All of the following carry forward into Phase 29 unchanged.

### 3.1 Verdict register (no modification)

- All Phase 27 sub-phase β verdicts preserved verbatim (27.0b/c/d/e/f).
- All Phase 28 sub-phase β verdicts preserved verbatim (28.0a/b/c).
- All routing review verdicts preserved (PR #336 / #339 / #343 / #346).
- All exhaustion declarations preserved (A1 / A4 / A0-narrow).
- All resolved carry-forward statuses preserved (R-T1 = FALSIFIED_under_A4).
- All deferred-not-foreclosed statuses preserved (A0-broad / A2 / R-B / A3).
- The FALSIFIED_A0_NARROW vs FALSIFIED_ALL_A0 distinction preserved verbatim.

### 3.2 Baseline reference (Phase 28 §10 immutable as archived reference)

- Phase 28 §10 baseline numeric: n_trades=34,626 / Sharpe=-0.1732 / ann_pnl=-204,664.4 / val Sharpe=-0.1863.
- **Immutable**. Not retroactively modified by Phase 29.
- Phase 29 may define **additional** baseline references per sub-phase α (Option 9c; see §9).

### 3.3 Production v9 wiring (untouched)

- Phase 9.12 production v9 closure tip `79ed1e8`.
- Untouched throughout Phase 27, Phase 28, and Phase 29.
- Phase 29 does NOT modify production wiring.

### 3.4 Binding production / OOS / falsifiability contracts

- D-1 bid/ask executable harness preserved.
- Validation-only selection preserved.
- Test touched once preserved.
- ADOPT_CANDIDATE wall preserved (Phase 29 opening does NOT relax).
- H2 PASS = PROMISING_BUT_NEEDS_OOS only.
- NG#10 / NG#11 not relaxed.
- γ closure PR #279 preserved.
- X-v2 OOS gating required for any future production deployment.
- Phase 22 frozen-OOS contract preserved.

### 3.5 Resolved carry-forward

- **R-T1** = FALSIFIED_under_A4 (resolved at PR #342; absorbed into Phase 28.0b A4 sub-phase frame).

### 3.6 Exhausted axes (status preserved)

- **A1** exhausted under tested closed 3-loss allowlist (L1/L2/L3; PR #338).
- **A4** exhausted under tested closed 4-rule allowlist (R1/R2/R3/R4; PR #342).
- **A0-narrow** exhausted under tested closed 4-architecture allowlist (AR1/AR2/AR3/AR4; PR #345); verdict = FALSIFIED_A0_NARROW (NEVER FALSIFIED_ALL_A0).

### 3.7 Deferred-not-foreclosed (status preserved; admissible per §6)

- **A0-broad** (sequence / NN model class beyond tabular LightGBM).
- **A2** (target redesign).
- **R-B** (feature class beyond R7-A).
- **A3** (learned regime gating / MoE; beyond AR4 deterministic split).

---

## 4. What Phase 29 explicitly does NOT inherit

These Phase 28 frame assumptions are **not** binding in Phase 29 and may be revisited via sub-phase α admissibility:

| Frame assumption | Phase 28 status | Phase 29 status |
|---|---|---|
| Single-axis-only frame (each sub-phase tests one axis) | binding | **NOT binding** — Policy C admits joint-axis sub-phases with explicit α motivation (§7) |
| R7-A as the only admissible feature surface | binding | **NOT binding** — R-B admissible at kickoff; new feature classes possible per sub-phase α |
| Triple-barrier realised-PnL as the only admissible target | binding | **NOT binding** — A2 admissible at kickoff; alternative target framings possible per sub-phase α |
| Tabular LightGBM as the only admissible model class | binding | **NOT binding** — A0-broad sequence/NN admissible at kickoff per sub-phase α |
| Top-q on score as the only admissible selection rule | binding | possibly revisited under joint frames (selection rule space already explored under A4; new admission requires sub-phase α motivation) |
| Symmetric Huber α=0.9 as the only admissible loss | binding | possibly revisited under joint frames (loss space already explored under A1; new admission requires sub-phase α motivation) |
| C-sb-baseline as the only canonical baseline cell ID | binding | possibly renamed / dual-defined under A2 (Option 9c; §9) |
| Phase 27/28 inertia routes | NOT admissible at Phase 28 kickoff | **NOT admissible at Phase 29 kickoff** without explicit amendment (§11) |

---

## 5. Deferred-not-foreclosed axes registry (Phase 28 closure carry-forward)

Verbatim from PR #347 §10. **All four axes admissible at Phase 29 kickoff per Scope III decision in §6.**

| Axis | Description | Phase 28 last-touched | Priority hint for Phase 29 first-mover ranking |
|---|---|---|---|
| **A0-broad** | sequence / NN model class beyond tabular LightGBM (RNN / LSTM / GRU / Temporal CNN / Transformer; multi-head NN) | newly elevated by 28.0c-β FALSIFIED_A0_NARROW; never tested | **high** (dissent 1 at PR #346) |
| **A2** | target redesign (pure return / time-weighted / multi-horizon / asymmetric K_FAV/K_ADV beyond 1.5/1.0; MAE-aware target) | never tested; long-standing dissent at PR #339 / #343 / #346 | **moderate** (dissent 2 at PR #346) |
| **R-B** | feature class beyond R7-A (path-shape / microstructure / multi-TF context / calendar / cross-asset) | never tested; carry-forward since 27.0d | **moderate** (Tier 3 at PR #346) |
| **A3** | learned regime gating / MoE; adaptive routing beyond AR4 deterministic split | partially probed by 28.0c AR4 deterministic split (val Sharpe lift -0.4053; worst of 4 ARs); learned routing untested | **low** (Tier 3 at PR #346; AR4 deep failure penalises) |

**Priority hints are informational only.** The actual first-mover decision is deferred to the Phase 29 first-mover routing review PR (separate later PR; §12).

---

## 6. Phase 29 admissibility scope — Scope III (LOCKED)

**Decision**: **Scope III** is locked at this kickoff PR.

All four deferred-not-foreclosed axes are admissible at Phase 29 kickoff:

- A0-broad (sequence / NN model class)
- A2 (target redesign)
- R-B (feature class beyond R7-A)
- A3 (learned regime gating / MoE)

### 6.1 What Scope III is

- An **admissibility declaration**: all four axes may be the subject of a Phase 29 sub-phase α design memo without requiring a kickoff amendment.
- An **inclusivity statement**: no deferred axis is foreclosed at Phase 29 opening.

### 6.2 What Scope III is NOT

- **NOT** first-mover selection. Scope III does **not** pick which axis goes first.
- **NOT** implementation approval. Scope III does **not** approve any β-eval, scope amendment, or design memo for any specific axis.
- **NOT** joint-axis pre-approval. Joint-axis sub-phases require explicit Policy C motivation at sub-phase α (§7).
- **NOT** scope-amendment-bypass. New axes not in {A0-broad, A2, R-B, A3} still require explicit scope amendment.

### 6.3 Scope III ranking note

Scope III intentionally admits all four axes including A3 (low priority due to AR4 deep failure) so that the first-mover routing review (separate later PR) can rank all four under the same kickoff scope rather than requiring an amendment to admit A3 later. This is **administrative inclusivity**; the first-mover routing review will still penalise A3 priors per PR #346 §5.5.

---

## 7. Joint-axis policy — Policy C hybrid (LOCKED)

**Decision**: **Policy C (hybrid)** is locked at this kickoff PR.

### 7.1 Policy C definition

- **Single-axis sub-phase is the default.** Each Phase 29 sub-phase α should target exactly one axis from {A0-broad, A2, R-B, A3} unless joint admission is explicitly motivated.
- **Joint-axis sub-phase is admissible only if the sub-phase α memo explicitly motivates the joint design.** Joint motivation must include:
  - **Why** the two (or more) axes are inseparable in the test (e.g., sequence model + windowed feature class; target redesign + multi-horizon feature; learned gating + per-regime target).
  - **How** falsifiability is preserved under the joint frame.
  - **How** attribution ambiguity is handled in the sub-phase H-Cx 4-outcome ladder and the 25-section eval_report.
- **No implicit joint route.** A sub-phase α that does not explicitly motivate joint admission is treated as single-axis.
- **No auto-route.** Joint admission does not trigger any automatic next sub-phase decision.

### 7.2 Attribution ambiguity handling under Policy C

If a Phase 29 joint-axis sub-phase produces a PASS or PARTIAL_SUPPORT verdict, the sub-phase eval_report MUST include:

- **Per-axis ablation results** (e.g., for A0-broad + R-B joint: report A0-broad with R7-A control row-set + R-B with tabular control model row-set).
- **Joint-only configuration** as the primary verdict cell, with single-axis ablations as DIAGNOSTIC-ONLY rows.
- **Explicit statement** of whether the PASS is attributable to one axis, both axes, or the joint interaction.
- **H-Cx outcome ladder** must include a `PARTIAL_DRIFT_JOINT_REPLICA` row (analogous to PR #344 §12.3 row 4) detecting whether the joint cell ≈ either single-axis control cell within tolerance — flagging joint-ambiguity.

### 7.3 Policy C falsifiability preservation

- Closed allowlist still required per sub-phase α (analogous to NG#A0-1 / NG#A1-1 / NG#A4-1 / NG#A0-1).
- 25-section eval_report still required.
- 4-outcome H-Cx ladder still required (extended to 5 outcomes for joint sub-phases per §7.2).
- C-sb-baseline FAIL-FAST still required where applicable (or its Phase 29 baseline analog under Option 9c).
- 5-phase bit-tight control reproduction chain continues (Phase 29 controls reproduce 27.0d C-se if tabular LightGBM control retained).

---

## 8. Falsifiability scaffolding decision (LOCKED)

**Decision**: Phase 29 retains the Phase 28 falsifiability scaffolding verbatim. Each Phase 29 sub-phase α and β must include:

| Component | Source pattern | Phase 29 status |
|---|---|---|
| Closed allowlist (per-axis α-fixed numerics; no β-time grid sweep) | PR #337 / #341 / #344 NG#A* | **retained** |
| NG#A* anti-collapse guards | PR #344 NG#A0-1/2/3 | **retained** (with axis-specific renaming per sub-phase α) |
| 25-section eval_report.md | PR #344 §15 / PR #341 §14 | **retained** (with axis-specific adaptations per sub-phase α) |
| 4-outcome H-Cx ladder (PASS / PARTIAL_SUPPORT / FALSIFIED_<axis>_INSUFFICIENT / PARTIAL_DRIFT_<control>_REPLICA) with precedence row 4 > 1 > 2 > 3 | PR #341 §10.2 / PR #344 §12.3 | **retained** (extended to 5 outcomes for joint sub-phases per §7.2) |
| Baseline FAIL-FAST | PR #344 §10 | **retained** where applicable (per Option 9c; §9) |
| Validation-only selection | PR #335 / PR #344 §14.1 | **retained** |
| Test touched once | PR #335 Clause 1 | **retained** |
| Explicit cross-cell aggregation (SPLIT_VERDICT_ROUTE_TO_REVIEW / REJECT_NON_DISCRIMINATIVE / FALSIFIED_<axis> aggregation patterns) | PR #344 §12.4 | **retained** |
| ADOPT_CANDIDATE wall (H2 PASS = PROMISING_BUT_NEEDS_OOS only) | PR #335 Clause 1 | **retained** |
| 5-phase bit-tight control reproduction (where tabular LightGBM control retained) | PR #344 §11 | **retained** as Phase 29 6th anchor; sub-phase α may extend to sequence-control if A0-broad first |

---

## 9. Baseline reference policy — Option 9c dual reference (LOCKED)

**Decision**: **Option 9c (dual reference)** is locked at this kickoff PR.

### 9.1 Phase 28 §10 baseline (immutable archived reference)

- n_trades = 34,626
- Sharpe = -0.1732
- ann_pnl = -204,664.4 (pip)
- val Sharpe = -0.1863

These numerics are **immutable**. They are **never retroactively modified** by Phase 29. They remain the canonical Phase 28 reference for the inherited verdict register.

### 9.2 Phase 29 baseline reference (defined per sub-phase α)

- Phase 29 may define a **new Phase 29 baseline reference** per first sub-phase α if the sub-phase axis changes baseline numeric semantics.
- **Especially if A2 target redesign is admitted at first sub-phase α**: target redesign changes realised PnL semantics, so Phase 28 §10 baseline numeric no longer represents the same outcome metric. The A2 sub-phase α MUST define a Phase 29 baseline reference numeric, with explicit re-computation methodology.
- **If A0-broad / R-B / A3 admitted without A2** (target unchanged): Phase 29 sub-phase α MAY inherit Phase 28 §10 verbatim as Phase 29 §10 reference (no redefinition needed).
- **Coexistence**: archived Phase 28 §10 reference and Phase 29 sub-phase-specific reference can coexist within the same sub-phase eval_report. Phase 28 §10 reference is cited as the **archived control**; Phase 29 sub-phase reference is the **active comparison**.

### 9.3 Baseline FAIL-FAST under Option 9c

- If Phase 29 sub-phase inherits Phase 28 §10 reference (no target redesign), C-sb-baseline FAIL-FAST per PR #344 §10 continues verbatim.
- If Phase 29 sub-phase defines a new Phase 29 baseline reference (target redesigned), the sub-phase α MUST define a new FAIL-FAST gate analog (with tolerances analogous to ±0 n_trades / ±1e-4 Sharpe / ±0.5 pip ann_pnl, recalibrated to the new target semantics).
- **No omission of FAIL-FAST.** Every Phase 29 sub-phase MUST have a FAIL-FAST baseline gate of some form.

---

## 10. Scope amendment policy (analogous to PR #335 §15)

Phase 29 sub-phases that go beyond the kickoff admissibility scope (Scope III) require a scope amendment PR before the sub-phase α can be authored.

### 10.1 What triggers a scope amendment

- New axes outside {A0-broad, A2, R-B, A3} (e.g., reviving A1 / A4 / A0-narrow under new allowlist semantics).
- Cell-shape changes incompatible with current Clause 2 (analogous to PR #340 admitting A4 non-quantile cells).
- New falsifiability scaffolding additions beyond §8 retention (e.g., new sequence-aware FAIL-FAST gates may admit via sub-phase α without amendment if they extend the existing scaffolding; but new model evaluation paradigms beyond H-Cx require amendment).

### 10.2 What does NOT trigger a scope amendment

- Sub-phase α design memo for any axis in {A0-broad, A2, R-B, A3} (admitted at kickoff per Scope III).
- Joint-axis sub-phase α with explicit Policy C motivation (admitted per §7).
- Phase 29 baseline reference redefinition per Option 9c (admitted per §9).
- Sub-phase-specific NG#A* renaming (admitted per §8).

### 10.3 Amendment PR sequencing

If an amendment is required, the sequence is:
1. Amendment PR (analogous to PR #340) — doc-only; updates the relevant clause.
2. Sub-phase α design memo PR — references the amended scope.
3. Sub-phase β eval PR — references the α design memo.

---

## 11. Phase 27/28 inertia routes NOT admissible at Phase 29 (without explicit amendment)

The following routes are **explicitly NOT admissible** at Phase 29 sub-phases without a scope amendment PR:

| Inertia route | Source exhaustion | Phase 29 status |
|---|---|---|
| **A1 single-loss-variant micro-redesign** (L1 / L2 / L3 extensions; new loss types beyond closed 3-loss allowlist) | PR #338 (A1 exhausted) | NOT admissible without amendment |
| **A4 single-rule extension** (R5/R6/... or revisions to R1/R2/R3/R4 numerics) | PR #342 (A4 exhausted) | NOT admissible without amendment |
| **A0-narrow tabular topology variant extension** (AR5/AR6/... or hyperparameter sweep within AR1/AR2/AR3/AR4) | PR #345 (A0-narrow exhausted; FALSIFIED_A0_NARROW) | NOT admissible without amendment |
| **S-axis score micro-redesign** (S-F / S-G / new score formulations within the C-sb-baseline-anchored frame) | Phase 27 inertia (27.0b/c/d/e/f exhausted) | NOT admissible without amendment |
| **R7-C-style regime-statistic-only feature widening** (regime features without joint frame) | PR #332 (Phase 27.0f exhausted) | NOT admissible without amendment |
| **C-sb-baseline-anchored sweep-only PRs** (sweeps that vary q% / score on C-sb-baseline without architectural change) | Phase 27/28 inertia | NOT admissible without amendment |
| **Standalone R-T1 / R-T2 / R-T3 continuation** (carry-forward elevation without target / selection-rule entanglement) | R-T1 resolved (PR #342); R-T2 absorbed under A4; R-T3 admissible only as part of A2 sub-phase | NOT admissible standalone without amendment |

### 11.1 Why these are not admissible

All seven routes are forms of single-axis or sub-axis continuation that the 8-eval picture has demonstrated as exhausted. Their non-admissibility is the **operationalisation** of the closure rationale (PR #347 §13): Phase 29's rebase frame requires that single-axis Phase 27/28 inertia continuations be explicitly amended in, not implicitly admitted.

### 11.2 Revival path (if needed)

Any of these routes can be revived via:
1. Scope amendment PR with motivation explaining why the route is admissible under Phase 29's rebase frame (e.g., A1 revival under A0-broad-joint frame).
2. Sub-phase α design memo with closed allowlist of new variants.
3. Sub-phase β eval.

**Phase 29 opening does NOT foreclose any route** — it requires explicit motivation for inertia-route admission.

---

## 12. First-mover routing — explicitly deferred

**The first sub-phase decision is NOT made in this PR.** The recommended sequence after this kickoff merge is:

1. **This PR (Phase 29 kickoff)** merges → Phase 29 formally opens with Scope III / Policy C / Option 9c locked.
2. **Phase 29 first-mover routing review PR** (separate later; analogous to PR #336 for Phase 28).
   - Recommended filename: `docs/design/phase29_first_mover_routing_review.md`.
   - Recommended content: rank the four admissible axes (A0-broad / A2 / R-B / A3) plus joint candidates (e.g., A0-broad + R-B), recommend a primary and dissents, defer the final pick to user instruction.
3. User picks first sub-phase (or joint sub-phase) at the routing review approval.
4. **Phase 29 first sub-phase α design memo PR** (axis-specific closed allowlist; NG#A*; H-Cx ladder; sub-phase α design).
5. **Phase 29 first sub-phase β eval PR** (β-eval implementation).

**After this kickoff merges**, the next PR should be `docs/design/phase29_first_mover_routing_review.md` unless the user explicitly instructs otherwise.

---

## 13. First-mover candidate axes (informational only)

Under Scope III + Policy C, the candidate first-mover axes (single or joint) are listed below for informational purposes only. **No first-mover decision is made here.**

| Candidate | Type | Information value | Cost | Notes |
|---|---|---|---|---|
| **A0-broad alone** | single-axis | high (newly elevated by 28.0c-β) | high (GPU pipeline + windowed dataset + sequence training) | aligned with H-A0-broad |
| **A2 alone** | single-axis | moderate (long-standing dissent) | low (existing tabular pipeline reused; target swap) | aligned with H-A2 |
| **R-B alone** | single-axis | moderate (carry-forward since 27.0d) | moderate (new feature class data pipeline) | aligned with H-R-B |
| **A3 alone** | single-axis | low (AR4 deep failure penalises) | moderate (learned gating implementation) | mildly penalised prior |
| **A0-broad + R-B joint** | joint (Policy C) | very high (sequence model + windowed feature class together) | high (GPU + windowed dataset + sequence + new features) | requires Policy C joint motivation per §7 |
| **A0-broad + A2 joint** | joint (Policy C) | very high (sequence model + target redesign together) | high (GPU + new target + sequence training) | requires Policy C joint motivation per §7 |
| **A2 + R-B joint** | joint (Policy C) | high (target + feature class together within tabular frame) | moderate (existing tabular pipeline + new target + new features) | lower-cost joint option |

**No first-mover decision is made here. The routing review PR will rank these.**

---

## 14. Pre-flight checklist for Phase 29 sub-phases

The kickoff memo records the pre-flight checks each Phase 29 sub-phase α must address before β:

### 14.1 If A0-broad admitted

- GPU compute availability (CUDA device check).
- Sequence model training pipeline class scaffolding (PyTorch / JAX / TensorFlow choice; one pipeline class per sub-phase α).
- Windowed / sequence dataset feasibility check (regenerable from M1 ba + M5 outcome; no production data dependency).
- Sequence-cell FAIL-FAST harness analog (sequence-aware control reproduction; new bit-tight chain anchor at Phase 29).

### 14.2 If A2 admitted

- D-1 bid/ask compatibility check per target (alternative targets must remain executable under bid/ask harness).
- Target semantics declaration (what does PnL mean under the new target; how is realised-PnL cached differently).
- Phase 29 baseline reference numeric per Option 9c (§9).
- FAIL-FAST gate analog (PR #344 §10 pattern; recalibrated tolerances).

### 14.3 If R-B admitted

- Feature class data pipeline cost (path-shape / microstructure / multi-TF context / calendar / cross-asset).
- New feature NaN-rate / positivity sanity probe (analogous to PR #344 §15 items 5-6).
- Feature class dependency on existing R7-A (whether R-B replaces, extends, or replaces parts of R7-A).

### 14.4 If A3 admitted

- Learned gating implementation class (transformer-style attention / per-regime MoE / soft routing).
- Per-regime target consistency under D-1 (regime routing must not break bid/ask harness).
- AR4 ablation control (Phase 29 A3 sub-phase MUST report ablation vs 28.0c-AR4 deterministic split; per Policy C attribution ambiguity handling).

### 14.5 If joint sub-phase admitted (Policy C)

- All single-axis pre-flight checks for each component axis.
- Joint motivation block (§7.1).
- Attribution ambiguity handling (§7.2).
- Joint-frame FAIL-FAST + arch-control + 5-outcome H-Cx ladder.

### 14.6 Phase 22 frozen-OOS continuity

- Sub-phase α MUST verify Phase 22 frozen-OOS dataset format compatibility with the new axes.
- If A2 or R-B redesign requires regenerating Phase 22 OOS labels, the sub-phase α MUST document the regeneration explicitly and provide a fallback to the Phase 22 archived OOS where possible.

---

## 15. Open questions (deferred to first sub-phase α; informational only)

The kickoff records these as deferred; they are addressed at the relevant first sub-phase α PR.

1. Which axis (or joint axis pair) is the Phase 29 first sub-phase? (deferred to first-mover routing review PR)
2. If joint admission (e.g., A0-broad + R-B), what is the joint motivation block? (deferred to sub-phase α)
3. If A2 admitted, what is the Phase 29 §10 baseline numeric? (deferred to sub-phase α per Option 9c)
4. If A0-broad admitted, what is the sequence-cell FAIL-FAST harness analog? (deferred to sub-phase α)
5. Does Phase 29 retain `C-sb-baseline` as the canonical baseline cell ID, or define a new sequence-aware / target-aware anchor? (deferred to sub-phase α)
6. What is the OOF fold strategy under windowed / temporal data if A0-broad first? (deferred to sub-phase α)
7. What is the Phase 29 GPU compute budget / time-box for sequence model training? (deferred to sub-phase α)

---

## 16. Mandatory clauses (updated for Phase 29; verbatim inheritance plus Clause 6 update)

**Clause 1** — **Phase framing**. ADOPT requires H2 PASS + full 8-gate A0-A5 harness. H2 PASS = PROMISING_BUT_NEEDS_OOS only. ADOPT_CANDIDATE wall preserved. Phase 29 opening does **NOT** relax.

**Clause 2** — **Diagnostic columns prohibition**. Calibration / threshold-sweep / directional-comparison / classification-quality / feature-importance / per-pair-Sharpe-contribution columns are diagnostic-only. Phase 29 sub-phase-specific diagnostics (e.g., sequence attention weights / multi-horizon target distributions / new feature class importance) are admissible per sub-phase α as DIAGNOSTIC-ONLY.

**Clause 3** — **γ closure preservation**. PR #279 is unmodified.

**Clause 4** — **Production-readiness preservation**. X-v2 OOS gating remains required. Production v9 20-pair (Phase 9.12 tip `79ed1e8`) untouched. Phase 22 frozen-OOS contract preserved.

**Clause 5** — **NG#10 / NG#11 not relaxed**.

**Clause 6 (NEW for Phase 29)** — **Phase 29 scope**. Phase 29 is a structural rebase opened after the Phase 28 closure decision (PR #347). Phase 29 admissibility scope is **Scope III** (A0-broad / A2 / R-B / A3 all admissible at kickoff per §6). Joint-axis sub-phases are admissible under **Policy C** (single-axis default; joint admission requires explicit sub-phase α motivation per §7). Baseline reference policy is **Option 9c (dual reference)** (Phase 28 §10 archived immutable; Phase 29 may define new reference per sub-phase α per §9). Phase 27/28 inertia routes (A1 single-loss / A4 single-rule / A0-narrow tabular topology / S-axis / R7-C-style regime widening / C-sb-baseline-anchored sweep-only / standalone R-T1/R-T2/R-T3 continuation) are **NOT admissible** at Phase 29 sub-phases without explicit scope amendment PR (§11).

---

## 17. Binding constraints (verbatim from PR #347 §16 + Phase 29 additions)

This kickoff memo preserves every constraint binding at PR #347 merge:

- D-1 bid/ask executable harness preserved
- Validation-only selection
- Test touched once
- ADOPT_CANDIDATE wall preserved
- H2 PASS = PROMISING_BUT_NEEDS_OOS only
- NG#10 / NG#11 not relaxed
- γ closure PR #279 preserved
- X-v2 OOS gating required
- Phase 22 frozen-OOS preserved
- Production v9 20-pair (Phase 9.12 tip `79ed1e8`) untouched
- **Phase 28 §10 baseline numeric immutable** (n=34626 / Sharpe -0.1732 / ann_pnl -204664.4 / val Sharpe -0.1863); never retroactively modified
- **No prior verdict modification** (Phase 27 + Phase 28 sub-phase β + routing review verdicts preserved verbatim)
- MEMORY.md unchanged inside PR (separate memo entry after merge)
- A1 / A4 / A0-narrow exhausted statuses preserved (carry-forward from PR #338 / #342 / #345)
- R-T1 = FALSIFIED_under_A4 (carry-forward from PR #342)
- A0-broad / A2 / R-B / A3 deferred-not-foreclosed statuses preserved (admissible per Scope III decision)
- FALSIFIED_A0_NARROW vs FALSIFIED_ALL_A0 distinction preserved verbatim
- R7-A subset preserved as the **default** feature surface (until R-B admitted via sub-phase α)
- Triple-barrier realised-PnL target preserved as the **default** target (until A2 admitted via sub-phase α)
- Top-q on score selection rule preserved as the **default** (unless revisited under joint frame per Policy C)
- Symmetric Huber α=0.9 loss preserved as the **default** (unless revisited under joint frame per Policy C)
- Tabular LightGBM family preserved as the **default** (until A0-broad admitted via sub-phase α)
- No scope amendment in this PR
- No first sub-phase α in this PR
- No first-mover routing review in this PR
- No β-eval in this PR
- No production change in this PR
- No auto-route after merge
- This PR is doc-only

---

## 18. What this PR is NOT (consolidated)

For clarity, the Phase 29 kickoff PR explicitly does **NOT** do any of the following:

- ❌ Select the Phase 29 first sub-phase (first-mover decision deferred to a separate first-mover routing review PR)
- ❌ Create a Phase 29 first sub-phase α design memo (separate later PR)
- ❌ Create a Phase 29 first-mover routing review (separate later PR; recommended filename `docs/design/phase29_first_mover_routing_review.md`)
- ❌ Create any A0-broad / A2 / R-B / A3 scope amendment (separate later PR if needed)
- ❌ Implement any β-eval (no script / test / artifact in this PR)
- ❌ Approve any A0-broad implementation
- ❌ Approve any A2 implementation
- ❌ Approve any R-B implementation
- ❌ Approve any A3 implementation
- ❌ Modify any prior verdict (Phase 27 + Phase 28 sub-phase β verdicts preserved verbatim)
- ❌ Modify the Phase 28 §10 baseline numeric (immutable; archived)
- ❌ Modify the production v9 wiring or any other production state
- ❌ Relax the ADOPT_CANDIDATE wall
- ❌ Relax NG#10 / NG#11 / γ closure / X-v2 OOS / Phase 22 frozen-OOS
- ❌ Foreclose any axis (A0-broad / A2 / R-B / A3 / or any other axis)
- ❌ Imply that Scope III approval is implementation approval
- ❌ Imply that Policy C admits joint sub-phases without explicit α motivation
- ❌ Auto-route to any Phase 29 sub-phase after merge
- ❌ Modify MEMORY.md inside the PR

---

## 19. References

### Phase 28 (immediate predecessor; full registry)

- **PR #335** — Phase 28 kickoff memo (template for this Phase 29 kickoff)
- **PR #336** — Phase 28 first-mover routing review (template for the upcoming Phase 29 first-mover routing review)
- **PR #337 / #338** — Phase 28.0a-α / β A1 objective redesign (A1 exhausted)
- **PR #339** — Phase 28 post-28.0a routing review
- **PR #340** — Phase 28 scope amendment A4 non-quantile cells
- **PR #341 / #342** — Phase 28.0b-α / β A4 monetisation-aware selection (A4 exhausted; R-T1 = FALSIFIED_under_A4)
- **PR #343** — Phase 28 post-28.0b routing review
- **PR #344 / #345** — Phase 28.0c-α / β A0-narrow architecture-topology audit (A0-narrow exhausted; FALSIFIED_A0_NARROW)
- **PR #346** — Phase 28 post-28.0c routing review (Phase 28 closure / Phase 29 rebase PRIMARY)
- **PR #347** — Phase 28 closure memo (Phase 28 formally closed)

### Phase 27 inheritance / template

- **PR #311 / #319 / #325 / #327 / #332** — Phase 27.0b/c/d/e/f sub-phase β-evals (5 of the 8 evidence points)
- **PR #334** — Phase 27 closure memo (secondary template; closure-then-rebase pattern)

### Binding contracts

- **PR #279** — γ closure (production behavior contract; preserved)
- **Phase 22 frozen-OOS contract** (preserved)
- **X-v2 OOS gating** (required for any future production deployment)
- **Phase 9.12 production v9 closure tip `79ed1e8`** (production v9 20-pair; untouched throughout Phase 27, Phase 28, and Phase 29)

---

*End of `docs/design/phase29_kickoff.md`.*
