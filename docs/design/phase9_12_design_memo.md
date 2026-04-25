# Phase 9.12 — Model quality (Phase C) Design Memo

**Status**: Design phase (2026-04-25)
**Predecessor**: Phase 9.10 closed NO-GO at master `17d00c7`
**Owner**: くりす
**Related**: `docs/phase9_roadmap.md` §6.14, `docs/design/phase9_10_closure_memo.md`

---

## 1. Why this phase

Phase 9.10 grid search (`grid_search_tp_sl_conf.py`) showed three things that this phase must address head-on:

1. **Confidence threshold barely moves Sharpe** (~0.01 per 0.05 step). LightGBM `predict_proba` is overconfident for most bars — most "signals" already exceed 0.65 confidence. Filtering by threshold cannot rescue the strategy.
2. **Spread is the dominant cost driver** — linear, ~0.21 Sharpe per 0.5pip. The fixed `TP=3pip / SL=2pip` is the binding constraint: at low ATR it's below noise, at high ATR it caps the upside.
3. **0.5pip is the cliff edge.** Even at the most aggressive retail spread assumption, best-cell Sharpe is 0.146 — just below the 0.15 SOFT GO threshold. So tweaking conf alone won't get us across.

Phase 9.12's job: change *what the strategy is shooting for* so the gross-to-net Sharpe gap shrinks from −0.42 to something tractable, then re-run the cost gate.

**Phase 9.11 (3+ year robustness) stays BLOCKED** until 9.12 produces a strategy that clears the 1pip cost gate.

---

## 2. Three levers, in priority order

### 2.1 Lever B-1 (highest priority): ATR-based dynamic TP/SL

**What:** replace fixed `TP=3pip` / `SL=2pip` with multiples of the recent ATR:

```
TP = TP_mult × ATR(14)
SL = SL_mult × ATR(14)
```

Default candidate: `TP_mult=1.5`, `SL_mult=1.0` → at typical EUR/USD ATR(14) ≈ 5–10 pip on M1, that's TP ≈ 7.5–15 pip, SL ≈ 5–10 pip. Gross EV becomes `0.58 × 7.5 − 0.42 × 5 ≈ +2.25 pip/trade` instead of `+0.90`. After 1pip spread: net `+1.25 pip/trade` instead of `−0.10`. **2.5× headroom.**

**Why it should help (assumption to test):**
- The triple-barrier label changes with TP/SL → models retrain on different objective → different signals
- Hit rate may drop (longer TP horizon → more chance to revert before reaching it)
- But the per-trade EV-to-spread ratio improves enough that even a lower hit rate clears the gate

**Risk:** if hit rate drops too far (e.g. from 58% to 45%), the EV improvement is wiped out. Grid search will sweep `(TP_mult, SL_mult)` to find the maximum.

### 2.2 Lever B-2: bid/ask-aware triple-barrier labels

**What:** replace mid-based barrier check with side-aware bid/ask check.

For a **long** trade:
```
Entry  = ask_o[t+1]                        (next bar's ask open)
TP hit ⇔ bid_h[t+k] >= entry + TP          (some bar k in horizon)
SL hit ⇔ bid_l[t+k] <= entry − SL          (some bar k in horizon)
```

For a **short** trade, mirror: entry at `bid_o`, TP/SL checked against `ask_l` / `ask_h`.

**Why it matters:**
- The current mid-based label says "the mid moved TP pips" but the trader can only register the move by crossing the spread. With the spread-aware label, the same move in mid registers as a hit *only if* it cleared the spread on the relevant side.
- This will *lower* the hit rate (some apparent wins won't actually get filled) but the labels then describe what a trader can actually capture. Models trained on these labels are then betting on real-world events, not mid-only ones.

**Risk:** without B-1, this just makes the gate even harder to clear (tighter labels with the same spread cost). Therefore B-2 must compose on top of B-1, not replace it.

### 2.3 Lever B-3 (optional, deferred unless B-1+B-2 still misses): Meta-labeling

**What:** Lopez de Prado-style 2-layer ML.

- Layer 1: existing LightGBM with the new bid/ask-aware labels (from B-2). Output: directional signal {long, short, no_trade}.
- Layer 2: a second LightGBM that takes Layer 1's output + the same features as additional inputs, and predicts a binary `keep/drop`. Trained on whether each Layer 1 signal would be profitable.

**Effect:** drives signal rate from 99.9% (current) toward 10–30% by *whitening* primary signals rather than thresholding them. The retained signals tend to have higher hit rate and smaller variance.

**Why deferred:** the cleanest measurement of B-3's contribution requires B-1+B-2 to be in place first. Skipping this step until needed avoids spending PRs on work that may turn out unnecessary (if B-1+B-2 already clears the gate).

---

## 3. PR breakdown

| PR | Scope | Size | Depends |
|----|-------|------|---------|
| **B-0** (this memo) | `docs/design/phase9_12_design_memo.md` | docs only | master `17d00c7` |
| **B-1** | `scripts/compare_multipair_v4_atr.py` — ATR-based TP/SL, single-cell run + sweep over `(TP_mult, SL_mult)` | ≤700 lines | B-0 |
| **B-2** | extend B-1 with bid/ask-aware barrier check (and observed per-bar spread cost from BA OHLC) | ≤300 lines diff | B-1 |
| **B-3** *(if needed)* | meta-labeling layer + re-run | ≤500 lines | B-2 |
| **B-4** | `docs/design/phase9_12_closure_memo.md` (Go / SOFT GO / NO-GO verdict) | docs only | B-2 (or B-3) |

---

## 4. Detailed design — B-1 (ATR-based dynamic TP/SL)

### 4.1 Labelling change

```python
def _add_labels_atr(df: pd.DataFrame, horizon: int,
                   tp_mult: float, sl_mult: float) -> pd.DataFrame:
    closes = df["close"].to_numpy()
    atr = df["atr_14"].to_numpy()  # already computed by _add_m1_features
    n = len(closes)
    labels: list[int | None] = [None] * n
    for i in range(n - horizon):
        if pd.isna(atr[i]) or atr[i] <= 0:
            continue
        tp = tp_mult * atr[i]
        sl = sl_mult * atr[i]
        window = closes[i + 1 : i + horizon + 1]
        tp_m = window >= closes[i] + tp
        sl_m = window <= closes[i] - sl
        # ... same triple-barrier resolution as v3
```

### 4.2 PnL change

For each trade, the cost-aware PnL also scales with ATR at entry:

```python
def _gross_pnl_pips_atr(sig: str, label: int,
                       tp_mult: float, sl_mult: float,
                       atr_at_entry: float, pip_size: float) -> float | None:
    if sig == "no_trade":
        return None
    tp_pip = tp_mult * atr_at_entry / pip_size
    sl_pip = sl_mult * atr_at_entry / pip_size
    if sig == "long":
        return tp_pip if label == 1 else (-sl_pip if label == -1 else 0.0)
    return tp_pip if label == -1 else (-sl_pip if label == 1 else 0.0)
```

Note: per-trade PnL is now *variable* — high-vol bars produce wider winners and losers than low-vol bars. The Sharpe calculation still works on the resulting per-trade pip series, so no metric change is needed.

### 4.3 Sweep grid

```
TP_mult ∈ {1.0, 1.5, 2.0, 2.5, 3.0}        (5 points)
SL_mult ∈ {0.5, 1.0, 1.5}                   (3 points)
spread_pip ∈ {0.0, 0.5, 1.0, 1.5}          (4 points)
conf_threshold = 0.50 (fixed; conf has minimal effect per 9.10)
```

Total: 60 cells. Each `(TP_mult, SL_mult)` combination requires retraining (different labels), so 15 train passes (5 × 3 = 15 distinct label schemes). Per train pass = ~30 model trains × ~5s each = 2.5 minutes; total train time ≈ 38 min. Per-cell evaluation reuses the same trained model across the 4 spread points (4 evaluations per train pass, like 9.10's grid). Total wall time ≈ 1 hour.

### 4.4 Go/No-Go gate (carries from 9.10)

Same thresholds: `SELECTOR net Sharpe ≥ 0.20 AND net PnL > 0` at any cell with `spread_pip ≥ 0.5`.

---

## 5. Detailed design — B-2 (bid/ask-aware barriers)

### 5.1 Data requirement

Already satisfied — `data/candles_<pair>_M1_365d_BA.jsonl` from Phase 9.10 carries `bid_h / bid_l / ask_h / ask_l` per bar.

### 5.2 Labelling change

```python
def _add_labels_atr_bidask(df: pd.DataFrame, horizon: int,
                          tp_mult: float, sl_mult: float) -> pd.DataFrame:
    """Side-aware triple barrier on bid/ask high/low."""
    bid_h = df["bid_h"].to_numpy()
    bid_l = df["bid_l"].to_numpy()
    ask_h = df["ask_h"].to_numpy()
    ask_l = df["ask_l"].to_numpy()
    ask_o = df["ask_o"].to_numpy()  # entry price for long
    bid_o = df["bid_o"].to_numpy()  # entry price for short
    atr = df["atr_14"].to_numpy()
    n = len(df)
    long_label  = [None] * n
    short_label = [None] * n
    for i in range(n - horizon):
        if pd.isna(atr[i]) or atr[i] <= 0:
            continue
        tp = tp_mult * atr[i]; sl = sl_mult * atr[i]

        # Long: enter at next bar's ask open, check bid_h/bid_l in horizon
        entry_long = ask_o[i + 1]
        bh = bid_h[i + 1 : i + 1 + horizon]
        bl = bid_l[i + 1 : i + 1 + horizon]
        long_tp = bh >= entry_long + tp
        long_sl = bl <= entry_long - sl
        long_label[i] = _resolve_triple_barrier(long_tp, long_sl)

        # Short: enter at next bar's bid open, check ask_l/ask_h in horizon
        entry_short = bid_o[i + 1]
        ah = ask_h[i + 1 : i + 1 + horizon]
        al = ask_l[i + 1 : i + 1 + horizon]
        short_tp = al <= entry_short - tp
        short_sl = ah >= entry_short + sl
        short_label[i] = _resolve_triple_barrier(short_tp, short_sl)
    df = df.copy()
    df["long_label"] = long_label
    df["short_label"] = short_label
    return df
```

This produces **two separate labels** per bar (one for each direction). The existing 3-class classifier (`{-1, 0, 1}` for `{SL, timeout, TP}`) is still used, but now the model is trained on whichever direction has a defined label. (One simple framing: collapse to a single label = `+1` if `long_label==+1`, `-1` if `short_label==+1`, `0` if both timeout, mixed otherwise = `0`.)

### 5.3 PnL change

Same as B-1 but the *gross* PnL now reflects bid/ask trip:
- Long win: `pnl = (entry + TP) − entry = TP` — but you already paid the spread implicitly because you entered at ask
- Long loss: `pnl = (entry − SL) − entry = −SL`
- Spread cost is **embedded** in the labelling now (entry at ask, TP/SL checked against bid). So we no longer subtract `spread_pip` from gross PnL — it's already accounted for.

The grid sweeps then become:
- `(TP_mult, SL_mult)` only — no `spread_pip` dimension because spread is built into the labels.
- We still report at fixed-spread *additional* slippage (e.g. 0.2pip) on top, since real fills include slippage beyond bid/ask.

---

## 6. Composition order and what gets reported

1. **B-1 alone:** answers "does ATR scaling alone get us to GO?" — fastest win path. If yes, can short-circuit.
2. **B-1 + B-2:** strict realism — labels and PnL both spread-aware, only slippage on top. The closure memo's verdict comes from this.
3. **B-3 (only if B-1+B-2 misses):** drives signal rate down to 10–30%. Avoids spending PR work if not needed.

---

## 7. Out of scope (deferred)

- Session / news filters → Phase 9.12 secondary scope only if B-1..B-3 still misses. Otherwise → Phase 9.13 with risk management.
- Ensemble (LightGBM + XGBoost + CatBoost) → Phase 9.13.
- 3+ year data + hold-out → Phase 9.11 (still BLOCKED until this phase clears the gate).
- Production code changes (`MLDirectionStrategy`, `feature_service.atr_14`) → only after this phase produces a GO; same pattern as 9.10 (research scripts now, production wiring later).

---

## 8. Success criteria for closure memo

The closure memo (B-4) reports verdict against the same Phase 9.10 thresholds:

| Cell condition | Verdict |
|----------------|---------|
| ≥1 cell with `spread ≥ 0.5pip` AND `net Sharpe ≥ 0.20` AND `net PnL > 0` | **GO** → unblock Phase 9.11 |
| ≥1 cell with `spread ≥ 0.5pip` AND `0.15 ≤ net Sharpe < 0.20` | **SOFT GO** → consider Phase 9.13 risk lever first |
| All cells with `spread ≥ 0.5pip` have `Sharpe < 0.15` or `PnL < 0` | **NO-GO** → 9.11 still blocked; reconsider scope |

---

## 9. Timeline estimate

- B-0 (this memo) + push: <1 hour
- B-1 implementation + smoke run: 1 day
- B-1 grid sweep run: ~1 hour wall time
- B-2 implementation: 0.5 day
- B-2 grid sweep run: ~1 hour wall time
- B-3 (if needed): 1 day
- B-4 closure memo: 0.5 day

Total ≈ 3–4 days excluding any No-Go pivot.
