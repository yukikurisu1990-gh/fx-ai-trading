# Phase 29.0a-β — A2 Target Redesign eval report

**Sub-phase**: 29.0a-β (Phase 29 first sub-phase)
**Design memo**: PR #350 (`phase29_0a_alpha_a2_target_redesign_design_memo.md`)
**Kickoff**: PR #348 (Scope III / Policy C / Option 9c)
**Routing**: PR #349 (post-kickoff routing review; Path 2 A2 PRIMARY)

**MISSION**: Phase 29.0a tests A2 (target redesign) as the Phase 29 first sub-phase. Closed 4-target allowlist (T1 fixed-horizon executable close / T2 time-weighted / T3 multi-horizon / T4 asymmetric K_FAV/K_ADV); all D-1 PASS; fixed non-target axes (R7-A / tabular LightGBM / top-q / Huber α=0.9 / sample_weight=1). Option 9c dual baseline reference policy exercised.

## 1. Executive summary

Per-target H-D1 outcome ladder (PR #350 §10; precedence row 4 > 1 > 2 > 3):

| Target | Cell | Outcome | Row | Reason |
|---|---|---|---|---|
| T1 | C-d1-T1 | FALSIFIED_TARGET_INSUFFICIENT | 3 | val Sharpe lift -0.0736 < +0.02 OR other H-D1 conditions failed |
| T2 | C-d1-T2 | FALSIFIED_TARGET_INSUFFICIENT | 3 | val Sharpe lift -0.4161 < +0.02 OR other H-D1 conditions failed |
| T3 | C-d1-T3 | FALSIFIED_TARGET_INSUFFICIENT | 3 | val Sharpe lift -0.1320 < +0.02 OR other H-D1 conditions failed |
| T4 | C-d1-T4 | FALSIFIED_TARGET_INSUFFICIENT | 3 | val Sharpe lift -1.3248 < +0.02 OR other H-D1 conditions failed |

**Aggregate verdict**: REJECT_NON_DISCRIMINATIVE
**A2-narrow status**: FALSIFIED_A2_NARROW
**R-T3 absorption status under T3**: FALSIFIED_under_T3
**Routing implication**: All 4 targets FALSIFIED_TARGET_INSUFFICIENT or PARTIAL_DRIFT_TARGET_REPLICA — A2 axis exhausted under tested closed 4-target allowlist. Result is FALSIFIED_A2_NARROW (NEVER FALSIFIED_ALL_A2). Alternate target framings outside closed 4-target allowlist remain admissible via separate scope amendment. Post-29.0a routing review compares A0-broad / R-B / A3 next-axis options.

> **EXPLICIT LABEL**: this result is `FALSIFIED_A2_NARROW`, NEVER `FALSIFIED_ALL_A2`. Alternate target framings outside the tested closed 4-target allowlist (T1/T2/T3/T4) remain admissible via separate scope amendment PR. Post-29.0a routing review compares A0-broad / R-B / A3 next-axis options.

**Per-target baseline FAIL-FAST (internal consistency)**: all_consistent=True
**C-d1-target-control drift vs 27.0d C-se**: all_within_tolerance=True (WARN=False; DIAGNOSTIC-ONLY; 6th-phase chain)

## 2. Cells overview

| Cell | Picker | Score | Target | Baseline |
|---|---|---|---|---|
| C-d1-T1 | S-E(per_target_regressor) on T1 fixed-horizon executable clo | s_e_per_target | T1 | False |
| C-d1-T2 | S-E(per_target_regressor) on T2 time-weighted PnL (linear de | s_e_per_target | T2 | False |
| C-d1-T3 | S-E(per_target_regressor) on T3 multi-horizon PnL (H={30,60, | s_e_per_target | T3 | False |
| C-d1-T4 | S-E(per_target_regressor) on T4 asymmetric (K_FAV=2.0/K_ADV= | s_e_per_target | T4 | False |
| C-d1-target-control | S-E(target_control_regressor) on inherited triple-barrier 1. | s_e_target_control | TARGET_CONTROL | False |
| C-d1-T1-baseline | S-B raw P(TP)-P(SL) + top-q q=5 on T1 PnL | s_b_raw_per_target_baseline | T1 | True |
| C-d1-T2-baseline | S-B raw P(TP)-P(SL) + top-q q=5 on T2 PnL | s_b_raw_per_target_baseline | T2 | True |
| C-d1-T3-baseline | S-B raw P(TP)-P(SL) + top-q q=5 on T3 PnL | s_b_raw_per_target_baseline | T3 | True |
| C-d1-T4-baseline | S-B raw P(TP)-P(SL) + top-q q=5 on T4 PnL | s_b_raw_per_target_baseline | T4 | True |

## 3. Row-set policy / drop stats

**A2 row-set policy**: R7-A-clean parent row-set unchanged. No R7-C drop. Per-target NaN-PnL drop applied separately for each target Tx regressor fit. Cross-target row-set is NOT unified; per-target row-set comparison is the monetisation claim.

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
- NaN-PnL T1: 0 train rows (threshold 2941) PASS=True
- NaN-PnL T2: 0 train rows (threshold 2941) PASS=True
- NaN-PnL T3: 0 train rows (threshold 2941) PASS=True
- NaN-PnL T4: 0 train rows (threshold 2941) PASS=True
- T1 train distribution: n_finite=2941032 mean=-2.280
- T2 train distribution: n_finite=2941032 mean=-2.217
- T3 train distribution: n_finite=2941032 mean=-6.667
- T4 train distribution: n_finite=2941032 mean=-2.003
- T3 overlap rate: 99.731% (WARN if > 10%; warn=True)

## 5. OOF correlation diagnostic — per target (DIAGNOSTIC-ONLY)

| Target | aggregate Pearson | aggregate Spearman |
|---|---|---|
| T1 | +0.0467 | +0.0638 |
| T2 | +0.1258 | +0.3475 |
| T3 | +0.0597 | +0.2108 |
| T4 | +0.1178 | +0.8256 |
| TARGET_CONTROL | +0.0748 | +0.3836 |

## 6. Regression diagnostic — per target (DIAGNOSTIC-ONLY)

| Target | Split | n | R² | MAE |
|---|---|---|---|---|
| T1 | train | 2941032 | +0.0012 | +10.152 |
| T1 | val | 517422 | +0.0032 | +8.296 |
| T1 | test | 597666 | +0.0021 | +9.694 |
| T2 | train | 2941032 | -0.0164 | +3.258 |
| T2 | val | 517422 | -0.0025 | +2.450 |
| T2 | test | 597666 | -0.0005 | +2.952 |
| T3 | train | 2941032 | -0.0060 | +13.855 |
| T3 | val | 517422 | -0.0007 | +10.406 |
| T3 | test | 597212 | -0.0001 | +12.669 |
| T4 | train | 2941032 | -0.0328 | +1.157 |
| T4 | val | 517422 | +0.0344 | +0.522 |
| T4 | test | 597666 | +0.0123 | +0.776 |
| TARGET_CONTROL | train | 2941032 | -0.0401 | +4.435 |
| TARGET_CONTROL | val | 517422 | -0.0454 | +3.177 |
| TARGET_CONTROL | test | 597666 | -0.0366 | +3.932 |

## 7. Per-cell quantile family results

### C-d1-T1 (S-E(per_target_regressor) on T1 fixed-horizon executable close PnL)

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | -1.801725 | -0.2348 | 25940 | -0.2128 | 18439 | -80984.8 |
| 10.0 | -1.840911 | -0.2298 | 51749 | -0.2036 | 36500 | -167001.3 |
| 20.0 | -1.945757 | -0.2214 | 103499 | -0.1971 | 86357 | -413822.6 |
| 30.0 | -2.041838 | -0.2038 | 155500 | -0.1768 | 151635 | -761497.5 |
| 40.0 | -2.153650 | -0.1781 | 207023 | -0.1519 | 221111 | -1151627.9 |

### C-d1-T2 (S-E(per_target_regressor) on T2 time-weighted PnL (linear decay))

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | -1.749223 | -0.9722 | 25970 | -1.0312 | 15132 | -65131.9 |
| 10.0 | -1.916944 | -0.9142 | 51839 | -0.9434 | 34806 | -154553.3 |
| 20.0 | -2.246591 | -0.8381 | 103515 | -0.8296 | 79188 | -365714.3 |
| 30.0 | -2.661382 | -0.7795 | 155231 | -0.7325 | 131969 | -631604.9 |
| 40.0 | -3.023377 | -0.7228 | 206983 | -0.5906 | 203887 | -1027878.0 |

### C-d1-T3 (S-E(per_target_regressor) on T3 multi-horizon PnL (H={30,60,120}); R-T)

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | -6.301436 | -0.8366 | 25882 | -0.8862 | 15408 | -211078.5 |
| 10.0 | -6.992361 | -0.7704 | 51805 | -0.8032 | 35601 | -503060.1 |
| 20.0 | -8.264060 | -0.6037 | 103505 | -0.4531 | 79912 | -1175306.3 |
| 30.0 | -8.682596 | -0.3612 | 155335 | -0.2719 | 165658 | -2535949.5 |
| 40.0 | -8.821593 | -0.3264 | 207134 | -0.2690 | 239064 | -4276830.0 |

### C-d1-T4 (S-E(per_target_regressor) on T4 asymmetric (K_FAV=2.0/K_ADV=0.5))

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | -1.101837 | -13.9154 | 25889 | -14.3246 | 15340 | -50678.0 |
| 10.0 | -1.217536 | -7.3837 | 51770 | -7.0468 | 35368 | -126631.3 |
| 20.0 | -1.442396 | -3.1179 | 103494 | -2.9497 | 78672 | -312373.7 |
| 30.0 | -1.695808 | -1.9187 | 155300 | -1.7449 | 129342 | -554712.9 |
| 40.0 | -1.946929 | -1.5770 | 207058 | -1.3639 | 184118 | -846918.7 |

### C-d1-target-control (S-E(target_control_regressor) on inherited triple-barrier 1.5/1.0)

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | -2.014166 | -0.7940 | 25975 | -0.8418 | 15463 | -70045.9 |
| 10.0 | -2.233683 | -0.7351 | 51772 | -0.7667 | 35439 | -165754.3 |
| 20.0 | -2.668087 | -0.6645 | 103530 | -0.6641 | 78590 | -381008.7 |
| 30.0 | -3.167135 | -0.6223 | 155299 | -0.5906 | 129039 | -650648.7 |
| 40.0 | -3.649628 | -0.5732 | 206985 | -0.4831 | 184703 | -999830.4 |

### C-d1-T1-baseline (S-B raw P(TP)-P(SL) + top-q q=5 on T1 PnL)

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | +0.126233 | -0.1044 | 25881 | -0.0951 | 34626 | -218684.3 |

### C-d1-T2-baseline (S-B raw P(TP)-P(SL) + top-q q=5 on T2 PnL)

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | +0.126233 | -0.3067 | 25881 | -0.2869 | 34626 | -228452.8 |

### C-d1-T3-baseline (S-B raw P(TP)-P(SL) + top-q q=5 on T3 PnL)

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | +0.126233 | -0.1944 | 25881 | -0.1789 | 34585 | -601200.7 |

### C-d1-T4-baseline (S-B raw P(TP)-P(SL) + top-q q=5 on T4 PnL)

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | +0.126233 | -0.2522 | 25881 | -0.2284 | 34626 | -195512.8 |

## 8. Val-selected (cell*, q*) cross-cell

- cell: id=C-d1-T1 picker=S-E(per_target_regressor) on T1 fixed-horizon executable close PnL score_type=s_e_per_target feature_set=r7a target_kind=T1 is_baseline=False
- q*=40.0 cutoff=-2.153649802390915
- val Sharpe=-0.1781 (n=207023)
- test Sharpe=-0.1519 ann_pnl=-1151627.9 n=221111 FORMAL Spearman=+0.0864

## 9. Cross-cell aggregate verdict

- aggregate verdict: SPLIT_VERDICT_ROUTE_TO_REVIEW
- agree: False
- branches: ['REJECT_BUT_INFORMATIVE_FLAT', 'REJECT_WEAK_SIGNAL_ONLY']

## 10. Phase 29 §10 per-target baseline (Option 9c)

**Internal-consistency FAIL-FAST per PR #350 §8.4**: per-target baseline computed twice must agree within tolerance (n_trades exact / Sharpe ±1e-4 / ann_pnl ±0.5 pip). Phase 28 §10 archived as DIAGNOSTIC-ONLY 2nd reference.

| Target | test_n_trades | test_Sharpe | test_ann_pnl | val_Sharpe |
|---|---|---|---|---|
| T1 | 34626 | -0.0951 | -218684.3 | -0.1044 |
| T2 | 34626 | -0.2869 | -228452.8 | -0.3067 |
| T3 | 34585 | -0.1789 | -601200.7 | -0.1944 |
| T4 | 34626 | -0.2284 | -195512.8 | -0.2522 |

**Archived Phase 28 §10 reference (immutable; DIAGNOSTIC-ONLY 2nd reference)**:
- n_trades=34626 | Sharpe=-0.1732 | ann_pnl=-204664.4 | val_Sharpe=-0.1863

**Per-target baseline drift vs archived Phase 28 §10 (DIAGNOSTIC-ONLY)**:
- T1: n_trades Δ=0 | Sharpe Δ=+0.0781 | ann_pnl Δ=-14019.9
- T2: n_trades Δ=0 | Sharpe Δ=-0.1137 | ann_pnl Δ=-23788.4
- T3: n_trades Δ=-41 | Sharpe Δ=-0.0057 | ann_pnl Δ=-396536.3
- T4: n_trades Δ=0 | Sharpe Δ=-0.0552 | ann_pnl Δ=+9151.6

**FAIL-FAST consistency**: all_consistent=True

## 11. Within-eval ablation drift per target (vs C-d1-target-control)

| Target | n_trades Δ | within | Sharpe Δ | within | ann_pnl Δ | within | all_within |
|---|---|---|---|---|---|---|---|
| T1 | 36408 | False | +3.3110e-01 | False | -151797.508 | False | False |
| T2 | 19184 | False | -1.0751e-01 | False | -28047.624 | False | False |
| T3 | 54361 | False | +2.1403e-01 | False | -3276999.576 | False | False |
| T4 | -585 | False | -8.8084e-01 | False | +152911.671 | False | False |

## 11b. C-d1-target-control drift vs 27.0d C-se (DIAGNOSTIC-ONLY WARN; 6th-phase chain)

**Chain position**: 6th anchor (27.0d -> 27.0f -> 28.0a -> 28.0b -> 28.0c -> 29.0a)

- n_trades: observed=184703 baseline_27_0d=184703 delta=0 within=True
- Sharpe: observed=-0.483051 baseline_27_0d=-0.4830508944 delta=+3.0473e-11 within=True
- ann_pnl: observed=-999830.405 baseline_27_0d=-999830.4048230398 delta=+0.000 within=True
- all_within_tolerance: True
- WARN: False

## 12. Feature importance — per target regressor (DIAGNOSTIC-ONLY)

### T1
(unavailable: {'buckets': {'pair': 520.0, 'direction': 569.0, 'atr_at_signal_pip': 633.0, 'spread_at_signal_pip': 1246.0}, 'buckets_normalised': {'pair': 0.1752021563342318, 'direction': 0.19171159029649595, 'atr_at_signal_pip': 0.21327493261455527, 'spread_at_signal_pip': 0.419811320754717}, 'total': 2968.0})

### T2
(unavailable: {'buckets': {'pair': 421.0, 'direction': 30.0, 'atr_at_signal_pip': 1450.0, 'spread_at_signal_pip': 1067.0}, 'buckets_normalised': {'pair': 0.14184636118598382, 'direction': 0.010107816711590296, 'atr_at_signal_pip': 0.488544474393531, 'spread_at_signal_pip': 0.35950134770889486}, 'total': 2968.0})

### T3
(unavailable: {'buckets': {'pair': 327.0, 'direction': 25.0, 'atr_at_signal_pip': 1936.0, 'spread_at_signal_pip': 680.0}, 'buckets_normalised': {'pair': 0.11017520215633424, 'direction': 0.008423180592991913, 'atr_at_signal_pip': 0.6522911051212938, 'spread_at_signal_pip': 0.22911051212938005}, 'total': 2968.0})

### T4
(unavailable: {'buckets': {'pair': 255.0, 'direction': 13.0, 'atr_at_signal_pip': 1943.0, 'spread_at_signal_pip': 757.0}, 'buckets_normalised': {'pair': 0.08591644204851752, 'direction': 0.004380053908355795, 'atr_at_signal_pip': 0.6546495956873315, 'spread_at_signal_pip': 0.25505390835579517}, 'total': 2968.0})

### TARGET_CONTROL
(unavailable: {'buckets': {'pair': 259.0, 'direction': 34.0, 'atr_at_signal_pip': 1978.0, 'spread_at_signal_pip': 697.0}, 'buckets_normalised': {'pair': 0.08726415094339622, 'direction': 0.011455525606469003, 'atr_at_signal_pip': 0.6664420485175202, 'spread_at_signal_pip': 0.23483827493261455}, 'total': 2968.0})

## 13. H-D1 outcome row binding per target (A2 closed allowlist; interpretation guards)

Per PR #350 §10: H-D1 = A2 target redesign axis. Failure of all 4 targets is `FALSIFIED_A2_NARROW`, NEVER `FALSIFIED_ALL_A2`. Alternate target framings outside closed 4-target allowlist remain admissible via separate scope amendment. R-T3 absorbed under T3 multi-horizon variant.

| Target | Cell | Outcome | Row | Sharpe lift | val Sharpe | val n | cell Spearman | Notes |
|---|---|---|---|---|---|---|---|---|
| T1 | C-d1-T1 | FALSIFIED_TARGET_INSUFFICIENT | 3 | -0.0736 | -0.1781 | 207023 | +0.0195 | val Sharpe lift -0.0736 < +0.02 OR other H-D1 conditions failed |
| T2 | C-d1-T2 | FALSIFIED_TARGET_INSUFFICIENT | 3 | -0.4161 | -0.7228 | 206983 | +0.3989 | val Sharpe lift -0.4161 < +0.02 OR other H-D1 conditions failed |
| T3 | C-d1-T3 | FALSIFIED_TARGET_INSUFFICIENT | 3 | -0.1320 | -0.3264 | 207134 | +0.3919 | val Sharpe lift -0.1320 < +0.02 OR other H-D1 conditions failed |
| T4 | C-d1-T4 | FALSIFIED_TARGET_INSUFFICIENT | 3 | -1.3248 | -1.5770 | 207058 | +0.9483 | val Sharpe lift -1.3248 < +0.02 OR other H-D1 conditions failed |

**Aggregate H-D1 verdict**: REJECT_NON_DISCRIMINATIVE
**A2-narrow status**: FALSIFIED_A2_NARROW
**R-T3 absorption status**: FALSIFIED_under_T3
**Routing**: All 4 targets FALSIFIED_TARGET_INSUFFICIENT or PARTIAL_DRIFT_TARGET_REPLICA — A2 axis exhausted under tested closed 4-target allowlist. Result is FALSIFIED_A2_NARROW (NEVER FALSIFIED_ALL_A2). Alternate target framings outside closed 4-target allowlist remain admissible via separate scope amendment. Post-29.0a routing review compares A0-broad / R-B / A3 next-axis options.

## 14. Trade-count budget audit per target

| Cell | val_n_trades | test_n_trades |
|---|---|---|
| C-d1-T1 | 207023 | 221111 |
| C-d1-T2 | 206983 | 203887 |
| C-d1-T3 | 207134 | 239064 |
| C-d1-T4 | 207058 | 184118 |
| C-d1-target-control | 206985 | 184703 |
| C-d1-T1-baseline | 25881 | 34626 |
| C-d1-T2-baseline | 25881 | 34626 |
| C-d1-T3-baseline | 25881 | 34585 |
| C-d1-T4-baseline | 25881 | 34626 |

## 15. Pair concentration per cell (val-selected)

| Cell | val top-3 pairs | val Herfindahl | test top-3 | test Herfindahl |
|---|---|---|---|---|
| C-d1-T1 |  | nan |  | nan |
| C-d1-T2 |  | nan |  | nan |
| C-d1-T3 |  | nan |  | nan |
| C-d1-T4 |  | nan |  | nan |
| C-d1-target-control |  | nan |  | nan |
| C-d1-T1-baseline |  | nan |  | nan |
| C-d1-T2-baseline |  | nan |  | nan |
| C-d1-T3-baseline |  | nan |  | nan |
| C-d1-T4-baseline |  | nan |  | nan |

## 16. Direction balance per cell (val-selected on test)

| Cell | long | short |
|---|---|---|
| C-d1-T1 | 128786 | 92325 |
| C-d1-T2 | 101980 | 101907 |
| C-d1-T3 | 119673 | 119391 |
| C-d1-T4 | 92059 | 92059 |
| C-d1-target-control | 92394 | 92309 |
| C-d1-T1-baseline | 18308 | 16318 |
| C-d1-T2-baseline | 18308 | 16318 |
| C-d1-T3-baseline | 18287 | 16298 |
| C-d1-T4-baseline | 18308 | 16318 |

## 17. Per-pair Sharpe contribution per cell (DIAGNOSTIC-ONLY)

### C-d1-T1
| pair | n | Sharpe contribution |
|---|---|---|

### C-d1-T2
| pair | n | Sharpe contribution |
|---|---|---|

### C-d1-T3
| pair | n | Sharpe contribution |
|---|---|---|

### C-d1-T4
| pair | n | Sharpe contribution |
|---|---|---|

### C-d1-target-control
| pair | n | Sharpe contribution |
|---|---|---|

### C-d1-T1-baseline
| pair | n | Sharpe contribution |
|---|---|---|

### C-d1-T2-baseline
| pair | n | Sharpe contribution |
|---|---|---|

### C-d1-T3-baseline
| pair | n | Sharpe contribution |
|---|---|---|

### C-d1-T4-baseline
| pair | n | Sharpe contribution |
|---|---|---|

## 18. Top-tail regime audit per target (DIAGNOSTIC-ONLY; spread_at_signal_pip only)

**Note**: R7-C f5a/f5b/f5c features NOT computed (out of scope per Clause 6).

### T1
- population mean spread = +2.340
- q=10.0: top mean=+1.275 (Δ -1.064); n_top=51749
- q=20.0: top mean=+1.352 (Δ -0.988); n_top=103499

### T2
- population mean spread = +2.340
- q=10.0: top mean=+1.346 (Δ -0.994); n_top=51839
- q=20.0: top mean=+1.413 (Δ -0.927); n_top=103515

### T3
- population mean spread = +2.340
- q=10.0: top mean=+1.371 (Δ -0.969); n_top=51805
- q=20.0: top mean=+1.438 (Δ -0.902); n_top=103505

### T4
- population mean spread = +2.340
- q=10.0: top mean=+1.363 (Δ -0.977); n_top=51770
- q=20.0: top mean=+1.429 (Δ -0.911); n_top=103494

### TARGET_CONTROL
- population mean spread = +2.340
- q=10.0: top mean=+1.363 (Δ -0.977); n_top=51772
- q=20.0: top mean=+1.430 (Δ -0.910); n_top=103530

### T3 overlap rate (DIAGNOSTIC-ONLY WARN if > 10%)
- overall: 99.731% (2933086/2941012 signals); warn=True

## 19. R7-A new-feature NaN-rate check (sanity probe item)

| Split | Feature | n | NaN | rate |
|---|---|---|---|---|
| train | atr_at_signal_pip | 2941032 | 0 | 0.000% |
| train | spread_at_signal_pip | 2941032 | 0 | 0.000% |
| val | atr_at_signal_pip | 517422 | 0 | 0.000% |
| val | spread_at_signal_pip | 517422 | 0 | 0.000% |
| test | atr_at_signal_pip | 597666 | 0 | 0.000% |
| test | spread_at_signal_pip | 597666 | 0 | 0.000% |

## 20. Realised PnL distribution per target on TRAIN (DIAGNOSTIC)

- T1: n_finite=2941032 mean=-2.280 p5=-25.400 p50=-2.100 p95=+20.200
- T2: n_finite=2941032 mean=-2.217 p5=-8.915 p50=-2.965 p95=+7.546
- T3: n_finite=2941032 mean=-6.667 p5=-32.115 p50=-10.913 p95=+34.000
- T4: n_finite=2941032 mean=-2.003 p5=-6.061 p50=-2.338 p95=+1.500

## 21. Predicted PnL distribution per target (DIAGNOSTIC)

| Target | Split | n | mean | p5 | p50 | p95 |
|---|---|---|---|---|---|---|
| T1 | train | 2941032 | -2.221 | -2.629 | -2.215 | -1.813 |
| T1 | val | 517422 | -2.247 | -2.721 | -2.246 | -1.802 |
| T1 | test | 597666 | -2.276 | -2.728 | -2.259 | -1.826 |
| T2 | train | 2941032 | -3.163 | -4.331 | -3.234 | -1.839 |
| T2 | val | 517422 | -3.186 | -4.541 | -3.246 | -1.749 |
| T2 | test | 597666 | -3.306 | -4.541 | -3.351 | -1.871 |
| T3 | train | 2941032 | -8.738 | -9.715 | -8.861 | -6.689 |
| T3 | val | 517422 | -8.747 | -9.729 | -9.065 | -6.301 |
| T3 | test | 597666 | -8.863 | -9.729 | -9.038 | -6.806 |
| T4 | train | 2941032 | -2.751 | -5.340 | -2.450 | -1.167 |
| T4 | val | 517422 | -2.478 | -4.797 | -2.210 | -1.102 |
| T4 | test | 597666 | -2.753 | -5.271 | -2.492 | -1.190 |
| TARGET_CONTROL | train | 2941032 | -3.804 | -5.001 | -4.050 | -2.130 |
| TARGET_CONTROL | val | 517422 | -3.775 | -5.091 | -4.042 | -2.014 |
| TARGET_CONTROL | test | 597666 | -3.940 | -5.079 | -4.158 | -2.177 |

## 22. References

- PR #348 — Phase 29 kickoff (Scope III / Policy C / Option 9c)
- PR #349 — Phase 29 first-mover routing review (Path 2 A2 PRIMARY)
- PR #350 — Phase 29.0a-α A2 design memo (this sub-phase α)
- PR #325 — Phase 27.0d-β S-E regression (score backbone)
- PR #344 — Phase 28.0c-α A0-narrow design memo (25-section pattern source)
- PR #347 — Phase 28 closure memo (Phase 28 §10 archived reference)
- PR #334 — Phase 27 closure memo (R-T3 carry-forward source)
- PR #279 — γ closure
- Phase 22 frozen-OOS contract
- Phase 9.12 production v9 tip 79ed1e8 (untouched)

## 23. Caveats

- All test-set metrics outside the val-selected per-cell configuration are DIAGNOSTIC-ONLY and excluded from the formal H-D1 verdict.
- H2 PASS = PROMISING_BUT_NEEDS_OOS only. ADOPT_CANDIDATE wall preserved per Clause 1. NG#10 / NG#11 not relaxed.
- All 4 target variants (T1/T2/T3/T4) are D-1 executable and ADOPT_CANDIDATE-eligible. No DIAGNOSTIC-ONLY target variants in the closed allowlist (NG#A2-1).
- **A2-narrow vs A2-broad distinction**: failure of all 4 targets in the closed allowlist is `FALSIFIED_A2_NARROW`, NEVER `FALSIFIED_ALL_A2`. Alternate target framings outside the 4-target allowlist remain admissible via separate scope amendment.
- **R-T3 absorbed under T3** (multi-horizon variant; PR #347 §12). R-T3 standalone elevation NOT admissible.
- **Phase 28 §10 archived as DIAGNOSTIC-ONLY 2nd reference per Option 9c**; Phase 29 §10 per-target baseline reference is the formal FAIL-FAST gate.
- T3 overlap with next signal_ts (DIAGNOSTIC-ONLY WARN if > 10%); reported in §18.
- Top-tail regime audit uses `spread_at_signal_pip` only; R7-C features out of scope per Clause 6.

## 24. Cross-validation re-fits diagnostic (DIAGNOSTIC-ONLY)

5-fold OOF (seed=42) per-target on S-E backbone. Aggregate Pearson / Spearman per target reported in §5.

## 25. Sub-phase verdict snapshot

- per-target outcomes:
  - T1 (C-d1-T1): FALSIFIED_TARGET_INSUFFICIENT (row 3)
  - T2 (C-d1-T2): FALSIFIED_TARGET_INSUFFICIENT (row 3)
  - T3 (C-d1-T3): FALSIFIED_TARGET_INSUFFICIENT (row 3)
  - T4 (C-d1-T4): FALSIFIED_TARGET_INSUFFICIENT (row 3)
- aggregate verdict: REJECT_NON_DISCRIMINATIVE
- A2-narrow status: FALSIFIED_A2_NARROW
- R-T3 absorption status: FALSIFIED_under_T3
- routing implication: All 4 targets FALSIFIED_TARGET_INSUFFICIENT or PARTIAL_DRIFT_TARGET_REPLICA — A2 axis exhausted under tested closed 4-target allowlist. Result is FALSIFIED_A2_NARROW (NEVER FALSIFIED_ALL_A2). Alternate target framings outside closed 4-target allowlist remain admissible via separate scope amendment. Post-29.0a routing review compares A0-broad / R-B / A3 next-axis options.
- per-target baseline FAIL-FAST internal consistency: True
- C-d1-target-control drift vs 27.0d C-se: all_within_tolerance=True (6th-phase chain; WARN-only)

*End of `artifacts/stage29_0a/eval_report.md`.*
