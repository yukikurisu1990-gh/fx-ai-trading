# Phase 26 — Routing Review Post-26.0c

**Type**: doc-only synthesis memo (post-26.0c-β; late Phase 26)
**Status**: synthesis ONLY; squash-merge approval accepts this review as the Phase 26 post-26.0c routing synthesis, but does NOT by itself authorise any next sub-phase implementation
**Branch**: `research/phase26-routing-review-post-26-0c`
**Base**: master @ 3fca280 (post-PR #309 merge)
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this review as the Phase 26 post-26.0c routing synthesis. It does NOT by itself authorise any next sub-phase implementation. The user explicitly confirms which next branch to pursue — R3 (L-4 trinary-no-trade), R6-new (feature widening pivot; scope amendment first), or R5 (soft close) — in a separate later instruction.*

Same pattern as #304 / #307 approval semantics: accept synthesis, defer next implementation.

---

## 1. L-1 26.0c-β finding (binding text from PR #309)

> *Phase 26.0c-β (PR #309) formally produced **REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL** on both formal cells. Val-selected: C01 P(TP), q\*=5%, cutoff = +0.398615. Test: n_trades = 42,150 ; realised Sharpe = -0.2232 ; ann_pnl = -237,310.8 pip. Formal Spearman(picker score, realised_pnl) on test: -0.0505 (C01 P(TP)) / -0.1077 (C02 P(TP)-P(SL)) — both fail H1-weak (> 0.05). All 42,150 trades concentrate 100% in USD_JPY (CONCENTRATION_HIGH=True, diagnostic-only). **The L-1 val-selected (cell\*, q\*) test realised-PnL outcome is IDENTICAL to L-2 (PR #306) and L-3 (PR #303) on every formal metric: same trade set, same Sharpe, same ann_pnl, same pair concentration.** Sanity probe PASSED before the full sweep (TP 19.2% / SL 74.3% / TIME 6.5%; 0 pairs over 99% TIME share; inherited `_compute_realised_barrier_pnl` bid/ask executable harness confirmed). Verdict unchanged from PR #309 closure.*

All three formal verdicts (L-1 / L-2 / L-3) stand. Nothing in this memo retroactively changes them. Label construction and realised-PnL harness behaviour are consistent with spec — this is not a bug, it is a substantive finding.

---

## 2. Consolidated L-1 / L-2 / L-3 evidence (3 formal verdicts; mandatory comparison table)

All three Phase 26 sub-phase β evals produced **REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL**. The val-selected (cell\*, q\*) realised-PnL outcomes are essentially identical:

| Aspect | L-3 (PR #303) | L-2 (PR #306) | L-1 (PR #309) |
|---|---|---|---|
| Label class type | continuous regression (spread-embedded) | continuous regression (mid-to-mid; spread NOT embedded) | ternary classification {TP, SL, TIME} |
| Val-selected cell | atr_normalised / Linear / q\*=5% | atr_normalised / Linear / q\*=5% | C01 picker=P(TP) / q\*=5% |
| Val-selected test realised Sharpe | -0.2232 | -0.2232 | **-0.2232** |
| Val-selected test ann_pnl (pip) | -237,310.8 | -237,310.8 | **-237,310.8** |
| Val-selected test n_trades | 42,150 | 42,150 | **42,150** |
| Test Spearman (formal H1 signal) | -0.1419 | -0.1139 | -0.0505 (C01) / -0.1077 (C02) |
| Pair concentration on test | 100% USD_JPY | 100% USD_JPY | **100% USD_JPY** |
| H1-weak (Spearman > 0.05) | FAIL | FAIL | FAIL |
| H2 / H3 / H4 | FAIL / FAIL / FAIL | FAIL / FAIL / FAIL | FAIL / FAIL / FAIL |
| Verdict | REJECT_NON_DISCRIMINATIVE | REJECT_NON_DISCRIMINATIVE | REJECT_NON_DISCRIMINATIVE |

L-1 sanity probe also produced a label-distribution snapshot worth recording:

- TP share: 19.2% (overall, train); SL: 74.3%; TIME: 6.5%
- 0 pairs over 99% TIME-class share on train (no degeneracy)
- Inherited `_compute_realised_barrier_pnl` bid/ask executable treatment confirmed

---

## 3. Load-bearing observation from the 3-evidence-point consolidation

> *Three label classes — L-3 (continuous regression, spread embedded in target), L-2 (continuous regression, mid-to-mid; spread NOT embedded), L-1 (ternary classification {TP, SL, TIME}) — all converge to the **IDENTICAL** val-selected trade set on test (n=42,150 ; Sharpe = -0.2232 ; ann_pnl = -237,310.8 ; 100% USD_JPY concentration). The label-class axis spans regression-vs-classification AND spread-embedded-vs-not, yet the formal realised-PnL outcome is invariant across all three. This is the strongest evidence point Phase 26 has produced. The post-26.0b §3 observation is now upgraded from "leading hypothesis" to a **3-evidence-point load-bearing finding**.*

This is a finding, not a proof. It does not foreclose that there exists some untested label-class configuration that would differentiate. It only says that across the admissible L-class axis we have exercised (3 of 4 disjoint cases), the realised-PnL identity holds.

---

## 4. Structural-gap hypothesis status update

| Hypothesis | Pre-26.0c (#307 status) | Post-26.0c (this review) |
|---|---|---|
| **Minimum feature set (`pair + direction`) is the binding constraint** | leading hypothesis | **3-evidence-point load-bearing finding (strongest current hypothesis)** |
| Continuous-vs-classification label axis is binding | unaddressed (continuous-only at #307) | **strongly disfavoured** (L-1 ternary classification = L-2 = L-3) |
| Spread-embedded-vs-not target is binding | rejected at #307 §3 | rejected (unchanged) |
| Label class shape (any L-class) is binding | partially testable | strongly disfavoured (3 disjoint cases all REJECT) |
| ATR-normalisation pair-bias is the sole failure mode | partial | partial (100% USD_JPY recurs across all 3; this concentration is **diagnostic-only** and not used in formal verdict) |
| Some untested label-class configuration could differentiate | possible | not ruled out (L-4 untested) |

The phrasing "load-bearing finding" / "strongest current hypothesis" is deliberate. It is not framed as a proof, and it is not framed as the only remaining hypothesis.

---

## 5. Routing space (3 options)

R1 (L-1 ternary) has been exercised in PR #309 and is removed from the routing space. Three options remain:

| ID | Path | Cost | Posterior expectation (qualitative; subjective / heuristic; not statistically estimated) |
|---|---|---|---|
| **R3** | L-4 trinary-with-no-trade (last admissible L-class) | medium | low (3-evidence-point identity pattern strongly disfavours another label-shape lever) |
| **R6-new** | Feature widening pivot — keep label fixed and widen feature set beyond `pair + direction`; requires Phase 26 scope-amendment PR first | medium-high | medium-to-high (the only lever the 3 evidence points have NOT touched) |
| **R5** | Phase 26 soft close | very low | n/a (phase-management) |

**Posterior expectations are subjective / heuristic / not statistically estimated.** They are discussion anchors only. The user reweights freely.

---

## 6. R6-new (feature widening pivot) — deep-dive (CANNOT start directly)

R6-new becomes the most direct test of the surviving load-bearing hypothesis (§3 / §4), but it is structurally constrained.

> ***R6-new cannot start directly from this review. It requires a Phase 26 scope-amendment doc-only PR first.*** *Phase 26 kickoff (PR #299) §5 explicitly states "Phase 26 is NOT a continuation of Phase 25's feature-axis sweep." The post-26.0b routing review (#307 §6) and the 26.0c-α design memo (#308 §12 clause 6) both preserve this scope. R6-new would re-introduce features beyond the minimum set, blurring the Phase 25 / Phase 26 boundary. The scope-amendment PR must explicitly authorise the feature-widening direction and define which feature additions are admissible before R6-new can begin.*

> ***R6-new-A is a minimal feature-widening audit, NOT a revival of the full Phase 25 F-class sweep.*** *The intent is to test whether the minimum feature set is the binding constraint, not to re-enter Phase 25's 5-class feature exploration.*

### 6.1 R6-new variants (inherited verbatim from #307 §6.1)

| Variant | Feature additions | Phase-26-scope distance |
|---|---|---|
| **R6-new-A** | `pair + direction` + `atr_at_signal_pip` + `spread_at_signal_pip` (both already in 25.0a-β dataset) | closest to Phase 26 scope — minimal feature-widening audit |
| **R6-new-B** | R6-new-A + Phase 25 F1 best features (vol expansion / compression) | moderate distance — re-engages F1 |
| **R6-new-C** | R6-new-A + Phase 25 F5 best features (liquidity / spread / volume) | moderate distance — re-engages F5 |
| **R6-new-D** | full Phase 25 F1-F5 feature set (~45 features) | farthest from Phase 26 scope — equivalent to Phase 25 continuation under fixed label |

R6-new-A is the lightest variant and the most direct test of "is the minimum feature set the binding constraint?" without re-entering Phase 25's full feature-axis sweep.

### 6.2 Cost / risk

- Cost: ~1 day for the scope-amendment doc + ~1 day for the 26.0d-α R6-new-A design memo + ~30 min sweep runtime per variant.
- Risk: even with widened features, the 100% USD_JPY concentration on raw_pip cells (independent of ATR-normalisation) appeared across all 3 evidence points; widened features may not change this, or they may (the load-bearing hypothesis from §3 / §4 says they might).

---

## 7. R3 (L-4 trinary-no-trade) — admissibility framing

L-4 (trinary classification: TP / SL / TIME-or-no-trade, with the 4th "no-trade" class distinguished from time-exit) is the last unexercised admissible L-class.

> ***L-4 remains admissible*** *as the last unexercised L-class under the Phase 26 scope-binding. It tests whether adding a 4th class (no-trade) to the L-1 ternary structure produces a differentiated ranking signal. **L-4 is not foreclosed by this review.***

> ***Honest framing*** *: given the 3-evidence-point identity pattern (L-1 = L-2 = L-3), running L-4 is **likely to produce the same identity result** on val-selected realised PnL at the minimum feature set. The argument for running L-4 anyway is "complete the L-class space hygienically before any Phase 26 close decision." The argument against is "the 3-evidence-point pattern already covers regression-vs-classification AND spread-embedded-vs-not; a 4th class is unlikely to break the identity."*

| Aspect | L-4 trinary-no-trade |
|---|---|
| Label type | classification with explicit no-trade class (4 classes total: TP / SL / TIME-trade / no-trade) |
| Feature set | `pair + direction` only (Phase 26 §5.1 binding **preserved**) |
| Distance from 3-evidence-point load-bearing hypothesis | medium — still minimum feature set, still classification family |
| Risk of same identity result as L-1 / L-2 / L-3 | high (subjective / heuristic) |
| Phase 26 scope fidelity | full — no scope amendment needed |
| Forecloses on close decision | NO — L-4 remains deferred-not-foreclosed if R5 is selected before R3 |

---

## 8. R5 (Phase 26 soft close) — admissibility framing

The post-26.0b review (#307 §10) noted soft stop conditions met but did NOT identify R5 as default. The post-26.0c picture is stronger:

> ***Strong soft stop condition (3+ L-classes confirm gap) is MET*** *post-26.0c. The 3-evidence-point identity pattern (L-1 = L-2 = L-3 on val-selected realised PnL) is informationally consistent with the Phase 25 #297 soft-close pattern (5 F-class evidence points all confirmed structural-gap). However, **this PR does NOT execute Phase 26 closure.** R5 is the routing pointer to a separate Phase 26 closure memo PR (analogous to PR #298 Phase 25 closure), which the user authorises explicitly.*

| Stop level | Trigger | Status post-26.0c |
|---|---|---|
| Definitive stop | All 4 L-classes tested AND no H2 PASS | NOT met (L-4 untested) |
| **Strong soft stop** | **3+ L-classes confirm gap** | **MET (L-1 + L-2 + L-3)** |
| Soft stop (post-26.0b) | 2 L-classes (regression family) identical | already met at #307 |
| 3-evidence-point identity finding | spread-embedding + continuous-vs-classification both NOT load-bearing | **CONFIRMED (binding text §3)** |

If the user picks R5:
- A separate Phase 26 soft-closure memo PR follows the #298 pattern.
- L-4 (R3) and R6-new (variants A/B/C/D) are explicitly **deferred-not-foreclosed**, analogous to Phase 25 F4 / F6 / F5-d / F5-e closure semantics in #297 / #298.
- γ closure PR #279, X-v2 OOS gating, production v9 20-pair (Phase 9.12) are unaffected.

---

## 9. Comparison vs Phase 25 routing pattern + earlier Phase 26 routing reviews

| Phase 25 (feature-axis sweep) | Phase 26 (label-target redesign) |
|---|---|
| 5 F-class evidence points (F1..F5) all confirmed structural-gap | **3 L-class evidence points (L-1 + L-2 + L-3) all confirmed structural-gap** |
| F-class space CLOSED after F5 (LAST high-orthogonality F-class) | L-class space: 1 remaining admissible (L-4) + 1 NEW option (R6-new, scope-amend required) + 1 close path (R5) |
| Routing review post-F5 (#297) → R5 (soft close) merged via #298 | Routing review post-26.0c — same shape, **strong soft stop MET**, but does NOT execute closure in this PR |

**Phase 26 is now late phase**: 3 of 4 admissible L-classes evaluated + 1 NEW routing option (R6-new) surfaced + soft-close (R5) condition met.

---

## 10. Stop conditions (updated)

| Stop level | Trigger | Status post-26.0c |
|---|---|---|
| Definitive stop | All 4 L-classes tested AND no H2 PASS | NOT met (L-4 untested) |
| **Strong soft stop** | 3+ L-classes confirm gap | **MET** |
| Soft stop (post-26.0b) | 2 L-classes (regression family) identical | already met (#307) |
| L-1 = L-2 = L-3 identity finding | label-class axis NOT load-bearing for the structural-gap | **CONFIRMED** (binding text §3) |

> *Phase 26 has reached a strong soft stop. R5 (soft close) is admissible. R3 (L-4) and R6-new are also admissible. The user picks.*

---

## 11. User-facing decision matrix

| Choice | Cost | Expected payoff (subjective / heuristic; not statistically estimated) | Closes Phase 26? |
|---|---|---|---|
| R3 → L-4 trinary-no-trade | medium | low (likely identity repeat) | No (completes L-class space; L-4 not foreclosed even if not picked) |
| R6-new → feature widening | medium-high (scope amendment + design memo + eval) | medium-to-high (only untouched lever) | No (continues Phase 26 under amended scope) |
| R5 → Phase 26 soft close | very low | n/a (phase-management) | YES (executed via a separate closure memo PR; preserves L-4 + R6-new as deferred-not-foreclosed) |

> Posterior payoff tags are subjective / heuristic / not statistically estimated. They are discussion anchors only.

---

## 12. Informational next-path framing (NOT a routing decision)

Three characterisations are informationally efficient, but none of them is a routing recommendation. The user picks separately.

| Characterisation | Detail |
|---|---|
| **Most direct test of the surviving load-bearing hypothesis (§3 / §4)** | **R6-new-A** — feature widening with `atr_at_signal_pip` + `spread_at_signal_pip`. Directly tests whether the minimum feature set is binding. **Cannot start directly from this review; requires a Phase 26 scope-amendment doc-only PR first (§6 binding).** R6-new-A is a minimal feature-widening audit, NOT a Phase 25 F-class sweep revival. |
| **Most Phase-26-faithful completion path** | **R3 (L-4 trinary-no-trade)** — completes the admissible L-class space without scope amendment. Honest framing: the 3-evidence-point pattern suggests L-4 likely repeats the identity outcome; the value is hygienic taxonomy completion before any close decision. |
| **Most evidence-consistent close path** | **R5 (Phase 26 soft close)** — informationally consistent with the Phase 25 #297 / #298 closure pattern after 5 F-class evidence points. Strong soft stop condition is met. Executed via a separate closure memo PR; preserves L-4 + R6-new as deferred-not-foreclosed. |

All three characterisations are informational. The user picks separately. This PR does NOT pick.

---

## 13. Mandatory clauses (verbatim, 6 total — inherited unchanged from #299 §7 / 26.0a-α §9 / rev1 §11 / 26.0b-α §9 / 26.0b post-routing-review §12 / 26.0c-α §12)

1. **Phase 26 framing** — Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.
2. **Diagnostic columns prohibition** — Calibration / threshold-sweep / directional-comparison / classification-quality columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.
3. **γ closure preservation** — Phase 24 γ hard-close (PR #279) is unmodified.
4. **Production-readiness preservation** — X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure) remains untouched.
5. **NG#10 / NG#11 not relaxed**.
6. **Phase 26 scope** — Phase 26 is NOT a continuation of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed. **(R6-new in §6 requires explicit scope amendment per §6 binding.)**

---

## 14. PR chain reference

```
Phase 26:
  #299 (kickoff) → #300 (first-scope review)
  → #301 (26.0a-α L-3 design) → #302 (26.0a-α-rev1)
  → #303 (26.0a-β rev1 L-3 eval)
  → #304 (post-26.0a routing review)
  → #305 (26.0b-α L-2 design) → #306 (26.0b-β L-2 eval)
  → #307 (post-26.0b routing review)
  → #308 (26.0c-α L-1 design) → #309 (26.0c-β L-1 eval)
  → THIS PR (post-26.0c routing review)
  → R3 (L-4) | R6-new (feature widening; scope amendment first) | R5 (soft close memo) — user picks
```

---

## 15. What this PR will NOT do

- ❌ Pick a routing decision (R3 / R6-new / R5).
- ❌ Initiate any L-class or feature-widening implementation.
- ❌ Write a Phase 26 scope-amendment PR (R6-new prerequisite if picked).
- ❌ Execute Phase 26 closure (R5 closure memo is a separate later PR).
- ❌ Modify any prior verdict (Phase 25 / Phase 26 #284..#309).
- ❌ Retroactively change L-3 / L-2 / L-1 verdict.
- ❌ Modify γ closure (PR #279).
- ❌ Pre-approve production deployment.
- ❌ Update MEMORY.md.
- ❌ Foreclose L-4 (R3) — explicitly deferred-not-foreclosed.
- ❌ Foreclose R6-new variants A/B/C/D — explicitly deferred-not-foreclosed.
- ❌ Foreclose F4 / F6 / F5-d / F5-e (Phase 25 deferred extensions).
- ❌ Use diagnostic D-1..D-3 / Spearman / AUC / κ / logloss / confusion matrix / per-class accuracy / CONCENTRATION_HIGH to feed any verdict-routing pipeline.
- ❌ Use the 3-evidence-point identity finding (§3) to retroactively change any verdict.
- ❌ Recommend R6-new without flagging the Phase 26 §5 scope-amendment requirement.
- ❌ Auto-route to any sub-phase after merge.
- ❌ Touch `src/`, `scripts/`, `tests/`, or `artifacts/`.

---

## 16. Sign-off

After the user picks one of R3 / R6-new / R5, the next PR is one of:

- **R3**: Phase 26.0d-α L-4 trinary-no-trade design memo (analogous to 26.0a-α / 26.0b-α / 26.0c-α design pattern).
- **R6-new**: Phase 26 scope-amendment doc-only PR (mini, ~150-200 lines) first, then 26.0d-α R6-new-A feature-widening design memo on a separate later PR.
- **R5**: Phase 26 soft-closure memo PR (analogous to PR #298 Phase 25 closure pattern; late-phase soft close; preserves L-4 + R6-new as deferred-not-foreclosed).

The user picks. **This PR stops here.**
