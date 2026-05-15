# Phase 27 — Post-27.0b Routing Review

**Type**: doc-only routing review
**Status**: routes Phase 27 after 27.0b-β S-C TIME-penalty eval (PR #318); does NOT initiate any sub-phase
**Branch**: `research/phase27-routing-review-post-27-0b`
**Base**: master @ 17be66a (post-PR #318 / Phase 27.0b-β eval merge)
**Pattern**: analogous to PR #310 (post-26.0c) and PR #314 (post-26.0d) routing reviews under Phase 26
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal post-27.0b routing review. It captures and consolidates the three-way picture from 27.0b-β (formal verdict, α-monotonicity, score-ranking vs realised-Sharpe direction), enumerates routing options, and presents a decision tree. It does NOT by itself authorise any 27.0c / 27.0d / S-D / R7-B / R7-C / soft-close sub-phase. The next sub-phase choice requires a separate later user instruction.*

Same approval-then-defer pattern as PR #310, #314, #316, and #317.

---

## 1. Executive summary — the three-way picture

Phase 27.0b-β (PR #318, merged at 17be66a) closed with **formal verdict REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL on all 4 α cells**, and the cross-cell aggregate is REJECT. No ADOPT_CANDIDATE was minted; no PROMISING_BUT_NEEDS_OOS branch triggered.

The α=0.0 cell **passed the baseline-match check** (n_trades=34,626 exact; Sharpe delta +3.55e-05 within ±1e-4 tolerance; ann_pnl delta -0.023 within ±0.5 pip tolerance). The inheritance chain from Phase 26 R6-new-A C02 (PR #313) is confirmed intact under R7-A fixed.

The **central routing-relevant finding** is the **opposite-direction α-monotonicity**:

- val realised Sharpe is **strict decreasing** in α
- test realised Sharpe is **strict decreasing** in α
- test formal Spearman is **strict increasing** in α
- α=1.0 is the **only positive-Spearman cell** but has the **worst realised Sharpe** of the four

That is — the S-C TIME-penalty score-objective intervention **demonstrably moves the formal ranking metric** (Channel B is a real, observable lever on Spearman), but it moves **realised executable PnL in the wrong direction**. This is the three-way picture: REJECT + Spearman-improved + Sharpe-worsened.

The reading is not free. Two parallel routing-hypotheses (H-B1 and H-B2 in §3) are consistent with this picture; **neither was falsified within 27.0b-β**, and each predicts a different next move.

This PR enumerates the routing space and presents a decision tree. It does **not** select a next sub-phase.

---

## 2. Three-axis result table (verbatim from PR #318 eval_report.md)

### 2.1 Val-selected (per cell, q*=5%) — formal verdict source

Source: `artifacts/stage27_0b/eval_report.md` §9 (PR #318).

| cell | α | q% | cutoff | val_sharpe | val_ann_pnl | val_n | test_sharpe | test_ann_pnl | test_n | test_spearman | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C-alpha0 | 0.0 | 5 | +0.1262 | -0.1863 | -142,234.1 | 25,881 | -0.1732 | -204,664.4 | 34,626 | -0.1535 | REJECT_NON_DISCRIMINATIVE |
| C-alpha03 | 0.3 | 5 | +0.0274 | -0.2116 | -134,972.6 | 25,886 | -0.2035 | -148,413.0 | 27,233 | -0.1127 | REJECT_NON_DISCRIMINATIVE |
| C-alpha05 | 0.5 | 5 | -0.0304 | -0.2234 | -134,299.0 | 25,872 | -0.2204 | -144,626.1 | 26,581 | -0.0786 | REJECT_NON_DISCRIMINATIVE |
| C-alpha10 | 1.0 | 5 | -0.1691 | -0.2446 | -132,789.0 | 25,890 | -0.2511 | -138,766.2 | 25,357 | +0.0226 | REJECT_NON_DISCRIMINATIVE |

α-monotonicity (strict per D-T6 / D5 binding, no ε-tolerance):
- val_sharpe: **decreasing** (-0.1863 → -0.2116 → -0.2234 → -0.2446)
- test_sharpe: **decreasing** (-0.1732 → -0.2035 → -0.2204 → -0.2511)
- test_ann_pnl: **increasing** (-204,664 → -148,413 → -144,626 → -138,766)
- test_spearman: **increasing** (-0.1535 → -0.1127 → -0.0786 → +0.0226)

Cross-cell aggregate (per 26.0c-α §7.2): all four cells agree → single verdict **REJECT_NON_DISCRIMINATIVE**.

### 2.2 Per-pair Sharpe contribution — paranoia view across all 4 α cells

Per D-R1 (paranoia mode), this review surfaces per-pair contribution for all 4 α cells. The merged eval_report.md §16 carries the **full** per-pair table only for the val-selected cell (α=0.0). For α=0.3 / 0.5 / 1.0 the merged report carries the §17 *pair concentration per cell* table (top-pair share only). Routing review re-cites both, and explicitly flags the data gap for follow-up sub-phase reporting.

**§16 full per-pair table — α=0.0 (val-selected cell), sorted by share_of_total_pnl desc** (D4 form):

| pair | n_trades | sharpe | share_of_total_pnl | share_of_total_trades |
|---|---|---|---|---|
| USD_JPY | 24,721 | -0.1803 | +0.6520 | 0.7139 |
| GBP_USD | 3,568 | -0.1677 | +0.1139 | 0.1030 |
| EUR_USD | 1,833 | -0.1812 | +0.0557 | 0.0529 |
| GBP_JPY | 985 | -0.1711 | +0.0539 | 0.0284 |
| AUD_USD | 1,803 | -0.1631 | +0.0498 | 0.0521 |
| EUR_JPY | 654 | -0.2171 | +0.0370 | 0.0189 |
| AUD_JPY | 657 | -0.1883 | +0.0300 | 0.0190 |
| USD_CAD | 350 | -0.1374 | +0.0088 | 0.0101 |
| EUR_AUD | 2 | -0.5188 | +0.0001 | 0.0001 |
| USD_CHF | 34 | -0.0098 | +0.0001 | 0.0010 |
| CHF_JPY | 7 | +0.0345 | -0.0001 | 0.0002 |
| NZD_USD | 12 | +0.3557 | -0.0013 | 0.0003 |

total_n_trades=34,626; total_pnl=-61,357.30.

**§17 pair concentration — α=0.3 / 0.5 / 1.0** (top-pair share on val and test):

| cell | α | q% | val_top_pair | val_top_share | test_top_pair | test_top_share |
|---|---|---|---|---|---|---|
| C-alpha0 | 0.0 | 5 | USD_JPY | 0.8685 | USD_JPY | 0.7139 |
| C-alpha03 | 0.3 | 5 | USD_JPY | 1.0000 | USD_JPY | 0.9998 |
| C-alpha05 | 0.5 | 5 | USD_JPY | 1.0000 | USD_JPY | 1.0000 |
| C-alpha10 | 1.0 | 5 | USD_JPY | 1.0000 | USD_JPY | 1.0000 |

This adds a **second axis of α-monotonicity not surfaced in §1**: as α increases from 0.0 → 0.3 → 0.5 → 1.0, the val-selected q*=5% slice collapses from **multi-pair (USD_JPY 71% test) toward single-pair USD_JPY (~100% test)**. From α=0.3 onward the picker selection is effectively degenerate single-pair on test.

**Data gap (flagged for follow-up sub-phase reporting)**: the merged 27.0b-β eval_report does NOT carry full §16-style per-pair tables for α=0.3 / 0.5 / 1.0. The §17 row above is all that is published for those cells. Future Phase 27 sub-phase β reports SHOULD include §16-style per-pair tables for every α cell when α-grid sub-phases are run.

---

## 3. Interpretation framework — hypotheses, not conclusions

### 3.1 The α=1.0 algebraic identity

For multiclass `P(TP) + P(SL) + P(TIME) = 1`:

```
S-C(row, α=1.0) = P(TP) - P(SL) - 1 · P(TIME)
                = P(TP) - P(SL) - (1 - P(TP) - P(SL))
                = 2·P(TP) - 1
```

So α=1.0 is a **monotone transform of P(TP)** — algebraically equivalent (up to ordering) to S-A (`P(TP)`). Argmax / quantile-cutoff selection under α=1.0 picks the same rows S-A would on the same probability vector.

This is the boundary cell that **must** be a monotone transform of P(TP), not a separate learned head. Its formal Spearman moves to +0.0226 because the formal Spearman target is the realised PnL ranking, and `P(TP)` alone *ranks* realised PnL better than `P(TP)-P(SL)` does at this feature set — yet it *monetises* worst (worst realised Sharpe at -0.2511; worst ann_pnl in absolute terms; tightest USD_JPY concentration at 100%). This decoupling — better ranking, worse monetisation — is the engine of the three-way picture.

### 3.2 H-B1 — P(TIME) as low-vol / range-regime proxy

**Statement**: P(TIME) is acting as a proxy for low-volatility / range-regime rows. Penalising P(TIME) preferentially keeps higher-volatility rows, which the formal Spearman target (against realised PnL ranking) rewards — but those higher-volatility rows are precisely the ones where bid/ask executable cost dominates, so executable PnL gets worse even though the ranking gets better.

**Why non-falsified within 27.0b-β**: 27.0b-β did not run regime-conditioned diagnostics (regime features are R7-C territory; not admissible at kickoff). 27.0b-β only confirms that TIME-penalty has *some* monotone effect on selection.

**Routing implication**: H-B1 predicts that regime / volatility-context features (R7-C family) — if admitted — would allow the model to *learn around* the regime proxy effect and recover monetisation alignment. Under H-B1, R7-C feature widening is the binding lever, not score-objective.

### 3.3 H-B2 — R7-A is too narrow for TIME-aware monetisation

**Statement**: The R7-A 2-feature allowlist (`atr_at_signal_pip` + `spread_at_signal_pip`) is too narrow for a TIME-aware score to monetise. The model cannot separate "high-TIME because regime is range" from "high-TIME because path stalls but eventually breaks" with only ATR and spread. With wider features (R7-B microstructure or R7-C regime context), the same S-C(α) sweep might flip direction.

**Why non-falsified within 27.0b-β**: 27.0b-β fixed R7-A by design (D10 single model fit across α cells; no feature additions). The α-monotonicity observation is conditioned on R7-A.

**Routing implication**: H-B2 predicts that wider features (R7-B or R7-C) combined with S-C(α>0) might produce aligned direction. This is the joint-redesign hypothesis the kickoff §1 anticipated.

### 3.4 Hypothesis status

Both H-B1 and H-B2 are **routing-relevant hypotheses, not conclusions** — they survived the 27.0b-β data unchallenged. Neither was tested *within* 27.0b-β. Both predict that wider features are the binding lever; they differ on whether the score-objective redesign would still matter after widening:

- H-B1: regime features unlock alignment; S-C(α) may become unnecessary
- H-B2: wider features + S-C(α) jointly recover alignment

A third hypothesis is also live but **not** part of routing-relevant H-B*:

- **H-B3 (alignment-structural)**: Channel B is structurally mis-aligned with realised PnL under the multiclass `P(TP)/P(SL)/P(TIME)` head. No score-objective composed from these three probabilities can fix the wrong-direction Sharpe. Under H-B3, S-D (calibrated EV) is the only remaining Channel B lever, and if it also fails, Channel B is exhausted.

H-B3 routes to R-A (S-D calibrated EV) or R-E (Phase 27 soft close).

---

## 4. Routing options (closed set — 5 options)

Each option states what evidence we currently lack that the option would supply. None are pre-selected.

| ID | Option | What it tests | Channel | Cost | Risk |
|---|---|---|---|---|---|
| **R-A** | S-D calibrated EV (one α-cell extension) | Whether per-class conditional-PnL calibration of the multiclass head fixes the wrong-direction Sharpe; tests H-B3 | B | medium (calibration design + 1 cell eval) | precedent: S-D was *admissible-but-deferred* at kickoff §5 — requires its own design memo before any formal eval |
| **R-B** | R7-B feature widening (R7-A + Phase 25 F1 vol expansion/compression) | Whether richer features fix the R7-A-conditioned bottleneck; tests H-B2 under microstructure axis | A | medium-high (scope amendment + design memo + eval) | Phase 26 closure §1 established A-only widening *partially* lifted Sharpe but did NOT solve Channel B (Spearman remained negative) |
| **R-C** | R7-C feature widening (R7-A + Phase 25 F5 liquidity/spread/volume composites) | Whether regime/context features unlock the TIME-vs-PnL trade-off; tests H-B1 + H-B2 under regime axis | A | medium-high (scope amendment + design memo + eval) | same as R-B; selection-overfit risk on R6-new-A val cell already used |
| **R-D** | Joint R7-B ⊕ S-C α=0.3 one-cell | Whether A + B intervention together flip the wrong-direction monotonicity; tests H-B2 directly | A + B | high (joint design; new failure modes from interaction) | scope expansion; harder to attribute outcome to either channel; precedent: kickoff §2 frames Phase 27 as a *joint redesign* but does not require joint sub-phases |
| **R-E** | Phase 27 soft close | Concede Channel B redesign under R7-A is exhausted; route to Phase 28 or pause | — | low | forecloses Phase 27 prematurely if R7-B / R7-C / S-D remain unexplored; precedent: Phase 26 closed under R5 at #315 only after 4 evidence points |

Notes on cost / sequencing:

- **R-A** does *not* require a Phase 27 scope-amendment PR — S-D is "admissible-but-deferred" per kickoff §5, requiring only its own design memo before formal eval. Two-PR sequence (design memo + eval).
- **R-B** requires a Phase 27 scope-amendment PR (per kickoff §4 — R7-B blocked behind a separate amendment analogous to PR #311). Three-PR sequence (scope amendment + design memo + eval).
- **R-C** requires a Phase 27 scope-amendment PR (analogous to R-B). Three-PR sequence.
- **R-D** requires a Phase 27 scope-amendment PR for R7-B *and* a joint design memo. Three-PR sequence (or four if R7-B is also evaluated standalone first).
- **R-E** is a single PR (Phase 27 soft closure memo) analogous to PR #315 Phase 26 closure.

---

## 5. Routing decision tree (bullet-tree)

The tree is presented for reasoning support; **no selection is made in this PR**. Order of leaves reflects logical dependency, not preference.

- **Q1**: Do we believe the wrong-direction monotonicity is **R7-A-conditioned** (i.e., would flip with wider features)?
  - **YES** → next move is feature widening before further score-objective work
    - **Q1a**: Which feature family first — microstructure (F1) or regime/context (F5)?
      - microstructure first → **R-B** (R7-B scope amendment + design memo + eval)
      - regime/context first → **R-C** (R7-C scope amendment + design memo + eval)
      - both jointly with α=0.3 → **R-D** (joint scope amendment + joint design memo + joint eval; higher cost / higher attribution risk)
  - **NO** → wrong-direction monotonicity is **structural** for the current multiclass head
    - **Q1b**: Does the structural mis-alignment have a Channel B remedy within the current label set?
      - calibrated EV might fix it → **R-A** (S-D design memo + S-D eval)
      - no Channel B remedy → **R-E** (Phase 27 soft closure under R5 pattern)
- **Q2 (independent)**: Does the multiclass `P(TP)/P(SL)/P(TIME)` head still admit any room above 2·P(TP)-1 ranking?
  - **YES** → 27.0b-β shows it does (Spearman moved from -0.1535 to +0.0226 as α moved 0.0 → 1.0). The score head is **informative**; the alignment problem is the failure mode, not the head's informativeness
  - **NO** → would route directly to R-E
- **Q3 (independent)**: Is the second axis of α-monotonicity — selection collapse to ~100% USD_JPY at α≥0.3 — itself a falsification of H-B2?
  - This question is **open** within 27.0b-β. R7-A may be too narrow for the picker to find non-USD_JPY rows under TIME-penalty regardless of feature widening; or USD_JPY may dominate the high-`P(TP)-P(SL)-α·P(TIME)` region in *all* feature configurations, in which case R7-B / R7-C would not solve it. R-B / R-C / R-D each implicitly tests this; R-A does not.

**Combined reading** (no selection): if Q1 = YES, the tree points to R-B / R-C / R-D in some order (testing H-B2 ± H-B1). If Q1 = NO, the tree points to R-A then R-E (testing H-B3). Q3 is the single most efficient discriminator across all R-B / R-C / R-D routes.

The user's answer to Q1 is the routing lever for the next sub-phase.

---

## 6. Constraints preserved (verbatim re-state)

### 6.1 Inherited bindings (carried forward unchanged)

- **D-1 binding**: formal realised-PnL uses inherited `_compute_realised_barrier_pnl` (bid/ask executable). Mid-to-mid PnL appears in sanity probe only.
- **D10 binding (27.0b-α §6)**: single model fit shared across cells. Carries forward to any α-grid or score-objective sweep sub-phase.
- **D5 binding (27.0b-α §12.3)**: α-monotonicity diagnostic is strict (no ε-tolerance) for the monotonic / mixed classification.
- **D4 binding (27.0b-α §12.4)**: per-pair Sharpe contribution sorted by share_of_total_pnl descending.
- **Verdict ladder**: H1-weak (Spearman > 0.05) / H1-meaningful (≥ 0.10) / H2 (Sharpe ≥ 0.082 AND ann_pnl ≥ 180) / H3 (Sharpe > -0.192) / H4 (Sharpe ≥ 0). Unchanged.
- **ADOPT_CANDIDATE wall**: H2 PASS → PROMISING_BUT_NEEDS_OOS only. Full A0-A5 8-gate harness required in a SEPARATE PR. Unchanged.
- **NG#10 / NG#11**: not relaxed.
- **γ closure PR #279**: preserved unchanged.
- **X-v2 OOS gating**: remains required for any production deployment.
- **Production v9 20-pair** (Phase 9.12 closure tip 79ed1e8): untouched.
- **Phase 22 frozen-OOS contract**: preserved unchanged.
- **Cross-cell verdict aggregation (26.0c-α §7.2)**: agree → single verdict; disagree → split verdicts, no auto-resolution.

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

This routing review does NOT amend clause 6. Any change to admissibility requires a SEPARATE Phase 27 scope-amendment PR.

---

## 7. What this PR does NOT do

- ❌ Authorise any 27.0c / 27.0d / 27.0e / 27.0f sub-phase or any joint sub-phase
- ❌ Authorise any S-D design memo (R-A path)
- ❌ Authorise any R7-B / R7-C scope amendment (R-B / R-C / R-D paths)
- ❌ Authorise a Phase 27 soft closure memo (R-E path)
- ❌ Select among R-A / R-B / R-C / R-D / R-E
- ❌ Modify any prior verdict (Phase 25 / Phase 26 / Phase 27.0b-β)
- ❌ Modify Phase 27 scope per kickoff §8 (R7-B / R7-C / R7-D / R7-Other admissibility unchanged; S-D / S-E / S-Other admissibility unchanged)
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

- (R-A) `docs/design/phase27_0c_alpha_s_d_calibrated_ev_design_memo.md` — S-D calibrated EV design memo
- (R-B) `docs/design/phase27_scope_amendment_r7_b.md` — R7-B (F1) scope-amendment PR
- (R-C) `docs/design/phase27_scope_amendment_r7_c.md` — R7-C (F5) scope-amendment PR
- (R-D) `docs/design/phase27_scope_amendment_r7_b_joint.md` — R7-B + joint S-C scope-amendment PR
- (R-E) `docs/design/phase27_closure_memo.md` — Phase 27 soft closure memo (R5 pattern)

The user picks the route in a separate later instruction.

---

## 9. Sign-off

Phase 27 has produced one substantive sub-phase β eval (27.0b-β, PR #318) since the kickoff (PR #316). The 27.0b-β three-way picture — formal REJECT + Spearman improvement + Sharpe worsening — is the binding evidence point for routing. The next move is one of {R-A, R-B, R-C, R-D, R-E} per §4 / §5; this review does not select.

**This PR stops here.**
