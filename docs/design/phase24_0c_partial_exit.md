# Stage 24.0c — Partial-Exit Variants on Frozen Entry Streams

**Date**: 2026-05-07
**Predecessor (kickoff)**: `docs/design/phase24_design_kickoff.md`
**Predecessor (foundation)**: `docs/design/phase24_0a_path_ev_characterisation.md`
**Predecessor (sibling stage)**: `docs/design/phase24_0b_trailing_stop.md`
**Required input**: `artifacts/stage24_0a/frozen_entry_streams.json` (top-K=3 cells, 23.0d M15 first-touch Donchian h=4)

---

## §1 Scope

24.0c tests three single-rule partial-exit variants on the frozen entry
streams from 24.0a. Each variant splits the position into two legs: a
fraction exited at the partial trigger, a remainder held to TP/SL/time.
M1 path simulation with NG#10 strict close-only causality and
direction-aware bid/ask close discipline (per 24.0b convention).

**Mandatory clause** (verbatim in eval_report.md):

> **All frozen entry streams originate from Phase 23.0d REJECT cells.
> Phase 24.0c tests exit-side capture only; it does not reclassify the
> entry signal itself as ADOPT.** A 24.0c ADOPT_CANDIDATE verdict means
> "for this entry stream that Phase 23 rejected, this partial-exit
> variant captures enough of the path-EV (per 24.0a) into realised PnL
> to clear the gates" — NOT "this entry signal is now adopted".
> Production-readiness still requires `24.0c-v2` frozen-cell strict OOS.

### In scope
- 3 frozen cells × 9 partial-exit variants = 27 cells
- M1 path simulation with bid/ask close discipline
- 8-gate verdict per cell + headline (max A1 Sharpe among A0-passers)
- realised_capture_ratio + partial_hit_rate diagnostics

### Out of scope
- Combinations of partial-exit modes (e.g., P1 + P3 stacked): deferred to 24.0e
- Fraction sweep on P3 (kept fixed at 0.5): deferred to a follow-up if motivated
- Intra-bar partial-exit variants: deferred to a hypothetical `24.0c-rev1` follow-up
- Re-search of frozen entry stream parameters (24.0a sealed)

### Hard constraints
- `src/` not touched
- `scripts/run_*.py` not touched
- DB schema not touched
- Existing 22.x / 23.x / 24 kickoff / 24.0a / 24.0b docs / artifacts unchanged
- 20-pair canonical universe; no pair / time-of-day filter
- `signal_timeframe == "M15"` runtime assertion (24.0a frozen cells)
- Frozen entry streams imported VERBATIM (no parameter override on entry signal generator)
- Partial-exit logic at M1 bar close ONLY (NG#10 strict)
- **Full TP/SL takes priority over partial trigger at the same M1 close** (see §3 ordering)

---

## §2 Frozen entry streams (imported from 24.0a, identical to 24.0b)

```
rank 1: 23.0d  N=50, h=4, exit=tb     (REJECT, still_overtrading)
rank 2: 23.0d  N=50, h=4, exit=time   (REJECT, still_overtrading)  -- same entry as rank 1
rank 3: 23.0d  N=20, h=4, exit=tb     (REJECT, still_overtrading)
```

Cells 1 and 2 share the same entry stream (24.0a tie). 24.0c will
produce identical metrics for them, documented in the report.

---

## §3 Partial-exit variants (3 modes × 3 params = 9 variants)

All variants wrap the 23.0a barrier profile (TP=1.5×ATR, SL=1.0×ATR)
with a partial-exit leg.

### Mode P1 — TP/2-triggered partial exit (price-triggered)

```
For long:
  partial_trigger_price = entry_ask + 0.5 * TP_ATR_MULT * ATR
                        = entry_ask + 0.75 * ATR    (= TP/2)
  Initial: full position; SL = entry_ask - 1.0 * ATR; TP = entry_ask + 1.5 * ATR

For short:  mirrored with entry_bid; partial_trigger_price = entry_bid - 0.75 * ATR

Per-bar order at each M1 close:
  1. Full TP/SL check (priority — see §3.4)
  2. Partial trigger check (only if full TP/SL did not fire and partial not done)
```

**Sweep**: `partial_fraction ∈ {0.25, 0.50, 0.75}` (3 values). Trigger
fixed at TP/2 = 0.75 × ATR.

### Mode P2 — Time-based midpoint partial exit

```
midpoint_idx = HORIZON_M1_BARS // 2 = 30  (half of 60 M1 bars for h=4)

Per-bar order at each M1 close:
  1. Full TP/SL check (priority)
  2. If t == midpoint_idx and partial not done: fire partial at this bar's close
```

**Sweep**: `partial_fraction ∈ {0.25, 0.50, 0.75}` (3 values). Midpoint
fixed at HORIZON_M1_BARS // 2.

### Mode P3 — MFE-triggered partial exit (close-only MFE)

```
For long:
  running_max_close = max(bid_close[entry..t])     (close-only, NG#10 strict)
  mfe_trigger_price = entry_ask + K_MFE * ATR
  partial fires when running_max_close >= mfe_trigger_price

For short:
  running_min_close = min(ask_close[entry..t])
  mfe_trigger_price = entry_bid - K_MFE * ATR
  partial fires when running_min_close <= mfe_trigger_price

The partial exit is executed at the same M1 close that first satisfies
the trigger (i.e., the bar at which running_max/min first crosses the
threshold). NO high/low is used.

Per-bar order at each M1 close:
  1. Update running_max / running_min (close-only)
  2. Full TP/SL check (priority)
  3. MFE trigger check (only if full TP/SL did not fire and partial not done)
```

**Sweep**: `K_MFE ∈ {1.0, 1.5, 2.0}` × ATR (3 values). `partial_fraction`
fixed at 0.5 (per user spec, fraction sweep on P3 deferred).

### §3.4 Per-bar priority ordering (CRITICAL — applied to all 3 modes)

> **At any M1 bar where both full TP/SL and partial trigger conditions
> are satisfied, full TP/SL takes priority and the partial trigger does
> NOT fire on that bar.**

Concretely:
- **P1**: at any bar, FIRST check `bid_close >= TP` and `bid_close <= SL` (long) / `ask_close <= TP` and `ask_close >= SL` (short). If full TP/SL hits, exit immediately (full position if partial not yet done; remaining-fraction position if partial already done from a previous bar). Only if neither full TP nor full SL fired on this bar, check the partial trigger.
- **P2**: at the midpoint bar (`t == midpoint_idx`), FIRST check full TP/SL. If full TP/SL fires, exit; partial does NOT fire even though `t == midpoint_idx`. Only if neither full TP nor full SL fired, fire the midpoint partial.
- **P3**: at any bar, FIRST update `running_max/min` (needed for MFE state), THEN check full TP/SL. If full TP/SL fires, exit; partial does NOT fire even if `running_max >= mfe_trigger`. Only if neither full TP nor full SL fired, check the MFE trigger.

**Mandatory unit tests (one per mode)** verify this priority:
- `test_p1_full_tp_priority_over_partial_at_same_bar`
- `test_p1_full_sl_priority_over_partial_at_same_bar`
- `test_p2_full_tp_priority_at_midpoint_bar`
- `test_p3_full_tp_priority_over_mfe_partial_at_same_bar`

Total: 27 cells.

---

## §4 NG#10 — strict close-only causality (mandatory)

Same strict reading as 24.0b — extended to partial-exit triggers:

- **All TP/SL/partial/MFE triggers** evaluated against `bid_close` (long) / `ask_close` (short) at M1 bar close ONLY.
- **MFE running_max** (P3): uses `bid_close` for long, `ask_close` for short — NOT high/low.
- **No intra-bar favourable ordering**, no forward-looking decisions.

The hybrid alternative ("running_max uses high, exit at close") is NOT
adopted. Intra-bar variants are out of Phase 24 scope.

**Mandatory unit tests**:
- `test_p1_partial_evaluated_at_close_only`
- `test_p3_mfe_running_max_uses_close_only`
- `test_no_intrabar_lookahead_on_partial_triggers`

---

## §5 Spread treatment (direction-aware bid/ask close, per 24.0b)

### Long
- `entry_ask` from 23.0a entry M1 bar
- All triggers (partial, TP, SL) and MFE running_max evaluated against `bid_close`
- Partial leg pnl: `fraction × (exit_bid_close - entry_ask) / pip`
- Remaining leg pnl: `(1 - fraction) × (exit_bid_close - entry_ask) / pip`

### Short
- `entry_bid` from 23.0a entry M1 bar
- All triggers and MFE running_min evaluated against `ask_close`
- Partial leg pnl: `fraction × (entry_bid - exit_ask_close) / pip`
- Remaining leg pnl: `(1 - fraction) × (entry_bid - exit_ask_close) / pip`

### Total per-trade pnl
```
if partial_done:
    total_pnl = partial_leg_pnl + remaining_leg_pnl
else:
    total_pnl = full-position exit pnl   (= (exit_close - entry) / pip for long)
```

`pip_size = 0.01` for JPY pairs, `0.0001` otherwise (per 23.0a).

---

## §6 8-gate harness (Phase 22/23 inherited, identical to 24.0b)

Same gates. REJECT-reason classification carried from 24.0b including
`path_ev_unrealisable`. S0/S1 diagnostic-only.

---

## §7 Diagnostics (NOT gates)

### realised_capture_ratio (24.0b convention)

```
realised_capture_ratio = mean(realised_pnl) / mean(best_possible_pnl)
```

Diagnostic-only — `best_possible_pnl` is ex-post path peak (after entry-
side spread), not executable PnL. Reported per cell for cross-variant
comparison.

### partial_hit_rate (NEW for 24.0c)

```
partial_hit_rate = count(trades with partial_done=True) / total_trades
```

Diagnostic-only. Reports how often the partial trigger actually fired
across the trade population. Useful to interpret per-mode behaviour:
- High partial_hit_rate + improved Sharpe → partial logic is the active mechanism
- Low partial_hit_rate + improved Sharpe → improvements come from full TP/SL behaviour, not partial

---

## §8 Verdict 3-class + headline

Same as 24.0b. Headline = best of 27 cells (max A1 Sharpe among A0-
passers).

If headline is ADOPT_CANDIDATE / PROMISING:
- 24.0d (regime-conditional) still mandatory per kickoff §5
- 24.0c-v2 production-readiness PR is candidate downstream
If headline is REJECT:
- 24.0d continues independently; 24.0c REJECT does NOT halt Phase 24

---

## §9 M1 path simulation pipeline

Per pair: load M1 BA → aggregate to M15 → generate signals (23.0d
module) → load 23.0a M15 labels → join → for each cell × variant,
simulate per-trade with partial-exit logic → pool 20 pairs → 8-gate
harness.

Estimated runtime: ~20-30 min on 20 pairs × 27 cells.

---

## §10 Mandatory unit tests (≥ 16 cases)

| # | name | what it verifies |
|---|---|---|
| 1 | `test_frozen_entry_streams_imported_from_24_0a` | 3 cells, all 23.0d / M15 / h=4 |
| 2 | `test_partial_exit_constants_fixed` | `PARTIAL_FRACTIONS={0.25,0.50,0.75}`, `K_MFE={1.0,1.5,2.0}`, `MIDPOINT_IDX=30`, P3 fraction = 0.5, all module constants |
| 3 | `test_variants_count_9` | 3 + 3 + 3 = 9 variants |
| 4 | `test_p1_partial_fires_at_tp_half_long` | bid_close >= entry+0.75*ATR → partial fires (when no TP/SL hit) |
| 5 | `test_p1_partial_evaluated_at_close_only` | NG#10: high above trigger but close below → no partial fire |
| 6 | `test_p1_full_tp_priority_over_partial_at_same_bar` | bid_close >= TP AND >= partial_trigger on same bar → full TP exit, no partial |
| 7 | `test_p1_full_sl_priority_over_partial_at_same_bar` | bid_close <= SL on same bar → full SL exit, no partial |
| 8 | `test_p2_partial_fires_at_midpoint_only` | partial fires only at t == midpoint_idx (when no TP/SL hit) |
| 9 | `test_p2_full_tp_priority_at_midpoint_bar` | at midpoint bar with bid_close >= TP → full TP exit, no midpoint partial |
| 10 | `test_p3_mfe_running_max_uses_close_only` | high above mfe_trigger but close below → MFE not yet triggered |
| 11 | `test_p3_mfe_partial_fires_when_running_max_close_crosses` | running_max_close (bid) >= mfe_trigger AND no TP/SL hit → partial fires at this bar's close |
| 12 | `test_p3_full_tp_priority_over_mfe_partial_at_same_bar` | bid_close >= TP AND running_max >= mfe_trigger on same bar → full TP exit, no MFE partial |
| 13 | `test_partial_pnl_weighted_sum` | total_pnl = fraction × partial_leg + (1-fraction) × remaining_leg |
| 14 | `test_long_uses_bid_close_partial` | all P1/P2/P3 long sims use bid_close for triggers and exit prices |
| 15 | `test_short_uses_ask_close_partial` | mirrored for short |
| 16 | `test_remaining_leg_takes_tp_after_partial` | post-partial: bid_close >= TP → remaining at TP, total = partial + remaining |
| 17 | `test_time_exit_with_partial_done` | horizon end with partial_done=True → time exit on remaining; total includes both legs |
| 18 | `test_partial_done_false_full_position_exit` | when partial trigger never fires, exit is full-position pnl (not weighted) |
| 19 | `test_a4_4fold_majority_inherited` | reuses Phase 23 _fold_stability |
| 20 | `test_reject_reason_path_ev_unrealisable_inherited_from_24_0b` | A0 pass + A1/A2 fail → "path_ev_unrealisable" |
| 21 | `test_smoke_mode_3pairs_subset_variants` | smoke covers all 3 modes |
| 22 | `test_partial_hit_rate_diagnostic_in_metrics` | `partial_hit_rate` key in metrics dict |

---

## §11 NG list compliance

| NG | how 24.0c complies |
|---|---|
| 1-8 | Phase 23 inheritance unchanged |
| 9 | Mandatory clause + frozen-stream attribution in report |
| **10** | strong rule: partial / TP / SL / MFE running_max all at M1 bar close ONLY; mandatory unit tests 5/9/10/12 enforce; per-bar TP/SL priority ordering tests 6/7/9/12 enforce |
| 11 | n/a (24.0c is regime-blind) |

---

## §12 CLI contract

```bash
python scripts/stage24_0c_partial_exit_eval.py [--smoke] [--frozen-json artifacts/stage24_0a/frozen_entry_streams.json]
```

Smoke: 3 pairs × 1 frozen cell × 3 variants (1 from each mode P1/P2/P3).

---

## §13 Outputs

- **Committed**: design doc, script, tests, eval_report.md, run.log
- **Gitignored**: `sweep_results.{parquet,json}` (Phase 23/24 convention)

eval_report.md mandatory sections:
1. Mandatory clause (frozen from REJECT cells; 24.0c tests exit-side capture only)
2. NG#10 strict-rule disclosure (close-only; per-bar TP/SL priority)
3. realised_capture_ratio + partial_hit_rate diagnostic disclosure
4. Verdict header + frozen-stream attribution
5. 27-cell sweep summary (sorted by Sharpe descending)
6. Per-mode P1/P2/P3 effectiveness comparison
7. Best cell deep-dive (gates, fold sharpes, S0/S1, capture, partial_hit_rate, per-pair, per-session)
8. Phase 24 routing: 24.0d still mandatory; 24.0c-v2 candidate if ADOPT/PROMISING

---

## §14 Effort estimate

| 項目 | hours |
|---|---|
| Frozen-stream import + entry-stream replay (reuse 24.0b infrastructure) | 1 |
| 3 partial-exit modes (P1/P2/P3) implementation with bid/ask close + weighted pnl | 3-4 |
| Per-bar priority ordering (full TP/SL > partial) with explicit testing | 1 |
| 8-gate harness reuse | 1 |
| Tests (≥ 16, target 18-22, mandatory NG#10 + priority) | 3-4 |
| Eval report drafting | 2 |
| Full eval run (~20-30 min on 20 pairs × 27 cells) | included |
| **Total** | **11-14** |

---

## §15 Document role boundary

This file is the stage contract for 24.0c. Per-cell results go to
`artifacts/stage24_0c/eval_report.md`. Frozen entry streams sealed by
24.0a; this 24.0c PR seals the partial-exit constants
(PARTIAL_FRACTIONS / K_MFE / MIDPOINT_IDX / P3 fraction). Downstream
stages (24.0d / 24.0e) do NOT override.

If a contradiction arises between this doc and the kickoff, the kickoff
wins.
