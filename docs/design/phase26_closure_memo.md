# Phase 26 Closure Memo

**Type**: doc-only formal closure memo
**Status**: closes the Phase 26 label / target redesign without ADOPT_CANDIDATE
**Branch**: `research/phase26-closure-memo`
**Base**: master @ 5cef0fe (post-PR #314 merge)
**Routing**: R5 selected by the user in post-26.0d routing review (PR #314)
**Pattern**: analogous to PR #298 Phase 25 closure memo, with two Phase 26-specific additions (§2 dual finding; §6 lever-exists preservation note)
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Closure declaration

This memo formally closes **Phase 26 (label / target redesign on the 20-pair canonical universe)** per the user's R5 routing decision in PR #314. The closure is final for the current Phase 26 scope as amended by PR #311 (closed 2-feature allowlist). It does **NOT** foreclose:

(a) **L-4 (R3)** — last unexercised L-class under the original Phase 26 scope (no scope amendment required).
(b) **R6-new-B / R6-new-C** — each requiring a SEPARATE further Phase 26 scope-amendment PR (analogous to PR #311) before any design memo or eval.
(c) **Phase 25 deferred-not-foreclosed items** (F4 / F6 / F5-d / F5-e) — preserved under Phase 25 semantics from PR #298.
(d) **Future label / target / feature redesign** — successor Phase / sub-phase choice is a separate later instruction.

No production change is associated with this closure. Production v9 20-pair (Phase 9.12 closure tip `79ed1e8`) remains untouched. γ closure (PR #279) is unmodified. NG#10 / NG#11 are not relaxed. X-v2 OOS gating remains required for any future production deployment.

---

## 1. Four evidence points

Four sub-phase β evaluations have been run under Phase 26. Each adopted the same canonical 20-pair universe, the same 70/15/15 chronological split, the same triple-barrier event-time horizon (K_FAV=1.5×ATR, K_ADV=1.0×ATR, H_M1=60), and the same inherited bid/ask executable realised-PnL harness. The four evidence points are summarised below.

| # | Evidence point | Source PR | val-selected test Sharpe | n_trades | concentration | verdict |
|---|---|---|---|---|---|---|
| 1 | L-3 EV regression (spread-embedded continuous target) | #303 | -0.2232 | 42,150 | 100% USD_JPY | REJECT_NON_DISCRIMINATIVE |
| 2 | L-2 mid-to-mid continuous regression (spread NOT embedded) | #306 | -0.2232 | 42,150 | 100% USD_JPY | REJECT_NON_DISCRIMINATIVE |
| 3 | L-1 ternary classification {TP, SL, TIME} | #309 | -0.2232 | 42,150 | 100% USD_JPY | REJECT_NON_DISCRIMINATIVE |
| 4 | R6-new-A feature-widening audit (closed 2-feature allowlist) | #313 | **-0.1732** | 34,626 | multi-pair | REJECT_NON_DISCRIMINATIVE (H1_WEAK_FAIL) + YES_IMPROVED identity-break |

The first three evidence points form the 3-evidence-point load-bearing finding consolidated at post-26.0c routing review (#310 §3): identical val-selected realised-PnL outcome across regression-vs-classification AND spread-embedded-vs-not. The fourth evidence point is the first Phase 26 result where the val-selected outcome differs from the L-baselines (the dual finding documented in §2 below).

All four formal verdicts stand unchanged at closure. The closure memo does **not** retroactively modify any prior verdict.

---

## 2. R6-new-A dual finding (Phase 26-specific section)

PR #313 produced two co-existing findings on the same val-selected (cell\*, q\*) record. Both are preserved verbatim at closure.

> ***Finding 1 (formal verdict ladder)***: ***REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL***. *Val-selected: C02 P(TP)-P(SL), q\*=5%, cutoff=+0.126233. Test n_trades=34,626 ; realised Sharpe = -0.1732 ; ann_pnl = -204,664.4 pip ; formal Spearman(picker score, realised_pnl) on test = -0.1535. C01 P(TP) cell: test Spearman = +0.0226 (just below H1-weak threshold 0.05). H1-weak FAIL on val-selected cell ; H2 / H3 / H4 all FAIL. Cross-cell aggregate: REJECT_NON_DISCRIMINATIVE.*
>
> ***Finding 2 (identity-break detector)***: ***YES_IMPROVED***. *The closed two-feature allowlist (`atr_at_signal_pip` + `spread_at_signal_pip`) DID break the L-1 / L-2 / L-3 identity. Trade count 42,150 → 34,626 ; Sharpe -0.2232 → -0.1732 (+22% relative improvement) ; ann_pnl -237,310.8 → -204,664.4 pip ; pair concentration shifted from 100% USD_JPY to multi-pair. Feature importance (4-bucket diagnostic, gain): pair=2631, direction=335, atr=3295, spread=2496 — the new features carry weight.*
>
> ***YES_IMPROVED does NOT override the formal verdict ladder.*** *R6-new-A's closure status is REJECT_NON_DISCRIMINATIVE. This closure does NOT produce ADOPT_CANDIDATE for R6-new-A. PROMISING_BUT_NEEDS_OOS is NOT applicable because H1 / H2 / H3 remain failed.*

Sanity probe PASSED before the R6-new-A full sweep (TP 19.2% / SL 74.3% / TIME 6.5%; 0 pairs over 99% TIME share; new-feature NaN rate 0.000%; positivity assertions OK; inherited bid/ask executable harness confirmed). Label construction, feature pipeline, and realised-PnL harness behaviour are consistent with spec — this is a substantive finding, not a bug.

---

## 3. Two-channel hypothesis split (closure status)

Post-26.0c routing review (#310 §3 / §4) framed the binding constraint as a single hypothesis: *"minimum feature set is the binding constraint."* The 26.0d-β dual finding bifurcated this into **two channels** at the post-26.0d routing review (#314 §3). Phase 26 closes with the following channel status:

| Channel | Closure status |
|---|---|
| **Channel A (feature-set channel)** *— does feature widening change selection?* | **PARTIALLY SUPPORTED** at closure. The closed two-feature allowlist changed the val-selected trade set AND improved realised PnL on test (R6-new-A YES_IMPROVED identity-break). The new features carry weight in LightGBM gain attribution. Subjective / heuristic; not statistically estimated. |
| **Channel B (score-ranking channel)** *— does the picker score → PnL ranking monetise on test?* | **STILL BINDING** at closure. Formal H1-weak failed on every evidence point including R6-new-A. Per-row score → PnL ranking does not monetise on test under the closed allowlist + fixed LightGBM multiclass + quantile-of-val framework at the val-selected cells. |

> *Synthesis at closure: **Feature widening helped, but did not solve score-ranking monetisation.** Channel A is preserved as an observation for future-Phase reference (§6 lever-exists note). Channel B remains the binding constraint at Phase 26 closure.*

---

## 4. Strong soft stop condition (met since #310; preserved through closure)

The strong soft stop condition (3+ L-classes confirm structural-gap) was met at post-26.0c routing review (#310 §10) and preserved through post-26.0d (#314 §10). The 4-evidence-point picture (3 L-class identity at L-baselines + R6-new-A dual REJECT + YES_IMPROVED) is informationally consistent with the Phase 25 closure pattern (PR #297 / PR #298 — 5 F-class evidence points all confirmed structural-gap).

| Stop level | Trigger | Status at closure |
|---|---|---|
| Definitive stop | All 4 L-classes tested AND no H2 PASS | NOT met (L-4 untested; L-4 admissible) |
| **Strong soft stop** | 3+ L-classes confirm gap | **MET (preserved from #310)** |
| 4-evidence-point dual-channel finding | 3 L-class identity + R6-new-A YES_IMPROVED with formal reject | informational; strengthens the closure case but does not promote it to definitive |
| L-1 ≡ L-2 ≡ L-3 identity finding | label-class axis NOT load-bearing for the structural-gap | **CONFIRMED (binding text #310 §3)** |

Phase 26 reaches closure not because all admissible options are exhausted, but because the soft-stop threshold has been met and the user explicitly elected R5 in post-26.0d routing review (PR #314). L-4 (R3) and R6-new-B / R6-new-C remain admissible after closure as deferred-not-foreclosed items (§5).

---

## 5. Carry-forward / deferred-not-foreclosed register

| Item | Status at closure | Path to revival |
|---|---|---|
| **L-4 trinary-with-no-trade (R3)** | deferred-not-foreclosed | a future Phase 26.0e-α design memo PR + 26.0e-β eval; no scope amendment needed (under original Phase 26 scope binding) |
| **R6-new-B (allowlist + Phase 25 F1 best features)** | deferred-not-foreclosed | a SEPARATE further Phase 26 scope-amendment PR (analogous to PR #311) admitting F1 to a new closed allowlist; then a separate design memo; then a separate eval |
| **R6-new-C (allowlist + Phase 25 F5 best features)** | deferred-not-foreclosed | a SEPARATE further Phase 26 scope-amendment PR admitting F5 to a new closed allowlist; then a separate design memo; then a separate eval |
| **R6-new-D (full Phase 25 F1..F5 ~45-feature set)** | **NOT a Phase 26 routing option.** Restarting Phase 25's full feature-axis sweep is materially a Phase 25 reopening decision; it is outside Phase 26's admissible scope under the amended clause 6 from PR #311 §8. | a separate Phase 25 reopening decision would be required; this closure memo does NOT authorise that path |
| **Phase 25 F4 / F6 / F5-d / F5-e** | preserved deferred-not-foreclosed from PR #298 under Phase 25 semantics | a Phase 25 reopening would be required |
| **Calibration adjustments (e.g., isotonic in the formal grid)** | deferred per 26.0c-α §4.3 selection-overfit binding | a future memo amending the formal-grid binding (within a successor sub-phase or a new phase) |

All deferred items above are preserved regardless of any future user choice. The closure does NOT foreclose any of them.

---

## 6. Lever-exists preservation note (NEW Phase 26-specific section; observation-only)

Phase 26 closure records the following observation for future-Phase reference. **This is an observation, not a recommendation. It is flagged subjective / heuristic / not statistically estimated. It is NOT used to mint ADOPT_CANDIDATE or PROMISING_BUT_NEEDS_OOS. The formal closure verdict on every evidence point is REJECT_NON_DISCRIMINATIVE.**

### 6.1 Channel A lever-exists observation

Under the configuration:

- Closed 2-feature allowlist (`atr_at_signal_pip` + `spread_at_signal_pip`)
- L-1 ternary {TP, SL, TIME} label
- Fixed conservative LightGBM multiclass (inherited from #308 / #309)
- Quantile-of-val 5% picker P(TP)-P(SL) (val-selected cell C02)

R6-new-A realised test Sharpe improved by +0.0500 (from L-baseline -0.2232 to R6-new-A -0.1732, ~22% relative improvement) with a multi-pair trade selection (vs 100% USD_JPY at L-baselines). New features carry weight in LightGBM gain attribution (4-bucket: pair=2631, direction=335, atr=3295, spread=2496).

This observation is documented for **future-Phase reference** as a potential lever to investigate the score-ranking channel further. It is **not** a Phase 26-internal recommendation. It is **not** a prediction that further feature widening will close the score-ranking gap. It is a recorded observation, nothing more.

### 6.2 Score-ranking-channel-binding research carry-forward observation

The Channel B binding pattern — H1-weak FAIL on every Phase 26 evidence point including R6-new-A with a widened feature set — is recorded as a research carry-forward observation. It is **not** a recommendation that a successor phase address it. It is **not** an implicit hypothesis-promoting statement. It is recorded so that a successor design effort (if any, at user discretion) has the explicit Phase 26 closure-time picture available.

Both observations in §6.1 and §6.2 are subjective / heuristic / not statistically estimated. They are not load-bearing for any Phase 26 verdict and do not affect any deferred item's status.

---

## 7. Production / γ closure / X-v2 OOS bindings unchanged

This closure memo does **not** touch any of:

- γ closure (PR #279) — unmodified
- X-v2 OOS gating — remains required for any future production deployment
- Production v9 20-pair (Phase 9.12 closure tip `79ed1e8`) — untouched
- NG#10 / NG#11 — not relaxed
- Production deployment for any Phase 26 evidence point — NOT pre-approved

No production change of any kind is associated with this closure.

---

## 8. Mandatory clauses (clause 6 = AMENDED from PR #311 §8 verbatim)

This closure memo is the **canonical source-of-truth** for the amended clause 6 going forward. Future revivals (L-4, R6-new-B, R6-new-C, or any successor Phase 26 work) re-quote clause 6 from this memo.

1. **Phase 26 framing.** Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness. *[unchanged]*
2. **Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison / classification-quality / feature-importance columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them. *[unchanged]*
3. **γ closure preservation.** Phase 24 γ hard-close (PR #279) is unmodified. *[unchanged]*
4. **Production-readiness preservation.** X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure) remains untouched. *[unchanged]*
5. **NG#10 / NG#11 not relaxed.** *[unchanged]*
6. **Phase 26 scope (AMENDED).** Phase 26's primary axis is label / target redesign on the 20-pair canonical universe. Phase 26 is NOT a revival of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed under Phase 25 semantics. A narrow feature-widening audit (R6-new-A) is authorised under the scope amendment in PR #311 with a closed allowlist of two features (`atr_at_signal_pip`, `spread_at_signal_pip`); all other features are out of scope until a further scope amendment. R6-new-A is a Phase 26 audit of the minimum-feature-set hypothesis; it is NOT a Phase 25 continuation. *[AMENDED per PR #311 §8 — VERBATIM]*

---

## 9. PR chain reference (Phase 26 complete)

```
Phase 26 routine stream (full):
  #299 (kickoff) → #300 (first-scope review)
  → #301 (26.0a-α L-3 design) → #302 (26.0a-α-rev1)
  → #303 (26.0a-β L-3 eval)
  → #304 (post-26.0a routing review)
  → #305 (26.0b-α L-2 design) → #306 (26.0b-β L-2 eval)
  → #307 (post-26.0b routing review)
  → #308 (26.0c-α L-1 design) → #309 (26.0c-β L-1 eval)
  → #310 (post-26.0c routing review)
  → #311 (scope amendment — feature widening) → #312 (26.0d-α R6-new-A design)
  → #313 (26.0d-β R6-new-A eval; dual REJECT + YES_IMPROVED)
  → #314 (post-26.0d routing review; R5 selected by user)
  → THIS PR (Phase 26 closure memo)
```

Phase 26 stream is closed at this memo.

---

## 10. What this closure does NOT do

- ❌ Pre-approve any production deployment.
- ❌ Modify γ closure (PR #279).
- ❌ Modify X-v2 OOS gating.
- ❌ Modify NG#10 / NG#11.
- ❌ Modify any prior verdict (Phase 25 / Phase 26 #284..#314).
- ❌ Retroactively change L-1 / L-2 / L-3 / R6-new-A formal verdict.
- ❌ Mint ADOPT_CANDIDATE for any Phase 26 evidence point.
- ❌ Mint PROMISING_BUT_NEEDS_OOS for R6-new-A.
- ❌ Use the YES_IMPROVED identity-break observation to elevate R6-new-A's status.
- ❌ Foreclose L-4 (R3) — preserved as deferred-not-foreclosed.
- ❌ Foreclose R6-new-B / R6-new-C — preserved as deferred-not-foreclosed.
- ❌ Foreclose Phase 25 F4 / F6 / F5-d / F5-e — preserved under Phase 25 semantics from PR #298.
- ❌ Authorise R6-new-D as a Phase 26 routing option.
- ❌ Reopen Phase 25.
- ❌ Name or recommend a successor Phase / sub-phase.
- ❌ Auto-route to any sub-phase or successor Phase.
- ❌ Update MEMORY.md.
- ❌ Touch `src/`, `scripts/`, `tests/`, or `artifacts/`.

---

## 11. What this closure DOES do (single-sentence declarations)

- ✅ Formally closes Phase 26 under the strong soft stop condition.
- ✅ Records the 4-evidence-point picture as the Phase 26 evidence basis.
- ✅ Documents the R6-new-A dual finding (REJECT + YES_IMPROVED) verbatim, with YES_IMPROVED explicitly not overriding the formal verdict.
- ✅ Documents the 2-channel hypothesis split (Channel A PARTIALLY SUPPORTED ; Channel B STILL BINDING).
- ✅ Preserves L-4 (R3) and R6-new-B / R6-new-C as deferred-not-foreclosed.
- ✅ Preserves Phase 25 F4 / F6 / F5-d / F5-e under Phase 25 semantics from PR #298.
- ✅ Records the Channel A lever-exists observation in §6 for future-Phase reference (observation-only; not a recommendation).
- ✅ Records the score-ranking-channel-binding research carry-forward observation in §6 (observation-only; not a recommendation).
- ✅ Preserves all production / γ closure / X-v2 OOS / NG#10 / NG#11 bindings unchanged.
- ✅ Designates itself as the canonical source-of-truth for the amended clause 6 going forward.

---

## 12. Sign-off

Phase 26 is closed. Successor Phase / sub-phase choice is a separate later instruction. No PR is queued. No auto-route after merge. **This is the final Phase 26 routine-stream PR.**
