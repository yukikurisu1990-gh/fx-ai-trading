# Stage 23.0b — M5 Donchian Breakout + M1 Execution Eval

Generated: 2026-05-05T20:18:49.996606+00:00

Design contract: `docs/design/phase23_0b_m5_donchian_baseline.md`

Universe: 20 pairs, signal TF = `M5`, span = 730d
Sweep: N (10, 20, 50) × horizon (1, 2, 3) × exit ('tb', 'time') = 18 cells

## Headline verdict

**REJECT**

Best cell: `N=50, horizon=3, exit=time` (Sharpe -0.3182, annual_pnl -291015.2 pip, n_trades 210406)

## Production-readiness

Even an `ADOPT_CANDIDATE` verdict is **not** production-ready. The S1 strict OOS is computed *after* the in-sample sweep selected the best cell across 18 cells × 20 pairs (multiple-testing surface). A separate `23.0b-v2` PR with frozen-cell strict OOS validation on chronologically out-of-sample data and no parameter re-search is required before any production migration.

## Gate thresholds (Phase 22 inherited)

- A0: annual_trades >= 70.0 (overtrading warning if > 1000.0, NOT blocking)
- A1: per-trade Sharpe (ddof=0, no √N) >= +0.082
- A2: annual_pnl_pip >= +180.0
- A3: max_dd_pip <= 200.0
- A4: 5-fold chronological, drop k=0, eval k=1..4, count(Sharpe > 0) >= 3/4
- A5: annual_pnl after subtracting 0.5 pip per round trip > 0

## Sweep summary (all 18 cells)

| N | h | exit | n_trades | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | A5 stress | A0 | A1 | A2 | A3 | A4 | A5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 50 | 3 | time | 210406 | 105275.1 | -0.3182 | -291015.2 | 581661.9 | 0/4 | -343652.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 20 | 3 | time | 346179 | 173208.1 | -0.3387 | -485262.4 | 969859.9 | 0/4 | -571866.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 10 | 3 | time | 498663 | 249502.3 | -0.3495 | -692651.6 | 1384350.6 | 0/4 | -817402.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 50 | 2 | time | 210407 | 105275.6 | -0.3709 | -286954.2 | 573570.2 | 0/4 | -339591.9 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 20 | 2 | time | 346181 | 173209.1 | -0.3962 | -477414.2 | 954182.4 | 0/4 | -564018.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 10 | 2 | time | 498666 | 249503.8 | -0.4096 | -685193.2 | 1369449.5 | 0/4 | -809945.1 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 50 | 3 | tb | 210406 | 105275.1 | -0.4246 | -249600.4 | 498856.5 | 0/4 | -302238.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 20 | 3 | tb | 346179 | 173208.1 | -0.4521 | -407018.7 | 813478.6 | 0/4 | -493622.7 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 50 | 2 | tb | 210407 | 105275.6 | -0.4624 | -247540.2 | 494749.7 | 0/4 | -300178.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 10 | 3 | tb | 498663 | 249502.3 | -0.4649 | -584913.1 | 1169017.3 | 0/4 | -709664.2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 50 | 1 | time | 210410 | 105277.1 | -0.4668 | -279300.5 | 558224.4 | 0/4 | -331939.0 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 20 | 2 | tb | 346181 | 173209.1 | -0.4945 | -404129.0 | 807712.2 | 0/4 | -490733.5 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 20 | 1 | time | 346187 | 173212.1 | -0.5002 | -465284.3 | 929935.3 | 0/4 | -551890.3 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 10 | 2 | tb | 498666 | 249503.8 | -0.5120 | -581984.5 | 1163171.7 | 0/4 | -706736.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 10 | 1 | time | 498673 | 249507.3 | -0.5183 | -670417.9 | 1339916.1 | 0/4 | -795171.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 50 | 1 | tb | 210410 | 105277.1 | -0.5529 | -244641.9 | 488954.6 | 0/4 | -297280.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 20 | 1 | tb | 346187 | 173212.1 | -0.5953 | -399890.5 | 799237.3 | 0/4 | -486496.6 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 10 | 1 | tb | 498673 | 249507.3 | -0.6210 | -576437.8 | 1152084.5 | 0/4 | -701191.4 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

## Best cell deep-dive

- N = 50, horizon = 3, exit = time
- n_trades = 210406 (long 109730 / short 100676)
- annual_trades = 105275.1 — **OVERTRADING WARNING** (> 1000.0)
- Sharpe = -0.3182
- annual_pnl = -291015.2 pip
- max_dd = 581661.9 pip
- A4 fold Sharpes (k=1..4): -0.3000, -0.3008, -0.3720, -0.3859
- A5 stressed annual_pnl = -343652.7 pip

### Diagnostics (NOT gates)

- hit_rate = 0.2871
- payoff_asymmetry = 0.8762
- S0 random-entry Sharpe = -0.3694
- S1 strict 80/20 OOS: IS Sharpe -0.3034 (n=168325), OOS Sharpe -0.3859 (n=42081), oos/is ratio +nan

### Per-pair contribution

| pair | n_trades | Sharpe | annual_pnl | hit_rate |
|---|---|---|---|---|
| USD_JPY | 11209 | -0.1711 | -11085.8 | 0.3755 |
| EUR_JPY | 10462 | -0.2382 | -15137.3 | 0.3540 |
| GBP_JPY | 10625 | -0.2643 | -21405.7 | 0.3392 |
| AUD_JPY | 10863 | -0.2690 | -13800.8 | 0.3259 |
| GBP_USD | 10881 | -0.3029 | -11979.2 | 0.3094 |
| EUR_USD | 11006 | -0.3044 | -10660.0 | 0.2977 |
| AUD_USD | 10943 | -0.3089 | -8313.4 | 0.3158 |
| USD_CHF | 10855 | -0.3317 | -9842.8 | 0.2902 |
| USD_CAD | 11296 | -0.3422 | -11367.8 | 0.2969 |
| EUR_AUD | 10349 | -0.3475 | -20050.4 | 0.2908 |
| NZD_USD | 11291 | -0.3608 | -9063.7 | 0.2935 |
| NZD_JPY | 10887 | -0.3951 | -17037.2 | 0.2741 |
| EUR_CAD | 10119 | -0.3980 | -15805.8 | 0.2681 |
| CHF_JPY | 10487 | -0.4033 | -24465.8 | 0.2864 |
| GBP_AUD | 10150 | -0.4266 | -26640.6 | 0.2781 |
| GBP_CHF | 9843 | -0.4394 | -15221.2 | 0.2527 |
| EUR_CHF | 9912 | -0.4412 | -10427.2 | 0.2419 |
| AUD_CAD | 10121 | -0.4859 | -14481.2 | 0.2308 |
| EUR_GBP | 9455 | -0.4890 | -8132.2 | 0.2292 |
| AUD_NZD | 9652 | -0.6442 | -16097.1 | 0.1578 |

### Per-session contribution

| session | n_trades | Sharpe | annual_pnl | hit_rate |
|---|---|---|---|---|
| American (12-18 UTC) | 57377 | -0.2695 | -73473.8 | 0.3288 |
| Asian (00-06 UTC) | 54884 | -0.3323 | -66192.9 | 0.2673 |
| European (06-12 UTC) | 63992 | -0.2904 | -75587.2 | 0.3052 |
| Late (18-24 UTC) | 34153 | -0.4399 | -75761.3 | 0.2153 |
