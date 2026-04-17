# Git ワークフロー

## 原則

- `main` へ雑に直接積まない
- 意味のある最小単位でコミット
- 破壊的変更・大規模変更の前に「何を変えるか」を先に説明
- 自動生成物・秘密情報はコミットしない

## コミットメッセージ (Conventional Commits 風)

```
<type>: <summary>

[optional body]
```

`type` は以下から選ぶ:

| type | 用途 |
|------|------|
| `feat` | 新機能 |
| `fix` | バグ修正 |
| `refactor` | 振る舞いを変えない構造変更 |
| `docs` | ドキュメント更新のみ |
| `test` | テスト追加・修正 |
| `chore` | ビルド・設定・依存など雑務 |

例:
```
feat: add data fetch interface for broker feed
fix: correct timezone handling in 1m candle aggregation
docs: update architecture.md with phase 2 plan
```

## ブランチ運用 (当面)

- `main` — 常に動く状態を保つ
- 作業ブランチ — Phase やタスク単位。`feat/data-fetch` 等
- 小さい変更は直接 `main` コミットでも可だが、意味のある単位で区切る

## リモート

- GitHub (private): `yukikurisu1990-gh/fx-ai-trading`
- push は HTTPS + gh CLI 経由の認証

## コミットしてはいけないもの

- `.env` / API キー / パスワード / トークン
- `__pycache__/`, `*.pyc`, `.venv/`, `venv/`
- `logs/`, `data/`, `models/`, `*.db`
- IDE 個人設定 (共通化するものを除く)

これらは `.gitignore` で弾く前提。該当パターンを追加したら `.gitignore` を更新。
