# Phase 9.15 — Orthogonal features (Phase F) Design Memo

**Status**: Design phase (2026-04-25)
**Predecessor**: Phase 9.13 closed SOFT GO+ at master `043b62a`
**Owner**: くりす
**Related**: `docs/phase9_roadmap.md` §6.17, `docs/design/phase9_13_closure_memo.md`

---

## 1. Why this phase

Phase 9.13 surfaced the binding constraint:

> Layer 1's predict_proba carries no actionable information beyond what its own threshold filter already produces. Risk levers built on it (B-3 meta-labeling, C-1 Kelly, C-2 cap) cannot lift Sharpe without sacrificing trade volume.

Phase 9.15 attacks this directly by giving Layer 1 **information it currently does not see**. The feature set has remained at 32 columns (M1 + MTF + cross-pair) since Phase 9.10. We have ignored several data sources we already collect:

- **bid/ask spread** — used as *label* in B-2, never as *feature*
- **volume** — column exists in JSONL, never read
- **time-of-day** — never encoded
- **regime classification** — Phase 9.7 classifier exists but feeds the Score stage, not the model itself
- **strategy self-feedback** — recent hit rate per pair is computable but absent

Each of these is *orthogonal* to what Layer 1 sees today. Adding them is the cheapest, highest-leverage move available before we move to bigger architectural changes (multi-strategy ensemble, pair expansion).

**Target outcome**: SELECTOR net Sharpe **0.18 → 0.22-0.28** (clears Phase 9.10 GO threshold) AND PnL **6,275 → 9,000-12,500 pip / 9 mo** (vs Phase 9.13 baseline).

---

## 2. Feature additions (13 new columns)

| # | Feature | Computation | Why it's orthogonal |
|---|---------|-------------|----------------------|
| 1 | `spread_now_pip` | `(ask_o - bid_o) / pip_size` | Liquidity proxy; widens before news / weekends |
| 2 | `spread_ma_ratio_20` | `spread_now / spread.rolling(20).mean()` | Anomaly detection; > 1 → unusually wide |
| 3 | `spread_zscore_50` | 50-bar z-score of spread | Regime indicator |
| 4 | `hour_sin` | `sin(2π × hour / 24)` | Cyclic encoding of UTC hour |
| 5 | `hour_cos` | `cos(2π × hour / 24)` | Pair with `hour_sin` for full cyclic |
| 6 | `is_asian` | 0 ≤ UTC hour < 7 | Asian session indicator |
| 7 | `is_london` | 7 ≤ UTC hour < 12 | London-only window |
| 8 | `is_overlap` | 12 ≤ UTC hour < 16 | London/NY overlap (highest volume) |
| 9 | `day_of_week_sin` | `sin(2π × dow / 7)` | Weekly cyclic |
| 10 | `volume_pct_100` | volume's 100-bar percentile rank | Activity regime |
| 11 | `volume_zscore_50` | 50-bar z-score of volume | Anomaly detection |
| 12 | `regime_atr_class` | ATR percentile mapped to {trend, range, high_vol} (one-hot) | Direct regime feature (vs Score-stage usage) |
| 13 | `recent_hit_rate_50` | rolling per-pair hit rate of Layer 1's signals over last 50 fired trades | Self-feedback — Layer 1's own track record per pair |

Total: **32 → 45 features**. Minor risk of overfitting; mitigated by walk-forward + 90-day train window (~91k rows / pair).

---

## 3. Why these specifically (rationale per feature group)

### 3.1 Bid/ask spread (#1-3)

Most likely highest single-feature contribution. The mechanism:

```
Wide spread bar  →  bid_h has to travel further to reach entry_ask + TP
                 →  hit rate structurally lower at wide-spread bars
                 →  Layer 1 should derisk OR pick the rare wide-spread setup that still works
```

We already saw this in Phase 9.10: `compare_multipair_v3_costs.py` showed Sharpe drops linearly with spread (~0.21 per 0.5pip). That linear drop is *structural* — the model literally cannot see when the bar's spread is wide and so cannot adapt. Giving it `spread_now_pip` should let it learn "no_trade when spread is unusual."

### 3.2 Time-of-day (#4-9)

Well-documented FX session statistics:
- **Asian (00-07 UTC)**: low volatility, ranging — momentum signals fail
- **London open (07)**: volatility spike, breakouts work
- **London/NY overlap (12-16)**: highest volume, best fills
- **NY close (20-22)**: trending, but spread widens
- **22-00 UTC**: thin liquidity, false moves

The model can learn these without us hard-coding them — but only if it has the hour as a feature.

### 3.3 Volume (#10-11)

Low-volume bars produce false breakouts at 2-3× the rate of normal bars. The model has access to the close-price changes but not the *quality* of the move (how many participants).

### 3.4 Regime classification (#12)

Phase 9.7 built `ATRRegimeClassifier` but routes its output to the MetaDecider Score stage, not the Layer 1 model. Adding it as a one-hot feature lets the model learn regime-conditional patterns directly.

### 3.5 Recent hit-rate (#13)

Self-feedback loop. If USD/JPY's last 50 Layer 1 signals had 65% hit rate, the model learns "trust this pair more right now." If EUR/GBP's last 50 had 35%, it derisks. This is essentially a Bayesian update on the model's own confidence using recent evidence — and it is **not** redundant with Layer 1's `predict_proba` because that probability is point-in-time per bar, not a running track record.

This is the only feature that requires sequential bookkeeping (per-fold replay to tally Layer 1's signal outcomes). Hence it's split into PR F-2.

---

## 4. PR breakdown

| PR | Scope | Size | Depends |
|----|-------|------|---------|
| **F-0** (this memo) | `docs/design/phase9_15_design_memo.md` | docs only | master `043b62a` |
| **F-1** | `scripts/compare_multipair_v9_orthogonal.py` — features 1-12 (vectorised); per-feature ablation | ≤ 700 lines | F-0 |
| **F-2** | extend F-1 with feature 13 (recent_hit_rate, sequential); ablation | ≤ 250 lines diff | F-1 |
| **F-3** | `docs/design/phase9_15_closure_memo.md` (Go / SOFT GO / NO-GO + per-feature attribution) | docs only | F-2 |

---

## 5. Detailed design — F-1

### 5.1 New BA loader columns

Already loaded in v8 (`bid_o, bid_h, bid_l, bid_c, ask_*`). Just need to expose `bid_o` and `ask_o` for `spread_now_pip`.

### 5.2 Feature computation (vectorised, in `_add_m1_features` extension)

```python
def _add_orthogonal_features(df: pd.DataFrame, instrument: str) -> pd.DataFrame:
    """Phase 9.15/F-1: add 12 orthogonal features (vectorised).

    Recent hit-rate (#13) lives in F-2's sequential pass.
    """
    pip = _pip_size(instrument)
    spread = (df["ask_o"] - df["bid_o"]) / pip
    df = df.copy()

    # 1-3: spread features
    df["spread_now_pip"] = spread
    df["spread_ma_ratio_20"] = spread / spread.rolling(20, min_periods=5).mean()
    df["spread_zscore_50"] = (
        (spread - spread.rolling(50, min_periods=10).mean())
        / spread.rolling(50, min_periods=10).std(ddof=0).replace(0, np.nan)
    )

    # 4-9: time features
    hour = df.index.hour if df.index.name == "timestamp" else df["timestamp"].dt.hour
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    df["is_asian"] = ((hour >= 0) & (hour < 7)).astype(np.int8)
    df["is_london"] = ((hour >= 7) & (hour < 12)).astype(np.int8)
    df["is_overlap"] = ((hour >= 12) & (hour < 16)).astype(np.int8)
    dow = df.index.dayofweek if df.index.name == "timestamp" else df["timestamp"].dt.dayofweek
    df["day_of_week_sin"] = np.sin(2 * np.pi * dow / 7)

    # 10-11: volume features
    vol = df["volume"]
    df["volume_pct_100"] = vol.rolling(100, min_periods=20).rank(pct=True)
    df["volume_zscore_50"] = (
        (vol - vol.rolling(50, min_periods=10).mean())
        / vol.rolling(50, min_periods=10).std(ddof=0).replace(0, np.nan)
    )

    # 12: regime class (from ATR percentile)
    atr = df["atr_14"]
    atr_pct = atr.rolling(200, min_periods=50).rank(pct=True)
    df["regime_trend"] = (atr_pct < 0.4).astype(np.int8)
    df["regime_range"] = ((atr_pct >= 0.4) & (atr_pct < 0.7)).astype(np.int8)
    df["regime_high_vol"] = (atr_pct >= 0.7).astype(np.int8)
    return df
```

### 5.3 Feature_cols update

Add new columns to feature_cols, keep existing exclusions for raw OHLC and labels.

### 5.4 Ablation grid

Run with subsets of features to attribute Sharpe lift:

```
Cell 1: v5 baseline                            → Sharpe 0.160
Cell 2: + spread features (1-3)                → measure
Cell 3: + time features (4-9)                  → measure
Cell 4: + volume features (10-11)              → measure
Cell 5: + regime feature (12)                  → measure
Cell 6: ALL features 1-12                       → measure
```

Each cell uses the same training data + same model architecture, only the feature_cols list differs. Internal sweep design (one load + train per fold, vary feature_cols across cells).

### 5.5 CLI

```
--features-bundle BUNDLE   # one of: baseline, spread, time, volume, regime, all
                           # default: all
```

---

## 6. Detailed design — F-2

### 6.1 Recent hit-rate computation

Sequential per-pair tally during walk-forward eval. At each test bar i for pair P:

```
1. Look at the last 50 Layer 1 signals fired for P (in time order from
   the start of this fold, including the training-set predictions if
   we want a warm start).
2. For each of those 50 signals, check the actual triple-barrier label:
     hit = 1 iff (signal == long  AND label == 1)
                 OR (signal == short AND label == -1)
3. recent_hit_rate_P = sum(hit) / 50
4. Use as the value of the `recent_hit_rate_50` feature for bar i.
```

### 6.2 Implementation note

This requires re-running Layer 1 on the training window to seed the rolling buffer (otherwise the first 50 test bars have no hit-rate history). Cost: one additional `predict_proba` pass per pair per fold. With the v8 vectorised path, that's ~1-2 sec/fold, negligible.

### 6.3 Ablation cell

```
Cell 7: ALL features (1-12) + recent_hit_rate (13)  → measure
```

If F-2 lifts Sharpe substantively over F-1 cell 6, recent_hit_rate is the key. If not, the static features did the heavy lifting and we can deprioritise self-feedback.

---

## 7. Success criteria for closure memo

| Cell condition | Verdict |
|---|---|
| Best F-1+F-2 cell SELECTOR net Sharpe ≥ 0.20 AND PnL > 6,000 pip | **GO** → unblock Phase 9.11 |
| Best cell 0.15 ≤ Sharpe < 0.20 | **SOFT GO** → continue with Phase 9.16/9.17/9.18 |
| Best cell < 0.15 OR PnL collapses below v5 baseline | **NO-GO** → orthogonal features didn't help, reconsider scope |

Secondary:
- **Per-feature attribution**: which of the 13 features contributed most? This guides whether to invest in further feature engineering.
- **PnL preservation**: unlike Phase 9.13 risk levers, Phase 9.15 features should NOT trade PnL for Sharpe — they should lift both.

---

## 8. Out of scope (deferred to later phases)

| Item | Deferred to |
|------|-------------|
| Pair universe expansion | Phase 9.16 |
| Multi-strategy ensemble | Phase 9.17 |
| Asymmetric TP/SL | Phase 9.18 |
| Tick / DOM data | Phase 11 |
| Sentiment / news NLP | Phase 12 |
| Production wiring (`feature_service.py`) | After Phase 9.15 produces full GO |
| OANDA paper run | Phase 9.14 |
| 3+ yr robustness | Phase 9.11 (BLOCKED on Phase 9.15+ GO) |

---

## 9. Timeline estimate

- F-0 (this memo): <1 hour
- F-1 implementation + ablation run: 1 day (~6 ablation cells × 6 min ≈ 40 min wall-time)
- F-2 implementation + run: 0.5 day
- F-3 closure memo: 0.5 day

Total ≈ 2 days excluding any unexpected issues.

---

## 10. Risks

| Risk | Mitigation |
|------|------------|
| Overfitting (32 → 45 features) | Walk-forward + 90-day train; per-feature ablation surfaces noise vs signal |
| Spread features drift between practice/live data | Phase 9.14 paper run will measure |
| `recent_hit_rate_50` introduces leakage if not careful | Strict per-fold sequential tally; test pin in F-2 |
| Time features add noise (model overfits hour patterns) | Ablation cell 3 surfaces this |
