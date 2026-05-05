# Stage 22.0c M5 Donchian Breakout + M1 Entry Hybrid — Evaluation Report

Generated: 2026-05-05T15:26:03.789032+00:00

Design contract: `docs/design/phase22_0c_m5_breakout_m1_entry_hybrid.md`.

> ⚠ **Multiple testing caveat**: 144 cells were searched. The reported best
> cell's Sharpe / PnL are *in-sample search results*. Production migration
> of any ADOPT-classified cell requires independent OOS validation
> (held-out future time slice, paper-run, or fresh data fetch). The
> ADOPT classification here means "passes all 6 in-sample gates" — not
> "production-ready".

## Pair coverage

- Active pairs: 20 / 20 canonical (missing: none)

## Verdict: **REJECT**

- Best realistic-exit cell: N=100, timing=retest, horizon=40, exit=time_exit_pnl
- annual_trades=26211 (A0 ≥ 70: PASS)
- Sharpe=-0.1751 (A1 ≥ 0.082: FAIL)
- annual_pnl=-62719.9 pip (A2 ≥ 180: FAIL)
- MaxDD=127643.7 pip (A3 ≤ 200: FAIL)
- fold pos/neg=0/5 (A4 ≥ 4/1: FAIL)
- annual_pnl @ +0.5 pip stress=-75825.4 (A5 > 0: FAIL)

**Gates that failed**:
- A1: sharpe -0.1751 < 0.082

⚠ Overtrading warning: annual_trades = 26211 > 1000.

## Top-10 cells (realistic exit_rule, by Sharpe)

| rank | N | timing | h | exit | n/yr | PnL/yr | Sharpe | MaxDD | DD%PnL | fold ± | +0.5 stress |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 100 | retest | 40 | time_exit_pnl | 26211 | -62719.9 | -0.1751 | 127643.7 | 203.5% | 0/5 | -75825.4 |
| 2 | 50 | retest | 40 | time_exit_pnl | 37278 | -88643.3 | -0.1772 | 179594.2 | 202.6% | 0/5 | -107282.1 |
| 3 | 20 | retest | 40 | time_exit_pnl | 59266 | -140739.3 | -0.1825 | 283356.1 | 201.3% | 0/5 | -170372.3 |
| 4 | 10 | retest | 40 | time_exit_pnl | 83991 | -199491.9 | -0.1851 | 400948.7 | 201.0% | 0/5 | -241487.6 |
| 5 | 100 | immediate | 40 | time_exit_pnl | 73035 | -194333.3 | -0.1983 | 391094.9 | 201.2% | 0/5 | -230850.8 |
| 6 | 100 | momentum | 40 | time_exit_pnl | 72637 | -193709.8 | -0.1994 | 389752.3 | 201.2% | 0/5 | -230028.1 |
| 7 | 50 | immediate | 40 | time_exit_pnl | 105504 | -291977.7 | -0.2137 | 586083.5 | 200.7% | 0/5 | -344729.5 |
| 8 | 50 | momentum | 40 | time_exit_pnl | 105034 | -292130.9 | -0.2155 | 586285.6 | 200.7% | 0/5 | -344648.1 |
| 9 | 20 | immediate | 40 | time_exit_pnl | 173392 | -482766.6 | -0.2243 | 967256.3 | 200.4% | 0/5 | -569462.4 |
| 10 | 20 | momentum | 40 | time_exit_pnl | 172792 | -484269.4 | -0.2263 | 970161.2 | 200.3% | 0/5 | -570665.3 |

## Top-10 per-fold PnL (pip)

| rank | f1 | f2 | f3 | f4 | f5 | CV | top concentration |
|---|---|---|---|---|---|---|---|
| 1 | -25898.0 | -23913.4 | -28889.8 | -24833.6 | -21819.2 | 0.09 | 23.0% |
| 2 | -33841.9 | -34949.7 | -41469.6 | -34734.4 | -32169.7 | 0.09 | 23.4% |
| 3 | -53383.8 | -58246.3 | -64710.2 | -54894.9 | -50050.7 | 0.09 | 23.0% |
| 4 | -72007.0 | -82815.3 | -95526.2 | -75953.6 | -72408.6 | 0.11 | 24.0% |
| 5 | -73974.1 | -65384.9 | -87386.3 | -79820.7 | -81834.5 | 0.10 | 22.5% |
| 6 | -73324.6 | -65428.8 | -87365.3 | -79855.0 | -81180.7 | 0.10 | 22.6% |
| 7 | -105271.7 | -103548.7 | -129861.1 | -120781.8 | -124092.3 | 0.09 | 22.3% |
| 8 | -104917.6 | -103928.7 | -130233.3 | -120987.6 | -123794.7 | 0.09 | 22.3% |
| 9 | -172739.3 | -179812.6 | -209829.9 | -202952.1 | -199538.4 | 0.07 | 21.7% |
| 10 | -172479.3 | -180850.3 | -211267.4 | -203553.3 | -199725.6 | 0.08 | 21.8% |

## Top-10 spread stress sensitivity (annual PnL, pip)

| rank | base | +0.2 | +0.5 |
|---|---|---|---|
| 1 | -62719.9 | -67962.1 | -75825.4 |
| 2 | -88643.3 | -96098.8 | -107282.1 |
| 3 | -140739.3 | -152592.5 | -170372.3 |
| 4 | -199491.9 | -216290.2 | -241487.6 |
| 5 | -194333.3 | -208940.3 | -230850.8 |
| 6 | -193709.8 | -208237.1 | -230028.1 |
| 7 | -291977.7 | -313078.4 | -344729.5 |
| 8 | -292130.9 | -313137.8 | -344648.1 |
| 9 | -482766.6 | -517444.9 | -569462.4 |
| 10 | -484269.4 | -518827.7 | -570665.3 |

## Failure-mode diagnostic — best_possible vs realistic

Per (N, timing, horizon), compare `best_possible_pnl` (post-hoc path peak) with `tb_pnl` and `time_exit_pnl`. Large gap = path EV exists but exit destroys it; small gap = no path EV to capture.

| N | timing | h | best/yr | tb/yr | time_exit/yr | best - tb | best - time_exit |
|---|---|---|---|---|---|---|---|
| 100 | retest | 40 | 174009.6 | -49596.5 | -62719.9 | +223606.1 | +236729.5 |
| 50 | retest | 40 | 239547.1 | -69900.7 | -88643.3 | +309447.8 | +328190.4 |
| 20 | retest | 40 | 358127.4 | -108904.3 | -140739.3 | +467031.7 | +498866.7 |
| 10 | retest | 40 | 491311.7 | -152336.0 | -199491.9 | +643647.6 | +690803.5 |
| 100 | immediate | 40 | 435153.1 | -133530.5 | -194333.3 | +568683.6 | +629486.3 |
| 100 | momentum | 40 | 430054.0 | -132524.5 | -193709.8 | +562578.6 | +623763.8 |
| 50 | immediate | 40 | 582599.4 | -190142.9 | -291977.7 | +772742.3 | +874577.1 |
| 50 | momentum | 40 | 575277.2 | -189083.6 | -292130.9 | +764360.8 | +867408.1 |
| 20 | immediate | 40 | 863578.6 | -300741.2 | -482766.6 | +1164319.7 | +1346345.2 |
| 20 | momentum | 40 | 852667.7 | -299456.7 | -484269.4 | +1152124.5 | +1336937.1 |

## Entry-timing comparison (top cell context)

Holding N=100, horizon=40, exit=time_exit_pnl fixed; varying entry_timing:

| timing | n/yr | mean_pnl | win_rate | Sharpe | MaxDD | annual_pnl |
|---|---|---|---|---|---|---|
| immediate | 73035 | -2.661 | 0.354 | -0.1983 | 391094.9 | -194333.3 |
| retest | 26211 | -2.393 | 0.379 | -0.1751 | 127643.7 | -62719.9 |
| momentum | 72637 | -2.667 | 0.353 | -0.1994 | 389752.3 | -193709.8 |

## Skipped-trade rate and time-to-fire histogram

Per (N, timing, direction):

| N | timing | dir | n_signals | n_fired | skipped_rate | bars_to_fire 1 / 2 / 3 / 4 / 5 |
|---|---|---|---|---|---|---|
| 10 | immediate | long | 259157 | 259156 | 0.000 | 259156 / 0 / 0 / 0 / 0 |
| 10 | immediate | short | 246093 | 246091 | 0.000 | 246091 / 0 / 0 / 0 / 0 |
| 10 | momentum | long | 259157 | 257836 | 0.005 | 256306 / 654 / 318 / 250 / 308 |
| 10 | momentum | short | 246093 | 244856 | 0.005 | 243258 / 675 / 335 / 273 / 315 |
| 10 | retest | long | 259157 | 86397 | 0.667 | 24499 / 21024 / 15623 / 12085 / 13166 |
| 10 | retest | short | 246093 | 82725 | 0.664 | 23546 / 20188 / 14931 / 11463 / 12597 |
| 20 | immediate | long | 180817 | 180817 | 0.000 | 180817 / 0 / 0 / 0 / 0 |
| 20 | immediate | short | 169723 | 169721 | 0.000 | 169721 / 0 / 0 / 0 / 0 |
| 20 | momentum | long | 180817 | 179855 | 0.005 | 178735 / 479 / 238 / 194 / 209 |
| 20 | momentum | short | 169723 | 168795 | 0.005 | 167627 / 504 / 230 / 209 / 225 |
| 20 | retest | long | 180817 | 61282 | 0.661 | 17792 / 14888 / 11074 / 8383 / 9145 |
| 20 | retest | short | 169723 | 58041 | 0.658 | 16959 / 14142 / 10392 / 7881 / 8667 |
| 50 | immediate | long | 111032 | 111032 | 0.000 | 111032 / 0 / 0 / 0 / 0 |
| 50 | immediate | short | 101731 | 101729 | 0.000 | 101729 / 0 / 0 / 0 / 0 |
| 50 | momentum | long | 111032 | 110386 | 0.006 | 109659 / 324 / 160 / 118 / 125 |
| 50 | momentum | short | 101731 | 101090 | 0.006 | 100316 / 346 / 164 / 135 / 129 |
| 50 | retest | long | 111032 | 38876 | 0.650 | 11529 / 9499 / 6988 / 5223 / 5637 |
| 50 | retest | short | 101731 | 36105 | 0.645 | 10884 / 8893 / 6249 / 4852 / 5227 |
| 100 | immediate | long | 77313 | 77313 | 0.000 | 77313 / 0 / 0 / 0 / 0 |
| 100 | immediate | short | 69458 | 69456 | 0.000 | 69456 / 0 / 0 / 0 / 0 |
| 100 | momentum | long | 77313 | 76849 | 0.006 | 76360 / 238 / 112 / 77 / 62 |
| 100 | momentum | short | 69458 | 68980 | 0.007 | 68439 / 249 / 116 / 99 / 77 |
| 100 | retest | long | 77313 | 27433 | 0.645 | 8380 / 6698 / 4906 / 3557 / 3892 |
| 100 | retest | short | 69458 | 25164 | 0.638 | 7775 / 6250 / 4260 / 3341 / 3538 |

## Breakout false-rate (direction-specific, mid-price returns through break level within 5 M1 bars)

| N | direction | n_signals | n_false | false_rate |
|---|---|---|---|---|
| 10 | long | 259157 | 114012 | 0.440 |
| 10 | short | 246093 | 108652 | 0.442 |
| 20 | long | 180817 | 79628 | 0.440 |
| 20 | short | 169723 | 74683 | 0.440 |
| 50 | long | 111032 | 48833 | 0.440 |
| 50 | short | 101731 | 44553 | 0.438 |
| 100 | long | 77313 | 33524 | 0.434 |
| 100 | short | 69458 | 30076 | 0.433 |

## Cost diagnostics for top-10 cells

### Rank 1: N=100, timing=retest, h=40, exit=time_exit_pnl

- median spread_entry: 2.000 pip
- median cost_ratio: 0.961 (p10 0.453, p90 1.867)

PnL by cost_ratio bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 0.5) | 6810 | -15840.2 | -2.326 |
| [0.5, 1.0) | 20868 | -48323.0 | -2.316 |
| [1.0, 1.5) | 14276 | -32993.0 | -2.311 |
| [1.5, 2.0) | 6251 | -15075.8 | -2.412 |
| [2.0, inf) | 4181 | -13122.0 | -3.138 |

PnL by spread_entry bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 1) pip | 1 | 3.1 | 3.100 |
| [1, 2) pip | 25319 | -42470.6 | -1.677 |
| [2, 3) pip | 17091 | -44233.6 | -2.588 |
| [3, inf) pip | 9975 | -38652.9 | -3.875 |

PnL by session:

| bucket | n | sum | mean |
|---|---|---|---|
| Tokyo (0-7 UTC) | 15578 | -36859.4 | -2.366 |
| London (7-14 UTC) | 20812 | -47023.6 | -2.259 |
| NY (14-21 UTC) | 13776 | -33752.6 | -2.450 |
| Rollover (21-24 UTC) | 2220 | -7718.4 | -3.477 |

Per-pair contribution (top 10 by absolute PnL):

| pair | n | sum | mean |
|---|---|---|---|
| GBP_JPY | 3027 | -11341.1 | -3.747 |
| CHF_JPY | 2645 | -10530.6 | -3.981 |
| GBP_AUD | 2499 | -9661.7 | -3.866 |
| EUR_AUD | 2653 | -8893.2 | -3.352 |
| EUR_CAD | 2518 | -8072.1 | -3.206 |
| EUR_JPY | 2982 | -6960.5 | -2.334 |
| NZD_JPY | 2390 | -6879.4 | -2.878 |
| AUD_JPY | 2931 | -6837.1 | -2.333 |
| GBP_CHF | 2306 | -6033.3 | -2.616 |
| GBP_USD | 3071 | -6021.4 | -1.961 |

### Rank 2: N=50, timing=retest, h=40, exit=time_exit_pnl

- median spread_entry: 2.000 pip
- median cost_ratio: 0.993 (p10 0.468, p90 1.965)

PnL by cost_ratio bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 0.5) | 8936 | -20633.9 | -2.309 |
| [0.5, 1.0) | 28627 | -64418.2 | -2.250 |
| [1.0, 1.5) | 20456 | -45443.6 | -2.222 |
| [1.5, 2.0) | 9412 | -23115.0 | -2.456 |
| [2.0, inf) | 7073 | -23554.6 | -3.330 |

PnL by spread_entry bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 1) pip | 2 | 3.1 | 1.550 |
| [1, 2) pip | 35561 | -59745.8 | -1.680 |
| [2, 3) pip | 24423 | -61208.6 | -2.506 |
| [3, inf) pip | 14518 | -56214.0 | -3.872 |

PnL by session:

| bucket | n | sum | mean |
|---|---|---|---|
| Tokyo (0-7 UTC) | 22214 | -49822.0 | -2.243 |
| London (7-14 UTC) | 28451 | -64883.9 | -2.281 |
| NY (14-21 UTC) | 19675 | -48029.0 | -2.441 |
| Rollover (21-24 UTC) | 4164 | -14430.4 | -3.466 |

Per-pair contribution (top 10 by absolute PnL):

| pair | n | sum | mean |
|---|---|---|---|
| GBP_JPY | 4314 | -15450.0 | -3.581 |
| CHF_JPY | 3784 | -15014.3 | -3.968 |
| GBP_AUD | 3619 | -14035.6 | -3.878 |
| EUR_AUD | 3850 | -12167.6 | -3.160 |
| EUR_JPY | 4366 | -10804.9 | -2.475 |
| EUR_CAD | 3558 | -10283.0 | -2.890 |
| AUD_JPY | 4251 | -9453.9 | -2.224 |
| NZD_JPY | 3395 | -9384.4 | -2.764 |
| GBP_USD | 4196 | -8440.4 | -2.012 |
| GBP_CHF | 3136 | -8273.0 | -2.638 |

### Rank 3: N=20, timing=retest, h=40, exit=time_exit_pnl

- median spread_entry: 2.000 pip
- median cost_ratio: 1.052 (p10 0.496, p90 2.090)

PnL by cost_ratio bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 0.5) | 12066 | -26861.6 | -2.226 |
| [0.5, 1.0) | 42749 | -97282.6 | -2.276 |
| [1.0, 1.5) | 33322 | -74788.3 | -2.244 |
| [1.5, 2.0) | 16590 | -40427.6 | -2.437 |
| [2.0, inf) | 13724 | -41925.8 | -3.055 |

PnL by spread_entry bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 1) pip | 4 | -14.4 | -3.600 |
| [1, 2) pip | 56246 | -95012.3 | -1.689 |
| [2, 3) pip | 39234 | -97051.8 | -2.474 |
| [3, inf) pip | 22967 | -89207.4 | -3.884 |

PnL by session:

| bucket | n | sum | mean |
|---|---|---|---|
| Tokyo (0-7 UTC) | 35402 | -80977.1 | -2.287 |
| London (7-14 UTC) | 42800 | -97924.7 | -2.288 |
| NY (14-21 UTC) | 33008 | -78358.9 | -2.374 |
| Rollover (21-24 UTC) | 7241 | -24025.2 | -3.318 |

Per-pair contribution (top 10 by absolute PnL):

| pair | n | sum | mean |
|---|---|---|---|
| GBP_JPY | 6847 | -23769.4 | -3.472 |
| CHF_JPY | 5997 | -23298.4 | -3.885 |
| GBP_AUD | 5731 | -22550.4 | -3.935 |
| EUR_AUD | 6211 | -18873.8 | -3.039 |
| EUR_JPY | 7125 | -17553.6 | -2.464 |
| EUR_CAD | 5697 | -17155.9 | -3.011 |
| NZD_JPY | 5428 | -14840.1 | -2.734 |
| GBP_CHF | 4901 | -14169.6 | -2.891 |
| AUD_JPY | 6746 | -14165.2 | -2.100 |
| USD_JPY | 7965 | -13061.6 | -1.640 |

### Rank 4: N=10, timing=retest, h=40, exit=time_exit_pnl

- median spread_entry: 2.000 pip
- median cost_ratio: 1.080 (p10 0.514, p90 2.143)

PnL by cost_ratio bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 0.5) | 15488 | -34974.7 | -2.258 |
| [0.5, 1.0) | 59018 | -133396.1 | -2.260 |
| [1.0, 1.5) | 47852 | -107581.3 | -2.248 |
| [1.5, 2.0) | 24472 | -60280.1 | -2.463 |
| [2.0, inf) | 21038 | -62478.5 | -2.970 |

PnL by spread_entry bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 1) pip | 4 | -14.4 | -3.600 |
| [1, 2) pip | 79520 | -133142.6 | -1.674 |
| [2, 3) pip | 55980 | -140021.7 | -2.501 |
| [3, inf) pip | 32364 | -125532.0 | -3.879 |

PnL by session:

| bucket | n | sum | mean |
|---|---|---|---|
| Tokyo (0-7 UTC) | 48868 | -110794.6 | -2.267 |
| London (7-14 UTC) | 59446 | -135410.7 | -2.278 |
| NY (14-21 UTC) | 48756 | -117581.9 | -2.412 |
| Rollover (21-24 UTC) | 10798 | -34923.5 | -3.234 |

Per-pair contribution (top 10 by absolute PnL):

| pair | n | sum | mean |
|---|---|---|---|
| GBP_JPY | 9806 | -35738.5 | -3.645 |
| GBP_AUD | 8253 | -33893.1 | -4.107 |
| CHF_JPY | 8376 | -30695.7 | -3.665 |
| EUR_JPY | 10084 | -26629.0 | -2.641 |
| EUR_AUD | 8873 | -26477.2 | -2.984 |
| EUR_CAD | 8070 | -23101.1 | -2.863 |
| AUD_JPY | 9612 | -20827.1 | -2.167 |
| NZD_JPY | 7708 | -20266.9 | -2.629 |
| USD_JPY | 11292 | -20129.8 | -1.783 |
| GBP_CHF | 7104 | -19160.9 | -2.697 |

### Rank 5: N=100, timing=immediate, h=40, exit=time_exit_pnl

- median spread_entry: 2.000 pip
- median cost_ratio: 1.087 (p10 0.497, p90 2.270)

PnL by cost_ratio bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 0.5) | 14857 | -36809.3 | -2.478 |
| [0.5, 1.0) | 49554 | -125395.5 | -2.530 |
| [1.0, 1.5) | 39706 | -94578.4 | -2.382 |
| [1.5, 2.0) | 20851 | -54642.1 | -2.621 |
| [2.0, inf) | 21002 | -76975.2 | -3.665 |

PnL by spread_entry bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 1) pip | 3 | -10.7 | -3.567 |
| [1, 2) pip | 69057 | -129306.1 | -1.872 |
| [2, 3) pip | 47997 | -126942.5 | -2.645 |
| [3, inf) pip | 28913 | -132141.2 | -4.570 |

PnL by session:

| bucket | n | sum | mean |
|---|---|---|---|
| Tokyo (0-7 UTC) | 46977 | -111938.5 | -2.383 |
| London (7-14 UTC) | 54451 | -127921.4 | -2.349 |
| NY (14-21 UTC) | 36491 | -103765.5 | -2.844 |
| Rollover (21-24 UTC) | 8051 | -44775.1 | -5.561 |

Per-pair contribution (top 10 by absolute PnL):

| pair | n | sum | mean |
|---|---|---|---|
| GBP_AUD | 7049 | -33915.2 | -4.811 |
| CHF_JPY | 7259 | -30439.0 | -4.193 |
| EUR_AUD | 7117 | -27116.0 | -3.810 |
| GBP_JPY | 7383 | -27009.3 | -3.658 |
| EUR_CAD | 7050 | -24950.1 | -3.539 |
| NZD_JPY | 7645 | -22722.1 | -2.972 |
| AUD_NZD | 6645 | -21258.2 | -3.199 |
| GBP_CHF | 6980 | -19570.5 | -2.804 |
| AUD_CAD | 7015 | -19295.6 | -2.751 |
| AUD_JPY | 7532 | -19018.2 | -2.525 |

### Rank 6: N=100, timing=momentum, h=40, exit=time_exit_pnl

- median spread_entry: 2.000 pip
- median cost_ratio: 1.091 (p10 0.501, p90 2.276)

PnL by cost_ratio bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 0.5) | 14458 | -35474.8 | -2.454 |
| [0.5, 1.0) | 49145 | -124732.2 | -2.538 |
| [1.0, 1.5) | 39684 | -94531.9 | -2.382 |
| [1.5, 2.0) | 20848 | -54585.7 | -2.618 |
| [2.0, inf) | 21039 | -77829.8 | -3.699 |

PnL by spread_entry bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 1) pip | 3 | -10.7 | -3.567 |
| [1, 2) pip | 68616 | -128504.8 | -1.873 |
| [2, 3) pip | 47743 | -125708.8 | -2.633 |
| [3, inf) pip | 28812 | -132930.1 | -4.614 |

PnL by session:

| bucket | n | sum | mean |
|---|---|---|---|
| Tokyo (0-7 UTC) | 46784 | -112266.5 | -2.400 |
| London (7-14 UTC) | 54102 | -126729.2 | -2.342 |
| NY (14-21 UTC) | 36229 | -102535.7 | -2.830 |
| Rollover (21-24 UTC) | 8059 | -45623.0 | -5.661 |

Per-pair contribution (top 10 by absolute PnL):

| pair | n | sum | mean |
|---|---|---|---|
| GBP_AUD | 7024 | -33994.9 | -4.840 |
| CHF_JPY | 7242 | -30853.5 | -4.260 |
| EUR_AUD | 7089 | -27182.6 | -3.834 |
| GBP_JPY | 7321 | -26516.6 | -3.622 |
| EUR_CAD | 7028 | -24927.4 | -3.547 |
| NZD_JPY | 7632 | -22685.5 | -2.972 |
| AUD_NZD | 6644 | -21308.2 | -3.207 |
| GBP_CHF | 6958 | -19495.0 | -2.802 |
| AUD_CAD | 6999 | -19233.2 | -2.748 |
| AUD_JPY | 7483 | -18733.4 | -2.503 |

### Rank 7: N=50, timing=immediate, h=40, exit=time_exit_pnl

- median spread_entry: 2.000 pip
- median cost_ratio: 1.141 (p10 0.517, p90 2.467)

PnL by cost_ratio bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 0.5) | 19256 | -48799.7 | -2.534 |
| [0.5, 1.0) | 67270 | -169608.2 | -2.521 |
| [1.0, 1.5) | 56494 | -132781.2 | -2.350 |
| [1.5, 2.0) | 31347 | -81263.9 | -2.592 |
| [2.0, inf) | 36496 | -151102.6 | -4.140 |

PnL by spread_entry bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 1) pip | 5 | -12.4 | -2.480 |
| [1, 2) pip | 98451 | -181640.7 | -1.845 |
| [2, 3) pip | 69188 | -182879.6 | -2.643 |
| [3, inf) pip | 43219 | -219022.9 | -5.068 |

PnL by session:

| bucket | n | sum | mean |
|---|---|---|---|
| Tokyo (0-7 UTC) | 67600 | -157060.4 | -2.323 |
| London (7-14 UTC) | 74285 | -175836.0 | -2.367 |
| NY (14-21 UTC) | 53002 | -152021.1 | -2.868 |
| Rollover (21-24 UTC) | 15976 | -98638.1 | -6.174 |

Per-pair contribution (top 10 by absolute PnL):

| pair | n | sum | mean |
|---|---|---|---|
| GBP_AUD | 10213 | -53755.5 | -5.263 |
| CHF_JPY | 10440 | -45856.9 | -4.392 |
| GBP_JPY | 10628 | -41428.7 | -3.898 |
| EUR_AUD | 10400 | -41353.3 | -3.976 |
| EUR_CAD | 10151 | -34440.6 | -3.393 |
| NZD_JPY | 10912 | -33082.5 | -3.032 |
| AUD_NZD | 9750 | -32973.3 | -3.382 |
| GBP_CHF | 9882 | -29860.9 | -3.022 |
| AUD_CAD | 10168 | -29808.3 | -2.932 |
| AUD_JPY | 10878 | -29096.1 | -2.675 |

### Rank 8: N=50, timing=momentum, h=40, exit=time_exit_pnl

- median spread_entry: 2.000 pip
- median cost_ratio: 1.146 (p10 0.520, p90 2.477)

PnL by cost_ratio bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 0.5) | 18773 | -47222.2 | -2.515 |
| [0.5, 1.0) | 66706 | -168763.8 | -2.530 |
| [1.0, 1.5) | 56451 | -132699.1 | -2.351 |
| [1.5, 2.0) | 31350 | -81245.0 | -2.592 |
| [2.0, inf) | 36645 | -153931.8 | -4.201 |

PnL by spread_entry bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 1) pip | 5 | -12.4 | -2.480 |
| [1, 2) pip | 97865 | -180431.5 | -1.844 |
| [2, 3) pip | 68876 | -181272.5 | -2.632 |
| [3, inf) pip | 43179 | -222145.5 | -5.145 |

PnL by session:

| bucket | n | sum | mean |
|---|---|---|---|
| Tokyo (0-7 UTC) | 67339 | -157258.6 | -2.335 |
| London (7-14 UTC) | 73837 | -174079.7 | -2.358 |
| NY (14-21 UTC) | 52658 | -150966.1 | -2.867 |
| Rollover (21-24 UTC) | 16091 | -101557.5 | -6.311 |

Per-pair contribution (top 10 by absolute PnL):

| pair | n | sum | mean |
|---|---|---|---|
| GBP_AUD | 10184 | -54288.1 | -5.331 |
| CHF_JPY | 10422 | -46314.2 | -4.444 |
| EUR_AUD | 10359 | -41345.2 | -3.991 |
| GBP_JPY | 10548 | -41064.7 | -3.893 |
| EUR_CAD | 10130 | -34450.1 | -3.401 |
| AUD_NZD | 9758 | -33217.3 | -3.404 |
| NZD_JPY | 10901 | -33196.0 | -3.045 |
| AUD_CAD | 10157 | -29920.6 | -2.946 |
| GBP_CHF | 9862 | -29861.8 | -3.028 |
| AUD_JPY | 10803 | -28694.3 | -2.656 |

### Rank 9: N=20, timing=immediate, h=40, exit=time_exit_pnl

- median spread_entry: 2.000 pip
- median cost_ratio: 1.231 (p10 0.557, p90 2.710)

PnL by cost_ratio bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 0.5) | 25696 | -62849.2 | -2.446 |
| [0.5, 1.0) | 100262 | -247525.3 | -2.469 |
| [1.0, 1.5) | 92002 | -218406.9 | -2.374 |
| [1.5, 2.0) | 55183 | -142542.7 | -2.583 |
| [2.0, inf) | 73403 | -293548.2 | -3.999 |

PnL by spread_entry bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 1) pip | 10 | -21.8 | -2.180 |
| [1, 2) pip | 160852 | -290790.5 | -1.808 |
| [2, 3) pip | 114101 | -303473.4 | -2.660 |
| [3, inf) pip | 71583 | -370586.6 | -5.177 |

PnL by session:

| bucket | n | sum | mean |
|---|---|---|---|
| Tokyo (0-7 UTC) | 110847 | -261044.7 | -2.355 |
| London (7-14 UTC) | 113080 | -269001.7 | -2.379 |
| NY (14-21 UTC) | 92734 | -253450.5 | -2.733 |
| Rollover (21-24 UTC) | 29885 | -181375.4 | -6.069 |

Per-pair contribution (top 10 by absolute PnL):

| pair | n | sum | mean |
|---|---|---|---|
| GBP_AUD | 16582 | -86359.7 | -5.208 |
| CHF_JPY | 17087 | -77162.3 | -4.516 |
| GBP_JPY | 17252 | -70098.6 | -4.063 |
| EUR_AUD | 17270 | -67154.7 | -3.889 |
| EUR_CAD | 16774 | -56474.6 | -3.367 |
| NZD_JPY | 17781 | -54672.7 | -3.075 |
| AUD_NZD | 16187 | -53763.3 | -3.321 |
| GBP_CHF | 16256 | -52263.2 | -3.215 |
| EUR_JPY | 17205 | -49435.1 | -2.873 |
| AUD_CAD | 17158 | -48481.0 | -2.826 |

### Rank 10: N=20, timing=momentum, h=40, exit=time_exit_pnl

- median spread_entry: 2.000 pip
- median cost_ratio: 1.236 (p10 0.561, p90 2.724)

PnL by cost_ratio bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 0.5) | 25043 | -60734.6 | -2.425 |
| [0.5, 1.0) | 99457 | -246330.5 | -2.477 |
| [1.0, 1.5) | 91921 | -218304.3 | -2.375 |
| [1.5, 2.0) | 55184 | -142521.9 | -2.583 |
| [2.0, inf) | 73742 | -299984.6 | -4.068 |

PnL by spread_entry bucket:

| bucket | n | sum | mean |
|---|---|---|---|
| [0, 1) pip | 11 | -35.3 | -3.209 |
| [1, 2) pip | 160017 | -289128.6 | -1.807 |
| [2, 3) pip | 113659 | -301559.2 | -2.653 |
| [3, inf) pip | 71660 | -377152.8 | -5.263 |

PnL by session:

| bucket | n | sum | mean |
|---|---|---|---|
| Tokyo (0-7 UTC) | 110481 | -261021.8 | -2.363 |
| London (7-14 UTC) | 112451 | -266564.4 | -2.370 |
| NY (14-21 UTC) | 92238 | -252184.2 | -2.734 |
| Rollover (21-24 UTC) | 30177 | -188105.5 | -6.233 |

Per-pair contribution (top 10 by absolute PnL):

| pair | n | sum | mean |
|---|---|---|---|
| GBP_AUD | 16548 | -87386.5 | -5.281 |
| CHF_JPY | 17073 | -78004.3 | -4.569 |
| GBP_JPY | 17133 | -70047.2 | -4.088 |
| EUR_AUD | 17219 | -67190.5 | -3.902 |
| EUR_CAD | 16736 | -56385.5 | -3.369 |
| NZD_JPY | 17784 | -55173.6 | -3.102 |
| AUD_NZD | 16196 | -54083.7 | -3.339 |
| GBP_CHF | 16235 | -52391.5 | -3.227 |
| EUR_JPY | 17046 | -49205.5 | -2.887 |
| AUD_CAD | 17153 | -48903.3 | -2.851 |

## NG list compliance (postmortem §4)

- NG#1 pair filter: 20/20 pairs evaluated; no cell-level pair drop ✓
- NG#2 train-side time filter: not applied — Donchian uses all M5 bars ✓
- NG#3 test-side filter improvement claim: verdict on all valid+non-gap rows, not a time-of-day subset ✓
- NG#4 WeekOpen-aware sample weighting: none ✓
- NG#5 universe-restricted cross-pair feature: none ✓
