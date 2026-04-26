# Phase 9.X-D — Cross-asset / DXY features Kickoff Design Memo

**Status**: Draft — implementation pending
**Predecessor**: Phase 9.X-C/M-1 closed NO ADOPT 2026-04-26 (LSTM Sharpe 0.061 << mtf 0.174)
**Master tip at authorship**: `1afd2dd` (after Phase 9.X-B closure merged)
**Style anchor**: `docs/design/phase9_x_b_design_memo.md`

---

## 1. Why this phase

Phase 9.13–9.X-C/M-1 confirmed the bottleneck is at the **data source layer**:
- 5 phases of "extraction tricks" on the same 21-feature space all hit Sharpe 0.143-0.177 ceiling (NO ADOPT pattern)
- The single successful lever (Phase 9.X-B mtf, Sharpe 0.174 / PnL 1.85×) came from **adding new time horizons** to the same OHLC stream
- LSTM (Phase 9.X-C/M-1) confirmed model class isn't the lever

The next axis is **expanding the input data set** with information NOT in the 20-pair OHLC feed:
- **A — Cross-asset / DXY** (THIS PHASE, ~3 days, no new data source)
- B — Economic calendar / event-distance (~2-3 days, OANDA labs API)
- C — Orderbook microstructure (~5+ days, requires non-OANDA data)

Phase 9.X-D starts with **A** because it's the cheapest decisive test that requires zero new data sources.

---

## 2. Core hypothesis

**H-1 (USD-cluster signal)**: The 20-pair feed contains 7 USD-quote pairs (EUR/USD, GBP/USD, AUD/USD, NZD/USD, USD/CHF, USD/CAD, USD/JPY). A trade-weighted average of these — a DXY-equivalent — captures **broad USD strength/weakness** that no single-pair feature reveals. Adding DXY momentum features as inputs to the per-pair LightGBM model may filter trades by macro USD regime.

**H-2 (cross-pair correlation drift)**: When DXY trends strongly (e.g., during Fed cycles), per-pair features (RSI, MACD, BB) misfire because individual pair moves are dominated by USD-side flows. DXY-aware features let the model condition signals on macro context.

**H-3 (orthogonality vs mtf)**: mtf adds INTRA-pair time horizons (4h/daily/weekly). DXY adds CROSS-pair USD aggregate. They should be largely orthogonal information axes. If both individually help, combined (mtf + DXY) may stack.

---

## 3. DXY computation (no new data dependency)

We compute a DXY-equivalent from existing 20-pair OHLC feeds. Standard DXY weights (Fed):

```
EUR/USD: 57.6%
USD/JPY: 13.6%
GBP/USD: 11.9%
USD/CAD:  9.1%
USD/SEK:  4.2%   ← NOT in our universe; redistribute
USD/CHF:  3.6%
```

Adjusted weights (renormalize without SEK):

```
EUR/USD: 60.1%
USD/JPY: 14.2%
GBP/USD: 12.4%
USD/CAD:  9.5%
USD/CHF:  3.8%
```

DXY value at time t:
```
DXY(t) = 50.14348112 × ∏ (rate_i(t) / rate_i(0))^weight_i

where:
  EUR/USD weight is NEGATIVE (DXY rises when EUR/USD falls)
  USD/JPY, USD/CAD, USD/CHF weights are POSITIVE
  GBP/USD weight is NEGATIVE
```

In log-return form (for momentum features):
```
log_DXY_return(t, lag) = -0.601 × log_eur_usd_return - 0.124 × log_gbp_usd_return + 0.142 × log_usd_jpy_return + 0.095 × log_usd_cad_return + 0.038 × log_usd_chf_return
```

This is a linear combination that any pair's existing close-to-close returns can compute.

---

## 4. Proposed cross-asset features (Group: dxy)

| Feature | Description |
|---------|-------------|
| `dxy_return_5` | DXY log-return over 5 m5 bars (~25 min) |
| `dxy_return_20` | DXY log-return over 20 m5 bars (~100 min) |
| `dxy_return_60` | DXY log-return over 60 m5 bars (~5h) |
| `dxy_volatility_20` | Rolling stdev of DXY 1-bar returns (20 bars) |
| `dxy_z_score_50` | DXY level z-score over rolling 50-bar window |
| `dxy_ma_cross_short` | Sign of (DXY 5-bar MA − 20-bar MA) |
| `dxy_correlation_pair_20` | Rolling 20-bar correlation between this pair's return and DXY return |
| `dxy_pair_alignment` | Categorical: +1 if pair is currently moving with DXY trend, −1 if against |

Total: 8 new features per pair. All computable from existing feed (no new data).

The `dxy_correlation_pair_20` and `dxy_pair_alignment` features are **per-pair contextual** — each pair has different relation to DXY (EUR/USD is anti-correlated, USD/JPY is correlated, AUD/JPY is partial).

---

## 5. Sweep design

5 cells, single eval (load + features + train ONCE, eval per cell):

```
Cell                           Features added vs v9 baseline
baseline                       none (Phase 9.16 production)
+mtf                           Phase 9.X-B mtf (benchmark to beat: Sharpe 0.174)
+dxy                           Phase 9.X-D dxy alone
+dxy+mtf                       both groups (orthogonal stacking test)
```

4 evals total. Each ~30-45 min wall time. Run 2-parallel for ~60-90 min total.

The +dxy+mtf cell is the key STRETCH GO test: if both add independent lift, combined Sharpe could clear 0.20.

---

## 6. Verdict gates

Mirror Phase 9.X-C frame (raised vs Phase 9.X-B mtf benchmark):

| Gate | Rule |
|------|------|
| **GO** | Sharpe ≥ 0.18 AND PnL ≥ 1.10 × baseline AND DD%PnL ≤ 5% |
| **PARTIAL GO** | Sharpe ≥ 0.174 (Phase 9.X-B mtf benchmark) |
| **STRETCH GO** | Sharpe ≥ 0.20 (unblocks Phase 9.11) |
| **NO ADOPT** | Sharpe < 0.174 |

Baseline = Phase 9.16 production default (Sharpe 0.160, PnL 8,157, DD%PnL 2.5%).

**Best case**: +dxy alone matches mtf (0.174); +dxy+mtf stacks to ≥ 0.20 STRETCH GO.
**Realistic case (per Phase 9.X-C closure §10)**: ~50% NO ADOPT prior; data axis is the next plausible lever, but extraction-tricks pattern may have generalised.

---

## 7. Implementation cost

| PR | Scope | Size |
|----|-------|------|
| **N-0** (this PR) | Kickoff design memo | docs only |
| N-1 | `compare_multipair_v18_crossasset.py` (clone v16) + DXY computation + dxy feature group + tests | ~250 lines + tests |
| N-2 | 4-eval 20-pair sweep + closure memo with verdict | log + docs |

**Estimated timeline**: ~3 days total (per Phase 9.X-C closure §6 estimate).

---

## 8. Open design questions (defaults documented)

1. **DXY weights**: standard Fed weights renormalised (no SEK). Default. Could test trade-weighted vs equal-weighted variant.
2. **DXY z-score window**: 50 m5 bars (~4h). Default. Aligns with bb_pct_b window.
3. **Correlation window**: 20 bars matches existing rolling features.
4. **Per-pair vs basket DXY**: same DXY for all pairs (basket interpretation). Default. Per-pair-conditioned could be Tier 2.
5. **JPY pair handling**: USD/JPY is a basket constituent; dxy_correlation feature for USD/JPY may be near-1.0 (degenerate). Document and accept.

---

## 9. Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| DXY components form linear combination of existing features → multicollinearity | Test +dxy alone first; combine only if +dxy alone has independent lift |
| `dxy_correlation_pair_20` is noisy (20-bar Pearson on returns) | Match the calibration prior — if noisy, will surface as no lift; cheap to discard |
| USD/JPY trains on basically-DXY features (degenerate) | Eval per-pair-share output will reveal if USD/JPY behaves anomalously; can downweight |
| +dxy+mtf shows negative interaction (Phase 9.X-B +all pattern) | Document. If individual lifts but combined doesn't, recommend +dxy alone or +mtf alone |

---

## 10. Calibration prior

Per Phase 9.X-C/M-1 closure §10:
- ~50% NO ADOPT (extraction-tricks pattern may generalise to data axis)
- ~30% +dxy alone gives Sharpe 0.165-0.180 (matches/slightly beats mtf)
- ~15% +dxy+mtf stacks to STRETCH GO (≥ 0.20)
- ~5% +dxy is decisive on its own (≥ 0.18)

The ~15% STRETCH GO chance is what justifies the 3-day cost. If it materialises, Phase 9.11 (3+ yr robustness) is unblocked.

---

## 11. Commit trail

```
<TBD>    PR #???  N-0 this kickoff design memo
<TBD>    PR #???  N-1 compare_multipair_v18_crossasset.py + DXY features + 20-pair eval
<TBD>    PR #???  N-2 closure memo with verdict
```

(N-1 and N-2 may be bundled into a single overnight PR.)
