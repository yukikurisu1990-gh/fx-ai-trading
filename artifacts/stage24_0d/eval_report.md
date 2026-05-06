# Stage 24.0d — Regime-Conditional Exits on Frozen Entry Streams

Generated: 2026-05-06T21:51:06.135932+00:00

Design contract: `docs/design/phase24_0d_regime_conditional.md`

## Mandatory clause

**All frozen entry streams originate from Phase 23.0d REJECT cells. Phase 24.0d tests exit-side capture only; it does not reclassify the entry signal itself as ADOPT. Regime conditioning is applied to exit logic only — regime tags select an exit parameter (trailing K or partial fraction) per trade and never drop or filter entries.** Production-readiness still requires `24.0d-v2` frozen-cell strict OOS.

## Regime is exit-parameter selector ONLY (not entry filter)

Per kickoff §5 24.0d, regime tags select WHICH trailing distance / partial fraction to use per trade. Regime tags MUST NOT be used as entry filters. Phase 22/23 explicitly rejected time-of-day, session, and regime entry filtering; 24.0d MUST NOT revive that route via the back door of 'regime-conditional exits'. Mandatory unit test `test_regime_is_exit_parameter_only_not_entry_filter` verifies entry-stream count is invariant across all regime configurations.

**R2 session note**: `asian` / `london` / `ny` are CONVENTIONAL UTC hour bucket labels for the 3-way `[0,8) / [8,16) / [16,24)` partition. They do NOT correspond to actual market-session boundaries (which vary with daylight saving and pair-specific session semantics). 24.0d does not enforce any market-open semantic — the labels are purely cosmetic for hour-of-day grouping.

## NG#10 strict-rule disclosure (carried from 24.0b/0c)

All exit triggers (TP, SL, partial trigger, MFE running max/min, trailing) are evaluated at M1 bar **close only**. 24.0d reuses `stage24_0b._simulate_atr_long/short` (R1, R3) and `stage24_0c._simulate_p1_long/short` (R2) directly — no re-implementation. The close-only discipline is inherited by reuse.

## NG#11 causal regime-tag disclosure

All regime tags are computed using data available **at signal time** only:
- **R1 ATR regime**: uses `atr_at_entry_signal_tf` from 23.0a labels (already causal — computed via `mid_c.shift(1).rolling(N)` per 23.0a §2.1).
- **R2 session regime**: `entry_ts.hour_utc` is always known at signal generation (trivially causal).
- **R3 trend regime**: `slope_5 = mid_c[t-1] - mid_c[t-5]` uses `mid_c.shift(1)` only — the signal bar's own close is NEVER used.

## Diagnostics disclosure

`realised_capture_ratio` (carried from 24.0b/0c) and `per_regime_breakdown` (NEW for 24.0d) are **diagnostic-only**. `per_regime_breakdown` reports per-bucket sub-statistics (n_trades, sharpe, mean_pnl, hit_rate) within each cell and **must NOT be used to ex-post select a 'best regime' and drop the others** — that would be a regime-as-entry-filter route via the back door. Use for interpretation only.

Universe: 20 pairs (canonical 20). Span = 730d. Cells evaluated: 27 (3 frozen × 9 variants).

## Frozen entry streams (imported from 24.0a)

| rank | source | cell_params | Phase 23 verdict | Phase 23 reject_reason |
|---|---|---|---|---|
| 1 | 23.0d (PR #266, d929867) | N=50, horizon_bars=4, exit_rule=tb | REJECT | still_overtrading |
| 2 | 23.0d (PR #266, d929867) | N=50, horizon_bars=4, exit_rule=time | REJECT | still_overtrading |
| 3 | 23.0d (PR #266, d929867) | N=20, horizon_bars=4, exit_rule=tb | REJECT | still_overtrading |

## Headline verdict

**REJECT**

Per-cell verdict counts: 27 REJECT / 0 PROMISING_BUT_NEEDS_OOS / 0 ADOPT_CANDIDATE — out of 27 cells.

REJECT reason breakdown:
- still_overtrading: 27 cell(s)

**Best cell (max A1 Sharpe among A0-passers):** rank 1 (N=50, h=4, exit_rule=tb) × R1_v2_K_low=1.5_K_high=2.5 → Sharpe -0.1802, annual_pnl -62994.5 pip, capture -0.350

## Per-mode effectiveness + uniform-control comparison

If conditional regime variants outperform their uniform-control siblings (R1_v3, R2_v3, R3_v3), the regime conditioning is capturing exit-side information. If conditional == uniform, the regime tag carries no useful exit-parameter signal.

| mode | best variant | best Sharpe | best ann_pnl | uniform Sharpe | uniform ann_pnl |
|---|---|---|---|---|---|
| R1_atr_regime | R1_v2_K_low=1.5_K_high=2.5 | -0.1802 | -62994.5 | -0.2071 | -64412.8 |
| R2_session_regime | R2_v1_asian=0.25_london=0.50_ny=0.75 | -0.2483 | -59425.1 | -0.2507 | -59352.8 |
| R3_trend_regime | R3_v1_with=2.0_against=1.0 | -0.2010 | -65586.1 | -0.2071 | -64412.8 |

## Sweep summary (all 27 cells, sorted by Sharpe descending)

| rank_cell | variant | n | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | A5 stress | capture | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r1_N=50_h=4_exit=tb | R1_v2_K_low=1.5_K_high=2.5 | 45229 | 22630.0 | -0.1802 | -62994.5 | 125935.5 | 0/4 | -74309.5 | -0.350 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | R1_v2_K_low=1.5_K_high=2.5 | 45229 | 22630.0 | -0.1802 | -62994.5 | 125935.5 | 0/4 | -74309.5 | -0.350 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | R1_v1_K_low=1.0_K_high=2.0 | 45229 | 22630.0 | -0.1924 | -63654.2 | 127241.6 | 0/4 | -74969.2 | -0.354 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | R1_v1_K_low=1.0_K_high=2.0 | 45229 | 22630.0 | -0.1924 | -63654.2 | 127241.6 | 0/4 | -74969.2 | -0.354 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | R1_v2_K_low=1.5_K_high=2.5 | 73510 | 36780.2 | -0.2008 | -108586.0 | 217057.9 | 0/4 | -126976.1 | -0.404 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | R3_v1_with=2.0_against=1.0 | 45229 | 22630.0 | -0.2010 | -65586.1 | 131124.3 | 0/4 | -76901.1 | -0.365 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | R3_v1_with=2.0_against=1.0 | 45229 | 22630.0 | -0.2010 | -65586.1 | 131124.3 | 0/4 | -76901.1 | -0.365 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | R1_v3_uniform_K=1.5 | 45229 | 22630.0 | -0.2071 | -64412.8 | 128770.2 | 0/4 | -75727.8 | -0.358 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | R3_v3_uniform_K=1.5 | 45229 | 22630.0 | -0.2071 | -64412.8 | 128770.2 | 0/4 | -75727.8 | -0.358 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | R1_v3_uniform_K=1.5 | 45229 | 22630.0 | -0.2071 | -64412.8 | 128770.2 | 0/4 | -75727.8 | -0.358 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | R3_v3_uniform_K=1.5 | 45229 | 22630.0 | -0.2071 | -64412.8 | 128770.2 | 0/4 | -75727.8 | -0.358 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | R1_v1_K_low=1.0_K_high=2.0 | 73510 | 36780.2 | -0.2141 | -109679.7 | 219236.8 | 0/4 | -128069.8 | -0.408 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | R3_v1_with=2.0_against=1.0 | 73510 | 36780.2 | -0.2226 | -112805.6 | 225504.2 | 0/4 | -131195.6 | -0.420 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | R1_v3_uniform_K=1.5 | 73510 | 36780.2 | -0.2275 | -110713.4 | 221309.9 | 0/4 | -129103.5 | -0.412 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | R3_v3_uniform_K=1.5 | 73510 | 36780.2 | -0.2275 | -110713.4 | 221309.9 | 0/4 | -129103.5 | -0.412 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | R3_v2_with=1.0_against=2.0 | 45229 | 22630.0 | -0.2280 | -64275.0 | 128470.6 | 0/4 | -75590.0 | -0.358 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | R3_v2_with=1.0_against=2.0 | 45229 | 22630.0 | -0.2280 | -64275.0 | 128470.6 | 0/4 | -75590.0 | -0.358 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | R3_v2_with=1.0_against=2.0 | 73510 | 36780.2 | -0.2470 | -109645.3 | 219156.4 | 0/4 | -128035.4 | -0.408 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | R2_v1_asian=0.25_london=0.50_ny=0.75 | 45229 | 22630.0 | -0.2483 | -59425.1 | 118773.7 | 0/4 | -70740.1 | -0.331 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | R2_v1_asian=0.25_london=0.50_ny=0.75 | 45229 | 22630.0 | -0.2483 | -59425.1 | 118773.7 | 0/4 | -70740.1 | -0.331 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | R2_v2_asian=0.75_london=0.50_ny=0.25 | 45229 | 22630.0 | -0.2503 | -59280.4 | 118484.5 | 0/4 | -70595.4 | -0.330 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | R2_v2_asian=0.75_london=0.50_ny=0.25 | 45229 | 22630.0 | -0.2503 | -59280.4 | 118484.5 | 0/4 | -70595.4 | -0.330 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | R2_v3_uniform_frac=0.50 | 45229 | 22630.0 | -0.2507 | -59352.8 | 118629.1 | 0/4 | -70667.8 | -0.330 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | R2_v3_uniform_frac=0.50 | 45229 | 22630.0 | -0.2507 | -59352.8 | 118629.1 | 0/4 | -70667.8 | -0.330 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | R2_v1_asian=0.25_london=0.50_ny=0.75 | 73510 | 36780.2 | -0.2721 | -102176.0 | 204225.1 | 0/4 | -120566.1 | -0.380 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | R2_v3_uniform_frac=0.50 | 73510 | 36780.2 | -0.2752 | -102158.3 | 204189.7 | 0/4 | -120548.4 | -0.380 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | R2_v2_asian=0.75_london=0.50_ny=0.25 | 73510 | 36780.2 | -0.2753 | -102140.6 | 204154.3 | 0/4 | -120530.7 | -0.380 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |

## Best cell — per-regime breakdown (diagnostic only)

| regime bucket | n_trades | Sharpe | mean_pnl | hit_rate |
|---|---|---|---|---|
| high_vol | 23741 | -0.1542 | -3.1023 | 0.3966 |
| low_vol | 21488 | -0.3285 | -2.4316 | 0.3057 |

(`per_regime_breakdown` is diagnostic-only; not used for any ADOPT decision or trade filtering.)

## Phase 24 routing post-24.0d

Best cell verdict is **REJECT**. Combined with 24.0b and 24.0c REJECTs, **24.0e (exit meta-labeling) is NOT triggered** per kickoff §5 (no 24.0b/c/d cell ADOPT/PROMISING). Phase 24 closes with 24.0f final synthesis (path A analogous to Phase 23): exit-side improvements under NG#10 strict close-only and non-forward-looking regime conditioning are insufficient to convert the 24.0a-validated path-EV into realised PnL clearing the 8-gate harness.
