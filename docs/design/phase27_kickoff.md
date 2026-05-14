# Phase 27 Kickoff Memo — Feature-Widening + Score-Ranking Monetisation Redesign

**Type**: doc-only formal kickoff memo
**Status**: opens Phase 27; declares scope binding; does NOT initiate any sub-phase
**Branch**: `research/phase27-kickoff`
**Base**: master @ d8dec02 (post-PR #315 / Phase 26 closure)
**Pattern**: analogous to PR #299 Phase 26 kickoff with Phase 27-specific axes (feature family + score-objective) added
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal Phase 27 kickoff and the canonical source of Phase 27's scope binding (mandatory clause 6 NEW for Phase 27, replacing the Phase 26 AMENDED clause 6 captured in PR #315 §8). It does NOT by itself authorise any 27.0a / 27.0b / 27.0c / ... design memo, implementation, or eval. Each sub-phase requires explicit user authorisation in a separate later instruction.*

Same approval-then-defer pattern as PR #299 Phase 26 kickoff and PR #311 scope amendment.

---

## 1. Why Phase 27 exists

Phase 26 closed at PR #315 with three load-bearing observations:

1. **Label / target redesign at minimum feature set was insufficient.** L-1 / L-2 / L-3 produced identical val-selected outcomes (n_trades=42,150 / Sharpe=-0.2232 / ann_pnl=-237,310.8 / 100% USD_JPY) — the 3-evidence-point load-bearing finding from #310 §3.
2. **Minimal feature widening broke the identity.** R6-new-A (PR #313) YES_IMPROVED: Sharpe -0.2232 → -0.1732 (+22%); trade count 42,150 → 34,626; concentration 100% USD_JPY → multi-pair. Channel A lever exists.
3. **Score-ranking monetisation remained binding.** R6-new-A H1-weak FAIL (val-selected Spearman -0.1535). Channel B was not lifted by 2-feature widening alone.

Phase 27 exists to address the **joint hypothesis** that Channel A AND Channel B both need to be exercised — feature widening AND score-objective redesign — to potentially unblock the score-ranking monetisation gate. Neither axis alone was sufficient in Phase 26.

---

## 2. Phase 27 framing — what it IS and what it is NOT

| Phase 27 IS | Phase 27 is NOT |
|---|---|
| Feature-widening + score-ranking monetisation **joint redesign** under controlled scope | A Phase 25 feature-axis sweep revival (closed allowlists per family; not all F-classes admitted) |
| Takes the Phase 26 R6-new-A YES_IMPROVED finding as the **starting evidence point**, not a Phase 25 reopen | Treats Channel A as automatically supporting more widening (still subject to its own evidence at each sub-phase) |
| Score-objective redesign space includes alternatives to `P(TP)` / `P(TP)-P(SL)` (e.g., TIME-penalty composites, regression-on-realised-PnL) | Label-class redesign — Phase 26 closed that axis with REJECT on L-1 / L-2 / L-3 |
| Pair-concentration diagnostic upgraded to **per-pair Sharpe contribution table** required in every sub-phase eval | Per-pair model training or per-pair feature engineering (out of scope unless a future scope amendment admits them) |
| **ADOPT_CANDIDATE wall preserved**: H2 PASS + full A0-A5 8-gate harness required in a SEPARATE PR, same as Phase 26 family | Shortcut path to ADOPT via H2 PASS alone (still PROMISING_BUT_NEEDS_OOS at best) |

---

## 3. Inheritance from Phase 26 (binding artifacts carried forward)

| Phase 26 artifact | Phase 27 inheritance status |
|---|---|
| 25.0a-β path-quality dataset | inherited unchanged |
| 70/15/15 chronological split | inherited |
| Triple-barrier inputs (K_FAV=1.5×ATR, K_ADV=1.0×ATR, H_M1=60) | inherited |
| `_compute_realised_barrier_pnl` (bid/ask executable harness) | inherited unchanged — D-1 binding preserved |
| 8-gate metrics + `gate_matrix` | inherited |
| H1-weak / H1-meaningful / H2 / H3 / H4 thresholds | inherited (0.05 / 0.10 / 0.082 Sharpe + 180 ann_pnl / -0.192 / 0) |
| Quantile-of-val cutoff fitting (val-only; test touched once) | inherited |
| CONCENTRATION_HIGH 80% flag | inherited as **baseline diagnostic**; Phase 27 adds per-pair Sharpe contribution table to every sub-phase report (§6) |
| L-1 label construction (`build_l1_labels_for_dataframe`) | inherited as **default starting label**; Phase 27 sub-phases may swap to L-2 / L-3 inherited variants as starting points (Phase 26-style label-class space is closed for redesign) |
| 2-feature allowlist (`atr_at_signal_pip` + `spread_at_signal_pip`) | inherited as **R7-A baseline feature family** |
| Fixed conservative LightGBM multiclass config | inherited as **default model class**; a model-class change (e.g., regression) requires a SEPARATE Phase 27 scope amendment |

---

## 4. Allowed feature families (Phase 27 closed allowlists)

Phase 27 partitions admissible features into **closed families**, each admissible only after a per-family scope-amendment PR (analogous to PR #311). This avoids Phase 25 sweep re-traversal while still opening the feature axis.

| Family | Source | Phase 27 admissibility status |
|---|---|---|
| **R7-A** (inherited from Phase 26 R6-new-A) | `atr_at_signal_pip` + `spread_at_signal_pip` | **admissible at kickoff** — already cleared via PR #311 |
| **R7-B** | Phase 25 F1 best features (vol expansion / compression) | admissible ONLY after a SEPARATE Phase 27 scope-amendment PR (analogous to PR #311) admitting F1 to a new closed allowlist |
| **R7-C** | Phase 25 F5 best features (liquidity / spread / volume composites) | admissible ONLY after a SEPARATE Phase 27 scope-amendment PR admitting F5 to a new closed allowlist |
| **R7-D** | Full Phase 25 F1..F5 ~45-feature set | **NOT admissible under any Phase 27 scope amendment.** Functionally a Phase 25 reopening; out of Phase 27 scope. Would require a separate Phase 25 reopening decision (not authorised here). |
| **R7-Other** | Multi-TF / calendar / external-data / per-pair / Phase 25 F2 / F3 / F4 / F6 / F5-d / F5-e | NOT admissible at kickoff. Each would require a SEPARATE Phase 27 scope-amendment PR with its own justification. |

R7-A is the only family admissible without further scope amendment. Each new family is its own multi-PR sequence (scope amendment + design memo + eval).

---

## 5. Score-objective redesign space (the NEW Phase 27 axis)

Phase 27's primary degree of freedom over Phase 26 is the **score-objective**. Phase 26 fixed `P(TP)` and `P(TP)-P(SL)` at #308 §3 binding. Phase 27 admits the following score-objective candidates, partitioned into four admissibility tiers.

| Score-objective ID | Definition | Phase 27 admissibility tier |
|---|---|---|
| **S-A** | `P(TP)` (inherited from Phase 26 C01) | **formal at kickoff** |
| **S-B** | `P(TP) - P(SL)` (inherited from Phase 26 C02) | **formal at kickoff** |
| **S-C** | `P(TP) - P(SL) - α · P(TIME)` for α ∈ {0.0, 0.3, 0.5, 1.0} (penalise TIME class explicitly) | **formal at kickoff** |
| **S-D** | calibrated EV: `P(TP) · E[PnL | TP] + P(SL) · E[PnL | SL] + P(TIME) · E[PnL | TIME]` | **admissible but deferred / diagnostic candidate**. Initial formal admission would force per-class conditional-PnL estimation, calibration design (likely isotonic or Platt), and an additional selection-overfit risk on the same val set. **Requires its own design memo** specifying conditional-PnL estimation policy, calibration policy, and selection-overfit handling before any formal eval. Until then, S-D can be reported as a diagnostic candidate in sub-phase evals but does NOT enter formal verdict routing. |
| **S-E** | regression-on-realised-PnL (continuous model trained directly on realised barrier PnL; not a class-prob picker) | requires a SEPARATE Phase 27 scope-amendment PR (changes model-class from multiclass classification to regression) |
| **S-Other** | quantile regression / ordinal score / learn-to-rank objectives | NOT admissible at kickoff |

Tier semantics:
- **formal at kickoff**: can be evaluated in any Phase 27 sub-phase β eval without further authorisation
- **admissible but deferred / diagnostic candidate**: documented as a future direction; cannot enter formal verdict routing until its own design memo merges
- **requires scope amendment**: each blocked behind a separate amendment PR
- **NOT admissible**: out of Phase 27 scope as currently framed

---

## 6. Pair-concentration diagnostic policy

| Phase 26 status | Phase 27 status |
|---|---|
| CONCENTRATION_HIGH 80% flag is **diagnostic-only**; NOT consulted by `select_cell_validation_only` or `assign_verdict` | CONCENTRATION_HIGH 80% flag remains **diagnostic-only** (clause 2 binding unchanged) |
| 100% USD_JPY concentration on L-baselines did not affect formal verdict | Phase 27 may **opt-in** a per-pair-share regularised cell selection in a sub-phase ONLY IF that sub-phase explicitly authorises it via its design memo. The formal verdict ladder is unchanged. |
| — | **NEW: per-pair Sharpe contribution table required in every Phase 27 sub-phase β eval_report.md.** Surfaces whether multi-pair lift (vs single-pair degenerate selection) is uniform or driven by a small subset. Diagnostic-only; NOT in formal verdict. |

The USD_JPY skew observed on L-baselines (and broken on R6-new-A) is treated as **observed phenomenon to surface in every report**, not as a formal verdict input. Phase 27 does not relax the diagnostic-only binding from clause 2.

---

## 7. Sub-phase enumeration (candidates; not committed)

Phase 27 sub-phases are admissible candidates only. Each requires its own design memo PR + eval PR. The kickoff enumerates candidates without committing the order.

| Sub-phase | Feature family | Score-objective | Notes |
|---|---|---|---|
| **27.0a** | R7-A (inherited) | S-A / S-B (inherited) | Phase 26 R6-new-A baseline replication on the Phase 27 framework; sanity-check Phase 27 wiring; first opportunity to confirm per-pair Sharpe contribution table reporting works |
| **27.0b** | **R7-A (fixed; no new feature additions)** | **S-C TIME penalty sweep over α ∈ {0.0, 0.3, 0.5, 1.0} (fixed, small)** | Recommended **first substantive sub-phase**. Smallest scope: feature family fixed at R7-A; score-objective sweep limited to the 4-point α grid. α=0.0 cell explicitly equals S-B baseline (sanity check). Tests Channel B lever in isolation — no scope amendment needed |
| **27.0c** | R7-A | S-A / S-B (inherited) | model-class or calibration variation (TBD; each variation needs its own design memo) |
| **27.0d** | R7-B (requires scope amendment) | S-A / S-B | First feature-family widening; Channel A continuation under F1 |
| **27.0e** | R7-C (requires scope amendment) | S-A / S-B | Second feature-family widening; Channel A continuation under F5 |
| **27.0f** | R7-A | S-E (regression-on-realised-PnL; requires scope amendment) | Model-class change |
| **27.0X** (combinations) | combinations of admitted families × admitted objectives | combinations | each requires its own design memo |

**Default first-sub-phase recommendation**: 27.0b. Reasoning: smallest scope (R7-A fixed; α grid fixed at 4 points; no further scope amendment needed); tests Channel B lever cleanly; α=0.0 sanity check tied to S-B baseline. The user picks the actual first sub-phase order in a separate later instruction.

---

## 8. Mandatory clauses (clauses 1-5 inherited verbatim from Phase 26; clause 6 NEW for Phase 27)

Clauses 1-5 inherited verbatim from PR #315 Phase 26 closure §8 (which inherited them from #299 §7 through the entire Phase 26 chain).

1. **Phase framing.** ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness. *[unchanged]*
2. **Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison / classification-quality / feature-importance / per-pair-Sharpe-contribution columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them. *[unchanged; Phase 27 explicitly adds per-pair Sharpe contribution to the diagnostic-only enumeration]*
3. **γ closure preservation.** Phase 24 γ hard-close (PR #279) is unmodified. *[unchanged]*
4. **Production-readiness preservation.** X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure tip 79ed1e8) remains untouched. Phase 22 frozen-OOS contract remains required for any ADOPT_CANDIDATE → production transition. *[unchanged]*
5. **NG#10 / NG#11 not relaxed.** *[unchanged]*

**Clause 6 (NEW for Phase 27, replacing the Phase 26 AMENDED clause 6 from PR #311 §8 / PR #315 §8)**:

> *6. Phase 27 scope. Phase 27's primary axes are (a) feature widening beyond the Phase 26 R6-new-A 2-feature allowlist via per-family closed allowlists and (b) score-objective redesign beyond P(TP) / P(TP)-P(SL). Phase 27 is NOT a Phase 25 feature-axis sweep revival. R7-A (inherited from PR #311) is admissible at kickoff; R7-B / R7-C each require a SEPARATE Phase 27 scope-amendment PR; R7-D and R7-Other are NOT admissible under any Phase 27 scope amendment currently on the table. Score-objectives S-A / S-B / S-C are admissible at kickoff for formal evaluation. S-D (calibrated EV) is admissible in principle but deferred — it requires its own design memo specifying per-class conditional-PnL estimation, calibration policy, and selection-overfit handling before any formal eval. S-E (regression-on-realised-PnL) requires a SEPARATE scope-amendment PR (model-class change). S-Other is NOT admissible. Phase 26 deferred-not-foreclosed items (L-4 / R6-new-B / R6-new-C / Phase 25 F4 / F6 / F5-d / F5-e) are NOT subsumed by Phase 27; they remain under their original phase semantics.*

This kickoff memo is the **canonical source-of-truth for clause 6 in Phase 27**. Future Phase 27 sub-phases re-quote clause 6 from this memo.

---

## 9. Production / γ closure / X-v2 OOS / 8-gate harness bindings preserved

This kickoff memo does **not** touch any of:

- γ closure (PR #279) — unmodified
- X-v2 OOS gating — remains required for any future production deployment
- Production v9 20-pair (Phase 9.12 closure tip `79ed1e8`) — untouched
- NG#10 / NG#11 — not relaxed
- Phase 22 frozen-OOS contract — required for any ADOPT_CANDIDATE → production transition
- ADOPT_CANDIDATE 8-gate A0-A5 harness — required in a SEPARATE PR; cannot be minted in a Phase 27 sub-phase β eval

No production change of any kind is associated with this kickoff.

---

## 10. ADOPT_CANDIDATE gate (preserved unchanged)

> *Phase 27 sub-phase β evals can produce at best **PROMISING_BUT_NEEDS_OOS** (H2 PASS branch). ADOPT_CANDIDATE requires the full 8-gate A0-A5 harness in a SEPARATE PR, same as Phase 26 family.*

Verdict tree structure inherited unchanged from Phase 26 family (PR #308 §6.2 / #309 / #313). The Phase 27-specific axes (feature family + score-objective) do NOT relax the verdict ladder. H1-weak (Spearman > 0.05) / H1-meaningful (≥ 0.10) / H2 (Sharpe ≥ 0.082 AND ann_pnl ≥ 180) / H3 (Sharpe > -0.192) / H4 (Sharpe ≥ 0) thresholds unchanged.

---

## 11. Stop conditions

| Stop level | Trigger |
|---|---|
| Definitive stop | All admissible feature-family × score-objective combinations tested AND no H2 PASS |
| **Strong soft stop** | 3+ Phase 27 evidence points confirm gap (analogous to Phase 26 #310 strong soft stop) |
| Soft stop | 2+ Phase 27 evidence points confirm gap |
| Per-sub-phase ADOPT_CANDIDATE | H2 PASS + full A0-A5 (SEPARATE PR) |

Stop conditions are evaluated per routing review after each sub-phase β closure (analogous to Phase 26 #304 / #307 / #310 / #314 pattern).

---

## 12. PR chain reference

```
Phase 27:
  THIS PR (Phase 27 kickoff)
  → user picks first sub-phase in a separate later instruction
    (default recommendation: 27.0b — S-C TIME penalty sweep over α ∈ {0.0, 0.3, 0.5, 1.0};
     feature family fixed at R7-A; no further scope amendment needed)
  → 27.0X-α design memo PR (one per sub-phase)
  → 27.0X-β eval PR (one per sub-phase)
  → post-27.0X routing review PR after each closure
  → eventual ADOPT_CANDIDATE → A0-A5 PR (separate from any sub-phase β eval)
  → eventual Phase 27 closure memo (R5 pattern) OR ADOPT_CANDIDATE → production
    (the latter only after X-v2 OOS gating + Phase 22 frozen-OOS contract)
```

Phase 26 chain (closed at PR #315) is reference history only; Phase 27 does not re-execute it.

---

## 13. What this PR will NOT do

- ❌ Authorise any 27.0a-α / 27.0b-α / 27.0c-α / ... design memo (each requires separate later user instruction)
- ❌ Authorise any 27.0X-β eval implementation
- ❌ Authorise R7-B / R7-C feature families (each needs separate Phase 27 scope-amendment PR)
- ❌ Authorise S-D (calibrated EV) formal evaluation (admissible but deferred; requires own design memo)
- ❌ Authorise S-E (regression-on-realised-PnL) (requires separate scope-amendment PR)
- ❌ Authorise R7-D (full Phase 25 F1..F5 set; Phase 25 reopening territory)
- ❌ Authorise R7-Other (multi-TF / calendar / external-data / per-pair / etc.; each needs separate scope-amendment PR)
- ❌ Authorise S-Other (quantile regression / ordinal / learn-to-rank)
- ❌ Reopen Phase 25
- ❌ Reopen Phase 26 (L-4 / R6-new-B / R6-new-C remain Phase 26 deferred-not-foreclosed)
- ❌ Modify γ closure (PR #279)
- ❌ Modify X-v2 OOS gating
- ❌ Modify Phase 22 frozen-OOS contract
- ❌ Modify NG#10 / NG#11
- ❌ Pre-approve production deployment
- ❌ Modify any prior verdict (Phase 25 / Phase 26 / earlier)
- ❌ Auto-route to any Phase 27 sub-phase after merge
- ❌ Touch `src/`, `scripts/`, `tests/`, or `artifacts/`
- ❌ Update MEMORY.md

---

## 14. Sign-off

Phase 27 is open. First sub-phase choice (27.0a / 27.0b / 27.0c / 27.0d / 27.0e / 27.0f) is a separate later user instruction. The kickoff's default first-sub-phase recommendation is **27.0b (S-C TIME penalty sweep; R7-A fixed; α grid fixed at 4 points)**, but the user picks the actual order.

**This PR stops here.**
