# Stage 25.0e-β — F3 Cross-Pair / Relative Currency Strength Eval

Generated: 2026-05-09T18:11:12.880190+00:00

Design contract: `docs/design/phase25_0e_alpha_f3_design.md` (PR #292)

## Mandatory clauses (verbatim per 25.0e-α §9)

**1. Phase 25 framing.** Phase 25 is the entry-side return on alternative admissible feature classes (F1-F6) layered on the 25.0a-β path-quality dataset. Each F-class is evaluated as an independent admissible-discriminative experiment. ADOPT requires both H2 PASS and the full 8-gate A1-A5 harness.

**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them. They exist to characterise the AUC-PnL gap, not to monetise it.

**3. γ closure preservation.** Phase 24 γ hard-close (PR #279) is unmodified. No 25.0e PR touches stage24 artifacts or stage24 verdict text.

**4. Production-readiness preservation.** X-v2 OOS gating remains required before any production deployment. No 25.0e PR pre-approves production wiring.

**5. NG#10 / NG#11 not relaxed.** 25.0e PRs do not change the entry-side budget cap or the diagnostic-vs-routing separation rule.

**6. F3 verdict scoping.** The 25.0e-β verdict applies only to the F3 best cell on the 25.0a-β-spread dataset. Convergence with F4-F6 is a separate question; structural-gap inferences are jointly conditional on F3 H4 outcome.

## Production-misuse guards (verbatim per 25.0e-α §5.1)

**GUARD 1 — research-not-production**: F3 features stay in scripts/; not auto-routed to feature_service.py.

**GUARD 2 — threshold-sweep-diagnostic**: any threshold sweep here is diagnostic-only.

**GUARD 3 — directional-comparison-diagnostic**: any long/short decomposition is diagnostic-only.

## Causality and correlation-set notes

F3 features at signal_ts=t use only bars strictly before t (bars ≤ t-1). All cross-pair series go through `shift(1)` before any rolling aggregation; a bar-t lookahead unit test enforces this invariant.

**F3-b uses a predeclared small correlation set; no target-aware pair selection.** The 6 predeclared pairs are: (EUR_USD,GBP_USD), (AUD_USD,NZD_USD), (USD_JPY,USD_CHF), (EUR_JPY,GBP_JPY), (EUR_GBP,EUR_USD), (AUD_JPY,NZD_JPY).

## Realised barrier PnL methodology

Final test 8-gate evaluation uses **realised barrier PnL** computed by re-traversing M1 paths with 25.0a barrier semantics (favourable barrier → +K_FAV × ATR; adverse barrier → -K_ADV × ATR; same-bar both-hit → adverse first; horizon expiry → mark-to-market). Validation threshold selection uses synthesized PnL proxy for speed.

## H3 reference (binding from 25.0e-α §4 + PR #292 review)

- best-of-{F1, F2} test AUC = 0.5644 (F1 rank-1 = 0.5644; F2 rank-1 = 0.5613)
- H3 PASS threshold = 0.5744 (lift ≥ 0.01)
- H3 is evaluated on the BEST F3 cell, single-set comparison.
- Combined feature set (F3 + F1/F2) is NOT implemented in 25.0e-β.

## Split dates

- min: 2024-04-30 15:50:00+00:00
- train < 2025-09-23 12:41:00+00:00
- val [2025-09-23 12:41:00+00:00, 2026-01-11 00:00:30+00:00)
- test [2026-01-11 00:00:30+00:00, 2026-04-30 11:20:00+00:00]

## Feature NaN drop

- overall drop count: 13802; rate: 0.0034

Per-pair feature NaN drop:

| pair | drop_count | drop_rate |
|---|---|---|
| AUD_CAD | 484 | 0.0033 |
| AUD_JPY | 802 | 0.0031 |
| AUD_NZD | 508 | 0.0086 |
| AUD_USD | 714 | 0.0029 |
| CHF_JPY | 654 | 0.0030 |
| EUR_AUD | 700 | 0.0031 |
| EUR_CAD | 590 | 0.0032 |
| EUR_CHF | 640 | 0.0042 |
| EUR_GBP | 594 | 0.0041 |
| EUR_JPY | 858 | 0.0033 |
| EUR_USD | 814 | 0.0036 |
| GBP_AUD | 664 | 0.0033 |
| GBP_CHF | 486 | 0.0030 |
| GBP_JPY | 832 | 0.0032 |
| GBP_USD | 684 | 0.0029 |
| NZD_JPY | 650 | 0.0035 |
| NZD_USD | 810 | 0.0038 |
| USD_CAD | 646 | 0.0034 |
| USD_CHF | 732 | 0.0035 |
| USD_JPY | 940 | 0.0034 |

## All 18 cells — summary (sorted by test AUC desc)

| subgroup | lookback | zscore_window | n_train | n_test | train_AUC | val_AUC | test_AUC | gap | verdict | h_state | n_trades | sharpe | ann_pnl | A4 | A5_ann | low_power |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F3a_F3b | 100 | 50 | 2501108 | 564298 | 0.5546 | 0.5551 | 0.5480 | 0.0066 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 259217 | -0.3628 | -2106178.3 | 0 | -2538502.5 | no |
| F3a_F3b | 100 | 20 | 2513608 | 565486 | 0.5541 | 0.5546 | 0.5480 | 0.0062 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 260354 | -0.3628 | -2113915.1 | 0 | -2548135.7 | no |
| F3b | 100 | 20 | 2520184 | 566012 | 0.5539 | 0.5540 | 0.5477 | 0.0062 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 260621 | -0.3630 | -2116546.1 | 0 | -2551212.0 | no |
| F3b | 100 | 50 | 2520184 | 566012 | 0.5539 | 0.5540 | 0.5477 | 0.0062 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 260621 | -0.3630 | -2116546.1 | 0 | -2551212.0 | no |
| F3a_F3b | 50 | 20 | 2745770 | 580726 | 0.5537 | 0.5548 | 0.5469 | 0.0068 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 267759 | -0.3659 | -2180343.1 | 0 | -2626913.8 | no |
| F3a_F3b | 50 | 50 | 2735294 | 579888 | 0.5538 | 0.5553 | 0.5468 | 0.0070 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 267173 | -0.3651 | -2172479.5 | 0 | -2618072.8 | no |
| F3a_F3b | 20 | 50 | 2865922 | 590940 | 0.5548 | 0.5557 | 0.5467 | 0.0081 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 275621 | -0.3668 | -2247257.3 | 0 | -2706940.2 | no |
| F3b | 50 | 20 | 2752800 | 581304 | 0.5536 | 0.5546 | 0.5465 | 0.0071 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 267866 | -0.3663 | -2183812.6 | 0 | -2630561.7 | no |
| F3b | 50 | 50 | 2752800 | 581304 | 0.5536 | 0.5546 | 0.5465 | 0.0071 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 267866 | -0.3663 | -2183812.6 | 0 | -2630561.7 | no |
| F3a_F3b | 20 | 20 | 2878026 | 591946 | 0.5547 | 0.5558 | 0.5463 | 0.0084 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 275831 | -0.3668 | -2250290.0 | 0 | -2710323.2 | no |
| F3b | 20 | 20 | 2884246 | 592562 | 0.5546 | 0.5559 | 0.5459 | 0.0087 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 276265 | -0.3672 | -2255679.0 | 0 | -2716436.0 | no |
| F3b | 20 | 50 | 2884246 | 592562 | 0.5546 | 0.5559 | 0.5459 | 0.0087 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 276265 | -0.3672 | -2255679.0 | 0 | -2716436.0 | no |
| F3a | 20 | 50 | 2917272 | 595546 | 0.5482 | 0.5518 | 0.5451 | 0.0031 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 290816 | -0.3718 | -2377159.5 | 0 | -2862184.8 | no |
| F3a | 100 | 50 | 2886882 | 592916 | 0.5489 | 0.5533 | 0.5446 | 0.0043 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 289011 | -0.3709 | -2358471.8 | 0 | -2840486.7 | no |
| F3a | 50 | 50 | 2906796 | 594708 | 0.5484 | 0.5528 | 0.5445 | 0.0039 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 290296 | -0.3713 | -2371049.5 | 0 | -2855207.5 | no |
| F3a | 20 | 20 | 2929376 | 596552 | 0.5479 | 0.5518 | 0.5444 | 0.0035 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 291378 | -0.3720 | -2383354.1 | 0 | -2869316.7 | no |
| F3a | 50 | 20 | 2917272 | 595546 | 0.5480 | 0.5519 | 0.5443 | 0.0037 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 290888 | -0.3718 | -2377889.1 | 0 | -2863034.5 | no |
| F3a | 100 | 20 | 2899382 | 594104 | 0.5483 | 0.5524 | 0.5442 | 0.0041 | REJECT_NON_DISCRIMINATIVE | H1_FAIL | 290306 | -0.3711 | -2370038.9 | 0 | -2854213.7 | no |

## Top-3 cells by test AUC — expanded breakdown

### Cell: subgroup=F3a_F3b, lookback=100, zscore_window=50

- n_train: 2501108, n_val: 491528, n_test: 564298
- train AUC: 0.5546, val AUC: 0.5551, test AUC: 0.5480, gap: 0.0066
- threshold selected on validation: 0.4
- realised: n_trades=259217, sharpe=-0.3628, ann_pnl=-2106178.3, max_dd=631446.0, A4 pos=0/4, A5 stress ann_pnl=-2538502.5
- proxy: n_trades=259217, sharpe=-0.4491, ann_pnl=-2605419.7
- gates: A0=OK A1=x A2=x A3=x A4=x A5=x
- calibration decile: monotonic=True, overall_brier=0.2325, low_n_flag=False
- verdict: **REJECT_NON_DISCRIMINATIVE** (H1_FAIL)
- by-pair trade count: {'EUR_USD': 16912, 'GBP_USD': 17565, 'AUD_USD': 18517, 'NZD_USD': 15490, 'USD_CHF': 15475, 'USD_CAD': 14539, 'EUR_GBP': 8809, 'USD_JPY': 19618, 'EUR_JPY': 17440, 'GBP_JPY': 17371, 'AUD_JPY': 18208, 'NZD_JPY': 11216, 'CHF_JPY': 13852, 'EUR_CHF': 8289, 'EUR_AUD': 14048, 'EUR_CAD': 10581, 'AUD_NZD': 13, 'AUD_CAD': 2084, 'GBP_AUD': 10416, 'GBP_CHF': 8774}
- by-direction trade count: {'long': 259217, 'short': 0}
- features: f3a_USD_strength_z, f3a_EUR_strength_z, f3a_JPY_strength_z, f3a_GBP_strength_z, f3a_AUD_strength_z, f3a_CAD_strength_z, f3a_CHF_strength_z, f3a_NZD_strength_z, f3b_corr_EUR_USD_GBP_USD, f3b_corr_AUD_USD_NZD_USD, f3b_corr_USD_JPY_USD_CHF, f3b_corr_EUR_JPY_GBP_JPY, f3b_corr_EUR_GBP_EUR_USD, f3b_corr_AUD_JPY_NZD_JPY

### Cell: subgroup=F3a_F3b, lookback=100, zscore_window=20

- n_train: 2513608, n_val: 493614, n_test: 565486
- train AUC: 0.5541, val AUC: 0.5546, test AUC: 0.5480, gap: 0.0062
- threshold selected on validation: 0.4
- realised: n_trades=260354, sharpe=-0.3628, ann_pnl=-2113915.1, max_dd=633765.5, A4 pos=0/4, A5 stress ann_pnl=-2548135.7
- proxy: n_trades=260354, sharpe=-0.4488, ann_pnl=-2613386.0
- gates: A0=OK A1=x A2=x A3=x A4=x A5=x
- calibration decile: monotonic=True, overall_brier=0.2325, low_n_flag=False
- verdict: **REJECT_NON_DISCRIMINATIVE** (H1_FAIL)
- by-pair trade count: {'EUR_USD': 16943, 'GBP_USD': 17594, 'AUD_USD': 18554, 'NZD_USD': 15575, 'USD_CHF': 15524, 'USD_CAD': 14576, 'EUR_GBP': 9036, 'USD_JPY': 19648, 'EUR_JPY': 17470, 'GBP_JPY': 17401, 'AUD_JPY': 18238, 'NZD_JPY': 11426, 'CHF_JPY': 13875, 'EUR_CHF': 8387, 'EUR_AUD': 14067, 'EUR_CAD': 10622, 'AUD_NZD': 14, 'AUD_CAD': 2099, 'GBP_AUD': 10425, 'GBP_CHF': 8880}
- by-direction trade count: {'long': 260354, 'short': 0}
- features: f3a_USD_strength_z, f3a_EUR_strength_z, f3a_JPY_strength_z, f3a_GBP_strength_z, f3a_AUD_strength_z, f3a_CAD_strength_z, f3a_CHF_strength_z, f3a_NZD_strength_z, f3b_corr_EUR_USD_GBP_USD, f3b_corr_AUD_USD_NZD_USD, f3b_corr_USD_JPY_USD_CHF, f3b_corr_EUR_JPY_GBP_JPY, f3b_corr_EUR_GBP_EUR_USD, f3b_corr_AUD_JPY_NZD_JPY

### Cell: subgroup=F3b, lookback=100, zscore_window=20

- n_train: 2520184, n_val: 494528, n_test: 566012
- train AUC: 0.5539, val AUC: 0.5540, test AUC: 0.5477, gap: 0.0062
- threshold selected on validation: 0.4
- realised: n_trades=260621, sharpe=-0.3630, ann_pnl=-2116546.1, max_dd=634554.3, A4 pos=0/4, A5 stress ann_pnl=-2551212.0
- proxy: n_trades=260621, sharpe=-0.4490, ann_pnl=-2615754.9
- gates: A0=OK A1=x A2=x A3=x A4=x A5=x
- calibration decile: monotonic=False, overall_brier=0.2325, low_n_flag=False
- verdict: **REJECT_NON_DISCRIMINATIVE** (H1_FAIL)
- by-pair trade count: {'EUR_USD': 16963, 'GBP_USD': 17616, 'AUD_USD': 18578, 'NZD_USD': 15572, 'USD_CHF': 15553, 'USD_CAD': 14609, 'EUR_GBP': 9089, 'USD_JPY': 19666, 'EUR_JPY': 17487, 'GBP_JPY': 17418, 'AUD_JPY': 18261, 'NZD_JPY': 11482, 'CHF_JPY': 13875, 'EUR_CHF': 8418, 'EUR_AUD': 14067, 'EUR_CAD': 10628, 'AUD_NZD': 23, 'AUD_CAD': 1991, 'GBP_AUD': 10424, 'GBP_CHF': 8901}
- by-direction trade count: {'long': 260621, 'short': 0}
- features: f3b_corr_EUR_USD_GBP_USD, f3b_corr_AUD_USD_NZD_USD, f3b_corr_USD_JPY_USD_CHF, f3b_corr_EUR_JPY_GBP_JPY, f3b_corr_EUR_GBP_EUR_USD, f3b_corr_AUD_JPY_NZD_JPY

## Best-cell decile reliability table (diagnostic-only)

n=564298, monotonic=True, overall_brier=0.2325, low_n_flag=False

| bucket | n | p_hat_mean | realised_win_rate | brier |
|---|---|---|---|---|
| 0 | 56430 | 0.3661 | 0.1408 | 0.1717 |
| 1 | 56430 | 0.4210 | 0.1508 | 0.2011 |
| 2 | 56430 | 0.4407 | 0.1631 | 0.2136 |
| 3 | 56429 | 0.4547 | 0.1675 | 0.2220 |
| 4 | 56430 | 0.4668 | 0.1786 | 0.2297 |
| 5 | 56430 | 0.4786 | 0.1844 | 0.2370 |
| 6 | 56429 | 0.4909 | 0.1890 | 0.2444 |
| 7 | 56430 | 0.5048 | 0.1959 | 0.2530 |
| 8 | 56430 | 0.5235 | 0.1979 | 0.2648 |
| 9 | 56430 | 0.5632 | 0.2329 | 0.2874 |

## Aggregate H1 / H2 / H3 / H4 outcome

- Best F3 cell: **{'subgroup': 'F3a_F3b', 'lookback': 100, 'zscore_window': 50}** with test AUC 0.5480
- H1 PASS threshold = 0.5500; H1 PASS at best cell: False
- H2 (A1 Sharpe ≥ 0.082 AND A2 ann_pnl ≥ 180.0) at best cell: **False** (sharpe=-0.3628, ann_pnl=-2106178.3)
- H3 (lift ≥ 0.01, threshold ≥ 0.5744): **False** (observed lift = -0.0164)
- H4 (best-cell realised Sharpe ≥ 0): **False** (realised Sharpe = -0.3628)

> H4 FAIL — F3 best-cell realised Sharpe < 0 at AUC ≈ structural-gap regime; triggers PR #291 §6.4 strong soft-stop strengthening.

## Routing recommendation framing (non-decisive)

This section lists which §7 verdict tree branch the best cell falls into. It is informational. The actual routing decision (next F-class / Phase 25 close / production discussion) is handed to the next PR.

Per 25.0e-α §7 verdict tree, applied to the best cell after H3 refinement of REJECT_BUT_INFORMATIVE branches:

- Best-cell refined verdict: **REJECT_NON_DISCRIMINATIVE**
- Best-cell h_state: H1_FAIL

If H4 FAIL, PR #291 §6.4 strong soft-stop strengthening is the recommended next-PR consideration; user judgement decides whether to continue F4/F5/F6 or close Phase 25.

## Multiple-testing caveat

These are 18 evaluated cells. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE verdicts are hypothesis-generating ONLY; production-readiness requires an X-v2-equivalent frozen-OOS PR per Phase 22 contract.
