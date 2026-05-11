# Phase 26 — Routing Review Post-26.0a

**Type**: doc-only synthesis memo (post-26.0a-β rev1; mid-Phase-26)
**Status**: synthesis ONLY; squash-merge approval accepts this review as the Phase 26 post-26.0a routing synthesis, but does NOT by itself authorise any next sub-phase implementation
**Branch**: `research/phase26-routing-review-post-26-0a`
**Base**: master @ 6e30dac (post-PR #303 merge)
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this review as the Phase 26 post-26.0a routing synthesis. It does NOT by itself authorise any next sub-phase implementation. The user explicitly confirms which next branch to pursue — R1 (L-1), R2 (L-2), R3 (L-4), R4 (L-3 rev2), or R5 (soft close) — in a separate later instruction.*

Same pattern as the Phase 25 routing reviews (#291 / #294 / #297) and the Phase 26 first-scope review (#300) approval semantics: accept synthesis, defer next implementation.

---

## 1. 26.0a-β rev1 finding (binding text)

> *Phase 26.0a-β rev1 (PR #303) formally produced **REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL**. The validation-selected cell was `entry_only / atr_normalised / none / LinearRegression / q*=5%` (val-fit cutoff = -0.5329). On the test set: n_trades = 42,150 ; realised Sharpe = -0.2232 ; ann_pnl = -237,310.8 pip ; **test Spearman = -0.1419** (negative). All 42,150 trades concentrated 100% in USD_JPY (21,075 long + 21,075 short). The rev1 quantile-threshold redesign successfully eliminated the pre-rev1 "no trades fire" gap (all 24 cells fire trades now), but the val-selected cell's realised Sharpe stayed negative and Spearman was below the H1-weak threshold of +0.05.*

The formal verdict is **REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL** and stands. Nothing in this memo retroactively changes it.

---

## 2. Diagnostic-only observations (NOT verdict basis)

Three observations from the eval report inform but do **NOT** change the formal verdict. All are diagnostic-only per 26.0a-α §9 clause 2 / rev1 §11 clause 2.

| # | Observation | Source |
|---|---|---|
| **D-1** | **Raw_pip cells show POSITIVE test Spearman ≈ +0.38** (best by Spearman: `entry_only / raw_pip / none / LightGBM` = +0.3836). The regression IS ranking-discriminative on raw_pip targets. **Diagnostic-only; not used for verdict.** | PR #303 eval_report §"Best cell by TEST Spearman" |
| **D-2** | **ATR-normalised cells show NEGATIVE Spearman ≈ -0.14.** Dividing the target by `atr_at_signal_pip` introduces a per-pair bias because pip-ATR varies systematically (JPY pairs have ~10× higher pip-ATR than majors). The val-selected ATR cell's 42k test trades are 100% USD_JPY — top 5% by ATR-normalised predicted EV concentrates entirely in JPY pairs. **Diagnostic-only.** | PR #303 eval_report §"Val-selected cell" + §"Whether ranking signal monetises" |
| **D-3** | **Best-by-test-Sharpe diagnostic cell has Sharpe = -0.22** — no cell escapes the structural-gap signature under L-3 + minimum feature set. No cell across the 24-cell sweep produced positive realised Sharpe on test. **Diagnostic-only.** | PR #303 eval_report §"Best cell by TEST realised Sharpe" |

> All three are diagnostic-only per the binding contract and explicitly labelled in the rev1 eval_report as "not used for verdict". They inform the next-routing decision but DO NOT retroactively change the L-3 verdict.

---

## 3. What's confirmed vs. what's open

| Aspect | Status |
|---|---|
| L-3 label construction (D-1..D-6 of 26.0a-α §3) | CORRECT — verified by 33 unit tests; eval_report reproduces correctly |
| Rev1 threshold redesign (quantile primary) | WORKS — trades fire at every cell |
| Validation-only cell+threshold selection per §5.3 | WORKS as specified — A0-pre-filter + tie-breakers operate correctly |
| L-3 formal verdict (val-selected `entry_only / atr_normalised / none / LinearRegression / q*=5%`) | **REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL** (binding) |
| Whether L-3 has SOMEWHERE a positive ranking signal | YES — diagnostic D-1 (raw_pip Spearman +0.38) |
| Whether L-3 has SOMEWHERE a positive realised Sharpe | **NO** — diagnostic D-3 (best-by-test Sharpe = -0.22 across all 24 cells) |
| Whether ATR-normalisation introduces pair-bias | LIKELY — diagnostic D-2 (100% USD_JPY concentration; negative Spearman) |
| Whether L-3 is salvageable with cell-selection priority change | UNCLEAR — would require a 26.0a-α-rev2 doc-only PR before any rev2 re-implementation |

---

## 4. Routing space (5 options)

| ID | Path | Cost | Posterior expectation (qualitative; subjective / heuristic) |
|---|---|---|---|
| **R1** | Accept L-3 verdict; proceed to L-1 ternary (TP-hit / SL-hit / time-exit) | medium | low-to-medium |
| **R2** | Accept L-3 verdict; proceed to L-2 generic path-quality regression | medium-high | medium |
| **R3** | Accept L-3 verdict; proceed to L-4 trinary-with-no-trade | medium | low-to-medium |
| **R4** | Revise L-3 via 26.0a-α-rev2 (ATR-cell exclusion / raw_pip-only re-eval; see §5) | medium (rev2 doc + re-run) | **low-to-medium / salvage uncertain** |
| **R5** | Phase 26 soft close | very low | n/a (phase-management) |

**Posterior expectations are subjective / heuristic / not statistically estimated.** They are discussion anchors only. The user reweights freely.

---

## 5. R4 (L-3 revise) — deep-dive

> *R4 is **low-to-medium / salvage uncertain**. It may be worth considering only if the user wants to exhaust L-3, but no diagnostic cell produced positive realised Sharpe. Diagnostic D-3 shows best-by-test-Sharpe = -0.22 across all 24 cells, including raw_pip cells with positive Spearman. The raw_pip Spearman +0.38 (diagnostic D-1) is informative but does not by itself imply realised-Sharpe-positive trades.*

### 5.1 Diagnostic-columns-prohibition consideration

26.0a-α §9 clause 2 (inherited by rev1 §11) states:

> *Diagnostic columns prohibition — Calibration / threshold-sweep / directional-comparison columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.*

> ***Using Spearman in formal cell selection is NOT recommended unless 26.0a-α-rev2 explicitly revises the diagnostic-selection boundary.*** Spearman is a regression diagnostic in 26.0a-α §8 and is treated as diagnostic-only by the formal verdict tree. Promoting it to a selection-priority key would feed a diagnostic column into the verdict pipeline, which the prohibition guards against. A 26.0a-α-rev2 doc-only PR would need to address this question explicitly before any rev2 re-implementation can use Spearman in cell-selection.

### 5.2 Safer R4 candidates

If R4 is chosen, the safer revision paths — both still requiring a 26.0a-α-rev2 doc-only PR before any rev2 re-implementation — are:

| Variant | Rationale | Contract impact |
|---|---|---|
| **R4-A** | **Exclude ATR-normalised cells from formal cell selection**; keep them as diagnostic-only in eval_report. Re-evaluate L-3 using only raw_pip cells. | Changes the 24-cell sweep grid (12 cells in formal selection; 12 diagnostic-only). Requires rev2 to amend the rev1 §8 "24-cell sweep grid unchanged" statement. |
| **R4-B** | **Re-run with raw_pip cells only** (drop ATR-normalised cells entirely). Equivalent to R4-A but cleaner: the formal sweep grid becomes 12 cells. | Same: requires rev2 amending the rev1 §8 grid-size statement. |
| **R4-C** | **Add Spearman to cell-selection priority** (e.g., require val Spearman ≥ +0.05 as pre-filter, then val Sharpe). | Requires rev2 explicitly revising the diagnostic-selection boundary (§5.1). NOT recommended without that. |

> R4-A or R4-B are the safer R4 variants. R4-C is NOT recommended without an explicit diagnostic-selection-boundary revision in 26.0a-α-rev2.

### 5.3 Cost / risk

- Cost: ~1 day for the rev2 doc + ~30 min for the re-run.
- Risk: even if R4 narrows the sweep to raw_pip cells, diagnostic D-3 shows their best test Sharpe is still negative (-0.35 at abs_thr=-5.0 per the rev1 eval_report's absolute-family diagnostic for raw_pip cells). A rev2 re-evaluation may produce the same REJECT_BUT_INFORMATIVE / REJECT_NON_DISCRIMINATIVE pattern with different specifics.

---

## 6. Comparison vs. Phase 25 routing pattern

| Phase 25 (feature-axis sweep) | Phase 26 (label-target redesign) |
|---|---|
| 5 evidence points all confirmed structural-gap | 1 evidence point (L-3 formal) + 3 diagnostic observations |
| F-class space was finite (F1-F6) and closed after F5 (LAST high-orthogonality F-class) | L-class space (L-1..L-4) has 3 candidates remaining post-L-3 |
| Routing review post-F5 (#297) recommended R5 (soft close) | Routing review post-L-3 is **mid-phase**, NOT pre-closure |

**Phase 26 is mid-phase**, not pre-closure. R5 (soft close) is one option in §4 but the L-class space is not yet exhausted, and Phase 25's "Strong Soft Stop" pattern would only apply if 3+ L-classes were tested with the same gap signature.

---

## 7. Stop conditions

| Stop level | Trigger | Status |
|---|---|---|
| Definitive stop | All 4 L-classes tested AND no H2 PASS | NOT met (only L-3 tested) |
| Strong soft stop | 3+ L-classes confirm gap | NOT met |
| **Soft stop (current)** | 1 L-class confirms gap with diagnostic ranking signal | MET (informational only) |
| L-3 specific salvage trigger | Diagnostic D-1 raw_pip Spearman +0.38 suggests possible salvage path | OPEN (would require R4 + 26.0a-α-rev2; salvage uncertain per §5) |

---

## 8. User-facing decision matrix

| Choice | Cost | Expected payoff (qualitative) | Closes Phase 26? |
|---|---|---|---|
| R1 → L-1 ternary | medium | low-to-medium | No (next L-class) |
| R2 → L-2 path-quality | medium-high | medium | No (next L-class) |
| R3 → L-4 trinary | medium | low-to-medium | No (next L-class) |
| R4 → L-3 rev2 (ATR-exclusion / raw_pip-only) | medium (rev2 doc + re-run) | **low-to-medium / salvage uncertain** | No (continues L-3) |
| R5 → Phase 26 soft close | very low | n/a (phase-management; mid-phase soft close) | YES |

> Posterior payoff tags are subjective / heuristic / not statistically estimated.

---

## 9. Informational next-path framing (NOT a routing decision)

> *Most conservative next path appears to be **R2: L-2 generic path-quality regression**, because L-2 is the parent family of L-3 (per #300 §3 family-and-specialisation framing), L-3 spread-aware specialization failed formally, and raw_pip diagnostic Spearman (+0.38) suggests continuous target ranking may still contain information.*

This is **informational only**. This memo does NOT pick a routing decision. The user explicitly selects R1 / R2 / R3 / R4 / R5 in a separate instruction. The R2 framing in this section is the most-conservative-next-step characterisation given:

- L-3 (spread-specialisation of L-2) formally REJECTed → its parent L-2 is the natural next step.
- Raw_pip Spearman +0.38 suggests continuous-target ranking has signal at minimum-feature-set level.
- L-2 reuses 25.0a-β path data with new label, similar implementation cost to L-3 rev2.
- L-2 cleanly tests "is L-3's failure due to spread-embedding specifics, or to continuous-target labelling in general".

Other R options (R1 L-1 / R3 L-4 / R4 L-3 rev2 / R5 soft close) remain admissible. The user picks.

---

## 10. Mandatory clauses (verbatim, 6 total — inherited from PR #299 §7 / 26.0a-α §9 / rev1 §11 unchanged)

1. **Phase 26 framing** — Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.
2. **Diagnostic columns prohibition** — Calibration / threshold-sweep / directional-comparison columns are diagnostic-only. (See §5.1 for the R4-specific interpretation question.)
3. **γ closure preservation** — Phase 24 γ hard-close (PR #279) is unmodified.
4. **Production-readiness preservation** — X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure) remains untouched.
5. **NG#10 / NG#11 not relaxed**.
6. **Phase 26 scope** — Phase 26 is NOT a continuation of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed.

---

## 11. PR chain reference

```
Phase 26:
  #299 (Phase 26 kickoff)
  → #300 (first-scope review — recommends L-3)
  → #301 (26.0a-α L-3 design memo)
  → #302 (26.0a-α-rev1 threshold redesign)
  → #303 (26.0a-β rev1 L-3 eval — REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL)
  → THIS PR (post-26.0a routing review)
  → R1 (L-1) | R2 (L-2) | R3 (L-4) | R4 (L-3 rev2) | R5 (soft close) — user picks
```

---

## 12. What this PR will NOT do

- ❌ Pick a routing decision (R1 / R2 / R3 / R4 / R5).
- ❌ Initiate any L-class implementation.
- ❌ Write a 26.0a-α-rev2 (R4 prerequisite if picked).
- ❌ Modify any prior verdict (Phase 25 / Phase 26 #299-#303).
- ❌ Modify γ closure (PR #279).
- ❌ Pre-approve production deployment.
- ❌ Update MEMORY.md.
- ❌ Foreclose L-1 / L-2 / L-4 (admissible follow-up candidates).
- ❌ Foreclose F4 / F6 / F5-d / F5-e (Phase 25 deferred extensions).
- ❌ Retroactively change the L-3 verdict from REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL.
- ❌ Use diagnostic D-1 / D-2 / D-3 to feed any verdict-routing pipeline (diagnostic-only per §2).
- ❌ Recommend Spearman as a formal cell-selection key without a 26.0a-α-rev2 explicit revision (per §5.1).
- ❌ Auto-route to any sub-phase after merge.
- ❌ Touch `src/`, `scripts/`, `tests/`, or `artifacts/`.

---

## 13. Test plan (CI for this doc-only PR)

- [x] `python tools/lint/run_custom_checks.py` rc = 0 expected (doc-only)
- [x] `ruff format --check` no code changed
- [x] No tests added or modified (doc-only)
- [x] Branch hygiene pre-push: `git diff --stat origin/master..HEAD` shows ONLY 1 expected file

---

## 14. Sign-off

This memo is the Phase 26 post-26.0a routing synthesis. After the user picks one of R1 / R2 / R3 / R4 / R5, the next PR is one of:

- **R1**: Phase 26.0b-α L-1 ternary design memo (analogous to 26.0a-α design pattern).
- **R2**: Phase 26.0b-α L-2 path-quality regression design memo.
- **R3**: Phase 26.0b-α L-4 trinary-with-no-trade design memo.
- **R4**: Phase 26.0a-α-rev2 doc-only PR (ATR-exclusion or raw_pip-only sweep grid revision). 26.0a-β rev2 re-implementation follows separately on user authorisation.
- **R5**: Phase 26 soft-close memo (analogous to PR #298 Phase 25 closure pattern; mid-phase soft close).

The user picks. **This PR stops here.**
