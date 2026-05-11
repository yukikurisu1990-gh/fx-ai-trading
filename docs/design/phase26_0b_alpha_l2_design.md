# Phase 26.0b-α — L-2 Generic Path-Quality Regression Design Memo

**Type**: doc-only design memo (binding contract for 26.0b-β)
**Status**: design-stage; NO implementation in this PR
**Label class**: **L-2** (generic continuous path-quality regression; parent family of L-3)
**Branch**: `research/phase26-0b-alpha-l2-design`
**Base**: master @ 03066fe (post-PR #304 merge — post-26.0a routing review)
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Context and approval semantics

PR #304 (post-26.0a routing review) framed five routing options (R1 L-1 / R2 L-2 / R3 L-4 / R4 L-3 rev2 / R5 soft close). The user explicitly selected **R2 (L-2)** as the next sub-phase per the routing review's §9 informational framing — L-2 is the parent family of L-3 (per PR #300 §3) and L-3's spread-aware specialisation formally REJECTed in PR #303, so the natural next step is to test whether a continuous path-quality target without spread embedding produces a different result.

This memo is the **binding contract** for the 26.0b-β implementation PR. Squash-merge approval of this PR binds:
- The L-2 design-point resolutions §3 (D-1..D-7),
- The 12-cell sweep grid §4 (Decision A — pair-set restriction is NOT a sweep knob),
- The H3 baseline of -0.192 (Phase 25 F1 best) per §6.1 (Decision B),
- The L-2 vs L-3 boundary statements §2 / §3.1 / §13,
- The CONCENTRATION_HIGH diagnostic-only flag rule §4.1,
- All ~28 unit-test requirements §10.

**The 26.0b-β implementation PR opens only on the user's separate explicit authorisation.** No implementation work is associated with this PR.

---

## 1. L-2 mission statement (binding label-class confirmation)

> *L-2 is the **generic continuous path-quality regression family**. Per PR #300 §3, L-2 is the parent of L-3 — L-3 is the spread-aware EV-regression specialisation that L-2 omits. Where L-3 embedded spread cost into the target at construction time (PR #301 §3.1), L-2 uses a continuous path-quality score that does **NOT** embed spread cost. The hypothesis tested in 26.0b-β is: does continuous-target ranking signal (diagnostic D-1 from PR #304: raw_pip Spearman +0.38) translate into realised PnL when the target is spread-independent? If L-2 also fails, the L-2/L-3 spread-embedding question is closed in favour of "neither variant monetises at minimum-feature-set"; if L-2 succeeds where L-3 didn't, the L-3 spread-embedding step was the binding piece.*

### 1.1 What L-2 changes vs L-3 (single-axis change)

> *L-2 target excludes spread at label construction. The 8-gate realised PnL still includes executable bid/ask spread / cost via inherited M1 path re-traverse (unchanged from L-3). L-2 tests whether a generic continuous path-quality target ranks opportunities better without embedding spread into the training target.*

| Aspect | L-3 (PR #301) | L-2 (this memo) |
|---|---|---|
| Target construction | mid-to-mid base PnL **minus spread cost** (D-4 from #301 §3.1) | mid-to-mid base PnL **WITHOUT spread subtraction** |
| Spread role in label | Embedded in target at construction time | Excluded from target |
| Spread role in 8-gate scoring | Via `_compute_realised_barrier_pnl` (ask/bid path) | **Unchanged** — same `_compute_realised_barrier_pnl` (ask/bid path) |
| Family | spread-aware EV-regression specialisation | generic continuous path-quality regression (parent family) |

This is a **single-axis change** from L-3. All other Phase 26 / 26.0a-α / rev1 contract elements are inherited unchanged (see §2).

---

## 2. Inheritance from Phase 25 / Phase 26 prior PRs (binding)

| Element | Source | Status in L-2 |
|---|---|---|
| 20-pair canonical universe | #299 / 25.0a-β | preserved |
| M5 signal bars + M1 path data | 25.0a-β | preserved |
| 70/15/15 chronological split | inherited | preserved |
| 8-gate harness A0-A5 (Sharpe ≥ +0.082, ann_pnl ≥ +180 pip, MaxDD ≤ 200, A4 ≥ 3/4 folds, A5 +0.5 pip stress > 0) | Phase 22 contract | preserved as authoritative gating |
| Realised PnL via M1 path re-traverse (`_compute_realised_barrier_pnl`) | inherited unchanged | preserved (ask/bid path with original cost model) |
| Regression head | #301 §4 + rev1 | preserved (LinearRegression / Ridge α=1.0 / LightGBM fixed conservative config per §4.1) |
| 3 production-misuse guards | inherited | preserved |
| NG#10 / NG#11 | inherited | preserved (NOT relaxed) |
| γ closure (PR #279) | inherited | preserved unchanged |
| Mid-to-mid base PnL (§3.1 from 26.0a-α #301) | inherited | preserved |
| **No double-counting of spread** | inherited from L-3 §3.1 | **VACUOUSLY held in L-2** because L-2 does NOT subtract spread in target construction |
| K_FAV / K_ADV barrier geometry | inherited | preserved (1.5 / 1.0) |
| **Quantile-of-val threshold family** | inherited from rev1 #302 | preserved (primary verdict basis: {Q-5, Q-10, Q-20, Q-30, Q-40}) |
| Negative absolute thresholds (secondary diagnostic) | inherited from rev1 | preserved (raw_pip {-5,-3,-1,0,+1} / atr {-0.5,-0.3,-0.1,0,+0.1}) |
| Validation-only cell+threshold selection | inherited from rev1 §6 | preserved (A0-prefilter → max val Sharpe → val annual_pnl → lower MaxDD → simpler model class) |
| Test set touched once | inherited | preserved |
| H1 two-tier (weak ρ>0.05 / meaningful ρ≥0.10) | inherited from 26.0a-α §6 | preserved |
| Verdict tree (H2 PASS alone NOT ADOPT_CANDIDATE) | inherited from 26.0a-α §7 | preserved |
| Diagnostic columns prohibition | inherited from 26.0a-α §9 clause 2 / rev1 | preserved |
| Realised-PnL precomputation cache (cell-independent) | inherited from rev1 implementation | preserved (~30 min total runtime) |
| Minimum feature set (`pair` + `direction` only) | inherited from 26.0a-α §5.1 | preserved |
| H3 reference Sharpe | -0.192 (Phase 25 F1 best) | preserved per Decision B §6.1 |

---

## 3. Design-point resolutions (D-1 to D-7; binding)

Most D-points inherit from L-3 verbatim. **The L-2 change is in D-4 (spread treatment)** — L-2 does NOT subtract spread at the label-construction stage.

| # | Design point | Binding resolution for L-2 |
|---|---|---|
| **D-1** | Horizon expiry handling | **Same as L-3**: include with mark-to-market via M5 close at `t + horizon_bars`; mid-to-mid difference. |
| **D-2** | MFE / MAE vs. actual exit PnL | **Same as L-3**: actual exit PnL only. MFE / MAE NOT in label. |
| **D-3** | TP / SL barrier dependency | **Same as L-3**: inherit 25.0a-β triple-barrier (K_FAV=1.5, K_ADV=1.0). |
| **D-4** | **Spread treatment** | **L-2 KEY DIFFERENCE** — **NO spread subtraction at label construction.** Target = mid-to-mid base PnL only, per §3.1. Spread cost surfaces ONLY at 8-gate realised-PnL scoring via inherited `_compute_realised_barrier_pnl`. |
| **D-5** | Raw pip vs. ATR-normalised target | **SWEEP KNOB** (inherited from rev1): raw_pip vs atr_normalised. Both retained pending L-3's ATR-normalised pair-bias finding (diagnostic D-2 from #304); pair-bias surfaces as **CONCENTRATION_HIGH** diagnostic-only flag per §4.1. |
| **D-6** | Outlier clipping / winsorisation | **SWEEP KNOB** (inherited): none vs q01/q99 train-fit. Train-only-fit; harness PnL NEVER winsorised. |
| **D-7** | Regression model | **SWEEP KNOB** (inherited): LinearRegression / Ridge α=1.0 / LightGBM fixed conservative config per rev1 §4.1. |

### 3.1 L-2 label construction (binding; mid-to-mid only)

> *For L-2, the regression target is the mid-to-mid base PnL with NO spread subtraction. The L-3 §3.1 base PnL definitions are inherited verbatim; the L-3 §3.1 D-4 spread-subtraction step is OMITTED in L-2.*

```
Base mid-path PnL (inherited from L-3 §3.1):
  Long  : base_mid_pnl = (mid_exit - mid_entry) / pip_size
  Short : base_mid_pnl = (mid_entry - mid_exit) / pip_size

mid_exit per triple-barrier outcome (inherited):
  TP    : mid_entry + sign(dir) * K_FAV * atr_at_signal_pip * pip_size
  SL    : mid_entry - sign(dir) * K_ADV * atr_at_signal_pip * pip_size
  TIME  : (bid_c + ask_c) / 2 at bar t + horizon_bars

L-2 label (NO D-4 spread subtraction):
  label_pre = base_mid_pnl                    # NOT base_mid_pnl - spread*factor

D-5 target scale (sweep knob):
  raw_pip          : label = label_pre
  atr_normalised   : label = label_pre / atr_at_signal_pip
```

> *Spread cost is NOT embedded in the L-2 target. The 8-gate harness still scores realised PnL through `_compute_realised_barrier_pnl` (ask/bid path with original cost model — unchanged from L-3); the difference is that the model's TRAINING TARGET does not include spread cost.*

### 3.2 Strict-causal stance (inherited unchanged)

Labels by construction use future bars within the horizon window (same as 25.0a-β and L-3). All inputs to label construction (`atr_at_signal_pip`, entry bid/ask) are at-or-before signal time. Minimum feature set = `pair + direction` only (per 26.0a-α §5.1).

---

## 4. Sweep grid (binding for 26.0b-β; Decision A: 12 cells)

> ***Decision A (locked):*** *Pair-set restriction is NOT a sweep knob in 26.0b-β. All formal cells use the canonical 20-pair universe.*

Total: **12 cells** (2 × 2 × 3).

| Knob | Values | Levels |
|---|---|---|
| **D-5 target scale** | {raw_pip, atr_normalised} | 2 |
| **D-6 outlier clipping** | {none, q01_q99 train-fit winsorise} | 2 |
| **Regression model (D-7)** | {LinearRegression, Ridge α=1.0, LightGBM fixed conservative} | 3 |
| **Total cells** | | **12** |

> *D-4 spread treatment is collapsed (single value: "no spread subtraction"); not a sweep knob in L-2.*

### 4.1 Pair concentration as diagnostic-only (Decision A; binding)

> *Pair concentration is reported as diagnostic-only. CONCENTRATION_HIGH flag fires when selected trades' single-pair share ≥ 80% on the validation set. This flag is **NOT** used for formal verdict or cell selection. It surfaces L-3's USD_JPY 100% concentration pattern (diagnostic D-2 from PR #304) and lets the user observe whether L-2 has the same pair-bias signature without coupling it to the verdict pipeline.*

The 26.0b-β eval_report must include:

- Per-cell, per-q% pair concentration table (val + test): pair → trade count, % of total selected.
- CONCENTRATION_HIGH flag column (boolean: `True` if any single pair ≥ 80% of val_selected trades at the val-fit cutoff).
- Explicit label "diagnostic; not used for verdict" on this table.

A unit test (#26 in §10) enforces the CONCENTRATION_HIGH threshold and confirms it is NOT consulted by `select_cell_validation_only` or `assign_verdict`.

### 4.2 LightGBM fixed conservative config (inherited from 26.0a-α §4.1)

```python
LIGHTGBM_FIXED_CONFIG = dict(
    n_estimators=200,
    learning_rate=0.03,
    num_leaves=31,
    max_depth=4,
    min_child_samples=100,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
)
```

No LightGBM hyperparameter tuning is allowed. If LightGBM is not importable, defer the LightGBM cells (4 of 12) and run 8 cells with Ridge + LinearRegression only.

> Note: `lightgbm 4.6.0` confirmed importable in the eval environment as of memo authoring (per PR #301 §4.1 / PR #303 confirmation).

---

## 5. Eval harness (inherited unchanged from 26.0a-α + rev1)

| Component | Spec |
|---|---|
| Universe | 20-pair canonical (M5 bars, 25.0a-β path-quality dataset). **No pair restriction.** |
| Triple-barrier geometry | K_FAV=1.5, K_ADV=1.0 (D-3) |
| Split | 70/15/15 strict chronological train/val/test |
| Regression head | Per-cell model per §4; `random_state=42` only for LightGBM |
| Realised PnL (for 8-gate scoring) | M1 path re-traverse via `_compute_realised_barrier_pnl` (unchanged) |
| 8-gate harness | A0 ≥ 70 ann trades, A1 Sharpe ≥ +0.082, A2 ann_pnl ≥ +180 pip, A3 MaxDD ≤ 200, A4 ≥ 3/4 folds, A5 +0.5 pip stress > 0 |
| LOW_BUCKET_N | n < 100 flag |

### 5.1 Threshold selection (inherited from rev1 §3 / §4 unchanged)

**PRIMARY**: quantile-of-val family {Q-5, Q-10, Q-20, Q-30, Q-40}. Cutoff is fit on val ONLY (scalar `np.quantile(pred_val, 1 - q/100)`); applied to test predictions as the same scalar. NO full-sample qcut; NO peeking at test predictions.

**SECONDARY DIAGNOSTIC**: negative absolute candidates per scale (raw_pip {-5,-3,-1,0,+1}; atr_normalised {-0.5,-0.3,-0.1,0,+0.1}). NOT used for formal verdict.

### 5.2 Cell+threshold selection (inherited from rev1 §6)

Validation-only. Priority:

1. Pre-filter: cells with `val_n_trades >= A0-equivalent` (under the candidate q's val cutoff) are eligible. If none, LOW_VAL_TRADES flag is set; fallback to all valid candidates.
2. Max val realised Sharpe (primary).
3. Tie-breakers (deterministic): max val annual_pnl → lower val MaxDD → simpler model class (LinearRegression > Ridge > LightGBM; deterministic final tie-breaker only, NOT a model preference).

Test set touched exactly once on the val-selected (cell*, q*) pair with the val-fit cutoff_q*.

### 5.3 Realised-PnL precomputation cache (inherited from rev1)

Realised PnL precomputed once per split (val + test) and reused across all 12 cells. Same optimisation as rev1.

---

## 6. Hypothesis chain (H1 two-tier; H2; H3; H4; inherited from 26.0a-α §6)

| H | Statement |
|---|---|
| **H1-weak** | val-selected cell test Spearman ρ > 0.05 |
| **H1-meaningful** | val-selected cell test Spearman ρ ≥ 0.10 (formal H1 PASS) |
| **H2** | val-selected cell A1+A2 PASS on test (Sharpe ≥ +0.082 AND ann_pnl ≥ +180 pip) |
| **H3** | val-selected cell test realised Sharpe > **-0.192** (Phase 25 F1 best; Decision B §6.1) |
| **H4** | val-selected cell test realised Sharpe ≥ 0 (structural-gap escape) |

### 6.1 H3 baseline = -0.192 (Decision B; binding)

> ***Decision B (locked):*** *H3 baseline is **-0.192** (Phase 25 F1 best realised Sharpe). L-3 val-selected -0.2232 is NOT used as a baseline because it is worse than F1 and would relax the H3 standard.*

The H3 baseline of -0.192 is the Phase 25 F1 best realised Sharpe (PR #284). This was the same value used in 26.0a-α §6 binding (inherited unchanged in rev1). L-3 val-selected test Sharpe was -0.2232 (worse than F1), so using it as the L-2 baseline would lower the bar relative to the binding 26.0a-α / rev1 framing. H3 measures "improvement over best prior-phase verdict-source"; F1's -0.192 remains the best so far.

A unit test (#25 in §10) enforces `H3_REFERENCE_SHARPE == -0.192`.

---

## 7. Verdict tree (inherited unchanged from 26.0a-α §7 + rev1)

| Outcome | Verdict |
|---|---|
| H1-meaningful PASS, H2 PASS, A0-A5 all pass | **ADOPT_CANDIDATE** |
| H1-meaningful PASS, H2 PASS, A3-A5 partial | PROMISING_BUT_NEEDS_OOS |
| H1-meaningful PASS, H2 PASS, A3-A5 fail | REJECT |
| H1-meaningful PASS, H2 FAIL, H3 PASS | REJECT_BUT_INFORMATIVE_IMPROVED |
| H1-meaningful PASS, H2 FAIL, H3 FAIL | REJECT_BUT_INFORMATIVE_FLAT |
| H1-weak PASS only (0.05 < ρ < 0.10) | REJECT_WEAK_SIGNAL_ONLY |
| H1-weak FAIL (ρ ≤ 0.05) | REJECT_NON_DISCRIMINATIVE |

> **H2 PASS alone does NOT imply ADOPT_CANDIDATE.** Full A0–A5 required.

---

## 8. Regression diagnostics (inherited; diagnostic-only)

For each cell: R², Pearson, Spearman (H1 metric), MAE, RMSE. Decile reliability table for val-selected cell on test. Best-by-test-Spearman and best-by-test-Sharpe diagnostic-only cells in eval_report (labelled "diagnostic; not used for verdict").

**Pair concentration table (§4.1 binding):** per-cell, per-q% pair → trade count + percentage. CONCENTRATION_HIGH flag at ≥80% single-pair share on val. Diagnostic-only; not used for verdict.

---

## 9. Mandatory clauses (verbatim, 6 total — inherited unchanged from #299 §7 / 26.0a-α §9 / rev1 §11)

1. **Phase 26 framing** — Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.
2. **Diagnostic columns prohibition** — Calibration / threshold-sweep / directional-comparison columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.
3. **γ closure preservation** — Phase 24 γ hard-close (PR #279) is unmodified.
4. **Production-readiness preservation** — X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure) remains untouched.
5. **NG#10 / NG#11 not relaxed**.
6. **Phase 26 scope** — Phase 26 is NOT a continuation of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed.

---

## 10. Required unit tests for 26.0b-β (~28 tests)

Inherits the L-3 rev1 test structure with L-2-specific NEW / MODIFIED tests:

| # | Test name | Purpose |
|---|---|---|
| 1 | `test_l2_label_construction_deterministic` | Same input → same label |
| 2 | `test_l2_base_pnl_is_mid_to_mid_long` | §3.1 long formula |
| 3 | `test_l2_base_pnl_is_mid_to_mid_short` | §3.1 short formula |
| 4 | **`test_l2_no_spread_subtraction_in_label`** ★ NEW | §3.1 binding: L-2 target = `base_mid_pnl` (no D-4 spread subtraction) |
| 5 | **`test_l2_target_unchanged_when_spread_perturbed`** ★ NEW | Perturbing `spread_at_signal_pip` does NOT change the L-2 label |
| 6 | `test_l2_inherits_triple_barrier_k_fav_k_adv` | D-3 |
| 7 | `test_l2_horizon_expiry_uses_m5_close_mark_to_market` | D-1 |
| 8 | `test_l2_label_excludes_mfe_mae` | D-2 |
| 9 | `test_l2_atr_normalised_scale` | D-5 |
| 10 | `test_l2_raw_pip_scale` | D-5 |
| 11 | `test_l2_winsorise_thresholds_fit_on_train_only` | D-6 |
| 12 | `test_l2_winsorise_does_not_touch_realised_pnl_for_harness` | D-6 scope |
| 13 | **`test_sweep_grid_has_12_cells`** ★ MODIFIED (12 not 24) | §4 invariant |
| 14 | `test_lightgbm_uses_fixed_conservative_config` | inherited |
| 15 | `test_lightgbm_defer_path_when_not_importable` | inherited |
| 16 | `test_cell_and_threshold_selection_uses_validation_only` | inherited from rev1 |
| 17 | `test_verdict_tree_h2_pass_alone_not_adopt` | §7 invariant |
| 18 | `test_verdict_tree_h1_meaningful_threshold_010` | §6 H1 two-tier |
| 19 | `test_verdict_tree_h1_weak_band_005_to_010` | §6 H1 two-tier |
| 20 | `test_quantile_cutoff_fits_on_val_only` | inherited from rev1 |
| 21 | `test_quantile_cutoff_applied_to_test_uses_val_fit_value` | inherited from rev1 |
| 22 | `test_no_full_sample_qcut_in_quantile_path` | inherited from rev1 |
| 23 | `test_quantile_threshold_family_has_5_candidates` | inherited from rev1 |
| 24 | `test_negative_absolute_thresholds_secondary_informational` | inherited from rev1 |
| 25 | **`test_h3_baseline_constant_phase25_f1_minus_0192`** | §6.1 Decision B: `H3_REFERENCE_SHARPE == -0.192` |
| 26 | **`test_concentration_high_flag_is_diagnostic_only`** ★ NEW | §4.1: CONCENTRATION_HIGH flag NOT consulted by `select_cell_validation_only` or `assign_verdict` |
| 27 | `test_no_diagnostic_columns_in_feature_set` | inherited |
| 28 | `test_ridge_pipeline_has_no_random_state` | inherited (Ridge deterministic without random_state) |

Plus invariant guards (A0-prefilter, barrier outcome branches) as in rev1. **Total: ~28 tests** including 3 NEW L-2-specific tests (#4, #5, #26).

---

## 11. Files for 26.0b-β (binding declaration)

```
scripts/stage26_0b_l2_eval.py             # ~1400-1600 lines
                                            # mirrors stage26_0a_l3_eval.py
                                            # with D-4 spread subtraction
                                            # step REMOVED + CONCENTRATION_HIGH
                                            # diagnostic flag added
tests/unit/test_stage26_0b_l2_eval.py     # ~28 unit tests per §10
artifacts/stage26_0b/eval_report.md       # ~190-250 lines
.gitignore                                # +1 stanza for stage26_0b raw artifacts
```

---

## 12. PR chain reference

```
Phase 26:
  #299 (kickoff) → #300 (first-scope review)
  → #301 (26.0a-α L-3 design) → #302 (26.0a-α-rev1 threshold redesign)
  → #303 (26.0a-β rev1 L-3 eval — REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL)
  → #304 (post-26.0a routing review — R2 L-2 selected)
  → THIS PR (26.0b-α L-2 design memo)
  → [user explicitly authorises 26.0b-β]
  → 26.0b-β L-2 eval (separate PR; binding contract = THIS PR)
  → review post-26.0b (separate PR)
  → ... (sub-phase chain)
```

---

## 13. What this PR will NOT do

- ❌ Implement any L-2 label / dataset / eval code.
- ❌ Run any sweep, generate any artifact under `artifacts/stage26_0b/`.
- ❌ Modify any prior verdict (Phase 25 / Phase 26 #284 / #287 / #290 / #293 / #296 / #297 / #298 / #299 / #300 / #301 / #302 / #303 / #304).
- ❌ Retroactively change the L-3 verdict (REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL from #303).
- ❌ Pre-approve production deployment of any L-2 model.
- ❌ Relax NG#10 / NG#11.
- ❌ Modify γ closure (PR #279).
- ❌ Touch existing artifacts (stage25_* / stage26_0a remain intact).
- ❌ Update MEMORY.md.
- ❌ Auto-route to 26.0b-β implementation. The next PR opens only on the user's separate explicit authorisation.
- ❌ Foreclose L-1 / L-4 / R4 L-3 rev2 (admissible follow-up candidates per PR #304 §4).
- ❌ Foreclose F4 / F6 / F5-d / F5-e (Phase 25 deferred extensions).
- ❌ Change K_FAV / K_ADV barrier geometry (inherited at 1.5 / 1.0).
- ❌ Add new dependencies. LightGBM is already in the environment; if it became unavailable, the §4.2 graceful 8-cell deferral path applies.
- ❌ Embed spread cost in the L-2 target (the L-2 vs L-3 distinction; spread surfaces only at 8-gate harness PnL stage via inherited `_compute_realised_barrier_pnl`).
- ❌ Use pair-set restriction as a sweep dimension (Decision A: 12 cells; pair concentration is diagnostic-only).
- ❌ Use the CONCENTRATION_HIGH flag for formal verdict or cell selection (§4.1 binding).
- ❌ Use Spearman as a formal cell-selection key (inherited diagnostic-columns prohibition from 26.0a-α §9 clause 2).

---

## 14. Sign-off / 26.0b-β binding requirements

This memo is the **binding contract** for 26.0b-β. The 26.0b-β implementation PR must:

- Construct the L-2 label strictly per §3 (D-1..D-7) with the resolutions locked above.
- **No spread subtraction at label construction (§3.1 binding).** Tests #4 and #5 enforce.
- Run the 12-cell sweep per §4 (Decision A: pair-set restriction NOT a sweep knob).
- Use the canonical 20-pair universe for all formal cells (§5).
- Use the quantile threshold family per §5.1 as the formal verdict basis (inherited from rev1 §3).
- Apply the validation-only cell-and-threshold selection rule per §5.2; touch the test set exactly once on the val-selected (cell, q) pair.
- Report pair concentration per §4.1 as diagnostic-only (CONCENTRATION_HIGH flag at ≥80% single-pair share; NOT used for verdict).
- Test the hypothesis chain per §6 (H1 two-tier; H2; H3 baseline = -0.192 per Decision B §6.1; H4) against the eval harness per §5.
- Include regression diagnostics per §8 (diagnostic-only; explicitly labelled).
- Apply the verdict tree per §7 — H2 PASS alone is **NOT** ADOPT_CANDIDATE.
- Honour all six mandatory clauses per §9 verbatim in `eval_report.md`.
- Include all ~28 unit tests per §10. Especially:
  - `test_l2_no_spread_subtraction_in_label` (§3.1 binding)
  - `test_l2_target_unchanged_when_spread_perturbed` (L-2 vs L-3 boundary)
  - `test_sweep_grid_has_12_cells` (Decision A invariant)
  - `test_h3_baseline_constant_phase25_f1_minus_0192` (Decision B invariant)
  - `test_concentration_high_flag_is_diagnostic_only` (§4.1 binding)
- NOT relax NG#10 / NG#11; NOT modify γ closure; NOT touch stage25_* / stage26_0a artifacts; NOT add new dependencies.

This memo stops here. The 26.0b-β implementation PR opens only on the user's separate explicit authorisation.
