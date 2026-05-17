# Phase 28.0b-β — A4 Monetisation-Aware Selection eval report

**Sub-phase**: 28.0b-β
**Design memo**: PR #341 (`phase28_0b_alpha_a4_monetisation_aware_selection_design_memo.md`)
**Scope amendment**: PR #340 (`phase28_scope_amendment_a4_non_quantile_cells.md`)
**Routing**: PR #339 (post-28.0a routing review; A4 primary)

## 1. Executive summary

Per-rule H-C2 outcome ladder (PR #341 §10.2; precedence row 4 > 1 > 2 > 3):

| Rule | Outcome | Row | Reason |
|---|---|---|---|
| C-a4-R1 | FALSIFIED_RULE_INSUFFICIENT | 3 | val Sharpe lift -0.2217 < +0.02 OR other H-C2 conditions failed |
| C-a4-R2 | FALSIFIED_RULE_INSUFFICIENT | 3 | val Sharpe lift -0.1304 < +0.02 OR other H-C2 conditions failed |
| C-a4-R3 | FALSIFIED_RULE_INSUFFICIENT | 3 | val Sharpe lift -0.1399 < +0.02 OR other H-C2 conditions failed |
| C-a4-R4 | FALSIFIED_RULE_INSUFFICIENT | 3 | val Sharpe lift -0.4589 < +0.02 OR other H-C2 conditions failed |

**Aggregate verdict**: REJECT_NON_DISCRIMINATIVE
**Routing implication**: All 4 rules FALSIFIED_RULE_INSUFFICIENT or PARTIAL_DRIFT — selection-rule axis exhausted. Route to A0 architecture redesign. R-T1 falsified under A4 absorption.
**R-T1 absorption status under A4**: FALSIFIED_under_A4

**C-sb-baseline reproduction**: PASS
**C-a4-top-q-control drift vs 27.0d C-se**: all_within_tolerance=True (warn=False; DIAGNOSTIC-ONLY)

## 2. Cells overview

| Cell | Picker | Score | Feature set | Rule | Rule kind |
|---|---|---|---|---|---|
| C-a4-R1 | S-E + R1(absolute_threshold_per_pair_median) | s_e_r1 | r7a | r1_absolute_threshold | non_quantile |
| C-a4-R2 | S-E + R2(middle_bulk_40_60) | s_e_r2 | r7a | r2_middle_bulk | quantile_range |
| C-a4-R3 | S-E + R3(per_pair_q95) | s_e_r3 | r7a | r3_per_pair_quantile | quantile_per_pair |
| C-a4-R4 | S-E + R4(top_k_per_bar_k1) | s_e_r4 | r7a | r4_top_k_per_bar | non_quantile |
| C-a4-top-q-control | S-E(regressor_pred; top-q vanilla) | s_e_topq | r7a | top_q_vanilla | quantile_topq |
| C-sb-baseline | S-B(raw_p_tp_minus_p_sl) | s_b_raw | r7a | top_q_baseline | quantile_topq |

## 3. Row-set policy / drop stats

**A4-specific row-set policy** (PR #341 §7.2): all 6 cells share the R7-A-clean parent row-set; no R7-C row-drop is applied in this sub-phase. Fix A row-set isolation contract is not exercised here. PR #340 Clause 2 amendment admits non-quantile cells (R1 / R4) within A4 scope.

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
- R1 c_per_pair (val-median): n_pairs=20 mean=-3.7602
- R2 cutoffs (global [40, 60]): lo=-4.2511 hi=-3.6496
- R3 cutoff_per_pair (val-percentile 95): n_pairs=20 mean=-2.9277
- R4 K=1 verification: traded_mask sum = n_unique_signal_ts = 20922 (PASS)

## 5. OOF correlation diagnostic — S-E only (DIAGNOSTIC-ONLY)

- S-E aggregate: pearson=+0.0748 spearman=+0.3836
- Rule cells (R1/R2/R3/R4) share the same S-E score; per-rule OOF is irrelevant (rules are deterministic post-fit operations).

## 6. Regression diagnostic — S-E only (DIAGNOSTIC-ONLY)

| Split | n | R² | MAE | MSE |
|---|---|---|---|---|
| train | 2941032 | -0.0401 | +4.435 | +nan |
| val | 517422 | -0.0454 | +3.177 | +nan |
| test | 597666 | -0.0366 | +3.932 | +nan |

## 7. Per-cell results

### C-a4-R1 (S-E + R1(absolute_threshold_per_pair_median))

- val Sharpe=-0.4080
- val n_trades=258186
- val cell Spearman(score, pnl)=+0.5445
- test Sharpe=-0.3561
- test n_trades=237681
- test ann_pnl=-2127239.4

### C-a4-R2 (S-E + R2(middle_bulk_40_60))

- val Sharpe=-0.3167
- val n_trades=103508
- val cell Spearman(score, pnl)=+0.2897
- test Sharpe=-0.2716
- test n_trades=157499
- test ann_pnl=-1194802.2

### C-a4-R3 (S-E + R3(per_pair_q95))

- val Sharpe=-0.3262
- val n_trades=26878
- val cell Spearman(score, pnl)=+0.5683
- test Sharpe=-0.2790
- test n_trades=23081
- test ann_pnl=-254490.9

### C-a4-R4 (S-E + R4(top_k_per_bar_k1))

- val Sharpe=-0.6452
- val n_trades=20922
- val cell Spearman(score, pnl)=+0.6172
- test Sharpe=-0.4908
- test n_trades=21552
- test ann_pnl=-103384.6

### C-a4-top-q-control (S-E(regressor_pred; top-q vanilla))

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

## 8. Val-selection (cell\*, q\* or rule-cell\*)

- cell: id=C-sb-baseline picker=S-B(raw_p_tp_minus_p_sl) score_type=s_b_raw feature_set=r7a rule=top_q_baseline
- q*=5.0 cutoff=0.12623330653454912
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

## 11. Within-eval ablation drift (per rule vs C-a4-top-q-control)

| Rule | n_trades Δ | within | Sharpe Δ | within | ann_pnl Δ | within | all_within |
|---|---|---|---|---|---|---|---|
| R1 | 52978 | False | +1.2692e-01 | False | -1127408.986 | False | False |
| R2 | -27204 | False | +2.1147e-01 | False | -194971.805 | False | False |
| R3 | -161622 | False | +2.0400e-01 | False | +745339.482 | False | False |
| R4 | -163151 | False | -7.7344e-03 | False | +896445.788 | False | False |

## 11b. C-a4-top-q-control drift vs 27.0d C-se (DIAGNOSTIC-ONLY WARN)

- source: artifacts/stage27_0d/sweep_results.json
- n_trades: observed=184703 baseline_27_0d=184703 delta=0 within=True
- Sharpe: observed=-0.483051 baseline_27_0d=-0.4830508944 delta=+3.0473e-11 within=True
- ann_pnl: observed=-999830.405 baseline_27_0d=-999830.4048230398 delta=+0.000 within=True
- all_within_tolerance: True
- WARN: False

## 12. Feature importance — S-E regressor (DIAGNOSTIC-ONLY)

(unavailable: {'buckets': {'pair': 259.0, 'direction': 34.0, 'atr_at_signal_pip': 1978.0, 'spread_at_signal_pip': 697.0}, 'buckets_normalised': {'pair': 0.08726415094339622, 'direction': 0.011455525606469003, 'atr_at_signal_pip': 0.6664420485175202, 'spread_at_signal_pip': 0.23483827493261455}, 'total': 2968.0})

## 13. H-C2 outcome row binding per rule (= R-T1 elevation under A4 frame resolution)

Per PR #341 §3 / §10 / §14: H-C2 = R-T1 elevation under A4 frame. The per-rule outcomes below resolve the R-T1 carry-forward inside Phase 28.

| Rule | Outcome | Row | Sharpe lift vs §10 | val Sharpe | val n | cell Spearman | Notes |
|---|---|---|---|---|---|---|---|
| C-a4-R1 | FALSIFIED_RULE_INSUFFICIENT | 3 | -0.2217 | -0.4080 | 258186 | +0.5445 | val Sharpe lift -0.2217 < +0.02 OR other H-C2 conditions fai |
| C-a4-R2 | FALSIFIED_RULE_INSUFFICIENT | 3 | -0.1304 | -0.3167 | 103508 | +0.2897 | val Sharpe lift -0.1304 < +0.02 OR other H-C2 conditions fai |
| C-a4-R3 | FALSIFIED_RULE_INSUFFICIENT | 3 | -0.1399 | -0.3262 | 26878 | +0.5683 | val Sharpe lift -0.1399 < +0.02 OR other H-C2 conditions fai |
| C-a4-R4 | FALSIFIED_RULE_INSUFFICIENT | 3 | -0.4589 | -0.6452 | 20922 | +0.6172 | val Sharpe lift -0.4589 < +0.02 OR other H-C2 conditions fai |

**Aggregate H-C2 verdict**: REJECT_NON_DISCRIMINATIVE
**Routing**: All 4 rules FALSIFIED_RULE_INSUFFICIENT or PARTIAL_DRIFT — selection-rule axis exhausted. Route to A0 architecture redesign. R-T1 falsified under A4 absorption.
**R-T1 absorption status**: FALSIFIED_under_A4

## 14. Trade-count budget audit — C-a4-top-q-control

| q% | n_trades | inflation |
|---|---|---|
| 5.0 | 0 | 1.004x |
| 10.0 | 0 | 2.000x |
| 20.0 | 0 | 4.000x |
| 30.0 | 0 | 6.001x |
| 40.0 | 0 | 7.998x |

Note: rule cells (R1 / R2 / R3 / R4) are single-cell; n_trades is reported directly in §7 above.

## 15. Pair concentration per cell (val-selected)

| Cell | val top-3 pairs | val Herfindahl | test top-3 | test Herfindahl |
|---|---|---|---|---|
| C-a4-R1 | - | nan | - | nan |
| C-a4-R2 | - | nan | - | nan |
| C-a4-R3 | - | nan | - | nan |
| C-a4-R4 | - | nan | - | nan |
| C-a4-top-q-control | - | nan | - | nan |
| C-sb-baseline | - | nan | - | nan |

## 16. Direction balance per cell (val-selected on test)

| Cell | long | short |
|---|---|---|
| C-a4-R1 | 119413 | 118268 |
| C-a4-R2 | 78760 | 78739 |
| C-a4-R3 | 11640 | 11441 |
| C-a4-R4 | 14151 | 7401 |
| C-a4-top-q-control | 92394 | 92309 |
| C-sb-baseline | 18308 | 16318 |

## 17. Per-pair Sharpe contribution per cell (DIAGNOSTIC-ONLY)

### C-a4-R1
| pair | n | Sharpe contribution |
|---|---|---|

### C-a4-R2
| pair | n | Sharpe contribution |
|---|---|---|

### C-a4-R3
| pair | n | Sharpe contribution |
|---|---|---|

### C-a4-R4
| pair | n | Sharpe contribution |
|---|---|---|

### C-a4-top-q-control
| pair | n | Sharpe contribution |
|---|---|---|

### C-sb-baseline
| pair | n | Sharpe contribution |
|---|---|---|

## 18. Top-tail regime audit per rule (DIAGNOSTIC-ONLY; spread_at_signal_pip only)

**Note**: R7-C f5a/f5b/f5c features are NOT computed in this sub-phase (out of scope per Clause 6). Audit uses `spread_at_signal_pip` (R7-A) only.

### R1
- population mean spread = +2.340 (p50 +2.100)
- q=10.0: top mean=+1.363 (Δ -0.977); n_top=51772
- q=20.0: top mean=+1.430 (Δ -0.910); n_top=103530

### R2
- population mean spread = +2.340 (p50 +2.100)
- q=10.0: top mean=+1.363 (Δ -0.977); n_top=51772
- q=20.0: top mean=+1.430 (Δ -0.910); n_top=103530

### R3
- population mean spread = +2.340 (p50 +2.100)
- q=10.0: top mean=+1.363 (Δ -0.977); n_top=51772
- q=20.0: top mean=+1.430 (Δ -0.910); n_top=103530

### R4
- population mean spread = +2.340 (p50 +2.100)
- q=10.0: top mean=+1.363 (Δ -0.977); n_top=51772
- q=20.0: top mean=+1.430 (Δ -0.910); n_top=103530

### top_q_control
- population mean spread = +2.340 (p50 +2.100)
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

## 21. Predicted PnL distribution — S-E (DIAGNOSTIC)

| Split | n | mean | p5 | p50 | p95 |
|---|---|---|---|---|---|
| train | 2941032 | -3.804 | -5.001 | -4.050 | -2.130 |
| val | 517422 | -3.775 | -5.091 | -4.042 | -2.014 |
| test | 597666 | -3.940 | -5.079 | -4.158 | -2.177 |

## 22. References

- PR #335 — Phase 28 kickoff
- PR #336 — Phase 28 first-mover routing review
- PR #339 — Phase 28 post-28.0a routing review (A4 primary)
- PR #340 — Phase 28 scope amendment A4 non-quantile cells
- PR #341 — Phase 28.0b-α A4 design memo (this sub-phase α)
- PR #325 — Phase 27.0d-β S-E regression (score backbone source)
- PR #332 — Phase 27.0f-β (within-eval ablation template)
- PR #334 — Phase 27 closure memo (R-T1 carry-forward source)
- PR #338 — Phase 28.0a-β A1 objective redesign (6-eval picture)
- PR #279 — γ closure
- Phase 22 frozen-OOS contract
- Phase 9.12 production v9 tip 79ed1e8 (untouched)

## 23. Caveats

- All test-set metrics outside the val-selected per-cell configuration are DIAGNOSTIC-ONLY and excluded from the formal H-C2 verdict.
- H2 PASS = PROMISING_BUT_NEEDS_OOS only. ADOPT_CANDIDATE wall preserved per Clause 1. NG#10 / NG#11 not relaxed.
- R-T1 absorption: per PR #341 §3, R-T1 carry-forward is formally absorbed under A4 sub-phase scope. §13 outcome row binding = R-T1 elevation resolution. No independent R-T1 elevation.
- S-E score source fixed per NG#A4-1; L2 / L3 NOT admissible. Score-axis variation requires memo amendment to revive A1.
- Top-tail regime audit uses `spread_at_signal_pip` only; R7-C features are out of scope per Clause 6.

## 24. Cross-validation re-fits diagnostic (DIAGNOSTIC-ONLY)

5-fold OOF (seed=42) on S-E score backbone (inherited from 27.0d). Rule cells (R1/R2/R3/R4) are deterministic post-fit operations and share the same OOF diagnostic via S-E. Aggregate Pearson / Spearman are reported in §5.

## 25. Sub-phase verdict snapshot

- per-rule outcomes:
  - C-a4-R1: FALSIFIED_RULE_INSUFFICIENT (row 3)
  - C-a4-R2: FALSIFIED_RULE_INSUFFICIENT (row 3)
  - C-a4-R3: FALSIFIED_RULE_INSUFFICIENT (row 3)
  - C-a4-R4: FALSIFIED_RULE_INSUFFICIENT (row 3)
- aggregate verdict: REJECT_NON_DISCRIMINATIVE
- routing implication: All 4 rules FALSIFIED_RULE_INSUFFICIENT or PARTIAL_DRIFT — selection-rule axis exhausted. Route to A0 architecture redesign. R-T1 falsified under A4 absorption.
- R-T1 absorption status under A4: FALSIFIED_under_A4
- C-sb-baseline reproduction: PASS
- C-a4-top-q-control drift vs 27.0d C-se: all_within_tolerance=True (WARN-only)

*End of `artifacts/stage28_0b/eval_report.md`.*
