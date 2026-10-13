# Rates-Anchored FX Convergence — 独立の strategy の研究の track（2026-10-13）

`PRODUCTION_READINESS_NOT_CLAIMED`.

**位置づけ**: Human + ChatGPT の指示「Rates-Anchored FX Convergence Strategy」（2026-10-13）の記録。

- **これは HOLD の解除ではない**。`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`（`docs/governance/fxid_long_term_hold_ruling_2026_10.md`）は変えない。指示 §1 に従い、**独立の strategy の研究の track**として扱う。
- 研究する strategy は **`RATES_ANCHORED_FX_CONVERGENCE` の 1 本だけ**（指示 §2、§59）。失敗した場合、indicator・ML・別の strategy で救済しない。

## 1. 裁定の記録

| 項目 | 内容 |
| --- | --- |
| PR #509 | merge 済み（head `0e18134` → merge `bea3a51`、2026-10-12T16:12:40Z、`--match-head-commit`）。master CI success（run 38275796415、16:24:52Z） |
| 仮説 | 短期の金利の再評価が示す FX の fair value と、実際の FX の間の短時間の乖離（overshoot / underreaction）が、retail の cost の後に収益化できるか |
| 主の universe | EUR/USD・GBP/USD・USD/JPY（内部は全て「外貨の USD 建ての価値」の log） |
| 最終の分類 | RAC-A〜G（指示 §52） |

## 2. data の読み取りの権限（Red の行為の範囲の記録）

この指示は、data の調査・**取得**・実装・backtest を 1 つの PR で進めることを、途中の確認なしに認めている（指示 §58、§60）。CLAUDE.md は実 data の読み取りを Red とし、操作・期間・pair・timeframe・head を名指す承認を求めるので、**この指示が承認した範囲を次のとおり狭く記録する**:

| 項目 | 範囲 |
| --- | --- |
| 操作 | (1) 承認済みの seen の route（`scripts.research.patsd_stage0.data.load_pair`）からの FX の M15 bid / ask の読み取り。(2) OANDA v20 の **historical / read-only** の candle の取得（金利の proxy の instrument と、その instrument の metadata）。注文・account の変更・position は一切行わない |
| 期間 | **2021-04-26 … 2025-12-28**（既に seen の期間、指示 §31）。request の上限と下限を request の段で固定し、返った frame の最小・最大を確かめる |
| pair / instrument | FX: EUR_USD・GBP_USD・USD_JPY（second-stage の cross の比較に EUR_JPY・GBP_JPY の seen の M15 も可）。金利: §3 の feasibility で決めた instrument |
| timeframe | M15（bid / ask） |
| head | 取得を実行した head を記録に残す |

**読まない**: protected fresh **`2016-06-02 … 2021-04-25`**、historical OOS `2025-12-29 … 2026-02-28`、dead window `2026-03-01 … 2026-04-24`、forward epoch `≥ 2026-04-25`。

## 3. 禁止（指示 §2、§30、§44、§46、§47）

- RSI・MACD・EMA・Bollinger・ADX・Donchian・candlestick・LightGBM・XGBoost・neural network・Transformer・AutoML・feature の総当たり・parameter の grid search・別 strategy への横展開
- regime の filter（ADX など）
- 結果を見た後の parameter の変更（primary は凍結し、sensitivity は報告だけ）
- 取引（live / demo / paper）、account の変更、有料 data の購入

## 4. STOP

最終の分類の確定と最終報告で STOP。RAC-A / B でも fresh は読まず、確認の提案を作って STOP（指示 §54）。
