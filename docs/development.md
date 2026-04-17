# 開発ガイド

## 必要環境

- Python 3.11 以上 (検証環境は 3.14)
- Git
- (将来) PostgreSQL

## 初期セットアップ

```bash
# 1. 仮想環境を作成
python -m venv .venv

# 2. 仮想環境を有効化
#   Windows (bash):
source .venv/Scripts/activate
#   PowerShell:
# .venv\Scripts\Activate.ps1

# 3. プロジェクトを editable + dev 依存でインストール
pip install -e ".[dev]"

# 4. 環境変数を設定
cp .env.example .env
# .env を編集して値を入れる (コミット禁止)
```

## テスト実行

```bash
pytest
```

## 依存の追加

- ランタイム依存: `pyproject.toml` の `[project].dependencies`
- 開発依存: `pyproject.toml` の `[project.optional-dependencies].dev`
  (従来の `requirements-dev.txt` に相当)

追加後は `pip install -e ".[dev]"` を再実行。

## Lint / Format (任意)

```bash
ruff check .
ruff format .
```

## ディレクトリの役割

- `src/fx_ai_trading/` — 実装本体 (詳細は各サブディレクトリの README)
- `tests/` — ユニット/スモークテスト
- `scripts/` — 使い捨てまたは運用系スクリプト
- `docs/` — 設計判断・方針ドキュメント
- `.env.example` — 環境変数テンプレート (`.env` はコミット禁止)

## 開発方針 (抜粋)

- Phase 単位で前進。巨大実装をいきなり作らない
- 先に計画 → 最小実装 → 検証 → 改善
- 層を分離し、外部依存は差し替え可能に保つ
- 設定値は `.env` / 設定ファイル経由、秘密はコード直書き禁止
- ドキュメント (README / docs) は毎回更新

詳細は [git_workflow.md](./git_workflow.md) / [architecture.md](./architecture.md) を参照。
