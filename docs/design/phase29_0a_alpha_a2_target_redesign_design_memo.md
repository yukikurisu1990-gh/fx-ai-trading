# Phase 29.0a-α A2 Target Redesign Design Memo — Closed 4-Target Allowlist (T1 Fixed-Horizon Executable Close / T2 Time-Weighted / T3 Multi-Horizon / T4 Asymmetric K_FAV/K_ADV); All D-1 Executable; Phase 29 §10 Per-Target Baseline Reference under Option 9c; H-D1 4-Outcome Ladder

**Type**: Phase 29 first sub-phase α design memo. **Doc-only**.
**Branch**: `research/phase29-0a-alpha-a2-target-redesign`
**Base**: master @ `9d1dd36` (post-PR #349; Phase 29 first-mover routing review recommendation accepted)
**Pattern**: analogous to PR #344 (28.0c-α A0-narrow design memo) + PR #341 (28.0b-α A4 design memo) + PR #337 (28.0a-α A1 design memo)
**Date**: 2026-05-20

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the formal **Phase 29.0a-α A2 target redesign design memo**. It pre-states the **closed 4-target allowlist** under A2 single-axis scope (T1 fixed-horizon executable close PnL / T2 time-weighted realised PnL / T3 multi-horizon realised PnL / T4 asymmetric K_FAV/K_ADV barrier PnL), the **fixed non-target axes** (R7-A feature surface / tabular LightGBM / top-q selection / symmetric Huber α=0.9 loss), the **6-cell structure**, the **Phase 29 §10 baseline reference policy under Option 9c**, the **H-D1 4-outcome ladder per target**, and the **NG#A2-1 / NG#A2-2 / NG#A2-3 anti-collapse guards**. All 4 target variants are **D-1 executable** and **formal-eval admissible**; no DIAGNOSTIC-ONLY target variants are included in the closed allowlist.*
>
> *This PR does **NOT**:*
>
> - *initiate the Phase 29.0a-β eval (no `scripts/stage29_0a_*.py`; no `tests/unit/test_stage29_0a_*.py`; no `artifacts/stage29_0a/`);*
> - *create any A0-broad / R-B / A3 design memo;*
> - *admit any joint-axis sub-phase (Policy C single-axis default; A2 alone per PR #349 primary recommendation);*
> - *modify the Phase 28 §10 baseline numeric (immutable; archived; inherited as DIAGNOSTIC-ONLY 2nd reference per Option 9c);*
> - *modify any prior verdict (Phase 27 + Phase 28 sub-phase β verdicts preserved verbatim);*
> - *modify the production v9 wiring (Phase 9.12 tip `79ed1e8`; untouched);*
> - *relax ADOPT_CANDIDATE wall, NG#10, NG#11, γ closure PR #279, X-v2 OOS gating, or the Phase 22 frozen-OOS contract;*
> - *auto-route to Phase 29.0a-β after merge.*
>
> *The β-eval implementation is a **separate later PR** (recommended path: `scripts/stage29_0a_a2_target_redesign_eval.py` + `tests/unit/test_stage29_0a_a2_target_redesign_eval.py` + `artifacts/stage29_0a/eval_report.md`). The pre-stated parameters and closed 4-target allowlist are fixed at α and cannot be changed at β; any change requires a memo amendment PR back to α.*

Same approval-then-defer pattern as PR #341 (28.0b-α A4) / PR #344 (28.0c-α A0-narrow).

---

## 1. A2 mission statement

**Phase 29.0a tests A2 (target redesign) as the Phase 29 first sub-phase per PR #349 primary recommendation.** The hypothesis is that the **triple-barrier realised-PnL target's specification** (K_FAV=1.5×ATR / K_ADV=1.0×ATR / H_M1=60) is the binding constraint on Sharpe lift across the 8-eval picture. Phase 29.0a replaces this target with a **closed allowlist of 4 alternative target framings**, keeping the R7-A feature surface, tabular LightGBM model class, top-q selection rule, and symmetric Huber α=0.9 loss **all fixed**. Only the target changes.

This sub-phase is Phase 29's first exercise of **Option 9c** (PR #348 §9): the Phase 28 §10 baseline numeric remains immutable as the archived DIAGNOSTIC-ONLY 2nd reference, while this sub-phase defines a **Phase 29 §10 per-target baseline reference** (one numeric tuple per target variant) for FAIL-FAST.

A2 is single-axis per Policy C default (PR #348 §7); A0-broad / R-B / A3 / joint admission are deferred-not-foreclosed.

---

## 2. Why A2 is not Phase 27/28 inertia (axis-purity distinction)

A2 is structurally distinct from each Phase 27 / Phase 28 single-axis attack:

### 2.1 A2 ≠ S-axis score micro-redesign (27.0b/c/d/e/f)

- S-axis varied the **score formulation** (S-C TIME penalty / S-D calibrated EV / S-E regression / quantile family trim / R7-C regime feature) while the target remained triple-barrier realised PnL.
- A2 varies the **target itself**; the score remains S-E regression (27.0d backbone) verbatim.
- NG#A2-1 enforces S-E score backbone fixed; score-axis variation requires separate scope amendment.

### 2.2 A2 ≠ A1 loss redesign (28.0a)

- A1 varied the **loss function** (L1 asymmetric Huber α=0.5 / L2 Huber α=0.7 / L3 Huber α=0.9 + regime sample weights) while target remained triple-barrier realised PnL.
- A2 varies the **target**; loss remains symmetric Huber α=0.9 verbatim.

### 2.3 A2 ≠ A4 selection rule redesign (28.0b)

- A4 varied the **selection rule** (R1 / R2 / R3 / R4) while target remained triple-barrier realised PnL.
- A2 varies the **target**; selection rule remains top-q on score (quantile family {5, 10, 20, 30, 40}) verbatim.

### 2.4 A2 ≠ A0-narrow tabular architecture-topology audit (28.0c)

- A0-narrow varied the **tabular topology** (AR1 hierarchical / AR2 pair-specialist / AR3 stacked / AR4 deterministic regime split) while target remained triple-barrier realised PnL.
- A2 varies the **target**; tabular LightGBM with single regressor topology (27.0d C-se equivalent) verbatim.

### 2.5 A2 ≠ R-T2 quantile trim (27.0e)

- R-T2 varied the **quantile family** (5 / 7.5 / 10) while target remained triple-barrier realised PnL.
- A2 varies the **target**; quantile family {5, 10, 20, 30, 40} verbatim.

### 2.6 A2 absorbs R-T3 (Phase 27 carry-forward; target-adjacent)

- R-T3 was a Phase 27 carry-forward (target-adjacent; never admitted standalone). PR #347 §12 declared R-T3 admissible only under an A2 sub-phase.
- Phase 29.0a-α A2 **absorbs R-T3** as part of the closed target allowlist; specifically, the T3 multi-horizon variant covers the R-T3 dimension.
- R-T3 standalone elevation is NOT admissible; R-T3 is resolved under A2 frame analogous to R-T1 resolution under A4 frame (PR #342).

---

## 3. Formal H-D1 hypothesis statement

> **H-D1 (A2 target redesign scope)**: At least one of the four closed target variants {T1, T2, T3, T4} will produce a val-selected configuration on the C-d1-Tx cell satisfying **all** of:
>
> 1. **H2 PASS**: val Sharpe lift ≥ **+0.05 absolute** vs Phase 29 §10 per-target baseline.
> 2. **H1m preserved**: val-selected cell Spearman score-vs-pnl ≥ **+0.30**.
> 3. **H3 PASS**: trade count ≥ **20,000**.
> 4. **Per-target Phase 29 §10 baseline reproduction PASS** (FAIL-FAST gate).
>
> **OR** H-D1 is FALSIFIED at the variant.

### 3.1 H-D1 falsification interpretation — FALSIFIED_A2_NARROW vs FALSIFIED_ALL_A2

Analogous to PR #344 §12.2 FALSIFIED_A0_NARROW load-bearing distinction.

- **If all 4 target variants FALSIFIED** (any combination of row 2 PARTIAL_SUPPORT / row 3 FALSIFIED_TARGET_INSUFFICIENT / row 4 PARTIAL_DRIFT_TARGET_REPLICA without any PASS) → the result is **FALSIFIED_A2_NARROW**, not `FALSIFIED_ALL_A2`.
- **Alternative target framings outside the closed 4-target allowlist remain admissible** via separate scope amendment PR. Phase 29.0a-α A2 only tests the 4 specific target variants in §6.
- **This PR explicitly does not claim `FALSIFIED_ALL_A2` under any β outcome.**

---

## 4. Closed 4-target allowlist (formal pre-statement)

**All 4 target variants are D-1 executable and formal-eval admissible**. No DIAGNOSTIC-ONLY target variants are included in the closed allowlist. NG#A2-1 enforces.

| Variant | Definition | Fixed numerics | D-1 status | ADOPT_CANDIDATE-eligible |
|---|---|---|---|---|
| **T1** | fixed-horizon executable close PnL | H_M1 = 60; no TP/SL barrier; entry at signal using D-1 bid/ask side; exit at H_M1 = 60 using D-1 bid/ask side | **PASS** (D-1 executable; bid/ask entry+exit) | yes |
| **T2** | time-weighted realised PnL | H_M1 = 60; linear decay = `(1 - hold_bars / H_M1)`; barrier definition inherited from 27.0d | **PASS** (inherited triple-barrier PnL × deterministic scalar) | yes |
| **T3** | multi-horizon realised PnL (absorbs R-T3) | horizons H = {30, 60, 120}; per-horizon triple-barrier PnL summed; barrier multipliers K_FAV=1.5 / K_ADV=1.0 unchanged | **PASS** (each horizon uses inherited bid/ask executable barrier PnL; sum preserves executable semantics) | yes |
| **T4** | asymmetric K_FAV / K_ADV barrier PnL | K_FAV = 2.0 × ATR; K_ADV = 0.5 × ATR; H_M1 = 60; ATR window unchanged | **PASS** (same harness as 27.0d; different barrier multipliers) | yes |

### 4.1 T1 — fixed-horizon executable close PnL (D-1 PASS)

- **Entry**: at signal_ts, using D-1 bid/ask executable side per inherited harness (long direction → enter at ask; short direction → enter at bid).
- **Exit**: at signal_ts + H_M1 = 60 M1 bars (fixed horizon; no path-dependent early exit; no TP/SL barrier).
- **Exit side**: D-1 bid/ask executable per inherited harness (long direction exit → bid; short direction exit → ask).
- **Realised PnL**: executable entry price → executable exit price; pip-denominated per pair.
- **No barrier**: T1 tests the **horizon-only / no-barrier framing** with D-1 executable semantics fully preserved.
- **D-1 compatibility**: PASS. T1 is ADOPT_CANDIDATE-eligible if it passes all H-D1 gates.
- **Rationale**: T1 isolates the **barrier-vs-no-barrier** lever from the asymmetry / time-weighting / multi-horizon levers.

### 4.2 T2 — time-weighted realised PnL

- **Definition**: `pnl_tw(t) = realised_pnl_barrier(t) × (1 - hold_bars / H_M1)` where `realised_pnl_barrier` is the inherited 27.0d triple-barrier executable PnL and `hold_bars` is the M1-bar count from signal_ts to barrier-resolution (TP / SL / TIME).
- **Decay**: linear (`(1 - hold_bars / H_M1)`); α-fixed; NO β-time decay-shape grid sweep (e.g., exponential / quadratic).
- **Fixed numerics**: H_M1 = 60; barrier multipliers K_FAV = 1.5 / K_ADV = 1.0 (unchanged from 27.0d).
- **D-1 compatibility**: PASS (inherited executable barrier PnL × deterministic scalar transform).
- **Rationale**: T2 tests whether **rewarding faster-resolving trades** lifts Sharpe.

### 4.3 T3 — multi-horizon realised PnL (absorbs R-T3)

- **Definition**: `pnl_mh(t) = pnl_barrier_H1(t) + pnl_barrier_H2(t) + pnl_barrier_H3(t)` where each `pnl_barrier_Hi` is the inherited triple-barrier executable PnL computed at horizon Hi.
- **Fixed horizons**: H1 = 30 / H2 = 60 / H3 = 120 (M1 bars). α-fixed; NO β-time horizon-set grid sweep.
- **Barrier multipliers**: K_FAV = 1.5 / K_ADV = 1.0 (unchanged across horizons).
- **D-1 compatibility**: PASS (each horizon executable; sum preserves executable semantics if all 3 horizons resolve before next signal).
- **R-T3 absorption**: T3 absorbs R-T3 carry-forward (Phase 27 §11 / PR #347 §12).
- **Rationale**: T3 tests whether **multi-horizon aggregation** lifts Sharpe by averaging out per-horizon resolution noise.

### 4.4 T4 — asymmetric K_FAV / K_ADV barrier PnL

- **Definition**: triple-barrier realised PnL with **K_FAV = 2.0 × ATR / K_ADV = 0.5 × ATR**.
- **Fixed numerics**: K_FAV = 2.0 / K_ADV = 0.5 (α-fixed; NO β-time grid sweep over alternate ratios like 1.8/0.7 or 2.5/0.4); H_M1 = 60 unchanged; ATR window unchanged.
- **D-1 compatibility**: PASS (same harness as 27.0d; different barrier multipliers).
- **Rationale**: T4 tests whether **asymmetric barrier geometry** (tighter SL; wider TP; reward favourable-side asymmetry) lifts Sharpe. K_FAV = 2.0 / K_ADV = 0.5 inverts the 27.0d baseline geometry where K_FAV > K_ADV but only by 50%.

### 4.5 Why these 4 variants exactly (closed allowlist)

The 4 variants jointly span four orthogonal target-redesign dimensions:

- **T1**: "the issue is path-dependent barrier resolution; horizon-only framing helps"
- **T2**: "the issue is that all trades are weighted equally regardless of duration; time-decay helps"
- **T3**: "the issue is per-horizon resolution noise; multi-horizon aggregation helps"
- **T4**: "the issue is barrier symmetry; favourable-side asymmetry helps"

A 5th target variant is NOT admissible at β (NG#A2-1); revival requires α memo amendment.

### 4.6 No grid sweep within a variant

- T1: H_M1 = 60 fixed; no horizon grid {30, 60, 90, 120}.
- T2: linear decay fixed; no decay-shape grid {linear, exponential, quadratic}.
- T3: horizon set {30, 60, 120} fixed; no horizon-set grid sweep.
- T4: K_FAV=2.0 / K_ADV=0.5 fixed; no ratio grid {1.8/0.7, 2.0/0.5, 2.5/0.4}.

**NG#A2-1 enforces**.

---

## 5. A2 vs A1 / A4 / A0-narrow / R-T2 / R-T3 / R7-C / S-axis (axis purity)

| Axis | What it varies | What it fixes | A2 distinction |
|---|---|---|---|
| **A2 (this sub-phase)** | target framing | feature / model / selection / loss | A2 varies target; everything else fixed |
| A1 (28.0a) | loss function | target / feature / model / selection | A2 varies target; loss fixed at Huber α=0.9 |
| A4 (28.0b) | selection rule | target / feature / model / loss | A2 varies target; selection fixed at top-q |
| A0-narrow (28.0c) | tabular topology | target / feature / selection / loss | A2 varies target; tabular topology fixed at 27.0d C-se single regressor |
| R-T2 (27.0e) | quantile family | target / feature / model / loss | A2 varies target; quantile family {5,10,20,30,40} fixed |
| R-T3 (Phase 27 carry-forward) | target-adjacent dimension | n/a | R-T3 absorbed into A2 via T3 multi-horizon variant |
| R7-C (27.0f) | regime feature class | target / model / selection / loss | A2 varies target; feature surface R7-A fixed |
| S-axis (27.0b/c/d) | score formulation | target / feature / model / selection / loss | A2 varies target; score fixed at S-E regression |

**A2 is structurally distinct on the target axis only**; every sibling axis (loss / selection / topology / quantile family / feature class / score) is held fixed at the verbatim 27.0d C-se backbone.

---

## 6. Fixed non-target axes

A2 commits to 5 invariants across all 4 target variants. Variation in any of these requires separate scope amendment.

| Axis | Fixed value | Source |
|---|---|---|
| Feature surface | **R7-A** (4 features: pair, direction, atr_at_signal_pip, spread_at_signal_pip) | Phase 28 default (PR #348 §17); R-B deferred-not-foreclosed |
| Model class | **tabular LightGBM** single regressor (27.0d C-se backbone) | Phase 28 default (PR #348 §17); A0-broad deferred-not-foreclosed |
| Selection rule | **top-q on score** with quantile family **{5, 10, 20, 30, 40}** | Phase 28 default (PR #348 §17); A4 exhausted |
| Loss function | **symmetric Huber α=0.9** | Phase 28 default (PR #348 §17); A1 exhausted |
| Sample weight | **sample_weight = 1** (uniform) | 27.0d / 28.0a / 28.0b / 28.0c verbatim |

NG#A2-1 enforces all 5 invariants.

---

## 7. Cell structure (6 cells; substantive + 1 control + per-target baseline)

| # | Cell ID | Score | Target | Selection | Purpose |
|---|---|---|---|---|---|
| 1 | **C-d1-T1** | S-E regression | T1 fixed-horizon executable close PnL (H_M1=60; no barrier) | top-q quantile family {5,10,20,30,40} | A2 T1 — horizon-only framing; D-1 PASS |
| 2 | **C-d1-T2** | S-E regression | T2 time-weighted PnL (linear decay; H_M1=60) | top-q quantile family {5,10,20,30,40} | A2 T2 — time-decay reward |
| 3 | **C-d1-T3** | S-E regression | T3 multi-horizon PnL (H={30,60,120}); absorbs R-T3 | top-q quantile family {5,10,20,30,40} | A2 T3 — multi-horizon aggregation |
| 4 | **C-d1-T4** | S-E regression | T4 asymmetric (K_FAV=2.0 / K_ADV=0.5; H_M1=60) | top-q quantile family {5,10,20,30,40} | A2 T4 — asymmetric barrier geometry |
| 5 | **C-d1-target-control** | S-E regression | inherited 27.0d triple-barrier (K_FAV=1.5 / K_ADV=1.0; H_M1=60) | top-q quantile family {5,10,20,30,40} | NG#A2-3 mandatory; target-axis null; reproduces 27.0d C-se |
| 6a-d | **C-d1-T<x>-baseline** | S-B raw P(TP)−P(SL) | per-target Tx | top-q q=5 fixed | Phase 29 §10 baseline reference per target |

**Total**: 5 quantile cells × 5 quantiles = **25 records** + 4 per-target baseline FAIL-FAST cells = **29 (cell, q) records**.

### 7.1 Per-target baseline cell structure (cells 6a-6d)

For each target Tx ∈ {T1, T2, T3, T4}, one **C-d1-Tx-baseline** cell:

- Same multiclass S-B head fitted on R7-A train (unchanged from 27.0d C-sb-baseline).
- Apply top-q (q=5) selection on S-B raw score (P(TP) − P(SL)) — same as 27.0b C-alpha0 C-sb-baseline.
- Compute realised PnL under **target Tx** (per the 4 target variant definitions in §4).
- The resulting (n_trades_Tx, Sharpe_Tx, ann_pnl_Tx) tuple is the **Phase 29 §10 baseline reference for target Tx**.

---

## 8. Phase 29 §10 baseline reference — Option 9c implementation

This is the **critical Option 9c exercise** at the Phase 29 first sub-phase (PR #348 §9).

### 8.1 Archived Phase 28 §10 reference (immutable; DIAGNOSTIC-ONLY 2nd reference)

| Metric | Value (Phase 28 §10) |
|---|---|
| n_trades (test, val-selected q*=5 on C-sb-baseline) | **34,626** |
| Sharpe (test) | **-0.1732** |
| ann_pnl (test, pip) | **-204,664.4** |
| val Sharpe | **-0.1863** |

- **Immutable**: never retroactively modified by Phase 29.
- **DIAGNOSTIC-ONLY 2nd reference** in this sub-phase eval_report — used for cross-target drift signal but NOT used for FAIL-FAST gate (target semantics changed).

### 8.2 Phase 29 §10 per-target baseline reference (FAIL-FAST gate; new)

For each target Tx ∈ {T1, T2, T3, T4}:

- The **C-d1-Tx-baseline cell value** (S-B raw + top-q q=5 + target Tx-specific realised PnL) is computed at β-eval.
- The resulting tuple `(n_trades_Tx_baseline, Sharpe_Tx_baseline, ann_pnl_Tx_baseline)` becomes the **Phase 29 §10 baseline reference for target Tx**.
- The substantive cell C-d1-Tx (S-E regression + top-q + target Tx) is compared to this per-target baseline for H-D1 H2 lift evaluation.

### 8.3 Per-target baseline FAIL-FAST tolerance (inherited from Phase 28 pattern)

| Metric | Tolerance |
|---|---|
| n_trades | exact (±0) |
| Sharpe | ±1e-4 |
| ann_pnl | ±0.5 pip |

**Inherited from PR #344 §10** (Phase 28 §10 baseline FAIL-FAST tolerance). The Phase 29 §10 per-target reference is computed at β-eval and frozen for that target; subsequent Phase 29 sub-phases that admit the same target inherit the frozen reference verbatim.

### 8.4 FAIL-FAST behavior

- If any C-d1-Tx-baseline cell fails to reproduce its own computed baseline (e.g., due to non-deterministic data load / non-deterministic multiclass fit / pipeline drift), `BaselineMismatchError` HALT.
- The FAIL-FAST gate verifies internal consistency of the Phase 29 §10 per-target baseline definition itself.

### 8.5 Archived Phase 28 §10 drift signal (DIAGNOSTIC-ONLY)

- For each target Tx, report the **drift** (`C-d1-Tx-baseline numeric` vs `archived Phase 28 §10 numeric`).
- Drift magnitude indicates how much each target variant changes the baseline numeric — informational for routing the next Phase 29 sub-phase.
- This drift is **not** a FAIL-FAST trigger; it is DIAGNOSTIC-ONLY.

---

## 9. NG#A2-* anti-collapse guards

### 9.1 NG#A2-1 — closed 4-target allowlist; fixed non-target axes; no joint admission

- Targets MUST be {T1, T2, T3, T4} with α-fixed numerics (§4 + §4.6).
- 5th target variant NOT admissible at β; requires α memo amendment.
- Numeric grid sweep within a variant NOT admissible (e.g., no T1-with-horizons={30,60,90}; no T4-with-ratios={1.8/0.7, 2.5/0.4}).
- Feature surface (R7-A), model class (tabular LightGBM single regressor), selection rule (top-q on score with quantile family {5,10,20,30,40}), loss (symmetric Huber α=0.9), sample_weight=1 all fixed.
- Joint admission (A0-broad / R-B / A3) NOT admissible (Policy C single-axis default; PR #348 §7).
- DIAGNOSTIC-ONLY target variants (e.g., mid-to-mid pure return without D-1) NOT admissible in the closed allowlist; all 4 variants must be D-1 executable and ADOPT_CANDIDATE-eligible.

### 9.2 NG#A2-2 — per-target verdict required

- Each target variant {T1, T2, T3, T4} must produce its own H-D1 outcome (PASS / PARTIAL_SUPPORT / FALSIFIED_TARGET_INSUFFICIENT / PARTIAL_DRIFT_TARGET_REPLICA).
- Aggregate-only verdict (e.g., "average of 4 targets is PARTIAL_SUPPORT") NOT admissible.

### 9.3 NG#A2-3 — C-d1-target-control mandatory

- C-d1-target-control reproduces 27.0d C-se with sample_weight=1 (target-axis null + architecture-axis null + rule-axis null).
- If any C-d1-Tx ≈ C-d1-target-control within tolerance (n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5%) at the val-selected (cell\*, q\*), the variant is flagged **PARTIAL_DRIFT_TARGET_REPLICA** (§11 row 4).
- Omitting C-d1-target-control NOT admissible.
- C-d1-target-control extends the 5-phase bit-tight reproduction chain: 27.0d → 27.0f → 28.0a → 28.0b → 28.0c → **29.0a target-control** (6th anchor); drift vs 27.0d C-se is DIAGNOSTIC-ONLY WARN per Phase 29 §15.

---

## 10. H-D1 4-outcome ladder per target (precedence row 4 > 1 > 2 > 3)

Inherited from PR #344 §12.3 / PR #341 §10.2 pattern; PARTIAL_DRIFT_TARGET_REPLICA checked first per NG#A2-3.

| Row | Outcome | Per-target condition |
|---|---|---|
| **4** | **PARTIAL_DRIFT_TARGET_REPLICA** (checked first) | C-d1-Tx ≈ C-d1-target-control (val-selected q\*) within tolerance (n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5 %) — target had zero effect on monetization vs inherited triple-barrier target |
| **1** | **PASS** | All four H-D1 conditions: val Sharpe lift ≥ +0.05 vs C-d1-Tx-baseline (Phase 29 §10 per-target reference) AND H1m ≥ +0.30 AND trade count ≥ 20,000 AND per-target baseline reproduction FAIL-FAST PASS |
| **2** | **PARTIAL_SUPPORT** | val Sharpe lift ∈ [+0.02, +0.05); others intact |
| **3** | **FALSIFIED_TARGET_INSUFFICIENT** (default) | val Sharpe lift < +0.02 OR other H-D1 conditions fail |

---

## 11. Aggregate verdict mapping

- **any AR PASS** → **SPLIT_VERDICT_ROUTE_TO_REVIEW** (route to Phase 29 post-29.0a routing review; PROMISING_BUT_NEEDS_OOS candidate; ADOPT_CANDIDATE wall preserved).
- **0 PASS + 1+ PARTIAL_SUPPORT** → **REJECT_NON_DISCRIMINATIVE** (sub-threshold; route to post-29.0a routing review for next axis).
- **All 4 targets FALSIFIED_TARGET_INSUFFICIENT or PARTIAL_DRIFT_TARGET_REPLICA** → **REJECT_NON_DISCRIMINATIVE** + diagnostic `FALSIFIED_A2_NARROW` (A2 axis exhausted under the tested closed 4-target allowlist; alternate target framings still possible via scope amendment; **NEVER labelled `FALSIFIED_ALL_A2`**).

The FALSIFIED_A2_NARROW vs FALSIFIED_ALL_A2 distinction is load-bearing and analogous to PR #344 FALSIFIED_A0_NARROW vs FALSIFIED_ALL_A0.

---

## 12. D-1 bid/ask compatibility per target (all PASS)

| Target | D-1 status | Compatibility notes |
|---|---|---|
| **T1** fixed-horizon executable close PnL | **PASS** | Entry at signal_ts using D-1 bid/ask executable side; exit at signal_ts + H_M1=60 using D-1 bid/ask executable side; no path-dependent intermediate state; pip-denominated per pair |
| **T2** time-weighted realised PnL | **PASS** | Inherited triple-barrier executable PnL × deterministic scalar `(1 - hold_bars / H_M1)`; executable semantics preserved |
| **T3** multi-horizon realised PnL | **PASS** | Each horizon uses inherited triple-barrier executable PnL; sum preserves executable semantics (per-horizon Independent resolution within signal cone) |
| **T4** asymmetric K_FAV / K_ADV | **PASS** | Same harness as 27.0d; different barrier multipliers; executable semantics unchanged |

**All 4 target variants are D-1 executable and ADOPT_CANDIDATE-eligible.** No DIAGNOSTIC-ONLY target variants are included in the closed allowlist (NG#A2-1).

---

## 13. Sanity probe + eval pre-flight items

The β-eval will exercise these items (analogous to PR #344 §15):

| Item | Description |
|---|---|
| Item 1 | Class priors per split (train / val / test) |
| Item 2 | Per-pair TIME share on train (inherited |
| Item 3 | D-1 binding check (precompute_realised_pnl_per_row signature; barrier_pnl source bid_h/ask_l/ask_h/bid_l) |
| Item 4 | Realised-PnL distribution per class on TRAIN (DIAGNOSTIC) |
| Item 5 | R7-A new-feature NaN-rate check |
| Item 6 | R7-A positivity check on TRAIN |
| **Item 7 (NEW)** | T1 fixed-horizon resolution rate per pair (TIME-only outcome distribution; no SL/TP filter) |
| **Item 8 (NEW)** | T2 time-decay distribution per pair (hold_bars distribution; scalar factor distribution) |
| **Item 9 (NEW)** | T3 per-horizon resolution rate per pair (per-horizon TP/SL/TIME breakdown; multi-horizon aggregation sanity) |
| **Item 10 (NEW)** | T4 asymmetric barrier trigger distribution per pair (K_FAV=2.0 trigger rate; K_ADV=0.5 trigger rate) |
| NaN-PnL HALT | per-target NaN-PnL train-row count > NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD → HALT |

---

## 14. eval_report.md (25-section pattern inherited from PR #344 §15)

| § | Adaptation for A2 |
|---|---|
| 1 Executive summary | Per-target H-D1 outcomes; aggregate verdict; **FALSIFIED_A2_NARROW vs FALSIFIED_ALL_A2 distinction** if all 4 falsify |
| 2 Cells overview | 6 cells (T1/T2/T3/T4/target-control/per-target baselines) |
| 3 Row-set policy | R7-A-clean parent row-set unchanged |
| 4 Sanity probe results | Inherited items 1-6 + NEW items 7-10 (per-target distribution sanity) |
| 5 OOF diagnostic | Per-target S-E OOF (5-fold; seed=42; DIAGNOSTIC-ONLY) |
| 6 Regression diagnostic | Per-target S-E |
| 7 Per-cell quantile family | 5 quantile cells × 5 quantiles = 25 records |
| 8 Val-selection per cell | Per-cell val-selected (cell\*, q\*) |
| 9 Cross-cell aggregate | Per Phase 28 cross-cell verdict template |
| 10 **Phase 29 §10 per-target baseline FAIL-FAST** | **(NEW Phase 29 pattern)**: per-target baseline reproduction; archived Phase 28 §10 DIAGNOSTIC-ONLY 2nd reference reported |
| 11 Within-eval drift | Per-target vs C-d1-target-control |
| 11b target-control vs 27.0d C-se drift | DIAGNOSTIC-ONLY WARN; **6th-phase bit-tight reproduction** extends chain 27.0d → 27.0f → 28.0a → 28.0b → 28.0c → 29.0a target-control |
| 12 Feature importance per target regressor | Per-target `feature_importances_` |
| 13 H-D1 outcome row binding per target | Per-target 4-outcome ladder + FALSIFIED_A2_NARROW distinction language |
| 14 Trade-count budget audit | Per-target |
| 15 Pair concentration | Per-target (val-selected) |
| 16 Direction balance | Per-target |
| 17 Per-pair Sharpe contribution | Per-target (DIAGNOSTIC-ONLY) |
| 18 Top-tail regime audit | Per-target on `spread_at_signal_pip` only (R7-C features NOT computed; out of scope) |
| 19 R7-A NaN check | Inherited |
| 20 Realised PnL distribution per target | Per-target distribution on TRAIN (DIAGNOSTIC) |
| 21 Predicted PnL distribution per target | Per-target S-E predicted distribution (train / val / test) |
| 22 References | PR #344 / #347 / #348 / #349 + Phase 28 templates + binding contracts |
| 23 Caveats | A2 target framing distinction; ADOPT_CANDIDATE wall; H2 PASS = PROMISING_BUT_NEEDS_OOS only; FALSIFIED_A2_NARROW vs FALSIFIED_ALL_A2 distinction; R-T3 absorbed under T3; **all 4 targets are D-1 executable** (no T1 diagnostic-only caveat); Phase 28 §10 archived as DIAGNOSTIC-ONLY 2nd reference per Option 9c |
| 24 Cross-validation re-fits | 5-fold OOF per target (DIAGNOSTIC-ONLY) |
| 25 Sub-phase verdict snapshot | Per-target outcomes + aggregate + routing implication; Phase 29 §10 per-target baseline reference recorded |

---

## 15. Selection-overfit guard; validation-only selection; verdict ladder preservation

Inherited verbatim from PR #344 §14:

### 15.1 Layer 1 — validation-only configuration selection per cell

Val-selected (cell\*, q\*) only contributes to formal H-D1 verdict. Other (cell, q) records labelled **DIAGNOSTIC-ONLY** in eval_report; excluded from H-D1 outcome row binding.

### 15.2 Layer 2 — cross-cell aggregation

Cross-cell aggregation rule unchanged from Phase 28. Target variants aggregate alongside target-control + per-target baselines.

### 15.3 H1 / H2 / H3 / H4 ladder preservation

- **H1m** ≥ +0.30 / **H2** lift ≥ +0.05 / **H3** ≥ 20,000 / **H4 DIAGNOSTIC**.
- **ADOPT_CANDIDATE wall preserved**: H2 PASS = PROMISING_BUT_NEEDS_OOS only.
- **NG#10 / NG#11 not relaxed**.

---

## 16. Open questions deferred to β

Five open questions pre-stated at α; the β-eval implementation PR (separate later) will address them:

1. Phase 29 §10 per-target baseline numeric values (computed at β; pre-stated as `Phase 29 §10 baseline reference for target Tx` at β; α only locks the definition method).
2. Per-target D-1 compatibility verification (pre-flight at β sanity probe; T1 entry/exit price reconciliation; T3 multi-horizon resolution overlap check; T4 asymmetric trigger rate check).
3. T3 multi-horizon overlap with signal cone (does H3 = 120 push past next signal_ts? Sanity probe at β; if overlap, T3 sum semantics need clarification).
4. T2 hold_bars boundary handling (when barrier resolves exactly at H_M1, decay factor = 0; α-fixed; β verifies distribution sanity).
5. T4 ATR window inheritance (ATR window unchanged from 27.0d; β verifies per-pair ATR distribution under new K_FAV / K_ADV).

---

## 17. Binding constraints (verbatim from PR #348 §17 + PR #349 §16)

This α design memo preserves every constraint binding at PR #349 merge:

- D-1 bid/ask executable harness preserved (all 4 target variants PASS D-1)
- R7-A feature surface preserved (4 features unchanged; R-B deferred-not-foreclosed)
- Tabular LightGBM model class preserved (single regressor; A0-broad deferred-not-foreclosed)
- Top-q on score selection rule preserved (quantile family {5,10,20,30,40}; A4 exhausted)
- Symmetric Huber α=0.9 loss preserved (A1 exhausted)
- sample_weight = 1 (uniform) preserved
- Validation-only selection preserved
- Test touched once preserved
- ADOPT_CANDIDATE wall preserved
- H2 PASS = PROMISING_BUT_NEEDS_OOS only
- NG#10 / NG#11 not relaxed
- γ closure PR #279 preserved
- X-v2 OOS gating required
- Phase 22 frozen-OOS preserved
- Production v9 20-pair (Phase 9.12 tip `79ed1e8`) untouched
- Phase 28 §10 baseline numeric immutable (n=34,626 / Sharpe -0.1732 / ann_pnl -204,664.4 / val Sharpe -0.1863); never retroactively modified; inherited as DIAGNOSTIC-ONLY 2nd reference per Option 9c
- Phase 29 §10 baseline reference defined per target Tx in this α memo per Option 9c (PR #348 §9.2)
- No prior verdict modification (Phase 27 + Phase 28 sub-phase β + routing review verdicts preserved verbatim)
- MEMORY.md unchanged inside PR
- A1 exhausted (PR #338); A4 exhausted (PR #342); A0-narrow exhausted (PR #345) — all statuses preserved
- R-T1 = FALSIFIED_under_A4 (PR #342) preserved
- R-T3 absorbed into A2 frame via T3 multi-horizon variant; R-T3 standalone elevation NOT admissible
- A0-broad / R-B / A3 deferred-not-foreclosed (admissible at Phase 29 per Scope III; not exercised by this A2 α)
- Joint admission NOT exercised (Policy C single-axis default; PR #348 §7)
- Phase 27/28 inertia routes NOT admissible (PR #348 §11)
- No A0-broad / R-B / A3 design / implementation in this PR
- No scope amendment in this PR
- No β-eval in this PR
- No production change in this PR
- No auto-route after merge
- This PR is doc-only

---

## 18. What this PR is NOT (consolidated; non-duplicated)

- ❌ Phase 29.0a-β eval implementation (separate later PR; recommended path: `scripts/stage29_0a_a2_target_redesign_eval.py` + `tests/unit/test_stage29_0a_a2_target_redesign_eval.py` + `artifacts/stage29_0a/eval_report.md`)
- ❌ A0-broad / R-B / A3 design memo (separate later PR if elevated at Phase 29 post-29.0a routing review)
- ❌ Joint sub-phase α (Policy C single-axis default; no joint admission)
- ❌ Scope amendment (none required if all decisions stay within Phase 29 kickoff Scope III + Policy C + Option 9c)
- ❌ β-eval implementation (no script / tests / artifacts in this PR)
- ❌ Production change
- ❌ Prior verdict modification (Phase 27 + Phase 28 verdicts preserved verbatim)
- ❌ Phase 28 §10 baseline numeric modification (immutable; archived)
- ❌ T1 D-1 amendment (T1 is fully D-1 executable; no amendment required)
- ❌ ADOPT_CANDIDATE wall / NG#10 / NG#11 / γ / X-v2 / Phase 22 frozen-OOS relaxation
- ❌ DIAGNOSTIC-ONLY target variants in the closed allowlist (all 4 variants formal-eval admissible)
- ❌ 5th target variant at β (NG#A2-1)
- ❌ Numeric grid sweep within a variant at β (NG#A2-1)
- ❌ Auto-route to Phase 29.0a-β after merge
- ❌ MEMORY.md edit inside PR

---

## 19. References

### Phase 29 PRs

- **PR #348** — Phase 29 kickoff memo (Scope III / Policy C / Option 9c)
- **PR #349** — Phase 29 first-mover routing review (Path 2 A2 PRIMARY)
- **This PR** — Phase 29.0a-α A2 target redesign design memo

### Phase 28 templates

- **PR #335** — Phase 28 kickoff memo
- **PR #337 / #338** — Phase 28.0a-α / β A1 (closed-loss-allowlist pattern)
- **PR #341 / #342** — Phase 28.0b-α / β A4 (closed-rule-allowlist pattern; R-T1 absorption template)
- **PR #344 / #345** — Phase 28.0c-α / β A0-narrow (closed-architecture-allowlist pattern; FALSIFIED_A0_NARROW distinction template)
- **PR #347** — Phase 28 closure memo

### Phase 27 inheritance / template

- **PR #325** — Phase 27.0d-β S-E regression (score backbone source; 27.0d C-se cell reproduced as C-d1-target-control)
- **PR #334** — Phase 27 closure memo (R-T3 carry-forward source)

### Binding contracts

- **PR #279** — γ closure (production behavior contract; preserved)
- **Phase 22 frozen-OOS contract** (preserved)
- **X-v2 OOS gating** (required for any future production deployment)
- **Phase 9.12 production v9 closure tip `79ed1e8`** (production v9 20-pair; untouched throughout Phase 27, Phase 28, and Phase 29)

---

*End of `docs/design/phase29_0a_alpha_a2_target_redesign_design_memo.md`.*
