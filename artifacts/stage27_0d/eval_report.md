# Stage 27.0d-β — S-E Regression-on-Realised-PnL Eval Report

Generated: 2026-05-15T14:51:39.583795+00:00

Design contract: `docs/design/phase27_0d_alpha_s_e_regression_on_realised_pnl_design_memo.md` (PR #324) under Phase 27 S-E scope amendment (PR #323), Phase 27 kickoff (PR #316), post-27.0c routing review (PR #322), and inherited Phase 26 framework (PR #311 / PR #313).

## 1. Mandatory clauses (clauses 1-5 verbatim; clause 6 = PR #323 §7 verbatim)

**1. Phase framing.** ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.

**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison / classification-quality / feature-importance / per-pair-Sharpe-contribution columns are diagnostic-only. 27.0c extension preserved: conditional-PnL estimator constants and calibration reliability diagrams are diagnostic-only. 27.0d extends: regressor feature importance, predicted-vs-realised correlation, R², MAE, and predicted-PnL distribution are diagnostic-only.

**3. γ closure preservation.** PR #279 is unmodified.

**4. Production-readiness preservation.** X-v2 OOS gating remains required. v9 20-pair (Phase 9.12) untouched. Phase 22 frozen-OOS contract preserved.

**5. NG#10 / NG#11 not relaxed.**

**6. Phase 27 scope.** R7-A admissible at kickoff; R7-B/C require separate scope amendments; R7-D/Other NOT admissible. S-A/S-B/S-C formal at kickoff. S-D promoted to formal at 27.0c-β via PR #320. S-E promoted from 'requires scope amendment' to 'admissible at 27.0d-α design memo' via PR #323; on PR #324 merge S-E became formal at 27.0d-β. S-Other NOT admissible. Phase 26 deferred items NOT subsumed.

## 2. D-1 binding (formal realised-PnL = inherited harness)

Formal realised-PnL uses inherited `_compute_realised_barrier_pnl` (bid/ask executable). Mid-to-mid PnL appears in sanity probe only. The S-E regression target uses the SAME bid/ask executable harness on a per-row basis.

## 3. R7-A feature set (FIXED per Phase 27.0d-α §2)

- ADMITTED: ['pair', 'direction', 'atr_at_signal_pip', 'spread_at_signal_pip']
- NO new feature additions in 27.0d.

## 4. S-E + S-B-baseline cell definitions (per 27.0d-α §7.1)

- C-se: S-E(row) = regressor.predict(row); LightGBM Huber regression
- C-sb-baseline: S-B = raw P(TP) - P(SL); separately-fit multiclass head
- 5-fold OOF protocol (seed=42); DIAGNOSTIC-ONLY (not in formal scoring)
- C-sb-baseline must reproduce 27.0b C-alpha0 (n_trades=34,626 / Sharpe=-0.1732 / ann_pnl=-204,664.4) or HALT with BaselineMismatchError

## 5. Sanity probe (per 27.0d-α §10)

- status: **PASS**
  - TP: 565106 (19.215%)
  - SL: 2184896 (74.290%)
  - TIME: 191030 (6.495%)
- target PnL train: n=2941032 mean=-2.2255 std=7.5221 p5=-11.0025 p50=-3.7475 p95=+11.9962
- NaN-PnL train rows dropped: 0 (HALT > 0.1% of n_train per D-J12)

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
| C-se | S-E(regressor_pred) | 40 | -3.6496 | -0.5732 | -1127169.4 | 206985 | -0.4831 | -999830.4 | 184703 | 0.4381 | OK |
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

**Note**: 27.0d-β cannot mint ADOPT_CANDIDATE. H2 PASS → PROMISING_BUT_NEEDS_OOS.

## 10. Cross-cell verdict aggregation (per 26.0c-α §7.2)
- per-cell branches: ['REJECT_BUT_INFORMATIVE_FLAT', 'REJECT_NON_DISCRIMINATIVE']
- cells agree: **False**
- aggregate verdict: **SPLIT_VERDICT_ROUTE_TO_REVIEW**
- C-se (S-E(regressor_pred)): REJECT_BUT_INFORMATIVE_FLAT (H1m_PASS_H2_FAIL_H3_FAIL)
- C-sb-baseline (S-B(raw_p_tp_minus_p_sl)): REJECT_NON_DISCRIMINATIVE (H1_WEAK_FAIL)

## 11. MANDATORY: Baseline comparison (per 27.0d-α §11.11)

| Aspect | 26.0d R6-new-A C02 (#313) | 27.0b C-alpha0 / S-B (#318) | 27.0c C-sd / S-D (#321) | 27.0d val-selected |
|---|---|---|---|---|
| Feature set | R7-A | R7-A | R7-A | R7-A |
| Score objective | S-B | S-B (≡ α=0.0) | S-D calibrated EV | S-E or S-B per val-sel |
| Cell signature | C02 P(TP)-P(SL) | C-alpha0 (α=0.0) | C-sd | id=C-sb-baseline picker=S-B(raw_p_tp_minus_p_sl) score_type=s_b_raw |
| Test n_trades | 34,626 | 34,626 | 32,324 | 34626 |
| Test Sharpe | -0.1732 | -0.1732 | -0.1760 | -0.1732 |
| Test ann_pnl | -204,664.4 | -204,664.4 | (per #321) | -204664.4 |
| Test Spearman | -0.1535 | -0.1535 | -0.1060 | -0.1535 |
| Verdict | REJECT (+ YES_IMPROVED) | REJECT_NON_DISCRIMINATIVE | REJECT_NON_DISCRIMINATIVE | REJECT_NON_DISCRIMINATIVE |

## 12. MANDATORY: C-sb-baseline reproduction check (per 27.0d-α §7.3)

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
| C-se | 40 | AUD_USD | 0.1513 | False | NZD_USD | 0.1446 |
| C-sb-baseline | 5 | USD_JPY | 0.8685 | True | USD_JPY | 0.7139 |

## 15. Classification-quality diagnostics on multiclass head (DIAGNOSTIC-ONLY)

| cell | AUC(P(TP)) | Cohen κ | logloss |
|---|---|---|---|
| C-se | 0.5765 | 0.0986 | 1.0338 |
| C-sb-baseline | 0.5765 | 0.0986 | 1.0338 |

## 16. Regressor feature importance (4-bucket; DIAGNOSTIC-ONLY)

- pair (gain): 259.0 (0.087)
- direction (gain): 34.0 (0.011)
- atr_at_signal_pip (gain): 1978.0 (0.666)
- spread_at_signal_pip (gain): 697.0 (0.235)

## 17. NEW: Predicted-PnL distribution train/val/test (DIAGNOSTIC-ONLY)

| split | n_finite | p5 | p25 | p50 | p75 | p95 | mean |
|---|---|---|---|---|---|---|---|
| train | 2941032 | -5.0005 | -4.4553 | -4.0504 | -3.1749 | -2.1304 | -3.8037 |
| val | 517422 | -5.0907 | -4.6187 | -4.0416 | -2.9182 | -2.0142 | -3.7747 |
| test | 597666 | -5.0792 | -4.6574 | -4.1580 | -3.3658 | -2.1765 | -3.9399 |

## 18. NEW: Predicted-vs-realised correlation diagnostic (DIAGNOSTIC-ONLY)

| split / source | n | Pearson | Spearman |
|---|---|---|---|
| OOF aggregate | n/a | +0.0748 | +0.3836 |
| train (refit) | 2941032 | +0.0751 | +0.3841 |
| val | 517422 | +0.1363 | +0.5040 |
| test | 597666 | +0.1142 | +0.4381 |
- OOF positive-Pearson folds: 5/5

## 19. NEW: Regressor MAE + R² on train/val/test (DIAGNOSTIC-ONLY)

| split | n | MAE | R² |
|---|---|---|---|
| train | 2941032 | 4.4347 | -0.0401 |
| val | 517422 | 3.1773 | -0.0454 |
| test | 597666 | 3.9325 | -0.0366 |

## 20. Multiple-testing caveat
2 formal cells × 5 quantile = 10 (cell, q) pairs. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE are hypothesis-generating only.

## 21. Verdict statement: **REJECT_NON_DISCRIMINATIVE** (C-sb-baseline match: True)
