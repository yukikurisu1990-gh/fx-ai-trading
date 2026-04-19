# Iteration 1 Completion Record

## 1. 判定サマリ

- **判定**: **Complete**
- **判定日**: 2026-04-19
- **判定種別**: Conditional Complete から昇格（Iteration 2 Carryover 明示化により正式完了）
- **判定根拠**:
  - Blocker: **0 件**
  - 総テスト: **511 passed / 0 failed**（contract 240 / unit 186 / integration 76 / migration 9）
  - ruff check / ruff format / custom lint すべて green
  - 契約テスト 15 本（M1–M11 対応）すべて保持
  - Supervisor startup 16 Step + safe_stop fire sequence 完全 green
  - Outbox 同一 tx / ULID / Reconciler Action Matrix / in-flight handling 保持
  - Strategy determinism / no-lookahead / 3 戦略 / Meta 3 段 保持
  - Risk 4 制約 / ExecutionGate TTL / Defer 保持
  - paper smoke 1 cycle end-to-end（Feature→Meta→Gate→PaperBroker→filled）green

**本記録により Iteration 1 は正式に「完了」とする**。未達・部分達成の項目は全て Iteration 2 Carryover として後述の通りスコープ管理下に置かれる。

---

## 2. 最終検証結果

### 2.1 テスト集計

| カテゴリ | 件数 | 状態 |
|---------|------|------|
| contract | 240 | all green |
| unit | 186 | all green |
| integration | 76 | all green |
| migration | 9 | all green（alembic deprecation warning のみ） |
| **合計** | **511** | **全 green** |

### 2.2 E2E 到達度（8 ステップ基準）

| # | ステップ | 到達 |
|---|---------|------|
| 1 | 起動シーケンス成功 | ✅ |
| 2 | market / feature / strategy / meta 最小判断 | ✅ |
| 3 | gate / outbox / broker 通過 | ✅ |
| 4 | order 記録 | ✅ |
| 5 | 擬似約定 / paper flow 反映 | ✅ |
| 6 | position 更新 | ✅ |
| 7 | exit policy 発火 | ❌（Iteration 2 Carryover: M-EXIT-1） |
| 8 | dashboard 実データ表示 | ⚠️ 構造のみ（Iteration 2 Carryover: Mi-DASH-1） |

**到達度: 6 / 8**。残り 2 ステップは Iteration 2 スコープ。

### 2.3 MVP §12 到達条件 10 項目

| # | 条件 | 達成 | Iteration 2 対応 ID |
|---|------|------|---------------------|
| 1 | M1-M12 完了 | ⚠️ Partial | M-METRIC-1 |
| 2 | alembic 46 tables + legacy View | ✅ Full | — |
| 3 | `ctl start` で 16 Step 全 green | ⚠️ Partial | Mi-CTL-1 |
| 4 | 1 cycle 発注→擬似約定→**決済** end-to-end | ❌ | **M-EXIT-1** |
| 5 | Streamlit 7 パネルデータ表示 | ⚠️ Partial | Mi-DASH-1 |
| 6 | 学習 UI 最小機能 | ❌ | **M-LRN-1** |
| 7 | safe_stop 正常発火・復帰 | ✅ Full | — |
| 8 | Contract 8 + 禁止 lint 10 | ✅ Full | — |
| 9 | PostgreSQL 全ログ + Common Keys 1 本 SQL 分析 | ❌ | M-METRIC-1 |
| 10 | Notifier 二経路 | ✅ Full | — |

---

## 3. M1–M12 達成状況

| M | 名称 | 達成度 | 備考 |
|---|------|--------|------|
| M1 | Tooling | Full | ruff / format / lint / CI / pre-commit |
| M2 | Schema | Full | 46 tables + legacy View + seed + up/down/up |
| M3 | Config/Foundations | Full | config_version / ULID / NTP / Clock / CommonKeys |
| M4 | Interfaces | Full | 30+ Protocol + DTO frozen + 例外階層 |
| M5 | Repository | Full | FSM / Common Keys 自動伝搬 / DELETE 禁止 |
| M6 | Broker/Notifier/Journal | Full | account_type / 二経路 / SafeStopJournal |
| M7 | Supervisor | Partial | 16 Step + fire sequence 完成 / **1 分毎メトリクス記録ループ未実装（M-METRIC-1）** |
| M8 | Outbox/Lifecycle | Full | 同一tx / ULID / Action Matrix / in-flight（MidRunReconciler 骨格のみ = 計画書通り） |
| M9 | Strategy | Full | Feature determinism / no-lookahead / 3 戦略 / Meta 3 段 |
| M10 | Risk/Gate | Full | PositionSizer / Risk 4 制約 / TTL / Defer |
| M11 | Contract Hardening | Full | 契約 8 項目以上 + 禁止 lint 10+ 項目 |
| M12 | Dashboard/Smoke | Partial | 7 panel 構造 / paper smoke（**exit 未含 = M-EXIT-1**）/ ctl stub（Mi-CTL-1） |

---

## 4. Iteration 2 Carryover Items

**本セクションは grep 対応 ID を保持する**。Iteration 2 計画時は各 ID で直接参照すること。

### 4.1 Major（Iteration 2 で解消必須）

#### M-EXIT-1

- **内容**: ExitPolicy / close_event までの end-to-end 疎通が未到達。`tests/integration/test_paper_smoke_end_to_end.py` は Feature→Meta→Gate→PaperBroker→filled までで停止し、TP/SL/time 発火 → close_event 記録 → position クローズの経路が smoke に含まれていない。
- **影響**: MVP §12 #4（1 cycle 分足判断 → 発注 → 擬似約定 → **決済** end-to-end 完走）
- **Iteration 2 での担当領域**: Iteration 2 主対象①「ExitPolicy 完成」
- **理由**: ExitPolicy は Phase 7 の Backtest / AI 実体化領域と設計が強く結合する（SlippageModel / LatencyModel / 反実仮想計算と共有型）。Iteration 1 で無理に簡易版を入れるより、Iteration 2 で Broker 強化（live 接続）と同時に ExitPolicy 本体を仕上げる方が整合的。

#### M-METRIC-1

- **内容**: Supervisor の「メトリクス 9 項目を 1 分毎に `supervisor_events` へ記録する常駐ループ」が未実装。`supervisor_events_repo.insert` の呼出口（`supervisor/startup.py::_emit_supervisor_event` / `supervisor/safe_stop.py`）は存在し startup / safe_stop イベントは記録されるが、周期的なメトリクス出力パスが無い。
- **影響**: MVP §12 #1（M1–M12 完了）/ #9（PostgreSQL 全ログ + Common Keys + cycle_id / correlation_id で 1 本 SQL 分析可能）
- **Iteration 2 での担当領域**: Iteration 2 主対象⑤「Observability / Metrics」
- **理由**: 1 分毎メトリクス記録は運用監視レイヤーであり、Iteration 2 の Dashboard 実データ統合（残り 3 panel）・Supabase Projector 実装と合わせて拡張するのが自然。単発で Iteration 1 に追加すると Dashboard の実データ結線が別サイクルで必要になり非効率。

#### M-LRN-1

- **内容**: 学習 UI（enqueue / status / history）最小機能の存在確認が未実施。計画書 §12 #6 に明記あり。
- **影響**: MVP §12 #6（学習 UI 最小機能が動作）
- **Iteration 2 での担当領域**: Iteration 2 主対象④「Learning UI / Pipeline」
- **理由**: LearningOps は Iteration 2 の主対象そのもの。Iteration 1 で stub を急いで入れるより、Iteration 2 で LearningOps 本体実装とセットで UI を仕上げる方が一貫性が高い。

### 4.2 Minor（Iteration 2 前後どちらでも可）

#### Mi-CTL-1

- **内容**: `scripts/ctl.py` の `start` / `stop` が log 出力のみの stub で、実 process 起動・停止は行わない。計画書 §6.12 の Decision（process management は Iteration 2）通りだが、MVP §12 #3 の文面「`ctl start` で Supervisor + Dashboard が起動」と部分乖離。
- **Iteration 2 での担当領域**: 主対象②「Live / Broker 強化」と同時の運用 CLI 本格化

#### Mi-DASH-1

- **内容**: Streamlit 7 panel は構造・import・`render()` 存在まで確認済だが、実 DB 接続下での panel データ表示は未検証（DB 未接続時は graceful fallback で `st.info(...)`）。
- **Iteration 2 での担当領域**: 主対象⑤「Observability / Metrics」の一部として実 DB 接続下での panel 結線確認

### 4.3 Observation（記録のみ、対応任意）

#### Ob-ALEMBIC-1

- **内容**: `tests/migration/test_roundtrip.py` 実行時に alembic の `path_separator` / `version_path_separator` に関する DeprecationWarning が 6 件出る。migration 自体は up/down/up 成功。alembic 2.x 以降で必須となる設定追加が将来的に望ましい。

#### Ob-MIDRUN-1

- **内容**: `MidRunReconciler` は骨格のみ（`check()` メソッドが存在し呼出可能、Rate Limiter 2 bucket 切替等の実体は未実装）。計画書 §6.8 Decision 通りの範囲。Iteration 2 の主対象③「Reconciler 完全化」で拡張予定。

#### Ob-PANEL-FALLBACK-1

- **内容**: `src/fx_ai_trading/dashboard/panels/market_state.py` が `phase_mode` / `environment` を `app_settings` から取得しようとするが、これらは seed migration（`0002_app_settings_seed` 相当）に定義されていない。panel は graceful fallback で `"—"` を表示するため機能影響はなし。Iteration 2 で app_settings seed 拡張時に同時解消が妥当。

---

## 5. スコープ切り分け宣言

**本記録に列挙された Major / Minor / Observation 項目は、「未実装」ではなく「Iteration 2 にスコープされた項目」として扱う**。

これらは:

- Iteration 1 の完了判定を妨げない（Iteration 1 の契約は 511 test + 15 contract + ruff / lint すべて保持）
- Iteration 2 の計画書作成時に本ドキュメントの ID（`M-EXIT-1` / `M-METRIC-1` / `M-LRN-1` / `Mi-CTL-1` / `Mi-DASH-1` / `Ob-*`）で直接参照すること
- `grep -R "M-EXIT-1" docs/` 等で検索して計画入力に使えること
- Iteration 2 の Designer が新規 discovery として扱わないこと（既知項目として引き継ぎ済）

---

## 6. Iteration 2 への接続

### 6.1 Iteration 2 主対象（5 領域）

| # | 主対象 | 紐付く Carryover ID | 概要 |
|---|--------|---------------------|------|
| ① | **ExitPolicy 完成** | M-EXIT-1 | TP / SL / time / emergency 発火と close_event 記録、paper smoke を exit まで延伸 |
| ② | **Live / Broker 強化** | Mi-CTL-1 | OandaBroker 本実装、demo→live 切替（手動 confirmation）、ctl の process 本格化 |
| ③ | **Reconciler 完全化** | Ob-MIDRUN-1 | 11 ケース Action Matrix 全網羅、MidRunReconciler 実体（RateLimiter 2 bucket 切替） |
| ④ | **Learning UI / Pipeline** | M-LRN-1 | LearningOps 本体 + enqueue / status / history UI |
| ⑤ | **Observability / Metrics** | M-METRIC-1 / Mi-DASH-1 / Ob-PANEL-FALLBACK-1 | 1 分毎メトリクスループ、残り 3 dashboard panel、実 DB 接続下 panel 結線、app_settings seed 拡張 |

### 6.2 Iteration 2 計画入力に使う grep キー一覧

```
M-EXIT-1
M-METRIC-1
M-LRN-1
Mi-CTL-1
Mi-DASH-1
Ob-ALEMBIC-1
Ob-MIDRUN-1
Ob-PANEL-FALLBACK-1
```

### 6.3 Phase 7 / Phase 8 との関係

- Iteration 2 は MVP の残り 4 項目（#3, #4, #5, #6, #9 部分）を完了に持っていく層
- Phase 7: Backtest 実体 / AI 本体 / Cold Archive / EVCalibrator v1+ / Chaos 体系化
- Phase 8: SSO / Slack 双方向 / DR 訓練 / 税務 / 権限分離

Iteration 2 Carryover はこのうち Phase 7 / Phase 8 に属さず、MVP 完成に直接必要な層のみ。

---

## 7. 本記録の取り扱い

- このファイルは **不可変な判定記録**。後から修正する場合は `## N. Revision History` セクションを末尾に追記し、元本文は改変しないこと。
- Iteration 2 の計画書（新規作成予定の `docs/iteration2_implementation_plan.md` 等）から本ファイルを参照すること。
- Iteration 2 で各 Carryover が解消された際は、Iteration 2 側の完了記録に「resolved by Iteration 2 M-xx」と ID 対応を書くこと。本ファイルの ID は削除しない。
