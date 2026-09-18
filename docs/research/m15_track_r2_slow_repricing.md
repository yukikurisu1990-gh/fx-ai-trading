# T-R2 — 市場利回りの slow repricing state（20 日）development 結果

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

判定: **`MARKET_YIELD_SLOW_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`**（裁定 §48 の Case C）

Human + ChatGPT 裁定（2026-09-18）で承認された slow formulation 1 本。事前登録は
`scripts/research/market_yields/prereg_r2.py` で **結果を含まない状態**で凍結・commit し（digest で固定）、そのあと 1 度だけ実行した。
保護 span（fresh pool `2016-06-02 … 2021-04-25`、historical OOS、dead window、forward epoch）は読んでいない。

---

## 1. 問いと、fast との違い

fast（T-R）は **shock** を問うた: その日の政策パス改定に FX が反応するか。
T-R2 は **state** を問う: 1 か月かけて動いた政策パスの位置に、FX が遅れて追随するか。

「cost を下げるために 5 日を均した」のではない。主張している市場像が違う（反応の速さ か、調整の遅さ か）。
horizon は **20 日 1 本**で、grid は禁止。20 日は裁定が名指しした値で、結果を見て選んでいない。

## 2. 事前に記録した予測（実行前）

| 項目 | 値 |
| --- | --- |
| band law（半減期 20 日）の turnover | 18.3 |
| fast の実測/設計 倍率から | **34.7** |
| noise attenuation model から | 58.0 |
| screen の turnover 上限 | **45** |
| net 0.3 に必要な日次 IC（breadth 2.5、band law） | 2.71% |
| 80% 検出力で分離できる net Sharpe | **1.13** |

**中心的診断**（事前登録）: turnover が落ちたとき gross が残るか。残れば fast の失敗は cost の問題。
消えれば、金利情報は短命で monetize 不能だったことになる。

## 3. 結果（1 回のみ実行、1190 決定日）

| book | gross Sharpe | net Sharpe | 年率 gross | 年率 net | 年間 cost | turnover | IC 20 日 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A fast 5 日（参照、再探索なし） | +0.279 | −0.727 | +3.04% | −7.94% | 10.98% | 83.3 | −2.49% |
| **B slow 20 日 state** | **+0.541** | **+0.042** | +5.66% | +0.44% | 5.22% | **39.3** | −4.01% |
| C FX price control（20 日） | −0.256 | −0.721 | −2.69% | −7.56% | 4.87% | 40.2 | −5.01% |
| **D 残差（主検定）** | **+0.834** | **+0.051** | +8.70% | +0.54% | 8.17% | 59.8 | −1.57% |
| E D の momentum 脚（分解用） | −0.024 | −0.770 | −0.25% | −8.07% | 7.82% | 65.3 | +3.97% |

### 中心的診断への答え

**turnover は落ち、gross は残った。むしろ上がった。**

- turnover: A 83.3 → B **39.3**（事前予測 34.7 に近い）
- gross Sharpe: A +0.279 → B **+0.541**、D **+0.834**
- net Sharpe: A −0.727 → B **+0.042**、D **+0.051**（符号が変わった）

つまり **fast formulation の失敗は、少なくとも部分的には cost の問題だった**。情報が完全に短命だったわけではない。
これは今回いちばん情報量のある観測で、事前に「どちらでも結論になる」と書いた両側のうち、片側が実現した。

### それでも成立しない理由

net は **+0.04 / +0.05** で、break-even 近傍にすぎない。screen の 9 条件のうち 3 つが落ちる。

| 条件 | 結果 |
| --- | --- |
| B の gross Sharpe > 0 | **満たす**（+0.541） |
| D が C に対して正の net 増分 | **満たす**（+0.051 対 −0.721） |
| D の rate 脚が D の gross の半分以上 | **満たす**（65.0%） |
| 6 block の過半が正 | **満たす**（4 / 6） |
| **1 通貨を落としても符号が残る** | **満たさない**（5 通り全部負: −0.09 〜 −1.03） |
| **turnover ≤ 45** | **満たさない**（D は 59.8。B 単独なら 39.3） |
| 年間 cost ≤ 年間 gross | **満たす**（8.17% 対 8.70%） |
| **cost 1.5 倍・2 倍でも net > 0** | **満たさない**（D: −0.34 / −0.73） |
| 5% 年率が gap stress の内側 | 形式的には満たす（後述） |

→ **stop**。

## 4. 主検定の分解（事前登録どおり）

D = B − β·C は「金利残差」と「逆向き momentum 脚」の合成なので、事前に分解を登録していた。

| 量 | 値 |
| --- | --- |
| D の年率 gross | +8.70% |
| rate 脚（B）の年率 gross | +5.66% |
| momentum 脚（E）の年率 gross | −0.25% |
| 突合ギャップ（cap と band による非線形分） | +3.29% |
| **rate 脚が D の gross に占める割合** | **65.0%** |
| β の平均 / 標準偏差 / 5–95%点 | 0.38 / 0.47 / [−0.54, 0.93] |

**D の gross は momentum 脚が作ったものではない。** ただし β のばらつきが大きく（sd 0.47、符号も変わる）、
突合ギャップ 3.29% は小さくない。D を「純粋な金利情報」と読むことはできない。

## 5. 持続性・安定性・集中

- signal の日次自己相関: B **0.898**（半減期 6.4 日）、D 0.826。fast の 0.661（1.7 日）より明確に持続する。
- position の自己相関: B 0.847（半減期 **4.2 日**）、D 0.717（2.1 日）。売買した日は B で 54.0%、D で 69.4%。
- block: B は 6 中 3 が正（+1.18, +0.88, +0.94 対 −0.28, −1.55, −0.98）、D は 4 / 6。
- **leave-one-currency-out は 5 通りすべて負**（D: without_EUR −0.09、without_GBP −0.12、without_CAD −0.49、without_USD −0.59、without_JPY −1.03）。
  1 通貨を抜くだけで符号が消えるので、**5 通貨という狭い断面に依存している**。
- 通貨別 gross: D は USD +0.30、JPY +0.19、EUR +0.12 対 CAD −0.19。**USD と JPY で大半**。
- 最大 DD: B −27.1%、D −36.9%。上位 5 日は net の 4.7〜6.0 倍（net がほぼ 0 なので比は意味を持たない）。

## 6. leverage・margin・利益容量（#484 の枠組み、この universe で測る）

この book 自身の単位 gross あたり vol（実現 vol ÷ 平均通貨 gross）で測ると:

- 10% vol target: 平均 risk leverage **3.83**、margin 利用率は leverage tail で **23.4%**、gap stress 後の維持率 **1.44** で loss-cut に至らない。
- **年 5% は届かない**: net Sharpe 0.05 では必要 vol が 98% になり、その leverage は gap stress で loss-cut に至る。
  net が break-even 近傍である以上、leverage は意味を持たない（#484 の原則どおり）。

screen の「5% が gap stress の内側」条件は net > 0 と loss-cut 無しで形式的に満たすが、**必要 vol の水準を見れば実質的には届かない**。
この条件の書き方は次の formulation で締めるべき（§8）。

## 7. 判定と、その scope

**`MARKET_YIELD_SLOW_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`。**

意味するもの: **事前登録した 20 日 state の formulation が、この seen span で経済的に成立しなかった。**
turnover は下がり gross は残ったが、net は break-even 近傍で、cost 1.5 倍で崩れ、1 通貨の除外で符号が消える。

意味しないもの:

- market-yield repricing family 全体の閉鎖。**fast と slow の両方が不支持**になったので、裁定 §20 の
  `MARKET_YIELD_REPRICING_SIMPLE_DIRECTIONAL_FAMILY_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` を**検討できる段階**には来たが、
  それは OIS・intraday rate futures・market-implied policy path・曲線の非線形性には**届かない**（いずれも未観測）。
- 「金利情報に予測内容が無い」。この span は 80% 検出力で net 1.13 未満を分離できない。D の gross +0.834（t ≈ 1.82）も、
  B の +0.541（t ≈ 1.18）も、**decision-grade ではない**。

## 8. 次にやらないこと / Human に返すこと

やらないこと（事前登録の禁止事項）:

- horizon・符号・lookback・universe・control の変更、vol target や band や cost 規約による救済、非線形化・ML 化。
- turnover 上限 45 を結果後に緩めること。D は 59.8 で落ちたが、これは事前に置いた数値である。
- AUD・NZD・CHF を足せば救えるという議論（裁定 §11 で明示的に禁止）。

Human + ChatGPT に返す論点:

1. **family closure を宣言するか**。fast と slow の両方が不支持で、closure token は用意してある。ただし上記のとおり
   未観測の情報源（OIS、政策パスの市場織り込み、曲線）には届かない。
2. **B 単独（turnover 39.3、net +0.042、cost 5.22%）を別 formulation として扱うか**。今回の主検定は D であり、
   B は control なしの book なので、`FX price control を超える増分` の保証がない。私からは提案しない。
3. **screen の「5% が gap stress の内側」条件**は、net がほぼ 0 でも形式的に真になりうる。次に使うなら
   「必要 vol が現実的な範囲（例えば 15% 以下）」を条件に含めるべき。
