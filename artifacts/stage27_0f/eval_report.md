# Stage 27.0f-β — S-E + R7-C Regime/Context Feature Eval Report

Generated: 2026-05-15T18:18:45.044279+00:00

Design contract: `docs/design/phase27_0f_alpha_s_e_r7_c_regime_context_design_memo.md` (PR #331) under PR #330 (R7-C scope amendment), PR #323 (S-E scope amendment), Phase 27 kickoff (PR #316), and inherited Phase 26 framework (PR #311 / #313).

## 1. Mandatory clauses (clauses 1-5 verbatim; clause 6 = PR #330 §6 verbatim)

**1. Phase framing.** ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.

**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison / classification-quality / feature-importance / per-pair-Sharpe-contribution columns are diagnostic-only. 27.0c-27.0e extensions preserved. 27.0f extension: R7-C feature distribution + per-pair R7-C stats + top-tail regime audit + C-se-r7a-replica drift are diagnostic-only.

**3. γ closure preservation.** PR #279 is unmodified.

**4. Production-readiness preservation.** X-v2 OOS gating remains required. v9 20-pair (Phase 9.12) untouched. Phase 22 frozen-OOS contract preserved.

**5. NG#10 / NG#11 not relaxed.**

**6. Phase 27 scope.** R7-A admissible at kickoff. R7-C promoted from 'requires SEPARATE scope-amendment PR' to 'admissible at 27.0f-α design memo' via PR #330; on PR #331 merge the S-E + R7-C 3-cell structure became formal at 27.0f-β. Closed allowlist: [f5a_spread_z_50, f5b_volume_z_50, f5c_high_spread_low_vol_50]. R7-B requires its own scope amendment. R7-D / R7-Other NOT admissible. S-A/S-B/S-C admissible at kickoff; S-D 27.0c-β via PR #320; S-E 27.0d-β via PR #323; 27.0e R-T2 formal via PR #327. Phase 26 deferred items NOT subsumed.

## 2. D-1 binding (formal realised-PnL = inherited harness)

Formal realised-PnL uses inherited `_compute_realised_barrier_pnl` (bid/ask executable). Mid-to-mid PnL appears in sanity probe only. S-E regression target uses the SAME bid/ask harness.

## 3. R7-A + R7-C feature set (FIXED per 27.0f-α §2; 7 features total)

- R7-A (4 features; FIXED): ['pair', 'direction', 'atr_at_signal_pip', 'spread_at_signal_pip']
- R7-C (3 features; ADDITIVE; PR #330): ['f5a_spread_z_50', 'f5b_volume_z_50', 'f5c_high_spread_low_vol_50']
- R7-A + R7-C union (7 features): ['pair', 'direction', 'atr_at_signal_pip', 'spread_at_signal_pip', 'f5a_spread_z_50', 'f5b_volume_z_50', 'f5c_high_spread_low_vol_50']
- R7-C construction per Phase 25.0f-α §2.4 / §2.5 / §2.6 (shift(1) BEFORE rolling; lookback 50).

## 4. 3-cell definitions (per 27.0f-α §6.1)

- C-se-rcw: S-E on R7-A + R7-C (7 features); LightGBMRegressor + Huber α=0.9
- C-se-r7a-replica: S-E on R7-A only (4 features); within-eval ablation control
- C-sb-baseline: raw P(TP) - P(SL) on multiclass head; inheritance-chain check
- Quantile family for ALL 3 cells: {5, 10, 20, 30, 40}
- D10 amendment 3-artifact form: 1 regressor on R7-A+R7-C + 1 regressor on R7-A + 1 multiclass head

## 5. Sanity probe (per 27.0f-α §10)

- status: **PASS**
- R7-C volume pre-flight: PASS
  - TP: 564812 (19.218%)
  - SL: 2183576 (74.296%)
  - TIME: 190642 (6.487%)
- R7-C drop train: n_dropped=2002 (0.068%)
- R7-C drop val: n_dropped=2474 (0.478%)
- R7-C drop test: n_dropped=2396 (0.401%)

## 6. Pre-flight diagnostics + row-drop + split dates
- label rows (pre-drop): 4056120
- pairs: 20
- LightGBM: True
- formal cells run: 3
R7-A row-drop policy:
- train: n_input=2941032 n_kept=2941032 n_dropped=0
- val: n_input=517422 n_kept=517422 n_dropped=0
- test: n_input=597666 n_kept=597666 n_dropped=0
R7-C row-drop policy (Fix A: applied to C-se-rcw row-set ONLY; C-se-r7a-replica and C-sb-baseline evaluate on R7-A-clean parent):
- train: n_input=2941032 n_kept=2939030 n_dropped=2002 drop_frac=0.068% (C-se-rcw only)
- val: n_input=517422 n_kept=514948 n_dropped=2474 drop_frac=0.478% (C-se-rcw only)
- test: n_input=597666 n_kept=595270 n_dropped=2396 drop_frac=0.401% (C-se-rcw only)
Split dates:
- min: 2024-04-30 14:10:00+00:00
- train < 2025-09-23 12:11:00+00:00
- val [2025-09-23 12:11:00+00:00, 2026-01-10 23:45:30+00:00)
- test [2026-01-10 23:45:30+00:00, 2026-04-30 11:20:00+00:00]

## 7. All formal cells — primary quantile-family summary (3 cells × 5 q = 15 (cell, q) pairs)

| cell | picker | q% | cutoff | val_sharpe | val_ann_pnl | val_n | test_sharpe | test_ann_pnl | test_n | test_spearman | h_state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C-se-rcw | S-E(regressor_pred_r7a+r7c) | 40.0 | -3.6504 | -0.5782 | -1120862.7 | 205985 | -0.4869 | -993007.7 | 183691 | 0.4379 | OK |
| C-se-r7a-replica | S-E(regressor_pred_r7a_only) | 40.0 | -3.6496 | -0.5732 | -1127169.4 | 206985 | -0.4831 | -999830.4 | 184703 | 0.4381 | OK |
| C-sb-baseline | S-B(raw_p_tp_minus_p_sl) | 5.0 | +0.1262 | -0.1863 | -142234.1 | 25881 | -0.1732 | -204664.4 | 34626 | -0.1535 | OK |

## 8. Val-selected (cell\*, q\*) — FORMAL verdict source

- cell: id=C-sb-baseline picker=S-B(raw_p_tp_minus_p_sl) score_type=s_b_raw feature_set=r7a
- selected q%: 5.0
- selected cutoff: +0.126233
- val: n_trades=25881, Sharpe=-0.1863, ann_pnl=-142234.1
- test: n_trades=34626, Sharpe=-0.1732, ann_pnl=-204664.4
- FORMAL Spearman(score, realised_pnl) on test: -0.1535

## 9. Aggregate H1 / H2 / H3 / H4 outcome

- H1-weak (> 0.05): **False**
- H1-meaningful (≥ 0.1): **False**
- H2: **False**
- H3 (> -0.192): **True**
- H4 (≥ 0): **False**

### Verdict: **REJECT_NON_DISCRIMINATIVE** (H1_WEAK_FAIL)

**Note**: 27.0f-β cannot mint ADOPT_CANDIDATE. H2 PASS → PROMISING_BUT_NEEDS_OOS.

## 10. Cross-cell verdict aggregation (per 26.0c-α §7.2)
- per-cell branches: ['REJECT_BUT_INFORMATIVE_FLAT', 'REJECT_NON_DISCRIMINATIVE']
- cells agree: **False**
- aggregate verdict: **SPLIT_VERDICT_ROUTE_TO_REVIEW**
- C-se-rcw (S-E(regressor_pred_r7a+r7c)): REJECT_BUT_INFORMATIVE_FLAT (H1m_PASS_H2_FAIL_H3_FAIL)
- C-se-r7a-replica (S-E(regressor_pred_r7a_only)): REJECT_BUT_INFORMATIVE_FLAT (H1m_PASS_H2_FAIL_H3_FAIL)
- C-sb-baseline (S-B(raw_p_tp_minus_p_sl)): REJECT_NON_DISCRIMINATIVE (H1_WEAK_FAIL)

## 11. MANDATORY: Baseline comparison (per 27.0f-α §11.11; 6-column)

| Aspect | 26.0d R6-new-A C02 | 27.0b C-alpha0 / S-B | 27.0c C-sd / S-D | 27.0d C-se / S-E q=40 | 27.0e C-se-trimmed q=10 | 27.0f val-selected |
|---|---|---|---|---|---|---|
| Feature set | R7-A | R7-A | R7-A | R7-A | R7-A | R7-A or R7-A+R7-C per val-sel |
| Score | S-B | S-B | S-D | S-E | S-E (trimmed q) | S-E or S-B per val-sel |
| Cell signature | C02 | C-alpha0 | C-sd | C-se | C-se-trimmed | id=C-sb-baseline picker=S-B(raw_p_tp_minus_p_sl) score_type=s_b_raw feature_set=r7a |
| Test n_trades | 34,626 | 34,626 | 32,324 | 184,703 | 35,439 | 34626 |
| Test Sharpe | -0.1732 | -0.1732 | -0.1760 | -0.4830 | -0.7670 | -0.1732 |
| Test Spearman | -0.1535 | -0.1535 | -0.1060 | +0.4381 | +0.4381 | -0.1535 |
| Verdict | REJECT (+ YES_IMPROVED) | REJECT_ND | REJECT_ND | SPLIT_VERDICT | SPLIT_VERDICT | REJECT_NON_DISCRIMINATIVE |

## 12. MANDATORY: C-sb-baseline reproduction check (per 27.0f-α §7.1)

- n_trades: observed=34626 baseline=34626 delta=+0 match=**True**
- Sharpe: observed=-0.173164 baseline=-0.173200 delta=+0.000036 (tolerance ±0.0001) match=**True**
- ann_pnl: observed=-204664.423 baseline=-204664.400 delta=-0.023 (tolerance ±0.5) match=**True**
- **all_match: True**

## 13. MANDATORY: C-se-r7a-replica reproduction check vs 27.0d C-se (DIAGNOSTIC-ONLY WARN)

- source: `artifacts/stage27_0d/sweep_results.json`
- n_trades: observed=184703 27.0d_baseline=184703 delta=0 within_tolerance=True
- Sharpe: observed=-0.483051 27.0d_baseline=-0.4830508944 delta=3.047273544609652e-11 within_tolerance=True
- ann_pnl: observed=-999830.405 27.0d_baseline=-999830.4048230398 delta=0.0 within_tolerance=True
- all_within_tolerance: True
- **drift WARN: False** (DIAGNOSTIC-ONLY; not HALT)

## 14. MANDATORY: Per-pair Sharpe contribution table (val-selected; D4 sort)

| pair | n_trades | sharpe | share_of_total_pnl | share_of_total_trades |
|---|---|---|---|---|
| USD_JPY | 24721 | -0.1803 | +0.6520 | 0.7139 |
| GBP_USD | 3568 | -0.1677 | +0.1139 | 0.1030 |
| EUR_USD | 1833 | -0.1812 | +0.0557 | 0.0529 |
| GBP_JPY | 985 | -0.1711 | +0.0539 | 0.0284 |
| AUD_USD | 1803 | -0.1631 | +0.0498 | 0.0521 |
| EUR_JPY | 654 | -0.2171 | +0.0370 | 0.0189 |
| AUD_JPY | 657 | -0.1883 | +0.0300 | 0.0190 |
| USD_CAD | 350 | -0.1374 | +0.0088 | 0.0101 |
| EUR_AUD | 2 | -0.5188 | +0.0001 | 0.0001 |
| USD_CHF | 34 | -0.0098 | +0.0001 | 0.0010 |
| CHF_JPY | 7 | 0.0345 | -0.0001 | 0.0002 |
| NZD_USD | 12 | 0.3557 | -0.0013 | 0.0003 |
- total_n_trades: 34626; total_pnl: -61357.30

## 15. MANDATORY: Pair concentration per cell

| cell | q% | val_top_pair | val_top_share | val_conc_high | test_top_pair | test_top_share |
|---|---|---|---|---|---|---|
| C-se-rcw | 40.0 | AUD_USD | 0.1514 | False | NZD_USD | 0.1450 |
| C-se-r7a-replica | 40.0 | AUD_USD | 0.1513 | False | NZD_USD | 0.1446 |
| C-sb-baseline | 5.0 | USD_JPY | 0.8685 | True | USD_JPY | 0.7139 |

## 16. Classification-quality diagnostics on multiclass head (DIAGNOSTIC-ONLY)

| cell | AUC(P(TP)) | Cohen κ | logloss |
|---|---|---|---|
| C-se-rcw | 0.5763 | 0.0985 | 1.0342 |
| C-se-r7a-replica | 0.5765 | 0.0986 | 1.0338 |
| C-sb-baseline | 0.5765 | 0.0986 | 1.0338 |

## 17. Regressor feature importance (DIAGNOSTIC-ONLY)

### C-se-rcw (R7-A + R7-C; 7 features)
- pair (gain): 261.0 (0.088)
- direction (gain): 32.0 (0.011)
- atr_at_signal_pip (gain): 1977.0 (0.666)
- spread_at_signal_pip (gain): 698.0 (0.235)
- f5a_spread_z_50 (gain): 0.0 (0.000)
- f5b_volume_z_50 (gain): 0.0 (0.000)
- f5c_high_spread_low_vol_50 (gain): 0.0 (0.000)

### C-se-r7a-replica (R7-A only; 4 features)
- pair (gain): 259.0 (0.087)
- direction (gain): 34.0 (0.011)
- atr_at_signal_pip (gain): 1978.0 (0.666)
- spread_at_signal_pip (gain): 697.0 (0.235)

## 18. Predicted-PnL distribution train/val/test for C-se-rcw (DIAGNOSTIC-ONLY)

| split | n_finite | p5 | p50 | p95 | mean |
|---|---|---|---|---|---|
| train | 2939030 | -5.0023 | -4.0489 | -2.1313 | -3.8037 |
| val | 514948 | -5.0895 | -4.0411 | -2.0117 | -3.7745 |
| test | 595270 | -5.0756 | -4.1588 | -2.1763 | -3.9406 |

## 19. Predicted-vs-realised correlation (DIAGNOSTIC-ONLY)

| split | n | Pearson | Spearman |
|---|---|---|---|
| OOF aggregate | n/a | +0.0749 | +0.3838 |
| train (refit) | 2939030 | +0.0751 | +0.3842 |
| val | 514948 | +0.1364 | +0.5041 |
| test | 595270 | +0.1143 | +0.4379 |

## 20. Regressor MAE + R² (DIAGNOSTIC-ONLY)

| split | n | MAE | R² |
|---|---|---|---|
| train | 2939030 | 4.4346 | -0.0401 |
| val | 514948 | 3.1777 | -0.0454 |
| test | 595270 | 3.9374 | -0.0364 |

## 21. Multiple-testing caveat
3 formal cells × per-cell quantile counts (sum) = 15 (cell, q) pairs (up from 10 in 27.0e → §22 H-B6 outcome row pre-stated to mitigate exposure). PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE are hypothesis-generating only.

## 22. H-B6 falsification outcome (per 27.0f-α §7; design-memo binding)

- **outcome: FALSIFIED_R7C_INSUFFICIENT**
- row matched: 3
- routing implication: regime features don't help; bottleneck is elsewhere; route to R-B (different feature axis) OR R-T1 / R-T3 / R-E
- C-se-rcw cell Spearman: +0.4379
- max-q delta-Sharpe (C-se-rcw - C-se-r7a-replica): +0.0029
- max abs delta-Sharpe: +0.0039
- Per-q delta-Sharpe:
  - q=5.0: delta_sharpe=+0.0029
  - q=10.0: delta_sharpe=-0.0020
  - q=20.0: delta_sharpe=+0.0002
  - q=30.0: delta_sharpe=+0.0002
  - q=40.0: delta_sharpe=-0.0039

## 23. NEW: Top-tail regime audit (DIAGNOSTIC-ONLY; H-B6 mechanism diagnosis)

Population: f5a=+0.0023, f5b=+0.1924, f5c activation=2.5%

| q% | n_trades_val | mean_f5a | Δpop_f5a | mean_f5b | Δpop_f5b | f5c_true % | Δpop_f5c |
|---|---|---|---|---|---|---|---|
| 10.0 | 51553 | -0.2504 | -0.2527 | +0.0301 | -0.1623 | 2.2% | -0.4% |
| 20.0 | 102996 | -0.1104 | -0.1128 | +0.0929 | -0.0995 | 2.8% | +0.3% |

## 24. NEW: C-se-r7a-replica vs 27.0d C-se delta (DIAGNOSTIC-ONLY)

- source: `artifacts/stage27_0d/sweep_results.json`
- n_trades delta: 0 (tolerance ±100)
- Sharpe delta: 3.047273544609652e-11 (tolerance ±0.005)
- ann_pnl delta: 0.0 (tolerance ±0.5% of magnitude)
- all_within_tolerance: True

## 25. Verdict statement: **REJECT_NON_DISCRIMINATIVE** (C-sb-baseline match: True; H-B6 outcome: FALSIFIED_R7C_INSUFFICIENT)
