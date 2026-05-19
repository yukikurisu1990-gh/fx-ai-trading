# Phase 29 First-Mover Routing Review — Path 2 (A2 target redesign) PRIMARY; Path 1 (A0-broad alone) DISSENT 1; Path 7 (preflight-first) DISSENT 2; Path 3 / 5 / 4 / 6 Tier 3

**Type**: post-kickoff routing review memo. **Doc-only**.
**Branch**: `research/phase29-first-mover-routing-review`
**Base**: master @ `2f6b89d` (post-PR #348; Phase 29 formally opened)
**Pattern**: analogous to PR #336 (Phase 28 first-mover routing review) + PR #346 (post-28.0c routing review)
**Date**: 2026-05-20

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval of this PR **formally accepts the routing recommendation**: Path 2 (A2 target redesign alone) is the recommended Phase 29 first-mover; Path 1 (A0-broad sequence/NN alone) is dissent 1; Path 7 (preflight-first) is dissent 2; Paths 3 / 5 / 4 / 6 are Tier 3.*
>
> ***Critical wording**: merging this PR does **NOT** auto-initiate Path 2 (or any path). The merge **formally accepts the recommendation only**. Actual authorisation to author the Phase 29.0a-α A2 design memo (or any other path's α memo / preflight PR) requires a **separate explicit user instruction** subsequent to this merge. There is no auto-route after merge.*
>
> *This PR does **NOT**:*
>
> - *create a Phase 29 first sub-phase α design memo (separate later PR; user-instructed);*
> - *create any GPU / windowed-data / pipeline preflight PR (separate later PR; user-instructed);*
> - *create any A0-broad / A2 / R-B / A3 scope amendment (separate later PR if needed);*
> - *implement a β-eval;*
> - *modify production wiring (Phase 9.12 tip `79ed1e8`; untouched);*
> - *modify the Phase 28 §10 baseline numeric (immutable; archived);*
> - *touch any prior verdict (Phase 27 + Phase 28 verdicts preserved verbatim);*
> - *relax ADOPT_CANDIDATE wall, NG#10, NG#11, γ closure PR #279, X-v2 OOS gating, or the Phase 22 frozen-OOS contract;*
> - *foreclose any axis — A0-broad / A2 / R-B / A3 all remain admissible at Phase 29 per Scope III (PR #348 §6);*
> - *override Policy C — joint sub-phases remain admissible later with explicit α motivation;*
> - *auto-route to any chosen path after merge.*

---

## 1. Inherited motivation: 8-eval evidence picture

Phase 29 inherits the 8-eval evidence picture from Phase 28 closure (PR #347 §4 / PR #348 §2). The val-selector picked C-sb-baseline in **8/8** sub-phase β-evals across four orthogonal channels (B / C / A / D within tabular LightGBM):

| Channel | Sub-phases | Status at Phase 29 first-mover routing |
|---|---|---|
| B (score / objective / loss) | 27.0b/c/d + 28.0a | exhausted |
| C (selection rule) | 27.0e + 28.0b | exhausted |
| A (regime feature) | 27.0f + 28.0a-L3 + 28.0b-R3 | exhausted |
| D (model class topology, tabular) | 28.0c | exhausted (FALSIFIED_A0_NARROW) |

**Active hypotheses at Phase 29 first-mover routing**:

| Hypothesis | Status |
|---|---|
| H-B9 (seam exhausted at this architecture stack) | strongly strengthened; 8 supporting data points |
| H-A0-broad (tabular model class insufficient; sequence/NN required) | newly elevated by 28.0c-β; never tested |
| H-A2 (target misspecified) | long-standing dissent; never tested |
| H-R-B (R7-A feature surface insufficient; new feature class required) | carry-forward since 27.0d; never tested |
| H-A3 (learned regime gating / MoE required, beyond deterministic split) | mildly penalised by 28.0c AR4 deep failure; never tested as separate axis |

Phase 29 first-mover routing must pick which hypothesis the first Phase 29 sub-phase tests, subject to Scope III + Policy C + Option 9c (PR #348).

---

## 2. Why Phase 29 is not Phase 28 inertia

The candidate first-mover paths below are framed under Phase 29's kickoff scope (PR #348), which is **structurally distinct** from Phase 28's single-axis frame:

- **Scope III** (PR #348 §6): A0-broad / A2 / R-B / A3 all admissible at kickoff — Phase 28 only admitted A0/A1/A2/A3/A4 with A1 / A4 / A0-narrow exhausted by closure.
- **Policy C hybrid** (PR #348 §7): joint-axis sub-phases admissible with explicit α motivation — Phase 28 was single-axis-only.
- **Option 9c dual baseline reference** (PR #348 §9): Phase 29 may define a new baseline reference per sub-phase α — Phase 28 §10 was the only reference.
- **Phase 27/28 inertia routes NOT admissible without amendment** (PR #348 §11): A1 single-loss / A4 single-rule / A0-narrow tabular topology variants / S-axis micro-redesign / R7-C-style regime / C-sb-baseline-anchored sweep-only / standalone R-T1/R-T2/R-T3 all require explicit amendment.

All seven candidate paths below are framed within these Phase 29 admissibilities; none of them reverts to Phase 28 inertia.

---

## 3. Seven candidate first-mover paths

Each path formally specified. Closed allowlists and pre-flight details are **not** decided here — they are deferred to the chosen path's sub-phase α design memo (separate later PR).

### 3.1 Path 1 — A0-broad alone (single-axis)

- **Axis**: sequence / NN model class beyond tabular LightGBM (RNN / LSTM / GRU / Temporal CNN / Transformer encoder / multi-head NN)
- **Cell shape**: per-row score with sequence-shaped input (e.g., last N M5 bars stacked on R7-A features) — TBD at sub-phase α
- **Closed allowlist candidates**: 3-5 sequence architectures; α-fixed numerics; NG#A0-broad-* anti-collapse guards; H-Cx 4-outcome ladder (PASS / PARTIAL_SUPPORT / FALSIFIED_ARCH_INSUFFICIENT / PARTIAL_DRIFT_TABULAR_REPLICA)
- **Hypothesis tested**: H-A0-broad
- **Baseline reference**: Phase 28 §10 inherited (target unchanged); arch-control = tabular LightGBM C-se-equivalent
- **Cost class**: high (GPU pipeline + windowed dataset + sequence training infrastructure)

### 3.2 Path 2 — A2 target redesign alone (single-axis; PROVISIONAL PRIMARY)

- **Axis**: target redesign (pure return / time-weighted / multi-horizon / asymmetric K_FAV/K_ADV beyond 1.5/1.0 / MAE-aware)
- **Cell shape**: tabular (R7-A features unchanged; same model class; new target semantics)
- **Closed allowlist candidates**: 3-5 target variants; α-fixed numerics; NG#A2-* anti-collapse guards; H-Cx 4-outcome ladder
- **Hypothesis tested**: H-A2
- **Baseline reference**: **Phase 29 §10 baseline reference defined per A2 sub-phase α** (Option 9c; target redesign changes baseline semantics)
- **Cost class**: low-moderate (existing tabular pipeline reused; only target precompute changes; Phase 29 baseline definition exercised first)

### 3.3 Path 3 — R-B feature-class redesign alone (single-axis)

- **Axis**: feature class beyond R7-A (path-shape / microstructure / multi-TF context / calendar / cross-asset)
- **Cell shape**: tabular (same model class; same target; expanded feature set)
- **Closed allowlist candidates**: 3-5 feature classes; α-fixed numerics; NG#R-B-* anti-collapse guards; H-Cx 4-outcome ladder
- **Hypothesis tested**: H-R-B
- **Baseline reference**: Phase 28 §10 inherited (target unchanged)
- **Cost class**: moderate (new feature engineering pipeline + data pipeline cost + sanity probes for NaN-rate / positivity / per-pair coverage)

### 3.4 Path 4 — A3 learned regime gating / MoE alone (single-axis; Tier 3)

- **Axis**: learned regime gating / MoE (soft routing / hard MoE / per-regime trained components with learned weights / attention-based gating)
- **Cell shape**: tabular base with learnable routing layer
- **Closed allowlist candidates**: 3-5 gating architectures; α-fixed numerics; NG#A3-* anti-collapse guards; H-Cx 4-outcome ladder; **AR4 ablation control required** per Policy C attribution handling
- **Hypothesis tested**: H-A3
- **Baseline reference**: Phase 28 §10 inherited
- **Cost class**: moderate (learned gating implementation; AR4 ablation cells double the eval cell count)

### 3.5 Path 5 — A0-broad + R-B joint (Policy C; Tier 3)

- **Joint motivation**: sequence models naturally consume windowed feature surfaces; R-B's path-shape / multi-TF / calendar features are natural sequence inputs. Testing model class + feature class together can isolate joint interaction from single-axis levers.
- **Cell shape**: sequence-aware; windowed R-B + R7-A residual
- **Closed allowlist candidates**: 3-4 (model × feature) combos within Policy C 5-outcome H-Cx ladder (adds PARTIAL_DRIFT_JOINT_REPLICA)
- **Hypothesis tested**: H-A0-broad + H-R-B + joint interaction
- **Baseline reference**: Phase 28 §10 inherited (target unchanged); requires both A0-broad-control (tabular + R-B feature) and R-B-control (sequence model + R7-A only) per Policy C §7.2
- **Cost class**: highest (GPU + windowed dataset + new feature class + sequence training + joint motivation block + attribution ambiguity handling + double ablation cells)

### 3.6 Path 6 — A0-broad + A2 joint (Policy C; Tier 3)

- **Joint motivation**: sequence models often interact with multi-horizon target framing; A2's multi-horizon target variant is a natural sequence target. Testing sequence model + new target together can isolate joint interaction from single-axis levers.
- **Cell shape**: sequence-aware; new target semantics
- **Closed allowlist candidates**: 3-4 (model × target) combos within Policy C 5-outcome H-Cx ladder
- **Hypothesis tested**: H-A0-broad + H-A2 + joint interaction
- **Baseline reference**: **Phase 29 §10 baseline reference defined per joint sub-phase α** (Option 9c; target redesigned)
- **Cost class**: very high (GPU + sequence training + new target semantics + new Phase 29 baseline + joint motivation + attribution handling + double ablation cells)

### 3.7 Path 7 — Preflight-first (no first mover yet; DISSENT 2)

- **Description**: defer the first-mover selection by 1-2 PRs; instead, author **preflight PRs** that derisk high-cost paths.
- **Recommended preflight PRs** (sequential or parallel, doc-only):
  - GPU availability + sequence-training-pipeline scaffolding audit PR (PyTorch / JAX / TensorFlow choice; pipeline class declaration; no implementation)
  - Windowed dataset feasibility check PR (regenerable from M1 + M5 outcome; data shape + storage + reproducibility audit)
  - New feature class data pipeline cost PR (path-shape / microstructure / multi-TF column dependency audit)
- **Hypothesis tested**: none directly; risk reduction for subsequent high-cost path (Path 1 / 5 / 6)
- **Cost class**: low (doc-only preflight PRs)
- **Why include**: if the user wants to derisk before committing to Path 1 / 5 / 6, Path 7 sequences preflight PRs first; subsequent first-mover decision deferred until preflight completes

---

## 4. Hypothesis register (post-kickoff)

Active hypotheses at Phase 29 first-mover routing decision point. Inherited from PR #347 §6 / PR #348 §2 with no modification.

| Hypothesis | Bias at Phase 29 opening | Path that tests it |
|---|---|---|
| H-B9 (seam exhausted at this architecture stack) | strongly strengthened (8 supporting data points) | indirectly addressed by any successful Phase 29 sub-phase |
| H-A0-broad (tabular model class insufficient) | newly elevated | Path 1 (alone) or Paths 5 / 6 (joint) |
| H-A2 (target misspecified) | long-standing dissent | Path 2 (alone) or Path 6 (joint) |
| H-R-B (R7-A feature surface insufficient) | carry-forward since 27.0d | Path 3 (alone) or Path 5 (joint) |
| H-A3 (learned regime gating / MoE required) | mildly penalised by 28.0c AR4 deep failure | Path 4 (alone) |

---

## 5. Joint-axis admissibility for first mover

Phase 29 Policy C admits joint-axis sub-phases with explicit α motivation. The question for first-mover routing is whether a **joint** sub-phase should be the **first** Phase 29 sub-phase.

### 5.1 Arguments for joint first mover

- Joint sub-phases test stronger hypotheses (e.g., sequence model + windowed feature class together).
- Phase 29 closure rationale was that single-axis tests fragment the lever; joint sub-phase directly addresses this fragmentation.
- Higher information value per β-eval at lower per-eval cumulative cost.

### 5.2 Arguments against joint first mover

- Phase 29 has **zero** β-eval verdicts yet. Establishing the falsifiability scaffolding (closed allowlist / NG#A* / H-Cx ladder / Policy C 5-outcome extension / attribution ablation cells) on a joint first sub-phase is harder than on a single-axis first sub-phase.
- Attribution ambiguity handling (PR #348 §7.2) requires per-axis ablation cells, which roughly **doubles** the cost of a joint sub-phase vs a single-axis sub-phase.
- A failed joint sub-phase is less informative than a failed single-axis sub-phase (joint failure could attribute to one axis, both, or interaction).

### 5.3 Recommendation

**First mover should be single-axis.** Joint sub-phases (Path 5 / 6) are admissible **after** the first single-axis result anchors the Phase 29 falsifiability discipline. This aligns with Policy C's "single-axis default" framing — joint admission is admissible but not the default; the first mover should not be the case that requires the most complex falsifiability handling.

The user can override this recommendation at PR review.

---

## 6. Scoring rubric

Each path scored on 6 axes; weights as below.

| Axis | Weight | Definition |
|---|---|---|
| Information value | 25% | Does the path test a non-tested hypothesis cleanly? Higher reward if H-? newly elevated or never tested. |
| Falsifiability discipline | 15% | Closed allowlist achievable; clean β verdict; analogous to NG#A0/A1/A4 patterns; Policy C attribution handling clean if joint. |
| Cost / time budget | 20% | Sub-phases to first β; engineering overhead; pipeline class change scope; cumulative Phase 29 cost. |
| Prior (Bayesian PASS rate given 8-eval picture) | 15% | Given H-B9 strength, what is estimated PASS rate at β. |
| Implementation risk | 15% | New pipeline class complexity; OOS / Phase 22 frozen-OOS compatibility; reproducibility risk. |
| Preflight readiness | 10% | GPU / windowed-data / feature-pipeline / target-redefinition prerequisites ready or pending. |

---

## 7. Score table (consolidated)

| Path | Info value | Falsifiability | Cost | Prior | Impl. risk | Preflight | **Total** | **Rank** |
|---|---|---|---|---|---|---|---|---|
| **Path 2 — A2 alone** | 7 | 8 | 8 | 5 | 8 | 9 | **7.1** | **#1 (PRIMARY)** |
| **Path 1 — A0-broad alone** | 9 | 7 | 4 | 6 | 5 | 4 | **6.0** | **#2 (DISSENT 1)** |
| **Path 7 — Preflight-first** | 4 | 9 | 9 | n/a | 9 | 10 | **6.6** | **#3 (DISSENT 2)** |
| Path 3 — R-B alone | 7 | 8 | 6 | 5 | 7 | 7 | **6.6** | #4 (Tier 3) |
| Path 5 — A0-broad + R-B joint | 10 | 6 | 3 | 6 | 4 | 3 | **5.7** | #5 (Tier 3) |
| Path 4 — A3 alone | 5 | 7 | 6 | 3 | 6 | 7 | **5.5** | #6 (Tier 3) |
| Path 6 — A0-broad + A2 joint | 10 | 5 | 2 | 5 | 3 | 2 | **5.0** | #7 (Tier 3) |

**Note on Path 3 vs Path 7 weighted total**: numerically close (both 6.6). The dissent-rank ordering reflects **risk-reduction novelty**: Path 7 reduces the cost / implementation risk of Path 1 (the strongest unfalsified hypothesis), while Path 3 tests a never-tested but long-standing carry-forward. Path 7 is dissent 2 because it is the natural complement to Path 1; Path 3 is Tier 3 because it tests an independent axis.

---

## 8. Provisional ranking

| Rank | Path | Type | Rationale |
|---|---|---|---|
| **#1 (PRIMARY)** | Path 2 — A2 target redesign alone | single-axis | cost-efficient; exercises Option 9c; tests long-standing dissent |
| **#2 (DISSENT 1)** | Path 1 — A0-broad alone | single-axis | strongest unfalsified hypothesis; cost-penalised |
| **#3 (DISSENT 2)** | Path 7 — Preflight-first | no-go | derisks Path 1 before commitment |
| #4 (Tier 3) | Path 3 — R-B alone | single-axis | carry-forward; moderate priority |
| #5 (Tier 3) | Path 5 — A0-broad + R-B joint | joint | highest scope coverage but highest cost and attribution complexity; admissible after single-axis anchor |
| #6 (Tier 3) | Path 4 — A3 alone | single-axis | AR4 deep failure penalises priors; preserved as deferred-not-foreclosed |
| #7 (Tier 3) | Path 6 — A0-broad + A2 joint | joint | very high cost (GPU + new target + sequence + joint motivation); admissible after single-axis anchor |

---

## 9. Why Path 2 (A2 alone) is provisional primary

### 9.1 Cost efficiency

- A2 target redesign reuses the existing tabular LightGBM pipeline. No GPU, no sequence training, no windowed dataset, no new feature class.
- Only target precompute changes (analogous in pipeline scope to 28.0b A4 where only selection rule changed).
- Estimated cost: ~2 sub-phase β-evals worth.
- Cumulative Phase 29 cost so far: 0 β-evals. Path 2 keeps cumulative cost low while testing a never-tested hypothesis.

### 9.2 Falsifiability + Option 9c alignment

- A2 redefines the target → requires Phase 29 §10 baseline reference per Option 9c (PR #348 §9.2).
- **This exercises Option 9c at first sub-phase**, validating the dual-reference policy concretely. Path 1 / 3 / 4 do not exercise Option 9c (target unchanged).
- A2 sub-phase α can author the Phase 29 §10 reference definition cleanly; subsequent Phase 29 sub-phases inherit the precedent.

### 9.3 Information value

- A2 tests H-A2 (target misspecified) — a long-standing dissent (active at PR #339 / #343 / #346) never tested.
- If A2 PASSes: target redesign is the binding lever; subsequent Phase 29 sub-phases re-evaluate A0-broad / R-B / A3 under the new target framing.
- If A2 FALSIFIED: a strong signal that the target is **not** the lever, redirecting Phase 29 toward A0-broad / R-B / A3.
- Either outcome is highly informative at low cost.

### 9.4 Preflight readiness

- A2 needs only target precompute pipeline changes + D-1 bid/ask compatibility check per target variant.
- No GPU, no windowed dataset, no new feature class.
- Preflight readiness score: 9/10 (highest of all candidate paths).

### 9.5 Phase 29 scaffolding establishment

- A2 sub-phase α can establish Phase 29's NG#A2-* anti-collapse guard pattern + 4-outcome H-Cx ladder + Phase 29 baseline reference definition + closed target allowlist (analogous to Phase 28's NG#A0/A1/A4 patterns).
- This scaffolding is then inherited by subsequent Phase 29 sub-phases (Path 1 / 3 / 4 / 5 / 6 if elevated later).

---

## 10. Why Path 1 (A0-broad alone) is dissent 1

### 10.1 Strongest unfalsified hypothesis

- A0-broad tests H-A0-broad — the strongest unfalsified hypothesis at Phase 29 opening (newly elevated by 28.0c-β FALSIFIED_A0_NARROW).
- If A0-broad PASSes: sequence/NN model class is the binding lever; Phase 29's rebase rationale is directly vindicated.
- If A0-broad FALSIFIED: H-B9 gains its 9th supporting data point; the seam is confirmed at an even deeper structural level (sequence models also fail), pushing routing toward A2 / R-B / Phase 30 rebase.

### 10.2 Cost-penalised

- GPU pipeline + windowed dataset + sequence training infrastructure all need to be set up.
- Estimated cost: ~4-6 sub-phase β-evals worth (including preflight PRs).
- Implementation risk: new pipeline class; OOS / Phase 22 frozen-OOS compatibility unknown for sequence cells.
- Preflight readiness score: 4/10 (lowest among single-axis paths).

### 10.3 Preserved as dissent 1

- A0-broad is **not** foreclosed by Path 2 primary.
- If user prefers to attack the strongest hypothesis directly despite cost, Path 1 is the natural choice.
- Dissent 1 ranking reflects information value × elevation novelty.

---

## 11. Why Path 7 (preflight-first) is dissent 2

### 11.1 Risk reduction before high-cost commitment

- Path 7 sequences preflight PRs (GPU availability + windowed dataset feasibility + new feature pipeline cost) before committing to Path 1 / 5 / 6.
- Reduces implementation risk of subsequent high-cost paths.
- Preflight PRs are doc-only; cumulative cost is low.

### 11.2 Natural complement to Path 1

- If A0-broad is the eventual choice, Path 7 reduces its preflight burden.
- Path 7 is dissent 2 (not Tier 3) because it directly enables Path 1 (dissent 1).

### 11.3 Trade-off

- Path 7 delays the first Phase 29 β-eval by 1-2 PRs.
- The trade-off is risk-reduction vs time-to-first-β.

---

## 12. Preflight requirements per path

| Path | GPU | Windowed data | New target precompute | New feature pipeline | D-1 compatibility | Phase 22 OOS compatibility | Phase 29 §10 baseline |
|---|---|---|---|---|---|---|---|
| Path 1 (A0-broad) | needed | needed | not needed | not needed | sequence-aware bid/ask harness | sequence-cell OOS handling | Phase 28 §10 inherited |
| **Path 2 (A2)** | not needed | not needed | needed | not needed | new target × D-1 check | A2 target on Phase 22 OOS | **defined per A2 α (Option 9c)** |
| Path 3 (R-B) | not needed | not needed | not needed | needed | unchanged | new features on Phase 22 OOS | Phase 28 §10 inherited |
| Path 4 (A3) | not needed | not needed | not needed | not needed | unchanged | gating-routed OOS compatibility | Phase 28 §10 inherited |
| Path 5 (A0-broad + R-B) | needed | needed | not needed | needed | sequence + new feature × D-1 | sequence + new-feature OOS | Phase 28 §10 inherited |
| Path 6 (A0-broad + A2) | needed | needed | needed | not needed | sequence + new target × D-1 | sequence + new-target OOS | defined per joint α (Option 9c) |
| Path 7 (preflight-first) | derisked via separate PR | derisked via separate PR | n/a | derisked via separate PR | derisked via separate PR | derisked via separate PR | n/a (no β-eval) |

---

## 13. Cumulative Phase 29 cost / budget pre-statement

Phase 29 cumulative β-eval cost so far: **0**.

| Path elevation | Projected sub-phase β-eval cost |
|---|---|
| Path 2 (A2 primary) | ~2 β-evals to A2 verdict |
| Path 1 (A0-broad dissent 1) | ~4-6 β-evals (including GPU / windowed preflight as part of α design) |
| Path 7 (preflight-first dissent 2) | 1-2 preflight PRs + subsequent first-mover (Path 1 / 5 / 6 likely) |
| Path 3 (R-B Tier 3) | ~2-3 β-evals (including new feature pipeline) |
| Path 5 (A0-broad + R-B joint Tier 3) | ~5-7 β-evals (GPU + windowed + new feature + joint) |
| Path 4 (A3 Tier 3) | ~2-3 β-evals (learned gating impl + AR4 ablation) |
| Path 6 (A0-broad + A2 joint Tier 3) | ~6-8 β-evals (GPU + windowed + new target + joint) |

**Note**: cumulative cost projections are informational. The user determines actual budget allocation at each routing decision.

---

## 14. Decision-rule pre-statement

Approving this PR squash-merge is a **routing decision** that **accepts the recommendation only**. The decision-rule mapping below identifies the **next PR** for each possible user-selected path. **There is no auto-route**; the user explicitly invokes the chosen path with a separate instruction after this routing review merges.

| User picks | Next PR (separate later; user-instructed) |
|---|---|
| **Path 2 (PRIMARY; recommended)** | `docs/design/phase29_0a_alpha_a2_target_redesign_design_memo.md` — Phase 29.0a-α A2 design memo defining closed target allowlist + Phase 29 §10 baseline reference per Option 9c + H-Cx ladder |
| **Path 1 (DISSENT 1; A0-broad alone)** | GPU / sequence pipeline preflight PR (analogous to Path 7 sub-step), then `docs/design/phase29_0a_alpha_a0_broad_design_memo.md` |
| **Path 7 (DISSENT 2; preflight-first)** | First preflight audit PR (GPU availability + sequence pipeline scaffolding); subsequent first-mover decision deferred until preflight completes |
| Path 3 (Tier 3; R-B alone) | `docs/design/phase29_0a_alpha_r_b_design_memo.md` |
| Path 5 (Tier 3; A0-broad + R-B joint) | GPU + R-B preflight PRs, then a joint sub-phase α design memo with explicit Policy C joint motivation block per PR #348 §7.2 |
| Path 4 (Tier 3; A3 alone) | `docs/design/phase29_0a_alpha_a3_design_memo.md` |
| Path 6 (Tier 3; A0-broad + A2 joint) | GPU preflight + joint sub-phase α design memo with explicit Policy C joint motivation block per PR #348 §7.2 |

**Critical**: this PR's merge **formally accepts the routing recommendation** (Path 2 as primary). It does **NOT** authorise the authoring of any subsequent PR. The Phase 29.0a-α A2 design memo (or any other path's α / preflight) requires a **separate explicit user instruction** subsequent to this merge.

---

## 15. Open questions (deferred to chosen path's sub-phase α; informational)

The memo records these as deferred; each is addressed at the relevant first sub-phase α PR:

1. If Path 2 (A2) elevated: what is the closed allowlist of target variants? (deferred to A2 sub-phase α)
2. If Path 2 elevated: what is the Phase 29 §10 baseline numeric under A2's first target variant? (deferred to A2 sub-phase α per Option 9c)
3. If Path 1 (A0-broad) elevated: what is the closed allowlist of sequence architectures? (deferred to A0-broad sub-phase α)
4. If Path 1 elevated: what is the windowed dataset shape (N M5 bars per sample)? (deferred to A0-broad sub-phase α; sequence pipeline class declaration)
5. If Path 3 (R-B) elevated: what is the closed allowlist of feature classes? (deferred to R-B sub-phase α)
6. If joint Path 5 / 6 elevated: what is the Policy C joint motivation block + attribution ambiguity handling design? (deferred to joint sub-phase α)
7. If Path 7 (preflight-first) elevated: what is the preflight PR sequence and dependency graph? (deferred to preflight PR planning)
8. What is the Phase 29 cumulative β-eval budget? (informational; deferred to user)
9. If Path 1 / 5 / 6 elevated: does Phase 29 retain `C-sb-baseline` as the canonical baseline cell ID for sequence cells, or define a sequence-aware analog? (deferred to sub-phase α)

---

## 16. Binding constraints (verbatim from PR #348 §17)

This routing review preserves every constraint binding at PR #348 merge:

- D-1 bid/ask executable harness preserved (until sub-phase α admits sequence-aware harness extension)
- R7-A subset preserved as default feature surface (until R-B admitted at sub-phase α)
- Triple-barrier realised-PnL target preserved as default (until A2 admitted at sub-phase α)
- Top-q on score selection rule preserved as default
- Symmetric Huber α=0.9 loss preserved as default
- Tabular LightGBM family preserved as default (until A0-broad admitted at sub-phase α)
- Validation-only selection preserved
- Test touched once preserved
- ADOPT_CANDIDATE wall preserved
- H2 PASS = PROMISING_BUT_NEEDS_OOS only
- NG#10 / NG#11 not relaxed
- γ closure PR #279 preserved
- X-v2 OOS gating required
- Phase 22 frozen-OOS preserved
- Production v9 20-pair (Phase 9.12 tip `79ed1e8`) untouched
- Phase 28 §10 baseline numeric immutable (n=34626 / Sharpe -0.1732 / ann_pnl -204664.4 / val Sharpe -0.1863); never retroactively modified
- Phase 29 baseline reference may be defined per sub-phase α (Option 9c; PR #348 §9)
- No prior verdict modification
- MEMORY.md unchanged inside PR
- A1 / A4 / A0-narrow exhausted statuses preserved
- R-T1 = FALSIFIED_under_A4 preserved
- A0-broad / A2 / R-B / A3 admissible at Phase 29 (Scope III; PR #348 §6)
- Policy C joint-axis admissibility preserved (PR #348 §7)
- Phase 27/28 inertia routes NOT admissible without amendment (PR #348 §11)
- No scope amendment in this PR
- No first sub-phase α in this PR
- No β-eval in this PR
- No production change in this PR
- **No auto-route after merge** (merge formally accepts recommendation only; subsequent authoring requires separate explicit user instruction)
- This PR is doc-only

### 16.1 What this PR is NOT (consolidated; non-duplicated)

- ❌ Phase 29 first sub-phase α design memo (separate later PR; user-instructed)
- ❌ GPU / windowed-data / sequence pipeline scaffolding (separate later PR if Path 1 / 7 elevated)
- ❌ New feature class data pipeline scaffolding (separate later PR if Path 3 / 5 elevated)
- ❌ A0-broad / A2 / R-B / A3 scope amendment (separate later PR if needed beyond Scope III)
- ❌ β-eval implementation
- ❌ Production change
- ❌ Prior verdict modification
- ❌ Phase 28 §10 baseline numeric modification (immutable; archived)
- ❌ ADOPT_CANDIDATE wall / NG#10 / NG#11 / γ / X-v2 / Phase 22 frozen-OOS relaxation
- ❌ Foreclosure of any path (all seven paths remain admissible at Phase 29; Tier 3 ranking is informational only)
- ❌ Auto-initiation of Path 2 or any path after merge
- ❌ MEMORY.md edit inside PR

---

## 17. References

### Phase 29 (kickoff)

- **PR #348** — Phase 29 kickoff memo (Scope III / Policy C / Option 9c / first-mover deferred)

### Phase 28 (immediate predecessor; full registry)

- **PR #335** — Phase 28 kickoff memo
- **PR #336** — Phase 28 first-mover routing review (template for this Phase 29 first-mover routing review)
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
- **PR #334** — Phase 27 closure memo

### Binding contracts

- **PR #279** — γ closure (production behavior contract; preserved)
- **Phase 22 frozen-OOS contract** (preserved)
- **X-v2 OOS gating** (required for any future production deployment)
- **Phase 9.12 production v9 closure tip `79ed1e8`** (production v9 20-pair; untouched throughout Phase 27, Phase 28, and Phase 29)

---

*End of `docs/design/phase29_first_mover_routing_review.md`.*
