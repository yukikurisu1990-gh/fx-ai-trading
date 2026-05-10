# Stage 25.0f-β — F5 Liquidity / Spread / Volume Eval

Generated: 2026-05-10T16:40:55.458608+00:00

Design contract: `docs/design/phase25_0f_alpha_f5_design.md` (PR #295)

**F5 is the LAST feature-axis attempt within Phase 25** per PR #294 routing review.

## Mandatory clauses (verbatim per 25.0f-α §9)

**1. Phase 25 framing.** Phase 25 is the entry-side return on alternative admissible feature classes (F1-F6) layered on the 25.0a-β path-quality dataset. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.

**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.

**3. γ closure preservation.** Phase 24 γ hard-close (PR #279) is unmodified.

**4. Production-readiness preservation.** X-v2 OOS gating remains required before any production deployment.

**5. NG#10 / NG#11 not relaxed.**

**6. F5 verdict scoping.** The 25.0f-β verdict applies only to the F5 best cell on the 25.0a-β-spread dataset. F5 is the LAST feature-axis attempt within Phase 25. F5 H4 FAIL strongly supports definitive feature-axis stop; next recommended routing consideration is R5 (soft close) or R2 (label redesign), but the user still chooses.

## Production-misuse guards (verbatim per 25.0f-α §5.1)

**GUARD 1 — research-not-production**: F5 features stay in scripts/; not auto-routed to feature_service.py.

**GUARD 2 — threshold-sweep-diagnostic**: any threshold sweep here is diagnostic-only.

**GUARD 3 — directional-comparison-diagnostic**: any long/short decomposition is diagnostic-only.

## Causality / leakage notes

F5 features at signal_ts=t use only bars strictly before t (bars ≤ t-1). All spread / volume / joint series go through `shift(1)` before any rolling aggregation. Bar-t lookahead unit tests cover F5-a, F5-b, F5-c.

**F5-c regime tercile thresholds are FIT ON TRAIN SPLIT ONLY** and applied to val/test (no full-sample qcut). spread_z and volume_z tercile cutoffs come from the train portion of the chronological 70/15/15 split per cell.

**F5-a spread basis**: 25.0a-β `spread_at_signal_pip` column (pip-normalised, signal-bar M5 spread). Values are dedup'd by (pair, signal_ts) then `shift(1)` is applied before rolling stats.

## Volume pre-flight (§2.5.1 binding contract)

| pair | m1_rows | non-null fraction | m1 vol min/mean/max | m5_sum_rows |
|---|---|---|---|---|
| AUD_CAD | 732062 | 1.000000 | 1 / 34.81 / 913 | 210241 |
| AUD_JPY | 741663 | 1.000000 | 1 / 115.74 / 1044 | 210241 |
| AUD_NZD | 738189 | 1.000000 | 1 / 73.37 / 915 | 210241 |
| AUD_USD | 737087 | 1.000000 | 1 / 59.68 / 2700 | 210241 |
| CHF_JPY | 735552 | 1.000000 | 1 / 80.36 / 1041 | 210241 |
| EUR_AUD | 741957 | 1.000000 | 1 / 128.45 / 1062 | 210241 |
| EUR_CAD | 740629 | 1.000000 | 1 / 92.20 / 1043 | 210241 |
| EUR_CHF | 737398 | 1.000000 | 1 / 49.08 / 1001 | 210241 |
| EUR_GBP | 734979 | 1.000000 | 1 / 42.88 / 932 | 210241 |
| EUR_JPY | 740735 | 1.000000 | 1 / 167.79 / 1100 | 210241 |
| EUR_USD | 740264 | 1.000000 | 1 / 99.93 / 2888 | 210241 |
| GBP_AUD | 740045 | 1.000000 | 1 / 120.53 / 1046 | 210241 |
| GBP_CHF | 736762 | 1.000000 | 1 / 71.60 / 1002 | 210241 |
| GBP_JPY | 742493 | 1.000000 | 1 / 177.06 / 1085 | 210241 |
| GBP_USD | 740908 | 1.000000 | 1 / 140.29 / 3793 | 210241 |
| NZD_JPY | 736025 | 1.000000 | 1 / 60.87 / 977 | 210241 |
| NZD_USD | 735593 | 1.000000 | 1 / 54.47 / 1901 | 210241 |
| USD_CAD | 739566 | 1.000000 | 1 / 90.27 / 2752 | 210241 |
| USD_CHF | 737060 | 1.000000 | 1 / 55.22 / 3929 | 210241 |
| USD_JPY | 740393 | 1.000000 | 1 / 188.62 / 3397 | 210241 |

All pairs met the binding contract: non-null ≥ 0.99, no negatives, monotonic indices.

## Realised barrier PnL methodology

Final test 8-gate evaluation uses **realised barrier PnL** computed by re-traversing M1 paths with 25.0a barrier semantics (favourable barrier → +K_FAV × ATR; adverse barrier → -K_ADV × ATR; same-bar both-hit → adverse first; horizon expiry → mark-to-market). Validation threshold selection uses synthesized PnL proxy for speed.

## H3 reference (binding from 25.0f-α §4.1)

- best-of-{F1, F2, F3} test AUC = 0.5644 (F1 rank-1 = 0.5644; F2 rank-1 = 0.5613; F3 rank-1 = 0.5480)
- H3 PASS threshold = 0.5744 (lift ≥ 0.01)

## Split dates

- min: 2024-04-30 14:10:00+00:00
- train < 2025-09-23 12:11:00+00:00
- val [2025-09-23 12:11:00+00:00, 2026-01-10 23:45:30+00:00)
- test [2026-01-10 23:45:30+00:00, 2026-04-30 11:20:00+00:00]

## Feature NaN drop (lookback warmup)

- overall drop count: 1292; rate: 0.0003

Per-pair feature NaN drop:

| pair | drop_count | drop_rate |
|---|---|---|
| AUD_CAD | 40 | 0.0003 |
| AUD_JPY | 40 | 0.0002 |
| AUD_NZD | 40 | 0.0007 |
| AUD_USD | 40 | 0.0002 |
| CHF_JPY | 520 | 0.0024 |
| EUR_AUD | 40 | 0.0002 |
| EUR_CAD | 40 | 0.0002 |
| EUR_CHF | 40 | 0.0003 |
| EUR_GBP | 40 | 0.0003 |
| EUR_JPY | 40 | 0.0002 |
| EUR_USD | 52 | 0.0002 |
| GBP_AUD | 40 | 0.0002 |
| GBP_CHF | 40 | 0.0003 |
| GBP_JPY | 40 | 0.0002 |
| GBP_USD | 40 | 0.0002 |
| NZD_JPY | 40 | 0.0002 |
| NZD_USD | 40 | 0.0002 |
| USD_CAD | 40 | 0.0002 |
| USD_CHF | 40 | 0.0002 |
| USD_JPY | 40 | 0.0001 |

## All 21 cells — summary (sorted by test AUC desc)

| subgroup | lookback | n_train | n_test | train_AUC | val_AUC | test_AUC | gap | verdict | h_state | n_trades | sharpe | ann_pnl | A4 | A5_ann | low_power |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F5a_F5b_F5c | 100 | 2937020 | 597270 | 0.5714 | 0.5741 | 0.5672 | 0.0042 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 280100 | -0.3672 | -2286727.7 | 0 | -2753880.8 | no |
| F5b_F5c | 100 | 2937020 | 597270 | 0.5714 | 0.5740 | 0.5670 | 0.0044 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 280558 | -0.3678 | -2293594.7 | 0 | -2761511.6 | no |
| F5a_F5b | 100 | 2937020 | 597270 | 0.5709 | 0.5729 | 0.5665 | 0.0044 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 283636 | -0.3690 | -2319774.8 | 0 | -2792825.3 | no |
| F5b | 100 | 2937020 | 597270 | 0.5705 | 0.5733 | 0.5661 | 0.0045 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 284270 | -0.3700 | -2329936.1 | 0 | -2804044.0 | no |
| F5a_F5c | 100 | 2937020 | 597270 | 0.5697 | 0.5726 | 0.5654 | 0.0043 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 280405 | -0.3674 | -2289191.4 | 0 | -2756853.2 | no |
| F5c | 100 | 2937020 | 597270 | 0.5697 | 0.5726 | 0.5652 | 0.0045 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 281800 | -0.3679 | -2300354.8 | 0 | -2770343.1 | no |
| F5a_F5b_F5c | 50 | 2937020 | 597270 | 0.5640 | 0.5684 | 0.5611 | 0.0029 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 285067 | -0.3696 | -2330015.3 | 0 | -2805452.3 | no |
| F5b_F5c | 50 | 2937020 | 597270 | 0.5639 | 0.5683 | 0.5608 | 0.0031 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 285331 | -0.3699 | -2334158.3 | 0 | -2810035.7 | no |
| F5a_F5b | 50 | 2937020 | 597270 | 0.5635 | 0.5677 | 0.5603 | 0.0032 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 285532 | -0.3704 | -2338415.5 | 0 | -2814628.1 | no |
| F5b | 50 | 2937020 | 597270 | 0.5633 | 0.5680 | 0.5600 | 0.0033 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 285906 | -0.3707 | -2342222.5 | 0 | -2819058.9 | no |
| F5a_F5c | 50 | 2937020 | 597270 | 0.5629 | 0.5672 | 0.5598 | 0.0031 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 284958 | -0.3694 | -2328412.0 | 0 | -2803667.3 | no |
| F5c | 50 | 2937020 | 597270 | 0.5629 | 0.5672 | 0.5596 | 0.0032 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 285518 | -0.3699 | -2334845.5 | 0 | -2811034.8 | no |
| F5a_F5b_F5c | 20 | 2937020 | 597270 | 0.5542 | 0.5584 | 0.5517 | 0.0025 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 287002 | -0.3710 | -2349218.8 | 0 | -2827883.1 | no |
| F5a_F5c | 20 | 2937020 | 597270 | 0.5540 | 0.5580 | 0.5516 | 0.0024 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 287080 | -0.3711 | -2349823.3 | 0 | -2828617.7 | no |
| F5b_F5c | 20 | 2937020 | 597270 | 0.5542 | 0.5584 | 0.5515 | 0.0027 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 287069 | -0.3711 | -2349782.2 | 0 | -2828558.2 | no |
| F5c | 20 | 2937020 | 597270 | 0.5540 | 0.5580 | 0.5514 | 0.0025 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 287089 | -0.3711 | -2350133.2 | 0 | -2828942.6 | no |
| F5a_F5b | 20 | 2937020 | 597270 | 0.5534 | 0.5579 | 0.5506 | 0.0029 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 288413 | -0.3716 | -2361405.4 | 0 | -2842422.9 | no |
| F5b | 20 | 2937020 | 597270 | 0.5533 | 0.5580 | 0.5505 | 0.0029 | REJECT_BUT_INFORMATIVE | H1_PASS_H2_FAIL | 287658 | -0.3713 | -2354311.3 | 0 | -2834069.7 | no |
| F5a | 100 | 2937020 | 597270 | 0.5490 | 0.5519 | 0.5449 | 0.0041 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 290713 | -0.3719 | -2378216.7 | 0 | -2863070.3 | no |
| F5a | 50 | 2939020 | 597270 | 0.5483 | 0.5519 | 0.5443 | 0.0040 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 291431 | -0.3722 | -2385104.7 | 0 | -2871155.7 | no |
| F5a | 20 | 2940220 | 597666 | 0.5479 | 0.5517 | 0.5439 | 0.0041 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 291913 | -0.3723 | -2389518.7 | 0 | -2876373.6 | no |

## Top-3 cells by test AUC — expanded breakdown

### Cell: subgroup=F5a_F5b_F5c, lookback=100

- n_train: 2937020, n_val: 516888, n_test: 597270
- train AUC: 0.5714, val AUC: 0.5741, test AUC: 0.5672, gap: 0.0042
- threshold selected on validation: 0.4
- realised: n_trades=280100, sharpe=-0.3672, ann_pnl=-2286727.7, max_dd=685570.4, A4 pos=0/4, A5 stress ann_pnl=-2753880.8
- proxy: n_trades=280100, sharpe=-0.4542, ann_pnl=-2825100.9
- gates: A0=OK A1=x A2=x A3=x A4=x A5=x
- calibration decile: monotonic=True, overall_brier=0.2465, low_n_flag=False
- verdict: **REJECT_BUT_INFORMATIVE** (H1_PASS_H2_FAIL)
- by-pair trade count: {'EUR_USD': 17939, 'GBP_USD': 18494, 'AUD_USD': 19456, 'NZD_USD': 17044, 'USD_CHF': 15976, 'USD_CAD': 14862, 'EUR_GBP': 8807, 'USD_JPY': 21075, 'EUR_JPY': 18397, 'GBP_JPY': 18343, 'AUD_JPY': 19373, 'NZD_JPY': 13272, 'CHF_JPY': 14385, 'EUR_CHF': 8824, 'EUR_AUD': 14664, 'EUR_CAD': 10904, 'AUD_NZD': 651, 'AUD_CAD': 8015, 'GBP_AUD': 10765, 'GBP_CHF': 8854}
- by-direction trade count: {'long': 280100, 'short': 0}
- features: f5a_spread_z_100, f5b_volume_z_100, f5c_spread_x_volume_100, f5c_high_spread_high_vol_100, f5c_high_spread_low_vol_100, f5c_low_spread_high_vol_100, f5c_regime_100_0, f5c_regime_100_1, f5c_regime_100_2, f5c_regime_100_3, f5c_regime_100_4, f5c_regime_100_5, f5c_regime_100_6, f5c_regime_100_7, f5c_regime_100_8

### Cell: subgroup=F5b_F5c, lookback=100

- n_train: 2937020, n_val: 516888, n_test: 597270
- train AUC: 0.5714, val AUC: 0.5740, test AUC: 0.5670, gap: 0.0044
- threshold selected on validation: 0.4
- realised: n_trades=280558, sharpe=-0.3678, ann_pnl=-2293594.7, max_dd=687629.0, A4 pos=0/4, A5 stress ann_pnl=-2761511.6
- proxy: n_trades=280558, sharpe=-0.4551, ann_pnl=-2834495.1
- gates: A0=OK A1=x A2=x A3=x A4=x A5=x
- calibration decile: monotonic=True, overall_brier=0.2465, low_n_flag=False
- verdict: **REJECT_BUT_INFORMATIVE** (H1_PASS_H2_FAIL)
- by-pair trade count: {'EUR_USD': 17990, 'GBP_USD': 18518, 'AUD_USD': 19388, 'NZD_USD': 17052, 'USD_CHF': 15977, 'USD_CAD': 14862, 'EUR_GBP': 8781, 'USD_JPY': 21075, 'EUR_JPY': 18408, 'GBP_JPY': 18410, 'AUD_JPY': 19423, 'NZD_JPY': 13414, 'CHF_JPY': 14392, 'EUR_CHF': 8817, 'EUR_AUD': 14664, 'EUR_CAD': 10908, 'AUD_NZD': 633, 'AUD_CAD': 8190, 'GBP_AUD': 10766, 'GBP_CHF': 8890}
- by-direction trade count: {'long': 280558, 'short': 0}
- features: f5b_volume_z_100, f5c_spread_x_volume_100, f5c_high_spread_high_vol_100, f5c_high_spread_low_vol_100, f5c_low_spread_high_vol_100, f5c_regime_100_0, f5c_regime_100_1, f5c_regime_100_2, f5c_regime_100_3, f5c_regime_100_4, f5c_regime_100_5, f5c_regime_100_6, f5c_regime_100_7, f5c_regime_100_8

### Cell: subgroup=F5a_F5b, lookback=100

- n_train: 2937020, n_val: 516888, n_test: 597270
- train AUC: 0.5709, val AUC: 0.5729, test AUC: 0.5665, gap: 0.0044
- threshold selected on validation: 0.4
- realised: n_trades=283636, sharpe=-0.3690, ann_pnl=-2319774.8, max_dd=695477.7, A4 pos=0/4, A5 stress ann_pnl=-2792825.3
- proxy: n_trades=283636, sharpe=-0.4565, ann_pnl=-2865750.6
- gates: A0=OK A1=x A2=x A3=x A4=x A5=x
- calibration decile: monotonic=True, overall_brier=0.2467, low_n_flag=False
- verdict: **REJECT_BUT_INFORMATIVE** (H1_PASS_H2_FAIL)
- by-pair trade count: {'EUR_USD': 18006, 'GBP_USD': 18743, 'AUD_USD': 19870, 'NZD_USD': 17405, 'USD_CHF': 16486, 'USD_CAD': 15299, 'EUR_GBP': 9692, 'USD_JPY': 21075, 'EUR_JPY': 18407, 'GBP_JPY': 18441, 'AUD_JPY': 19510, 'NZD_JPY': 13640, 'CHF_JPY': 14672, 'EUR_CHF': 8976, 'EUR_AUD': 15089, 'EUR_CAD': 11027, 'AUD_NZD': 678, 'AUD_CAD': 6486, 'GBP_AUD': 11064, 'GBP_CHF': 9070}
- by-direction trade count: {'long': 283636, 'short': 0}
- features: f5a_spread_z_100, f5b_volume_z_100

## Best-cell decile reliability table (diagnostic-only)

n=597270, monotonic=True, overall_brier=0.2465, low_n_flag=False

| bucket | n | p_hat_mean | realised_win_rate | brier |
|---|---|---|---|---|
| 0 | 59727 | 0.3782 | 0.1229 | 0.1730 |
| 1 | 59727 | 0.4282 | 0.1437 | 0.2041 |
| 2 | 59727 | 0.4520 | 0.1529 | 0.2189 |
| 3 | 59727 | 0.4722 | 0.1625 | 0.2320 |
| 4 | 59727 | 0.4870 | 0.1651 | 0.2415 |
| 5 | 59727 | 0.5034 | 0.1867 | 0.2521 |
| 6 | 59727 | 0.5216 | 0.1959 | 0.2636 |
| 7 | 59727 | 0.5390 | 0.2016 | 0.2748 |
| 8 | 59727 | 0.5612 | 0.2181 | 0.2882 |
| 9 | 59727 | 0.6066 | 0.2402 | 0.3167 |

## Aggregate H1 / H2 / H3 / H4 outcome

- Best F5 cell: **{'subgroup': 'F5a_F5b_F5c', 'lookback': 100}** with test AUC 0.5672
- H1 PASS threshold = 0.5500; H1 PASS at best cell: True
- H2 (A1 Sharpe ≥ 0.082 AND A2 ann_pnl ≥ 180.0) at best cell: **False** (sharpe=-0.3672, ann_pnl=-2286727.7)
- H3 (lift ≥ 0.01, threshold ≥ 0.5744): **False** (observed lift = +0.0028)
- H4 (best-cell realised Sharpe ≥ 0): **False** (realised Sharpe = -0.3672)

> H4 FAIL — F5 best-cell realised Sharpe < 0 at AUC ≈ structural-gap regime. This strongly supports definitive feature-axis stop within Phase 25, but the user still chooses (next routing consideration: R5 soft close or R2 label redesign).

## Routing recommendation framing (non-decisive)

This section lists which §7 verdict tree branch the best cell falls into. It is informational. The actual routing decision (R5 soft close / R2 label redesign / continue) is handed to the next PR. **F5 H4 FAIL strongly supports definitive feature-axis stop within Phase 25, but the user still chooses.**

- Best-cell refined verdict: **REJECT_BUT_INFORMATIVE_REDUNDANT**
- Best-cell h_state: H1_PASS_H2_FAIL

## Multiple-testing caveat

These are 21 evaluated cells. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE verdicts are hypothesis-generating ONLY; production-readiness requires an X-v2-equivalent frozen-OOS PR per Phase 22 contract.
