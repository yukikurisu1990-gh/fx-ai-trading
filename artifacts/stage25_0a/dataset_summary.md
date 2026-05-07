# Stage 25.0a-β — Path-Quality Label Dataset Summary

Generated: 2026-05-07T14:29:24.457130+00:00

Design contract: `docs/design/phase25_0a_label_design.md` (PR #281)

## Mandatory clauses

**Design constants are fixed.** K_FAV=1.5, K_ADV=1.0, M_MARGIN=2.0, H_M1_BARS=60 were fixed in 25.0a-α before implementation and MUST NOT be retuned in response to observed label balance. If the dataset is pathological per §12, this script halts and the user decides next steps.

**Causality.** Labels are computed from FUTURE bars [t+1, t+H_M1_BARS] only; features and ATR are computed from PAST bars only. The boundary at signal time t is hard. Same-bar SL-first invariant per PR #276 envelope §3.3.

**Diagnostic columns are not features.** The columns `max_fav_excursion_pip`, `max_adv_excursion_pip`, `time_to_fav_bar`, `time_to_adv_bar`, `same_bar_both_hit` are label-side diagnostic outputs computed from the same future bars as the label. Downstream feature-class evals (25.0b+) MUST NOT use them as model input features — doing so constitutes feature leakage.

**γ closure preservation.** Phase 25.0a does not modify the γ closure declared in PR #279. Phase 25 results, regardless of outcome, do not change Phase 24 / NG#10 β-chain closure status.

## Headline counts

- Total rows emitted: **4056120**
- Total positive labels: 757849
- Overall positive rate: **0.1868**
- Pairs processed: 20 / 20

## Per-pair drop counts

| pair | total_candidates | dropped_no_atr | dropped_no_entry | dropped_path_short | dropped_invalid_spread | dropped_by_margin | rows_emitted |
|---|---|---|---|---|---|---|---|
| EUR_USD | 149134 | 21 | 1136 | 12 | 0 | 35488 | 224954 |
| GBP_USD | 149099 | 21 | 1014 | 12 | 0 | 31359 | 233386 |
| AUD_USD | 149108 | 21 | 1770 | 12 | 0 | 23309 | 247992 |
| NZD_USD | 149098 | 21 | 2169 | 12 | 0 | 40453 | 212886 |
| USD_CHF | 149058 | 21 | 1688 | 12 | 0 | 43000 | 208674 |
| USD_CAD | 149114 | 21 | 1291 | 12 | 0 | 51554 | 192472 |
| EUR_GBP | 149114 | 21 | 2189 | 12 | 0 | 74381 | 145022 |
| USD_JPY | 149103 | 21 | 1146 | 12 | 0 | 8640 | 278568 |
| EUR_JPY | 149089 | 21 | 1073 | 12 | 0 | 16824 | 262318 |
| GBP_JPY | 149104 | 21 | 713 | 12 | 0 | 18272 | 260172 |
| AUD_JPY | 149100 | 21 | 848 | 12 | 0 | 19489 | 257460 |
| NZD_JPY | 148954 | 21 | 1929 | 12 | 0 | 53118 | 187748 |
| CHF_JPY | 148422 | 21 | 1427 | 12 | 0 | 39178 | 215568 |
| EUR_CHF | 149038 | 21 | 1636 | 12 | 0 | 71184 | 152370 |
| EUR_AUD | 149119 | 21 | 812 | 12 | 0 | 35166 | 226216 |
| EUR_CAD | 149131 | 21 | 1123 | 12 | 0 | 55796 | 184358 |
| AUD_NZD | 149052 | 21 | 1553 | 12 | 0 | 117846 | 59240 |
| AUD_CAD | 149013 | 21 | 2723 | 12 | 0 | 72857 | 146800 |
| GBP_AUD | 149045 | 21 | 1137 | 12 | 0 | 47790 | 200170 |
| GBP_CHF | 148804 | 21 | 1553 | 12 | 0 | 67345 | 159746 |

## Rows by pair

| pair | rows |
|---|---|
| AUD_CAD | 146800 |
| AUD_JPY | 257460 |
| AUD_NZD | 59240 |
| AUD_USD | 247992 |
| CHF_JPY | 215568 |
| EUR_AUD | 226216 |
| EUR_CAD | 184358 |
| EUR_CHF | 152370 |
| EUR_GBP | 145022 |
| EUR_JPY | 262318 |
| EUR_USD | 224954 |
| GBP_AUD | 200170 |
| GBP_CHF | 159746 |
| GBP_JPY | 260172 |
| GBP_USD | 233386 |
| NZD_JPY | 187748 |
| NZD_USD | 212886 |
| USD_CAD | 192472 |
| USD_CHF | 208674 |
| USD_JPY | 278568 |

## Rows by direction

| direction | rows |
|---|---|
| long | 2028060 |
| short | 2028060 |

## Positive label rate by pair

| pair | positive_rate |
|---|---|
| AUD_CAD | 0.1451 |
| AUD_JPY | 0.1995 |
| AUD_NZD | 0.1062 |
| AUD_USD | 0.1960 |
| CHF_JPY | 0.1740 |
| EUR_AUD | 0.1794 |
| EUR_CAD | 0.1717 |
| EUR_CHF | 0.1597 |
| EUR_GBP | 0.1542 |
| EUR_JPY | 0.2103 |
| EUR_USD | 0.2029 |
| GBP_AUD | 0.1737 |
| GBP_CHF | 0.1596 |
| GBP_JPY | 0.2034 |
| GBP_USD | 0.2039 |
| NZD_JPY | 0.1599 |
| NZD_USD | 0.1761 |
| USD_CAD | 0.1818 |
| USD_CHF | 0.1889 |
| USD_JPY | 0.2525 |

## Positive label rate by direction

| direction | positive_rate |
|---|---|
| long | 0.1878 |
| short | 0.1859 |

## Margin filter — drop count and rate

- Overall: 923049 / 2980699 = **0.3097**

Per-pair `dropped_by_margin_rate`:

| pair | dropped_by_margin_rate |
|---|---|
| AUD_CAD | 0.4889 |
| AUD_JPY | 0.1307 |
| AUD_NZD | 0.7906 |
| AUD_USD | 0.1563 |
| CHF_JPY | 0.2640 |
| EUR_AUD | 0.2358 |
| EUR_CAD | 0.3741 |
| EUR_CHF | 0.4776 |
| EUR_GBP | 0.4988 |
| EUR_JPY | 0.1128 |
| EUR_USD | 0.2380 |
| GBP_AUD | 0.3206 |
| GBP_CHF | 0.4526 |
| GBP_JPY | 0.1225 |
| GBP_USD | 0.2103 |
| NZD_JPY | 0.3566 |
| NZD_USD | 0.2713 |
| USD_CAD | 0.3457 |
| USD_CHF | 0.2885 |
| USD_JPY | 0.0579 |

## Same-bar both-hit count and rate

- count: 2688
- rate (per emitted row): 0.0007

## Distribution: time_to_fav_bar (resolved rows only; -1 excluded)

- count: 1375817, mean: 27.5256, median: 26.0000, p25: 14.0000, p75: 40.0000, p95: 55.0000, max: 59.0000

## Distribution: time_to_adv_bar (resolved rows only; -1 excluded)

- count: 3168847, mean: 10.7893, median: 5.0000, p25: 2.0000, p75: 15.0000, p95: 42.0000, max: 59.0000

## Distribution: atr_at_signal_pip

- count: 4056120, mean: 5.8076, median: 4.9250, p25: 3.4050, p75: 7.1250, p95: 12.1700, max: 85.3325

## Distribution: spread_at_signal_pip

- count: 4056120, mean: 2.2307, median: 2.0000, p25: 1.6000, p75: 2.7000, p95: 3.9000, max: 35.6000

## Pathological balance check

- overall_positive_rate: 0.1868408725580111
- overall_low_breach (< 0.05): False
- overall_high_breach (> 0.6): False
- per_pair_low_breaches (< 0.02): []
- per_pair_high_dropped_by_margin (> 0.8): []

**Final flag: PASS**
