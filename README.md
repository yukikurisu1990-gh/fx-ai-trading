# fx-ai-trading

FX為替予測アプリ。価格データ + テクニカル指標 + (将来) ファンダメンタル要素で為替予測を行う、
ローカル開発から段階的に育てていくモノレポプロジェクト。

## 目的

- 主戦略判断は **1分足 / 5分足** を中心に行う
- 秒単位監視は執行補助として扱う
- 一次DB (生・中間データ) / 二次DB (集計・分析) を分離して保守性を確保
- 学習は常時ではなく、手動実行またはスケジュールバッチ
- 初期は「予測・分析・可視化・検証」を優先。自動発注は後段で安全に実装
- 最優先は **壊れにくさ / 原因調査しやすさ / 段階的に育てられること**

## 想定ディレクトリ構成

```
fx-ai-trading/
├── src/fx_ai_trading/
│   ├── app/         # (将来) Web API / CLI エントリポイント
│   ├── services/    # データ取得/保存/特徴量/予測/シグナル/執行
│   ├── batch/       # 学習/集計など手動・スケジュール実行
│   ├── dashboard/   # 可視化・管理画面
│   └── common/      # 設定・ログなど横断ユーティリティ
├── tests/           # ユニット/スモークテスト
├── scripts/         # 運用・使い捨てスクリプト
├── docs/            # 設計判断・方針ドキュメント
├── .env.example     # 環境変数テンプレート (.env はコミット禁止)
├── pyproject.toml   # 依存・ツール設定の単一ソース
└── README.md
```

## 初期セットアップ

```bash
# 1. 仮想環境
python -m venv .venv
source .venv/Scripts/activate   # Windows bash。PowerShell は .venv\Scripts\Activate.ps1

# 2. 依存インストール (editable + dev)
pip install -e ".[dev]"

# 3. 環境変数
cp .env.example .env
# .env を編集。コミット禁止。

# 4. 動作確認
pytest
```

詳細は [docs/development.md](./docs/development.md) を参照。

## 開発方針

- Phase 単位で前進 (`docs/architecture.md` のロードマップ参照)
- 先に計画 → 最小実装 → 検証 → 改善
- 層を分離し、外部依存は差し替え可能に保つ (モック/テストハーネスで本番前検証)
- 設定値は `.env` / 設定ファイル経由。秘密情報はコード直書き禁止
- Git は Conventional Commits 風、意味のある最小単位でコミット (`docs/git_workflow.md`)
- ドキュメント (README / docs) は毎回更新

## ドキュメント

- [docs/architecture.md](./docs/architecture.md) — 設計・レイヤ・Phaseロードマップ
- [docs/development.md](./docs/development.md) — 開発環境と運用手順
- [docs/git_workflow.md](./docs/git_workflow.md) — コミット規約とブランチ方針

## ステータス

Phase 0: 骨格整備 (本コミット時点)。
次は Phase 1 (データ取得層の最小実装 + モック) に進む想定。
