# Stage 24.0d — Regime-Conditional Exits on Frozen Entry Streams

**Date**: 2026-05-07
**Predecessor (kickoff)**: `docs/design/phase24_design_kickoff.md`
**Predecessor (foundation)**: `docs/design/phase24_0a_path_ev_characterisation.md`
**Predecessor (sibling stages)**: `docs/design/phase24_0b_trailing_stop.md`, `docs/design/phase24_0c_partial_exit.md`
**Required input**: `artifacts/stage24_0a/frozen_entry_streams.json`

---

## §1 Scope

24.0d tests three regime-conditional exit-rule variants on the frozen
entry streams from 24.0a. Regime tags are computed causally at signal
time and used **exclusively** to select an exit parameter (trailing
distance K_ATR or partial-exit fraction) per trade. **Regime tags MUST
NOT be used to drop signals or filter entries** — entry stream count is
invariant across all regime configurations.

### Mandatory clause (verbatim in eval_report.md)

> **All frozen entry streams originate from Phase 23.0d REJECT cells.
> Phase 24.0d tests exit-side capture only; it does not reclassify the
> entry signal itself as ADOPT. Regime conditioning is applied to exit
> logic only — regime tags select an exit parameter (trailing K or
> partial fraction) per trade and never drop or filter entries.**
> Production-readiness still requires `24.0d-v2` frozen-cell strict OOS.

### In scope
- 3 regime modes × 3 variants = 9 variants × 3 frozen cells = 27 cells
- Causal regime tags (NG#11 carried forward)
- M1 path simulation reusing 24.0b ATR trailing + 24.0c P1 partial-exit
  simulators (NG#10 strict close-only carried forward)
- 8-gate verdict per cell + headline (max A1 Sharpe among A0-passers)
- realised_capture_ratio + per_regime_breakdown diagnostics

### Out of scope
- Combined regime conditions (e.g., R1 × R2 stacked): deferred to 24.0e
- Multi-step regime decisions (e.g., trend changes during trade): out of Phase 24
- Re-search of frozen entry stream parameters (24.0a sealed)

### Hard constraints
- `src/`, `scripts/run_*.py`, DB schema, existing 22.x / 23.x / 24
  kickoff / 24.0a / 24.0b / 24.0c docs/artifacts unchanged
- 20-pair canonical universe; signal_timeframe == "M15" runtime assertion
- Frozen entry streams imported VERBATIM (no parameter override)
- Regime is exit-parameter selector only (kickoff §5 24.0d restriction)
- NG#10 strict close-only (carried)
- NG#11 causal regime tags (carried)

---

## §2 CRITICAL — regime is exit-parameter selector ONLY (kickoff §5)

> **Allowed**: regime selects which trailing distance / partial fraction is applied per trade.
> **PROHIBITED**: regime as entry filter ("if session is X, do not enter the trade" / "if ATR is high, drop signal" / "if trend is up, only take longs").

The Phase 22/23 NG list explicitly rejected time-of-day, session, and
regime-based entry filtering (NG#1-6 inheritance). Phase 24.0d must NOT
revive that route via the back door of "regime-conditional exits".

**Mandatory unit test**:
`test_regime_is_exit_parameter_only_not_entry_filter` — for any regime
configuration variant, the entry-stream pooled trade count is identical
to the baseline (regime-blind) count. Regime never drops or filters a
signal.

> **R2 session regime is NOT a market-open filter.** The session names
> (`asian` / `london` / `ny`) are conventional UTC bucket labels for
> hour-of-day grouping. They do NOT correspond to actual market-session
> boundaries (which vary with daylight saving and would require pair-
> specific tags). 24.0d uses fixed UTC buckets `[0, 8) / [8, 16) /
> [16, 24)` purely as a 3-way hour-of-day partition for exit-parameter
> selection.

---

## §3 Regime types and tag computation (NG#11 causal — mandatory)

### R1 — ATR regime (binary, cross-pair median split)

**Tag**: `low_vol` if `atr_at_entry_signal_tf < ATR_MEDIAN`, else `high_vol`.

`ATR_MEDIAN` is the **cross-pair median** of all valid signals'
`atr_at_entry_signal_tf` values (pip units), computed once at script
start across the 20-pair × N-cells universe. Per-pair medians are NOT
used.

`atr_at_entry_signal_tf` is taken directly from 23.0a labels parquet
(already causal — computed via `mid_c.shift(1).rolling(ATR_PERIOD)` per
23.0a §2.1). NG#11 trivially compliant.

### R2 — Session regime (3-bucket by UTC hour)

**Tag**: based on `entry_ts.hour_utc`:
- `asian` if `0 <= hour < 8`
- `london` if `8 <= hour < 16`
- `ny` if `16 <= hour < 24`

> **Note**: these labels are conventional bucket names for fixed UTC
> hour ranges, NOT market-open filters. 24.0d does not enforce any
> market-session semantic. The labels are purely cosmetic for the
> 3-way hour-of-day partition.

`entry_ts` is always known at signal generation (before exit logic runs);
NG#11 trivially compliant.

### R3 — Trend regime (binary, M15 slope using shift(1))

**Tag**: based on `slope_5` computed causally from M15 mid_c series:
```
slope_5(t) = mid_c.shift(1)[t] - mid_c.shift(1)[t - 5]
           = mid_c[t-1] - mid_c[t-5]    (M15 5-bar slope)
trend = "up"   if slope_5 > 0
trend = "down" if slope_5 <= 0
```

The `shift(1)` ensures the slope uses bars **strictly before** the signal
bar — `mid_c[t]` (the signal bar's own close) is NEVER used. Entry-time
data only. NG#11 compliant.

For the first 5 M15 bars (where `slope_5` is undefined), the trend tag
defaults to `"up"`. This affects only the warmup region and is washed
out across the 730-day signal stream.

**Mandatory unit test**: `test_no_forward_looking_regime_tag` — synthesise
an M15 series whose post-signal data would invert the slope; verify the
trend tag is unaffected (uses `shift(1)` only).

---

## §4 Variants (3 modes × 3 variants = 9, with uniform controls)

### Mode R1 — ATR-regime-conditional ATR trailing

Exit logic: 24.0b T1 ATR trailing with regime-conditional `K_ATR`.
- low-vol trade → use `K_low`
- high-vol trade → use `K_high`

| variant | K_low | K_high | role |
|---|---|---|---|
| `R1_v1` | 1.0 | 2.0 | high-vol gets wider trail |
| `R1_v2` | 1.5 | 2.5 | symmetric upshift |
| `R1_v3` | 1.5 | 1.5 | **uniform control** (no regime conditioning effect) |

### Mode R2 — Session-regime-conditional partial-exit fraction

Exit logic: 24.0c P1 TP/2-triggered partial exit with regime-conditional
`partial_fraction`.

| variant | asian | london | ny | role |
|---|---|---|---|---|
| `R2_v1` | 0.25 | 0.50 | 0.75 | increasing through UTC day |
| `R2_v2` | 0.75 | 0.50 | 0.25 | decreasing through UTC day |
| `R2_v3` | 0.50 | 0.50 | 0.50 | **uniform control** |

### Mode R3 — Trend-regime-conditional ATR trailing

Exit logic: 24.0b T1 ATR trailing with regime-conditional `K_ATR` based
on whether trade direction matches trend regime.

For longs:
- `up` trend = `with_trend` (trade direction matches)
- `down` trend = `against_trend`

For shorts:
- `down` trend = `with_trend`
- `up` trend = `against_trend`

| variant | with_trend K | against_trend K | role |
|---|---|---|---|
| `R3_v1` | 2.0 | 1.0 | looser trail when trend matches direction |
| `R3_v2` | 1.0 | 2.0 | tighter trail when trend matches |
| `R3_v3` | 1.5 | 1.5 | **uniform control** |

### Sweep total

`3 frozen cells × (3 + 3 + 3) = 3 × 9 = 27 cells`.

The three uniform-control variants (`R1_v3`, `R2_v3`, `R3_v3`) provide
within-mode sanity checks: if regime conditioning gives no improvement,
the conditional variants should not outperform their uniform
counterparts. If a non-uniform variant beats its uniform control,
that is evidence of regime-conditional information capture.

---

## §5 NG#10 strict close-only (carried from 24.0b/0c)

24.0d's exit simulators are **direct imports** from:
- `stage24_0b._simulate_atr_long` / `_simulate_atr_short` (R1, R3)
- `stage24_0c._simulate_p1_long` / `_simulate_p1_short` (R2)

These simulators were unit-tested in 24.0b/0c to satisfy NG#10 strict
close-only (running max/min, exit, TP/SL/BE all at M1 close; no intra-
bar high/low). 24.0d inherits the discipline by reuse — no
re-implementation.

**Mandatory unit tests**:
- `test_ng10_close_only_inherited_via_24_0b_simulator`
- `test_ng10_close_only_inherited_via_24_0c_simulator`

---

## §6 Spread treatment (carried from 24.0b/0c)

Long: `bid_close` for triggers; pnl = `(exit_bid_close - entry_ask) / pip`.
Short: `ask_close` for triggers; pnl = `(entry_bid - exit_ask_close) / pip`.

---

## §7 8-gate harness + verdict (Phase 22/23 inherited)

A0..A5 thresholds identical. REJECT-reason classification with
`path_ev_unrealisable` (carried from 24.0b/0c). S0/S1 diagnostic-only.

Headline = best of 27 cells (max A1 Sharpe among A0-passers).

---

## §8 Diagnostics

### realised_capture_ratio (carried)
`mean(realised_pnl) / mean(best_possible_pnl)` per cell. Diagnostic-only.

### per_regime_breakdown (NEW for 24.0d)
Per cell, sub-statistics broken out by regime bucket:
- R1: low-vol / high-vol → (n_trades, sharpe, mean_pnl, hit_rate)
- R2: asian / london / ny → (n_trades, sharpe, mean_pnl, hit_rate)
- R3: up / down → (n_trades, sharpe, mean_pnl, hit_rate)

Diagnostic-only.

> **`per_regime_breakdown` is NOT used to drop or filter trades.** It
> is purely a post-hoc analysis of how the realised PnL distributes
> across regime buckets within a cell. Using `per_regime_breakdown` to
> ex-post select a "best regime" and drop the others would itself be
> a regime-as-entry-filter route and is explicitly out of scope.

---

## §9 Phase 24 routing post-24.0d

If headline ADOPT_CANDIDATE / PROMISING:
- 24.0e (exit meta-labeling) trigger condition met per kickoff §5
  ("if any of 24.0b/c/d returns ADOPT_CANDIDATE OR PROMISING_BUT_NEEDS_OOS")
- 24.0d-v2 production-readiness candidate downstream

If headline REJECT:
- 24.0e is NOT triggered (assuming 24.0b and 24.0c also REJECT, as is
  the case here)
- 24.0f Phase 24 final synthesis becomes the next stage; Phase 24
  closes path A (analogous to Phase 23 path A but at the exit-side
  search-space level)

---

## §10 M1 path simulation pipeline

1. Per pair: load M1 BA, aggregate to M15, compute mid_c slope arrays
   (R3 prep), generate 23.0d signals per N, load 23.0a M15 labels.
2. Pass 1 (cross-pair ATR median): collect all signals' joined
   `atr_at_entry_signal_tf`; compute cross-pair median.
3. Pass 2 (per-cell × per-variant): for each frozen cell × variant, per
   pair, per signal: compute regime tag (R1 ATR vs median / R2 hour /
   R3 slope), look up exit parameter from variant, dispatch to 24.0b/0c
   simulator, collect pnl + regime tag.
4. Pool 20 pairs per cell, compute 8-gate metrics + per_regime_breakdown.

Estimated runtime: ~25-35 min on 20 pairs × 27 cells.

---

## §11 Mandatory unit tests (≥ 16)

| # | name | what it verifies |
|---|---|---|
| 1 | `test_frozen_entry_streams_imported_from_24_0a` | 3 cells, all 23.0d / M15 / h=4 |
| 2 | `test_regime_constants_fixed` | R1/R2/R3 variant constants are module-level |
| 3 | `test_variants_count_9` | 3 + 3 + 3 = 9 variants |
| 4 | `test_regime_is_exit_parameter_only_not_entry_filter` | for ANY regime variant, pooled entry-stream count is identical (regime never drops a signal) |
| 5 | `test_no_forward_looking_regime_tag` | R3 trend uses `mid_c.shift(1)` only — signal bar's own data NEVER used |
| 6 | `test_r1_atr_regime_uses_cross_pair_median` | low/high split at cross-pair median, NOT per-pair |
| 7 | `test_r1_atr_dispatch_K_low_vs_K_high` | low-vol → K_low; high-vol → K_high |
| 8 | `test_r2_session_3_buckets_utc_hour` | hour [0,8)→asian, [8,16)→london, [16,24)→ny |
| 9 | `test_r2_session_labels_are_utc_bucket_not_market_open` | docstring assertion + module constant `_R2_LABELS_ARE_CONVENTIONAL_UTC_BUCKETS = True` |
| 10 | `test_r2_dispatch_partial_fraction_by_session` | exit fraction looked up by session bucket |
| 11 | `test_r3_trend_slope_5_mid_c_shift1` | slope = mid_c[t-1] - mid_c[t-5] |
| 12 | `test_r3_trend_uptrend_long_uses_with_trend_K` | long + up regime → with_trend K |
| 13 | `test_r3_trend_downtrend_short_uses_with_trend_K` | short + down regime → with_trend K |
| 14 | `test_ng10_close_only_inherited_via_24_0b_simulator` | imports `stage24_0b._simulate_atr_long/short` directly |
| 15 | `test_ng10_close_only_inherited_via_24_0c_simulator` | imports `stage24_0c._simulate_p1_long/short` directly |
| 16 | `test_uniform_controls_have_no_regime_effect` | R1_v3 / R2_v3 / R3_v3 use the same exit param across all regime buckets |
| 17 | `test_a4_4fold_majority_inherited` | reuses Phase 23 _fold_stability |
| 18 | `test_reject_reason_path_ev_unrealisable_inherited` | A0 pass + A1/A2 fail → "path_ev_unrealisable" |
| 19 | `test_smoke_mode_3pairs_subset_variants` | smoke covers all 3 modes |
| 20 | `test_per_regime_breakdown_in_metrics` | per-bucket sub-stats reported (diagnostic) |

---

## §12 NG list compliance

| NG | how 24.0d complies |
|---|---|
| 1-8 | Phase 23 inheritance unchanged |
| 9 | Mandatory clause + frozen-stream attribution |
| **10** | strong rule: all exit triggers via 24.0b/0c simulators (close-only); mandatory unit tests 14/15 |
| **11** | strong rule: regime tags causal — R1 (23.0a causal ATR), R2 (always-known hour), R3 (shift(1) slope); mandatory unit tests 5/11 |
| **kickoff §5 24.0d** | strong rule: regime is exit-parameter selector ONLY; mandatory unit test 4 (regime never drops signal) |

---

## §13 CLI contract

```bash
python scripts/stage24_0d_regime_conditional_eval.py [--smoke] [--frozen-json artifacts/stage24_0a/frozen_entry_streams.json]
```

Smoke: 3 pairs × 1 frozen cell × 3 variants (1 from each mode).

---

## §14 Outputs

- **Committed**: design doc, script, tests, eval_report.md, run.log
- **Gitignored**: `sweep_results.{parquet,json}`

eval_report.md mandatory sections:
1. Mandatory clause (frozen from REJECT cells; regime conditioning applied to exit logic only)
2. NG#10 strict-rule disclosure
3. NG#11 causal regime-tag disclosure
4. **24.0d-specific**: regime is exit-parameter selector only (NOT entry filter); R2 session labels are conventional UTC buckets, not market-open filters
5. realised_capture_ratio + per_regime_breakdown disclosures (both diagnostic-only; per_regime_breakdown must NOT be used to drop trades)
6. Verdict header + frozen-stream attribution
7. 27-cell sweep summary (sorted by Sharpe descending)
8. Per-mode (R1/R2/R3) effectiveness comparison + uniform-control comparison (does conditional beat uniform?)
9. Per-regime-bucket diagnostic (within best cell)
10. Best cell deep-dive (gates, fold sharpes, capture, per-pair, per-session)
11. Phase 24 routing: 24.0e trigger condition; if all 24.0b/c/d REJECT → 24.0f closure

---

## §15 Effort estimate

| 項目 | hours |
|---|---|
| Frozen-stream import + entry-stream replay (reuse 24.0b/c) | 1 |
| 3 regime tag computers (R1/R2/R3) with NG#11 enforcement | 2-3 |
| Regime-conditional dispatcher (wraps 24.0b/0c simulators) | 2 |
| Per-regime breakdown diagnostic | 1 |
| 8-gate harness reuse | 1 |
| Tests (≥ 16, target 18-20, mandatory NG#10/NG#11/entry-filter prohibition) | 4 |
| Eval report drafting (with regime breakdown + uniform control comparison) | 2 |
| Full eval run (~25-35 min) | included |
| **Total** | **13-15** |

---

## §16 Document role boundary

This file is the stage contract for 24.0d. Per-cell results go to
`artifacts/stage24_0d/eval_report.md`. Frozen entry streams sealed by
24.0a; this 24.0d PR seals the regime-variant constants. Downstream
stages do NOT override.

If a contradiction arises between this doc and the kickoff, the kickoff
wins.
