# FX system architecture — 裁定の記録（2026-10-08）

**採用した判定: `ARCH-C — COMPOSITION_DOES_NOT_SOLVE_THE_FUNDAMENTAL_LIMITATION`**

`PRODUCTION_READINESS_NOT_CLAIMED`.

**位置づけ**: FX の自動売買 system の合成の構造（architecture）についての authoritative な記録。**FXID の研究状態の single source of truth は、引き続き `docs/governance/fxid_long_term_hold_ruling_2026_10.md`**で、この文書はそれを変えない。

---

## 1. 裁定（Human + ChatGPT、2026-10-08）

| 項目 | 裁定 |
| --- | --- |
| PR #505 | MERGE APPROVED → merge `57723a2`（head `a2d75e8`） |
| 最終判定 | **ARCH-C `COMPOSITION_DOES_NOT_SOLVE_THE_FUNDAMENTAL_LIMITATION`** |
| 将来の baseline | **Architecture H** |
| Architecture G | synthetic の帰無の上で、事前登録の基準で H より明確に優れる場合だけ候補 |
| G4 | **system 単位の縮小後 / 事後の net Sharpe ≥ 1.0** を維持 |
| component ごとの縮小の和 | **G4 の迂回に使うことを禁止** |
| fresh | 最終的に凍結した system 全体に 1 回だけ |
| FXID の state | **`FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` は解除しない** |
| 一度限りの例外 | **P1 と、条件付きの P2 だけ**を、HOLD の中で実行することを許可（§5） |

## 2. ARCH-C の意味

足し算・掛け算・ensemble・Mixture of Experts・通貨の netting・portfolio の最適化は、**正の component を効率よく統合する方法**ではある。しかし、**正で・cost の後に残り・重複しない component そのものを作り出すことはできない**。

したがって、現在の主な制約は次のとおり。

| 区分 | 中身 |
| --- | --- |
| 主な制約である | **`COMPONENT_SUPPLY + COST + INDEPENDENT_DATA`** |
| 主な制約ではない | `COMPOSITION_ARCHITECTURE` |

## 3. Architecture H（将来の再開の baseline）

| 要素 | 内容 |
| --- | --- |
| 原子 | strategy ではなく、**economic mechanism family が出す通貨単位の期待 return の view** |
| 予測 | 各 mechanism は、通貨の view・期待 return・不確実性を出す。**H では、期待 return を新しい価格 data から推定しない**。peer-reviewed の文献・受け入れた外部の証拠・commit 済みの証拠から事前に固定する |
| 合成 | 単純平均でも勝者総取りでもなく、**予測の誤差の共分散を含む精度の加重の合成**（Black–Litterman 型を baseline） |
| 通貨の表現 | pair ではなく通貨の exposure が基本の単位。pair は執行の手段 |
| position | 通貨の view・risk の共分散・執行の cost・turnover・margin・集中を、まとめて最適化して決める |
| 時間 | fix などの時刻に依存する mechanism には、1 期間ではなく多期間 / aim portfolio 型の最適化 |
| 硬い制約 | 当日決済（same-day flat）・週末をまたがない・rollover の回避・指標の発表の blackout か event の cost の stress・margin・通貨の exposure・family の集中・ES / tail・vol target |

## 4. H で固定しないもの

次の具体的な値は、**authoritative に凍結しない**。将来の実際の REOPEN の時に、その時点の証拠に基づいて事前登録する。

- 文献の効果の最終値
- 公表の後の減衰の haircut（PR #505 の 30〜60% は**設計の感度としてだけ**残し、恒久の parameter にしない）
- Ω
- 共分散の重み付け
- λ
- family の risk の予算
- turnover の罰則
- 厳密な exposure の上限・ES の上限・相関の構造

## 5. Architecture G と system の prior

**Architecture G**:

- H に、mechanism の中の条件付きの μ の推定・状態変数・family の縮小などの自由度を加えたもの。**既定にしない**。
- P2 で、**同じ selection-error の予算の下で、H より実質的に高い検出力**を、事前登録した基準で示した場合だけ候補にする。それ以外は H。
- **ML / GBDT で G を救済してはならない**。

**system の prior**:

- G4 の prior は、**最終の system の net Sharpe に直接**課す。
- component ごとに独立な prior を置いて足し、system の prior が `τ√k` に膨らむことを禁止する。
- component の prior を使う場合は、**含意する system の prior が G4 の prior と一致するよう scale する**。

## 6. 一度限りの例外: P1 と条件付きの P2

**例外の範囲**:

- `P1 — COMPONENT_SUPPLY_AND_SYSTEM_UPPER_BOUND` と、`P2 — SYNTHETIC_PIPELINE_VALIDATION`（**P1 が PASS した場合だけ**）を、HOLD の中で実行することを許可する。
- これは、HOLD の裁定と PR #505 の「P1 / P2 は REOPEN の承認の後だけ」を、**P1 / P2 に限って**この指示で上書きするもの。

**P1 / P2 で行わないこと**:

- 新しい価格 data の読み取り
- broker の接続
- alpha の backtest
- fresh の使用
- 実際の strategy の検証

**この例外が及ばないもの**:

- **P3 以降には及ばない**。P3（cost の較正と replication）・P4（component の推定）の実行には、Human + ChatGPT の新しい Red の承認が要る。
- **REOPEN の提案（`FXID_REOPEN_REVIEW_PROPOSAL`）は、実行の許可ではない**。提案を作っても HOLD は自動で解除されない。
- P1 / P2 が失敗した場合、次のことはしない。state は `FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE` のまま。
  - 追加の strategy 案・indicator の追加
  - ML
  - 交互作用の探索
  - 保有期間の変更による救済
  - CFD への拡張
- P1 の component の universe を、**結果に依存して広げることは禁止**する。

## 7. Provenance

| 項目 | 記録 |
| --- | --- |
| 裁定の元の報告 | `docs/research/fx_system_architecture_redesign_2026_10.md`（PR #505） |
| P1 / P2 の実行の記録と最終報告 | `docs/research/fx_system_p1_p2_fast_track_final_2026_10.md` |
| merge の SHA | PR #505 `57723a2`（2026-10-08T12:13:31Z）、PR #504 `bd69dd1` |
