# Phase 22 Alternatives Postmortem

**Date**: 2026-05-05
**Scope**: Stage 22.0z-3 / 3b / 3c / 3d / 3e の確定判定。
alpha-independent improvement (universe restriction / time-of-day gate) を
Phase 22 から完全に閉じる根拠を一元記録する。
**Status**: Phase 22 設計上の正式な reject log。再試行禁止。

---

## 0. Summary table

| Route | Verdict | Decisive evidence |
|---|---|---|
| Universe (pair tier filter) | ❌ 完全 reject | 22.0z-3 / 3b: 全 variant で baseline 大幅劣後、multipair LGBM 構造依存 |
| Time-of-day gate (test-side only) | ❌ reject | 22.0z-3 / 3c / 3d: 改善は fold4 限定の 7 件に集中、CV > 1.0、post-hoc / fragile |
| Time-of-day gate (train+test side) | ❌ reject | 22.0z-3e: production-realistic な v2 構成で PnL +234 → +21〜-183 に崩壊 |
| Liquidity Reversion (tick 前提) | ⚠ LOW_PRIORITY 据置 | 22.0z-4: PricingStream 未実装、historical tick replay 不可。live-only paper test 候補 |

---

## 1. Universe (Pair tier filter): ❌ 完全 reject

### 1.1 Tested variants
| Config | n | Sharpe | annual PnL | MaxDD | top pair share |
|---|---|---|---|---|---|
| baseline (20 pairs) | 141 | +0.0822 | +180 | 159 | 48.9% (USD_JPY) |
| usd_jpy_only | 819 | -0.192 | -1056 | 1109 | 100% |
| jpy_pairs_only (6) | 235 | -0.043 | -131 | 282 | 71.1% |
| jpy_4pairs_only | 308 | -0.087 | -296 | 481 | 74.7% |
| cleanest_top5 | 265 | -0.109 | -319 | 433 | 70.9% |

### 1.2 Why all variants failed
- B Rule LGBM は **multipair で同時学習する構造**。universe 縮小で
  - 学習サンプル数が激減
  - cross-pair signal (相関、強弱) が失われる
- 残った pair に USD_JPY が 70-100% 集中 → portfolio risk が悪化
- per-pair PnL contribution が config 違いで sign flip → **統計的に不安定**
- 高 spread pair (NZD_JPY / CHF_JPY) を抜いても **改善せず、むしろ悪化**
  - 6-pair PnL -131 → 4-pair PnL -296

### 1.3 Verdict
- **Phase 22 から alpha-independent alternative としての pair filter を完全削除**
- 再試行禁止 (NG list 1)
- B Rule の multipair 学習構造を温存したまま universe を絞ることは、本研究では実証されていない構造変更を要する

---

## 2. Time-of-day gate: ❌ reject (test-only / train-side ともに不採用)

### 2.1 Stage 22.0z-3 初出 (誤名 weekopen_excluded)
- 当初 `hour ∈ {21, 22}` 全曜日除外を「WeekOpen 除外」と誤称した
- 結果は `hour ∈ {21, 22}` の rollover-hour gate (曜日問わず)
- 表面値: Sharpe +0.0822 → +0.1123、PnL +180 → +234 (一見 ADOPT 候補)

### 2.2 Stage 22.0z-3c / 3d 厳密分解

| Config | n | excluded | annual PnL | ΔPnL | Sharpe | ΔSharpe | excluded avg PnL |
|---|---|---|---|---|---|---|---|
| baseline | 141 | 0 | +180.2 | +0.0 | +0.0822 | +0.0000 | +0.00 |
| daily_21_22 | 134 | 7 | +234.5 | +54.3 | +0.1123 | +0.0302 | -7.75 |
| true_week_open_only (Sun 21-23 UTC) | 137 | 4 | +190.5 | +10.2 | +0.0891 | +0.0070 | -2.56 |
| true_week_open_extended (+Mon 00 UTC) | 134 | 7 | +220.0 | +39.7 | +0.1047 | +0.0225 | -5.67 |
| non_weekopen_daily_21_22 (≠Sun) | 138 | 3 | +224.3 | +44.0 | +0.1046 | +0.0224 | -14.67 |
| monday_21_22_utc_only | 141 | 0 | +180.2 | +0.0 | +0.0822 | +0.0000 | +0.00 |

### 2.3 Fold stability (per-fold PnL, base spread)

| Config | f1 | f2 | f3 | f4 | f5 | mean | stdev | CV |
|---|---|---|---|---|---|---|---|---|
| baseline | +10.0 | +66.2 | +106.8 | -21.3 | +18.4 | +36.0 | 45.2 | 1.25 |
| daily_21_22 | +10.0 | +66.2 | +106.8 | +32.9 | +18.4 | +46.9 | 35.6 | 0.76 |
| true_week_open_only | +10.0 | +66.2 | +106.8 | -11.1 | +18.4 | +38.1 | 42.7 | 1.12 |
| non_weekopen_daily_21_22 | +10.0 | +66.2 | +106.8 | +22.7 | +18.4 | +44.8 | 36.6 | 0.82 |

**全 7 件の除外 trade が fold4 にのみ集中** (4 Sunday avg -2.56 pip + 3 weekday Tue avg -14.67 pip)。
`f1, f2, f3, f5` は除外 0 件。

### 2.4 Stage 22.0z-3e Train/Test filter ablation (decisive evidence)

| Filter | v1 (train full + test filtered) | v2 (train+test filtered, production-realistic) | v3 (train filtered + test full) |
|---|---|---|---|
| daily_21_22 | PnL +234 (改善) | PnL +21 (崩壊) | PnL +17 (崩壊) |
| true_week_open_only | PnL +190 | PnL -78 (negative) | PnL -78 (negative) |
| non_weekopen_daily_21_22 | PnL +224 | PnL -183 (negative) | PnL -201 (negative) |

#### Mechanism
- multipair LGBM は train 集合の at-21-22 UTC bar から学習する partial signal に依存している
- train-side で当該時間帯を抜くと、その時間帯の bar が **unseen domain** 化
- test-time で同じ時間帯を抜く v2 でも、モデル品質劣化が他時間帯の prediction にも波及して PnL が崩壊する
- v1 で表面的に改善して見えたのは、test-time での 7 件除外が fold4 の負け trade を後から抜いた効果

### 2.5 Verdict (test-side only)
> *test-side only filter is not inherently invalid as a production entry gate simulation,
> but in this case it is rejected because the improvement was post-hoc, fold4-fragile,
> and based on only 7 excluded trades.*

production の entry gate を simulation する手段として test-side only filter は理論上成立する。
しかし本件では:
- 改善が fold4 の 7 件除外に集中 (post-hoc selection)
- CV > 1.0 で fold 安定性を欠く (fragile)
- 除外件数が少ない (7 trades over 5 folds)

ため、**production entry gate としての一般化を支える証拠が無い**と判定し採用不可。

### 2.6 Verdict (train-side filter)
production-realistic 構成 (v2) で全 filter variant が崩壊。
**train-side で時間帯 sample を削る経路は完全に閉じた。**

### 2.7 NG list (再試行禁止)
1. `hour` / `dow` ベースの train-side sample filter (任意の時間帯)
2. WeekOpen / rollover hour に基づく sample weighting (train-side touch 含む)
3. test-side only filter による「改善」claim (extraordinary evidence 無しでは不可)

---

## 3. Liquidity Reversion (tick 前提): ⚠ LOW_PRIORITY 据置

### 3.1 OANDA API survey
| Endpoint | Implemented in repo |
|---|---|
| REST `/pricing` (snapshot) | ✓ Yes |
| REST `/candles` (S5+, history) | ✓ Yes |
| STREAM `/pricing/stream` (live tick) | ✗ No (oandapyV20 lib supports, repo unused) |
| `record_quotes.py` (REST polling, 1sec min) | ✓ Yes |

### 3.2 Historical granularity
- 最小: **S5 (5 秒 OHLC)**, true tick history **NOT available**

### 3.3 M1 OHLC 内 spread fluctuation 検出力
| Pair | spread (median) | intra-bar Δ p95 | spike rate |
|---|---|---|---|
| USD_JPY | 1.70p | 0.500p | 1.66% |
| EUR_USD | 1.60p | 0.300p | 1.36% |
| GBP_JPY | 3.60p | 0.900p | 1.76% |

→ M1 OHLC は intra-bar Δspread/spread 比が **< 30%**、liquidity reversion 検出には不足。

### 3.4 REST polling (live forward only)
- 1 sec cadence で 60-180 sec event window に十分なサンプル数

### 3.5 Verdict: LOW_PRIORITY
- Historical backtest **不可能** (S5 が最小、tick 不在)
- Live forward test は理論上可能 (PricingStream 新規実装が必要)
- → **Phase 22.0d は他 stage 完了後に検討する低優先度案件**として残置
- Phase 22 main path には含めない

---

## 4. NG list (再試行禁止 - formal)

| # | NG path | Reason |
|---|---|---|
| 1 | Pair tier filter / single-pair concentration | 22.0z-3 / 3b 全 variant baseline 劣後、multipair 学習構造依存 |
| 2 | Train-side time-of-day filter (任意時間帯) | 22.0z-3e v2/v3 で多様な構成下で PnL 崩壊 |
| 3 | Test-side only filter による improvement claim | 22.0z-3c/3d で fold4 集中 + 少数 trade 由来と判明、extraordinary evidence なしでは ADOPT 不可 |
| 4 | WeekOpen-aware sample weighting (train-side touch) | NG #2 と同根、train-side で時間帯 sample を歪めることが destructive |
| 5 | Universe を絞った後の cross-pair feature engineering 単独 | universe 縮小自体が NG #1 で閉じている |

---

## 5. Confirmed baseline (final, post-postmortem)

```
Config:        B Rule (M1 17feat LGBM + H1 23feat agreement filter,
               conf=0.40, TP=1.5×ATR, SL=1.0×ATR)
Universe:      20 pairs
Time gate:     なし
Sharpe:        +0.0822
annual PnL:    +180 pip/year
MaxDD:         159 pip
n:             141 trades/year
spread +0.5 stress PnL:  +110 pip/year
```

これが Phase 22 の **唯一の baseline**。
新候補は本 baseline を超えなければ ADOPT 不可。
詳細な改善目標と kill criteria は `phase22_main_design.md` §3 参照。

---

## 6. 検証 artifact 一覧

### Scripts (research, production 不 touch)
- `scripts/stage22_0z_1_data_validation.py`
- `scripts/stage22_0z_2_m5_native_vs_aggregated.py`
- `scripts/stage22_0z_3_alternatives.py`
- `scripts/stage22_0z_3b_jpy_4pairs_supplement.py`
- `scripts/stage22_0z_3c_temporal_decomposition.py`
- `scripts/stage22_0z_3d_temporal_decomposition_v2.py`
- `scripts/stage22_0z_3e_train_test_filter.py`
- `scripts/stage22_0z_4_tick_prereq.py`

### Output artifacts
- `artifacts/stage22_0z/data_validation/*`
- `artifacts/stage22_0z/m5_feasibility/*`
- `artifacts/stage22_0z/alternatives/*`
- `artifacts/stage22_0z/temporal_decomposition/*` (3c)
- `artifacts/stage22_0z/temporal_decomposition_v2/*` (3d)
- `artifacts/stage22_0z/train_test_filter/*` (3e)
- `artifacts/stage22_0z/tick_prereq/*`

### Related design docs
- `docs/design/phase22_0z_results_summary.md` (旧 PR0 snapshot, SUPERSEDED)
- `docs/design/phase22_main_design.md` (Phase 22 active 正本)

### Memory entries
- `memory/project_m1_spread_atr_recalibration_2026_05_05.md`
- `memory/project_v2_baseline_critical_fixes.md`
- `memory/project_phase9_invalidation_2026_05_03.md`

---

**Postmortem status: CLOSED.**
