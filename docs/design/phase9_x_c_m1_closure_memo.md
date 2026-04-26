# Phase 9.X-C/M-1 — LSTM Mode A (full replacement) Closure Memo

**Status**: Closed — **NO ADOPT** (Sharpe 0.061 << Phase 9.X-B mtf benchmark 0.174)
**Master tip at authorship**: `ff5f3be` (after Phase 9.X-A merged)
**Predecessor**: Phase 9.X-B closed PARTIAL GO+ for `+mtf` 2026-04-26 (Sharpe 0.174)
**Related**: `docs/design/phase9_x_c_design_memo.md`, `docs/design/phase9_x_b_closure_memo.md`

---

## 1. What this phase set out to do

Phase 9.X-B PARTIAL GO+ for `+mtf` (Sharpe 0.174) confirmed the FEATURES axis has a lever. M-1 tests whether the **MODEL CLASS axis** (LSTM vs LightGBM on identical features) provides additional signal.

Mode A — full replacement: LSTM-3-class output replaces LightGBM's `predict_proba` in the lgbm strategy slot. SELECTOR rule and rule-based MR/BO strategies unchanged. Same 21 features (15 baseline + 6 mtf), same TB labels, same 39-fold walk-forward — only the model differs.

This is the **clean apples-to-apples test**: does sequence-aware modeling extract more signal than tree-based splits on the same input?

---

## 2. What shipped

| PR | Scope | Result |
|----|-------|--------|
| (this PR #221) | M-1 — `compare_multipair_v17_lstm.py` + LSTM training pipeline + 20-pair Mode A eval + this closure memo | **NO ADOPT** |

Implementation highlights:
- 2-layer LSTM, 64 hidden units, dropout 0.2 (~35k params)
- PyTorch 2.5.1+cu121 on RTX 3060 Ti
- Inverse-frequency class weights (counters ~84% timeout label imbalance)
- Sequence length 100 m5 bars, 10 epochs, batch 256
- Per-fold retrain at the same cadence as LightGBM (3 retrains × 39 folds)

---

## 3. Results

### 3.1 LSTM Mode A 20-pair sweep (K∈{1, 2, 3, 5} × 2 cells)

```
Cell              K   Sharpe   PnL(pip)   MaxDD   DD%PnL   Trades
lgbm_only         1   0.050    6,126      189.0   3.1%     95,945
lgbm_only         2   0.057    8,753      166.8   1.9%     95,945
lgbm_only         3   0.060    10,116     187.1   1.8%     95,945
lgbm_only         5   0.061    10,538     217.3   2.1%     95,945
lgbm+mr+bo        1   0.031    7,513      168.9   2.2%     237,913
lgbm+mr+bo        2   0.043    14,933     179.1   1.2%     237,913
lgbm+mr+bo        3   0.051    22,257     216.6   1.0%     237,913
lgbm+mr+bo        5   0.062    34,242     201.5   0.6%     237,913
```

### 3.2 Comparison vs benchmarks

| Variant | Best Sharpe | Best PnL | Trades | Per-trade EV |
|---------|------------|----------|--------|---------------|
| Phase 9.16 baseline (v9, no mtf) | 0.160 | 8,157 (1.00×) | 12,461 | 0.654 pip/trade |
| Phase 9.X-B `+mtf` K=3 ★ benchmark | **0.174** | **15,118 (1.85×)** | 16,958 | 0.892 pip/trade |
| **Phase 9.X-C M-1 LSTM K=5** | **0.061** | 10,538 (1.72×) | **95,945** | **0.110 pip/trade** |

**LSTM Mode A is decisively worse than both baselines.** Sharpe 0.061 vs benchmark 0.174 (−0.113); per-trade EV collapsed to 0.110 pip (8× drop vs baseline 0.654).

### 3.3 Per-rank Sharpe diagnostic (LSTM K=3 lgbm_only)

```
Rank 1     0.045
Rank 2     0.054
Rank 3     0.060
```

Per-rank Sharpe is uniformly low (0.045-0.060). Compare to Phase 9.X-B mtf K=3:
- Rank 1: 0.176, Rank 2: 0.168 — both individual picks well above any LSTM rank.

**Notable**: in LSTM Mode A, rank-3 has higher Sharpe than rank-1 (0.060 > 0.045). This is anomalous — typically rank-1 should be the highest-confidence pick. This suggests LSTM's confidence ranking is poorly calibrated.

---

## 4. Verdict — NO ADOPT

| Gate | Best LSTM result | Pass? |
|------|------------------|-------|
| GO (Sharpe ≥ 0.18) | 0.061 | ✗ |
| **PARTIAL GO** (Sharpe ≥ 0.174 mtf benchmark) | 0.061 | **✗** |
| STRETCH GO (Sharpe ≥ 0.20) | 0.061 | ✗ |
| **NO ADOPT** (Sharpe < 0.174) | 0.061 | **✓ TRIGGERED** |

**Verdict: NO ADOPT.** LSTM Mode A is decisively worse than Phase 9.X-B mtf alone.

This is the **bear case (~25% prior)** outcome from M-0 §10 calibration. The hypothesis "sequence-aware modeling extracts more signal from same features" is **falsified** at this scale and configuration.

---

## 5. Why LSTM Mode A failed — same pattern as 9.17/9.17b/9.19/9.X-A

LSTM produced **95,945 trades** vs LightGBM baseline 12,461 (7.7× more) but per-trade EV collapsed from 0.654 pip to 0.110 pip (84% drop). This is the **same "trade-rate explosion + per-trade EV collapse" pattern** seen in:

- Phase 9.17 (multi-strategy ensemble): trade rate 15× → Sharpe collapsed
- Phase 9.17b (threshold filter): same pattern across thresholds
- Phase 9.19 (Top-K SELECTOR): partial mitigation via diversification
- Phase 9.X-A (regression labels): same pattern, label class wasn't the lever
- **Phase 9.X-C M-1 (LSTM Mode A): same pattern, model class isn't the lever (at this scale)**

5 phases now confirm: when a mechanism produces MORE trades from the same feature space, Sharpe collapses regardless of mechanism.

The class-weighted cross-entropy loss made the LSTM over-predict TP/SL classes, generating signals on too many bars. Without class weighting (preliminary smoke), the LSTM produced 0 trades (always predicted timeout). The "sweet spot" calibration that produces a useful trade rate AT high quality was not reached at default settings.

### 5.1 What the per-rank pattern shows

`Rank 1 < Rank 3` Sharpe (0.045 < 0.060) means the SELECTOR is picking poorly when given LSTM confidence. The LSTM's softmax probabilities don't reliably rank trade quality. This is the **same calibration problem** Phase 9.18 found for LightGBM (confidence ≥ 0.65 hit at 54.1% vs 54.5% overall) — but worse in LSTM because of the class-weighted loss distortion.

---

## 6. Implications for Phase 9.X-C Tier 1 plan

Per the M-0 design memo §3 sequencing:

> If Mode A produces Sharpe ≥ baseline 0.174: proceed to Mode B-2 for ensemble lift.
> **If Mode A is decisively worse: skip B-2 (averaging won't rescue it), pivot to B-3/B-4 or data-source layer.**

LSTM Sharpe 0.061 is **decisively worse**. Mode B-2 output averaging at 50/50 weight would yield ~(0.174 + 0.061)/2 = 0.118 — well below mtf alone (0.174). **B-2 is NOT viable** as a standalone follow-up.

### 6.1 Tier 2 candidates re-evaluated

| Mode | Original cost | Adjusted recommendation |
|------|--------------|------------------------|
| **B-1 Feature stacking** | 7 days | DEFER — relies on LSTM hidden state having signal value; M-1 evidence suggests LSTM extracts no orthogonal info |
| **B-3 Gating / arbiter** | 6 days | POSSIBLE — LSTM as regime classifier may not need to be accurate, just informative; different task than Mode A |
| **B-4 Specialization** | 6 days | POSSIBLE — LSTM at LONG horizon (40-60 bars) may extract slow-moving signal LSTM-100 missed |

### 6.2 Recommended pivot: Phase 9.X-D (data source)

The cumulative evidence (now 5 phases) suggests the bottleneck is at the **data source layer**, not at the model/feature/label/SELECTOR layer. Same OHLC feed × variations of (model, label, features, SELECTOR) all hit the same Sharpe ceiling 0.143-0.177, with the only meaningful breakout (mtf at 0.174) coming from **adding new time horizons** to the same OHLC stream.

To break Sharpe ≥ 0.20, we likely need:
- **Microstructure / orderbook data** (L2 imbalance, trade flow, Kyle's lambda) — not in OANDA
- **Calendar / news data** (event-time, FOMC/NFP distance)
- **Cross-asset data** (DXY momentum, equity-FX correlation, real interest rate differentials)

These are Phase 9.X-D candidates. None require model architecture change; they extend the input data set.

---

## 7. Cumulative path through Phase 9.10–9.X-C/M-1

```
v9-20p (Phase 9.16):                  Sharpe 0.160  ★ production default
v14 lgbm_only K=2 naive (9.19):       Sharpe 0.165  ★ PARTIAL GO
v15 regression pct=50 K=5 (9.X-A):    Sharpe 0.092  ✗ NO ADOPT (label class not lever)
v16 +mtf K=3 lgbm_only (9.X-B):       Sharpe 0.174  ★ PARTIAL GO+
v17 LSTM Mode A K=5 (this):           Sharpe 0.061  ✗ NO ADOPT (model class not lever)
```

**The progression confirms: features matter (mtf +0.014), model class doesn't (LSTM −0.113).**

---

## 8. What's next — recommended sequencing

1. **Phase 9.X-D — Data source expansion (recommended)**
   - Cheapest decisive test: DXY momentum + cross-asset features (~3 days)
   - Or: economic calendar / event-distance features (~2-3 days)
   - These don't require model architecture changes; they widen the input set
   - Higher ceiling potential than Tier 2 LSTM modes

2. **Phase 9.X-C/M-2 (B-3 gating) — Optional Tier 2**
   - Different mechanism: LSTM as regime classifier rather than signal generator
   - May work where Mode A failed; requires regime label engineering
   - ~6 days; lower priority than 9.X-D given M-1 evidence

3. **Phase 9.X-C/M-3 (B-4 specialization)**
   - LSTM at long horizon (40-60 bars) + LightGBM at short (20)
   - Tests whether model-class matters at DIFFERENT task scales
   - ~6 days; deprioritized

**Recommendation**: pivot to Phase 9.X-D first. Tier 2 LSTM modes are deprioritized given M-1's clear NO ADOPT.

---

## 9. Notes for future-me

1. **LSTM at this scale doesn't beat LightGBM on identical features.** 21-feature × 100-bar sequence is information-saturated for the m5 / 20-bar TB problem. The temporal dependency LSTM can extract from these aggregated features doesn't add signal beyond what LightGBM splits already capture.

2. **Class weighting cuts both ways.** Without it, LSTM converges to "always timeout" → 0 trades. With inverse-frequency weights, model over-predicts TP/SL → 7.7× too many trades. The narrow band where LSTM matches LightGBM's calibration was not reached at default 10 epochs.

3. **The "trade-rate explosion + EV collapse" pattern is now confirmed in 5 phases**: 9.17, 9.17b, 9.19, 9.X-A, **9.X-C/M-1**. This is structural. Any mechanism that extracts more signals from the existing 21-feature space dilutes per-trade quality. The only successful lever (Phase 9.X-B mtf) **expanded the feature set with new time horizons**, not increased extraction from existing features.

4. **The next axis is data source.** Phase 9.X-D (cross-asset, orderbook, calendar) is the natural pivot. Same models, same labels, broader input data. This is the textbook approach when feature engineering on existing data is exhausted.

5. **Tier 2 LSTM modes (B-3, B-4) are not entirely ruled out** but are lower priority than 9.X-D. B-3 (regime gate) has the best theoretical case because it doesn't require LSTM to be accurate, just informative — but the implementation cost (~6 days) doesn't pay off if 9.X-D produces a clean Sharpe lift first.

6. **Per-rank Sharpe inversion** (rank 3 > rank 1) is a strong signal that the model's confidence ordering is broken. Future ML attempts should explicitly verify the predict_proba calibration before committing to a full eval.

7. **PyTorch + CUDA setup is confirmed working.** RTX 3060 Ti / 8GB / CUDA 12.1 → ~50 min for 20-pair × 39-fold × 3 retrain × 10 epochs LSTM training + inference. Reusable for future ML phases.

---

## 10. Commit trail

```
8b853fe  PR #221  M-1 v17 LSTM Mode A implementation + smoke
<TBD>    PR #221  M-1 closure memo + 20-pair eval log (this addition)
```
