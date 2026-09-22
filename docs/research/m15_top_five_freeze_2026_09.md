# Top-Five 一括凍結（2026-09-20）

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Authority: `docs/governance/m15_adjudication_2026_09_19_and_09_20.md`
（2026-09-20 Human + ChatGPT 裁定 §8–§14、§20–§26、§41–§42）

**freeze digest: `28100ebedfea45765371585df5c4308fee261e2496a9798acca79c920158962c`**

> 旧 digest `29ba80d68a5462fe015a6f2566d3c0b63319d0549de7b9a4d34a890f2339b1ca` は
> **`SUPERSEDED_PRE_EXECUTION`** として保持。2026-09-21 裁定が T3 の符号を dual-hypothesis へ、
> leverage の解釈を三概念の分離と target-vol scenario へ、acquisition を承認済みへ改めた。
> **この差し替え時点でも alpha を 1 本も見ていない**ので、post-result rescue ではない。

**本文書を書いた時点で、5 本のうち alpha を 1 本も見ていない。** それが凍結の意味である。

## 初稿は独立レビューに通らなかった

本文書は初稿ではない。初稿を 2 つの独立ロール（economics / mechanism と data timing / leakage / governance）に通したところ、**実際に凍結を壊していた欠陥が 6 つ**出た。
いずれも alpha に依存しない — つまり**結果を見る前に直せるものだった**。

| # | 初稿の欠陥 | 直した内容 |
| --- | --- | --- |
| 1 | **lag の論証が逆向き**。「米国引け値が同じ日の欧州 fix を動かせない」は fix(t) が VIX(t) に汚染されていない証明であって、VIX(t) で fix(t) の建玉を決めてよい証明ではない。VIX close 22:15 CET は ECB fix 14:15 CET の**後**なので、1 日 lag は**8 時間の先読み** | 規約を「外部値は公表時刻より後に始まる return 窓にしか入れない」に置き換え、source ごとの公表時刻表を凍結 |
| 2 | **近 span 終端 2025-12-26 は金曜**で、その t+1 return は 2025-12-29 = OOS 初日。R1 の「window の 1 行先を decode した」事故と同型 | 最終 decision day を **2025-12-24** へ繰り上げ、「t+1 return が span 内に存在する最後の日」を規約化 |
| 3 | **digest が 4 定数を覆っていなかった** — `FORBIDDEN_RESCUES` / `NEGATIVE_CLASSES` / `NONLINEAR_ML` / `PROMOTION_REASONING`。**事後に最も緩めたくなるリストが digest の外**だった | 全公開定数を payload に入れ、**集合等価を test で固定**。`default=str` も外した |
| 4 | **T4 の rename gate が発火しえない**。1 日量と h 日 momentum の相関上限は `ρ/√h` で 5 日 0.36 / 20 日 0.18 / 60 日 0.10、閾値 0.8 に構造的に届かない | 比較対象を**自通貨 lag-1 残差と 1 日 own-return book** に差し替え。H-010（VR<1 で CLOSED）との符号衝突も明記 |
| 5 | **T2 の EIA は OLE2 バイナリ .xls** で、`xlrd`/`openpyxl` とも未導入。CSV 代替は存在しない | 依存追加が要ることを **Amber 変更として明示**。凍結文に data_caveat として記録 |
| 6 | **leverage 規約が無く、config 既定の `max_leverage=5.0` を使っていた** — 裁定が明示的に禁じた 5x hard cap | OANDA 公開 margin から **A=20x** を導き、A/B/C を分離 |

さらに: T2 の **NZD は原油の純輸入国**なのに beta が +0.5 で、宣言した機構を自分の beta が破っていた（→ −0.5）。T1 と T2 の beta 相関は **+0.856（R² 0.73）** で、T4 の rename 閾値 0.8 を超えている（→ T2 に T1 への incremental IC を義務化）。T3 の data 欄は **404 を返した系列名**を指していた（Umlaufsrendite → Zinsstruktur）。

**採用しなかった指摘が 1 つある。** レビューは「5 本とも現実的 leverage では年 5% net に届かない」と結論したが、その算術は `max_leverage=5.0` を前提にしていた。実際の broker 制約（20x）では年 5% に必要な net Sharpe は **0.429 ではなく 0.107** であり、net Sharpe 0.3 なら vol 16.7%・risk leverage 7.16x・margin 利用率 35.8% で届く。**禁じられた placeholder を前提にした結論なので、採用しない。**

---

## 0. この cycle が答えようとしている問い

勝者を作ることではない。

> G10 FX spot において、どの種類の information source に economic edge の兆候が残っているかを、
> 同一の development framework で一気に地図化する

したがって 5 本は互いに独立に事前固定され、**1 本目の結果を見てから 2 本目以降を調整しない**
（裁定 §10・§11）。1 本ずつ見て調整すれば、5 本は 5 つの独立な観測ではなく
1 本の長い探索になり、「どこに兆候があるか」には答えられなくなる — 答えは常に
「最後に調整した方向」になるからである。

これは confirmation ではなく **development candidate discovery / comparative screening**
である（裁定 §0）。

---

## 1. 選んだ 5 本

| | 候補 | 情報カテゴリ | mechanism | data（probe 済み） |
| --- | --- | --- | --- | --- |
| **T1** | **S05** | cross-asset information | 株式 volatility の repricing → funding / commodity 通貨 | CBOE VIX（200） |
| **T2** | **S06** | external macro-financial state | 原油 → 産出国の実質所得 | EIA WTI（200、**OLE2 .xls で依存追加が要る**） |
| **T3** | **S02** | rates（closure が届かない領域） | 金利 curve の**形状**（level ではない） | US / DE / CA / CH / GB（5 通貨、すべて 200） |
| **T4** | **S10** | currency-network propagation | 相手通貨の**残差**が 1 日遅れて伝播 | 既 seen の FX panel |
| **T5** | **S26** | flow / positioning proxy | 越境証券 flow → USD 需要 | TIC `s1_globl.csv`（200） |

**5 本のうち price 由来は T4 の 1 本だけ**である（裁定 §12）。
残り 4 本は FX の外から情報を持ち込む。

## 2. 実行しない候補 — 順位は保持する（裁定 §9）

| 候補 | 旧順位 | status | 理由 |
| --- | --- | --- | --- |
| **S07** credit spread | 3 | `DESIGN_ONLY_NOT_EXECUTED` | ICE 指数は FRED 経由しか無料 route が無く、承認済み probe は series page も root も **TIMEOUT**。**仮説は何も検定されていない**。2026-09-14 の記録は当該 series が 200 で配信されていることを示す — 閉じたのではなく届かない |
| **S25** 中銀 balance sheet | 5 | `DESIGN_ONLY_NOT_EXECUTED` | ECB 200 / SNB 200 だが **Fed H.4.1 に clean な無料 CSV endpoint が無い**（DDP は 400、HTML のみ 200）。**Fed 抜きの G10 中銀 balance sheet panel は仮説として成立しない** |
| S20 ほか有料 | — | `PAID_DATA_DESIGN_ONLY_NOTHING_PURCHASED` | 裁定 §15 により購入しない |

### なぜ S14 / S15 / S12 を繰り上げなかったか

順位だけを見れば S07・S25 の次は S14(7)・S15(8)・S12(9) である。しかし 3 つとも
price-only または conditioning であり、**H-023 / H-024 / H-003 という閉じた family に隣接**する。
凍結枠をそこに使えば rename を生みかねず、裁定 §6 がそれを禁じている。
また「5 本すべてが price momentum の変形にならないように」という §12 にも反する。

S26(10) は非価格の別情報集合で、data も probe 済みである。だからこれを繰り上げた。
**この判断は alpha を 1 つも見る前に行っている。**

---

## 3. 全 track 共通の枠組

| 項目 | 固定した内容 |
| --- | --- |
| universe | G10 8 通貨 `AUD CAD CHF EUR GBP JPY NZD USD`（T3 のみ 10y の取得可否で 5 通貨に限定、§4 参照） |
| 長 span | decision `1999-01-04 … 2016-05-31`、return は `fix(t)→fix(t+1)`、最終 return 日 `2016-06-01` |
| 近 span | decision `2021-04-27 … 2025-12-24`、return は UTC 日足 `close(t)→close(t+1)`、最終 return 日 `2025-12-26` |
| **lag** | **外部値は、その公表時刻より後に始まる return 窓にしか入れない。** source ごとに公表時刻を凍結（下表） |
| 執行層 | `continuous_portfolio.construction.run_book` を**数値ごと凍結**（band 0.10 / vol_target 0.10 / weight_cap 0.25 / sigma 60 / factor 120 / **max_leverage 20.0**） |
| leverage | **A / B / C を分離**（下記）。broker ceiling を hurdle にしない |
| cost | `CHARGED_ONE_WAY_BP` = 1.703 bp、stress ×1.5 / ×2。**判定は近 span のみ**（cost 規約が実測された唯一の span） |
| turnover | band law の値と **×1.90 補正値の両方**を凍結。実測が補正値を超えたら `B_cost_or_turnover_failure` |
| benchmark | zero signal ／ FX own momentum 20d ／ simple mean reversion 20d |
| control | FX 自身の価格情報を超える incremental IC。**T2 は T1 に対する incremental IC も必須** |
| Stage | Stage 1 は fixed / unfitted rule のみ。Stage 2 条件は事前凍結 |
| 非線形 ML | 本 cycle では training しない |

### 公表時刻と lag（推定ではなく publisher の仕様）

| source | 公表（CET） | 長 span lag | 近 span lag |
| --- | --- | --- | --- |
| CBOE VIX close | 22:15 | **2 営業日** | 1 営業日 |
| EIA WTI spot | **水曜サイクル**（日次公表ではない） | **7 営業日** | **7 営業日** |
| 各国 sovereign curve | 各国夕刻（US 21:30–24:00 ほか） | **2 営業日** | **2 営業日** |
| TIC 月次 | m+2 月中旬 | m+2 月末以降 | 同左 |
| FX 内部（T4） | 同一 panel | 1 営業日 | 1 営業日 |

**なぜ長 span で 2 日なのか。** ECB fix は 14:15 CET なので、`fix(t)→fix(t+1)` の建玉は
14:15 CET(t) に決まる。VIX close(22:15 CET) はその**後**なので、1 日 lag だと 8 時間の先読みになる。

### 保護境界

| 境界 | 値 |
| --- | --- |
| fresh pool 開始 | `2016-06-02` |
| development 終端 | `2025-12-28` |
| OOS slice 開始 | `2025-12-29` |

**最終 decision day は、その t+1 return が span の内側に存在する最後の日**とする。
近 span を 2025-12-26（金）で終えると t+1 が 2025-12-29 = OOS 初日になるため、2025-12-24 へ繰り上げた。

境界は **parsed date で比較**する（文字列比較はしない）。
VIX / EIA / SNB / TIC は期間パラメータを取らない全量配信 endpoint なので、
**取得後に parsed date で切り落としてから** panel に入れ、切り落とし前の frame を signal に触れさせない。

### Stage 2 へ進む条件（結果を見てから決めない）

**近 span で**次の 3 つすべてを満たしたときにのみ、事前登録した単純線形モデルへ自動的に進む。

1. `gross Sharpe > 0`
2. FX own momentum 20d に対する `incremental IC > 0`
3. 規約コストで `net annual return > 0`

満たさなければ **STOP**。モデルは 2 変数の単一線形回帰のみ。

**同じ規則でも track ごとに厳しさが違う** — cost drag が違うので、低 turnover の track は
ノイズでも通りやすい。Stage 2 へ自動進行した事実を報告するときは、**その track の帰無通過確率を必ず添える**。

### leverage は 3 概念に分ける — どちらの誤りも犯さない

| | 概念 | 値 | 意味 |
| --- | --- | --- | --- |
| **A** | broker hard leverage / margin ceiling | **20x**（OANDA 公開 margin の最悪値 0.05） | **margin 上の absolute ceiling**。それ以上でも以下でもない |
| **B** | portfolio gross leverage | 毎日記録 | book が実際に建てた gross |
| **C** | risk leverage / target-vol scaling | target vol ÷ 0.023288 | **運用の risk budget はここで決まる** |

**A が意味しないこと**: 20x の risk scaling が安全だということ／Sharpe 0.1 でも 20x 掛ければ
有望だということ／年 5% capacity が実用的だということ。

**禁じられている読み方は両方向ある:**

- ❌「5x を超えるから不可」
- ❌「20x まで可能だから Sharpe 0.107 で十分」

**正しい問い**: candidate の**実測** net Sharpe と volatility から、
realistic な target risk で年間 return へ変換できるか。
**alpha を見る前に固定倍率だけで否定も肯定もしない。**

`max_leverage = 20.0` を config に置いてあるが、**これは binding しない** —
vol_target 0.10 なら必要 leverage は 4.29x、最も高い scenario 15% でも 6.44x である。
cap を ceiling の位置に置いたのは、**risk は vol targeting が決める**という構造を明示するためである。

### 標準 target-vol scenario

positive / marginal candidate は **8% / 10% / 12% / 15%** で評価する。
それより高い vol は stress scenario としてのみ扱う。

net-positive candidate については、**年 5% / 年 10% net** に必要な
target vol・risk leverage・portfolio gross・pair 別 margin 利用率・DD・gap stress・
残 margin buffer を算出する。

### 長 span の excess panel

`CARRY_LEG_ABSENT_ON_THE_LONG_SPAN` — ECB reference rate から作る spot return には carry leg が無い。
**T3 は金利の signal を、金利 carry を落とした panel の上で測る**ことになる（脱落変数が signal と相関する）。
この欠落込みで読み、**carry を後から足さない**。

---

## 4. 各 track の凍結内容

### T1 / S05 — cross-asset risk repricing

- **signal**: `z` = 5 日 `log(VIX)` 変化を 252 日で標準化（day t までの行のみ）
- **direction**: `mu = z × beta`、
  `beta = {JPY +1, CHF +1, USD +0.5, EUR 0, GBP 0, CAD −0.5, AUD −1, NZD −1}`
- **turnover**: band law 43.4 ／ 補正 82.5 RT/年
- **breadth 2.0**（`candidates.py` の「実効 2（risk 軸 1 本）」に合わせた。初稿の 2.5 は根拠なき上方修正）
- **data caveat**: 1990–2003 の VIX は 2003 年の新方式による**遡及計算**で、長 span 前半は実時間に存在しなかった値
- **弱点**: USD +0.5 は dollar smile が支配的になる 2008 年以降の性質で長 span 前半では成立しない。
  EUR 0 は numeraire 軸かつ regime 依存の正直な棄権

### T2 / S06 — commodity terms of trade

- **signal**: `z` = 5 日 `log(WTI)` return を 252 日で標準化
- **direction**: `beta = {CAD +1, AUD +0.5, NZD −0.5, USD 0, GBP 0, EUR −0.5, CHF −0.25, JPY −1}`
  - **初稿からの修正**: NZD は原油の**純輸入国**（輸出は乳製品・食肉・木材）なので +0.5 → **−0.5**。
    豪州の輸出は鉄鉱石・石炭・LNG で原油ではないので +1.0 → **+0.5**。石油輸入強度に照らして CHF −0.5 → **−0.25**
- **turnover**: band law 43.4 ／ 補正 82.5 RT/年
- **cross-track control**: **T1 の signal に対する incremental IC も報告する**（beta 相関 +0.856）
- **data caveat**: **OLE2 バイナリ .xls** で、読むには `xlrd` 追加という **Amber 変更**が要る
- **弱点**: 実効 breadth 1.5 で最も狭い。USD 0 は近 span では誤り（米国は石油の純輸出国）だが長 span では正しい

### T3 / S02 — sovereign curve shape

- **universe**: **USD / EUR / CAD / CHF / GBP の 5 通貨**。JPY・AUD・NZD は 10y が取れず**除外を今ここで固定**
  （JGB 404、RBA・RBNZ 403）。Stage 0 で取れても**加えない** — 凍結後の cross-section 変更は設計変更である
- **data**: US Treasury ／ Bundesbank **Zinsstruktur 10 年**（初稿が書いていた Umlaufsrendite は 404 だった）／
  BoC Valet ／ SNB rendoblid ／ BoE。2y は取得済み
- **signal**: `slope = 10y − 2y` の 20 日変化を 5 通貨 cross-section で rank して中心化

#### 符号は 1 つに決めない — 両方を事前登録する

実行前レビューで **economic sign が理論的に曖昧**と判明したため、旧 freeze の
「steepening → 通貨高」を primary として実行**しない**。代わりに次の 2 つを
**両方 prespecified sub-hypothesis** として凍結する。

| id | 仮説 |
| --- | --- |
| **T3-H1** | steepening → subsequent currency **appreciation** |
| **T3-H2** | steepening → subsequent currency **depreciation** |

**報告規則:**

- **H1 と H2 を両方報告する。** 結果を見て良かった符号だけを primary 扱いしない
- 「どちらかが positive だったから curve theory が支持された」という主張は**禁止**
- **sign multiplicity を明示する** — T3 は 2 通りの探索である

**なぜ曖昧なのか。** curve steepening は単一 mechanism ではない:
bull steepening / bear steepening / policy easing expectations /
inflation–growth repricing / term-premium change / fiscal-risk premium
で符号が異なりうる。**これらを結果後に分類して最適化しない。**
まず凍結済みの simple curve-shape hypothesis を評価する。

- **rename gate**: Δ10y-only book と (−Δ2y)-only book を併走させ、T3 の日次 P&L が後者と
  `|corr| > 0.8` なら「**閉じた T-R2 の反転**」と判定して結果を採らない
- **turnover**: band law 18.3 ／ 補正 34.8 RT/年（5 本で最小）
- **breadth 1.5**（5 通貨 sum-zero の自由度 4、dollar factor 除去後の実効）

### T4 / S10 — currency-network propagation

- **signal**: (1) **trailing** 120 日窓の leading factor を除いて残差を得る（centered 窓は使わない）
  (2) 通貨 `i` について trailing 252 日窓で残差相関が最大の相手 `j` を選ぶ
  (3) `mu_i(t) = 残差_j(t)`
- **direction**: 正の伝播（反転版は事後に試さない）
- **rename gate（初稿から差し替え）**:
  初稿は 5/20/60 日 momentum との相関に閾値 0.8 を置いていたが、1 日量と h 日 momentum の相関上限は
  `ρ/√h` で **5 日 0.36 / 20 日 0.18 / 60 日 0.10**。**閾値に構造的に届かない gate だった。**
  比較対象を **(i) 自通貨の lag-1 残差 `res_i(t)`、(ii) 1 日 own-return book の日次 P&L** に差し替え、
  どちらかで `|corr| > 0.8` なら RENAME と判定する。
  相手 `j` は残差相関が最大の通貨として選ばれるので `corr(mu_i, res_i)` は定義上その最大相関に等しく、
  G10 の 1 factor 除去後で EUR/CHF や AUD/NZD は 0.6–0.8 に達しうる — **そこを測るのが正しい gate**
- **H-010 との衝突**: H-010 は残差の 1 日構造を **VR < 1（平均回帰）で CLOSED** と記録しており、
  T4 は**符号が逆**である。正の伝播を選ぶ理由は、H-010 が測ったのは *自分自身* の系列相関で、
  T4 が賭けるのは *他通貨への* 伝播だからである。**この区別が薄ければ T4 は H-010 の裏返し**になり、
  gate (i) がそこを捕まえる
- **turnover**: band law 100.8 ／ 補正 **191.5** RT/年。**gate を通っても cost で落ちる公算が高い**ことは実行前に分かっている

### T5 / S26 — international capital flow (TIC)

- **signal**: S-1 の **全世界計・長期証券の net foreign purchases of US securities** 行の 12 か月 z-score。
  **行と集計を今ここで固定する** — gross でも domestic/foreign 別でも国別でもない
- **vintage**: 第 `m` 月の値は `m+2` 月末以降にしか使わない。ただし配信ファイルは**改訂後の値**なので
  `NOT_THE_VINTAGE_AVAILABLE_AT_DECISION_TIME` が残る
- **direction**: `mu_USD = +z`、他 7 通貨は `−z/7`
- **執行層の逸脱（開示済み）**: T5 のみ `neutralize_leading_factor=False`。
  **T5 の mu は正規化すれば dollar factor そのもの**で、層が除く PC1 は G10 panel では dollar factor である。
  既定のままだと**層が仮説を消す**ので、null が「flow に情報が無い」のか「層が消した」のか区別できない
- **rename gate**: 使用可能になる時点で 2–3 か月前の flow なので、**「2 か月ラグの USD momentum」と
  ほぼ同じになりうる**。TIC z と 1/2/3 か月ラグの USD basket return の相関を報告し、
  いずれかで `|corr| > 0.8` なら RENAME と判定する
- **denomination caveat**: TIC の net purchase は USD 建てなので、z-score は買われた資産の
  USD 価格水準の z-score を部分的に含む
- **turnover**: band law 5.1 ／ 補正 9.7 RT/年
- **breadth 1.0**（USD 1 軸）

---


## 5. 実行と停止の規律

- 実行順は **T1 → T2 → T3 → T4 → T5**。ただし**前 track の結果を後 track の設計に反映しない**（§41）
- **T1 が negative でも T2 へ進む**（§42）。5 本は既に凍結済みなので、途中結果で cycle を止めない
- 例外は共通基盤の blocker のみ（data leakage / execution bug / protected-data violation /
  shared methodology defect）。その場合は実行停止 → 修正 → 影響範囲特定 → 既実行 track の
  結果無効化要否判定 → reviewer 確認（§43）。**結果を都合よく保持しない**
- **5 本終了後は STOP。6 本目へ進まない**（§60・§64）

### 判定の目安（統計的有意性の規則ではなく economic な解釈・§29）

| net Sharpe | 解釈 |
| --- | --- |
| ≤ 0 | negative |
| 0–0.2 | weak |
| 0.2–0.5 | marginal / potentially useful（安定性と cost 次第） |
| 0.5–0.8 | meaningful development candidate |
| > 0.8 | strong development candidate |

**「5 本の中で最大だった」「p < 0.05 だった」「Sharpe が一番高かった」だけでは昇格しない**（§32）。

### negative は 4 つに分ける（§31）

`A signal content` / `B cost・turnover` / `C data・power` / `D concentration`。
「failed」で一括りにしない。

### 結果を見た後の救済は禁止（§52）

符号反転・horizon 調整・閾値最適化・通貨除外・feature 追加・band 最適化・
leverage 最適化・非線形救済 — いずれも行わない。

---

## 6. この凍結が主張していないこと

- **どれかが当たるとは言っていない。** 5 本とも negative でありうるし、それは正当な結果である
- **検出力は足りない。** #489 が確定したとおり、到達可能などの span も現実的な 0.2–0.5 の
  edge を 0 と分離できない。**だが development screening はそれで禁止されない**
  （`UNDERPOWERED_FOR_CONFIRMATORY_CLAIM_DOES_NOT_FORBID_DEVELOPMENT`）
- **confirmation ではない。** fresh / OOS / dead / forward epoch へは進まない
- **S07・S25 を否定していない。** 取得できないだけで、仮説は検定されていない
