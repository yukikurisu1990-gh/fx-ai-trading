# Phase 22.0z (PR0) Final Summary

**Date**: 2026-05-05
**Scope**: Phase 22 entry validation gate. 4 sub-stages (data validation, M5 native vs aggregated, alpha-independent alternatives, tick prerequisite). NO production code touched.

> ⚠ **SUPERSEDED 2026-05-05**: Section 3 / 5 / 7 / 9 (WeekOpen 除外 ADOPT 判定および
> +234 pip/year 新 baseline) は Stage 22.0z-3c / 3d / 3e の追加検証で **撤回** された。
> WeekOpen 除外は (1) fold4 限定の少数 trade 由来で fragile、
> (2) train-side filter 適用で multipair LGBM 大幅劣化 (PnL +234 → -183) のため
> production migration 不可。確定 baseline は **B Rule 無修正 +180 pip/year / Sharpe +0.082** に戻る。
> PR1 (WeekOpen production migration) は完全 abandon。
>
> - 後継 (Phase 22 正本): `docs/design/phase22_main_design.md`
> - alpha-independent reject 根拠: `docs/design/phase22_alternatives_postmortem.md`

---

## 1. Stage 22.0z-1 Data Validation: **✓ PASS**

- **Critical anomalies: 0**
  - bid > ask violations: 0% across all 20 pairs
  - duplicate timestamps: 0
- **Soft warnings: 40** (mostly spread/ATR + missing timestamp expected weekend gaps)
- **Critical recalibration finding**:
  - **M1 spread/ATR median = 65–236% (median across pairs: ~128%)**
  - Previously assumed value of "25%" is **completely wrong**
  - Cleanest pair (USD_JPY): 64.9%, Worst (AUD_NZD): 236.4%
  - WeekOpen (21-23 UTC) is 1.5–2.3x worse than other sessions

→ 致命的データ corruption 無し、ただし **Phase 22 期待値前提の下方修正必須**。

## 2. Stage 22.0z-2 Native M5 vs Aggregated: **✓ CONSISTENT**

- USD_JPY native vs M1→M5 agg: 39.1% vs 41.0% (diff -1.9pp)
- EUR_USD: 53.4% vs 54.1% (diff -0.7pp)
- GBP_JPY: 63.0% vs 65.1% (diff -2.1pp)
- All within 2pp → aggregation is NOT introducing artifact
- **Stage 21.0a EUR_USD M5 50.5% baseline confirmed real** (730d aggregated 49.6%)

→ M1→M5 集約は妥当。Phase 22.0a の M5 ラベル grid は M1 集約データで OK。Native M5 全 pair × 730d 取得は不要。

## 3. Stage 22.0z-3 + 3b Alternatives: **Pair filter ❌ REJECT, WeekOpen 除外 ✓ ADOPT**

### Headline 結果（base spread, no stress）

| Config | n | Sharpe | annual PnL | MaxDD | top USD_JPY share |
|---|---|---|---|---|---|
| **baseline (20 pairs)** | 141 | +0.0822 | +180 | 159 | 48.9% |
| **weekopen_excluded (20 pairs)** | 134 | **+0.1123** | **+234** | 164 | 50.7% |
| jpy_pairs_only (6) | 235 | -0.043 | -131 | 282 | 71.1% |
| jpy_4pairs_only | 308 | -0.087 | -296 | 481 | 74.7% |
| cleanest_top5 | 265 | -0.109 | -319 | 433 | 70.9% |
| usd_jpy_only | 819 | -0.192 | -1056 | 1109 | 100% |
| jpy_4pairs + WeekOpen excl | 298 | -0.069 | -231 | 424 | 75.2% |

### Spread stress sensitivity

| Config | base | +0.2pip | +0.5pip |
|---|---|---|---|
| baseline | +180 | +152 | +110 |
| **weekopen_excluded** | **+234** | **+208** | **+168** |
| jpy_4pairs_plus_excl | -231 | -271 | -317 (推定) |

### 重要な知見

- **NZD_JPY/CHF_JPY 除外で改善せず、むしろ悪化** (6-pair PnL -131 → 4-pair -296)
- 真の原因は **B Rule LGBM の multipair 学習構造依存**:
  - Universe 縮小 → 学習サンプル激減 + cross-pair signal 喪失
  - USD_JPY が 70-100% 集中して個別 pair 信号崩壊
- Per-pair PnL contribution は config 違いで sign flip → **統計的不安定性**
- **WeekOpen 除外単独**は spread stress 下でも一貫して優位（+168 vs baseline +110）

### 判定
- ❌ **Pair filter (USD_JPY only / JPY only / cleanest 5): 完全棄却**
- ✓ **WeekOpen 除外: production 候補として ADOPT**

> ⚠ **撤回 2026-05-05** (Stage 22.0z-3c / 3d / 3e): WeekOpen 除外の ADOPT 判定は撤回。
> test-only filter は production の entry gate simulation として理論上は成立するが、
> 本件では (a) 改善が fold4 限定の 7 件除外に由来する post-hoc / fragile な選択であり、
> (b) production-realistic な v2 (train+test 両側 filter) では PnL +234 → +21〜-183 に崩壊した。
> 詳細は `phase22_alternatives_postmortem.md` §2 参照。

## 4. Stage 22.0z-4 Tick Prerequisite: **LOW_PRIORITY**

### OANDA API Survey
| Endpoint | Implemented in repo |
|---|---|
| REST `/pricing` (snapshot) | ✓ Yes |
| REST `/candles` (S5+, history) | ✓ Yes |
| STREAM `/pricing/stream` (live tick) | **✗ No** (oandapyV20 lib supports, repo unused) |
| `record_quotes.py` (REST polling) | ✓ Yes (1sec min) |

### Historical granularity
- 最小: **S5 (5秒 OHLC)**, true tick history NOT available

### M1 OHLC 内 spread fluctuation 検出力
- USD_JPY: spread 1.70p, intra-Δ p95 0.500p, spike rate 1.66%
- EUR_USD: spread 1.60p, intra-Δ p95 0.300p, spike rate 1.36%
- GBP_JPY: spread 3.60p, intra-Δ p95 0.900p, spike rate 1.76%
- → M1 OHLC は intra-bar Δspread/spread 比が < 30%、liquidity reversion 検出には不足

### REST polling
- 1 sec cadence で 60-180 sec event window に十分なサンプル数

### 判定: **LOW_PRIORITY**
- Historical backtest 不可能（S5 が最小、tick 不在）
- Live forward test は理論上可能（PricingStream 新規実装が必要）
- → **Phase 22.0d は他 stage 完了後に検討する低優先度案件**として残置

---

## 5. WeekOpen 除外を production migration 候補にするか? **YES（ただし別 PR）**

### 判定根拠
- ✓ Sharpe +0.082 → +0.112 (+37%)
- ✓ annual PnL +180 → +234 (+30%)
- ✓ MaxDD 159 → 164 (+3%、誤差範囲)
- ✓ spread stress +0.5pip でも +168 pip 維持（baseline +110 の 1.5x）
- ✓ 20 pair universe 維持（multipair 学習保全）
- ✓ 実装変更最小: `hour ∉ {21, 22}` filter のみ
- ✓ alpha-independent（モデル変更不要）

### 別 PR 推奨理由（PR0 内では実装しない）
- PR0 は research conclusion のみ（production code 触らない原則）
- production migration には paper/live runner cadence 設定の調整が必要
- 別 PR で StateManager / supervisor の trading hour filter として実装
- 1 PR = 1 責務の維持

→ **次 PR1（または別の独立 PR）として WeekOpen 除外 production migration を起票**

> ⚠ **撤回 2026-05-05**: PR1 (WeekOpen 除外 production migration) は完全 abandon。
> Stage 22.0z-3e で train-side filter が destructive であることが確定し、
> 「test-only での改善実証」を production に移植する経路が閉じた。

## 6. Pair filter を Phase 22 から完全 drop するか? **YES**

### 判定根拠
- 4-pair, 6-pair, cleanest_5, USD_JPY-only すべて baseline 大幅劣後（-130 〜 -1056 pip）
- 高 spread pair 除外で改善せず（むしろ悪化）
- Pair filter は B Rule の multipair 学習構造と相性根本的に悪い
- top pair concentration 70-100% で portfolio risk 悪化
- 統計的不安定性顕著

→ **Phase 22 設計から alpha-independent alternative としての pair filter は完全削除**。再試行禁止。

## 7. Phase 22 新 baseline を weekopen_excluded に更新するか? **YES**

### 新 baseline
```
Config: B Rule + WeekOpen excluded (hour ∉ {21, 22})
Sharpe: +0.1123
annual PnL: +234 pip/year
n: 134 trades/year
MaxDD: 164 pip
spread +0.5 stress PnL: +168 pip/year
```

### 含意
- Phase 22 戦略候補（22.0a 〜 22.0f）の **改善基準値が +180 → +234 に上方修正**
- 新候補が +234 を超えなければ ADOPT 不可
- 期待値計算の前提も合わせて変更必要

> ⚠ **撤回 2026-05-05**: 新 baseline +234 は撤回。確定 baseline は
> **B Rule 無修正 / 20 pair / 時間帯 filter なし: Sharpe +0.0822, PnL +180 pip/year, MaxDD 159 pip**。
> Phase 22 戦略候補の改善基準値は +180 (現実的目標 +50〜100 pip 改善) に修正。
> 詳細は `phase22_main_design.md` §3 参照。

## 8. M1 spread/ATR=25% 前提崩壊を設計変更理由として明記するか? **YES**

### 設計文書に明記すべき事項
旧前提:
- 「M1 spread/ATR ≈ 25%」「signal が ATR の 5-10% で勝てる」

新事実（Stage 22.0z-1 確定）:
- 「M1 spread/ATR median = 65-236% (median 128%)」
- 「spread cost ≈ ATR レベル」「signal が ATR を超えなければ positive EV 不可能」

### 設計変更理由として明記する場所
- `docs/design/phase22_0z_results_summary.md` (本文書)
- `memory/project_m1_spread_atr_recalibration_2026_05_05.md`（既に保存済）
- Phase 22 全体設計レビュー時に **戦略期待値の下方修正** として参照

### 戦略候補への影響
- Mean Reversion: 反発幅が spread を超える bar が稀 → 仮説難航予想
- Micro Breakout: 突破幅が spread を超える bar 限定 → Stage 21.0c の再現リスク高
- Liquidity Reversion: tick データ無しで spread 動態追えず（22.0z-4 確認）
- → **Phase 22 戦略全体の期待 PnL を下方修正、kill criteria を厳しく設定**

## 9. 次 PR は何にするか?

### 推奨順位

#### **PR1 候補 A: WeekOpen 除外 production migration**（最優先）
- 範囲: `services/state_manager.py` または supervisor cadence に **hour ∉ {21, 22} filter** 追加
- 期待効果: production B Rule の Sharpe +37% / PnL +30% 改善（無コスト）
- リスク: low（純粋な hour filter、戦略変更なし）
- 工数: 1 日（コード + tests + 切替確認）
- 制約遵守: production code に touch するため別 PR

#### **PR2 候補 B: Stage 22.0a Scalp Label Design**（Phase 22 本体開始）
- 範囲: 当初設計通り、path-aware EV label 基盤構築
- 但し以下を反映:
  - **新 baseline = weekopen_excluded (+234 pip/year)**
  - **M1 spread/ATR=128% 前提**で期待値再計算
  - Pair filter alternative は 22.0a 内では検証不要（22.0z で完全 drop 済）
  - `is_week_open_window` flag は 22.0a label に含む（既設計通り）
- 工数: 当初計画通り（~500 行 + tests）

#### **PR3 候補 C: Phase 22 設計レビュー document update**（軽量）
- 範囲: `docs/design/phase22_0z_results_summary.md`（本文書）+ Phase 22 main design doc 更新
- 期待効果: 設計確定、PR2 開始の正式な前提化
- 工数: 0.5 日

### 推奨実行順序
1. **PR1（WeekOpen 除外 production）** 先行 → 即座に +30% PnL 改善を取りに行く
2. **PR3（設計 doc update）** 並行で軽く
3. **PR2（22.0a 開始）** 設計確定後

> ⚠ **撤回 2026-05-05**: 推奨順序は **PR3 (本 PR, 設計 doc 統合) → PR2 (Stage 22.0a)** に変更。
> PR1 (WeekOpen production migration) は完全 abandon。

---

## 統計的サマリー

### 新 baseline
- Sharpe: **+0.1123**
- annual PnL: **+234 pip/year**
- MaxDD: 164 pip
- spread +0.5 stress: +168 pip

### Phase 22 改善目標
- Sharpe > +0.20（baseline 比 +78%）
- annual PnL > +500 pip/year（baseline 比 +114%）
- MaxDD < 200 pip
- spread +0.5 stress でも positive 維持

### 確定 reject 戦略
- ❌ Pair tier filter（全 variant 検証済、棄却）
- ❌ Single-pair concentration（USD_JPY only -1056 pip）

### 低優先度戦略
- ⚠ Liquidity Reversion (Phase 22.0d)（tick prereq LOW_PRIORITY、live-only paper test 限定）

### Active research path
- Stage 22.0a: scalp label design（最重要）
- Stage 22.0b: mean reversion (戦略仮説 1-pager 必須)
- Stage 22.0c: M5 breakout + M1 entry hybrid
- Stage 22.0e: meta-labeling (allowlist + shuffle-target test 必須)
- Stage 22.0f: strategy comparison (multi-metric verdict + Deflated Sharpe)
- Stage 22.0g: M5-only fallback variant

---

## 21.0z 完了時点のリポジトリ状態

### 追加された research script（読み取り専用、production 未touch）
- `scripts/stage22_0z_1_data_validation.py`
- `scripts/stage22_0z_2_m5_native_vs_aggregated.py`
- `scripts/stage22_0z_3_alternatives.py`
- `scripts/stage22_0z_3b_jpy_4pairs_supplement.py`
- `scripts/stage22_0z_4_tick_prereq.py`

### 取得された data（既存と分離）
- `data/native_m5/native_M5_USD_JPY_30d_BA.jsonl`
- `data/native_m5/native_M5_EUR_USD_30d_BA.jsonl`
- `data/native_m5/native_M5_GBP_JPY_30d_BA.jsonl`

### 出力 artifacts
- `artifacts/stage22_0z/data_validation/*`
- `artifacts/stage22_0z/m5_feasibility/*`
- `artifacts/stage22_0z/alternatives/*`
- `artifacts/stage22_0z/tick_prereq/*`

### Memory entries
- `memory/project_m1_spread_ceiling_2026_05_05.md`（更新: 25% 仮定誤りを注記）
- `memory/project_m1_spread_atr_recalibration_2026_05_05.md`（新規）
- `memory/project_phase21_roadmap.md`
- `memory/feedback_research_autonomy.md`

### 未touch（原則遵守）
- `src/fx_ai_trading/services/exit_policy.py`
- `src/fx_ai_trading/services/state_manager.py`
- `src/fx_ai_trading/services/supervisor.py`
- `src/fx_ai_trading/adapters/broker/oanda.py`
- DB schema 関連
- `scripts/run_paper_decision_loop.py`, `run_live_loop.py`

---

**PR0 status: COMPLETE.**

次の判断を仰ぎます: **PR1 (WeekOpen 除外 production)** から着手か、**PR3 (Phase 22 design doc update)** が先か、それとも **PR2 (Stage 22.0a) 直行**か。
