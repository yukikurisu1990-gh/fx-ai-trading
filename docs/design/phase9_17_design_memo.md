# Phase 9.17 — Multi-strategy ensemble (Phase I) Kickoff Design Memo

**Status**: Draft — implementation pending
**Predecessor**: Phase 9.18 closed NO ADOPT 2026-04-26 (per-trade EV exhausted)
**Master tip at authorship**: `d4b51c8` (Phase 9.18 H-3 closure merged)
**Roadmap**: `docs/phase9_roadmap.md` §6.19 (lines 615-648)
**Style anchor**: `docs/design/phase9_18_design_memo.md`

---

## 1. Why this phase

Phase 9.13–9.18 confirmed empirically that the **single-strategy LightGBM stack has a Sharpe ceiling of 0.143–0.177** that cannot be broken by:

- Layer 1 features (Phase 9.4–9.9): SELECTOR plateau
- Risk multipliers / kill switches (Phase 9.13 C-3): +0.017 lift, then flat
- Pair-universe expansion (Phase 9.16): +20% PnL, Sharpe flat at 0.160
- Per-trade exit engineering (Phase 9.18): regression on both bucketed TP/SL and partial exits

The 9.18 closure memo's §8 finding — **"model confidence ≥ 0.65 hits at 54.1% vs 54.5% overall"** — is structural: more LightGBM cannot fix LightGBM. The model class itself is calibration-saturated.

The only remaining un-tried lever is **orthogonal alpha** — adding signal sources from a *different family* whose correlation with the LightGBM strategy is low enough that the ensemble Sharpe rises by the textbook formula:

```
Sharpe(ensemble) = (Sharpe_A + Sharpe_B) / sqrt(2 * (1 + ρ))
```

At ρ = 0.0 and equal-Sharpe components, ensemble Sharpe = single × √2 ≈ 1.41×. Even with ρ = 0.4, ensemble lift is ~+19%. **Below ρ ≈ 0.7, adding a strategy is net Sharpe-positive.**

---

## 2. Current state (research findings)

The codebase has **partial infrastructure** for multi-strategy already:

| Component | Status | Location |
|-----------|--------|----------|
| RSI / MACD / Bollinger strategies | Pure rule-based, `StrategyEvaluator` protocol implemented, **not wired into production** | `src/fx_ai_trading/services/strategies/{rsi,macd,bollinger}.py` |
| LightGBM `MLDirectionStrategy` | Production single-strategy | `src/fx_ai_trading/services/strategies/ai.py` |
| MetaDecider Score stage | **Multi-candidate ranking already exists** (EV × conf × regime_weight) | `src/fx_ai_trading/services/meta_decider.py:221-255` |
| SELECTOR layer | **Backtest-only** in `compare_multipair_*.py`; no production class | scripts only |
| Inter-strategy correlation | Interface exists; implementation is no-op stub (Phase 7+) | `src/fx_ai_trading/services/correlation_matrix.py` |
| `services/ml/ensemble.py` | **Does NOT exist** — was a Phase 9.12 reference that was never built | n/a |

**Implication**: the architectural skeleton (`StrategyEvaluator` protocol, MetaDecider candidate-list scoring) is in place. We do not need to invent the abstraction; we need to **wire additional strategies into the eval loop and extend SELECTOR over (pair × strategy)**.

---

## 3. Core hypothesis

**H-1 (orthogonality)**: At least one rule-based strategy from Phase 9.4 (or a new one) has return correlation ρ ≤ 0.4 with the LightGBM 20-pair v9 baseline, producing measurable Sharpe lift in ensemble.

**H-2 (selector enrichment)**: Extending SELECTOR from `argmax over pairs` to `argmax over (pair, strategy)` raises the trade count without proportional variance increase, because additional candidates fire in *different bars* than the LightGBM signal.

**H-3 (regime complementarity)**: Mean-reversion fires predominantly in `range` regime; LightGBM dominantly in `trend` regime (per Phase 9.7 ATRRegimeClassifier). This non-overlap in *time* is the dominant orthogonality channel, not direction-disagreement.

---

## 4. Why "more LightGBM" won't work

Re-iterating the 9.18 finding for explicit alignment with this phase's scope:

- LightGBM with 15 TA features hits 54.5% globally
- LightGBM with same features at confidence ≥ 0.65 hits 54.1%
- **Confidence is not a hit-rate predictor** for this model class

Therefore:
- An ensemble of LightGBM + XGBoost + CatBoost on the **same feature set** (the original Phase 9.12 plan in `services/ml/ensemble.py`) will inherit the same calibration ceiling.
- An ensemble of LightGBM trained on different feature subsets will be highly correlated (same data, same labeling, same target).
- **True orthogonality requires a different alpha-source family** — rule-based mean-reversion, breakout, or event-driven signals.

This memo therefore deliberately **defers the multi-ML-model ensemble** (Phase 9.12 ensemble.py) and prioritizes rule-based orthogonal strategies first.

---

## 5. Verdict gates (PnL-priority frame)

| Gate | Rule | Notes |
|------|------|-------|
| **GO** | PnL ≥ 1.10 × baseline AND Sharpe ≥ baseline AND inter-strategy ρ ≤ 0.4 AND DD%PnL ≤ 5% | adopt ensemble; promote in production |
| **PARTIAL GO** | PnL ≥ 1.05 × baseline AND Sharpe ≥ baseline AND DD%PnL ≤ 5% (correlation 0.4–0.6) | adopt with documented correlation drag |
| **STRETCH GO** | any cell reaches Sharpe ≥ 0.18 | unblocks Phase 9.11 (3+ yr robustness) regardless of PnL gate |
| **NO ADOPT** | PnL < baseline OR DD%PnL > 5% OR ρ > 0.6 | revert to symmetric v9 single-strategy baseline |

**Baseline** = Phase 9.16 production default: 20-pair v9 spread bundle, SELECTOR Sharpe 0.160, PnL 8,157 pip, DD%PnL 2.5%.

The **correlation gate is new vs 9.18**: ensemble adoption can fail even with PnL win if the strategies turn out to be near-duplicates.

---

## 6. Candidate strategy slate

### 6.1 Tier 1 — implement first (this phase)

| Rank | Strategy | Complexity | Orthogonality | Risk |
|------|----------|-----------|---------------|------|
| 1 | **Mean reversion (RSI/Bollinger fade)** | Low — features from Phase 9.4 already exist; needs label + entry threshold | **High** — LightGBM signal is dominantly trend-coded (MACD/EMA features); fading at band edges is structurally opposite | Low — no new data; only edge-decay risk |
| 2 | **Breakout (range-exit follow)** | Medium — needs range detector (Donchian) + confirmation bar | **Medium-High** — fires in regimes where trend-LightGBM is hesitant (post-consolidation) | Medium — false breakouts in chop |

Tier 1 is the **cheapest test of the orthogonality thesis**. If ρ between LightGBM and at least one of these is ≤ 0.4 AND ensemble Sharpe ≥ baseline, the thesis is validated.

### 6.2 Tier 2 — conditional on Tier 1 verdict

| Strategy | Why deferred |
|----------|--------------|
| Session opener momentum (London 7-9 UTC) | Narrow window, low trade count, statistical noise risk |
| News spike fade | Requires economic-calendar API (OANDA labs) integration; sparse training data |
| Carry overlay | Multi-day hold conflicts with current barrier semantics; needs overnight-rate data source |

Tier 2 work begins **only if** Tier 1 produces GO or PARTIAL GO. If Tier 1 is NO ADOPT, the binding constraint is structural (model class, label design) and Tier 2 won't fix it.

---

## 7. Selector redesign

Current SELECTOR (in `scripts/compare_multipair_*.py`):
```python
best_pair = max(active_pairs, key=lambda x: confidence(x))
```

Phase 9.17 SELECTOR:
```python
candidates = [
    (pair, strategy, signal, confidence, ev_after_cost)
    for pair in pairs
    for strategy in strategies
    if strategy.is_active(pair, bar)
]
best = max(candidates, key=lambda x: x.ev_after_cost * x.confidence)
```

**Conflict resolution** (when MR says short and LGBM says long on same pair, same bar):
- Default: **rank-by-EV-after-cost** wins (no special offsetting / netting)
- Document conflict frequency in closure memo per-cell summary

**Trade-book budget**: shared cap (one position-slot pool across strategies). Splitting forces sub-optimal under regime shifts.

**Position-overlap rule**: if SELECTOR picks (EUR/USD, MR, short) at bar t, and (EUR/USD, LGBM, long) at bar t+1, treat as independent trades (close prior, open new). Future-work: net-position semantics for Phase 9.X.

---

## 8. Eval pipeline architecture

Mirror the v9/v12 internal-sweep pattern (load + features once, eval N times):

```
1. Load 20-pair OHLC + features ONCE per fold
2. Train LightGBM model ONCE per fold (Phase 9.16 v9 baseline)
3. Compute MR signal per pair (rule-based, no training)
4. Compute Breakout signal per pair (rule-based, no training)
5. Eval-loop the cell sweep:
   - cell_a: LightGBM only (20-pair baseline reproduction)
   - cell_b: LightGBM + MR (2-strategy ensemble)
   - cell_c: LightGBM + Breakout (2-strategy ensemble)
   - cell_d: LightGBM + MR + Breakout (3-strategy ensemble)
6. Per-cell: SELECTOR over (pair × strategy) → trade book → PnL series
7. Inter-strategy correlation matrix from per-bar PnL series across folds
```

**Wall-time budget**: ~2× the Phase 9.18 v12 run (extra 2 cells × ~30 min/cell). Acceptable.

**Script name**: `scripts/compare_multipair_v13_ensemble.py`.

---

## 9. EV / Sharpe math

### 9.1 Ensemble Sharpe formula

For two strategies A, B with annualized Sharpe S_A, S_B and return correlation ρ:

```
Sharpe(0.5×A + 0.5×B) = (S_A + S_B) / (2 × sqrt((1 + 2ρ + 1) / 4))
                      = (S_A + S_B) / sqrt(2 × (1 + ρ))
```

### 9.2 Theoretical lift table (assuming S_A = S_B = 0.160)

| ρ | Ensemble Sharpe | Lift vs single | Verdict gate |
|---|----------------|----------------|--------------|
| 0.0 | 0.226 | +41% | clears 0.20 STRETCH GO |
| 0.2 | 0.207 | +29% | clears 0.20 STRETCH GO |
| 0.4 | 0.191 | +19% | clears 0.18 STRETCH GO |
| 0.5 | 0.185 | +16% | borderline 0.18 STRETCH GO |
| 0.6 | 0.180 | +12% | barely clears 0.18 STRETCH GO |
| 0.7 | 0.174 | +9% | misses 0.18 |
| 0.8 | 0.169 | +6% | misses 0.18 |
| 1.0 | 0.160 | 0% | no benefit |

**Critical threshold**: ρ ≤ 0.5 is the hard cut for "ensemble produces a meaningful lift."

### 9.3 Honesty disclosure

This memo's predicted outcome is **uncertain**. Phase 9.4's TA strategies were authored without an explicit orthogonality target — they may be highly correlated with LightGBM's MACD / EMA / RSI features (all of which the model already uses). The eval is the arbiter.

A plausible failure mode: MR / Breakout signals turn out to be ρ ≈ 0.7+ with LightGBM because the model has *implicitly* learned the same edge from the same features. If so, this phase produces NO ADOPT, and the only remaining lever is **alternative model class** (LSTM, transformer, alternative labels) — Phase 9.X.

---

## 10. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| MR / Breakout ρ > 0.5 vs LightGBM | Eval first; if confirmed, document and pivot to Tier 2 / alternative model class |
| Edge decay on rule-based strategies (parameter sensitivity) | Walk-forward training already controls this; do NOT optimize MR/Breakout parameters per fold (out-of-sample) |
| SELECTOR over-fitting to training-fold strategy mix | Each fold uses 90d train / 7d test; selector tie-breaks computed on out-of-sample per-strategy realized Sharpe within fold |
| Eval wall-time blowup | Internal sweep pattern (single load + features + train, multiple eval cells) caps wall-time at ~2× v12 |
| Strategy turnover / pair starvation | Shared trade-book budget = SELECTOR top-1 per bar; no per-strategy quota |
| Trade-book conflicts (same pair, opposite directions across strategies) | Document conflict frequency in closure memo; default rule = EV×confidence ranking wins |

---

## 11. PR breakdown

| PR | Scope | Size | Depends on |
|----|-------|------|-----------|
| **G-0** | This memo (`docs/design/phase9_17_design_memo.md`) | docs only | 9.18 closure (#205) |
| **G-1** | `services/strategies/mean_reversion.py` + label + unit tests; standalone single-strategy backtest to establish per-pair Sharpe | ~300 + tests | G-0 |
| **G-2** | `services/strategies/breakout.py` + label + unit tests; standalone backtest | ~300 + tests | G-0 (parallel to G-1) |
| **G-3** | `scripts/compare_multipair_v13_ensemble.py` — internal sweep over 4 cells; SELECTOR extended; inter-strategy correlation matrix | ~400 + tests | G-1, G-2 |
| **G-4** | `docs/design/phase9_17_closure_memo.md` — verdict, correlation matrix, per-strategy contribution | docs | G-3 |
| **G-5** *(conditional on GO/PARTIAL GO)* | Production runtime wiring — strategy registry, SELECTOR config schema; updates `meta_cycle_runner.py` to consume multi-strategy candidates | ~200 + tests | G-4 verdict |

**Timeline estimate**: ~2 days for G-1+G-2+G-3+G-4 (research / backtest only). G-5 is separate sub-day if triggered.

---

## 12. Out of scope

- Tier 2 strategies (News fade / Carry / Session opener) — deferred to Phase 9.17b conditional on Tier 1 verdict
- Multi-ML-model ensemble (LightGBM + XGBoost + CatBoost) — original Phase 9.12 plan; deferred indefinitely (will re-emerge as Phase 9.X if Tier 1+2 both fail)
- Phase 9.11 (3+ year robustness) — gated on STRETCH GO from this phase
- Production live mode integration — separate Phase 9.X after backtest closure

---

## 13. Open design questions (resolve before G-1 starts)

1. **Trade-book conflict resolution rule**: at a bar where two strategies pick the same pair in opposite directions, default = "EV × confidence ranks; higher wins, lower drops." Confirm before G-3.
2. **Correlation gate interpretation**: roadmap §6.19 says "ρ < 0.5"; this memo treats this as soft (PARTIAL GO at 0.4–0.6, NO ADOPT at > 0.6). Confirm threshold semantics.
3. **MR / Breakout parameter selection**: use Phase 9.4's hardcoded TA defaults (RSI 14, BB 20×2σ, Donchian 20)? Or sweep? Default = use 9.4 hardcoded values; note in closure memo that parameter robustness is a separate study.
4. **Per-strategy label choice**: keep triple-barrier 1.5/1.0×ATR for MR / Breakout (apples-to-apples PnL with LightGBM)? Or strategy-specific barriers? Default = same triple-barrier for comparability.
5. **Walk-forward fold count**: 39 folds (Phase 9.16 baseline)? Same train window? Default = same as v9 baseline for direct comparison.
6. **Per-pair strategy gating**: should JPY pairs only run LightGBM (excluded from MR/Breakout)? Default = all 20 pairs run all strategies; document JPY behavior in closure memo.

If user does not respond to these defaults, G-1 proceeds with the Default values listed.

---

## 14. References

- `docs/design/phase9_18_closure_memo.md` — confidence-doesn't-predict-hit-rate finding (motivates orthogonality requirement)
- `docs/design/phase9_16_closure_memo.md` — 20-pair v9 spread bundle = production baseline
- `docs/phase9_roadmap.md` §6.19 — candidate strategy slate (this memo defers 3 of 5 to Tier 2)
- `src/fx_ai_trading/services/strategies/{rsi,macd,bollinger}.py` — Phase 9.4 TA strategies (pattern reference for new MR / Breakout)
- `src/fx_ai_trading/services/meta_decider.py:221-255` — existing multi-candidate score stage
- `scripts/compare_multipair_v12_asymmetric.py` — eval pipeline template (clone for v13)

---

## 15. Commit trail

```
<TBD>    PR #???  G-0 this kickoff design memo
<TBD>    PR #???  G-1 mean_reversion strategy + standalone backtest
<TBD>    PR #???  G-2 breakout strategy + standalone backtest
<TBD>    PR #???  G-3 compare_multipair_v13_ensemble.py + closure memo input
<TBD>    PR #???  G-4 phase9_17_closure_memo.md
<TBD>    PR #???  G-5 production runtime wiring (CONDITIONAL on G-4 verdict)
```
