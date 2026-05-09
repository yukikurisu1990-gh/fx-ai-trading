# Phase 25.0d-α — Deployment-Layer Audit Design Memo (binding contract for 25.0d-β)

Doc-only design memo locking the methodology for the Phase 25
deployment-layer investigation. **No code, no eval, no
implementation in this PR.**

> **Production misunderstanding guard** (binding):
>
> *This is a research deployment-layer audit, not a production
> deployment study.* The findings inform Phase 25's research routing
> only. They do not pre-approve any threshold, pipeline, or
> directional candidate generation for production. Production-
> readiness still requires an X-v2-equivalent frozen-OOS PR per
> Phase 22 contract.

## §1. Stage purpose

Tests **H-A / H-B / H-D / H-F** from PR #288 §5 by analysing the
F1 best cell (rank-1 from #284) and F2 best cell (rank-1 from #287)
under varied deployment-layer settings. Does NOT redesign features,
labels, or model class. Re-uses the existing F1 / F2 trained
pipelines with `random_state=42` deterministic re-fit.

This memo locks:
- §3 Cell selection
- §4 Calibration analysis methodology (H-A)
- §5 Per-bucket realised barrier PnL methodology (H-F empirical)
- §6 Threshold sweep extension methodology (H-B)
- §7 Bidirectional argmax vs directional methodology (H-D)
- §8 AUC-EV theoretical bound calculation (H-F theoretical)
- §9 Verdict criteria
- §10 Test contract (≥ 12 tests)
- §11 eval_report.md required outputs
- §12 Mandatory clauses (verbatim)

## §2. Scope

**In scope**:
- Audit of F1 rank-1 cell + F2 rank-1 cell ONLY (not all F1/F2 cells).
- Calibration analysis (decile bucketing; reliability diagram;
  Brier score per decile).
- Per-bucket realised barrier PnL using existing
  `_compute_realised_barrier_pnl` (inherited from 25.0b-β).
- Threshold sweep extension to 7 thresholds (diagnostic-only).
- Directional candidate generation comparison (diagnostic-only).
- AUC-EV theoretical bound (closed-form; diagnostic-only).
- LOW_BUCKET_N flagging (n < 100).
- Verdict per H-A / H-B / H-D / H-F.

**Explicitly out of scope**:
- All F1/F2 cells beyond rank-1 (per direction §2).
- Implementation (deferred to 25.0d-β).
- F1/F2 verdict modification — #284 and #287 verdicts stand
  unchanged.
- New feature classes (F3-F6) / new model class (LightGBM) / label
  redesign / K_FAV-K_ADV redesign.
- Modifying 25.0a label dataset / Phase 25 PRs #280-#288.
- Modifying 22.x/23.x/24.x docs/artifacts.
- Relaxing NG#10 / NG#11.
- Modifying γ closure (PR #279).
- Pre-approving any production deployment.
- Pre-approving threshold selection or directional candidate
  generation for production.
- MEMORY.md update.

## §3. Cell selection (locked)

### §3.1 F1 best cell (rank-1 from PR #284)

- Pair-pool, signal_tf = M5
- q (compression quantile) = 0.20
- e (expansion threshold) = 1.25
- **lookback = 50** (representative of the lookback={50,100}
  identical-result pair, per 25.0b-β's documented compression_pct
  precomputation approximation; both lookback values use the same
  precomputed column, so 50 is a faithful representative of either).
- Features: 25.0b-α §3 — 16 base + 2 categorical (pair, direction).

### §3.2 F2 best cell (rank-1 from PR #287)

- Pair-pool, trailing_window = 200
- representation = `per_tf_only`
- admissibility = `none` (full-sample baseline)
- Features: 25.0c-α §3 — `per_tf_only` selection (4 cols + 2
  categorical = 6 categorical inputs after one-hot).

> Both cells investigated separately; convergence/divergence of
> findings is the load-bearing observation. The audit's goal is to
> see whether the **best** cell of each feature class breaks down
> at the deployment layer.

### §3.3 Re-fit semantics

25.0d-β re-trains both cells deterministically with
`random_state=42`. Same chronological 70/15/15 split, same feature
catalogue, same hyperparameters as the original PRs (#284 for F1,
#287 for F2). No retraining of features or hyperparameters.

## §4. Calibration analysis methodology (H-A)

### §4.1 Procedure

For each cell:
1. Re-train logistic on train (deterministic).
2. Predict P(positive) on test set.
3. **Decile bucketing**: split test rows by predicted P into 10
   equal-width buckets (predicted_P ∈ [0.0, 0.1), [0.1, 0.2), ...,
   [0.9, 1.0]).
4. Per-bucket compute:
   - n (sample count)
   - mean predicted P (bucket centre)
   - actual positive rate
   - Brier score
   - LOW_BUCKET_N flag if n < 100
5. **Reliability diagram**: plot bucket_mean_predicted vs
   bucket_actual_positive_rate. Compare to y=x line.
6. **Quintile monotonicity flag** (supplementary; 5 buckets,
   monotonic = predicted-rate-rank matches actual-rate-rank).

### §4.2 Verdict on H-A (calibration mismatch)

- **Calibration OK** if reliability diagram is roughly diagonal
  (deviation from y=x within **±0.05** across deciles).
- **Mis-calibrated (H-A confirmed)** if predictions consistently
  over-estimate or under-estimate by **> 0.10** systematically
  across multiple deciles.
- **Boundary case** if deviation is in [0.05, 0.10] zone — report
  with a "Boundary calibration" supplemental note; verdict deferred
  to user judgement based on the per-decile breakdown.

## §5. Per-bucket realised barrier PnL methodology (H-F empirical)

### §5.1 Procedure

For each cell × each predicted-P decile:
1. Identify all (signal_ts, pair, direction) test rows in that
   bucket.
2. Compute realised barrier PnL via existing
   `_compute_realised_barrier_pnl` (inherited from 25.0b-β; same
   25.0a barrier semantics — favourable/adverse/same-bar SL-first/
   horizon mark-to-market).
3. Compute spread cost per row (already in 25.0a labels via
   `spread_at_signal_pip`).
4. Per-bucket: mean realised PnL, mean spread cost, **net EV** =
   mean_realised − mean_spread.

### §5.2 Verdict on H-F (empirical level)

- **Structural gap confirmed** if no decile produces positive
  net_EV across both F1 and F2 cells.
- **Threshold or calibration is the issue** (NOT structural) if
  some deciles (typically top deciles) produce positive net_EV.

## §6. Threshold sweep extension methodology (H-B)

### §6.1 Threshold range (LOCKED)

`{0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80}` — 7 thresholds.

> **Threshold sweep guard** (binding):
>
> *The extended threshold sweep is diagnostic-only. It must not be
> interpreted as selecting a production threshold from the test set.*
> Production threshold selection requires a separate predeclared
> design PR and frozen-OOS validation. The audit's purpose is to
> determine whether the original {0.20-0.40} range was binding,
> NOT to recommend a new production threshold.

### §6.2 Procedure

For each cell × each threshold:
1. Filter test rows where `max(P_long, P_short) ≥ threshold`
   (bidirectional argmax — same as 25.0b-β / 25.0c-β).
2. Compute realised barrier PnL on filtered rows.
3. Compute Sharpe + ann_pnl + n_trades.
4. Output table: cell × threshold × (Sharpe / ann_pnl / n_trades).

### §6.3 Verdict on H-B

- **H-B confirmed** if extended thresholds {0.50+} produce
  **positive Sharpe** on F1 OR F2 best cell.
- **H-B refuted** if all thresholds (including {0.50, 0.60, 0.70,
  0.80}) produce negative Sharpe on both cells.

## §7. Bidirectional argmax vs directional methodology (H-D)

### §7.1 Procedure

For each cell:
1. **Bidirectional argmax** (existing): re-use F1/F2 model +
   `max(P_long, P_short) ≥ threshold` logic. Threshold = the cell's
   selected threshold from #284/#287 OR the best from §6 sweep
   (clarified per option in 25.0d-β).
2. **Directional candidate generation**:
   - Train **two separate models** on train: one on `direction=long`
     rows only (long-only model), one on `direction=short` rows only
     (short-only model).
   - **Per-direction threshold selection on val** (independent val
     Sharpe proxy max per direction; same threshold candidates set as
     bidirectional).
   - Test: for each (signal_ts, pair), check `long_model.P ≥
     long_threshold` AND `short_model.P ≥ short_threshold`
     separately. Take the trade in either direction if either fires.
   - **Same-bar both-fire conservative resolution**: if at the same
     signal_ts both directions fire on the same pair, resolve **to
     SL-first conservative** — emit no trade for that signal_ts (skip).
     This is the strictly-conservative interpretation; alternatives
     (random-pick / lower-prob-skip) are not used.
3. Compare Sharpe + ann_pnl + n_trades between bidirectional and
   directional.

### §7.2 Verdict on H-D

- **H-D confirmed** if directional materially beats bidirectional:
  - Sharpe lift ≥ +0.10, OR
  - ann_pnl improvement ≥ 50% — *but* this must be interpreted
    alongside **absolute profitability**. A 50% improvement from
    deeply negative ann_pnl (e.g., -2,300,000 → -1,150,000) is NOT
    monetisation; the report must call out the absolute level.
- **H-D refuted** if directional is similar or worse than
  bidirectional.

> **Directional comparison guard** (binding):
>
> *Directional comparison is diagnostic-only. If directional
> candidate generation appears promising, it requires a separate
> predeclared design PR and frozen-OOS validation.* The audit
> identifies WHETHER the bidirectional argmax is the bottleneck;
> deploying a directional pipeline is a separate downstream
> decision.

## §8. AUC-EV theoretical bound (H-F theoretical level)

### §8.1 Closed-form derivation (locked)

Pure analytical calculation; no model retraining.

Given:
- AUC = 0.561 (F2 best) or 0.564 (F1 best)
- Base positive rate p₀ = 0.187 (from 25.0a-β dataset)
- K_FAV = 1.5 × ATR; K_ADV = 1.0 × ATR
- Mean ATR per pair from 25.0a label dataset

Closed-form ROC-area derivation:
- For a binary classifier with AUC = a, the conditional positive
  rate at the q-th quantile of predicted probability follows a
  closed-form relationship from the ROC area (e.g., Cover-Hart-
  style bound or normal-pair derivation).
- For each quantile q ∈ {0.5, 0.6, 0.7, 0.8, 0.9}:
  - Theoretical P(positive | predicted ≥ q-th quantile) from
    AUC=a + base rate p₀
  - Theoretical mean realised PnL = P(pos) × K_FAV × ATR −
    P(neg) × K_ADV × ATR
  - Subtract mean spread cost
  - Result: theoretical net EV per quantile

### §8.2 Verdict on H-F (theoretical level)

- **H-F confirmed at theoretical level** if theoretical max net EV
  (across quantiles) is **negative** for both F1 and F2 cells —
  i.e., AUC ≈ 0.56 is fundamentally insufficient given the
  K_FAV/K_ADV/spread setup.
- **H-F refuted at theoretical level** if theoretical max net EV
  is **positive** but empirical is negative — i.e., the empirical
  pipeline wastes the theoretical edge (H-A or H-D issue).

> **Theoretical bound is diagnostic-only.** The empirical realised
> barrier PnL findings (§5, §6) take priority. The theoretical
> bound exists to surface "is the AUC ceiling fundamental or not"
> — not to substitute for empirical evidence.

## §9. Verdict criteria (locked)

The 25.0d-β eval_report.md will produce one or more of these
conclusions per cell + cross-cell:

| Finding | Implication for next PR |
|---|---|
| Calibration mismatch + extended threshold rescues | H-A confirmed → calibration-before-threshold PR |
| Calibration OK + extended threshold rescues | H-B confirmed → expand threshold range design PR |
| Calibration OK + threshold doesn't rescue + directional rescues | H-D confirmed → directional pipeline design PR (see §7 guard) |
| Calibration OK + threshold doesn't rescue + directional doesn't rescue + AUC-EV bound shows insufficient | H-F confirmed → structural gap fundamental; pivot to F3-F6 / label redesign |
| Multiple findings positive | Document each; user picks dominant axis |
| All deployment-layer hypotheses refuted | Empirical: AUC alone is binding; structural at the labelling/feature axis; pivot to F3-F6 or label redesign |

The doc explicitly states **25.0d-β does NOT auto-route**. The user
picks based on the report's findings.

## §10. Test contract (≥ 12 tests minimum; locked)

The 25.0d-β implementation MUST include at least these tests:

1. `test_decile_bucketing_correct` — synthetic predictions; assert
   10 equal-width buckets with no overlap.
2. `test_reliability_diagram_diagonal_on_calibrated_data` —
   synthetic well-calibrated predictions (P[predicted=k/10] →
   actual positive rate ≈ k/10); assert reliability output is
   diagonal within ±0.02.
3. `test_per_bucket_net_ev_calculation_correct` — synthetic bucket
   data; assert net_EV = mean_realised - mean_spread.
4. `test_threshold_sweep_includes_extended_range` — assert
   threshold list = {0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80}
   exactly (7 elements).
5. `test_directional_models_trained_separately` — assert long-only
   model trained on `direction='long'` rows only; short-only model
   trained on `direction='short'` rows only.
6. `test_directional_threshold_selected_per_direction_on_val` —
   assert val-only per-direction threshold selection.
7. `test_directional_same_bar_both_fire_skipped_conservatively` —
   synthetic case where both directions fire at same signal_ts;
   assert no trade emitted (conservative skip).
8. `test_aucEV_theoretical_bound_at_chance_level_correct` —
   closed-form check at AUC=0.50 → bound at chance level
   (= base rate × K_FAV − (1−base rate) × K_ADV − spread; should
   be negative).
9. `test_low_bucket_n_flag_threshold_100` — bucket n < 100 receives
   LOW_BUCKET_N flag.
10. `test_diagnostic_columns_absent_from_feature_matrix_hard` —
    inherited HARD invariant (25.0a leakage prohibition).
11. `test_no_modification_of_f1_f2_artifacts` — assert 25.0d-β does
    not write to `artifacts/stage25_0b/*` or `artifacts/stage25_0c/*`
    (read-only). Filesystem-level test.
12. `test_chronological_train_val_test_inherited` — assert split
    times match 25.0a-β labels (same dates as 25.0b-β / 25.0c-β
    pipelines).

### §10.1 Suggested extra tests (implementation may add)

- `test_threshold_sweep_marked_diagnostic_only` — assert eval_report
  emits the verbatim guard "extended threshold sweep is
  diagnostic-only".
- `test_directional_comparison_marked_diagnostic_only` — assert
  eval_report emits the verbatim guard "Directional comparison is
  diagnostic-only".
- `test_smoke_run_completes_with_data` — skipif-no-data;
  subprocess.

## §11. eval_report.md required outputs

The 25.0d-β report MUST include:

1. **Mandatory clauses (§12)** verbatim at top.
2. **Production misunderstanding guard** verbatim.
3. **Threshold sweep diagnostic-only guard** verbatim.
4. **Directional comparison diagnostic-only guard** verbatim.
5. **F1 cell section**:
   - Reliability diagram (decile + quintile-monotonicity flag).
   - Per-bucket net_EV table with LOW_BUCKET_N flags.
   - Extended threshold sweep table.
   - Directional vs bidirectional comparison (with absolute
     profitability annotation).
   - AUC-EV theoretical bound (diagnostic-only).
   - Per-cell H-A / H-B / H-D / H-F verdict.
6. **F2 cell section**: same structure as F1.
7. **Cross-cell convergence summary**: which findings replicate
   across both cells; divergent findings called out.
8. **Routing recommendations**: enumerate options per §9 verdict
   table; **NO auto-routing**.
9. **Boundary case notes**: any calibration deviation in [0.05,
   0.10] flagged for user review.
10. **Multiple-testing caveat** verbatim: "These are 2 evaluated
    cells × 4 hypotheses (H-A, H-B, H-D, H-F). Findings are
    research-level; production-readiness still requires X-v2-
    equivalent frozen-OOS PR."
11. **"test set touched once"** + **"threshold selected on val
    only"** lines.

## §12. Mandatory clauses (verbatim in 25.0d-β script + report)

### Clause 1 — Phase 25 framing (inherited)

> *Phase 25 is not a hyperparameter-tuning phase. It is a
> label-and-feature-class redesign phase.*

### Clause 2 — Diagnostic-leakage prohibition (inherited)

> *The 25.0a-β diagnostic columns (max_fav_excursion_pip,
> max_adv_excursion_pip, time_to_fav_bar, time_to_adv_bar,
> same_bar_both_hit) MUST NOT appear in any model's feature matrix.*

### Clause 3 — Causality and split discipline (inherited)

> *All features use shift(1).rolling pattern. Train/val/test splits
> are strictly chronological (70/15/15). Threshold selection uses
> VALIDATION ONLY; test set is touched once.*

### Clause 4 — γ closure preservation

> *Phase 25.0d does not modify the γ closure (PR #279). Phase 25
> results, regardless of outcome, do not change Phase 24 / NG#10
> β-chain closure status.*

### Clause 5 — Production-readiness preservation

> *PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE / structural-gap
> findings in 25.0d are hypothesis-generating only.
> Production-readiness requires X-v2-equivalent frozen-OOS PR per
> Phase 22 contract.*

### Clause 6 — Deployment-layer scope clause (NEW)

> *This PR investigates the structural AUC-PnL gap surfaced in
> PR #288 §4.2 by analysing F1+F2 best cells under varied
> deployment-layer settings. Tests H-A/H-B/H-D/H-F from #288 §5.
> Does NOT redesign features, labels, or model class. Verdict
> applies only to F1+F2 best cells; convergence with F3-F6 is a
> separate question. F1 and F2 verdicts (#284, #287) are NOT
> modified by this audit.*

### Clause 7 — Production misunderstanding guard (NEW)

> *This is a research deployment-layer audit, not a production
> deployment study.*

### Clause 8 — Threshold sweep guard (NEW)

> *The extended threshold sweep is diagnostic-only. It must not be
> interpreted as selecting a production threshold from the test
> set.*

### Clause 9 — Directional comparison guard (NEW)

> *Directional comparison is diagnostic-only. If directional
> candidate generation appears promising, it requires a separate
> predeclared design PR and frozen-OOS validation.*

## §13. Routing to 25.0d-β

After 25.0d-α merges:
- 25.0d-β implements the contract above.
- 25.0d-β must include the §10 test contract (≥ 12 tests).
- 25.0d-β commits eval_report.md with §11 required outputs.
- 25.0d-β does NOT auto-route.

## §14. What this 25.0d-α PR does NOT do

- Does not implement any code.
- Does not generate any features, models, or eval reports.
- Does not modify Phase 25 PRs #280-#288.
- Does not modify F1/F2 verdicts (#284, #287).
- Does not relax NG#10 / NG#11.
- Does not modify γ closure (PR #279).
- Does not pre-approve threshold or directional pipeline for
  production.
- Does not pre-approve any production deployment.
- Does not update MEMORY.md.

## §15. Files

| Path | Status | Lines |
|---|---|---|
| `docs/design/phase25_0d_deployment_audit_design.md` | NEW | this file |

**Single file. No `artifacts/` entry. No `tests/` entry. No
`scripts/` entry. No `src/` change. No DB schema change. No
MEMORY.md update. Existing 22.x/23.x/24.x/25.x docs/artifacts:
unchanged. NG#10/NG#11: not relaxed. γ closure (PR #279):
preserved.**

## §16. CI surface

- `python tools/lint/run_custom_checks.py` (rc=0 expected;
  doc-only)
- `pytest` (no test changes; existing tests untouched)

---

**Phase 25.0d-α — deployment-layer audit design contract locked. Implementation in 25.0d-β. F1+F2 best cells only; H-A/H-B/H-D/H-F empirical+theoretical tests. Diagnostic-only; no production pre-approval.**
