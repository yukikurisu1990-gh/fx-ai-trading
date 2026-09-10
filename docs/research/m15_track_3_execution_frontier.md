# Track 3 — オフライン実行フロンティア：結果

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Status: **`SIMULATED_EXECUTION_COST_BOUND_ESTABLISHED`** ·
**`OFFLINE_EXECUTION_FRONTIER_ESTIMATED`** ·
**`CLOCK_STRUCTURE_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER`** ·
**`CLOCK_STRUCTURE_TRACK_V1_WITHDRAWN_AFTER_UNIT_CORRECTION`**

事前登録は `docs/research/m15_track_3_execution_prereg.md`（英語、測定前に凍結）。
本文書は Human + ChatGPT の裁定に従い日本語で記す。成果物は
`artifacts/research/execution_frontier/replay.json` と同 `frontier.json`。
本文書の表の数値はすべて成果物と機械照合される
(`tests/research/test_execution_frontier_document.py`)。

---

## 0. 一行で

**passive 執行はコストを下げなかった。上げた。** 保守的な約定モデルの下で
`C′/C = 1.281 / 1.322`（2 パネル）、事前登録した帯では両パネルとも **weak**。
事前登録した感度セル 6 個すべてが weak で、最良でも 1.051。
その結果、実行調整後のフロンティアでは **IR_max = 1.5 以下で feasible な cell は
ゼロ**（quoted では 1 個あった）。

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
なら クロス — **全判断が必ず約定する**ので同一母集団上の平均となり、これが `C′`
で帯を適用する対象。`P1` は指値を置いて取消 — 平均が「市場が寄って来た部分集合」
に条件付くため診断値であり帯の対象ではない。

**約定規則**（保守側に倒した項目のみ）: touch では約定しない（1 pip の突き抜けを
要求）／価格改善なし／判断したバー内では約定しない／バー内の順序が曖昧なら不約定
／セッション gap を跨いで待たない／部分約定なし／rollover 窓は主母集団から除外。
`WAIT_BARS = 4`、`PENETRATION_PIPS = 1.0`、感度軸は事前宣言。

**成功帯**: `C′ ≤ 0.60C` strong / `≤ 0.70C` material / `≤ 0.85C` modest /
それ以外 weak。2 パネルが割れたら**悪い方**が支配する。

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
| all_bars · momentum | 2.6902 | 3.4473 | 1.2814 | 0.7041 | 2.6049 |
| all_bars · supplemental | 2.4660 | 3.2609 | 1.3223 | 0.6745 | 2.5423 |
| non_event · momentum | 2.6599 | 3.4052 | 1.2802 | 0.7024 | 2.6145 |
| non_event · supplemental | 2.4370 | 3.2134 | 1.3186 | 0.6729 | 2.5480 |
| session_asia · momentum | 2.4198 | 3.3857 | 1.3992 | 0.7007 | 2.8087 |
| session_asia · supplemental | 2.2326 | 3.2330 | 1.4481 | 0.6753 | 2.7162 |
| session_europe · momentum | 2.3289 | 3.3936 | 1.4572 | 0.8024 | 2.7033 |
| session_europe · supplemental | 2.2390 | 3.1980 | 1.4283 | 0.7693 | 2.5753 |
| session_us · momentum | 3.3838 | 3.5736 | 1.0561 | 0.5999 | 2.2939 |
| session_us · supplemental | 2.9710 | 3.3606 | 1.1311 | 0.5697 | 2.3407 |
| rollover_window · momentum | 8.1292 | 4.1551 | 0.5111 | 0.2617 | 4.2181 |
| rollover_window · supplemental | 6.6005 | 3.6284 | 0.5497 | 0.2701 | 3.9858 |

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

**12 セルすべてが weak。** 重要なのは、この結論が約定規則の保守性で作られたもの
では**ない**ということ。突き抜け要求を半分（0.5 pip）まで緩めても比は 1.051 /
1.089 で、依然として 1.0 を超える。突き抜け要求はコストの単調な増加要因
（0.5 → 1.0 → 2.0 pip で 1.051 → 1.281 → 1.675）だが、**最も緩い設定でも
passive はクロスに負ける**。

### 4.3 ペア別分布

pooled 値が 1 ペアの合成物である可能性は、両パネルで否定される。

| パネル | ペア数 | C′/C > 1.0 のペア | 最小 | 最大 | 中央値 |
| --- | --- | --- | --- | --- | --- |
| momentum | 20 | 19 | 0.990 (AUD_NZD) | 1.577 (AUD_USD) | 1.258 |
| supplemental | 20 | 20 | 1.111 (AUD_NZD) | 1.597 (USD_JPY) | 1.292 |

JPY 中央値 1.317 / 1.308、非 JPY 中央値 1.241 / 1.292。ブロック分解でも符号は
変わらない。唯一 1.0 を下回った `AUD_NZD` は他方のパネルで 1.111 であり、二枚で
一致しない。

## 5. Adverse-selection diagnostics

なぜ 70% の約定率で half spread を稼ぎながら往復が高くつくのか。三つの drift を
別々に測ると分かる（`all_bars`、entry leg、両方向 pooled）。

| 量 | momentum | supplemental |
| --- | --- | --- |
| baseline leg cost bp | 1.3621 | 1.2490 |
| passive leg cost bp (`P2`) | 1.7315 | 1.6369 |
| conditional leg cost bp (`P1`, 約定分のみ) | −0.9715 | −0.9036 |
| capture bp（`P2` の対クロス節約） | −0.3694 | −0.3879 |
| drift after a market order bp | −1.3618 | −1.2493 |
| drift after a market order, **約定した判断のみ** bp | −3.9667 | −3.7916 |
| adverse selection bp | 2.6049 | 2.5423 |

読み方は 2 段階ある。

1. **`P1` の −0.97 bp は「執行コストがマイナス」ではない。** これは市場が寄って
   来た部分集合の平均で、母集団が違う。事前登録がこれを帯の対象から外していた
   理由がそのまま出ている。同じデータで `P2` は **+1.73 bp**（baseline +1.36）。
2. **選択の大きさは執行モデルを固定して母集団だけ変えれば測れる。** market order
   の drift は全判断で −1.36 bp、**passive が約定した判断に限ると −3.97 bp**。
   差の **2.60 bp** が選択そのもの。約定した 70% は「1 時間後にさらに 2.6 bp 逆行
   した」判断であり、稼いだ half spread（約 1.3 bp）を上回る。

構造的に言えば、near touch の指値は **上限つきの利得と上限なしの損失を交換する
オプションを売っている**。約定すれば利得は half spread で頭打ちになり、約定しな
ければ逃げた分をそのまま払う。fill rate 0.70 はその交換が有利であることを意味
しない。

## 6. Limitations（`C′` を broker-realizable と読んではならない理由）

* **`BROKER_REALIZABLE_COST_REDUCTION_ESTABLISHED` は主張しない。** M15 の
  bid/ask バーからは queue position、クオート引込み、latency、broker 固有の約定
  ロジック、hidden liquidity、部分約定が観測できない。到達できる最強の status は
  `SIMULATED_EXECUTION_COST_BOUND_ESTABLISHED`。
* **本結果の符号は保守側の仮定と同方向ではない。** 上記の未観測要因はいずれも
  passive 執行を*悪く*する方向に働くので、`C′/C > 1` という結論は仮定を緩めても
  救われにくい。逆に言えば、`C′/C < 1` を得るには本モデルより*楽観的*な仮定が要る。
* **戦略の再シミュレーションではない。** リターンは設計自身の entry/exit バーから
  測り続けており、passive の約定は待機窓のどこかに落ちる。答えているのは
  「往復が `C′` だったとき、どの cell が判定可能か」というフロンティアのコスト感度
  であって、passive clock 戦略が何を稼いだかではない。
* **`P2` の待機は clock 窓に収まらない。** clock 窓は 4 バー。4 バー待つ policy は
  窓の中で建玉を完了できないので、primary rule は clock cell が使える規則ではない。
  収まるのは w1 と w2 だけで、これは事前に宣言してあり §7 の表もその区別を持つ。
* **約定モデルが値付けできない pair-window がある。** gap 隣接やパネル端で
  23,610–34,160 件。frontier ではその pair をそのイベントから外す（0 で埋めない）
  ため、`calendar:1d` の N は 519 → 414（momentum）/ 517 → 410（supplemental）に
  落ちる。これは MDE を上げる方向で、`C′` 側に不利ではなく有利に働き得るので、
  下の結論はその点でも保守的ではない。
* **試したのは passive 設計空間の 1 点だけ。** near touch に置いて `W` バー後に
  クロスする族のみで、mid 指値、スプレッド内側への提示、分割執行、venue 選択は
  測っていない。「passive 執行一般が無効」ではなく「この族はこの 2 パネルでは
  無効」が言えることの全部である。
* **方向をランダムに引いていることは passive に有利な仮定である。** 実際の
  シグナルは方向を持つので、passive buy は「まず下がった」ときだけ約定する
  ——つまりシグナルが当たった取引ほど取り逃がす。signal-free の本測定はその
  逆選択を含んでいないので、実戦の `C′/C` は本結果より悪くなりこそすれ良くは
  ならない。
* **本 stage は seen data のみ。** fresh pool、historical OOS、dead window、
  forward epoch は未読。

## 7. Updated feasibility frontier

フロンティアは **unit audit と同一の列挙**を、cost source だけ差し替えて再計算した。
`quoted` を差し戻したとき、commit 済みの unit-audit 成果物と全 cell・両パネルで
**フィールド不一致 0** を確認している（テストで固定）。したがって variant 間の差は
執行に帰属する。

### 7.1 design-feasible cell 数（**signal survivor ではない**）

gate は unit audit のものから変えていない: powered（MDE ≤ 2×median C、**両パネル**）
／payable（break-even gross IR ≤ IR_max、**両パネル**）／two-panel。

| variant | 測定 cell 数 | IR_max 1.0 | IR_max 1.5 | IR_max 2.0 | 4 バー窓に収まるか |
| --- | --- | --- | --- | --- | --- |
| quoted | 34 | 0 | 1 | 1 | — |
| passive_w1_p1 | 34 | 0 | 0 | 2 | yes |
| passive_w2_p1 | 34 | 0 | 0 | 1 | yes |
| passive_w4_p1 | 34 | 0 | 0 | 0 | no |
| passive_w8_p1 | 34 | 0 | 0 | 0 | no |

quoted の 1 個は `clock:london_open_pre__month_end`（unit audit の唯一の生存者を
そのまま再現）。passive_w1 の 2 個は `calendar:1d` と
`clock:ny_option_cut_pre__month_end`、passive_w2 の 1 個は後者のみ。

### 7.2 主要 cell の実行調整後の姿

| cell | variant | N | MDE bp | median C bp | mean C bp | hurdle bp | headroom bp | break-even IR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| london_open pre · month-end | quoted · momentum | 25 | 6.031 | 3.113 | 3.115 | 6.227 | 0.196 | 1.42 |
| london_open pre · month-end | quoted · supplemental | 25 | 5.874 | 2.980 | 3.017 | 5.960 | 0.086 | 1.36 |
| london_open pre · month-end | passive_w1_p1 · momentum | 25 | 6.031 | 3.931 | 4.479 | 7.861 | 1.830 | 2.05 |
| london_open pre · month-end | passive_w1_p1 · supplemental | 25 | 5.874 | 4.096 | 4.517 | 8.191 | 2.318 | 2.03 |
| ny_option_cut pre · month-end | quoted · momentum | 25 | 6.319 | 3.166 | 3.241 | 6.331 | 0.013 | 1.4 |
| ny_option_cut pre · month-end | quoted · supplemental | 25 | 7.956 | 3.195 | 3.264 | 6.390 | −1.566 | 1.22 |
| ny_option_cut pre · month-end | passive_w1_p1 · momentum | 25 | 6.319 | 3.639 | 4.311 | 7.279 | 0.960 | 1.87 |
| ny_option_cut pre · month-end | passive_w1_p1 · supplemental | 25 | 7.956 | 4.156 | 4.766 | 8.312 | 0.356 | 1.78 |
| london_fix pre · month-end | quoted · momentum | 25 | 14.745 | 2.925 | 2.924 | 5.850 | −8.895 | 0.59 |
| london_fix pre · month-end | quoted · supplemental | 25 | 10.484 | 2.886 | 2.906 | 5.772 | −4.713 | 0.82 |
| london_fix pre · month-end | passive_w1_p1 · momentum | 25 | 14.745 | 2.523 | 3.315 | 5.047 | −9.698 | 0.67 |
| london_fix pre · month-end | passive_w1_p1 · supplemental | 25 | 10.484 | 3.321 | 3.992 | 6.643 | −3.841 | 1.12 |
| calendar 1d | quoted · momentum | 519 | 5.275 | 3.418 | 4.406 | 6.835 | 1.560 | 2.08 |
| calendar 1d | quoted · supplemental | 517 | 4.536 | 3.176 | 3.799 | 6.352 | 1.816 | 2.04 |
| calendar 1d | passive_w1_p1 · momentum | 414 | 5.865 | 3.664 | 4.182 | 7.328 | 1.462 | 1.79 |
| calendar 1d | passive_w1_p1 · supplemental | 410 | 5.235 | 3.639 | 4.138 | 7.279 | 2.044 | 1.98 |

### 7.3 ⭐ 「passive で feasible になった cell」は改善ではない

unit audit が発見した gate の逆転がここで実地に出た。`MDE ≤ 2 × median C` は
**設計が高くつくほど通りやすくなる**。`ny_option_cut pre · month-end` は quoted
では supplemental で headroom −1.566（powered でない）が、passive_w1 では
**+0.356 で powered になる**。MDE は 7.956 のまま一切動いていない。動いたのは
コストだけで、hurdle が 6.390 → 8.312 に上がったから通ったのである。

つまり **passive_w1/w2 の「生存者」は、執行が悪化したことによって生まれている。**
これを Track 1 v2 の候補として採ることは、gate の欠陥を利益と読み替えることに
等しい。unit-free な指標である break-even IR で見れば全 cell が悪化しており、
`london_open pre · month-end` は **1.42 → 2.05** に要求が上がっている。

## 8. Track 1 v1 status

**`CLOCK_STRUCTURE_TRACK_V1_WITHDRAWN_AFTER_UNIT_CORRECTION`**。
v1 の primary A/B/C は unit 修正で前提が失われており、本 stage はそれを回復しな
かった。ただし **clock / institutional-flow family 自体は closed ではない**。

## 9. Track 1 v2 feasibility

裁定は Human + ChatGPT の §20 のツリーに従う。

* **Case A は満たさない。** 「複数の economically meaningful な cell が 3 gate を
  満たす」状態は、いかなる variant・いかなる IR_max でも生じていない。
* **IR_max 1.0 と 1.5 では、clock 窓に収まる variant で feasible cell は 0。**
  quoted で 1 個あった `london_open pre · month-end` は passive で消える。
* **IR_max 2.0 でのみ 1〜2 個が現れるが、§7.3 の理由でそれは改善ではない。**
  加えて IR_max を結果を見て 2.0 に選ぶことは §2 が明示的に禁じている。
* **primary rule（w4）では、どの IR_max でも 0。**

したがって **Case C**:
**`CLOCK_STRUCTURE_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER`**。
family を null 扱いにはしない（§17）。これは検出力・経済性の設計不能であって、
「十分な検出力で検定して edge が支持されなかった」ではない。

`MARGINAL_CELL_NOT_ROBUST_TO_EXECUTION_UNCERTAINTY` は本測定で裏づけられた:
`london_open pre · month-end` の余裕は 0.196 / 0.086 bp だが、執行方式を現実的な
代替に変えるだけで required IR が 0.6 以上動く。余裕は執行の不確実性より 1 桁
小さい。

## 10. London fix

`LONDON_FIX_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER`。
公表された根拠は最も強いが、月末 dispersion が大きく（MDE 14.745 / 10.484 に対し
hurdle 5.850 / 5.772）、コストが下がらない以上どの variant でも powered にならない。
Track 3 でコストが十分下がった場合のみ再評価という条件は、**下がらなかった**ので
発火しない。これは null ではない。

## 11. Track 2 status

**待機**。prereg freeze、Stage 0、Stage 1 のいずれにも進んでいない（§21）。

## 12. M1 status

**未使用**。本 stage は既存 M15 キャッシュのみで完結した。M1 再集約は行っておらず、
必要も生じなかった（§23）。

## 13. Protected-data confirmation

読んでいない: fresh pool `2016-06-02 … 2021-04-25`、historical OOS slice、
dead window、forward Formal Confirmation epoch。有料データ取得なし（CME /
Databento を含む）。broker 認証、demo/paper/live 執行、実注文、production
デプロイのいずれも行っていない。`scripts/research/execution_frontier/` は archive
path を持たず、パネルは `round_a.panels` 経由でのみ読む。
