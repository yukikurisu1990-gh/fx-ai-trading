# Phase 9.18 — Asymmetric TP/SL + partial exits (Phase H) Design Memo

**Status**: Design phase (2026-04-25)
**Predecessor**: Phase 9.16 closed at master `a973018`
**Owner**: くりす
**Related**: `docs/phase9_roadmap.md` §6.20, `docs/design/phase9_16_closure_memo.md`, `docs/design/phase9_15_closure_memo.md`

---

## 1. Why this phase

Phase 9.15 lifted PnL +13–15.5% via signal quality (orthogonal `spread` features). Phase 9.16 lifted PnL another +6.3% via universe expansion (10 → 20 pairs). Cumulative path **v5 → v9-20p = +20.1% PnL** at MaxDD%PnL 2.5%.

But Sharpe stayed rangebound at **0.143–0.177** across Phase 9.13–9.16. The closure memo §7 named the cause:

> Sharpe alone can't break out from this band on Layer 1 / pair / risk-lever changes; that's the whole reason we shifted to PnL-priority. To clear Sharpe ≥ 0.20, we need either:
> - **Per-trade EV improvement** (Phase 9.18 asymmetric TP/SL + partial exits)
> - **Orthogonal alpha source** (Phase 9.17 multi-strategy ensemble)

Phase 9.18 attacks the **per-trade EV** axis. It is the single remaining lever that touches the EV/variance ratio directly (and therefore can move Sharpe), without expanding to a multi-strategy stack.

The math:
```
PnL = trade_count × per_trade_EV
        ↑                  ↑
   widened by 9.16    Phase 9.18 target
   (10 → 20 pairs)    (vary TP/SL by confidence + partial exits)

Sharpe = mean(per_trade_PnL) / std(per_trade_PnL) × √(trades_per_year)
              ↑                       ↑
         lifted by 9.18         can shrink slightly
         (asymmetric TP/SL)     (more variance from
                                 partial exits) — must verify
```

---

## 2. Current state

### 2.1 Symmetric TP/SL is the de-facto baseline

`compare_multipair_v9_orthogonal.py` (and v10/v11) hardcode:
```
--tp-mult 1.5 --sl-mult 1.0
```
Triple-barrier label fires `+1` (TP) / `-1` (SL) / `0` (timeout) at the same `1.5×ATR` and `1.0×ATR` distances regardless of model confidence.

In production, every trade — `conf=0.51` borderline and `conf=0.78` strong — uses the same payoff geometry. This is leaving EV on the table.

### 2.2 No partial exits

When a trade hits TP (1.5×ATR), it's fully closed. When trends extend beyond 1.5×ATR — a **fat-tail favorable case** — the strategy doesn't capture them. Conversely, when a trade is well into profit and reverses, there's no profit-locking mechanism short of TP itself.

### 2.3 What Phase 9.16 closure says about confidence distribution

The SELECTOR uses `argmax(predict_proba)` and a fixed `0.50` confidence threshold. From v9 20p logs:
- ~40% of fired trades have `conf ∈ [0.50, 0.55]` — borderline
- ~45% have `conf ∈ [0.55, 0.65]` — typical
- ~15% have `conf ≥ 0.65` — strong

Borderline trades have lower hit rates (typically 50–53%) but the same payoff geometry — they're net EV drag. Strong trades (60–65% hit rate) deserve **larger payoff multiples** because the model is confidently right more often.

---

## 3. Hypothesis

**H-1**: A confidence-bucketed TP/SL schedule increases per-trade EV by **+15–25%** without materially changing trade count or MaxDD%PnL.

**H-2**: Partial exit at 1×ATR + entry-stop trail on the remainder captures **+5–10%** additional PnL on the long-tail favorable moves at the cost of slightly higher per-trade variance.

**Combined target**: per-trade EV +20–30%, Sharpe +0.02–0.04, PnL +10–20% over the 20-pair v9 spread baseline.

If the combined Sharpe lift takes us from 0.160 → ≥ 0.18, we're inside reach of the **legacy GO threshold (Sharpe ≥ 0.20)** with a single more lever (any of: 9.17 multi-strategy, OOF RH rewrite, or 9.18 H-3 conf-threshold tuning) — Phase 9.11 (3+ yr robustness) becomes unblockable.

---

## 4. Design

### 4.1 H-1 — Confidence-bucketed TP/SL

Three buckets, named for the histogram from §2.3:

| Bucket | Confidence | TP×ATR | SL×ATR | Rationale |
|--------|-----------|--------|--------|-----------|
| **Low** (`borderline`) | `[0.50, 0.55)` | **1.2** | **1.2** | symmetric tight — minimize loss tail when model barely calls direction |
| **Mid** (`typical`) | `[0.55, 0.65)` | **1.5** | **1.0** | current default — keep for continuity / A/B baseline |
| **High** (`strong`) | `[0.65, 1.00]` | **2.0** | **0.8** | asymmetric wide — let winners run when model is confident |

**Why these numbers**:
- High bucket: 2.5× payoff ratio (2.0/0.8) means break-even hit rate = 28.6%. With observed ~62% hit rate on `conf ≥ 0.65`, expected per-trade EV ≈ +0.74×ATR (vs +0.45 in current 1.5/1.0).
- Mid bucket: identical to current — guarantees the policy is non-degenerate (zero behavioral drift on 45% of trades).
- Low bucket: payoff ratio 1.0× with **the same hit rate** as today gives ~0 EV; shrinking to 1.2/1.2 caps the loss tail.
   - Alternative: drop borderline trades entirely (set bucket to "no-trade"). Cleaner statistically but reduces trade count by 40%. Per Phase 9.16 closure §6, trade count is one of two PnL levers — cutting 40% of trades is too aggressive in a PnL-priority frame. Keep them but neutralize.

**Pure-label interpretation** (no executor needed): we relabel triple-barrier targets per-trade by recomputing barrier hits at the bucket-specific multiples, after model inference. This is a **post-prediction transform** on the eval loop, not a feature-side change. Training labels stay at the global `1.5×ATR / 1.0×ATR` for stability.

```
Current (symmetric):
  if move_to_TP <= move_to_SL: label = +1 (TP)
  elif move_to_SL <= move_to_TP: label = -1 (SL)
  else: label = 0 (timeout)

New (asymmetric, applied at eval-time after predict_proba):
  bucket = bucketize(predict_proba.max())
  TP_dist, SL_dist = bucket.tp_mult * ATR, bucket.sl_mult * ATR
  recompute barrier with these distances
  realized_pnl = TP_dist (TP) / -SL_dist (SL) / 0 (timeout)
```

**Slippage**: still applied as `pnl - slippage_pip` at TP/SL hit. Asymmetric SL=0.8×ATR means tighter stops which **may hit more often under high-volatility regimes** — explicitly track `bucket × outcome` matrix in the closure memo.

### 4.2 H-2 — Partial exit at 1×ATR + entry-stop trail

Applied **only on the High bucket** (TP=2.0, SL=0.8). Mid and Low buckets keep single TP/SL. Reasons:
- High-bucket trades have the longest expected favorable runs.
- Mid and Low buckets are already at tight payoff ratios; partial exits there add variance without proportional EV gain.
- Limiting partial exits to 15% of trades keeps the executor logic shallow (a sweep over 15% of fills), keeping eval time within budget.

```
At entry (High bucket only):
  TP = entry + 2.0 × ATR
  SL = entry - 0.8 × ATR
  partial_TP = entry + 1.0 × ATR
  partial_size = 0.5 × full_size
  trail_stop_after_partial = entry  (lock to entry once partial fires)

Sequence at eval:
  if hits SL first:                           pnl = -0.8 × ATR (full size)
  elif hits partial_TP first:
       realize 0.5 × 1.0 × ATR = 0.5 × ATR
       remaining 0.5 × size now has SL=entry, TP=2.0×ATR
       if hits trail_stop (entry):            additional 0
       elif hits TP (2.0×ATR):                additional 0.5 × 2.0 × ATR = 1.0 × ATR
       elif timeout:                          additional 0 (closed at last price; eval simplifies to 0)
  elif hits TP first (without partial):       pnl = 2.0 × ATR (full size)
                                              ← cannot happen because partial_TP < TP
                                              ← so this branch is dead in practice
  elif timeout:                               pnl = 0
```

In bar-aggregated eval, "first" is determined by the **per-bar OHLC ordering convention** used in the existing label code (already implemented in `_label_pair`). We extend that function to also emit:
- `partial_hit: bool` — did partial fire?
- `partial_pnl: float` — realized at partial
- `final_pnl: float` — realized at terminal barrier (full or remainder)
- `total_pnl: float` — sum

`total_pnl` is the per-trade pnl used in Sharpe / cumulative PnL / MaxDD calculations.

**Slippage**: `total_pnl - slippage_pip × n_legs` where `n_legs = 1` (no partial) or `2` (with partial). H-2 raises commission cost slightly — explicitly amortized in the closure memo.

### 4.3 Eval pipeline integration

We follow the **internal sweep** pattern proven in Phase 9.15 / 9.16:

- `scripts/compare_multipair_v12_asymmetric.py` is the new eval. **No code in `src/` changes.** It is research-only.
- It reuses the v9 (20-pair, spread bundle) feature pipeline verbatim — load + features run **once**.
- The sweep dimension is the labeling/exit policy:
  - `cell A`: baseline = v9 20p symmetric (TP=1.5, SL=1.0, no partial)
  - `cell B`: H-1 asymmetric only (bucketed TP/SL, no partial)
  - `cell C`: H-1 + H-2 (bucketed + partial on High bucket)
- The model is trained **once on the global label** (TP=1.5 / SL=1.0); only the eval-side relabeling differs across cells. This preserves the model and guarantees the bucketed comparison is a pure exit-policy A/B, not a model A/B.

Wall time estimate: 1.0× v9 internal sweep (~25 min single fold-set, 39 folds × 20 pairs, no extra train passes).

### 4.4 What we explicitly avoid

| Avoided | Why |
|---|---|
| Re-training per bucket | Would mix exit-policy and model effects; can't attribute |
| Bucketed labels at training time | Different barrier per training row destroys label consistency; also the bucket depends on a confidence we don't have at training time (chicken-and-egg without OOF) |
| Adding `confidence_bucket` as a feature | Same chicken-and-egg as above |
| Partial exits on Mid / Low buckets | Variance increase without EV justification; also longer eval time |
| Tuning bucket boundaries via grid search | Over-fitting risk on 39 folds; pick principled values, accept what they yield, walk-forward CV reports out-of-sample stability |
| Touching `services/labeling/` or production code | This is research first. Production wiring lands only if the closure memo says GO. Pattern matches Phase 9.15 (research → runtime toggle wiring deferred) |

### 4.5 Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Bucket boundaries (0.55 / 0.65) are ad-hoc → over-fit | Walk-forward CV across 39 folds reports per-fold Sharpe / PnL stability; closure memo includes per-bucket trade-count distribution to verify all three buckets are populated in every fold |
| Tighter SL=0.8×ATR on High bucket → higher hit-rate on SL in volatile periods | Track `bucket × outcome` matrix in closure memo; if High-bucket SL hit rate spikes > 50%, the bucket is mis-defined and we revert |
| Partial exit logic introduces eval bugs | Property-style smoke test: for any cell, `total_pnl == partial_pnl + final_pnl`; sum of `bucket × outcome` cells equals total trade count |
| Slippage doubling (n_legs=2 on partial) eats the EV gain | Explicit `pnl_after_costs` column in summary; if slippage ate >30% of partial gain, H-2 is not adopted |
| In-sample leakage (model sees barrier outcomes that depend on a confidence the model itself is producing) | Mitigated by §4.3 design: model trained once on global labels; bucketing happens post-prediction. There is no path from bucket to feature |
| Wall time blows up | Internal sweep guarantees load+features+train is shared across cells. Only the eval loop runs 3× (one per cell), and it's the cheapest stage |

---

## 5. Success criteria for closure memo

Verdict gates (PnL-priority frame, consistent with Phase 9.13/9.15/9.16 closures):

| Cell condition | Verdict |
|---|---|
| **PnL ≥ 1.10 × baseline AND DD%PnL ≤ 5% AND Sharpe ≥ baseline** | **GO** — adopt as production default |
| **PnL ≥ 1.05 × baseline AND DD%PnL ≤ 5%** (Sharpe flat) | **PARTIAL GO** — adopt but flag the lack of Sharpe lift |
| **Sharpe ≥ 0.18** (any cell) | **STRETCH GO** — within reach of legacy 0.20 gate |
| **PnL < baseline OR DD%PnL > 5%** | **NO ADOPT** — keep symmetric baseline |

Secondary:
- per-bucket trade-count and hit-rate distribution
- per-bucket realized EV vs theoretical EV
- bucket-conditional MaxDD (does Low bucket cause DD spikes?)
- partial-exit fire rate on High bucket (should be ~35–50% of High trades)

---

## 6. PR breakdown

| PR | Scope | Size | Depends |
|----|-------|------|---------|
| **H-0** (this memo) | `docs/design/phase9_18_design_memo.md` | docs only | master `a973018` |
| **H-1** | `scripts/compare_multipair_v12_asymmetric.py` — bucketed TP/SL eval, internal sweep over `{symmetric, bucketed}` cells; 20-pair v9 spread feature pipeline | ~250 lines (mostly copied-and-extended from v9) + ~10 unit tests on the bucketing function | H-0 |
| **H-2** | Add partial-exit cell to v12 sweep; extend `_label_pair` to emit `partial_pnl / final_pnl / total_pnl`; per-bucket × per-outcome matrix in summary | ~120 lines + ~5 unit tests | H-1 |
| **H-3** | Closure memo `docs/design/phase9_18_closure_memo.md` — verdict, per-cell metrics, per-bucket distribution, recommendation for production wiring | docs + summary table | H-2 |
| **H-4** (conditional) | If H-3 says GO/PARTIAL GO: production runtime toggle wiring (`exit_policy: "symmetric" / "bucketed" / "bucketed+partial"` in runner config) | ~150 lines + tests | H-3 verdict |

H-4 is **not authored speculatively**. We open it only if the closure memo says GO.

---

## 7. Detailed design — H-1 (bucketed TP/SL)

### 7.1 Bucket function

```python
def _bucket_for_confidence(conf: float) -> tuple[float, float, str]:
    """Return (tp_mult, sl_mult, bucket_name) for a model confidence."""
    if conf < 0.55:
        return (1.2, 1.2, "low")
    if conf < 0.65:
        return (1.5, 1.0, "mid")
    return (2.0, 0.8, "high")
```

This function is pure, deterministic, and unit-testable. Boundaries are exclusive at the upper end (`< 0.65`) so a confidence of exactly 0.65 falls into `high`.

### 7.2 Eval-time relabel

The existing `_label_pair` produces TP/SL hit times for the global `tp_mult / sl_mult`. For H-1 we want **per-trade barrier distances**. Two implementation options:

**Option A** (cleaner, slower): re-run barrier-search per-trade with bucket-specific multipliers. Cost: O(trades × bar_lookahead).

**Option B** (faster, requires care): pre-compute barrier-hit times at three reference multiplier pairs `(1.2,1.2)`, `(1.5,1.0)`, `(2.0,0.8)` for *every* candidate bar. At eval time, look up the right pair per trade. Cost: O(bars × 3) at label time, O(trades) at eval time.

**Pick B**. The label step in v9 already runs O(bars × 1) — going to O(bars × 3) keeps wall-time linear, and the eval-time lookup becomes essentially free. Memory grows by 3× on the label DataFrame; on 365d M1 × 20 pairs ≈ 50MB → 150MB, well within budget.

### 7.3 Output columns

Existing v9 trade-summary CSV has columns:
```
fold, pair, signal_time, direction, conf, label, pnl, pnl_after_cost, ...
```
H-1 adds:
```
bucket, tp_mult, sl_mult
```
H-2 adds:
```
partial_hit, partial_pnl, final_pnl, total_pnl, n_legs, slippage_total
```
`pnl_after_cost` becomes `total_pnl - slippage_total`.

---

## 8. Detailed design — H-2 (partial exit)

### 8.1 Bar-level sequencing

Inside a candidate bar's lookahead window (configurable, default 60 bars = 60 minutes M1), we walk bars in order. Per bar:
```
for each remaining position leg:
    if leg.barrier_hit_in_this_bar(direction):
        realize leg
        if all legs realized: break
```

For the High bucket (partial-exit cell):
- Initially, two legs: `partial` (size 0.5, TP=1.0×ATR, SL=0.8×ATR) and `runner` (size 0.5, TP=2.0×ATR, SL=0.8×ATR initially).
- When `partial` hits its TP, runner's SL is **moved to entry** (trail = entry-stop).
- When `partial` hits SL (= same as runner SL = 0.8×ATR), both legs close at SL — same as no-partial outcome but split across two legs.

This doesn't introduce new failure modes vs the symmetric-baseline labeling: the SL hit event is already captured in baseline, we just attribute half its loss to one leg and half to another.

### 8.2 Conservation property (test-asserted)

For every trade:
```
total_pnl == partial_pnl + final_pnl
abs(total_pnl) <= max_excursion_in_window  (sanity)
n_legs ∈ {1, 2}
```

A unit test in H-1 PR confirms the bucketing function. A unit test in H-2 PR confirms the conservation property on synthetic OHLC arrays (trend / chop / gap-down / gap-up scenarios).

---

## 9. Expected impact (theoretical bounds)

### 9.1 H-1 (bucketing only)

Assume bucket distribution from §2.3 (Low 40% / Mid 45% / High 15%) and bucket-conditional hit rates roughly:
- Low: ~52% (borderline trades barely above coin-flip)
- Mid: ~57% (current default)
- High: ~62% (model confident is at least somewhat informative)

Per-trade EV (in ATR units):
- Symmetric baseline (1.5/1.0):   `0.40 × 0.52 + 0.45 × 0.57 + 0.15 × 0.62 = 0.572` → EV = 0.572 × 1.5 - 0.428 × 1.0 = +0.430 ATR
- H-1 bucketed:
  - Low (1.2/1.2):    EV_L = 0.52 × 1.2 - 0.48 × 1.2 = +0.048
  - Mid (1.5/1.0):    EV_M = 0.57 × 1.5 - 0.43 × 1.0 = +0.425
  - High (2.0/0.8):   EV_H = 0.62 × 2.0 - 0.38 × 0.8 = +0.936
  - Weighted total:   0.40 × 0.048 + 0.45 × 0.425 + 0.15 × 0.936 = +0.351 ATR

Wait — the headline EV math goes **down** (+0.351 vs +0.430)? Let me re-check.

The discrepancy is in the Low bucket: 1.2/1.2 with 52% hit rate produces EV ≈ 0 (essentially symmetric). At 1.5/1.0 with 52% hit rate, EV = 0.52 × 1.5 - 0.48 × 1.0 = +0.300. So the Low bucket **loses EV** going from current to bucketed.

This is the price of capping the loss tail. The benefit comes from the High bucket: EV jumps from `0.62 × 1.5 - 0.38 × 1.0 = +0.550` (current) to `+0.936` (bucketed) — a +70% per-trade EV lift on those trades.

**Whether H-1 is net positive depends on the actual bucket distribution and hit rates.** The numbers above are estimates; the eval will produce ground truth. If observed bucket distribution skews higher (e.g., High = 25%) or hit rates are different, the net effect changes.

**This is exactly why we run the eval before committing to production.** Phase 9.18 might be a partial GO (Mid+High only, drop Low entirely) rather than a full GO.

### 9.2 Decision implication

If the eval shows the Low bucket is EV-neutral or negative even at 1.2/1.2, the closure memo recommends a **simpler 2-bucket policy**:
```
conf < 0.55: skip the trade
conf in [0.55, 0.65): TP=1.5, SL=1.0  (current)
conf >= 0.65: TP=2.0, SL=0.8           (asymmetric)
```
This is a cleaner alternative considered in §4.1 and held in reserve. Phase 9.16 closure §6's lesson — "don't add complexity that the data doesn't support" — applies here.

### 9.3 H-2 (partial exit) expected lift

On High-bucket trades only (~15% of trades). Roughly:
- Without partial: EV_H = +0.936 ATR (computed above)
- With partial (assume 70% of High trades hit partial first, then 50% of remaining hit TP, 30% trail to entry, 20% timeout):
  - Partial leg: +0.5 ATR realized on 70% × 100% of trades = +0.35 ATR contribution
  - Runner leg (split 50/30/20 of remaining 70%):
    - TP: 0.5 × 2.0 = +1.0 ATR on 70% × 50% = 35% → +0.35 contribution
    - Trail: 0 on 70% × 30% = 21% → 0
    - Timeout: 0 on 70% × 20% = 14% → 0
  - SL (no partial fire): -0.8 ATR on 30% → -0.24 contribution
  - Total weighted: +0.35 + 0.35 - 0.24 = +0.46 ATR per High-bucket trade with partial

Compared to **+0.936 without partial**, this is **worse**. Why?

Because `partial(0.5 × 1.0)` + `runner(0.5 × 2.0 = 1.0)` = `1.5 ATR ceiling` is below the `2.0 ATR` ceiling of no-partial. Partial trades lose the possibility of running all the way to 2.0 in one piece. The trade-off:
- Without partial: full +2.0 ATR ceiling, full -0.8 ATR floor, hit-rate ~62% TP / 38% SL.
- With partial: partial lock at +0.5 ATR realized (70% of trades, conservatively), runner caps at +1.0 ATR ceiling, runner floor at 0 (entry).

H-2's value isn't in raising the ceiling — it's in **converting partial-tail losses into wins** (the trail-to-entry mechanism). If trail-to-entry rescues a meaningful fraction of trades that would have otherwise hit SL, H-2 helps. If most of those trades would have hit TP anyway, H-2 is a self-inflicted EV haircut.

**The eval will tell us.** Don't pre-commit to H-2.

### 9.4 Provisional realistic targets

| Cell | Trade count | PnL (vs 20p baseline 8,157) | DD%PnL | Sharpe |
|------|------------|----|----|----|
| 20p v9 baseline (cell A) | 12,461 | 8,157 | 2.5% | 0.160 |
| H-1 bucketed (cell B) | 12,461 (same) | **8,800–9,500 (+8–17%)** | 2.5–3.5% | **0.165–0.185** |
| H-1 + H-2 (cell C) | 12,461 (same, but doubled-leg costs) | **8,300–9,800 (+2–20%)** | 3.0–5.0% | 0.155–0.180 |

Cell C is **much wider** because the partial-exit benefit is more sensitive to bucket-level dynamics. We honestly don't know if H-2 helps until we run it.

---

## 10. Out of scope (deferred)

| Item | Deferred to |
|------|-------------|
| Multi-strategy ensemble (alpha diversification) | Phase 9.17 |
| Production runtime toggle for `exit_policy` | H-4 (conditional on H-3 verdict) |
| OOF rewrite of recent_hit_rate | Phase 9.X (orthogonal, low priority) |
| 3+ yr robustness | Phase 9.11 (BLOCKED on Sharpe gate; lifted iff this phase reaches Sharpe ≥ 0.20) |
| Conf-threshold sweep (raise from 0.50 to 0.55) | Phase 9.X-D — naturally tested as a side effect of the Low bucket if Low bucket is dropped |

---

## 11. Timeline estimate

| Step | Wall time |
|------|-----------|
| H-0 (this memo + PR) | <1 hr |
| H-1 implementation + tests | 4–6 hr |
| H-1 eval run (internal sweep) | ~25 min |
| H-2 implementation + tests | 3–4 hr |
| H-2 eval run | ~30 min |
| H-3 closure memo | 1.5 hr |
| **Total** | **~1.5 day** |

H-4 is a separate sub-day if triggered.

---

## 12. Open questions

- **Should the Low bucket simply be dropped?** §4.1 keeps it for trade-count preservation; §9.1 hints it might not pay. The eval answers this.
- **Should partial-exit ratio be 0.5 or 0.33?** Smaller partial = less ceiling sacrifice but smaller lock-in. Defer to single-shot 0.5; sweep is overkill at this stage.
- **Should H-1 boundaries be 0.55 / 0.65 or 0.53 / 0.62 (matching empirical histogram inflection points)?** Pick the round numbers; rerun if the closure memo's per-bucket histograms look mis-aligned.
- **If H-1 succeeds and H-2 doesn't, do we still run H-2 in production?** No. H-4 wires only the cell that won.

---

## 13. References

- `docs/design/phase9_15_closure_memo.md` — orthogonal features, PnL-priority frame, internal sweep pattern
- `docs/design/phase9_16_closure_memo.md` — pair expansion, why textbook math overshoots, redundancy lessons
- `docs/phase9_roadmap.md` §6.20 — original Phase 9.18 entry (this memo expands and supersedes)
- `scripts/compare_multipair_v9_orthogonal.py` — feature pipeline + internal sweep template (clone for v12)
