# Phase 7 — 運用自動化 (Roadmap / 将来計画)

> **本書の位置付け**: Phase 7 は **MVP および Phase 6 Hardening の対象外**であり、現時点では**実装しない**。本書は Phase 6 完了後に着手するための前提条件・拡張ポイント・実装スコープ・リスク・着手条件を記述する将来計画書である。実装内容を拘束するものではなく、着手時点で内容を見直すこと。

---

## 1. 目的

Phase 6 Hardening により「動けば運用で壊れない仕組み」が揃った状態を前提に、**運用者の手動介入を減らし、改善ループを自動で回せる状態**へ進化させる。

- MVP 期 (Phase 0–6): 動く / 壊れない / 最小限の運用で回る
- **Phase 7 期 (本書)**: 回す / 改善を自動化する / 属人性を減らす
- Phase 8 期 (`docs/phase8_roadmap.md`): チーム運用・長期運用対応

Phase 7 は「動く」から「育つ」への移行フェーズに位置する。

---

## 2. 対象機能

Phase 6 で**契約のみ確保し実装を MVP 後に回した項目**、および Phase 6 で提案された**運用自動化領域**を Phase 7 で実装する。

### 2.1 相関双窓 regime tightening の強制適用
Phase 6 では双窓計算・`regime_detected` 記録までが MVP スコープだった。Phase 7 で MetaDecider Select に tightening を有効化し、regime 検知時に `correlation_threshold` を一時緊縮する挙動を実装する。

### 2.2 AIStrategy shadow → active Promotion 実運用
Phase 6 で `stub / shadow / active` の 3 状態と Promotion 判定基準 (OOS / Calibration / Drift / Sample size) が契約化された。Phase 7 で本物の AI モデルを投入し、shadow 期間 30 日を経て active 昇格する運用を確立する。

### 2.3 CI/CD 自動マイグレーションテスト
Phase 6 では手動テスト前提だった Alembic up/down/up / PG・SQLite 互換検証 / strategy 変更時の shadow backtest を CI で自動化する。

### 2.4 Chaos Engineering の体系化
MVP で骨格の Fault Injection テスト (DB 切断 / Stream 切断 / Broker API 5xx / EventCalendar 削除) を実装している前提で、Phase 7 でシナリオカタログを拡張し週次 chaos run を定常化する。

### 2.5 Emergency Flat CLI の権限・監査拡張
MVP は single-user 前提で権限確認が緩い。Phase 7 で以下を追加:
- 実行者の認証 (OS user / token)
- 2-factor 確認 (interactive prompt or signed token)
- 監査ログ (`emergency_actions` テーブル)
- Slack 通知 (誰がいつ発動したか)

### 2.6 EmailNotifier 拡張 (基本実装は Iter2 M17 で完了)
Phase 6 では `FileNotifier` (必須) + `SlackNotifier` (MVP 必須) のみで、EmailNotifier は任意扱いだった。**Iter2 M17 で SMTP fan-out (3-path: File + Slack + Email) は実装済**で、SMTP_HOST / SMTP_PORT / SMTP_SENDER / SMTP_USERNAME / SMTP_PASSWORD / SMTP_RECIPIENTS の 6 環境変数全 set で auto-activate する (phase6 §6.13 / implementation_contracts §2.13)。Phase 7 では SES 対応 / OAuth 認証 / 配信ステータス追跡など**運用拡張**を追加する。

---

## 3. なぜ今は実装しないか

| 項目 | 見送り理由 |
|---|---|
| 相関 regime tightening | MVP 期は相関マトリクスの実データ収集と閾値検証が先。実データなしでの tightening 有効化は過剰制限 → no_trade 増 → 機会損失のリスク |
| AIStrategy shadow/active | MVP 時点で本物の AI モデルが存在しない。`AIStrategyStub` で EV パイプだけ通した状態が妥当。学習データの蓄積も不十分 |
| CI/CD 自動化 | MVP 段階は migrations 数が少なく (初期 1 〜 数個)、手動確認で十分。migrations が累積した段階で自動化効果が現れる |
| Chaos Engineering 体系化 | MVP 運用実績から**実際に起きた失敗モード**を抽出してシナリオ化する方が投資対効果が高い。先に体系化してもカバレッジが想像で決まり漏れる |
| Emergency Flat 拡張 | MVP は single-user。複数人運用や権限分離が不要 |
| EmailNotifier (運用拡張) | 基本 SMTP fan-out は **Iter2 M17 で実装済**。SES / OAuth / 配信ステータス追跡などは MVP 要件外、Phase 7 で運用熟成と合わせて追加 |

---

## 4. 現在の設計で保持している拡張ポイント

### 4.1 相関 regime tightening
Phase 6.5 で以下が既に確定・実装予定:
- `app_settings` に `correlation_short_window_hours=1` / `correlation_long_window_days=30` / `correlation_regime_delta_threshold=0.3` / `correlation_regime_tightening_delta=0.1`
- `meta_decisions` / `correlation_snapshots` に双窓値と `regime_detected: bool` フラグを記録
- `CorrelationMatrix` Interface は `CorrelationConfig` を受け取る設計

**Phase 7 で有効化する部分**: MetaDecider Select ロジックで `regime_detected == true` の時のみ `correlation_threshold - tightening_delta` を適用する分岐。

### 4.2 AIStrategy shadow → active
Phase 6.11 で以下が契約済:
- `AIStrategy` に `stub / shadow / active` の 3 状態機構
- `model_evaluations.shadow` フラグ列
- Promotion 判定基準 (OOS Sharpe ≥ 0.5 / Brier score 改善 / drift_events 発火なし / 1000 件 predictions)
- `strategy_version` による集計境界分離 (Aggregator で跨がない)

**Phase 7 で有効化する部分**: shadow モード稼働、30 日経過後の promotion 判定、active への切替処理。

### 4.3 CI/CD 基盤
MVP 時点で存在するもの:
- Alembic migration 履歴 (git 管理)
- pytest 基盤
- Phase 6 契約として「strategy/meta 変更時の shadow backtest を CI で自動実行」を宣言済

**Phase 7 で有効化する部分**: GitHub Actions workflow、PG/SQLite 両対応テスト、up/down/up 往復テスト。

### 4.4 Chaos Engineering 基盤
MVP で最低限の Fault Injection テスト (6 系統: DB / Stream / Broker / Calendar / NTP / Rate limit) が単発テストとして実装済。

**Phase 7 で有効化する部分**: シナリオカタログ化、組合せシナリオ、週次 run、結果ログ (`chaos_test_runs` テーブル)。

### 4.5 Emergency Flat CLI
Phase 6.14 で CLI 自体 (`ctl emergency-flat-all`) は MVP 実装。認証・監査は後回し。

**Phase 7 で有効化する部分**: 認証層、2-factor、監査ログテーブル、Slack 連動通知。

### 4.6 Notifier 抽象
Phase 6.13 で `Notifier` Interface が抽象化済、実装追加のみで EmailNotifier を差し込める。

---

## 5. 実装時に追加が必要なもの

### 5.1 相関 regime tightening
- **コード**: MetaDecider Select の tightening 分岐実装
- **仕様**: regime cooldown 管理 (検知後一定時間は緊縮維持、`regime_cooldown_minutes` を `app_settings` に追加)
- **検証**: MVP 期の `meta_decisions` / `correlation_snapshots` ログで tightening 有効化後の挙動をバックテスト
- **A/B**: tightening 有効化前 / 後の `strategy_performance` を config_version 境界で比較

### 5.2 AIStrategy shadow → active
- **モデル**: 本物の AI 実装 (候補: XGBoost / LightGBM / 小型 DNN)
- **学習パイプライン**: LearningOps での定期学習 + 評価 + ModelRegistry 登録
- **UI**: 管理画面に `promote_to_active` ボタン (shadow → active 切替、権限・監査必須)
- **運用手順**: 30 日 shadow 期間の監視チェックリスト
- **ロールバック**: active 化後の性能悪化時の demoted への遷移手順

### 5.3 CI/CD 自動マイグレーションテスト
- **GitHub Actions workflow**: PR 時 / main push 時に走るパイプライン
- **PG / SQLite 両対応テスト**: schema 作成 + fixture 投入 + クエリ動作確認
- **Alembic up/down/up**: 全リビジョンを往復実行して破壊的変更を検出
- **Shadow backtest**: strategy / meta 変更を含む PR で自動的に過去データに対して shadow 実行、成績劣化検出
- **依存**: pytest 基盤、サンプルデータセット、CI 用 PG コンテナ

### 5.4 Chaos Engineering 体系化
- **ツール選定**: Toxiproxy (ネットワーク層 fault) / 自前スクリプト (アプリ層 fault) の組合せ
- **シナリオカタログ**: Phase 6 Failure Modes を元に最低 20 シナリオ (単発 + 組合せ)
- **週次 run**: staging 環境で毎週自動実行、結果を `chaos_test_runs` に記録
- **合格基準**: safe_stop が正しく発火する / Reconciler が正しく動く / Notifier が通知する
- **カタログ例**:
  - DB 接続断 60 秒 → safe_stop 発火確認
  - Stream gap 180 秒 → Mid-Run Reconciler 動作 + 120s 超で safe_stop
  - EventCalendar 削除 → Stale failsafe で全 no_trade
  - Broker 5xx 連発 → Retry / RateLimiter / degraded 遷移
  - 複合: DB 断 + Stream 断 → safe_stop + SafeStopJournal 記録確認

### 5.5 Emergency Flat CLI 拡張
- **認証**: OS user check + token (hash 保存、ローテーション可能)
- **2-factor**: interactive prompt (再入力) or signed token file
- **監査テーブル**: `emergency_actions` (actor / action / timestamp / reason / result)
- **Slack 通知**: 実行と同時に `SlackNotifier` で通知
- **dry-run モード**: `--dry-run` で実際には実行せず対象ポジションを表示

### 5.6 EmailNotifier (運用拡張、基本 SMTP は Iter2 M17 で実装済)
- **基本 SMTP fan-out**: Iter2 M17 で実装済 (phase6 §6.13、SMTP_* 6 変数 auto-activate)
- **拡張**: AWS SES / OAuth 2.0 認証 / 配信ステータス追跡 (bounce / delivery webhook)
- **テンプレート**: プレーンテキスト + HTML、severity 別にフォーマット
- **送信抑制**: 同一イベント連発時の rate limiting (例: 同イベント 5 分以内に 2 通まで)

---

## 6. リスク

### 6.1 Phase 7 着手前のリスク (現状維持のリスク)
- **相関 tightening 不在**: regime change 時の相関急変で同方向ペア集中 → 過剰損失 (Phase 6 のシナリオ S3 型)
- **AI 不在**: MA/ATR だけでは改善ループに上限。EV 予測の精度が頭打ち
- **CI/CD 不在**: migrations 数が 10 超えると手動確認ミスが顕在化
- **Chaos 不在**: 既知の失敗モード以外に脆弱、未知のモードで MVP の価値が毀損
- **Emergency Flat が single-user**: 運用引き継ぎ時に属人化、操作事故リスク
- **EmailNotifier 運用拡張不在 (基本実装は Iter2 M17 で完了)**: SES / OAuth / 配信トラッキング不在のため、Gmail 等 SMTP 障害時に通知ロストを検知できない

### 6.2 Phase 7 実装中のリスク
- **regime tightening を急に有効化**: 過去のデータで tightening 閾値が甘いと、有効化直後に全ペア no_trade → 機会損失。段階投入が必要
- **Shadow 期間短縮の誘惑**: 「早く active にしたい」バイアスで 30 日を守らない → 未検証モデル投入
- **CI/CD の false positive**: 本番デプロイ遅延で緊急パッチが出せない
- **Chaos test が production に波及**: staging と production の分離が甘いと、本番影響
- **Emergency Flat の認証誤設定**: 認証を足した結果、緊急時に発動できない (fail-closed になる)
- **Email 送信過多**: 設定ミスで重要イベント毎にメール、通知疲れ → 見られなくなる

### 6.3 Phase 7 完了後のリスク
- **自動化への過信**: 「Chaos pass = 全て安全」と錯覚して運用監視を怠る
- **AI 性能ドリフトへの依存**: shadow 期間で良好でも本番で悪化 (regime change)、ロールバック手順が機能するか
- **Emergency 濫用**: 権限緩和 (2-factor 省略等) の圧力

---

## 7. 実装開始条件

Phase 7 全体の着手条件 (すべて必須):

1. **MVP リリース完了** — Phase 6 絶対必須項目がすべて本番稼働していること
2. **最低 30 日の安定稼働実績** — safe_stop が頻発していないこと、critical 通知が運用ルールで解釈できる規模であること
3. **Phase 6 通知実績が整理済** — 通知過多 / 通知不足の初期チューニング完了
4. **運用者 1 名以上の MVP 手動運用経験** — Emergency 等の実運用感覚

各項目の個別着手条件:

| 項目 | 着手条件 (追加) |
|---|---|
| 5.1 相関 regime tightening | MVP 期に最低 **1000 件の `meta_decisions`** と **50 件以上の regime_detected イベント** が蓄積 |
| 5.2 AIStrategy shadow → active | **AI モデル候補実装が 1 つ以上** 完成している / 学習データセット (最低 6 ヶ月分の `strategy_signals` + `close_events`) が揃う |
| 5.3 CI/CD | **Alembic revision が 10 個以上** 累積 / PR 数 / 月 が手動確認を圧迫し始める |
| 5.4 Chaos Engineering | **MVP 運用中に最低 3 件の実障害** (stream 断 / DB 低下 / Broker エラー等) を経験済 |
| 5.5 Emergency Flat 拡張 | **複数運用者の参加が具体化** (次 Phase 8 の前哨戦として) |
| 5.6 EmailNotifier | Phase 7 全体と同時 or 軽微作業として任意タイミング (他項目より軽い) |

Phase 7 全体としては **MVP リリース + 30 日以上** を最低ライン、**90 日以上の安定運用実績** を推奨開始条件とする。

---

## 本書の更新ポリシー

- Phase 7 着手時点で本書を読み直し、MVP 運用で得た知見を踏まえて見直すこと
- 特に各項目の「実装時に追加が必要なもの」は、MVP 運用で生じた具体ニーズに合わせて取捨選択・追加を行う
- 本書は**計画書**であり**契約ではない**。MVP 運用の実態に応じて優先度順序は変わりうる
- Phase 7 完了時に次の `docs/phase8_roadmap.md` を同様に見直す
