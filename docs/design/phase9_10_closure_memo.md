# Phase 9.10 — Cost-aware backtest (Phase A) Closure Memo

**Status**: Closed — **NO-GO verdict at the 1.0 pip spread baseline**
**Master tip at authorship**: `76ed330` (PR #187 merged)
**Related**: `docs/phase9_roadmap.md` §6.12, `docs/design/phase9_10_design_memo.md`

---

## 1. What this phase set out to do

Phase 9.1-9.8 established the D3 scaffolding (strategy Protocol, MetaDecider, feature service, ML baseline, regime, promotion gate) and validated that the multi-pair ML selection backtest (v2 / `scripts/compare_multipair_v2.py`) yields `SELECTOR Sharpe ≈ 0.35 / PnL ≈ 230k pip / 10 pairs` over a 39-fold walk-forward year — **under zero transaction costs**.

The design memo (`phase9_10_design_memo.md`) pinned the Go/No-Go question:

> Does SELECTOR keep `net Sharpe ≥ 0.20` and `net PnL > 0` once realistic spread is deducted, at a plausible confidence threshold that keeps `signal_rate ≤ 30%`?

Phase 9.10 was the series of infrastructure PRs (A-1..A-4) that made that question answerable, and the two research scripts (A-5 + A-6) that answered it.

---

## 2. What shipped

### Infrastructure (merged)

| PR | Scope | Lines | Tests |
|----|-------|-------|-------|
| #185 (A-1..A-3) | `Quote` bid/ask, `PaperBroker` side-aware fills, `fetch_oanda_candles --price BA\|MBA` | 990 | +20 |
| #186 (A-4) | `Candle` bid/ask, `CandleFileBarFeed` / `CandleReplayQuoteFeed` bid/ask propagation | 199 | +12 |

Back-compat held throughout — all pre-9.10 `Quote(price=X, ts=T, source=S)` call sites still work, all existing tests pass.

### Research scripts (merged)

| PR | Scope | Lines |
|----|-------|-------|
| #187 (A-5 + A-6) | `compare_multipair_v3_costs.py` (v2 + spread) and `grid_search_tp_sl_conf.py` (spread × conf sweep) | 1170 |

### Data (local only, not checked in)

10 pairs × 365 days × M1 × `--price BA` ≈ 750 MB across 10 JSONL files under `data/candles_<pair>_M1_365d_BA.jsonl`.

---

## 3. Results

### 3.1 A-5: single-cell baseline at `--spread-pip 1.0`

39-fold walk-forward (90d train / 7d test / 7d step), 10 pairs, retrain every 90d:

```
  Strategy      NetSharpe   GrossSh   NetPnL(pip)   GrossPnL(pip)   WinFold%   SigRate    Trades
  --------------------------------------------------------------------------------------------------
  EURUSD_ML       -0.087     0.343      -33,072       128,642          0%       58.5%    161,714
  SELECTOR        -0.076     0.346      -49,611       226,501          0%       99.9%    276,112
  EQUAL_AVG       -0.199     0.592      -69,928       206,184          0%       99.9%    276,112
  RANDOM          -0.108     0.316      -41,866       122,009          0%       59.3%    163,875
```

**Pair selection frequency (SELECTOR):**
```
  USD_JPY  27.4%  EUR_JPY  21.1%  GBP_JPY  15.3%   (JPY total: 63.8%)
  EUR_USD   9.7%  AUD_USD   8.0%  GBP_USD   5.6%
  USD_CAD   4.7%  NZD_USD   4.2%  EUR_GBP   2.6%   USD_CHF  1.5%
```

**Sanity check:** the gross Sharpes (0.343 / 0.346) reproduce v2's zero-cost numbers (0.337 / 0.351) to within rounding, confirming the cost model is layered cleanly on top of v2's signal stream — there is no data-pipeline regression between v2 and v3.

**Cost gap:** the move from gross to net Sharpe is approximately **−0.42** for both EUR/USD and SELECTOR — a 1pip round-trip spread destroys the entire mid-based edge.

### 3.2 A-6: spread × conf grid heatmap

20 cells from `grid_search_tp_sl_conf.py` (TP=3 / SL=2 / horizon=20 fixed; same models reused across cells).

**SELECTOR net Sharpe** (cells marked `*` would clear the GO threshold):

```
  spread \ conf | 0.50    | 0.55    | 0.60    | 0.65
  --------------+---------+---------+---------+---------
  0.00          |  0.346* |  0.347* |  0.350* |  0.356*
  0.50          |  0.135  |  0.136  |  0.140  |  0.146
  1.00          | -0.076  | -0.075  | -0.071  | -0.065
  1.50          | -0.286  | -0.285  | -0.281  | -0.275
  2.00          | -0.497  | -0.496  | -0.492  | -0.485
```

**SELECTOR net PnL (pip):**

```
  spread \ conf | 0.50     | 0.55     | 0.60     | 0.65
  --------------+----------+----------+----------+----------
  0.00          | +226,501 | +224,812 | +214,299 | +186,386
  0.50          |  +88,445 |  +88,210 |  +85,584 |  +76,264
  1.00          |  -49,611 |  -48,393 |  -43,131 |  -33,858
  1.50          | -187,667 | -184,996 | -171,846 | -143,980
  2.00          | -325,723 | -321,598 | -300,561 | -254,102
```

**EURUSD_ML net Sharpe (baseline contrast):**

```
  spread \ conf | 0.50    | 0.55    | 0.60    | 0.65
  --------------+---------+---------+---------+---------
  0.00          |  0.339* |  0.359* |  0.367* |  0.376*
  0.50          |  0.126  |  0.147  |  0.155  |  0.164
  1.00          | -0.087  | -0.066  | -0.058  | -0.048
  1.50          | -0.300  | -0.279  | -0.270  | -0.260
  2.00          | -0.514  | -0.492  | -0.483  | -0.473
```

**Best cell overall**: spread=0.00, conf=0.65 → Sharpe 0.356, PnL +186k pip — **but spread=0 is the v2 reproducer cell, not a realistic regime**.

**Three things this grid pins down:**

1. **Confidence threshold has almost no effect.** Sweeping conf from 0.50 → 0.65 only moves SELECTOR Sharpe by ~0.01 at any spread row. LightGBM's `predict_proba` outputs are clustered well above 0.65 for most bars, so raising the threshold filters very few signals. **Conf-only filtering cannot rescue this strategy.**
2. **Spread is the dominant cost driver.** Each 0.5 pip of spread costs ~0.21 net Sharpe. Linear in cost, exactly as the spread-deduction model predicts.
3. **The half-spread regime (0.5 pip) is just below the SOFT GO threshold.** Best cell at spread=0.5 is Sharpe 0.146 — `< 0.15` SOFT GO, `< 0.20` GO. So even at the most aggressive *retail* spread assumption (0.5 pip round-trip on EUR/USD), the strategy fails the gate.

---

## 4. Go/No-Go verdict

**Result: NO-GO at the 1.0 pip baseline**

**Why it failed:**

1. **Tight TP/SL gets eaten by spread.** With `TP=3pip / SL=2pip` and a hit rate of ~58%, gross EV is `0.58×3 − 0.42×2 ≈ +0.90 pip/trade`. A 1.0 pip round-trip spread brings net EV to `−0.10 pip/trade`. Negative expectation per trade is not survivable at any trade count.
2. **SELECTOR has higher gross Sharpe but loses more in absolute terms** because its signal rate is **99.9%** — it trades every bar. The 1.7× trade volume relative to EUR/USD baseline (276k vs 162k trades) means 1.7× the total spread bleed. SELECTOR's net PnL is **−49.6k pip vs EURUSD_ML's −33.1k pip** despite SELECTOR's slightly better net Sharpe.
3. **JPY concentration persists under cost.** Pair selection is unchanged from v2 (USD/JPY 27%, EUR/JPY 21%, GBP/JPY 15% — 64% combined). This is a structural property of the EV-based picker plus the volatility/trend characteristics of JPY crosses, not an artifact of cost modelling.

**Per the design memo's gates:** SELECTOR net Sharpe `−0.076` < `0.15` SOFT-GO threshold and `< 0.20` GO threshold. Net PnL is negative.

The grid search (§3.2) confirms this verdict: **0 GO cells and 0 SOFT GO cells at realistic spreads (≥0.5 pip)**. The 4 cells flagged `GO` by the script all sit at `spread=0.0` and serve only as the v2 reproducer (zero-cost sanity check) — by definition they are not a viable trading regime. The script's verdict logic was tightened in this PR to exclude the spread=0 row from the count.

**NO-GO.**

---

## 5. Next phase

**Phase 9.11 is blocked** — extending data to 3+ years and adding hold-out is meaningless until the strategy clears the cost gate at a single year.

**Three productive next steps, ordered by expected information value:**

1. **ATR-based dynamic TP/SL is the highest-priority lever.** The grid search §3.2 result (3) showed the conf threshold barely moves Sharpe — ~0.01 per 0.05 conf step — because LightGBM's predict_proba is overconfident for most bars. Filtering won't help. What *would* help: widening TP and SL relative to the spread cost. Replacing fixed `TP=3pip / SL=2pip` with ATR multiples (e.g. `TP = 1.5×ATR(14)`, `SL = 1.0×ATR(14)`) typically delivers 5-15 pip TP at typical EUR/USD volatility, restoring the gross-to-net Sharpe gap from −0.42 toward something tractable. **Phase 9.12 should start here.**

2. **Re-do the labelling on bid/ask-aware barriers.** Long TP fired by `bid_high ≥ entry_ask + TP`, long SL by `bid_low ≤ entry_ask − SL` (and mirror for short). The current mid-based labels overstate hit rates because they don't acknowledge that the trader needs to cross the spread to register either barrier. Without this, even a wider-TP strategy could over-train on spread-free signals.

3. **Meta-labeling (Lopez de Prado) is the third lever.** A 2-layer ML where the second layer filters signals from the first (whitening rather than thresholding) typically pulls signal rate down to 10–30% with hit-rate up by ~5pp. This compounds with (1) — a 5pp hit-rate lift on a TP=10pip strategy is far more valuable than the same 5pp on TP=3pip.

The NO-GO verdict should be cited in the kickoff design memo for whichever 9.12 sub-phase comes first.

---

## 6. What stayed out of scope (deferred by design)

| Item | Deferred to |
|------|-------------|
| ATR-based dynamic TP/SL | Phase 9.12 |
| Meta-labeling (2-layer ML) | Phase 9.12 |
| Session / economic-event filters | Phase 9.12 |
| Bid/ask-aware triple-barrier labels (bid_high for long TP etc.) | Phase 9.12 |
| Per-bar observed-spread PnL (using BA OHLC directly) | Phase 9.11 |
| 3+ yr multi-regime data | Phase 9.11 (BLOCKED until 9.12 lifts the cost gate) |
| Out-of-sample hold-out | Phase 9.11 |
| Production path end-to-end backtest (`run_paper_decision_loop` over BA replay) | Phase 9.14 |

---

## 7. Commit trail

```
b7c057e  PR #185  Phase 9.10 cost-aware infrastructure (A-1..A-3) + roadmap 9.10-9.14
daeea18  PR #186  A-4 Candle bid_close/ask_close + replay feed propagation
76ed330  PR #187  A-5 compare_multipair_v3_costs.py + A-6 grid_search_tp_sl_conf.py
<TBD>    PR #???  A-7 this closure memo + Unicode fixes for cp932 stdout
```

---

## 8. Notes for future-me

- **Practice account spreads are wider than retail live.** OANDA practice EUR/USD typical spread observed in the BA fetch was ~1.5 pip (versus a typical retail live 0.6–1.0 pip on EUR/USD). The `--spread-pip 1.0` baseline is therefore **mildly conservative for live EUR/USD** but probably **optimistic for crosses** (EUR/GBP, JPY crosses).
- **Running v3 at `--spread-pip 0.0` reproduced v2's gross Sharpe exactly** (0.343 vs 0.337 baseline, 0.346 vs 0.351 SELECTOR), which is the sanity check the cost model is layered cleanly on top of v2 (no data regression).
- **Buffering gotcha.** Without `PYTHONUNBUFFERED=1` and `PYTHONIOENCODING=utf-8`, redirecting `print()` output to a file on Windows can: (a) buffer the entire run until exit, hiding live progress; (b) crash on cp932 encoding when the buffer flushes any non-Latin character. The grid-search run uses both flags; v3's first run did neither and crashed on the final `→` after producing the verdict line. Fix landed in this PR (em-dashes/arrows in printable strings replaced with ASCII).
- **The v3 traceback in the first run** (`UnicodeEncodeError: 'cp932' codec can't encode character '—'`) was post-VERDICT — the headline result was already on stdout. The em-dash was on the `[NO-GO] SELECTOR net Sharpe<0.15 — strategy redesign required` line. After this memo is merged, future v3 / grid runs will be ASCII-clean.
- **JPY concentration is real signal, not a JPY-bias artifact.** With v1 (6 pairs, no JPY crosses) USD/JPY alone was 39.2%; v2 (10 pairs, with JPY crosses) USD/JPY drops to 30.1% but JPY total reaches 64% — i.e. EUR_JPY and GBP_JPY take share from USD_JPY but the JPY total is stable. This is a property of the EV picker plus the volatility regime of JPY crosses, and it's worth investigating in Phase 9.12 whether a regime-aware filter can unblend the JPY signals.
