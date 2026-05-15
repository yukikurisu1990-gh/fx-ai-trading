# Phase 27 — Post-27.0c Routing Review

**Type**: doc-only routing review
**Status**: routes Phase 27 after 27.0c-β S-D calibrated EV eval (PR #321); does NOT initiate any sub-phase
**Branch**: `research/phase27-routing-review-post-27-0c`
**Base**: master @ 0c34ebe (post-PR #321 / Phase 27.0c-β eval merge)
**Pattern**: analogous to PR #319 (post-27.0b routing review) under Phase 27 and PR #310 / #314 (post-26.0c / 26.0d) under Phase 26
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal post-27.0c routing review. It consolidates the two-evidence-point Channel B picture (27.0b-β S-C TIME penalty + 27.0c-β S-D calibrated EV both REJECT with the same Spearman↑ / Sharpe↓ wrong-direction pattern under R7-A), enumerates routing options, and presents a decision tree. It does NOT by itself authorise any R-B / R-C / R-D / R-S-E / R-E sub-phase. The next sub-phase choice requires a separate later user instruction.*

Same approval-then-defer pattern as PR #310, #314, #316, #317, #319, #320.

---

## 1. Executive summary — two-evidence-point Channel B picture

Phase 27 has now produced **two substantive Channel B sub-phase β evals** since kickoff (PR #316):

1. **27.0b-β** (PR #318) — S-C TIME penalty (4 α cells; structurally linear in P(TIME)): REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL on all 4 cells. α-monotonic Spearman↑ / Sharpe↓.
2. **27.0c-β** (PR #321) — S-D calibrated EV (isotonic per class + per-class realised-PnL weights; structurally nonlinear): REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL on both cells. S-D's Spearman improves by **+0.047** vs S-B baseline (-0.1060 vs -0.1535) but realised Sharpe is **slightly worse** (-0.176 vs -0.173) and n_trades drops **6.6 %** (32,324 vs 34,626).

**The two evidence points reproduce the same core wrong-direction pattern** through two structurally different Channel B interventions: score-objective redesign under R7-A moves the formal ranking metric in the correct direction but moves realised executable Sharpe in the wrong monetisation direction.

The C-sb-baseline match check in PR #321 PASSED (n_trades exact / Sharpe within ±1e-4 / ann_pnl within ±0.5 pip); the inheritance chain from 27.0b / 26.0d / 26.0c is confirmed intact. The wrong-direction pattern is therefore not a wiring artefact.

This PR enumerates the routing space and presents a decision tree. It does **not** select a next sub-phase.

---

## 2. Two-evidence-point table (verbatim from PR #318 / PR #321)

| Phase | Channel B intervention | Verdict | Best test Spearman | Best test Sharpe (val-sel) | Pattern |
|---|---|---|---|---|---|
| 26.0d (R7-A baseline) | none (S-B) | REJECT (+ YES_IMPROVED) | -0.1535 | -0.1732 | n/a (baseline) |
| **27.0b-β** | S-C α grid {0.0, 0.3, 0.5, 1.0} | **REJECT_NON_DISCRIMINATIVE** | +0.0226 (α=1.0) | -0.251 (α=1.0) | Spearman↑ / Sharpe↓ as α↑ |
| **27.0c-β** | S-D calibrated EV | **REJECT_NON_DISCRIMINATIVE** | -0.1060 (S-D) | -0.176 (S-D) | Spearman↑ / Sharpe↓ vs S-B |

### 2.1 27.0c-β per-cell val-selected (verbatim from PR #321 §7 / §8)

| cell | val_sharpe | val_n | test_sharpe | test_n | test_spearman |
|---|---|---|---|---|---|
| C-sd (S-D) | -0.190 | 25,887 | -0.176 | 32,324 | -0.1060 |
| C-sb-baseline (S-B raw) | -0.186 | 25,881 | -0.173 | 34,626 | -0.1535 |

Val-selected = **C-sb-baseline** (S-B is val-better than S-D; verdict source is the S-B branch).

### 2.2 Pair concentration cross-reference (Q2 axis)

For Q2 (§5 below), the second axis observed in 27.0b — USD_JPY concentration collapse to ~100% as α↑ — does **not replicate** in 27.0c.

**27.0b-β §17 (verbatim from PR #318)** — top-pair share per α cell:

| cell | α | val_top_share | test_top_share |
|---|---|---|---|
| C-alpha0 | 0.0 | 0.8685 | 0.7139 |
| C-alpha03 | 0.3 | 1.0000 | 0.9998 |
| C-alpha05 | 0.5 | 1.0000 | 1.0000 |
| C-alpha10 | 1.0 | 1.0000 | 1.0000 |

**27.0c-β §14 (verbatim from PR #321)** — top-pair share per cell:

| cell | val_top_share | test_top_share |
|---|---|---|
| C-sd (S-D) | 0.8877 | **0.7760** |
| C-sb-baseline (S-B raw) | 0.8685 | 0.7139 |

S-D's test USD_JPY share (0.7760) is only modestly above the S-B baseline (0.7139), **not** the ~100% collapse observed in 27.0b at α ≥ 0.3. The "concentration collapse" axis of α-monotonicity is **specific to S-C with α > 0** and does **not** generalise to S-D. The core Spearman↑ / Sharpe↓ pattern does generalise.

---

## 3. Interpretation framework — hypotheses after two evidence points

### 3.1 H-B3 (structural mis-alignment) — elevated to load-bearing under R7-A

Two structurally different Channel B interventions (S-C linear in P(TIME); S-D nonlinear via isotonic + per-class realised-PnL weights) under R7-A both produced wrong-direction Sharpe with improved Spearman. This is no longer a one-off; under R7-A, **no Channel B intervention has yet produced any Sharpe-positive direction**, while both have improved Spearman.

H-B3 from #319 §3.4 was a *hypothesis* after one evidence point. After two, it is the **load-bearing reading under R7-A**: the multiclass head + L-1 label set under R7-A may not admit any monotone-correct score-objective for realised PnL. This does not yet say *why*; §3.4 introduces a specific mechanism (H-B4).

### 3.2 H-B2 (R7-A too narrow) — remains non-falsified

Both 27.0b and 27.0c were R7-A-conditioned (kickoff §4 / #320 §2 binding). The two evidence points test Channel B **under R7-A**; they do not discriminate between H-B2 and H-B3. H-B2 predicts that wider features (R7-B / R7-C) might allow Channel B to align with realised PnL.

Until a wider-feature Channel B run is performed, H-B2 remains non-falsified. The R-B / R-C / R-D routes test it.

### 3.3 H-B1 (P(TIME) as low-vol / range-regime proxy) — partially weakened

27.0c diagnostic exposes the realised-PnL expectation per class on train: Ê[PnL|TP] = +9.82, Ê[PnL|SL] = -5.67, **Ê[PnL|TIME] = +1.57**. Under the regime-proxy reading of H-B1 (TIME ≈ low-vol/range where executable PnL is low), Ê[PnL|TIME] should be near 0 or negative; instead it is clearly positive.

This partially weakens H-B1 but does not falsify it cleanly — the isotonic shift for TIME is -0.25 (raw head over-predicts TIME), so the head's TIME signal may still be confounded with regime in ways the per-class scalar Ê[PnL|TIME] hides. H-B1 remains a routing-relevant hypothesis; R-C (regime/context features) is the targeted test.

### 3.4 H-B4 (label/PnL coupling miscalibration) — NEW, surfaced by 27.0c diagnostic

**Statement**: the multiclass head's class probabilities under R7-A are miscalibrated relative to realised barrier PnL in a way that **cannot be fixed by per-class scalar weights** (i.e., not by S-D's per-class Ê[PnL|c] structure).

**Evidence within 27.0c-β (DIAGNOSTIC-ONLY)**:
- Substantial isotonic shifts per class: TP -0.139, SL +0.389, TIME -0.250 — raw multiclass head systematically over-predicts TP and TIME and under-predicts SL
- S-D still improves Spearman but worsens Sharpe → the per-class scalar weighting Σ_c P_cal(c) · Ê[PnL|c] is insufficient to recover monetisation alignment

**Status within 27.0c-β**: **non-falsified, routing-relevant hypothesis, not a conclusion.** H-B4 is a more specific form of H-B3 — it predicts a particular mechanism (per-row PnL miscalibration not absorbed by class-conditional means) but does not rule out the broader H-B3 (some structural mis-alignment not captured by class-conditional weighting). Discriminating H-B4 from H-B3 requires a Channel B intervention that does not rely on per-class scalar weighting — e.g., a regression model trained on realised PnL per row (S-E).

If H-B4 holds, then a per-row regression head (S-E) is the natural Channel B test, since it bypasses the class-prob × class-scalar factorisation entirely.

### 3.5 Hypothesis status summary

| Hypothesis | After 27.0b only (#319) | After 27.0c (this review) |
|---|---|---|
| H-B1 (P(TIME) regime proxy) | non-falsified | **partially weakened** (Ê[PnL|TIME]=+1.57; not aligned with low-PnL prediction) |
| H-B2 (R7-A too narrow) | non-falsified | non-falsified (not yet tested under wider features) |
| H-B3 (structural mis-alignment) | one-of-three hypothesis | **load-bearing under R7-A** (2 evidence points, 2 distinct interventions) |
| H-B4 (label/PnL coupling miscalibration) | n/a | **NEW; non-falsified; routing-relevant** |

---

## 4. Routing options (6 options; R-A struck through)

Routing options are taken forward from #319 §4 with status updates after 27.0c-β evidence.

| ID | Option | What it tests | Status / cost |
|---|---|---|---|
| ~~R-A~~ | ~~S-D calibrated EV (one cell)~~ | ~~H-B3 / Channel B under R7-A~~ | **CLOSED — completed by 27.0c-β (PR #321); REJECT** |
| **R-B** | R7-B feature widening (R7-A + Phase 25 F1 microstructure) | H-B2 / Channel A under microstructure | scope-amendment PR + design memo + eval (3-PR sequence) |
| **R-C** | R7-C feature widening (R7-A + Phase 25 F5 regime / context) | H-B1 + H-B2 / Channel A under regime | scope-amendment PR + design memo + eval (3-PR sequence) |
| **R-D** | Joint R7-B ⊕ S-C α=0.3 one-cell | A + B together; H-B2 under microstructure with TIME-aware score | scope-amendment PR + joint design memo + eval (3-PR sequence) |
| **R-S-E** *(NEW)* | S-E regression-on-realised-PnL | H-B4 / model-class change (multiclass → regression) bypassing per-class scalar weighting | scope-amendment PR + design memo + eval (3-PR sequence); per kickoff §5 requires model-class scope amendment |
| **R-E** | Phase 27 soft close (R5 pattern) | Concede Channel B under R7-A is exhausted | **strengthened** — now backed by 2 evidence points; single-PR cost (analogous to PR #315 Phase 26 closure) |

Per kickoff §8, **R7-B / R7-C scope amendments** are required for R-B / R-C / R-D. Per kickoff §5, **S-E requires a separate scope-amendment PR** (model-class change). R-E is the only single-PR option.

R-A is included for completeness with strikethrough — completed at PR #321; not a future option.

---

## 5. Routing decision tree (bullet-tree; no selection in this PR)

The tree is presented for reasoning support; **no selection is made in this PR**.

- **Q1**: Do we believe Channel B **under R7-A** is structurally exhausted (i.e., H-B3 is load-bearing as in §3.1)?
  - **YES** → next move is NOT another Channel B intervention under R7-A
    - **Q1a**: Test if Channel A (feature widening) unlocks Channel B?
      - microstructure first → **R-B** (Phase 25 F1)
      - regime/context first → **R-C** (Phase 25 F5)
      - both jointly with TIME-aware score → **R-D** (R7-B ⊕ S-C α=0.3)
    - **Q1b**: Test if model-class change (regression) bypasses Channel B alignment under R7-A entirely?
      - → **R-S-E** (model-class scope amendment; tests H-B4 directly)
    - **Q1c**: Concede Channel B under R7-A?
      - → **R-E** (Phase 27 soft close)
  - **NO** → Channel B remains a candidate but no within-R7-A intervention has worked so far. Routes are unchanged from #319 (R-B / R-C / R-D / R-E).
- **Q2 (independent)**: Does the **concentration collapse** observed in 27.0b (USD_JPY share → ~100 % at α ≥ 0.3) replicate in 27.0c?
  - § 2.2 above answers **NO**: S-D test USD_JPY share = 0.7760 vs S-B baseline 0.7139; modest lift, not a collapse. The concentration-collapse axis is **specific to S-C with α > 0** and does NOT generalise to S-D
  - Reading: the core Spearman↑ / Sharpe↓ pattern is structurally robust across Channel B interventions, but the *mechanism* by which the wrong direction manifests differs (concentration collapse for S-C; trade-count drop + per-trade EV drop for S-D)
- **Q3 (independent)**: Does the 27.0c diagnostic (Ê[PnL|TIME] = +1.57; substantial isotonic shifts) elevate **H-B4** as a discriminator from H-B3?
  - If H-B4 is plausible → **R-S-E** is the targeted test (regression on realised PnL bypasses per-class scalar weighting)
  - If H-B4 is implausible → R-B / R-C / R-D / R-E remain the routes
- **Q4 (counterfactual)**: If R-B / R-C / R-D were run, what *would* falsify H-B3 under R7-A?
  - A wider feature set producing a Channel B intervention with **same-direction** Spearman and Sharpe (both positive lift; not just Spearman) would falsify the R7-A-conditioned H-B3 reading by demonstrating that the structural mis-alignment is **R7-A-conditioned**, not inherent to the multiclass head + L-1 label combination
  - If R-B / R-C / R-D *also* produce wrong-direction → H-B3 escalates from "load-bearing under R7-A" to "binding more broadly" and R-S-E / R-E gain weight
- **Q5 (cost vs information)**: R-B / R-C / R-D each require a 3-PR sequence (scope amendment + design memo + eval) and discriminate H-B2 vs H-B3 but **not** H-B3 vs H-B4. R-S-E also requires a 3-PR sequence and discriminates H-B4 from H-B3 but does NOT test H-B2. R-E is single-PR and concedes the question
- **Combined reading** (no selection): if Q1 = YES, the tree points to one of {R-B, R-C, R-D, R-S-E, R-E}; Q3 elevates R-S-E above R-B/R-C/R-D if H-B4 is the load-bearing concern; Q5 makes R-E the lowest-cost option if neither H-B2 nor H-B4 is the bottleneck. The user's answer to Q1 / Q3 is the routing lever for the next sub-phase

---

## 6. Constraints preserved (verbatim re-state)

### 6.1 Inherited bindings (carried forward unchanged)

- **D-1 binding**: formal realised-PnL uses inherited `_compute_realised_barrier_pnl` (bid/ask executable). Mid-to-mid PnL appears in sanity probe only.
- **D10 amendment** (3-artifact single fit; per 27.0c-α §7.5): one multiclass head + one isotonic triple + one estimator triple, shared across cells. Carries forward to any sub-phase that re-uses S-D-style structure.
- **Verdict ladder**: H1-weak (Spearman > 0.05) / H1-meaningful (≥ 0.10) / H2 (Sharpe ≥ 0.082 AND ann_pnl ≥ 180) / H3 (Sharpe > -0.192) / H4 (Sharpe ≥ 0). Unchanged.
- **Cross-cell verdict aggregation** (26.0c-α §7.2): agree → single verdict; disagree → split, no auto-resolution.
- **ADOPT_CANDIDATE wall**: H2 PASS → PROMISING_BUT_NEEDS_OOS only. Full A0-A5 8-gate harness in a SEPARATE PR. Unchanged.
- **NG#10 / NG#11**: not relaxed.
- **γ closure PR #279**: preserved unchanged.
- **X-v2 OOS gating**: remains required for any production deployment.
- **Production v9 20-pair** (Phase 9.12 closure tip 79ed1e8): untouched.
- **Phase 22 frozen-OOS contract**: preserved unchanged.

### 6.2 Phase 27 kickoff §8 — verbatim re-cite (drift prevention per D-R6)

The canonical source-of-truth is `docs/design/phase27_kickoff.md` §8 (merged at PR #316, master 84e7b76).

**Clauses 1–5 (inherited verbatim from Phase 26)**:

1. **Phase framing.** ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.
2. **Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison / classification-quality / feature-importance / per-pair-Sharpe-contribution columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.
3. **γ closure preservation.** Phase 24 γ hard-close (PR #279) is unmodified.
4. **Production-readiness preservation.** X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure tip 79ed1e8) remains untouched. Phase 22 frozen-OOS contract remains required for any ADOPT_CANDIDATE → production transition.
5. **NG#10 / NG#11 not relaxed.**

**Clause 6 (NEW for Phase 27, verbatim from kickoff §8)**:

> *6. Phase 27 scope. Phase 27's primary axes are (a) feature widening beyond the Phase 26 R6-new-A 2-feature allowlist via per-family closed allowlists and (b) score-objective redesign beyond P(TP) / P(TP)-P(SL). Phase 27 is NOT a Phase 25 feature-axis sweep revival. R7-A (inherited from PR #311) is admissible at kickoff; R7-B / R7-C each require a SEPARATE Phase 27 scope-amendment PR; R7-D and R7-Other are NOT admissible under any Phase 27 scope amendment currently on the table. Score-objectives S-A / S-B / S-C are admissible at kickoff for formal evaluation. S-D (calibrated EV) is admissible in principle but deferred — it requires its own design memo specifying per-class conditional-PnL estimation, calibration policy, and selection-overfit handling before any formal eval. S-E (regression-on-realised-PnL) requires a SEPARATE scope-amendment PR (model-class change). S-Other is NOT admissible. Phase 26 deferred-not-foreclosed items (L-4 / R6-new-B / R6-new-C / Phase 25 F4 / F6 / F5-d / F5-e) are NOT subsumed by Phase 27; they remain under their original phase semantics.*

This routing review does NOT amend clause 6. PR #320 tier-promoted S-D to *formal at 27.0c-β*; that promotion is complete (R-A is closed). All other tier semantics from clause 6 are preserved.

---

## 7. What this PR will NOT do

- ❌ Authorise any 27.0d / 27.0e / 27.0f sub-phase or any joint sub-phase
- ❌ Authorise any R7-B / R7-C scope amendment (R-B / R-C / R-D paths remain available but require separate scope-amendment PRs)
- ❌ Authorise S-E (regression-on-realised-PnL) scope amendment (model-class change requires separate PR per kickoff §5)
- ❌ Authorise a Phase 27 soft closure memo (R-E path)
- ❌ Select among R-B / R-C / R-D / R-S-E / R-E
- ❌ Modify any prior verdict (Phase 25 / Phase 26 / Phase 27.0b-β / Phase 27.0c-β / post-27.0b routing)
- ❌ Modify Phase 27 scope per kickoff §8 (R7-B / R7-C / R7-D / R7-Other admissibility unchanged; S-A / S-B / S-C admissibility unchanged; S-D's tier was promoted at PR #320 and that completion is preserved; S-E and S-Other admissibility unchanged)
- ❌ Relax the ADOPT_CANDIDATE 8-gate wall
- ❌ Relax NG#10 / NG#11
- ❌ Modify γ closure (PR #279)
- ❌ Modify X-v2 OOS gating
- ❌ Modify Phase 22 frozen-OOS contract
- ❌ Pre-approve any production deployment
- ❌ Touch `src/`, `scripts/`, `tests/`, `artifacts/`
- ❌ Update `.gitignore`
- ❌ Update MEMORY.md
- ❌ Auto-route to any next sub-phase after merge

---

## 8. Recommended next-PR-after-this-routing-doc

*Placeholder — to be filled by user choice on route.*

The next PR after this routing review is one of:

- (R-B) `docs/design/phase27_scope_amendment_r7_b.md` — R7-B (F1 microstructure) scope-amendment PR
- (R-C) `docs/design/phase27_scope_amendment_r7_c.md` — R7-C (F5 regime / context) scope-amendment PR
- (R-D) `docs/design/phase27_scope_amendment_r7_b_joint.md` — R7-B + joint S-C scope-amendment PR
- (R-S-E) `docs/design/phase27_scope_amendment_s_e.md` — S-E (regression-on-realised-PnL) model-class scope-amendment PR
- (R-E) `docs/design/phase27_closure_memo.md` — Phase 27 soft closure memo (R5 pattern)

The user picks the route in a separate later instruction.

---

## 9. Sign-off

Phase 27 has now produced two substantive Channel B sub-phase β evals (27.0b-β / 27.0c-β) since kickoff. The 2-evidence-point Channel B wrong-direction picture under R7-A is the binding evidence for routing. H-B3 (structural mis-alignment) is load-bearing under R7-A; H-B4 is newly surfaced and non-falsified; H-B2 remains the principal alternative; H-B1 is partially weakened.

The next move is one of {R-B, R-C, R-D, R-S-E, R-E} per §4 / §5; this review does not select.

**This PR stops here.**
