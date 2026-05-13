# Phase 26 — Scope Amendment: Feature Widening (R6-new prerequisite)

**Type**: doc-only mini scope-amendment memo (R6-new prerequisite)
**Status**: scope authorisation only; does NOT initiate R6-new-A design memo or eval
**Branch**: `research/phase26-scope-amendment-feature-widening`
**Base**: master @ 4d99714 (post-PR #310 merge)
**Pattern**: stand-alone scope amendment (new doc family within the Phase 26 stream)

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as a narrow, controlled amendment to Phase 26 mandatory clause 6. It does NOT by itself authorise the R6-new-A design memo, R6-new-A implementation, R6-new-A eval, or any R6-new-B / R6-new-C / R6-new-D variant. The user explicitly authorises the next Phase 26 sub-phase (R6-new-A design memo) in a separate later instruction.*

Same approval-then-defer pattern as #304 / #307 / #310 routing reviews and #305 / #308 design memos.

---

## 1. Why this amendment is needed

Post-26.0c routing review (PR #310) recorded a **3-evidence-point load-bearing finding** (§3 binding text): L-1 (PR #309), L-2 (PR #306), L-3 (PR #303) all converged to the IDENTICAL val-selected (cell\*, q\*) realised-PnL outcome on test (n_trades=42,150 ; Sharpe=-0.2232 ; ann_pnl=-237,310.8 ; 100% USD_JPY concentration). The label-class axis spans regression-vs-classification AND spread-embedded-vs-not, yet the formal realised-PnL outcome is invariant.

The strongest current hypothesis (subjective / heuristic; not statistically estimated) is that **the minimum feature set (`pair + direction`) is the binding constraint**. This is a 3-evidence-point load-bearing finding, NOT a proof.

R6-new (feature widening pivot; #310 §6) is the most direct test of this hypothesis. But Phase 26 kickoff (PR #299 §5), first-scope review (#300), and every subsequent Phase 26 sub-phase have carried clause 6 forward verbatim: *"Phase 26 is NOT a continuation of Phase 25's feature-axis sweep."*

R6-new cannot start without explicitly amending clause 6. **This memo is that amendment.** It is doc-only, narrow, and minimal.

---

## 2. Scope of the amendment (the controlled exception to clause 6)

The amendment opens a **controlled, narrow exception** to clause 6:

> *Phase 26 mandatory clause 6 is **amended** to permit a **narrow feature-widening audit** (R6-new-A) under the following conditions:*
>
> *(a) The audit is **labelled as a Phase 26 audit, NOT a Phase 25 continuation.***
> *(b) The audit is tightly scoped to a **minimal feature set bump** — `pair + direction` plus a **closed two-feature allowlist** (see §3).*
> *(c) The audit is **NOT** a revival of Phase 25's F-class sweep (F1..F5). F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed under their original Phase 25 semantics.*
> *(d) The audit is run on the **same canonical 20-pair universe** with the **same 70/15/15 split** and the **same triple-barrier event-time horizon** (K_FAV=1.5×ATR, K_ADV=1.0×ATR, H_M1=60) as L-1 / L-2 / L-3.*
> *(e) The audit's verdict tree, H1/H2/H3/H4 thresholds, and ADOPT criteria remain **unchanged** from Phase 26's existing verdict family (#299 / 26.0a-α / 26.0b-α / 26.0c-α).*
> *(f) ADOPT_CANDIDATE in R6-new still requires the **full 8-gate A0-A5 harness** in a separate PR. R6-new-A by itself can resolve to PROMISING_BUT_NEEDS_OOS at best.*
> *(g) R6-new-B / R6-new-C / R6-new-D are **NOT** authorised by this amendment. Each would require its own subsequent scope amendment.*

**Clauses 1, 2, 3, 4, 5 are unchanged by this amendment.**

---

## 3. Admissible feature additions (enumerated allowlist; closed set; D-S2 explicit boundary)

### 3.1 Admitted (closed allowlist; exactly 2 features)

In addition to `pair + direction` (already in the Phase 26 minimum feature set):

| Feature | Source column in 25.0a-β dataset | Why admissible (minimal step) |
|---|---|---|
| `atr_at_signal_pip` | already in dataset | already used as a *normaliser* in 26.0a-β atr_normalised cells (denominator in label scaling); treating it as a *feature* (regressor / predictor) is the minimum incremental step from the L-class evals |
| `spread_at_signal_pip` | already in dataset | already used as a label-construction component in L-3 D-4 (subtracted from target); treating it as a *feature* (not target component) is the minimum incremental step that tests whether liquidity-cost level — when surfaced to the model rather than embedded in the target — changes the ranking signal |

Both features are continuous numeric. Both are already present in the 25.0a-β path-quality dataset and do not require dataset regeneration.

### 3.2 NOT admitted (enumerated exclusions; out of scope until a further scope amendment)

The amendment is **explicit on what is excluded** (not just on what is admitted). Each item below requires a **separate, subsequent scope amendment** before it can be used in Phase 26:

| Excluded feature class | Out-of-scope reason |
|---|---|
| ❌ Phase 25 F1 features (vol expansion / compression) | full F-class sweep revival prohibited per amended clause 6 |
| ❌ Phase 25 F2 features (trend / momentum) | full F-class sweep revival prohibited per amended clause 6 |
| ❌ Phase 25 F3 features (microstructure) | full F-class sweep revival prohibited per amended clause 6 |
| ❌ Phase 25 F5 features (liquidity / spread / volume **composites**) | N.B. `spread_at_signal_pip` alone is admissible per §3.1 row 2; F5's full composite set is NOT |
| ❌ F4 (Phase 25 deferred-not-foreclosed) | preserved under Phase 25 semantics; outside this Phase 26 amendment |
| ❌ F6 (Phase 25 deferred-not-foreclosed) | preserved under Phase 25 semantics; outside this Phase 26 amendment |
| ❌ F5-d / F5-e (Phase 25 deferred-not-foreclosed) | preserved under Phase 25 semantics; outside this Phase 26 amendment |
| ❌ Multi-timeframe features (M5 / M15 / H1 aggregates) | requires separate amendment + dataset-side wiring |
| ❌ Calendar / time-of-day features | requires separate amendment |
| ❌ External-data features (DXY, news, calendar events) | requires separate amendment + data-supply work |

R6-new-B / R6-new-C / R6-new-D variants from #310 §6.1 are **explicitly NOT authorised** by this amendment (per (g) above).

---

## 4. Label class for R6-new (re-use of inherited L-class; choice deferred to next PR)

The scope amendment is on the **feature axis**, NOT the label axis. R6-new-A must adopt **exactly one** of the existing inherited L-classes as its label. This amendment does **NOT** fix which L-class — that choice is a **Decision A** for the next R6-new-A design memo PR.

| Inherited L-class | Admissible as R6-new-A label? | Recommendation note |
|---|---|---|
| **L-1 (ternary classification {TP, SL, TIME})** | yes — **recommended default** | most recently characterised in #309; multiclass picker scoring (P(TP) / P(TP)-P(SL)) carries over cleanly; same verdict-tree wiring |
| L-2 (continuous mid-to-mid regression) | yes — admissible alternative | clean inheritance from #306 |
| L-3 (continuous spread-embedded regression) | yes — admissible alternative | clean inheritance from #303 |
| L-4 (trinary-with-no-trade) | **NO — not admissible under this amendment** | L-4 is the deferred-not-foreclosed R3 route; mixing R3 + R6-new would conflate two axes |

The choice among L-1 / L-2 / L-3 is open here. The R6-new-A design memo will fix it before any eval runs.

---

## 5. Verdict-tree preservation (H1/H2/H3/H4 unchanged from Phase 26 family)

R6-new-A inherits the Phase 26 verdict tree **without modification**:

- **H1-weak** = test Spearman(score, realised_pnl) > 0.05
- **H1-meaningful** = test Spearman(score, realised_pnl) ≥ 0.10
- **H2** = test realised Sharpe ≥ +0.082 AND ann_pnl ≥ +180
- **H3** = test realised Sharpe > -0.192 (Phase 25 F1 best baseline; **unchanged**)
- **H4** = test realised Sharpe ≥ 0
- **H2 PASS path** = PROMISING_BUT_NEEDS_OOS (NOT ADOPT_CANDIDATE; full 8-gate A0-A5 harness is a separate PR; **ADOPT_CANDIDATE wall preserved**)
- Validation-only cell + threshold selection (test touched once)
- Quantile-of-val {5, 10, 20, 30, 40}% PRIMARY verdict basis
- Absolute thresholds, classification diagnostics, CONCENTRATION_HIGH flag all remain DIAGNOSTIC-ONLY

The amendment **does NOT relax the verdict-tree thresholds**, the H3 baseline, the ADOPT_CANDIDATE wall, or the test-touched-once rule.

---

## 6. Production / γ closure / X-v2 OOS bindings preserved

- **γ closure (PR #279)**: unmodified.
- **X-v2 OOS gating**: remains required before any production deployment.
- **Production v9 20-pair (Phase 9.12 closure)**: untouched.
- **Production deployment for any R6-new variant**: **NOT pre-approved**; requires X-v2 OOS gating per Phase 22 contract.
- **NG#10 / NG#11**: NOT relaxed.

This amendment is **research-only**. It does not move any production stack.

---

## 7. R6-new-A vs Phase 25 F-class sweep — explicit boundary

The amendment is intentionally narrow to keep the Phase 25 / Phase 26 boundary clear:

| Aspect | Phase 25 F-class sweep | R6-new-A under this amendment |
|---|---|---|
| Number of feature groups | 5 (F1..F5) with optional F-extensions | 1 (single closed allowlist) |
| Feature count | ~45 across the full F1..F5 | 2 additions to the minimum set (`pair + direction + atr_at_signal_pip + spread_at_signal_pip` = 4 features) |
| Driving question | "which feature groups carry signal" | "is the minimum feature set the binding constraint on the 3-evidence-point identity" |
| Phase ownership | Phase 25 | Phase 26 |
| Foreclosure status of unused F-classes | F4 / F6 / F5-d / F5-e deferred-not-foreclosed | unchanged; still deferred-not-foreclosed under Phase 25 semantics |
| ADOPT path | Phase 22 contract via X-v2 OOS | unchanged; ADOPT_CANDIDATE wall preserved |

**R6-new-A is a Phase 26 audit of the minimum-feature-set hypothesis. It is NOT a Phase 25 continuation.**

---

## 8. Updated mandatory clauses (clause 6 amended; clauses 1-5 verbatim unchanged)

The full 6-clause block as it applies from this PR forward:

1. **Phase 26 framing.** Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness. *[unchanged]*
2. **Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison / classification-quality columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them. *[unchanged]*
3. **γ closure preservation.** Phase 24 γ hard-close (PR #279) is unmodified. *[unchanged]*
4. **Production-readiness preservation.** X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure) remains untouched. *[unchanged]*
5. **NG#10 / NG#11 not relaxed.** *[unchanged]*
6. **Phase 26 scope (AMENDED).** Phase 26's primary axis is label / target redesign on the 20-pair canonical universe. Phase 26 is NOT a revival of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed under Phase 25 semantics. A narrow feature-widening audit (R6-new-A) is authorised under this scope amendment with a closed allowlist of two features (`atr_at_signal_pip`, `spread_at_signal_pip`); all other features are out of scope until a further scope amendment. R6-new-A is a Phase 26 audit of the minimum-feature-set hypothesis; it is NOT a Phase 25 continuation.

Future PRs in the Phase 26 R6-new sub-stream will quote the amended clause 6 **verbatim**.

---

## 9. What this PR will NOT do

- ❌ Authorise R6-new-A design memo (separate next PR).
- ❌ Authorise R6-new-A implementation or eval.
- ❌ Authorise R6-new-B / R6-new-C / R6-new-D variants.
- ❌ Modify mandatory clauses 1 / 2 / 3 / 4 / 5.
- ❌ Re-open Phase 25 F-class sweep.
- ❌ Modify γ closure (PR #279).
- ❌ Modify X-v2 OOS gating.
- ❌ Pre-approve production deployment for any R6-new variant.
- ❌ Modify any prior verdict (Phase 25 / Phase 26 #284..#310).
- ❌ Retroactively change L-1 / L-2 / L-3 verdict.
- ❌ Foreclose F4 / F6 / F5-d / F5-e (preserved as deferred-not-foreclosed under Phase 25 semantics).
- ❌ Foreclose R3 (L-4 trinary-no-trade) — explicitly still admissible at a future routing review.
- ❌ Foreclose R5 (Phase 26 soft close) — explicitly still admissible at a future routing review.
- ❌ Update MEMORY.md.
- ❌ Auto-route to the R6-new-A design memo PR, the R6-new-A implementation PR, or the R6-new-A eval PR after merge.
- ❌ Touch `src/`, `scripts/`, `tests/`, or `artifacts/`.

---

## 10. PR chain reference

```
Phase 26:
  #299 (kickoff) → #300 (first-scope review)
  → #301 → #302 → #303 → #304 (post-26.0a)
  → #305 → #306 → #307 (post-26.0b)
  → #308 → #309 → #310 (post-26.0c)
  → THIS PR (scope amendment — R6-new prerequisite)
  → R6-new-A design memo (26.0d-α equivalent; next PR; user-authorised separately)
  → R6-new-A eval (26.0d-β equivalent; separate PR after design merges)
  → post-26.0d routing review (next routing pivot OR R3 / R5 admissibility re-examination)
```

L-4 (R3) and R5 (Phase 26 soft close) remain admissible at any subsequent routing review. They are unaffected by this amendment.

---

## 11. Sign-off

After this scope amendment merges:

- **R6-new-A design memo** is the next admissible PR (analogous to 26.0a-α / 26.0b-α / 26.0c-α design memo pattern). The user authorises it explicitly in a separate later instruction.
- The R6-new-A design memo will fix the L-class label (L-1 recommended default per §4) and define the 26.0d-α cell grid (analogous to #308 §7's 2-cell pattern, possibly expanded since the feature axis now has handles).
- After R6-new-A eval closes, a post-26.0d routing review follows the #304 / #307 / #310 pattern.

**This PR stops here.**
