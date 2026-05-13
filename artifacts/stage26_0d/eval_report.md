# Stage 26.0d-β — R6-new-A Feature-Widening Audit Eval Report

Generated: 2026-05-13T23:45:06.024005+00:00

Design contract: `docs/design/phase26_0d_alpha_r6_new_a_design_memo.md` (PR #312) under scope amendment `docs/design/phase26_scope_amendment_feature_widening.md` (PR #311).

R6-new-A is a feature-widening AUDIT, NOT a model-class comparison. The tested intervention is the closed two-feature allowlist (`atr_at_signal_pip`, `spread_at_signal_pip`) added to the Phase 26 minimum feature set (`pair + direction`). Model class is held fixed at the conservative LightGBM multiclass configuration inherited from 26.0c-β (PR #309).

## Mandatory clauses (clause 6 AMENDED per PR #311 §8)

**1. Phase 26 framing.** Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.

**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison / classification-quality / feature-importance columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.

**3. γ closure preservation.** PR #279 is unmodified.

**4. Production-readiness preservation.** X-v2 OOS gating remains required before any production deployment. v9 20-pair (Phase 9.12) remains untouched.

**5. NG#10 / NG#11 not relaxed.**

**6. Phase 26 scope (AMENDED).** Phase 26's primary axis is label / target redesign on the 20-pair canonical universe. Phase 26 is NOT a revival of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed under Phase 25 semantics. A narrow feature-widening audit (R6-new-A) is authorised under the scope amendment in PR #311 with a closed allowlist of two features (`atr_at_signal_pip`, `spread_at_signal_pip`); all other features are out of scope until a further scope amendment. R6-new-A is a Phase 26 audit of the minimum-feature-set hypothesis; it is NOT a Phase 25 continuation.

## D-1 binding (formal realised-PnL = inherited harness)

Formal realised-PnL scoring uses the inherited `_compute_realised_barrier_pnl` (bid/ask executable; same harness as L-2 / L-3 / L-1). Mid-to-mid PnL appears in the sanity probe / label diagnostic only and is NEVER the formal realised-PnL metric.

## Closed feature allowlist (per PR #311 §3 / 26.0d-α §2)

- ADMITTED: ['pair', 'direction', 'atr_at_signal_pip', 'spread_at_signal_pip'] (pair + direction one-hot; atr_at_signal_pip + spread_at_signal_pip numeric passthrough)
- NOT ADMITTED: Phase 25 F1/F2/F3/F5 full feature sets; F4/F6/F5-d/F5-e (Phase 25 deferred-not-foreclosed); multi-TF; calendar; external-data. (Each excluded class requires a separate scope amendment.)

## Sanity probe results (per 26.0d-α §12)

- status: **PASS**
- class priors (train):
  - TP: 565106 (19.215%)
  - SL: 2184896 (74.290%)
  - TIME: 191030 (6.495%)
- per-pair TIME-share > 99% pairs: []
- realised-PnL cache basis: inherited_compute_realised_barrier_pnl_bid_ask_executable
- new-feature NaN rate per split:
  - train.atr_at_signal_pip: 0 / 2941032 (0.000%)
  - train.spread_at_signal_pip: 0 / 2941032 (0.000%)
  - val.atr_at_signal_pip: 0 / 517422 (0.000%)
  - val.spread_at_signal_pip: 0 / 517422 (0.000%)
  - test.atr_at_signal_pip: 0 / 597666 (0.000%)
  - test.spread_at_signal_pip: 0 / 597666 (0.000%)
- new-feature distribution on TRAIN:
  - atr_at_signal_pip: n=2941032 mean=+5.959 p5=+2.287 p50=+4.985 p95=+12.788 min=+1.345 max=+85.332
  - spread_at_signal_pip: n=2941032 mean=+2.169 p5=+1.300 p50=+1.900 p95=+3.700 min=+0.800 max=+35.600

## Row-drop policy (per Decision F; 26.0d-α §5.2)

- train: n_input=2941032 n_kept=2941032 n_dropped=0; per-feature NaN: {'atr_at_signal_pip': 0, 'spread_at_signal_pip': 0}
- val: n_input=517422 n_kept=517422 n_dropped=0; per-feature NaN: {'atr_at_signal_pip': 0, 'spread_at_signal_pip': 0}
- test: n_input=597666 n_kept=597666 n_dropped=0; per-feature NaN: {'atr_at_signal_pip': 0, 'spread_at_signal_pip': 0}

## Pre-flight diagnostics

- label rows (pre-drop): 4056120
- horizon_bars (M1): 60
- pairs: 20
- LightGBM available: True
- LightGBM version: 4.6.0
- formal cells run: 2

## Validation-only cell + quantile selection

Pre-filter: candidates with `val_n_trades >= A0-equivalent`. Tie-breakers: max val Sharpe → max val ann_pnl → lower val MaxDD → smaller q%.

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
| C01 | P(TP) | 5 | +0.4155 | -0.2446 | -132789.0 | 25890 | -0.2511 | -138766.2 | 25357 | 0.0226 | 0 | -181056.8 | OK |
| C02 | P(TP)-P(SL) | 5 | +0.1262 | -0.1863 | -142234.1 | 25881 | -0.1732 | -204664.4 | 34626 | -0.1535 | 0 | -262414.0 | OK |

## Val-selected (cell*, q*) — FORMAL verdict source

- cell: id=C02 picker=P(TP)-P(SL)
- selected q%: 5
- selected cutoff (val-fit scalar): +0.126233
- val: n_trades=25881, Sharpe=-0.1863, ann_pnl=-142234.1, MaxDD=42634.3
- test: n_trades=34626, Sharpe=-0.1732, ann_pnl=-204664.4, MaxDD=61385.6, A4_pos=0/4, A5_stress_ann_pnl=-262414.0
- gates: A0=OK A1=x A2=x A3=x A4=x A5=x
- FORMAL Spearman(score, realised_pnl) on test: -0.1535
- by-pair trade count: {'EUR_USD': 1833, 'GBP_USD': 3568, 'AUD_USD': 1803, 'NZD_USD': 12, 'USD_CHF': 34, 'USD_CAD': 350, 'USD_JPY': 24721, 'EUR_JPY': 654, 'GBP_JPY': 985, 'AUD_JPY': 657, 'CHF_JPY': 7, 'EUR_AUD': 2}
- by-direction trade count: {'long': 18308, 'short': 16318}

## Aggregate H1 / H2 / H3 / H4 outcome

- H1-weak (Spearman > 0.05): **False**
- H1-meaningful (Spearman >= 0.1): **False**
- H2 (A1 Sharpe >= 0.082 AND A2 ann_pnl >= 180.0): **False**
- H3 (realised Sharpe > Phase 25 best F1 -0.192): **True**
- H4 (realised Sharpe >= 0; structural-gap escape): **False**

### Verdict: **REJECT_NON_DISCRIMINATIVE** (H1_WEAK_FAIL)

**Note**: 26.0d-β cannot mint ADOPT_CANDIDATE. H2 PASS path resolves to PROMISING_BUT_NEEDS_OOS pending the separate A0-A5 8-gate harness PR.

## Cross-cell verdict aggregation (per 26.0c-α §7.2)

- per-cell branches: ['REJECT_NON_DISCRIMINATIVE']
- cells agree: **True**
- aggregate verdict: **REJECT_NON_DISCRIMINATIVE**

- C01 (P(TP)): REJECT_NON_DISCRIMINATIVE (H1_WEAK_FAIL)
- C02 (P(TP)-P(SL)): REJECT_NON_DISCRIMINATIVE (H1_WEAK_FAIL)

## MANDATORY: L-1 / L-2 / L-3 vs R6-new-A 4-column comparison (per 26.0d-α §13.1)

L-3 / L-2 / L-1 reference values from PR #303 / #306 / #309. FIXED; do NOT recompute.

| Aspect | L-3 (PR #303) | L-2 (PR #306) | L-1 (PR #309) | R6-new-A (this PR) |
|---|---|---|---|---|
| Label class | continuous regression (spread-embedded) | continuous regression (mid-to-mid) | ternary classification | ternary classification (inherited from L-1) |
| Feature set | pair + direction | pair + direction | pair + direction | pair + direction + atr_at_signal_pip + spread_at_signal_pip |
| Val-selected cell signature | atr_normalised / Linear / q*=5% | atr_normalised / Linear / q*=5% | C01 P(TP) / q*=5% | id=C02 picker=P(TP)-P(SL) / q*=5 |
| Val-selected test realised Sharpe | -0.2232 | -0.2232 | -0.2232 | -0.1732 |
| Val-selected test ann_pnl (pip) | -237310.8 | -237310.8 | -237310.8 | -204664.4 |
| Val-selected test n_trades | 42150 | 42150 | 42150 | 34626 |
| Test Spearman (formal H1) | -0.1419 | -0.1139 | -0.0505 (C01) / -0.1077 (C02) | -0.1535 |
| Pair concentration on test | 100% USD_JPY | 100% USD_JPY | 100% USD_JPY | USD_JPY 71.4% |
| Verdict | REJECT_NON_DISCRIMINATIVE | REJECT_NON_DISCRIMINATIVE | REJECT_NON_DISCRIMINATIVE | REJECT_NON_DISCRIMINATIVE |

## MANDATORY: Identity-break YES / NO / PARTIAL paragraph (per 26.0d-α §13.2-§13.4)

**Did the closed two-feature allowlist (`atr_at_signal_pip`, `spread_at_signal_pip`) change the val-selected trade set away from the L-1 / L-2 / L-3 identity outcome (n_trades=42,150 ; Sharpe=-0.2232 ; ann_pnl=-237,310.8 ; 100% USD_JPY)? **YES_IMPROVED**.**

- n_trades observed: 34626 (baseline 42,150 ; delta -7524)
- Sharpe observed: -0.1732 (baseline -0.2232 ; delta +0.0500)
- ann_pnl observed: -204664.4 (baseline -237,310.8 ; delta +32646.4)
- top pair observed: USD_JPY share 0.714 (baseline USD_JPY 1.000 ; delta -0.286)

**Interpretation**: Val-selected trade set differs from baseline AND test Sharpe improved by +0.0500. The closed two-feature allowlist broke the identity and improved realised PnL. The minimum-feature-set hypothesis (post-26.0c §3 / §4) is SUPPORTED as binding at this closed allowlist. Routes to H1/H2/H3 ladder per design memo §9.

## Pair concentration per cell (DIAGNOSTIC-ONLY; per 26.0c-α §9.2)

CONCENTRATION_HIGH fires when val top-pair share >= 0.8. NOT consulted by `select_cell_validation_only` or `assign_verdict`.

| cell | picker | q% | val_top_pair | val_top_share | val_concentration_high | test_top_pair | test_top_share |
|---|---|---|---|---|---|---|---|
| C01 | P(TP) | 5 | USD_JPY | 1.0000 | True | USD_JPY | 1.0000 |
| C02 | P(TP)-P(SL) | 5 | USD_JPY | 0.8685 | True | USD_JPY | 0.7139 |

## Classification-quality diagnostics (DIAGNOSTIC-ONLY)

| cell | picker | AUC(P(TP)) | Cohen κ | logloss | per-class acc (TP/SL/TIME) |
|---|---|---|---|---|---|
| C01 | P(TP) | 0.5765 | 0.0986 | 1.0338 | 0.289 / 0.544 / 0.474 |
| C02 | P(TP)-P(SL) | 0.5765 | 0.0986 | 1.0338 | 0.289 / 0.544 / 0.474 |

## Feature importance (DIAGNOSTIC-ONLY; per 26.0d-α §11.4 / Decision D10)

LightGBM gain importance aggregated into 4 buckets (`pair_*` one-hots → `pair`; `direction_*` one-hots → `direction`; `atr_at_signal_pip` and `spread_at_signal_pip` individually). DIAGNOSTIC-ONLY; NOT used in formal verdict routing.

| cell | picker | pair (gain) | direction (gain) | atr_at_signal_pip (gain) | spread_at_signal_pip (gain) | pair (%) | direction (%) | atr (%) | spread (%) |
|---|---|---|---|---|---|---|---|---|---|
| C01 | P(TP) | 2631.0 | 335.0 | 3295.0 | 2496.0 | 0.300 | 0.038 | 0.376 | 0.285 |
| C02 | P(TP)-P(SL) | 2631.0 | 335.0 | 3295.0 | 2496.0 | 0.300 | 0.038 | 0.376 | 0.285 |

## Diagnostic absolute-probability thresholds (DIAGNOSTIC-ONLY)

P(TP) candidates: (0.3, 0.4, 0.45, 0.5). P(TP)-P(SL) candidates: (0.0, 0.05, 0.1, 0.15). NOT used in formal verdict routing.

| cell | picker | abs_thr | val_sharpe | val_n | test_sharpe | test_n |
|---|---|---|---|---|---|---|
| C01 | P(TP) | +0.3000 | -0.3671 | 367941 | -0.3303 | 417641 |
| C01 | P(TP) | +0.4000 | -0.2505 | 31760 | -0.2497 | 31031 |
| C01 | P(TP) | +0.4500 | nan | 0 | nan | 0 |
| C01 | P(TP) | +0.5000 | nan | 0 | nan | 0 |
| C02 | P(TP)-P(SL) | +0.0000 | -0.2915 | 172928 | -0.2683 | 253894 |
| C02 | P(TP)-P(SL) | +0.0500 | -0.2542 | 105453 | -0.2348 | 168182 |
| C02 | P(TP)-P(SL) | +0.1000 | -0.2123 | 48161 | -0.1952 | 81831 |
| C02 | P(TP)-P(SL) | +0.1500 | -0.1774 | 16239 | -0.1663 | 18260 |

## Isotonic-calibration appendix — OMITTED per 26.0c-α §4.3 (preserved)

Fitting isotonic on val AND using the same val to select the quantile cutoff introduces selection-overfit risk. `compute_isotonic_diagnostic_appendix` stub raises `NotImplementedError`. Deferred to later sub-phase.

## Multiple-testing caveat

2 formal cells × 5 quantile candidates = 10 primary (cell, q) pairs evaluated. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE verdicts are hypothesis-generating ONLY; production-readiness requires an X-v2-equivalent frozen-OOS PR per Phase 22 contract.
