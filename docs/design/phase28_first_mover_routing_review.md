# Phase 28 — First-Mover Routing Review

**Type**: doc-only routing review
**Status**: compares Phase 28 admissible axes A0 — A4; recommends a first-mover with two dissents; does **NOT** authorise any sub-phase initiation
**Branch**: `research/phase28-first-mover-routing-review`
**Base**: master @ `a05469b` (post-PR #335 / Phase 28 kickoff merge)
**Pattern**: analogous to PR #319 / #322 / #326 / #329 / #333 routing reviews under Phase 27
**Date**: 2026-05-16

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Phase 28 first-mover routing review**. It records the **comparison + recommendation** across the five admissible axes (A0 — A4 per Phase 28 kickoff PR #335 §5), nominates a **primary** first-mover and **two dissents**, and pre-states a decision rule under which the user can elevate either dissent. It does **NOT**:*
>
> - *authorise any A0 — A4 sub-phase initiation,*
> - *create any Phase 28 sub-phase design memo,*
> - *open any scope amendment,*
> - *elevate R-T1 / R-B / R-T3 (all carry-forward routes remain in their PR #334 status),*
> - *modify the §10 baseline,*
> - *change any prior verdict.*
>
> *The recommendation is **scope-level only**. Executing it — i.e., initiating the first Phase 28 sub-phase — requires a **separate later user routing decision**, after which a sub-phase design memo PR will be drafted. R-T1 / R-B / R-T3 reframing also requires a separate routing decision.*

Same approval-then-defer pattern as PR #319 / #322 / #326 / #329 / #333.

---

## 1. Executive summary

**Primary recommendation**: **A1 objective redesign** (first-mover for Phase 28).
**Dissent 1**: **A4 monetisation-aware selection**.
**Dissent 2**: **A0 architecture redesign**.

| Bucket | Axis | Prior P(GO) | One-line rationale |
|---|---|---|---|
| **Tier 1 (primary)** | **A1** objective redesign | **35-45 %** | Preserves the 27.0d S-E ranking signal (Spearman +0.438) while attacking the Sharpe gap at training time via the loss; no scope amendment; lowest cost. |
| Tier 2 (dissent 1) | **A4** monetisation-aware selection | 25-35 % | Directly attacks H-B7 (val-selection misspecification); R-T1 reframing applicable; moderate cost. |
| Tier 2 (dissent 2) | **A0** architecture redesign | 15-25 % | Directly attacks H-B9 (seam exhaustion at this architecture); highest information value but highest cost. |
| Tier 3 (below-primary; deferred candidates) | **A2** target redesign | 10-20 % | Always requires scope amendment; risks §10 baseline misalignment; high implementation cost. |
| Tier 3 (below-primary; deferred candidates) | **A3** regime-conditioned modeling | 10-20 % | Natural home for R-B reframing under a new closed allowlist; scope amendment required; better as Phase 28 second mover after A1's result is in. |

This PR does not foreclose A2 or A3; they remain admissible at kickoff (PR #335 §7) but are not nominated as Tier 1 or Tier 2 for the first move. R-T1 / R-B remain deferred-not-foreclosed in their PR #334 carry-forward status; R-T3 remains below-threshold; none is elevated by this PR.

---

## 2. Routing review semantics — what this PR does and does NOT do

Phase 28 is in an unusual position relative to prior phases: the kickoff (PR #335) was merged 0 sub-phases ago, so the conventional routing-review-after-sub-phase-β-eval pattern (used at PR #319 / #322 / #326 / #329 / #333) does not directly apply. Instead this PR serves as a **post-kickoff initial routing decision** — i.e., a comparison of admissible-at-kickoff axes to suggest where to spend the first sub-phase budget.

**This PR does**:

1. Compare the five admissible axes A0 — A4 along the 9-column rubric in §4.
2. Recommend a primary first-mover (A1) and two dissents (A4, A0).
3. Pre-state the decision rule under which the user can elevate either dissent to primary (§16).
4. Record R-T1 / R-B reframing **applicability** per axis (§13) without electing to use it.
5. Evaluate Phase 27 inertia risk per axis (§11).

**This PR does NOT**:

1. Initiate any sub-phase (no β-eval, no design memo).
2. Author any falsifiable H-Cx that would belong in a sub-phase design memo. The H-Cx column in §4 is a *placeholder pre-statement* at scope level; the formal pre-stating happens in the sub-phase design memo PR after a routing decision.
3. Elevate R-T1 / R-B / R-T3.
4. Modify the §10 baseline numeric or any prior verdict.
5. Touch src / scripts / tests / artifacts / .gitignore / MEMORY.md.
6. Trigger auto-routing.

---

## 3. Phase 28 evidence anchors (post-kickoff snapshot)

Phase 28's first-mover routing review draws its evidence from two artifacts that are stable as of master `a05469b`:

### 3.1 Phase 27 5-eval evidence picture (from PR #334 §4.1)

| sub-phase | Channel | Intervention | val-selected cell | H-Bx outcome | Verdict |
|---|---|---|---|---|---|
| 27.0b-β | B | S-C TIME penalty α grid | C-alpha0 (S-B) | — | REJECT |
| 27.0c-β | B | S-D calibrated EV | C-sb-baseline (S-B) | — | REJECT |
| 27.0d-β | B | S-E regression on realised PnL | C-sb-baseline (S-B) | — | REJECT (split) |
| 27.0e-β | C | R-T2 quantile-family trim | C-sb-baseline (S-B) | H-B5 PARTIAL_SUPPORT (row 2) | REJECT (split) |
| 27.0f-β | A | R7-C regime/context features | C-sb-baseline (S-B) | H-B6 FALSIFIED_R7C_INSUFFICIENT (row 3) | REJECT (split) |

Val-selector picked C-sb-baseline in 5/5 sub-phases. 27.0d C-se cell unlocked Spearman +0.438 (real H1m PASS) but Sharpe -0.483 (FAIL) — the discrimination ≠ monetisation gap. This is the load-bearing observation for §5 (A1 attacks the gap at training time) and §9 (A4 attacks it at selection time).

### 3.2 §10 baseline (immutable; verbatim from PR #335 §10)

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

The §10 baseline is the **immutable reference** for every Phase 28 sub-phase eval. Each sub-phase eval will embed the FAIL-FAST baseline reproduction check inherited from 27.0c-α §7.3.

### 3.3 Carry-forward hypotheses (from PR #334 §9)

- **H-B7** — val-selection rule misspecified → motivates A4
- **H-B8** — path / microstructure / multi-TF feature class needed → motivates A3 / A0 / A2
- **H-B9** — selection→monetisation seam exhausted at this architecture → motivates A0

All three carry into Phase 28 as **UNRESOLVED**. This routing review does not test any of them; sub-phase β-evals will.

### 3.4 Carry-forward register status

- **R-T1** (selection-rule redesign) — deferred-not-foreclosed; prior 25-35 %; reframing under A4 admissible (§13)
- **R-B** (different feature axis) — deferred-not-foreclosed; prior 15-25 %; reframing under A3 / A0 / A2 admissible + scope amendment required (§13)
- **R-T3** (concentration formalisation) — below-threshold; deferred; NOT a dissent; not reframed by this PR

---

## 4. Comparison framework (9-column rubric)

Each axis is evaluated along the columns below. The rubric is applied in §5 — §9 per-axis and summarised in §10 cross-comparison.

| Column | Meaning | Source |
|---|---|---|
| 1. Lever | One-line description of what the axis changes | Phase 28 kickoff §5 |
| 2. Cost | Sub-phases / days (single sub-phase ≈ 3-5 days) | Estimated honestly per axis |
| 3. Blast radius | low / medium / high (production / shared-state exposure) | This PR (always low for doc-only kickoff routing review; high for production) |
| 4. Implementation complexity | low / medium / high | Honest estimate per axis |
| 5. Scope amendment required | Per Phase 28 kickoff §15 amendment policy | This PR's interpretation, deferring to per-sub-phase confirmation |
| 6. Expected information value | high / medium / low + reasoning | Phase 27 findings + closure-time hypotheses |
| 7. Phase 27 inertia risk | low / medium / high + which inertia route the axis could collapse into | §11 |
| 8. Falsifiable H-Cx (placeholder pre-statement) | One-line pre-stated hypothesis; formal pre-stating happens in sub-phase design memo | Sketch only |
| 9. R-T1 / R-B reframing applicability | none / partial / full | §13 |

Column 9 is **applicability** only — declaring that R-T1 or R-B *could* be reframed under that axis. The actual elevation requires a separate routing decision.

---

## 5. A1 — objective redesign (primary recommendation)

### 5.1 Definition

Redefine the **loss function** used to train the model, holding the architecture (LightGBM tabular regressor / classifier on R7-A features), the target (triple-barrier realised PnL), and the feature surface (R7-A only as baseline; R7-C as 27.0f's tested but inert addition) approximately fixed. Examples (the sub-phase design memo pre-states the specific loss):

- **Realised-PnL re-weighted loss** — weight per-row loss by realised-PnL magnitude (absolute) or by absolute spread cost; emphasise expensive rows during training.
- **Asymmetric loss** — penalise false-positives in expensive regimes (top-tail rows with wide spread) more heavily than false-negatives in cheap regimes.
- **Cost-aware loss** — incorporate spread cost or realised slippage directly into the per-row training signal.

### 5.2 Mechanism — why this might solve the residual gap

The 27.0d S-E result showed that the regressor *can* rank-order rows by realised PnL with Spearman +0.438. The same result showed that the top-quantile selection on those rankings produces Sharpe -0.483 (and 27.0e R-T2 trim made it worse, -0.767 at q=10). The interpretation in PR #334 §6 was that the top tail is **monotonically adversarial**: most-confident rows are most expensive.

A1 attacks that gap at **training time**: if the training loss already penalises mis-prediction in the expensive regime more heavily, the regressor's confidence top-tail should align differently with realised PnL. The ranking signal is preserved; the *meaning* of the ranking changes.

### 5.3 Falsifiable H-Cx (placeholder pre-statement)

> **H-C1 (placeholder)**: At least one re-weighted / asymmetric / cost-aware loss formulation will lift the C-se cell's val Sharpe above the §10 baseline by ≥ +0.05 absolute at q ∈ {5, 10} while preserving cell Spearman ≥ +0.30, OR else H-C1 is falsified.

The formal pre-statement (with exact loss class, exact tolerance thresholds, baseline reproduction gate, and FAIL-FAST conditions) happens in the A1 sub-phase design memo.

### 5.4 Implementation cost

- **~1.0 — 1.5 sub-phases (~3-5 days)**.
- Re-uses the 27.0d-β / 27.0e-β / 27.0f-β harness: same `path_quality_dataset.parquet`, same 20-pair / 730d / 70-15-15 split, same 5-fold OOF, same realised-PnL precompute.
- The only new code is the loss function (LightGBM custom objective or a wrapper if needed). ~50-150 lines.
- Inherits the C-sb-baseline reproduction FAIL-FAST gate from 27.0c-α §7.3 unchanged.
- No new feature surface (R7-A as inherited; R7-C remains available for diagnostic comparison).

### 5.5 Risk surface

- **Blast radius**: low — loss change does not touch production v9, scope binding (R7-A / R7-C closed allowlists), or §10 baseline.
- **Rollback**: trivial — sub-phase isolated under `scripts/stage28_0?_*.py` and `artifacts/stage28_0?/`.
- **前提崩しの可能性**: none in the binding-constraint dimension. ADOPT_CANDIDATE wall / H2 wall / NG#10 / NG#11 / γ closure PR #279 / Phase 22 frozen-OOS / X-v2 OOS gating all unaffected.

### 5.6 Prior P(GO)

**35-45 %.**

Reasoning:

- 27.0d S-E unlocked a real H1m signal (Spearman +0.438). That signal is not lost; A1 keeps using it.
- The gap that A1 addresses (training-time treatment of the expensive regime) is structurally different from R-T2 (selection-time trim) and R7-C (feature-side regime widening), neither of which lifted Sharpe. A1 is a third orthogonal attack on the *same* gap.
- The prior is above A4's 25-35 % because A1 preserves the score signal that S-E unlocked, whereas A4 redesigns the selection rule on top of *some* score (which still needs to be a useful score). A1 is the more incremental, lower-risk first move.
- The prior is below 50 % because the 5-eval picture's val-selector-picks-baseline pattern is strong evidence that **no** simple per-axis intervention closes the gap; a loss change is still a per-axis intervention.

### 5.7 R-T1 / R-B reframing applicability

- **R-T1**: **none**. A1 does not change the selection rule.
- **R-B**: **none**. A1 does not change the feature surface.

### 5.8 Why A1 is the primary recommendation (consolidated reasoning)

1. **Preserves the only positive Phase 27 finding** (S-E ranking signal).
2. **Lowest implementation cost** among A0 — A4.
3. **No scope amendment required** under Phase 28 kickoff §15.
4. **Lowest blast radius** (production / closed allowlists untouched).
5. **Direct response to H-B3 partial** (Spearman PASS / Sharpe FAIL) — the residual gap is attacked exactly where the gap exists.
6. **Information value**: if A1 succeeds, the selection→monetisation seam re-opens at this architecture (H-B9 partially falsified); if A1 fails, H-B9 is reinforced and A0 / A4 become more attractive on the strength of A1's negative result.

---

## 6. A4 — monetisation-aware selection (dissent 1)

### 6.1 Definition

Redesign the **selection rule** jointly with the score, instead of applying top-quantile-on-score after the fact. Examples (sub-phase design memo pre-states the specific design):

- **Joint training of score + selection threshold** — the threshold becomes a learned parameter.
- **Cost-aware ranking** — rank by score-minus-expected-cost rather than score alone.
- **Position-conditional selection** — selection decision depends on current portfolio / pair concentration / direction balance.

### 6.2 Mechanism

H-B7 (val-selection rule misspecified) is the closure-time hypothesis that A4 attacks most directly. The 5-eval picture's val-selector-picks-baseline-in-5/5 pattern is consistent with the rule, not the score, being the issue. A4 replaces or augments the rule.

### 6.3 Falsifiable H-Cx (placeholder pre-statement)

> **H-C2 (placeholder)**: At least one monetisation-aware selection rule (joint score+threshold / cost-aware ranking / position-conditional) will lift val Sharpe above the §10 baseline by ≥ +0.05 absolute at a trade count ≥ 20,000, OR else H-C2 is falsified.

Same falsification threshold as R-T1's H-C2 in PR #334 §11; this is intentional — A4 is the natural home for R-T1 reframing (§13).

### 6.4 Implementation cost

**~1.5 — 2.0 sub-phases (~4-6 days)**. Higher than A1 because selection-rule changes touch the cell-construction harness, the val-selector, and potentially the eval-report writer. A scope amendment may be needed if non-quantile cell shapes are introduced (per kickoff §15.2).

### 6.5 Risk surface

- **Blast radius**: medium — selection-rule changes affect more harness components than a loss change.
- **Rollback**: clean per-sub-phase, but if a Clause 2 amendment is needed, the amendment leaves a permanent surface.
- **前提崩しの可能性**: validation-only selection / test once preserved; ADOPT_CANDIDATE wall / H2 wall not threatened.

### 6.6 Prior P(GO)

**25-35 %.**

Reasoning:

- A4 directly attacks H-B7, the closure-time hypothesis most consistent with the 5-eval val-selector pattern. This is structural attack power.
- However, A4 still depends on having a useful score: if the score itself remains poorly aligned with monetisation, even a smart selection rule may not surface a candidate beating the §10 baseline. A1 is the more incremental first move; A4 is the second move that operates on top of an A1 result (whether positive or negative).
- Prior matches R-T1's PR #334 §10 prior (25-35 %) because A4 *is* the Phase 28 reframing of R-T1.

### 6.7 R-T1 / R-B reframing applicability

- **R-T1**: **full**. R-T1's dissent hypothesis (absolute-threshold / middle-bulk / per-pair calibrated cutoff / ranked-cutoff) maps onto A4's selection-rule redesign space. A4 is R-T1's natural Phase 28 frame.
- **R-B**: **none**. A4 does not change the feature surface.

---

## 7. A0 — architecture redesign (dissent 2)

### 7.1 Definition

Replace or augment the model class itself with a structurally different architecture. Examples (sub-phase design memo pre-states the specific architecture):

- **Hierarchical two-stage candidate → confirm** — stage 1 generates candidates; stage 2 confirms / rejects with a different model or feature subset.
- **Multi-task heads** — joint loss over TP-prob / SL-prob / TIME-prob / realised-PnL regression, with shared backbone.
- **Regime-conditioned heads** (overlap with A3; the architectural-vs-conditional split is a sub-phase scoping decision).
- **Sequence / structural models** — RNN / temporal CNN over recent bars rather than per-bar tabular features.

### 7.2 Mechanism

H-B9 (seam exhausted at this architecture) is the closure-time hypothesis that A0 attacks most directly. If H-B9 is the binding constraint, then no amount of loss / selection / feature redesign within the LightGBM tabular architecture can lift Sharpe; only a structurally different model class can. A0 is the most surgical test of H-B9.

### 7.3 Falsifiable H-Cx (placeholder pre-statement)

> **H-C3 (placeholder)**: A structurally different architecture (hierarchical / multi-task / sequence) will lift val Sharpe above the §10 baseline by ≥ +0.05 absolute at trade count ≥ 20,000 on the same target and feature surface, OR else H-C3 is falsified.

The architecture class is pre-stated in the A0 sub-phase design memo.

### 7.4 Implementation cost

**~2.0 — 3.0 sub-phases (~6-10 days)**. Highest among A0 — A4. Includes new training pipeline, new model serialisation / deserialisation, possibly new compute requirements (e.g., GPU for sequence models). May trigger a scope amendment if the architecture change implies a target reshape (e.g., sequence models often require sequence targets, edging into A2 territory).

### 7.5 Risk surface

- **Blast radius**: medium-high — architecture change creates a new model class that does not share weights / hyperparameter conventions with the LightGBM baselines used in Phase 26 / 27.
- **Rollback**: clean per-sub-phase but with higher engineering surface.
- **前提崩しの可能性**: ADOPT_CANDIDATE wall / H2 wall preserved; the only relaxation risk is if the architecture's hyperparameter search inadvertently relaxes the 2-layer selection-overfit guard — this must be enforced at sub-phase design memo time.

### 7.6 Prior P(GO)

**15-25 %.**

Reasoning:

- A0 is the most direct attack on H-B9, which the 5-eval picture supports as a likely binding constraint.
- However, the prior is lower than A1 / A4 because architecture change has the highest implementation cost and the highest engineering risk surface, and because A0's *information value* is partially recoverable from running A1 first (if A1 fails, H-B9 becomes more likely, justifying A0 as the second move).
- Prior 15-25 % is honest: there is a real chance a new architecture closes the seam, but the cost-prior ratio is unfavorable for the *first* sub-phase.

### 7.7 R-T1 / R-B reframing applicability

- **R-T1**: **partial** — only if the architecture itself decides selection (e.g., two-stage candidate→confirm where stage 2 *is* the selection rule). Otherwise none.
- **R-B**: **partial** — only if the architecture admits a path / microstructure / sequence feature class as part of its definition (e.g., temporal CNN over recent bars implicitly uses path-shape information). Scope amendment required.

---

## 8. A2 — target redesign (Tier 3; not a dissent)

### 8.1 Definition

Replace or augment the realised-PnL target with a structurally different target. Examples:

- **Trade-quality target** — continuous target combining path features (MFE / MAE / time-in-trade) rather than terminal barrier PnL.
- **Risk-adjusted target** — per-trade Sharpe-like target normalised by realised volatility.
- **Cost-decomposed target** — separate gross PnL from spread cost; target each.

### 8.2 Mechanism

If the realised-PnL target itself is misaligned with the monetisation goal (because per-trade noise dominates, or because the target ignores intra-trade path information), then any score that ranks well on it will not necessarily monetise. A2 attacks the target.

### 8.3 Falsifiable H-Cx (placeholder pre-statement)

> **H-C4 (placeholder)**: A redesigned target (trade-quality / risk-adjusted / cost-decomposed) will produce a ranking that, applied at val-selection, lifts realised-PnL Sharpe above the §10 baseline by ≥ +0.05 absolute, OR else H-C4 is falsified.

### 8.4 Implementation cost

**~2.0 sub-phases (~5-7 days)**. Includes the target rebuild on the existing dataset (or a new `path_quality_dataset.parquet` variant), the new sub-phase eval harness, and the auxiliary baseline (since §10 baseline is defined against realised-PnL).

### 8.5 Risk surface

- **Blast radius**: medium — target change touches the dataset layer (kept under `artifacts/stage25_0a/` lineage) and creates semantic incompatibility with the §10 baseline.
- **Always requires scope amendment** per kickoff §15.2 (target spec change is a closed surface).
- **§10 baseline misalignment**: A2 sub-phases must declare an auxiliary baseline alongside §10; §10 numeric remains unchanged but the comparison becomes mixed.

### 8.6 Prior P(GO)

**10-20 %.**

Reasoning:

- Information value is genuinely high (target adequacy is a fundamental question), but cost is high and §10 baseline becomes semantically tricky.
- Prior is below A0's because A0's H-B9 has stronger 5-eval-picture evidence than A2's "target may be wrong" framing.
- A2 is preserved as Tier 3 (not foreclosed); it may be elevated by user routing decision if A1's result raises target-adequacy as the next question.

### 8.7 R-T1 / R-B reframing applicability

- **R-T1**: **none**.
- **R-B**: **partial** — only if the redesigned target incorporates path / microstructure information as part of its construction.

---

## 9. A3 — regime-conditioned / hierarchical modeling (Tier 3; not a dissent)

### 9.1 Definition

Decompose the model along a regime axis in a structural way (not as additive features as in 27.0f R7-C). Examples:

- **Gating network** — a learned gate decides which sub-model handles a given bar based on regime features.
- **Mixture-of-experts** — multiple specialised models, weighted per bar by regime.
- **Per-regime training** — fit separate models per regime cell (e.g., spread tertile × volume tertile) and combine.

### 9.2 Mechanism

H-B8 (path / microstructure / multi-TF feature class needed, not regime-statistic) is the closure-time hypothesis that A3 attacks. Where R7-C used regime *features*, A3 uses regime as an *architectural decomposition*. The information enters the model via the architecture, not the feature surface.

### 9.3 Falsifiable H-Cx (placeholder pre-statement)

> **H-C5 (placeholder)**: A regime-conditioned model (gating / MoE / per-regime training) will lift val Sharpe above the §10 baseline by ≥ +0.05 absolute at trade count ≥ 20,000, OR else H-C5 is falsified.

### 9.4 Implementation cost

**~2.0 — 2.5 sub-phases (~5-8 days)**. New training pipeline; gating network or per-regime cells; scope amendment required if R-B reframing admits a new feature class.

### 9.5 Risk surface

- **Blast radius**: medium.
- **Phase 27 inertia risk**: medium-high (§11.4) — must be distinguished from R7-C in scoping.
- **Always requires scope amendment** if R-B reframing introduces a new closed allowlist (path / microstructure / multi-TF features).

### 9.6 Prior P(GO)

**10-20 %.**

Reasoning:

- H-B8 is a real open question, but the 5-eval picture's specific Phase 27 finding (R7-C insufficient) is consistent with the regime axis being structurally weak at this architecture/target, not just at this feature representation.
- A3 is more attractive *as a second move* after A1 fails, because A1's failure would shift the bottleneck-narrative toward "the regressor itself cannot use regime information at all," which A3 attacks.
- Prior 10-20 % is honest: real but not first-move.

### 9.7 R-T1 / R-B reframing applicability

- **R-T1**: **none**.
- **R-B**: **full** — A3 is the natural Phase 28 home for R-B, especially if path / microstructure features enter as part of the regime decomposition. Requires scope amendment.

---

## 10. 5-axis cross-comparison matrix

| Axis | Lever | Cost (sub-phases) | Blast radius | Impl complexity | Scope amendment | Info value | Phase 27 inertia risk | Prior P(GO) | R-T1 reframe | R-B reframe | Tier |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A1** | objective / loss redesign | 1.0 — 1.5 | low | low | not required | medium-high | medium (manageable) | **35-45 %** | none | none | **Tier 1 (primary)** |
| **A4** | monetisation-aware selection | 1.5 — 2.0 | medium | medium | maybe (non-quantile cells) | medium-high | medium | 25-35 % | **full** | none | Tier 2 (dissent 1) |
| **A0** | architecture redesign | 2.0 — 3.0 | medium-high | high | maybe (if implies target reshape) | high | low | 15-25 % | partial | partial | Tier 2 (dissent 2) |
| **A2** | target redesign | 2.0 | medium | medium-high | **always** | high | low | 10-20 % | none | partial | Tier 3 |
| **A3** | regime-conditioned modeling | 2.0 — 2.5 | medium | medium-high | maybe (if new feature class) | medium | medium-high | 10-20 % | none | **full** | Tier 3 |

**Reading the matrix**: A1 wins on cost-prior. A4 attacks the strongest closure-time hypothesis (H-B7) but operates on top of *some* score. A0 attacks H-B9 most directly but at the highest cost. A2 and A3 are real but better suited as second movers after A1's result is in.

---

## 11. Phase 27 inertia risk per axis

The Phase 28 kickoff (PR #335 §3) listed five Phase 27 inertia routes that are NOT admissible at kickoff. Each Phase 28 axis carries a risk of collapsing into one of those routes during scoping. The mitigation is **sub-phase scoping** (pre-stating in the sub-phase design memo what the axis *is* and what it is *not*).

### 11.1 A0 — architecture redesign — inertia risk **low**

A0 changes the model class itself, which by definition diverges from any Phase 27 inertia route (all Phase 27 sub-phases used the same LightGBM tabular regressor / classifier). The only inertia danger is if the "new" architecture is essentially the old one with hyperparameter retuning; this must be explicitly disallowed at sub-phase scoping ("hyperparameter sweep alone is not A0").

### 11.2 A1 — objective redesign — inertia risk **medium**

A1 risks collapsing into a Phase 27 S-C / S-D / S-E score-axis micro-redesign if the loss change is small-scale (e.g., adding a single re-weighting term over the same Huber regression on the same target). The mitigation is to pre-state at sub-phase design memo time which loss class is being tested and to require it to be structurally distinct from S-C TIME-α-grid / S-D calibrated EV / S-E Huber regression. A re-weighted-by-realised-PnL-magnitude loss is admissible; a single-α-scaling tweak is not.

### 11.3 A2 — target redesign — inertia risk **low**

A2 always requires a target spec change, which by definition exits Phase 27's realised-PnL-target frame. The only inertia danger is a *very* minor target spec change (e.g., changing K_FAV from 1.5×ATR to 1.4×ATR) that does not actually exercise A2's information value; the sub-phase design memo must pre-state the structural target change.

### 11.4 A3 — regime-conditioned modeling — inertia risk **medium-high**

A3 risks collapsing into a Phase 27 R7-C-style regime-statistic feature widening (which has been falsified). The Phase 28 distinction is **architectural conditioning** (gating network / MoE / per-regime cells) versus **feature-level conditioning** (R7-C). The sub-phase design memo must declare which side of that line it is on; if the model is "LightGBM regressor on R7-A + regime-statistic features," that is **R7-C inertia**, not A3.

### 11.5 A4 — monetisation-aware selection — inertia risk **medium**

A4 risks collapsing into a Phase 27 R-T2-style quantile-family trim if the "new selection rule" is essentially "use the same top-quantile-on-score rule with a different q grid." The Phase 28 distinction is **structural redesign** (absolute thresholds / middle-bulk / per-pair calibration / ranked-cutoff / joint score+selection) versus **trim of the same rule** (R-T2). The sub-phase design memo must declare which side of that line it is on.

---

## 12. How each axis uses Phase 27 findings

| Axis | Phase 27 finding directly attacked | Phase 27 finding preserved | Notes |
|---|---|---|---|
| **A1** | H-B3 PARTIAL (Spearman PASS / Sharpe FAIL) — train-time response | 27.0d S-E ranking signal (Spearman +0.438) | The most incremental use of Phase 27 findings; preserves the positive result, attacks the negative result at the training-time entry point. |
| **A4** | H-B7 (val-selection rule misspecified) — selection-time response | 27.0d S-E ranking signal as one possible score input | Acknowledges the val-selector picked baseline in 5/5 sub-phases as the load-bearing observation. |
| **A0** | H-B9 (seam exhausted at this architecture) — architecture-level response | All Phase 27 findings as historical evidence | The most ambitious use of Phase 27 findings; the closure-time hypothesis chain (H-B7 / H-B8 / H-B9) provides the rationale for changing the architecture. |
| **A2** | H-B3 partial + open question §17-2 (target adequacy) | 27.0d ranking signal *if* the new target is comparable | Often produces a new dataset surface; §10 baseline becomes semantically tricky. |
| **A3** | H-B8 (regime-conditioned ≠ regime-statistic features) | R7-A baseline | The R-B-reframing-friendly axis; admits new feature class via scope amendment. |

---

## 13. R-T1 / R-B reframing eligibility table

| Axis | R-T1 reframing | R-B reframing | Notes |
|---|---|---|---|
| A0 architecture redesign | partial | partial | If the architecture decides selection or admits a new feature class (e.g., sequence model with path-shape implicit features). |
| A1 objective redesign | none | none | A1 keeps both the selection rule and the feature surface. |
| A2 target redesign | none | partial | If the new target incorporates path / microstructure information. |
| **A3** regime-conditioned modeling | none | **full** | The natural Phase 28 home for R-B. Scope amendment required. |
| **A4** monetisation-aware selection | **full** | none | The natural Phase 28 home for R-T1. Scope amendment maybe (non-quantile cells). |
| R-T3 (concentration formalisation) | n/a | n/a | Not reframed under any A-axis; remains below-threshold per PR #334 §12. Future revival requires Clause 2 amendment. |

**This PR does not elevate R-T1 or R-B.** It records that *if* the user later decides to elevate, A4 (R-T1) and A3 (R-B) are the canonical Phase 28 frames; A0 / A2 admit partial reframing.

---

## 14. Recommended first mover + 2 dissents

### 14.1 Primary — **A1 objective redesign**

A1 is recommended as Phase 28's first mover for six reasons:

1. **Preserves the only positive Phase 27 finding** (27.0d S-E Spearman +0.438).
2. **Lowest implementation cost** among A0 — A4 (~1.0 — 1.5 sub-phases).
3. **No scope amendment required** under Phase 28 kickoff §15 (unless the loss change touches Clause 2, which a re-weighted / asymmetric / cost-aware loss generally does not).
4. **Lowest blast radius** — production v9, closed allowlists, §10 baseline all untouched.
5. **Direct response to H-B3 partial** — the residual gap is attacked exactly where it exists (training-time treatment of the expensive regime).
6. **Negative-result information value**: if A1 fails to lift Sharpe, that is strong additional evidence for H-B9 (seam exhausted at this architecture), which raises the prior for A0 as the second move. A1's negative-result information value is high in addition to its positive-result information value.

The A1 sub-phase design memo (out of scope here) will pre-state the specific loss class, the FAIL-FAST baseline reproduction gate, the cell structure (control + candidate cells), and H-C1.

### 14.2 Dissent 1 — **A4 monetisation-aware selection**

A4 is preserved as dissent 1. The strongest argument against the A1 primary is that the 5-eval picture's val-selector-picks-baseline pattern is more consistent with H-B7 (rule misspecified) than with H-B3 (training under-fit on expensive regime). If the user reads the 5-eval picture as "the rule is wrong," then A4 attacks H-B7 directly while reframing the deferred R-T1 (absolute-threshold / middle-bulk / per-pair / ranked-cutoff) inside Phase 28.

A4 can be elevated to primary at the user's discretion (decision rule §16 row 2).

### 14.3 Dissent 2 — **A0 architecture redesign**

A0 is preserved as dissent 2. The strongest argument against A1 *and* A4 is that the 5-eval picture's pattern is consistent with H-B9 (seam exhausted at this architecture), in which case no loss or selection-rule change at the current architecture will lift Sharpe; only a structurally different model class can. If the user reads H-B9 as the binding constraint, A0 attacks it most directly.

A0 can be elevated to primary at the user's discretion (decision rule §16 row 3) at the cost of accepting the highest implementation cost and engineering surface.

### 14.4 Why A2 and A3 are NOT dissents

A2 always requires a scope amendment (target spec change) and creates §10 baseline misalignment, raising the implementation surface beyond what is comfortable for the *first* Phase 28 move. It is preserved as Tier 3 and may be elevated if A1's result raises target adequacy as the next question.

A3 has the highest Phase 27 inertia risk (medium-high — must be distinguished from R7-C feature-level conditioning) and requires scope amendment for any R-B reframing. It is preserved as Tier 3 and is more attractive as a second mover after A1's result is in.

---

## 15. Why NOT pick A2 / A3 as primary (judgement section)

### 15.1 Why not A2 first

A2's information value is genuinely high: target adequacy is a structural question that Phase 27 did not test. However:

- A2 requires a scope amendment PR (target spec is closed; kickoff §15.2 always-required).
- A2 creates §10 baseline misalignment, requiring auxiliary baselines and complicating sub-phase comparisons.
- A2's prior P(GO) at 10-20 % is below A0's despite higher information value, because the 5-eval picture supports H-B9 (architecture) more strongly than "target may be wrong."

A2 is better positioned as a Phase 28 second or third mover after A1's result is in. If A1 succeeds, target adequacy becomes less binding; if A1 fails, the second-move decision is between A0 (architecture) and A2 (target), which is itself a downstream routing decision.

### 15.2 Why not A3 first

A3's Phase 27 inertia risk is the highest among the five axes (medium-high; §11.4). The Phase 28 distinction between architectural regime-conditioning (A3) and feature-level regime widening (Phase 27 R7-C) requires careful scoping; any failure to maintain that distinction collapses A3 into R7-C inertia. As the first Phase 28 sub-phase, A3 has the highest scoping-failure cost.

A3 also requires a scope amendment if R-B reframing introduces a new feature class. This is admissible but heavier than the no-amendment A1 path.

A3 is better positioned after A1's result: if A1 fails, the next question is whether the regressor itself can use regime information at all, which A3 attacks.

### 15.3 Why A1 over A4 (more nuanced)

A4 has a stronger structural argument: H-B7 is more consistent with the 5-eval pattern than H-B3. So why not A4 first?

- **A4 still depends on having a useful score.** If A4 changes the selection rule but the score itself remains poorly aligned with monetisation, even the smartest selection rule will not surface a candidate beating the §10 baseline. A1 first tests whether the score can be improved; A4 then operates on top of that result.
- **A1's information value is symmetric.** A1's positive result re-opens the seam; A1's negative result strengthens H-B9 and raises A0's prior. A4's information value is more lopsided: a positive result supports H-B7, but a negative result is consistent with both "rule was fine, score was wrong" and "rule and score are both wrong" — less informative for the next move.
- **A1 cost is lower.** Even if A4 is the "structurally right" first move, the implementation cost gap (A1 ~1.0-1.5 vs A4 ~1.5-2.0 sub-phases) favours A1 as the cheaper exploratory step.

The user may override this judgement and elevate A4 to primary; decision rule §16 row 2 records the condition.

---

## 16. Decision rule — pre-stated thresholds

Pre-state the conditions under which each axis is elevated to primary, so the routing decision is mechanical rather than vibes-based:

| Condition | Selected axis as first mover |
|---|---|
| 5-eval picture interpreted as "training-time response to H-B3 partial is the first move" AND scope-amendment cost is to be minimised AND S-E ranking signal preservation is valued → | **A1 (default primary)** |
| User reads 5-eval picture as "the val-selection rule is the binding constraint per H-B7" AND user accepts moderate cost AND wants R-T1 reframing inside Phase 28 → | **A4 (overrides A1)** |
| User reads 5-eval picture as "the architecture itself is the binding constraint per H-B9" AND user accepts highest cost AND wants the most direct attack on seam exhaustion → | **A0 (overrides A1)** |
| User explicitly elevates target redesign with prior > 25 % AND authorises target-spec scope amendment → | **A2 (overrides A1; downstream comparison strategy required)** |
| User explicitly elevates regime-conditioned modeling with prior > 25 % AND authorises closed-allowlist scope amendment for R-B reframing AND accepts medium-high inertia risk → | **A3 (overrides A1)** |

The default condition (5-eval picture → training-time response) is consistent with the recommendation in §14.1. The four override conditions correspond to four different user readings of the 5-eval picture, each pre-stated so the routing choice is auditable.

---

## 17. Open questions / unknowns

Five open questions carried into Phase 28 and not resolved by this routing review:

1. **What specific loss class for A1?** Re-weighted by absolute realised-PnL, asymmetric by spread cost, or fully cost-aware? The A1 sub-phase design memo pre-states this.
2. **If A1 succeeds, does §10 baseline remain the canonical reference, or does the new C-se cell become the comparison anchor for Phase 28 second-mover routing?** This depends on A1's verdict and is a Phase 28 second-mover routing decision.
3. **Should the Phase 22 frozen-OOS contract be revisited if a Phase 28 sub-phase explores subset / superset universes?** Kickoff §12-3 records this as an open question. Sub-phase design memos that touch universe scope must pre-state compatibility with the frozen-OOS contract.
4. **Should R-T3 (concentration formalisation) ever be revived?** Current status: below-threshold; deferred; not reframed by this PR. Revival depends on the cumulative Phase 28 result picture; not a Phase 28 first-mover question.
5. **Does the routing-review-after-N-sub-phases cadence (used in Phase 27) apply to Phase 28, or should Phase 28 use a different cadence (e.g., routing review after every sub-phase)?** Not decided here; will emerge from Phase 28 sub-phase practice.

---

## 18. Binding constraints (verbatim)

This routing review preserves every constraint that was binding at the start of Phase 28:

- D-1 bid/ask executable harness preserved
- validation-only selection
- test touched once
- ADOPT_CANDIDATE wall preserved
- H2 PASS = PROMISING_BUT_NEEDS_OOS only
- NG#10 / NG#11 not relaxed
- γ closure PR #279 preserved
- X-v2 OOS gating remains required
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
- no A0 — A4 sub-phase initiation
- no prior verdict modification
- no auto-route after merge

The recommendation is **scope-level only**. The next action requires an explicit separate user routing decision.

---

## 19. References

**Phase 28**:
- PR #335 — Phase 28 kickoff (`docs/design/phase28_kickoff.md`)

**Phase 27 (evidence anchor)**:
- PR #334 — Phase 27 closure memo (`docs/design/phase27_closure_memo.md`)
- PR #333 — Phase 27 post-27.0f routing review (`docs/design/phase27_post_27_0f_routing_review.md`)
- PR #316 — Phase 27 kickoff
- PR #318 / #321 / #325 / #328 / #332 — five Phase 27 β-evals
- PR #319 / #322 / #326 / #329 — four Phase 27 intermediate routing reviews

**Binding contracts**:
- PR #279 — γ closure
- Phase 22 frozen-OOS contract
- X-v2 OOS gating
- Phase 9.12 production v9 closure tip `79ed1e8` (production v9 20-pair, untouched throughout Phase 27 and Phase 28 kickoff)

---

*End of `docs/design/phase28_first_mover_routing_review.md`.*
