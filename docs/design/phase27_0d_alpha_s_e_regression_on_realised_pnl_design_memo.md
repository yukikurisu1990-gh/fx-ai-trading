# Phase 27.0d-α — S-E Regression-on-Realised-PnL Design Memo

**Type**: doc-only design memo
**Status**: tier-promotes S-E *admissible at 27.0d-α design memo* (PR #323) → *formal at 27.0d-β*; does NOT trigger 27.0d-β implementation
**Branch**: `research/phase27-0d-alpha-s-e-regression-design-memo`
**Base**: master @ 8171458 (post-PR #323 / Phase 27 S-E scope amendment merge)
**Pattern**: analogous to PR #312 (26.0d-α R6-new-A), PR #317 (27.0b-α S-C TIME), PR #320 (27.0c-α S-D) design memos
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this PR as the **canonical S-E implementation contract** under PR #323 (Phase 27 S-E scope amendment) / clause 6. On merge, S-E moves from "admissible at 27.0d-α design memo" → "formal at sub-phase 27.0d-β", meaning a future 27.0d-β eval PR may evaluate S-E under the policies bound here without further scope amendment. It does NOT by itself authorise the 27.0d-β eval implementation — that requires a separate later user instruction.*

Same approval-then-defer pattern as PR #308 / #312 / #317 / #320.

This PR is doc-only. No `src/`, `scripts/`, `tests/`, `artifacts/`, `.gitignore`, or `MEMORY.md` is touched.

---

## 1. Why 27.0d-α exists

The post-27.0c routing review (PR #322, master 2bfd948) §4 selected **R-S-E** — S-E regression-on-realised-PnL — as the next move, with the user's verbatim rationale: classification-head-derived score modifications produced the wrong-direction pattern in both 27.0b and 27.0c, so the next test leaves the classification head and targets realised PnL directly. The Phase 27 S-E scope amendment (PR #323, master 8171458) promoted S-E from "requires scope amendment" → "admissible at 27.0d-α design memo".

This design memo is the kickoff §5 / clause 6 "own design memo" required for S-E's tier promotion to formal evaluation. On merge, S-E becomes *formal at sub-phase 27.0d-β*.

**Targeted hypotheses** (from #322 §3):

- **H-B4** (direct test): label/PnL coupling miscalibration not fixable by per-class scalar weights. S-E bypasses the class-prob × class-scalar factorisation entirely by regressing on realised PnL per row.
- **H-B3** (implicit test): structural mis-alignment of multiclass head with realised PnL under R7-A. If S-E aligns under R7-A, H-B3 is falsified as R7-A-conditioned; if S-E also fails, H-B3 is reinforced and routing pivots to R-B / R-C / R-D / R-E.

**27.0d-α scope is narrow**: define S-E so 27.0d-β can evaluate it without further design ambiguity. No scope amendment is requested (PR #323 already lifted S-E to admissibility). No new feature family is admitted. No additional model-class change is proposed beyond the regressor for S-E cells.

---

## 2. Inheritance bindings (FIXED for 27.0d-β)

The following are FIXED for 27.0d-β and CANNOT be relaxed by this design memo:

| Binding | Source | Inheritance status |
|---|---|---|
| R7-A 4-feature allowlist (`pair`, `direction`, `atr_at_signal_pip`, `spread_at_signal_pip`) | PR #311 / #313 / #323 | FIXED |
| 25.0a-β path-quality dataset | inherited | FIXED |
| 70/15/15 chronological split | inherited | FIXED |
| Triple-barrier inputs (K_FAV=1.5·ATR, K_ADV=1.0·ATR, H_M1=60) | inherited | FIXED |
| `_compute_realised_barrier_pnl` (bid/ask executable harness) | D-1 binding | FIXED — both the formal-verdict PnL AND the S-E regression target |
| 8-gate metrics + `gate_matrix` | inherited | FIXED |
| Verdict ladder H1/H2/H3/H4 thresholds (0.05 / 0.10 / Sharpe ≥0.082 ∧ ann_pnl ≥180 / >−0.192 / ≥0) | inherited | FIXED |
| Quantile-of-val 5/10/20/30/40 % cutoff family | inherited | FIXED |
| Validation-only cutoff selection; test touched once | inherited | FIXED |
| Cross-cell verdict aggregation (26.0c-α §7.2) | inherited | FIXED |
| ADOPT_CANDIDATE 8-gate A0–A5 SEPARATE-PR wall | inherited | FIXED |
| Pair-concentration diagnostic + per-pair Sharpe contribution diagnostic | inherited | FIXED |
| L-1 ternary class encoding (TP/SL/TIME) | inherited | PRESERVED for sanity probe + label diagnostics + C-sb-baseline; **NOT used as S-E regression target** |
| Multiclass head config (`build_pipeline_lightgbm_multiclass_widened`) | inherited from 26.0d | FIXED — used ONLY for C-sb-baseline replica cell |
| Phase 22 frozen-OOS contract | inherited | FIXED |
| Production v9 20-pair tip 79ed1e8 | inherited | UNTOUCHED |
| D10 single model fit binding | inherited, **amended** | AMENDED — see §7.5 (2-artifact form: one regressor + one multiclass head; each fit ONCE) |

---

## 3. S-E score definition

### 3.1 Authoritative form

Target (per-row regression label, computed ONCE on full train):

```
target(row) = _compute_realised_barrier_pnl(row)   # inherited bid/ask executable; D-1 binding
```

Score (per-row prediction at val/test):

```
S-E(row) = regressor.predict(row)                  # predicted realised PnL per row
```

The target is **the same value** used by the formal-verdict harness across all prior Phase 26 / Phase 27 sub-phases. There is no new harness, no new realised-PnL semantics, no mid-to-mid relaxation. Mid-to-mid PnL appears in sanity probe only (D-1 binding preserved).

### 3.2 Algebraic comparison with prior score objectives

| Score | Form | Model class | What is being predicted |
|---|---|---|---|
| S-A | `P(TP)` | multiclass | class probability |
| S-B | `P(TP) - P(SL)` | multiclass | class probability difference |
| S-C(α) | `P(TP) - P(SL) - α · P(TIME)` | multiclass | TIME-penalised difference |
| S-D | `Σ_c P_cal(c) · Ê[PnL\|c]` | multiclass + isotonic + class-scalar | class-conditional expectation of PnL |
| **S-E** | `regressor.predict(row)` | **regression** | **per-row realised PnL directly** |

S-E **bypasses the class-prob × class-scalar factorisation** that 27.0c's S-D could not align with realised PnL — this is the structural change that targets H-B4. If H-B4 holds (per-class scalar weighting is insufficient), a regressor trained directly on realised PnL should expose the alignment that S-D's factored form could not.

### 3.3 Score sign convention (D-W9)

**Higher predicted PnL = better.** Quantile-of-val selection picks the **top-(q/100)** val rows by S-E score (highest predicted PnL). The cutoff at quantile q is the score at the val (1 − q/100)-quantile. Same convention as S-A / S-B / S-C / S-D — higher score = candidate for selection.

---

## 4. LightGBMRegressor config (D-W1)

Inherited from `build_pipeline_lightgbm_multiclass_widened` shape (PR #313); only `objective`, `metric`, and the loss-related param change for regression:

| Param | Multiclass head (inherited) | Regression head (S-E) |
|---|---|---|
| objective | `multiclass` (3 classes) | **`huber`** (per D-W2) |
| metric | `multi_logloss` | **`huber`** |
| alpha (Huber breakpoint) | n/a | **`0.9`** (per D-W2) |
| n_estimators | inherited | inherited |
| learning_rate | inherited | inherited |
| max_depth | inherited | inherited |
| num_leaves | inherited | inherited |
| min_data_in_leaf | inherited | inherited |
| categorical handling (`pair`, `direction`) | inherited | inherited |
| random_state | `42` | **`42`** |
| verbose | `-1` | `-1` |

A separate helper `build_pipeline_lightgbm_regression_widened()` will be authored in 27.0d-β implementation (per §12 below), mirroring the multiclass version but with the regression objective.

---

## 5. Loss / target preprocessing (D-W2 + D-W3)

### 5.1 D-W2 — Loss / objective: Huber regression

```
objective = 'huber'
alpha     = 0.9              # Huber breakpoint (sklearn / LightGBM convention)
metric    = 'huber'          # training metric
```

**Rationale**: realised barrier PnL has a fat-tailed distribution (per 27.0b-β sanity-probe diagnostic § 4: TP p95 ≈ +21 pips; SL p5 ≈ −12 pips). MSE would over-weight a few extreme rows; L1 (MAE) would be maximally robust but discard variance information from moderate-magnitude rows. **Huber is the standard middle-ground**: it is quadratic for residuals below `alpha` and linear above, bounding the influence of extreme rows while preserving variance information for typical rows.

Alternatives within the regression family — MSE (`objective='regression'`) / L1 (`objective='regression_l1'`) / Tweedie / Poisson — are not selected by default but remain admissible within the regression model class per PR #323. If 27.0d-β with Huber produces REJECT, a follow-up 27.0d-α-rev1 may revisit D-W2 with a different default; this PR does not pre-commit.

### 5.2 D-W3 — Target preprocessing: NONE

Raw realised PnL from `_compute_realised_barrier_pnl(row)` is used directly as the regression target. **No winsorisation, no clipping, no log-transform, no standardisation of the target.**

**Rationale**: the regression target MUST equal the value used by the formal-verdict harness (D-1 binding). Any winsorisation / clipping would distort the target away from `_compute_realised_barrier_pnl` semantics and constitute a form of D-1 leakage — the regressor would be optimising a winsorised proxy instead of the actual realised PnL the formal verdict uses. **Not admissible** under D-1 binding.

The choice to use Huber (D-W2) instead of MSE is the principled solution to fat-tailed PnL: it adapts the loss to the tail without distorting the target.

Feature standardisation (z-scoring) is permitted within the pipeline as part of the LightGBM preprocessing (analogous to multiclass head behaviour); this affects feature scales, not the target.

---

## 6. Train-only fitting boundary + OOF policy (D-W4)

### 6.1 Train-only fitting boundary (verbatim binding)

> *S-E's regressor is fit on train-only data. The multiclass head used by C-sb-baseline is also fit on train-only data. Val data is used ONLY for cutoff selection (quantile-of-val q\* per cell). Test data is touched exactly once at the val-selected (cell\*, q\*). 5-fold OOF (if computed) is DIAGNOSTIC-ONLY and does NOT enter formal verdict routing. Any deviation is a NG#10 violation.*

### 6.2 OOF protocol (D-W4)

Decision: **NO 5-fold OOF for formal scoring; 5-fold OOF retained as DIAGNOSTIC-ONLY**.

Rationale:

- Unlike S-D, S-E does NOT require a post-fit calibration step. The regressor's output IS the score by D-1 binding (predicted realised PnL = score directly)
- A single train-fit suffices for production scoring on val / test
- 5-fold OOF computation (5 fold-fits ≈ 5× training time) is non-trivial; default is to skip it for formal scoring
- 5-fold OOF is retained as a DIAGNOSTIC-ONLY signal: per-fold predicted-vs-realised correlation on OOF rows. Provides a generalisation-check that does not enter formal verdict routing (clause 2 extension; see §10 item 9)

Fold seed (if 5-fold OOF is computed): **42** (inherited convention from 27.0c-α §4.3 / D-I1).

---

## 7. Cell structure + baseline-replica policy (D-W5 + D-W6)

### 7.1 Two formal cells (D-W5)

| Cell ID | Score | Model class | Purpose |
|---|---|---|---|
| **C-se** | `regressor.predict(row)` (S-E) | LightGBMRegressor (Huber loss) | the substantive cell — tests H-B4 directly |
| **C-sb-baseline** | raw `P(TP) - P(SL)` | LightGBM multiclass classifier | inheritance-chain sanity check — must reproduce 27.0b C-alpha0 / R6-new-A C02 baseline |

### 7.2 D-W6 — Baseline-replica head mechanics

Because C-se uses a regressor and C-sb-baseline uses a multiclass classifier, the two cells **cannot share a head** (different model classes). C-sb-baseline therefore requires a **separately-fit multiclass head** on the same train data.

Procedure (binding):

1. Fit a regression pipeline (`build_pipeline_lightgbm_regression_widened`) on full train → produces the production S-E head
2. Fit a multiclass pipeline (`build_pipeline_lightgbm_multiclass_widened`) on the same full train data → produces the C-sb-baseline head
3. Score val + test with both heads; C-se uses regressor predictions, C-sb-baseline uses raw `P(TP) - P(SL)`

Cost: ~30s additional model fit per 27.0d-β run (multiclass head fit, based on 27.0c-β precedent). Judged worth the BaselineMismatchError inheritance-chain guarantee.

**Determinism check**: with `random_state=42` and same train data and same LightGBM config, the multiclass head fit in 27.0d-β must produce row-for-row probabilities matching the 27.0b / 27.0c multiclass head outputs (LightGBM is deterministic under fixed seed + single-thread or `deterministic=True`). If C-sb-baseline's val-selected metrics drift outside tolerance, the inheritance chain has broken and BaselineMismatchError fires.

### 7.3 D-W7 — BaselineMismatchError tolerances (inherited verbatim)

C-sb-baseline must reproduce 27.0b C-alpha0 / R6-new-A C02 baseline within inherited tolerances:

| Metric | Reference value (PR #318 §10) | Tolerance | Inherited from |
|---|---|---|---|
| n_trades | 34,626 | exact | 27.0b-α §12.2 |
| Sharpe | -0.1732 | ±1e-4 | 27.0b-α §12.2 |
| ann_pnl | -204,664.4 | ±0.5 pip | 27.0b-α §12.2 |

HALT pattern (per D-I9 from 27.0c-α §7.3, inherited): if C-sb-baseline q*=5% test metrics deviate beyond tolerance, the 27.0d-β eval HALTs with `BaselineMismatchError` **before** C-se verdict assignment (fail-fast).

### 7.4 Sweep grid

- 2 cells × 5 quantiles = 10 (cell, q) pairs
- quantile family: 5 / 10 / 20 / 30 / 40 % of val (inherited from 27.0b-α / 26.0c-α)
- per-cell val-selection: max val_sharpe per inherited `select_cell_validation_only` rule
- cross-cell aggregation: per 26.0c-α §7.2 (agree → single; disagree → split)

### 7.5 D10 amendment for 27.0d (2-artifact form)

"Single model fit" in 27.0d-β means:

- **one** LightGBMRegressor fit on full train (production S-E head)
- **one** LightGBM multiclass head fit on full train (for C-sb-baseline only)

Both artifacts fit ONCE each; neither is re-fit per cell. The train-only realised PnL precomputation is shared across both cells (used both as the regression target for C-se and indirectly via the L-1 ternary label encoding for C-sb-baseline scoring).

### 7.6 No within-27.0d-β sweep of regression variants

Only one S-E pipeline is evaluated in 27.0d-β (LightGBMRegressor with Huber loss, R7-A features). MSE / L1 / Tweedie variants are **deferred** to a potential future 27.0d-α-rev1 design memo ONLY IF S-E with Huber produces NO-ADOPT in 27.0d-β. This keeps 27.0d-β scope minimal and avoids loss-function × quantile combinatorial selection-overfit (same rationale as 27.0c-α §7.4 / D-U9).

---

## 8. Verdict tree (inherited unchanged)

Inherited from 26.0c-α / 26.0d-α / 27.0b-α / 27.0c-α verbatim:

- H1-weak: Spearman > 0.05
- H1-meaningful: Spearman ≥ 0.10
- H2: Sharpe ≥ 0.082 AND ann_pnl ≥ 180
- H3: Sharpe > −0.192
- H4: Sharpe ≥ 0
- Cross-cell aggregation per 26.0c-α §7.2 (agree → single; disagree → split, no auto-resolution)
- H2 PASS branch → **PROMISING_BUT_NEEDS_OOS only**
- ADOPT_CANDIDATE requires a SEPARATE A0-A5 8-gate PR
- No production pre-approval under any 27.0d-β outcome
- NG#10 / NG#11 not relaxed

---

## 9. Mandatory clauses (clauses 1–5 verbatim; clause 6 = PR #323 §7 verbatim wording)

Clauses 1–5 inherited verbatim:

1. **Phase framing.** ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.
2. **Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison / classification-quality / feature-importance / per-pair-Sharpe-contribution columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them. *[27.0c extension preserved: conditional-PnL estimator constants and calibration reliability diagrams are diagnostic-only. 27.0d extends: regressor feature importance, predicted-vs-realised correlation, R², MAE, and predicted-PnL distribution are diagnostic-only.]*
3. **γ closure preservation.** Phase 24 γ hard-close (PR #279) is unmodified.
4. **Production-readiness preservation.** X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure tip 79ed1e8) remains untouched. Phase 22 frozen-OOS contract remains required for any ADOPT_CANDIDATE → production transition.
5. **NG#10 / NG#11 not relaxed.**

**Clause 6 (verbatim from PR #323 §7 — the canonical S-E-updated wording from PR #323 forward)**:

> *6. Phase 27 scope. Phase 27's primary axes are (a) feature widening beyond the Phase 26 R6-new-A 2-feature allowlist via per-family closed allowlists and (b) score-objective redesign beyond P(TP) / P(TP)-P(SL). Phase 27 is NOT a Phase 25 feature-axis sweep revival. R7-A (inherited from PR #311) is admissible at kickoff; R7-B / R7-C each require a SEPARATE Phase 27 scope-amendment PR; R7-D and R7-Other are NOT admissible under any Phase 27 scope amendment currently on the table. Score-objectives S-A / S-B / S-C are admissible at kickoff for formal evaluation. S-D (calibrated EV) was promoted from admissible-but-deferred to formal at sub-phase 27.0c-β via PR #320. **S-E (regression-on-realised-PnL) was promoted from "requires scope amendment" to "admissible at 27.0d-α design memo" via Phase 27 S-E scope-amendment PR #323. S-E uses realised barrier PnL (inherited bid/ask executable, D-1 binding) as the per-row regression target under the FIXED R7-A feature family; LightGBM regression is the default model class but the 27.0d-α design memo may specify alternatives within the regression family. S-Other (quantile regression / ordinal / learn-to-rank) remains NOT admissible. R7-D and R7-Other remain NOT admissible. R7-B / R7-C remain admissible only after their own separate scope amendments.** Phase 26 deferred-not-foreclosed items (L-4 / R6-new-B / R6-new-C / Phase 25 F4 / F6 / F5-d / F5-e) are NOT subsumed by Phase 27; they remain under their original phase semantics.*

This design memo IS the kickoff §5 / clause 6 "27.0d-α design memo" required for S-E's tier promotion to formal evaluation. On merge, S-E becomes *formal at sub-phase 27.0d-β*. The 27.0d-β eval PR will re-cite clause 6 verbatim from this PR (which is verbatim from PR #323 §7).

---

## 10. Sanity probe (inherited + S-E-specific)

Inherited from 27.0c-α §10 / 27.0b-α §11 / 26.0c-α §10:

1. Class priors per split (TP/SL/TIME) — HALT if any class < 1%
2. Per-pair TIME share — HALT if any pair > 99%
3. Realised-PnL cache basis (D-1 binding) confirmed via signature + source check
4. Mid-to-mid PnL distribution per class on train (DIAGNOSTIC-ONLY)
5. R7-A new-feature NaN rate per split — HALT if > 5%
6. R7-A positivity assertions — HALT if > 1% violation

**NEW for S-E** (DIAGNOSTIC-ONLY per clause 2 27.0d extension; not in formal verdict):

7. **Target (realised PnL) distribution on train**: mean / p5 / p25 / p50 / p75 / p95 / std / min / max — confirms target distribution is in expected fat-tailed shape
8. **Predicted PnL distribution on val/test** (post-fit): same quantiles — confirms regressor outputs are in plausible range
9. **OOF predicted-vs-realised correlation diagnostic** (5-fold OOF on train; DIAGNOSTIC-ONLY): per-fold Pearson + Spearman correlations
10. **Regressor MAE + R² on train/val/test** (DIAGNOSTIC-ONLY): not used to gate verdict
11. **Regressor feature importance** (4-bucket gain): analogous to multiclass version in 27.0c §16

Probe writes to `artifacts/stage27_0d/sanity_probe.json` + `sanity_probe_run.log`.

PASS criteria: (a) inherited HALTs (class share / TIME share / NaN / positivity); (b) target distribution within expected pip range; (c) predicted-PnL distribution finite (no NaN / Inf). NEW items 7–11 are diagnostic; do NOT HALT.

---

## 11. Eval report (27.0d-β) mandatory sections

The 27.0d-β eval_report.md MUST contain (re-stated here so 27.0d-β inherits unambiguously):

1. Mandatory clauses 1–6 verbatim (clause 6 from §9 above; verbatim from PR #323 §7)
2. D-1 binding restated (formal PnL = bid/ask executable harness; S-E target = same harness)
3. R7-A feature set restated (FIXED)
4. S-E + S-B-baseline cell definitions (per §7.1)
5. Sanity probe (incl. NEW items 7–11; per §10)
6. Pre-flight diagnostics + row-drop policy + split dates
7. All formal cells primary table (val + test for both cells)
8. Val-selected cell\* + q\* — FORMAL verdict source
9. Aggregate H1 / H2 / H3 / H4 outcome + verdict
10. Cross-cell verdict aggregation (per 26.0c-α §7.2)
11. **MANDATORY** 4-column baseline comparison:
    - 26.0d R6-new-A C02 (n=34,626 / Sharpe -0.1732 / Spearman -0.1535)
    - 27.0b C-alpha0 / S-B (n=34,626 / Sharpe -0.1732 / Spearman -0.1535)
    - 27.0c C-sd / S-D (n=32,324 / Sharpe -0.176 / Spearman -0.1060)
    - 27.0d val-selected
12. **MANDATORY** C-sb-baseline reproduction check (BaselineMismatchError HALT per §7.3; n_trades exact / Sharpe ±1e-4 / ann_pnl ±0.5 pip)
13. **MANDATORY** per-pair Sharpe contribution table for the val-selected cell (D4 sort: share_of_total_pnl desc)
14. **MANDATORY** pair concentration per cell (val_top_pair / val_top_share / test_top_pair / test_top_share)
15. Classification-quality diagnostics on the multiclass head (C-sb-baseline only; C-se has no class probs; AUC / Cohen κ / logloss — DIAGNOSTIC-ONLY)
16. Feature importance from regressor (4-bucket; DIAGNOSTIC-ONLY)
17. **NEW**: Predicted-PnL distribution train / val / test (DIAGNOSTIC-ONLY)
18. **NEW**: Predicted-vs-realised correlation diagnostic (OOF + train + val + test Pearson + Spearman; DIAGNOSTIC-ONLY)
19. **NEW**: Regressor MAE + R² on train / val / test (DIAGNOSTIC-ONLY)
20. Multiple-testing caveat (2 cells × 5 quantiles = 10 pairs)
21. Verdict statement

---

## 12. 27.0d-β implementation contract (high-level only; no code)

The 27.0d-β implementation PR (separate later instruction) will:

- Author `scripts/stage27_0d_s_e_regression_eval.py` inheriting from `scripts/stage27_0c_s_d_calibrated_ev_eval.py`
- Author `tests/unit/test_stage27_0d_s_e_regression_eval.py`
- Implement `build_pipeline_lightgbm_regression_widened()` (analogous to multiclass version but with regression objective per §4)
- Fit and freeze: ONE regressor (full-train; Huber loss) + ONE multiclass head (for C-sb-baseline only)
- 5-fold OOF protocol DIAGNOSTIC-ONLY (per D-W4): same fold seed (42) inherited from 27.0c
- Score val + test for both cells; cell scoring uses cached probs / regressor predictions (D10 amendment from §7.5)
- BaselineMismatchError HALT on C-sb-baseline non-match (§7.3)
- Emit `artifacts/stage27_0d/eval_report.md` with all 21 sections from §11
- Add `.gitignore` entries for `artifacts/stage27_0d/*` intermediates analogous to `artifacts/stage27_0c/*` entries
- Run sanity probe FIRST, then full sweep — same staging as 27.0b-β / 27.0c-β
- Lint via `run_custom_checks.py` + `ruff check` + `ruff format --check` before push
- CI green before merge

None of the above is authorised by THIS PR. It is documented here so 27.0d-β has an unambiguous contract.

---

## 13. Selection-overfit handling — explicit binding

> *S-E's two trainable artifacts (LightGBMRegressor for C-se; LightGBM multiclass head for C-sb-baseline) are BOTH fit on train-only data. Val data is used ONLY for cutoff selection (quantile-of-val q\* per cell). Test data is touched exactly once at the val-selected (cell\*, q\*). 5-fold OOF (if computed) is DIAGNOSTIC-ONLY and does NOT enter formal verdict routing. Any deviation is a NG#10 violation.*

This is the central S-E design risk and the binding wording. The two-layer separation is simpler than S-D's three-layer (no calibration layer, since the regressor's output IS the score by D-1 binding):

1. **Fitting layer**: regressor + multiclass head both fit on train-only; val never enters fitting
2. **Selection layer**: quantile-of-val cutoff fitting is val-only; test touched once at val-selected (cell\*, q\*)

If 27.0d-β implementation cannot satisfy either layer (e.g., a library forces val-touching during fit), the implementation MUST HALT and route back to design-memo amendment, not work around the binding.

---

## 14. What this PR will NOT do

- ❌ Authorise 27.0d-β eval implementation (separate later user instruction)
- ❌ Authorise post-27.0d routing review
- ❌ Authorise any other Phase 27 sub-phase (27.0e / 27.0f / ...)
- ❌ Authorise any R7-B / R7-C scope amendment (R-B / R-C / R-D paths remain available but require separate scope-amendment PRs)
- ❌ Authorise S-Other (quantile regression / ordinal / learn-to-rank) — NOT admissible per kickoff §8 / PR #323
- ❌ Authorise R7-D / R7-Other (NOT admissible per kickoff §8 / PR #323)
- ❌ Authorise additional regression-variant cells (MSE / L1 / Tweedie / etc.) within 27.0d-β (deferred per §7.6 to a possible future 27.0d-α-rev1)
- ❌ Authorise model-class changes for non-S-E score objectives (S-A / S-B / S-C / S-D remain bound to multiclass head)
- ❌ Modify Phase 27 scope per kickoff §8 / PR #323 clause 6 update
- ❌ Relax the ADOPT_CANDIDATE 8-gate A0-A5 wall
- ❌ Relax NG#10 / NG#11
- ❌ Modify γ closure (PR #279) / X-v2 OOS gating / Phase 22 frozen-OOS contract / production v9 20-pair tip 79ed1e8
- ❌ Pre-approve any production deployment under any 27.0d-β outcome
- ❌ Modify any prior verdict (Phase 25 / Phase 26 / Phase 27.0b-β / Phase 27.0c-β / routing reviews / scope amendment)
- ❌ Reopen Phase 26 L-class label-target redesign space
- ❌ Touch `src/`, `scripts/`, `tests/`, `artifacts/`, `.gitignore`, or `MEMORY.md`
- ❌ Auto-route to 27.0d-β implementation after merge

---

## 15. Sign-off

Phase 27 produces its fourth design memo (after kickoff #316 + 27.0b-α #317 + 27.0c-α #320). S-E tier moves from *admissible at 27.0d-α design memo* (PR #323) → *formal at sub-phase 27.0d-β* on merge of this design memo. The 27.0d-β implementation PR is triggered by a separate later user instruction. No auto-route.

**This PR stops here.**
