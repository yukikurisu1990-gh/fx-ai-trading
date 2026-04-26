# Phase 9.X-C — LSTM (replacement + support modes) Kickoff Design Memo

**Status**: Draft — implementation pending
**Predecessor**: Phase 9.X-B closed PARTIAL GO+ for `+mtf` 2026-04-26 (Sharpe 0.174 K=3)
**Master tip at authorship**: `ff5f3be` (after Phase 9.X-A merged)
**Style anchor**: `docs/design/phase9_x_b_design_memo.md`

---

## 1. Why this phase

Phase 9.X-B PARTIAL GO+ for `+mtf` (Sharpe 0.174 / PnL 1.85×) confirmed **the features axis HAS a lever**. But `+mtf` alone tops out at Sharpe 0.174 — STRETCH GO (≥0.20) still requires another step. The remaining un-tested axis is **model class**.

Phase 9.X-C tests whether **sequence-aware modeling** (LSTM, GRU, or TFT) can extract additional signal from the same feature stream that LightGBM (tree-based, position-independent) cannot. Per Phase 9.X-B closure §8, prior probability for LSTM stacking with `+mtf` to break Sharpe ≥ 0.20: **~40%** (updated up from ~25% pre-9.X-B).

Per user direction: **consider both full-replacement AND support-style activation**, not just the replacement test.

---

## 2. Design overview — Mode A (replacement) vs Mode B (support, 4 variants)

### Mode A — Full LSTM replacement

```
Inputs: same 15 baseline + 6 mtf = 21 features per bar
        (sequence of last L bars, L ∈ {50, 100})
Model:  LSTM-3-class classifier (mirrors LightGBM target)
Output: replaces LightGBM signal entirely
```

**Pros**: simplest test of "is LSTM model class better than LGBM on the same features?"
**Cons**: discards LightGBM's proven tree-based feature interaction extraction
**Risk**: if LSTM is just-as-good but not better, the added complexity is unjustified

### Mode B — Support / stacking (LSTM augments, doesn't replace)

#### B-1 — Feature stacking (LSTM hidden state → LightGBM input)

```
Stage 1: LSTM trained as auxiliary task → 32-d hidden state per bar
Stage 2: LightGBM on (21 baseline features + 32 LSTM hidden state) = 53 features
Output: LightGBM prediction (uses LSTM as feature engineer)
```

**Pros**: preserves LightGBM strength, LSTM contributes summarized history
**Cons**: two-stage training, higher operational complexity
**Estimated cost**: ~7 days

#### B-2 — Output averaging (probability-weighted ensemble)

```
LSTM:     P_lstm = (P_sl, P_to, P_tp)   [softmax]
LightGBM: P_lgbm = (P_sl, P_to, P_tp)   [predict_proba]
Combined: P_final = α × P_lgbm + (1-α) × P_lstm
α: tunable; sweep over {0.3, 0.5, 0.7}
```

**Pros**: simplest support mode, interpretable, easy A/B
**Cons**: assumes both models are well-calibrated (Phase 9.18 found LightGBM's predict_proba ISN'T well-calibrated; LSTM may have same issue)
**Estimated cost**: ~5 days

#### B-3 — Gating / arbiter (LSTM as regime filter)

```
LSTM trained as regime classifier:
  output ∈ {favorable_long, favorable_short, choppy, dont_trade}
  labels derived from LightGBM's empirical hit rate per (regime, direction)

LightGBM signal fires only when LSTM regime is favorable AND aligns with LGBM direction
```

**Pros**: LSTM as a quality filter; preserves LGBM's signal generation
**Cons**: requires regime label engineering; LSTM regime may add filter at the wrong cadence
**Estimated cost**: ~6 days

#### B-4 — Specialization (LSTM long-horizon + LightGBM short-horizon)

```
LSTM: predicts longer-horizon direction (40-bar, 60-bar) — slow drift
LGBM: predicts short-horizon TB outcome (20-bar) — fast signal

Trade only when LSTM_long_direction == LGBM_short_direction
```

**Pros**: each model specializes in its strength; natural alignment-check filter
**Cons**: trade rate drops (only fires when both agree); throws away tradable disagreements
**Estimated cost**: ~6 days

---

## 3. Tier 1 / Tier 2 sequencing

### Tier 1 — implement first (this phase)

| Order | Mode | Reason |
|-------|------|--------|
| **M-1** | **Mode A** (replacement) | Cleanest test of LSTM model class vs LGBM on identical features. Definitive answer to "does LSTM provide additional value?" |
| **M-2** | **Mode B-2** (output averaging) | Cheapest support mode (reuses M-1 LSTM). Tests if LSTM contributes orthogonal probability mass even if A < baseline. |

If Mode A produces Sharpe ≥ baseline 0.174 (i.e. matches +mtf): proceed to Mode B-2 for ensemble lift.
If Mode A is decisively worse: skip B-2 (averaging won't rescue it), pivot to B-3/B-4 or data-source layer.

### Tier 2 — conditional on Tier 1 verdict

- **B-1 (feature stacking)**: most sophisticated; only justified if A or B-2 shows LSTM has signal value
- **B-3 (regime gate)**: only if B-2 averaging shows LSTM provides regime-style info but not signal-style
- **B-4 (specialization)**: only if neither A nor B-2 work — last attempt before Phase 9.X-D

### Tier 3 — DEFERRED

- Transformer / TFT: more expressive but data-hungry; ~7 days, only if LSTM Tier 1 is mixed
- Bayesian model averaging: complex, low expected lift, defer

---

## 4. Architecture choices

### 4.1 Model: LSTM vs GRU vs Transformer

| Model | Pros | Cons | Recommendation |
|-------|------|------|----------------|
| **LSTM** | Well-understood, stable training, decent default for time series | Slower training than GRU | ★ Default choice |
| GRU | Faster than LSTM, similar performance in practice | Less expressive for long sequences | Optional comparison |
| Transformer / TFT | More expressive, attention to specific timesteps | Data-hungry, harder to train | Tier 3 only |

Default: **2-layer LSTM, 64 hidden units**. Roughly 35k parameters — fits in memory, trains in minutes per fold on GPU.

### 4.2 Sequence length

Triple-barrier label horizon = 20 m5 bars (~100 min). LSTM input sequence:
- L=50 bars (~4h): captures 1-2 hours of history relevant to the 100-min trade
- L=100 bars (~8h): captures full session context
- Default: **L=100**, with sweep to L=50 if memory tight

### 4.3 Training target

To maintain apples-to-apples with LightGBM:
- **3-class TB label** (same as LGBM): {-1, 0, 1} encoded as one-hot
- Cross-entropy loss
- Output via softmax → P_sl, P_to, P_tp

Alternative: regression target (label_return per Phase 9.X-A). **Defer**: Phase 9.X-A showed regression worse than classification at this scale. Stick with classification.

### 4.4 Training infrastructure

- **PyTorch** (already in requirements? — check before M-1)
- **GPU recommended** (CUDA on dev machine if available; CPU fallback available but ~10× slower)
- Training time estimate: ~5-15 min per fold per pair on GPU; ~50-150 min on CPU
- 39 folds × 20 pairs × 1 model = 780 model trainings — must be automated efficiently
- **Per-fold caching**: train once per fold per pair (matches Phase 9.16 v9 pattern)

### 4.5 Walk-forward CV (matches Phase 9.16+)

Same 39-fold walk-forward, 90d train / 7d test windows. LSTM training:
- Train on the 90-day window (~26k m5 bars per pair)
- Validate on the next 7 days
- Retrain every 90 days (3 retrains over 39 folds)

Match LightGBM's retrain schedule for clean comparison.

---

## 5. Verdict gates

Mirror Phase 9.X-B PARTIAL GO+ frame, with the bar set higher (because Phase 9.X-C costs ~5 days, vs Phase 9.X-B's ~1 day):

| Gate | Rule |
|------|------|
| **GO** (must-ship) | Sharpe ≥ 0.18 AND PnL ≥ 1.10 × baseline AND DD%PnL ≤ 5% |
| **PARTIAL GO** | Sharpe ≥ 0.174 (Phase 9.X-B mtf benchmark) AND PnL ≥ Phase 9.X-B mtf PnL |
| **STRETCH GO** | Sharpe ≥ 0.20 — **unblocks Phase 9.11** |
| **NO ADOPT** | Sharpe < 0.174 (worse than Phase 9.X-B mtf) |

**Baseline**: Phase 9.X-B `+mtf` K=3 lgbm_only (Sharpe 0.174, PnL 15,118, DD%PnL 1.8%) — NOT Phase 9.16 v9. We must beat the current best to justify LSTM's complexity.

---

## 6. Theoretical Sharpe expectations

Phase 9.X-B closure §8 prior: ~40% probability of STRETCH GO when LSTM stacks with +mtf. Breakdown:

- **30% chance** Sharpe lifts to 0.18-0.22 (Mode A only or Mode A+B-2 stacked)
- **10% chance** STRETCH GO (Sharpe ≥ 0.20) clean — would unblock Phase 9.11
- **35% chance** Sharpe similar to mtf 0.174 (LSTM matches but doesn't exceed LGBM)
- **25% chance** Sharpe < mtf (LSTM underperforms; complexity not justified)

The optimistic case is real but not dominant. **The decision is whether 5 days of LSTM work is worth a 40% chance of unblocking Phase 9.11**. Given that Phase 9.11 (3+ year robustness validation) is the gate to actual production deployment, this is justified.

---

## 7. PR breakdown

| PR | Scope | Size | Depends on |
|----|-------|------|-----------|
| **M-0** (this PR) | Kickoff design memo | docs only | Phase 9.X-B closure (#218) |
| M-1 | LSTM training pipeline + `compare_multipair_v17_lstm.py` + Mode A eval (replacement) | ~500 lines + tests + GPU training | M-0 |
| M-2 | Mode B-2 output averaging (reuses M-1 LSTM) + 20-pair eval | ~150 lines + tests | M-1 |
| M-3 | Closure memo with verdict for Modes A + B-2 | docs | M-2 |
| **M-4** *(conditional on M-3 verdict)* | Tier 2: B-1 / B-3 / B-4 if needed | ~200-300 lines each | M-3 |

**Estimated timeline**:
- M-0: this PR (15 min)
- M-1: ~3 days (training pipeline is the bulk)
- M-2: ~1 day (builds on M-1)
- M-3: ~0.5 days (docs)
- Total Tier 1: **~4.5 days**
- Tier 2 (if needed): +2-4 days

---

## 8. Open design questions (defaults documented)

1. **PyTorch dep**: Is PyTorch already in `requirements.txt`? (Likely no — needs to be added for this phase. Default: add as optional dep.)
2. **GPU vs CPU training**: CPU is ~10× slower but always available. Default: try GPU first; fallback to CPU with reduced n_estimators-equivalent (epochs).
3. **Sequence length**: 100 bars default; sweep to 50 if performance budget tight.
4. **LSTM hyperparams**: 2-layer, 64 hidden, dropout 0.2, batch_size 256. Conservative defaults — can tune in M-1 if Mode A close-but-not-quite.
5. **Per-pair models vs unified**: per-pair (matches LGBM Phase 9.16 design). Unified per-instrument-class (G10) is Tier 3.
6. **Trade-PnL eval consistency**: same TB mid-bucket label PnL (1.5/1.0×ATR) as Phase 9.X-B. No change.
7. **Train-time data layout**: m5 OHLC + 21 features → tensor of shape (n_samples, 100, 21). Standard. Default.

---

## 9. Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| Training too slow on CPU | GPU first; if unavailable, scope down to 5 representative pairs for initial validation |
| LSTM overfits on 90-day train | Walk-forward CV controls this; early stopping on validation loss |
| LSTM matches but doesn't beat LGBM (NO ADOPT) | Mode B-2 averaging may still rescue if LSTM has orthogonal info; otherwise pivot to B-1/B-3 |
| Mode A worse than LGBM but B-2 better | Documents that LSTM has support value but not replacement value — directs Tier 2 work |
| GPU dep complicates production deployment | Production-side: Mode A would require GPU inference. Mode B-2 averaging can use cached LSTM predictions (offline batch inference). Document for J-5 production wiring. |

---

## 10. Honest disclosure (calibration prior)

The "trade-rate explosion + per-trade EV collapse" pattern was finally broken by `+mtf` in Phase 9.X-B. But that was at the FEATURE layer. LSTM tests the MODEL layer. Whether LSTM continues to extract value once features are saturated is uncertain.

**Bull case (~40% prior)**: LSTM's sequence-aware modeling captures temporal dependencies that LightGBM (position-independent splits) cannot. With `+mtf` features as input, LSTM may align signal generation with regime context to produce STRETCH GO.

**Bear case (~60% prior)**: The 21-feature space is information-saturated for the m5 / 20-bar TB problem. Even sequence-aware modeling can't extract more signal than already encoded. LSTM matches but doesn't exceed LGBM. Modes B-2/B-3/B-4 may add minor lift but not enough.

If bear case: pivot to Phase 9.X-D (data source layer — microstructure / orderbook).

---

## 11. Commit trail

```
<TBD>    PR #???  M-0 this kickoff design memo
<TBD>    PR #???  M-1 LSTM training + Mode A eval
<TBD>    PR #???  M-2 Mode B-2 output averaging
<TBD>    PR #???  M-3 closure memo
<TBD>    PR #???  M-4 Tier 2 modes (CONDITIONAL)
```
