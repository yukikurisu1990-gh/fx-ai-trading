# Stage 26.0a-β — L-3 EV Regression Eval (rev1)

Generated: 2026-05-11T23:07:07.305699+00:00

Design contract: `docs/design/phase26_0a_alpha_l3_design.md` (PR #301) + `docs/design/phase26_0a_alpha_rev1.md` (PR #302).

L-2 = generic continuous path-quality regression (parent family of L-3). **L-2 target excludes spread at label construction.** The 8-gate realised PnL still includes executable bid/ask spread/cost via inherited M1 path re-traverse. L-2 tests whether a generic continuous path-quality target ranks opportunities better without embedding spread into the training target. Quantile-of-val threshold family is the PRIMARY verdict basis; negative absolute thresholds are SECONDARY DIAGNOSTIC.

## Mandatory clauses (verbatim per 26.0a-α §9 + rev1 §11)

**1. Phase 26 framing.** Phase 26 is the entry-side return on alternative label / target designs on the 20-pair canonical universe. ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness.

**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / directional-comparison columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on any single one of them.

**3. γ closure preservation.** PR #279 is unmodified.

**4. Production-readiness preservation.** X-v2 OOS gating remains required before any production deployment. v9 20-pair (Phase 9.12) remains untouched.

**5. NG#10 / NG#11 not relaxed.**

**6. Phase 26 scope.** Phase 26 is NOT a continuation of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed.

## Production-misuse guards (verbatim per 26.0a-α §5.1)

**GUARD 1**: research-not-production.

**GUARD 2**: threshold-sweep-diagnostic.

**GUARD 3**: directional-comparison-diagnostic.

## L-2 vs L-3 boundary (per 26.0b-α §1.1 / §3.1)

**L-2 vs L-3 single-axis change**: L-3 (PR #301) embedded spread cost in the target at construction time (D-4: `label_pre = base_mid_pnl − spread_at_signal_pip × spread_factor`). L-2 OMITS D-4 entirely (`label_pre = base_mid_pnl`). Spread cost surfaces ONLY at 8-gate realised-PnL scoring stage via inherited `_compute_realised_barrier_pnl` (ask/bid path with original cost model — UNCHANGED from L-3). The L-2 no-double-counting clause is held VACUOUSLY because the L-2 target subtracts spread zero times (instead of one).

## Causality + no-double-counting notes (per 26.0a-α §3.1)

Spread cost is subtracted EXACTLY ONCE during label construction (D-4). Base PnL is mid-to-mid. Realised PnL fed to the 8-gate harness uses 25.0a-β `_compute_realised_barrier_pnl` (ask/bid path with original cost model) unchanged. Winsorisation (D-6) applies only to the training target y; harness realised PnL is NEVER winsorised.

## Threshold-selection design (per rev1 §3 / §4)

**PRIMARY family (formal verdict basis)**: quantile-of-val, top q% per candidate `{5, 10, 20, 30, 40}`. Cutoff is fit on val predictions ONLY (scalar value), then applied to test predictions as the same scalar. NO full-sample qcut; NO peeking at test predictions.

**SECONDARY DIAGNOSTIC family**: negative-spanning absolute candidates raw_pip [-5.0, -3.0, -1.0, 0.0, 1.0] / ATR-normalised [-0.5, -0.3, -0.1, 0.0, 0.1]. Reported per cell but NOT used for verdict.

## Pre-flight diagnostics

- label rows: 4056120
- horizon_bars (M1): 60
- pairs: 20
- LightGBM available: True
- LightGBM version: 4.6.0
- cells run in this sweep: 12

## Validation-only cell + quantile selection (per 26.0a-α §5.3)

Pre-filter: candidates with `val_n_trades >= A0-equivalent` are eligible. If none, LOW_VAL_TRADES flag is set and fallback to all valid candidates.

Tie-breaker order (deterministic):
1. max val realised Sharpe (primary)
2. max val annual_pnl
3. lower val MaxDD
4. simpler model class (LinearRegression > Ridge > LightGBM) — final deterministic tie-breaker only, NOT a model preference

- A0-equivalent val trade threshold: 21.0
- LOW_VAL_TRADES flag: False

## Split dates

- min: 2024-04-30 14:10:00+00:00
- train < 2025-09-23 12:11:00+00:00
- val [2025-09-23 12:11:00+00:00, 2026-01-10 23:45:30+00:00)
- test [2026-01-10 23:45:30+00:00, 2026-04-30 11:20:00+00:00]

## All cells — primary quantile-family summary (sorted by VAL realised Sharpe desc)

| scale | clip | model | q% | cutoff | val_sharpe | val_ann_pnl | val_n | test_sharpe | test_ann_pnl | test_n | test_spearman | A4 | A5_ann | h_state |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| atr_normalised | none | LinearRegression | 5 | -0.2574 | -0.2398 | -217825.1 | 41272 | -0.2232 | -237310.8 | 42150 | -0.1139 | 0 | -307608.9 | OK |
| atr_normalised | none | Ridge | 5 | -0.2574 | -0.2398 | -217825.1 | 41272 | -0.2232 | -237310.8 | 42150 | -0.1139 | 0 | -307608.9 | OK |
| atr_normalised | none | LightGBM | 5 | -0.2681 | -0.2398 | -217825.1 | 41272 | -0.2232 | -237310.8 | 42150 | -0.1198 | 0 | -307608.9 | OK |
| atr_normalised | q01_q99 | LinearRegression | 5 | -0.2576 | -0.2398 | -217825.1 | 41272 | -0.2232 | -237310.8 | 42150 | -0.1139 | 0 | -307608.9 | OK |
| atr_normalised | q01_q99 | Ridge | 5 | -0.2576 | -0.2398 | -217825.1 | 41272 | -0.2232 | -237310.8 | 42150 | -0.1139 | 0 | -307608.9 | OK |
| atr_normalised | q01_q99 | LightGBM | 5 | -0.2686 | -0.2398 | -217825.1 | 41272 | -0.2232 | -237310.8 | 42150 | -0.1187 | 0 | -307608.9 | OK |
| raw_pip | none | LinearRegression | 40 | -1.6996 | -0.3656 | -1032346.9 | 208925 | -0.3079 | -1235699.0 | 240871 | 0.3800 | 0 | -1637425.6 | OK |
| raw_pip | none | Ridge | 40 | -1.6996 | -0.3656 | -1032346.9 | 208925 | -0.3079 | -1235699.0 | 240871 | 0.3800 | 0 | -1637425.6 | OK |
| raw_pip | none | LightGBM | 40 | -1.8227 | -0.3656 | -1032346.9 | 208925 | -0.3079 | -1235699.0 | 240871 | 0.3817 | 0 | -1637425.6 | OK |
| raw_pip | q01_q99 | LinearRegression | 40 | -1.7054 | -0.3656 | -1032346.9 | 208925 | -0.3079 | -1235699.0 | 240871 | 0.3799 | 0 | -1637425.6 | OK |
| raw_pip | q01_q99 | Ridge | 40 | -1.7054 | -0.3656 | -1032346.9 | 208925 | -0.3079 | -1235699.0 | 240871 | 0.3799 | 0 | -1637425.6 | OK |
| raw_pip | q01_q99 | LightGBM | 40 | -1.8287 | -0.3656 | -1032346.9 | 208925 | -0.3079 | -1235699.0 | 240871 | 0.3845 | 0 | -1637425.6 | OK |

## Val-selected (cell*, q*) — FORMAL verdict source (test touched once)

- cell: scale=atr_normalised clip=none    model=LinearRegression
- selected q%: 5
- selected cutoff (val-fit scalar): -0.257432
- val: n_trades=41272, Sharpe=-0.2398, ann_pnl=-217825.1, MaxDD=65312.4
- test: n_trades=42150, Sharpe=-0.2232, ann_pnl=-237310.8, MaxDD=71201.1, A4_pos=0/4, A5_stress_ann_pnl=-307608.9
- gates: A0=OK A1=x A2=x A3=x A4=x A5=x
- regression diagnostics on test (diagnostic-only): R²=-0.0997, Pearson=0.0104, Spearman=-0.1139, MAE=5.7847, RMSE=6.8729, n=597666
- by-pair trade count: {'USD_JPY': 42150}
- by-direction trade count: {'long': 21075, 'short': 21075}

## Best cell by TEST Spearman (diagnostic-only; NOT used for verdict)

- cell: scale=raw_pip        clip=q01_q99 model=LightGBM        
- test Spearman: 0.3845 (R²=0.0156, Pearson=0.1559)
- test realised at primary q*: Sharpe=-0.3079, ann_pnl=-1235699.0, n_trades=240871
- **Diagnostic only; not used for verdict.**

## Best cell by TEST realised Sharpe (diagnostic-only; NOT used for verdict)

- cell: scale=atr_normalised clip=none    model=LinearRegression
- test realised Sharpe: -0.2232 (ann_pnl=-237310.8, n_trades=42150)
- test Spearman: -0.1139
- **Diagnostic only; not used for verdict.**

## Secondary DIAGNOSTIC absolute-threshold family (per cell; NOT used for verdict)

Per-cell best absolute-threshold result. Reported for reference only; the formal verdict basis is the primary quantile family above.

| scale | clip | model | abs_thr | val_sharpe | val_n | test_sharpe | test_n |
|---|---|---|---|---|---|---|---|---|
| atr_normalised | none | LinearRegression | -0.3000 | -0.2398 | 41272 | -0.2232 | 42150 |
| atr_normalised | none | Ridge | -0.3000 | -0.2398 | 41272 | -0.2232 | 42150 |
| atr_normalised | none | LightGBM | -0.3000 | -0.2398 | 41272 | -0.2232 | 42150 |
| atr_normalised | q01_q99 | LinearRegression | -0.3000 | -0.2398 | 41272 | -0.2232 | 42150 |
| atr_normalised | q01_q99 | Ridge | -0.3000 | -0.2398 | 41272 | -0.2232 | 42150 |
| atr_normalised | q01_q99 | LightGBM | -0.3000 | -0.2398 | 41272 | -0.2232 | 42150 |
| raw_pip | none | LinearRegression | -3.0000 | -0.4223 | 434650 | -0.3680 | 508962 |
| raw_pip | none | Ridge | -3.0000 | -0.4223 | 434650 | -0.3680 | 508962 |
| raw_pip | none | LightGBM | -3.0000 | -0.4137 | 453042 | -0.3655 | 527410 |
| raw_pip | q01_q99 | LinearRegression | -3.0000 | -0.4223 | 434650 | -0.3680 | 508962 |
| raw_pip | q01_q99 | Ridge | -3.0000 | -0.4223 | 434650 | -0.3680 | 508962 |
| raw_pip | q01_q99 | LightGBM | -3.0000 | -0.4223 | 434650 | -0.3680 | 508962 |

**Selected threshold family declaration**: the formal verdict basis is the quantile-family val-selected (cell*, q*) pair.

## Whether ranking signal monetises in top predicted-EV buckets (narrative)

- val-selected cell has test Spearman = -0.1139 (ranking-quality signal between predicted EV and realised pip PnL on test).
- At the val-selected q* = 5% cutoff, test realised Sharpe = -0.2232 and annual pip PnL = -237310.8.
- The ranking signal does NOT monetise at the selected quantile cutoff (realised Sharpe < 0). H4 FAIL: structural-gap signature persists at this label / barrier / spread-cost combination.

## L-2 vs L-3 comparison (mandatory section)

L-3 reference values are from PR #303 26.0a-β rev1 eval (fixed, do NOT recompute):

| Aspect | L-3 (PR #303) | L-2 (this PR) |
|---|---|---|
| Val-selected test realised Sharpe | -0.2232 | -0.2232 |
| Val-selected test Spearman (formal) | -0.1419 | -0.1139 |
| Best-by-test-Spearman diagnostic | +0.3836 (raw_pip / LightGBM cell) | +0.3845 |
| Best-by-test-Sharpe diagnostic | -0.2232 | -0.2232 |

**Interpretation guide**:
- If L-2 val-selected Sharpe > L-3 val-selected Sharpe → L-3 spread-embedding step harmed realised PnL conversion.
- If L-2 val-selected Sharpe ≈ L-3 val-selected Sharpe → continuous-target labelling at minimum feature set is the binding issue regardless of spread embedding.
- If L-2 best-by-Spearman > L-3's +0.3836 → L-2 ranking signal is stronger; if ≈ similar → L-3's ranking signal was not spread-driven.

## Pair concentration per cell (per 26.0b-α §4.1; diagnostic-only; NOT used for verdict)

Val concentration = top-pair share among traded rows at the val-fit cutoff. CONCENTRATION_HIGH flag fires when val top-pair share >= 0.8.

| scale | clip | model | q% | val_top_pair | val_top_share | val_concentration_high | test_top_pair | test_top_share |
|---|---|---|---|---|---|---|---|---|
| atr_normalised | none | LinearRegression | 5 | USD_JPY | 1.0000 | True | USD_JPY | 1.0000 |
| atr_normalised | none | Ridge | 5 | USD_JPY | 1.0000 | True | USD_JPY | 1.0000 |
| atr_normalised | none | LightGBM | 5 | USD_JPY | 1.0000 | True | USD_JPY | 1.0000 |
| atr_normalised | q01_q99 | LinearRegression | 5 | USD_JPY | 1.0000 | True | USD_JPY | 1.0000 |
| atr_normalised | q01_q99 | Ridge | 5 | USD_JPY | 1.0000 | True | USD_JPY | 1.0000 |
| atr_normalised | q01_q99 | LightGBM | 5 | USD_JPY | 1.0000 | True | USD_JPY | 1.0000 |
| raw_pip | none | LinearRegression | 40 | USD_JPY | 0.1975 | False | USD_JPY | 0.1750 |
| raw_pip | none | Ridge | 40 | USD_JPY | 0.1975 | False | USD_JPY | 0.1750 |
| raw_pip | none | LightGBM | 40 | USD_JPY | 0.1975 | False | USD_JPY | 0.1750 |
| raw_pip | q01_q99 | LinearRegression | 40 | USD_JPY | 0.1975 | False | USD_JPY | 0.1750 |
| raw_pip | q01_q99 | Ridge | 40 | USD_JPY | 0.1975 | False | USD_JPY | 0.1750 |
| raw_pip | q01_q99 | LightGBM | 40 | USD_JPY | 0.1975 | False | USD_JPY | 0.1750 |

**Diagnostic only; not used for verdict.** The CONCENTRATION_HIGH flag is NOT consulted by `select_cell_validation_only` or `assign_verdict`.

## Aggregate H1 / H2 / H3 / H4 outcome (val-selected (cell*, q*) on test)

- H1-weak (Spearman > 0.05): **False**
- H1-meaningful (Spearman >= 0.1; formal H1 PASS): **False**
- H2 (A1 Sharpe >= 0.082 AND A2 ann_pnl >= 180.0): **False**
- H3 (realised Sharpe > Phase 25 best F1 -0.192): **False**
- H4 (realised Sharpe >= 0; structural-gap escape): **False**

### Verdict: **REJECT_NON_DISCRIMINATIVE** (H1_WEAK_FAIL)

## Multiple-testing caveat

12 cells × 5 quantile candidates = 60 primary (cell, q) pairs evaluated. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE verdicts are hypothesis-generating ONLY; production-readiness requires an X-v2-equivalent frozen-OOS PR per Phase 22 contract.
