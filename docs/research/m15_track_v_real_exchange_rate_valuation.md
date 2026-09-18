# T-V — 実質為替 valuation development 結果（pre-2016 public data）

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

判定: **`REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT`**（裁定 §48 の Case C）

Human + ChatGPT 裁定（2026-09-18）§21–§34 の D-1 条件付き承認による。
事前登録 `scripts/research/valuation/prereg.py` は **FX を 1 観測も取得する前に**凍結・commit（`4e537a4`、digest で固定）。
そのあとに `acquire.py` を書き、取得した。順序が本 track の主張そのものである。

---

## 0. 保護 span の除外は「request の性質」である

裁定 §25 は、保護 span を含む full dataset を download してから local filter する方法を禁じている。
本 track は **request 側で除外**した:

- FX: ECB euro reference rates、`endPeriod=2016-06-01`（fresh pool 開始 `2016-06-02` の前日）。
- CPI: BIS long consumer prices、`endPeriod=2016-05`。
- `fx_url()` / `cpi_url()` は保護 span に届く bound を **ValueError で拒否**する（test 済み）。
- 取得後、各系列の最大観測日を保護開始日と照合し、届いていれば `ProtectedDataError` で**ファイルを残さず拒否**する。
  server が bound を無視しても通らない。
- この機構は **non-FX dataset のみ**（ECB yield curve、BIS CPI）で事前検証した。FX 観測は検証に 1 つも使っていない。

実際の取得結果: FX 7 系列 × 4,459 行（`1999-01-04 … 2016-06-01`）、CPI 8 系列 × 269 行（`1994-01 … 2016-05`）。
到達不能な source は 0。fresh pool・historical OOS・dead window・forward epoch は読んでいない。

**開示**: BIS API の形を確認する過程で、pre-registration より**前**に 2005–2006 年の日次 JPY/USD ファイルを 1 度取得し、
即座に削除した（header と title のみ表示、観測値は読まず・分析せず・保持せず）。span はどの保護窓の外だが、
順序が逆であったことは事実なので `sources.py` に記録してある。

## 1. 問いと、除外すべき対抗仮説

問い: **実質で自国史より割安な通貨は、その後の数か月で超過リターンを生むか。**

対抗仮説は market factor ではなく、もっと単純なものである — **名目の平均回帰**。
名目水準が長期平均から離れただけなら、それは価格統計であって物価水準を必要としない。
valuation の主張は「戻る先の均衡が相対物価とともに動く」ことなので、
**control book は名目乖離そのもの**で、**主検定は control を除去したあとに残るもの**（book C）である。

| 記号 | 定義 |
| --- | --- |
| `n_c` | 通貨 c 1 単位のユーロ建て価値の log（ECB は c/EUR 建てなので log rate の符号反転）、断面で demean |
| `pi_c` | `log CPI_c`（lag 済み）、断面で demean |
| `q_c` | `n_c + pi_c` — 名目が据え置きのまま物価が上がった通貨は実質で割高 |
| `a_c` | `q_c` の expanding mean（観測済みの月のみ、最低 **60 か月**） |
| `d_c` | `q_c − a_c`（正 = 割高） |
| signal | `−d_c` の断面 z-score |

**基準年は打ち消える。** CPI 指数の基準年は国ごとに違うので `log CPI_c` の水準は任意だが、
anchor は各通貨自身の expanding mean であり `d_c = q_c − a_c` は通貨ごとの定数を消す。
残るのは「その通貨自身の歴史からの相対物価の変化」で、それが仮説の対象そのものである。

## 2. 実行設定（すべて凍結済み）

- universe: AUD CAD CHF EUR GBP JPY NZD USD の 8 通貨。routing 可能な pair は **20 本すべて**（universe-closed）。
  identity check: 4,458 日すべてで残差 3.5e-18、欠損 pair 日 0。
- span: return panel `1999-01-05 … 2016-06-01`（4,458 日）、決定月 210。warm-up により**最初の建玉は 2003-12-31**、
  建玉のある決定月は 151、実質 **12.62 年**。
- CPI lag: 月 M の指数は **M+2 の月末**から。AU と NZ は四半期公表で、四半期値をそのまま carry forward（平滑しない）。
- cadence: **毎月末に決定、band 0.10 で月次 rebalance**。執行 layer は Track 1 の universe-closed 版、
  weight cap 0.25、vol target 10%、leverage 上限なし。
- cost: 荷重規約 1.703 bp/片道、**2 倍と 3 倍**でも stress（1999 年まで遡るので規約より spread は広かったはず）。
- 主 horizon: **3 か月 1 本**。robustness anchor は expanding median 1 本のみ、事前宣言済み。

## 3. 結果（1 回のみ実行）

| book | gross Sharpe | net Sharpe | 年率 gross | 年率 net | 年間 cost | turnover | 3 か月 IC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A 実質 valuation | +0.192 | +0.169 | +2.15% | +1.90% | **0.25%** | **2.01** | −2.35% |
| B 名目 control | +0.030 | +0.011 | +0.41% | +0.16% | 0.26% | 2.12 | +3.17% |
| **C 残差（主検定）** | **+0.179** | **+0.165** | +2.00% | +1.85% | **0.16%** | **1.29** | **−9.12%** |

### 3.1 設計どおりに効いた唯一のもの: cost

**この programme で初めて、cost が結論を壊さない book が出た。**

- turnover は **1.3〜2.1 回転/年**（事前上限 12、T-R2 の D は 59.8、fast は 98.8）。
- 年間 cost **0.16%**（T-R2 の D は 8.17%）。
- **break-even cost 倍率 12.9**（T-R2 の D は 1.07）。cost 規約が 13 倍狂っても net は正のまま。
- cost 2 倍で net +0.151、3 倍で +0.137。ほぼ無傷。
- 売買した日は年 14.7 日。決定は年 12 回なので、vol targeter の leverage 追随が足す売買は年 3 日程度にとどまる。

これは「低 turnover が本 source の経済的な強みである」という事前の主張が、**設計として実現した**ということである。
発見ではなく、設計に組み込んだものが期待どおり動いた。

### 3.2 それでも stop である理由

net Sharpe **+0.165** は marginal 帯（0.25）にも届かない。加えて 12 条件のうち **3 つ**が落ちる。

| 条件 | 結果 |
| --- | --- |
| A の gross Sharpe > 0 | **満たす**（+0.192） |
| C の gross と net がともに正 | **満たす**（+0.179 / +0.165） |
| C が B に対して正の net 増分 | **満たす**（+0.165 対 +0.011） |
| **割安 tercile から割高 tercile へ単調に減少** | **満たさない**（§3.3） |
| block の過半が正 | **満たす**（4 / 6） |
| 1 通貨が gross の半分を超えない | **満たす**（最大 CHF 29.8%） |
| **8 通貨のどれを落としても符号が残る** | **満たさない**（3 通り負: AUD −0.11、NZD −0.14、USD −0.20、CHF −0.31） |
| 最良 12 か月を除いても符号が残る | **満たす**（C のみ。A と B は落ちる） |
| turnover ≤ 12 | **満たす**（1.29） |
| cost 2 倍・3 倍でも net > 0 | **満たす**（+0.151 / +0.137） |
| robustness anchor（expanding median）で符号不変 | **満たす**（+0.154） |
| **年 5% が vol 15% 以下 かつ gap stress の内側で到達可能** | **満たさない**（必要 vol 30.3%、そこで loss-cut） |

→ **stop**。net が帯に届かない時点で、条件が全部通っていても stop である。

### 3.3 いちばん重要な所見 — 事前登録した経済的順序は、主検定には現れない

事前に「割安 tercile ほど先の超過リターンが高い」という**単調性**を条件に入れていた。3 か月先、1,176 観測:

| book | 割安 | 中位 | 割高 | 単調か |
| --- | --- | --- | --- | --- |
| A 実質 valuation | **+0.337%** | −0.195% | −0.214% | **○** |
| B 名目 control | **+0.366%** | −0.065% | −0.451% | **○** |
| **C 残差（主検定）** | −0.106% | −0.197% | **+0.455%** | **×（逆転）** |

読み方はひとつしかない。**予測された順序は、名目の平均回帰で説明できる部分に乗っている。**
A も B も単調で、しかも B のほうが割安–割高の開き（0.82pp）は A（0.55pp）より大きい。
control を除去したあとに残る部分 — つまり「物価水準を必要とする分」— は、**3 か月先で順序が逆転する**。
C の 3 か月 IC も **−9.12%** で、同じ向きを指している。

にもかかわらず C の book P&L は正（gross +0.179）で、B（+0.030）より高い。
**この 2 つは矛盾しない**が、意味するところは厳しい: **C の正の Sharpe は、事前登録した予測力の指標に支えられていない。**
book の P&L は cap・band・vol target・月次保有の相互作用を通ったもので、3 か月断面の順位相関ではない。
「実質 valuation が名目平均回帰を超えて効いた」という主張は、**この run からは支持されない**。

### 3.4 統計的な位置

この span（建玉 12.62 年）が 80% 検出力で分離できるのは net Sharpe **0.789** 以上。
C の +0.165（net t **0.59**）も A の +0.169（t 0.60）も、**ゼロと区別できない**。
したがって stop は「効かないことの証明」ではなく、**「この span では支持されなかった」**である。

## 4. leverage・margin・利益容量

C 自身の単位 gross あたり vol は 0.0317。

- 10% vol target: risk leverage 平均 **3.16**、leverage tail での margin 利用率 **17.9%**、gap stress 後の維持率 **3.57**。
  loss-cut に至らず、**broker 制約は binding しない**。
- **年 5% は届かない**: net Sharpe 0.165 では必要 vol が **30.3%** になり、
  凍結条件の上限 15% を超え、かつその leverage は gap stress で loss-cut に至る。

net が小さいので leverage は救済にならない（#484 の原則どおり）。

## 5. 開示する不足（結果の読み方に直接効く）

1. **本 book は spot-only であって、完全な currency excess return ではない。**
   凍結した data source は ECB reference rates と BIS consumer prices で、**どちらも金利を持たない**。
   freeze 後に金利 source を足すことはしていない（それは pre-registration の外側の選択になる）。
   方向は中立ではない: 実質で割安な通貨は概してインフレが速く金利も高いので、
   **carry の欠落は valuation book のリターンを過小評価する側に効く可能性が高い**。
   したがって「carry を入れれば通ったかもしれない」は否定できない。ただしそれは**別の事前登録**であって、本 run の救済ではない。
2. **CPI は vintage ではなく改訂後の系列である。** 8 か国を 1994 年まで遡る無料の vintage data は存在しない。
   決定の後に到着した改訂は当時知りえないので、この設計はその分だけ楽観側に偏る。
   今回は結果が negative なので、この偏りは結論を弱める方向には働いていない。
3. **AU と NZ は四半期公表**。四半期値を lag 付きで carry forward しており、月次国との情報鮮度は同じではない。

## 6. 判定と、その scope

**`REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT`。**

意味するもの: **事前登録した実質 valuation の formulation が、1999–2016 の public data で支持されなかった。**
具体的には、(a) net Sharpe が事前の帯に届かず、(b) 予測された経済的順序は名目平均回帰の側にあり、
主検定では逆転し、(c) 8 通貨のうち 3 つを落とすと符号が消える。

意味しないもの:

- **「実質為替 valuation に内容が無い」**。この span は net Sharpe 0.79 未満を分離できない。
  A book の tercile 単調性は予測どおりに出ており（割安 +0.34% 対 割高 −0.21%）、
  それが**名目からも出る**ことが、valuation 固有の寄与を否定しているだけである。
- **「低 turnover の source には価値が無い」**。むしろ逆のことが示された。
  この programme で初めて **cost が結論を決めない book** が得られた（break-even cost 倍率 12.9）。
  問題は cost ではなく **signal の内容**に移った。これは programme にとって新しい情報である。
- **carry を含めた valuation の否定**。§5.1 のとおり本 book は spot-only である。

## 7. 事前登録により禁止されること

- anchor・lag・horizon・cadence・符号・universe の変更。
- control や book や通貨の追加（**carry leg の追加もこれに含まれる**）。
- 別の vol target や cost 規約での再実行による経済性の救済。
- 非線形化・ML 化。
- 保護 span の読み取り、凍結した終端日を超える request。

## 8. Human + ChatGPT に返す論点

1. **carry を含めた再定式化を新規 pre-registration として認めるか。** 本 run の最大の構造的限界は spot-only であること。
   valuation と carry は相関するので、これは救済ではなく**別の仮説**である。無料 source（BIS policy rates 等）で組めるが、
   本 run のデータを見たあとの設計になるため、**seen-data 汚染を承知したうえでの判断**が要る。私からは提案しない。
2. **A book（実質 valuation 単独、tercile 単調、net +0.169、turnover 2.0、cost 0.25%）の扱い。**
   主検定は C であり、A は control を超える増分を保証しない。単独では「名目平均回帰と区別できない」。
3. **低 turnover 帯そのものの位置づけ。** T-R / T-R2 は cost で落ちたが、T-V は cost では落ちていない。
   次に探す source を「cost で落ちない帯」に絞るかどうかは programme の方針決定であり、この結果からは導けない。
