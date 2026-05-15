# Phase 27 — Post-27.0e Routing Review

**Type**: doc-only routing review
**Status**: routes Phase 27 after 27.0e-β S-E quantile family trim eval (PR #328); does NOT initiate any sub-phase
**Branch**: `research/phase27-routing-review-post-27-0e`
**Base**: master @ 0d9eca0 (post-PR #328 / Phase 27.0e-β eval merge)
**Pattern**: analogous to PR #319 / #322 / #326 routing reviews under Phase 27
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal post-27.0e routing review. It consolidates the 4-evidence-point Channel B picture + 27.0e Channel C result, captures the substantively new finding that R-T2 trim made Sharpe WORSE not better, enumerates 9 routing options, presents a decision tree, and introduces H-B6 (top-tail adversarial selection / regime confound in regressor confidence) as a routing-relevant hypothesis. It does NOT by itself authorise any R-B / R-C / R-T1 / R-T3 / R-E sub-phase. The next sub-phase choice requires a separate later user instruction.*

Same approval-then-defer pattern as PR #319 / #322 / #326.

---

## 1. Executive summary — 4-evidence-point Channel B picture + 27.0e Channel C surprise

Phase 27 now has **4 substantive sub-phase β evals** since kickoff (PR #316):

1. **27.0b-β** (Channel B; PR #318) — S-C TIME penalty: REJECT on all 4 α cells; α-monotonic Spearman↑ / Sharpe↓
2. **27.0c-β** (Channel B; PR #321) — S-D calibrated EV: REJECT on both cells; small Spearman lift / Sharpe slightly worse
3. **27.0d-β** (Channel B; PR #325) — S-E regression: **SPLIT_VERDICT**; first H1-meaningful PASS (Spearman +0.4381) but H2 FAIL (Sharpe -0.483; n=184,703)
4. **27.0e-β** (**Channel C**; PR #328) — **R-T2 trim of S-E quantile family**: **SPLIT_VERDICT**; H-B5 outcome PARTIAL_SUPPORT (row 2); Spearman preserved (+0.4381) but **Sharpe got WORSE** (-0.767 at q*=10)

27.0e was the **first selection-rule (Channel C) intervention** in Phase 27. Its result is **substantively new**: trimming the quantile family did **NOT** recover monetisation — it actively made Sharpe worse while preserving the discriminative ranking signal. H-B5's monetisation-transformation-bottleneck reading is partially supported but **the bottleneck is deeper than the q-budget choice**.

This PR introduces **H-B6** (top-tail adversarial selection / regime confound in regressor confidence) as a routing-relevant hypothesis that re-frames the next move toward **feature widening targeted at regime context (R-C)** as the highest-information targeted test.

This PR does **not** select a next sub-phase.

---

## 2. Four-evidence-point table + 27.0e §22 cross-reference

### 2.1 Side-by-side per-phase comparison (D-R1)

| Phase | Channel | Intervention | Top-level verdict | Best test Spearman | Best test Sharpe (val-sel) | Trade count (val-sel) |
|---|---|---|---|---|---|---|
| 26.0d (baseline) | — | none (S-B) | REJECT (+ YES_IMPROVED) | -0.1535 | -0.1732 | 34,626 |
| 27.0b-β | B | S-C α grid | REJECT | +0.0226 (α=1.0) | -0.251 (α=1.0) | 25,357 |
| 27.0c-β | B | S-D calibrated EV | REJECT | -0.1060 | -0.176 | 32,324 |
| 27.0d-β | B | S-E regression | SPLIT_VERDICT | +0.4381 (C-se, q=40) | -0.483 (C-se, q=40) | 184,703 |
| **27.0e-β** | **C** | **S-E + R-T2 trim {5, 7.5, 10}** | **SPLIT_VERDICT** | **+0.4381 (C-se-trimmed)** | **-0.767 (q*=10) WORSE** | **35,439** |

### 2.2 27.0e §22 trimmed-vs-original cross-reference (D-R2; load-bearing for H-B6)

Verbatim from PR #328 §22:

- 27.0d C-se at q=40: test_sharpe = -0.483, n=184,703, Spearman = +0.4381
- 27.0e C-se-trimmed at q=5: val_sharpe even worse than q=10 (val-selection picked q=10 as least-bad)
- 27.0e C-se-trimmed at q=7.5: val_sharpe in between
- 27.0e C-se-trimmed at q=10: test_sharpe = -0.767, n=35,439, Spearman = +0.4381

Trade-count budget audit (PR #328 §13):
- q=5.0: inflation 1.004× — basically baseline-aligned
- q=7.5: inflation 1.501× — under WARN threshold
- q=10.0: inflation 2.000× — exactly at WARN threshold

**Monotonicity reading**: as q decreases (more selective / further into the top tail), Sharpe gets **monotonically worse**. The most-confident top tail of S-E is the most adversarial to realised PnL. This is load-bearing evidence for H-B6 (§3.2).

### 2.3 27.0e C-sb-baseline match check (verbatim from PR #328 §12)

| Metric | Observed | Baseline (27.0b C-alpha0) | Delta | Tolerance | Match |
|---|---|---|---|---|---|
| n_trades | 34,626 | 34,626 | +0 | exact | ✓ |
| Sharpe | -0.17316449693 | -0.1732 | +3.55e-05 | ±1e-4 | ✓ |
| ann_pnl | -204,664.42 | -204,664.4 | -0.022 | ±0.5 pip | ✓ |

Inheritance chain from 27.0d / 27.0c / 27.0b confirmed intact across 4 sub-phases.

---

## 3. Updated hypothesis status (5 prior + 1 NEW)

### 3.1 Hypothesis status table

| Hypothesis | After 27.0d (#326) | After 27.0e (this review) |
|---|---|---|
| H-B1 (P(TIME) regime proxy) | partially weakened | unchanged at score level; **but see H-B6** for regime-confound reading at top-q region |
| H-B2 (R7-A too narrow) | non-falsified | non-falsified; still untested under wider features (R7-B / R7-C) |
| H-B3 (structural mis-alignment under R7-A) | score-axis falsified; Sharpe-axis NOT falsified | unchanged; 27.0e is a Channel C test, not B |
| H-B4 (label/PnL coupling miscalibration) | partially SUPPORTED | unchanged at score level (Spearman preserved); monetisation problem persists |
| **H-B5 (monetisation-transformation bottleneck)** | NEW; routing-relevant | **REFINED** — bottleneck is real but **DEEPER than q-budget choice**. Trimming q alone makes Sharpe worse; selection-rule revision needs a *different kind* of intervention than quantile trim |
| **H-B6 (NEW; top-tail adversarial selection / regime confound in regressor confidence)** | n/a | **NEW; routing-relevant; non-falsified within 27.0e.** Statement below |

### 3.2 H-B6 statement (D-R3 + D-R10; routing-relevant, not a conclusion)

> *The S-E regressor's monotonic Spearman ranking is approximately correct in the bulk (test Spearman +0.4381 generalises OOF + held-out) but is **non-monotonically inverted at the top tail**. The most-confident predictions (top-q region) correspond to feature configurations — high ATR, wide spread, specific pair / direction patterns — where the regressor over-predicts realised PnL because bid/ask executable cost in those high-vol regimes structurally dominates the predicted edge. This is a regime confound **in the regressor's confidence**, not in the multiclass head's class probabilities.*

**Status within 27.0e-β**: **non-falsified, routing-relevant hypothesis, not a conclusion.**

#### Evidence FOR H-B6
- Trim from q=40 (broad selection; n=184,703) → q=10 (narrow top-q; n=35,439) made Sharpe **worse** (-0.483 → -0.767); §2.2 monotonicity reading
- Spearman conserved (+0.4381) — overall ranking is preserved; only the top-tail mapping inverts
- 27.0d feature importance (re-cited from PR #325 §16): ATR (3,295 gain) + spread (2,496 gain) dominate the regressor; pair (2,631 gain) third. Implication: regressor's top-q rows are high-ATR + wide-spread rows where executable cost dominates
- The regressor's strong OOF + held-out Pearson (+0.075 OOF / +0.136 val / +0.114 test) confirms it learns *real* signal — but the signal's monotonicity to realised PnL is broken at the upper tail

#### Evidence AGAINST H-B6 (alternatives)
- Could alternatively be explained by H-B2 (R7-A too narrow): wider features (R7-B microstructure / R7-C regime/context) might let the regressor identify regime-conditioned EV separately. Not yet tested
- Could be a more general statistical artefact (Goodhart-style overfit on val-quantile cutoff)

H-B6 and H-B2 are **discriminable**: R-C (regime/context features) tests H-B6 directly; if H-B6 holds, R-C should produce H2 PASS at some cell.

### 3.3 Q2 axis update (D-R8)

The post-27.0d routing review (#326 §3.3) cited **"trade-rate explosion magnitude"** as the cross-cutting axis for H-B5. After 27.0e-β, this axis is **demoted** to a *consequence*, not the binding cause:

- 27.0e-β trimmed the quantile family to enforce a trade-count budget
- Trade-rate inflation was capped at 2× (q=10 was at exactly 2×; q=5 was at 1×)
- **Sharpe still got worse**, not better

The NEW cross-cutting axis for H-B6 is **top-tail adversarial selection**: the regressor's confidence ordering is anti-monotonic at the upper tail of its own score distribution. Trade-rate explosion was a *symptom* of selecting too broadly; but selecting more narrowly amplified the adversarial mapping because the narrow selection IS the adversarial top tail.

---

## 4. Routing options (9 total)

| ID | Option | Channel | Status / cost |
|---|---|---|---|
| ~~R-A~~ | ~~S-D calibrated EV~~ | B | **CLOSED at PR #321** |
| ~~R-S-E~~ | ~~S-E regression~~ | B | **CLOSED at PR #325** |
| ~~R-T2~~ | ~~Trade-rate-capped quantile-of-val family~~ | C | **CLOSED at PR #328** (PARTIAL_SUPPORT; trim alone does NOT recover monetisation) |
| R-D | Joint R7-B ⊕ S-C α=0.3 | A+B | **deferred, not near-term** |
| **R-B** | R7-B (F1 microstructure) feature widening | A | unchanged; 3-PR sequence (scope amendment + design memo + eval). **NEW relevance**: partial test of H-B6 (does microstructure help regressor avoid the adversarial top-q region?) |
| **R-C** | R7-C (F5 regime/context) feature widening | A | unchanged; 3-PR sequence. **NEW relevance**: **directly tests H-B6** (regime context features should let regressor separate "high-vol high-EV" from "high-vol high-cost"). Highest-information option for H-B6 |
| **R-T1** | S-E threshold / selection redesign | C | tests H-B5 + H-B6 — e.g., absolute-threshold cells at *middle-bulk* score thresholds (avoid top tail), or minimum-confidence cells. Cost: 2-3 PR sequence; clause-2 framing required |
| **R-T3** | Pair-concentration formalisation | C | tests H-B6 indirectly via concentration filter. 3-PR sequence (**scope amendment required**; clause 2 modification) |
| **R-E** | Phase 27 soft close (R5 pattern) | — | **further strengthened** — 4 evidence points; 2 H-B5/B6 PARTIAL_SUPPORT results without a PROMISING outcome. Cost: 1-PR |

### 4.1 Clause-2 admissibility table (D-R9; load-bearing for routing decision)

| Option | Clause-2 status | Clause-6 status | Scope amendment? |
|---|---|---|---|
| **R-B** | clause-2 clean | clause-6 R7-B family addition (per kickoff §8) | **required** for R7-B (analogous to PR #311 / #323) |
| **R-C** | clause-2 clean | clause-6 R7-C family addition (per kickoff §8) | **required** for R7-C (analogous to PR #311 / #323) |
| **R-T1** | clause-2-sensitive; admissible only if framed as parallel diagnostic cells alongside quantile-of-val OR as quantile-family replacement (not new diagnostic-to-formal promotion) | clause-6 clean | depends on framing — design memo decides |
| **R-T3** | **clause 2 violation**: promotes per-pair-Sharpe-contribution from diagnostic-only to formal cell filter | clause-6 clean | **required** for clause 2 modification |
| **R-E** | no clause modifications | no clause modifications | not required |

**R-T1 is the cheapest H-B6 test if framed cleanly under clause 2.** R-C is the cleanest *direct* test of H-B6 but costs more.

---

## 5. Routing decision tree (bullet-tree; no selection in this PR)

The tree is presented for reasoning support; **no selection is made in this PR**.

- **Q1**: Is H-B6 (top-tail adversarial selection / regime confound) the binding mechanism?
  - **YES** → routes that address regime confound directly
    - **Q1a**: Add regime/context features to let regressor separate high-vol-high-EV from high-vol-high-cost rows → **R-C** (cleanest direct test of H-B6; 3-PR sequence; scope amendment required)
    - **Q1b**: Add microstructure features (vol expansion/compression) → **R-B** (partial H-B6 test; 3-PR sequence; scope amendment required)
    - **Q1c**: Address via selection-rule revision targeting *middle-bulk* rows (avoid the adversarial top tail) → **R-T1** (cheaper; 2-3 PR sequence; clause-2 framing required)
  - **NO** → bottleneck is somewhere else
    - Q1d: Concentration is the lever → **R-T3** (scope amendment; clause-2 modification)
    - Q1e: Bottleneck is structural / not addressable in Phase 27 → **R-E** (soft close)
- **Q2**: Is concentration the lever (regardless of H-B6 status)?
  - **YES** → **R-T3** (scope amendment + clause-2 modification required)
  - **NO** → R-T3 not on critical path
- **Q3**: Cost-vs-information ladder
  1. R-E (1 PR; soft close)
  2. R-T1 (2-3 PR; clause-2-clean if framed correctly; tests H-B6 + H-B5 at lower depth)
  3. R-B / R-C / R-T3 (3 PR each; scope-amendment-gated; R-C highest information for H-B6 if H-B6 is correct)
- **Q4 (counterfactual; what would falsify H-B6?)**:
  - R-C producing H2 PASS at some cell → **strong H-B6 support** (regime features fix the top-tail confound)
  - R-T1 middle-bulk absolute-threshold cells producing H1m + H2 PASS → **strong H-B6 support** (avoiding the adversarial top tail fixes it)
  - R-C + R-B + R-T1 all REJECT → **H-B6 falsified**; bottleneck even deeper; route to R-E
- **Q5 (information density)**:
  - R-C is the highest-information option for H-B6 if H-B6 is correct
  - R-T1 is the lowest-cost option that *might* falsify H-B6 cheaply (clause-2-clean framing assumed)
  - R-E is the conservative option after 4 evidence points without a PROMISING outcome

**Combined reading** (no selection): if H-B6 is plausible (and §3.2's evidence FOR is suggestive), **R-C** is the highest-information targeted test of the hypothesis. If cost-conscious, **R-T1** is cheaper and bears on the same hypothesis at lower depth. **R-E** is the conservative option after 4 sub-phases without a PROMISING outcome.

---

## 6. Constraints preserved (verbatim re-state)

### 6.1 Inherited bindings (carried forward unchanged)

- **D-1 binding**: formal realised-PnL uses inherited `_compute_realised_barrier_pnl` (bid/ask executable). S-E regression target uses the same harness.
- **D10 amendment** (per-sub-phase variants; 2-artifact form preserved for any S-E-style follow-on)
- **Verdict ladder** H1-weak / H1-meaningful / H2 / H3 / H4 thresholds unchanged
- **Cross-cell verdict aggregation** (26.0c-α §7.2) — SPLIT_VERDICT_ROUTE_TO_REVIEW branch demonstrated at 27.0d / 27.0e
- **ADOPT_CANDIDATE wall**: H2 PASS → PROMISING_BUT_NEEDS_OOS only. Full A0-A5 8-gate harness in a SEPARATE PR. Unchanged
- **NG#10 / NG#11**: not relaxed
- **γ closure PR #279**: preserved unchanged
- **X-v2 OOS gating**: remains required
- **Production v9 20-pair** (Phase 9.12 tip 79ed1e8): untouched
- **Phase 22 frozen-OOS contract**: preserved
- **Clause 2 diagnostic-only binding**: **load-bearing** for R-T1 / R-T3 framings (per §4.1)

### 6.2 Clause 6 — verbatim from PR #323 §7 (D-R6; canonical source-of-truth)

The canonical source-of-truth is PR #323 §7. From PR #323 forward, all Phase 27 PRs re-quote clause 6 verbatim as:

> *6. Phase 27 scope. Phase 27's primary axes are (a) feature widening beyond the Phase 26 R6-new-A 2-feature allowlist via per-family closed allowlists and (b) score-objective redesign beyond P(TP) / P(TP)-P(SL). Phase 27 is NOT a Phase 25 feature-axis sweep revival. R7-A (inherited from PR #311) is admissible at kickoff; R7-B / R7-C each require a SEPARATE Phase 27 scope-amendment PR; R7-D and R7-Other are NOT admissible under any Phase 27 scope amendment currently on the table. Score-objectives S-A / S-B / S-C are admissible at kickoff for formal evaluation. S-D (calibrated EV) was promoted from admissible-but-deferred to formal at sub-phase 27.0c-β via PR #320. S-E (regression-on-realised-PnL) was promoted from "requires scope amendment" to "admissible at 27.0d-α design memo" via Phase 27 S-E scope-amendment PR #323. S-E uses realised barrier PnL (inherited bid/ask executable, D-1 binding) as the per-row regression target under the FIXED R7-A feature family; LightGBM regression is the default model class but the 27.0d-α design memo may specify alternatives within the regression family. S-Other (quantile regression / ordinal / learn-to-rank) remains NOT admissible. R7-D and R7-Other remain NOT admissible. R7-B / R7-C remain admissible only after their own separate scope amendments. Phase 26 deferred-not-foreclosed items (L-4 / R6-new-B / R6-new-C / Phase 25 F4 / F6 / F5-d / F5-e) are NOT subsumed by Phase 27; they remain under their original phase semantics.*

This routing review does **NOT** amend clause 6. Any change to clause 2 (for R-T3 admissibility) or clause 6 (for R-T1 / R-B / R-C framings beyond their existing tiers) requires a SEPARATE Phase 27 scope-amendment PR.

---

## 7. What this PR will NOT do

- ❌ Authorise any 27.0f / 27.0g sub-phase
- ❌ Authorise any R7-B / R7-C scope amendment (R-B / R-C paths)
- ❌ Authorise R-T1 design memo
- ❌ Authorise R-T3 scope amendment (clause-2 modification)
- ❌ Authorise a Phase 27 soft closure memo (R-E path)
- ❌ Select among R-B / R-C / R-T1 / R-T3 / R-E
- ❌ Modify any prior verdict (Phase 25 / Phase 26 / Phase 27.0b / 27.0c / 27.0d / 27.0e / routing reviews / scope amendments)
- ❌ Modify Phase 27 scope per kickoff §8 / PR #323 clause 6
- ❌ Modify clause 2 diagnostic-only binding (load-bearing for R-T1 / R-T3 framings)
- ❌ Relax the ADOPT_CANDIDATE 8-gate wall
- ❌ Relax NG#10 / NG#11
- ❌ Modify γ closure (PR #279) / X-v2 OOS gating / Phase 22 frozen-OOS contract / production v9 20-pair tip 79ed1e8
- ❌ Pre-approve any production deployment
- ❌ Reopen Phase 26 L-class label-target redesign space
- ❌ Touch `src/`, `scripts/`, `tests/`, `artifacts/`, `.gitignore`, or `MEMORY.md`
- ❌ Auto-route to any next sub-phase after merge

---

## 8. Recommended next-PR-after-this-routing-doc

*Placeholder — to be filled by user choice on route.*

Candidate filenames per option:

- (R-B) `docs/design/phase27_scope_amendment_r7_b.md` — R7-B (F1 microstructure) scope amendment
- (R-C) `docs/design/phase27_scope_amendment_r7_c.md` — R7-C (F5 regime / context) scope amendment
- (R-T1) `docs/design/phase27_0f_alpha_s_e_selection_redesign_design_memo.md` — S-E selection redesign (absolute-threshold middle-bulk cells / minimum-confidence cells) design memo
- (R-T3) `docs/design/phase27_scope_amendment_concentration_formalisation.md` — pair-concentration formalisation scope amendment
- (R-E) `docs/design/phase27_closure_memo.md` — Phase 27 soft closure memo (R5 pattern; PR #315 analogue)

The user picks the route in a separate later instruction.

---

## 9. Sign-off

Phase 27 has produced 4 substantive sub-phase β evals (27.0b / 27.0c / 27.0d / 27.0e) since kickoff. The 4-evidence-point picture confirms:

- **Channel B interventions** (27.0b / 27.0c / 27.0d) hit a ceiling at H-B3 / H-B4 / H-B5: Spearman *can* move (27.0d unlocked +0.44 Spearman) but Sharpe doesn't recover under R7-A
- **Channel C intervention** (27.0e R-T2 trim) made Sharpe **WORSE** while preserving Spearman: the bottleneck is **deeper than the q-budget choice**
- **H-B6** is now the binding routing question: top-tail adversarial selection / regime confound in regressor confidence

The next move must target either H-B6 directly (**R-C** = cleanest direct test; **R-B** = partial test; **R-T1** = cheaper test at lower depth) or close Phase 27 (**R-E**). R-T3 remains available but requires scope amendment (clause 2 modification).

The next move is one of {R-B, R-C, R-T1, R-T3, R-E}; this review does not select.

**This PR stops here.**
