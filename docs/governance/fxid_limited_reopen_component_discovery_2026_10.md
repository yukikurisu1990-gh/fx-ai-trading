# FXID の限定的な再開 — `FXID_REOPEN_FOR_COMPONENT_DISCOVERY`（2026-10-11）

`PRODUCTION_READINESS_NOT_CLAIMED`.

**位置づけ**: Human + ChatGPT の指示「FXID Limited Reopen — New Component Discovery Fast-Track」（2026-10-11）の記録。

- **FXID の研究状態の single source of truth は、引き続き `docs/governance/fxid_long_term_hold_ruling_2026_10.md`**。
- この文書は、それに対する一度限りの限定的な例外を記録する。

## 1. 裁定

| 項目 | 裁定 |
| --- | --- |
| 前回の結果 | `FAST-A — NO_REOPEN_JUSTIFICATION_COMPONENT_SUPPLY_INSUFFICIENT` を受け入れる |
| PR #506 | merge 済み（head `ba446f7` → merge `0de76b8`） |
| 再開の範囲 | **`NEW_COMPONENT_DISCOVERY` だけ**。この指示が、`FXID_REOPEN_REVIEW_PROPOSAL` に対する限定的な承認に当たる |
| HOLD | **全面的な再開ではない**。`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` は、この限定の範囲の外ではそのまま有効 |
| 失敗した場合 | **自動的に HOLD に戻る** |
| 目的 | Architecture H に供給できる、互いに異なる economic mechanism を持ち、retail の cost の後に正になりうる FX の component の family を、**最低 2 つ**確保できるかの判定 |

## 2. 許可する Phase

D0 → D9 を、STOP の条件に当たるまで自律的に進める。

| Phase | 中身 |
| --- | --- |
| D0 | 既存の state の freeze |
| D1 | 新しい mechanism の発見 |
| D2 | 机上の経済性・cost の実現性 |
| D3 | 候補の family の freeze |
| D4 | 必要最小限の過去の data の取得 |
| D5 | component の実証の screen |
| D6 | 独立な推定・頑健性 |
| D7 | 複数の component の実現性 |
| D8 | 条件付きの P2（合成 data だけ） |
| D9 | system 単位の判定 |

## 3. 研究の予算（結果を見て増やさない）

| 項目 | 上限 |
| --- | --- |
| 机上の発見の mechanism family | 5 |
| 実証に進める family | 3 |
| family ごとの主要な仮説 | 2 |
| family ごとの主要な variant | 3 |
| 新しい過去の data の取得の package | 2 |
| 解像度 | mechanism が要求する最小限（M15 に固定しない。day trading の範囲） |
| fresh | **0** |
| production / broker の取引 | **0** |

## 4. data の取得

- **D3 を通った候補についてだけ**、read-only の過去の価格（OANDA の historical pricing endpoint を含む）・bid / ask・公開の macro / event・benchmark / fixing・先物 / positioning・金利の data の取得を許可する。
- **trading / order / account の balance / live order / demo order / funding / deposit / withdrawal の endpoint は禁止**。認証が要る historical read-only endpoint を使う場合も、取引や account の変更は絶対に行わない。
- 取得の前に manifest を commit する。取得の後に hash・行数・時刻の範囲・欠損・bid / ask・timezone・DST を保存する。

## 5. 保護する data

| 区分 | 扱い |
| --- | --- |
| **fresh `2016-06-02 … 2021-04-25`** | **読まない** |
| 2021–2025 | seen として扱う |
| 文献の sample の期間の内側の data | independent confirmation とは呼ばない。用途を replication / calibration / development / independent estimation に分けて明示する |

## 6. 禁止（どこまで進んでも）

- protected の fresh の読み取り
- production / demo / paper / live の取引、broker の変更、入金・出金、leverage の変更、実際の資金の exposure
- CFD・crypto・株式への拡張（FX のみ）
- ML を新しい alpha の生成器として使うこと（LightGBM・XGBoost・NN・Transformer・AutoML の総当たり、特徴量の爆発、hyperparameter の探索）
- 交互作用の自由探索

## 7. 維持するもの

| 項目 | 内容 |
| --- | --- |
| G4 | **system 単位の事後 / 縮小後の net Sharpe ≥ 1.0 だけ**。component 単体には要求しない |
| system の prior | 契約（`τ² · tr(R⁻¹)` と tail の制約、PR #506）を維持する |
| fresh | 最終的に凍結した system に 1 回だけ。今回は使わない |
| architecture | Architecture H の baseline、G は事前の基準で H を上回る場合だけ |

## 8. 終了（STOP）

次のどれかで STOP し、Human + ChatGPT に返す。

| # | 条件 |
| --- | --- |
| A | 新しい distinct な mechanism が見つからない |
| B | 机上の経済性で全て消える |
| C | 実証の screen で 2 family 未満 |
| D | 独立な推定で 2 family 未満 |
| E | system の実現性が G4 未満 |
| F | P2 で失敗 |
| G | DISCOVERY-C に到達（その場合も fresh には進まない） |

- A〜F の場合、state は `FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` に戻る。
- STOP の後に、別の候補を足して予算を延ばすことはしない。
