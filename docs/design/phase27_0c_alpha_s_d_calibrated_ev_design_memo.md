# Phase 27.0c-α — S-D Calibrated EV Design Memo

**Type**: doc-only design memo
**Status**: tier-promotes S-D *admissible-but-deferred* → *formal at 27.0c-β*; does NOT trigger any 27.0c-β implementation
**Branch**: `research/phase27-0c-alpha-s-d-calibrated-ev-design-memo`
**Base**: master @ 94bd770 (post-PR #319 / post-27.0b routing review merge)
**Pattern**: analogous to PR #308 (26.0c-α L-1) and PR #317 (27.0b-α S-C TIME) design memos
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the **canonical S-D definition** under Phase 27 kickoff §5 *admissible-but-deferred* tier. On merge, S-D's tier is lifted to *formal at sub-phase 27.0c-β*, meaning a future 27.0c-β eval PR may evaluate S-D under the policies bound here without further scope amendment. It does NOT by itself authorise the 27.0c-β eval implementation — that requires a separate later user instruction.*

Same approval-then-defer pattern as PR #308 (26.0c-α), PR #312 (26.0d-α), PR #317 (27.0b-α).

This PR is doc-only. No `src/`, `scripts/`, `tests/`, `artifacts/`, `.gitignore`, or `MEMORY.md` is touched.

---

## 1. Why 27.0c-α exists

The post-27.0b routing review (PR #319, master 94bd770) §4 enumerated 5 routing options after 27.0b-β's three-way picture (REJECT + Spearman↑ + Sharpe↓). The user explicitly selected **R-A — S-D calibrated EV** as the next move, with the routing rationale (verbatim):

> *27.0b S-C TIME penaltyでは、test Spearmanはα増加で改善したが、test Sharpeは単調悪化した。つまり単純なclass probability scoreではranking metricとrealised PnLがズレている。R7-B/R7-C feature wideningも候補だが、先にS-DでChannel Bを直接検証する方が小さい差分で済む。S-Dは class probability に class-conditional realised PnL expectation を組み込むため、score-ranking monetisationのズレを直接検証できる。*

R-A targets the **H-B3 hypothesis** from post-27.0b §3.4 (structural mis-alignment of multiclass head with realised PnL). H-B1 (P(TIME) as regime proxy) and H-B2 (R7-A too narrow) remain non-falsified; the R-B / R-C / R-D routes are **not foreclosed** by R-A. If S-D produces REJECT, R-B / R-C / R-D / R-E remain available at the post-27.0c routing review.

**27.0c-α scope is narrow**: define S-D so 27.0c-β can evaluate it without further design ambiguity. No scope amendment is requested. No new feature family is admitted. No model-class change is proposed.

---

## 2. Inheritance from 27.0b / 26.0d / kickoff (binding artifacts carried forward)

The following are FIXED for 27.0c-β and CANNOT be relaxed by this design memo:

| Artifact | Source | Inheritance status |
|---|---|---|
| R7-A 4-feature allowlist (`pair`, `direction`, `atr_at_signal_pip`, `spread_at_signal_pip`) | PR #311 / #313 | FIXED |
| L-1 ternary label (TP / SL / TIME from triple-barrier) | PR #309 / #313 | FIXED |
| LightGBM multiclass head config | PR #313 (26.0d) | FIXED |
| `_compute_realised_barrier_pnl` (bid/ask executable harness) | inherited | FIXED — D-1 binding (§4) |
| 70/15/15 chronological split | inherited | FIXED |
| Quantile-of-val 5 / 10 / 20 / 30 / 40 % cutoff family | inherited | FIXED |
| Validation-only selection / test set touched once | inherited | FIXED |
| Verdict ladder H1-weak / H1-meaningful / H2 / H3 / H4 thresholds (0.05 / 0.10 / Sharpe ≥0.082 ∧ ann_pnl ≥180 / >−0.192 / ≥0) | inherited | FIXED |
| Cross-cell verdict aggregation (26.0c-α §7.2) | inherited | FIXED |
| ADOPT_CANDIDATE 8-gate A0–A5 SEPARATE-PR wall | inherited | FIXED |
| Single model fit binding (D10 from 27.0b-α) | inherited, **amended** | AMENDED — see §7 |

D10 amendment (§7): "single model fit" means **one** multiclass-head fit + **one** isotonic-calibrator fit + **one** conditional-PnL-estimator fit; all three artifacts are shared across both cells defined in §7. No re-fit per cell.

---

## 3. S-D score definition

### 3.1 Authoritative form

For each row in val / test scoring:

```
S-D(row) = P_cal(TP | row) · Ê[PnL | TP]
        + P_cal(SL | row) · Ê[PnL | SL]
        + P_cal(TIME | row) · Ê[PnL | TIME]
```

Where:
- `P_cal(· | row)` is the **calibrated** multiclass class probability (calibration policy = §5; per-row sum-to-1 renormalised)
- `Ê[PnL | class]` is the **constant per-class conditional-PnL estimator** for class ∈ {TP, SL, TIME} (estimation policy = §4)
- "PnL" throughout = inherited `_compute_realised_barrier_pnl` (D-1 bid/ask executable)

### 3.2 Algebraic distinction from S-A / S-B / S-C

| Score | Form | PnL-weighted? | TIME-aware? |
|---|---|---|---|
| S-A | `P(TP)` | No | No |
| S-B | `P(TP) - P(SL)` | No (treats TP/SL ±1 unweighted) | No (TIME implicit only) |
| S-C(α) | `P(TP) - P(SL) - α·P(TIME)` | No | Yes (explicit, unweighted) |
| **S-D** | `Σ_c P_cal(c | row) · Ê[PnL | c]` | **Yes (by class-conditional realised PnL)** | Yes (TIME term included with sign of Ê[PnL\|TIME]) |

S-D **is** the row-level expected realised PnL under the calibrated multiclass posterior, integrated over class. If the multiclass head and the constant-per-class estimator are jointly well-specified for the realised barrier PnL, then S-D ranking = realised PnL ranking up to noise. This is the direct test of H-B3.

### 3.3 Behaviour at the algebraic boundaries

- **If isotonic calibration is monotone-trivial per class** (i.e., the raw multiclass head is already well-calibrated for that class), then P_cal ≡ P for that class, and S-D collapses to a constant-shifted S-B-like form on that class's contribution. This is an **expected** outcome under H-B3 if the head is already well-calibrated; it is NOT a falsification of S-D.
- **If Ê[PnL | TP] > 0**, **Ê[PnL | SL] < 0**, **Ê[PnL | TIME] ≈ 0** (the prior-expected pattern), then S-D ranking approximates a PnL-magnitude-weighted version of S-B. Deviations from this pattern (e.g., Ê[PnL | TIME] significantly negative) directly inform whether TIME contributes monetisation drag.
- The constant-per-class estimator is the **minimal** PnL-weighting structure that still tests H-B3; richer per-row regressors are deferred per D-U9 (§7).

---

## 4. Per-class conditional-PnL estimation policy

### 4.1 D-U1 — Estimation method: constant per-class

Three scalars are fit and frozen:
- Ê[PnL | TP] = train-set mean realised PnL over rows with realised label = TP (across the train OOF folds)
- Ê[PnL | SL] = same with realised label = SL
- Ê[PnL | TIME] = same with realised label = TIME

These three scalars are computed once, reused for all val / test scoring. No per-pair / per-feature-bin / per-class-regressor variants are admitted in 27.0c-β (deferred per D-U9 to a possible future 27.0d-α S-D variant).

### 4.2 D-U2 — Estimation data boundary: train-only

Val and test data are NEVER used to fit Ê[PnL | class]. Any deviation is an NG#10 violation (§13).

### 4.3 D-U3 — OOF protocol: 5-fold OOF on train, refit-on-full-train for production

The 5-fold OOF assignment is **shared** between:
- the multiclass-head calibration fit (§5)
- the conditional-PnL estimator fit (this section)

Procedure (binding):
1. Partition train into 5 folds by row index (deterministic seed; same folds reused across artifacts and reproducible across runs)
2. For each fold f ∈ {0, 1, 2, 3, 4}:
   - Fit a "fold-f" multiclass head on the other 4 folds
   - Predict on fold f → OOF probabilities
   - On fold f, group rows by realised label class and compute per-class realised PnL means
3. The **OOF conditional-PnL estimator** = the per-class realised PnL mean across all OOF rows (i.e., across all 5 folds aggregated)
4. The **production conditional-PnL estimator** = the same per-class realised PnL means recomputed on **full train** rows grouped by realised label class

The production estimator (step 4) is the one used for S-D scoring on val and test. The OOF estimator (step 3) exists only for the calibration step (§5) and as a diagnostic comparison (its 3 scalars should be close to step 4's 3 scalars; large divergence is a fitting-pathology flag).

### 4.4 D-U4 — PnL definition for estimator: inherited bid/ask executable harness

`Ê[PnL | class]` is computed on **realised barrier PnL** from `_compute_realised_barrier_pnl` (D-1 binding). Mid-to-mid PnL is NOT admitted for estimator fitting under any circumstance.

Rationale: S-D's purpose is to test whether **PnL-weighted** scoring fixes the wrong-direction Sharpe observed in 27.0b. If the estimator's PnL definition diverges from the formal-verdict PnL definition, S-D would be testing the wrong question (mid-to-mid alignment, not executable alignment).

---

## 5. Multiclass-head calibration policy

### 5.1 D-U5 — Calibration method: isotonic regression per class + per-row sum-to-1

For each class c ∈ {TP, SL, TIME}:
- Fit a one-vs-rest isotonic regression `g_c: [0, 1] → [0, 1]` mapping raw P(c | row) → calibrated P̃_c(row), using OOF predictions on train (§4.3 fold assignments)
- The isotonic map is monotone non-decreasing; it absorbs class-conditional miscalibration without forcing a parametric shape

After fitting all three `g_c`, calibrated probabilities are renormalised per-row to sum to 1:

```
P_cal(c | row) = P̃_c(row) / Σ_{c'} P̃_{c'}(row)
```

This per-row renormalisation is **required** so S-D remains a proper expectation under a probability distribution on {TP, SL, TIME}.

### 5.2 D-U6 — Calibration data boundary: train-internal OOF

Isotonic maps are fit on train OOF predictions (§4.3 step 2 fold-f predictions, aggregated across all 5 folds). Val is NEVER used to fit any isotonic map. **Val calibration is prohibited** under this binding; doing so would leak the cutoff-selection target into the probabilities being thresholded — a textbook selection-overfit (§13).

### 5.3 D-U7 — Calibration application: train-end

After the multiclass head is refit on full train (step 4 in §4.3), its predictions on val and test are transformed by the **OOF-fitted** isotonic maps (per class) and per-row renormalised. The isotonic maps are NOT refit on full train; they are fit once, on OOF, and frozen.

This means:
- Full-train refit affects raw P(c | row) only
- Isotonic maps stay anchored to OOF data → calibration cannot leak val/test information
- Per-row sum-to-1 happens at inference time per row

---

## 6. Selection-overfit guard

Three layers; each closes one specific leak vector.

### 6.1 Estimator-fitting layer
Ê[PnL | class] uses **train-only** rows grouped by **realised label class**; OOF assignment is symmetric (§4.3). Val rows are never touched. Result: the estimator constants Ê[PnL | class] are independent of val data.

### 6.2 Calibration layer
Isotonic maps fit on **train-internal OOF**; val never enters calibration fitting (§5.2). Result: P_cal(· | val_row) is a deterministic transform of (raw P, OOF-fitted g_c), neither of which depends on val.

### 6.3 Selection layer
Quantile-of-val cutoff fitting is **val-only**. Test is touched once at the val-selected cutoff (cell\*, q\*). This is inherited unchanged from 27.0b-α / 26.0d-α.

### 6.4 Joint property
Together, layers 6.1–6.3 ensure: the only way val data influences the final test verdict is through cutoff selection on a fixed score function. The score function itself (S-D) is val-independent. This is the binding S-D property that distinguishes 27.0c-β from a naive "fit everything on train+val" pipeline.

---

## 7. Cell definition + sweep policy

### 7.1 D-U8 — Two formal cells

| Cell ID | Score | Purpose |
|---|---|---|
| **C-sd** | S-D calibrated EV (§3.1) | the substantive cell — tests H-B3 |
| **C-sb-baseline** | S-B = P(TP) - P(SL) on the **same** multiclass head (uncalibrated; same as 27.0b α=0.0) | inheritance-chain sanity check — must reproduce 27.0b C-alpha0 / R6-new-A C02 |

C-sb-baseline uses the **same raw multiclass head** as C-sd (same train-set, same fold structure, same model config). The only difference is the score function: C-sb-baseline uses the raw `P(TP) - P(SL)` from the refit-on-full-train head; C-sd uses S-D from calibrated probabilities × constant estimator. By construction, C-sb-baseline's val/test outcome must match 27.0b C-alpha0 within tolerances.

### 7.2 Sweep grid

- 2 cells × 5 quantiles = 10 (cell, q) pairs
- quantile family: 5 / 10 / 20 / 30 / 40 % of val (inherited from 27.0b-α)
- per-cell val-selection: the (q*) that maximises val_sharpe per the inherited rule
- cross-cell aggregation: per 26.0c-α §7.2 (agree → single verdict; disagree → split, no auto-resolution)

### 7.3 BaselineMismatchError HALT

If C-sb-baseline's val-selected (q\*) produces test outcome that deviates from 27.0b C-alpha0 baseline beyond tolerance, the 27.0c-β eval HALTs with `BaselineMismatchError`. Tolerances inherited verbatim from 27.0b-α §12.2:
- `n_trades`: **exact match required**
- `Sharpe`: |delta| ≤ 1e-4
- `ann_pnl`: |delta| ≤ 0.5

Reference values from 27.0b-β PR #318 §10:
- C-alpha0 val-selected q*=5 %
- test: n_trades = 34,626; Sharpe = -0.1732; ann_pnl = -204,664.4

These three numbers are the binding inheritance-chain check.

### 7.4 D-U9 — No within-27.0c-β estimation-method sweep

Only one S-D pipeline is evaluated in 27.0c-β (constant-per-class estimator + isotonic-per-class calibration). Per-pair, per-feature-bin, and per-class-regressor estimator variants are **deferred** to a potential future 27.0d-α S-D variant **only if S-D produces NO-ADOPT in 27.0c-β**. This keeps 27.0c-β scope minimal and avoids method × quantile combinatorial selection-overfit.

### 7.5 D10 amendment — single model fit (3-artifact form)

"Single model fit" in 27.0c-β means:
- **one** multiclass-head refit on full train (after OOF folds for calibration / estimator)
- **one** triple of isotonic maps (g_TP, g_SL, g_TIME) frozen from OOF
- **one** triple of conditional-PnL constants (Ê[PnL | TP], Ê[PnL | SL], Ê[PnL | TIME]) frozen from full-train

All three artifacts are shared across both cells. C-sd uses (head + isotonic + constants); C-sb-baseline uses (head only). No re-fit per cell.

---

## 8. Verdict tree (inherited unchanged)

Inherited from 26.0c-α / 26.0d-α / 27.0b-α verbatim:
- H1-weak: Spearman > 0.05
- H1-meaningful: Spearman ≥ 0.10
- H2: Sharpe ≥ 0.082 AND ann_pnl ≥ 180
- H3: Sharpe > -0.192
- H4: Sharpe ≥ 0
- Cross-cell aggregation per 26.0c-α §7.2 (agree → single; disagree → split, no auto-resolution)
- H2 PASS branch → **PROMISING_BUT_NEEDS_OOS only**
- ADOPT_CANDIDATE requires a SEPARATE A0-A5 8-gate PR
- No production pre-approval under any 27.0c-β outcome
- NG#10 / NG#11 not relaxed

---

## 9. Mandatory clauses (1–5 verbatim from Phase 26 closure / kickoff; clause 6 = Phase 27 kickoff §8 verbatim)

Clauses 1–5 inherited verbatim:

1. **Phase framing.** ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.
2. **Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison / classification-quality / feature-importance / per-pair-Sharpe-contribution columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them. *[27.0c extends: conditional-PnL estimator constants and calibration reliability diagrams are diagnostic-only]*
3. **γ closure preservation.** Phase 24 γ hard-close (PR #279) is unmodified.
4. **Production-readiness preservation.** X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure tip 79ed1e8) remains untouched. Phase 22 frozen-OOS contract remains required for any ADOPT_CANDIDATE → production transition.
5. **NG#10 / NG#11 not relaxed.**

**Clause 6 (NEW for Phase 27, verbatim from kickoff §8 — drift prevention per D-U10)**:

> *6. Phase 27 scope. Phase 27's primary axes are (a) feature widening beyond the Phase 26 R6-new-A 2-feature allowlist via per-family closed allowlists and (b) score-objective redesign beyond P(TP) / P(TP)-P(SL). Phase 27 is NOT a Phase 25 feature-axis sweep revival. R7-A (inherited from PR #311) is admissible at kickoff; R7-B / R7-C each require a SEPARATE Phase 27 scope-amendment PR; R7-D and R7-Other are NOT admissible under any Phase 27 scope amendment currently on the table. Score-objectives S-A / S-B / S-C are admissible at kickoff for formal evaluation. S-D (calibrated EV) is admissible in principle but deferred — it requires its own design memo specifying per-class conditional-PnL estimation, calibration policy, and selection-overfit handling before any formal eval. S-E (regression-on-realised-PnL) requires a SEPARATE scope-amendment PR (model-class change). S-Other is NOT admissible. Phase 26 deferred-not-foreclosed items (L-4 / R6-new-B / R6-new-C / Phase 25 F4 / F6 / F5-d / F5-e) are NOT subsumed by Phase 27; they remain under their original phase semantics.*

This design memo IS the kickoff §5 / clause 6 "own design memo" required for S-D's tier promotion. On merge, S-D becomes *formal at sub-phase 27.0c-β*.

---

## 10. Sanity probe (inherited + S-D extensions)

Inherited from 26.0c-α §10 / 27.0b-α §11:
- Class-share probe (TP / SL / TIME row counts on train)
- P(TIME) distribution diagnostic on val and test (report-only)
- pair / row-drop diagnostics
- positivity check on label encoding

NEW for S-D (DIAGNOSTIC-ONLY; not in formal verdict):
- **Conditional-PnL estimator constants disclosure**: print the 3 frozen scalars (Ê[PnL | TP], Ê[PnL | SL], Ê[PnL | TIME]) and their OOF vs full-train delta
- **Calibration-map summary per class**: isotonic breakpoint count + mean pre-vs-post-calibration probability shift
- **OOF-vs-full-train estimator divergence flag**: if |OOF Ê - full-train Ê| / |full-train Ê| > 10 % on any class, raise a fitting-pathology warning (does NOT halt; reported only)
- **S-D distribution diagnostic on train / val / test**: quantiles 5 / 25 / 50 / 75 / 95 %

---

## 11. Eval report (27.0c-β) mandatory sections

The 27.0c-β eval_report.md MUST contain (re-stated here so 27.0c-β inherits unambiguously):

1. Mandatory clauses 1–6 verbatim (per §9)
2. D-1 binding restated (formal PnL = bid/ask executable harness)
3. R7-A feature set restated (FIXED)
4. S-D + S-B-baseline cell definitions (per §7.1)
5. Sanity probe (incl. estimator constants + calibration diagnostic + S-D distribution; per §10)
6. Pre-flight diagnostics + row-drop policy + split dates
7. All formal cells primary table (val + test for both cells)
8. Val-selected cell\* + q\* — FORMAL verdict source
9. Aggregate H1 / H2 / H3 / H4 outcome + verdict
10. Cross-cell verdict aggregation (per 26.0c-α §7.2)
11. **MANDATORY** three-column baseline comparison vs:
    - 27.0b C-alpha0 / S-B baseline (n_trades 34,626 / Sharpe -0.1732 / ann_pnl -204,664.4)
    - 26.0d C02 / R6-new-A (n_trades 34,626 / Sharpe -0.1732 / ann_pnl -204,664.4)
    - 26.0c C02 / L-1 (n_trades 42,150 / Sharpe -0.2232 / ann_pnl -237,310.8)
12. **MANDATORY** C-sb-baseline α=0.0 / S-B sanity-check declaration (n_trades exact / Sharpe ±1e-4 / ann_pnl ±0.5 pip; HALT on mismatch per §7.3)
13. **MANDATORY** per-pair Sharpe contribution table for the val-selected cell (D4 sort: share_of_total_pnl desc). If both cells are aggregated into a split verdict, both per-pair tables MUST appear.
14. **MANDATORY** pair concentration per cell table (val_top_pair / val_top_share / test_top_pair / test_top_share)
15. Classification-quality diagnostics (AUC / Cohen κ / logloss; DIAGNOSTIC-ONLY)
16. Feature importance (4-bucket; DIAGNOSTIC-ONLY)
17. **NEW for 27.0c**: S-D score distribution diagnostic (train / val / test quantiles; DIAGNOSTIC-ONLY)
18. **NEW for 27.0c**: calibration reliability diagram per class (pre-vs-post-isotonic; DIAGNOSTIC-ONLY)
19. **NEW for 27.0c**: conditional-PnL estimator constants table (Ê[PnL | c] with OOF vs full-train side-by-side; DIAGNOSTIC-ONLY)
20. Multiple-testing caveat (2 cells × 5 quantiles = 10 pairs; PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE remain hypothesis-generating)
21. Verdict statement

---

## 12. 27.0c-β implementation contract (high-level only; no code here)

The 27.0c-β implementation PR (separate later instruction) will:

- Author `scripts/stage27_0c_s_d_calibrated_ev_eval.py` inheriting from `scripts/stage27_0b_s_c_time_penalty_eval.py`
- Author `tests/unit/test_stage27_0c_s_d_calibrated_ev_eval.py`
- Implement the 5-fold OOF protocol on train, with shared fold assignment between calibration and estimator fitting
- Fit and freeze: one multiclass-head (full-train refit) + three isotonic maps (OOF-fitted) + three conditional-PnL constants (full-train)
- Materialise both cells (C-sd, C-sb-baseline) from cached probs (D10 amendment from §7.5)
- BaselineMismatchError HALT on C-sb-baseline non-match (§7.3)
- Emit `artifacts/stage27_0c/eval_report.md` with all 21 sections from §11
- Add `.gitignore` entries for `artifacts/stage27_0c/` intermediates analogous to `artifacts/stage27_0b/` entries
- Run sanity probe FIRST, then full sweep — same staging as 27.0b-β
- Lint via `python tools/lint/run_custom_checks.py` + `ruff check` + `ruff format --check` before push
- CI green before merge

None of the above is authorised by THIS PR. It is documented here so 27.0c-β has an unambiguous contract.

---

## 13. Selection-overfit handling — explicit binding

> *S-D's three trainable artifacts (multiclass head P, isotonic calibrators per class, conditional-PnL constants Ê[PnL | class]) are ALL fit on train-only data, using a single 5-fold OOF assignment that is reused across all three artifacts. Val data is used ONLY for cutoff selection (quantile-of-val q\* per cell). Test data is touched exactly once at the val-selected (cell\*, q\*). Any deviation from this is a NG#10 violation.*

This is the central S-D design risk and the binding wording. The three-layer guard (§6) closes:
- estimator leak vector (§6.1)
- calibration leak vector (§6.2)
- selection leak vector (§6.3)

If 27.0c-β implementation cannot satisfy any of the three layers (e.g., a library forces val-touching during isotonic fitting), the implementation MUST HALT and route back to design-memo amendment, not work around the binding.

---

## 14. What this PR will NOT do

- ❌ Authorise 27.0c-β eval implementation (separate later user instruction)
- ❌ Authorise any 27.0d / 27.0e / 27.0f sub-phase or any joint sub-phase
- ❌ Authorise any R7-B / R7-C scope amendment (R-B / R-C / R-D paths remain available but require separate scope-amendment PRs)
- ❌ Authorise any S-E (regression-on-realised-PnL) work — would require separate scope-amendment PR (model-class change)
- ❌ Authorise any S-Other (quantile / ordinal / learn-to-rank) work — NOT admissible per kickoff §5
- ❌ Authorise per-pair / per-feature-bin / per-class-regressor estimator variants (deferred per D-U9)
- ❌ Modify Phase 27 scope per kickoff §8 (other than tier-promoting S-D from *admissible-but-deferred* to *formal at 27.0c-β*, which is the explicit purpose authorised in kickoff §5)
- ❌ Relax the ADOPT_CANDIDATE 8-gate A0-A5 wall
- ❌ Relax NG#10 / NG#11
- ❌ Modify γ closure (PR #279) / X-v2 OOS gating / Phase 22 frozen-OOS contract / production v9 20-pair tip 79ed1e8
- ❌ Pre-approve any production deployment under any 27.0c-β outcome
- ❌ Modify any prior verdict (Phase 25 / Phase 26 / Phase 27.0b-β / post-27.0b routing)
- ❌ Touch `src/`, `scripts/`, `tests/`, `artifacts/`, `.gitignore`, or `MEMORY.md`
- ❌ Auto-route to 27.0c-β implementation after merge

---

## 15. Sign-off

Phase 27 produces its second design memo (after 27.0b-α / PR #317). S-D tier moves from *admissible-but-deferred* (kickoff §5) → *formal at 27.0c-β* on merge. The 27.0c-β implementation PR is triggered by a separate later user instruction. No auto-route.

**This PR stops here.**
