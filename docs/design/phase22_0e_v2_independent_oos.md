# Phase 22.0e-v2 Independent OOS Validation

**Date**: 2026-05-06
**Status**: ACTIVE — research-only, single-cell verification of PR #259's PROMISING_BUT_NEEDS_OOS finding
**Parent design**: `docs/design/phase22_main_design.md`
**Companion**: `docs/design/phase22_0e_meta_labeling.md` (PR #259)
**Audit go-conditions**: `docs/design/phase22_research_integrity_audit.md` §13

---

## 1. Hypothesis

PR #259's best cell (N=50, conf=0.55, horizon=40, exit=`time_exit_pnl`) was the result of a 48-cell sweep. Its OOS predictions came from rolling walk-forward folds where each fold's training data may have included test windows of other folds.

This PR tests whether **the same cell, with no re-tuning**, survives a stricter chronological hold-out: train on the **first 80%** of the 730-day data, test on the **last 20%** (~146 days), with no overlap and no peeking.

Two specific questions:

1. **Reproducibility**: do A1 (Sharpe ≥ +0.082) and A2 (annual_pnl ≥ +180) hold on the held-out tail?
2. **Risk concentration**: is A3's MaxDD = 355.7 from PR #259 a structural feature of the strategy or a concentrated-trade artifact (few worst trades / one pair / one period)?

**Prior expectation**: tentatively PROMISING_CONFIRMED. PR #259's S0 (shuffled-target = 0.0) and S1 (gap = 0.17) are clean — no contamination signal. The cell's Sharpe 0.14 is modest but above baseline. The MaxDD blow-out is the genuine concern; this PR's diagnostics will frame whether it's a structural risk-control problem or a concentration phenomenon.

---

## 2. Frozen specification — DO NOT VARY

Hard-coded constants asserted by unit tests:

```python
PRIMARY_SIGNAL = "donchian_immediate"
N_DONCHIAN = 50
CONF_THRESHOLD = 0.55
HORIZON_BARS = 40
EXIT_RULE = "time_exit_pnl"
FEATURE_SET = MAIN_FEATURE_COLS  # imported from stage22_0e_meta_labeling
                                 #   (no hour_utc, no dow, no is_week_open_window)
```

A unit test asserts no sweep loop in the script (`for n in N_DONCHIAN_VALUES`, `for ct in CONF_THRESHOLDS`, etc. are absent).

The script imports the following from `scripts/stage22_0e_meta_labeling`:

```python
from stage22_0e_meta_labeling import (
    MAIN_FEATURE_COLS, FORBIDDEN_FEATURES,
    causal_zscore, aggregate_m1_to_m5_mid, detect_donchian_breakouts,
    build_signal_dataset, train_model,
    early_stopping_split,
    EVAL_SPAN_YEARS_DEFAULT,
    LGBM_PARAMS,
    ADOPT_MIN_TRADES, ADOPT_MIN_SHARPE, ADOPT_MIN_PNL, ADOPT_MAX_DD,
    ADOPT_MIN_FOLD_POSNEG, S0_HARD_GATE, S0_DIAGNOSTIC, S1_MAX_TRAIN_TEST_GAP,
    OVERTRADE_WARN_TRADES,
    PAIRS_CANONICAL_20,
)
```

PR #259's behaviour is **not** modified.

---

## 3. Train / OOS split — strict chronological hold-out

### 3.1 Split definition

```
total_signals = build_signal_dataset(pair, N=50)  # for all 20 pairs, concat
                # then sort by entry_ts ascending

cut_ts = quantile(entry_ts, 0.80)
train_set = signals where entry_ts <= cut_ts          # ~80%
oos_set   = signals where entry_ts >  cut_ts          # ~20%
```

The OOS set is the chronological **tail**; no future data leaks into training.

### 3.2 Early-stopping validation (within-train, time-ordered)

Within the 80% train range, the **last 20% (chronologically)** is held out for early-stopping validation:

```
es_cut = quantile(train_entry_ts, 0.80)
fit_idx = train_entry_ts <= es_cut    # 64% of total
val_idx = train_entry_ts >  es_cut    # 16% of total
```

A unit test asserts random splits are **not** used.

### 3.3 Single model

ONE LightGBM model is trained on the fit set, validated on the val set (early-stopping), and applied to the OOS set. **No walk-forward inside this PR.**

### 3.4 Cross-pair model

`pair` and `direction` are categorical features (matching PR #259). One model jointly trained across 20 pairs and both directions.

---

## 4. OOS sub-folds (DIAGNOSTIC ONLY — not training)

The OOS window is divided into **4 chronological sub-folds** of equal size (~36.5 days each) for stability diagnostics:

```
oos_edges = quantile(oos_entry_ts, [0, 0.25, 0.50, 0.75, 1.0])
sub_fold[k] = oos rows in (oos_edges[k], oos_edges[k+1]]   for k = 0..3
```

These are **NOT** used for any training or model selection. They exist exclusively to compute fold-level Sharpe / PnL / pos/neg counts for the A4 gate and stability diagnostics.

A unit test asserts the script never trains a model conditioned on sub-fold membership.

---

## 5. Hard ADOPT criteria — eight gates (audit-aligned)

| # | Criterion | Note |
|---|---|---|
| **A0** | OOS annual_trades ≥ 70 | annualised over the OOS span (~0.4 years) |
| **A1** | OOS Sharpe ≥ +0.082 | per-trade, no sqrt-of-N |
| **A2** | OOS annual_pnl ≥ +180 pip | annualised over the OOS span |
| **A3** | OOS MaxDD ≤ 200 pip | over the chronologically-pooled OOS PnL stream |
| **A4** | OOS sub-fold pos/neg ≥ 3/1 | 3 of 4 sub-folds positive |
| **A5** | OOS spread +0.5 pip stress annual_pnl > 0 | per-trade tax |
| **S0** | \|shuffled_sharpe\| < 0.10 (hard); 0.05 reported as diagnostic | shuffle the **train-set** y, retrain, predict on OOS |
| **S1** | mean(train_sharpe − OOS_sharpe) ≤ 0.30 | train-set sharpe is on filtered conf≥0.55 trades within the 80% train range |

`best_possible_pnl` is N/A (single cell uses `time_exit_pnl` only).

### 5.1 OOS span and annualisation

OOS span = (oos_entry_ts.max() - oos_entry_ts.min()) / 365.25 days. Annual metrics use this span (NOT the full 730-day span used in PR #259 — because the OOS window is only 20% of the data, ~0.4 years).

This makes the OOS annualisation directly comparable to baseline `+180 pip/year` and `+0.082 Sharpe`.

---

## 6. Verdict classification (3-class — user-revised boundaries)

| Verdict | Condition |
|---|---|
| **ADOPT** | A0–A5 + S0 + S1 ALL pass. Not production-ready — paper-run is the next layer. |
| **PROMISING_CONFIRMED** | A1 ≥ baseline AND A2 ≥ baseline AND S0 PASS AND S1 PASS, but at least one of A3/A4/A5 fails (risk gate). |
| **FAILED_OOS** | A1 OR A2 fails (signal didn't survive the held-out tail), OR S0 fails (contamination), OR S1 fails (overfit). |

The user-revised boundary: A4 alone failing → PROMISING_CONFIRMED (not FAILED_OOS). A3 alone failing → PROMISING_CONFIRMED. A1 OR A2 fail → FAILED_OOS. A0 fail (insufficient trades) → FAILED_OOS (treated as A0 below threshold = no statistical power).

---

## 7. Drawdown concentration analysis (mandatory, all 5)

Required outputs in the eval report regardless of verdict.

### 7.1 Worst trades
Top 20 single-trade most-negative PnLs:
- entry_ts, pair, direction, predicted_P, realised_pnl
- Sum of top-20 worst as % of total negative PnL → tells us how concentrated the loss is

### 7.2 Worst pair
Per-pair OOS PnL aggregation, sorted by sum_pnl ascending:
- n_trades, sum_pnl, mean_pnl, per-pair MaxDD
- Identify the pair contributing the most to total MaxDD

### 7.3 Worst OOS sub-fold
Per-sub-fold (4 buckets) PnL:
- n_trades, sum_pnl, mean_pnl, sub-fold MaxDD, time-range
- Identify the worst sub-fold and its date range

### 7.4 Consecutive losses
- Longest run of consecutive losing trades on the chronologically-ordered OOS stream
- Histogram of consecutive-loss-run lengths

### 7.5 Pair / session concentration
- Per-pair share of total absolute PnL (Gini-like dispersion)
- Per-session (Tokyo 0-7 / London 7-14 / NY 14-21 / Rollover 21-24 UTC) PnL contribution
- Note: session bucketing uses `hour_utc` for **diagnostic only**, NOT as a model feature (matches audit policy; `hour_utc` is in the diagnostic set, not main features)

### 7.6 Conclusion attribution

The report must explicitly attribute the A3 MaxDD failure (if any) to **one** of:
- **Few-trade concentration**: top-20 worst account for >60% of negative PnL
- **Single-pair concentration**: 1 pair contributes >40% of MaxDD
- **Single-period concentration**: 1 sub-fold contributes >40% of MaxDD
- **Consecutive-loss streak**: longest streak ≥ 10
- **Distributed**: no single dimension dominates

This attribution informs (but does NOT prescribe) any future risk-control PR.

---

## 8. Multiple-testing & independence caveat (mandatory in report)

> ⚠ This is an OOS validation of a single cell pre-selected from a 48-cell
> sweep in PR #259. The OOS window is a chronological hold-out from the same
> 730-day OANDA pull, NOT a fresh fetch. ADOPT here means:
>
> 1. The PR #259 cell was not a multiple-testing artifact (its alpha survives
>    a held-out tail).
> 2. The eight gates are met without re-tuning.
>
> ADOPT does NOT mean production-ready. A separate paper-run on bars beyond
> the 730-day pull is the next layer of validation.

---

## 9. Files

| File | Type | Lines (target) |
|---|---|---|
| `docs/design/phase22_0e_v2_independent_oos.md` | Design (this) | ~250 |
| `scripts/stage22_0e_v2_independent_oos.py` | Research script | ~500 |
| `tests/unit/test_stage22_0e_v2_oos.py` | Tests | ~250 |
| `artifacts/stage22_0e_v2/eval_report.md` | Report | committed |
| `artifacts/stage22_0e_v2/run.log` | Run log | committed |
| `artifacts/stage22_0e_v2/oos_trades.parquet` | OOS trade list | regenerable, NOT committed |

---

## 10. Tests (unit)

### 10.1 Frozen-parameter assertions
- `test_n_donchian_frozen_at_50`
- `test_conf_threshold_frozen_at_055`
- `test_horizon_frozen_at_40`
- `test_exit_rule_frozen_at_time_exit_pnl`
- `test_feature_set_is_main_only` — uses `stage22_0e.MAIN_FEATURE_COLS` exactly
- `test_no_sweep_loops_in_script` — text grep

### 10.2 Train/OOS split
- `test_train_first_80pct_oos_last_20pct` — by entry_ts
- `test_train_oos_no_temporal_overlap` — train.max < oos.min
- `test_es_split_uses_time_ordered_last_20pct_of_train` — NOT random
- `test_oos_4_sub_folds_chronological_no_training_role` — diagnostic only

### 10.3 Verdict logic (user-revised boundaries)
- `test_verdict_adopt_when_all_eight_gates_pass`
- `test_verdict_promising_confirmed_when_a3_fails`
- `test_verdict_promising_confirmed_when_a4_fails`
- `test_verdict_promising_confirmed_when_a5_fails`
- `test_verdict_failed_oos_when_a1_fails`
- `test_verdict_failed_oos_when_a2_fails`
- `test_verdict_failed_oos_when_a0_fails`
- `test_verdict_failed_oos_when_s0_fails`
- `test_verdict_failed_oos_when_s1_fails`

### 10.4 Drawdown diagnostics
- `test_worst_trades_top_20_returned`
- `test_per_pair_pnl_aggregation_present`
- `test_consecutive_loss_run_length_correct`
- `test_attribution_categorises_correctly` — synthetic data per category

### 10.5 Audit allowlist re-assertion
- `test_main_feature_cols_unchanged_from_pr_259`
- `test_no_hour_utc_no_dow_no_is_week_open_window_in_features`

~16 tests, ~250 lines.

---

## 11. NG list compliance (postmortem §4)

| # | NG | Compliance |
|---|---|---|
| 1 | Pair tier filter | All 20 pairs in train and OOS |
| 2 | Train-side time-of-day filter | None |
| 3 | Test-side filter improvement claim | OOS verdict on full last-20% slice; no time-of-day cherry-pick |
| 4 | WeekOpen-aware sample weighting | None |
| 5 | Universe-restricted cross-pair feature | None |

---

## 12. Out of scope

- src/, scripts/run_*.py, DB schema (Phase 22 invariant)
- Any re-search of N / conf_threshold / horizon / exit_rule / feature set (FORBIDDEN)
- `hour_utc` / `dow` as headline features (used in §7.5 diagnostics only)
- Pair filter / time filter (NG list)
- Trailing-stop / partial-exit rules
- Risk-control filters (this PR analyses, does NOT prescribe)
- Live OANDA fetch / paper run (separate PR after verdict)

---

## 13. Conventions (matching PR #259)

- Sharpe = mean / std (per-trade, no sqrt-of-N annualisation)
- Annualisation uses **OOS span** (NOT 2 years) — the OOS window is ~0.4 years
- Filter `valid_label & ~gap_affected_forward_window` applied uniformly upstream (in `build_signal_dataset`)
- LightGBM hyperparameters identical to PR #259's `LGBM_PARAMS`

---

## 14. Estimated effort

| Step | Time |
|---|---|
| Design doc | 45 min |
| Script (reuse 22.0e helpers; single train + OOS + diagnostics + report) | 90 min |
| Tests (~16) | 60 min |
| Run (single model train + predict + diagnostics) | < 5 min |
| Verdict report | 45 min |
| PR + CI | 30 min |

Total: **~4-5 hours**.

---

**Status: ACTIVE.** PR2 of Phase-22 (-e-v2) implementation references this design directly.
