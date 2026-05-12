# Stage 26.0c-β — L-1 Ternary Classification Eval

Generated: 2026-05-12T22:26:53.201347+00:00

Design contract: `docs/design/phase26_0c_alpha_l1_design_memo.md` (PR #308).

L-1 = ternary classification {TP=0, SL=1, TIME=2}. Multiclass LightGBM with class_weight=balanced on the minimum feature set (pair + direction). Two formal cells: picker = P(TP) and P(TP)-P(SL); raw probabilities only (isotonic deferred per §4.3). Quantile-of-val {5,10,20,30,40}% is the PRIMARY (formal) verdict basis. Absolute probability thresholds and classification diagnostics (AUC / κ / logloss / confusion matrix / per-class accuracy) are DIAGNOSTIC-ONLY. Formal H1 = Spearman(picker score, realised PnL via inherited M1 path harness).

## Mandatory clauses (verbatim per 26.0c-α §12)

**1. Phase 26 framing.** Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.

**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison / classification-quality columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.

**3. γ closure preservation.** PR #279 is unmodified.

**4. Production-readiness preservation.** X-v2 OOS gating remains required before any production deployment. v9 20-pair (Phase 9.12) remains untouched.

**5. NG#10 / NG#11 not relaxed.**

**6. Phase 26 scope.** Phase 26 is NOT a continuation of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed. R6-new requires explicit scope amendment.

## D-1 binding (formal realised-PnL = inherited harness)

L-1 LABEL ASSIGNMENT uses TP / SL / TIME classes, but FORMAL realised-PnL scoring uses inherited `_compute_realised_barrier_pnl` (bid/ask executable; same harness as L-2 / L-3). mid-to-mid PnL appears in the sanity probe / label diagnostic ONLY and is NEVER the formal realised-PnL metric.

## Production-misuse guards

**GUARD 1**: research-not-production.

**GUARD 2**: threshold-sweep-diagnostic.

**GUARD 3**: directional-comparison-diagnostic.

## Sanity probe results (per 26.0c-α §10)

- status: **PASS**
- class priors (train):
  - TP: 565106 (19.215%)
  - SL: 2184896 (74.290%)
  - TIME: 191030 (6.495%)
- per-pair TIME-share > 99% pairs: []
- realised-PnL cache basis: inherited_compute_realised_barrier_pnl_bid_ask_executable

## Pre-flight diagnostics

- label rows: 4056120
- horizon_bars (M1): 60
- pairs: 20
- LightGBM available: True
- LightGBM version: 4.6.0
- formal cells run: 2

## Validation-only cell + quantile selection (per 26.0c-α §7.1)

Pre-filter: candidates with `val_n_trades >= A0-equivalent`. If none, LOW_VAL_TRADES flag is set; fallback to all valid.

Tie-breakers (deterministic):
1. max val realised Sharpe (primary)
2. max val annual_pnl
3. lower val MaxDD
4. smaller q% (more selective; final deterministic tie-breaker)

- A0-equivalent val trade threshold: 21.0
- LOW_VAL_TRADES flag: False

## Split dates

- min: 2024-04-30 14:10:00+00:00
- train < 2025-09-23 12:11:00+00:00
- val [2025-09-23 12:11:00+00:00, 2026-01-10 23:45:30+00:00)
- test [2026-01-10 23:45:30+00:00, 2026-04-30 11:20:00+00:00]

## All formal cells — primary quantile-family summary

| cell | picker | q% | cutoff | val_sharpe | val_ann_pnl | val_n | test_sharpe | test_ann_pnl | test_n | test_spearman | A4 | A5_ann | h_state |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C01 | P(TP) | 5 | +0.3986 | -0.2398 | -217825.1 | 41272 | -0.2232 | -237310.8 | 42150 | -0.0505 | 0 | -307608.9 | OK |
| C02 | P(TP)-P(SL) | 5 | +0.1217 | -0.2398 | -217825.1 | 41272 | -0.2232 | -237310.8 | 42150 | -0.1077 | 0 | -307608.9 | OK |

## Val-selected (cell*, q*) — FORMAL verdict source (test touched once)

- cell: id=C01 picker=P(TP)
- selected q%: 5
- selected cutoff (val-fit scalar): +0.398615
- val: n_trades=41272, Sharpe=-0.2398, ann_pnl=-217825.1, MaxDD=65312.4
- test: n_trades=42150, Sharpe=-0.2232, ann_pnl=-237310.8, MaxDD=71201.1, A4_pos=0/4, A5_stress_ann_pnl=-307608.9
- gates: A0=OK A1=x A2=x A3=x A4=x A5=x
- FORMAL Spearman(score, realised_pnl) on test: -0.0505
- by-pair trade count: {'USD_JPY': 42150}
- by-direction trade count: {'long': 21075, 'short': 21075}

## Aggregate H1 / H2 / H3 / H4 outcome (val-selected (cell*, q*) on test)

- H1-weak (Spearman > 0.05): **False**
- H1-meaningful (Spearman >= 0.1): **False**
- H2 (A1 Sharpe >= 0.082 AND A2 ann_pnl >= 180.0): **False**
- H3 (realised Sharpe > Phase 25 best F1 -0.192): **False**
- H4 (realised Sharpe >= 0; structural-gap escape): **False**

### Verdict: **REJECT_NON_DISCRIMINATIVE** (H1_WEAK_FAIL)

**Note**: 26.0c-β cannot mint ADOPT_CANDIDATE. H2 PASS path resolves to PROMISING_BUT_NEEDS_OOS pending the separate A0-A5 8-gate harness PR.

## Cross-cell verdict aggregation (per 26.0c-α §7.2)

- per-cell branches: ['REJECT_NON_DISCRIMINATIVE']
- cells agree: **True**
- aggregate verdict: **REJECT_NON_DISCRIMINATIVE**

- C01 (P(TP)): REJECT_NON_DISCRIMINATIVE (H1_WEAK_FAIL)
- C02 (P(TP)-P(SL)): REJECT_NON_DISCRIMINATIVE (H1_WEAK_FAIL)

## L-1 vs L-2 vs L-3 comparison (mandatory section per 26.0c-α §9.6)

L-3 and L-2 reference values are from PR #303 (26.0a-β rev1) and PR #306 (26.0b-β) eval reports respectively. They are FIXED and do NOT recompute.

| Aspect | L-3 (PR #303) | L-2 (PR #306) | L-1 (this PR) |
|---|---|---|---|
| Val-selected cell signature | atr_normalised / Linear / q*=5% | atr_normalised / Linear / q*=5% | id=C01 picker=P(TP) / q*=5 |
| Val-selected test realised Sharpe | -0.2232 | -0.2232 | -0.2232 |
| Val-selected test ann_pnl (pip) | -237310.8 | -237310.8 | -237310.8 |
| Val-selected test n_trades | 42150 | 42150 | 42150 |
| Test Spearman (formal H1 signal) | -0.1419 | -0.1139 | -0.0505 |

**Interpretation guide**:
- If L-1 val-selected Sharpe >> L-2/L-3 → L-1 ternary classification structure breaks the structural-gap pattern that continuous-regression labels could not.
- If L-1 val-selected Sharpe ≈ L-2/L-3 → continuous-vs-classification axis is NOT the binding constraint at the minimum feature set; supports the leading hypothesis from post-26.0b routing review §3 / §4 (minimum-feature-set is binding).
- If L-1 test Spearman ≥ +0.05 → ranking signal exists; subsequent gating behaviour depends on realised PnL conversion at the selected quantile cutoff.

## Pair concentration per cell (DIAGNOSTIC-ONLY; per 26.0c-α §9.2)

CONCENTRATION_HIGH fires when val top-pair share >= 0.8. NOT consulted by `select_cell_validation_only` or `assign_verdict`.

| cell | picker | q% | val_top_pair | val_top_share | val_concentration_high | test_top_pair | test_top_share |
|---|---|---|---|---|---|---|---|
| C01 | P(TP) | 5 | USD_JPY | 1.0000 | True | USD_JPY | 1.0000 |
| C02 | P(TP)-P(SL) | 5 | USD_JPY | 1.0000 | True | USD_JPY | 1.0000 |

## Classification-quality diagnostics (DIAGNOSTIC-ONLY; per 26.0c-α §9.3)

AUC of P(TP) one-vs-rest / Cohen's κ / multiclass logloss / confusion matrix / per-class accuracy on test. NOT formal H1; NOT used in formal verdict routing per §6.1 binding.

| cell | picker | AUC(P(TP)) | Cohen κ | logloss | per-class acc (TP/SL/TIME) |
|---|---|---|---|---|---|
| C01 | P(TP) | 0.5479 | 0.0213 | 1.0940 | 0.428 / 0.394 / 0.251 |
| C02 | P(TP)-P(SL) | 0.5479 | 0.0213 | 1.0940 | 0.428 / 0.394 / 0.251 |

## Diagnostic absolute-probability thresholds (DIAGNOSTIC-ONLY; per 26.0c-α §9.4)

P(TP) candidates: (0.3, 0.4, 0.45, 0.5). P(TP)-P(SL) candidates: (0.0, 0.05, 0.1, 0.15). Reported per cell; NOT used in formal verdict routing.

| cell | picker | abs_thr | val_sharpe | val_n | test_sharpe | test_n |
|---|---|---|---|---|---|---|
| C01 | P(TP) | +0.3000 | -0.4147 | 440618 | -0.3692 | 499774 |
| C01 | P(TP) | +0.4000 | nan | 0 | nan | 0 |
| C01 | P(TP) | +0.4500 | nan | 0 | nan | 0 |
| C01 | P(TP) | +0.5000 | nan | 0 | nan | 0 |
| C02 | P(TP)-P(SL) | +0.0000 | -0.3622 | 213012 | -0.3256 | 228802 |
| C02 | P(TP)-P(SL) | +0.0500 | -0.3233 | 77192 | -0.3051 | 79362 |
| C02 | P(TP)-P(SL) | +0.1000 | -0.2398 | 41272 | -0.2232 | 42150 |
| C02 | P(TP)-P(SL) | +0.1500 | nan | 0 | nan | 0 |

## Isotonic-calibration appendix — OMITTED

Per 26.0c-α §4.3 / §9.5 binding: isotonic calibration is deferred. Fitting isotonic on val AND using the same val to select the quantile cutoff introduces selection-overfit risk. The 26.0c-β stub raises `NotImplementedError`. Deferred to a later sub-phase or diagnostic-only appendix.

## Multiple-testing caveat

2 formal cells × 5 quantile candidates = 10 primary (cell, q) pairs evaluated. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE verdicts are hypothesis-generating ONLY; production-readiness requires an X-v2-equivalent frozen-OOS PR per Phase 22 contract.
