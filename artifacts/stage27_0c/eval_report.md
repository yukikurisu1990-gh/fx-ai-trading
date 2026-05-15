# Stage 27.0c-β — S-D Calibrated EV Eval Report

Generated: 2026-05-15T13:34:21.564879+00:00

Design contract: `docs/design/phase27_0c_alpha_s_d_calibrated_ev_design_memo.md` (PR #320) under Phase 27 kickoff (PR #316), post-27.0b routing review (PR #319), and inherited Phase 26 framework (PR #311 / PR #313).

## 1. Mandatory clauses (clauses 1-5 verbatim; clause 6 = Phase 27 kickoff §8)

**1. Phase framing.** ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.

**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison / classification-quality / feature-importance / per-pair-Sharpe-contribution columns are diagnostic-only. 27.0c extends: conditional-PnL estimator constants and calibration reliability diagrams are diagnostic-only.

**3. γ closure preservation.** PR #279 is unmodified.

**4. Production-readiness preservation.** X-v2 OOS gating remains required. v9 20-pair (Phase 9.12) untouched. Phase 22 frozen-OOS contract preserved.

**5. NG#10 / NG#11 not relaxed.**

**6. Phase 27 scope.** R7-A admissible at kickoff; R7-B/C require separate scope amendments; R7-D NOT admissible. S-A/S-B/S-C formal at kickoff; S-D promoted to formal at 27.0c-β per kickoff §5 / PR #320; S-E requires separate amendment; S-Other NOT admissible. Phase 26 deferred items NOT subsumed.

## 2. D-1 binding (formal realised-PnL = inherited harness)

Formal realised-PnL uses inherited `_compute_realised_barrier_pnl` (bid/ask executable). Mid-to-mid PnL appears in sanity probe only. Conditional-PnL estimator Ê[PnL|c] uses the SAME bid/ask executable harness on train rows.

## 3. R7-A feature set (FIXED per Phase 27.0c-α §2)

- ADMITTED: ['pair', 'direction', 'atr_at_signal_pip', 'spread_at_signal_pip']
- NO new feature additions in 27.0c.

## 4. S-D + S-B-baseline cell definitions (per 27.0c-α §7.1)

- C-sd: S-D(row) = Σ_c P_cal(c|row) · Ê[PnL|c] (calibrated EV)
- C-sb-baseline: S-B(row) = raw P(TP) - P(SL) on refit-on-full-train head
- 5-fold OOF protocol (seed=42); isotonic per class + per-row sum-to-1
- C-sb-baseline must reproduce 27.0b C-alpha0 (n_trades=34,626 / Sharpe=-0.1732 / ann_pnl=-204,664.4) or HALT with BaselineMismatchError

## 5. Sanity probe (per 27.0c-α §10)

- status: **PASS**
  - TP: 565106 (19.215%)
  - SL: 2184896 (74.290%)
  - TIME: 191030 (6.495%)
- OOF fold sizes (seed=42): [588207, 588207, 588206, 588206, 588206] max_delta=1
- zero-sum-row fallback: val=0 test=0 (HALT > 0 per D-I11)

## 6. Pre-flight diagnostics + row-drop + split dates
- label rows (pre-drop): 4056120
- pairs: 20
- LightGBM: True
- formal cells run: 2
Row-drop policy (R7-A inherited):
- train: n_input=2941032 n_kept=2941032 n_dropped=0
- val: n_input=517422 n_kept=517422 n_dropped=0
- test: n_input=597666 n_kept=597666 n_dropped=0
Split dates:
- min: 2024-04-30 14:10:00+00:00
- train < 2025-09-23 12:11:00+00:00
- val [2025-09-23 12:11:00+00:00, 2026-01-10 23:45:30+00:00)
- test [2026-01-10 23:45:30+00:00, 2026-04-30 11:20:00+00:00]

## 7. All formal cells — primary quantile-family summary

| cell | picker | q% | cutoff | val_sharpe | val_ann_pnl | val_n | test_sharpe | test_ann_pnl | test_n | test_spearman | h_state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C-sd | S-D(calibrated_ev) | 5 | -1.3872 | -0.1898 | -142110.1 | 25887 | -0.1760 | -188303.2 | 32324 | -0.1060 | OK |
| C-sb-baseline | S-B(raw_p_tp_minus_p_sl) | 5 | +0.1262 | -0.1863 | -142234.1 | 25881 | -0.1732 | -204664.4 | 34626 | -0.1535 | OK |

## 8. Val-selected (cell\*, q\*) — FORMAL verdict source

- cell: id=C-sb-baseline picker=S-B(raw_p_tp_minus_p_sl) score_type=s_b_raw
- selected q%: 5
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

**Note**: 27.0c-β cannot mint ADOPT_CANDIDATE. H2 PASS → PROMISING_BUT_NEEDS_OOS.

## 10. Cross-cell verdict aggregation (per 26.0c-α §7.2)
- per-cell branches: ['REJECT_NON_DISCRIMINATIVE']
- cells agree: **True**
- aggregate verdict: **REJECT_NON_DISCRIMINATIVE**
- C-sd (S-D(calibrated_ev)): REJECT_NON_DISCRIMINATIVE (H1_WEAK_FAIL)
- C-sb-baseline (S-B(raw_p_tp_minus_p_sl)): REJECT_NON_DISCRIMINATIVE (H1_WEAK_FAIL)

## 11. MANDATORY: Baseline comparison (per 27.0c-α §11.11)

| Aspect | 26.0c L-1 C02 (#309) | 26.0d R6-new-A C02 (#313) | 27.0b C-alpha0 / S-B (#318) | 27.0c val-selected |
|---|---|---|---|---|
| Feature set | pair + direction | + atr + spread (R7-A) | + atr + spread (R7-A) | + atr + spread (R7-A) |
| Score objective | S-B | S-B | S-B (≡ α=0.0 of S-C) | S-D or S-B per val-sel |
| Cell signature | C02 P(TP)-P(SL) | C02 P(TP)-P(SL) | C-alpha0 (α=0.0) | id=C-sb-baseline picker=S-B(raw_p_tp_minus_p_sl) score_type=s_b_raw |
| Test n_trades | 42,150 | 34,626 | 34,626 | 34626 |
| Test Sharpe | -0.2232 | -0.1732 | -0.1732 | -0.1732 |
| Test ann_pnl | -237,310.8 | -204,664.4 | -204,664.4 | -204664.4 |
| Test Spearman | -0.1077 | -0.1535 | -0.1535 | -0.1535 |
| Verdict | REJECT | REJECT (+ YES_IMPROVED) | REJECT_NON_DISCRIMINATIVE | REJECT_NON_DISCRIMINATIVE |

## 12. MANDATORY: C-sb-baseline reproduction check (per 27.0c-α §7.3)

- n_trades: observed=34626 baseline=34626 delta=+0 match=**True**
- Sharpe: observed=-0.173164 baseline=-0.173200 delta=+0.000036 (tolerance ±0.0001) match=**True**
- ann_pnl: observed=-204664.423 baseline=-204664.400 delta=-0.023 (tolerance ±0.5) match=**True**
- **all_match: True**

## 13. MANDATORY: Per-pair Sharpe contribution table (val-selected; D4 sort)

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

## 14. MANDATORY: Pair concentration per cell

| cell | q% | val_top_pair | val_top_share | val_conc_high | test_top_pair | test_top_share |
|---|---|---|---|---|---|---|
| C-sd | 5 | USD_JPY | 0.8877 | True | USD_JPY | 0.7760 |
| C-sb-baseline | 5 | USD_JPY | 0.8685 | True | USD_JPY | 0.7139 |

## 15. Classification-quality diagnostics (DIAGNOSTIC-ONLY)

| cell | AUC(P(TP)) | Cohen κ | logloss |
|---|---|---|---|
| C-sd | 0.5848 | 0.0000 | 0.6799 |
| C-sb-baseline | 0.5765 | 0.0986 | 1.0338 |

## 16. Feature importance (4-bucket; DIAGNOSTIC-ONLY)

- pair (gain): 2631.0 (0.300)
- direction (gain): 335.0 (0.038)
- atr_at_signal_pip (gain): 3295.0 (0.376)
- spread_at_signal_pip (gain): 2496.0 (0.285)

## 17. NEW: S-D distribution diagnostic (train/val/test; DIAGNOSTIC-ONLY)

| split | n_finite | p5 | p25 | p50 | p75 | p95 | mean |
|---|---|---|---|---|---|---|---|
| train | 2941032 | -3.5008 | -2.7105 | -2.0830 | -1.6508 | -1.3048 | -2.2139 |
| val | 517422 | -3.5606 | -3.0714 | -2.4126 | -1.8849 | -1.3872 | -2.4531 |
| test | 597666 | -3.5302 | -2.9615 | -2.2616 | -1.7588 | -1.3765 | -2.3487 |

## 18. NEW: Calibration reliability diagram per class (DIAGNOSTIC-ONLY)

### Class TP

| bin_lo | bin_hi | bin_count | mean_pred_raw | mean_pred_cal | freq_actual |
|---|---|---|---|---|---|
| 0.00 | 0.10 | 6071 | 0.1793 | 0.0897 | 0.0805 |
| 0.10 | 0.20 | 321857 | 0.2911 | 0.1547 | 0.1456 |
| 0.20 | 0.30 | 269738 | 0.3640 | 0.2223 | 0.2210 |
| 0.30 | 0.40 | 0 | - | - | - |
| 0.40 | 0.50 | 0 | - | - | - |
| 0.50 | 0.60 | 0 | - | - | - |
| 0.60 | 0.70 | 0 | - | - | - |
| 0.70 | 0.80 | 0 | - | - | - |
| 0.80 | 0.90 | 0 | - | - | - |
| 0.90 | 1.00 | 0 | - | - | - |

### Class SL

| bin_lo | bin_hi | bin_count | mean_pred_raw | mean_pred_cal | freq_actual |
|---|---|---|---|---|---|
| 0.00 | 0.10 | 0 | - | - | - |
| 0.10 | 0.20 | 0 | - | - | - |
| 0.20 | 0.30 | 0 | - | - | - |
| 0.30 | 0.40 | 0 | - | - | - |
| 0.40 | 0.50 | 6 | 0.1228 | 0.4784 | 0.3333 |
| 0.50 | 0.60 | 234 | 0.1515 | 0.5636 | 0.4957 |
| 0.60 | 0.70 | 123248 | 0.2461 | 0.6774 | 0.6457 |
| 0.70 | 0.80 | 331743 | 0.3583 | 0.7461 | 0.7564 |
| 0.80 | 0.90 | 142435 | 0.4857 | 0.8273 | 0.8497 |
| 0.90 | 1.00 | 0 | - | - | - |

### Class TIME

| bin_lo | bin_hi | bin_count | mean_pred_raw | mean_pred_cal | freq_actual |
|---|---|---|---|---|---|
| 0.00 | 0.10 | 509437 | 0.2867 | 0.0524 | 0.0530 |
| 0.10 | 0.20 | 86307 | 0.4533 | 0.1304 | 0.1325 |
| 0.20 | 0.30 | 1651 | 0.5660 | 0.2254 | 0.3065 |
| 0.30 | 0.40 | 243 | 0.6448 | 0.3232 | 0.4486 |
| 0.40 | 0.50 | 28 | 0.7223 | 0.4081 | 0.5357 |
| 0.50 | 0.60 | 0 | - | - | - |
| 0.60 | 0.70 | 0 | - | - | - |
| 0.70 | 0.80 | 0 | - | - | - |
| 0.80 | 0.90 | 0 | - | - | - |
| 0.90 | 1.00 | 0 | - | - | - |

## 19. NEW: Conditional-PnL estimator constants (DIAGNOSTIC-ONLY)

| class | full_train Ê[PnL\|c] | oof_aggregate | delta | rel_delta | flag |
|---|---|---|---|---|---|
| TP | +9.8197 | +9.8197 | +0.0000 | +0.0000 | False |
| SL | -5.6730 | -5.6730 | +0.0000 | +0.0000 | False |
| TIME | +1.5727 | +1.5728 | +0.0001 | +0.0000 | False |

Divergence threshold: |rel_delta| > 10% (suppressed when |full_train| < 1e-09). DIAGNOSTIC-ONLY; not in formal verdict.

## 20. Multiple-testing caveat
2 formal cells × 5 quantile = 10 (cell, q) pairs. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE are hypothesis-generating only.

## 21. Verdict statement: **REJECT_NON_DISCRIMINATIVE** (C-sb-baseline match: True)
