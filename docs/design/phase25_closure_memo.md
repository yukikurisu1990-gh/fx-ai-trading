# Phase 25 Closure Memo

**Type**: doc-only formal closure memo
**Status**: closes the Phase 25 feature-axis sweep without ADOPT_CANDIDATE
**Branch**: `research/phase25-closure-memo`
**Base**: master @ 8e36ce3 (post-PR #297 merge)
**Routing**: R5 leg of the R5 → R2 sequence selected by the user in PR #297
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Closure declaration

This memo formally closes the **Phase 25 feature-axis sweep** per the user's R5 routing decision in PR #297. The closure is final for the current Phase 25 scope (the F1-F6 admissible feature classes layered on the 25.0a-β path-quality dataset). It does **NOT** foreclose label redesign, future feature-axis revisits, a new dataset, or a new target design — those are Phase 26+ scope.

No production change is associated with this closure. Production v9 20-pair (Phase 9.12 closure tip `79ed1e8`) remains untouched. γ closure (PR #279) is unmodified. NG#10 / NG#11 are not relaxed. X-v2 OOS gating remains required for any future production deployment.

---

## 1. Five evidence points

**Four admissible F-classes (F1, F2, F3, F5) have been tested. In addition, one deployment-layer audit (25.0d-β) tested whether the F1/F2 AUC-PnL gap could be rescued downstream. Together, these form five evidence points (4 F-classes + 1 deployment audit), not five F-classes.**

| # | Evidence point | Source | best test AUC | realised Sharpe | gap signature |
|---|---|---|---|---|---|
| 1 | F1 (volatility expansion / compression) | PR #284 | 0.5644 | -0.192 | CONFIRMED |
| 2 | F2 (multi-TF volatility regime) | PR #287 | 0.5613 | -0.317 | CONFIRMED |
| 3 | 25.0d-β deployment-layer audit (re-fit of F1+F2 best) | PR #290 | re-fit | -0.21 / -0.36 | H-A miscalibrated; H-B / H-D refuted; H-F **CONFIRMED** |
| 4 | F3 (cross-pair / relative currency strength) | PR #293 | 0.5480 (H1 FAIL) | -0.363 | CONFIRMED at sub-H1 AUC |
| 5 | F5 (liquidity / spread / volume) | PR #296 | 0.5672 (H1 PASS, beats F1) | -0.367 | CONFIRMED at above-ceiling AUC |

All five evidence points support the structural-gap signature. F5 specifically demonstrated that the gap is independent of AUC level — improving AUC past F1's ceiling did not improve realised Sharpe.

---

## 2. Load-bearing closure observation

> *F5 nudged AUC past F1's ceiling but failed to translate it into realised PnL. Therefore the binding constraint is not feature-class shortage or an AUC ceiling — it is structurally the realised-EV translation under the current binary path-quality label, K_FAV=1.5 / K_ADV=1.0 barrier geometry, and the spread-cost environment.*

This observation is the **load-bearing reason for closing Phase 25**. The Phase 25 sweep was designed to test whether alternative admissible feature classes layered on the 25.0a-β path-quality dataset could produce an ADOPT_CANDIDATE on the 8-gate harness. Five evidence points (covering price, volatility, cross-pair currency strength, liquidity, and a downstream deployment-layer audit) consistently demonstrate that the binding constraint is upstream of the feature axis. No further feature-axis evaluation within the current Phase 25 scope is expected to produce a different result.

---

## 3. Phase 25 verdict

**VERDICT: Phase 25 closes WITHOUT ADOPT_CANDIDATE.**

- No F-class produced an H2 PASS on the 8-gate harness.
- The deployment-layer audit (25.0d-β) ruled out calibration / threshold / directional-comparison interventions on F1/F2 best cells.
- F3 confirmed the gap below the AUC ceiling (best AUC 0.5480, H1 FAIL).
- F5 confirmed the gap above the AUC ceiling (best AUC 0.5672, beats F1, but realised Sharpe -0.367).
- The structural binding constraint is identified per §2 and lies outside the scope of Phase 25's feature-axis framing.

The Phase 25 verdict is final for the current scope.

---

## 4. What this closure DOES NOT do (binding scoping rules)

This memo is precise about what stays open after closure.

- **NOT a foreclosure of the F1-F6 admissible-feature space.** F4 (range compression) and F6 (higher-TF) remain admissible-but-deferred per #294 §5.4 / #297 §5.1. The post-F5 posterior in #297 §3 makes them low-priority, but they are **deferred, not foreclosed**.
- **NOT a foreclosure of F5 sub-extensions.** F5-d (tick imbalance) and F5-e (pair-level liquidity rank) were deferred per 25.0f-α §2.3 and remain admissible future extensions.
- **NOT a foreclosure of label redesign.** Label redesign is the natural next research direction per #297 §5 / §7. It opens as a separate Phase 26+ PR on user instruction.
- **NOT a foreclosure of new datasets.** A different barrier geometry, different bar-frequency basis, different spread-cost regime, or different path-EV target structure can re-open the question (see §6 reactivation criteria).
- **NOT a modification of γ closure (PR #279).** γ closure stays as-is.
- **NOT a modification of NG#10 / NG#11.**
- **NOT a modification of any prior Phase 25 verdict** (#284 / #287 / #290 / #293 / #296). Those verdicts stand as written.
- **NOT a production deployment change.** Production v9 20-pair (Phase 9.12 closure tip `79ed1e8`) remains untouched. X-v2 OOS gating remains required for any future production deployment, regardless of which research direction follows.
- **NOT an update to MEMORY.md.** Per the established Phase 25 pattern, closure memos are captured in git history and not propagated to MEMORY.md unless the user explicitly requests it.
- **NOT auto-routing to Phase 26 / label redesign.** Phase 26 / label redesign opens only by separate user instruction.

---

## 5. What stays in production (binding statement)

The following are explicitly preserved:

- **Production v9 20-pair**: Phase 9.12 closure tip `79ed1e8`. Untouched by Phase 25 work; untouched by this closure.
- **OANDA Volume Mode infrastructure**: per memory `project_volume_mode_500k_complete.md`. Untouched.
- **γ closure (PR #279)**: untouched.
- **8-gate harness (A0–A5)**: untouched. The 8-gate thresholds (Sharpe ≥ +0.082, ann_pnl ≥ +180 pip, MaxDD ≤ 200, A4 ≥ 3/4 folds, A5 +0.5 pip stress > 0) remain as the gating contract for any future ADOPT_CANDIDATE decision.
- **NG#10 / NG#11**: untouched.
- **X-v2 OOS gating contract**: still required before any production deployment.
- **Production-misuse guards**:
  - GUARD 1 — research-not-production: research features stay in `scripts/`; not auto-routed to `feature_service.py`.
  - GUARD 2 — threshold-sweep-diagnostic: any threshold sweep is diagnostic-only.
  - GUARD 3 — directional-comparison-diagnostic: any long/short decomposition is diagnostic-only.

---

## 6. Reactivation criteria

The Phase 25 sweep can be re-opened (or a Phase 25.x sub-phase opened) under any of the following conditions. None of these are pre-authorised by this memo — they are enumerated for clarity, and reactivation remains the user's call.

1. **A new label class produces a realised-EV surface where AUC > 0.55 monetises.** I.e., R2 / H-G hypothesis test in Phase 26 succeeds. At that point, F4 / F6 / F5 sub-extensions become eligible for re-evaluation under the new label.
2. **A new dataset produces a different ceiling structure.** Different barrier geometry (e.g., different K_FAV / K_ADV multipliers), different bar-frequency basis (e.g., M1 / M15 instead of M5), or different spread-cost regime.
3. **A new path-EV target structure** (e.g., not triple-barrier; intra-bar mark-to-market; explicit risk-aware EV target).
4. **A new orthogonal data source** (e.g., order-book depth, cross-asset macro, fundamentals) that creates a feature axis distinct from F1-F6 and that lands on a label / barrier geometry materially different from 25.0a-β.

---

## 7. Recommended next research direction (informational)

Per #297 §5 / §7, the leading hypothesis post-F5 is **H-G binary-label binding**. The natural next research move is **R2 (label redesign)**, which is the second leg of the user's selected R5 → R2 sequence in #297.

Possible alternative label classes (from #297 §7.1; not exhaustive, not pre-committed):

| Alt | Description |
|---|---|
| L-1 | Ternary: TP-hit / SL-hit / Time-exit |
| L-2 | Regression on path-quality score (continuous; e.g., MFE − MAE differential) |
| L-3 | EV regression with bid/ask spread embedded in target |
| L-4 | Trinary with explicit "no-trade" class |

> *This is informational only. **This PR does NOT initiate label redesign or any Phase 26 work.** The user picks Phase 26 timing and label-class selection separately. The next-PR (when the user is ready) is a Phase 26-α label-redesign design memo, analogous to the 25.0a-α / 25.0e-α / 25.0f-α design pattern.*

---

## 8. Mandatory clauses (verbatim, 6 total — carried forward in any subsequent Phase 26+ PR)

These clauses survive the Phase 25 closure and apply to any future research building on the 25.0a-β dataset or its successors.

1. **Phase 25 framing** (closed as of this memo; preserved as historical context for future work)
2. **Diagnostic columns prohibition** — calibration / threshold-sweep / directional-comparison columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.
3. **γ closure preservation** — Phase 24 γ hard-close (PR #279) is unmodified.
4. **Production-readiness preservation** — X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure) remains untouched.
5. **NG#10 / NG#11 not relaxed** — entry-side budget cap and diagnostic-vs-routing separation rule remain in force.
6. **Phase 25 closure scoping** — *this memo formally closes the Phase 25 feature-axis sweep without ADOPT_CANDIDATE. It does NOT foreclose label redesign, future feature-axis revisits, new datasets, or new target designs. Phase 26 / label-redesign opens separately on user instruction.*

---

## 9. PR chain (Phase 25 archive)

```
#280 (Phase 25 kickoff)
  → #281 / #282 (25.0a-α design + 25.0a-β path-quality dataset)
  → #283 / #284 (F1 design + eval — REJECT_BUT_INFORMATIVE)
  → #285 (review post-F1)
  → #286 / #287 (F2 design + eval — REJECT_BUT_INFORMATIVE)
  → #288 (review post-F2)
  → #289 / #290 (25.0d-β deployment audit — H-A miscalibrated; H-B/H-D refuted; H-F CONFIRMED)
  → #291 (review post-deployment-audit)
  → #292 / #293 (F3 design + eval — REJECT_NON_DISCRIMINATIVE)
  → #294 (review post-F3)
  → #295 / #296 (F5 design + eval — LAST feature-axis attempt; REJECT_BUT_INFORMATIVE; H1 PASS, H4 FAIL)
  → #297 (routing review post-F5 — R5/R2 binary framing; user picked R5 → R2)
  → THIS PR (Phase 25 closure memo — R5 leg of R5 → R2 sequence)
```

After this merge, the Phase 25 archive is complete. Phase 26 (if pursued) opens with a fresh kickoff PR and a Phase 26-α label-redesign design memo.

---

## 10. What this PR will NOT do

- ❌ Initiate Phase 26 or any label-redesign code.
- ❌ Write the Phase 26-α label-redesign design memo.
- ❌ Modify any prior Phase 25 verdict (#284 / #287 / #290 / #293 / #296).
- ❌ Modify γ closure (PR #279).
- ❌ Pre-approve production deployment.
- ❌ Update `MEMORY.md` (closure memo recorded in master git history; MEMORY.md update deferred per established Phase 25 pattern).
- ❌ Touch the 8-gate harness (A0–A5).
- ❌ Foreclose F4 / F6 / F5 sub-extensions (those are deferred, not foreclosed).
- ❌ Foreclose label redesign (the natural next research direction).
- ❌ Foreclose new datasets or new target designs.
- ❌ Auto-route to Phase 26 after merge.
- ❌ Touch `src/`, `scripts/`, `tests/`, or `artifacts/`.

---

## 11. Test plan (CI for this doc-only PR)

- [x] `python tools/lint/run_custom_checks.py` rc = 0 expected (doc-only)
- [x] `ruff format --check` no code changed
- [x] No tests added or modified (doc-only)
- [x] CI gates: `contract-tests` + `test` (no functional change → green expected)
- [x] Branch hygiene pre-push: `git diff --stat origin/master..HEAD` shows ONLY 1 expected file

---

## 12. Sign-off

**Phase 25 is closed.** This memo is the formal record. No further Phase 25 PRs are expected unless one of the §6 reactivation criteria triggers and the user explicitly opens a sub-phase.

The next research move (when the user is ready) is **R2 (label redesign) as Phase 26-α**. That opens with a separate doc-only design memo PR analogous to the 25.0a-α / 25.0e-α / 25.0f-α pattern, carrying forward the §8 mandatory clauses verbatim and a fresh hypothesis chain calibrated for the new label class.

The user picks Phase 26 timing and label-class selection separately. **This PR stops here.**
