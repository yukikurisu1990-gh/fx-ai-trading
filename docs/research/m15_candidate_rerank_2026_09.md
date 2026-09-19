# 候補 inventory 全面 rerank と signal-blind feasibility（2026-09-19）

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Human + ChatGPT 裁定（2026-09-19）§10–§18 による。#484 の 28 候補 / 21 distinct directions を、
T-R・T-R2・T-V の実行結果と family closure を織り込んで全面的に評価し直す。
古い ranking はそのまま使わない。

---

## 0. 確定した status（§2–§8）

| track | 正式 status |
| --- | --- |
| T-R fast | `MARKET_YIELD_REPRICING_FAST_5D_MEASURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` |
| T-R2 slow | `MARKET_YIELD_SLOW_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT` |
| family | `MARKET_YIELD_REPRICING_SIMPLE_DIRECTIONAL_FAMILY_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT`（scope 限定 CLOSED） |
| T-V | `REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT` |

closure が**閉じる**のは public daily sovereign-yield data / simple fast directional repricing /
simple slow directional repricing / subsequent G10 FX directional return の 4 点。
**閉じない**のは OIS・market-implied policy path・rate futures・intraday rate repricing・curve shape・
term-premium information・rates options・distributional policy-path information の 8 つ（いずれも未観測）。

## 1. rerank を支配したのは mechanism ではなく **span** である

今回いちばん重要な発見は、どの候補についてでもない。**検出力**についてである。
両側 5%・検出力 80% で分離できる年率 Sharpe は概ね `2.80 / √年数`:

| span | 年数 | 分離できる net Sharpe |
| --- | --- | --- |
| seen M15 corpus `2021-04-27 … 2025-12-26` | 4.69 | **1.29** |
| ECB 日次 FX `1999-01-04 … 2016-06-01`（T-V で seen 化） | 17.41 | 0.67 |
| **上記 2 つ（保護 pool を挟んで disjoint）** | **22.10** | **0.60** |

現実的な単一 source の edge は net Sharpe 0.2〜0.5。
**4.7 年の seen corpus では、その帯域のどこも 0 と区別できない。**
T-R も T-R2 も正の gross を出しながら何も決められなかったのは、これが理由である。

したがって候補の価値は「prior の強さ」より **「情報源に長い無料履歴があり、読んでよい FX 履歴と突き合わせられるか」**
で決まる。これは mechanism についてのどんな判断よりも順位を動かす。

さらに: **2 つの span は保護 pool を挟んで disjoint** である。凍結した rule に
**両方で符号一致を要求できる**。同じ総年数を 1 本の span で持つより遥かに強い development 証拠であり、
本 programme のどの track もこれを持っていなかった。

## 2. reachability は仮定せず**実測**した（重要な副産物）

#484 の inventory は cross-asset 候補の大半の source を FRED としていた。
**FRED はこの環境から到達不能**である（3 回試行: connection reset 1、45 秒 timeout 2。同時刻 ECB は正常応答）。

inventory の source 欄を額面どおり受け取っていたら、**cross-asset 方向全体が環境障害で消えていた。**
実際には消えない — **一次公表者が同じ系列を直接配信している**からで、しかも aggregator より provenance が良い:

| host | 状態 | 証拠 |
| --- | --- | --- |
| `fred.stlouisfed.org` | **UNREACHABLE** | 3 回失敗 |
| `cdn.cboe.com` | REACHABLE | `VIX_History.csv` 200、**1990-01-02 から 9,276 営業日** |
| `www.eia.gov` | REACHABLE | 公式 US 原油 spot 系列 200 |
| `home.treasury.gov` | REACHABLE | 2Yr・10Yr を含む全 curve、probe した 1995 年まで全年 200 |
| `api.statistiken.bundesbank.de` | REACHABLE | 日次 10y 系列 200 |
| `www.bankofcanada.ca` | REACHABLE | Valet 10y benchmark 200 |
| `data.snb.ch` | REACHABLE | curve cube 200 |
| `data-api.ecb.europa.eu` | REACHABLE | T-V で使用済み |
| `stats.bis.org` | REACHABLE | policy rates / DSR / REER すべて 200 |
| `query1.finance.yahoo.com` | REACHABLE だが**不使用** | v8 は 200 だが redistributor。§41 は official / exchange を上位に置き、両方到達可能なので license 曖昧性を負う理由がない |
| `dataservices.imf.org` | UNREACHABLE | DNS 解決失敗 |

## 3. 新証拠で ranking から外れた候補（§11）

| ID | 旧順位 | 処遇 | 理由 |
| --- | --- | --- | --- |
| **S01** front-end 金利 repricing | **1** | 実行済み CLOSED | T-R / T-R2 として実行、両方 NOT_SUPPORTED、family closure |
| **S13** 実質為替 valuation | **2** | 実行済み CLOSED | T-V として実行。cost ではなく **incremental IC −5.57pp (t −3.34)** |
| **S03** 会合日 repricing（T-E 主） | 4 | **除外** | §4 の詳細は下記 |
| **S04** 指標発表日 repricing（T-E 副） | 6 | **除外** | 同上 + 非 US の無料公式時刻付きカレンダーが存在しない |
| **S16** 金利 × vol 閾値 | 9 | 除外 | S01 の増分。自身の順序規律で「S01 の線形 baseline が正でない限り検定しない」。baseline は 2 回とも正にならず family は closed |
| **S08** 金利 vol 状態 | 18 | 除外 | 同上 |
| **S17** event 日 cross-asset | 15 | 除外 | S03・S04 の増分で、両方除外 |
| **S28** breakeven repricing | 12 | **closure 内** | breakeven は public sovereign yield 2 本の差であり、rule は simple directional repricing。data も rule も closure が覆う。加えて breadth 1〜2 |
| S14 / S15 / S10 / S12 | 11/17/16/19 | 大幅 penalty | price-only または conditioning のみ。H-023・H-024・H-003・H-017 と重複 |

既存の除外（S11・S19・S23・S24 = 改名/救済、S09 = 構造的不成立、S21 = 停止中 family、
S18/S20/S22 = データ不可）は**そのまま維持**する。

### S03 / T-E の再評価 — §15 が求めた検査に通らない

§15 は「T-R の failed signal に event filter を掛けただけではないか」を確認せよと指示している。**そのとおりだった。**

- S03 の方向情報は **2 年金利の当日変化** — closure が覆う *public daily sovereign-yield の simple directional repricing* そのものである。
  無料データで得られる会合日の測度は日次変化なので、event で条件付けることは
  **同じ closed な量のきれいな部分集合を選ぶ**ことであって、別の情報を供給することではない。
- closure は **intraday rate repricing を閉じていない**。しかし intraday 金利は無料では取得できない。
  **本当に新しくなる版は、作れない版である。**
- opportunity 層は既に測定済みで、**cost advantage は無いと分かっている**:
  H-018/H-019 は event 日の絶対変動が 1.33〜1.63 倍である一方、**spread は 1.01〜1.05 倍広く**、
  round trip を超える日の比率は **1.00** と記録している。H-019 自身の status は
  「a forward-known opportunity anchor with **nothing to point it at**」。
  そこに closed な金利 signal を向けても、この事実は変わらない。
- 検出力: 無料で取得できる中銀は 4 行のみ（Fed・ECB・BoJ・RBA）。
  **GBP・CAD・NZD・CHF には anchor が無い。** 年 34.4 事象、seen corpus で約 160 事象、
  net 0.5 に事象あたり約 12 bp が必要。

→ **T-E は選択しない。** §28 に従い `EVENT_REPRICING_DATA_NOT_DECISION_GRADE` として記録し、backtest しない。
これは「event 情報に価値が無い」ではない（§12）。**方向 source が closed でないものに替わるまで保留**である。

### S02 の再評価（§16 が求めた明示的再評価）

#484 で T-E と競っていた S02 は、**§4 の closure が curve shape を明示的に閉じていない**ので生き残る。
言い換えによる除外はできない。ただし prior は下がる:

- 同じ情報源（sovereign yield）の *level* が 2 回失敗した直後の、**同じ data に対する第 2 仮説**である。
- T-R / T-R2 の rate book の実測 IC は測定したどの horizon でも負だった。
- 必要な非 US 日次 10 年系列は **#484 時点で一度も probe されていなかった**（今回 probe し、到達可能と判明）。

→ **順位 4 で残す**（旧 3 位）。後述のとおり Track B として選ぶが、それは prior の強さではなく
**data の質と span の長さ**による。

## 4. 新しい ranking（§13・§14）

比較原則: `P(real edge) × 経済的規模 × persistence × breadth × 資本利用 × 情報利得`
÷ `cost × complexity × overfit risk × data burden × engineering burden`。厳密な score ではなく理由を明示する。

| 新順位 | ID | 方向 | なぜこの位置か |
| --- | --- | --- | --- |
| **1** | **S05** cross-asset risk repricing | B | **情報集合が本 programme で未検定**（H-002 は price-only の session/ATR 条件付け）。CBOE が自社 index を 1990 年から直接配信 → 長 span の FX と揃い、**22.1 年 / 検出力 0.60**。disjoint 2 span で符号一致を要求できる。弱点は breadth（risk 軸 1 本 ≒ 実効 2〜3） |
| **2** | **S06** commodity terms of trade | B | 未検定（C11 未実行）、EIA が公式に日次 1986 年から配信、mechanism が**通貨固有の実質所得**で S05 の単一 risk 軸とは別の経済主張。弱点は実効 breadth 1〜1.5 |
| **3** | **S07** credit spread / funding stress | B | 未検定・長 span だが **ICE 指数に無料の一次公表者が無く、FRED 不達でデータを失った**。S05 と同じ risk 軸でもある → S05 の robustness check が適所 |
| **4** | **S02** curve slope / curvature | A | closure が明示的に閉じていない。data は tier-1 公式で 1999 年より前まで届く。turnover 8〜18 は全候補中最小。**弱いのは prior であって feasibility ではない** |
| 5 | S25 中銀 balance sheet | A | 未検定・無料だが月次。長 span なら約 209 観測、seen corpus だけなら 56 で negative を閉じられない |
| 6 | S10 通貨 network 伝播 | C | §31 の重複監査が要る（H-003 / Track 1）。intraday 版は turnover 100 超、data は 4.7 年の seen corpus のみ |
| 7 | S14 multi-horizon price state | E | price-only。Track 1 の 5/20/60 線形結合が gross 負（H-023）、H-024 が復活を禁止 |
| 8 | S15 latent regime | E | return source ではなく conditioning。正の base が存在しない。H-017 が先例（vol filter が carry を 15/15 で悪化させた） |
| 9 | S12 相関 breakdown | D | H-003・H-024 と重複、自身の capacity 注記で年 2% 未満 |
| 10 | S26 国際資本 flow (TIC) | H | H-021 とは別物（現物 flow ≠ 先物投機）だが月次・6 週 lag・US 中心・availability 未 probe |
| 11 | S27 中銀 communication tone | A | 事象数は S03 と同じ天井。時刻付き過去テキストの機械取得は未検証、scoring に NLP（§33 で Human 判断） |

## 5. 誤った一般化はしない（§12）

以下は**この結果から導けない**:

- 「rates 全部が無理」— closed なのは simple public daily sovereign-yield directional family のみ。
  OIS・market-implied policy path・rate futures・intraday rate repricing・curve shape・term premium・
  rates options・distributional policy-path information は**いずれも無傷**。
- 「valuation 全部が無理」— 1 span 上の spot-only formulation 1 本が失敗しただけ。
- 「non-price 全部が無理」— その大半はまだ取得すらしていない。
- 「ML 全部が無理」— 積み上げる base となる stage 1 がまだ出ていないだけ。
- 「event 全部が無理」— opportunity 構造は実在が確立している。欠けているのは **closed でない方向 source**。
- 「cross-asset 全部が無理」— **方向 source として一度も検定していない**。
- 「cross-sectional 全部が無理」— H-023 は線形 architecture 1 本を否定しただけで、明示的に `FX_HAS_NO_EDGE` ではない。

## 6. signal-blind feasibility（§19–§22）

alpha を見る前に算定した。`vol/単位 gross = 0.030`（3 つの異なる signal の book で共通して観測された値）、
荷重規約 1.703 bp 片道。

| turnover (RT/年) | cost drag (IR) | net 0.3 に必要な日次 IC（breadth 2.5） |
| --- | --- | --- |
| 8 | 0.091 | 1.84% |
| 18 | 0.204 | 2.37% |
| 20 | 0.227 | 2.50% |
| 45 | 0.511 | 3.84% |

| ID | decision capability | 根拠 |
| --- | --- | --- |
| **S05** | **DECISION_CAPABLE** | VIX 9,276 日（うち長 span 内 4,381・近 span 内 1,389）。22.1 年で検出力 0.60 |
| **S02** | **DECISION_CAPABLE** | 2 年 leg は取得済み、10 年 leg のみ新規。全 source 到達確認済み |
| S06 | DECISION_CAPABLE_BUT_NARROW | span は十分だが実効 breadth 1.5 → 必要 IC が S05 比で約 30% 増 |
| S07 | **DATA_UNAVAILABLE_WITH_CURRENT_FREE_SOURCES** | ICE 指数に無料一次公表者が無い |
| S25 / S26 | MARGINAL | 月次。seen corpus だけでは negative を閉じられない |
| **S03/S04 (T-E)** | **EVENT_REPRICING_DATA_NOT_DECISION_GRADE** | §3 のとおり。backtest しない |

## 7. 有料データの評価（§18、design-only・購入しない）

| ID | 内容 | provider | 概算コスト | 可能になる仮説 | 無料代替が不十分な理由 | 期待情報利得 |
| --- | --- | --- | --- | --- | --- | --- |
| **S20** | G10 FX option の 25-delta risk reversal / IV skew（日次） | Bloomberg / Refinitiv、または CME（自社上場分） | terminal 級で年 USD 20–30k 規模、CME の historical dataset は USD 1–5k 規模。**公開価格表からの桁の目安であり見積ではない。照会していない** | risk reversal は**市場自身が付けた非対称性の価格** — 通貨が下がる保険と上がる保険の価格差。spot から導出できない forward-looking な方向期待で、本 programme が一度も観測していない instrument | FX の optionality を無料で価格付けるものは存在しない。spot からの実現 skew は backward-looking な price 統計で、既に何度も閉じた型 | **高い。** 未取得のうち最強の prior。negative でも「もう 1 本の formulation」ではなく**別の情報集合そのもの**を閉じられる |
| — | G10 の OIS curve / 短期金利先物履歴 | Bloomberg / Refinitiv / 各取引所 | terminal 級または dataset 単位。照会していない | **market-implied policy path** — closure が明示的に開けたまま残したもの。closed family は実現 2 年利回りを使ったが、OIS は期待経路を直接価格付けし term premium と分離する | 無料の代替が 2 年 sovereign yield であり、それがちょうど閉じた。G10 の無料 OIS 履歴は無い | **中程度。** きれいな instrument で金利方向を再開できるが、closed family の失敗は現実的 cost での monetisability であり、OIS がそれを変える保証はない |
| S22 | intraday 株価指数先物 | 各取引所 / vendor | dataset 単位、中程度 | session 間 cross-market 伝達 | price-only 版は C03・H-002 で閉鎖済み | **低い。** intraday horizon は本 programme が繰り返し致命的と測った turnover を伴う |

## 8. 選択した 2 track（§23–§26）

| | track | 候補 | 情報集合 |
| --- | --- | --- | --- |
| **Track A** | cross-asset risk repricing → G10 FX | **S05** | 外部資産（株式 volatility）の repricing |
| **Track B** | sovereign curve shape → G10 FX | **S02** | 金利 curve の**形状**（level ではない） |

**2 本にした理由**: §23 は最大 2 本を許すが 2 本を要求しない。S06 は 3 本目になり、実効 breadth の狭さで 3 つの中では最弱。
S07 はデータを失った。証拠が支えるのは 2 本である。

**この 2 本にした理由**: ranked 候補のうち、(a) 長 span で decision-capable、(b) 応答する無料**一次**公表者がいる、
(c) どの closed family の外側にある — を**同時に**満たすのはこの 2 つだけ。
さらに互いに情報が独立で（外部資産の repricing と金利 curve の形状）、
**一方の結果を使わずにもう一方を freeze できる**（§26）。

## 9. 進め方

- Track A を先に実行。**Track B の signal・horizon・benchmark・threshold・universe は Track A の結果で変更しない**（§26）。
  両方とも独立に freeze する。
- 各 track は **Stage 1: fixed / unfitted rule のみ**（§32）。Stage 1 で経済的証拠がゼロなら complex ML へ進まない（§33）。
- 許される結論は §46 の A〜E のみ。
- 5% / 10% 年率 net に必要な Sharpe・target vol・risk leverage・portfolio gross・margin 利用率・DD を算定するが、
  **net edge ≤ 0 なら leverage で救わない**（§35）。
