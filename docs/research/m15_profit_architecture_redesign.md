# FX Spot Profit Architecture Redesign — 結果

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Status: **`PROFIT_ARCHITECTURE_REDESIGN_ASSESSED`**

成果物は `artifacts/research/profit_architecture/redesign.json`。実装は
`scripts/research/profit_architecture/`（cost_audit / mechanics / candidates）。
**市場データを 1 バイトも読んでいない** — 全数値は、凍結済みの実測定数
（vol 377.7 bp/gross、往復 3.406 bp、実測 turnover 36.7 等）に対する算術と、
**合成 weight 過程の signal-free シミュレーション**である。裁定 §47 の
「軽量検証のみ」の範囲内。

本文書は 2 稿目。2 ロールの独立レビュー（Role 1: 経済・算術 / Role 2: 既往証拠・
閉鎖境界・governance）が BLOCKER 計 4・required fix 計 12 を返し、
**すべて再現してから採用した**。主な訂正は §0a に一覧する。

---

## 0a. ⭐ レビューが直したもの（初稿の誤りの記録）

| 指摘 | 訂正 |
| --- | --- |
| ⭐ **「band の tracking gap はコストゼロ」を『実測済み』と書いたが、誰も測っていなかった** | alpha capture を実際に計算に追加: band 0.10 で **0.958** — gross IR の **4.2% を犠牲**にする。必要 IC は capture 込みで請求 |
| ⭐ **headline の下端 T=12 が band の結果として書かれていたが、band 0.10 の実測は 14.4** | T=12 は一般参考行に戻し、band 行は 14.4 + capture で請求 |
| ⭐ **「yield CHANGE は未検定」— ledger が反証**（H-016 は BIS 政策金利の level と **change** の両方を検定、carry_change は全頻度でパネル間符号反転） | 境界を**商品軸**で引き直した: 未検定なのは**市場国債金利・カーブ**であって change ではない |
| ⭐ **+0.55（非証拠の開発観測）の引用が同じ artifact 内の不合格事実を落としていた** | 引用箇所すべてに併記: top10 占有 3.05、JPY +493bp/全体+92bp、fold 2/6 負、×2 コストで −0.08 — **自らの kill rule に既に抵触** |
| **H-003 閉鎖を「pair-level のみ」と書いた** — inventory は C08（**currency-level** rank persistence）を閉鎖済み | A01 は C08 との境界（多特徴量条件付き推定 vs 素の persistence）を prereg で明示する義務を負う |
| **A16 の 6–16% から「POST HOC・in-sample」の限定が落ちていた** | ledger の限定を復元。移転は測るまで仮定 |
| **「event day はコスト不利なし」— 実測は spread 1.05×/1.02× WIDER** | 「1–2% 広い。優位が無いだけでなく僅かな不利が実測されている」に訂正 |
| **A05/A11/A12 の turnover が mechanics 由来と書かれていたが simulation は存在しない** | 「宣言された判断（mechanics の隣接行の間）」と明記 |
| **閉鎖 family ガードが飾りだった**（gate_family を宣言する候補が 0） | 機構テストを追加（合成候補で `assert_prospective` 発火を実測）。判定は prose であることを docstring に明記 |
| **multi-horizon の加法上界が share 0.5 で破れる**（41.8 > 40.6） | 「share ≤ 0.3 の変調に限る」と上界を限定し、破れる点もテストで固定 |
| **netting の過大請求を「10–20%」と過小開示** | routing 監査を単位修正して 3 比を実測: **1.32（課金値）/ 0.77（実装）/ 0.55（下限）** — 因子 **1.71 / 2.38** |
| **model-learning 実行が ledger に無かった** | **H-022** を追記（実測 turnover 36.7 等の出典） |
| **redesign.json に classification が無かった** | 追加 |
| その他: 6.87 は smooth book のみの因子（他は 2.8/1.8）、「34.5 と 36.7 の一致」→「近い（6% 差・half-life は 5 点グリッド）」、event 型稼働率 13%→**13.7%**（34.4/252）、SE(IR)=1/√y は (1+IR²/2) 項を省略（24.7 年→約 27.8 年、悲観方向）、A04 の breadth を自分の event 数と整合（0.16/日） | 各所修正 |

---

## A. Executive conclusion

**G10 FX spot で意味のある年間利益を狙う最も合理的な architecture は、
「連続的な通貨レベル long-short ポートフォリオ + no-trade band + vol targeting」
であり、その最低要求は次の通り**:

> 日次断面 IC ≈ **2.1〜2.6%**（band 0.10・capture 0.958 込みで 2.07〜2.11、
> band なし実測 turnover で 2.62）、
> 実効 breadth **4 通貨方向 × 252 日**、
> 実現 turnover **14〜37 round trips/年**（予測は毎日でよい）、
> レバレッジ **2.65×**（10% vol target）、
> 達成収益 **年率 5%（net Sharpe 0.5）、想定 max DD ≈ 19%**。

コスト請求を（保守的な 3.406 ではなく）実装実測の netting（1.99 bp/単位）にすると
必要 IC は **≈2.2%** まで下がる — この余地は headline に入れず開示に留める。

この regime は**過去のどの研究も検定していない** — 過去の検定は
(a) 1 予測 = 1 往復のコスト規約、(b) per-trade 経済、(c) confirmation 級の検定力
要求のいずれかで、この帯域を構造的に見えなくしていた。統計的に排除されたのでは
なく、**測定されなかった**。

同時に正直な限界: この regime の実在は未検証であり、**α=0.05 の formal 証明は
現実的な edge に対して数十年分のデータを要する**（net 0.5 で 24.7〜27.8 年）。
したがって「研究する価値」は、**証明基準ではなく意思決定基準（小規模展開 +
kill rule）を人間が受け入れるか**に依存する。

## B. What prior research actually proved

1. **Per-trade の大きな edge は M15〜数日の price 構造に存在しない** — 26 戦略、
   1,078 条件付き fit、reversal/momentum family 3 span、すべて full-cost 後負または雑音。
2. **VR < 1 の短期 mean reversion は実在する**が、それに付随する 6〜16% of
   break-even という数字は **ledger の POST HOC・in-sample な最良線形予測子**
   （楽観上界）である（H-010）。
3. **Carry は short-yen 集中**（63〜95 倍、H-016）— そして H-016 は BIS 政策金利の
   **level と change の両方**を検定済みで、**carry_change は全頻度でパネル間
   符号反転**した。**Volume は volatility を当てるが direction を当てない**
   （H-015/H-017）。**Event は movement を作る（matched 1.58〜1.63×）が direction を
   作らず、spread は 1.05×/1.02× 広い** — コスト優位が無いだけでなく僅かな不利が
   実測されている（H-018/H-019）。COT null（H-021）。
4. **実行コストの床は market order で往復 2.47〜2.69 bp**、passive 執行では
   突き抜け定数 0.25〜0.4 pip を越えられない（Track 3）。
5. **構造定数**: gross 1 単位あたり年次 vol 377.7 bp（span 別 370〜430、
   構成依存性あり — M01 の book は 393 相当）、20 ペアの有効独立方向 3.2〜6.5、
   通貨断面の有効独立 ≈ 4。
6. **日次更新 book の実測 turnover は 36.7〜142.5 RT/年**であって 252 ではない
   （H-022、`development.json`）。

## C. What prior research did NOT prove

1. **「連続 currency portfolio に gross IR 0.6〜0.8 の edge が無い」ことは証明されて
   いない。** 3.17 年の out-of-fold での IR の標準誤差は ≈ 0.56 — この帯域は
   **検出力の外**にあった。
2. **「price では無理」「ML では無理」「cross-sectional では無理」は証明されていない**
   — 閉じたのは特定の設計（絶対 direction、離散 position、full-RT コスト、
   そして C08 の**素の currency rank persistence**）である。
3. **市場国債金利・カーブの repricing → FX は一度も開かれていない。**
   検定されたのは **BIS 政策金利**（level・change とも）のみ — この区別は
   level/change ではなく**商品**の軸である。
4. **Portfolio の効率層（band、vol targeting、multi-horizon 合成、部分リバランス）は
   一度も評価されていない。** ただし「全 phase が per-trade 経済」は過言で、
   H-016 は実現 turnover を課金し、model-learning の evaluator も実現 |Δw| に
   課金していた — 未評価なのは上記の**効率層**である。

## D. Why previous research may have underexplored profit architecture — Gate 監査

**どの verdict も再開しない**（テストが `verdicts_reopened_by_this_audit == []` を
固定する）。監査対象は判定ではなく**計器**である。

| Gate | 正しく制御していたもの | 構造的に見えなかったもの |
| --- | --- | --- |
| v1 | なし（高コスト設計を優遇） | — v2 が既に修正 |
| v2 / preflight | **確認級**の仮説主張（α=0.05・80% power・2 パネル） | ≤2 年パネル上の**開発活動そのもの** |
| model-learning gate | capacity 会計、leakage 形状、閉鎖 family、単位規律 | ⭐ **予測頻度を turnover として課金**（smooth book で 6.87 倍 — 他の実測 book では 2.8×/1.8× で、filtered book は実測 turnover でも経済条件に落ちる）。⭐ **confirmation 級 FWER を開発選択に課金**（1 選択 10.8 年）。⭐ **per-trade 経済**が unit of account |

⭐ **model-learning の capacity 予算は本 redesign でも有効なまま**である: その記録は
「実測 turnover なら経済条件は通るが、そのとき許される有効パラメータは IR 0.5 で
0.188 個、当てはめた 4.2 個は 22 倍超過」と**両面**を開示している。初稿は有利な
半分だけ引いた。Track 1 の prereg はこの制約への回答（後述 §V）を含む義務を負う。

## E. Transaction-cost audit

**3.406 bp の完全分解**:

```
3.406 bp = 2.58（pair 往復 = Track 3 実測 2.6902/2.4660 の中点、両脚）
         × 1.32（孤立した 1 通貨対バスケット position の実測 routing、Track 2）
```

単位は「実際に取引した notional」であって予測・シグナル・日ではない。片道 1.29 bp。

**旧規約**は `annual_cost = 予測頻度 × 3.406` — 日次設計に 858.3 bp/年を課した。
実測（H-022）は smooth book で **125.0 bp/年**。**6.87 倍の過大計上**（smooth book の
因子。regime book 2.8×、filtered book 1.8×）。

### ⭐ Netting 監査 — 課金値自体も保守的（新規実測）

一つの式 **cost/turnover 単位 = R × 2.58 bp** に 3 つの R:

| R の意味 | R | cost/単位 | 保守係数 | drag @ T=36.7 |
| --- | --- | --- | --- | --- |
| **課金値**（孤立 position の routing） | 1.320 | **3.406** | 1.00 | 0.331 |
| **実装**（corpus の equal-split netting） | **0.770** | 1.987 | **1.71** | 0.193 |
| **下限**（最小 notional LP、実 20 ペア位相） | 0.554 | 1.429 | 2.38 | 0.139 |

caveat: 両実測行は全ペアを平均 2.58 bp で価格付けしており、最小 notional routing は
spread の広い cross に寄るため、実現可能な節約は下限より小さい。
**headline は保守的な 3.406 のまま請求し、この表は開示** — 取りに行く候補が A08。

## F. Prediction frequency vs turnover — 機構法則

⭐ **中心的な機構事実（signal-free、全行が毎日更新）**:

| target の半減期 | 日次自己相関 | 年間 turnover | 年間コスト | IR drag |
| --- | --- | --- | --- | --- |
| （毎日新規） | 0 | 175.2 | 596.7 bp | 1.58 |
| 1 日 | 0.500 | 125.4 | 427.0 bp | 1.13 |
| 5 日 | 0.871 | 65.9 | 224.4 bp | 0.59 |
| 10 日 | 0.933 | 48.0 | 163.5 bp | 0.43 |
| **20 日** | **0.966** | **34.5** | **117.5 bp** | **0.31** |
| 60 日 | 0.989 | 20.2 | 68.7 bp | 0.18 |

**`turnover ∝ √(1−ρ)`** — コストを決めるのは**予測の持続性**であって更新頻度では
ない。20 日行（34.5）は実測 36.7 に**近い**（6% 差。half-life は 5 点グリッドからの
選択なので「検証」ではなく桁の整合）。

**No-trade band**（半減期 20 日）— ⭐ **capture 列が band の代金**:

| band | turnover | コスト | tracking gap | **alpha capture** | 必要 IC（net 0.5、capture 込み） |
| --- | --- | --- | --- | --- | --- |
| 0 | 34.5 | 117.5 bp | 0 | 1.000 | 2.55% |
| 0.05 | 23.1 | 78.5 bp | 0.13 | 0.989 | 2.26% |
| **0.10** | **14.4** | **49.0 bp** | 0.29 | **0.958** | **2.07%** |
| 0.15 | 10.0 | 34.1 bp | 0.44 | 0.907 | 2.05% |

0.15 で頭打ち — capture の損失が turnover の節約を食い始める。

**Multi-horizon**（60 日 core + 3 日 fast）: share 0 → 19.9、0.2 → 27.7、0.3 → 37.3、
0.5 → 61.7、fast 単独 → 81.2。⭐ **「fast は share × fast 単独以下しか追加しない」は
share ≤ 0.3 の変調に限って成立**（0.5 では 41.8 > 40.6 で破れる — テストで両側固定）。

## G. Capital utilization

| 設計型 | 稼働率 |
| --- | --- |
| 連続 portfolio | **~100%** |
| event window 型（34.4 決定/年 × 1 日） | 34.4/252 ≈ **13.7%** |
| 離散 per-trade 型（H-014 の唯一の生存 population） | 数% |

## H. Leverage / return translation

**レバレッジは edge ではない** — drag `T×3.406/377.7` は per-gross 比の比なので
レバレッジ不変（テストで固定）。

| vol target | レバレッジ | net Sharpe 0.3 | 0.5 | 0.8 | 1.0 |
| --- | --- | --- | --- | --- | --- |
| 8% | 2.12 | 2.4% | 4.0% | 6.4% | 8.0% |
| **10%** | **2.65** | 3.0% | **5.0%** | 8.0% | 10.0% |
| 12% | 3.18 | 3.6% | 6.0% | 9.6% | 12.0% |

5 年想定 max DD（10% vol、Gaussian）: Sharpe 0.3 → 22%、0.5 → 19%、0.8 → 16%、
1.0 → 15%。裾はこれより重い（Gaussian は過小、方向は悲観側に開示）。

**逆算**（§3）: 2%/年 = Sharpe 0.2。**5% = Sharpe 0.5 が中心シナリオ**。10% =
Sharpe 1.0（必要 gross 1.11〜1.33、天井 1.5 の内側上端）。15% は 10% vol では
天井超え — 12〜15% vol でのみ理論上射程（DD 30% 級）。

## I–J. Currency-level / continuous portfolio assessment

* **Pair は執行手段であって予測対象ではない。**
* ⭐ **C08（currency-level rank persistence）は閉鎖済み**である — 初稿は「閉鎖は
  pair-level」と書き、レビューが inventory の記録で訂正した。生き残る線は
  「**多特徴量の条件付き推定**（currency strength は係数 0 も許される 1 入力）」で
  あり、「strength が persist する」という仮説そのものではない。**Track 1 の
  prereg はこの境界を C08 に対して明示的に引く義務を負う。**
* **必要 edge**（capture 込み）: band なし実測 T=36.7 → gross 0.831 → **IC 2.62%**。
  band 0.10（T≈15.3、capture 0.958）→ gross(target) 0.669 → **IC 2.11%**。
  合成 34.5 基準なら 2.55% → 2.07%。
* ⭐ **唯一の直接観測は「同じ桁」ではなく「無情報」と読む**のが正しい:
  model-learning run の 4 book の gross IR は **+0.94 / +0.55 / −0.48 / −0.53** —
  SE ≈ 0.56 の下で zero-edge が予言する散らばりそのもの。そして +0.55 の book は
  **自らの事前登録規則に不合格**（top10 占有 3.05、JPY +493bp/全体 +92bp、
  fold 2/6 負、×2 コストで −0.08）で、その集中形は H-016 の short-yen 再演であり、
  **Track 1 が宣言する kill rule に既に抵触する**。非証拠・汚染。
  この観測が支えるのは「要求水準が空想の桁ではない」ことだけで、
  「観測されている」ことではない。

## K. Multi-horizon assessment

3 horizon の合成は breadth を最大 ~1.5 倍にし得る（**仮定**であり相関次第で 1.0）。
turnover 追加は share ≤ 0.3 で share × fast 単独以下（§F）。Track 1 成立後の拡張。

## L. Core + overlay assessment

Overlay は direction を作らず **gross exposure・concentration・タイミング**を変調
する（gross 正規化 book への日次一定 gain は厳密に無効 — H-022 の教訓）。
event の breadth は **34.4 決定/年 ≈ 0.16/日**（初稿の 0.5 は自分の event 数と
不整合だった）。価値は core の edge に条件付き。

## M. Cross-asset assessment

**未開封なのは「市場金利・カーブ」という商品**であって「change という変換」では
ない — H-016 は BIS 政策金利の change まで検定し、**全頻度でパネル間符号反転**を
記録している。これは隣接する**不利な**証拠として A06/A11 が背負う。無料 EOD の
鮮度リスクも変わらず。

## N. Regime assessment

役割は selector / blender / exposure scaler / turnover controller のみ（A07、score 1）。

## O. Event / opportunity assessment

確立済み: matched movement 1.58〜1.63×、null と区別可能（p=0.005 床）。
**spread は 1.05×/1.02× 広い — コスト優位なし、僅かな不利が実測**。direction なし。
→ sizing / timing / concentration（A04）。

## P. ML role assessment

ML の役割は expected-return vector 推定 / weight mapping / horizon blend /
trade-no-trade / risk allocation。**capacity 予算は引き続き有効**で、Level 2（木）は
40 倍超過のまま。⭐ **Track 1 は capacity 制約（§D の 22×）への回答を prereg に
含める義務を負う** — 例えば「特徴量 4〜7 本を**固定重みの合成 1〜2 本**に縮約し、
fitted 実効自由度を ≤1〜2 に抑える」— 本文書はその設計を予告するだけで解決とは
主張しない。

## Q. Portfolio construction assessment

band が第一選択（drag 0.33 → 0.14、capture 0.958 の代金込みで必要 IC を **約 20%**
引き下げる）。optimizer（A10）は plain band を有意に上回る場合のみ。

## R. Candidate universe — 20 architectures

| # | ID | role | capacity | score |
| --- | --- | --- | --- | --- |
| A01 | continuous currency portfolio | core | 5–10% | 9 |
| A02 | no-trade band rebalancing | efficiency | enabler | 18 |
| A03 | multi-horizon blend | core | 5–10% | 6 |
| A04 | core + event overlay | overlay | 2–5% | 8 |
| A05 | residual factor-neutral book | core | 2–5% | 1 |
| A06 | cross-asset repricing | core | 5–10% | 4 |
| A07 | regime-adaptive exposure | overlay | 2–5% | 1 |
| A08 | execution vehicle optimization | efficiency | enabler | 15 |
| A09 | sparse high-confidence overlay | overlay | 2–5% | −1 |
| A10 | turnover-penalized optimizer | efficiency | enabler | 3 |
| A11 | yield-change slow component | core | 2–5% | 8 |
| A12 | dispersion relative value | core | <2% | −4 |
| A13 | event portfolio tilt | overlay | <2% | −2 |
| A14 | volatility-conditioned leverage | efficiency | enabler | 18 |
| A15 | horizon-ensemble ML | core | 5–10% | −3 |
| A16 | MR-timed rebalancing | efficiency | enabler | 8 |
| A17 | session-aware scheduling | efficiency | enabler | 18 |
| A18 | weekly currency trend | core | 2–5% | 1 |
| A19 | drawdown-governed meta-risk | efficiency | enabler | 16 |
| A20 | paper-forward evaluation | evaluation | enabler | 15 |

turnover の由来は候補ごとに `turnover_basis` が「mechanics 実測」か「宣言された
判断」かを区別する（A05/A11/A12 は判断）。score は宣言された整数判断の線形結合で、
**測定ではなく攻撃可能な形の判断**。⭐ **閉鎖 family ガードは自己申告制** —
20 候補のどれも `gate_family` を宣言していないので `assert_prospective` は発火せず、
隣接判定は prose で争う（機構自体は合成候補のテストで発火を実測済み）。

⭐ **A16**: H-010 の VR<1 は実在するが、6–16% は **POST HOC・in-sample の上界**。
「強制 trade の retiming なら増分コストゼロ」という移転は**測るまで仮定**であり、
standalone closure の範囲外であることだけが確か。
⭐ **A18**: 3 つの閉鎖（4–6 日 family、C08、H-012）の間に座る。走らせるには
**新しい instruction が要る**（no round licenses the next one）。

## S. Economic capacity table

10% vol target、breadth 4/day、**capture 込み**:

| turnover | コスト | IR drag | capture | 5%/年に必要な gross IR | 必要日次 IC |
| --- | --- | --- | --- | --- | --- |
| 252（旧規約） | 858 bp | 2.272 | 1.0 | 2.77 | 8.7% |
| 50 | 170 bp | 0.451 | 1.0 | 0.95 | 3.0% |
| **36.7（実測、band なし）** | **125 bp** | **0.331** | 1.0 | **0.831** | **2.62%** |
| 25 | 85 bp | 0.226 | 1.0 | 0.73 | 2.3% |
| **≈15.3（実測 book に band 0.10）** | **52 bp** | **0.141** | **0.958** | **0.669** | **2.11%** |
| 12（一般参考行 — band の結果ではない） | 41 bp | 0.108 | 1.0 | 0.61 | 1.9% |
| 6 | 20 bp | 0.054 | 1.0 | 0.55 | 1.7% |

⭐ 初稿は T=12 の一般行を「band 後」と誤ってラベルしていた。band 0.10 の正しい行は
**T≈15.3・capture 0.958 → IC 2.11%**（合成 34.5 基準なら 14.4 → 2.07%）。
netting-faithful なコスト（1.99 bp/単位）ならさらに ≈2.2% 帯へ — 開示のみ。

## T. Candidate ranking

§R の score 列。role 混在の単純 top-3 は category error なので選抜は role ごと（§V）。

## U. Adversarial review（各 top candidate への反証）

* **A01「弱い edge を複雑化しただけでは」** — モデル自体は Round 1 より単純
  （係数数本の ridge）。複雑化したのは**評価**。ただし edge の前提は依然無証拠で、
  唯一の観測は**無情報 + 自らの規則に不合格**（§I–J）— これが Track 1 の検定対象。
* **A01「capacity 予算と矛盾しないか」** — 現状はする（22×）。prereg で fitted
  実効自由度を予算内に縮約する設計（固定重み合成）を示せなければ走らない。
* **A01「portfolio 化が negative expectancy を隠さないか」** — net = gross − T×cost
  は線形分解され、gross と T を別々に報告する。
* **efficiency bundle「edge ゼロなら無意味では」** — その通り、enabler と分類し
  return を主張しない。ただし drag 0.331 → 0.141（capture 込み実質）は必要 IC を
  **約 20%** 下げ、探索対象の実在確率そのものを変える。初稿の「27%」は
  capture を無視し band の T を 12 と誤記した値。
* **A04「H-002 の再演では」** — H-002 は離散 rule の on/off gate、A04 は連続 book の
  gross 変調。core の edge への条件付きであることは明記。
* **Bottom 側の過剰棄却チェック（§43）** — A18/A12 は閉鎖への隣接で減点（同形
  だからではない）。A15 は capacity で落ちる（ML だからではない）。A06 は情報利得
  最大級だが、**H-016 の carry_change 符号反転という隣接不利証拠**を新たに背負う
  （初稿はこの証拠を「未検定」と書いて消していた）。

## V. Top profit-seeking tracks（最大 3）

### Track 1 — Continuous currency portfolio core（A01、拡張 A03/A06）

* **経済仮説**: 小さく持続的な断面予測性 × 全稼働 × 4 有効 breadth × 低実現
  turnover が、per-trade では見えない年率 5% 級を作る。
* **成功に必要な magnitude**: gross(target) IR 0.67〜0.83、日次 IC **2.1〜2.6%**
  （capture 込み）。
* **prereg が解決すべき 2 制約**（本文書は予告のみ）:
  (1) **capacity** — fitted 実効自由度を model-learning 予算内へ（固定重み合成
  1〜2 本など）。(2) **C08 境界** — 素の rank persistence との線を明示。
* **kill**: 宣言された点推定規則として運用する — ⭐ **OOF gross IR の SE は ≈0.56
  なので、kill rule は統計的推論として自らを解決できない**（「gross < 0.3 で kill」は
  0 とも 0.8 とも区別できないまま切る決定規則である）。これを隠さず、判定は
  paper-forward と confirmation 層に送る。DSR/PBO 診断併用。
* **profit potential**: 10% vol で 3〜8%/年（Sharpe 0.3〜0.8）。

### Track 2 — Efficiency bundle（A02+A14+A17+A19+A08、後続 A16/A10）

* **経済仮説**: なし — 算術。band は drag 0.331 → 0.141（capture の 4.2% 込みで
  必要 IC **−20%**）。A08 は netting の実測余地（1.71×〜2.38×）を取りに行く。
* signal-free に構築・検証可能で、alpha の存在に依存しない。
* kill: なし（機構）。実装検証のみ。

### Track 3 — Event/vol exposure overlay（A04、後続 A07）

* **経済仮説**: 確立済みの movement 構造（1.58〜1.63×）を direction なしで
  exposure/concentration/timing に換金する。breadth 0.16/日、event 34.4/年。
* **前提**: Track 1 の core が正の期待値を持つこと。着手は Track 1 の初期読みの後。
* profit potential: core に +1〜3%/年の変調利得、または同収益での DD 低減。

**全 track 共通**: 凍結候補は **paper-forward（A20）** に載せ、fresh pool を消費せず
非汚染評価データを蓄積する（true net 0.5 でも fresh+3 年 paper の one-shot 検出力は
40% — 証明ではなく不確実性の縮小）。

## W. Minimal development experiments（今回実施済み・すべて signal-free）

1. Turnover 法則（√(1−ρ) 則）— `mechanics`
2. No-trade band の turnover/**capture**/tracking トレードオフ — `mechanics`
3. Multi-horizon 合成の turnover 加算則（上界の破れ点含む）— `mechanics`
4. **Pair routing 監査**（equal-split 実装 0.77 / 最小 LP 0.554、実 20 ペア位相）
5. Capacity/leverage/DD/power の全表 — `mechanics`
6. コスト規約の分解と 6.87 倍（smooth book）の同定 — `cost_audit`
7. 変異テスト（PR 本文に記録）

**新しい alpha backtest は 1 本も実行していない。**

## X. What not to repeat

M15 indicator zoo → 絶対 direction / 4–6 日 reversal と mirror momentum /
単純 HTF sign conditioning / H-003 同形（**C08 currency-level rank persistence を
含む**）/ BIS policy-rate carry（**level も change も**）/ 検定済み COT family /
生 M15 price → direction ML / ≤12h linear path harvesting（standalone として）/
retrace geometry / tick volume → direction / event-day コスト優位の主張 /
USD-pooled 絶対 1h consensus surprise / **1 予測 = 1 往復のコスト規約** /
**予測頻度と turnover の混同** / **per-trade 経済での architecture 評価** /
**confirmation 級 FWER の開発への適用** / **「実測した」と書く前に実測しないこと**。

## Y. Final recommendation — §50 への回答

**Q1: 最も合理的な system architecture は何か。**
連続・通貨レベル・factor-neutral の long-short portfolio（Track 1）を core とし、
no-trade band + vol targeting + DD governor（Track 2）で drag を 0.14 まで削り、
event/vol overlay（Track 3）で exposure を変調し、pair を執行手段としてのみ使う。
凍結候補は paper-forward で評価する。

**Q2: 最低限必要な数値。**

| 量 | 最低要求（5%/年 @ 10% vol） | 楽観上限（10%/年） |
| --- | --- | --- |
| net Sharpe | 0.5 | 1.0 |
| gross(target) 年次 IR | 0.67（band 0.10・capture 込み）〜0.83（band なし） | 1.19〜1.33 |
| 日次断面 IC | **2.1〜2.6%**（netting-faithful 請求なら ≈2.2% 下限） | 3.7〜4.2% |
| 有効 breadth | 4 通貨方向/日（+horizon で最大 ×1.5、仮定） | 同左 |
| turnover | 14〜37 RT/年（予測は日次） | 同左 |
| レバレッジ | 2.65×（10% vol） | 同左 |
| 想定 max DD | ~19%（Gaussian、裾はより重い） | ~15% |

**Q3: 現実的に研究する価値があるか。**
**条件付き YES — ただし NO と答え得る根拠も同じ表にある。**

YES の根拠: (1) この帯域は過去に**測定されていない**、(2) 必要 IC 2.1〜2.6% は
天井の内側、(3) 開発コストは低く、(4) efficiency bundle は edge の有無に関わらず
価値が残る。

NO の根拠（レビューが要求した明示）: (i) **開発の kill rule は SE 0.56 の下で
自らを統計的に解決できない**、(ii) 唯一の肯定的観測は自らの規則に不合格で、
4 book の散らばりは zero-edge の予言と一致する、(iii) 補正不能な seen-data
multiplicity（~1,200 構成 + 22 仮説）が開発選択の IC を上方バイアスし、
confirmation 層はそれを **29.5%**（fresh one-shot）/ **40%**（+3 年 paper）の
検出力でしか救えない、(iv) 停止する場合 efficiency bundle の価値も 0。

条件: **α=0.05 の formal 証明は net 0.5 に対し 24.7〜27.8 年**を要する。したがって
この研究が意味を持つのは、**「証明後に展開」ではなく「開発証拠 + paper-forward +
小規模展開 + kill rule」という意思決定基準を Human が採用する場合に限る**。
その採否は本報告の範囲外の人間の判断である。採用しないなら、正直な帰結は
「FX spot active alpha は証明基準の下では研究不能」であり、そこで止めるのが一貫する。

---

## レビュー記録

2 ロール（Role 1: 経済・算術、Role 2: 既往証拠・閉鎖境界・governance）。
BLOCKER 4 / required fix 12 / 観測 13 — 全採用、§0a に記録。変異テストの結果は
PR 本文に記録する。
