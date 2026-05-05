# Stage 22.0e-v2 Independent OOS Validation — Evaluation Report

Generated: 2026-05-05T18:41:31.696442+00:00

Design contract: `docs/design/phase22_0e_v2_independent_oos.md`.

> ⚠ **Independence caveat**: this is an OOS validation of a single cell
> pre-selected from a 48-cell sweep in PR #259. The OOS window is a
> chronological hold-out from the same 730-day OANDA pull, NOT a fresh
> fetch. ADOPT here means (1) the PR #259 cell was not a multiple-
> testing artifact and (2) the eight gates are met without re-tuning.
> ADOPT does NOT mean production-ready — paper-run on bars beyond the
> 730-day pull is the next layer.

## Frozen cell

- primary signal: donchian_immediate
- N_DONCHIAN = 50
- CONF_THRESHOLD = 0.55
- HORIZON_BARS = 40
- EXIT_RULE = time_exit_pnl
- FEATURE_SET = ['cost_ratio', 'atr_at_entry', 'spread_entry', 'z_score_10', 'z_score_20', 'z_score_50', 'z_score_100', 'donchian_position', 'breakout_age_M5_bars', 'pair', 'direction']

## Pair coverage

- Active pairs: 20 / 20 canonical (missing: none)

## Verdict: **FAILED_OOS**

- A0 OOS annual_trades=70 ≥ 70: **PASS**
- A1 OOS Sharpe=-0.0191 ≥ 0.082: **FAIL**
- A2 OOS annual_pnl=-58.5 ≥ 180.0: **FAIL**
- A3 OOS MaxDD=312.1 ≤ 200.0: **FAIL**
- A4 OOS sub-fold pos/neg=1/3 ≥ 3/1: **FAIL**
- A5 stress +0.5pip annual_pnl=-93.5 > 0: **FAIL**
- S0 |shuffled_sharpe|=0.0000 < 0.1: **PASS** (diagnostic <0.05: pass)
- S1 train_test_gap=0.3804 ≤ 0.3: **FAIL**

**Gates failed**: A1, A2, A3, A4, A5, S1

## OOS summary

- Train rows: 168,690
- OOS rows (raw breakouts in last 20%): 42,173
- OOS rows after conf=0.55 filter: 20
- OOS span: 0.286 years
- OOS mean PnL/trade: -0.835 pip
- OOS win rate: 0.400
- OOS DD%PnL: 533.8%
- Train Sharpe (filtered conf≥0.55): 0.3613
- OOS Sharpe (filtered conf≥0.55): -0.0191
- Train-OOS gap (S1): 0.3804

## OOS sub-folds (DIAGNOSTIC ONLY — no training role)

| sub-fold | range | n | sum_pnl | sharpe |
|---|---|---|---|---|
| 1 | 2026-01-16T02:41:00 → 2026-02-11T13:31:00 | 5 | -27.7 | -0.3395 |
| 2 | 2026-02-11T13:31:00 → 2026-02-11T13:31:00 | 5 | -215.8 | -2.1445 |
| 3 | 2026-02-25T00:31:00 → 2026-03-30T13:36:00 | 5 | -39.2 | -0.4191 |
| 4 | 2026-03-31T14:56:00 → 2026-04-30T10:31:00 | 5 | 266.0 | 1.2382 |

## Spread stress (OOS annual PnL, pip)

| stress | annual_pnl |
|---|---|
| +0.0 | -58.5 |
| +0.2 | -72.5 |
| +0.5 | -93.5 |

## Drawdown concentration analysis

- Total OOS PnL: -16.7
- Total MaxDD: 312.1
- Worst-20 trade PnL sum: -16.7
- Worst-20 share of negative PnL: 5.0%
- Worst pair: **USD_JPY** (MaxDD share = 46.1%)
- Longest consecutive loss run: 9

### Worst 20 trades

| entry_ts | pair | dir | pred_P | pnl |
|---|---|---|---|---|
| 2026-02-11 13:31:00 | USD_JPY | long | 0.645 | -80.0 |
| 2026-02-11 13:31:00 | AUD_USD | short | 0.584 | -43.1 |
| 2026-02-11 13:31:00 | GBP_USD | short | 0.633 | -42.8 |
| 2026-03-24 20:26:00 | USD_JPY | short | 0.562 | -32.3 |
| 2026-02-11 13:31:00 | NZD_USD | short | 0.572 | -28.0 |
| 2026-02-11 13:31:00 | EUR_USD | short | 0.606 | -26.5 |
| 2026-02-11 13:31:00 | USD_CHF | long | 0.619 | -23.4 |
| 2026-03-23 11:06:00 | USD_JPY | short | 0.591 | -23.4 |
| 2026-01-16 02:41:00 | USD_JPY | short | 0.571 | -16.5 |
| 2026-01-28 15:11:00 | USD_JPY | long | 0.608 | -8.1 |
| 2026-04-22 05:21:00 | AUD_USD | long | 0.556 | -7.3 |
| 2026-02-25 00:31:00 | AUD_USD | long | 0.595 | -5.0 |
| 2026-03-24 17:06:00 | NZD_USD | short | 0.572 | 0.5 |
| 2026-01-22 00:31:00 | AUD_USD | long | 0.580 | 7.3 |
| 2026-03-31 14:56:00 | GBP_JPY | short | 0.557 | 11.2 |
| 2026-01-20 07:36:00 | GBP_USD | long | 0.565 | 17.6 |
| 2026-03-30 13:36:00 | GBP_USD | short | 0.562 | 21.0 |
| 2026-04-30 10:31:00 | USD_JPY | short | 0.562 | 73.3 |
| 2026-04-30 10:31:00 | EUR_JPY | short | 0.587 | 92.6 |
| 2026-04-30 10:31:00 | GBP_JPY | short | 0.603 | 96.2 |

### Per-pair PnL (sorted ascending by sum_pnl)

| pair | n | sum_pnl | mean_pnl | max_dd | max_dd_share |
|---|---|---|---|---|---|
| USD_JPY | 6 | -87.0 | -14.500 | 143.8 | 46.1% |
| AUD_USD | 4 | -48.1 | -12.025 | 55.4 | 17.8% |
| NZD_USD | 2 | -27.5 | -13.750 | 0.0 | 0.0% |
| EUR_USD | 1 | -26.5 | -26.500 | 0.0 | 0.0% |
| USD_CHF | 1 | -23.4 | -23.400 | 0.0 | 0.0% |
| GBP_USD | 3 | -4.2 | -1.400 | 42.8 | 13.7% |
| EUR_JPY | 1 | 92.6 | 92.600 | 0.0 | 0.0% |
| GBP_JPY | 2 | 107.4 | 53.700 | 0.0 | 0.0% |

### Per-session PnL

| session | n | sum_pnl | mean | max_dd |
|---|---|---|---|---|
| Tokyo (0-7) | 4 | -21.5 | -5.375 | 12.3 |
| London (7-14) | 12 | 33.5 | 2.792 | 267.2 |
| NY (14-21) | 4 | -28.7 | -7.175 | 32.3 |
| Rollover (21-24) | 0 | 0.0 | 0.000 | 0.0 |

### Consecutive-loss-run histogram

| run length | count |
|---|---|
| 1 | 3 |
| 9 | 1 |

### Drawdown attribution: **SINGLE_PAIR_CONCENTRATION (worst pair MaxDD share = 46.1%); SINGLE_PERIOD_CONCENTRATION (worst sub-fold = 76.3%)**

*This attribution is descriptive only — it does not prescribe any risk-control mechanism in this PR. The attribution informs (but does not authorise) future risk-control studies subject to NG-list constraints.*

## Feature importance (LightGBM gain)

| feature | gain |
|---|---|
| cost_ratio | 20788 |
| spread_entry | 7756 |
| atr_at_entry | 6402 |
| donchian_position | 2976 |
| breakout_age_M5_bars | 1999 |
| z_score_10 | 0 |
| z_score_20 | 0 |
| z_score_50 | 0 |
| z_score_100 | 0 |

## NG list compliance (postmortem §4)

- NG#1 pair filter: 20-pair universe, no cell-level pair drop ✓
- NG#2 train-side time-of-day filter: not applied ✓
- NG#3 test-side filter improvement claim: OOS verdict on full last-20% ✓
- NG#4 WeekOpen-aware sample weighting: none ✓
- NG#5 universe-restricted cross-pair feature: none ✓

## Feature allowlist compliance (audit PR #258)

- MAIN_FEATURE_COLS = ['cost_ratio', 'atr_at_entry', 'spread_entry', 'z_score_10', 'z_score_20', 'z_score_50', 'z_score_100', 'donchian_position', 'breakout_age_M5_bars', 'pair', 'direction']
- is_week_open_window in MAIN: False (must be False)
- hour_utc in MAIN: False (must be False)
- dow in MAIN: False (must be False)
