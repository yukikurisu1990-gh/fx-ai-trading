# Phase 26 — Routing Review Post-26.0d

**Type**: doc-only synthesis memo (post-26.0d-β; late Phase 26 with new pivot info)
**Status**: synthesis ONLY; squash-merge approval accepts this review as the Phase 26 post-26.0d routing synthesis, but does NOT by itself authorise any next sub-phase implementation
**Branch**: `research/phase26-routing-review-post-26-0d`
**Base**: master @ ae8d021 (post-PR #313 merge)
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this review as the Phase 26 post-26.0d routing synthesis. It does NOT by itself authorise any next sub-phase implementation. The user explicitly confirms which next branch to pursue — R6-new-B / R6-new-C (each requires a SEPARATE further scope-amendment PR first), R3 (L-4 trinary-with-no-trade), or R5 (Phase 26 soft close memo PR) — in a separate later instruction.*

Same approval-then-defer pattern as #304 / #307 / #310 routing reviews.

---

## 1. R6-new-A 26.0d-β finding (verbatim binding text — DUAL FINDING)

> *Phase 26.0d-β (PR #313) produced two co-existing findings on the same val-selected (cell\*, q\*) record:*
>
> ***Finding 1 (formal verdict ladder)***: ***REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL***. *Val-selected: C02 P(TP)-P(SL), q\*=5%, cutoff=+0.126233. Test n_trades=34,626 ; realised Sharpe = -0.1732 ; ann_pnl = -204,664.4 pip ; formal Spearman(score, realised_pnl) on test = -0.1535. C01 P(TP) cell: test Spearman = +0.0226 (just below H1-weak threshold 0.05). H1-weak FAIL on val-selected cell; H2 / H3 / H4 all FAIL. Cross-cell aggregate: REJECT_NON_DISCRIMINATIVE.*
>
> ***Finding 2 (identity-break detector)***: ***YES_IMPROVED***. *The closed two-feature allowlist (`atr_at_signal_pip` + `spread_at_signal_pip`) DID break the L-1 / L-2 / L-3 identity. Trade count 42,150 → 34,626 ; Sharpe -0.2232 → -0.1732 (+22%) ; ann_pnl -237,310.8 → -204,664.4 pip ; pair concentration shifted from 100% USD_JPY to multi-pair. Feature importance (4-bucket diagnostic, gain): pair=2631, direction=335, atr=3295, spread=2496 — the new features carry weight.*
>
> ***YES_IMPROVED does NOT override the formal verdict ladder.*** *Per the user binding on Decision H interpretation, the formal verdict is fixed as REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL. This PR does NOT produce ADOPT_CANDIDATE. PROMISING_BUT_NEEDS_OOS is NOT applicable because H1 / H2 / H3 remain failed. Sanity probe PASSED before the full sweep (TP 19.2% / SL 74.3% / TIME 6.5%; 0 pairs over 99% TIME share; new-feature NaN rate 0.000%; positivity assertions OK; inherited bid/ask executable harness confirmed). Verdict unchanged from PR #313 closure.*

L-1 / L-2 / L-3 formal verdicts also stand unchanged. Label construction, feature pipeline, and realised-PnL harness behaviour are consistent with spec — this is a substantive finding, not a bug.

---

## 2. Consolidated 4-evidence-point picture

| Aspect | L-3 (PR #303) | L-2 (PR #306) | L-1 (PR #309) | R6-new-A (PR #313) |
|---|---|---|---|---|
| Label class type | continuous (spread-embedded) | continuous (mid-to-mid) | ternary classification | ternary classification (inherited L-1) |
| Feature set | pair + direction | pair + direction | pair + direction | pair + direction + atr_at_signal_pip + spread_at_signal_pip |
| Val-selected cell signature | atr_normalised / Linear / q\*=5% | atr_normalised / Linear / q\*=5% | C01 P(TP) / q\*=5% | C02 P(TP)-P(SL) / q\*=5% |
| Val-selected test Sharpe | -0.2232 | -0.2232 | -0.2232 | **-0.1732** |
| Val-selected test ann_pnl (pip) | -237,310.8 | -237,310.8 | -237,310.8 | **-204,664.4** |
| Val-selected test n_trades | 42,150 | 42,150 | 42,150 | **34,626** |
| Test Spearman (formal H1 signal) | -0.1419 | -0.1139 | -0.0505 (C01) | -0.1535 (C02) / +0.0226 (C01) |
| Pair concentration on test | 100% USD_JPY | 100% USD_JPY | 100% USD_JPY | **multi-pair** (no longer 100%) |
| H1-weak (Spearman > 0.05) | FAIL | FAIL | FAIL | FAIL |
| H2 / H3 / H4 | FAIL / FAIL / FAIL | FAIL / FAIL / FAIL | FAIL / FAIL / FAIL | FAIL / FAIL / FAIL |
| Verdict | REJECT_NON_DISCRIMINATIVE | REJECT_NON_DISCRIMINATIVE | REJECT_NON_DISCRIMINATIVE | REJECT_NON_DISCRIMINATIVE |
| Identity-break vs L-baselines | — (baseline) | — (baseline) | — (baseline) | **YES_IMPROVED** |

The first three evidence points form the identity outcome consolidated at post-26.0c (#310). R6-new-A is the first evidence point in Phase 26 where the val-selected outcome differs from the L-baseline identity — but the formal verdict ladder still rejects.

---

## 3. Two-channel hypothesis update (NEW post-26.0d framing)

Post-26.0c routing review (#310 §3 / §4) framed the binding constraint as a single hypothesis: *"minimum feature set is the binding constraint."* The 26.0d-β dual finding bifurcates this into **two channels** that must be addressed separately.

| Channel | Pre-26.0d status | Post-26.0d status |
|---|---|---|
| **Channel A: feature-set channel** *(does feature widening change selection?)* | unaddressed (untested before R6-new-A) | **PARTIALLY SUPPORTED** — the closed two-feature allowlist changed the val-selected trade set AND improved realised PnL on test. New features carry weight in the LightGBM gain attribution. Subjective / heuristic; not statistically estimated. |
| **Channel B: score-ranking channel** *(does the picker score → PnL ranking monetise on test?)* | binding (L-1/L-2/L-3 H1-weak FAIL with single-pair degenerate ranking) | **STILL BINDING** — formal H1-weak still fails on the val-selected cell on the widened feature set. Per-row score-vs-PnL rank is inverted (-0.1535) on C02 or barely positive (+0.0226) on C01. The 2-feature widening did not lift the val-selected cell over the H1-weak threshold. |

**Synthesis statement (per user binding wording)**: *Feature widening helped, but did not solve score-ranking monetisation.*

The minimum-feature-set hypothesis from post-26.0c is **materially strengthened** on Channel A — pair + direction only was likely a binding limitation. But feature widening alone did **not** produce informative score → PnL ranking on test. Therefore the formal verdict remains REJECT.

The two-channel split is the load-bearing analytical contribution of this routing review. It is the basis on which the §5 routing space is evaluated.

---

## 4. Why this routing review is different from #307 / #310

| Prior review | Picture | Routing options |
|---|---|---|
| Post-26.0a (#304) | 1 evidence point (L-3 reject) | L-1 / L-2 / L-4 / R5 |
| Post-26.0b (#307) | 2 evidence points (L-2 ≡ L-3 identical) | L-1 / L-4 / R6-new / R5 (R6-new surfaced) |
| Post-26.0c (#310) | 3 evidence points (L-1 ≡ L-2 ≡ L-3 identical); strong soft stop MET | R3 / R6-new / R5 |
| **Post-26.0d (this review)** | 4 evidence points; **R6-new-A is NOT identical to the L-baselines**; dual REJECT + YES_IMPROVED; 2-channel hypothesis split | R6-new-B/C / R3 (L-4) / R5 |

Key differences post-26.0d:

- This is the **first** Phase 26 post-routing review where the identity pattern did NOT hold exactly. R6-new-A differs from L-1 / L-2 / L-3 on every realised-PnL metric.
- A genuinely new lever (Channel A feature widening) is demonstrated to alter the val-selected outcome.
- But the formal verdict still rejects because Channel B remains unresolved.
- The user-facing question shifts from *"is there anything left to try?"* (post-26.0c framing) to *"given the lever now exists but isn't sufficient, is the next move worth the cost?"*

---

## 5. Routing space (3 options as specified)

| ID | Path | Cost | Posterior expectation (subjective / heuristic; not statistically estimated) |
|---|---|---|---|
| **R6-new-B / R6-new-C** | Continue feature widening — each variant admits a different closed allowlist (R6-new-B = + Phase 25 F1 vol-expansion features; R6-new-C = + Phase 25 F5 liquidity composites). **Each variant requires a SEPARATE further Phase 26 scope-amendment PR first**, then a separate design memo PR, then a separate eval PR. | high (≥3 PRs per variant; ~1.5 days per variant minimum) | low-to-medium for H1-weak PASS on val-selected cell ; low for H2 PASS ; medium for further identity-break with additional Sharpe lift. All subjective / heuristic. |
| **R3** | L-4 trinary-with-no-trade — last unexercised L-class under the original Phase 26 scope; admissible without scope amendment | medium | low — Channel B remains unresolved and L-1 / L-2 / L-3 label changes did not differentiate; L-4 likely repeats the L-baseline identity at minimum feature set. Subjective / heuristic. |
| **R5** | Phase 26 soft close — admissible and now evidence-consistent. **This PR does NOT execute closure.** R5 would be a separate later closure memo PR (analogous to PR #298 Phase 25 closure). L-4 + R6-new-B/C preserved as deferred-not-foreclosed if R5 is chosen. | very low (single doc PR) | n/a (phase-management) |

**Posterior expectations are subjective / heuristic / not statistically estimated.** They are discussion anchors only. The user reweights freely.

---

## 6. R6-new-B / R6-new-C deep-dive (continuation; each requires further scope amendment)

> ***R6-new-B and R6-new-C cannot start directly from this review.*** *Each variant requires a SEPARATE Phase 26 scope-amendment doc-only PR (analogous to PR #311) admitting a different closed allowlist before the design memo PR can begin. The amended clause 6 from PR #311 §8 explicitly states "all other features are out of scope until a further scope amendment."*

> ***R6-new-B and R6-new-C are NOT presented here as an automatic continuation.*** *Each is a distinct multi-PR sequence with its own cost-benefit weighting. The R6-new-A YES_IMPROVED finding is encouraging for Channel A but does not by itself authorise the further amendments.*

### 6.1 Variant scope (verbatim from #310 §6.1 / #311 §3.2 exclusion list)

| Variant | Allowlist increment | Phase-26 / Phase-25 boundary status |
|---|---|---|
| **R6-new-B** | + Phase 25 F1 best features (vol expansion / compression) | moderate distance from Phase 26 scope — re-engages F1 family; partially blurs Phase 25 / Phase 26 boundary |
| **R6-new-C** | + Phase 25 F5 best features (liquidity / spread / volume composites) | moderate distance — re-engages F5 family |

> ***R6-new-D (full Phase 25 F1..F5 ~45-feature set) is NOT a routing option in this review.*** *It would functionally restart Phase 25 and is outside the admissible scope of this review.*

### 6.2 Cost framing per variant

| Step | Estimated cost |
|---|---|
| Further Phase 26 scope-amendment doc-only PR | ~3-4 hours |
| Design memo PR (analogous to 26.0d-α / PR #312) | ~half day |
| Eval implementation + sanity probe + sweep + report PR (analogous to 26.0d-β / PR #313) | ~half to full day |
| **Per-variant total** | **~1.5-2 days minimum** |

Each variant is independent. Running both is ~3 days minimum and ~6 PRs.

### 6.3 Why this might work (subjective)

R6-new-A demonstrated +22% Sharpe improvement and trade-set differentiation from 2 features. F1 (vol structure) or F5 (liquidity) features add structural signals that may further break the score-ranking inversion on Channel B.

### 6.4 Why this might NOT work (subjective)

The H1-weak failure pattern across L-1 / L-2 / L-3 / R6-new-A suggests the score-ranking channel may not respond to features added under the current LightGBM multiclass + quantile-of-val framework. The R6-new-A lift may be a one-shot effect of geometric / liquidity proxies (`atr_at_signal_pip`, `spread_at_signal_pip`), not a generalisable feature-widening trend.

Both lines of reasoning are subjective / heuristic / not statistically estimated.

---

## 7. R3 (L-4 trinary-with-no-trade) — admissibility framing

L-4 status is **unchanged** from post-26.0c (#310 §7): L-4 remains the last unexercised admissible L-class under the original Phase 26 scope, with no scope amendment required.

> ***L-4 remains admissible and not foreclosed.*** *However, the honest framing post-26.0d is that L-4 is likely low value: Channel B remains unresolved across L-1 / L-2 / L-3, and label changes at the minimum feature set did not differentiate. Adding a 4th class boundary (no-trade) without addressing Channel A is unlikely to produce a differentiated score → PnL ranking on test.*

L-4 is structurally **less likely** to differentiate post-26.0d than it was post-26.0c, because:

- The Channel A lever (now demonstrated on R6-new-A) is feature-set-side, NOT label-shape-side.
- L-4 keeps the feature set at the minimum and varies only the class boundary.
- The 3-evidence-point identity pattern (L-1 / L-2 / L-3 same val-selected outcome) directly speaks against label-shape differentiation at minimum features.

L-4 is **NOT foreclosed** by this review. It remains deferred-not-foreclosed under either R6-new-B/C selection or R5 selection.

---

## 8. R5 (Phase 26 soft close) — admissibility framing

The strong soft stop condition (3+ L-classes confirm gap) was MET at post-26.0c (#310 §10). Post-26.0d, the picture is more nuanced.

> ***R5 is admissible and now evidence-consistent.*** *The 4-evidence-point picture (3 L-class identity + 1 feature-widening identity-break with formal reject) is informationally consistent with the Phase 25 #297 / #298 closure pattern after 5 F-class evidence points all confirmed structural-gap. The dual REJECT + YES_IMPROVED finding shows the lever exists (Channel A) but does not by itself unblock ADOPT (Channel B remains binding).*
>
> ***However, this PR does NOT execute Phase 26 closure.*** *R5 if picked is a SEPARATE later closure memo PR (analogous to PR #298 Phase 25 closure pattern). L-4 (R3) and R6-new-B / R6-new-C (each with its own further scope amendment required) remain explicitly deferred-not-foreclosed if R5 is later chosen.*

| Stop level | Trigger | Status post-26.0d |
|---|---|---|
| Definitive stop | All 4 L-classes tested AND no H2 PASS | NOT met (L-4 untested) |
| **Strong soft stop** | 3+ L-classes confirm gap | **MET (L-1 + L-2 + L-3)** — preserved from #310 |
| 4-evidence-point dual-channel finding | Channel A lever exists; Channel B unresolved | informational — strengthens the case for R5 without promoting it to definitive |
| L-1 ≡ L-2 ≡ L-3 identity finding | label-class axis NOT load-bearing for the structural-gap | **CONFIRMED (binding text #310 §3)** |

R5 if picked preserves Phase 26 closure semantics analogous to Phase 25 #297 / #298 with an additional "lever-exists" preservation note documenting Channel A.

---

## 9. Comparison vs Phase 25 routing pattern + earlier Phase 26 routing reviews

| Phase 25 (feature-axis sweep) | Phase 26 (label + narrow-feature) |
|---|---|
| 5 F-class evidence points (F1..F5) all confirmed structural-gap | 4 evidence points: 3 identical (L-1 / L-2 / L-3), 1 partial differentiation (R6-new-A) with formal reject |
| F-class space CLOSED after F5 (LAST high-orthogonality F-class) | L-class space: 1 remaining admissible (L-4); R6-new-A exercised; R6-new-B / R6-new-C admissible only under further scope amendment |
| Routing review post-F5 (#297) → R5 (soft close) merged via #298 | Routing review post-26.0d — strong soft stop MET (since #310) and now evidence-consistent; but with a new lever (Channel A) on the table that complicates the close vs continue trade-off |

Phase 26 is now **late phase but not as cleanly converged as Phase 25 was at post-F5**. The dual REJECT + YES_IMPROVED finding creates the first non-trivial "continue vs close" trade-off in Phase 26's routing history.

---

## 10. Stop conditions update

| Stop level | Trigger | Status post-26.0d |
|---|---|---|
| Definitive stop | All 4 L-classes tested AND no H2 PASS | NOT met (L-4 untested) |
| **Strong soft stop** | 3+ L-classes confirm gap | **MET (preserved from #310)** |
| 4-evidence-point dual-channel finding | 3 L-class identity + R6-new-A YES_IMPROVED with formal reject | informational; strengthens case for R5 without promoting to definitive |
| 2-channel hypothesis split (Channel A partial / Channel B binding) | identified at this review | **load-bearing for §5 routing space evaluation** |

> *Phase 26 has reached a strong soft stop with a documented Channel A lever. R5 is admissible. R6-new-B / R6-new-C are admissible (each with further scope amendment). R3 (L-4) is admissible. The user picks.*

---

## 11. User-facing decision matrix

| Choice | Cost | Expected payoff (subjective / heuristic; not statistically estimated) | Closes Phase 26? |
|---|---|---|---|
| R6-new-B / R6-new-C → further feature widening (each variant) | high (≥3 PRs per variant; ~1.5-2 days per variant) | medium for trade-set differentiation; low-to-medium for H1-weak PASS; low for H2 PASS | No (continues Phase 26 under further-amended scope) |
| R3 → L-4 trinary-no-trade | medium | low (likely identity repeat at minimum feature set; Channel B unchanged) | No (completes L-class space taxonomy; L-4 not foreclosed even if not picked) |
| R5 → Phase 26 soft close (separate closure memo PR) | very low | n/a (phase-management) | YES (executed via separate later closure memo PR; preserves L-4 + R6-new-B/C as deferred-not-foreclosed) |

> Posterior expectation tags are subjective / heuristic / not statistically estimated.

---

## 12. Informational next-path framing (NOT a routing decision)

Three characterisations are informationally efficient. None is a routing recommendation. The user picks separately.

| Characterisation | Detail |
|---|---|
| **Most direct continuation of the surviving Channel A lever** | **R6-new-B or R6-new-C** — adds Phase 25 F1 or F5 features to the closed allowlist via a SEPARATE further scope amendment per variant. Tests if feature widening compounds the R6-new-A Sharpe lift on Channel A and if it lifts the H1-weak threshold on Channel B. Each variant is its own multi-PR sequence (scope amendment + design memo + eval). |
| **Most Phase-26-faithful completion path** | **R3 (L-4)** — completes the admissible L-class space taxonomy without scope amendment. Honest framing: post-26.0d evidence (4-point picture; 2-channel split) strengthens the suggestion that Channel B (label shape) is not the active lever; L-4 likely repeats the L-1 / L-2 / L-3 identity pattern. Hygienic taxonomy completion. |
| **Most evidence-consistent close path** | **R5** — strong soft stop MET (since #310) AND now evidence-consistent with the 4-evidence-point picture. Executed via a SEPARATE later closure memo PR. Preserves L-4 + R6-new-B / R6-new-C as deferred-not-foreclosed. Consistent with Phase 25 #297 / #298 closure pattern with an additional "lever-exists" preservation note. |

All three characterisations are informational. The user picks separately. **This PR does NOT pick.**

---

## 13. Mandatory clauses (verbatim; clause 6 = AMENDED per #311 §8)

1. **Phase 26 framing.** Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness. *[unchanged]*
2. **Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison / classification-quality / feature-importance columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them. *[unchanged]*
3. **γ closure preservation.** Phase 24 γ hard-close (PR #279) is unmodified. *[unchanged]*
4. **Production-readiness preservation.** X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure) remains untouched. *[unchanged]*
5. **NG#10 / NG#11 not relaxed.** *[unchanged]*
6. **Phase 26 scope (AMENDED).** Phase 26's primary axis is label / target redesign on the 20-pair canonical universe. Phase 26 is NOT a revival of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed under Phase 25 semantics. A narrow feature-widening audit (R6-new-A) is authorised under the scope amendment in PR #311 with a closed allowlist of two features (`atr_at_signal_pip`, `spread_at_signal_pip`); all other features are out of scope until a further scope amendment. R6-new-A is a Phase 26 audit of the minimum-feature-set hypothesis; it is NOT a Phase 25 continuation. *[AMENDED per PR #311 §8 — VERBATIM]*

R6-new-B / R6-new-C each require a SEPARATE further scope amendment to admit additional features. R6-new-D is not authorised under any scope amendment currently on the table.

---

## 14. PR chain reference

```
Phase 26:
  #299 (kickoff) → #300 (first-scope review)
  → #301 → #302 → #303 → #304 (post-26.0a)
  → #305 → #306 → #307 (post-26.0b)
  → #308 → #309 → #310 (post-26.0c)
  → #311 (scope amendment) → #312 (R6-new-A design)
  → #313 (R6-new-A eval; dual REJECT + YES_IMPROVED)
  → THIS PR (post-26.0d routing review)
  → user picks one of:
       R6-new-B: further scope amendment + design + eval (≥3 PRs)
       R6-new-C: further scope amendment + design + eval (≥3 PRs)
       R3:      L-4 design + eval (2 PRs)
       R5:      Phase 26 soft-closure memo (1 PR)
```

L-4 (R3) and R6-new-B / R6-new-C remain deferred-not-foreclosed under any choice (including R5).

---

## 15. What this PR will NOT do

- ❌ Pick a routing decision (R6-new-B / R6-new-C / R3 / R5).
- ❌ Initiate any L-class or feature-widening implementation.
- ❌ Write a further Phase 26 scope-amendment PR (R6-new-B / R6-new-C prerequisite).
- ❌ Execute Phase 26 closure (R5 closure memo is a separate later PR).
- ❌ Modify any prior verdict (Phase 25 / Phase 26 #284..#313).
- ❌ Retroactively change L-1 / L-2 / L-3 / R6-new-A formal verdict.
- ❌ Use the R6-new-A YES_IMPROVED identity-break finding to override the formal verdict ladder.
- ❌ Mint ADOPT_CANDIDATE for R6-new-A.
- ❌ Mint PROMISING_BUT_NEEDS_OOS for R6-new-A (H1 / H2 / H3 remain failed).
- ❌ Modify γ closure (PR #279).
- ❌ Modify X-v2 OOS gating.
- ❌ Pre-approve production deployment.
- ❌ Update MEMORY.md.
- ❌ Foreclose L-4 (R3) — preserved as deferred-not-foreclosed.
- ❌ Foreclose R6-new-B / R6-new-C — preserved as deferred-not-foreclosed.
- ❌ Foreclose F4 / F6 / F5-d / F5-e (Phase 25 deferred-not-foreclosed).
- ❌ Authorise R6-new-D as a routing option.
- ❌ Auto-route to any sub-phase after merge.
- ❌ Touch `src/`, `scripts/`, `tests/`, or `artifacts/`.

---

## 16. Sign-off

After the user picks one of R6-new-B / R6-new-C / R3 / R5, the next PR is one of:

- **R6-new-B**: a further Phase 26 scope-amendment doc-only PR (~150-200 lines) admitting Phase 25 F1 features to a new closed allowlist; then 26.0e-α R6-new-B design memo PR; then 26.0e-β R6-new-B eval PR (≥3 PRs total).
- **R6-new-C**: analogous chain for Phase 25 F5 features (≥3 PRs total).
- **R3**: Phase 26.0e-α L-4 design memo (analogous to 26.0a-α / 26.0b-α / 26.0c-α pattern); then 26.0e-β L-4 eval PR.
- **R5**: Phase 26 soft-closure memo PR (analogous to PR #298 Phase 25 closure pattern; late-phase soft close; preserves L-4 + R6-new-B / R6-new-C as deferred-not-foreclosed).

The user picks. **This PR stops here.**
