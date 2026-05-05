# Phase 22.0c M5 Breakout + M1 Entry Hybrid

**Date**: 2026-05-05
**Status**: ACTIVE — research-only, follows PR2 (22.0a outcome dataset) and PR3 (22.0b mean reversion REJECT)
**Parent design**: `docs/design/phase22_main_design.md`
**Companion**: `docs/design/phase22_0b_mean_reversion_baseline.md` (failure-mode insight on entry/exit gap motivates this PR)

---

## 1. Hypothesis

At M5 timeframe, **Donchian breakout** signals — price closing outside an N-bar Donchian range — produce a path-level edge in the breakout direction over forward 5 / 10 / 20 / 40 M1 bars. The M5-level signal then triggers an M1 entry, where the 22.0a outcome dataset takes over for outcome calculation.

Two specific claims tested:

1. **Signal claim**: Donchian-style M5 breakouts yield a per-trade edge that survives M1 spread cost on the 22.0a outcome dataset.
2. **Entry-timing claim**: M1 entry timing (`immediate` vs `retest` vs `momentum`) materially affects realised PnL — i.e. the 22.0b "path EV exists but exits destroy it" failure mode can be partially closed by choosing better fill timing rather than by exit redesign.

**Prior expectation**: tentatively neutral. M5 spread/ATR ≈ 50% (vs M1's 128%) suggests a lighter cost burden when tied to M5-level dynamics, but Phase 22 has shown nothing works trivially.

---

## 2. Scope notes

> **M5 is signal-side only; outcome remains M1-entry based via the 22.0a dataset.**
> The strategy detects breakouts on M5 (M1→M5 on-the-fly aggregation), but
> entries fire on M1 bars and outcomes are looked up directly from
> `artifacts/stage22_0a/labels/labels_<pair>.parquet`. No new outcome dataset
> is needed (consistent with 22.0a §3.2 deferring native M5 horizons).
> Stage 22.0z-2 confirmed M1→M5 aggregation is within ±2 pp of native M5,
> so on-the-fly aggregation is methodologically sound.

> **Harness reuse note**: PR 22.0c copy-pastes the cell aggregation, fold
> split, spread stress, verdict logic, and cost-diagnostic functions from
> `scripts/stage22_0b_mean_reversion_baseline.py`. Refactor into a shared
> `phase22_research_lib.py` should be considered before 22.0e (meta-labeling)
> or 22.0f (strategy comparison) lands. **Out of scope for this PR.**

---

## 3. Strategy parameterization

### 3.1 Sweep dimensions

| Dimension | Values | Cells |
|---|---|---|
| Donchian N (M5 bars) | {10, 20, 50, 100} = 50 / 100 / 250 / 500 min look-back | 4 |
| Entry timing | `immediate`, `retest`, `momentum` | 3 |
| Horizon (M1 bars on outcome dataset) | {5, 10, 20, 40} | 4 |
| Exit rule | `tb_pnl`, `time_exit_pnl`, `best_possible_pnl` | 3 |

Total: **144 cells** (smaller than 22.0b's 192 — multiple-testing footprint deliberately tighter).

Breakout *style* is fixed to **Donchian only**. ATR-Keltner / Bollinger / volatility-breakout variants are explicitly out of scope here.

### 3.2 M1→M5 aggregation (causal)

```
mid_close[t]   = (bid_c[t] + ask_c[t]) / 2     # M1 mid
mid_high[t]    = (bid_h[t] + ask_h[t]) / 2
mid_low[t]     = (bid_l[t] + ask_l[t]) / 2

# right-closed, right-labeled 5-min resample of M1 mid:
mid_close_M5   = mid_close.resample("5min", closed="right", label="right").last()
mid_high_M5    = mid_high.resample("5min", closed="right", label="right").max()
mid_low_M5     = mid_low.resample("5min", closed="right", label="right").min()
```

Each M5 bar is labeled at its right edge (the 5-minute boundary). The M5
close at boundary `T` reflects only M1 bars whose timestamp `≤ T`.

### 3.3 Donchian channel (causal, excludes current bar)

```
hi_N[T] = mid_high_M5.shift(1).rolling(N).max()    # uses bars < T
lo_N[T] = mid_low_M5.shift(1).rolling(N).min()
```

The `shift(1)` ensures the current M5 bar is **excluded** from the channel,
so a bar cannot be measured against a channel that already contains it.

### 3.4 Breakout flags

```
long_break_M5[T]  = mid_close_M5[T] >  hi_N[T]
short_break_M5[T] = mid_close_M5[T] <  lo_N[T]
```

`break_level_long  = hi_N[T]` (channel top, used for retest/momentum reference).
`break_level_short = lo_N[T]` (channel bottom).

---

## 4. Entry-timing logic (the 3 variants)

A breakout signalled at M5 close `T` triggers a search over the next **5 M1
bars** with timestamp `> T` (strictly greater — bars at exactly `T` are
excluded; see §4.4).

### 4.1 Bid/ask convention rationale

The 22.0a outcome dataset uses **bid/ask separated entry/exit**:
- Long entry uses `ask_o[i+1]` (entry-side ask)
- Short entry uses `bid_o[i+1]` (entry-side bid)

For an entry to actually be executable, the **entry-side price** must reach
the trigger level — not just any side of the bid/ask spread. Therefore both
retest and momentum conditions are evaluated on the **entry-side price**:

| Direction | Entry-side leg | Used for retest / momentum check |
|---|---|---|
| long | ask | `ask_l` for retest (ask drops to break level), `ask_h` for momentum (ask continues up) |
| short | bid | `bid_h` for retest (bid rises to break level), `bid_l` for momentum (bid continues down) |

This is **more conservative** than using mid prices or the opposite-side
leg: an entry only counts as "executable" if the side that will actually
fill the order has reached the relevant level. A retest detected only on
mid would over-count fills.

### 4.2 `immediate`

Fire entry on the **first M1 bar with timestamp > T**.

### 4.3 `retest`

Scan the next 5 M1 bars (timestamps `> T`):
- **Long**: fire on the first bar where `ask_l[i] <= hi_N[T]` (ask returns to / below break level)
- **Short**: fire on the first bar where `bid_h[i] >= lo_N[T]` (bid returns to / above break level)

If no bar satisfies the condition within the 5-bar window, the signal is
**skipped** (no entry).

### 4.4 `momentum`

Scan the next 5 M1 bars (timestamps `> T`):
- **Long**: fire on the first bar where `ask_h[i] > hi_N[T] + 0.5 × atr_at_entry[i]` (ask continues up by ≥ ½ ATR beyond the break)
- **Short**: fire on the first bar where `bid_l[i] < lo_N[T] - 0.5 × atr_at_entry[i]` (bid continues down by ≥ ½ ATR beyond the break)

Where `atr_at_entry[i]` is the M1 ATR(14) at bar `i`, sourced from the
22.0a outcome dataset's `atr_at_entry` column (causal by construction —
see 22.0a §4.4).

If no bar satisfies the condition within the 5-bar window, the signal is
**skipped**.

### 4.5 Skipped trades

When `retest` or `momentum` does not fire within 5 M1 bars, the M5 signal
is dropped silently. Skipped signals are:
- **Not** counted in `n_trades`
- **Not** treated as PnL = 0
- Reported as a separate `skipped_rate` metric per (cell, direction)
- Reported with a `time_to_fire` histogram for fired entries (1..5 bars)

### 4.6 Outcome lookup

Once the M1 entry timestamp `entry_ts` is determined, the strategy joins
against the 22.0a outcome parquet on
`(entry_ts, pair, horizon_bars, direction)`. Filter to
`valid_label = True AND gap_affected_forward_window = False`. The chosen
`exit_rule` column gives the per-trade PnL.

---

## 5. Hard ADOPT criteria (six gates, same as 22.0b)

A cell is ADOPT-candidate iff it passes all six on a **realistic** exit_rule
(`tb_pnl` or `time_exit_pnl`):

| # | Criterion |
|---|---|
| **A0** | annual_trades ≥ 70 (overtrading warning > 1000) |
| **A1** | Sharpe ≥ +0.082 |
| **A2** | annual PnL ≥ +180 pip |
| **A3** | MaxDD ≤ 200 pip |
| **A4** | 5-fold pos/neg ≥ 4/1 |
| **A5** | spread +0.5 pip stress annual PnL > 0 |

`best_possible_pnl` cells are forced to **REJECT** regardless of metric
values (diagnostic only). Verdict 3-class: **ADOPT / PROMISING_BUT_NEEDS_OOS / REJECT**.

---

## 6. Diagnostic outputs (mandatory)

### 6.1 Carried over from 22.0b
- 144-cell sweep heatmap (Sharpe, PnL) per exit_rule
- Top-10 cells with full eval table
- Per-fold PnL + CV + concentration for top-10
- Spread stress (+0, +0.2, +0.5)
- Cost diagnostics: median spread_entry, median cost_ratio, cost_ratio bucket, spread bucket, per-pair, per-session
- `best_possible_pnl - realistic_pnl` gap

### 6.2 New for 22.0c (entry-timing comparison)
For each (N, horizon, exit_rule), report side-by-side {immediate, retest, momentum}:
- n_trades, mean_pnl, win_rate, Sharpe, MaxDD
- **`skipped_rate`** = (skipped signals) / (total breakouts)
- **`time_to_fire` histogram** (1..5 M1 bars) — only over fired entries
- If `skipped_rate > 0.95` the cell is annotated as
  `INSUFFICIENT_FIRES: too few entries to evaluate`

### 6.3 New for 22.0c (breakout sanity)
- Breakout-rate per (pair, N): how many M5 bars per pair fire a breakout signal
- **False-breakout rate (direction-specific)**:
  - Long: % of long breakouts where mid price returns **below** `hi_N[T]` within 5 M1 bars (regardless of fill / no-fill)
  - Short: % of short breakouts where mid price returns **above** `lo_N[T]` within 5 M1 bars
- Long-side and short-side reported separately (the asymmetry is a known characteristic of FX trends)

---

## 7. Files

| File | Type | Lines (target) |
|---|---|---|
| `docs/design/phase22_0c_m5_breakout_m1_entry_hybrid.md` | Design (this file) | ~250 |
| `scripts/stage22_0c_m5_breakout_m1_entry_hybrid.py` | Research script | ~700 |
| `tests/unit/test_stage22_0c_breakout.py` | Unit tests | ~350 |
| `artifacts/stage22_0c/sweep_results.parquet` | Output | regenerable, NOT committed |
| `artifacts/stage22_0c/eval_report.md` | Report | committed |
| `artifacts/stage22_0c/run.log` | Run log | committed |

---

## 8. Tests (unit)

### 8.1 Reused-pattern tests (parallel to 22.0b)
- `test_donchian_causal_no_lookahead`
- `test_breakout_signal_directions`
- `test_outcome_join_uses_correct_keys`
- `test_filter_excludes_invalid_and_gap_rows`
- `test_no_week_open_filter_applied`
- `test_walkforward_5fold_split_chronological`
- `test_spread_stress_subtracts_uniformly`
- `test_best_possible_pnl_excluded_from_adopt_judgement`
- `test_overtrading_warning_threshold`
- `test_minimum_trades_a0_blocks_adopt`

### 8.2 22.0c-specific tests
- `test_m5_aggregation_right_closed_no_lookahead` — current M5 close at boundary `T` uses only M1 bars with timestamp `≤ T`
- `test_donchian_excludes_current_bar` — `hi_N[T]` uses bars `< T` (shift(1) confirmed)
- `test_immediate_entry_ts_strictly_greater_than_signal_ts` — entry bar timestamp `> T`, never `== T`
- `test_retest_long_uses_ask_l_short_uses_bid_h` — bid/ask convention asserted on a synthetic fixture
- `test_retest_skipped_when_no_retest_within_5_bars` — `skipped_rate` increments correctly
- `test_momentum_long_uses_ask_h_short_uses_bid_l` — bid/ask convention asserted
- `test_momentum_threshold_uses_half_atr_at_entry`
- `test_momentum_skipped_when_no_continuation_within_5_bars`
- `test_skipped_signals_not_counted_as_trades` — skipped trades are not in n_trades and not PnL=0
- `test_time_to_fire_histogram_in_1_to_5_range`
- `test_false_breakout_rate_long_definition` — long false break = mid returns below break_level within 5 M1 bars
- `test_false_breakout_rate_short_definition` — short false break = mid returns above break_level within 5 M1 bars
- `test_breakout_long_signal_paired_with_long_direction_outcome` — direction sign correctness in the join

~14 tests, ~350 lines.

---

## 9. NG list compliance (postmortem §4)

| # | NG | Compliance approach |
|---|---|---|
| 1 | Pair tier filter | All 20 pairs evaluated; per-pair contribution reported but not used to prune cells |
| 2 | Train-side time-of-day filter | None |
| 3 | Test-side filter improvement claim | Verdict on all valid+non-gap rows; no time-of-day subset cherry-pick |
| 4 | WeekOpen-aware sample weighting | None |
| 5 | Universe-restricted cross-pair feature | None |

A unit test asserts no row drop based on `is_week_open_window`.

---

## 10. Out-of-scope

- src/, scripts/run_*.py, DB schema (Phase 22 invariant)
- M5 outcome dataset (deferred per 22.0a §3.2; 22.0c does not need it because entries fire on M1)
- ATR-Keltner / Bollinger / volatility-breakout signal styles
- Trailing-stop / partial-exit rules (would need path data not in the parquet)
- ML-based breakout filter (22.0e meta-labeling territory)
- Refactor of harness into `phase22_research_lib.py` (consider before 22.0e/22.0f, not now)

---

## 11. Multiple testing bias

144 cells × 20 pairs is searched. Same caveat as 22.0b — eval_report.md
verdict section opens with the in-sample-search disclaimer; production
migration of any ADOPT cell would require independent OOS validation
(held-out time slice, paper-run, or fresh data fetch).

---

## 12. Connection to 22.0b's failure-mode finding

22.0b documented `best_possible - realistic` gaps of +1M to +15M pip/year
on top MR cells. Two interpretations:
- **"signal good, exit bad"**: paths move favorably but exits cut profit
- **"signal noisy"**: high best_possible is the path's max bar, not a true edge

22.0c's three entry-timing variants test the first interpretation:
- If `retest` or `momentum` improves realised PnL meaningfully over `immediate`
  while keeping signal volume reasonable → entry timing is part of the cure.
- If all three perform identically → the signal is the issue and any future
  improvement must come from signal redesign or exit redesign.

The diagnostic in §6.2 makes this comparison directly visible in the report.

---

## 13. Conventions (matching 22.0b)

- Sharpe = mean / std (per-trade, no sqrt-of-N annualization), matching `compare_multipair_v19_causal.py:_sharpe`. Baseline +0.0822 is comparable.
- annualization uses fixed dataset span (730 d ≈ 2 years).
- 5-fold walk-forward: time-ordered chronological split of pooled trade list.
- `valid_label = True AND gap_affected_forward_window = False` filter applied uniformly.
- minimum 30 trades for inclusion in top-K ranking (separate from A0=70 ADOPT gate).

---

## 14. Verdict classification

| Verdict | Condition |
|---|---|
| **ADOPT** | A0–A5 all pass on a realistic exit_rule |
| **PROMISING_BUT_NEEDS_OOS** | A0–A3 pass but A4 (fold stability) and/or A5 (spread stress) fail |
| **REJECT** | A1 or A2 (or A0) fails |

Best cell selected by Sharpe, with annual_pnl and n_trades as tiebreakers.

---

**Status: ACTIVE.** PR2-of-Phase-22 (-c) implementation references this design directly.
