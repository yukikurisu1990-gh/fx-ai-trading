# Phase 22.0b Mean Reversion Baseline

**Date**: 2026-05-05
**Status**: ACTIVE — research-only, follows PR2 (22.0a outcome dataset)
**Parent design**: `docs/design/phase22_main_design.md`
**Outcome dataset**: `artifacts/stage22_0a/labels/labels_<pair>.parquet`

---

## 1. Hypothesis

When the M1 mid close is `threshold` standard deviations away from a short rolling mean, the next forward window has mean-reverting drift that, **after spread cost**, exceeds zero EV under a realistic exit rule.

Formally — there exists a cell `(N, threshold, horizon, exit_rule ∈ {tb_pnl, time_exit_pnl})` such that

- Sharpe ≥ +0.0822 (B Rule baseline)
- annual PnL ≥ +180 pip (B Rule baseline)
- spread +0.5 pip stress annual PnL > 0
- 5-fold pos/neg ≥ 4/1
- annual trades ≥ 70

**Prior expectation: NO ADOPT.** The 22.0z-1 finding of M1 spread/ATR ≈ 128% means typical mean-reversion targets (≤ 1×ATR) are below spread cost. This PR formally tests and documents the failure mode (or — surprise — finds a working corner of the parameter space).

## 2. Strategy parameterization

### 2.1 Sweep dimensions

| Dimension | Values | Cells |
|---|---|---|
| Rolling window N (M1 bars) | {10, 20, 50, 100} | 4 |
| z-threshold | {1.5, 2.0, 2.5, 3.0} | 4 |
| Horizon (M1 bars) | {5, 10, 20, 40} (= outcome dataset native) | 4 |
| Exit rule | `tb_pnl`, `time_exit_pnl`, `best_possible_pnl` | 3 |

Total: **192 cells** = 4×4×4×3.

`best_possible_pnl` is included **for diagnostic / failure-mode analysis only** — it is the post-hoc upper bound (path peak) and **never enters ADOPT judgement** (§5).

### 2.2 Multiple testing bias

192 cells per pair × 19 pairs (CAD_JPY excluded — see §11) is a **large search space**. The best cell is discovered, not pre-registered. We follow Phase 9 convention:

- All-data + 5-fold walk-forward results are reported for the top-K cells.
- Best-cell verdict is *exploratory*; production migration requires **independent OOS validation** (held-out time slice, fresh fetch, or paper run).
- The eval report includes a **multiple-testing-bias warning** prominently in the verdict section.

### 2.3 Signal definition (causal)

```
mid_close[t]  = (bid_c[t] + ask_c[t]) / 2
mu[t]         = rolling_mean(mid_close, N) over bars ≤ t
sigma[t]      = rolling_std(mid_close, N) over bars ≤ t      # ddof=0
z[t]          = (mid_close[t] - mu[t]) / sigma[t]            # NaN if sigma == 0

if z[t] < -threshold: signal = long
elif z[t] > +threshold: signal = short
else: no signal
```

`mu[t]` and `sigma[t]` strictly use bars `≤ t`. This is enforced by causal rolling windows (no `.shift(-1)` or future-leaning resample). A unit test asserts that perturbing bar `t+1..end` does not change `z[t]`.

The signal does **not** drop rows on context flags (`is_week_open_window`, `hour_utc`, `dow`). Those are NG-listed in `phase22_alternatives_postmortem.md` §4.

## 3. Evaluation pipeline

For each cell `(N, threshold, horizon, exit_rule)`:

1. For each pair, compute `z[t]` causally on M1 mid close.
2. Build entry tuples `(entry_ts, pair, horizon_bars=horizon, direction=sign(-z))` where `|z| > threshold`.
3. **Inner-join** these tuples against `labels_<pair>.parquet`. Filter:
   - `valid_label == True`
   - `gap_affected_forward_window == False` (excluded for cleanliness; reported separately)
4. Read the `exit_rule` column as the per-trade PnL.
5. Aggregate to per-cell metrics.

### 3.1 Cell metrics (all-data)

- `n_trades` (over the full eval span)
- `annual_pnl_pip` = sum(PnL) / span_years (span_years = 730/365.25 ≈ 2.0)
- `mean_pnl`, `std_pnl` (population std, ddof=0)
- `sharpe` = `mean_pnl / std_pnl` (per-trade, **no sqrt-of-N annualization**, matching the Phase 9 convention in `compare_multipair_v19_causal.py:_sharpe`. The B Rule baseline +0.0822 is reported under the same convention; this keeps the Phase 22 verdicts directly comparable.)
- `max_dd_pip` over the chronologically-pooled equity curve
- `dd_pct_pnl` = max_dd / abs(annual_pnl) × 100
- `annual_trades` = n_trades / span_years

### 3.2 5-fold walk-forward (mandatory for top-K cells)

After all-data sweep, **re-evaluate the top-K cells (K=10)** on five non-overlapping time-ordered folds:
- Sort all entries by `entry_ts`
- Split equally into 5 contiguous folds
- Per fold: `n`, PnL, mean, std, fold-sharpe
- Aggregate: `pos/neg` ratio, fold-PnL stdev, fold-PnL CV, fold-concentration (top fold's share of total PnL)

### 3.3 Spread stress

Apply post-hoc spread tax to **every** cell entry's PnL:
- `pnl_stress_+0.2 = pnl - 0.2`
- `pnl_stress_+0.5 = pnl - 0.5`

Aggregate the same metrics on stressed PnL streams.

### 3.4 Cost diagnostics (mandatory for top-K)

For top-K cells:
- median `spread_entry`
- median `cost_ratio` (= spread_entry / atr_at_entry, in pip ratio)
- PnL by `cost_ratio` bucket: {(0, 0.5], (0.5, 1.0], (1.0, 1.5], (1.5, 2.0], (2.0, ∞)}
- PnL by `spread_entry` bucket: {(0, 1], (1, 2], (2, 3], (3, ∞)} pip
- Per-pair contribution of total cell PnL
- Per-session contribution: hour_utc bucketed into {Tokyo 0-7, London 7-14, NY 14-21, rollover 21-24}

## 4. Hard ADOPT criteria

A cell is ADOPT-candidate iff it passes all six hard gates **on a realistic exit rule** (`tb_pnl` or `time_exit_pnl`):

| # | Criterion |
|---|---|
| **A0** | `annual_trades ≥ 70` (overtrading warning emitted but not blocking when `annual_trades > 1000`) |
| **A1** | Sharpe ≥ +0.082 |
| **A2** | annual PnL ≥ +180 pip |
| **A3** | MaxDD ≤ 200 pip |
| **A4** | 5-fold pos/neg ≥ 4/1 |
| **A5** | spread +0.5 pip stress annual PnL > 0 |

Only `tb_pnl` and `time_exit_pnl` are eligible for ADOPT judgement.
**`best_possible_pnl` is diagnostic only and never passes A1/A2/A3/A5.**

## 5. Verdict classification

| Verdict | Condition |
|---|---|
| **ADOPT** | A0–A5 all pass on a realistic exit rule |
| **PROMISING_BUT_NEEDS_OOS** | A0–A3 pass but A4 (fold stability) and/or A5 (spread stress) fail |
| **REJECT** | A1 or A2 fail (Sharpe or PnL below baseline on any realistic exit rule) |

The verdict applies to the single best cell selected by:
- Primary key: A1 (Sharpe) on `tb_pnl`
- Tiebreak: A2 (annual PnL), then n_trades

If multiple cells reach ADOPT, the report lists them but the headline verdict is still tied to the best-Sharpe cell.

## 6. Diagnostic-only outputs (not pass/fail)

- 192-cell sweep heatmap (Sharpe and PnL) — per exit_rule
- Top-10 cells full-eval table (with 5-fold metrics, cost decomposition)
- `best_possible_pnl - tb_pnl` gap per top cell — **failure mode analysis**:
  - Large gap (> 50% of `best_possible_pnl`) → "exit is bad, path was favorable" → suggests trailing stop / partial exit study
  - Small gap (< 20%) → "no path EV to capture" → mean reversion has no signal here
- `tb_pnl` vs `time_exit_pnl` difference per top cell — characterizes whether TP/SL is helping or hurting
- z-score distribution histogram per pair (sanity)
- Spread stress: +0.2 pip and +0.5 pip both reported

## 7. Files

| File | Type | Lines (target) |
|---|---|---|
| `docs/design/phase22_0b_mean_reversion_baseline.md` | Design (this file) | ~250 |
| `scripts/stage22_0b_mean_reversion_baseline.py` | Research script | ~500 |
| `tests/unit/test_stage22_0b_mr.py` | Unit tests | ~250 |
| `artifacts/stage22_0b/sweep_results.parquet` | Output | regenerable, NOT committed |
| `artifacts/stage22_0b/eval_report.md` | Report | committed |
| `artifacts/stage22_0b/run.log` | Run log | committed |

## 8. Tests (unit)

- `test_zscore_causal_no_lookahead` — perturbing future bars doesn't change z[t]
- `test_zscore_signal_directions` — z < -threshold → long; z > +threshold → short
- `test_outcome_join_uses_correct_keys` — cell joins on (entry_ts, pair, horizon_bars, direction)
- `test_filter_excludes_invalid_and_gap_rows` — both flags excluded
- `test_no_week_open_filter_applied` — strategy never inspects is_week_open_window
- `test_no_pair_filter_applied` — all 19 available pairs are in the cell aggregation
- `test_walkforward_5fold_split` — time-ordered fold slicing, no leakage
- `test_spread_stress_applied_to_all_entries` — +0.5 pip stress reduces every PnL by 0.5
- `test_best_possible_excluded_from_adopt_judgement` — verdict logic refuses to use it
- `test_overtrading_warning_threshold` — annual_trades > 1000 triggers warning string
- `test_minimum_trades_a0_blocks_adopt` — annual_trades < 70 → REJECT before A1
- `test_diagnostic_buckets_disjoint` — cost_ratio / spread buckets cover full range
- ~12 tests, ~250 lines

## 9. NG list compliance (postmortem §4)

| # | NG | Compliance approach |
|---|---|---|
| 1 | Pair tier filter | All 19 available pairs evaluated; per-pair contribution reported but never used to prune cells |
| 2 | Train-side time filter | Strategy uses all bars; z-score uses no time gate |
| 3 | Test-side filter improvement claim | Best-cell verdict is on **all valid rows**, not a time-of-day subset |
| 4 | WeekOpen-aware sample weighting | None |
| 5 | Universe-restricted cross-pair feature | None |

A unit test (`test_no_week_open_filter_applied`) asserts no row drop occurs based on `is_week_open_window`.

## 10. Out-of-scope

- src/fx_ai_trading/* (any file)
- scripts/run_paper_decision_loop.py, run_live_loop.py
- DB schema (decision_log, close_events, orders, position_open)
- src/fx_ai_trading/domain/reason_codes.py
- Outcome dataset schema modification
- M5 horizon evaluation (deferred per phase22_0a_scalp_label_design §3.2)

## 11. Pair coverage note

PR 22.0b uses the **canonical 20-pair list** from production
(`compare_multipair_v19_causal.py:DEFAULT_PAIRS`). All 20 candle files
are present locally; the report's "Pair coverage" section will state
`20 / 20 canonical (missing: none)`. If a future run encounters a
missing file, it is caught (`FileNotFoundError`), logged as `SKIP`,
and the report includes the missing pair list. (An earlier PR2 plan
draft incorrectly noted CAD_JPY as part of the canonical 20; the
canonical list does not include CAD_JPY at all — `GBP_CHF` is the
20th. PR2's `label_validation_report.md` lists 20 rows.)

## 12. Multiple testing bias warning (mandatory in report)

The report's verdict section opens with:

> ⚠ **Multiple testing caveat**: 192 cells were searched. The reported best
> cell's Sharpe / PnL are *in-sample search results*. Production migration
> of any ADOPT-classified cell requires independent OOS validation
> (held-out future time slice, paper-run, or fresh data fetch). The
> ADOPT classification here means "passes all 6 in-sample gates" — not
> "production-ready".

## 13. Estimated effort

| Step | Time |
|---|---|
| Design doc (this file) | 60 min |
| Script (causal z-score, parquet join, 192-cell sweep, walk-forward, cost diagnostics, stress) | 180 min |
| Tests (12) | 80 min |
| Sweep run on 19 pairs × 192 cells | 30–60 min |
| Walk-forward on top-10 + cost diagnostics | 30 min |
| Verdict report | 50 min |
| PR + CI | 30 min |

Total: **~7.5 hours**.

---

**Status: ACTIVE.** PR2-of-Phase-22 implementation references this design directly.
