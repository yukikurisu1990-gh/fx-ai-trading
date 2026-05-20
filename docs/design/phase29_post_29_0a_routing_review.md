# Phase 29 Post-29.0a Routing Review — Path 1 (A0-broad preflight-gated) PRIMARY; Path 4 (A0-broad + R-B joint) DISSENT 1; Path 3 (preflight-first) DISSENT 2; Path 2 / 5 / 6 Tier 3

**Type**: post-sub-phase-β routing review memo. **Doc-only**.
**Branch**: `research/phase29-post-29-0a-routing-review`
**Base**: master @ `abe1ed5` (post-PR #351)
**Pattern**: analogous to PR #349 (Phase 29 first-mover routing review) + PR #346 (post-28.0c routing review)
**Date**: 2026-05-20

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval **formally accepts the routing recommendation**: Path 1 (A0-broad sequence/NN alone, **preflight-gated**) is PRIMARY; Path 4 (A0-broad + R-B joint, Policy C) is DISSENT 1; Path 3 (preflight-first) is DISSENT 2; Path 2 (R-B alone), Path 5 (A3 alone), Path 6 (Phase 29 closure / rebase) are Tier 3.*
>
> ***Critical wording**: merging this PR does **NOT** auto-initiate any path. The merge **formally accepts the recommendation only**. The Path 1 sequencing is **preflight-gated**: even if Path 1 is elevated, the **immediate next PR is an A0-broad preflight audit PR**, not a sub-phase α design memo. The 29.0b-α design memo authorisation requires a separate explicit user instruction subsequent to the preflight audit's completion.*
>
> *This PR does **NOT**:*
>
> - *create a Phase 29.0b-α design memo (separate later PR; user-instructed);*
> - *create any GPU / windowed-data / pipeline preflight PR (separate later PR; first concrete PR if Path 1 / 3 / 4 elevated);*
> - *create any A0-broad / R-B / A3 scope amendment (separate later PR if needed beyond Scope III);*
> - *create a Phase 29 closure memo (separate later PR if Path 6 elevated; premature after 1 β-eval);*
> - *implement a β-eval, modify production, or touch any prior verdict;*
> - *modify the Phase 28 §10 baseline numeric (immutable; archived);*
> - *modify the Phase 29 §10 per-target baseline values (frozen at PR #351 for T1/T2/T3/T4);*
> - *relax ADOPT_CANDIDATE wall, NG#10, NG#11, γ closure PR #279, X-v2 OOS gating, or the Phase 22 frozen-OOS contract;*
> - *foreclose any path — A0-broad / R-B / A3 / joint all remain admissible at Phase 29 per Scope III (PR #348 §6) and Policy C (PR #348 §7);*
> - *auto-route to any chosen path after merge.*

---

## 1. Inherited motivation: 9-eval evidence picture

The val-selector picked C-sb-baseline (or per-target equivalent in Phase 29) in **9/9** sub-phase β-evals across **5 orthogonal axes** within the tabular LightGBM frame.

| # | Sub-phase | Axis attacked | Closed allowlist | Verdict |
|---|---|---|---|---|
| 1 | 27.0b-β (PR #311) | Channel B: S-C TIME penalty | α ∈ {0.0, 0.3, 0.5, 1.0} | REJECT_NON_DISCRIMINATIVE |
| 2 | 27.0c-β (PR #319) | Channel B: S-D calibrated EV | β ∈ {0.0, 0.3, 0.5, 1.0} | REJECT_NON_DISCRIMINATIVE |
| 3 | 27.0d-β (PR #325) | Channel B: S-E regression | symmetric Huber α=0.9 | REJECT_NON_DISCRIMINATIVE |
| 4 | 27.0e-β (PR #327) | Channel C: S-E quantile trim | family ∈ {5, 7.5, 10} | REJECT_NON_DISCRIMINATIVE |
| 5 | 27.0f-β (PR #332) | Channel A: S-E + R7-C regime | RCW with row-set isolation | REJECT_NON_DISCRIMINATIVE |
| 6 | 28.0a-β (PR #338) | A1 loss redesign | L1 / L2 / L3 closed | REJECT_NON_DISCRIMINATIVE |
| 7 | 28.0b-β (PR #342) | A4 selection rule redesign | R1 / R2 / R3 / R4 closed | REJECT_NON_DISCRIMINATIVE; R-T1 = FALSIFIED_under_A4 |
| 8 | 28.0c-β (PR #345) | A0-narrow tabular topology | AR1 / AR2 / AR3 / AR4 closed | REJECT_NON_DISCRIMINATIVE; FALSIFIED_A0_NARROW |
| **9** | **29.0a-β (PR #351)** | **A2 target redesign** | **T1 / T2 / T3 / T4 closed** | **REJECT_NON_DISCRIMINATIVE; FALSIFIED_A2_NARROW; R-T3 = FALSIFIED_under_T3** |

**H-B9 (seam exhausted at this architecture stack)**: 9 supporting data points across 5 axes; **strongly strengthened**.

---

## 2. Phase 29 sub-phase chain so far

| PR | Scope | Outcome |
|---|---|---|
| #348 | Phase 29 kickoff (Scope III / Policy C / Option 9c) | doc-only; admissibility declared |
| #349 | Phase 29 first-mover routing review | Path 2 A2 PRIMARY; Path 1 A0-broad DISSENT 1; Path 7 Preflight-first DISSENT 2 |
| #350 | Phase 29.0a-α A2 target redesign design memo | doc-only; closed 4-target allowlist pre-stated |
| #351 | Phase 29.0a-β A2 target redesign eval | A2-narrow FALSIFIED; all 4 targets FALSIFIED_TARGET_INSUFFICIENT; R-T3 = FALSIFIED_under_T3 |
| **This PR** | **Phase 29 post-29.0a routing review** | **doc-only; ranks 6 candidates; recommendation only** |

**Cumulative Phase 29 cost**: 1 β-eval (29.0a A2). Phase 28 closure followed 3 β-evals (28.0a + 28.0b + 28.0c). Phase 29 has 3 of 4 kickoff-admissible axes (A0-broad / R-B / A3) **still untested**.

---

## 3. What 29.0a-β added

### 3.1 FALSIFIED_A2_NARROW (verbatim from PR #351)

Per-target outcomes (all FALSIFIED_TARGET_INSUFFICIENT; row 3 of H-D1 ladder):

| Target | Val Sharpe lift vs Phase 29 §10 per-target baseline |
|---|---|
| T1 (fixed-horizon executable close PnL) | -0.0736 |
| T2 (time-weighted linear decay) | -0.4161 |
| T3 (multi-horizon {30, 60, 120}; absorbs R-T3) | -0.1320 |
| T4 (asymmetric K_FAV=2.0 / K_ADV=0.5) | -1.3248 |

Aggregate verdict: REJECT_NON_DISCRIMINATIVE. A2-narrow status: `FALSIFIED_A2_NARROW` (explicit; **NEVER** `FALSIFIED_ALL_A2`).

### 3.2 R-T3 resolved

R-T3 carry-forward (Phase 27 §11) was absorbed into A2 via T3 multi-horizon variant. T3 FALSIFIED → **R-T3 absorption status = `FALSIFIED_under_T3`** (resolved analogous to R-T1 = FALSIFIED_under_A4 at PR #342). R-T3 standalone elevation NOT admissible.

### 3.3 9th eval point

The 9-eval picture now spans 5 axes: score / selection / regime / tabular-topology / **target**. H-B9 gains its 9th supporting data point; the strongest active hypothesis at Phase 29 post-29.0a is now **9 ↔ 5** (data points ↔ axes exhausted).

### 3.4 Phase 29 §10 per-target baseline preserved

Phase 29 §10 baseline numeric (n_trades / Sharpe / ann_pnl per T1/T2/T3/T4) frozen at PR #351 in `artifacts/stage29_0a/phase29_section10_per_target_baseline.json`. **Not modified by this PR.** Phase 28 §10 archived numeric (n=34626 / Sharpe -0.1732 / ann_pnl -204664.4 / val Sharpe -0.1863) immutable; preserved as DIAGNOSTIC-ONLY 2nd reference per Option 9c.

---

## 4. Phase 29 admissibility status (post-29.0a)

Scope III + Policy C + Option 9c (PR #348) preserved. Per-axis status:

| Axis | Status at post-29.0a |
|---|---|
| **A2** (target redesign) | **exhausted** under tested closed 4-target allowlist (FALSIFIED_A2_NARROW); alternate target framings outside T1/T2/T3/T4 admissible via separate scope amendment |
| **A0-broad** (sequence / NN model class) | admissible at Phase 29 per Scope III; **never tested**; strongest unfalsified hypothesis |
| **R-B** (feature class beyond R7-A) | admissible at Phase 29 per Scope III; never tested |
| **A3** (learned regime gating / MoE) | admissible at Phase 29 per Scope III; never tested; **prior penalised** (AR4 deep failure 28.0c + T4 deep failure 29.0a) |
| **Joint A0-broad + R-B** | admissible per Policy C with explicit α motivation |
| **Joint A0-broad + A2** | NOT admissible without A2 scope amendment (A2 exhausted; revival requires α memo amendment) |
| **R-T1** | resolved at 28.0b (FALSIFIED_under_A4) |
| **R-T3** | resolved at 29.0a (FALSIFIED_under_T3) |
| **Phase 27/28 inertia routes** (A1 single-loss / A4 single-rule / A0-narrow topology / S-axis / C-sb-baseline-anchored sweeps) | NOT admissible without scope amendment (PR #348 §11) |

---

## 5. Six candidate next moves (formal specification)

### 5.1 Path 1 — A0-broad sequence / NN alone (preflight-gated; PROVISIONAL PRIMARY)

- **Axis**: sequence / NN model class beyond tabular LightGBM (RNN / LSTM / GRU / Temporal CNN / Transformer encoder / multi-head NN)
- **Hypothesis tested**: H-A0-broad (strongest unfalsified hypothesis after 29.0a)
- **Cell shape**: per-row score with sequence-shaped input (windowed M5 bars on R7-A); TBD at α
- **Baseline reference**: Phase 28 §10 inherited (target unchanged); arch-control = tabular LightGBM C-se-equivalent
- **Cost class**: high (GPU pipeline + windowed dataset + sequence training)
- **Sequencing**: **preflight-gated** — see §11.1 (Path 1 immediate next PR is preflight audit, NOT α design memo)

### 5.2 Path 2 — R-B feature-class redesign alone (single-axis; Tier 3)

- **Axis**: feature class beyond R7-A (path-shape / microstructure / multi-TF context / calendar / cross-asset)
- **Hypothesis tested**: H-R-B (carry-forward since 27.0d; never tested)
- **Cell shape**: tabular (same model class; same target; expanded feature set)
- **Baseline reference**: Phase 28 §10 inherited
- **Cost class**: moderate (feature engineering pipeline + data pipeline cost + sanity probes)

### 5.3 Path 3 — Preflight-first (no-go-with-preflight; DISSENT 2)

- **Description**: defer next-move selection by 1-2 PRs; sequence preflight PRs for GPU / windowed dataset / new feature pipeline; derisk Path 1 / 4 commitment without yet committing to A0-broad
- **Hypothesis tested**: none directly; risk reduction
- **Cost class**: low (doc-only preflight PRs)
- **Note**: if Path 1 PRIMARY is accepted, its **first concrete PR already includes the A0-broad preflight audit** (§11.1). Path 3 remains a separate route only if user prefers a fully decoupled preflight track without committing to A0-broad as the post-preflight first-mover.

### 5.4 Path 4 — A0-broad + R-B joint (Policy C; DISSENT 1)

- **Joint motivation**: sequence models naturally consume windowed feature surfaces; R-B's path-shape / multi-TF / calendar features are natural sequence inputs. Testing model class + feature class together can isolate joint interaction from single-axis levers.
- **Hypothesis tested**: H-A0-broad + H-R-B + joint interaction
- **Cell shape**: sequence-aware; windowed R-B + R7-A residual
- **Baseline reference**: Phase 28 §10 inherited (target unchanged)
- **Cost class**: highest (GPU + windowed dataset + new feature class + sequence training + joint motivation block + Policy C 5-outcome H-Cx ladder + attribution ablation cells)

### 5.5 Path 5 — A3 learned regime gating / MoE alone (single-axis; Tier 3)

- **Axis**: learned regime gating / MoE; adaptive routing beyond AR4 deterministic
- **Hypothesis tested**: H-A3 (further penalised; AR4 deep failure 28.0c + T4 deep failure 29.0a both regime-axis-adjacent)
- **Cell shape**: tabular base with learnable routing layer
- **Baseline reference**: Phase 28 §10 inherited
- **Cost class**: moderate (learned gating implementation + AR4 ablation control)

### 5.6 Path 6 — Phase 29 closure / rebase consideration (Tier 3 / premature)

- **Description**: close Phase 29 with FALSIFIED_A2_NARROW + 9-eval H-B9 confirmation; open Phase 30 with joint architecture / target / data / feature rebase
- **Required artifacts**: Phase 29 closure memo + Phase 30 kickoff memo (separate later PRs)
- **Cost class**: moderate-to-high (closure + kickoff + first sub-phase α)
- **Note**: **premature at post-29.0a**. Phase 28 closure followed 3 β-evals (28.0a / 28.0b / 28.0c). Phase 29 has tested only 1 of 4 kickoff-admissible axes (A2 done; A0-broad / R-B / A3 untested). Closure becomes more reasonable only after A0-broad (or R-B) also falsifies, unless user explicitly judges A0-broad / R-B / A3 prohibitively costly.

---

## 6. Hypothesis register update post-29.0a

| Hypothesis | Bias at post-29.0a |
|---|---|
| **H-B9** (seam exhausted at this architecture stack) | **strongly strengthened** (9 data points across 5 axes; up from 8 / 4 at post-28.0c) |
| **H-A0-broad** (sequence/NN model class required) | **strongest unfalsified hypothesis**; remains the leading candidate after A2 exhaustion |
| H-A2 (target misspecified) | **falsified under closed 4-target allowlist** (A2-narrow exhausted); alternate target framings admissible via amendment |
| **H-R-B** (R7-A feature surface insufficient; new feature class required) | not yet tested; carry-forward strengthens as second-strongest unfalsified single-axis hypothesis |
| **H-A3** (learned regime gating / MoE required) | **further penalised** — T4 asymmetric val Sharpe lift -1.3248 (worst of 9 evals) + AR4 deep failure (28.0c -0.4053); regime-axis attacks have lowest prior of the 4 Scope III axes |
| H-R-T1 (top-q selection rule alternative) | falsified at 28.0b (FALSIFIED_under_A4) |
| H-R-T3 (multi-horizon target helps) | falsified at 29.0a (FALSIFIED_under_T3) |

**Active unfalsified hypotheses at Phase 29 post-29.0a**: H-A0-broad (strongest), H-R-B (second-strongest), H-A3 (third; penalised).

---

## 7. Scoring rubric

Per-path scored on 6 axes; weights from PR #349 §6.

| Axis | Weight |
|---|---|
| Information value | 25% |
| Falsifiability discipline | 15% |
| Cost / time budget | 20% |
| Prior (Bayesian PASS rate given 9-eval) | 15% |
| Implementation risk | 15% |
| Preflight readiness | 10% |

---

## 8. Score table

| Path | Info | Falsif. | Cost | Prior | Impl. risk | Preflight | **Total** | **Rank** |
|---|---|---|---|---|---|---|---|---|
| **Path 1 — A0-broad alone (preflight-gated)** | 10 | 7 | 4 | 6 | 5 | 4 | **6.5** | **#1 (PRIMARY)** |
| **Path 4 — A0-broad + R-B joint** | 10 | 6 | 3 | 6 | 4 | 3 | **5.7** | **#2 (DISSENT 1)** |
| **Path 3 — Preflight-first** | 4 | 9 | 9 | n/a | 9 | 10 | **6.6** | **#3 (DISSENT 2)** |
| Path 2 — R-B alone | 7 | 8 | 6 | 5 | 7 | 7 | **6.6** | #4 (Tier 3) |
| Path 5 — A3 alone | 4 | 7 | 6 | 2 | 6 | 7 | **5.0** | #5 (Tier 3) |
| Path 6 — Phase 29 closure | 5 | 9 | 5 | n/a | 9 | 9 | **6.2** | #6 (Tier 3; premature) |

**Note on Path 3 vs Path 1 weighted total**: Path 3 (6.6) is numerically higher than Path 1 (6.5). However, Path 1 is upgraded to PRIMARY because:
1. Information value (25% weight) of Path 1 is 10/10 (directly tests H-A0-broad, the strongest unfalsified hypothesis); Path 3 is 4/10 (pure risk reduction; tests nothing directly).
2. Path 1 is **preflight-gated** — the preflight audit (effectively Path 3 sub-step) is embedded as Path 1's first concrete PR (§11.1), so Path 1 captures Path 3's risk-reduction benefit without sacrificing information value.
3. Path 3 as a separate route is preserved as DISSENT 2 for users who prefer a fully decoupled preflight without committing to A0-broad as the post-preflight first-mover.

**Note on Path 2 vs Path 3 ranking**: numerically tied (6.6). Path 3 ranked Dissent 2 (above Path 2 Tier 3) because:
- Path 3 is the natural complement to Path 1 (risk reduction); if Path 1 is rejected, Path 3 is the natural fallback that still keeps A0-broad on the future routing table
- Path 2 (R-B alone) is single-axis with lower information value than Path 1's joint-with-preflight framing

---

## 9. Provisional ranking

| Rank | Path | Type | Rationale |
|---|---|---|---|
| **#1 (PRIMARY)** | Path 1 — A0-broad alone (preflight-gated) | single-axis | strongest unfalsified hypothesis; preflight-gated sequencing controls implementation risk |
| **#2 (DISSENT 1)** | Path 4 — A0-broad + R-B joint | joint (Policy C) | directly tests sequence × feature interaction; highest information value but highest cost + attribution complexity |
| **#3 (DISSENT 2)** | Path 3 — Preflight-first | no-go-with-preflight | fully decoupled preflight; useful if user prefers not to commit to A0-broad as post-preflight first-mover |
| #4 (Tier 3) | Path 2 — R-B alone | single-axis | lower information value than A0-broad; naturally absorbable into joint Path 4 later |
| #5 (Tier 3) | Path 5 — A3 alone | single-axis | AR4 + T4 deep failures penalise priors; lowest of unfalsified hypotheses |
| #6 (Tier 3; premature) | Path 6 — Phase 29 closure | no-go | only 1 of 4 admissible axes tested; closure premature without A0-broad / R-B tested |

---

## 10. Why Path 1 (A0-broad alone, preflight-gated) primary — synthesis

### 10.1 Strongest unfalsified hypothesis

H-A0-broad was the strongest unfalsified hypothesis at PR #349 (post-kickoff routing). It **remains the strongest after A2 exhaustion**, because A2 falsification weakens H-A2 (the only sibling-strength unfalsified hypothesis at that time).

### 10.2 9-eval picture suggests model class is the leading lever

The 9 exhausted axes cover: score / selection / regime / tabular topology / target. The remaining unaddressed levers are:

- **Model class** (tabular → sequence/NN) — **H-A0-broad** (most structurally distinct from 9 exhausted axes)
- Feature class (R7-A → R-B) — H-R-B (feature-axis related; partial overlap with channel A regime feature exhaustion)
- Learned regime gating (deterministic → MoE/learned) — H-A3 (regime-axis; lowest prior)

Model class is the **most structurally distinct** lever; tests the most fundamental architectural assumption of the 9-eval picture.

### 10.3 A2 exhaustion eliminated the lowest-cost competitor

At PR #349, A2 was primary specifically because of **low cost** (existing tabular pipeline reused; only target precompute changed). A2 has now been tested and falsified. **A0-broad's high cost is no longer a relative disadvantage** at Phase 29 second sub-phase — the remaining single-axis paths (R-B, A3) are also moderate-to-high cost while testing lower-priority hypotheses.

### 10.4 Preflight-gating controls implementation risk

A0-broad introduces a **new pipeline class**: GPU / sequence training / windowed dataset / sequence-aware D-1 harness / sequence-cell OOS compatibility / sequence-cell FAIL-FAST harness analog.

**Preflight-gating** (§11.1) means Path 1's **first concrete PR is an A0-broad preflight audit**, not the α design memo directly. This:

- Establishes GPU compute availability + pipeline class choice (PyTorch / JAX / TensorFlow)
- Verifies windowed / sequence dataset feasibility from existing M1 + M5 outcome data
- Confirms sequence-cell D-1 bid/ask harness extension is achievable
- Verifies Phase 22 frozen-OOS compatibility with sequence-cell format
- Defines sequence baseline / control reproduction requirements (the 7th anchor in bit-tight chain: 27.0d → 27.0f → 28.0a → 28.0b → 28.0c → 29.0a target-control → **29.0b A0-broad sequence-control**)

The preflight audit PR is doc-only; the 29.0b-α design memo follows it; the β-eval follows the α merge. **3-step preflight-gated sequence under Path 1 primary**.

### 10.5 Path 1 vs Path 3 distinction

- Path 1 (preflight-gated): user accepts A0-broad as the post-preflight first-mover; preflight audit + α + β sequenced in order.
- Path 3 (preflight-first): user wants the same preflight content but **without committing to A0-broad** as the post-preflight first-mover; routing decision deferred until preflight completes.

Path 1 captures Path 3's risk-reduction value while preserving the routing decision (A0-broad primary). Path 3 remains DISSENT 2 for users who prefer the decoupled framing.

---

## 11. Why Path 4 (A0-broad + R-B joint) dissent 1 — synthesis

### 11.1 Directly tests sequence × feature joint hypothesis

Phase 29 closure rationale (PR #347) was that single-axis tests fragment the lever. Joint A0-broad + R-B addresses this directly: sequence models naturally consume windowed feature surfaces; testing them together prevents the "sequence on R7-A vs tabular on R-B" fragmentation.

### 11.2 Higher information value than R-B alone

If the issue is the sequence × feature interaction, R-B alone (Path 2) would falsify in the same way as A0-broad alone (Path 1) — neither alone addresses the joint hypothesis. Path 4 directly tests it.

### 11.3 Cost-penalised; attribution complexity

GPU + windowed dataset + new feature class + sequence training + joint motivation block + Policy C 5-outcome H-Cx ladder + attribution ablation cells = highest cost of all 6 paths.

**Dissent 1**, not primary, because:
- Phase 29's first sequence sub-phase should establish A0-broad single-axis scaffolding (NG#A0-broad-* / sequence-cell FAIL-FAST / sequence-control reproduction) before adding R-B attribution ambiguity
- attribution ambiguity handling (Policy C §7.2) requires per-axis ablation cells, doubling the cost of joint vs single-axis at first sequence sub-phase
- a failed joint sub-phase is less informative than a failed single-axis sub-phase (joint failure could attribute to one axis, both, or interaction)

### 11.4 Elevation criterion

If user prefers to attack the strongest joint hypothesis directly despite cost + attribution complexity, Path 4 is the natural choice. The Policy C joint motivation block must include explicit attribution handling per PR #348 §7.2.

---

## 12. Why Path 3 (preflight-first) dissent 2 — synthesis

### 12.1 Risk-reduction route preserved

If Path 1 PRIMARY is not accepted, Path 3 sequences GPU + windowed + sequence pipeline preflight PRs (doc-only) without yet committing to A0-broad. This preserves A0-broad / R-B / A3 / joint as the post-preflight decision-set.

### 12.2 Why dissent 2, not primary

Path 1's preflight-gated sequencing already embeds the preflight audit as Path 1's first concrete PR. Path 3 is therefore "Path 1 minus the routing commitment". It is dissent 2 — a more cautious framing — not primary.

### 12.3 Elevation criterion

Choose Path 3 if user wants to keep the post-preflight decision fully open (i.e., A0-broad might not be the next sub-phase after preflight; R-B / A3 / joint also on the table). Path 1's preflight-gated framing assumes A0-broad is the post-preflight first-mover.

### 12.4 Note on Path 3 weighted total

Path 3's 6.6 weighted total exceeds Path 1's 6.5 numerically. The PRIMARY designation reflects **information value × routing commitment**: Path 1 directly tests H-A0-broad after the preflight audit; Path 3 does not commit to any specific test post-preflight. The ranking inversion is intentional — Path 1's preflight-gating absorbs Path 3's risk-reduction benefit while preserving the high-information-value commitment.

---

## 13. R-B / A3 / closure rationale

### 13.1 Path 2 (R-B alone) Tier 3

- Lower information value than A0-broad (model class is more structurally distinct from 9 exhausted axes than feature class)
- R-B testing alone leaves the sequence × feature joint interaction untested
- Naturally absorbable into joint Path 4 if A0-broad becomes primary
- R-B remains deferred-not-foreclosed; admissible at Phase 29 per Scope III

### 13.2 Path 5 (A3 alone) Tier 3

- **AR4 deep failure** (28.0c val Sharpe lift -0.4053; worst of 4 ARs) penalises priors
- **T4 deep failure** (29.0a val Sharpe lift -1.3248; worst of 4 targets) further penalises; T4 asymmetric K_FAV / K_ADV is regime-axis-adjacent in that it tests asymmetric resolution
- Regime-axis attacks now have **two** deep-failure data points
- A3 remains deferred-not-foreclosed (low priority); admissible at Phase 29 per Scope III

### 13.3 Path 6 (Phase 29 closure) Tier 3 / premature

- Phase 29 has tested only **1 of 4** kickoff-admissible axes (A2 done; A0-broad / R-B / A3 untested)
- Phase 28 closure followed **3 β-evals** (28.0a / 28.0b / 28.0c)
- Phase 29 closure at 1 β-eval is **premature** unless user explicitly judges A0-broad / R-B / A3 prohibitively costly
- **Closure becomes more reasonable only after A0-broad (or R-B) also falsifies**, unless user explicitly decides cost is prohibitive
- Listed as Tier 3 with "premature" caveat

---

## 14. Preflight requirements per path

| Path | GPU | Windowed data | New target | New feature pipeline | D-1 compat | Phase 22 OOS |
|---|---|---|---|---|---|---|
| **Path 1 (A0-broad alone, preflight-gated)** | needed | needed | not needed | not needed | sequence-aware bid/ask | sequence-cell OOS |
| Path 2 (R-B alone) | not needed | not needed | not needed | needed | unchanged | new features on OOS |
| Path 3 (preflight-first) | derisked via separate PR | derisked via separate PR | n/a | derisked via separate PR | derisked | derisked |
| Path 4 (A0-broad + R-B joint) | needed | needed | not needed | needed | sequence + new feature × D-1 | sequence + new-feature OOS |
| Path 5 (A3 alone) | not needed | not needed | not needed | not needed | unchanged | gating-routed OOS |
| Path 6 (Phase 29 closure) | n/a | n/a | n/a | n/a | n/a | n/a (no β-eval) |

---

## 15. Decision rule pre-statement

Approving this PR squash-merge **formally accepts the routing recommendation only**. The decision-rule mapping below identifies the **next PR** for each possible user-selected path. **There is no auto-route**; the user explicitly invokes the chosen path with a separate instruction after merge.

### 15.1 If user picks Path 1 (PRIMARY; A0-broad alone, preflight-gated)

**3-step preflight-gated sequence**:

1. **First concrete PR**: A0-broad preflight audit PR (doc-only). Audits:
   - GPU compute availability (CUDA device check; pipeline class choice — PyTorch / JAX / TensorFlow)
   - Windowed / sequence dataset feasibility (regenerable from M1 + M5 outcome data; data shape + storage)
   - Sequence-cell D-1 bid/ask harness feasibility (sequence-aware executable harness extension)
   - Phase 22 frozen-OOS compatibility with sequence-cell format
   - Sequence baseline / control reproduction requirements (7th anchor in bit-tight chain: 27.0d → 27.0f → 28.0a → 28.0b → 28.0c → 29.0a → **29.0b A0-broad sequence-control**)
2. **Second PR**: `docs/design/phase29_0b_alpha_a0_broad_design_memo.md` — 29.0b-α design memo after preflight audit merge; pre-states closed sequence-architecture allowlist + sequence-cell FAIL-FAST + H-Cx ladder under Policy C single-axis default
3. **Third PR**: 29.0b-β eval implementation

### 15.2 If user picks Path 4 (DISSENT 1; A0-broad + R-B joint, Policy C)

1. **GPU + R-B preflight PRs** (sequenced or parallel; preflight audit must also cover R-B feature class data pipeline)
2. **Joint α design memo PR**: `docs/design/phase29_0b_alpha_a0_broad_plus_r_b_joint_design_memo.md` — joint α with explicit Policy C joint motivation block per PR #348 §7.2 (why axes are inseparable; how falsifiability is preserved; how attribution ambiguity is handled in 5-outcome H-Cx ladder)
3. **Third PR**: joint β-eval implementation

### 15.3 If user picks Path 3 (DISSENT 2; preflight-first)

1. **First concrete PR**: preflight audit PR (analogous to Path 1 §15.1 step 1, but without commitment to A0-broad as post-preflight first-mover)
2. **Subsequent**: user picks next sub-phase from {A0-broad / R-B / A0-broad+R-B joint / A3} after preflight completes

### 15.4 If user picks Path 2 (Tier 3; R-B alone)

1. **R-B α design memo PR**: `docs/design/phase29_0b_alpha_r_b_design_memo.md`
2. **β-eval PR**

### 15.5 If user picks Path 5 (Tier 3; A3 alone)

1. **A3 α design memo PR**: `docs/design/phase29_0b_alpha_a3_design_memo.md`
2. **β-eval PR**

### 15.6 If user picks Path 6 (Tier 3; Phase 29 closure / rebase)

1. **Phase 29 closure memo PR**: `docs/design/phase29_closure_memo.md` (analogous to PR #347 Phase 28 closure)
2. **Phase 30 kickoff memo PR** (separate later)

**Critical**: this PR's merge formally accepts the routing recommendation (Path 1 PRIMARY). It does **NOT** authorise the authoring of any subsequent PR. The A0-broad preflight audit PR (or any other path's first concrete PR) requires a **separate explicit user instruction** subsequent to this merge.

---

## 16. Open questions deferred to chosen path's α / preflight (informational)

The memo records these as deferred; each is addressed at the relevant PR.

1. If Path 1 elevated: what is the preflight audit's GPU / pipeline class choice? (deferred to A0-broad preflight audit PR)
2. If Path 1 elevated: what is the windowed dataset shape (N M5 bars per sample)? (deferred to A0-broad preflight audit PR)
3. If Path 1 elevated: what is the closed sequence-architecture allowlist? (deferred to 29.0b-α A0-broad design memo)
4. If Path 1 elevated: what is the 29.0b-α Phase 29 §10 baseline reference policy (inherit Phase 28 §10 directly, since target unchanged, or define new sequence-cell reference)? (deferred to 29.0b-α)
5. If Path 4 elevated: what is the Policy C joint motivation block + attribution ambiguity handling design? (deferred to joint α)
6. If Path 2 elevated: what is the closed feature-class allowlist? (deferred to R-B α)
7. If Path 3 elevated: what is the preflight PR dependency sequence? (deferred to preflight planning)
8. If Path 6 elevated: is Phase 29 closure premature without A0-broad / R-B test? (user judgment; this memo says yes; user can override)

---

## 17. Binding constraints + what this PR is NOT (consolidated; non-duplicated)

### 17.1 Binding constraints preserved (verbatim from PR #348 §17 + PR #350 §17)

- D-1 bid/ask executable harness preserved (until 29.0b-α admits sequence-aware harness extension under Path 1 / 4)
- R7-A feature surface preserved as default (until R-B admitted at α under Path 2 / 4)
- Triple-barrier realised-PnL target preserved as default (A2-narrow exhausted under closed 4-target allowlist; alternate target framings admissible via separate scope amendment)
- Top-q on score selection rule preserved as default
- Symmetric Huber α=0.9 loss preserved as default
- Tabular LightGBM model class preserved as default (until A0-broad admitted at α under Path 1 / 4)
- Validation-only selection preserved
- Test touched once preserved
- ADOPT_CANDIDATE wall preserved
- H2 PASS = PROMISING_BUT_NEEDS_OOS only
- NG#10 / NG#11 not relaxed
- γ closure PR #279 preserved
- X-v2 OOS gating required
- Phase 22 frozen-OOS preserved
- Production v9 20-pair (Phase 9.12 tip `79ed1e8`) untouched
- **Phase 28 §10 baseline numeric immutable** (n=34626 / Sharpe -0.1732 / ann_pnl -204664.4 / val Sharpe -0.1863); never retroactively modified; inherited as DIAGNOSTIC-ONLY 2nd reference per Option 9c
- **Phase 29 §10 per-target baseline** (T1/T2/T3/T4 numeric values frozen at PR #351; persisted to `artifacts/stage29_0a/phase29_section10_per_target_baseline.json`) preserved as archived reference
- No prior verdict modification (Phase 27 + Phase 28 + Phase 29.0a verdicts preserved verbatim)
- MEMORY.md unchanged inside PR
- A1 / A4 / A0-narrow / A2-narrow exhausted statuses preserved
- R-T1 = FALSIFIED_under_A4 / R-T3 = FALSIFIED_under_T3 preserved
- A0-broad / R-B / A3 admissible at Phase 29 (Scope III; PR #348 §6) — only A2 now exhausted
- Policy C joint-axis admissibility preserved (PR #348 §7)
- Option 9c dual baseline reference policy preserved (PR #348 §9; Phase 28 §10 archived + Phase 29 §10 per-target frozen)
- Phase 27/28 inertia routes NOT admissible without amendment (PR #348 §11)
- No scope amendment in this PR
- No 29.0b-α in this PR
- No preflight audit PR in this PR
- No β-eval in this PR
- No Phase 29 closure / Phase 30 kickoff in this PR
- No production change in this PR
- **No auto-route after merge** (merge formally accepts recommendation only; subsequent authoring requires separate explicit user instruction)
- This PR is doc-only

### 17.2 What this PR is NOT

- ❌ 29.0b-α design memo (separate later PR)
- ❌ A0-broad preflight audit PR (separate later PR; the **first concrete PR if Path 1 PRIMARY elevated**)
- ❌ GPU / windowed-data / sequence pipeline scaffolding (separate later PR)
- ❌ New feature class data pipeline scaffolding (separate later PR if Path 2 / 4 elevated)
- ❌ A0-broad / R-B / A3 scope amendment (separate later PR if needed beyond Scope III)
- ❌ Phase 29 closure memo (separate later PR if Path 6 elevated)
- ❌ Phase 30 kickoff (separate later PR after Phase 29 closure)
- ❌ β-eval implementation
- ❌ Production change
- ❌ Prior verdict modification
- ❌ Phase 28 §10 baseline numeric modification (immutable; archived)
- ❌ Phase 29 §10 per-target baseline modification (frozen at PR #351; preserved as archived reference)
- ❌ ADOPT_CANDIDATE wall / NG / γ / X-v2 / Phase 22 frozen-OOS relaxation
- ❌ Foreclosure of any path (A0-broad / R-B / A3 / joint / closure all remain admissible)
- ❌ Auto-initiation of Path 1 or any path after merge
- ❌ MEMORY.md edit inside PR

---

## 18. References

### Phase 29 PRs

- PR #348 — Phase 29 kickoff (Scope III / Policy C / Option 9c)
- PR #349 — Phase 29 first-mover routing review (Path 2 A2 PRIMARY)
- PR #350 — Phase 29.0a-α A2 design memo
- PR #351 — Phase 29.0a-β A2 target redesign eval (A2-narrow FALSIFIED; R-T3 = FALSIFIED_under_T3; 9-eval picture)
- **This PR** — Phase 29 post-29.0a routing review

### Phase 28 (immediate predecessor; pattern source)

- PR #335 — Phase 28 kickoff
- PR #336 — Phase 28 first-mover routing review (template)
- PR #338 — Phase 28.0a-β A1 (A1 exhausted)
- PR #342 — Phase 28.0b-β A4 (A4 exhausted; R-T1 = FALSIFIED_under_A4)
- PR #345 — Phase 28.0c-β A0-narrow (A0-narrow exhausted; FALSIFIED_A0_NARROW)
- PR #346 — Phase 28 post-28.0c routing review (closure PRIMARY pattern)
- PR #347 — Phase 28 closure memo

### Phase 27 inheritance

- PR #311 / #319 / #325 / #327 / #332 — Phase 27.0b/c/d/e/f sub-phase β-evals (5 of 9 evidence points)
- PR #334 — Phase 27 closure memo

### Binding contracts

- PR #279 — γ closure
- Phase 22 frozen-OOS contract
- X-v2 OOS gating
- Phase 9.12 production v9 closure tip `79ed1e8` (untouched throughout Phase 27 / Phase 28 / Phase 29)

---

*End of `docs/design/phase29_post_29_0a_routing_review.md`.*
