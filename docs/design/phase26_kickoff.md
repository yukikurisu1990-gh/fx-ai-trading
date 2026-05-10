# Phase 26 Kickoff

**Type**: doc-only kickoff memo (Phase 26 = label / target redesign)
**Status**: Phase 26 opens; label-class selection deferred to first-scope review
**Branch**: `research/phase26-kickoff`
**Base**: master @ 36edba3 (post-PR #298 merge — Phase 25 closure)
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Routing context (PR #297 → #298 → R2 leg)

PR #297 (post-F5 routing review) consolidated five evidence points and framed the routing space as **R5 (Phase 25 soft close)** vs **R2 (label redesign)**. The user selected the **R5 → R2 sequence**: close Phase 25 first, then open Phase 26 with label / target redesign.

PR #298 was the R5 leg — the Phase 25 closure memo. Phase 25 is formally closed without ADOPT_CANDIDATE.

This PR is the **R2 leg kickoff**: Phase 26 opens with a mission statement and the candidate label-class admissible space. **It does NOT pick a label class, and it does NOT initiate any dataset rebuild or eval code.** Label-class selection is deferred to a separate Phase 26 first-scope review PR; the first sub-phase design memo (26.0a-α) follows that.

---

## 1. Phase 26 mission statement (binding)

> *Phase 26 is the entry-side return on alternative **label / target designs** layered on the 20-pair canonical universe and the 8-gate harness. Phase 26 is NOT a continuation of Phase 25's feature-axis sweep — it is a structurally different phase that responds to the post-F5 load-bearing observation: the binding constraint is the realised-EV translation under the current binary path-quality label, K_FAV=1.5 / K_ADV=1.0 barrier geometry, and the spread-cost environment, NOT feature-class shortage or an AUC ceiling.*

---

## 2. Central hypothesis (inherited from #298 §2)

The Phase 25 closure memo §2 (verbatim from PR #297 §3) gives the load-bearing observation that motivates Phase 26:

> *F5 nudged AUC past F1's ceiling but failed to translate it into realised PnL. Therefore the binding constraint is not feature-class shortage or an AUC ceiling — it is structurally the realised-EV translation under the current binary path-quality label, K_FAV=1.5 / K_ADV=1.0 barrier geometry, and the spread-cost environment.*

Phase 26's central question follows directly:

> *Does a different label / target structure produce a realised-EV surface where classifier ranking translates into per-trade edge that survives the 8-gate harness?*

The Phase 25 evidence (5 evidence points — 4 F-classes + 1 deployment audit) established the existence of the gap; it did not isolate the cause. Phase 26 tests **labels** as the cause. If Phase 26 also fails to monetise across the candidate label space, the next phase (Phase 27, hypothetical) would test barrier geometry / horizon / spread-cost-environment changes. That is not in Phase 26 scope.

---

## 3. Candidate label-class admissible space (NOT pre-committed)

Four candidate label classes per the user's directive. **The kickoff enumerates them as the admissible space; it does NOT pick one.** The next PR (Phase 26 first-scope review) ranks them; the subsequent PR (26.0a-α) writes a binding design memo for the user-picked candidate.

| ID | Name | Description |
|---|---|---|
| **L-1** | **Ternary label** | TP-hit / SL-hit / time-exit. Three discrete outcomes. Preserves the time-exit class explicitly (current binary collapses time-exit into class 0). Information preservation over the current binary; same triple-barrier geometry. |
| **L-2** | **Regression on continuous path-quality score** | Continuous target (e.g., MFE − MAE differential, realised barrier EV, risk-adjusted path score, normalised excursion ratio). Most expressive of the four; allows ranking by magnitude rather than category. |
| **L-3** | **EV regression with bid/ask spread embedded in target** | Continuous EV target where bid/ask spread cost is baked into the label at construction time. Directly addresses the spread-cost-environment piece of §2's binding-constraint hypothesis. |
| **L-4** | **Trinary with explicit no-trade class** | positive / negative / no-trade. Embeds an admissibility prior at the label level; the model learns when *not* to trade. |

**This kickoff PR will NOT pre-empt the first-scope review.** The user's selection of L-1 / L-2 / L-3 / L-4 happens in the first-scope review PR, not here.

---

## 4. What Phase 26 IS (mission boundaries)

- **IS** a label / target redesign phase.
- **IS** built on the existing 20-pair canonical universe (M5 signal bars, M1 path data) and reuses the 25.0a-β infrastructure (data loaders, M1 path re-traverse, 70 / 15 / 15 chronological split discipline, calibration diagnostics).
- **IS** evaluated on the **8-gate harness (A0-A5)** — the Phase 22 thresholds remain authoritative.
- **IS** doc-then-implement, sub-phase-by-sub-phase, matching the Phase 25 design pattern: alpha = design memo (binding contract), beta = eval; verdict → scope review → next sub-phase.
- **IS** research-only at the script level (`scripts/stage26_*`). **NO `src/` changes.**

---

## 5. What Phase 26 IS NOT (binding scoping rules)

- **NOT a continuation of Phase 25's feature-axis sweep.** Phase 25 closed in #298 without ADOPT_CANDIDATE. Phase 26 is structurally a new phase: the primary research lever is **label / target design**, not feature class.
- **NOT a foreclosure of F4 / F6 / F5-d / F5-e** or any other Phase 25 deferred extension. They remain admissible-but-deferred per #298 §4. If a Phase 26 label produces a realised-EV surface where AUC > 0.55 monetises, those feature-axis extensions become eligible for re-evaluation in a Phase 26.x sub-phase under the NEW label (not a Phase 25 re-open).
- **NOT a dataset rebuild in this kickoff PR.** The dataset rebuild is the **26.0a-β** scope, after the first-scope review picks a label class and the 26.0a-α design memo locks the construction contract.
- **NOT a 26.0a-α design memo.** The 26.0a-α PR is a separate later PR; the kickoff does not pre-empt it.
- **NOT a K_FAV / K_ADV barrier-geometry change.** The first Phase 26 sub-phase inherits K_FAV = 1.5 / K_ADV = 1.0 from 25.0a-β so the label / barrier-geometry variables are not changed simultaneously. Barrier redesign is hypothetical Phase 27 scope only if Phase 26 also fails to monetise.
- **NOT a modification of γ closure (PR #279).**
- **NOT a relaxation of NG#10 / NG#11.**
- **NOT a modification of any prior Phase 25 verdict** (#284 / #287 / #290 / #293 / #296) or any Phase 25 routing review / closure (#291 / #294 / #297 / #298).
- **NOT a production deployment change.** Production v9 20-pair (Phase 9.12 closure tip `79ed1e8`) remains untouched. X-v2 OOS gating remains required for any future production deployment.
- **NOT an update to MEMORY.md.** Same pattern as Phase 25 — kickoff captured in git history.
- **NOT auto-routing to the first-scope review** or any sub-phase after merge.

---

## 6. Inheritance from Phase 25 (carried forward, binding)

These elements survive into Phase 26 unchanged. The first Phase 26 sub-phase implementation will explicitly cite this table.

| Element | Source | Status in Phase 26 |
|---|---|---|
| 20-pair canonical universe | #280 / #282 | preserved |
| M5 signal bars + M1 path data | #282 | preserved (re-used; new labels join on `(pair, signal_ts)`) |
| 70 / 15 / 15 chronological split | #283 §8 | preserved |
| 8-gate harness A0-A5 (Sharpe ≥ +0.082, ann_pnl ≥ +180 pip, MaxDD ≤ 200, A4 ≥ 3/4 folds, A5 +0.5 pip stress > 0) | Phase 22 contract | preserved as authoritative gating |
| Realised barrier PnL via M1 path re-traverse | #283 / #284 onward | preserved (re-used regardless of which label is chosen) |
| Bidirectional logistic regression + `class_weight='balanced'` | #284 onward | **default starting point for L-1 / L-4** (discrete-class labels); NOT binding for L-2 / L-3 (regression labels may use a regression model — to be decided in 26.0a-α) |
| 3 production-misuse guards (research-not-production / threshold-sweep-diagnostic / directional-comparison-diagnostic) | inherited | preserved |
| NG#10 / NG#11 | inherited | preserved (not relaxed) |
| γ closure (PR #279) | preserved | preserved |
| Calibration decile + Brier diagnostic | inherited | preserved (diagnostic-only) |
| Mandatory-clauses pattern in eval reports | inherited | preserved (Phase 26 clause set in §7) |

---

## 7. Mandatory clauses (verbatim, 6 total — to be carried forward in every Phase 26 sub-phase PR)

1. **Phase 26 framing** — *Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.*
2. **Diagnostic columns prohibition** — *Calibration / threshold-sweep / directional-comparison columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.*
3. **γ closure preservation** — *Phase 24 γ hard-close (PR #279) is unmodified.*
4. **Production-readiness preservation** — *X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure) remains untouched.*
5. **NG#10 / NG#11 not relaxed** — entry-side budget cap and diagnostic-vs-routing separation rule remain in force.
6. **Phase 26 scope** — *Phase 26 is NOT a continuation of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed; they become eligible for re-evaluation in a Phase 26.x sub-phase ONLY if a label change produces a monetisable realised-EV surface. Phase 26's primary research lever is label / target design, NOT feature class.*

---

## 8. Phase 26 PR pattern (analogous to Phase 25)

Same doc-then-implement, alpha-then-beta pattern matching the Phase 25 cadence:

```
THIS PR (Phase 26 kickoff)
  → Phase 26 first-scope review (doc-only; ranks L-1 / L-2 / L-3 / L-4; user picks)
  → 26.0a-α design memo for the picked label class (doc-only; binding contract)
  → 26.0a-β dataset rebuild + eval (research; new label parquet + eval script)
  → review post-26.0a (doc-only; verdict synthesis)
  → 26.0b-α / β next label class (if needed)
  → ... (continues until either ADOPT_CANDIDATE or phase closure)
```

The kickoff (this PR) names the pattern but does not initiate any of these steps.

---

## 9. Phase 26 first-scope review (what comes AFTER this kickoff)

The next PR on user instruction is a doc-only Phase 26 first-scope review that:

- Re-states the four admissible candidates from §3 (L-1 / L-2 / L-3 / L-4).
- Discusses prior strength and implementation cost per candidate (qualitative, NOT statistically estimated — same pattern as #294 / #297 routing reviews).
- Discusses dataset rebuild scope per candidate (some labels reuse the 25.0a-β path data with simple relabeling; others may need a fresh build with spread embedded).
- Discusses model-family implications per candidate (L-1 / L-4 fit logistic / softmax; L-2 / L-3 fit regression — to be locked in 26.0a-α).
- Recommends a starting candidate but explicitly hands the choice to the user.
- Does **NOT** initiate any dataset or eval work.

The first-scope review opens only after explicit user instruction.

---

## 10. What this PR will NOT do

- ❌ Pick a label class (L-1 / L-2 / L-3 / L-4).
- ❌ Initiate any dataset rebuild or label-construction code.
- ❌ Write the 26.0a-α design memo.
- ❌ Write the Phase 26 first-scope review.
- ❌ Modify any prior verdict (Phase 25: #284 / #287 / #290 / #293 / #296; routing reviews: #291 / #294 / #297; closure: #298).
- ❌ Modify γ closure (PR #279).
- ❌ Pre-approve production deployment.
- ❌ Update MEMORY.md.
- ❌ Touch γ closure or 8-gate harness gates.
- ❌ Foreclose F4 / F6 / F5-d / F5-e or any other Phase 25 deferred extension.
- ❌ Change K_FAV / K_ADV barrier geometry.
- ❌ Auto-route to the first-scope review after merge.
- ❌ Touch `src/`, `scripts/`, `tests/`, or `artifacts/`.

---

## 11. PR chain (Phase 26 start)

```
Phase 25 archive (closed in #298):
  #280 → #281 → #282 → #283 → #284 → #285 → #286 → #287 → #288 →
  #289 → #290 → #291 → #292 → #293 → #294 → #295 → #296 → #297 → #298

Phase 26 begins HERE:
  THIS PR (Phase 26 kickoff)
  → Phase 26 first-scope review (separate PR; user-instructed)
  → 26.0a-α design memo (separate PR after first-scope review picks a label class)
  → 26.0a-β dataset rebuild + eval (separate PR)
  → ... (sub-phase chain)
```

---

## 12. Test plan (CI for this doc-only PR)

- [x] `python tools/lint/run_custom_checks.py` rc = 0 expected (doc-only)
- [x] `ruff format --check` no code changed
- [x] No tests added or modified (doc-only)
- [x] CI gates: `contract-tests` + `test` (no functional change → green expected)
- [x] Branch hygiene pre-push: `git diff --stat origin/master..HEAD` shows ONLY 1 expected file

---

## 13. Sign-off

This memo opens Phase 26. After merge, the next PR (when the user is ready) is the **Phase 26 first-scope review** (doc-only), which ranks the four candidate label classes (L-1 / L-2 / L-3 / L-4) and hands the user the pick of which to implement first. **This kickoff PR stops here.**
