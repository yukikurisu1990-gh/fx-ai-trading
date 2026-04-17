# D5. Retention Policy

## Purpose
一次DB (42 + backtest 2 = 44 物理テーブル) およびローカル永続ファイル (2) について、**保持期間 / アーカイブ手順 / 削除禁止条件 / 監査証跡**を単一ソースとして契約化する。`phase6_hardening.md` 6.21 の契約を拡張し、全テーブルに retention class を割り当て、Cold アーカイブ運用と No-Reset 原則の整合を明確化する。

## Scope
- Retention class 定義とテーブルマッピング (44 物理 + 2 ファイル全てカバー)
- Cold アーカイブの 3 段プロセスの具体化
- No-Reset ポリシーとの整合
- 監査証跡 / 復旧 / 違反検知
- Backup 方針
- Purge / Archive の実行責務

## Out of Scope
- バックアップツールの具体選定 (pg_dump / wal-g / pgbackrest 等、Iteration 1 以降)
- Cold アーカイブの物理ストレージ (ローカル / S3 / GCS、Phase 8 で具体化)
- 実アーカイブジョブのスケジュール・コード (MVP は契約のみ、実ジョブは Phase 7+)

## Dependencies
- `docs/schema_catalog.md` (D1): テーブル一覧と属性
- `docs/phase6_hardening.md` 6.21 (Retention vs No-Reset 契約)
- `docs/phase6_hardening.md` 6.5 (app_settings 初期値)
- `docs/backtest_design.md` (D2): `backtest_runs` / `backtest_metrics` の位置付け

## Related Docs
- `docs/implementation_contracts.md` (D3): Archiver / Retention Enforcer の Interface
- `docs/operations.md` (D4): Purge / Archive ジョブの運用と監視

---

## 1. 基本原則 (Inherited Constraints)

### 1.1 No-Reset 原則 (6.21 継承)

**定義**: 本番・準本番 DB に対する以下を禁止する:
- `TRUNCATE TABLE`
- `DROP TABLE` (migration 経由の破壊的変更、新旧 View 保全不在の場合)
- アーカイブを伴わないバルク削除

### 1.2 Cold アーカイブ原則 (6.21 継承)

**定義**: データを一次DB から削除する場合、**必ず以下の 3 段プロセス**を踏む:

1. **Copy** — 外部ストレージに export (MVP: ローカル `archives/{table}_{yyyymm}.parquet`、Phase 8: S3 等)
2. **Verify** — 行数・チェックサム・サンプル整合性を検証 (失敗時は 3 に進まない)
3. **Delete** — 検証成功後のみ一次DB から DELETE (パーティション `DROP PARTITION` が望ましい)

### 1.3 単純 DELETE 禁止

MVP 時点から**強制**される唯一の retention ルール。CI lint で以下を検出:
- コード内の `DELETE FROM` 直接発行 (Archiver 経由に限る)
- Alembic migration での TRUNCATE / DROP (View 保全と expand-contract を通ること)

### 1.4 グローバル既定値と per-category 上書き (6.5 / 6.21 整合)

**Decision (1.4-1)**: 6.5 の `retention_hot_days=7` / `retention_warm_days=90` / `retention_cold_years=2` は**デフォルト値**。カテゴリ別・テーブル別の retention (本書 3 章) は**上書き**として作用する。矛盾時は**カテゴリ別が優先**。

**Rationale**: 単一値では表現できない多様性 (Market raw は Hot 30d、Supervisor は Cold 移動なし、Outbox は 30d 以降直接削除等) に対応するため。

---

## 2. Retention Class 定義

以下 8 クラスに分類する:

### 2.1 `REFERENCE_PERMANENT`
- **方針**: 永続保持、Cold 移動なし
- **対象**: マスタデータ・設定履歴・モデルレジストリ
- **根拠**: 履歴参照頻度が高く、体積が小さい
- **削除可能条件**: ない (masa なし)
- **監査**: 変更履歴を別途 `app_settings_changes` / `model_registry` の状態遷移で保持

### 2.2 `EXECUTION_PERMANENT`
- **方針**: 永続保持、Cold 移動なし
- **対象**: 発注・約定・ポジション・決済・口座スナップショット
- **根拠**: 法的・税務・監査要件 (最低 7 年保存が日本の FX 税務慣行)
- **削除可能条件**: ない
- **監査**: 税務エクスポート (Phase 8) の根拠データ

### 2.3 `AGGREGATE_PERMANENT`
- **方針**: 永続保持、Cold 移動なし
- **対象**: ロールアップ集計 (`strategy_performance`, `meta_strategy_evaluations`, `daily_metrics`)
- **根拠**: 体積が小さく、長期トレンド分析・改善ループで頻用
- **削除可能条件**: ない
- **再計算**: Aggregator は idempotent、元データが残る限り再計算可能

### 2.4 `SUPERVISOR_PERMANENT`
- **方針**: 永続保持、Cold 移動なし (Hot 90d / Warm 2y / 以降も削除せず運用 DB に保持)
- **対象**: `supervisor_events`, `reconciliation_events`
- **根拠**: 事故・障害検証の根幹、いつでも素早く SQL アクセスできる必要
- **削除可能条件**: ない

### 2.5 `DECISION_LOGS_TIERED`
- **方針**: Hot 7d / Warm 90d / Cold 2y 以降アーカイブ + DB 削除
- **対象**: 判断系ログ (全候補シグナル / meta 判断 / 特徴量スナップショット / EV 内訳 / 予測 / Select 明細 / 相関スナップショット)
- **根拠**: 体積大、短期はオンライン参照、長期は外部アーカイブで改善ループ可能

### 2.6 `OBSERVABILITY_TIERED`
- **方針**: Hot 7d / Warm 90d / Cold 1y 以降アーカイブ + DB 削除 (サンプリング許可)
- **対象**: 観測系 (no_trade / drift / data_quality / anomalies / stream_status / retry)
- **根拠**: 診断用、短期アクセスが中心、長期は要約保持で十分

### 2.7 `MARKET_RAW_TIERED`
- **方針**: Hot 30d / Warm 1y / Cold 3y 以降アーカイブ + DB 削除
- **対象**: Market raw (candles / ticks / economic events)
- **根拠**: Hot は backtest 直近短期で頻用、Cold は再取得可能性が高い

### 2.8 `OUTBOX_NONPERSISTENT`
- **方針**: dispatch 済は Hot 30d / Warm 90d 以降**直接削除可** (Cold 不要)
- **対象**: `outbox_events`, `notification_outbox`
- **根拠**: 業務データではなく dispatch 管理用。消えても業務影響なし
- **例外**: Outbox でも **未 dispatch で古いもの (90d 超)** は data_quality_events にログして調査対象

### 2.9 `RUNTIME_STATE_ROLLING`
- **方針**: 直近 N 件 + 履歴 30d 保持
- **対象**: `app_runtime_state`
- **根拠**: 稼働中の正本ではなく、再起動 Reconciler の起点。直近とちょっとの履歴で十分

---

## 3. テーブル別 Retention マッピング (完全版)

D1 の 44 物理テーブル (42 Phase 6 canonical + 2 backtest 用) + 2 ローカルファイルを**全件カバー**する。

### 3.1 一次DB テーブル (44)

| # | Physical | Retention Class | Hot | Warm | Cold | 備考 |
|---|---|---|---|---|---|---|
| 1 | `brokers` | REFERENCE_PERMANENT | — | — | — | 永続、変更は稀 |
| 2 | `accounts` | REFERENCE_PERMANENT | — | — | — | 永続 |
| 3 | `instruments` | REFERENCE_PERMANENT | — | — | — | 永続 (追加・削除は稀) |
| 4 | `app_settings` | REFERENCE_PERMANENT | — | — | — | 現行値、変更履歴は `app_settings_changes` |
| 5 | `market_candles` | MARKET_RAW_TIERED | 30d | 1y | 3y+ archive | パーティション (tier, month) |
| 6 | `market_ticks_or_events` | MARKET_RAW_TIERED | 30d | 1y | 3y+ archive | パーティション (month)、ハートビート類はサンプリング |
| 7 | `economic_events` | REFERENCE_PERMANENT | — | — | — | 過去の指標も永続保持 (backtest で使う) |
| 8 | `training_runs` | REFERENCE_PERMANENT | — | — | — | **D5 で追加確定** (6.21 欠落分)。学習履歴は永続 |
| 9 | `model_registry` | REFERENCE_PERMANENT | — | — | — | モデル一覧・状態遷移 |
| 10 | `model_evaluations` | REFERENCE_PERMANENT | — | — | — | **D5 で追加確定**。評価結果は永続 (model_registry と紐づく) |
| 11 | `predictions` | DECISION_LOGS_TIERED | 7d | 90d | 2y+ archive | 体積大、パーティション (month) |
| 12 | `strategy_signals` | DECISION_LOGS_TIERED | 7d | 90d | 2y+ archive | 最大量、retention_class 列で条件付サンプリング可 |
| 13 | `pair_selection_runs` | DECISION_LOGS_TIERED | 7d | 90d | 2y+ archive | |
| 14 | `pair_selection_scores` | DECISION_LOGS_TIERED | 7d | 90d | 2y+ archive | |
| 15 | `meta_decisions` | DECISION_LOGS_TIERED | 7d | 90d | 2y+ archive | |
| 16 | `feature_snapshots` | DECISION_LOGS_TIERED | 7d | 90d | 2y+ archive | compact_mode 既定で体積抑制 (6.10) |
| 17 | `ev_breakdowns` | DECISION_LOGS_TIERED | 7d | 90d | 2y+ archive | |
| 18 | `correlation_snapshots` | DECISION_LOGS_TIERED | 7d | 90d | 2y+ archive | 窓種別ごとに独立 |
| 19 | `trading_signals` | EXECUTION_PERMANENT | — | — | — | 発注一式、法的・監査 |
| 20 | `orders` | EXECUTION_PERMANENT | — | — | — | 永続、state machine 履歴含む |
| 21 | `order_transactions` | EXECUTION_PERMANENT | — | — | — | 永続 (税務)。ハートビート系は要約済 |
| 22 | `positions` | EXECUTION_PERMANENT | — | — | — | 永続 (ポジション推移の時系列) |
| 23 | `close_events` | EXECUTION_PERMANENT | — | — | — | 永続 (決済事由は税務説明責任) |
| 24 | `execution_metrics` | DECISION_LOGS_TIERED | 7d | 90d | 2y+ archive | 執行品質、体積中規模 |
| 25 | `no_trade_events` | OBSERVABILITY_TIERED | 7d | 90d | 1y+ archive | taxonomy 別サンプリング可 |
| 26 | `drift_events` | OBSERVABILITY_TIERED | 7d | 90d | 1y+ archive | |
| 27 | `account_snapshots` | EXECUTION_PERMANENT | — | — | — | 永続 (残高推移は税務・監査) |
| 28 | `risk_events` | OBSERVABILITY_TIERED | 7d | 90d | 1y+ archive | **D5 で追加確定** (6.21 欠落分) |
| 29 | `stream_status` | OBSERVABILITY_TIERED | 7d | 90d | 1y+ archive | |
| 30 | `data_quality_events` | OBSERVABILITY_TIERED | 7d | 90d | 1y+ archive | |
| 31 | `reconciliation_events` | SUPERVISOR_PERMANENT | 90d | 2y | **永続** (Cold 移動なし) | 事故検証の根幹 |
| 32 | `retry_events` | OBSERVABILITY_TIERED | 7d | 90d | 1y+ archive | |
| 33 | `anomalies` | OBSERVABILITY_TIERED | 7d | 90d | 1y+ archive | |
| 34 | `strategy_performance` | AGGREGATE_PERMANENT | — | — | — | 永続、体積小 |
| 35 | `meta_strategy_evaluations` | AGGREGATE_PERMANENT | — | — | — | 永続、反実仮想含む |
| 36 | `daily_metrics` | AGGREGATE_PERMANENT | — | — | — | 永続、日次 KPI |
| 37 | `system_jobs` | `OPERATIONS_MEDIUM` (派生) | 180d | 1y | 永続 | ジョブ履歴、トラブルシュート用に長期 |
| 38 | `app_runtime_state` | RUNTIME_STATE_ROLLING | 直近 + 30d | — | — | 再起動 Reconciler の起点 |
| 39 | `outbox_events` | OUTBOX_NONPERSISTENT | 30d | 90d | 直接削除可 | dispatch 済のみ削除、未 dispatch は残す |
| 40 | `notification_outbox` | OUTBOX_NONPERSISTENT | 30d | 90d | 直接削除可 | 同上 |
| 41 | `supervisor_events` | SUPERVISOR_PERMANENT | 90d | 2y | **永続** (Cold 移動なし) | safe_stop / config_version / account_type verification 等 |
| 42 | `app_settings_changes` | REFERENCE_PERMANENT | — | — | — | 設定変更履歴、永続 |
| 43 | `backtest_runs` (D2 追加) | AGGREGATE_PERMANENT | — | — | — | 永続、backtest の主記録 |
| 44 | `backtest_metrics` (D2 追加) | AGGREGATE_PERMANENT | — | — | — | 永続、体積小 |

**Decision (3.1-1)**: `system_jobs` は中期保持クラス `OPERATIONS_MEDIUM` を新設 (Hot 180d / Warm 1y / それ以降は DB 内保持)。ジョブのトラブルシュートで過去 1 年程度の参照が頻繁なため Cold 移動しない。

### 3.2 ローカルアーティファクト (2 ファイル)

| # | Path | Retention | 削除方針 | 備考 |
|---|---|---|---|---|
| L1 | `logs/safe_stop.jsonl` | 日次ローテ、**180d 保持** | ローテ済の古いファイルから削除 | safe_stop 発火の二次正本、DB と突合済みの古い分は削除可 |
| L2 | `logs/notifications.jsonl` | 日次ローテ、**90d 保持** | ローテ済の古いファイルから削除 | 通知の最終フォールバック記録 |

**Rationale**: ローカルファイルは DB 比較で体積が大きくなりにくい (1 日数 KB〜数 MB)。短期保持で十分。Cold アーカイブ対象外 (DB のアーカイブジョブとは独立にファイルローテで管理)。

---

## 4. Cold アーカイブ手順の具体化

### 4.1 Copy 段階

**責務**: Archiver (D3 で定義される Interface)

**入力**: `table_name` / `partition_key` (例: `year_month`)

**処理**:
1. 対象パーティション / 対象期間の行を抽出
2. 外部ストレージに**Parquet 形式**で export (`archives/{table}_{partition}.parquet`)
3. メタデータを `system_jobs` に記録 (job_type=`cold_archive_copy`、result_summary_json に行数・checksum・path)
4. Copy 中のエラーは `anomalies` に記録し、Retry Policy で再試行

**Inherited Constraint (4.1-1)**: Copy 中に対象テーブルへの書込を**ブロックしない** (Postgres は snapshot isolation、WHERE 条件で読むだけなので影響軽微)。

### 4.2 Verify 段階

**責務**: Archiver

**処理**:
1. Parquet から行数を読み、DB 側と一致確認
2. Parquet のサンプル行 (先頭 N 行 + ランダム N 行) を DB と突合、完全一致
3. チェックサム (例: SHA256 of canonical JSON) を事前計算値と照合
4. Verify 失敗時: `system_jobs.status=failed`、Notifier warning、Copy から再実行 (次回ジョブで)

**Decision (4.2-1)**: Verify が失敗する限り、次の Delete 段には**絶対に進まない** (データ喪失防止)。失敗が連続する場合は Notifier critical + 調査待ち。

### 4.3 Delete 段階

**責務**: Archiver

**処理**:
1. Verify 成功を `system_jobs.status=verified` で確認
2. パーティション単位の `DROP PARTITION` を優先 (大量 DELETE より高速・ロック軽)
3. パーティション非対応テーブルは `DELETE FROM ... WHERE partition_key = ...` で実施
4. 結果を `system_jobs.status=completed` で記録
5. アーカイブ完了イベントを `supervisor_events` に記録 (`event_type=cold_archive_completed`)

**Inherited Constraint (4.3-1)**: Delete 後の整合性検証として、対象テーブルの最新 MIN(partition_key) が想定値以上になっていることを確認。想定値未満なら即座に rollback (アーカイブログに残し調査)。

### 4.4 Archive 失敗時の挙動

- Verify 失敗 → Delete に進まない、次回再実行
- Delete 中のエラー → トランザクションロールバック、`anomalies` + Notifier
- Copy と Verify の整合性破綻 → critical 通知、手動調査

---

## 5. No-Reset ポリシーとの整合

### 5.1 No-Reset の厳格解釈

以下は一次DB (本番・準本番) で**常に禁止**:
- `TRUNCATE TABLE`
- `DROP TABLE ... CASCADE` (migration 経由の破壊的変更、旧 View 保全なし)
- 単純 DELETE (Archiver 経由でなく直接)

### 5.2 Cold アーカイブの No-Reset 整合

Cold アーカイブの Delete 段は**例外的に DELETE を実行する**が、以下を満たす限り No-Reset と整合:
- 外部ストレージにコピー済 + 検証済
- 対象が**Cold 移動対象のカテゴリ** (本書 2. の DECISION_LOGS_TIERED / OBSERVABILITY_TIERED / MARKET_RAW_TIERED / OUTBOX_NONPERSISTENT のみ)
- Archiver Interface 経由 (手動 SQL ではない)
- 実行ログが `system_jobs` + `supervisor_events` に残る

### 5.3 開発環境の扱い

- `environment=local` の開発 DB は No-Reset の対象外 (自由に TRUNCATE / DROP 可)
- `environment ∈ {vps, aws}` は厳格 No-Reset

### 5.4 Migration での破壊的変更

- 列追加・新テーブル追加は自由 (expand-contract)
- 列削除 / テーブル削除は View で旧名保全 + 実体は別 migration で段階的削除
- Alembic revision の up/down/up 往復テストを CI (Phase 7) で実施、自動検出

---

## 6. 監査証跡の保持

### 6.1 永続保持必須項目 (EXECUTION_PERMANENT + REFERENCE_PERMANENT)

以下は**永久に削除しない**:
- 全発注・約定・決済 (`trading_signals`, `orders`, `order_transactions`, `positions`, `close_events`)
- 口座スナップショット (`account_snapshots`)
- マスタ (`brokers`, `accounts`, `instruments`, `app_settings`, `app_settings_changes`)
- モデル系 (`model_registry`, `training_runs`, `model_evaluations`)
- 安全系 (`supervisor_events`, `reconciliation_events`, L1 `safe_stop_journal`)

### 6.2 再現性保持項目

以下はアーカイブされても外部から参照可能:
- 判断系 (`strategy_signals`, `meta_decisions`, `ev_breakdowns`, `feature_snapshots`, `predictions`, `correlation_snapshots`)
- 執行品質 (`execution_metrics`)

**Rationale**: 戦略変更後に過去の判断を再現 / 反実仮想で再評価するために必要。外部アーカイブ (Parquet) を DB に temp import して分析可能。

### 6.3 税務対応 (日本 FX)

- FX 取引記録は最低 **7 年間**保持 (日本の税法慣行)
- EXECUTION_PERMANENT クラスは無期限なので自動的に満たす
- Phase 8 の税務エクスポート GUI では、年度指定で CSV 生成、7 年遡れるか確認

---

## 7. Model / Strategy / Config / Prediction / Execution の対応関係保持

改善ループの前提として、以下の**チェーン**が常に成立していること:

```
code_version
  → strategy_version (各戦略モジュール)
    → feature_version (Feature Service)
      → model_version (AIStrategy が使った)
        → config_version (その時点の app_settings + env)
          → cycle_id (1 分足単位)
            → meta_decision_id
              → trading_signal_id
                → order_id (ULID)
                  → fill / close_event
                    → account_snapshot (事後残高)
```

このチェーンが Common Keys と FK で保証されるため、**任意の決済に対して「どのコード・どの設定・どのモデル・どの判断・どの発注から生まれたか」が遡及可能**。

**Decision (7-1)**: 上記チェーン上のいずれのテーブル行も、永続保持または Archive 可能であること。外部 Archive された行も Parquet の Common Keys 列を頼りに再結合可能。

---

## 8. バックアップ方針

### 8.1 一次DB バックアップ

**Decision (8.1-1)**: MVP から以下を必須:
- **日次論理ダンプ** (`pg_dump -Fc`) を毎日 00:30 UTC に実行
- **WAL アーカイブ** (`wal-g` or 同等) で PITR (Point-In-Time Recovery) 可能に
- 保存先は**別ストレージ** (ローカル SSD + 外部 SSD or クラウド)
- RPO: 24h (論理ダンプ) + WAL 範囲内では分単位
- RTO: 2h (MVP、Phase 8 の DR 訓練で改善)

### 8.2 ローカルファイル (L1 / L2) バックアップ

- L1 `safe_stop.jsonl`: 日次ローテ後、日次バックアップに含める
- L2 `notifications.jsonl`: 日次ローテ後、週次バックアップに含める (重要度低)

### 8.3 Cold アーカイブ (Parquet) バックアップ

- MVP: ローカル別ディスクで冗長化
- Phase 8: S3 等のクラウドストレージで 3-2-1 バックアップ (3 コピー / 2 メディア / 1 オフサイト)

### 8.4 バックアップ整合性検証

- 月次: 論理ダンプのリストアテスト (staging 環境で pg_restore、エラーなし確認)
- 月次: Cold アーカイブのランダム行 Verify (Parquet 読み出し → DB 一時 import → 整合確認)
- 失敗時: `anomalies` + Notifier warning、調査

---

## 9. Purge / Archive の実行責務

### 9.1 Archiver の起動

- **バッチ方式**: cron-like (systemd timer / cron / APScheduler) で日次トリガ
- **MVP は手動キック可**: `ctl run-archive-job --table=strategy_signals --partition=2026-04` のような CLI
- 実行単位: `system_jobs` に 1 行作成、status=queued→running→completed/failed

### 9.2 Archiver の責任範囲

- 各テーブルの retention class に従い、Hot/Warm/Cold 境界を越えた行を処理
- Cold 対象は 4. の 3 段プロセス、非 Cold 対象 (REFERENCE / EXECUTION / AGGREGATE / SUPERVISOR_PERMANENT / RUNTIME_STATE_ROLLING) はスキップ
- OUTBOX_NONPERSISTENT は直接削除 (Archive なし)
- 実行結果を `system_jobs` + 該当 tier 移動を `supervisor_events` に記録

### 9.3 MVP スコープ (実装)

**Decision (9.3-1)**: MVP 時点では:
- Archiver Interface と retention class 割当は**完全に定義**
- 実 Archive ジョブ本体は**実装しない** (Phase 7 以降に回す)
- ただし**「単純 DELETE 禁止」**は CI lint で MVP から強制
- データが溜まり続けることを許容する (MVP 期間 3-6 ヶ月では限界に達しない体積試算)
- Hot/Warm/Cold の境界チェック機能 (計測のみ、削除なし) を MVP で入れ、境界超過を `data_quality_events` にログ

**Rationale**: MVP の本数・期間を考慮すると、Archive ジョブの実装よりも live 運用の安定化を優先すべき。retention 契約だけ先に固定し、データ蓄積が問題化する前に Phase 7 で実装。

---

## 10. 障害時復旧との整合

### 10.1 DB 破損からのリストア

1. 直近論理ダンプをリストア (pg_restore)
2. WAL を applied して PITR
3. Reconciler が起動時に OANDA から現在ポジションを取得、DB と突合 (6.12 Action Matrix)
4. Cold アーカイブ済みデータは必要に応じて temp import して分析 (業務稼働には不要)

### 10.2 Cold アーカイブが復旧の一部になる場合

通常は Cold アーカイブ = 過去データなので復旧クリティカルパスに含まれない。ただし以下のケースで必要:
- 長期間跨ぐ分析クエリ (backtest を 3 年分走らせる等)
- 監査対応 (税務調査で 5 年前のデータ要求)

**Decision (10.2-1)**: Cold Archive の**一時リストア Interface**を `ColdRestorer` として D3 で定義 (Phase 7 実装)。MVP では手動で Parquet を analytics 用 temp table に import する運用。

### 10.3 SafeStopJournal の復旧時の役割

- 再起動時に L1 (`safe_stop.jsonl`) を読み、直近の safe_stop を DB (`supervisor_events`) と突合
- L1 にあって DB にない記録 → DB に補完挿入 (Reconciler が実施)

---

## 11. Retention 違反検知

以下を**自動検出**する仕組み:

### 11.1 静的検知 (CI / コードレビュー)

- `DELETE FROM` 直接発行を grep + AST check で検出
- Archiver Interface を経由しない DELETE は CI 失敗
- `TRUNCATE` / `DROP TABLE` の migration 直接使用を CI 失敗

### 11.2 動的検知 (運用時)

- 各テーブルの行数トレンドを監視 (`daily_metrics` に `row_count_by_table_*` を追加するか、独立メトリクスとして)
- 予期しない急減 (急激な DELETE) → `anomalies` + Notifier critical
- 予期しない急増 (アーカイブされるべきデータの蓄積) → warning

### 11.3 監査ログ

- Archive ジョブの実行履歴を `system_jobs` で保持
- 各テーブルで「最後にアーカイブした partition」を `archive_state` メタテーブル (Phase 7 追加予定) で管理

---

## 12. C6 再発防止の観点

Phase 5 / Phase 6 レビューで指摘された **Critical C6 "Retention と No-Reset の整合性"** の再発防止:

| C6 の論点 | 本書での解消 |
|---|---|
| "物理リセットしない" と "Cold アーカイブで削除" の文面矛盾 | 5.1 / 5.2 で「No-Reset は破壊禁止、Cold は 3 段プロセスの論理移管」と分離定義 |
| 削除対象と永続対象の曖昧 | 2. で Retention class を 9 種類に明確定義、3. で 44 テーブル + 2 ファイル**全件**にクラス割当 |
| 6.21 で漏れた 3 テーブル (training_runs, model_evaluations, risk_events) | 3.1 で明示マッピング (training_runs / model_evaluations は REFERENCE_PERMANENT、risk_events は OBSERVABILITY_TIERED) |
| 6.5 グローバル retention vs 6.21 カテゴリ別の主従不明 | 1.4 で「カテゴリ別が優先、6.5 は default」と明記 |
| Archive 手順の曖昧 | 4. で Copy→Verify→Delete の各段を具体化、失敗時挙動も明記 |
| 監査証跡の保証 | 6. / 11. で監査証跡と違反検知を仕様化 |

---

## 13. 運用責務とスケジュール

### 13.1 責務分担

| 責務 | 担当 | タイミング |
|---|---|---|
| Archiver 起動 | Scheduler / cron | 日次 02:00 UTC (取引影響少ない時間帯) |
| ジョブ結果監視 | Supervisor / Notifier | Archive ジョブ failed で critical 通知 |
| Retention 違反検知 | CI (静的) / 定期メトリクス (動的) | PR 時 / 日次 |
| バックアップ実行 | 独立 cron (アプリ外) | 日次 00:30 UTC |
| リストアテスト | 運用者 | 月次 (Phase 7 で自動化) |
| DR 訓練 | 運用者 | 月次 (Phase 8 で定例化) |

### 13.2 通知対象 (6.13 Notifier と整合)

以下は Notifier 必須イベント:
- `archive.verify_failed` (critical)
- `archive.delete_succeeded` (info、1 日分まとめ)
- `retention.row_count_anomaly_detected` (warning)
- `backup.pg_dump_failed` (critical)
- `backup.restore_test_failed` (critical、月次テスト時)

---

## 14. Open Questions

| ID | 論点 | 解決予定 |
|---|---|---|
| RP-Q1 | Cold Archive の物理ストレージ選定 (ローカル SSD / S3 / GCS) | Phase 7 / Phase 8 で環境別に判断 |
| RP-Q2 | Parquet vs JSON Lines の選択 | Phase 7 実装時、Parquet 優先 (カラムナ形式で分析向き) |
| RP-Q3 | パーティション粒度 (月次 / 週次 / 日次) | Iteration 1 実装時、テーブル別に決定 (market_candles は月次、feature_snapshots は週次等) |
| RP-Q4 | 税務 7 年要件を満たす外部アーカイブの法的保全方式 | Phase 8 で会計士・税理士と協議 |
| RP-Q5 | `archive_state` メタテーブルの要否 | Phase 7 で Archiver 実装時に判断 |

---

## 15. Summary (契約固定点)

本書は以下を**MVP 実装に向けた契約**として固定する:

1. **Retention class 9 種類**で 44 DB テーブル + 2 ローカルファイル**全件**カバー
2. **No-Reset 原則**は「破壊禁止」、Cold アーカイブは「Copy→Verify→Delete の 3 段論理移管」で両立
3. **単純 DELETE 禁止**は MVP から CI lint で強制
4. **EXECUTION_PERMANENT / REFERENCE_PERMANENT / AGGREGATE_PERMANENT / SUPERVISOR_PERMANENT** は Cold 移動なし (永続)
5. **DECISION_LOGS_TIERED / OBSERVABILITY_TIERED / MARKET_RAW_TIERED** は Hot/Warm/Cold 階層で Cold Archive 対象
6. **OUTBOX_NONPERSISTENT** は Cold 不要で直接削除可 (dispatch 済のみ)
7. **6.5 グローバル vs カテゴリ別 retention** はカテゴリ優先、6.5 は default 扱い
8. **MVP で Archive ジョブ実装は不要**、retention 契約と「単純 DELETE 禁止」のみ強制
9. **バックアップは MVP から必須** (日次論理ダンプ + WAL アーカイブ、RPO 24h / RTO 2h)
10. **C6 はこれで解消**、以降 Phase 7 で Archive ジョブ実装時に本書を単一ソースとする
