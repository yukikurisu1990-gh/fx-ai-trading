# Phase 28.0a-β — A1 Objective Redesign eval report

**Sub-phase**: 28.0a-β
**Design memo**: PR #337 (`phase28_0a_alpha_a1_objective_redesign_design_memo.md`)
**Kickoff**: PR #335 / first-mover routing review PR #336

## 1. Executive summary

Per-variant H-C1 outcome ladder (PR #337 §3.2; precedence row 4 > 1 > 2 > 3):

| Variant | Outcome | Row | Reason |
|---|---|---|---|
| C-a1-L1 | FALSIFIED_OBJECTIVE_INSUFFICIENT | 3 | val Sharpe lift -0.1190 < +0.02 OR other H-C1 conditions failed |
| C-a1-L2 | FALSIFIED_OBJECTIVE_INSUFFICIENT | 3 | val Sharpe lift -0.4071 < +0.02 OR other H-C1 conditions failed |
| C-a1-L3 | FALSIFIED_OBJECTIVE_INSUFFICIENT | 3 | val Sharpe lift -0.4155 < +0.02 OR other H-C1 conditions failed |

**Aggregate verdict**: REJECT_NON_DISCRIMINATIVE
**Routing implication**: All 3 variants FALSIFIED_OBJECTIVE_INSUFFICIENT or PARTIAL_DRIFT — objective-axis exhausted. Route to A4 (R-T1 elevation) OR A0 (architecture redesign).

**C-sb-baseline reproduction**: PASS
**C-a1-se-r7a-replica drift vs 27.0d C-se**: all_within_tolerance=True (warn=False; DIAGNOSTIC-ONLY)

## 2. Cells overview

| Cell | Picker | Score | Feature set | Loss |
|---|---|---|---|---|
| C-a1-L1 | S-E(regressor_pred_l1_magweight) | s_e_l1 | r7a | l1_magnitude_weighted_huber |
| C-a1-L2 | S-E(regressor_pred_l2_asymmetric) | s_e_l2 | r7a | l2_asymmetric_huber |
| C-a1-L3 | S-E(regressor_pred_l3_spreadcost) | s_e_l3 | r7a | l3_spread_cost_weighted_huber |
| C-a1-se-r7a-replica | S-E(regressor_pred_symmetric_control) | s_e_control | r7a | symmetric_huber_alpha_0_9 |
| C-sb-baseline | S-B(raw_p_tp_minus_p_sl) | s_b_raw | r7a | multiclass_ce |

## 3. Row-set policy / drop stats

**A1-specific row-set policy** (PR #337 §5.2): all 5 cells share the R7-A-clean parent row-set; no R7-C row-drop is applied in this sub-phase. Fix A row-set isolation contract is not exercised here.

R7-A new-feature row-drop:
- train: n_input=2941032 n_kept=2941032 n_dropped=0
- val: n_input=517422 n_kept=517422 n_dropped=0
- test: n_input=597666 n_kept=597666 n_dropped=0
Split dates:
- min: 2024-04-30 14:10:00+00:00
- train < 2025-09-23 12:11:00+00:00
- val [2025-09-23 12:11:00+00:00, 2026-01-10 23:45:30+00:00)
- test [2026-01-10 23:45:30+00:00, 2026-04-30 11:20:00+00:00]

## 4. Sanity probe results

- train: total=2941032, TP 19.215% / SL 74.290% / TIME 6.495%
- val: total=517422, TP 16.576% / SL 77.172% / TIME 6.252%
- test: total=597666, TP 17.899% / SL 75.568% / TIME 6.533%
- D-1 binding check: PASS
- L1 sample_weight: n=2941032 mean=+6.292 max=+30.000 (clip 30.0)
- L3 sample_weight: n=2941032 mean=+2.084 max=+18.800 (γ=0.5)
- L2 grad/hess sanity check: PASS (6 subtests)

## 5. OOF correlation diagnostic per variant (DIAGNOSTIC-ONLY)

| Variant | Pearson | Spearman |
|---|---|---|
| control | +0.0748 | +0.3836 |
| L1 | +0.0748 | +0.3836 |
| L2 | +0.0748 | +0.3836 |
| L3 | +0.0748 | +0.3836 |

## 6. Regression diagnostic per variant (DIAGNOSTIC-ONLY)

| Variant | Split | n | R² | MAE | MSE |
|---|---|---|---|---|---|
| L1 | train | 2941032 | -0.0042 | +4.818 | +nan |
| L1 | val | 517422 | +0.0032 | +3.547 | +nan |
| L1 | test | 597666 | +0.0031 | +4.349 | +nan |
| L2 | train | 2941032 | -0.4328 | +3.996 | +nan |
| L2 | val | 517422 | -0.3513 | +2.941 | +nan |
| L2 | test | 597666 | -0.3799 | +3.569 | +nan |
| L3 | train | 2941032 | -0.0453 | +4.398 | +nan |
| L3 | val | 517422 | -0.0522 | +3.138 | +nan |
| L3 | test | 597666 | -0.0421 | +3.885 | +nan |
| control | train | 2941032 | -0.0401 | +4.435 | +nan |
| control | val | 517422 | -0.0454 | +3.177 | +nan |
| control | test | 597666 | -0.0366 | +3.932 | +nan |

## 7. All formal cells — primary quantile-family summary (5 cells × 5 q = 25 (cell, q) pairs)

### C-a1-L1 (S-E(regressor_pred_l1_magweight))

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | -1.951545 | -0.8064 | 25904 | -0.8508 | 15485 | -70475.4 |
| 10.0 | -2.151636 | -0.4720 | 51748 | -0.2902 | 37524 | -179999.2 |
| 20.0 | -2.483910 | -0.3593 | 103583 | -0.2532 | 90590 | -470686.1 |
| 30.0 | -2.712112 | -0.3053 | 155264 | -0.2412 | 161044 | -970435.7 |
| 40.0 | -2.886378 | -0.3063 | 207146 | -0.2571 | 232276 | -1461697.8 |

### C-a1-L2 (S-E(regressor_pred_l2_asymmetric))

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | -2.070918 | -0.5934 | 25936 | -0.5729 | 19922 | -129107.8 |
| 10.0 | -2.274140 | -0.6238 | 51903 | -0.5976 | 38522 | -217218.7 |
| 20.0 | -2.891554 | -0.6328 | 103550 | -0.6088 | 80370 | -425491.1 |
| 30.0 | -3.237139 | -0.6186 | 155236 | -0.5819 | 129928 | -693974.5 |
| 40.0 | -3.650385 | -0.6157 | 207447 | -0.5806 | 182617 | -1042863.0 |

### C-a1-L3 (S-E(regressor_pred_l3_spreadcost))

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | -2.015243 | -0.7987 | 25916 | -0.8439 | 15482 | -70208.7 |
| 10.0 | -2.234188 | -0.7348 | 51752 | -0.7667 | 35436 | -165755.3 |
| 20.0 | -2.665459 | -0.6662 | 103493 | -0.6640 | 78483 | -380327.2 |
| 30.0 | -3.167582 | -0.6228 | 155314 | -0.5916 | 129049 | -651393.8 |
| 40.0 | -3.658954 | -0.6018 | 206994 | -0.5622 | 183236 | -991294.9 |

### C-a1-se-r7a-replica (S-E(regressor_pred_symmetric_control))

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | -2.014166 | -0.7940 | 25975 | -0.8418 | 15463 | -70045.9 |
| 10.0 | -2.233683 | -0.7351 | 51772 | -0.7667 | 35439 | -165754.3 |
| 20.0 | -2.668087 | -0.6645 | 103530 | -0.6641 | 78590 | -381008.7 |
| 30.0 | -3.167135 | -0.6223 | 155299 | -0.5906 | 129039 | -650648.7 |
| 40.0 | -3.649628 | -0.5732 | 206985 | -0.4831 | 184703 | -999830.4 |

### C-sb-baseline (S-B(raw_p_tp_minus_p_sl))

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | +0.126233 | -0.1863 | 25881 | -0.1732 | 34626 | -204664.4 |
| 10.0 | +0.095318 | -0.2150 | 51803 | -0.1989 | 89279 | -562058.1 |
| 20.0 | +0.051759 | -0.2534 | 103505 | -0.2331 | 164973 | -1127721.0 |
| 30.0 | +0.013798 | -0.2832 | 155234 | -0.2601 | 231694 | -1681337.0 |
| 40.0 | -0.026591 | -0.3066 | 207018 | -0.2825 | 294367 | -2211158.6 |

## 8. Val-selection (cell*, q*)

- cell: id=C-sb-baseline picker=S-B(raw_p_tp_minus_p_sl) score_type=s_b_raw feature_set=r7a loss=multiclass_ce
- q*=5.0 cutoff=+0.126233
- val Sharpe=-0.1863 (n=25881)
- test Sharpe=-0.1732 ann_pnl=-204664.4 n=34626 FORMAL Spearman=-0.1535

## 9. Cross-cell aggregate verdict

- aggregate verdict: SPLIT_VERDICT_ROUTE_TO_REVIEW
- agree: False
- branches: ['REJECT_BUT_INFORMATIVE_FLAT', 'REJECT_NON_DISCRIMINATIVE']

## 10. §10 baseline reproduction (FAIL-FAST)

- n_trades: observed=34626 baseline=34626 delta=+0 match=True
- Sharpe: observed=-0.173164 baseline=-0.173200 delta=+3.550307e-05 match=True
- ann_pnl: observed=-204664.423 baseline=-204664.400 delta=-0.023 match=True
- all_match: True

## 11. Within-eval ablation drift (per variant vs C-a1-se-r7a-replica)

| Variant | n_trades Δ | within | Sharpe Δ | within | ann_pnl Δ | within | all_within |
|---|---|---|---|---|---|---|---|
| L1 | -23659 | False | +2.4182e-01 | False | +29394.720 | False | False |
| L2 | -164781 | False | -8.9885e-02 | False | +870722.635 | False | False |
| L3 | -1467 | False | -7.9139e-02 | False | +8535.488 | False | False |

**Caveat**: API divergence — L1 / L3 use sklearn pipeline + `sample_weight`; L2 uses LightGBM Booster API with custom objective + manual ColumnTransformer preprocessing. Both paths produce predictions of the same dtype but the internal training loop differs (per PR #337 §15.1 / D-BA8).

## 12. Feature importance per variant (DIAGNOSTIC-ONLY)

### L1

(unavailable: {'buckets': {'pair': 333.0, 'direction': 31.0, 'atr_at_signal_pip': 1462.0, 'spread_at_signal_pip': 1124.0}, 'buckets_normalised': {'pair': 0.11288135593220339, 'direction': 0.010508474576271187, 'atr_at_signal_pip': 0.49559322033898306, 'spread_at_signal_pip': 0.38101694915254236}, 'total': 2950.0})

### L2

- num__atr_at_signal_pip: gain=+199088318.9
- num__spread_at_signal_pip: gain=+145257548.0
- cat__pair_CHF_JPY: gain=+3913257.7
- cat__pair_EUR_GBP: gain=+2219938.4
- cat__pair_GBP_JPY: gain=+2099414.6
- cat__pair_USD_JPY: gain=+1884377.3
- cat__pair_EUR_CHF: gain=+1621029.4
- cat__pair_EUR_AUD: gain=+1566295.2
- cat__pair_GBP_AUD: gain=+1275633.8
- cat__pair_EUR_JPY: gain=+528831.9
- cat__direction_long: gain=+482920.7
- cat__pair_AUD_JPY: gain=+145765.7
- cat__pair_NZD_JPY: gain=+48141.3
- cat__pair_NZD_USD: gain=+16989.9
- cat__pair_AUD_USD: gain=+13952.3
- cat__pair_EUR_USD: gain=+13592.6
- cat__pair_GBP_CHF: gain=+11099.2
- cat__pair_EUR_CAD: gain=+10861.3
- cat__pair_GBP_USD: gain=+4604.0
- cat__pair_USD_CAD: gain=+2457.5
- cat__pair_USD_CHF: gain=+2027.5
- cat__direction_short: gain=+644.8
- cat__pair_AUD_CAD: gain=+631.9
- cat__pair_AUD_NZD: gain=+0.0

### L3

(unavailable: {'buckets': {'pair': 280.0, 'direction': 36.0, 'atr_at_signal_pip': 1823.0, 'spread_at_signal_pip': 829.0}, 'buckets_normalised': {'pair': 0.09433962264150944, 'direction': 0.012129380053908356, 'atr_at_signal_pip': 0.6142183288409704, 'spread_at_signal_pip': 0.27931266846361186}, 'total': 2968.0})

### control

(unavailable: {'buckets': {'pair': 259.0, 'direction': 34.0, 'atr_at_signal_pip': 1978.0, 'spread_at_signal_pip': 697.0}, 'buckets_normalised': {'pair': 0.08726415094339622, 'direction': 0.011455525606469003, 'atr_at_signal_pip': 0.6664420485175202, 'spread_at_signal_pip': 0.23483827493261455}, 'total': 2968.0})

## 13. H-C1 outcome row binding per variant

| Variant | Outcome | Row | Sharpe lift vs §10 | val Sharpe | val n | cell Spearman | Notes |
|---|---|---|---|---|---|---|---|
| C-a1-L1 | FALSIFIED_OBJECTIVE_INSUFFICIENT | 3 | -0.1190 | -0.3053 | 155264 | +0.2296 | val Sharpe lift -0.1190 < +0.02 OR other H-C1 conditions fai |
| C-a1-L2 | FALSIFIED_OBJECTIVE_INSUFFICIENT | 3 | -0.4071 | -0.5934 | 25936 | +0.4657 | val Sharpe lift -0.4071 < +0.02 OR other H-C1 conditions fai |
| C-a1-L3 | FALSIFIED_OBJECTIVE_INSUFFICIENT | 3 | -0.4155 | -0.6018 | 206994 | +0.4587 | val Sharpe lift -0.4155 < +0.02 OR other H-C1 conditions fai |

**Aggregate H-C1 verdict**: REJECT_NON_DISCRIMINATIVE
**Routing**: All 3 variants FALSIFIED_OBJECTIVE_INSUFFICIENT or PARTIAL_DRIFT — objective-axis exhausted. Route to A4 (R-T1 elevation) OR A0 (architecture redesign).

## 14. Trade-count budget audit per variant

### L1

| q% | n_trades | inflation |
|---|---|---|
| 5.0 | 0 | 1.001x |
| 10.0 | 0 | 1.999x |
| 20.0 | 0 | 4.002x |
| 30.0 | 0 | 5.999x |
| 40.0 | 0 | 8.004x |

### L2

| q% | n_trades | inflation |
|---|---|---|
| 5.0 | 0 | 1.002x |
| 10.0 | 0 | 2.005x |
| 20.0 | 0 | 4.001x |
| 30.0 | 0 | 5.998x |
| 40.0 | 0 | 8.015x |

### L3

| q% | n_trades | inflation |
|---|---|---|
| 5.0 | 0 | 1.001x |
| 10.0 | 0 | 2.000x |
| 20.0 | 0 | 3.999x |
| 30.0 | 0 | 6.001x |
| 40.0 | 0 | 7.998x |

## 15. Pair concentration per cell (val-selected q*)

| Cell | val top-3 pairs | val Herfindahl | test top-3 | test Herfindahl |
|---|---|---|---|---|
| C-a1-L1 | - | nan | - | nan |
| C-a1-L2 | - | nan | - | nan |
| C-a1-L3 | - | nan | - | nan |
| C-a1-se-r7a-replica | - | nan | - | nan |
| C-sb-baseline | - | nan | - | nan |

## 16. Direction balance per cell (val-selected q* on test)

| Cell | long | short |
|---|---|---|
| C-a1-L1 | 80569 | 80475 |
| C-a1-L2 | 9868 | 10054 |
| C-a1-L3 | 91627 | 91609 |
| C-a1-se-r7a-replica | 92394 | 92309 |
| C-sb-baseline | 18308 | 16318 |

## 17. Per-pair Sharpe contribution per cell (DIAGNOSTIC-ONLY)

### C-a1-L1
| pair | n | Sharpe contribution |
|---|---|---|

### C-a1-L2
| pair | n | Sharpe contribution |
|---|---|---|

### C-a1-L3
| pair | n | Sharpe contribution |
|---|---|---|

### C-a1-se-r7a-replica
| pair | n | Sharpe contribution |
|---|---|---|

### C-sb-baseline
| pair | n | Sharpe contribution |
|---|---|---|

## 18. Top-tail regime audit per variant (DIAGNOSTIC-ONLY; spread_at_signal_pip only)

**Note**: R7-C f5a/f5b/f5c features are NOT re-computed in this sub-phase (out of scope per PR #337 §5.2). Audit uses `spread_at_signal_pip` (R7-A) only.

### L1
- population mean spread = +2.340 (p50 +2.100)
- q=10.0: top mean=+1.367 (Δ -0.973); n_top=51748
- q=20.0: top mean=+1.455 (Δ -0.885); n_top=103583

### L2
- population mean spread = +2.340 (p50 +2.100)
- q=10.0: top mean=+1.533 (Δ -0.807); n_top=51903
- q=20.0: top mean=+1.516 (Δ -0.824); n_top=103550

### L3
- population mean spread = +2.340 (p50 +2.100)
- q=10.0: top mean=+1.363 (Δ -0.977); n_top=51752
- q=20.0: top mean=+1.430 (Δ -0.910); n_top=103493

## 19. R7-A new-feature NaN-rate check (sanity probe item)

| Split | Feature | n | NaN | rate |
|---|---|---|---|---|
| train | atr_at_signal_pip | 2941032 | 0 | 0.000% |
| train | spread_at_signal_pip | 2941032 | 0 | 0.000% |
| val | atr_at_signal_pip | 517422 | 0 | 0.000% |
| val | spread_at_signal_pip | 517422 | 0 | 0.000% |
| test | atr_at_signal_pip | 597666 | 0 | 0.000% |
| test | spread_at_signal_pip | 597666 | 0 | 0.000% |

## 20. Realised-PnL distribution by class on TRAIN (DIAGNOSTIC)

| Class | n | mean | p5 | p50 | p95 |
|---|---|---|---|---|---|
| TP | 565106 | +9.820 | +3.660 | +8.306 | +21.030 |
| SL | 2184896 | -5.673 | -12.023 | -4.762 | -2.243 |
| TIME | 191030 | +1.573 | -5.000 | +1.100 | +9.700 |

## 21. Predicted PnL distribution per variant (DIAGNOSTIC)

| Variant | Split | n | mean | p5 | p50 | p95 |
|---|---|---|---|---|---|---|
| L1 | train | 2941032 | -2.902 | -3.802 | -2.905 | -2.033 |
| L1 | val | 517422 | -3.011 | -3.865 | -3.044 | -1.952 |
| L1 | test | 597666 | -3.044 | -3.861 | -3.043 | -2.085 |
| L2 | train | 2941032 | -5.787 | -12.975 | -4.761 | -2.193 |
| L2 | val | 517422 | -4.934 | -10.084 | -4.405 | -2.071 |
| L2 | test | 597666 | -5.595 | -11.327 | -4.789 | -2.210 |
| L3 | train | 2941032 | -3.893 | -5.175 | -4.177 | -2.130 |
| L3 | val | 517422 | -3.855 | -5.323 | -4.096 | -2.015 |
| L3 | test | 597666 | -4.041 | -5.315 | -4.298 | -2.177 |
| control | train | 2941032 | -3.804 | -5.001 | -4.050 | -2.130 |
| control | val | 517422 | -3.775 | -5.091 | -4.042 | -2.014 |
| control | test | 597666 | -3.940 | -5.079 | -4.158 | -2.177 |

## 22. References

- PR #335 — Phase 28 kickoff
- PR #336 — Phase 28 first-mover routing review (A1 primary)
- PR #337 — Phase 28.0a-α A1 objective redesign design memo
- PR #334 — Phase 27 closure memo (§10 baseline source)
- PR #325 — Phase 27.0d-β S-E regression (C-a1-se-r7a-replica reference)
- PR #332 — Phase 27.0f-β (3-cell + within-eval ablation control template)
- PR #279 — γ closure
- Phase 22 frozen-OOS contract
- Phase 9.12 production v9 tip 79ed1e8 (untouched)

## 23. Caveats

- All test-set metrics outside the val-selected (cell\*, q\*) are DIAGNOSTIC-ONLY and excluded from the formal H-C1 verdict.
- H2 PASS = PROMISING_BUT_NEEDS_OOS only. ADOPT_CANDIDATE wall preserved per Clause 1. NG#10 / NG#11 not relaxed.
- L2 asymmetric Huber uses LightGBM Booster API with custom objective; API differs from L1 / L3 (sklearn pipeline). Predictions are dtype-aligned but training loop differs (per PR #337 §15.1).
- Top-tail regime audit uses `spread_at_signal_pip` only; R7-C features are out of scope per PR #337 §5.2.

## 24. Cross-validation re-fits diagnostic (DIAGNOSTIC-ONLY)

5-fold OOF (seed=42) inherited from 27.0d / 27.0f. Per-fold predictions are computed for L1, L2, L3 variants and the symmetric Huber control. Aggregate Pearson / Spearman are reported in §5.

## 25. Sub-phase verdict snapshot

- per-variant outcomes:
  - C-a1-L1: FALSIFIED_OBJECTIVE_INSUFFICIENT (row 3)
  - C-a1-L2: FALSIFIED_OBJECTIVE_INSUFFICIENT (row 3)
  - C-a1-L3: FALSIFIED_OBJECTIVE_INSUFFICIENT (row 3)
- aggregate verdict: REJECT_NON_DISCRIMINATIVE
- routing implication: All 3 variants FALSIFIED_OBJECTIVE_INSUFFICIENT or PARTIAL_DRIFT — objective-axis exhausted. Route to A4 (R-T1 elevation) OR A0 (architecture redesign).
- C-sb-baseline reproduction: PASS
- C-a1-se-r7a-replica drift vs 27.0d C-se: all_within_tolerance=True (WARN-only)

*End of `artifacts/stage28_0a/eval_report.md`.*
