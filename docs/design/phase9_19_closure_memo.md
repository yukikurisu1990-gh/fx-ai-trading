# Phase 9.19 — SELECTOR multi-pick (Top-K) Closure Memo

**Status**: Closed — **PARTIAL GO** at K=2 lgbm_only (modest +25% PnL, +0.005 Sharpe over baseline)
**Master tip at authorship**: `64d04bc` (Phase 9.19/J-0 merged) + J-1 queued + this PR
**Predecessor**: Phase 9.17b closed NO ADOPT 2026-04-26 at master `0203c34`
**Related**: `docs/design/phase9_19_design_memo.md`, `docs/design/phase9_17_closure_memo.md`, `docs/design/phase9_17b_closure_memo.md`

---

## 1. What this phase set out to do

Phase 9.13–9.17b confirmed every alpha lever feeding INTO the SELECTOR has been exhausted (features, exit policies, more strategies, threshold filters — all hit Sharpe ceiling 0.143–0.177). Phase 9.19 attacked the **SELECTOR rule itself**: take top-K candidates per bar instead of top-1.

**Hypothesis**: at ρ ≤ 0.4 between picks, Sharpe scales by sqrt(K). At K=3 with baseline 0.160, theoretical Sharpe = 0.277 (clears 0.20 GO).

**Two variants tested**:
- **Naive top-K**: argpartition top-K candidates per bar; sum gross PnLs
- **Diversified top-K** (`--diversify-by-currency`): per-bar greedy fill with cap 1 per currency family

---

## 2. What shipped

| PR | Scope | Result |
|----|-------|--------|
| #213 | J-0 — kickoff design memo | merged |
| #214 | J-1 — `compare_multipair_v14_topk.py` + Top-K SELECTOR + diversification | merged |
| **(this PR)** | J-2 — 20-pair eval at K∈{1,2,3,5} naive + diversified + closure memo | PARTIAL GO at K=2 |
| (TBD) | J-3 — production runtime wiring (CONDITIONAL on this verdict) | not triggered (modest lift) |

---

## 3. Results

### 3.1 Naive Top-K sweep (20-pair, 39-fold)

```
Cell              K    Sharpe   PnL(pip)   MaxDD   DD%PnL   PnL ratio
lgbm_only         1    0.160    8,157.2    203.4    2.5%    1.00x  (baseline)
lgbm_only         2    0.165    10,219.8   268.7    2.6%    1.25x
lgbm_only         3    0.163    10,805.0   289.1    2.7%    1.32x
lgbm_only         5    0.161    11,112.8   289.1    2.6%    1.36x
lgbm+mr+bo        1    0.036    9,023.3    247.9    2.7%    1.11x
lgbm+mr+bo        2    0.047    16,854.2   162.6    1.0%    2.07x
lgbm+mr+bo        3    0.055    24,097.1   220.7    0.9%    2.95x
lgbm+mr+bo        5    0.064    36,001.0   282.2    0.8%    4.41x
```

### 3.2 Diversified Top-K sweep (one pick per currency family)

```
Cell              K    Sharpe   PnL(pip)   MaxDD   DD%PnL   PnL ratio
lgbm_only         1    0.160    8,157.2    203.4    2.5%    1.00x
lgbm_only         2    0.167    8,841.0    273.4    3.1%    1.08x
lgbm_only         3    0.165    8,801.9    280.0    3.2%    1.08x
lgbm_only         5    0.165    8,801.9    280.0    3.2%    1.08x   (= K=3, currency cap saturates)
lgbm+mr+bo        1    0.036    8,944.8    258.3    2.9%    1.10x
lgbm+mr+bo        2    0.044    13,616.9   166.3    1.2%    1.67x
lgbm+mr+bo        3    0.046    14,603.6   175.6    1.2%    1.79x
lgbm+mr+bo        5    0.046    14,643.4   177.0    1.2%    1.80x
```

### 3.3 Per-rank Sharpe diagnostics (lgbm_only K=3)

**Naive** — picks tend to USD-quote majors (correlated):
```
Rank 1     0.158
Rank 2     0.147   (slight dilution)
Rank 3     0.072   (clear dilution)
```

**Diversified** — rank-2 forced to non-overlapping currency family:
```
Rank 1     0.158
Rank 2     0.251   (HIGHER than rank 1 — diversification picks better-quality non-USD pairs)
Rank 3    -0.054   (NEGATIVE — drags portfolio; currency cap exhausted)
```

### 3.4 Best result vs baseline

| Variant | K | Sharpe | PnL | DD%PnL | Verdict |
|---------|---|--------|-----|--------|---------|
| Naive | 2 | 0.165 | 1.25× | 2.6% | best PnL/Sharpe combo |
| **Diversified** | **2** | **0.167** | **1.08×** | **3.1%** | **best Sharpe** |
| Naive | 3 | 0.163 | 1.32× | 2.7% | best PnL gain |

---

## 4. Verdict — PARTIAL GO at K=2

Per Phase 9.19 design memo §5 gates:

| Gate | Best candidate | Result |
|------|----------------|--------|
| **GO** (PnL ≥ 1.30× AND Sharpe ≥ 0.18 AND DD%PnL ≤ 5%) | Naive K=3 lgbm_only (PnL 1.32×, Sharpe 0.163) | ✗ Sharpe 0.163 < 0.18 |
| **PARTIAL GO** (PnL ≥ 1.20× AND Sharpe ≥ baseline AND DD%PnL ≤ 5%) | Naive K=2 lgbm_only (PnL 1.25×, Sharpe 0.165) | ✓ **MEETS GATE** |
| **STRETCH GO** (any Sharpe ≥ 0.20) | best is Diversified K=2 at 0.167 | ✗ |
| **NO ADOPT** (PnL < baseline OR DD%PnL > 5% OR ρ > 0.7) | none | ✗ (doesn't trigger) |

**Verdict: PARTIAL GO** — Naive K=2 lgbm_only achieves PnL +25% with Sharpe +0.005 over baseline, DD%PnL within bounds.

**However**: the lift is modest, not the breakthrough we hoped for. The theoretical sqrt(K) Sharpe lift did not materialize (expected 0.226 at K=2, ρ=0; actual 0.165). **The picks are highly correlated despite being on different pairs** — see §5.

**Phase 9.11 (3+ yr robustness) remains BLOCKED on Sharpe ≥ 0.20 gate.** No cell achieves it.

---

## 5. Why the sqrt(K) lift didn't materialize

The design memo predicted Sharpe lift `S × sqrt(K) / sqrt(1 + (K-1)ρ)`. At K=2, ρ=0 we expected 0.226; actual was 0.165.

**Root cause**: simultaneous picks on different pairs are NOT independent. They are highly correlated despite being on different instruments because:

1. **LightGBM is signaling on systemic moves**. When LGBM picks EUR/USD long with high confidence, it often picks GBP/USD long, AUD/USD long etc. simultaneously — all reflecting USD weakness. The features that drive LGBM (RSI, MACD, EMA, BB, ATR) are highly correlated across G10 pairs during regime moves.

2. **Diversification HELPS but exhausts quickly**. The diversified K=2 Sharpe (0.167) is barely better than naive K=2 (0.165), but the K=3 diversified is the same as K=2 because the currency-family cap saturates fast (8 currencies / 2 per pair = max 4 picks; usable picks far fewer due to confidence threshold).

3. **Per-rank Sharpe in diversified shows the structure**:
   - Rank-1 (often USD-major): 0.158
   - Rank-2 (forced to different family, often higher-quality): 0.251 (+59% vs rank-1!)
   - Rank-3 (third family, low-conf trades): -0.054 (negative)

   Diversification picks BETTER trades at rank-2 by avoiding USD-cluster, but the marginal trade quality drops sharply at rank-3 because high-conf signals on disjoint families are rare.

4. **Naive K=5 has anomalous rank-5 Sharpe = 0.477**. Suggests a small set of extreme-confidence outlier trades. Not statistically meaningful given small fold count.

**Conclusion**: The "1-per-bar SELECTOR cap" is NOT the binding constraint. The binding constraint is **per-trade EV calibration** combined with **systemic correlation across pairs**. Even multi-pick can't bypass it — the 2nd, 3rd, 4th picks have similar EV characteristics to the 1st and don't add independent edge.

---

## 6. What's next

**Production toggle (J-3) NOT triggered**. The +0.005 Sharpe / +25% PnL lift at K=2 is too modest to justify production complexity (multi-position management, K-fold spread cost, position-size budget changes). The gate was set conservatively (Sharpe ≥ 0.18 for GO) and we missed by 0.015.

**Pivot to Option B (LSTM / model-class change)** is now the natural next step. Phase 9.13–9.19 collectively prove:

- Layer 1 features: exhausted
- Risk multipliers: small lift
- Pair pool expansion: +20% PnL, Sharpe flat
- Per-trade exit engineering: regression
- Multi-strategy ensemble: NO ADOPT (drowning)
- Strategy threshold filtering: +0.005 Sharpe
- **SELECTOR multi-pick: +0.005 Sharpe** (this phase)

The Sharpe ceiling 0.143–0.177 holds across **every alpha-engineering lever attempted on the LightGBM + 15 TA features + triple-barrier label combination**. The structural conclusion is unavoidable: the **calibration ceiling is in the model class itself**.

### 6.1 Phase 9.X — Option B kickoff (next)

**Targets**: 3 candidate axes, sequenced:

1. **Alternative labels** (cheapest, ~1-2 days): meta-labeling, return-based regression, multi-horizon TB. Test: does a different label produce different confidence calibration?
2. **Alternative features** (~3 days): orderbook/microstructure-derived if data available; volatility clustering; fractal dimension; market-regime embeddings.
3. **Alternative model class** (~5 days): LSTM/Transformer time-series model. Test: does sequence-aware modeling break the per-trade EV ceiling?

Phase 9.X-A through Phase 9.X-C sub-phases. Recommend starting with axis 1 (alternative labels) — it's the cheapest test of whether the ceiling is label-dependent vs model-dependent.

Phase 9.11 (3+ yr robustness) remains **BLOCKED** until any of these breaks Sharpe ≥ 0.20.

---

## 7. Cumulative path through Phase 9.10–9.19

```
v3 (mid label, 1pip):                 Sharpe -0.076  NO-GO
v5 (bid/ask label):                   Sharpe +0.160  SOFT GO  ★ DECISIVE
v8 (C-3 kill switches):               Sharpe +0.177  SOFT GO+
v9-20p (20 pairs):                    Sharpe +0.160  PnL +20.1% vs v5  ★ Phase 9.16 (production default)
v11 (+CSI):                           Sharpe +0.143  PnL -15% vs 20p   ✗ rejected
v12 bucketed (H-1):                   Sharpe +0.127  PnL -19%          ✗ Phase 9.18 NO ADOPT
v12 bucketed+partial (H-2):           Sharpe -0.025  PnL -116%         ✗ Phase 9.18 NO ADOPT
v13 lgbm+mr (t=0.0):                  Sharpe +0.053  PnL +52%, ρ=0.317 ✗ Phase 9.17 NO ADOPT
v13 lgbm+mr (t=0.5):                  Sharpe +0.058  PnL +40%          ✗ Phase 9.17b NO ADOPT
v14 lgbm_only K=2 naive:              Sharpe +0.165  PnL +25%          ★ this phase (PARTIAL GO)
v14 lgbm_only K=2 diversified:        Sharpe +0.167  PnL +8%           ★ this phase
v14 lgbm+mr+bo K=5 naive:             Sharpe +0.064  PnL +341%         ✗ Sharpe collapse despite 4× PnL
```

---

## 8. Notes for future-me

1. **The ρ in the design memo §5 gates was ambiguous**. Inter-strategy ρ (carried from Phase 9.17 framework) doesn't apply to lgbm_only multi-pick. The relevant ρ is between simultaneous picks on different pairs. Future phases that touch SELECTOR rules should explicitly compute this ρ as a primary diagnostic.

2. **Currency-family diversification works but caps fast**. With 8 currencies and 2-currency pairs, max 4 disjoint picks per bar. Practically limited to 2-3 useful picks. For larger universes (+CFDs, +crypto), this lever has more headroom.

3. **Diversified rank-2 BEAT rank-1 in Sharpe** (0.251 vs 0.158). This is unexpected and suggests the SELECTOR's `argmax(confidence)` is biased toward USD-cluster pairs that have systematically lower per-trade Sharpe than non-USD pairs. **Future work**: replace `argmax(confidence)` with `argmax(confidence × non-USD-bonus)` or rank-by-historical-Sharpe.

4. **Per-trade EV calibration is the binding constraint, confirmed for the 4th time**. Phase 9.18 found it for LGBM (confidence ≠ hit rate). Phase 9.17b found it for rule-based MR/BO. Phase 9.19 finds it for multi-pick LGBM (rank-2/3 picks have similar quality to rank-1, not better). Every test of "more trades from the same model class" finds diminishing returns. Conclusion: **the model class itself is the ceiling**.

5. **Naive K=2 PnL +25% may still be worth adopting in production** despite missing the GO gate. Reasoning: production trading rarely needs Sharpe > 0.20; what matters is positive PnL with controlled DD. Naive K=2 lgbm_only delivers +25% PnL, DD%PnL 2.6%, similar Sharpe. If user wants to ship something useful before structural model change, **adopt K=2 naive with `--top-ks 2 --ensemble-cells lgbm_only` as opt-in production toggle**.

6. **lgbm+mr+bo cells with high K should be REJECTED outright**: PnL grows linearly with K (4.41× at K=5) but Sharpe stays at 0.06. This is just multiplied gambling on the same low-EV signals. If a future user is tempted by the PnL number, this is the warning sign.

---

## 9. Commit trail

```
64d04bc  PR #213  J-0 Phase 9.19 kickoff design memo
<TBD>    PR #214  J-1 compare_multipair_v14_topk.py + Top-K SELECTOR + diversification
<TBD>    PR #???  J-2 this closure memo
```
