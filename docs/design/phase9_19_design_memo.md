# Phase 9.19 — SELECTOR multi-pick (Top-K) Kickoff Design Memo

**Status**: Draft — implementation pending
**Predecessor**: Phase 9.17b closed NO ADOPT 2026-04-26 (Option A — confidence threshold filter — failed)
**Master tip at authorship**: `0203c34` (Phase 9.17b/I-2 merged)
**Style anchor**: `docs/design/phase9_17_design_memo.md`

---

## 1. Why this phase

Phase 9.13–9.18 / 9.17b confirmed that **all alpha levers feeding INTO the SELECTOR have been exhausted**:

- Layer 1 features (Phase 9.4–9.9, 9.15): SELECTOR plateau
- Risk multipliers / kill switches (Phase 9.13 C-3): +0.017 lift, then flat
- Pair-universe expansion (Phase 9.16): +20% PnL, Sharpe flat at 0.160
- Per-trade exit engineering (Phase 9.18): regression on bucketed TP/SL and partial exits
- Multi-strategy ensemble (Phase 9.17): NO ADOPT despite strategies being orthogonal (ρ ≤ 0.58)
- Confidence-threshold filter on rule strategies (Phase 9.17b): +0.005 Sharpe across full sweep

Every approach so far has modified what *feeds into* the SELECTOR. **None has modified the SELECTOR rule itself.**

The SELECTOR rule is currently `argmax over (pair × strategy)` → **exactly one trade per bar**. This caps the trade rate at the per-bar cadence. Phase 9.16 closure memo §3 already noted: *"realistic pair-set doubling lift is +5–15%, NOT the textbook +50–100%"* because expanding the candidate pool doesn't expand the trade rate when the picker takes only one.

Phase 9.19 attacks the **SELECTOR rule** axis — taking the top-K candidates per bar instead of top-1.

---

## 2. Current state

The v13 SELECTOR (Phase 9.17 G-3, in `compare_multipair_v13_ensemble.py:_eval_fold`):

```python
candidates = [(p, s) for p in all_pairs for s in cell_strategies]
conf_for_pick = np.where(traded_mat, conf_mat, -1.0)
sel_cand_idx = np.argmax(conf_for_pick, axis=0)  # <-- 1 per bar
```

For 20 pairs × N strategies, this reduces a candidate pool of up to 20×N to a single trade per bar. With 39 folds × ~3,200 bars/fold ≈ 125k bars, the trade rate caps at ~12,461 (the SELECTOR-eligible bars). Phase 9.17 confirmed: trade rate is structurally bound by this rule, not by candidate availability.

---

## 3. Core hypothesis

**H-1 (multi-pick lift)**: Taking the top-K LGBM picks per bar (K ≥ 2) at SELECTOR time multiplies the trade rate by approximately K. If picks are sufficiently independent (ρ ≤ 0.4), the ensemble Sharpe scales by sqrt(K) per the standard formula:

```
Sharpe(K independent picks) = sqrt(K) × Sharpe(1 pick)
```

At K=3 with the Phase 9.16 baseline (Sharpe 0.160), theoretical Sharpe = 0.277 (clears the 0.20 GO gate).

**H-2 (correlation reality)**: FX pair correlations within a currency family are typically 0.5–0.7 (EUR/USD long ≈ GBP/USD long, both USD short). Naive top-K may pick highly correlated pairs from the same family, eroding the lift. **Diversification-aware top-K** (limit one pick per currency family) should outperform naive top-K.

**H-3 (per-strategy contribution)**: With K = 3+ slots, multi-strategy cells (lgbm+mr+bo) become viable again — Phase 9.17's failure was *competition for the single slot*. With multiple slots, MR/BO can fill remaining bars where LGBM doesn't dominate. The MR vs BO anti-correlation (ρ = -0.669 at t=0.5) becomes useful again.

---

## 4. Why this could work where prior phases failed

All prior phases attacked SELECTOR *inputs*:

| Phase | Lever | Result |
|-------|-------|--------|
| 9.4–9.9 | Layer 1 features | SELECTOR plateau |
| 9.13 | Risk multipliers (output gate) | +0.017 |
| 9.15 | Orthogonal features | spread bundle = production |
| 9.16 | Pair pool expansion | +20% PnL, Sharpe flat |
| 9.18 | Exit policy (per-trade EV) | regression |
| 9.17 / 9.17b | More strategies + thresholds | NO ADOPT (drowning) |

Phase 9.19 is the first phase to modify the **SELECTOR rule itself**. The lever is structurally orthogonal to all prior attempts. The trade-rate × independence Sharpe-lift math is well-known and applies whenever ρ < 1 between picks.

---

## 5. Verdict gates (PnL-priority + diversification gate)

| Gate | Rule |
|------|------|
| **GO** | PnL ≥ 1.30 × baseline AND Sharpe ≥ 0.18 AND DD%PnL ≤ 5% AND mean ρ between picks ≤ 0.5 |
| **PARTIAL GO** | PnL ≥ 1.20 × baseline AND Sharpe ≥ baseline AND DD%PnL ≤ 5% (mean ρ 0.5–0.7) |
| **STRETCH GO** | any (K, variant) reaches Sharpe ≥ 0.20 — clears Phase 9.11 robustness gate |
| **NO ADOPT** | PnL < baseline OR DD%PnL > 5% OR mean ρ > 0.7 |

Notes:
- The PnL gate is **higher** here (1.30× vs 1.10× in 9.17). With K=3 we expect roughly 3× trade volume, so PnL must reflect that. PnL ≥ 1.30× is intentionally below 3× to allow for spread cost and pick-overlap effects.
- Mean ρ is calculated per-bar across the K simultaneous picks (rolling window).
- Baseline = Phase 9.16 production default (Sharpe 0.160, PnL 8,157).

---

## 6. Variants — Tier 1 / Tier 2

### 6.1 Tier 1 — naive top-K (this phase)

Simplest implementation: at each bar, take the K highest-confidence candidates from the (pair × strategy) candidate matrix. K is a CLI parameter; sweep K ∈ {1, 2, 3, 5} for evaluation.

**Cost**: ~0.5 day implementation. Baseline test of the multi-pick thesis.

### 6.2 Tier 2 — diversification-aware top-K (this phase)

Constraint: at most one pick per currency family per bar. Currency families derived from the 20-pair universe:

```
USD-base:    USD_JPY, USD_CHF, USD_CAD
EUR-base:    EUR_USD, EUR_GBP, EUR_JPY, EUR_CHF, EUR_AUD, EUR_CAD
GBP-base:    GBP_USD, GBP_JPY, GBP_AUD, GBP_CHF
AUD-base:    AUD_USD, AUD_JPY, AUD_NZD, AUD_CAD
NZD-base:    NZD_USD, NZD_JPY
CHF-base:    (covered)
```

Diversification rule: a pair "uses" both currencies in its name (EUR/USD uses EUR and USD slots). At each bar, greedily pick top-confidence candidates while respecting per-currency caps.

**Cost**: +0.5 day on top of Tier 1. Tests whether currency-family clustering is the bottleneck.

### 6.3 Tier 3 — DEFERRED

- Sharpe-weighted picking (rank candidates by Sharpe-of-fold, not raw confidence)
- Regime-aware multi-pick (different K per regime)
- Risk-budget allocator (Markowitz-style portfolio optimization)

These are larger scope; defer until Tier 1+2 verdict.

---

## 7. Selector redesign details

### 7.1 Top-K argpartition

Replace:
```python
sel_cand_idx = np.argmax(conf_for_pick, axis=0)
```

With:
```python
# Top-K per bar (descending). conf_for_pick is (n_candidates, n_lab).
# np.argpartition is O(N) per axis; we negate to get descending order.
top_k_idx = np.argpartition(-conf_for_pick, k - 1, axis=0)[:k, :]
# top_k_idx is (k, n_lab); each column is the k candidate indices.
```

### 7.2 Diversification-aware variant

```python
# Build currency family map once at fold setup.
pair_to_families: dict[str, tuple[str, ...]] = {p: _split_pair(p) for p in all_pairs}

# Per-bar greedy fill with per-family caps.
for bar in range(n_lab):
    candidates = sorted(active_for_bar, key=lambda c: -c.confidence)
    used_currencies: set[str] = set()
    picked = []
    for c in candidates:
        family_a, family_b = pair_to_families[c.pair]
        if family_a in used_currencies or family_b in used_currencies:
            continue
        picked.append(c)
        used_currencies.update({family_a, family_b})
        if len(picked) >= k:
            break
```

### 7.3 PnL aggregation across picks

For each bar's K picks, compute per-bar gross PnL as the **sum** of the K individual gross PnLs (not the mean). This represents taking K full-size positions.

Position-sizing caveat (for production): real trading would split risk budget across K. Backtest sums for Sharpe comparability with the 1-pick baseline; add a `--position-size-fraction` flag for production-realistic backtest if Tier 1 results are promising.

### 7.4 Conflict resolution

Multi-pick can produce contradictory signals on the *same* pair from different strategies (e.g., MR says short EUR/USD, LGBM says long EUR/USD, both in the top-K). Default rule: **same-pair conflicting picks net out** — sum is zero. Alternative: **drop the lower-confidence one before the next pick**. Default chosen for simplicity; can be swept later.

---

## 8. Eval pipeline architecture

Reuse v13's internal-sweep pattern. New cell sweep dimension is K, not strategy set:

```
Cell                              K=1 (baseline)   K=2   K=3   K=5
lgbm_only                         (existing)       new   new   new
lgbm+mr+bo (full ensemble)        (existing)       new   new   new
```

8 cells per eval = ~2× wall time vs Phase 9.17 (manageable, ~60 min).

**Diversification variant**: rerun the 8 cells with `--diversify-by-currency`. Total = 16 cells per eval.

**Script name**: `scripts/compare_multipair_v14_topk.py` (clone v13 and modify SELECTOR).

---

## 9. Risk / Sharpe math

### 9.1 Naive top-K with uniform correlation ρ

For K independent draws from a strategy with Sharpe S and pairwise correlation ρ:

```
Sharpe(K-portfolio) = K × S / sqrt(K + K(K-1)ρ)
                    = S × sqrt(K) / sqrt(1 + (K-1)ρ)
```

Lift table (S = 0.160 baseline):

| K | ρ=0.0 | ρ=0.3 | ρ=0.5 | ρ=0.7 |
|---|-------|-------|-------|-------|
| 1 | 0.160 | 0.160 | 0.160 | 0.160 |
| 2 | 0.226 | 0.198 | 0.184 | 0.173 |
| 3 | 0.277 | 0.224 | 0.196 | 0.179 |
| 5 | 0.358 | 0.252 | 0.207 | 0.183 |

**Critical findings**:
- At ρ = 0.7 (typical USD-family correlation), even K=5 gives only Sharpe 0.183 — barely clears 0.18 STRETCH GO.
- Diversification-aware variant should reduce mean ρ from ~0.7 to ~0.3 by avoiding USD-family clustering.
- At ρ = 0.3 with K=3, Sharpe = 0.224 (clears 0.20 LEGACY GO).

### 9.2 Honesty disclosure

The math assumes equal Sharpe per pick. Real picks at K > 1 are necessarily lower-confidence than the top-1; their per-trade EV is presumably lower. The Sharpe lift formula gives an **upper bound**.

A plausible failure mode: the K-th pick has Sharpe << S → adding it dilutes the portfolio Sharpe. We'll monitor per-pick Sharpe in eval output.

---

## 10. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| FX pair correlations destroy the sqrt(K) lift | Tier 2 (diversify-by-currency) explicitly addresses this |
| Lower-conf picks dilute Sharpe | Eval emits per-pick Sharpe; if K-th pick Sharpe < 0, it should be dropped |
| Same-pair conflicting picks (MR vs LGBM on EUR/USD) | Default = net out; alternative configurable later |
| Naive sum-of-PnL inflates absolute PnL | Add `--position-size-fraction` flag; backtest comparison still uses raw sum |
| Wall-time blowup with 16 cells | Acceptable (~60 min); internal sweep keeps train shared |
| ρ measurement on per-bar series biased | Sample size control: only correlate bars where >= K picks exist |

---

## 11. PR breakdown

| PR | Scope | Size | Depends on |
|----|-------|------|-----------|
| **J-0** | This kickoff design memo | docs only | Phase 9.17b/I-2 (#212) MERGED |
| **J-1** | `compare_multipair_v14_topk.py` clone of v13 + Top-K SELECTOR + naive variant; new CLI `--top-k`, `--diversify-by-currency`; eval prints per-pick Sharpe | ~300 + tests | J-0 |
| **J-2** | 20-pair eval at K ∈ {1, 2, 3, 5} naive + diversified; closure memo with verdict | log + docs | J-1 |
| **J-3** *(conditional on J-2 GO)* | Production runtime wiring for Top-K SELECTOR | ~150 + tests | J-2 verdict |

**Timeline estimate**: J-0 + J-1 + J-2 = ~1.5 day total.

---

## 12. Out of scope

- Tier 3 (Sharpe-weighted picking, regime-aware K, risk-budget allocator) — defer to follow-up phase if Tier 1+2 produce GO/PARTIAL GO
- Position-size scaling for production (Phase 9.X-prod)
- Phase 9.11 (3+ yr robustness) — gated on STRETCH GO from this phase
- Option B (LSTM / model class change) — only if Phase 9.19 NO ADOPT

---

## 13. Open design questions (resolve before J-1 starts)

1. **Conflict resolution rule**: same-pair contradictory picks net out (default) vs drop lower-conf? Confirm before J-1.
2. **Currency family definition**: 6 currencies (USD/EUR/GBP/AUD/NZD/CHF/JPY/CAD = 8) — confirm the JPY/CAD inclusion. Default = derive from pair name split.
3. **Per-pick Sharpe threshold**: drop K-th pick from portfolio if its per-fold Sharpe < 0? Default = always include; defer pruning to closure-memo analysis.
4. **K sweep values**: {1, 2, 3, 5}? Or include {1, 2, 3, 4, 6}? Default = 4-value sweep; 5 is likely starvation point.
5. **Diversification rule strictness**: "no two picks share a currency" (strict) vs "no more than 2 USD-base picks" (loose)? Default = strict; covers the worst USD-cluster case.

If user does not respond to these defaults, J-1 proceeds with the values listed.

---

## 14. References

- `docs/design/phase9_17b_closure_memo.md` — per-trade EV is binding constraint, not trade volume; recommended Option C
- `docs/design/phase9_17_closure_memo.md` — strategies are orthogonal but SELECTOR slot competition kills the lift
- `docs/design/phase9_16_closure_memo.md` — pair expansion limited by 1-per-bar SELECTOR cap (foundational evidence)
- `scripts/compare_multipair_v13_ensemble.py:_eval_fold` — current SELECTOR implementation to clone for v14

---

## 15. Commit trail

```
<TBD>    PR #???  J-0 this kickoff design memo
<TBD>    PR #???  J-1 compare_multipair_v14_topk.py + Top-K SELECTOR + diversification
<TBD>    PR #???  J-2 20-pair eval + closure memo
<TBD>    PR #???  J-3 production runtime wiring (CONDITIONAL on J-2 verdict)
```
