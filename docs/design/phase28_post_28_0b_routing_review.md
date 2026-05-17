# Phase 28 — Post-28.0b Routing Review

**Type**: doc-only routing review
**Status**: routes Phase 28 after 28.0b-β A4 monetisation-aware selection eval (PR #342); does NOT initiate any sub-phase
**Branch**: `research/phase28-post-28-0b-routing-review`
**Base**: master @ `c4abdee` (post-PR #342 / Phase 28.0b-β eval merge)
**Pattern**: analogous to PR #319 / #322 / #326 / #329 / #333 / #336 / #339 routing reviews
**Date**: 2026-05-18

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Phase 28 post-28.0b routing review**. It records the **comparison + recommendation** across the 3 remaining admissible Phase 28 axes (A0 / A2 / A3 per Phase 28 kickoff PR #335 §5; A1 exhausted by PR #338 closed 3-loss allowlist; A4 exhausted by PR #342 closed 4-rule allowlist), updates the carry-forward register (R-T1 → FALSIFIED_under_A4; R-B and R-T3 preserved), nominates a **primary** third-mover and **two dissents**, and pre-states a decision rule under which the user can elevate either dissent. It does **NOT**:*
>
> - *authorise any A0 / A2 / A3 sub-phase initiation,*
> - *create any Phase 28 sub-phase design memo,*
> - *open any scope amendment,*
> - *elevate R-B / R-T3 (carry-forward routes remain in PR #334 status as updated by §10 of this PR),*
> - *modify the §10 baseline numeric or any prior verdict.*
>
> *The recommendation is **scope-level only**. Executing it requires a **separate later user routing decision**, after which a sub-phase design memo PR will be drafted. R-B / R-T3 reframing also requires a separate routing decision.*

Same approval-then-defer pattern as PR #319 / #322 / #326 / #329 / #333 / #336 / #339.

---

## 1. Executive summary

**Primary recommendation**: **A0 architecture redesign** (Phase 28 third-mover).
**Dissent 1**: **A2 target redesign**.
**Dissent 2**: **A3 regime-conditioned modeling**.

| Bucket | Route | Prior P(GO) (post-28.0b updated) | One-line rationale |
|---|---|---|---|
| **Tier 1 (primary)** | **A0** architecture redesign | **35-45 %** | 28.0b-β reinforces H-B9 (now 7 data points); H-B7 strongly falsified by A4 failure; A0 is the most direct attack on the strengthened binding constraint. |
| Tier 2 (dissent 1) | **A2** target redesign | 20-30 % | Target adequacy concern reinforced by "Spearman robust / Sharpe stuck" pattern; scope amendment + auxiliary baseline required. |
| Tier 2 (dissent 2) | **A3** regime-conditioned modeling | 10-20 % | Regime-axis attack via architectural conditioning; **high inertia risk** (R7-C / L3 / R3 cumulative negative evidence); R-B reframing absorbable. |
| Tier 3 (carry-forward; not dissents) | **R-B** different feature axis | 20-30 % | Reframing under A3 / A0 / A2 admissible + scope amendment required. Prior raised by selection-rule axis exhaustion. |
| Tier 3 (below-threshold) | **R-T3** concentration formalisation | 5-15 % | Below-threshold; deferred. R3 28.0b result reinforces concentration-axis negative evidence. |

**Resolved carry-forward**: **R-T1** (selection-rule redesign) — formally absorbed under A4 sub-phase scope by PR #341 §3, resolved by PR #342 as **FALSIFIED_under_A4**. No further R-T1 elevation expected within Phase 28.

**Exhausted axes**: **A1** (objective; exhausted under PR #338 closed 3-loss allowlist; revival via scope amendment); **A4** (selection rule; exhausted under PR #342 closed 4-rule allowlist; revival via scope amendment if needed).

This PR does **not** initiate any sub-phase. The next action (A0 design memo, A2 / A3 dissent elevation, R-B / R-T3 elevation, or Phase 28 closure consideration) requires an **explicit separate user routing decision**.

---

## 2. Routing review semantics — what this PR does and does NOT do

Phase 28 has now run **two** sub-phase β-evals (28.0a-β PR #338 = A1 exhausted; 28.0b-β PR #342 = A4 exhausted + R-T1 resolved). With A1 / A4 both exhausted and R-T1 absorbed-and-falsified, this PR serves as the **Phase 28 third-mover routing decision** — analogous to PR #339 (post-28.0a) one move earlier.

**This PR does**:

1. Compare the 3 remaining admissible axes A0 / A2 / A3 along the 9-column rubric in §6.
2. Recommend a primary third-mover (A0) and two dissents (A2, A3).
3. Update prior P(GO) for each axis given 28.0b-β evidence (§14 / §16).
4. Pre-state the decision rule under which the user can elevate either dissent (§16).
5. Update R-B / R-T3 carry-forward status post-28.0b (§10).
6. Record R-T1 resolution as FALSIFIED_under_A4 (§3.6).
7. Document the channel-wise exhaustion picture (§4) — 7-eval picture organised by 3 channels + 1 reframing.

**This PR does NOT**:

1. Initiate any sub-phase (no β-eval, no design memo).
2. Author any falsifiable H-Cx that would belong in a sub-phase design memo.
3. Elevate R-B / R-T3.
4. Modify the §10 baseline numeric or any prior verdict.
5. Touch src / scripts / tests / artifacts / .gitignore / MEMORY.md.
6. Trigger auto-routing.
7. Foreclose A1 / A4 absolutely — scope-amendment revival remains possible for both per PR #339 §3.4 / PR #340 / new amendment for A4 future extensions.

---

## 3. Phase 28 evidence anchors (post-28.0b snapshot)

### 3.1 7-eval evidence picture (Phase 27 + Phase 28.0a + Phase 28.0b)

The Phase 27 closure memo (PR #334 §4.1) recorded the 5-eval picture; PR #339 §3.1 extended to 6-eval after 28.0a-β; PR #342 extends to **7 sub-phase β-evals**. The val-selected (cell\*, q\*) record remains **bit-identical** across all seven:

| sub-phase | Channel | Intervention | val-selected cell | val Sharpe | val n | test Sharpe | test n | H-Bx / H-Cx outcome | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 27.0b-β | B | S-C TIME penalty α grid | C-alpha0 (S-B) | -0.1863 | 25,881 | -0.1732 | 34,626 | — | REJECT |
| 27.0c-β | B | S-D calibrated EV | C-sb-baseline (S-B) | -0.1863 | 25,881 | -0.1732 | 34,626 | — | REJECT |
| 27.0d-β | B | S-E regression on realised PnL | C-sb-baseline (S-B) | -0.1863 | 25,881 | -0.1732 | 34,626 | — | REJECT (split) |
| 27.0e-β | C | R-T2 quantile-family trim | C-sb-baseline (S-B) | -0.1863 | 25,881 | -0.1732 | 34,626 | H-B5 PARTIAL_SUPPORT | REJECT (split) |
| 27.0f-β | A | R7-C regime/context features | C-sb-baseline (S-B) | -0.1863 | 25,881 | -0.1732 | 34,626 | H-B6 FALSIFIED_R7C_INSUFFICIENT | REJECT (split) |
| 28.0a-β | B (objective) | L1 / L2 / L3 closed loss allowlist | C-sb-baseline (S-B) | -0.1863 | 25,881 | -0.1732 | 34,626 | H-C1 all 3 FALSIFIED_OBJECTIVE_INSUFFICIENT | REJECT (split) |
| **28.0b-β** | **C (selection rule)** | **R1 / R2 / R3 / R4 closed 4-rule allowlist** | **C-sb-baseline (S-B)** | **-0.1863** | **25,881** | **-0.1732** | **34,626** | **H-C2 all 4 FALSIFIED_RULE_INSUFFICIENT; R-T1 = FALSIFIED_under_A4** | **REJECT (split)** |

**Bit-identical val-selected outcome in 7/7 sub-phases.** Seven different interventions across four channel-axes (B-score, B-objective, C-trim, C-redesign, A-regime) produced the same val-selected cell. The cumulative pattern is now the strongest single piece of evidence in the Phase 27 / Phase 28 inheritance chain.

### 3.2 28.0b-β specific findings (NEW)

From PR #342's eval_report.md / aggregate_summary.json:

| Cell | Configuration | val Sharpe | val n | test Sharpe | test n | test Spearman | H-C2 outcome |
|---|---|---|---|---|---|---|---|
| C-a4-R1 | absolute-threshold (per-pair val-median) | -0.408 | 258,186 | -0.356 | 237,681 | +0.438 | FALSIFIED_RULE_INSUFFICIENT (row 3) |
| C-a4-R2 | middle-bulk (global [40, 60]) | -0.317 | 103,508 | -0.272 | 157,499 | +0.438 | FALSIFIED_RULE_INSUFFICIENT (row 3) |
| C-a4-R3 | per-pair quantile (top 5%) | -0.326 | 26,878 | -0.279 | 23,081 | +0.438 | FALSIFIED_RULE_INSUFFICIENT (row 3) |
| C-a4-R4 | top-K per bar (K=1 per signal_ts) | -0.645 | 20,922 | -0.491 | 21,552 | +0.438 | FALSIFIED_RULE_INSUFFICIENT (row 3) |
| C-a4-top-q-control (rule-axis null) | top-q vanilla (q\*=40) | -0.573 | 206,985 | -0.483 | 184,703 | +0.438 | bit-tight reproduction of 27.0d C-se |
| C-sb-baseline (§10) | top-q on S-B (q\*=5) | -0.186 | 25,881 | -0.173 | 34,626 | -0.154 | §10 baseline reproduction PASS |

**Four substantive observations**:

1. **All 4 structurally distinct selection rules produced val Sharpe worse than §10 baseline.** R-T1 hypothesis (absolute-threshold / middle-bulk / per-pair / ranked-cutoff) — the carry-forward dissent from Phase 27 closure — is **falsified at every variant** under A4 absorption.
2. **Test Spearman +0.438 preserved in all 4 rules + top-q-control + r7a-replica reproductions.** The score-half discrimination signal is **robustly identical to 27.0d S-E** across all rule cells. The selection-half is the failure point.
3. **C-a4-top-q-control bit-reproduces 27.0d C-se** (val Sharpe -0.573 / test Sharpe -0.483 / test n 184,703). Harness is reliable across 3 phases (27.0d / 27.0f C-se-r7a-replica / 28.0a C-a1-se-r7a-replica / 28.0b C-a4-top-q-control = 4 reproductions).
4. **§10 baseline reproduction unchanged across 7 sub-phases.** C-sb-baseline at q\*=5 produces n_trades=34,626 / Sharpe=-0.173 / ann_pnl=-204,664 in every sub-phase. The baseline reproduction FAIL-FAST gate has held perfectly.

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

The §10 baseline remains the **immutable reference** for every Phase 28 sub-phase eval. PR #342 confirms 7th-time reproduction within tolerance.

### 3.4 Carry-forward hypotheses (updated by 28.0b-β)

| ID | Status before 28.0b-β | Status after 28.0b-β |
|---|---|---|
| H-B7 — val-selection rule misspecified | STRENGTHENED (PR #339 §3.5) | **STRONGLY FALSIFIED at this architecture** — A4 closed 4-rule allowlist (R1/R2/R3/R4) tested all 4 R-T1-class hypothesis structures; all 4 FALSIFIED. Rule is not the binding lever at this architecture / feature / target setup. |
| H-B8 — path / microstructure / multi-TF feature class | UNRESOLVED | UNRESOLVED — neither A3 (regime-as-architecture) nor R-B (path/microstructure features) tested in Phase 28 yet; A3 carries accumulated regime-axis negative evidence. |
| H-B9 — seam exhausted at this architecture | STRENGTHENED (PR #339 §3.5) | **FURTHER STRENGTHENED** — 7th data point (28.0b-β REJECT with 4 different rule variants + R-T1 absorbed-and-falsified). The only major active axis untested under this architecture is A0 (architecture itself); A2 (target) and A3 (regime-as-architecture) are also untested but carry distinct hypothesis structures. |

### 3.5 Carry-forward register status (updated by 28.0b-β)

- **R-T1** (selection-rule redesign): **RESOLVED — FALSIFIED_under_A4** per PR #341 §3 absorption + PR #342 H-C2 verdict. No longer active in the carry-forward register.
- **R-B** (different feature axis): deferred-not-foreclosed; prior **20-30 %** (PR #339 §3.6 15-25 % → upward; selection-rule axis exhaustion raises relative attractiveness of feature-class axis); reframing under A3 / A0 / A2 admissible + scope amendment required.
- **R-T3** (concentration formalisation): below-threshold; deferred; **prior 5-15 %** (unchanged; R3 28.0b per-pair quantile failure adds incremental negative evidence to concentration-axis hypothesis); NOT a dissent.

### 3.6 R-T1 absorption resolution (NEW; PR #342 outcome)

PR #341 §3 declared R-T1 formally absorbed under A4 sub-phase scope. PR #342 H-C2 aggregate verdict produced **R-T1 absorption status = FALSIFIED_under_A4** (all 4 rules FALSIFIED_RULE_INSUFFICIENT). R-T1 carry-forward register status (PR #334 §11) is now **resolved** — no longer in active routing space. R-T1 revival in a future Phase 29 sub-phase would require a fresh hypothesis distinct from the 4 rules tested under A4 (e.g., a different feature surface or a different score backbone enabling a new rule class).

---

## 4. Channel-wise exhaustion picture (post-28.0b; NEW frame)

Phase 27 + Phase 28 has tested 7 sub-phase β-evals organised by 3 channels and 1 carry-forward reframing. The exhaustion picture is now:

### 4.1 Channel B — score / objective axis

**EXHAUSTED at this architecture / feature / target setup.**

Tested variants:
- **27.0b S-C** — TIME penalty α grid: FALSIFIED (H-B1)
- **27.0c S-D** — calibrated EV: FALSIFIED (H-B2)
- **27.0d S-E** — symmetric Huber regression on realised PnL: PARTIAL (H-B3) — first H1m PASS in chain (Spearman +0.438) but H2 FAIL (Sharpe -0.483)
- **28.0a L1** — magnitude-weighted Huber: FALSIFIED_OBJECTIVE_INSUFFICIENT (H-C1)
- **28.0a L2** — asymmetric Huber (δ_pos=0.5, δ_neg=1.5): FALSIFIED_OBJECTIVE_INSUFFICIENT (H-C1; Spearman +0.466 — highest in chain)
- **28.0a L3** — spread-cost-weighted Huber (γ=0.5): FALSIFIED_OBJECTIVE_INSUFFICIENT (H-C1)

**Lesson**: 6 score / objective variants tested. Spearman PASS is achievable (S-E / L2 / L3 all in [+0.438, +0.466]). Sharpe lift impossible under this architecture / feature / target. **Score-half is solved**; the rest of the seam is not.

### 4.2 Channel C — selection-rule axis

**EXHAUSTED at this architecture / score / feature / target setup.**

Tested variants:
- **27.0e R-T2** — quantile-family trim to {5, 7.5, 10}: PARTIAL_SUPPORT (H-B5 row 2) — Spearman preserved but Sharpe monotonically worse (-0.483 → -0.767 → -0.842 at q=40 → 10 → 5)
- **28.0b R1** — absolute-threshold (per-pair val-median): FALSIFIED_RULE_INSUFFICIENT (H-C2)
- **28.0b R2** — middle-bulk ([40, 60] global): FALSIFIED_RULE_INSUFFICIENT (H-C2)
- **28.0b R3** — per-pair quantile (top 5% per pair): FALSIFIED_RULE_INSUFFICIENT (H-C2) — concentration-attacking rule failed
- **28.0b R4** — top-K=1 per signal_ts (bar-level argmax): FALSIFIED_RULE_INSUFFICIENT (H-C2) — bar-level adverse-selection-attacking rule failed

**Lesson**: 5 selection-rule sub-axes tested (1 trim + 4 redesigns). Trim made Sharpe worse; redesigns also worse than baseline. **Selection-half cannot be fixed by any rule variant** that operates on the existing S-E score at this feature surface. R-T1 carry-forward is absorbed-and-falsified.

### 4.3 Channel A — feature / regime-statistic axis

**EXHAUSTED at the regime-statistic sub-axis; broader feature-class axis NOT tested.**

Tested variants:
- **27.0f R7-C** — regime/context features (f5a spread_z / f5b volume_z / f5c high_spread_low_vol): FALSIFIED_R7C_INSUFFICIENT (H-B6) — C-se-rcw ≈ C-se-r7a-replica within max |Δ Sharpe| 0.004

**Untested feature classes** (R-B carry-forward; deferred):
- Path-shape features (e.g., MFE/MAE structural features)
- Microstructure features (e.g., recent quote micro-changes)
- Multi-TF context features (e.g., higher-timeframe regime indicators)

**Lesson**: regime-statistic sub-axis is insufficient. R-B (broader feature class) remains the standing carry-forward route on this channel, deferred-not-foreclosed.

### 4.4 R-T1 reframing (absorbed-and-falsified)

R-T1 carry-forward (Phase 27 closure memo PR #334 §11) was formally absorbed under A4 sub-phase scope by PR #341 §3. PR #342 H-C2 aggregate verdict resolved R-T1 as **FALSIFIED_under_A4** at the 4-rule closed allowlist. R-T1 reframing under A4 is now closed.

### 4.5 Active untested axes after 28.0b

1. **A0 architecture redesign** — model class itself (hierarchical / multi-task / sequence / regime-conditioned heads)
2. **A2 target redesign** — replace realised-PnL target (trade-quality / risk-adjusted / cost-decomposed / calibrated-by-regime)
3. **A3 regime-conditioned modeling** — gating network / MoE / per-regime training (architectural conditioning, NOT feature widening)
4. **R-B** different feature axis (carry-forward; not a dissent)
5. **R-T3** concentration formalisation (carry-forward; below-threshold; not a dissent)

H-B9 (seam exhausted at this architecture) is the closure-time hypothesis most directly attacked by A0.

---

## 5. What 28.0b-β changes about the routing space (post-A4 update)

The 28.0b-β result delivers five pieces of additional information that update the post-28.0a routing review (PR #339):

1. **Selection-rule axis exhaustion is now formal.** 5 selection-rule sub-axes (R-T2 trim + R1/R2/R3/R4 redesigns) tested across Phase 27 and Phase 28; none lifted Sharpe above §10 baseline. The selection-rule axis under R-T1's hypothesis space is **structurally exhausted**.
2. **R-T1 carry-forward resolved.** PR #341 absorbed R-T1 into A4; PR #342 resolved it as FALSIFIED_under_A4. R-T1 is no longer an active carry-forward route.
3. **Score is robust across all rule cells.** Spearman +0.438 preserved identically in 4 rule cells + top-q-control = score-half is solved; rule is the issue, but **no rule fix works → architecture-level issue**.
4. **Architecture is the most strongly unattacked surface among remaining routes.** H-B9 has now 7 supporting data points (7/7 val-selector pattern bit-identical to baseline). A0 is the route that most directly tests H-B9.
5. **Target / R-B remain unattacked surfaces.** A2 target redesign and R-B path/microstructure features both remain untested under Phase 28. They become more attractive routes if A0 also fails.

---

## 6. Comparison framework (9-column rubric; inherited from PR #339 §5)

| Column | Meaning |
|---|---|
| 1. Lever | One-line description of what the route changes |
| 2. Cost | Sub-phases / days |
| 3. Blast radius | low / medium / high |
| 4. Implementation complexity | low / medium / high |
| 5. Scope amendment required | Per Phase 28 kickoff §15 amendment policy |
| 6. Expected information value | high / medium / low + reasoning |
| 7. Phase 27 / 28 inertia risk | low / medium / medium-high / high |
| 8. Falsifiable H-Cx (placeholder pre-statement) | One-line pre-stated hypothesis; formal pre-stating in sub-phase α design memo |
| 9. R-B reframing applicability | none / partial / full (R-T1 no longer applicable post-resolution) |

---

## 7. A0 — architecture redesign (primary recommendation)

### 7.1 Definition

Replace or augment the model class itself with a structurally different architecture. Examples (sub-phase design memo pre-states the specific architecture):

- **Hierarchical two-stage candidate → confirm**
- **Multi-task heads** (joint TP-prob / SL-prob / TIME-prob / realised-PnL regression with shared backbone)
- **Regime-conditioned heads** (overlap with A3; scoped distinct from feature-level conditioning)
- **Sequence / structural models** (RNN / temporal CNN / Transformer over recent bars)

### 7.2 Mechanism — why this attacks H-B9 most directly

H-B9 (seam exhausted at this architecture) is the closure-time hypothesis with the strongest support after 28.0b-β: 7/7 val-selector-picks-baseline + 6 axes exhausted (score / objective / selection-trim / selection-redesign / regime-statistic). The only major dimension untested at this architecture is the **architecture itself**. If H-B9 is the binding constraint, no further intervention within the LightGBM tabular architecture can lift Sharpe; only a structurally different model class can. **A0 is the most surgical test of H-B9.**

### 7.3 Falsifiable H-C3 (placeholder pre-statement)

> **H-C3 (placeholder)**: A structurally different architecture (hierarchical / multi-task / sequence / regime-conditioned) will lift val Sharpe above the §10 baseline by ≥ +0.05 absolute at trade count ≥ 20,000 on the inherited target and feature surface, OR else H-C3 is falsified.

### 7.4 Implementation cost

**~2.0 — 3.0 sub-phases (~6-10 days)**. Highest among A0 / A2 / A3. Includes new training pipeline, new model serialisation, possibly new compute requirements (GPU for sequence models). May trigger a scope amendment if the architecture change implies a target reshape (edging into A2).

### 7.5 Risk surface

- **Blast radius**: medium-high — architecture change creates a new model class that does not share weights / hyperparameter conventions with the LightGBM baselines.
- **Rollback**: clean per-sub-phase but with higher engineering surface.
- **前提崩しの可能性**: ADOPT_CANDIDATE wall / H2 wall preserved. Architecture hyperparameter search must respect the 2-layer selection-overfit guard; enforced at sub-phase design memo time.

### 7.6 Prior P(GO) — **35-45 %**

Reasoning:

- **Updated upward from PR #339 §7.6 (25-35 %)** because 28.0b-β reinforced H-B9 and falsified H-B7. A0 is now the most direct attack on the strongest active hypothesis.
- **Cost-prior ratio is the best among the 3 active axes**: A0 (~2-3 sub-phases / 35-45 %) > A2 (~2 sub-phases + scope amendment / 20-30 %) > A3 (~2-2.5 sub-phases + scope amendment + high inertia risk / 10-20 %).
- **Information value is symmetric**: A0 success → architecture-level fix → PROMISING_BUT_NEEDS_OOS candidate; A0 failure → Phase 28 closure-and-Phase-29-rebase prior rises dramatically. Either outcome is decisive for routing.

### 7.7 R-B reframing applicability

- **R-B**: **partial** — only if the architecture admits a path / microstructure / sequence feature class as part of its definition (e.g., temporal CNN implicitly uses path-shape information). Scope amendment required.
- **R-T1**: n/a (resolved as FALSIFIED_under_A4).

### 7.8 Why A0 is the primary recommendation (eight reasons)

1. **H-B9 most strongly supported by 7-eval picture** (7/7 val-selector pattern; 6 axes exhausted at this architecture).
2. **A4 failure directly raised A0 prior** (PR #339 §7.8 / §14.2 sequencing logic confirmed: A4 failure → A0 next-move).
3. **No further "single-axis intervention at this architecture" expected to lift Sharpe** — Channel B / Channel C / Channel A (regime-statistic) all exhausted.
4. **Cost-prior ratio is the best** among A0 / A2 / A3.
5. **No mandatory scope amendment** if the architecture stays on the inherited R7-A / realised-PnL target (amendment only if target reshape implied).
6. **Symmetric information value** (success or failure both routing-decisive).
7. **No inertia risk** — A0 by definition diverges from any Phase 27 / 28 inertia route (different model class).
8. **A2 / A3 alternatives have specific obstacles**: A2 always requires scope amendment + §10 baseline misalignment; A3 has accumulated regime-axis negative evidence (27.0f R7-C + 28.0a L3 + 28.0b R3) + medium-high → high inertia risk.

---

## 8. A2 — target redesign (dissent 1)

### 8.1 Definition

Replace or augment the realised-PnL target with a structurally different target. Examples (sub-phase design memo pre-states the specific target):

- **Trade-quality target** — continuous target combining path features (MFE / MAE / time-in-trade)
- **Risk-adjusted target** — per-trade Sharpe-like target normalised by realised volatility
- **Cost-decomposed target** — separate gross PnL from spread cost; target each
- **Calibrated-by-regime target** — realised PnL conditioned on regime label

### 8.2 Mechanism — why this attacks H-B3 + target adequacy

28.0b-β reinforced a specific pattern: **score Spearman robust (+0.438 preserved in 5 cells); Sharpe stuck (val Sharpe lift ≤ +0.02 in all 4 rules)**. If the realised-PnL target itself is misaligned with the monetisation goal, then any score that ranks well on it will not necessarily monetize. A2 attacks the target directly.

### 8.3 Falsifiable H-C4 (placeholder pre-statement)

> **H-C4 (placeholder)**: A redesigned target (trade-quality / risk-adjusted / cost-decomposed / calibrated-by-regime) will produce a ranking that, applied at val-selection on the §10 baseline rule, lifts realised-PnL Sharpe above the §10 baseline by ≥ +0.05 absolute at trade count ≥ 20,000, OR else H-C4 is falsified.

### 8.4 Implementation cost

**~2.0 sub-phases (~5-7 days)**. Target rebuild on the existing dataset (or a new `path_quality_dataset.parquet` variant); new sub-phase eval harness; auxiliary baseline construction (since §10 is defined against realised-PnL).

### 8.5 Risk surface

- **Blast radius**: medium.
- **Always requires scope amendment** per kickoff §15.2.
- **§10 baseline misalignment**: A2 sub-phases must declare an auxiliary baseline alongside §10.

### 8.6 Prior P(GO) — **20-30 %**

Reasoning:

- **Updated upward from PR #339 §8.6 (15-25 %)** because 28.0b-β "Spearman robust / Sharpe stuck" pattern is now a 7-eval-supported observation, strengthening the target-adequacy concern.
- **Still below A0** because A2 requires scope amendment, creates §10 baseline misalignment, and the cost-prior ratio is less favorable.
- **A2 is the natural Phase 28 next-move after A0 failure** — if A0 also fails (architecture-level fix doesn't work), target adequacy becomes the strongest remaining hypothesis.

### 8.7 R-B reframing applicability

- **R-B**: **partial** — only if the redesigned target incorporates path / microstructure information as part of its construction.

---

## 9. A3 — regime-conditioned modeling (dissent 2)

### 9.1 Definition

Decompose the model along a regime axis in a structural way (not as additive features as in 27.0f R7-C, not as training-time weights as in 28.0a L3, not as per-pair selection cutoffs as in 28.0b R3). Examples:

- **Gating network** — learned gate decides which sub-model handles a given bar based on regime features
- **Mixture-of-experts** — multiple specialised models weighted per bar by regime
- **Per-regime training** — fit separate models per regime cell (spread tertile × volume tertile)

### 9.2 Mechanism

H-B8 (path / microstructure / multi-TF feature class needed) is the closure-time hypothesis A3 attacks via architectural conditioning. Where R7-C used regime *features*, L3 used regime as *training-time weights*, R3 used regime (per-pair) as *selection cutoffs*, A3 uses regime as **architectural decomposition**.

### 9.3 Falsifiable H-C5 (placeholder pre-statement)

> **H-C5 (placeholder)**: A regime-conditioned model (gating / MoE / per-regime training) will lift val Sharpe above the §10 baseline by ≥ +0.05 absolute at trade count ≥ 20,000, OR else H-C5 is falsified.

### 9.4 Implementation cost

**~2.0 — 2.5 sub-phases (~5-8 days)**. New training pipeline; gating network or per-regime cells; scope amendment required if R-B reframing admits a new feature class.

### 9.5 Risk surface

- **Blast radius**: medium.
- **Phase 27 / 28 inertia risk**: **HIGH** (§12.3 elevated from medium-high). Three distinct regime-axis-attacking interventions have already failed:
  - 27.0f R7-C — regime as features → FALSIFIED
  - 28.0a L3 — regime (spread) as training-time weight → FALSIFIED
  - 28.0b R3 — regime (pair) as selection cutoff → FALSIFIED
  A3 is **structurally distinct** from each (architectural conditioning, not feature/weight/cutoff), but the cumulative regime-axis negative evidence increases the structural-failure prior.
- **Always requires scope amendment** if R-B reframing introduces a new closed allowlist (path / microstructure / multi-TF features).

### 9.6 Prior P(GO) — **10-20 %**

Reasoning:

- **Unchanged from PR #339 §9.6 (10-20 %)**. Despite 28.0b R3 adding a 3rd regime-axis negative data point, A3 architectural conditioning is structurally distinct from R7-C / L3 / R3; the prior is not strictly downward, but inertia risk is upgraded to **high**.
- **A3 remains in Tier 2 (dissent 2)** because H-B8 is genuinely unresolved and R-B reframing under A3 is the most natural Phase 28 home for R-B's path / microstructure exploration.

### 9.7 R-B reframing applicability

- **R-B**: **full** — A3 is the natural Phase 28 home for R-B. Requires scope amendment.

---

## 10. R-B / R-T3 carry-forward status (updated post-28.0b)

### 10.1 R-B (different feature axis)

- **Status**: deferred-not-foreclosed; carry-forward (PR #334 §11 verbatim, unchanged in policy).
- **Prior P(GO)**: **20-30 %** (PR #339 §3.6 15-25 % → upward).
- **Why prior raised**: selection-rule axis exhaustion (28.0b) makes feature-class axis relatively more attractive among unattacked surfaces. Phase 28 has now exhausted score / selection at the same R7-A feature surface; the R7-A feature surface itself remains a possible binding constraint.
- **Reframing applicability**: A3 (full) / A0 (partial) / A2 (partial).
- **Resumption requirement**: separate routing decision + scope amendment PR (analogous to PR #330 R7-C amendment) declaring a new closed feature allowlist (e.g., R7-D path-shape, R7-E microstructure, R7-F multi-TF context).
- **Tier 3 in §11 matrix; NOT a dissent.** R-B elevation requires explicit user routing decision; not auto-triggered by 28.0b-β.

### 10.2 R-T3 (concentration formalisation)

- **Status**: below-threshold; deferred; NOT a dissent (PR #334 §12 verbatim, unchanged in policy).
- **Prior P(GO)**: **5-15 %** (unchanged from PR #339 §3.6).
- **Negative evidence reinforcement**: R3 28.0b result (per-pair top 5% selection → FALSIFIED_RULE_INSUFFICIENT) is a concentration-axis attack via selection rule. It failed. While R-T3 (concentration via Clause 2 amendment + per-pair budget constraints in cell-construction) is structurally different from R3 (per-pair quantile selection), R3's failure incrementally lowers expectations for concentration-axis attacks.
- **Resumption requirement**: separate routing decision + Clause 2 scope amendment + R3 negative evidence acknowledgement.
- **Tier 3 in §11 matrix; NOT a dissent.**

### 10.3 Why R-B is NOT dissent 1 or dissent 2

R-B carries higher prior (20-30 %) than A3 (10-20 %), but is **not promoted to dissent** because:
- R-B requires its own scope amendment PR before any β-eval can run (R-B closed allowlist must be defined first; analogous to PR #330).
- R-B reframing under A3 (full) makes it operationally equivalent to A3 elevation in many practical scenarios.
- A2 and A3 are A-axes (admissible at Phase 28 kickoff §5); R-B is a carry-forward route requiring elevation. Tier 2 dissents stay restricted to the directly admissible axes for cleaner sequencing.

R-B can be elevated to primary at the user's discretion (decision rule §16 row 5) at the cost of accepting the additional scope-amendment surface.

---

## 11. 5-route cross-comparison matrix

| Route | Lever | Cost (sub-phases) | Blast radius | Impl complexity | Scope amendment | Info value | Phase 27 / 28 inertia risk | Prior P(GO) | R-B reframe | Tier |
|---|---|---|---|---|---|---|---|---|---|---|
| **A0** | architecture redesign | 2.0 — 3.0 | medium-high | high | maybe (if implies target reshape) | high | low | **35-45 %** | partial | **Tier 1 (primary)** |
| **A2** | target redesign | 2.0 | medium | medium-high | **always** | high | low | **20-30 %** | partial | Tier 2 (dissent 1) |
| **A3** | regime-conditioned modeling | 2.0 — 2.5 | medium | medium-high | maybe (if new feature class) | medium | **high** | 10-20 % | **full** | Tier 2 (dissent 2) |
| R-B | different feature axis | unknown until scope amendment | medium | medium | **always** | medium-high | medium-high | 20-30 % | n/a | Tier 3 (carry-forward) |
| R-T3 | concentration formalisation | 2.0 | medium-high | medium | **always (Clause 2)** | low | high | 5-15 % | n/a | Tier 3 (below-threshold) |

**Reading the matrix**: A0 wins on cost-prior + no mandatory amendment + low inertia risk. A2 is the second-most informative move after A0 — reserved for the post-A0-failure routing review. A3 carries high inertia risk despite being structurally distinct; remains as dissent for completeness. R-B is a strong carry-forward candidate awaiting separate elevation. R-T3 below dissent threshold.

---

## 12. Risk of Phase 27 / 28 inertia per route (updated post-28.0b)

The Phase 28 kickoff (PR #335 §3) listed five Phase 27 inertia routes that are NOT admissible. 28.0a-α §2 added A1 single-loss-variant micro-redesign; PR #341 §2 added 4 more A4-inertia routes. After 28.0b-β:

### 12.1 A0 — architecture redesign — inertia risk **low**

A0 changes the model class itself, which by definition diverges from any Phase 27 / 28 inertia route. The only inertia danger is if the "new" architecture is essentially the old one with hyperparameter retuning; the sub-phase design memo must disallow this. Phase 28 inertia routes (S-C/S-D/S-E/L1/L2/L3 score-axis, R-T2/R1/R2/R3/R4 selection-rule axis, R7-C/L3 regime-feature/loss axis) are all sub-axes of the same LightGBM tabular architecture; A0 changes the architecture itself.

### 12.2 A2 — target redesign — inertia risk **low**

A2 always requires a target spec change, which by definition exits the realised-PnL frame used by Phase 27 / 28.0a / 28.0b. Only very minor target tweaks (e.g., K_FAV 1.5 → 1.4) would risk inertia; the sub-phase design memo must declare a structural target change.

### 12.3 A3 — regime-conditioned modeling — inertia risk **HIGH** (upgraded from medium-high)

A3 risks collapsing into:

- **27.0f R7-C feature widening**: regime as additive features → FALSIFIED. A3 must declare architectural conditioning, not feature-level conditioning.
- **28.0a L3 spread-cost-weighted Huber**: regime as training-time weight → FALSIFIED. A3 must declare architectural conditioning, not loss-level conditioning.
- **28.0b R3 per-pair quantile**: regime (pair) as selection-rule cutoff → FALSIFIED. A3 must declare architectural conditioning, not selection-rule-level conditioning.

A3 is **structurally distinct** from each (architectural conditioning is a different model class), but the **cumulative regime-axis negative evidence** is now substantial. The sub-phase design memo MUST pre-state the architectural-conditioning mechanism and explicitly distinguish it from each of the 3 failed regime-axis attacks.

### 12.4 R-B — different feature axis — inertia risk **medium-high**

R-B risks collapsing into:

- **27.0f R7-C-style regime-statistic widening**: another rolling z-score feature family that fails for the same reason as R7-C. R-B scope amendment must declare a structurally distinct feature class (path-shape / microstructure / multi-TF context — NOT regime statistics).

### 12.5 R-T3 — concentration formalisation — inertia risk **HIGH**

R-T3 risks collapsing into:

- **28.0b R3 per-pair quantile**: R3 already attacked concentration via selection-rule. R-T3 via Clause 2 amendment + cell-shape concentration constraints must declare a structurally distinct mechanism (e.g., per-pair budget caps at cell-construction time, not at selection time). The Clause 2 amendment cost is high relative to the post-28.0b prior.

### 12.6 A1 / A4 — exhausted under tested closed allowlists

A1 is exhausted under the 28.0a closed 3-loss allowlist (L1 / L2 / L3 with α-fixed numerics per PR #337 §4). Revival requires a Phase 28 scope amendment declaring a new closed loss family (non-Huber backbone / additional variants).

A4 is exhausted under the 28.0b closed 4-rule allowlist (R1 / R2 / R3 / R4 with α-fixed numerics per PR #341 §4) plus PR #340 Clause 2 amendment for non-quantile cells. Revival requires a fresh sub-phase design memo with a new rule class structurally distinct from R1 / R2 / R3 / R4.

Both A1 and A4 remain deferred-not-foreclosed in principle but are NOT admissible without amendment.

---

## 13. How each route uses Phase 27 + 28 findings (7-eval picture × route relevance)

| Route | Phase 27 + 28 findings directly attacked | Phase 27 + 28 findings preserved | Notes |
|---|---|---|---|
| **A0** | H-B9 (seam exhausted at this architecture; **7 data points** — strongest evidence) | All 7 findings as historical evidence; S-E ranking signal usable as input | Most ambitious use of findings; architecture change can in principle recover the seam. |
| **A2** | H-B3 partial + open question (target adequacy) + 28.0b "Spearman robust / Sharpe stuck" pattern | S-E ranking signal *if* the new target is comparable | Often produces a new dataset surface; §10 baseline becomes semantically tricky. |
| **A3** | H-B8 (regime-conditioned ≠ regime-feature / regime-loss / regime-rule) | R7-A baseline | R-B-reframing-friendly axis; admits new feature class via scope amendment. **Penalised by 27.0f / 28.0a L3 / 28.0b R3 cumulative regime-axis negative evidence.** |
| R-B | H-B8 (path / microstructure NOT tested) | R7-A baseline; existing closed allowlist contracts | Requires scope amendment first; reframing under A3 / A0 / A2 admissible. |
| R-T3 | concentration hypothesis (post-28.0b R3 negative evidence weakens this further) | Clause 2 contract (if amendment passes) | Below dissent threshold; revival on cumulative-failure trigger only. |

---

## 14. Recommended third mover + 2 dissents

### 14.1 Primary — **A0 architecture redesign**

A0 is recommended as Phase 28's third mover for **eight reasons** (consolidated from §7.8):

1. **Most direct attack on the strengthened binding constraint** H-B9 (7 supporting data points; 7/7 val-selector pattern).
2. **A4 failure directly raised A0 prior** from 25-35 % to 35-45 % (PR #339 §14.2 sequencing logic confirmed).
3. **No further single-axis intervention at this architecture is expected to lift Sharpe** — all 3 channels (B / C / A regime-statistic) exhausted.
4. **Cost-prior ratio is the best** among A0 / A2 / A3.
5. **No mandatory scope amendment** if the architecture stays on inherited R7-A / realised-PnL.
6. **Symmetric information value** — both outcomes routing-decisive.
7. **No inertia risk** — A0 by definition diverges from any Phase 27 / 28 inertia route.
8. **A2 / A3 alternatives have specific obstacles** (A2: scope amendment + §10 misalignment; A3: regime-axis cumulative negative evidence + high inertia risk).

The A0 sub-phase design memo (out of scope here) will pre-state the specific architecture class, the FAIL-FAST baseline reproduction gate, the cell structure (control + candidate cells), and H-C3.

### 14.2 Dissent 1 — **A2 target redesign**

A2 is preserved as dissent 1. The strongest argument for A2 is the 28.0b "Spearman robust / Sharpe stuck" pattern: the score's ranking signal is solid but does not monetize via any selection rule on this target. If the realised-PnL target is the binding misalignment, target redesign is the fix. However:

- A2 always requires scope amendment + auxiliary baseline construction (heavier than A0 setup).
- A2's prior (20-30 %) is below A0's because H-B9 (architecture exhaustion) is more directly supported by the 7-eval picture than target-adequacy is.

A2 is positioned as **"the next move if A0 fails."** A2 can be elevated to primary at the user's discretion (decision rule §16 row 2).

### 14.3 Dissent 2 — **A3 regime-conditioned modeling**

A3 is preserved as dissent 2. The argument for A3 is that H-B8 (regime-conditioned ≠ regime-statistic) remains unresolved and R-B reframing under A3 is the natural Phase 28 home. However:

- A3 has the **highest inertia risk among all active routes** (regime-axis cumulative negative evidence from R7-C / L3 / R3).
- A3 carries scope amendment surface for any R-B reframing.
- A3's structural-failure prior is now higher than at PR #339 §9.6.

A3 can be elevated to primary at the user's discretion (decision rule §16 row 3) under strict inertia-risk pre-stating in the sub-phase design memo.

### 14.4 Why R-B is NOT a dissent

R-B carries a prior (20-30 %) competitive with A2's, but:
- R-B requires its own scope amendment PR before any β-eval can run.
- R-B reframing under A3 (full) makes the two operationally similar.
- A2 and A3 are admissible-at-kickoff A-axes; R-B is a carry-forward route requiring elevation.

R-B remains in §10 / §11 / §14 as Tier 3 (carry-forward; not dissent). Elevation requires explicit user routing decision (§16 row 5).

### 14.5 Why R-T3 is NOT a dissent

R-T3 carries prior 5-15 % — below the dissent threshold (≥ 15-20 % bucket for dissents). R3 28.0b result adds incremental negative evidence to concentration-axis hypothesis. R-T3 remains Tier 3 below-threshold; revival only on cumulative-failure trigger.

---

## 15. Why A0 over A2 / A3 (judgement; post-28.0b updated reasoning)

PR #339 §15 reasoned that A4 was primary because the 6-eval picture's val-selector pattern most directly supported H-B7 (rule misspecified). 28.0b-β falsified H-B7 directly: 4 structurally distinct rule variants all failed. The 7-eval picture now most directly supports **H-B9 (architecture exhaustion)** — and A0 is the route that most directly tests H-B9.

The sequencing logic is preserved from PR #339:

- A4 failure → H-B7 falsified → H-B9 further strengthened → A0 next-move
- A0 failure (if it happens) → H-B9 further reinforced (8 data points) → A2 / A3 / R-B / Phase 28 closure consideration prior all rise
- A0 success → architecture-level fix → PROMISING_BUT_NEEDS_OOS candidate → eventual production deployment path

A0 is **the route whose outcome best informs the next routing decision** regardless of result. This is the same "symmetric information value" reasoning PR #336 §6.8 / PR #339 §14.1 #5 used to support A4 primary — now applied to A0.

The user may override this judgement and elevate A2 / A3 / R-B (or initiate Phase 28 closure consideration) at any time; decision rule §16 records the conditions.

---

## 16. Decision rule — pre-stated thresholds (updated post-28.0b)

Pre-state the conditions under which each route is elevated to primary:

| Condition | Selected third mover |
|---|---|
| 7-eval H-B9 strengthening interpreted as "architecture is the binding constraint" AND A0 cost-prior is best AND no scope amendment needed (if no target reshape) → | **A0 (default primary)** |
| User reads 7-eval "Spearman robust / Sharpe stuck" as "target adequacy is the binding constraint" AND authorises target-spec scope amendment AND accepts §10 baseline misalignment → | **A2 (overrides A0)** |
| User explicitly elevates regime-conditioned modeling with prior > 20 % AND accepts high inertia risk (R7-C / L3 / R3 cumulative regime-axis negative evidence) AND authorises closed-allowlist scope amendment for R-B reframing → | **A3 (overrides A0)** |
| User authorises Clause 2 amendment AND R-T3 prior revised above 20 % AND accepts R3 28.0b negative evidence → | **R-T3 (carry-forward elevation)** |
| User authorises new closed feature allowlist (R7-D / R7-E / R7-F path / microstructure / multi-TF) AND R-B prior is the binding consideration → | **R-B elevation (with reframing under A3 / A0 / A2)** |
| A0 also fails at its β-eval (HYPOTHETICAL; not in scope of this PR) → | **Phase 28 closure consideration** (analogous to PR #333 R-E pattern for Phase 27) |

The default condition (7-eval H-B9 strengthening → A0 primary) is consistent with §14.1.

---

## 17. Open questions / unknowns

Five open questions carried into Phase 28 third-mover decision and not resolved by this routing review:

1. **What specific architecture class for A0?** Hierarchical / multi-task / sequence / regime-conditioned heads — multiple options admissible. The A0 sub-phase design memo pre-states which.
2. **What specific target class for A2 (if elevated)?** Trade-quality (MFE/MAE-based) / risk-adjusted / cost-decomposed / calibrated-by-regime. The A2 sub-phase design memo pre-states which + the auxiliary baseline construction.
3. **A3 vs A0 distinction**: regime-conditioned architectural decomposition (gating / MoE / per-regime training) overlaps with A0's regime-conditioned heads option. The A3 sub-phase design memo must declare which axis it occupies; if it self-identifies as A0-regime-conditioned, then A3 is absorbed.
4. **R-B specific feature class (if elevated)?** Path-shape (MFE/MAE structural features) / microstructure (recent quote micro-changes) / multi-TF context (higher-timeframe regime indicators). The R-B scope amendment PR pre-states which closed allowlist is admitted.
5. **Phase 28 closure prior if A0 also fails**: 7-eval picture + A0 failure would form 8 data points against same-target / same-feature-surface interventions. Phase 28 closure consideration (analogous to PR #333 Phase 27 R-E primary) would become competitive. Not in scope for this PR; pre-stated as decision rule §16 row 6 trigger.

---

## 18. Binding constraints (verbatim)

This routing review preserves every constraint binding at the end of Phase 28.0b:

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
- no A0 / A2 / A3 sub-phase initiation
- no R-B / R-T3 elevation
- R-T1 absorbed-and-falsified under A4 (resolved by PR #342; status preserved here)
- A1 / A4 exhausted under tested closed allowlists (status preserved here)
- no prior verdict modification
- no auto-route after merge

The recommendation is **scope-level only**. The next action requires an explicit separate user routing decision.

---

## 19. References

**Phase 28**:
- PR #335 — Phase 28 kickoff
- PR #336 — Phase 28 first-mover routing review (A1 primary at first-mover)
- PR #337 — Phase 28.0a-α A1 objective redesign design memo
- PR #338 — Phase 28.0a-β A1 objective redesign eval (FALSIFIED_OBJECTIVE_INSUFFICIENT; A1 exhausted)
- PR #339 — Phase 28 post-28.0a routing review (A4 primary; A0 / A2 dissents; A3 Tier 3)
- PR #340 — Phase 28 scope amendment A4 non-quantile cells
- PR #341 — Phase 28.0b-α A4 monetisation-aware selection design memo (R-T1 formal absorption)
- PR #342 — Phase 28.0b-β A4 eval (FALSIFIED_RULE_INSUFFICIENT; R-T1 = FALSIFIED_under_A4; A4 exhausted)

**Phase 27 (evidence anchor)**:
- PR #316 — Phase 27 kickoff
- PR #318 / #321 / #325 / #328 / #332 — five Phase 27 β-evals
- PR #319 / #322 / #326 / #329 / #333 — five Phase 27 routing reviews
- PR #334 — Phase 27 closure memo (5-eval evidence picture; R-T1 / R-B / R-T3 carry-forward source)

**Binding contracts**:
- PR #279 — γ closure
- Phase 22 frozen-OOS contract
- X-v2 OOS gating
- Phase 9.12 production v9 closure tip `79ed1e8` (production v9 20-pair, untouched throughout Phase 27 and Phase 28)

---

*End of `docs/design/phase28_post_28_0b_routing_review.md`.*
