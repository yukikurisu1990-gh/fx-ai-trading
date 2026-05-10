# Phase 26 First-Scope Review

**Type**: doc-only synthesis memo (ranks the four candidate label classes; presents a tentative recommendation)
**Status**: synthesis ONLY; squash-merge approval accepts the review as the Phase 26 first-scope synthesis, but does NOT by itself authorise 26.0a-α
**Branch**: `research/phase26-first-scope-review`
**Base**: master @ ba5ab10 (post-PR #299 merge — Phase 26 kickoff)
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding, read this first)

This PR is a doc-only synthesis. **Squash-merge approval accepts this review as the Phase 26 first-scope synthesis. It does NOT by itself authorise 26.0a-α.** The user must explicitly confirm the first label class — and explicitly authorise the start of 26.0a-α — in a separate instruction after this PR merges. Until that explicit confirmation arrives, no 26.0a-α design memo, no dataset rebuild, and no eval-pipeline scaffolding starts.

This memo presents a **tentative recommendation** for the first label class (L-3, per §6). The recommendation is hand-off material for the user's decision. It is not a decision.

---

## 1. Phase 26 framing recap (from PR #299)

> *Phase 26 is the entry-side return on alternative label / target designs layered on the 20-pair canonical universe and the 8-gate harness. Phase 26 is NOT a continuation of Phase 25's feature-axis sweep.*

The four admissible candidate label classes from #299 §3:

| ID | Name | Description |
|---|---|---|
| **L-1** | Ternary label | TP-hit / SL-hit / time-exit |
| **L-2** | Regression on continuous path-quality score | MFE − MAE / realised barrier EV / risk-adjusted path score |
| **L-3** | EV regression with bid/ask spread embedded | Continuous EV target with spread cost baked in at label construction |
| **L-4** | Trinary with explicit no-trade class | positive / negative / no-trade (admissibility prior embedded) |

---

## 2. Failure-cause connection from Phase 25 (load-bearing observation, verbatim)

Verbatim from PR #298 §2 / PR #299 §2:

> *F5 nudged AUC past F1's ceiling but failed to translate it into realised PnL. Therefore the binding constraint is not feature-class shortage or an AUC ceiling — it is structurally the realised-EV translation under the current binary path-quality label, K_FAV=1.5 / K_ADV=1.0 barrier geometry, and the spread-cost environment.*

**Implication for label-class selection**: the candidate that brings the model's target *closest to realised EV under the current spread-cost environment* is the one most likely to test the H-G binary-label-binding hypothesis cleanly. This is the load-bearing prior for the §6 recommendation.

---

## 3. Relationship between L-2 and L-3 (clarifying scoping)

> *L-2 is the generic continuous path-quality regression family. L-3 is the spread-aware EV-regression specialisation of that family. Because Phase 25 identified realised-EV translation under spread-cost as the binding issue, L-3 is preferred as the first concrete test.*

L-2 in this memo refers to a continuous path-quality regression that does NOT necessarily embed bid/ask spread in the target (e.g., raw MFE − MAE, risk-adjusted excursion ratio). L-3 is the same continuous regression family with spread baked into the target at construction time. The two are not orthogonal candidates — L-3 is a more specific instance of L-2 with the spread-embedding step added. The reason L-3 leads the recommendation is precisely the §2 finding: spread-cost is the binding piece.

---

## 4. Evaluation axes (7 axes)

The memo compares L-1 / L-2 / L-3 / L-4 along these axes:

| # | Axis | Question |
|---|---|---|
| **A-1** | Realised-EV closeness | How close is the label to the per-trade realised PnL the 8-gate harness ultimately measures? |
| **A-2** | Information preservation | How much information is preserved vs. the current binary collapse? |
| **A-3** | Implementation cost | Effort to construct the label, rebuild the dataset, and adapt the eval pipeline. |
| **A-4** | Leakage / causality risk | Risk that label construction introduces forward leakage or breaks the strict-causal contract. |
| **A-5** | 8-gate harness fit | Compatibility with realised barrier PnL via M1 path re-traverse + 8-gate (A0-A5) scoring. The harness measures realised pip PnL per trade; the label is what the model regresses / classifies. |
| **A-6** | Direct verification of Phase 25 finding | How directly does this label test the H-G binary-label-binding hypothesis from #298 §2? |
| **A-7** | Suitability as first 26.0a sub-phase | Whether this label is the right starting point (vs. a follow-up under a different label) given Phase 26's overall plan. |

Evaluations are **qualitative / heuristic / not statistically estimated**. They are discussion anchors, not authoritative probabilities. The user reweights freely.

---

## 5. Per-candidate evaluation

### 5.1 — L-1 Ternary label (TP-hit / SL-hit / time-exit)

| Axis | Evaluation |
|---|---|
| A-1 Realised-EV closeness | medium — still a discrete classification; one step closer than binary by preserving the time-exit class |
| A-2 Information preservation | medium — restores the time-exit class but still collapses magnitude |
| A-3 Implementation cost | low — same triple-barrier geometry; relabel the existing 25.0a-β dataset; existing logistic pipeline extends to multi-class |
| A-4 Leakage / causality risk | low — uses the same future-window mechanics as 25.0a-β |
| A-5 8-gate harness fit | high — discrete classes fit naturally with the current threshold-on-validation pattern |
| A-6 Phase 25 finding verification | partial — tests "information loss in collapse to binary" hypothesis; does NOT directly test the spread-cost piece |
| A-7 First-pick suitability | medium — useful incremental test but not the strongest first lever |

**Verdict**: useful follow-up candidate if L-3 fails to monetise. Not the recommended first pick.

### 5.2 — L-2 Regression on continuous path-quality score

| Axis | Evaluation |
|---|---|
| A-1 Realised-EV closeness | medium-high — continuous target captures magnitude; closer to realised PnL than discrete classes; but not yet spread-aware |
| A-2 Information preservation | high — full information from the path is retained |
| A-3 Implementation cost | medium — requires regression pipeline; existing logistic pipeline does NOT extend directly; threshold-selection logic needs re-design (continuous score → trade/no-trade decision) |
| A-4 Leakage / causality risk | medium — definition of "path-quality score" (MFE − MAE, EV proxy) needs to be precise; otherwise risk of subtle look-ahead in score construction |
| A-5 8-gate harness fit | medium — fits if threshold-selection is well-defined on the validation set; harness itself is unchanged |
| A-6 Phase 25 finding verification | partial-strong — tests the binary-collapse part; partial on spread-cost (depends on whether spread is embedded — if it is, the label becomes L-3) |
| A-7 First-pick suitability | medium-high — strong general candidate but the spread-cost coverage is partial |

**Verdict**: strong general candidate. Could be the first pick if the user prefers magnitude preservation without committing to spread-embedded targets up front. See §3 for the relationship between L-2 and L-3.

### 5.3 — L-3 EV regression with bid/ask spread embedded ⭐ tentatively recommended first 26.0a candidate

| Axis | Evaluation |
|---|---|
| A-1 Realised-EV closeness | highest — target IS the realised EV (spread-cost-aware); reduces the gap between training objective and 8-gate scoring to a minimum |
| A-2 Information preservation | high — continuous target; preserves magnitude; preserves cost information |
| A-3 Implementation cost | medium-high — requires regression pipeline AND a precise spread-embedded EV definition (locked in 26.0a-α; see §5.3.1); dataset rebuild reuses 25.0a-β path data with new label computation; eval pipeline forks the threshold-selection logic |
| A-4 Leakage / causality risk | medium — 25.0a-β `spread_at_signal_pip` is signal-bar M5 spread (pre-trade); the risk is in how exit-side spread / horizon-expiry spread is handled (deferred to 26.0a-α) |
| A-5 8-gate harness fit | high — target tracks realised pip PnL directly; threshold-selection is straightforward (trade if predicted EV exceeds an admissibility threshold, definition deferred to 26.0a-α) |
| A-6 Phase 25 finding verification | strongest — directly tests the H-G binary-label-binding + spread-cost-environment hypothesis from #298 §2 |
| A-7 First-pick suitability | highest — most directly responsive to Phase 25's load-bearing finding |

**Verdict**: tentatively recommended first 26.0a candidate. The recommendation is grounded in §2's load-bearing observation, not in arbitrary preference.

#### 5.3.1 — L-3 EV definition is NOT fixed in this scope review

> *L-3 is intended to make the training target closer to realised EV by embedding bid/ask spread into target construction. The exact EV definition is deferred to 26.0a-α.*

The 26.0a-α design memo (a separate later PR, opened only on explicit user instruction) must lock at minimum the following design points:

| # | Design point | Question to answer in 26.0a-α |
|---|---|---|
| D-1 | **Horizon expiry handling** | What EV value is assigned to rows where the path exits via horizon expiry rather than TP / SL hit? Mark-to-market close-minus-entry? Truncated? Excluded? |
| D-2 | **MFE / MAE vs. actual exit PnL** | Does the label use realised exit PnL only, or does it incorporate path-internal extremes (MFE / MAE) as part of the score? |
| D-3 | **TP / SL barrier dependency** | Does the EV computation assume the K_FAV=1.5 / K_ADV=1.0 triple-barrier outcomes (inheriting 25.0a-β geometry), or does it bypass barriers and use a fixed-horizon exit? |
| D-4 | **Entry-spread-only vs. exit-side spread treatment** | Is the spread cost subtracted only at entry (using 25.0a-β `spread_at_signal_pip`), or does the EV also account for exit-side spread (which would require modelling exit-bar spread)? |
| D-5 | **Raw pip PnL vs. ATR-normalised target** | Is the regression target in raw pip units, or normalised by the signal-bar ATR (matching the K_FAV / K_ADV barrier scaling)? |
| D-6 | **Outlier clipping / winsorisation** | Does the target clip extreme PnL values (e.g., winsorise at q99 / q01) to stabilise regression? If so, the clipping thresholds are train-only-fit (analogous to F5-c tercile guard from 25.0f-α §2.6). |

These six design points are open in this scope review and become binding once 26.0a-α writes them down. The user reweights freely in 26.0a-α; this memo does not pre-commit any of the six.

### 5.4 — L-4 Trinary with explicit no-trade class

| Axis | Evaluation |
|---|---|
| A-1 Realised-EV closeness | medium — discrete classes; closer than binary by allowing explicit abstention; not magnitude-aware |
| A-2 Information preservation | medium — abstention class is novel but magnitude is still collapsed |
| A-3 Implementation cost | medium — requires defining the no-trade class (admissibility prior); class boundaries are tunable / arbitrary; pipeline extends to multi-class |
| A-4 Leakage / causality risk | medium-high — no-trade class definition is the design freedom; risk of accidentally encoding hindsight into "no-trade" (e.g., labeling rows as no-trade based on future cost windows) |
| A-5 8-gate harness fit | high — discrete classes fit; harness scoring is unchanged |
| A-6 Phase 25 finding verification | partial — tests "admissibility prior" hypothesis; less direct on spread-cost translation |
| A-7 First-pick suitability | low-medium — class-boundary design freedom is a confounder; better as a follow-up under a known label structure |

**Verdict**: better positioned as a follow-up candidate after L-3 establishes the realised-EV baseline. The "no-trade" class is interesting but its definition is too design-dependent to lead with.

---

## 6. Cross-candidate summary table

| Candidate | A-1 EV | A-2 Info | A-3 Cost | A-4 Leakage | A-5 8-gate | A-6 P25 verify | A-7 First-pick |
|---|---|---|---|---|---|---|---|
| L-1 Ternary | medium | medium | low | low | high | partial | medium |
| L-2 Path-quality regression | med-high | high | medium | medium | medium | partial-strong | med-high |
| **L-3 EV regression with spread** | **highest** | **high** | **med-high** | **medium** | **high** | **strongest** | **highest** ⭐ |
| L-4 Trinary with no-trade | medium | medium | medium | med-high | high | partial | low-med |

> Evaluations are qualitative / heuristic / not statistically estimated.

---

## 7. Tentative recommendation (binding text — recommendation, not decision)

> *Tentative recommendation: **L-3 (EV regression with bid/ask spread embedded in target)** as the first 26.0a-α target. Rationale: Phase 25's load-bearing observation (PR #298 §2) identified the binding constraint as realised-EV translation under the current binary label / barrier / spread-cost environment. L-3 brings the model's target closest to the realised PnL the 8-gate harness scores; it is the most direct test of the H-G binary-label-binding hypothesis. L-2 is a strong alternative if the user prefers magnitude preservation without committing to spread-embedded targets up front; L-1 and L-4 are better positioned as follow-ups under whichever label establishes the realised-EV baseline first.*

> **Squash-merge approval accepts this review as the Phase 26 first-scope synthesis. It does NOT by itself authorise 26.0a-α.** The user must explicitly confirm the first label class — and explicitly authorise the start of 26.0a-α — in a separate instruction after this PR merges.

---

## 8. What the next PR after this looks like (informational)

Once the user explicitly confirms the first label class and authorises 26.0a-α to start, the next PR is the **Phase 26.0a-α design memo** for that label class. Its structure mirrors the 25.0a-α / 25.0e-α / 25.0f-α design pattern:

- Lock the precise label construction rule (for L-3: the six design points in §5.3.1, plus any additional constraints).
- Lock the eval pipeline (regression head; threshold-selection logic; 8-gate harness inherits unchanged).
- Lock the sweep grid (knobs over horizon / barrier inheritance / spread basis variants — all to be enumerated in 26.0a-α).
- Strict-causal contract + bar-t lookahead unit tests required.
- Mandatory clauses verbatim.
- Doc-only PR; binding contract for 26.0a-β.

**This PR does NOT pre-empt the 26.0a-α design memo.** That PR opens only on explicit user instruction after this review merges and the label class is explicitly confirmed.

---

## 9. Mandatory clauses (verbatim, 6 total — inherited from PR #299 §7)

1. **Phase 26 framing** — *Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.*
2. **Diagnostic columns prohibition** — *Calibration / threshold-sweep / directional-comparison columns are diagnostic-only.*
3. **γ closure preservation** — *Phase 24 γ hard-close (PR #279) is unmodified.*
4. **Production-readiness preservation** — *X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure) remains untouched.*
5. **NG#10 / NG#11 not relaxed**.
6. **Phase 26 scope** — *Phase 26 is NOT a continuation of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed; primary lever is label / target design, NOT feature class.*

---

## 10. What this PR will NOT do

- ❌ Authorise 26.0a-α (squash-merge approval = scope-synthesis acceptance only; not 26.0a-α authorisation; user must explicitly confirm separately).
- ❌ Fix the L-3 EV definition (deferred to 26.0a-α per §5.3.1).
- ❌ Implement any label / dataset / eval code.
- ❌ Write the 26.0a-α design memo.
- ❌ Rebuild any dataset.
- ❌ Modify any prior verdict (Phase 25 evals / routing reviews / closure; Phase 26 kickoff).
- ❌ Modify γ closure (PR #279).
- ❌ Pre-approve production deployment.
- ❌ Update MEMORY.md.
- ❌ Foreclose any of L-1 / L-2 / L-4 (they remain admissible as follow-up candidates).
- ❌ Foreclose F4 / F6 / F5-d / F5-e Phase 25 deferred extensions.
- ❌ Change K_FAV / K_ADV barrier geometry (inherited at 1.5 / 1.0 for first 26.0a sub-phase).
- ❌ Auto-route to 26.0a-α design memo after merge.
- ❌ Touch `src/`, `scripts/`, `tests/`, or `artifacts/`.

---

## 11. PR chain (Phase 26 in progress)

```
Phase 26 begin:
  #299 (Phase 26 kickoff)
  → THIS PR (Phase 26 first-scope review — ranks L-1/L-2/L-3/L-4; tentatively recommends L-3)
  → [user explicitly confirms label class AND authorises 26.0a-α]
  → 26.0a-α design memo for the confirmed label class (separate PR; deferred L-3 EV definition decided here)
  → 26.0a-β dataset rebuild + eval (separate PR)
  → review post-26.0a (separate PR)
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

This memo is the Phase 26 first-scope synthesis. It compares the four candidate label classes per the seven evaluation axes, presents a tentative recommendation (L-3) grounded in PR #298 §2's load-bearing observation, and clarifies that L-2 and L-3 are family-and-specialisation rather than orthogonal candidates. The L-3 EV definition is intentionally left open — six design points (§5.3.1) become binding only when 26.0a-α writes them down.

**Squash-merge approval accepts this scope synthesis. It does NOT authorise 26.0a-α.** The user must explicitly confirm the first label class and explicitly authorise the start of 26.0a-α before any 26.0a-α design memo is written. **This PR stops here.**
