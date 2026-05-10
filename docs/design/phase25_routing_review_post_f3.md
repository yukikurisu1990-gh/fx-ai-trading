# Phase 25 Routing Review — Post-F3

**Type**: doc-only synthesis memo (NOT a routing decision)
**Status**: mid-stage synthesis after PR #293 (F3 eval); 4 evidence points consolidated
**Branch**: `research/phase25-routing-review-post-f3`
**Base**: master @ ac39d11 (post-PR #293 merge)
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Routing context (PR #291 → #293)

PR #291 (routing review post-deployment-audit) consolidated three converging signals — F1 best cell (PR #284), F2 best cell (PR #287), and 25.0d-β deployment-layer audit (PR #290) — and surfaced 7 routing options with a per-class prioritisation framework. The user picked **Option A (F3 cross-pair / relative currency strength)** because F3 was the most orthogonal admissible F-class to F1 and F2.

PR #292 was the F3 design memo. PR #293 was the F3 eval. F3 came back **even worse than the design memo anticipated**: best cell H1 FAIL (AUC 0.5480 < 0.55), H2 FAIL, H3 FAIL, H4 FAIL. F3 escapes neither the H1 admissibility threshold nor the AUC-PnL gap.

This memo is the **mid-stage synthesis** that consolidates the four evidence points and lays out the remaining routing space, **without making the decision**. The user picks.

---

## 1. 25.0e-β finding (binding text)

> *F3 best test AUC = 0.5480 across all 18 cells (BELOW the H1 PASS threshold of 0.55). Best-cell realised Sharpe = -0.3628; ann_pnl = -2.11M pip on ~259k trades. H1, H2, H3, and H4 all FAIL. Train-test AUC gap is ~0.007 — not an overfit; structural ceiling. Best cell is well-calibrated (decile reliability monotonic; Brier 0.2325). This is a stronger result than the 25.0e-α design memo anticipated: F3 escapes neither H1 nor the AUC-PnL gap.*

---

## 2. Updated evidence consolidation (4 evidence points; **not** 4 F-classes)

**Three admissible F-classes have been tested: F1, F2, F3. In addition, one deployment-layer audit tested whether the F1/F2 AUC-PnL gap could be rescued downstream. Together, these form four evidence points, but not four F-classes.**

| # | Evidence point | Source | Best test AUC | Realised Sharpe | Gap signature |
|---|---|---|---|---|---|
| 1 | **F1** (volatility expansion / compression) | PR #284 | 0.5644 | -0.192 | CONFIRMED |
| 2 | **F2** (multi-TF volatility regime) | PR #287 | 0.5613 | -0.317 | CONFIRMED |
| 3 | **25.0d-β deployment-layer audit** (re-fit of F1+F2 best) | PR #290 | re-fit | -0.21 / -0.36 | H-A miscalibrated; H-B/H-D refuted; H-F **CONFIRMED** |
| 4 | **F3** (cross-pair / relative currency strength) | PR #293 | **0.5480 (H1 FAIL)** | -0.363 | CONFIRMED even at sub-H1 AUC |

> *Binding observation*: 3 F-classes + 1 deployment audit all support the structural-gap signature. F3 H4 FAIL specifically activates **PR #291 §6.4 strong soft-stop strengthening**. Two F-classes remain untested at this point in the sweep: **F4 (range compression)** and **F6 (higher-TF)**, both ranked LOWER-priority by PR #291 §5.4 due to overlap with F1/F2. **F5 (liquidity)** also remains untested.

---

## 3. Why F3's H1 FAIL matters more than F1's or F2's H1 PASS

F3 was selected (#291 §5.4) as the **most orthogonal admissible class** to F1/F2. The expectation was that orthogonality alone could push test AUC past the structural ceiling. Instead:

- F3 best AUC (0.5480) is **below** F1 best (0.5644) and F2 best (0.5613).
- This is **NOT** a sample-size, calibration, or overfitting issue:
  - n_test = 564,298 (huge),
  - decile reliability monotonic with Brier 0.2325 (well-calibrated),
  - train-test AUC gap ~0.007 (no overfit signature).
- F3 still hits the gap signature on the realised PnL side (Sharpe -0.363).

**Implication**: the structural ceiling is not a property of one feature axis. It appears to be a property of the **LdP-style binary path-quality label** at K_FAV=1.5×ATR / K_ADV=1.0×ATR on the 25.0a-β-spread dataset. The label-design hypothesis (PR #291 Option F; "H-G binary-label-binding") gains weight relative to the feature-class hypotheses (Options A-D from #291).

This is a **shift in posterior weighting**, not a final inference. F4/F5/F6 remain untested.

---

## 4. Phase 25 stop status

| Stop level | Trigger | Status |
|---|---|---|
| Definitive stop | All 6 F-classes tested AND no H2 PASS | **NOT met yet** (F4/F5/F6 untested) |
| **Strong soft stop** | **3 F-classes + 1 deployment audit all support the structural-gap signature** | **MET** |
| Soft stop (general) | 3+ evidence points all show same signature | met (already at #291) |
| F3-specific strengthening | F3 H4 FAIL | **TRIGGERED** (per #291 §6.4) |

**Phase 25 is currently in Strong Soft Stop status.** The user is at the decision point. The remaining options span feature-axis attempts (F5/F4/F6), label redesign, and Phase 25 soft close.

---

## 5. Remaining routing space (5 options)

PR #291 listed 7 options (A-G). Three are now retired or refined:

- **Option A (F3)** — done in PR #293; result REJECT_NON_DISCRIMINATIVE.
- **Option E (calibration-before-threshold)** — superseded; F3 calibration was already monotonic, so calibration-only intervention would not help on the F3 axis. Kept implicit; no longer a standalone routing arm.
- **Option B (F5)** — still open. Reframed as R1 below.

The remaining decision space is now five routing options:

| ID | Path | Cost | Posterior expectation (qualitative) |
|---|---|---|---|
| **R1** | **F5** — liquidity / volume / spread loaders (last high-orthogonality F-class) | medium | **low-to-medium** |
| **R2** | **Label redesign** — H-G binary-label-binding hypothesis | high | **medium** |
| **R3** | **F4** — range compression | medium | **very low** (overlap with F1/F2 per #291 §5.4) |
| **R4** | **F6** — higher-TF | medium | **very low** (overlap with F1/F2 per #291 §5.4) |
| **R5** | **Phase 25 soft close** — synthesis memo only; current sweep stops | very low | n/a (decision-level recommendation) |

> **Posterior expectations are subjective / heuristic / not statistically estimated.** They reflect rough qualitative weighting after 3 F-classes + 1 deployment audit, and are intended as discussion anchors only. The user reweights freely.

---

## 6. R1 (F5 liquidity) — deep-dive

F5 is the **last plausible feature-axis attempt** before the label-redesign hypothesis (R2) becomes the leading candidate. F5 is dedicated this section because it is the only remaining HIGH-orthogonality F-class per PR #291 §5.4.

| Aspect | Detail |
|---|---|
| Feature ideas | rolling spread mean / std; volume z-score (M1 BA jsonl carries `volume`); bid/ask imbalance; pip-spread regime indicator |
| Data dependencies | Volume already in M1 BA jsonl. Spread series already embedded in 25.0a-β. **No new data extension required** — this corrects PR #291 §5.4's "data ext cost" estimate. |
| Risk | F5 may correlate with F1 vol-regime (high spread ↔ high vol), reducing actual orthogonality |
| Cost estimate | ~1–2 days (eval + report) |
| Decision implication | If F5 ALSO confirms the structural-gap signature, the case for **definitive stop on feature-axis approach within Phase 25** strengthens substantially; R2 (label redesign) becomes the leading remaining candidate. |

---

## 7. R2 (label redesign) — deep-dive

R2 is the natural pivot if R1 also confirms the structural ceiling — or if the user decides 3 F-classes + 1 deployment audit is already enough evidence to pivot directly without F5.

| Hypothesis | Statement |
|---|---|
| **H-G binary-label binding** | The K_FAV=1.5×ATR / K_ADV=1.0×ATR triple-barrier binary label collapses too much information; the model can rank candidates internally but cannot translate ranking into edge-aware threshold selection on this realised-PnL surface. |

**Possible alternative label classes** (not exhaustive, not pre-committed):

| Alt | Description |
|---|---|
| L-1 | Ternary label: TP-hit / SL-hit / Time-exit |
| L-2 | Regression on path-quality score (continuous, e.g., MFE-MAE differential) |
| L-3 | Calibrated EV regression with bid/ask spread embedded in the target |
| L-4 | Trinary with explicit "no-trade" class to embed an admissibility prior |

**Cost**: high — re-build dataset, re-run all priors, ~3–5 days.

**When to pick**: after F5 (R1) also confirms the structural ceiling; OR if the user chooses to skip F5 and treat #291 §6.4 strong-soft-stop strengthening as already definitive.

---

## 8. R5 (Phase 25 soft close) — deep-dive

Soft close is the most conservative routing choice. R5 has its own deliverables.

| Deliverable | Content |
|---|---|
| Phase 25 closure memo | Synthesis of F1+F2+25.0d+F3 (and F5 if R1 was picked first); declares Phase 25 closed without ADOPT |
| Reactivation criteria | Conditions under which Phase 25 could re-open (e.g. new label class, new dataset, new path-EV target structure) |
| Production stance | NG#10 / NG#11 untouched; γ closure (PR #279) unmodified; production v9 20-pair (Phase 9.12 closure tip 79ed1e8) remains as-is |
| Roadmap re-prioritisation note | What Phase 26+ could look like — likely label-class focused (R2-style), or a structurally different path-EV target |

**Critical scoping rule** (binding):

> *Soft close stops the **current Phase 25 sweep**. It does **NOT** prevent label redesign, future feature-axis revisits, or any other research direction. It does **NOT** declare the F1-F6 admissible-feature space exhausted. It declares only that the current Phase 25 sweep has reached strong soft-stop and the next research move is more naturally framed as a new phase / sub-phase rather than another F-class within Phase 25.*

R5 is a phase-management routing choice; it is independent of the label / feature hypothesis space.

---

## 9. User-facing decision matrix

A clean comparison table the user can read in 30 seconds. **Informational only.**

| Choice | Cost | Expected payoff (qualitative) | Closes Phase 25? |
|---|---|---|---|
| R1 → F5 | medium | low-to-medium | No (F5 is still admissible class) |
| R2 → label redesign | high | medium (best lever if H-G is correct) | No (would open Phase 25.5 or Phase 26 label-redesign branch) |
| R3 → F4 | medium | very low (overlap with F1/F2) | No |
| R4 → F6 | medium | very low (overlap with F1/F2) | No |
| R5 → soft close | very low | n/a (phase-management, not signal-search) | YES (current sweep) |

> The above qualitative payoff tags are subjective / heuristic / not statistically estimated. They reflect rough weighting after 3 F-classes + 1 deployment audit. The user reweights freely.

---

## 10. Stop conditions that would change after this routing review

| If user picks | Then |
|---|---|
| R1 (F5) | If F5 also confirms gap → **definitive stop** for feature-axis approach within Phase 25; R2 becomes the leading remaining candidate |
| R2 (label redesign) | Suspend the current Phase 25 F-class sweep; open a label-redesign sub-phase. F4/F5/F6 stay deferred unless re-opened later. |
| R3 / R4 (F4 / F6) | One more evidence point added; Phase 25 stays in soft-stop status; user re-evaluates after the next eval |
| R5 (soft close) | Phase 25 declared closed; production v9 20-pair remains; future label / feature work is a new phase or sub-phase |

---

## 11. Mandatory clauses (verbatim, 6 total — to be carried forward in any subsequent PR)

1. **Phase 25 framing** (inherited from #280 kickoff) — *Phase 25 is the entry-side return on alternative admissible feature classes (F1-F6) layered on the 25.0a-β path-quality dataset. ADOPT requires both H2 PASS and the full 8-gate A1-A5 harness.*
2. **Diagnostic columns prohibition** — *Calibration / threshold-sweep / directional-comparison columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.*
3. **γ closure preservation** — *Phase 24 γ hard-close (PR #279) is unmodified.*
4. **Production-readiness preservation** — *X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure) remains untouched.*
5. **NG#10 / NG#11 not relaxed** — *25.0e routing PRs do not change the entry-side budget cap or the diagnostic-vs-routing separation rule.*
6. **Routing review scoping** — *This memo is a synthesis, not a decision. The user picks R1 / R2 / R3 / R4 / R5. Posterior expectations in §5 / §9 are subjective / heuristic / not statistically estimated.*

---

## 12. PR chain reference

```
#280 (Phase 25 kickoff)
  → #281 (25.0a-α dataset spec) → #282 (25.0a-β dataset)
  → #283 (25.0b-α F1 design) → #284 (25.0b-β F1 eval — REJECT_BUT_INFORMATIVE)
  → #285 (first scope review, post-F1)
  → #286 (25.0c-α F2 design) → #287 (25.0c-β F2 eval — REJECT_BUT_INFORMATIVE)
  → #288 (second scope review, post-F2)
  → #289 (25.0d-α deployment audit design) → #290 (25.0d-β deployment audit eval)
  → #291 (routing review post-deployment-audit)
  → #292 (25.0e-α F3 design) → #293 (25.0e-β F3 eval — REJECT_NON_DISCRIMINATIVE; H1/H2/H3/H4 all FAIL)
  → THIS PR (Phase 25 routing review post-F3 — synthesis of 4 evidence points)
  → R1 / R2 / R3 / R4 / R5 (separate PR; user picks one)
```

---

## 13. What this PR will NOT do

- ❌ Pick a routing decision; this is a synthesis memo only.
- ❌ Implement any F-class, label-redesign code, or closure memo.
- ❌ Modify any prior verdict (#284 / #287 / #290 / #293).
- ❌ Pre-approve production deployment.
- ❌ Update MEMORY.md (closure memo deferred per established Phase 25 pattern).
- ❌ Touch γ closure or 8-gate harness gates.
- ❌ Auto-route to next PR after merge.

---

## 14. Sign-off

This memo is a synthesis only. After the user picks one of R1 / R2 / R3 / R4 / R5, the next PR is one of:

- **R1**: 25.0f-α F5 liquidity design memo (analogous to 25.0b-α / 25.0c-α / 25.0e-α design pattern).
- **R2**: 25.0g-α label redesign design memo (binding contract for a new dataset re-build).
- **R3**: 25.0h-α F4 range compression design memo (lower-priority).
- **R4**: 25.0i-α F6 higher-TF design memo (lower-priority).
- **R5**: Phase 25 closure memo (declares the sweep closed without ADOPT; carries reactivation criteria).

The user picks. This PR stops here.
