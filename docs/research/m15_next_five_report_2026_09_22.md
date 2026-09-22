# 次の 5 本 — 最終比較報告（2026-09-22）

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Authority: 2026-09-22 Human + ChatGPT 裁定

> ## 結論を先に
>
> **5 本すべてが Stage 0（データ取得可能性）で止まった。** alpha は 1 本も測っていない。
>
> 原因は **この環境から FRED へ到達できないこと**である — 19 URL がすべて timeout した。
> 一方、federalreserve.gov / ecb.europa.eu / data.snb.ch / bankofcanada.ca /
> bankofengland.co.uk は HTTP 200 を返している。**FRED だけが届かない。**
>
> **これは「無料のデータが無い」ではない。** series は無料で存在する。
> だから status は `DATA_UNAVAILABLE_WITH_CURRENT_FREE_SOURCES` ではなく
> **`DATA_NOT_RETRIEVABLE_FROM_THIS_ENVIRONMENT_PROVIDER_UNAFFECTED`** とした。
> この区別を誤ると、次の判断が **不要な paid data 購入へ向かう。**

---

## 1. Identity

| | |
| --- | --- |
| 前 cycle PR | **#490 MERGED** — merge SHA **`60923fe`** |
| 本 cycle branch | `research/m15-next-five-freeze` |
| 新 freeze digest | 実行時 `e647629f…` → **現在 `2e805781…`**（下記 amendment） |
| 主な artefact | `artifacts/research/next_five/{stage0_probe,stage0_probe_direct,gate_calibration,development}.json` |
| alpha | **1 本も測っていない** |

### 凍結の修正（alpha を見る前に 1 度）

`FREEZE_AMENDMENT_PRE_ALPHA` / `AMENDED_PRE_ALPHA_NO_SIGNAL_HAD_RUN`。

`TRACK_STATUS_SUFFIXES` に
`DATA_NOT_RETRIEVABLE_FROM_THIS_ENVIRONMENT_PROVIDER_UNAFFECTED` を追加した。
既存語彙では「無料ソースが無い」としか書けず、**それは事実に反する**からである。
**signal は 1 本も走っていない時点での修正**であり、結果を見て語彙を変えたのではない。

---

## 2. #490 Merge（裁定 §A）

| 要求 | 実施 |
| --- | --- |
| cycle 全体に `CORRECTED_AFTER_RESULTS_WERE_SEEN…` を authoritative qualifier として保持 | ✅ `prereg.CYCLE_QUALIFIER`。track 単位ではなく**あらゆる数値**にかかる |
| C-1 / C-2 / C-3 を削除・弱化しない | ✅ test が 3 件の存在と C-2 の裁量記述を固定 |
| initial / execution / corrected の 3 段 provenance | ✅ `FREEZE_PROVENANCE`（`29ba80d6…` → `28100ebe…` → 現 digest） |
| T5 status 変更 | ✅ `T5_S26_POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE` |
| tests / contract-tests / mutation / CI green | ✅ 1,855 passed / CI green / **mutation 17/17** |
| merge SHA 記録 | ✅ **`60923fe`** |

---

## 3. Top-Five 前 cycle の最終 status

| | 候補 | 最終 status |
| --- | --- | --- |
| T1 | S05 株式 volatility | `NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（COST） |
| T2 | S06 原油 | `NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（T1 超の増分が両 span で負） |
| T3 | S02 金利 curve | `NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` / 長 span は `DATA_NOT_DECISION_GRADE` |
| T4 | S10 通貨伝播 | `NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（5 本で最悪 net） |
| **T5** | **S26 TIC flow** | **`POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE`** |

## 4. T5 の降格の解釈

**`MARGINAL_DEVELOPMENT_CANDIDATE` としては扱わない**（裁定 §4）。意味は 4 つに限られる:

1. observed net positive は**記録する**（近 span net +0.838 / 年 +8.57%）
2. **edge confirmed とはしない**（permutation p = 0.314、検出下限 1.321 > 実測 +0.838）
3. **development candidate へ昇格しない**
4. **fresh confirmation へ進めない**

**TIC / capital-flow の方向そのものは family closure にしていない**（§C）。
genuine historical vintage data・独立した flow source・実質的に異なる positioning / flow
情報が得られたときは、**それは新しい hypothesis であって、この track の救済ではない**。

---

## 5. Updated Candidate Inventory（裁定 §D）

全 28 候補 + 新規 2 = 30 を 7 分類へ。**覆えているかは主張ではなく計算で示す**（`coverage()`）。

| 分類 | 数 | 候補 |
| --- | ---: | --- |
| `CLOSED` | 12 | S03 S04 S08 S09 S11 S16 S17 S19 S21 S23 S24 S28 |
| `NOT_SUPPORTED` | 6 | S01 S02 S05 S06 S10 S13 |
| `POSITIVE_EXPLORATORY_NOT_DECISION_GRADE` | 1 | S26 |
| `DATA_NOT_DECISION_GRADE` | 0 | —（S02 長 span が sub-status として保持） |
| `DATA_UNAVAILABLE` | 1 | S18 |
| `PAID_DATA_ONLY` | 2 | S20 S22 |
| `UNTESTED` | 8 | S07 S12 S14 S15 S25 S27 **S29 S31** |

実行済み 7 本（Top-Five の 5 + S01 + S13）は次の execution set から除外した。

**裁定 §F が禁じた一般化は書いていない** — high-turnover / cross-asset / event / flow /
rates が「全部だめ」とは記録していない。今回 tested した scope だけを反映してある。

### 新しく足した 2 本と、その理由

既存 28 本のうち **未検証 eligible は 6 本しか残っていなかった**。しかもその 3 本
（S12 / S14 / S15）は FX 価格の変換で、裁定 §E が 2 番目に置いた「price を超える
incremental information」が**構造上ほぼ無い**。CORE PRINCIPLE の
"Then move to genuinely new information" に従い、無料・非価格・機構が明確で、
既存 family の言い換えでない source を 2 本足した。**alpha は 1 本も見ていない。**

- **S29 実体貿易 flow** — S26（US 証券投資 flow）とは主体も対象も違う
- **S31 公的外貨準備** — S25（自国通貨建て balance sheet）とも S26（民間証券投資）とも別

**足さなかった場合の counterfactual も記録してある**（`ranking.counterfactual_without_new_candidates`）:
rename filter で S14 が落ちるので残りはちょうど 5 本になり、**選定という行為自体が存在しなかった**。
新候補は選択肢を作るために足したのであって、特定の結論へ寄せるためではない。

---

## 6. New Ranking（裁定 §E）

10 次元を等重みで加算。**重みを自分で選ぶと、重みが結論になる**ので選ばない。
同点の決め方（TIEBREAK = 次元 2「price を超える incremental information」）は**先に**決めた —
根拠は前 cycle の実測、すなわち **T2 は gross が正でも T1 超の増分が両 span で負だった**こと。

**hard filter は点数より先に効く**（裁定 §I）。

| 順位 | 候補 | 計 | 次元 2 | 備考 |
| ---: | --- | ---: | ---: | --- |
| 1 | **S29** 実体貿易 flow | 45 | 5 | breadth が構造的に大きい（8 通貨すべてが公表） |
| 2 | **S25** 中銀 balance sheet | 43 | 5 | breadth 中程度 |
| 3 | **S27** 中銀 communication tone | 39 | 5 | 再現性が最低（Stage 0 で落ちる公算が最大と宣言） |
| 4 | **S31** 公的外貨準備 | 38 | 5 | **breadth の低さを事前に宣言** |
| 5 | **S07** 信用 spread | 28 | 4 | **TIEBREAK で S15 に勝った** |
| 6 | S15 regime 遷移 | 28 | 1 | 価格由来 |
| 7 | S12 dispersion | 23 | 1 | 価格由来・breadth 最低 |
| — | S14 多 horizon 価格 state | 26 | 1 | **filter 落ち** |

**S14 は点数では S12 より上だが除外した。** Track 1 が同じ入力（5/20/60 日 price state +
trend age）の線形結合を走らせて gross 負だったので、裁定 §I の
「prior failed family の rename ではない」を満たさない。**filter は点数より先に効く。**

**`low turnover 自体を alpha source にしない`** を実装してある — 次元 3 は
`persistence_is_mechanistic` が真のときしか高得点にならない。
「平滑化して遅くした signal」はここで点を取れない。

## 7. New Top Five

**5 本すべてが非価格の外部情報**である。前 cycle は 5 本中 4 本が価格に隣接していた。

| | 候補 | 機構 | 周期 | primary span | 事前宣言した弱点 |
| --- | --- | --- | --- | --- | --- |
| U1 | S29 | 実需の決済通貨需要 | 月次 | long | 改訂留保（現行 vintage） |
| U2 | S25 | QE/QT の相対ペース | 週〜月次 | long | breadth 中程度 |
| U3 | S27 | 声明 tone の先行性 | 事象 | recent | **Stage 0 で落ちる公算が最大** |
| U4 | S31 | 公的部門の実際の為替売買 | 月次 | long | **breadth 小（CHF/JPY のみ能動）** |
| U5 | S07 | funding stress → 安全通貨 | 日次 | recent | **5 本で最も不利**・S05 と同じ向き |

### primary span を signal の周期で決める（新規則）

前 cycle の T5 は月次 signal を 555 日・独立状態 24 個で測り、**その窓の検出下限 1.321 が
実測 +0.838 を上回った**。設計段階で負けていた。今回は周期で primary を決める。

| span | 検出下限 MDE95 |
| --- | ---: |
| long（17.2 年） | **0.466** |
| recent（4.8 年） | 0.893 |
| （参考）前 cycle T5 の窓（2.2 年） | 1.321 |

**月次 signal を長 span で判定することで、検出力がおよそ 3 倍になる。**

### rename gate（結果を見る前に閾値を置いた）

| track | 比較対象 | 閾値 | 超えたら |
| --- | --- | ---: | --- |
| S07 | S05（T1）の VIX shock score | 0.8 | **結果にかかわらず `RENAME_OF_A_CLOSED_TRACK`** |
| S31 | S26（T5）の TIC flow score | 0.8 | `RENAME_OF_A_PRIOR_TRACK` |
| S25 | S31 の reserves score | 0.8 | `RENAME_WITHIN_THIS_CYCLE` |

S07 は **向きが S05 と同じ**（risk-off → 安全通貨）で情報源だけが違う。
だから「違う」と主張する以上、**測って示す**ことを事前に約束してある。

---

## 8. Null-Calibrated Gate Design（裁定 §G）

### 旧 gate は降格した

前 cycle の 3 条件 gate（gross > 0 / incremental IC > 0 / net > 0）は
**帰無のもとで 42% 通った**。しかも通過率は track ごとに違い、**turnover が低いほど高い**
（net > 0 が cost drag 超えを要求するため）。同じ規則が track によって全く違う厳しさで
効いていた。

→ `DEMOTED_TO_DIAGNOSTIC_NOT_A_SELECTION_GATE`。**報告はするが、通ったことを根拠に進まない。**

### 新しい hard gate

`PERMUTATION_SEPARATION` — primary span で **net > 0 かつ circular-shift permutation
p ≤ 0.05**。circular shift を使うのは、行を混ぜると turnover が跳ね上がり
「回転が少ないから cost を払わない」という性質まで壊れるからである。

**多重性を事前に書いてある** — 5 本を同じ gate に通すので、**帰無でもいずれか 1 本が
5% を切る確率は約 23%**。1 本通ったことを「edge が見つかった」とは書かない。

### 凍結時点で測った帰無通過率

各 track が**宣言した周期**と同じ持続性を持つ零情報 signal を引き、凍結した執行層に通し、
凍結した gate に当てた。**候補のデータは一切使っていない**（signal-blind）。

| track | primary span | **旧 gate の帰無通過率** | 内訳 gross>0 | incIC>0 | net>0 | 零情報 null の net SR p95 | MDE95 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| U1 S29 | long | **25.3%** | 0.39 | 0.51 | 0.31 | +0.273 | 0.466 |
| U2 S25 | long | **28.7%** | 0.53 | 0.61 | 0.34 | +0.308 | 0.466 |
| U3 S27 | recent | **20.7%** | 0.45 | 0.41 | 0.34 | +0.503 | 0.893 |
| U4 S31 | long | **27.3%** | 0.48 | 0.49 | 0.36 | +0.236 | 0.466 |
| U5 S07 | recent | **9.3%** | 0.54 | 0.42 | **0.11** | +0.226 | 0.893 |

（零情報 signal 150 本 × 5 track、seed 20260922。**候補のデータは一切使っていない。**）

**裁定 §G の前提が実測で確認された — 同じ規則が track によって 3 倍違う厳しさで効いている**
（9.3% 〜 28.7%、幅 19.3 ポイント）。

そして**厳しさを決めているのは signal の質ではなく cost drag** である。
内訳を見ると `gross > 0` と `incIC > 0` はどの track も 0.4〜0.6 とほぼ coin flip なのに、
`net > 0` だけが U5 で **0.11**、遅い 4 本で 0.31〜0.36 と大きく割れている。
U5 は日次 signal で turnover が高く、cost drag が帰無の net をほぼ確実に負にするからである。

> **U5 の 9.3% を「良い gate」と読んではならない。**
> 通りにくいのは signal を見分けているからではなく、**cost が重いから**である。
> 同じ理由で、前 cycle の T5 が 42% だったのは turnover が 5 本で最小だったからであって、
> T5 の signal が良かったからではない。
> **通過率は signal の質ではなく book の回転を測っている。**

前 cycle の `M-001` が置いた運用規則（**通過率が 20% を超える gate は、gate ではなく
足切りとして扱う**）に照らすと、**5 本中 4 本が 20% を超える**。旧 gate の降格は正しかった。


---

## 9. Nuisance Sensitivity Design（裁定 §H）

前 cycle は `max_staleness_days` を**結果を見た後に選び**、その値が試した 9 点の
**net Sharpe 最大**だった。今回は集合を先に決め、**全点を報告する**。

| 定数 | primary | 感度集合 | なぜ economic meaning を持たないか |
| --- | ---: | --- | --- |
| `max_staleness_days` | 75 | 45 / 60 / 75 / 90 / 120 | 「古すぎる」の線は事務上の取り決め |
| `z_window` | 252 | 126 / 252 / 504 | 標準化の窓長は signal の意味を変えない |
| `change_window_months` | 12 | 6 / 12 / 24 | 「変化」の定義幅 |
| `implementation_tolerance_band` | 0.10 | 0.05 / 0.10 / 0.20 | 執行側の都合 |

**集合の外の値は実装が拒否する**（`ValueError`）。結果後に best point を選ぶ経路を作らない。

---

## 10. 各 track の結果

**共通:** すべて Stage 0 で止まったので、gross / net / IC / turnover / cost / stability /
breadth / concentration / leverage / capacity は **1 つも測っていない**。
測れているのは検出力（MDE95）と gate の帰無通過率だけである。

| 項目 | U1 S29 | U2 S25 | U3 S27 | U4 S31 | U5 S07 |
| --- | --- | --- | --- | --- | --- |
| mechanism | 実需決済 | QE/QT 相対 | 声明 tone | 公的為替売買 | funding stress |
| data | 月次貿易収支 | 中銀総資産 | 中銀テキスト | 月次外貨準備 | HY OAS |
| timing | m+2 月末以降 | 公表 +2 営業日 | 公表 +1 営業日 | m+1 月末以降 | 公表 +2 営業日 |
| **power (MDE95)** | 0.466 | 0.466 | 0.893 | 0.466 | 0.893 |
| **null gate pass rate** | 25.3% | 28.7% | 20.7% | 27.3% | 9.3% |
| 検証できた通貨 | **0** / 3 | **2** / 3 | **2** / 3 | **1** / 3 | **0** / 1 |
| gross / net / IC | 未測定 | 未測定 | 未測定 | 未測定 | 未測定 |
| turnover / cost | 未測定 | 未測定 | 未測定 | 未測定 | 未測定 |
| breadth / concentration | 未測定 | 未測定 | 未測定 | 未測定 | 未測定 |
| leverage / 5% / 10% | 未測定 | 未測定 | 未測定 | 未測定 | 未測定 |
| **verdict** | `DATA_NOT_RETRIEVABLE_FROM_THIS_ENVIRONMENT_PROVIDER_UNAFFECTED` | 同左 | 同左 | 同左 | 同左 |

### Stage 0 で実際に何が起きたか

**到達したホスト:** federalreserve.gov / ecb.europa.eu / data-api.ecb.europa.eu /
data.snb.ch / bankofcanada.ca / bankofengland.co.uk
**到達しなかったホスト:** fred.stlouisfed.org（**19 URL すべて timeout**）

**provider のカタログで検証できた series:**

| 通貨 | series | 出典 |
| --- | --- | --- |
| CHF 総資産 | SNB cube `snbbipo` D0=`T0` | dimension 一覧で確認 |
| CHF 外貨準備 | SNB cube `snbbipo` D0=`D` | 同上 |
| CAD 総資産 | BoC valet `V36651` | group `B1_MONTHLY` のラベルで確認 |

**推定が外れたもの（provider 自身が教えてくれた）:**

- BoC `V36612` は自己申告で **「Treasury Bills」** — 総資産ではなかった
- BoE `LPMB8LU` は **HTTP 200 で HTML のエラーページ**を返した
- ECB ILM `A050100` は **「Main refinancing operation」** — 総資産ではなかった
- ECB ILM は資産・負債の**個別項目しか公開しておらず、総資産の系列が無い**

### 2 通貨で走らせなかった理由

**2 通貨の cross-section は demean 後に互いの鏡像になり、breadth 1 になる。**
それは前 cycle の T5 を決定不能にしたのと同じ構造である。
凍結した signal は cross-section を要求しているので、**通貨数を下げて走らせることは
実行ではなく凍結の変更**にあたる。だからしなかった。

### この過程で見つけて直した 2 つの欠陥

1. **`classify_failure` に `HTTPError` の分岐が無かった。** 404 も 403 も
   `LOCAL_ENVIRONMENT_FAILURE` に落ち、**`HTTP_STATUS` はどの経路からも到達できない
   死んだ分類**だった。保守側へ倒したつもりで、「相手が『そこには無い』と答えた」という
   事実を消していた。修正し、6 つの status code で test を置いた。
2. **probe が「HTTP 200 だが HTML」を到達 OK と記録していた。** 存在しない series code に
   対して BoE が 200 でエラーページを返し、それを「取れた」と記録した。
   **到達と取得は別の事実**なので、中身を見て弾くようにした。

---

## 11. 裁定の 5 つの問いへの回答

### 1. absolute net edge を示した source はあるか

**無い。本 cycle では 1 本も測っていない。**
前 cycle まで遡っても、**正の側でノイズ帯（MDE95）の外に出た測定は 1 つも無い**。
T5 の +0.838 が唯一の net 正だが、その窓の検出下限 1.321 を下回っている。

### 2. price information への incremental value はあるか

**本 cycle では測っていない。**
前 cycle で測れた範囲では、**T2 は T1 を超える増分が両 span とも負**で、
独立な情報源として支持されなかった。T1 / T3 / T5 の incremental IC は符号が正だったが、
**個別の有意性検定をしていない**ので「ある」とは書けない。

### 3. candidate は null exploration を超えているか

**超えていない。** 本 cycle は Stage 0 で止まったので、超える機会が無かった。
前 cycle の T5 は permutation p = 0.314 で、**零情報 null の 95 パーセンタイル +1.13 の内側**。
さらに、前 cycle の gate 自体が帰無で 42% 通る代物だった —
**「gate を通った」という事実が null exploration を超える証拠にならない**ことが、
今回の設計変更（§8）の出発点である。

### 4. realistic risk で年 5% が射程か

**本 cycle では判定不能。** 測定が無いので capacity も無い。
前 cycle の T5 について機械的に解けば target vol 5.97% / portfolio gross 1.46x /
margin 利用率 7.3% で到達するが、**それは net Sharpe 0.838 を真値としたときの計算**であり、
その前提は検証されていない。**「前提が本物なら届く」であって「届く」ではない。**

### 5. 次に必要なのは free / paid / new mechanism / execution engineering のどれか

**どれでもない。今いちばん効くのは `data access engineering` である。**

本 cycle の結果はこう読むべきである — **候補が尽きたのではなく、候補に到達できなかった。**
5 本とも機構は明確で、データは無料で存在し、timing も防御できる設計になっていた。
止めたのは **FRED への network 到達性**という、研究の中身とは無関係な要因である。

その根拠:

- FRED の 19 URL がすべて timeout する一方、6 つの公式ホストは HTTP 200 を返した
- provider のカタログを引けば series は特定できた（CHF と CAD で実際に成功している）
- つまり **可用性の問題ではなく、経路と手間の問題**である

したがって優先順位は:

1. **`data access engineering`** — FRED への到達経路の確保、または各 provider の
   カタログから series を特定する作業。**これが解ければ 5 本とも即座に実行できる。**
2. `execution engineering`（turnover 設計）— 前 cycle の
   「4 本とも gross は正なのに cost に負けた」への対処。**ただし前 5 本の救済としてではなく、
   新しい candidate の設計原則として**（裁定 §B）
3. `paid information` — **今は要らない。** 必要な series は無料で存在する。
   ここで paid へ進むのは、到達性の問題を購買で解こうとすることになる
4. `new mechanism` — 候補プールは細っているが（未検証 eligible は 6 本だった）、
   まだ尽きてはいない

---

## 12. この報告が主張していないこと

- **「これらの機構が否定された」とは言っていない。** 1 本も測っていない
- **「無料データが無い」とは言っていない。** series は無料で存在し、到達できないだけである
- **「候補が尽きた」とは言っていない。** 未検証は 8 本残っている（うち 3 本は価格由来で弱い）
- **前 5 本の救済はしていない**（裁定 §B）。低 turnover 版も horizon smoothing も走らせていない
- **T5 の追加実行もしていない**（§C）。TIC / capital-flow を family closure にもしていない
- **programme-level の判断はしていない**（§55 / §O）。`FX research paused` は設定していない
- **6 本目へ進んでいない。** fresh / paid / 非線形 ML / multi-source optimization /
  paper-forward のいずれにも触れていない
