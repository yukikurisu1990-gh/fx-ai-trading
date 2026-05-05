# Stage 23.0b — M5 Donchian Breakout + M1 Execution Baseline

**Date**: 2026-05-06
**Predecessor (kickoff)**: `docs/design/phase23_design_kickoff.md`
**Predecessor (outcome dataset)**: `docs/design/phase23_0a_outcome_dataset.md`
**Phase 22 analogues (read-only)**:
- `docs/design/phase22_0b_mean_reversion_baseline.md` — gate threshold inheritance
- `docs/design/phase22_alternatives_postmortem.md` — Phase 22 Donchian M1 failure record

This stage runs the first Phase 23 strategy evaluation: a **rule-based**
Donchian breakout signal on the M5 timeframe, with M1 execution and the
Phase 22 8-gate harness. There is no LightGBM, no meta-labeling, no
parameter learning — every signal is deterministic from the M5 OHLC.
This is a *naive baseline* whose result feeds 23.0e/e-v2 conditional
meta-labeling if and only if at least one cell scores positive
realistic-exit Sharpe.

---

## §1 Scope and constraints

### In scope
- 18-cell sweep over `(N, horizon_bars, exit_rule)` on the M5 signal timeframe
- 20-pair canonical universe (no pair filter), pooled per cell
- 23.0a M5 outcome dataset (`labels_M5_<pair>.parquet`) as the sole PnL source
- Phase 22 8-gate harness (A0..A5) with **exact** Phase 22 thresholds
- S0 (random-entry sanity) and S1 (strict 80/20 OOS) as **diagnostic-only**
- 3-class verdict: `ADOPT_CANDIDATE`, `PROMISING_BUT_NEEDS_OOS`, `REJECT`

### Explicitly out of scope
- Any meta-labeling layer (that is 23.0e)
- Any per-pair adoption / exclusion (per-pair statistics are diagnostic only)
- Any wide barrier profile, alternative ATR period, or alternative same-bar resolution
- Phase 22's **exact** M1 Donchian-immediate cell (`N=50, conf=0.55, h=40, time_exit_pnl on M1`) — kickoff §8 / NG #6

### Hard constraints (mirroring kickoff §10)
- `src/` not touched
- `scripts/run_*.py` not touched
- DB schema not touched
- Existing 22.x and 23.0a artifacts / docs not modified
- 20-pair canonical universe; no pair / time-of-day filter
- `signal_timeframe == "M5"` enforced at runtime by the sweep

---

## §2 Signal definition (Donchian breakout on M5 mid OHLC)

Operate on **mid prices** at the M5 signal-TF level. The M5 OHLC is
re-aggregated from M1 BA via the same right-closed/right-labeled
convention as 23.0a (we import `aggregate_m1_to_tf` from
`scripts/stage23_0a_build_outcome_dataset.py`).

```
mid_h = (bid_h + ask_h) / 2
mid_l = (bid_l + ask_l) / 2
mid_c = (bid_c + ask_c) / 2

upper_N = mid_h.shift(1).rolling(N).max()
lower_N = mid_l.shift(1).rolling(N).min()

long_break  = mid_c >  upper_N
short_break = mid_c <  lower_N
```

The `shift(1)` enforces causality: at signal bar `t`, `upper_N`/`lower_N`
read M5 bars `[t-N, t-1]` only — never bar `t` itself.

`mid_c` is strict `>` / `<` (not `>=`); equality is treated as no signal.
Both `long_break` and `short_break` cannot be true simultaneously
(would require `mid_c > upper_N` AND `mid_c < lower_N`, which is
arithmetically impossible).

The first `N` M5 bars produce no signal (`upper_N` / `lower_N` NaN).

**Why mid for signal, bid/ask for outcome**: the Donchian band is a
*structural* feature of the price track, computed once per M5 bar; using
mid avoids spread-induced left-right asymmetry. The realised PnL must
account for spread cost, which is why 23.0a recorded bid/ask separated
entry/exit prices and the `tb_pnl` / `time_exit_pnl` columns already
embed that asymmetry.

---

## §3 Cell sweep grid

| dim | values | count |
|---|---|---|
| `N` (Donchian window, M5 bars) | `{10, 20, 50}` | 3 |
| `horizon_bars` | `{1, 2, 3}` | 3 |
| `exit_rule` | `{tb, time}` (= `tb_pnl` / `time_exit_pnl`) | 2 |

**Total: 18 cells.** Each cell is evaluated on the 20-pair pool.

The set excludes Phase 22's M1 Donchian-immediate cell (`N=50,
conf=0.55, h=40, time_exit_pnl on M1`) by construction:
- `signal_timeframe` here is M5 (Phase 22 cell was M1)
- `horizon_bars` here are 1/2/3 in M5 units (= 5/10/15 min); Phase 22's
  h=40 is in M1 units (= 40 min)
- The outcome dataset is `labels_M5_*.parquet` (Phase 22 cell used `labels_*.parquet` in M1)
- There is no `conf` parameter in 23.0b (rule-based, no model)

A runtime assertion in the script verifies `signal_timeframe == "M5"`
for every emitted trade row.

---

## §4 8-gate harness — Phase 22 thresholds, mirrored exactly

Per cell, pool all 20 pairs' joined trades (via inner join on
`(entry_ts, pair, signal_timeframe='M5', horizon_bars, direction)` to
the corresponding 23.0a parquet, restricted to `valid_label = True`).
Then compute:

| gate | metric | threshold | source |
|---|---|---|---|
| **A0** | `annual_trades = n_trades / span_years` | `>= 70` | 22.0b §4.4.1 |
| **A1** | per-trade Sharpe `mean / std` (ddof=0, **no √N annualisation**) | `>= +0.082` | 22.0b §4.4.1 |
| **A2** | `annual_pnl_pip = sum(pnl) / span_years` | `>= +180` | 22.0b §4.4.1 |
| **A3** | `max_dd_pip` on cumulative pip curve (positive value) | `<= 200` | 22.0b §4.4.1 |
| **A4** | 5-fold chronological split, drop k=0 (warmup), evaluate k=1..4; count Sharpe-positive folds | `>= 3 / 4` | user-spec (relaxed from Phase 22's 4/5; reflects k=0 drop) |
| **A5** | `annual_pnl_pip` after subtracting 0.5 pip from each trade (= `+0.5 pip` spread stress per round trip) | `> 0` | 22.0b §4.4.1 |

`span_years = 730 / 365.25 ≈ 1.9986`.

**Overtrading warning** (Phase 22 22.0b convention): if
`annual_trades > 1000`, emit a warning string in the report; this is
**not blocking** for A0.

**Diagnostic-only metrics** (computed and reported, but never gate-blocking):
- hit rate = `mean(pnl > 0)`
- payoff asymmetry = `|mean(positive_pnl)| / |mean(negative_pnl)|`
- false-breakout rate (long signals where `mid_c` retreats below `upper_N` within 5 M1 bars) — diagnostic per the kickoff §3 H3 hypothesis
- per-pair contribution (Sharpe / annual_pnl per pair, sorted)
- per-session contribution (Tokyo / London / NY by `entry_ts.hour`)

---

## §5 S0 / S1 diagnostics (NOT hard ADOPT gates)

### S0 — random-entry sanity

For each cell, generate a comparison "trade set" of the same size as the
Donchian-triggered set, but with entry timestamps drawn uniformly at
random from the pool of valid M5 signal bars (same pair, same horizon,
same direction-balance) using `seed=42`. Compute Sharpe.

Interpretation: if Donchian-Sharpe and random-entry Sharpe are
indistinguishable, the cell's edge is sample-size luck rather than
Donchian structure. Reported as `s0_random_entry_sharpe`.

This is a **diagnostic** — does NOT block ADOPT_CANDIDATE.

### S1 — strict 80/20 chronological hold-out

After the sweep, identify the **best cell** (max A1 Sharpe among cells
passing A0). On that single cell only:
- Sort pooled trades by `entry_ts`
- IS = first 80% of trades, OOS = last 20% of trades
- Compute Sharpe on each segment
- `s1_oos_is_ratio = oos_sharpe / is_sharpe` (NaN if `is_sharpe <= 0`)

Reported as `s1_strict_oos`. **No re-search of cell parameters** on the
OOS segment — the cell is frozen at the IS best.

This is a **diagnostic** — does NOT block ADOPT_CANDIDATE. It DOES
modulate the verdict between ADOPT_CANDIDATE and PROMISING_BUT_NEEDS_OOS
(see §6).

---

## §6 Verdict (3-class)

Headline verdict per the best cell (max A1 Sharpe among cells passing
A0). The other 17 cells are listed in the report but do not change the
headline.

| verdict | criteria |
|---|---|
| **ADOPT_CANDIDATE** | A0..A5 all pass AND S1 strict OOS is "strong" (`oos_sharpe > 0` and `oos/is_sharpe >= 0.5`). Independent OOS validation (a separate `23.0b-v2` PR analogous to 22.0e-v2) is **mandatory** before any production claim. |
| **PROMISING_BUT_NEEDS_OOS** | A0..A3 pass but A4 OR A5 fails; OR A0..A5 all pass but S1 strict OOS is weak (`oos_sharpe <= 0` or `oos/is_sharpe < 0.5`). 23.0e/e-v2 (meta-labeling + independent OOS) is the path forward. |
| **REJECT** | A1 OR A2 fails; OR A0 fails (trade count insufficient — `annual_trades < 70`). |

**Production-readiness clause (mandatory inclusion in eval_report.md)**:

> Even an ADOPT_CANDIDATE verdict is *not* production-ready. The S1 strict
> OOS is computed *after* the in-sample sweep selected the best cell,
> which is itself a multiple-testing situation across 18 cells × 20 pairs.
> A separate `23.0b-v2` PR (frozen-cell, fresh strict OOS on
> chronologically out-of-sample data, no re-search) is required before
> any production migration.

---

## §7 Walk-forward methodology (A4 implementation)

For a cell's pooled trade list (across 20 pairs, sorted by `entry_ts`):
- Split into 5 chronological quintiles of equal *trade count*
  (NOT equal time): `n_per_fold = round(n_trades / 5)`, last fold
  absorbs the remainder.
- `k = 0` → warmup, dropped from A4.
- `k = 1..4` → evaluation folds.
- Compute per-trade Sharpe per fold (ddof=0).
- A4 passes if `count(fold_sharpe > 0 for k in 1..4) >= 3`.

Folds with fewer than 2 trades are recorded as `NaN` Sharpe and counted
as not-positive for A4.

This mirrors the Phase 22 22.0b `_fold_stability` convention except for
the user-revised 3/4 threshold (Phase 22 used 4/5, which under k=0-drop
becomes "all 4 of 4"; the user has explicitly relaxed this for 23.0b).

---

## §8 Outputs and commit policy

### Committed
- `docs/design/phase23_0b_m5_donchian_baseline.md` (this file)
- `scripts/stage23_0b_m5_donchian_eval.py`
- `tests/unit/test_stage23_0b_m5_donchian.py`
- `artifacts/stage23_0b/eval_report.md` (generated; sweep summary embedded as Markdown tables)
- `artifacts/stage23_0b/run.log`

### NOT committed (regenerable from script + 23.0a labels)
- `artifacts/stage23_0b/sweep_results.parquet` — raw per-cell metrics
  (excluded via `.gitignore`; the same content is summarised inside
  `eval_report.md`)
- per-cell trade lists (transient working data; not written to disk)

---

## §9 Mandatory unit tests (≥ 12 cases)

| # | name | what it verifies |
|---|---|---|
| 1 | `test_donchian_upper_lower_causal_shift1` | `upper_N` at bar `t` = max of mid_h over `[t-N, t-1]`; bar `t` itself excluded. |
| 2 | `test_donchian_uses_mid_high_low_not_bid_or_ask` | `mid_h = (bid_h+ask_h)/2`; signal-side never reads `bid_h` or `ask_h` directly. |
| 3 | `test_long_trigger_strict_above_upper` | `mid_c > upper_N` triggers; `mid_c == upper_N` does not. |
| 4 | `test_short_trigger_strict_below_lower` | mirrored. |
| 5 | `test_no_signal_when_donchian_window_not_filled` | bars 0..N-1 have NaN bands → no triggers emitted. |
| 6 | `test_signal_join_to_23_0a_outcome` | An emitted signal joins to a 23.0a row with finite `tb_pnl`/`time_exit_pnl`. |
| 7 | `test_signal_drops_invalid_rows` | 23.0a rows with `valid_label=False` are excluded. |
| 8 | `test_sharpe_per_trade_ddof0_no_annualize` | `mean(pnl) / pnl.std(ddof=0)`; no √N factor. |
| 9 | `test_a0_annual_trades_uses_dataset_span_2_years` | `annual_trades = n / 1.9986`. |
| 10 | `test_a4_4fold_majority_rule` | synthetic 4 folds with known sign pattern → correct n_positive. |
| 11 | `test_a5_spread_stress_subtracts_half_pip_per_trade` | every pnl reduced by 0.5; annual_pnl recomputed. |
| 12 | `test_no_phase22_m1_cell_reused` | every emitted trade has `signal_timeframe == "M5"` (runtime assertion). |
| 13 | `test_cell_pooling_aggregates_all_pairs` | a cell's trade set covers all 20 pairs (no per-pair filter). |
| 14 | `test_smoke_mode_3pairs_2cells` | `--smoke` reduces to USD_JPY/EUR_USD/GBP_JPY × 2 cells. |
| 15 | `test_verdict_3class_assignment` | synthetic gate matrix yields the documented verdict. |
| 16 | `test_s0_random_entry_sharpe_near_zero` | random-entry Sharpe over a long-mean-zero series is near 0. |
| 17 | `test_s1_strict_oos_split_80_20_chronological` | first 80% / last 20% by `entry_ts`. |
| 18 | `test_overtrading_warning_threshold` | `annual_trades > 1000` triggers warning string but does NOT block A0. |

---

## §10 NG list compliance

| NG | how 23.0b complies |
|---|---|
| 1 | 20-pair canonical universe; no pair filter. |
| 2 | No train-side time filter; all M5 bars eligible. |
| 3 | No test-side filter — strict 80/20 OOS uses chronological split, no cell re-search. |
| 4 | No WeekOpen-aware sample weighting; no week-open-window column read. |
| 5 | No universe-restricted cross-pair feature. |
| 6 | M5 signal_timeframe enforced at runtime; horizon units differ from Phase 22 M1; outcome dataset is 23.0a M5 (not 22.0a M1); `conf` parameter does not exist (rule-based). |
| 7 | n/a (relevant at later stages). |
| 8 | 23.0a M5 outcome dataset is the sole PnL source; Phase 22 M1 dataset is read-only context. |

---

## §11 Effort estimate

| item | hours |
|---|---|
| Donchian signal generator + 23.0a join | 2-3 |
| 8-gate harness (per-cell aggregation + A4 fold split) | 3-4 |
| Sweep runner + S0 random-entry + S1 strict OOS | 2 |
| Tests (≥ 12 cases, target 16-18) | 3-4 |
| Eval report drafting | 1-2 |
| **Total** | **11-15** |

---

## §12 Document role boundary

This file is the stage contract for 23.0b. It does not record per-cell
results (those go into `artifacts/stage23_0b/eval_report.md`) and does
not describe the data construction (that is 23.0a's domain).

If a contradiction arises between this doc and the kickoff doc, the
kickoff wins.
