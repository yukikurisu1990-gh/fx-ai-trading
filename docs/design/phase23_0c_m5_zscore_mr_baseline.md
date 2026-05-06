# Stage 23.0c — M5 z-score MR + M1 Execution Alternative Baseline

**Date**: 2026-05-06
**Predecessor (kickoff)**: `docs/design/phase23_design_kickoff.md`
**Predecessors (prior stages)**:
- `docs/design/phase23_0a_outcome_dataset.md`
- `docs/design/phase23_0b_m5_donchian_baseline.md`
**Phase 22 analogue (read-only)**: `docs/design/phase22_0b_mean_reversion_baseline.md`

This stage runs the second Phase 23 strategy evaluation: a rule-based
**z-score mean-reversion** signal on M5, with M1 execution and the
Phase 22 8-gate harness. It complements 23.0b's breakout cell space
with the alternative regime hypothesis (mean reversion). No model, no
meta-labeling — every signal is deterministic from M5 mid OHLC.

---

## §1 Scope and constraints

### In scope
- 36-cell sweep over `(N, threshold, horizon_bars, exit_rule)` on the M5 signal timeframe
- 20-pair canonical universe (no pair filter), pooled per cell
- 23.0a M5 outcome dataset (`labels_M5_<pair>.parquet`) as the sole PnL source
- Phase 22 8-gate harness (A0..A5) with **exact** Phase 22 thresholds (same as 23.0b)
- S0 (random-entry sanity) and S1 (strict 80/20 OOS) as **diagnostic-only**
- 3-class verdict: `ADOPT_CANDIDATE`, `PROMISING_BUT_NEEDS_OOS`, `REJECT`
- **First-touch only** signal trigger semantics with same-direction re-entry lock (see §2)
- MR-specific diagnostics: `z_at_entry` distribution, `time_to_revert_to_mean`
- Explicit REJECT-reason classification: `under_firing`, `still_overtrading`, `pnl_edge_insufficient`

### Explicitly out of scope
- Continuous-trigger MR (variant only as future diagnostic, see §2)
- Any meta-labeling layer (23.0e scope)
- Per-pair adoption / exclusion (per-pair stats are diagnostic only)
- Wide barrier profile, alternative ATR period, alternative ambiguity resolution
- Phase 22's exact M1 z-score MR cells from 22.0b (NG#6)

### Hard constraints (mirroring kickoff §10)
- `src/` not touched
- `scripts/run_*.py` not touched
- DB schema not touched
- Existing 22.x, 23.0a, 23.0b artifacts / docs not modified
- 20-pair canonical universe; no pair / time-of-day filter
- `signal_timeframe == "M5"` enforced at runtime by the sweep

---

## §2 Signal definition (causal z-score MR on M5 mid)

Operate on **mid close prices** at the M5 signal-TF level. The M5 OHLC
is re-aggregated from M1 BA via `aggregate_m1_to_tf` imported from
`scripts/stage23_0a_build_outcome_dataset.py`.

```
mid_c = (bid_c + ask_c) / 2          on M5

mu_N    = mid_c.shift(1).rolling(N).mean()
sigma_N = mid_c.shift(1).rolling(N).std(ddof=0)
z[t]    = (mid_c[t] - mu_N[t]) / sigma_N[t]
```

The `shift(1)` enforces causality: at signal bar `t`, `mu_N` and `sigma_N`
read M5 bars `[t-N, t-1]` only — never bar `t` itself.

Sigma=0 protection: rows with `sigma_N <= 0` produce no signal (z is
undefined / infinite); the script masks these out before evaluating the
trigger condition.

### 2.1 Trigger semantics — first-touch with re-entry lock

```
long_signal[t]  = (z[t] < -threshold) AND (z[t-1] >= -threshold)
short_signal[t] = (z[t] > +threshold) AND (z[t-1] <= +threshold)
```

This is a **rising-edge** condition into the extreme zone:
- A long signal fires only on the bar at which `z` first crosses below `-threshold` from inside the band.
- While `z` stays below `-threshold` (`z[t-1]` already below), no further long signal fires — same-direction re-entry is locked.
- The lock releases when `z` returns inside the band (`z[t-1] >= -threshold`); the next downward crossing can fire a new long signal.

The long-side and short-side locks are **independent**. A direct
`z < -threshold → z > +threshold` swing without crossing zero would fire
a short signal (since `z[t-1] <= +threshold` is satisfied while `z` was
in the negative-extreme zone), even though no return-to-mean happened
in between.

`z[t-1]` is undefined for the first bar after the rolling window fills.
Such bars produce no signal regardless of `z[t]`.

### 2.2 Why first-touch (not continuous)

> **Continuous trigger is not the Phase 23 default because 23.0b showed
> continuous-trigger overtrading. A continuous variant may be reintroduced
> only as a diagnostic follow-up, not as the main baseline.**

The 23.0b Donchian breakout REJECT was caused by `mid_c > upper_N` firing
every bar the price stayed above the band — producing 100k–500k annual
trades pooled, dominated by spread cost. A naive continuous MR
(`z < -threshold` every bar) would replicate this pathology, even though
MR's lower duty-cycle (~5% of bars at threshold=2.0 vs ~30% for
breakout-continuous) softens it. Phase 23 is therefore committed to
first-touch by design at the rule-based stage; continuous-trigger
variants are deferred to follow-up diagnostics or to 23.0e meta-labeling
filters.

---

## §3 Cell sweep grid

| dim | values | count |
|---|---|---|
| `N` (rolling window, M5 bars) | `{12, 24, 48}` = 1h / 2h / 4h | 3 |
| `threshold` (absolute z) | `{2.0, 2.5}` | 2 |
| `horizon_bars` | `{1, 2, 3}` | 3 |
| `exit_rule` | `{tb, time}` | 2 |

**Total: 36 cells.** Each evaluated on the 20-pair pool.

`threshold = 1.5` is excluded (likely overtrading even with first-touch);
`threshold = 3.0` is excluded (likely under-firing — too few trades to
clear A0). These boundaries can be revisited in a follow-up if the 36
cells leave both REJECT-reasons exhausted.

The Phase 22 22.0b cells (M1, threshold ∈ {1.5, 2.0, 2.5, 3.0}, N ∈
{12, 24, 48, 96} M1 bars, h ∈ {3, 5, 8, 13, 21, 40} M1 bars, conf
parameter) are excluded by construction: signal_timeframe (M5 here vs
M1 there), horizon units (M5 here vs M1 there), no `conf` parameter.
A runtime assertion verifies `signal_timeframe == "M5"` for every
emitted trade row.

---

## §4 8-gate harness — Phase 22 thresholds, mirrored exactly (same as 23.0b)

Per cell, pool all 20 pairs' joined trades (inner join on `(entry_ts,
pair, signal_timeframe='M5', horizon_bars, direction)` to the 23.0a
parquet, restricted to `valid_label = True`). Then compute:

| gate | metric | threshold |
|---|---|---|
| **A0** | `annual_trades = n_trades / span_years` | `>= 70` |
| **A1** | per-trade Sharpe `mean / std` (ddof=0, no √N annualisation) | `>= +0.082` |
| **A2** | `annual_pnl_pip = sum(pnl) / span_years` | `>= +180` |
| **A3** | `max_dd_pip` on cumulative pip curve (positive value) | `<= 200` |
| **A4** | 5-fold chronological split, drop k=0 (warmup), eval k=1..4; count Sharpe-positive folds | `>= 3 / 4` |
| **A5** | `annual_pnl_pip` after subtracting 0.5 pip from each trade (+0.5 pip spread stress per round trip) | `> 0` |

`span_years = 730 / 365.25 ≈ 1.9986`.

**Overtrading warning** (Phase 22 22.0b convention): if
`annual_trades > 1000`, emit a warning string in the report; this is
**NOT blocking** for A0.

**Diagnostic-only metrics** (computed and reported, never gate-blocking):
- hit rate, payoff asymmetry
- per-pair contribution, per-session contribution
- `z_at_entry` distribution: p10 / p25 / p50 / p75 / p90 of `|z|` at signal bars
- `time_to_revert_to_mean`: the M1-bar count from entry until the **mid path price** first returns to within ±0.5 σ_N of `mu_N` (capped at the path length). Diagnostic-only — must NOT be used in features or in any ADOPT decision.

---

## §5 S0 / S1 diagnostics (NOT hard ADOPT gates)

### S0 — random-entry sanity

For each cell, generate a comparison "trade set" of the same size as the
MR-triggered set, sampled uniformly at random from valid M5 signal bars
in the same `(signal_TF, horizon)` slice with the same long/short
balance, using `seed=42`. Compute Sharpe.

Interpretation: if the random-entry Sharpe is indistinguishable from
the cell's Sharpe, the cell's edge is sample-size luck rather than MR
structure. Reported as `s0_random_entry_sharpe`.

### S1 — strict 80/20 chronological hold-out

After the sweep, on the **best cell** (max A1 Sharpe among cells passing
A0): sort pooled trades by `entry_ts`, IS = first 80%, OOS = last 20%,
compute Sharpe on each. `s1_oos_is_ratio = oos_sharpe / is_sharpe`
(NaN if `is_sharpe <= 0`). **No re-search of cell parameters.**

S1 modulates between `ADOPT_CANDIDATE` and `PROMISING_BUT_NEEDS_OOS`
(see §6). It does NOT REJECT.

---

## §6 Verdict (3-class) — same convention as 23.0b

Headline verdict is per the best cell (max A1 Sharpe among cells
passing A0). The other 35 cells are listed in the report but do not
change the headline.

| verdict | criteria |
|---|---|
| **ADOPT_CANDIDATE** | A0..A5 all pass AND S1 strict OOS is "strong" (`oos_sharpe > 0` and `oos/is_sharpe >= 0.5`). Independent OOS validation (`23.0c-v2`, analogous to 22.0e-v2) is **mandatory** before any production claim. |
| **PROMISING_BUT_NEEDS_OOS** | A0..A3 pass but A4 OR A5 fails; OR A0..A5 all pass but S1 strict OOS is weak (`oos_sharpe <= 0` or `oos/is_sharpe < 0.5`). 23.0e/e-v2 (meta-labeling + independent OOS) is the path forward. |
| **REJECT** | A1 OR A2 fails; OR A0 fails. The script also emits a `reject_reason` classification (see §7). |

**Production-readiness clause (mandatory in eval_report.md)**:

> Even an ADOPT_CANDIDATE verdict is *not* production-ready. The S1 strict
> OOS is computed *after* the in-sample sweep selected the best cell from
> 36 cells × 20 pairs (multiple-testing surface). A separate `23.0c-v2`
> PR with frozen-cell strict OOS validation on chronologically
> out-of-sample data and no parameter re-search is required before any
> production migration.

---

## §7 REJECT reason classification

When a cell's verdict is `REJECT`, the eval report attaches a
`reject_reason` derived as follows (per cell, after the gates are
computed):

```
if not A0_pass:
    reason = "under_firing"            # annual_trades < 70
elif overtrading_warning AND (not A1_pass OR not A2_pass):
    reason = "still_overtrading"        # too many trades, spread eats EV
elif (not A1_pass OR not A2_pass):
    reason = "pnl_edge_insufficient"    # right trade volume, no edge
elif (not A3_pass OR not A4_pass OR not A5_pass):
    reason = "robustness_failure"       # PnL OK but A3/A4/A5 fail
else:
    reason = None                       # not a REJECT
```

The headline verdict report includes per-cell counts:

```
under_firing:           N cells
still_overtrading:      N cells
pnl_edge_insufficient:  N cells
robustness_failure:     N cells
adopt_candidate:        N cells
promising:              N cells
```

Plus a "Did first-touch fix overtrading?" subsection that reports:
- annual_trades histogram across the 36 cells
- comparison: 23.0b's 105k–250k annual_trades vs 23.0c's distribution
- count of cells triggering the overtrading warning (`annual_trades > 1000`)
- conclusion: did first-touch reduce trade count to a tractable range, and
  if not, is the residual REJECT reason `pnl_edge_insufficient` or
  `still_overtrading`?

---

## §8 Walk-forward methodology (A4 — same as 23.0b)

For a cell's pooled trade list (across 20 pairs, sorted by `entry_ts`):
- Split into 5 chronological quintiles of equal *trade count*.
- `k = 0` → warmup, dropped.
- `k = 1..4` → evaluation folds.
- Compute per-trade Sharpe per fold (ddof=0). Folds with fewer than 2
  trades return NaN and count as not-positive.
- A4 passes if `count(fold_sharpe > 0 for k in 1..4) >= 3`.

---

## §9 Outputs and commit policy

### Committed
- `docs/design/phase23_0c_m5_zscore_mr_baseline.md` (this file)
- `scripts/stage23_0c_m5_zscore_mr_eval.py`
- `tests/unit/test_stage23_0c_m5_zscore_mr.py`
- `artifacts/stage23_0c/eval_report.md` (generated)
- `artifacts/stage23_0c/run.log`

### NOT committed (regenerable)
- `artifacts/stage23_0c/sweep_results.parquet` — raw per-cell metrics
  (excluded via `.gitignore`; same content embedded in `eval_report.md`)
- `artifacts/stage23_0c/sweep_results.json` — sidecar JSON

---

## §10 Mandatory unit tests (≥ 14 cases)

| # | name | what it verifies |
|---|---|---|
| 1 | `test_zscore_mu_sigma_use_causal_shift1` | μ/σ at bar `t` use M5 bars `[t-N, t-1]`; bar `t` excluded |
| 2 | `test_zscore_uses_mid_close_not_bid_or_ask` | `mid_c = (bid_c+ask_c)/2`; signal-side does not read bid_c/ask_c directly |
| 3 | `test_long_signal_when_z_below_neg_threshold_first_touch` | z[t] < -threshold AND z[t-1] >= -threshold → long fires |
| 4 | `test_short_signal_when_z_above_pos_threshold_first_touch` | mirrored for short |
| 5 | `test_first_touch_does_not_re_trigger_in_extreme_zone` | z stays < -threshold for K bars → exactly 1 long signal at the rising-edge bar |
| 6 | `test_first_touch_resets_after_returning_inside` | z below -threshold, returns inside, then below again → 2 long signals |
| 7 | `test_long_short_locks_independent` | z swings −extreme → +extreme without crossing zero → both signals fire (one each) |
| 8 | `test_no_signal_when_rolling_window_not_filled` | bars 0..N have NaN μ/σ → no triggers |
| 9 | `test_no_signal_when_sigma_zero` | constant series → σ=0 → no signals (div-by-0 guard) |
| 10 | `test_signal_join_to_23_0a_outcome` | join (entry_ts, pair, 'M5', horizon_bars, direction) → finite tb_pnl/time_exit_pnl |
| 11 | `test_signal_drops_invalid_rows` | 23.0a `valid_label=False` excluded |
| 12 | `test_sharpe_per_trade_ddof0_no_annualize` | mean / std (ddof=0); no √N |
| 13 | `test_a4_4fold_majority_rule` | synthetic fold pattern → correct n_positive |
| 14 | `test_a5_spread_stress_subtracts_half_pip_per_trade` | pnl − 0.5 per trade |
| 15 | `test_no_phase22_m1_cell_reused` | runtime assertion: every emitted trade has `signal_timeframe == "M5"` |
| 16 | `test_cell_pooling_aggregates_all_pairs` | trade set covers all 20 pairs |
| 17 | `test_smoke_mode_3pairs_2cells` | --smoke = USD_JPY/EUR_USD/GBP_JPY × 2 cells |
| 18 | `test_verdict_3class_assignment` | synthetic gate matrix → correct verdict |
| 19 | `test_reject_reason_classification` | synthetic gate combinations → correct under_firing / still_overtrading / pnl_edge_insufficient / robustness_failure |
| 20 | `test_trigger_mode_constant_documented` | `TRIGGER_MODE == "first_touch"` is set in the script |

---

## §11 NG list compliance

| NG | how 23.0c complies |
|---|---|
| 1 | 20-pair canonical universe; no pair filter |
| 2 | No train-side time filter; all M5 bars eligible |
| 3 | No test-side filter; 80/20 OOS chronological, no re-search |
| 4 | No WeekOpen-aware sample weighting |
| 5 | No universe-restricted cross-pair feature |
| 6 | M5 signal_timeframe enforced at runtime; horizon units differ from Phase 22 M1; outcome dataset is 23.0a M5 (NOT 22.0a M1); no `conf` parameter |
| 7 | n/a |
| 8 | 23.0a M5 outcome dataset is the sole PnL source |

---

## §12 Effort estimate

| item | hours |
|---|---|
| z-score signal generator + first-touch + re-entry lock | 2-3 |
| 23.0a join + 8-gate harness (mostly reusable from 23.0b) | 1-2 |
| Sweep runner + S0 random-entry + S1 strict OOS | 1-2 |
| MR-specific diagnostic (z_at_entry, time_to_revert_to_mean) | 2 |
| REJECT-reason classification + first-touch effectiveness summary | 1 |
| Tests (≥ 14 cases, target 18-20) | 2-3 |
| Eval report drafting | 1-2 |
| **Total** | **10-15** |

---

## §13 Document role boundary

This file is the stage contract for 23.0c. It does not record per-cell
results (those go into `artifacts/stage23_0c/eval_report.md`) and does
not describe the data construction (that is 23.0a's domain).

If a contradiction arises between this doc and the kickoff doc, the
kickoff wins.
