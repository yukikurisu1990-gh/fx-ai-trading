# FX Spot Decision-Grade Research Inventory — 結果

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Status: **`CURRENT_SEEN_DATA_FX_RESEARCH_SPACE_EXHAUSTED`**

成果物は `artifacts/research/feasibility/inventory.json`。**signal・return・sign・
IC・Sharpe・p 値・PnL を一切計算していない。** 独立レビューが import closure と
`sys.addaudithook` で全 `build()` を追跡し、**open / socket / subprocess のイベントが
0 件**であることを実測した。

---

## 0. 一行で

**GREEN 0、AMBER 0。** 22 の研究方向のうち
**RED 15 / BLOCKED 2 / OUT_OF_GATE_SCOPE 2 / CLOSED 3**。

理由は個々の仮説ではなく**データ地平**である。Gate v2 の 2 条件は dispersion 軸上の
区間を定め、区間が空でない条件から MRE も σ も cost も消えて
`effN ≥ (z/IR_max)²·f` だけが残る。1 つの設計は**1 つの観測単位**を持ち、その単位で
`N = f × panel_years`・`effN ≤ N` なので `effective_years ≤ panel_years`。
決定パネルは **1.996 年**、必要は **3.488 年**。

**seen data をすべて足しても届かない**（連続 4.674 年を 2 パネルに割ると 2.337 年）。
**fresh pool 相当の長さ（4.786 年/パネル）にしても、PASS に達する候補は 0**、
MARGINAL が 1 件だけである。

---

## 1. ⭐ 初稿はレビューで 3 つの BLOCKER を受けた

本文書は 2 稿目。2 つの独立ロールのうち Role 1 が BLOCKER 3 件、Role 2 が
BLOCKER 0 件・required fix 2 件を返した。すべて自分で再現してから採用した。

### B1 — 「horizon が理由」は Gate v2 の性質か、記述の都合か

Role 1 は、`effective_years ≤ panel_years` が `ResearchPlan` の
`n_events = f × panel_years` という**構成**から出ており、Gate v2 の `Design` は
その 2 つを意図的に分離している、と指摘した。そして今日のパネルで合成判定を通る
反例を示した（`N = 3521` を通貨日で、`f = 252` をポートフォリオ日で数える）。

**再現した結果、それは単位の不整合だった。** 同じ設計を**どちらの単位でも一貫して**
組むと、**ゼロコスト・完全独立でも、どの dispersion でも通らない**:

| 組み方 | N | f | effN/f | 全 dispersion を掃引して通る数 |
| --- | --- | --- | --- | --- |
| 混在（反例） | 3521 | 252 | 4.19 | 通る |
| (a) 通貨日で統一 | 3521 | 1764 | 0.60 | **0** |
| (b) ポートフォリオ日で統一 | 503 | 252 | ≤1.996 | **0** |

反例は「7 倍の精度を主張しながら 1 冊分の回転しか払わない」形になっている。
7 本を netting した book は dispersion が 1/√7 になり、observation 数の増加と
ちょうど相殺するので、「推定だけ鋭い」第三の道も無い。

**ただし Role 1 の指摘自体は正しい** — 初稿はこの規約を**主張しただけで正当化して
いなかった**。規約と証明を `preflight.py` の冒頭に書き、
`TestTheUnitConventionIsForced` が上表を実測する。

### B2 — 見出しの不足年数がどの候補にも当てはまらない

初稿の「不足 2.303 年」は `share = 1.0`（完全独立）で計算したもので、**どの候補も
その仮定を使っていない**。候補ごとの必要年数は 4.36〜15.51 年/パネル。
さらに `ADDITIONAL_INDEPENDENT_HISTORY_WOULD_OPEN_PASS_REGION` は share フリーの
フラグから出しており、**候補ごとに再判定すると PASS は 0、MARGINAL が 1**。
成果物は候補ごとの再判定を持つようになり、フラグは False に変わった。

### B3 — CLOSED 6 件のうち 3 件は根拠が足りなかった

* **C04 / C05（fix flow・month-end）** — Track 1 の status は
  `..._NOT_DECISION_GRADE_...`、つまり**反証ではなく検出力不足**。反証済みとして
  記録するのは、このプログラムが繰り返し直してきた誤りそのもの。
  → **RED** に変更し、`suspended_by_decision` を別に持たせた（提案はできない）。
* **C13（timeframe disagreement）** — リポジトリにある唯一の HTF 判定は自ら
  「null も誤差棒も無い diagnostic」と書いている。閉じる根拠にならない。→ **RED**。
* C08 / C21 / C22 は裁定が明示的に閉じた family（H-003 同形 relative strength、
  COT tested cells、policy-rate proxy carry）なので **CLOSED のまま**。ただし
  **成果物に引用を持たせ**、`assert_prospective` が実際に例外を投げたことを
  `refused_by` として記録する（散文の約束ではなくコードによる拒否）。

### 主な required fix

| 指摘 | 対応 |
| --- | --- |
| preflight の multiplier が Gate v2 と別計算（2.8015852 対 2.802） | Gate v2 の定数を import し、`required_effective_years_gate_v2()` を分離。テストで一致を固定 |
| Bonferroni は Gate v2 に無く、preflight は**より厳しい** | 「Gate v2 の必要条件」と「preflight が追加する admissibility」を分離して明記。two-panel との二重補正と power の未補正を両方開示 |
| `binding_constraint` が通った条件を指すことがある | 失敗した条件から選ぶ |
| 遡及禁止が手書き文字列でしか効いていない | `assert_prospective` を `assess` から呼ぶ。例外を inventory が捕捉して記録 |
| C15 / C17 の target が return ではないのに return の gate にかけていた | **`OUT_OF_GATE_SCOPE`** を新設 |
| C01 の頻度 24/年は推測 | リポジトリの `s1_calendar.json` から **34.4/年**（169 件 / 4.91 年）。event floor 不合格は消えた |
| `BASKET_EXPOSURE = 1.29` は実測の**最小値**（N=11 セル由来） | 実測平均 **1.32** に（unit audit の 1.549 は別のポジション） |
| `PAIR_ROUNDTRIP_BP = 2.58` を「実測値」と書いていた | 2 実測値の**中点**と明記 |
| `signal_free: True` が固定リテラル | レコードを走査して**計算**する |
| 汚染スキャンが 5 ファイル中 2 つだけ | 全計算モジュールへ拡大。driver は別途検査 |
| 成果物比較が 2 キーだけ | レコード全体を比較 |
| `PANEL_YEARS` などの定数が未固定 | ローダー自身の span 定数と突き合わせて固定 |

## 2. Pass-Region Preflight

    σ ∈ [ MRE·√f / IR_max ,  MRE·√effN / z ]   → 空でない条件は  effN ≥ (z/IR_max)²·f

| | 値 |
| --- | --- |
| **Gate v2 自身の必要条件**（補正なし） | **3.488 年** |
| preflight が加える admissibility（2 cell） | 4.224 年 |
| 同（3 cell） | 4.653 年 |

残りの条件は**頻度の帯**を与える（event floor が下限、stressed cost が上限）。
cost は economic 条件にしか入らない。

## 3. Track 2 Retrospective Check

**止められた。** 凍結設計（panel 1.996 年、cell 3、パネル 2 枚）で **signal を一切
見ずに** `NO_DECISION_GRADE_PASS_REGION`、binding は `horizon`。頻度 30〜250、
コスト 0〜6 bp、完全独立、cell 1 個のいずれでも refuse される。
**Track 2 の verdict は変更していない。**

## 4. 現在の seen data 棚卸し

| span | 期間 | 役割 |
| --- | --- | --- |
| momentum_2021_2023 | 2021-04-26 … 2023-04-25 | 決定パネル |
| supplemental_2023_2025 | 2023-04-26 … 2025-04-24 | 決定パネル |
| **development_2025** | **2025-04-25 … 2025-12-28** | **seen だがどちらの決定パネルにも入っていない** |

通貨は G10 8 通貨・`PAIRS_20`。粒度は M1 由来の M15（bid/ask OHLC、spread、
pip_size、rollover、session）。**tick volume の列は決定パネルのキャッシュに無い。**
event calendar は FOMC / ECB / BoJ / RBA の公式発表日のみ機械可読（他 4 行は
自動取得経路をすべて拒否）。consensus は無料アーカイブ（**時刻は使用不可**、
日付は +5h 補正で公式 103/103 一致）。rates は BIS / FRED / ALFRED / Cleveland Fed。
positioning は CFTC COT（取得済み・検定済み）。cross-asset は未取得。

## 5. ⭐ 未使用だが既に seen のデータ（判断事項として残す）

**`development_2025`（0.68 年）**。`EXPLORATORY_SEEN_DATA`、protected ではなく、
どちらの決定パネルにも入っていない。足すと seen は **連続 4.674 年**になる。
**勝手にパネルへ追加していない。** ただし足しても 2 パネルでは 2.337 年にしかならず、
pass region は開かない。

## 6. Protected data boundary

**読んでいない**: fresh pool `2016-06-02 … 2021-04-25` / historical OOS slice
（`2025-12-29` 以降）/ dead window / forward epoch。counterfactual は
**マニフェストが既に持つ 2 つの日付の引き算**のみで、独立レビューが audit hook で
ファイルを一切開いていないことを実測した。

## 7. Candidate preflight 表

コストは 1 ペア往復 **2.58 bp**（Track 3 の 2 実測値の中点）と、通貨バスケット実装の
実測 gross exposure **1.32** を掛けた **3.406 bp**。

| Candidate | N/panel | effective years | MRE bp | binding | Verdict |
| --- | --- | --- | --- | --- | --- |
| C01 central bank decision response | 69 | 1.597 / 3.488 | 11.221 | horizon | RED |
| C02 macro surprise intraday | — | — | — | timestamp unusable | **BLOCKED** |
| C03 session handover relative | 10563 | 0.599 / 3.488 | 2.557 | horizon | RED |
| C04 benchmark fix flow | 503 | 1.597 / 3.488 | 3.691 | horizon | RED（**suspended**） |
| C05 month-end rebalancing flow | 24 | 1.597 / 3.488 | 27.500 | **event_floor** | RED（**suspended**） |
| C06 factor-neutral residual value | 3521 | 0.599 / 3.488 | 2.670 | horizon | RED |
| C07 cross-sectional dispersion state | 3521 | 0.599 / 4.224 | 2.670 | horizon | RED |
| C08 currency rank persistence | — | — | — | H-003 同形 | **CLOSED** |
| C09 yield-differential change | 3521 | 0.599 / 3.488 | 2.670 | horizon | RED |
| C10 equity risk regime | 3521 | 0.599 / 4.224 | 2.670 | horizon | RED |
| C11 commodity link response | 1509 | 0.599 / 3.488 | 2.897 | horizon | RED |
| C12 volatility regime transition | 3521 | 0.599 / 4.224 | 2.670 | horizon | RED |
| C13 timeframe disagreement | 3521 | 0.599 / 3.488 | 2.670 | horizon | RED |
| C14 latent regime state | 3521 | 0.599 / 4.653 | 2.670 | horizon | RED |
| C15 movement magnitude forecast | — | — | — | target が return でない | **OUT_OF_SCOPE** |
| C16 horizon selection | 3521 | 0.599 / 4.653 | 2.670 | horizon | RED |
| C17 intraday execution timing | — | — | — | target が return でない | **OUT_OF_SCOPE** |
| C18 ML currency ranking | 3521 | 0.599 / 4.653 | 2.670 | horizon | RED |
| C19 ML take/skip gate | 3521 | 0.599 / 4.224 | 2.670 | horizon | RED |
| C20 broker order flow | — | — | — | broker 認証が未承認 | **BLOCKED** |
| C21 futures positioning | — | — | — | COT tested cells | **CLOSED** |
| C22 carry level | — | — | — | policy-rate proxy carry | **CLOSED** |

### GREEN candidates

**なし。**

### AMBER candidates

**なし。**

### OUT_OF_GATE_SCOPE（2）

**C15**（移動幅の予測）と **C17**（日中の執行タイミング）は、target が符号付きの
per-event return ではない。Gate v2 の MRE も IR 上限もそこには定義されないので、
return の gate で RED と判定するのは**誤った物差しで測ること**になる。

⭐ **C17 は測定としては成立しうる**（パネルあたり 10,060 ペア・バー観測）。ただし
それは**コストの測定**であって edge ではなく、単独では取引可能な優位を生まない。
Gate v2 の economic 側に入力されるものである。

### CLOSED（3）

C08 / C21 / C22。いずれも裁定が明示的に閉じた family で、成果物に引用を持ち、
`assert_prospective` が実際に拒否した記録（`refused_by`）を伴う。

## 8. ⭐ Data-horizon gaps

| 構成 | 合計年数 | 1 パネル | PASS 到達 | MARGINAL 到達 |
| --- | --- | --- | --- | --- |
| 現在の 2 決定パネル | 3.992 | 1.996 | **0** | 0 |
| seen 全部（development 含む）を 2 分割 | 4.674 | 2.337 | **0** | 0 |
| fresh pool を足した場合（**読んでいない**） | 9.572 | 4.786 | **0** | **1**（C01） |

`share = 1.0` で計算した参考値: 2 パネルに必要 6.977 年、現有 4.674 年、不足 2.303 年。
**ただしどの候補もその仮定を使っていない。** 候補ごとの実際の必要年数:

| 設計型 | share | 必要パネル年数 | 2 パネル合計 |
| --- | --- | --- | --- |
| currency-level（C01, C04, C05） | 0.80 | 4.360 | 8.721 |
| cross-sectional 1 cell | 0.30 | 11.628 | 23.256 |
| cross-sectional 2 cells | 0.30 | 14.082 | 28.163 |
| cross-sectional 3 cells | 0.30 | 15.510 | 31.020 |

⭐ **断面を広げることは power の解決策にならない。** 通貨 7 本は events/year を
7 倍にするが有効独立方向はそこまで増えないので `effN/f` はむしろ縮む。

## 9. ML feasibility

C14 / C18 / C19 は性能を測っていない。設計だけで **RED**。理由は特徴量でも
モデルでもなく**独立標本の年数**で、cross-sectional な ML 設計は primary cell が
増えやすく必要パネル年数は 15.5 年に達する。「バーが 100 万本ある」ことは
independent sample の代わりにならない。

## 10. Remaining external-free research space

無料・公開で未取得のものは残る（株価指数、コモディティ、ボラティリティ指数、
追加の国債利回り）。しかし **horizon 条件には効かない** — conditioning 変数を
増やしても `effective_years = panel_years × share` は変わらず、primary cell が
増えれば必要年数はむしろ上がる。

## 11. Research ranking

**行わない。** GREEN が 0 であり、裁定は GREEN のみを ranking すると定める。

初稿はここに「horizon が解決した場合に最初に評価すべき順序」を 3 件書いていたが、
その根拠（機構の明快さ・強さ）は expected alpha についての定性的な事前判断であり、
成果物のどのフィールドにも存在しない。**レビューの指摘を受けて削除した。**

## 12. Suggested next tracks

**なし。**

## 13. Gate v2 audit

threshold は変更していない。見つかった性質は 1 件、分類は **design limitation**:
合成判定が要求する年数が現在のデータ地平を上回っている。これは統計的に正しい要求で、
緩めることでしか消せず、緩めることは禁止されている。

preflight が加える multiple-testing 補正については、**Gate v2 には無い追加要件**で
あることを明記した。two-panel 規則との二重補正（過剰）と conjunction power の
未補正（過小）は逆向きに働く。**どちらも相殺せずに開示する** — 相殺は threshold の
選択になり、threshold は凍結されている。
