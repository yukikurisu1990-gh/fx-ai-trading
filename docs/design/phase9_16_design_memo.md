# Phase 9.16 — Pair universe expansion (Phase G) Design Memo

**Status**: Design phase (2026-04-26)
**Predecessor**: Phase 9.15 closed at master `3454d13`
**Owner**: くりす
**Related**: `docs/phase9_roadmap.md` §6.18, `docs/design/phase9_15_closure_memo.md`

---

## 1. Why this phase

Phase 9.15 (orthogonal features) lifted PnL by **+13–15.5%** at improved DD. The mechanism was *better signal quality* per trade. Phase 9.16 attacks the orthogonal axis: **more trade opportunities** by expanding the SELECTOR's pair universe from 10 to 25–30 instruments.

The math:
```
PnL = trade_count × per_trade_EV
        ↑                  ↑
   widen via            held flat
   pair expansion       by 9.15
```

With per-trade EV held at ~0.65 pip (Phase 9.15 confirmed this is structurally bounded by mid→bid/ask label realism), the only ways to grow PnL further are:
1. **More trades** (Phase 9.16: pair universe expansion)
2. **More alpha sources** (Phase 9.17: multi-strategy ensemble)
3. **Bigger trades** (Phase 9.18: asymmetric TP/SL + partial exits)

Phase 9.16 takes the cheapest path: more pairs = more SELECTOR options at each bar.

---

## 2. Current state

```
DEFAULT_PAIRS (Phase 9.15, n=10):
  EUR_USD, GBP_USD, AUD_USD, NZD_USD,
  USD_CHF, USD_CAD, EUR_GBP,
  USD_JPY, EUR_JPY, GBP_JPY
```

SELECTOR's pair selection frequency (v9 spread bundle):
```
USD_JPY  ~32%   ← heavy concentration
EUR_USD  ~22%
AUD_USD  ~16%
GBP_USD  ~13%
EUR_JPY  ~3%
NZD_USD  ~3%
EUR_GBP  ~3%
USD_CAD  ~3%
USD_CHF  ~2%
GBP_JPY  ~2%
```

JPY-block (USD/JPY + EUR/JPY + GBP/JPY) takes ~37% of selections. Adding more JPY crosses (AUD/JPY, NZD/JPY, CHF/JPY) and other liquid majors should:
- Distribute selection across more pairs (lower concentration risk)
- Capture trade opportunities currently missed (no good pair → no trade)
- Modestly lift PnL via increased trade count

---

## 3. Universe expansion plan

### 3.1 Tier 1 — high-liquidity priority (10 pairs to add)

These have OANDA spreads typically < 3 pips and high daily volume:

| Pair | Cluster | Why |
|------|---------|-----|
| **AUD/JPY** | JPY + Commodity | Top JPY cross beyond G/E/U pairs |
| **NZD/JPY** | JPY + Commodity | Pairs naturally with AUD/JPY |
| **CHF/JPY** | JPY + EUR-block | Safe-haven cross, distinct dynamics |
| **EUR/CHF** | EUR + Safe-haven | Highly liquid; SNB-influenced range |
| **EUR/AUD** | EUR + Commodity | Active in Asian/London transition |
| **EUR/CAD** | EUR + Commodity | Crude-oil-correlated alpha |
| **AUD/NZD** | Commodity inner | Pure commodity-currency dynamics |
| **AUD/CAD** | Commodity inner | Both export-driven |
| **GBP/AUD** | GBP + Commodity | Often trends in London hours |
| **GBP/CHF** | GBP + Safe-haven | Volatile, can produce wide signals |

This brings total to **20 pairs**.

### 3.2 Tier 2 — extension to 25 pairs (5 more)

If Tier 1 results show meaningful lift, extend to 25:

| Pair | Cluster | Notes |
|------|---------|-------|
| GBP/CAD | GBP + Commodity | Liquid, tighter spreads than expected |
| EUR/NZD | EUR + Commodity | Fewer pure trend periods, but valid |
| GBP/NZD | GBP + Commodity | Most volatile of the GBP block |
| CAD/JPY | JPY + Commodity | Underused but active |
| USD/SGD | USD-quoted | Asian-session liquid, low correlation |

### 3.3 Out of scope for now

- USD/HKD, USD/MXN — pegged or thin
- USD/SEK, USD/NOK — Nordic pairs, less liquid than majors
- USD/ZAR, USD/TRY, USD/MXN — emerging-market noise

---

## 4. Expected impact

### 4.1 Theoretical bounds

If trade count is dominated by "any pair has a valid signal at this bar" probability:
```
P(any signal | n pairs) = 1 - (1 - p)^n
```

With per-pair signal rate ≈ 5% on the v9 spread bundle:
- n=10: P = 1 - 0.95^10 ≈ 40%
- n=20: P = 1 - 0.95^20 ≈ 64%
- n=25: P = 1 - 0.95^25 ≈ 72%

So trade count could grow up to **+60–80%** in the upper bound. Realistic case (signal rates correlated, some new pairs lower-quality):
- **+25–50%** trade count expected

With per-trade EV held constant, PnL scales similarly.

### 4.2 Realistic targets

| Universe | Trade count est. | PnL est. (vs v9 spread) | DD est. |
|---|---|---|---|
| 10 pairs (current) | 11,958 | 7,677 (baseline) | 218 |
| 20 pairs (Tier 1) | 14,000–17,000 | 9,000–12,000 (**+17–56%**) | 220–280 |
| 25 pairs (Tier 1+2) | 15,000–19,000 | 10,000–14,000 (**+30–82%**) | 230–300 |

DD is expected to scale modestly with PnL — diversification across more pairs helps reduce correlation, but adding more positions also increases tail exposure. Net effect: DD%PnL likely stays at 2.5–4%.

### 4.3 Phase 9.10 GO threshold check

Sharpe is invariant under trade-count scaling (Phase 9.13 finding). Adding pairs:
- Same per-trade EV → same per-trade Sharpe
- Same per-trade variance → Sharpe **unchanged at ~0.15**

So Phase 9.16 alone will NOT clear Sharpe ≥ 0.20. The PnL-priority frame remains the winning verdict path. To clear the legacy Sharpe gate, Phase 9.17 (multi-strategy) or Phase 9.18 (asymmetric exits) are needed because they alter the per-trade EV/variance ratio.

---

## 5. PR breakdown

| PR | Scope | Size | Depends |
|----|-------|------|---------|
| **G-0** (this memo) | `docs/design/phase9_16_design_memo.md` | docs only | master `3454d13` |
| **G-1** | Fetch BA data for 10–15 new pairs (parallel); per-pair spread/volume statistics for liquidity audit | ~50 lines + ~750MB data | G-0 |
| **G-2** | Run v9 (spread bundle) with 20-pair universe; compare to 10-pair baseline | ~30 lines (default pair list update) | G-1 |
| **G-3** | Optional: extend to 25 pairs if Tier 1 succeeds; final closure memo | docs + data fetch | G-2 |

---

## 6. Detailed design — G-1 data fetch

```
Pairs to fetch (10):
  AUD_JPY, NZD_JPY, CHF_JPY, EUR_CHF, EUR_AUD,
  EUR_CAD, AUD_NZD, AUD_CAD, GBP_AUD, GBP_CHF

Data per pair: ~75 MB JSONL (BA mode, 365d M1, ~370k rows)
Total: ~750 MB

Fetch command:
  for pair in <new pairs>; do
    python scripts/fetch_oanda_candles.py \
      --instrument $pair --granularity M1 --days 365 --price BA \
      --output data/candles_${pair}_M1_365d_BA.jsonl &
  done
  wait

Wall time: ~5–10 min in parallel (OANDA rate limits)
```

After fetch, run a quick liquidity audit per pair:
```python
for pair in new_pairs:
    df = load_ba(f"data/candles_{pair}_M1_365d_BA.jsonl")
    median_spread_pip = ((df.ask_o - df.bid_o) / pip_size).median()
    print(f"{pair}: median spread {median_spread_pip:.2f} pip")
```

If any pair has median spread > 5 pip, exclude it (too costly to capture realistic alpha).

---

## 7. Detailed design — G-2 backtest run

Modify `DEFAULT_PAIRS` in v9 (or a v9-derived script) to include the 10 new pairs. Run with the F-1 winner config:

```
--features-bundle spread
--tp-mult 1.5 --sl-mult 1.0 --slippage-pip 0.0
```

Compare:
- 10-pair baseline (already known): SELECTOR PnL 7,677, DD 218
- 20-pair run: target SELECTOR PnL 9,000–12,000, DD < 280

Per-pair SELECTOR pick frequency in the new run will tell us:
- Are new pairs being chosen often? (good — they add value)
- Or are they ignored? (no harm, just wasted compute)

---

## 8. Out of scope (deferred)

| Item | Deferred to |
|------|-------------|
| Multi-strategy ensemble | Phase 9.17 |
| Asymmetric TP/SL + partial exits | Phase 9.18 |
| Conf threshold sweep | Phase 9.X-D (orthogonal to 9.16, can run anytime) |
| Production wiring (FeatureService pair set, OandaInstrumentRegistry expansion) | After Phase 9.18 produces full GO |
| 3+ yr robustness | Phase 9.11 (BLOCKED on Sharpe gate) |

---

## 9. Success criteria for closure memo

| Cell condition | Verdict |
|---|---|
| 20-pair PnL ≥ 1.20 × (10-pair PnL) AND DD%PnL ≤ 5% | **GO** (proceed to 9.17 with confidence) |
| 1.10 ≤ PnL ratio < 1.20 AND DD acceptable | **PARTIAL GO** (modest lift, continue to 9.17 anyway) |
| PnL ratio < 1.10 OR DD%PnL > 5% | **NO LIFT** (universe expansion doesn't help; rare) |

Secondary: per-pair selection histogram to confirm new pairs are actively chosen (not just dead weight).

---

## 10. Timeline estimate

- G-0 (this memo): <1 hour
- G-1 BA fetch: ~10 min wall time (parallel)
- G-1 liquidity audit: ~10 min
- G-2 backtest run: ~20 min (load + features + train + eval for 20 pairs)
- G-3 closure memo: 0.5 day

Total ≈ 1 day excluding any unexpected pair-data issues.

---

## 11. Risks

| Risk | Mitigation |
|------|------------|
| New pairs have wider spreads than majors → bid/ask labels harder to clear → low hit rate on those pairs | Liquidity audit in G-1 filters >5pip pairs; SELECTOR auto-picks the best pair anyway, so dud pairs are simply ignored (no harm) |
| OANDA practice account spreads diverge from live; new pairs more affected | Phase 9.14 paper validation will measure |
| 20× pairs increases compute time linearly | v8/v9 vectorised eval is ~5 sec/fold per 10 pairs → ~10 sec/fold per 20 pairs. Acceptable |
| Per-pair selection frequency table grows large | Cosmetic; output sorted top-20 or bottom-5 only |

---

## 12. Open questions

- **Should we keep 10 pairs as a default in the production runner?** Likely yes — operator can choose universe size as another runtime toggle (similar to Phase 9.15's feature_set toggle). Production wiring lands in Phase 9.14 prep.
- **Is 25 pairs better than 20?** Empirical question for G-3. Diminishing returns past 20 — might not justify the extra compute and operational complexity.
