# Phase 27.0b-α — S-C TIME Penalty Design Memo

**Type**: doc-only design memo (binding contract for the eventual Phase 27.0b-β eval)
**Branch**: `research/phase27-0b-alpha-s-c-time-penalty-design`
**Base**: master @ 84e7b76 (post-PR #316 Phase 27 kickoff merge)
**Pattern**: analogous to 26.0c-α (PR #308) / 26.0d-α (PR #312) design-memo structure with the **α sweep** as the new substantive axis
**Status**: design memo only — does NOT initiate 27.0b-β implementation
**Stop condition**: design memo merged → 27.0b-β implementation in a SEPARATE later instruction

---

## 0. Approval semantics (binding read-first)

> *Squash-merge approval accepts this design memo as the binding contract for the eventual Phase 27.0b-β S-C TIME penalty eval. It does NOT by itself authorise 27.0b-β implementation. The user explicitly authorises the 27.0b-β implementation PR in a separate later instruction.*

Same approval-then-defer pattern as #308 (26.0c-α) / #312 (26.0d-α) and Phase 27 kickoff (PR #316).

---

## 1. Phase 27.0b framing

Phase 27.0b is the **first substantive Phase 27 sub-phase** following the Phase 27 kickoff (PR #316). The tested intervention is the **score-objective α sweep on S-C = P(TP) − P(SL) − α·P(TIME) over α ∈ {0.0, 0.3, 0.5, 1.0}**, evaluated under all other Phase 27 binding inputs held fixed.

| Held fixed | Source |
|---|---|
| Feature family = R7-A (`pair, direction, atr_at_signal_pip, spread_at_signal_pip`) | Phase 27 kickoff §4 R7-A admissibility at kickoff |
| Label class = L-1 ternary {TP=0, SL=1, TIME=2} | 26.0c-α (PR #308) §2.3 inherited |
| Model class = fixed conservative LightGBM multiclass | 26.0c-α §4.1 / #309 inherited; `class_weight=balanced` |
| Realised-PnL harness = inherited bid/ask executable | Phase 26 D-1 binding from #309 / #313 |
| Threshold family = quantile-of-val {5, 10, 20, 30, 40}% PRIMARY | Phase 26 family inherited |
| Verdict ladder = H1-weak / H1-meaningful / H2 / H3 / H4 unchanged | Phase 26 family |
| ADOPT_CANDIDATE wall = H2 PASS path → PROMISING_BUT_NEEDS_OOS only | Phase 27 kickoff §10 |

> *27.0b is NOT a model-class comparison, NOT a feature widening, NOT a calibration test, NOT a label-class redesign. It tests one axis in isolation: whether explicitly penalising the TIME class share of the picker output produces an informative score → PnL ranking on test (Channel B lever from Phase 26 #314 §3 / Phase 27 kickoff §1).*

---

## 2. Inherited bindings (verbatim from Phase 27 kickoff §3)

| Item | Inherited from | Inheritance status into 27.0b |
|---|---|---|
| 25.0a-β path-quality dataset | Phase 25 #284..#296 | unchanged |
| 70/15/15 chronological split | Phase 26 family | unchanged |
| Triple-barrier inputs (K_FAV=1.5×ATR, K_ADV=1.0×ATR, H_M1=60) | Phase 25 / Phase 26 | unchanged |
| `_compute_realised_barrier_pnl` (bid/ask executable harness) | `scripts/stage25_0b_f1_volatility_expansion_eval.py` | unchanged; D-1 binding preserved |
| `precompute_realised_pnl_per_row` (cell-independent cache) | `scripts/stage26_0b_l2_eval.py` | inherited unchanged |
| 8-gate metrics + `gate_matrix` | `stage25_0b` | unchanged |
| H1-weak / H1-meaningful / H2 / H3 / H4 thresholds | Phase 26 family | unchanged (0.05 / 0.10 / 0.082 + 180 / -0.192 / 0) |
| `build_l1_labels_for_dataframe` | `scripts/stage26_0c_l1_eval.py` | inherited unchanged |
| LightGBM fixed conservative multiclass config | 26.0c-α §4.1 / #309 | unchanged |
| R7-A feature pipeline (one-hot `pair + direction`; numeric passthrough `atr + spread`) | #313 `build_pipeline_lightgbm_multiclass_widened` | **R7-A FIXED; 27.0b does NOT add features** |
| `compute_pair_concentration` | `stage26_0b` | inherited unchanged |
| Quantile-of-val cutoff fitting + A0-prefilter + tie-breaker chain | Phase 26 family | unchanged |
| Cross-cell verdict aggregation (agree → single ; disagree → split, no auto-resolution) | 26.0c-α §7.2 | inherited |

---

## 3. S-C score-objective definition (the new Phase 27.0b axis)

The S-C score function per row is:

```
S-C(row, α) = P(TP)[row] − P(SL)[row] − α · P(TIME)[row]
```

where `P(TP)`, `P(SL)`, `P(TIME)` are the multiclass LightGBM `predict_proba` outputs (`P(TP) + P(SL) + P(TIME) = 1` row-wise per the LightGBM multiclass contract).

### 3.1 Boundary observations (informational; D-T4 binding)

| α value | S-C reduces to | Note |
|---|---|---|
| **α = 0.0** | `P(TP) − P(SL)` | exactly equals S-B (Phase 26 C02 picker; #313). This is the sanity-check cell — α=0.0 must reproduce R6-new-A C02's val-selected metrics within tolerance (§13 / D-T3). |
| α = 0.3 | (new) | partial TIME penalty |
| α = 0.5 | (new) | mid TIME penalty |
| **α = 1.0** | `P(TP) − P(SL) − P(TIME) = P(TP) − (1 − P(TP)) = 2·P(TP) − 1` | **monotone transform of P(TP)** (= Phase 26 C01 picker). Same val-selected ranking as S-A; the val-selected (cell\*, q\*) outcome under α=1.0 is informationally comparable to Phase 26 R6-new-A C01 (test Spearman +0.0226). The quantile cutoff value will differ (scalar shift + scaling) but the trade set selected at the 5%/10%/20%/30%/40% top quantile is identical to running S-A under the same cutoff. |

> *α=1.0 is included to bound the α grid at the full-penalty end. Because of its monotone equivalence to P(TP), it is NOT an independent score family — it is the boundary cell tied to S-A. This is informational; the formal verdict tree still evaluates α=1.0 like any other cell.*

### 3.2 Range

Given `P(TP), P(SL), P(TIME) ∈ [0,1]` and they sum to 1, S-C ∈ `[-1 − α, 1]`. For α=0.5, S-C ∈ `[-1.5, 1]`. The quantile-of-val cutoff fitting handles this automatically (val-only scalar cutoff applied to test).

---

## 4. α grid (closed 4-point; D-T1 binding)

The α grid is **closed at 4 points**. No α extension, no other S-variant combinations, no model variation, no calibration variation, no feature variation. This is the smallest grid that captures the α axis cleanly while including the two boundary sanity cells.

| Cell ID | α | S-C reduces to | Role |
|---|---|---|---|
| **C-α0** | 0.0 | S-B (= Phase 26 C02 picker) | sanity-check vs Phase 26 R6-new-A C02 baseline (#313); HALT if mismatch (§13) |
| **C-α03** | 0.3 | (new) | partial TIME penalty |
| **C-α05** | 0.5 | (new) | mid TIME penalty |
| **C-α10** | 1.0 | monotone transform of P(TP) (≡ S-A) | full TIME penalty boundary; informationally tied to Phase 26 C01 |

Total: **4 formal cells × 5 quantile candidates = 20 (cell, q) pairs evaluated**. Each cell sweeps the inherited quantile-of-val {5, 10, 20, 30, 40}%.

### 4.1 Explicitly NOT in the α grid (out of scope for 27.0b)

- α ∈ {0.1, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9} (intermediate values not included)
- α > 1.0 (super-full penalty)
- α < 0.0 (TIME reward instead of penalty)
- Continuous-α optimisation
- α-conditional model retraining (model is fit once; α changes the picker only)

Any α extension beyond the 4-point closed grid requires a separate sub-phase design memo.

---

## 5. Realised-PnL cache (inherited D-1 binding)

> *D-1 binding inherited verbatim from Phase 26 #309 §8 / #313 / Phase 27 kickoff §3: formal realised-PnL scoring uses the inherited `_compute_realised_barrier_pnl` (bid/ask executable). Mid-to-mid PnL appears only in sanity probe / label diagnostic; NEVER as the formal realised-PnL metric.*

Re-use `precompute_realised_pnl_per_row` from `scripts/stage26_0b_l2_eval.py` unchanged. Cell-independent precomputation cache. The single model fit (R7-A pipeline, L-1 multiclass) is run **once**; the 4 α cells differ only in their picker scores computed from the same `predict_proba` outputs.

---

## 6. Picker / threshold family

### 6.1 Picker per cell (single picker per α; D-T2 binding)

Per cell, the picker is the single S-C(α) function for that cell's α. **No multiple pickers per α.** This isolates the α sweep — additional pickers (e.g., a companion P(TP) cell per α) would muddle the axis.

### 6.2 Threshold family — PRIMARY formal verdict basis

Quantile-of-val {5, 10, 20, 30, 40}%. Val-fit scalar cutoff applied to test predictions once.

### 6.3 Threshold family — DIAGNOSTIC-ONLY

Absolute thresholds on S-C per α. Since S-C range varies with α, the diagnostic absolute thresholds are constructed per-α:

- α=0.0: same as Phase 26 C02 P(TP)-P(SL) absolute thresholds: `{0.0, 0.05, 0.10, 0.15}` (inherited)
- α=0.3 / α=0.5: adapted from α=0.0 by shifting the centre by the empirical mid-quantile shift in the val distribution; reported diagnostically only
- α=1.0: same as Phase 26 C01 P(TP) absolute thresholds: `{0.30, 0.40, 0.45, 0.50}` (mapped via the `2·P(TP) − 1` transform: `{-0.40, -0.20, -0.10, 0.0}`)

All absolute thresholds are DIAGNOSTIC-ONLY per clause 2 binding; NOT in formal verdict routing.

---

## 7. Formal cell grid (4 cells × 5 quantiles = 20 records)

| Cell ID | α | Picker | Calibration | Cutoff family (formal) |
|---|---|---|---|---|
| **C-α0** | 0.0 | S-C(α=0.0) ≡ S-B | raw probability | quantile-of-val {5, 10, 20, 30, 40}% |
| **C-α03** | 0.3 | S-C(α=0.3) | raw probability | quantile-of-val 5/10/20/30/40% |
| **C-α05** | 0.5 | S-C(α=0.5) | raw probability | quantile-of-val 5/10/20/30/40% |
| **C-α10** | 1.0 | S-C(α=1.0) ≡ monotone(P(TP)) | raw probability | quantile-of-val 5/10/20/30/40% |

### 7.1 Val-selection rule (inherited verbatim from Phase 26 family)

Per cell:
1. Apply A0-prefilter: drop quantiles whose val trade count is below `A0_MIN_ANNUAL_TRADES × VAL_SPAN_YEARS`.
2. Among survivors, pick the quantile maximising val realised Sharpe.
3. Tie-breakers (in order): val realised ann_pnl → lower val MaxDD → smaller q% (more selective).

Then across cells:
1. Apply the same A0-prefilter + tie-breaker chain across the 4 cells' val-selected (cell, q) records.
2. Result: a single val-selected (cell\*, q\*, α\*) record. Test set is touched once on this record.

### 7.2 Cross-cell verdict aggregation (per D-T8 / 26.0c-α §7.2)

Each of the 4 cells produces its own verdict via the H1/H2/H3/H4 ladder. Cross-cell aggregation:
- **Agree**: all 4 cells produce the same verdict → single aggregate verdict.
- **Disagree**: split branches reported separately; no auto-resolution.

---

## 8. Hypothesis ladder + verdict tree (UNCHANGED from Phase 26 family)

| Hypothesis | Pass threshold | Notes |
|---|---|---|
| **H1-weak** | val-selected cell test Spearman(S-C(α\*), realised_pnl) > 0.05 | formal H1 binding inherited from Phase 26 |
| **H1-meaningful** | ≥ 0.10 | |
| **H2** | test realised Sharpe ≥ +0.082 AND ann_pnl ≥ +180 | Phase 26 binding |
| **H3** | test realised Sharpe > -0.192 | Phase 25 F1 best baseline; unchanged |
| **H4** | test realised Sharpe ≥ 0 | |

Verdict tree branches:
- REJECT_NON_DISCRIMINATIVE / H1_WEAK_FAIL → H1-weak FAIL
- REJECT_WEAK_SIGNAL_ONLY / H1_WEAK_PASS_ONLY → H1-weak but not H1-meaningful
- REJECT_BUT_INFORMATIVE_IMPROVED / H1m_PASS_H2_FAIL_H3_PASS → H1-meaningful + H2 FAIL + H3 PASS
- REJECT_BUT_INFORMATIVE_FLAT / H1m_PASS_H2_FAIL_H3_FAIL → H1-meaningful + H2 FAIL + H3 FAIL
- **PROMISING_BUT_NEEDS_OOS** / H2_PASS_AWAITS_A0_A5 → H2 PASS

> *27.0b-β cannot mint ADOPT_CANDIDATE per Phase 27 kickoff §10 binding. H2 PASS path resolves to PROMISING_BUT_NEEDS_OOS pending a SEPARATE A0-A5 8-gate harness PR.*

---

## 9. Diagnostic columns (binding: ALL diagnostic-only)

All items below are diagnostic-only per clause 2 binding. **None enter formal verdict routing**:

| Diagnostic | Source / scope |
|---|---|
| AUC of P(TP) one-vs-rest on test | inherited from #309 |
| Cohen's κ on test (multiclass) | inherited |
| Multiclass logloss on test | inherited |
| Confusion matrix on test | inherited |
| Per-class accuracy on test | inherited |
| CONCENTRATION_HIGH 80% flag | inherited from #313 |
| Absolute-threshold sweep per α | per §6.3 above; per-α grid |
| Feature importance (4-bucket: pair / direction / atr_at_signal_pip / spread_at_signal_pip) | inherited from #313 / Decision D10 |
| **NEW: per-pair Sharpe contribution table** | per Phase 27 kickoff §6 / D-T7; required in every 27.0b-β report |
| **NEW: α-monotonicity diagnostic** | required per D-T6; reports whether realised Sharpe / formal Spearman varies monotonically (or non-monotonically) with α |
| **NEW: α-comparison side-by-side table** | the 4 α cells' val-selected (cell, q) records side-by-side; informational |

---

## 10. Pair-concentration policy

| Element | Status |
|---|---|
| CONCENTRATION_HIGH 80% flag | inherited unchanged from #313; **diagnostic-only**; NOT in formal verdict |
| **Per-pair Sharpe contribution table** (NEW; required per Phase 27 kickoff §6 + D-T7) | required in 27.0b-β `eval_report.md`; per-pair: `n_trades`, realised Sharpe, share of total PnL, share of total trades; computed on val-selected (cell\*, q\*, α\*) on test; diagnostic-only; NOT in formal verdict routing |
| Per-pair-share regularised cell selection | NOT opted-in for 27.0b (default per Phase 27 kickoff §6); the val-selection rule consumes only Sharpe / ann_pnl / MaxDD / q% (no per-pair-share input) |

---

## 11. Sanity probe (extends 26.0c-α §10 + #313 §12.2)

| Check | Source | HALT condition |
|---|---|---|
| Class priors TP / SL / TIME per split | 26.0c-α §10 | any class < 1% of total rows |
| Per-pair TIME-class share on train | 26.0c-α §10 | any pair > 99% TIME share |
| Realised-PnL cache basis check (bid/ask executable confirmed via `_compute_realised_barrier_pnl` signature + body inspection) | 26.0c-α §10 / D-1 | inherited harness basis violated |
| Mid-to-mid PnL distribution per class on train (diagnostic) | 26.0c-α §10 | report-only |
| R7-A new-feature NaN rate per split | #313 §12.2 | NaN rate > 5% per split for either feature |
| R7-A new-feature positivity (`atr_at_signal_pip > 0`; `spread_at_signal_pip ≥ 0`) | #313 §12.2 | positivity violated on ≥ 1% of rows |
| **NEW: P(TIME) distribution diagnostic** (mean / p5 / p50 / p95 per pair on val + test) | 27.0b-α specific per D-T5 | **report-only; no HALT threshold** |

HALT raises `SanityProbeError` with the failing condition before the full sweep starts. Same pattern as #309 / #313.

> *The new P(TIME) distribution diagnostic is report-only (per D-T5); it surfaces the test-time distribution of TIME-class predicted probabilities that S-C explicitly penalises, but it does NOT halt the sweep. A future sub-phase may convert it into a HALT threshold after baseline data is available.*

---

## 12. Mandatory comparison section in 27.0b-β report

The 27.0b-β `eval_report.md` MUST include the following four mandatory sections in this order.

### 12.1 Baseline comparison table (vs Phase 26 L-1 C02 + R6-new-A C02)

| Aspect | Phase 26 L-1 C02 (#309) | Phase 26 R6-new-A C02 (#313) | Phase 27 27.0b val-selected (cell\*, α\*) |
|---|---|---|---|
| Feature set | pair + direction | + atr + spread (R7-A) | + atr + spread (R7-A fixed) |
| Score objective | S-B = P(TP) − P(SL) | S-B | S-C(α\*) per val-selection |
| Test n_trades | 42,150 | 34,626 | TBD |
| Test Sharpe | -0.2232 | -0.1732 | TBD |
| Test ann_pnl (pip) | -237,310.8 | -204,664.4 | TBD |
| Test Spearman (formal H1) | -0.1077 | -0.1535 | TBD |
| Pair concentration | 100% USD_JPY | multi-pair | TBD |
| Verdict | REJECT_NON_DISCRIMINATIVE | REJECT_NON_DISCRIMINATIVE (+ YES_IMPROVED identity-break) | TBD |

### 12.2 α=0.0 sanity-check declaration (D-T3 binding; HALT path)

The 27.0b-β eval must explicitly confirm that **C-α0 (α=0.0) reproduces Phase 26 R6-new-A C02's val-selected metrics within numerical tolerance**:

| Metric | Tolerance | Source baseline |
|---|---|---|
| Test n_trades | **exact match (integer)** | 34,626 (#313) |
| Test realised Sharpe | abs diff ≤ 1e-4 | -0.1732 (#313) |
| Test realised ann_pnl (pip) | abs diff ≤ 0.5 pip | -204,664.4 (#313) |

If any of the three tolerances is violated → **HALT with `BaselineMismatchError`**. The cell wiring or data inheritance has drifted from #313; further sweep would produce unreliable comparisons.

This is the load-bearing wiring confirmation that 27.0b inherits the Phase 26 framework correctly.

### 12.3 α-monotonicity diagnostic (D-T6 binding; diagnostic-only)

For each α ∈ {0.0, 0.3, 0.5, 1.0}, report on val-selected (cell, q):
- Val realised Sharpe
- Val realised ann_pnl
- Test realised Sharpe
- Test realised ann_pnl
- Test formal Spearman

Then declare whether the sequence is monotonic (increasing / decreasing / non-monotonic / mixed). Diagnostic-only; NOT in formal verdict.

### 12.4 Per-pair Sharpe contribution table (D-T7 binding; diagnostic-only)

For the val-selected (cell\*, α\*, q\*) record on test, report per pair:
- `n_trades`
- Realised Sharpe (per pair)
- Share of total PnL (per pair)
- Share of total trades (per pair)

Diagnostic-only; NOT in formal verdict.

---

## 13. Identity-comparison policy (α=0.0 ≡ S-B sanity check)

Per §12.2: **C-α0 must reproduce R6-new-A C02 within tolerance, OR HALT**. This is the load-bearing wiring confirmation that 27.0b inherits the Phase 26 framework correctly.

Reasoning: with α=0.0, S-C = P(TP) − P(SL) ≡ S-B ≡ Phase 26 R6-new-A C02 picker. With R7-A held fixed, L-1 label held fixed, model class held fixed, dataset / split / harness all inherited unchanged, the val-selected metrics on C-α0 must coincide with R6-new-A C02 exactly (n_trades; ≤ 1e-4 on Sharpe; ≤ 0.5 pip on ann_pnl). If they do not, something in the inheritance chain has drifted.

The HALT path uses a `BaselineMismatchError` exception with the failing metric and observed-vs-baseline values.

---

## 14. Implementation outline for 27.0b-β (NOT this PR)

| Item | Detail |
|---|---|
| Script | `scripts/stage27_0b_s_c_time_penalty_eval.py` (~1700-1900 lines; closely modelled on `scripts/stage26_0d_r6_new_a_eval.py` from #313 with the α grid as the new substantive axis) |
| Tests | `tests/unit/test_stage27_0b_s_c_time_penalty_eval.py` (~40-45 tests; 6+ NEW 27.0b-specific tests: α grid closed-set enforcement, S-C formula correctness, α=0.0 ≡ S-B identity, α=1.0 ≡ monotone-of-P(TP) equivalence, BaselineMismatchError trigger on α=0.0 mismatch, per-pair Sharpe contribution table generator, α-monotonicity diagnostic format) |
| Sanity probe | per §11; HALTs on the inherited Phase 26 conditions; reports the new P(TIME) distribution diagnostic without HALT |
| Eval report | `artifacts/stage27_0b/eval_report.md` with mandatory §12.1 baseline comparison + §12.2 α=0.0 sanity-check declaration + §12.3 α-monotonicity diagnostic + §12.4 per-pair Sharpe contribution table |
| Runtime estimate | ~20-35 min (single model fit at R7-A; then 4 cells × 5 quantiles using cached `predict_proba` outputs) |
| `.gitignore` entries | `artifacts/stage27_0b/{run.log, sweep_results.parquet, sweep_results.json, aggregate_summary.json, val_selected_cell.json, sanity_probe.json}` |

---

## 15. Mandatory clauses (clauses 1-5 verbatim from Phase 27 kickoff §8; clause 6 = Phase 27 kickoff §8 verbatim)

Clauses 1-5 inherited verbatim from Phase 27 kickoff §8 (which inherited them from Phase 26 closure §8 / #299 chain). Clause 6 = Phase 27 kickoff §8 clause 6 **verbatim** (the canonical source-of-truth for Phase 27 clause 6 remains PR #316 / Phase 27 kickoff).

1. **Phase framing.** ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness. *[unchanged]*
2. **Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison / classification-quality / feature-importance / per-pair-Sharpe-contribution / α-monotonicity columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them. *[unchanged; α-monotonicity explicitly added to the diagnostic-only enumeration for 27.0b]*
3. **γ closure preservation.** Phase 24 γ hard-close (PR #279) is unmodified. *[unchanged]*
4. **Production-readiness preservation.** X-v2 OOS gating remains required before any production deployment. Production v9 20-pair (Phase 9.12 closure tip `79ed1e8`) remains untouched. Phase 22 frozen-OOS contract remains required for any ADOPT_CANDIDATE → production transition. *[unchanged]*
5. **NG#10 / NG#11 not relaxed.** *[unchanged]*
6. **Phase 27 scope.** *Phase 27's primary axes are (a) feature widening beyond the Phase 26 R6-new-A 2-feature allowlist via per-family closed allowlists and (b) score-objective redesign beyond P(TP) / P(TP)-P(SL). Phase 27 is NOT a Phase 25 feature-axis sweep revival. R7-A (inherited from PR #311) is admissible at kickoff; R7-B / R7-C each require a SEPARATE Phase 27 scope-amendment PR; R7-D and R7-Other are NOT admissible under any Phase 27 scope amendment currently on the table. Score-objectives S-A / S-B / S-C are admissible at kickoff for formal evaluation. S-D (calibrated EV) is admissible in principle but deferred — it requires its own design memo specifying per-class conditional-PnL estimation, calibration policy, and selection-overfit handling before any formal eval. S-E (regression-on-realised-PnL) requires a SEPARATE scope-amendment PR (model-class change). S-Other is NOT admissible. Phase 26 deferred-not-foreclosed items (L-4 / R6-new-B / R6-new-C / Phase 25 F4 / F6 / F5-d / F5-e) are NOT subsumed by Phase 27; they remain under their original phase semantics.* *[Phase 27 kickoff §8 verbatim]*

---

## 16. What this PR will NOT do

- ❌ Implement `scripts/stage27_0b_s_c_time_penalty_eval.py`
- ❌ Implement `tests/unit/test_stage27_0b_s_c_time_penalty_eval.py`
- ❌ Run any sweep or produce `artifacts/stage27_0b/*`
- ❌ Touch `.gitignore` for `artifacts/stage27_0b/*` (deferred to 27.0b-β PR)
- ❌ Modify `src/`, `scripts/` outside the design memo path, `tests/`, or `artifacts/`
- ❌ Extend the α grid beyond {0.0, 0.3, 0.5, 1.0}
- ❌ Add features to R7-A
- ❌ Authorise R7-B / R7-C / R7-D / R7-Other (each needs separate Phase 27 scope-amendment PR)
- ❌ Authorise S-D (calibrated EV; admissible but deferred per Phase 27 kickoff §5)
- ❌ Authorise S-E (regression-on-realised-PnL; requires separate scope-amendment PR)
- ❌ Authorise S-Other
- ❌ Change the model class away from fixed conservative LightGBM multiclass
- ❌ Change the label class away from L-1 ternary
- ❌ Modify γ closure (PR #279)
- ❌ Modify X-v2 OOS gating or Phase 22 frozen-OOS contract
- ❌ Pre-approve production deployment
- ❌ Modify any prior verdict (Phase 25 / Phase 26 / Phase 27 kickoff)
- ❌ Foreclose any Phase 27 admissible candidate (R7-B/C, S-D, S-E, other α grids in later sub-phases, model-class variations, calibration variations)
- ❌ Foreclose Phase 26 deferred-not-foreclosed items (L-4 / R6-new-B / R6-new-C; preserved under Phase 26 semantics)
- ❌ Mint ADOPT_CANDIDATE for 27.0b
- ❌ Mint PROMISING_BUT_NEEDS_OOS at the design-memo stage (verdict produced only by the eval PR)
- ❌ Update MEMORY.md
- ❌ Authorise the 27.0b-β implementation PR (separate later instruction)
- ❌ Auto-route to 27.0b-β implementation after merge

---

## 17. Sign-off

After this design memo merges:

- **27.0b-β implementation** is authorised only by a SEPARATE later user instruction.
- The 27.0b-β PR will implement `scripts/stage27_0b_s_c_time_penalty_eval.py` + `tests/unit/test_stage27_0b_s_c_time_penalty_eval.py` + `artifacts/stage27_0b/eval_report.md` with the mandatory §12 four-section comparison + α=0.0 BaselineMismatchError HALT path + α-monotonicity diagnostic + per-pair Sharpe contribution table.
- After 27.0b-β closure, a post-27.0b routing review will follow the Phase 26 #304 / #307 / #310 / #314 pattern.

**This PR stops here.**
