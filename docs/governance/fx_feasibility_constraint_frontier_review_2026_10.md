# FX Feasibility Constraint Frontier — `FX_FEASIBILITY_CONSTRAINT_FRONTIER_REVIEW`（2026-10-11）

`PRODUCTION_READINESS_NOT_CLAIMED`.

**位置づけ**: Human + ChatGPT の指示「FX Feasibility Constraint Frontier — One-Shot Fast Track」（2026-10-11）の記録。

- **FXID の研究状態の single source of truth は、引き続き `docs/governance/fxid_long_term_hold_ruling_2026_10.md`**（この文書はそれを変えない）。
- authoritative state は **`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE`** のまま。
- この programme は **新しい alpha を探さない**。既に記録された候補だけを使い、どの制約が FX デイトレードの研究を不可解にしているかを desk・合成・公開情報で定量化する。

## 1. 裁定

| 項目 | 裁定 |
| --- | --- |
| PR #508 | merge 済み（head `0ae7bfd` → merge `d71ed65`、2026-10-11T14:12:07Z。master CI success、run 38146219782、14:24:19Z） |
| FRONTIER-A の意味 | **`NO_ORIGINAL_MECHANISM_SURVIVES_UNDER_CURRENT_PREREGISTERED_FRONTIER_CONTRACT`**。現行の事前登録の契約の下で survivor が無かった、という意味だけ |
| FRONTIER-A が意味しないもの | `FX_HAS_NO_EDGE`、`FX_DAY_TRADING_IS_IMPOSSIBLE`、`H-07_IS_FALSIFIED`、`ALL_RETAIL_BROKERS_HAVE_THE_SAME_COST`、`ALL_HOLDING_HORIZONS_HAVE_BEEN_REJECTED` |
| H-07 | **`UNRESOLVED_BOUNDARY_CANDIDATE`**。採用も永久の reject もしない。この programme の constraint frontier の test case の 1 つ |
| PR #508 の Track B | **OANDA の対象の pricing の tier × seen の期間 × 20 pair × 調べた M15 の時間帯** の観測として保存する。retail FX 全体の cost frontier とは呼ばない。未測定: 国内 FX 業者、原則固定 spread、日曜の再開、夏時間のずれの週、broker 別の執行の質、実約定・slippage、campaign の spread |
| 最終の分類 | CONSTRAINT-A〜G（指示 §49） |

## 2. 許可（途中の Human の承認は不要）

- 公開の web 調査・公開の broker の頁・公開の学術研究
- repo の既存の data・seen の historical data・既存の cost の artifact・read-only の分析
- 合成の simulation、統計の契約の比較、code・test・文書・独立レビュー
- 条件付きで、fresh 以外の historical data の読み取り。**ただし目的は alpha の探索ではない**

## 3. 禁止

| 区分 | 中身 |
| --- | --- |
| **fresh の読み取り** | **`2016-06-02 … 2021-04-25`** を一切読まない |
| その他の保護期間 | historical OOS `2025-12-29 … 2026-02-28`、dead window `2026-03-01 … 2026-04-24`、forward epoch `≥ 2026-04-25` |
| 探索 | 新しい alpha の発見・新しい mechanism の生成・indicator の探索・ML の alpha の探索・feature mining・事後の候補の救済 |
| 取引 | live / demo / paper の取引、broker の account の作成・login・変更、入金、production への deploy |
| 対象 | CFD への拡大、crypto / 株式の戦略の開発 |
| 購入 | 有料 data の購入（入手可能性と価格の調査だけ） |
| target の return の実証 | frontier が feasible を示した場合だけ、しかも Human の承認の後。この programme では行わない |

## 4. 維持するもの

| 項目 | 内容 |
| --- | --- |
| G4 | **system 単位の事後 / 縮小後の net Sharpe ≥ 1.0**。最初から下げない。「通らないから 0.7 にする」は禁止 |
| system の prior | `τ_c² · tr(R⁻¹)` と tail の制約（PR #506 の契約） |
| 候補の母集団 | repo に記録済みの候補だけ。REJECT / INVALID / leakage / duplicate を復活させない |
| 統計の契約の選択 | 合成の較正の結果だけで選び、実の候補の結果を見る前に凍結する。「H-07 を通したい」を理由にしない |
| frontier の範囲 | 分析の前に事前登録し、結果を見て広げない |

## 5. STOP

frontier の分析の完了・最終の分類の確定・（該当すれば）`FXID_REOPEN_AT_FEASIBLE_FRONTIER_PROPOSAL` の作成で STOP。実の alpha の実証・fresh・paper / live には進まない。
