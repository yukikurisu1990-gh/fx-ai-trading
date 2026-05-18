# Phase 28 Closure Memo — A1 / A4 / A0-narrow Exhausted; A0-broad / A2 / R-B / A3 Deferred-Not-Foreclosed; Phase 29 Rebase Routing Accepted

**Type**: formal Phase closure memo. **Doc-only**.
**Branch**: `research/phase28-closure-memo`
**Base**: master @ `2b053c7` (post-PR #346)
**Pattern**: analogous to PR #334 (Phase 27 closure memo) and PR #315 (Phase 26 closure memo)
**Date**: 2026-05-19

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Phase 28 closure memo**. The closure is a **scope hygiene / rebase decision** accepted at PR #346 (post-28.0c routing review). It records the **8-eval evidence picture**, the **three exhausted axes** (A1 / A4 / A0-narrow under their respective tested closed allowlists), the **resolved carry-forward** (R-T1 = FALSIFIED_under_A4), and the **four deferred-not-foreclosed axes** (A0-broad / A2 / R-B / A3). This PR does **NOT**:*
>
> - *create a Phase 29 kickoff (separate later PR; user-instructed);*
> - *create any scope amendment (separate later PR if A0-broad / A2 / R-B / A3 elevated);*
> - *create a Phase 29 first sub-phase α design memo (separate later PR);*
> - *foreclose A0-broad, A2, R-B, or A3 — all four remain `deferred-not-foreclosed`;*
> - *modify any prior verdict (Phase 27 + Phase 28 sub-phase β verdicts preserved verbatim);*
> - *modify the §10 baseline numeric (immutable);*
> - *modify the production v9 wiring (Phase 9.12 tip `79ed1e8`; untouched throughout Phase 27 and Phase 28);*
> - *relax ADOPT_CANDIDATE wall, NG#10, NG#11, γ closure PR #279, X-v2 OOS gating, or the Phase 22 frozen-OOS contract;*
> - *auto-route to any Phase 29 sub-phase after merge.*
>
> *Phase 28 closure does **NOT** mean production-readiness. It does **NOT** mean "giving up." It is a **scope hygiene / rebase decision** driven by the 8-eval evidence picture and the channel-exhaustion finding. The four deferred-not-foreclosed axes remain admissible at the Phase 29 kickoff (separate later PR), but the routing decision for which axis(es) Phase 29 admits is **explicitly deferred** to that separate kickoff PR.*

Same approval-then-defer pattern as PR #334 (Phase 27 closure) and PR #315 (Phase 26 closure).

---

## 1. Phase 28 closure declaration

**Phase 28 is formally closed at this PR merge.**

The closure is a **scope hygiene / rebase decision** accepted at PR #346 §11 (post-28.0c routing review primary recommendation). The 8-eval evidence picture — 8/8 sub-phases with val-selector picking the inherited C-sb-baseline cell across four orthogonal channels — established that continuing Phase 28 by single-axis extension has diminishing information return relative to a Phase 29 joint multi-axis rebase. PR #346 selected this routing with explicit primary status; this memo records the formal closure.

The closure is **not** a foreclosure of any unresolved axis. A0-broad, A2, R-B, and A3 all remain `deferred-not-foreclosed` and are admissible at the Phase 29 kickoff PR (separate later PR; not created here). The closure is also **not** a production-readiness adjustment; the ADOPT_CANDIDATE wall, NG#10, NG#11, γ closure PR #279, X-v2 OOS gating, Phase 22 frozen-OOS contract, and production v9 20-pair wiring (Phase 9.12 tip `79ed1e8`) all remain binding and untouched.

---

## 2. Phase 28 scope at kickoff (recap from PR #335)

Phase 28 was opened at PR #335 (Phase 28 kickoff memo) after the R-E routing decision at the end of Phase 27. The kickoff admitted **five axes** as kickoff-admissible:

| Axis | Description | Status at Phase 28 kickoff |
|---|---|---|
| A0 | Architecture redesign | admissible |
| A1 | Objective / loss redesign | admissible |
| A2 | Target redesign | admissible |
| A3 | Regime-conditioned modeling | admissible |
| A4 | Monetisation-aware selection rule redesign | admissible |

PR #335 also recorded **three carry-forward items** from Phase 27:

- R-T1 (Phase 27 R-T1 carry-forward; A4-adjacent)
- R-B (feature-class redesign; carry-forward since 27.0d)
- R-T3 (Phase 27 R-T3 carry-forward; target-adjacent)

The Phase 28 amendment policy (§15) required closed-allowlist NG#A* patterns per sub-phase and explicit Clause 2 amendments for non-quantile cell shapes (PR #340 for A4 R1/R4 admission).

---

## 3. Phase 28 sub-phase chain (per-PR registry)

Per-PR registry of every Phase 28 PR. Verdicts are recorded verbatim; **no modification** of any prior verdict.

| # | PR | Scope | Outcome / verdict |
|---|---|---|---|
| 1 | #335 | Phase 28 kickoff memo | doc-only; A0/A1/A2/A3/A4 admissible |
| 2 | #336 | Phase 28 first-mover routing review | A1 primary; A0 / A4 dissents |
| 3 | #337 | Phase 28.0a-α A1 design memo | doc-only; closed 3-loss allowlist (L1/L2/L3) pre-stated |
| 4 | #338 | Phase 28.0a-β A1 objective redesign eval | A1 FALSIFIED (L1/L2/L3 each REJECT_NON_DISCRIMINATIVE; H-C1 4-outcome ladder) |
| 5 | #339 | Phase 28 post-28.0a routing review | A4 primary; A0 dissent 1; A2 dissent 2 |
| 6 | #340 | Phase 28 scope amendment for A4 non-quantile cells | doc-only; Clause 2 updated to admit R1 absolute-threshold + R4 top-K per bar |
| 7 | #341 | Phase 28.0b-α A4 design memo | doc-only; closed 4-rule allowlist (R1/R2/R3/R4) pre-stated; R-T1 absorbed under A4 frame |
| 8 | #342 | Phase 28.0b-β A4 monetisation-aware selection eval | A4 FALSIFIED (all 4 rules REJECT_NON_DISCRIMINATIVE; H-C2 4-outcome ladder); R-T1 = FALSIFIED_under_A4 |
| 9 | #343 | Phase 28 post-28.0b routing review | A0 primary; A2 dissent 1; A3 dissent 2; R-B / R-T3 carry-forward; R-T1 resolved |
| 10 | #344 | Phase 28.0c-α A0-narrow design memo | doc-only; closed 4-architecture allowlist (AR1/AR2/AR3/AR4) pre-stated; A0-broad explicitly deferred-not-foreclosed (§7.2) |
| 11 | #345 | Phase 28.0c-β A0-narrow architecture-topology eval | A0-narrow FALSIFIED (all 4 AR variants FALSIFIED_ARCH_INSUFFICIENT; H-C3 4-outcome ladder); aggregate = FALSIFIED_A0_NARROW (NEVER FALSIFIED_ALL_A0) |
| 12 | #346 | Phase 28 post-28.0c routing review | Phase 28 closure / Phase 29 rebase PRIMARY; A0-broad dissent 1; A2 dissent 2; R-B / A3 Tier 3 |

**Cumulative β-eval cost across Phase 28**: 3 sub-phase β-evals (28.0a + 28.0b + 28.0c).
**Cumulative scope amendments**: 1 (PR #340; A4 non-quantile cells only).
**Cumulative verdicts**: A1 exhausted; A4 exhausted (R-T1 absorbed); A0-narrow exhausted.

---

## 4. 8-eval evidence picture (consolidated)

The val-selector picked the inherited C-sb-baseline cell in **8/8** sub-phase β-evals. Every channel attacked has produced REJECT_NON_DISCRIMINATIVE on its terminal verdict.

| # | Sub-phase | Channel attacked | Closed allowlist | Verdict | Inheritance status |
|---|---|---|---|---|---|
| 1 | 27.0b-β (PR #311) | Channel B (score: S-C TIME penalty) | α ∈ {0.0, 0.3, 0.5, 1.0} | REJECT_NON_DISCRIMINATIVE | val-selector picked C-sb-baseline |
| 2 | 27.0c-β (PR #319) | Channel B (score: S-D calibrated EV) | β ∈ {0.0, 0.3, 0.5, 1.0} | REJECT_NON_DISCRIMINATIVE | val-selector picked C-sb-baseline |
| 3 | 27.0d-β (PR #325) | Channel B (score: S-E regression-on-realised-PnL) | symmetric Huber α=0.9 | REJECT_NON_DISCRIMINATIVE | val-selector picked C-sb-baseline |
| 4 | 27.0e-β (PR #327) | Channel C (selection: S-E quantile family trim) | family ∈ {5, 7.5, 10} | REJECT_NON_DISCRIMINATIVE | val-selector picked C-sb-baseline |
| 5 | 27.0f-β (PR #332) | Channel A (regime feature: S-E + R7-C) | RCW with row-set isolation | REJECT_NON_DISCRIMINATIVE | val-selector picked C-sb-baseline |
| 6 | 28.0a-β (PR #338) | Channel B (objective / loss: A1) | L1 / L2 / L3 closed | REJECT_NON_DISCRIMINATIVE | val-selector picked C-sb-baseline |
| 7 | 28.0b-β (PR #342) | Channel C (selection rule: A4) | R1 / R2 / R3 / R4 closed | REJECT_NON_DISCRIMINATIVE | val-selector picked C-sb-baseline |
| 8 | 28.0c-β (PR #345) | Channel D (model class topology, tabular: A0-narrow) | AR1 / AR2 / AR3 / AR4 closed | REJECT_NON_DISCRIMINATIVE (FALSIFIED_A0_NARROW) | val-selector picked C-sb-baseline |

**8/8 val-selector pattern**: across Phase 27.0b/c/d/e/f and Phase 28.0a/b/c, every β-eval val-selector chose the inherited multiclass C-sb-baseline cell over the substantive cell. H-B9 (seam exhausted at this architecture stack) is the strongest active hypothesis with 8 supporting data points across four orthogonal channels.

---

## 5. Channel exhaustion summary

The 8 sub-phases attack **four orthogonal channels**. At Phase 28 closure, all four channels are exhausted under their tested closed allowlists.

| Channel | Definition | Sub-phases | Status at closure |
|---|---|---|---|
| **B** | Score / objective / loss function | 27.0b/c/d + 28.0a | exhausted (4 sub-phases; closed allowlists per sub-phase) |
| **C** | Selection rule (top-q / R-T2 / R1/R2/R3/R4) | 27.0e + 28.0b | exhausted (2 sub-phases; closed allowlists per sub-phase) |
| **A** | Regime feature / regime-axis loss weighting / per-pair selection quantile | 27.0f + 28.0a-L3 + 28.0b-R3 | exhausted under tested closed allowlists |
| **D** | Model class topology, tabular LightGBM | 28.0c | exhausted under tested closed allowlist (A0-narrow) |

**Untested**: A0-broad (sequence / NN model class beyond tabular) — `deferred-not-foreclosed`.

---

## 6. Hypothesis register — final state at closure

Each Phase 27 / Phase 28 hypothesis with final bias at closure.

| Hypothesis | Final bias | Evidence basis |
|---|---|---|
| **H-B5** (S-axis specifically) | strongly falsified | 4 sub-phases: 27.0b (S-C) + 27.0c (S-D) + 27.0d (S-E) + 28.0a (L2/L3 over S-E) |
| **H-B6** (regime feature widening insufficient) | strongly falsified | 3 sub-phases: 27.0f (R7-C) + 28.0a L3 (regime-axis loss weighting) + 28.0b R3 (per-pair selection quantile) |
| **H-B7** (selection rule misspecified) | strongly falsified | 28.0b A4 (R-T1 absorbed; FALSIFIED_under_A4) |
| **H-B8** (within-architecture decoupling) | partially falsified | 28.0c C-a0-arch-control drift vs 27.0d C-se within tolerance (5-phase bit-tight reproduction successful) |
| **H-B9** (seam exhausted at this architecture stack) | **strongly strengthened** | 8 data points across 4 channels |
| **H-A0-broad** (tabular model class insufficient; sequence / NN required) | newly elevated | 28.0c-β FALSIFIED_A0_NARROW; never tested |
| **H-A2** (target misspecified) | not yet tested; dissent active | long-standing dissent at #339 / #343 / #346 |
| **H-A3** (learned regime gating / MoE required, beyond deterministic split) | mildly penalised | 28.0c AR4 val Sharpe lift -0.4053 (worst of 4 ARs); deterministic-routing prior penalises learned-gating prior, but does not foreclose |
| **H-R-B** (R7-A feature surface insufficient; new feature class required) | not yet tested; carry-forward active | carry-forward since 27.0d; long-standing |

---

## 7. A1 exhaustion declaration (PR #338)

**A1 axis (objective / loss redesign) is formally exhausted under the tested closed allowlist.**

- **Tested at**: PR #338 (Phase 28.0a-β)
- **Closed allowlist**: L1 (asymmetric Huber α=0.5), L2 (Huber α=0.7), L3 (Huber α=0.9 + regime-axis sample weights) — α-fixed per PR #337 / NG#A1-1
- **H-C1 4-outcome ladder**: PASS / PARTIAL_SUPPORT / FALSIFIED_LOSS_INSUFFICIENT / PARTIAL_DRIFT_R7A_REPLICA (precedence row 4 > 1 > 2 > 3)
- **Per-loss outcomes**: all 4 cells (C-a1-L1, C-a1-L2, C-a1-L3, C-a1-se-r7a-replica) → FALSIFIED_LOSS_INSUFFICIENT
- **Aggregate**: REJECT_NON_DISCRIMINATIVE
- **C-sb-baseline reproduction**: PASS

**Exhaustion scope**: A1 is exhausted **under the tested closed 3-loss allowlist (L1/L2/L3)**. Adding L4-L5 loss variants is NOT admissible under the current Phase 28 framing; any L4-L5 revival would require a scope amendment PR (analogous to PR #340 for A4). Such revival is **not foreclosed** in principle but is **not currently in scope** at Phase 28 closure; admission to Phase 29 is a separate decision deferred to the Phase 29 kickoff PR.

---

## 8. A4 exhaustion declaration (PR #342)

**A4 axis (monetisation-aware selection rule redesign) is formally exhausted under the tested closed allowlist.**

- **Tested at**: PR #342 (Phase 28.0b-β)
- **Scope amendment**: PR #340 (Clause 2 admitted R1 absolute-threshold + R4 top-K per bar; non-quantile cell shapes)
- **Closed allowlist**: R1 (absolute threshold; per-pair val-median; 50%), R2 (middle-bulk; global [40, 60] percentile), R3 (per-pair quantile; top 5%), R4 (top-K per bar; K=1) — α-fixed per PR #341 / NG#A4-1
- **H-C2 4-outcome ladder**: PASS / PARTIAL_SUPPORT / FALSIFIED_RULE_INSUFFICIENT / PARTIAL_DRIFT_TOPQ_REPLICA (precedence row 4 > 1 > 2 > 3)
- **Per-rule outcomes**: all 4 rules (C-a4-R1, C-a4-R2, C-a4-R3, C-a4-R4) → FALSIFIED_RULE_INSUFFICIENT
- **Aggregate**: REJECT_NON_DISCRIMINATIVE
- **R-T1 absorption status**: FALSIFIED_under_A4 (resolved; see §11)
- **C-sb-baseline reproduction**: PASS

**Exhaustion scope**: A4 is exhausted **under the tested closed 4-rule allowlist (R1/R2/R3/R4)**. Adding a 5th rule variant is NOT admissible without a memo amendment PR back to α (PR #341 §6 NG#A4-1). Such revival is **not foreclosed** in principle but is **not currently in scope** at Phase 28 closure.

---

## 9. A0-narrow exhaustion declaration (PR #345)

**A0-narrow (tabular LightGBM architecture topology) is formally exhausted under the tested closed allowlist.**

- **Tested at**: PR #345 (Phase 28.0c-β)
- **Closed allowlist**: AR1 (hierarchical two-stage; stage-1 top 50% per-pair val-median admission), AR2 (pair-conditioned specialists; 20 per-pair regressors), AR3 (stacked S-B/S-E blend; 0.5/0.5 fixed weights), AR4 (deterministic regime split; per-pair val-median atr_at_signal_pip) — α-fixed per PR #344 / NG#A0-1
- **H-C3 4-outcome ladder**: PASS / PARTIAL_SUPPORT / FALSIFIED_ARCH_INSUFFICIENT / PARTIAL_DRIFT_ARCH_REPLICA (precedence row 4 > 1 > 2 > 3)
- **Per-AR outcomes**: all 4 AR variants (C-a0-AR1, C-a0-AR2, C-a0-AR3, C-a0-AR4) → FALSIFIED_ARCH_INSUFFICIENT
- **Aggregate**: REJECT_NON_DISCRIMINATIVE
- **A0-narrow status**: **FALSIFIED_A0_NARROW**
- **C-sb-baseline reproduction**: PASS (n_trades 34626 exact; Sharpe Δ +3.55e-5 within 1e-4; ann_pnl Δ -0.023 within 0.5 pip)
- **C-a0-arch-control drift vs 27.0d C-se**: within tolerance (5-phase bit-tight reproduction: 27.0d → 27.0f r7a-replica → 28.0a r7a-replica → 28.0b top-q-control → 28.0c arch-control)
- **Interpretation guards preserved** (PR #344 §3 §4 §12; PR #345 §4):
  - AR1: "architecture-topology with embedded admission gate" (stage-1 admission threshold resembles 28.0b R1 selection-like behavior; admitted under A0-narrow as architecture-conditioning of stage 2's training set, NOT final selection rule)
  - AR4: "deterministic tabular regime split" (NOT learned gating / MoE; A3 elevation requires separate scope amendment)

### 9.1 FALSIFIED_A0_NARROW vs FALSIFIED_ALL_A0 distinction (load-bearing)

This is the most load-bearing distinction in the entire Phase 28 closure register.

- The 28.0c-β verdict is `FALSIFIED_A0_NARROW`.
- It is **explicitly NOT** `FALSIFIED_ALL_A0`.
- All 4 AR variants remain within tabular LightGBM.
- **Sequence / NN model classes (A0-broad) remain `deferred-not-foreclosed`** in all routing outcomes.
- Phase 29 kickoff (separate later PR) may admit A0-broad as a kickoff-admissible axis; this is **not** prejudged at Phase 28 closure.

**Exhaustion scope**: A0-narrow is exhausted **under the tested closed 4-architecture tabular-LightGBM allowlist**. A0-broad (sequence / NN model classes) is **not exhausted** and is admissible at Phase 29 kickoff.

---

## 10. Deferred-not-foreclosed axes registry

Per-axis status declaration at Phase 28 closure. **All four axes remain admissible** at the Phase 29 kickoff PR (separate later PR; not created here).

| Axis | Status | Last touched | Priority hint for Phase 29 |
|---|---|---|---|
| **A0-broad** (sequence / NN model class) | `deferred-not-foreclosed` | never tested; newly elevated by 28.0c-β FALSIFIED_A0_NARROW | high (dissent 1 at PR #346) |
| **A2** (target redesign; e.g., pure return / time-weighted / multi-horizon / asymmetric K_FAV / K_ADV beyond 1.5 / 1.0) | `deferred-not-foreclosed` | never tested; long-standing dissent at PR #339 / #343 / #346 | moderate (dissent 2 at PR #346) |
| **R-B** (feature class beyond R7-A; path-shape / microstructure / multi-TF / calendar / cross-asset) | `deferred-not-foreclosed` | never tested; carry-forward since 27.0d | moderate (Tier 3 at PR #346) |
| **A3** (learned regime gating / MoE; beyond AR4 deterministic split) | `deferred-not-foreclosed` (low priority) | partially probed by 28.0c AR4 deterministic split → AR4 val Sharpe lift -0.4053 (worst of 4 ARs); learned routing as separate axis untested | low (Tier 3 at PR #346; AR4 deep failure penalises) |

**Priority hints are informational only.** The actual Phase 29 admissibility decision and first-mover decision are **deferred** to the separate Phase 29 kickoff PR.

---

## 11. Resolved carry-forward register

Carry-forward items from Phase 27 that have been **resolved** within Phase 28.

| Carry-forward | Origin | Resolved at | Resolution |
|---|---|---|---|
| R-T1 | PR #334 (Phase 27 closure §11) | PR #342 (Phase 28.0b-β) | FALSIFIED_under_A4 (absorbed into A4 sub-phase frame per PR #341 §3; per PR #342 aggregate H-C2 verdict) |

**Resolution notes**:
- R-T1 was a Phase 27 carry-forward item (top-q selection rule alternative). PR #341 §3 formally absorbed R-T1 into the Phase 28.0b A4 sub-phase as a sub-frame of the closed 4-rule allowlist (R1/R2/R3/R4).
- The H-C2 aggregate verdict at PR #342 was REJECT_NON_DISCRIMINATIVE, which resolves R-T1 as FALSIFIED_under_A4.
- R-T1 revival would require a scope amendment beyond the closed 4-rule allowlist; such revival is **not foreclosed** but is **not currently in scope** at Phase 28 closure.

---

## 12. Preserved carry-forward register

Carry-forward items from Phase 27 that remain **active** and are **preserved at closure**.

| Carry-forward | Origin | Status at closure | Phase 29 routing |
|---|---|---|---|
| R-B | PR #334 (Phase 27 closure); active since 27.0d | `deferred-not-foreclosed`; never primary | admissible at Phase 29 kickoff (decision deferred) |
| R-T3 | PR #334 (Phase 27 closure) | `deferred-not-foreclosed`; never primary | admissible at Phase 29 kickoff (decision deferred) |

**Preservation notes**:
- R-B (feature class beyond R7-A) was a long-standing carry-forward; never elevated to primary within Phase 28. The four candidate Phase 28 axes (A0/A1/A2/A3/A4) absorbed routing attention.
- R-T3 was a Phase 27 carry-forward (target-adjacent; A2-adjacent). Not touched within Phase 28. The natural Phase 29 framing is to either absorb R-T3 into an A2 sub-phase or to fold it into a joint multi-axis kickoff.

---

## 13. Why Phase 28 should not continue by inertia (closure rationale)

Five bullet-point reasons (consolidated from PR #346 §8):

### 13.1 8/8 val-selector pattern → single-axis information return diminishing

After 8 sub-phase β-evals across four orthogonal channels, the val-selector has picked the inherited C-sb-baseline cell in every case. The most parsimonious interpretation is **not** that the 9th axis is the missing piece — it is that **the entire stack (R7-A + realised-PnL target + top-q selection + tabular LightGBM family + the implicit assumption that any single-axis change can lift Sharpe) is the wrong frame**. H-B9 gains its 8th data point with 28.0c-β; adding a 9th single-axis test has diminishing information return relative to a stack-level rebase.

### 13.2 Sequence / NN naturally entangles with windowed input + target framing + learned gating

Option 1 (A0-broad sequence/NN) is the strongest single-axis hypothesis, but it does not stay neatly inside Phase 28's frame:
- Sequence models require **windowed / sequence-shaped input** (R-B-adjacent — touches feature class).
- Sequence models often interact with **multi-horizon target framing** (A2-adjacent — touches target redesign).
- Sequence models with attention / gating heads are **regime-conditioning-adjacent** (A3-adjacent — touches learned gating).

Treating A0-broad as a Phase 28 single-axis scope amendment risks **partial frame**: the sequence model would be tested with R7-A-shaped 4-feature input and triple-barrier realised-PnL target unchanged, preserving the very stack assumptions that 8/8 sub-phases have failed to discriminate against. A Phase 29 joint redesign can re-frame all four axes coherently.

### 13.3 Scope hygiene over scope creep

Phase 28 was opened with A0/A1/A2/A3/A4 admissible at kickoff. Of these:
- A1 → exhausted (PR #338)
- A4 → exhausted (PR #342)
- A0-narrow → exhausted (PR #345)
- A0-broad / A2 / A3 → all `deferred-not-foreclosed`

The cleanest scope hygiene is: **close Phase 28 with the channels-exhausted finding, then open Phase 29 with the deferred axes as kickoff admissibility**. Continuing to graft one-axis-at-a-time onto Phase 28 — A0-broad scope amendment, then A2 scope amendment, then R-B scope amendment, then A3 scope amendment — fragments the deferred axes across separate sub-phases that would each be **partially-rebased Phase 28 sub-phases**, all using a partially-rebased scope. Closure preserves scope coherence.

### 13.4 Cumulative cost vs marginal information

Cumulative Phase 28 cost: 3 sub-phase β-evals (28.0a + 28.0b + 28.0c). If A0-broad / A2 / R-B / A3 were each tested as independent Phase 28 single-axis extensions, Phase 28 would house ~7-9 β-evals total before reaching the rebase point that PR #346 §11 already identified as the natural primary. The marginal information return of each single-axis test, given the 8/8 pattern, is low; Phase 29 joint redesign returns more information per β-eval cost.

### 13.5 Stack-level rebase supports H-B9-driven framing

H-B9 (seam exhausted at this architecture stack) is the strongest active hypothesis. Stack-level rebase — jointly redesigning data / target / architecture / feature surface — is the most direct test of H-B9 as a falsifiable claim. If Phase 29 with joint multi-axis redesign produces no lift, H-B9 is essentially confirmed at a fundamental level; if Phase 29 produces lift, the joint axis change is the lever and H-B9 was the wrong frame. Either outcome is more informative than a 9th single-axis Phase 28 sub-phase.

---

## 14. Why Phase 29 rebase is the clean next frame

Four bullet-point reasons (consolidated from PR #346 §8):

### 14.1 Joint multi-axis attack absorbs four deferred axes

A Phase 29 joint redesign can admit A0-broad + A2 + R-B + A3 as candidate axes at the kickoff, with the first sub-phase decision (which axis goes first, or whether two axes are tested jointly) made at the Phase 29 kickoff PR. This is structurally cleaner than four separate Phase 28 scope amendments.

### 14.2 Clean kickoff PR can re-state admissibility scope and amendment policy

Phase 29 kickoff (separate later PR) will:
- Re-state the admissibility scope (the four deferred axes + any new axes that emerge).
- Re-state the amendment policy (analogous to Phase 28 §15).
- Re-state inertia-route exclusion clauses (analogous to Phase 28 §3 — Phase 27 inertia routes NOT admissible).
- Re-define the §10 baseline reference if A2 target redesign is admitted (target redesign affects the baseline numeric; see §15 deferred questions).

This re-statement is hard to do cleanly via Phase 28 scope amendments; it is naturally done in a fresh kickoff.

### 14.3 Preserves all binding constraints

Phase 29 inherits **all** binding constraints from Phase 28 closure verbatim: ADOPT_CANDIDATE wall, NG#10, NG#11, γ closure PR #279, X-v2 OOS gating, Phase 22 frozen-OOS contract, production v9 untouched, validation-only selection, test-touched-once, H2 PASS = PROMISING_BUT_NEEDS_OOS only. None of these are relaxed by closure or by rebase.

### 14.4 H-B9 strength supports stack-level rebase

H-B9 (seam exhausted at this architecture stack) is the strongest active hypothesis at closure. The most direct test of H-B9 as falsifiable is a stack-level rebase that jointly redesigns target + features + architecture (rather than continuing to single-axis-attack within the same stack). Phase 29 is the appropriate frame for this stack-level rebase.

---

## 15. Phase 29 directional hint only (NOT kickoff content)

**This memo does NOT create the Phase 29 kickoff.** It records a one-paragraph **directional hint** to guide the eventual Phase 29 kickoff PR (separate later PR; user-instructed).

**Directional hint**: Phase 29 should be allowed to **jointly redesign data / target / architecture / feature surface**. The candidate first-mover axes are A0-broad (sequence / NN model class), A2 (target redesign), R-B (feature class beyond R7-A), and A3 (learned regime gating / MoE). Whether Phase 29 admits these axes individually, in pairs (e.g., A0-broad + R-B; A0-broad + A2), or jointly under a unified scope decision is **deferred to the Phase 29 kickoff PR**. No priority ranking, admissibility scope, or first-mover decision is made here.

**What this memo does NOT do**:
- Does NOT create the Phase 29 kickoff memo.
- Does NOT create the Phase 29 first sub-phase α design memo.
- Does NOT create any A0-broad / A2 / R-B / A3 scope amendment.
- Does NOT auto-route to any Phase 29 sub-phase after merge.
- Does NOT pre-judge which axis(es) Phase 29 admits.

---

## 16. Binding constraints preserved (verbatim from PR #346 §13)

This closure memo preserves every constraint binding at PR #346 merge:

- **D-1 bid/ask executable harness** preserved (R7-A-clean parent row-set; bid/ask treatment in triple-barrier realised PnL cache; no mid-to-mid)
- **R7-A subset preserved** (4 features: pair, direction, atr_at_signal_pip, spread_at_signal_pip); R7-C closed allowlist preserved (no R7-C re-admission); no R7-B / R7-D widening
- **Triple-barrier realised-PnL target preserved** (K_FAV=1.5×ATR; K_ADV=1.0×ATR; H_M1=60); A2 dissent preserved as `deferred-not-foreclosed`
- **Top-q on score selection rule preserved** (quantile family {5, 10, 20, 30, 40}); R-T2 trim and A4 rule alternatives exhausted under their closed allowlists
- **Symmetric Huber α=0.9 loss preserved** (L1/L2/L3 alternatives exhausted under closed 3-loss allowlist)
- **Tabular LightGBM family preserved** (AR1/AR2/AR3/AR4 alternatives exhausted under closed 4-architecture allowlist); A0-broad sequence / NN `deferred-not-foreclosed` (admissible at Phase 29 kickoff)
- **Validation-only selection** preserved
- **Test touched once** preserved
- **ADOPT_CANDIDATE wall preserved** (closure does NOT relax)
- **H2 PASS = PROMISING_BUT_NEEDS_OOS only** preserved
- **NG#10 / NG#11 not relaxed** (closure does NOT relax)
- **γ closure PR #279 preserved** (production behavior contract untouched)
- **X-v2 OOS gating required** for any future production deployment
- **Phase 22 frozen-OOS contract preserved**
- **Production v9 20-pair (Phase 9.12 closure tip `79ed1e8`) untouched** throughout Phase 27 and Phase 28
- **§10 baseline immutable** (n_trades=34626; Sharpe=-0.1732; ann_pnl=-204664.4; val Sharpe=-0.1863); Phase 29 may re-define the baseline reference if A2 target redesign is admitted, but the Phase 28 §10 baseline numeric is **not modified retroactively**
- **MEMORY.md unchanged inside PR** (separate memo entry after merge if useful)
- A1 / A4 / A0-narrow exhausted under tested closed allowlists (statuses preserved)
- R-T1 = FALSIFIED_under_A4 (PR #342 resolution preserved)
- A0-broad / A2 / R-B / A3 all `deferred-not-foreclosed` (statuses preserved)
- 28.0c-β verdict = FALSIFIED_A0_NARROW, NEVER FALSIFIED_ALL_A0 (distinction preserved)
- No scope amendment in this PR
- No Phase 29 kickoff in this PR
- No β-eval in this PR
- No production change in this PR
- No prior verdict modification
- No auto-route after merge
- This PR is doc-only

---

## 17. What this PR is NOT (re-stated)

For clarity, the closure memo PR explicitly does **NOT** do any of the following:

- ❌ Create a Phase 29 kickoff memo (separate later PR; user-instructed; analogous to PR #335 for Phase 28 kickoff)
- ❌ Create a Phase 29 first sub-phase α design memo (separate later PR; sequenced after the Phase 29 kickoff PR)
- ❌ Create any A0-broad / A2 / R-B / A3 scope amendment (separate later PR if elevated at Phase 29 kickoff)
- ❌ Implement any β-eval (no script / test / artifact in this PR)
- ❌ Modify any prior verdict (Phase 27 + Phase 28 sub-phase β verdicts preserved verbatim)
- ❌ Modify the §10 baseline numeric (immutable; preserved exactly)
- ❌ Modify the production v9 wiring or any other production state
- ❌ Relax the ADOPT_CANDIDATE wall (H2 PASS = PROMISING_BUT_NEEDS_OOS only)
- ❌ Relax NG#10 / NG#11 / γ closure / X-v2 OOS / Phase 22 frozen-OOS
- ❌ Foreclose A0-broad, A2, R-B, or A3 (all four remain `deferred-not-foreclosed`)
- ❌ Pre-judge the Phase 29 admissibility scope, first-mover decision, or NG-pattern continuity
- ❌ Auto-route to any Phase 29 sub-phase after merge
- ❌ Modify MEMORY.md inside the PR
- ❌ Open questions §18: claim resolution of any of the deferred Phase 29 kickoff decisions

### 17.1 Open questions deferred to Phase 29 kickoff

The following questions remain **unanswered** at Phase 28 closure and are explicitly deferred to the Phase 29 kickoff PR (separate later PR):

1. Which axis(es) are Phase 29 kickoff-admissible? (decision deferred)
2. Should A0-broad be the Phase 29 first sub-phase, or should A2 / R-B / A3 go first? (decision deferred)
3. Should Phase 29 admit A0-broad / A2 / R-B / A3 jointly (e.g., A0-broad + R-B for sequence-with-new-features) or staged (one-axis-per-sub-phase)? (decision deferred)
4. Does Phase 29 retain the closed-allowlist + NG#A* + 25-section eval_report pattern, or does it introduce new falsifiability scaffolding? (decision deferred)
5. How does Phase 29 handle the §10 baseline reference if A2 target redesign is admitted (target redesign changes the baseline numeric semantics)? (decision deferred — the Phase 28 §10 baseline numeric is not retroactively modified; Phase 29 may define a separate Phase 29 baseline reference if needed)
6. What pre-flight checks does Phase 29 need for GPU / windowed data / new feature classes? (decision deferred to Phase 29 kickoff)

**None of the above is pre-judged at Phase 28 closure.**

---

## 18. References

### Phase 28 PRs (full registry)

- **PR #335** — Phase 28 kickoff memo (A0/A1/A2/A3/A4 admissible)
- **PR #336** — Phase 28 first-mover routing review (A1 primary)
- **PR #337** — Phase 28.0a-α A1 design memo
- **PR #338** — Phase 28.0a-β A1 objective redesign eval (A1 FALSIFIED under closed 3-loss allowlist)
- **PR #339** — Phase 28 post-28.0a routing review (A4 primary)
- **PR #340** — Phase 28 scope amendment A4 non-quantile cells
- **PR #341** — Phase 28.0b-α A4 design memo (R-T1 absorbed under A4)
- **PR #342** — Phase 28.0b-β A4 monetisation-aware selection eval (A4 FALSIFIED under closed 4-rule allowlist; R-T1 = FALSIFIED_under_A4)
- **PR #343** — Phase 28 post-28.0b routing review (A0 primary; A2 / A3 dissents)
- **PR #344** — Phase 28.0c-α A0-narrow design memo (A0-broad explicitly deferred-not-foreclosed)
- **PR #345** — Phase 28.0c-β A0-narrow architecture-topology eval (A0-narrow FALSIFIED under closed 4-architecture allowlist; FALSIFIED_A0_NARROW; A0-broad deferred-not-foreclosed)
- **PR #346** — Phase 28 post-28.0c routing review (Phase 28 closure / Phase 29 rebase PRIMARY; A0-broad DISSENT 1; A2 DISSENT 2; R-B / A3 Tier 3)
- **This PR** — Phase 28 closure memo

### Phase 27 inheritance / template

- **PR #311** / **PR #319** / **PR #325** / **PR #327** / **PR #332** — Phase 27.0b/c/d/e/f sub-phase β-evals (inheritance for the 8-eval picture rows 1-5)
- **PR #334** — Phase 27 closure memo (template for this Phase 28 closure memo)
- **PR #315** — Phase 26 closure memo (template; secondary)

### Binding contracts

- **PR #279** — γ closure (production behavior contract; preserved)
- **Phase 22 frozen-OOS contract** (preserved)
- **X-v2 OOS gating** (required for any future production deployment)
- **Phase 9.12 production v9 closure tip `79ed1e8`** (production v9 20-pair; untouched throughout Phase 27 and Phase 28)

---

*End of `docs/design/phase28_closure_memo.md`.*
