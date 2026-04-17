# Phase 8 — 観測・運用高度化 (Roadmap / 将来計画)

> **本書の位置付け**: Phase 8 は **MVP / Phase 6 Hardening / Phase 7 運用自動化のいずれにも含まれない**、現時点では**実装しない**将来計画である。Phase 7 完了後、**複数運用者対応・長期運用資産化・対外的整合**が現実的に必要になった段階で着手する。実装内容を拘束するものではなく、着手時点で内容を見直すこと。

---

## 1. 目的

Phase 7 によって改善ループが自動で回る状態になったシステムに、**複数人運用 / 長期運用 / 対外的整合**の観点を加える。個人運用から「小規模チーム運用」「長期運用者 (年単位で資産蓄積)」への移行フェーズ。

- Phase 6: 壊れない
- Phase 7: 育つ / 自動で回る
- **Phase 8 (本書)**: チームで運用できる / 長く運用できる / 外部整合できる
- Phase 9 以降 (スケール期): ML 高度化 / マルチブローカー / champion-challenger 等 (本書範囲外)

---

## 2. 対象機能

### 2.1 Notifier の OAuth / SSO 認証
MVP / Phase 7 では Webhook / SMTP での通知。Phase 8 で Slack Bot Token (OAuth 2.0) に移行し、チーム単位での認証・権限管理を導入する。

### 2.2 Slack 双方向運用
現状は Slack への**一方向通知**のみ (safe_stop 発火通知等)。Phase 8 で Slack から**コマンド入力**を受け付ける双方向運用を追加し、運用者が Dashboard にアクセスできない状況でも `safe_stop` からの復帰や状態確認を Slack 経由で可能にする。

### 2.3 Dashboard の SSO / マルチユーザ
MVP / Phase 7 は BasicAuth + IP 制限の single-user 運用。Phase 8 で SSO (OAuth / SAML) と権限分離 (viewer / operator / admin) を導入。Streamlit が同時ユーザ 3 超・SSO 必須・レイテンシ 2 秒未満の卒業条件に達したら、Next.js / FastAPI + React 等への**UI フロントエンド刷新**を含む。

### 2.4 DR 訓練 (定期 failover リハーサル)
Phase 6 で日次バックアップ (RPO 24h / RTO 2h) は確保済だが、**訓練**は未実施。Phase 8 で月次の DR リハーサルを定例化し、実際の失敗時にも機能する復旧手順を維持する。

### 2.5 税務エクスポートの GUI 化
Phase 6 で「確定申告用の年次 CSV エクスポート機能」を仕様化。MVP / Phase 7 では CLI バッチ実行。Phase 8 で Dashboard 内の税務メニューとして GUI 化し、期間指定・フォーマット選択 (国税庁テンプレート等)・PDF 出力を提供。

---

## 3. なぜ今は実装しないか

| 項目 | 見送り理由 |
|---|---|
| OAuth / SSO | MVP / Phase 7 は single-user。Webhook + BasicAuth で十分。OAuth は token 管理・rotation など運用負荷が増える |
| Slack 双方向 | 書込操作 (コマンド実行) は監査・権限・安全性の問題を伴う。単方向通知で信頼性を積んでから双方向化が筋。誤コマンドによる誤発注リスク |
| Dashboard SSO / マルチユーザ | Streamlit は session-per-tab の特性で多ユーザに弱い。Phase 8 で Streamlit 卒業が現実になるまでは BasicAuth + IP 制限で足りる |
| DR 訓練 | MVP は small scale、失った場合の loss が小さい。長期運用で資産 (履歴データ・モデル・設定履歴) が積み上がってから訓練の価値が出る |
| 税務 GUI | MVP / Phase 7 は CLI バッチで十分 (年 1 回の処理)。GUI 化は利便性向上であり、運用リスク低減ではない |

全体として Phase 8 は「**現在の運用を阻害していない問題**」への対応が中心であり、早期投資は過剰設計になる。

---

## 4. 現在の設計で保持している拡張ポイント

### 4.1 OAuth / SSO (Notifier)
Phase 6.13 で `Notifier` Interface は抽象化済。`SlackNotifier` は Webhook 実装だが、Bot Token 実装に差し替え可能な Interface 設計。

### 4.2 Slack 双方向
Slack Webhook は `SlackNotifier` で送信方向のみ使用。Slack Events API (subscription) を別コンポーネントとして追加すれば双方向化可能。既存の Webhook を壊さず共存。

### 4.3 Dashboard マルチユーザ
Phase 5.11 で **Streamlit 卒業条件** が宣言済:
- 同時ユーザ 3 超
- UI 書込操作が MVP を超えて必要
- 認証が SSO 必須
- レイテンシ要件 2 秒未満

上記のいずれかを満たしたら Next.js / FastAPI+React へ移行する。Phase 5.9 の「Dashboard Query Service を A (Python 関数) / B (HTTP) の 2 形態」で、B 形態への切替で多フロントエンド対応が可能な設計。

### 4.4 DR 訓練
Phase 6.14 で以下が既に設計済:
- 日次 pg_dump + WAL アーカイブ
- RPO 24h / RTO 2h
- バックアップ先は別ストレージ (ローカル + 外部の 2 系統)

**Phase 8 で追加する部分**: 訓練手順 (runbook) と月次実施体制。

### 4.5 税務エクスポート
Phase 6.14 で年次 CSV エクスポート機能が仕様化。CLI 実装を MVP / Phase 7 で完成させる想定。

**Phase 8 で追加する部分**: Dashboard 内 UI、フォーマット選択、PDF 出力。

---

## 5. 実装時に追加が必要なもの

### 5.1 OAuth / SSO 対応 Notifier
- **Slack Bot Token 取得**: Slack App 作成、OAuth scopes 定義 (`chat:write`, `commands`, `app_mentions:read` 等)
- **Token 管理**: 保管、rotation、失効検知
- **Webhook からの移行**: 既存 webhook URL 廃止前の並走期間
- **認証失敗時のフォールバック**: FileNotifier への退避
- **設定移行**: `app_settings.notification_channels.slack` の key 名変更と既存データの追従

### 5.2 Slack 双方向
- **Slack Events API**: subscription 設定、エンドポイント (HTTPS 必須、TLS 証明書)
- **Command Handler**: スラッシュコマンド or mention 経由で以下を受け付け:
  - `/fx-ai-trading status` — 現在状態 (safe_stop / degraded / online)
  - `/fx-ai-trading safe-stop-resume` — safe_stop 復帰
  - `/fx-ai-trading flat-all` — Emergency Flat (権限必須)
  - `/fx-ai-trading recent-signals` — 直近シグナル
- **権限モデル**: allow-list of Slack user_id、role (admin / operator / viewer)
- **監査ログ**: 全 Slack 由来コマンドを `audit_log_slack_commands` テーブルに記録 (actor / command / timestamp / result)
- **書込系の 2-factor**: `flat-all` / `safe-stop-resume` 等の破壊的コマンドは再確認 (Slack 内での confirm ボタン)

### 5.3 Dashboard SSO / マルチユーザ
- **UI フロントエンド刷新の判断**:
  - Streamlit 継続: 同時 3 ユーザ以下なら継続可能
  - **Next.js + FastAPI**: 多ユーザ / SSO / 低レイテンシが必要なら移行
- **SSO 認証**: OAuth (Google / Microsoft) / SAML 対応、session 管理
- **権限分離**:
  - `viewer`: 閲覧のみ
  - `operator`: 閲覧 + 学習 enqueue + Emergency Flat
  - `admin`: 全操作 + 設定変更 + ユーザ管理
- **監査ログ**: UI 経由の全書込操作を `dashboard_operations_audit` テーブルに記録 (Phase 5 M4 の実装)
- **Dashboard Query Service の HTTP 化**: Phase 5.9 の B 形態 (FastAPI 等) に移行

### 5.4 DR 訓練体系
- **DR Runbook** (`docs/dr_runbook.md`):
  - 障害シナリオ別手順 (DB 全損 / マシン全損 / データセンタ障害 等)
  - バックアップからのリストア手順
  - Reconciler 経由の整合回復手順
  - RTO 計測記録方法
- **月次リハーサル**:
  - staging 環境で実際にバックアップを用いた DR 訓練
  - RTO 実測、目標 2h を下回るか確認
  - 発見された問題を Runbook に反映
- **バックアップ整合性検証の自動化**:
  - pg_dump 後の自動リストアテスト
  - スキーマ互換性の自動検証
- **記録**: `dr_drill_runs` テーブルに実施記録 (日時 / 担当者 / RTO / 発見問題 / 対処)

### 5.5 税務エクスポート GUI 化
- **Dashboard 内メニュー**: 税務タブ追加
- **期間指定**: 年度 (1/1–12/31) / 任意期間
- **フォーマット**:
  - CSV (国税庁テンプレート準拠)
  - PDF (取引履歴レポート)
- **集計項目**:
  - 取引ごとの損益 (円換算)
  - スワップ損益
  - 手数料
  - 年間損益合計
  - 勝敗件数
- **エクスポート履歴**: `tax_export_runs` テーブル (誰がいつ出力したか)
- **再現性**: 同一期間のエクスポートが同一結果になること (No-Reset 原則と整合)

---

## 6. リスク

### 6.1 Phase 8 着手前のリスク (現状維持のリスク)
- **single-user のまま運用者が増える**: 環境変数 / 設定 / token の共有事故、誰が何をしたか追跡不能
- **Dashboard の公開範囲拡大**: BasicAuth は弱い認証で、外部ネットワークに出せない (内部 VPN 前提になる)
- **DR 訓練なし**: バックアップは取れているが**戻せる保証がない**。本番障害時に手順ミスで長時間ダウン
- **税務 GUI なし**: CLI バッチで対応可能だが、年次作業が属人化。運用者交代時に引き継ぎ困難
- **Slack 双方向なし**: 運用者が Dashboard にアクセスできない環境 (移動中 / PC 故障) で safe_stop 復帰が不能 → 無駄な停止時間

### 6.2 Phase 8 実装中のリスク
- **認証変更時の既存セッション切断**: BasicAuth → SSO 切替時に既存ユーザがログアウト、UI 利用不能期間発生 (売買系は無影響だが運用者が現状把握できなくなる)
- **Slack 双方向の誤コマンド**: `flat-all` を誤って入力 → 全ポジション強制決済 → 不必要な損失
- **Dashboard フロント移行中のリグレッション**: Streamlit → Next.js 移行中に一部機能の欠落、見える情報の不整合
- **DR 訓練で本番 DB に影響**: 訓練と本番の分離が甘いと、訓練スクリプトが本番を破壊する事故
- **税務 GUI の計算誤り**: 税務は法的責任を伴うため、誤計算が実害 (過少申告 / 過大申告)

### 6.3 Phase 8 完了後のリスク
- **マルチユーザ運用で権限濫用**: 責任所在の曖昧化、操作履歴の監査不足
- **認証疲れ**: 通知を見ない / Slack コマンドを雑に打つ / 2-factor をスキップしたがる圧力
- **訓練と実運用のギャップ**: 訓練は順調でも実際の障害時に想定外 (人的パニック等) で手順通り動けない
- **税務 GUI 利用時の法改正未追従**: 税法改正に自動追従する仕組みがないと、翌年に計算方式が合わなくなる

---

## 7. 実装開始条件

Phase 8 全体の着手条件 (すべて必須):

1. **Phase 7 完了** — 運用自動化が動いている (regime tightening 有効化、shadow→active Promotion 経験、CI/CD 稼働、Chaos 週次)
2. **複数運用者の必要性が具体化** — 「一人運用が限界」な実績 (運用負荷超過 / 24h カバー不可 / 引継ぎ要請)
3. **長期運用 3 ヶ月以上の実績** — DR 訓練が意味を持つ資産蓄積 (履歴 DB、学習済モデル、設定履歴)
4. **税務処理の最初の年次処理経験** — CLI バッチで 1 回やった後に GUI 化 (実データで検証済 → GUI 化が妥当な状態)

各項目の個別着手条件:

| 項目 | 追加条件 |
|---|---|
| 5.1 OAuth / SSO (Notifier) | 条件 2 + Slack Bot 登録の組織的許可 |
| 5.2 Slack 双方向 | 条件 2 + 5.1 完了 (Bot Token 先行) |
| 5.3 Dashboard SSO / マルチユーザ | 条件 2 + **Phase 5.11 の Streamlit 卒業条件のいずれかを満たす** |
| 5.4 DR 訓練 | 条件 3 + staging 環境整備完了 |
| 5.5 税務 GUI | 条件 4 + 税理士 or 運用者の要件確認 |

Phase 8 全体としては **Phase 7 完了 + 複数運用者要件発生** を最低ライン、**運用 1 年以上経過** を推奨開始条件とする。

---

## Phase 9 以降 (スケール期) — 範囲外の参考

Phase 8 の対象外だが、将来的に検討される領域として以下を挙げておく (実装計画は Phase 9 時点で別書にて作成):

- **Drift detection の本格実装**: PSI / KL ダイバージェンス / 残差ドリフト
- **EVCalibrator**: isotonic regression 等で EV 予測をオンライン補正
- **multi_service_mode / container_ready_mode の本番展開**: 小規模 single_process から分離運用へ
- **複数ブローカー対応**: OANDA 以外の追加
- **champion/challenger A/B テスト基盤**: shadow だけでなく並行 live テスト
- **クラウドネイティブ化**: AWS 上のマネージド PG (RDS) / オーケストレーション (ECS / EKS)

---

## 本書の更新ポリシー

- Phase 8 着手時点で本書を読み直し、Phase 7 運用で得た知見を踏まえて見直すこと
- 複数運用者要件の発生時期・内容は運用実態に大きく依存するため、本書の優先度順序は着手時点で再評価する
- 本書は**計画書**であり**契約ではない**。Phase 7 の結果次第で、Phase 8 項目の一部が先送り or 不要化しうる
- Phase 8 完了時点で Phase 9 以降のロードマップを同様のフォーマットで作成する
