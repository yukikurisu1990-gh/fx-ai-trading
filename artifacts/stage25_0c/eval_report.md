# Stage 25.0c-β — F2 Multi-Timeframe Volatility Regime Eval

Generated: 2026-05-08T15:25:57.593940+00:00

Design contract: `docs/design/phase25_0c_f2_design.md` (PR #286)

## Mandatory clauses

**1. Phase 25 framing.** Phase 25 is not a hyperparameter-tuning phase. It is a label-and-feature-class redesign phase. Novelty must come from input feature class and label design.

**2. F2 negative list (binding).** F2 features are CATEGORICAL multi-TF volatility regime tags. F2 is NOT continuous vol-derivative magnitudes (that's F1, REJECT_BUT_INFORMATIVE per PR #284). Raw RV, raw expansion ratio, raw vol-of-vol, raw range compression score are PROHIBITED as direct model features. f2_e (return sign) is secondary directional context only.

**3. Diagnostic columns are not features.** The 25.0a-β diagnostic columns MUST NOT appear in any model's feature matrix.

**4. Causality and split discipline.** All f2 features use shift(1).rolling pattern. Train / val / test splits are strictly chronological (70/15/15). Threshold selection uses VALIDATION ONLY; test set is touched once.

**5. γ closure preservation.** Phase 25.0c does not modify the γ closure (PR #279).

**6. Production-readiness preservation.** PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE in 25.0c are hypothesis-generating only. Production-readiness requires X-v2-equivalent frozen-OOS PR.

**Test-touched-once invariant**: threshold selected on validation only; test set touched once.

## Realised barrier PnL methodology (inherited from 25.0b-β)

Final test 8-gate evaluation uses realised barrier PnL via M1 path re-traverse with 25.0a barrier semantics:
- favourable barrier first → +K_FAV × ATR
- adverse barrier first → −K_ADV × ATR
- same-bar both-hit → adverse first → −K_ADV × ATR
- horizon expiry → mark-to-market

Validation threshold selection uses synthesized PnL proxy (±K_FAV/K_ADV × ATR by label).

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

## All 18 cells — summary (sorted by test AUC desc)

| trailing | rep | admissibility | n_train | n_test | pt% (test) | train_AUC | val_AUC | test_AUC | gap | verdict | n_trades | sharpe | ann_pnl | low_power |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 200 | per_tf_only | none | 2889806 | 591004 | 1.000 | 0.5660 | 0.5703 | 0.5613 | 0.0047 | REJECT_BUT_INFORMATIVE | 280763 | -0.3696 | -2309569.5 | no |
| 200 | per_tf_joint | none | 2889806 | 591004 | 1.000 | 0.5660 | 0.5703 | 0.5612 | 0.0048 | REJECT_BUT_INFORMATIVE | 280073 | -0.3693 | -2303667.2 | no |
| 200 | all | none | 2889806 | 591004 | 1.000 | 0.5661 | 0.5702 | 0.5611 | 0.0050 | REJECT_BUT_INFORMATIVE | 280081 | -0.3693 | -2303836.2 | no |
| 200 | per_tf_joint | transition | 950234 | 197162 | 0.334 | 0.5656 | 0.5695 | 0.5603 | 0.0053 | REJECT_BUT_INFORMATIVE | 93056 | -0.3821 | -770231.8 | no |
| 200 | all | transition | 950234 | 197162 | 0.334 | 0.5658 | 0.5691 | 0.5601 | 0.0057 | REJECT_BUT_INFORMATIVE | 93023 | -0.3821 | -770116.6 | no |
| 200 | per_tf_only | transition | 950234 | 197162 | 0.334 | 0.5654 | 0.5695 | 0.5599 | 0.0056 | REJECT_BUT_INFORMATIVE | 93089 | -0.3822 | -770602.4 | no |
| 100 | per_tf_only | none | 2910530 | 596856 | 1.000 | 0.5613 | 0.5653 | 0.5568 | 0.0046 | REJECT_BUT_INFORMATIVE | 285091 | -0.3703 | -2338568.4 | no |
| 100 | per_tf_joint | none | 2910530 | 596856 | 1.000 | 0.5614 | 0.5652 | 0.5566 | 0.0047 | REJECT_BUT_INFORMATIVE | 284652 | -0.3702 | -2335927.2 | no |
| 100 | all | none | 2910530 | 596856 | 1.000 | 0.5615 | 0.5652 | 0.5566 | 0.0049 | REJECT_BUT_INFORMATIVE | 284744 | -0.3703 | -2336316.3 | no |
| 200 | all | high_alignment | 1158524 | 247276 | 0.418 | 0.5543 | 0.5609 | 0.5563 | -0.0021 | REJECT_BUT_INFORMATIVE | 116557 | -0.3170 | -996122.6 | no |
| 200 | per_tf_joint | high_alignment | 1158524 | 247276 | 0.418 | 0.5540 | 0.5612 | 0.5563 | -0.0023 | REJECT_BUT_INFORMATIVE | 116621 | -0.3171 | -996754.7 | no |
| 200 | per_tf_only | high_alignment | 1158524 | 247276 | 0.418 | 0.5540 | 0.5612 | 0.5563 | -0.0023 | REJECT_BUT_INFORMATIVE | 116621 | -0.3171 | -996754.7 | no |
| 100 | all | transition | 1032950 | 214508 | 0.359 | 0.5617 | 0.5632 | 0.5562 | 0.0055 | REJECT_BUT_INFORMATIVE | 102403 | -0.3838 | -848148.7 | no |
| 100 | per_tf_joint | transition | 1032950 | 214508 | 0.359 | 0.5616 | 0.5634 | 0.5562 | 0.0053 | REJECT_BUT_INFORMATIVE | 102406 | -0.3838 | -848093.1 | no |
| 100 | per_tf_only | transition | 1032950 | 214508 | 0.359 | 0.5614 | 0.5635 | 0.5562 | 0.0053 | REJECT_BUT_INFORMATIVE | 102473 | -0.3837 | -848282.8 | no |
| 100 | per_tf_only | high_alignment | 1108806 | 238138 | 0.399 | 0.5525 | 0.5590 | 0.5544 | -0.0019 | REJECT_BUT_INFORMATIVE | 113254 | -0.3210 | -960862.9 | no |
| 100 | per_tf_joint | high_alignment | 1108806 | 238138 | 0.399 | 0.5525 | 0.5590 | 0.5543 | -0.0018 | REJECT_BUT_INFORMATIVE | 113253 | -0.3217 | -971701.4 | no |
| 100 | all | high_alignment | 1108806 | 238138 | 0.399 | 0.5527 | 0.5591 | 0.5543 | -0.0016 | REJECT_BUT_INFORMATIVE | 113141 | -0.3211 | -960320.0 | no |

## Top-3 cells by test AUC — expanded breakdown

### Cell: trailing=200, rep=per_tf_only, adm=none

- n_train: 2889806, n_val: 502486, n_test: 591004
- pass-through (train/val/test): 1.000 / 1.000 / 1.000
- train AUC: 0.5660, val AUC: 0.5703, test AUC: 0.5613, gap: 0.0047
- threshold selected on validation: 0.4
- realised: n_trades=280763, sharpe=-0.3696, ann_pnl=-2309569.5, max_dd=692394.7, A4 pos=0/4, A5 stress ann_pnl=-2777828.3
- proxy: n_trades=280763, sharpe=-0.4584, ann_pnl=-2859956.0
- gates: A0=OK A1=x A2=x A3=x A4=x A5=x
- calibration: monotonic=True, brier=0.2479
- verdict: **REJECT_BUT_INFORMATIVE** (H1_PASS_H2_FAIL)
- by-pair trade count: {'EUR_USD': 17788, 'GBP_USD': 18514, 'AUD_USD': 19680, 'NZD_USD': 16937, 'USD_CHF': 16269, 'USD_CAD': 15174, 'EUR_GBP': 9514, 'USD_JPY': 20803, 'EUR_JPY': 18367, 'GBP_JPY': 18220, 'AUD_JPY': 19299, 'NZD_JPY': 12524, 'CHF_JPY': 14556, 'EUR_CHF': 8817, 'EUR_AUD': 14987, 'EUR_CAD': 10879, 'AUD_CAD': 8294, 'GBP_AUD': 11077, 'GBP_CHF': 9064}
- by-direction trade count: {'long': 280763, 'short': 0}

### Cell: trailing=200, rep=per_tf_joint, adm=none

- n_train: 2889806, n_val: 502486, n_test: 591004
- pass-through (train/val/test): 1.000 / 1.000 / 1.000
- train AUC: 0.5660, val AUC: 0.5703, test AUC: 0.5612, gap: 0.0048
- threshold selected on validation: 0.4
- realised: n_trades=280073, sharpe=-0.3693, ann_pnl=-2303667.2, max_dd=690625.2, A4 pos=0/4, A5 stress ann_pnl=-2770775.3
- proxy: n_trades=280073, sharpe=-0.4581, ann_pnl=-2853527.3
- gates: A0=OK A1=x A2=x A3=x A4=x A5=x
- calibration: monotonic=True, brier=0.2479
- verdict: **REJECT_BUT_INFORMATIVE** (H1_PASS_H2_FAIL)
- by-pair trade count: {'EUR_USD': 17788, 'GBP_USD': 18514, 'AUD_USD': 19680, 'NZD_USD': 16526, 'USD_CHF': 16269, 'USD_CAD': 15008, 'EUR_GBP': 9584, 'USD_JPY': 20803, 'EUR_JPY': 18367, 'GBP_JPY': 18220, 'AUD_JPY': 19299, 'NZD_JPY': 12603, 'CHF_JPY': 14327, 'EUR_CHF': 8844, 'EUR_AUD': 14987, 'EUR_CAD': 10797, 'AUD_CAD': 8294, 'GBP_AUD': 11077, 'GBP_CHF': 9086}
- by-direction trade count: {'long': 280073, 'short': 0}

### Cell: trailing=200, rep=all, adm=none

- n_train: 2889806, n_val: 502486, n_test: 591004
- pass-through (train/val/test): 1.000 / 1.000 / 1.000
- train AUC: 0.5661, val AUC: 0.5702, test AUC: 0.5611, gap: 0.0050
- threshold selected on validation: 0.4
- realised: n_trades=280081, sharpe=-0.3693, ann_pnl=-2303836.2, max_dd=690675.9, A4 pos=0/4, A5 stress ann_pnl=-2770957.6
- proxy: n_trades=280081, sharpe=-0.4581, ann_pnl=-2853622.2
- gates: A0=OK A1=x A2=x A3=x A4=x A5=x
- calibration: monotonic=True, brier=0.2480
- verdict: **REJECT_BUT_INFORMATIVE** (H1_PASS_H2_FAIL)
- by-pair trade count: {'EUR_USD': 17788, 'GBP_USD': 18514, 'AUD_USD': 19680, 'NZD_USD': 16541, 'USD_CHF': 16258, 'USD_CAD': 15013, 'EUR_GBP': 9566, 'USD_JPY': 20803, 'EUR_JPY': 18367, 'GBP_JPY': 18220, 'AUD_JPY': 19299, 'NZD_JPY': 12590, 'CHF_JPY': 14345, 'EUR_CHF': 8849, 'EUR_AUD': 14987, 'EUR_CAD': 10817, 'AUD_CAD': 8319, 'GBP_AUD': 11040, 'GBP_CHF': 9085}
- by-direction trade count: {'long': 280081, 'short': 0}

## Top-3 cells by realised Sharpe — compact

| trailing | rep | admissibility | sharpe | ann_pnl | n_trades | verdict |
|---|---|---|---|---|---|---|
| 200 | all | high_alignment | -0.3170 | -996122.6 | 116557 | REJECT_BUT_INFORMATIVE |
| 200 | per_tf_only | high_alignment | -0.3171 | -996754.7 | 116621 | REJECT_BUT_INFORMATIVE |
| 200 | per_tf_joint | high_alignment | -0.3171 | -996754.7 | 116621 | REJECT_BUT_INFORMATIVE |

## Per-cell admissibility pass-through rate

| trailing | rep | admissibility | pt_train | pt_val | pt_test |
|---|---|---|---|---|---|
| 100 | per_tf_only | none | 1.000 | 1.000 | 1.000 |
| 100 | per_tf_only | high_alignment | 0.381 | 0.424 | 0.399 |
| 100 | per_tf_only | transition | 0.355 | 0.368 | 0.359 |
| 100 | per_tf_joint | none | 1.000 | 1.000 | 1.000 |
| 100 | per_tf_joint | high_alignment | 0.381 | 0.424 | 0.399 |
| 100 | per_tf_joint | transition | 0.355 | 0.368 | 0.359 |
| 100 | all | none | 1.000 | 1.000 | 1.000 |
| 100 | all | high_alignment | 0.381 | 0.424 | 0.399 |
| 100 | all | transition | 0.355 | 0.368 | 0.359 |
| 200 | per_tf_only | none | 1.000 | 1.000 | 1.000 |
| 200 | per_tf_only | high_alignment | 0.401 | 0.456 | 0.418 |
| 200 | per_tf_only | transition | 0.329 | 0.341 | 0.334 |
| 200 | per_tf_joint | none | 1.000 | 1.000 | 1.000 |
| 200 | per_tf_joint | high_alignment | 0.401 | 0.456 | 0.418 |
| 200 | per_tf_joint | transition | 0.329 | 0.341 | 0.334 |
| 200 | all | none | 1.000 | 1.000 | 1.000 |
| 200 | all | high_alignment | 0.401 | 0.456 | 0.418 |
| 200 | all | transition | 0.329 | 0.341 | 0.334 |

## Joint regime distribution (train set)

| joint_regime | count | rate | rare (<1%) |
|---|---|---|---|
| high_high_low | 274628 | 0.0944 | no |
| high_high_high | 219902 | 0.0756 | no |
| high_high_med | 196042 | 0.0674 | no |
| high_med_high | 138950 | 0.0477 | no |
| high_med_low | 138744 | 0.0477 | no |
| med_high_high | 135348 | 0.0465 | no |
| low_med_high | 127586 | 0.0438 | no |
| med_med_high | 121378 | 0.0417 | no |
| high_med_med | 118760 | 0.0408 | no |
| med_high_low | 115316 | 0.0396 | no |
| low_low_high | 111050 | 0.0382 | no |
| med_high_med | 97206 | 0.0334 | no |
| med_med_low | 95550 | 0.0328 | no |
| med_med_med | 88224 | 0.0303 | no |
| low_med_low | 87526 | 0.0301 | no |
| low_low_low | 86912 | 0.0299 | no |
| low_med_med | 82552 | 0.0284 | no |
| low_low_med | 80606 | 0.0277 | no |
| low_high_high | 79658 | 0.0274 | no |
| med_low_high | 76536 | 0.0263 | no |
| high_low_low | 68378 | 0.0235 | no |
| low_high_low | 67978 | 0.0234 | no |
| high_low_high | 64278 | 0.0221 | no |
| med_low_low | 63288 | 0.0217 | no |
| med_low_med | 59218 | 0.0203 | no |
| low_high_med | 57644 | 0.0198 | no |
| high_low_med | 57272 | 0.0197 | no |

## 'none' admissibility cell — interpretation

The 'none' admissibility cells use ALL 25.0a-β labels (no regime filter). They are the **full-sample baseline cells** — by design (per 25.0c-α §5), they address F1's sample-size pressure and provide the cleanest test of whether F2's categorical regime features alone produce learnable signal under realistic sample sizes.

## Multiple-testing caveat

These are 18 evaluated cells. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE verdicts are hypothesis-generating ONLY; production-readiness requires an X-v2-equivalent frozen-OOS PR per Phase 22 contract.

## H1 routing summary: 18 / 18 cells PASS H1 (test AUC >= 0.55)
