# Phase 28 — Post-28.0a Routing Review

**Type**: doc-only routing review
**Status**: routes Phase 28 after 28.0a-β A1 objective redesign eval (PR #338); does NOT initiate any sub-phase
**Branch**: `research/phase28-post-28-0a-routing-review`
**Base**: master @ `2b6dee1` (post-PR #338 / Phase 28.0a-β eval merge)
**Pattern**: analogous to PR #319 / #322 / #326 / #329 / #333 / #336 routing reviews
**Date**: 2026-05-17

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Phase 28 post-28.0a routing review**. It records the **comparison + recommendation** across the 4 remaining admissible axes (A0 / A2 / A3 / A4 per Phase 28 kickoff PR #335 §5; A1 now exhausted under the 28.0a-β closed 3-loss allowlist), nominates a **primary** second-mover and **two dissents**, and pre-states a decision rule under which the user can elevate either dissent. It does **NOT**:*
>
> - *authorise any A4 / A0 / A2 / A3 sub-phase initiation,*
> - *create any Phase 28 sub-phase design memo,*
> - *open any scope amendment,*
> - *elevate R-T1 / R-B / R-T3 (all carry-forward routes remain in their PR #334 status),*
> - *modify the §10 baseline numeric or any prior verdict.*
>
> *The recommendation is **scope-level only**. Executing it requires a **separate later user routing decision**, after which a sub-phase design memo PR will be drafted. R-T1 / R-B / R-T3 reframing also requires a separate routing decision.*

Same approval-then-defer pattern as PR #319 / #322 / #326 / #329 / #333 / #336.

---

## 1. Executive summary

**Primary recommendation**: **A4 monetisation-aware selection** (Phase 28 second-mover).
**Dissent 1**: **A0 architecture redesign**.
**Dissent 2**: **A2 target redesign**.

| Bucket | Axis | Prior P(GO) (post-28.0a updated) | One-line rationale |
|---|---|---|---|
| **Tier 1 (primary)** | **A4** monetisation-aware selection | **35-45 %** | 28.0a-β 6/6 val-selector-picks-baseline pattern directly attacks H-B7; R-T1 reframing absorbed; ranking signal (S-E Spearman +0.438 / L2 +0.466 / L3 +0.459) is real and selection rule is the residual unattacked surface. |
| Tier 2 (dissent 1) | **A0** architecture redesign | 25-35 % | 28.0a-β reinforces H-B9 (seam exhausted at this architecture); A0 is the most direct attack but highest cost. Positioned as "A4 が失敗した場合の next move". |
| Tier 2 (dissent 2) | **A2** target redesign | 15-25 % | Target adequacy (H-B3 partial) remains unresolved; scope amendment required and §10 baseline becomes semantically tricky. |
| Tier 3 (below dissent) | **A3** regime-conditioned modeling | 10-20 % | Natural R-B reframing home, but Phase 27 R7-C inertia risk remains medium-high. Better as Phase 28 third move. |

**A1 status**: **exhausted under the closed 3-loss allowlist tested at 28.0a-β** (L1 magnitude-weighted Huber w_clip=30.0 / L2 asymmetric Huber δ_pos=0.5,δ_neg=1.5 / L3 spread-cost-weighted Huber γ=0.5). A1 further micro-redesign within the same closed allowlist is **NOT admissible**. A new A1-class loss family (e.g., non-Huber backbone, additional variants beyond the 3-loss allowlist) is **deferred-not-foreclosed** and requires a **scope amendment PR** before any further A1 sub-phase.

R-T1 / R-B remain deferred-not-foreclosed (PR #334 carry-forward); R-T3 below-threshold; none elevated by this PR. R-T1 reframing under A4 is now the natural Phase 28 fit (see §13).

---

## 2. Routing review semantics — what this PR does and does NOT do

Phase 28 has now run **one** sub-phase β-eval (28.0a-β; PR #338). With A1 exhausted, this PR serves as the **Phase 28 second-mover routing decision** — analogous to PR #319 (post-27.0b) / PR #322 (post-27.0c) / PR #326 (post-27.0d) / PR #329 (post-27.0e) / PR #333 (post-27.0f) under Phase 27.

**This PR does**:

1. Compare the 4 remaining admissible axes A0 / A2 / A3 / A4 along the 9-column rubric in §5.
2. Recommend a primary second-mover (A4) and two dissents (A0, A2).
3. Update prior P(GO) for each axis given 28.0a-β evidence (§14 / §16).
4. Pre-state the decision rule under which the user can elevate either dissent (§16).
5. Record R-T1 / R-B / R-T3 reframing applicability per axis (§13) without electing to use it.
6. Evaluate Phase 27 / 28 inertia risk per axis (§11).
7. Document A1's exhausted status with a deferred-not-foreclosed clause for scope-amendment revival (§3.4).

**This PR does NOT**:

1. Initiate any sub-phase (no β-eval, no design memo).
2. Author any falsifiable H-Cx that would belong in a sub-phase design memo.
3. Elevate R-T1 / R-B / R-T3.
4. Modify the §10 baseline numeric or any prior verdict.
5. Touch src / scripts / tests / artifacts / .gitignore / MEMORY.md.
6. Trigger auto-routing.
7. Foreclose A1 absolutely — scope-amendment revival remains possible per §3.4.

---

## 3. Phase 28 evidence anchors (post-28.0a snapshot)

Phase 28's second-mover routing review draws its evidence from three sources stable as of master `2b6dee1`:

### 3.1 6-eval evidence picture (Phase 27 + Phase 28.0a)

The Phase 27 closure memo (PR #334 §4.1) recorded the 5-eval evidence picture. 28.0a-β (PR #338) extends it to **6 sub-phase β-evals**. The val-selected (cell\*, q\*) record remains **bit-identical** across all six:

| sub-phase | Channel | Intervention | val-selected cell | val Sharpe | val n | test Sharpe | test n | H-Bx outcome | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 27.0b-β | B | S-C TIME penalty α grid | C-alpha0 (S-B) | -0.1863 | 25,881 | -0.1732 | 34,626 | — | REJECT |
| 27.0c-β | B | S-D calibrated EV | C-sb-baseline (S-B) | -0.1863 | 25,881 | -0.1732 | 34,626 | — | REJECT |
| 27.0d-β | B | S-E regression on realised PnL | C-sb-baseline (S-B) | -0.1863 | 25,881 | -0.1732 | 34,626 | — | REJECT (split) |
| 27.0e-β | C | R-T2 quantile-family trim | C-sb-baseline (S-B) | -0.1863 | 25,881 | -0.1732 | 34,626 | H-B5 PARTIAL_SUPPORT | REJECT (split) |
| 27.0f-β | A | R7-C regime/context features | C-sb-baseline (S-B) | -0.1863 | 25,881 | -0.1732 | 34,626 | H-B6 FALSIFIED_R7C_INSUFFICIENT | REJECT (split) |
| **28.0a-β** | **— (A1 objective)** | **L1 / L2 / L3 closed allowlist** | **C-sb-baseline (S-B)** | **-0.1863** | **25,881** | **-0.1732** | **34,626** | **H-C1 all 3 FALSIFIED_OBJECTIVE_INSUFFICIENT** | **REJECT (split)** |

**Bit-identical val-selected outcome in 6/6 sub-phases.** Six different interventions across four channels (B / C / A / A1-objective) produced the same val-selected cell.

### 3.2 28.0a-β specific findings (NEW)

From PR #338's eval_report.md / aggregate_summary.json:

| Cell | q\* | val Sharpe | val n | test Sharpe | test n | test Spearman | H-C1 outcome |
|---|---|---|---|---|---|---|---|
| C-a1-L1 (magnitude-weighted) | 30 | -0.305 | 155,264 | -0.241 | 161,044 | +0.230 | FALSIFIED_OBJECTIVE_INSUFFICIENT (row 3) |
| C-a1-L2 (asymmetric δ_pos=0.5/δ_neg=1.5) | 5 | -0.593 | 25,936 | -0.573 | 19,922 | +0.466 | FALSIFIED_OBJECTIVE_INSUFFICIENT (row 3) |
| C-a1-L3 (spread-cost γ=0.5) | 40 | -0.602 | 206,994 | -0.562 | 183,236 | +0.459 | FALSIFIED_OBJECTIVE_INSUFFICIENT (row 3) |
| C-a1-se-r7a-replica (control) | 40 | -0.573 | 206,985 | -0.483 | 184,703 | +0.438 | bit-tight reproduction of 27.0d C-se |
| C-sb-baseline (§10) | 5 | -0.186 | 25,881 | -0.173 | 34,626 | -0.154 | §10 baseline reproduction PASS |

**Three substantive observations**:

1. **All three loss variants produce val Sharpe worse than §10 baseline** (sharpe lift −0.119 / −0.407 / −0.416). Aggregate verdict REJECT_NON_DISCRIMINATIVE; routing implication: objective-axis exhausted.
2. **L2 and L3 raise cell Spearman to +0.466 and +0.459** — the highest cell-Spearman scores recorded in the Phase 27+28 inheritance chain (S-E Spearman +0.438). Ranking signal is **real and strengthening**, but does not monetize at the val-selected (cell\*, q\*) record.
3. **C-a1-se-r7a-replica bit-reproduces 27.0d C-se** (val Sharpe −0.573 / test Sharpe −0.483 / test n 184,703 — within tolerance of 27.0d's published numbers). The harness is reliable; the negative result is substantive, not a wiring artefact.

### 3.3 §10 baseline (immutable; verbatim from PR #335 §10)

| Metric | Value |
|---|---|
| Picker | S-B raw (P(TP) − P(SL)) |
| Cell | C-sb-baseline |
| Selected q\* | 5 % |
| Val Sharpe | -0.1863 |
| Val n_trades | 25,881 |
| **Test Sharpe** | **-0.1732** |
| **Test n_trades** | **34,626** |
| **Test ann_pnl (pip)** | **-204,664.4** |
| Test formal Spearman(score, realised_pnl) | -0.1535 |

The §10 baseline is the **immutable reference** for every Phase 28 sub-phase eval. PR #338 confirms reproduction within tolerance.

### 3.4 A1 status — exhausted but not foreclosed

**Status at this routing review**: A1 (objective redesign) is **exhausted under the closed 3-loss allowlist tested at 28.0a-β**. The tested allowlist {L1 magnitude-weighted Huber, L2 asymmetric Huber, L3 spread-cost-weighted Huber} produced 3/3 FALSIFIED_OBJECTIVE_INSUFFICIENT outcomes. No further A1 sub-phase within this closed allowlist is admissible.

**Deferred-not-foreclosed**: A new A1-class loss family — e.g., **non-Huber backbone** (MSE / quantile regression / log-cosh), **additional variants** beyond the 3-loss allowlist, or **fundamentally different loss structures** (e.g., ranking-based losses, contrastive losses, monotonicity-constrained losses) — is **NOT admissible at this routing review** but **MAY be revived** via a **separate Phase 28 scope amendment PR** analogous to PR #330 (Phase 27 R7-C scope amendment). The scope amendment would have to:

- pre-state the new loss family and a falsifiable hypothesis distinct from H-C1;
- explain why the new loss is structurally different from L1 / L2 / L3 (not a numeric variant);
- preserve the closed-allowlist principle (no open-ended sweep);
- preserve all binding constraints (§18).

This routing review does **not** initiate such an amendment.

### 3.5 Carry-forward hypotheses (updated by 28.0a-β)

| ID | Status before 28.0a-β | Status after 28.0a-β |
|---|---|---|
| H-B7 — val-selection rule misspecified | UNRESOLVED (PR #334 §9) | **STRENGTHENED** — 6/6 val-selector-picks-baseline pattern is the most direct evidence; motivates A4 |
| H-B8 — path / microstructure / multi-TF feature class | UNRESOLVED (PR #334 §9) | UNRESOLVED — 28.0a does not test feature-class question; motivates A3 (deferred) |
| H-B9 — seam exhausted at this architecture | Phase 28 background premise (PR #334 §9) | **STRENGTHENED** — 28.0a A1 negative result is a 6th data point against same-architecture interventions; motivates A0 |

### 3.6 Carry-forward register status (PR #334 §11 unchanged)

- **R-T1** (selection-rule redesign): deferred-not-foreclosed; prior 25-35 %; **reframing under A4 admissible**
- **R-B** (different feature axis): deferred-not-foreclosed; prior 15-25 %; **reframing under A3 / A0 / A2 admissible + scope amendment required**
- **R-T3** (concentration formalisation): below-threshold; deferred; **NOT a dissent**

---

## 4. What 28.0a-β changes about the routing space

The 28.0a-β result delivers six pieces of additional information that update the Phase 28 first-mover routing review (PR #336):

1. **Objective-axis exhaustion is now formally established.** Phase 27 sub-phases tested S-C / S-D / S-E (score-axis micro-redesigns) and 28.0a tested L1 / L2 / L3 (closed loss allowlist). Together: 6 sub-phases have tried 6 different objective formulations; none lifted Sharpe above §10. The objective axis under the closed allowlist tested is **exhausted at this architecture / feature / target setup**.

2. **Scores can produce strong Spearman signals.** S-E (+0.438) / L2 (+0.466) / L3 (+0.459) all preserve or strengthen the ranking signal first surfaced at 27.0d. The discrimination half of the problem is **solved**.

3. **Selection rule is the unattacked surface.** All 6 sub-phases used the same **top-quantile-on-score selection rule** with the same quantile family. No sub-phase has yet redesigned the selection rule itself. A4 is now the structurally most under-tested axis.

4. **Architecture is also unattacked**, but more expensive to address than the selection rule. A0 attacks H-B9 most directly but at higher cost.

5. **Target adequacy remains an open question** (H-B3 partial). A2 could address it but requires scope amendment + auxiliary baseline.

6. **Feature surface remains R7-A-only**, with R7-C tested (and falsified) as additive features in 27.0f. The Phase 27 conclusion was "regime-statistic features are not sufficient." A3 (regime-as-architecture, not as features) is a different attack but carries Phase 27 R7-C inertia risk.

The cumulative implication: **A4 is the cost-prior-favoured next move**; A0 is the most fundamentally targeted; A2 / A3 are second- or third-priority candidates.

---

## 5. Comparison framework (9-column rubric; inherited from PR #336 §4)

| Column | Meaning |
|---|---|
| 1. Lever | One-line description of what the axis changes |
| 2. Cost | Sub-phases / days |
| 3. Blast radius | low / medium / high |
| 4. Implementation complexity | low / medium / high |
| 5. Scope amendment required | Per Phase 28 kickoff §15 amendment policy |
| 6. Expected information value | high / medium / low + reasoning |
| 7. Phase 27 / 28 inertia risk | low / medium / high |
| 8. Falsifiable H-Cx (placeholder pre-statement) | One-line pre-stated hypothesis; formal pre-stating happens in sub-phase design memo |
| 9. R-T1 / R-B reframing applicability | none / partial / full |

---

## 6. A4 — monetisation-aware selection (primary recommendation)

### 6.1 Definition

Redesign the **selection rule** jointly with the score, instead of applying top-quantile-on-score after the fact. Examples (sub-phase design memo pre-states the specific design):

- **Absolute-threshold** — trade when `score > c` for a learned threshold `c` (rather than top-q quantile)
- **Middle-bulk** — trade quantile 40-60 %, avoiding both tails
- **Per-pair calibrated cutoff** — learn a separate threshold per pair
- **Ranked-cutoff (top-K per bar)** — at each bar, take the K highest-scoring candidates
- **Joint training of score + selection threshold** — threshold becomes a learned parameter
- **Cost-aware ranking** — rank by score-minus-expected-cost rather than score alone
- **Position-conditional selection** — selection decision depends on current portfolio / pair concentration / direction balance

### 6.2 Mechanism — why this attacks H-B7

The 6/6 val-selector-picks-baseline pattern is the most direct evidence that **the selection rule is mis-specified**. Every score-axis intervention (Phase 27 S-C / S-D / S-E + Phase 28 L1 / L2 / L3) has produced a candidate cell whose val Sharpe is below the §10 baseline at the val-selector's chosen q\*. Either (a) every score is wrong (refuted by S-E / L2 / L3 Spearman +0.43-+0.47), or (b) the **rule that turns score into trades** is wrong. A4 attacks the latter.

### 6.3 Falsifiable H-Cx (placeholder pre-statement)

> **H-C2 (placeholder)**: At least one monetisation-aware selection rule (joint score+threshold / cost-aware ranking / position-conditional / absolute-threshold / middle-bulk / per-pair calibration / ranked-cutoff) will lift val Sharpe above the §10 baseline by ≥ +0.05 absolute at a trade count ≥ 20,000, OR else H-C2 is falsified.

Threshold parameters intentionally match PR #336 §5.3 placeholder + PR #334 §11 R-T1 dissent thresholds. Formal pre-statement is in the A4 sub-phase design memo.

### 6.4 Implementation cost

**~1.5 sub-phases (~4-5 days)**. Selection-rule changes touch the cell-construction harness, val-selector, and eval-report writer but **not the regressor training pipeline** (which is already in place from 28.0a-β). A scope amendment may be needed if non-quantile cell shapes are introduced (per kickoff §15.2).

### 6.5 Risk surface

- **Blast radius**: medium — selection-rule changes affect more harness components than a loss change but do not touch production v9 / closed allowlists / §10 baseline.
- **Rollback**: clean per-sub-phase; if Clause 2 amendment is needed, the amendment leaves a permanent surface but does not affect production.
- **前提崩しの可能性**: validation-only selection / test once preserved; ADOPT_CANDIDATE wall / H2 wall / NG#10 / NG#11 preserved. Selection-rule redesign does not threaten any of these gates.

### 6.6 Prior P(GO) — **35-45 %**

Reasoning:

- **Updated upward from PR #336 § 6.6 (25-35 %)** because 28.0a-β strengthened H-B7. The 6/6 val-selector pattern is now the dominant evidence anchor; A4 attacks it directly.
- **Cost-prior ratio remains favorable** vs A0's ~2-3 sub-phases / 25-35 % prior. A4 is the second-mover-most-informative-per-day axis.
- **A4 absorbs the R-T1 reframing** with no additional scope amendment surface (if cell shape remains quantile-based; if not, Clause 2 amendment is required — see §15).
- Prior is below 50 % because Phase 28 has now seen 1 sub-phase reject under the same architecture, and **any single-axis intervention** at this architecture carries a structural-exhaustion prior.

### 6.7 R-T1 / R-B reframing applicability

- **R-T1**: **full** — R-T1's hypothesis (absolute-threshold / middle-bulk / per-pair calibrated cutoff / ranked-cutoff) maps directly onto A4's selection-rule redesign space. A4 is R-T1's natural Phase 28 frame.
- **R-B**: **none** — A4 does not change the feature surface.

### 6.8 Why A4 is the primary recommendation (consolidated reasoning)

1. **Most direct attack on the 6/6 val-selector-picks-baseline pattern** — the load-bearing evidence anchor.
2. **R-T1 reframing absorbed** — Phase 27 carry-forward R-T1 is naturally tested inside A4 without an independent elevation.
3. **Cost-prior ratio best among A0 / A2 / A3 / A4**.
4. **Preserves the existing positive findings** (S-E / L2 / L3 ranking signals) — A4 can use any of these scores as input.
5. **Symmetric information value**: A4 success re-opens the seam (rule was wrong); A4 failure strengthens H-B9 (seam exhausted at this architecture) and raises A0's second-move prior. Either outcome is informative.
6. **Scope amendment requirement is conditional** — if cell shape stays quantile-based (e.g., per-pair-quantile / ranked-cutoff over per-bar top-K), no amendment is needed. Only non-quantile cells (absolute-threshold cells) trigger Clause 2 amendment.

---

## 7. A0 — architecture redesign (dissent 1)

### 7.1 Definition

Replace or augment the model class itself with a structurally different architecture. Examples (sub-phase design memo pre-states the specific architecture):

- **Hierarchical two-stage candidate → confirm**
- **Multi-task heads** (joint TP-prob / SL-prob / TIME-prob / realised-PnL regression)
- **Regime-conditioned heads** (overlap with A3; scoped distinct from feature-level conditioning)
- **Sequence / structural models** (RNN / temporal CNN / Transformer over recent bars)

### 7.2 Mechanism — why this attacks H-B9

H-B9 (seam exhausted at this architecture) is the closure-time hypothesis that A0 attacks most directly. 28.0a-β reinforced H-B9 by adding a 6th data point against same-architecture interventions. If H-B9 is the binding constraint, then no loss / feature / selection redesign within the LightGBM tabular architecture can lift Sharpe; only a structurally different model class can.

### 7.3 Falsifiable H-Cx (placeholder pre-statement)

> **H-C3 (placeholder)**: A structurally different architecture (hierarchical / multi-task / sequence / regime-conditioned) will lift val Sharpe above the §10 baseline by ≥ +0.05 absolute at trade count ≥ 20,000, OR else H-C3 is falsified.

### 7.4 Implementation cost

**~2.0 — 3.0 sub-phases (~6-10 days)**. Highest among A0 / A2 / A3 / A4. Includes new training pipeline, new model serialisation / deserialisation, possibly new compute requirements (e.g., GPU for sequence models). May trigger a scope amendment if the architecture change implies a target reshape (edging into A2 territory).

### 7.5 Risk surface

- **Blast radius**: medium-high — architecture change creates a new model class that does not share weights / hyperparameter conventions with the LightGBM baselines.
- **Rollback**: clean per-sub-phase but with higher engineering surface.
- **前提崩しの可能性**: ADOPT_CANDIDATE wall / H2 wall preserved. Architecture hyperparameter search must respect the 2-layer selection-overfit guard — this must be enforced at sub-phase design memo time.

### 7.6 Prior P(GO) — **25-35 %**

Reasoning:

- **Updated upward from PR #336 §7.6 (15-25 %)** because 28.0a-β reinforced H-B9. A0 is now the most direct attack on the strengthened binding constraint.
- **Cost-prior ratio is unfavorable for the second move** because A4 attacks H-B7 at lower cost; if A4 succeeds, A0 may not be needed. If A4 fails, H-B9 is further reinforced and A0's prior would update higher still — making A0 a stronger third-move candidate than second-move.
- **Implementation risk is highest** among the 4 axes. Architecture changes are engineering-intensive and can fail for technical (rather than scientific) reasons.

### 7.7 R-T1 / R-B reframing applicability

- **R-T1**: **partial** — only if the architecture itself decides selection (e.g., two-stage candidate → confirm where stage 2 *is* the selection rule).
- **R-B**: **partial** — only if the architecture admits a path / microstructure / sequence feature class as part of its definition (e.g., temporal CNN). Scope amendment required.

### 7.8 Why A0 is dissent 1 (not primary)

A0 is the most fundamentally targeted attack on the binding constraint H-B9, but its cost is the highest of the 4 axes. Sequencing matters: **if A4 succeeds, A0's information value decreases**; **if A4 fails, A0's prior rises** and the cost-prior ratio improves. Running A4 first preserves A0 as a stronger downstream move at lower opportunity cost.

This positions A0 as **"the next move if A4 fails."** PR #336 §15.3 had the same A4-first-A0-later reasoning. 28.0a-β did not invalidate that reasoning; it strengthened both priors but preserved the relative ordering.

---

## 8. A2 — target redesign (dissent 2)

### 8.1 Definition

Replace or augment the realised-PnL target with a structurally different target. Examples:

- **Trade-quality target** — continuous target combining path features (MFE / MAE / time-in-trade) rather than terminal barrier PnL
- **Risk-adjusted target** — per-trade Sharpe-like target normalised by realised volatility
- **Cost-decomposed target** — separate gross PnL from spread cost; target each
- **Calibrated-by-regime target** — realised PnL conditioned on regime label

### 8.2 Mechanism — why this attacks H-B3 (partial)

If the realised-PnL target itself is mis-aligned with the monetisation goal (because per-trade noise dominates, or because the target ignores intra-trade path information), then any score that ranks well on it will not necessarily monetize. A2 attacks the target. The 28.0a-β observation that L2 / L3 raised Spearman to +0.46-+0.47 but did not monetize is consistent with this reading (the score is ranking *something*, just not Sharpe-relevant outcomes).

### 8.3 Falsifiable H-Cx (placeholder pre-statement)

> **H-C4 (placeholder)**: A redesigned target (trade-quality / risk-adjusted / cost-decomposed / calibrated-by-regime) will produce a ranking that, applied at val-selection, lifts realised-PnL Sharpe above the §10 baseline by ≥ +0.05 absolute at trade count ≥ 20,000, OR else H-C4 is falsified.

### 8.4 Implementation cost

**~2.0 sub-phases (~5-7 days)**. Target rebuild on the existing dataset (or a new `path_quality_dataset.parquet` variant), new sub-phase eval harness, and auxiliary baseline construction (since §10 is defined against realised-PnL).

### 8.5 Risk surface

- **Blast radius**: medium — target change touches the dataset layer and creates semantic incompatibility with the §10 baseline.
- **Always requires scope amendment** per kickoff §15.2 (target spec change is a closed surface).
- **§10 baseline misalignment**: A2 sub-phases must declare an auxiliary baseline alongside §10; §10 numeric remains unchanged but the comparison becomes mixed.

### 8.6 Prior P(GO) — **15-25 %**

Reasoning:

- **Slightly upward from PR #336 §8.6 (10-20 %)** because 28.0a-β's "Spearman rises but Sharpe falls" pattern is one piece of evidence that **the target may not be measuring what the score should optimise**.
- **Still below A0** because A2 requires scope amendment and creates §10 baseline misalignment; the implementation surface is heavier.
- **Better as third or fourth move** after A4 and A0 results are in — both A4 success and A0 success would reduce A2's urgency; both A4 failure and A0 failure would dramatically increase A2's prior.

### 8.7 R-T1 / R-B reframing applicability

- **R-T1**: **none**.
- **R-B**: **partial** — only if the redesigned target incorporates path / microstructure information as part of its construction.

---

## 9. A3 — regime-conditioned modeling (Tier 3; not a dissent)

### 9.1 Definition

Decompose the model along a regime axis in a structural way (not as additive features as in 27.0f R7-C). Examples:

- **Gating network** — learned gate decides which sub-model handles a given bar
- **Mixture-of-experts** — multiple specialised models, weighted per bar by regime
- **Per-regime training** — fit separate models per regime cell (e.g., spread tertile × volume tertile) and combine

### 9.2 Mechanism

H-B8 (path / microstructure / multi-TF feature class needed, not regime-statistic) is the closure-time hypothesis A3 attacks. Where R7-C used regime *features*, A3 uses regime as an *architectural decomposition*.

### 9.3 Falsifiable H-Cx (placeholder pre-statement)

> **H-C5 (placeholder)**: A regime-conditioned model (gating / MoE / per-regime training) will lift val Sharpe above the §10 baseline by ≥ +0.05 absolute at trade count ≥ 20,000, OR else H-C5 is falsified.

### 9.4 Implementation cost

**~2.0 — 2.5 sub-phases (~5-8 days)**. New training pipeline; gating network or per-regime cells; scope amendment required if R-B reframing admits a new feature class.

### 9.5 Risk surface

- **Blast radius**: medium.
- **Phase 27 R7-C inertia risk**: **medium-high** (§11.4) — must be distinguished from R7-C in scoping. 28.0a-β L3 spread-cost-weighted Huber was a "regime information enters via training-time weight, not as feature" attack and failed; the architectural-conditioning version is structurally different but the underlying regime-axis prior is still affected.
- **Always requires scope amendment** if R-B reframing introduces a new closed allowlist (path / microstructure / multi-TF features).

### 9.6 Prior P(GO) — **10-20 %**

Reasoning:

- **Unchanged from PR #336 §9.6 (10-20 %)**. 28.0a-β L3 result (γ-weighted spread cost) is informative for A3: the regime-aware information enters the model via the loss but does not lift Sharpe. This is **negative evidence** for regime-conditioned attacks in general (whether the conditioning is at the feature level, loss level, or architecture level).
- A3 remains in Tier 3 (not a dissent) because the negative evidence is not conclusive — architectural conditioning is structurally different from feature- or loss-level conditioning, but the prior is now penalised by 28.0a-β's L3 negative result.

### 9.7 R-T1 / R-B reframing applicability

- **R-T1**: **none**.
- **R-B**: **full** — A3 is the natural Phase 28 home for R-B. Requires scope amendment.

---

## 10. 4-axis cross-comparison matrix

| Axis | Lever | Cost (sub-phases) | Blast radius | Impl complexity | Scope amendment | Info value | Phase 27 / 28 inertia risk | Prior P(GO) | R-T1 reframe | R-B reframe | Tier |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A4** | monetisation-aware selection | 1.5 | medium | medium | maybe (non-quantile cells) | medium-high | medium (R-T2 trim collapse) | **35-45 %** | **full** | none | **Tier 1 (primary)** |
| **A0** | architecture redesign | 2.0 — 3.0 | medium-high | high | maybe (if implies target reshape) | high | low | 25-35 % | partial | partial | Tier 2 (dissent 1) |
| **A2** | target redesign | 2.0 | medium | medium-high | **always** | high | low | 15-25 % | none | partial | Tier 2 (dissent 2) |
| **A3** | regime-conditioned modeling | 2.0 — 2.5 | medium | medium-high | maybe (if new feature class) | medium | medium-high (R7-C collapse) | 10-20 % | none | **full** | Tier 3 |

**Reading the matrix**: A4 wins on cost-prior. A0 has highest information value but highest cost; positioned as "A4 が失敗した場合の next move" (§14.2). A2 / A3 carry heavier scope-amendment + inertia-risk surfaces and are better suited as third / fourth movers.

---

## 11. Risk of Phase 27 / 28 inertia per axis (updated)

The Phase 28 kickoff (PR #335 §3) listed five Phase 27 inertia routes that are NOT admissible. 28.0a-β adds A1 single-loss-variant micro-redesign to the inertia-risk vocabulary. This section evaluates each axis's risk of collapsing into one of these inertia routes during scoping.

### 11.1 A4 — monetisation-aware selection — inertia risk **medium**

Specific collapse risks:

- **R-T2 quantile-trim collapse**: if "selection rule redesign" is essentially "try a different q grid", that is Phase 27 inertia (kickoff §3 item 2). The A4 sub-phase design memo must declare which structurally distinct rule class is tested (absolute-threshold / middle-bulk / per-pair / ranked-cutoff / joint training / cost-aware ranking / position-conditional).
- **Score-only-sweep collapse**: if "monetisation-aware selection" is applied over the same C-sb-baseline cell without changing the rule structurally, that is Phase 27 inertia (kickoff §3 item 4).

Mitigation: A4 sub-phase design memo MUST pre-state which rule class is tested and confirm it is structurally distinct from R-T2 trim.

### 11.2 A0 — architecture redesign — inertia risk **low**

A0 changes the model class itself, which by definition diverges from any Phase 27 / 28 inertia route. The only inertia danger is if the "new" architecture is essentially the old one with hyperparameter retuning; the sub-phase design memo must disallow this.

### 11.3 A2 — target redesign — inertia risk **low**

A2 always requires a target spec change, which by definition exits the realised-PnL frame used by Phase 27 / 28.0a-β. Only very minor target tweaks (e.g., K_FAV 1.5 → 1.4) would risk inertia; the sub-phase design memo must declare a structural target change.

### 11.4 A3 — regime-conditioned modeling — inertia risk **medium-high**

A3 risks collapsing into:

- **27.0f R7-C feature widening**: if regime information enters as additive features rather than as architectural decomposition, that is Phase 27 inertia (kickoff §3 item 3).
- **28.0a L3 spread-cost-weighted Huber**: if regime information enters as a per-row training weight, that is 28.0a-β inertia (A1 closed allowlist already tested L3).

The Phase 28 distinction is **architectural conditioning** (gating / MoE / per-regime cells) versus **feature-level or loss-level conditioning** (R7-C / L3). The sub-phase design memo MUST declare which side of that line it is on.

### 11.5 A1 micro-redesign — NOT admissible without scope amendment

Per §3.4: A1 single-variant micro-redesign within the 28.0a-β closed 3-loss allowlist is NOT admissible. New A1-class loss families (non-Huber backbone, additional variants beyond 3) require a scope amendment PR.

---

## 12. How each axis uses Phase 27 + 28.0a findings (6-eval picture × axis relevance)

| Axis | Phase 27 + 28.0a findings directly attacked | Phase 27 + 28.0a findings preserved | Notes |
|---|---|---|---|
| **A4** | H-B7 (val-selection misspecified; **strongest evidence**: 6/6 val-selector pattern) + 28.0a L2 / L3 Spearman gains unmonetized | 27.0d / 27.0e / 27.0f / 28.0a S-E + L2 + L3 ranking signals (used as input to redesigned selection rule) | Most incremental use of findings; preserves all positive results, attacks the residual unattacked surface. |
| **A0** | H-B9 (seam exhausted at this architecture; **strengthened by 28.0a-β**) | All 6 findings as historical evidence | Most ambitious use of findings; architecture change can in principle recover the seam. |
| **A2** | H-B3 partial + open question (target adequacy) + 28.0a "Spearman rises, Sharpe falls" pattern | 27.0d / 27.0e / 27.0f / 28.0a ranking signals *if* the new target is comparable | Often produces a new dataset surface; §10 baseline becomes semantically tricky. |
| **A3** | H-B8 (regime-conditioned ≠ regime-statistic features) | R7-A baseline | R-B-reframing-friendly axis; admits new feature class via scope amendment. **Partially penalised by 28.0a-β L3 negative result.** |

---

## 13. R-T1 / R-B / R-T3 reframing eligibility table

| Axis | R-T1 reframing | R-B reframing | Notes |
|---|---|---|---|
| **A4** monetisation-aware selection | **full** | none | The natural Phase 28 home for R-T1. Scope amendment maybe (non-quantile cells). |
| A0 architecture redesign | partial | partial | If the architecture decides selection or admits a new feature class. |
| A2 target redesign | none | partial | If the new target incorporates path / microstructure information. |
| **A3** regime-conditioned modeling | none | **full** | The natural Phase 28 home for R-B. Scope amendment required. |
| R-T3 (concentration formalisation) | n/a | n/a | Not reframed under any A-axis; below-threshold per PR #334 §12. Future revival requires Clause 2 amendment. |

**This PR does not elevate R-T1 or R-B.** It records that **if** the user later decides to elevate, A4 (R-T1) and A3 (R-B) are the canonical Phase 28 frames; A0 / A2 admit partial reframing.

---

## 14. Recommended second mover + 2 dissents

### 14.1 Primary — **A4 monetisation-aware selection**

A4 is recommended as Phase 28's second mover for **eight** reasons:

1. **Most direct attack on the strongest evidence anchor** — the 6/6 val-selector-picks-baseline pattern is the single most informative observation in the Phase 27 + 28.0a inheritance chain.
2. **R-T1 reframing absorbed without independent elevation** — A4 naturally tests the deferred R-T1 dissent inside Phase 28's frame.
3. **Lowest cost among A0 / A2 / A3 / A4**.
4. **Preserves all positive findings** — A4 can use any of S-E / L1 / L2 / L3 as input score (val-selected score is whichever variant val-selects best on the redesigned rule).
5. **No scope amendment required** if cell shape stays quantile-based (per-pair quantile / ranked-cutoff over per-bar top-K).
6. **Symmetric information value** — A4 success re-opens the seam; A4 failure strengthens H-B9 and raises A0's third-move prior.
7. **Lowest blast radius** among the 4 axes (medium; no production / closed allowlist / §10 baseline touched).
8. **Direct response to 28.0a-β's load-bearing observation** — L2 / L3 raised Spearman to +0.466 / +0.459 but did not monetize. The score is ranking *something*, just not Sharpe-relevant outcomes under the current selection rule.

The A4 sub-phase design memo (out of scope here) will pre-state the specific rule class, the FAIL-FAST baseline reproduction gate, the cell structure (control + candidate cells), and H-C2.

### 14.2 Dissent 1 — **A0 architecture redesign** ("A4 が失敗した場合の next move")

A0 is preserved as dissent 1, positioned explicitly as **the next move if A4 fails**. Reasoning:

- A0 attacks H-B9 most directly, and 28.0a-β reinforced H-B9.
- However, A0's cost is highest (~2-3 sub-phases) and engineering surface is largest.
- Sequencing logic: if A4 fails, H-B7 is also falsified, and the combined H-B7 / H-B9 strengthening would update A0's prior from 25-35 % to ~35-45 %, making A0 the next-best move at improved cost-prior.
- If A4 succeeds, A0's information value drops sharply (architecture change becomes unnecessary at the current target / feature surface).

A0 can be elevated to primary at the user's discretion (decision rule §16 row 2) if the user reads H-B9 as the binding constraint immediately rather than after testing A4.

### 14.3 Dissent 2 — **A2 target redesign**

A2 is preserved as dissent 2. The strongest argument for A2 is the 28.0a "Spearman rises, Sharpe falls" pattern: the target may not be measuring what the score should optimise. However:

- A2 always requires scope amendment + auxiliary baseline construction (heavier than A4 or A0 setup).
- A2's prior P(GO) (15-25 %) is below A0's (25-35 %) because 28.0a-β's reinforcement of H-B9 is more direct evidence than its bearing on target adequacy.
- A2 is better positioned as a third or fourth mover, after A4 and possibly A0 results refine the prior.

A2 can be elevated to primary at the user's discretion (decision rule §16 row 3) if the user authorises target spec scope amendment immediately.

### 14.4 Why A3 is NOT a dissent

A3 has the highest Phase 27 / 28 inertia risk (medium-high; §11.4) — it must be distinguished from both 27.0f R7-C feature widening AND 28.0a-β L3 spread-cost-weighted loss. As the second Phase 28 sub-phase, A3 has the highest scoping-failure cost.

A3 also requires a scope amendment for R-B reframing. While natural as R-B's Phase 28 home (§13), it is heavier to set up than A4 / A0 and the 28.0a-β L3 negative result partially penalises the regime-axis prior.

A3 stays Tier 3, deferred-not-foreclosed; revival by elevation possible (§16 row 4) but requires explicit user routing decision and likely scope amendment.

---

## 15. Why A4 over A0 (more nuanced; post-28.0a updated reasoning)

PR #336 §15.3 reasoned that A4 was the right primary because (a) A4 still requires a useful score and (b) A4's information value is symmetric. 28.0a-β reinforces both arguments:

- **A useful score exists**: S-E (+0.438) / L2 (+0.466) / L3 (+0.459) all produce strong ranking signals. The score-half of monetisation is solved. A4 can pick any of these scores as input.
- **The 6/6 val-selector pattern is now the strongest evidence anchor in the inheritance chain**. A4 attacks it directly.
- **A0's prior rose**, but A0's cost remains highest. The relative ordering A4 > A0 is preserved by 28.0a-β.
- **A4-first, A0-later sequencing** preserves A0's information value: if A4 fails, H-B7 is falsified, H-B9 is further strengthened, and A0 becomes a stronger second-move candidate at improved prior.

The user may override this judgement and elevate A0 to primary at any point; decision rule §16 row 2 records the condition.

---

## 16. Decision rule — pre-stated thresholds (updated)

Pre-state the conditions under which each axis is elevated to primary:

| Condition | Selected axis as second mover |
|---|---|
| 6/6 val-selector-picks-baseline pattern interpreted as "rule misspecified" AND A4 cost-prior is best AND R-T1 reframing is acceptable inside Phase 28 → | **A4 (default primary)** |
| User reads 28.0a-β's reinforced H-B9 as "architecture is the binding constraint" AND user accepts highest cost AND wants the most direct attack on seam exhaustion immediately → | **A0 (overrides A4)** |
| User elevates target redesign with prior > 25 % AND authorises target-spec scope amendment AND accepts §10 baseline misalignment → | **A2 (overrides A4)** |
| User explicitly elevates regime-conditioned modeling with prior > 20 % AND authorises closed-allowlist scope amendment for R-B reframing AND accepts medium-high inertia risk (must be distinguished from 27.0f R7-C and 28.0a L3) → | **A3 (overrides A4)** |
| User authorises Clause 2 amendment AND R-T3 prior revised above 20 % → | **R-T3 (carry-forward; below-threshold per current evidence)** |

The default condition (6/6 val-selector pattern → A4) is consistent with the recommendation in §14.1. The four override conditions correspond to four different user readings of the 6-eval evidence picture, each pre-stated so the routing choice is auditable.

---

## 17. Open questions / unknowns

Five open questions carried into Phase 28 second-mover decision and not resolved by this routing review:

1. **What specific rule class for A4?** Absolute-threshold / middle-bulk / per-pair calibrated cutoff / ranked-cutoff / joint training of score+threshold / cost-aware ranking / position-conditional selection — multiple options admissible. The A4 sub-phase design memo pre-states which.
2. **Should A4 be framed as a pure A4 sub-phase or as an explicit R-T1 elevation under A4?** PR #336 §13 and this PR §13 both record R-T1 reframing applicability as **full**. The A4 sub-phase design memo must declare whether it self-identifies as "A4 sub-phase" or "R-T1 elevation in A4 frame." Naming has implications for the inheritance chain's hypothesis ID (H-C2 vs H-C2-from-R-T1).
3. **If A0 is elevated, sequence-class architecture compute / 730d split compatibility**. Some A0 architectures (RNN / temporal CNN / Transformer) require different windowing or compute resources. The A0 sub-phase design memo must pre-state this.
4. **If A2 is elevated, auxiliary baseline construction**. §10 baseline numeric remains immutable, but A2 sub-phases need an auxiliary baseline aligned with the new target. The A2 sub-phase design memo must pre-state how this is constructed.
5. **R-T3 revival condition**. Current status: below-threshold; deferred. 28.0a-β does not change R-T3's prior (5-15 %). Revival is conditioned on cumulative Phase 28 results: if A4 / A0 / A2 all fail, R-T3 could become next-most-attractive among carry-forward routes; not a Phase 28 second-mover question.

---

## 18. Binding constraints (verbatim)

This routing review preserves every constraint binding at the end of Phase 28.0a:

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
- §10 baseline immutable (no numeric change in this PR)
- no implementation
- no eval
- no production change
- no MEMORY.md change inside this PR
- no `src/` / `scripts/` / `tests/` / `artifacts/` / `.gitignore` changes
- no Phase 28 sub-phase design memo
- no scope amendment
- no R-T1 / R-B / R-T3 elevation
- no A4 / A0 / A2 / A3 sub-phase initiation
- no prior verdict modification
- no auto-route after merge

The recommendation is **scope-level only**. The next action requires an explicit separate user routing decision.

---

## 19. References

**Phase 28**:
- PR #335 — Phase 28 kickoff (`docs/design/phase28_kickoff.md`)
- PR #336 — Phase 28 first-mover routing review (`docs/design/phase28_first_mover_routing_review.md`; A1 primary at first-mover; A4 / A0 dissents)
- PR #337 — Phase 28.0a-α A1 objective redesign design memo
- PR #338 — Phase 28.0a-β A1 objective redesign eval (sources H-C1 outcomes + 28.0a row of 6-eval picture)

**Phase 27 (evidence anchor)**:
- PR #316 — Phase 27 kickoff
- PR #318 / #321 / #325 / #328 / #332 — five Phase 27 β-evals
- PR #319 / #322 / #326 / #329 / #333 — five Phase 27 routing reviews
- PR #334 — Phase 27 closure memo (5-eval evidence picture source; H-B7 / H-B8 / H-B9 carry-forward; §10 baseline source)

**Binding contracts**:
- PR #279 — γ closure
- Phase 22 frozen-OOS contract
- X-v2 OOS gating
- Phase 9.12 production v9 closure tip `79ed1e8` (production v9 20-pair, untouched throughout Phase 27 and Phase 28)

---

*End of `docs/design/phase28_post_28_0a_routing_review.md`.*
