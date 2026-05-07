# Stage 25.0b-β — F1 Volatility Expansion / Compression Eval

Generated: 2026-05-07T22:19:32.832424+00:00

Design contract: `docs/design/phase25_0b_f1_design.md` (PR #283)

## Mandatory clauses

**1. Phase 25 framing.** Phase 25 is not a hyperparameter-tuning phase. It is a label-and-feature-class redesign phase. Novelty must come from input feature class and label design.

**2. F1 negative list.** F1 features are volatility-derivative. F1 is NOT a Donchian breakout, NOT a z-score, NOT a Bollinger band touch, NOT a moving average crossover, NOT a calibration-only signal. Recent return sign (f1_f) is secondary directional context only — it MUST NOT serve as a standalone primary trigger.

**3. Diagnostic columns are not features.** The 25.0a-β diagnostic columns (max_fav_excursion_pip, max_adv_excursion_pip, time_to_fav_bar, time_to_adv_bar, same_bar_both_hit) MUST NOT appear in any model's feature matrix. A unit test enforces this.

**4. Causality and split discipline.** All f1 features use shift(1).rolling pattern; signal bar t's own data MUST NOT enter feature[t]. Train / val / test splits are strictly chronological (70/15/15 by calendar date). Threshold selection uses VALIDATION ONLY; test set is touched once.

**5. γ closure preservation.** Phase 25.0b does not modify the γ closure (PR #279). Phase 25 results, regardless of outcome, do not change Phase 24 / NG#10 β-chain closure status.

**6. Production-readiness preservation.** PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE in 25.0b are hypothesis-generating only. Production-readiness requires an X-v2-equivalent frozen-OOS PR per Phase 22 contract. No production deployment is pre-approved by this PR.

**Test-touched-once invariant**: threshold selected on validation only; test set touched once.

## Realised barrier PnL methodology

Final test 8-gate evaluation uses **realised barrier PnL** computed by re-traversing M1 paths with 25.0a barrier semantics:
- favourable barrier first → +K_FAV × ATR
- adverse barrier first → −K_ADV × ATR
- same-bar both-hit → adverse first → −K_ADV × ATR
- horizon expiry → mark-to-market (close at t+H − entry, in pips)

This is **realised barrier PnL, not broker-fill PnL**. Production deployment requires X-v2-equivalent frozen-OOS PR with broker-aware fill modeling.

Validation threshold selection uses **synthesized PnL proxy** (±K_FAV/K_ADV × ATR by label) for speed.

## Cell-grid integrity note

The 24-cell grid has a `lookback` dimension at {50, 100}. The current implementation pre-computes `f1_b_compression_pct` with the global `COMPRESSION_TRAILING=100` constant; both `lookback` values therefore use the same precomputed column as an approximation. Future refinement: pre-compute compression_pct at both lookbacks and dispatch per cell. This is documented as a known approximation; cell rankings remain informative for the 24-cell sweep.

## Split dates

- min: 2024-05-07 18:00:00+00:00
- train < 2025-09-25 15:44:00+00:00
- val [2025-09-25 15:44:00+00:00, 2026-01-12 01:32:00+00:00)
- test [2026-01-12 01:32:00+00:00, 2026-04-30 11:20:00+00:00]

## Feature NaN drop

- overall drop count: 44434; rate: 0.0110

Per-pair feature NaN drop:

| pair | drop_count | drop_rate |
|---|---|---|
| AUD_CAD | 1978 | 0.0135 |
| AUD_JPY | 2788 | 0.0108 |
| AUD_NZD | 420 | 0.0071 |
| AUD_USD | 2580 | 0.0104 |
| CHF_JPY | 2802 | 0.0130 |
| EUR_AUD | 2752 | 0.0122 |
| EUR_CAD | 2088 | 0.0113 |
| EUR_CHF | 1852 | 0.0122 |
| EUR_GBP | 1070 | 0.0074 |
| EUR_JPY | 2830 | 0.0108 |
| EUR_USD | 1958 | 0.0087 |
| GBP_AUD | 2830 | 0.0141 |
| GBP_CHF | 2068 | 0.0129 |
| GBP_JPY | 2776 | 0.0107 |
| GBP_USD | 2302 | 0.0099 |
| NZD_JPY | 2078 | 0.0111 |
| NZD_USD | 2260 | 0.0106 |
| USD_CAD | 2044 | 0.0106 |
| USD_CHF | 2156 | 0.0103 |
| USD_JPY | 2802 | 0.0101 |

## All 24 cells — summary (sorted by test AUC desc)

| TF | lookback | quantile | expansion | n_train | n_test | train_AUC | val_AUC | test_AUC | gap | verdict | h_state | n_trades | sharpe | ann_pnl | low_power |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M5 | 50 | 0.2 | 1.25 | 386 | 96 | 0.8144 | 0.4816 | 0.5644 | 0.2500 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 26 | -0.1920 | -107.6 | YES |
| M5 | 100 | 0.2 | 1.25 | 386 | 96 | 0.8144 | 0.4816 | 0.5644 | 0.2500 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 26 | -0.1920 | -107.6 | YES |
| M15 | 50 | 0.2 | 1.25 | 1332 | 178 | 0.6595 | 0.5058 | 0.5038 | 0.1557 | REJECT | H1_FAIL | 57 | -0.4998 | -540.9 | YES |
| M15 | 100 | 0.2 | 1.25 | 1332 | 178 | 0.6595 | 0.5058 | 0.5038 | 0.1557 | REJECT | H1_FAIL | 57 | -0.4998 | -540.9 | YES |
| M5 | 50 | 0.1 | 1.25 | 114 | 38 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| M5 | 50 | 0.1 | 1.5 | 40 | 14 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| M5 | 50 | 0.2 | 1.5 | 86 | 22 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| M5 | 100 | 0.1 | 1.25 | 114 | 38 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| M5 | 100 | 0.1 | 1.5 | 40 | 14 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| M5 | 100 | 0.2 | 1.5 | 86 | 22 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| M15 | 50 | 0.1 | 1.25 | 334 | 42 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| M15 | 50 | 0.1 | 1.5 | 108 | 6 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| M15 | 50 | 0.2 | 1.5 | 324 | 24 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| M15 | 100 | 0.1 | 1.25 | 334 | 42 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| M15 | 100 | 0.1 | 1.5 | 108 | 6 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| M15 | 100 | 0.2 | 1.5 | 324 | 24 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| H1 | 50 | 0.1 | 1.25 | 0 | 0 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| H1 | 50 | 0.1 | 1.5 | 0 | 0 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| H1 | 50 | 0.2 | 1.25 | 48 | 0 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| H1 | 50 | 0.2 | 1.5 | 0 | 0 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| H1 | 100 | 0.1 | 1.25 | 0 | 0 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| H1 | 100 | 0.1 | 1.5 | 0 | 0 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| H1 | 100 | 0.2 | 1.25 | 48 | 0 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |
| H1 | 100 | 0.2 | 1.5 | 0 | 0 | nan | nan | nan | nan | REJECT | INSUFFICIENT_DATA | 0 | nan | +0.0 | YES |

## Top-3 cells by test AUC — expanded breakdown

### Cell: TF=M5, lookback=50, quantile=0.2, expansion=1.25

- n_train: 386, n_val: 54, n_test: 96
- train AUC: 0.8144, val AUC: 0.4816, test AUC: 0.5644, gap: 0.2500
- threshold selected on validation: 0.4
- realised: n_trades=26, sharpe=-0.1920, ann_pnl=-107.6, max_dd=38.6, A4 pos=1/4, A5 stress ann_pnl=-150.9
- proxy: n_trades=26, sharpe=-0.3030, ann_pnl=-169.2
- gates: A0=OK A1=x A2=x A3=OK A4=x A5=x
- calibration: monotonic=False, brier=0.2381
- verdict: **REJECT_BUT_INFORMATIVE** (H1_PASS_H2_FAIL)
- by-pair trade count: {'EUR_USD': 6, 'AUD_USD': 6, 'NZD_USD': 1, 'USD_CHF': 1, 'USD_JPY': 4, 'GBP_JPY': 1, 'AUD_JPY': 3, 'EUR_AUD': 1, 'AUD_CAD': 3}
- by-direction trade count: {'long': 0, 'short': 26}

### Cell: TF=M5, lookback=100, quantile=0.2, expansion=1.25

- n_train: 386, n_val: 54, n_test: 96
- train AUC: 0.8144, val AUC: 0.4816, test AUC: 0.5644, gap: 0.2500
- threshold selected on validation: 0.4
- realised: n_trades=26, sharpe=-0.1920, ann_pnl=-107.6, max_dd=38.6, A4 pos=1/4, A5 stress ann_pnl=-150.9
- proxy: n_trades=26, sharpe=-0.3030, ann_pnl=-169.2
- gates: A0=OK A1=x A2=x A3=OK A4=x A5=x
- calibration: monotonic=False, brier=0.2381
- verdict: **REJECT_BUT_INFORMATIVE** (H1_PASS_H2_FAIL)
- by-pair trade count: {'EUR_USD': 6, 'AUD_USD': 6, 'NZD_USD': 1, 'USD_CHF': 1, 'USD_JPY': 4, 'GBP_JPY': 1, 'AUD_JPY': 3, 'EUR_AUD': 1, 'AUD_CAD': 3}
- by-direction trade count: {'long': 0, 'short': 26}

### Cell: TF=M15, lookback=50, quantile=0.2, expansion=1.25

- n_train: 1332, n_val: 186, n_test: 178
- train AUC: 0.6595, val AUC: 0.5058, test AUC: 0.5038, gap: 0.1557
- threshold selected on validation: 0.4
- realised: n_trades=57, sharpe=-0.4998, ann_pnl=-540.9, max_dd=156.6, A4 pos=0/4, A5 stress ann_pnl=-635.9
- proxy: n_trades=57, sharpe=-0.6316, ann_pnl=-664.7
- gates: A0=OK A1=x A2=x A3=OK A4=x A5=x
- calibration: monotonic=False, brier=0.2360
- verdict: **REJECT** (H1_FAIL)
- by-pair trade count: {'AUD_USD': 10, 'NZD_USD': 2, 'USD_CAD': 5, 'EUR_GBP': 3, 'USD_JPY': 9, 'GBP_JPY': 6, 'NZD_JPY': 3, 'CHF_JPY': 4, 'EUR_CHF': 3, 'EUR_CAD': 3, 'GBP_AUD': 6, 'GBP_CHF': 3}
- by-direction trade count: {'long': 57, 'short': 0}

## Top-3 cells by realised Sharpe — compact

| TF | lookback | quantile | expansion | sharpe | ann_pnl | n_trades | verdict |
|---|---|---|---|---|---|---|---|
| M5 | 50 | 0.2 | 1.25 | -0.1920 | -107.6 | 26 | REJECT_BUT_INFORMATIVE |
| M5 | 100 | 0.2 | 1.25 | -0.1920 | -107.6 | 26 | REJECT_BUT_INFORMATIVE |
| M15 | 50 | 0.2 | 1.25 | -0.4998 | -540.9 | 57 | REJECT |

## Multiple-testing caveat

These are 24 evaluated cells. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE verdicts are hypothesis-generating ONLY; production-readiness requires an X-v2-equivalent frozen-OOS PR per Phase 22 contract.

## H1 routing summary: 2 / 24 cells PASS H1 (test AUC >= 0.55)
