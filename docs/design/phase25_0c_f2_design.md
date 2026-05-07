# Phase 25.0c-α — F2 Multi-Timeframe Volatility Regime Design Memo (binding contract for 25.0c-β)

Doc-only PR fixing the binding contract for 25.0c-β implementation
(F2: multi-timeframe volatility regime, the second feature class
evaluated under Phase 25 path-quality labels). **No code, no eval, no
implementation in this PR.**

> **Phase 25 framing inheritance** (from kickoff PR #280):
>
> *Phase 25 is not a hyperparameter-tuning phase. It is a label-and-
> feature-class redesign phase. Novelty must come from input feature
> class and label design.*
>
> The hyperparameters in this memo are **design constants** for F2.
> They are fixed before 25.0c-β implementation and **MUST NOT be
> retuned** during implementation. Pathological balance / unsuitable
> result paths halt-and-report (no in-place retune).

## §1. Stage purpose

This memo locks F2's binding design contract. It is the second
feature-class design memo under Phase 25 (after F1 in PR #283), and
it explicitly addresses the sample-size pressure observed in F1's
24-cell sweep (PR #284, scope review #285).

F2 evaluates whether **categorical multi-TF volatility regime
patterns** — distinct from F1's continuous vol-derivative magnitudes
— predict the path-quality binary label.

## §2. Scope

**In scope**:
- F2 feature class definition (categorical regime tags + cross-TF
  combinations); §3.
- Negative list — what F2 is NOT, including the binding "F2 must not
  become F1 redo" prohibition; §4.
- Cell grid (18 cells; bidirectionality LOCKED); §5.
- Validation split inheritance (70/15/15 chronological); §6.
- Threshold candidates inheritance ({0.20, 0.25, 0.30, 0.35, 0.40})
  + validation-only selection; §7.
- Realised barrier PnL methodology inheritance; §8.
- Diagnostic-leakage prohibition (HARD test); §9.
- Test contract (≥ 14 tests); §10.
- eval_report.md required outputs (with F2-specific additions); §11.
- Mandatory clauses (verbatim); §12.

**Explicitly out of scope**:
- Implementation (deferred to 25.0c-β).
- LightGBM (deferred unless F2 logistic AUC ≥ 0.55).
- F1 envelope redesign (separate PR if pursued; option γ from PR #285).
- F3-F6 feature classes (separate per-class PRs).
- Modifying 25.0a label dataset / thresholds.
- Modifying Phase 25 kickoff (#280) / 25.0a-α (#281) / 25.0a-β (#282)
  / 25.0b-α (#283) / 25.0b-β (#284) / scope review (#285).
- Modifying 22.x / 23.x / 24.x docs/artifacts.
- Relaxing NG#10 / NG#11.
- Modifying γ closure (PR #279).
- Pre-approving any production deployment.
- MEMORY.md update.

## §3. F2 feature class definition (binding)

### §3.1 Feature catalogue (5 families; numerical params FIXED)

All windows are computed with strict `shift(1)` causality so signal
bar `t`'s features use only bars ≤ `t-1`.

#### f2_a — Per-TF regime tag (categorical, 3 cols)

For each TF ∈ {M5, M15, H1}:
- Compute realised volatility `RV[t]` per TF using F1's f1_a formula
  (`shift(1).rolling(N)` of squared log-returns, with N = M5×12,
  M15×8, H1×24).
- Discretise into `{low, med, high}` using rolling **tertile**
  boundaries:
  - `low_threshold[t]` = 33rd percentile of `RV[t-trailing..t-1]`
  - `high_threshold[t]` = 66th percentile of `RV[t-trailing..t-1]`
  - `regime[t] = "low"` if `RV[t-1] < low_threshold[t]`
  - `regime[t] = "high"` if `RV[t-1] > high_threshold[t]`
  - `regime[t] = "med"` otherwise

> **Tertile boundaries are FIXED at 33/66 percentile**. Quintile
> boundaries are NOT swept in 25.0c. Tag scheme retuning requires a
> 25.0c-α-rev1 doc-only PR.

Output: `f2_a_regime_M5`, `f2_a_regime_M15`, `f2_a_regime_H1` ∈
{low, med, high} (3 categorical features).

#### f2_b — Joint regime tag (categorical, 1 col, ≤ 27 levels)

```
f2_b_joint_regime[t] = f"{f2_a_regime_M5[t]}_{f2_a_regime_M15[t]}_{f2_a_regime_H1[t]}"
```

Up to 27 distinct joint regime levels (3³). Some levels may be rare
or empty in the train set (see §3.4 rare-regime policy).

#### f2_c — Alignment counts (numeric, 2 cols)

```
f2_c_high_count[t] = number of TFs in 'high' state ∈ {0, 1, 2, 3}
f2_c_low_count[t]  = number of TFs in 'low'  state ∈ {0, 1, 2, 3}
```

Captures how aligned the regimes are across TFs without exploding
the categorical cardinality of f2_b.

#### f2_d — Regime transition flag (binary, 3 cols)

For each TF:
```
f2_d_transitioned_<TF>[t] = (f2_a_regime_<TF>[t] != f2_a_regime_<TF>[t-1])
```

Captures the "regime just changed" mechanism that F1 did not have
explicit access to. Computed from causally-tagged regime series; no
forward leakage.

> **Binding: f2_d is an F2-specific differentiator**. The "regime
> transition" event is a feature F1 did not encode and is one of the
> primary mechanisms F2 tests.

#### f2_e — Recent return sign (secondary directional context only)

Carried over from F1's f1_f unchanged:
```
f2_e_return_sign[t] = sign(close_M5[t-1] - close_M5[t-13])
```

> **Binding constraint** (carried from 25.0b-α §3.1): f2_e is
> **secondary directional context only**. A cell MUST NOT use f2_e
> as a standalone primary trigger. The regime tags (f2_a/b/c/d) are
> the primary triggers; f2_e informs direction-of-trade but does not
> generate signals on its own.

### §3.2 Total feature count

3 (f2_a) + 1 (f2_b) + 2 (f2_c) + 3 (f2_d) + 1 (f2_e) = **10
features** + 2 categorical covariates (`pair`, `direction`).

After one-hot encoding (treating f2_a, f2_b, f2_e as categoricals;
pair × 20, direction × 2; f2_a × 3 levels each = 9 cols; f2_b ≤ 27
levels; f2_e × 3 levels = 3 cols), the model X matrix has roughly
**60-80 columns**.

### §3.3 Causality

All features use shift(1) on RV computation (inherited from F1's
f1_a pattern). Regime tags computed AT signal time t use only RV
values at bars ≤ t-1.

- **f2_a**: RV computed via shift(1); tertile boundaries computed
  from RV[t-trailing..t-1] only.
- **f2_b**: function of f2_a — same causality.
- **f2_c**: function of f2_a — same causality.
- **f2_d**: regime[t] vs regime[t-1]; both causal — no forward leak.
- **f2_e**: shift(1) close-to-close diff — same as F1's f1_f.

### §3.4 Rare joint regime policy (binding)

Some joint regimes (e.g., `low_low_high` or `high_low_low`) may be
rare in the train set. **For 25.0c-β first implementation, rare
joint regimes are kept as-is**:

- No target-aware category collapsing is allowed.
- No frequency-based collapsing in this PR.
- `OneHotEncoder(handle_unknown="ignore")` is used so unseen joint
  regimes in val/test are handled gracefully (encoded as all-zero).

> Any future joint-regime category collapsing must be (a)
> frequency-only (NOT target-aware), (b) train-set-only (compute
> frequency on train; apply to val/test), and (c) declared in a
> separate 25.0c-α-rev1 PR with explicit pre-data hypothesis.

## §4. Negative list — what F2 IS NOT (binding)

The 25.0c-β implementation MUST NOT introduce ANY of the following:

1. **Donchian band breakout** (NG#1 — NEVER as primary or
   sub-feature).
2. **Rolling z-score on close** (NG#2).
3. **Bollinger band touch** as primary trigger.
4. **Moving-average crossover** alone.
5. **Calibration-only / probability-smoothing-only signal** (NG#12).
6. **f2_e as standalone primary trigger** (per §3.1 binding
   constraint).
7. **Pair / time-of-day / WeekOpen filter as primary edge** (NG#8-10).
8. **F2 must not become F1 redo** (binding):
   - **Raw continuous RV** is prohibited as a direct model feature in
     25.0c. RV is used ONLY to derive the categorical regime tags
     (f2_a) and downstream features (f2_b/c/d).
   - **Raw expansion ratio** (F1's f1_c) is prohibited as a direct
     model feature in 25.0c.
   - **Raw vol-of-vol** (F1's f1_d) is prohibited as a direct model
     feature in 25.0c.
   - **Raw range compression score** (F1's f1_e) is prohibited as a
     direct model feature in 25.0c.

The 25.0c-β script's design preamble must contain a one-paragraph
justification for each F2 feature explaining why it is NOT a direct
re-encoding of F1's continuous magnitudes.

## §5. Cell grid (18 cells; bidirectionality LOCKED)

Per direction §3 / scope review #285 §4.4 soft suggestion. Smaller
than F1's 24-cell grid to address the sample-size pressure observed
in PR #284.

| Dimension | Values | Count |
|---|---|---|
| Trailing window for tertile boundaries | {100, 200} | 2 |
| Feature representation included | {per-TF only (f2_a), per-TF + joint (f2_a + f2_b), all (f2_a + f2_b + f2_c + f2_d + f2_e)} | 3 |
| Admissibility filter | {none, high-alignment ≥ 2 of 3 TFs in 'high', transition-just-occurred-at-any-TF} | 3 |
| **Total** | | **18** |

### §5.1 Admissibility filter semantics

- **none**: all admissible 25.0a signals (full sample). Mandatory
  per direction §3 — addresses F1's sample-size issue with a
  full-sample baseline.
- **high-alignment ≥ 2 of 3 TFs in 'high'**: keep rows where
  `f2_c_high_count[t] >= 2`.
- **transition-just-occurred-at-any-TF**: keep rows where
  `f2_d_transitioned_M5[t] OR f2_d_transitioned_M15[t] OR
  f2_d_transitioned_H1[t]`.

### §5.2 Bidirectionality LOCKED

Bidirectional candidate generation is FIXED, NOT a cell dimension
(per kickoff §6.2 + 25.0b-α §4 inheritance). Each (pair, signal_ts)
emits 2 model-input rows (long + short).

### §5.3 Within kickoff §10 budget

18 cells lies within kickoff §10's 18-33 budget. **Expansion beyond
33 cells requires explicit multiple-testing justification** in the
per-class design memo (none requested here).

## §6. Validation split (LOCKED inheritance)

Per 25.0b-α §8 inheritance:

- **Train**: first 70% of 730d (≈ 511 days).
- **Validation**: next 15% (≈ 110 days). Used for threshold
  selection (§7) and any cell-specific decision.
- **Test**: last 15% (≈ 110 days). **Held strictly until the final
  pass**. Touched ONCE in 25.0c-β. Re-running test set across
  hyperparameter retunes is FORBIDDEN.

Calendar-date boundaries lock the split. Random splits PROHIBITED.

## §7. Trade-decision threshold (validation-only selection; LOCKED inheritance)

Per 25.0b-α §9 inheritance:

- **Threshold candidates**: {0.20, 0.25, 0.30, 0.35, 0.40}.
- **Selection rule**: on the VALIDATION set, compute val Sharpe
  proxy per threshold; pick the threshold maximising val Sharpe
  proxy.
- **Tie-breakers** (per direction A from 25.0b-α): val Sharpe →
  total_pnl → trade count → higher threshold.
- **Selected threshold is FROZEN** before test-set evaluation.

> **Mandatory in eval_report.md**: explicit lines stating *"threshold
> selected on validation only"* and *"test set touched once"*.

## §8. Realised barrier PnL methodology (LOCKED inheritance)

Per 25.0b-β §3.8 inheritance. Final test 8-gate evaluation uses
realised barrier PnL via M1 path re-traverse with 25.0a barrier
semantics:

- favourable barrier first → +K_FAV × ATR
- adverse barrier first → −K_ADV × ATR
- same-bar both-hit → adverse first → −K_ADV × ATR
- horizon expiry → mark-to-market (close at t+H − entry, in pips)

Validation threshold selection uses synthesized PnL proxy
(±K_FAV/K_ADV × ATR by label).

> **This is realised barrier PnL, not broker-fill PnL**.
> Production deployment requires X-v2-equivalent frozen-OOS PR.

## §9. Leakage guards (HARD invariants)

### §9.1 25.0a diagnostic columns prohibition

The 25.0c-β model's feature matrix MUST NOT contain any of:
- `max_fav_excursion_pip`
- `max_adv_excursion_pip`
- `time_to_fav_bar`
- `time_to_adv_bar`
- `same_bar_both_hit`

A unit test enforces this.

### §9.2 OneHotEncoder unknown handling

`OneHotEncoder(handle_unknown="ignore")` for `f2_a`, `f2_b`, `f2_e`
categorical columns. Required because some joint regimes may not
appear in train but appear in val/test. Unseen categories are
encoded as all-zero (no error, no leakage).

### §9.3 Causality

All features use shift(1).rolling pattern. Signal bar t's RV does
NOT enter feature[t]'s computation.

### §9.4 Train/val/test boundary

Scaler + encoders fit on train only. A unit test enforces.

### §9.5 NaN-warmup row drop

F2 features (f2_a/b/c/d depend on RV which depends on TF aggregation)
require warmup beyond 25.0a's 20-bar ATR. Rows where ANY f2_a..f2_d
feature is NaN MUST be dropped. f2_e is allowed to be 0 (sign of
zero return).

Drop counters required in eval_report.md (§11.10):
- `feature_nan_drop_count` overall + per pair
- `feature_nan_drop_rate` overall + per pair

## §10. Test contract (≥ 14 tests minimum)

The 25.0c-β implementation MUST include at least these tests:

### §10.1 Feature correctness (5 tests)

1. `test_f2_a_regime_tertile_boundaries_correct` — synthetic RV;
   assert tertile boundaries (33rd / 66th percentile) and tag mapping
   correct.
2. `test_f2_b_joint_regime_construction_correct` — concat of per-TF
   tags.
3. `test_f2_c_high_low_counts_correct` — count logic across TFs.
4. `test_f2_d_transition_flag_correct` — regime change detection
   between t-1 and t.
5. `test_f2_e_return_sign_carried_unchanged_from_f1` — sign(close[t-1]
   − close[t-13]).

### §10.2 Causality (2 tests)

6. `test_features_use_only_past_bars_shift_1` — modifying bar t does
   not change feature[t].
7. `test_no_lookahead_at_t_plus_1` — modifying bar t+1 does not
   change feature[t].

### §10.3 Diagnostic-leakage HARD (1 test)

8. `test_diagnostic_columns_absent_from_feature_matrix_hard` — assert
   none of 25.0a's 5 prohibited columns in X matrix.

### §10.4 Cell grid integrity (1 test)

9. `test_cell_grid_has_exactly_18_cells_no_duplicates` — assert 18
   unique parameter combinations.

### §10.5 Validation split chronological (1 test)

10. `test_chronological_70_15_15_split_no_overlap`.

### §10.6 Standardisation no-leak (1 test)

11. `test_scaler_fit_on_train_only`.

### §10.7 F2 negative-list (1 HARD test)

12. `test_f2_does_not_use_continuous_rv_or_f1_features_hard` — assert
    feature columns do NOT include `rv_<tf>` (raw RV), `expansion_ratio_<tf>`
    (F1's f1_c), `vol_of_vol_<tf>` (F1's f1_d), `range_score_<tf>`
    (F1's f1_e). HARD invariant per §4.8.

### §10.8 Bidirectional shape (1 test)

13. `test_bidirectional_two_rows_per_signal_ts`.

### §10.9 Threshold selection (1 test)

14. `test_threshold_selected_on_validation_only`.

### §10.10 OneHotEncoder unknown handling (1 test)

15. `test_one_hot_encoder_handles_unknown_joint_regime` — synthetic
    val/test row with joint regime not in train; assert no error,
    encoded as all-zero.

### §10.11 NaN-warmup drop (1 test)

16. `test_feature_nan_rows_dropped_with_counter` — synthetic series
    with NaN f2_a; assert dropped + counter incremented.

### §10.12 Realised barrier PnL inheritance (1 test)

17. `test_realised_pnl_uses_25_0a_barrier_semantics` — verify
    favourable/adverse/same-bar/expiry outcomes match 25.0a barrier
    rules.

**Minimum total: 17 tests** (above the ≥ 14 minimum).

## §11. eval_report.md required outputs

The 25.0c-β report MUST include:

1. **Mandatory clauses (§12)** verbatim at top.
2. **Headline verdict** per cell.
3. **Held-out (test) AUC** per cell, sorted descending.
4. **AUC bootstrap CI** per cell — diagnostic only.
5. **Calibration sanity** per cell: monotonicity flag + Brier score.
6. **Train/val/test positive label rates**.
7. **8-gate harness results** (A0-A5) per cell at trade-decision
   level (after threshold filter).
8. **Trade decision metrics** per cell:
   - `annual_trades`
   - `selected_trade_count`
   - `trade_rate`
   - by-pair trade count
   - by-direction trade count
9. **Per-pair AUC** per cell.
10. **Per-direction AUC** per cell.
11. **Feature coefficient summary** (logistic coefficients
    standardised; top-and-bottom by magnitude).
12. **`feature_nan_drop_count` and `feature_nan_drop_rate`** overall
    + per pair.
13. **Threshold selection log**: which threshold picked, val Sharpe
    proxy that drove the pick, frozen-test result.
14. **Multiple-testing caveat (verbatim)**: *"These are 18 evaluated
    cells. PROMISING / ADOPT_CANDIDATE verdicts are hypothesis-
    generating ONLY; production-readiness requires an
    X-v2-equivalent frozen-OOS PR per Phase 22 contract."*
15. **H1 / H2 / verdict routing** (REJECT / REJECT_BUT_INFORMATIVE /
    PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE) per kickoff §8 +
    25.0b-β §verdict-logic.
16. **Explicit lines**: *"threshold selected on validation only"*
    AND *"test set touched once"*.

### §11.1 F2-specific additions

17. **Per-cell admissibility pass-through rate**: for each cell,
    report `(rows_after_admissibility_filter / rows_before)` per
    train/val/test split.
18. **Regime distribution table**: count and rate of rows per joint
    regime (f2_b) on the train set; flag rare regimes (< 1% of
    train).

## §12. Mandatory clauses (verbatim in 25.0c-β script docstring + eval_report.md)

Six clauses to lock:

### Clause 1 — Phase 25 framing (inherited)

> *Phase 25 is not a hyperparameter-tuning phase. It is a label-and-
> feature-class redesign phase. Novelty must come from input feature
> class and label design.*

### Clause 2 — F2 negative list (binding)

> *F2 features are CATEGORICAL multi-TF volatility regime tags. F2
> is NOT continuous vol-derivative magnitudes (that's F1,
> REJECT_BUT_INFORMATIVE per PR #284 — see scope review PR #285).
> Raw RV, raw expansion ratio, raw vol-of-vol, raw range compression
> score are PROHIBITED as direct model features in 25.0c. F2 is NOT
> a Donchian / z-score / Bollinger band touch / moving-average
> crossover / calibration-only signal. Recent return sign (f2_e) is
> secondary directional context only — it MUST NOT serve as a
> standalone primary trigger. The trigger uses the joint regime
> VECTOR, alignment counts, and transition events.*

### Clause 3 — Diagnostic columns are not features (inherited)

> *The 25.0a-β diagnostic columns (max_fav_excursion_pip,
> max_adv_excursion_pip, time_to_fav_bar, time_to_adv_bar,
> same_bar_both_hit) MUST NOT appear in any model's feature matrix.
> A unit test enforces this.*

### Clause 4 — Causality and split discipline (inherited)

> *All f2 features use shift(1).rolling pattern; signal bar t's own
> data MUST NOT enter feature[t]. Train / val / test splits are
> strictly chronological (70/15/15 by calendar date). Threshold
> selection uses VALIDATION ONLY; test set is touched once.*

### Clause 5 — γ closure preservation (inherited)

> *Phase 25.0c does not modify the γ closure (PR #279). Phase 25
> results, regardless of outcome, do not change Phase 24 / NG#10
> β-chain closure status.*

### Clause 6 — Production-readiness preservation (inherited)

> *PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE in 25.0c are
> hypothesis-generating only. Production-readiness requires an
> X-v2-equivalent frozen-OOS PR per Phase 22 contract. No production
> deployment is pre-approved by this PR.*

## §13. Routing to 25.0c-β

Once this 25.0c-α PR merges:
- 25.0c-β implements the contract above.
- 25.0c-β must include the §10 test contract (≥ 17 tests).
- 25.0c-β commits eval_report.md with §11 required outputs.
- 25.0c-β may NOT retune any §3 / §5 / §6 / §7 / §8 / §9 numerical
  parameter. If retuning is needed, 25.0c-α must be revised in a
  separate documented PR with explicit pre-data justification.

After 25.0c-β merges, routing depends on results (per kickoff §8 +
PR #285 hypothesis logic):
- **H1 PASS (best-cell test AUC ≥ 0.55) AND H2 PASS (clears A1/A2
  with selected threshold)** → candidate next PR is X-v2 frozen-OOS
  for the best cell (Phase 22 contract).
- **H1 PASS, H2 FAIL** → REJECT_BUT_INFORMATIVE. User decides:
  LightGBM follow-up on F2 features, OR pivot to F3/F4/F5/F6, OR F2
  envelope redesign.
- **H1 FAIL** → REJECT. User decides: pivot to next F-class OR Phase
  25 scope review (analogous to PR #285 but post-F2).

The 25.0c-β eval_report.md will surface routing recommendation; the
user decides.

## §14. What this 25.0c-α PR does NOT do

- Does not implement any code.
- Does not generate any features or models.
- Does not modify Phase 25 kickoff (#280) / 25.0a-α (#281) / 25.0a-β
  (#282) / 25.0b-α (#283) / 25.0b-β (#284) / scope review (#285).
- Does not relax NG#10 / NG#11.
- Does not pre-approve threshold or feature retuning.
- Does not pre-approve any production deployment.
- Does not update MEMORY.md.
- Does not modify Phases 22-24 docs / artifacts.
- Does not modify γ closure (PR #279).
- Does not address F1 envelope redesign (separate option from PR #285).

## §15. Files

| Path | Status | Lines |
|---|---|---|
| `docs/design/phase25_0c_f2_design.md` | NEW | this file |

**Single file. No `artifacts/` entry. No `tests/` entry. No
`scripts/` entry. No `src/` change. No DB schema change. No
MEMORY.md update. Existing 22.x / 23.x / 24.x / 25.x docs/artifacts:
unchanged. NG#10 / NG#11: not relaxed. γ closure (PR #279):
preserved.**

## §16. CI surface

- `python tools/lint/run_custom_checks.py` (rc=0 expected; doc-only)
- `pytest` (no test changes; existing tests untouched)

---

**Phase 25.0c-α — F2 design contract locked. Implementation in 25.0c-β.**
