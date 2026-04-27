# Sharpe Improvement Brief — FX AI Trading System

**Audience:** external reviewer (human or AI) asked to suggest novel ideas for lifting Sharpe ratio above the system's current ~0.158 per-trade ceiling.
**Date:** 2026-04-27.
**Authors of underlying work:** Claude Code agent + repo owner.
**Repo state at brief time:** master tip `fd1d2f1` plus open PRs #227–#231 with eval results captured below.

---

## 0. The single question we want help with

> **What is the most likely path to push the backtest's per-trade SELECTOR Sharpe from 0.158 to ≥ 0.20 (and ideally to ≥ 0.30)?** Equivalently in annualized daily terms: from a likely ~1-3 to a robust ≥ 5.

We have empirically falsified ~10 distinct ideas already (each with full 9-month walk-forward eval). Section 9 lists what we have NOT yet tried.

---

## 1. System architecture (concise)

- **Universe:** 20 FX pairs covering 8 currencies (USD/EUR/GBP/JPY/AUD/NZD/CAD/CHF; majors + the 12 most-liquid crosses).
- **Timeframe:** 5-minute bars (m5). Some features re-sample to m15 / h1 / 4h / D / W.
- **Data span:** 2025-04-24 → 2026-04-24 (1 year). 90-day rolling train, 7-day rolling test, 39 walk-forward folds.
- **Per-pair model:** LightGBM 3-class classifier (P_sl / P_timeout / P_tp).
- **Label:** triple-barrier with bid/ask-aware PnL realization (Phase 9.12), default `tp_mult=4 × ATR`, `sl_mult=4 × ATR`, horizon=12 bars.
- **Per-pair signal:** classify based on `max(p_tp, p_sl) ≥ ml_threshold`; sign from which barrier is more probable.
- **SELECTOR:** at each m5 bar, take the highest-confidence (pair × strategy) candidate (K=1) or argpartition top-K (K=2/3/5).
- **Production runtime:**
  - `scripts/run_paper_decision_loop.py` — alpha decision logger (broker call deferred).
  - `scripts/run_live_loop.py` — M9 exit gate cadence on OANDA demo/live.
  - `scripts/run_volume_mode.py` — alpha-independent USD/JPY churn for OANDA GOLD volume requirement.
  - `src/fx_ai_trading/services/feature_service.py` — production FeatureService with opt-in `mtf` and `vol` groups (FEATURE_VERSION v3).

### Causal invariants enforced

- `FeatureService.build()` filters candles to `timestamp < as_of_time` (strict <).
- `_compute_mtf_features` (production) uses pure-Python bucket aggregation; no `pandas.resample` lookahead.
- v19 backtest (`compare_multipair_v19_causal.py`) fixed a `_add_multi_tf_extended_features` lookahead bug that had inflated Phase 9.X-B's claimed +mtf Sharpe from a true 0.158 to 0.174 (~9% inflation).

---

## 2. Sharpe definition (so reviewer interprets numbers correctly)

```python
def _sharpe(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)  # population variance
    return mu / sqrt(var) if var > 0 else 0.0
```

- **Per-trade Sharpe** (the headline number we report): `values` = per-trade NET PnL in pips.
- **No annualization** (not multiplied by √N).
- **No risk-free rate** (FX-neutral assumption).
- **Phase 9.X-K (just added):** also report **annualized daily Sharpe** = `mean(daily_pct_return) / std × √252` based on running equity curve.

Per-trade 0.158 ≈ annualized 1-3 (depending on trade-correlation structure). Phase 9.11 robustness gate target = per-trade ≥ 0.20.

---

## 3. Production-current Sharpe (the anchor)

Phase 9.X-E v19 causal `+mtf` 20-pair `lgbm_only` SELECTOR @ K=3:

| Metric | Value |
| --- | --- |
| Per-trade Sharpe | **0.158** |
| Net PnL (9 mo) | 11,414 pip |
| Trades | 13,608 |
| MaxDD | 240 pip |
| DD%PnL | 2.1% |
| `--feature-groups mtf` is the production wire (PR #223 merged) |

`+vol` cell ties on Sharpe (0.160) but loses on PnL (10,385). Production candidate retained as alternative (`--feature-groups vol`, PR #226 merged).

---

## 4. The single most important pattern observed (5× confirmed)

Across 5 distinct phases (9.17, 9.17b, 9.19, 9.X-A, 9.X-C/M-1), every attempt to **increase trade volume** caused **per-trade EV to collapse** by roughly the same factor. Specifically:

| Phase | What was added | Trade rate | Per-trade EV | Sharpe |
| --- | --- | --- | --- | --- |
| 9.16 baseline | — | 1.0× | 1.0× | 0.149 |
| 9.17 ensemble (MR/BO + lgbm) | 13× more candidates | **15×** | **0.07×** | 0.039 |
| 9.17b conf threshold | filter to high-conf | 0.7× | 1.05× | 0.155 |
| 9.19 Top-K=2 (naive) | 2× picks/bar | 1.0× (per cand.) | 0.92× | 0.157 |
| 9.X-A regression labels | continuous target | 4.5× | 0.21× | 0.092 |
| 9.X-C LSTM Mode A | LSTM replaces LGBM | 7.7× | 0.13× | 0.061 |

**Hypothesized cause:** the model has fixed predictive power; expanding the candidate pool only adds candidates of roughly the same edge distribution, but trade selection logic over-samples them (more trades fired) and the PnL-per-trade dilutes proportionally.

The *only* lever that escaped this pattern in the backtest:

- **Phase 9.X-B `+mtf` features** (v19 causal): trade rate ~constant (-1.5%), per-trade EV preserved, Sharpe 0.149 → 0.158.

That is, **adding features that re-rank existing high-conf trades better** lifted Sharpe slightly, but adding more candidates / more model classes / lower thresholds did not.

---

## 5. Full phase verdict table (chronological, 9.10 onwards)

GO = adopted. PARTIAL = some lift but not decisive. NO = rejected. ❌ = current production runs without it.

| Phase | Lever | Verdict | Sharpe / metric | Notes |
| --- | --- | --- | --- | --- |
| 9.10 | Cost analysis | observation | gross→net gap quantified | revealed why earlier "Sharpe 0.35 gross" became "-0.076 net" |
| 9.12 B-2 | Bid/ask aware labels | **GO** ★ | Sharpe 0.16 from -0.08 | decisive; production-default |
| 9.13 C-3 | Kill switches | **GO** | small additive | minor risk control |
| 9.15 F | Spread + RH bundle | **GO** | PnL +13% | feature engineering |
| 9.16 | 20-pair expansion | **GO** | PnL +20% | universe doubling |
| 9.17 G-3 | Ensemble (MR/BO + lgbm) | NO | Sharpe 0.039 (collapse) | trade-rate explosion #1 |
| 9.17b | Confidence threshold | NO | +0.005 Sharpe lift | per-trade EV is binding constraint |
| 9.18 H | Asymmetric TP/SL bucket | NO | low-bucket drag | bucket below mean drags down EV |
| 9.19 J-1 | Top-K=2 SELECTOR | PARTIAL GO | PnL +25%, Sharpe 0.165 | sqrt(K) lift didn't materialize |
| 9.X-A | Regression labels | NO | Sharpe 0.092 (best of 16 cells) | label class is not the lever |
| 9.X-B | Alt features (vol/mtf/moments/all) | PARTIAL GO+ | mtf 0.174→0.158 causal | mtf wins on PnL, vol on Sharpe (Δ=0.002) |
| 9.X-C | LSTM Mode A (full replacement) | NO | Sharpe 0.061 | model class change failed |
| 9.X-D | Synthetic DXY | NO | Sharpe 0.154-0.168 | single-pair features already encode USD beta |
| 9.X-E | Lookahead-fix verification | observation | -9.2% real Sharpe | inflation isolated; production unaffected (causal-by-construction) |
| 9.X-F | Volume-mode runner | n/a | separate from alpha | OANDA GOLD-maintenance, EV≈0 by design |
| 9.X-G | Portfolio-opt (greedy de-corr) | NO | rho=0.5 Sharpe 0.159 (Δ +0.001) | 6th confirmed: pairs not orthogonal even after explicit filter |
| 9.X-H | Calendar features | eval running | TBD | curated CSV: 106 events 2025-07→2026-06 |
| 9.X-I | Risk-based sizing JPY | eval running | TBD | PositionSizerService formula in backtest |
| 9.X-J | Realism pack: compound + risk-mgr + CSI | eval running | TBD | mostly realism, J-1 compound is real lever |
| 9.X-K | Daily annualized Sharpe (measurement) | n/a | TBD | reporting, not lever |

Per-phase closure memos in `docs/design/phase9_*.md`.

---

## 6. Detailed summaries of the most informative phases

### 6.1 Phase 9.12 (the decisive original lift)

Replaced mid-bucket triple-barrier labels with **bid/ask aware** PnL: long trades pay ASK on entry, sell at BID on exit. SL/TP barriers also bid/ask aware. This single change took gross-Sharpe-0.35 / net-Sharpe-(-0.08) to net-Sharpe-0.16. **Without this, nothing else matters.**

### 6.2 Phase 9.X-B feature group sweep

Three opt-in feature groups vs Phase 9.16 baseline. K=3 lgbm_only causal:

| Group | Sharpe | PnL (pip) | DD%PnL | Trades |
| --- | --- | --- | --- | --- |
| Baseline (no group) | 0.149 | 8,186 | 2.7% | 11,613 |
| +mtf (h4/d1/w1 stats) | **0.158** | **11,414** | 2.1% | 13,608 |
| +vol (real_var, EWMA) | 0.160 | 10,385 | 3.3% | 11,299 |
| +moments (skew/kurt/autocorr) | 0.157 | 9,650 | 2.7% | 11,961 |
| +all (vol+moments+mtf) | 0.156 | 11,428 | 2.8% | 13,456 |

**Key takeaway:** different feature groups give *similar* Sharpe (Δ ≤ 0.003); they do NOT stack. +mtf wins on PnL, +vol on Sharpe, but the Sharpe difference is within run-to-run noise. Conclusion: feature engineering returns are nearly exhausted within OHLC-only data on this 1-year sample.

### 6.3 Phase 9.X-C/M-1 LSTM (Mode A full replacement)

2-layer LSTM with class-weighted CE loss, on RTX 3060 Ti CUDA. Class weights critical (without them: 84% timeout class, model predicts only timeout, 0 trades).

Result: per-trade Sharpe 0.061 vs LGBM baseline 0.149.

Why it failed:
- Class weights overshot: LSTM produced 7.7× too many trades, per-trade EV collapsed.
- Per-rank Sharpe inversion: rank-1 worse than rank-3 → confidence ranking is poorly calibrated.
- LSTM has no prior advantage on m5 FX bars; not enough sequence signal beyond what LGBM already extracts.

### 6.4 Phase 9.X-G greedy de-correlation top-K (just rejected)

**Hypothesis:** Phase 9.19 closure said "pairs systemically correlated → no sqrt(K) Sharpe lift." This phase tests the converse: *force* picks to be orthogonal via a filter `|corr(c, already_picked)| < ρ_max`.

Result: at ρ_max ∈ {0.4, 0.5}, K ∈ {2, 3, 5}, the per-trade Sharpe lift was Δ ≤ +0.001 (within noise). PnL dropped -18% to -20%. The filter strips out high-conf trades that happen to correlate, but those are the trades with the highest EV (regime-aligned).

**Falsified hypothesis:** "the picks aren't orthogonal" was a structural property, not a SELECTOR-logic property. The greedy filter doesn't fix it — perhaps Markowitz / HRP would, but Phase 9.X-G stopped at greedy.

### 6.5 Phase 9.X-D synthetic DXY (rejected)

Computed a synthetic USD index from existing 5 USD-pair returns with adjusted Fed weights. 8 cross-asset features per pair (`dxy_return_5/20/60`, `dxy_volatility_20`, `dxy_z_score_50`, `dxy_ma_cross_short`, `dxy_correlation_pair_20`, `dxy_pair_alignment`).

Result NO ADOPT: +dxy alone Sharpe 0.154 (worse), +dxy+mtf 0.168 (worse than mtf alone 0.174 [v18 inflated] or 0.158 [v19 causal]).

Why: single-pair features (`xp_*` cross-pair correlations) already encode USD beta implicitly. Synthetic DXY is information-redundant and noise-dominated.

---

## 7. Lookahead audit (so reviewer doesn't worry)

Identified one case during Phase 9.X-E: `_add_multi_tf_extended_features` (v18) used `df.resample(...).reindex(idx, method="ffill")` without a `shift(1)`. Daily bar labelled 2026-01-15 contains the 23:55 close; ffill at m5 10:00 leaked the future close (~14h lookahead). Fixed in v19 (`raw.shift(1).reindex(...)`, matching the same-script `_add_upper_tf` pattern) and verified bit-equal to vectorised pandas reference.

**Impact:** v18 +mtf Sharpe 0.174 → v19 causal 0.158 (-9.2% real). All other phases re-checked; only `+all` cell was bug-affected (also drops, still NO ADOPT).

**Production unaffected** — `feature_service.py` `_compute_mtf_features` operates only on candles already filtered to `timestamp < as_of_time` and uses pure-Python bucket aggregation. No pandas resample.

---

## 8. Constraints (please respect when proposing ideas)

- **Capital:** ¥300,000 retail account. Leverage caps via OANDA Japan margin rules (4% min margin, ~25:1 max leverage).
- **Broker:** OANDA Japan REST v20. No direct order book access; tick stream available but expensive to integrate.
- **Data:** 1 year of m1 OHLC + bid/ask spread, all 20 pairs (`data/candles_*_M1_365d_BA.jsonl`). Pre-built m5 features.
- **Compute:** single PC, RTX 3060 Ti GPU, ~32GB RAM. No distributed training.
- **Engineering bandwidth:** solo developer; "1 day" = 1 person-day of focused work; "1 week" = ~5 person-days.
- **Live readiness:** PRs ready to wire production; OANDA demo+live accounts available; M9 exit-gate + SafeStop already live.

---

## 9. What we have NOT yet tried (the open levers — your suggestion field)

### Tried but not yet evaluated (in flight)
- **Account compounding (Phase 9.X-J/J-1):** monthly rebase of size based on running balance. Returns rate not Sharpe lift.
- **RiskManager 4-constraint gate (J-2):** concurrent / per-instrument / per-direction / total-risk caps in backtest.
- **CSI Rule F5 filter (J-3):** reject trades where `|CSI(base) - CSI(quote)| < 0.5σ`.
- **Risk-based JPY sizing (Phase 9.X-I):** per-trade `size_units = floor(balance × risk_pct / sl_pip / pip_value / min_lot) × min_lot`. Variance equalisation expected to lift JPY-Sharpe by 10-20%.
- **Calendar features (Phase 9.X-H):** 9 features per (pair, bar) from FOMC/NFP/CPI/ECB/BOJ/BOE/RBA/BOC schedule. Curated CSV with 106 events.

### Not yet started — your idea space
1. **Markowitz / HRP portfolio optimization** (vs greedy 9.X-G). Mean-variance solve over per-bar candidate covariance.
2. **Limit-order execution** (capture spread instead of pay): rewrite execution layer to use limit orders with chase-and-cancel logic. ~+0.3 pip per trade durable edge.
3. **True economic indicator surprise values** (vs scheduled-time-only): forecast vs actual divergence as feature.
4. **Microstructure / tape features:** OANDA v20 streaming gives bid/ask velocity, spread variation, partial fills. Currently not used.
5. **Transformer / TCN architectures:** different inductive bias than LSTM (attention vs sequence). Tier-2 prior with effective fine-tuning was 30%.
6. **Online learning (FTRL, Adam-online):** continuous adaptation vs 90/7 batch. Could adapt to regime shifts faster.
7. **Mixture-of-experts / hierarchical strategies:** per-regime specialists, gated by ATRRegimeClassifier.
8. **Multi-horizon joint prediction:** predict 1h / 4h / daily moves jointly; the longer horizons may be more predictable.
9. **Meta-labelling (López de Prado):** binary "should I take this signal" classifier on Layer-1 outputs. Only Phase 9.12 B-3 tried it; got mixed result; might be revisitable with better features.
10. **CFD asset class expansion:** XAU/USD, US500, NAS100 — different vol regimes, less correlated. **User has rejected this:** OANDA CFD spreads are 50-100× FX majors, kills the EV.
11. **Time-of-day filter** (Tokyo / London / NY session-conditional EV): cheap to test, ~30 min.
12. **Walk-forward window length sweep:** 90/7 fixed currently; 30/14, 60/14, 120/14 are unexplored.
13. **Different SL / TP optimization** (vs fixed `atr_mult`): per-pair, per-regime, or learned.
14. **Feature interaction / kernel features:** GBDT already captures interactions; explicit polynomial / rolling-window features may add lift.
15. **Adversarial training / regime drift detection:** flag bars that look out-of-distribution vs training; abstain.

### Specifically falsified — please don't suggest these again unless you have a reason ours didn't apply

- More feature groups within OHLC (already exhausted: vol, moments, mtf all tied at Sharpe ~0.158)
- Lower confidence threshold (Phase 9.17b: per-trade EV is binding, not trade volume)
- Naive Top-K (Phase 9.19: sqrt(K) lift doesn't materialize at K=2/3/5)
- Greedy de-correlation Top-K (Phase 9.X-G: filters out the high-conf USD-cluster regime trades)
- Asymmetric TP/SL bucketed (Phase 9.18: low-bucket drag dominates)
- Ensemble of independent model classes without per-strategy thresholds (Phase 9.17: trade-rate explosion)
- Regression labels (Phase 9.X-A)
- LSTM full replacement (Phase 9.X-C)
- Synthetic DXY (Phase 9.X-D)

---

## 10. Useful reading order (in order of relevance)

1. `docs/design/phase9_x_b_amendment_memo.md` — most current Sharpe ranking
2. `docs/design/phase9_x_e_lookahead.md` — causal v19 anchor (this brief's 0.158 number)
3. `docs/design/phase9_x_g_design_memo.md` + `phase9_x_g_closure` (in `artifacts/phase9_x_g_*.log`)
4. `docs/design/phase9_x_b_closure_memo.md` — feature-group sweep findings
5. `docs/design/phase9_x_d_closure_memo.md` — DXY rejection
6. `docs/design/phase9_x_c_m1_closure_memo.md` — LSTM rejection
7. `docs/design/phase9_19_closure_memo.md` — Top-K, "pairs are correlated" finding
8. `docs/design/phase9_17_closure_memo.md` — first appearance of trade-rate explosion pattern
9. `docs/design/phase9_x_e_live_deploy_plan.md` — what production currently looks like

---

## 11. What would constitute an actionable suggestion

A "good" answer for our purposes:

- Names a **specific lever** (not "try more features" — be concrete about which feature class).
- Has a **falsifiable hypothesis** (specifies the metric direction and magnitude expected).
- Estimates **engineering cost** in person-days.
- Identifies **what could go wrong** (failure mode if hypothesis is wrong).
- Distinguishes from the things we have already falsified above.

Bonus: novel cross-domain ideas (from quant fundamental, fixed income, options, crypto, etc.) that we wouldn't naturally consider in retail FX.

---

## 12. Open question for the reviewer

Given:
- Per-trade Sharpe 0.158 ceiling on 20-pair × m5 × LGBM × bid/ask labels × walk-forward CV
- Adding features within OHLC has saturated
- Adding model complexity (LSTM) has failed
- Adding signal volume (top-K, ensemble, threshold) has failed
- Adding cross-asset synthetic indices (DXY) has failed
- Most trades are USD-cluster correlated regardless of selector logic

**What is the single most likely lever, and why?**

Optional secondary: rank the open-lever list (section 9.16) by your prior of clearing the 0.20 gate.
