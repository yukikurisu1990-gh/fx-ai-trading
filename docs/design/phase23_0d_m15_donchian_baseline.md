# Stage 23.0d — M15 Donchian First-Touch Breakout + M1 Execution

**Date**: 2026-05-06
**Predecessor (kickoff)**: `docs/design/phase23_design_kickoff.md`
**Predecessors (prior stages)**:
- `docs/design/phase23_0a_outcome_dataset.md`
- `docs/design/phase23_0b_m5_donchian_baseline.md`
- `docs/design/phase23_0c_m5_zscore_mr_baseline.md`
**Phase 22 analogues (read-only)**: `phase22_0b_*`, `phase22_0c_*`

This stage runs the third Phase 23 strategy evaluation: a rule-based
**Donchian breakout** signal on the **M15** signal timeframe, with M1
execution and the Phase 22 8-gate harness. Following the 23.0c lesson
(continuous-trigger overtrades; first-touch reduces but does not
eliminate overtrading at M5), 23.0d uses **first-touch trigger
semantics with same-direction re-entry lock** by default.

This stage tests the kickoff §3 hypothesis on M15: that the lighter
cost regime (cross-pair median `cost_ratio` = 0.319 from 23.0a, vs
M5's 0.573 and M1's 1.28) admits a positive-EV breakout cell. M15
horizon includes the kickoff §6.2 H1-equivalent value (`horizon=4` =
60 min), which is the longest holding period that can plausibly
capture EV after M1 execution-side cost.

---

## §1 Scope and constraints

### In scope
- 18-cell sweep over `(N, horizon_bars, exit_rule)` on the M15 signal timeframe
- 20-pair canonical universe (no pair filter), pooled per cell
- 23.0a M15 outcome dataset (`labels_M15_<pair>.parquet`) as the sole PnL source
- Phase 22 8-gate harness (A0..A5) with **exact** Phase 22 thresholds (same as 23.0b/0c)
- S0 (random-entry sanity) and S1 (strict 80/20 OOS) as **diagnostic-only**
- 3-class verdict: `ADOPT_CANDIDATE`, `PROMISING_BUT_NEEDS_OOS`, `REJECT`
- **First-touch only** Donchian breakout with same-direction re-entry lock (see §2)
- REJECT reason classification: `under_firing`, `still_overtrading`, `pnl_edge_insufficient`, `robustness_failure`

### Explicitly out of scope
- Continuous-trigger Donchian (23.0b legacy; not the Phase 23 default)
- Z-score MR on M15 (deferred to a separate stage if 23.0d shows promise)
- Any meta-labeling layer (23.0e scope)
- Per-pair adoption / exclusion (per-pair stats are diagnostic only)
- Wide barrier profile, alternative ATR period, alternative ambiguity resolution
- Phase 22's exact M1 Donchian-immediate cell (NG#6)

### Hard constraints (mirroring kickoff §10)
- `src/` not touched
- `scripts/run_*.py` not touched
- DB schema not touched
- Existing 22.x, 23.0a, 23.0b, 23.0c artifacts / docs not modified
- 20-pair canonical universe; no pair / time-of-day filter
- `signal_timeframe == "M15"` enforced at runtime by the sweep

---

## §2 Signal definition (first-touch Donchian on M15 mid OHLC)

Operate on **mid prices** at the M15 signal-TF level. The M15 OHLC is
re-aggregated from M1 BA via `aggregate_m1_to_tf` imported from
`scripts/stage23_0a_build_outcome_dataset.py`.

```
mid_h = (bid_h + ask_h) / 2          on M15
mid_l = (bid_l + ask_l) / 2          on M15
mid_c = (bid_c + ask_c) / 2          on M15

upper_N = mid_h.shift(1).rolling(N).max()
lower_N = mid_l.shift(1).rolling(N).min()
upper_N_prev = upper_N.shift(1)
lower_N_prev = lower_N.shift(1)
mid_c_prev   = mid_c.shift(1)

long_break  = (mid_c > upper_N)  AND (mid_c_prev <= upper_N_prev)
short_break = (mid_c < lower_N)  AND (mid_c_prev >= lower_N_prev)
```

The `shift(1)` enforces causality on the band itself: `upper_N` /
`lower_N` at bar `t` read M15 bars `[t-N, t-1]` only.

The first-touch condition uses **both the current and the prior bar's
relationship to their respective bands** — necessary because the band
moves bar by bar, so `(mid_c > upper_N AND mid_c_prev <= upper_N)`
(comparing the prior close against today's band) is wrong; the prior
close must be compared against the prior band.

`mid_c == upper_N` is treated as not-yet-broken (strict `>` / `<`).
The first `N+1` M15 bars produce no signal (`upper_N_prev` /
`lower_N_prev` NaN).

Long-side and short-side locks are independent. After a long signal
fires, no further long signal fires until the price returns inside
the upper band (`mid_c <= upper_N` for some bar) — at which point
the next upward crossing can fire a new long signal.

### 2.1 Why first-touch (Phase 23 commitment)

> **Continuous trigger is not the Phase 23 default because 23.0b showed
> continuous-trigger overtrading. A continuous variant may be
> reintroduced only as a diagnostic follow-up, not as the main
> baseline.**

Repeating the 23.0c articulation: 23.0b naive continuous Donchian
REJECTed with overtrading; 23.0c first-touch z-score MR REJECTed with
`still_overtrading`. 23.0d applies first-touch to Donchian on M15 to
test whether the **lighter M15 cost regime + first-touch precision
together** find a positive-EV cell.

---

## §3 Cell sweep grid

| dim | values | count |
|---|---|---|
| `N` (Donchian window, M15 bars) | `{10, 20, 50}` = 2.5h / 5h / 12.5h | 3 |
| `horizon_bars` | `{1, 2, 4}` = 15 / 30 / 60 min (kickoff §6.2) | 3 |
| `exit_rule` | `{tb, time}` | 2 |

**Total: 18 cells.** Each evaluated on the 20-pair pool.

`N` rationale: the M15 values are numerically the same as 23.0b's M5
sweep (`{10, 20, 50}`) but the time-spans are 3× larger (M15 bars are
15 min vs M5's 5 min). This gives a structural daily-cycle look-back
range (2.5h to 12.5h, roughly half a session to 1.5 sessions).

`horizon_bars = {1, 2, 4}` matches the 23.0a M15 parquet output
exactly per kickoff §6.2. The 60-min H1-equivalent horizon (`h=4`) is
the most informative for the Phase 23 hypothesis.

NG#6 Phase 22 cell (M1, h=40, conf=0.55) is excluded by construction:
signal_timeframe (M15 vs M1), horizon units (M15 vs M1), no `conf`
parameter. Runtime assertion verifies `signal_timeframe == "M15"` for
every emitted trade row.

---

## §4 8-gate harness (Phase 22 inherited, identical to 23.0b/0c)

Per cell, pool all 20 pairs' joined trades on `(entry_ts, pair,
signal_timeframe='M15', horizon_bars, direction)` against the 23.0a
`labels_M15_<pair>.parquet` (restricted to `valid_label = True`):

| gate | metric | threshold |
|---|---|---|
| **A0** | `annual_trades = n_trades / span_years` | `>= 70` |
| **A1** | per-trade Sharpe (ddof=0, no √N) | `>= +0.082` |
| **A2** | `annual_pnl_pip = sum(pnl) / span_years` | `>= +180` |
| **A3** | `max_dd_pip` on cumulative pip curve | `<= 200` |
| **A4** | 5-fold split, drop k=0, eval k=1..4, count Sharpe-positive | `>= 3 / 4` |
| **A5** | annual_pnl after subtracting 0.5 pip per round trip | `> 0` |

`span_years = 730 / 365.25 ≈ 1.9986`.

Overtrading warning: `annual_trades > 1000` emits a warning string
(NOT blocking).

**Diagnostic-only metrics** (NEVER gate-blocking):
- hit_rate, payoff_asymmetry
- per-pair contribution, per-session contribution
- `band_distance_at_entry`: how far above/below the band the breakout was at the signal bar (in pips)
- `breakout_holding_diagnostic` (best-cell only, forward-path M1 bars: median time the price stays beyond the band before retreating). Forward-path diagnostic-only — must NOT be used in features or ADOPT.

---

## §5 S0 / S1 diagnostics (NOT hard ADOPT gates — same as 23.0b/0c)

### S0 — random-entry sanity
Same-count random sample from valid M15 signal bars in the cell's
`(signal_TF, horizon)` slice, matching long/short balance, seed=42.
Compute Sharpe; expect ≈ 0 if the cell's edge is genuine.

### S1 — strict 80/20 chronological hold-out
Best cell only (max A1 Sharpe among A0-passers). Sort pooled trades
by `entry_ts`, IS = first 80%, OOS = last 20%. No re-search.
`s1_oos_is_ratio = oos_sharpe / is_sharpe`.

S1 modulates between `ADOPT_CANDIDATE` and `PROMISING_BUT_NEEDS_OOS`.
Does NOT REJECT.

---

## §6 Verdict (3-class) + REJECT reason classification

Headline verdict on the best cell (max A1 Sharpe among A0-passers):

| verdict | criteria |
|---|---|
| **ADOPT_CANDIDATE** | A0..A5 all pass AND S1 strict OOS strong (`oos > 0` and `oos/is >= 0.5`). Independent OOS validation (`23.0d-v2`) mandatory before production. |
| **PROMISING_BUT_NEEDS_OOS** | A0..A3 pass but A4 OR A5 fails; OR A0..A5 pass but S1 weak |
| **REJECT** | A1 OR A2 fails; OR A0 fails. With `reject_reason` ∈ {under_firing, still_overtrading, pnl_edge_insufficient, robustness_failure} |

`reject_reason` classification (per cell, after gates):

```
if not A0_pass:
    reason = "under_firing"
elif overtrading_warning AND (not A1_pass OR not A2_pass):
    reason = "still_overtrading"
elif (not A1_pass OR not A2_pass):
    reason = "pnl_edge_insufficient"
elif (not A3_pass OR not A4_pass OR not A5_pass):
    reason = "robustness_failure"
else:
    reason = None
```

**Production-readiness clause (mandatory in eval_report.md)**:

> Even an ADOPT_CANDIDATE verdict is *not* production-ready. The S1
> strict OOS is computed *after* the in-sample sweep selected the best
> cell from 18 cells × 20 pairs (multiple-testing surface). A separate
> `23.0d-v2` PR with frozen-cell strict OOS validation on
> chronologically out-of-sample data and no parameter re-search is
> required before any production migration.

---

## §7 Interpretation note carried from 23.0c (mandatory in eval_report.md)

**The 23.0c REJECT is not a complete dismissal of M5 z-score MR.** All
36 cells were classified `still_overtrading`, meaning trade volume
was reduced 2-5× by first-touch but remained above the 1000-trade
warning threshold; per-trade EV was dominated by spread cost. This is
consistent with **insufficient signal firing precision**, not with
"M5 z-score MR has no edge".

23.0d's design therefore considers first-touch a *partial* fix and
documents follow-up signal-quality controls below.

### 7.1 23.0c-rev1 candidate signal-quality controls

If 23.0d also REJECTs, the next stage is **NOT** to skip directly to
23.0e meta-labeling. The intermediate stage `23.0c-rev1` should test
fixed (non-search) overtrading-suppression rules layered on top of
the 23.0c first-touch z-score MR signal:

| candidate | rule |
|---|---|
| **neutral reset** | Same `(pair, direction)` re-entry permitted only after `z` returns to the neutral band `[-0.5, +0.5]` (not just back inside `[-threshold, +threshold]`). |
| **cooldown** | Same `(pair, direction)` re-entry blocked for the next `3` M5 bars after a fire (deterministic time-out independent of `z`). |
| **reversal confirmation** | Long fires only when `z` is rising (`z[t] > z[t-1]`) AND `mid_c[t] > mid_c[t-1]`; short mirrored. (Captures the moment the move starts to reverse.) |
| **fixed cost gate** | Drop signals where `cost_ratio_at_entry > 0.6` (filter by 23.0a's `cost_ratio` column). |

**These are fixed rules, NOT a parameter sweep.** Each is added as a
single deterministic filter on top of 23.0c's first-touch trigger;
the 23.0c-rev1 stage runs each filter independently and reports
whether any single filter brings annual_trades into a tractable
range and clears the A0-A5 gates.

### 7.2 Phase 23 routing (post-23.0d)

The Phase 23 stage routing depends on the 23.0d outcome:

```
23.0d returns:
├── ADOPT_CANDIDATE / PROMISING_BUT_NEEDS_OOS
│     → 23.0e (meta-labeling on best 23.0b/c/d cell) triggers
│     → 23.0d-v2 (frozen-cell strict OOS) mandatory before production
│
└── REJECT (any reason)
      ├── If any 23.0b/c/d cell has positive realistic-exit Sharpe
      │     → 23.0e meta-labeling on that cell triggers
      │     → 23.0d does NOT itself proceed to 23.0d-v2
      │
      └── If NO 23.0b/c/d cell has positive realistic-exit Sharpe
            → 23.0e DOES NOT trigger
            → 23.0c-rev1 (signal-quality control study, §7.1) is the next candidate
            → If 23.0c-rev1 also REJECTs across all four candidate filters,
              Phase 23 closes with the negative-but-bounded conclusion
```

**The Phase 23 conclusion must distinguish two failure modes**:

1. *"Cost regime alone (M5/M15 vs M1) was insufficient for naive /
   weakly-controlled signal firing"* — supported by current 23.0b/0c
   evidence and (if it REJECTs) 23.0d evidence.
2. *"M5/M15 has no recoverable edge even with stronger signal-quality
   controls"* — would require 23.0c-rev1 also failing to find a
   positive-EV cell with the §7.1 candidate filters.

These are different conclusions with different next-phase
implications. Phase 23 closure must NOT short-circuit (1) into (2).

---

## §8 Walk-forward methodology (A4 — same as 23.0b/0c)

For a cell's pooled trade list (across 20 pairs, sorted by
`entry_ts`):

- Split into 5 chronological quintiles of equal *trade count*.
- `k = 0` → warmup, dropped.
- `k = 1..4` → evaluation folds.
- Compute per-trade Sharpe per fold (ddof=0). Folds with fewer than
  2 trades return NaN and count as not-positive.
- A4 passes if `count(fold_sharpe > 0 for k in 1..4) >= 3`.

---

## §9 Outputs and commit policy

### Committed
- `docs/design/phase23_0d_m15_donchian_baseline.md` (this file)
- `scripts/stage23_0d_m15_donchian_eval.py`
- `tests/unit/test_stage23_0d_m15_donchian.py`
- `artifacts/stage23_0d/eval_report.md` (generated)
- `artifacts/stage23_0d/run.log`

### NOT committed (regenerable)
- `artifacts/stage23_0d/sweep_results.parquet` — raw per-cell metrics (excluded via `.gitignore`)
- `artifacts/stage23_0d/sweep_results.json` — sidecar JSON

---

## §10 Mandatory unit tests (≥ 14 cases)

| # | name | what it verifies |
|---|---|---|
| 1 | `test_donchian_upper_lower_causal_shift1` | upper_N / lower_N at bar `t` use bars `[t-N, t-1]`; bar `t` excluded |
| 2 | `test_donchian_uses_mid_high_low_not_bid_or_ask` | mid_h = (bid_h+ask_h)/2; signal-side never reads bid_h/ask_h directly |
| 3 | `test_long_first_touch_strict_above_upper` | `mid_c > upper_N AND mid_c_prev <= upper_N_prev` triggers; equality not |
| 4 | `test_short_first_touch_strict_below_lower` | mirrored |
| 5 | `test_first_touch_does_not_re_trigger_above_band` | sustained price above band → ≤ 1 long signal in zone |
| 6 | `test_first_touch_resets_after_returning_inside_band` | break-and-return-and-break-again → 2 long signals |
| 7 | `test_long_short_locks_independent` | swing across both bands → both fire |
| 8 | `test_no_signal_when_donchian_window_not_filled` | bars 0..N have NaN bands → no signals |
| 9 | `test_signal_join_to_23_0a_M15_outcome` | join (entry_ts, pair, 'M15', horizon_bars, direction) → finite tb_pnl/time_exit_pnl |
| 10 | `test_horizon_4_M15_yields_60_min_outcome` | `h=4` looks up the 60-min outcome row |
| 11 | `test_sharpe_per_trade_ddof0_no_annualize` | mean / std (ddof=0); no √N |
| 12 | `test_a4_4fold_majority_rule` | synthetic fold pattern → correct n_positive |
| 13 | `test_a5_spread_stress_subtracts_half_pip_per_trade` | pnl − 0.5 per trade |
| 14 | `test_no_phase22_m1_cell_reused` | runtime assertion: every emitted trade has `signal_timeframe == "M15"` |
| 15 | `test_cell_pooling_aggregates_all_pairs` | trade set covers all 20 pairs |
| 16 | `test_smoke_mode_3pairs_2cells` | --smoke = USD_JPY/EUR_USD/GBP_JPY × 2 cells |
| 17 | `test_verdict_3class_assignment` | synthetic gate matrix → correct verdict |
| 18 | `test_reject_reason_classification` | synthetic combos → correct reason |
| 19 | `test_trigger_mode_constant_documented` | `TRIGGER_MODE == "first_touch"` set in script |
| 20 | `test_signal_timeframe_constant_M15` | `SIGNAL_TIMEFRAME == "M15"` set in script |

---

## §11 NG list compliance

| NG | how 23.0d complies |
|---|---|
| 1 | 20-pair canonical, no filter |
| 2 | No train-side time filter |
| 3 | No test-side filter; 80/20 OOS chronological, no re-search |
| 4 | No WeekOpen-aware weighting |
| 5 | No universe-restricted cross-pair feature |
| 6 | M15 signal_TF (NOT M1); horizon units M15; outcome dataset 23.0a M15 (NOT 22.0a M1); no `conf` parameter |
| 7 | n/a |
| 8 | 23.0a M15 outcome dataset is sole PnL source |

---

## §12 Effort estimate

| item | hours |
|---|---|
| Donchian first-touch signal generator (M15, with shift(1)-shift(1) condition) | 2-3 |
| 23.0a M15 join + 8-gate harness (mostly reusable from 23.0b/c) | 1-2 |
| Sweep runner + S0/S1 + reject_reason | 1-2 |
| Tests (target 18-20) | 2-3 |
| Eval report drafting (with §7 routing note) | 1-2 |
| **Total** | **7-12** |

---

## §13 Document role boundary

This file is the stage contract for 23.0d. Per-cell results go to
`artifacts/stage23_0d/eval_report.md`; data construction belongs to
23.0a. The §7 interpretation note is normative for downstream Phase
23 routing — closure docs (eventual `phase23_final_synthesis.md`)
must respect the (1) vs (2) failure-mode distinction.

If a contradiction arises between this doc and the kickoff doc, the
kickoff wins.
