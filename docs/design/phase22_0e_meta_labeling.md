# Phase 22.0e Meta-Labeling

**Date**: 2026-05-06
**Status**: ACTIVE — research-only, follows audit PR #258 (VERDICT: PASS)
**Parent design**: `docs/design/phase22_main_design.md`
**Companion docs**:
- `docs/design/phase22_0a_scalp_label_design.md` (outcome dataset)
- `docs/design/phase22_0b_mean_reversion_baseline.md` (REJECT)
- `docs/design/phase22_0c_m5_breakout_m1_entry_hybrid.md` (REJECT)
- `docs/design/phase22_research_integrity_audit.md` (PASS — feature-allowlist policy)

---

## 1. Hypothesis

A LightGBM binary classifier trained on **causal context features only** can rank Donchian breakout signals by `P(profitable)` such that high-confidence trades (after `conf_threshold` filter) have **OOS** Sharpe ≥ +0.082 and OOS annual_pnl ≥ +180 pip on the 22.0a outcome dataset.

Two specific claims tested:

1. **Filter claim**: The classifier ranks trades non-randomly by P(profitable) — confirmed by shuffled-target sanity (S0).
2. **Generalisation claim**: train Sharpe and OOS Sharpe agree within hygiene tolerance — confirmed by train-test parity gate (S1), and OOS metrics survive the standard six gates A0..A5.

**Prior expectation**: REJECT or PROMISING_BUT_NEEDS_OOS. The audit (PR #258 §8) showed `best_possible_pnl - time_exit_pnl` median 3.9 pip per trade — path EV genuinely exists. Meta-labeling tests whether causal features alone can pre-filter the destroyed cases.

## 2. Scope and constraints

- **Research-only PR**. No src/, no scripts/run_*.py, no DB schema.
- 20-pair canonical universe; no pair filter; no time-of-day filter.
- Reuses 22.0a outcome dataset (`artifacts/stage22_0a/labels/labels_<pair>.parquet`).
- Reuses 22.0b/c harness (CellAcc, fold split, spread stress, verdict, cost diagnostics) — copy-paste, with the same harness-extraction-deferred note as 22.0c.
- Honours all NG list items (postmortem §4) and the audit's feature-allowlist policy (PR #258 §10).

## 3. Primary signal source

- **Donchian-immediate breakout** from 22.0c (the breakout style with the highest signal volume; immediate-entry has zero skipped trades and so produces the largest training set).
- N ∈ {20, 50} (M5 bars). N=10 is too noisy; N=100 has too few signals after the conf_threshold filter.
- Entry timing fixed to **immediate** (the M1 bar with timestamp `> signal_ts_M5`).

Z-score primary (22.0b's strategy as primary source) is **deferred** to a follow-up if 22.0e ADOPTs.

## 4. Sweep dimensions

| Dimension | Values | Cells |
|---|---|---|
| Donchian N (M5 bars) | {20, 50} | 2 |
| Confidence threshold | {0.50, 0.55, 0.60, 0.65} | 4 |
| Horizon (M1 bars) | {10, 20, 40} | 3 |
| Exit rule | `tb_pnl`, `time_exit_pnl` | 2 |

Total: **48 cells** (smallest sweep of all 22.0 stages — multiple-testing footprint deliberately tightest).

`best_possible_pnl` is **excluded from the sweep entirely** (diagnostic-only — was forced REJECT in 22.0b/c). Including it adds noise without informational value.

## 5. Meta-label `y` (cell-dependent)

The label is the **sign of the realised PnL under the cell's exit rule**:

```python
if exit_rule == "tb_pnl":
    y = (tb_pnl > 0).astype(int)
elif exit_rule == "time_exit_pnl":
    y = (time_exit_pnl > 0).astype(int)
```

A `tb_pnl`-cell asks "did the triple-barrier outcome close positive?". A `time_exit_pnl`-cell asks "did the time-exit close positive?". Each cell has its own label vector; the model is trained per (N, horizon, exit_rule) with that cell's `y`.

`conf_threshold` is a **post-prediction filter** — the same model serves all 4 confidence-threshold cells under a given (N, horizon, exit_rule).

A unit test asserts that `y` derives **only from the cell's exit_rule column**, never from `mfe`, `mae`, `time_to_*`, or other forward-looking columns beyond the chosen exit_rule.

## 6. Feature layer (audit-mandated allowlist)

### 6.1 `MAIN_FEATURE_COLS`

Strict equality with the audit's allowlist (PR #258 §10):

```python
MAIN_FEATURE_COLS = (
    "cost_ratio",          # spread_entry / atr_at_entry, signal-time
    "atr_at_entry",        # M1 ATR(14) at signal bar (pip)
    "spread_entry",        # spread at signal bar (pip)
    "z_score_10",          # causal rolling z(10) on M1 mid_close at signal_ts
    "z_score_20",
    "z_score_50",
    "z_score_100",
    "donchian_position",   # signed distance from break level / atr_at_entry
    "breakout_age_M5_bars", # M5 bars since previous same-direction breakout
    "pair",                # categorical (LightGBM natively handles)
    "direction",           # categorical (long / short)
)
```

### 6.2 Forbidden in main features (asserted by unit test)

```python
FORBIDDEN_FEATURES = (
    # User-modified policy:
    "is_week_open_window", "hour_utc", "dow",
    # Forward-looking outcome columns:
    "mfe_after_cost", "mae_after_cost", "best_possible_pnl",
    "time_exit_pnl", "tb_pnl", "tb_outcome",
    "time_to_tp", "time_to_sl", "same_bar_tp_sl_ambiguous",
    "path_shape_class", "exit_bid_close", "exit_ask_close",
    "valid_label", "gap_affected_forward_window",
)
```

`set(MAIN_FEATURE_COLS) ∩ FORBIDDEN_FEATURES == ∅` is an integration-time assertion.

### 6.3 Ablation-only features

`hour_utc` and `dow` are computed and stored alongside the signal dataset, but **not** included in the main model. They are used in:

- **Ablation-A** (mandatory): `MAIN + ("hour_utc",)` — re-train and re-evaluate
- **Ablation-B** (conditional): `MAIN + ("hour_utc", "dow")` — only run if Ablation-A shows a clear lift (best-cell Sharpe lift ≥ 0.05)

Ablation results are reported in the eval doc but **never enter the headline verdict**.

## 7. Causal feature computation

For each Donchian breakout at M5 bar `T`:

| Feature | Formula | Causality |
|---|---|---|
| `cost_ratio` | from labels parquet at signal bar (signal_ts = M1 timestamp matching M5 close T) | atr & spread at bar ≤ T |
| `atr_at_entry` | from labels parquet | bar ≤ T |
| `spread_entry` | from labels parquet | bar ≤ T |
| `z_score_N` | `causal_zscore(M1 mid_close, N)` evaluated at M1 timestamp T | rolling on bars ≤ T |
| `donchian_position` | `(mid_close[T] - hi_N[T]) / atr_at_entry` for long; `(mid_close[T] - lo_N[T]) / atr_at_entry` for short | hi_N excludes current bar (shift(1) Donchian) |
| `breakout_age_M5_bars` | M5 bars since previous same-direction Donchian-N breakout (capped at 1000) | uses past breakouts only |

A unit test asserts that perturbing future M1 bars does not change any feature value at signal time.

## 8. Cross-pair model

One LightGBM model per **(N, horizon, exit_rule, fold, feature_set)**.

`pair` is a categorical feature. `direction` is also categorical. The model jointly learns across all 20 pairs and both directions; per-pair contributions are reported but not used to prune cells.

LightGBM hyperparameters (matching `compare_multipair_v19_causal.py:DEFAULT_PARAMS`):

```python
{
    "objective": "binary",
    "metric": "binary_logloss",
    "num_leaves": 31,
    "learning_rate": 0.05,
    "n_estimators": 200,
    "min_data_in_leaf": 100,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.9,
    "bagging_freq": 5,
    "verbose": -1,
}
```

**Early-stopping validation split** (audit-mandated): the validation set is the **time-ordered last 20% of the train period** (NOT random). Random splits leak future-into-past in time-series.

```python
# In a fold's train range [t_min, edge_k]:
val_cut = quantile(train_entry_ts, 0.80)
fit_idx = train_entry_ts <= val_cut
val_idx = train_entry_ts > val_cut
```

## 9. Walk-forward 4-fold OOS

Time-ordered 5-quintile split. Folds k=1..4 train on `[t_min, edges[k]]` and test on `(edges[k], edges[k+1]]`. **Fold k=0 is dropped** (train too small).

Pooled OOS predictions across folds k=1..4 give 4/5 of the dataset as OOS coverage. Cell metrics are computed on this pooled OOS PnL stream.

Per-fold metrics also tracked for fold-stability gates (A4).

## 10. Hard ADOPT criteria — eight gates

A cell is **ADOPT** iff all eight gates pass on **OOS predictions**:

| # | Criterion | Note |
|---|---|---|
| **A0** | annual_trades ≥ 70 (overtrading warning > 1000) | matches 22.0b/c |
| **A1** | OOS Sharpe ≥ +0.082 | matches 22.0b/c (per-trade Sharpe, no sqrt-of-N) |
| **A2** | OOS annual_pnl ≥ +180 pip | matches 22.0b/c |
| **A3** | OOS MaxDD ≤ 200 pip | matches 22.0b/c |
| **A4** | **OOS 4-fold pos/neg ≥ 3/1** | **revised** (was 4/1; 4 OOS folds → 3/1) |
| **A5** | OOS spread +0.5 pip stress annual_pnl > 0 | matches 22.0b/c |
| **S0** | **`|shuffled_sharpe| < 0.10`** (hard gate); `< 0.05` reported as diagnostic | **revised** (was 0.05) |
| **S1** | mean(train_sharpe − test_sharpe) ≤ 0.30 | NEW — meta-specific |

`best_possible_pnl` is N/A (excluded from sweep). Even if accidentally introduced, `classify_cell` continues to force REJECT (matching 22.0b/c convention).

## 11. Verdict classification (3-class)

| Verdict | Condition |
|---|---|
| **ADOPT** | A0–A5 + S0 + S1 all pass |
| **PROMISING_BUT_NEEDS_OOS** | A0–A3 + S0 + S1 pass, A4 OR A5 fail |
| **REJECT** | A0/A1/A2 fail, OR S0 fail, OR S1 fail |

Best cell selected by Sharpe; tiebreak by annual_pnl, then n_trades.

## 12. Shuffled-target sanity (S0)

For each cell:
1. Compute baseline OOS Sharpe via the standard pipeline.
2. **Within-fold shuffle** the `y` vector (preserves train/test split structure but breaks feature → label association).
3. Re-train and re-predict per fold. Pool OOS predictions.
4. Report:
   - `shuffled_sharpe`
   - `shuffled_sharpe_diagnostic_005 = bool(|shuffled_sharpe| < 0.05)` — informational
   - `shuffled_sharpe_hard_gate_010 = bool(|shuffled_sharpe| < 0.10)` — hard gate
5. **S0 fails** when `|shuffled_sharpe| ≥ 0.10`.

If S0 fails, the model is contaminated — non-ADOPT regardless of A0–A5.

## 13. Train-test parity (S1)

Per fold, log `train_sharpe` (sharpe over the train set's filtered predictions) vs `test_sharpe` (OOS sharpe). Aggregate:

```
train_test_gap = mean(train_sharpe[k] - test_sharpe[k]) for k in 1..4
```

**S1 fails** when `train_test_gap > 0.30`.

## 14. Diagnostic outputs

### 14.1 Carried over from 22.0b/c
- 48-cell sweep table per exit_rule
- Top-10 cells with full eval
- Per-fold PnL + CV + concentration
- Spread stress (+0, +0.2, +0.5)
- Cost diagnostics (cost_ratio bucket, spread bucket, per-pair, per-session)

### 14.2 New for 22.0e (mandatory)
- **Feature importance** per top-10 cell (LightGBM `gain`)
- **Shuffled-target sanity table** per cell: `baseline_sharpe`, `shuffled_sharpe`, both gate / diagnostic outcomes
- **Train-test parity table**: per fold, `train_sharpe`, `test_sharpe`, gap
- **Confidence-bin calibration**: per top cell, predicted-P bins {0.50–0.55, 0.55–0.60, ..., 0.95–1.00} vs realised win rate (should be monotonic)
- **Coverage curve**: per (N, horizon, exit_rule), 4 conf_threshold values → (n_trades, Sharpe) plot data
- **Filter ratio**: filtered n_trades / raw breakout count

### 14.3 Ablation diagnostics
- **Ablation-A (mandatory)**: re-run sweep with `MAIN + ("hour_utc",)`. Report Δ Sharpe / Δ PnL vs main per cell.
- **Ablation-B (conditional)**: only if Ablation-A best-cell Sharpe lift ≥ 0.05. Re-run with `MAIN + ("hour_utc", "dow")`.
- Both ablations are **diagnostic-only** — their cells do NOT enter the headline verdict.

## 15. Files

| File | Type | Lines (target) |
|---|---|---|
| `docs/design/phase22_0e_meta_labeling.md` | Design (this) | ~250 |
| `scripts/stage22_0e_meta_labeling.py` | Research | ~750 |
| `tests/unit/test_stage22_0e_meta_labeling.py` | Tests (~20) | ~350 |
| `artifacts/stage22_0e/sweep_results.parquet` | Output | regenerable, NOT committed |
| `artifacts/stage22_0e/feature_importance.parquet` | Output | regenerable, NOT committed |
| `artifacts/stage22_0e/eval_report.md` | Report | committed |
| `artifacts/stage22_0e/run.log` | Run log | committed |

## 16. Tests (unit)

### 16.1 Audit-mandated allowlist tests
- `test_main_features_match_audit_allowlist`
- `test_main_features_exclude_is_week_open_window`
- `test_main_features_exclude_hour_utc`
- `test_main_features_exclude_dow`
- `test_main_features_exclude_all_forward_looking`
- `test_ablation_a_extra_features_only_hour_utc`
- `test_ablation_b_extra_features_hour_utc_and_dow`

### 16.2 Label-mapping tests (audit-revised)
- `test_y_label_matches_exit_rule_tb_pnl` — y = (tb_pnl > 0)
- `test_y_label_matches_exit_rule_time_exit_pnl` — y = (time_exit_pnl > 0)
- `test_y_uses_no_forward_features_beyond_exit_rule` — only the chosen exit_rule column appears in y derivation

### 16.3 Walk-forward / leakage
- `test_walk_forward_4_fold_chronological_split` — k=1..4, no fold-0
- `test_train_test_no_overlap_per_fold`
- `test_early_stopping_split_uses_time_ordered_last_20pct` — NOT random
- `test_z_score_features_causal`
- `test_donchian_position_feature_causal`
- `test_breakout_age_feature_causal`

### 16.4 Verdict / gates
- `test_a4_threshold_3_of_4_folds`
- `test_s0_hard_gate_at_010_pass`
- `test_s0_hard_gate_at_010_fail`
- `test_s1_train_test_parity_at_030`
- `test_overtrading_warning_threshold`
- `test_minimum_trades_a0_blocks_adopt`

~20 tests, ~350 lines.

## 17. NG list compliance (postmortem §4)

| # | NG | Compliance |
|---|---|---|
| 1 | Pair tier filter | All 20 pairs in training; `pair` is a categorical feature |
| 2 | Train-side time-of-day filter | None — Donchian breakouts use all bars |
| 3 | Test-side filter improvement claim | Verdict on OOS predictions only; no time-of-day cherry-pick |
| 4 | WeekOpen-aware sample weighting | None; `is_week_open_window` excluded entirely |
| 5 | Universe-restricted cross-pair feature | None |

A unit test asserts no row drop based on `is_week_open_window`.

## 18. Out-of-scope

- src/, scripts/run_*.py, DB schema (Phase 22 invariant)
- Z-score primary signal (deferred)
- Combined Donchian + Z-score primary (deferred)
- Trailing-stop / partial-exit rules
- M5 outcome dataset
- Refactor of harness into `phase22_research_lib.py`

## 19. Multiple testing bias

48 cells × 20 pairs is searched on Donchian primary. The eval report's verdict section opens with the in-sample-search caveat — production migration requires independent OOS validation.

## 20. Conventions (matching 22.0b/c)

- Sharpe = mean / std (per-trade, no sqrt-of-N annualisation)
- Annualisation uses fixed dataset span (730 d ≈ 2 years)
- Filter `valid_label & ~gap_affected_forward_window` applied uniformly
- Minimum 30 trades for inclusion in top-K ranking (A0=70 is the ADOPT threshold)

---

**Status: ACTIVE.** PR2-of-Phase-22 (-e) implementation references this design directly.
