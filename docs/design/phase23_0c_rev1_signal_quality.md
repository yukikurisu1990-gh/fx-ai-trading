# Stage 23.0c-rev1 — Signal-Quality Control Study

**Date**: 2026-05-06
**Predecessor (kickoff)**: `docs/design/phase23_design_kickoff.md`
**Predecessors (prior stages)**:
- `docs/design/phase23_0a_outcome_dataset.md`
- `docs/design/phase23_0b_m5_donchian_baseline.md`
- `docs/design/phase23_0c_m5_zscore_mr_baseline.md`
- `docs/design/phase23_0d_m15_donchian_baseline.md`

This stage is a **diagnostic sweep** — NOT a strategy adoption study —
that tests whether four fixed (non-search) signal-quality control rules,
layered on the 23.0c first-touch z-score MR baseline, can suppress
overtrading enough to admit an A0..A5-clearing cell.

It is the bridge between the Phase 23 outcomes (1) "cost regime alone
insufficient for naive / weakly-controlled signal firing" and (2)
"M5/M15 has no recoverable edge even with stronger signal-quality
controls" articulated in `phase23_0d_m15_donchian_baseline.md` §7.2.
The 23.0c-rev1 sweep adjudicates between (1) and (2): a single
ADOPT_CANDIDATE / PROMISING cell on any of the four filters supports
(1) and routes forward to 23.0c-rev2 / 23.0e; all-REJECT supports (2)
and closes Phase 23 with the negative-but-bounded conclusion.

---

## §1 Scope and constraints

### In scope
- Four fixed-rule filters layered on 23.0c first-touch z-score MR
  (definitions in §3); each filter evaluated independently
- 144-cell sweep: 4 filters × 3 N × 2 threshold × 3 horizon × 2 exit_rule
- 20-pair canonical universe (no pair filter), pooled per cell
- 23.0a M5 outcome dataset (`labels_M5_<pair>.parquet`) as the sole PnL source
- Phase 22 8-gate harness (A0..A5) with **exact** Phase 22 thresholds (same as 23.0b/c/d)
- S0 (random-entry sanity) and S1 (strict 80/20 OOS) as **diagnostic-only**
- 3-class verdict per filter + overall verdict picking the best filter
- REJECT reason classification (under_firing / still_overtrading /
  pnl_edge_insufficient / robustness_failure)

### Explicitly out of scope
- **No parameter search over the filter constants.** `NEUTRAL_BAND = 0.5`,
  `COOLDOWN_BARS = 3`, `COST_GATE_THRESHOLD = 0.6` are all fixed values
  selected before running.
- Combining filters (no F1+F2 stack, no F1+F4 stack). Each filter alone.
- Z-MR variants, Donchian variants, M15 cells, meta-labeling — out of scope.
- Production claim / migration. **Even a PROMISING result here is
  hypothesis-generating only**; 23.0c-rev2 frozen-cell strict OOS is
  mandatory before any production discussion.

### Hard constraints (mirroring kickoff §10)
- `src/` not touched
- `scripts/run_*.py` not touched
- DB schema not touched
- Existing 22.x, 23.0a, 23.0b, 23.0c, 23.0d artifacts/docs not modified
- 20-pair canonical universe; no pair / time-of-day filter
- `signal_timeframe == "M5"` enforced at runtime by the sweep
- Filter constants fixed (no sweeping over them)

---

## §2 Multiple-testing caveat (mandatory in eval_report.md)

This stage runs a 144-cell sweep across four filters. The 23.0c base
sweep (36 cells) was already a multiple-testing surface; layering 4
filters on top of it multiplies the effective hypothesis count to
> 100. **Any single ADOPT_CANDIDATE / PROMISING cell here is
hypothesis-generating only** and does not constitute production-ready
evidence. The path to production requires:

1. 23.0c-rev1 produces an ADOPT_CANDIDATE / PROMISING cell on at least one filter
2. **23.0c-rev2** runs that single frozen-cell on a chronologically
   strict-OOS hold-out with **no parameter re-search** (analogous to
   22.0e-v2)
3. 23.0c-rev2 confirms the cell still clears the gates on the OOS slice
4. Production migration considered only after (3)

The `assign_verdict` function does NOT account for the multiple-testing
inflation in the 144-cell space; this is intentional (the per-filter
verdict mirrors the 23.0b/c/d convention so cross-stage comparison is
straightforward), but the report must explicitly remind the reader.

---

## §3 Filter definitions (fixed rules)

All filters operate on the 23.0c-style causal z-score:
```
mid_c   = (bid_c + ask_c) / 2  on M5
mu_N    = mid_c.shift(1).rolling(N).mean()
sigma_N = mid_c.shift(1).rolling(N).std(ddof=0)
z[t]    = (mid_c[t] - mu_N[t]) / sigma_N[t]
```
Sigma=0 protection: rows with `sigma_N <= 0` produce no signal.

### F1 — neutral reset (re-entry control)

Modifies the first-touch lock release condition: re-entry permitted
only after `z` returns to the **neutral band** (not just back inside
the threshold band).

```
trigger (long):  z[t] < -threshold  AND  not locked_long
trigger (short): z[t] > +threshold  AND  not locked_short
release: |z[t]| <= NEUTRAL_BAND   (= 0.5, fixed)
fire    -> locked = True
```

**Role**: re-entry control. Forces price to actually return toward
mean (not just briefly back inside the band) before re-firing the same
direction.

### F2 — cooldown (time-interval control)

First-touch trigger plus a fixed-duration block on the same direction
regardless of where `z` is.

```
trigger (long):  z[t] < -threshold  AND  z[t-1] >= -threshold
                 AND  (t - last_long_fire_idx >= COOLDOWN_BARS)
                 AND  not locked_long  (standard first-touch lock)
trigger (short): mirrored
COOLDOWN_BARS = 3   (= 3 M5 bars, fixed)
```

The standard first-touch lock (release at `z` back inside band) is
preserved; the cooldown adds an *extra* time block. Long-side and
short-side cooldowns are independent.

**Role**: time-interval control. Prevents re-fires within 3 M5 bars
(= 15 min) of the previous fire even if `z` oscillates rapidly.

### F3 — reversal confirmation (reversal start confirmation)

**Replaces** the first-touch trigger with a "wait for reversal to
start" trigger. Includes its own lock with neutral-band release.

```
trigger (long):
  z[t] < -threshold
  AND  z[t] > z[t-1]            (z is rising)
  AND  mid_c[t] > mid_c[t-1]    (mid_c is rising)
  AND  not locked_long

trigger (short):
  z[t] > +threshold
  AND  z[t] < z[t-1]            (z is falling)
  AND  mid_c[t] < mid_c[t-1]    (mid_c is falling)
  AND  not locked_short

release: |z[t]| <= NEUTRAL_BAND   (= 0.5, fixed)
fire    -> locked = True
```

**Role**: reversal start confirmation. By waiting for `z` to reverse
direction (and `mid_c` to confirm), the filter avoids "falling-knife"
entries during accelerating moves; the neutral-band lock prevents
multiple fires during a single bouncing reversal.

### F4 — fixed cost gate (per-entry execution-cost sanity gate)

Generates 23.0c first-touch signals unchanged, then **post-filters
the joined trades** by the per-entry execution cost recorded in the
23.0a outcome dataset.

```
keep:  cost_ratio_at_entry <= COST_GATE_THRESHOLD
drop:  cost_ratio_at_entry > COST_GATE_THRESHOLD
COST_GATE_THRESHOLD = 0.6   (fixed)
```

**Important**: this is a **per-entry execution-cost sanity gate**,
NOT a pair filter. It evaluates each individual trade against its
own bar-level `cost_ratio` (= `spread_pip / atr_at_entry_signal_tf`
recorded in 23.0a §3.5), and drops only the trades whose execution
cost is judged structurally unfavourable. A pair (e.g. `AUD_NZD`)
whose median cost_ratio is high may still contribute trades if any
of its individual bars happen to have favourable per-bar
cost_ratios.

`COST_GATE_THRESHOLD = 0.6` is chosen as the upper edge of the M5 WARN
band (kickoff §6.4 + 23.0a validation report: WARN band [0.40, 0.65]).

**Role**: per-entry execution-cost sanity gate.

---

## §4 Cell sweep grid

Each filter is evaluated independently across the same 36-cell base:

| dim | values | count |
|---|---|---|
| filter | `{F1_neutral_reset, F2_cooldown, F3_reversal_confirmation, F4_cost_gate}` | 4 |
| N (rolling window, M5 bars) | `{12, 24, 48}` | 3 |
| threshold (\|z\|) | `{2.0, 2.5}` | 2 |
| horizon_bars | `{1, 2, 3}` | 3 |
| exit_rule | `{tb, time}` | 2 |

**Total: 4 × 36 = 144 cells.** Each evaluated on the 20-pair pool.

The 23.0c base (no filter) is **NOT re-run** in this PR — the 23.0c
eval_report serves as the baseline for comparison.

---

## §5 8-gate harness (Phase 22 inherited, identical to 23.0b/c/d)

Per cell, pool all 20 pairs' joined trades on `(entry_ts, pair,
signal_timeframe='M5', horizon_bars, direction)` against the 23.0a
parquet (restricted to `valid_label = True`):

| gate | metric | threshold |
|---|---|---|
| **A0** | annual_trades | `>= 70` (overtrading WARN > 1000, NOT blocking) |
| **A1** | per-trade Sharpe (ddof=0, no √N) | `>= +0.082` |
| **A2** | annual_pnl_pip | `>= +180` |
| **A3** | max_dd_pip | `<= 200` |
| **A4** | 5-fold split, drop k=0, eval k=1..4, count Sharpe-positive | `>= 3 / 4` |
| **A5** | annual_pnl after subtracting 0.5 pip per round trip | `> 0` |

`span_years = 730 / 365.25 ≈ 1.9986`.

**Diagnostic-only**: hit_rate, payoff_asymmetry, S0 random-entry,
S1 strict 80/20 OOS, per-pair contribution, per-session contribution.

---

## §6 Verdict structure

### 6.1 Per-filter verdict

For each of the 4 filters, select the best cell (max A1 Sharpe among
A0-passers) and assign a 3-class verdict:

| verdict | criteria |
|---|---|
| **ADOPT_CANDIDATE** | A0..A5 all pass AND S1 strict OOS strong (`oos > 0` and `oos/is >= 0.5`). Per §2, this is hypothesis-generating only — 23.0c-rev2 mandatory before production. |
| **PROMISING_BUT_NEEDS_OOS** | A0..A3 pass but A4 OR A5 fails; OR A0..A5 all pass but S1 weak |
| **REJECT** | A1 OR A2 fails; OR A0 fails. With reject_reason ∈ {under_firing, still_overtrading, pnl_edge_insufficient, robustness_failure} |

### 6.2 Overall headline verdict

```
overall_verdict =
  if any filter ADOPT_CANDIDATE:
    overall = ADOPT_CANDIDATE  (note which filter)
  elif any filter PROMISING_BUT_NEEDS_OOS:
    overall = PROMISING_BUT_NEEDS_OOS  (note which filter)
  else:
    overall = REJECT
```

### 6.3 Phase 23 routing post-23.0c-rev1

```
23.0c-rev1 returns:
├── any filter ADOPT_CANDIDATE / PROMISING
│     → that single frozen cell promotes to 23.0c-rev2
│       (frozen-cell strict OOS, no parameter re-search)
│     → 23.0e meta-labeling MAY trigger on this cell
│     → Phase 23 conclusion (path B): "naive firing was the issue;
│       signal-quality controls fix it"
│
└── all 4 filters REJECT
      → 23.0e DOES NOT trigger
      → Phase 23 closes with negative-but-bounded conclusion (path A):
        "M5/M15 has no recoverable edge even with stronger signal-quality
        controls; cost regime improvement (M5 0.57 / M15 0.32 vs M1 1.28)
        was insufficient even when paired with the four-filter battery"
      → Phase 24 (Exit/Capture Study, kickoff §7) is the next pivot
```

### 6.4 F4-only improvement flag (mandatory)

If F4 is the **only** filter producing ADOPT_CANDIDATE / PROMISING (and
F1, F2, F3 all REJECT), the eval_report must flag this as a
**cost-based selection effect**:

> The improvement is driven by selecting trades with favourable
> execution cost, not by improving signal precision per se. The same
> per-entry cost filter could be applied to ANY signal source as a
> trivial post-hoc improvement. F4-only ADOPT_CANDIDATE therefore
> warrants extra scrutiny before being treated as evidence for "M5
> z-score MR has a recoverable edge under signal-quality controls":
> the result may instead say "high-cost trades drag the average; drop
> them and the average improves," which is a tautology rather than a
> finding about MR.

This flag does not block the verdict; it is an interpretation note for
downstream consumers.

---

## §7 Production-readiness clause (mandatory in eval_report.md)

Even an ADOPT_CANDIDATE verdict on one filter is **NOT** production-ready.
This is a 144-cell diagnostic sweep — multiple-testing inflation is
substantial. The path forward requires:

1. Identify the ADOPT/PROMISING cell on the winning filter
2. Open a separate `23.0c-rev2` PR with that frozen cell as input
3. Run strict OOS validation on the held-out 20% (or fresh data) with
   no parameter re-search and no filter re-search
4. Production discussion only after 23.0c-rev2 confirms

---

## §8 Comparison table (mandatory in eval_report.md)

The eval report must include the following comparison table verbatim:

| stage / filter | best Sharpe | best annual_pnl pip | best annual_trades | best cell |
|---|---|---|---|---|
| 23.0c base (no filter) | -0.283 | -109,888 | 43,378 | N=48, thr=2.5, h=3, time |
| F1 neutral_reset | TBD | TBD | TBD | TBD |
| F2 cooldown | TBD | TBD | TBD | TBD |
| F3 reversal_confirmation | TBD | TBD | TBD | TBD |
| F4 cost_gate | TBD | TBD | TBD | TBD |

The 23.0c base row is a transcribed reference from the 23.0c eval
report. Each filter's row is filled at runtime.

Plus a per-filter "filter effectiveness" summary table with median
Sharpe / median annual_trades / count of cells passing each gate
across the 36 sub-cells per filter.

---

## §9 Filter-role interpretation labels (mandatory in eval_report.md)

The report must include the role label for each filter explicitly so
the reader does not confuse the four mechanisms:

- **F1 neutral_reset**: re-entry control
- **F2 cooldown**: time-interval control
- **F3 reversal_confirmation**: reversal start confirmation
- **F4 cost_gate**: per-entry execution-cost sanity gate (NOT a pair filter)

---

## §10 Walk-forward methodology (A4 — same as 23.0b/c/d)

5 chronological quintiles of equal trade count, k=0 dropped, k=1..4
evaluated, A4 passes if ≥ 3/4 fold Sharpes > 0.

---

## §11 Outputs and commit policy

### Committed
- `docs/design/phase23_0c_rev1_signal_quality.md` (this file)
- `scripts/stage23_0c_rev1_signal_quality_eval.py`
- `tests/unit/test_stage23_0c_rev1_signal_quality.py`
- `artifacts/stage23_0c_rev1/eval_report.md` (generated)
- `artifacts/stage23_0c_rev1/run.log`

### NOT committed (regenerable)
- `artifacts/stage23_0c_rev1/sweep_results.parquet` — raw per-cell metrics
- `artifacts/stage23_0c_rev1/sweep_results.json` — sidecar JSON

---

## §12 Mandatory unit tests (≥ 16 cases)

| # | name | what it verifies |
|---|---|---|
| 1 | `test_filter_constants_fixed_not_search` | NEUTRAL_BAND=0.5, COOLDOWN_BARS=3, COST_GATE_THRESHOLD=0.6 are module constants; no CLI overrides |
| 2 | `test_zscore_computation_matches_23_0c` | base z-score matches 23.0c (regression check via direct comparison) |
| 3 | `test_f1_neutral_reset_lock_release_at_z_inside_neutral_band` | sustained dip → 1 fire; z back to ±0.5 → re-fire allowed; another dip → 2nd fire |
| 4 | `test_f1_neutral_reset_does_not_release_in_outer_band` | z bounces between -threshold and -0.5 (not entering neutral) → no re-fire |
| 5 | `test_f2_cooldown_3_bars_blocks_re_entry` | first-touch fire → next 3 bars blocked even if z re-crosses |
| 6 | `test_f2_cooldown_does_not_block_after_4_bars` | first-touch fire → bar 4 onwards re-firing allowed (subject to first-touch lock) |
| 7 | `test_f2_cooldown_independent_per_direction` | long fires, short can still fire on same/next bar |
| 8 | `test_f3_reversal_confirmation_requires_z_rising_for_long` | z below -threshold but FALLING → no fire |
| 9 | `test_f3_reversal_confirmation_requires_mid_c_rising_for_long` | z rising but mid_c falling → no fire |
| 10 | `test_f3_reversal_confirmation_fires_when_both_rising_and_z_below` | z below -threshold AND z rising AND mid_c rising → fire |
| 11 | `test_f3_neutral_band_lock_release` | F3 locks until \|z\| <= 0.5 |
| 12 | `test_f4_cost_gate_drops_high_cost_signals` | trades with cost_ratio > 0.6 dropped from cell |
| 13 | `test_f4_cost_gate_keeps_low_cost_signals` | trades with cost_ratio <= 0.6 preserved |
| 14 | `test_signal_join_to_23_0a_outcome_per_filter` | each filter's signals join cleanly to 23.0a M5 outcomes |
| 15 | `test_no_phase22_m1_cell_reused` | runtime assertion: signal_timeframe == 'M5' |
| 16 | `test_per_filter_verdict_assignment` | synthetic gate matrix per filter → correct verdict |
| 17 | `test_overall_verdict_picks_best_filter` | mock 4-filter results → overall picks ADOPT_CANDIDATE if any exists |
| 18 | `test_smoke_mode_3pairs_4filters_2cells_each` | --smoke covers all 4 filters with reduced grid |
| 19 | `test_filter_effectiveness_ranking_in_report` | report contains the 4-filter ranking table |
| 20 | `test_f4_cost_gate_is_per_entry_not_pair_filter` | F4 keeps individual low-cost trades from any pair, doesn't drop entire pairs |

---

## §13 NG list compliance

| NG | how 23.0c-rev1 complies |
|---|---|
| 1 | 20-pair canonical, no pair filter (F4 is per-entry) |
| 2 | No train-side time filter |
| 3 | No test-side filter; 80/20 OOS chronological diagnostic only |
| 4 | No WeekOpen-aware weighting |
| 5 | No universe-restricted cross-pair feature |
| 6 | M5 signal_TF; no `conf` parameter; not the Phase 22 M1 cell |
| 7 | n/a |
| 8 | 23.0a M5 outcome dataset is sole PnL source |

---

## §14 Effort estimate

| item | hours |
|---|---|
| F1/F2/F3 sequential signal generators (numpy loops) | 3-4 |
| F4 post-join cost filter | 0.5 |
| Per-filter sweep + 8-gate harness | 1-2 |
| Per-filter + overall verdict + filter-effectiveness ranking | 1-2 |
| Tests (target 18-20) | 3-4 |
| Eval report drafting (with §6.4 F4-only flag, §8 comparison table, §9 role labels) | 1-2 |
| Full eval run (~12-15 min) | included |
| **Total** | **9-13** |

---

## §15 Document role boundary

This file is the stage contract for 23.0c-rev1. Per-cell results go to
`artifacts/stage23_0c_rev1/eval_report.md`. The §2 multiple-testing
caveat, §6.4 F4-only flag, §7 production-readiness clause, §8
comparison table, and §9 role labels are **normative** for the report
generation — the script must emit them verbatim or in equivalent form.

If a contradiction arises between this doc and the kickoff doc, the
kickoff wins.
