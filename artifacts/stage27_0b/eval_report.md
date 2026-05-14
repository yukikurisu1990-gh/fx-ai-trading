# Stage 27.0b-β — S-C TIME Penalty Eval Report

Generated: 2026-05-14T23:25:21.461021+00:00

Design contract: `docs/design/phase27_0b_alpha_s_c_time_penalty_design_memo.md` (PR #317) under Phase 27 kickoff (PR #316) and inherited Phase 26 framework (PR #311 / PR #313).

## 1. Mandatory clauses (clauses 1-5 verbatim; clause 6 = Phase 27 kickoff §8)

**1. Phase framing.** ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.

**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison / classification-quality / feature-importance / per-pair-Sharpe-contribution / α-monotonicity columns are diagnostic-only.

**3. γ closure preservation.** PR #279 is unmodified.

**4. Production-readiness preservation.** X-v2 OOS gating remains required. v9 20-pair (Phase 9.12) untouched. Phase 22 frozen-OOS contract preserved.

**5. NG#10 / NG#11 not relaxed.**

**6. Phase 27 scope.** R7-A admissible at kickoff; R7-B/C require separate scope amendments; R7-D NOT admissible. S-A/S-B/S-C formal at kickoff; S-D deferred; S-E requires separate amendment; S-Other NOT admissible. Phase 26 deferred items NOT subsumed.

## 2. D-1 binding (formal realised-PnL = inherited harness)

Formal realised-PnL uses inherited `_compute_realised_barrier_pnl` (bid/ask executable). Mid-to-mid PnL appears in sanity probe only.

## 3. R7-A feature set (FIXED per Phase 27.0b-α §2)

- ADMITTED: ['pair', 'direction', 'atr_at_signal_pip', 'spread_at_signal_pip']
- NO new feature additions in 27.0b.

## 4. S-C score-objective + α grid (per 27.0b-α §3 / §4)

- S-C(row, α) = P(TP)[row] - P(SL)[row] - α · P(TIME)[row]
- closed α grid: [0.0, 0.3, 0.5, 1.0]
- α=0.0 ≡ S-B (Phase 26 C02 picker)
- α=1.0 ≡ 2·P(TP) - 1 (monotone transform of P(TP))

## 5. Sanity probe (per 27.0b-α §11)

- status: **PASS**
  - TP: 565106 (19.215%)
  - SL: 2184896 (74.290%)
  - TIME: 191030 (6.495%)
- P(TIME) distribution (NEW; report-only per D-T5):
  - val: mean=0.2812 p5=0.1697 p50=0.2739 p95=0.4154
  - test: mean=0.3117 p5=0.1903 p50=0.3027 p95=0.4669

## 6. Pre-flight diagnostics
- label rows (pre-drop): 4056120
- pairs: 20
- LightGBM: True
- formal cells run: 4

## 7. Row-drop policy (R7-A inherited)
- train: n_input=2941032 n_kept=2941032 n_dropped=0
- val: n_input=517422 n_kept=517422 n_dropped=0
- test: n_input=597666 n_kept=597666 n_dropped=0

## 8. Split dates
- min: 2024-04-30 14:10:00+00:00
- train < 2025-09-23 12:11:00+00:00
- val [2025-09-23 12:11:00+00:00, 2026-01-10 23:45:30+00:00)
- test [2026-01-10 23:45:30+00:00, 2026-04-30 11:20:00+00:00]

## 9. All formal cells — primary quantile-family summary

| cell | α | q% | cutoff | val_sharpe | val_ann_pnl | val_n | test_sharpe | test_ann_pnl | test_n | test_spearman | h_state |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C-alpha0 | 0.0 | 5 | +0.1262 | -0.1863 | -142234.1 | 25881 | -0.1732 | -204664.4 | 34626 | -0.1535 | OK |
| C-alpha03 | 0.3 | 5 | +0.0274 | -0.2116 | -134972.6 | 25886 | -0.2035 | -148413.0 | 27233 | -0.1127 | OK |
| C-alpha05 | 0.5 | 5 | -0.0304 | -0.2234 | -134299.0 | 25872 | -0.2204 | -144626.1 | 26581 | -0.0786 | OK |
| C-alpha10 | 1.0 | 5 | -0.1691 | -0.2446 | -132789.0 | 25890 | -0.2511 | -138766.2 | 25357 | 0.0226 | OK |

## 10. Val-selected (cell\*, α\*, q\*) — FORMAL verdict source

- cell: id=C-alpha0 alpha=0.0 picker=S-C(α=0.0)
- selected q%: 5
- selected cutoff: +0.126233
- val: n_trades=25881, Sharpe=-0.1863, ann_pnl=-142234.1
- test: n_trades=34626, Sharpe=-0.1732, ann_pnl=-204664.4
- FORMAL Spearman(score, realised_pnl) on test: -0.1535

## 11. Aggregate H1 / H2 / H3 / H4 outcome

- H1-weak (> 0.05): **False**
- H1-meaningful (≥ 0.1): **False**
- H2: **False**
- H3 (> -0.192): **True**
- H4 (≥ 0): **False**

### Verdict: **REJECT_NON_DISCRIMINATIVE** (H1_WEAK_FAIL)

**Note**: 27.0b-β cannot mint ADOPT_CANDIDATE. H2 PASS → PROMISING_BUT_NEEDS_OOS.

## 12. Cross-cell verdict aggregation (per 26.0c-α §7.2)
- per-cell branches: ['REJECT_NON_DISCRIMINATIVE']
- cells agree: **True**
- aggregate verdict: **REJECT_NON_DISCRIMINATIVE**
- C-alpha0 (S-C(α=0.0)): REJECT_NON_DISCRIMINATIVE (H1_WEAK_FAIL)
- C-alpha03 (S-C(α=0.3)): REJECT_NON_DISCRIMINATIVE (H1_WEAK_FAIL)
- C-alpha05 (S-C(α=0.5)): REJECT_NON_DISCRIMINATIVE (H1_WEAK_FAIL)
- C-alpha10 (S-C(α=1.0)): REJECT_NON_DISCRIMINATIVE (H1_WEAK_FAIL)

## 13. MANDATORY: Baseline comparison (per 27.0b-α §12.1)

| Aspect | Phase 26 L-1 C02 (#309) | Phase 26 R6-new-A C02 (#313) | Phase 27 27.0b val-selected |
|---|---|---|---|
| Feature set | pair + direction | + atr + spread (R7-A) | + atr + spread (R7-A fixed) |
| Score objective | S-B | S-B | S-C(α\*) per val-selection |
| Cell signature | C02 P(TP)-P(SL) | C02 P(TP)-P(SL) | id=C-alpha0 alpha=0.0 picker=S-C(α=0.0) |
| Test n_trades | 42,150 | 34,626 | 34626 |
| Test Sharpe | -0.2232 | -0.1732 | -0.1732 |
| Test ann_pnl | -237,310.8 | -204,664.4 | -204664.4 |
| Test Spearman | -0.1077 | -0.1535 | -0.1535 |
| Verdict | REJECT | REJECT (+ YES_IMPROVED) | REJECT_NON_DISCRIMINATIVE |

## 14. MANDATORY: α=0.0 sanity-check declaration (per 27.0b-α §12.2)

- n_trades: observed=34626 baseline=34626 delta=+0 match=**True**
- Sharpe: observed=-0.173164 baseline=-0.173200 delta=+0.000036 (tolerance ±0.0001) match=**True**
- ann_pnl: observed=-204664.423 baseline=-204664.400 delta=-0.023 (tolerance ±0.5) match=**True**
- **all_match: True**

## 15. MANDATORY: α-monotonicity diagnostic (per 27.0b-α §12.3)

DIAGNOSTIC-ONLY; strict monotonic or mixed (per D-T6 + D5 binding).

| α | val_sharpe | val_ann_pnl | test_sharpe | test_ann_pnl | test_spearman |
|---|---|---|---|---|---|
| 0.0 | -0.1863 | -142234.1 | -0.1732 | -204664.4 | -0.1535 |
| 0.3 | -0.2116 | -134972.6 | -0.2035 | -148413.0 | -0.1127 |
| 0.5 | -0.2234 | -134299.0 | -0.2204 | -144626.1 | -0.0786 |
| 1.0 | -0.2446 | -132789.0 | -0.2511 | -138766.2 | 0.0226 |

- monotonic val Sharpe: **decreasing**
- monotonic test Sharpe: **decreasing**
- monotonic test ann_pnl: **increasing**
- monotonic test Spearman: **increasing**

## 16. MANDATORY: Per-pair Sharpe contribution table (per 27.0b-α §12.4)

DIAGNOSTIC-ONLY; sorted by share_of_total_pnl descending (per D4).
Computed on val-selected (cell\*, α\*, q\*) on test.

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

## 17. Pair concentration per cell (DIAGNOSTIC-ONLY)

| cell | α | q% | val_top_pair | val_top_share | val_conc_high | test_top_pair | test_top_share |
|---|---|---|---|---|---|---|---|
| C-alpha0 | 0.0 | 5 | USD_JPY | 0.8685 | True | USD_JPY | 0.7139 |
| C-alpha03 | 0.3 | 5 | USD_JPY | 1.0000 | True | USD_JPY | 0.9998 |
| C-alpha05 | 0.5 | 5 | USD_JPY | 1.0000 | True | USD_JPY | 1.0000 |
| C-alpha10 | 1.0 | 5 | USD_JPY | 1.0000 | True | USD_JPY | 1.0000 |

## 18. Classification-quality diagnostics (DIAGNOSTIC-ONLY)

| cell | α | AUC(P(TP)) | Cohen κ | logloss |
|---|---|---|---|---|
| C-alpha0 | 0.0 | 0.5765 | 0.0986 | 1.0338 |
| C-alpha03 | 0.3 | 0.5765 | 0.0986 | 1.0338 |
| C-alpha05 | 0.5 | 0.5765 | 0.0986 | 1.0338 |
| C-alpha10 | 1.0 | 0.5765 | 0.0986 | 1.0338 |

## 19. Feature importance (4-bucket; DIAGNOSTIC-ONLY)

- pair (gain): 2631.0 (0.300)
- direction (gain): 335.0 (0.038)
- atr_at_signal_pip (gain): 3295.0 (0.376)
- spread_at_signal_pip (gain): 2496.0 (0.285)

## 20. Absolute-threshold sweep per α (DIAGNOSTIC-ONLY)

| cell | α | abs_thr | val_sharpe | val_n | test_sharpe | test_n |
|---|---|---|---|---|---|---|
| C-alpha0 | 0.0 | +0.0000 | -0.2915 | 172928 | -0.2683 | 253894 |
| C-alpha0 | 0.0 | +0.0500 | -0.2542 | 105453 | -0.2348 | 168182 |
| C-alpha0 | 0.0 | +0.1000 | -0.2123 | 48161 | -0.1952 | 81831 |
| C-alpha0 | 0.0 | +0.1500 | -0.1774 | 16239 | -0.1663 | 18260 |
| C-alpha03 | 0.3 | -0.1000 | -0.2979 | 186284 | -0.2703 | 258648 |
| C-alpha03 | 0.3 | -0.0500 | -0.2587 | 108612 | -0.2341 | 161440 |
| C-alpha03 | 0.3 | +0.0000 | -0.2147 | 37722 | -0.2054 | 42293 |
| C-alpha03 | 0.3 | +0.0500 | -0.2127 | 18652 | -0.1992 | 19449 |
| C-alpha03 | 0.3 | +0.1000 | -0.4225 | 4 | -0.6861 | 6 |
| C-alpha05 | 0.5 | -0.1500 | -0.2911 | 168915 | -0.2643 | 231801 |
| C-alpha05 | 0.5 | -0.1000 | -0.2501 | 80890 | -0.2342 | 104028 |
| C-alpha05 | 0.5 | -0.0500 | -0.2228 | 30341 | -0.2168 | 31516 |
| C-alpha05 | 0.5 | +0.0000 | -0.2241 | 14253 | -0.2004 | 13907 |
| C-alpha05 | 0.5 | +0.0500 | nan | 0 | nan | 0 |
| C-alpha10 | 1.0 | -0.4000 | -0.3671 | 367941 | -0.3303 | 417641 |
| C-alpha10 | 1.0 | -0.2000 | -0.2505 | 31760 | -0.2497 | 31031 |
| C-alpha10 | 1.0 | -0.1000 | nan | 0 | nan | 0 |
| C-alpha10 | 1.0 | +0.0000 | nan | 0 | nan | 0 |

## 21. Isotonic-calibration appendix — OMITTED per 26.0c-α §4.3

## 22. Multiple-testing caveat
4 formal cells × 5 quantile = 20 (cell, q) pairs. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE are hypothesis-generating only.

## 23. Verdict statement: **REJECT_NON_DISCRIMINATIVE** (α-monotonicity test Sharpe: decreasing; α=0.0 baseline match: True)
