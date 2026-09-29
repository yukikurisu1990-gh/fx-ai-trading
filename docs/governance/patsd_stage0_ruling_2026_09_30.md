# PATSD Stage 0 — 裁定の記録と事前登録（2026-09-30、Stage 0 の実行前）

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `PRODUCTION_READINESS_NOT_CLAIMED`.**

## 1. 裁定（Human + ChatGPT、2026-09-30）

| 項目 | 内容 |
| --- | --- |
| PR #497 | MERGE APPROVED → merge 済み（`d38fa2c`） |
| PR #498 | MERGE APPROVED（#497 の後） |
| 新 programme | `PROFITABLE_AUTOMATED_TRADING_SYSTEM_DISCOVERY` の開始を承認 |
| 旧 programme | `EXPECTED_RETURN_SOURCE_DISCOVERY` は `LONG_TERM_HOLD` / `NO_FURTHER_SEEN_DATA_ALPHA_SEARCH` のまま |
| 承認する作業 | **S0-G / Stage 0 だけ** |
| 承認コード | **R-A だけ** |
| 未承認 | R-B1 / R-B2 / R-B3 / R-C / R-D / R-E / R-F / R-G / R-H |
| 終了後 | Stage 0 の報告の後に STOP し、Human + ChatGPT へ戻る |

**R-A の範囲**（#498 §24 から広げない）

- **読んでよいもの**:
  - 既に seen である 3 window の M15 bid / ask cache
  - それを読む route: `exploratory_m15.bars.load`（2025-04-25 … 2025-12-28）、`exploratory_m15.supplemental.load`（2023-04-26 … 2025-04-24）、`exploratory_m15.momentum.load`（2021-04-26 … 2023-04-25）
  - spread・bid / ask・ATR・timeframe の集約に要る価格の統計
  - signal に依存しない cost の統計
- **禁止**:
  - signal と return の突き合わせ・alpha・方向 strategy・entry rule の損益・candidate system の backtest
  - training・特徴量の選択・meta-labeling
  - H4 strategy の実行・barrier の PnL・exit の最適化・portfolio の最適化
  - fresh / OOS / dead / forward の読み取り・broker・有料 data・市場の拡張
  - **実際の価格の経路の上で「ここで entry していれば」を計算すること**
  - B′ の準備（特徴量・label・学習用 dataset・family の実装）

## 2. S0-3 の変更（Stage 0 の実行前の programme ruling。結果を見た後の救済ではない）

旧: 真の Sharpe 1.5 の system が G4 を通る確率 ≥ 0.30 で合格。

**新**:

| 分類 | G4 通過確率 |
| --- | --- |
| GREEN | ≥ 0.30 |
| AMBER | 0.20 以上 0.30 未満 |
| RED | < 0.20 |

- AMBER は自動の FAIL ではない。他の Stage 0 項目と合わせて Human + ChatGPT が判断する。
- 境界 0.20 / 0.30 は、ここで凍結する。

## 3. Stage 0 の各項目の分類（lead が Stage 0 の実行前に定めた）

- #498 の S0 の番号と定義を保つ。S0-3 だけを裁定で更新した。
- 各項目の GREEN の境界は #498 の合格線と同じにした。AMBER と RED の境界は、裁定 §23 の要求に応えて、実行前に lead が定めたものである。

| 項目 | GREEN | AMBER | RED |
| --- | --- | --- | --- |
| **S0-1 cost economics** | H4 の標準の想定（平均保有 5 営業日）で、pair の中央値の Sharpe drag ≤ 0.5（net 1.0 に要る gross ≤ 1.5。#498 の合格線） | 0.5 < drag ≤ 1.0 | drag > 1.0 |
| **S0-2 pipeline の帰無** | 事前宣言の階段（deflated Sharpe の p の閾値: 0.10 / 0.05 / 0.025 / 0.01 / 0.005 / 0.001）の中で、p* ≥ 0.01 で family-wise の誤合格率 ≤ 10% を達成 | ≤ 10% を達成できるのが p* ∈ {0.005, 0.001} だけ | 階段の中で ≤ 10% を達成できない |
| **S0-3 confirmability** | 上の裁定 | 同左 | 同左 |
| **S0-4 保護 data の汚染** | fresh の価格の読み取りが無いと確認でき、外部情報の露出が特定の mechanism・通貨・期間に限られる | 価格の重なりの可能性が未解決、または露出が cycle 1 の family の確認を広く損なう | fresh の価格の読み取りを確認した |
| **S0-5 rename 台帳** | cycle 1 の 4 family 全てに、過去の同型との本物の差がある | 2〜3 family | 1 family 以下 |

**全体の status**: 単一の数字で PASS / FAIL にしない（裁定 §40）。

| 状態 | status |
| --- | --- |
| RED が 1 つでもある | `STAGE0_RED_RETURN_TO_HUMAN`（failure の原因で D / E / H を選ぶ候補にする） |
| RED が無く AMBER がある | `STAGE0_AMBER_PROCEED_REQUIRES_HUMAN_DECISION` |
| 全て GREEN | `STAGE0_GREEN_B_PRIME_ELIGIBLE_PENDING_R_B1`（R-B1 は未承認なので、B′ は自動で始めない） |

## 4. 成功確率の表記（裁定 §14・§15）

- 使う表記は `MODEL_BASED_PRIOR_SUCCESS_ESTIMATE_VERY_LOW`、または「凍結した参照クラスの仮定の下で約 1% 以下」。
- prior は standalone な tier A mechanism から作った。一方、探すのは選択された system の portfolio である。**参照クラスが一致せず、span も重なる。**
- したがって 0.8〜1.1% を、頻度論的な実際の成功確率として扱わない。用途は計画・hurdle の設計・情報価値の比較に限る。

## 5. business objective（裁定 §16〜§19）

**production portfolio の目標**:

- `FULL_RETAIL_NET_SHARPE >= 1.0`
- `REALIZED_VOL ≈ 5%`
- `ANNUAL_STRATEGY_NET ≈ >= 5%`
- `STRESS_MAX_DD <= 15%`

**その他の区別**:

- 年 5% は、strategy の取引 P&L で測る。financing・cash yield・担保の利息は分けて表示する。
- **Sharpe 1.0 は production portfolio の目標で、個々の discovery candidate の要求ではない。**
- 真の Sharpe 0.8〜1.0 の candidate は `PROMISING_BUT_BELOW_PRODUCTION_TARGET` として Human に返す。fresh + 36 か月の forward は自動では承認されない。

## 6. Stage 0 の実行上の技術的な決定（結果の前）

- **S0-2 の合成 data**:
  - seen の H4 の mid の log return に、**時点ごとに全 pair 共通のランダムな符号**を掛ける（ベクトルの符号ランダム化）。これで vol の塊・pair 間の相関・大きさを保ち、方向の情報を壊す。
  - #498 が挙げた circular shift は、**実際の価格の経路の上で候補の position の損益を計算することになるので、R-A の禁止に当たる**。そのため使わない（結果の前の決定）。誤合格率への影響は、合成 data の種類が 1 つ減ることだけで、偏りの向きは無い。
- **candidate は signal を持たない置き換えの規則だけで作る**（ランダムな entry 時刻・ランダムな方向・事前固定の保有期間）。
  - B′ の family の実装はしない（裁定 §42）。
  - candidate の損益は、合成 data の上でだけ計算する。
  - barrier / trailing の exit は模擬しない（経路依存。限界として開示する）。
- **G4 の deflation**: #498 §13 の「deflate してから縮小」は、deflated Sharpe の p の閾値を hard filter として課す（deflation を gate として扱う）形で実装する。感度として、点推定の deflation（観測 − SE × E[max_Neff]）も報告する。
