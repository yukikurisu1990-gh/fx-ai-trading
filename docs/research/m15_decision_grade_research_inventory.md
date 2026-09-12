# FX Spot Decision-Grade Research Inventory — 結果

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Status: **`CURRENT_SEEN_DATA_FX_RESEARCH_SPACE_EXHAUSTED`** ·
**`ADDITIONAL_INDEPENDENT_HISTORY_WOULD_OPEN_PASS_REGION`**

成果物は `artifacts/research/feasibility/inventory.json`。**signal・return・sign・
IC・Sharpe・p 値・PnL を一切計算していない。** 設計統計だけである。

---

## 0. 一行で

**GREEN は 0。** 22 の研究方向を preflight にかけた結果、RED 14 / BLOCKED 2 /
CLOSED 6 / AMBER 0 / GREEN 0。

理由は個々の仮説ではなく**データ地平**である。Gate v2 の合成判定は
`(z(k)/IR_max)² = 3.488 年`（primary cell 1 個のとき）の有効観測を要求するが、
`effective_years = panel_years × share` という恒等式により**パネル長を超えられない**。
決定パネルは **1.996 年**。したがって share・頻度・コスト・分散のどの仮定を
置いても horizon 条件は満たせない——これは意見ではなく算術である。

**seen data をすべて足しても届かない**（4.674 年を 2 パネルに割ると 2.337 年）。
2 パネル分には **6.977 年**が要り、**2.303 年足りない**。

---

## 1. Pass-Region Preflight

仕様は `docs/design/m15_pass_region_preflight.md`、実装は
`scripts/research/feasibility/preflight.py`。**Gate v2 の threshold は変更していない**
（すべて import している）。

Gate v2 の 2 条件を dispersion について解くと区間になる。

    σ ∈ [ MRE·√f / IR_max ,  MRE·√effN / z(k) ]

区間が空でない条件は `effN ≥ (z(k)/IR_max)²·f`。**MRE も σ も cost も消える。**

| primary cells | z(k) | 必要有効年数 |
| --- | --- | --- |
| 1 | 2.8016 | **3.488** |
| 2 | 3.0830 | 4.224 |
| 3 | 3.2356 | 4.653 |

残りの条件は**頻度の帯**を与える: event floor が下限（`f ≥ 60/years`）、
stressed cost が上限（`f ≤ 300/(2c − 2)`）。**設計は「稀すぎて判定できない」ことも
「頻繁すぎて払えない」こともある。**

cost は economic 条件にしか入らない。下げても statistical は動かない（v1 の逆転を
構造的に排除）。synthetic test 6 本で固定。

## 2. Track 2 Retrospective Check — preflight は止められたか

**止められた。** Track 2 の凍結設計（panel 1.996 年、primary cell 3、パネル 2 枚）を
入れると、**signal を一切見ずに** `NO_DECISION_GRADE_PASS_REGION`、binding は
`horizon`。しかも:

* 頻度 30〜250/年のどれでも、
* コスト 0〜6 bp のどれでも、
* **観測が完全独立（share = 1.0）でも**、
* **primary cell が 1 個でも**（必要 3.488 年 > 1.996 年）

refuse される。必要だったのは有効 4.653 年で、当時あったのは 1.597 年。
**Track 2 の verdict は変更していない**（`NON_USD_SURPRISE_DATA_NOT_DECISION_GRADE_SKIP`
のまま）。これは diagnostic である。

## 3. 現在の seen data 棚卸し

| span | 期間 | 役割 | 読んだ主体 |
| --- | --- | --- | --- |
| momentum_2021_2023 | 2021-04-26 … 2023-04-25 | 決定パネル | exploratory momentum round |
| supplemental_2023_2025 | 2023-04-26 … 2025-04-24 | 決定パネル | supplemental historical replication |
| **development_2025** | **2025-04-25 … 2025-12-28** | **seen だがどちらの決定パネルにも入っていない** | Track A R1 |

* **通貨/ペア**: G10 8 通貨、`PAIRS_20`。
* **粒度**: M1 から導出した M15（bid/ask OHLC、spread、pip_size、rollover、session）。
  M1 生バーは R1 の窓のみ。**tick volume は決定パネルのキャッシュに列として存在しない。**
* **event calendar**: FOMC / ECB / BoJ / RBA の公式発表日（無料・機械可読）。
  BoE / BoC / RBNZ / SNB は自動取得経路をすべて拒否する（既知の被覆限界）。
* **consensus**: 無料アーカイブ（Forex Factory cache、83,427 行、actual/forecast/previous）。
  **時刻は使えない**（同定が 19 時間幅）。日付は +5h 補正で公式 103/103 一致。
* **rates**: BIS 政策金利、FRED / ALFRED vintage、Cleveland Fed nowcast。
* **positioning**: CFTC COT（取得済み、検定済み）。
* **cross-asset**: 未取得。無料公開ソースは利用可能。

## 4. ⭐ 未使用だが既に seen のデータ（§17）

**`development_2025`（2025-04-25 … 2025-12-28、0.68 年）**が該当する。

| 項目 | 内容 |
| --- | --- |
| span | 2025-04-25 … 2025-12-28 |
| なぜ決定パネルに入っていないか | Track A R1 の authorised read の対象であり、R1 の成果物専用として扱われてきた。2 枚の決定パネルは別ルート（momentum / supplemental）で構成された |
| contamination status | **`EXPLORATORY_SEEN_DATA`**。protected ではない。OOS でも dead window でも forward epoch でもない |
| independent horizon を増やすか | **増やす。** 2021-04-26 … 2025-12-28 は**連続**で 4.674 年になる |
| development data になりうるか | 汚染の観点では障害が見当たらない。ただし**判断事項として残す** |

**ただし、これを足しても pass region は開かない。** 4.674 年を 2 パネルに割ると
**2.337 年**で、必要 3.488 年に届かない。**勝手にパネルへ追加していない。**

## 5. Protected data boundary

**読んでいない**: fresh pool `2016-06-02 … 2021-04-25` / historical OOS slice
（`2025-12-29` 以降）/ dead window / forward Formal Confirmation epoch。
§7 の counterfactual は**マニフェストが既に持つ 2 つの日付の引き算**だけで、
protected span の中身は一切読んでいない。

## 6. Candidate universe と preflight 表

コストは Track 3 の実測 market-order 往復 **2.58 bp**（1 ペア）と、通貨バスケット
実装の gross exposure 1.29 を掛けた **3.328 bp**。variance は必要な候補のみ
signal-blind な出所を宣言（unconditional / frozen design statistic）。

| Candidate | Mechanism | N/panel | effective years | MRE bp | binding | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| C01 central bank decision response | mandate-bound repricing | 48 | 1.597 / 3.488 | 15.000 | horizon（+ event floor） | RED |
| C02 macro surprise intraday | announcement repricing | — | — | — | timestamp unusable | **BLOCKED** |
| C03 session handover relative | regional participation change | 1509 | 1.597 / 3.488 | 2.897 | **economic (too frequent)** | RED |
| C04 benchmark fix flow | mandated transaction at a fix | — | — | — | Track 1 suspended | **CLOSED** |
| C05 month-end rebalancing flow | calendar-bound rebalancing | — | — | — | Track 1 suspended | **CLOSED** |
| C06 factor-neutral residual value | idiosyncratic unwind | 3521 | 0.599 / 3.488 | 2.670 | horizon | RED |
| C07 cross-sectional dispersion state | idiosyncratic vs common driving | 3521 | 0.599 / 4.224 | 2.670 | horizon | RED |
| C08 currency rank persistence | relative strength | — | — | — | H-003 と同形 | **CLOSED** |
| C09 yield-differential change | policy-path repricing | 3521 | 0.599 / 3.488 | 2.670 | horizon | RED |
| C10 equity risk regime | risk-on/off funding flows | 3521 | 0.599 / 4.224 | 2.670 | horizon | RED |
| C11 commodity link response | terms of trade | 1509 | 0.599 / 3.488 | 2.897 | horizon | RED |
| C12 volatility regime transition | volatility clustering breaks | 3521 | 0.599 / 4.224 | 2.670 | horizon | RED |
| C13 timeframe disagreement | horizon disagreement | — | — | — | simple HTF conditioning 同形 | **CLOSED** |
| C14 latent regime state | unobserved regime | 3521 | 0.599 / 4.653 | 2.670 | horizon | RED |
| C15 movement magnitude forecast | volatility persistence | 3521 | 0.599 / 3.488 | 2.670 | horizon | RED |
| C16 horizon selection | absorption speed varies | 3521 | 0.599 / 4.653 | 2.670 | horizon | RED |
| C17 intraday execution timing | stable intraday spread shape | 10060 | 0.599 / 3.488 | 2.559 | horizon | RED |
| C18 ML currency ranking | nonlinear state combination | 3521 | 0.599 / 4.653 | 2.670 | horizon | RED |
| C19 ML take/skip gate | conditional cost-adjusted return | 3521 | 0.599 / 4.224 | 2.670 | horizon | RED |
| C20 broker order flow | crowded retail unwind | — | — | — | broker 認証が未承認 | **BLOCKED** |
| C21 futures positioning | speculative crowding | — | — | — | COT tested cells | **CLOSED** |
| C22 carry level | funding risk premium | — | — | — | policy-rate proxy carry | **CLOSED** |

### GREEN candidates

**なし。**

### AMBER candidates

**なし。** MARGINAL に届く候補も存在しない（horizon が全候補で不足するため）。

### RED candidates（14）

C01 / C03 / C06 / C07 / C09 / C10 / C11 / C12 / C14 / C15 / C16 / C17 / C18 / C19。

うち **C01 は event floor にも**（48 < 60）、**C03 は経済条件にも**引っかかる
（MRE 2.897 に対し必要 7.156 — 1 年に 756 回建てる設計は、参照コストの 2 倍を
賄うだけの per-event 効果を要求できない）。残りは horizon 単独で落ちる。

### BLOCKED candidates（2）

* **C02 macro surprise intraday** — 無料アーカイブの時刻が 19 時間幅でしか同定
  できず、非 USD の統計機関に無料の公式リリース時刻 calendar が無い。
* **C20 broker order flow** — 認証付き broker endpoint が必要で未承認。

### CLOSED candidates（6）

C04 / C05（Track 1 suspended を尊重）、C08（H-003 同形）、C13（simple HTF
conditioning 同形）、C21（COT tested cells）、C22（policy-rate proxy carry）。

## 7. ⭐ Data-horizon gaps

| 構成 | 合計年数 | 1 パネルあたり | horizon 条件 |
| --- | --- | --- | --- |
| 現在の 2 決定パネル | 3.992 | **1.996** | **不可** |
| **seen data 全部**（development を含む）を 2 分割 | 4.674 | **2.337** | **不可** |
| fresh pool を足した場合（**counterfactual、読んでいない**） | 9.572 | **4.786** | **可** |

* 2 パネル分に必要な seen 年数: **6.977 年**
* 現在の seen 年数: **4.674 年**
* **不足: 2.303 年**

そして **どの仮定でも届かない**ことを算術で確認した。
`effective_years = panel_years × share` なので、share を 0.1 から 1.0、頻度を
12 から 1764 まで振っても最大値は **1.996** で、必要 3.488 に届かない。

## 8. Years-to-decision（候補別）

RED 14 候補すべてについて `years_to_decision` を成果物に出力している。
`effective_n_share` が小さい cross-sectional 設計ほど必要パネル年数は長い。

| 設計型 | share | 必要パネル年数 / パネル | 2 パネル合計 |
| --- | --- | --- | --- |
| currency-level（C01, C03） | 0.80 | 4.36 | 8.72 |
| cross-sectional 1 cell（C06, C09, C11, C15, C17） | 0.30 | 11.63 | 23.26 |
| cross-sectional 2 cells（C07, C10, C12, C19） | 0.30 | 14.08 | 28.16 |
| cross-sectional 3 cells（C14, C16, C18） | 0.30 | 15.51 | 31.02 |

⭐ **cross-sectional 設計は horizon 条件に対して不利である。** 通貨断面は
events/year を 7 倍にするが、有効独立方向は 7 倍にならないので、
`effN/f` はむしろ縮む。**断面を広げることは power の解決策にならない。**

## 9. ML feasibility

C14 / C18 / C19 は性能を測っていない。設計だけで見て、いずれも **RED**。
理由は特徴量でもモデルでもなく、**独立標本の年数**である。cross-sectional な
ML 設計は primary cell が増えやすく（3 cell で必要 4.653 年）、`effN/f` も小さいので
**必要パネル年数は 15.5 年/パネル**に達する。「バーが 100 万本ある」ことは
independent sample の代わりにならない。

## 10. Remaining external-free research space

無料・公開で未取得のものは残っている（株価指数、コモディティ、ボラティリティ指数、
国債利回りの追加系列）。しかし **それらは horizon 条件に効かない**——
conditioning 変数を増やしても `effective_years = panel_years × share` は変わらず、
primary cell が増えれば必要年数はむしろ上がる。**外部データの追加では開かない。**

## 11. Research ranking

GREEN が 0 なので **ranking しない**（§32 は GREEN のみを ranking すると定める）。

参考として、**horizon が解決した場合に**最初に評価すべき順序の材料だけ記す
（performance は一切使っていない。broad-family information gain と機構の強さのみ）:
C09（yield-differential change、機構が最も明快で 1 cell）、C06（factor-neutral
residual、広い hypothesis class を一度に閉じられる）、C01（central bank decision、
event 数さえ足りれば機構は最も強い）。**これは提案ではなく、材料である。**

## 12. Suggested next tracks

**なし。** GREEN が 0 なので、無理に family を生成しない。

## 13. Gate v2 audit（§41）

Inventory の実行中に Gate v2 の threshold を変更していない。見つかった性質は 1 件で、
分類は **design limitation**（bug でも policy issue でもない）:

> 合成判定は `(z(k)/IR_max)²` 年の有効観測を要求する。これは「年次 IR を 1.5 以下と
> 主張しつつ 80% の検出力を持つには数年分の独立観測が要る」という統計的に正しい
> 帰結であり、gate の誤りではない。ただし**その要求が現在のデータ地平を上回っている**。

閾値を動かせば preflight も同じだけ動く（定数を import している）ので、
**この制約は緩めることでしか消せず、緩めることは禁止されている。**
