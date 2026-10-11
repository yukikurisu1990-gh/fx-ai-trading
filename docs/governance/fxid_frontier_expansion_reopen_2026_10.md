# FXID Frontier Expansion — `FXID_FRONTIER_EXPANSION_REOPEN`（2026-10-11）

`PRODUCTION_READINESS_NOT_CLAIMED`.

**位置づけ**: Human + ChatGPT の指示「FXID Frontier Expansion — Original Mechanism Research + Execution Frontier Fast-Track」（2026-10-11）の記録。

- **FXID の研究状態の single source of truth は、引き続き `docs/governance/fxid_long_term_hold_ruling_2026_10.md`**。
- この文書は、その中での一度限りの範囲付きの再開を記録する。
- 失敗した場合（指示 §47 の FRONTIER-A〜D）は、HOLD に戻る。

## 1. 裁定

| 項目 | 裁定 |
| --- | --- |
| 前回の結果 | `DISCOVERY-A — NEW_COMPONENT_SUPPLY_NOT_FOUND` を受け入れる |
| PR #507 | merge 済み（head `47be79d` → merge `f91e20d`） |
| 転換 | **literature-first から mechanism-first の original research へ**。文献に完成済みの edge があることを候補の条件にしない |
| 手順 | mechanism → 検定できる仮説 → 方向・timing・情報集合 → 事前登録 → data の取得 → 1 回の実証 → 独立な推定 → portfolio / system の統合 |
| 2 つの track | Track A `ORIGINAL_MECHANISM_DISCOVERY`、Track B `EXECUTION_COST_FRONTIER`（並行） |
| 到達してよい最終段 | `SYSTEM_CANDIDATE_READY_FOR_FORMAL_CONFIRMATION`（FRONTIER-E）。fresh の確認の事前登録の草案まで作り、fresh を読む直前で STOP |

## 2. 許可（途中の Human の承認は不要）

- 公開の文献の調査、mechanism の設計、original な仮説、事前登録
- 公開 / 利用権のある過去の data の取得（OANDA の historical の read-only を含む）
- price / bid-ask / 公開の macro・金利・先物・option の data の読み取り
- component の検定、独立な推定、cost の model、portfolio の構築
- 合成の P2、Architecture H の評価、条件付きの G
- code、test、独立レビュー

## 3. 禁止（どこまで進んでも）

| 区分 | 中身 |
| --- | --- |
| **fresh の読み取り** | **`2016-06-02 … 2021-04-25`** を一切読まない。戦略の選択・特徴量の選択・mechanism の検証・効果の推定・parameter・portfolio・共分散・debug を含む |
| その他の保護期間 | historical OOS `2025-12-29 … 2026-02-28`、dead window `2026-03-01 … 2026-04-24`、forward epoch `≥ 2026-04-25`（CLAUDE.md の常時の拘束。厳しい方を採る） |
| 取引 | live / demo / paper の取引、実際の資金の執行、account の変更、入金・出金、leverage の変更、broker の position、production への deploy |
| broker の API | historical / read-only だけ |
| 対象の資産 | FX だけを取引する。CFD・crypto・株式・commodity の取引に逃げない（それらの data を FX の予測の情報源に使うことは可） |
| 探索 | 仮説の無制限の拡大、indicator の grid、ML の総当たりの alpha の発見、事後の救済 |
| 購入 | 新しい有料 data の購入は、Human の承認なしに行わない |

## 4. 予算（結果を見て増やさない）

| 項目 | 上限 |
| --- | --- |
| 実証する original mechanism family | 3 |
| family ごとの primary hypothesis | 1 |
| family ごとの secondary variant | 1 |
| 実証の variant の合計 | 6 |
| data の取得の package | 3 |
| 候補の生成（data を見る前） | 5〜10。data を見る前に、最大 3 family に絞る |

## 5. 維持するもの

| 項目 | 内容 |
| --- | --- |
| G4 | **system 単位の事後 / 縮小後の net Sharpe ≥ 1.0** |
| system の prior | `τ_c² · tr(R⁻¹)` の 2 次の moment の整合と、system 単位の tail の制約（PR #506 の契約） |
| architecture | Architecture H を baseline にし、G は事前の基準で H を上回る場合だけ |
| 数え方 | 同じ mechanism の複数の窓や pair を、別の family として数えない |
