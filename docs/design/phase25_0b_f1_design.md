# Phase 25.0b-α — F1 Volatility Expansion / Compression Design Memo (binding contract for 25.0b-β)

Doc-only PR fixing the binding contract for 25.0b-β implementation
(F1: volatility expansion / compression breakout, the first feature
class evaluated under Phase 25 path-quality labels). **No code, no
eval, no implementation in this PR.**

> **Phase 25 framing inheritance** (from kickoff PR #280):
>
> *Phase 25 is not a hyperparameter-tuning phase. It is a label-and-
> feature-class redesign phase. Novelty must come from input feature
> class and label design.*
>
> The hyperparameters in this memo are **design constants** for F1.
> They are fixed before 25.0b-β implementation and **MUST NOT be
> retuned** during implementation. If F1's first run produces an
> unsatisfactory verdict, the path forward is documented redesign
> (separate PR with explicit justification), NOT silent retune.

## §1. Stage purpose

This memo locks the F1 feature class for 25.0b-β implementation:
- §3 feature definitions (formulae, windows, causality).
- §4 negative list — what F1 is NOT.
- §5 signal candidate generation (bidirectional).
- §6 model class (logistic regression + L2 + balanced; NOT LightGBM).
- §7 cell grid (24 cells; no directionality dimension).
- §8 validation split (70/15/15 chronological).
- §9 trade-decision threshold (selected on validation set only).
- §10 leakage guards (HARD invariants).
- §11 unit-test contract (≥ 13 tests).
- §12 reporting requirements.
- §13 mandatory clauses verbatim.
- §14 routing to 25.0b-β.

## §2. Scope

**In scope**: F1 binding contract for 25.0b-β.

**Explicitly out of scope**:
- Implementation of any feature, model, or eval (deferred to 25.0b-β).
- LightGBM exploration (deferred unless logistic AUC ≥ 0.55 on held-out test).
- Other feature classes F2-F6 (deferred to subsequent per-class PRs).
- Modifying 25.0a label dataset / thresholds.
- Modifying Phase 25 kickoff (#280) / 25.0a-α (#281) / 25.0a-β (#282).
- Modifying 22.x / 23.x / 24.x docs / artifacts.
- Relaxing NG#10 / NG#11.
- Pre-approving any production deployment.

## §3. F1 feature class definition (binding)

F1 is **volatility-derivative features** as primary trigger. The
trigger is volatility regime transition (compression → expansion).
Direction-of-trade is informed by secondary context (recent realised
return sign), NOT by price-level band touches.

### §3.1 Feature catalogue (6 families; numerical params FIXED)

All windows are computed with strict `shift(1)` causality so signal
bar `t`'s features use only bars ≤ `t-1`.

#### f1_a — Realised Volatility (RV) per timeframe

For each TF ∈ {M5, M15, H1}:
- Aggregate M1 → TF using existing `aggregate_m1_to_tf` (M30/H1 added
  to `TF_MINUTES` dict if needed; or M5/M15 used directly with
  longer windows).
- Compute log-return on TF mid-close: `r[t] = log(mid_c[t]) - log(mid_c[t-1])`.
- RV[t] = sqrt(sum(r[t-N+1..t]^2)) where N is the TF-specific window:

| TF | N | Period |
|---|---|---|
| M5 | 12 | 1h |
| M15 | 8 | 2h |
| H1 | 24 | 1d |

Apply `shift(1)` so signal bar t's RV uses bars [t-N..t-1].

Output: `f1_a_rv_M5`, `f1_a_rv_M15`, `f1_a_rv_H1` (3 features).

#### f1_b — Compression percentile

For each TF, compute the rolling quantile rank of current RV vs the
trailing 100-bar window of RV:

```
f1_b_compression_pct[t] = rank(rv[t-1] | rv[t-100..t-2]) / 100
```

Lower value (closer to 0) = more compressed (current vol below
trailing distribution).

Output: `f1_b_compression_pct_M5`, `f1_b_compression_pct_M15`,
`f1_b_compression_pct_H1` (3 features).

#### f1_c — Expansion ratio

For each TF:
```
f1_c_expansion_ratio[t] = mean(rv[t-4..t-1]) / mean(rv[t-50..t-5])
```

Numerator = recent 4 bars; denominator = trailing baseline 5..50 (45
bars). Ratio > 1 = recent vol higher than baseline; ratio < 1 =
compression.

Output: `f1_c_expansion_ratio_M5`, `f1_c_expansion_ratio_M15`,
`f1_c_expansion_ratio_H1` (3 features).

#### f1_d — Vol-of-vol

For each TF, std of RV over rolling 100-bar window:

```
f1_d_vol_of_vol[t] = std(rv[t-100..t-1])
```

Output: `f1_d_vol_of_vol_M5`, `f1_d_vol_of_vol_M15`,
`f1_d_vol_of_vol_H1` (3 features).

#### f1_e — Range compression score

For each TF:
```
f1_e_range_score[t] = (max(high[t-N..t-1]) - min(low[t-N..t-1])) / mean(ATR[t-N..t-1])
```

with N matching the TF (M5: 12, M15: 8, H1: 24). ATR is the existing
causal ATR helper from stage23_0a applied per TF.

Lower value = tighter range relative to its volatility baseline =
more compressed.

Output: `f1_e_range_score_M5`, `f1_e_range_score_M15`,
`f1_e_range_score_H1` (3 features).

#### f1_f — Recent return sign (secondary directional context only)

```
f1_f_return_sign[t] = sign(close_M5[t-1] - close_M5[t-13])  # 12 M5 bars = 1h
```

Output: `f1_f_return_sign` (1 feature; integer ∈ {-1, 0, +1}).

> **Binding constraint**: f1_f is **secondary directional context
> only**. A cell MUST NOT use f1_f as the sole trigger. The
> compression/expansion features (f1_b, f1_c, f1_e) are the primary
> triggers; f1_f informs direction-of-trade but does not generate
> signals on its own.

### §3.2 Total feature count

3 + 3 + 3 + 3 + 3 + 1 = **16 base features** + 2 categorical
covariates (`pair`, `direction`) = **18 columns** in the model
input matrix.

## §4. Negative list — what F1 IS NOT (binding)

The 25.0b-β implementation MUST NOT introduce ANY of the following
as a primary trigger or as a model input:

1. **Donchian band breakout** on any timeframe (NG#1).
2. **Rolling z-score** on close price (NG#2).
3. **Bollinger band touch** as a primary trigger (degenerate
   Donchian; NG#1 by analogy).
4. **Price crosses N-day high/low** signal (NG#1 by analogy).
5. **Moving-average crossover** alone.
6. **Calibration-only** / probability-smoothing-only signal (NG#12).
7. **f1_f as standalone primary trigger** (per §3.1 binding constraint).
8. **Pair / time-of-day / WeekOpen filter as primary edge** (NG#8-10).

The 25.0b-β script's design preamble must contain a one-paragraph
justification for each F1 feature explaining why it is NOT a
re-encoding of any §4 NG'd route.

## §5. Signal candidate generation (bidirectional)

Per direction §2 (bidirectional). For each (pair, signal_ts) emitted
by 25.0a:

- Emit **2 model-input rows**: one for `direction=long`, one for
  `direction=short`.
- The features (f1_a..f1_e) are **identical** for both rows; only
  the categorical covariates `direction` and the corresponding label
  (joined from 25.0a) differ.
- Model produces P(path_quality_positive | features, direction) per
  row.
- Trade decision: at each signal_ts, pick the direction with the
  higher P(positive). Trade only if max(P_long, P_short) ≥ threshold
  (§9). If both are below threshold, no trade.

Long-format dataset shape:
```
columns: pair, signal_ts, direction, label, f1_a_rv_M5, ..., f1_f_return_sign
2 rows per signal_ts emitted from 25.0a
```

## §6. Model class (locked)

- **First-class model**: `sklearn.linear_model.LogisticRegression`
  with:
  - `penalty='l2'`
  - `C=1.0` (default L2 strength)
  - `class_weight='balanced'` (handles ~0.187 positive rate)
  - `solver='lbfgs'`, `max_iter=1000`
  - `random_state=42` (reproducibility)
- **Standardisation**: train-set-only `StandardScaler` mean/std;
  applied verbatim to val/test. NO refit on val/test.
- **Categorical handling**: `pair` (20 levels) and `direction`
  (2 levels) one-hot encoded; encoder fit on train only.
- **LightGBM is NOT in scope for 25.0b**. If logistic produces
  held-out test AUC ≥ 0.55, LightGBM may be considered as a
  separate downstream PR (NOT 25.0b's responsibility).

## §7. Cell grid (24 cells; bidirectional locked)

Per direction §3, directionality is fixed (bidirectional) and not a
cell dimension.

| Dimension | Values | Count |
|---|---|---|
| Primary vol TF (which f1_a/b/c/e TF is the cell-defining "primary") | {M5, M15, H1} | 3 |
| Compression lookback (bars for f1_b's quantile window) | {50, 100} | 2 |
| Compression quantile threshold (for f1_b "compressed" label) | {0.10, 0.20} | 2 |
| Expansion ratio threshold (for f1_c "expanding" trigger) | {1.25, 1.50} | 2 |
| **Total** | | **24** |

### §7.1 Cell semantics

Each cell trains and evaluates a logistic regression model with the
SAME 16-feature catalogue but the cell's specific
compression/expansion thresholds determine **which signals are kept
in the dataset**:

- A signal_ts is admissible for a cell if:
  - `f1_b_compression_pct_<primary_TF>[t]` (computed with the cell's
    lookback) ≤ cell's compression quantile threshold (compression
    detected), AND
  - `f1_c_expansion_ratio_<primary_TF>[t]` ≥ cell's expansion ratio
    threshold (expansion just started).

Signals not meeting both conditions for the cell's primary TF are
dropped from that cell's dataset.

The model is then trained on the surviving rows. Cell-specific
admissibility filters but cell-shared feature catalogue.

### §7.2 Cell sweep size discipline (kickoff §10)

24 cells is within the kickoff §10 budget of 18-33 cells per
F-class. No expansion beyond 33 cells without a documented
multiple-testing justification in a follow-up PR.

## §8. Validation split (70/15/15 chronological; locked)

- **Train**: first 70% of 730d (≈ 511 days).
- **Validation**: next 15% (≈ 110 days). Used for threshold selection
  (§9) and any cell-specific decision before final test pass.
- **Test**: last 15% (≈ 110 days). **Held strictly until the final
  pass**. Touched ONCE in 25.0b-β. Re-running test set across
  hyperparameter retunes is FORBIDDEN.

Random splits are PROHIBITED. Calendar-date boundaries lock the
split.

## §9. Trade-decision threshold (validation-only selection)

Per direction §7:

- **Threshold candidates**: {0.20, 0.25, 0.30, 0.35, 0.40}.
- **Selection rule**: on the VALIDATION set, for each threshold,
  compute expected PnL proxy (sum of (label - 0 if not traded; +1
  if true positive; -spread if false positive) per row meeting
  threshold). Or equivalently: mean PnL_pip per traded row * trade
  count. Pick the threshold maximising val Sharpe proxy.
- **Selected threshold is FROZEN** before test-set evaluation.
- The test-set evaluation uses the validation-frozen threshold;
  threshold is NOT swept on test.

> **Mandatory in eval_report.md**: explicit lines stating
> *"threshold selected on validation only"* and *"test set touched
> once"*.

## §10. Leakage guards (HARD invariants)

### §10.1 25.0a diagnostic columns prohibition

The 25.0b-β model's feature matrix MUST NOT contain any of:
- `max_fav_excursion_pip`
- `max_adv_excursion_pip`
- `time_to_fav_bar`
- `time_to_adv_bar`
- `same_bar_both_hit`

A unit test enforces this.

### §10.2 Causality guards

- All f1_a..f1_f features MUST use `shift(1)` (or strictly past bars)
  in their rolling computations. The signal bar's own data MUST NOT
  enter its own feature.
- A unit test enforces causality on synthetic data: changing bar
  `t`'s value must NOT change feature[t]'s value.

### §10.3 Train/val/test boundary guard

- `StandardScaler.fit()` MUST be called on train set only. A unit
  test inspects the scaler's mean/std are identical when refit on
  train alone vs full dataset (sanity check that no leakage occurred
  during fitting).
- One-hot encoders for `pair` / `direction` similarly fit on train
  only.

### §10.4 NaN-warmup row drop

F1 features (especially f1_b / f1_d with 100-bar windows + f1_a's
lookback) require additional warmup beyond 25.0a's ATR_N=20 warmup.
Rows where ANY f1_a..f1_e feature is NaN MUST be dropped before
model training. f1_f is the only feature allowed to be 0 (sign of 0
return).

Drop counters required in eval_report.md (§12.10):
- `feature_nan_drop_count` overall + per pair
- `feature_nan_drop_rate` overall + per pair

## §11. Test contract (≥ 13 tests minimum)

The 25.0b-β implementation MUST include at least these tests:

### §11.1 Feature correctness (6 tests)

1. `test_f1_a_rv_correctness` — synthetic price series with known log-return sequence; assert RV matches closed-form value.
2. `test_f1_b_compression_pct_correctness` — synthetic series; assert quantile rank matches expected value.
3. `test_f1_c_expansion_ratio_correctness` — synthetic series; assert ratio = mean(recent 4) / mean(trailing 5..50).
4. `test_f1_d_vol_of_vol_correctness` — synthetic series; assert std of rolling RV matches.
5. `test_f1_e_range_score_correctness` — synthetic OHLC; assert score = range / mean(ATR).
6. `test_f1_f_return_sign_correctness` — synthetic; assert sign(close[t-1] - close[t-13]).

### §11.2 Causality (2 tests)

7. `test_features_use_only_past_bars_shift_1` — synthetic where bar t has extreme value; assert features at t are unchanged from a baseline computation that excludes bar t.
8. `test_features_no_lookahead_at_t_plus_1` — synthetic where bar t+1 has extreme value; assert features at t are unchanged.

### §11.3 Diagnostic-leakage guard (1 HARD test)

9. `test_diagnostic_columns_absent_from_feature_matrix_hard` — assert NONE of the 5 prohibited 25.0a-β diagnostic columns appear in the model's input X matrix.

### §11.4 Cell grid integrity (1 test)

10. `test_cell_grid_has_exactly_24_cells_no_duplicates` — assert exactly 24 unique parameter combinations.

### §11.5 Validation split chronological (1 test)

11. `test_chronological_70_15_15_split_no_overlap` — assert train.max_ts < val.min_ts; val.max_ts < test.min_ts; split percentages within ±1% of 70/15/15.

### §11.6 Standardisation no-leak (1 test)

12. `test_scaler_fit_on_train_only` — fit scaler on train, transform val/test; assert scaler's mean/std equals what's computed on train alone.

### §11.7 F1 negative-list assertion (1 test)

13. `test_no_donchian_zscore_imports_from_phase23` — defensive: assert no import statement from `stage23_0b` / `stage23_0c` / `stage23_0d` Donchian/z-score helpers in the 25.0b-β script (string-grep on script source).

### §11.8 Bidirectional shape (1 test)

14. `test_bidirectional_two_rows_per_signal_ts` — verify long-format dataset has exactly 2 rows per (pair, signal_ts).

### §11.9 Threshold selection (1 test)

15. `test_threshold_selected_on_validation_only` — synthetic predictions/labels; assert selected threshold maximises val score, NOT test score; verify test score not consulted in selection.

### §11.10 NaN-warmup drop (1 test)

16. `test_feature_nan_rows_dropped_with_counter` — synthetic short series where f1_b is NaN for first 100 bars; assert those rows excluded from model input AND counter incremented.

**Minimum total: 16 tests** (above the ≥ 13 minimum).

## §12. eval_report.md required outputs

The 25.0b-β report MUST include:

1. **Mandatory clauses (§13)** verbatim at top.
2. **Headline verdict** (PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE / REJECT) per cell.
3. **Held-out (test) AUC** per cell, sorted descending.
4. **AUC bootstrap CI** per cell — diagnostic only, not gate-bearing.
5. **Calibration sanity** per cell: predicted P(positive) bucketed quintiles vs realised positive rate; monotonicity flag.
6. **Train/val/test positive label rates** to verify split integrity.
7. **8-gate harness results** (A0-A5) per cell at the trade-decision level (after threshold filter).
8. **Trade decision metrics** per cell:
   - `annual_trades`
   - `selected_trade_count`
   - `trade_rate` (= selected_trade_count / total_signal_candidates)
   - by-pair trade count
   - by-direction trade count
9. **Per-pair AUC** (20-row table per cell or summary stats).
10. **Per-direction AUC** (long vs short).
11. **Feature coefficient summary** (logistic coefficients standardised; top-and-bottom by magnitude).
12. **`feature_nan_drop_count` and `feature_nan_drop_rate`** overall + per pair.
13. **Threshold selection log**: which threshold was picked, val-PnL or val-Sharpe-proxy that drove the pick, frozen-test result with that threshold.
14. **Multiple-testing caveat (verbatim)**: *"These are 24 evaluated cells. PROMISING / ADOPT_CANDIDATE verdicts are hypothesis-generating ONLY; production-readiness requires an X-v2-equivalent frozen-OOS PR per Phase 22 contract."*
15. **H1 routing** (AUC ≥ 0.55 PASS/FAIL): per-cell + best-cell summary.
16. **Explicit lines**: *"threshold selected on validation only"* AND *"test set touched once"*.

## §13. Mandatory clauses (verbatim in 25.0b-β script docstring AND eval_report.md)

### Clause 1 — Phase 25 framing (inherited)

> *Phase 25 is not a hyperparameter-tuning phase. It is a label-and-
> feature-class redesign phase. Novelty must come from input feature
> class and label design.*

### Clause 2 — F1 negative list (binding)

> *F1 features are volatility-derivative. F1 is NOT a Donchian
> breakout, NOT a z-score, NOT a Bollinger band touch, NOT a moving
> average crossover, NOT a calibration-only signal. Recent return
> sign (f1_f) is secondary directional context only — it MUST NOT
> serve as a standalone primary trigger.*

### Clause 3 — Diagnostic columns are not features

> *The 25.0a-β diagnostic columns (max_fav_excursion_pip,
> max_adv_excursion_pip, time_to_fav_bar, time_to_adv_bar,
> same_bar_both_hit) MUST NOT appear in any model's feature matrix.
> A unit test enforces this.*

### Clause 4 — Causality and split discipline

> *All f1 features use shift(1).rolling pattern; signal bar t's own
> data MUST NOT enter feature[t]. Train / val / test splits are
> strictly chronological (70/15/15 by calendar date). Threshold
> selection uses VALIDATION ONLY; test set is touched once.*

### Clause 5 — γ closure preservation

> *Phase 25.0b does not modify the γ closure (PR #279). Phase 25
> results, regardless of outcome, do not change Phase 24 / NG#10
> β-chain closure status.*

### Clause 6 — Production-readiness preservation

> *PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE in 25.0b are hypothesis-
> generating only. Production-readiness requires an X-v2-equivalent
> frozen-OOS PR per Phase 22 contract. No production deployment is
> pre-approved by this PR.*

## §14. Routing to 25.0b-β

Once this 25.0b-α PR merges:
- 25.0b-β implements the contract above.
- 25.0b-β must include the §11 test contract (≥ 16 tests).
- 25.0b-β commits eval_report.md with the §12 required outputs.
- 25.0b-β may NOT retune any §3 / §6 / §7 / §8 / §9 numerical
  parameter. If retuning is needed, 25.0b-α must be revised in a
  separate documented PR with explicit justification.

After 25.0b-β merges, 25.0c routing depends on results:
- **H1 PASS (best-cell test AUC ≥ 0.55) AND H2 PASS (clears A1/A2 with
  selected threshold)** → candidate next PR is X-v2 frozen-OOS for
  the best cell (Phase 22 contract).
- **H1 PASS, H2 FAIL** → user decides: open LightGBM follow-up
  (different model class) on F1 features, OR pivot to F2-F6.
- **H1 FAIL** → user decides: pivot to another F-class (F2-F6), OR
  declare F1 closed and reconsider Phase 25 scope.

The 25.0b-β eval_report.md will surface the routing recommendation;
the user decides.

## §15. What this 25.0b-α PR does NOT do

- Does not implement any code.
- Does not generate any features or models.
- Does not modify the kickoff (#280), 25.0a-α (#281), or 25.0a-β
  (#282).
- Does not relax NG#10 / NG#11.
- Does not pre-approve threshold or feature retuning.
- Does not pre-approve any production deployment.
- Does not update MEMORY.md.
- Does not modify Phases 22-24 docs / artifacts.

## §16. Files

| Path | Status | Lines |
|---|---|---|
| `docs/design/phase25_0b_f1_design.md` | NEW | this file |

**Single file. No `artifacts/` entry. No `tests/` entry. No
`scripts/` entry. No `src/` change. No DB schema change. No
MEMORY.md update. Existing 22.x / 23.x / 24.x / 25 docs/artifacts:
unchanged. NG#10 / NG#11: not relaxed.**

## §17. CI surface

- `python tools/lint/run_custom_checks.py` (rc=0 expected; doc-only)
- `pytest` (no test changes; existing tests untouched)

---

**Phase 25.0b-α — F1 design contract locked. Implementation in 25.0b-β.**
