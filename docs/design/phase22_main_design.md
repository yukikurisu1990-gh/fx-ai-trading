# Phase 22 Main Design (path-aware EV redesign)

**Date**: 2026-05-05
**Status**: ACTIVE — Stage 22.0a (PR2) 開始の正式前提
**Supersedes**:
- `docs/design/phase22_0z_results_summary.md` (旧 PR0 snapshot)

**Companion**:
- `docs/design/phase22_alternatives_postmortem.md` (alpha-independent reject 根拠)

---

## 1. Background — なぜ alpha-independent ルートを閉じたか

Phase 22.0z (PR0) は当初、**alpha-independent improvement** (universe 縮小 / 時間帯 gate) で
無コスト Sharpe / PnL 改善が得られないかを検証することを想定していた。

PR0 の 4 sub-stage に加え、追加検証 22.0z-3c / 3d / 3e を実施した結果、
**alpha-independent improvement での Sharpe / PnL 改善は実証されなかった**。

| Route | Result |
|---|---|
| Universe (pair tier filter) | 全 variant baseline 大幅劣後 — 完全 reject |
| Time-of-day gate (test-side only) | 改善は fold4 限定 7 件除外による post-hoc / fragile な選択 — reject |
| Time-of-day gate (train-side含む) | production-realistic 構成で PnL 崩壊 — reject |
| Liquidity Reversion (tick) | historical tick 不在で halt — LOW_PRIORITY 据置 |

→ **Phase 22 は alpha (label / model / exit) 改造に集中する。**
詳細は `phase22_alternatives_postmortem.md` を参照。

---

## 2. Premise corrections — 旧設計仮定の更新

### 2.1 M1 spread / ATR (Stage 22.0z-1)

| | 旧前提 | 新事実 (確定) |
|---|---|---|
| M1 spread/ATR median | 25% | **128%** (range 65-236%) |
| 戦略含意 | signal が ATR の 5-10% で勝てる | signal が ATR を超える bar でなければ positive EV 不可能 |

- Cleanest pair (USD_JPY): 64.9%
- Worst (AUD_NZD): 236.4%
- WeekOpen (21-23 UTC) は他セッションの 1.5-2.3x 悪化

### 2.2 M5 spread / ATR (Stage 22.0z-2)

- 50.5% は **real** (Stage 21.0a → 22.0z-2 で confirmed)
- aggregation artifact ではない
- M1 → M5 集約 data で M5 label 作成可能 (native M5 全 pair × 730d 取得不要)

### 2.3 Production baseline (final)

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

**この baseline を Phase 22 の唯一の比較軸とする。**

---

## 3. Realistic target — 期待値の下方修正

### 3.1 Target table

| 区分 | 目標 | 根拠 |
|---|---|---|
| 第一目標 | **+50〜100 pip/year 改善** (Sharpe +0.10〜+0.15) | spread cost 128% 前提下で構造的に実現可能なレンジ |
| ストレッチ | +200 pip/year 改善 (Sharpe ≧ +0.20) | path-aware label が機能した場合 |
| 構造的に困難 | +1000 pip/year 級 改善 | spread cost > ATR の universe では現時点では非現実的、明記する |

### 3.2 Kill criteria (新候補が ADOPT 不可となる条件)

新戦略候補は次のいずれかに該当した時点で **即 reject**:

1. spread +0.5 pip stress で baseline +110 pip/year を割る
2. MaxDD > 250 pip
3. DSR (Deflated Sharpe Ratio) で baseline 同等を割る
4. 5-fold pos/neg ratio が baseline 4/1 を下回り CV > 1.0
5. n が baseline 141 trades/year の 50% 未満で Sharpe lift が +0.05 未満

### 3.3 ADOPT 条件 (基本)

- baseline (PnL +180, Sharpe +0.0822) を超え
- spread +0.5 stress で +110 を維持または改善
- MaxDD <= 200 pip
- 5-fold pos/neg >= 4/1
- DSR で baseline を上回る

---

## 4. Phase 22 Active research path

| Stage | 内容 | 主前提 |
|---|---|---|
| **22.0a** | Scalp label design (path-aware EV) — 最重要 | M1 spread/ATR=128% 反映、`is_week_open_window` flag は label に **含むのみ** (filter 用途禁止) |
| 22.0b | Mean reversion 仮説 (1-pager 必須) | spread > 反発幅の bar 多い予想、kill criteria 厳格 |
| 22.0c | M5 breakout + M1 entry hybrid | M5 50% spread/ATR で micro breakout 候補 |
| 22.0e | Meta-labeling (allowlist + shuffle-target test 必須) | feature contamination guard 必須 |
| 22.0f | Strategy comparison (multi-metric verdict + DSR) | baseline +180 を超えなければ ADOPT 不可 |
| 22.0g | M5-only fallback variant | 22.0a-f で +180 突破できなかった場合 |

### 4.1 Stage 22.0a Scalp Label Design (PR2 = 次 PR)

- 範囲: path-aware EV label の基盤構築
- 含める要素:
  - M1 path-aware EV label (forward N-min path 上の MFE / MAE / NPR を要約)
  - M1 spread/ATR=128% 前提を label normalization に反映
  - `is_week_open_window` flag を **label の context として保持** (ただし filter 用途には使わない)
  - Triple-barrier との整合性
- 除外する要素:
  - production code (src/) touch
  - run_paper_decision_loop / run_live_loop の変更
  - DB schema 変更
- 想定工数: 設計 doc + research script + tests, ~500 行
- ADOPT 基準: §3.3 を満たす label 設計

---

## 5. Frozen / removed paths

### 5.1 Frozen (LOW_PRIORITY)
- **22.0d Liquidity Reversion**
  - Historical tick 不在で halt
  - PricingStream 新規実装後の live-only paper test 候補
  - Phase 22 main path には含めない

### 5.2 Removed (再試行禁止)

`phase22_alternatives_postmortem.md` §4 の NG list を本設計の正式制約として継承:

1. Pair tier filter / single-pair concentration
2. Train-side time-of-day filter (任意時間帯)
3. Test-side only filter による improvement claim (extraordinary evidence なしで不可)
4. WeekOpen-aware sample weighting (train-side touch を含む)
5. Universe を絞った後の cross-pair feature engineering 単独

---

## 6. Out-of-scope — 本 Phase でも touch しない

Phase 22 の研究 / 設計 stage は production code を一切 touch しない。
具体的に以下のファイル / 機能は本 Phase では変更不可:

- `src/fx_ai_trading/services/state_manager.py` (時間帯 gate 追加禁止)
- `src/fx_ai_trading/services/exit_policy.py`
- `src/fx_ai_trading/services/supervisor.py` cadence 変更
- `src/fx_ai_trading/services/meta_decider.py` rule 追加 (F1-F5 既存ルール変更も含む)
- DB schema (decision_log, close_events, orders, position_open など)
- `scripts/run_paper_decision_loop.py` の filter 追加
- `scripts/run_live_loop.py` の filter 追加
- `src/fx_ai_trading/domain/reason_codes.py` (`MetaFilterReason.SESSION_CLOSED` は既定義だが本 Phase では使用しない)

production migration が必要な改善が確定した場合は、Phase 22 終了後の **別 PR** で扱う。

---

## 7. Next PR (PR2)

- **Stage 22.0a Scalp Label Design**
- doc + research script + tests (~500 行)
- production code 不 touch 維持
- ADOPT 判定は §3.3 の条件を満たすこと

---

## 8. References

### Phase 22 関連
- `docs/design/phase22_0z_results_summary.md` (旧 PR0 snapshot, SUPERSEDED)
- `docs/design/phase22_alternatives_postmortem.md` (alpha-independent reject 根拠)

### Verification artifacts
- `artifacts/stage22_0z/**/*`
  - `data_validation/`
  - `m5_feasibility/`
  - `alternatives/`
  - `temporal_decomposition/` (3c)
  - `temporal_decomposition_v2/` (3d)
  - `train_test_filter/` (3e)
  - `tick_prereq/`

### Memory entries
- `memory/project_v2_baseline_critical_fixes.md`
- `memory/project_phase9_invalidation_2026_05_03.md`
- `memory/project_m1_spread_atr_recalibration_2026_05_05.md` (もし保存済)
- `memory/project_phase22_pr3_doc_consolidation.md` (本 PR で追加)

---

**Phase 22 Main Design status: ACTIVE.**
次の判断は **PR2 (Stage 22.0a Scalp Label Design)** の起票。
