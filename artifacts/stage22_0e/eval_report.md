# Stage 22.0e Meta-Labeling — Evaluation Report

Generated: 2026-05-05T18:10:10.379709+00:00

Design contract: `docs/design/phase22_0e_meta_labeling.md`.

> ⚠ **Multiple testing caveat**: 48 cells were searched on the Donchian-immediate
> primary signal, against OOS predictions over 4 walk-forward folds. The reported
> best cell's metrics are *in-sample search results on OOS predictions*. Production
> migration of any ADOPT cell requires independent OOS validation (held-out future
> time slice, paper-run, or fresh data fetch).

## Pair coverage

- Active pairs: 20 / 20 canonical (missing: none)

## Verdict (main feature set)

### **PROMISING_BUT_NEEDS_OOS**

- Best cell: N=50, conf=0.55, horizon=40, exit=time_exit_pnl
- A0 annual_trades=80 >= 70: **PASS**
- A1 sharpe=0.1377 >= 0.082: **PASS**
- A2 annual_pnl=276.8 >= 180.0: **PASS**
- A3 MaxDD=355.7 <= 200.0: **FAIL**
- A4 OOS fold pos/neg=3/1 >= 3/1: **PASS**
- A5 stress +0.5pip annual_pnl=237.0 > 0: **PASS**
- S0 hard gate |shuffled_sharpe|=0.0000 < 0.1: **PASS** (diagnostic <0.05: pass)
- S1 train_test_gap=0.1745 <= 0.3: **PASS**

**Gates that failed**:
- A3: MaxDD 355.7 > 200.0

## Top-10 cells (main feature set, by Sharpe)

| rank | N | conf | h | exit | n/yr | PnL/yr | Sharpe | MaxDD | DD%PnL | fold ± | +0.5 stress | shuffled | gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 50 | 0.55 | 40 | time_exit_pnl | 80 | 276.8 | 0.1377 | 355.7 | 128.5% | 3/1 | 237.0 | 0.0000 | 0.1745 |
| 2 | 50 | 0.60 | 40 | time_exit_pnl | 30 | 61.1 | 0.0716 | 338.0 | 553.3% | 2/1 | 46.3 | 0.0000 | 0.2857 |
| 3 | 20 | 0.55 | 40 | time_exit_pnl | 56 | 117.9 | 0.0653 | 533.5 | 452.4% | 2/2 | 90.2 | 0.0000 | 0.2400 |
| 4 | 50 | 0.50 | 40 | time_exit_pnl | 194 | 360.6 | 0.0636 | 879.3 | 243.8% | 2/2 | 263.8 | 0.0000 | 0.2572 |
| 5 | 20 | 0.50 | 40 | time_exit_pnl | 230 | -270.0 | -0.0327 | 1648.3 | 610.4% | 2/2 | -384.9 | 0.0000 | 0.2817 |
| 6 | 50 | 0.50 | 20 | time_exit_pnl | 96 | -298.4 | -0.0845 | 1193.9 | 400.2% | 1/3 | -346.1 | 0.0000 | 0.3976 |
| 7 | 20 | 0.50 | 20 | time_exit_pnl | 91 | -431.4 | -0.1051 | 1451.3 | 336.4% | 2/2 | -476.7 | 0.0000 | 0.4256 |
| 8 | 20 | 0.50 | 10 | time_exit_pnl | 42 | -408.1 | -0.2780 | 896.9 | 219.8% | 0/3 | -428.8 | 0.0000 | 0.8958 |
| 9 | 50 | 0.50 | 10 | tb_pnl | 20 | -151.5 | -0.2857 | 458.9 | 302.9% | 1/2 | -161.3 | 0.0000 | 1.3516 |
| 10 | 50 | 0.50 | 10 | time_exit_pnl | 59 | -586.5 | -0.2985 | 1332.8 | 227.2% | 1/2 | -616.0 | 0.0000 | 0.7602 |

## Top-10 OOS per-fold PnL

| rank | f1 | f2 | f3 | f4 | CV | top conc |
|---|---|---|---|---|---|---|
| 1 | 352.6 | 86.0 | 161.0 | -46.4 | 1.04 | 54.6% |
| 2 | 128.8 | 18.0 | 0.0 | -24.7 | 1.92 | 75.1% |
| 3 | 289.2 | 209.8 | -67.0 | -196.3 | 3.36 | 37.9% |
| 4 | 510.6 | -112.2 | 837.9 | -515.6 | 2.93 | 42.4% |
| 5 | 450.1 | -696.6 | 287.4 | -580.6 | 3.77 | 34.6% |
| 6 | -44.4 | -527.4 | 247.4 | -271.9 | 1.92 | 48.3% |
| 7 | 364.8 | -956.4 | 9.3 | -279.9 | 2.25 | 59.4% |
| 8 | -24.5 | -440.7 | 0.0 | -350.4 | 0.95 | 54.0% |
| 9 | 87.8 | -170.3 | 0.0 | -220.3 | 1.65 | 46.0% |
| 10 | 22.1 | -801.5 | 0.0 | -392.8 | 1.15 | 65.9% |

## Train-test parity (S1) for top-10

| rank | train_sharpe (per fold) | test_sharpe (per fold) | gap |
|---|---|---|---|
| 1 | 0.362 / 0.353 / 0.362 / 0.353 | 0.179 / 0.264 / 0.334 / -0.045 | 0.1745 |
| 2 | 0.437 / 0.293 / 0.369 / 0.357 | 0.141 / 0.221 / 0.000 / -0.048 | 0.2857 |
| 3 | 0.294 / 0.282 / 0.341 / 0.338 | 0.233 / 0.238 / 0.000 / -0.175 | 0.2400 |
| 4 | 0.308 / 0.241 / 0.309 / 0.291 | 0.110 / -0.064 / 0.356 / -0.281 | 0.2572 |
| 5 | 0.318 / 0.242 / 0.193 / 0.294 | 0.075 / -0.099 / 0.279 / -0.336 | 0.2817 |
| 6 | 0.576 / 0.354 / 0.345 / 0.359 | -0.050 / -0.123 / 0.487 / -0.270 | 0.3976 |
| 7 | 0.624 / 0.258 / 0.344 / 0.384 | 0.357 / -0.163 / 0.000 / -0.287 | 0.4256 |
| 8 | 0.668 / 0.322 / 0.949 / 0.356 | -0.437 / -0.194 / 0.000 / -0.657 | 0.8958 |
| 9 | 1.001 / 0.754 / 0.524 / 0.559 | 0.274 / -0.353 / 0.000 / -2.489 | 1.3516 |
| 10 | 0.558 / 0.411 / 0.692 / 0.246 | 0.035 / -0.321 / 0.000 / -0.848 | 0.7602 |

## Feature importance (LightGBM gain, summed across folds) — top-10 cells

### Rank 1: N=50, conf=0.55, h=40, exit=time_exit_pnl

| feature | gain |
|---|---|
| cost_ratio | 49240 |
| spread_entry | 19734 |
| atr_at_entry | 17903 |
| donchian_position | 9465 |
| breakout_age_M5_bars | 6174 |
| z_score_10 | 0 |
| z_score_20 | 0 |
| z_score_50 | 0 |
| z_score_100 | 0 |

### Rank 2: N=50, conf=0.60, h=40, exit=time_exit_pnl

| feature | gain |
|---|---|
| cost_ratio | 49240 |
| spread_entry | 19734 |
| atr_at_entry | 17903 |
| donchian_position | 9465 |
| breakout_age_M5_bars | 6174 |
| z_score_10 | 0 |
| z_score_20 | 0 |
| z_score_50 | 0 |
| z_score_100 | 0 |

### Rank 3: N=20, conf=0.55, h=40, exit=time_exit_pnl

| feature | gain |
|---|---|
| cost_ratio | 98416 |
| spread_entry | 32459 |
| atr_at_entry | 29147 |
| donchian_position | 11135 |
| breakout_age_M5_bars | 5806 |
| z_score_10 | 0 |
| z_score_20 | 0 |
| z_score_50 | 0 |
| z_score_100 | 0 |

### Rank 4: N=50, conf=0.50, h=40, exit=time_exit_pnl

| feature | gain |
|---|---|
| cost_ratio | 49240 |
| spread_entry | 19734 |
| atr_at_entry | 17903 |
| donchian_position | 9465 |
| breakout_age_M5_bars | 6174 |
| z_score_10 | 0 |
| z_score_20 | 0 |
| z_score_50 | 0 |
| z_score_100 | 0 |

### Rank 5: N=20, conf=0.50, h=40, exit=time_exit_pnl

| feature | gain |
|---|---|
| cost_ratio | 98416 |
| spread_entry | 32459 |
| atr_at_entry | 29147 |
| donchian_position | 11135 |
| breakout_age_M5_bars | 5806 |
| z_score_10 | 0 |
| z_score_20 | 0 |
| z_score_50 | 0 |
| z_score_100 | 0 |

### Rank 6: N=50, conf=0.50, h=20, exit=time_exit_pnl

| feature | gain |
|---|---|
| cost_ratio | 76494 |
| atr_at_entry | 26073 |
| spread_entry | 17637 |
| donchian_position | 9433 |
| breakout_age_M5_bars | 5319 |
| z_score_10 | 0 |
| z_score_20 | 0 |
| z_score_50 | 0 |
| z_score_100 | 0 |

### Rank 7: N=20, conf=0.50, h=20, exit=time_exit_pnl

| feature | gain |
|---|---|
| cost_ratio | 143103 |
| atr_at_entry | 42488 |
| spread_entry | 31892 |
| donchian_position | 8938 |
| breakout_age_M5_bars | 5518 |
| z_score_10 | 0 |
| z_score_20 | 0 |
| z_score_50 | 0 |
| z_score_100 | 0 |

### Rank 8: N=20, conf=0.50, h=10, exit=time_exit_pnl

| feature | gain |
|---|---|
| cost_ratio | 202570 |
| atr_at_entry | 59054 |
| spread_entry | 28237 |
| donchian_position | 12388 |
| breakout_age_M5_bars | 6487 |
| z_score_10 | 0 |
| z_score_20 | 0 |
| z_score_50 | 0 |
| z_score_100 | 0 |

### Rank 9: N=50, conf=0.50, h=10, exit=tb_pnl

| feature | gain |
|---|---|
| cost_ratio | 309472 |
| atr_at_entry | 100319 |
| spread_entry | 28924 |
| donchian_position | 16431 |
| breakout_age_M5_bars | 9230 |
| z_score_10 | 0 |
| z_score_20 | 0 |
| z_score_50 | 0 |
| z_score_100 | 0 |

### Rank 10: N=50, conf=0.50, h=10, exit=time_exit_pnl

| feature | gain |
|---|---|
| cost_ratio | 106054 |
| atr_at_entry | 33665 |
| spread_entry | 17433 |
| donchian_position | 9933 |
| breakout_age_M5_bars | 6005 |
| z_score_10 | 0 |
| z_score_20 | 0 |
| z_score_50 | 0 |
| z_score_100 | 0 |

## Ablation-A diagnostic (main + hour_utc) — DIAGNOSTIC ONLY, NOT verdict

- Best Ablation-A cell Sharpe: 0.2289 (main best: 0.1377)
- Δ Sharpe lift = +0.0911
- Lift ≥ 0.05 — flagged for Ablation-B

## Ablation-B diagnostic (main + hour_utc + dow) — DIAGNOSTIC ONLY

- Best Ablation-B cell Sharpe: 0.1909

## NG list compliance (postmortem §4)

- NG#1 pair filter: 20-pair universe, no cell-level pair drop ✓
- NG#2 train-side time-of-day filter: not applied; Donchian uses all bars ✓
- NG#3 test-side filter improvement claim: verdict on OOS predictions only ✓
- NG#4 WeekOpen-aware sample weighting: none; is_week_open_window excluded entirely ✓
- NG#5 universe-restricted cross-pair feature: none ✓

## Feature allowlist compliance (audit PR #258)

- MAIN_FEATURE_COLS = ['cost_ratio', 'atr_at_entry', 'spread_entry', 'z_score_10', 'z_score_20', 'z_score_50', 'z_score_100', 'donchian_position', 'breakout_age_M5_bars', 'pair', 'direction']
- is_week_open_window in MAIN: False  (must be False)
- hour_utc in MAIN: False  (must be False)
- dow in MAIN: False  (must be False)
- forbidden ∩ main: [] (must be empty)
