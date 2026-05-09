# Stage 25.0d-β — Deployment-Layer Audit Eval

Generated: 2026-05-09T07:01:34.256305+00:00

Design contract: `docs/design/phase25_0d_deployment_audit_design.md` (PR #289)

## Mandatory clauses

**1. Phase 25 framing.** Phase 25 is not a hyperparameter-tuning phase. It is a label-and-feature-class redesign phase.

**2. Diagnostic-leakage prohibition.** The 25.0a-β diagnostic columns MUST NOT appear in any model's feature matrix.

**3. Causality and split discipline.** All features use shift(1).rolling pattern. Train/val/test splits are strictly chronological (70/15/15). Threshold selection uses VALIDATION ONLY; test set is touched once.

**4. γ closure preservation.** Phase 25.0d does not modify the γ closure (PR #279).

**5. Production-readiness preservation.** Findings in 25.0d are hypothesis-generating only. Production-readiness requires X-v2-equivalent frozen-OOS PR per Phase 22 contract.

**6. Deployment-layer scope clause.** This PR investigates the structural AUC-PnL gap surfaced in PR #288 §4.2 by analysing F1+F2 best cells under varied deployment-layer settings. Tests H-A/H-B/H-D/H-F from #288 §5. Does NOT redesign features, labels, or model class. Verdict applies only to F1+F2 best cells; convergence with F3-F6 is a separate question. F1 and F2 verdicts (#284, #287) are NOT modified by this audit.

**7. Production misunderstanding guard.** This is a research deployment-layer audit, not a production deployment study.

**8. Threshold sweep guard.** The extended threshold sweep is diagnostic-only. It must not be interpreted as selecting a production threshold from the test set.

**9. Directional comparison guard.** Directional comparison is diagnostic-only. If directional candidate generation appears promising, it requires a separate predeclared design PR and frozen-OOS validation.


## Test-touched-once invariant

**threshold selected on validation only; test set touched once.**

## Cell: F1 rank-1 (M5, q=0.20, e=1.25, lb=50)

- n_train: 386, n_val: 54, n_test: 96
- test AUC: 0.5644
- mean ATR (pip): 5.4505
- mean spread (pip): 2.2938

> **F1 decile calibration is low-power due to small n_test. Interpret F1 bucket diagnostics as qualitative only.**

### H-A Calibration (decile reliability)

- Verdict: **MISCALIBRATED** (max abs deviation 0.9152; systematic over/under-estimation > 0.10)
- Quintile monotonic: False

| bucket | n | mean_predicted | actual_pos_rate | brier | LOW_BUCKET_N |
|---|---|---|---|---|---|
| 0 | 3 | 0.0817 | 0.0000 | 0.0068 | YES |
| 1 | 19 | 0.1573 | 0.1579 | 0.1399 | YES |
| 2 | 16 | 0.2566 | 0.0625 | 0.0957 | YES |
| 3 | 12 | 0.3522 | 0.3333 | 0.2238 | YES |
| 4 | 14 | 0.4412 | 0.1429 | 0.2081 | YES |
| 5 | 12 | 0.5593 | 0.1667 | 0.2951 | YES |
| 6 | 6 | 0.6484 | 0.5000 | 0.2805 | YES |
| 7 | 7 | 0.7314 | 0.1429 | 0.4661 | YES |
| 8 | 5 | 0.8398 | 0.2000 | 0.5766 | YES |
| 9 | 2 | 0.9152 | 0.0000 | 0.8377 | YES |

**Quintile (5 buckets) supplementary:**

| bucket | n | mean_predicted | actual_pos_rate | LOW_BUCKET_N |
|---|---|---|---|---|
| 0 | 22 | 0.1470 | 0.1364 | YES |
| 1 | 28 | 0.2976 | 0.1786 | YES |
| 2 | 26 | 0.4957 | 0.1538 | YES |
| 3 | 13 | 0.6931 | 0.3077 | YES |
| 4 | 7 | 0.8614 | 0.1429 | YES |

### H-F empirical: per-bucket realised PnL

- Verdict: **CONFIRMED**

| bucket | n | mean_realised_pip | mean_spread_pip | net_EV_pip | LOW_BUCKET_N |
|---|---|---|---|---|---|
| 0 | 3 | -2.6708 | 2.3333 | -5.0042 | YES |
| 1 | 19 | -2.9412 | 2.7105 | -5.6518 | YES |
| 2 | 16 | -5.0343 | 2.4000 | -7.4343 | YES |
| 3 | 12 | +0.7958 | 2.0750 | -1.2792 | YES |
| 4 | 14 | -3.3655 | 2.0786 | -5.4441 | YES |
| 5 | 12 | -2.6801 | 2.1167 | -4.7968 | YES |
| 6 | 6 | +0.8796 | 2.0000 | -1.1204 | YES |
| 7 | 7 | -0.8487 | 2.2857 | -3.1345 | YES |
| 8 | 5 | -3.7933 | 2.2200 | -6.0133 | YES |
| 9 | 2 | -5.8425 | 2.4000 | -8.2425 | YES |

### H-B extended threshold sweep

- Verdict: **REFUTED**

> *Extended threshold sweep is diagnostic-only. It must not be interpreted as selecting a production threshold from the test set.*

| threshold | status | n_trades | sharpe | annual_pnl |
|---|---|---|---|---|
| 0.2 | OK | 41 | -0.3296 | -286.2 |
| 0.3 | OK | 34 | -0.1847 | -134.7 |
| 0.4 | OK | 26 | -0.1920 | -107.6 |
| 0.5 | OK | 21 | -0.3019 | -126.3 |
| 0.6 | OK | 13 | -0.3512 | -89.3 |
| 0.7 | OK | 9 | -0.6426 | -96.9 |
| 0.8 | OK | 5 | -0.7237 | -63.3 |

### H-D bidirectional vs directional

- Verdict: **REFUTED**
- Bidirectional baseline (val-selected threshold 0.4): n_trades=26, Sharpe=-0.1920, ann_pnl=-107.6
- Directional (long_thr=0.2, short_thr=0.4): n_trades=22, n_skipped_both=17, Sharpe=-0.1862, ann_pnl=-89.9, status=OK
- ⚠ DIRECTIONAL_LOW_DATA flag (per-direction n_train < 1000)

> *Directional comparison is diagnostic-only. If directional candidate generation appears promising, it requires a separate predeclared design PR and frozen-OOS validation.*

> *Absolute profitability caveat: a 50% improvement from deeply-negative ann_pnl is NOT monetisation; check absolute level.*

### H-F theoretical: AUC-EV bound (closed-form binormal; diagnostic-only)

- Verdict (theoretical): **CONFIRMED**
- AUC: 0.5644; base rate: 0.187; K_FAV=1.5; K_ADV=1.0; mean_atr_pip=5.4505; mean_spread_pip=2.2938

| quantile | P(pos | predicted ≥ q) | expected_pnl_pip | net_EV_pip |
|---|---|---|---|
| 0.5 | 0.2147 | -2.5251 | -4.8189 |
| 0.6 | 0.2211 | -2.4374 | -4.7311 |
| 0.7 | 0.2287 | -2.3336 | -4.6274 |
| 0.8 | 0.2385 | -2.2002 | -4.4939 |
| 0.9 | 0.2536 | -1.9955 | -4.2892 |

> *Theoretical bound is diagnostic-only. Empirical realised barrier PnL takes priority.*

---

## Cell: F2 rank-1 (tw=200, rep=per_tf_only, adm=none)

- n_train: 2889806, n_val: 502486, n_test: 591004
- test AUC: 0.5613
- mean ATR (pip): 5.7461
- mean spread (pip): 2.4432

### H-A Calibration (decile reliability)

- Verdict: **MISCALIBRATED** (max abs deviation 0.3725; systematic over/under-estimation > 0.10)
- Quintile monotonic: True

| bucket | n | mean_predicted | actual_pos_rate | brier | LOW_BUCKET_N |
|---|---|---|---|---|---|
| 0 | 0 | n/a | n/a | n/a | YES |
| 1 | 0 | n/a | n/a | n/a | YES |
| 2 | 1001 | 0.2814 | 0.0919 | 0.1195 | no |
| 3 | 29233 | 0.3638 | 0.1163 | 0.1642 | no |
| 4 | 268875 | 0.4614 | 0.1588 | 0.2250 | no |
| 5 | 267490 | 0.5368 | 0.2003 | 0.2733 | no |
| 6 | 24405 | 0.6240 | 0.2514 | 0.3267 | no |
| 7 | 0 | n/a | n/a | n/a | YES |
| 8 | 0 | n/a | n/a | n/a | YES |
| 9 | 0 | n/a | n/a | n/a | YES |

**Quintile (5 buckets) supplementary:**

| bucket | n | mean_predicted | actual_pos_rate | LOW_BUCKET_N |
|---|---|---|---|---|
| 0 | 0 | n/a | n/a | YES |
| 1 | 30234 | 0.3611 | 0.1155 | no |
| 2 | 536365 | 0.4990 | 0.1795 | no |
| 3 | 24405 | 0.6240 | 0.2514 | no |
| 4 | 0 | n/a | n/a | YES |

### H-F empirical: per-bucket realised PnL

- Verdict: **CONFIRMED**

| bucket | n | mean_realised_pip | mean_spread_pip | net_EV_pip | LOW_BUCKET_N |
|---|---|---|---|---|---|
| 0 | 0 | n/a | n/a | n/a | YES |
| 1 | 0 | n/a | n/a | n/a | YES |
| 2 | 1001 | -2.7094 | 2.5440 | -5.2533 | no |
| 3 | 29233 | -2.5374 | 2.4690 | -5.0064 | no |
| 4 | 268875 | -2.4219 | 2.3851 | -4.8070 | no |
| 5 | 267490 | -2.6020 | 2.5445 | -5.1465 | no |
| 6 | 24405 | -1.9524 | 1.9378 | -3.8902 | no |
| 7 | 0 | n/a | n/a | n/a | YES |
| 8 | 0 | n/a | n/a | n/a | YES |
| 9 | 0 | n/a | n/a | n/a | YES |

### H-B extended threshold sweep

- Verdict: **REFUTED**

> *Extended threshold sweep is diagnostic-only. It must not be interpreted as selecting a production threshold from the test set.*

| threshold | status | n_trades | sharpe | annual_pnl |
|---|---|---|---|---|
| 0.2 | OK | 295502 | -0.3764 | -2434223.6 |
| 0.3 | OK | 295015 | -0.3761 | -2429895.3 |
| 0.4 | OK | 280763 | -0.3696 | -2309569.5 |
| 0.5 | OK | 149618 | -0.3223 | -1263632.8 |
| 0.6 | OK | 12291 | -0.2155 | -82440.3 |
| 0.7 | EMPTY | 0 | n/a | n/a |
| 0.8 | EMPTY | 0 | n/a | n/a |

### H-D bidirectional vs directional

- Verdict: **PARTIAL_LIFT_BUT_STILL_NEG**
- Bidirectional baseline (val-selected threshold 0.4): n_trades=280763, Sharpe=-0.3696, ann_pnl=-2309569.5
- Directional (long_thr=0.6, short_thr=0.6): n_trades=394, n_skipped_both=11897, Sharpe=-0.2985, ann_pnl=-3163.1, status=OK

> *Directional comparison is diagnostic-only. If directional candidate generation appears promising, it requires a separate predeclared design PR and frozen-OOS validation.*

> *Absolute profitability caveat: a 50% improvement from deeply-negative ann_pnl is NOT monetisation; check absolute level.*

### H-F theoretical: AUC-EV bound (closed-form binormal; diagnostic-only)

- Verdict (theoretical): **CONFIRMED**
- AUC: 0.5613; base rate: 0.187; K_FAV=1.5; K_ADV=1.0; mean_atr_pip=5.7461; mean_spread_pip=2.4432

| quantile | P(pos | predicted ≥ q) | expected_pnl_pip | net_EV_pip |
|---|---|---|---|
| 0.5 | 0.2133 | -2.6814 | -5.1246 |
| 0.6 | 0.2194 | -2.5938 | -5.0370 |
| 0.7 | 0.2266 | -2.4904 | -4.9336 |
| 0.8 | 0.2359 | -2.3575 | -4.8007 |
| 0.9 | 0.2501 | -2.1540 | -4.5972 |

> *Theoretical bound is diagnostic-only. Empirical realised barrier PnL takes priority.*

---

## Cross-cell convergence summary

| Hypothesis | F1 verdict | F2 verdict | Convergent? |
|---|---|---|---|
| H-A calibration | MISCALIBRATED | MISCALIBRATED | YES |
| H-B threshold range | REFUTED | REFUTED | YES |
| H-D bidirectional argmax | REFUTED | PARTIAL_LIFT_BUT_STILL_NEG | no |
| H-F empirical | CONFIRMED | CONFIRMED | YES |
| H-F theoretical | CONFIRMED | CONFIRMED | YES |

**Evidence weight reminder**: F1 bucket diagnostics are low-power (n_test=96; ~10/decile); F2 bucket diagnostics are high-sample (n_test ~600k; ~60k/decile). F2 is the primary evidence base for calibration and threshold-EV structure; F1 is qualitative only.

## Routing options post-25.0d-β (no auto-routing; user picks)

Per 25.0d-α §9 verdict criteria:
- Calibration mismatch + extended threshold rescues → H-A: calibration-before-threshold PR
- Calibration OK + extended threshold rescues → H-B: expand threshold range design PR
- Calibration OK + threshold doesn't rescue + directional rescues → H-D: directional pipeline design PR (separate predeclared design + frozen-OOS)
- All deployment-layer hypotheses refuted → empirical structural gap; pivot to F3-F6 / label redesign

## Multiple-testing caveat

These are 2 evaluated cells × 4 hypotheses (H-A, H-B, H-D, H-F). Findings are research-level; production-readiness still requires X-v2-equivalent frozen-OOS PR.
