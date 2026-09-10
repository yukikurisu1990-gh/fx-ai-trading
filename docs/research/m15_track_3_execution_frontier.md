# Track 3 — オフライン実行フロンティア：結果

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Status: **`SIMULATED_EXECUTION_COST_BOUND_ESTABLISHED`** ·
**`OFFLINE_EXECUTION_FRONTIER_ESTIMATED`** ·
**`CLOCK_STRUCTURE_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER`** ·
**`CLOCK_STRUCTURE_TRACK_V1_WITHDRAWN_AFTER_UNIT_CORRECTION`** ·
**`LONDON_FIX_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER`**

事前登録は `docs/research/m15_track_3_execution_prereg.md`（英語、測定前に凍結）。
本文書は Human + ChatGPT の裁定に従い日本語で記す。成果物は
`artifacts/research/execution_frontier/replay.json` と同 `frontier.json`。
本文書の表の数値はすべて成果物と機械照合される
(`tests/research/test_execution_frontier_document.py`)。

---

## 0. 一行で

**passive 執行は、この 2 パネルで意味のあるコスト削減を与えられない。**
事前登録した規則では `C′/C = 1.2814 / 1.3223`（band **weak**）でコストは増える。
最も楽観的な約定仮定（1/20 pip の突き抜けで約定＝実質 touch）でも `0.8358 / 0.8621`
にしか届かず、事前登録した **material（≤0.70C）帯には到達しない**。

そして**どの執行水準でも decision-grade な clock cell は生まれない**。事前登録
policy で IR_max 1.5 以下の feasible cell は 0、コストが実際に下がる touch 較正
では**すべての IR 上限で 0**（コストが下がると hurdle も下がって powered を失う）。
feasible になったことのある clock cell は例外なく **N = 25**、committed な
60-event floor を一度も超えない。

---

## 1. Identity

| 項目 | 値 |
| --- | --- |
| PR #474（unit audit）merge SHA | `5231efe808e70d2eef87f2ebe25fef27b8251037` |
| 本作業のブランチ | `research/m15-track-3-execution-frontier` |
| 事前登録の凍結コミット | `e673a5d`（測定コード・成果物より前） |
| 対象パネル | `momentum_2021_2023`, `supplemental_2023_2025`（既読 2 枚のみ） |
| 実測 span | `2021-04-26 … 2023-04-25` / `2023-04-26 … 2025-04-24` |
| バー数 | 999,238 / 993,878（うち measurable 989,917 / 984,678） |
| 取引日 / 年数 | 521 / 518 日、いずれも 1.996 年 |

## 2. 事前登録の要点（測定前に凍結済み）

**コスト定義**は implementation shortfall。
`leg cost (bp) = direction × (fill price − decision mid) / decision mid × 1e4`。
「クオート spread の半分」ではない理由は、passive 注文は判断時点で約定しないから
で、spread だけを価格付けする指標は節約を計上して遅延を隠す。

**3 つの policy**。`P0` は即時クロス＝`C`。`P2` は near touch に指値を置き、未約定
ならクロス — **全判断が必ず約定する**ので同一母集団上の平均となり、これが `C′`
で帯を適用する対象。`P1` は指値を置いて取消 — 平均が「市場が寄って来た部分集合」
に条件付くため診断値であり帯の対象ではない。

**約定規則**（保守側に倒した項目のみ）: touch では約定しない（1 pip の突き抜けを
要求）／価格改善なし／判断したバー内では約定しない／バー内の順序が曖昧なら不約定
／セッション gap を跨いで待たない／部分約定なし／rollover 窓は主母集団から除外。
`WAIT_BARS = 4`、`PENETRATION_PIPS = 1.0`、感度軸は事前宣言。

**成功帯**: `C′ ≤ 0.60C` strong / `≤ 0.70C` material / `≤ 0.85C` modest /
それ以外 weak。2 パネルが割れたら**悪い方**が支配する。

**事前登録からの逸脱 1 件**: 事前登録 §6 は「4 つの session」（`clock.session_of`）
と書いたが、実装はデータに既にある 3 分割（`bars.SESSION_BOUNDS`：asia / europe /
us）を使った。24 時間の被覆は完全で欠落はないが、規定と実装が食い違っているので
記録する。

## 3. Baseline execution — `C`

market order を判断バーのクオートで即時執行した場合の往復コスト。片脚あたり
half spread ＋ pad 0.25 pip で、往復は既存プログラム全段が使ってきた
`spread + 0.5 pip` と一致する（この恒等式はテストで固定してある。ここが一致しな
ければ `C` は frontier の `C` ではなく、比を取る意味がない）。

`all_bars`（rollover 除外）での `C` は **2.6902 / 2.4660 bp**。

## 4. Simulated execution — `C′`、`C′/C`

### 4.1 主結果（primary rule `w4_p1`、rollover 除外）

| population | C bp | C′ bp | C′/C | fill rate | adverse bp |
| --- | --- | --- | --- | --- | --- |
| all_bars · momentum | 2.6902 | 3.4473 | 1.2814 | 0.7041 | 0.0095 |
| all_bars · supplemental | 2.4660 | 3.2609 | 1.3223 | 0.6745 | -0.0058 |
| non_event · momentum | 2.6599 | 3.4052 | 1.2802 | 0.7024 | 0.0062 |
| non_event · supplemental | 2.4370 | 3.2134 | 1.3186 | 0.6729 | -0.0082 |
| session_asia · momentum | 2.4198 | 3.3857 | 1.3992 | 0.7007 | 0.0146 |
| session_asia · supplemental | 2.2326 | 3.2330 | 1.4481 | 0.6753 | 0.0010 |
| session_europe · momentum | 2.3289 | 3.3936 | 1.4572 | 0.8024 | 0.0115 |
| session_europe · supplemental | 2.2390 | 3.1980 | 1.4283 | 0.7693 | -0.0012 |
| session_us · momentum | 3.3838 | 3.5736 | 1.0561 | 0.5999 | -0.0004 |
| session_us · supplemental | 2.9710 | 3.3606 | 1.1311 | 0.5697 | -0.0217 |
| rollover_window · momentum | 8.1292 | 4.1551 | 0.5111 | 0.2617 | -0.0338 |
| rollover_window · supplemental | 6.6005 | 3.6284 | 0.5497 | 0.2701 | -0.0499 |

**band = weak**（`C′ > 0.85C`）が rollover 以外のすべて。両パネルの `all_bars`
比の差は 0.0409 で、帯の判定は一致している。

**rollover だけが strong なのは passive が効いたからではない。** そこは baseline
自体が流動性の穴（8.13 / 6.60 bp、通常帯の 3 倍超）で、fill rate は 0.26–0.27
しかない。つまり `P2` はほぼ必ずクロスしており、安くなったのは **1 時間待って
スプレッドの尖りが消えてからクロスしたから**である。これは passive 執行の効果で
はなく待機の効果で、同じ利得は「その時間に建てない」だけで得られる。逆に
`rollover_pre`（尖りに向かって待つ側）は 2.096 / 2.485 と最悪の比になる。

### 4.2 事前宣言した感度軸（`all_bars`）

| rule | C bp | C′ bp | C′/C | fill rate | 4 バー窓に収まるか |
| --- | --- | --- | --- | --- | --- |
| w1_p1 · momentum | 2.6950 | 3.3508 | 1.2433 | 0.4849 | yes |
| w1_p1 · supplemental | 2.4679 | 3.0555 | 1.2381 | 0.4435 | yes |
| w2_p1 · momentum | 2.6928 | 3.4555 | 1.2832 | 0.6023 | yes |
| w2_p1 · supplemental | 2.4668 | 3.1900 | 1.2932 | 0.5657 | yes |
| w4_p0.5 · momentum | 2.6902 | 2.8279 | 1.0512 | 0.7459 | no |
| w4_p0.5 · supplemental | 2.4660 | 2.6845 | 1.0886 | 0.7219 | no |
| w4_p1 · momentum | 2.6902 | 3.4473 | 1.2814 | 0.7041 | no |
| w4_p1 · supplemental | 2.4660 | 3.2609 | 1.3223 | 0.6745 | no |
| w4_p2 · momentum | 2.6902 | 4.5067 | 1.6752 | 0.6241 | no |
| w4_p2 · supplemental | 2.4660 | 4.1911 | 1.6996 | 0.5859 | no |
| w8_p1 · momentum | 2.6884 | 3.4635 | 1.2883 | 0.7875 | no |
| w8_p1 · supplemental | 2.4668 | 3.3324 | 1.3509 | 0.7650 | no |

12 セルすべてが weak。

### 4.3 ⭐ 比の**符号**は市場ではなく約定規則が決めている（`POST_HOC_EXPLORATORY`）

初稿はここで「この結論は約定規則の保守性で作られたものではない」と書き、根拠に
「事前登録した最も緩い設定 0.5 pip でも 1.05」を挙げた。**レビューがこれを反証し、
私は自分で再現して確認した。** 事前登録した軸 `{0.5, 1.0, 2.0}` は比が 1.0 を
横切る点より**すべて上側**にあり、軸の構成上その事実を見せられなかった。

| rule | C bp | C′ bp | C′/C | fill rate |
| --- | --- | --- | --- | --- |
| w4_p0.05 · momentum | 2.6902 | 2.2485 | 0.8358 | 0.7824 |
| w4_p0.05 · supplemental | 2.4660 | 2.1259 | 0.8621 | 0.7647 |
| w4_p0.1 · momentum | 2.6902 | 2.2696 | 0.8437 | 0.7811 |
| w4_p0.1 · supplemental | 2.4660 | 2.1432 | 0.8691 | 0.7635 |
| w4_p0.25 · momentum | 2.6902 | 2.5353 | 0.9424 | 0.7646 |
| w4_p0.25 · supplemental | 2.4660 | 2.4055 | 0.9755 | 0.7438 |
| w4_p0.4 · momentum | 2.6902 | 2.7017 | 1.0043 | 0.7542 |
| w4_p0.4 · supplemental | 2.4660 | 2.5613 | 1.0386 | 0.7319 |
| w4_p0.75 · momentum | 2.6902 | 3.1961 | 1.1881 | 0.7215 |
| w4_p0.75 · supplemental | 2.4660 | 3.0331 | 1.2300 | 0.6938 |

比は **0.25 pip と 0.4 pip の間で 1.0 を横切る**（両パネル）。突き抜け要求は
queue position の代理変数であり、そこに置く値が符号を決めている。したがって
「passive はコストを上げる」は**市場の性質としては確立していない**。

**では何が確立したか。** 上表の最良点 0.8358 / 0.8621 は、1/20 pip の突き抜けで
約定を認める＝**queue の先頭に必ず並べると仮定**した場合の値である。リテール
口座がそれを前提にできる根拠はない。それでも到達するのは **modest 帯どまりで、
material（≤0.70C）には届かない**。つまり:

> この passive 族が与えうる削減の**上界**は、最も楽観的な約定仮定の下でも
> `C′ ≈ 0.84 C` であり、事前登録した material 帯に入らない。

### 4.4 ⭐ 無情報ベンチマーク（`POST_HOC_EXPLORATORY`）

同じ推定器を、情報を一切持たない martingale（バー内 300 分割、spread 2.5 pip、
σ 4.0 pip/バー、seed 20260911、24,000 バー、4 系列）に当てた。

| rule | C bp | C′ bp | C′/C | fill rate |
| --- | --- | --- | --- | --- |
| benchmark w4_p0.05 | 2.7340 | 2.6338 | 0.9634 | 0.7391 |
| benchmark w4_p0.25 | 2.7340 | 2.8959 | 1.0592 | 0.7199 |
| benchmark w4_p0.5 | 2.7340 | 3.2182 | 1.1771 | 0.6965 |
| benchmark w4_p1 | 2.7340 | 3.7782 | 1.3819 | 0.6510 |
| benchmark w4_p2 | 2.7340 | 4.6568 | 1.7033 | 0.5643 |

比の**水準**は無情報市場でも 0.96 → 1.70 と動く。つまり水準は機械的である。
実データはどの較正でもベンチマークより **約 0.10 だけ有利側**にあり（1.2814 /
1.3223 対 1.3819、0.8358 / 0.8621 対 0.9634）、その差は両パネル・全較正で符号が
一致する。**passive 執行に有利な実在の偏差はあるが、コストを賄う規模にはない。**

### 4.5 ペア別分布

pooled 値が 1 ペアの合成物である可能性は、両パネルで否定される。

| パネル | ペア数 | C′/C > 1.0 のペア | 最小 | 最大 | 中央値 |
| --- | --- | --- | --- | --- | --- |
| momentum | 20 | 19 | 0.990 | 1.577 | 1.258 |
| supplemental | 20 | 20 | 1.111 | 1.597 | 1.292 |

最小は両パネルとも `AUD_NZD`、最大は `AUD_USD` / `USD_JPY`。JPY 中央値
1.317 / 1.308、非 JPY 中央値 1.241 / 1.292。唯一 1.0 を下回った `AUD_NZD` は
他方のパネルで 1.111 であり、二枚で一致しない。

## 5. Adverse-selection diagnostics

### 5.1 ⭐ 初稿の「2.60 bp の逆選択」は推定器のアーティファクトだった

初稿は「約定した判断は 1 時間後にさらに 2.60 bp 逆行していた」と書いた。**これは
撤回する。** 当時の推定器は drift の終点を `index + offset + drift − 1` に置いて
おり、primary rule ではそれが**待機窓の最終バーそのもの**だった。約定は同じ窓の
安値で決まるので、「約定した」で条件付けてからその窓の終わりまでを測れば機械的に
負になる。レビューが無情報 random walk で同等の値を再現した。

修正版は**待機窓が閉じた後の 1 本目を基準点**にし、そこから 4 バーを測る。約定
判定が見られないバーだけを見る。基準点も窓の外に出す必要があった（窓の最終バーを
基準にすると、今度は符号が反転したアーティファクトが出る）。

| 量 | momentum | supplemental |
| --- | --- | --- |
| baseline leg cost bp | 1.3621 | 1.2490 |
| passive leg cost bp (`P2`) | 1.7315 | 1.6369 |
| conditional leg cost bp (`P1`, 約定分のみ) | -0.9715 | -0.9036 |
| capture bp（`P2` の対クロス節約） | -0.3694 | -0.3879 |
| 約定したときに節約した bp | 2.1742 | 2.0305 |
| 未約定で追いかけて払った bp | 6.4227 | 5.4004 |
| 窓の後の drift、全判断 bp | -0.0000 | 0.0000 |
| 窓の後の drift、約定した判断のみ bp | -0.0095 | 0.0058 |
| adverse selection bp | 0.0095 | -0.0058 |

**逆選択は測れない**（0.0095 / −0.0058 bp、しかも符号が 2 パネルで逆）。

### 5.2 では何が `C′ > C` を作っているのか

分解が答える。約定した 70.4% は 1 脚あたり **2.1742 bp** 節約し、未約定の 29.6%
は **6.4227 bp** 払って追いかけた。

    0.7041 × 2.1742 − 0.2959 × 6.4227 = −0.3696 bp ＝ capture の実測値

near touch の指値は**上限つきの利得と上限なしの損失を交換している**。約定すれば
利得は half spread で頭打ち、約定しなければ逃げた分をそのまま払う。fill rate 0.70
はその交換が有利であることを意味しない。そしてこれは §4.4 が示すとおり、無情報
市場でも同じ向きに起きる**構造的**な非対称であって、この 2 パネルの性質ではない。

`P1` の −0.97 bp は事前登録が名指しで帯から外した罠で、母集団が違う。

## 6. Limitations

* **`BROKER_REALIZABLE_COST_REDUCTION_ESTABLISHED` は主張しない。** M15 の
  bid/ask バーからは queue position、クオート引込み、latency、broker 固有の約定
  ロジック、hidden liquidity、部分約定が観測できない。到達できる最強の status は
  `SIMULATED_EXECUTION_COST_BOUND_ESTABLISHED`。
* **`C′/C > 1` は保守側の仮定と同じ向きである。** 初稿は逆のことを書いていたが、
  §4.3 のとおり突き抜け要求（＝queue 仮定）を緩めれば比は 1 を下回る。だから
  「保守的だから安心」とは言えない。言えるのは §4.3 の上界のほうで、そちらは
  最も楽観的な側から押さえている。
* **試したのは passive 設計空間の 1 点だけ。** near touch に置いて `W` バー後に
  クロスする族のみで、mid 指値、スプレッド内側への提示、分割執行、venue 選択は
  測っていない。
* **方向をランダムに引いていることは passive に有利な仮定である。** 実際の
  シグナルは方向を持つので、passive buy は「まず下がった」ときだけ約定する
  ——つまりシグナルが当たった取引ほど取り逃がす。
* **戦略の再シミュレーションではない。** リターンは設計自身の entry/exit バーから
  測り続けており、passive の約定は待機窓のどこかに落ちる。答えているのは
  フロンティアのコスト感度であって、passive clock 戦略の損益ではない。
* **`P2` の待機は clock 窓に収まらない。** clock 窓は 4 バー。4 バー待つ policy は
  窓の中で建玉を完了できない。収まるのは w1 と w2 だけで、§7 の表はその区別を持つ。
* **約定モデルが値付けできない pair-window がある。** 4,267–8,906 件（wait 依存）。
  frontier ではその pair をそのイベントから外す（0 で埋めない）ため、
  `calendar:1d` の N は 519 → 414（momentum）/ 517 → 410（supplemental）に落ちる。
  初稿はこれを 23,610–34,160 と書いたが、それは 1 window あたり 2〜4 回行われる
  leg 参照を数えていた。**§7 が `market` 対照群を持つ理由がここにある**：この脱落は
  policy ではなくサンプルの効果なので、対照群も同じ脱落を持たなければならない。
* **本 stage は seen data のみ。** fresh pool、historical OOS、dead window、
  forward epoch は未読。

## 7. Updated feasibility frontier

フロンティアは **unit audit と同一の列挙**を、cost source だけ差し替えて再計算した。
`quoted` を差し戻すと commit 済み unit-audit 成果物を **68 cell 全フィールド一致**で
再現する（両成果物を突き合わせるテストで固定）。

**`market_wN` 対照群**。初稿は「variant 間の差は執行に帰属する」と書いたが、
`quoted` は entry leg をそのバーの*終値*スプレッドで値付けし（開値 mid に適用）、
どのバーでも値付けできる。measured source はそのバーの実際の始値 bid/ask を使い、
約定モデルが届かないバーを拒否する。つまり `quoted → passive` の差には **policy
ではなくソースとサンプルの項**が混ざっている。`market_wN` は measured source で
**market order** を値付けするので、`passive_wN` と母集団・ソース・脱落が完全に
一致し、差は policy だけになる。

### 7.1 design-feasible cell 数（**signal survivor ではない**）

gate は unit audit のものから変えていない: powered（MDE ≤ 2×median C、**両パネル**）
／payable（break-even gross IR ≤ IR_max、**両パネル**）／two-panel。

| variant | 測定 cell 数 | IR_max 1.0 | IR_max 1.5 | IR_max 2.0 |
| --- | --- | --- | --- | --- |
| quoted | 34 | 0 | 1 | 1 |
| market_w1_p1 | 34 | 0 | 3 | 3 |
| market_w2_p1 | 34 | 0 | 3 | 3 |
| market_w4_p1 | 34 | 0 | 2 | 2 |
| market_w8_p1 | 34 | 0 | 2 | 2 |
| passive_w1_p1 | 34 | 0 | 0 | 2 |
| passive_w2_p1 | 34 | 0 | 0 | 1 |
| passive_w4_p1 | 34 | 0 | 0 | 0 |
| passive_w8_p1 | 34 | 0 | 0 | 0 |
| post_hoc_touch_w1_p0.05 | 34 | 0 | 0 | 0 |
| post_hoc_touch_w2_p0.05 | 34 | 0 | 0 | 0 |

**同一母集団での policy 比較**（`market_wN` → `passive_wN`、IR_max 1.5）:
**3 → 0**（w1, w2）、**2 → 0**（w4, w8）。passive はどの wait でも feasible cell を
全滅させる。

### 7.2 主要 cell の実行調整後の姿

| cell | variant | N | MDE bp | median C bp | mean C bp | hurdle bp | headroom bp | break-even IR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| london_open pre · month-end | quoted · momentum | 25 | 6.031 | 3.113 | 3.115 | 6.227 | 0.196 | 1.42 |
| london_open pre · month-end | quoted · supplemental | 25 | 5.874 | 2.980 | 3.017 | 5.960 | 0.086 | 1.36 |
| london_open pre · month-end | market_w1_p1 · momentum | 25 | 6.031 | 3.246 | 3.232 | 6.493 | 0.462 | 1.48 |
| london_open pre · month-end | market_w1_p1 · supplemental | 25 | 5.874 | 3.037 | 3.070 | 6.075 | 0.201 | 1.38 |
| london_open pre · month-end | passive_w1_p1 · momentum | 25 | 6.031 | 3.931 | 4.479 | 7.861 | 1.830 | 2.05 |
| london_open pre · month-end | passive_w1_p1 · supplemental | 25 | 5.874 | 4.096 | 4.517 | 8.191 | 2.318 | 2.03 |
| london_open pre · month-end | post_hoc_touch_w1_p0.05 · momentum | 25 | 6.031 | 2.456 | 3.114 | 4.912 | -1.119 | 1.42 |
| london_open pre · month-end | post_hoc_touch_w1_p0.05 · supplemental | 25 | 5.874 | 2.852 | 3.306 | 5.703 | -0.170 | 1.49 |
| london_fix pre · month-end | quoted · momentum | 25 | 14.745 | 2.925 | 2.924 | 5.850 | -8.895 | 0.59 |
| london_fix pre · month-end | quoted · supplemental | 25 | 10.484 | 2.886 | 2.906 | 5.772 | -4.713 | 0.82 |
| london_fix pre · month-end | post_hoc_touch_w1_p0.05 · momentum | 25 | 14.745 | 1.105 | 1.900 | 2.210 | -12.534 | 0.39 |
| london_fix pre · month-end | post_hoc_touch_w1_p0.05 · supplemental | 25 | 10.484 | 1.876 | 2.647 | 3.752 | -6.732 | 0.74 |
| calendar 1d | quoted · momentum | 519 | 5.275 | 3.418 | 4.406 | 6.835 | 1.560 | 2.08 |
| calendar 1d | quoted · supplemental | 517 | 4.536 | 3.176 | 3.799 | 6.352 | 1.816 | 2.04 |
| calendar 1d | market_w1_p1 · momentum | 414 | 5.865 | 3.342 | 3.401 | 6.684 | 0.819 | 1.46 |
| calendar 1d | market_w1_p1 · supplemental | 410 | 5.235 | 3.086 | 3.091 | 6.173 | 0.938 | 1.48 |
| calendar 1d | passive_w1_p1 · momentum | 414 | 5.865 | 3.664 | 4.182 | 7.328 | 1.462 | 1.79 |
| calendar 1d | passive_w1_p1 · supplemental | 410 | 5.235 | 3.639 | 4.138 | 7.279 | 2.044 | 1.98 |
| calendar 1d | post_hoc_touch_w1_p0.05 · momentum | 414 | 5.865 | 2.510 | 3.060 | 5.020 | -0.845 | 1.31 |
| calendar 1d | post_hoc_touch_w1_p0.05 · supplemental | 410 | 5.235 | 2.673 | 3.142 | 5.345 | 0.111 | 1.51 |

`calendar:1d` の `quoted → market` は **N が 519/517 → 414/410 に落ちる**サンプル
効果で、IR が 2.08 → 1.48 まで動く。これは執行の改善ではない。脱落したのは gap
隣接の高コスト期間である。**だから policy の比較は `market → passive` の行だけで
読むこと。**

### 7.3 ⭐ 「passive で feasible になった cell」は改善ではない

unit audit が発見した gate の逆転が実地に出た。`MDE ≤ 2 × median C` は
**設計が高くつくほど通りやすくなる**。`ny_option_cut pre · month-end` は quoted
でも market_w1 でも powered でない（headroom +0.013/−1.566、+0.099/−1.581）が、
passive_w1 では **+0.960/+0.356 で powered になる**。MDE は動いていない。
hurdle が上がっただけである。

### 7.4 ⭐ そして逆向きにも壊れる：**コストが下がると powered を失う**

これが本 stage の最も重要な構造的発見で、初稿には無かった。`powered` は
`MDE ≤ 2 × median C` なので、コストが**下がる**と hurdle も下がって落ちる。
`post_hoc_touch_w1_p0.05` はコストが実際に下がる唯一の variant だが、そこでは:

* `london_open pre · month-end` の headroom が **+0.462/+0.201 → −1.119/−0.170**
  （median C は 3.246/3.037 → 2.456/2.852 と確かに下がっている）
* `calendar 1d` の headroom が **+0.819/+0.938 → −0.845/+0.111**
* `london_fix pre · month-end` は median C が 3.169/3.079 → **1.105/1.876** まで
  下がるのに、MDE 14.745/10.484 に対して hurdle が 2.210/3.752 へ落ち、headroom は
  −8.406/−4.327 から **−12.534/−6.732** へ悪化する
* feasible cell は **すべての IR 上限で 0**

つまり **powered は cost の下限を、payable は cost の上限を与える**。両者は
コスト軸上の帯を定義しており、コストを下げれば帯から下に抜ける。unit audit が
「コスト半減で実行可能帯 4 倍」と書いたのは *events-per-year 軸*での話で、
**cell の頻度を固定したままコストだけ下げても、その cell は decidable にならない**。

したがって本 stage の裁定は「執行が改善しなかったから Case C」ではない。
**この 34 cell 列挙には、測定・模擬したどのコスト水準でも 3 gate を通る clock cell
が存在しない。** それが Case C の中身である。

### 7.5 60-event floor

committed な `MIN_EVENTS_PER_DECIDING_PANEL = 60` を超える feasible cell は、
**どの variant でも `calendar:1d` ただ 1 つ**（Track 1 の clock cell ではない）。
feasible になったことのある clock cell は例外なく **N = 25**。しかも
`london_open post · month-end` は market_w1/w2 で powered、market_w4/w8 で
not powered — policy は同じでサンプルだけが違う。**この規模では feasible 判定が
サンプル構成で反転する。**

## 8. Track 1 v1 status

**`CLOCK_STRUCTURE_TRACK_V1_WITHDRAWN_AFTER_UNIT_CORRECTION`**。
v1 の primary A/B/C は unit 修正で前提が失われており、本 stage はそれを回復しな
かった。ただし **clock / institutional-flow family 自体は closed ではない**。

## 9. Track 1 v2 feasibility — 裁定

事前登録 §9 の A/B/C ツリー（リポジトリ内で凍結済み。Human + ChatGPT 決定文書の
節番号はリポジトリ外なので、判定はこちらに対して行う）に照らす。

* **Case A は満たさない。** 「複数の economically meaningful な cell が 3 gate を
  満たす」状態は、事前登録 policy でも、コストが実際に下がる touch 較正でも
  生じない（いずれも IR_max 1.5 以下で 0）。
* **baseline 側で feasible に見える clock cell は N = 25 のみ**で、committed な
  60-event floor を超えず、サンプル構成で反転する（§7.5）。
* **Case B（1 個の marginal cell）でもない**：残るとしても floor 未満の cell であり、
  Human + ChatGPT の裁定 `MARGINAL_CELL_NOT_ROBUST_TO_EXECUTION_UNCERTAINTY` の
  対象そのもの。本測定はそれを独立に裏づけた——`london_open pre · month-end` の
  余裕 0.196/0.086 bp に対し、執行方式を現実的な代替に変えるだけで required IR が
  1.42 → 2.05 動く。
* **IR_max を結果を見て 2.0 に選ぶことはしない。** 事前登録は 3 つの上限すべてで
  報告することを定めており、cell を残すために上限を選ぶことは Human + ChatGPT が
  明示的に禁じている。

したがって **Case C**:
**`CLOCK_STRUCTURE_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER`**。
family を null 扱いにはしない。これは「十分な検出力で検定して edge が支持されな
かった」ではなく、**必要な効果を検出できる設計が存在しない**という research
infeasibility である。

## 10. London fix

`LONDON_FIX_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER`。
公表された根拠は最も強いが、月末 dispersion が大きく（MDE 14.745 / 10.484 に対し
hurdle 5.850 / 5.772）、どの variant でも powered にならない。「Track 3 でコストが
十分下がった場合のみ再評価」という条件は、下がらなかったので発火せず、しかも
§7.4 によりコストが下がっても powered には近づかない。これは null ではない。

## 11. Track 2 status

**待機**。prereg freeze、Stage 0、Stage 1 のいずれにも進んでいない。

## 12. M1 status

**未使用**。本 stage は既存 M15 キャッシュのみで完結した。M1 再集約は行っておらず、
必要も生じなかった。

## 13. Protected-data confirmation

読んでいない: fresh pool `2016-06-02 … 2021-04-25`、historical OOS slice、
dead window、forward Formal Confirmation epoch。有料データ取得なし（CME /
Databento を含む）。broker 認証、demo/paper/live 執行、実注文、production
デプロイのいずれも行っていない。`scripts/research/execution_frontier/` は archive
path を持たず、パネルは `round_a.panels` 経由でのみ読む。
