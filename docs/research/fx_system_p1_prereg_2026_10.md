# P1 — COMPONENT_SUPPLY_AND_SYSTEM_UPPER_BOUND 事前登録（2026-10-08、計算の前）

**この文書と `scripts/research/fx_system_reopen_feasibility/prereg.py` は、system の上限を計算する code を書く前・走らせる前に commit する。** 計算の記録は、両方の sha256 を保存する。

**承認**: Human + ChatGPT の指示（2026-10-08）の、P1 / 条件付きの P2 に限った一度限りの HOLD の例外（`docs/governance/fx_system_architecture_ruling_2026_10.md` §6）。新しい価格 data・broker・fresh・backtest は使わない。新しい文献の候補は加えない。

## 1. 問い

現在までに確認された economic mechanism だけを使った場合、production 級の system の Sharpe 1.0 に理論的に到達する余地があるか。新しい alpha は探さない。

## 2. component の universe

`prereg.py` の `FAMILIES` に、15 の family を固定する。

- 同じ economic source を、strategy の名前の違いで複数に数えない。
- EUR の欧州の朝・JPY の仲値の後・EUR の ECB の後は、**同じ W 字の fixing / 在庫の family（F1）の別の窓**。
- 自国時間の顧客の flow（F2）は、F1 と同じ時間・同じ符号の窓なので、F1 に統合する。
- **過去の判定（REJECT・RED・CLOSED・HOLD・NO_DECISION_GRADE_PASS_REGION・DUPLICATE・NOT_IMPLEMENTABLE・ECONOMICALLY_UNATTRACTIVE）を受けた family は、全ての scenario で寄与 0**（LOCKED）。
- F1 だけは、HOLD の裁定 §6 が near-miss として保存した family なので、上限の計算に入れる。これは component gate の判定ではなく、上限の計算である。

## 3. scenario（計算の前に固定）

年率の retail の net Sharpe（真の値の想定）。

| 窓 | P1-O（Optimistic） | P1-B（Base） | P1-S（Stress） |
| --- | --- | --- | --- |
| EUR の欧州の朝（02:00 → 08:15 ET） | 0.74（B&R 1997–2007、古い） | 0.40 × 0.70 = 0.28 | 0.16 × 0.40 = 0.064 |
| JPY の仲値の後 | 0.85（KMW 1999–2018 の平均。**最近の証拠と矛盾**） | 0 | 0 |
| EUR の ECB の後（08:15 → 17:00） | 0.25（KMW 1999–2018） | 0 | 0 |
| 窓の間の相関 ρ | 0 | 0.3 | 0.5 |
| cost の倍率 | 1.0 | 1.0 | 1.5 |

**根拠**:

- **O**: 原典で確認された、実装の可能性のある最も強い post-cost の効果（#503 §13a〜§13c）。3 つとも、最近の証拠より古い sample の値。
- **B**:
  - 最近の原典の証拠（KMW の CME 2009–2018、firm な気配・全 spread）を優先する。
  - EUR の朝: CME を基にした retail の推定 0.29〜0.52 の中間 0.40 に、公表の後の減衰 30% を掛ける。#505 の設計の感度 30〜60% の低い端を使う理由は、CME の期間が KMW の公表より前なので、減衰の全量は掛けないため。
  - JPY: 最近の中心は 0 以下で、最適化は持たないので 0。
  - ECB の後: CME で 0.08 で、retail ではそれ以下なので 0。
  - 相関 0.3: W 字の強さが日ごとに共通に効く。
- **S**: 最低の推定（L1 を基にした 0.16）に減衰 60%、cost 1.5 倍、相関 0.5。

## 4. 上限の計算（code で行う）

- **制約なし**: 窓の Sharpe の vector s と相関 R から √(sᵀR⁻¹s)（符号の制約なし）と、long だけ（重み ≥ 0）の値。
- **cost の stress**: 各窓の Sharpe を 0.5 × cost / σ × √250 だけ下げる（cost の倍率が 1.5 の場合）。
- **通貨の exposure の制約**: 3 つの窓は時間が重ならず、同時に複数の通貨の exposure を持たない。Sharpe は変わらないことを確かめる。
- **family の集中の制約**: distinct な family の数を数える。1 つなら、集中の上限（1 family ≤ 50% の risk）の下で system を組めない。
- **時刻の重なり**: 3 つの窓の時刻を列挙し、重なりの有無を記録する。
- **当日決済の制約**: overnight の family を除く（全て LOCKED なので、判定に影響しない）。
- **判定に使わない感度**（事前に宣言）:
  - 窓の間の負の相関 ρ = −0.2
  - 状態を解いた参考の行（#497 の TC-net 0.127、#495 の M16 の 0.276。当日決済に反し、閉じた family）

## 5. 判定の規則（指示 §13。後から変えない）

| 判定 | 条件 |
| --- | --- |
| **PASS** | (1) Base の credible な system の上限 ≥ 1.0、(2) 1 つの古い sample・1 つの極端な相関・1 つの古い component だけで成立していない、(3) 正の限界の寄与を持つ distinct な family が 2 つ以上、(4) cost の stress の後も現実的な余地 |
| **AMBER** | Optimistic で ≥ 1.0、Base で < 1.0 → P2 に進まない |
| **STOP** | Base と Optimistic のどちらにも credible な 1.0 の経路が無い、または 1.0 超えが古い JPY など 1 つの古い推定だけに依存する → `PORTFOLIO_ARCHITECTURE_FEASIBLE_BUT_COMPONENT_SUPPLY_INSUFFICIENT`、HOLD 継続 |

P2 は P1 が PASS の場合だけ実行する。
