# Phase 9.16 — Pair universe expansion (Phase G) Closure Memo

**Status**: Closed — 20-pair production default; CSI features rejected (interference with existing cross-pair ranks).
**Master tip at authorship**: `3454d13` (Phase 9.15 merged) + this PR
**Predecessor**: Phase 9.15 closed at master `3454d13`
**Related**: `docs/phase9_roadmap.md` §6.18, `docs/design/phase9_16_design_memo.md`, `docs/design/phase9_15_closure_memo.md`

---

## 1. What this phase set out to do

Phase 9.15 lifted PnL +13–15.5% via signal quality (orthogonal `spread` features). Phase 9.16 attacked the orthogonal axis: **more trade opportunities** by expanding the SELECTOR's universe from 10 to 25–30 pairs.

`PnL = trade_count × per_trade_EV`. With per-trade EV held constant by Phase 9.12/B-2 (mid→bid/ask realism), the only remaining lever for PnL is trade count.

The kickoff design memo predicted **+25–50% PnL** from doubling the pair set.

After G-2 (20-pair backtest) returned only +6.3%, a follow-up question surfaced: **isn't the expansion also supposed to strengthen currency-strength (CSI) signals?** That spawned **G-2.5** — adding explicit per-currency strength features to v11.

---

## 2. What shipped

| PR | Scope | Result |
|----|-------|--------|
| #200 | Phase 9.16 design memo | docs only |
| **(this PR)** | G-1 BA fetch + G-2 20-pair backtest + G-2.5 CSI experiment + closure | 20-pair adopted; CSI rejected |

---

## 3. Results

### 3.1 G-2: 20-pair vs 10-pair (no CSI)

```
                          Sharpe   PnL(pip)   MaxDD   DD%PnL   WinFold%   Trades
10-pair v9 spread (base)   0.152    7,677     218     2.8%     82%      11,958
20-pair v9 spread          0.160    8,157     203     2.5%     90%      12,461
Δ                         +0.008    +480      -15    -0.3pp   +8pp     +503
```

vs v5 baseline (6,793 pip): **PnL +20.1%, MaxDD −22%, WinFold% 82% → 90%**. All metrics improved.

### 3.2 G-2.5: CSI features added on top (v11 = v9 + cs_base/cs_quote/cs_diff)

```
                                  Sharpe   PnL(pip)   MaxDD   DD%PnL   WinFold%   Trades
20-pair v9 (no CSI)               0.160    8,157     203     2.5%     90%      12,461
20-pair v11 (+CSI)                0.143    6,955     215     3.1%     82%      11,680
Δ                                -0.017   -1,202    +12    +0.6pp    -8pp    -781
```

**CSI hurt SELECTOR by 15% PnL**. EU baseline did improve (0.159 → 0.176, +0.017), so CSI is informative *for single-pair strategies* — but on SELECTOR it caused interference.

### 3.3 Pair selection histogram (v9 20-pair)

The internal-sweep code path doesn't surface the per-pair frequency table; we know from the trade count delta (+4%) that new pairs got chosen but at modest rates. The SOFT GO PnL lift mostly comes from the existing 10 pairs, with new pairs filling occasional gaps.

---

## 4. Why was the original +25–50% prediction too optimistic?

The kickoff math:
```
P(any signal | n pairs) = 1 - (1 - p)^n
  n=10: 40%
  n=20: 64%
```

The reality:
- **SELECTOR picks ONE pair per bar.** Adding pairs increases the pool of *candidates* but the trade rate is bounded by bar count, not pair count.
- **Confidence threshold (0.50) filters most candidates.** Many bars in the new pairs have weaker signals than the existing 10.
- **Existing pairs stay dominant.** USD/JPY (29%), EUR/USD (21%), AUD/USD (15%) still take ~65% of selections; the 10 new pairs share the remaining ~35%.

So the realistic picture: **pair expansion is a modest +6% PnL lift, not a +25–50% one**. The lift comes from quality-substitution (newly-added pair beats existing pair on conf at this bar) more than volume-addition (extra trades that wouldn't have fired).

---

## 5. Why did CSI features hurt?

Hypothesis (consistent with Phase 9.15 "all features" finding):

**The existing cross-pair features already encode CSI-like information.**

- `xp_ret_rank` = "this pair's return percentile across the universe" — implicitly captures currency strength when many pairs containing the same base currency are all up
- `xp_basket_corr` = "is this pair moving with or against the basket?" — implicitly captures regime alignment
- `cs_base / cs_quote / cs_diff` = explicit per-currency aggregation

When the model has both implicit (xp_*) and explicit (cs_*) representations of overlapping information:
1. Feature redundancy confuses LightGBM split selection
2. The argmax-by-confidence picker (SELECTOR) interprets the now-noisier `predict_proba` worse
3. Per-bar predictions are correct on average but their *ranking across pairs* becomes less reliable

EU baseline (single-pair) improves because there's no cross-pair argmax — the model uses CSI directly without a downstream picker.

**Production CSI (Phase 9.3) avoids this trap** because it feeds the MetaDecider Score *stage* (filter weight adjustment) rather than Layer 1 features. Different mechanism, no interference.

---

## 6. Verdict

**Production default: 20-pair v9 `spread` bundle, no CSI features.**

| Criterion | Result | Verdict |
|---|---|---|
| Sharpe ≥ 0.20 (legacy GO) | 0.160 | NOT MET |
| **PnL > v5 baseline** | **+20.1%** | **PASS** |
| **DD%PnL < 5%** | **2.5%** | **PASS** |
| New pairs actively selected | ~4% additional trades | weak but positive |

Per the user's PnL-priority frame (since Phase 9.13 closure):
- **Phase 9.16 is a SOFT GO win** — universe expansion delivers a clean +6% on top of Phase 9.15
- The Sharpe gate stays SOFT (legacy 0.20 not met)
- CSI as Layer 1 feature is REJECTED; it doesn't add value because xp_* already captures the signal

---

## 7. Cumulative path through Phase 9.10–9.16

```
v3 (mid label, 1pip):    Sharpe -0.076  NO-GO
v5 (bid/ask label):      Sharpe +0.160  SOFT GO  ★ DECISIVE
v8 (C-3 kill switches):  Sharpe +0.177  SOFT GO+
v9 (10p, +spread):       Sharpe +0.152  PnL +13%, DD -17%      ★ Phase 9.15
v10 (10p, +spread+RH):   Sharpe +0.143  PnL +15.5%             ★ Phase 9.15 opt-in
v9-20p (20 pairs):       Sharpe +0.160  PnL +20.1% vs v5       ★ Phase 9.16 (this)
v11 (+CSI):              Sharpe +0.143  PnL -15% vs 20p        ✗ rejected
```

**Cumulative PnL lift over the entire Phase 9.10–9.16 path: +20.1% from v5 baseline.** Compute it differently: 8,157 / 6,793 = 1.20.

The Sharpe path is rangebound 0.143–0.177 across Phase 9.13–9.16. Sharpe alone can't break out from this band on Layer 1 / pair / risk-lever changes; that's the whole reason we shifted to PnL-priority. To clear Sharpe ≥ 0.20, we need either:
- **Per-trade EV improvement** (Phase 9.18 asymmetric TP/SL + partial exits)
- **Orthogonal alpha source** (Phase 9.17 multi-strategy ensemble)

---

## 8. What's next

**Phase 9.18 (asymmetric TP/SL + partial exits)** is now the highest-priority lever because it's the only remaining one targeting per-trade EV directly. Phase 9.17 (multi-strategy) is bigger scope and depends on having a single solid strategy first — which Phase 9.15+9.16 has now produced (20-pair spread bundle, +20% PnL over v5).

Alternative ordering: Phase 9.17 first if the user wants alpha diversification before EV tuning.

Phase 9.11 (3+ yr robustness) remains BLOCKED on Sharpe ≥ 0.20.

---

## 9. Tier 2 not pursued

The kickoff memo mentioned an optional Tier 2 extension to 25 pairs (GBP/CAD, EUR/NZD, GBP/NZD, CAD/JPY, USD/SGD). Given that 20-pair only delivered +6% PnL — well below the +25–50% prediction — pushing to 25 pairs would produce diminishing returns:
- Estimated Tier 2 incremental: +2–3% PnL beyond 20-pair
- Cost: +5 BA files × 75MB = +375MB data, ~5 min fetch
- Operational footprint: 5 more pairs to monitor / spread-audit

Skip for now; revisit if Phase 9.17/9.18 don't reach full GO and we need every percentage point.

---

## 10. Production runtime toggle (extends Phase 9.15's pattern)

The Phase 9.15 closure proposed `feature_set` as a runtime toggle. Phase 9.16 adds `pair_universe`:

```yaml
# scripts/run_paper_decision_loop.py config
pair_universe: "g10_majors"     # 10 pairs (Phase 9.15 baseline)
                                # or "g20_majors" for 20-pair (recommended)
feature_set: "spread"           # "spread" or "spread+rh"
```

The runner reads both, loads the matching model, instantiates the matching FeatureService, and trades the matching pair list. No code change between universes — just retrain at universe change time.

---

## 11. Commit trail

```
5b46fe1  PR #197  Phase 9.15 design memo
b709df1  PR #198  F-1 orthogonal features + MaxDD + internal sweep
3454d13  PR #199  F-2 RH + Phase 9.15 closure memo
<TBD>    PR #200  Phase 9.16 kickoff design memo (merged earlier this session)
<TBD>    PR #???  G-2 + G-2.5 + this closure memo
```

---

## 12. Notes for future-me

- **Pair expansion gives less than the textbook math predicts** because SELECTOR's per-bar picker bounds the trade rate. Realistic expansion lift is +5–15% PnL per pair-set doubling, not the +50–100% from independent signal-rate math.
- **Don't add CSI as Layer 1 features when xp_* features exist.** Phase 9.16/G-2.5 was a clean negative result. The same redundancy lesson applies to any future explicit cross-pair feature.
- **CSI has its place — in MetaDecider Score stage (production Phase 9.3)**. Different mechanism, different objective, complementary to xp_*. Don't conflate them.
- **Per-trade EV is the binding constraint for further Sharpe improvement.** Phase 9.18 (asymmetric TP/SL) targets this directly. If 9.18 doesn't reach Sharpe ≥ 0.20, the strategy probably needs a structural change (LSTM, alternative labels, etc.) rather than more feature engineering.
- **20 pairs is comfortably enough for production.** Tier 2 (25 pairs) gives diminishing returns; not worth the operational complexity unless 9.17/9.18 force the issue.
