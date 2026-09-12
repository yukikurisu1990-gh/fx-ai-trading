# Model-Learning Candidate Universe — 18 方向と 2 つの予算

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

成果物は `artifacts/research/model_learning/design.json`。**return・sign・IC・
Sharpe・p 値・PnL を一切計算していない。** 判定は設計の性質である。

---

## 0. 一行で

18 の model / target / architecture 方向のうち **DEVELOPMENT_ADMISSIBLE 9 /
CAPACITY_EXCEEDED 7 / ECONOMICALLY_UNREACHABLE 1 / PRIOR_FAMILY_CLOSED 1**。

そして予算が phase の形を決めた: **3 トラック × 1 構成、ハイパーパラメータ探索ゼロ、
Level 2（木のアンサンブル）は走らせない。**

---

## 1. ⭐ 「バーは標本ではない」を数字にする

| | |
| --- | --- |
| コーパスの M15 行数（20 ペア） | **2,328,360** |
| 日次・断面 20 の名目行数 | 23,557 |
| **有効独立観測数** | **3,015** |
| 1 有効観測あたりのバー数 | **772.2** |

そして重要なのは、**この数字は 2 つの予算のどちらにも入らない**ことである。
両方とも**年**で表される。有効標本が決めるのは fold ごとの経済統計の雑音であって、
何個のパラメータを載せてよいかではない。

## 2. 二つの予算（詳細は設計書）

```
capacity:  p_eff ≤ (1 − retention) × IR_annual² × train_years
search:    z_max(M_eff) ≤ MRIE × √validation_years
```

`train_years = 4.674`、`validation_years = 3.174`（初期学習 1.5 年）。

⭐ **周波数も断面も capacity 予算を緩めない** — 導出で `D_eff` と `T` が消える。
⭐ **有効パラメータの絶対上限は 5.258**、届くには IR が天井 1.5 ちょうど必要。

## 3. ⭐ 頻度が決める帯（バスケット往復 3.406 bp）

| 頻度 | 年間コスト | 必要 gross IR | 許される有効パラメータ |
| --- | --- | --- | --- |
| monthly | 40.9 bp | 0.426 | 0.424 |
| weekly | 177.1 bp | 0.596 | 0.831 |
| twice weekly | 354.2 bp | 0.818 | 1.563 |
| **daily** | **858.3 bp** | **1.448** | **4.899** |

**週次で許されるのは 1 個未満** — つまり定数（手作りルール）しか載らず、それは
前フェーズが exhausted と裁定した領域である。**日次だけが使える予算を持ち、代償は
天井すれすれの必要 IR。**

## 4. 候補表

`p` は宣言された有効パラメータ / 許容量。

| ID | role | verdict | p | effN |
| --- | --- | --- | --- | --- |
| M01 currency cross-sectional ranking | ranking | **ADMISSIBLE** | 4.2 / 4.899 | 3769 |
| M02 residual factor-adjusted return | return | **ADMISSIBLE** | 3.0 / 3.297 | 4711 |
| M03 regime-conditioned level, multi-timeframe | return | **ADMISSIBLE** | 4.4 / 4.899 | 3769 |
| M04 cross-sectional trade/skip | trade/skip | **ADMISSIBLE** | 2.4 / 4.899 | 3769 |
| M05 holding-period selection | horizon | **ADMISSIBLE** | 1.5 / 1.563 | 1821 |
| M06 volatility-scaled allocation | portfolio | **ADMISSIBLE** | 1.0 / 4.899 | 3769 |
| M07 event-proximity conditional return | return | CAPACITY_EXCEEDED | 1.8 / 0.831 | 2120 |
| M08 cross-asset context conditional return | return | CAPACITY_EXCEEDED | 3.0 / 0.831 | 780 |
| M09 dispersion/correlation representation | regime | CAPACITY_EXCEEDED | 5.4 / 4.9 | 3769 |
| M10 HMM per-regime mapping | regime | CAPACITY_EXCEEDED | 16.2 / 4.9 | 3769 |
| M11 learned factor representation | regime | CAPACITY_EXCEEDED | 4.5 / 3.298 | 4711 |
| M12 excursion-conditional exit design | execution | **ADMISSIBLE** | 2.4 / 5.258 | 4711 |
| M13 hurdle-clearing probability + threshold | trade/skip | **ADMISSIBLE** | 3.6 / 4.899 | 2827 |
| M14 intraday session-state return | return | ECONOMICALLY_UNREACHABLE | — | 11307 |
| M15 structural-break state | regime | CAPACITY_EXCEEDED | 5.4 / 4.9 | 3769 |
| M16 activity-state opportunity gate | trade/skip | **ADMISSIBLE** | 1.8 / 4.899 | 3769 |
| M17 rate-differential conditional residual | return | PRIOR_FAMILY_CLOSED | — | 182 |
| M18 boosted-tree cross-sectional ranking | ranking | CAPACITY_EXCEEDED | **72.0 / 4.899** | 3769 |

### ⭐ 落ち方が 4 通りあることが情報である

* **M18（既定の選択肢）** — 300 本 × 8 葉 × lr 0.03 で有効 72 パラメータ、許容の
  **14.7 倍**。Round 1 の ML の失敗は不運ではなく**予算超過**だったことがここで
  説明される。Level 2 を走らせない理由は検証結果ではなく**この数字**である。
* **M14（日中）** — 年 756 回転でコスト 2,555 bp、必要 gross IR は **3.57**。
  天井 1.5 の倍以上で、モデルの良し悪し以前に届かない。
* **M09 / M10 / M11 / M15（表現）** — consumer のパラメータと**合算**して課金する
  ので、admissible な consumer の上に表現を載せると合計で予算を割る。
  ⭐ **モデルを 2 つに割っても予算は 2 つにならない。**
* **M07 / M08（低頻度 × 多特徴量）** — 週次以下は許容 0.831 個なので、3〜5 個の
  係数は載らない。
* **M17** — `assert_prospective` が carry family を実際に拒否（`refused_by` に記録）。

### ⭐ 買える regime conditioning は 1 つだけ

`states × (coefficients + 1)`（状態ごとに別の写像）は 3 状態 3 係数で 12 個。
`coefficients × shrinkage + states`（**傾きは共有、水準だけ状態依存**）なら
2 状態 4 係数 0.6 で 4.4 個。**4.674 年が買えるのは後者だけ。**

## 5. Phase 予算 — トラックごとではなく phase 全体

| tracks × configs | M_eff | inflation | 可否 |
| --- | --- | --- | --- |
| 1 × 7 | 2.80 | 0.463 | ✓ |
| 2 × 2 | 2.60 | 0.435 | ✓ |
| **3 × 1** | **3.00** | **0.488** | **✓** |
| 3 × 2 | 3.90 | 0.590 | ✗ |
| 4 × 1 | 4.00 | 0.600 | ✗ |

⭐ **3 トラックが買えるのは「各 1 構成」のときだけ。** ハイパーパラメータ探索は
どこにも存在しない。そして Level 2 を諦めることは**何も失わない** — capacity が
先に否決しているので、検証で何が出ても採用できない。

## 6. Ranking と選抜

ランキング基準は**すべて成果物にあるフィールド**である（前フェーズのレビューが
「成果物に無い基準での ranking」を削除させた）。順に: self-contained か、
capacity 利用率が帯 `[0.50, 0.95]` に入るか、特徴量ファミリー数。

| rank | candidate | role | 利用率 | 帯内 | families |
| --- | --- | --- | --- | --- | --- |
| 1 | M03 regime-conditioned level | return | 0.898 | ✓ | 4 |
| 2 | M13 hurdle-clearing probability | trade/skip | 0.735 | ✓ | 4 |
| 3 | M01 currency ranking | ranking | 0.857 | ✓ | 3 |
| 4 | M02 residual return | return | 0.910 | ✓ | 3 |
| 5 | M04 cross-sectional trade/skip | trade/skip | 0.490 | ✗ | 3 |
| 6 | M05 holding-period selection | horizon | 0.960 | ✗ | 3 |
| 7 | M12 excursion exit design | execution | 0.456 | ✗ | 3 |
| 8 | M16 activity-state gate | trade/skip | 0.367 | ✗ | 3 |
| 9 | M06 volatility-scaled allocation | portfolio | 0.204 | ✗ | 3 |

帯の**両端**を外す理由: 利用率が低い候補は data が答えられる問いより小さい問いを
聞いており、高すぎる候補は誤差のある有効パラメータ推定に依存している。

**選抜（role 重複なし、phase 予算の上限まで）: M01 / M03 / M13。**
これは裁定 §41 が必ず比較対象に含めよと指定した Track candidate A / B / C と
一致した — 強制ではなく、宣言された規則の出力である。

## 7. Seen training data inventory

| span | 期間 | これまでの役割 | 汚染 |
| --- | --- | --- | --- |
| momentum_2021_2023 | 2021-04-26 … 2023-04-25 | deciding panel | H-007 〜 H-021 の 15 本 |
| supplemental_2023_2025 | 2023-04-26 … 2025-04-24 | deciding panel | H-006 〜 H-021 の 15 本 |
| development_2025 | 2025-04-25 … 2025-12-28 | screening のみ | H-001 〜 H-021 の 19 本、約 1,200 構成 |

3 つは**連続**（隣接が import 時に検査される）、合計 **4.674 年**。それぞれが
自分の guarded route を持ち、本パッケージは境界を再実装しない。

⭐ **約 1,200 構成という既往の multiplicity は補正しない。** 本フェーズの
当てはめだけを数える予算では補正できないし、seen data 上の何をしても補正できない。
守るのは誰も見ていないデータでの一度きりの評価だけである。

## 8. Protected data confirmation

fresh pool `2016-06-02 … 2021-04-25`、historical OOS、dead window、
forward Formal Confirmation epoch — **すべて未読**。`assert_not_protected` が
両端を拒否し、**厳密な `YYYY-MM-DD` でない境界は比較せずに拒否**する（3 つの
reader route で監査が見つけた欠陥を最初から閉じてある）。設計段階のモジュールは
`open(` すら含まない（driver を除く）。

## 9. 変異テスト

**32/32 kill。** 初回は 28/32 で、生存 4 件がそのまま 4 本のテストになった:

* ⭐ **選択雑音が年数の平方根ではなく年数で減る** — どちらも単調に減るので
  monotonicity テストでは見分けられない。このコーパスでは 1.8 倍の差で、
  「3 トラック買える」と「12 トラック買える」の差。
* ⭐ **ranking が self-contained を優先しなくなる** — 現行カタログでは順位だけが
  動いて結論は動かないので、結果のテストでは見えない。
* ⭐ **選抜が同じ role を 2 つ採れるようになる** — 実際のランキングの上位 3 件は
  たまたま role が異なるので、出力テストでは検出できない。
* ⭐ **capacity 利用率の帯が両端を外さなくなる** — 帯を外れる候補が上位 3 件に
  入ってこないので、やはり出力テストでは検出できない。

4 件とも「**現行データでは結論が変わらないが、機構は壊れている**」型である。
