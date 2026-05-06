# Stage 24.0b — Trailing-Stop Variants on Frozen Entry Streams

**Date**: 2026-05-07
**Predecessor (kickoff)**: `docs/design/phase24_design_kickoff.md`
**Predecessor (foundation)**: `docs/design/phase24_0a_path_ev_characterisation.md`
**Required input**: `artifacts/stage24_0a/frozen_entry_streams.json` (top-K=3 cells, all 23.0d M15 first-touch Donchian h=4)

---

## §1 Scope

24.0b tests three single-rule trailing-stop variants (ATR-scaled, fixed-pip,
breakeven-move) on the frozen entry streams from 24.0a. All exit decisions
are computed at M1 bar close per Phase 24 NG#10 strict reading. The 8-gate
harness (Phase 22/23 inherited) decides ADOPT_CANDIDATE / PROMISING /
REJECT per cell and overall.

**Mandatory clause** (verbatim in eval_report.md per user spec):

> **All frozen entry streams originate from Phase 23.0d REJECT cells.
> Phase 24.0b tests exit-side capture only; it does not reclassify the
> entry signal itself as ADOPT.** A Phase 24.0b ADOPT_CANDIDATE verdict
> means: "for this entry stream that Phase 23 rejected, this trailing-
> stop variant converts enough of the path-EV (per 24.0a) into realised
> PnL to clear the gates" — NOT "this entry signal is now adopted".
> Production-readiness still requires `24.0b-v2` frozen-cell strict OOS
> per kickoff §7.

### In scope
- 3 frozen cells × 11 trailing variants = 33 cells
- M1 path simulation with bid/ask close discipline (direction-aware)
- 8-gate verdict per cell + headline (max A1 Sharpe among A0-passers)
- realised_capture_ratio diagnostic (NOT a gate, NOT production efficiency)

### Out of scope
- Combinations of trailing modes (e.g., ATR + breakeven): deferred to 24.0e
- Intra-bar trailing variants (high/low usage): not in Phase 24 (deferred to 24.0b-rev1 if motivated)
- Re-search of frozen entry stream parameters (24.0a sealed)
- Model-based exits: 24.0e (conditional)

### Hard constraints
- `src/` not touched
- `scripts/run_*.py` not touched
- DB schema not touched
- Existing 22.x / 23.x / 24 kickoff / 24.0a docs / artifacts unchanged
- 20-pair canonical universe; no pair / time-of-day filter
- `signal_timeframe == "M15"` runtime assertion (24.0a frozen cells are all M15)
- **Frozen entry streams imported VERBATIM** (no parameter override on entry signal generator)
- Trailing logic at M1 bar close ONLY (NG#10 strict)

---

## §2 Frozen entry streams (imported from 24.0a)

```
rank 1: 23.0d  N=50, h=4, exit=tb     (REJECT, still_overtrading)
rank 2: 23.0d  N=50, h=4, exit=time   (REJECT, still_overtrading)  -- same entry signal as rank 1
rank 3: 23.0d  N=20, h=4, exit=tb     (REJECT, still_overtrading)
```

All cells: M15 first-touch Donchian, horizon = 4 (= 60 minute holding window).

The script imports `artifacts/stage24_0a/frozen_entry_streams.json` and
re-generates entry signals using
`stage23_0d.extract_signals_first_touch_donchian` per pair × N. The
`exit_rule` field in the JSON is the 23.0a baseline reference; 24.0b's
trailing variants REPLACE it.

**Note**: ranks 1 and 2 share the same entry stream (N=50, M15 first-touch
Donchian) — the only difference in the 24.0a JSON is `cell_params.exit_rule`
(tb vs time), which 24.0b overrides. The two cells will therefore produce
identical trailing metrics; this is a 24.0a tie artefact, documented in
the report. The 24.0b verdict is determined by the unique-entry-stream
top performer, not the duplicate row.

---

## §3 Trailing-stop variants (3 modes, single-rule, FIXED constants)

Each frozen cell × each variant produces a 24.0b cell. The variant
constants are sealed in this PR; downstream stages (24.0c/d/e) cannot
override them.

### Mode T1 — ATR trailing
Trail distance = `K_ATR × ATR_at_entry`, where `ATR_at_entry` is the
signal-TF ATR (M15 ATR(14) at signal close, fixed at entry).

**K_ATR sweep**: `{1.0, 1.5, 2.0, 2.5}` (4 values).

### Mode T2 — Fixed-pip trailing
Trail distance = fixed pip value (independent of ATR).

**fixed_pip sweep**: `{5, 10, 20, 30}` pip (4 values).

### Mode T3 — Breakeven move
Wraps the original 23.0a barrier profile (TP = 1.5 × ATR, SL = 1.0 × ATR)
with a breakeven SL shift triggered when path mfe crosses a threshold.

**BE_threshold sweep**: `{1.0, 1.5, 2.0}` × ATR (3 values).

### Total

`3 cells × (4 + 4 + 3) = 3 × 11 = 33 cells`

---

## §4 NG#10 — strict close-only causality (mandatory)

Per Phase 24 kickoff §4 NG#10 "Causal exit decisions at M1 bar close
(strong rule)":

> All trailing-stop, partial-exit, and regime-conditional exit decisions
> MUST be computed at M1 bar close. **No intra-bar favourable ordering,
> no forward-looking path decisions, no "if the high happened before the
> low" assumptions.**

24.0b's strict reading enforces:

1. **Running max / min uses M1 close only** (NOT high or low). For long
   trailing, `running_max = max(bid_close[entry..t])`. For short,
   `running_min = min(ask_close[entry..t])`.
2. **Exit condition evaluated at M1 close only**. If `bid_close[t] <=
   trail_level` (long) → exit at this bar's `bid_close[t]`. The intra-bar
   low is NOT used.
3. **TP / SL / BE all at close only**. T3 mode's TP, SL, and BE-shifted-SL
   are checked against `bid_close` (long) or `ask_close` (short) only.
4. **No favourable intra-bar ordering**. No "high happened before low"
   assumptions; no "TP touched before SL on the same bar" assumptions.

The hybrid alternative ("running max uses high, exit uses close") is
**explicitly NOT adopted** in 24.0b. If motivated by 24.0b results, a
follow-up `24.0b-rev1` PR may introduce intra-bar variants — but Phase
24 closes its core verdict on the strict-close basis.

**Mandatory unit test**: `test_no_intra_bar_lookahead`. Construct
synthetic bars where intra-bar high / low would naively trigger an exit
but close does not; verify NO exit fires. Construct a complementary case
where close triggers exit; verify exit fires.

---

## §5 Spread treatment (direction-aware bid/ask close)

Consistent with 23.0a's bid/ask convention:

### Long
- `running_max_close = max(bid_close[entry..t])`
- `trail_level = running_max_close - distance`
- exit if `bid_close[t] <= trail_level` → `exit_close = bid_close[t]`
- `pnl_pip = (exit_close - entry_ask) / pip_size`

For T3:
- TP check: `bid_close[t] >= entry_ask + 1.5 * ATR` → exit at `bid_close[t]`
- SL check: `bid_close[t] <= sl_level` → exit at `bid_close[t]`
- BE shift: when `(bid_close[t] - entry_ask) >= BE_threshold * ATR`, set `sl_level = entry_ask`

### Short
- `running_min_close = min(ask_close[entry..t])`
- `trail_level = running_min_close + distance`
- exit if `ask_close[t] >= trail_level` → `exit_close = ask_close[t]`
- `pnl_pip = (entry_bid - exit_close) / pip_size`

For T3:
- TP check: `ask_close[t] <= entry_bid - 1.5 * ATR` → exit at `ask_close[t]`
- SL check: `ask_close[t] >= sl_level` → exit at `ask_close[t]`
- BE shift: when `(entry_bid - ask_close[t]) >= BE_threshold * ATR`, set `sl_level = entry_bid`

### Time exit (no trailing or TP/SL hit within horizon)
- Long: `pnl_pip = (bid_close[horizon-1] - entry_ask) / pip_size`
- Short: `pnl_pip = (entry_bid - ask_close[horizon-1]) / pip_size`

`pip_size = 0.01` for JPY pairs, `0.0001` otherwise (per 23.0a `pip_size_for`).

`entry_ask` and `entry_bid` come from M1 bar at `signal_ts + 1 minute`
(per 23.0a convention). `ATR_at_entry` is the M15 signal-TF ATR
(`atr_at_entry_signal_tf` from 23.0a labels, in pip units).

---

## §6 8-gate harness (Phase 22/23 inherited, identical to 23.0b/c/d/c-rev1)

A0 ann_tr ≥ 70 (overtrading WARN > 1000, NOT blocking),
A1 Sharpe (ddof=0, no √N) ≥ +0.082,
A2 ann_pnl_pip ≥ +180,
A3 max_dd_pip ≤ 200,
A4 5-fold split, k=0 dropped, eval k=1..4, count(>0) ≥ 3,
A5 +0.5 pip stress ann_pnl > 0.

**Phase 24 new REJECT reason**: `path_ev_unrealisable` — A0 passes, but A1
and A2 fail on this trailing variant. Means "entry has positive path-EV
per 24.0a, but THIS trailing logic cannot capture enough". Distinct from
`pnl_edge_insufficient` which assumes no edge to capture at all.

S0 (random-entry sanity) and S1 (strict 80/20 OOS on best cell)
diagnostic-only, same convention as Phase 23.

### Diagnostic: realised_capture_ratio (NOT a gate)

Per Phase 24 kickoff §8:

```
realised_capture_ratio = mean(realised_pnl) / mean(best_possible_pnl)
```

Interpretable as "what fraction of path-EV the trailing logic captured".
`realised_pnl` is the trailing variant's per-trade PnL; `best_possible_pnl`
is the 23.0a path peak (after entry-side spread). Diagnostic-only — must
NOT be used in features or in any ADOPT decision. Reported per cell to
help compare T1/T2/T3 effectiveness.

> Note: `best_possible_pnl` is an ex-post path diagnostic, not an
> executable PnL; `realised_capture_ratio` is therefore a diagnostic of
> "how close did this trailing logic get to the unattainable upper
> bound", NOT a measure of production efficiency.

---

## §7 Verdict 3-class (Phase 23 convention)

Per cell: ADOPT_CANDIDATE / PROMISING_BUT_NEEDS_OOS / REJECT.

**Headline verdict** = best of 33 cells (max A1 Sharpe among A0-passers).

If headline is ADOPT_CANDIDATE / PROMISING:
- 24.0c (partial-exit) and 24.0d (regime-conditional) still mandatory per kickoff §5
- 24.0b-v2 frozen-cell strict OOS becomes a candidate downstream PR

If headline is REJECT:
- 24.0c / 24.0d continue independently
- 24.0b's REJECT does NOT halt Phase 24

The mandatory clause in §1 reiterates that an ADOPT_CANDIDATE here does
NOT promote the underlying entry signal to ADOPT — only that the
trailing variant captures enough of the path-EV.

---

## §8 M1 path simulation pipeline

Per pair:
1. Load M1 BA candles (730d).
2. Aggregate to M15 (right-closed/right-labeled, per 23.0a convention).
3. Generate frozen entry signals via `stage23_0d.extract_signals_first_touch_donchian(m15_df, N)` per unique N (= {20, 50}).
4. Load 23.0a M15 labels parquet (read-only). Inner-join signals to labels
   restricted to `valid_label = True`, `horizon_bars = 4`. The labels
   provide `atr_at_entry_signal_tf` (in pip units), `entry_ask`,
   `entry_bid`, etc. — all already-validated 23.0a foundation columns.
5. For each signal × variant: locate entry M1 bar at `signal_ts + 1 min`,
   walk 60 M1 bars forward, simulate trailing logic with bid/ask close
   discipline (§5) and NG#10 strict close-only rule (§4). Compute
   `pnl_pip`.
6. Pool all 20 pairs' trades per cell. Apply 8-gate harness, S0/S1
   diagnostics, and realised_capture_ratio.

Estimated runtime: 20 pairs × ~7s preload + 33 cells × pooled sim ≈
15-25 min total.

---

## §9 Mandatory unit tests (≥ 14 cases)

| # | name | what it verifies |
|---|---|---|
| 1 | `test_frozen_entry_streams_imported` | reads 24.0a JSON; cell count = 3; all 23.0d / M15 / h=4 |
| 2 | `test_no_parameter_override_on_entry_streams` | script does not modify the 23.0d signal generator's signature |
| 3 | `test_atr_trailing_K_constants` | K_ATR sweep = {1.0, 1.5, 2.0, 2.5} (module constant) |
| 4 | `test_fixed_pip_constants` | fixed_pip sweep = {5, 10, 20, 30} |
| 5 | `test_breakeven_threshold_constants` | BE_threshold sweep = {1.0, 1.5, 2.0} |
| 6 | `test_running_max_uses_close_not_high` | synthetic path with high above close → running_max equals max close, not max high |
| 7 | `test_running_min_uses_close_not_low` | mirrored for short |
| 8 | `test_no_intra_bar_lookahead` | bar with low ≤ trail but close > trail → no exit; bar with close ≤ trail → exit |
| 9 | `test_long_trail_uses_bid_close_for_eval_and_exit` | running_max_close, trail_level, exit_price all from bid_close array |
| 10 | `test_short_trail_uses_ask_close_for_eval_and_exit` | mirrored |
| 11 | `test_long_pnl_uses_entry_ask_minus_exit_bid_close` | pnl = (exit_bid_close - entry_ask) / pip |
| 12 | `test_short_pnl_uses_entry_bid_minus_exit_ask_close` | pnl = (entry_bid - exit_ask_close) / pip |
| 13 | `test_breakeven_shifts_sl_to_entry_when_threshold_crossed` | bid_close - entry_ask >= BE * ATR → sl_level = entry_ask |
| 14 | `test_breakeven_does_not_shift_below_threshold` | below threshold → sl unchanged |
| 15 | `test_tp_evaluated_at_close_only` | bar with high ≥ TP but close < TP → no TP exit; close ≥ TP → exit |
| 16 | `test_sl_evaluated_at_close_only` | mirrored for SL |
| 17 | `test_horizon_time_exit_when_no_other` | 60 bars elapse with no trail/TP/SL → time exit at last close |
| 18 | `test_a4_4fold_majority_inherited` | reuses Phase 23 _fold_stability semantics |
| 19 | `test_reject_reason_path_ev_unrealisable` | A0 pass + A1/A2 fail → reject_reason = "path_ev_unrealisable" |
| 20 | `test_smoke_mode_3pairs_subset_variants` | smoke runs without error |

---

## §10 NG list compliance

| NG | how 24.0b complies |
|---|---|
| 1 | 20-pair canonical |
| 2 | No train-side time filter |
| 3 | No test-side filter improvement claim; S1 diagnostic-only |
| 4 | No WeekOpen weighting |
| 5 | No universe-restricted cross-pair feature |
| 6 | M15 signal_TF (24.0a frozen); runtime assertion carried forward |
| 7 | n/a |
| 8 | 23.0a M5/M15 read-only context; M1 BA reloaded for path sim |
| 9 | eval_report.md records frozen streams' Phase 23 source (PR #266 23.0d, REJECT, still_overtrading) verbatim — honest entry-status reporting; mandatory clause about not reclassifying entries as ADOPT |
| **10** | strong rule: trailing logic at M1 bar close ONLY; mandatory unit test 8 (`test_no_intra_bar_lookahead`); tests 6/7/9/10/15/16 also enforce |
| 11 | n/a (24.0b is regime-blind) |

---

## §11 Outputs

- **Committed**: design doc, script, tests, eval_report.md, run.log
- **Gitignored**: `sweep_results.{parquet,json}` (Phase 23 convention)

eval_report.md mandatory sections:
1. Mandatory clause (§1): "frozen entry streams from Phase 23.0d REJECT cells; 24.0b tests exit-side capture only; does NOT reclassify entries as ADOPT"
2. Verdict header + frozen-stream attribution (PR #266, merge commit, Phase 23 verdict, reject_reason)
3. NG#10 strict-rule disclosure: "all exit decisions at M1 bar close; intra-bar variants out of scope (24.0b-rev1 if motivated)"
4. realised_capture_ratio diagnostic disclosure: ex-post diagnostic, NOT production efficiency
5. 33-cell sweep summary (sorted by Sharpe descending)
6. Best cell deep-dive (gates, fold sharpes, S0/S1, per-pair, per-session, realised_capture_ratio)
7. Per-mode T1/T2/T3 effectiveness comparison
8. Per-stage routing: 24.0c/d still mandatory; 24.0b-v2 candidate if ADOPT/PROMISING

---

## §12 Effort estimate

| 項目 | hours |
|---|---|
| Frozen-stream import + entry-stream replay (23.0d module) | 1-2 |
| M1 path simulation infrastructure (per-pair preload) | 2-3 |
| 3 trailing modes (T1/T2/T3) implementation with bid/ask close | 3-4 |
| 8-gate harness reuse + path_ev_unrealisable reject reason | 1 |
| Tests (≥ 14, target 18-20, mandatory NG#10) | 3-4 |
| Eval report drafting (mandatory clause + caveats + per-mode table) | 2 |
| Full eval run (~15-25 min on 20 pairs × 33 cells) | included |
| **Total** | **12-16** |

---

## §13 Document role boundary

This file is the stage contract for 24.0b. Per-cell results go to
`artifacts/stage24_0b/eval_report.md`. The frozen entry streams are
sealed by 24.0a; this 24.0b PR seals the trailing-stop constants
(K_ATR / fixed_pip / BE_threshold). Downstream stages (24.0c / 24.0d /
24.0e) do NOT override 24.0b's trailing constants — combinations are
deferred to 24.0e's meta-labeling layer.

If a contradiction arises between this doc and the kickoff, the kickoff
wins.
