# Stage 24.0b — Trailing-Stop Variants on Frozen Entry Streams

Generated: 2026-05-06T19:04:38.000295+00:00

Design contract: `docs/design/phase24_0b_trailing_stop.md`

## Mandatory clause

**All frozen entry streams originate from Phase 23.0d REJECT cells. Phase 24.0b tests exit-side capture only; it does not reclassify the entry signal itself as ADOPT.** A 24.0b ADOPT_CANDIDATE verdict means "for this entry stream that Phase 23 rejected, this trailing-stop variant converts enough of the path-EV (per 24.0a) into realised PnL to clear the gates" — NOT "this entry signal is now adopted". Production-readiness still requires `24.0b-v2` frozen-cell strict OOS.

## NG#10 strict-rule disclosure

All trailing decisions in this stage are computed at M1 bar **close only**. Running max/min, exit conditions, TP/SL, and breakeven shifts all use `bid_close` (long) or `ask_close` (short) — intra-bar high/low are NOT used. This is conservatively pessimistic vs intra-bar variants. If 24.0b results motivate testing intra-bar variants, that work goes into a follow-up `24.0b-rev1` PR — Phase 24's core verdict closes on the strict-close basis.

## realised_capture_ratio diagnostic disclosure

`realised_capture_ratio = mean(realised_pnl) / mean(best_possible_pnl)` is the **fraction of path-EV captured by the trailing logic**. It is **diagnostic-only** — `best_possible_pnl` is an ex-post path peak (after entry-side spread), not an executable PnL, so capture ratio is NOT a production efficiency metric. Use for cross-variant comparison only.

Universe: 20 pairs (canonical 20). Span = 730d. Cells evaluated: 33 (3 frozen × 11 variants).

## Frozen entry streams (imported from 24.0a)

| rank | source | cell_params | Phase 23 verdict | Phase 23 reject_reason |
|---|---|---|---|---|
| 1 | 23.0d (PR #266, d929867) | N=50, horizon_bars=4, exit_rule=tb | REJECT | still_overtrading |
| 2 | 23.0d (PR #266, d929867) | N=50, horizon_bars=4, exit_rule=time | REJECT | still_overtrading |
| 3 | 23.0d (PR #266, d929867) | N=20, horizon_bars=4, exit_rule=tb | REJECT | still_overtrading |

## Headline verdict

**REJECT**

Per-cell verdict counts: 33 REJECT / 0 PROMISING_BUT_NEEDS_OOS / 0 ADOPT_CANDIDATE — out of 33 cells.

REJECT reason breakdown:
- still_overtrading: 33 cell(s)

**Best cell (max A1 Sharpe among A0-passers):** rank 1 (N=50, h=4, exit_rule=tb) × T1_ATR_K=2.5 → Sharpe -0.1773, annual_pnl -62937.0 pip, capture -0.350

## Per-mode effectiveness (best cell per mode)

| mode | best variant | best Sharpe | best ann_pnl | best capture |
|---|---|---|---|---|
| T1_ATR | T1_ATR_K=2.5 | -0.1773 | -62937.0 | -0.350 |
| T2_fixed_pip | T2_fixed_pip_30 | -0.1882 | -62205.9 | -0.346 |
| T3_breakeven | T3_breakeven_BE=1.5 | -0.2290 | -60251.5 | -0.335 |

## Sweep summary (all 33 cells, sorted by Sharpe descending)

| rank_cell | variant | n | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | A5 stress | capture | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r1_N=50_h=4_exit=tb | T1_ATR_K=2.5 | 45229 | 22630.0 | -0.1773 | -62937.0 | 125829.6 | 0/4 | -74252.0 | -0.350 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | T1_ATR_K=2.5 | 45229 | 22630.0 | -0.1773 | -62937.0 | 125829.6 | 0/4 | -74252.0 | -0.350 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | T1_ATR_K=2.0 | 45229 | 22630.0 | -0.1881 | -64027.8 | 128009.7 | 0/4 | -75342.8 | -0.356 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | T1_ATR_K=2.0 | 45229 | 22630.0 | -0.1881 | -64027.8 | 128009.7 | 0/4 | -75342.8 | -0.356 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | T2_fixed_pip_30 | 45229 | 22630.0 | -0.1882 | -62205.9 | 124368.4 | 0/4 | -73520.9 | -0.346 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | T2_fixed_pip_30 | 45229 | 22630.0 | -0.1882 | -62205.9 | 124368.4 | 0/4 | -73520.9 | -0.346 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | T1_ATR_K=2.5 | 73510 | 36780.2 | -0.1970 | -108438.8 | 216776.7 | 0/4 | -126828.9 | -0.403 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | T2_fixed_pip_30 | 73510 | 36780.2 | -0.2015 | -105000.5 | 209904.8 | 0/4 | -123390.6 | -0.391 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | T1_ATR_K=1.5 | 45229 | 22630.0 | -0.2071 | -64412.8 | 128770.2 | 0/4 | -75727.8 | -0.358 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | T1_ATR_K=1.5 | 45229 | 22630.0 | -0.2071 | -64412.8 | 128770.2 | 0/4 | -75727.8 | -0.358 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | T1_ATR_K=2.0 | 73510 | 36780.2 | -0.2082 | -110225.6 | 220347.9 | 0/4 | -128615.7 | -0.410 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | T2_fixed_pip_20 | 45229 | 22630.0 | -0.2085 | -63432.7 | 126820.3 | 0/4 | -74747.7 | -0.353 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | T2_fixed_pip_20 | 45229 | 22630.0 | -0.2085 | -63432.7 | 126820.3 | 0/4 | -74747.7 | -0.353 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | T2_fixed_pip_20 | 73510 | 36780.2 | -0.2231 | -107395.4 | 214691.2 | 0/4 | -125785.4 | -0.399 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | T1_ATR_K=1.5 | 73510 | 36780.2 | -0.2275 | -110713.4 | 221309.9 | 0/4 | -129103.5 | -0.412 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | T3_breakeven_BE=1.5 | 45229 | 22630.0 | -0.2290 | -60251.5 | 120429.4 | 0/4 | -71566.5 | -0.335 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | T3_breakeven_BE=2.0 | 45229 | 22630.0 | -0.2290 | -60251.5 | 120429.4 | 0/4 | -71566.5 | -0.335 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | T3_breakeven_BE=1.5 | 45229 | 22630.0 | -0.2290 | -60251.5 | 120429.4 | 0/4 | -71566.5 | -0.335 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | T3_breakeven_BE=2.0 | 45229 | 22630.0 | -0.2290 | -60251.5 | 120429.4 | 0/4 | -71566.5 | -0.335 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | T3_breakeven_BE=1.0 | 45229 | 22630.0 | -0.2350 | -60464.6 | 120843.6 | 0/4 | -71779.6 | -0.336 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | T3_breakeven_BE=1.0 | 45229 | 22630.0 | -0.2350 | -60464.6 | 120843.6 | 0/4 | -71779.6 | -0.336 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | T1_ATR_K=1.0 | 45229 | 22630.0 | -0.2488 | -65833.4 | 131585.2 | 0/4 | -77148.4 | -0.366 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | T1_ATR_K=1.0 | 45229 | 22630.0 | -0.2488 | -65833.4 | 131585.2 | 0/4 | -77148.4 | -0.366 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | T3_breakeven_BE=1.5 | 73510 | 36780.2 | -0.2533 | -103944.5 | 207765.3 | 0/4 | -122334.6 | -0.387 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | T3_breakeven_BE=2.0 | 73510 | 36780.2 | -0.2533 | -103944.5 | 207765.3 | 0/4 | -122334.6 | -0.387 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | T3_breakeven_BE=1.0 | 73510 | 36780.2 | -0.2589 | -104109.7 | 208083.7 | 0/4 | -122499.7 | -0.387 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | T2_fixed_pip_10 | 45229 | 22630.0 | -0.2684 | -64897.9 | 129739.8 | 0/4 | -76212.9 | -0.361 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | T2_fixed_pip_10 | 45229 | 22630.0 | -0.2684 | -64897.9 | 129739.8 | 0/4 | -76212.9 | -0.361 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | T1_ATR_K=1.0 | 73510 | 36780.2 | -0.2692 | -112225.2 | 224312.7 | 0/4 | -130615.3 | -0.417 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | T2_fixed_pip_10 | 73510 | 36780.2 | -0.2894 | -111815.0 | 223515.4 | 0/4 | -130205.1 | -0.416 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r1_N=50_h=4_exit=tb | T2_fixed_pip_5 | 45229 | 22630.0 | -0.3551 | -62839.4 | 125605.0 | 0/4 | -74154.4 | -0.350 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r2_N=50_h=4_exit=time | T2_fixed_pip_5 | 45229 | 22630.0 | -0.3551 | -62839.4 | 125605.0 | 0/4 | -74154.4 | -0.350 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |
| r3_N=20_h=4_exit=tb | T2_fixed_pip_5 | 73510 | 36780.2 | -0.3810 | -108477.0 | 216818.7 | 0/4 | -126867.1 | -0.403 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | still_overtrading |

## Phase 24 routing post-24.0b

Best cell verdict is **REJECT**. 24.0b's REJECT does NOT halt Phase 24 — 24.0c and 24.0d continue independently. The trailing-stop search space tested here (3 modes × 11 variants under NG#10 strict close-only) was insufficient to convert the 24.0a-validated path-EV into realised PnL clearing the 8-gate harness.
