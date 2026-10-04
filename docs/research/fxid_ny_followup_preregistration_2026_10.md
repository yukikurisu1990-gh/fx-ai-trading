# R-A2b 事前登録 — NY の entry 時刻の signal-free の経済性（2026-10-05）

**`POST_HOC_EXPLORATORY_FOLLOW_UP` · `NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.**

この文書は**実 data を読む前に** commit する。run はこの文書の sha256 を記録し、この文書が commit されていない、または変更されているときは走らない。

## 0. 位置づけ

- Human + ChatGPT の裁定（2026-10-05、R-A2b = `NY_ENTRY_TIME_SIGNAL_FREE_ECONOMICS`）に基づく。
- FXID Cycle 1 の結論 `FXID_CYCLE1_EXIT_CONDITION_II_FIRED_RETURN_TO_HUMAN` は変更しない。この検証の結果が良くても、Cycle 1 が PASS になることはない。
- Cycle 1 の結果を見た後に設計したので、**`POST_HOC_EXPLORATORY_FOLLOW_UP`** であり、独立した確認の証拠ではない。

## 1. data

| 項目 | 範囲 |
| --- | --- |
| cache | seen の M15 bid / ask cache（Cycle 1 と同じ） |
| 期間 | 2021-04-26 … 2025-12-28 |
| pair | `PAIRS_20` |
| route | `scripts/research/patsd_stage0/data.py::load_pair`（`exploratory_m15.{momentum,supplemental,bars}` の span と fresh の guard を通る） |

新しい取得・OANDA の接続・fresh / OOS / dead / forward は無い。

## 2. 評価時刻（固定。追加・変更しない）

時刻帯は `America/New_York`（夏時間と冬時間を時刻帯の規則で扱う）。NY の現地の平日ごとに 1 回。

| 名前 | entry（ET） | exit（ET、4 時間後） | 役割 |
| --- | --- | --- | --- |
| `ny_0900` | 09:00 | 13:00 | **主** |
| `ny_0930` | 09:30 | 13:30 | **主** |
| `ny_1000` | 10:00 | 14:00 | **主** |
| `ny_0800` | 08:00 | 12:00 | 比較の基準（Cycle 1 の anchor） |

- 決済は全て NY 16:45 より前で、同じ取引日（NY 17:00 区切り）の中にある。rollover（17:00）の前後 30 分に掛からない。
- 08:00 ET は既存の FX 研究上の anchor で、米国の株式市場の公式の開場（09:30 ET）とは別のものである。

## 3. 統計量（pair × 評価時刻ごと）

**価格の snapshot**: 時刻 T の snapshot は、T に終わる M15 bar（開始 T − 15 分）の終値。T と T + 4 時間の両方の snapshot がある日だけを使う。

| # | 量 | 定義 |
| --- | --- | --- |
| 1 | entry の spread | T の snapshot の close spread / mid（日の平均、bp） |
| 2 | 決済の spread | T + 4 時間の snapshot の close spread / mid（日の平均、bp） |
| 2b | entry の直後の spread（開示用） | T + 15 分の snapshot（10:00 の発表の時刻の参考） |
| 3 | σ_4h | T から T + 4 時間の log mid の変化の標準偏差（ddof 1） |
| 4 | round-trip cost（**主**） | 日ごとの (s_entry / 2 + s_exit / 2) の平均 + slippage |
| 4′ | round-trip cost（Cycle 1 の方式、比較用） | T と T + 15 分の snapshot の spread の平均（片側の spread を全額、往復の cost とする）+ slippage |
| 5 | cost / σ | 4 / 3（4′ / 3 も） |
| 6 | 追加の必要期待利益 / σ | S / √(k · n)。S = 1.0（G4 は変えない） |
| 7 | 必要 gross / σ | 5 + 6 |
| 8 | 15% 基準との比較 | 7 ≤ 0.15 なら基準内 |

- **二重計上しない**: mid を基準に、entry と exit でそれぞれ half spread を払う。同じ size の往復を想定する。
- **slippage の計上の単位**: 往復で 1 回、0.5 bp（Cycle 1 と同じ。片側 0.25 bp に当たる）。
- 方向・side・return の平均・損益は計算しない。

## 4. 主判定（固定）

- 基本条件: k = 3、n = 100（1 pair 年 100 回）、slippage 0.5 bp / 往復、cost は 4（entry と exit の half spread）。
- **評価時刻ごとの主統計量** = 20 pair の中央値の必要 gross / σ。
  - ≤ 0.15 → その時刻は `ECON_WITHIN_15PCT`
  - それ以外 → `ECON_EXCEEDS_15PCT`
- **全体**:

  | 区分 | 条件 |
  | --- | --- |
  | `R_A2B_ECON_ALL_THREE` | 主の 3 時刻とも基準内 |
  | `R_A2B_ECON_PARTIAL` | 1〜2 時刻が基準内 |
  | `R_A2B_ECON_NONE` | 0 時刻 |

- **境界**: pair の値が 0.15 ± 0.005 なら「境界」と表示する（判定は変えない）。
- 結論の A / B / C（裁定 §20）は、この経済性の区分と、S1 / S2 の機構の監査（data を使わない）を合わせて決める。
  - 経済性が `R_A2B_ECON_NONE` なら C。
  - それ以外は、機構が立てば A、弱ければ B。

## 5. 感度（主判定とは別。判定を変えない）

各評価時刻で、20 pair の中央値と基準内の pair の数を出す。

| 軸 | 値 |
| --- | --- |
| 実効の breadth k | 2, 3, 5 |
| 1 pair の年間取引数 n | 50, 100, 200 |
| slippage（往復） | 0.5 bp（基本）、1.0 bp（stress） |
| cost の方式 | entry と exit の half spread（主）、Cycle 1 の entry の窓だけの近似 |

## 6. その他の signal-free 統計（開示用）

- 評価時刻ごとの 4 時間の変化の、pair 間の相関行列の participation ratio（Cycle 1 と同じ関数）。return の相関に基づく代理で、戦略の独立な賭けの数を保証しない。
- 08:00 の Cycle 1 方式の cost / σ が、Cycle 1 の記録（中央値 0.0731）を再現するかの確認。

## 7. 停止

R-A2b の run は 1 回。記録は上書きしない。dirty tree・この文書が未 commit・この文書の sha256 の不一致では走らない。
