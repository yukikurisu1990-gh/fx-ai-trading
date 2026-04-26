# Phase 9.X-A — Alternative labels: return-based regression Kickoff Design Memo

**Status**: Draft — implementation pending
**Predecessor**: Phase 9.19 closed PARTIAL GO 2026-04-26 (modest +25% PnL via Top-K but Sharpe lift didn't materialize)
**Master tip at authorship**: `64d04bc` (after Phase 9.19/J-1 merged)
**Style anchor**: `docs/design/phase9_19_design_memo.md`

---

## 1. Why this phase

Phase 9.13–9.19 collectively prove that **every alpha-engineering lever on (LightGBM + 15 TA features + triple-barrier label) hits a Sharpe ceiling of 0.143–0.177**. The Phase 9.19 closure §6 framed the structural conclusion: "the model class itself is the ceiling."

Option B (model-class change) has three candidate axes:
- **A — Alternative labels** (THIS PHASE, ~1-2 days, cheapest)
- **B — Alternative features** (~3 days)
- **C — Alternative model class — LSTM/Transformer** (~5 days)

Phase 9.X-A starts with **A** because it isolates the question: **is the ceiling label-dependent (training target signal-to-noise) or model-dependent (LightGBM's calibration)?**

If alt label breaks the ceiling → answer is "labels were the issue" → solve cheaply.
If alt label fails → calibration ceiling is in the LGBM × 15-features pair → pivot to B or C.

---

## 2. Core hypothesis

**H-1 (target signal-to-noise)**: Triple-barrier classification labels in {-1, 0, 1} discard magnitude information. Training on **raw realized return** (regression target) preserves it, potentially producing a model whose confidence (= predicted return magnitude) correlates better with actual hit rate than the TB classifier's predict_proba does.

The Phase 9.18 closure §8 found: "model confidence ≥ 0.65 hits at 54.1% vs 54.5% overall" — LGBM classifier's confidence is **NOT** a hit-rate predictor. If the regressor's predicted-return-magnitude IS a hit-rate predictor, that's evidence the label was the problem.

**H-2 (apples-to-apples PnL)**: PnL must be computed via the same triple-barrier mechanism as Phase 9.16/9.19 baselines so the comparison is clean. Only the *signal-generation* layer changes (what makes a trade fire); the *outcome-measurement* layer stays the same.

---

## 3. What changes vs Phase 9.19 v14

```
Component               Phase 9.19 v14                  Phase 9.X-A v15
-----------------------------------------------------------------------
Training label          label_tb (∈ {-1, 0, 1})         label_return (∈ R)
Model                   LGBMClassifier (3-class)        LGBMRegressor
Output                  predict_proba: (P_sl, P_to, P_tp)  predict: y_hat (∈ R)
Signal rule             argmax + threshold on prob      sign(y_hat) + threshold on |y_hat|
Confidence              max(P_tp, P_sl)                  |y_hat| / scale
PnL eval                triple-barrier label_tb         (same — apples to apples)
SELECTOR                argmax / Top-K                   (same)
```

**No other changes.** Same 20 pairs, same 39 folds, same features, same TB PnL. Only the model + signal layer.

---

## 4. Signal generation from regression output

```python
# Training:
y_train = train_df['label_return']  # raw return at horizon
model = lgb.LGBMRegressor(...).fit(X_train, y_train)

# Eval per bar:
y_hat = model.predict(X_test)   # predicted return for each bar
abs_y = np.abs(y_hat)

# Threshold: predicted-return magnitude must exceed an adaptive threshold
# computed from training-set distribution.
abs_y_train = np.abs(model.predict(X_train))
thresh = np.quantile(abs_y_train, 0.50)  # median magnitude as floor

sig = np.where(y_hat >= thresh, 1, np.where(y_hat <= -thresh, -1, 0))
confidence = np.minimum(abs_y / (2 * thresh), 1.0)  # normalize to [0, 1]
```

**Threshold choice**: 50th percentile of absolute-magnitude predictions. This produces ~50% no-trade rate, comparable to LGBM classifier's behavior at threshold=0.50.

---

## 5. Verdict gates

Mirror Phase 9.19 PnL-priority frame:

| Gate | Rule |
|------|------|
| **GO** | Sharpe ≥ 0.18 AND PnL ≥ 1.10 × baseline AND DD%PnL ≤ 5% |
| **PARTIAL GO** | Sharpe ≥ baseline AND PnL ≥ baseline AND DD%PnL ≤ 5% |
| **STRETCH GO** | Sharpe ≥ 0.20 (clears Phase 9.11 robustness gate) |
| **NO ADOPT** | Sharpe < baseline OR PnL < baseline OR DD%PnL > 5% |

Baseline = Phase 9.16 production default (20-pair v9 spread bundle, Sharpe 0.160, PnL 8,157, DD%PnL 2.5%).

---

## 6. PR breakdown

| PR | Scope | Size |
|----|-------|------|
| **K-0** (this PR) | Kickoff design memo | docs |
| K-1 | `compare_multipair_v15_regression.py` + `label_return` generator + LGBMRegressor wiring + 20-pair eval log | ~150 lines diff vs v14 |
| K-2 | Closure memo with verdict | docs + log |
| K-3 *(conditional on GO)* | Production runtime wiring (model_type config) | ~100 lines |

K-1 and K-2 are deliberately bundled into a single overnight PR because the implementation is small (model class swap + label change) and the eval is the binding result.

---

## 7. Open design questions (defaults documented)

1. **Return horizon**: same 20-bar horizon as TB? (Default YES — keep apples-to-apples.)
2. **Threshold percentile**: 50th vs 60th vs 70th of training |y_hat|? (Default 50th — keep trade rate comparable to baseline.)
3. **Cross-pair feature inclusion**: keep xp_* features (Phase 9.16 spread bundle)? (Default YES.)
4. **Multi-target regression**: predict bid/ask returns separately? (Default NO — keep single close-to-close return target for simplicity.)

---

## 8. Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| Regression target is noisier than TB labels (no clipping) | Use median absolute prediction as threshold to filter low-confidence noise |
| LGBMRegressor objective default (L2) may not be ideal for asymmetric returns | Default L2 first; if NO ADOPT, retry with quantile loss |
| Predicted return doesn't translate to TB hit rate | This IS the test — if it doesn't, label class isn't the lever |
| Threshold percentile creates self-reference (uses training-fold prediction) | Compute threshold per-fold from training set only; no leakage |

---

## 9. Theoretical Sharpe expectation

Honestly, this is a long-shot. The Phase 9.18-9.19 finding was that LightGBM's calibration is structurally limited; switching from classification to regression keeps the same model class. Expected outcomes:

- **Most likely (60% probability)**: Sharpe similar to baseline (0.13-0.18). Marginal lift if any. Confirms label class isn't the lever; pivot to features (B) or model class (C).
- **Optimistic (25%)**: Sharpe 0.18-0.22. Some breakthrough; explore further within label-tuning.
- **Pessimistic (15%)**: Regression target is noisier than expected; Sharpe < 0.10. Confirms classification was the right call; pivot.

The eval is the arbiter. ~30-45 min wall time.

---

## 10. Commit trail

```
<TBD>    PR #???  K-0 this kickoff design memo
<TBD>    PR #???  K-1 compare_multipair_v15_regression.py + 20-pair eval log + closure memo
```

(Bundled K-1 + K-2 into one overnight PR.)
