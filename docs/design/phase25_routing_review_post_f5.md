# Phase 25 Routing Review — Post-F5

**Type**: doc-only synthesis memo (NOT a routing decision)
**Status**: post-F5 binary routing synthesis; 5 evidence points consolidated
**Branch**: `research/phase25-routing-review-post-f5`
**Base**: master @ 5a4ca64 (post-PR #296 merge)
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Routing context (PR #294 → #296)

PR #294 (post-F3 routing review) flagged Phase 25 in **Strong Soft Stop** status with five routing options (R1-R5). The user picked **R1 (F5 liquidity / spread / volume)** explicitly framed as the LAST feature-axis attempt within Phase 25. PR #295 was the F5 design memo. PR #296 was the F5 eval.

F5's outcome is the load-bearing piece of evidence for this routing review: F5 became the FIRST F-class to push test AUC above F1's 0.5644 ceiling (best F5 = 0.5672), yet realised Sharpe was the worst of the four F-class evaluations (-0.367 vs F1 -0.192).

This memo is the **post-F5 binary routing synthesis**. The reasonable routing space has now narrowed to two substantive options — **R5 (Phase 25 soft close)** vs **R2 (label redesign)** — plus a sequenced combination. This memo consolidates the five evidence points and frames the choice; the user picks.

---

## 1. 25.0f-β finding (binding text)

> *F5 best test AUC = 0.5672 across 18 / 21 cells passing H1 (best cell: F5a_F5b_F5c, lookback=100). This is the FIRST F-class to push test AUC above F1's 0.5644 ceiling. Yet best-cell realised Sharpe = -0.3672, realised ann_pnl = -2.29M pip on ~280k trades — strictly worse than F1 (-0.192) and F3 (-0.363). All H1-pass cells are REJECT_BUT_INFORMATIVE (H1_PASS_H2_FAIL). Train-test AUC gap = 0.0042 (not overfit; structural). Calibration monotonic, Brier 0.2465. F5b (volume alone) shows clean monotonic AUC improvement with lookback (0.5505 → 0.5600 → 0.5661) — volume IS discriminative, just not monetisable on this label.*

---

## 2. Updated 5-evidence-point consolidation

**Four admissible F-classes have been tested: F1, F2, F3, F5. In addition, one deployment-layer audit (25.0d-β) tested whether the F1/F2 AUC-PnL gap could be rescued downstream. Together, these form five evidence points (4 F-classes + 1 deployment audit), not five F-classes.**

| # | Evidence point | Source | best test AUC | realised Sharpe | gap signature |
|---|---|---|---|---|---|
| 1 | F1 (volatility expansion / compression) | #284 | 0.5644 | -0.192 | CONFIRMED |
| 2 | F2 (multi-TF volatility regime) | #287 | 0.5613 | -0.317 | CONFIRMED |
| 3 | 25.0d-β deployment-layer audit | #290 | (re-fit) | -0.21 / -0.36 | H-A miscalibrated; H-B/H-D refuted; H-F **CONFIRMED** |
| 4 | F3 (cross-pair / relative currency strength) | #293 | 0.5480 (H1 FAIL) | -0.363 | CONFIRMED at sub-H1 AUC |
| 5 | **F5** (liquidity / spread / volume) | #296 | **0.5672 (H1 PASS, beats F1)** | **-0.367** | **CONFIRMED at above-ceiling AUC** |

> *Binding observation: 4 admissible F-classes + 1 deployment audit = 5 evidence points all support the structural-gap signature. F5 specifically demonstrates that the gap is independent of AUC level — improving AUC past F1's ceiling did not improve realised Sharpe.*

---

## 3. Why F5's H1 PASS + H4 FAIL changes the routing posterior decisively

**Load-bearing observation** (verbatim user interpretation post-F5):

> *F5 nudged AUC past F1's ceiling but failed to translate it into realised PnL. Therefore the binding constraint is not feature-class shortage or an AUC ceiling — it is structurally the realised-EV translation under the current binary path-quality label, K_FAV=1.5 / K_ADV=1.0 barrier geometry, and the spread-cost environment.*

**Implications for the routing posterior** (qualitative; reweighted from #294 §5):

| Hypothesis | Pre-F5 weighting | Post-F5 weighting |
|---|---|---|
| Feature-axis shortage (F4 / F6 might still help) | low (per #294) | **very low** (F5 broke F1's ceiling and still failed; remaining classes overlap F1/F2 per #291 §5.4) |
| AUC ceiling is the binding constraint | medium | **rejected** (F5 cleared F1's ceiling without monetising) |
| Realised-EV translation under current binary label / K_FAV=1.5 / K_ADV=1.0 / spread-cost environment is the binding constraint | medium | **leading hypothesis** |
| Calibration / threshold / deployment layer | low (per #290) | very low (already refuted by #290) |

> Posterior weightings remain **subjective / heuristic / not statistically estimated** — same framing as #294 §5 / §9. They are discussion anchors, not authoritative probabilities.

---

## 4. Phase 25 stop status (post-F5 strengthened)

| Stop level | Trigger | Status |
|---|---|---|
| Definitive stop (formal) | All 6 F-classes tested AND no H2 PASS | NOT met (F4 / F6 untested) |
| **Strong soft stop** | 3+ F-classes + 1 deployment audit confirm gap | **STILL MET** |
| **Strengthened beyond #294** | F5 (LAST high-orthogonality F-class) confirms the gap above F1's ceiling | **NEW: post-F5 strengthening** |
| F4 / F6 routing | low-priority per #291 §5.4 (overlap with F1 / F2) | now even less attractive in light of F5 result |

**Phase 25 is now in Strong Soft Stop, post-F5 strengthened.** The reasonable routing space has narrowed from five options (#294 §5) to two substantive options (R5 / R2) plus a sequencing combination.

---

## 5. Routing space narrowed to 2 substantive options

| ID | Path | Cost | Posterior expectation (qualitative) |
|---|---|---|---|
| **R5** | **Phase 25 soft close** — current sweep stops; production v9 20-pair untouched; future label / feature work is a new phase | very low | n/a (phase-management decision, not signal-search) |
| **R2** | **Label redesign** — H-G binary-label-binding hypothesis; rebuild dataset with alternative label class | high | **medium** (best lever if H-G is correct; F5 result moves this from "promising" to "leading hypothesis") |

### 5.1 Retired / deferred options (relative to PR #294 §5)

| ID | Path | Status |
|---|---|---|
| R1 | F5 — done in #296; result REJECT_BUT_INFORMATIVE / H1 PASS, H2/H3/H4 FAIL | retired |
| R3 | F4 (range compression) | DEFERRED — F5 directly tested whether AUC > F1 ceiling helps; broke the ceiling without monetising. F4 would be redundant work given the post-F5 posterior. |
| R4 | F6 (higher-TF) | DEFERRED — same reasoning as R3 |

> Deferring is **not the same as foreclosing**. If R2 (label redesign) succeeds and a new label re-opens the question of which feature classes monetise best, F4 / F6 / F5 sub-extensions (F5-d tick imbalance, F5-e pair liquidity rank) become eligible again under a new phase.

---

## 6. R5 (Phase 25 soft close) — deep-dive

R5 is a **phase-management decision** that stops the current Phase 25 feature-axis sweep. Same scoping rule as PR #294 §8.

| Deliverable | Content |
|---|---|
| Phase 25 closure memo (next-PR if R5 is picked) | Synthesis of F1 + F2 + 25.0d + F3 + F5 (5 evidence points); declares Phase 25 closed without ADOPT |
| Reactivation criteria | Conditions under which Phase 25 could re-open (new label class, new dataset, new path-EV target structure) |
| Production stance | NG#10 / NG#11 untouched; γ closure (PR #279) unmodified; production v9 20-pair (Phase 9.12 closure tip 79ed1e8) remains as-is |
| Roadmap re-prioritisation note | What Phase 26 could look like — likely a label-redesign phase that subsumes R2 |

**Critical scoping rule (binding, restated from #294 §8):**

> *Soft close stops the **current Phase 25 sweep**. It does **NOT** prevent label redesign, future feature-axis revisits, or any other research direction. It does **NOT** declare the F1-F6 admissible-feature space exhausted. It declares only that the current Phase 25 sweep has reached strong soft-stop and the next research move is more naturally framed as a new phase rather than another F-class within Phase 25.*

R5 is a phase-management routing choice. **It does not decide on or against R2 — it is fully compatible with R2 being executed as the kickoff of Phase 26.**

---

## 7. R2 (label redesign) — deep-dive

R2 is the natural pivot per the post-F5 posterior shift in §3.

| Hypothesis | Statement |
|---|---|
| **H-G binary-label binding** | The K_FAV=1.5 × ATR / K_ADV=1.0 × ATR triple-barrier binary label collapses too much information; even a discriminative classifier cannot translate ranking into edge-aware monetisation on this realised-PnL surface. F5's "AUC up, Sharpe down" result is the cleanest single piece of evidence for this. |

### 7.1 Possible alternative label classes (not exhaustive, not pre-committed)

| Alt | Description | Notes |
|---|---|---|
| L-1 | **Ternary label**: TP-hit / SL-hit / Time-exit | Information preservation over binary; preserves time-exit class explicitly. |
| L-2 | **Regression on path-quality score** | Continuous target (e.g., MFE − MAE differential, or normalised excursion ratio). Most expressive of the four. |
| L-3 | **Calibrated EV regression with bid/ask spread embedded in target** | Directly addresses the spread-cost environment piece of the §3 binding-constraint hypothesis. |
| L-4 | **Trinary with explicit "no-trade" class** | Embeds an admissibility prior at the label level; the model learns when *not* to trade. |

### 7.2 Cost / framing

- **Cost**: high — re-build dataset, re-run all priors, ~3-5 days minimum for a full eval cycle.
- **When to pick**: now, if the user judges 5 evidence points sufficient and wants to test the H-G hypothesis directly.
- **What this PR does NOT do**: this PR does NOT initiate label redesign. The R2 path, if picked, opens with a separate Phase 25.5-α / Phase 26-α design memo PR (analogous to 25.0a-α / 25.0e-α / 25.0f-α design pattern).

---

## 8. R5 vs R2 — sequencing, not exclusion

The two options are **not mutually exclusive**. The realistic framing:

| Sequence | Description |
|---|---|
| **R5 only** | Soft-close Phase 25; no immediate label redesign. User picks Phase 26 (or any other next phase) timing separately. |
| **R5 → R2** | Soft-close Phase 25 with a closure memo, then open Phase 26 with R2 as kickoff (label-redesign design memo). Clean phase boundary. |
| **R2 directly** | Treat F5 result as definitive enough; go straight to label redesign as a Phase 25.5 sub-phase, deferring formal closure of Phase 25. |

**R5 only and R5 → R2 end up in the same place** if the user wants to pursue label redesign next. The choice is about closure-memo timing and phase-boundary clarity vs. continuity. **R2 directly skips the closure memo** in favour of treating R2 as a continuation of Phase 25.

---

## 9. User-facing decision matrix

| Choice | Cost | Expected payoff (qualitative) | Closes Phase 25? |
|---|---|---|---|
| **R5 only** → soft close | very low | n/a (phase-management) | YES |
| **R5 → R2** | very low + high | medium | YES (then opens Phase 26) |
| **R2 directly** | high | medium | No (Phase 25.5 sub-phase) |
| Re-open R3 (F4) / R4 (F6) | medium | very low | No |

> Posterior payoff tags are **subjective / heuristic / not statistically estimated**. They reflect rough qualitative weighting after 4 F-classes + 1 deployment audit. The user reweights freely. This memo presents R5 and R2 as equally valid routes; R5 is the conservative default, R2 is the substantive next research move.

---

## 10. Stop conditions that would change after this routing review

| If user picks | Then |
|---|---|
| R5 only | Phase 25 declared closed; production v9 20-pair remains; user picks Phase 26 timing separately |
| R5 → R2 (sequence) | Phase 25 closure memo lands; Phase 26 opens with label-redesign design memo (analogous to 25.0a-α / 25.0e-α / 25.0f-α pattern) |
| R2 directly | Phase 25.5-α label-redesign design memo opens; Phase 25 stays formally open as containing the label-redesign sub-phase |
| R3 / R4 (F4 / F6) re-opened | Phase 25 stays in Strong Soft Stop, post-F5 strengthened; one more low-priority evidence point added |

---

## 11. Mandatory clauses (verbatim, 6 total — to be carried forward in any subsequent PR)

1. **Phase 25 framing** (inherited from #280) — *Phase 25 is the entry-side return on alternative admissible feature classes (F1-F6) layered on the 25.0a-β path-quality dataset. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.*
2. **Diagnostic columns prohibition** — *Calibration / threshold-sweep / directional-comparison columns are diagnostic-only.*
3. **γ closure preservation** — *Phase 24 γ hard-close (PR #279) is unmodified.*
4. **Production-readiness preservation** — *X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure tip 79ed1e8) remains untouched.*
5. **NG#10 / NG#11 not relaxed**.
6. **Routing review scoping** — *This memo is a synthesis, not a decision. The user picks R5 / R5→R2 / R2 directly / R3 or R4 re-opened. Posterior weightings in §3 / §5 / §9 are subjective / heuristic / not statistically estimated.*

---

## 12. PR chain reference

```
#280 (Phase 25 kickoff)
  → #281 / #282 (25.0a dataset)
  → #283 / #284 (F1 design + eval)
  → #285 (review post-F1)
  → #286 / #287 (F2 design + eval)
  → #288 (review post-F2)
  → #289 / #290 (25.0d-β deployment audit design + eval)
  → #291 (review post-deployment-audit)
  → #292 / #293 (F3 design + eval)
  → #294 (review post-F3)
  → #295 / #296 (F5 design + eval — LAST feature-axis attempt within Phase 25)
  → THIS PR (Phase 25 routing review post-F5 — synthesis of 5 evidence points;
              R5 / R5→R2 / R2 directly framed as binary routing)
  → R5 only OR R5 → R2 OR R2 directly OR R3 / R4 re-opened — user picks
```

---

## 13. What this PR will NOT do

- ❌ Pick a routing decision; this is a synthesis memo only.
- ❌ Initiate label redesign or write any label-redesign code.
- ❌ Write the Phase 25 closure memo (that's a separate PR if R5 is picked).
- ❌ Modify any prior verdict (#284 / #287 / #290 / #293 / #296).
- ❌ Pre-approve production deployment.
- ❌ Update `MEMORY.md` (closure memo deferred per established Phase 25 pattern).
- ❌ Touch γ closure or 8-gate harness gates.
- ❌ Auto-route to next PR after merge.
- ❌ **Close Phase 25 in this PR** (closure is its own separate doc-only PR if R5 is picked).
- ❌ Re-open R3 (F4) or R4 (F6) on its own — the user reweights and decides.

---

## 14. Sign-off

This memo is a synthesis only. After the user picks one of the routing options, the next PR is one of:

- **R5 only**: Phase 25 closure memo PR (~250-300 lines; declares closure; carries reactivation criteria; references all 5 prior evidence points).
- **R5 → R2 sequence**: Phase 25 closure memo PR first, then a separate Phase 26-α label-redesign design memo PR.
- **R2 directly**: Phase 25.5-α label-redesign design memo PR (binding contract for a new dataset rebuild; analogous to 25.0a-α / 25.0e-α / 25.0f-α design pattern).
- **R3 or R4 re-opened**: F4 or F6 design memo PR (low-priority; not recommended given §3 posterior shift, but the user can choose).

The user picks. **This PR stops here.**
