# Model-Learning Development — 事前登録（凍結）

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Frozen hash（実行時）: **`6d0809fdb3e3e47ce20babb3d2ed2171f32479956a219db1dba5e157c7680475`**
Frozen hash（レビュー後に coverage を拡張した現行値）: **``**

> ⭐ **実行された run が承認されていたハッシュは前者であり、動かさない。**
> レビューが「ハッシュが覆う範囲は主張より遥かに狭い」ことを 9 定数の改変で
> 実演したため、spec は span の実日付・`PAIRS_20`・実測ボラティリティ・妥当性
> 天井・leakage controls・feature モジュールの SHA-256 を覆うようになった。
> それがハッシュを動かす。**記録はそれと一緒に動いてはならない。**

正本は `scripts/research/model_learning/prereg.py`。本文書はその写しであり、
両者が一致することをテストが測る。**凍結は文章ではなく content hash で行う** —
`assert_frozen()` が一致しない限り development は走らない。閾値を fold を見た後で
動かすのは規律の問題ではなく、**実行が止まる**。

---

## 0. ⭐ レビュー後の状態

この事前登録は**実行された run の記録**として保持する。訂正後のゲートの下では:

* **登録された shape は買えない** — 3 track × 1 config の null pass 確率は 0.46、
  α = 0.05 に対して。1 選択でも 0.19 で、3.174 年では 0 通り。
* **3 トラックとも admissible ではない** — 実測 377.7 bp のボラティリティに対し
  日次バスケットは break-even gross IR 2.27 を要求し、天井は 1.5。
* **それでも run は起きた**（レビューが返る前）。3 本とも自分の合格規則に落ちた。
* **訂正後に再実行はしていない。**

## 1. 探索予算（裁定 §30 / §31）

| | |
| --- | --- |
| tracks | **3** |
| configurations / track | **1** |
| 当てはめる構成の総数 | **3** |
| phase 有効構成数 | 3.00 |
| 選択による年次 IR 膨張 | **0.488**（天井 0.5） |
| 走らせる階層 | Level 0 baseline、Level 1 regularised linear |
| Level 2 を走らせない理由 | **capacity 予算**であって検証結果ではない |

**ハイパーパラメータ探索・特徴量選択・fold 外での閾値掃引は、どこにも存在しない。**

## 2. CV architecture（裁定 §18）

* scheme `walk_forward`、window `expanding`
* 初期学習 **1.5 年**、ステップ 0.5 年、合計 4.674 年、out-of-fold **3.174 年**
* purge = target の forward horizon 全体、embargo = さらに 1 日
* **validation から未来の train へ戻らない**
* **random split 禁止**（role gate が拒否する）

## 3. Cost model（裁定 §23 / §33）

| | |
| --- | --- |
| pair 往復 | 2.58 bp |
| basket 往復 | 3.406 bp |
| 根拠 | Track 3 の実測 market-order 往復 × バスケット gross exposure |
| ストレス倍率 | 2.0 |
| 課金 | 実現 turnover に対し、リバランスごと、両脚 |

## 4. トラック

### Track A — `M01_currency_cross_sectional_ranking`

* **target**: 各 G10 通貨の翌 UTC 日の対バスケット相対リターンから、建てる
  リバランスの往復コストを引いたもの
* **cross-section**: 8 通貨、**係数ベクトルは共有 1 本**
* **features（7 個、凍結）**: `currency_excess_return_5d_z` /
  `_20d_z` / `_60d_z` / `currency_realised_vol_20d_z` /
  `currency_dispersion_share_20d_z` / `currency_beta_to_common_factor_60d` /
  `currency_beta_to_risk_factor_60d`
* **model**: ridge、学習 fold 内で**実効自由度 4.2 を目標**に penalty を決める
  （目標であってチューニング対象ではない）
* **baseline (Level 0)**: `currency_excess_return_20d_z` 単独の等加重断面ランク、
  上位 2 ロング・下位 2 ショート、同じ turnover と同じコストモデル

### Track B — `M03_regime_conditioned_level_multi_timeframe`

* **target**: 同じ cost-adjusted 翌日相対リターン。共有された傾きに対する
  **gain** だけが 2 状態で異なることを許す（切片は断面で一定になり、target は
  断面で 0 和なので、切片は構造上同定されない）
* **features（4 個、凍結）**: `currency_excess_return_20d_z` /
  `multi_timeframe_alignment_h1_h4_d1` / `currency_realised_vol_20d_z` /
  `trend_age_d1_normalised`
* **state**: バスケットの 60 日実現ボラティリティの 2 分割。閾値は**学習 fold 内の
  expanding-window 中央値のみ**
* **baseline (Level 0)**: 同じ 4 特徴量に**単一の gain**、regime 分割なし —
  これが「状態そのものの価値」を切り出す

### Track C — `M13_hurdle_clearing_probability_with_learned_threshold`

* **target**: 通貨脚の翌日絶対変動が自分の往復コストを超える確率。
  受容閾値は**学習 fold 内で**当てはめる
* **features（6 個、凍結）**: `currency_realised_vol_20d_z` /
  `currency_realised_vol_5d_over_20d` /
  `days_to_next_scheduled_g4_decision` /
  `days_since_last_scheduled_g4_decision` / `currency_spread_state_20d_z` /
  `currency_range_state_20d_z`
* **base opportunity**: Track A の baseline がポジションを取る全ての日次通貨脚。
  ⭐ **その無条件 cost-adjusted 期待値を先に測り、それが kill rule である** —
  base が負なら、その中でのフィルタは証拠にならない
* **baseline (Level 0)**: base opportunity を全部取る（フィルタなし）

## 4a. ⭐ 実行前に訂正した 6 点（当てはめる前、結果は存在しない）

| was | now | なぜ |
| --- | --- | --- |
| `cross_sectional_dispersion_20d_z` | `currency_dispersion_share_20d_z` | 日ごとに一定の特徴量は、断面で 0 和の target と共分散が厳密に 0 — 係数が同定されない |
| `currency_beta_to_usd_factor_60d` | `currency_beta_to_common_factor_60d`（leave-one-out） | 自分を含む平均に回帰すると、算術だけで beta が上振れする |
| regime 依存の**切片** | regime 依存の **gain** | 同じ同定問題。容量コストは同じ |
| `tick_activity_state_20d_z` | `currency_range_state_20d_z` | 3 route が作った M15 キャッシュに volume 列が無い（※ volume は `monetizability/volume_cache/` に存在する。substitution の理由付けは後に訂正した） |
| 通貨別の中銀近接 | 4 行の最も近い決定までの距離（global） | AUD/EUR/JPY/USD しか取得できない。通貨別にするとその 4 通貨のダミーになる |
| 脚ごとに cost-adjusted な回帰 target | forward excess return + 建てる時点でコスト課金 | 脚のコストはポジション変化に依存し、ポジションは予測に依存する（同定不能） |

## 5. 指標（裁定 §32）

out-of-fold net / gross 年次 IR、年次 turnover、net 年次リターン bp、
ストレスコスト下の net、fold ごとの net IR、通貨ごとの net 寄与、
ボラティリティ regime ごとの net 寄与、上位 10 日の net 占有率、最大ドローダウン、
rank IC、fold 間の係数安定性。

## 6. Success rule（裁定 §46 Case A）

**全条件が成立すること。**

| 条件 | 閾値 |
| --- | --- |
| 宣言した baseline を上回る年次 IR | **≥ 0.5** |
| out-of-fold net 年次 IR | 正 |
| ストレスコスト（×2）で生存 | 必須 |
| 正の fold の割合 | **≥ 0.75** |
| 正に寄与する通貨数 | **≥ 5** |
| 上位 10 日の net 占有率 | **≤ 0.50** |
| 当てはめ後の実効自由度が予算内 | 必須 |

## 7. Kill rule（裁定 §39）

baseline を MRIE だけ上回らない / out-of-fold net が負 / ストレスコストで消える /
正の fold が 3/4 未満 / 正の通貨が 5 未満 / 上位 10 日が net の過半 /
効果が 1 つのボラティリティ regime に限局 / leakage control の違反が見つかる。

## 8. 禁じられた救済（裁定 §38）

fold を見た後の特徴量追加、fold を見た後の horizon 変更、符号反転、
負けた期間を切り出す regime 条件の後付け、モデル容量の引き上げ、
seed を変えて良い方を報告、**保護 span の目的を問わない読み取り**。

## 9. 到達しうる最大の status（裁定 §34）

`DEVELOPMENT_MODEL_CANDIDATE`。**`EDGE_CONFIRMED` も `PRODUCTION_READY` も
使わない。** 成立した場合でも fresh pool へは自動で進まず、凍結した最終仕様を
Human + ChatGPT へ提出する（裁定 §35）。
