# Phase 26.0a-α — L-3 EV Regression Design Memo

**Type**: doc-only design memo (binding contract for 26.0a-β)
**Status**: design-stage; NO implementation in this PR
**Label class**: **L-3** (spread-aware EV-regression specialisation of the L-2 family)
**Branch**: `research/phase26-0a-alpha-l3-design`
**Base**: master @ 7e3609a (post-PR #300 merge — Phase 26 first-scope review)
**Author**: research/post-bug-fix-2026-05-03 stream

---

## 0. Context and approval semantics

PR #300 (Phase 26 first-scope review) tentatively recommended L-3 with the EV definition explicitly deferred to this memo. The user then explicitly selected L-3 and authorised 26.0a-α to start. This memo is the **binding contract** for the 26.0a-β implementation PR.

**Squash-merge approval of this PR binds the design-point resolutions (D-1..D-6), the 24-cell sweep grid (§4), the validation-only cell-and-threshold selection rule (§5.3), the two-tier H1 hypothesis (§6), and all unit-test requirements (§10). The 26.0a-β implementation PR opens only on the user's separate explicit authorisation.** No implementation work is associated with this PR.

---

## 1. Phase 26 framing recap (from PR #299)

> *Phase 26 is the entry-side return on alternative label / target designs layered on the 20-pair canonical universe and the 8-gate harness. Phase 26 is NOT a continuation of Phase 25's feature-axis sweep.*

---

## 2. L-3 mission statement (binding label-class confirmation)

> *L-3 is confirmed as the first Phase 26 label class. L-3 is the spread-aware EV-regression specialisation of the L-2 family (per PR #300 §3). The target is a continuous EV value with bid/ask spread embedded at label construction time, intended to bring the model's training objective closer to the realised pip PnL the 8-gate harness ultimately scores.*

---

## 3. Design-point resolutions (D-1 to D-6, binding)

| # | Design point | Binding resolution |
|---|---|---|
| **D-1** | Horizon expiry handling | Include with mark-to-market: use the M5 close at `t + horizon_bars` minus the entry mid, then subtract spread cost per D-4. ATR-normalised only if cell's target scale is "ATR-normalised". |
| **D-2** | MFE / MAE vs. actual exit PnL | **Actual exit PnL only.** MFE / MAE are NOT in the label. |
| **D-3** | TP / SL barrier dependency | Inherit 25.0a-β triple-barrier: K_FAV = 1.5 × ATR, K_ADV = 1.0 × ATR, same-bar SL-first. Per PR #299 §5 binding rule. |
| **D-4** | Entry-spread-only vs. exit-side spread | **SWEEP KNOB** — 2 variants: (a) entry-only (subtract `spread_at_signal_pip` × 1); (b) round-trip 2× (subtract `spread_at_signal_pip` × 2). Both use only the pre-trade signal-bar spread; both are strictly causal w.r.t. signal time. |
| **D-5** | Raw pip vs. ATR-normalised target | **SWEEP KNOB** — 2 variants: (a) raw pip PnL; (b) ATR-normalised (`PnL_pip / atr_at_signal_pip`). |
| **D-6** | Outlier clipping / winsorisation | **SWEEP KNOB** — 2 variants: (a) no clipping; (b) winsorise at q01 / q99 fitted on **TRAIN ONLY**; train-fit thresholds applied to val / test. **Winsorisation applies ONLY to the training target y; it MUST NOT modify realised PnL fed to the 8-gate harness.** Unit test enforces. |

### 3.1 No double-counting of spread (binding statement)

> *Spread cost is subtracted exactly once during label construction, in accordance with D-4. The base PnL for label construction is the mid-path PnL (mid-to-mid). D-4 then subtracts the spread cost.*

**Base mid-path PnL definitions (binding):**

| Direction | Pre-cost PnL |
|---|---|
| Long  | `(mid_exit − mid_entry) / pip_size` |
| Short | `(mid_entry − mid_exit) / pip_size` |

where `mid_entry = (bid_o + ask_o) / 2` at the entry bar and `mid_exit` is determined by the triple-barrier outcome:

- **TP hit**: `mid_exit = mid_entry + sign(direction) × K_FAV × atr_at_signal_pip × pip_size`
- **SL hit**: `mid_exit = mid_entry − sign(direction) × K_ADV × atr_at_signal_pip × pip_size`
- **Horizon expiry**: `mid_exit = (bid_c + ask_c) / 2` at bar `t + horizon_bars` (M5 bars; matches 25.0a-β `_compute_realised_barrier_pnl` mark-to-market semantics — per D-1)

**Then subtract spread cost per D-4** (the only place spread enters the label):

- D-4 (a) entry-only: `label_pre_norm = base_mid_pnl − spread_at_signal_pip × 1`
- D-4 (b) round-trip 2×: `label_pre_norm = base_mid_pnl − spread_at_signal_pip × 2`

**Then apply D-5 target scale:**

- D-5 (a) raw pip: `label = label_pre_norm`
- D-5 (b) ATR-normalised: `label = label_pre_norm / atr_at_signal_pip`

> **Spread is subtracted exactly once. The base PnL is mid-to-mid (NO ask/bid asymmetry in the base PnL). Realised PnL fed to the 8-gate harness is unchanged from 25.0a-β semantics (`_compute_realised_barrier_pnl`) and uses the ask/bid path properly with the original cost model. The label and the harness PnL are computed independently; the label is the regression target, the harness PnL is what the verdict measures.**

### 3.2 Strict-causal stance for L-3

Labels by construction use future bars within the horizon window (same as 25.0a-β). The strict-causal contract that applies to L-3 is:

- All inputs to label construction (`spread_at_signal_pip`, `atr_at_signal_pip`, entry bid/ask) are **at-or-before signal time** (`signal_ts`) — no future spread or future ATR.
- Features (inherited from 25.0a-β or any future Phase 26 sub-phase) use bars ≤ t-1 (strict-causal). This memo does NOT introduce new features; it inherits the bare 25.0a-β features (pair, direction) plus the regression head.

---

## 4. Sweep grid (binding for 26.0a-β)

| Knob | Values | Levels |
|---|---|---|
| **D-4 spread treatment** | {entry-only, round-trip 2×} | 2 |
| **D-6 outlier clipping** | {none, q01–q99 train-fit winsorise} | 2 |
| **D-5 target scale** | {raw pip, ATR-normalised} | 2 |
| **Regression model** | {Ridge α=1.0, LinearRegression, LightGBM fixed conservative config} | 3 |
| **Total cells** | | **24** |

### 4.1 LightGBM fixed conservative config (binding)

> *LightGBM default hyperparameters are PROHIBITED in 26.0a-β. LightGBM is used as a fixed non-linear sanity check, not as a model-tuning lever. No LightGBM hyperparameter tuning is allowed in 26.0a-β.*

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

If LightGBM is not importable in the implementation environment, the 26.0a-β PR must **defer LightGBM cells (8 of 24) rather than introduce a new dependency**. The sweep then proceeds with 16 cells (Ridge + LinearRegression branches only) and `eval_report.md` explicitly notes the deferral.

> Note: `lightgbm 4.6.0` is confirmed importable in this repo's eval environment as of memo authoring time.

---

## 5. Eval harness (inherits 25.0a-β + regression-specific additions)

| Component | Spec |
|---|---|
| Universe | 20-pair canonical (M5 bars, 25.0a-β path-quality dataset) |
| Triple-barrier geometry | K_FAV = 1.5, K_ADV = 1.0 (inherited; per D-3) |
| Split | 70 / 15 / 15 strict chronological train / val / test |
| Regression head | Per-cell model per §4; `random_state=42` for reproducibility |
| Realised PnL (for 8-gate scoring) | M1 path re-traverse — `_compute_realised_barrier_pnl` from `stage25_0b`, unchanged |
| 8-gate harness | A0 ≥ 70 ann trades, A1 Sharpe ≥ +0.082, A2 ann_pnl ≥ +180 pip, A3 MaxDD ≤ 200, A4 ≥ 3/4 folds, A5 +0.5 pip stress > 0 |
| LOW_BUCKET_N | flag at n < 100 (inherited) |

### 5.1 Feature set for 26.0a-β

> *26.0a-β uses the minimum feature set for the regression head: `pair` (categorical) and `direction` (categorical). NO Phase 25 F1-F5 features are added. This isolates the label-effect from any feature-effect.*

Subsequent Phase 26 sub-phases (26.0b+, on user instruction) may revisit feature additions under the chosen label; 26.0a-β is the label-isolation baseline.

### 5.2 Threshold-selection (validation-only)

- Threshold candidates: `{0.0, 0.1, 0.2, 0.3, 0.4}` (for ATR-normalised cells) or `{0.0, 1.0, 2.0, 3.0, 4.0}` pip (for raw-pip cells; ~ATR-multiple equivalents at typical 10-pip ATR).
- For each candidate threshold, compute validation realised barrier PnL (using `_compute_realised_barrier_pnl`).
- Selection metric per cell: validation realised Sharpe. Tie-breaker by validation annual_pnl.
- Threshold is locked per cell BEFORE the test set is touched.

### 5.3 Cell-and-threshold selection (binding rule)

> *Both cell selection (one of 24 cells) AND threshold selection (one of 5 per cell) are made on validation only. Test set is touched exactly once on the val-selected (cell, threshold) pair.*

**Selection objective (in priority order):**

| Priority | Criterion |
|---|---|
| 1 | Maximum validation realised Sharpe (using realised barrier PnL via M1 path re-traverse with the cell's val-selected threshold) |
| 2 | Maximum validation annual_pnl |
| 3 | Validation trade count meets A0-equivalent (≥ 70 × val_span_years annualised); cells below A0 are de-prioritised |
| 4 | Lower validation MaxDD |
| 5 | Simpler model class (LinearRegression > Ridge > LightGBM) if all above tied |

The eval_report MAY include **diagnostic-only** tables of top cells by test Spearman and by test realised Sharpe, but the **formal verdict is based on the validation-selected cell evaluated on the test set, touched once**. Diagnostic tables MUST be labelled "diagnostic; not used for verdict".

---

## 6. Hypothesis chain (H1 two-tier; H2-H4)

| H | Statement |
|---|---|
| **H1-weak** | Validation-selected cell test **Spearman ρ > 0.05** between predicted EV and realised pip PnL (weak label-quality signal) |
| **H1-meaningful** | Validation-selected cell test **Spearman ρ ≥ 0.10** between predicted EV and realised pip PnL (formal H1 PASS threshold) |
| **H2** | Validation-selected cell A1 + A2 PASS on the 8-gate harness on the test set (Sharpe ≥ +0.082 AND ann_pnl ≥ +180 pip) |
| **H3** | Validation-selected cell test realised Sharpe > Phase 25 best ( = F1's −0.192) — *label-redesign demonstrably improves over the best Phase 25 feature-axis result* |
| **H4** | Validation-selected cell test realised Sharpe ≥ 0 — **structural-gap escape test** (the load-bearing test for the H-G binary-label-binding hypothesis) |

### 6.1 H1 two-tier reporting

The eval_report explicitly splits H1 into weak (ρ > 0.05) and meaningful (ρ ≥ 0.10):

- **H1-weak FAIL** (ρ ≤ 0.05): label has no discriminative signal at all → REJECT_NON_DISCRIMINATIVE.
- **H1-weak PASS, H1-meaningful FAIL** (0.05 < ρ < 0.10): weak signal only → reported in the verdict tree as a separate band.
- **H1-meaningful PASS** (ρ ≥ 0.10): formal H1 PASS; verdict tree proceeds normally.

H2 remains the most important gate. The two-tier H1 framing is for **eval_report clarity and routing-decision context**, not for changing the verdict tree's ADOPT_CANDIDATE / REJECT structure.

---

## 7. Verdict tree (analogous to Phase 25 25.0e-α §7, extended for H1 two-tier)

| Outcome | Verdict |
|---|---|
| H1-meaningful PASS, H2 PASS, all 8 gates A0-A5 PASS | **ADOPT_CANDIDATE** |
| H1-meaningful PASS, H2 PASS, A3-A5 partial | PROMISING_BUT_NEEDS_OOS |
| H1-meaningful PASS, H2 PASS, A3-A5 fail | REJECT |
| H1-meaningful PASS, H2 FAIL, H3 PASS | REJECT_BUT_INFORMATIVE_IMPROVED |
| H1-meaningful PASS, H2 FAIL, H3 FAIL | REJECT_BUT_INFORMATIVE_FLAT |
| H1-weak PASS only (0.05 < ρ < 0.10) | REJECT_WEAK_SIGNAL_ONLY (informative for next-PR routing) |
| H1-weak FAIL (ρ ≤ 0.05) | REJECT_NON_DISCRIMINATIVE |

**H2 PASS alone does NOT imply ADOPT_CANDIDATE.** Full A0–A5 required.

H4 reported separately at the aggregate level with the same softened wording pattern as Phase 25 (#296): *H4 FAIL strongly supports continuing the label-redesign hypothesis on the next L-class variant or moving to a different design axis, but the user still chooses.*

---

## 8. Regression diagnostics (diagnostic-only)

For each cell:

- Test R²
- Test Pearson ρ
- Test Spearman ρ (the H1 metric)
- Predicted-vs-realised decile reliability table (binned by predicted target; mean realised PnL per bin)
- Per-bucket MSE / MAE

> **Diagnostic-only — does NOT change ADOPT criteria.** NG#10 / NG#11 not relaxed. The eval_report labels all such tables explicitly.

---

## 9. Mandatory clauses (verbatim, 6 total — inherited from PR #299 §7)

1. **Phase 26 framing** — *Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.*
2. **Diagnostic columns prohibition** — *Calibration / threshold-sweep / directional-comparison columns are diagnostic-only.*
3. **γ closure preservation** — *Phase 24 γ hard-close (PR #279) is unmodified.*
4. **Production-readiness preservation** — *X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure) remains untouched.*
5. **NG#10 / NG#11 not relaxed** — entry-side budget cap and diagnostic-vs-routing separation rule remain in force.
6. **Phase 26 scope** — *Phase 26 is NOT a continuation of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed; primary research lever is label / target design, NOT feature class.*

---

## 10. Required unit tests for 26.0a-β

| # | Test | Purpose |
|---|---|---|
| 1 | `test_l3_label_construction_deterministic` | Reproducibility: same input → same label |
| 2 | `test_l3_base_pnl_is_mid_to_mid_long` | D-3.1 / §3.1 binding: base PnL = `mid_exit − mid_entry` for long |
| 3 | `test_l3_base_pnl_is_mid_to_mid_short` | §3.1 binding: base PnL = `mid_entry − mid_exit` for short |
| 4 | `test_l3_spread_subtracted_exactly_once` | **No double-counting** of spread (§3.1 binding) |
| 5 | `test_l3_entry_only_spread_subtracts_once_factor` | D-4 (a): factor = 1 |
| 6 | `test_l3_round_trip_spread_subtracts_twice_factor` | D-4 (b): factor = 2 |
| 7 | `test_l3_inherits_triple_barrier_K_FAV_K_ADV` | D-3: K_FAV=1.5 / K_ADV=1.0 inherited |
| 8 | `test_l3_horizon_expiry_uses_M5_close_mark_to_market` | D-1: horizon expiry mark-to-market on M5 close |
| 9 | `test_l3_label_excludes_mfe_mae` | D-2: realised exit PnL only |
| 10 | `test_l3_atr_normalised_scale` | D-5 (b): `label = label_pre_norm / atr_at_signal_pip` |
| 11 | `test_l3_raw_pip_scale` | D-5 (a): no ATR normalisation |
| 12 | `test_l3_winsorise_thresholds_fit_on_train_only` | D-6 (b): train-only-fit guard (mandatory; analogous to 25.0f-α F5-c tercile guard) |
| 13 | `test_l3_winsorise_does_not_touch_realised_pnl_for_harness` | **Winsorisation applies ONLY to training target y, NOT to realised PnL fed to 8-gate harness** (§3 D-6 binding statement) |
| 14 | `test_l3_winsorise_disabled_passes_through` | D-6 (a) baseline |
| 15 | `test_sweep_grid_has_24_cells` | §4 invariant |
| 16 | `test_lightgbm_uses_fixed_conservative_config` | §4.1 binding: no default hyperparams |
| 17 | `test_lightgbm_defer_path_when_not_importable` | §4.1: 16-cell graceful path |
| 18 | `test_cell_and_threshold_selection_uses_validation_only` | §5.3 selection rule |
| 19 | `test_verdict_tree_h2_pass_alone_not_adopt` | §7 invariant |
| 20 | `test_verdict_tree_h1_meaningful_threshold_010` | §6 H1 two-tier (ρ ≥ 0.10) |
| 21 | `test_verdict_tree_h1_weak_band_005_to_010` | §6 H1 two-tier weak band |
| 22 | `test_h3_baseline_constant_phase25_best_minus_0192` | H3 reference value hardcoded |
| 23 | `test_regression_diagnostic_returns_r2_pearson_spearman` | §8 |
| 24 | `test_no_diagnostic_columns_in_feature_set` | Inheritance: PROHIBITED_DIAGNOSTIC_COLUMNS leakage prohibition |

---

## 11. Files for 26.0a-β (binding declaration)

```
scripts/stage26_0a_l3_eval.py             # ~1000–1300 lines
tests/unit/test_stage26_0a_l3_eval.py     # ~24 unit tests per §10
artifacts/stage26_0a/eval_report.md       # ~280–330 lines
.gitignore                                # +1 stanza for raw artifacts
```

---

## 12. PR chain reference

```
Phase 26 begin:
  #299 (Phase 26 kickoff)
  → #300 (Phase 26 first-scope review — recommends L-3)
  → [user explicitly confirms L-3 + authorises 26.0a-α]
  → THIS PR (26.0a-α L-3 design memo)
  → [user explicitly authorises 26.0a-β implementation]
  → 26.0a-β L-3 eval (separate PR; binding contract = THIS PR)
  → review post-26.0a (separate PR)
  → ... (sub-phase chain)
```

---

## 13. What this PR will NOT do

- ❌ Implement any L-3 label / dataset / eval code.
- ❌ Run any sweep, generate any artifact under `artifacts/stage26_0a/`.
- ❌ Modify any prior verdict (Phase 25 evals / routing reviews / closure; Phase 26 kickoff / first-scope review).
- ❌ Pre-approve production deployment of any L-3 model.
- ❌ Relax NG#10 / NG#11.
- ❌ Modify γ closure (PR #279).
- ❌ Touch existing artifacts (stage25_0a / 0b / 0c / 0d / 0e / 0f remain intact).
- ❌ Update MEMORY.md.
- ❌ Auto-route to 26.0a-β implementation. The next PR opens only on explicit user authorisation.
- ❌ Foreclose L-1 / L-2 / L-4 (admissible follow-up candidates per #300).
- ❌ Foreclose F4 / F6 / F5-d / F5-e (Phase 25 deferred extensions).
- ❌ Change K_FAV / K_ADV barrier geometry (inherited at 1.5 / 1.0 per #299 §5).
- ❌ Add new dependencies. LightGBM is already in the environment; if it were missing, §4.1 specifies the 16-cell graceful deferral path.

---

## 14. Sign-off / 26.0a-β binding requirements

This memo is the **binding contract** for 26.0a-β. The 26.0a-β implementation PR must:

- Construct the L-3 label strictly per §3 (D-1..D-6) with the user-approved resolutions; **subtract spread exactly once per §3.1; mid-to-mid base PnL per §3.1; long/short formulas explicit**.
- Run the 24-cell sweep per §4. LightGBM cells use §4.1 fixed conservative config; if LightGBM is not importable, defer 8 cells and run 16 with the eval_report noting the deferral.
- Apply the validation-only cell-and-threshold selection rule per §5.3; touch the test set exactly once on the val-selected (cell, threshold) pair.
- Test the four hypotheses per §6 (H1 two-tier; H2 / H3 / H4) against the eval harness per §5.
- Include regression diagnostics per §8 (diagnostic-only; explicitly labelled).
- Apply the verdict tree per §7 — H2 PASS alone is **NOT** ADOPT_CANDIDATE; H1-weak PASS only is REJECT_WEAK_SIGNAL_ONLY.
- Honour all six mandatory clauses per §9 verbatim in `eval_report.md`.
- Include all 24 unit tests per §10. Especially `test_l3_spread_subtracted_exactly_once` (no double-counting) and `test_l3_winsorise_does_not_touch_realised_pnl_for_harness` (winsorisation scope) are mandatory.
- NOT relax NG#10 / NG#11; NOT modify γ closure; NOT touch stage25_0a/0b/0c/0d/0e/0f artifacts; NOT add new dependencies.

This kickoff PR stops here. The 26.0a-β implementation PR opens only on the user's separate explicit authorisation.
