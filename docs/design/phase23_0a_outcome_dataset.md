# Stage 23.0a — M5/M15 Outcome Dataset Design

**Date**: 2026-05-06
**Predecessor (Phase 23 starting reference)**: `docs/design/phase23_design_kickoff.md`
**Phase 22 analogue (read-only reference)**: `docs/design/phase22_0a_scalp_label_design.md`

This stage builds the foundation outcome datasets that all subsequent
Phase 23 stages (23.0b/c/d/e/e-v2/f) will consume. It is a **dataset
construction PR** — no strategy claims, no parameter sweeps, no EV
verdicts. Phase 23.0b/c/d will use these parquets as their input.

---

## §1 Scope and constraints

### In scope
- Build path-aware outcome datasets at signal timeframes **M5** and **M15**
- 20 canonical pairs (no pair filter)
- 730-day OANDA M1 BA dataset (same source as 22.0a; 22.0a labels are NOT touched)
- Standard barrier profile only: `TP = 1.5 × ATR(14)`, `SL = 1.0 × ATR(14)`, ATR computed on the **signal timeframe**
- Conservative same-bar TP/SL ambiguity resolution (SL priority)
- Schema is 22.0a-compatible (column-subset compatible) with explicit grouping (key / price / outcome / validity / context / barrier)

### Explicitly out of scope
- Any strategy implementation (z-score MR / Donchian) — those are 23.0b/c/d
- Any meta-labeling — that is 23.0e
- Wide barrier profile (`TP=2.0/SL=1.5` or similar) — deferred to a follow-up
- M15 horizon=3 (45 min) and horizon ≥ 8 — deferred per kickoff §6.2
- DB schema, `src/`, `scripts/run_*.py`, runner code — none touched

### Hard constraints (mirroring kickoff §10)
- `src/` not touched
- `scripts/run_*.py` not touched
- DB schema not touched
- Existing Phase 22 artifacts and docs not modified
- 20-pair canonical universe (no filter)
- No pair / time-of-day filter applied at dataset construction

---

## §2 Aggregation convention

### 2.1 M1 → M5 / M15 right-closed/right-labeled

OANDA M1 candle timestamps mark the **start** of the bar. Aggregation to a higher TF uses pandas resample with `label='right'` and `closed='right'`:

- A signal-TF bar labeled `T` aggregates the M1 bars whose start timestamps fall in the half-open interval `(T - tf_minutes, T]`.
- Open / High / Low / Close are computed separately for the `bid_*` and `ask_*` columns (not the mid).
- Empty bins (e.g., across weekend gaps) are dropped. Aggregated bars that contain fewer than `tf_minutes` constituent M1 bars are still kept (boundary cases at week start / week end), but are still subject to the gap-affected check on the M1 path that follows them.

The label timestamp `T` itself is the boundary at which the signal-TF bar is "complete". An M5 bar labeled `09:05` is the M5 bar whose constituent M1 bars are `(09:00, 09:05]`. The close of this M5 bar is the close of the M1 bar at `09:05` (the M1 bar starting at `09:05` and ending at `09:06`).

### 2.2 Entry timing

For a signal generated on the close of the signal-TF bar at `signal_ts`:

- `entry_ts` is recorded as `signal_ts` itself (the signal-TF bar boundary at which the signal "becomes known").
- The entry M1 bar is the M1 bar whose start timestamp is `signal_ts + 1 minute` (i.e., the FIRST M1 bar that begins **after** the signal-TF bar's close). This is the smallest representable look-ahead-free entry.
- `entry_ask` = `ask_o` of that entry M1 bar (long uses ask).
- `entry_bid` = `bid_o` of that entry M1 bar (short uses bid).

If the M1 bar at `signal_ts + 1 minute` is missing (weekend gap, holiday, or data hole), the signal row is marked `valid_label = False` and all metric columns are NaN. The signal_TF bar itself is still recorded so that downstream consumers can join.

### 2.3 Path on M1

The path-aware metrics are computed on the **M1** bars covering exactly `horizon_bars × tf_minutes` minutes following the entry M1 bar (inclusive of the entry bar). For a signal of `(timeframe=M15, horizon_bars=4)`, this is 60 M1 bars: M1[`signal_ts + 1 min`] through M1[`signal_ts + 60 min`] inclusive.

- The exit-at-horizon is the **close** of the LAST M1 bar in the path. For long, exit uses `bid_c`; for short, exit uses `ask_c`.
- All TP / SL trigger checks read M1 highs and lows, with the appropriate bid/ask side per direction.

If the path runs past the end of the M1 dataset, the signal row is marked `valid_label = False`.

---

## §3 Schema

The Parquet output has the following columns. Every column appears in every row; direction-specific values (mfe, mae, tb_outcome, etc.) are NaN-or-default for invalid rows.

### 3.1 Key columns

| column | dtype | description |
|---|---|---|
| `entry_ts` | timestamp[ns, UTC] | The signal-TF bar boundary at which the signal becomes known. Tz-aware. |
| `pair` | string | One of the 20 canonical pairs. |
| `signal_timeframe` | string | `"M5"` or `"M15"`. Encoded in BOTH the file name (`labels_M5_*.parquet` / `labels_M15_*.parquet`) and as a row column so that downstream `pd.concat` is safe. |
| `horizon_bars` | int8 | Number of signal-TF bars (M5: 1/2/3, M15: 1/2/4). |
| `horizon_minutes` | int16 | `horizon_bars × tf_minutes`. Convenience column. |
| `direction` | string | `"long"` or `"short"`. |

Row key uniqueness: `(entry_ts, pair, signal_timeframe, horizon_bars, direction)`.

### 3.2 Price columns

| column | dtype | description |
|---|---|---|
| `entry_ask` | float64 | `ask_o` of the M1 bar at `signal_ts + 1 min`. |
| `entry_bid` | float64 | `bid_o` of the M1 bar at `signal_ts + 1 min`. |
| `exit_bid_close` | float64 | `bid_c` of the M1 bar at end of path (long exit price). |
| `exit_ask_close` | float64 | `ask_c` of the M1 bar at end of path (short exit price). |

### 3.3 Outcome columns

| column | dtype | description |
|---|---|---|
| `tb_pnl` | float32 | Triple-barrier PnL in pips, signed. `+tp_dist_pip` if TP first, `-sl_dist_pip` if SL first, `time_exit_pnl` if neither hit. |
| `time_exit_pnl` | float32 | Time-exit PnL in pips: long = `(exit_bid_close - entry_ask) / pip`; short = `(entry_bid - exit_ask_close) / pip`. |
| `best_possible_pnl` | float32 | Path peak PnL in pips, after entry-side spread. Long = `(max bid_h - entry_ask) / pip`; short = `(entry_bid - min ask_l) / pip`. |
| `worst_possible_pnl` | float32 | Path trough PnL in pips, after entry-side spread. Long = `(min bid_l - entry_ask) / pip`; short = `(entry_bid - max ask_h) / pip`. |
| `mfe_after_cost` | float32 | Alias of `best_possible_pnl` — included for downstream readers expecting the 22.0a-style name. |
| `mae_after_cost` | float32 | Alias of `worst_possible_pnl`. |
| `tb_outcome` | int8 | `1` = TP first, `-1` = SL first, `0` = time exit (neither hit). |
| `time_to_tp` | float32 | Number of M1 bars from entry until first TP touch (1-indexed; 1 = first M1 bar). NaN if no TP. |
| `time_to_sl` | float32 | Same for SL. NaN if no SL. |
| `hit_tp` | bool | True iff TP barrier was touched at any point in the path (regardless of whether SL was also touched). |
| `hit_sl` | bool | True iff SL barrier was touched at any point in the path. |
| `same_bar_tp_sl_ambiguous` | bool | True iff at least one M1 bar in the path simultaneously touched both TP and SL (with bar high/low; intra-bar order unknown). |

### 3.4 Validity columns

| column | dtype | description |
|---|---|---|
| `valid_label` | bool | True iff entry M1 bar exists, full path fits, ATR is finite and positive, and entry/exit prices are finite. False rows have all metric columns NaN-or-default. |
| `gap_affected_forward_window` | bool | True iff any M1 bar inside the forward path has a delta-from-previous-M1 timestamp greater than 300 seconds (weekend gap, holiday, data hole). Independent of `valid_label`; a row may be valid AND gap-affected. |

### 3.5 Context columns

| column | dtype | description |
|---|---|---|
| `atr_at_entry_signal_tf` | float32 | ATR(14) computed on the **signal timeframe**, in pip units, at the bar just before `entry_ts` (causal). |
| `spread_entry` | float32 | `(entry_ask - entry_bid) / pip` at the entry M1 bar. |
| `cost_ratio` | float32 | `spread_entry / atr_at_entry_signal_tf`. The headline cost-regime metric for the kickoff §6.4 validation gates. |

### 3.6 Barrier columns

| column | dtype | description |
|---|---|---|
| `barrier_profile` | string | `"standard"` for this PR. Reserved for `"wide"` etc. in follow-ups. |
| `tp_atr_mult` | float32 | Multiplier applied to the signal-TF ATR to set TP distance. `1.5` for standard. |
| `sl_atr_mult` | float32 | Multiplier for SL distance. `1.0` for standard. |
| `tp_dist_pip` | float32 | Realised TP distance in pips for this row: `tp_atr_mult × atr_at_entry_signal_tf`. |
| `sl_dist_pip` | float32 | Realised SL distance in pips for this row: `sl_atr_mult × atr_at_entry_signal_tf`. |

### 3.7 Auxiliary columns

| column | dtype | description |
|---|---|---|
| `exit_reason` | string | `"tp"`, `"sl"`, `"time"`, or `"weekend_gap"`. Derived from `tb_outcome` and `gap_affected_forward_window`. Convenience column; downstream consumers may re-derive. |

### 3.8 Schema compatibility with 22.0a

Every 22.0a column whose meaning carries over (`entry_ts`, `pair`, `horizon_bars`, `direction`, `tb_pnl`, `time_exit_pnl`, `tb_outcome`, `time_to_tp`, `time_to_sl`, `same_bar_tp_sl_ambiguous`, `entry_ask`, `entry_bid`, `exit_bid_close`, `exit_ask_close`, `gap_affected_forward_window`, `valid_label`, `mfe_after_cost`, `mae_after_cost`, `spread_entry`, `cost_ratio`) is present here with the same dtype and same semantics. Phase 23 adds the explicit signal_timeframe / horizon_minutes / hit_tp / hit_sl / barrier_profile / tp_atr_mult / sl_atr_mult / tp_dist_pip / sl_dist_pip / atr_at_entry_signal_tf / best_possible_pnl / worst_possible_pnl / exit_reason columns. Removed: 22.0a's diagnostic-only `path_shape_class`, `is_week_open_window`, `hour_utc`, `dow`, `atr_at_entry` columns are NOT carried over (the Phase 23 audit-mandated allowlist excludes the time-of-day signals from main features; ATR is renamed to `atr_at_entry_signal_tf` for explicitness).

---

## §4 Same-bar TP/SL ambiguity

When a single M1 path bar has a high above the TP barrier AND a low below the SL barrier, the intra-bar sequence is unobservable. Two consequences:

1. `same_bar_tp_sl_ambiguous = True` for that row (the flag is True if any path bar is ambiguous, not just the first-hit bar).
2. `tb_outcome` resolution treats the ambiguous bar as **SL** (conservative). Concretely, the algorithm builds two boolean trigger arrays `tp_trig` and `sl_trig` over the path, then computes:
   - `effective_tp = tp_trig & ~sl_trig`
   - `effective_sl = sl_trig` (SL wins on ambiguous bars)
   - `tb_outcome = +1` if `first(effective_tp)` strictly precedes `first(effective_sl)`, `-1` if the reverse (or only SL), `0` otherwise.

The raw `tp_trig` / `sl_trig` arrays are NOT persisted, but `hit_tp = tp_trig.any()` and `hit_sl = sl_trig.any()` ARE persisted — so a downstream consumer can reconstruct an "optimistic" interpretation (count `hit_tp & ~hit_sl` as TP, `hit_sl & ~hit_tp` as SL, the remaining as ambiguous) or a "drop ambiguous" interpretation without re-running the build.

Mirrors the Phase 22 22.0a convention.

---

## §5 Validation gates

Validation runs after dataset construction and produces `validation_report.md`. It separates **WARN** from **HALT** outcomes.

### WARN (logged; does NOT block 23.0b/c/d kickoff)

- M5 cross-pair median `cost_ratio` outside `[0.40, 0.65]`.
- M15 cross-pair median `cost_ratio` outside `[0.20, 0.45]`.
- Per-pair `cost_ratio` median is in the WARN band but the cross-pair median is in the OK band (single-pair anomaly).
- Same-bar ambiguity rate exceeds 5% on any pair × horizon × direction cell.

WARN entries are listed in the report with a `[WARN]` prefix and the specific pair / TF / metric.

### HALT (blocks 23.0b/c/d kickoff; closes Phase 23 with a halt note per kickoff §5)

- M15 cross-pair median `cost_ratio` ≥ M5 cross-pair median (the cost regime ordering is structurally wrong).
- M5 cross-pair median `cost_ratio` ≥ Phase 22 M1 median 1.28 (M5 is no better than M1).
- M15 cross-pair median `cost_ratio` ≥ Phase 22 M1 median 1.28 (M15 is no better than M1).
- Coverage `n_valid_rows / theoretical_max_rows` < 95% for any pair × TF.
- Bid/ask sign convention check fails (a fabricated long signal at known-monotonic-up M1 series produces negative time_exit_pnl, or vice versa).
- Schema compatibility check fails (any column missing, wrong dtype, or wrong nullability vs `label_schema.json`).

Reference: kickoff §6.4 set the 50% / 25–35% targets; the WARN/HALT bands above widen the targets to account for cross-pair heterogeneity (Phase 22 M1 already showed a per-pair range of ~67% to ~237%).

---

## §6 Deliverables

### Committed
- `docs/design/phase23_0a_outcome_dataset.md` (this file)
- `scripts/stage23_0a_build_outcome_dataset.py`
- `scripts/stage23_0a_validate_dataset.py`
- `tests/unit/test_stage23_0a_outcome_dataset.py`
- `artifacts/stage23_0a/validation_report.md` (generated)
- `artifacts/stage23_0a/label_schema.json` (generated)
- `artifacts/stage23_0a/run.log` (generated)
- A `.gitignore` rule excluding the per-pair parquets

### Generated but NOT committed (regenerable from script + data)
- `artifacts/stage23_0a/labels_M5/labels_M5_<pair>.parquet` × 20
- `artifacts/stage23_0a/labels_M15/labels_M15_<pair>.parquet` × 20

---

## §7 Tests (mandatory unit-test list)

Every item is a single-purpose test in `tests/unit/test_stage23_0a_outcome_dataset.py`:

| # | Name | What it verifies |
|---|---|---|
| 1 | `test_aggregate_m1_to_m5_right_closed_right_labeled` | M5 bar labeled `09:05` aggregates M1 bars at start times 09:01..09:05; OHLC matches expected from synthetic M1. |
| 2 | `test_aggregate_m1_to_m15_right_closed_right_labeled` | Same for M15. |
| 3 | `test_signal_aggregation_does_not_use_future_m1_bars` | M5 bar at `09:05` does not include any M1 bar with start ≥ `09:06`. |
| 4 | `test_entry_uses_next_m1_bar_open` | For signal at `09:05`, `entry_ask == ask_o` of M1 bar starting `09:06`. |
| 5 | `test_entry_ts_equals_signal_close` | `entry_ts` in the parquet equals the signal-TF bar's right-edge timestamp. |
| 6 | `test_no_lookahead_in_path_index` | All path M1 bar timestamps are strictly greater than `entry_ts`. |
| 7 | `test_long_bid_ask_convention` | Long entry uses ask, exit uses bid; on a synthetic monotonic-up series, time_exit_pnl_long > 0. |
| 8 | `test_short_bid_ask_convention` | Short entry uses bid, exit uses ask; monotonic-up series → time_exit_pnl_short < 0. |
| 9 | `test_horizon_4_m15_covers_60_m1_bars` | For M15 h=4, the path contains exactly 60 M1 bars and `exit_*_close` reads the 60th bar. |
| 10 | `test_tp_sl_atr_scaling_on_signal_tf` | `tp_dist_pip == 1.5 × atr_at_entry_signal_tf` and SL is `1.0 ×`. ATR uses the signal-TF, not M1. |
| 11 | `test_same_bar_ambiguous_resolves_to_sl` | A synthetic M1 bar with high above TP and low below SL resolves to `tb_outcome = -1` and the row is flagged `same_bar_tp_sl_ambiguous = True`. |
| 12 | `test_hit_tp_and_hit_sl_preserved_for_ambiguous` | When ambiguous, both `hit_tp` and `hit_sl` are True (preserves optimistic-reinterpretation capability). |
| 13 | `test_gap_affected_flag_set_on_weekend` | A weekend gap inserted into the synthetic series lights `gap_affected_forward_window`. |
| 14 | `test_valid_label_false_when_path_runs_past_end_of_data` | The last `horizon × tf_minutes` M1 bars worth of signal-TF rows have `valid_label = False`. |
| 15 | `test_schema_columns_match_design` | The output parquet has exactly the columns enumerated in §3, in that order, with the documented dtypes. |
| 16 | `test_schema_identity_within_tf` | Two different pairs at the same TF produce parquets with identical schema (column names, column order, dtypes). |
| 17 | `test_schema_compat_with_22_0a` | Every 22.0a column listed in §3.8 as carried over is present with the same dtype. |
| 18 | `test_signal_timeframe_present_as_column_and_filename` | The output has both `signal_timeframe` as a column and lives at the correctly-named path. |
| 19 | `test_tz_aware_timestamps` | `entry_ts` dtype is timestamp with tz=UTC. |
| 20 | `test_resolution_agnostic_gap_detection` | Gap detection works whether the M1 DatetimeIndex resolution is ns or us (regression test for the 22.0a fix). |
| 21 | `test_barrier_profile_columns_persisted` | All five barrier columns (`barrier_profile`, `tp_atr_mult`, `sl_atr_mult`, `tp_dist_pip`, `sl_dist_pip`) are present and equal to standard-profile values for every row. |

---

## §8 NG list compliance check

Phase 23 inherits the 8-item NG list from kickoff §4. Per-item:

| NG | Compliance |
|---|---|
| 1 | 20-pair canonical universe, no filter applied. |
| 2 | No train-side time filter; this stage is dataset-only. |
| 3 | No test-side filter improvement claim; outcome-only PR. |
| 4 | No WeekOpen-aware sample weighting (and no week-open-window column persisted). |
| 5 | No universe-restricted cross-pair feature. |
| 6 | No M1 Donchian-immediate cell touched (this PR has no strategy at all). |
| 7 | Implicit; relevant only at evaluation stages. |
| 8 | New outcome dataset; 22.0a M1 dataset is read-only. |

---

## §9 Effort estimate

| Item | Hours |
|---|---|
| Aggregation + schema + barrier implementation | 4-5 |
| Validation script (WARN/HALT gates) | 2 |
| 20 pairs × 2 TFs generation (with parallelism) | 1-2 |
| Tests (21 cases) | 3-4 |
| Validation report drafting | 1 |
| **Total** | **11-14** |

---

## §10 Document role boundary

This file is the **stage contract** for 23.0a: schema, conventions, gates, deliverables. It does **not** describe strategy logic (that belongs in 23.0b/c/d) and does **not** record outcome statistics (those go into `artifacts/stage23_0a/validation_report.md`).

If a contradiction arises between this doc and the kickoff doc, the **kickoff** wins; this doc's role is to operationalise it for one stage.
