# Phase 27 — Post-27.0d Routing Review

**Type**: doc-only routing review
**Status**: routes Phase 27 after 27.0d-β S-E regression-on-realised-PnL eval (PR #325); does NOT initiate any sub-phase
**Branch**: `research/phase27-routing-review-post-27-0d`
**Base**: master @ 999859f (post-PR #325 / Phase 27.0d-β eval merge)
**Pattern**: analogous to PR #319 (post-27.0b) and PR #322 (post-27.0c) routing reviews under Phase 27
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal post-27.0d routing review. It consolidates the 3-evidence-point Channel B picture (27.0b S-C / 27.0c S-D / 27.0d S-E), captures the 27.0d-specific SPLIT_VERDICT_ROUTE_TO_REVIEW outcome (first H1-meaningful PASS in Phase 27 + monetisation-bottleneck failure mode), enumerates 8 routing options, and presents a decision tree. It does NOT by itself authorise any R-B / R-C / R-T1 / R-T2 / R-T3 / R-E sub-phase. The next sub-phase choice requires a separate later user instruction.*

Same approval-then-defer pattern as PR #319, #322, #316, #320, #323, #324.

---

## 1. Executive summary — 3-evidence-point Channel B picture + new SPLIT outcome

Phase 27 now has **3 substantive Channel B sub-phase β evals** since kickoff (PR #316):

1. **27.0b-β** (PR #318) — S-C TIME penalty (4 α cells; linear in P(TIME)): REJECT on all 4 cells; α-monotonic Spearman↑ / Sharpe↓ (small magnitude)
2. **27.0c-β** (PR #321) — S-D calibrated EV (isotonic + class-scalar weights): REJECT on both cells; Spearman improved +0.047 vs S-B / Sharpe slightly worsened (small magnitude)
3. **27.0d-β** (PR #325) — **S-E regression** (LightGBMRegressor + Huber + R7-A; bypasses class-prob × class-scalar factorisation): **SPLIT_VERDICT_ROUTE_TO_REVIEW**. C-se H1-meaningful PASS (test Spearman **+0.4381**) but H2 FAIL (test Sharpe **-0.483**); C-sb-baseline reproduces 27.0b C-alpha0 baseline exactly within tolerances

The **wrong-direction monotonicity is now expressed at much wider amplitude**: Spearman lift roughly ×9 vs 27.0c, Sharpe deterioration roughly ×3 vs 27.0c. The 3-evidence-point picture confirms the wrong-direction pattern is **mechanistically robust** across three structurally different Channel B interventions.

The 27.0d C-se outcome adds a **substantively new finding**: Phase 27 *can* produce H1-meaningful score-ranking signal under R7-A. What fails is the **monetisation transformation** from ranking → executable Sharpe under the inherited quantile-of-val selection rule. This is the basis for new hypothesis H-B5 (§3).

This PR enumerates the routing space and presents a decision tree. It does **not** select a next sub-phase.

---

## 2. Three-evidence-point + 27.0d split-verdict + §18 diagnostic cross-reference

### 2.1 Side-by-side per-phase comparison (D-R1)

| Phase | Channel B intervention | Top-level verdict | Best test Spearman | Best test Sharpe (val-sel) | Trade count (val-sel) |
|---|---|---|---|---|---|
| 26.0d (baseline) | none (S-B) | REJECT (+ YES_IMPROVED) | -0.1535 | -0.1732 | 34,626 |
| 27.0b-β | S-C α grid {0.0, 0.3, 0.5, 1.0} | **REJECT** | +0.0226 (α=1.0) | -0.251 (α=1.0) | 25,357 (α=1.0) |
| 27.0c-β | S-D calibrated EV | **REJECT** | -0.1060 (S-D) | -0.176 (S-D) | 32,324 |
| **27.0d-β** | **S-E regression** | **SPLIT_VERDICT_ROUTE_TO_REVIEW** | **+0.4381 (C-se)** | **-0.483 (C-se)** | **184,703 (C-se)** |

### 2.2 27.0d per-cell verdict (verbatim from PR #325 §10)

- **C-se** (S-E regressor.predict): `REJECT_BUT_INFORMATIVE_FLAT` (H1m_PASS / H2_FAIL / H3_FAIL)
- **C-sb-baseline** (raw P(TP)-P(SL)): `REJECT_NON_DISCRIMINATIVE` (H1_WEAK_FAIL)
- Cells agree: **False**
- Aggregate verdict: **SPLIT_VERDICT_ROUTE_TO_REVIEW**
- Val-selection picks C-sb-baseline (val_sharpe -0.186 > C-se's -0.573) → formal top-level verdict = REJECT_NON_DISCRIMINATIVE

### 2.3 27.0d §18 OOF + per-split correlation diagnostic cross-reference (D-R2)

Verbatim from PR #325 §18 (DIAGNOSTIC-ONLY; not in formal verdict):

| Source | n | Pearson | Spearman |
|---|---|---|---|
| OOF aggregate | (5-fold; ~2.94M rows) | +0.0748 | **+0.3836** |
| train (refit) | 2,941,032 | (refit train; see PR #325 §18) | (refit train) |
| val | 517,422 | **+0.1363** | (per PR #325 §18) |
| test | 597,666 | **+0.1142** | (per PR #325 §18) |

- 5-fold OOF: **5/5 positive Pearson folds** — generalisation signal present per fold
- Held-out val + test both produce positive Pearson — regressor learns *real* predictive signal that generalises

This is load-bearing for H-B5 (§3.5): the regressor produces a meaningful per-row ranking; the failure is not the predictive signal itself.

### 2.4 27.0d C-sb-baseline match check (verbatim from PR #325 §12)

| Metric | Observed | Baseline (27.0b C-alpha0) | Delta | Tolerance | Match |
|---|---|---|---|---|---|
| n_trades | 34,626 | 34,626 | +0 | exact | ✓ |
| Sharpe | -0.17316449693 | -0.1732 | +3.55e-05 | ±1e-4 | ✓ |
| ann_pnl | -204,664.42 | -204,664.4 | -0.022 | ±0.5 pip | ✓ |

Inheritance chain from 27.0c / 27.0b / 26.0d confirmed intact. The wrong-direction Sharpe pattern is therefore not a wiring artefact.

---

## 3. Updated hypothesis status (4 prior + 1 NEW)

### 3.1 Hypothesis status table

| Hypothesis | After 27.0c (#322) | After 27.0d (this review) |
|---|---|---|
| H-B1 (P(TIME) regime proxy) | partially weakened | unchanged (S-E does not directly test) |
| H-B2 (R7-A too narrow) | non-falsified | non-falsified; S-E shows R7-A *is sufficient for ranking* (test Spearman +0.44) but the monetisation question is still R7-A-conditioned |
| H-B3 (structural mis-alignment under R7-A) | load-bearing | **score-axis falsified** by S-E (+0.44 Spearman). **Sharpe-axis NOT falsified.** Bifurcation: multiclass head with per-class scalar weighting limited score-ranking (S-D failed); regressor unlocks ranking (S-E succeeds). The wrong-direction Sharpe is *independent* of the score head structure |
| H-B4 (label/PnL coupling miscalibration not fixable by class-scalar) | non-falsified, NEW at #322 | **partially SUPPORTED** — bypassing class-scalar factorisation via direct regression DID unlock H1-meaningful ranking. Not fully proven (H1m PASS coexists with H2 FAIL; ranking ≠ monetisation) |
| **H-B5 (NEW; monetisation-transformation bottleneck)** | n/a | **NEW; routing-relevant; non-falsified within 27.0d.** Claim below |

### 3.2 H-B5 statement (NEW; D-R3)

> *The wrong-direction Sharpe pattern observed across 27.0b / 27.0c / 27.0d is mechanistically dominated by the inherited **quantile-of-val cell-selection's response to a wider-spread score function**, NOT by the score-objective per se. A discriminative ranking (real per-row signal generalising OOF + held-out) + a top-q selection on val + an **unconstrained trade count** produces a **trade-rate explosion** that overwhelms per-trade alpha. A Channel C (selection-rule / cell-rule) intervention may resolve the wrong direction independently of further Channel A or Channel B work.*

**Status within 27.0d-β**: **non-falsified, routing-relevant hypothesis, not a conclusion.** Evidence for H-B5 within 27.0d:

- S-E's positive OOF Pearson (+0.0748) and Spearman (+0.3836) demonstrate the regressor learns real signal
- Held-out val Pearson +0.1363 / test Pearson +0.1142 generalise
- Yet val-selected q* = 40% picks 184,703 trades (5.4× the 34,626 baseline)
- Per-trade EV collapses → realised Sharpe -0.483

**Evidence against H-B5** (or alternative explanation):
- The same trade-rate explosion appeared at lower magnitude in 27.0b α≥0.3 cells (USD_JPY concentration collapse to ~100%; PR #319 §2.2)
- The "wrong-direction Sharpe with informative score" pattern might be a *structural* monetisation constraint under R7-A (not selection-rule contingent)

H-B5 is **routing-relevant**: it suggests R-T1 / R-T2 / R-T3 (selection-rule interventions) as the targeted next test. If H-B5 falsifies under R-T2 (trimming the quantile family produces the same wrong-direction Sharpe), then the bottleneck is deeper than selection-rule and routing pivots to R-B / R-C / R-E.

### 3.3 Q2 axis update — "trade-rate explosion magnitude" replaces "concentration collapse" (D-R8)

Post-27.0b §3.2 / #322 cited "concentration collapse" as the secondary axis of α-monotonicity. That axis **did not generalise to 27.0c** (S-D's USD_JPY share 0.7760 was only modestly above baseline 0.7139; no collapse to ~100%).

The cross-cutting axis that **does generalise** across 27.0b α>0 / 27.0d C-se is **trade-rate explosion magnitude**:

| Cell | val-selected q% | val_n_trades | trade-rate multiplier vs baseline 25,881 |
|---|---|---|---|
| baseline 27.0b α=0.0 / 27.0c C-sb / 27.0d C-sb | 5% | 25,881 | 1.0× |
| 27.0b α=0.3 / 0.5 / 1.0 | 5% (degenerate) | 25,886 / 25,872 / 25,890 | ~1.0× (same q; but concentrated 100% USD_JPY) |
| 27.0c C-sd | 5% | 25,887 | 1.0× |
| **27.0d C-se** | **40%** | **206,985** | **8.0×** |

So the *new* axis is: 27.0d's score-function widened predictive spread, and the inherited val-quantile selection responded by picking a much higher q with much more trades. H-B5 is the hypothesis that this is the binding failure mechanism. Concentration collapse and trade-rate explosion are two faces of the same selection-rule response.

---

## 4. Routing options (8 total; D-R4)

| ID | Option | Channel | Status / cost |
|---|---|---|---|
| ~~R-A~~ | ~~S-D calibrated EV~~ | B | **CLOSED at #321 (REJECT)** |
| ~~R-S-E~~ | ~~S-E regression~~ | B | **CLOSED at #325 (SPLIT_VERDICT)** |
| R-D | Joint R7-B ⊕ S-C α=0.3 | A + B | **deferred — not near-term**; superseded by S-E's H1m PASS (score-axis is not the binding gap); joint is high-cost / low-information |
| **R-B** | R7-B (F1 microstructure) feature widening | A | unchanged; admissible after scope amendment (3-PR sequence) |
| **R-C** | R7-C (F5 regime / context) feature widening | A | unchanged; admissible after scope amendment (3-PR sequence) |
| **R-T1** *(NEW)* | S-E threshold / selection redesign | **C (selection rule)** | tests H-B5; e.g., absolute-threshold or minimum-confidence cell variants for S-E |
| **R-T2** *(NEW)* | trade-rate-capped quantile-of-val family for S-E | **C (selection rule)** | tests H-B5; narrowest test — trim quantile family for S-E only (e.g., {5, 7.5, 10}) |
| **R-T3** *(NEW)* | pair-concentration formalisation as cell filter | **C (cell selection)** | tests H-B5 + concentration mechanism; **requires scope amendment** (clause 2 lifts pair-concentration from diagnostic-only to formal) |
| **R-E** | Phase 27 soft close (R5 pattern) | — | modified — 3 evidence points now; **but** S-E's H1m PASS is substantively new → soft close may be premature; single-PR cost |

### 4.1 Cost / sequencing notes

- **R-B**: 3-PR sequence (scope amendment + design memo + eval); per kickoff §8 / PR #323 clause 6
- **R-C**: 3-PR sequence (analogous to R-B)
- **R-T1**: 2-PR sequence (design memo + eval) IF framed as "additional selection variants alongside inherited quantile-of-val for S-E only". 3-PR sequence if it modifies cross-cell aggregation logic. Framing decision lives in the design memo
- **R-T2**: 2-PR sequence (design memo + eval); arguably the cleanest because it is a *trim* of the inherited 5-quantile family for S-E only (a quantile-family choice, not a new formal verdict input)
- **R-T3**: **scope amendment required** (3-PR sequence: scope amendment + design memo + eval). Clause 2 binding: per-pair Sharpe contribution is diagnostic-only. Promoting concentration to a formal cell filter is a clause 2 change
- **R-E**: 1-PR (Phase 27 soft closure memo; R5 pattern; PR #315 analogue)
- **R-D**: deferred; not estimated

### 4.2 Clause-2 admissibility notes (D-R9; load-bearing)

Clause 2 (carried verbatim through all Phase 27 sub-phases since kickoff §8) states:

> *Calibration / threshold-sweep / directional-comparison / classification-quality / feature-importance / per-pair-Sharpe-contribution columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.*

This binding constrains R-T1 / R-T2 / R-T3 framings:

- **R-T2 is the cleanest under clause 2.** Trimming the val-quantile family for S-E from {5, 10, 20, 30, 40} to {5, 7.5, 10} is a *quantile-family choice*, not a new diagnostic-to-formal promotion. The selection rule (quantile-of-val with max-val-sharpe per cell) is unchanged; only the family of admissible q is narrowed. This sits within the existing kickoff §8 / PR #323 clause 6 scope and does NOT require a scope amendment
- **R-T1** is admissible under clause 2 only if framed as *additional* cell variants (absolute-threshold cells or minimum-confidence cells) **in parallel with** the inherited quantile-of-val family — analogous to 27.0b §20's absolute-threshold sweep. Those variants must remain diagnostic-only OR the design memo must explicitly argue they are not threshold-sweeps under clause 2's prohibition. The cleanest design-memo framing keeps quantile-of-val as the formal verdict source and adds R-T1 variants as parallel cells
- **R-T3 explicitly requires scope amendment.** Promoting per-pair-Sharpe-contribution from diagnostic-only to a formal cell filter is a clause 2 modification. Per kickoff §8 / PR #323 / precedent PR #311, a clause modification needs its own scope-amendment PR

The cleanest sequencing if H-B5 is accepted is therefore **R-T2 first** (narrowest test, no scope amendment, 2-PR cost), then escalate to R-T1 or R-T3 only if R-T2's results suggest further selection-rule revision is needed.

---

## 5. Routing decision tree (bullet-tree; no selection in this PR)

The tree is presented for reasoning support; **no selection is made in this PR**.

- **Q1**: Is the binding failure under R7-A **structural at the score-objective level** (H-B3 at the Sharpe axis)?
  - **NO** — S-E's H1m PASS rules this out at the *score* level. Channel B is informative; the failure is elsewhere
  - Implication: routes that test Channel B further (R-D) are **deprioritised**
- **Q2**: Is the binding failure at the **monetisation transformation** (H-B5)?
  - **YES** → R-T1 / R-T2 / R-T3 are the targeted tests
    - **Q2a**: Trim the quantile family for S-E only → **R-T2** (narrowest; cleanest under clause 2)
    - **Q2b**: Add absolute-threshold or minimum-confidence cell variants → **R-T1**
    - **Q2c**: Formalise pair-concentration as a cell filter → **R-T3** (requires scope amendment)
  - **NO** → routes are R-B / R-C / R-E
- **Q3**: Is **feature widening** still admissible as a parallel question (independent of Q2)?
  - **YES** → R-B / R-C remain open even if Q2 = YES
  - **NO** → R-E gains weight
- **Q4 (cost vs information ladder)**: from cheapest to most expensive:
  1. R-E (1 PR; soft closure memo)
  2. R-T2 (2 PR; narrowest selection-rule test)
  3. R-T1 (2-3 PR; moderate selection-rule test)
  4. R-B / R-C / R-T3 (3 PR each; scope-amendment-gated)
- **Q5 (counterfactual)**: what would falsify H-B5?
  - R-T2 producing the *same* wrong-direction Sharpe pattern across all q ∈ {5, 7.5, 10} for S-E would falsify H-B5. The bottleneck is then deeper than selection-rule; routes pivot to R-B / R-C / R-E
  - R-T2 producing H1m PASS + H2 PASS at q=5 or q=7.5 would *strongly support* H-B5 and Phase 27's ADOPT_CANDIDATE pathway becomes live (PROMISING_BUT_NEEDS_OOS → separate A0-A5 8-gate PR per kickoff §10)
- **Q6 (admissibility under clause 2)**:
  - R-T2 (trim quantile family) is cleanest under clause 2 — no scope amendment
  - R-T1 needs explicit clause-2 framing in its design memo (parallel cells vs replacement cells)
  - R-T3 explicitly requires scope amendment to lift per-pair-Sharpe-contribution from diagnostic to formal

**Combined reading** (no selection): if Q2 = YES, prefer R-T2 first (narrowest, lowest cost, cleanest clause-2 compatibility). If R-T2 falsifies H-B5, escalate to R-B / R-C / R-T3 / R-E. If Q2 = NO, route to R-B / R-C / R-E directly.

---

## 6. Constraints preserved (verbatim re-state)

### 6.1 Inherited bindings (carried forward unchanged)

- **D-1 binding**: formal realised-PnL uses inherited `_compute_realised_barrier_pnl` (bid/ask executable); S-E target uses the same harness
- **D10 amendment** (per-sub-phase variants; 2-artifact form preserved from 27.0d-α §7.5 for any S-E-style follow-on)
- **Verdict ladder** H1-weak / H1-meaningful / H2 / H3 / H4 thresholds (0.05 / 0.10 / Sharpe ≥0.082 ∧ ann_pnl ≥180 / >−0.192 / ≥0). Unchanged.
- **Cross-cell verdict aggregation** (26.0c-α §7.2): SPLIT_VERDICT_ROUTE_TO_REVIEW branch *demonstrated at 27.0d*; routing review is the resolution path
- **ADOPT_CANDIDATE wall**: H2 PASS → PROMISING_BUT_NEEDS_OOS only. Full A0-A5 8-gate harness required in a SEPARATE PR
- **NG#10 / NG#11**: not relaxed
- **γ closure PR #279**: preserved unchanged
- **X-v2 OOS gating**: remains required
- **Production v9 20-pair** (Phase 9.12 tip 79ed1e8): untouched
- **Phase 22 frozen-OOS contract**: preserved
- **Clause 2 diagnostic-only binding**: **load-bearing** for R-T1 / R-T2 / R-T3 framings (per §4.2)

### 6.2 Clause 6 — verbatim from PR #323 §7 (D-R6; canonical source-of-truth)

The canonical source-of-truth is PR #323 §7. From PR #323 forward, all Phase 27 PRs re-quote clause 6 verbatim as:

> *6. Phase 27 scope. Phase 27's primary axes are (a) feature widening beyond the Phase 26 R6-new-A 2-feature allowlist via per-family closed allowlists and (b) score-objective redesign beyond P(TP) / P(TP)-P(SL). Phase 27 is NOT a Phase 25 feature-axis sweep revival. R7-A (inherited from PR #311) is admissible at kickoff; R7-B / R7-C each require a SEPARATE Phase 27 scope-amendment PR; R7-D and R7-Other are NOT admissible under any Phase 27 scope amendment currently on the table. Score-objectives S-A / S-B / S-C are admissible at kickoff for formal evaluation. S-D (calibrated EV) was promoted from admissible-but-deferred to formal at sub-phase 27.0c-β via PR #320. S-E (regression-on-realised-PnL) was promoted from "requires scope amendment" to "admissible at 27.0d-α design memo" via Phase 27 S-E scope-amendment PR #323. S-E uses realised barrier PnL (inherited bid/ask executable, D-1 binding) as the per-row regression target under the FIXED R7-A feature family; LightGBM regression is the default model class but the 27.0d-α design memo may specify alternatives within the regression family. S-Other (quantile regression / ordinal / learn-to-rank) remains NOT admissible. R7-D and R7-Other remain NOT admissible. R7-B / R7-C remain admissible only after their own separate scope amendments. Phase 26 deferred-not-foreclosed items (L-4 / R6-new-B / R6-new-C / Phase 25 F4 / F6 / F5-d / F5-e) are NOT subsumed by Phase 27; they remain under their original phase semantics.*

This routing review does **NOT** amend clause 6. Any change to clause 2 (for R-T3 admissibility) or clause 6 (for R-T1 / R-T2 framing) requires a SEPARATE Phase 27 scope-amendment PR.

---

## 7. What this PR will NOT do

- ❌ Authorise any 27.0e / 27.0f sub-phase
- ❌ Authorise any R7-B / R7-C scope amendment
- ❌ Authorise R-T3 scope amendment (per-pair concentration formalisation)
- ❌ Authorise R-T1 / R-T2 design memos
- ❌ Authorise a Phase 27 soft closure memo (R-E path)
- ❌ Select among R-B / R-C / R-T1 / R-T2 / R-T3 / R-E
- ❌ Modify Phase 27 scope per kickoff §8 / PR #323 clause 6
- ❌ Modify clause 2 diagnostic-only binding (load-bearing for R-T-family framings)
- ❌ Relax the ADOPT_CANDIDATE 8-gate wall
- ❌ Relax NG#10 / NG#11
- ❌ Modify γ closure (PR #279) / X-v2 OOS gating / Phase 22 frozen-OOS contract / production v9 20-pair tip 79ed1e8
- ❌ Pre-approve any production deployment
- ❌ Modify any prior verdict (Phase 25 / Phase 26 / Phase 27.0b / 27.0c / 27.0d / routing reviews / scope amendments)
- ❌ Reopen Phase 26 L-class label-target redesign space
- ❌ Touch `src/`, `scripts/`, `tests/`, `artifacts/`, `.gitignore`, or `MEMORY.md`
- ❌ Auto-route to any next sub-phase after merge

---

## 8. Recommended next-PR-after-this-routing-doc

*Placeholder — to be filled by user choice on route.*

Candidate filenames per option:

- (R-B) `docs/design/phase27_scope_amendment_r7_b.md` — R7-B (F1 microstructure) scope amendment
- (R-C) `docs/design/phase27_scope_amendment_r7_c.md` — R7-C (F5 regime/context) scope amendment
- (R-T1) `docs/design/phase27_0e_alpha_s_e_selection_redesign_design_memo.md` — S-E threshold / selection redesign design memo
- (R-T2) `docs/design/phase27_0e_alpha_s_e_quantile_family_trim_design_memo.md` — S-E quantile-family-trim design memo (cleanest under clause 2)
- (R-T3) `docs/design/phase27_scope_amendment_concentration_formalisation.md` — per-pair-concentration formalisation scope amendment
- (R-E) `docs/design/phase27_closure_memo.md` — Phase 27 soft closure memo (R5 pattern; PR #315 analogue)

The user picks the route in a separate later instruction.

---

## 9. Sign-off

Phase 27 has produced 3 substantive Channel B sub-phase β evals (27.0b-β / 27.0c-β / 27.0d-β) since kickoff. The 3-evidence-point picture confirms the wrong-direction Sharpe pattern is **mechanistically robust** across structurally different Channel B interventions. The 27.0d C-se outcome adds the first H1-meaningful PASS in Phase 27 and the new H-B5 (monetisation-transformation bottleneck) hypothesis.

The next move is one of {R-B, R-C, R-T1, R-T2, R-T3, R-E} per §4 / §5; this review does not select.

**This PR stops here.**
