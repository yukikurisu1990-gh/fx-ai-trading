# Phase 9.X-B — Alternative features (multi-pattern) Kickoff Design Memo

**Status**: Draft — implementation pending
**Predecessor**: Phase 9.X-A closed NO ADOPT 2026-04-26 (label class is NOT the lever)
**Master tip at authorship**: `d9eab56` (after Phase 9.19/J-3 merged)
**Style anchor**: `docs/design/phase9_x_a_design_memo.md`

---

## 1. Why this phase

Phase 9.X-A confirmed: **label class is NOT the lever** (regression Sharpe 0.092 vs classifier 0.160). Combined with Phase 9.13–9.19 (all alpha-engineering levers feeding INTO the SELECTOR exhausted), the working hypothesis is now:

**The bottleneck is in the (LightGBM × 15 TA features) calibration pair.**

Phase 9.X-B attacks the **features axis** — the cheapest remaining test. If new feature groups break the Sharpe ceiling, features were the issue. If not, model class is the issue (→ Phase 9.X-C LSTM/TFT).

Per user direction: **try multiple feature patterns in parallel**, not just one. This produces more diagnostic information per session.

---

## 2. Three feature-group candidates (all OHLC-only)

| Group | Features added | Cost | Theoretical lift |
|-------|---------------|------|-------------------|
| **A — Volatility clustering** | rolling realized variance (5/20 bars), vol-of-vol (std of variance), variance ratio test, EWMA-half-life-30 conditional variance | ~40 lines | **Medium-High** — well-documented FX driver; complementary to existing ATR |
| **B — Higher-order moments** | rolling realized skewness (20 bars), kurtosis (20 bars), autocorrelation lag-1, lag-5 | ~30 lines | **Medium** — captures regime asymmetry; cheap |
| **C — Multi-TF deep extension** | daily resample stats (range%, return-3d, ATR-D), weekly stats (return-1w, range-1w), 4h ATR | ~50 lines | **Low-Medium** — Phase 9.4-9.9 already explored multi-TF; this is the deep-bar extension |

All three groups are OHLC-only — **no new data dependency**. Each can be enabled/disabled independently via CLI flag.

---

## 3. Sweep design

```
Cell                        Features added vs v9 spread baseline
baseline (v9)               none (Phase 9.16 production)
+vol                        + Group A
+moments                    + Group B
+mtf                        + Group C
+all                        + A + B + C combined
```

5 cells, single internal-sweep eval (load + features + train ONCE, eval per cell). Wall time ≈ 1 × baseline (~30-45 min for 20 pairs). Results compared in closure memo.

This isolates each feature group's individual contribution AND the combined effect (so we can detect feature-group interaction).

---

## 4. Verdict gates

Mirror Phase 9.X-A frame:

| Gate | Rule |
|------|------|
| **GO** | Sharpe ≥ 0.18 AND PnL ≥ 1.10 × baseline AND DD%PnL ≤ 5% |
| **PARTIAL GO** | Sharpe ≥ baseline AND PnL ≥ baseline AND DD%PnL ≤ 5% |
| **STRETCH GO** | Sharpe ≥ 0.20 (clears Phase 9.11 robustness gate) |
| **NO ADOPT** | Sharpe < baseline OR PnL < baseline OR DD%PnL > 5% |

Baseline = Phase 9.16 production default (Sharpe 0.160, PnL 8,157, DD%PnL 2.5%).

**Per-group verdict** is what matters here. If only one group lifts Sharpe, that's the answer; if all five cells fail, the bottleneck is at the model-class layer.

---

## 5. Honesty disclosure (calibration prior)

**The "trade-rate explosion + per-trade EV collapse" pattern has now repeated 4 times** (Phase 9.17, 9.17b, 9.19, 9.X-A). Across 4 different mechanisms, every attempt to extract more signal from the same feature space has resulted in PnL growth + Sharpe collapse.

**Prior probability for Phase 9.X-B: ~50% NO ADOPT**. The cheap OHLC-only feature groups may be too closely correlated with existing features to break the ceiling. The optimistic case (~30%) is one group has medium-to-high orthogonal lift; the pessimistic case (~20%) is all groups dilute Sharpe further.

If Phase 9.X-B fails:
- Pivot to Phase 9.X-C (LSTM, ~5 days) — last cheap test
- If that also fails → bottleneck is at **data source layer** (microstructure / orderbook required) → Phase 9.X-D

---

## 6. Implementation plan

| PR | Scope | Size |
|----|-------|------|
| **L-0** (this PR) | Kickoff design memo | docs only |
| L-1 | `compare_multipair_v16_features.py` (clone v14) + 3 feature group helpers + CLI flags + tests | ~250 lines + tests |
| L-2 | 5-cell 20-pair eval log + closure memo with verdict | log + docs |

L-1 and L-2 will be bundled into one overnight PR (similar to Phase 9.X-A).

---

## 7. Open design questions (defaults documented)

1. **Variance lookback windows** for Group A: {5, 20} bars chosen as short/long pair. Default. Could sweep {10, 30, 50} if Group A NO ADOPT.
2. **Higher-moment window** for Group B: 20 bars. Default. Aligns with bb_width window (20).
3. **Daily/weekly resample point**: end-of-bar (UTC). Default. Could test London-close anchor if NO ADOPT.
4. **Feature normalization**: leave raw (LightGBM is tree-based, normalization-insensitive). Default. No preprocessing change.
5. **Cross-pair feature interaction**: keep Phase 9.16 xp_* features for all 5 cells (apples-to-apples vs baseline).

---

## 8. Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| New features high-correlated with existing | Test each group individually first; only combined if individual lifts |
| GARCH-like vol features overfit to recent regime | Walk-forward CV already controls this; 39 folds × 7-day test windows |
| Daily/weekly resample sparsifies features (NaN) | Forward-fill within-day; drop training rows with NaN |
| Combined +all cell suffers from feature-multicollinearity | Document per-group results; combined is diagnostic only |
| 5-cell sweep wall time exceeds budget | Single train per fold, 5 evals per fold — should match v14 wall time |

---

## 9. Commit trail

```
<TBD>    PR #???  L-0..L-2 bundled — design memo + v16 script + 5-cell eval + closure memo
```
