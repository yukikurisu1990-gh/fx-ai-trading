# Stage 24.0c — Partial-Exit Variants on Frozen Entry Streams

Generated: 2026-05-06T19:37:45.325179+00:00

Design contract: `docs/design/phase24_0c_partial_exit.md`

## Mandatory clause

**All frozen entry streams originate from Phase 23.0d REJECT cells. Phase 24.0c tests exit-side capture only; it does not reclassify the entry signal itself as ADOPT.** A 24.0c ADOPT_CANDIDATE verdict means "for this entry stream that Phase 23 rejected, this partial-exit variant captures enough of the path-EV (per 24.0a) into realised PnL to clear the gates" — NOT "this entry signal is now adopted". Production-readiness still requires `24.0c-v2` frozen-cell strict OOS.

## NG#10 strict-rule disclosure

All triggers (TP, SL, partial trigger, MFE running max/min) are evaluated at M1 bar **close only**. Long uses `bid_close`, short uses `ask_close`. Intra-bar high/low are NOT used. **Per-bar priority**: at any M1 bar where both full TP/SL and partial trigger conditions are satisfied, full TP/SL takes priority and the partial trigger does NOT fire on that bar. Mandatory unit tests verify this priority for P1, P2, and P3.

## Diagnostics disclosure

`realised_capture_ratio = mean(realised_pnl) / mean(best_possible_pnl)` and `partial_hit_rate = count(partial_done=True) / total_trades` are **diagnostic-only**. `best_possible_pnl` is an ex-post path peak (after entry-side spread), not an executable PnL — capture ratio is NOT a production efficiency metric. `partial_hit_rate` reports how often the partial trigger fired across the trade population; useful to interpret per-mode behaviour but not a gate.

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

**Best cell (max A1 Sharpe among A0-passers):** rank 1 (N=50, h=4, exit_rule=tb) × P3_mfe_K=1.5_frac=0.5 → Sharpe -0.2290, annual_pnl -60251.5 pip, capture -0.335, partial_hit_rate 0.000

## Per-mode effectiveness (best cell per mode)

| mode | best variant | best Sharpe | best ann_pnl | capture | partial_hit_rate |
|---|---|---|---|---|---|
| P1_tp_half | P1_tp_half_frac=0.25 | -0.2412 | -59802.2 | -0.333 | 0.300 |
| P2_time_midpoint | P2_midpoint_frac=0.25 | -0.2422 | -60014.0 | -0.334 | 0.474 |
| P3_mfe | P3_mfe_K=1.5_frac=0.5 | -0.2290 | -60251.5 | -0.335 | 0.000 |

## Sweep summary (all 27 cells, sorted by Sharpe descending)

| rank_cell | variant | n | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | A5 stress | capture | phr | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r1_N=50_h=4_exit=tb | P3_mfe_K=1.5_frac=0.5 | 45229 | 22630.0 | -0.2290 | -60251.5 | 120429.4 | 0/4 | -71566.5 | -0.335 | 0.000 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | P3_mfe_K=2.0_frac=0.5 | 45229 | 22630.0 | -0.2290 | -60251.5 | 120429.4 | 0/4 | -71566.5 | -0.335 | 0.000 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | P3_mfe_K=1.5_frac=0.5 | 45229 | 22630.0 | -0.2290 | -60251.5 | 120429.4 | 0/4 | -71566.5 | -0.335 | 0.000 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | P3_mfe_K=2.0_frac=0.5 | 45229 | 22630.0 | -0.2290 | -60251.5 | 120429.4 | 0/4 | -71566.5 | -0.335 | 0.000 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | P3_mfe_K=1.0_frac=0.5 | 45229 | 22630.0 | -0.2410 | -59791.9 | 119507.4 | 0/4 | -71106.9 | -0.333 | 0.226 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | P3_mfe_K=1.0_frac=0.5 | 45229 | 22630.0 | -0.2410 | -59791.9 | 119507.4 | 0/4 | -71106.9 | -0.333 | 0.226 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | P1_tp_half_frac=0.25 | 45229 | 22630.0 | -0.2412 | -59802.2 | 119529.3 | 0/4 | -71117.2 | -0.333 | 0.300 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | P1_tp_half_frac=0.25 | 45229 | 22630.0 | -0.2412 | -59802.2 | 119529.3 | 0/4 | -71117.2 | -0.333 | 0.300 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | P2_midpoint_frac=0.25 | 45229 | 22630.0 | -0.2422 | -60014.0 | 119949.7 | 0/4 | -71329.0 | -0.334 | 0.474 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | P2_midpoint_frac=0.25 | 45229 | 22630.0 | -0.2422 | -60014.0 | 119949.7 | 0/4 | -71329.0 | -0.334 | 0.474 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | P1_tp_half_frac=0.5 | 45229 | 22630.0 | -0.2507 | -59352.8 | 118629.1 | 0/4 | -70667.8 | -0.330 | 0.300 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | P1_tp_half_frac=0.5 | 45229 | 22630.0 | -0.2507 | -59352.8 | 118629.1 | 0/4 | -70667.8 | -0.330 | 0.300 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | P2_midpoint_frac=0.5 | 45229 | 22630.0 | -0.2529 | -59776.4 | 119470.0 | 0/4 | -71091.4 | -0.333 | 0.474 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | P2_midpoint_frac=0.5 | 45229 | 22630.0 | -0.2529 | -59776.4 | 119470.0 | 0/4 | -71091.4 | -0.333 | 0.474 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | P3_mfe_K=1.5_frac=0.5 | 73510 | 36780.2 | -0.2533 | -103944.5 | 207765.3 | 0/4 | -122334.6 | -0.387 | 0.000 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | P3_mfe_K=2.0_frac=0.5 | 73510 | 36780.2 | -0.2533 | -103944.5 | 207765.3 | 0/4 | -122334.6 | -0.387 | 0.000 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | P1_tp_half_frac=0.75 | 45229 | 22630.0 | -0.2558 | -58903.4 | 117729.0 | 0/4 | -70218.4 | -0.328 | 0.300 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | P1_tp_half_frac=0.75 | 45229 | 22630.0 | -0.2558 | -58903.4 | 117729.0 | 0/4 | -70218.4 | -0.328 | 0.300 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | P2_midpoint_frac=0.75 | 45229 | 22630.0 | -0.2597 | -59538.9 | 118992.3 | 0/4 | -70853.8 | -0.331 | 0.474 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | P2_midpoint_frac=0.75 | 45229 | 22630.0 | -0.2597 | -59538.9 | 118992.3 | 0/4 | -70853.8 | -0.331 | 0.474 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | P3_mfe_K=1.0_frac=0.5 | 73510 | 36780.2 | -0.2650 | -102841.2 | 205555.8 | 0/4 | -121231.3 | -0.383 | 0.218 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | P1_tp_half_frac=0.25 | 73510 | 36780.2 | -0.2658 | -103051.4 | 205977.5 | 0/4 | -121441.5 | -0.383 | 0.289 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | P2_midpoint_frac=0.25 | 73510 | 36780.2 | -0.2689 | -103648.6 | 207168.5 | 0/4 | -122038.7 | -0.386 | 0.460 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | P1_tp_half_frac=0.5 | 73510 | 36780.2 | -0.2752 | -102158.3 | 204189.7 | 0/4 | -120548.4 | -0.380 | 0.289 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | P1_tp_half_frac=0.75 | 73510 | 36780.2 | -0.2799 | -101265.2 | 202401.8 | 0/4 | -119655.3 | -0.377 | 0.289 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | P2_midpoint_frac=0.5 | 73510 | 36780.2 | -0.2818 | -103352.7 | 206571.7 | 0/4 | -121742.8 | -0.384 | 0.460 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | P2_midpoint_frac=0.75 | 73510 | 36780.2 | -0.2900 | -103056.8 | 205976.9 | 0/4 | -121446.8 | -0.383 | 0.460 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |

## Phase 24 routing post-24.0c

Best cell verdict is **REJECT**. 24.0c's REJECT does NOT halt Phase 24 — 24.0d continues independently. The partial-exit search space tested here (3 modes × 9 variants under NG#10 strict close-only) was insufficient to convert the 24.0a-validated path-EV into realised PnL clearing the 8-gate harness.
