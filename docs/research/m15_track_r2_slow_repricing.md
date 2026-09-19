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

## 3. 結果（1 回のみ実行。return panel 1212 日、主検定 D の決定日 1190 日）

| book | gross Sharpe | net Sharpe | 年率 gross | 年率 net | 年間 cost | turnover | IC 20 日 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A fast 5 日（参照、再探索なし） | +0.279 | −0.727 | +3.04% | −7.94% | 10.98% | 83.3 | −2.49% |
| **B slow 20 日 state** | **+0.541** | **+0.042** | +5.66% | +0.44% | 5.22% | **39.3** | −4.01% |
| C FX price control（20 日） | −0.256 | −0.721 | −2.69% | −7.56% | 4.87% | 40.2 | −5.01% |
| **D 残差（主検定）** | **+0.834** | **+0.051** | +8.70% | +0.54% | 8.17% | 59.8 | −1.57% |
| E D の momentum 脚（分解用） | −0.024 | −0.770 | −0.25% | −8.07% | 7.82% | 65.3 | +3.97% |

### 中心的診断への答え — 比較対象を正しく取ると

診断は **A → B**（rate state book どうし）で登録されている。そこでは turnover が落ちて gross は上がった。
一方で **主検定どうし**（fast の残差 対 D）を並べると、像が変わる。fast を同じ修復済み layer で再実行した記録
（`artifacts/research/market_yields/fast_repaired.json`）が既にあるので、like-for-like で比較できる。

| 比較 | fast 5 日 | slow 20 日 | 差 |
| --- | --- | --- | --- |
| **rate state book**（A → B、事前登録の診断） | gross +0.279 / turnover 83.3 / net −0.727 | **+0.541 / 39.3 / +0.042** | gross **+0.261** |
| **主検定の残差**（fast の C → D） | gross **+0.863** / turnover 98.8 / net −0.359 | **+0.834 / 59.8 / +0.051** | gross **−0.029** |

つまり:

- **rate state book では gross が上がった**（+0.279 → +0.541）。これが事前登録した診断の答えで、片側が実現した。
- **主検定では gross は上がっていない**。ほぼ横ばい（年率 9.28% → 8.70%、Sharpe −0.029）で、
  **net の改善 +0.41 は全額 cost の節約**（年間 cost 13.16% → 8.17%）である。

この読み方のほうが結論は強い。**同じ gross を、4 割少ない売買で取れている。**
初稿は D の gross +0.834 を A の +0.279 と並べて「むしろ上がった」と書いていたが、
それは別の book どうしの比較で、+0.863 という比較対象は既に手元にあった。訂正する。

したがって: **fast formulation の失敗は、少なくとも部分的には cost の問題だった。**
情報が完全に短命だったわけではない。ただし「情報量が増えた」わけでもない。

### それでも成立しない理由

net は **+0.04 / +0.05** で、break-even 近傍にすぎない。screen の 9 条件のうち **4 つ**が落ちる。

| 条件 | 結果 |
| --- | --- |
| B の gross Sharpe > 0 | **満たす**（+0.541） |
| D が C に対して正の net 増分 | **満たす**（+0.051 対 −0.721） |
| D の rate 脚が D の gross の半分以上 | **満たす**（65.0%。ただし §4 のとおりこの比は P&L の配分ではない） |
| 6 block の過半が正 | **満たす**（4 / 6） |
| **1 通貨を落としても符号が残る** | **満たさない**（5 通り全部負: −0.09 〜 −1.03） |
| **turnover ≤ 45** | **満たさない**（D は 59.8。B 単独なら 39.3） |
| 年間 cost ≤ 年間 gross | **満たす**（8.17% 対 8.70%） |
| **cost 1.5 倍・2 倍でも net > 0** | **満たさない**（D: −0.34 / −0.73） |
| **5% 年率が gap stress の内側** | **満たさない**（§6） |

→ **stop**。

### cost の余裕はどれだけか

「cost 1.5 倍で崩れる」は余裕を過大に見せる。exposure は cost を見ないので charged cost は倍率に正比例し、
**break-even 倍率 = 年率 gross ÷ 年間 cost** で厳密に出る:

| book | break-even cost 倍率 | gross t | net t |
| --- | --- | --- | --- |
| B slow 20 日 state | **1.085** | 1.18 | 0.09 |
| D 残差（主検定） | **1.066** | 1.81 | 0.11 |

**1.703 bp の片道規約が 6.5% 狂えば D の net は消える。** net の t 値は 0.1 前後で、ゼロと区別できない。

## 4. 主検定の分解 — 事前登録した比と、それが測れていないもの

D = B − β·C なので、事前に「rate 脚（B）と momentum 脚（E）への分解」を登録していた。実行結果:

| 量 | 値 |
| --- | --- |
| D の年率 gross | +8.70% |
| rate 脚（B）の年率 gross | +5.66% |
| momentum 脚（E）の年率 gross | −0.25% |
| 突合ギャップ | +3.29% |
| **rate 脚が D の gross に占める「割合」** | **65.0%** |
| 帰属できていない残り | **37.8%** |
| β の平均 / 標準偏差 / 5–95%点 / 負の日の割合 | 0.38 / 0.47 / [−0.54, 0.93] / 22.7% |

**この 65.0% は P&L の配分ではない。** 理由は 2 つあり、どちらも実装の性質である:

1. `construction.capped_weights` は各サイドを固定合計に再正規化するので、**日次の正のスカラー倍に対して厳密に不変**。
   book E の score は `−β_t · C_t` だから、E を単独で回した時点で **|β_t| は捨てられている**。
   E は「D の中で β の大きさを持って効いている脚」ではなく、**`−sign(β_t)·C_t`** である（β が負の日は 22.7%）。
2. B・E・D はそれぞれ日次で正規化され、別々に vol target まで levered される。so **3 者の年率は加算的でない**。
   突合ギャップ 3.29% は「cap と band の近似誤差」ではなく、**この非加算性そのもの**である
   （平均 leverage の差 4.40 / 3.98 / 4.52 から来る一次の再スケールは 0.15pp 程度しか説明しない）。
   初稿は原因を cap と band に帰していた。訂正する。

条件は digest で凍結されているので**そのまま適用した**（結果を見てから別の量に差し替えるのは禁止された救済にあたる）。
そのうえで、**問いに実際に答えられる量**を併記する — D の日次 gross P&L が何と一緒に動くか、全決定日で直接測る:

| 相関 | 値 |
| --- | --- |
| D の日次 gross × rate 脚（B）の日次 gross | **+0.610** |
| D の日次 gross × momentum 脚（E）の日次 gross | **+0.017** |

通貨別でも同じ向きで、D（CAD −0.19、EUR +0.12、GBP −0.01、JPY +0.19、USD +0.30）は
B（−0.13、−0.07、−0.01、+0.20、+0.28）に追随し、E（+0.09、+0.11、−0.02、−0.04、−0.15）とは逆である。

**D の gross は momentum 脚が作ったものではない** — この結論は維持されるが、根拠は 65% の比ではなく上の相関である。
ただし β のばらつきは大きく（sd 0.47、22.7% の日で符号が反転）、D を「純粋な金利情報」と読むことはできない。

## 5. 持続性・安定性・集中

- signal の日次自己相関: B **0.898**（半減期 6.4 日）、D 0.826。今回再実行した A（fast）は 0.681（1.8 日）で、
  slow のほうが明確に持続する。
- position の自己相関: B 0.847（半減期 **4.2 日**）、D 0.717（2.1 日）。売買した日は B で 54.0%、D で 69.4%。
- block: B は 6 中 3 が正（+1.18, +0.88, +0.94 対 −0.28, −1.55, −0.98）、D は 4 / 6。
- **leave-one-currency-out は 5 通りすべて負**（D: without_EUR −0.09、without_GBP −0.12、without_CAD −0.49、
  without_USD −0.59、without_JPY −1.03）。条件は事前登録されており、落ちる。

  ただし**落ちた理由は「USD と JPY への集中」ではない**。5 通り全部が full sample の +0.051 より 0.14〜1.08 低い、
  という一様な水準低下であって、抜いた通貨への再配分ではない。実際 `without_CAD` は 2 番目に悪い（−0.49）が、
  CAD は D の中で唯一はっきり負の寄与（−0.19）で、損を出している名前を抜いて Sharpe が 0.54 下がるのは
  集中では説明できない。原因は universe closure のほうにある: 1 通貨を落とすと **routing 可能な pair 集合が変わり**、
  残る 4 通貨の**リターン定義そのものが変わる**。4 名の sum-zero・cap 0.25 の book は符号 book にほぼ等しくなり、
  cap が 5 名のときよりはるかに強く binding する（これは prereg 自身が指摘していた）。
  routed book として正しい検定だが、**5 名の結果の部分集合ではない**。
- 通貨別 gross: D は USD +0.30、JPY +0.19、EUR +0.12 対 CAD −0.19。
- 最大 DD: B −27.1%、D −36.9%。上位 5 日は net の 4.7〜6.0 倍（net がほぼ 0 なので比は意味を持たない）。

### IC — 唯一の直接的な予測力の測定は、情報を持っていない

事前の feasibility frame（net 0.3 に必要な日次 IC 対 実測 IC）を各 book に適用した:

| book | net 0.3 に必要な日次 IC（実測 turnover で） | 実測の日次換算 IC（20 日） |
| --- | --- | --- |
| B slow 20 日 state | 3.78% | **−2.07%** |
| D 残差（主検定） | 5.13% | **−1.25%** |

**金利系 book の Spearman IC は 5 日でも 20 日でも全て負**（B −4.38% / −4.01%、C −5.16% / −5.01%、D −2.12% / −1.57%）で、
凍結した符号 `+1` とも P&L とも逆向きである。一方 momentum 脚 E だけが正（+2.13% / +3.97%）。
5 名の順位相関を独立実効 63 観測程度で測っているので、これは **−0.6σ 程度、すなわち「反証」ではなく「無情報」**である。
しかし **正の gross は測定された予測力に支えられていない**ということでもある。
gross は順位相関ではなく、weight の大きさと cap・band・vol target の相互作用から出ている。
この事実は判定を変えないが、B を単独 formulation として扱う議論（§8.2）には直接効く。

## 6. leverage・margin・利益容量（#484 の枠組み、この universe で測る）

この book 自身の単位 gross あたり vol（実現 vol ÷ 平均通貨 gross = 0.0261）で測ると:

- 10% vol target: 平均 risk leverage **3.83**、margin 利用率は leverage tail で **23.4%**、gap stress 後の維持率 **1.44** で loss-cut に至らない。
- **年 5% は届かない**: net Sharpe 0.05 では必要 vol が **97.8%** になり、その leverage（risk leverage 平均 37.5、tail 59.3）は
  gap stress で margin 利用率 229%、維持率 −2.4 となって **loss-cut に至る**。

凍結した条件文は「5% 年率が、**その gap stress が loss-cut を強制しない target volatility で**到達可能か」である。
これは `risk.leverage_for_return(annual_target=0.05)` そのもので、答えは **`reachable: false`**。
**したがってこの条件は満たさない。**

初稿はこの条件を「10% target での gap stress が loss-cut しないこと」として実装しており、それは**別の、弱い述語**だった
（net Sharpe が 0.5 未満のとき両者は必ず食い違う — まさにこの screen が捕まえるべき領域である）。
record には `reachable: false` と条件 `true` が同時に載っていた。実装を凍結文どおりに直し、落ちる条件は 3 つではなく **4 つ**に改めた。
**凍結文の書き方に問題があったのではなく、実装が凍結文から外れていた。** 初稿は逆に帰していた。訂正する。

`deviations_from_the_frozen_text` を record に追加し、凍結文どおりには測れなかった 2 点（§4 の比と book E の定義）を明示した。

## 7. 判定と、その scope

**`MARKET_YIELD_SLOW_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`。**

意味するもの: **事前登録した 20 日 state の formulation が、この seen span で経済的に成立しなかった。**
turnover は下がり、**同じ gross を 4 割少ない売買で取れた**が、net は break-even 近傍（break-even cost 倍率 1.07）で、
cost 規約が 6.5% 狂えば消え、1 通貨を落とすと符号が消える。

意味しないもの:

- market-yield repricing family 全体の閉鎖。**fast と slow の両方が不支持**になったので、裁定 §20 の
  `MARKET_YIELD_REPRICING_SIMPLE_DIRECTIONAL_FAMILY_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` を**検討できる段階**には来たが、
  それは OIS・intraday rate futures・market-implied policy path・曲線の非線形性には**届かない**（いずれも未観測）。
- 「金利情報の内容が時間とともに劣化した」。示されたのはそれではない。**主検定の gross は落ちていない。**
  示されたのは、**想定した cost 水準で monetize できないこと**である。
- 「金利情報に予測内容が無い」。この span は 80% 検出力で net 1.13 未満を分離できない。D の gross +0.834（t ≈ 1.81）も、
  B の +0.541（t ≈ 1.18）も、**decision-grade ではない**。IC は無情報（§5）。

## 8. 次にやらないこと / Human に返すこと

やらないこと（事前登録の禁止事項）:

- horizon・符号・lookback・universe・control の変更、vol target や band や cost 規約による救済、非線形化・ML 化。
- turnover 上限 45 を結果後に緩めること。D は 59.8 で落ちたが、これは事前に置いた数値である。
- AUD・NZD・CHF を足せば救えるという議論（裁定 §11 で明示的に禁止）。

Human + ChatGPT に返す論点:

1. **family closure を宣言するか**。fast と slow の両方が不支持で、closure token は用意してある。ただし上記のとおり
   未観測の情報源（OIS、政策パスの市場織り込み、曲線）には届かない。closure を記録するなら、
   「情報が劣化した」ではなく「**この cost 水準で monetize できない**」という形で記録すべきである。
2. **B 単独（turnover 39.3、net +0.042、cost 5.22%）を別 formulation として扱うか**。今回の主検定は D であり、
   B は control なしの book なので、`FX price control を超える増分` の保証がない。
   併せて B の不利な側も置く: block は 6 中 3（−0.28, +1.18, +0.88, −1.55, −0.98, +0.94）、cost 1.5 倍で net −0.21、
   break-even cost 倍率 1.085、net t 0.09、leave-one-out は未計算。**私からは提案しない。**
3. **screen 条件の実装忠実性**。今回 1 条件が凍結文より弱く実装されていた（§6）。判定は変わらなかったが、
   record が凍結契約について偽の値を持っていた。同種の検出のため、test を artefact 読みから
   **コード実行**へ移し、13 個の mutation（horizon、符号、forward shift、turnover 上限、cost 倍率、
   分解閾値、脚の取り違え、条件の hardcode、book の脱落、記録漏れ）が全て落ちることを確認した。
