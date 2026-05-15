# Phase 27 Closure Memo

**Type**: doc-only formal closure memo
**Status**: closes Phase 27 (score → selection → feature widening on top of Phase 26 R6-new-A baseline) without ADOPT_CANDIDATE
**Branch**: `research/phase27-closure-memo`
**Base**: master @ `8028f03` (post-PR #333 merge)
**Routing**: **R-E** selected by the user after the post-27.0f routing review (PR #333)
**Pattern**: analogous to PR #298 (Phase 25 closure) / PR #315 (Phase 26 closure), with Phase 27-specific additions (§4 5-eval evidence picture; §5 Channel-wise lessons; §11 carry-forward register)
**Date**: 2026-05-16

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval of this PR accepts the formal closure declaration: **Phase 27 is closed**. The closure consolidates the **5-eval evidence picture** (27.0b / 27.0c / 27.0d / 27.0e / 27.0f β-evals), records the hypothesis-status snapshot, and preserves R-T1 and R-B as **deferred-not-foreclosed** dissents. The closure does **not** prejudge the eventual outcome of R-T1 or R-B if either is later elevated by an explicit user routing decision. The closure does **not** create a Phase 28 kickoff and does **not** decide any next sub-phase. Any post-closure resumption of R-T1 / R-B / R-T3 — or any Phase 28 work — requires a **separate later user routing decision**.*

Same approval-then-defer pattern as PR #298 / PR #315.

---

## 1. Executive summary

This memo **formally closes Phase 27** per the user's **R-E** routing decision after PR #333. Phase 27 ran five sub-phase β-evals on top of the Phase 26 R6-new-A baseline:

- **27.0b-β** (PR #318) — S-C TIME penalty α grid
- **27.0c-β** (PR #321) — S-D calibrated EV
- **27.0d-β** (PR #325) — S-E regression on realised PnL
- **27.0e-β** (PR #328) — R-T2 quantile-family trim
- **27.0f-β** (PR #332) — R7-C regime/context feature widening

**Top-level closure-time facts**:

1. **All five β-evals returned REJECT.** No sub-phase produced ADOPT_CANDIDATE. No sub-phase produced PROMISING_BUT_NEEDS_OOS.
2. **Val-selector picked C-sb-baseline in 5/5 sub-phases.** The val-selected (cell\*, q\*) record is bit-identical across all five sub-phases (q\*=5; val Sharpe -0.1863; test Sharpe -0.1732; test n=34,626; test ann_pnl -204,664.4; test Spearman -0.1535) — none of the new candidate cells were val-superior.
3. **S-E (27.0d) unlocked ranking signal but failed monetisation conversion.** Spearman +0.438 (PASS at the H1m level) but Sharpe -0.483 at the C-se cell.
4. **R-T2 trim (27.0e) did not fix Sharpe.** Reducing the quantile budget to {5, 7.5, 10} preserved Spearman but worsened Sharpe further (H-B5 PARTIAL_SUPPORT, row 2).
5. **R7-C regime/context features (27.0f) did not fix the top-tail adversarial selection.** C-se-rcw ≈ C-se-r7a-replica at every quantile (max |Δ Sharpe| = 0.0039) — H-B6 FALSIFIED_R7C_INSUFFICIENT, row 3.

The 5-eval picture supports the **R-E** primary recommendation from PR #333 §13. **R-T1** (selection-rule redesign) and **R-B** (different feature axis) are preserved as **deferred-not-foreclosed** dissents. **R-T3** (concentration formalisation) is recorded as below-threshold and deferred; it is not preserved as a dissent.

No production change. No modification of any prior verdict. ADOPT_CANDIDATE wall, H2 wall, NG#10 / NG#11, γ closure PR #279, X-v2 OOS gating, Phase 22 frozen-OOS contract, production v9 20-pair (Phase 9.12 closure tip `79ed1e8`) all preserved untouched.

---

## 2. Closure declaration (verbatim)

**Phase 27 is formally closed at master `8028f03` (post-PR #333).**

The closure is final for the Phase 27 scope as defined at PR #316 (kickoff) and amended by:

- PR #324 — Phase 27 scope amendment S-E (`phase27_scope_amendment_s_e.md`)
- PR #330 — Phase 27 scope amendment R7-C (`phase27_scope_amendment_r7_c.md`)

The closure does **NOT** foreclose:

(a) **R-T1** — selection-rule redesign (absolute-threshold / middle-bulk / per-pair calibrated cutoff / ranked-cutoff). Deferred-not-foreclosed; see §11.
(b) **R-B** — different feature axis (path-shape / microstructure / multi-TF context). Deferred-not-foreclosed; see §11. Resumption requires a new scope-amendment PR analogous to PR #330.
(c) **R-T3** — concentration formalisation. Below-threshold and deferred; see §12. Not preserved as a dissent.
(d) **Phase 25 / Phase 26 deferred-not-foreclosed items** — preserved under their respective closure semantics (PR #298 / PR #315).
(e) **Future architecture / objective / hierarchy / target redesign** — successor Phase 28 scope is a separate later instruction; not created in this PR.

The closure is a declaration, not an analysis. The substantive analysis lives in PR #333 (`docs/design/phase27_post_27_0f_routing_review.md`) and is referenced by this memo without restatement.

---

## 3. Phase 27 timeline

| Event | PR | Type |
|---|---|---|
| Phase 27 kickoff | #316 | doc-only |
| 27.0b-β S-C TIME penalty eval | #318 | eval |
| Phase 27 post-27.0b routing review | #319 | doc-only |
| 27.0c-α S-D design memo | #320 | doc-only |
| 27.0c-β S-D calibrated EV eval | #321 | eval |
| Phase 27 post-27.0c routing review | #322 | doc-only |
| Phase 27 scope amendment S-E | #324 | doc-only |
| 27.0d-α S-E design memo | (in #325) | doc-only |
| 27.0d-β S-E regression eval | #325 | eval |
| Phase 27 post-27.0d routing review | #326 | doc-only |
| 27.0e-α S-E quantile-trim design memo | #327 | doc-only |
| 27.0e-β S-E quantile-family trim eval | #328 | eval |
| Phase 27 post-27.0e routing review (introduced H-B6) | #329 | doc-only |
| Phase 27 scope amendment R7-C | #330 | doc-only |
| 27.0f-α S-E + R7-C design memo | #331 | doc-only |
| 27.0f-β S-E + R7-C regime/context eval (with Fix A row-set isolation) | #332 | eval |
| Phase 27 post-27.0f routing review — R-E primary | #333 | doc-only |
| **Phase 27 closure memo** | **this PR** | **doc-only** |

Five β-evals (#318, #321, #325, #328, #332). Five routing reviews (#319, #322, #326, #329, #333). Two scope amendments (#324, #330). Five design memos (one per sub-phase, kickoff included). One closure memo (this PR).

---

## 4. 5-eval evidence picture

The single most informative artifact of Phase 27 is the table below. The val-selected row is **bit-identical** across all five sub-phases because the val-selector chose the inherited `C-sb-baseline` cell (or its equivalent `C-alpha0` at 27.0b) in every sub-phase.

### 4.1 5-eval table (val-selected cells across 27.0b — 27.0f)

| sub-phase | Channel | Intervention | val-selected cell | q\* | val Sharpe | val n | test Sharpe | test n | test ann_pnl | test Spearman | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 27.0b-β | B | S-C TIME penalty α grid | C-alpha0 (S-B; α=0.0) | 5 | -0.1863 | 25,881 | -0.1732 | 34,626 | -204,664.4 | -0.1535 | REJECT |
| 27.0c-β | B | S-D calibrated EV | C-sb-baseline (S-B) | 5 | -0.1863 | 25,881 | -0.1732 | 34,626 | -204,664.4 | -0.1535 | REJECT |
| 27.0d-β | B | S-E regression on realised PnL | C-sb-baseline (S-B) | 5 | -0.1863 | 25,881 | -0.1732 | 34,626 | -204,664.4 | -0.1535 | REJECT (split) |
| 27.0e-β | C | R-T2 quantile-family trim {5, 7.5, 10} | C-sb-baseline (S-B) | 5 | -0.1863 | 25,881 | -0.1732 | 34,626 | -204,664.4 | -0.1535 | REJECT (split) |
| 27.0f-β | A | R7-C regime/context features (3-feature additive) | C-sb-baseline (S-B) | 5 | -0.1863 | 25,881 | -0.1732 | 34,626 | -204,664.4 | -0.1535 | REJECT (split) |

**Closure-time interpretation**: five different interventions across three channels (B / C / A) produced the same val-selected outcome. No new candidate cell was val-superior. The pattern is consistent with the selection→monetisation seam at this architecture being **saturated** relative to the realised-PnL target's signal-to-noise.

### 4.2 27.0f supplemental — C-se-rcw ≈ C-se-r7a-replica

The non-baseline cells inside 27.0f-β show that adding R7-C features on top of R7-A delivered **essentially no discriminative or monetisation lift**:

| q\* | C-se-rcw test Sharpe | C-se-r7a-replica test Sharpe | Δ Sharpe (rcw − replica) |
|---|---|---|---|
| 5 | -0.8389 | -0.8418 | +0.0029 |
| 10 | -0.7687 | -0.7667 | -0.0020 |
| 20 | -0.6639 | -0.6641 | +0.0002 |
| 30 | -0.5903 | -0.5906 | +0.0002 |
| 40 | -0.4869 | -0.4831 | -0.0039 |

**max |Δ Sharpe| = 0.0039** (sign-noisy; no systematic improvement). Cell Spearman for C-se-rcw is +0.43794, essentially identical to 27.0d's C-se +0.43813. R7-C did not move the regressor's discriminative power one decimal.

All formal verdicts in §4.1 stand unchanged at closure. This memo does **not** retroactively modify any prior verdict.

---

## 5. Channel-wise lessons consolidated at closure

Phase 27 attacked the bottleneck via three orthogonal channels. Each channel's closure-time lesson is consolidated below.

### 5.1 Channel B — score axis (S-C, S-D, S-E)

- **27.0b S-C TIME penalty**: α-monotonic Spearman improvement (small) accompanied by α-monotonic Sharpe degradation. Downweighting TIME-label rows did not help monetisation. H-B1 FALSIFIED.
- **27.0c S-D calibrated EV**: Calibration produced slightly negative Spearman (-0.106) vs raw S-B. H-B2 FALSIFIED.
- **27.0d S-E regression on realised PnL**: **First H1m PASS in Phase 27** — Spearman +0.438 at C-se. However Sharpe at C-se is -0.483 (n=184,703 at q=40), and val-selection still picked the baseline C-sb cell. H-B3 PARTIAL (ranking signal real, monetisation conversion failed).

**Closure-time channel lesson**: A meaningful ranking signal **is achievable** at this feature surface (S-E demonstrated this). It does **not** translate into Sharpe lift under any of the score formulations tried. The score-axis intervention surface is consumed by 27.0b / 27.0c / 27.0d at this architecture.

### 5.2 Channel C — selection-rule trim axis (R-T2)

- **27.0e R-T2 quantile-family trim**: Reduced family to {5, 7.5, 10} from baseline {5, 7.5, 10, 15, 20, 25, 30, 40}. Spearman preserved (+0.438), but Sharpe at the trimmed top tail got **monotonically worse** (-0.842 at q=5, -0.767 at q=10). Top-tail concentration is adversarial; trimming does not save it. H-B5 PARTIAL_SUPPORT (row 2).

**Closure-time channel lesson**: Reducing the quantile budget **alone** does not fix the seam. The bottleneck is deeper than the q-budget choice — top-tail rows are *more* adversarial, not less, when isolated. The selection-rule trim sub-axis is consumed by 27.0e at this architecture. The broader selection-rule **redesign** axis (R-T1) is *not* consumed and remains as a dissent (§11).

### 5.3 Channel A — feature axis (R7-A baseline, R7-C additive)

- **27.0f R7-C regime/context features**: Three-feature closed allowlist (`f5a_spread_z_50`, `f5b_volume_z_50`, `f5c_high_spread_low_vol_50`) added on top of R7-A (4 features). C-se-rcw ≈ C-se-r7a-replica at every quantile (§4.2). Top-tail audit confirms the regime axis is *directionally correct* (tighter spread, slightly elevated volume in the top tail), but the magnitude does not translate into Sharpe lift. H-B6 FALSIFIED_R7C_INSUFFICIENT, row 3.

**Closure-time channel lesson**: The regime-statistic feature class did not lift Sharpe. The broader feature-axis question — whether path-shape, microstructure, or multi-TF context features carry more information than R7-C — is *not* tested by 27.0f and remains as a dissent (R-B; §11). The closure does **not** claim the entire feature axis is exhausted; it claims the regime-statistic sub-axis tested at 27.0f is.

---

## 6. Key load-bearing finding — S-E unlocked ranking signal but monetisation conversion failed

The closure-time **single most important** observation is the 27.0d (PR #325) result reinforced by 27.0e (PR #328) and 27.0f (PR #332):

- 27.0d C-se cell: **Spearman = +0.4381** (PASS; H1m-meaningful)
- 27.0d C-se cell at val-selected (cell\*, q\*): **Sharpe = -0.483** (FAIL)
- 27.0e C-se-trimmed at q=10: **Spearman = +0.4381 (preserved)** / **Sharpe = -0.767 (worse)**
- 27.0f C-se-rcw at q=40: **Spearman = +0.43794 (preserved)** / **Sharpe = -0.487**

The discriminative signal that S-E unlocked is **real, robust, and preserved** across selection-rule trim and feature widening. The monetisation conversion is **broken at the same magnitude** across all three sub-phases. This is the falsification of the "Phase 27 hypothesis chain at this architecture": ranking ability exists, monetisation does not follow.

Two implications follow at closure:

1. The signal is **not** missing; it is mis-applied by the selection rule (top-quantile-on-regressor-score). This is the rationale for **R-T1** as a preserved dissent.
2. The regime-statistic feature axis is **not** the residual missing information. This is the rationale for **R-B** as a preserved dissent under a *different* feature class.

Both dissents are pre-stated to be falsifiable; neither is asserted at closure (§11).

---

## 7. Why R-T2 (trim) did not fix Sharpe

27.0e tested the simplest possible reading of the 27.0d Sharpe collapse: "the q-budget is too wide; trimming the top tail will preserve discrimination and remove the worst rows." The result was the opposite — trimming the family **monotonically worsened** Sharpe (-0.483 at q=40 → -0.767 at q=10 → -0.842 at q=5).

Closure-time reading:

- The top tail of the S-E regressor is **monotonically more adversarial** as q decreases. The most-confident rows are the most expensive ones to trade.
- The mechanism is consistent with **top-tail adversarial selection / regime confound** in regressor confidence (H-B6 origin). 27.0f then tested the specific regime-confound reading and falsified it as an *R7-C-statistic* problem.
- R-T2 closure: *quantile-family trim alone* is not a viable selection-rule lever. Any selection-rule fix must be **structurally different** from trim (e.g., absolute thresholds, middle-bulk, ranked-cutoff, per-pair calibration). This is the rationale for **R-T1** as a distinct dissent from R-T2.

---

## 8. Why R7-C (regime/context) did not fix top-tail adversarial selection

27.0f tested H-B6 (top-tail adversarial selection driven by regime confound) by adding three closed-allowlist regime/context features. The result was a clean falsification:

- C-se-rcw (R7-A + R7-C, 7 features) and C-se-r7a-replica (R7-A only, 4 features) are bit-tied across all five quantiles (§4.2; max |Δ Sharpe| = 0.0039).
- Cell Spearman for C-se-rcw (+0.43794) is essentially identical to 27.0d's C-se (+0.43813); R7-C added no discriminative weight.
- Top-tail audit at q=10: regime axis **is** directionally correct (top-tail rows have tighter spread, slightly elevated volume), but the magnitude does not translate.

Closure-time reading:

- The H-B6 mechanism is *directionally* real but *quantitatively* small.
- The information that would close the seam is **not in the regime-statistic surface tested by R7-C**. Whether it is in a different feature class (path-shape, microstructure, multi-TF context) is the open question that motivates **R-B** as a preserved dissent.
- The closure does **not** claim that no feature axis can help. It claims that *this* feature axis (regime-statistic) does not.

Fix A row-set isolation contract (developed mid-27.0f-β PR) is preserved at closure as part of the harness vocabulary: when an additive feature row-drop is introduced, the drop must be scoped to the test cell only and the parent baseline must be evaluated on the un-dropped row-set. This pattern is reusable for any future R-B sub-phase that introduces a different additive feature surface.

---

## 9. Hypothesis-status snapshot (closure-time)

| ID | Original framing | Status at Phase 27 closure | Notes |
|---|---|---|---|
| H-B1 | TIME-label rows distort EV scoring; S-C downweighting will help | **FALSIFIED** (27.0b) | α-monotonic Spearman↑ / Sharpe↓ |
| H-B2 | EV-scoring needs calibrated probabilities; S-D will help | **FALSIFIED** (27.0c) | Calibrated EV slightly worse than raw S-B |
| H-B3 | Direct regression on realised PnL will beat classifier S-B in monetisation | **PARTIAL** (27.0d) | Spearman PASS (+0.438) but Sharpe FAIL (-0.483); discrimination ≠ monetisation |
| H-B4 | Multi-q widening expands trade count without adverse selection | **FOLDED into H-B3** | Trade-count inflation observed; Sharpe degrades with q |
| H-B5 | Quantile-family trim {5, 7.5, 10} preserves Sharpe by cutting q-budget | **PARTIAL_SUPPORT** (27.0e row 2) | Trimming preserved Spearman but worsened Sharpe further |
| H-B6 | Top-tail regime confound; R7-C will lift Sharpe back | **FALSIFIED_R7C_INSUFFICIENT** (27.0f row 3) | Regime axis directionally correct but quantitatively insufficient |
| **H-B7** | The val-selection rule itself is misspecified (top-quantile on regressor score is the wrong rule) | **NEW closure-time / UNRESOLVED — carried into Phase 28** | val-selector picked baseline in all 5 sub-phases; motivates R-T1 dissent |
| **H-B8** | The feature surface needs path / microstructure / multi-TF context features, not regime-statistic features | **NEW closure-time / UNRESOLVED — carried into Phase 28** | R7-C tested only the regime-statistic sub-axis; motivates R-B dissent |
| **H-B9** | The Phase 27 hypothesis chain has structurally exhausted the selection→monetisation seam at this architecture | **NEW closure-time / UNRESOLVED — carried into Phase 28** | 5 consecutive REJECTs with bit-identical val-selection; motivates R-E (this closure) |

H-B7 / H-B8 / H-B9 are **NEW at closure-time** and are **UNRESOLVED — carried into Phase 28**. They are *not* Phase 27 conclusions; they are pre-stated open hypotheses that Phase 28 (or a dissent-elevation R-T1 / R-B sub-phase) may falsify or support later.

---

## 10. Primary closure rationale — R-E (verbatim from PR #333)

The substantive routing analysis for R-E lives in PR #333 (`docs/design/phase27_post_27_0f_routing_review.md` §§ 9 / 10 / 13). The closure-time consolidation is:

- **Prior P(R-E GO) = 45-55 %** (PR #333 §9.6). The single most informative fact in the 5-eval picture is that the val-selector chose the inherited baseline cell in every sub-phase. This is consistent with the hypothesis that the selection→monetisation seam at the current architecture has been thoroughly tested and the residual signal-to-noise is below what additional Phase 27 interventions can lift.
- **Cost / blast radius**: R-E is doc-only (no eval, no production change, no scope amendment); blast radius zero; rollback trivial (Phase 27 sub-phases can be reopened by a future routing decision).
- **Cost-prior comparison**: PR #333 §10 cross-branch matrix:
  - R-E: ~2-3 days doc-only, prior 45-55 %
  - R-T1: 1.5 sub-phases (~4-5 days), prior 25-35 %
  - R-B: 1.0 sub-phase (~3-4 days) + scope amendment, prior 15-25 %
  - R-T3: 2 sub-phases + Clause 2 amendment, prior 5-15 %

R-E has the best cost-prior ratio under the 5-eval evidence picture. R-T1 and R-B remain as dissents because their priors are non-zero and they attack the residual unresolved hypotheses (H-B7 / H-B8) directly. R-T3's prior is too low relative to its scope-amendment cost to justify dissent status.

The closure adopts R-E as **declaration**, not as analysis. The analysis already lives at PR #333. This memo *consolidates* the closure-time fact set so a future reader can read it standalone.

---

## 11. Carry-forward register — R-T1 / R-B deferred-not-foreclosed

The two preserved dissents are recorded below as a **carry-forward register**. Each row records the dissent name, falsifiable hypothesis, preconditions, and resumption procedure. **Phase 27 closure does not authorise resumption of any of these.**

| Dissent | Falsifiable hypothesis | Preconditions for resumption | Resumption procedure |
|---|---|---|---|
| **R-T1** — selection-rule redesign | **H-C2 (pre-stated)**: at least one of {absolute-threshold, middle-bulk, per-pair calibrated cutoff, ranked-cutoff} will lift val Sharpe above the C-sb-baseline by ≥ +0.05 absolute at a trade count ≥ 20,000. | User pre-states a specific rule class. No open-ended search (would violate validation-only / test-once). Scope amendment may be required if non-quantile cell shapes are introduced. | Separate later user routing decision → new design memo PR → β-eval PR → routing review PR (analogous to 27.0c / 27.0d / 27.0e / 27.0f path). |
| **R-B** — different feature axis | **H-C1 (pre-stated)**: adding closed-allowlist non-regime features to R7-A will lift C-se-rcw's val Sharpe above C-sb-baseline at q ≤ 20 by ≥ +0.05 absolute. | User pre-states a specific feature class (path-shape / microstructure / multi-TF context). Scope amendment PR analogous to PR #330 required first. R7-A subset remains closed; R7-C closed allowlist remains intact. NG#10 / NG#11 not relaxed. Fix A row-set isolation contract preserved for any additive surface. | Separate later user routing decision → scope amendment PR → design memo PR → β-eval PR → routing review PR. |

**Closure-time guarantee**:

- **Neither R-T1 nor R-B resumes automatically.** Both are deferred-not-foreclosed: their hypotheses remain testable in principle, but no work begins until the user issues an explicit routing decision.
- **Closure does not prejudge dissent outcomes.** If either dissent is later elevated, the resulting sub-phase produces its own verdict on its own row of the (later) evidence picture; the closure-time hypothesis-status (§9) is not retroactively revised.
- **Closure does not foreclose future revisitation.** Phase 27 sub-phases can be reopened by any future routing decision; the merged artifacts and verdicts remain valid (§14).

---

## 12. R-T3 — below-threshold; deferred (not a dissent)

R-T3 (concentration formalisation: per-pair budget caps, direction-balanced selection, max-share-per-bar, formal trade-spacing) was considered in PR #333 §8 and the cross-branch matrix (§10). Its prior P(GO) was estimated at **5-15 %**, below the dissent threshold, because: (a) it requires a Clause 2 scope amendment with non-trivial closure surface; (b) the 5-eval picture's strongest signal is val-selection / monetisation, not pair concentration; (c) conditioning on five sub-phases of broader interventions failing to lift Sharpe, expecting a pair-level constraint to do so is a low-prior bet. **R-T3 is enumerated for completeness but is NOT preserved as a dissent.** It is deferred: any future revival requires not only a routing decision but also a scope amendment and Clause 2 audit. The closure does not put R-T3 on the carry-forward register (§11).

---

## 13. Phase 28 directional hint (Phase 28 NOT created here)

Phase 28 is **not** created by this closure memo. No Phase 28 kickoff, no Phase 28 scope, no Phase 28 design memo, no Phase 28 sub-phase initiation. The Phase 28 kickoff PR is a separate later artifact requiring its own user instruction.

The 5-eval picture (§4), the channel-wise lessons (§5), and the carry-forward hypotheses H-B7 / H-B8 / H-B9 (§9) jointly suggest that — when Phase 28 is later kicked off — the most cost-prior-favorable scope is a **structural redesign** on one or more of: **architecture** (e.g., hierarchical / multi-task / regime-conditioned), **objective** (e.g., reweighted realised-PnL, asymmetric loss), **hierarchy** (e.g., two-stage candidate → confirm), or **target redesign** (e.g., alternative path-aware target construction). This is a directional hint, not a Phase 28 scope.

---

## 14. Preserved artifacts / what stays valid post-closure

The following Phase 27 artifacts remain valid post-closure and are referenced as the canonical Phase 27 record:

**Eval artifacts**:
- `artifacts/stage27_0b/eval_report.md` and `aggregate_summary.json` (#318)
- `artifacts/stage27_0c/eval_report.md` and `aggregate_summary.json` (#321)
- `artifacts/stage27_0d/eval_report.md` and `aggregate_summary.json` (#325)
- `artifacts/stage27_0e/eval_report.md` and `aggregate_summary.json` (#328)
- `artifacts/stage27_0f/eval_report.md` and `aggregate_summary.json` (#332)

**Eval scripts**:
- `scripts/stage27_0b_s_c_time_penalty_eval.py`
- `scripts/stage27_0c_s_d_calibrated_ev_eval.py`
- `scripts/stage27_0d_s_e_regression_eval.py`
- `scripts/stage27_0e_s_e_quantile_trim_eval.py`
- `scripts/stage27_0f_s_e_r7_c_regime_eval.py`

**Doc artifacts**:
- `docs/design/phase27_kickoff.md` (#316)
- `docs/design/phase27_0b_alpha_s_c_time_penalty_design_memo.md`
- `docs/design/phase27_0c_alpha_s_d_calibrated_ev_design_memo.md`
- `docs/design/phase27_scope_amendment_s_e.md` (#324)
- `docs/design/phase27_0d_alpha_s_e_regression_on_realised_pnl_design_memo.md`
- `docs/design/phase27_0e_alpha_s_e_quantile_family_trim_design_memo.md`
- `docs/design/phase27_scope_amendment_r7_c.md` (#330)
- `docs/design/phase27_0f_alpha_s_e_r7_c_regime_context_design_memo.md` (#331)
- `docs/design/phase27_routing_review_post_27_0b.md` (#319)
- `docs/design/phase27_routing_review_post_27_0c.md` (#322)
- `docs/design/phase27_routing_review_post_27_0d.md` (#326)
- `docs/design/phase27_routing_review_post_27_0e.md` (#329) — introduced H-B6
- `docs/design/phase27_post_27_0f_routing_review.md` (#333) — R-E primary decision
- `docs/design/phase27_closure_memo.md` (this PR)

**Contracts inherited / preserved**:
- D-1 bid/ask executable realised-PnL harness
- R7-A closed allowlist (4 features: `pair`, `direction`, `atr_at_signal_pip`, `spread_at_signal_pip`)
- R7-C closed allowlist (3 features: `f5a_spread_z_50`, `f5b_volume_z_50`, `f5c_high_spread_low_vol_50`)
- Fix A row-set isolation contract (27.0f-β; reusable for any future additive feature surface)
- 5-fold OOF (DIAGNOSTIC-ONLY; seed=42)
- 2-layer selection-overfit guard

**Production**:
- Production v9 20-pair (Phase 9.12 closure tip `79ed1e8`) — **touched zero times during Phase 27**.

---

## 15. Binding constraints preserved (verbatim)

This closure preserves every constraint that was binding during Phase 27. They remain binding into Phase 28 and any later dissent elevation:

- D-1 bid/ask executable harness preserved
- R7-A subset preserved
- R7-C closed allowlist preserved (no broader F5-c / F5-d / F5-e)
- no R7-B
- no R-T1 / R-T3 choices smuggled in (closure does not select any next sub-phase)
- validation-only selection
- test touched once
- diagnostics not used for formal verdict
- H2 PASS = PROMISING_BUT_NEEDS_OOS only
- ADOPT_CANDIDATE wall preserved
- NG#10 / NG#11 not relaxed
- γ closure PR #279 preserved
- X-v2 OOS gating remains required
- Phase 22 frozen-OOS contract preserved
- production v9 20-pair untouched
- no `src/` / `scripts/` / `tests/` / `artifacts/` / `.gitignore` changes in this PR
- **no MEMORY.md modification inside this PR** (post-merge bookkeeping is a separate operation, not part of the PR diff)
- no auto-route after merge
- no modification of prior verdicts

---

## 16. References

**Phase 27 PRs**:
- PR #316 — Phase 27 kickoff
- PR #318 — Phase 27.0b-β S-C TIME penalty eval
- PR #319 — Phase 27 post-27.0b routing review
- PR #320 — Phase 27.0c-α S-D design memo
- PR #321 — Phase 27.0c-β S-D calibrated EV eval
- PR #322 — Phase 27 post-27.0c routing review
- PR #324 — Phase 27 scope amendment S-E
- PR #325 — Phase 27.0d-β S-E regression on realised PnL eval
- PR #326 — Phase 27 post-27.0d routing review
- PR #327 — Phase 27.0e-α S-E quantile-trim design memo
- PR #328 — Phase 27.0e-β S-E quantile-family trim eval
- PR #329 — Phase 27 post-27.0e routing review (introduced H-B6)
- PR #330 — Phase 27 scope amendment R7-C
- PR #331 — Phase 27.0f-α S-E + R7-C design memo
- PR #332 — Phase 27.0f-β S-E + R7-C regime/context eval (with Fix A row-set isolation)
- PR #333 — Phase 27 post-27.0f routing review (R-E primary)

**Prior closure memos (template / context)**:
- PR #298 — Phase 25 closure memo
- PR #315 — Phase 26 closure memo

**Binding contracts**:
- PR #279 — γ closure
- Phase 22 frozen-OOS contract
- X-v2 OOS gating
- Phase 9.12 production v9 closure tip `79ed1e8` (production v9 20-pair, untouched throughout Phase 27)

---

*End of `docs/design/phase27_closure_memo.md`.*
