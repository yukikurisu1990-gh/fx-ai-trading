# Phase 26 — Routing Review Post-26.0b

**Type**: doc-only synthesis memo (post-26.0b-β; mid-late Phase 26)
**Status**: synthesis ONLY; squash-merge approval accepts this review as the Phase 26 post-26.0b routing synthesis, but does NOT by itself authorise any next sub-phase implementation
**Branch**: `research/phase26-routing-review-post-26-0b`
**Base**: master @ 0ebde1c (post-PR #306 merge)
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this review as the Phase 26 post-26.0b routing synthesis. It does NOT by itself authorise any next sub-phase implementation. The user explicitly confirms which next branch to pursue — R1 (L-1 ternary), R3 (L-4 trinary-no-trade), R6-new (feature widening pivot), or R5 (soft close) — in a separate later instruction.*

Same pattern as #297 / #300 / #302 / #304 approval semantics: accept synthesis, defer next implementation.

---

## 1. L-2 26.0b-β finding (binding text from PR #306)

> *Phase 26.0b-β (PR #306) formally produced **REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL**. The validation-selected cell was `scale=atr_normalised / clip=none / model=LinearRegression / q*=5%, cutoff=-0.2574`. On the test set: n_trades=42,150 ; realised Sharpe = -0.2232 ; ann_pnl = -237,310.8 pip ; test Spearman = -0.1139. All 42,150 trades concentrated 100% in USD_JPY (CONCENTRATION_HIGH=True). **The L-2 val-selected cell is IDENTICAL to L-3's val-selected cell on every realised-PnL metric** — same scale/clip/model/q\*, same trades, same Sharpe, same ann_pnl. Test Spearman is -0.1139 (vs L-3's -0.1419 — slightly less negative due to the constant offset between L-2 and L-3 predictions, which does NOT change top-5% ranking).*

Both L-2 and L-3 formal verdicts stand. Nothing in this memo retroactively changes them.

---

## 2. Consolidated L-2 / L-3 evidence (2 formal verdicts + diagnostic observations)

Both L-2 and L-3 produced **REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL**. The val-selected metrics are essentially identical:

| Metric | L-3 (#303) | L-2 (#306) | Diff |
|---|---|---|---|
| Val-selected cell | atr_normalised / none / Linear / q\*=5% | atr_normalised / none / Linear / q\*=5% | identical |
| Val-selected test realised Sharpe | -0.2232 | **-0.2232** | 0 |
| Val-selected test ann_pnl | -237,310.8 | -237,310.8 | 0 |
| Val-selected test n_trades | 42,150 | 42,150 | 0 |
| Val-selected test Spearman | -0.1419 | -0.1139 | +0.028 (less negative) |
| Best-by-test-Spearman diagnostic | +0.3836 | +0.3845 | +0.001 |
| Best-by-test-Sharpe diagnostic | -0.2232 | -0.2232 | 0 |
| ATR-normalised cells concentration | 100% USD_JPY | 100% USD_JPY | identical |
| Raw_pip cells concentration | ~17-20% USD_JPY (diverse) | ~17-20% USD_JPY (diverse) | identical |

---

## 3. Load-bearing observation from L-2 / L-3 consolidation

> *L-3 spread-aware EV regression (PR #303) and L-2 generic continuous path-quality regression (PR #306) produce **IDENTICAL** val-selected (cell\*, q\*) records and IDENTICAL realised-PnL metrics on test. This is because the spread-embedding step (D-4 of L-3 §3.1) creates a constant offset between L-2 and L-3 predictions that does NOT change the top-q% ranking — the same 41,272 val rows are traded in both, with the same `_compute_realised_barrier_pnl` outputs. Therefore the **spread-embedding step is NOT load-bearing for the structural-gap failure**. The binding constraint is more likely the **continuous-target ranking → realised-PnL conversion at the minimum feature set (`pair + direction` only)**, NOT the spread-embedding-vs-not axis.*

This is the cleanest "single-axis change → identical result" evidence we have so far in Phase 26.

---

## 4. Structural-gap hypothesis status

| Hypothesis | Pre-26.0b status | Post-26.0b status |
|---|---|---|
| H-G binary-label binding (Phase 25 closure §6) | leading | **less likely** — both L-3 and L-2 are continuous regression labels and both FAILED |
| **Continuous-target ranking → realised-PnL conversion at minimum feature set is binding** | not framed | **leading hypothesis** — supported by L-2 / L-3 identity (§3) |
| Spread-embedding-in-target is binding | possible (L-3 specific) | **rejected** (L-2 = L-3 result; §3 binding) |
| ATR-normalisation pair-bias is the failure mode | possible | partial — affects val-selection (USD_JPY 100% concentration) but raw_pip cells without ATR-bias ALSO have negative Sharpe at all quantiles |

---

## 5. Routing space (4 options)

| ID | Path | Cost | Posterior expectation (qualitative; subjective / heuristic) |
|---|---|---|---|
| **R1** | Accept L-2 / L-3 verdicts; proceed to **L-1 ternary** (TP-hit / SL-hit / time-exit) | medium | low-to-medium |
| **R3** | Accept L-2 / L-3 verdicts; proceed to **L-4 trinary-with-no-trade** | medium | low-to-medium |
| **R6-new** | **Feature widening pivot** — keep continuous label (e.g., L-2 raw_pip) but widen the feature set beyond `pair + direction` | medium-high | medium |
| **R5** | Phase 26 soft close | very low | n/a (phase-management; mid-late phase soft close) |

**Posterior expectations are subjective / heuristic / not statistically estimated.** They are discussion anchors only. The user reweights freely. R5 is one option among four; it is NOT the default close.

---

## 6. R6-new (feature widening pivot) — deep-dive (CANNOT start directly)

R6-new is a NEW routing option surfaced by the L-2 / L-3 identity finding (§3). It does NOT fit the original Phase 26 first-scope-review (#300) L-1 / L-2 / L-3 / L-4 framing.

> ***R6-new cannot start directly from this review. It requires a Phase 26 scope-amendment doc-only PR first.*** *Phase 26 kickoff (PR #299) §5 explicitly states "Phase 26 is NOT a continuation of Phase 25's feature-axis sweep." R6-new would re-introduce features beyond the minimum set, blurring the Phase 25 / Phase 26 boundary. The scope-amendment PR must explicitly authorise the feature-widening direction and define which feature additions are admissible before R6-new can begin.*

> ***R6-new-A is a minimal feature-widening audit, NOT a revival of the full Phase 25 F-class sweep.*** *The intent is to test whether the binding constraint is the minimum feature set, not to re-enter Phase 25's 5-class feature exploration.*

### 6.1 R6-new variants

| Variant | Feature additions | Phase-26-scope distance |
|---|---|---|
| **R6-new-A** | `pair + direction` + `atr_at_signal_pip` + `spread_at_signal_pip` (both already in 25.0a-β dataset) | closest to Phase 26 scope — minimal feature-widening audit |
| **R6-new-B** | R6-new-A + Phase 25 F1 best features (vol expansion / compression) | moderate distance — re-engages F1 |
| **R6-new-C** | R6-new-A + Phase 25 F5 best features (liquidity / spread / volume) | moderate distance — re-engages F5 |
| **R6-new-D** | full Phase 25 F1-F5 feature set (~45 features) | farthest from Phase 26 scope — equivalent to Phase 25 continuation under continuous label |

R6-new-A is the lightest variant and the most direct test of "is the minimum feature set the binding constraint?" without re-entering Phase 25's full feature-axis sweep.

### 6.2 Cost / risk

- Cost: ~1 day for the scope-amendment doc + ~1 day for the 26.0c-α design memo + ~30 min sweep runtime per variant.
- Risk: even with widened features, raw_pip cells without ATR-bias already showed negative Sharpe at all thresholds (diagnostic D-3 from #303 / #306). A wider feature set may not change this; or it may (the leading hypothesis from §3 / §4 says it might).

---

## 7. R1 (L-1 ternary) — admissibility framing

L-1 (ternary classification: TP-hit / SL-hit / time-exit) is the cleanest remaining in-scope label-class test:

> ***L-1 is the cleanest remaining in-scope label-class test.*** *It tests classification structure without changing the feature set. L-2/L-3 identity does not imply L-1 will fail.*

| Aspect | L-1 ternary |
|---|---|
| Label type | classification (3 discrete classes: TP / SL / TIME) |
| Information preserved over binary | time-exit class explicit |
| Feature set | `pair + direction` only (Phase 26 §5.1 binding preserved) |
| Distance from L-2 / L-3 binding-constraint hypothesis | high — classification, not regression |
| Risk of same failure pattern | medium — still minimum feature set; same dataset; but L-2 / L-3 identity is a regression-family finding |
| Phase 26 scope fidelity | full — no scope amendment needed |

**Why L-2 / L-3 identity does NOT imply L-1 failure**: L-2 / L-3 are both **continuous-target regression** labels and produced identical results because the spread-embedding step creates a constant prediction offset that doesn't change rank order. L-1 is a structurally **different** label class (3-way classification, not regression). The quantile-of-val selection mechanism applies differently to classification probabilities than to regression magnitudes. The L-2 / L-3 identity is a property of the continuous-regression family; it does not extend to classification.

---

## 8. Comparison vs Phase 25 routing pattern + earlier Phase 26 routing reviews

| Phase 25 (feature-axis sweep) | Phase 26 (label-target redesign) |
|---|---|
| 5 evidence points all confirmed structural-gap | **2 evidence points (L-3 + L-2)** confirm same val-selected cell + same realised PnL |
| F-class space closed after F5 (LAST high-orthogonality F-class) | L-class space has 2 remaining candidates (L-1, L-4) + 1 NEW routing option (R6-new with scope-amendment prerequisite) |
| Routing review post-F5 (#297) recommended R5 (soft close) | Routing review post-26.0b is **mid-late phase**, NOT pre-closure; soft close NOT default |

**Phase 26 is now mid-late phase**: 2 of 4 admissible L-classes evaluated + 1 NEW routing option surfaced.

---

## 9. Stop conditions

| Stop level | Trigger | Status |
|---|---|---|
| Definitive stop | All 4 L-classes tested AND no H2 PASS | NOT met (only L-2, L-3 tested) |
| Strong soft stop | 3+ L-classes confirm gap | NOT met |
| **Soft stop (post-26.0b)** | 2 L-classes (continuous regression family) produce identical realised-PnL result | **MET** (informational only) |
| L-2 / L-3 identity finding | spread-embedding step is NOT load-bearing | **CONFIRMED** (binding text §3) |

> *Phase 26 has reached a soft stop (informational); definitive stop is NOT met. R5 (soft close) remains one of four options, but it is NOT the default close.*

---

## 10. User-facing decision matrix

| Choice | Cost | Expected payoff (qualitative) | Closes Phase 26? |
|---|---|---|---|
| R1 → L-1 ternary | medium | low-to-medium | No (next L-class; Phase-26-faithful) |
| R3 → L-4 trinary | medium | low-to-medium | No (next L-class; adds class-boundary design freedom) |
| R6-new → feature widening | medium-high (scope amendment + design memo + eval) | medium | No (continues Phase 26 under amended scope) |
| R5 → Phase 26 soft close | very low | n/a (phase-management) | YES |

> Posterior payoff tags are subjective / heuristic / not statistically estimated.

---

## 11. Informational next-path framing (NOT a routing decision)

Two characterisations are informationally efficient, but they are NOT routing recommendations. The user picks separately.

| Characterisation | Detail |
|---|---|
| **Most direct test of the newly surfaced hypothesis (§3 / §4)** | **R6-new-A** — feature widening with `atr_at_signal_pip` + `spread_at_signal_pip`. Directly tests whether the minimum feature set is binding. **Requires a Phase 26 scope-amendment doc-only PR first (§6 binding).** |
| **Most Phase-26-faithful next path** | **R1 (L-1 ternary)** — tests a structurally different label class (classification, not regression) without touching the feature set or scope binding. The L-2 / L-3 identity finding does NOT directly imply L-1 will fail (§7). |

Both characterisations are informational. R3 (L-4) and R5 (soft close) also remain admissible. The user picks.

---

## 12. Mandatory clauses (verbatim, 6 total — inherited unchanged from #299 §7 / 26.0a-α §9 / rev1 §11 / 26.0b-α §9)

1. **Phase 26 framing** — Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.
2. **Diagnostic columns prohibition** — Calibration / threshold-sweep / directional-comparison columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.
3. **γ closure preservation** — Phase 24 γ hard-close (PR #279) is unmodified.
4. **Production-readiness preservation** — X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure) remains untouched.
5. **NG#10 / NG#11 not relaxed**.
6. **Phase 26 scope** — Phase 26 is NOT a continuation of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed. **(R6-new in §6 requires explicit scope amendment per §6 binding.)**

---

## 13. PR chain reference

```
Phase 26:
  #299 (kickoff) → #300 (first-scope review)
  → #301 (26.0a-α L-3 design) → #302 (26.0a-α-rev1)
  → #303 (26.0a-β rev1 L-3 eval)
  → #304 (post-26.0a routing review)
  → #305 (26.0b-α L-2 design) → #306 (26.0b-β L-2 eval)
  → THIS PR (post-26.0b routing review)
  → R1 (L-1) | R3 (L-4) | R6-new (feature widening; scope amendment first) | R5 (soft close) — user picks
```

---

## 14. What this PR will NOT do

- ❌ Pick a routing decision (R1 / R3 / R6-new / R5).
- ❌ Initiate any L-class or feature-widening implementation.
- ❌ Write a Phase 26 scope-amendment PR (R6-new prerequisite if picked).
- ❌ Modify any prior verdict (Phase 25 / Phase 26 #284..#306).
- ❌ Retroactively change L-3 or L-2 verdict.
- ❌ Modify γ closure (PR #279).
- ❌ Pre-approve production deployment.
- ❌ Update MEMORY.md.
- ❌ Foreclose L-1 / L-4 / R6-new variants (admissible follow-up candidates).
- ❌ Foreclose F4 / F6 / F5-d / F5-e (Phase 25 deferred extensions).
- ❌ Use diagnostic D-1..D-3 from #304 (raw_pip Spearman +0.38 etc.) to feed any verdict-routing pipeline.
- ❌ Use the L-2 / L-3 identity finding (§3) to retroactively change either verdict.
- ❌ Recommend R6-new without flagging the Phase 26 §5 scope-binding question (§6 binding).
- ❌ Auto-route to any sub-phase after merge.
- ❌ Touch `src/`, `scripts/`, `tests/`, or `artifacts/`.

---

## 15. Sign-off

After the user picks one of R1 / R3 / R6-new / R5, the next PR is one of:

- **R1**: Phase 26.0c-α L-1 ternary design memo (analogous to 26.0a-α / 26.0b-α design pattern).
- **R3**: Phase 26.0c-α L-4 trinary-no-trade design memo.
- **R6-new**: Phase 26 scope-amendment doc-only PR (mini, ~150-200 lines) first, then 26.0c-α feature-widening design memo on a separate later PR.
- **R5**: Phase 26 soft-close memo (analogous to PR #298 Phase 25 closure pattern; mid-late-phase soft close).

The user picks. **This PR stops here.**
