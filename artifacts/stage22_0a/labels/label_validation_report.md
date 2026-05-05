# Stage 22.0a Scalp Label Validation Report

Generated: 2026-05-05T06:15:06.218113+00:00

Design contract: `docs/design/phase22_0a_scalp_label_design.md`

## Hard ADOPT criteria

- H1 (all 20 pair × 4 horizon × 2 dir rows generated): **PASS**
- H2 (bid/ask separated entry/exit correct): **verified by unit tests**
- H3 (look-ahead bias sanity): **verified by unit tests**
- H4 (tail horizon_bars rows valid_label=False per (pair, horizon)): **PASS**
- H5 (gap_affected_forward_window flagged): **verified by unit tests**
- H6 (same_bar_tp_sl_ambiguous flagged): **verified by unit tests**
- H7 (median of per-pair median cost_ratio = 1.385 vs 22.0z-1 ~1.28 ±0.15; per-pair range [0.673, 2.375], structural finding ~67%–~237% reproduced): **PASS**
- H8 (schema reusable in 22.0b/22.0c): **verified by unit tests (pivot)**

## Per-pair summary

| pair | bars | rows | valid | cost_ratio p10 | p50 | p90 | H7 in-band? |
|---|---|---|---|---|---|---|---|
| AUD_CAD | 732062 | 5856496 | 5856234 | 1.007 | 1.854 | 3.640 | ✗ |
| AUD_JPY | 741663 | 5933304 | 5933042 | 0.542 | 1.035 | 2.123 | ✗ |
| AUD_NZD | 738189 | 5905512 | 5905250 | 1.419 | 2.375 | 3.933 | ✗ |
| AUD_USD | 737087 | 5896696 | 5896434 | 0.629 | 1.199 | 2.464 | ✓ |
| CHF_JPY | 735552 | 5884416 | 5884154 | 0.681 | 1.345 | 2.902 | ✓ |
| EUR_AUD | 741957 | 5935656 | 5935394 | 0.667 | 1.270 | 2.638 | ✓ |
| EUR_CAD | 740629 | 5925032 | 5924770 | 0.697 | 1.455 | 3.170 | ✗ |
| EUR_CHF | 737398 | 5899184 | 5898922 | 0.845 | 1.806 | 4.068 | ✗ |
| EUR_GBP | 734979 | 5879832 | 5879570 | 0.931 | 1.867 | 4.261 | ✗ |
| EUR_JPY | 740735 | 5925880 | 5925618 | 0.432 | 0.905 | 1.986 | ✗ |
| EUR_USD | 740264 | 5922112 | 5921850 | 0.574 | 1.206 | 2.917 | ✓ |
| GBP_AUD | 740045 | 5920360 | 5920098 | 0.655 | 1.359 | 2.954 | ✓ |
| GBP_CHF | 736762 | 5894096 | 5893834 | 0.835 | 1.717 | 3.930 | ✗ |
| GBP_JPY | 742493 | 5939944 | 5939682 | 0.506 | 0.969 | 2.132 | ✗ |
| GBP_USD | 740908 | 5927264 | 5927002 | 0.573 | 1.125 | 2.705 | ✗ |
| NZD_JPY | 736025 | 5888200 | 5887938 | 0.866 | 1.591 | 3.173 | ✗ |
| NZD_USD | 735593 | 5884744 | 5884482 | 0.814 | 1.483 | 2.947 | ✗ |
| USD_CAD | 739566 | 5916528 | 5916266 | 0.723 | 1.516 | 3.242 | ✗ |
| USD_CHF | 737060 | 5896480 | 5896218 | 0.674 | 1.412 | 3.223 | ✓ |
| USD_JPY | 740393 | 5923144 | 5922882 | 0.341 | 0.673 | 1.583 | ✗ |

## Diagnostic metrics (NOT pass/fail)

### Same-bar TP/SL ambiguity rate (valid rows only)
| pair | long | short |
|---|---|---|
| AUD_CAD | 0.0182 | 0.0182 |
| AUD_JPY | 0.0208 | 0.0239 |
| AUD_NZD | 0.0160 | 0.0170 |
| AUD_USD | 0.0247 | 0.0245 |
| CHF_JPY | 0.0219 | 0.0251 |
| EUR_AUD | 0.0201 | 0.0200 |
| EUR_CAD | 0.0190 | 0.0179 |
| EUR_CHF | 0.0222 | 0.0238 |
| EUR_GBP | 0.0208 | 0.0204 |
| EUR_JPY | 0.0238 | 0.0271 |
| EUR_USD | 0.0277 | 0.0278 |
| GBP_AUD | 0.0162 | 0.0168 |
| GBP_CHF | 0.0166 | 0.0180 |
| GBP_JPY | 0.0231 | 0.0263 |
| GBP_USD | 0.0253 | 0.0256 |
| NZD_JPY | 0.0197 | 0.0225 |
| NZD_USD | 0.0239 | 0.0237 |
| USD_CAD | 0.0258 | 0.0264 |
| USD_CHF | 0.0242 | 0.0263 |
| USD_JPY | 0.0327 | 0.0369 |

### tb_pnl × time_exit_pnl correlation
| pair | corr |
|---|---|
| AUD_CAD | 0.1774 |
| AUD_JPY | 0.2752 |
| AUD_NZD | 0.1505 |
| AUD_USD | 0.2493 |
| CHF_JPY | 0.2338 |
| EUR_AUD | 0.2461 |
| EUR_CAD | 0.2371 |
| EUR_CHF | 0.2193 |
| EUR_GBP | 0.1804 |
| EUR_JPY | 0.3003 |
| EUR_USD | 0.2656 |
| GBP_AUD | 0.2326 |
| GBP_CHF | 0.2279 |
| GBP_JPY | 0.2849 |
| GBP_USD | 0.2615 |
| NZD_JPY | 0.1917 |
| NZD_USD | 0.1927 |
| USD_CAD | 0.2271 |
| USD_CHF | 0.2501 |
| USD_JPY | 0.3241 |

### Path shape class distribution (across valid rows)
| pair | 0 (cont up) | 1 (cont dn) | 2 (rev up) | 3 (rev dn) | 4 (range) |
|---|---|---|---|---|---|
| AUD_CAD | 0.315 | 0.306 | 0.120 | 0.119 | 0.141 |
| AUD_JPY | 0.322 | 0.303 | 0.121 | 0.119 | 0.136 |
| AUD_NZD | 0.312 | 0.303 | 0.120 | 0.119 | 0.147 |
| AUD_USD | 0.317 | 0.307 | 0.117 | 0.116 | 0.142 |
| CHF_JPY | 0.319 | 0.303 | 0.122 | 0.121 | 0.135 |
| EUR_AUD | 0.309 | 0.314 | 0.121 | 0.121 | 0.135 |
| EUR_CAD | 0.314 | 0.307 | 0.121 | 0.120 | 0.139 |
| EUR_CHF | 0.310 | 0.306 | 0.118 | 0.118 | 0.148 |
| EUR_GBP | 0.304 | 0.306 | 0.116 | 0.117 | 0.157 |
| EUR_JPY | 0.323 | 0.301 | 0.122 | 0.120 | 0.135 |
| EUR_USD | 0.318 | 0.309 | 0.117 | 0.117 | 0.139 |
| GBP_AUD | 0.308 | 0.312 | 0.122 | 0.122 | 0.136 |
| GBP_CHF | 0.311 | 0.306 | 0.120 | 0.119 | 0.144 |
| GBP_JPY | 0.323 | 0.301 | 0.123 | 0.120 | 0.133 |
| GBP_USD | 0.316 | 0.310 | 0.118 | 0.117 | 0.138 |
| NZD_JPY | 0.319 | 0.306 | 0.120 | 0.119 | 0.136 |
| NZD_USD | 0.315 | 0.313 | 0.116 | 0.116 | 0.141 |
| USD_CAD | 0.313 | 0.312 | 0.117 | 0.117 | 0.141 |
| USD_CHF | 0.313 | 0.312 | 0.117 | 0.117 | 0.141 |
| USD_JPY | 0.325 | 0.307 | 0.119 | 0.117 | 0.131 |

### Gap-affected forward window rate (all rows)
| pair | gap rate |
|---|---|
| AUD_CAD | 0.0072 |
| AUD_JPY | 0.0034 |
| AUD_NZD | 0.0054 |
| AUD_USD | 0.0064 |
| CHF_JPY | 0.0077 |
| EUR_AUD | 0.0032 |
| EUR_CAD | 0.0038 |
| EUR_CHF | 0.0063 |
| EUR_GBP | 0.0055 |
| EUR_JPY | 0.0044 |
| EUR_USD | 0.0043 |
| GBP_AUD | 0.0046 |
| GBP_CHF | 0.0065 |
| GBP_JPY | 0.0033 |
| GBP_USD | 0.0043 |
| NZD_JPY | 0.0058 |
| NZD_USD | 0.0075 |
| USD_CAD | 0.0048 |
| USD_CHF | 0.0056 |
| USD_JPY | 0.0044 |

## NG list compliance

- NG#1 pair filter: 20-pair universe in output ✓
- NG#2 train-side time filter: no filter applied; context flags are informational ✓
- NG#3 test-side filter improvement claim: PR2 records outcomes, no strategy PnL claim ✓
- NG#4 WeekOpen-aware sample weighting: no weighting ✓
- NG#5 Universe-restricted cross-pair feature: no restriction ✓
