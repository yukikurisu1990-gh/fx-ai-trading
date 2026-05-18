# Phase 28 Post-28.0c Routing Review — A0-narrow Exhausted; Phase 28 Closure / Phase 29 Rebase Primary

**Type**: post-sub-phase-β routing review memo. **Doc-only**.
**Branch**: `research/phase28-post-28-0c-routing-review`
**Base**: master @ `49c08f5` (post-PR #345)
**Pattern**: analogous to PR #339 (post-28.0a) / PR #343 (post-28.0b)
**Date**: 2026-05-19

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Phase 28 post-28.0c routing review memo**. It records the **8-eval evidence picture**, the **A0-narrow exhaustion** under PR #345, and the **five candidate next-move comparison** with **primary recommendation = Option 2 (Phase 28 closure / Phase 29 rebase)**, **dissent 1 = Option 1 (A0-broad sequence/NN scope amendment)**, **dissent 2 = Option 3 (A2 target redesign)**, and **Tier 3 = Options 4 (R-B) + 5 (A3)**. This PR does **NOT**:*
>
> - *create a Phase 28 closure memo (separate later PR);*
> - *create a Phase 29 kickoff memo (separate later PR);*
> - *create any scope amendment (separate later PR if dissent 1/2 elevated);*
> - *foreclose A0-broad, A2, R-B, or A3 — all four remain `deferred-not-foreclosed`;*
> - *modify any prior verdict, the §10 baseline numeric, the production v9 wiring, or the binding constraint set;*
> - *relax ADOPT_CANDIDATE wall, NG#10, NG#11, γ closure PR #279, X-v2 OOS gating, or the Phase 22 frozen-OOS contract;*
> - *auto-route to any next sub-phase after merge.*
>
> *The path-1-vs-path-2-vs-path-3 selection is a **routing decision** made by approving this PR with primary = Option 2. The next PR (Phase 28 closure memo) is a **separate later PR** sequenced after this one. If the user later chooses to invoke dissent 1 or dissent 2 instead, the routing recommendation can be revisited via memo amendment without re-litigating the channel-exhaustion finding.*

Same approval-then-defer pattern as PR #343 (post-28.0b) / PR #339 (post-28.0a).

---

## 1. 8-eval evidence picture (formal consolidation)

The val-selector picked the inherited C-sb-baseline cell in **8/8** sub-phases. Every channel attacked has produced REJECT_NON_DISCRIMINATIVE on its terminal verdict.

| # | Sub-phase | Axis attacked | Closed allowlist | Verdict | Carry-forward to next |
|---|---|---|---|---|---|
| 1 | 27.0b-β (PR #311) | S-C TIME penalty (score) | α ∈ {0.0, 0.3, 0.5, 1.0} | REJECT_NON_DISCRIMINATIVE | H-B5 strengthened |
| 2 | 27.0c-β (PR #319) | S-D calibrated EV (score) | β ∈ {0.0, 0.3, 0.5, 1.0} | REJECT_NON_DISCRIMINATIVE | H-B5 strengthened |
| 3 | 27.0d-β (PR #325) | S-E regression-on-realised-PnL (score) | symmetric Huber α=0.9 fixed | REJECT_NON_DISCRIMINATIVE | H-B6 / H-B7 emerged |
| 4 | 27.0e-β (PR #327) | S-E quantile-family trim (selection) | family ∈ {5, 7.5, 10} | REJECT_NON_DISCRIMINATIVE | H-B7 strengthened |
| 5 | 27.0f-β (PR #332) | S-E + R7-C regime feature (regime feature) | RCW with row-set isolation | REJECT_NON_DISCRIMINATIVE | H-B8 / H-B9 emerged |
| 6 | 28.0a-β (PR #338) | A1 objective redesign (loss) | L1 / L2 / L3 closed | REJECT_NON_DISCRIMINATIVE | A1 exhausted |
| 7 | 28.0b-β (PR #342) | A4 monetisation-aware selection (rule) | R1 / R2 / R3 / R4 closed | REJECT_NON_DISCRIMINATIVE | A4 exhausted; R-T1 = FALSIFIED_under_A4 |
| 8 | **28.0c-β (PR #345)** | **A0-narrow tabular architecture topology** | **AR1 / AR2 / AR3 / AR4 closed** | **REJECT_NON_DISCRIMINATIVE; A0-narrow status = FALSIFIED_A0_NARROW** | **A0-broad = `deferred-not-foreclosed`** |

**Strongest active hypothesis**: H-B9 (seam exhausted at the current R7-A + realised-PnL target + top-q-selection + tabular LightGBM stack). 8 supporting data points across **four orthogonal channels**.

### 1.1 Channel summary (post-28.0c)

| Channel | Sub-phases | Status |
|---|---|---|
| Channel B (score / objective / loss) | 27.0b/c/d + 28.0a | **exhausted** (4 sub-phases × closed allowlists) |
| Channel C (selection rule) | 27.0e + 28.0b | **exhausted** (2 sub-phases × closed allowlists) |
| Channel A (regime feature / regime-axis loss weighting / per-pair quantile) | 27.0f + 28.0a-L3 + 28.0b-R3 | **exhausted** under tested closed allowlists |
| Channel D (model class topology, tabular LightGBM) | 28.0c | **exhausted** under tested closed allowlist (A0-narrow) |

### 1.2 What is **NOT** yet tested

| Axis | Status | Last touched |
|---|---|---|
| Sequence / NN model classes (A0-broad) | `deferred-not-foreclosed` | never tested |
| Target redesign (A2; e.g., pure return / time-weighted / multi-horizon / asymmetric K_FAV/K_ADV beyond 1.5/1.0) | `deferred-not-foreclosed` (dissent at #339/#343) | never tested |
| Feature class beyond R7-A (R-B; path-shape / microstructure / multi-TF context / calendar / cross-asset) | `deferred-not-foreclosed` (carry-forward since 27.0d) | never tested |
| Learned regime gating / MoE / adaptive routing (A3) | `deferred-not-foreclosed` (dissent at #343) | partially probed by 28.0c-AR4 deterministic split → AR4 val Sharpe lift -0.4053 (worst of 4 ARs); learned routing as separate axis untested |

---

## 2. Channel-coverage map (post-28.0c; cross-axis status)

The matrix below summarises every axis that has been touched vs untouched within Phase 27 and Phase 28.

| Axis | Sub-phases | Verdict | Status |
|---|---|---|---|
| Score formulation (S-C / S-D / S-E) | 27.0b/c/d | all REJECT | exhausted (3) |
| Loss function (A1) | 28.0a | REJECT | exhausted (closed L1/L2/L3) |
| Selection rule (R-T2; A4) | 27.0e + 28.0b | both REJECT | exhausted (closed R-T2 + R1/R2/R3/R4) |
| Regime feature widening (R7-C) | 27.0f | REJECT | exhausted (closed R7-C) |
| Regime-axis loss weighting (28.0a L3) | 28.0a | REJECT | exhausted (sub-cell within L3) |
| Per-pair selection quantile (28.0b R3) | 28.0b | REJECT | exhausted (sub-cell within R3) |
| **Tabular topology (A0-narrow)** | **28.0c** | **REJECT; FALSIFIED_A0_NARROW** | **exhausted (closed AR1/AR2/AR3/AR4)** |
| Sequence / NN model class (A0-broad) | — | — | `deferred-not-foreclosed` |
| Target redesign (A2) | — | — | `deferred-not-foreclosed` |
| Learned regime gating (A3, beyond AR4 deterministic) | — | — | `deferred-not-foreclosed` |
| Feature-class redesign (R-B) | — | — | `deferred-not-foreclosed` |
| Outside-Phase-28 joint redesign | — | — | Phase 29 rebase candidate |

---

## 3. Hypothesis register update (post-28.0c)

Each carry-forward hypothesis updated with strengthened / weakened bias.

| Hypothesis | Bias post-28.0c | Evidence basis |
|---|---|---|
| **H-B5** (S-axis specifically) | strongly falsified | 4 sub-phases (27.0b/c/d + 28.0a L2/L3) |
| **H-B6** (regime feature widening insufficient) | strongly falsified | 27.0f + 28.0a L3 + 28.0b R3 |
| **H-B7** (selection rule misspecified) | strongly falsified | 28.0b (R-T1 absorbed; FALSIFIED_under_A4) |
| **H-B8** (within-arch decoupling) | partially falsified | 28.0c C-a0-arch-control drift vs 27.0d C-se within tolerance (5-phase bit-tight reproduction successful) |
| **H-B9** (seam exhausted at this architecture stack) | **further strengthened** | 8 supporting data points; cross-channel + cross-topology |
| **H-A0-broad** (tabular model class insufficient; sequence/NN required) | newly elevated | 28.0c-β FALSIFIED_A0_NARROW |
| **H-A2** (target misspecified) | not yet tested; dissent active | unchanged since #343 |
| **H-A3** (learned regime gating / MoE required, beyond deterministic split) | mildly penalised | 28.0c-AR4 val Sharpe lift -0.4053 (worst of 4 ARs) |
| **H-R-B** (R7-A feature surface insufficient; new feature class required) | not yet tested; carry-forward active | unchanged since 27.0d |

---

## 4. 28.0c-β specific findings re-stated

Cross-reference to PR #344 (α design memo) and PR #345 (β eval).

### 4.1 Per-AR outcomes

All 4 AR variants → **FALSIFIED_ARCH_INSUFFICIENT (row 3)**:

| AR | Architecture | Val Sharpe | Val Sharpe lift vs §10 | Test Sharpe | Test n |
|---|---|---|---|---|---|
| AR1 | Hierarchical two-stage | -0.286 | -0.1002 | -0.239 | 145,252 |
| AR2 | Pair-conditioned specialists | -0.453 | -0.2671 | -0.328 | 223,584 |
| AR3 | Stacked S-B/S-E blend | -0.197 | -0.0108 | -0.180 | 56,970 |
| AR4 | Deterministic regime split | -0.592 | -0.4053 | -0.519 | 183,480 |

### 4.2 Interpretation guards preserved

- **AR1 guard**: stage-1 admission threshold resembled 28.0b R1 selection-like behavior. AR1's FALSIFIED outcome is **architecture-topology with embedded admission gate** — failure of the **conditioned-on-stage-1 stage-2 regressor topology**, NOT pure architecture-only.
- **AR4 guard**: deterministic regime split is A3-boundary-sensitive. AR4's deep failure (-0.4053 lift; worst of 4) **mildly penalises** A3 elevation (learned gating) priors, but does NOT foreclose A3 — the failure mode is **deterministic routing**, and learned routing remains a distinct axis.

### 4.3 Sanity / inheritance gates

| Gate | Status |
|---|---|
| §10 baseline reproduction | PASS (n_trades 34626 exact; Sharpe Δ +3.55e-5 within 1e-4; ann_pnl Δ -0.023 within 0.5 pip) |
| C-a0-arch-control drift vs 27.0d C-se | within tolerance (5-phase bit-tight reproduction: 27.0d → 27.0f r7a-replica → 28.0a r7a-replica → 28.0b top-q-control → 28.0c arch-control) |
| D-1 bid/ask executable harness | preserved |
| Validation-only selection | preserved |
| Test touched once | preserved |
| No-fallback policy (NG#A0-1) | enforced (no HALT trigger; AR4 no imbalance pairs) |

### 4.4 FALSIFIED_A0_NARROW distinction (load-bearing)

The 28.0c-β verdict is `FALSIFIED_A0_NARROW`. **It is NOT `FALSIFIED_ALL_A0`.** All 4 AR variants remain within tabular LightGBM. Sequence / NN model classes (A0-broad) **remain `deferred-not-foreclosed`** in all downstream routing decisions.

---

## 5. Five candidate next moves — formal specification

### 5.1 Option 2 (PRIMARY) — Phase 28 closure / Phase 29 rebase

**Description**: close Phase 28 with the 8-eval H-B9 confirmation; open Phase 29 with a **joint multi-axis redesign** that admits A0-broad, A2, R-B, and A3 under a unified scope. Phase 29 first sub-phase to be decided at the kickoff memo (separate later PR).

**Why primary** (8-eval-picture-driven):

1. **8/8 val-selector-picks-baseline pattern** across four orthogonal channels (score / objective / selection-rule / regime-feature / tabular-topology). The seam is unlikely to be unlocked by adding one more axis to Phase 28.
2. **Scope hygiene**: Phase 28 was opened with A0/A1/A2/A3/A4 admissible at kickoff (PR #335). A1, A4, and A0-narrow have all been formally exhausted under their closed allowlists. Continuing to graft one-axis-at-a-time onto Phase 28 risks **scope creep without scope coherence** — by the time A0-broad + A2 + R-B + A3 are independently tested, Phase 28 will have housed ~7-9 sub-phase β-evals, all using a partially-rebased scope.
3. **A0-broad sequence/NN is genuinely heavy**: it requires (a) windowed/sequence input surface (new feature class), (b) new compute infrastructure (GPU pipeline), (c) likely target interaction (sequence-aware target framing). These are exactly the **joint axes** that Phase 29 should absorb. Treating A0-broad as a Phase 28 single-axis extension is **architecturally awkward**.
4. **Phase 29 rebase is a clean restart**: kickoff memo + first sub-phase α can absorb A0-broad + A2 + R-B + A3 candidates under a unified scope decision, instead of fragmenting them across 3-4 separate Phase 28 scope amendments.

**Why this is NOT "giving up"**:
- All four `deferred-not-foreclosed` axes (A0-broad / A2 / R-B / A3) **remain admissible**; they shift from "Phase 28 single-axis extension" to "Phase 29 joint-axis kickoff."
- The §10 baseline numeric is **immutable** in Phase 29.
- Production v9 (Phase 9.12 tip `79ed1e8`) is untouched.
- All binding constraints (ADOPT_CANDIDATE wall / NG#10 / NG#11 / γ closure PR #279 / X-v2 OOS / Phase 22 frozen-OOS) are preserved through Phase 29.
- Closure does **NOT** mean production-readiness; the ADOPT_CANDIDATE wall remains.
- No prior verdict is modified.

**Required artifacts** (separate later PRs, NOT this PR):
1. **Phase 28 closure memo** (analogous to PR #334 for Phase 27 closure) — records 8-eval picture, R-T1 absorption, A1/A4/A0-narrow exhaustion, A0-broad/A2/R-B/A3 deferred-not-foreclosed status.
2. **Phase 29 kickoff memo** (analogous to PR #335 for Phase 28 kickoff) — opens Phase 29 with admissibility scope to be determined at the kickoff PR.
3. **Phase 29 first sub-phase α design memo** (e.g., A0-broad-α / A2-α / R-B-α / joint-α — TBD at Phase 29 kickoff).

**Cost**: moderate (closure memo + kickoff memo + first α; ~3-5 weeks elapsed before first Phase 29 β-eval).

**Information value**: high. Clean restart with joint multi-axis attack; absorbs all four deferred axes under a single coherent scope.

**Prior estimate**: **~35-40%** (the ranked-#1 path given the 8-eval picture; Phase 29 first sub-phase pick remains an open decision).

### 5.2 Option 1 (DISSENT 1) — A0-broad sequence/NN scope amendment

**Description**: stay within Phase 28; amend scope (Clause 6) to admit non-tabular model classes (RNN / LSTM / GRU / Temporal CNN / Transformer / multi-head NN); author 28.0d-α design memo with closed sequence-architecture allowlist; run 28.0d-β.

**Information value**: high. Directly tests H-A0-broad (newly elevated by 28.0c-β failure).

**Cost**: high. Required artifacts:
- Scope amendment PR (Clause 6 update; likely also Clause 2 if windowed inputs change row-set semantics)
- Possibly second scope amendment for the new windowed/sequence feature surface
- 28.0d-α sequence-architecture design memo
- 28.0d-β eval (GPU pipeline; new training infrastructure; ~4-8 weeks elapsed)

**Why dissent 1 instead of primary**:
- A0-broad **alone** as a Phase 28 single-axis extension is heavy and scope-creep-prone. Sequence/NN naturally interacts with windowed inputs (R-B-adjacent), with target framing (A2-adjacent), and with regime conditioning (A3-adjacent). Treating it as a single Phase 28 axis fragments these interactions.
- The 8-eval picture argues that **whatever lifts Sharpe is unlikely to be a single-axis change** — Phase 29's joint redesign is a better frame.
- However, **A0-broad is the strongest single-axis hypothesis** if the user prefers to stay within Phase 28. It is preserved as the **primary dissent**.

**Preserved status**: A0-broad **remains `deferred-not-foreclosed` in all cases**, whether or not Option 1 is elevated.

**Prior estimate**: ~20-25% (relative to Option 2; high information value; cost-penalised).

### 5.3 Option 3 (DISSENT 2) — A2 target redesign elevation

**Description**: stay within Phase 28; amend scope to admit a closed allowlist of alternative targets (e.g., pure return; time-weighted PnL; multi-horizon; asymmetric K_FAV / K_ADV beyond 1.5/1.0; MAE-aware target); author 28.0d-α A2 design memo.

**Information value**: moderate-to-high. A2 was the **dissent 2** at PR #343 (post-28.0b routing review). Tests whether the seam is on the **prediction side** (target misspecification) vs the **input / architecture side**.

**Cost**: moderate. Existing tabular LightGBM pipeline can be reused; only target precompute changes. ~2 sub-phases worth.

**Why dissent 2 instead of dissent 1**:
- A2 target redesign is **lighter weight** than A0-broad but **less novel** in information value (target redesign has been an active dissent at #339/#343 without elevation across two prior routing reviews; the prior on it converting from dissent → elevation is lower than on A0-broad-driven elevation after the explicit FALSIFIED_A0_NARROW result).
- However, A2 is **structurally orthogonal** to all 8 exhausted axes and could plausibly be tested cleanly within Phase 28.
- A2 is also **naturally absorbable** into a Phase 29 joint redesign, which is part of the rationale for ranking Option 2 as primary.

**Preserved status**: A2 **remains `deferred-not-foreclosed`** in all cases.

**Prior estimate**: ~10-15% (vs Option 2 primary).

### 5.4 Option 4 (TIER 3) — R-B feature-class elevation

**Description**: stay within Phase 28; amend scope to admit non-R7-A feature classes (closed allowlist: path-shape / microstructure / multi-TF context / calendar / cross-asset); author 28.0d-α R-B design memo.

**Information value**: moderate. R-B was carry-forward since 27.0d; never primary. The R7-A 4-feature surface is genuinely sparse, but R7-C widening (27.0f) already tested one form of feature widening and FALSIFIED.

**Cost**: moderate-to-high. Feature engineering pipeline + data pipeline change. ~2-4 sub-phases.

**Why Tier 3**:
- R-B is a feature-axis attack; channel A (regime feature) is already exhausted. The information value of R-B is **partially overlapping** with the already-failed 27.0f result.
- R-B is **naturally absorbable** into a Phase 29 joint redesign — windowed inputs (sequence-NN-adjacent), path-shape (target-adjacent), multi-TF (regime-adjacent).
- Carry-forward status is preserved; not elevated.

**Preserved status**: R-B **remains `deferred-not-foreclosed`** in all cases.

**Prior estimate**: ~5-10% (vs Option 2 primary).

### 5.5 Option 5 (TIER 3) — A3 regime-conditioned modeling elevation

**Description**: stay within Phase 28; amend scope to admit learned regime gating / MoE / adaptive routing (beyond 28.0c-AR4 deterministic split); author 28.0d-α A3 design memo.

**Information value**: low-moderate. AR4's val Sharpe lift -0.4053 (worst of 4 ARs in 28.0c-β) **mildly penalises** A3 priors — the deepest failure was on the regime-axis topology variant. Learned gating could in principle outperform deterministic routing, but the prior is now penalised.

**Cost**: moderate. Extends 28.0c AR4 with learnable routing; ~2-3 sub-phases.

**Why Tier 3**:
- AR4 deep failure depresses A3 priors.
- A3 is **naturally absorbable** into a Phase 29 joint redesign — learned gating is sequence-NN-adjacent (gating heads in transformer architectures), target-adjacent (per-regime target framing), and feature-axis-adjacent.

**Preserved status**: A3 **remains `deferred-not-foreclosed`** in all cases (low priority).

**Prior estimate**: ~3-5% (vs Option 2 primary).

---

## 6. Scoring rubric

Each option scored on 5 axes; weights as below.

| Axis | Weight | Definition |
|---|---|---|
| Information value | 30% | Does it test a non-tested hypothesis cleanly? Higher reward if orthogonal to 8-eval picture. |
| Falsifiability discipline | 20% | Closed allowlist achievable; clean β verdict; analogous to NG#A0/A1/A4 patterns. |
| Cost / time budget | 20% | Sub-phases to first β; engineering overhead; pipeline class change scope. |
| Prior (Bayesian PASS rate) | 15% | Given 8-eval picture, what is the estimated probability that the option produces PASS H-?? at β. |
| Scope coherence | 15% | Does this option fit cleanly inside Phase 28 frame, or is it cross-axis-entangled and better routed to Phase 29? |

---

## 7. Score table (final; reflects user-confirmed primary)

Higher = better. Total = weighted sum (rounded).

| Option | Info value (30%) | Falsifiability (20%) | Cost (20%) | Prior (15%) | Scope coherence (15%) | **Total** | Rank |
|---|---|---|---|---|---|---|---|
| **Option 2 — Phase 28 closure / Phase 29 rebase** | 9 | 9 | 6 | 7 | 10 | **8.0** | **#1 (PRIMARY)** |
| Option 1 — A0-broad sequence/NN scope amendment | 9 | 7 | 3 | 6 | 5 | **6.4** | **#2 (DISSENT 1)** |
| Option 3 — A2 target redesign elevation | 7 | 8 | 7 | 5 | 6 | **6.6** | **#3 (DISSENT 2)** |
| Option 4 — R-B feature-class elevation | 6 | 8 | 5 | 4 | 5 | **5.6** | #4 (Tier 3) |
| Option 5 — A3 learned regime gating elevation | 5 | 7 | 6 | 3 | 5 | **5.3** | #5 (Tier 3) |

**Note**: Option 1's raw weighted total (6.4) and Option 3's (6.6) are numerically close. The dissent-rank ordering reflects **information value × elevation novelty**: Option 1 (A0-broad) directly attacks H-A0-broad which was **newly elevated** by 28.0c-β's FALSIFIED_A0_NARROW; Option 3 (A2) is a long-standing dissent that has not been primary at any prior routing review. Both are admissible alternative dissents, but Option 1 has the stronger "new evidence after 28.0c" link.

**Primary recommendation**: **Option 2 (Phase 28 closure / Phase 29 rebase)**. Tier-3 options (4 and 5) are preserved as `deferred-not-foreclosed` but not recommended as Phase 28 single-axis extensions.

---

## 8. Why Phase 28 closure / Phase 29 rebase is primary — synthesis

The choice of Option 2 as primary is **8-eval-picture-driven**, not "giving up":

### 8.1 The 8/8 val-selector pattern is the binding evidence

When the val-selector picks C-sb-baseline in 8/8 sub-phases across four orthogonal channels (score / selection / regime / topology), the most parsimonious interpretation is **not** that the 9th axis is the missing piece. The most parsimonious interpretation is that **the entire stack — R7-A features + realised-PnL target + top-q selection + tabular LightGBM family + the implicit assumption that any single-axis change can lift Sharpe — is the wrong frame**.

H-B9 (seam exhausted at this architecture stack) gains its 8th data point in 28.0c-β. After 8 data points, adding a 9th single-axis test inside Phase 28 has **diminishing information return** compared to a phase rebase.

### 8.2 Sequence / NN naturally entangles with windowed input and target framing

Option 1 (A0-broad sequence/NN) is the strongest single-axis hypothesis, but it **does not stay neatly inside Phase 28's frame**:

- Sequence models require **windowed / sequence-shaped input** (R-B-adjacent — touches feature class).
- Sequence models often interact with **multi-horizon target framing** (A2-adjacent — touches target redesign).
- Sequence models with attention / gating heads are **regime-conditioning-adjacent** (A3-adjacent — touches learned gating).

Treating A0-broad as a Phase 28 single-axis scope amendment risks **partial frame**: the sequence model is tested with R7-A-shaped 4-feature input and triple-barrier realised-PnL target unchanged, which preserves the very stack assumptions that 8/8 sub-phases have failed to discriminate against. A Phase 29 joint redesign can re-frame all four axes coherently.

### 8.3 Scope hygiene over scope creep

Phase 28 was opened at PR #335 with A0/A1/A2/A3/A4 admissible at kickoff. Of these:
- A1 → exhausted (28.0a)
- A4 → exhausted (28.0b)
- A0-narrow → exhausted (28.0c)
- A0-broad / A2 / A3 → all `deferred-not-foreclosed`

The cleanest scope hygiene is: **close Phase 28 with the channels-exhausted finding, then open Phase 29 with the deferred axes as kickoff admissibility**. This preserves the falsifiability discipline (closed allowlists per sub-phase) and the verdict register (no prior verdict is modified).

### 8.4 A0-broad is preserved, not abandoned

Critical point: **A0-broad remains `deferred-not-foreclosed`**. Phase 29 will (likely) admit A0-broad as a primary admissibility candidate at its kickoff. The choice of Option 2 over Option 1 is **not** a foreclosure of A0-broad; it is a **routing-frame** decision about where A0-broad is best tested.

If Phase 29 kickoff later picks A0-broad as its first sub-phase, the practical outcome is similar to Option 1 — but the scope is then properly framed for joint windowed-input + sequence-architecture + (possibly) target-framing redesign, rather than fragmented across separate Phase 28 scope amendments.

---

## 9. Option 2 readiness pre-check (informational; NOT this PR's scope)

The actual Phase 28 closure memo and Phase 29 kickoff memo are **separate later PRs** if Option 2 is elevated. This memo only pre-checks readiness.

### 9.1 Phase 28 closure memo (separate later PR) readiness

Required content (analogous to PR #334 Phase 27 closure):
- 8-eval picture consolidation table (this memo §1)
- Hypothesis register state (this memo §3)
- Per-sub-phase verdict register (preserved from each individual β-eval PR)
- A1 / A4 / A0-narrow exhausted status (preserved)
- R-T1 = FALSIFIED_under_A4 status (preserved)
- A0-broad / A2 / R-B / A3 deferred-not-foreclosed status (preserved)
- §10 baseline immutability preserved
- Production v9 untouched preserved
- All binding constraints preserved
- Phase 28 formal closure declaration

### 9.2 Phase 29 kickoff memo (separate later PR) readiness

Required content (analogous to PR #335 Phase 28 kickoff):
- Phase 29 admissibility scope (decision TBD at kickoff — likely a subset of {A0-broad, A2, R-B, A3} elevated to kickoff-admissible)
- Phase 29 amendment policy (analogous to Phase 28 §15)
- Phase 29 scope-boundary clauses (analogous to Phase 28 §3 inertia routes that are NOT admissible)
- First sub-phase pick (TBD at kickoff)

**Neither memo is created in this PR.**

---

## 10. Dissent 1 / Dissent 2 / Tier 3 readiness pre-checks

If the user later prefers a dissent over Option 2, the readiness pre-checks below indicate what additional artifacts each path requires. **None of these are created in this PR.**

### 10.1 Option 1 readiness (A0-broad)

- Scope amendment PR for non-tabular model classes (Clause 6 update; possibly Clause 2 for windowed inputs)
- GPU infrastructure availability check
- Windowed/sequence dataset feasibility check (computed from existing M1 ba data + M5 outcome dataset)
- 28.0d-α sequence-architecture design memo
- 28.0d-β eval

### 10.2 Option 3 readiness (A2)

- Scope amendment PR for closed target allowlist
- D-1 bid/ask executable harness compatibility check per target
- 28.0d-α A2 design memo (closed target allowlist)
- 28.0d-β eval

### 10.3 Option 4 readiness (R-B)

- Scope amendment PR for non-R7-A feature classes (closed allowlist)
- Data pipeline cost check (path-shape / microstructure / multi-TF / calendar / cross-asset)
- 28.0d-α R-B design memo
- 28.0d-β eval

### 10.4 Option 5 readiness (A3)

- Scope amendment PR for learned regime gating
- 28.0d-α A3 design memo (closed gating-class allowlist)
- 28.0d-β eval

---

## 11. Decision rule (pre-stated; analogous to PR #343 §14)

Approving this PR squash-merge is a **routing decision**. The decision-rule mapping below is binding.

| If user picks | Then next PR is |
|---|---|
| **Option 2 (PRIMARY; recommended)** | Phase 28 closure memo (separate later PR), then Phase 29 kickoff memo (separate later PR) |
| Option 1 (DISSENT 1) | Scope amendment PR for sequence/NN model classes, then 28.0d-α A0-broad design memo |
| Option 3 (DISSENT 2) | Scope amendment PR for closed target allowlist, then 28.0d-α A2 design memo |
| Option 4 (Tier 3) | Scope amendment PR for non-R7-A feature classes, then 28.0d-α R-B design memo |
| Option 5 (Tier 3) | Scope amendment PR for learned regime gating, then 28.0d-α A3 design memo |

**No auto-route**: merging this PR does NOT trigger any of the above. The user explicitly invokes the chosen path with a separate instruction.

---

## 12. Open questions / unknowns

Five open questions pre-stated; the chosen-path PR (closure memo or scope amendment) will address them.

### 12.1 Phase 28 closure: what state is preserved verbatim?

The Phase 28 closure memo (separate later PR) will preserve:
- Every per-sub-phase β-eval verdict (no modification)
- The §10 baseline numeric (immutable)
- The production v9 wiring (untouched)
- All binding constraints (ADOPT_CANDIDATE wall / NG#10 / NG#11 / γ closure PR #279 / X-v2 OOS / Phase 22 frozen-OOS)
- A0-broad / A2 / R-B / A3 deferred-not-foreclosed status
- A1 / A4 / A0-narrow exhausted status
- R-T1 = FALSIFIED_under_A4 status

### 12.2 Phase 29 kickoff: which axes will be kickoff-admissible?

Decision TBD at Phase 29 kickoff PR. Candidate admissibility scope:
- A0-broad (sequence/NN) — strong candidate
- A2 (target redesign) — strong candidate
- R-B (feature class) — moderate candidate (depends on A0-broad windowed-input framing)
- A3 (learned regime gating) — weak candidate

### 12.3 Phase 29 first sub-phase: which axis goes first?

Decision TBD at Phase 29 first sub-phase α PR. Candidate first-mover:
- A0-broad (highest information value; newly elevated; aligned with windowed-input + sequence-arch joint frame)
- A2 (lighter cost; structurally orthogonal; long-standing dissent)
- Joint A0-broad + R-B (windowed sequence + new feature class together; highest scope coverage)

### 12.4 What is the remaining Phase 28 budget?

Phase 28 cost to date: 3 sub-phase β-evals (28.0a + 28.0b + 28.0c). If Option 2 elevated, Phase 28 closes at this point. If Option 1/3/4/5 elevated, an additional 1-2+ sub-phase β-evals would be incurred.

### 12.5 Hidden Phase 29 prerequisites?

If A0-broad becomes the Phase 29 first sub-phase:
- GPU compute availability
- Windowed / sequence dataset feasibility (regenerable from M1 ba + M5 outcome)
- Sequence model training pipeline class
- New 8-gate / FAIL-FAST harness for sequence cells

These are pre-checked at Phase 29 kickoff PR (separate later PR); not addressed here.

---

## 13. Binding constraints (verbatim; memo §13)

This routing review preserves every constraint binding at PR #344 / #345 merge:

- D-1 bid/ask executable harness preserved
- R7-A subset preserved (unless Option 4 R-B elevated → separate scope amendment required)
- Triple-barrier realised PnL target preserved (unless Option 3 A2 elevated → separate scope amendment required)
- Top-q on score selection rule preserved
- Symmetric Huber α=0.9 loss preserved
- Tabular LightGBM (unless Option 1 A0-broad elevated → separate scope amendment required)
- Validation-only selection
- Test touched once
- ADOPT_CANDIDATE wall preserved (Option 2 closure does NOT relax this)
- H2 PASS = PROMISING_BUT_NEEDS_OOS only
- NG#10 / NG#11 not relaxed (Option 2 closure does NOT relax these)
- γ closure PR #279 preserved
- X-v2 OOS gating required
- Phase 22 frozen-OOS preserved
- Production v9 20-pair (Phase 9.12 tip `79ed1e8`) untouched
- §10 baseline immutable (no numeric change)
- MEMORY.md unchanged inside this PR
- A1 exhausted (PR #338)
- A4 exhausted (PR #342)
- A0-narrow exhausted (PR #345); A0-narrow status = FALSIFIED_A0_NARROW, NEVER FALSIFIED_ALL_A0
- R-T1 = FALSIFIED_under_A4 (PR #342)
- **A0-broad remains `deferred-not-foreclosed`** (regardless of routing outcome)
- **A2 remains `deferred-not-foreclosed`** (regardless of routing outcome)
- **R-B remains `deferred-not-foreclosed`** (regardless of routing outcome)
- **A3 remains `deferred-not-foreclosed`** (regardless of routing outcome; low priority post-AR4 deep failure)
- No scope amendment in this PR
- No Phase 28 closure memo in this PR
- No Phase 29 kickoff memo in this PR
- No β-eval in this PR
- No production change in this PR
- No prior verdict modification
- No auto-route after merge
- This PR is doc-only

---

## 14. References

**Phase 28 (this sub-phase chain)**:
- PR #335 — Phase 28 kickoff (A0/A1/A2/A3/A4 admissibility)
- PR #336 — Phase 28 first-mover routing review
- PR #337 / #338 — Phase 28.0a-α / β A1 objective redesign (A1 exhausted)
- PR #339 — Phase 28 post-28.0a routing review (A4 primary; A0 / A2 dissents)
- PR #340 — Phase 28 scope amendment A4 non-quantile cells
- PR #341 / #342 — Phase 28.0b-α / β A4 monetisation-aware selection (A4 exhausted; R-T1 = FALSIFIED_under_A4)
- PR #343 — Phase 28 post-28.0b routing review (A0 primary; A2 / A3 dissents; R-B / R-T3 carry-forward)
- PR #344 — Phase 28.0c-α A0-narrow design memo
- PR #345 — Phase 28.0c-β A0-narrow eval (A0-narrow exhausted; FALSIFIED_A0_NARROW; A0-broad deferred-not-foreclosed)

**Phase 27 (inheritance / template)**:
- PR #311 / #319 / #325 / #327 / #332 — Phase 27.0b/c/d/e/f β-evals
- PR #334 — Phase 27 closure memo (template for Phase 28 closure memo)

**Binding contracts**:
- PR #279 — γ closure
- Phase 22 frozen-OOS contract
- X-v2 OOS gating
- Phase 9.12 production v9 closure tip `79ed1e8` (untouched throughout Phase 27 and Phase 28)

---

*End of `docs/design/phase28_post_28_0c_routing_review.md`.*
