# Phase 28.0c-β — A0-narrow Tabular Architecture-Topology Audit eval report

**Sub-phase**: 28.0c-β
**Design memo**: PR #344 (`phase28_0c_alpha_a0_architecture_redesign_design_memo.md`)
**Routing**: PR #343 (post-28.0b routing review; A0 primary)
**Scope**: A0-narrow tabular topology audit (NOT full A0-broad sequence/NN redesign)

**INTERPRETATION**: A negative result falsifies A0-narrow, not all possible A0. A0-broad (sequence / NN model classes) remains deferred-not-foreclosed per PR #344 §7.2.

## 1. Executive summary

Per-AR H-C3 outcome ladder (PR #344 §12.3; precedence row 4 > 1 > 2 > 3):

| AR | Cell | Outcome | Row | Reason |
|---|---|---|---|---|
| AR1 | C-a0-AR1 | FALSIFIED_ARCH_INSUFFICIENT | 3 | val Sharpe lift -0.1002 < +0.02 OR other H-C3 conditions failed |
| AR2 | C-a0-AR2 | FALSIFIED_ARCH_INSUFFICIENT | 3 | val Sharpe lift -0.2671 < +0.02 OR other H-C3 conditions failed |
| AR3 | C-a0-AR3 | FALSIFIED_ARCH_INSUFFICIENT | 3 | val Sharpe lift -0.0108 < +0.02 OR other H-C3 conditions failed |
| AR4 | C-a0-AR4 | FALSIFIED_ARCH_INSUFFICIENT | 3 | val Sharpe lift -0.4053 < +0.02 OR other H-C3 conditions failed |

**Aggregate verdict**: REJECT_NON_DISCRIMINATIVE
**A0-narrow status**: FALSIFIED_A0_NARROW
**A0-broad status**: deferred_not_foreclosed
**Routing implication**: All 4 AR variants FALSIFIED_ARCH_INSUFFICIENT or PARTIAL_DRIFT_ARCH_REPLICA — A0-narrow tabular topology axis exhausted. Result is FALSIFIED_A0_NARROW (NEVER FALSIFIED_ALL_A0). A0-broad sequence/NN remains deferred-not-foreclosed (PR #344 §7.2 / §12.2). Post-28.0c routing review MUST compare Path B (A0-broad scope amendment) vs Phase 28 closure / Phase 29 rebase.

> **EXPLICIT LABEL**: this result is `FALSIFIED_A0_NARROW`, NEVER `FALSIFIED_ALL_A0`. A0-broad sequence / NN model classes remain deferred-not-foreclosed; post-28.0c routing review MUST compare Path B (A0-broad scope amendment) vs Phase 28 closure / Phase 29 rebase.

**C-sb-baseline reproduction**: PASS
**C-a0-arch-control drift vs 27.0d C-se**: all_within_tolerance=True (warn=False; DIAGNOSTIC-ONLY)

## 2. Cells overview

| Cell | Picker | Score | Architecture |
|---|---|---|---|
| C-a0-AR1 | AR1(stage1_S-B → admit50%-per-pair-val-median → stage2_S-E) | ar1_hierarchical | hierarchical_two_stage |
| C-a0-AR2 | AR2(20 per-pair S-E specialists; 27.0d backbone verbatim) | ar2_pair_specialist | pair_conditioned_specialist_heads |
| C-a0-AR3 | AR3(0.5·rank(S-B raw) + 0.5·rank(S-E)) | ar3_stacked_blend | stacked_classifier_regressor_blend |
| C-a0-AR4 | AR4(deterministic regime split: per-pair val-median atr) | ar4_regime_split | deterministic_regime_split |
| C-a0-arch-control | S-E(vanilla regressor; sample_weight=1; arch-axis null) | arch_control | vanilla_s_e_27_0d_backbone |
| C-sb-baseline | S-B(raw_p_tp_minus_p_sl) | s_b_raw | multiclass_s_b_baseline |

## 3. Row-set policy / drop stats

**A0-narrow row-set policy** (PR #344 §9.2): all 6 cells share the R7-A-clean parent row-set; no R7-C row-drop. Fix A row-set isolation contract not exercised.

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
- AR1 admitted-train: total=2007219 (per-pair mean≈100361)
- AR2 per-pair train rows: mean=147052 p5=99686 p95=189484
- AR3 blend: w_S-B=0.5 w_S-E=0.5 (α-fixed; NG#A0-1)
- AR4 regime split: high_train=1785730 low_train=1155302 imbalance_warn_pairs=0

## 5. OOF correlation diagnostic — S-E control only (DIAGNOSTIC-ONLY)

- S-E control aggregate: pearson=+0.0748 spearman=+0.3836
- Per-AR OOF not run (impractical for AR2 with 20 specialists × 5 folds). S-E control OOF is the NG#A0-3 anchor; rule-axis + architecture-axis null.

## 6. Regression diagnostic — S-E control (DIAGNOSTIC-ONLY)

| Split | n | R² | MAE | MSE |
|---|---|---|---|---|
| train | 2941032 | -0.0401 | +4.435 | +nan |
| val | 517422 | -0.0454 | +3.177 | +nan |
| test | 597666 | -0.0366 | +3.932 | +nan |

## 7. Per-cell quantile family results

### C-a0-AR1 (AR1(stage1_S-B → admit50%-per-pair-val-median → stage2_S-E))

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | -2.512721 | -0.5774 | 12972 | -0.5579 | 9801 | -44853.5 |
| 10.0 | -2.741240 | -0.5408 | 25948 | -0.5222 | 21852 | -101297.1 |
| 20.0 | -3.307150 | -0.4877 | 51937 | -0.4583 | 53374 | -252233.3 |
| 30.0 | -3.871319 | -0.3586 | 77847 | -0.2903 | 93598 | -470583.6 |
| 40.0 | -4.089043 | -0.2865 | 103828 | -0.2392 | 145252 | -863007.5 |

### C-a0-AR2 (AR2(20 per-pair S-E specialists; 27.0d backbone verbatim))

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | -2.016130 | -0.7926 | 25873 | -0.8428 | 15123 | -68446.0 |
| 10.0 | -2.239627 | -0.7347 | 51753 | -0.7647 | 35420 | -165442.5 |
| 20.0 | -2.666128 | -0.6582 | 103488 | -0.5189 | 82247 | -397833.5 |
| 30.0 | -3.097787 | -0.5443 | 155230 | -0.3641 | 149081 | -746611.8 |
| 40.0 | -3.447517 | -0.4534 | 206994 | -0.3280 | 223584 | -1168029.3 |

### C-a0-AR3 (AR3(0.5·rank(S-B raw) + 0.5·rank(S-E)))

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | +0.727861 | -0.1971 | 25875 | -0.1802 | 56970 | -321149.1 |
| 10.0 | +0.705144 | -0.2149 | 51756 | -0.1920 | 84147 | -469107.0 |
| 20.0 | +0.670338 | -0.2487 | 103499 | -0.2147 | 135700 | -762146.0 |
| 30.0 | +0.628130 | -0.2710 | 155235 | -0.2333 | 192023 | -1099319.3 |
| 40.0 | +0.578593 | -0.2901 | 206969 | -0.2477 | 248721 | -1459502.7 |

### C-a0-AR4 (AR4(deterministic regime split: per-pair val-median atr))

| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |
|---|---|---|---|---|---|---|
| 5.0 | -1.999833 | -0.8024 | 25874 | -0.8441 | 15326 | -69433.8 |
| 10.0 | -2.211457 | -0.7370 | 51750 | -0.7690 | 35439 | -166003.3 |
| 20.0 | -2.658878 | -0.6701 | 103498 | -0.6656 | 78431 | -380379.2 |
| 30.0 | -3.157583 | -0.6290 | 155242 | -0.5975 | 128532 | -651696.1 |
| 40.0 | -3.640611 | -0.5916 | 206982 | -0.5187 | 183480 | -996557.3 |

### C-a0-arch-control (S-E(vanilla regressor; sample_weight=1; arch-axis null))

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

## 8. Val-selected (cell*, q*) cross-cell

- cell: id=C-sb-baseline picker=S-B(raw_p_tp_minus_p_sl) score_type=s_b_raw feature_set=r7a architecture=multiclass_s_b_baseline
- q*=5.0 cutoff=0.12623330653454912
- val Sharpe=-0.1863 (n=25881)
- test Sharpe=-0.1732 ann_pnl=-204664.4 n=34626 FORMAL Spearman=-0.1535

## 9. Cross-cell aggregate verdict

- aggregate verdict: SPLIT_VERDICT_ROUTE_TO_REVIEW
- agree: False
- branches: ['REJECT_BUT_INFORMATIVE_FLAT', 'REJECT_BUT_INFORMATIVE_IMPROVED', 'REJECT_NON_DISCRIMINATIVE']

## 10. §10 baseline reproduction (FAIL-FAST)

- n_trades: observed=34626 baseline=34626 delta=+0 match=True
- Sharpe: observed=-0.173164 baseline=-0.173200 delta=+3.550307e-05 match=True
- ann_pnl: observed=-204664.423 baseline=-204664.400 delta=-0.023 match=True
- all_match: True

## 11. Within-eval ablation drift (per AR vs C-a0-arch-control)

| AR | n_trades Δ | within | Sharpe Δ | within | ann_pnl Δ | within | all_within |
|---|---|---|---|---|---|---|---|
| AR1 | -39451 | False | +2.4389e-01 | False | +136822.892 | False | False |
| AR2 | 38881 | False | +1.5504e-01 | False | -168198.884 | False | False |
| AR3 | -127733 | False | +3.0288e-01 | False | +678681.278 | False | False |
| AR4 | -1223 | False | -3.5600e-02 | False | +3273.140 | True | False |

## 11b. C-a0-arch-control drift vs 27.0d C-se (DIAGNOSTIC-ONLY WARN)

**5-phase bit-reproduction chain**: 27.0d C-se → 27.0f r7a-replica → 28.0a r7a-replica → 28.0b top-q-control → 28.0c arch-control.

- source: artifacts/stage27_0d/sweep_results.json
- n_trades: observed=184703 baseline_27_0d=184703 delta=0 within=True
- Sharpe: observed=-0.483051 baseline_27_0d=-0.4830508944 delta=+3.0473e-11 within=True
- ann_pnl: observed=-999830.405 baseline_27_0d=-999830.4048230398 delta=+0.000 within=True
- all_within_tolerance: True
- WARN: False

## 12. Feature importance — S-E control regressor (DIAGNOSTIC-ONLY)

(unavailable: {'buckets': {'pair': 259.0, 'direction': 34.0, 'atr_at_signal_pip': 1978.0, 'spread_at_signal_pip': 697.0}, 'buckets_normalised': {'pair': 0.08726415094339622, 'direction': 0.011455525606469003, 'atr_at_signal_pip': 0.6664420485175202, 'spread_at_signal_pip': 0.23483827493261455}, 'total': 2968.0})

## 13. H-C3 outcome row binding per AR (A0-narrow scope; interpretation guards embedded)

Per PR #344 §12: H-C3 = A0-narrow tabular topology audit. Failure of all AR variants is `FALSIFIED_A0_NARROW`, NEVER `FALSIFIED_ALL_A0`. A0-broad sequence/NN model classes remain deferred-not-foreclosed per §7.2.

| AR | Cell | Outcome | Row | Sharpe lift vs §10 | val Sharpe | val n | cell Spearman | Notes |
|---|---|---|---|---|---|---|---|---|
| AR1 | C-a0-AR1 | FALSIFIED_ARCH_INSUFFICIENT | 3 | -0.1002 | -0.2865 | 103828 | +0.4055 | val Sharpe lift -0.1002 < +0.02 OR other H-C3 conditions failed |
| AR2 | C-a0-AR2 | FALSIFIED_ARCH_INSUFFICIENT | 3 | -0.2671 | -0.4534 | 206994 | +0.5248 | val Sharpe lift -0.2671 < +0.02 OR other H-C3 conditions failed |
| AR3 | C-a0-AR3 | FALSIFIED_ARCH_INSUFFICIENT | 3 | -0.0108 | -0.1971 | 25875 | -0.0590 | val Sharpe lift -0.0108 < +0.02 OR other H-C3 conditions failed |
| AR4 | C-a0-AR4 | FALSIFIED_ARCH_INSUFFICIENT | 3 | -0.4053 | -0.5916 | 206982 | +0.5981 | val Sharpe lift -0.4053 < +0.02 OR other H-C3 conditions failed |

**Aggregate H-C3 verdict**: REJECT_NON_DISCRIMINATIVE
**A0-narrow status**: FALSIFIED_A0_NARROW
**A0-broad status**: deferred_not_foreclosed
**Routing**: All 4 AR variants FALSIFIED_ARCH_INSUFFICIENT or PARTIAL_DRIFT_ARCH_REPLICA — A0-narrow tabular topology axis exhausted. Result is FALSIFIED_A0_NARROW (NEVER FALSIFIED_ALL_A0). A0-broad sequence/NN remains deferred-not-foreclosed (PR #344 §7.2 / §12.2). Post-28.0c routing review MUST compare Path B (A0-broad scope amendment) vs Phase 28 closure / Phase 29 rebase.

## 14. Trade-count budget audit — per AR + arch-control

| Cell | val_n_trades | test_n_trades |
|---|---|---|
| C-a0-AR1 | 103828 | 145252 |
| C-a0-AR2 | 206994 | 223584 |
| C-a0-AR3 | 25875 | 56970 |
| C-a0-AR4 | 206982 | 183480 |
| C-a0-arch-control | 206985 | 184703 |
| C-sb-baseline | 25881 | 34626 |

## 15. Pair concentration per cell (val-selected)

| Cell | val top-3 pairs | val Herfindahl | test top-3 | test Herfindahl |
|---|---|---|---|---|
| C-a0-AR1 |  | nan |  | nan |
| C-a0-AR2 |  | nan |  | nan |
| C-a0-AR3 |  | nan |  | nan |
| C-a0-AR4 |  | nan |  | nan |
| C-a0-arch-control |  | nan |  | nan |
| C-sb-baseline |  | nan |  | nan |

## 16. Direction balance per cell (val-selected on test)

| Cell | long | short |
|---|---|---|
| C-a0-AR1 | 73539 | 71713 |
| C-a0-AR2 | 113190 | 110394 |
| C-a0-AR3 | 29588 | 27382 |
| C-a0-AR4 | 91747 | 91733 |
| C-a0-arch-control | 92394 | 92309 |
| C-sb-baseline | 18308 | 16318 |

## 17. Per-pair Sharpe contribution per cell (DIAGNOSTIC-ONLY)

### C-a0-AR1
| pair | n | Sharpe contribution |
|---|---|---|

### C-a0-AR2
| pair | n | Sharpe contribution |
|---|---|---|

### C-a0-AR3
| pair | n | Sharpe contribution |
|---|---|---|

### C-a0-AR4
| pair | n | Sharpe contribution |
|---|---|---|

### C-a0-arch-control
| pair | n | Sharpe contribution |
|---|---|---|

### C-sb-baseline
| pair | n | Sharpe contribution |
|---|---|---|

## 18. Top-tail regime audit per AR (DIAGNOSTIC-ONLY; spread_at_signal_pip only)

**Note**: R7-C f5a/f5b/f5c features NOT computed (out of scope per Clause 6).

### AR1
- population mean spread = +2.340
- q=10.0: top mean=+1.346 (Δ -0.994); n_top=25948
- q=20.0: top mean=+1.398 (Δ -0.942); n_top=51937

### AR2
- population mean spread = +2.340
- q=10.0: top mean=+1.362 (Δ -0.978); n_top=51753
- q=20.0: top mean=+1.430 (Δ -0.910); n_top=103488

### AR3
- population mean spread = +2.340
- q=10.0: top mean=+1.527 (Δ -0.813); n_top=51756
- q=20.0: top mean=+1.553 (Δ -0.787); n_top=103499

### AR4
- population mean spread = +2.340
- q=10.0: top mean=+1.365 (Δ -0.974); n_top=51750
- q=20.0: top mean=+1.435 (Δ -0.904); n_top=103498

### arch_control
- population mean spread = +2.340
- q=10.0: top mean=+1.363 (Δ -0.977); n_top=51772
- q=20.0: top mean=+1.430 (Δ -0.910); n_top=103530

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

## 21. Predicted PnL distribution — S-E control (DIAGNOSTIC)

| Split | n | mean | p5 | p50 | p95 |
|---|---|---|---|---|---|
| train | 2941032 | -3.804 | -5.001 | -4.050 | -2.130 |
| val | 517422 | -3.775 | -5.091 | -4.042 | -2.014 |
| test | 597666 | -3.940 | -5.079 | -4.158 | -2.177 |

## 22. References

- PR #335 — Phase 28 kickoff
- PR #336 — Phase 28 first-mover routing review
- PR #339 — Phase 28 post-28.0a routing review
- PR #341 — Phase 28.0b-α A4 design memo
- PR #342 — Phase 28.0b-β A4 eval (R-T1 = FALSIFIED_under_A4)
- PR #343 — Phase 28 post-28.0b routing review (A0 primary)
- PR #344 — Phase 28.0c-α A0-narrow design memo (this sub-phase α)
- PR #325 — Phase 27.0d-β S-E regression (score backbone source)
- PR #332 — Phase 27.0f-β (within-eval ablation template)
- PR #334 — Phase 27 closure memo
- PR #279 — γ closure
- Phase 22 frozen-OOS contract
- Phase 9.12 production v9 tip 79ed1e8 (untouched)

## 23. Caveats

- All test-set metrics outside the val-selected per-cell configuration are DIAGNOSTIC-ONLY and excluded from the formal H-C3 verdict.
- H2 PASS = PROMISING_BUT_NEEDS_OOS only. ADOPT_CANDIDATE wall preserved per Clause 1. NG#10 / NG#11 not relaxed.
- **AR1 interpretation guard**: stage-1 admission threshold resembles 28.0b R1 selection-like behavior. Admitted under A0-narrow as architecture-conditioning of stage 2's training set, NOT final selection rule. PASS/PARTIAL_SUPPORT outcomes are 'architecture-topology with embedded admission gate', NOT 'pure architecture-only success'. NG#A0-1 enforces.
- **AR4 interpretation guard**: deterministic regime split is A3-boundary-sensitive but admitted under A0-narrow because routing is deterministic (no learned gating / MoE / adaptive weights). PASS/PARTIAL_SUPPORT outcomes are 'deterministic tabular regime split helped', NOT 'full A3 regime-conditioned modeling is solved'. A3 elevation requires separate scope amendment.
- **A0-narrow vs A0-broad distinction**: all 4 AR variants remain within tabular LightGBM. Failure of all 4 is `FALSIFIED_A0_NARROW`, NEVER `FALSIFIED_ALL_A0`. A0-broad sequence/NN model classes remain deferred-not-foreclosed per PR #344 §7.2.
- Top-tail regime audit uses `spread_at_signal_pip` only; R7-C features are out of scope per Clause 6.
- No fallback policy (NG#A0-1): AR1 admitted-train shortage / AR2 per-pair fit failure → HALT; AR4 regime imbalance → WARN-only. No fallback to global model / hyperparameter tuning / threshold adjustment.

## 24. Cross-validation re-fits diagnostic (DIAGNOSTIC-ONLY)

5-fold OOF (seed=42) on S-E control backbone (inherited from 27.0d). Per-AR OOF not run (impractical for AR2 with 20 specialists). Aggregate Pearson / Spearman reported in §5.

## 25. Sub-phase verdict snapshot

- per-AR outcomes:
  - AR1 (C-a0-AR1): FALSIFIED_ARCH_INSUFFICIENT (row 3)
  - AR2 (C-a0-AR2): FALSIFIED_ARCH_INSUFFICIENT (row 3)
  - AR3 (C-a0-AR3): FALSIFIED_ARCH_INSUFFICIENT (row 3)
  - AR4 (C-a0-AR4): FALSIFIED_ARCH_INSUFFICIENT (row 3)
- aggregate verdict: REJECT_NON_DISCRIMINATIVE
- A0-narrow status: FALSIFIED_A0_NARROW
- A0-broad status: deferred_not_foreclosed (PR #344 §7.2)
- routing implication: All 4 AR variants FALSIFIED_ARCH_INSUFFICIENT or PARTIAL_DRIFT_ARCH_REPLICA — A0-narrow tabular topology axis exhausted. Result is FALSIFIED_A0_NARROW (NEVER FALSIFIED_ALL_A0). A0-broad sequence/NN remains deferred-not-foreclosed (PR #344 §7.2 / §12.2). Post-28.0c routing review MUST compare Path B (A0-broad scope amendment) vs Phase 28 closure / Phase 29 rebase.
- C-sb-baseline reproduction: PASS
- C-a0-arch-control drift vs 27.0d C-se: all_within_tolerance=True (WARN-only)

*End of `artifacts/stage28_0c/eval_report.md`.*
