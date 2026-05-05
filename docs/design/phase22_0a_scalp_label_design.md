# Phase 22.0a Scalp Label Design (path-aware label foundation for EV evaluation)

**Date**: 2026-05-05
**Status**: ACTIVE — PR2 of Phase 22
**Parent design**: `docs/design/phase22_main_design.md`
**Context**: `docs/design/phase22_alternatives_postmortem.md`

---

## 1. Background and naming

### 1.1 Why a new label

`phase22_main_design.md` §2.1 confirmed M1 spread/ATR median = 128%. The
existing B Rule label (`label_tb` in `compare_multipair_v*.py`) is a
binary triple-barrier outcome that **discards path information** —
once a TP/SL fires, the rest of the forward path is invisible.

For a scalp redesign that respects spread cost, we need every forward
bar's worst- / best-case excursion, the time-exit fallback PnL, and the
triple-barrier resolution **side-by-side per row** so subsequent
strategy / exit / EV experiments can pivot freely.

### 1.2 Naming

This dataset is a **path-aware scalp outcome dataset** — a foundation
for EV evaluation in subsequent PRs. The word *EV* is intentionally
deferred: PR2 records *what happened* over each forward window, not
*what a strategy would have earned*. Strategy / exit rules that turn
this into EV come in PR 22.0b and beyond.

The PR title remains "Stage 22.0a Scalp Label Design" for index
continuity, but body text uses *path-aware scalp outcome dataset* or
*path-aware label foundation for EV evaluation*.

---

## 2. Schema (true-long format)

### 2.1 Row key

| Field | Type | Domain |
|---|---|---|
| `entry_ts` | timestamp[ns, UTC] | M1 bar timestamp at which the signal/decision is taken |
| `pair` | str / categorical | one of 20 pairs |
| `horizon_bars` | int8 | one of {5, 10, 20, 40} (M1 bars) |
| `direction` | str / categorical | "long" or "short" |

Per `(entry_ts, pair)`, the script emits **8 rows** (4 horizons × 2 directions).

### 2.2 Direction-specific columns (no `_long` / `_short` suffix)

| Field | Type | Definition |
|---|---|---|
| `mfe_after_cost` | float32 (pip) | max favorable excursion of the path expressed as pip PnL after entry-side spread (long: `bid_h.max() - entry_ask`; short: `entry_bid - ask_l.min()`) |
| `mae_after_cost` | float32 (pip) | max adverse excursion (long: `bid_l.min() - entry_ask`; short: `entry_bid - ask_h.max()`) |
| `best_possible_pnl` | float32 (pip) | post-hoc upper bound — same numeric as `mfe_after_cost` on this side; kept as a separate column so subsequent PRs can swap in a strategy-aware definition |
| `time_exit_pnl` | float32 (pip) | PnL if exit at horizon end with the opposite-side close (long: `exit_bid_close - entry_ask`; short: `entry_bid - exit_ask_close`) |
| `tb_outcome` | int8 | -1=SL first, 0=neither (time exit), +1=TP first; conservative resolution of same-bar ambiguity (see §5) |
| `tb_pnl` | float32 (pip) | TP-distance pip on +1, -SL-distance pip on -1, time-exit pip on 0 |
| `time_to_tp` | float32 (bars, NaN-able) | bars from entry until TP first hits, else NaN |
| `time_to_sl` | float32 (bars, NaN-able) | bars from entry until SL first hits, else NaN |
| `same_bar_tp_sl_ambiguous` | bool | True iff there exists a forward bar k where both TP and SL trigger conditions hold (raw flag; see §5) |

### 2.3 Common columns (replicated across the 2 direction rows)

| Field | Type | Definition |
|---|---|---|
| `entry_ask` | float64 (price) | ask open of bar `i+1` |
| `entry_bid` | float64 (price) | bid open of bar `i+1` |
| `exit_bid_close` | float64 (price) | bid close of bar `i+horizon` |
| `exit_ask_close` | float64 (price) | ask close of bar `i+horizon` |
| `gap_affected_forward_window` | bool | True iff any consecutive timestamp gap inside the forward window exceeds 300 s (5 min) |
| `valid_label` | bool | True iff path fits, ATR finite, entry/exit prices finite, no NaN bars in path |
| `path_shape_class` | int8 | diagnostic 5-class shape proxy (Stage 19.0f compatible). Range {0..4}, -1 if invalid. **NOT a pass/fail criterion, NOT an input to filter logic.** |
| `cost_ratio` | float32 | `spread_entry_pip / atr_entry_pip` (sanity recheck of the 128% premise) |
| `is_week_open_window` | bool | dow=6 (Sun) AND hour∈{21,22,23}. **Context flag, never used as filter.** |
| `hour_utc` | int8 | 0..23 |
| `dow` | int8 | 0..6 |
| `atr_at_entry` | float32 (pip) | M1 ATR(14) at the signal bar (causal — uses bars ≤ i) |
| `spread_entry` | float32 (pip) | `entry_ask - entry_bid` in pip |

### 2.4 Pip size convention

| Pair family | pip size |
|---|---|
| `*_JPY` | 0.01 |
| Non-JPY | 0.0001 |

All pip-denominated fields divide raw price differences by `pip_size`.

---

## 3. Multi-horizon

### 3.1 PR2 implemented horizons (M1)

| Horizon (bars) | Duration (min) | Purpose |
|---|---|---|
| 5 | 5 | scalp short |
| 10 | 10 | scalp mid |
| 20 | 20 | scalp long |
| 40 | 40 | B Rule compatibility |

### 3.2 Deferred to a subsequent PR (M5)

The same schema is intended to be reusable on M5 candles. Horizons:

| Horizon (M5 bars) | Duration (min) |
|---|---|
| 1 | 5 |
| 2 | 10 |
| 3 | 15 |

**M5 is explicitly out of PR2 implementation scope.** Reasons:
- M5 candle data load + path computation is a non-trivial second pass
- 22.0z-2 confirmed M1→M5 aggregation is reliable, so the M5 horizon
  evaluation can be built on either native M5 (already fetched for 3
  pilot pairs) or M1→M5 aggregation in a focused follow-up PR
- Schema compatibility is verified in §3.3 below so the next PR re-uses
  the same parquet layout

### 3.3 Schema compatibility check for M5

The PR2 schema is timeframe-agnostic in every column except
`horizon_bars` (which is naturally interpreted as bars-of-the-source-TF).
A subsequent M5 PR can:
- Load M5 BA candles with the same `entry_ask` / `entry_bid` / `bid_h` /
  ... convention.
- Use `horizon_bars ∈ {1, 2, 3}` and re-write to a separate parquet
  (e.g. `labels_M5_<pair>.parquet`).
- Pivot to combined M1+M5 study by union-ing the two parquet sets and
  selecting on `(timeframe, horizon_bars)`. (PR2 may add a `timeframe`
  column with default `"M1"` to make this trivial.)

---

## 4. Computation rules

### 4.1 Entry / exit (bid-ask separated)

| Direction | Entry | Exit (time) | TP trigger | SL trigger |
|---|---|---|---|---|
| long | `ask_o[i+1]` | `bid_c[i+horizon]` | `bid_h[k] >= entry_ask + tp_dist` | `bid_l[k] <= entry_ask - sl_dist` |
| short | `bid_o[i+1]` | `ask_c[i+horizon]` | `ask_l[k] <= entry_bid - tp_dist` | `ask_h[k] >= entry_bid + sl_dist` |

`tp_dist = 1.5 * atr_at_entry`, `sl_dist = 1.0 * atr_at_entry` (B Rule
compatible). `atr_at_entry` is M1 ATR(14) computed from bars `≤ i`.

### 4.2 Path metrics

For a forward window of `horizon` bars `(i+1 .. i+horizon)`:

```
mfe_after_cost_long  = (bid_h[i+1..i+horizon].max() - entry_ask) / pip
mae_after_cost_long  = (bid_l[i+1..i+horizon].min() - entry_ask) / pip
mfe_after_cost_short = (entry_bid - ask_l[i+1..i+horizon].min()) / pip
mae_after_cost_short = (entry_bid - ask_h[i+1..i+horizon].max()) / pip

best_possible_pnl_long  = mfe_after_cost_long
best_possible_pnl_short = mfe_after_cost_short

time_exit_pnl_long  = (bid_c[i+horizon] - entry_ask) / pip
time_exit_pnl_short = (entry_bid - ask_c[i+horizon]) / pip
```

### 4.3 Triple-barrier outcome

For each direction:
- Find first forward bar `k` where TP triggers; call it `k_tp` (else -1).
- Find first forward bar `k` where SL triggers; call it `k_sl` (else -1).
- Apply same-bar ambiguity rule (§5) to derive conservative outcome.
- `tb_outcome` ∈ {-1, 0, +1}; `tb_pnl` is `+tp_dist_pip`, `-sl_dist_pip`,
  or `time_exit_pnl` respectively; `time_to_tp` / `time_to_sl` are
  `k_hit + 1` (1-based) or NaN.

### 4.4 Causality guarantee

- `atr_at_entry`, `entry_ask`, `entry_bid`, `is_week_open_window`,
  `hour_utc`, `dow` are all derived from bars `≤ i+1`.
- The forward path strictly uses bars `i+1 .. i+horizon` (exclusive of
  `i`).
- No resample-then-reindex pattern is used; this avoids the lookahead
  pitfall that Phase 9.X-E fixed.

---

## 5. Same-bar TP/SL ambiguity

### 5.1 Detection

For a given forward bar `k` and direction:
- Long TP trigger: `bid_h[k] >= entry_ask + tp_dist`
- Long SL trigger: `bid_l[k] <= entry_ask - sl_dist`

If both conditions hold for the same `k`, the M1 OHLC does **not** tell
us which one fired first within the bar. We flag this:

```
same_bar_tp_sl_ambiguous = (any forward bar k has both TP and SL trigger conditions True)
```

### 5.2 Conservative resolution (PR2 default)

`tb_outcome` is computed by treating every ambiguous bar as if **only
SL fired**. Concretely:

```
effective_tp_hit = tp_trigger AND NOT sl_trigger
effective_sl_hit = sl_trigger        # ambiguous bar still counts as SL
first_tp = first index where effective_tp_hit
first_sl = first index where effective_sl_hit
outcome  = +1 if (first_tp != -1 and (first_sl == -1 or first_tp < first_sl))
           -1 if (first_sl != -1 and (first_tp == -1 or first_sl <= first_tp))
            0 otherwise
```

`tb_pnl` follows: `+tp_dist_pip` / `-sl_dist_pip` / `time_exit_pnl`.

### 5.3 Why conservative is the PR2 default

- Pessimistic bias is the safer floor — if the strategy still works with
  conservative resolution, optimistic resolution can only improve it.
- The raw flag `same_bar_tp_sl_ambiguous` is preserved in every row, so
  any subsequent PR can recompute the outcome under
  `optimistic` (treat ambiguous bar as TP) or
  `drop` (set `tb_outcome = NaN` and exclude) policies **without
  regenerating the parquet** (the path arrays are not strictly needed —
  ambiguous bar location is captured implicitly via tb_outcome / time_to_tp
  / time_to_sl plus the raw flag).

A more granular re-resolution (per-bar tp/sl arrays) would require
either re-running the script or persisting the per-bar trigger arrays;
both are deliberately out of scope for PR2.

### 5.4 Rule for subsequent PRs

When a subsequent PR introduces an alternative resolution policy, it
**must** filter or recompute strictly via the raw flag, e.g.:
- `optimistic`: rows with `same_bar_tp_sl_ambiguous=True` and
  `tb_outcome=-1` are upgraded to `tb_outcome=+1` (this is a strict
  upper bound; the actual ambiguous-bar TP-or-SL ordering may differ).
- `drop`: rows with `same_bar_tp_sl_ambiguous=True` are excluded from
  evaluation entirely.
- The PR must record the resolution policy in its evaluation header to
  preserve reproducibility.

---

## 6. Validity flags

### 6.1 `valid_label`

`valid_label = True` iff **all** of the following hold:
- `i + horizon < n` (forward path fits in the dataset)
- `atr_at_entry` is finite and > 0
- `entry_ask`, `entry_bid` are finite (and `entry_ask >= entry_bid`)
- `bid_h`, `bid_l`, `ask_h`, `ask_l`, `bid_c`, `ask_c` are finite for
  every bar in `[i+1, i+horizon]`

Otherwise `valid_label = False` and all direction-specific metrics
(`mfe_after_cost`, `mae_after_cost`, `best_possible_pnl`,
`time_exit_pnl`, `tb_pnl`, `time_to_tp`, `time_to_sl`) are NaN;
`tb_outcome` is set to a sentinel of `int8(0)` with `valid_label=False`
to signal "do not consume" (downstream code must filter on
`valid_label`).

### 6.2 `gap_affected_forward_window`

`gap_affected_forward_window = True` iff any consecutive pair of
timestamps inside the forward window `[i, i+horizon]` is separated by
more than 300 seconds (5 minutes).

This is **independent of `valid_label`**: a gap-affected window may
still be computable (`valid_label=True`); the flag is informational so
downstream code can choose to exclude such rows.

The 5-minute threshold catches typical OANDA weekend gaps (~48 h) and
larger holiday breaks; routine 1-bar drops (rare but possible) within
5 minutes are not flagged.

---

## 7. Diagnostic columns

### 7.1 `path_shape_class` (Stage 19.0f-compatible 5-class)

A diagnostic categorisation of forward mid-price path shape:

| Class | Heuristic | Description |
|---|---|---|
| 0 | `npr > 1.0` and `mid_ret > 0` | continuation up |
| 1 | `npr < -1.0` and `mid_ret < 0` | continuation down |
| 2 | `npr > 0` but `mid_ret < 0` | reversal up |
| 3 | `npr < 0` but `mid_ret > 0` | reversal down |
| 4 | otherwise | range / no clear direction |
| -1 | `valid_label=False` | undefined |

where `mid_close = (bid_c + ask_c) / 2` along the path,
`ret_end = (mid_close[-1] - mid_close[0]) / pip_size`,
`ret_std = max(std(mid_close in pip), eps)`,
`npr = ret_end / ret_std`,
`mid_ret = (mid_close[horizon // 2] - mid_close[0]) / pip_size`.

This is a **diagnostic-only column**. It is never used for
- ADOPT criteria pass/fail
- strategy selection
- filter logic

### 7.2 `cost_ratio`

`cost_ratio = spread_entry_pip / atr_at_entry_pip`. Used for:
- per-pair / per-time-of-day distribution sanity (recheck the 22.0z-1
  finding of median 128%)
- diagnostic plots in subsequent PRs

---

## 8. Hard ADOPT criteria

PR2 acceptance is judged exclusively on the quality of the dataset
**generation** (not on any strategy PnL).

| # | Hard gate |
|---|---|
| H1 | All 20 pairs × 730 days × 4 horizons × 2 directions yield rows |
| H2 | Bid/ask separated entry/exit correct (verified by unit test fixtures) |
| H3 | Look-ahead bias sanity passes (forward window strictly bars `> i`) |
| H4 | The last `horizon_bars` rows of every (pair, horizon, direction) group have `valid_label=False` |
| H5 | `gap_affected_forward_window=True` is set on rows whose forward window crosses a > 300 s gap |
| H6 | `same_bar_tp_sl_ambiguous=True` is set on rows where any forward bar has both TP and SL trigger conditions |
| H7 | The median of per-pair `cost_ratio` medians is within ±15 percentage-points of the Stage 22.0z-1 cross-pair median (≈ 128%). The original ~128% figure is an approximate cross-pair median; ±15pp is the "概ね整合 (broadly consistent)" gate. The structural finding to preserve is the per-pair *range* (USD_JPY cleanest at ~67%, AUD_NZD worst at ~237%), which PR2 reproduces almost exactly. The cross-pair midpoint can shift ~10pp from sample composition without invalidating the "spread ≈ ATR" premise. |
| H8 | Output schema is reusable in subsequent 22.0b / 22.0c PRs (long format, direction / horizon are pivot keys) |

### 8.1 Diagnostic-only metrics (NOT pass/fail)

Reported in `label_validation_report.md`, but never gate the PR:

- distributions of `mfe_after_cost`, `mae_after_cost`,
  `best_possible_pnl`, `time_exit_pnl`, `tb_pnl`
- `tb_outcome` × `time_exit_pnl` correlation
- `path_shape_class` per-pair / per-horizon distribution
- `cost_ratio` per-pair distribution including p10/p50/p90
- ambiguous bar rate by pair / horizon / direction

---

## 9. NG list inheritance

`phase22_alternatives_postmortem.md` §4 NG list applies in full:

| # | NG path | PR2 compliance |
|---|---|---|
| 1 | Pair tier filter / single-pair concentration | All 20 pairs in output |
| 2 | Train-side time-of-day filter | No filter applied; context flags are informational only |
| 3 | Test-side filter improvement claim | PR2 does not measure strategy PnL |
| 4 | WeekOpen-aware sample weighting | No weighting |
| 5 | Universe-restricted cross-pair feature engineering | No universe restriction |

A unit test asserts that `is_week_open_window=True` rows are present
in the output for every pair (i.e. the flag is recorded but never used
to drop rows).

---

## 10. Out-of-scope (PR2 will NOT touch)

- `src/fx_ai_trading/services/*` (any file)
- `src/fx_ai_trading/domain/reason_codes.py`
- `scripts/run_paper_decision_loop.py`, `scripts/run_live_loop.py`
- DB schema (`decision_log`, `close_events`, `orders`, `position_open`)
- Any production strategy or exit policy code

---

## 11. Future PRs (outline only — not committed)

- **PR2-M5**: same schema applied to M5 candles, horizons {1, 2, 3} M5 bars
- **PR 22.0b**: mean-reversion strategy 1-pager, consumes the dataset for
  EV computation under a defined exit rule
- **PR 22.0c**: M5 breakout + M1 entry hybrid, consumes the dataset
- **PR 22.0e**: meta-labeling (allowlist + shuffle-target test required)
- **PR 22.0f**: strategy comparison with multi-metric verdict + DSR

---

**Status: ACTIVE.** PR2 implementation references this design directly.
